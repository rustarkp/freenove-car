# Testing the motor/PCA9685 stack without real hardware

## Goal
Let `Code/Server/motor.py` and `Code/Server/pca9685.py` be unit-tested (and run
on a non-Pi machine) without a real I2C bus or PCA9685 board attached.

## Why
While surveying other Freenove-kit forks for ideas, `reinterpretcat/smart_car`
had a `Fake`/dry-run hardware layer that lets its whole command set run with no
GPIO/I2C present. We already do dependency injection for hardware at the
`streaming_server.py` `DriveController(motor_factory=...)` layer (see
`tests/test_drive_controller.py`), but that only covers the HTTP/drive-command
layer — `Ordinary_Car` and `PCA9685` themselves had no way to run without real
hardware, so their logic (wheel-direction routing, duty clamping, PWM register
encoding) had zero test coverage. This adds the same kind of injection point
one level lower, without rewriting the bus auto-detection or adopting a global
import-time monkeypatch scheme.

## How it works
- `PCA9685(address, debug, bus=None)` — pass `bus=` to skip I2C
  auto-detection entirely and use the given object instead. Any object with
  `write_byte_data(addr, reg, value)`, `read_byte_data(addr, reg)`, and
  `close()` works, matching `smbus.SMBus`'s interface.
- `Ordinary_Car(pwm=None)` — pass `pwm=` to inject a stand-in for the PCA9685
  instance instead of constructing a real one.
- `Code/Server/fake_hardware.py` provides `FakeI2CBus`, a minimal in-memory
  stand-in for `smbus.SMBus` that records every write so tests can assert on
  exact register/channel values.

Neither change affects existing callers — `motor.py`'s `__main__` block,
`streaming_server.py`'s `DriveController`, and the original `Code/Server`
entrypoints still construct `Ordinary_Car()`/`PCA9685()` with no arguments and
get the real auto-detecting I2C behavior.

## Running the tests
```bash
.venv/bin/pip install -r requirements-dev.txt  # one-time
.venv/bin/python -m pytest tests/
```

`tests/test_motor.py` and `tests/test_pca9685.py` cover wheel-direction
routing, duty clamping, and PWM register encoding using the fake bus/pwm
above — no I2C bus or PCA9685 board required.
