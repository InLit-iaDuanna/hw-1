"""
PD Controller with Phase-Dependent Gain Scheduling for hw-1 Gait Assist Device.

Based on V13.7 successful runs with phase-aware torque control.
Motor: Dynamixel MX-64AR (6.0 N·m rated torque)
"""

import numpy as np
from typing import Dict, Optional, Tuple
from enum import Enum


class GaitPhase(Enum):
    """Gait phase enumeration for gain scheduling."""
    STANCE = 0
    SWING = 1
    UNKNOWN = 2


class PDController:
    """
    PD controller with phase-dependent gain scheduling and torque saturation.

    Implements different control gains for stance and swing phases based on
    biomechanical requirements and V13.7 empirical tuning results.
    """

    def __init__(
        self,
        kp_stance: float = 80.0,
        kd_stance: float = 8.0,
        kp_swing: float = 40.0,
        kd_swing: float = 4.0,
        torque_limit: float = 6.0,
        enable_logging: bool = False
    ):
        """
        Initialize PD controller with phase-dependent gains.

        Args:
            kp_stance: Proportional gain during stance phase (N·m/rad)
            kd_stance: Derivative gain during stance phase (N·m·s/rad)
            kp_swing: Proportional gain during swing phase (N·m/rad)
            kd_swing: Derivative gain during swing phase (N·m·s/rad)
            torque_limit: Maximum output torque magnitude (N·m)
            enable_logging: Enable detailed control logging

        Note:
            Default gains from V13.7 successful runs:
            - Stance: Higher gains for weight-bearing stability
            - Swing: Lower gains for compliant leg advancement
        """
        self.kp_stance = kp_stance
        self.kd_stance = kd_stance
        self.kp_swing = kp_swing
        self.kd_swing = kd_swing
        self.torque_limit = torque_limit
        self.enable_logging = enable_logging

        # Logging buffers
        self._log_buffer: list = []
        self._log_counter = 0

    def compute_torque(
        self,
        e_pos: float,
        e_vel: float,
        phase: GaitPhase
    ) -> float:
        """
        Compute control torque based on position/velocity error and gait phase.

        Args:
            e_pos: Position error (rad) = theta_desired - theta_actual
            e_vel: Velocity error (rad/s) = omega_desired - omega_actual
            phase: Current gait phase for gain scheduling

        Returns:
            Saturated control torque (N·m)

        Note:
            Torque is saturated to motor limits (±6.0 N·m for MX-64AR)
        """
        # Select gains based on phase
        if phase == GaitPhase.STANCE:
            kp = self.kp_stance
            kd = self.kd_stance
        elif phase == GaitPhase.SWING:
            kp = self.kp_swing
            kd = self.kd_swing
        else:
            # Fallback to swing gains for unknown phase (safer/more compliant)
            kp = self.kp_swing
            kd = self.kd_swing

        # Compute raw PD torque
        tau_raw = kp * e_pos + kd * e_vel

        # Apply torque saturation
        tau_saturated = np.clip(tau_raw, -self.torque_limit, self.torque_limit)

        # Log if enabled
        if self.enable_logging:
            self._log_step(e_pos, e_vel, phase, kp, kd, tau_raw, tau_saturated)

        return tau_saturated

    def compute_torque_bilateral(
        self,
        e_pos_left: float,
        e_vel_left: float,
        phase_left: GaitPhase,
        e_pos_right: float,
        e_vel_right: float,
        phase_right: GaitPhase
    ) -> Tuple[float, float]:
        """
        Compute bilateral control torques for left and right actuators.

        Args:
            e_pos_left: Left hip position error (rad)
            e_vel_left: Left hip velocity error (rad/s)
            phase_left: Left leg gait phase
            e_pos_right: Right hip position error (rad)
            e_vel_right: Right hip velocity error (rad/s)
            phase_right: Right leg gait phase

        Returns:
            (tau_left, tau_right): Control torques for left and right hips (N·m)
        """
        tau_left = self.compute_torque(e_pos_left, e_vel_left, phase_left)
        tau_right = self.compute_torque(e_pos_right, e_vel_right, phase_right)

        return tau_left, tau_right

    def update_gains(
        self,
        kp_stance: Optional[float] = None,
        kd_stance: Optional[float] = None,
        kp_swing: Optional[float] = None,
        kd_swing: Optional[float] = None
    ) -> None:
        """
        Update controller gains for online tuning.

        Args:
            kp_stance: New stance proportional gain (N·m/rad)
            kd_stance: New stance derivative gain (N·m·s/rad)
            kp_swing: New swing proportional gain (N·m/rad)
            kd_swing: New swing derivative gain (N·m·s/rad)
        """
        if kp_stance is not None:
            self.kp_stance = kp_stance
        if kd_stance is not None:
            self.kd_stance = kd_stance
        if kp_swing is not None:
            self.kp_swing = kp_swing
        if kd_swing is not None:
            self.kd_swing = kd_swing

    def get_gains(self, phase: GaitPhase) -> Dict[str, float]:
        """
        Get current gains for specified phase.

        Args:
            phase: Gait phase to query

        Returns:
            Dictionary with 'kp' and 'kd' keys
        """
        if phase == GaitPhase.STANCE:
            return {'kp': self.kp_stance, 'kd': self.kd_stance}
        elif phase == GaitPhase.SWING:
            return {'kp': self.kp_swing, 'kd': self.kd_swing}
        else:
            return {'kp': self.kp_swing, 'kd': self.kd_swing}

    def set_torque_limit(self, limit: float) -> None:
        """
        Update torque saturation limit.

        Args:
            limit: New torque limit (N·m), must be positive
        """
        if limit <= 0:
            raise ValueError(f"Torque limit must be positive, got {limit}")
        self.torque_limit = limit

    def _log_step(
        self,
        e_pos: float,
        e_vel: float,
        phase: GaitPhase,
        kp: float,
        kd: float,
        tau_raw: float,
        tau_sat: float
    ) -> None:
        """Internal logging method."""
        log_entry = {
            'step': self._log_counter,
            'e_pos': e_pos,
            'e_vel': e_vel,
            'phase': phase.name,
            'kp': kp,
            'kd': kd,
            'tau_raw': tau_raw,
            'tau_saturated': tau_sat,
            'saturation_active': abs(tau_raw) > self.torque_limit
        }
        self._log_buffer.append(log_entry)
        self._log_counter += 1

    def get_logs(self) -> list:
        """
        Retrieve logged control data.

        Returns:
            List of log entries (dicts)
        """
        return self._log_buffer.copy()

    def clear_logs(self) -> None:
        """Clear logged control data."""
        self._log_buffer.clear()
        self._log_counter = 0

    def get_saturation_ratio(self) -> float:
        """
        Calculate fraction of control steps with active torque saturation.

        Returns:
            Saturation ratio [0, 1], or 0.0 if no logs available
        """
        if not self._log_buffer:
            return 0.0
        saturated_count = sum(1 for log in self._log_buffer if log['saturation_active'])
        return saturated_count / len(self._log_buffer)


