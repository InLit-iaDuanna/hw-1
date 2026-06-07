"""
Post-process heel-strike ODB: extract reaction force history, peak stress, energy.
Run: abaqus python postprocess_odb.py
(from fea_heel_strike/out/ directory, uses abaqus python - no CAE license needed)
"""

import json
import os
import sys as _sys

from abaqusConstants import *
from odbAccess import openOdb

ODB_PATH = _sys.argv[1] if len(_sys.argv) > 1 else "Job_HeelStrike.odb"
_job_name = ODB_PATH.replace(".odb", "")
OUT_DIR = (
    os.path.dirname(os.path.abspath(__file__)) if "__file__" in dir() else os.getcwd()
)


def main():
    odb = openOdb(path=ODB_PATH, readOnly=True)
    step = odb.steps["Impact"]
    frames = step.frames

    # --- Reaction force history from ground RP ---
    rf_history = []
    hr_keys = odb.steps["Impact"].historyRegions.keys()
    for hr_name in hr_keys:
        hr = odb.steps["Impact"].historyRegions[hr_name]
        if "RF2" in hr.historyOutputs:
            rf2_data = hr.historyOutputs["RF2"].data
            has_rf1 = "RF1" in hr.historyOutputs
            rf1_data_list = hr.historyOutputs["RF1"].data if has_rf1 else None
            for i, (t, val) in enumerate(rf2_data):
                rf_r = rf1_data_list[i][1] if rf1_data_list else 0.0
                rf_history.append(
                    {
                        "time_ms": t * 1000,
                        "RF_axial_N": val,
                        "RF_radial_N": rf_r,
                    }
                )
            break

    # --- Peak von Mises stress ---
    max_mises = 0.0
    max_peeq = 0.0
    peak_time = 0.0

    for frame in frames:
        if "S" not in frame.fieldOutputs:
            continue
        s_field = frame.fieldOutputs["S"]
        for val in s_field.values:
            if val.mises > max_mises:
                max_mises = val.mises
                peak_time = frame.frameValue

        if "PEEQ" in frame.fieldOutputs:
            peeq_field = frame.fieldOutputs["PEEQ"]
            for val in peeq_field.values:
                if val.data > max_peeq:
                    max_peeq = val.data

    # --- Energy history ---
    energy = {}
    for hr_name in hr_keys:
        hr = odb.steps["Impact"].historyRegions[hr_name]
        for key in ("ALLKE", "ALLIE", "ALLPD", "ALLSE", "ETOTAL"):
            if key in hr.historyOutputs:
                data = hr.historyOutputs[key].data
                if data:
                    energy[key] = data[-1][1]
        if energy:
            break

    # --- Peak reaction force ---
    peak_rf = 0.0
    peak_rf_time = 0.0
    for entry in rf_history:
        rf_mag = abs(entry["RF_axial_N"])
        if rf_mag > peak_rf:
            peak_rf = rf_mag
            peak_rf_time = entry["time_ms"]

    # --- Summary ---
    yield_stress = 60.0e6  # PLA
    safety_factor = yield_stress / max_mises if max_mises > 0 else 999

    summary = {
        "analysis": "HeelStrike_V10_Axisymmetric_Explicit",
        "status": "COMPLETED",
        "material": "PLA",
        "peak_contact_force_N": round(peak_rf, 2),
        "peak_force_time_ms": round(peak_rf_time, 4),
        "peak_von_mises_Pa": round(max_mises, 0),
        "peak_von_mises_MPa": round(max_mises / 1e6, 2),
        "safety_factor_yield": round(safety_factor, 2),
        "peak_PEEQ": round(max_peeq, 6),
        "plastic_deformation": max_peeq > 0.001,
        "energy_balance": energy,
        "v22_design_verdict": "",
    }

    if safety_factor >= 1.5:
        summary["v22_design_verdict"] = "PLA adequate (SF=%.1f)" % safety_factor
    elif safety_factor >= 1.0:
        summary["v22_design_verdict"] = (
            "PLA marginal (SF=%.2f) - add TPU damping layer" % safety_factor
        )
    else:
        summary["v22_design_verdict"] = (
            "PLA FAILS (SF=%.2f) - use AL6061 or redesign" % safety_factor
        )

    # --- Write outputs ---
    with open(os.path.join(OUT_DIR, _job_name + "_results.json"), "w") as f:
        json.dump(summary, f, indent=2)

    with open(os.path.join(OUT_DIR, _job_name + "_rf_history.json"), "w") as f:
        json.dump(rf_history, f, indent=2)

    print("=== Heel-Strike FEA Results ===")
    print("  Peak contact force: %.1f N at t=%.3f ms" % (peak_rf, peak_rf_time))
    print("  Peak von Mises: %.2f MPa" % (max_mises / 1e6))
    print("  Safety factor: %.2f" % safety_factor)
    print("  Peak plastic strain: %.6f" % max_peeq)
    print("  Verdict: %s" % summary["v22_design_verdict"])
    print(
        "  Energy: KE=%.4f J, IE=%.4f J, PD=%.4f J"
        % (energy.get("ALLKE", 0), energy.get("ALLIE", 0), energy.get("ALLPD", 0))
    )

    odb.close()


if __name__ == "__main__":
    main()
