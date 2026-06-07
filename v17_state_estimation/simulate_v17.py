"""V17: V13.7 摩擦补偿 FSM + 传感器噪声 + 状态估计器。

验证控制律在编码器量化、FK hip 估计、接触抖动下是否仍能稳定行走。
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from dataclasses import dataclass, field, replace
from pathlib import Path

import mujoco
import numpy as np

ROOT = Path(__file__).resolve().parent
HW1_ROOT = ROOT.parent
V14_DIR = HW1_ROOT / "v14_passive_arms"
V136_DIR = HW1_ROOT / "v13_6_event_driven_fsm"
V14C_DIR = HW1_ROOT / "v14c_arm_mass_lightening"
V137_DIR = HW1_ROOT / "v13_7_friction_compensation"
sys.path.insert(0, str(V14_DIR))
sys.path.insert(0, str(V136_DIR))
sys.path.insert(0, str(V14C_DIR))
sys.path.insert(0, str(V137_DIR))
sys.path.insert(0, str(ROOT))

from simulate_passive_arms_v14 import (  # noqa: E402
    SUCCESS_FORWARD,
    SUCCESS_TIME,
    SUCCESS_TOUCHDOWNS,
    PassiveArmsParams,
    build_model_xml,
    classify_failure,
    contact_flags,
    initialize,
    make_row,
)
from simulate_v13_6 import (  # noqa: E402
    V136Params,
    control_v136,
)
from simulate_v14c import make_v14c_params  # noqa: E402

sys.path.insert(0, str(HW1_ROOT))
from sensor_model import SensorModel, SensorNoiseParams  # noqa: E402
from state_estimator import EstimatedState, StateEstimator  # noqa: E402

from common.motor_dynamics import (  # noqa: E402
    PRESETS as MOTOR_PRESETS,
)
from common.motor_dynamics import (
    L1MotorActuator,
    MotorParams,
    _sign_smooth,
    joint_armature_with_motor,
    joint_damping_with_motor,
)

OUT_DIR = ROOT / "out"
MODEL_DIR = OUT_DIR / "v17_models"
MODEL_PATH = MODEL_DIR / "state_est_walker.xml"

DEFAULT_BASE_ARMATURE = 0.004
PHASE_NAMES = ("stance_early", "stance_late", "swing_thrust", "swing_retract")
G = 9.81


@dataclass(frozen=True)
class V17Params:
    base: PassiveArmsParams
    fsm: V136Params
    hip_motor: MotorParams = field(default_factory=lambda: MOTOR_PRESETS["mx64ar"])
    knee_motor: MotorParams = field(default_factory=lambda: MOTOR_PRESETS["mx64ar"])
    compensate_friction: bool = True
    sensor_noise: SensorNoiseParams = field(default_factory=SensorNoiseParams)


def _compensate(tau_fsm: float, omega_joint: float, motor: MotorParams) -> float:
    tau_C_eff = motor.joint_tau_C_eff()
    return tau_fsm + tau_C_eff * _sign_smooth(omega_joint, motor.omega_eps)


def _energy_from_estimate(p: PassiveArmsParams, est: EstimatedState) -> float:
    m = p.hip_mass + 2.0 * p.torso_mass
    return 0.5 * m * (est.hip_vx**2 + est.hip_vz**2) + m * G * est.hip_z


def make_v17_fsm(base: PassiveArmsParams) -> V136Params:
    return make_v14c_params(base)


def build_model_xml_v17(p: V17Params) -> str:
    import re

    xml = build_model_xml(p.base)
    xml = xml.replace('model="passive_arms_walker_v14"', 'model="state_est_walker_v17"')
    hip_arm = joint_armature_with_motor(DEFAULT_BASE_ARMATURE, p.hip_motor)
    hip_damp = joint_damping_with_motor(p.base.hip_joint_damping, p.hip_motor)
    knee_arm = joint_armature_with_motor(DEFAULT_BASE_ARMATURE, p.knee_motor)
    knee_damp = joint_damping_with_motor(p.base.knee_damping, p.knee_motor)
    targets = [
        ("left_hip", hip_arm, hip_damp),
        ("right_hip", hip_arm, hip_damp),
        ("left_knee", knee_arm, knee_damp),
        ("right_knee", knee_arm, knee_damp),
    ]
    for jname, J, b in targets:
        new_xml, n = re.subn(
            rf'(<joint name="{jname}"[^/>]*?)damping="[^"]+"',
            rf'\1damping="{b:.6f}" armature="{J:.6f}"',
            xml,
            count=1,
        )
        if n != 1:
            raise RuntimeError(f"V17 XML injection failed for joint '{jname}'")
        xml = new_xml
    return xml


def write_model_v17(p: V17Params, path: Path = MODEL_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_model_xml_v17(p), encoding="utf-8")


def _control_from_estimate(
    fsm: V136Params,
    est: EstimatedState,
    data,
    t: float,
    support_foot: str,
    burst_start_t: float,
    E_current: float,
):
    """调用 control_v136，但用估计状态替换 data 中的对应值。"""
    data.qpos[0] = est.hip_x
    data.qpos[1] = est.hip_z
    data.qpos[2] = est.joint_angles[0]
    data.qpos[3] = est.joint_angles[1]
    data.qpos[5] = est.joint_angles[2]
    data.qpos[6] = est.joint_angles[3]
    data.qvel[0] = est.hip_vx
    data.qvel[1] = est.hip_vz
    data.qvel[2] = est.joint_velocities[0]
    data.qvel[3] = est.joint_velocities[1]
    data.qvel[5] = est.joint_velocities[2]
    data.qvel[6] = est.joint_velocities[3]
    return control_v136(fsm, data, t, support_foot, burst_start_t, E_current)


def run_simulation_v17(
    params: V17Params,
    save_prefix: str | None = None,
    sample_hz: float = 160.0,
):
    p = params.base
    fsm = params.fsm
    write_model_v17(params)
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    data = mujoco.MjData(model)
    initialize(model, data, p)

    ctrl_data = mujoco.MjData(model)

    sensor = SensorModel(params.sensor_noise)
    estimator = StateEstimator(
        thigh_length=p.thigh_length,
        shank_length=p.shank_length,
        foot_radius=p.foot_radius,
        slope_rad=math.radians(p.slope_deg),
        dt=p.timestep,
    )
    estimator.init_from_ground_truth(data, "left")

    actuators = {
        "left_hip": L1MotorActuator(params.hip_motor),
        "left_knee": L1MotorActuator(params.knee_motor),
        "right_hip": L1MotorActuator(params.hip_motor),
        "right_knee": L1MotorActuator(params.knee_motor),
    }
    qvel_addr = {"left_hip": 2, "left_knee": 3, "right_hip": 5, "right_knee": 6}

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
    positive_input_energy = 0.0
    net_work = 0.0
    positive_input_energy_elec = 0.0
    coulomb_dissipation = 0.0
    rows: list[dict] = []
    failure = ""
    sample_stride = max(1, int(round(1.0 / (p.timestep * sample_hz))))

    est_errors_vx: list[float] = []
    est_errors_hip_x: list[float] = []

    for step in range(int(p.duration / p.timestep)):
        t = step * p.timestep

        # --- 真实接触（物理层，用于 debounce 逻辑）---
        left_contact_gt, right_contact_gt = contact_flags(model, data)

        # --- 传感器测量 ---
        reading = sensor.measure(data, t, left_contact_gt, right_contact_gt)

        # --- 状态估计 ---
        estimator.update(reading, support_foot)
        est = estimator.get_state()

        # --- 估计误差记录 ---
        est_errors_vx.append(est.hip_vx - float(data.qvel[0]))
        est_errors_hip_x.append(est.hip_x - float(data.qpos[0]))

        # --- 控制器（用估计状态）---
        E_current = _energy_from_estimate(p, est)

        # 复制 data 到 ctrl_data 用于控制器（避免污染物理 data）
        ctrl_data.qpos[:] = data.qpos[:]
        ctrl_data.qvel[:] = data.qvel[:]
        tau = _control_from_estimate(
            fsm, est, ctrl_data, t, support_foot, burst_start_t, E_current
        )
        l_hip_des, l_knee_des, r_hip_des, r_knee_des = tau[0], tau[1], tau[2], tau[3]

        # --- V13.7 摩擦补偿（用估计速度）---
        if params.compensate_friction:
            l_hip_des = _compensate(
                l_hip_des, est.joint_velocities[0], params.hip_motor
            )
            l_knee_des = _compensate(
                l_knee_des, est.joint_velocities[1], params.knee_motor
            )
            r_hip_des = _compensate(
                r_hip_des, est.joint_velocities[2], params.hip_motor
            )
            r_knee_des = _compensate(
                r_knee_des, est.joint_velocities[3], params.knee_motor
            )

        # --- 电机模型（用真实速度，物理层）---
        l_hip_out, _ = actuators["left_hip"].compute_actual_torque(
            l_hip_des, float(data.qvel[qvel_addr["left_hip"]])
        )
        l_knee_out, _ = actuators["left_knee"].compute_actual_torque(
            l_knee_des, float(data.qvel[qvel_addr["left_knee"]])
        )
        r_hip_out, _ = actuators["right_hip"].compute_actual_torque(
            r_hip_des, float(data.qvel[qvel_addr["right_hip"]])
        )
        r_knee_out, _ = actuators["right_knee"].compute_actual_torque(
            r_knee_des, float(data.qvel[qvel_addr["right_knee"]])
        )
        data.ctrl[:] = (l_hip_out, l_knee_out, r_hip_out, r_knee_out)

        # --- 能量和耗散统计 ---
        omega = [
            float(data.qvel[qvel_addr[k]])
            for k in ("left_hip", "left_knee", "right_hip", "right_knee")
        ]
        tau_out = [l_hip_out, l_knee_out, r_hip_out, r_knee_out]
        input_power_mech = sum(tau_out[i] * omega[i] for i in range(4))
        positive_input_energy += max(0.0, input_power_mech) * p.timestep
        net_work += input_power_mech * p.timestep
        for key, om in zip(("left_hip", "left_knee", "right_hip", "right_knee"), omega):
            coulomb_dissipation += actuators[key]._tau_C_eff * abs(om) * p.timestep

        mujoco.mj_step(model, data)
        max_x = max(max_x, float(data.qpos[0]))

        # --- 接触事件检测（用估计的接触状态）---
        contacts = {"left": est.left_contact, "right": est.right_contact}
        stable_feet: list[str] = []
        for foot, has_contact in contacts.items():
            if has_contact:
                if candidate_start_t[foot] is None:
                    candidate_start_t[foot] = t
                    contact_reported[foot] = False
                if t - float(candidate_start_t[foot]) >= p.stable_contact_time:
                    stable_feet.append(foot)
            else:
                candidate_start_t[foot] = None
                contact_reported[foot] = False

        for foot in stable_feet:
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

        if step % sample_stride == 0:
            row = make_row(
                model,
                data,
                p,
                t,
                left_contact_gt,
                right_contact_gt,
                support_foot,
                "v17",
                (l_hip_out, l_knee_out, r_hip_out, r_knee_out),
                input_power_mech,
                positive_input_energy,
            )
            rows.append(row)

        failure = classify_failure(model, data, p, start_x, t)
        if failure:
            break

    # --- 汇总 ---
    simulated_time = float(rows[-1]["time"]) if rows else 0.0
    forward = max_x - start_x
    success = (
        simulated_time >= SUCCESS_TIME
        and alternations >= SUCCESS_TOUCHDOWNS
        and forward >= SUCCESS_FORWARD
        and not failure
    )

    rmse_vx = (
        float(np.sqrt(np.mean(np.array(est_errors_vx) ** 2))) if est_errors_vx else 0.0
    )
    rmse_hip_x = (
        float(np.sqrt(np.mean(np.array(est_errors_hip_x) ** 2)))
        if est_errors_hip_x
        else 0.0
    )

    summary = {
        "success": success,
        "forward_distance": forward,
        "simulated_time": simulated_time,
        "alternating_touchdowns": alternations,
        "failure": failure or "completed",
        "active_input_energy_mech_j": positive_input_energy,
        "coulomb_friction_dissipation_j": coulomb_dissipation,
        "compensate_friction": params.compensate_friction,
        "sensor_noise_scale": params.sensor_noise.noise_scale,
        "estimation_rmse_vx": rmse_vx,
        "estimation_rmse_hip_x": rmse_hip_x,
        "controller": "v17_state_estimated_friction_comp_fsm",
    }

    if save_prefix:
        OUT_DIR.mkdir(exist_ok=True)
        if rows:
            with (OUT_DIR / f"{save_prefix}_data.csv").open(
                "w", newline="", encoding="utf-8"
            ) as f:
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
    parser.add_argument("--arm-mass", type=float, default=0.01)
    parser.add_argument("--foot-radius", type=float, default=0.042)
    parser.add_argument("--leg-scale", type=float, default=1.02)
    parser.add_argument(
        "--motor-preset", choices=list(MOTOR_PRESETS.keys()), default="mx64ar"
    )
    parser.add_argument("--noise-scale", type=float, default=1.0)
    parser.add_argument("--no-compensate", action="store_true")
    parser.add_argument("--save-prefix", default="v17_baseline")
    args = parser.parse_args()

    base0 = PassiveArmsParams()
    base = replace(
        base0,
        duration=args.duration,
        arm_mass=args.arm_mass,
        arm_length=0.40,
        arm_damping=0.02,
        arm_stiffness=0.0,
        thigh_length=float(base0.thigh_length * args.leg_scale),
        shank_length=float(base0.shank_length * args.leg_scale),
        step_length=float(base0.step_length * args.leg_scale),
        foot_radius=float(args.foot_radius),
    )
    motor = MOTOR_PRESETS[args.motor_preset]
    params = V17Params(
        base=base,
        fsm=make_v17_fsm(base),
        hip_motor=motor,
        knee_motor=motor,
        compensate_friction=not args.no_compensate,
        sensor_noise=SensorNoiseParams(noise_scale=args.noise_scale),
    )
    _, summary = run_simulation_v17(
        params, save_prefix=args.save_prefix, sample_hz=160.0
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
