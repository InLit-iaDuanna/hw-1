"""测试诊断系统功能。"""

import os
import sys
from pathlib import Path

# 设置控制台编码为 UTF-8
if sys.platform == "win32":
    os.system("chcp 65001 > nul")

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from diagnostics import (
    ErrorDetector,
    HealthChecker,
    SolutionDatabase,
)


def test_error_detector():
    """测试错误检测器。"""
    print("=" * 70)
    print("测试 1: 错误检测器")
    print("=" * 70)

    detector = ErrorDetector()

    # 测试 1: 从数据检测 fall_down
    test_data_1 = {
        "success": False,
        "failure": "fall_down",
        "hip_height": 0.3,
        "forward": 0.5,
        "alternation_count": 2,
    }

    errors = detector.detect_from_data(test_data_1)
    print(f"\n测试数据 1 (fall_down): 检测到 {len(errors)} 个错误")
    for error_type, severity in errors:
        print(f"  [OK] {error_type} (严重性: {severity})")

    assert len(errors) > 0, "应该检测到 fall_down 错误"
    assert any(e[0] == "fall_down" for e in errors), "应包含 fall_down"

    # 测试 2: 从数据检测 NaN
    test_data_2 = {"success": False, "failure": "nan_or_unstable", "has_nan": True}

    errors = detector.detect_from_data(test_data_2)
    print(f"\n测试数据 2 (NaN): 检测到 {len(errors)} 个错误")
    for error_type, severity in errors:
        print(f"  [OK] {error_type} (严重性: {severity})")

    assert any(e[0] == "simulation_nan" for e in errors), "应包含 simulation_nan"

    # 测试 3: 时间序列检测
    import numpy as np

    qpos_with_nan = np.array([0.0, 0.5, 1.0, np.nan, 0.8])
    errors = detector.detect_from_timeseries(qpos=qpos_with_nan)
    print(f"\n测试数据 3 (时间序列 NaN): 检测到 {len(errors)} 个错误")
    for error_type, severity in errors:
        print(f"  [OK] {error_type} (严重性: {severity})")

    assert len(errors) > 0, "应检测到时间序列 NaN"

    print("\n[PASS] 错误检测器测试通过")


def test_solution_database():
    """测试解决方案知识库。"""
    print("\n" + "=" * 70)
    print("测试 2: 解决方案知识库")
    print("=" * 70)

    db = SolutionDatabase()

    # 测试 1: 加载知识库
    print(f"\n[OK] 加载了 {len(db.entries)} 个错误条目")
    print(f"[OK] 类别: {', '.join(db.list_categories())}")

    assert len(db.entries) >= 10, "应至少有 10 个错误条目"

    # 测试 2: 获取特定错误
    entry = db.get("simulation_nan")
    assert entry is not None, "应找到 simulation_nan 条目"
    print(f"\n[OK] 找到错误条目: {entry.error_type}")
    print(f"  - 症状数: {len(entry.symptoms)}")
    print(f"  - 原因数: {len(entry.causes)}")
    print(f"  - 解决方案数: {len(entry.solutions)}")

    assert len(entry.solutions) > 0, "应至少有 1 个解决方案"

    # 测试 3: 搜索功能
    results = db.search("fall")
    print(f"\n[OK] 搜索 'fall' 找到 {len(results)} 个结果:")
    for entry in results:
        print(f"  - {entry.error_type} (严重性: {entry.severity})")

    assert len(results) > 0, "应找到包含 'fall' 的错误"

    # 测试 4: 推荐解决方案
    recommendations = db.recommend_solutions(
        ["simulation_nan", "fall_down"], max_solutions_per_error=2
    )
    print("\n[OK] 为 2 个错误推荐解决方案:")
    for error_type, solutions in recommendations.items():
        print(f"  [{error_type}]: {len(solutions)} 个方案")
        for sol in solutions:
            print(f"    - {sol.action}")

    print("\n[PASS] 解决方案知识库测试通过")


def test_health_checker():
    """测试系统健康检查。"""
    print("\n" + "=" * 70)
    print("测试 3: 系统健康检查")
    print("=" * 70)

    checker = HealthChecker(project_root=project_root)

    # 运行健康检查
    summary = checker.run_all_checks(verbose=False)

    print(f"\n[OK] 总检查项: {summary['total_checks']}")
    print(f"[OK] 通过: {summary['passed_checks']}")
    print(f"[WARN] 失败: {summary['failed_checks']}")

    # 显示失败项
    if summary["failed_checks"] > 0:
        print("\n失败的检查项:")
        for check in summary["checks"]:
            if not check["passed"]:
                print(f"  [FAIL] {check['name']}: {check['details']}")

    # 运行 smoke test
    print("\n运行 Smoke Test...")
    smoke_result = checker.run_smoke_test(duration=0.5, verbose=False)

    if smoke_result["passed"]:
        print(f"[PASS] Smoke test 通过: {smoke_result['details']}")
    else:
        print(f"[FAIL] Smoke test 失败: {smoke_result['details']}")
        if smoke_result["error"]:
            print(f"  错误: {smoke_result['error']}")

    print("\n[PASS] 系统健康检查测试完成")


def test_integration():
    """测试集成功能。"""
    print("\n" + "=" * 70)
    print("测试 4: 集成测试")
    print("=" * 70)

    detector = ErrorDetector()
    db = SolutionDatabase()

    # 模拟一个仿真失败场景
    simulation_result = {
        "success": False,
        "failure": "fall_down",
        "forward": 1.2,
        "alternation_count": 3,
        "hip_height": 0.45,
        "duration": 2.5,
    }

    print("\n仿真结果:")
    print(f"  - success: {simulation_result['success']}")
    print(f"  - failure: {simulation_result['failure']}")
    print(f"  - forward: {simulation_result['forward']} m")
    print(f"  - alternation_count: {simulation_result['alternation_count']}")

    # 分析结果
    report = detector.analyze_simulation_result(simulation_result)

    print("\n诊断报告:")
    print(f"  - 检测到错误: {report['has_errors']}")
    print(f"  - 错误数量: {report['error_count']}")
    print(f"  - 主要错误: {report['primary_error']}")
    print(f"  - 严重性: {report['severity']}")

    # 获取解决方案
    if report["has_errors"]:
        print("\n推荐解决方案:")
        for error_info in report["errors"][:2]:  # 显示前 2 个
            error_type = error_info["type"]
            entry = db.get(error_type)

            if entry:
                print(f"\n  [{error_type}]")
                for i, sol in enumerate(entry.solutions[:2], 1):
                    print(f"    方案 {i}: {sol.action}")
                    print(f"            {sol.details}")

    print("\n[PASS] 集成测试通过")


def main():
    """运行所有测试。"""
    print("\nhw-1 诊断系统测试套件\n")

    try:
        test_error_detector()
        test_solution_database()
        test_health_checker()
        test_integration()

        print("\n" + "=" * 70)
        print("[SUCCESS] 所有测试通过")
        print("=" * 70)

    except AssertionError as e:
        print(f"\n[FAIL] 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] 测试错误: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
