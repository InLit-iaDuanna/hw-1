"""Online sagittal pitch estimation from scaled IMU samples."""

from __future__ import annotations

import math
from dataclasses import dataclass


def accel_pitch_deg(ax_g: float, ay_g: float, az_g: float) -> float:
    """Return sagittal pitch from gravity in degrees.

    The sign convention is intentionally simple and explicit: positive pitch is
    produced when the sensor's +X axis tilts upward relative to gravity.
    """

    return math.degrees(math.atan2(-ax_g, math.hypot(ay_g, az_g)))


@dataclass
class ComplementaryPitchFilter:
    """Minimal online complementary filter for one segment pitch."""

    alpha: float = 0.98
    gyro_axis: str = "gy_dps"
    pitch_deg: float | None = None

    def update(self, sample: dict[str, float], dt_s: float | None) -> float:
        acc_pitch = accel_pitch_deg(sample["ax_g"], sample["ay_g"], sample["az_g"])
        if self.pitch_deg is None or dt_s is None or dt_s <= 0.0:
            self.pitch_deg = acc_pitch
            return self.pitch_deg

        gyro_rate = float(sample.get(self.gyro_axis, 0.0))
        predicted = self.pitch_deg + gyro_rate * dt_s
        self.pitch_deg = self.alpha * predicted + (1.0 - self.alpha) * acc_pitch
        return self.pitch_deg
