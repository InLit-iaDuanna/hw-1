"""
State Estimator Module - Kalman Filter for Sensor Fusion
Hardware-ready implementation for hw-1 gait rehabilitation device

Specifications from V17:
- Encoder: 4096 CPR (counts per revolution)
- Contact sensor delay: max 15ms
- Target: smooth velocity estimates for PD control
"""

import numpy as np
from typing import Tuple, Optional
from dataclasses import dataclass


@dataclass
class KalmanConfig:
    """Configuration for Kalman filter parameters."""

    # Process noise covariance (from V17 tuning)
    process_noise_position: float = 1e-8  # rad^2
    process_noise_velocity: float = 1e-4  # (rad/s)^2

    # Measurement noise (encoder quantization + sensor noise)
    measurement_noise_encoder: float = (2 * np.pi / 4096) ** 2  # quantization noise
    measurement_noise_velocity: float = 1e-2  # (rad/s)^2

    # Contact detection parameters
    contact_force_threshold: float = 5.0  # N, from V17
    contact_delay_compensation: float = 0.015  # 15ms max delay
    contact_debounce_samples: int = 3  # require N consecutive samples


class KalmanFilter:
    """
    Kalman filter for joint angle and velocity estimation.

    State vector: [angle, angular_velocity]
    Measurement: [encoder_angle] or [encoder_angle, derivative_velocity]
    """

    def __init__(self, config: KalmanConfig, dt: float = 0.001):
        """
        Initialize Kalman filter.

        Args:
            config: Kalman filter configuration
            dt: Sampling time (default 1ms = 1kHz control)
        """
        self.config = config
        self.dt = dt

        # State: [angle, velocity]
        self.x = np.zeros(2)  # state estimate
        self.P = np.eye(2) * 0.1  # state covariance

        # State transition matrix (constant velocity model)
        self.F = np.array([[1.0, dt], [0.0, 1.0]])

        # Process noise covariance
        self.Q = np.array(
            [[config.process_noise_position, 0.0], [0.0, config.process_noise_velocity]]
        )

        # Measurement matrix (observe angle only)
        self.H = np.array([[1.0, 0.0]])

        # Measurement noise covariance
        self.R = np.array([[config.measurement_noise_encoder]])

        # Identity matrix
        self.I = np.eye(2)

    def predict(self) -> np.ndarray:
        """
        Prediction step: propagate state forward in time.

        Returns:
            Predicted state [angle, velocity]
        """
        # State prediction
        self.x = self.F @ self.x

        # Covariance prediction
        self.P = self.F @ self.P @ self.F.T + self.Q

        return self.x.copy()

    def update(self, measurement: float) -> np.ndarray:
        """
        Update step: correct state with encoder measurement.

        Args:
            measurement: Encoder angle (radians)

        Returns:
            Updated state [angle, velocity]
        """
        # Innovation (measurement residual)
        z = np.array([measurement])
        y = z - self.H @ self.x

        # Innovation covariance
        S = self.H @ self.P @ self.H.T + self.R

        # Kalman gain
        K = self.P @ self.H.T @ np.linalg.inv(S)

        # State update
        self.x = self.x + K @ y

        # Covariance update (Joseph form for numerical stability)
        I_KH = self.I - K @ self.H
        self.P = I_KH @ self.P @ I_KH.T + K @ self.R @ K.T

        return self.x.copy()

    def step(self, measurement: float) -> Tuple[float, float]:
        """
        Complete filter step: predict + update.

        Args:
            measurement: Encoder angle (radians)

        Returns:
            (filtered_angle, filtered_velocity)
        """
        self.predict()
        state = self.update(measurement)
        return state[0], state[1]

    def get_state(self) -> Tuple[float, float]:
        """Get current state estimate."""
        return self.x[0], self.x[1]

    def reset(self, angle: float = 0.0, velocity: float = 0.0):
        """Reset filter state."""
        self.x = np.array([angle, velocity])
        self.P = np.eye(2) * 0.1


