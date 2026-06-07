"""V13 单点仿真适配器：复用 V10 的 run_simulation，按 (slope, leg, foot, mass) 构造 RollingFootParams。

V13 不改物理，只暴露给 scan_atlas 一个干净的 evaluate(point) -> dict 接口。
"""

from __future__ import annotations

import sys
from dataclasses import asdict, replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V10_DIR = ROOT / "v10_rolling_foot_biomimetic_gait"
if str(V10_DIR) not in sys.path:
    sys.path.insert(0, str(V10_DIR))

from simulate_rolling_foot_gait_v10 import (
    RollingFootParams,
    run_simulation,
)  # noqa: E402

sys.path.insert(0, str(ROOT))
from common.energy_metrics import cost_of_transport  # noqa: E402

BASELINE = RollingFootParams(
    slope_deg=0.0,
    gait_period=0.80,
    hip_torque_limit=4.0,
    knee_torque_limit=4.0,
    hip_kp=30.0,
    hip_kd=6.0,
    knee_kp=16.0,
    knee_kd=2.0,
    initial_vx=0.03,
    torso_mass=0.05,
    foot_length=0.12,
    foot_radius=0.04,
    ankle_stiffness=10.0,
    ankle_damping=0.08,
    duration=12.0,
)


def make_params(
    *,
    slope_deg: float | None = None,
    leg_scale: float | None = None,
    foot_radius: float | None = None,
    torso_ratio: float | None = None,
    hip_kp: float | None = None,
    hip_kd: float | None = None,
    hip_kd_ratio: float | None = None,
    hip_torque_limit: float | None = None,
) -> RollingFootParams:
    """以 BASELINE 为基础，按维度键覆盖。leg_scale 等比缩放 thigh+shank。

    hip_kd_ratio: 若给定，hip_kd = hip_kp * ratio（覆盖 hip_kd 显式值）。
    """
    kwargs: dict[str, float] = {}
    if slope_deg is not None:
        kwargs["slope_deg"] = float(slope_deg)
    if leg_scale is not None:
        kwargs["thigh_length"] = float(BASELINE.thigh_length * leg_scale)
        kwargs["shank_length"] = float(BASELINE.shank_length * leg_scale)
        kwargs["step_length"] = float(BASELINE.step_length * leg_scale)
    if foot_radius is not None:
        kwargs["foot_radius"] = float(foot_radius)
    if torso_ratio is not None:
        kwargs["torso_mass"] = float(BASELINE.hip_mass * torso_ratio)
    if hip_kp is not None:
        kwargs["hip_kp"] = float(hip_kp)
    if hip_kd is not None:
        kwargs["hip_kd"] = float(hip_kd)
    if hip_kd_ratio is not None:
        kp_eff = kwargs.get("hip_kp", BASELINE.hip_kp)
        kwargs["hip_kd"] = float(kp_eff * hip_kd_ratio)
    if hip_torque_limit is not None:
        kwargs["hip_torque_limit"] = float(hip_torque_limit)
    return replace(BASELINE, **kwargs)


def evaluate(params: RollingFootParams, sample_hz: float = 40.0) -> dict:
    """跑一点，返回扁平指标 dict（包含 params、success、CoT、failure）。"""
    rows, summary = run_simulation(params, sample_hz=sample_hz)
    mass = params.hip_mass + 2 * params.torso_mass
    cot = (
        cost_of_transport(
            summary["active_input_energy_j"], mass, summary["forward_distance"]
        )
        if summary["success"]
        else float("nan")
    )
    return {
        **asdict(params),
        "success": bool(summary["success"]),
        "alternating_touchdowns": int(summary["alternating_touchdowns"]),
        "forward_distance": float(summary["forward_distance"]),
        "simulated_time": float(summary["simulated_time"]),
        "active_input_energy_j": float(summary["active_input_energy_j"]),
        "failure": str(summary["failure"]),
        "cot": float(cot),
        "score": float(summary["score"]),
    }


if __name__ == "__main__":
    import json

    p = make_params()
    print(json.dumps(evaluate(p), ensure_ascii=False, indent=2))
