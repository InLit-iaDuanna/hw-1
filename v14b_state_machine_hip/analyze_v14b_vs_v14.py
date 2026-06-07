"""Compare the V14 V10-controller scan against V14b's V13.6 FSM scan."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HW1_ROOT = ROOT.parent
OUT_DIR = ROOT / "out"
V14_OUT_DIR = HW1_ROOT / "v14_passive_arms" / "out"


def _bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    return value.lower() == "true"


def load_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def aggregate(rows: list[dict]) -> dict[float, dict]:
    out: dict[float, dict] = defaultdict(
        lambda: {"success": 0, "total": 0, "forward_sum": 0.0}
    )
    for row in rows:
        mass = float(row["arm_mass"])
        out[mass]["total"] += 1
        out[mass]["success"] += 1 if _bool(row["success"]) else 0
        out[mass]["forward_sum"] += float(row["forward_distance"])
    for stats in out.values():
        stats["forward_mean"] = stats["forward_sum"] / max(1, stats["total"])
    return dict(out)


def main() -> None:
    v14_rows = load_csv(V14_OUT_DIR / "v14_arm_scan.csv")
    v14b_rows = load_csv(OUT_DIR / "v14b_arm_scan.csv")
    v14 = aggregate(v14_rows)
    v14b = aggregate(v14b_rows)
    masses = sorted(set(v14) | set(v14b))

    rows = []
    for mass in masses:
        a = v14.get(mass, {"success": 0, "total": 0, "forward_mean": 0.0})
        b = v14b.get(mass, {"success": 0, "total": 0, "forward_mean": 0.0})
        rows.append(
            {
                "arm_mass": mass,
                "v14_success": a["success"],
                "v14_total": a["total"],
                "v14b_success": b["success"],
                "v14b_total": b["total"],
                "delta_success": b["success"] - a["success"],
                "v14_forward_mean": a["forward_mean"],
                "v14b_forward_mean": b["forward_mean"],
                "delta_forward_mean": b["forward_mean"] - a["forward_mean"],
            }
        )

    critical = next(row for row in rows if abs(row["arm_mass"] - 0.05) < 1e-9)
    if critical["v14b_success"] >= 2:
        verdict = "pass"
        verdict_note = "V14b recovers part of the V10-failed arm_mass=0.05 row."
    elif critical["v14b_success"] == 1:
        verdict = "borderline_sensitivity_followup"
        verdict_note = "Only 1/5 in the critical row; report as borderline and open damping sensitivity later."
    else:
        verdict = "reject"
        verdict_note = "No critical-row recovery; do not promote V14b."

    OUT_DIR.mkdir(exist_ok=True)
    csv_path = OUT_DIR / "v14b_vs_v14_by_mass.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    v14_success = sum(1 for row in v14_rows if _bool(row["success"]))
    v14b_success = sum(1 for row in v14b_rows if _bool(row["success"]))
    summary = {
        "v14": {
            "success": v14_success,
            "total": len(v14_rows),
            "rate": v14_success / len(v14_rows),
        },
        "v14b": {
            "success": v14b_success,
            "total": len(v14b_rows),
            "rate": v14b_success / len(v14b_rows),
        },
        "by_mass": rows,
        "critical_arm_mass_0_05": critical,
        "verdict": verdict,
        "verdict_note": verdict_note,
        "academic_note": "V14b remains quasi-passive: hip+knee active, arms passive; no claim of pure passive or 3D quasi-passive walking.",
    }
    json_path = OUT_DIR / "v14b_vs_v14_summary.json"
    json_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(csv_path)
    print(json_path)


if __name__ == "__main__":
    main()