class JointStateEstimator:
    """
    Multi-joint state estimator with Kalman filtering.
    Manages filters for hip, knee, and ankle joints.
    """

    def __init__(self, config: Optional[KalmanConfig] = None, dt: float = 0.001):
        """
        Initialize joint state estimator.

        Args:
            config: Kalman filter configuration (uses default if None)
            dt: Sampling time (seconds)
        """
        if config is None:
            config = KalmanConfig()

        self.config = config
        self.dt = dt

        # Create Kalman filters for each joint
        self.filters = {
            "hip": KalmanFilter(config, dt),
            "knee": KalmanFilter(config, dt),
            "ankle": KalmanFilter(config, dt),
        }

        # Contact state tracking
        self.contact_state = False
        self.contact_history = []  # for debouncing

        # Timestamp tracking for delay compensation
        self.last_update_time = 0.0

    def update_joint(
        self, joint_name: str, encoder_angle: float
    ) -> Tuple[float, float]:
        """
        Update state estimate for a single joint.

        Args:
            joint_name: 'hip', 'knee', or 'ankle'
            encoder_angle: Raw encoder reading (radians)

        Returns:
            (filtered_angle, filtered_velocity)
        """
        if joint_name not in self.filters:
            raise ValueError(f"Unknown joint: {joint_name}")

        return self.filters[joint_name].step(encoder_angle)

    def update_all_joints(
        self, hip_angle: float, knee_angle: float, ankle_angle: float
    ) -> dict:
        """
        Update all joint state estimates.

        Args:
            hip_angle: Hip encoder reading (radians)
            knee_angle: Knee encoder reading (radians)
            ankle_angle: Ankle encoder reading (radians)

        Returns:
            Dictionary with filtered states for all joints
        """
        states = {}
        states["hip"] = self.update_joint("hip", hip_angle)
        states["knee"] = self.update_joint("knee", knee_angle)
        states["ankle"] = self.update_joint("ankle", ankle_angle)

        return states

    def get_all_states(self) -> dict:
        """Get current state estimates for all joints."""
        return {name: filt.get_state() for name, filt in self.filters.items()}

    def reset_all(self):
        """Reset all joint filters."""
        for filt in self.filters.values():
            filt.reset()
        self.contact_state = False
        self.contact_history.clear()


class ForwardKinematics:
    """
    Forward kinematics for hip position estimation.
    Simplified 2D sagittal plane model.
    """

    def __init__(self, thigh_length: float = 0.4, shank_length: float = 0.4):
        """
        Initialize forward kinematics.

        Args:
            thigh_length: Thigh segment length (meters)
            shank_length: Shank segment length (meters)
        """
        self.L_thigh = thigh_length
        self.L_shank = shank_length

    def compute_hip_position(
        self, hip_angle: float, knee_angle: float, ankle_angle: float
    ) -> Tuple[float, float]:
        """
        Compute hip position in world frame (ankle as origin).

        Args:
            hip_angle: Hip joint angle (radians, positive = flexion)
            knee_angle: Knee joint angle (radians, positive = flexion)
            ankle_angle: Ankle joint angle (radians, positive = dorsiflexion)

        Returns:
            (x_hip, y_hip) position in meters (sagittal plane)
        """
        # Ankle to knee vector (shank)
        theta_shank = ankle_angle  # shank orientation
        x_knee = self.L_shank * np.sin(theta_shank)
        y_knee = self.L_shank * np.cos(theta_shank)

        # Knee to hip vector (thigh)
        theta_thigh = theta_shank + knee_angle  # thigh orientation
        x_hip = x_knee + self.L_thigh * np.sin(theta_thigh)
        y_hip = y_knee + self.L_thigh * np.cos(theta_thigh)

        return x_hip, y_hip

    def compute_hip_velocity(
        self,
        hip_angle: float,
        knee_angle: float,
        ankle_angle: float,
        hip_vel: float,
        knee_vel: float,
        ankle_vel: float,
    ) -> Tuple[float, float]:
        """
        Compute hip velocity using Jacobian.

        Args:
            hip_angle, knee_angle, ankle_angle: Joint angles (radians)
            hip_vel, knee_vel, ankle_vel: Joint velocities (rad/s)

        Returns:
            (vx_hip, vy_hip) velocity in m/s
        """
        # Jacobian computation
        theta_shank = ankle_angle
        theta_thigh = ankle_angle + knee_angle

        # Partial derivatives
        dx_dankle = self.L_shank * np.cos(theta_shank) + self.L_thigh * np.cos(
            theta_thigh
        )
        dy_dankle = -self.L_shank * np.sin(theta_shank) - self.L_thigh * np.sin(
            theta_thigh
        )

        dx_dknee = self.L_thigh * np.cos(theta_thigh)
        dy_dknee = -self.L_thigh * np.sin(theta_thigh)

        # Hip joint doesn't affect hip position in this kinematic chain

        # Velocity mapping
        vx_hip = dx_dankle * ankle_vel + dx_dknee * knee_vel
        vy_hip = dy_dankle * ankle_vel + dy_dknee * knee_vel

        return vx_hip, vy_hip


