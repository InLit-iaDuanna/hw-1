"""V13.6 步态分析：读取 baseline data + phases，输出 (phase 时序图 + 力矩/能量/接触) 综合报告 PNG。

主交付：
  out/v13_6_baseline_report.png
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
OUT_DIR = ROOT / "out"

PHASE_ORDER = ["stance_early", "stance_late", "swing_thrust", "swing_retract"]
PHASE_COLOR = {
    "stance_early": "#4d8b7e",
    "stance_late": "#2e5e8a",
    "swing_thrust": "#d96b3c",
    "swing_retract": "#b9a14e",
}


def main() -> None:
    summary = json.loads(
        (OUT_DIR / "v13_6_baseline_summary.json").read_text(encoding="utf-8")
    )
    data_path = OUT_DIR / "v13_6_baseline_data.csv"
    with data_path.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    t = np.array([float(r["time"]) for r in rows])
    left_phase = [r["left_phase"] for r in rows]
    right_phase = [r["right_phase"] for r in rows]
    lhip_tau = np.array([float(r["left_hip_tau"]) for r in rows])
    rhip_tau = np.array([float(r["right_hip_tau"]) for r in rows])
    lcontact = np.array([int(float(r["left_contact"])) for r in rows])
    rcontact = np.array([int(float(r["right_contact"])) for r in rows])
    E_current = np.array([float(r["E_current"]) for r in rows])
    A_swing = np.array([float(r["A_swing"]) for r in rows])
    e_E_swing = np.array([float(r["e_E_swing"]) for r in rows])
    hip_x = np.array([float(r["hip_x"]) for r in rows])
    hip_clr = np.array([float(r["hip_clearance"]) for r in rows])

    fig, axes = plt.subplots(5, 1, figsize=(12, 11), sharex=True)

    # 1. phase timeline (left & right bands)
    ax = axes[0]
    for i, ph in enumerate(left_phase):
        ax.barh(
            0.7,
            t[i] - (t[i - 1] if i > 0 else 0),
            left=(t[i - 1] if i > 0 else 0),
            height=0.45,
            color=PHASE_COLOR.get(ph, "#888"),
            edgecolor="none",
        )
    for i, ph in enumerate(right_phase):
        ax.barh(
            0.2,
            t[i] - (t[i - 1] if i > 0 else 0),
            left=(t[i - 1] if i > 0 else 0),
            height=0.45,
            color=PHASE_COLOR.get(ph, "#888"),
            edgecolor="none",
        )
    ax.set_yticks([0.2, 0.7])
    ax.set_yticklabels(["right", "left"])
    ax.set_title("FSM phase timeline (per leg)")
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in PHASE_COLOR.values()]
    ax.legend(handles, list(PHASE_COLOR.keys()), loc="upper right", fontsize=8, ncol=4)
    ax.set_ylim(0, 1)

    # 2. hip torque
    ax = axes[1]
    ax.plot(t, lhip_tau, color="#05749e", label="left hip τ", lw=0.8)
    ax.plot(t, rhip_tau, color="#dc4a36", label="right hip τ", lw=0.8)
    ax.axhline(0, color="k", lw=0.4)
    ax.set_ylabel("hip τ (Nm)")
    ax.legend(loc="upper right", fontsize=8)
    ax.set_title("Hip torque (FSM output)")

    # 3. mechanical energy + e_E
    ax = axes[2]
    ax.plot(t, E_current, color="#2c3e50", label="E (J)", lw=0.9)
    ax.axhline(52.66, color="#7f8c8d", ls="--", lw=0.7, label="E* = 52.66 J (V13b)")
    ax.set_ylabel("E (J)")
    ax.legend(loc="upper right", fontsize=8)
    ax.set_title("Mechanical energy vs limit-cycle target")

    # 4. swing thrust amplitude
    ax = axes[3]
    ax.plot(t, A_swing, color="#d96b3c", label="A_energy (swing_thrust)", lw=0.8)
    ax.fill_between(t, 0, A_swing, alpha=0.3, color="#d96b3c")
    ax.set_ylabel("A (Nm)")
    ax.legend(loc="upper right", fontsize=8)
    ax.set_title("Swing-thrust energy-shaping amplitude")

    # 5. contact pattern + hip x
    ax = axes[4]
    ax.fill_between(
        t, 0, lcontact * 0.4, color="#05749e", alpha=0.5, label="left contact"
    )
    ax.fill_between(
        t, 0.5, 0.5 + rcontact * 0.4, color="#dc4a36", alpha=0.5, label="right contact"
    )
    ax2 = ax.twinx()
    ax2.plot(t, hip_x, color="#27ae60", lw=0.9, label="hip x (m)")
    ax2.set_ylabel("hip x (m)")
    ax.set_xlabel("time (s)")
    ax.set_ylabel("contact")
    ax.legend(loc="upper left", fontsize=8)
    ax2.legend(loc="lower right", fontsize=8)
    ax.set_title("Foot contact + forward progress")

    title = (
        f"V13.6 baseline | success={summary['success']} | "
        f"alt={summary['alternating_touchdowns']} | "
        f"dist={summary['forward_distance']:.2f} m | "
        f"E_in={summary['active_input_energy_j']:.2f} J | "
        f"failure={summary['failure']}"
    )
    fig.suptitle(title, fontsize=11)
    fig.tight_layout()
    out = OUT_DIR / "v13_6_baseline_report.png"
    fig.savefig(out, dpi=120)
    plt.close(fig)
    print(out)

    # 文本汇总
    print(
        json.dumps(
            {
                "success": summary["success"],
                "alternating_touchdowns": summary["alternating_touchdowns"],
                "forward_distance": summary["forward_distance"],
                "simulated_time": summary["simulated_time"],
                "phase_transitions": summary["phase_transitions"],
                "phase_durations_s": summary["phase_durations_s"],
                "phase_torque_integral_Nms": summary["phase_torque_integral_Nms"],
                "failure": summary["failure"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
