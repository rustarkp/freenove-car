#!/usr/bin/env python3
import io
import json
import os
import sys
import time
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from picamera2 import Picamera2
from picamera2.encoders import JpegEncoder
from picamera2.outputs import FileOutput
from libcamera import Transform

ROOT = Path(__file__).resolve().parent
SERVER_DIR = ROOT / "Code" / "Server"
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

from gamepad_controller import GamepadController

PRIVATE_DATA = ROOT / "private_data"
IMAGES_DIR = PRIVATE_DATA / "images"
VIDEOS_DIR = PRIVATE_DATA / "videos"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)
VIDEOS_DIR.mkdir(parents=True, exist_ok=True)


class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = threading.Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()
        return len(buf)


class FrameStreamer:
    def __init__(self, camera_service):
        self.camera_service = camera_service
        self.thread = None
        self.running = False

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1)

    def _run(self):
        while self.running:
            try:
                frame = self.camera_service.picam2.capture_array()
                if frame is None:
                    time.sleep(0.01)
                    continue
                # Convert to JPEG bytes for MJPEG streaming.
                import cv2
                import numpy as np
                image = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                _, encoded = cv2.imencode('.jpg', image, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
                self.camera_service.output.frame = encoded.tobytes()
                self.camera_service.output.condition.notify_all()
            except Exception:
                time.sleep(0.01)


class CameraService:
    def __init__(self, stream_size=(480, 320), capture_size=None):
        self.stream_size = stream_size
        self.capture_size = capture_size or (2592, 1944)
        self.jpeg_quality = int(os.environ.get("JPEG_QUALITY", "85"))
        self.picam2 = Picamera2()
        self.transform = Transform(hflip=0, vflip=0)
        self.preview_config = self.picam2.create_preview_configuration(main={"size": self.stream_size}, transform=self.transform)
        self.capture_config = self.picam2.create_still_configuration(main={"size": self.capture_size}, transform=self.transform)
        self.stream_config = self.picam2.create_video_configuration(main={"size": self.stream_size}, transform=self.transform)
        self.output = StreamingOutput()
        self.file_output = FileOutput(self.output)
        self.frame_streamer = FrameStreamer(self)
        self.thread = None
        self.running = False
        self.latest_capture_path = None
        self._lock = threading.Lock()
        self.picam2.configure(self.preview_config)
        self.picam2.start()
        self.running = True

    def capture_image(self, filename=None):
        if filename is None:
            filename = datetime.now().strftime("capture-%Y%m%d-%H%M%S.jpg")
        path = IMAGES_DIR / filename
        was_streaming = self.running
        if was_streaming:
            self.stop_stream()
        self.picam2.switch_mode_and_capture_file(self.capture_config, str(path), signal_function=lambda: None)
        self.latest_capture_path = str(path)
        if was_streaming:
            self.start_stream()
        return self.latest_capture_path

    def start_stream(self):
        if self.thread and self.thread.is_alive():
            return
        self.picam2.stop()
        self.picam2.configure(self.stream_config)
        self.picam2.start()
        self.running = True
        self.frame_streamer.start()

    def stop_stream(self):
        self.frame_streamer.stop()
        self.picam2.stop()
        self.picam2.configure(self.preview_config)
        self.picam2.start()
        self.running = False

    def _stream_loop(self):
        while self.running:
            time.sleep(0.01)

    def get_latest_frame(self):
        with self.output.condition:
            if self.output.frame is None:
                self.output.condition.wait(timeout=0.2)
            return self.output.frame


class DriveController:
    def __init__(self, motor_factory=None):
        self.motor_factory = motor_factory or (lambda: None)
        self.motor = None
        self.last_command = None
        self.last_vector = None
        self.last_error = None
        self.hardware_ready = False
        self._command_map = {
            "forward": (1000, 1000, 1000, 1000),
            "backward": (-1000, -1000, -1000, -1000),
            "left": (-1000, -1000, 1000, 1000),
            "right": (1000, 1000, -1000, -1000),
            "stop": (0, 0, 0, 0),
        }

    def ensure_motor(self):
        if self.motor is None:
            try:
                self.motor = self.motor_factory()
                self.hardware_ready = True
                self.last_error = None
            except Exception as exc:
                self.hardware_ready = False
                self.last_error = str(exc)
                self.motor = None
        return self.motor

    def apply_command(self, command):
        if command not in self._command_map:
            return False
        self.last_command = command
        self.last_vector = None
        motor = self.ensure_motor()
        if motor is None:
            return True
        try:
            motor.set_motor_model(*self._command_map[command])
        except Exception as exc:
            self.last_error = str(exc)
            return False
        return True

    def apply_vector(self, x, y, rotation=0.0):
        self.last_command = "joystick"
        self.last_vector = (float(x), float(y), float(rotation))
        motor = self.ensure_motor()
        if motor is None:
            return True
        try:
            strafe = float(x)
            throttle = float(y)
            turn = float(rotation)
            fl = throttle + strafe + turn
            fr = throttle - strafe - turn
            bl = throttle - strafe + turn
            br = throttle + strafe - turn
            max_abs = max(abs(value) for value in (fl, fr, bl, br)) or 1.0
            scale = 1.0 if max_abs <= 1.0 else 1.0 / max_abs
            values = [int(value * scale * 2000) for value in (fl, fr, bl, br)]
            motor.set_motor_model(*values)
        except Exception as exc:
            self.last_error = str(exc)
            return False
        return True


class CameraController:
    """Drives the pan/tilt camera servos (PCA9685 channels '0'/'1') as a rate
    integrator: callers pass a -1..1 rate per axis each tick rather than an
    absolute angle, so releasing a stick/button holds position instead of
    snapping back to center. See docs/GAMEPAD_CONTROL.md."""

    PAN_CHANNEL = '0'
    TILT_CHANNEL = '1'
    PAN_MIN, PAN_MAX = 0.0, 180.0
    TILT_MIN, TILT_MAX = 80.0, 180.0
    PAN_SPEED_DEG_S = 90.0
    TILT_SPEED_DEG_S = 60.0

    def __init__(self, servo_factory=None):
        self.servo_factory = servo_factory or (lambda: None)
        self.servo = None
        self.pan_angle = 90.0
        self.tilt_angle = 90.0
        self.last_error = None
        self.hardware_ready = False

    def ensure_servo(self):
        if self.servo is None:
            try:
                self.servo = self.servo_factory()
                self.hardware_ready = True
                self.last_error = None
            except Exception as exc:
                self.hardware_ready = False
                self.last_error = str(exc)
                self.servo = None
        return self.servo

    def update(self, pan_rate, tilt_rate, dt):
        pan_rate = max(-1.0, min(1.0, float(pan_rate)))
        tilt_rate = max(-1.0, min(1.0, float(tilt_rate)))
        if pan_rate == 0.0 and tilt_rate == 0.0:
            return True
        self.pan_angle = max(self.PAN_MIN, min(self.PAN_MAX, self.pan_angle + pan_rate * self.PAN_SPEED_DEG_S * dt))
        self.tilt_angle = max(self.TILT_MIN, min(self.TILT_MAX, self.tilt_angle + tilt_rate * self.TILT_SPEED_DEG_S * dt))
        servo = self.ensure_servo()
        if servo is None:
            return True
        try:
            servo.set_servo_pwm(self.PAN_CHANNEL, int(self.pan_angle))
            servo.set_servo_pwm(self.TILT_CHANNEL, int(self.tilt_angle))
        except Exception as exc:
            self.last_error = str(exc)
            return False
        return True


class StreamingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(self._html().encode('utf-8'))
            return
        if self.path == '/status':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            payload = {
                'streaming': bool(service and service.running),
                'last_capture': service.latest_capture_path if service else None,
                'image_dir': str(IMAGES_DIR),
                'last_command': drive_controller.last_command if drive_controller else None,
                'hardware_ready': bool(drive_controller and drive_controller.hardware_ready),
                'last_error': drive_controller.last_error if drive_controller else None,
                'gamepad_connected': bool(gamepad_controller and gamepad_controller.connected),
                'pan_angle': camera_controller.pan_angle if camera_controller else None,
                'tilt_angle': camera_controller.tilt_angle if camera_controller else None,
                'camera_hardware_ready': bool(camera_controller and camera_controller.hardware_ready),
            }
            self.wfile.write(json.dumps(payload).encode('utf-8'))
            return
        if self.path.startswith('/drive/'):
            parsed = urlparse(self.path)
            path_parts = parsed.path.split('/')
            if len(path_parts) >= 3 and path_parts[2] == 'joystick':
                params = parse_qs(parsed.query)
                x = float(params.get('x', ['0'])[0])
                y = float(params.get('y', ['0'])[0])
                rotation = float(params.get('rotation', ['0'])[0])
                ok = drive_controller.apply_vector(x, y, rotation) if drive_controller else False
                self.send_response(200 if ok else 400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'ok': ok, 'command': 'joystick', 'vector': [x, y, rotation], 'hardware_ready': bool(drive_controller and drive_controller.hardware_ready), 'last_error': drive_controller.last_error if drive_controller else None}).encode('utf-8'))
                return
            command = path_parts[-1]
            ok = drive_controller.apply_command(command) if drive_controller else False
            self.send_response(200 if ok else 400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'ok': ok, 'command': command, 'hardware_ready': bool(drive_controller and drive_controller.hardware_ready), 'last_error': drive_controller.last_error if drive_controller else None}).encode('utf-8'))
            return
        if self.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
            self.end_headers()
            while True:
                frame = service.get_latest_frame()
                if frame is None:
                    continue
                self.wfile.write(b'--frame\r\n')
                self.wfile.write(b'Content-Type: image/jpeg\r\n')
                self.wfile.write(f'Content-Length: {len(frame)}\r\n\r\n'.encode('utf-8'))
                self.wfile.write(frame)
                self.wfile.write(b'\r\n')
                self.wfile.flush()
            return
        if self.path.startswith('/capture'):
            path = service.capture_image()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(f'{{"path":"{path}"}}'.encode('utf-8'))
            return
        self.send_error(404)

    def _html(self):
        return """
        <html>
          <head>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
            <title>Pi Car Stream</title>
            <style>
              :root { color-scheme: dark; }
              * { box-sizing: border-box; }
              body { font-family: Arial, sans-serif; margin: 0; padding: clamp(10px, 2.5vw, 20px); background: #0f172a; color: #f8fafc; line-height: 1.4; }
              .panel { width: min(100%, 920px); margin: 0 auto; }
              h1 { margin: 0 0 10px; font-size: clamp(1.2rem, 2.2vw, 1.7rem); }
              .controls { display: flex; gap: 8px; flex-wrap: wrap; margin: 10px 0 12px; }
              button { border: 0; border-radius: 999px; padding: 10px 14px; background: linear-gradient(135deg, #2563eb, #3b82f6); color: white; font-weight: 600; cursor: pointer; min-height: 44px; touch-action: manipulation; }
              button:hover { filter: brightness(1.05); }
              .stream-wrap { width: 100%; border-radius: 14px; overflow: hidden; background: #000; border: 1px solid rgba(255,255,255,0.12); position: relative; }
              .stream-wrap img { display: block; width: 100%; height: auto; max-width: 100%; border-radius: 14px; background: #000; aspect-ratio: 4 / 3; object-fit: contain; }
              .status { margin-top: 10px; padding: 12px; border-radius: 12px; background: rgba(15, 23, 42, 0.95); border: 1px solid rgba(255,255,255,0.08); font-size: 0.95rem; word-break: break-word; }
              .joystick-card { margin: 10px 0 12px; padding: 12px; border-radius: 14px; background: rgba(15, 23, 42, 0.9); border: 1px solid rgba(255,255,255,0.08); }
              .joystick-label { font-size: 0.95rem; margin-bottom: 8px; opacity: 0.9; }
              .joystick-shell { position: relative; width: min(100%, 280px); aspect-ratio: 1; margin: 0 auto; border-radius: 50%; background: radial-gradient(circle at 30% 30%, #243447, #0f172a 70%); border: 2px solid rgba(255,255,255,0.16); touch-action: none; }
              .joystick-handle { position: absolute; width: 38%; aspect-ratio: 1; border-radius: 50%; background: linear-gradient(135deg, #60a5fa, #2563eb); box-shadow: 0 10px 20px rgba(0,0,0,0.25); left: 31%; top: 31%; }
              .compact .controls { margin: 6px 0 8px; }
              .compact button { padding: 8px 12px; min-height: 40px; font-size: 0.95rem; }
              .compact .status { padding: 10px; font-size: 0.9rem; }
              .fullscreen-toggle { margin-top: 8px; }
              body.fullscreen .panel { width: 100%; max-width: none; padding: 0; }
              body.fullscreen .controls { padding: 8px; margin: 0; }
              body.fullscreen .stream-wrap { border-radius: 0; border: 0; }
              body.fullscreen .stream-wrap img { border-radius: 0; aspect-ratio: auto; height: 100vh; object-fit: contain; }
              body.fullscreen .status { display: none; }
              @media (max-width: 640px) {
                body { padding: 8px; }
                .controls { flex-direction: column; }
                button { width: 100%; }
                .status { font-size: 0.9rem; }
              }
              @media (max-width: 480px) {
                body { padding: 6px; }
                .panel { width: 100%; }
                .controls { gap: 6px; }
                .compact .controls { flex-direction: row; }
                .compact button { width: auto; flex: 1; }
                .stream-wrap img { aspect-ratio: 3 / 4; }
              }
            </style>
          </head>
          <body>
            <div class="panel">
              <h1>Pi Car Stream</h1>
              <div class="controls">
                <button onclick="captureImage()">Capture image</button>
                <button onclick="refreshStatus()">Refresh status</button>
                <button class="fullscreen-toggle" onclick="toggleFullscreen()">Fullscreen</button>
              </div>
              <div class="controls">
                <button onclick="sendDriveCommand('forward')">Forward</button>
                <button onclick="sendDriveCommand('left')">Left</button>
                <button onclick="sendDriveCommand('stop')">Stop</button>
                <button onclick="sendDriveCommand('right')">Right</button>
                <button onclick="sendDriveCommand('backward')">Backward</button>
              </div>
              <div class="joystick-card">
                <div class="joystick-label">Touch and drag to combine throttle and turning.</div>
                <div class="joystick-shell" id="joystickShell">
                  <div class="joystick-handle" id="joystickHandle"></div>
                </div>
              </div>
              <div class="stream-wrap" id="streamWrap">
                <img src="/stream.mjpg" alt="Live stream" />
              </div>
              <div class="status" id="status">Loading...</div>
            </div>
            <script>
              async function captureImage() {
                const response = await fetch('/capture');
                const data = await response.json();
                document.getElementById('status').textContent = 'Captured: ' + data.path;
              }
              async function refreshStatus() {
                const response = await fetch('/status');
                const data = await response.json();
                const hardware = data.hardware_ready ? 'ready' : 'unavailable';
                const error = data.last_error ? ' | Error: ' + data.last_error : '';
                document.getElementById('status').textContent = 'Streaming: ' + data.streaming + ' | Last capture: ' + (data.last_capture || 'none') + ' | Command: ' + (data.last_command || 'none') + ' | Hardware: ' + hardware + error;
              }
              async function sendDriveCommand(command) {
                const response = await fetch('/drive/' + command);
                const data = await response.json();
                if (data.ok) {
                  await refreshStatus();
                }
              }
              async function sendJoystickCommand(x, y, rotation) {
                const response = await fetch('/drive/joystick?x=' + x.toFixed(3) + '&y=' + y.toFixed(3) + '&rotation=' + rotation.toFixed(3));
                const data = await response.json();
                if (data.ok) {
                  await refreshStatus();
                }
              }
              const joystickShell = document.getElementById('joystickShell');
              const joystickHandle = document.getElementById('joystickHandle');
              let activeJoystick = false;
              function updateJoystick(clientX, clientY) {
                const rect = joystickShell.getBoundingClientRect();
                const centerX = rect.left + rect.width / 2;
                const centerY = rect.top + rect.height / 2;
                const dx = Math.max(-1, Math.min(1, (clientX - centerX) / (rect.width / 2)));
                const dy = Math.max(-1, Math.min(1, (centerY - clientY) / (rect.height / 2)));
                const handleX = Math.max(-rect.width * 0.3, Math.min(rect.width * 0.3, dx * rect.width * 0.3));
                const handleY = Math.max(-rect.height * 0.3, Math.min(rect.height * 0.3, dy * rect.height * 0.3));
                joystickHandle.style.transform = 'translate(' + handleX + 'px, ' + handleY + 'px)';
                sendJoystickCommand(dx, dy, dx);
              }
              joystickShell.addEventListener('pointerdown', (event) => {
                activeJoystick = true;
                joystickShell.setPointerCapture(event.pointerId);
                updateJoystick(event.clientX, event.clientY);
              });
              joystickShell.addEventListener('pointermove', (event) => {
                if (!activeJoystick) return;
                updateJoystick(event.clientX, event.clientY);
              });
              function endJoystick(event) {
                if (!activeJoystick) return;
                activeJoystick = false;
                joystickHandle.style.transform = 'translate(0px, 0px)';
                sendJoystickCommand(0, 0, 0);
              }
              joystickShell.addEventListener('pointerup', endJoystick);
              joystickShell.addEventListener('pointercancel', endJoystick);
              joystickShell.addEventListener('pointerleave', endJoystick);
              function toggleFullscreen() {
                const body = document.body;
                const wrap = document.getElementById('streamWrap');
                const isFullscreen = body.classList.toggle('fullscreen');
                if (isFullscreen) {
                  body.classList.add('compact');
                  wrap.scrollIntoView({ behavior: 'smooth', block: 'start' });
                } else {
                  body.classList.remove('compact');
                }
              }
              function adaptLayout() {
                const body = document.body;
                const isPortrait = window.matchMedia('(orientation: portrait)').matches;
                if (window.innerWidth <= 480 || isPortrait) {
                  body.classList.add('compact');
                } else {
                  body.classList.remove('compact');
                }
              }
              window.addEventListener('resize', adaptLayout);
              window.addEventListener('orientationchange', adaptLayout);
              adaptLayout();
              refreshStatus();
            </script>
          </body>
        </html>
        """

    def log_message(self, format, *args):
        return


service = None
drive_controller = None
camera_controller = None
gamepad_controller = None


def main():
    global service, drive_controller, camera_controller, gamepad_controller
    service = CameraService()
    drive_controller = DriveController(motor_factory=lambda: __import__('motor', fromlist=['Ordinary_Car']).Ordinary_Car())
    camera_controller = CameraController(servo_factory=lambda: __import__('servo', fromlist=['Servo']).Servo())
    gamepad_controller = GamepadController(drive_controller, camera_controller)
    gamepad_controller.start()
    service.start_stream()
    server = ThreadingHTTPServer(('0.0.0.0', 8000), StreamingHandler)
    print('Streaming server listening on http://0.0.0.0:8000')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        gamepad_controller.stop()
        service.stop_stream()
        server.server_close()


if __name__ == '__main__':
    main()
