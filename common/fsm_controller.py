"""FSM-based gait controller unified API.

Implements phase-driven finite state machine control based on v13.6 event-driven FSM
and v13.7 friction compensation implementations.

Usage:
    # From v13.6
    fsm = FSMController.from_v136(v136_params, base_params)
    tau = fsm.compute_control(data, t, support_foot, burst_start_t, E_current)

    # From v13.7
    fsm = FSMController.from_v137(v137_params, data)
    tau = fsm.compute_control(data, t, support_foot, burst_start_t, E_current)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

import mujoco
import numpy as np


G = 9.81


@dataclass(frozen=True)
class PhaseParams:
    """Per-phase control parameters for FSM gait controller.

    Each phase has independent gains for:
    - k_E: energy shaping gain (0 = PD-only, >0 = energy-based bang-bang)
    - k_PD: proportional gain for position tracking
    - tau_max: torque saturation limit
    - kd: derivative (damping) gain
    - E_target: target mechanical energy (used only when k_E > 0)
    """
    k_E: float
    k_PD: float
    tau_max: float
    kd: float = 6.0
    E_target: float = 52.66  # J, from V13b limit cycle measurement


@dataclass(frozen=True)
class FSMParams:
    """Complete FSM controller parameters for 4-phase gait control.

    Phases:
      - stance_early: 0-50% of support phase (strong PD tracking)
      - stance_late: 50-100% of support phase (push-off preparation)
      - swing_thrust: 0-50% of swing phase (energy injection)
      - swing_retract: 50-100% of swing phase (passive return)
    """
    stance_early: PhaseParams = field(
        default_factory=lambda: PhaseParams(k_E=0.0, k_PD=30.0, tau_max=4.0, kd=6.0)
    )
    stance_late: PhaseParams = field(
        default_factory=lambda: PhaseParams(k_E=0.0, k_PD=30.0, tau_max=4.0, kd=6.0)
    )
    swing_thrust: PhaseParams = field(
        default_factory=lambda: PhaseParams(
            k_E=7.5, k_PD=10.0, tau_max=4.0, kd=6.0, E_target=52.66
        )
    )
    swing_retract: PhaseParams = field(
        default_factory=lambda: PhaseParams(k_E=0.0, k_PD=30.0, tau_max=2.0, kd=6.0)
    )


@dataclass(frozen=True)
class BaseGaitParams:
    """Base gait parameters needed for FSM controller."""
    gait_period: float = 0.80
    gamma: float = 0.0  # hip angle offset
    stance_front_deg: float = 0.0
    stance_back_deg: float = 0.0
    swing_back_deg: float = 0.0
    swing_front_deg: float = 0.0
    recovery_clearance: float = 0.38
    slope_deg: float = 0.0
    hip_mass: float = 1.0
    torso_mass: float = 0.05


def smoothstep(u: float) -> float:
    """Smooth interpolation function: s(u) = 3u² - 2u³."""
    u = max(0.0, min(1.0, u))
    return u * u * (3.0 - 2.0 * u)


def ramp_height(x: float, params: BaseGaitParams) -> float:
    """Ground height at position x for sloped terrain."""
    return x * math.tan(math.radians(params.slope_deg))


class FSMController:
    """Finite state machine gait controller.

    Implements 4-phase FSM control with per-phase gains and energy shaping.
    Based on v13.6 event-driven FSM and v13.7 friction compensation.
    """

    def __init__(
        self,
        fsm_params: FSMParams,
        base_params: BaseGaitParams,
        knee_kp: float = 16.0,
        knee_kd: float = 2.0,
        knee_torque_limit: float = 4.0,
        swing_knee_flex_deg: float = 30.0,
        stance_knee_deg: float = 0.0,
    ):
        """Initialize FSM controller.

        Args:
            fsm_params: Per-phase FSM control parameters
            base_params: Base gait parameters (timing, targets, terrain)
            knee_kp: Knee PD proportional gain
            knee_kd: Knee PD derivative gain
            knee_torque_limit: Knee torque saturation limit
            swing_knee_flex_deg: Peak knee flexion during swing (deg)
            stance_knee_deg: Knee angle during stance (deg)
        """
        self.fsm = fsm_params
        self.base = base_params
        self.knee_kp = knee_kp
        self.knee_kd = knee_kd
        self.knee_torque_limit = knee_torque_limit
        self.swing_knee_flex_deg = swing_knee_flex_deg
        self.stance_knee_deg = stance_knee_deg

        self._phase_map = {
            "stance_early": fsm_params.stance_early,
            "stance_late": fsm_params.stance_late,
            "swing_thrust": fsm_params.swing_thrust,
            "swing_retract": fsm_params.swing_retract,
        }

    @classmethod
    def from_v136(cls, v136_params, v10_base_params) -> FSMController:
        """Factory method: create FSMController from V13.6 parameters.

        Args:
            v136_params: V136Params object from simulate_v13_6.py
            v10_base_params: RollingFootParams (V10Params) base configuration

        Returns:
            FSMController instance
        """
        fsm = FSMParams(
            stance_early=v136_params.stance_early,
            stance_late=v136_params.stance_late,
            swing_thrust=v136_params.swing_thrust,
            swing_retract=v136_params.swing_retract,
        )

        base = BaseGaitParams(
            gait_period=v10_base_params.gait_period,
            gamma=v10_base_params.gamma,
            stance_front_deg=v10_base_params.stance_front_deg,
            stance_back_deg=v10_base_params.stance_back_deg,
            swing_back_deg=v10_base_params.swing_back_deg,
            swing_front_deg=v10_base_params.swing_front_deg,
            recovery_clearance=v10_base_params.recovery_clearance,
            slope_deg=v10_base_params.slope_deg,
            hip_mass=v10_base_params.hip_mass,
            torso_mass=v10_base_params.torso_mass,
        )

        return cls(
            fsm_params=fsm,
            base_params=base,
            knee_kp=v10_base_params.knee_kp,
            knee_kd=v10_base_params.knee_kd,
            knee_torque_limit=v10_base_params.knee_torque_limit,
            swing_knee_flex_deg=v10_base_params.swing_knee_flex_deg,
            stance_knee_deg=v10_base_params.stance_knee_deg,
        )

    @classmethod
    def from_v137(cls, v137_params) -> FSMController:
        """Factory method: create FSMController from V13.7 parameters.

        Args:
            v137_params: V137Params object from simulate_v13_7.py

        Returns:
            FSMController instance
        """
        fsm = v137_params.fsm
        base_v14 = v137_params.base

        fsm_params = FSMParams(
            stance_early=fsm.stance_early,
            stance_late=fsm.stance_late,
            swing_thrust=fsm.swing_thrust,
            swing_retract=fsm.swing_retract,
        )

        base = BaseGaitParams(
            gait_period=base_v14.gait_period,
            gamma=base_v14.gamma,
            stance_front_deg=base_v14.stance_front_deg,
            stance_back_deg=base_v14.stance_back_deg,
            swing_back_deg=base_v14.swing_back_deg,
            swing_front_deg=base_v14.swing_front_deg,
            recovery_clearance=base_v14.recovery_clearance,
            slope_deg=base_v14.slope_deg,
            hip_mass=base_v14.hip_mass,
            torso_mass=base_v14.torso_mass,
        )

        return cls(
            fsm_params=fsm_params,
            base_params=base,
            knee_kp=base_v14.knee_kp,
            knee_kd=base_v14.knee_kd,
            knee_torque_limit=base_v14.knee_torque_limit,
            swing_knee_flex_deg=base_v14.swing_knee_flex_deg,
            stance_knee_deg=base_v14.stance_knee_deg,
        )

    def _effective_mass(self) -> float:
        """Effective mass for energy calculation (hip + 2*torso)."""
        return self.base.hip_mass + 2.0 * self.base.torso_mass

    def mechanical_energy(self, data: mujoco.MjData) -> float:
        """Calculate total mechanical energy (kinetic + potential).

        Args:
            data: MuJoCo data structure

        Returns:
            Total mechanical energy in Joules
        """
        m = self._effective_mass()
        vx = float(data.qvel[0])
        vz = float(data.qvel[1])
        z = float(data.qpos[1])
        return 0.5 * m * (vx * vx + vz * vz) + m * G * z

    def _leg_phase(
        self, is_support: bool, u: float, clearance: float
    ) -> str:
        """Determine current phase for a leg.

        Args:
            is_support: True if leg is in stance, False if swing
            u: Phase variable in [0, 1] (0=contact, 1=next contact)
            clearance: Hip height above ground

        Returns:
            Phase name: "stance_early", "stance_late", "swing_thrust", or "swing_retract"
        """
        if is_support:
            # Safety: if hip drops too low, revert to conservative early stance
            if clearance < self.base.recovery_clearance:
                return "stance_early"
            return "stance_early" if u < 0.5 else "stance_late"
        # Swing phase
        return "swing_thrust" if u < 0.5 else "swing_retract"

    def _phase_torque(
        self,
        pp: PhaseParams,
        q: float,
        qd: float,
        target: float,
        u: float,
        E_current: float,
    ) -> tuple[float, float, float]:
        """Compute torque for a single phase.

        Args:
            pp: Phase parameters
            q: Current joint angle
            qd: Current joint velocity
            target: Target angle from smoothstep trajectory
            u: Phase variable in [0, 1]
            E_current: Current mechanical energy

        Returns:
            (torque, energy_error, energy_drive_amplitude)
        """
        e_q = target - q
        pd = pp.k_PD * e_q - pp.kd * qd

        # PD-only phase
        if pp.k_E <= 0.0:
            tau = float(np.clip(pd, -pp.tau_max, pp.tau_max))
            return tau, 0.0, 0.0

        # Energy shaping phase
        e_E = pp.E_target - E_current
        drive = max(0.0, e_E)
        A_energy = float(np.clip(pp.k_E * drive, 0.0, pp.tau_max))
        sgn = 1.0 if e_q > 1e-4 else (-1.0 if e_q < -1e-4 else 0.0)

        # Smooth PD blending at end of phase (u > 0.85)
        alpha = smoothstep(max(0.0, (u - 0.85) / 0.15))
        tau = float(np.clip(A_energy * sgn + alpha * pd, -pp.tau_max, pp.tau_max))
        return tau, float(e_E), A_energy

    def _limited_pd(
        self, q: float, qd: float, target: float, kp: float, kd: float, limit: float
    ) -> float:
        """PD controller with torque limiting."""
        tau = kp * (target - q) - kd * qd
        return float(np.clip(tau, -limit, limit))

    def compute_control(
        self,
        data: mujoco.MjData,
        t: float,
        support_foot: str,
        burst_start_t: float,
        E_current: Optional[float] = None,
    ) -> tuple[float, float, float, float, str, str, str, float, float]:
        """Compute FSM control outputs for all joints.

        Args:
            data: MuJoCo data structure
            t: Current simulation time
            support_foot: "left" or "right"
            burst_start_t: Time of last contact event
            E_current: Current mechanical energy (computed if None)

        Returns:
            Tuple of (l_hip_tau, l_knee_tau, r_hip_tau, r_knee_tau,
                     mode_label, left_phase, right_phase, e_E_swing, A_swing)
        """
        if E_current is None:
            E_current = self.mechanical_energy(data)

        # Compute phase variable u ∈ [0, 1]
        hip_x = float(data.qpos[0])
        hip_z = float(data.qpos[1])
        clearance = hip_z - ramp_height(hip_x, self.base)
        u = min(
            max((t - burst_start_t) / max(self.base.gait_period, 1e-6), 0.0), 1.0
        )

        # Safety: compress phase if hip drops too low
        if clearance < self.base.recovery_clearance:
            u = min(u, 0.55)

        s = smoothstep(u)
        offset = self.base.gamma

        # V10-style continuous target trajectories (no phase-switch jumps)
        stance_target = offset + math.radians(
            self.base.stance_front_deg
            + (self.base.stance_back_deg - self.base.stance_front_deg) * s
        )
        swing_target = offset + math.radians(
            self.base.swing_back_deg
            + (self.base.swing_front_deg - self.base.swing_back_deg) * s
        )

        # Determine phase for each leg
        left_is_support = support_foot == "left"
        left_phase = self._leg_phase(left_is_support, u, clearance)
        right_phase = self._leg_phase(not left_is_support, u, clearance)

        # Hip control
        l_target = stance_target if left_is_support else swing_target
        r_target = stance_target if not left_is_support else swing_target

        l_hip_tau, l_eE, l_A = self._phase_torque(
            self._phase_map[left_phase],
            float(data.qpos[2]),
            float(data.qvel[2]),
            l_target,
            u,
            E_current,
        )
        r_hip_tau, r_eE, r_A = self._phase_torque(
            self._phase_map[right_phase],
            float(data.qpos[5]),
            float(data.qvel[5]),
            r_target,
            u,
            E_current,
        )

        # Knee control (V10-style PD)
        swing_knee = math.radians(self.swing_knee_flex_deg * math.sin(math.pi * u))
        stance_knee = math.radians(self.stance_knee_deg)
        left_knee_target = stance_knee if left_is_support else swing_knee
        right_knee_target = stance_knee if not left_is_support else swing_knee

        l_knee_tau = self._limited_pd(
            float(data.qpos[3]),
            float(data.qvel[3]),
            left_knee_target,
            self.knee_kp,
            self.knee_kd,
            self.knee_torque_limit,
        )
        r_knee_tau = self._limited_pd(
            float(data.qpos[6]),
            float(data.qvel[6]),
            right_knee_target,
            self.knee_kp,
            self.knee_kd,
            self.knee_torque_limit,
        )

        # Diagnostic: energy error from swing thrust phase
        if left_phase == "swing_thrust":
            eE_diag, A_diag = l_eE, l_A
        elif right_phase == "swing_thrust":
            eE_diag, A_diag = r_eE, r_A
        else:
            eE_diag, A_diag = 0.0, 0.0

        mode_label = f"{'L' if left_is_support else 'R'}:{left_phase}|{right_phase}"

        return (
            l_hip_tau,
            l_knee_tau,
            r_hip_tau,
            r_knee_tau,
            mode_label,
            left_phase,
            right_phase,
            eE_diag,
            A_diag,
        )
