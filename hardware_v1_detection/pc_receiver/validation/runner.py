"""A-track validation runner: replay synthesized frames through the pipeline.

Feeds simulation-derived ``SampleFrame``s into the *same* ``RealtimePipeline``
the live dashboard uses, then scores the L1-L4 outputs against the simulation
ground truth.

Scope (academic-integrity note): this measures **functional correctness of the
algorithm chain** — does L1 recover the input joint angles, does L2 fire near
the injected contact edges, are L3/L4 computed consistently. It does NOT assert
sensor-noise robustness or clinical validity. Those need real data.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

from hardware_v1_detection.pc_receiver.pipeline import DerivedSample, RealtimePipeline

from .synth import (
    SynthConfig,
    TrajectorySample,
    TrajectorySynthesizer,
    load_trajectory_csv,
)


@dataclass
class JointError:
    """L1 round-trip error for one joint (degrees)."""

    joint: str
    rmse_deg: float
    max_abs_deg: float
    n: int


@dataclass
class EventScore:
    """L2 event-timing score against injected contact edges."""

    side: str
    n_truth: int
    n_detected: int
    matched: int
    mean_latency_ms: float
    tolerance_ms: float

    @property
    def recall(self) -> float:
        return self.matched / self.n_truth if self.n_truth else 0.0

    @property
    def precision(self) -> float:
        return self.matched / self.n_detected if self.n_detected else 0.0


@dataclass
class ValidationReport:
    joint_errors: list[JointError] = field(default_factory=list)
    event_scores: list[EventScore] = field(default_factory=list)
    n_frames: int = 0
    final_metrics: dict = field(default_factory=dict)
    final_clinical: dict = field(default_factory=dict)

    def summary_lines(self) -> list[str]:
        lines = [
            f"frames replayed: {self.n_frames}",
            "",
            "L1 joint-angle round trip (deg):",
        ]
        for je in self.joint_errors:
            lines.append(
                f"  {je.joint:11s}  rmse={je.rmse_deg:6.3f}  max={je.max_abs_deg:6.3f}  n={je.n}"
            )
        lines.append("")
        lines.append("L2 event timing vs injected contact edges:")
        for es in self.event_scores:
            lines.append(
                f"  {es.side:5s} heel-strike  truth={es.n_truth} detected={es.n_detected} "
                f"matched={es.matched} recall={es.recall:.2f} prec={es.precision:.2f} "
                f"lat={es.mean_latency_ms:+.1f}ms (tol {es.tolerance_ms:.0f}ms)"
            )
        lines.append("")
        lines.append("L3/L4 final snapshot:")
        for key, value in self.final_metrics.items():
            lines.append(f"  {key}: {value}")
        for key, value in self.final_clinical.items():
            lines.append(f"  {key}: {value}")
        return lines


def _truth_segment_pitch_deg(
    sample: TrajectorySample, joint: str, pelvis_pitch: float
) -> float:
    """Ground-truth joint angle in degrees (matches pipeline's joint defs)."""

    left_thigh = pelvis_pitch + sample.left_hip
    left_shank = left_thigh - sample.left_knee
    right_thigh = pelvis_pitch + sample.right_hip
    right_shank = right_thigh - sample.right_knee

    table = {
        "left_knee": left_thigh - left_shank,  # == left_knee angle
        "right_knee": right_thigh - right_shank,
        "left_hip": left_thigh - pelvis_pitch,  # == left_hip angle
        "right_hip": right_thigh - pelvis_pitch,
        "left_ankle": (left_shank + sample.left_ankle) - left_shank,
        "right_ankle": (right_shank + sample.right_ankle) - right_shank,
    }
    return math.degrees(table[joint])


def _truth_contact_edges(samples: list[TrajectorySample], side: str) -> list[float]:
    attr = f"{side}_contact"
    edges: list[float] = []
    prev = False
    for sample in samples:
        now = getattr(sample, attr)
        if now and not prev:
            edges.append(sample.t_s)
        prev = now
    return edges


def run_validation(
    csv_path: str | Path,
    config: SynthConfig | None = None,
    event_tolerance_ms: float = 80.0,
    warmup_frames: int = 5,
) -> ValidationReport:
    config = config or SynthConfig()
    samples = load_trajectory_csv(csv_path)
    synthesizer = TrajectorySynthesizer(config)
    frames = synthesizer.synthesize(samples)

    pipeline = RealtimePipeline()
    derived: list[DerivedSample] = [pipeline.update(frame) for frame in frames]

    report = ValidationReport(n_frames=len(frames))

    # ---- L1 joint-angle round trip ----
    joints = ("left_hip", "right_hip", "left_knee", "right_knee")
    for joint in joints:
        sq = 0.0
        max_abs = 0.0
        count = 0
        for idx in range(warmup_frames, len(samples)):
            truth = _truth_segment_pitch_deg(
                samples[idx], joint, config.pelvis_pitch_rad
            )
            est = derived[idx].joints.as_dict()[joint]
            err = est - truth
            sq += err * err
            max_abs = max(max_abs, abs(err))
            count += 1
        rmse = math.sqrt(sq / count) if count else 0.0
        report.joint_errors.append(JointError(joint, rmse, max_abs, count))

    # ---- L2 event timing ----
    for side in ("left", "right"):
        truth_edges = _truth_contact_edges(samples, side)
        detected = [
            ev.time_s
            for d in derived
            for ev in d.events
            if ev.side == side and ev.kind == "heel_strike"
        ]
        report.event_scores.append(
            _score_events(side, truth_edges, detected, event_tolerance_ms)
        )

    # ---- L3/L4 final snapshot ----
    if derived:
        last = derived[-1]
        m = last.metrics
        report.final_metrics = {
            "cadence_spm": round(m.cadence_spm, 1),
            "left_stance_s": _round(m.left_stance_s),
            "right_stance_s": _round(m.right_stance_s),
            "left_knee_rom_deg": _round(m.left_knee_rom_deg),
            "right_knee_rom_deg": _round(m.right_knee_rom_deg),
            "left_hip_rom_deg": _round(m.left_hip_rom_deg),
            "right_hip_rom_deg": _round(m.right_hip_rom_deg),
        }
        c = last.clinical
        report.final_clinical = {
            "symmetry_index_pct": round(c.symmetry_index_pct, 1),
            "symmetry_zone": c.symmetry_zone,
            "affected_side": c.affected_side,
        }
    return report


def _score_events(
    side: str, truth_edges: list[float], detected: list[float], tol_ms: float
) -> EventScore:
    tol_s = tol_ms / 1000.0
    used = [False] * len(detected)
    latencies: list[float] = []
    matched = 0
    for t_truth in truth_edges:
        best_j = -1
        best_dt = tol_s
        for j, t_det in enumerate(detected):
            if used[j]:
                continue
            dt = abs(t_det - t_truth)
            if dt <= best_dt:
                best_dt = dt
                best_j = j
        if best_j >= 0:
            used[best_j] = True
            matched += 1
            latencies.append((detected[best_j] - t_truth) * 1000.0)
    mean_lat = sum(latencies) / len(latencies) if latencies else 0.0
    return EventScore(
        side=side,
        n_truth=len(truth_edges),
        n_detected=len(detected),
        matched=matched,
        mean_latency_ms=mean_lat,
        tolerance_ms=tol_ms,
    )


def _round(value: float | None) -> float | None:
    return None if value is None else round(value, 3)
