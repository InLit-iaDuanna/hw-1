"""
Hardware Interface Module
Abstract hardware interface with MuJoCo simulation implementation.

Provides:
- Abstract HardwareInterface base class
- MuJoCoInterface for simulation testing
- Sensor reading (joint angles, velocities, contact states)
- Motor commands with safety checks
- Real-time loop timing utilities
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

import numpy as np


@dataclass
class SensorData:
    """Container for sensor readings."""

    joint_angles: np.ndarray  # [rad] for each joint
    joint_velocities: np.ndarray  # [rad/s] for each joint
    contact_states: np.ndarray  # [0/1] for each contact sensor
    timestamp: float  # [s] time of reading


@dataclass
class MotorCommand:
    """Container for motor commands."""

    torques: np.ndarray  # [Nm] for each actuator
    timestamp: float  # [s] time of command


class HardwareInterface(ABC):
    """Abstract base class for hardware interfaces."""

    @abstractmethod
    def initialize(self) -> bool:
        """Initialize hardware connection and sensors.

        Returns:
            bool: True if initialization successful
        """
        pass

    @abstractmethod
    def read_sensors(self) -> SensorData:
        """Read all sensor data.

        Returns:
            SensorData: Current sensor readings
        """
        pass

    @abstractmethod
    def write_motors(self, command: MotorCommand) -> bool:
        """Write motor commands with safety checks.

        Args:
            command: Motor command to execute

        Returns:
            bool: True if command accepted and executed
        """
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """Safely shutdown hardware interface."""
        pass

    @abstractmethod
    def get_joint_names(self) -> List[str]:
        """Get list of joint names in order.

        Returns:
            List[str]: Joint names
        """
        pass

    @abstractmethod
    def get_contact_names(self) -> List[str]:
        """Get list of contact sensor names in order.

        Returns:
            List[str]: Contact sensor names
        """
        pass


class MuJoCoInterface(HardwareInterface):
    """MuJoCo simulation interface for testing."""

    def __init__(
        self,
        model,
        data,
        joint_ids: List[int],
        actuator_ids: List[int],
        contact_geom_ids: List[int],
        joint_names: Optional[List[str]] = None,
        contact_names: Optional[List[str]] = None,
        max_torque: float = 100.0,
        contact_threshold: float = 1.0,
    ):
        """Initialize MuJoCo interface.

        Args:
            model: MuJoCo model object
            data: MuJoCo data object
            joint_ids: List of joint IDs to monitor
            actuator_ids: List of actuator IDs to control
            contact_geom_ids: List of geom IDs for contact detection
            joint_names: Optional joint names (defaults to joint0, joint1, ...)
            contact_names: Optional contact names (defaults to contact0, contact1, ...)
            max_torque: Maximum allowed torque per actuator [Nm]
            contact_threshold: Force threshold for contact detection [N]
        """
        self.model = model
        self.data = data
        self.joint_ids = np.array(joint_ids, dtype=int)
        self.actuator_ids = np.array(actuator_ids, dtype=int)
        self.contact_geom_ids = contact_geom_ids

        self.joint_names_list = joint_names or [
            f"joint{i}" for i in range(len(joint_ids))
        ]
        self.contact_names_list = contact_names or [
            f"contact{i}" for i in range(len(contact_geom_ids))
        ]

        self.max_torque = max_torque
        self.contact_threshold = contact_threshold

        self._initialized = False
        self._start_time = None

    def initialize(self) -> bool:
        """Initialize MuJoCo interface.

        Returns:
            bool: True if successful
        """
        try:
            # Verify indices are valid
            if np.any(self.joint_ids >= self.model.njnt):
                raise ValueError(f"Invalid joint IDs: max is {self.model.njnt-1}")
            if np.any(self.actuator_ids >= self.model.nu):
                raise ValueError(f"Invalid actuator IDs: max is {self.model.nu-1}")

            self._start_time = time.perf_counter()
            self._initialized = True
            return True

        except Exception as e:
            print(f"MuJoCo interface initialization failed: {e}")
            return False

    def read_sensors(self) -> SensorData:
        """Read sensor data from MuJoCo simulation.

        Returns:
            SensorData: Current sensor readings
        """
        if not self._initialized:
            raise RuntimeError("Interface not initialized. Call initialize() first.")

        # Read joint positions and velocities
        joint_angles = self.data.qpos[self.joint_ids].copy()
        joint_velocities = self.data.qvel[self.joint_ids].copy()

        # Detect contacts
        contact_states = self._detect_contacts()

        # Get timestamp
        timestamp = time.perf_counter() - self._start_time

        return SensorData(
            joint_angles=joint_angles,
            joint_velocities=joint_velocities,
            contact_states=contact_states,
            timestamp=timestamp,
        )

    def _detect_contacts(self) -> np.ndarray:
        """Detect contacts from MuJoCo contact buffer.

        Returns:
            np.ndarray: Binary contact states for each sensor
        """
        contact_states = np.zeros(len(self.contact_geom_ids), dtype=int)

        # Check all active contacts in MuJoCo
        for i in range(self.data.ncon):
            contact = self.data.contact[i]

            # Check if either geom in contact pair matches our sensors
            for idx, geom_id in enumerate(self.contact_geom_ids):
                if contact.geom1 == geom_id or contact.geom2 == geom_id:
                    # Calculate contact force magnitude
                    contact_force = np.linalg.norm(contact.frame[:3])
                    if contact_force > self.contact_threshold:
                        contact_states[idx] = 1
                        break

        return contact_states

    def write_motors(self, command: MotorCommand) -> bool:
        """Write motor commands to MuJoCo actuators.

        Args:
            command: Motor command with torques

        Returns:
            bool: True if command accepted
        """
        if not self._initialized:
            raise RuntimeError("Interface not initialized. Call initialize() first.")

        # Validate command size
        if len(command.torques) != len(self.actuator_ids):
            print(
                f"Command size mismatch: got {len(command.torques)}, expected {len(self.actuator_ids)}"
            )
            return False

        # Safety check: clamp torques to max
        clamped_torques = np.clip(command.torques, -self.max_torque, self.max_torque)

        # Check if clamping occurred
        if not np.allclose(command.torques, clamped_torques):
            print(
                f"Warning: Torques clamped from {command.torques} to {clamped_torques}"
            )

        # Write to MuJoCo actuators
        self.data.ctrl[self.actuator_ids] = clamped_torques

        return True

    def shutdown(self) -> None:
        """Shutdown MuJoCo interface."""
        if self._initialized:
            # Zero out all actuators
            self.data.ctrl[self.actuator_ids] = 0.0
            self._initialized = False
            print("MuJoCo interface shutdown complete.")

    def get_joint_names(self) -> List[str]:
        """Get joint names.

        Returns:
            List[str]: Joint names in order
        """
        return self.joint_names_list

    def get_contact_names(self) -> List[str]:
        """Get contact sensor names.

        Returns:
            List[str]: Contact sensor names in order
        """
        return self.contact_names_list

    def get_simulation_time(self) -> float:
        """Get current MuJoCo simulation time.

        Returns:
            float: Simulation time [s]
        """
        return self.data.time


class RealtimeLoop:
    """Utility for maintaining real-time loop timing."""

    def __init__(self, dt: float, tolerance: float = 0.001):
        """Initialize real-time loop.

        Args:
            dt: Target loop period [s]
            tolerance: Timing tolerance [s]
        """
        self.dt = dt
        self.tolerance = tolerance
        self._last_time = None
        self._overruns = 0
        self._total_iterations = 0

    def wait(self) -> float:
        """Wait to maintain target loop rate.

        Returns:
            float: Actual time elapsed since last wait [s]
        """
        current_time = time.perf_counter()

        if self._last_time is None:
            self._last_time = current_time
            return self.dt

        # Calculate elapsed time
        elapsed = current_time - self._last_time

        # Check for timing overrun
        if elapsed > self.dt + self.tolerance:
            self._overruns += 1

        # Sleep for remaining time
        remaining = self.dt - elapsed
        if remaining > 0:
            time.sleep(remaining)

        # Update timing
        actual_elapsed = time.perf_counter() - self._last_time
        self._last_time = time.perf_counter()
        self._total_iterations += 1

        return actual_elapsed

    def get_overrun_rate(self) -> float:
        """Get timing overrun rate.

        Returns:
            float: Fraction of iterations with timing overruns
        """
        if self._total_iterations == 0:
            return 0.0
        return self._overruns / self._total_iterations

    def reset_stats(self) -> None:
        """Reset timing statistics."""
        self._overruns = 0
        self._total_iterations = 0


class SafetyMonitor:
    """Monitor and enforce safety limits."""

    def __init__(
        self,
        joint_limits: Optional[np.ndarray] = None,
        velocity_limits: Optional[np.ndarray] = None,
        torque_limits: Optional[np.ndarray] = None,
    ):
        """Initialize safety monitor.

        Args:
            joint_limits: [n_joints x 2] array of [min, max] joint angles [rad]
            velocity_limits: [n_joints] array of max velocities [rad/s]
            torque_limits: [n_actuators] array of max torques [Nm]
        """
        self.joint_limits = joint_limits
        self.velocity_limits = velocity_limits
        self.torque_limits = torque_limits

        self._violations = []

    def check_state(self, sensor_data: SensorData) -> bool:
        """Check if current state is safe.

        Args:
            sensor_data: Current sensor readings

        Returns:
            bool: True if all checks pass
        """
        safe = True

        # Check joint limits
        if self.joint_limits is not None:
            for i, (angle, limits) in enumerate(
                zip(sensor_data.joint_angles, self.joint_limits)
            ):
                if angle < limits[0] or angle > limits[1]:
                    self._violations.append(
                        f"Joint {i} angle {angle:.3f} outside limits {limits}"
                    )
                    safe = False

        # Check velocity limits
        if self.velocity_limits is not None:
            for i, (vel, limit) in enumerate(
                zip(sensor_data.joint_velocities, self.velocity_limits)
            ):
                if abs(vel) > limit:
                    self._violations.append(
                        f"Joint {i} velocity {vel:.3f} exceeds limit {limit}"
                    )
                    safe = False

        return safe

    def check_command(self, command: MotorCommand) -> bool:
        """Check if motor command is safe.

        Args:
            command: Motor command to check

        Returns:
            bool: True if all checks pass
        """
        safe = True

        # Check torque limits
        if self.torque_limits is not None:
            for i, (torque, limit) in enumerate(
                zip(command.torques, self.torque_limits)
            ):
                if abs(torque) > limit:
                    self._violations.append(
                        f"Actuator {i} torque {torque:.3f} exceeds limit {limit}"
                    )
                    safe = False

        return safe

    def get_violations(self) -> List[str]:
        """Get list of safety violations.

        Returns:
            List[str]: Violation descriptions
        """
        return self._violations.copy()

    def clear_violations(self) -> None:
        """Clear violation history."""
        self._violations.clear()
