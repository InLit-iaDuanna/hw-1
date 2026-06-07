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
MODEL_PATH = MODEL_DIR / "stable_kneed_walker.xml"
QPOS_KEYS = ["hip_x", "hip_z", "left_hip", "left_knee", "right_hip", "right_knee"]
QVEL_KEYS = [f"{key}_vel" for key in QPOS_KEYS]
SUCCESS_TIME = 10.0
SUCCESS_TOUCHDOWNS = 10
SUCCESS_FORWARD = 0.8


@dataclass(frozen=True)
class StableParams:
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

    @property
    def gamma(self) -> float:
        return math.radians(self.slope_deg)

    @property
    def leg_length(self) -> float:
        return self.thigh_length + self.shank_length


def ramp_height(x: float, params: StableParams) -> float:
    return -math.tan(params.gamma) * x


def foot_center_z_on_ramp(x: float, params: StableParams) -> float:
    return ramp_height(x, params) + params.foot_radius / max(
        0.2, math.cos(params.gamma)
    )


def smoothstep(u: float) -> float:
    u = min(max(u, 0.0), 1.0)
    return u * u * (3.0 - 2.0 * u)


def leg_ik_front_knee(
    hip_x: float, hip_z: float, foot_x: float, foot_z: float, params: StableParams
) -> tuple[float, float]:
    px = hip_x - foot_x
    pz = hip_z - foot_z
    d = math.hypot(px, pz)
    d = float(
        np.clip(
            d,
            abs(params.thigh_length - params.shank_length) + 1e-5,
            params.leg_length - 1e-5,
        )
    )
    base = math.atan2(px, pz)
    cos_delta = (params.thigh_length**2 + d**2 - params.shank_length**2) / (
        2.0 * params.thigh_length * d
    )
    delta = math.acos(float(np.clip(cos_delta, -1.0, 1.0)))
    thigh = base - delta
    knee_x = hip_x - params.thigh_length * math.sin(thigh)
    knee_z = hip_z - params.thigh_length * math.cos(thigh)
    shank = math.atan2(knee_x - foot_x, knee_z - foot_z)
    knee = float(np.clip(shank - thigh, 0.0, math.radians(params.knee_limit_deg)))
    return thigh, knee