# V13.7 Default Gain Presets
GAINS_V13_CONSERVATIVE = {
    'kp_stance': 60.0,
    'kd_stance': 6.0,
    'kp_swing': 30.0,
    'kd_swing': 3.0,
}

GAINS_V13_NOMINAL = {
    'kp_stance': 80.0,
    'kd_stance': 8.0,
    'kp_swing': 40.0,
    'kd_swing': 4.0,
}

GAINS_V13_AGGRESSIVE = {
    'kp_stance': 100.0,
    'kd_stance': 10.0,
    'kp_swing': 50.0,
    'kd_swing': 5.0,
}


def create_controller(preset: str = 'nominal', **kwargs) -> PDController:
    """
    Factory function for creating PD controller with preset gains.

    Args:
        preset: Gain preset ('conservative', 'nominal', 'aggressive')
        **kwargs: Override parameters passed to PDController constructor

    Returns:
        Configured PDController instance

    Example:
        >>> controller = create_controller('nominal', torque_limit=5.0)
        >>> tau = controller.compute_torque(0.1, 0.05, GaitPhase.STANCE)
    """
    preset_map = {
        'conservative': GAINS_V13_CONSERVATIVE,
        'nominal': GAINS_V13_NOMINAL,
        'aggressive': GAINS_V13_AGGRESSIVE,
    }

    if preset not in preset_map:
        raise ValueError(f"Unknown preset '{preset}'. Choose from {list(preset_map.keys())}")

    gains = preset_map[preset].copy()
    gains.update(kwargs)

    return PDController(**gains)
