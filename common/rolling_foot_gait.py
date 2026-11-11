"""RollingFootGait model - Heel-toe rolling capable biped walker.

Based on v10 implementation with heel-toe rolling capability.
Provides a reusable model class for biomimetic gait with passive foot rolling.

Key features:
- Heel-toe-toe geometry with separate contact points
- Passive ankle joint with spring-damper
- Quasi-passive control with minimal actuation
- Event-driven phase transitions
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any

import mujoco
import numpy as np

from .model_loader import load_model_from_xml


@dataclass(frozen=True)
class RollingFootParams:
    """Parameters for the rolling foot biped model."""

    # Terrain
    slope_deg: float = 0.0
    friction: float = 1.35

    # Foot geometry (heel-toe rolling)
    foot_radius: float = 0.04  # Heel radius
    foot_length: float = 0.16  # Total foot length
    toe_radius: float = 0.028  # Toe radius (smaller for natural roll-off)

    # Leg dimensions
    thigh_length: float = 0.48
    shank_length: float = 0.52

    # Masses
    hip_mass: float = 5.0
    torso_mass: float = 0.2
    torso_height: float = 0.30

    # Joint limits and passive dynamics
    ankle_limit_deg: float = 25.0
    ankle_damping: float = 0.08
    ankle_stiffness: float = 0.55
    knee_limit_deg: float = 70.0
    knee_damping: float = 0.08
    knee_stiffness: float = 0.8
    hip_joint_damping: float = 0.02
    joint_damping: float = 0.01

    # Control parameters
    hip_kp: float = 18.0
    hip_kd: float = 4.0
    knee_kp: float = 10.0
    knee_kd: float = 1.2
    hip_torque_limit: float = 8.0
    knee_torque_limit: float = 2.0

    # Gait timing and targets
    gait_period: float = 1.00
    swing_back_deg: float = 20.0
    swing_front_deg: float = -22.0
    stance_front_deg: float = -14.0
    stance_back_deg: float = 22.0
    swing_knee_flex_deg: float = 28.0
    stance_knee_deg: float = 2.0

    # Initialization
    initial_vx: float = 0.04
    step_length: float = 0.34
    release_phase: float = 0.08
    swing_foot_x: float = 0.38
    swing_foot_clearance: float = 0.12
    swing_hip_vel: float = 0.10
    swing_knee_vel: float = -0.04

    # Contact detection
    min_event_interval: float = 0.22
    stable_contact_time: float = 0.035
    recovery_clearance: float = 0.38

    # Simulation
    timestep: float = 0.001
    duration: float = 12.0

    @property
    def gamma(self) -> float:
        """Slope angle in radians."""
        return math.radians(self.slope_deg)

    @property
    def leg_length(self) -> float:
        """Total leg length."""
        return self.thigh_length + self.shank_length

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class RollingFootGait:
    """Rolling foot biped gait model with heel-toe capability.

    This class encapsulates:
    - Model XML generation
    - Initialization (IK-based)
    - Contact detection (heel/sole/toe)
    - Control law (PD-based quasi-passive)
    - Geometry utilities (ramp height, foot positioning)
    """

    def __init__(self, params: RollingFootParams):
        """Initialize the model.

        Args:
            params: Model parameters
        """
        self.params = params
        self._model: mujoco.MjModel | None = None
        self._data: mujoco.MjData | None = None

    @property
    def model(self) -> mujoco.MjModel:
        """Get or build the MuJoCo model."""
        if self._model is None:
            self._model = self._build_model()
        return self._model

    @property
    def data(self) -> mujoco.MjData:
        """Get or create MuJoCo data structure."""
        if self._data is None:
            self._data = mujoco.MjData(self.model)
        return self._data

    def _build_model(self) -> mujoco.MjModel:
        """Build MuJoCo model from parameters."""
        xml_string = self._generate_xml()
        return load_model_from_xml(xml_string, validate=True)

    def _generate_xml(self) -> str:
        """Generate MuJoCo XML model string."""
        p = self.params
        ctrl_limit = max(p.hip_torque_limit, p.knee_torque_limit, 1.0)

        return f"""<mujoco model="rolling_foot_biomimetic_gait">
  <compiler angle="degree" coordinate="local"/>
  <option timestep="{p.timestep}" integrator="implicitfast" gravity="0 0 -9.81"/>
  <visual><global offwidth="1280" offheight="720"/></visual>
  <default>
    <joint armature="0.004" damping="{p.joint_damping}"/>
    <geom condim="3" friction="{p.friction} 0.04 0.004" solref="0.006 1" solimp="0.90 0.98 0.002"/>
  </default>
  <asset>
    <texture name="grid" type="2d" builtin="checker" rgb1="0.80 0.87 0.84" rgb2="0.96 0.94 0.88" width="512" height="512"/>
    <material name="ramp_mat" texture="grid" texrepeat="12 1" rgba="0.76 0.82 0.78 1"/>
    <material name="left_mat" rgba="0.05 0.47 0.57 1"/>
    <material name="right_mat" rgba="0.86 0.29 0.21 1"/>
    <material name="hip_mat" rgba="0.08 0.12 0.20 1"/>
    <material name="knee_mat" rgba="0.95 0.74 0.36 1"/>
    <material name="foot_mat" rgba="0.08 0.08 0.08 1"/>
  </asset>
  <worldbody>
    <light name="key" pos="-2 -3 5" dir="0.3 0.5 -1" diffuse="0.85 0.85 0.85"/>
    <geom name="ramp" type="plane" pos="0 0 0" euler="0 {p.slope_deg} 0" size="45 1.8 0.08" material="ramp_mat" contype="1" conaffinity="1"/>
    <body name="hip" pos="0 0 0">
      <joint name="hip_x" type="slide" axis="1 0 0" damping="0.001"/>
      <joint name="hip_z" type="slide" axis="0 0 1" damping="0.001"/>
      <geom name="hip_mass" type="sphere" size="0.08" mass="{p.hip_mass}" material="hip_mat" contype="0" conaffinity="0"/>
      <geom name="torso_mass" type="capsule" fromto="0 0 0.02 0 0 {p.torso_height}" size="0.04" mass="{p.torso_mass}" material="hip_mat" contype="0" conaffinity="0"/>
      <geom name="hip_axis" type="cylinder" fromto="0 -0.13 0 0 0.13 0" size="0.018" mass="0.05" material="hip_mat" contype="0" conaffinity="0"/>
      <body name="left_thigh" pos="0 -0.055 0">
        <joint name="left_hip" type="hinge" axis="0 1 0" range="-95 95" limited="true" damping="{p.hip_joint_damping}"/>
        <geom name="left_upper" type="capsule" fromto="0 0 0 0 0 -{p.thigh_length}" size="0.026" mass="0.18" material="left_mat" contype="0" conaffinity="0"/>
        <body name="left_shank" pos="0 0 -{p.thigh_length}">
          <joint name="left_knee" type="hinge" axis="0 1 0" range="0 {p.knee_limit_deg}" limited="true" damping="{p.knee_damping}" stiffness="{p.knee_stiffness}" springref="0"/>
          <geom name="left_knee_marker" type="sphere" pos="0 0 0" size="0.04" mass="0.03" material="knee_mat" contype="0" conaffinity="0"/>
          <geom name="left_lower" type="capsule" fromto="0 0 0 0 0 -{p.shank_length}" size="0.023" mass="0.16" material="left_mat" contype="0" conaffinity="0"/>
          <body name="left_foot_body" pos="0 0 -{p.shank_length}">
            <joint name="left_ankle" type="hinge" axis="0 1 0" range="-{p.ankle_limit_deg} {p.ankle_limit_deg}" limited="true" damping="{p.ankle_damping}" stiffness="{p.ankle_stiffness}" springref="0"/>
            <geom name="left_sole" type="capsule" fromto="-{p.foot_length * 0.45} 0 -0.015 {p.foot_length * 0.35} 0 -0.015" size="{p.foot_radius * 0.55}" mass="0.06" material="foot_mat" contype="1" conaffinity="1"/>
            <geom name="left_heel" type="sphere" pos="-{p.foot_length * 0.50} 0 -0.015" size="{p.foot_radius}" mass="0.025" material="foot_mat" contype="1" conaffinity="1"/>
            <geom name="left_toe" type="sphere" pos="{p.foot_length * 0.48} 0 -0.018" size="{p.toe_radius}" mass="0.025" material="foot_mat" contype="1" conaffinity="1"/>
            <site name="left_foot_site" pos="0 0 -0.015" size="0.01"/>
            <site name="left_heel_site" pos="-{p.foot_length * 0.50} 0 -0.015" size="0.01"/>
            <site name="left_toe_site" pos="{p.foot_length * 0.48} 0 -0.018" size="0.01"/>
          </body>
        </body>
      </body>
      <body name="right_thigh" pos="0 0.055 0">
        <joint name="right_hip" type="hinge" axis="0 1 0" range="-95 95" limited="true" damping="{p.hip_joint_damping}"/>
        <geom name="right_upper" type="capsule" fromto="0 0 0 0 0 -{p.thigh_length}" size="0.026" mass="0.18" material="right_mat" contype="0" conaffinity="0"/>
        <body name="right_shank" pos="0 0 -{p.thigh_length}">
          <joint name="right_knee" type="hinge" axis="0 1 0" range="0 {p.knee_limit_deg}" limited="true" damping="{p.knee_damping}" stiffness="{p.knee_stiffness}" springref="0"/>
          <geom name="right_knee_marker" type="sphere" pos="0 0 0" size="0.04" mass="0.03" material="knee_mat" contype="0" conaffinity="0"/>
          <geom name="right_lower" type="capsule" fromto="0 0 0 0 0 -{p.shank_length}" size="0.023" mass="0.16" material="right_mat" contype="0" conaffinity="0"/>
          <body name="right_foot_body" pos="0 0 -{p.shank_length}">
            <joint name="right_ankle" type="hinge" axis="0 1 0" range="-{p.ankle_limit_deg} {p.ankle_limit_deg}" limited="true" damping="{p.ankle_damping}" stiffness="{p.ankle_stiffness}" springref="0"/>
            <geom name="right_sole" type="capsule" fromto="-{p.foot_length * 0.45} 0 -0.015 {p.foot_length * 0.35} 0 -0.015" size="{p.foot_radius * 0.55}" mass="0.06" material="foot_mat" contype="1" conaffinity="1"/>
            <geom name="right_heel" type="sphere" pos="-{p.foot_length * 0.50} 0 -0.015" size="{p.foot_radius}" mass="0.025" material="foot_mat" contype="1" conaffinity="1"/>
            <geom name="right_toe" type="sphere" pos="{p.foot_length * 0.48} 0 -0.018" size="{p.toe_radius}" mass="0.025" material="foot_mat" contype="1" conaffinity="1"/>
            <site name="right_foot_site" pos="0 0 -0.015" size="0.01"/>
            <site name="right_heel_site" pos="-{p.foot_length * 0.50} 0 -0.015" size="0.01"/>
            <site name="right_toe_site" pos="{p.foot_length * 0.48} 0 -0.018" size="0.01"/>
          </body>
        </body>
      </body>
    </body>
  </worldbody>
  <actuator>
    <motor name="left_hip_muscle" joint="left_hip" gear="1" ctrllimited="true" ctrlrange="-{ctrl_limit} {ctrl_limit}"/>
    <motor name="left_knee_stabilizer" joint="left_knee" gear="1" ctrllimited="true" ctrlrange="-{ctrl_limit} {ctrl_limit}"/>
    <motor name="right_hip_muscle" joint="right_hip" gear="1" ctrllimited="true" ctrlrange="-{ctrl_limit} {ctrl_limit}"/>
    <motor name="right_knee_stabilizer" joint="right_knee" gear="1" ctrllimited="true" ctrlrange="-{ctrl_limit} {ctrl_limit}"/>
  </actuator>
