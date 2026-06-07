"""V14 被动摆臂仿真。

设计：在 V10 滚动足模型的 hip body 上挂两根 capsule 作为被动摆臂。
- 摆臂用 hinge joint，**无 actuator**：纯被动绕肩 pivot 摆动，靠惯性 / 重力反相位补偿。
- 关节 qpos 顺序保持与 V10 完全兼容（前 8 个），arm 关节追加在末尾 [8..9]，
  这样 V10 的控制律 (`control()` 中的 qpos 索引 2/3/5/6) 不必修改。

学术诚信：摆臂本身被动，但 hip+knee 仍主动 PD 控制，因此整机仍属**准被动**
（与 V08-V11 同档），不可宣称"纯被动"。控制律继承自 V10 baseline，已在
V13 决策门报告中标记为 (kp, kd) 平面孤立点解，本版本作为机构变化对孤立点
稳定性的扰动测试，失败如实报告。
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

import mujoco
import numpy as np

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "out"
MODEL_DIR = ROOT / "models"
MODEL_PATH = MODEL_DIR / "passive_arms_walker.xml"
QPOS_KEYS = [
    "hip_x",
    "hip_z",
    "left_hip",
    "left_knee",
    "left_ankle",
    "right_hip",
    "right_knee",
    "right_ankle",
    "left_arm",
    "right_arm",
]
QVEL_KEYS = [f"{k}_vel" for k in QPOS_KEYS]
SUCCESS_TIME = 10.0
SUCCESS_TOUCHDOWNS = 10
SUCCESS_FORWARD = 0.8


@dataclass(frozen=True)
class PassiveArmsParams:
    # ---- 继承自 V10 best (v10_best_params.json) ----
    slope_deg: float = 0.0
    foot_radius: float = 0.04
    foot_length: float = 0.12
    toe_radius: float = 0.028
    ankle_limit_deg: float = 25.0
    ankle_damping: float = 0.08
    ankle_stiffness: float = 10.0
    friction: float = 1.35
    hip_mass: float = 5.0
    torso_mass: float = 0.05
    torso_height: float = 0.30
    initial_vx: float = 0.03
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

    # ---- V14 新增：被动摆臂 ----
    arm_length: float = 0.40  # m，肩 pivot → 手末端
    arm_mass: float = 0.30  # kg，单臂质量
    arm_shoulder_z: float = 0.20  # m，肩 pivot 在 hip 之上的高度
    arm_lateral: float = 0.13  # m，肩 pivot 侧向偏移（与肩宽一致）
    arm_limit_deg: float = 70.0  # 摆臂角度限位
    arm_damping: float = 0.02  # N·m·s/rad，被动阻尼
    arm_stiffness: float = 0.0  # N·m/rad，0 = 纯被动重力摆，>0 = 含恢复弹簧
    arm_radius: float = 0.022  # 视觉 capsule 半径
    arm_init_deg: float = 0.0  # 初始相位

    @property
    def gamma(self) -> float:
        return math.radians(self.slope_deg)

    @property
    def leg_length(self) -> float:
        return self.thigh_length + self.shank_length

    @property
    def total_mass(self) -> float:
        # hip + torso + 2 thigh + 2 shank + 2 foot(sole+heel+toe) + knee marker + 2 arm
        return (
            self.hip_mass
            + self.torso_mass
            + 0.05
            + 2 * (0.18 + 0.16 + 0.06 + 0.025 + 0.025 + 0.03)
            + 2 * self.arm_mass
        )


def ramp_height(x: float, p: PassiveArmsParams) -> float:
    return -math.tan(p.gamma) * x


def foot_center_z_on_ramp(x: float, p: PassiveArmsParams) -> float:
    return ramp_height(x, p) + p.foot_radius / max(0.2, math.cos(p.gamma))


def smoothstep(u: float) -> float:
    u = min(max(u, 0.0), 1.0)
    return u * u * (3.0 - 2.0 * u)


def leg_ik_front_knee(hip_x, hip_z, foot_x, foot_z, p: PassiveArmsParams):
    px = hip_x - foot_x
    pz = hip_z - foot_z
    d = math.hypot(px, pz)
    d = float(
        np.clip(d, abs(p.thigh_length - p.shank_length) + 1e-5, p.leg_length - 1e-5)
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


def build_model_xml(p: PassiveArmsParams) -> str:
    ctrl_limit = max(p.hip_torque_limit, p.knee_torque_limit, 1.0)
    arm_half = p.arm_length
    return f"""<mujoco model="passive_arms_walker_v14">
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
    <material name="arm_left_mat" rgba="0.20 0.55 0.65 1"/>
    <material name="arm_right_mat" rgba="0.85 0.45 0.35 1"/>
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
      <body name="left_arm" pos="0 -{p.arm_lateral} {p.arm_shoulder_z}">
        <joint name="left_arm" type="hinge" axis="0 1 0" range="-{p.arm_limit_deg} {p.arm_limit_deg}" limited="true" damping="{p.arm_damping}" stiffness="{p.arm_stiffness}" springref="0"/>
        <geom name="left_arm_geom" type="capsule" fromto="0 0 0 0 0 -{arm_half}" size="{p.arm_radius}" mass="{p.arm_mass}" material="arm_left_mat" contype="0" conaffinity="0"/>
      </body>
      <body name="right_arm" pos="0 {p.arm_lateral} {p.arm_shoulder_z}">
        <joint name="right_arm" type="hinge" axis="0 1 0" range="-{p.arm_limit_deg} {p.arm_limit_deg}" limited="true" damping="{p.arm_damping}" stiffness="{p.arm_stiffness}" springref="0"/>
        <geom name="right_arm_geom" type="capsule" fromto="0 0 0 0 0 -{arm_half}" size="{p.arm_radius}" mass="{p.arm_mass}" material="arm_right_mat" contype="0" conaffinity="0"/>
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


