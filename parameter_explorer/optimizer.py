"""自动优化算法。

支持多种优化策略：
- 贝叶斯优化：高效的黑盒优化
- 遗传算法：全局搜索，适合多峰
- 梯度自由优化：Nelder-Mead、Powell
- 多目标优化：Pareto 前沿
"""

from __future__ import annotations

from typing import Any, Callable

import numpy as np
from scipy.optimize import differential_evolution, minimize
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, Matern


class Optimizer:
    """优化器基类。"""

    def __init__(self, param_names: list[str], param_bounds: list[tuple[float, float]]):
        """
        Args:
            param_names: 参数名称列表
            param_bounds: 参数边界列表 [(min, max), ...]
        """
        self.param_names = param_names
        self.param_bounds = param_bounds
        self.n_params = len(param_names)

    def array_to_dict(self, x: np.ndarray) -> dict[str, float]:
        """将参数数组转换为字典。"""
        return {name: float(x[i]) for i, name in enumerate(self.param_names)}

    def dict_to_array(self, param_dict: dict[str, float]) -> np.ndarray:
        """将参数字典转换为数组。"""
        return np.array([param_dict[name] for name in self.param_names])


class BayesianOptimizer(Optimizer):
    """贝叶斯优化器。

    使用高斯过程建模目标函数，通过采集函数平衡探索与利用。

    优点：
    - 样本效率高（适合昂贵的目标函数）
    - 自适应采样
    - 提供不确定性估计

    缺点：
    - 高维时性能下降（D > 20）
    - 计算开销较大
    """

    def __init__(
        self,
        param_names: list[str],
        param_bounds: list[tuple[float, float]],
        acquisition: str = "ei",
        xi: float = 0.01,
        kappa: float = 2.576,
        random_state: int | None = None,
    ):
        """
        Args:
            param_names: 参数名称列表
            param_bounds: 参数边界列表
            acquisition: 采集函数 ("ei"=期望改进, "ucb"=置信上界, "poi"=改进概率)
            xi: EI/POI 的探索参数
            kappa: UCB 的探索参数
            random_state: 随机种子
        """
        super().__init__(param_names, param_bounds)
        self.acquisition = acquisition
        self.xi = xi
        self.kappa = kappa
        self.random_state = random_state

        # 高斯过程模型
        kernel = ConstantKernel(1.0) * Matern(length_scale=1.0, nu=2.5)
        self.gp = GaussianProcessRegressor(
            kernel=kernel, n_restarts_optimizer=10, random_state=random_state, normalize_y=True
        )

        # 历史数据
        self.X_observed: list[np.ndarray] = []
        self.y_observed: list[float] = []

    def _acquisition_function(self, X: np.ndarray) -> np.ndarray:
        """计算采集函数值（负值，因为要最小化）。"""
        if len(self.y_observed) == 0:
            return np.zeros(len(X))

        mu, sigma = self.gp.predict(X, return_std=True)
        sigma = np.maximum(sigma, 1e-9)  # 避免除零

        if self.acquisition == "ei":
            # Expected Improvement
            y_best = np.max(self.y_observed)
            Z = (mu - y_best - self.xi) / sigma
            ei = (mu - y_best - self.xi) * self._norm_cdf(Z) + sigma * self._norm_pdf(Z)
            return -ei  # 负号，因为要最大化 EI

        elif self.acquisition == "ucb":
            # Upper Confidence Bound
            ucb = mu + self.kappa * sigma
            return -ucb

        elif self.acquisition == "poi":
            # Probability of Improvement
            y_best = np.max(self.y_observed)
            Z = (mu - y_best - self.xi) / sigma
            poi = self._norm_cdf(Z)
            return -poi

        else:
            raise ValueError(f"Unknown acquisition function: {self.acquisition}")

    @staticmethod
    def _norm_pdf(x: np.ndarray) -> np.ndarray:
        """标准正态分布 PDF。"""
        return np.exp(-0.5 * x**2) / np.sqrt(2 * np.pi)

    @staticmethod
    def _norm_cdf(x: np.ndarray) -> np.ndarray:
        """标准正态分布 CDF。"""
        from scipy.stats import norm

        return norm.cdf(x)

    def optimize(
        self,
        objective_func: Callable[[dict[str, float]], float],
        n_initial: int = 10,
        n_iterations: int = 50,
        verbose: bool = True,
    ) -> dict[str, Any]:
        """执行贝叶斯优化。

        Args:
            objective_func: 目标函数（要最大化）
            n_initial: 初始随机样本数
            n_iterations: 优化迭代次数
            verbose: 是否打印进度

        Returns:
            结果字典，包含：
            - best_params: 最优参数字典
            - best_value: 最优值
            - all_params: 所有评估的参数
            - all_values: 所有评估的值
        """
        # 初始随机采样
        np.random.seed(self.random_state)
        for i in range(n_initial):
            x = np.array(
                [np.random.uniform(low, high) for low, high in self.param_bounds]
            )
            param_dict = self.array_to_dict(x)
            y = objective_func(param_dict)

            self.X_observed.append(x)
            self.y_observed.append(y)

            if verbose:
                print(f"Initial {i+1}/{n_initial}: y = {y:.4f}")

        # 贝叶斯优化迭代
        for iteration in range(n_iterations):
            # 用观测数据更新 GP
            X_train = np.array(self.X_observed)
            y_train = np.array(self.y_observed)
            self.gp.fit(X_train, y_train)

            # 最大化采集函数（通过最小化负采集函数）
            x_best_acq = None
            y_best_acq = np.inf

            for _ in range(10):  # 多次随机初始化
                x0 = np.array(
                    [np.random.uniform(low, high) for low, high in self.param_bounds]
                )
                result = minimize(
                    lambda x: self._acquisition_function(x.reshape(1, -1))[0],
                    x0,
                    bounds=self.param_bounds,
                    method="L-BFGS-B",
                )
                if result.fun < y_best_acq:
                    y_best_acq = result.fun
                    x_best_acq = result.x

            # 评估新点
            param_dict = self.array_to_dict(x_best_acq)
            y_new = objective_func(param_dict)

            self.X_observed.append(x_best_acq)
            self.y_observed.append(y_new)

            if verbose:
                y_best_so_far = np.max(self.y_observed)
                print(f"Iteration {iteration+1}/{n_iterations}: y = {y_new:.4f}, best = {y_best_so_far:.4f}")

        # 返回结果
        best_idx = np.argmax(self.y_observed)
        best_x = self.X_observed[best_idx]
        best_y = self.y_observed[best_idx]

        return {
            "best_params": self.array_to_dict(best_x),
            "best_value": best_y,
            "all_params": [self.array_to_dict(x) for x in self.X_observed],
            "all_values": self.y_observed,
            "n_evaluations": len(self.y_observed),
        }


