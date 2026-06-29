#!/usr/bin/python

import time
import math
import smbus
import glob
import re
import subprocess

# ============================================================================
# Raspi PCA9685 16-Channel PWM Servo Driver
# ============================================================================

class PCA9685:
    # Registers/etc.
    __SUBADR1            = 0x02
    __SUBADR2            = 0x03
    __SUBADR3            = 0x04
    __MODE1              = 0x00
    __PRESCALE           = 0xFE
    __LED0_ON_L          = 0x06
    __LED0_ON_H          = 0x07
    __LED0_OFF_L         = 0x08
    __LED0_OFF_H         = 0x09
    __ALLLED_ON_L        = 0xFA
    __ALLLED_ON_H        = 0xFB
    __ALLLED_OFF_L       = 0xFC
    __ALLLED_OFF_H       = 0xFD

    def __init__(self, address: int = 0x40, debug: bool = False, bus=None):
        # `bus` lets callers (tests, dry-run tooling) inject a stand-in object
        # implementing write_byte_data/read_byte_data/close instead of a real
        # smbus.SMBus, e.g. fake_hardware.FakeI2CBus. See docs/HARDWARE_TESTING.md.
        if bus is not None:
            self.bus = bus
            used_bus = 'injected'
            self.address = address
            self.debug = debug
            self.available = True
            if self.debug:
                print(f"PCA9685: using injected bus address {hex(address)}")
            try:
                self.write(self.__MODE1, 0x00)
            except Exception as exc:
                self.available = False
                if self.debug:
                    print('PCA9685 init warning:', type(exc).__name__, exc)
            return

        # Auto-detect an available I2C bus. Try common bus numbers first,
        # then any /dev/i2c-* entries found on the system.
        self.bus = None
        # Build candidate bus list: prefer actual /dev/i2c-* entries first
        candidates = []
        try:
            devs = glob.glob('/dev/i2c-*')
            bus_nums = []
            for d in devs:
                m = re.search(r'i2c-(\d+)', d)
                if m:
                    bus_nums.append(int(m.group(1)))
            # prefer discovered buses first, then fallback common buses
            candidates = bus_nums + [1, 4, 11, 13, 14]
        except Exception:
            candidates = [1, 4, 11, 13, 14]

        # If i2cdetect is available, prefer buses that report address 0x40
        i2cdetect_available = False
        try:
            subprocess.run(['i2cdetect', '--version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            i2cdetect_available = True
        except Exception:
            i2cdetect_available = False

        if i2cdetect_available:
            for b in candidates:
                try:
                    out = subprocess.check_output(['i2cdetect', '-y', str(b)], text=True, stderr=subprocess.DEVNULL)
                    # look for '40' as a standalone hex token in the output
                    if re.search(r'(?<!:)\b40\b(?!:)', out):
                        try:
                            self.bus = smbus.SMBus(b)
                            used_bus = b
                            break
                        except Exception:
                            self.bus = None
                            continue
                except Exception:
                    continue
        else:
            for b in candidates:
                try:
                    # Attempt to open the SMBus for this bus number
                    test_bus = smbus.SMBus(b)
                except Exception:
                    continue
                # Keep the bus open; we'll test device when accessing it later
                self.bus = test_bus
                used_bus = b
                break

        if self.bus is None:
            raise FileNotFoundError('No available i2c bus found')

        self.address = address
        self.debug = debug
        self.available = True
        if self.debug:
            print(f"PCA9685: using i2c bus {used_bus} address {hex(address)}")
        try:
            self.write(self.__MODE1, 0x00)
        except Exception as exc:
            # Hardware not responding; mark unavailable and continue so higher-level
            # code can decide to run in simulation or handle absence.
            self.available = False
            if self.debug:
                print('PCA9685 init warning:', type(exc).__name__, exc)
    
    def write(self, reg: int, value: int) -> None:
        """Writes an 8-bit value to the specified register/address."""
        if not getattr(self, 'available', True):
            raise OSError('PCA9685 not available')
        self.bus.write_byte_data(self.address, reg, value)
      
    def read(self, reg: int) -> int:
        """Read an unsigned byte from the I2C device."""
        if not getattr(self, 'available', True):
            raise OSError('PCA9685 not available')
        result = self.bus.read_byte_data(self.address, reg)
        return result
    
    def set_pwm_freq(self, freq: float) -> None:
        """Sets the PWM frequency."""
        prescaleval = 25000000.0    # 25MHz
        prescaleval /= 4096.0       # 12-bit
        prescaleval /= float(freq)
        prescaleval -= 1.0
        prescale = math.floor(prescaleval + 0.5)

        oldmode = self.read(self.__MODE1)
        newmode = (oldmode & 0x7F) | 0x10        # sleep
        self.write(self.__MODE1, newmode)        # go to sleep
        self.write(self.__PRESCALE, int(math.floor(prescale)))
        self.write(self.__MODE1, oldmode)
        time.sleep(0.005)
        self.write(self.__MODE1, oldmode | 0x80)


    def set_pwm(self, channel: int, on: int, off: int) -> None:
        """Sets a single PWM channel."""
        self.write(self.__LED0_ON_L + 4 * channel, on & 0xFF)
        self.write(self.__LED0_ON_H + 4 * channel, on >> 8)
        self.write(self.__LED0_OFF_L + 4 * channel, off & 0xFF)
        self.write(self.__LED0_OFF_H + 4 * channel, off >> 8)
    def set_motor_pwm(self, channel: int, duty: int) -> None:
        """Sets the PWM duty cycle for a motor."""
        self.set_pwm(channel, 0, duty)

    def set_servo_pulse(self, channel: int, pulse: float) -> None:
        """Sets the Servo Pulse, The PWM frequency must be 50HZ."""
        pulse = pulse * 4096 / 20000        # PWM frequency is 50HZ, the period is 20000us
        self.set_pwm(channel, 0, int(pulse))

    def close(self) -> None:
        """Close the I2C bus."""
        try:
            if self.bus is not None:
                self.bus.close()
        except Exception:
            pass


if __name__=='__main__':
    pass
    
      
