"""诊断系统演示脚本。

展示如何使用诊断系统的各项功能。
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from diagnostics import ErrorDetector, SolutionDatabase, HealthChecker


def demo_error_detection():
    """演示错误检测功能。"""
    print("=" * 70)
    print("演示 1: 自动错误检测")
    print("=" * 70)

    detector = ErrorDetector()

    # 模拟仿真失败结果
    simulation_result = {
        "success": False,
        "failure": "fall_down",
        "forward": 0.8,
        "alternation_count": 2,
        "hip_height": 0.42,
        "duration": 1.5,
    }

    print("\n仿真结果:")
    for key, value in simulation_result.items():
        print(f"  {key}: {value}")

    # 检测错误
    errors = detector.detect_from_data(simulation_result)

    print(f"\n检测到 {len(errors)} 个错误:")
    for error_type, severity in errors:
        print(f"  - {error_type} (严重性: {severity})")


def demo_solution_lookup():
    """演示解决方案查询。"""
    print("\n" + "=" * 70)
    print("演示 2: 解决方案查询")
    print("=" * 70)

    db = SolutionDatabase()

    # 查询 fall_down 错误
    error_type = "fall_down"
    entry = db.get(error_type)

    if entry:
        print(f"\n错误类型: {error_type}")
        print(f"严重性: {entry.severity}")

        print("\n可能原因:")
        for i, cause in enumerate(entry.causes[:3], 1):
            print(f"  {i}. {cause}")

        print("\n推荐解决方案:")
        for i, solution in enumerate(entry.solutions[:3], 1):
            print(f"\n  方案 {i}: {solution.action}")
            print(f"  详情: {solution.details}")
            if solution.code:
                print(f"  代码示例: {solution.code}")


def demo_search():
    """演示知识库搜索。"""
    print("\n" + "=" * 70)
    print("演示 3: 搜索知识库")
    print("=" * 70)

    db = SolutionDatabase()

    # 搜索关键词
    keyword = "motor"
    results = db.search(keyword)

    print(f"\n搜索 '{keyword}' 找到 {len(results)} 个相关错误:")
    for entry in results:
        print(f"\n  错误: {entry.error_type}")
        print(f"  严重性: {entry.severity}")
        print(f"  症状数: {len(entry.symptoms)}")
        print(f"  解决方案数: {len(entry.solutions)}")


def demo_health_check():
    """演示系统健康检查。"""
    print("\n" + "=" * 70)
    print("演示 4: 系统健康检查")
    print("=" * 70)

    checker = HealthChecker(project_root=project_root)

    # 运行健康检查
    print("\n正在运行系统健康检查...")
    summary = checker.run_all_checks(verbose=False)

    print(f"\n检查结果:")
    print(f"  总检查项: {summary['total_checks']}")
    print(f"  通过: {summary['passed_checks']}")
    print(f"  失败: {summary['failed_checks']}")

    if summary["failed_checks"] > 0:
        print("\n失败的检查项:")
        for check in summary["checks"]:
            if not check["passed"]:
                print(f"  - {check['name']}: {check['details']}")

    # 运行 smoke test
    print("\n正在运行 Smoke Test...")
    smoke_result = checker.run_smoke_test(duration=0.5, verbose=False)

    if smoke_result["passed"]:
        print(f"  [PASS] {smoke_result['details']}")
    else:
        print(f"  [FAIL] {smoke_result['details']}")


def demo_integrated_workflow():
    """演示完整诊断工作流。"""
    print("\n" + "=" * 70)
    print("演示 5: 完整诊断工作流")
    print("=" * 70)

    detector = ErrorDetector()
    db = SolutionDatabase()

    # 模拟一个复杂的失败场景
    simulation_result = {
        "success": False,
        "failure": "nan_or_unstable",
        "has_nan": True,
        "forward": 0.0,
        "duration": 0.3,
        "last_valid_time": 0.28,
    }

    print("\n场景: 仿真在 0.28 秒时出现 NaN")
    print("\n1. 检测错误...")
    report = detector.analyze_simulation_result(simulation_result)

    if report["has_errors"]:
        print(f"   检测到: {report['primary_error']} (严重性: {report['severity']})")

        # 2. 获取解决方案
        print("\n2. 查询解决方案...")
        entry = db.get(report["primary_error"])

        if entry:
            print(f"   找到 {len(entry.solutions)} 个解决方案")

            # 3. 显示最优方案
            print("\n3. 推荐方案 (按优先级):")
            for i, solution in enumerate(entry.solutions[:2], 1):
                print(f"\n   方案 {i}: {solution.action}")
                print(f"   {solution.details}")

            # 4. 参考资料
            if entry.references:
                print("\n4. 参考资料:")
                for ref in entry.references:
                    print(f"   - {ref}")


def main():
    """运行所有演示。"""
    print("\nhw-1 诊断系统功能演示\n")

    demo_error_detection()
    demo_solution_lookup()
    demo_search()
    demo_health_check()
    demo_integrated_workflow()

    print("\n" + "=" * 70)
    print("演示完成")
    print("=" * 70)
    print("\n使用方式:")
    print("  1. 交互式诊断: python -m diagnostics.diagnostic_wizard")
    print("  2. 健康检查: python -m diagnostics.health_checker --smoke-test")
    print("  3. Python API: 参见 diagnostics/README.md")
    print()


if __name__ == "__main__":
    main()
