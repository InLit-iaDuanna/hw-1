"""Analyze V14c arm-mass lightening scan outputs.

Reads ``out/v14c_C_foot_leg.csv`` and writes:

* ``out/v14c_C_heatmaps.png``
* ``out/v14c_vs_v14b_v1361best.json``
"""

from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from collections.abc import Iterable
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "out"
SCAN_CSV = OUT_DIR / "v14c_C_foot_leg.csv"
HEATMAP_PATH = OUT_DIR / "v14c_C_heatmaps.png"
SUMMARY_PATH = OUT_DIR / "v14c_vs_v14b_v1361best.json"

EXPECTED_MASSES = (0.01, 0.02, 0.03, 0.05)
CELL_PRECISION = 3

V1361_BEST_NO_ARMS = {
    (0.042, 0.980),
    (0.042, 1.020),
    (0.042, 1.060),
    (0.046, 1.060),
    (0.046, 1.100),
}
V14B_CELLS = {
    (0.038, 1.020),
    (0.042, 0.980),
    (0.042, 1.020),
}


def parse_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def finite_float(value: object, default: float = 0.0) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return out if math.isfinite(out) else default


def key_float(value: object) -> float:
    return round(float(value), CELL_PRECISION)


def cell_key(row: dict[str, str]) -> tuple[float, float]:
    return (key_float(row["foot_radius_x"]), key_float(row["leg_scale_y"]))


def cell_list(cells: Iterable[tuple[float, float]]) -> list[list[float]]:
    return [[x, y] for x, y in sorted(cells)]


