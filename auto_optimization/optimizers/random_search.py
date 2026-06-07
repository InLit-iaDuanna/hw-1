"""随机搜索：随机采样参数空间。

作为基线方法，对比其他优化算法的性能。
"""

from __future__ import annotations

import time
from typing import Any, Callable

import numpy as np

from ..constraints.parameter_bounds import ParameterSpace
from ..objectives.objective_functions import ObjectiveFunction


class RandomSearch:
    """随机搜索优化器。

    在参数空间中随机采样，评估目标函数值。

    优点：
    - 实现简单
    - 适用于任意维度
    - 作为基线方法

    Example:
        >>> from auto_optimization.optimizers.random_search import RandomSearch
        >>> from auto_optimization import maximize_distance
        >>>
        >>> optimizer = RandomSearch(space, maximize_distance(), simulate_func)
        >>> result = optimizer.optimize(budget=50)
    """

    def __init__(
        self,
        param_space: ParameterSpace,
        objective: ObjectiveFunction,
        evaluate_func: Callable[[dict[str, Any]], dict[str, Any]],
        random_state: int | None = None,
    ):
        """初始化随机搜索优化器。

        Args:
            param_space: 参数空间
            objective: 目标函数
            evaluate_func: 评估函数 params -> simulation_result
            random_state: 随机种子
        """
        self.param_space = param_space
        self.objective = objective
        self.evaluate_func = evaluate_func

        if random_state is not None:
            np.random.seed(random_state)

        self.history: list[tuple[dict[str, Any], float]] = []

    def optimize(self, budget: int = 50, verbose: bool = True):
        """运行随机搜索。

        Args:
            budget: 评估预算（采样次数）
            verbose: 是否打印进度

        Returns:
            OptimizationResult 对象
        """
        from .bayesian_optimizer import OptimizationResult

        param_names = self.param_space.get_parameter_names()
        bounds = self.param_space.get_bounds()

        best_params = None
        best_value = float("-inf")

        for i in range(budget):
            # 随机采样
            params = {}
            for name, (low, high) in zip(param_names, bounds):
                params[name] = np.random.uniform(low, high)

            start_time = time.time()
            result = self.evaluate_func(params)
            value = self.objective.evaluate(result)
            elapsed = time.time() - start_time

            self.history.append((params.copy(), value))

            if value > best_value:
                best_value = value
                best_params = params.copy()

            if verbose:
                print(
                    f"[{i+1}/{budget}] "
                    f"value={value:.4f}, best={best_value:.4f} ({elapsed:.2f}s)"
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
                "optimizer": "RandomSearch",
                "objective": self.objective.name,
            },
        )
