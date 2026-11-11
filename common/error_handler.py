"""HW-1 项目统一错误处理装饰器和工具。

设计原则：
- 统一的异常捕获和转换
- 自动重试机制（带指数退避）
- 错误降级策略
- 异常上下文保存（用于调试）
- 集成日志系统

提供的功能：
- @handle_errors: 统一错误处理装饰器
- @retry_on_failure: 自动重试装饰器
- ErrorRecoveryStrategy: 错误恢复策略基类
- safe_execute: 安全执行函数（捕获异常）
"""

from __future__ import annotations

import functools
import time
import traceback
from typing import Any, Callable, TypeVar, cast

from .exceptions import (
    ControlError,
    DataError,
    HW1Error,
    ModelError,
    SimulationError,
)
from .logging_config import get_logger

T = TypeVar("T")

logger = get_logger(__name__)


# ============================================================================
# 错误处理装饰器
# ============================================================================


_UNSET = object()  # 哨兵值，用于区分 None 和未设置


def handle_errors(
    *,
    error_types: tuple[type[Exception], ...] = (Exception,),
    default_return: Any = _UNSET,
    raise_as: type[HW1Error] | None = None,
    log_level: str = "ERROR",
    capture_context: bool = True,
) -> Callable:
    """统一错误处理装饰器。

    Args:
        error_types: 要捕获的异常类型
        default_return: 发生错误时的默认返回值（_UNSET 则重新抛出）
        raise_as: 将捕获的异常转换为指定的 HW1Error 子类
        log_level: 日志级别（"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"）
        capture_context: 是否捕获局部变量作为上下文

    Example:
        >>> @handle_errors(error_types=(ValueError, KeyError), default_return=False)
        ... def risky_operation(x, y):
        ...     return x / y
        >>> risky_operation(1, 0)  # 返回 False 而不是抛出异常
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return func(*args, **kwargs)
            except error_types as e:
                # 构建错误上下文
                context = {
                    "function": func.__name__,
                    "module": func.__module__,
                    "args": str(args)[:200],  # 限制长度
                    "kwargs": str(kwargs)[:200],
                }

                # 捕获局部变量（调试用）
                if capture_context:
                    try:
                        frame = traceback.extract_tb(e.__traceback__)[-1]
                        context["file"] = frame.filename
                        context["line"] = frame.lineno
                    except Exception:
                        pass

                # 记录日志
                log_func = getattr(logger, log_level.lower())
                log_func(
                    f"Error in {func.__name__}: {e}",
                    exc_info=True,
                    extra={"context": context},
                )

                # 转换异常类型
                if raise_as is not None:
                    if not isinstance(e, HW1Error):
                        raise raise_as(
                            f"Error in {func.__name__}: {e}",
                            context=context,
                            original_exception=e,
                        ) from e
                    else:
                        raise

                # 返回默认值或重新抛出
                if default_return is not _UNSET:
                    return cast(T, default_return)
                else:
                    raise

        return wrapper

    return decorator


# ============================================================================
# 重试装饰器
# ============================================================================


def retry_on_failure(
    *,
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    on_retry: Callable[[Exception, int], None] | None = None,
) -> Callable:
    """自动重试装饰器（带指数退避）。

    Args:
        max_attempts: 最大尝试次数
        delay: 初始延迟时间（秒）
        backoff: 退避系数（每次失败后延迟时间乘以此系数）
        exceptions: 触发重试的异常类型
        on_retry: 重试前的回调函数（接收异常和尝试次数）

    Example:
        >>> @retry_on_failure(max_attempts=3, delay=0.5, backoff=2.0)
        ... def unstable_operation():
        ...     # 可能失败的操作
        ...     pass
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            current_delay = delay
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_attempts:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts",
                            exc_info=True,
                        )
                        raise

                    logger.warning(
                        f"{func.__name__} failed (attempt {attempt}/{max_attempts}), "
                        f"retrying in {current_delay:.2f}s...",
                        extra={"attempt": attempt, "exception": str(e)},
                    )

                    if on_retry:
                        on_retry(e, attempt)

                    time.sleep(current_delay)
                    current_delay *= backoff

            # 不应该到达这里，但为了类型检查
            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected retry loop exit")

        return wrapper

    return decorator


# ============================================================================
# 错误恢复策略
# ============================================================================


class ErrorRecoveryStrategy:
    """错误恢复策略基类。

    子类需要实现 recover 方法，定义具体的恢复逻辑。
    """

    def recover(
        self,
        error: Exception,
        context: dict[str, Any],
    ) -> Any:
        """尝试从错误中恢复。

        Args:
            error: 发生的异常
            context: 错误上下文

        Returns:
            恢复后的结果（如果恢复失败则抛出异常）

        Raises:
            Exception: 如果无法恢复
        """
        raise NotImplementedError


class FallbackStrategy(ErrorRecoveryStrategy):
    """降级策略：使用备用值或备用函数。"""

    def __init__(
        self,
        fallback_value: Any = None,
        fallback_func: Callable | None = None,
    ):
        """初始化降级策略。

        Args:
            fallback_value: 备用返回值
            fallback_func: 备用函数（优先于 fallback_value）
        """
        self.fallback_value = fallback_value
        self.fallback_func = fallback_func

    def recover(self, error: Exception, context: dict[str, Any]) -> Any:
        """使用备用值或备用函数恢复。"""
        logger.warning(
            f"Using fallback strategy for error: {error}",
            extra={"context": context},
        )

        if self.fallback_func is not None:
            return self.fallback_func(error, context)
        else:
            return self.fallback_value


