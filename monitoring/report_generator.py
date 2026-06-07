"""
监控报告生成器 - 生成每日健康报告和趋势图表
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class ReportGenerator:
    """监控报告生成器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.monitoring_dir = project_root / "monitoring"
        self.reports_dir = self.monitoring_dir / "reports"
        self.reports_dir.mkdir(exist_ok=True)

    def load_latest_data(self) -> dict[str, Any]:
        """加载最新的监控数据"""
        data = {}

        # 健康报告
        health_file = self.monitoring_dir / "health_report.json"
        if health_file.exists():
            with open(health_file, encoding="utf-8") as f:
                data["health"] = json.load(f)

        # 指标数据
        metrics_file = self.monitoring_dir / "metrics_latest.json"
        if metrics_file.exists():
            with open(metrics_file, encoding="utf-8") as f:
                data["metrics"] = json.load(f)

        # 告警数据
        alerts_file = self.monitoring_dir / "alerts_history.json"
        if alerts_file.exists():
            with open(alerts_file, encoding="utf-8") as f:
                alerts = json.load(f)
                # 只取最近10条
                data["alerts"] = alerts[-10:] if len(alerts) > 10 else alerts

        return data

    def generate_markdown_report(self, data: dict[str, Any]) -> str:
        """生成 Markdown 格式的报告"""
        report = []
        report.append("# hw-1 项目健康监控报告\n")
        report.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        report.append("---\n")

        # 1. 总体健康状况
        report.append("## 1. 总体健康状况\n")
        if "health" in data:
            health = data["health"]
            summary = health.get("summary", {})
            total = summary.get("total", 0)
            passed = summary.get("passed", 0)
            failed = summary.get("failed", 0)
            warnings = summary.get("warnings", 0)

            # 计算健康分数
            if total > 0:
                health_score = (passed / total) * 100
                if failed > 0:
                    status_emoji = "🔴"
                    status_text = "不健康"
                elif warnings > 0:
                    status_emoji = "🟡"
                    status_text = "需要关注"
                else:
                    status_emoji = "🟢"
                    status_text = "健康"

                report.append(f"**状态**: {status_emoji} {status_text}\n")
                report.append(f"**健康分数**: {health_score:.1f}/100\n")
                report.append(f"**检查项**: {total} 项 ({passed} 通过, {failed} 失败, {warnings} 警告)\n")
            else:
                report.append("**状态**: ⚪ 无数据\n")

            # 详细检查结果
            report.append("\n### 详细检查结果\n")
            for check in health.get("checks", []):
                name = check.get("name", "unknown")
                status = check.get("status", "unknown")
                message = check.get("message", "")

                status_map = {
                    "PASS": "✅",
                    "FAIL": "❌",
                    "WARNING": "⚠️",
                    "UNKNOWN": "❓",
                }
                status_symbol = status_map.get(status, "❓")

                report.append(f"- **{name}** {status_symbol}: {message}\n")

        report.append("\n---\n")

        # 2. 关键指标
        report.append("## 2. 关键指标\n")
        if "metrics" in data:
            metrics = data["metrics"]

            # 代码指标
            code = metrics.get("code", {})
            report.append("### 代码度量\n")
            report.append(f"- Python 版本: {code.get('python_version', 'N/A')}\n")
            report.append(f"- 代码行数: {code.get('lines_of_code', 0):,}\n")
            report.append(f"- 文件数: {code.get('file_count', 0)}\n")
            report.append(f"- 版本目录: {code.get('version_count', 0)} 个\n")

            # 测试指标
            testing = metrics.get("testing", {})
            report.append("\n### 测试度量\n")
            report.append(f"- 测试文件: {testing.get('test_files_count', 0)} 个\n")
            report.append(f"- 测试用例: {testing.get('test_count', 0)} 个\n")
            cov = testing.get("coverage_percentage")
            if cov is not None:
                cov_emoji = "✅" if cov >= 80 else "⚠️" if cov >= 60 else "❌"
                report.append(f"- 测试覆盖率: {cov_emoji} {cov}%\n")
            else:
                report.append("- 测试覆盖率: 未测量\n")

            # 存储指标
            storage = metrics.get("storage", {})
            report.append("\n### 存储使用\n")
            report.append(
                f"- 输出目录: {storage.get('output_directory_size', 'N/A')}\n"
            )
            report.append(
                f"- 缓存目录: {storage.get('cache_directory_size', 'N/A')}\n"
            )

        report.append("\n---\n")

        # 3. 告警信息
        report.append("## 3. 最近告警\n")
        if "alerts" in data and data["alerts"]:
            alerts = data["alerts"]
            report.append(f"**总计**: {len(alerts)} 条告警\n\n")

            for alert in alerts:
                level = alert.get("level", "info")
                title = alert.get("title", "")
                message = alert.get("message", "")
                timestamp = alert.get("timestamp", "")

                level_emoji = {
                    "critical": "🔴",
                    "warning": "🟡",
                    "info": "🔵",
                }.get(level, "⚪")

                report.append(f"- {level_emoji} **{title}** ({timestamp})\n")
                report.append(f"  {message}\n")
        else:
            report.append("✅ 没有告警\n")

        report.append("\n---\n")

        # 4. 建议
        report.append("## 4. 改进建议\n")
        suggestions = []

        # 基于数据生成建议
        if "metrics" in data:
            cov = data["metrics"].get("testing", {}).get("coverage_percentage")
            if cov is not None and cov < 80:
                suggestions.append(
                    f"- 提高测试覆盖率（当前 {cov}%，建议 ≥ 80%）"
                )

        if "health" in data:
            failed = data["health"].get("summary", {}).get("failed", 0)
            if failed > 0:
                suggestions.append("- 修复失败的健康检查项")

        if "alerts" in data:
            critical_alerts = [
                a for a in data["alerts"] if a.get("level") == "critical"
            ]
            if critical_alerts:
                suggestions.append(f"- 处理 {len(critical_alerts)} 条严重告警")

        if suggestions:
            for suggestion in suggestions:
                report.append(f"{suggestion}\n")
        else:
            report.append("✅ 目前没有改进建议，保持当前状态\n")

        report.append("\n---\n")
        report.append("*本报告由 hw-1 监控系统自动生成*\n")

        return "".join(report)

    def generate_report(self) -> Path:
        """生成报告"""
        print("=" * 60)
        print("生成监控报告")
        print("=" * 60)

        # 加载数据
        print("加载监控数据...")
        data = self.load_latest_data()

        # 生成 Markdown 报告
        print("生成 Markdown 报告...")
        markdown_content = self.generate_markdown_report(data)

        # 保存报告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.reports_dir / f"health_report_{timestamp}.md"

        with open(report_file, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        # 同时保存一份最新的
        latest_file = self.reports_dir / "health_report_latest.md"
        with open(latest_file, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        print(f"[OK] 报告已生成: {report_file}")
        print(f"[OK] 最新报告: {latest_file}")
        print("=" * 60)

        return report_file

    def generate_trend_chart(self) -> Path | None:
        """生成趋势图表"""
        try:
            import matplotlib.pyplot as plt

            # 读取历史数据
            history_file = self.monitoring_dir / "metrics_history.json"
            if not history_file.exists():
                print("[WARN] 没有历史数据，跳过图表生成")
                return None

            with open(history_file, encoding="utf-8") as f:
                history = json.load(f)

            if len(history) < 2:
                print("[WARN] 历史数据不足，跳过图表生成")
                return None

            # 提取覆盖率数据
            timestamps = []
            coverages = []
            for record in history[-30:]:  # 最近30条记录
                cov = record.get("testing", {}).get("coverage_percentage")
                if cov is not None:
                    timestamps.append(record.get("timestamp", ""))
                    coverages.append(cov)

            if not timestamps:
                print("[WARN] 没有覆盖率数据，跳过图表生成")
                return None

            # 创建图表
            plt.figure(figsize=(12, 6))
            plt.plot(range(len(coverages)), coverages, marker="o", linewidth=2)
            plt.axhline(y=80, color="r", linestyle="--", label="目标: 80%")
            plt.xlabel("记录序号")
            plt.ylabel("测试覆盖率 (%)")
            plt.title("测试覆盖率趋势")
            plt.grid(True, alpha=0.3)
            plt.legend()
            plt.tight_layout()

            # 保存图表
            chart_file = self.reports_dir / "coverage_trend.png"
            plt.savefig(chart_file, dpi=150)
            plt.close()

            print(f"[OK] 趋势图已生成: {chart_file}")
            return chart_file

        except ImportError:
            print("[WARN] matplotlib 未安装，跳过图表生成")
            return None
        except Exception as e:
            print(f"[WARN] 图表生成失败: {e}")
            return None


if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    generator = ReportGenerator(project_root)

    # 生成报告
    report_file = generator.generate_report()

    # 生成图表
    chart_file = generator.generate_trend_chart()

    print("\n[OK] 报告生成完成")
