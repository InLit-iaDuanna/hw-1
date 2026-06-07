"""V18 3D 模型生成器：在 V10 基础上加入侧向 DOF。

新增：hip_y (slide), hip_roll (hinge), left/right_hip_abd (hinge w/ passive spring),
      lateral foot capsules, condim=4 friction model.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODEL_DIR = ROOT / "out" / "v18_models"
MODEL_PATH = MODEL_DIR / "lateral_3d_walker.xml"


@dataclass(frozen=True)
class Lateral3DParams:
    slope_deg: float = 0.0
    foot_radius: float = 0.042
    foot_length: float = 0.12
    toe_radius: float = 0.028
    ankle_limit_deg: float = 25.0
    ankle_damping: float = 0.08
    ankle_stiffness: float = 10.0
    friction: float = 1.35
    friction_lateral: float = 0.5
    hip_mass: float = 5.0
    torso_mass: float = 0.05
    torso_height: float = 0.30
    initial_vx: float = 0.03
    knee_limit_deg: float = 70.0
    duration: float = 10.0
    timestep: float = 0.001
    thigh_length: float = 0.4896
    shank_length: float = 0.5304
    step_length: float = 0.3468
    knee_damping: float = 0.08
    knee_stiffness: float = 0.8
    hip_joint_damping: float = 0.02
    joint_damping: float = 0.01
    release_phase: float = 0.08
    swing_foot_x: float = 0.38
    swing_foot_clearance: float = 0.12
    swing_hip_vel: float = 0.10
    swing_knee_vel: float = -0.04
    hip_torque_limit: float = 4.0
    knee_torque_limit: float = 4.0
    hip_kp: float = 30.0
    hip_kd: float = 6.0
    knee_kp: float = 16.0
    knee_kd: float = 2.0
    gait_period: float = 0.80
    swing_back_deg: float = 20.0
    swing_front_deg: float = -22.0
    stance_front_deg: float = -14.0
    stance_back_deg: float = 22.0
    swing_knee_flex_deg: float = 28.0
    stance_knee_deg: float = 2.0
    recovery_clearance: float = 0.38
    min_event_interval: float = 0.22
    stable_contact_time: float = 0.035
    # --- V18 3D 新增 ---
    hip_abd_stiffness: float = 20.0
    hip_abd_damping: float = 2.0
    hip_abd_range_deg: float = 15.0
    hip_roll_damping: float = 0.5
    hip_roll_stiffness: float = 50.0
    foot_lateral_width: float = 0.04
    init_hip_y: float = 0.0
    init_hip_roll_deg: float = 3.0
    hip_lateral_offset: float = 0.055

    @property
    def gamma(self) -> float:
        return math.radians(self.slope_deg)

    @property
    def leg_length(self) -> float:
        return self.thigh_length + self.shank_length


def build_3d_model_xml(p: Lateral3DParams) -> str:
    ctrl_limit = max(p.hip_torque_limit, p.knee_torque_limit, 1.0)
    flw = p.foot_lateral_width
    sole_r = p.foot_radius * 0.55
    return f"""<mujoco model="lateral_3d_walker_v18">
  <compiler angle="degree" coordinate="local"/>
  <option timestep="{p.timestep}" integrator="implicitfast" gravity="0 0 -9.81"/>
  <visual><global offwidth="1280" offheight="720"/></visual>
  <default>
    <joint armature="0.004" damping="{p.joint_damping}"/>
    <geom condim="3" friction="{p.friction} 0.04 0.004" solref="0.006 1" solimp="0.90 0.98 0.002"/>
  </default>
  <asset>
    <texture name="grid" type="2d" builtin="checker" rgb1="0.80 0.87 0.84" rgb2="0.96 0.94 0.88" width="512" height="512"/>
    <material name="ramp_mat" texture="grid" texrepeat="12 4" rgba="0.76 0.82 0.78 1"/>
    <material name="left_mat" rgba="0.05 0.47 0.57 1"/>
    <material name="right_mat" rgba="0.86 0.29 0.21 1"/>
    <material name="hip_mat" rgba="0.08 0.12 0.20 1"/>
    <material name="knee_mat" rgba="0.95 0.74 0.36 1"/>
    <material name="foot_mat" rgba="0.08 0.08 0.08 1"/>
  </asset>
  <worldbody>
    <light name="key" pos="-2 -3 5" dir="0.3 0.5 -1" diffuse="0.85 0.85 0.85"/>
    <geom name="ramp" type="plane" pos="0 0 0" euler="0 {p.slope_deg} 0" size="45 3.0 0.08" material="ramp_mat" contype="1" conaffinity="1"/>
    <body name="hip" pos="0 0 0">
      <joint name="hip_x" type="slide" axis="1 0 0" damping="0.001"/>
      <joint name="hip_y" type="slide" axis="0 1 0" damping="0.001"/>
      <joint name="hip_z" type="slide" axis="0 0 1" damping="0.001"/>
      <joint name="hip_roll" type="hinge" axis="1 0 0" damping="{p.hip_roll_damping}" stiffness="{p.hip_roll_stiffness}" springref="0"/>
      <geom name="hip_mass" type="sphere" size="0.08" mass="{p.hip_mass}" material="hip_mat" contype="0" conaffinity="0"/>
      <geom name="torso_mass" type="capsule" fromto="0 0 0.02 0 0 {p.torso_height}" size="0.04" mass="{p.torso_mass}" material="hip_mat" contype="0" conaffinity="0"/>
      <geom name="hip_axis" type="cylinder" fromto="0 -0.13 0 0 0.13 0" size="0.018" mass="0.05" material="hip_mat" contype="0" conaffinity="0"/>
      <body name="left_abd" pos="0 -{p.hip_lateral_offset} 0">
        <joint name="left_hip_abd" type="hinge" axis="1 0 0" range="-{p.hip_abd_range_deg} {p.hip_abd_range_deg}" limited="true" stiffness="{p.hip_abd_stiffness}" damping="{p.hip_abd_damping}" springref="0"/>
        <geom name="left_abd_mass" type="sphere" size="0.01" mass="0.01" contype="0" conaffinity="0" rgba="0 0 0 0"/>
        <body name="left_thigh" pos="0 0 0">
          <joint name="left_hip" type="hinge" axis="0 1 0" range="-95 95" limited="true" damping="{p.hip_joint_damping}"/>
          <geom name="left_upper" type="capsule" fromto="0 0 0 0 0 -{p.thigh_length}" size="0.026" mass="0.18" material="left_mat" contype="0" conaffinity="0"/>
          <body name="left_shank" pos="0 0 -{p.thigh_length}">
            <joint name="left_knee" type="hinge" axis="0 1 0" range="0 {p.knee_limit_deg}" limited="true" damping="{p.knee_damping}" stiffness="{p.knee_stiffness}" springref="0"/>
            <geom name="left_knee_marker" type="sphere" pos="0 0 0" size="0.04" mass="0.03" material="knee_mat" contype="0" conaffinity="0"/>
            <geom name="left_lower" type="capsule" fromto="0 0 0 0 0 -{p.shank_length}" size="0.023" mass="0.16" material="left_mat" contype="0" conaffinity="0"/>
            <body name="left_foot_body" pos="0 0 -{p.shank_length}">
              <joint name="left_ankle" type="hinge" axis="0 1 0" range="-{p.ankle_limit_deg} {p.ankle_limit_deg}" limited="true" damping="{p.ankle_damping}" stiffness="{p.ankle_stiffness}" springref="0"/>
              <geom name="left_sole" type="capsule" fromto="-{p.foot_length*0.45} 0 -0.015 {p.foot_length*0.35} 0 -0.015" size="{sole_r}" mass="0.06" material="foot_mat" contype="1" conaffinity="1"/>
              <geom name="left_sole_lat" type="capsule" fromto="0 -{flw} -0.015 0 {flw} -0.015" size="{sole_r}" mass="0.02" material="foot_mat" contype="1" conaffinity="1"/>
              <geom name="left_heel" type="sphere" pos="-{p.foot_length*0.50} 0 -0.015" size="{p.foot_radius}" mass="0.025" material="foot_mat" contype="1" conaffinity="1"/>
              <geom name="left_toe" type="sphere" pos="{p.foot_length*0.48} 0 -0.018" size="{p.toe_radius}" mass="0.025" material="foot_mat" contype="1" conaffinity="1"/>
              <site name="left_foot_site" pos="0 0 -0.015" size="0.01"/>
            </body>
          </body>
        </body>
      </body>
      <body name="right_abd" pos="0 {p.hip_lateral_offset} 0">
        <joint name="right_hip_abd" type="hinge" axis="1 0 0" range="-{p.hip_abd_range_deg} {p.hip_abd_range_deg}" limited="true" stiffness="{p.hip_abd_stiffness}" damping="{p.hip_abd_damping}" springref="0"/>
        <geom name="right_abd_mass" type="sphere" size="0.01" mass="0.01" contype="0" conaffinity="0" rgba="0 0 0 0"/>
        <body name="right_thigh" pos="0 0 0">
          <joint name="right_hip" type="hinge" axis="0 1 0" range="-95 95" limited="true" damping="{p.hip_joint_damping}"/>
          <geom name="right_upper" type="capsule" fromto="0 0 0 0 0 -{p.thigh_length}" size="0.026" mass="0.18" material="right_mat" contype="0" conaffinity="0"/>
          <body name="right_shank" pos="0 0 -{p.thigh_length}">
            <joint name="right_knee" type="hinge" axis="0 1 0" range="0 {p.knee_limit_deg}" limited="true" damping="{p.knee_damping}" stiffness="{p.knee_stiffness}" springref="0"/>
            <geom name="right_knee_marker" type="sphere" pos="0 0 0" size="0.04" mass="0.03" material="knee_mat" contype="0" conaffinity="0"/>
            <geom name="right_lower" type="capsule" fromto="0 0 0 0 0 -{p.shank_length}" size="0.023" mass="0.16" material="right_mat" contype="0" conaffinity="0"/>
            <body name="right_foot_body" pos="0 0 -{p.shank_length}">
              <joint name="right_ankle" type="hinge" axis="0 1 0" range="-{p.ankle_limit_deg} {p.ankle_limit_deg}" limited="true" damping="{p.ankle_damping}" stiffness="{p.ankle_stiffness}" springref="0"/>
              <geom name="right_sole" type="capsule" fromto="-{p.foot_length*0.45} 0 -0.015 {p.foot_length*0.35} 0 -0.015" size="{sole_r}" mass="0.06" material="foot_mat" contype="1" conaffinity="1"/>
              <geom name="right_sole_lat" type="capsule" fromto="0 -{flw} -0.015 0 {flw} -0.015" size="{sole_r}" mass="0.02" material="foot_mat" contype="1" conaffinity="1"/>
              <geom name="right_heel" type="sphere" pos="-{p.foot_length*0.50} 0 -0.015" size="{p.foot_radius}" mass="0.025" material="foot_mat" contype="1" conaffinity="1"/>
              <geom name="right_toe" type="sphere" pos="{p.foot_length*0.48} 0 -0.018" size="{p.toe_radius}" mass="0.025" material="foot_mat" contype="1" conaffinity="1"/>
              <site name="right_foot_site" pos="0 0 -0.015" size="0.01"/>
            </body>
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


def write_model(p: Lateral3DParams, path: Path = MODEL_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_3d_model_xml(p), encoding="utf-8")
