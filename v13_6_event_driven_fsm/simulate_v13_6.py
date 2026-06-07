"""V13.6 事件驱动 FSM hip 控制律。

设计动机（详见 v13_5_robust_hip_control/v13_5_lessons.md §10.2）：
- V13.5 三方案（A 步周期前馈 / A' 提力矩限幅 / C 能量整形 bang-bang）均被实验否决。
- 教训：V10 的稳定性来自 hip 力矩 ⊗ 触地相位的**隐式时序锁定**——
  任何"单一标量目标"（角度 / 饱和点 / 整机能量）压成一维都会丢失稳定信息。
- V14（已完成机构维度孤立点验证）也间接证明这点。
- V13.6 路线：把 V10 的隐式 bang-bang 解构成 4 段显式 phase，
  每段独立的 (k_E, k_PD, τ_max, target) 三元组，使时序锁定从隐式变显式。

状态集合：
  stance_early   触地后 0~50% 步周期    （u ∈ [0,   0.5]，支撑腿前期）
  stance_late    触地后 50~100%         （u ∈ [0.5, 1.0]，支撑腿后期 push-off 准备）
  swing_thrust   摆动腿前半段          （u ∈ [0,   0.5]，能量注入）
  swing_retract  摆动腿后半段          （u ∈ [0.5, 1.0]，被动摆回）

状态切换：
  stance_* ↔ swing_* 由 contact_events 触发（V10 已有 stable_contact_time + min_event_interval 抗抖）
  stance_early → stance_late : u ≥ 0.5
  swing_thrust → swing_retract: u ≥ 0.5 OR clearance > recovery_clearance

每 phase 力矩：
  e_E = E_phase_target - E_current        # 仅在 k_E>0 的 phase 有意义
  e_q = target - q_hip
  A_energy = clip(k_E * e_E, 0, τ_max)    # 能量不足则推
  sgn      = sign(e_q)                    # 沿 phase target 方向
  PD       = k_PD * e_q - kd * qdot
  if k_E == 0:                            # PD-only phase（stance_*, swing_retract）
      hip_tau = clip(PD, -τ_max, τ_max)
  else:                                   # 推力 phase（swing_thrust）
      alpha   = smoothstep((u - 0.85) / 0.15)  # 末段 PD 平滑过渡
      hip_tau = clip(A_energy * sgn + alpha * PD, -τ_max, τ_max)

康复设备应用对位（每 phase ↔ 临床步态周期）：
  stance_early  ↔ Loading Response + Mid-Stance（足底压力传感器主接触）
  stance_late   ↔ Terminal Stance + Pre-Swing  （趾压力上升 → 触发 push-off 检测）
  swing_thrust  ↔ Initial Swing                 （IMU 检测髋抬高 → 主动注能）
  swing_retract ↔ Mid/Terminal Swing            （角速度过零 → 准备落地）
传感映射：触地切换由鞋底压力开关；u 由内部步周期计时；clearance 由髋部 IMU 高度积分。
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Optional

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


# ---------------------------------------------------------------------------
# Phase-local 参数三元组
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class PhaseParams:
    """每 phase 暴露给康复师的独立参数：能量增益 / PD 跟踪增益 / 力矩限幅 / 阻尼。

    target 角度不再 phase-local：使用与 V10 同形式的 smoothstep 连续目标，
    避免 phase 切换时刻的角度阶跃破坏时序锁定（smoke 测试已确认 phase-local target 会摔）。
    Phase 只控制 *力如何作用* 而不是 *目标在哪里* —— 对应临床直觉：
    医生调节"该相位用多大力"，目标轨迹由整体步态时序决定。

    若 k_E > 0：phase 内为能量整形 bang-bang，PD 仅作末段平滑过渡（u>0.85 渐入）。
    若 k_E == 0：phase 内为纯 PD 跟踪（与 V10 同形式）。
    """

    k_E: float
    k_PD: float
    tau_max: float
    kd: float = 6.0
    E_target: float = 52.66  # J，仅 k_E>0 时使用，默认 V13b 测得极限环能量


@dataclass(frozen=True)
class V136Params:
    """V13.6 完整参数 = V10 base + 4 个 phase 三元组。

    base 中 hip_kp/kd/torque_limit 不再直接用（被 phase params 覆盖），保留以兼容 V10 helpers。
    knee 仍用 base.knee_kp/kd/torque_limit 的 V10 PD（V13 切片显示 knee 不是孤立点主因）。
    """

    base: V10Params = field(default_factory=V10Params)
    # 默认参数经 baseline 调参确定（详见 README §Step A）：
    # stance_*  : 强 PD（k_PD=30, kd=6, τ=4），与 V10 同档跟踪 smoothstep stance 目标
    # swing_thrust : 能量整形为主（k_E=7.5）+ 弱 PD（k_PD=10）做末段平滑
    # swing_retract: 弱限幅 PD（τ=2），鼓励被动摆回
    stance_early: PhaseParams = field(
        default_factory=lambda: PhaseParams(k_E=0.0, k_PD=30.0, tau_max=4.0, kd=6.0)
    )
    stance_late: PhaseParams = field(
        default_factory=lambda: PhaseParams(k_E=0.0, k_PD=30.0, tau_max=4.0, kd=6.0)
    )
    swing_thrust: PhaseParams = field(
        default_factory=lambda: PhaseParams(
            k_E=7.5, k_PD=10.0, tau_max=4.0, kd=6.0, E_target=52.66
        )
    )
    swing_retract: PhaseParams = field(
        default_factory=lambda: PhaseParams(k_E=0.0, k_PD=30.0, tau_max=2.0, kd=6.0)
    )

    def __getattr__(self, name):
        return getattr(self.base, name)


# ---------------------------------------------------------------------------
# 能量计算：与 V13b / plan C 同口径 (mass = hip + 2*torso)
# ---------------------------------------------------------------------------
def _effective_mass(p: V10Params) -> float:
    return float(p.hip_mass + 2.0 * p.torso_mass)


def _mechanical_energy(p: V10Params, data: mujoco.MjData) -> float:
    m = _effective_mass(p)
    vx = float(data.qvel[0])
    vz = float(data.qvel[1])
    z = float(data.qpos[1])
    return 0.5 * m * (vx * vx + vz * vz) + m * G * z


# ---------------------------------------------------------------------------
# FSM 单腿状态判定
# ---------------------------------------------------------------------------
def _leg_phase(
    is_support: bool, u: float, clearance: float, recovery_clearance: float
) -> str:
    """根据是否 support、相位 u、髋部 clearance 返回该腿当前 phase 名。

    切换条件（已修订，参见 README §实现细节）：
      stance_early → stance_late    : u ≥ 0.5
      swing_thrust → swing_retract  : u ≥ 0.5
      （注：原设计含 "clearance > recovery_clearance" 防早落地条件，但 V10 的
        recovery_clearance=0.38 m 是 *髋部高度* 阈值，正常步态期间髋部恒高于此值，
        会让该条件恒真——swing_thrust 永远不激活。smoke 测试已确认。
        改为只看 u；clearance 由 V10 原有 recovery 模式继续保护异常情况。）

    异常保护：clearance < recovery_clearance（髋部过低，疑似跌倒前奏）时，
    强制把 stance 段 phase 退回 stance_early（不让 push-off 推力继续作恶）。
    """
    if is_support:
        if clearance < recovery_clearance:
            return "stance_early"  # 髋部过低，退回保守 PD
        return "stance_early" if u < 0.5 else "stance_late"
    # swing
    return "swing_thrust" if u < 0.5 else "swing_retract"


def _phase_torque(
    pp: PhaseParams,
    q: float,
    qd: float,
    target: float,
    u: float,
    E_current: float,
) -> tuple[float, float, float]:
    """phase 力矩计算。target 为 V10-style smoothstep 连续目标（外部传入）。

    返回 (tau, e_E, A_energy)。
    """
    e_q = target - q
    pd = pp.k_PD * e_q - pp.kd * qd
    if pp.k_E <= 0.0:
        tau = float(np.clip(pd, -pp.tau_max, pp.tau_max))
        return tau, 0.0, 0.0
    e_E = pp.E_target - E_current
    drive = max(0.0, e_E)
    A_energy = float(np.clip(pp.k_E * drive, 0.0, pp.tau_max))
    sgn = 1.0 if e_q > 1e-4 else (-1.0 if e_q < -1e-4 else 0.0)
    # phase 末段 PD 平滑过渡（u>0.85 渐入），不破坏中段时序锁定
    alpha = smoothstep(max(0.0, (u - 0.85) / 0.15))
    tau = float(np.clip(A_energy * sgn + alpha * pd, -pp.tau_max, pp.tau_max))
    return tau, float(e_E), A_energy


def control_v136(
    params: V136Params,
    data: mujoco.MjData,
    t: float,
    support_foot: str,
    burst_start_t: float,
    E_current: float,
) -> tuple[float, float, float, float, str, str, str, float, float]:
    """V13.6 FSM 控制律。

    返回 (l_hip, l_knee, r_hip, r_knee, mode_label, left_phase, right_phase, e_E_swing, A_swing)
    """
    p = params.base
    hip_x = float(data.qpos[0])
    hip_z = float(data.qpos[1])
    clearance = hip_z - ramp_height(hip_x, p)
    u = min(max((t - burst_start_t) / max(p.gait_period, 1e-6), 0.0), 1.0)
    # 异常恢复：髋部过低时压缩相位（与 V10 同处理）
    if clearance < p.recovery_clearance:
        u = min(u, 0.55)
    s = smoothstep(u)
    offset = p.gamma
    # V10-style 连续目标轨迹（不引入 phase 切换时刻的阶跃）
    stance_target = offset + math.radians(
        p.stance_front_deg + (p.stance_back_deg - p.stance_front_deg) * s
    )
    swing_target = offset + math.radians(
        p.swing_back_deg + (p.swing_front_deg - p.swing_back_deg) * s
    )

    left_is_support = support_foot == "left"
    left_phase = _leg_phase(left_is_support, u, clearance, p.recovery_clearance)
    right_phase = _leg_phase(not left_is_support, u, clearance, p.recovery_clearance)

    phase_map = {
        "stance_early": params.stance_early,
        "stance_late": params.stance_late,
        "swing_thrust": params.swing_thrust,
        "swing_retract": params.swing_retract,
    }

    l_target = stance_target if left_is_support else swing_target
    r_target = stance_target if not left_is_support else swing_target

    l_hip_tau, l_eE, l_A = _phase_torque(
        phase_map[left_phase],
        float(data.qpos[2]),
        float(data.qvel[2]),
        l_target,
        u,
        E_current,
    )
    r_hip_tau, r_eE, r_A = _phase_torque(
        phase_map[right_phase],
        float(data.qpos[5]),
        float(data.qvel[5]),
        r_target,
        u,
        E_current,
    )

    # knee：保留 V10 PD（V13 切片确认 knee 不是孤立点主因）
    swing_knee = math.radians(p.swing_knee_flex_deg * math.sin(math.pi * u))
    stance_knee = math.radians(p.stance_knee_deg)
    left_knee_target = stance_knee if left_is_support else swing_knee
    right_knee_target = stance_knee if not left_is_support else swing_knee
    l_knee_tau = limited_pd(
        float(data.qpos[3]),
        float(data.qvel[3]),
        left_knee_target,
        p.knee_kp,
        p.knee_kd,
        p.knee_torque_limit,
    )
    r_knee_tau = limited_pd(
        float(data.qpos[6]),
        float(data.qvel[6]),
        right_knee_target,
        p.knee_kp,
        p.knee_kd,
        p.knee_torque_limit,
    )

    if left_phase == "swing_thrust":
        eE_diag, A_diag = l_eE, l_A
    elif right_phase == "swing_thrust":
        eE_diag, A_diag = r_eE, r_A
    else:
        eE_diag, A_diag = 0.0, 0.0

    mode_label = f"{'L' if left_is_support else 'R'}:{left_phase}|{right_phase}"
    return (
        l_hip_tau,
        l_knee_tau,
        r_hip_tau,
        r_knee_tau,
        mode_label,
        left_phase,
        right_phase,
        eE_diag,
        A_diag,
    )


# ---------------------------------------------------------------------------
# 主仿真循环（结构沿用 V10 / plan C，更换 control 调用 + phase 时序记录）
# ---------------------------------------------------------------------------
def run_simulation(
    params: V136Params,
    save_prefix: Optional[str] = None,
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
    candidate_start_t: dict[str, Optional[float]] = {"left": None, "right": None}
    contact_reported = {"left": False, "right": False}
    last_event_t = -1.0
    burst_start_t = -p.gait_period
    alternations = 0
    contact_events: list[dict] = []
    positive_input_energy = 0.0
    net_work = 0.0
    rows: list[dict] = []
    failure = ""
    sample_stride = max(1, int(round(1.0 / (p.timestep * sample_hz))))

    phase_timeline: list[tuple[float, str, str]] = []  # (t, left_phase, right_phase)
    last_left_phase = ""
    last_right_phase = ""
    phase_durations = {
        "stance_early": 0.0,
        "stance_late": 0.0,
        "swing_thrust": 0.0,
        "swing_retract": 0.0,
    }
    phase_torque_int = {
        "stance_early": 0.0,
        "stance_late": 0.0,
        "swing_thrust": 0.0,
        "swing_retract": 0.0,
    }  # ∫|τ| dt 累计

    for step in range(int(p.duration / p.timestep)):
        t = step * p.timestep
        E_current = _mechanical_energy(p, data)
        tau = control_v136(params, data, t, support_foot, burst_start_t, E_current)
        l_hip, l_knee, r_hip, r_knee = tau[0], tau[1], tau[2], tau[3]
        mode_label = tau[4]
        left_phase = tau[5]
        right_phase = tau[6]
        eE_diag = tau[7]
        A_diag = tau[8]
        data.ctrl[:] = (l_hip, l_knee, r_hip, r_knee)
        input_power = sum(
            float(data.ctrl[i]) * float(data.qvel[j])
            for i, j in zip(range(4), [2, 3, 5, 6])
        )
        positive_input_energy += max(0.0, input_power) * p.timestep
        net_work += input_power * p.timestep

        # 累计 phase duration 和 torque 积分（左右合计）
        phase_durations[left_phase] += p.timestep
        phase_durations[right_phase] += p.timestep
        phase_torque_int[left_phase] += abs(l_hip) * p.timestep
        phase_torque_int[right_phase] += abs(r_hip) * p.timestep

        if (left_phase != last_left_phase) or (right_phase != last_right_phase):
            phase_timeline.append((t, left_phase, right_phase))
            last_left_phase, last_right_phase = left_phase, right_phase

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
            row = make_row(
                model,
                data,
                p,
                t,
                left_contact,
                right_contact,
                support_foot,
                mode_label,
                (l_hip, l_knee, r_hip, r_knee),
                input_power,
                positive_input_energy,
            )
            row["E_current"] = float(E_current)
            row["e_E_swing"] = float(eE_diag)
            row["A_swing"] = float(A_diag)
            row["left_phase"] = left_phase
            row["right_phase"] = right_phase
            rows.append(row)

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
                "init",
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
        "params": asdict(p),
        "v136_phases": {
            "stance_early": asdict(params.stance_early),
            "stance_late": asdict(params.stance_late),
            "swing_thrust": asdict(params.swing_thrust),
            "swing_retract": asdict(params.swing_retract),
        },
        "phase_durations_s": phase_durations,
        "phase_torque_integral_Nms": phase_torque_int,
        "phase_timeline_head": phase_timeline[:64],
        "phase_timeline_tail": phase_timeline[-16:],
        "phase_transitions": len(phase_timeline),
        "score": score,
        "success": success,
        "alternating_touchdowns": alternations,
        "contact_events": contact_events[:64],
        "forward_distance": forward,
        "simulated_time": simulated_time,
        "failure": failure or "completed",
        "active_input_energy_j": positive_input_energy,
        "net_actuator_work_j": net_work,
        "energy_per_alternation_j": positive_input_energy / max(1, alternations),
        "quasi_passive": True,
        "pure_passive": False,
        "controller": "v13_6_event_driven_fsm",
    }

    if save_prefix:
        OUT_DIR.mkdir(exist_ok=True)
        with (OUT_DIR / f"{save_prefix}_data.csv").open(
            "w", newline="", encoding="utf-8"
        ) as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        # 单独保存 phase 时序
        with (OUT_DIR / f"{save_prefix}_phases.csv").open(
            "w", newline="", encoding="utf-8"
        ) as f:
            w = csv.writer(f)
            w.writerow(["time", "left_phase", "right_phase"])
            for t_evt, lp, rp in phase_timeline:
                w.writerow([t_evt, lp, rp])
        (OUT_DIR / f"{save_prefix}_summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return rows, summary


def _baseline_v10() -> V10Params:
    """与 V13 / V13b / plan C 同口径。"""
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


def make_v136_params(base: Optional[V10Params] = None, **phase_overrides) -> V136Params:
    """便捷构造：base + 可选 phase 字典覆盖。"""
    base = base or _baseline_v10()
    return V136Params(
        base=base,
        stance_early=phase_overrides.get("stance_early", V136Params().stance_early),
        stance_late=phase_overrides.get("stance_late", V136Params().stance_late),
        swing_thrust=phase_overrides.get("swing_thrust", V136Params().swing_thrust),
        swing_retract=phase_overrides.get("swing_retract", V136Params().swing_retract),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=float, default=12.0)
    parser.add_argument("--save-prefix", type=str, default="v13_6_baseline")
    args = parser.parse_args()
    base = _baseline_v10()
    base = replace(base, duration=args.duration)
    params = make_v136_params(base=base)
    _, summary = run_simulation(params, save_prefix=args.save_prefix, sample_hz=160.0)
    out = {
        "success": summary["success"],
        "alt": summary["alternating_touchdowns"],
        "dist": summary["forward_distance"],
        "sim_t": summary["simulated_time"],
        "fail": summary["failure"],
        "phase_transitions": summary["phase_transitions"],
        "phase_durations_s": summary["phase_durations_s"],
        "controller": summary["controller"],
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
