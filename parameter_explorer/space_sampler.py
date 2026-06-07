"""参数空间采样策略。

支持多种采样方法：
- 网格采样（Grid）：均匀覆盖参数空间
- 随机采样（Random）：Monte Carlo 采样
- 拉丁超立方采样（LHS）：更高效的空间覆盖
- 自适应采样（Adaptive）：关注有趣区域
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.stats import qmc


@dataclass
class ParameterRange:
    """单个参数的取值范围。"""

    name: str
    min_value: float
    max_value: float
    log_scale: bool = False  # 是否对数尺度采样
    discrete_values: list[float] | None = None  # 离散值列表（可选）

    def sample(self, n: int, method: str = "uniform") -> np.ndarray:
        """采样 n 个值。"""
        if self.discrete_values is not None:
            # 从离散值中采样
            indices = np.random.choice(len(self.discrete_values), size=n, replace=True)
            return np.array([self.discrete_values[i] for i in indices])

        if method == "uniform":
            if self.log_scale:
                log_min = np.log10(self.min_value)
                log_max = np.log10(self.max_value)
                return 10 ** np.random.uniform(log_min, log_max, size=n)
            else:
                return np.random.uniform(self.min_value, self.max_value, size=n)
        elif method == "linspace":
            if self.log_scale:
                return np.logspace(np.log10(self.min_value), np.log10(self.max_value), n)
            else:
                return np.linspace(self.min_value, self.max_value, n)
        else:
            raise ValueError(f"Unknown sampling method: {method}")

    def normalize(self, value: float) -> float:
        """归一化到 [0, 1]。"""
        if self.log_scale:
            log_min = np.log10(self.min_value)
            log_max = np.log10(self.max_value)
            log_val = np.log10(value)
            return (log_val - log_min) / (log_max - log_min)
        else:
            return (value - self.min_value) / (self.max_value - self.min_value)

    def denormalize(self, normalized: float) -> float:
        """从 [0, 1] 反归一化。"""
        if self.log_scale:
            log_min = np.log10(self.min_value)
            log_max = np.log10(self.max_value)
            log_val = log_min + normalized * (log_max - log_min)
            return 10**log_val
        else:
            return self.min_value + normalized * (self.max_value - self.min_value)


class SpaceSampler:
    """参数空间采样器。"""

    def __init__(self, param_ranges: list[ParameterRange]):
        """
        Args:
            param_ranges: 参数范围列表
        """
        self.param_ranges = param_ranges
        self.param_names = [p.name for p in param_ranges]
        self.n_params = len(param_ranges)

    def grid_sample(self, n_per_dim: int) -> tuple[np.ndarray, list[dict[str, float]]]:
        """网格采样（均匀覆盖）。

        Args:
            n_per_dim: 每个维度的采样点数

        Returns:
            samples: (n_samples, n_params) 数组
            param_dicts: 参数字典列表
        """
        # 为每个参数生成等间隔点
        grids = []
        for param in self.param_ranges:
            if param.discrete_values is not None:
                grids.append(np.array(param.discrete_values))
            else:
                grids.append(param.sample(n_per_dim, method="linspace"))

        # 生成网格
        mesh = np.meshgrid(*grids, indexing="ij")
        samples = np.column_stack([m.ravel() for m in mesh])

        # 转换为字典列表
        param_dicts = [
            {name: float(samples[i, j]) for j, name in enumerate(self.param_names)}
            for i in range(len(samples))
        ]

        return samples, param_dicts

    def random_sample(self, n_samples: int, seed: int | None = None) -> tuple[np.ndarray, list[dict[str, float]]]:
        """随机采样（Monte Carlo）。

        Args:
            n_samples: 采样点数
            seed: 随机种子

        Returns:
            samples: (n_samples, n_params) 数组
            param_dicts: 参数字典列表
        """
        if seed is not None:
            np.random.seed(seed)

        samples = np.zeros((n_samples, self.n_params))
        for i, param in enumerate(self.param_ranges):
            samples[:, i] = param.sample(n_samples, method="uniform")

        param_dicts = [
            {name: float(samples[i, j]) for j, name in enumerate(self.param_names)}
            for i in range(n_samples)
        ]

        return samples, param_dicts

    def lhs_sample(self, n_samples: int, seed: int | None = None) -> tuple[np.ndarray, list[dict[str, float]]]:
        """拉丁超立方采样（LHS）。

        更高效的空间覆盖，适合高维参数空间。

        Args:
            n_samples: 采样点数
            seed: 随机种子

        Returns:
            samples: (n_samples, n_params) 数组
            param_dicts: 参数字典列表
        """
        # 使用 scipy 的 LHS 采样器
        sampler = qmc.LatinHypercube(d=self.n_params, seed=seed)
        normalized_samples = sampler.random(n=n_samples)

        # 反归一化到实际参数范围
        samples = np.zeros_like(normalized_samples)
        for i, param in enumerate(self.param_ranges):
            samples[:, i] = np.array([param.denormalize(x) for x in normalized_samples[:, i]])

        param_dicts = [
            {name: float(samples[i, j]) for j, name in enumerate(self.param_names)}
            for i in range(n_samples)
        ]

        return samples, param_dicts

    def sobol_sample(self, n_samples: int, seed: int | None = None) -> tuple[np.ndarray, list[dict[str, float]]]:
        """Sobol 序列采样（低差异序列）。

        比 LHS 更均匀的空间填充，适合灵敏度分析。

        Args:
            n_samples: 采样点数（建议使用 2^n）
            seed: 随机种子

        Returns:
            samples: (n_samples, n_params) 数组
            param_dicts: 参数字典列表
        """
        sampler = qmc.Sobol(d=self.n_params, scramble=True, seed=seed)
        normalized_samples = sampler.random(n=n_samples)

        samples = np.zeros_like(normalized_samples)
        for i, param in enumerate(self.param_ranges):
            samples[:, i] = np.array([param.denormalize(x) for x in normalized_samples[:, i]])

        param_dicts = [
            {name: float(samples[i, j]) for j, name in enumerate(self.param_names)}
            for i in range(n_samples)
        ]

        return samples, param_dicts

    def adaptive_sample(
        self,
        objective_func: Any,
        n_initial: int,
        n_adaptive: int,
        exploit_ratio: float = 0.5,
        seed: int | None = None,
    ) -> tuple[np.ndarray, list[dict[str, float]], np.ndarray]:
        """自适应采样（关注有趣区域）。

        先用 LHS 初始采样，然后根据目标函数值决定后续采样位置：
        - exploit_ratio 比例的样本在已知高值区域附近
        - 其余样本继续探索未知区域

        Args:
            objective_func: 目标函数 func(param_dict) -> float
            n_initial: 初始 LHS 采样数
            n_adaptive: 自适应采样数
            exploit_ratio: 利用已知高值区域的比例
            seed: 随机种子

        Returns:
            samples: (n_initial + n_adaptive, n_params) 数组
            param_dicts: 参数字典列表
            objectives: 目标函数值数组
        """
        # 初始 LHS 采样
        samples, param_dicts = self.lhs_sample(n_initial, seed=seed)
        objectives = np.array([objective_func(pd) for pd in param_dicts])

        # 自适应采样
        n_exploit = int(n_adaptive * exploit_ratio)
        n_explore = n_adaptive - n_exploit

        for _ in range(n_adaptive):
            if np.random.rand() < exploit_ratio and len(objectives) > 0:
                # Exploit: 在高值区域附近采样
                top_k = min(5, len(objectives))
                top_indices = np.argsort(objectives)[-top_k:]
                center_idx = np.random.choice(top_indices)
                center = samples[center_idx]

                # 在中心附近添加高斯噪声
                noise = np.random.randn(self.n_params) * 0.1
                new_sample_normalized = np.zeros(self.n_params)
                for i, param in enumerate(self.param_ranges):
                    center_norm = param.normalize(center[i])
                    new_norm = np.clip(center_norm + noise[i], 0, 1)
                    new_sample_normalized[i] = param.denormalize(new_norm)
            else:
                # Explore: 随机采样
                new_sample_normalized = np.zeros(self.n_params)
                for i, param in enumerate(self.param_ranges):
                    new_sample_normalized[i] = param.sample(1, method="uniform")[0]

            # 评估新样本
            new_sample = new_sample_normalized.reshape(1, -1)
            new_dict = {name: float(new_sample[0, j]) for j, name in enumerate(self.param_names)}
            new_obj = objective_func(new_dict)

            samples = np.vstack([samples, new_sample])
            param_dicts.append(new_dict)
            objectives = np.append(objectives, new_obj)

        return samples, param_dicts, objectives

    def normalize_samples(self, samples: np.ndarray) -> np.ndarray:
        """归一化样本到 [0, 1]^n。"""
        normalized = np.zeros_like(samples)
        for i, param in enumerate(self.param_ranges):
            normalized[:, i] = [param.normalize(x) for x in samples[:, i]]
        return normalized

    def denormalize_samples(self, normalized_samples: np.ndarray) -> np.ndarray:
        """从 [0, 1]^n 反归一化。"""
        samples = np.zeros_like(normalized_samples)
        for i, param in enumerate(self.param_ranges):
            samples[:, i] = [param.denormalize(x) for x in normalized_samples[:, i]]
        return samples
