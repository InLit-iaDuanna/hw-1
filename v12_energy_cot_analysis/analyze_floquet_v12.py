"""V12 实验 Floquet 乘子估计：对 V09/V10/V11_flat 的 Poincaré 截面点序列做 return-map 线性回归。"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common import (  # noqa: E402
    PALETTE,
    collect_section,
    floquet_multipliers,
    set_style,
)

OUT_DIR = Path(__file__).resolve().parent / "out"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# 状态键：摆腿/支撑腿无缝切换不影响左/左截面，统一取左腿四维状态
STATE_KEYS = ("left_hip", "left_knee", "left_hip_vel", "left_knee_vel")
SKIP_HEAD = 2  # 跳过初始暂态点

CASES = [
    {
        "key": "V09",
        "label": "V09 仿生稳定",
        "csv": "v09_stable_biomimetic_gait/out/v9_stable_walk_data.csv",
        "color": PALETTE["ok"],
    },
    {
        "key": "V10",
        "label": "V10 滚动足",
        "csv": "v10_rolling_foot_biomimetic_gait/out/v10_rolling_foot_walk_data.csv",
        "color": PALETTE["left"],
    },
    {
        "key": "V11_flat",
        "label": "V11 平地",
        "csv": "v11_rugged_terrain_robustness/out/v11_sanity_flat_data.csv",
        "color": PALETTE["right"],
    },
]


def load_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main() -> None:
    set_style()
    results: dict[str, dict] = {}

    for case in CASES:
        c_path = ROOT / case["csv"]
        if not c_path.exists():
            print(f"[skip] missing {c_path}")
            continue
        rows = load_rows(c_path)
        # collect_section 只在 support_foot 字段切换时取点，左/右交替，故同一脚的截面是隔点
        all_pts = collect_section(rows, STATE_KEYS)
        # 取 support_to == 'left' 的子序列（左脚触地视作 Poincaré 截面）
        left_pts: list[list[float]] = []
        last = ""
        for r in rows[1:]:
            cur = r.get("support_foot", "")
            if cur != last and cur == "left":
                left_pts.append([float(r[k]) for k in STATE_KEYS])
            if cur in {"left", "right"}:
                last = cur
        pts = np.array(left_pts) if left_pts else np.empty((0, len(STATE_KEYS)))
        n_total = pts.shape[0]
        if n_total < 4:
            print(
                f"[warn] {case['key']} only {n_total} left-touchdown points; Floquet 不可靠"
            )
        f = floquet_multipliers(pts, skip_head=SKIP_HEAD)
        eig = f["eigvals"]
        moduli = np.abs(eig)
        results[case["key"]] = {
            "label": case["label"],
            "n_section_points_total": n_total,
            "n_pairs_used": f["n_pairs"],
            "fixed_point": f["fixed_point"].tolist(),
            "eigvals_real": eig.real.tolist(),
            "eigvals_imag": eig.imag.tolist(),
            "moduli": moduli.tolist(),
            "max_modulus": float(np.max(moduli)) if moduli.size else float("nan"),
            "stable": bool(moduli.size and np.all(moduli < 1.0)),
        }
        print(
            f"[{case['key']}] n_pts={n_total} pairs={f['n_pairs']} max|λ|={results[case['key']]['max_modulus']:.3f}"
        )
        print(f"   eigvals = {eig}")

    # 单位圆 + 特征值散点
    fig, ax = plt.subplots(figsize=(6.5, 6.5))
    theta = np.linspace(0, 2 * np.pi, 200)
    ax.plot(np.cos(theta), np.sin(theta), "k--", lw=0.8, alpha=0.6, label="单位圆")
    ax.axhline(0, color="k", lw=0.4, alpha=0.4)
    ax.axvline(0, color="k", lw=0.4, alpha=0.4)
    for case in CASES:
        k = case["key"]
        if k not in results:
            continue
        r = results[k]
        ax.scatter(
            r["eigvals_real"],
            r["eigvals_imag"],
            s=70,
            color=case["color"],
            alpha=0.85,
            edgecolors="k",
            linewidths=0.5,
            label=f"{r['label']}  max|λ|={r['max_modulus']:.2f}",
        )
    ax.set_xlabel("Re(λ)")
    ax.set_ylabel("Im(λ)")
    ax.set_title("V12 实验 Floquet 乘子（return-map 线性回归，Goswami 1996 方法）")
    ax.set_aspect("equal")
    lim = 1.4
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.legend(loc="upper left", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "v12_floquet_spectrum.png")
    plt.close(fig)
    print("[ok] wrote v12_floquet_spectrum.png")

    # Poincaré 收敛曲线：到不动点的范数随步数变化
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for case in CASES:
        k = case["key"]
        if k not in results:
            continue
        rows = load_rows(ROOT / case["csv"])
        left_pts: list[list[float]] = []
        last = ""
        for r in rows[1:]:
            cur = r.get("support_foot", "")
            if cur != last and cur == "left":
                left_pts.append([float(r[ky]) for ky in STATE_KEYS])
            if cur in {"left", "right"}:
                last = cur
        pts = np.array(left_pts) if left_pts else np.empty((0, len(STATE_KEYS)))
        if pts.shape[0] < 2:
            continue
        fp = np.array(results[k]["fixed_point"])
        norms = np.linalg.norm(pts - fp, axis=1)
        ax.plot(
            np.arange(len(norms)),
            norms,
            "-o",
            ms=4,
            color=case["color"],
            label=results[k]["label"],
        )
    ax.set_xlabel("Poincaré 步数（左脚触地）")
    ax.set_ylabel("‖x_k − x*‖")
    ax.set_yscale("log")
    ax.set_title("V12 Poincaré 截面到不动点距离（对数轴）")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT_DIR / "v12_poincare_convergence.png")
    plt.close(fig)
    print("[ok] wrote v12_poincare_convergence.png")

    # 写 JSON
    out_json = OUT_DIR / "v12_floquet_table.json"
    with out_json.open("w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"[ok] wrote {out_json}")


if __name__ == "__main__":
    main()
