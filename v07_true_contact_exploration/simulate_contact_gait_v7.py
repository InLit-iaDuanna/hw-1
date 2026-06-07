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
MODEL_PATH = MODEL_DIR / "contact_kneed_walker.xml"
QPOS_KEYS = ["hip_x", "hip_z", "left_hip", "left_knee", "right_hip", "right_knee"]
QVEL_KEYS = [f"{key}_vel" for key in QPOS_KEYS]


@dataclass(frozen=True)
class ContactParams:
    slope_deg: float = 5.0
    foot_radius: float = 0.055
    friction: float = 1.2
    hip_mass: float = 4.5
    initial_vx: float = 0.30
    knee_limit_deg: float = 55.0
    duration: float = 8.0
    timestep: float = 0.001
    thigh_length: float = 0.48
    shank_length: float = 0.52
    step_length: float = 0.34
    knee_damping: float = 0.018
    knee_stiffness: float = 0.0
    joint_damping: float = 0.012
    release_phase: float = 0.12
    swing_foot_x: float = -0.22
    swing_foot_clearance: float = 0.08
    swing_hip_vel: float = 0.45
    swing_knee_vel: float = -0.20

    @property
    def gamma(self) -> float:
        return math.radians(self.slope_deg)

    @property
    def leg_length(self) -> float:
        return self.thigh_length + self.shank_length


def ramp_height(x: float, params: ContactParams) -> float:
    return -math.tan(params.gamma) * x


def foot_center_z_on_ramp(x: float, params: ContactParams) -> float:
    return ramp_height(x, params) + params.foot_radius / math.cos(params.gamma)


def smoothstep(u: float) -> float:
    u = min(max(u, 0.0), 1.0)
    return u * u * (3.0 - 2.0 * u)


def foot_fk(
    hip_x: float, hip_z: float, thigh_q: float, knee_q: float, params: ContactParams
) -> tuple[float, float]:
    knee_x = hip_x - params.thigh_length * math.sin(thigh_q)
    knee_z = hip_z - params.thigh_length * math.cos(thigh_q)
    foot_x = knee_x - params.shank_length * math.sin(thigh_q + knee_q)
    foot_z = knee_z - params.shank_length * math.cos(thigh_q + knee_q)
    return foot_x, foot_z


def leg_ik_front_knee(
    hip_x: float,
    hip_z: float,
    foot_x: float,
    foot_z: float,
    params: ContactParams,
    prefer_straight: bool = False,
) -> tuple[float, float]:
    px = hip_x - foot_x
    pz = hip_z - foot_z
    d = math.hypot(px, pz)
    if prefer_straight or d >= params.leg_length - 1e-5:
        return math.atan2(px, pz), 0.0
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


def build_model_xml(params: ContactParams) -> str:
    return f"""<mujoco model="passive_contact_gait_v7">
  <compiler angle="degree" coordinate="local"/>
  <option timestep="{params.timestep}" integrator="RK4" gravity="0 0 -9.81"/>
  <visual><global offwidth="1280" offheight="720"/></visual>
  <default>
    <joint armature="0.004" damping="{params.joint_damping}"/>
    <geom condim="3" friction="{params.friction} 0.03 0.003" solref="0.006 1" solimp="0.90 0.98 0.002"/>
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
    <geom name="ramp" type="plane" pos="0 0 0" euler="0 {params.slope_deg} 0" size="40 1.8 0.08" material="ramp_mat" contype="1" conaffinity="1"/>
    <body name="hip" pos="0 0 0">
      <joint name="hip_x" type="slide" axis="1 0 0" damping="0.001"/>
      <joint name="hip_z" type="slide" axis="0 0 1" damping="0.001"/>
      <geom name="hip_mass" type="sphere" size="0.08" mass="{params.hip_mass}" material="hip_mat" contype="0" conaffinity="0"/>
      <geom name="hip_axis" type="cylinder" fromto="0 -0.13 0 0 0.13 0" size="0.018" mass="0.05" material="hip_mat" contype="0" conaffinity="0"/>
      <body name="left_thigh" pos="0 -0.055 0">
        <joint name="left_hip" type="hinge" axis="0 1 0" range="-85 85" limited="true"/>
        <geom name="left_upper" type="capsule" fromto="0 0 0 0 0 -{params.thigh_length}" size="0.026" mass="0.18" material="left_mat" contype="0" conaffinity="0"/>
        <body name="left_shank" pos="0 0 -{params.thigh_length}">
          <joint name="left_knee" type="hinge" axis="0 1 0" range="0 {params.knee_limit_deg}" limited="true" damping="{params.knee_damping}" stiffness="{params.knee_stiffness}" springref="0"/>
          <geom name="left_knee_marker" type="sphere" pos="0 0 0" size="0.04" mass="0.03" material="knee_mat" contype="0" conaffinity="0"/>
          <geom name="left_lower" type="capsule" fromto="0 0 0 0 0 -{params.shank_length}" size="0.023" mass="0.16" material="left_mat" contype="0" conaffinity="0"/>
          <geom name="left_foot" type="sphere" pos="0 0 -{params.shank_length}" size="{params.foot_radius}" mass="0.06" material="foot_mat" contype="1" conaffinity="1"/>
          <site name="left_foot_site" pos="0 0 -{params.shank_length}" size="0.01"/>
        </body>
      </body>
      <body name="right_thigh" pos="0 0.055 0">
        <joint name="right_hip" type="hinge" axis="0 1 0" range="-85 85" limited="true"/>
        <geom name="right_upper" type="capsule" fromto="0 0 0 0 0 -{params.thigh_length}" size="0.026" mass="0.18" material="right_mat" contype="0" conaffinity="0"/>
        <body name="right_shank" pos="0 0 -{params.thigh_length}">
          <joint name="right_knee" type="hinge" axis="0 1 0" range="0 {params.knee_limit_deg}" limited="true" damping="{params.knee_damping}" stiffness="{params.knee_stiffness}" springref="0"/>
          <geom name="right_knee_marker" type="sphere" pos="0 0 0" size="0.04" mass="0.03" material="knee_mat" contype="0" conaffinity="0"/>
          <geom name="right_lower" type="capsule" fromto="0 0 0 0 0 -{params.shank_length}" size="0.023" mass="0.16" material="right_mat" contype="0" conaffinity="0"/>
          <geom name="right_foot" type="sphere" pos="0 0 -{params.shank_length}" size="{params.foot_radius}" mass="0.06" material="foot_mat" contype="1" conaffinity="1"/>
          <site name="right_foot_site" pos="0 0 -{params.shank_length}" size="0.01"/>
        </body>
      </body>
    </body>
  </worldbody>
</mujoco>
"""