def write_model(p: PassiveArmsParams, path: Path = MODEL_PATH) -> None:
    MODEL_DIR.mkdir(exist_ok=True)
    path.write_text(build_model_xml(p), encoding="utf-8")


def initialize(model, data, p: PassiveArmsParams) -> None:
    u = smoothstep(p.release_phase)
    alpha = math.asin(p.step_length / (2.0 * p.leg_length))
    support_x = 0.0
    support_z = foot_center_z_on_ramp(support_x, p)
    left_hip = p.gamma + alpha - 2.0 * alpha * u
    hip_x = support_x + p.leg_length * math.sin(left_hip)
    hip_z = support_z + p.leg_length * math.cos(left_hip)
    right_hip, right_knee = leg_ik_front_knee(
        hip_x,
        hip_z,
        p.swing_foot_x,
        foot_center_z_on_ramp(p.swing_foot_x, p) + p.swing_foot_clearance,
        p,
    )
    arm_init = math.radians(p.arm_init_deg)
    # qpos 顺序：hip_x, hip_z, left_hip, left_knee, left_ankle,
    #            right_hip, right_knee, right_ankle, left_arm, right_arm
    data.qpos[:] = [
        hip_x,
        hip_z,
        left_hip,
        0.0,
        0.0,
        right_hip,
        right_knee,
        0.0,
        -arm_init,
        arm_init,
    ]
    data.qvel[:] = [
        p.initial_vx,
        -math.tan(p.gamma) * p.initial_vx,
        0.04,
        0.0,
        0.0,
        p.swing_hip_vel,
        p.swing_knee_vel,
        0.0,
        0.0,
        0.0,
    ]
    data.ctrl[:] = 0.0
    mujoco.mj_forward(model, data)


def foot_contact_detail(model, data) -> dict[str, bool]:
    ramp = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "ramp")
    names = [
        "left_heel",
        "left_sole",
        "left_toe",
        "right_heel",
        "right_sole",
        "right_toe",
    ]
    geom_ids = {n: mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, n) for n in names}
    detail = dict.fromkeys(names, False)
    for i in range(data.ncon):
        pair = {data.contact[i].geom1, data.contact[i].geom2}
        if ramp in pair:
            for n, gid in geom_ids.items():
                if gid in pair:
                    detail[n] = True
    return detail


def contact_flags(model, data) -> tuple[bool, bool]:
    d = foot_contact_detail(model, data)
    return (
        d["left_heel"] or d["left_sole"] or d["left_toe"],
        d["right_heel"] or d["right_sole"] or d["right_toe"],
    )


def site_margin(model, data, site_name: str, p: PassiveArmsParams) -> float:
    sid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, site_name)
    pos = data.site_xpos[sid]
    return float(pos[2] - foot_center_z_on_ramp(float(pos[0]), p))


def actuator_names(model) -> list[str]:
    return [
        mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_ACTUATOR, i) or f"a{i}"
        for i in range(model.nu)
    ]


def limited_pd(q, qd, target, kp, kd, limit) -> float:
    return float(np.clip(kp * (target - q) - kd * qd, -limit, limit))


