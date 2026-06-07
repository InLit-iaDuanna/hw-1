"""V13.5 鲁棒 hip 控制（方案 A）：步周期前馈 + PD。

V13 决策门发现 V10 hip 控制律是 (kp, kd) 平面孤立点 + 共振线。根因：
control 用静态 `gait_period` 算相位 u = (t - burst_start_t) / gait_period，
任何让自然摆动周期偏离 baseline gait_period 的扰动都会让 u 错位 → 摔。

V13.5 方案 A：burst 触发时记录"上一步实测时长"，EMA 估计真实步周期 T_meas，
用 T_meas 代替 gait_period 算相位。其余部分（IK / 初始化 / 接触检测 / 失败分类）
全部复用 V10。

新增超参：
  T_meas_alpha: EMA 平滑因子 (0..1)，0 = 完全用初始 gait_period，1 = 立刻跟上一步
  T_meas_min, T_meas_max: 实测周期截断范围（防异常值）
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


@dataclass(frozen=True)
class V135Params:
    """V13.5 参数 = V10 全部 + 步周期估计三参数。"""

    base: V10Params = field(default_factory=V10Params)
    T_meas_alpha: float = 0.4
    T_meas_min: float = 0.4
    T_meas_max: float = 1.6

    def __getattr__(self, name):
        return getattr(self.base, name)


def control_adaptive(
    params: V135Params,
    data: mujoco.MjData,
    t: float,
    support_foot: str,
    burst_start_t: float,
    T_meas: float,
):
    hip_x = float(data.qpos[0])
    hip_z = float(data.qpos[1])
    clearance = hip_z - ramp_height(hip_x, params.base)
    mode = "left_stance" if support_foot == "left" else "right_stance"
    period_eff = max(T_meas, 1e-3)
    u = min(max((t - burst_start_t) / period_eff, 0.0), 1.0)
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

    p = params.base
    left_hip_tau = limited_pd(
        float(data.qpos[2]),
        float(data.qvel[2]),
        left_hip_target,
        p.hip_kp,
        p.hip_kd,
        p.hip_torque_limit,
    )
    left_knee_tau = limited_pd(
        float(data.qpos[3]),
        float(data.qvel[3]),
        left_knee_target,
        p.knee_kp,
        p.knee_kd,
        p.knee_torque_limit,
    )
    right_hip_tau = limited_pd(
        float(data.qpos[5]),
        float(data.qvel[5]),
        right_hip_target,
        p.hip_kp,
        p.hip_kd,
        p.hip_torque_limit,
    )
    right_knee_tau = limited_pd(
        float(data.qpos[6]),
        float(data.qvel[6]),
        right_knee_target,
        p.knee_kp,
        p.knee_kd,
        p.knee_torque_limit,
    )
    return left_hip_tau, left_knee_tau, right_hip_tau, right_knee_tau, mode


def run_simulation(
    params: V135Params,
    save_prefix: str | None = None,
    sample_hz: float = 120.0,
):
    base = params.base
    write_model(base)
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    data = mujoco.MjData(model)
    initialize(model, data, base)

    start_x = float(data.qpos[0])
    max_x = start_x
    support_foot = "left"
    accepted_contact = ""
    candidate_start_t: dict[str, float | None] = {"left": None, "right": None}
    contact_reported = {"left": False, "right": False}
    last_event_t = -1.0
    burst_start_t = -base.gait_period
    alternations = 0
    contact_events: list[dict] = []
    positive_input_energy = 0.0
    net_work = 0.0
    rows: list[dict] = []
    failure = ""
    mode = "left_stance"
    sample_stride = max(1, int(round(1.0 / (base.timestep * sample_hz))))

    T_meas = base.gait_period  # EMA 估计的实测步周期
    last_burst_t: float | None = None
    period_history: list[float] = []

    for step in range(int(base.duration / base.timestep)):
        t = step * base.timestep
        tau = control_adaptive(params, data, t, support_foot, burst_start_t, T_meas)
        data.ctrl[:] = tau[:4]
        input_power = sum(
            float(data.ctrl[i]) * float(data.qvel[j])
            for i, j in zip(range(4), [2, 3, 5, 6])
        )
        positive_input_energy += max(0.0, input_power) * base.timestep
        net_work += input_power * base.timestep
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
                if t - float(candidate_start_t[foot]) >= base.stable_contact_time:
                    stable_feet.append(foot)
            else:
                candidate_start_t[foot] = None
                contact_reported[foot] = False

        for foot in stable_feet:
            if (
                not contact_reported[foot]
                and foot != accepted_contact
                and t - last_event_t > base.min_event_interval
            ):
                if accepted_contact in {"left", "right"}:
                    alternations += 1
                    if last_burst_t is not None:
                        dt_step = t - last_burst_t
                        dt_step = max(
                            params.T_meas_min, min(params.T_meas_max, dt_step)
                        )
                        T_meas = (
                            1.0 - params.T_meas_alpha
                        ) * T_meas + params.T_meas_alpha * dt_step
                        period_history.append(dt_step)
                accepted_contact = foot
                support_foot = foot
                burst_start_t = t
                last_event_t = t
                last_burst_t = t
                contact_reported[foot] = True
                contact_events.append({"time": t, "foot": foot, "T_meas": T_meas})
                break

        if step % sample_stride == 0:
            rows.append(
                make_row(
                    model,
                    data,
                    base,
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

        failure = classify_failure(model, data, base, start_x, t)
        if failure:
            break

    if not rows:
        left_contact, right_contact = contact_flags(model, data)
        rows.append(
            make_row(
                model,
                data,
                base,
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

    summary = {
        "params": asdict(base),
        "v135_extra": {
            "T_meas_alpha": params.T_meas_alpha,
            "T_meas_min": params.T_meas_min,
            "T_meas_max": params.T_meas_max,
            "T_meas_final": T_meas,
            "period_history": period_history,
        },
        "score": score,
        "success": success,
        "alternating_touchdowns": alternations,
        "contact_events": contact_events,
        "forward_distance": forward,
        "simulated_time": simulated_time,
        "failure": failure or "completed",
        "active_input_energy_j": positive_input_energy,
        "net_actuator_work_j": net_work,
        "energy_per_alternation_j": positive_input_energy / max(1, alternations),
        "quasi_passive": True,
        "pure_passive": False,
        "controller": "v13_5_adaptive_period_pd",
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
    parser.add_argument("--alpha", type=float, default=0.4)
    parser.add_argument("--save-prefix", type=str, default="v13_5_baseline")
    parser.add_argument("--hip-kp", type=float, default=30.0)
    parser.add_argument("--hip-kd", type=float, default=6.0)
    args = parser.parse_args()
    base = V10Params(
        slope_deg=0.0,
        gait_period=0.80,
        hip_torque_limit=4.0,
        knee_torque_limit=4.0,
        hip_kp=args.hip_kp,
        hip_kd=args.hip_kd,
        knee_kp=16.0,
        knee_kd=2.0,
        initial_vx=0.03,
        torso_mass=0.05,
        foot_length=0.12,
        foot_radius=0.04,
        ankle_stiffness=10.0,
        ankle_damping=0.08,
        duration=args.duration,
    )
    params = V135Params(base=base, T_meas_alpha=args.alpha)
    _, summary = run_simulation(params, save_prefix=args.save_prefix, sample_hz=160.0)
    print(
        json.dumps(
            {
                "success": summary["success"],
                "alt": summary["alternating_touchdowns"],
                "dist": summary["forward_distance"],
                "fail": summary["failure"],
                "T_meas_final": summary["v135_extra"]["T_meas_final"],
                "period_history": summary["v135_extra"]["period_history"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