def load_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing scan CSV: {path}. Run the V14c C foot/leg scan before analysis."
        )
    with path.open("r", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError(f"Scan CSV is empty: {path}")

    required = {"arm_mass", "foot_radius_x", "leg_scale_y", "success", "failure"}
    missing = required - set(rows[0])
    if missing:
        raise ValueError(f"Scan CSV missing required columns: {sorted(missing)}")
    return rows


def summarize_by_mass(rows: list[dict[str, str]]) -> dict[float, dict]:
    grouped: dict[float, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[key_float(row["arm_mass"])].append(row)

    summary: dict[float, dict] = {}
    for mass, mass_rows in grouped.items():
        success_rows = [row for row in mass_rows if parse_bool(row["success"])]
        success_cells = {cell_key(row) for row in success_rows}
        failures = Counter(
            (row.get("failure") or "completed").strip() or "completed"
            for row in mass_rows
        )
        forward_values = [
            finite_float(row.get("forward_distance")) for row in mass_rows
        ]
        score_values = [finite_float(row.get("score")) for row in mass_rows]
        summary[mass] = {
            "arm_mass": mass,
            "total_n": len(mass_rows),
            "success_n": len(success_rows),
            "success_rate_pct": 100.0 * len(success_rows) / max(1, len(mass_rows)),
            "success_cells": success_cells,
            "failure_distribution": dict(sorted(failures.items())),
            "forward_mean_m": sum(forward_values) / max(1, len(forward_values)),
            "score_mean": sum(score_values) / max(1, len(score_values)),
        }
    return dict(sorted(summary.items()))


def health_verdict(success_n_005: int | None) -> str:
    if success_n_005 in {2, 3, 4}:
        return "v14b_reproduction_passed"
    return "v14b_reproduction_failed_must_diagnose"


def primary_verdict(health_passed: bool, success_n_001: int | None) -> str | None:
    if not health_passed:
        return None

    if success_n_001 is None:
        return "missing_m001_scan_rerun_v14c"
    if success_n_001 >= 5:
        return "arm_mass_is_root_cause_v15_unblocked"
    elif success_n_001 == 4:
        return "partial_arm_mass_relief_consider_elastic_attachment"
    elif success_n_001 == 3:
        return "arm_mass_not_dominant_cause_route_X_failing"
    return "unexpected_regression_must_diagnose"


def overlap_report(
    cells: set[tuple[float, float]], reference: set[tuple[float, float]]
) -> dict:
    overlap = cells & reference
    lost = reference - cells
    new = cells - reference
    return {
        "overlap": cell_list(overlap),
        "overlap_n": len(overlap),
        "retained": cell_list(overlap),
        "retained_n": len(overlap),
        "lost": cell_list(lost),
        "lost_n": len(lost),
        "new": cell_list(new),
        "new_n": len(new),
        "is_subset_of_reference": cells <= reference,
        "contains_reference": cells >= reference,
    }


def monotonicity(by_mass: dict[float, dict]) -> dict:
    masses = [mass for mass in EXPECTED_MASSES if mass in by_mass]
    counts = [int(by_mass[mass]["success_n"]) for mass in masses]
    nonincreasing = all(a >= b for a, b in zip(counts, counts[1:]))
    nondecreasing = all(a <= b for a, b in zip(counts, counts[1:]))
    return {
        "masses": masses,
        "success_counts": counts,
        "nonincreasing_with_mass": nonincreasing,
        "nondecreasing_with_mass": nondecreasing,
        "strictly_decreases_anywhere": any(a > b for a, b in zip(counts, counts[1:])),
        "note": "Expected lightening trend is nonincreasing success as arm_mass increases.",
    }


def comparison_rows(by_mass: dict[float, dict]) -> list[dict]:
    rows = []
    for mass in EXPECTED_MASSES:
        stats = by_mass.get(mass)
        success_n = int(stats["success_n"]) if stats else 0
        total_n = int(stats["total_n"]) if stats else 0
        rows.append(
            {
                "arm_mass": mass,
                "v14c_success_n": success_n,
                "v14c_total_n": total_n,
                "v14c_rate_pct": (100.0 * success_n / total_n) if total_n else 0.0,
                "v14b_reference_success_n": len(V14B_CELLS),
                "delta_vs_v14b_success_n": success_n - len(V14B_CELLS),
                "v13_6_1_best_no_arms_success_n": len(V1361_BEST_NO_ARMS),
                "delta_vs_v13_6_1_best_success_n": success_n - len(V1361_BEST_NO_ARMS),
            }
        )
    return rows


def write_heatmaps(rows: list[dict[str, str]], by_mass: dict[float, dict]) -> None:
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.colors import ListedColormap

    xs = sorted({key_float(row["foot_radius_x"]) for row in rows})
    ys = sorted({key_float(row["leg_scale_y"]) for row in rows})
    x_index = {x: i for i, x in enumerate(xs)}
    y_index = {y: i for i, y in enumerate(ys)}
    x_edges = grid_edges(xs)
    y_edges = grid_edges(ys)

    fig, axes = plt.subplots(2, 2, figsize=(11, 8), constrained_layout=True)
    cmap = ListedColormap(["#eeeeee", "#2ca25f"])

    for ax, mass in zip(axes.ravel(), EXPECTED_MASSES):
        grid = np.full((len(ys), len(xs)), np.nan)
        for row in rows:
            if key_float(row["arm_mass"]) != mass:
                continue
            x, y = cell_key(row)
            grid[y_index[y], x_index[x]] = 1.0 if parse_bool(row["success"]) else 0.0

        masked = np.ma.masked_invalid(grid)
        ax.pcolormesh(
            x_edges, y_edges, masked, cmap=cmap, vmin=0, vmax=1, shading="flat"
        )
        ax.scatter(
            [x for x, _ in V1361_BEST_NO_ARMS],
            [y for _, y in V1361_BEST_NO_ARMS],
            marker="o",
            s=92,
            facecolors="none",
            edgecolors="#2166ac",
            linewidths=1.8,
            label="V13.6.1 best no-arms",
        )
        ax.scatter(
            [x for x, _ in V14B_CELLS],
            [y for _, y in V14B_CELLS],
            marker="x",
            s=86,
            c="#b2182b",
            linewidths=2.0,
            label="V14b",
        )
        success_n = int(by_mass.get(mass, {}).get("success_n", 0))
        total_n = int(by_mass.get(mass, {}).get("total_n", 0))
        ax.set_title(f"arm_mass={mass:.2f} success {success_n}/{total_n}")
        ax.set_xlabel("foot_radius_x")
        ax.set_ylabel("leg_scale_y")
        ax.set_xticks(xs)
        ax.set_yticks(ys)
        ax.grid(color="white", linewidth=0.8)

    handles, labels = axes.ravel()[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=2, frameon=False)
    fig.suptitle("V14c C foot/leg success heatmaps", fontsize=14)
    OUT_DIR.mkdir(exist_ok=True)
    fig.savefig(HEATMAP_PATH, dpi=180)
    plt.close(fig)


def grid_edges(values: list[float]) -> list[float]:
    if len(values) == 1:
        step = 0.002
        return [values[0] - step / 2.0, values[0] + step / 2.0]
    edges = [values[0] - (values[1] - values[0]) / 2.0]
    for left, right in zip(values, values[1:]):
        edges.append((left + right) / 2.0)
    edges.append(values[-1] + (values[-1] - values[-2]) / 2.0)
    return edges


def main() -> None:
    rows = load_rows(SCAN_CSV)
    by_mass = summarize_by_mass(rows)
    write_heatmaps(rows, by_mass)

    mass_001 = by_mass.get(0.01)
    mass_005 = by_mass.get(0.05)
    success_n_001 = int(mass_001["success_n"]) if mass_001 else None
    success_n_005 = int(mass_005["success_n"]) if mass_005 else None
    health = health_verdict(success_n_005)
    primary = primary_verdict(health == "v14b_reproduction_passed", success_n_001)
    m001_cells = set(mass_001["success_cells"]) if mass_001 else set()

    summary = {
        "scan_csv": str(SCAN_CSV),
        "heatmap_png": str(HEATMAP_PATH),
        "comparison_rows": comparison_rows(by_mass),
        "success_cells_by_mass": {
            f"{mass:.2f}": cell_list(stats["success_cells"])
            for mass, stats in by_mass.items()
        },
        "failure_distributions_by_mass": {
            f"{mass:.2f}": stats["failure_distribution"]
            for mass, stats in by_mass.items()
        },
        "m001_vs_v13_6_1_best_no_arms": overlap_report(m001_cells, V1361_BEST_NO_ARMS),
        "m001_vs_v14b": overlap_report(m001_cells, V14B_CELLS),
        "mass_success_monotonicity": monotonicity(by_mass),
        "health_check_verdict": health,
        "primary_verdict": primary,
        "verdict_metadata": {
            "health_check_arm_mass": 0.05,
            "health_check_success_n": success_n_005,
            "health_check_rule": "pass iff m=0.05 success_n in {2,3,4}",
            "primary_arm_mass": 0.01,
            "primary_success_n": success_n_001,
            "primary_rule": "only evaluated when health_check_verdict passes; m=0.01 success_n >=5, ==4, ==3, <3",
        },
        "references": {
            "v13_6_1_best_no_arms_cells": cell_list(V1361_BEST_NO_ARMS),
            "v14b_cells": cell_list(V14B_CELLS),
        },
        "notes": [
            "Cells are rounded to 3 decimals for stable set comparison.",
            "Primary verdict is intentionally null unless the m=0.05 health check passes.",
        ],
    }

    SUMMARY_PATH.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