class RetryStrategy(ErrorRecoveryStrategy):
    """重试策略：多次尝试执行。"""

    def __init__(
        self,
        func: Callable,
        max_attempts: int = 3,
        delay: float = 1.0,
    ):
        """初始化重试策略。

        Args:
            func: 要重试的函数
            max_attempts: 最大尝试次数
            delay: 重试间隔（秒）
        """
        self.func = func
        self.max_attempts = max_attempts
        self.delay = delay

    def recover(self, error: Exception, context: dict[str, Any]) -> Any:
        """通过重试恢复。"""
        for attempt in range(1, self.max_attempts + 1):
            try:
                logger.info(f"Retry attempt {attempt}/{self.max_attempts}")
                return self.func()
            except Exception:
                if attempt == self.max_attempts:
                    raise
                time.sleep(self.delay)
        raise error


# ============================================================================
# 安全执行工具
# ============================================================================


def safe_execute(
    func: Callable[..., T],
    *args: Any,
    default: T | None = None,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    log_errors: bool = True,
    **kwargs: Any,
) -> tuple[bool, T | None, Exception | None]:
    """安全执行函数，捕获异常。

    Args:
        func: 要执行的函数
        *args: 函数参数
        default: 发生错误时的默认返回值
        exceptions: 要捕获的异常类型
        log_errors: 是否记录错误日志
        **kwargs: 函数关键字参数

    Returns:
        (成功标志, 结果或默认值, 异常对象或None) 三元组

    Example:
        >>> success, result, error = safe_execute(risky_func, x=10)
        >>> if success:
        ...     print(f"Result: {result}")
        ... else:
        ...     print(f"Failed: {error}")
    """
    try:
        result = func(*args, **kwargs)
        return True, result, None
    except exceptions as e:
        if log_errors:
            logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
        return False, default, e


def safe_execute_with_recovery(
    func: Callable[..., T],
    recovery_strategy: ErrorRecoveryStrategy,
    *args: Any,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    **kwargs: Any,
) -> T:
    """安全执行函数，失败时使用恢复策略。

    Args:
        func: 要执行的函数
        recovery_strategy: 错误恢复策略
        *args: 函数参数
        exceptions: 要捕获的异常类型
        **kwargs: 函数关键字参数

    Returns:
        函数结果或恢复后的结果

    Example:
        >>> strategy = FallbackStrategy(fallback_value=0.0)
        >>> result = safe_execute_with_recovery(compute, strategy, x=10)
    """
    try:
        return func(*args, **kwargs)
    except exceptions as e:
        context = {
            "function": func.__name__,
            "args": args,
            "kwargs": kwargs,
        }
        logger.warning(f"Attempting recovery for error: {e}")
        return recovery_strategy.recover(e, context)


# ============================================================================
# 上下文管理器
# ============================================================================


class ErrorContext:
    """错误上下文管理器，自动捕获和转换异常。

    Example:
        >>> with ErrorContext(SimulationError, "Simulation failed"):
        ...     run_simulation()
        # 任何异常都会被转换为 SimulationError
    """

    def __init__(
        self,
        error_class: type[HW1Error],
        message: str,
        context: dict[str, Any] | None = None,
        reraise: bool = True,
    ):
        """初始化错误上下文。

        Args:
            error_class: 要转换成的异常类
            message: 错误消息
            context: 上下文信息
            reraise: 是否重新抛出异常
        """
        self.error_class = error_class
        self.message = message
        self.context = context or {}
        self.reraise = reraise

    def __enter__(self):
        """进入上下文。"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文，处理异常。"""
        if exc_type is None:
            return False

        # 如果已经是目标异常类型，直接重新抛出
        if isinstance(exc_val, self.error_class):
            return False

        # 转换异常
        logger.error(
            f"{self.message}: {exc_val}",
            exc_info=(exc_type, exc_val, exc_tb),
        )

        if self.reraise:
            raise self.error_class(
                self.message,
                context=self.context,
                original_exception=exc_val,
            ) from exc_val

        return True  # 抑制异常


# ============================================================================
# 异常分类器
# ============================================================================


def classify_exception(exception: Exception) -> str:
    """分类异常类型，返回分类标签。

    Args:
        exception: 异常对象

    Returns:
        异常分类标签（"model", "simulation", "data", "control", "unknown"）

    Example:
        >>> try:
        ...     risky_operation()
        ... except Exception as e:
        ...     category = classify_exception(e)
        ...     logger.error(f"Error category: {category}")
    """
    if isinstance(exception, ModelError):
        return "model"
    elif isinstance(exception, SimulationError):
        return "simulation"
    elif isinstance(exception, DataError):
        return "data"
    elif isinstance(exception, ControlError):
        return "control"
    elif isinstance(exception, (ValueError, TypeError)):
        return "validation"
    elif isinstance(exception, (IOError, OSError, FileNotFoundError)):
        return "io"
    else:
        return "unknown"


def get_recovery_suggestion(exception: Exception) -> str:
    """根据异常类型返回恢复建议。

    Args:
        exception: 异常对象

    Returns:
        恢复建议文本

    Example:
        >>> try:
        ...     load_model(path)
        ... except Exception as e:
        ...     suggestion = get_recovery_suggestion(e)
        ...     logger.info(f"Suggestion: {suggestion}")
    """
    category = classify_exception(exception)

    suggestions = {
        "model": "检查模型 XML 文件是否有效，关节/执行器名称是否正确",
        "simulation": "检查初始条件是否合理，仿真参数是否在有效范围内",
        "data": "检查数据文件是否存在，格式是否正确",
        "control": "检查控制参数是否合理，是否超出物理限制",
        "validation": "检查输入参数的类型和范围",
        "io": "检查文件路径是否正确，是否有读写权限",
        "unknown": "查看详细日志和堆栈跟踪信息",
    }

    return suggestions.get(category, suggestions["unknown"])
