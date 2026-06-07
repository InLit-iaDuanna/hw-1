"""V13.7 优化实战示例：优化 FSM 相位时长参数。

直接集成 V13.7 仿真，演示完整优化流程。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HW1_ROOT = ROOT.parent
V137_DIR = HW1_ROOT / "v13_7_refactored"

sys.path.insert(0, str(V137_DIR))
sys.path.insert(0, str(HW1_ROOT))

from auto_optimization.constraints.parameter_bounds import (
    Parameter,
    ParameterSpace,
    ParameterType,
)
from auto_optimization.objectives.objective_functions import maximize_distance
from auto_optimization.optimizers import BayesianOptimizer


def create_v137_evaluate_func():
    """创建 V13.7 评估函数。

    Returns:
        评估函数 params -> result
    """
    try:
        # 尝试导入 V13.7 仿真模块
        from simulate_v137_refactored import (
            V137Controller,
            V137Params,
            simulate_with_controller,
        )

        def evaluate_func(params: dict) -> dict:
            """评估 V13.7 FSM 参数。

            Args:
                params: 参数字典，包含 FSM 时长参数

            Returns:
                仿真结果字典
            """
            # 加载默认参数
            base_params = V137Params()

            # 更新 FSM 时长参数
            if "stance_early_duration" in params:
                base_params.fsm.stance_early_duration = params["stance_early_duration"]
            if "stance_late_duration" in params:
                base_params.fsm.stance_late_duration = params["stance_late_duration"]
            if "swing_thrust_duration" in params:
                base_params.fsm.swing_thrust_duration = params["swing_thrust_duration"]
            if "swing_retract_duration" in params:
                base_params.fsm.swing_retract_duration = params["swing_retract_duration"]

            # 运行仿真
            try:
                result = simulate_with_controller(base_params)
                return result
            except Exception as e:
                print(f"仿真失败: {e}")
                return {
                    "success": False,
                    "forward_distance": 0.0,
                    "num_touchdowns": 0,
                }

        return evaluate_func

    except ImportError as e:
        print(f"无法导入 V13.7 仿真模块: {e}")
        print("使用模拟评估函数进行演示...")

        # 返回模拟函数
        import numpy as np

        def dummy_evaluate_func(params: dict) -> dict:
            """模拟评估函数（仅用于演示）。"""
            # 模拟：相位时长在合理范围内表现更好
            stance_early = params.get("stance_early_duration", 0.20)
            stance_late = params.get("stance_late_duration", 0.18)
            swing_thrust = params.get("swing_thrust_duration", 0.12)
            swing_retract = params.get("swing_retract_duration", 0.15)

            # 理想值
            ideal = {
                "stance_early_duration": 0.22,
                "stance_late_duration": 0.16,
                "swing_thrust_duration": 0.10,
                "swing_retract_duration": 0.14,
            }

            # 计算距离（模拟目标函数）
            error = (
                (stance_early - ideal["stance_early_duration"]) ** 2
                + (stance_late - ideal["stance_late_duration"]) ** 2
                + (swing_thrust - ideal["swing_thrust_duration"]) ** 2
                + (swing_retract - ideal["swing_retract_duration"]) ** 2
            )

            distance = 15.0 - 50.0 * error
            distance += np.random.normal(0, 0.2)  # 添加噪声

            return {
                "success": distance > 0,
                "forward_distance": max(0, distance),
                "num_touchdowns": int(max(0, distance / 1.5)),
            }

        return dummy_evaluate_func


def optimize_v137_fsm_timing(budget: int = 50, use_bayesian: bool = True):
    """优化 V13.7 FSM 相位时长。

    Args:
        budget: 评估预算
        use_bayesian: 是否使用贝叶斯优化（否则使用遗传算法）
    """
    print("=" * 60)
    print("V13.7 FSM 相位时长优化")
    print("=" * 60)

    # 定义参数空间
    param_space = ParameterSpace(
        [
            Parameter(
                "stance_early_duration",
                ParameterType.CONTINUOUS,
                (0.10, 0.30),
                default=0.20,
                description="支撑早期相位时长 (s)",
            ),
            Parameter(
                "stance_late_duration",
                ParameterType.CONTINUOUS,
                (0.10, 0.30),
                default=0.18,
                description="支撑晚期相位时长 (s)",
            ),
            Parameter(
                "swing_thrust_duration",
                ParameterType.CONTINUOUS,
                (0.05, 0.20),
                default=0.12,
                description="摆动推进相位时长 (s)",
            ),
            Parameter(
                "swing_retract_duration",
                ParameterType.CONTINUOUS,
                (0.05, 0.20),
                default=0.15,
                description="摆动回收相位时长 (s)",
            ),
        ]
    )

    print("\n参数空间:")
    for name, param in param_space.parameters.items():
        print(f"  {name}: {param.bounds} (默认: {param.default})")

    # 创建评估函数
    print("\n创建评估函数...")
    evaluate_func = create_v137_evaluate_func()

    # 定义目标函数
    objective = maximize_distance()
    print(f"目标函数: {objective.name}")

    # 选择优化器
    if use_bayesian:
        print(f"\n使用贝叶斯优化（预算: {budget} 次评估）")
        try:
            optimizer = BayesianOptimizer(
                param_space=param_space,
                objective=objective,
                evaluate_func=evaluate_func,
                n_initial_points=min(10, budget // 5),
                acq_func="EI",
            )
            result = optimizer.optimize(budget=budget, verbose=True)
        except ImportError:
            print("scikit-optimize 未安装，请运行: pip install scikit-optimize")
            return

    else:
        print(f"\n使用遗传算法（预算: {budget} 次评估）")
        try:
            from auto_optimization.optimizers import GeneticAlgorithm

            population_size = 20
            n_generations = budget // population_size

            optimizer = GeneticAlgorithm(
                param_space=param_space,
                objective=objective,
                evaluate_func=evaluate_func,
                population_size=population_size,
                n_generations=n_generations,
            )
            result = optimizer.optimize(verbose=True)
        except ImportError:
            print("DEAP 未安装，请运行: pip install deap")
            return

    # 打印结果
    print("\n" + "=" * 60)
    print("优化完成！")
    print("=" * 60)
    print("\n最优参数:")
    for key, value in result.best_params.items():
        print(f"  {key}: {value:.6f}")
    print(f"\n最优前进距离: {result.best_value:.6f} m")
    print(f"评估次数: {result.n_evaluations}")

    # 保存结果
    output_dir = ROOT / "results"
    output_dir.mkdir(parents=True, exist_ok=True)
    result_path = output_dir / "v137_fsm_timing_optimized.json"

    if hasattr(optimizer, "save_results"):
        optimizer.save_results(result, result_path)
    else:
        import json

        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "best_params": result.best_params,
                    "best_value": result.best_value,
                    "n_evaluations": result.n_evaluations,
                    "convergence_curve": result.convergence_curve,
                },
                f,
                indent=2,
            )
        print(f"结果已保存到: {result_path}")

    # 绘制收敛曲线
    try:
        import matplotlib.pyplot as plt

        plt.figure(figsize=(10, 6))
        plt.plot(
            range(1, len(result.convergence_curve) + 1),
            result.convergence_curve,
            marker="o",
            markersize=4,
            linewidth=2,
        )
        plt.xlabel("评估次数", fontsize=12)
        plt.ylabel("最优前进距离 (m)", fontsize=12)
        plt.title("V13.7 FSM 时长优化收敛曲线", fontsize=14, fontweight="bold")
        plt.grid(alpha=0.3)

        plot_path = output_dir / "v137_convergence.png"
        plt.savefig(plot_path, dpi=300, bbox_inches="tight")
        print(f"收敛曲线已保存到: {plot_path}")
    except Exception as e:
        print(f"绘图失败: {e}")

    print("=" * 60)

    return result


def main():
    """主函数。"""
    import argparse

    parser = argparse.ArgumentParser(description="V13.7 FSM 时长优化")
    parser.add_argument("--budget", type=int, default=50, help="评估预算")
    parser.add_argument(
        "--optimizer",
        type=str,
        choices=["bayesian", "genetic"],
        default="bayesian",
        help="优化器类型",
    )

    args = parser.parse_args()

    optimize_v137_fsm_timing(
        budget=args.budget, use_bayesian=(args.optimizer == "bayesian")
    )


if __name__ == "__main__":
    main()
