"""CMA-ES 优化器：协方差矩阵自适应进化策略。

适合高维连续优化问题，样本效率高于遗传算法。

依赖：cma (Covariance Matrix Adaptation Evolution Strategy)
安装：pip install cma
"""

from __future__ import annotations

import time
from typing import Any, Callable

import numpy as np

try:
    import cma

    CMA_AVAILABLE = True
except ImportError:
    CMA_AVAILABLE = False

from ..constraints.parameter_bounds import ParameterSpace
from ..objectives.objective_functions import ObjectiveFunction


class CMAES:
    """CMA-ES 优化器。

    使用协方差矩阵自适应策略搜索最优参数。

    优点：
    - 适合高维连续优化（10-100 维）
    - 自适应步长
    - 对噪声鲁棒

    Example:
        >>> from auto_optimization.optimizers.cma_es import CMAES
        >>> from auto_optimization import maximize_distance
        >>>
        >>> optimizer = CMAES(space, maximize_distance(), simulate_func)
        >>> result = optimizer.optimize(budget=100)
    """

    def __init__(
        self,
        param_space: ParameterSpace,
        objective: ObjectiveFunction,
        evaluate_func: Callable[[dict[str, Any]], dict[str, Any]],
        sigma0: float = 0.5,
        random_state: int | None = None,
    ):
        """初始化 CMA-ES 优化器。

        Args:
            param_space: 参数空间
            objective: 目标函数
            evaluate_func: 评估函数 params -> simulation_result
            sigma0: 初始步长（相对边界范围）
            random_state: 随机种子
        """
        if not CMA_AVAILABLE:
            raise ImportError("cma 未安装。请运行: pip install cma")

        self.param_space = param_space
        self.objective = objective
        self.evaluate_func = evaluate_func
        self.sigma0 = sigma0
        self.random_state = random_state

        self.history: list[tuple[dict[str, Any], float]] = []

    def optimize(self, budget: int = 100, verbose: bool = True):
        """运行 CMA-ES 优化。

        Args:
            budget: 评估预算
            verbose: 是否打印进度

        Returns:
            OptimizationResult 对象
        """
        from .bayesian_optimizer import OptimizationResult

        param_names = self.param_space.get_parameter_names()
        bounds = self.param_space.get_bounds()

        # 初始点（中点）
        x0 = [(low + high) / 2.0 for low, high in bounds]

        # 创建 CMA-ES 优化器
        options = {
            "maxfevals": budget,
            "bounds": [[low for low, _ in bounds], [high for _, high in bounds]],
            "seed": self.random_state,
            "verbose": -1,  # 禁用内部输出
        }
        es = cma.CMAEvolutionStrategy(x0, self.sigma0, options)

        # 主优化循环
        iteration = 0
        while not es.stop():
            solutions = es.ask()
            fitnesses = []

            for solution in solutions:
                params = {name: value for name, value in zip(param_names, solution)}

                start_time = time.time()
                result = self.evaluate_func(params)
                value = self.objective.evaluate(result)
                elapsed = time.time() - start_time

                self.history.append((params.copy(), value))
                fitnesses.append(-value)  # CMA-ES 最小化

                if verbose and len(self.history) % 5 == 0:
                    best_so_far = max(v for _, v in self.history)
                    print(
                        f"[{len(self.history)}/{budget}] "
                        f"value={value:.4f}, best={best_so_far:.4f} ({elapsed:.2f}s)"
                    )

            es.tell(solutions, fitnesses)
            iteration += 1

            if len(self.history) >= budget:
                break

        # 找到最优解
        best_idx = np.argmax([value for _, value in self.history])
        best_params = self.history[best_idx][0]
        best_value = self.history[best_idx][1]

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
                "optimizer": "CMAES",
                "sigma0": self.sigma0,
                "objective": self.objective.name,
            },
        )
