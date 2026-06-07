"""灵敏度分析。

评估参数对系统行为的影响程度：
- Sobol 指数：全局灵敏度分析
- Morris 方法：参数筛选
- 偏相关分析：线性相关性
"""

from __future__ import annotations

from typing import Any, Callable

import numpy as np
from SALib.analyze import morris as morris_analyze
from SALib.analyze import sobol as sobol_analyze
from SALib.sample import morris as morris_sample
from SALib.sample import saltelli


class SensitivityAnalyzer:
    """灵敏度分析器。"""

    def __init__(self, param_names: list[str], param_bounds: list[tuple[float, float]]):
        """
        Args:
            param_names: 参数名称列表
            param_bounds: 参数边界列表 [(min, max), ...]
        """
        self.param_names = param_names
        self.param_bounds = param_bounds
        self.n_params = len(param_names)

        # SALib 问题定义
        self.problem = {
            "num_vars": self.n_params,
            "names": param_names,
            "bounds": param_bounds,
        }

    def sobol_analysis(
        self,
        objective_func: Callable[[dict[str, float]], float],
        n_samples: int = 1024,
        calc_second_order: bool = True,
        seed: int | None = None,
    ) -> dict[str, Any]:
        """Sobol 全局灵敏度分析。

        计算一阶和总阶 Sobol 指数：
        - S1: 一阶效应（单参数独立影响）
        - ST: 总阶效应（包含交互作用）
        - S2: 二阶交互效应（可选）

        Args:
            objective_func: 目标函数 func(param_dict) -> float
            n_samples: 基础样本数（实际评估数 = n_samples * (2D + 2)）
            calc_second_order: 是否计算二阶交互
            seed: 随机种子

        Returns:
            结果字典，包含：
            - S1: 一阶指数
            - ST: 总阶指数
            - S2: 二阶指数（如果 calc_second_order=True）
            - samples: 采样点
            - objectives: 目标函数值
        """
        # Saltelli 采样（Sobol 序列）
        # Note: SALib uses different random_state parameter naming
        if seed is not None:
            np.random.seed(seed)
        param_values = saltelli.sample(
            self.problem, n_samples, calc_second_order=calc_second_order
        )

        # 评估目标函数
        n_evals = param_values.shape[0]
        objectives = np.zeros(n_evals)

        for i in range(n_evals):
            param_dict = {name: float(param_values[i, j]) for j, name in enumerate(self.param_names)}
            objectives[i] = objective_func(param_dict)

        # Sobol 分析
        Si = sobol_analyze.analyze(
            self.problem, objectives, calc_second_order=calc_second_order, print_to_console=False
        )

        # 组织结果
        results = {
            "S1": Si["S1"],  # 一阶指数
            "S1_conf": Si["S1_conf"],  # 置信区间
            "ST": Si["ST"],  # 总阶指数
            "ST_conf": Si["ST_conf"],
            "param_names": self.param_names,
            "samples": param_values,
            "objectives": objectives,
            "n_evals": n_evals,
        }

        if calc_second_order:
            results["S2"] = Si["S2"]  # 二阶交互指数
            results["S2_conf"] = Si["S2_conf"]

        return results

    def morris_screening(
        self,
        objective_func: Callable[[dict[str, float]], float],
        n_trajectories: int = 10,
        n_levels: int = 4,
        seed: int | None = None,
    ) -> dict[str, Any]:
        """Morris 方法（参数筛选）。

        快速识别重要参数：
        - μ: 平均效应（参数影响大小）
        - σ: 标准差（非线性/交互作用）
        - μ*: 绝对平均效应（考虑符号）

        Args:
            objective_func: 目标函数 func(param_dict) -> float
            n_trajectories: 轨迹数（越多越精确）
            n_levels: 离散化水平数
            seed: 随机种子

        Returns:
            结果字典，包含：
            - mu: 平均效应
            - mu_star: 绝对平均效应
            - sigma: 标准差
            - mu_star_conf: 置信区间
        """
        # Morris 采样
        if seed is not None:
            np.random.seed(seed)
        param_values = morris_sample.sample(
            self.problem, N=n_trajectories, num_levels=n_levels
        )

        # 评估目标函数
        n_evals = param_values.shape[0]
        objectives = np.zeros(n_evals)

        for i in range(n_evals):
            param_dict = {name: float(param_values[i, j]) for j, name in enumerate(self.param_names)}
            objectives[i] = objective_func(param_dict)

        # Morris 分析
        Si = morris_analyze.analyze(self.problem, param_values, objectives, print_to_console=False)

        results = {
            "mu": Si["mu"],  # 平均效应
            "mu_star": Si["mu_star"],  # 绝对平均效应
            "sigma": Si["sigma"],  # 标准差
            "mu_star_conf": Si["mu_star_conf"],  # 置信区间
            "param_names": self.param_names,
            "samples": param_values,
            "objectives": objectives,
            "n_evals": n_evals,
        }

        return results

    def partial_correlation(self, X: np.ndarray, y: np.ndarray) -> dict[str, Any]:
        """偏相关分析。

        计算每个参数与响应的相关性（控制其他参数）。

        Args:
            X: (n_samples, n_params) 参数矩阵
            y: (n_samples,) 响应值

        Returns:
            结果字典，包含：
            - pearson: Pearson 相关系数
            - spearman: Spearman 秩相关系数
        """
        from scipy.stats import pearsonr, spearmanr

        n_params = X.shape[1]
        pearson_corr = np.zeros(n_params)
        pearson_pval = np.zeros(n_params)
        spearman_corr = np.zeros(n_params)
        spearman_pval = np.zeros(n_params)

        for i in range(n_params):
            # Pearson 相关（线性）
            corr, pval = pearsonr(X[:, i], y)
            pearson_corr[i] = corr
            pearson_pval[i] = pval

            # Spearman 秩相关（单调）
            corr, pval = spearmanr(X[:, i], y)
            spearman_corr[i] = corr
            spearman_pval[i] = pval

        results = {
            "pearson_corr": pearson_corr,
            "pearson_pval": pearson_pval,
            "spearman_corr": spearman_corr,
            "spearman_pval": spearman_pval,
            "param_names": self.param_names,
        }

        return results

    def rank_parameters(self, results: dict[str, Any], method: str = "sobol") -> list[tuple[str, float]]:
        """根据灵敏度分析结果排序参数。

        Args:
            results: 分析结果（来自 sobol_analysis 或 morris_screening）
            method: 排序方法 ("sobol", "morris", "pearson")

        Returns:
            (参数名, 重要性分数) 列表，按重要性降序排列
        """
        if method == "sobol":
            # 使用总阶 Sobol 指数
            scores = results["ST"]
        elif method == "morris":
            # 使用绝对平均效应
            scores = results["mu_star"]
        elif method == "pearson":
            # 使用 Pearson 相关系数绝对值
            scores = np.abs(results["pearson_corr"])
        else:
            raise ValueError(f"Unknown method: {method}")

        param_names = results["param_names"]
        ranked = sorted(zip(param_names, scores), key=lambda x: abs(x[1]), reverse=True)

        return ranked

    def interaction_matrix(self, results: dict[str, Any]) -> np.ndarray | None:
        """提取二阶交互矩阵（仅适用于 Sobol 分析）。

        Args:
            results: sobol_analysis 返回的结果

        Returns:
            (n_params, n_params) 交互矩阵，或 None（如果未计算二阶）
        """
        if "S2" not in results:
            return None

        S2 = results["S2"]
        n_params = len(results["param_names"])
        interaction = np.zeros((n_params, n_params))

        # S2 是上三角矩阵的展开
        idx = 0
        for i in range(n_params):
            for j in range(i + 1, n_params):
                # Handle both array and scalar values
                value = float(S2[idx]) if hasattr(S2[idx], '__iter__') else S2[idx]
                interaction[i, j] = value
                interaction[j, i] = value  # 对称
                idx += 1

        return interaction


