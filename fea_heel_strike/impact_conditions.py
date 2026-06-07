"""
Extract heel-strike impact conditions from V10 MuJoCo simulation data.
Provides loading inputs for Abaqus FEA heel-strike analysis.
"""

import csv
import json
import math
import os

V10_DATA = os.path.join(
    os.path.dirname(__file__),
    "..",
    "v10_rolling_foot_biomimetic_gait",
    "out",
    "v10_rolling_foot_walk_data.csv",
)
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "out", "impact_conditions.json")

THIGH_L = 0.48
SHANK_L = 0.52
HIP_MASS = 5.0
EFFECTIVE_MASS = HIP_MASS / 2  # single-leg chain approximation

TD_TIMES = [6.263, 7.493, 8.72, 9.945]
TD_FEET = ["left", "right", "left", "right"]


def extract_impact_conditions():
    with open(V10_DATA) as f:
        rows = list(csv.DictReader(f))

    impacts = []
    for t_td, foot in zip(TD_TIMES, TD_FEET):
        row = min(rows, key=lambda r: abs(float(r["time"]) - t_td))
        t = float(row["time"])
        hip_vx = float(row["hip_x_vel"])
        hip_vz = float(row["hip_z_vel"])
        hip_w = float(row[foot + "_hip_vel"])
        knee_w = float(row[foot + "_knee_vel"])
        hip_angle = float(row[foot + "_hip"])
        knee_angle = float(row[foot + "_knee"])

        v_heel_z = (
            hip_vz
            - THIGH_L * hip_w * math.cos(hip_angle)
            - SHANK_L * (hip_w + knee_w) * math.cos(hip_angle + knee_angle)
        )
        v_heel_x = (
            hip_vx
            - THIGH_L * hip_w * math.sin(hip_angle)
            - SHANK_L * (hip_w + knee_w) * math.sin(hip_angle + knee_angle)
        )

        impacts.append(
            {
                "time": t,
                "foot": foot,
                "v_heel_x": round(v_heel_x, 5),
                "v_heel_z": round(v_heel_z, 5),
                "hip_angle_rad": round(hip_angle, 5),
                "knee_angle_rad": round(knee_angle, 5),
            }
        )

    vz_vals = [imp["v_heel_z"] for imp in impacts]
    vx_vals = [imp["v_heel_x"] for imp in impacts]

    result = {
        "source": "V10 rolling_foot_biomimetic_gait steady-state heel-strikes",
        "effective_mass_kg": EFFECTIVE_MASS,
        "heel_radius_m": 0.04,
        "ground_friction": 1.35,
        "impacts": impacts,
        "average_v_heel_z_m_s": round(sum(vz_vals) / len(vz_vals), 5),
        "average_v_heel_x_m_s": round(sum(vx_vals) / len(vx_vals), 5),
        "kinetic_energy_J": round(
            0.5 * EFFECTIVE_MASS * (sum(vz_vals) / len(vz_vals)) ** 2, 4
        ),
        "peak_force_estimate_N": round(
            EFFECTIVE_MASS * abs(sum(vz_vals) / len(vz_vals)) / 0.005, 1
        ),
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(result, f, indent=2)
    print(f"Impact conditions saved to {OUTPUT_PATH}")
    print(f"  v_heel_z = {result['average_v_heel_z_m_s']:.4f} m/s")
    print(f"  KE = {result['kinetic_energy_J']:.4f} J")
    print(f"  F_peak ~ {result['peak_force_estimate_N']:.0f} N")
    return result


if __name__ == "__main__":
    extract_impact_conditions()
