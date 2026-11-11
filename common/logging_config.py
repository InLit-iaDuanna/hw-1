"""HW-1 项目统一日志配置。

设计原则：
- 结构化日志（支持 JSON 格式）
- 多级别日志（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- 多输出目标（控制台、文件、轮转文件）
- 性能友好（避免在关键路径产生开销）
- 上下文管理（自动附加实验参数、版本信息）

使用方式：
    from common.logging_config import get_logger, setup_logging

    # 在主脚本开始时设置
    setup_logging(level="INFO", log_dir="out/logs", enable_json=False)

    # 在模块中获取 logger
    logger = get_logger(__name__)
    logger.info("Simulation started", extra={"duration": 10.0})
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# ============================================================================
# 全局配置
# ============================================================================

DEFAULT_LOG_DIR = Path("out/logs")
DEFAULT_LEVEL = logging.INFO
DEFAULT_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 控制台彩色输出（可选）
COLORS = {
    "DEBUG": "\033[36m",  # Cyan
    "INFO": "\033[32m",  # Green
    "WARNING": "\033[33m",  # Yellow
    "ERROR": "\033[31m",  # Red
    "CRITICAL": "\033[1;31m",  # Bold Red
    "RESET": "\033[0m",
}

# 全局 logger 注册表
_loggers: dict[str, logging.Logger] = {}
_logging_configured = False


# ============================================================================
# 结构化日志格式化器
# ============================================================================


class StructuredFormatter(logging.Formatter):
    """JSON 格式的结构化日志。

    输出格式：
    {
        "timestamp": "2026-06-05T10:30:45.123456",
        "level": "INFO",
        "logger": "common.simulation_runner",
        "message": "Simulation completed",
        "context": {"duration": 10.0, "steps": 5000}
    }
    """

    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录为 JSON。"""
        log_obj = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # 添加额外的上下文信息
        if hasattr(record, "context"):
            log_obj["context"] = record.context
        elif hasattr(record, "extra"):
            log_obj["context"] = record.extra

        # 添加异常信息
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        # 添加代码位置信息（DEBUG 模式）
        if record.levelno >= logging.DEBUG:
            log_obj["location"] = {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName,
            }

        return json.dumps(log_obj, ensure_ascii=False)


class ColoredFormatter(logging.Formatter):
    """带颜色的控制台日志格式化器。"""

    def __init__(self, fmt: str, datefmt: str | None = None, use_colors: bool = True):
        super().__init__(fmt, datefmt)
        self.use_colors = use_colors

    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录（带颜色）。"""
        if self.use_colors and sys.stderr.isatty():
            levelname = record.levelname
            color = COLORS.get(levelname, "")
            reset = COLORS["RESET"]
            record.levelname = f"{color}{levelname}{reset}"

        result = super().format(record)
        return result


# ============================================================================
# 日志设置
# ============================================================================


def setup_logging(
    *,
    level: str | int = "INFO",
    log_dir: Path | str | None = None,
    log_file_prefix: str = "hw1",
    enable_console: bool = True,
    enable_file: bool = True,
    enable_json: bool = False,
    console_colors: bool = True,
    max_file_size: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5,
) -> None:
    """配置全局日志系统。

    Args:
        level: 日志级别（"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL" 或数字）
        log_dir: 日志文件目录（None 则使用默认）
        log_file_prefix: 日志文件前缀
        enable_console: 是否启用控制台输出
        enable_file: 是否启用文件输出
        enable_json: 是否使用 JSON 格式（文件）
        console_colors: 控制台是否使用颜色
        max_file_size: 单个日志文件最大大小（字节）
        backup_count: 保留的历史日志文件数量

    Example:
        >>> setup_logging(level="DEBUG", log_dir="out/logs/v19")
        >>> logger = get_logger(__name__)
        >>> logger.info("Test message")
    """
    global _logging_configured

    # 解析日志级别
    if isinstance(level, str):
        level = getattr(logging, level.upper(), DEFAULT_LEVEL)

    # 创建日志目录
    if log_dir is None:
        log_dir = DEFAULT_LOG_DIR
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    # 获取根 logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # 清除现有的 handlers
    root_logger.handlers.clear()

    # 控制台 handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(level)
        console_formatter = ColoredFormatter(
            DEFAULT_FORMAT,
            DEFAULT_DATE_FORMAT,
            use_colors=console_colors,
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

    # 文件 handler（轮转）
    if enable_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"{log_file_prefix}_{timestamp}.log"

        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(level)

        if enable_json:
            file_formatter = StructuredFormatter()
        else:
            file_formatter = logging.Formatter(DEFAULT_FORMAT, DEFAULT_DATE_FORMAT)

        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

        # 记录日志文件位置
        root_logger.info(f"Logging initialized: {log_file}")

    _logging_configured = True


def get_logger(name: str) -> logging.Logger:
    """获取或创建指定名称的 logger。

    Args:
        name: logger 名称（通常使用 __name__）

    Returns:
        Logger 实例

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Module loaded")
    """
    if name not in _loggers:
        logger = logging.getLogger(name)
        _loggers[name] = logger

        # 如果日志系统未初始化，使用基本配置
        if not _logging_configured:
            logging.basicConfig(
                level=DEFAULT_LEVEL,
                format=DEFAULT_FORMAT,
                datefmt=DEFAULT_DATE_FORMAT,
            )

    return _loggers[name]


# ============================================================================
# 上下文管理器（自动附加上下文信息）
# ============================================================================


class LogContext:
    """日志上下文管理器，自动附加元数据到日志。

    Example:
        >>> with LogContext(experiment="v19", slope_deg=2.5):
        ...     logger.info("Running simulation")
        # 输出: ... | Running simulation | context: {"experiment": "v19", "slope_deg": 2.5}
    """

    _context_stack: list[dict[str, Any]] = []

    def __init__(self, **context: Any):
        """初始化上下文。

        Args:
            **context: 上下文键值对
        """
        self.context = context

    def __enter__(self):
        """进入上下文。"""
        self._context_stack.append(self.context)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文。"""
        self._context_stack.pop()

    @classmethod
    def get_current_context(cls) -> dict[str, Any]:
        """获取当前累积的上下文。"""
        if not cls._context_stack:
            return {}
        # 合并所有上下文
        merged = {}
        for ctx in cls._context_stack:
            merged.update(ctx)
        return merged


