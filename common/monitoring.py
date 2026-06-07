"""HW-1 项目监控和告警系统。

设计原则：
- 实时监控关键指标（内存、CPU、仿真状态）
- 阈值告警机制
- 性能指标收集和分析
- 资源使用追踪
- 集成日志系统

提供的功能：
- SystemMonitor: 系统资源监控
- SimulationMonitor: 仿真状态监控
- PerformanceTracker: 性能指标追踪
- AlertManager: 告警管理
"""

from __future__ import annotations

import platform
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

try:
    import psutil

    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

from .logging_config import get_logger

logger = get_logger(__name__)


# ============================================================================
# 数据类
# ============================================================================


@dataclass
class ResourceSnapshot:
    """系统资源快照。"""

    timestamp: float
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    available_memory_mb: float


@dataclass
class SimulationMetrics:
    """仿真指标快照。"""

    timestamp: float
    simulated_time: float
    step_count: int
    wall_time: float
    steps_per_second: float
    realtime_factor: float
    custom_metrics: dict[str, Any] = field(default_factory=dict)


@dataclass
class Alert:
    """告警记录。"""

    timestamp: float
    level: str  # "INFO", "WARNING", "ERROR", "CRITICAL"
    category: str  # "resource", "performance", "simulation", "custom"
    message: str
    context: dict[str, Any] = field(default_factory=dict)


# ============================================================================
# 系统资源监控
# ============================================================================


