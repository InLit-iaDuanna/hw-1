"""控制器基类与具体实现。

提供统一的控制器接口，支持被动控制（无驱动）和 PD 控制。
用于 hw-1 项目中各版本的控制策略实现。
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np


class Controller(ABC):
    """控制器抽象基类。

    定义统一的控制器接口，所有具体控制器必须实现 compute_torque 方法。
    """

    @abstractmethod
    def compute_torque(
        self,
        q: float,
        qd: float,
        target: float | None = None,
        **kwargs,
    ) -> float:
        """计算控制力矩。

        Args:
            q: 当前关节位置 (rad)
            qd: 当前关节速度 (rad/s)
            target: 目标关节位置 (rad)，对于被动控制器可为 None
            **kwargs: 其他控制参数（如 kp, kd 等）

        Returns:
            控制力矩 (N·m)
        """
        pass

    def reset(self) -> None:
        """重置控制器状态（可选实现）。

        用于有状态的控制器（如积分器、滤波器等）。
        默认实现为空操作。
        """
        pass


class PassiveController(Controller):
    """被动控制器（无驱动）。

    始终输出零力矩，用于模拟被动关节或验证系统的自然动力学行为。

    Examples:
        >>> controller = PassiveController()
        >>> controller.compute_torque(0.1, 0.5)
        0.0
        >>> controller.compute_torque(0.5, -0.2, target=0.0)
        0.0
    """

    def compute_torque(
        self,
        q: float,
        qd: float,
        target: float | None = None,
        **kwargs,
    ) -> float:
        """返回零力矩（无驱动）。

        Args:
            q: 当前关节位置 (rad)，未使用
            qd: 当前关节速度 (rad/s)，未使用
            target: 目标关节位置 (rad)，未使用
            **kwargs: 其他参数，未使用

        Returns:
            0.0
        """
        return 0.0


class PDController(Controller):
    """标准 PD 控制器。

    实现比例-微分（Proportional-Derivative）控制：
        τ = Kp * (target - q) - Kd * qd

    支持可选的力矩限幅。

    Args:
        kp: 比例增益 (N·m/rad)，默认 100.0
        kd: 微分增益 (N·m·s/rad)，默认 10.0
        torque_limit: 力矩限制幅值 (N·m)，None 表示无限制

    Examples:
        >>> controller = PDController(kp=100.0, kd=10.0)
        >>> controller.compute_torque(0.1, 0.0, target=0.0)
        -10.0
        >>> controller.compute_torque(0.0, 1.0, target=0.0)
        -10.0
        >>>
        >>> # 带限幅的控制器
        >>> limited = PDController(kp=200.0, kd=20.0, torque_limit=50.0)
        >>> limited.compute_torque(1.0, 0.0, target=0.0)  # 饱和
        -50.0
    """

    def __init__(
        self,
        kp: float = 100.0,
        kd: float = 10.0,
        torque_limit: float | None = None,
    ) -> None:
        """初始化 PD 控制器。

        Args:
            kp: 比例增益 (N·m/rad)
            kd: 微分增益 (N·m·s/rad)
            torque_limit: 力矩限制幅值 (N·m)，None 表示无限制
        """
        self.kp = kp
        self.kd = kd
        self.torque_limit = torque_limit

    def compute_torque(
        self,
        q: float,
        qd: float,
        target: float | None = None,
        **kwargs,
    ) -> float:
        """计算 PD 控制力矩。

        Args:
            q: 当前关节位置 (rad)
            qd: 当前关节速度 (rad/s)
            target: 目标关节位置 (rad)，必须提供
            **kwargs: 可选的临时参数覆盖
                kp: 临时比例增益
                kd: 临时微分增益
                torque_limit: 临时力矩限制

        Returns:
            控制力矩 (N·m)，如果设置了限幅则会被裁剪

        Raises:
            ValueError: 如果未提供 target 参数
        """
        if target is None:
            raise ValueError("PDController requires a target position")

        # 允许临时覆盖参数
        kp = kwargs.get("kp", self.kp)
        kd = kwargs.get("kd", self.kd)
        limit = kwargs.get("torque_limit", self.torque_limit)

        # 计算 PD 控制律
        error = target - q
        torque = kp * error - kd * qd

        # 应用力矩限幅
        if limit is not None:
            torque = float(np.clip(torque, -limit, limit))

        return float(torque)

    def set_gains(self, kp: float | None = None, kd: float | None = None) -> None:
        """更新控制增益。

        Args:
            kp: 新的比例增益，None 表示保持不变
            kd: 新的微分增益，None 表示保持不变
        """
        if kp is not None:
            self.kp = kp
        if kd is not None:
            self.kd = kd

    def __repr__(self) -> str:
        """返回控制器的字符串表示。"""
        limit_str = f"{self.torque_limit:.1f}" if self.torque_limit else "None"
        return f"PDController(kp={self.kp:.1f}, kd={self.kd:.1f}, limit={limit_str})"
