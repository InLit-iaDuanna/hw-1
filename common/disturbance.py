"""扰动注入：外力脉冲 + 触地相位噪声。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class ImpulseSpec:
    """单脉冲外力规范。

    body_name: 施力 body（V10 中通常为 "hip"）
    force_xyz: 力向量 (Fx, Fy, Fz) 单位 N（世界系）
    t_start_s: 脉冲起点（仿真时间）
    duration_s: 持续时长
    """

    body_name: str
    force_xyz: tuple[float, float, float]
    t_start_s: float
    duration_s: float

    @property
    def t_end_s(self) -> float:
        return self.t_start_s + self.duration_s


def apply_impulse(model, data, spec: ImpulseSpec, t: float) -> bool:
    """在仿真主循环内每步调用。返回是否当前正在施力。

    施力：写入 data.xfrc_applied[body_id, 0:3]
    出窗口：清零（避免遗留外力）
    """
    import mujoco

    body_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, spec.body_name)
    if body_id < 0:
        # body 不存在，无法施力也无法清零，直接返回
        return False

    if spec.t_start_s <= t < spec.t_end_s:
        # 在脉冲窗口内，施加外力
        data.xfrc_applied[body_id, 0] = spec.force_xyz[0]
        data.xfrc_applied[body_id, 1] = spec.force_xyz[1]
        data.xfrc_applied[body_id, 2] = spec.force_xyz[2]
        return True
    else:
        # 出窗口（包括未到达和已结束），清零外力
        data.xfrc_applied[body_id, 0:3] = 0.0
        return False


@dataclass
class ContactPhaseNoise:
    """触地稳定时间噪声：直接抖动 V10 的 stable_contact_time 阈值。

    sigma_s: 高斯噪声标准差（秒）
    seed:    随机种子
    """

    sigma_s: float = 0.0
    seed: int = 0

    def __post_init__(self) -> None:
        self._rng = np.random.default_rng(self.seed)

    def perturbed_threshold(self, base_threshold_s: float) -> float:
        """每次触地候选事件触发时调用，返回扰动后的稳定时长阈值（不小于 1 ms）。"""
        if self.sigma_s <= 0.0:
            return base_threshold_s
        return max(0.001, base_threshold_s + float(self._rng.normal(0.0, self.sigma_s)))