class SystemMonitor:
    """系统资源监控器。

    监控 CPU、内存使用情况，并在超过阈值时发出告警。

    Example:
        >>> monitor = SystemMonitor(
        ...     memory_threshold_percent=80.0,
        ...     cpu_threshold_percent=90.0
        ... )
        >>> monitor.start()
        >>> # ... 运行仿真 ...
        >>> monitor.stop()
        >>> report = monitor.get_report()
    """

    def __init__(
        self,
        *,
        memory_threshold_percent: float = 85.0,
        memory_threshold_mb: float | None = None,
        cpu_threshold_percent: float = 95.0,
        check_interval: float = 1.0,
        alert_callback: Callable[[Alert], None] | None = None,
    ):
        """初始化系统监控器。

        Args:
            memory_threshold_percent: 内存使用百分比阈值
            memory_threshold_mb: 内存使用绝对值阈值（MB）
            cpu_threshold_percent: CPU 使用百分比阈值
            check_interval: 检查间隔（秒）
            alert_callback: 告警回调函数
        """
        if not HAS_PSUTIL:
            logger.warning(
                "psutil not installed, system monitoring will be limited. "
                "Install with: pip install psutil"
            )

        self.memory_threshold_percent = memory_threshold_percent
        self.memory_threshold_mb = memory_threshold_mb
        self.cpu_threshold_percent = cpu_threshold_percent
        self.check_interval = check_interval
        self.alert_callback = alert_callback

        self.snapshots: list[ResourceSnapshot] = []
        self.alerts: list[Alert] = []
        self.is_running = False
        self.start_time: float | None = None
        self.process = psutil.Process() if HAS_PSUTIL else None

    def start(self) -> None:
        """开始监控。"""
        self.is_running = True
        self.start_time = time.time()
        self.snapshots.clear()
        self.alerts.clear()
        logger.info("System monitoring started")

    def stop(self) -> None:
        """停止监控。"""
        self.is_running = False
        logger.info(
            f"System monitoring stopped. Collected {len(self.snapshots)} snapshots, "
            f"{len(self.alerts)} alerts"
        )

    def check(self) -> ResourceSnapshot | None:
        """检查当前资源使用情况。

        Returns:
            资源快照（如果 psutil 不可用则返回 None）
        """
        if not HAS_PSUTIL or not self.process:
            return None

        try:
            # 获取进程信息
            mem_info = self.process.memory_info()
            memory_mb = mem_info.rss / (1024 * 1024)

            # 获取系统信息
            sys_mem = psutil.virtual_memory()
            memory_percent = sys_mem.percent
            available_memory_mb = sys_mem.available / (1024 * 1024)

            # CPU 使用率（需要一定时间间隔才准确）
            cpu_percent = self.process.cpu_percent(interval=0.1)

            snapshot = ResourceSnapshot(
                timestamp=time.time(),
                cpu_percent=cpu_percent,
                memory_mb=memory_mb,
                memory_percent=memory_percent,
                available_memory_mb=available_memory_mb,
            )

            if self.is_running:
                self.snapshots.append(snapshot)

            # 检查阈值
            self._check_thresholds(snapshot)

            return snapshot

        except Exception as e:
            logger.warning(f"Failed to collect resource snapshot: {e}")
            return None

    def _check_thresholds(self, snapshot: ResourceSnapshot) -> None:
        """检查资源使用是否超过阈值。"""
        # 检查内存百分比
        if snapshot.memory_percent > self.memory_threshold_percent:
            self._raise_alert(
                level="WARNING",
                category="resource",
                message=f"System memory usage high: {snapshot.memory_percent:.1f}%",
                context={
                    "memory_percent": snapshot.memory_percent,
                    "threshold": self.memory_threshold_percent,
                },
            )

        # 检查内存绝对值
        if (
            self.memory_threshold_mb is not None
            and snapshot.memory_mb > self.memory_threshold_mb
        ):
            self._raise_alert(
                level="WARNING",
                category="resource",
                message=f"Process memory usage high: {snapshot.memory_mb:.1f} MB",
                context={
                    "memory_mb": snapshot.memory_mb,
                    "threshold_mb": self.memory_threshold_mb,
                },
            )

        # 检查 CPU
        if snapshot.cpu_percent > self.cpu_threshold_percent:
            self._raise_alert(
                level="INFO",
                category="resource",
                message=f"CPU usage high: {snapshot.cpu_percent:.1f}%",
                context={
                    "cpu_percent": snapshot.cpu_percent,
                    "threshold": self.cpu_threshold_percent,
                },
            )

    def _raise_alert(
        self,
        level: str,
        category: str,
        message: str,
        context: dict[str, Any],
    ) -> None:
        """触发告警。"""
        alert = Alert(
            timestamp=time.time(),
            level=level,
            category=category,
            message=message,
            context=context,
        )

        self.alerts.append(alert)

        # 记录日志
        log_func = getattr(logger, level.lower())
        log_func(message, extra={"alert": True, "context": context})

        # 调用回调
        if self.alert_callback:
            try:
                self.alert_callback(alert)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")

    def get_report(self) -> dict[str, Any]:
        """生成监控报告。

        Returns:
            监控报告字典
        """
        if not HAS_PSUTIL:
            return {
                "status": "psutil_not_available",
                "message": "psutil not installed, monitoring data unavailable",
            }

        if not self.snapshots:
            return {
                "status": "no_data",
                "message": "No monitoring data collected",
            }

        cpu_values = [s.cpu_percent for s in self.snapshots]
        mem_values = [s.memory_mb for s in self.snapshots]
        mem_pct_values = [s.memory_percent for s in self.snapshots]

        report = {
            "duration": (
                time.time() - self.start_time if self.start_time else 0.0
            ),
            "snapshots_count": len(self.snapshots),
            "alerts_count": len(self.alerts),
            "cpu": {
                "mean": sum(cpu_values) / len(cpu_values),
                "max": max(cpu_values),
                "min": min(cpu_values),
            },
            "memory_mb": {
                "mean": sum(mem_values) / len(mem_values),
                "max": max(mem_values),
                "min": min(mem_values),
            },
            "memory_percent": {
                "mean": sum(mem_pct_values) / len(mem_pct_values),
                "max": max(mem_pct_values),
                "min": min(mem_pct_values),
            },
            "alerts": [
                {
                    "level": a.level,
                    "category": a.category,
                    "message": a.message,
                    "timestamp": a.timestamp,
                }
                for a in self.alerts
            ],
        }

        return report


# ============================================================================
# 仿真状态监控
# ============================================================================


