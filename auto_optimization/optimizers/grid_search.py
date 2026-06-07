"""网格搜索：穷举所有参数组合。

适合低维参数空间和快速仿真。
"""

from __future__ import annotations

import itertools
import time
from typing import Any, Callable

import numpy as np

from ..constraints.parameter_bounds import ParameterSpace
from ..objectives.objective_functions import ObjectiveFunction


class GridSearch:
    """网格搜索优化器。

    在每个维度上均匀划分网格，穷举所有组合。

    优点：
    - 简单可靠
    - 覆盖整个空间

    缺点：
    - 计算量随维度指数增长（维度诅咒）
    - 只适合 2-3 维低维问题

    Example:
        >>> from auto_optimization.optimizers.grid_search import GridSearch
        >>> from auto_optimization import maximize_distance
        >>> from auto_optimization.constraints.parameter_bounds import ParameterSpace, Parameter, ParameterType
        >>>
        >>> space = ParameterSpace([
        ...     Parameter("k_p", ParameterType.CONTINUOUS, (0.5, 5.0)),
        ...     Parameter("k_d", ParameterType.CONTINUOUS, (0.1, 2.0)),
        ... ])
        >>> optimizer = GridSearch(space, maximize_distance(), simulate_func, n_points_per_dim=10)
        >>> result = optimizer.optimize()
    """

    def __init__(
        self,
        param_space: ParameterSpace,
        objective: ObjectiveFunction,
        evaluate_func: Callable[[dict[str, Any]], dict[str, Any]],
        n_points_per_dim: int = 10,
    ):
        """初始化网格搜索优化器。

        Args:
            param_space: 参数空间
            objective: 目标函数
            evaluate_func: 评估函数 params -> simulation_result
            n_points_per_dim: 每个维度的网格点数
        """
        self.param_space = param_space
        self.objective = objective
        self.evaluate_func = evaluate_func
        self.n_points_per_dim = n_points_per_dim

        self.history: list[tuple[dict[str, Any], float]] = []

    def optimize(self, verbose: bool = True):
        """运行网格搜索。

        Args:
            verbose: 是否打印进度

        Returns:
            OptimizationResult 对象
        """
        from .bayesian_optimizer import OptimizationResult

        param_names = self.param_space.get_parameter_names()
        bounds = self.param_space.get_bounds()

        # 生成每个维度的网格点
        grids = []
        for low, high in bounds:
            grids.append(np.linspace(low, high, self.n_points_per_dim))

        # 笛卡尔积生成所有组合
        all_combinations = list(itertools.product(*grids))
        total = len(all_combinations)

        if verbose:
            print(f"网格搜索：{total} 个参数组合 ({self.n_points_per_dim}^{len(bounds)})")

        best_params = None
        best_value = float("-inf")

        # 遍历所有组合
        for idx, combination in enumerate(all_combinations):
            params = {name: value for name, value in zip(param_names, combination)}

            start_time = time.time()
            result = self.evaluate_func(params)
            value = self.objective.evaluate(result)
            elapsed = time.time() - start_time

            self.history.append((params.copy(), value))

            if value > best_value:
                best_value = value
                best_params = params.copy()

            if verbose and (idx + 1) % max(1, total // 20) == 0:
                print(
                    f"[{idx+1}/{total}] "
                    f"current={value:.4f}, best={best_value:.4f} ({elapsed:.2f}s)"
                )

        # 收敛曲线
        convergence_curve = []
        current_best = float("-inf")
        for _, value in self.history:
            current_best = max(current_best, value)
            convergence_curve.append(current_best)

        return OptimizationResult(
            best_params=best_params,
            best_value=best_value,
            n_evaluations=len(self.history),
            convergence_curve=convergence_curve,
            all_params=[params for params, _ in self.history],
            all_values=[value for _, value in self.history],
            metadata={
                "optimizer": "GridSearch",
                "n_points_per_dim": self.n_points_per_dim,
                "objective": self.objective.name,
            },
        )