def write_model(params: ContactParams, path: Path = MODEL_PATH) -> None:
    MODEL_DIR.mkdir(exist_ok=True)
    path.write_text(build_model_xml(params), encoding="utf-8")


def initialize(
    model: mujoco.MjModel, data: mujoco.MjData, params: ContactParams
) -> None:
    phase = params.release_phase
    u = smoothstep(phase)
    alpha = math.asin(params.step_length / (2.0 * params.leg_length))
    support_x = 0.0
    support_z = foot_center_z_on_ramp(support_x, params)
    left_hip = params.gamma - alpha + 2.0 * alpha * u
    hip_x = support_x + params.leg_length * math.sin(left_hip)
    hip_z = support_z + params.leg_length * math.cos(left_hip)

    swing_x = params.swing_foot_x
    swing_z = foot_center_z_on_ramp(swing_x, params) + params.swing_foot_clearance
    right_hip, right_knee = leg_ik_front_knee(hip_x, hip_z, swing_x, swing_z, params)
    data.qpos[:] = [hip_x, hip_z, left_hip, 0.0, right_hip, right_knee]
    data.qvel[:] = [
        params.initial_vx,
        -math.tan(params.gamma) * params.initial_vx,
        0.10,
        0.0,
        params.swing_hip_vel,
        params.swing_knee_vel,
    ]
    mujoco.mj_forward(model, data)


def contact_flags(model: mujoco.MjModel, data: mujoco.MjData) -> tuple[bool, bool]:
    ramp = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "ramp")
    left = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "left_foot")
    right = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "right_foot")
    left_contact = False
    right_contact = False
    for i in range(data.ncon):
        con = data.contact[i]
        pair = {con.geom1, con.geom2}
        if ramp in pair and left in pair:
            left_contact = True
        if ramp in pair and right in pair:
            right_contact = True
    return left_contact, right_contact


def site_margin(
    model: mujoco.MjModel, data: mujoco.MjData, site_name: str, params: ContactParams
) -> float:
    site_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, site_name)
    pos = data.site_xpos[site_id]
    return float(pos[2] - foot_center_z_on_ramp(float(pos[0]), params))


def classify_failure(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    params: ContactParams,
    start_x: float,
    t: float,
    left_contact: bool,
    right_contact: bool,
) -> str:
    if not np.all(np.isfinite(data.qpos)) or not np.all(np.isfinite(data.qvel)):
        return "nan_or_unstable"
    speed = float(np.linalg.norm(data.qvel))
    if speed > 25.0:
        return "nan_or_unstable"
    hip_x, hip_z = float(data.qpos[0]), float(data.qpos[1])
    hip_clearance = hip_z - ramp_height(hip_x, params)
    if hip_clearance < 0.28:
        return "fall_down"
    if hip_clearance > 2.4:
        return "fly_away"
    if (
        min(
            site_margin(model, data, "left_foot_site", params),
            site_margin(model, data, "right_foot_site", params),
        )
        < -0.08
    ):
        return "penetration"
    if t > 2.0 and hip_x - start_x < 0.08 and (left_contact or right_contact):
        return "stuck"
    return ""


