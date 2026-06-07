"""
测试覆盖率监控 - 跟踪测试覆盖率变化趋势
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


class TestCoverageMonitor:
    """测试覆盖率监控器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def run_coverage_analysis(self) -> dict[str, Any]:
        """运行覆盖率分析"""
        results = {
            "status": "unknown",
            "coverage_percentage": 0,
            "covered_lines": 0,
            "missing_lines": 0,
            "total_statements": 0,
        }

        try:
            print("运行测试并收集覆盖率数据...")

            # 运行 pytest 并生成覆盖率报告
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "tests/",
                    "--cov=common",
                    "--cov-report=json",
                    "--cov-report=term",
                    "-q",
                ],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                check=False,
                timeout=300,
            )

            results["test_output"] = result.stdout
            results["test_exit_code"] = result.returncode

            # 读取生成的 coverage.json
            coverage_file = self.project_root / "coverage.json"
            if coverage_file.exists():
                with open(coverage_file, encoding="utf-8") as f:
                    cov_data = json.load(f)

                totals = cov_data.get("totals", {})
                results["coverage_percentage"] = round(
                    totals.get("percent_covered", 0), 2
                )
                results["covered_lines"] = totals.get("covered_lines", 0)
                results["missing_lines"] = totals.get("missing_lines", 0)
                results["total_statements"] = totals.get("num_statements", 0)

                # 按文件统计覆盖率
                files_coverage = {}
                for file_path, file_data in cov_data.get("files", {}).items():
                    summary = file_data.get("summary", {})
                    files_coverage[file_path] = {
                        "percent_covered": round(
                            summary.get("percent_covered", 0), 2
                        ),
                        "covered_lines": summary.get("covered_lines", 0),
                        "missing_lines": summary.get("missing_lines", 0),
                    }

                results["files_coverage"] = files_coverage
                results["status"] = "success"
            else:
                results["status"] = "error"
                results["message"] = "coverage.json 未生成"

        except subprocess.TimeoutExpired:
            results["status"] = "timeout"
            results["message"] = "测试超时（5分钟）"
        except Exception as e:
            results["status"] = "error"
            results["error"] = str(e)

        return results

    def compare_with_history(
        self, current: dict[str, Any], history: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """与历史数据比较"""
        comparison = {
            "current_coverage": current.get("coverage_percentage", 0),
            "previous_coverage": None,
            "change": None,
            "trend": "stable",
        }

        if history and len(history) > 0:
            # 查找最近的有效覆盖率数据
            for hist in reversed(history):
                prev_cov = hist.get("coverage_percentage")
                if prev_cov is not None:
                    comparison["previous_coverage"] = prev_cov
                    break

            if comparison["previous_coverage"] is not None:
                change = (
                    comparison["current_coverage"] - comparison["previous_coverage"]
                )
                comparison["change"] = round(change, 2)

                if change > 1:
                    comparison["trend"] = "improving"
                elif change < -1:
                    comparison["trend"] = "declining"

        return comparison

    def find_uncovered_code(self, results: dict[str, Any]) -> list[dict[str, Any]]:
        """找出覆盖率最低的文件"""
        files_cov = results.get("files_coverage", {})
        uncovered = []

        for file_path, cov_data in files_cov.items():
            if cov_data["percent_covered"] < 80:
                uncovered.append(
                    {
                        "file": file_path,
                        "coverage": cov_data["percent_covered"],
                        "missing_lines": cov_data["missing_lines"],
                    }
                )

        # 按覆盖率排序
        uncovered.sort(key=lambda x: x["coverage"])
        return uncovered

    def run_monitoring(self) -> dict[str, Any]:
        """运行监控"""
        print("=" * 60)
        print("测试覆盖率监控")
        print("=" * 60)

        # 运行覆盖率分析
        results = self.run_coverage_analysis()

        # 打印结果
        if results["status"] == "success":
            print(f"\n✅ 覆盖率: {results['coverage_percentage']}%")
            print(f"   已覆盖: {results['covered_lines']} 行")
            print(f"   未覆盖: {results['missing_lines']} 行")
            print(f"   总语句: {results['total_statements']} 行")

            # 读取历史数据进行比较
            history_file = self.project_root / "monitoring" / "coverage_history.json"
            history = []
            if history_file.exists():
                try:
                    with open(history_file, encoding="utf-8") as f:
                        history = json.load(f)
                except Exception:
                    pass

            comparison = self.compare_with_history(results, history)
            print(f"\n📊 趋势: {comparison['trend']}")
            if comparison["previous_coverage"] is not None:
                print(f"   之前: {comparison['previous_coverage']}%")
                print(f"   变化: {comparison['change']:+.2f}%")

            # 找出低覆盖率文件
            uncovered = self.find_uncovered_code(results)
            if uncovered:
                print(f"\n⚠️  {len(uncovered)} 个文件覆盖率低于 80%:")
                for item in uncovered[:5]:  # 只显示前5个
                    print(f"   {item['file']}: {item['coverage']}%")

            # 保存到历史
            history.append(
                {
                    "timestamp": results.get("timestamp"),
                    "coverage_percentage": results["coverage_percentage"],
                    "covered_lines": results["covered_lines"],
                    "missing_lines": results["missing_lines"],
                }
            )

            # 限制历史记录数
            if len(history) > 100:
                history = history[-100:]

            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2, ensure_ascii=False)

        else:
            print(f"\n❌ 状态: {results['status']}")
            print(f"   消息: {results.get('message', results.get('error', 'N/A'))}")

        print("=" * 60)

        return results


if __name__ == "__main__":
    from datetime import datetime

    project_root = Path(__file__).parent.parent.parent
    monitor = TestCoverageMonitor(project_root)
    results = monitor.run_monitoring()

    # 添加时间戳
    results["timestamp"] = datetime.now().isoformat()

    # 保存详细报告
    output_file = project_root / "monitoring" / "coverage_report.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n详细报告已保存至: {output_file}")
