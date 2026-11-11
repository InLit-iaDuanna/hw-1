"""系统健康检查模块。

检查环境配置、依赖包、数据完整性等，并执行 smoke test。
"""

import sys
from pathlib import Path
from typing import Any
import subprocess
import importlib.util


class HealthChecker:
    """系统健康检查器。"""

    def __init__(self, project_root: Path | str | None = None):
        if project_root is None:
            # 尝试从当前文件推导项目根目录
            project_root = Path(__file__).parent.parent
        self.project_root = Path(project_root)
        self.results: list[dict[str, Any]] = []

    def run_all_checks(self, verbose: bool = True) -> dict[str, Any]:
        """运行所有健康检查。

        Returns:
            {
                "passed": bool,
                "total_checks": int,
                "passed_checks": int,
                "failed_checks": int,
                "checks": [check_result, ...]
            }
        """
        self.results = []

        if verbose:
            print("=" * 70)
            print("hw-1 系统健康检查")
            print("=" * 70)
            print()

        # 运行各项检查
        self._check_python_version(verbose)
        self._check_required_packages(verbose)
        self._check_project_structure(verbose)
        self._check_common_library(verbose)
        self._check_data_directories(verbose)

        # 统计结果
        passed_count = sum(1 for r in self.results if r["passed"])
        failed_count = len(self.results) - passed_count

        summary = {
            "passed": failed_count == 0,
            "total_checks": len(self.results),
            "passed_checks": passed_count,
            "failed_checks": failed_count,
            "checks": self.results,
        }

        if verbose:
            print("\n" + "=" * 70)
            print("健康检查摘要")
            print("=" * 70)
            print(f"总检查项: {summary['total_checks']}")
            print(f"✓ 通过: {summary['passed_checks']}")
            print(f"✗ 失败: {summary['failed_checks']}")
            print()

            if summary["passed"]:
                print("✓ 系统健康状态良好")
            else:
                print("✗ 系统存在问题，请修复失败项")

        return summary

    def _check_python_version(self, verbose: bool) -> None:
        """检查 Python 版本。"""
        name = "Python 版本"
        min_version = (3, 10)
        current = sys.version_info[:2]

        passed = current >= min_version

        result = {
            "name": name,
            "passed": passed,
            "details": f"当前版本: {current[0]}.{current[1]}, 最低要求: {min_version[0]}.{min_version[1]}",
            "severity": "critical" if not passed else "none",
        }

        self.results.append(result)

        if verbose:
            status = "✓" if passed else "✗"
            print(f"{status} {name}: {result['details']}")

    def _check_required_packages(self, verbose: bool) -> None:
        """检查必需的 Python 包。"""
        required_packages = [
            ("mujoco", "critical"),
            ("numpy", "critical"),
            ("matplotlib", "high"),
            ("pandas", "high"),
            ("yaml", "medium"),
        ]

        for package_name, severity in required_packages:
            # 特殊处理 yaml (模块名是 yaml，包名是 PyYAML)
            import_name = package_name
            if package_name == "yaml":
                import_name = "yaml"

            spec = importlib.util.find_spec(import_name)
            passed = spec is not None

            result = {
                "name": f"包: {package_name}",
                "passed": passed,
                "details": "已安装" if passed else "未安装",
                "severity": severity if not passed else "none",
            }

            self.results.append(result)

            if verbose:
                status = "✓" if passed else "✗"
                print(f"{status} {result['name']}: {result['details']}")

    def _check_project_structure(self, verbose: bool) -> None:
        """检查项目目录结构。"""
        required_dirs = [
            ("common", "critical"),
            ("diagnostics", "low"),
            ("tests", "medium"),
        ]

        for dir_name, severity in required_dirs:
            dir_path = self.project_root / dir_name
            passed = dir_path.exists() and dir_path.is_dir()

            result = {
                "name": f"目录: {dir_name}/",
                "passed": passed,
                "details": str(dir_path) if passed else f"不存在: {dir_path}",
                "severity": severity if not passed else "none",
            }

            self.results.append(result)

            if verbose:
                status = "✓" if passed else "✗"
                print(f"{status} {result['name']}: {'存在' if passed else '不存在'}")

    def _check_common_library(self, verbose: bool) -> None:
        """检查 common 库模块。"""
        common_modules = [
            "model_loader",
            "simulation_runner",
            "control_utils",
            "data_io",
        ]

        common_path = self.project_root / "common"
        if not common_path.exists():
            # 如果 common 目录不存在，跳过模块检查
            return

        for module_name in common_modules:
            module_file = common_path / f"{module_name}.py"
            passed = module_file.exists()

            result = {
                "name": f"模块: common/{module_name}.py",
                "passed": passed,
                "details": "存在" if passed else "不存在",
                "severity": "medium" if not passed else "none",
            }

            self.results.append(result)

            if verbose:
                status = "✓" if passed else "✗"
                print(f"{status} {result['name']}: {result['details']}")

    def _check_data_directories(self, verbose: bool) -> None:
        """检查数据目录可写性。"""
        test_dirs = [
            self.project_root / "diagnostics",
        ]

        for dir_path in test_dirs:
            if not dir_path.exists():
                continue

            # 尝试写入测试文件
            test_file = dir_path / ".health_check_test"
            try:
                test_file.write_text("test", encoding="utf-8")
                test_file.unlink()
                passed = True
                details = "可写"
            except Exception as e:
                passed = False
                details = f"不可写: {e}"

            result = {
                "name": f"目录可写: {dir_path.name}/",
                "passed": passed,
                "details": details,
                "severity": "medium" if not passed else "none",
            }

            self.results.append(result)

            if verbose:
                status = "✓" if passed else "✗"
                print(f"{status} {result['name']}: {details}")

    def run_smoke_test(
        self,
        model_xml_path: Path | str | None = None,
        duration: float = 1.0,
        verbose: bool = True,
    ) -> dict[str, Any]:
        """运行仿真 smoke test。

        Args:
            model_xml_path: 模型 XML 路径 (可选)
            duration: 仿真时长 (秒)
            verbose: 是否打印详细信息

        Returns:
            {"passed": bool, "details": str, "error": str | None}
        """
        if verbose:
            print("\n" + "=" * 70)
            print("Smoke Test")
            print("=" * 70)

        try:
            import mujoco
            import numpy as np
        except ImportError as e:
            return {"passed": False, "details": "无法导入必需包", "error": str(e)}

        # 如果没有提供模型，创建一个简单的测试模型
        if model_xml_path is None:
            xml_string = """
            <mujoco model="smoke_test">
                <worldbody>
                    <light pos="0 0 3" dir="0 0 -1"/>
                    <geom name="floor" type="plane" size="10 10 0.1" rgba="0.8 0.8 0.8 1"/>
                    <body name="box" pos="0 0 1">
                        <freejoint/>
                        <geom type="box" size="0.1 0.1 0.1" rgba="1 0 0 1"/>
                        <inertial mass="1" pos="0 0 0" diaginertia="0.01 0.01 0.01"/>
                    </body>
                </worldbody>
            </mujoco>
            """
            try:
                model = mujoco.MjModel.from_xml_string(xml_string)
            except Exception as e:
                return {"passed": False, "details": "无法创建测试模型", "error": str(e)}
        else:
            model_path = Path(model_xml_path)
            if not model_path.exists():
                return {
                    "passed": False,
                    "details": f"模型文件不存在: {model_path}",
                    "error": None,
                }

            try:
                model = mujoco.MjModel.from_xml_path(str(model_path))
            except Exception as e:
                return {
                    "passed": False,
                    "details": f"无法加载模型: {model_path}",
                    "error": str(e),
                }

        # 运行仿真
        try:
            data = mujoco.MjData(model)
            dt = model.opt.timestep
            steps = int(duration / dt)

            if verbose:
                print(f"运行仿真: duration={duration}s, dt={dt}, steps={steps}")

            for _ in range(steps):
                mujoco.mj_step(model, data)

                # 检查 NaN
                if np.any(np.isnan(data.qpos)) or np.any(np.isnan(data.qvel)):
                    return {"passed": False, "details": "仿真出现 NaN", "error": None}

            if verbose:
                print(f"✓ 仿真成功完成 {steps} 步")

            return {
                "passed": True,
                "details": f"仿真成功运行 {duration}s",
                "error": None,
            }

        except Exception as e:
            return {"passed": False, "details": "仿真运行时错误", "error": str(e)}

    def export_report(self, output_path: Path | str) -> None:
        """导出健康检查报告为 JSON。"""
        import json

        output_path = Path(output_path)

        summary = {
            "passed": all(r["passed"] for r in self.results),
            "total_checks": len(self.results),
            "passed_checks": sum(1 for r in self.results if r["passed"]),
            "failed_checks": sum(1 for r in self.results if not r["passed"]),
            "checks": self.results,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        print(f"健康检查报告已导出: {output_path}")


def main() -> None:
    """命令行入口。"""
    import argparse

    parser = argparse.ArgumentParser(description="hw-1 系统健康检查")
    parser.add_argument("--project-root", type=str, help="项目根目录路径")
    parser.add_argument("--smoke-test", action="store_true", help="运行 smoke test")
    parser.add_argument("--model", type=str, help="Smoke test 使用的模型 XML 路径")
    parser.add_argument(
        "--duration", type=float, default=1.0, help="Smoke test 仿真时长 (秒)"
    )
    parser.add_argument("--export", type=str, help="导出报告到 JSON 文件")

    args = parser.parse_args()

    checker = HealthChecker(project_root=args.project_root)

    # 运行健康检查
    summary = checker.run_all_checks(verbose=True)

    # 运行 smoke test
    if args.smoke_test:
        smoke_result = checker.run_smoke_test(
            model_xml_path=args.model, duration=args.duration, verbose=True
        )

        if smoke_result["passed"]:
            print("\n✓ Smoke test 通过")
        else:
            print(f"\n✗ Smoke test 失败: {smoke_result['details']}")
            if smoke_result["error"]:
                print(f"   错误: {smoke_result['error']}")

    # 导出报告
    if args.export:
        checker.export_report(args.export)

    # 返回退出码
    sys.exit(0 if summary["passed"] else 1)


if __name__ == "__main__":
    main()
