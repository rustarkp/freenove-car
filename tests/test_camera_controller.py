import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "streaming_server.py"

spec = importlib.util.spec_from_file_location("streaming_server", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class FakeServo:
    def __init__(self):
        self.calls = []

    def set_servo_pwm(self, channel, angle):
        self.calls.append((channel, angle))


def test_pan_rate_moves_pan_angle_right():
    camera = module.CameraController(servo_factory=lambda: FakeServo())
    camera.update(pan_rate=1.0, tilt_rate=0.0, dt=1.0)
    assert camera.pan_angle == 180.0
    assert camera.tilt_angle == 90.0


def test_pan_rate_clamped_to_max():
    camera = module.CameraController(servo_factory=lambda: FakeServo())
    camera.update(pan_rate=1.0, tilt_rate=0.0, dt=5.0)
    assert camera.pan_angle == module.CameraController.PAN_MAX


def test_tilt_rate_clamped_to_min():
    camera = module.CameraController(servo_factory=lambda: FakeServo())
    camera.update(pan_rate=0.0, tilt_rate=-1.0, dt=5.0)
    assert camera.tilt_angle == module.CameraController.TILT_MIN


def test_rate_out_of_range_is_clamped_before_integrating():
    camera = module.CameraController(servo_factory=lambda: FakeServo())
    camera.update(pan_rate=5.0, tilt_rate=-5.0, dt=1.0)
    assert camera.pan_angle == 180.0  # rate clamped to 1.0, not 5.0
    assert camera.tilt_angle == 80.0  # rate clamped to -1.0, not -5.0


def test_zero_rate_does_not_call_servo():
    servo = FakeServo()
    camera = module.CameraController(servo_factory=lambda: servo)
    camera.update(pan_rate=0.0, tilt_rate=0.0, dt=1.0)
    assert servo.calls == []


def test_nonzero_rate_writes_both_channels():
    servo = FakeServo()
    camera = module.CameraController(servo_factory=lambda: servo)
    camera.update(pan_rate=0.5, tilt_rate=0.0, dt=0.1)
    assert servo.calls == [('0', int(camera.pan_angle)), ('1', int(camera.tilt_angle))]
