"""Reads a gamepad plugged directly into the Pi (via pygame/SDL) and drives
DriveController + CameraController. See docs/GAMEPAD_CONTROL.md.

Axis/button indices below match a common Xbox-style controller under SDL on
Linux. Controllers vary, so if yours doesn't match, run this file directly to
print live axis/button/hat values and adjust the constants:
    .venv/bin/python Code/Server/gamepad_controller.py
"""
import os
import threading
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

LEFT_X_AXIS = 0
LEFT_Y_AXIS = 1
RIGHT_X_AXIS = 2
RIGHT_Y_AXIS = 3
BUTTON_LB = 4
BUTTON_RB = 5
DEADZONE = 0.08
POLL_HZ = 30


def _default_joystick_factory():
    import pygame
    pygame.init()
    pygame.joystick.init()
    if pygame.joystick.get_count() == 0:
        return None
    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    return joystick


def _apply_deadzone(value, deadzone=DEADZONE):
    return 0.0 if abs(value) < deadzone else value


class GamepadController:
    """Polls a gamepad on a background thread and feeds DriveController +
    CameraController. `joystick_factory` lets tests inject a fake joystick
    instead of talking to pygame/SDL."""

    def __init__(self, drive_controller, camera_controller, joystick_factory=None, poll_hz=POLL_HZ):
        self.drive_controller = drive_controller
        self.camera_controller = camera_controller
        self.joystick_factory = joystick_factory or _default_joystick_factory
        self.poll_interval = 1.0 / poll_hz
        self.joystick = None
        self.thread = None
        self.running = False
        self.connected = False
        self.last_error = None

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

    def _ensure_joystick(self):
        if self.joystick is None:
            try:
                self.joystick = self.joystick_factory()
                self.connected = self.joystick is not None
                self.last_error = None if self.connected else "no gamepad detected"
            except Exception as exc:
                self.joystick = None
                self.connected = False
                self.last_error = str(exc)
        return self.joystick

    def _hat_x(self, joystick):
        try:
            return joystick.get_hat(0)[0]
        except Exception:
            return 0

    def poll_once(self, dt):
        joystick = self._ensure_joystick()
        if joystick is None:
            return False
        try:
            import pygame
            pygame.event.pump()
            left_x = _apply_deadzone(joystick.get_axis(LEFT_X_AXIS))
            left_y = _apply_deadzone(joystick.get_axis(LEFT_Y_AXIS))
            right_x = _apply_deadzone(joystick.get_axis(RIGHT_X_AXIS))
            right_y = _apply_deadzone(joystick.get_axis(RIGHT_Y_AXIS))
            hat_x = self._hat_x(joystick)
            pan_left = bool(joystick.get_button(BUTTON_LB)) or hat_x < 0
            pan_right = bool(joystick.get_button(BUTTON_RB)) or hat_x > 0
        except Exception as exc:
            self.joystick = None
            self.connected = False
            self.last_error = str(exc)
            return False

        # SDL reports "stick up" as a negative axis value; flip so pushing a
        # stick forward/up maps to a positive throttle/tilt rate.
        self.drive_controller.apply_vector(left_x, -left_y, right_x)
        self.drive_controller.last_command = "gamepad"

        pan_rate = (1.0 if pan_right else 0.0) - (1.0 if pan_left else 0.0)
        self.camera_controller.update(pan_rate, -right_y, dt)
        return True

    def _run(self):
        last = time.monotonic()
        while self.running:
            now = time.monotonic()
            dt = now - last
            last = now
            self.poll_once(dt)
            time.sleep(self.poll_interval)


if __name__ == '__main__':
    import pygame
    pygame.init()
    pygame.joystick.init()
    if pygame.joystick.get_count() == 0:
        print('No gamepad detected.')
    else:
        joystick = pygame.joystick.Joystick(0)
        joystick.init()
        print(f"Found: {joystick.get_name()} "
              f"({joystick.get_numaxes()} axes, {joystick.get_numbuttons()} buttons, {joystick.get_numhats()} hats)")
        print("Move sticks / press buttons. Ctrl+C to stop.")
        try:
            while True:
                pygame.event.pump()
                axes = [round(joystick.get_axis(i), 2) for i in range(joystick.get_numaxes())]
                buttons = [i for i in range(joystick.get_numbuttons()) if joystick.get_button(i)]
                hats = [joystick.get_hat(i) for i in range(joystick.get_numhats())]
                print(f"axes={axes} buttons={buttons} hats={hats}" + " " * 10, end='\r')
                time.sleep(0.1)
        except KeyboardInterrupt:
            print()