def row(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    params: ContactParams,
    t: float,
    left_contact: bool,
    right_contact: bool,
) -> dict[str, float | int]:
    left_margin = site_margin(model, data, "left_foot_site", params)
    right_margin = site_margin(model, data, "right_foot_site", params)
    out: dict[str, float | int] = {"time": t}
    for key, value in zip(QPOS_KEYS, data.qpos):
        out[key] = float(value)
    for key, value in zip(QVEL_KEYS, data.qvel):
        out[key] = float(value)
    out.update(
        {
            "left_contact": int(left_contact),
            "right_contact": int(right_contact),
            "left_margin": left_margin,
            "right_margin": right_margin,
            "hip_clearance": float(data.qpos[1])
            - ramp_height(float(data.qpos[0]), params),
        }
    )
    return out


def run_simulation(
    params: ContactParams, save_prefix: str | None = None, sample_hz: float = 120.0
) -> tuple[list[dict[str, float | int]], dict]:
    write_model(params)
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    data = mujoco.MjData(model)
    initialize(model, data, params)

    rows: list[dict[str, float | int]] = []
    start_x = float(data.qpos[0])
    max_x = start_x
    current_candidate = ""
    candidate_start_t = 0.0
    accepted_contact = ""
    last_event_t = -1.0
    alternations = 0
    contact_events: list[dict[str, float | str]] = []
    failure = ""
    sample_stride = max(1, int(round(1.0 / (params.timestep * sample_hz))))
    total_steps = int(params.duration / params.timestep)

    for step in range(total_steps):
        t = step * params.timestep
        mujoco.mj_step(model, data)
        left_contact, right_contact = contact_flags(model, data)
        max_x = max(max_x, float(data.qpos[0]))

        active = ""
        if left_contact and not right_contact:
            active = "left"
        elif right_contact and not left_contact:
            active = "right"
        elif left_contact and right_contact:
            active = "both"
        if active in {"left", "right"}:
            if active != current_candidate:
                current_candidate = active
                candidate_start_t = t
            stable_contact = t - candidate_start_t >= 0.035
        else:
            current_candidate = ""
            stable_contact = False

        if (
            active in {"left", "right"}
            and active != accepted_contact
            and stable_contact
            and t - last_event_t > 0.18
        ):
            if accepted_contact in {"left", "right"}:
                alternations += 1
            accepted_contact = active
            last_event_t = t
            contact_events.append({"time": t, "foot": active})

        if step % sample_stride == 0:
            rows.append(row(model, data, params, t, left_contact, right_contact))

        failure = classify_failure(
            model, data, params, start_x, t, left_contact, right_contact
        )
        if failure:
            break

    if not rows:
        left_contact, right_contact = contact_flags(model, data)
        rows.append(row(model, data, params, 0.0, left_contact, right_contact))

    forward = max_x - start_x
    score = alternations * 120.0 + forward * 18.0 + float(rows[-1]["time"]) * 25.0
    if failure:
        score -= 20.0
    if failure in {"nan_or_unstable", "fly_away", "penetration"}:
        score -= 50.0
    summary = {
        "params": asdict(params),
        "score": score,
        "alternating_touchdowns": alternations,
        "contact_events": contact_events,
        "forward_distance": forward,
        "simulated_time": float(rows[-1]["time"]),
        "failure": failure or "completed",
        "no_actuators": bool(model.nu == 0),
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
    parser.add_argument("--slope", type=float, default=5.0)
    parser.add_argument("--foot-radius", type=float, default=0.055)
    parser.add_argument("--friction", type=float, default=1.2)
    parser.add_argument("--hip-mass", type=float, default=4.5)
    parser.add_argument("--initial-vx", type=float, default=0.30)
    parser.add_argument("--knee-limit", type=float, default=55.0)
    parser.add_argument("--knee-stiffness", type=float, default=0.0)
    parser.add_argument("--duration", type=float, default=8.0)
    args = parser.parse_args()
    params = ContactParams(
        slope_deg=args.slope,
        foot_radius=args.foot_radius,
        friction=args.friction,
        hip_mass=args.hip_mass,
        initial_vx=args.initial_vx,
        knee_limit_deg=args.knee_limit,
        knee_stiffness=args.knee_stiffness,
        duration=args.duration,
    )
    _, summary = run_simulation(params, save_prefix="v7_single")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
