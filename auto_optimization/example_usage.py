"""简单示例：演示如何使用优化工具集。

不需要 YAML 配置，直接在代码中定义参数和目标。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HW1_ROOT = ROOT.parent

sys.path.insert(0, str(HW1_ROOT))

from auto_optimization.constraints.parameter_bounds import (
    Parameter,
    ParameterSpace,
    ParameterType,
)
from auto_optimization.objectives.objective_functions import maximize_distance
from auto_optimization.optimizers import BayesianOptimizer, GeneticAlgorithm


def dummy_simulation(params: dict) -> dict:
    """模拟仿真函数（仅用于演示）。

    实际使用时，替换为真实的 MuJoCo 仿真。

    Args:
        params: 参数字典

    Returns:
        仿真结果字典
    """
    import numpy as np

    # 模拟目标函数（带噪声的二次函数）
    x = params["param1"]
    y = params["param2"]

    # 最优点在 (3.0, 2.0) 附近
    distance = 10.0 - (x - 3.0) ** 2 - (y - 2.0) ** 2
    distance += np.random.normal(0, 0.1)  # 添加噪声

    return {
        "success": distance > 0,
        "forward_distance": max(0, distance),
        "num_touchdowns": 10 if distance > 0 else 0,
    }


def example_bayesian_optimization():
    """示例 1：贝叶斯优化。"""
    print("=" * 60)
    print("示例 1：贝叶斯优化")
    print("=" * 60)

    # 定义参数空间
    param_space = ParameterSpace(
        [
            Parameter("param1", ParameterType.CONTINUOUS, (0.0, 5.0), default=2.5),
            Parameter("param2", ParameterType.CONTINUOUS, (0.0, 5.0), default=2.5),
        ]
    )

    # 定义目标函数
    objective = maximize_distance()

    # 创建优化器
    optimizer = BayesianOptimizer(
        param_space=param_space,
        objective=objective,
        evaluate_func=dummy_simulation,
        n_initial_points=5,
    )

    # 运行优化
    result = optimizer.optimize(budget=20, verbose=True)

    # 打印结果
    print("\n最优参数:")
    for key, value in result.best_params.items():
        print(f"  {key}: {value:.4f}")
    print(f"\n最优值: {result.best_value:.4f}")
    print(f"评估次数: {result.n_evaluations}")

    # 保存结果
    output_path = ROOT / "results" / "example_bayesian.json"
    optimizer.save_results(result, output_path)

    return result


def example_genetic_algorithm():
    """示例 2：遗传算法。"""
    print("\n" + "=" * 60)
    print("示例 2：遗传算法")
    print("=" * 60)

    # 定义参数空间
    param_space = ParameterSpace(
        [
            Parameter("param1", ParameterType.CONTINUOUS, (0.0, 5.0)),
            Parameter("param2", ParameterType.CONTINUOUS, (0.0, 5.0)),
        ]
    )

    # 定义目标函数
    objective = maximize_distance()

    # 创建优化器
    optimizer = GeneticAlgorithm(
        param_space=param_space,
        objective=objective,
        evaluate_func=dummy_simulation,
        population_size=10,
        n_generations=5,
    )

    # 运行优化
    result = optimizer.optimize(verbose=True)

    # 打印结果
    print("\n最优参数:")
    for key, value in result.best_params.items():
        print(f"  {key}: {value:.4f}")
    print(f"\n最优值: {result.best_value:.4f}")
    print(f"评估次数: {result.n_evaluations}")

    return result


def example_comparison():
    """示例 3：对比优化器。"""
    print("\n" + "=" * 60)
    print("示例 3：对比优化器")
    print("=" * 60)

    import matplotlib.pyplot as plt

    from auto_optimization.optimizers import RandomSearch

    # 定义问题
    param_space = ParameterSpace(
        [
            Parameter("param1", ParameterType.CONTINUOUS, (0.0, 5.0)),
            Parameter("param2", ParameterType.CONTINUOUS, (0.0, 5.0)),
        ]
    )
    objective = maximize_distance()
    budget = 30

    results = {}

    # 随机搜索
    print("\n运行随机搜索...")
    random_opt = RandomSearch(param_space, objective, dummy_simulation)
    results["random"] = random_opt.optimize(budget=budget, verbose=False)

    # 贝叶斯优化
    print("运行贝叶斯优化...")
    bayesian_opt = BayesianOptimizer(
        param_space, objective, dummy_simulation, n_initial_points=5
    )
    results["bayesian"] = bayesian_opt.optimize(budget=budget, verbose=False)

    # 绘制收敛曲线
    plt.figure(figsize=(10, 6))
    for name, result in results.items():
        plt.plot(
            range(1, len(result.convergence_curve) + 1),
            result.convergence_curve,
            marker="o",
            label=name,
        )

    plt.xlabel("评估次数")
    plt.ylabel("最优值")
    plt.title("优化器收敛曲线对比")
    plt.legend()
    plt.grid(alpha=0.3)

    output_path = ROOT / "results" / "example_comparison.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    print(f"\n对比图已保存到: {output_path}")

    # 打印对比
    print("\n对比结果:")
    for name, result in results.items():
        print(
            f"  {name}: 最优值={result.best_value:.4f}, 评估次数={result.n_evaluations}"
        )


def main():
    """运行所有示例。"""
    print("自动参数优化工具集 - 示例脚本\n")

    # 示例 1：贝叶斯优化
    example_bayesian_optimization()

    # 示例 2：遗传算法
    try:
        example_genetic_algorithm()
    except ImportError as e:
        print(f"\n遗传算法示例跳过: {e}")
        print("请安装 DEAP: pip install deap")

    # 示例 3：对比
    example_comparison()

    print("\n" + "=" * 60)
    print("所有示例完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
