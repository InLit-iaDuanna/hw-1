"""逆运动学求解器：2D/3D 腿部 IK。

提供统一的 IK 实现，支持 2D 矢状面和 3D 空间的腿部运动学求解。
"""

from __future__ import annotations

import math

import numpy as np


def solve_2d_leg_ik(
    hip_xz: tuple[float, float],
    foot_xz: tuple[float, float],
    thigh_len: float,
    shank_len: float,
    knee_limit_deg: float = 70.0,
) -> tuple[float, float] | None:
    """2D 逆运动学：矢状面腿部 IK（hip-knee-ankle 链）。

    给定髋关节和落脚点位置，求解髋关节和膝关节角度。使用余弦定理求解。

    Args:
        hip_xz: 髋关节位置 (x, z)，x 为前向，z 为竖直
        foot_xz: 目标落脚点位置 (x, z)
        thigh_len: 大腿长度 (m)
        shank_len: 小腿长度 (m)
        knee_limit_deg: 膝关节最大弯曲角度限制（度）

    Returns:
        (hip_angle, knee_angle) 单位 rad，或 None（当目标点超出工作空间时）

        hip_angle: 髋关节角度，正值表示向前摆动
        knee_angle: 膝关节角度，正值表示弯曲

    Examples:
        >>> hip_angle, knee_angle = solve_2d_leg_ik(
        ...     (0.0, 1.0),  # 髋关节在 1m 高处
        ...     (0.2, 0.1),  # 脚在前方 0.2m，高度 0.1m
        ...     0.5, 0.5     # 大小腿各 0.5m
        ... )
    """
    dx = hip_xz[0] - foot_xz[0]
    dz = hip_xz[1] - foot_xz[1]

    leg_len = thigh_len + shank_len
    d = math.hypot(dx, dz)

    # 检查可达性
    if d < abs(thigh_len - shank_len) + 1e-5 or d > leg_len - 1e-5:
        return None

    # 限制距离在可达范围内
    d = float(np.clip(d, abs(thigh_len - shank_len) + 1e-5, leg_len - 1e-5))

    # 使用余弦定理求解 hip 角度
    base = math.atan2(dx, dz)
    cos_delta = (thigh_len**2 + d**2 - shank_len**2) / (2.0 * thigh_len * d)
    cos_delta = float(np.clip(cos_delta, -1.0, 1.0))
    delta = math.acos(cos_delta)
    hip_angle = base - delta

    # 从几何约束计算 knee 角度
    knee_x = hip_xz[0] - thigh_len * math.sin(hip_angle)
    knee_z = hip_xz[1] - thigh_len * math.cos(hip_angle)
    shank_angle = math.atan2(knee_x - foot_xz[0], knee_z - foot_xz[1])
    knee_angle = float(
        np.clip(shank_angle - hip_angle, 0.0, math.radians(knee_limit_deg))
    )

    return (hip_angle, knee_angle)


