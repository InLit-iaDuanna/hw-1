"""
指标收集器 - hw-1 项目度量数据收集
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


class MetricsCollector:
    """项目度量数据收集器"""

    def __init__(self, project_root: Path, config_path: Path | None = None):
        self.project_root = project_root
        if config_path is None:
            config_path = project_root / "monitoring" / "config.yaml"
        self.config = self._load_config(config_path)
        self.metrics: dict[str, Any] = {}

    def _load_config(self, config_path: Path) -> dict:
        """加载配置文件"""
        if not config_path.exists():
            return {}
        with open(config_path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def collect_code_metrics(self) -> dict[str, Any]:
        """收集代码度量"""
        metrics = {}

        try:
            # Python 版本
            py_version = sys.version_info
            metrics["python_version"] = f"{py_version.major}.{py_version.minor}.{py_version.micro}"

            # 统计代码行数
            common_dir = self.project_root / "common"
            if common_dir.exists():
                py_files = list(common_dir.rglob("*.py"))
                total_lines = 0
                for py_file in py_files:
                    try:
                        with open(py_file, encoding="utf-8") as f:
                            total_lines += len(f.readlines())
                    except Exception:
                        pass
                metrics["lines_of_code"] = total_lines
                metrics["file_count"] = len(py_files)
            else:
                metrics["lines_of_code"] = 0
                metrics["file_count"] = 0

            # 版本目录统计
            version_dirs = [
                d.name for d in self.project_root.glob("v*")
                if d.is_dir() and d.name[1:2].isdigit()
            ]
            metrics["version_directories"] = sorted(version_dirs)
            metrics["version_count"] = len(version_dirs)

            # 依赖版本
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "list", "--format=json"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if result.returncode == 0:
                    packages = json.loads(result.stdout)
                    key_packages = ["mujoco", "numpy", "matplotlib", "pytest"]
                    metrics["dependency_versions"] = {
                        pkg["name"]: pkg["version"]
                        for pkg in packages
                        if pkg["name"] in key_packages
                    }
            except Exception:
                metrics["dependency_versions"] = {}

        except Exception as e:
            metrics["error"] = str(e)

        return metrics

    def collect_test_metrics(self) -> dict[str, Any]:
        """收集测试度量"""
        metrics = {}

        try:
            # 统计测试文件数
            tests_dir = self.project_root / "tests"
            if tests_dir.exists():
                test_files = list(tests_dir.rglob("test_*.py"))
                metrics["test_files_count"] = len(test_files)

                # 统计测试函数数（简单估算）
                test_functions = 0
                for test_file in test_files:
                    try:
                        with open(test_file, encoding="utf-8") as f:
                            content = f.read()
                            test_functions += content.count("def test_")
                    except Exception:
                        pass
                metrics["test_count"] = test_functions
            else:
                metrics["test_files_count"] = 0
                metrics["test_count"] = 0

            # 读取覆盖率数据
            coverage_file = self.project_root / "coverage.json"
            if coverage_file.exists():
                with open(coverage_file, encoding="utf-8") as f:
                    cov_data = json.load(f)
                    totals = cov_data.get("totals", {})
                    metrics["coverage_percentage"] = round(
                        totals.get("percent_covered", 0), 2
                    )
                    metrics["covered_lines"] = totals.get("covered_lines", 0)
                    metrics["missing_lines"] = totals.get("missing_lines", 0)
            else:
                metrics["coverage_percentage"] = None

            # 运行快速测试以获取通过率（仅单元测试）
            try:
                result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "pytest",
                        "tests/unit",
                        "--collect-only",
                        "-q",
                    ],
                    capture_output=True,
                    text=True,
                    cwd=self.project_root,
                    check=False,
                    timeout=30,
                )
                output = result.stdout
                # 解析收集的测试数量
                for line in output.split("\n"):
                    if "test" in line and "selected" in line:
                        parts = line.split()
                        try:
                            metrics["unit_tests_collected"] = int(parts[0])
                        except (ValueError, IndexError):
                            pass
            except Exception:
                pass

        except Exception as e:
            metrics["error"] = str(e)

        return metrics

    def collect_performance_metrics(self) -> dict[str, Any]:
        """收集性能度量"""
        metrics = {}

        try:
            # 检查基准测试结果
            benchmarks_dir = self.project_root / "benchmarks"
            if benchmarks_dir.exists():
                # 查找最新的基准测试结果
                result_files = list(benchmarks_dir.glob("*.json"))
                if result_files:
                    latest_file = max(result_files, key=lambda p: p.stat().st_mtime)
                    with open(latest_file, encoding="utf-8") as f:
                        bench_data = json.load(f)
                        metrics["latest_benchmark_file"] = latest_file.name
                        metrics["benchmark_data"] = bench_data

            # 检查性能分析结果
            profiling_dir = self.project_root / "profiling_results"
            if profiling_dir.exists():
                prof_files = list(profiling_dir.glob("*.json"))
                metrics["profiling_results_count"] = len(prof_files)

        except Exception as e:
            metrics["error"] = str(e)

        return metrics

    def collect_storage_metrics(self) -> dict[str, Any]:
        """收集存储度量"""
        metrics = {}

        def get_dir_size(directory: Path) -> int:
            """计算目录大小（字节）"""
            total = 0
            try:
                for item in directory.rglob("*"):
                    if item.is_file():
                        total += item.stat().st_size
            except Exception:
                pass
            return total

        def format_size(size_bytes: int) -> str:
            """格式化文件大小"""
            for unit in ["B", "KB", "MB", "GB"]:
                if size_bytes < 1024:
                    return f"{size_bytes:.2f} {unit}"
                size_bytes /= 1024
            return f"{size_bytes:.2f} TB"

        try:
            # 输出目录大小
            out_dir = self.project_root / "out"
            if out_dir.exists():
                size = get_dir_size(out_dir)
                metrics["output_directory_size_bytes"] = size
                metrics["output_directory_size"] = format_size(size)

            # 缓存目录大小
            cache_dirs = [
                ".pytest_cache",
                ".mypy_cache",
                ".ruff_cache",
                "__pycache__",
            ]
            total_cache = 0
            for cache_dir in cache_dirs:
                cache_path = self.project_root / cache_dir
                if cache_path.exists():
                    total_cache += get_dir_size(cache_path)
            metrics["cache_directory_size_bytes"] = total_cache
            metrics["cache_directory_size"] = format_size(total_cache)

            # htmlcov 目录
            htmlcov_dir = self.project_root / "htmlcov"
            if htmlcov_dir.exists():
                size = get_dir_size(htmlcov_dir)
                metrics["htmlcov_size_bytes"] = size
                metrics["htmlcov_size"] = format_size(size)

        except Exception as e:
            metrics["error"] = str(e)

        return metrics

    def collect_all_metrics(self) -> dict[str, Any]:
        """收集所有度量"""
        print("=" * 60)
        print("hw-1 项目指标收集")
        print("=" * 60)
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        all_metrics = {
            "timestamp": datetime.now().isoformat(),
            "code": self.collect_code_metrics(),
            "testing": self.collect_test_metrics(),
            "performance": self.collect_performance_metrics(),
            "storage": self.collect_storage_metrics(),
        }

        # 打印摘要
        print("代码度量:")
        for key, value in all_metrics["code"].items():
            if key != "version_directories" and key != "dependency_versions":
                print(f"  {key}: {value}")
        print()

        print("测试度量:")
        for key, value in all_metrics["testing"].items():
            print(f"  {key}: {value}")
        print()

        print("存储度量:")
        for key, value in all_metrics["storage"].items():
            if not key.endswith("_bytes"):
                print(f"  {key}: {value}")
        print()

        print("=" * 60)

        return all_metrics

    def save_metrics(self, metrics: dict[str, Any]):
        """保存度量数据"""
        # 保存当前度量
        output_file = self.project_root / "monitoring" / "metrics_latest.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)
        print(f"指标已保存至: {output_file}")

        # 追加到历史记录
        history_file = self.project_root / "monitoring" / "metrics_history.json"
        history = []
        if history_file.exists():
            try:
                with open(history_file, encoding="utf-8") as f:
                    history = json.load(f)
            except Exception:
                history = []

        history.append(metrics)

        # 限制历史记录数量
        max_records = self.config.get("history", {}).get("max_records", 1000)
        if len(history) > max_records:
            history = history[-max_records:]

        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
        print(f"历史记录已更新: {history_file} ({len(history)} 条记录)")


if __name__ == "__main__":
    # 获取项目根目录
    project_root = Path(__file__).parent.parent

    # 创建收集器并运行
    collector = MetricsCollector(project_root)
    metrics = collector.collect_all_metrics()
    collector.save_metrics(metrics)
