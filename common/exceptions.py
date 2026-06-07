"""HW-1 项目统一异常类定义。

设计原则：
- 明确的异常层次结构，便于捕获和处理
- 包含上下文信息（时间、参数、状态）
- 支持异常链（exception chaining）
- 便于日志记录和调试

异常层次：
- HW1Error (基类)
  - ModelError (模型相关)
    - ModelLoadError
    - ModelValidationError
  - SimulationError (仿真相关)
    - SimulationFailureError
    - SimulationTimeoutError
    - SimulationNaNError
  - DataError (数据处理相关)
    - DataValidationError
    - DataIOError
  - ControlError (控制相关)
    - ControlLimitError
    - ControlStabilityError
"""

from __future__ import annotations

from typing import Any


class HW1Error(Exception):
    """HW-1 项目所有自定义异常的基类。

    所有自定义异常都应该继承此类，便于统一处理。
    """

    def __init__(
        self,
        message: str,
        *,
        context: dict[str, Any] | None = None,
        original_exception: Exception | None = None,
    ):
        """初始化异常。

        Args:
            message: 错误描述信息
            context: 上下文信息（如参数、状态、时间等）
            original_exception: 原始异常（用于异常链）
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.original_exception = original_exception

    def __str__(self) -> str:
        """格式化异常信息。"""
        parts = [self.message]
        if self.context:
            ctx_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            parts.append(f"[context: {ctx_str}]")
        if self.original_exception:
            parts.append(f"[caused by: {type(self.original_exception).__name__}]")
        return " ".join(parts)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典，便于日志记录和序列化。"""
        return {
            "type": self.__class__.__name__,
            "message": self.message,
            "context": self.context,
            "original_error": (
                str(self.original_exception) if self.original_exception else None
            ),
        }


# ============================================================================
# 模型相关异常
# ============================================================================


class ModelError(HW1Error):
    """模型相关错误的基类。"""
    pass


class ModelLoadError(ModelError):
    """模型加载失败。"""

    def __init__(
        self,
        message: str,
        *,
        path: str | None = None,
        xml_hash: str | None = None,
        original_exception: Exception | None = None,
    ):
        context = {}
        if path:
            context["path"] = path
        if xml_hash:
            context["xml_hash"] = xml_hash
        super().__init__(message, context=context, original_exception=original_exception)


class ModelValidationError(ModelError):
    """模型验证失败。"""

    def __init__(
        self,
        message: str,
        *,
        required_joints: list[str] | None = None,
        required_actuators: list[str] | None = None,
        missing_items: list[str] | None = None,
    ):
        context = {}
        if required_joints:
            context["required_joints"] = required_joints
        if required_actuators:
            context["required_actuators"] = required_actuators
        if missing_items:
            context["missing_items"] = missing_items
        super().__init__(message, context=context)


# ============================================================================
# 仿真相关异常
# ============================================================================


class SimulationError(HW1Error):
    """仿真相关错误的基类。"""
    pass


class SimulationFailureError(SimulationError):
    """仿真失败（跌倒、不稳定等）。"""

    def __init__(
        self,
        message: str,
        *,
        failure_type: str | None = None,
        time: float | None = None,
        step: int | None = None,
        state: dict[str, Any] | None = None,
    ):
        context = {}
        if failure_type:
            context["failure_type"] = failure_type
        if time is not None:
            context["time"] = time
        if step is not None:
            context["step"] = step
        if state:
            context["state"] = state
        super().__init__(message, context=context)


class SimulationTimeoutError(SimulationError):
    """仿真超时。"""

    def __init__(
        self,
        message: str,
        *,
        elapsed_time: float | None = None,
        timeout: float | None = None,
    ):
        context = {}
        if elapsed_time is not None:
            context["elapsed_time"] = elapsed_time
        if timeout is not None:
            context["timeout"] = timeout
        super().__init__(message, context=context)


class SimulationNaNError(SimulationError):
    """仿真出现 NaN 值。"""

    def __init__(
        self,
        message: str,
        *,
        time: float | None = None,
        step: int | None = None,
        nan_variables: list[str] | None = None,
    ):
        context = {}
        if time is not None:
            context["time"] = time
        if step is not None:
            context["step"] = step
        if nan_variables:
            context["nan_variables"] = nan_variables
        super().__init__(message, context=context)


# ============================================================================
# 数据处理相关异常
# ============================================================================


class DataError(HW1Error):
    """数据处理相关错误的基类。"""
    pass


class DataValidationError(DataError):
    """数据验证失败。"""

    def __init__(
        self,
        message: str,
        *,
        field: str | None = None,
        expected: Any = None,
        actual: Any = None,
    ):
        context = {}
        if field:
            context["field"] = field
        if expected is not None:
            context["expected"] = expected
        if actual is not None:
            context["actual"] = actual
        super().__init__(message, context=context)


class DataIOError(DataError):
    """数据 I/O 错误。"""

    def __init__(
        self,
        message: str,
        *,
        path: str | None = None,
        operation: str | None = None,
        original_exception: Exception | None = None,
    ):
        context = {}
        if path:
            context["path"] = path
        if operation:
            context["operation"] = operation
        super().__init__(message, context=context, original_exception=original_exception)


# ============================================================================
# 控制相关异常
# ============================================================================


class ControlError(HW1Error):
    """控制相关错误的基类。"""
    pass


class ControlLimitError(ControlError):
    """控制输出超限。"""

    def __init__(
        self,
        message: str,
        *,
        actuator: str | None = None,
        value: float | None = None,
        limit: float | None = None,
    ):
        context = {}
        if actuator:
            context["actuator"] = actuator
        if value is not None:
            context["value"] = value
        if limit is not None:
            context["limit"] = limit
        super().__init__(message, context=context)


class ControlStabilityError(ControlError):
    """控制不稳定。"""

    def __init__(
        self,
        message: str,
        *,
        time: float | None = None,
        instability_metric: float | None = None,
    ):
        context = {}
        if time is not None:
            context["time"] = time
        if instability_metric is not None:
            context["instability_metric"] = instability_metric
        super().__init__(message, context=context)


# ============================================================================
# 便捷函数
# ============================================================================


def wrap_exception(
    exception: Exception,
    message: str | None = None,
    context: dict[str, Any] | None = None,
) -> HW1Error:
    """将标准异常包装为 HW1Error。

    Args:
        exception: 原始异常
        message: 自定义消息（如果为 None，使用原始异常消息）
        context: 额外的上下文信息

    Returns:
        HW1Error 实例

    Example:
        >>> try:
        ...     model = mujoco.MjModel.from_xml_path(path)
        ... except Exception as e:
        ...     raise wrap_exception(e, "Failed to load model", {"path": path})
    """
    msg = message or str(exception)
    return HW1Error(msg, context=context, original_exception=exception)
