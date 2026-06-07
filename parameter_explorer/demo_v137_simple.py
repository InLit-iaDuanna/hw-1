"""V13.7 参数空间探索演示（简化版）。

使用代理模型快速演示工具集功能，无需运行完整仿真。
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from space_sampler import ParameterRange
from run_exploration import ParameterExplorer


def create_mock_objective():
    """创建模拟 V13.7 目标函数（快速演示）。

    模拟真实步态优化问题的特征：
    - 多个局部最优
    - 参数交互
    - 噪声
    """

    def objective_func(params: dict[str, float]) -> float:
        """模拟目标函数：前进距离（米）。

        物理意义：
        - stance_early: 0.15-0.25s 最佳
        - stance_late: 0.20-0.30s 最佳
        - hip_kp: 25-35 最佳
        - hip_kd: 4-6 最佳
        """
        # 提取参数
        se = params.get("stance_early_duration", 0.20)
        sl = params.get("stance_late_duration", 0.25)
        hip_kp = params.get("hip_kp", 30.0)
        hip_kd = params.get("hip_kd", 5.0)

        # 模拟复杂响应曲面
        # 1. 相位时长：钟形曲线
        phase_score = -((se - 0.20) ** 2) * 50 - ((sl - 0.25) ** 2) * 40

        # 2. PD 增益：二次最优
        gain_score = -((hip_kp - 30) ** 2) * 0.02 - ((hip_kd - 5) ** 2) * 0.5

        # 3. 交互作用：相位与增益的耦合
        interaction = -0.1 * (se - 0.20) * (hip_kp - 30)

        # 4. 总距离（基础值 + 调优收益）
        base_distance = 8.0
        tuning_bonus = phase_score + gain_score + interaction

        # 5. 添加小噪声
        noise = np.random.randn() * 0.05

        # 6. 失败惩罚（极端参数）
        if se < 0.12 or se > 0.28 or sl < 0.17 or sl > 0.33:
            return 0.0
        if hip_kp < 15 or hip_kp > 45 or hip_kd < 2 or hip_kd > 8:
            return 0.0

        return max(0.0, base_distance + tuning_bonus + noise)

    return objective_func


def demo_exploration():
    """演示完整参数空间探索流程。"""
    print("=" * 80)
    print("Parameter Space Exploration Demo (V13.7 Simplified)")
    print("=" * 80)

    # 1. 定义参数范围
    param_ranges = [
        ParameterRange("stance_early_duration", 0.12, 0.28),
        ParameterRange("stance_late_duration", 0.17, 0.33),
        ParameterRange("hip_kp", 15.0, 45.0),
        ParameterRange("hip_kd", 2.0, 8.0),
    ]

    # 2. 创建模拟目标函数
    np.random.seed(42)
    objective_func = create_mock_objective()

    # 3. 创建探索器
    output_dir = ROOT / "out" / "demo_exploration"
    explorer = ParameterExplorer(
        param_ranges=param_ranges,
        output_dir=output_dir,
        objective_func=objective_func,
        verbose=True,
    )

    # 4. 初始 LHS 采样
    print("\n[Step 1/7] Initial LHS Sampling (50 samples)...")
    explorer.initial_sampling(method="lhs", n_samples=50, seed=42)

    # 5. 拟合高斯过程响应曲面
    print("\n[Step 2/7] Fitting Gaussian Process Response Surface...")
    explorer.fit_response_surface(method="gp", kernel="matern", noise_level=0.1)

    # 6. Morris 灵敏度筛选
    print("\n[Step 3/7] Morris Sensitivity Screening...")
    morris_results = explorer.sensitivity_analysis(method="morris", n_samples=20, seed=42)

    print("\nParameter Importance Ranking:")
    for i, (name, score) in enumerate(morris_results["ranked_params"], 1):
        print(f"  {i}. {name}: {score:.4f}")

    # 7. Sobol 全局灵敏度（可选，不计算二阶以避免复杂性）
    print("\n[Step 4/7] Sobol Global Sensitivity Analysis...")
    sobol_results = explorer.sensitivity_analysis(
        method="sobol", n_samples=256, calc_second_order=False, seed=42
    )

    print("\nSobol Total Indices:")
    for name, st in zip(sobol_results["param_names"], sobol_results["ST"]):
        print(f"  {name}: {st:.4f}")

    # 8. 贝叶斯优化
    print("\n[Step 5/7] Bayesian Optimization (30 iterations)...")
    best_results = explorer.optimize(method="bayesian", n_iterations=30, seed=42)

    print(f"\nBest Parameters Found:")
    for name, value in best_results["best_params"].items():
        print(f"  {name}: {value:.6f}")
    print(f"Best Objective: {best_results['best_value']:.4f} m")

    # 9. 可视化 2D 切片
    print("\n[Step 6/7] Visualizing 2D Slices...")
    explorer.visualize_2d_slices(fixed_params=best_results["best_params"])

    # 10. 可视化 3D 曲面（选择最重要的参数对）
    print("\n[Step 7/7] Visualizing 3D Surfaces...")
    important_pairs = [
        ("stance_early_duration", "stance_late_duration"),
        ("hip_kp", "hip_kd"),
        ("stance_early_duration", "hip_kp"),
    ]

    for p1, p2 in important_pairs:
        print(f"  Generating {p1} vs {p2}...")
        explorer.visualize_3d_surface(p1, p2, fixed_params=best_results["best_params"])

    # 11. 生成报告
    print("\nGenerating Final Report...")
    explorer.generate_report()

    print(f"\n{'=' * 80}")
    print(f"Exploration Complete!")
    print(f"{'=' * 80}")
    print(f"\nResults saved to: {output_dir}")
    print(f"\nGenerated files:")
    print(f"  - initial_sampling.json")
    print(f"  - sensitivity_morris.json & .png")
    print(f"  - sensitivity_sobol.json & .png")
    print(f"  - interaction_heatmap.png")
    print(f"  - optimization_bayesian.json & .png")
    print(f"  - slice_2d_*.png (4 files)")
    print(f"  - surface_3d_*.png & contour_*.png (6 files)")
    print(f"  - exploration_report.txt")
    print(f"\nRecommended Next Steps:")
    print(f"  1. Review sensitivity analysis to identify critical parameters")
    print(f"  2. Examine 3D surfaces to understand parameter interactions")
    print(f"  3. Validate best parameters with full V13.7 simulation")
    print(f"  4. Fine-tune around optimal region with denser sampling")

    return explorer, best_results


def demo_multiobjective():
    """演示多目标优化（距离 vs 能耗）。"""
    print("\n\n" + "=" * 80)
    print("Multi-Objective Optimization Demo")
    print("=" * 80)

    # 模拟两个目标函数
    def distance_objective(params: dict[str, float]) -> float:
        """最大化前进距离。"""
        hip_kp = params.get("hip_kp", 30.0)
        hip_kd = params.get("hip_kd", 5.0)
        return 8.0 - ((hip_kp - 30) ** 2) * 0.02 - ((hip_kd - 5) ** 2) * 0.5

    def efficiency_objective(params: dict[str, float]) -> float:
        """最大化效率（最小化能耗的负值）。"""
        hip_kp = params.get("hip_kp", 30.0)
        hip_kd = params.get("hip_kd", 5.0)
        # 高增益通常消耗更多能量
        cot = 0.05 + hip_kp * 0.001 + hip_kd * 0.005
        return -cot  # 转为最大化

    param_ranges = [
        ParameterRange("hip_kp", 15.0, 45.0),
        ParameterRange("hip_kd", 2.0, 8.0),
    ]

    output_dir = ROOT / "out" / "demo_multiobjective"
    explorer = ParameterExplorer(
        param_ranges=param_ranges,
        output_dir=output_dir,
        objective_func=distance_objective,
        verbose=True,
    )

    # 初始采样
    print("\n[Step 1/2] Initial Sampling...")
    explorer.initial_sampling(method="lhs", n_samples=20, seed=42)

    # 多目标优化
    print("\n[Step 2/2] Multi-Objective Optimization (NSGA-II)...")
    pareto_results = explorer.multi_objective_optimize(
        objective_funcs=[distance_objective, efficiency_objective],
        objective_names=["Distance (m)", "Efficiency (-CoT)"],
        maximize=[True, True],
        n_generations=30,
        population_size=40,
        seed=42,
    )

    print(f"\nFound {pareto_results['n_solutions']} Pareto-optimal solutions")
    print(f"\nPareto Front saved to: {output_dir / 'pareto_front.png'}")

    return explorer, pareto_results


if __name__ == "__main__":
    import matplotlib

    matplotlib.use("Agg")  # 无 GUI 后端

    # 运行演示
    print("Starting Parameter Space Exploration Demo...\n")

    explorer1, best1 = demo_exploration()
    explorer2, pareto = demo_multiobjective()

    print("\n\n" + "=" * 80)
    print("DEMO COMPLETE!")
    print("=" * 80)
    print("\nAll visualization files have been generated.")
    print("Check the output directories for detailed results.")
