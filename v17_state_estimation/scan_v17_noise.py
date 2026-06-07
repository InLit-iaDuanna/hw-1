"""V17 噪声容限扫描：找到传感器噪声导致步态失败的临界 noise_scale。"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HW1_ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HW1_ROOT))

from sensor_model import SensorNoiseParams  # noqa: E402
from simulate_v17 import (  # noqa: E402
    OUT_DIR,
    PassiveArmsParams,
    V17Params,
    make_v17_fsm,
    run_simulation_v17,
)

from common.motor_dynamics import PRESETS  # noqa: E402

ARM_MASS = 0.01
FOOT_RADIUS = 0.042
LEG_SCALE = 1.02
DURATION = 12.0

NOISE_SCALE_GRID = [0.0, 0.5, 1.0, 2.0, 3.0, 5.0, 8.0, 12.0, 20.0]


def make_params(noise_scale: float) -> V17Params:
    base0 = PassiveArmsParams()
    base = replace(
        base0,
        duration=DURATION,
        arm_mass=ARM_MASS,
        arm_length=0.40,
        arm_damping=0.02,
        arm_stiffness=0.0,
        foot_radius=FOOT_RADIUS,
        thigh_length=base0.thigh_length * LEG_SCALE,
        shank_length=base0.shank_length * LEG_SCALE,
        step_length=base0.step_length * LEG_SCALE,
    )
    motor = PRESETS["mx64ar"]
    return V17Params(
        base=base,
        fsm=make_v17_fsm(base),
        hip_motor=motor,
        knee_motor=motor,
        compensate_friction=True,
        sensor_noise=SensorNoiseParams(noise_scale=noise_scale),
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for ns in NOISE_SCALE_GRID:
        prefix = f"v17_noise_scan_ns{ns:.1f}"
        _, summary = run_simulation_v17(
            make_params(ns), save_prefix=prefix, sample_hz=160.0
        )
        rows.append(
            {
                "noise_scale": ns,
                "success": summary["success"],
                "forward_distance": summary["forward_distance"],
                "alt_touchdowns": summary["alternating_touchdowns"],
                "simulated_time": summary["simulated_time"],
                "rmse_vx": summary["estimation_rmse_vx"],
                "rmse_hip_x": summary["estimation_rmse_hip_x"],
                "failure": summary["failure"],
            }
        )
        status = "PASS" if summary["success"] else "FAIL"
        print(
            f"  noise_scale={ns:<5.1f}  {status}  fwd={summary['forward_distance']:.2f}m  "
            f"alt_td={summary['alternating_touchdowns']}  rmse_vx={summary['estimation_rmse_vx']:.4f}"
        )

    first_fail = next((r for r in rows if not r["success"]), None)
    last_pass = next((r for r in reversed(rows) if r["success"]), None)
    critical = first_fail["noise_scale"] if first_fail else float("inf")

    result = {
        "grid": NOISE_SCALE_GRID,
        "rows": rows,
        "critical_noise_scale": critical,
        "last_pass_noise_scale": last_pass["noise_scale"] if last_pass else None,
        "verdict": (
            "mx64ar_within_tolerance" if critical > 1.0 else "mx64ar_exceeds_tolerance"
        ),
    }

    out_path = OUT_DIR / "scan_v17_noise.json"
    out_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"\n{'='*50}")
    print("V17 噪声容限扫描结果")
    print(f"{'='*50}")
    print(f"Critical noise_scale: {critical}")
    print(
        f"MX-64AR spec (noise_scale=1.0): {'WITHIN TOLERANCE' if critical > 1.0 else 'EXCEEDS TOLERANCE'}"
    )
    print(f"Safety margin: {critical / 1.0:.1f}x")
    print(f"Verdict: {result['verdict']}")


if __name__ == "__main__":
    main()
