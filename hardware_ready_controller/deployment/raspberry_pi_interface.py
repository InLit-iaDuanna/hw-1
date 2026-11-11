"""
Raspberry Pi Hardware Interface Implementation
Provides real hardware drivers for Dynamixel motors, SPI encoders, and GPIO sensors.
"""

import threading
import time
from typing import Optional

import numpy as np

try:
    import spidev
except ImportError:
    spidev = None

try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None

try:
    from dynamixel_sdk import *
except ImportError:
    # Fallback mock for development
    class PortHandler:
        @staticmethod
        def getPortHandler(port):
            return None

    class PacketHandler:
        @staticmethod
        def getPacketHandler(version):
            return None

    COMM_SUCCESS = 0
    DXL_LOBYTE = lambda x: x & 0xFF
    DXL_LOWORD = lambda x: x & 0xFFFF
    DXL_HIBYTE = lambda x: (x >> 8) & 0xFF
    DXL_HIWORD = lambda x: (x >> 16) & 0xFFFF

from ..core.hardware_interface import HardwareConfig, HardwareInterface


class RaspberryPiInterface(HardwareInterface):
    """
    Raspberry Pi hardware interface for real deployment.
    Interfaces with:
    - Dynamixel motors via serial UART
    - AS5048 magnetic encoders via SPI
    - Contact sensors via GPIO
    """

    # Dynamixel Protocol 2.0 Control Table
    ADDR_TORQUE_ENABLE = 64
    ADDR_GOAL_POSITION = 116
    ADDR_PRESENT_POSITION = 132
    ADDR_GOAL_VELOCITY = 104
    ADDR_PRESENT_VELOCITY = 128
    ADDR_GOAL_CURRENT = 102
    ADDR_PRESENT_CURRENT = 126
    ADDR_OPERATING_MODE = 11

    # Operating Modes
    MODE_CURRENT = 0
    MODE_VELOCITY = 1
    MODE_POSITION = 3
    MODE_CURRENT_POSITION = 5

    # AS5048 SPI Commands
    AS5048_ANGLE_REG = 0xFFFF
    AS5048_CMD_READ = 0x4000

    def __init__(self, config: HardwareConfig):
        super().__init__(config)

        # Dynamixel setup
        self.port_handler: Optional[PortHandler] = None
        self.packet_handler: Optional[PacketHandler] = None
        self.motor_ids = config.motor_ids if hasattr(config, "motor_ids") else [1, 2]

        # SPI encoder setup
        self.spi: Optional[spidev.SpiDev] = None
        self.encoder_channels = (
            config.encoder_channels if hasattr(config, "encoder_channels") else [0, 1]
        )

        # GPIO sensor setup
        self.contact_pins = (
            config.contact_pins if hasattr(config, "contact_pins") else [17, 27]
        )

        # State tracking
        self._last_positions = np.zeros(len(self.motor_ids))
        self._last_velocities = np.zeros(len(self.motor_ids))
        self._position_offsets = np.zeros(len(self.motor_ids))

        # Thread safety
        self._lock = threading.Lock()
        self._initialized = False

        # Error tracking
        self._error_counts = {"motor": 0, "encoder": 0, "gpio": 0}
        self._max_errors = 10

    def initialize(self) -> bool:
        """Initialize all hardware interfaces."""
        try:
            success = True

            # Initialize Dynamixel motors
            if not self._init_dynamixel():
                print("Warning: Dynamixel initialization failed")
                success = False

            # Initialize SPI encoders
            if not self._init_spi():
                print("Warning: SPI encoder initialization failed")
                success = False

            # Initialize GPIO sensors
            if not self._init_gpio():
                print("Warning: GPIO initialization failed")
                success = False

            # Set real-time thread priority
            self._set_realtime_priority()

            self._initialized = success
            return success

        except Exception as e:
            print(f"Hardware initialization error: {e}")
            return False

    def _init_dynamixel(self) -> bool:
        """Initialize Dynamixel motor communication."""
        try:
            device_name = (
                self.config.device_name
                if hasattr(self.config, "device_name")
                else "/dev/ttyUSB0"
            )
            baudrate = (
                self.config.baudrate if hasattr(self.config, "baudrate") else 57600
            )
            protocol_version = 2.0

            self.port_handler = PortHandler(device_name)
            self.packet_handler = PacketHandler(protocol_version)

            if not self.port_handler.openPort():
                print(f"Failed to open port {device_name}")
                return False

            if not self.port_handler.setBaudRate(baudrate):
                print(f"Failed to set baudrate to {baudrate}")
                return False

            # Enable torque and set operating mode for each motor
            for motor_id in self.motor_ids:
                # Disable torque to change operating mode
                self._write_dynamixel(motor_id, self.ADDR_TORQUE_ENABLE, 0, 1)

                # Set to current-based position control mode
                self._write_dynamixel(
                    motor_id, self.ADDR_OPERATING_MODE, self.MODE_CURRENT_POSITION, 1
                )

                # Enable torque
                self._write_dynamixel(motor_id, self.ADDR_TORQUE_ENABLE, 1, 1)

            print(f"Dynamixel motors initialized: {self.motor_ids}")
            return True

        except Exception as e:
            print(f"Dynamixel initialization error: {e}")
            return False

    def _init_spi(self) -> bool:
        """Initialize SPI communication for encoders."""
        try:
            if spidev is None:
                print("spidev module not available")
                return False

            self.spi = spidev.SpiDev()
            spi_bus = 0
            spi_device = 0

            self.spi.open(spi_bus, spi_device)
            self.spi.max_speed_hz = 1000000  # 1 MHz
            self.spi.mode = 1  # CPOL=0, CPHA=1 for AS5048

            # Test read from each encoder
            for channel in self.encoder_channels:
                angle = self._read_encoder_raw(channel)
                if angle < 0:
                    print(f"Failed to read encoder channel {channel}")
                    return False

            print(f"SPI encoders initialized: {self.encoder_channels}")
            return True

        except Exception as e:
            print(f"SPI initialization error: {e}")
            return False

    def _init_gpio(self) -> bool:
        """Initialize GPIO pins for contact sensors."""
        try:
            if GPIO is None:
                print("RPi.GPIO module not available")
                return False

            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)

            for pin in self.contact_pins:
                GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

            print(f"GPIO contact sensors initialized: {self.contact_pins}")
            return True

        except Exception as e:
            print(f"GPIO initialization error: {e}")
            return False

    def _set_realtime_priority(self):
        """Set real-time thread priority for deterministic control."""
        try:
            import os

            # Set nice value for higher scheduling priority
            os.nice(-10)

            # Attempt to set real-time scheduling (requires root)
            try:
                import ctypes

                libc = ctypes.CDLL("libc.so.6")
                SCHED_FIFO = 1

                class SchedParam(ctypes.Structure):
                    _fields_ = [("sched_priority", ctypes.c_int)]

                param = SchedParam()
                param.sched_priority = 50  # RT priority 50

                result = libc.sched_setscheduler(0, SCHED_FIFO, ctypes.byref(param))
                if result == 0:
                    print("Real-time thread priority set (SCHED_FIFO)")
                else:
                    print("Failed to set RT priority (may need root)")
            except:
                print("Real-time scheduling not available")

        except Exception as e:
            print(f"Priority setting warning: {e}")

    def read_joint_positions(self) -> np.ndarray:
        """Read joint positions from encoders."""
        with self._lock:
            try:
                positions = np.zeros(len(self.encoder_channels))

                for i, channel in enumerate(self.encoder_channels):
                    raw_angle = self._read_encoder_raw(channel)
                    if raw_angle >= 0:
                        # Convert 14-bit value to radians
                        positions[i] = (
                            raw_angle / 16384.0
                        ) * 2 * np.pi - self._position_offsets[i]
                        self._error_counts["encoder"] = 0
                    else:
                        # Use last known position on error
                        positions[i] = self._last_positions[i]
                        self._error_counts["encoder"] += 1
                        if self._error_counts["encoder"] > self._max_errors:
                            raise RuntimeError(
                                "Encoder read failures exceeded threshold"
                            )

                self._last_positions = positions.copy()
                return positions

            except Exception as e:
                print(f"Position read error: {e}")
                return self._last_positions.copy()

    def read_joint_velocities(self) -> np.ndarray:
        """Read joint velocities from motors."""
        with self._lock:
            try:
                velocities = np.zeros(len(self.motor_ids))

                for i, motor_id in enumerate(self.motor_ids):
                    raw_vel = self._read_dynamixel(
                        motor_id, self.ADDR_PRESENT_VELOCITY, 4
                    )
                    if raw_vel is not None:
                        # Convert Dynamixel velocity units to rad/s
                        # Dynamixel velocity unit: 0.229 rpm
                        velocities[i] = (raw_vel * 0.229 * 2 * np.pi) / 60.0
                        self._error_counts["motor"] = 0
                    else:
                        velocities[i] = self._last_velocities[i]
                        self._error_counts["motor"] += 1

                self._last_velocities = velocities.copy()
                return velocities

            except Exception as e:
                print(f"Velocity read error: {e}")
                return self._last_velocities.copy()

    def read_contact_states(self) -> np.ndarray:
        """Read contact sensor states from GPIO."""
        try:
            if GPIO is None:
                return np.zeros(len(self.contact_pins), dtype=bool)

            contacts = np.zeros(len(self.contact_pins), dtype=bool)
            for i, pin in enumerate(self.contact_pins):
                # Inverted logic: LOW = contact (pull-up resistor)
                contacts[i] = not GPIO.input(pin)

            return contacts

        except Exception as e:
            print(f"Contact read error: {e}")
            self._error_counts["gpio"] += 1
            return np.zeros(len(self.contact_pins), dtype=bool)

    def write_motor_torques(self, torques: np.ndarray) -> bool:
        """Write torque commands to motors."""
        with self._lock:
            try:
                for i, motor_id in enumerate(self.motor_ids):
                    # Convert torque (Nm) to Dynamixel current units
                    # Adjust conversion factor based on motor specs
                    current_mA = int(torques[i] * 1000)  # Example conversion
                    current_value = max(-2047, min(2047, current_mA))

                    success = self._write_dynamixel(
                        motor_id, self.ADDR_GOAL_CURRENT, current_value, 2
                    )
                    if not success:
                        self._error_counts["motor"] += 1
                        if self._error_counts["motor"] > self._max_errors:
                            return False

                return True

            except Exception as e:
                print(f"Torque write error: {e}")
                return False

    def _read_encoder_raw(self, channel: int) -> int:
        """Read raw 14-bit angle from AS5048 encoder via SPI."""
        try:
            if self.spi is None:
                return -1

            # Send read command for angle register
            cmd = [
                (self.AS5048_CMD_READ | self.AS5048_ANGLE_REG) >> 8,
                (self.AS5048_CMD_READ | self.AS5048_ANGLE_REG) & 0xFF,
            ]

            response = self.spi.xfer2(cmd)

            # Extract 14-bit angle from response
            angle = ((response[0] & 0x3F) << 8) | response[1]
            return angle

        except Exception as e:
            print(f"Encoder read error (channel {channel}): {e}")
            return -1

    def _read_dynamixel(
        self, motor_id: int, address: int, length: int
    ) -> Optional[int]:
        """Read data from Dynamixel motor."""
        try:
            if length == 1:
                value, result, error = self.packet_handler.read1ByteTxRx(
                    self.port_handler, motor_id, address
                )
            elif length == 2:
                value, result, error = self.packet_handler.read2ByteTxRx(
                    self.port_handler, motor_id, address
                )
            elif length == 4:
                value, result, error = self.packet_handler.read4ByteTxRx(
                    self.port_handler, motor_id, address
                )
            else:
                return None

            if result != COMM_SUCCESS:
                print(
                    f"Dynamixel read error: {self.packet_handler.getTxRxResult(result)}"
                )
                return None

            return value

        except Exception as e:
            print(f"Dynamixel read exception: {e}")
            return None

    def _write_dynamixel(
        self, motor_id: int, address: int, value: int, length: int
    ) -> bool:
        """Write data to Dynamixel motor."""
        try:
            if length == 1:
                result, error = self.packet_handler.write1ByteTxRx(
                    self.port_handler, motor_id, address, value
                )
            elif length == 2:
                result, error = self.packet_handler.write2ByteTxRx(
                    self.port_handler, motor_id, address, value
                )
            elif length == 4:
                result, error = self.packet_handler.write4ByteTxRx(
                    self.port_handler, motor_id, address, value
                )
            else:
                return False

            if result != COMM_SUCCESS:
                print(
                    f"Dynamixel write error: {self.packet_handler.getTxRxResult(result)}"
                )
                return False

            return True

        except Exception as e:
            print(f"Dynamixel write exception: {e}")
            return False

    def emergency_stop(self) -> bool:
        """Immediately disable all motor torques."""
        try:
            success = True
            for motor_id in self.motor_ids:
                if not self._write_dynamixel(motor_id, self.ADDR_TORQUE_ENABLE, 0, 1):
                    success = False

            print("Emergency stop executed")
            return success

        except Exception as e:
            print(f"Emergency stop error: {e}")
            return False

    def reset(self) -> bool:
        """Reset hardware to safe state and re-enable."""
        try:
            # Disable all torques
            self.emergency_stop()
            time.sleep(0.1)

            # Reset error counters
            self._error_counts = {"motor": 0, "encoder": 0, "gpio": 0}

            # Re-enable torques
            for motor_id in self.motor_ids:
                self._write_dynamixel(motor_id, self.ADDR_TORQUE_ENABLE, 1, 1)

            # Zero position offsets
            current_positions = self.read_joint_positions()
            self._position_offsets = current_positions.copy()

            print("Hardware reset complete")
            return True

        except Exception as e:
            print(f"Reset error: {e}")
            return False

    def shutdown(self):
        """Clean shutdown of all hardware interfaces."""
        try:
            # Disable motor torques
            if self.port_handler and self.packet_handler:
                for motor_id in self.motor_ids:
                    self._write_dynamixel(motor_id, self.ADDR_TORQUE_ENABLE, 0, 1)
                self.port_handler.closePort()

            # Close SPI
            if self.spi:
                self.spi.close()

            # Clean up GPIO
            if GPIO:
                GPIO.cleanup()

            print("Hardware shutdown complete")

        except Exception as e:
            print(f"Shutdown error: {e}")

    def get_hardware_info(self) -> dict:
        """Get hardware status and diagnostic information."""
        return {
            "initialized": self._initialized,
            "motor_ids": self.motor_ids,
            "encoder_channels": self.encoder_channels,
            "contact_pins": self.contact_pins,
            "error_counts": self._error_counts.copy(),
            "dynamixel_connected": (
                self.port_handler is not None and self.port_handler.is_open
                if self.port_handler
                else False
            ),
            "spi_connected": self.spi is not None,
            "gpio_available": GPIO is not None,
        }
