"""响应曲面拟合与建模。

使用多种回归方法拟合参数-性能的关系：
- 高斯过程回归（GPR）：适合小样本，提供不确定性估计
- 多项式拟合：简单快速，适合平滑响应
- 径向基函数（RBF）：适合复杂非线性
"""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy.interpolate import Rbf
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel, Matern, WhiteKernel
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler


class ResponseSurface:
    """响应曲面基类。"""

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        """拟合响应曲面。

        Args:
            X: (n_samples, n_features) 参数矩阵
            y: (n_samples,) 响应值向量
        """
        raise NotImplementedError

    def predict(self, X: np.ndarray) -> np.ndarray:
        """预测响应值。

        Args:
            X: (n_samples, n_features) 参数矩阵

        Returns:
            y_pred: (n_samples,) 预测值
        """
        raise NotImplementedError

    def predict_with_uncertainty(self, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """预测响应值及不确定性（如果模型支持）。

        Args:
            X: (n_samples, n_features) 参数矩阵

        Returns:
            y_pred: (n_samples,) 预测值
            y_std: (n_samples,) 标准差
        """
        y_pred = self.predict(X)
        y_std = np.zeros_like(y_pred)  # 默认无不确定性
        return y_pred, y_std


class GaussianProcessSurface(ResponseSurface):
    """高斯过程回归响应曲面。

    优点：
    - 小样本性能好
    - 提供不确定性估计
    - 适合贝叶斯优化

    缺点：
    - 计算复杂度 O(n³)
    - 大样本时较慢
    """

    def __init__(
        self,
        kernel: str = "matern",
        noise_level: float = 0.1,
        random_state: int | None = None,
    ):
        """
        Args:
            kernel: 核函数类型 ("matern", "rbf", "rq")
            noise_level: 噪声水平（观测噪声方差）
            random_state: 随机种子
        """
        # 构造核函数
        if kernel == "matern":
            base_kernel = ConstantKernel(1.0) * Matern(length_scale=1.0, nu=2.5)
        elif kernel == "rbf":
            base_kernel = ConstantKernel(1.0) * RBF(length_scale=1.0)
        elif kernel == "rq":
            from sklearn.gaussian_process.kernels import RationalQuadratic

            base_kernel = ConstantKernel(1.0) * RationalQuadratic(
                length_scale=1.0, alpha=1.0
            )
        else:
            raise ValueError(f"Unknown kernel: {kernel}")

        # 添加白噪声核
        full_kernel = base_kernel + WhiteKernel(noise_level=noise_level)

        self.gp = GaussianProcessRegressor(
            kernel=full_kernel,
            n_restarts_optimizer=10,
            random_state=random_state,
            normalize_y=True,
        )

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        self.gp.fit(X, y)

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self.gp.predict(X, return_std=False)

    def predict_with_uncertainty(self, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        y_pred, y_std = self.gp.predict(X, return_std=True)
        return y_pred, y_std

    def get_kernel_params(self) -> dict[str, Any]:
        """获取拟合后的核函数参数。"""
        return {"kernel": str(self.gp.kernel_)}


class PolynomialSurface(ResponseSurface):
    """多项式响应曲面。

    优点：
    - 简单快速
    - 可解释性强
    - 适合平滑响应

    缺点：
    - 高阶多项式易过拟合
    - 外推性能差
    """

    def __init__(self, degree: int = 2, interaction_only: bool = False):
        """
        Args:
            degree: 多项式阶数
            interaction_only: 是否仅包含交互项（不含高次单项）
        """
        self.degree = degree
        self.model = make_pipeline(
            PolynomialFeatures(
                degree=degree, interaction_only=interaction_only, include_bias=True
            ),
            StandardScaler(),
            LinearRegression(),
        )

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        self.model.fit(X, y)

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self.model.predict(X)

    def get_coefficients(self) -> dict[str, Any]:
        """获取多项式系数。"""
        lr = self.model.named_steps["linearregression"]
        poly = self.model.named_steps["polynomialfeatures"]
        return {
            "coefficients": lr.coef_,
            "intercept": lr.intercept_,
            "feature_names": poly.get_feature_names_out(),
        }


class RBFSurface(ResponseSurface):
    """径向基函数响应曲面。

    优点：
    - 适合复杂非线性
    - 局部性强
    - 无需梯度

    缺点：
    - 可能过拟合
    - 参数敏感
    """

    def __init__(
        self,
        function: str = "multiquadric",
        epsilon: float | None = None,
        smooth: float = 0.0,
    ):
        """
        Args:
            function: RBF 函数类型 ("multiquadric", "inverse", "gaussian", "linear", "cubic", "quintic", "thin_plate")
            epsilon: RBF 形状参数（None 则自动选择）
            smooth: 平滑参数（0 = 插值，>0 = 近似）
        """
        self.function = function
        self.epsilon = epsilon
        self.smooth = smooth
        self.rbf = None

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        # RBF 需要转置（每行是一个维度）
        X_T = X.T
        self.rbf = Rbf(
            *X_T, y, function=self.function, epsilon=self.epsilon, smooth=self.smooth
        )

    def predict(self, X: np.ndarray) -> np.ndarray:
        if self.rbf is None:
            raise RuntimeError("Model not fitted yet")
        X_T = X.T
        return self.rbf(*X_T)


class EnsembleSurface(ResponseSurface):
    """集成响应曲面（多模型平均）。"""

    def __init__(
        self, models: list[ResponseSurface], weights: list[float] | None = None
    ):
        """
        Args:
            models: 响应曲面模型列表
            weights: 模型权重（None 则等权）
        """
        self.models = models
        self.weights = (
            weights if weights is not None else [1.0 / len(models)] * len(models)
        )

        if len(self.weights) != len(self.models):
            raise ValueError("Number of weights must match number of models")

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        for model in self.models:
            model.fit(X, y)

    def predict(self, X: np.ndarray) -> np.ndarray:
        predictions = np.array([model.predict(X) for model in self.models])
        weights = np.array(self.weights).reshape(-1, 1)
        return (predictions * weights).sum(axis=0)

    def predict_with_uncertainty(self, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        predictions = []
        stds = []
        for model in self.models:
            pred, std = model.predict_with_uncertainty(X)
            predictions.append(pred)
            stds.append(std)

        predictions = np.array(predictions)
        stds = np.array(stds)
        weights = np.array(self.weights).reshape(-1, 1)

        # 加权平均
        y_pred = (predictions * weights).sum(axis=0)
        # 不确定性：模型间方差 + 加权平均的模型内不确定性
        y_std = np.sqrt(
            ((predictions - y_pred) ** 2 * weights).sum(axis=0)
            + (stds**2 * weights).sum(axis=0)
        )

        return y_pred, y_std


def build_response_surface(
    X: np.ndarray, y: np.ndarray, method: str = "gp", **kwargs: Any
) -> ResponseSurface:
    """构建响应曲面的便捷函数。

    Args:
        X: (n_samples, n_features) 参数矩阵
        y: (n_samples,) 响应值向量
        method: 方法类型 ("gp", "polynomial", "rbf", "ensemble")
        **kwargs: 传递给具体模型的参数

    Returns:
        拟合好的响应曲面模型
    """
    if method == "gp":
        model = GaussianProcessSurface(**kwargs)
    elif method == "polynomial":
        model = PolynomialSurface(**kwargs)
    elif method == "rbf":
        model = RBFSurface(**kwargs)
    elif method == "ensemble":
        # 默认集成：GP + 二次多项式 + RBF
        models = [
            GaussianProcessSurface(kernel="matern"),
            PolynomialSurface(degree=2),
            RBFSurface(function="multiquadric"),
        ]
        model = EnsembleSurface(models)
    else:
        raise ValueError(f"Unknown method: {method}")

    model.fit(X, y)
    return model
