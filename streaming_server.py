#!/usr/bin/env python3
import io
import os
import time
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from picamera2 import Picamera2
from picamera2.encoders import JpegEncoder
from picamera2.outputs import FileOutput
from libcamera import Transform

ROOT = Path(__file__).resolve().parent
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


class CameraService:
    def __init__(self, stream_size=(640, 480), capture_size=None):
        self.stream_size = stream_size
        self.capture_size = capture_size or (2592, 1944)
        self.picam2 = Picamera2()
        self.transform = Transform(hflip=0, vflip=0)
        self.preview_config = self.picam2.create_preview_configuration(main={"size": self.stream_size}, transform=self.transform)
        self.capture_config = self.picam2.create_still_configuration(main={"size": self.capture_size}, transform=self.transform)
        self.stream_config = self.picam2.create_video_configuration(main={"size": self.stream_size}, transform=self.transform)
        self.output = StreamingOutput()
        self.file_output = FileOutput(self.output)
        self.thread = None
        self.running = False
        self._lock = threading.Lock()
        self.picam2.configure(self.preview_config)
        self.picam2.start()
        self.running = True

    def capture_image(self, filename=None):
        if filename is None:
            filename = datetime.now().strftime("capture-%Y%m%d-%H%M%S.jpg")
        path = IMAGES_DIR / filename
        self.picam2.switch_mode_and_capture_file(self.capture_config, str(path), signal_function=lambda: None)
        return str(path)

    def start_stream(self):
        if self.thread and self.thread.is_alive():
            return
        self.picam2.stop()
        self.picam2.configure(self.stream_config)
        encoder = JpegEncoder()
        self.picam2.start_recording(encoder, self.file_output)
        self.running = True
        self.thread = threading.Thread(target=self._stream_loop, daemon=True)
        self.thread.start()

    def stop_stream(self):
        if self.thread and self.thread.is_alive():
            self.picam2.stop_recording()
            self.thread.join(timeout=1)
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


class StreamingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(self._html().encode('utf-8'))
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
          <head><title>Pi Car Stream</title></head>
          <body>
            <h1>Pi Car Stream</h1>
            <img src="/stream.mjpg" width="640" />
            <br/><br/>
            <button onclick="fetch('/capture').then(r=>r.json()).then(d=>alert(d.path))">Capture image</button>
          </body>
        </html>
        """

    def log_message(self, format, *args):
        return


service = None


def main():
    global service
    service = CameraService()
    service.start_stream()
    server = ThreadingHTTPServer(('0.0.0.0', 8000), StreamingHandler)
    print('Streaming server listening on http://0.0.0.0:8000')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        service.stop_stream()
        server.server_close()


if __name__ == '__main__':
    main()
