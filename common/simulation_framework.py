"""增强仿真框架：提取 V10/V13.6/V14/V16/V17 的共享模式。

在 simulation_runner.py 的基础上，增加：
- 接触检测与事件驱动切换（stable_contact_time + min_event_interval）
- 能量/功率统计（正功、净功、库仑摩擦耗散）
- 失败分类（classify_failure）
- Phase timeline 记录
- 控制器抽象接口（PD / FSM / 电机模型）

设计原则：
- 向后兼容现有版本
- 减少重复代码 50-70%
- 保持各版本可独立运行
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable

import mujoco
import numpy as np

from .simulation_runner import (
    Callback,
    EarlyStopCondition,
)

# ============================================================================
# 接触检测与事件驱动状态机
# ============================================================================


@dataclass
class ContactState:
    """接触状态追踪器（用于抗抖和事件检测）。"""

    stable_contact_time: float = 0.035  # 稳定接触判定时长
    min_event_interval: float = 0.22  # 最小事件间隔（防抖）

    # 内部状态
    candidate_start_t: dict[str, float | None] = field(
        default_factory=lambda: {"left": None, "right": None}
    )
    contact_reported: dict[str, bool] = field(
        default_factory=lambda: {"left": False, "right": False}
    )
    last_event_t: float = -1.0
    accepted_contact: str = ""
    support_foot: str = "left"
    alternations: int = 0
    contact_events: list[dict[str, Any]] = field(default_factory=list)


def update_contact_state(
    state: ContactState,
    t: float,
    left_contact: bool,
    right_contact: bool,
    extra_data: dict[str, Any] | None = None,
) -> list[str]:
    """更新接触状态，返回新稳定触地的脚列表。

    Args:
        state: ContactState 对象（会原地修改）
        t: 当前时间
        left_contact: 左脚是否接触
        right_contact: 右脚是否接触
        extra_data: 额外数据（记录到 contact_events）

    Returns:
        新稳定触地的脚列表（可能为空）
    """
    contacts = {"left": left_contact, "right": right_contact}
    stable_feet: list[str] = []

    # 检测稳定接触
    for foot, has_contact in contacts.items():
        if has_contact:
            if state.candidate_start_t[foot] is None:
                state.candidate_start_t[foot] = t
                state.contact_reported[foot] = False
            if t - float(state.candidate_start_t[foot]) >= state.stable_contact_time:
                stable_feet.append(foot)
        else:
            state.candidate_start_t[foot] = None
            state.contact_reported[foot] = False

    # 处理状态切换事件
    new_events: list[str] = []
    for foot in stable_feet:
        if (
            not state.contact_reported[foot]
            and foot != state.accepted_contact
            and t - state.last_event_t > state.min_event_interval
        ):
            # 记录交替触地
            if state.accepted_contact in {"left", "right"}:
                state.alternations += 1

            state.accepted_contact = foot
            state.support_foot = foot
            state.last_event_t = t
            state.contact_reported[foot] = True

            event = {"time": t, "foot": foot}
            if extra_data:
                event.update(extra_data)
            state.contact_events.append(event)
            new_events.append(foot)

    return new_events


# ============================================================================
# 能量统计
# ============================================================================


@dataclass
class EnergyStats:
    """能量/功率统计容器。"""

    positive_input_energy: float = 0.0  # 正功累积（J）
    net_work: float = 0.0  # 净功（J）
    positive_input_energy_elec: float = 0.0  # 电功率累积（含电阻损耗）
    coulomb_dissipation: float = 0.0  # 库仑摩擦耗散（J）

    def update(
        self,
        input_power: float,
        timestep: float,
        *,
        resistive_power: float = 0.0,
        coulomb_power: float = 0.0,
    ) -> None:
        """更新能量统计。

        Args:
            input_power: 机械功率（W）
            timestep: 时间步长（s）
            resistive_power: 电阻损耗功率（W）
            coulomb_power: 库仑摩擦功率（W）
        """
        self.positive_input_energy += max(0.0, input_power) * timestep
        self.net_work += input_power * timestep
        if resistive_power > 0.0:
            self.positive_input_energy_elec += (
                max(0.0, input_power) + resistive_power
            ) * timestep
        if coulomb_power > 0.0:
            self.coulomb_dissipation += coulomb_power * timestep


# ============================================================================
# 控制器抽象接口
# ============================================================================


class Controller(ABC):
    """控制器抽象基类。

    各版本控制律实现此接口，框架负责调用和能量统计。
    """

    @abstractmethod
    def compute_control(
        self,
        model: mujoco.MjModel,
        data: mujoco.MjData,
        t: float,
        context: dict[str, Any],
    ) -> tuple[np.ndarray, dict[str, Any]]:
        """计算控制力矩。

        Args:
            model: MuJoCo 模型
            data: MuJoCo 数据
            t: 当前时间
            context: 上下文信息（support_foot、burst_start_t 等）

        Returns:
            (ctrl, diagnostics) 元组
            - ctrl: 控制力矩数组
            - diagnostics: 诊断信息字典（mode_label、phase 等）
        """
        pass

    def on_contact_event(self, foot: str, t: float, context: dict[str, Any]) -> None:
        """触地事件回调（可选）。

        Args:
            foot: 触地的脚（"left" 或 "right"）
            t: 触地时间
            context: 上下文信息
        """
        pass


# ============================================================================
# Phase 时序记录
# ============================================================================


@dataclass
class PhaseTracker:
    """Phase 时序追踪器（用于 FSM 控制律）。"""

    phase_names: tuple[str, ...] = (
        "stance_early",
        "stance_late",
        "swing_thrust",
        "swing_retract",
    )

    # 时序记录
    phase_timeline: list[tuple[float, str, str]] = field(default_factory=list)
    last_left_phase: str = ""
    last_right_phase: str = ""

    # 统计
    phase_durations: dict[str, float] = field(default_factory=dict)
    phase_torque_int: dict[str, float] = field(default_factory=dict)
    phase_saturation_steps: dict[str, int] = field(default_factory=dict)
    phase_total_steps: dict[str, int] = field(default_factory=dict)

    def __post_init__(self):
        if not self.phase_durations:
            self.phase_durations = dict.fromkeys(self.phase_names, 0.0)
            self.phase_torque_int = dict.fromkeys(self.phase_names, 0.0)
            self.phase_saturation_steps = dict.fromkeys(self.phase_names, 0)
            self.phase_total_steps = dict.fromkeys(self.phase_names, 0)

    def update(
        self,
        t: float,
        left_phase: str,
        right_phase: str,
        timestep: float,
        *,
        left_hip_tau: float = 0.0,
        right_hip_tau: float = 0.0,
        hip_saturated: bool = False,
    ) -> None:
        """更新 phase 统计。

        Args:
            t: 当前时间
            left_phase: 左腿 phase
            right_phase: 右腿 phase
            timestep: 时间步长
            left_hip_tau: 左髋力矩（用于积分）
            right_hip_tau: 右髋力矩（用于积分）
            hip_saturated: 髋关节是否饱和
        """
        # 记录 phase 切换
        if left_phase != self.last_left_phase or right_phase != self.last_right_phase:
            self.phase_timeline.append((t, left_phase, right_phase))
            self.last_left_phase = left_phase
            self.last_right_phase = right_phase

        # 更新统计（左右合计）
        self.phase_durations[left_phase] += timestep
        self.phase_durations[right_phase] += timestep
        self.phase_torque_int[left_phase] += abs(left_hip_tau) * timestep
        self.phase_torque_int[right_phase] += abs(right_hip_tau) * timestep
        self.phase_total_steps[left_phase] += 1
        self.phase_total_steps[right_phase] += 1

        if hip_saturated:
            self.phase_saturation_steps[left_phase] += 1
            self.phase_saturation_steps[right_phase] += 1


# ============================================================================
# 增强的数据记录器（支持字典行）
# ============================================================================


class DictRowRecorder(Callback):
    """字典行记录器（兼容 V10-V17 的 make_row 模式）。

    Example:
        >>> def make_custom_row(model, data, t, context):
        ...     return {"time": t, "hip_x": float(data.qpos[0]), ...}
        >>>
        >>> recorder = DictRowRecorder(row_builder=make_custom_row, sample_hz=160.0)
        >>> runner = SimulationRunner(model, data, callbacks=[recorder])
        >>> result = runner.run(10.0)
        >>> rows = recorder.get_rows()
    """

    def __init__(
        self,
        *,
        row_builder: Callable[
            [mujoco.MjModel, mujoco.MjData, float, dict[str, Any]], dict[str, Any]
        ],
        sample_hz: float = 160.0,
        context: dict[str, Any] | None = None,
    ):
        """初始化字典行记录器。

        Args:
            row_builder: 行构造函数，签名为 (model, data, t, context) -> dict
            sample_hz: 采样频率
            context: 上下文字典（传递给 row_builder）
        """
        self.row_builder = row_builder
        self.sample_hz = sample_hz
        self.context = context or {}
        self._rows: list[dict[str, Any]] = []
        self._sample_stride = 1
        self._step_counter = 0

    def on_start(self, model: mujoco.MjModel, data: mujoco.MjData) -> None:
        timestep = float(model.opt.timestep)
        self._sample_stride = max(1, int(round(1.0 / (timestep * self.sample_hz))))
        self._step_counter = 0
        self._rows = []

    def on_step(
        self, model: mujoco.MjModel, data: mujoco.MjData, t: float, step: int
    ) -> None:
        if self._step_counter % self._sample_stride == 0:
            row = self.row_builder(model, data, t, self.context)
            self._rows.append(row)
        self._step_counter += 1

    def get_rows(self) -> list[dict[str, Any]]:
        """返回记录的行列表。"""
        return self._rows


# ============================================================================
# 集成回调：控制 + 接触检测 + 能量统计
# ============================================================================


class IntegratedSimulationCallback(Callback):
    """集成控制、接触检测、能量统计的一体化回调。

    适用于事件驱动的 FSM 控制律（V13.6+）。
    """

    def __init__(
        self,
        controller: Controller,
        contact_detector: Callable[[mujoco.MjModel, mujoco.MjData], tuple[bool, bool]],
        *,
        contact_state: ContactState | None = None,
        energy_stats: EnergyStats | None = None,
        phase_tracker: PhaseTracker | None = None,
        context: dict[str, Any] | None = None,
    ):
        """初始化集成回调。

        Args:
            controller: 控制器实例
            contact_detector: 接触检测函数，返回 (left_contact, right_contact)
            contact_state: 接触状态追踪器
            energy_stats: 能量统计容器
            phase_tracker: Phase 追踪器（可选，用于 FSM）
            context: 共享上下文字典
        """
        self.controller = controller
        self.contact_detector = contact_detector
        self.contact_state = contact_state or ContactState()
        self.energy_stats = energy_stats or EnergyStats()
        self.phase_tracker = phase_tracker
        self.context = context or {}

        # 初始化 context
        self.context.setdefault("support_foot", "left")
        self.context.setdefault("burst_start_t", -1.0)
        self.context.setdefault("start_x", 0.0)
        self.context.setdefault("max_x", 0.0)

    def on_start(self, model: mujoco.MjModel, data: mujoco.MjData) -> None:
        self.context["start_x"] = float(data.qpos[0])
        self.context["max_x"] = float(data.qpos[0])
        # 重置 burst_start_t（用于 gait_period 相位计算）
        if "gait_period" in self.context:
            self.context["burst_start_t"] = -self.context["gait_period"]

    def on_step(
        self, model: mujoco.MjModel, data: mujoco.MjData, t: float, step: int
    ) -> None:
        # 1. 计算控制力矩
        ctrl, diagnostics = self.controller.compute_control(
            model, data, t, self.context
        )
        data.ctrl[:] = ctrl

        # 2. 能量统计
        timestep = float(model.opt.timestep)
        # 关节速度：left_hip(2), left_knee(3), right_hip(5), right_knee(6)
        # 注意：跳过 left_ankle(4) 和 right_ankle(7)
        omega = np.array([data.qvel[2], data.qvel[3], data.qvel[5], data.qvel[6]])
        input_power = float(np.dot(ctrl[:4], omega))  # 机械功率

        # 从 diagnostics 获取额外功率信息（如果有）
        resistive_power = diagnostics.get("resistive_power", 0.0)
        coulomb_power = diagnostics.get("coulomb_power", 0.0)
        self.energy_stats.update(
            input_power,
            timestep,
            resistive_power=resistive_power,
            coulomb_power=coulomb_power,
        )

        # 3. 接触检测与事件驱动
        left_contact, right_contact = self.contact_detector(model, data)
        extra_data = {"E": diagnostics.get("E_current", 0.0)}
        new_events = update_contact_state(
            self.contact_state, t, left_contact, right_contact, extra_data
        )

        # 触发控制器的事件回调
        for foot in new_events:
            self.controller.on_contact_event(foot, t, self.context)
            # 更新上下文
            self.context["support_foot"] = self.contact_state.support_foot
            self.context["burst_start_t"] = t

        # 4. Phase tracking（如果启用）
        if self.phase_tracker is not None:
            left_phase = diagnostics.get("left_phase", "")
            right_phase = diagnostics.get("right_phase", "")
            if left_phase and right_phase:
                self.phase_tracker.update(
                    t,
                    left_phase,
                    right_phase,
                    timestep,
                    left_hip_tau=float(ctrl[0]),
                    right_hip_tau=float(ctrl[2]),
                    hip_saturated=diagnostics.get("hip_saturated", False),
                )

        # 5. 更新 max_x
        self.context["max_x"] = max(self.context["max_x"], float(data.qpos[0]))

        # 6. 将诊断信息注入 context（供 DictRowRecorder 使用）
        self.context.update(diagnostics)
        self.context["left_contact"] = left_contact
        self.context["right_contact"] = right_contact
        self.context["input_power"] = input_power


# ============================================================================
# 通用失败分类早停条件
# ============================================================================


class FailureClassifier(EarlyStopCondition):
    """通用失败分类器（复用 V10-V17 的 classify_failure 逻辑）。"""

    def __init__(
        self,
        classify_fn: Callable[
            [mujoco.MjModel, mujoco.MjData, float, dict[str, Any]], str
        ],
        context: dict[str, Any],
    ):
        """初始化失败分类器。

        Args:
            classify_fn: 失败分类函数，签名为 (model, data, t, context) -> failure_reason
            context: 上下文字典（包含 start_x 等）
        """
        self.classify_fn = classify_fn
        self.context = context

    def check(
        self, model: mujoco.MjModel, data: mujoco.MjData, t: float
    ) -> tuple[bool, str]:
        failure = self.classify_fn(model, data, t, self.context)
        if failure:
            return True, failure
        return False, ""


__all__ = [
    "ContactState",
    "update_contact_state",
    "EnergyStats",
    "Controller",
    "PhaseTracker",
    "DictRowRecorder",
    "IntegratedSimulationCallback",
    "FailureClassifier",
]