class ContactDetector:
    """
    Ground contact detection with delay compensation and debouncing.
    """

    def __init__(self, config: Optional[KalmanConfig] = None, dt: float = 0.001):
        """
        Initialize contact detector.

        Args:
            config: Configuration with contact parameters
            dt: Sampling time (seconds)
        """
        if config is None:
            config = KalmanConfig()

        self.config = config
        self.dt = dt

        # Contact state
        self.contact_state = False
        self.contact_history = []

        # Delay compensation buffer
        self.force_buffer = []
        self.max_buffer_size = int(config.contact_delay_compensation / dt)

    def update(self, ground_force: float, current_time: float) -> bool:
        """
        Update contact state with force measurement.

        Args:
            ground_force: Ground reaction force (N)
            current_time: Current timestamp (seconds)

        Returns:
            True if in contact, False otherwise
        """
        # Add to delay compensation buffer
        self.force_buffer.append((current_time, ground_force))
        if len(self.force_buffer) > self.max_buffer_size:
            self.force_buffer.pop(0)

        # Threshold detection
        contact_detected = ground_force > self.config.contact_force_threshold

        # Debouncing
        self.contact_history.append(contact_detected)
        if len(self.contact_history) > self.config.contact_debounce_samples:
            self.contact_history.pop(0)

        # Require consecutive detections
        if len(self.contact_history) >= self.config.contact_debounce_samples:
            self.contact_state = all(self.contact_history)

        return self.contact_state

    def get_compensated_contact_time(self) -> Optional[float]:
        """
        Get contact time with delay compensation.

        Returns:
            Timestamp of actual contact (compensated), or None if no contact
        """
        if not self.contact_state or not self.force_buffer:
            return None

        # Find first time force exceeded threshold in buffer
        for timestamp, force in self.force_buffer:
            if force > self.config.contact_force_threshold:
                return timestamp

        return None

    def reset(self):
        """Reset contact detector."""
        self.contact_state = False
        self.contact_history.clear()
        self.force_buffer.clear()


class StateEstimator:
    """
    Complete state estimator combining Kalman filtering, kinematics, and contact detection.
    """

    def __init__(
        self,
        config: Optional[KalmanConfig] = None,
        dt: float = 0.001,
        thigh_length: float = 0.4,
        shank_length: float = 0.4,
    ):
        """
        Initialize complete state estimator.

        Args:
            config: Kalman filter configuration
            dt: Sampling time (seconds)
            thigh_length: Thigh segment length (meters)
            shank_length: Shank segment length (meters)
        """
        self.joint_estimator = JointStateEstimator(config, dt)
        self.kinematics = ForwardKinematics(thigh_length, shank_length)
        self.contact_detector = ContactDetector(config, dt)

        self.dt = dt
        self.current_time = 0.0

    def update(
        self,
        hip_angle: float,
        knee_angle: float,
        ankle_angle: float,
        ground_force: float,
    ) -> dict:
        """
        Complete state update with all sensors.

        Args:
            hip_angle: Hip encoder reading (radians)
            knee_angle: Knee encoder reading (radians)
            ankle_angle: Ankle encoder reading (radians)
            ground_force: Ground reaction force (N)

        Returns:
            Dictionary with complete state information
        """
        # Update joint states
        joint_states = self.joint_estimator.update_all_joints(
            hip_angle, knee_angle, ankle_angle
        )

        # Extract filtered values
        hip_pos, hip_vel = joint_states["hip"]
        knee_pos, knee_vel = joint_states["knee"]
        ankle_pos, ankle_vel = joint_states["ankle"]

        # Compute hip position
        hip_x, hip_y = self.kinematics.compute_hip_position(
            hip_pos, knee_pos, ankle_pos
        )

        # Compute hip velocity
        hip_vx, hip_vy = self.kinematics.compute_hip_velocity(
            hip_pos, knee_pos, ankle_pos, hip_vel, knee_vel, ankle_vel
        )

        # Update contact state
        contact = self.contact_detector.update(ground_force, self.current_time)
        contact_time = self.contact_detector.get_compensated_contact_time()

        # Increment time
        self.current_time += self.dt

        return {
            "joints": {
                "hip": {"angle": hip_pos, "velocity": hip_vel},
                "knee": {"angle": knee_pos, "velocity": knee_vel},
                "ankle": {"angle": ankle_pos, "velocity": ankle_vel},
            },
            "hip_position": {"x": hip_x, "y": hip_y},
            "hip_velocity": {"x": hip_vx, "y": hip_vy},
            "contact": {"state": contact, "force": ground_force, "time": contact_time},
            "timestamp": self.current_time,
        }

    def reset(self):
        """Reset all estimators."""
        self.joint_estimator.reset_all()
        self.contact_detector.reset()
        self.current_time = 0.0


# Utility functions


def encoder_counts_to_radians(counts: int, cpr: int = 4096) -> float:
    """
    Convert encoder counts to radians.

    Args:
        counts: Encoder counts
        cpr: Counts per revolution (default 4096 from V17)

    Returns:
        Angle in radians
    """
    return (counts / cpr) * 2 * np.pi


def estimate_velocity_finite_diff(
    angle_curr: float, angle_prev: float, dt: float
) -> float:
    """
    Simple finite difference velocity estimate (noisy, use Kalman filter instead).

    Args:
        angle_curr: Current angle (radians)
        angle_prev: Previous angle (radians)
        dt: Time step (seconds)

    Returns:
        Angular velocity (rad/s)
    """
    return (angle_curr - angle_prev) / dt
