"""
Trajectory Generator for Gait Training Device
Generates desired joint angles and velocities per phase based on V13.7 FSM

Provides phase-specific setpoints with optional smooth interpolation for
hardware-ready control implementation.
"""

import math
from dataclasses import dataclass
from typing import Optional

from phase_fsm import PhaseState


@dataclass
class JointTrajectory:
    """Desired joint state for control"""
    theta_des: float  # Desired joint angle (radians)
    omega_des: float  # Desired joint velocity (rad/s)


@dataclass
class TrajectoryProfile:
    """Phase-specific trajectory parameters from V13.7 optimal configuration"""
    # Hip joint angles (degrees, converted to radians in class methods)
    stance_front_deg: float = -14.0    # Hip angle at start of stance
    stance_back_deg: float = 22.0      # Hip angle at end of stance
    swing_back_deg: float = 20.0       # Hip angle at start of swing
    swing_front_deg: float = -22.0     # Hip angle at end of swing

    # Knee joint angles (degrees)
    stance_knee_deg: float = 2.0       # Knee angle during stance (nearly straight)
    swing_knee_flex_deg: float = 28.0  # Peak knee flexion during swing

    # Slope compensation
    slope_deg: float = 0.0             # Ground slope angle

    # Phase durations (seconds, matches FSM)
    stance_early_duration: float = 0.15
    stance_late_duration: float = 0.25
    swing_thrust_duration: float = 0.20
    swing_retract_duration: float = 0.20

    # Velocity estimates for swing phase (rad/s)
    swing_hip_velocity: float = 0.10
    swing_knee_velocity: float = -0.04

    @property
    def total_cycle_time(self) -> float:
        """Total gait cycle duration"""
        return (self.stance_early_duration + self.stance_late_duration +
                self.swing_thrust_duration + self.swing_retract_duration)


