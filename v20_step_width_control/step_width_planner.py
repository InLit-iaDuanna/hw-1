"""V20 步宽规划器：基于 LIPM 的侧向落脚点控制。"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

# 导入 common 库工具
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from common import (
    smoothstep,
)  # noqa: E402


@dataclass(frozen=True)
class StepWidthParams:
    """步宽控制参数。"""

    k_p: float = 0.0  # 位置反馈增益
    k_d: float = 0.0  # 速度反馈增益
    y_nominal: float = 0.055  # 名义步宽偏移（单侧）
    y_max_deviation: float = 0.15  # 最大侧向偏移限制


class StepWidthPlanner:
    """步宽规划器：计算目标落脚点侧向位置并生成轨迹。"""

    def __init__(self, params: StepWidthParams):
        self.params = params
        self.y_target_left = -params.y_nominal
        self.y_target_right = params.y_nominal
        self.y_swing_start = 0.0

    def compute_target_y(
        self, hip_y: float, vy_hip: float, is_left_swing: bool
    ) -> float:
        """计算目标落脚点侧向位置（LIPM 反馈律）。

        Args:
            hip_y: 当前髋关节侧向位置 (m)
            vy_hip: 当前髋关节侧向速度 (m/s)
            is_left_swing: True 表示左腿摆动，False 表示右腿摆动

        Returns:
            目标落脚点侧向位置 (m)，负值表示左侧，正值表示右侧
        """
        p = self.params
        sign = -1.0 if is_left_swing else 1.0

        # LIPM 步宽控制律：y_foot = y_hip + k_p * y_hip + k_d * vy_hip + y_nominal
        y_target = hip_y + p.k_p * hip_y + p.k_d * vy_hip + sign * p.y_nominal

        # 限制在安全范围内
        y_target = float(np.clip(y_target, -p.y_max_deviation, p.y_max_deviation))

        return y_target

    def on_swing_start(
        self, hip_y: float, vy_hip: float, is_left_swing: bool, current_y_foot: float
    ) -> None:
        """在摆动相开始时记录目标和初始位置。

        Args:
            hip_y: 当前髋关节侧向位置
            vy_hip: 当前髋关节侧向速度
            is_left_swing: 是否左腿摆动
            current_y_foot: 摆动脚当前的侧向位置
        """
        self.y_swing_start = current_y_foot
        y_target = self.compute_target_y(hip_y, vy_hip, is_left_swing)

        if is_left_swing:
            self.y_target_left = y_target
        else:
            self.y_target_right = y_target

    def interpolate_y_trajectory(self, u: float, is_left_swing: bool) -> float:
        """在摆动相插值侧向轨迹。

        Args:
            u: 摆动相相位 [0, 1]
            is_left_swing: 是否左腿摆动

        Returns:
            当前时刻目标侧向位置 (m)
        """
        s = smoothstep(u)
        y_target = self.y_target_left if is_left_swing else self.y_target_right
        return self.y_swing_start + (y_target - self.y_swing_start) * s
