"""批量测试运行器 - 运行所有测试并生成报告。

使用方法:
    python run_all_tests.py                    # 运行所有测试
    python run_all_tests.py --unit             # 仅运行单元测试
    python run_all_tests.py --integration      # 仅运行集成测试
    python run_all_tests.py --regression       # 仅运行回归测试
    python run_all_tests.py --coverage         # 生成覆盖率报告
    python run_all_tests.py --verbose          # 详细输出
    python run_all_tests.py --fast             # 快速模式（跳过慢速测试）
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pytest

HW1_ROOT = Path(__file__).resolve().parent


def print_banner(text: str) -> None:
    """打印测试横幅。"""
    width = 70
    print("\n" + "=" * width)
    print(f"{text:^{width}}")
    print("=" * width + "\n")


def run_test_suite(
    name: str,
    path: Path,
    pytest_args: list[str],
    markers: str | None = None,
) -> tuple[int, float]:
    """运行测试套件并返回结果。

    Args:
        name: 套件名称
        path: 测试路径
        pytest_args: pytest 参数
        markers: pytest marker 表达式

    Returns:
        (exit_code, duration) 元组
    """
    print_banner(f"运行 {name}")

    args = [str(path)] + pytest_args

    if markers:
        args.extend(["-m", markers])

    start_time = time.time()
    exit_code = pytest.main(args)
    duration = time.time() - start_time

    status = "✓ 通过" if exit_code == 0 else "✗ 失败"
    print(f"\n{name}: {status} ({duration:.2f}s)\n")

    return exit_code, duration


def main() -> int:
    """主函数。"""
    parser = argparse.ArgumentParser(description="运行 hw-1 项目测试套件")
    parser.add_argument("--unit", action="store_true", help="仅运行单元测试")
    parser.add_argument("--integration", action="store_true", help="仅运行集成测试")
    parser.add_argument("--regression", action="store_true", help="仅运行回归测试")
    parser.add_argument("--coverage", action="store_true", help="生成覆盖率报告")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    parser.add_argument("--fast", action="store_true", help="快速模式（跳过慢速测试）")
    parser.add_argument("--failfast", "-x", action="store_true", help="首次失败时停止")
    parser.add_argument("--markers", type=str, help="pytest marker 表达式")
    parser.add_argument("--test", "-k", type=str, help="仅运行匹配的测试")

    args = parser.parse_args()

    # 构建 pytest 参数
    pytest_args = []

    if args.verbose:
        pytest_args.append("-v")
    else:
        pytest_args.append("-q")

    if args.failfast:
        pytest_args.append("-x")

    if args.test:
        pytest_args.extend(["-k", args.test])

    if args.fast:
        pytest_args.extend(["-m", "not slow"])

    if args.coverage:
        pytest_args.extend(
            [
                "--cov=common",
                "--cov-report=html",
                "--cov-report=term",
            ]
        )

    # 确定运行哪些测试套件
    run_unit = args.unit or not (args.integration or args.regression)
    run_integration = args.integration or not (args.unit or args.regression)
    run_regression = args.regression or not (args.unit or args.integration)

    # 如果指定了特定类型，只运行该类型
    if args.unit or args.integration or args.regression:
        run_unit = args.unit
        run_integration = args.integration
        run_regression = args.regression

    results = []
    total_duration = 0.0

    print_banner("hw-1 测试套件")
    print(f"测试根目录: {HW1_ROOT}")
    print(f"Python: {sys.version.split()[0]}")
    print(f"pytest 参数: {' '.join(pytest_args)}")

    # 运行单元测试
    if run_unit:
        unit_path = HW1_ROOT / "tests" / "unit"
        if unit_path.exists():
            exit_code, duration = run_test_suite(
                "单元测试 (Unit Tests)",
                unit_path,
                pytest_args,
                args.markers,
            )
            results.append(("单元测试", exit_code, duration))
            total_duration += duration
        else:
            print(f"⚠ 单元测试目录不存在: {unit_path}")

    # 运行集成测试
    if run_integration:
        integration_path = HW1_ROOT / "tests" / "integration"
        if integration_path.exists():
            exit_code, duration = run_test_suite(
                "集成测试 (Integration Tests)",
                integration_path,
                pytest_args,
                args.markers,
            )
            results.append(("集成测试", exit_code, duration))
            total_duration += duration
        else:
            print(f"⚠ 集成测试目录不存在: {integration_path}")

    # 运行回归测试
    if run_regression:
        regression_path = HW1_ROOT / "tests" / "regression"
        if regression_path.exists():
            exit_code, duration = run_test_suite(
                "回归测试 (Regression Tests)",
                regression_path,
                pytest_args,
                args.markers,
            )
            results.append(("回归测试", exit_code, duration))
            total_duration += duration
        else:
            print(f"⚠ 回归测试目录不存在: {regression_path}")

    # 打印总结
    print_banner("测试总结")

    all_passed = all(exit_code == 0 for _, exit_code, _ in results)

    for name, exit_code, duration in results:
        status = "✓ 通过" if exit_code == 0 else "✗ 失败"
        print(f"  {name:30s} {status:10s} ({duration:.2f}s)")

    print(f"\n总耗时: {total_duration:.2f}s")

    if all_passed:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print("\n❌ 部分测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
