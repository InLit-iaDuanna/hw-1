"""多目标优化：Pareto 前沿搜索。

支持多个相互冲突的目标（如距离 vs CoT）。
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field
from typing import Any, Callable

from .objective_functions import ObjectiveFunction


@dataclass
class ParetoSolution:
    """Pareto 解。"""

    params: dict[str, Any]
    objectives: list[float]  # [obj1, obj2, ...]
    metadata: dict[str, Any] = field(default_factory=dict)


class ParetoFront:
    """Pareto 前沿管理。

    维护非支配解集合。
    """

    def __init__(self):
        """初始化 Pareto 前沿。"""
        self.solutions: list[ParetoSolution] = []

    def add_solution(self, solution: ParetoSolution) -> bool:
        """添加解到 Pareto 前沿。

        Args:
            solution: 候选解

        Returns:
            是否添加成功（即解是非支配的）
        """
        # 检查是否被现有解支配
        is_dominated = False
        to_remove = []

        for i, existing in enumerate(self.solutions):
            if self._dominates(existing.objectives, solution.objectives):
                is_dominated = True
                break
            elif self._dominates(solution.objectives, existing.objectives):
                to_remove.append(i)

        if is_dominated:
            return False

        # 移除被新解支配的解
        for i in reversed(to_remove):
            self.solutions.pop(i)

        self.solutions.append(solution)
        return True

    def _dominates(self, obj1: list[float], obj2: list[float]) -> bool:
        """检查 obj1 是否支配 obj2（假设最大化所有目标）。

        Args:
            obj1: 目标值列表 1
            obj2: 目标值列表 2

        Returns:
            obj1 是否支配 obj2
        """
        better_in_all = all(o1 >= o2 for o1, o2 in zip(obj1, obj2))
        better_in_one = any(o1 > o2 for o1, o2 in zip(obj1, obj2))
        return better_in_all and better_in_one

    def get_solutions(self) -> list[ParetoSolution]:
        """获取所有 Pareto 最优解。"""
        return self.solutions

    def get_best_by_objective(self, objective_index: int) -> ParetoSolution | None:
        """获取某个目标最优的解。

        Args:
            objective_index: 目标索引（0 开始）

        Returns:
            最优解，如果前沿为空则返回 None
        """
        if not self.solutions:
            return None
        return max(self.solutions, key=lambda s: s.objectives[objective_index])


class MultiObjectiveOptimizer:
    """多目标优化器（NSGA-II 风格）。

    Example:
        >>> from auto_optimization.objectives import maximize_distance, minimize_cot
        >>> objectives = [maximize_distance(), minimize_cot(mass=10.0)]
        >>> optimizer = MultiObjectiveOptimizer(objectives, simulate_func)
        >>> pareto_front = optimizer.optimize(param_space, budget=100)
    """

    def __init__(
        self,
        objectives: list[ObjectiveFunction],
        evaluate_func: Callable[[dict[str, Any]], dict[str, Any]],
    ):
        """初始化多目标优化器。

        Args:
            objectives: 目标函数列表
            evaluate_func: 评估函数 params -> result
        """
        self.objectives = objectives
        self.evaluate_func = evaluate_func

    def evaluate_objectives(self, result: dict[str, Any]) -> list[float]:
        """评估所有目标函数。

        Args:
            result: 仿真结果

        Returns:
            目标值列表
        """
        return [obj.evaluate(result) for obj in self.objectives]

    def optimize(
        self,
        param_space: Any,
        budget: int = 100,
        population_size: int = 20,
        mutation_rate: float = 0.1,
        crossover_rate: float = 0.8,
    ) -> ParetoFront:
        """运行多目标优化（简化 NSGA-II）。

        Args:
            param_space: 参数空间
            budget: 评估预算
            population_size: 种群大小
            mutation_rate: 变异率
            crossover_rate: 交叉率

        Returns:
            Pareto 前沿
        """
        pareto_front = ParetoFront()
        population = self._initialize_population(param_space, population_size)
        evaluations = 0

        while evaluations < budget:
            # 评估当前种群
            for individual in population:
                if evaluations >= budget:
                    break
                result = self.evaluate_func(individual)
                objectives = self.evaluate_objectives(result)
                solution = ParetoSolution(individual.copy(), objectives)
                pareto_front.add_solution(solution)
                evaluations += 1

            if evaluations >= budget:
                break

            # 选择、交叉、变异（简化实现）
            population = self._evolve_population(
                population, pareto_front, param_space, mutation_rate, crossover_rate
            )

        return pareto_front

    def _initialize_population(
        self, param_space: Any, size: int
    ) -> list[dict[str, Any]]:
        """初始化随机种群。"""
        population = []
        bounds = param_space.get_bounds()
        names = param_space.get_parameter_names()

        for _ in range(size):
            individual = {}
            for name, (low, high) in zip(names, bounds):
                individual[name] = np.random.uniform(low, high)
            population.append(individual)

        return population

    def _evolve_population(
        self,
        population: list[dict[str, Any]],
        pareto_front: ParetoFront,
        param_space: Any,
        mutation_rate: float,
        crossover_rate: float,
    ) -> list[dict[str, Any]]:
        """进化种群（简化实现）。"""
        # 从 Pareto 前沿选择精英个体
        elite = [s.params for s in pareto_front.get_solutions()[: len(population) // 2]]

        # 随机扰动生成新个体
        new_population = elite.copy()
        bounds = param_space.get_bounds()
        names = param_space.get_parameter_names()

        while len(new_population) < len(population):
            parent = elite[np.random.randint(len(elite))].copy()
            for name, (low, high) in zip(names, bounds):
                if np.random.rand() < mutation_rate:
                    parent[name] = np.random.uniform(low, high)
            new_population.append(parent)

        return new_population
