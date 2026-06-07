"""V13.7 FSM 参数空间探索示例。

探索 V13.7 FSM 相位时长参数对步态性能的影响。
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

# 添加项目路径
ROOT = Path(__file__).resolve().parent
HW1_ROOT = ROOT.parent
V137_DIR = HW1_ROOT / "v13_7_refactored"

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(V137_DIR))
sys.path.insert(0, str(HW1_ROOT))

from space_sampler import ParameterRange
from run_exploration import ParameterExplorer


def create_v137_objective():
    """创建 V13.7 目标函数。"""
    from simulate_v137_refactored import V137Params, make_v137_params, run_simulation

    def objective_func(params: dict[str, float]) -> float:
        """V13.7 目标函数：最大化前进距离。

        Args:
            params: 参数字典，包含 FSM 相位时长等

        Returns:
            前进距离（米）
        """
        try:
            # 构造 V137Params
            v137_params = make_v137_params()

            # 更新 FSM 相位时长
            if "stance_early_duration" in params:
                v137_params.fsm.stance_early_duration = params["stance_early_duration"]
            if "stance_late_duration" in params:
                v137_params.fsm.stance_late_duration = params["stance_late_duration"]
            if "swing_thrust_duration" in params:
                v137_params.fsm.swing_thrust_duration = params["swing_thrust_duration"]
            if "swing_retract_duration" in params:
                v137_params.fsm.swing_retract_duration = params["swing_retract_duration"]

            # 更新 PD 增益（如果提供）
            if "hip_kp" in params:
                v137_params.fsm.hip_kp = params["hip_kp"]
            if "hip_kd" in params:
                v137_params.fsm.hip_kd = params["hip_kd"]
            if "knee_kp" in params:
                v137_params.fsm.knee_kp = params["knee_kp"]
            if "knee_kd" in params:
                v137_params.fsm.knee_kd = params["knee_kd"]

            # 运行仿真
            _, summary = run_simulation(v137_params, verbose=False)

            # 返回前进距离（如果失败则返回 0）
            if summary.get("success", False):
                return summary.get("forward_distance", 0.0)
            else:
                return 0.0

        except Exception as e:
            print(f"Simulation failed: {e}")
            return 0.0

    return objective_func


def explore_fsm_phase_timing():
    """探索 FSM 相位时长参数。"""
    print("=" * 80)
    print("V13.7 FSM Phase Timing Exploration")
    print("=" * 80)

    # 定义参数范围
    param_ranges = [
        ParameterRange("stance_early_duration", 0.10, 0.30),
        ParameterRange("stance_late_duration", 0.15, 0.35),
        ParameterRange("swing_thrust_duration", 0.10, 0.25),
        ParameterRange("swing_retract_duration", 0.10, 0.25),
    ]

    # 创建目标函数
    objective_func = create_v137_objective()

    # 创建探索器
    output_dir = ROOT / "out" / "v137_fsm_exploration"
    explorer = ParameterExplorer(
        param_ranges=param_ranges,
        output_dir=output_dir,
        objective_func=objective_func,
        verbose=True,
    )

    # 1. 初始 LHS 采样（50 个样本）
    print("\n[Step 1] Initial LHS Sampling...")
    explorer.initial_sampling(method="lhs", n_samples=50, seed=42)

    # 2. 拟合高斯过程响应曲面
    print("\n[Step 2] Fitting Gaussian Process Response Surface...")
    explorer.fit_response_surface(method="gp", kernel="matern", noise_level=0.1)

    # 3. Morris 灵敏度筛选
    print("\n[Step 3] Morris Sensitivity Screening...")
    morris_results = explorer.sensitivity_analysis(method="morris", n_samples=20, seed=42)

    # 4. 贝叶斯优化
    print("\n[Step 4] Bayesian Optimization...")
    best_results = explorer.optimize(method="bayesian", n_iterations=30, seed=42)

    # 5. 可视化 2D 切片（使用最优参数作为基准）
    print("\n[Step 5] Visualizing 2D Slices...")
    explorer.visualize_2d_slices(fixed_params=best_results["best_params"])

    # 6. 可视化 3D 曲面（选择最重要的两个参数）
    print("\n[Step 6] Visualizing 3D Surfaces...")
    top_params = [name for name, _ in morris_results["ranked_params"][:2]]
    if len(top_params) >= 2:
        explorer.visualize_3d_surface(top_params[0], top_params[1], fixed_params=best_results["best_params"])

    # 7. 生成报告
    print("\n[Step 7] Generating Report...")
    explorer.generate_report()

    print(f"\n{'=' * 80}")
    print(f"Exploration Complete!")
    print(f"Results saved to: {output_dir}")
    print(f"{'=' * 80}")

    return explorer, best_results


def explore_pd_gains():
    """探索 PD 增益参数。"""
    print("=" * 80)
    print("V13.7 PD Gains Exploration")
    print("=" * 80)

    # 定义参数范围（对数尺度）
    param_ranges = [
        ParameterRange("hip_kp", 10.0, 50.0, log_scale=False),
        ParameterRange("hip_kd", 1.0, 10.0, log_scale=False),
        ParameterRange("knee_kp", 5.0, 30.0, log_scale=False),
        ParameterRange("knee_kd", 0.5, 5.0, log_scale=False),
    ]

    # 创建目标函数
    objective_func = create_v137_objective()

    # 创建探索器
    output_dir = ROOT / "out" / "v137_pd_exploration"
    explorer = ParameterExplorer(
        param_ranges=param_ranges,
        output_dir=output_dir,
        objective_func=objective_func,
        verbose=True,
    )

    # 1. 初始采样
    print("\n[Step 1] Initial Sobol Sampling...")
    explorer.initial_sampling(method="sobol", n_samples=64, seed=42)

    # 2. 拟合响应曲面（集成模型）
    print("\n[Step 2] Fitting Ensemble Response Surface...")
    explorer.fit_response_surface(method="ensemble")

    # 3. Sobol 全局灵敏度分析
    print("\n[Step 3] Sobol Sensitivity Analysis...")
    sobol_results = explorer.sensitivity_analysis(
        method="sobol", n_samples=256, calc_second_order=True, seed=42
    )

    # 4. 遗传算法优化
    print("\n[Step 4] Genetic Algorithm Optimization...")
    best_results = explorer.optimize(method="genetic", n_iterations=50, seed=42)

    # 5. 可视化
    print("\n[Step 5] Visualizing Results...")
    explorer.visualize_2d_slices(fixed_params=best_results["best_params"])

    # 选择最重要的两个参数对可视化
    top_pairs = [
        ("hip_kp", "hip_kd"),
        ("knee_kp", "knee_kd"),
        ("hip_kp", "knee_kp"),
    ]
    for p1, p2 in top_pairs:
        explorer.visualize_3d_surface(p1, p2, fixed_params=best_results["best_params"])

    # 6. 生成报告
    print("\n[Step 6] Generating Report...")
    explorer.generate_report()

    print(f"\n{'=' * 80}")
    print(f"Exploration Complete!")
    print(f"Results saved to: {output_dir}")
    print(f"{'=' * 80}")

    return explorer, best_results


def multiobjective_distance_cot():
    """多目标优化：最大化距离 + 最小化 CoT。"""
    print("=" * 80)
    print("V13.7 Multi-Objective Optimization: Distance + CoT")
    print("=" * 80)

    from simulate_v137_refactored import make_v137_params, run_simulation

    # 定义参数范围（选择少数关键参数）
    param_ranges = [
        ParameterRange("hip_kp", 20.0, 40.0),
        ParameterRange("hip_kd", 3.0, 8.0),
        ParameterRange("knee_kp", 10.0, 25.0),
        ParameterRange("stance_early_duration", 0.15, 0.25),
    ]

    # 定义两个目标函数
    def distance_objective(params: dict[str, float]) -> float:
        """最大化前进距离。"""
        try:
            v137_params = make_v137_params()
            # 更新参数
            if "hip_kp" in params:
                v137_params.fsm.hip_kp = params["hip_kp"]
            if "hip_kd" in params:
                v137_params.fsm.hip_kd = params["hip_kd"]
            if "knee_kp" in params:
                v137_params.fsm.knee_kp = params["knee_kp"]
            if "stance_early_duration" in params:
                v137_params.fsm.stance_early_duration = params["stance_early_duration"]

            _, summary = run_simulation(v137_params, verbose=False)
            if summary.get("success", False):
                return summary.get("forward_distance", 0.0)
            return 0.0
        except:
            return 0.0

    def efficiency_objective(params: dict[str, float]) -> float:
        """最大化效率（最小化 CoT 的负值）。"""
        try:
            v137_params = make_v137_params()
            # 更新参数
            if "hip_kp" in params:
                v137_params.fsm.hip_kp = params["hip_kp"]
            if "hip_kd" in params:
                v137_params.fsm.hip_kd = params["hip_kd"]
            if "knee_kp" in params:
                v137_params.fsm.knee_kp = params["knee_kp"]
            if "stance_early_duration" in params:
                v137_params.fsm.stance_early_duration = params["stance_early_duration"]

            _, summary = run_simulation(v137_params, verbose=False)
            if summary.get("success", False):
                cot = summary.get("cost_of_transport", float("inf"))
                # 返回负 CoT（越小越好转为越大越好）
                return -cot if cot < float("inf") else -1000.0
            return -1000.0
        except:
            return -1000.0

    # 创建探索器（使用 distance 作为主目标函数）
    output_dir = ROOT / "out" / "v137_multiobjective"
    explorer = ParameterExplorer(
        param_ranges=param_ranges,
        output_dir=output_dir,
        objective_func=distance_objective,
        verbose=True,
    )

    # 1. 初始采样
    print("\n[Step 1] Initial LHS Sampling...")
    explorer.initial_sampling(method="lhs", n_samples=30, seed=42)

    # 2. 多目标优化
    print("\n[Step 2] Multi-Objective Optimization (NSGA-II)...")
    pareto_results = explorer.multi_objective_optimize(
        objective_funcs=[distance_objective, efficiency_objective],
        objective_names=["Distance (m)", "Efficiency (-CoT)"],
        maximize=[True, True],
        n_generations=50,
        population_size=50,
        seed=42,
    )

    # 3. 分析 Pareto 前沿
    print("\n[Step 3] Analyzing Pareto Front...")
    pareto_objectives = pareto_results["pareto_objectives"]
    pareto_params = pareto_results["pareto_params"]

    # 找到几个代表性解
    # a) 最大距离
    max_dist_idx = np.argmax(pareto_objectives[:, 0])
    # b) 最大效率
    max_eff_idx = np.argmax(pareto_objectives[:, 1])
    # c) 折中（加权和）
    weights = np.array([0.6, 0.4])
    scores = pareto_objectives @ weights
    balanced_idx = np.argmax(scores)

    print("\nPareto Front Analysis:")
    print(f"  Total solutions: {len(pareto_params)}")
    print(f"\n  Solution A (Max Distance):")
    print(f"    Distance: {pareto_objectives[max_dist_idx, 0]:.4f} m")
    print(f"    Efficiency: {pareto_objectives[max_dist_idx, 1]:.4f}")
    print(f"    Params: {pareto_params[max_dist_idx]}")
    print(f"\n  Solution B (Max Efficiency):")
    print(f"    Distance: {pareto_objectives[max_eff_idx, 0]:.4f} m")
    print(f"    Efficiency: {pareto_objectives[max_eff_idx, 1]:.4f}")
    print(f"    Params: {pareto_params[max_eff_idx]}")
    print(f"\n  Solution C (Balanced):")
    print(f"    Distance: {pareto_objectives[balanced_idx, 0]:.4f} m")
    print(f"    Efficiency: {pareto_objectives[balanced_idx, 1]:.4f}")
    print(f"    Params: {pareto_params[balanced_idx]}")

    # 4. 生成报告
    print("\n[Step 4] Generating Report...")
    explorer.generate_report()

    print(f"\n{'=' * 80}")
    print(f"Multi-Objective Optimization Complete!")
    print(f"Results saved to: {output_dir}")
    print(f"{'=' * 80}")

    return explorer, pareto_results


def main():
    """主函数。"""
    import argparse

    parser = argparse.ArgumentParser(description="V13.7 Parameter Space Exploration")
    parser.add_argument(
        "--mode",
        type=str,
        choices=["fsm", "pd", "multiobjective", "all"],
        default="fsm",
        help="Exploration mode",
    )
    args = parser.parse_args()

    if args.mode == "fsm":
        explore_fsm_phase_timing()
    elif args.mode == "pd":
        explore_pd_gains()
    elif args.mode == "multiobjective":
        multiobjective_distance_cot()
    elif args.mode == "all":
        print("Running all exploration modes...\n")
        explore_fsm_phase_timing()
        print("\n" * 3)
        explore_pd_gains()
        print("\n" * 3)
        multiobjective_distance_cot()


if __name__ == "__main__":
    main()
