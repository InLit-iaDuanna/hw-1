"""Data contracts for realtime dashboard-derived gait signals."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SegmentAngles:
    """Sagittal segment pitch angles in degrees."""

    left_foot: float = 0.0
    right_foot: float = 0.0
    left_shank: float = 0.0
    right_shank: float = 0.0
    left_thigh: float = 0.0
    right_thigh: float = 0.0
    pelvis: float = 0.0

    def as_dict(self) -> dict[str, float]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class JointAngles:
    """Sagittal joint angles in degrees, using segment pitch differences."""

    left_ankle: float = 0.0
    right_ankle: float = 0.0
    left_knee: float = 0.0
    right_knee: float = 0.0
    left_hip: float = 0.0
    right_hip: float = 0.0

    def as_dict(self) -> dict[str, float]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class GaitEvent:
    """Confirmed realtime gait event."""

    side: str
    kind: str
    time_s: float


@dataclass(frozen=True)
class RollingMetrics:
    """Rolling-window gait metrics for the dashboard."""

    cadence_spm: float = 0.0
    left_stance_s: float | None = None
    right_stance_s: float | None = None
    left_swing_s: float | None = None
    right_swing_s: float | None = None
    left_knee_rom_deg: float | None = None
    right_knee_rom_deg: float | None = None
    left_hip_rom_deg: float | None = None
    right_hip_rom_deg: float | None = None

    def as_dict(self) -> dict[str, float | None]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class ClinicalSummary:
    """Clinical-facing asymmetry summary.

    This is a detection/visualization aid only. It does not assert clinical
    validity without patient-data validation.
    """

    symmetry_index_pct: float = 0.0
    symmetry_zone: str = "green"
    affected_side: str = "unknown"
    classifier_pattern: str = "unknown"
    confidence: float = 0.0


@dataclass(frozen=True)
class DerivedSample:
    """One realtime derived sample emitted from a raw Hardware V1 frame."""

    seq: int
    time_s: float
    segments: SegmentAngles
    joints: JointAngles
    events: tuple[GaitEvent, ...] = field(default_factory=tuple)
    metrics: RollingMetrics = field(default_factory=RollingMetrics)
    clinical: ClinicalSummary = field(default_factory=ClinicalSummary)
    health: dict[str, object] = field(default_factory=dict)
