"""V17 传感器噪声模型：ground truth → 带噪声测量。"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class SensorNoiseParams:
    encoder_cpr: int = 4096
    encoder_quantize: bool = True
    contact_chatter_ms: float = 5.0
    noise_scale: float = 1.0


@dataclass
class SensorReading:
    joint_angles: np.ndarray
    left_contact_raw: bool
    right_contact_raw: bool
    timestamp: float


class SensorModel:
    def __init__(self, params: SensorNoiseParams, seed: int = 42):
        self.params = params
        self._rad_per_count = 2.0 * math.pi / params.encoder_cpr
        self._last_left_contact: bool | None = None
        self._last_right_contact: bool | None = None
        self._left_transition_t: float = -1.0
        self._right_transition_t: float = -1.0
        self._rng = random.Random(seed)

    def _quantize_angle(self, angle: float) -> float:
        if not self.params.encoder_quantize or self.params.noise_scale == 0.0:
            return angle
        counts = round(angle / self._rad_per_count)
        return counts * self._rad_per_count

    def _chatter_contact(
        self,
        true_contact: bool,
        last_contact: bool | None,
        transition_t: float,
        t: float,
    ) -> tuple[bool, float]:
        """接触开关抖动模型：转换后延迟 chatter_window 才报告新状态。"""
        if last_contact is None or self.params.noise_scale == 0.0:
            return true_contact, transition_t
        if true_contact != last_contact:
            transition_t = t
        chatter_window = self.params.contact_chatter_ms * 1e-3 * self.params.noise_scale
        if t - transition_t < chatter_window:
            return not true_contact, transition_t
        return true_contact, transition_t

    def measure(
        self, data, t: float, true_left_contact: bool, true_right_contact: bool
    ) -> SensorReading:
        raw_angles = np.array(
            [
                float(data.qpos[2]),  # left_hip
                float(data.qpos[3]),  # left_knee
                float(data.qpos[5]),  # right_hip
                float(data.qpos[6]),  # right_knee
            ]
        )
        quantized = np.array([self._quantize_angle(a) for a in raw_angles])

        left_out, self._left_transition_t = self._chatter_contact(
            true_left_contact, self._last_left_contact, self._left_transition_t, t
        )
        right_out, self._right_transition_t = self._chatter_contact(
            true_right_contact, self._last_right_contact, self._right_transition_t, t
        )
        self._last_left_contact = true_left_contact
        self._last_right_contact = true_right_contact

        return SensorReading(
            joint_angles=quantized,
            left_contact_raw=left_out,
            right_contact_raw=right_out,
            timestamp=t,
        )
