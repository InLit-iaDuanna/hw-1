"""
Abaqus/CAE post-processing: Extract heel-strike FEA results from ODB.

Run: abaqus cae noGUI=postprocess_heel_strike.py

Outputs:
  - Contact force history (JSON + PNG)
  - Peak stress / contact pressure
  - Energy balance verification
  - V22 design envelope summary
"""

import json
import os

from abaqus import *
from abaqusConstants import *
from odbAccess import *

ODB_PATH = "Job_HeelStrike.odb"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")


def extract_results():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    odb = openOdb(path=ODB_PATH, readOnly=True)

    step = odb.steps["Impact"]
    frames = step.frames

    # --- Contact force history from ground RP ---
    ground_rp = odb.rootAssembly.instances["GROUND-1"].nodeSets["GROUNDRP"]
    rf_history = []
    for frame in frames:
        rf_field = frame.fieldOutputs["RF"]
        rf_sub = rf_field.getSubset(region=ground_rp)
        if rf_sub.values:
            rf_val = rf_sub.values[0]
            rf_history.append(
                {
                    "time_ms": frame.frameValue * 1000,
                    "RF_x": rf_val.data[0],
                    "RF_y": rf_val.data[1],
                    "RF_z": rf_val.data[2],
                    "RF_mag": (
                        rf_val.data[0] ** 2 + rf_val.data[1] ** 2 + rf_val.data[2] ** 2
                    )
                    ** 0.5,
                }
            )

    # --- Peak stress in heel ---
    max_mises = 0.0
    max_cpress = 0.0
    max_peeq = 0.0
    peak_frame_idx = 0

    for i, frame in enumerate(frames):
        if "S" in frame.fieldOutputs:
            s_field = frame.fieldOutputs["S"]
            heel_region = odb.rootAssembly.instances["HEEL-1"].elementSets["ALLCELLS"]
            s_sub = s_field.getSubset(region=heel_region)
            for val in s_sub.values:
                if val.mises > max_mises:
                    max_mises = val.mises
                    peak_frame_idx = i

        if "CPRESS" in frame.fieldOutputs:
            cp_field = frame.fieldOutputs["CPRESS"]
            for val in cp_field.values:
                if val.data > max_cpress:
                    max_cpress = val.data

        if "PEEQ" in frame.fieldOutputs:
            peeq_field = frame.fieldOutputs["PEEQ"]
            heel_region = odb.rootAssembly.instances["HEEL-1"].elementSets["ALLCELLS"]
            peeq_sub = peeq_field.getSubset(region=heel_region)
            for val in peeq_sub.values:
                if val.data > max_peeq:
                    max_peeq = val.data

    # --- Energy balance ---
    energy = {}
    last_frame = frames[-1]
    for key in ("ALLKE", "ALLIE", "ALLSE", "ALLPD"):
        if key in odb.steps["Impact"].historyRegions.values()[0].historyOutputs:
            ho = odb.steps["Impact"].historyRegions.values()[0].historyOutputs[key]
            energy[key] = ho.data[-1][1]

    # --- Summary ---
    peak_rf = max(rf_history, key=lambda x: x["RF_mag"]) if rf_history else {}

    summary = {
        "material": "PLA",
        "peak_contact_force_N": peak_rf.get("RF_mag", 0),
        "peak_force_time_ms": peak_rf.get("time_ms", 0),
        "peak_von_mises_MPa": max_mises / 1e6,
        "peak_contact_pressure_MPa": max_cpress / 1e6,
        "peak_PEEQ": max_peeq,
        "plastic_deformation": max_peeq > 0.001,
        "energy_balance": energy,
        "v22_design_notes": {
            "heel_material_ok": max_mises < 60e6 * 0.7,  # 70% yield safety factor
            "contact_pressure_ok": max_cpress < 100e6,
            "recommendation": "",
        },
    }

    if summary["v22_design_notes"]["heel_material_ok"]:
        summary["v22_design_notes"][
            "recommendation"
        ] = "PLA heel adequate for walking loads"
    else:
        summary["v22_design_notes"][
            "recommendation"
        ] = "PLA heel exceeds 70% yield - consider TPU damping layer or AL6061"

    # Save outputs
    with open(os.path.join(OUTPUT_DIR, "heel_strike_results.json"), "w") as f:
        json.dump(summary, f, indent=2)

    with open(os.path.join(OUTPUT_DIR, "contact_force_history.json"), "w") as f:
        json.dump(rf_history, f, indent=2)

    print("=== Heel-Strike FEA Results ===")
    print(
        "  Peak contact force: {:.1f} N at t={:.2f} ms".format(
            summary["peak_contact_force_N"], summary["peak_force_time_ms"]
        )
    )
    print("  Peak von Mises: {:.1f} MPa".format(summary["peak_von_mises_MPa"]))
    print("  Peak CPRESS: {:.1f} MPa".format(summary["peak_contact_pressure_MPa"]))
    print(f"  Plastic strain: {max_peeq:.4f}")
    print("  Design verdict: {}".format(summary["v22_design_notes"]["recommendation"]))

    odb.close()
    return summary


if __name__ == "__main__":
    extract_results()
