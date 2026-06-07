"""
健康检查器 - hw-1 项目健康状态监控
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


class HealthCheck:
    """单个健康检查项"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.status = "UNKNOWN"  # PASS, FAIL, WARNING, UNKNOWN
        self.message = ""
        self.details = {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "message": self.message,
            "details": self.details,
        }


class HealthMonitor:
    """健康监控器"""

    def __init__(self, project_root: Path, config_path: Path | None = None):
        self.project_root = project_root
        if config_path is None:
            config_path = project_root / "monitoring" / "config.yaml"
        self.config = self._load_config(config_path)
        self.checks: list[HealthCheck] = []

    def _load_config(self, config_path: Path) -> dict:
        """加载配置文件"""
        if not config_path.exists():
            return {}
        with open(config_path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def add_check(self, check: HealthCheck):
        """添加检查项"""
        self.checks.append(check)

    def check_environment(self) -> HealthCheck:
        """检查环境健康"""
        check = HealthCheck("environment", "Python 环境和依赖检查")

        try:
            # 检查 Python 版本
            py_version = sys.version_info
            check.details["python_version"] = f"{py_version.major}.{py_version.minor}.{py_version.micro}"

            # 检查关键依赖
            required_packages = ["mujoco", "numpy", "matplotlib", "pytest"]
            installed = {}
            missing = []

            for pkg in required_packages:
                try:
                    result = subprocess.run(
                        [sys.executable, "-m", "pip", "show", pkg],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    if result.returncode == 0:
                        # 解析版本号
                        for line in result.stdout.split("\n"):
                            if line.startswith("Version:"):
                                version = line.split(":")[1].strip()
                                installed[pkg] = version
                                break
                    else:
                        missing.append(pkg)
                except Exception:
                    missing.append(pkg)

            check.details["installed_packages"] = installed
            check.details["missing_packages"] = missing

            if missing:
                check.status = "FAIL"
                check.message = f"缺少依赖包: {', '.join(missing)}"
            else:
                check.status = "PASS"
                check.message = "环境检查通过"

        except Exception as e:
            check.status = "FAIL"
            check.message = f"环境检查失败: {e}"

        return check

    def check_code_health(self) -> HealthCheck:
        """检查代码健康"""
        check = HealthCheck("code_health", "代码语法和导入检查")

        try:
            # 检查关键文件存在性
            critical_files = self.config.get("critical_files", [])
            missing_files = []
            for file_path in critical_files:
                if not (self.project_root / file_path).exists():
                    missing_files.append(file_path)

            check.details["missing_critical_files"] = missing_files

            # 检查关键目录
            critical_dirs = self.config.get("critical_directories", [])
            missing_dirs = []
            for dir_path in critical_dirs:
                if not (self.project_root / dir_path).is_dir():
                    missing_dirs.append(dir_path)

            check.details["missing_critical_directories"] = missing_dirs

            # 运行 ruff 检查
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "ruff", "check", "common", "--statistics"],
                    capture_output=True,
                    text=True,
                    cwd=self.project_root,
                    check=False,
                )
                check.details["ruff_output"] = result.stdout
                violations_count = result.stdout.count("\n") if result.stdout else 0
                check.details["ruff_violations"] = violations_count
            except Exception as e:
                check.details["ruff_error"] = str(e)
                violations_count = 0

            # 综合评估
            if missing_files or missing_dirs:
                check.status = "FAIL"
                check.message = "缺少关键文件或目录"
            elif violations_count > self.config.get("checks", [{}])[3].get("max_violations", 50):
                check.status = "WARNING"
                check.message = f"代码质量问题较多 ({violations_count} 个违规)"
            else:
                check.status = "PASS"
                check.message = "代码检查通过"

        except Exception as e:
            check.status = "FAIL"
            check.message = f"代码检查失败: {e}"

        return check

    def check_test_health(self) -> HealthCheck:
        """检查测试健康"""
        check = HealthCheck("test_health", "测试通过率和覆盖率检查")

        try:
            # 运行测试
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short", "-x"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                check=False,
                timeout=300,
            )

            check.details["test_exit_code"] = result.returncode
            output = result.stdout

            # 解析测试结果
            passed = failed = 0
            for line in output.split("\n"):
                if " passed" in line:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == "passed":
                            try:
                                passed = int(parts[i - 1])
                            except (ValueError, IndexError):
                                pass
                        elif part == "failed":
                            try:
                                failed = int(parts[i - 1])
                            except (ValueError, IndexError):
                                pass

            check.details["tests_passed"] = passed
            check.details["tests_failed"] = failed
            total = passed + failed
            if total > 0:
                pass_rate = (passed / total) * 100
                check.details["test_pass_rate"] = round(pass_rate, 2)
            else:
                check.details["test_pass_rate"] = 0

            # 检查覆盖率
            coverage_file = self.project_root / "coverage.json"
            if coverage_file.exists():
                with open(coverage_file, encoding="utf-8") as f:
                    cov_data = json.load(f)
                    coverage_pct = cov_data.get("totals", {}).get("percent_covered", 0)
                    check.details["coverage_percentage"] = round(coverage_pct, 2)
            else:
                check.details["coverage_percentage"] = None

            # 评估
            threshold = self.config.get("checks", [{}])[2].get("threshold", 95)
            if result.returncode != 0 and failed > 0:
                check.status = "FAIL"
                check.message = f"测试失败 ({failed} 个失败)"
            elif check.details.get("test_pass_rate", 0) < threshold:
                check.status = "WARNING"
                check.message = f"测试通过率低于 {threshold}%"
            else:
                check.status = "PASS"
                check.message = "测试检查通过"

        except subprocess.TimeoutExpired:
            check.status = "FAIL"
            check.message = "测试超时（5分钟）"
        except Exception as e:
            check.status = "FAIL"
            check.message = f"测试检查失败: {e}"

        return check

    def check_data_integrity(self) -> HealthCheck:
        """检查数据完整性"""
        check = HealthCheck("data_integrity", "关键数据文件完整性检查")

        try:
            # 检查重要的输出目录
            out_dir = self.project_root / "out"
            check.details["out_directory_exists"] = out_dir.exists()

            # 检查测试数据
            test_data_files = []
            if (self.project_root / "tests").exists():
                test_data_files = list((self.project_root / "tests").rglob("*.xml"))
            check.details["test_data_files_count"] = len(test_data_files)

            # 检查版本脚本完整性
            version_dirs = [
                d for d in self.project_root.glob("v*") if d.is_dir() and d.name[1:2].isdigit()
            ]
            check.details["version_directories_count"] = len(version_dirs)

            # 简单评估
            if not out_dir.exists():
                check.status = "WARNING"
                check.message = "输出目录不存在（首次运行正常）"
            else:
                check.status = "PASS"
                check.message = "数据完整性检查通过"

        except Exception as e:
            check.status = "FAIL"
            check.message = f"数据完整性检查失败: {e}"

        return check

    def run_all_checks(self) -> dict[str, Any]:
        """运行所有健康检查"""
        print("=" * 60)
        print("hw-1 项目健康检查")
        print("=" * 60)
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"项目路径: {self.project_root}")
        print()

        # 运行各项检查
        self.add_check(self.check_environment())
        self.add_check(self.check_code_health())
        self.add_check(self.check_test_health())
        self.add_check(self.check_data_integrity())

        # 统计结果
        passed = sum(1 for c in self.checks if c.status == "PASS")
        failed = sum(1 for c in self.checks if c.status == "FAIL")
        warnings = sum(1 for c in self.checks if c.status == "WARNING")

        # 打印结果
        for check in self.checks:
            status_symbol = {
                "PASS": "[PASS]",
                "FAIL": "[FAIL]",
                "WARNING": "[WARN]",
                "UNKNOWN": "[????]",
            }
            print(f"{status_symbol.get(check.status, '[????]')} {check.name}: {check.message}")
            if check.details:
                for key, value in check.details.items():
                    if value is not None and value != [] and value != {}:
                        print(f"    {key}: {value}")
            print()

        # 总结
        print("=" * 60)
        print(f"总结: {passed} 通过, {failed} 失败, {warnings} 警告")
        print("=" * 60)

        # 返回结果
        return {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total": len(self.checks),
                "passed": passed,
                "failed": failed,
                "warnings": warnings,
            },
            "checks": [c.to_dict() for c in self.checks],
        }


if __name__ == "__main__":
    # 获取项目根目录
    project_root = Path(__file__).parent.parent

    # 创建监控器并运行检查
    monitor = HealthMonitor(project_root)
    results = monitor.run_all_checks()

    # 保存结果
    output_file = project_root / "monitoring" / "health_report.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n详细报告已保存至: {output_file}")

    # 根据结果设置退出码
    if results["summary"]["failed"] > 0:
        sys.exit(1)
    elif results["summary"]["warnings"] > 0:
        sys.exit(0)  # 警告不影响退出码
    else:
        sys.exit(0)
