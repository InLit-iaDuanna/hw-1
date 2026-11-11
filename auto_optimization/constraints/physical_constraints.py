"""物理约束检查。

确保参数满足物理可行性条件（稳定性、重心高度等）。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Constraint(ABC):
    """约束基类。"""

    @abstractmethod
    def check(self, params: dict[str, Any]) -> tuple[bool, str]:
        """检查约束是否满足。

        Args:
            params: 参数字典

        Returns:
            (是否满足, 描述信息)
        """
        pass


class MassConstraint(Constraint):
    """质量约束：确保所有质量 > 0。"""

    def __init__(self, mass_params: list[str]):
        """初始化质量约束。

        Args:
            mass_params: 质量参数名称列表
        """
        self.mass_params = mass_params

    def check(self, params: dict[str, Any]) -> tuple[bool, str]:
        """检查质量是否为正。"""
        for param in self.mass_params:
            if param in params and params[param] <= 0:
                return False, f"质量参数 {param} 必须 > 0"
        return True, "质量约束满足"


class StiffnessConstraint(Constraint):
    """刚度约束：确保刚度系数 >= 0。"""

    def __init__(self, stiffness_params: list[str]):
        """初始化刚度约束。

        Args:
            stiffness_params: 刚度参数名称列表
        """
        self.stiffness_params = stiffness_params

    def check(self, params: dict[str, Any]) -> tuple[bool, str]:
        """检查刚度是否非负。"""
        for param in self.stiffness_params:
            if param in params and params[param] < 0:
                return False, f"刚度参数 {param} 必须 >= 0"
        return True, "刚度约束满足"


class DampingConstraint(Constraint):
    """阻尼约束：确保阻尼系数 >= 0。"""

    def __init__(self, damping_params: list[str]):
        """初始化阻尼约束。

        Args:
            damping_params: 阻尼参数名称列表
        """
        self.damping_params = damping_params

    def check(self, params: dict[str, Any]) -> tuple[bool, str]:
        """检查阻尼是否非负。"""
        for param in self.damping_params:
            if param in params and params[param] < 0:
                return False, f"阻尼参数 {param} 必须 >= 0"
        return True, "阻尼约束满足"


class PDGainRatioConstraint(Constraint):
    """PD 增益比约束：确保 K_d^2 < 4 * K_p（临界阻尼条件）。"""

    def __init__(self, kp_param: str, kd_param: str):
        """初始化 PD 增益比约束。

        Args:
            kp_param: 比例增益参数名
            kd_param: 微分增益参数名
        """
        self.kp_param = kp_param
        self.kd_param = kd_param

    def check(self, params: dict[str, Any]) -> tuple[bool, str]:
        """检查 PD 增益是否满足稳定性条件。"""
        if self.kp_param in params and self.kd_param in params:
            kp = params[self.kp_param]
            kd = params[self.kd_param]
            if kd * kd >= 4.0 * kp:
                return (
                    False,
                    f"PD 增益不满足稳定性条件: K_d^2 ({kd**2:.3f}) >= 4*K_p ({4*kp:.3f})",
                )
        return True, "PD 增益比约束满足"


class PhysicalConstraints:
    """物理约束集合。

    Example:
        >>> constraints = PhysicalConstraints([
        ...     MassConstraint(["hip_mass", "torso_mass"]),
        ...     StiffnessConstraint(["ankle_stiffness", "knee_stiffness"]),
        ... ])
        >>> is_valid, msg = constraints.check_all({"hip_mass": 5.0, "ankle_stiffness": 0.5})
    """

    def __init__(self, constraints: list[Constraint]):
        """初始化物理约束集合。

        Args:
            constraints: 约束列表
        """
        self.constraints = constraints

    def check_all(self, params: dict[str, Any]) -> tuple[bool, str]:
        """检查所有约束。

        Args:
            params: 参数字典

        Returns:
            (是否所有约束都满足, 描述信息)
        """
        for constraint in self.constraints:
            is_valid, msg = constraint.check(params)
            if not is_valid:
                return False, msg
        return True, "所有物理约束满足"

    def add_constraint(self, constraint: Constraint) -> None:
        """添加新约束。

        Args:
            constraint: 约束对象
        """
        self.constraints.append(constraint)
