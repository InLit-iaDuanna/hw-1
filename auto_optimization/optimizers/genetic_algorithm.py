"""遗传算法优化器。

适合离散参数优化和多峰目标函数。

依赖：DEAP (Distributed Evolutionary Algorithms in Python)
安装：pip install deap
"""

from __future__ import annotations

import json
import random
import time
from pathlib import Path
from typing import Any, Callable

import numpy as np

try:
    from deap import algorithms, base, creator, tools

    DEAP_AVAILABLE = True
except ImportError:
    DEAP_AVAILABLE = False

from ..constraints.parameter_bounds import ParameterSpace
from ..objectives.objective_functions import ObjectiveFunction


class GeneticAlgorithm:
    """遗传算法优化器。

    使用选择、交叉、变异操作搜索参数空间。

    优点：
    - 适合离散/混合参数空间
    - 全局搜索能力强
    - 可并行评估

    Example:
        >>> from auto_optimization import GeneticAlgorithm, maximize_distance
        >>> from auto_optimization.constraints.parameter_bounds import ParameterSpace, Parameter, ParameterType
        >>>
        >>> space = ParameterSpace([
        ...     Parameter("k_p", ParameterType.CONTINUOUS, (0.5, 5.0)),
        ...     Parameter("k_d", ParameterType.CONTINUOUS, (0.1, 2.0)),
        ... ])
        >>> optimizer = GeneticAlgorithm(
        ...     param_space=space,
        ...     objective=maximize_distance(),
        ...     evaluate_func=my_simulation_function,
        ...     population_size=30,
        ...     n_generations=20,
        ... )
        >>> result = optimizer.optimize()
    """

    def __init__(
        self,
        param_space: ParameterSpace,
        objective: ObjectiveFunction,
        evaluate_func: Callable[[dict[str, Any]], dict[str, Any]],
        population_size: int = 50,
        n_generations: int = 30,
        cx_prob: float = 0.7,
        mut_prob: float = 0.2,
        mutation_strength: float = 0.1,
        tournament_size: int = 3,
        elitism: int = 2,
        random_state: int | None = None,
    ):
        """初始化遗传算法优化器。

        Args:
            param_space: 参数空间
            objective: 目标函数
            evaluate_func: 评估函数 params -> simulation_result
            population_size: 种群大小
            n_generations: 进化代数
            cx_prob: 交叉概率
            mut_prob: 变异概率
            mutation_strength: 变异强度（相对边界范围）
            tournament_size: 锦标赛选择大小
            elitism: 精英保留数量
            random_state: 随机种子
        """
        if not DEAP_AVAILABLE:
            raise ImportError("DEAP 未安装。请运行: pip install deap")

        self.param_space = param_space
        self.objective = objective
        self.evaluate_func = evaluate_func
        self.population_size = population_size
        self.n_generations = n_generations
        self.cx_prob = cx_prob
        self.mut_prob = mut_prob
        self.mutation_strength = mutation_strength
        self.tournament_size = tournament_size
        self.elitism = elitism

        if random_state is not None:
            random.seed(random_state)
            np.random.seed(random_state)

        # 参数名称和边界
        self.param_names = param_space.get_parameter_names()
        self.bounds = param_space.get_bounds()

        # 历史记录
        self.history: list[tuple[dict[str, Any], float]] = []
        self.generation_best: list[float] = []

    def optimize(self, verbose: bool = True):
        """运行遗传算法优化。

        Args:
            verbose: 是否打印进度

        Returns:
            OptimizationResult 对象
        """
        from .bayesian_optimizer import OptimizationResult

        # 设置 DEAP 框架
        self._setup_deap()

        # 创建工具箱
        toolbox = base.Toolbox()

        # 注册个体生成
        toolbox.register("individual", self._create_individual)
        toolbox.register("population", tools.initRepeat, list, toolbox.individual)

        # 注册遗传操作
        toolbox.register("evaluate", self._evaluate_individual)
        toolbox.register("mate", self._crossover)
        toolbox.register("mutate", self._mutate)
        toolbox.register("select", tools.selTournament, tournsize=self.tournament_size)

        # 初始化种群
        population = toolbox.population(n=self.population_size)

        # 统计信息
        stats = tools.Statistics(lambda ind: ind.fitness.values)
        stats.register("max", np.max)
        stats.register("mean", np.mean)
        stats.register("std", np.std)

        # 主进化循环
        for gen in range(self.n_generations):
            # 评估种群
            fitnesses = list(map(toolbox.evaluate, population))
            for ind, fit in zip(population, fitnesses):
                ind.fitness.values = fit

            # 记录本代最优
            best_fitness = max(ind.fitness.values[0] for ind in population)
            self.generation_best.append(best_fitness)

            if verbose:
                record = stats.compile(population)
                print(
                    f"Gen {gen+1}/{self.n_generations}: "
                    f"max={record['max']:.4f}, mean={record['mean']:.4f}, std={record['std']:.4f}"
                )

            # 选择、交叉、变异
            offspring = toolbox.select(population, len(population) - self.elitism)
            offspring = list(map(toolbox.clone, offspring))

            # 交叉
            for child1, child2 in zip(offspring[::2], offspring[1::2]):
                if random.random() < self.cx_prob:
                    toolbox.mate(child1, child2)
                    del child1.fitness.values
                    del child2.fitness.values

            # 变异
            for mutant in offspring:
                if random.random() < self.mut_prob:
                    toolbox.mutate(mutant)
                    del mutant.fitness.values

            # 精英保留
            elites = tools.selBest(population, self.elitism)
            population[:] = offspring + elites

        # 找到最优个体
        best_individual = tools.selBest(population, 1)[0]
        best_params = self._individual_to_params(best_individual)
        best_value = best_individual.fitness.values[0]

        # 收敛曲线（累积最优值）
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
                "optimizer": "GeneticAlgorithm",
                "population_size": self.population_size,
                "n_generations": self.n_generations,
                "cx_prob": self.cx_prob,
                "mut_prob": self.mut_prob,
                "objective": self.objective.name,
            },
        )

    def _setup_deap(self):
        """设置 DEAP 创建者。"""
        # 避免重复定义
        if hasattr(creator, "FitnessMax"):
            del creator.FitnessMax
        if hasattr(creator, "Individual"):
            del creator.Individual

        creator.create("FitnessMax", base.Fitness, weights=(1.0,))
        creator.create("Individual", list, fitness=creator.FitnessMax)

    def _create_individual(self):
        """创建随机个体。"""
        individual = []
        for low, high in self.bounds:
            individual.append(random.uniform(low, high))
        return creator.Individual(individual)

    def _individual_to_params(self, individual) -> dict[str, Any]:
        """将个体转换为参数字典。"""
        return {name: value for name, value in zip(self.param_names, individual)}

    def _evaluate_individual(self, individual):
        """评估个体适应度。"""
        params = self._individual_to_params(individual)

        # 裁剪到边界内
        params = self.param_space.clip(params)

        # 评估仿真
        result = self.evaluate_func(params)
        value = self.objective.evaluate(result)

        # 记录历史
        self.history.append((params.copy(), value))

        return (value,)  # DEAP 需要元组

    def _crossover(self, ind1, ind2):
        """SBX 交叉（模拟二进制交叉）。"""
        eta = 20.0  # 分布指数
        for i in range(len(ind1)):
            if random.random() < 0.5:
                if abs(ind1[i] - ind2[i]) > 1e-14:
                    y1 = min(ind1[i], ind2[i])
                    y2 = max(ind1[i], ind2[i])
                    low, high = self.bounds[i]

                    beta = 1.0 + 2.0 * (y1 - low) / (y2 - y1)
                    alpha = 2.0 - beta ** -(eta + 1.0)
                    u = random.random()
                    if u <= 1.0 / alpha:
                        beta_q = (u * alpha) ** (1.0 / (eta + 1.0))
                    else:
                        beta_q = (1.0 / (2.0 - u * alpha)) ** (1.0 / (eta + 1.0))

                    c1 = 0.5 * (y1 + y2 - beta_q * (y2 - y1))
                    c2 = 0.5 * (y1 + y2 + beta_q * (y2 - y1))

                    ind1[i] = np.clip(c1, low, high)
                    ind2[i] = np.clip(c2, low, high)

        return ind1, ind2

    def _mutate(self, individual):
        """多项式变异。"""
        eta = 20.0  # 分布指数
        for i in range(len(individual)):
            if random.random() < 1.0 / len(individual):
                low, high = self.bounds[i]
                x = individual[i]
                delta_max = high - low

                u = random.random()
                delta_q = 0.0

                if u < 0.5:
                    delta_q = (2.0 * u) ** (1.0 / (eta + 1.0)) - 1.0
                else:
                    delta_q = 1.0 - (2.0 * (1.0 - u)) ** (1.0 / (eta + 1.0))

                x = x + delta_q * delta_max
                individual[i] = np.clip(x, low, high)

        return (individual,)
