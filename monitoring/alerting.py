"""
告警系统 - hw-1 项目告警和通知
"""

import json
import logging
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import yaml


class AlertLevel(Enum):
    """告警级别"""

    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class Alert:
    """告警对象"""

    def __init__(
        self,
        level: AlertLevel,
        title: str,
        message: str,
        details: dict[str, Any] | None = None,
    ):
        self.level = level
        self.title = title
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.now()

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "title": self.title,
            "message": self.message,
            "details": self.details,
        }

    def __str__(self) -> str:
        level_symbols = {
            AlertLevel.CRITICAL: "[CRITICAL]",
            AlertLevel.WARNING: "[WARNING]",
            AlertLevel.INFO: "[INFO]",
        }
        symbol = level_symbols.get(self.level, "[UNKNOWN]")
        time_str = self.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        return f"{symbol} {time_str} - {self.title}: {self.message}"


class AlertingSystem:
    """告警系统"""

    def __init__(self, project_root: Path, config_path: Path | None = None):
        self.project_root = project_root
        if config_path is None:
            config_path = project_root / "monitoring" / "config.yaml"
        self.config = self._load_config(config_path)
        self.alerts: list[Alert] = []
        self._setup_logging()

    def _load_config(self, config_path: Path) -> dict:
        """加载配置文件"""
        if not config_path.exists():
            return {}
        with open(config_path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _setup_logging(self):
        """设置日志系统"""
        log_file = self.config.get("alerting", {}).get(
            "log_file", "monitoring/alerts.log"
        )
        log_path = self.project_root / log_file

        # 确保目录存在
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # 配置日志
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(log_path, encoding="utf-8"),
                logging.StreamHandler(),
            ],
        )
        self.logger = logging.getLogger(__name__)

    def add_alert(self, alert: Alert):
        """添加告警"""
        self.alerts.append(alert)

        # 根据配置的方式发送告警
        methods = self.config.get("alerting", {}).get("methods", ["console"])

        if "console" in methods:
            print(alert)

        if "log_file" in methods:
            if alert.level == AlertLevel.CRITICAL:
                self.logger.error(f"{alert.title}: {alert.message}")
            elif alert.level == AlertLevel.WARNING:
                self.logger.warning(f"{alert.title}: {alert.message}")
            else:
                self.logger.info(f"{alert.title}: {alert.message}")

    def analyze_health_report(self, health_report: dict[str, Any]):
        """分析健康报告并生成告警"""
        print("=" * 60)
        print("告警分析")
        print("=" * 60)

        for check in health_report.get("checks", []):
            status = check.get("status")
            name = check.get("name")
            message = check.get("message")
            details = check.get("details", {})

            if status == "FAIL":
                self.add_alert(
                    Alert(
                        level=AlertLevel.CRITICAL,
                        title=f"健康检查失败: {name}",
                        message=message,
                        details=details,
                    )
                )
            elif status == "WARNING":
                self.add_alert(
                    Alert(
                        level=AlertLevel.WARNING,
                        title=f"健康检查警告: {name}",
                        message=message,
                        details=details,
                    )
                )

    def analyze_metrics(self, metrics: dict[str, Any], history: list[dict[str, Any]] | None = None):
        """分析指标并生成告警"""
        # 检查测试覆盖率
        coverage = metrics.get("testing", {}).get("coverage_percentage")
        if coverage is not None:
            threshold = 80  # 从配置读取
            for check_config in self.config.get("checks", []):
                if check_config.get("name") == "test_coverage":
                    threshold = check_config.get("threshold", 80)
                    break

            if coverage < threshold:
                self.add_alert(
                    Alert(
                        level=AlertLevel.WARNING,
                        title="测试覆盖率不足",
                        message=f"当前覆盖率 {coverage}% 低于阈值 {threshold}%",
                        details={"coverage": coverage, "threshold": threshold},
                    )
                )

        # 检查性能退化（如果有历史数据）
        if history and len(history) > 1:
            prev_metrics = history[-2] if len(history) >= 2 else None
            if prev_metrics:
                # 比较存储使用
                current_size = metrics.get("storage", {}).get(
                    "output_directory_size_bytes", 0
                )
                prev_size = prev_metrics.get("storage", {}).get(
                    "output_directory_size_bytes", 0
                )

                if prev_size > 0 and current_size > prev_size * 1.5:
                    self.add_alert(
                        Alert(
                            level=AlertLevel.WARNING,
                            title="存储使用量增长过快",
                            message=f"输出目录大小增长了 {((current_size - prev_size) / prev_size * 100):.1f}%",
                            details={
                                "current_size": metrics["storage"].get(
                                    "output_directory_size"
                                ),
                                "previous_size": prev_metrics["storage"].get(
                                    "output_directory_size"
                                ),
                            },
                        )
                    )

        # 检查代码质量
        code_metrics = metrics.get("code", {})
        if "error" in code_metrics:
            self.add_alert(
                Alert(
                    level=AlertLevel.WARNING,
                    title="代码指标收集失败",
                    message=code_metrics["error"],
                )
            )

        print(f"生成了 {len(self.alerts)} 条告警")
        print("=" * 60)

    def save_alerts(self):
        """保存告警历史"""
        alerts_file = self.project_root / "monitoring" / "alerts_history.json"

        # 读取现有告警
        history = []
        if alerts_file.exists():
            try:
                with open(alerts_file, encoding="utf-8") as f:
                    history = json.load(f)
            except Exception:
                history = []

        # 追加新告警
        for alert in self.alerts:
            history.append(alert.to_dict())

        # 限制历史记录
        max_records = 1000
        if len(history) > max_records:
            history = history[-max_records:]

        # 保存
        with open(alerts_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)

        print(f"告警历史已保存至: {alerts_file}")

    def generate_alert_summary(self) -> str:
        """生成告警摘要"""
        if not self.alerts:
            return "[OK] 没有告警"

        critical = sum(1 for a in self.alerts if a.level == AlertLevel.CRITICAL)
        warning = sum(1 for a in self.alerts if a.level == AlertLevel.WARNING)
        info = sum(1 for a in self.alerts if a.level == AlertLevel.INFO)

        summary = f"[SUMMARY] 告警摘要: {critical} 严重, {warning} 警告, {info} 信息\n\n"

        if critical > 0:
            summary += "[CRITICAL] 严重告警:\n"
            for alert in self.alerts:
                if alert.level == AlertLevel.CRITICAL:
                    summary += f"  - {alert.title}: {alert.message}\n"
            summary += "\n"

        if warning > 0:
            summary += "[WARNING] 警告:\n"
            for alert in self.alerts:
                if alert.level == AlertLevel.WARNING:
                    summary += f"  - {alert.title}: {alert.message}\n"
            summary += "\n"

        return summary


if __name__ == "__main__":
    # 测试告警系统
    project_root = Path(__file__).parent.parent

    system = AlertingSystem(project_root)

    # 读取最新的健康报告
    health_report_file = project_root / "monitoring" / "health_report.json"
    if health_report_file.exists():
        with open(health_report_file, encoding="utf-8") as f:
            health_report = json.load(f)
        system.analyze_health_report(health_report)

    # 读取最新的指标
    metrics_file = project_root / "monitoring" / "metrics_latest.json"
    history_file = project_root / "monitoring" / "metrics_history.json"

    if metrics_file.exists():
        with open(metrics_file, encoding="utf-8") as f:
            metrics = json.load(f)

        history = None
        if history_file.exists():
            with open(history_file, encoding="utf-8") as f:
                history = json.load(f)

        system.analyze_metrics(metrics, history)

    # 保存告警
    system.save_alerts()

    # 打印摘要
    print("\n" + system.generate_alert_summary())
