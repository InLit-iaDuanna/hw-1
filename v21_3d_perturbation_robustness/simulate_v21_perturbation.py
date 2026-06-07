"""V21: V19 3D 行走 + 3D 扰动鲁棒性测试。

测试三类扰动：
1. 初始 roll 扰动（优先级 1）
2. 侧向脉冲（优先级 2）
3. 随机风（优先级 3，可选）

目标：量化 V19 最佳配置在扰动下的侧向不稳定程度。
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import mujoco
import numpy as np

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common import disturbance  # noqa: E402
from v19_hip_abduction_active.model_3d_v19 import (
    MODEL_PATH,
    V19Params,
    write_model,
)  # noqa: E402

OUT_DIR = ROOT / "out"


@dataclass(frozen=True)
class PerturbationScenario:
    """V21 3D 扰动场景。"""

    init_hip_roll_deg: float = 0.0
    lateral_impulse_n: float = 0.0
    impulse_t_s: float = 2.0
    impulse_duration_s: float = 0.05
    random_wind_std_n: float = 0.0
    wind_seed: int = 0


def _smoothstep(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * (3.0 - 2.0 * u)


def _lpd(q, qd, target, kp, kd, limit):
    return float(np.clip(kp * (target - q) - kd * qd, -limit, limit))


def _ramp_h(x, p):
    return -math.tan(p.gamma) * x


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


def run_simulation_v21(
    p: V19Params,
    scenario: PerturbationScenario,
    save_prefix: str | None = None,
):
    """V19 仿真主循环 + 3D 扰动。"""
    # 使用 scenario 中的 init_hip_roll_deg 覆盖参数
    p = V19Params(**{**asdict(p), "init_hip_roll_deg": scenario.init_hip_roll_deg})

    write_model(p)
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    data = mujoco.MjData(model)

    hx_q, hx_v = _jaddr(model, "hip_x")
    hy_q, hy_v = _jaddr(model, "hip_y")
    hz_q, hz_v = _jaddr(model, "hip_z")
    hr_q, hr_v = _jaddr(model, "hip_roll")
    lh_q, lh_v = _jaddr(model, "left_hip")
    lk_q, lk_v = _jaddr(model, "left_knee")
    rh_q, rh_v = _jaddr(model, "right_hip")
    rk_q, rk_v = _jaddr(model, "right_knee")
    la_q, la_v = _jaddr(model, "left_hip_abd")
    ra_q, ra_v = _jaddr(model, "right_hip_abd")

    # 初始化（复用 V19 逻辑）
    u0 = _smoothstep(p.release_phase)
    alpha = math.asin(p.step_length / (2.0 * p.leg_length))
    sz = _ramp_h(0.0, p) + p.foot_radius / max(0.2, math.cos(p.gamma))
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

    # 扰动配置
    impulse_spec = disturbance.ImpulseSpec(
        body_name="hip",
        force_xyz=(0.0, scenario.lateral_impulse_n, 0.0),
        t_start_s=scenario.impulse_t_s,
        duration_s=scenario.impulse_duration_s,
    )

    wind_rng = (
        np.random.default_rng(scenario.wind_seed)
        if scenario.random_wind_std_n > 0.0
        else None
    )

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
    impulse_active = False

    for step in range(int(p.duration / p.timestep)):
        t = step * p.timestep
        hx = float(data.qpos[hx_q])
        hz = float(data.qpos[hz_q])
        u = min(max((t - burst_t) / max(p.gait_period, 1e-6), 0.0), 1.0)
        if hz - _ramp_h(hx, p) < p.recovery_clearance:
            u = min(u, 0.55)
        s = _smoothstep(u)
        st = p.gamma + math.radians(
            p.stance_front_deg + (p.stance_back_deg - p.stance_front_deg) * s
        )
        sw = p.gamma + math.radians(
            p.swing_back_deg + (p.swing_front_deg - p.swing_back_deg) * s
        )
        skn = math.radians(p.swing_knee_flex_deg * math.sin(math.pi * u))
        skst = math.radians(p.stance_knee_deg)
        ls = support == "left"
        lh_t = _lpd(
            float(data.qpos[lh_q]),
            float(data.qvel[lh_v]),
            st if ls else sw,
            p.hip_kp,
            p.hip_kd,
            p.hip_torque_limit,
        )
        lk_t = _lpd(
            float(data.qpos[lk_q]),
            float(data.qvel[lk_v]),
            skst if ls else skn,
            p.knee_kp,
            p.knee_kd,
            p.knee_torque_limit,
        )
        rh_t = _lpd(
            float(data.qpos[rh_q]),
            float(data.qvel[rh_v]),
            st if not ls else sw,
            p.hip_kp,
            p.hip_kd,
            p.hip_torque_limit,
        )
        rk_t = _lpd(
            float(data.qpos[rk_q]),
            float(data.qvel[rk_v]),
            skst if not ls else skn,
            p.knee_kp,
            p.knee_kd,
            p.knee_torque_limit,
        )

        # V19 主动髋外展控制（基于 hip_y 反馈）
        hip_y_err = float(data.qpos[hy_q])
        hip_y_vel = float(data.qvel[hy_v])
        lat_correction = p.abd_kp * hip_y_err + p.abd_kd * hip_y_vel
        lat_correction = float(
            np.clip(lat_correction, -p.abd_torque_limit, p.abd_torque_limit)
        )
        if ls:
            la_t = -lat_correction
            ra_t = _lpd(
                float(data.qpos[ra_q]),
                float(data.qvel[ra_v]),
                abd_tgt,
                p.abd_kp * 0.3,
                p.abd_kd * 0.3,
                p.abd_torque_limit,
            )
        else:
            la_t = _lpd(
                float(data.qpos[la_q]),
                float(data.qvel[la_v]),
                abd_tgt,
                p.abd_kp * 0.3,
                p.abd_kd * 0.3,
                p.abd_torque_limit,
            )
            ra_t = lat_correction
        data.ctrl[:] = (lh_t, lk_t, rh_t, rk_t, la_t, ra_t)

        # 施加侧向脉冲
        impulse_active = disturbance.apply_impulse(model, data, impulse_spec, t)

        # 施加随机风（连续扰动）
        if wind_rng is not None:
            hip_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "hip")
            wind_fx = float(wind_rng.normal(0.0, scenario.random_wind_std_n))
            wind_fy = float(wind_rng.normal(0.0, scenario.random_wind_std_n))
            data.xfrc_applied[hip_id, 0] += wind_fx
            data.xfrc_applied[hip_id, 1] += wind_fy

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
        if hz - _ramp_h(hx, p) < 0.22:
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
        "scenario": asdict(scenario),
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
    ap.add_argument("--init-roll", type=float, default=0.0, help="初始 roll 扰动 (deg)")
    ap.add_argument("--lateral-impulse", type=float, default=0.0, help="侧向脉冲 (N)")
    ap.add_argument("--impulse-t", type=float, default=2.0, help="脉冲时间 (s)")
    ap.add_argument("--wind-std", type=float, default=0.0, help="随机风标准差 (N)")
    ap.add_argument("--wind-seed", type=int, default=0, help="风随机种子")
    ap.add_argument("--duration", type=float, default=10.0)
    ap.add_argument("--save-prefix", default="v21_test")
    args = ap.parse_args()

    # V19 最佳配置
    p = V19Params(
        abd_kp=40.0,
        abd_kd=4.0,
        init_hip_roll_deg=0.0,  # 将被 scenario 覆盖
        abd_torque_limit=6.0,
        duration=args.duration,
    )

    scenario = PerturbationScenario(
        init_hip_roll_deg=args.init_roll,
        lateral_impulse_n=args.lateral_impulse,
        impulse_t_s=args.impulse_t,
        random_wind_std_n=args.wind_std,
        wind_seed=args.wind_seed,
    )

    summary = run_simulation_v21(p, scenario, save_prefix=args.save_prefix)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
