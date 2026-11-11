"""目标函数定义。

支持单目标优化（最大化距离、最小化 CoT）和组合目标。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ObjectiveFunction(ABC):
    """目标函数基类。"""

    @abstractmethod
    def evaluate(self, result: dict[str, Any]) -> float:
        """评估目标函数值。

        Args:
            result: 仿真结果字典

        Returns:
            目标函数值（优化器会最大化此值）
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """目标函数名称。"""
        pass


class MaximizeDistance(ObjectiveFunction):
    """最大化前进距离。

    目标：max forward_distance
    """

    def evaluate(self, result: dict[str, Any]) -> float:
        """评估前进距离。

        Args:
            result: 仿真结果，需包含 'forward_distance' 键

        Returns:
            前进距离（失败返回 -1000 惩罚）
        """
        if not result.get("success", False):
            return -1000.0  # 失败惩罚
        return float(result.get("forward_distance", 0.0))

    @property
    def name(self) -> str:
        return "maximize_distance"


class MinimizeCOT(ObjectiveFunction):
    """最小化 Cost of Transport (CoT)。

    目标：min CoT = 正功 / (质量 × 重力加速度 × 前进距离)
    等价于：max -CoT
    """

    def __init__(self, mass: float = 10.0, gravity: float = 9.81):
        """初始化 CoT 目标函数。

        Args:
            mass: 机器人总质量 (kg)
            gravity: 重力加速度 (m/s^2)
        """
        self.mass = mass
        self.gravity = gravity

    def evaluate(self, result: dict[str, Any]) -> float:
        """评估 CoT（返回负值以便最大化）。

        Args:
            result: 仿真结果，需包含 'positive_work', 'forward_distance'

        Returns:
            -CoT（失败返回 -1000 惩罚）
        """
        if not result.get("success", False):
            return -1000.0

        positive_work = float(result.get("positive_work", 0.0))
        distance = float(result.get("forward_distance", 0.0))

        if distance < 0.1:  # 距离太小
            return -1000.0

        cot = positive_work / (self.mass * self.gravity * distance)
        return -cot  # 返回负值以便最大化

    @property
    def name(self) -> str:
        return "minimize_cot"


class CombinedObjective(ObjectiveFunction):
    """组合目标函数。

    将多个目标函数加权组合：
    f = w1 * obj1 + w2 * obj2 + ...
    """

    def __init__(self, objectives: list[tuple[ObjectiveFunction, float]]):
        """初始化组合目标函数。

        Args:
            objectives: [(目标函数, 权重), ...] 列表
        """
        self.objectives = objectives

    def evaluate(self, result: dict[str, Any]) -> float:
        """评估组合目标函数。

        Args:
            result: 仿真结果

        Returns:
            加权组合值
        """
        total = 0.0
        for obj_func, weight in self.objectives:
            total += weight * obj_func.evaluate(result)
        return total

    @property
    def name(self) -> str:
        names = [f"{w:.2f}*{obj.name}" for obj, w in self.objectives]
        return f"combined[{'+'.join(names)}]"


class StabilityMetric(ObjectiveFunction):
    """稳定性指标：最大化连续步数。"""

    def evaluate(self, result: dict[str, Any]) -> float:
        """评估步数。

        Args:
            result: 仿真结果，需包含 'num_touchdowns'

        Returns:
            连续步数
        """
        if not result.get("success", False):
            return -100.0
        return float(result.get("num_touchdowns", 0))

    @property
    def name(self) -> str:
        return "stability_metric"


# 便捷函数


def maximize_distance() -> MaximizeDistance:
    """创建最大化距离目标函数。"""
    return MaximizeDistance()


def minimize_cot(mass: float = 10.0, gravity: float = 9.81) -> MinimizeCOT:
    """创建最小化 CoT 目标函数。"""
    return MinimizeCOT(mass, gravity)


def combined_objective(
    distance_weight: float = 1.0,
    cot_weight: float = 0.0,
    stability_weight: float = 0.0,
    mass: float = 10.0,
) -> CombinedObjective:
    """创建组合目标函数。

    Args:
        distance_weight: 距离权重
        cot_weight: CoT 权重（负值表示最小化）
        stability_weight: 稳定性权重
        mass: 机器人总质量

    Returns:
        组合目标函数

    Example:
        >>> obj = combined_objective(distance_weight=0.7, cot_weight=-0.3)
        >>> # 优化目标：0.7 * distance - 0.3 * CoT
    """
    objectives = []
    if distance_weight != 0:
        objectives.append((MaximizeDistance(), distance_weight))
    if cot_weight != 0:
        objectives.append((MinimizeCOT(mass), cot_weight))
    if stability_weight != 0:
        objectives.append((StabilityMetric(), stability_weight))
    return CombinedObjective(objectives)
