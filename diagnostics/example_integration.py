"""示例: 将诊断系统集成到仿真脚本中。

此示例展示如何在仿真失败时自动调用诊断系统并提供解决建议。
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from diagnostics import ErrorDetector, SolutionDatabase


def run_simulation_with_diagnostics(config: dict) -> dict:
    """运行仿真并自动诊断失败原因。

    Args:
        config: 仿真配置参数

    Returns:
        包含诊断信息的结果字典
    """
    print("=" * 70)
    print("运行仿真 (集成诊断系统)")
    print("=" * 70)

    # ========== 模拟仿真运行 ==========
    # 在实际使用中，这里应该是真实的 MuJoCo 仿真代码
    print("\n1. 初始化仿真...")
    print(f"   配置: dt={config['dt']}, duration={config['duration']}")

    print("\n2. 运行仿真...")
    # 模拟一个失败的仿真结果
    simulation_result = {
        "success": False,
        "failure": "fall_down",
        "forward": 1.2,
        "alternation_count": 3,
        "hip_height": 0.42,
        "duration": 2.5,
        "last_valid_time": 2.3,
        "config": config
    }

    print(f"   仿真在 {simulation_result['last_valid_time']} 秒时失败")
    print(f"   失败类型: {simulation_result['failure']}")

    # ========== 自动诊断 ==========
    if not simulation_result["success"]:
        print("\n" + "=" * 70)
        print("3. 自动诊断失败原因")
        print("=" * 70)

        detector = ErrorDetector()
        db = SolutionDatabase()

        # 检测错误
        report = detector.analyze_simulation_result(simulation_result)

        if report["has_errors"]:
            print(f"\n检测到 {report['error_count']} 个错误:")
            for error_info in report["errors"]:
                print(f"  - {error_info['type']} (严重性: {error_info['severity']})")

            # 获取主要错误的解决方案
            primary_error = report["primary_error"]
            entry = db.get(primary_error)

            if entry:
                print(f"\n主要错误: {primary_error}")
                print(f"严重性: {entry.severity}")

                # 显示可能原因
                print("\n可能原因:")
                for i, cause in enumerate(entry.causes[:3], 1):
                    print(f"  {i}. {cause}")

                # 显示推荐解决方案
                print(f"\n推荐解决方案 (共 {len(entry.solutions)} 个):")
                for i, solution in enumerate(entry.solutions[:3], 1):
                    print(f"\n  方案 {i}: {solution.action}")
                    print(f"  详情: {solution.details}")
                    if solution.code:
                        print(f"  代码示例:")
                        for line in solution.code.split("\n"):
                            print(f"    {line}")

                # 显示参考资料
                if entry.references:
                    print("\n参考资料:")
                    for ref in entry.references:
                        print(f"  - {ref}")

                # 将诊断信息添加到结果中
                simulation_result["diagnosis"] = {
                    "errors": report["errors"],
                    "primary_error": primary_error,
                    "recommended_solutions": [
                        {
                            "action": sol.action,
                            "details": sol.details,
                            "code": sol.code
                        }
                        for sol in entry.solutions[:3]
                    ]
                }

        else:
            print("\n未检测到已知错误模式。")
            print("建议:")
            print("  1. 检查日志文件获取更多信息")
            print("  2. 使用交互式诊断向导: python -m diagnostics.diagnostic_wizard")

    return simulation_result


def suggest_next_steps(result: dict) -> None:
    """根据诊断结果建议下一步操作。"""
    print("\n" + "=" * 70)
    print("4. 建议的下一步操作")
    print("=" * 70)

    if "diagnosis" in result:
        primary_error = result["diagnosis"]["primary_error"]

        # 根据不同错误类型给出具体建议
        if primary_error == "simulation_nan":
            print("\n立即尝试:")
            print("  1. 将 dt 从 0.002 减小到 0.001")
            print("  2. 检查初始 hip_height 是否 >= 0.8 m")
            print("  3. 如仍失败，提高地面接触刚度")

        elif primary_error == "fall_down":
            print("\n立即尝试:")
            print("  1. 提高 stance_late_tau_max 到 4.0 N·m")
            print("  2. 检查 FSM 相位切换时序")
            print("  3. 如使用电机模型，应用 V13.7 摩擦补偿")
            print("  4. 如使用摆臂，减重至 0.01 kg (V14c)")

        elif primary_error == "motor_friction_failure_band":
            print("\n立即尝试:")
            print("  1. 应用前馈摩擦补偿 (V13.7)")
            print("  2. 或选择低摩擦电机 (tau_C < 0.013 N·m)")

        else:
            print("\n参考推荐的解决方案按优先级尝试")

        print("\n如需更多帮助:")
        print("  - 运行交互式诊断: python -m diagnostics.diagnostic_wizard")
        print("  - 搜索知识库: 在 Python 中使用 db.search('关键词')")
        print("  - 查阅文档: diagnostics/README.md")


def main():
    """主函数。"""
    print("\n示例: 集成诊断系统到仿真脚本\n")

    # 仿真配置
    config = {
        "dt": 0.002,
        "duration": 5.0,
        "model_path": "models/biped.xml"
    }

    # 运行仿真并诊断
    result = run_simulation_with_diagnostics(config)

    # 建议下一步操作
    suggest_next_steps(result)

    print("\n" + "=" * 70)
    print("示例完成")
    print("=" * 70)
    print("\n在实际仿真脚本中:")
    print("  1. 将 run_simulation_with_diagnostics() 的模拟部分替换为真实仿真代码")
    print("  2. 在失败时自动获得诊断建议")
    print("  3. 根据建议快速调整参数")
    print()


if __name__ == "__main__":
    main()