class TrajectoryGenerator:
    """
    Generates desired joint trajectories for each gait phase.

    Based on V13.7 rolling-foot biomimetic gait with phase-specific
    hip and knee angle targets. Supports smooth interpolation within phases.
    """

    def __init__(self, profile: Optional[TrajectoryProfile] = None,
                 enable_smoothing: bool = True):
        """
        Initialize trajectory generator.

        Args:
            profile: Trajectory profile with phase-specific setpoints.
                    If None, uses default V13.7 parameters.
            enable_smoothing: If True, use smoothstep interpolation within phases.
                             If False, use linear interpolation.
        """
        self.profile = profile if profile is not None else TrajectoryProfile()
        self.enable_smoothing = enable_smoothing

        # Precompute slope offset in radians
        self._slope_offset = math.radians(self.profile.slope_deg)

    def get_hip_trajectory(self, phase: PhaseState, phase_progress: float,
                          is_stance_leg: bool) -> JointTrajectory:
        """
        Get desired hip joint trajectory for current phase.

        Args:
            phase: Current gait phase (0-3)
            phase_progress: Progress through phase in range [0.0, 1.0]
            is_stance_leg: True if this is the stance leg, False if swing leg

        Returns:
            JointTrajectory with desired angle and velocity
        """
        phase_progress = max(0.0, min(1.0, phase_progress))  # Clamp to [0, 1]

        # Apply smoothstep if enabled
        u = self._smoothstep(phase_progress) if self.enable_smoothing else phase_progress

        if is_stance_leg:
            # Stance leg trajectory
            if phase in (PhaseState.STANCE_EARLY, PhaseState.STANCE_LATE):
                # Stance phase: sweep from front to back
                theta_start = math.radians(self.profile.stance_front_deg) + self._slope_offset
                theta_end = math.radians(self.profile.stance_back_deg) + self._slope_offset

                # Progress through full stance using combined progress
                if phase == PhaseState.STANCE_EARLY:
                    stance_progress = u * (self.profile.stance_early_duration /
                                          (self.profile.stance_early_duration +
                                           self.profile.stance_late_duration))
                else:  # STANCE_LATE
                    stance_progress = (self.profile.stance_early_duration /
                                      (self.profile.stance_early_duration +
                                       self.profile.stance_late_duration)) + \
                                     u * (self.profile.stance_late_duration /
                                          (self.profile.stance_early_duration +
                                           self.profile.stance_late_duration))

                theta_des = theta_start + (theta_end - theta_start) * stance_progress

                # Velocity estimate based on angular displacement and time
                total_stance_time = (self.profile.stance_early_duration +
                                   self.profile.stance_late_duration)
                omega_des = (theta_end - theta_start) / total_stance_time

            else:  # Swing phases - transition from back to front for next stance
                theta_start = math.radians(self.profile.stance_back_deg) + self._slope_offset
                theta_end = math.radians(self.profile.stance_front_deg) + self._slope_offset
                theta_des = theta_start + (theta_end - theta_start) * u

                total_swing_time = (self.profile.swing_thrust_duration +
                                  self.profile.swing_retract_duration)
                omega_des = (theta_end - theta_start) / total_swing_time

        else:
            # Swing leg trajectory
            if phase in (PhaseState.STANCE_EARLY, PhaseState.STANCE_LATE):
                # During stance of other leg, this leg is in swing
                theta_start = math.radians(self.profile.swing_back_deg) + self._slope_offset
                theta_end = math.radians(self.profile.swing_front_deg) + self._slope_offset
                theta_des = theta_start + (theta_end - theta_start) * u
                omega_des = self.profile.swing_hip_velocity

            else:  # Actually in swing phase
                # SWING_THRUST and SWING_RETRACT
                theta_start = math.radians(self.profile.swing_back_deg) + self._slope_offset
                theta_end = math.radians(self.profile.swing_front_deg) + self._slope_offset

                # Combine progress through both swing phases
                if phase == PhaseState.SWING_THRUST:
                    swing_progress = u * (self.profile.swing_thrust_duration /
                                         (self.profile.swing_thrust_duration +
                                          self.profile.swing_retract_duration))
                else:  # SWING_RETRACT
                    swing_progress = (self.profile.swing_thrust_duration /
                                     (self.profile.swing_thrust_duration +
                                      self.profile.swing_retract_duration)) + \
                                    u * (self.profile.swing_retract_duration /
                                         (self.profile.swing_thrust_duration +
                                          self.profile.swing_retract_duration))

                theta_des = theta_start + (theta_end - theta_start) * swing_progress
                omega_des = self.profile.swing_hip_velocity

        return JointTrajectory(theta_des=theta_des, omega_des=omega_des)

    def get_knee_trajectory(self, phase: PhaseState, phase_progress: float,
                           is_stance_leg: bool) -> JointTrajectory:
        """
        Get desired knee joint trajectory for current phase.

        Args:
            phase: Current gait phase (0-3)
            phase_progress: Progress through phase in range [0.0, 1.0]
            is_stance_leg: True if this is the stance leg, False if swing leg

        Returns:
            JointTrajectory with desired angle and velocity
        """
        phase_progress = max(0.0, min(1.0, phase_progress))

        if is_stance_leg:
            # Stance leg: keep knee nearly straight
            theta_des = math.radians(self.profile.stance_knee_deg)
            omega_des = 0.0

        else:
            # Swing leg: flex during swing phases
            if phase in (PhaseState.SWING_THRUST, PhaseState.SWING_RETRACT):
                # Combine progress through both swing phases for smooth sinusoidal flexion
                if phase == PhaseState.SWING_THRUST:
                    swing_progress = phase_progress * (self.profile.swing_thrust_duration /
                                                       (self.profile.swing_thrust_duration +
                                                        self.profile.swing_retract_duration))
                else:  # SWING_RETRACT
                    swing_progress = (self.profile.swing_thrust_duration /
                                     (self.profile.swing_thrust_duration +
                                      self.profile.swing_retract_duration)) + \
                                    phase_progress * (self.profile.swing_retract_duration /
                                                     (self.profile.swing_thrust_duration +
                                                      self.profile.swing_retract_duration))

                # Sinusoidal knee flexion: peaks at mid-swing
                theta_des = math.radians(self.profile.swing_knee_flex_deg *
                                        math.sin(math.pi * swing_progress))

                # Velocity: derivative of sine wave
                total_swing_time = (self.profile.swing_thrust_duration +
                                  self.profile.swing_retract_duration)
                omega_des = (math.radians(self.profile.swing_knee_flex_deg) *
                           math.pi / total_swing_time *
                           math.cos(math.pi * swing_progress))
            else:
                # Stance phases of other leg: prepare for next stance
                theta_des = math.radians(self.profile.stance_knee_deg)
                omega_des = self.profile.swing_knee_velocity

        return JointTrajectory(theta_des=theta_des, omega_des=omega_des)

    def get_full_trajectory(self, phase: PhaseState, phase_progress: float,
                           stance_leg: str = 'left') -> dict[str, JointTrajectory]:
        """
        Get complete trajectory for both legs.

        Args:
            phase: Current gait phase (0-3)
            phase_progress: Progress through phase in range [0.0, 1.0]
            stance_leg: Which leg is currently in stance ('left' or 'right')

        Returns:
            Dictionary with keys 'left_hip', 'left_knee', 'right_hip', 'right_knee'
        """
        left_is_stance = (stance_leg.lower() == 'left')

        left_hip = self.get_hip_trajectory(phase, phase_progress, is_stance_leg=left_is_stance)
        left_knee = self.get_knee_trajectory(phase, phase_progress, is_stance_leg=left_is_stance)
        right_hip = self.get_hip_trajectory(phase, phase_progress, is_stance_leg=not left_is_stance)
        right_knee = self.get_knee_trajectory(phase, phase_progress, is_stance_leg=not left_is_stance)

        return {
            'left_hip': left_hip,
            'left_knee': left_knee,
            'right_hip': right_hip,
            'right_knee': right_knee,
        }

    def update_profile(self, **kwargs):
        """
        Update trajectory profile parameters.

        Accepts any TrajectoryProfile field as keyword argument.
        Example: update_profile(stance_front_deg=-12.0, swing_knee_flex_deg=30.0)
        """
        for key, value in kwargs.items():
            if hasattr(self.profile, key):
                setattr(self.profile, key, value)
            else:
                raise ValueError(f"Unknown profile parameter: {key}")

        # Recompute slope offset if slope changed
        if 'slope_deg' in kwargs:
            self._slope_offset = math.radians(self.profile.slope_deg)

    @staticmethod
    def _smoothstep(u: float) -> float:
        """
        Smoothstep interpolation function: s(u) = 3u² - 2u³

        Provides smooth acceleration/deceleration at phase boundaries.

        Args:
            u: Input value in range [0, 1]

        Returns:
            Smoothed value in range [0, 1]
        """
        u = max(0.0, min(1.0, u))
        return u * u * (3.0 - 2.0 * u)