def control(
    p: PassiveArmsParams, data, t: float, support_foot: str, burst_start_t: float
):
    """继承自 V10：摆臂被动，不参与控制，因此与 V10 控制律一致。"""
    hip_x = float(data.qpos[0])
    hip_z = float(data.qpos[1])
    clearance = hip_z - ramp_height(hip_x, p)
    mode = "left_stance" if support_foot == "left" else "right_stance"
    u = min(max((t - burst_start_t) / max(p.gait_period, 1e-6), 0.0), 1.0)
    if clearance < p.recovery_clearance:
        u = min(u, 0.55)
        mode = "recovery"
    s = smoothstep(u)
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
    lh_t = stance_target if left_is_support else swing_target
    rh_t = stance_target if not left_is_support else swing_target
    lk_t = stance_knee if left_is_support else swing_knee
    rk_t = stance_knee if not left_is_support else swing_knee

    lh = limited_pd(
        float(data.qpos[2]),
        float(data.qvel[2]),
        lh_t,
        p.hip_kp,
        p.hip_kd,
        p.hip_torque_limit,
    )
    lk = limited_pd(
        float(data.qpos[3]),
        float(data.qvel[3]),
        lk_t,
        p.knee_kp,
        p.knee_kd,
        p.knee_torque_limit,
    )
    rh = limited_pd(
        float(data.qpos[5]),
        float(data.qvel[5]),
        rh_t,
        p.hip_kp,
        p.hip_kd,
        p.hip_torque_limit,
    )
    rk = limited_pd(
        float(data.qpos[6]),
        float(data.qvel[6]),
        rk_t,
        p.knee_kp,
        p.knee_kd,
        p.knee_torque_limit,
    )
    return lh, lk, rh, rk, mode


def classify_failure(
    model, data, p: PassiveArmsParams, start_x: float, t: float
) -> str:
    if not np.all(np.isfinite(data.qpos)) or not np.all(np.isfinite(data.qvel)):
        return "nan_or_unstable"
    if float(np.linalg.norm(data.qvel)) > 45.0:
        return "nan_or_unstable"
    hip_x, hip_z = float(data.qpos[0]), float(data.qpos[1])
    hc = hip_z - ramp_height(hip_x, p)
    if hc < 0.22:
        return "fall_down"
    if hc > 2.5:
        return "fly_away"
    foot_margins = [
        site_margin(model, data, "left_heel_site", p),
        site_margin(model, data, "left_toe_site", p),
        site_margin(model, data, "right_heel_site", p),
        site_margin(model, data, "right_toe_site", p),
    ]
    if min(foot_margins) < -0.12:
        return "penetration"
    if t > 4.0 and hip_x - start_x < 0.20:
        return "stuck"
    return ""


def make_row(
    model, data, p: PassiveArmsParams, t, lc, rc, support, mode, tau, in_p, in_e
):
    out: dict[str, float | int | str] = {"time": t}
    for k, v in zip(QPOS_KEYS, data.qpos):
        out[k] = float(v)
    for k, v in zip(QVEL_KEYS, data.qvel):
        out[k] = float(v)
    d = foot_contact_detail(model, data)
    out.update(
        {
            "left_contact": int(lc),
            "right_contact": int(rc),
            "left_heel_contact": int(d["left_heel"]),
            "left_sole_contact": int(d["left_sole"]),
            "left_toe_contact": int(d["left_toe"]),
            "right_heel_contact": int(d["right_heel"]),
            "right_sole_contact": int(d["right_sole"]),
            "right_toe_contact": int(d["right_toe"]),
            "support_foot": support,
            "mode": mode,
            "left_margin": site_margin(model, data, "left_foot_site", p),
            "right_margin": site_margin(model, data, "right_foot_site", p),
            "left_heel_margin": site_margin(model, data, "left_heel_site", p),
            "left_toe_margin": site_margin(model, data, "left_toe_site", p),
            "right_heel_margin": site_margin(model, data, "right_heel_site", p),
            "right_toe_margin": site_margin(model, data, "right_toe_site", p),
            "hip_clearance": float(data.qpos[1]) - ramp_height(float(data.qpos[0]), p),
            "left_hip_tau": tau[0],
            "left_knee_tau": tau[1],
            "left_ankle_tau": 0.0,
            "right_hip_tau": tau[2],
            "right_knee_tau": tau[3],
            "right_ankle_tau": 0.0,
            "left_arm_tau": 0.0,
            "right_arm_tau": 0.0,
            "input_power": in_p,
            "input_energy": in_e,
        }
    )
    return out


