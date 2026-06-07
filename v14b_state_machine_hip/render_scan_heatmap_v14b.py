"""Render V14 vs V14b scan heatmaps."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent
HW1_ROOT = ROOT.parent
sys.path.insert(0, str(HW1_ROOT))
from common import set_style  # noqa: E402

OUT_DIR = ROOT / "out"
V14_OUT_DIR = HW1_ROOT / "v14_passive_arms" / "out"


def _bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    return value.lower() == "true"


def load_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def grid(
    rows: list[dict], masses: list[float], lengths: list[float], key: str
) -> np.ndarray:
    out = np.zeros((len(masses), len(lengths)))
    for row in rows:
        i = masses.index(float(row["arm_mass"]))
        j = lengths.index(float(row["arm_length"]))
        if key == "success":
            out[i, j] = 1.0 if _bool(row[key]) else 0.0
        else:
            out[i, j] = float(row[key])
    return out


def main() -> None:
    v14_rows = load_rows(V14_OUT_DIR / "v14_arm_scan.csv")
    v14b_rows = load_rows(OUT_DIR / "v14b_arm_scan.csv")
    summary = json.loads(
        (OUT_DIR / "v14b_arm_scan_summary.json").read_text(encoding="utf-8")
    )
    masses = sorted({float(row["arm_mass"]) for row in v14_rows + v14b_rows})
    lengths = sorted({float(row["arm_length"]) for row in v14_rows + v14b_rows})

    v14_success = grid(v14_rows, masses, lengths, "success")
    v14b_success = grid(v14b_rows, masses, lengths, "success")
    v14_forward = grid(v14_rows, masses, lengths, "forward_distance")
    v14b_forward = grid(v14b_rows, masses, lengths, "forward_distance")
    delta = v14b_forward - v14_forward

    set_style()
    plt.rcParams["font.sans-serif"] = [
        "Microsoft YaHei",
        "SimHei",
        "Arial Unicode MS",
        "DejaVu Sans",
    ]
    plt.rcParams["axes.unicode_minus"] = False

    fig, axes = plt.subplots(1, 3, figsize=(17, 5.6), constrained_layout=True)
    fig.suptitle(
        "V14b scan: passive arms + V13.6 FSM hip "
        f"({summary['n_success']}/{summary['n_total']} success)",
        fontsize=14,
    )

    extent = [
        lengths[0] - 0.05,
        lengths[-1] + 0.05,
        masses[0] - 0.02,
        masses[-1] + 0.02,
    ]
    for ax, data, title in [
        (axes[0], v14_success, "V14 success (V10 controller)"),
        (axes[1], v14b_success, "V14b success (V13.6 FSM)"),
    ]:
        im = ax.imshow(
            data,
            origin="lower",
            aspect="auto",
            cmap="RdYlGn",
            extent=extent,
            vmin=0,
            vmax=1,
        )
        ax.set_xticks(lengths)
        ax.set_yticks(masses)
        ax.set_xlabel("arm_length / m")
        ax.set_ylabel("arm_mass / kg")
        ax.set_title(title)
        for i, mass in enumerate(masses):
            for j, length in enumerate(lengths):
                ax.text(
                    length,
                    mass,
                    "OK" if data[i, j] > 0.5 else "fail",
                    ha="center",
                    va="center",
                    fontsize=7,
                )
        fig.colorbar(im, ax=ax)

    vmax = max(0.1, float(np.nanmax(np.abs(delta))))
    im = axes[2].imshow(
        delta,
        origin="lower",
        aspect="auto",
        cmap="coolwarm",
        extent=extent,
        vmin=-vmax,
        vmax=vmax,
    )
    axes[2].set_xticks(lengths)
    axes[2].set_yticks(masses)
    axes[2].set_xlabel("arm_length / m")
    axes[2].set_ylabel("arm_mass / kg")
    axes[2].set_title("Forward distance delta / m (V14b - V14)")
    for i, mass in enumerate(masses):
        for j, length in enumerate(lengths):
            axes[2].text(
                length,
                mass,
                f"{delta[i, j]:+.1f}",
                ha="center",
                va="center",
                fontsize=7,
            )
    fig.colorbar(im, ax=axes[2])

    out = OUT_DIR / "v14b_arm_scan_heatmap.png"
    fig.savefig(out, dpi=170)
    plt.close(fig)
    print(out)


if __name__ == "__main__":
    main()