# Example usage and testing
if __name__ == "__main__":
    import time

    print("Trajectory Generator Test - V13.7 Configuration")
    print("=" * 60)

    # Create generator with default V13.7 profile
    generator = TrajectoryGenerator(enable_smoothing=True)

    print(f"\nProfile Parameters:")
    print(f"  Stance front: {generator.profile.stance_front_deg}°")
    print(f"  Stance back: {generator.profile.stance_back_deg}°")
    print(f"  Swing back: {generator.profile.swing_back_deg}°")
    print(f"  Swing front: {generator.profile.swing_front_deg}°")
    print(f"  Stance knee: {generator.profile.stance_knee_deg}°")
    print(f"  Swing knee flex: {generator.profile.swing_knee_flex_deg}°")
    print(f"  Total cycle time: {generator.profile.total_cycle_time:.2f}s")

    # Simulate one complete gait cycle
    print("\n" + "=" * 60)
    print("Simulated Gait Cycle (Left leg stance):")
    print("=" * 60)
    print(f"{'Time':>6} {'Phase':>15} {'Prog':>5} {'L.Hip':>8} {'L.Knee':>8} {'R.Hip':>8} {'R.Knee':>8}")
    print("-" * 60)

    phases = [
        (PhaseState.STANCE_EARLY, generator.profile.stance_early_duration),
        (PhaseState.STANCE_LATE, generator.profile.stance_late_duration),
        (PhaseState.SWING_THRUST, generator.profile.swing_thrust_duration),
        (PhaseState.SWING_RETRACT, generator.profile.swing_retract_duration),
    ]

    t = 0.0
    dt = 0.05  # 50ms timestep

    for phase, duration in phases:
        phase_time = 0.0
        while phase_time < duration:
            progress = phase_time / duration

            # Get trajectories
            trajectories = generator.get_full_trajectory(phase, progress, stance_leg='left')

            # Print state
            print(f"{t:6.2f} {phase.name:>15} {progress:5.2f} "
                  f"{math.degrees(trajectories['left_hip'].theta_des):8.1f} "
                  f"{math.degrees(trajectories['left_knee'].theta_des):8.1f} "
                  f"{math.degrees(trajectories['right_hip'].theta_des):8.1f} "
                  f"{math.degrees(trajectories['right_knee'].theta_des):8.1f}")

            phase_time += dt
            t += dt

    # Test custom profile
    print("\n" + "=" * 60)
    print("Custom Profile Test (Increased knee flexion):")
    print("=" * 60)

    custom_generator = TrajectoryGenerator()
    custom_generator.update_profile(swing_knee_flex_deg=35.0, slope_deg=2.0)

    print(f"Updated swing knee flex: {custom_generator.profile.swing_knee_flex_deg}°")
    print(f"Updated slope: {custom_generator.profile.slope_deg}°")

    # Sample mid-swing trajectory
    mid_swing_traj = custom_generator.get_full_trajectory(
        PhaseState.SWING_THRUST, 0.5, stance_leg='left'
    )

    print(f"\nMid-swing right knee angle: "
          f"{math.degrees(mid_swing_traj['right_knee'].theta_des):.1f}°")

    print("\n" + "=" * 60)
    print("Trajectory Generator Ready for Hardware Integration")
    print("=" * 60)
