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
    def __init__(
        self,
        params: SensorNoiseParams | None = None,
        seed: int = 42,
        encoder_resolution_rad: float | None = None,
        contact_threshold_N: float | None = None,
        noise_seed: int | None = None,
    ):
        if noise_seed is not None:
            seed = noise_seed
        if params is None:
            if encoder_resolution_rad is not None and encoder_resolution_rad > 0.0:
                encoder_cpr = max(1, int(round(2.0 * math.pi / encoder_resolution_rad)))
            else:
                encoder_cpr = SensorNoiseParams.encoder_cpr
            params = SensorNoiseParams(encoder_cpr=encoder_cpr)
        self.params = params
        self._rad_per_count = 2.0 * math.pi / params.encoder_cpr
        self._read_noise_std = (
            0.5 * encoder_resolution_rad
            if encoder_resolution_rad is not None
            else 0.0
        )
        self.contact_threshold_N = contact_threshold_N
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

    def read(self, model, data) -> dict:
        """Compatibility wrapper used by older integration tests."""
        left_contact, right_contact = self._infer_contacts(model, data)
        reading = self.measure(data, float(getattr(data, "time", 0.0)), left_contact, right_contact)
        joint_angles = reading.joint_angles.copy()
        if self._read_noise_std > 0.0:
            joint_angles = np.array(
                [
                    angle + self._rng.gauss(0.0, self._read_noise_std)
                    for angle in joint_angles
                ]
            )
        return {
            "joint_angles": joint_angles,
            "left_contact": reading.left_contact_raw,
            "right_contact": reading.right_contact_raw,
            "timestamp": reading.timestamp,
        }

    @staticmethod
    def _infer_contacts(model, data) -> tuple[bool, bool]:
        left_contact = False
        right_contact = False
        for i in range(data.ncon):
            contact = data.contact[i]
            names = []
            for geom_id in (contact.geom1, contact.geom2):
                name = model.geom(geom_id).name
                if name:
                    names.append(name)
            joined = " ".join(names).lower()
            if "floor" not in joined and "ground" not in joined and "ramp" not in joined:
                continue
            if "left" in joined:
                left_contact = True
            if "right" in joined:
                right_contact = True
        return left_contact, right_contact
