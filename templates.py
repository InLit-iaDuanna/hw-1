"""Predefined configuration templates for hw-1 gait models.

This module provides preset configurations for different versions of the gait simulation:
- v05_passive: Hybrid compass gait with passive dynamics
- v10_rolling: Rolling foot biomimetic gait with PD control
- v137_fsm: Event-driven FSM with phase-based control (V13.6)
- biomimetic: Stable biomimetic gait (V09)

Each preset includes tuned parameters validated through extensive simulation testing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any


# =============================================================================
# V05 Passive Hybrid Compass Configuration
# =============================================================================
@dataclass(frozen=True)
class V05PassiveConfig:
    """V05 hybrid compass proof - passive-dominant walker on slope.

    Key characteristics:
    - Minimal actuation, relies on gravity and collision dynamics
    - Fixed point speed determined by energy balance
    - Suited for understanding fundamental gait mechanics
    """
    slope_deg: float = 5.0
    leg_length: float = 1.0
    foot_radius: float = 0.035
    step_angle_deg: float = 10.0
    gravity: float = 9.81
    stance_damping: float = 0.012
    swing_damping: float = 0.035
    passive_hip_stiffness: float = 0.42
    collision_retention: float = 0.82
    energy_gain_scale: float = 0.42
    initial_speed: float = 0.28
    initial_error: float = 0.34
    steps: int = 18
    dt: float = 0.002
    samples_per_step: int = 80

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'slope_deg': self.slope_deg,
            'leg_length': self.leg_length,
            'foot_radius': self.foot_radius,
            'step_angle_deg': self.step_angle_deg,
            'gravity': self.gravity,
            'stance_damping': self.stance_damping,
            'swing_damping': self.swing_damping,
            'passive_hip_stiffness': self.passive_hip_stiffness,
            'collision_retention': self.collision_retention,
            'energy_gain_scale': self.energy_gain_scale,
            'initial_speed': self.initial_speed,
            'initial_error': self.initial_error,
            'steps': self.steps,
            'dt': self.dt,
            'samples_per_step': self.samples_per_step
        }


# =============================================================================
# V10 Rolling Foot Biomimetic Configuration
# =============================================================================
@dataclass(frozen=True)
class V10RollingConfig:
    """V10 rolling foot biomimetic gait - full featured walker with rolling foot.

    Key characteristics:
    - Curved foot geometry for natural rolling motion
    - PD control with phase-dependent targets
    - Ankle compliance for terrain adaptation
    - Validated for robustness and energy efficiency
    """
    slope_deg: float = 0.0
    foot_radius: float = 0.04
    foot_length: float = 0.16
    toe_radius: float = 0.028
    ankle_limit_deg: float = 25.0
    ankle_damping: float = 0.08
    ankle_stiffness: float = 0.55
    friction: float = 1.35
    hip_mass: float = 5.0
    torso_mass: float = 0.2
    torso_height: float = 0.30
    initial_vx: float = 0.04
    knee_limit_deg: float = 70.0
    duration: float = 12.0
    timestep: float = 0.001
    thigh_length: float = 0.48
    shank_length: float = 0.52
    step_length: float = 0.34
    knee_damping: float = 0.08
    knee_stiffness: float = 0.8
    hip_joint_damping: float = 0.02
    joint_damping: float = 0.01
    release_phase: float = 0.08
    swing_foot_x: float = 0.38
    swing_foot_clearance: float = 0.12
    swing_hip_vel: float = 0.10
    swing_knee_vel: float = -0.04
    hip_torque_limit: float = 8.0
    knee_torque_limit: float = 2.0
    hip_kp: float = 18.0
    hip_kd: float = 4.0
    knee_kp: float = 10.0
    knee_kd: float = 1.2
    gait_period: float = 1.00
    swing_back_deg: float = 20.0
    swing_front_deg: float = -22.0
    stance_front_deg: float = -14.0
    stance_back_deg: float = 22.0
    swing_knee_flex_deg: float = 28.0
    stance_knee_deg: float = 2.0
    recovery_clearance: float = 0.38
    min_event_interval: float = 0.22
    stable_contact_time: float = 0.035

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'slope_deg': self.slope_deg,
            'foot_radius': self.foot_radius,
            'foot_length': self.foot_length,
            'toe_radius': self.toe_radius,
            'ankle_limit_deg': self.ankle_limit_deg,
            'ankle_damping': self.ankle_damping,
            'ankle_stiffness': self.ankle_stiffness,
            'friction': self.friction,
            'hip_mass': self.hip_mass,
            'torso_mass': self.torso_mass,
            'torso_height': self.torso_height,
            'initial_vx': self.initial_vx,
            'knee_limit_deg': self.knee_limit_deg,
            'duration': self.duration,
            'timestep': self.timestep,
            'thigh_length': self.thigh_length,
            'shank_length': self.shank_length,
            'step_length': self.step_length,
            'knee_damping': self.knee_damping,
            'knee_stiffness': self.knee_stiffness,
            'hip_joint_damping': self.hip_joint_damping,
            'joint_damping': self.joint_damping,
            'release_phase': self.release_phase,
            'swing_foot_x': self.swing_foot_x,
            'swing_foot_clearance': self.swing_foot_clearance,
            'swing_hip_vel': self.swing_hip_vel,
            'swing_knee_vel': self.swing_knee_vel,
            'hip_torque_limit': self.hip_torque_limit,
            'knee_torque_limit': self.knee_torque_limit,
            'hip_kp': self.hip_kp,
            'hip_kd': self.hip_kd,
            'knee_kp': self.knee_kp,
            'knee_kd': self.knee_kd,
            'gait_period': self.gait_period,
            'swing_back_deg': self.swing_back_deg,
            'swing_front_deg': self.swing_front_deg,
            'stance_front_deg': self.stance_front_deg,
            'stance_back_deg': self.stance_back_deg,
            'swing_knee_flex_deg': self.swing_knee_flex_deg,
            'stance_knee_deg': self.stance_knee_deg,
            'recovery_clearance': self.recovery_clearance,
            'min_event_interval': self.min_event_interval,
            'stable_contact_time': self.stable_contact_time
        }


# =============================================================================
# V13.6 Event-Driven FSM Configuration
# =============================================================================
@dataclass(frozen=True)
class PhaseParams:
    """Phase-specific control parameters for FSM.

    Each gait phase has independent control gains:
    - k_E: Energy shaping gain (0 = disabled)
    - k_PD: PD tracking gain
    - tau_max: Torque saturation limit
    - kd: Derivative gain
    - E_target: Target mechanical energy (used when k_E > 0)
    """
    k_E: float
    k_PD: float
    tau_max: float
    kd: float = 6.0
    E_target: float = 52.66

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'k_E': self.k_E,
            'k_PD': self.k_PD,
            'tau_max': self.tau_max,
            'kd': self.kd,
            'E_target': self.E_target
        }


@dataclass(frozen=True)
class V137FSMConfig:
    """V13.6 event-driven FSM - explicit phase-based control.

    Key characteristics:
    - 4-phase FSM: stance_early, stance_late, swing_thrust, swing_retract
    - Phase transitions triggered by contact events and timing
    - Explicit temporal locking for robust gait
    - Suitable for rehabilitation device control mapping

    Phase mapping to clinical gait cycle:
    - stance_early  → Loading Response + Mid-Stance
    - stance_late   → Terminal Stance + Pre-Swing
    - swing_thrust  → Initial Swing (active energy injection)
    - swing_retract → Mid/Terminal Swing (passive return)
    """
    # Base parameters (inherited from V10)
    base_slope_deg: float = 0.0
    base_foot_radius: float = 0.04
    base_foot_length: float = 0.16
    base_toe_radius: float = 0.028
    base_ankle_limit_deg: float = 25.0
    base_ankle_damping: float = 0.08
    base_ankle_stiffness: float = 0.55
    base_friction: float = 1.35
    base_hip_mass: float = 5.0
    base_torso_mass: float = 0.2
    base_torso_height: float = 0.30
    base_initial_vx: float = 0.04
    base_knee_limit_deg: float = 70.0
    base_duration: float = 12.0
    base_timestep: float = 0.001
    base_thigh_length: float = 0.48
    base_shank_length: float = 0.52
    base_step_length: float = 0.34
    base_knee_damping: float = 0.08
    base_knee_stiffness: float = 0.8
    base_hip_joint_damping: float = 0.02
    base_joint_damping: float = 0.01
    base_release_phase: float = 0.08
    base_swing_foot_x: float = 0.38
    base_swing_foot_clearance: float = 0.12
    base_swing_hip_vel: float = 0.10
    base_swing_knee_vel: float = -0.04
    base_hip_torque_limit: float = 8.0
    base_knee_torque_limit: float = 2.0
    base_hip_kp: float = 18.0
    base_hip_kd: float = 4.0
    base_knee_kp: float = 10.0
    base_knee_kd: float = 1.2
    base_gait_period: float = 1.00
    base_swing_back_deg: float = 20.0
    base_swing_front_deg: float = -22.0
    base_stance_front_deg: float = -14.0
    base_stance_back_deg: float = 22.0
    base_swing_knee_flex_deg: float = 28.0
    base_stance_knee_deg: float = 2.0
    base_recovery_clearance: float = 0.38
    base_min_event_interval: float = 0.22
    base_stable_contact_time: float = 0.035

    # Phase-specific parameters (tuned for stability)
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

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'base': {
                'slope_deg': self.base_slope_deg,
                'foot_radius': self.base_foot_radius,
                'foot_length': self.base_foot_length,
                'toe_radius': self.base_toe_radius,
                'ankle_limit_deg': self.base_ankle_limit_deg,
                'ankle_damping': self.base_ankle_damping,
                'ankle_stiffness': self.base_ankle_stiffness,
                'friction': self.base_friction,
                'hip_mass': self.base_hip_mass,
                'torso_mass': self.base_torso_mass,
                'torso_height': self.base_torso_height,
                'initial_vx': self.base_initial_vx,
                'knee_limit_deg': self.base_knee_limit_deg,
                'duration': self.base_duration,
                'timestep': self.base_timestep,
                'thigh_length': self.base_thigh_length,
                'shank_length': self.base_shank_length,
                'step_length': self.base_step_length,
                'knee_damping': self.base_knee_damping,
                'knee_stiffness': self.base_knee_stiffness,
                'hip_joint_damping': self.base_hip_joint_damping,
                'joint_damping': self.base_joint_damping,
                'release_phase': self.base_release_phase,
                'swing_foot_x': self.base_swing_foot_x,
                'swing_foot_clearance': self.base_swing_foot_clearance,
                'swing_hip_vel': self.base_swing_hip_vel,
                'swing_knee_vel': self.base_swing_knee_vel,
                'hip_torque_limit': self.base_hip_torque_limit,
                'knee_torque_limit': self.base_knee_torque_limit,
                'hip_kp': self.base_hip_kp,
                'hip_kd': self.base_hip_kd,
                'knee_kp': self.base_knee_kp,
                'knee_kd': self.base_knee_kd,
                'gait_period': self.base_gait_period,
                'swing_back_deg': self.base_swing_back_deg,
                'swing_front_deg': self.base_swing_front_deg,
                'stance_front_deg': self.base_stance_front_deg,
                'stance_back_deg': self.base_stance_back_deg,
                'swing_knee_flex_deg': self.base_swing_knee_flex_deg,
                'stance_knee_deg': self.base_stance_knee_deg,
                'recovery_clearance': self.base_recovery_clearance,
                'min_event_interval': self.base_min_event_interval,
                'stable_contact_time': self.base_stable_contact_time
            },
            'phases': {
                'stance_early': self.stance_early.to_dict(),
                'stance_late': self.stance_late.to_dict(),
                'swing_thrust': self.swing_thrust.to_dict(),
                'swing_retract': self.swing_retract.to_dict()
            }
        }


# =============================================================================
# V09 Biomimetic Configuration
# =============================================================================
@dataclass(frozen=True)
class BiomimeticConfig:
    """V09 stable biomimetic gait - natural human-like walking pattern.

    Key characteristics:
    - Simplified foot geometry (no ankle joint)
    - Stable limit cycle behavior
    - Natural gait timing and coordination
    - Foundation for later rolling foot development (V10)
    """
    slope_deg: float = 0.0
    foot_radius: float = 0.04
    foot_length: float = 0.10
    friction: float = 1.35
    hip_mass: float = 5.0
    torso_mass: float = 0.2
    torso_height: float = 0.30
    initial_vx: float = 0.04
    knee_limit_deg: float = 70.0
    duration: float = 12.0
    timestep: float = 0.001
    thigh_length: float = 0.48
    shank_length: float = 0.52
    step_length: float = 0.34
    knee_damping: float = 0.08
    knee_stiffness: float = 0.8
    hip_joint_damping: float = 0.02
    joint_damping: float = 0.01
    release_phase: float = 0.08
    swing_foot_x: float = 0.38
    swing_foot_clearance: float = 0.12
    swing_hip_vel: float = 0.10
    swing_knee_vel: float = -0.04
    hip_torque_limit: float = 8.0
    knee_torque_limit: float = 2.0
    hip_kp: float = 18.0
    hip_kd: float = 4.0
    knee_kp: float = 10.0
    knee_kd: float = 1.2
    gait_period: float = 1.00
    swing_back_deg: float = 20.0
    swing_front_deg: float = -22.0
    stance_front_deg: float = -14.0
    stance_back_deg: float = 22.0
    swing_knee_flex_deg: float = 28.0
    stance_knee_deg: float = 2.0
    recovery_clearance: float = 0.38
    min_event_interval: float = 0.22
    stable_contact_time: float = 0.035

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'slope_deg': self.slope_deg,
            'foot_radius': self.foot_radius,
            'foot_length': self.foot_length,
            'friction': self.friction,
            'hip_mass': self.hip_mass,
            'torso_mass': self.torso_mass,
            'torso_height': self.torso_height,
            'initial_vx': self.initial_vx,
            'knee_limit_deg': self.knee_limit_deg,
            'duration': self.duration,
            'timestep': self.timestep,
            'thigh_length': self.thigh_length,
            'shank_length': self.shank_length,
            'step_length': self.step_length,
            'knee_damping': self.knee_damping,
            'knee_stiffness': self.knee_stiffness,
            'hip_joint_damping': self.hip_joint_damping,
            'joint_damping': self.joint_damping,
            'release_phase': self.release_phase,
            'swing_foot_x': self.swing_foot_x,
            'swing_foot_clearance': self.swing_foot_clearance,
            'swing_hip_vel': self.swing_hip_vel,
            'swing_knee_vel': self.swing_knee_vel,
            'hip_torque_limit': self.hip_torque_limit,
            'knee_torque_limit': self.knee_torque_limit,
            'hip_kp': self.hip_kp,
            'hip_kd': self.hip_kd,
            'knee_kp': self.knee_kp,
            'knee_kd': self.knee_kd,
            'gait_period': self.gait_period,
            'swing_back_deg': self.swing_back_deg,
            'swing_front_deg': self.swing_front_deg,
            'stance_front_deg': self.stance_front_deg,
            'stance_back_deg': self.stance_back_deg,
            'swing_knee_flex_deg': self.swing_knee_flex_deg,
            'stance_knee_deg': self.stance_knee_deg,
            'recovery_clearance': self.recovery_clearance,
            'min_event_interval': self.min_event_interval,
            'stable_contact_time': self.stable_contact_time
        }


# =============================================================================
# Template Registry
# =============================================================================
TEMPLATES: Dict[str, Any] = {
    'v05_passive': V05PassiveConfig(),
    'v10_rolling': V10RollingConfig(),
    'v137_fsm': V137FSMConfig(),
    'biomimetic': BiomimeticConfig()
}


def get_template(name: str) -> Any:
    """Retrieve a template configuration by name.

    Args:
        name: Template identifier ('v05_passive', 'v10_rolling', 'v137_fsm', 'biomimetic')

    Returns:
        Configuration dataclass instance

    Raises:
        KeyError: If template name not found
    """
    if name not in TEMPLATES:
        available = ', '.join(TEMPLATES.keys())
        raise KeyError(f"Template '{name}' not found. Available: {available}")
    return TEMPLATES[name]


def list_templates() -> list[str]:
    """Get list of available template names."""
    return list(TEMPLATES.keys())


def get_template_dict(name: str) -> Dict[str, Any]:
    """Get template configuration as dictionary.

    Args:
        name: Template identifier

    Returns:
        Dictionary representation of configuration
    """
    template = get_template(name)
    return template.to_dict()


# =============================================================================
# Usage Examples
# =============================================================================
if __name__ == '__main__':
    import json

    print("Available templates:")
    for name in list_templates():
        print(f"  - {name}")

    print("\n" + "=" * 70)
    print("V05 Passive Configuration:")
    print("=" * 70)
    v05 = get_template('v05_passive')
    print(json.dumps(v05.to_dict(), indent=2))

    print("\n" + "=" * 70)
    print("V10 Rolling Configuration (first 10 parameters):")
    print("=" * 70)
    v10 = get_template('v10_rolling')
    v10_dict = v10.to_dict()
    for i, (key, value) in enumerate(v10_dict.items()):
        if i >= 10:
            print(f"  ... ({len(v10_dict) - 10} more parameters)")
            break
        print(f"  {key}: {value}")

    print("\n" + "=" * 70)
    print("V13.7 FSM Phase Configuration:")
    print("=" * 70)
    v137 = get_template('v137_fsm')
    v137_dict = v137.to_dict()
    print(json.dumps(v137_dict['phases'], indent=2))

    print("\n" + "=" * 70)
    print("Biomimetic Configuration (summary):")
    print("=" * 70)
    bio = get_template('biomimetic')
    bio_dict = bio.to_dict()
    print(f"  Total parameters: {len(bio_dict)}")
    print(f"  Leg length: {bio.thigh_length + bio.shank_length:.2f}m")
    print(f"  Hip mass: {bio.hip_mass}kg")
    print(f"  Gait period: {bio.gait_period}s")
