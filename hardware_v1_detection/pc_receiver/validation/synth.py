"""Synthesize Hardware V1 SampleFrames from a simulation joint-angle trajectory.

The synthesis is the *inverse* of the dashboard's L1 chain, so a correct
pipeline recovers the inputs (round-trip self-consistency):

* Segment absolute pitch is built with the SAME joint definitions the pipeline
  uses to go the other way::

      thigh = pelvis + hip
      shank = thigh - knee
      foot  = shank + ankle

* Each segment IMU is modeled as a gravity-only accelerometer plus a rate gyro::

      ax_g = -sin(pitch),  ay_g = 0,  az_g = cos(pitch)   ->  atan2(-ax, |.|) = pitch
      gy_dps = d(pitch_deg)/dt

  This is exactly the assumption L1's complementary filter makes, so the
  recovered pitch should track the input pitch closely.

* A configurable heel-strike accel transient is injected at each contact
  rising edge so the L2 event detector has a physical impact to trigger on.

No sensor noise is added by default; this is a functional test, not a
noise-robustness test (see package docstring).
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass, field
from pathlib import Path

from hardware_v1_detection.pc_receiver.protocol import (
    BMI_ACCEL_LSB_PER_G,
    BMI_GYRO_LSB_PER_DPS,
    BMI_SENSOR_COUNT,
    BMX_ACCEL_LSB_PER_G,
    BMX_GYRO_LSB_PER_DPS,
    FRAME_TYPE_SAMPLE,
    Imu6,
    Imu9,
    SampleFrame,
    SENSOR_NAMES,
    VERSION,
)

_INT16_MIN = -32768
_INT16_MAX = 32767


def _clamp_int16(value: float) -> int:
    return max(_INT16_MIN, min(_INT16_MAX, int(round(value))))


@dataclass
class TrajectorySample:
    """One row of simulation ground truth (radians, seconds)."""

    t_s: float
    left_hip: float
    left_knee: float
    left_ankle: float
    right_hip: float
    right_knee: float
    right_ankle: float
    left_contact: bool
    right_contact: bool


@dataclass(frozen=True)
class SynthConfig:
    """Knobs for the simulation -> IMU synthesis."""

    pelvis_pitch_rad: float = 0.0  # trunk lean; compass gait ~ upright
    heel_impact_g: float = 2.0  # extra accel magnitude at contact rising edge
    heel_impact_frames: int = 2  # how many frames the impact spike lasts
    sample_rate_hz: float = 200.0  # nominal device rate (ts spacing uses CSV dt)


# Segment pitch is keyed by SENSOR_NAMES order (first 6 are BMI, last is pelvis).
_BMI_NAMES = SENSOR_NAMES[:BMI_SENSOR_COUNT]


def load_trajectory_csv(path: str | Path) -> list[TrajectorySample]:
    """Load a V13.x ``*_data.csv`` trajectory into ground-truth samples."""

    rows: list[TrajectorySample] = []
    with open(path, newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(
                TrajectorySample(
                    t_s=float(row["time"]),
                    left_hip=float(row["left_hip"]),
                    left_knee=float(row["left_knee"]),
                    left_ankle=float(row["left_ankle"]),
                    right_hip=float(row["right_hip"]),
                    right_knee=float(row["right_knee"]),
                    right_ankle=float(row["right_ankle"]),
                    left_contact=_truthy(row.get("left_contact", "0")),
                    right_contact=_truthy(row.get("right_contact", "0")),
                )
            )
    return rows


def _truthy(value: str) -> bool:
    text = str(value).strip().lower()
    if text in ("", "0", "0.0", "false", "no"):
        return False
    try:
        return float(text) != 0.0
    except ValueError:
        return text in ("true", "yes")


def _segment_pitches(sample: TrajectorySample, pelvis_pitch: float) -> dict[str, float]:
    """Invert joint angles into absolute segment pitch (radians).

    Uses the pipeline's own joint definitions so the round trip is exact.
    """

    left_thigh = pelvis_pitch + sample.left_hip
    left_shank = left_thigh - sample.left_knee
    left_foot = left_shank + sample.left_ankle

    right_thigh = pelvis_pitch + sample.right_hip
    right_shank = right_thigh - sample.right_knee
    right_foot = right_shank + sample.right_ankle

    return {
        "left_foot": left_foot,
        "right_foot": right_foot,
        "left_shank": left_shank,
        "right_shank": right_shank,
        "left_thigh": left_thigh,
        "right_thigh": right_thigh,
        "pelvis": pelvis_pitch,
    }


@dataclass
class TrajectorySynthesizer:
    """Turn a ground-truth trajectory into a stream of SampleFrames."""

    config: SynthConfig = field(default_factory=SynthConfig)

    def synthesize(self, samples: list[TrajectorySample]) -> list[SampleFrame]:
        if not samples:
            return []

        pelvis_pitch = self.config.pelvis_pitch_rad
        pitch_series = [_segment_pitches(s, pelvis_pitch) for s in samples]

        # Per-segment pitch rate (deg/s) by central/forward difference.
        rate_series = self._pitch_rates(samples, pitch_series)

        # Frames where a heel impact spike should be applied (contact rising edge).
        impact_left = self._impact_frames(samples, "left")
        impact_right = self._impact_frames(samples, "right")

        frames: list[SampleFrame] = []
        for i, sample in enumerate(samples):
            pitches = pitch_series[i]
            rates = rate_series[i]
            bmi: list[Imu6] = []
            for name in _BMI_NAMES:
                impact = 0.0
                if name == "left_foot" and i in impact_left:
                    impact = self.config.heel_impact_g
                elif name == "right_foot" and i in impact_right:
                    impact = self.config.heel_impact_g
                bmi.append(self._bmi_imu(pitches[name], rates[name], impact))
            pelvis = self._pelvis_imu(pitches["pelvis"], rates["pelvis"])
            frames.append(
                SampleFrame(
                    version=VERSION,
                    frame_type=FRAME_TYPE_SAMPLE,
                    seq=i,
                    ts_us=int(round(sample.t_s * 1_000_000)),
                    status=0,
                    bmi=tuple(bmi),
                    pelvis=pelvis,
                )
            )
        return frames

    def _pitch_rates(
        self, samples: list[TrajectorySample], pitch_series: list[dict[str, float]]
    ) -> list[dict[str, float]]:
        n = len(samples)
        rates: list[dict[str, float]] = []
        for i in range(n):
            j0 = max(0, i - 1)
            j1 = min(n - 1, i + 1)
            dt = samples[j1].t_s - samples[j0].t_s
            row: dict[str, float] = {}
            for name in pitch_series[i]:
                if dt <= 0.0:
                    row[name] = 0.0
                else:
                    d_rad = pitch_series[j1][name] - pitch_series[j0][name]
                    row[name] = math.degrees(d_rad / dt)
            rates.append(row)
        return rates

    def _impact_frames(self, samples: list[TrajectorySample], side: str) -> set[int]:
        attr = f"{side}_contact"
        frames: set[int] = set()
        prev = False
        for i, sample in enumerate(samples):
            now = getattr(sample, attr)
            if now and not prev:
                for k in range(
                    i, min(len(samples), i + self.config.heel_impact_frames)
                ):
                    frames.add(k)
            prev = now
        return frames

    def _bmi_imu(self, pitch_rad: float, rate_dps: float, impact_g: float) -> Imu6:
        ax_g = -math.sin(pitch_rad)
        az_g = math.cos(pitch_rad)
        if impact_g:
            # Add the impact along the gravity-aligned axis (vertical-ish) so the
            # accel norm rises above the heel-strike threshold without corrupting
            # the resting pitch estimate too badly.
            az_g += impact_g
        return Imu6(
            ax=_clamp_int16(ax_g * BMI_ACCEL_LSB_PER_G),
            ay=0,
            az=_clamp_int16(az_g * BMI_ACCEL_LSB_PER_G),
            gx=0,
            gy=_clamp_int16(rate_dps * BMI_GYRO_LSB_PER_DPS),
            gz=0,
        )

    def _pelvis_imu(self, pitch_rad: float, rate_dps: float) -> Imu9:
        ax_g = -math.sin(pitch_rad)
        az_g = math.cos(pitch_rad)
        return Imu9(
            ax=_clamp_int16(ax_g * BMX_ACCEL_LSB_PER_G),
            ay=0,
            az=_clamp_int16(az_g * BMX_ACCEL_LSB_PER_G),
            gx=0,
            gy=_clamp_int16(rate_dps * BMX_GYRO_LSB_PER_DPS),
            gz=0,
            mx=0,
            my=0,
            mz=0,
        )
