from __future__ import annotations

import math
from types import SimpleNamespace

import numpy as np
import pytest

from common.ik_utils import leg_ik_front_knee, ramp_height, smoothstep


def test_smoothstep_boundaries() -> None:
    assert smoothstep(-1.0, 0.0, 1.0) == pytest.approx(0.0)
    assert smoothstep(0.0, 0.0, 1.0) == pytest.approx(0.0)
    assert smoothstep(1.0, 0.0, 1.0) == pytest.approx(1.0)
    assert smoothstep(2.0, 0.0, 1.0) == pytest.approx(1.0)


def test_smoothstep_array_input() -> None:
    values = smoothstep(np.array([0.0, 0.5, 1.0]))
    np.testing.assert_allclose(values, np.array([0.0, 0.5, 1.0]))


def test_smoothstep_rejects_equal_edges() -> None:
    with pytest.raises(ValueError, match="edge0 and edge1"):
        smoothstep(0.5, 1.0, 1.0)


def test_ramp_height_legacy_params_mode() -> None:
    params = SimpleNamespace(gamma=0.1)
    assert ramp_height(2.0, params) == pytest.approx(-math.tan(0.1) * 2.0)


def test_ramp_height_smooth_transition() -> None:
    values = ramp_height(np.array([-1.0, 0.0, 0.5, 1.0, 2.0]), 0.0, 1.0)
    np.testing.assert_allclose(values, np.array([0.0, 0.0, 0.5, 1.0, 1.0]))


def test_leg_ik_front_knee_respects_knee_limit() -> None:
    params = SimpleNamespace(
        thigh_length=0.48,
        shank_length=0.52,
        leg_length=1.0,
        knee_limit_deg=35.0,
    )
    _, knee = leg_ik_front_knee(0.0, 1.0, 0.45, 0.1, params)
    assert 0.0 <= knee <= math.radians(35.0)


def test_leg_ik_front_knee_rejects_invalid_length() -> None:
    with pytest.raises(ValueError, match="leg_length"):
        leg_ik_front_knee(0.0, 1.0, 0.0)
