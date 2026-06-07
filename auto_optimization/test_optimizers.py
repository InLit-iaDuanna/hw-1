"""测试优化器基本功能。

验证各优化器能正确运行并找到最优解。
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
HW1_ROOT = ROOT.parent
sys.path.insert(0, str(HW1_ROOT))

from auto_optimization.constraints.parameter_bounds import (
    Parameter,
    ParameterSpace,
    ParameterType,
)
from auto_optimization.objectives.objective_functions import maximize_distance
from auto_optimization.optimizers import BayesianOptimizer, RandomSearch


def sphere_function(params: dict) -> dict:
    """球函数：f(x) = sum(x_i^2)，最小值在原点。

    我们优化 -f(x)（最大化负值），最优点在 (0, 0)。
    """
    x = params["x1"]
    y = params["x2"]
    value = -(x**2 + y**2)

    return {
        "success": True,
        "forward_distance": value,
    }


def test_bayesian_optimizer():
    """测试贝叶斯优化器。"""
    print("测试贝叶斯优化器...")

    param_space = ParameterSpace(
        [
            Parameter("x1", ParameterType.CONTINUOUS, (-5.0, 5.0)),
            Parameter("x2", ParameterType.CONTINUOUS, (-5.0, 5.0)),
        ]
    )

    optimizer = BayesianOptimizer(
        param_space=param_space,
        objective=maximize_distance(),
        evaluate_func=sphere_function,
        n_initial_points=5,
        random_state=42,
    )

    result = optimizer.optimize(budget=20, verbose=False)

    # 检查是否接近最优解 (0, 0)
    x1_opt = result.best_params["x1"]
    x2_opt = result.best_params["x2"]
    distance_to_optimum = np.sqrt(x1_opt**2 + x2_opt**2)

    print(f"  最优点: ({x1_opt:.4f}, {x2_opt:.4f})")
    print(f"  距离真实最优点: {distance_to_optimum:.4f}")
    print(f"  最优值: {result.best_value:.4f}")

    assert distance_to_optimum < 2.0, "贝叶斯优化未找到接近最优解的点"
    print("  [PASS] 测试通过\n")


def test_random_search():
    """测试随机搜索。"""
    print("测试随机搜索...")

    param_space = ParameterSpace(
        [
            Parameter("x1", ParameterType.CONTINUOUS, (-5.0, 5.0)),
            Parameter("x2", ParameterType.CONTINUOUS, (-5.0, 5.0)),
        ]
    )

    optimizer = RandomSearch(
        param_space=param_space,
        objective=maximize_distance(),
        evaluate_func=sphere_function,
        random_state=42,
    )

    result = optimizer.optimize(budget=30, verbose=False)

    x1_opt = result.best_params["x1"]
    x2_opt = result.best_params["x2"]
    distance_to_optimum = np.sqrt(x1_opt**2 + x2_opt**2)

    print(f"  最优点: ({x1_opt:.4f}, {x2_opt:.4f})")
    print(f"  距离真实最优点: {distance_to_optimum:.4f}")
    print(f"  最优值: {result.best_value:.4f}")

    assert result.n_evaluations == 30, "评估次数不正确"
    print("  [PASS] 测试通过\n")


def test_parameter_space():
    """测试参数空间。"""
    print("测试参数空间...")

    space = ParameterSpace(
        [
            Parameter("p1", ParameterType.CONTINUOUS, (0.0, 10.0), default=5.0),
            Parameter("p2", ParameterType.INTEGER, (1, 100), default=50),
        ]
    )

    # 测试验证
    assert space.validate({"p1": 5.0, "p2": 50}) == True
    assert space.validate({"p1": 15.0, "p2": 50}) == False  # p1 超出边界
    assert space.validate({"p1": 5.0, "p2": 50.5}) == False  # p2 应该是整数

    # 测试裁剪
    clipped = space.clip({"p1": 15.0, "p2": 150})
    assert clipped["p1"] == 10.0
    assert clipped["p2"] == 100

    # 测试默认值
    defaults = space.get_defaults()
    assert defaults["p1"] == 5.0
    assert defaults["p2"] == 50

    print("  [PASS] 测试通过\n")


def test_objective_functions():
    """测试目标函数。"""
    print("测试目标函数...")

    from auto_optimization.objectives.objective_functions import (
        MinimizeCOT,
        combined_objective,
    )

    # 成功仿真
    result_success = {
        "success": True,
        "forward_distance": 10.0,
        "positive_work": 500.0,
    }

    # 失败仿真
    result_failure = {
        "success": False,
        "forward_distance": 0.0,
    }

    # 测试最大化距离
    obj_dist = maximize_distance()
    assert obj_dist.evaluate(result_success) == 10.0
    assert obj_dist.evaluate(result_failure) == -1000.0

    # 测试最小化 CoT
    obj_cot = MinimizeCOT(mass=10.0, gravity=9.81)
    cot_value = obj_cot.evaluate(result_success)
    assert cot_value < 0  # 返回负值（以便最大化）

    # 测试组合目标
    obj_combined = combined_objective(distance_weight=0.7, cot_weight=-0.3, mass=10.0)
    combined_value = obj_combined.evaluate(result_success)
    assert combined_value > 0

    print("  [PASS] 测试通过\n")


def main():
    """运行所有测试。"""
    print("=" * 60)
    print("运行优化器测试套件")
    print("=" * 60 + "\n")

    test_parameter_space()
    test_objective_functions()
    test_random_search()

    try:
        test_bayesian_optimizer()
    except ImportError:
        print("跳过贝叶斯优化测试（需安装 scikit-optimize）\n")

    print("=" * 60)
    print("所有测试通过！")
    print("=" * 60)


if __name__ == "__main__":
    main()