def solve_3d_leg_ik(
    hip_xyz: tuple[float, float, float],
    foot_xyz: tuple[float, float, float],
    thigh_len: float,
    shank_len: float,
    hip_lat_offset: float,
    knee_limit_deg: float = 70.0,
    abd_limit_deg: float = 15.0,
) -> tuple[float, float, float] | None:
    """3D 逆运动学：给定 hip 和 foot 位置，求解 hip/knee/abd 角度。

    先求解髋外展角度（从侧向偏移），然后投影到矢状面求解 hip/knee。

    Args:
        hip_xyz: 髋关节中心位置 (x, y, z)，x 前向，y 侧向，z 竖直
        foot_xyz: 目标落脚点位置 (x, y, z)
        thigh_len: 大腿长度 (m)
        shank_len: 小腿长度 (m)
        hip_lat_offset: 髋外展关节侧向偏移（从躯干中心到外展轴的距离）
        knee_limit_deg: 膝关节最大弯曲角度限制（度）
        abd_limit_deg: 髋外展角度限制（度）

    Returns:
        (hip_angle, knee_angle, abd_angle) 单位 rad，或 None（无解时）

        hip_angle: 髋关节矢状面角度
        knee_angle: 膝关节弯曲角度
        abd_angle: 髋外展角度（正值表示外展，负值表示内收）

    Examples:
        >>> result = solve_3d_leg_ik(
        ...     (0.0, 0.05, 1.0),   # 髋关节在 1m 高，右侧偏移 0.05m
        ...     (0.2, 0.1, 0.1),    # 脚在前方 0.2m，侧向 0.1m，高度 0.1m
        ...     0.5, 0.5, 0.02      # 大小腿各 0.5m，髋偏移 0.02m
        ... )
    """
    dx = hip_xyz[0] - foot_xyz[0]
    dy_total = hip_xyz[1] - foot_xyz[1]
    dz = hip_xyz[2] - foot_xyz[2]

    # 1. 求解髋外展角度（从侧向偏移反解）
    # 简化假设：hip_abd 主要影响 y 方向，矢状面几何近似不变
    d_sagittal_raw = math.hypot(dx, dz)

    # 处理 dy_total 符号（左腿为负，右腿为正）
    sign_y = 1.0 if dy_total > 0 else -1.0
    dy_corrected = dy_total - sign_y * hip_lat_offset

    # abd 角度（小角度近似）
    if d_sagittal_raw > 1e-6:
        abd_angle = math.atan2(dy_corrected, d_sagittal_raw)
    else:
        abd_angle = 0.0

    # 限制 abd 角度在合理范围内
    abd_angle = float(
        np.clip(abd_angle, math.radians(-abd_limit_deg), math.radians(abd_limit_deg))
    )

    # 2. 投影到矢状面求解 hip/knee（复用 2D IK）
    leg_len = thigh_len + shank_len
    d_sagittal = math.hypot(dx, dz)
    d_sagittal = float(
        np.clip(d_sagittal, abs(thigh_len - shank_len) + 1e-5, leg_len - 1e-5)
    )

    # 余弦定理求 hip 角度
    base = math.atan2(dx, dz)
    cos_delta = (thigh_len**2 + d_sagittal**2 - shank_len**2) / (
        2.0 * thigh_len * d_sagittal
    )
    cos_delta = float(np.clip(cos_delta, -1.0, 1.0))
    delta = math.acos(cos_delta)
    hip_angle = base - delta

    # 3. knee 角度（从几何约束）
    knee_x = hip_xyz[0] - thigh_len * math.sin(hip_angle)
    knee_z = hip_xyz[2] - thigh_len * math.cos(hip_angle)
    shank_angle = math.atan2(knee_x - foot_xyz[0], knee_z - foot_xyz[2])
    knee_angle = float(
        np.clip(shank_angle - hip_angle, 0.0, math.radians(knee_limit_deg))
    )

    return (hip_angle, knee_angle, abd_angle)


def compute_foot_position_from_joints(
    hip_xyz: tuple[float, float, float],
    hip_angle: float,
    knee_angle: float,
    abd_angle: float,
    thigh_len: float,
    shank_len: float,
    hip_lat_offset: float,
) -> tuple[float, float, float]:
    """正运动学：从关节角度计算脚底位置（用于验证 IK）。

    Args:
        hip_xyz: 髋关节中心位置 (x, y, z)
        hip_angle: 髋关节角度 (rad)
        knee_angle: 膝关节角度 (rad)
        abd_angle: 髋外展角度 (rad)
        thigh_len: 大腿长度 (m)
        shank_len: 小腿长度 (m)
        hip_lat_offset: 髋外展关节侧向偏移

    Returns:
        脚底位置 (x, y, z)
    """
    # 从 hip 到 knee
    knee_x = hip_xyz[0] - thigh_len * math.sin(hip_angle)
    knee_y = hip_xyz[1] + hip_lat_offset * (1.0 if hip_xyz[1] > 0 else -1.0)
    knee_z = hip_xyz[2] - thigh_len * math.cos(hip_angle)

    # 从 knee 到 foot
    shank_angle = hip_angle + knee_angle
    foot_x = knee_x - shank_len * math.sin(shank_angle)
    foot_y = knee_y + shank_len * math.cos(hip_angle) * math.sin(abd_angle)
    foot_z = knee_z - shank_len * math.cos(shank_angle)

    return (foot_x, foot_y, foot_z)
