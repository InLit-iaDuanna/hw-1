"""参数边界定义和验证。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ParameterType(Enum):
    """参数类型。"""

    CONTINUOUS = "continuous"  # 连续参数
    INTEGER = "integer"  # 整数参数
    CATEGORICAL = "categorical"  # 分类参数
    LOG_UNIFORM = "log_uniform"  # 对数尺度均匀分布


@dataclass
class Parameter:
    """单个参数定义。

    Attributes:
        name: 参数名称
        param_type: 参数类型
        bounds: 参数边界 (min, max) 或分类选项列表
        default: 默认值
        description: 参数描述
    """

    name: str
    param_type: ParameterType
    bounds: tuple[float, float] | list[Any]
    default: float | int | str | None = None
    description: str = ""

    def validate(self, value: Any) -> bool:
        """验证参数值是否在边界内。

        Args:
            value: 参数值

        Returns:
            是否有效
        """
        if self.param_type == ParameterType.CONTINUOUS:
            return (
                isinstance(value, (int, float))
                and self.bounds[0] <= value <= self.bounds[1]
            )
        elif self.param_type == ParameterType.INTEGER:
            return isinstance(value, int) and self.bounds[0] <= value <= self.bounds[1]
        elif self.param_type == ParameterType.CATEGORICAL:
            return value in self.bounds
        elif self.param_type == ParameterType.LOG_UNIFORM:
            return (
                isinstance(value, (int, float))
                and self.bounds[0] <= value <= self.bounds[1]
            )
        return False

    def clip(self, value: Any) -> Any:
        """将参数值裁剪到边界内。

        Args:
            value: 参数值

        Returns:
            裁剪后的值
        """
        if self.param_type in (ParameterType.CONTINUOUS, ParameterType.LOG_UNIFORM):
            return max(self.bounds[0], min(self.bounds[1], float(value)))
        elif self.param_type == ParameterType.INTEGER:
            return max(int(self.bounds[0]), min(int(self.bounds[1]), int(value)))
        elif self.param_type == ParameterType.CATEGORICAL:
            return value if value in self.bounds else self.bounds[0]
        return value


class ParameterSpace:
    """参数空间定义。

    管理多个参数的边界、类型和验证。

    Example:
        >>> space = ParameterSpace([
        ...     Parameter("k_p", ParameterType.CONTINUOUS, (0.5, 5.0), default=2.0),
        ...     Parameter("k_d", ParameterType.CONTINUOUS, (0.1, 2.0), default=0.5),
        ... ])
        >>> space.validate({"k_p": 3.0, "k_d": 0.8})
        True
    """

    def __init__(self, parameters: list[Parameter]):
        """初始化参数空间。

        Args:
            parameters: 参数列表
        """
        self.parameters = {p.name: p for p in parameters}

    def validate(self, params: dict[str, Any]) -> bool:
        """验证参数字典是否有效。

        Args:
            params: 参数字典

        Returns:
            是否所有参数都有效
        """
        for name, value in params.items():
            if name not in self.parameters:
                return False
            if not self.parameters[name].validate(value):
                return False
        return True

    def clip(self, params: dict[str, Any]) -> dict[str, Any]:
        """将参数字典裁剪到边界内。

        Args:
            params: 参数字典

        Returns:
            裁剪后的参数字典
        """
        clipped = {}
        for name, value in params.items():
            if name in self.parameters:
                clipped[name] = self.parameters[name].clip(value)
        return clipped

    def get_bounds(self) -> list[tuple[float, float]]:
        """获取所有连续/整数参数的边界列表（用于优化器）。

        Returns:
            边界列表 [(min1, max1), (min2, max2), ...]
        """
        bounds = []
        for param in self.parameters.values():
            if param.param_type in (
                ParameterType.CONTINUOUS,
                ParameterType.INTEGER,
                ParameterType.LOG_UNIFORM,
            ):
                bounds.append(param.bounds)
        return bounds

    def get_parameter_names(self) -> list[str]:
        """获取所有参数名称（按定义顺序）。

        Returns:
            参数名称列表
        """
        return list(self.parameters.keys())

    def get_defaults(self) -> dict[str, Any]:
        """获取所有参数的默认值。

        Returns:
            默认参数字典
        """
        defaults = {}
        for name, param in self.parameters.items():
            if param.default is not None:
                defaults[name] = param.default
            else:
                # 如果没有默认值，使用中点
                if param.param_type == ParameterType.CONTINUOUS:
                    defaults[name] = (param.bounds[0] + param.bounds[1]) / 2.0
                elif param.param_type == ParameterType.INTEGER:
                    defaults[name] = int((param.bounds[0] + param.bounds[1]) / 2)
                elif param.param_type == ParameterType.CATEGORICAL:
                    defaults[name] = param.bounds[0]
                elif param.param_type == ParameterType.LOG_UNIFORM:
                    import math

                    defaults[name] = math.sqrt(param.bounds[0] * param.bounds[1])
        return defaults
