"""V13b: 长程 Floquet 重算 + 极限环辨识。

V12 留下的 follow-up：V10/V11 仅 7 次左脚触地，4D Floquet 退化为精确插值。
V13b 把 V10 baseline duration 从 12 s 拉到 20 s，应得 ≥ 16 次触地，谱可信。

输出还要给 V13.5 方案 C 用：极限环能量目标 E*（取末段触地点平均机械能）。

学术口径：仍是准被动（hip+knee 主动），不与文献纯被动 McGeer Floquet 直接对照。
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent
HW1 = ROOT.parent
V10_DIR = HW1 / "v10_rolling_foot_biomimetic_gait"
sys.path.insert(0, str(V10_DIR))
sys.path.insert(0, str(HW1))

from simulate_rolling_foot_gait_v10 import (
    RollingFootParams,
    run_simulation,
)  # noqa: E402

from common.energy_metrics import mechanical_energy_series  # noqa: E402
from common.poincare import (
    collect_section,
    floquet_multipliers,
    plot_section,
)  # noqa: E402

OUT_DIR = ROOT / "out"

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
    duration=20.0,
)
STATE_KEYS = ("right_hip", "right_hip_vel", "right_knee", "right_knee_vel")


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    print(f"[V13b] running V10 baseline at duration={BASELINE.duration}s ...")
    rows, summary = run_simulation(BASELINE, save_prefix=None, sample_hz=160.0)

    # 把 simulate 写到 V10 目录的 csv 移到 V13b（save_prefix=None 时不写，所以这里直接落盘）
    import csv

    csv_path = OUT_DIR / "v13b_baseline_20s_data.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    section_pts = collect_section(rows, STATE_KEYS)
    print(f"[V13b] collected {len(section_pts)} Poincare section points (target ≥ 16)")
    floq = floquet_multipliers(section_pts, skip_head=2)
    eig = floq["eigvals"]
    max_abs = float(np.max(np.abs(eig))) if eig.size else float("nan")

    mass = BASELINE.hip_mass + 2 * BASELINE.torso_mass
    energy = mechanical_energy_series(rows, mass_kg=mass)
    e_total = energy["total"]
    # 极限环能量目标：取后半段（稳定后）的均值
    if len(e_total) > 0:
        n = len(e_total)
        E_star = float(np.mean(e_total[n // 2 :]))
        E_std = float(np.std(e_total[n // 2 :]))
    else:
        E_star = float("nan")
        E_std = float("nan")

    result = {
        "duration": BASELINE.duration,
        "success": bool(summary["success"]),
        "alternations": int(summary["alternating_touchdowns"]),
        "forward_distance": float(summary["forward_distance"]),
        "n_section_points": int(len(section_pts)),
        "fixed_point": floq["fixed_point"].tolist(),
        "eigvals_real": [float(np.real(v)) for v in eig],
        "eigvals_imag": [float(np.imag(v)) for v in eig],
        "eigvals_abs": [float(np.abs(v)) for v in eig],
        "max_abs_floquet": max_abs,
        "n_pairs_used": int(floq["n_pairs"]),
        "E_star_J": E_star,
        "E_std_J": E_std,
        "mass_kg": mass,
        "params": asdict(BASELINE),
        "state_keys": list(STATE_KEYS),
    }
    (OUT_DIR / "v13b_floquet_summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    plot_section(
        axes[0],
        section_pts[:, [0, 1]],
        STATE_KEYS[0],
        STATE_KEYS[1],
        title=f"Poincare (right_hip plane, n={len(section_pts)})",
    )
    plot_section(
        axes[1],
        section_pts[:, [2, 3]],
        STATE_KEYS[2],
        STATE_KEYS[3],
        title="Poincare (right_knee plane)",
    )
    if eig.size:
        theta = np.linspace(0, 2 * np.pi, 200)
        axes[2].plot(np.cos(theta), np.sin(theta), "k--", lw=0.7)
        axes[2].scatter(np.real(eig), np.imag(eig), s=80, c="C3", marker="x")
        axes[2].set_xlim(-1.5, 1.5)
        axes[2].set_ylim(-1.5, 1.5)
        axes[2].set_aspect("equal")
        axes[2].grid(alpha=0.3)
        axes[2].set_title(f"Floquet eigvals (max|λ|={max_abs:.3f})")
        axes[2].set_xlabel("Re")
        axes[2].set_ylabel("Im")
    fig.suptitle(
        f"V13b: V10 baseline @ duration=20s, E*={E_star:.2f} +/- {E_std:.2f} J"
    )
    fig.tight_layout()
    out_png = OUT_DIR / "v13b_floquet_report.png"
    fig.savefig(out_png, dpi=140)
    print(f"[V13b] -> {out_png}")
    print(f"[V13b] -> {OUT_DIR / 'v13b_floquet_summary.json'}")
    print(
        f"[V13b] alternations={result['alternations']}  max|lambda|={max_abs:.3f}  "
        f"E*={E_star:.2f} +/- {E_std:.2f} J  (n_pairs={result['n_pairs_used']})"
    )


if __name__ == "__main__":
    main()
