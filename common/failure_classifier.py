"""Shared failure classification utilities for gait simulations."""

from __future__ import annotations

from enum import Enum
from typing import Any

import numpy as np

from .ik_utils import ramp_height


class FailureMode(str, Enum):
    """Canonical failure labels used by reusable classifiers."""

    SUCCESS = "success"
    STUCK = "stuck"
    FALL_DOWN = "fall_down"
    POSTURE_COLLAPSE = "posture_collapse"
    NAN_OR_UNSTABLE = "nan_or_unstable"
    FLY_AWAY = "fly_away"
    PENETRATION = "penetration"


def _classify_arrays(
    qpos: np.ndarray,
    qvel: np.ndarray,
    nq: int,
    *,
    hip_z_threshold: float,
    vel_threshold: float,
    hip_z_index: int,
    stuck_velocity_threshold: float,
) -> str:
    if nq <= 0:
        raise ValueError("nq must be positive")
    if qpos.size < nq or qvel.size < nq:
        raise ValueError("qpos and qvel must contain at least nq values")
    if hip_z_index < 0 or hip_z_index >= nq:
        raise ValueError("hip_z_index must be within the first nq entries")

    qpos_view = qpos[:nq]
    qvel_view = qvel[:nq]
    if not np.all(np.isfinite(qpos_view)) or not np.all(np.isfinite(qvel_view)):
        return FailureMode.POSTURE_COLLAPSE.value

    if float(qpos_view[hip_z_index]) < hip_z_threshold:
        return FailureMode.FALL_DOWN.value

    vel_norm = float(np.linalg.norm(qvel_view))
    if vel_norm > vel_threshold:
        return FailureMode.POSTURE_COLLAPSE.value
    if vel_norm <= stuck_velocity_threshold:
        return FailureMode.STUCK.value
    return FailureMode.SUCCESS.value


def _site_margin(model: Any, data: Any, site_name: str, params: Any) -> float | None:
    try:
        import mujoco

        site_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, site_name)
    except Exception:
        return None
    if site_id < 0:
        return None
    pos = data.site_xpos[site_id]
    return float(pos[2] - ramp_height(float(pos[0]), params))


def _classify_mujoco_like(
    model: Any,
    data: Any,
    params: Any,
    start_x: float,
    t: float,
) -> str:
    if not np.all(np.isfinite(data.qpos)) or not np.all(np.isfinite(data.qvel)):
        return FailureMode.NAN_OR_UNSTABLE.value
    if float(np.linalg.norm(data.qvel)) > 45.0:
        return FailureMode.NAN_OR_UNSTABLE.value

    hip_x, hip_z = float(data.qpos[0]), float(data.qpos[1])
    hip_clearance = hip_z - ramp_height(hip_x, params)
    if hip_clearance < 0.22:
        return FailureMode.FALL_DOWN.value
    if hip_clearance > 2.5:
        return FailureMode.FLY_AWAY.value

    margins = [
        _site_margin(model, data, "left_heel_site", params),
        _site_margin(model, data, "left_toe_site", params),
        _site_margin(model, data, "right_heel_site", params),
        _site_margin(model, data, "right_toe_site", params),
    ]
    valid_margins = [m for m in margins if m is not None]
    if valid_margins and min(valid_margins) < -0.12:
        return FailureMode.PENETRATION.value
    if t > 4.0 and hip_x - start_x < 0.20:
        return FailureMode.STUCK.value
    return ""


def classify_failure(
    qpos: Any,
    qvel: Any | None = None,
    nq: int | Any | None = None,
    *legacy_args: Any,
    hip_z_threshold: float = 0.3,
    vel_threshold: float = 5.0,
    hip_z_index: int = 1,
    stuck_velocity_threshold: float = 1e-6,
) -> str:
    """Classify a gait state or a legacy MuJoCo simulation state.

    Preferred array form:
        ``classify_failure(qpos, qvel, nq, hip_z_index=1)``

    Legacy compatibility form:
        ``classify_failure(model, data, params, start_x, t)``

    Returns:
        Array form returns one of ``'stuck'``, ``'fall_down'``,
        ``'posture_collapse'`` or ``'success'``.  Legacy MuJoCo form preserves
        historical version labels and returns ``''`` when no failure is active.
    """
    if qvel is not None and hasattr(qvel, "qpos") and hasattr(qvel, "qvel"):
        if nq is None:
            raise ValueError("params must be provided for legacy MuJoCo form")
        if len(legacy_args) < 2:
            raise ValueError("legacy MuJoCo form requires start_x and t")
        return _classify_mujoco_like(
            qpos,
            qvel,
            nq,
            float(legacy_args[0]),
            float(legacy_args[1]),
        )

    if qvel is None or nq is None or not isinstance(nq, int):
        raise ValueError("array form requires qpos, qvel and integer nq")
    qpos_arr = np.asarray(qpos, dtype=float)
    qvel_arr = np.asarray(qvel, dtype=float)
    return _classify_arrays(
        qpos_arr,
        qvel_arr,
        nq,
        hip_z_threshold=hip_z_threshold,
        vel_threshold=vel_threshold,
        hip_z_index=hip_z_index,
        stuck_velocity_threshold=stuck_velocity_threshold,
    )


def make_row(
    qpos: np.ndarray,
    qvel: np.ndarray,
    qpos_keys: list[str] | None = None,
    qvel_keys: list[str] | None = None,
    **extra: float | int | str,
) -> dict[str, float | int | str]:
    """Build a flat telemetry row from position/velocity arrays.

    Args:
        qpos: Position vector.
        qvel: Velocity vector.
        qpos_keys: Optional names for ``qpos`` values.
        qvel_keys: Optional names for ``qvel`` values.
        **extra: Additional fields to merge into the row.

    Returns:
        A dictionary ready for CSV/JSON serialization.
    """
    qpos_arr = np.asarray(qpos, dtype=float)
    qvel_arr = np.asarray(qvel, dtype=float)
    qpos_names = qpos_keys or [f"qpos_{i}" for i in range(qpos_arr.size)]
    qvel_names = qvel_keys or [f"qvel_{i}" for i in range(qvel_arr.size)]
    row: dict[str, float | int | str] = {}
    row.update({key: float(value) for key, value in zip(qpos_names, qpos_arr)})
    row.update({key: float(value) for key, value in zip(qvel_names, qvel_arr)})
    row.update(extra)
    return row


__all__ = ["FailureMode", "classify_failure", "make_row"]
