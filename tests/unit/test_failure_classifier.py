from __future__ import annotations

import numpy as np
import pytest

from common.failure_classifier import FailureMode, classify_failure, make_row


def test_classify_stuck_when_velocity_is_zero() -> None:
    qpos = np.array([0.0, 1.0, 0.0])
    qvel = np.zeros(3)
    assert classify_failure(qpos, qvel, 3) == FailureMode.STUCK.value


def test_classify_fall_down_by_hip_height() -> None:
    qpos = np.array([0.0, 0.2, 0.0])
    qvel = np.array([0.1, 0.0, 0.0])
    assert classify_failure(qpos, qvel, 3, hip_z_threshold=0.3) == "fall_down"


def test_classify_posture_collapse_by_velocity_norm() -> None:
    qpos = np.array([0.0, 1.0, 0.0])
    qvel = np.array([0.0, 6.0, 0.0])
    assert classify_failure(qpos, qvel, 3, vel_threshold=5.0) == "posture_collapse"


def test_classify_different_nq_layout() -> None:
    qpos = np.array([0.0, 0.0, 0.0, 0.8, 99.0])
    qvel = np.array([0.1, 0.0, 0.0, 0.0, 99.0])
    assert classify_failure(qpos, qvel, 4, hip_z_index=3) == "success"


def test_classify_rejects_bad_layout() -> None:
    with pytest.raises(ValueError, match="hip_z_index"):
        classify_failure(np.ones(3), np.ones(3), 3, hip_z_index=3)


def test_make_row_serializes_named_arrays() -> None:
    row = make_row(
        np.array([1.0, 2.0]),
        np.array([3.0]),
        qpos_keys=["hip_x", "hip_z"],
        qvel_keys=["hip_x_vel"],
        mode="test",
    )
    assert row == {
        "hip_x": 1.0,
        "hip_z": 2.0,
        "hip_x_vel": 3.0,
        "mode": "test",
    }
