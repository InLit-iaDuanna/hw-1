"""V11 simulate: V10 准被动步态 + 崎岖地形 + 单脉冲外力 + 触地相位噪声。

学术口径：准被动 / 鲁棒性 + 敏感性研究。失败结果如实记录。

复用：从 V10 直接 import 物理参数、控制律、接触检测、失败分类，本脚本只新增
扰动/地形相关的代码路径。当 amplitude=0 且 impulse=0 且 phase_noise=0 时，仿真
应等价于 V10 平地基线（除 hfield 几何替换为 plane）。
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import mujoco

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common import disturbance, terrain  # noqa: E402
from v10_rolling_foot_biomimetic_gait.simulate_rolling_foot_gait_v10 import (  # noqa: E402
    QPOS_KEYS,
    QVEL_KEYS,
    SUCCESS_FORWARD,
    SUCCESS_TIME,
    SUCCESS_TOUCHDOWNS,
    RollingFootParams,
    actuator_names,
    classify_failure,
    contact_flags,
    control,
    foot_contact_detail,
    initialize,
    ramp_height,
)

OUT_DIR = ROOT / "out"
MODEL_DIR = ROOT / "models"
MODEL_PATH = MODEL_DIR / "rugged_walker.xml"
V10_BEST_PARAMS_PATH = (
    PROJECT_ROOT / "v10_rolling_foot_biomimetic_gait" / "out" / "v10_best_params.json"
)


@dataclass(frozen=True)
class RuggedScenario:
    """V11 扰动场景。三类扰动归零时退化为 V10 平地基线。"""

    terrain_amplitude_m: float = 0.0
    terrain_wavelength_m: float = 1.2
    terrain_seed: int = 0
    impulse_force_n: float = 0.0
    impulse_t_s: float = 5.0
    impulse_duration_s: float = 0.05
    impulse_dir: tuple[float, float, float] = (1.0, 0.0, 0.0)
    contact_phase_noise_s: float = 0.0
    contact_phase_seed: int = 0


def load_v10_best_params() -> RollingFootParams:
    if not V10_BEST_PARAMS_PATH.exists():
        return RollingFootParams()
    raw = json.loads(V10_BEST_PARAMS_PATH.read_text(encoding="utf-8"))
    p = raw.get("params", {})
    valid = {f for f in RollingFootParams.__dataclass_fields__}
    return RollingFootParams(**{k: v for k, v in p.items() if k in valid})


def build_model_xml_rugged(params: RollingFootParams, scenario: RuggedScenario) -> str:
    """V10 模型字符串的崎岖地形版本：仅替换 ramp 几何与新增 hfield 资产。"""
    ctrl_limit = max(params.hip_torque_limit, params.knee_torque_limit, 1.0)
    asset_extra = terrain.build_rugged_assets_xml(scenario.terrain_amplitude_m)
    ramp_geom = terrain.build_rugged_geom_xml(
        scenario.terrain_amplitude_m, params.slope_deg
    )
    return f"""<mujoco model="rugged_walker_v11">
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
{asset_extra}  </asset>
  <worldbody>
    <light name="key" pos="-2 -3 5" dir="0.3 0.5 -1" diffuse="0.85 0.85 0.85"/>
{ramp_geom}    <body name="hip" pos="0 0 0">
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
          <body name="left_foot_body" pos="0 0 -{params.shank_length}">
            <joint name="left_ankle" type="hinge" axis="0 1 0" range="-{params.ankle_limit_deg} {params.ankle_limit_deg}" limited="true" damping="{params.ankle_damping}" stiffness="{params.ankle_stiffness}" springref="0"/>
            <geom name="left_sole" type="capsule" fromto="-{params.foot_length * 0.45} 0 -0.015 {params.foot_length * 0.35} 0 -0.015" size="{params.foot_radius * 0.55}" mass="0.06" material="foot_mat" contype="1" conaffinity="1"/>
            <geom name="left_heel" type="sphere" pos="-{params.foot_length * 0.50} 0 -0.015" size="{params.foot_radius}" mass="0.025" material="foot_mat" contype="1" conaffinity="1"/>
            <geom name="left_toe" type="sphere" pos="{params.foot_length * 0.48} 0 -0.018" size="{params.toe_radius}" mass="0.025" material="foot_mat" contype="1" conaffinity="1"/>
            <site name="left_foot_site" pos="0 0 -0.015" size="0.01"/>
            <site name="left_heel_site" pos="-{params.foot_length * 0.50} 0 -0.015" size="0.01"/>
            <site name="left_toe_site" pos="{params.foot_length * 0.48} 0 -0.018" size="0.01"/>
          </body>
        </body>
      </body>
      <body name="right_thigh" pos="0 0.055 0">
        <joint name="right_hip" type="hinge" axis="0 1 0" range="-95 95" limited="true" damping="{params.hip_joint_damping}"/>
        <geom name="right_upper" type="capsule" fromto="0 0 0 0 0 -{params.thigh_length}" size="0.026" mass="0.18" material="right_mat" contype="0" conaffinity="0"/>
        <body name="right_shank" pos="0 0 -{params.thigh_length}">
          <joint name="right_knee" type="hinge" axis="0 1 0" range="0 {params.knee_limit_deg}" limited="true" damping="{params.knee_damping}" stiffness="{params.knee_stiffness}" springref="0"/>
          <geom name="right_knee_marker" type="sphere" pos="0 0 0" size="0.04" mass="0.03" material="knee_mat" contype="0" conaffinity="0"/>
          <geom name="right_lower" type="capsule" fromto="0 0 0 0 0 -{params.shank_length}" size="0.023" mass="0.16" material="right_mat" contype="0" conaffinity="0"/>
          <body name="right_foot_body" pos="0 0 -{params.shank_length}">
            <joint name="right_ankle" type="hinge" axis="0 1 0" range="-{params.ankle_limit_deg} {params.ankle_limit_deg}" limited="true" damping="{params.ankle_damping}" stiffness="{params.ankle_stiffness}" springref="0"/>
            <geom name="right_sole" type="capsule" fromto="-{params.foot_length * 0.45} 0 -0.015 {params.foot_length * 0.35} 0 -0.015" size="{params.foot_radius * 0.55}" mass="0.06" material="foot_mat" contype="1" conaffinity="1"/>
            <geom name="right_heel" type="sphere" pos="-{params.foot_length * 0.50} 0 -0.015" size="{params.foot_radius}" mass="0.025" material="foot_mat" contype="1" conaffinity="1"/>
            <geom name="right_toe" type="sphere" pos="{params.foot_length * 0.48} 0 -0.018" size="{params.toe_radius}" mass="0.025" material="foot_mat" contype="1" conaffinity="1"/>
            <site name="right_foot_site" pos="0 0 -0.015" size="0.01"/>
            <site name="right_heel_site" pos="-{params.foot_length * 0.50} 0 -0.015" size="0.01"/>
            <site name="right_toe_site" pos="{params.foot_length * 0.48} 0 -0.018" size="0.01"/>
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


