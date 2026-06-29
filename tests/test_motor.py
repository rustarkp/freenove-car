import sys
from pathlib import Path

SERVER_DIR = Path(__file__).resolve().parents[1] / "Code" / "Server"
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

from motor import Ordinary_Car


class FakePwm:
    def __init__(self):
        self.calls = []

    def set_pwm_freq(self, freq):
        pass

    def set_motor_pwm(self, channel, duty):
        self.calls.append((channel, duty))

    def close(self):
        pass


def test_left_upper_wheel_forward():
    pwm = FakePwm()
    car = Ordinary_Car(pwm=pwm)
    car.left_upper_wheel(2000)
    assert pwm.calls == [(0, 0), (1, 2000)]


def test_left_upper_wheel_reverse():
    pwm = FakePwm()
    car = Ordinary_Car(pwm=pwm)
    car.left_upper_wheel(-2000)
    assert pwm.calls == [(1, 0), (0, 2000)]


def test_left_upper_wheel_stop_brakes():
    pwm = FakePwm()
    car = Ordinary_Car(pwm=pwm)
    car.left_upper_wheel(0)
    assert pwm.calls == [(0, 4095), (1, 4095)]


def test_set_motor_model_clamps_and_routes_each_wheel():
    pwm = FakePwm()
    car = Ordinary_Car(pwm=pwm)
    car.set_motor_model(5000, -5000, 0, 4095)
    assert pwm.calls == [
        (0, 0), (1, 4095),   # left_upper: 5000 clamped to 4095
        (2, 0), (3, 4095),   # left_lower: -5000 clamped to -4095
        (6, 4095), (7, 4095),  # right_upper: 0 -> brake
        (4, 0), (5, 4095),   # right_lower: 4095
    ]


def test_close_stops_motors():
    pwm = FakePwm()
    car = Ordinary_Car(pwm=pwm)
    pwm.calls.clear()
    car.close()
    assert pwm.calls == [
        (0, 4095), (1, 4095),
        (2, 4095), (3, 4095),
        (6, 4095), (7, 4095),
        (4, 4095), (5, 4095),
    ]
