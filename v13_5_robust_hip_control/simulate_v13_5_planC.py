"""V13.5 方案 C：能量整形 bang-bang hip 控制器。

设计动机（详见 v13_5_lessons.md §1-4）：
- V13 决策门发现 V10 hip 控制律是 (kp, kd) 平面孤立点。
- V13.5 方案 A（自适应步周期）/ A'（提力矩限幅）均被实验否决。
- diagnose_saturation.py 揭示 V10 hip 力矩 58.8% 时间在饱和：V10 不是 PD 跟踪，
  而是 **bang-bang 隐式饱和供能脉冲**，PD 增益是饱和占空比的形状参数。
- 方案 C：直接显式建模这个过程：用能量误差 (E* - E_actual) 决定推力幅值，
  用 swing 方向 PD 误差决定推力符号；只在能量不足时推，超过 E* 后停推。
  knee 保留 V10 PD（V13 切片显示 knee 不是孤立点主因）。

公式（每个 timestep）：
    e_E = E_star - E_current            # 能量误差 (J)
    A   = clip(k_E * e_E, 0, hip_torque_limit)   # 推力幅值，能量盈余时不推
    sgn = sign(swing 方向 PD 误差)         # 沿摆腿目标方向
    hip_tau = A * sgn

能量定义：E = 0.5 * mass_eff * (vx^2 + vz^2) + mass_eff * g * z
其中 mass_eff = hip_mass + 2 * torso_mass（与 V13b E* 同口径，mass_kg = 5.1）。

新参数（V135ParamsC）：
    E_star : 极限环能量目标，默认 52.66 J（V13b 测得）
    k_E    : 能量增益 Nm/J，默认 7.5（≈ τ_lim / E_std，使 |e_E|>=0.5J 即饱和）
    hip_torque_limit : 保留 V10 硬上限 4 Nm

V10 的 hip_kp / hip_kd 在方案 C 中不再使用（hip 不再做 PD 角度跟踪），
但仍保留在 base 参数里：(a) knee PD 需要其他增益不变；(b) 与 V10 / V13 工程对齐。
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

import mujoco
import numpy as np

ROOT = Path(__file__).resolve().parent
V10_DIR = ROOT.parent / "v10_rolling_foot_biomimetic_gait"
sys.path.insert(0, str(V10_DIR))

from simulate_rolling_foot_gait_v10 import (  # noqa: E402
    MODEL_PATH,
    SUCCESS_FORWARD,
    SUCCESS_TIME,
    SUCCESS_TOUCHDOWNS,
    classify_failure,
    contact_flags,
    initialize,
    limited_pd,
    make_row,
    ramp_height,
    smoothstep,
    write_model,
)
from simulate_rolling_foot_gait_v10 import (
    RollingFootParams as V10Params,
)

OUT_DIR = ROOT / "out"
G = 9.81


@dataclass(frozen=True)
class V135ParamsC:
    """V13.5 方案 C 参数 = V10 base + (E_star, k_E)。

    hip_kp / hip_kd / hip_torque_limit 沿用 V10 base；其中 hip_kp/kd 在方案 C
    中只用于符号方向，不再作为线性反馈增益（强度由能量误差决定）。
    """

    base: V10Params = field(default_factory=V10Params)
    E_star: float = 52.66  # J，极限环能量目标（V13b 测得 52.66 ± 0.53）
    k_E: float = 7.5  # Nm/J，能量误差 -> 推力幅值的增益
    # E_dead 设为 0：只要能量低于 E* 就推；如需"死区"放回正值
    E_dead: float = 0.0

    def __getattr__(self, name):
        # 透传到 V10 base：knee_kp/kd, foot_radius 等
        return getattr(self.base, name)


def _effective_mass(p: V10Params) -> float:
    """与 V13b E_star 同口径：m = hip_mass + 2 * torso_mass。"""
    return float(p.hip_mass + 2.0 * p.torso_mass)


def _mechanical_energy(p: V10Params, data: mujoco.MjData) -> float:
    """就地 KE + PE（hip body 平动近似），与 common.energy_metrics 同公式。"""
    m = _effective_mass(p)
    vx = float(data.qvel[0])
    vz = float(data.qvel[1])
    z = float(data.qpos[1])
    return 0.5 * m * (vx * vx + vz * vz) + m * G * z


def control_planC(
    params: V135ParamsC,
    data: mujoco.MjData,
    t: float,
    support_foot: str,
    burst_start_t: float,
    E_current: float,
) -> tuple[float, float, float, float, str, float, float]:
    """方案 C 控制律。

    返回 (l_hip, l_knee, r_hip, r_knee, mode, e_E, hip_amp)
    后两项用于诊断：能量误差和当前 hip 推力幅值。
    """
    p = params.base
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
    left_hip_target = stance_target if left_is_support else swing_target
    right_hip_target = stance_target if not left_is_support else swing_target
    left_knee_target = stance_knee if left_is_support else swing_knee
    right_knee_target = stance_knee if not left_is_support else swing_knee

    # ---- hip：能量整形 bang-bang -------------------------------------------
    e_E = params.E_star - E_current
    drive = e_E - params.E_dead
    if drive <= 0.0:
        hip_amp = 0.0  # 能量已超过目标，不推
    else:
        hip_amp = float(np.clip(params.k_E * drive, 0.0, p.hip_torque_limit))

    # 推力方向：沿 swing 方向 PD 误差符号。stance 腿无需主动推（让其自然支撑+落腿），
    # 但 V10 stance 也有 PD 力矩去维持躯干，所以这里也按 sign(target - q) 给 stance 推一份。
    def _sign_err(idx_q: int, idx_v: int, target: float) -> float:
        err = (target - float(data.qpos[idx_q])) - 0.0 * float(data.qvel[idx_v])
        if err > 1e-4:
            return 1.0
        if err < -1e-4:
            return -1.0
        return 0.0

    l_hip_sgn = _sign_err(2, 2, left_hip_target)
    r_hip_sgn = _sign_err(5, 5, right_hip_target)
    left_hip_tau = hip_amp * l_hip_sgn
    right_hip_tau = hip_amp * r_hip_sgn

    # ---- knee：保留 V10 PD（V13 切片确认 knee 不是孤立点的主因） ----------
    left_knee_tau = limited_pd(
        float(data.qpos[3]),
        float(data.qvel[3]),
        left_knee_target,
        p.knee_kp,
        p.knee_kd,
        p.knee_torque_limit,
    )
    right_knee_tau = limited_pd(
        float(data.qpos[6]),
        float(data.qvel[6]),
        right_knee_target,
        p.knee_kp,
        p.knee_kd,
        p.knee_torque_limit,
    )

    return (
        left_hip_tau,
        left_knee_tau,
        right_hip_tau,
        right_knee_tau,
        mode,
        float(e_E),
        float(hip_amp),
    )


def run_simulation(
    params: V135ParamsC,
    save_prefix: str | None = None,
    sample_hz: float = 120.0,
):
    p = params.base
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
    positive_input_energy = 0.0
    net_work = 0.0
    rows: list[dict] = []
    failure = ""
    mode = "left_stance"
    sample_stride = max(1, int(round(1.0 / (p.timestep * sample_hz))))

    energy_err_sum = 0.0
    energy_err_count = 0
    energy_history: list[tuple[float, float, float, float]] = []  # (t, E, e_E, hip_amp)
    hip_amp_active_count = 0
    hip_amp_total_count = 0

    for step in range(int(p.duration / p.timestep)):
        t = step * p.timestep
        E_current = _mechanical_energy(p, data)
        tau = control_planC(params, data, t, support_foot, burst_start_t, E_current)
        data.ctrl[:] = tau[:4]
        input_power = sum(
            float(data.ctrl[i]) * float(data.qvel[j])
            for i, j in zip(range(4), [2, 3, 5, 6])
        )
        positive_input_energy += max(0.0, input_power) * p.timestep
        net_work += input_power * p.timestep
        mode = str(tau[4])
        e_E = float(tau[5])
        hip_amp = float(tau[6])
        energy_err_sum += abs(e_E)
        energy_err_count += 1
        hip_amp_total_count += 1
        if hip_amp > 1e-6:
            hip_amp_active_count += 1
        if step % sample_stride == 0:
            energy_history.append((t, E_current, e_E, hip_amp))

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
                contact_events.append({"time": t, "foot": foot, "E": E_current})
                break

        if step % sample_stride == 0:
            rows.append(
                make_row(
                    model,
                    data,
                    p,
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

        failure = classify_failure(model, data, p, start_x, t)
        if failure:
            break

    if not rows:
        left_contact, right_contact = contact_flags(model, data)
        rows.append(
            make_row(
                model,
                data,
                p,
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
    score = (
        alternations * 200.0
        + simulated_time * 80.0
        + forward * 60.0
        - 3.0 * positive_input_energy
    )
    if success:
        score += 2000.0
    if failure:
        score -= 300.0

    mean_energy_error_J = (
        (energy_err_sum / energy_err_count) if energy_err_count else float("nan")
    )
    hip_duty = (
        (hip_amp_active_count / hip_amp_total_count) if hip_amp_total_count else 0.0
    )

    summary = {
        "params": asdict(p),
        "v135c_extra": {
            "E_star": params.E_star,
            "k_E": params.k_E,
            "E_dead": params.E_dead,
            "mass_eff_kg": _effective_mass(p),
            "mean_energy_error_J": mean_energy_error_J,
            "hip_active_duty": hip_duty,
            "energy_history_head": energy_history[:8],
            "energy_history_tail": energy_history[-8:],
        },
        "score": score,
        "success": success,
        "alternating_touchdowns": alternations,
        "contact_events": contact_events[:64],  # 防止 summary 过大
        "forward_distance": forward,
        "simulated_time": simulated_time,
        "failure": failure or "completed",
        "active_input_energy_j": positive_input_energy,
        "net_actuator_work_j": net_work,
        "energy_per_alternation_j": positive_input_energy / max(1, alternations),
        "quasi_passive": True,
        "pure_passive": False,
        "controller": "v13_5_planC_energy_shaping",
    }

    if save_prefix:
        OUT_DIR.mkdir(exist_ok=True)
        with (OUT_DIR / f"{save_prefix}_data.csv").open(
            "w", newline="", encoding="utf-8"
        ) as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        # 单独把能量轨迹存一个紧凑 csv
        with (OUT_DIR / f"{save_prefix}_energy.csv").open(
            "w", newline="", encoding="utf-8"
        ) as f:
            w = csv.writer(f)
            w.writerow(["t", "E", "e_E", "hip_amp"])
            w.writerows(energy_history)
        (OUT_DIR / f"{save_prefix}_summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return rows, summary


def _baseline_v10() -> V10Params:
    """与 V13b / V13 BASELINE 同口径，是 V13b E_star 测量所基于的物理。"""
    return V10Params(
        slope_deg=0.0,
        gait_period=0.80,
        hip_torque_limit=4.0,
        knee_torque_limit=4.0,
        hip_kp=30.0,
        hip_kd=6.0,
        knee_kp=16.0,
        knee_kd=2.0,
        initial_vx=0.03,
        torso_mass=0.05,
        foot_length=0.12,
        foot_radius=0.04,
        ankle_stiffness=10.0,
        ankle_damping=0.08,
        duration=12.0,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=float, default=12.0)
    parser.add_argument("--E_star", type=float, default=52.66)
    parser.add_argument("--k_E", type=float, default=7.5)
    parser.add_argument("--save-prefix", type=str, default="v13_5_planC_baseline")
    args = parser.parse_args()
    base = _baseline_v10()
    base = type(base)(**{**asdict(base), "duration": args.duration})
    params = V135ParamsC(base=base, E_star=args.E_star, k_E=args.k_E)
    _, summary = run_simulation(params, save_prefix=args.save_prefix, sample_hz=160.0)
    out = {
        "success": summary["success"],
        "alt": summary["alternating_touchdowns"],
        "dist": summary["forward_distance"],
        "sim_t": summary["simulated_time"],
        "fail": summary["failure"],
        "mean_energy_error_J": summary["v135c_extra"]["mean_energy_error_J"],
        "hip_active_duty": summary["v135c_extra"]["hip_active_duty"],
        "controller": summary["controller"],
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
