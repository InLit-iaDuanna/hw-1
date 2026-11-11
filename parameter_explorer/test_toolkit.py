"""测试参数探索工具集。

验证各模块的基本功能。
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from optimizer import BayesianOptimizer
from response_surface import build_response_surface
from run_exploration import ParameterExplorer
from sensitivity_analyzer import SensitivityAnalyzer
from space_sampler import ParameterRange, SpaceSampler
from visualizer import ParameterVisualizer


def test_sampling():
    """测试采样功能。"""
    print("\n" + "=" * 60)
    print("Testing Sampling...")
    print("=" * 60)

    param_ranges = [
        ParameterRange("x", 0.0, 10.0),
        ParameterRange("y", -5.0, 5.0),
    ]

    sampler = SpaceSampler(param_ranges)

    # 测试各种采样方法
    samples_grid, _ = sampler.grid_sample(n_per_dim=5)
    print(f"Grid sampling: {samples_grid.shape}")

    samples_random, _ = sampler.random_sample(n_samples=20, seed=42)
    print(f"Random sampling: {samples_random.shape}")

    samples_lhs, _ = sampler.lhs_sample(n_samples=20, seed=42)
    print(f"LHS sampling: {samples_lhs.shape}")

    samples_sobol, _ = sampler.sobol_sample(n_samples=32, seed=42)
    print(f"Sobol sampling: {samples_sobol.shape}")

    print("[PASS] Sampling tests passed")


def test_response_surface():
    """测试响应曲面拟合。"""
    print("\n" + "=" * 60)
    print("Testing Response Surface...")
    print("=" * 60)

    # 生成测试数据（二维 Rosenbrock 函数）
    np.random.seed(42)
    n_samples = 30
    X = np.random.uniform(-2, 2, size=(n_samples, 2))
    y = (1 - X[:, 0]) ** 2 + 100 * (X[:, 1] - X[:, 0] ** 2) ** 2

    # 测试不同的响应曲面方法
    for method in ["gp", "polynomial", "rbf"]:
        surface = build_response_surface(X, y, method=method)
        y_pred = surface.predict(X[:5])
        print(f"{method.upper()}: predicted {len(y_pred)} values")

    print("[PASS] Response surface tests passed")


def test_sensitivity():
    """测试灵敏度分析。"""
    print("\n" + "=" * 60)
    print("Testing Sensitivity Analysis...")
    print("=" * 60)

    # 简单测试函数
    def objective(params):
        x = params["x"]
        y = params["y"]
        z = params["z"]
        return x**2 + 2 * y**2 + 0.1 * z**2  # y 应该最敏感

    param_names = ["x", "y", "z"]
    param_bounds = [(0.0, 1.0), (0.0, 1.0), (0.0, 1.0)]

    analyzer = SensitivityAnalyzer(param_names, param_bounds)

    # Morris 筛选
    morris_results = analyzer.morris_screening(objective, n_trajectories=10, seed=42)
    ranked = analyzer.rank_parameters(morris_results, method="morris")
    print(f"Morris ranking: {[name for name, _ in ranked]}")

    # 验证 y 是最敏感的
    assert ranked[0][0] == "y", "y should be most sensitive"

    print("[PASS] Sensitivity analysis tests passed")


def test_optimizer():
    """测试优化器。"""
    print("\n" + "=" * 60)
    print("Testing Optimizers...")
    print("=" * 60)

    # 简单测试函数（在 x=5, y=3 处最大）
    def objective(params):
        x = params["x"]
        y = params["y"]
        return -((x - 5) ** 2 + (y - 3) ** 2)

    param_names = ["x", "y"]
    param_bounds = [(0.0, 10.0), (0.0, 10.0)]

    # 贝叶斯优化
    bo = BayesianOptimizer(param_names, param_bounds, random_state=42)
    bo_results = bo.optimize(objective, n_initial=5, n_iterations=10, verbose=False)
    print(
        f"Bayesian Opt: best = {bo_results['best_value']:.4f} at {bo_results['best_params']}"
    )

    # 验证找到了接近最优的解
    best_x = bo_results["best_params"]["x"]
    best_y = bo_results["best_params"]["y"]
    assert (
        abs(best_x - 5) < 1.0 and abs(best_y - 3) < 1.0
    ), "Should find near-optimal solution"

    print("[PASS] Optimizer tests passed")


def test_visualizer():
    """测试可视化（不实际显示图像）。"""
    print("\n" + "=" * 60)
    print("Testing Visualizer...")
    print("=" * 60)

    output_dir = ROOT / "out" / "test_visualizer"
    viz = ParameterVisualizer(output_dir=output_dir)

    # 生成测试数据
    x = np.linspace(0, 10, 50)
    y = np.sin(x) + np.random.randn(50) * 0.1

    # 测试 2D 切片（不显示，只保存）
    import matplotlib

    matplotlib.use("Agg")  # 无 GUI 后端

    viz.plot_2d_slice(
        "test_param",
        x,
        y,
        filename="test_2d_slice.png",
    )

    print(f"[PASS] Visualizer tests passed (output saved to {output_dir})")


def test_full_workflow():
    """测试完整工作流。"""
    print("\n" + "=" * 60)
    print("Testing Full Workflow...")
    print("=" * 60)

    # 简单测试函数
    def objective(params):
        x = params["x"]
        y = params["y"]
        return np.sin(x) * np.cos(y) + 0.1 * x

    param_ranges = [
        ParameterRange("x", 0.0, 6.28),
        ParameterRange("y", 0.0, 6.28),
    ]

    output_dir = ROOT / "out" / "test_workflow"
    explorer = ParameterExplorer(
        param_ranges=param_ranges,
        output_dir=output_dir,
        objective_func=objective,
        verbose=False,
    )

    # 运行简化工作流
    import matplotlib

    matplotlib.use("Agg")

    explorer.initial_sampling(method="lhs", n_samples=20, seed=42)
    explorer.fit_response_surface(method="gp")
    sensitivity = explorer.sensitivity_analysis(method="morris", n_samples=10, seed=42)
    best = explorer.optimize(method="bayesian", n_iterations=10, seed=42)
    explorer.generate_report()

    print(f"Best found: {best['best_value']:.4f} at {best['best_params']}")
    print(f"[PASS] Full workflow test passed (output saved to {output_dir})")


def main():
    """运行所有测试。"""
    print("=" * 60)
    print("Parameter Explorer Test Suite")
    print("=" * 60)

    try:
        test_sampling()
        test_response_surface()
        test_sensitivity()
        test_optimizer()
        test_visualizer()
        test_full_workflow()

        print("\n" + "=" * 60)
        print("All tests passed!")
        print("=" * 60)

    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