def run_simulation(
    p: PassiveArmsParams, save_prefix: str | None = None, sample_hz: float = 120.0
):
    write_model(p)
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    data = mujoco.MjData(model)
    initialize(model, data, p)

    start_x = float(data.qpos[0])
    max_x = start_x
    support_foot = "left"
    accepted_contact = ""
    candidate_start_t: dict[str, float | None] = {"left": None, "right": None}
    contact_reported = {"left": False, "right": False}
    last_event_t = -1.0
    burst_start_t = -p.gait_period
    alternations = 0
    contact_events: list[dict] = []
    pos_in_e = 0.0
    net_work = 0.0
    rows: list[dict] = []
    failure = ""
    mode = "left_stance"
    sample_stride = max(1, int(round(1.0 / (p.timestep * sample_hz))))

    n_steps = int(p.duration / p.timestep)
    for step in range(n_steps):
        t = step * p.timestep
        tau = control(p, data, t, support_foot, burst_start_t)
        data.ctrl[:] = tau[:4]
        in_p = (
            float(data.ctrl[0]) * float(data.qvel[2])
            + float(data.ctrl[1]) * float(data.qvel[3])
            + float(data.ctrl[2]) * float(data.qvel[5])
            + float(data.ctrl[3]) * float(data.qvel[6])
        )
        pos_in_e += max(0.0, in_p) * p.timestep
        net_work += in_p * p.timestep
        mode = str(tau[4])

        mujoco.mj_step(model, data)
        lc, rc = contact_flags(model, data)
        max_x = max(max_x, float(data.qpos[0]))

        for foot, has in (("left", lc), ("right", rc)):
            if has:
                if candidate_start_t[foot] is None:
                    candidate_start_t[foot] = t
                    contact_reported[foot] = False
                if t - float(candidate_start_t[foot]) >= p.stable_contact_time:
                    if (
                        not contact_reported[foot]
                        and foot != accepted_contact
                        and t - last_event_t > p.min_event_interval
                    ):
                        if accepted_contact in {"left", "right"}:
                            alternations += 1
                        accepted_contact = foot
                        support_foot = foot
                        burst_start_t = t
                        last_event_t = t
                        contact_reported[foot] = True
                        contact_events.append({"time": t, "foot": foot})
                        break
            else:
                candidate_start_t[foot] = None
                contact_reported[foot] = False

        if step % sample_stride == 0:
            rows.append(
                make_row(
                    model,
                    data,
                    p,
                    t,
                    lc,
                    rc,
                    support_foot,
                    mode,
                    tau[:4],
                    in_p,
                    pos_in_e,
                )
            )

        failure = classify_failure(model, data, p, start_x, t)
        if failure:
            break

    if not rows:
        lc, rc = contact_flags(model, data)
        rows.append(
            make_row(
                model,
                data,
                p,
                0.0,
                lc,
                rc,
                support_foot,
                mode,
                (0, 0, 0, 0),
                0.0,
                pos_in_e,
            )
        )

    sim_t = float(rows[-1]["time"])
    forward = max_x - start_x
    success = (
        sim_t >= SUCCESS_TIME
        and alternations >= SUCCESS_TOUCHDOWNS
        and forward >= SUCCESS_FORWARD
        and not failure
    )
    score = alternations * 200.0 + sim_t * 80.0 + forward * 60.0 - 3.0 * pos_in_e
    if success:
        score += 2000.0
    if failure:
        score -= 300.0
    if failure in {"nan_or_unstable", "fly_away", "penetration"}:
        score -= 500.0

    summary = {
        "params": asdict(p),
        "score": score,
        "success": success,
        "success_criteria": {
            "simulated_time_s": SUCCESS_TIME,
            "alternating_touchdowns": SUCCESS_TOUCHDOWNS,
            "forward_distance_m": SUCCESS_FORWARD,
            "must_complete_without_failure": True,
        },
        "alternating_touchdowns": alternations,
        "contact_events": contact_events,
        "forward_distance": forward,
        "simulated_time": sim_t,
        "failure": failure or "completed",
        "actuator_count": int(model.nu),
        "actuator_names": actuator_names(model),
        "knee_actuators": ["left_knee_stabilizer", "right_knee_stabilizer"],
        "ankle_actuators": [],
        "arm_actuators": [],
        "active_input_energy_j": pos_in_e,
        "net_actuator_work_j": net_work,
        "energy_per_alternation_j": pos_in_e / max(1, alternations),
        "total_mass_kg": p.total_mass,
        "quasi_passive": True,
        "pure_passive": False,
        "passive_arms": True,
        "uses_reward_function": False,
    }

    if save_prefix:
        OUT_DIR.mkdir(exist_ok=True)
        with (OUT_DIR / f"{save_prefix}_data.csv").open(
            "w", newline="", encoding="utf-8"
        ) as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        (OUT_DIR / f"{save_prefix}_summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return rows, summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=float, default=12.0)
    parser.add_argument("--slope", type=float, default=0.0)
    parser.add_argument("--arm-mass", type=float, default=0.30)
    parser.add_argument("--arm-length", type=float, default=0.40)
    parser.add_argument("--arm-damping", type=float, default=0.02)
    parser.add_argument("--prefix", type=str, default="v14_single")
    args = parser.parse_args()
    params = PassiveArmsParams(
        duration=args.duration,
        slope_deg=args.slope,
        arm_mass=args.arm_mass,
        arm_length=args.arm_length,
        arm_damping=args.arm_damping,
    )
    _, summary = run_simulation(params, save_prefix=args.prefix)
    print(
        json.dumps(
            {k: v for k, v in summary.items() if k != "params"},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
