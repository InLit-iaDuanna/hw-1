"""V20: 3D 行走 + 步宽控制（主动落脚点规划）。"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

import mujoco
import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent))  # 添加父目录以访问 common/
from model_3d_v20 import MODEL_PATH, V20Params, write_model  # noqa: E402
from step_width_planner import StepWidthParams, StepWidthPlanner  # noqa: E402

from common import (
    get_contact_flags,
    get_joint_address,
    limited_pd,
    ramp_height,
    smoothstep,
    solve_3d_leg_ik,
)  # noqa: E402

OUT_DIR = ROOT / "out"


def run_simulation_v20(
    p: V20Params, save_prefix: str | None = None, save_csv: bool = False
):
    write_model(p)
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    data = mujoco.MjData(model)

    hx_q, hx_v = get_joint_address(model, "hip_x")
    hy_q, hy_v = get_joint_address(model, "hip_y")
    hz_q, hz_v = get_joint_address(model, "hip_z")
    hr_q, _ = get_joint_address(model, "hip_roll")
    lh_q, lh_v = get_joint_address(model, "left_hip")
    lk_q, lk_v = get_joint_address(model, "left_knee")
    rh_q, rh_v = get_joint_address(model, "right_hip")
    rk_q, rk_v = get_joint_address(model, "right_knee")
    la_q, la_v = get_joint_address(model, "left_hip_abd")
    ra_q, ra_v = get_joint_address(model, "right_hip_abd")

    # 初始化步宽规划器
    sw_params = StepWidthParams(
        k_p=p.step_width_kp,
        k_d=p.step_width_kd,
        y_nominal=p.step_width_nominal,
        y_max_deviation=p.step_width_max_deviation,
    )
    planner = StepWidthPlanner(sw_params)

    # 初始化（2D 矢状面 + 侧向初始状态）
    u0 = smoothstep(p.release_phase)
    alpha = math.asin(p.step_length / (2.0 * p.leg_length))
    sz = ramp_height(0.0, p.gamma) + p.foot_radius / max(0.2, math.cos(p.gamma))
    lhi = p.gamma + alpha - 2.0 * alpha * u0
    hxi = p.leg_length * math.sin(lhi)
    hzi = sz + p.leg_length * math.cos(lhi)

    # 摆动腿 (right leg) 初始化：使用 3D IK
    swing_foot_x = p.swing_foot_x
    swing_foot_y = p.step_width_nominal  # 初始右脚侧向位置
    swing_foot_z = sz + p.swing_foot_clearance

    ik_result = solve_3d_leg_ik(
        (hxi, p.init_hip_y, hzi),
        (hxi - swing_foot_x, swing_foot_y, swing_foot_z),
        p.thigh_length,
        p.shank_length,
        p.hip_lateral_offset,
    )

    if ik_result:
        rhi, rki, ra_init = ik_result
    else:
        # Fallback: 使用 2D IK
        px, pz = hxi - swing_foot_x, hzi - swing_foot_z
        d = float(
            np.clip(
                math.hypot(px, pz),
                abs(p.thigh_length - p.shank_length) + 1e-5,
                p.leg_length - 1e-5,
            )
        )
        cd = (p.thigh_length**2 + d**2 - p.shank_length**2) / (2.0 * p.thigh_length * d)
        rhi = math.atan2(px, pz) - math.acos(float(np.clip(cd, -1.0, 1.0)))
        kx = hxi - p.thigh_length * math.sin(rhi)
        kz = hzi - p.thigh_length * math.cos(rhi)
        rki = float(
            np.clip(
                math.atan2(kx - (hxi - swing_foot_x), kz - swing_foot_z) - rhi,
                0.0,
                math.radians(p.knee_limit_deg),
            )
        )
        ra_init = 0.0

    data.qpos[hx_q] = hxi
    data.qpos[hy_q] = p.init_hip_y
    data.qpos[hz_q] = hzi
    data.qpos[hr_q] = math.radians(p.init_hip_roll_deg)
    data.qpos[la_q] = 0.0
    data.qpos[ra_q] = ra_init
    data.qpos[lh_q] = lhi
    data.qpos[lk_q] = 0.0
    data.qpos[rh_q] = rhi
    data.qpos[rk_q] = rki
    data.qvel[hx_v] = p.initial_vx
    data.qvel[hz_v] = -math.tan(p.gamma) * p.initial_vx
    data.qvel[lh_v] = 0.04
    data.qvel[rh_v] = p.swing_hip_vel
    data.qvel[rk_v] = p.swing_knee_vel
    data.ctrl[:] = 0.0
    mujoco.mj_forward(model, data)

    support = "left"
    burst_t = -p.gait_period
    last_ev = -1.0
    alternations = 0
    accepted = ""
    cand = {"left": None, "right": None}
    crep = {"left": False, "right": False}
    failure = ""
    start_x = float(data.qpos[hx_q])
    max_x = start_x
    max_roll = 0.0
    max_hy = 0.0
    max_abd = 0.0

    # 步宽控制状态
    swing_phase_start_recorded = False
    y_foot_target_current = 0.0

    # CSV 记录
    rows = []

    for step in range(int(p.duration / p.timestep)):
        t = step * p.timestep
        hx = float(data.qpos[hx_q])
        hy = float(data.qpos[hy_q])
        hz = float(data.qpos[hz_q])
        vy = float(data.qvel[hy_v])
        u = min(max((t - burst_t) / max(p.gait_period, 1e-6), 0.0), 1.0)

        if hz - ramp_height(hx, p.gamma) < p.recovery_clearance:
            u = min(u, 0.55)
        s = smoothstep(u)

        # 矢状面控制（V10 PD）
        st = p.gamma + math.radians(
            p.stance_front_deg + (p.stance_back_deg - p.stance_front_deg) * s
        )
        sw = p.gamma + math.radians(
            p.swing_back_deg + (p.swing_front_deg - p.swing_back_deg) * s
        )
        skn = math.radians(p.swing_knee_flex_deg * math.sin(math.pi * u))
        skst = math.radians(p.stance_knee_deg)
        ls = support == "left"

        lh_t = limited_pd(
            float(data.qpos[lh_q]),
            float(data.qvel[lh_v]),
            st if ls else sw,
            p.hip_kp,
            p.hip_kd,
            p.hip_torque_limit,
        )
        lk_t = limited_pd(
            float(data.qpos[lk_q]),
            float(data.qvel[lk_v]),
            skst if ls else skn,
            p.knee_kp,
            p.knee_kd,
            p.knee_torque_limit,
        )
        rh_t = limited_pd(
            float(data.qpos[rh_q]),
            float(data.qvel[rh_v]),
            st if not ls else sw,
            p.hip_kp,
            p.hip_kd,
            p.hip_torque_limit,
        )
        rk_t = limited_pd(
            float(data.qpos[rk_q]),
            float(data.qvel[rk_v]),
            skst if not ls else skn,
            p.knee_kp,
            p.knee_kd,
            p.knee_torque_limit,
        )

        # --- V20: 步宽控制（冠状面）---
        # 暂时使用 V19 的控制策略作为基线（支撑腿根据 hip_y 反馈调整）
        # TODO: 后续版本实现真正的步宽轨迹规划
        hip_y_err = hy
        lat_correction = p.abd_kp * hip_y_err + p.abd_kd * vy
        lat_correction = float(
            np.clip(lat_correction, -p.abd_torque_limit, p.abd_torque_limit)
        )

        abd_tgt = math.radians(p.abd_target_deg)
        if ls:
            # 左腿支撑：向右漂时左腿外展将 CoM 推左
            la_t = -lat_correction
            ra_t = limited_pd(
                float(data.qpos[ra_q]),
                float(data.qvel[ra_v]),
                abd_tgt,
                p.abd_kp * 0.3,
                p.abd_kd * 0.3,
                p.abd_torque_limit,
            )
        else:
            # 右腿支撑：向右漂时右腿内收
            la_t = limited_pd(
                float(data.qpos[la_q]),
                float(data.qvel[la_v]),
                abd_tgt,
                p.abd_kp * 0.3,
                p.abd_kd * 0.3,
                p.abd_torque_limit,
            )
            ra_t = lat_correction

        data.ctrl[:] = (lh_t, lk_t, rh_t, rk_t, la_t, ra_t)

        mujoco.mj_step(model, data)
        max_x = max(max_x, float(data.qpos[hx_q]))
        roll = abs(float(data.qpos[hr_q]))
        hy_abs = abs(float(data.qpos[hy_q]))
        abd = max(abs(float(data.qpos[la_q])), abs(float(data.qpos[ra_q])))
        max_roll = max(max_roll, roll)
        max_hy = max(max_hy, hy_abs)
        max_abd = max(max_abd, abd)

        # 接触检测和步态事件
        left_geoms = ["left_heel", "left_sole", "left_toe", "left_sole_lat"]
        right_geoms = ["right_heel", "right_sole", "right_toe", "right_sole_lat"]
        lc, rc = get_contact_flags(model, data, "ramp", left_geoms, right_geoms)
        for foot, has_c in (("left", lc), ("right", rc)):
            if has_c:
                if cand[foot] is None:
                    cand[foot] = t
                    crep[foot] = False
                if t - float(cand[foot]) >= p.stable_contact_time:
                    if (
                        not crep[foot]
                        and foot != accepted
                        and t - last_ev > p.min_event_interval
                    ):
                        if accepted in {"left", "right"}:
                            alternations += 1
                        accepted = foot
                        support = foot
                        burst_t = t
                        last_ev = t
                        crep[foot] = True
                        swing_phase_start_recorded = False
            else:
                cand[foot] = None
                crep[foot] = False

        # CSV 记录
        if save_csv and step % 10 == 0:
            rows.append(
                {
                    "time": t,
                    "hip_x": hx,
                    "hip_y": hy,
                    "hip_z": hz,
                    "hip_y_vel": vy,
                    "support": support,
                    "phase_u": u,
                    "left_abd": float(data.qpos[la_q]),
                    "right_abd": float(data.qpos[ra_q]),
                    "y_foot_target": y_foot_target_current,
                    "alternations": alternations,
                }
            )

        # 失败检测
        if not np.all(np.isfinite(data.qpos)):
            failure = "nan_or_unstable"
            break
        if roll > math.radians(45):
            failure = "lateral_fall"
            break
        if hy_abs > 0.5:
            failure = "lateral_drift"
            break
        if hz - ramp_height(hx, p.gamma) < 0.22:
            failure = "fall_down"
            break
        if t > 4.0 and float(data.qpos[hx_q]) - start_x < 0.20:
            failure = "stuck"
            break

    fwd = max_x - start_x
    sim_t = step * p.timestep
    ok = sim_t >= p.duration * 0.9 and alternations >= 10 and fwd >= 4.0 and not failure

    # 侧向漂移率计算
    lateral_drift_rate = max_hy / max(alternations, 1) if alternations > 0 else max_hy

    summary = {
        "success": ok,
        "lateral_stable": max_roll < math.radians(15) and max_hy < 0.2,
        "forward_distance": fwd,
        "simulated_time": sim_t,
        "alternating_touchdowns": alternations,
        "failure": failure or "completed",
        "max_abs_roll_deg": math.degrees(max_roll),
        "max_abs_hip_y_m": max_hy,
        "max_abs_abd_deg": math.degrees(max_abd),
        "lateral_drift_rate_m_per_step": lateral_drift_rate,
        "params": {
            "step_width_kp": p.step_width_kp,
            "step_width_kd": p.step_width_kd,
            "step_width_nominal": p.step_width_nominal,
            "init_hip_roll_deg": p.init_hip_roll_deg,
        },
    }

    if save_prefix:
        OUT_DIR.mkdir(exist_ok=True)
        (OUT_DIR / f"{save_prefix}_summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        if save_csv and rows:
            csv_path = OUT_DIR / f"{save_prefix}_trace.csv"
            with csv_path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)

    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--step-width-kp", type=float, default=0.0)
    ap.add_argument("--step-width-kd", type=float, default=0.0)
    ap.add_argument("--roll-perturb", type=float, default=3.0)
    ap.add_argument("--duration", type=float, default=12.0)
    ap.add_argument("--save-prefix", default="v20_smoke")
    ap.add_argument("--save-csv", action="store_true")
    args = ap.parse_args()

    p = V20Params(
        step_width_kp=args.step_width_kp,
        step_width_kd=args.step_width_kd,
        init_hip_roll_deg=args.roll_perturb,
        duration=args.duration,
    )

    summary = run_simulation_v20(
        p, save_prefix=args.save_prefix, save_csv=args.save_csv
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
