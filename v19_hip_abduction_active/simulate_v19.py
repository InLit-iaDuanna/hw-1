"""V19: 3D 行走 + 主动髋外展 PD 侧向稳定。"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import mujoco
import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent))  # Add parent for common/
from model_3d_v19 import MODEL_PATH, V19Params, write_model  # noqa: E402

from common.control_utils import limited_pd, ramp_height, smoothstep

OUT_DIR = ROOT / "out"


def _jaddr(model, name):
    jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)
    return model.jnt_qposadr[jid], model.jnt_dofadr[jid]


def _contacts(model, data):
    rid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "ramp")
    lg = [
        mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, n)
        for n in ("left_heel", "left_sole", "left_toe", "left_sole_lat")
    ]
    rg = [
        mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, n)
        for n in ("right_heel", "right_sole", "right_toe", "right_sole_lat")
    ]
    lc = rc = False
    for i in range(data.ncon):
        pair = {data.contact[i].geom1, data.contact[i].geom2}
        if rid in pair:
            if any(g in pair for g in lg):
                lc = True
            if any(g in pair for g in rg):
                rc = True
    return lc, rc


def run_simulation_v19(p: V19Params, save_prefix: str | None = None):
    write_model(p)
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    data = mujoco.MjData(model)

    hx_q, hx_v = _jaddr(model, "hip_x")
    hy_q, _ = _jaddr(model, "hip_y")
    hz_q, hz_v = _jaddr(model, "hip_z")
    hr_q, _ = _jaddr(model, "hip_roll")
    lh_q, lh_v = _jaddr(model, "left_hip")
    lk_q, lk_v = _jaddr(model, "left_knee")
    rh_q, rh_v = _jaddr(model, "right_hip")
    rk_q, rk_v = _jaddr(model, "right_knee")
    la_q, la_v = _jaddr(model, "left_hip_abd")
    ra_q, ra_v = _jaddr(model, "right_hip_abd")

    # 初始化
    u0 = smoothstep(p.release_phase)
    alpha = math.asin(p.step_length / (2.0 * p.leg_length))
    sz = ramp_height(0.0, gamma=p.gamma) + p.foot_radius / max(0.2, math.cos(p.gamma))
    lhi = p.gamma + alpha - 2.0 * alpha * u0
    hxi = p.leg_length * math.sin(lhi)
    hzi = sz + p.leg_length * math.cos(lhi)
    px, pz = hxi - p.swing_foot_x, hzi - (sz + p.swing_foot_clearance)
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
            math.atan2(kx - p.swing_foot_x, kz - (sz + p.swing_foot_clearance)) - rhi,
            0.0,
            math.radians(p.knee_limit_deg),
        )
    )

    data.qpos[hx_q] = hxi
    data.qpos[hy_q] = p.init_hip_y
    data.qpos[hz_q] = hzi
    data.qpos[hr_q] = math.radians(p.init_hip_roll_deg)
    data.qpos[la_q] = 0.0
    data.qpos[ra_q] = 0.0
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
    abd_tgt = math.radians(p.abd_target_deg)

    for step in range(int(p.duration / p.timestep)):
        t = step * p.timestep
        hx = float(data.qpos[hx_q])
        hz = float(data.qpos[hz_q])
        u = min(max((t - burst_t) / max(p.gait_period, 1e-6), 0.0), 1.0)
        if hz - ramp_height(hx, gamma=p.gamma) < p.recovery_clearance:
            u = min(u, 0.55)
        s = smoothstep(u)
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
        # --- V19: 主动髋外展 PD（基于 hip_y 反馈的侧向平衡控制）---
        # 支撑腿根据 hip_y 偏移调整外展角，将 CoM 推回中线
        hip_y_err = float(data.qpos[hy_q])  # 正 = 向右漂
        hip_y_vel = float(data.qvel[_jaddr(model, "hip_y")[1]])
        lat_correction = p.abd_kp * hip_y_err + p.abd_kd * hip_y_vel
        lat_correction = float(
            np.clip(lat_correction, -p.abd_torque_limit, p.abd_torque_limit)
        )
        # 支撑腿施加侧向修正，摆腿保持中立
        if ls:
            la_t = -lat_correction  # 左腿支撑：向右漂时左腿外展将 CoM 推左
            ra_t = limited_pd(
                float(data.qpos[ra_q]),
                float(data.qvel[ra_v]),
                abd_tgt,
                p.abd_kp * 0.3,
                p.abd_kd * 0.3,
                p.abd_torque_limit,
            )
        else:
            la_t = limited_pd(
                float(data.qpos[la_q]),
                float(data.qvel[la_v]),
                abd_tgt,
                p.abd_kp * 0.3,
                p.abd_kd * 0.3,
                p.abd_torque_limit,
            )
            ra_t = lat_correction  # 右腿支撑：向右漂时右腿内收
        data.ctrl[:] = (lh_t, lk_t, rh_t, rk_t, la_t, ra_t)

        mujoco.mj_step(model, data)
        max_x = max(max_x, float(data.qpos[hx_q]))
        roll = abs(float(data.qpos[hr_q]))
        hy = abs(float(data.qpos[hy_q]))
        abd = max(abs(float(data.qpos[la_q])), abs(float(data.qpos[ra_q])))
        max_roll = max(max_roll, roll)
        max_hy = max(max_hy, hy)
        max_abd = max(max_abd, abd)

        lc, rc = _contacts(model, data)
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
            else:
                cand[foot] = None
                crep[foot] = False

        if not np.all(np.isfinite(data.qpos)):
            failure = "nan_or_unstable"
            break
        if roll > math.radians(45):
            failure = "lateral_fall"
            break
        if hy > 0.5:
            failure = "lateral_drift"
            break
        if hz - ramp_height(hx, gamma=p.gamma) < 0.22:
            failure = "fall_down"
            break
        if t > 4.0 and float(data.qpos[hx_q]) - start_x < 0.20:
            failure = "stuck"
            break

    fwd = max_x - start_x
    sim_t = step * p.timestep
    ok = sim_t >= p.duration * 0.9 and alternations >= 10 and fwd >= 0.8 and not failure
    summary = {
        "success": ok,
        "lateral_stable": max_roll < math.radians(15) and max_hy < 0.15,
        "forward_distance": fwd,
        "simulated_time": sim_t,
        "alternating_touchdowns": alternations,
        "failure": failure or "completed",
        "max_abs_roll_deg": math.degrees(max_roll),
        "max_abs_hip_y_m": max_hy,
        "max_abs_abd_deg": math.degrees(max_abd),
        "params": {
            "abd_kp": p.abd_kp,
            "abd_kd": p.abd_kd,
            "init_hip_roll_deg": p.init_hip_roll_deg,
        },
    }
    if save_prefix:
        OUT_DIR.mkdir(exist_ok=True)
        (OUT_DIR / f"{save_prefix}_summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--abd-kp", type=float, default=40.0)
    ap.add_argument("--abd-kd", type=float, default=4.0)
    ap.add_argument("--roll-perturb", type=float, default=3.0)
    ap.add_argument("--abd-torque-limit", type=float, default=6.0)
    ap.add_argument("--duration", type=float, default=10.0)
    ap.add_argument("--save-prefix", default="v19_baseline")
    args = ap.parse_args()
    p = V19Params(
        abd_kp=args.abd_kp,
        abd_kd=args.abd_kd,
        init_hip_roll_deg=args.roll_perturb,
        abd_torque_limit=args.abd_torque_limit,
        duration=args.duration,
    )
    summary = run_simulation_v19(p, save_prefix=args.save_prefix)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