def write_model_rugged(params: RollingFootParams, scenario: RuggedScenario) -> None:
    MODEL_DIR.mkdir(exist_ok=True)
    MODEL_PATH.write_text(build_model_xml_rugged(params, scenario), encoding="utf-8")


def make_row(
    model,
    data,
    params,
    t,
    left_contact,
    right_contact,
    support_foot,
    mode,
    tau,
    input_power,
    input_energy,
):
    out: dict[str, float | int | str] = {"time": t}
    for key, value in zip(QPOS_KEYS, data.qpos):
        out[key] = float(value)
    for key, value in zip(QVEL_KEYS, data.qvel):
        out[key] = float(value)
    detail = foot_contact_detail(model, data)
    out.update(
        {
            "left_contact": int(left_contact),
            "right_contact": int(right_contact),
            "left_heel_contact": int(detail["left_heel"]),
            "left_sole_contact": int(detail["left_sole"]),
            "left_toe_contact": int(detail["left_toe"]),
            "right_heel_contact": int(detail["right_heel"]),
            "right_sole_contact": int(detail["right_sole"]),
            "right_toe_contact": int(detail["right_toe"]),
            "support_foot": support_foot,
            "mode": mode,
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


def run_rugged_simulation(
    params: RollingFootParams,
    scenario: RuggedScenario,
    save_prefix: str | None = None,
    sample_hz: float = 120.0,
) -> tuple[list[dict], dict]:
    """V10 主循环 + 崎岖地形 + 外力脉冲 + 触地相位噪声。"""
    write_model_rugged(params, scenario)
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))

    if scenario.terrain_amplitude_m > 0.0:
        profile = terrain.generate_profile(
            scenario.terrain_amplitude_m,
            scenario.terrain_wavelength_m,
            length_m=90.0,
            seed=scenario.terrain_seed,
        )
        terrain.fill_hfield_data(model, profile)

    data = mujoco.MjData(model)
    initialize(model, data, params)

    impulse_spec = disturbance.ImpulseSpec(
        body_name="hip",
        force_xyz=(
            scenario.impulse_force_n * scenario.impulse_dir[0],
            scenario.impulse_force_n * scenario.impulse_dir[1],
            scenario.impulse_force_n * scenario.impulse_dir[2],
        ),
        t_start_s=scenario.impulse_t_s,
        duration_s=scenario.impulse_duration_s,
    )
    phase_noise = disturbance.ContactPhaseNoise(
        sigma_s=scenario.contact_phase_noise_s,
        seed=scenario.contact_phase_seed,
    )

    start_x = float(data.qpos[0])
    max_x = start_x
    support_foot = "left"
    accepted_contact = ""
    candidate_start_t: dict[str, float | None] = {"left": None, "right": None}
    candidate_threshold: dict[str, float] = {
        "left": params.stable_contact_time,
        "right": params.stable_contact_time,
    }
    contact_reported = {"left": False, "right": False}
    last_event_t = -1.0
    burst_start_t = -params.gait_period
    alternations = 0
    contact_events: list[dict] = []
    positive_input_energy = 0.0
    net_work = 0.0
    rows: list[dict] = []
    failure = ""
    mode = "left_stance"
    impulse_active_steps = 0
    sample_stride = max(1, int(round(1.0 / (params.timestep * sample_hz))))

    n_steps = int(params.duration / params.timestep)
    for step in range(n_steps):
        t = step * params.timestep
        tau = control(params, data, t, support_foot, burst_start_t)
        data.ctrl[:] = tau[:4]
        input_power = (
            float(data.ctrl[0]) * float(data.qvel[2])
            + float(data.ctrl[1]) * float(data.qvel[3])
            + float(data.ctrl[2]) * float(data.qvel[5])
            + float(data.ctrl[3]) * float(data.qvel[6])
        )
        positive_input_energy += max(0.0, input_power) * params.timestep
        net_work += input_power * params.timestep
        mode = str(tau[4])

        if disturbance.apply_impulse(model, data, impulse_spec, t):
            impulse_active_steps += 1

        mujoco.mj_step(model, data)
        left_contact, right_contact = contact_flags(model, data)
        max_x = max(max_x, float(data.qpos[0]))

        contacts = {"left": left_contact, "right": right_contact}
        stable_feet: list[str] = []
        for foot, has_contact in contacts.items():
            if has_contact:
                if candidate_start_t[foot] is None:
                    candidate_start_t[foot] = t
                    candidate_threshold[foot] = phase_noise.perturbed_threshold(
                        params.stable_contact_time
                    )
                    contact_reported[foot] = False
                if t - float(candidate_start_t[foot]) >= candidate_threshold[foot]:
                    stable_feet.append(foot)
            else:
                candidate_start_t[foot] = None
                candidate_threshold[foot] = params.stable_contact_time
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
        rows.append(
            make_row(
                model,
                data,
                params,
                0.0,
                False,
                False,
                support_foot,
                mode,
                (0, 0, 0, 0),
                0.0,
                0.0,
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

    summary = {
        "params": asdict(params),
        "scenario": asdict(scenario),
        "success": success,
        "alternating_touchdowns": alternations,
        "contact_events": contact_events,
        "forward_distance": forward,
        "simulated_time": simulated_time,
        "failure": failure or "completed",
        "actuator_count": int(model.nu),
        "actuator_names": actuator_names(model),
        "active_input_energy_j": positive_input_energy,
        "net_actuator_work_j": net_work,
        "impulse_active_steps": impulse_active_steps,
        "quasi_passive": True,
        "pure_passive": False,
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
    parser = argparse.ArgumentParser(
        description="V11 rugged terrain robustness simulator"
    )
    parser.add_argument("--amplitude", type=float, default=0.0, help="地形振幅 (m)")
    parser.add_argument("--wavelength", type=float, default=1.2, help="地形波长 (m)")
    parser.add_argument("--terrain-seed", type=int, default=0)
    parser.add_argument(
        "--impulse", type=float, default=0.0, help="脉冲力幅值 (N)，作用于 hip 沿 +x"
    )
    parser.add_argument("--impulse-t", type=float, default=5.0)
    parser.add_argument("--impulse-duration", type=float, default=0.05)
    parser.add_argument(
        "--phase-noise", type=float, default=0.0, help="触地相位 sigma (s)"
    )
    parser.add_argument("--phase-seed", type=int, default=0)
    parser.add_argument("--duration", type=float, default=12.0)
    parser.add_argument("--save-prefix", type=str, default="v11_single")
    args = parser.parse_args()

    base = load_v10_best_params()
    params = RollingFootParams(**{**asdict(base), "duration": args.duration})
    scenario = RuggedScenario(
        terrain_amplitude_m=args.amplitude,
        terrain_wavelength_m=args.wavelength,
        terrain_seed=args.terrain_seed,
        impulse_force_n=args.impulse,
        impulse_t_s=args.impulse_t,
        impulse_duration_s=args.impulse_duration,
        contact_phase_noise_s=args.phase_noise,
        contact_phase_seed=args.phase_seed,
    )
    _, summary = run_rugged_simulation(params, scenario, save_prefix=args.save_prefix)
    print(
        json.dumps(
            {k: v for k, v in summary.items() if k not in ("params",)},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