class GeneticAlgorithmOptimizer(Optimizer):
    """遗传算法优化器。

    优点：
    - 全局搜索能力强
    - 适合多峰、非凸问题
    - 并行化友好

    缺点：
    - 收敛较慢
    - 需要较多评估次数
    """

    def __init__(
        self,
        param_names: list[str],
        param_bounds: list[tuple[float, float]],
        population_size: int = 50,
        mutation: float = 0.5,
        recombination: float = 0.7,
        seed: int | None = None,
    ):
        """
        Args:
            param_names: 参数名称列表
            param_bounds: 参数边界列表
            population_size: 种群大小
            mutation: 变异率
            recombination: 交叉率
            seed: 随机种子
        """
        super().__init__(param_names, param_bounds)
        self.population_size = population_size
        self.mutation = mutation
        self.recombination = recombination
        self.seed = seed

    def optimize(
        self,
        objective_func: Callable[[dict[str, float]], float],
        max_generations: int = 100,
        tol: float = 1e-6,
        verbose: bool = True,
    ) -> dict[str, Any]:
        """执行遗传算法优化。

        Args:
            objective_func: 目标函数（要最大化）
            max_generations: 最大代数
            tol: 收敛容差
            verbose: 是否打印进度

        Returns:
            结果字典
        """

        def neg_objective(x: np.ndarray) -> float:
            """负目标函数（scipy 的 differential_evolution 是最小化）。"""
            param_dict = self.array_to_dict(x)
            return -objective_func(param_dict)

        # 使用 scipy 的 differential_evolution
        result = differential_evolution(
            neg_objective,
            bounds=self.param_bounds,
            strategy="best1bin",
            maxiter=max_generations,
            popsize=self.population_size,
            tol=tol,
            mutation=self.mutation,
            recombination=self.recombination,
            seed=self.seed,
            disp=verbose,
            polish=True,  # 最后用局部优化细化
        )

        return {
            "best_params": self.array_to_dict(result.x),
            "best_value": -result.fun,  # 转回最大化
            "n_evaluations": result.nfev,
            "success": result.success,
            "message": result.message,
        }


