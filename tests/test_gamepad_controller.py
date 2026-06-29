import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

SERVER_DIR = Path(__file__).resolve().parents[1] / "Code" / "Server"
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

import pygame  # noqa: E402  (must come after the SDL dummy-driver env vars above)
pygame.init()

from gamepad_controller import (  # noqa: E402
    GamepadController,
    LEFT_X_AXIS,
    LEFT_Y_AXIS,
    RIGHT_X_AXIS,
    RIGHT_Y_AXIS,
    BUTTON_LB,
    BUTTON_RB,
)


class FakeJoystick:
    def __init__(self, axes=None, buttons=None, hat=(0, 0)):
        self._axes = axes or {}
        self._buttons = buttons or {}
        self._hat = hat

    def get_axis(self, index):
        return self._axes.get(index, 0.0)

    def get_button(self, index):
        return self._buttons.get(index, 0)

    def get_hat(self, index):
        return self._hat


class SpyDriveController:
    def __init__(self):
        self.calls = []
        self.last_command = None

    def apply_vector(self, x, y, rotation=0.0):
        self.calls.append((x, y, rotation))
        return True


class SpyCameraController:
    def __init__(self):
        self.calls = []

    def update(self, pan_rate, tilt_rate, dt):
        self.calls.append((pan_rate, tilt_rate, dt))
        return True


def make_controller(joystick):
    drive = SpyDriveController()
    camera = SpyCameraController()
    gamepad = GamepadController(drive, camera, joystick_factory=lambda: joystick)
    return gamepad, drive, camera


def test_no_gamepad_detected_is_a_safe_noop():
    gamepad, drive, camera = make_controller(None)
    assert gamepad.poll_once(dt=0.05) is False
    assert drive.calls == []
    assert camera.calls == []
    assert gamepad.connected is False


def test_left_stick_drives_strafe_and_throttle_inverted_y():
    joystick = FakeJoystick(axes={LEFT_X_AXIS: 0.5, LEFT_Y_AXIS: -0.5})
    gamepad, drive, camera = make_controller(joystick)
    gamepad.poll_once(dt=0.05)
    assert drive.calls == [(0.5, 0.5, 0.0)]  # stick-up (-0.5) becomes +0.5 throttle
    assert drive.last_command == "gamepad"


def test_right_stick_x_drives_rotation():
    joystick = FakeJoystick(axes={RIGHT_X_AXIS: 0.7})
    gamepad, drive, camera = make_controller(joystick)
    gamepad.poll_once(dt=0.05)
    assert drive.calls == [(0.0, 0.0, 0.7)]


def test_right_stick_y_drives_camera_tilt_inverted():
    joystick = FakeJoystick(axes={RIGHT_Y_AXIS: -0.6})
    gamepad, drive, camera = make_controller(joystick)
    gamepad.poll_once(dt=0.05)
    assert camera.calls == [(0.0, 0.6, 0.05)]


def test_deadzone_filters_small_axis_noise():
    joystick = FakeJoystick(axes={LEFT_X_AXIS: 0.02, LEFT_Y_AXIS: 0.03})
    gamepad, drive, camera = make_controller(joystick)
    gamepad.poll_once(dt=0.05)
    assert drive.calls == [(0.0, 0.0, 0.0)]


def test_lb_pans_left_rb_pans_right():
    left = FakeJoystick(buttons={BUTTON_LB: 1})
    right = FakeJoystick(buttons={BUTTON_RB: 1})

    gamepad, _, camera = make_controller(left)
    gamepad.poll_once(dt=0.1)
    assert camera.calls[-1][0] == -1.0

    gamepad, _, camera = make_controller(right)
    gamepad.poll_once(dt=0.1)
    assert camera.calls[-1][0] == 1.0


def test_dpad_left_right_also_pans():
    left = FakeJoystick(hat=(-1, 0))
    right = FakeJoystick(hat=(1, 0))

    gamepad, _, camera = make_controller(left)
    gamepad.poll_once(dt=0.1)
    assert camera.calls[-1][0] == -1.0

    gamepad, _, camera = make_controller(right)
    gamepad.poll_once(dt=0.1)
    assert camera.calls[-1][0] == 1.0