def quick_sensitivity_screening(
    param_names: list[str],
    param_bounds: list[tuple[float, float]],
    objective_func: Callable[[dict[str, float]], float],
    n_trajectories: int = 20,
    seed: int | None = None,
) -> dict[str, Any]:
    """快速灵敏度筛选（Morris 方法）。

    用于快速识别重要参数，适合高维参数空间的初步分析。

    Args:
        param_names: 参数名称列表
        param_bounds: 参数边界列表
        objective_func: 目标函数
        n_trajectories: Morris 轨迹数
        seed: 随机种子

    Returns:
        Morris 分析结果 + 参数排名
    """
    analyzer = SensitivityAnalyzer(param_names, param_bounds)
    results = analyzer.morris_screening(objective_func, n_trajectories=n_trajectories, seed=seed)
    ranked = analyzer.rank_parameters(results, method="morris")

    results["ranked_params"] = ranked

    return results


def comprehensive_sensitivity_analysis(
    param_names: list[str],
    param_bounds: list[tuple[float, float]],
    objective_func: Callable[[dict[str, float]], float],
    n_sobol_samples: int = 512,
    calc_second_order: bool = True,
    seed: int | None = None,
) -> dict[str, Any]:
    """全面灵敏度分析（Sobol 方法）。

    提供详细的一阶、总阶和二阶交互效应。

    Args:
        param_names: 参数名称列表
        param_bounds: 参数边界列表
        objective_func: 目标函数
        n_sobol_samples: Sobol 基础样本数
        calc_second_order: 是否计算二阶交互
        seed: 随机种子

    Returns:
        Sobol 分析结果 + 参数排名 + 交互矩阵
    """
    analyzer = SensitivityAnalyzer(param_names, param_bounds)
    results = analyzer.sobol_analysis(
        objective_func, n_samples=n_sobol_samples, calc_second_order=calc_second_order, seed=seed
    )
    ranked = analyzer.rank_parameters(results, method="sobol")
    interaction = analyzer.interaction_matrix(results)

    results["ranked_params"] = ranked
    results["interaction_matrix"] = interaction

    return results