</mujoco>
"""

    # ========================================================================
    # Geometry utilities
    # ========================================================================

    def ramp_height(self, x: float) -> float:
        """Calculate ramp height at position x."""
        return -math.tan(self.params.gamma) * x

    def foot_center_z_on_ramp(self, x: float) -> float:
        """Calculate foot center z-coordinate on ramp at position x."""
        return self.ramp_height(x) + self.params.foot_radius / max(
            0.2, math.cos(self.params.gamma)
        )

    @staticmethod
    def smoothstep(u: float) -> float:
        """Smoothstep interpolation function."""
        u = min(max(u, 0.0), 1.0)
        return u * u * (3.0 - 2.0 * u)

    def leg_ik_front_knee(
        self,
        hip_x: float,
        hip_z: float,
        foot_x: float,
        foot_z: float,
    ) -> tuple[float, float]:
        """Inverse kinematics for front-knee leg configuration.

        Args:
            hip_x, hip_z: Hip position
            foot_x, foot_z: Foot position

        Returns:
            (hip_angle, knee_angle) in radians
        """
        p = self.params
        px = hip_x - foot_x
        pz = hip_z - foot_z
        d = math.hypot(px, pz)
        d = float(
            np.clip(
                d,
                abs(p.thigh_length - p.shank_length) + 1e-5,
                p.leg_length - 1e-5,
            )
        )
        base = math.atan2(px, pz)
        cos_delta = (p.thigh_length**2 + d**2 - p.shank_length**2) / (
            2.0 * p.thigh_length * d
        )
        delta = math.acos(float(np.clip(cos_delta, -1.0, 1.0)))
        thigh = base - delta
        knee_x = hip_x - p.thigh_length * math.sin(thigh)
        knee_z = hip_z - p.thigh_length * math.cos(thigh)
        shank = math.atan2(knee_x - foot_x, knee_z - foot_z)
        knee = float(np.clip(shank - thigh, 0.0, math.radians(p.knee_limit_deg)))
        return thigh, knee

    # ========================================================================
    # Initialization
    # ========================================================================

    def initialize(self) -> None:
        """Initialize the model state using IK.

        Sets initial positions and velocities based on release_phase.
        """
        p = self.params
        data = self.data

        u = self.smoothstep(p.release_phase)
        alpha = math.asin(p.step_length / (2.0 * p.leg_length))
        support_x = 0.0
        support_z = self.foot_center_z_on_ramp(support_x)
        left_hip = p.gamma + alpha - 2.0 * alpha * u
        hip_x = support_x + p.leg_length * math.sin(left_hip)
        hip_z = support_z + p.leg_length * math.cos(left_hip)
        right_hip, right_knee = self.leg_ik_front_knee(
            hip_x,
            hip_z,
            p.swing_foot_x,
            self.foot_center_z_on_ramp(p.swing_foot_x) + p.swing_foot_clearance,
        )
        data.qpos[:] = [hip_x, hip_z, left_hip, 0.0, 0.0, right_hip, right_knee, 0.0]
        data.qvel[:] = [
            p.initial_vx,
            -math.tan(p.gamma) * p.initial_vx,
            0.04,
            0.0,
            0.0,
            p.swing_hip_vel,
            p.swing_knee_vel,
            0.0,
        ]
        data.ctrl[:] = 0.0
        mujoco.mj_forward(self.model, data)

    # ========================================================================
    # Contact detection
    # ========================================================================

    def foot_contact_detail(self) -> dict[str, bool]:
        """Get detailed contact information for each foot segment.

        Returns:
            Dictionary with keys: left_heel, left_sole, left_toe,
                                  right_heel, right_sole, right_toe
        """
        model = self.model
        data = self.data
        ramp = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "ramp")
        names = [
            "left_heel",
            "left_sole",
            "left_toe",
            "right_heel",
            "right_sole",
            "right_toe",
        ]
        geom_ids = {
            name: mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, name)
            for name in names
        }
        detail = dict.fromkeys(names, False)
        for i in range(data.ncon):
            pair = {data.contact[i].geom1, data.contact[i].geom2}
            if ramp in pair:
                for name, geom_id in geom_ids.items():
                    if geom_id in pair:
                        detail[name] = True
        return detail

    def contact_flags(self) -> tuple[bool, bool]:
        """Get overall contact flags for left and right feet.

        Returns:
            (left_contact, right_contact) tuple
        """
        detail = self.foot_contact_detail()
        left_contact = detail["left_heel"] or detail["left_sole"] or detail["left_toe"]
        right_contact = (
            detail["right_heel"] or detail["right_sole"] or detail["right_toe"]
        )
        return left_contact, right_contact

    def site_margin(self, site_name: str) -> float:
        """Calculate margin (clearance) for a site above the ramp.

        Args:
            site_name: Name of the site

        Returns:
            Vertical distance from site to ramp surface
        """
        model = self.model
        data = self.data
        site_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, site_name)
        pos = data.site_xpos[site_id]
        return float(pos[2] - self.foot_center_z_on_ramp(float(pos[0])))

    # ========================================================================
    # Control
    # ========================================================================

    @staticmethod
    def limited_pd(
        q: float, qd: float, target: float, kp: float, kd: float, limit: float
    ) -> float:
        """PD controller with torque limiting.

        Args:
            q: Current position
            qd: Current velocity
            target: Target position
            kp: Proportional gain
            kd: Derivative gain
            limit: Torque limit

        Returns:
            Limited torque command
        """
        return float(np.clip(kp * (target - q) - kd * qd, -limit, limit))

    def compute_control(
        self,
        t: float,
        support_foot: str,
        burst_start_t: float,
    ) -> tuple[float, float, float, float, str]:
        """Compute control torques based on current state.

        Args:
            t: Current time
            support_foot: Which foot is currently supporting ("left" or "right")
            burst_start_t: Time when current gait cycle started

        Returns:
            (left_hip_tau, left_knee_tau, right_hip_tau, right_knee_tau, mode)
        """
        p = self.params
        data = self.data

        hip_x = float(data.qpos[0])
        hip_z = float(data.qpos[1])
        clearance = hip_z - self.ramp_height(hip_x)
        mode = "left_stance" if support_foot == "left" else "right_stance"

        u = min(max((t - burst_start_t) / max(p.gait_period, 1e-6), 0.0), 1.0)
        if clearance < p.recovery_clearance:
            u = min(u, 0.55)
            mode = "recovery"

        s = self.smoothstep(u)
        offset = p.gamma
        stance_target = offset + math.radians(
            p.stance_front_deg + (p.stance_back_deg - p.stance_front_deg) * s
        )
        swing_target = offset + math.radians(
            p.swing_back_deg + (p.swing_front_deg - p.swing_back_deg) * s
        )
        swing_knee = math.radians(p.swing_knee_flex_deg * math.sin(math.pi * u))
        stance_knee = math.radians(p.stance_knee_deg)

        left_is_support = support_foot == "left"
        left_hip_target = stance_target if left_is_support else swing_target
        right_hip_target = stance_target if not left_is_support else swing_target
        left_knee_target = stance_knee if left_is_support else swing_knee
        right_knee_target = stance_knee if not left_is_support else swing_knee

        left_hip_tau = self.limited_pd(
            float(data.qpos[2]),
            float(data.qvel[2]),
            left_hip_target,
            p.hip_kp,
            p.hip_kd,
            p.hip_torque_limit,
        )
        left_knee_tau = self.limited_pd(
            float(data.qpos[3]),
            float(data.qvel[3]),
            left_knee_target,
            p.knee_kp,
            p.knee_kd,
            p.knee_torque_limit,
        )
        right_hip_tau = self.limited_pd(
            float(data.qpos[5]),
            float(data.qvel[5]),
            right_hip_target,
            p.hip_kp,
            p.hip_kd,
            p.hip_torque_limit,
        )
        right_knee_tau = self.limited_pd(
            float(data.qpos[6]),
            float(data.qvel[6]),
            right_knee_target,
            p.knee_kp,
            p.knee_kd,
            p.knee_torque_limit,
        )
        return left_hip_tau, left_knee_tau, right_hip_tau, right_knee_tau, mode

    # ========================================================================
    # Simulation utilities
    # ========================================================================

    def classify_failure(self, start_x: float, t: float) -> str:
        """Classify failure mode based on current state.

        Args:
            start_x: Initial hip x position
            t: Current time

        Returns:
            Failure string (empty if no failure detected)
        """
        data = self.data
        p = self.params

        if not np.all(np.isfinite(data.qpos)) or not np.all(np.isfinite(data.qvel)):
            return "nan_or_unstable"
        if float(np.linalg.norm(data.qvel)) > 45.0:
            return "nan_or_unstable"
        hip_x, hip_z = float(data.qpos[0]), float(data.qpos[1])
        hip_clearance = hip_z - self.ramp_height(hip_x)
        if hip_clearance < 0.22:
            return "fall_down"
        if hip_clearance > 2.5:
            return "fly_away"
        foot_margins = [
            self.site_margin("left_heel_site"),
            self.site_margin("left_toe_site"),
            self.site_margin("right_heel_site"),
            self.site_margin("right_toe_site"),
        ]
        if min(foot_margins) < -0.12:
            return "penetration"
        if t > 4.0 and hip_x - start_x < 0.20:
            return "stuck"
        return ""

    def reset(self) -> None:
        """Reset the simulation state."""
        self._data = mujoco.MjData(self.model)
        self.initialize()


__all__ = [
    "RollingFootParams",
    "RollingFootGait",
]