def build_model_xml(params: StableParams) -> str:
    ctrl_limit = max(params.hip_torque_limit, params.knee_torque_limit, 1.0)
    return f"""<mujoco model="stable_kneed_walker_v9">
  <compiler angle="degree" coordinate="local"/>
  <option timestep="{params.timestep}" integrator="implicitfast" gravity="0 0 -9.81"/>
  <visual><global offwidth="1280" offheight="720"/></visual>
  <default>
    <joint armature="0.004" damping="{params.joint_damping}"/>
    <geom condim="3" friction="{params.friction} 0.04 0.004" solref="0.006 1" solimp="0.90 0.98 0.002"/>
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
    <geom name="ramp" type="plane" pos="0 0 0" euler="0 {params.slope_deg} 0" size="45 1.8 0.08" material="ramp_mat" contype="1" conaffinity="1"/>
    <body name="hip" pos="0 0 0">
      <joint name="hip_x" type="slide" axis="1 0 0" damping="0.001"/>
      <joint name="hip_z" type="slide" axis="0 0 1" damping="0.001"/>
      <geom name="hip_mass" type="sphere" size="0.08" mass="{params.hip_mass}" material="hip_mat" contype="0" conaffinity="0"/>
      <geom name="torso_mass" type="capsule" fromto="0 0 0.02 0 0 {params.torso_height}" size="0.04" mass="{params.torso_mass}" material="hip_mat" contype="0" conaffinity="0"/>
      <geom name="hip_axis" type="cylinder" fromto="0 -0.13 0 0 0.13 0" size="0.018" mass="0.05" material="hip_mat" contype="0" conaffinity="0"/>
      <body name="left_thigh" pos="0 -0.055 0">
        <joint name="left_hip" type="hinge" axis="0 1 0" range="-95 95" limited="true" damping="{params.hip_joint_damping}"/>
        <geom name="left_upper" type="capsule" fromto="0 0 0 0 0 -{params.thigh_length}" size="0.026" mass="0.18" material="left_mat" contype="0" conaffinity="0"/>
        <body name="left_shank" pos="0 0 -{params.thigh_length}">
          <joint name="left_knee" type="hinge" axis="0 1 0" range="0 {params.knee_limit_deg}" limited="true" damping="{params.knee_damping}" stiffness="{params.knee_stiffness}" springref="0"/>
          <geom name="left_knee_marker" type="sphere" pos="0 0 0" size="0.04" mass="0.03" material="knee_mat" contype="0" conaffinity="0"/>
          <geom name="left_lower" type="capsule" fromto="0 0 0 0 0 -{params.shank_length}" size="0.023" mass="0.16" material="left_mat" contype="0" conaffinity="0"/>
          <geom name="left_foot" type="capsule" fromto="-{params.foot_length / 2.0} 0 -{params.shank_length} {params.foot_length / 2.0} 0 -{params.shank_length}" size="{params.foot_radius}" mass="0.08" material="foot_mat" contype="1" conaffinity="1"/>
          <site name="left_foot_site" pos="0 0 -{params.shank_length}" size="0.01"/>
        </body>
      </body>
      <body name="right_thigh" pos="0 0.055 0">
        <joint name="right_hip" type="hinge" axis="0 1 0" range="-95 95" limited="true" damping="{params.hip_joint_damping}"/>
        <geom name="right_upper" type="capsule" fromto="0 0 0 0 0 -{params.thigh_length}" size="0.026" mass="0.18" material="right_mat" contype="0" conaffinity="0"/>
        <body name="right_shank" pos="0 0 -{params.thigh_length}">
          <joint name="right_knee" type="hinge" axis="0 1 0" range="0 {params.knee_limit_deg}" limited="true" damping="{params.knee_damping}" stiffness="{params.knee_stiffness}" springref="0"/>
          <geom name="right_knee_marker" type="sphere" pos="0 0 0" size="0.04" mass="0.03" material="knee_mat" contype="0" conaffinity="0"/>
          <geom name="right_lower" type="capsule" fromto="0 0 0 0 0 -{params.shank_length}" size="0.023" mass="0.16" material="right_mat" contype="0" conaffinity="0"/>
          <geom name="right_foot" type="capsule" fromto="-{params.foot_length / 2.0} 0 -{params.shank_length} {params.foot_length / 2.0} 0 -{params.shank_length}" size="{params.foot_radius}" mass="0.08" material="foot_mat" contype="1" conaffinity="1"/>
          <site name="right_foot_site" pos="0 0 -{params.shank_length}" size="0.01"/>
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


def write_model(params: StableParams, path: Path = MODEL_PATH) -> None:
    MODEL_DIR.mkdir(exist_ok=True)
    path.write_text(build_model_xml(params), encoding="utf-8")


def initialize(
    model: mujoco.MjModel, data: mujoco.MjData, params: StableParams
) -> None:
    u = smoothstep(params.release_phase)
    alpha = math.asin(params.step_length / (2.0 * params.leg_length))
    support_x = 0.0
    support_z = foot_center_z_on_ramp(support_x, params)
    left_hip = params.gamma + alpha - 2.0 * alpha * u
    hip_x = support_x + params.leg_length * math.sin(left_hip)
    hip_z = support_z + params.leg_length * math.cos(left_hip)
    right_hip, right_knee = leg_ik_front_knee(
        hip_x,
        hip_z,
        params.swing_foot_x,
        foot_center_z_on_ramp(params.swing_foot_x, params)
        + params.swing_foot_clearance,
        params,
    )
    data.qpos[:] = [hip_x, hip_z, left_hip, 0.0, right_hip, right_knee]
    data.qvel[:] = [
        params.initial_vx,
        -math.tan(params.gamma) * params.initial_vx,
        0.04,
        0.0,
        params.swing_hip_vel,
        params.swing_knee_vel,
    ]
    data.ctrl[:] = 0.0
    mujoco.mj_forward(model, data)


def contact_flags(model: mujoco.MjModel, data: mujoco.MjData) -> tuple[bool, bool]:
    ramp = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "ramp")
    left = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "left_foot")
    right = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "right_foot")
    left_contact = False
    right_contact = False
    for i in range(data.ncon):
        pair = {data.contact[i].geom1, data.contact[i].geom2}
        left_contact = left_contact or (ramp in pair and left in pair)
        right_contact = right_contact or (ramp in pair and right in pair)
    return left_contact, right_contact


def site_margin(
    model: mujoco.MjModel, data: mujoco.MjData, site_name: str, params: StableParams
) -> float:
    site_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, site_name)
    pos = data.site_xpos[site_id]
    return float(pos[2] - foot_center_z_on_ramp(float(pos[0]), params))


def actuator_names(model: mujoco.MjModel) -> list[str]:
    return [
        mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_ACTUATOR, i) or f"actuator_{i}"
        for i in range(model.nu)
    ]


def limited_pd(
    q: float, qd: float, target: float, kp: float, kd: float, limit: float
) -> float:
    return float(np.clip(kp * (target - q) - kd * qd, -limit, limit))


def control(
    params: StableParams,
    data: mujoco.MjData,
    t: float,
    support_foot: str,
    burst_start_t: float,
) -> tuple[float, float, float, float, str]:
    hip_x = float(data.qpos[0])
    hip_z = float(data.qpos[1])
    clearance = hip_z - ramp_height(hip_x, params)
    mode = "left_stance" if support_foot == "left" else "right_stance"
    u = min(max((t - burst_start_t) / max(params.gait_period, 1e-6), 0.0), 1.0)
    if clearance < params.recovery_clearance:
        u = min(u, 0.55)
        mode = "recovery"
    s = smoothstep(u)
    offset = params.gamma
    stance_target = offset + math.radians(
        params.stance_front_deg + (params.stance_back_deg - params.stance_front_deg) * s
    )
    swing_target = offset + math.radians(
        params.swing_back_deg + (params.swing_front_deg - params.swing_back_deg) * s
    )
    swing_knee = math.radians(params.swing_knee_flex_deg * math.sin(math.pi * u))
    stance_knee = math.radians(params.stance_knee_deg)

    left_is_support = support_foot == "left"
    left_hip_target = stance_target if left_is_support else swing_target
    right_hip_target = stance_target if not left_is_support else swing_target
    left_knee_target = stance_knee if left_is_support else swing_knee
    right_knee_target = stance_knee if not left_is_support else swing_knee

    left_hip_tau = limited_pd(
        float(data.qpos[2]),
        float(data.qvel[2]),
        left_hip_target,
        params.hip_kp,
        params.hip_kd,
        params.hip_torque_limit,
    )
    left_knee_tau = limited_pd(
        float(data.qpos[3]),
        float(data.qvel[3]),
        left_knee_target,
        params.knee_kp,
        params.knee_kd,
        params.knee_torque_limit,
    )
    right_hip_tau = limited_pd(
        float(data.qpos[4]),
        float(data.qvel[4]),
        right_hip_target,
        params.hip_kp,
        params.hip_kd,
        params.hip_torque_limit,
    )
    right_knee_tau = limited_pd(
        float(data.qpos[5]),
        float(data.qvel[5]),
        right_knee_target,
        params.knee_kp,
        params.knee_kd,
        params.knee_torque_limit,
    )
    return left_hip_tau, left_knee_tau, right_hip_tau, right_knee_tau, mode


def classify_failure(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    params: StableParams,
    start_x: float,
    t: float,
) -> str:
    if not np.all(np.isfinite(data.qpos)) or not np.all(np.isfinite(data.qvel)):
        return "nan_or_unstable"
    if float(np.linalg.norm(data.qvel)) > 45.0:
        return "nan_or_unstable"
    hip_x, hip_z = float(data.qpos[0]), float(data.qpos[1])
    hip_clearance = hip_z - ramp_height(hip_x, params)
    if hip_clearance < 0.22:
        return "fall_down"
    if hip_clearance > 2.5:
        return "fly_away"
    if (
        min(
            site_margin(model, data, "left_foot_site", params),
            site_margin(model, data, "right_foot_site", params),
        )
        < -0.10
    ):
        return "penetration"
    if t > 4.0 and hip_x - start_x < 0.20:
        return "stuck"
    return ""


def make_row(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    params: StableParams,
    t: float,
    left_contact: bool,
    right_contact: bool,
    support_foot: str,
    mode: str,
    tau: tuple[float, float, float, float],
    input_power: float,
    input_energy: float,
) -> dict[str, float | int | str]:
    out: dict[str, float | int | str] = {"time": t}
    for key, value in zip(QPOS_KEYS, data.qpos):
        out[key] = float(value)
    for key, value in zip(QVEL_KEYS, data.qvel):
        out[key] = float(value)
    out.update(
        {
            "left_contact": int(left_contact),
            "right_contact": int(right_contact),
            "support_foot": support_foot,
            "mode": mode,
            "left_margin": site_margin(model, data, "left_foot_site", params),
            "right_margin": site_margin(model, data, "right_foot_site", params),
            "hip_clearance": float(data.qpos[1])
            - ramp_height(float(data.qpos[0]), params),
            "left_hip_tau": tau[0],
            "left_knee_tau": tau[1],
            "right_hip_tau": tau[2],
            "right_knee_tau": tau[3],
            "input_power": input_power,
            "input_energy": input_energy,
        }
    )
    return out


def run_simulation(
    params: StableParams, save_prefix: str | None = None, sample_hz: float = 120.0
) -> tuple[list[dict[str, float | int | str]], dict]:
    write_model(params)
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    data = mujoco.MjData(model)
    initialize(model, data, params)

    start_x = float(data.qpos[0])
    max_x = start_x
    support_foot = "left"
    accepted_contact = ""
    candidate_start_t: dict[str, float | None] = {"left": None, "right": None}
    contact_reported = {"left": False, "right": False}
    last_event_t = -1.0
    burst_start_t = -params.gait_period
    alternations = 0
    contact_events: list[dict[str, float | str]] = []
    positive_input_energy = 0.0
    net_work = 0.0
    rows: list[dict[str, float | int | str]] = []
    failure = ""
    mode = "left_stance"
    sample_stride = max(1, int(round(1.0 / (params.timestep * sample_hz))))

    for step in range(int(params.duration / params.timestep)):
        t = step * params.timestep
        tau = control(params, data, t, support_foot, burst_start_t)
        data.ctrl[:] = tau[:4]
        input_power = sum(
            float(data.ctrl[i]) * float(data.qvel[2 + i]) for i in range(4)
        )
        positive_input_energy += max(0.0, input_power) * params.timestep
        net_work += input_power * params.timestep
        mode = str(tau[4])

        mujoco.mj_step(model, data)
        left_contact, right_contact = contact_flags(model, data)
        max_x = max(max_x, float(data.qpos[0]))

        contacts = {"left": left_contact, "right": right_contact}
        stable_feet: list[str] = []
        for foot, has_contact in contacts.items():
            if has_contact:
                if candidate_start_t[foot] is None:
                    candidate_start_t[foot] = t
                    contact_reported[foot] = False
                if t - float(candidate_start_t[foot]) >= params.stable_contact_time:
                    stable_feet.append(foot)
            else:
                candidate_start_t[foot] = None
                contact_reported[foot] = False

        for foot in stable_feet:
            if (
                not contact_reported[foot]
                and foot != accepted_contact
                and t - last_event_t > params.min_event_interval
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

        if step % sample_stride == 0:
            rows.append(
                make_row(
                    model,
                    data,
                    params,
                    t,
                    left_contact,
                    right_contact,
                    support_foot,
                    mode,
                    tau[:4],
                    input_power,
                    positive_input_energy,
                )
            )

        failure = classify_failure(model, data, params, start_x, t)
        if failure:
            break

    if not rows:
        left_contact, right_contact = contact_flags(model, data)
        rows.append(
            make_row(
                model,
                data,
                params,
                0.0,
                left_contact,
                right_contact,
                support_foot,
                mode,
                (0, 0, 0, 0),
                0.0,
                positive_input_energy,
            )
        )

    simulated_time = float(rows[-1]["time"])
    forward = max_x - start_x
    success = (
        simulated_time >= SUCCESS_TIME
        and alternations >= SUCCESS_TOUCHDOWNS
        and forward >= SUCCESS_FORWARD
        and not failure
    )
    effort_penalty = 3.0 * positive_input_energy
    score = (
        alternations * 200.0 + simulated_time * 80.0 + forward * 60.0 - effort_penalty
    )
    if success:
        score += 2000.0
    if failure:
        score -= 300.0
    if failure in {"nan_or_unstable", "fly_away", "penetration"}:
        score -= 500.0

    summary = {
        "params": asdict(params),
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
        "simulated_time": simulated_time,
        "failure": failure or "completed",
        "actuator_count": int(model.nu),
        "actuator_names": actuator_names(model),
        "knee_actuators": ["left_knee_stabilizer", "right_knee_stabilizer"],
        "active_input_energy_j": positive_input_energy,
        "net_actuator_work_j": net_work,
        "energy_per_alternation_j": positive_input_energy / max(1, alternations),
        "quasi_passive": True,
        "pure_passive": False,
        "uses_reward_function": False,
    }

    if save_prefix:
        OUT_DIR.mkdir(exist_ok=True)
        data_path = OUT_DIR / f"{save_prefix}_data.csv"
        with data_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        (OUT_DIR / f"{save_prefix}_summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return rows, summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=float, default=12.0)
    parser.add_argument("--slope", type=float, default=0.0)
    args = parser.parse_args()
    _, summary = run_simulation(
        StableParams(duration=args.duration, slope_deg=args.slope),
        save_prefix="v9_single",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
