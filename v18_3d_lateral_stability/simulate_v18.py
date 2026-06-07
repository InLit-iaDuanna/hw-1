"""V18: 3D 侧向被动稳定探索。V10 矢状面控制 + 冠状面被动弹性。"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import mujoco
import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
from common.control_utils import limited_pd, ramp_height, smoothstep
from common.mujoco_utils import get_contact_flags, get_joint_address

sys.path.insert(0, str(ROOT))
from model_3d import (
    MODEL_PATH,
    Lateral3DParams,
    write_model,
)  # noqa: E402

OUT_DIR = ROOT / "out"
G = 9.81


def run_simulation_v18(params: Lateral3DParams, save_prefix: str | None = None):
    p = params
    write_model(p)
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    data = mujoco.MjData(model)

    # 命名关节地址解析
    hx_q, hx_v = get_joint_address(model, "hip_x")
    hy_q, hy_v = get_joint_address(model, "hip_y")
    hz_q, hz_v = get_joint_address(model, "hip_z")
    hr_q, hr_v = get_joint_address(model, "hip_roll")
    lh_q, lh_v = get_joint_address(model, "left_hip")
    lk_q, lk_v = get_joint_address(model, "left_knee")
    la_q, la_v = get_joint_address(model, "left_ankle")
    rh_q, rh_v = get_joint_address(model, "right_hip")
    rk_q, rk_v = get_joint_address(model, "right_knee")
    ra_q, ra_v = get_joint_address(model, "right_ankle")
    la_abd_q, _ = get_joint_address(model, "left_hip_abd")
    ra_abd_q, _ = get_joint_address(model, "right_hip_abd")

    # 初始化（V10 逻辑 + 侧向扰动）
    u0 = smoothstep(p.release_phase)
    alpha = math.asin(p.step_length / (2.0 * p.leg_length))
    support_z = ramp_height(0.0, gamma=p.gamma) + p.foot_radius / max(
        0.2, math.cos(p.gamma)
    )
    left_hip_init = p.gamma + alpha - 2.0 * alpha * u0
    hip_x_init = p.leg_length * math.sin(left_hip_init)
    hip_z_init = support_z + p.leg_length * math.cos(left_hip_init)

    # swing leg IK (simplified)
    px = hip_x_init - p.swing_foot_x
    pz = hip_z_init - (support_z + p.swing_foot_clearance)
    d = math.hypot(px, pz)
    d = float(
        np.clip(d, abs(p.thigh_length - p.shank_length) + 1e-5, p.leg_length - 1e-5)
    )
    base = math.atan2(px, pz)
    cos_delta = (p.thigh_length**2 + d**2 - p.shank_length**2) / (
        2.0 * p.thigh_length * d
    )
    delta = math.acos(float(np.clip(cos_delta, -1.0, 1.0)))
    right_hip_init = base - delta
    thigh_angle = right_hip_init
    knee_x = hip_x_init - p.thigh_length * math.sin(thigh_angle)
    knee_z = hip_z_init - p.thigh_length * math.cos(thigh_angle)
    shank_angle = math.atan2(
        knee_x - p.swing_foot_x, knee_z - (support_z + p.swing_foot_clearance)
    )
    right_knee_init = float(
        np.clip(shank_angle - thigh_angle, 0.0, math.radians(p.knee_limit_deg))
    )

    data.qpos[hx_q] = hip_x_init
    data.qpos[hy_q] = p.init_hip_y
    data.qpos[hz_q] = hip_z_init
    data.qpos[hr_q] = math.radians(p.init_hip_roll_deg)
    data.qpos[la_abd_q] = 0.0
    data.qpos[ra_abd_q] = 0.0
    data.qpos[lh_q] = left_hip_init
    data.qpos[lk_q] = 0.0
    data.qpos[rh_q] = right_hip_init
    data.qpos[rk_q] = right_knee_init

    data.qvel[hx_v] = p.initial_vx
    data.qvel[hz_v] = -math.tan(p.gamma) * p.initial_vx
    data.qvel[lh_v] = 0.04
    data.qvel[rh_v] = p.swing_hip_vel
    data.qvel[rk_v] = p.swing_knee_vel
    data.ctrl[:] = 0.0
    mujoco.mj_forward(model, data)

    # 仿真循环
    support_foot = "left"
    burst_start_t = -p.gait_period
    last_event_t = -1.0
    alternations = 0
    accepted_contact = ""
    candidate_start_t = {"left": None, "right": None}
    contact_reported = {"left": False, "right": False}
    failure = ""
    max_x = float(data.qpos[hx_q])
    start_x = max_x
    max_abs_roll = 0.0
    max_abs_hip_y = 0.0

    for step in range(int(p.duration / p.timestep)):
        t = step * p.timestep

        # V10 矢状面控制器
        hip_x = float(data.qpos[hx_q])
        hip_z = float(data.qpos[hz_q])
        clearance = hip_z - ramp_height(hip_x, gamma=p.gamma)
        u = min(max((t - burst_start_t) / max(p.gait_period, 1e-6), 0.0), 1.0)
        if clearance < p.recovery_clearance:
            u = min(u, 0.55)
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
        lh_tau = limited_pd(
            float(data.qpos[lh_q]),
            float(data.qvel[lh_v]),
            stance_target if left_is_support else swing_target,
            p.hip_kp,
            p.hip_kd,
            p.hip_torque_limit,
        )
        lk_tau = limited_pd(
            float(data.qpos[lk_q]),
            float(data.qvel[lk_v]),
            stance_knee if left_is_support else swing_knee,
            p.knee_kp,
            p.knee_kd,
            p.knee_torque_limit,
        )
        rh_tau = limited_pd(
            float(data.qpos[rh_q]),
            float(data.qvel[rh_v]),
            stance_target if not left_is_support else swing_target,
            p.hip_kp,
            p.hip_kd,
            p.hip_torque_limit,
        )
        rk_tau = limited_pd(
            float(data.qpos[rk_q]),
            float(data.qvel[rk_v]),
            stance_knee if not left_is_support else swing_knee,
            p.knee_kp,
            p.knee_kd,
            p.knee_torque_limit,
        )
        data.ctrl[:] = (lh_tau, lk_tau, rh_tau, rk_tau)

        mujoco.mj_step(model, data)
        max_x = max(max_x, float(data.qpos[hx_q]))

        # 侧向度量
        roll = float(data.qpos[hr_q])
        hip_y = float(data.qpos[hy_q])
        max_abs_roll = max(max_abs_roll, abs(roll))
        max_abs_hip_y = max(max_abs_hip_y, abs(hip_y))

        # 接触事件检测
        left_c, right_c = get_contact_flags(
            model,
            data,
            "ramp",
            ["left_heel", "left_sole", "left_toe", "left_sole_lat"],
            ["right_heel", "right_sole", "right_toe", "right_sole_lat"],
        )
        contacts = {"left": left_c, "right": right_c}
        stable_feet = []
        for foot, has_c in contacts.items():
            if has_c:
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
                break

        # 失败检测
        if not np.all(np.isfinite(data.qpos)) or not np.all(np.isfinite(data.qvel)):
            failure = "nan_or_unstable"
            break
        if abs(roll) > math.radians(45):
            failure = "lateral_fall"
            break
        if abs(hip_y) > 0.5:
            failure = "lateral_drift"
            break
        hc = hip_z - ramp_height(hip_x, gamma=p.gamma)
        if hc < 0.22:
            failure = "fall_down"
            break
        if t > 4.0 and float(data.qpos[hx_q]) - start_x < 0.20:
            failure = "stuck"
            break

    simulated_time = step * p.timestep
    forward = max_x - start_x
    success = (
        simulated_time >= p.duration * 0.9
        and alternations >= 10
        and forward >= 0.8
        and not failure
    )
    lateral_stable = max_abs_roll < math.radians(15) and max_abs_hip_y < 0.15

    summary = {
        "success": success,
        "lateral_stable": lateral_stable,
        "forward_distance": forward,
        "simulated_time": simulated_time,
        "alternating_touchdowns": alternations,
        "failure": failure or "completed",
        "max_abs_roll_deg": math.degrees(max_abs_roll),
        "max_abs_hip_y_m": max_abs_hip_y,
        "params": {
            "hip_abd_stiffness": p.hip_abd_stiffness,
            "hip_abd_damping": p.hip_abd_damping,
            "foot_lateral_width": p.foot_lateral_width,
            "init_hip_roll_deg": p.init_hip_roll_deg,
            "hip_roll_damping": p.hip_roll_damping,
            "hip_roll_stiffness": p.hip_roll_stiffness,
        },
    }

    if save_prefix:
        OUT_DIR.mkdir(exist_ok=True)
        (OUT_DIR / f"{save_prefix}_summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--abd-stiffness", type=float, default=20.0)
    parser.add_argument("--abd-damping", type=float, default=2.0)
    parser.add_argument("--foot-width", type=float, default=0.04)
    parser.add_argument("--roll-perturb", type=float, default=3.0)
    parser.add_argument("--hip-roll-damping", type=float, default=0.5)
    parser.add_argument("--hip-roll-stiffness", type=float, default=50.0)
    parser.add_argument("--duration", type=float, default=10.0)
    parser.add_argument("--save-prefix", default="v18_baseline")
    args = parser.parse_args()

    p = Lateral3DParams(
        hip_abd_stiffness=args.abd_stiffness,
        hip_abd_damping=args.abd_damping,
        foot_lateral_width=args.foot_width,
        init_hip_roll_deg=args.roll_perturb,
        hip_roll_damping=args.hip_roll_damping,
        hip_roll_stiffness=args.hip_roll_stiffness,
        duration=args.duration,
    )
    summary = run_simulation_v18(p, save_prefix=args.save_prefix)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
