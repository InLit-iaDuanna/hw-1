import math

from hardware_v1_detection.pc_receiver.pipeline import RealtimePipeline
from hardware_v1_detection.pc_receiver.protocol import (
    SAMPLE_VALUE_COUNT,
    FrameParser,
    encode_sample_frame,
)


def _counts_for_pitch(pitch_deg, accel_scale=4096.0):
    theta = math.radians(pitch_deg)
    ax = int(round(-math.sin(theta) * accel_scale))
    ay = 0
    az = int(round(math.cos(theta) * accel_scale))
    return ax, ay, az


def _frame(
    seq,
    t_s,
    pitches=None,
    left_gyro=0.0,
    right_gyro=0.0,
    left_accel_gain=1.0,
    right_accel_gain=1.0,
):
    pitches = pitches or {}
    values = []
    for name in (
        "left_foot",
        "right_foot",
        "left_shank",
        "right_shank",
        "left_thigh",
        "right_thigh",
    ):
        gain = (
            left_accel_gain
            if name == "left_foot"
            else right_accel_gain if name == "right_foot" else 1.0
        )
        ax, ay, az = _counts_for_pitch(pitches.get(name, 0.0))
        gy = (
            left_gyro
            if name == "left_foot"
            else right_gyro if name == "right_foot" else 0.0
        )
        values.extend(
            [
                int(round(ax * gain)),
                int(round(ay * gain)),
                int(round(az * gain)),
                0,
                int(round(gy * 32.768)),
                0,
            ]
        )
    ax, ay, az = _counts_for_pitch(pitches.get("pelvis", 0.0), accel_scale=256.0)
    values.extend([ax, ay, az, 0, 0, 0, 0, 0, 0])
    assert len(values) == SAMPLE_VALUE_COUNT
    packet = encode_sample_frame(
        seq=seq, ts_us=int(t_s * 1_000_000), status=0, values=values
    )
    return FrameParser().feed(packet)[0]


def test_pipeline_derives_segment_and_joint_angles():
    pipeline = RealtimePipeline(alpha=0.98)
    frame = _frame(
        1,
        0.0,
        pitches={
            "left_shank": 5.0,
            "left_thigh": 20.0,
            "right_shank": -3.0,
            "right_thigh": 12.0,
            "pelvis": 2.0,
        },
    )

    sample = pipeline.update(frame)

    assert sample.segments.left_thigh == pytest_approx(20.0, abs=0.2)
    assert sample.joints.left_knee == pytest_approx(15.0, abs=0.3)
    assert sample.joints.left_hip == pytest_approx(18.0, abs=0.3)
    assert sample.joints.right_knee == pytest_approx(15.0, abs=0.3)


def test_pipeline_detects_events_and_updates_symmetry_metrics():
    pipeline = RealtimePipeline()
    frames = [
        _frame(1, 0.00, left_accel_gain=1.35),
        _frame(2, 0.10, left_gyro=100.0),
        _frame(3, 0.50, right_accel_gain=1.35),
        _frame(4, 0.60, right_gyro=100.0),
        _frame(5, 1.00, left_accel_gain=1.35),
        _frame(6, 1.10, left_gyro=100.0),
        _frame(7, 1.50, right_accel_gain=1.35),
    ]
    samples = [pipeline.update(frame) for frame in frames]

    all_events = [event for sample in samples for event in sample.events]
    assert [(event.side, event.kind) for event in all_events] == [
        ("left", "heel_strike"),
        ("left", "toe_off"),
        ("right", "heel_strike"),
        ("right", "toe_off"),
        ("left", "heel_strike"),
        ("left", "toe_off"),
        ("right", "heel_strike"),
    ]
    assert samples[-1].metrics.cadence_spm == pytest_approx(120.0, abs=0.1)
    assert samples[-1].metrics.left_stance_s == pytest_approx(0.1, abs=0.01)
    assert samples[-1].clinical.symmetry_zone == "green"


def pytest_approx(*args, **kwargs):
    import pytest

    return pytest.approx(*args, **kwargs)