class SimulationMonitor:
    """仿真状态监控器。

    监控仿真进度、性能、稳定性等指标。

    Example:
        >>> monitor = SimulationMonitor()
        >>> monitor.start()
        >>> for step in range(n_steps):
        ...     # 仿真循环
        ...     monitor.update(simulated_time=step*dt, step_count=step)
        >>> monitor.stop()
    """

    def __init__(
        self,
        *,
        target_realtime_factor: float = 1.0,
        min_steps_per_second: float = 100.0,
        alert_callback: Callable[[Alert], None] | None = None,
    ):
        """初始化仿真监控器。

        Args:
            target_realtime_factor: 目标实时因子（1.0 = 实时）
            min_steps_per_second: 最小步进速率（步/秒）
            alert_callback: 告警回调函数
        """
        self.target_realtime_factor = target_realtime_factor
        self.min_steps_per_second = min_steps_per_second
        self.alert_callback = alert_callback

        self.metrics: list[SimulationMetrics] = []
        self.alerts: list[Alert] = []
        self.is_running = False
        self.start_time: float | None = None
        self.last_check_time: float | None = None
        self.last_step_count: int = 0

    def start(self) -> None:
        """开始监控。"""
        self.is_running = True
        self.start_time = time.time()
        self.last_check_time = self.start_time
        self.last_step_count = 0
        self.metrics.clear()
        self.alerts.clear()
        logger.info("Simulation monitoring started")

    def stop(self) -> None:
        """停止监控。"""
        self.is_running = False
        logger.info(
            f"Simulation monitoring stopped. Collected {len(self.metrics)} metrics"
        )

    def update(
        self,
        simulated_time: float,
        step_count: int,
        custom_metrics: dict[str, Any] | None = None,
    ) -> None:
        """更新仿真状态。

        Args:
            simulated_time: 当前仿真时间
            step_count: 当前步数
            custom_metrics: 自定义指标
        """
        if not self.is_running or self.start_time is None:
            return

        current_time = time.time()
        wall_time = current_time - self.start_time

        # 计算性能指标
        if self.last_check_time is not None and wall_time > 0:
            dt = current_time - self.last_check_time
            steps_elapsed = step_count - self.last_step_count

            if dt > 0:
                steps_per_second = steps_elapsed / dt
                realtime_factor = simulated_time / wall_time if wall_time > 0 else 0.0

                metric = SimulationMetrics(
                    timestamp=current_time,
                    simulated_time=simulated_time,
                    step_count=step_count,
                    wall_time=wall_time,
                    steps_per_second=steps_per_second,
                    realtime_factor=realtime_factor,
                    custom_metrics=custom_metrics or {},
                )

                self.metrics.append(metric)

                # 检查性能阈值
                self._check_performance(metric)

        self.last_check_time = current_time
        self.last_step_count = step_count

    def _check_performance(self, metric: SimulationMetrics) -> None:
        """检查性能指标。"""
        # 检查步进速率
        if metric.steps_per_second < self.min_steps_per_second:
            self._raise_alert(
                level="WARNING",
                category="performance",
                message=f"Simulation speed low: {metric.steps_per_second:.1f} steps/s",
                context={
                    "steps_per_second": metric.steps_per_second,
                    "threshold": self.min_steps_per_second,
                },
            )

    def _raise_alert(
        self,
        level: str,
        category: str,
        message: str,
        context: dict[str, Any],
    ) -> None:
        """触发告警。"""
        alert = Alert(
            timestamp=time.time(),
            level=level,
            category=category,
            message=message,
            context=context,
        )

        self.alerts.append(alert)

        log_func = getattr(logger, level.lower())
        log_func(message, extra={"alert": True, "context": context})

        if self.alert_callback:
            try:
                self.alert_callback(alert)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")

    def get_report(self) -> dict[str, Any]:
        """生成监控报告。"""
        if not self.metrics:
            return {"status": "no_data", "message": "No simulation metrics collected"}

        sps_values = [m.steps_per_second for m in self.metrics]
        rtf_values = [m.realtime_factor for m in self.metrics]

        report = {
            "total_simulated_time": (
                self.metrics[-1].simulated_time if self.metrics else 0.0
            ),
            "total_wall_time": (
                time.time() - self.start_time if self.start_time else 0.0
            ),
            "total_steps": self.metrics[-1].step_count if self.metrics else 0,
            "metrics_count": len(self.metrics),
            "alerts_count": len(self.alerts),
            "steps_per_second": {
                "mean": sum(sps_values) / len(sps_values),
                "max": max(sps_values),
                "min": min(sps_values),
            },
            "realtime_factor": {
                "mean": sum(rtf_values) / len(rtf_values),
                "max": max(rtf_values),
                "min": min(rtf_values),
            },
            "alerts": [
                {
                    "level": a.level,
                    "category": a.category,
                    "message": a.message,
                    "timestamp": a.timestamp,
                }
                for a in self.alerts
            ],
        }

        return report


