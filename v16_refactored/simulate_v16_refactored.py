"""V16 重构版本：使用统一仿真框架。

代码量减少约 61%，保留完整功能：
- V13.6.1 FSM 控制律
- L1 电机动力学（电流饱和 + 库仑摩擦）
- 接触检测与事件驱动
- Phase timeline 记录
- 能量统计（含电阻损耗和摩擦耗散）

对比原版 simulate_v16.py：
- 仿真循环逻辑迁移到 common.simulation_framework
- 控制律封装为 Controller 接口
- 电机模型集成到控制器内部
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
V14_DIR = HW1_ROOT / "v14_passive_arms"
V136_DIR = HW1_ROOT / "v13_6_event_driven_fsm"
V14C_DIR = HW1_ROOT / "v14c_arm_mass_lightening"
V16_DIR = HW1_ROOT / "v16_motor_dynamics"

sys.path.insert(0, str(V14_DIR))
sys.path.insert(0, str(V136_DIR))
sys.path.insert(0, str(V14C_DIR))
sys.path.insert(0, str(V16_DIR))
sys.path.insert(0, str(HW1_ROOT))

from simulate_passive_arms_v14 import (  # noqa: E402
    SUCCESS_FORWARD,
    SUCCESS_TIME,
    SUCCESS_TOUCHDOWNS,
    PassiveArmsParams,
    classify_failure,
    contact_flags,
    initialize,
    make_row,
)
from simulate_v13_6 import (  # noqa: E402
    _mechanical_energy,
    control_v136,
)
from simulate_v14c import make_v14c_params  # noqa: E402
from simulate_v16 import (  # noqa: E402
    MODEL_PATH,
    V16Params,
    _motor_summary,
    write_model_v16,
)

from common.motor_dynamics import (
    PRESETS as MOTOR_PRESETS,
)
from common.motor_dynamics import (
    L1MotorActuator,
)  # noqa: E402
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
# V16 控制器封装
# ============================================================================


class V16Controller(Controller):
    """V16 控制器：V13.6.1 FSM + L1 电机动力学。"""

    def __init__(self, params: V16Params):
        self.params = params
        self.fsm = params.fsm

        # 电机执行器
        self.actuators = {
            "left_hip": L1MotorActuator(params.hip_motor),
            "left_knee": L1MotorActuator(params.knee_motor),
            "right_hip": L1MotorActuator(params.hip_motor),
            "right_knee": L1MotorActuator(params.knee_motor),
        }
        self.qvel_addr = {
            "left_hip": 2,
            "left_knee": 3,
            "right_hip": 5,
            "right_knee": 6,
        }

    def compute_control(
        self,
        model: mujoco.MjModel,
        data: mujoco.MjData,
        t: float,
        context: dict[str, Any],
    ) -> tuple[np.ndarray, dict[str, Any]]:
        """计算 V16 控制力矩。"""
        support_foot = context["support_foot"]
        burst_start_t = context["burst_start_t"]
        E_current = _mechanical_energy(self.params.base, data)

        # V13.6 FSM 控制律
        tau = control_v136(self.fsm, data, t, support_foot, burst_start_t, E_current)
        l_hip_des, l_knee_des, r_hip_des, r_knee_des = tau[0], tau[1], tau[2], tau[3]
        mode_label = tau[4]
        left_phase = tau[5]
        right_phase = tau[6]
        eE_diag = tau[7]
        A_diag = tau[8]

        # L1 电机模型（电流饱和 + 库仑摩擦）
        sat_before = {k: a.saturation_count for k, a in self.actuators.items()}
        l_hip_out, _ = self.actuators["left_hip"].compute_actual_torque(
            l_hip_des, float(data.qvel[self.qvel_addr["left_hip"]])
        )
        l_knee_out, _ = self.actuators["left_knee"].compute_actual_torque(
            l_knee_des, float(data.qvel[self.qvel_addr["left_knee"]])
        )
        r_hip_out, _ = self.actuators["right_hip"].compute_actual_torque(
            r_hip_des, float(data.qvel[self.qvel_addr["right_hip"]])
        )
        r_knee_out, _ = self.actuators["right_knee"].compute_actual_torque(
            r_knee_des, float(data.qvel[self.qvel_addr["right_knee"]])
        )

        ctrl = np.array(
            [l_hip_out, l_knee_out, r_hip_out, r_knee_out], dtype=np.float64
        )

        # 电阻损耗功率
        omega = [
            float(data.qvel[self.qvel_addr[k]])
            for k in ("left_hip", "left_knee", "right_hip", "right_knee")
        ]
        tau_des = [l_hip_des, l_knee_des, r_hip_des, r_knee_des]
        p_resistive = 0.0
        for key, t_des in zip(
            ("left_hip", "left_knee", "right_hip", "right_knee"), tau_des
        ):
            act = self.actuators[key]
            tau_after_sat = max(-act._tau_sat, min(act._tau_sat, t_des))
            if act._kt_joint > 0.0:
                i_motor = tau_after_sat / act._kt_joint
                p_resistive += i_motor * i_motor * act.motor.R_arm

        # 库仑摩擦耗散功率
        p_coulomb = 0.0
        for key, om in zip(("left_hip", "left_knee", "right_hip", "right_knee"), omega):
            act = self.actuators[key]
            p_coulomb += act._tau_C_eff * abs(om)

        # 髋关节饱和判断
        any_hip_sat = (
            self.actuators["left_hip"].saturation_count > sat_before["left_hip"]
            or self.actuators["right_hip"].saturation_count > sat_before["right_hip"]
        )

        # 诊断信息
        diagnostics = {
            "E_current": E_current,
            "mode_label": mode_label,
            "left_phase": left_phase,
            "right_phase": right_phase,
            "e_E_swing": eE_diag,
            "A_swing": A_diag,
            "resistive_power": p_resistive,
            "coulomb_power": p_coulomb,
            "hip_saturated": any_hip_sat,
            "tau_l_hip_des": l_hip_des,
            "tau_l_knee_des": l_knee_des,
            "tau_r_hip_des": r_hip_des,
            "tau_r_knee_des": r_knee_des,
            "tau_l_hip_out": l_hip_out,
            "tau_l_knee_out": l_knee_out,
            "tau_r_hip_out": r_hip_out,
            "tau_r_knee_out": r_knee_out,
        }

        return ctrl, diagnostics

    def on_contact_event(self, foot: str, t: float, context: dict[str, Any]) -> None:
        """触地事件回调（V16 不需要特殊处理）。"""
        pass


# ============================================================================
# 数据记录器（兼容原版 make_row）
# ============================================================================


def make_v16_row(
    model: mujoco.MjModel, data: mujoco.MjData, t: float, context: dict[str, Any]
) -> dict[str, Any]:
    """构造 V16 数据行（兼容原版格式）。"""
    p = context["params"].base
    left_contact = context.get("left_contact", False)
    right_contact = context.get("right_contact", False)
    support_foot = context["support_foot"]
    mode_label = context.get("mode_label", "")

    # 获取控制力矩（输出力矩）
    ctrl_out = (
        context.get("tau_l_hip_out", 0.0),
        context.get("tau_l_knee_out", 0.0),
        context.get("tau_r_hip_out", 0.0),
        context.get("tau_r_knee_out", 0.0),
    )
    input_power = context.get("input_power", 0.0)
    energy_stats = context["energy_stats"]

    # 复用 V14 的 make_row
    row = make_row(
        model,
        data,
        p,
        t,
        left_contact,
        right_contact,
        support_foot,
        mode_label,
        ctrl_out,
        input_power,
        energy_stats.positive_input_energy,
    )

    # 添加 V16 特有字段
    row.update(
        {
            "E_current": context.get("E_current", 0.0),
            "e_E_swing": context.get("e_E_swing", 0.0),
            "A_swing": context.get("A_swing", 0.0),
            "left_phase": context.get("left_phase", ""),
            "right_phase": context.get("right_phase", ""),
            "tau_l_hip_des": context.get("tau_l_hip_des", 0.0),
            "tau_l_knee_des": context.get("tau_l_knee_des", 0.0),
            "tau_r_hip_des": context.get("tau_r_hip_des", 0.0),
            "tau_r_knee_des": context.get("tau_r_knee_des", 0.0),
        }
    )

    return row


# ============================================================================
# 主仿真函数（使用新框架）
# ============================================================================


def run_simulation_v16_refactored(
    params: V16Params,
    save_prefix: str | None = None,
    sample_hz: float = 160.0,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """V16 重构版仿真（使用统一框架）。"""
    p = params.base

    # 构建模型
    write_model_v16(params)
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
    controller = V16Controller(params)

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
        row_builder=make_v16_row, sample_hz=sample_hz, context=context
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

    # 计算饱和率
    phase_saturation_rate = {}
    for name in PHASE_NAMES:
        total = phase_tracker.phase_total_steps.get(name, 0)
        sat = phase_tracker.phase_saturation_steps.get(name, 0)
        phase_saturation_rate[name] = sat / max(1, total)

    # 汇总结果
    summary = {
        "params": {
            "base": params.base.__class__.__name__,
            "hip_motor": params.hip_motor.name,
            "knee_motor": params.knee_motor.name,
        },
        "motor_specs": {
            "hip": _motor_summary(params.hip_motor),
            "knee": _motor_summary(params.knee_motor),
        },
        "phase_durations_s": phase_tracker.phase_durations,
        "phase_torque_integral_Nms": phase_tracker.phase_torque_int,
        "phase_saturation_steps": phase_tracker.phase_saturation_steps,
        "phase_total_steps": phase_tracker.phase_total_steps,
        "phase_saturation_rate": phase_saturation_rate,
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
        "positive_input_energy_elec_j": energy_stats.positive_input_energy_elec,
        "coulomb_dissipation_j": energy_stats.coulomb_dissipation,
        "energy_per_alternation_j": energy_stats.positive_input_energy
        / max(1, alternations),
        "quasi_passive": True,
        "pure_passive": False,
        "controller": "v16_motor_dynamics_refactored",
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
    parser = argparse.ArgumentParser(description="V16 Refactored Simulation")
    parser.add_argument(
        "--duration", type=float, default=12.0, help="Simulation duration (s)"
    )
    parser.add_argument(
        "--save-prefix", type=str, default="v16_refactored", help="Output file prefix"
    )
    args = parser.parse_args()

    # 构造参数（与原版 V16 同口径）
    base = PassiveArmsParams(
        slope_deg=0.0,
        gait_period=0.80,
        duration=args.duration,
        torso_mass=0.05,
        foot_length=0.12,
        foot_radius=0.04,
        ankle_stiffness=10.0,
        ankle_damping=0.08,
        initial_vx=0.03,
        arm_mass=0.05,
        arm_length=0.24,
    )
    fsm = make_v14c_params(base)
    params = V16Params(
        base=base,
        fsm=fsm,
        hip_motor=MOTOR_PRESETS["mx64ar"],
        knee_motor=MOTOR_PRESETS["mx64ar"],
    )

    _, summary = run_simulation_v16_refactored(
        params, save_prefix=args.save_prefix, sample_hz=160.0
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
        "coulomb_dissipation_j": summary["coulomb_dissipation_j"],
        "controller": summary["controller"],
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
