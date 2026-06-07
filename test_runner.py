"""测试运行器脚本（PowerShell 兼容）。

用法：
    python test_runner.py              # 运行所有测试
    python test_runner.py unit         # 仅运行单元测试
    python test_runner.py regression   # 仅运行回归测试
    python test_runner.py --coverage   # 生成覆盖率报告
    python test_runner.py --quick      # 快速测试（跳过慢速测试）
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="hw-1 测试运行器")
    parser.add_argument(
        "suite",
        nargs="?",
        choices=["all", "unit", "regression", "integration"],
        default="all",
        help="测试套件选择",
    )
    parser.add_argument("--coverage", action="store_true", help="生成覆盖率报告")
    parser.add_argument("--quick", action="store_true", help="跳过慢速测试")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    parser.add_argument("--failfast", "-x", action="store_true", help="首次失败后停止")
    parser.add_argument(
        "--last-failed", "--lf", action="store_true", help="仅重新运行上次失败的测试"
    )

    args = parser.parse_args()

    # 构建 pytest 命令
    cmd = [sys.executable, "-m", "pytest"]

    # 测试路径
    project_root = Path(__file__).parent
    if args.suite == "unit":
        cmd.append(str(project_root / "tests" / "unit"))
    elif args.suite == "regression":
        cmd.append(str(project_root / "tests" / "regression"))
    elif args.suite == "integration":
        cmd.append(str(project_root / "tests" / "integration"))
    else:
        cmd.append(str(project_root / "tests"))

    # 标记过滤
    if args.quick:
        cmd.extend(["-m", "not slow"])

    # 覆盖率
    if args.coverage:
        cmd.extend(
            [
                "--cov=common",
                "--cov-report=term-missing",
                "--cov-report=html",
            ]
        )

    # 其他选项
    if args.verbose:
        cmd.append("-vv")
    if args.failfast:
        cmd.append("-x")
    if args.last_failed:
        cmd.append("--lf")

    # 运行测试
    print(f"运行命令: {' '.join(cmd)}")
    print("-" * 70)

    result = subprocess.run(cmd, cwd=project_root)

    # 报告结果
    if result.returncode == 0:
        print("\n" + "=" * 70)
        print("✓ 所有测试通过")
        if args.coverage:
            print(
                f"✓ 覆盖率报告生成于: {project_root / 'tests' / 'htmlcov' / 'index.html'}"
            )
        print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print("✗ 测试失败")
        print("=" * 70)
        sys.exit(1)


if __name__ == "__main__":
    main()