class ContextAdapter(logging.LoggerAdapter):
    """Logger 适配器，自动附加上下文信息。"""

    def process(self, msg: str, kwargs: dict) -> tuple[str, dict]:
        """处理日志消息，附加上下文。"""
        context = LogContext.get_current_context()
        if context:
            # 将上下文添加到 extra
            extra = kwargs.get("extra", {})
            extra.update(context)
            kwargs["extra"] = extra
        return msg, kwargs


def get_context_logger(name: str) -> ContextAdapter:
    """获取带上下文的 logger。

    Args:
        name: logger 名称

    Returns:
        ContextAdapter 实例

    Example:
        >>> logger = get_context_logger(__name__)
        >>> with LogContext(version="v19"):
        ...     logger.info("Test")  # 自动附加 version=v19
    """
    base_logger = get_logger(name)
    return ContextAdapter(base_logger, {})


# ============================================================================
# 性能计时装饰器
# ============================================================================


def log_execution_time(
    logger: logging.Logger | None = None, level: int | str = logging.INFO
):
    """装饰器：记录函数执行时间。

    Args:
        logger: 使用的 logger（None 则使用函数所在模块的 logger）
        level: 日志级别

    Example:
        >>> @log_execution_time()
        ... def simulate(duration):
        ...     time.sleep(duration)
        >>> simulate(1.0)
        # 输出: Function 'simulate' executed in 1.002s
    """
    import functools
    import time

    def decorator(func):
        nonlocal logger, level
        if logger is None:
            logger = get_logger(func.__module__)

        # 转换 level 为整数
        if isinstance(level, str):
            level_int = getattr(logging, level.upper(), logging.INFO)
        else:
            level_int = level

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                elapsed = time.perf_counter() - start
                logger.log(
                    level_int,
                    f"Function '{func.__name__}' executed in {elapsed:.3f}s",
                    extra={"function": func.__name__, "elapsed_time": elapsed},
                )
                return result
            except Exception as e:
                elapsed = time.perf_counter() - start
                logger.error(
                    f"Function '{func.__name__}' failed after {elapsed:.3f}s: {e}",
                    exc_info=True,
                )
                raise

        return wrapper

    return decorator


# ============================================================================
# 便捷函数
# ============================================================================


def log_exception(
    logger: logging.Logger,
    exception: Exception,
    message: str | None = None,
    context: dict[str, Any] | None = None,
) -> None:
    """记录异常信息（带上下文）。

    Args:
        logger: Logger 实例
        exception: 异常对象
        message: 自定义消息
        context: 上下文信息

    Example:
        >>> try:
        ...     risky_operation()
        ... except Exception as e:
        ...     log_exception(logger, e, "Operation failed", {"param": value})
    """
    msg = message or f"Exception occurred: {type(exception).__name__}"
    logger.error(msg, exc_info=exception, extra={"context": context or {}})


def log_simulation_start(
    logger: logging.Logger,
    version: str,
    params: dict[str, Any],
) -> None:
    """记录仿真开始（标准格式）。

    Args:
        logger: Logger 实例
        version: 版本标识（如 "v19"）
        params: 仿真参数
    """
    logger.info(
        f"=== Simulation Start: {version} ===",
        extra={"event": "simulation_start", "version": version, "params": params},
    )


def log_simulation_end(
    logger: logging.Logger,
    version: str,
    success: bool,
    duration: float,
    metrics: dict[str, Any] | None = None,
) -> None:
    """记录仿真结束（标准格式）。

    Args:
        logger: Logger 实例
        version: 版本标识
        success: 是否成功
        duration: 仿真时长
        metrics: 性能指标
    """
    status = "SUCCESS" if success else "FAILURE"
    logger.info(
        f"=== Simulation End: {version} - {status} ({duration:.2f}s) ===",
        extra={
            "event": "simulation_end",
            "version": version,
            "success": success,
            "duration": duration,
            "metrics": metrics or {},
        },
    )
