"""贝叶斯优化器：使用高斯过程代理模型和采集函数。

推荐用于样本高效的参数调优（每次仿真较耗时的场景）。

依赖：scikit-optimize (skopt)
安装：pip install scikit-optimize
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

try:
    from skopt import gp_minimize
    from skopt.space import Categorical, Integer, Real
    from skopt.utils import use_named_args

    SKOPT_AVAILABLE = True
except ImportError:
    SKOPT_AVAILABLE = False

from ..constraints.parameter_bounds import ParameterSpace, ParameterType
from ..objectives.objective_functions import ObjectiveFunction


@dataclass
class OptimizationResult:
    """优化结果容器。"""

    best_params: dict[str, Any]
    best_value: float
    n_evaluations: int
    convergence_curve: list[float] = field(default_factory=list)
    all_params: list[dict[str, Any]] = field(default_factory=list)
    all_values: list[float] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class BayesianOptimizer:
    """贝叶斯优化器。

    使用高斯过程（GP）建模目标函数，利用 EI（期望改进）或 UCB 采集函数选择下一个采样点。

    优点：
    - 样本高效（适合每次评估耗时的场景）
    - 能处理噪声
    - 自动权衡探索与利用

    Example:
        >>> from auto_optimization import BayesianOptimizer, maximize_distance, ParameterSpace, Parameter
        >>> from auto_optimization.constraints.parameter_bounds import ParameterType
        >>>
        >>> space = ParameterSpace([
        ...     Parameter("k_p", ParameterType.CONTINUOUS, (0.5, 5.0)),
        ...     Parameter("k_d", ParameterType.CONTINUOUS, (0.1, 2.0)),
        ... ])
        >>> optimizer = BayesianOptimizer(
        ...     param_space=space,
        ...     objective=maximize_distance(),
        ...     evaluate_func=my_simulation_function,
        ... )
        >>> result = optimizer.optimize(budget=50)
        >>> print(f"Best params: {result.best_params}")
        >>> print(f"Best value: {result.best_value}")
    """

    def __init__(
        self,
        param_space: ParameterSpace,
        objective: ObjectiveFunction,
        evaluate_func: Callable[[dict[str, Any]], dict[str, Any]],
        acq_func: str = "EI",
        n_initial_points: int = 10,
        random_state: int | None = None,
    ):
        """初始化贝叶斯优化器。

        Args:
            param_space: 参数空间
            objective: 目标函数
            evaluate_func: 评估函数 params -> simulation_result
            acq_func: 采集函数 ("EI", "LCB", "PI")
            n_initial_points: 初始随机采样点数
            random_state: 随机种子
        """
        if not SKOPT_AVAILABLE:
            raise ImportError(
                "scikit-optimize 未安装。请运行: pip install scikit-optimize"
            )

        self.param_space = param_space
        self.objective = objective
        self.evaluate_func = evaluate_func
        self.acq_func = acq_func
        self.n_initial_points = n_initial_points
        self.random_state = random_state

        # 历史记录
        self.history: list[tuple[dict[str, Any], float]] = []

    def optimize(
        self, budget: int = 50, n_calls: int | None = None, verbose: bool = True
    ) -> OptimizationResult:
        """运行贝叶斯优化。

        Args:
            budget: 评估预算（总评估次数）
            n_calls: 优化调用次数（None 则使用 budget）
            verbose: 是否打印进度

        Returns:
            优化结果
        """
        if n_calls is None:
            n_calls = budget

        # 构建 skopt 搜索空间
        dimensions = self._build_skopt_space()
        param_names = self.param_space.get_parameter_names()

        # 定义优化目标（skopt 最小化，所以取负）
        @use_named_args(dimensions)
        def objective_wrapper(**params):
            start_time = time.time()

            # 评估仿真
            result = self.evaluate_func(params)
            value = self.objective.evaluate(result)

            # 记录历史
            self.history.append((params.copy(), value))

            elapsed = time.time() - start_time
            if verbose:
                print(
                    f"[{len(self.history)}/{n_calls}] "
                    f"params={self._format_params(params)} "
                    f"value={value:.4f} ({elapsed:.2f}s)"
                )

            # 返回负值（skopt 最小化）
            return -value

        # 运行优化
        res = gp_minimize(
            objective_wrapper,
            dimensions,
            n_calls=n_calls,
            n_initial_points=self.n_initial_points,
            acq_func=self.acq_func,
            random_state=self.random_state,
        )

        # 构建结果
        best_params_list = res.x
        best_params = {
            name: value for name, value in zip(param_names, best_params_list)
        }
        best_value = -res.fun  # 转回最大化

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
                "optimizer": "BayesianOptimizer",
                "acq_func": self.acq_func,
                "n_initial_points": self.n_initial_points,
                "objective": self.objective.name,
            },
        )

    def _build_skopt_space(self):
        """构建 skopt 搜索空间。"""
        dimensions = []
        for name, param in self.param_space.parameters.items():
            if param.param_type == ParameterType.CONTINUOUS:
                dimensions.append(Real(param.bounds[0], param.bounds[1], name=name))
            elif param.param_type == ParameterType.INTEGER:
                dimensions.append(
                    Integer(int(param.bounds[0]), int(param.bounds[1]), name=name)
                )
            elif param.param_type == ParameterType.CATEGORICAL:
                dimensions.append(Categorical(param.bounds, name=name))
            elif param.param_type == ParameterType.LOG_UNIFORM:
                dimensions.append(
                    Real(
                        param.bounds[0],
                        param.bounds[1],
                        name=name,
                        prior="log-uniform",
                    )
                )
        return dimensions

    def _format_params(self, params: dict[str, Any]) -> str:
        """格式化参数显示。"""
        items = [
            f"{k}={v:.3f}" if isinstance(v, float) else f"{k}={v}"
            for k, v in params.items()
        ]
        return "{" + ", ".join(items) + "}"

    def save_results(self, result: OptimizationResult, filepath: Path) -> None:
        """保存优化结果到 JSON。

        Args:
            result: 优化结果
            filepath: 保存路径
        """
        data = {
            "best_params": result.best_params,
            "best_value": result.best_value,
            "n_evaluations": result.n_evaluations,
            "convergence_curve": result.convergence_curve,
            "all_params": result.all_params,
            "all_values": result.all_values,
            "metadata": result.metadata,
        }
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"结果已保存到: {filepath}")