# ============================================================================
# 性能追踪器
# ============================================================================


class PerformanceTracker:
    """性能追踪器（细粒度计时）。

    Example:
        >>> tracker = PerformanceTracker()
        >>> with tracker.track("forward_kinematics"):
        ...     # 耗时操作
        ...     pass
        >>> report = tracker.get_report()
    """

    def __init__(self):
        """初始化性能追踪器。"""
        self.timings: dict[str, list[float]] = {}

    def track(self, name: str):
        """创建计时上下文管理器。

        Args:
            name: 操作名称

        Returns:
            上下文管理器
        """
        return self._TimingContext(self, name)

    class _TimingContext:
        def __init__(self, tracker: PerformanceTracker, name: str):
            self.tracker = tracker
            self.name = name
            self.start_time: float | None = None

        def __enter__(self):
            self.start_time = time.perf_counter()
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            if self.start_time is not None:
                elapsed = time.perf_counter() - self.start_time
                if self.name not in self.tracker.timings:
                    self.tracker.timings[self.name] = []
                self.tracker.timings[self.name].append(elapsed)

    def get_report(self) -> dict[str, dict[str, float]]:
        """生成性能报告。

        Returns:
            {操作名: {mean, max, min, total, count}}
        """
        report = {}
        for name, times in self.timings.items():
            if times:
                report[name] = {
                    "mean": sum(times) / len(times),
                    "max": max(times),
                    "min": min(times),
                    "total": sum(times),
                    "count": len(times),
                }
        return report

    def clear(self) -> None:
        """清除所有计时数据。"""
        self.timings.clear()


# ============================================================================
# 告警管理器
# ============================================================================


class AlertManager:
    """统一告警管理器。

    Example:
        >>> manager = AlertManager()
        >>> system_monitor = SystemMonitor(alert_callback=manager.handle_alert)
        >>> sim_monitor = SimulationMonitor(alert_callback=manager.handle_alert)
        >>> # ... 运行监控 ...
        >>> manager.print_summary()
    """

    def __init__(self):
        """初始化告警管理器。"""
        self.alerts: list[Alert] = []

    def handle_alert(self, alert: Alert) -> None:
        """处理告警。

        Args:
            alert: 告警对象
        """
        self.alerts.append(alert)

        # 根据级别采取不同动作
        if alert.level == "CRITICAL":
            logger.critical(f"CRITICAL ALERT: {alert.message}")
        elif alert.level == "ERROR":
            logger.error(f"ERROR ALERT: {alert.message}")
        elif alert.level == "WARNING":
            logger.warning(f"WARNING: {alert.message}")
        else:
            logger.info(f"INFO: {alert.message}")

    def get_alerts(
        self,
        level: str | None = None,
        category: str | None = None,
    ) -> list[Alert]:
        """获取告警列表（可选过滤）。

        Args:
            level: 过滤级别
            category: 过滤类别

        Returns:
            告警列表
        """
        filtered = self.alerts
        if level:
            filtered = [a for a in filtered if a.level == level]
        if category:
            filtered = [a for a in filtered if a.category == category]
        return filtered

    def print_summary(self) -> None:
        """打印告警摘要。"""
        if not self.alerts:
            logger.info("No alerts recorded")
            return

        by_level = {}
        by_category = {}

        for alert in self.alerts:
            by_level[alert.level] = by_level.get(alert.level, 0) + 1
            by_category[alert.category] = by_category.get(alert.category, 0) + 1

        logger.info("=== Alert Summary ===")
        logger.info(f"Total alerts: {len(self.alerts)}")
        logger.info(f"By level: {by_level}")
        logger.info(f"By category: {by_category}")

    def clear(self) -> None:
        """清除所有告警。"""
        self.alerts.clear()
