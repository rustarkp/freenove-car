"""Stand-ins for real I2C hardware, used to test/run the motor stack
without a PCA9685 or any I2C bus attached. See docs/HARDWARE_TESTING.md.
"""


class FakeI2CBus:
    """Drop-in replacement for smbus.SMBus that records writes instead of
    talking to real hardware. Pass to PCA9685(bus=FakeI2CBus())."""

    def __init__(self):
        self.writes = []
        self.registers = {}
        self.closed = False

    def write_byte_data(self, address, register, value):
        self.writes.append((address, register, value))
        self.registers[(address, register)] = value

    def read_byte_data(self, address, register):
        return self.registers.get((address, register), 0)

    def close(self):
        self.closed = True
