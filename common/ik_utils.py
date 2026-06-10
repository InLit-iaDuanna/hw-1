"""Shared inverse-kinematics and gait interpolation helpers.

The simulation versions historically carried local copies of these small
helpers.  This module keeps those call sites compatible while offering a more
general API for tests and new versions.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np


def _return_scalar_if_scalar(original: Any, value: np.ndarray) -> float | np.ndarray:
    if np.isscalar(original):
        return float(value)
    return value


def smoothstep(
    x: float | np.ndarray,
    edge0: float = 0.0,
    edge1: float = 1.0,
) -> float | np.ndarray:
    """Interpolate smoothly from 0 to 1 over ``[edge0, edge1]``.

    Args:
        x: Scalar or NumPy array input.
        edge0: Lower transition edge.
        edge1: Upper transition edge.  Must differ from ``edge0``.

    Returns:
        A scalar for scalar input, otherwise a NumPy array.  Values below
        ``edge0`` return 0, and values above ``edge1`` return 1.

    Example:
        >>> smoothstep(0.5)
        0.5
        >>> smoothstep(np.array([0.0, 0.5, 1.0]))
        array([0. , 0.5, 1. ])
    """
    if edge0 == edge1:
        raise ValueError("edge0 and edge1 must differ")

    x_arr = np.asarray(x, dtype=float)
    u = np.clip((x_arr - edge0) / (edge1 - edge0), 0.0, 1.0)
    y = u * u * (3.0 - 2.0 * u)
    return _return_scalar_if_scalar(x, y)


def ramp_height(
    x: float | np.ndarray,
    params_or_x0: Any,
    x1: float | None = None,
    *,
    height0: float = 0.0,
    height1: float = 1.0,
) -> float | np.ndarray:
    """Compute ramp terrain height or a smooth normalized ramp.

    This function intentionally supports the legacy version call
    ``ramp_height(x, params)`` where ``params.gamma`` is the slope in radians.
    It also supports ``ramp_height(x, gamma)`` and the test-friendly
    ``ramp_height(x, x0, x1, height0=..., height1=...)`` form.

    Args:
        x: Scalar or NumPy array position.
        params_or_x0: Parameter object with ``gamma``, a numeric slope angle in
            radians, or the lower edge ``x0`` for the smooth-ramp form.
        x1: Upper edge for the smooth-ramp form.  If omitted, slope mode is
            used.
        height0: Output height at and below ``x0``.
        height1: Output height at and above ``x1``.

    Returns:
        Ramp height as a scalar or NumPy array matching ``x``.

    Example:
        >>> ramp_height(1.0, 0.1)
        -0.10033467208545055
        >>> ramp_height(np.array([0.0, 0.5, 1.0]), 0.0, 1.0)
        array([0. , 0.5, 1. ])
    """
    x_arr = np.asarray(x, dtype=float)

    if x1 is None:
        gamma = getattr(params_or_x0, "gamma", params_or_x0)
        y = -math.tan(float(gamma)) * x_arr
        return _return_scalar_if_scalar(x, y)

    s = smoothstep(x_arr, float(params_or_x0), float(x1))
    y = float(height0) + (float(height1) - float(height0)) * s
    return _return_scalar_if_scalar(x, np.asarray(y, dtype=float))


def _leg_lengths(
    params: Any | None,
    thigh_length: float | None,
    shank_length: float | None,
    leg_length: float | None,
) -> tuple[float, float]:
    if params is not None:
        thigh_length = getattr(params, "thigh_length", thigh_length)
        shank_length = getattr(params, "shank_length", shank_length)
        leg_length = getattr(params, "leg_length", leg_length)

    if thigh_length is None and shank_length is None:
        if leg_length is None:
            raise ValueError("Provide thigh_length/shank_length or leg_length")
        if leg_length <= 0.0:
            raise ValueError("leg_length must be positive")
        thigh_length = shank_length = 0.5 * float(leg_length)
    elif thigh_length is None or shank_length is None:
        raise ValueError("thigh_length and shank_length must be provided together")

    thigh = float(thigh_length)
    shank = float(shank_length)
    if thigh <= 0.0 or shank <= 0.0:
        raise ValueError("leg segment lengths must be positive")
    return thigh, shank


def leg_ik_front_knee(
    hip_x: float,
    hip_z: float,
    foot_x: float,
    foot_z: float | None = None,
    params: Any | None = None,
    *,
    thigh_length: float | None = None,
    shank_length: float | None = None,
    leg_length: float | None = None,
    knee_limit_deg: float | None = None,
    prefer_straight: bool = False,
) -> tuple[float, float]:
    """Solve 2D leg inverse kinematics with a forward-bending knee.

    The legacy version call is ``leg_ik_front_knee(hip_x, hip_z, foot_x,
    foot_z, params)``.  A compact call is also supported:
    ``leg_ik_front_knee(dx, dz, leg_length)`` with equal thigh/shank lengths.

    Args:
        hip_x: Hip x coordinate, or hip-foot x offset in compact mode.
        hip_z: Hip z coordinate, or hip-foot z offset in compact mode.
        foot_x: Foot x coordinate, or total leg length in compact mode.
        foot_z: Foot z coordinate.  Omit for compact mode.
        params: Optional object with ``thigh_length``, ``shank_length``,
            ``leg_length`` and ``knee_limit_deg`` attributes.
        thigh_length: Upper-leg length when ``params`` is not supplied.
        shank_length: Lower-leg length when ``params`` is not supplied.
        leg_length: Total leg length for compact/equal-segment mode.
        knee_limit_deg: Maximum knee flexion in degrees.
        prefer_straight: Return a straight leg when the target is at or beyond
            reach instead of clipping to a tiny flexion.

    Returns:
        ``(thigh_angle, knee_angle)`` in radians.

    Example:
        >>> leg_ik_front_knee(0.0, 1.0, 0.0, 0.0, leg_length=1.0)
        (0.0, 0.0)
    """
    if foot_z is None and params is None:
        px = float(hip_x)
        pz = float(hip_z)
        leg_length = float(foot_x)
    else:
        if foot_z is None:
            raise ValueError("foot_z is required for coordinate IK mode")
        px = float(hip_x) - float(foot_x)
        pz = float(hip_z) - float(foot_z)

    thigh, shank = _leg_lengths(params, thigh_length, shank_length, leg_length)
    if knee_limit_deg is None:
        knee_limit_deg = float(getattr(params, "knee_limit_deg", 180.0))

    reach = thigh + shank
    d = math.hypot(px, pz)
    if prefer_straight or d >= reach - 1e-5:
        return math.atan2(px, pz), 0.0

    d = float(np.clip(d, abs(thigh - shank) + 1e-5, reach - 1e-5))
    base = math.atan2(px, pz)
    cos_delta = (thigh**2 + d**2 - shank**2) / (2.0 * thigh * d)
    delta = math.acos(float(np.clip(cos_delta, -1.0, 1.0)))
    thigh_angle = base - delta
    knee_x = float(hip_x) - thigh * math.sin(thigh_angle)
    knee_z = float(hip_z) - thigh * math.cos(thigh_angle)
    target_foot_x = 0.0 if foot_z is None else float(foot_x)
    target_foot_z = 0.0 if foot_z is None else float(foot_z)
    shank_angle = math.atan2(knee_x - target_foot_x, knee_z - target_foot_z)
    knee = float(
        np.clip(
            shank_angle - thigh_angle,
            0.0,
            math.radians(float(knee_limit_deg)),
        )
    )
    return thigh_angle, knee


__all__ = ["smoothstep", "ramp_height", "leg_ik_front_knee"]
