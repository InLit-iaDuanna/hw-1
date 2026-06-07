"""V13.6 重构版本：使用统一仿真框架。

代码量减少约 60%，保留完整功能：
- V13.6 FSM 控制律（4-phase 显式状态机）
- 接触检测与事件驱动
- Phase timeline 记录
- 能量统计

对比原版 simulate_v13_6.py：
- 仿真循环逻辑迁移到 common.simulation_framework
- 控制律封装为 Controller 接口
- 接触检测/能量统计自动化
- 数值结果应一致（forward distance 误差 <5%）
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

import mujoco
import numpy as np

ROOT = Path(__file__).resolve().parent
HW1_ROOT = ROOT.parent
V10_DIR = HW1_ROOT / "v10_rolling_foot_biomimetic_gait"
V136_DIR = HW1_ROOT / "v13_6_event_driven_fsm"

sys.path.insert(0, str(V10_DIR))
sys.path.insert(0, str(V136_DIR))
sys.path.insert(0, str(HW1_ROOT))

from simulate_rolling_foot_gait_v10 import (  # noqa: E402
    MODEL_PATH,
    SUCCESS_FORWARD,
    SUCCESS_TIME,
    SUCCESS_TOUCHDOWNS,
    classify_failure,
    contact_flags,
    initialize,
    make_row,
    write_model,
)
from simulate_rolling_foot_gait_v10 import (
    RollingFootParams as V10Params,
)
from simulate_v13_6 import (  # noqa: E402
    V136Params,
    _mechanical_energy,
    control_v136,
)

from common.simulation_framework import (  # noqa: E402
    ContactState,
    Controller,
    DictRowRecorder,
    EnergyStats,
    FailureClassifier,
    IntegratedSimulationCallback,
    PhaseTracker,
)
from common.simulation_runner import SimulationRunner  # noqa: E402

OUT_DIR = ROOT / "out"
PHASE_NAMES = ("stance_early", "stance_late", "swing_thrust", "swing_retract")


# ============================================================================
# V13.6 控制器封装
# ============================================================================


class V136Controller(Controller):
    """V13.6 控制器：4-phase FSM 显式状态机。"""

    def __init__(self, params: V136Params):
        self.params = params

    def compute_control(
        self,
        model: mujoco.MjModel,
        data: mujoco.MjData,
        t: float,
        context: dict[str, Any],
    ) -> tuple[np.ndarray, dict[str, Any]]:
        """计算 V13.6 控制力矩。"""
        support_foot = context["support_foot"]
        burst_start_t = context["burst_start_t"]
        E_current = _mechanical_energy(self.params.base, data)

        # V13.6 FSM 控制律
        tau = control_v136(self.params, data, t, support_foot, burst_start_t, E_current)
        l_hip, l_knee, r_hip, r_knee = tau[0], tau[1], tau[2], tau[3]
        mode_label = tau[4]
        left_phase = tau[5]
        right_phase = tau[6]
        eE_diag = tau[7]
        A_diag = tau[8]

        ctrl = np.array([l_hip, l_knee, r_hip, r_knee], dtype=np.float64)

        # 诊断信息
        diagnostics = {
            "E_current": E_current,
            "mode_label": mode_label,
            "left_phase": left_phase,
            "right_phase": right_phase,
            "e_E_swing": eE_diag,
            "A_swing": A_diag,
        }

        return ctrl, diagnostics

    def on_contact_event(self, foot: str, t: float, context: dict[str, Any]) -> None:
        """触地事件回调（V13.6 不需要特殊处理）。"""
        pass


# ============================================================================
# 数据记录器（兼容原版 make_row）
# ============================================================================


def make_v136_row(
    model: mujoco.MjModel, data: mujoco.MjData, t: float, context: dict[str, Any]
) -> dict[str, Any]:
    """构造 V13.6 数据行（兼容原版格式）。"""
    p = context["params"].base
    left_contact = context.get("left_contact", False)
    right_contact = context.get("right_contact", False)
    support_foot = context["support_foot"]
    mode_label = context.get("mode_label", "")

    # 获取控制力矩
    ctrl = (
        float(data.ctrl[0]),
        float(data.ctrl[1]),
        float(data.ctrl[2]),
        float(data.ctrl[3]),
    )
    input_power = context.get("input_power", 0.0)
    energy_stats = context["energy_stats"]

    # 复用 V10 的 make_row
    row = make_row(
        model,
        data,
        p,
        t,
        left_contact,
        right_contact,
        support_foot,
        mode_label,
        ctrl,
        input_power,
        energy_stats.positive_input_energy,
    )

    # 添加 V13.6 特有字段
    row.update(
        {
            "E_current": context.get("E_current", 0.0),
            "e_E_swing": context.get("e_E_swing", 0.0),
            "A_swing": context.get("A_swing", 0.0),
            "left_phase": context.get("left_phase", ""),
            "right_phase": context.get("right_phase", ""),
        }
    )

    return row


# ============================================================================
# 主仿真函数（使用新框架）
# ============================================================================


def run_simulation_v136_refactored(
    params: V136Params,
    save_prefix: str | None = None,
    sample_hz: float = 120.0,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """V13.6 重构版仿真（使用统一框架）。"""
    p = params.base

    # 构建模型
    write_model(p)
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    data = mujoco.MjData(model)
    initialize(model, data, p)

    # 初始化状态容器
    contact_state = ContactState(
        stable_contact_time=p.stable_contact_time,
        min_event_interval=p.min_event_interval,
    )
    energy_stats = EnergyStats()
    phase_tracker = PhaseTracker(phase_names=PHASE_NAMES)

    # 上下文字典
    context = {
        "params": params,
        "gait_period": p.gait_period,
        "energy_stats": energy_stats,
    }

    # 创建控制器
    controller = V136Controller(params)

    # 集成回调
    integrated_callback = IntegratedSimulationCallback(
        controller=controller,
        contact_detector=lambda m, d: contact_flags(m, d),
        contact_state=contact_state,
        energy_stats=energy_stats,
        phase_tracker=phase_tracker,
        context=context,
    )

    # 数据记录器
    recorder = DictRowRecorder(
        row_builder=make_v136_row, sample_hz=sample_hz, context=context
    )

    # 失败分类器
    def classify_wrapper(model, data, t, ctx):
        return classify_failure(model, data, p, ctx["start_x"], t)

    failure_classifier = FailureClassifier(
        classify_fn=classify_wrapper, context=context
    )

    # 运行仿真
    runner = SimulationRunner(
        model,
        data,
        callbacks=[integrated_callback, recorder],
        early_stop_conditions=[failure_classifier],
    )

    result = runner.run(duration=p.duration)

    # 提取结果
    rows = recorder.get_rows()
    if not rows:
        # 添加初始行（与原版一致）
        left_contact, right_contact = contact_flags(model, data)
        rows.append(
            make_row(
                model,
                data,
                p,
                0.0,
                left_contact,
                right_contact,
                "left",
                "init",
                (0, 0, 0, 0),
                0.0,
                0.0,
            )
        )

    simulated_time = result.simulated_time
    forward = context["max_x"] - context["start_x"]
    alternations = contact_state.alternations
    success = (
        simulated_time >= SUCCESS_TIME
        and alternations >= SUCCESS_TOUCHDOWNS
        and forward >= SUCCESS_FORWARD
        and result.success
    )

    # 计算分数（与原版同口径）
    score = alternations * 200.0 + simulated_time * 80.0 + forward * 60.0
    score -= 3.0 * energy_stats.positive_input_energy
    if success:
        score += 2000.0
    if not result.success:
        score -= 300.0

    # 汇总结果
    summary = {
        "params": {
            "base": params.base.__class__.__name__,
            "stance_early": {
                "k_E": params.stance_early.k_E,
                "k_PD": params.stance_early.k_PD,
                "tau_max": params.stance_early.tau_max,
            },
            "stance_late": {
                "k_E": params.stance_late.k_E,
                "k_PD": params.stance_late.k_PD,
                "tau_max": params.stance_late.tau_max,
            },
            "swing_thrust": {
                "k_E": params.swing_thrust.k_E,
                "k_PD": params.swing_thrust.k_PD,
                "tau_max": params.swing_thrust.tau_max,
                "E_target": params.swing_thrust.E_target,
            },
            "swing_retract": {
                "k_E": params.swing_retract.k_E,
                "k_PD": params.swing_retract.k_PD,
                "tau_max": params.swing_retract.tau_max,
            },
        },
        "phase_durations_s": phase_tracker.phase_durations,
        "phase_torque_integral_Nms": phase_tracker.phase_torque_int,
        "phase_timeline_head": phase_tracker.phase_timeline[:64],
        "phase_timeline_tail": phase_tracker.phase_timeline[-16:],
        "phase_transitions": len(phase_tracker.phase_timeline),
        "score": score,
        "success": success,
        "alternating_touchdowns": alternations,
        "contact_events": contact_state.contact_events[:64],
        "forward_distance": forward,
        "simulated_time": simulated_time,
        "failure": result.stop_reason if not result.success else "completed",
        "active_input_energy_j": energy_stats.positive_input_energy,
        "net_actuator_work_j": energy_stats.net_work,
        "energy_per_alternation_j": energy_stats.positive_input_energy
        / max(1, alternations),
        "quasi_passive": True,
        "pure_passive": False,
        "controller": "v13_6_event_driven_fsm_refactored",
        "framework_version": "simulation_framework_v1",
    }

    # 保存结果
    if save_prefix:
        OUT_DIR.mkdir(exist_ok=True)

        # 数据 CSV
        with (OUT_DIR / f"{save_prefix}_data.csv").open(
            "w", newline="", encoding="utf-8"
        ) as f:
            if rows:
                w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                w.writeheader()
                w.writerows(rows)

        # Phase 时序 CSV
        with (OUT_DIR / f"{save_prefix}_phases.csv").open(
            "w", newline="", encoding="utf-8"
        ) as f:
            w = csv.writer(f)
            w.writerow(["time", "left_phase", "right_phase"])
            for t_evt, lp, rp in phase_tracker.phase_timeline:
                w.writerow([t_evt, lp, rp])

        # 摘要 JSON
        (OUT_DIR / f"{save_prefix}_summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    return rows, summary


# ============================================================================
# 命令行入口
# ============================================================================


def main() -> None:
    parser = argparse.ArgumentParser(description="V13.6 Refactored Simulation")
    parser.add_argument(
        "--duration", type=float, default=12.0, help="Simulation duration (s)"
    )
    parser.add_argument(
        "--save-prefix",
        type=str,
        default="v136_refactored",
        help="Output file prefix",
    )
    args = parser.parse_args()

    # 构造参数（与原版 V13.6 同口径 - _baseline_v10）
    base = V10Params(
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
        duration=args.duration,
    )
    params = V136Params(base=base)

    _, summary = run_simulation_v136_refactored(
        params, save_prefix=args.save_prefix, sample_hz=120.0
    )

    # 输出摘要
    out = {
        "success": summary["success"],
        "alternations": summary["alternating_touchdowns"],
        "forward_distance": summary["forward_distance"],
        "simulated_time": summary["simulated_time"],
        "failure": summary["failure"],
        "phase_transitions": summary["phase_transitions"],
        "active_energy_j": summary["active_input_energy_j"],
        "controller": summary["controller"],
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
