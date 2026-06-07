"""
代码质量监控 - 使用 ruff 和 mypy 检查代码质量
"""

import subprocess
import sys
from pathlib import Path
from typing import Any


class CodeQualityMonitor:
    """代码质量监控器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def check_ruff(self) -> dict[str, Any]:
        """运行 Ruff 代码检查"""
        results = {
            "tool": "ruff",
            "status": "unknown",
            "violations": [],
            "total_violations": 0,
        }

        try:
            # 运行 ruff check
            result = subprocess.run(
                [sys.executable, "-m", "ruff", "check", "common", "--output-format=json"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                check=False,
            )

            if result.stdout:
                import json
                violations = json.loads(result.stdout)
                results["violations"] = violations
                results["total_violations"] = len(violations)
                results["status"] = "pass" if len(violations) == 0 else "fail"
            else:
                results["status"] = "pass"
                results["total_violations"] = 0

            # 统计违规类型
            violation_types: dict[str, int] = {}
            for violation in results["violations"]:
                code = violation.get("code", "unknown")
                violation_types[code] = violation_types.get(code, 0) + 1
            results["violation_types"] = violation_types

        except Exception as e:
            results["status"] = "error"
            results["error"] = str(e)

        return results

    def check_mypy(self) -> dict[str, Any]:
        """运行 mypy 类型检查"""
        results = {
            "tool": "mypy",
            "status": "unknown",
            "errors": 0,
            "notes": 0,
        }

        try:
            # 运行 mypy
            result = subprocess.run(
                [sys.executable, "-m", "mypy", "common"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                check=False,
            )

            output = result.stdout + result.stderr
            results["output"] = output

            # 解析输出
            lines = output.split("\n")
            for line in lines:
                if "error:" in line:
                    results["errors"] += 1
                elif "note:" in line:
                    results["notes"] += 1

            results["status"] = "pass" if results["errors"] == 0 else "fail"

        except FileNotFoundError:
            results["status"] = "skipped"
            results["message"] = "mypy 未安装"
        except Exception as e:
            results["status"] = "error"
            results["error"] = str(e)

        return results

    def check_formatting(self) -> dict[str, Any]:
        """检查代码格式"""
        results = {
            "tool": "ruff format",
            "status": "unknown",
            "files_need_formatting": [],
        }

        try:
            # 运行 ruff format --check
            result = subprocess.run(
                [sys.executable, "-m", "ruff", "format", "--check", "common"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                check=False,
            )

            if result.returncode == 0:
                results["status"] = "pass"
                results["message"] = "所有文件格式正确"
            else:
                results["status"] = "fail"
                # 解析需要格式化的文件
                for line in result.stdout.split("\n"):
                    if "Would reformat:" in line:
                        file_path = line.split("Would reformat:")[1].strip()
                        results["files_need_formatting"].append(file_path)
                results["message"] = f"{len(results['files_need_formatting'])} 个文件需要格式化"

        except Exception as e:
            results["status"] = "error"
            results["error"] = str(e)

        return results

    def run_all_checks(self) -> dict[str, Any]:
        """运行所有代码质量检查"""
        print("=" * 60)
        print("代码质量监控")
        print("=" * 60)

        all_results = {
            "ruff": self.check_ruff(),
            "mypy": self.check_mypy(),
            "formatting": self.check_formatting(),
        }

        # 打印结果
        print("\n1. Ruff 代码检查:")
        ruff_results = all_results["ruff"]
        print(f"   状态: {ruff_results['status']}")
        print(f"   违规数: {ruff_results['total_violations']}")
        if ruff_results.get("violation_types"):
            print("   违规类型分布:")
            for code, count in sorted(
                ruff_results["violation_types"].items(), key=lambda x: x[1], reverse=True
            )[:5]:
                print(f"     {code}: {count}")

        print("\n2. Mypy 类型检查:")
        mypy_results = all_results["mypy"]
        print(f"   状态: {mypy_results['status']}")
        if mypy_results["status"] != "skipped":
            print(f"   错误数: {mypy_results['errors']}")
            print(f"   提示数: {mypy_results['notes']}")

        print("\n3. 代码格式检查:")
        format_results = all_results["formatting"]
        print(f"   状态: {format_results['status']}")
        print(f"   消息: {format_results.get('message', 'N/A')}")

        # 总体评估
        passed = sum(
            1 for r in all_results.values() if r.get("status") in ["pass", "skipped"]
        )
        total = len(all_results)
        print("\n" + "=" * 60)
        print(f"总结: {passed}/{total} 检查通过")
        print("=" * 60)

        return all_results


if __name__ == "__main__":
    project_root = Path(__file__).parent.parent.parent
    monitor = CodeQualityMonitor(project_root)
    results = monitor.run_all_checks()

    # 保存结果
    import json
    output_file = project_root / "monitoring" / "code_quality_report.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n详细报告已保存至: {output_file}")
