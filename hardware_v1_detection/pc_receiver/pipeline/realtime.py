"""Realtime L1-L4 pipeline for Hardware V1 dashboard."""

from __future__ import annotations

from dataclasses import dataclass, field

from hardware_v1_detection.pc_receiver.protocol import (
    BMI_SENSOR_NAMES,
    SENSOR_NAMES,
    SampleFrame,
    scale_sensor,
)

from .attitude import ComplementaryPitchFilter
from .events import FootEventDetector, RollingGaitMetrics, robinson_si
from .models import ClinicalSummary, DerivedSample, JointAngles, SegmentAngles

try:  # Optional reuse; dashboard must keep working if the research module changes.
    from gait_medical_system.diagnosis.stroke_gait_classifier import (
        StrokeGaitClassifier,
    )
except Exception:  # pragma: no cover - defensive dependency boundary
    StrokeGaitClassifier = None  # type: ignore[assignment]


def _zone_for_si(si_pct: float) -> str:
    if si_pct < 10.0:
        return "green"
    if si_pct < 20.0:
        return "yellow"
    return "red"


@dataclass
class RealtimePipeline:
    """Pure-Python realtime derived-signal pipeline.

    Inputs are raw `SampleFrame`s; raw persistence remains handled by
    `SessionWriter`. The pipeline scales only its own copy for visualization and
    analysis.
    """

    calibration: dict | None = None
    sample_rate_hz: float = 200.0
    alpha: float = 0.98
    _filters: dict[str, ComplementaryPitchFilter] = field(init=False)
    _event_detectors: dict[str, FootEventDetector] = field(init=False)
    _metrics: RollingGaitMetrics = field(default_factory=RollingGaitMetrics)
    _last_t_s: float | None = None
    _classifier: object | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        self._filters = {
            name: ComplementaryPitchFilter(alpha=self.alpha) for name in SENSOR_NAMES
        }
        self._event_detectors = {
            "left": FootEventDetector("left"),
            "right": FootEventDetector("right"),
        }
        if StrokeGaitClassifier is not None:
            try:
                self._classifier = StrokeGaitClassifier()
            except Exception:
                self._classifier = None

    def reset(self) -> None:
        self.__post_init__()
        self._metrics = RollingGaitMetrics()
        self._last_t_s = None

    def update(self, frame: SampleFrame) -> DerivedSample:
        t_s = frame.ts_us / 1_000_000.0
        dt_s = self._dt(t_s)
        scaled = self._scale_frame(frame)
        segment_values = {
            name: self._filters[name].update(values, dt_s)
            for name, values in scaled.items()
        }
        segments = SegmentAngles(**segment_values)
        joints = self._joint_angles(segments)

        events = tuple(
            [
                *self._event_detectors["left"].update(t_s, scaled["left_foot"]),
                *self._event_detectors["right"].update(t_s, scaled["right_foot"]),
            ]
        )
        metrics = self._metrics.update(t_s, joints, events)
        clinical = self._clinical_summary(metrics)
        health = {
            "status": frame.status,
            "status_names": frame.status_names(),
            "sample_rate_hz": self.sample_rate_hz,
        }

        return DerivedSample(
            seq=frame.seq,
            time_s=t_s,
            segments=segments,
            joints=joints,
            events=events,
            metrics=metrics,
            clinical=clinical,
            health=health,
        )

    def _dt(self, t_s: float) -> float | None:
        if self._last_t_s is None:
            self._last_t_s = t_s
            return None
        dt_s = t_s - self._last_t_s
        self._last_t_s = t_s
        if dt_s <= 0.0:
            return 1.0 / self.sample_rate_hz
        return dt_s

    def _scale_frame(self, frame: SampleFrame) -> dict[str, dict[str, float]]:
        scaled = {
            name: scale_sensor(name, imu, self.calibration)
            for name, imu in zip(BMI_SENSOR_NAMES, frame.bmi)
        }
        scaled["pelvis"] = scale_sensor("pelvis", frame.pelvis, self.calibration)
        return scaled

    @staticmethod
    def _joint_angles(segments: SegmentAngles) -> JointAngles:
        return JointAngles(
            left_ankle=segments.left_foot - segments.left_shank,
            right_ankle=segments.right_foot - segments.right_shank,
            left_knee=segments.left_thigh - segments.left_shank,
            right_knee=segments.right_thigh - segments.right_shank,
            left_hip=segments.left_thigh - segments.pelvis,
            right_hip=segments.right_thigh - segments.pelvis,
        )

    def _clinical_summary(self, metrics) -> ClinicalSummary:
        stance_si = robinson_si(metrics.left_stance_s, metrics.right_stance_s)
        knee_si = robinson_si(metrics.left_knee_rom_deg, metrics.right_knee_rom_deg)
        hip_si = robinson_si(metrics.left_hip_rom_deg, metrics.right_hip_rom_deg)
        si_pct = max(stance_si, knee_si, hip_si)
        affected_side = self._affected_side(metrics)
        pattern = "unknown"
        confidence = 0.0

        if self._classifier is not None and metrics.left_knee_rom_deg is not None:
            features = {
                "stride_length_left": metrics.left_swing_s or 1.0,
                "stride_length_right": metrics.right_swing_s or 1.0,
                "stance_time_left": metrics.left_stance_s or 0.0,
                "stance_time_right": metrics.right_stance_s or 0.0,
                "knee_rom_left": metrics.left_knee_rom_deg or 0.0,
                "knee_rom_right": metrics.right_knee_rom_deg or 0.0,
                "hip_rom_left": metrics.left_hip_rom_deg or 0.0,
                "hip_rom_right": metrics.right_hip_rom_deg or 0.0,
                "cadence": metrics.cadence_spm or 0.0,
            }
            try:
                diagnosis = self._classifier.classify_gait_pattern(features)
                pattern = str(diagnosis.get("pattern_type", "unknown"))
                confidence = float(diagnosis.get("confidence", 0.0))
            except Exception:
                pattern = "unknown"
                confidence = 0.0

        return ClinicalSummary(
            symmetry_index_pct=si_pct,
            symmetry_zone=_zone_for_si(si_pct),
            affected_side=affected_side,
            classifier_pattern=pattern,
            confidence=confidence,
        )

    @staticmethod
    def _affected_side(metrics) -> str:
        left_score = 0
        right_score = 0
        comparisons = [
            (metrics.left_stance_s, metrics.right_stance_s, "shorter"),
            (metrics.left_knee_rom_deg, metrics.right_knee_rom_deg, "smaller"),
            (metrics.left_hip_rom_deg, metrics.right_hip_rom_deg, "smaller"),
        ]
        for left, right, _mode in comparisons:
            if left is None or right is None:
                continue
            if abs(left - right) < 1e-6:
                continue
            if left < right:
                left_score += 1
            else:
                right_score += 1
        if left_score == right_score:
            return "unknown"
        return "left" if left_score > right_score else "right"
