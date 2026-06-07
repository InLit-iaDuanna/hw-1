"""
性能监控 - 跟踪仿真性能和基准测试结果
"""

import json
import time
from pathlib import Path
from typing import Any


class PerformanceMonitor:
    """性能监控器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def check_benchmark_results(self) -> dict[str, Any]:
        """检查基准测试结果"""
        results = {
            "status": "unknown",
            "benchmarks": [],
            "latest_results": None,
        }

        try:
            benchmarks_dir = self.project_root / "benchmarks"
            if not benchmarks_dir.exists():
                results["status"] = "no_benchmarks"
                results["message"] = "基准测试目录不存在"
                return results

            # 查找基准测试结果文件
            result_files = list(benchmarks_dir.glob("*.json"))
            if not result_files:
                results["status"] = "no_results"
                results["message"] = "未找到基准测试结果"
                return results

            # 读取最新的结果
            latest_file = max(result_files, key=lambda p: p.stat().st_mtime)
            with open(latest_file, encoding="utf-8") as f:
                latest_data = json.load(f)

            results["latest_file"] = latest_file.name
            results["latest_results"] = latest_data
            results["status"] = "success"

        except Exception as e:
            results["status"] = "error"
            results["error"] = str(e)

        return results

    def run_quick_performance_test(self) -> dict[str, Any]:
        """运行快速性能测试"""
        results = {
            "status": "unknown",
            "tests": [],
        }

        try:
            # 测试 1: 导入性能
            start = time.time()
            try:
                import common  # noqa: F401

                import_time = time.time() - start
                results["tests"].append(
                    {
                        "name": "import_time",
                        "value": round(import_time * 1000, 2),
                        "unit": "ms",
                        "status": "pass" if import_time < 1.0 else "slow",
                    }
                )
            except Exception as e:
                results["tests"].append(
                    {
                        "name": "import_time",
                        "status": "error",
                        "error": str(e),
                    }
                )

            # 测试 2: NumPy 性能
            start = time.time()
            try:
                import numpy as np

                # 简单矩阵运算
                a = np.random.rand(1000, 1000)
                b = np.random.rand(1000, 1000)
                _ = np.dot(a, b)
                numpy_time = time.time() - start
                results["tests"].append(
                    {
                        "name": "numpy_matmul_1000x1000",
                        "value": round(numpy_time * 1000, 2),
                        "unit": "ms",
                        "status": "pass" if numpy_time < 0.5 else "slow",
                    }
                )
            except Exception as e:
                results["tests"].append(
                    {
                        "name": "numpy_matmul",
                        "status": "error",
                        "error": str(e),
                    }
                )

            results["status"] = "success"

        except Exception as e:
            results["status"] = "error"
            results["error"] = str(e)

        return results

    def compare_with_baseline(
        self, current: dict[str, Any], baseline: dict[str, Any]
    ) -> dict[str, Any]:
        """与基线性能比较"""
        comparison = {"regressions": [], "improvements": [], "stable": []}

        # 比较测试结果
        current_tests = {t["name"]: t for t in current.get("tests", [])}
        baseline_tests = baseline.get("baseline_performance", {})

        for test_name, baseline_value in baseline_tests.items():
            if test_name in current_tests:
                current_test = current_tests[test_name]
                current_value = current_test.get("value")

                if current_value is not None and isinstance(baseline_value, (int, float)):
                    change_pct = ((current_value - baseline_value) / baseline_value) * 100

                    comparison_item = {
                        "test": test_name,
                        "baseline": baseline_value,
                        "current": current_value,
                        "change_percent": round(change_pct, 2),
                    }

                    if change_pct > 10:  # 性能退化超过10%
                        comparison["regressions"].append(comparison_item)
                    elif change_pct < -10:  # 性能提升超过10%
                        comparison["improvements"].append(comparison_item)
                    else:
                        comparison["stable"].append(comparison_item)

        return comparison

    def run_monitoring(self) -> dict[str, Any]:
        """运行性能监控"""
        print("=" * 60)
        print("性能监控")
        print("=" * 60)

        # 检查基准测试结果
        print("\n1. 基准测试结果:")
        benchmark_results = self.check_benchmark_results()
        print(f"   状态: {benchmark_results['status']}")
        if benchmark_results["status"] == "success":
            print(f"   最新文件: {benchmark_results['latest_file']}")

        # 运行快速性能测试
        print("\n2. 快速性能测试:")
        perf_results = self.run_quick_performance_test()
        if perf_results["status"] == "success":
            for test in perf_results["tests"]:
                if test["status"] == "pass":
                    print(
                        f"   ✓ {test['name']}: {test['value']} {test['unit']}"
                    )
                elif test["status"] == "slow":
                    print(
                        f"   ⚠ {test['name']}: {test['value']} {test['unit']} (慢)"
                    )
                elif test["status"] == "error":
                    print(f"   ✗ {test['name']}: {test.get('error', 'N/A')}")

        # 与基线比较
        print("\n3. 性能趋势:")
        config_file = self.project_root / "monitoring" / "config.yaml"
        if config_file.exists():
            import yaml

            with open(config_file, encoding="utf-8") as f:
                config = yaml.safe_load(f)

            comparison = self.compare_with_baseline(perf_results, config)

            if comparison["regressions"]:
                print(f"   ⚠ {len(comparison['regressions'])} 个性能退化")
                for reg in comparison["regressions"]:
                    print(
                        f"      {reg['test']}: {reg['change_percent']:+.1f}% "
                        f"({reg['baseline']} → {reg['current']})"
                    )
            elif comparison["improvements"]:
                print(f"   ✓ {len(comparison['improvements'])} 个性能提升")
            else:
                print("   ✓ 性能稳定")

        print("=" * 60)

        # 组合所有结果
        all_results = {
            "benchmark_results": benchmark_results,
            "performance_tests": perf_results,
        }

        return all_results


if __name__ == "__main__":
    from datetime import datetime

    project_root = Path(__file__).parent.parent.parent
    monitor = PerformanceMonitor(project_root)
    results = monitor.run_monitoring()

    # 添加时间戳
    results["timestamp"] = datetime.now().isoformat()

    # 保存结果
    output_file = project_root / "monitoring" / "performance_report.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n详细报告已保存至: {output_file}")
