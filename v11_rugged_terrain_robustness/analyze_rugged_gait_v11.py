from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
OUT_DIR = ROOT / "out"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.energy_metrics import cost_of_transport  # noqa: E402
from common.plot_styles import PALETTE, set_style  # noqa: E402

SCENARIOS = [
    ("v11_sanity_flat", "Flat baseline"),
    ("v11_smoke_terrain", "1.5 cm terrain"),
    ("v11_smoke_hard", "4 cm + 60 N impulse"),
]


def load_rows(path: Path) -> dict[str, np.ndarray]:
    with path.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    data: dict[str, np.ndarray] = {}
    if not rows:
        return data
    for key in rows[0].keys():
        try:
            data[key] = np.array([float(row[key]) for row in rows], dtype=float)
        except ValueError:
            continue
    return data


def load_case(prefix: str, label: str) -> dict:
    summary_path = OUT_DIR / f"{prefix}_summary.json"
    data_path = OUT_DIR / f"{prefix}_data.csv"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    data = load_rows(data_path) if data_path.exists() else {}
    return {"prefix": prefix, "label": label, "summary": summary, "data": data}


def total_mass(summary: dict) -> float:
    params = summary["params"]
    return (
        params["hip_mass"]
        + params["torso_mass"]
        + 2.0 * (0.18 + 0.16 + 0.06 + 0.025 + 0.025 + 0.03)
    )


def write_report(cases: list[dict]) -> Path:
    lines = [
        "# V11 rugged terrain robustness report",
        "",
        "V11 extends V10 with sagittal hfield terrain, single impulse disturbance, and contact-phase noise hooks.",
        "It remains quasi-passive because hip and knee actuators are active; failed runs are robustness boundary evidence.",
        "",
        "| Case | Terrain | Impulse | Success | Touchdowns | Distance (m) | Time (s) | Input energy (J) | CoT | Failure |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for case in cases:
        s = case["summary"]
        scenario = s["scenario"]
        cot = cost_of_transport(
            s["active_input_energy_j"],
            total_mass(s),
            max(s["forward_distance"], 1e-9),
        )
        lines.append(
            "| {label} | {terrain:.3f} | {impulse:.1f} | {success} | {touchdowns} | "
            "{distance:.2f} | {time:.2f} | {energy:.2f} | {cot:.3f} | {failure} |".format(
                label=case["label"],
                terrain=scenario["terrain_amplitude_m"],
                impulse=scenario["impulse_force_n"],
                success="yes" if s["success"] else "no",
                touchdowns=s["alternating_touchdowns"],
                distance=s["forward_distance"],
                time=s["simulated_time"],
                energy=s["active_input_energy_j"],
                cot=cot,
                failure=s["failure"],
            )
        )
    lines.extend(
        [
            "",
            "Recommended interpretation: flat and mild terrain cases show the inherited V10 controller still walks under small terrain disturbance; the hard case fails after the impulse, so it should be reported as the first robustness boundary rather than a success.",
        ]
    )
    out = OUT_DIR / "v11_report_text.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def plot_report(cases: list[dict]) -> Path:
    set_style()
    fig, axes = plt.subplots(2, 2, figsize=(14, 9), constrained_layout=True)
    fig.suptitle("V11 Rugged Terrain Robustness", fontsize=17)

    labels = [case["label"] for case in cases]
    colors = [
        PALETTE["ok"] if case["summary"]["success"] else PALETTE["fail"]
        for case in cases
    ]
    x = np.arange(len(cases))

    ax = axes[0, 0]
    distances = [case["summary"]["forward_distance"] for case in cases]
    touchdowns = [case["summary"]["alternating_touchdowns"] for case in cases]
    ax.bar(
        x - 0.18, distances, width=0.36, color=colors, alpha=0.85, label="distance / m"
    )
    ax.bar(
        x + 0.18,
        touchdowns,
        width=0.36,
        color="#6b7280",
        alpha=0.75,
        label="touchdowns",
    )
    ax.set_xticks(x, labels, rotation=12, ha="right")
    ax.set_title("Robustness outcomes")
    ax.legend()

    ax = axes[0, 1]
    for case, color in zip(cases, colors):
        data = case["data"]
        if "time" in data and "hip_x" in data:
            ax.plot(
                data["time"], data["hip_x"], lw=1.4, label=case["label"], color=color
            )
    ax.set_title("Hip forward trajectory")
    ax.set_xlabel("time / s")
    ax.set_ylabel("hip x / m")
    ax.legend()

    ax = axes[1, 0]
    for case in cases[:2]:
        data = case["data"]
        if "time" not in data:
            continue
        offset = 1.0 if case["prefix"].endswith("flat") else -1.0
        ax.step(
            data["time"],
            data.get("left_contact", np.array([])) * offset,
            where="post",
            lw=1.0,
            label=f"{case['label']} left",
        )
        ax.step(
            data["time"],
            -data.get("right_contact", np.array([])) * offset,
            where="post",
            lw=1.0,
            label=f"{case['label']} right",
        )
    ax.set_title("Contact rhythm: flat vs mild terrain")
    ax.set_xlabel("time / s")
    ax.set_yticks([-1, 0, 1], ["terrain R/L", "none", "flat L/R"])
    ax.legend(fontsize=8, ncol=2)

    ax = axes[1, 1]
    for case in cases:
        data = case["data"]
        if "time" in data and "input_energy" in data:
            ax.plot(data["time"], data["input_energy"], lw=1.4, label=case["label"])
    ax.set_title("Cumulative positive actuator input")
    ax.set_xlabel("time / s")
    ax.set_ylabel("energy / J")
    ax.legend()

    out = OUT_DIR / "v11_robustness_report.png"
    fig.savefig(out, dpi=180)
    plt.close(fig)
    return out


def main() -> None:
    missing = [
        prefix
        for prefix, _ in SCENARIOS
        if not (OUT_DIR / f"{prefix}_summary.json").exists()
    ]
    if missing:
        raise FileNotFoundError(f"missing V11 summary files: {', '.join(missing)}")
    cases = [load_case(prefix, label) for prefix, label in SCENARIOS]
    report_path = write_report(cases)
    figure_path = plot_report(cases)
    print(report_path)
    print(figure_path)


if __name__ == "__main__":
    main()
