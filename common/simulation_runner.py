"""通用仿真循环框架：支持回调、数据记录、早停条件。

设计原则：
- 提供可扩展的仿真循环基础结构
- 支持用户自定义回调函数（控制律、数据记录、事件检测）
- 统一的早停条件判断
- 向后兼容现有版本的仿真模式

接口：
- SimulationRunner(model, data, callbacks, early_stop)
- runner.run(duration) -> SimulationResult
- Callback 基类：on_step(model, data, t, step) -> None
- EarlyStopCondition 基类：check(model, data, t) -> tuple[bool, str]
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable

import mujoco
import numpy as np


@dataclass
class SimulationResult:
    """仿真结果容器。"""

    success: bool
    simulated_time: float
    total_steps: int
    stop_reason: str  # "completed", "early_stop", "failure"
    custom_data: dict[str, Any] = field(default_factory=dict)


class Callback(ABC):
    """仿真回调基类。

    子类需要实现 on_step 方法，在每个仿真步执行自定义逻辑。
    """

    @abstractmethod
    def on_step(
        self, model: mujoco.MjModel, data: mujoco.MjData, t: float, step: int
    ) -> None:
        """每个仿真步调用。

        Args:
            model: MuJoCo 模型
            data: MuJoCo 数据
            t: 当前仿真时间
            step: 当前步数（从 0 开始）
        """
        pass

    def on_start(self, model: mujoco.MjModel, data: mujoco.MjData) -> None:
        """仿真开始前调用（可选）。"""
        pass

    def on_finish(
        self, model: mujoco.MjModel, data: mujoco.MjData, result: SimulationResult
    ) -> None:
        """仿真结束后调用（可选）。"""
        pass


class EarlyStopCondition(ABC):
    """早停条件基类。"""

    @abstractmethod
    def check(
        self, model: mujoco.MjModel, data: mujoco.MjData, t: float
    ) -> tuple[bool, str]:
        """检查是否应该提前终止仿真。

        Args:
            model: MuJoCo 模型
            data: MuJoCo 数据
            t: 当前仿真时间

        Returns:
            (是否停止, 停止原因) 元组
        """
        pass


class SimulationRunner:
    """通用仿真循环执行器。

    Example:
        >>> from common.model_loader import load_model_from_file
        >>> model = load_model_from_file("model.xml")
        >>> data = mujoco.MjData(model)
        >>>
        >>> # 添加自定义回调
        >>> class MyController(Callback):
        ...     def on_step(self, model, data, t, step):
        ...         data.ctrl[0] = np.sin(t)  # 简单的正弦控制
        >>>
        >>> runner = SimulationRunner(model, data, callbacks=[MyController()])
        >>> result = runner.run(duration=10.0)
        >>> print(result.simulated_time, result.success)
    """

    def __init__(
        self,
        model: mujoco.MjModel,
        data: mujoco.MjData,
        *,
        callbacks: list[Callback] | None = None,
        early_stop_conditions: list[EarlyStopCondition] | None = None,
    ):
        """初始化仿真执行器。

        Args:
            model: MuJoCo 模型
            data: MuJoCo 数据（应已初始化 qpos/qvel）
            callbacks: 回调列表（按注册顺序执行）
            early_stop_conditions: 早停条件列表（任一满足即停止）
        """
        self.model = model
        self.data = data
        self.callbacks = callbacks or []
        self.early_stop_conditions = early_stop_conditions or []

    def run(
        self, duration: float, *, sample_hz: float | None = None
    ) -> SimulationResult:
        """运行仿真。

        Args:
            duration: 仿真持续时间（秒）
            sample_hz: 如果指定，仅在此频率下调用回调（降低开销）

        Returns:
            SimulationResult 包含仿真结果和停止原因
        """
        timestep = float(self.model.opt.timestep)
        total_steps = int(duration / timestep)

        # 计算回调采样步长
        if sample_hz is not None:
            callback_stride = max(1, int(round(1.0 / (timestep * sample_hz))))
        else:
            callback_stride = 1

        # 调用 on_start 回调
        for cb in self.callbacks:
            cb.on_start(self.model, self.data)

        stop_reason = "completed"
        actual_steps = 0

        for step in range(total_steps):
            t = step * timestep

            # 执行回调（控制律、数据记录等）
            if step % callback_stride == 0:
                for cb in self.callbacks:
                    cb.on_step(self.model, self.data, t, step)

            # 仿真步进
            mujoco.mj_step(self.model, self.data)
            actual_steps = step + 1

            # 检查早停条件
            for condition in self.early_stop_conditions:
                should_stop, reason = condition.check(self.model, self.data, t)
                if should_stop:
                    stop_reason = reason
                    break

            if stop_reason != "completed":
                break

        # 最终时间
        simulated_time = actual_steps * timestep
        success = stop_reason == "completed"

        result = SimulationResult(
            success=success,
            simulated_time=simulated_time,
            total_steps=actual_steps,
            stop_reason=stop_reason,
        )

        # 调用 on_finish 回调
        for cb in self.callbacks:
            cb.on_finish(self.model, self.data, result)

        return result

    def add_callback(self, callback: Callback) -> None:
        """动态添加回调。"""
        self.callbacks.append(callback)

    def add_early_stop(self, condition: EarlyStopCondition) -> None:
        """动态添加早停条件。"""
        self.early_stop_conditions.append(condition)


# ============================================================================
# 常用回调实现
# ============================================================================


class DataRecorder(Callback):
    """时间序列数据记录器。

    Example:
        >>> recorder = DataRecorder(
        ...     sample_hz=200.0,
        ...     extractors={
        ...         "hip_x": lambda m, d: float(d.qpos[0]),
        ...         "hip_z": lambda m, d: float(d.qpos[1]),
        ...     }
        ... )
        >>> runner = SimulationRunner(model, data, callbacks=[recorder])
        >>> result = runner.run(10.0)
        >>> data_dict = recorder.get_data()  # {"time": [...], "hip_x": [...], ...}
    """

    def __init__(
        self,
        *,
        sample_hz: float = 200.0,
        extractors: (
            dict[str, Callable[[mujoco.MjModel, mujoco.MjData], float]] | None
        ) = None,
    ):
        """初始化数据记录器。

        Args:
            sample_hz: 采样频率
            extractors: 列名 -> 提取函数字典
        """
        self.sample_hz = sample_hz
        self.extractors = extractors or {}
        self._data: dict[str, list[float]] = {
            k: [] for k in ["time", *self.extractors.keys()]
        }
        self._sample_stride = 1
        self._step_counter = 0

    def on_start(self, model: mujoco.MjModel, data: mujoco.MjData) -> None:
        timestep = float(model.opt.timestep)
        self._sample_stride = max(1, int(round(1.0 / (timestep * self.sample_hz))))
        self._step_counter = 0
        # 清空历史数据
        self._data = {k: [] for k in self._data}

    def on_step(
        self, model: mujoco.MjModel, data: mujoco.MjData, t: float, step: int
    ) -> None:
        if self._step_counter % self._sample_stride == 0:
            self._data["time"].append(t)
            for key, extractor in self.extractors.items():
                self._data[key].append(extractor(model, data))
        self._step_counter += 1

    def get_data(self) -> dict[str, list[float]]:
        """返回记录的数据字典。"""
        return self._data.copy()

    def get_numpy_data(self) -> dict[str, np.ndarray]:
        """返回 numpy 数组格式的数据。"""
        return {k: np.array(v) for k, v in self._data.items()}


class ControllerCallback(Callback):
    """通用控制律回调包装器。

    Example:
        >>> def my_controller(model, data, t):
        ...     data.ctrl[0] = 10.0 * (target_angle - data.qpos[0])
        >>>
        >>> runner = SimulationRunner(
        ...     model, data,
        ...     callbacks=[ControllerCallback(my_controller)]
        ... )
    """

    def __init__(
        self, controller_fn: Callable[[mujoco.MjModel, mujoco.MjData, float], None]
    ):
        """初始化控制律回调。

        Args:
            controller_fn: 控制函数，签名为 (model, data, t) -> None
        """
        self.controller_fn = controller_fn

    def on_step(
        self, model: mujoco.MjModel, data: mujoco.MjData, t: float, step: int
    ) -> None:
        self.controller_fn(model, data, t)


# ============================================================================
# 常用早停条件实现
# ============================================================================


class NaNDetector(EarlyStopCondition):
    """检测 NaN 或数值不稳定。"""

    def check(
        self, model: mujoco.MjModel, data: mujoco.MjData, t: float
    ) -> tuple[bool, str]:
        if not np.all(np.isfinite(data.qpos)) or not np.all(np.isfinite(data.qvel)):
            return True, "nan_or_unstable"
        return False, ""


class HeightThreshold(EarlyStopCondition):
    """检测高度越界（摔倒判据）。"""

    def __init__(
        self, body_name: str, min_height: float = -0.1, max_height: float = 5.0
    ):
        self.body_name = body_name
        self.min_height = min_height
        self.max_height = max_height
        self._body_id = -1

    def check(
        self, model: mujoco.MjModel, data: mujoco.MjData, t: float
    ) -> tuple[bool, str]:
        if self._body_id < 0:
            self._body_id = mujoco.mj_name2id(
                model, mujoco.mjtObj.mjOBJ_BODY, self.body_name
            )
            if self._body_id < 0:
                return False, ""  # body 不存在，跳过检查

        z = float(data.xpos[self._body_id, 2])
        if z < self.min_height:
            return True, "hip_too_low"
        if z > self.max_height:
            return True, "fly_away"
        return False, ""


class PenetrationDetector(EarlyStopCondition):
    """检测穿透（接触距离异常）。"""

    def __init__(self, threshold_dist: float = -0.01):
        """初始化穿透检测器。

        Args:
            threshold_dist: 接触距离阈值（负值表示穿透），单位米
        """
        self.threshold = threshold_dist

    def check(
        self, model: mujoco.MjModel, data: mujoco.MjData, t: float
    ) -> tuple[bool, str]:
        for i in range(data.ncon):
            # 检查接触距离（dist < 0 表示穿透）
            if data.contact[i].dist < self.threshold:
                return True, "penetration"
        return False, ""


__all__ = [
    "SimulationResult",
    "Callback",
    "EarlyStopCondition",
    "SimulationRunner",
    "DataRecorder",
    "ControllerCallback",
    "NaNDetector",
    "HeightThreshold",
    "PenetrationDetector",
]
