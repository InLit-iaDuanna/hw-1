"""自动参数优化工具集。

替代手动试错，自动搜索最优控制参数。

支持的优化器：
- 贝叶斯优化（样本高效，推荐）
- 遗传算法（适合离散参数）
- 网格搜索（穷举法）
- 随机搜索（基线方法）
- CMA-ES（适合高维连续优化）

主要功能：
- 单目标优化（最大化距离、最小化 CoT）
- 多目标优化（Pareto 优化）
- 参数约束（边界、物理约束）
- 对比实验（不同算法性能）
"""

from .constraints.parameter_bounds import Parameter, ParameterSpace
from .objectives.objective_functions import (
    combined_objective,
    maximize_distance,
    minimize_cot,
)
from .optimizers.bayesian_optimizer import BayesianOptimizer
from .optimizers.genetic_algorithm import GeneticAlgorithm

__all__ = [
    "maximize_distance",
    "minimize_cot",
    "combined_objective",
    "ParameterSpace",
    "Parameter",
    "BayesianOptimizer",
    "GeneticAlgorithm",
]
