"""传感器噪声模型与仿真器。

基于 V17 noise_scale 参数实现编码器量化、噪声注入和接触传感器延迟模型。
用于测试控制器在真实传感器噪声下的鲁棒性。
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass(frozen=True)
class SensorNoiseParams:
    """传感器噪声参数配置。

    Attributes:
        encoder_cpr: 编码器每转脉冲数 (Counts Per Revolution)
        encoder_quantize: 是否启用编码器量化模拟
        contact_chatter_ms: 接触传感器抖动窗口 (毫秒)
        noise_scale: 全局噪声缩放因子 (0.0=无噪声, 1.0=标称噪声)
    """
    encoder_cpr: int = 4096
    encoder_quantize: bool = True
    contact_chatter_ms: float = 5.0
    noise_scale: float = 1.0


@dataclass
class SensorReading:
    """传感器读数数据结构。

    Attributes:
        joint_angles: 关节角度 [left_hip, left_knee, right_hip, right_knee] (rad)
        left_contact_raw: 左脚接触传感器原始读数
        right_contact_raw: 右脚接触传感器原始读数
        timestamp: 时间戳 (s)
    """
    joint_angles: np.ndarray
    left_contact_raw: bool
    right_contact_raw: bool
    timestamp: float


class SensorModel:
    """传感器噪声模型：ground truth → 带噪声测量。

    功能：
    1. 编码器量化模拟（基于 CPR）
    2. 接触传感器抖动/延迟模型
    3. 可选高斯噪声注入（通过 noise_scale 控制）

    基于 V17 实现，用于硬件控制器的传感器接口测试。
    """

    def __init__(self, params: SensorNoiseParams, seed: int = 42):
        """初始化传感器模型。

        Args:
            params: 传感器噪声参数
            seed: 随机数种子（用于可重复的噪声生成）
        """
        self.params = params
        self._rad_per_count = 2.0 * math.pi / params.encoder_cpr

        # 接触传感器状态跟踪
        self._last_left_contact: Optional[bool] = None
        self._last_right_contact: Optional[bool] = None
        self._left_transition_t: float = -1.0
        self._right_transition_t: float = -1.0

        # 随机数生成器
        self._rng = np.random.RandomState(seed)

    def _quantize_angle(self, angle: float) -> float:
        """编码器量化模拟。

        将连续角度量化到离散编码器计数值，模拟真实编码器的分辨率限制。

        Args:
            angle: 真实关节角度 (rad)

        Returns:
            量化后的角度 (rad)
        """
        if not self.params.encoder_quantize or self.params.noise_scale == 0.0:
            return angle

        counts = round(angle / self._rad_per_count)
        return counts * self._rad_per_count

    def _chatter_contact(
        self,
        true_contact: bool,
        last_contact: Optional[bool],
        transition_t: float,
        t: float,
    ) -> tuple[bool, float]:
        """接触传感器抖动模型。

        模拟机械接触传感器在状态转换时的抖动/延迟现象：
        - 状态转换后，在 chatter_window 时间内，传感器读数不稳定
        - 在抖动窗口内，返回旧状态（延迟报告新状态）

        Args:
            true_contact: 真实接触状态
            last_contact: 上次接触状态
            transition_t: 上次状态转换时间
            t: 当前时间

        Returns:
            (传感器读数, 更新后的转换时间)
        """
        if last_contact is None or self.params.noise_scale == 0.0:
            return true_contact, transition_t

        # 检测状态转换
        if true_contact != last_contact:
            transition_t = t

        # 计算抖动窗口（受 noise_scale 缩放）
        chatter_window = self.params.contact_chatter_ms * 1e-3 * self.params.noise_scale

        # 在抖动窗口内，返回反向状态（模拟延迟）
        if t - transition_t < chatter_window:
            return not true_contact, transition_t

        return true_contact, transition_t

    def measure(
        self,
        data,
        t: float,
        true_left_contact: bool,
        true_right_contact: bool,
    ) -> SensorReading:
        """从 MuJoCo 仿真数据生成带噪声的传感器读数。

        Args:
            data: MuJoCo 数据对象 (data.qpos 包含关节角度)
            t: 当前仿真时间 (s)
            true_left_contact: 真实左脚接触状态
            true_right_contact: 真实右脚接触状态

        Returns:
            带噪声的传感器读数
        """
        # 提取关节角度 (假设 qpos 顺序：[root_x, root_z, left_hip, left_knee, ...])
        raw_angles = np.array([
            float(data.qpos[2]),  # left_hip
            float(data.qpos[3]),  # left_knee
            float(data.qpos[5]),  # right_hip
            float(data.qpos[6]),  # right_knee
        ])

        # 编码器量化
        quantized = np.array([self._quantize_angle(a) for a in raw_angles])

        # 接触传感器抖动模拟
        left_out, self._left_transition_t = self._chatter_contact(
            true_left_contact,
            self._last_left_contact,
            self._left_transition_t,
            t,
        )
        right_out, self._right_transition_t = self._chatter_contact(
            true_right_contact,
            self._last_right_contact,
            self._right_transition_t,
            t,
        )

        # 更新接触状态历史
        self._last_left_contact = true_left_contact
        self._last_right_contact = true_right_contact

        return SensorReading(
            joint_angles=quantized,
            left_contact_raw=left_out,
            right_contact_raw=right_out,
            timestamp=t,
        )

    def add_gaussian_noise(
        self,
        angles: np.ndarray,
        noise_std_rad: float = 0.001,
    ) -> np.ndarray:
        """可选的高斯噪声注入（用于测试）。

        在编码器量化的基础上，额外添加高斯分布的测量噪声。

        Args:
            angles: 关节角度数组 (rad)
            noise_std_rad: 噪声标准差 (rad), 默认 0.001 rad ≈ 0.057°

        Returns:
            添加噪声后的角度数组
        """
        if self.params.noise_scale == 0.0:
            return angles

        noise = self._rng.normal(
            loc=0.0,
            scale=noise_std_rad * self.params.noise_scale,
            size=angles.shape,
        )
        return angles + noise

    def reset(self):
        """重置传感器模型内部状态（用于新仿真开始时）。"""
        self._last_left_contact = None
        self._last_right_contact = None
        self._left_transition_t = -1.0
        self._right_transition_t = -1.0


class EncoderSimulator:
    """独立的编码器量化仿真器（用于硬件接口测试）。

    可独立于 SensorModel 使用，模拟真实编码器的数字化过程。
    """

    def __init__(self, cpr: int = 4096):
        """初始化编码器模拟器。

        Args:
            cpr: 编码器每转脉冲数
        """
        self.cpr = cpr
        self.rad_per_count = 2.0 * math.pi / cpr
        self.count_per_rad = cpr / (2.0 * math.pi)

    def angle_to_counts(self, angle_rad: float) -> int:
        """将角度转换为编码器计数值。

        Args:
            angle_rad: 角度 (rad)

        Returns:
            编码器计数值 (整数)
        """
        return round(angle_rad * self.count_per_rad)

    def counts_to_angle(self, counts: int) -> float:
        """将编码器计数值转换为角度。

        Args:
            counts: 编码器计数值

        Returns:
            角度 (rad)
        """
        return counts * self.rad_per_count

    def quantize(self, angle_rad: float) -> float:
        """量化角度（往返转换模拟）。

        Args:
            angle_rad: 输入角度 (rad)

        Returns:
            量化后的角度 (rad)
        """
        counts = self.angle_to_counts(angle_rad)
        return self.counts_to_angle(counts)

    def resolution_rad(self) -> float:
        """返回编码器角度分辨率 (rad)。"""
        return self.rad_per_count

    def resolution_deg(self) -> float:
        """返回编码器角度分辨率 (度)。"""
        return math.degrees(self.rad_per_count)


class ContactSensorSimulator:
    """独立的接触传感器延迟/抖动模拟器（用于硬件接口测试）。"""

    def __init__(self, chatter_window_ms: float = 5.0):
        """初始化接触传感器模拟器。

        Args:
            chatter_window_ms: 抖动窗口时间 (毫秒)
        """
        self.chatter_window_s = chatter_window_ms * 1e-3
        self._last_state: Optional[bool] = None
        self._transition_t: float = -1.0

    def read(self, true_state: bool, current_time: float) -> bool:
        """读取带抖动的传感器状态。

        Args:
            true_state: 真实接触状态
            current_time: 当前时间 (s)

        Returns:
            传感器报告的状态（可能延迟）
        """
        if self._last_state is None:
            self._last_state = true_state
            return true_state

        # 检测状态转换
        if true_state != self._last_state:
            self._transition_t = current_time
            self._last_state = true_state

        # 在抖动窗口内，返回旧状态
        if current_time - self._transition_t < self.chatter_window_s:
            return not true_state

        return true_state

    def reset(self):
        """重置传感器状态。"""
        self._last_state = None
        self._transition_t = -1.0


# 便捷函数：创建标称噪声参数
def make_nominal_noise_params() -> SensorNoiseParams:
    """创建标称传感器噪声参数（基于 V17 默认值）。"""
    return SensorNoiseParams(
        encoder_cpr=4096,
        encoder_quantize=True,
        contact_chatter_ms=5.0,
        noise_scale=1.0,
    )


def make_no_noise_params() -> SensorNoiseParams:
    """创建无噪声参数（用于理想测试）。"""
    return SensorNoiseParams(
        encoder_cpr=4096,
        encoder_quantize=False,
        contact_chatter_ms=0.0,
        noise_scale=0.0,
    )
