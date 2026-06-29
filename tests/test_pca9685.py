import sys
from pathlib import Path

SERVER_DIR = Path(__file__).resolve().parents[1] / "Code" / "Server"
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

from pca9685 import PCA9685
from fake_hardware import FakeI2CBus


def test_injected_bus_skips_autodetect_and_inits_ok():
    bus = FakeI2CBus()
    pwm = PCA9685(address=0x40, bus=bus)
    assert pwm.bus is bus
    assert pwm.available is True
    assert (0x40, 0x00, 0x00) in bus.writes  # MODE1 reset write from __init__


def test_set_motor_pwm_writes_expected_registers():
    bus = FakeI2CBus()
    pwm = PCA9685(address=0x40, bus=bus)
    bus.writes.clear()

    pwm.set_motor_pwm(channel=2, duty=1500)

    written = {(reg, value) for _, reg, value in bus.writes}
    on_l, on_h = 0x06 + 4 * 2, 0x07 + 4 * 2
    off_l, off_h = 0x08 + 4 * 2, 0x09 + 4 * 2
    assert (on_l, 0) in written
    assert (on_h, 0) in written
    assert (off_l, 1500 & 0xFF) in written
    assert (off_h, 1500 >> 8) in written


def test_close_closes_injected_bus():
    bus = FakeI2CBus()
    pwm = PCA9685(address=0x40, bus=bus)
    pwm.close()
    assert bus.closed is True