class NelderMeadOptimizer(Optimizer):
    """Nelder-Mead 梯度自由优化器。

    优点：
    - 无需梯度
    - 实现简单
    - 适合中小规模问题

    缺点：
    - 易陷入局部最优
    - 高维性能差
    """

    def optimize(
        self,
        objective_func: Callable[[dict[str, float]], float],
        x0: dict[str, float] | None = None,
        max_iterations: int = 1000,
        verbose: bool = True,
    ) -> dict[str, Any]:
        """执行 Nelder-Mead 优化。

        Args:
            objective_func: 目标函数（要最大化）
            x0: 初始参数（None 则随机选择）
            max_iterations: 最大迭代次数
            verbose: 是否打印进度

        Returns:
            结果字典
        """
        if x0 is None:
            x0_array = np.array(
                [np.random.uniform(low, high) for low, high in self.param_bounds]
            )
        else:
            x0_array = self.dict_to_array(x0)

        def neg_objective(x: np.ndarray) -> float:
            """负目标函数。"""
            param_dict = self.array_to_dict(x)
            return -objective_func(param_dict)

        result = minimize(
            neg_objective,
            x0_array,
            method="Nelder-Mead",
            bounds=self.param_bounds,
            options={"maxiter": max_iterations, "disp": verbose},
        )

        return {
            "best_params": self.array_to_dict(result.x),
            "best_value": -result.fun,
            "n_evaluations": result.nfev,
            "success": result.success,
            "message": result.message,
        }


class MultiObjectiveOptimizer(Optimizer):
    """多目标优化器（NSGA-II）。

    用于同时优化多个目标（如最大化距离 + 最小化能耗）。
    """

    def __init__(
        self,
        param_names: list[str],
        param_bounds: list[tuple[float, float]],
        n_objectives: int = 2,
        population_size: int = 100,
        seed: int | None = None,
    ):
        """
        Args:
            param_names: 参数名称列表
            param_bounds: 参数边界列表
            n_objectives: 目标数量
            population_size: 种群大小
            seed: 随机种子
        """
        super().__init__(param_names, param_bounds)
        self.n_objectives = n_objectives
        self.population_size = population_size
        self.seed = seed

    def optimize(
        self,
        objective_funcs: list[Callable[[dict[str, float]], float]],
        maximize: list[bool],
        n_generations: int = 100,
        verbose: bool = True,
    ) -> dict[str, Any]:
        """执行多目标优化。

        Args:
            objective_funcs: 目标函数列表
            maximize: 是否最大化（每个目标）
            n_generations: 代数
            verbose: 是否打印进度

        Returns:
            结果字典，包含 Pareto 前沿
        """
        from pymoo.algorithms.moo.nsga2 import NSGA2
        from pymoo.core.problem import Problem
        from pymoo.optimize import minimize as pymoo_minimize

        class MultiObjectiveProblem(Problem):
            def __init__(self, opt: MultiObjectiveOptimizer, funcs: list, maximize_flags: list):
                super().__init__(
                    n_var=opt.n_params,
                    n_obj=len(funcs),
                    xl=np.array([b[0] for b in opt.param_bounds]),
                    xu=np.array([b[1] for b in opt.param_bounds]),
                )
                self.opt = opt
                self.funcs = funcs
                self.maximize_flags = maximize_flags

            def _evaluate(self, X, out, *args, **kwargs):
                objectives = np.zeros((len(X), len(self.funcs)))
                for i, x in enumerate(X):
                    param_dict = self.opt.array_to_dict(x)
                    for j, func in enumerate(self.funcs):
                        obj_value = func(param_dict)
                        # pymoo 是最小化，所以最大化的目标要取负
                        objectives[i, j] = -obj_value if self.maximize_flags[j] else obj_value
                out["F"] = objectives

        problem = MultiObjectiveProblem(self, objective_funcs, maximize)
        algorithm = NSGA2(pop_size=self.population_size)

        result = pymoo_minimize(
            problem,
            algorithm,
            ("n_gen", n_generations),
            seed=self.seed,
            verbose=verbose,
        )

        # 提取 Pareto 前沿
        pareto_X = result.X
        pareto_F = result.F

        # 转回最大化
        for j in range(len(maximize)):
            if maximize[j]:
                pareto_F[:, j] = -pareto_F[:, j]

        pareto_params = [self.array_to_dict(x) for x in pareto_X]

        return {
            "pareto_params": pareto_params,
            "pareto_objectives": pareto_F,
            "n_solutions": len(pareto_params),
            "n_evaluations": result.algorithm.evaluator.n_eval,
        }
