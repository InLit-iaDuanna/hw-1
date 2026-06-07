"""控制工具函数：平滑插值、PD 控制、地形高度计算。

用于 V18-V20（3D 阶段）及后续版本的通用控制算法。
"""

from __future__ import annotations

import math

import numpy as np


def smoothstep(u: float) -> float:
    """Smoothstep 插值函数 [0,1] → [0,1]。

    提供 C² 连续的平滑过渡，常用于相位插值和轨迹规划。

    Args:
        u: 输入值，会自动裁剪到 [0, 1] 范围

    Returns:
        平滑插值后的值 [0, 1]

    Examples:
        >>> smoothstep(0.0)
        0.0
        >>> smoothstep(0.5)
        0.5
        >>> smoothstep(1.0)
        1.0
    """
    u = min(max(u, 0.0), 1.0)
    return u * u * (3.0 - 2.0 * u)


def limited_pd(
    q: float, qd: float, target: float, kp: float, kd: float, limit: float
) -> float:
    """有限幅 PD 控制器。

    计算 PD 控制力矩：τ = Kp(target - q) - Kd·qd，并限制在 [-limit, +limit] 范围。

    Args:
        q: 当前关节位置 (rad)
        qd: 当前关节速度 (rad/s)
        target: 目标关节位置 (rad)
        kp: 比例增益 (N·m/rad)
        kd: 微分增益 (N·m·s/rad)
        limit: 力矩限制幅值 (N·m)，输出范围为 [-limit, +limit]

    Returns:
        限幅后的控制力矩 (N·m)

    Examples:
        >>> limited_pd(0.1, 0.0, 0.0, 100.0, 10.0, 50.0)
        -10.0
        >>> limited_pd(1.0, 0.0, 0.0, 100.0, 10.0, 50.0)  # 饱和
        -50.0
    """
    torque = kp * (target - q) - kd * qd
    return float(np.clip(torque, -limit, limit))


def ramp_height(x: float, gamma: float) -> float:
    """计算斜坡在给定 x 位置的高度。

    坡面方程：z = -tan(γ) · x，其中 γ 为坡度角（弧度）。

    Args:
        x: 斜坡纵向坐标 (m)，x=0 为原点
        gamma: 坡度角 (rad)，正值表示下坡，负值表示上坡

    Returns:
        对应位置的斜坡高度 (m)

    Examples:
        >>> ramp_height(0.0, 0.05)  # 原点高度
        0.0
        >>> ramp_height(1.0, 0.05)  # 1m 处，坡度 0.05 rad ≈ 2.86°
        -0.05...
    """
    return -math.tan(gamma) * x
