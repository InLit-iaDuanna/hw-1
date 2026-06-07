"""V12 横向能量 / CoT 分析（V07-V11）。

读取已有 simulate 输出，不重跑。仅做后处理。
"""

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
    collision_loss_per_step,
    cost_of_transport,
    mechanical_energy_series,
    set_style,
)

OUT_DIR = Path(__file__).resolve().parent / "out"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def total_mass(params: dict) -> float:
    return float(params.get("hip_mass", 0.0)) + float(params.get("torso_mass", 0.0))


# 版本元数据：每条 = (label, csv 相对路径, summary JSON 相对路径, 是否准被动有 input_energy, 报告组)
VERSIONS = [
    {
        "key": "V07",
        "label": "V07 纯被动失败",
        "csv": "v07_true_contact_exploration/out/v7_single_data.csv",
        "summary": "v07_true_contact_exploration/out/v7_single_summary.json",
        "has_input_energy": False,
        "color": PALETTE["fail"],
    },
    {
        "key": "V08",
        "label": "V08 准被动髋助力",
        "csv": "v08_quasi_passive_assisted/out/v8_assisted_walk_data.csv",
        "summary": "v08_quasi_passive_assisted/out/v8_assisted_walk_summary.json",
        "has_input_energy": True,
        "color": PALETTE["warn"],
    },
    {
        "key": "V09",
        "label": "V09 仿生稳定",
        "csv": "v09_stable_biomimetic_gait/out/v9_stable_walk_data.csv",
        "summary": "v09_stable_biomimetic_gait/out/v9_stable_walk_summary.json",
        "has_input_energy": True,
        "color": PALETTE["ok"],
    },
    {
        "key": "V10",
        "label": "V10 滚动足",
        "csv": "v10_rolling_foot_biomimetic_gait/out/v10_rolling_foot_walk_data.csv",
        "summary": "v10_rolling_foot_biomimetic_gait/out/v10_rolling_foot_walk_summary.json",
        "has_input_energy": True,
        "color": PALETTE["left"],
    },
    {
        "key": "V11_flat",
        "label": "V11 平地",
        "csv": "v11_rugged_terrain_robustness/out/v11_sanity_flat_data.csv",
        "summary": "v11_rugged_terrain_robustness/out/v11_sanity_flat_summary.json",
        "has_input_energy": True,
        "color": PALETTE["right"],
    },
    {
        "key": "V11_terrain",
        "label": "V11 小幅地形",
        "csv": "v11_rugged_terrain_robustness/out/v11_smoke_terrain_data.csv",
        "summary": "v11_rugged_terrain_robustness/out/v11_smoke_terrain_summary.json",
        "has_input_energy": True,
        "color": PALETTE["neutral"],
    },
    {
        "key": "V11_hard",
        "label": "V11 大扰动失败",
        "csv": "v11_rugged_terrain_robustness/out/v11_smoke_hard_data.csv",
        "summary": "v11_rugged_terrain_robustness/out/v11_smoke_hard_summary.json",
        "has_input_energy": True,
        "color": PALETTE["fail"],
    },
]

ENERGY_GROUP = ("V09", "V10", "V11_flat")  # 详细机械能时序图
COLLISION_GROUP = ("V08", "V09", "V10", "V11_flat", "V11_terrain", "V11_hard")


def load_csv_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def load_summary(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    set_style()

    rows_by_key: dict[str, list[dict]] = {}
    summary_by_key: dict[str, dict] = {}
    mass_by_key: dict[str, float] = {}

    for v in VERSIONS:
        s_path = ROOT / v["summary"]
        c_path = ROOT / v["csv"]
        if not s_path.exists():
            print(f"[skip] missing summary: {s_path}")
            continue
        summary = load_summary(s_path)
        rows = load_csv_rows(c_path)
        rows_by_key[v["key"]] = rows
        summary_by_key[v["key"]] = summary
        mass_by_key[v["key"]] = total_mass(summary.get("params", {}))

    # 1) CoT / 能量横向表
    table_path = OUT_DIR / "v12_energy_cot_table.csv"
    table_rows = []
    for v in VERSIONS:
        k = v["key"]
        if k not in summary_by_key:
            continue
        s = summary_by_key[k]
        m = mass_by_key[k]
        dist = float(s.get("forward_distance", 0.0))
        if v["has_input_energy"] and s.get("failure") != "fall_down":
            E = float(s.get("active_input_energy_j", float("nan")))
            net = float(s.get("net_actuator_work_j", float("nan")))
            cot = cost_of_transport(E, m, dist) if not np.isnan(E) else float("nan")
        else:
            E = float("nan")
            net = float("nan")
            cot = float("nan")
        table_rows.append(
            {
                "version": k,
                "label": v["label"],
                "mass_kg": round(m, 4),
                "distance_m": round(dist, 4),
                "active_input_energy_j": E if not np.isnan(E) else "",
                "net_actuator_work_j": net if not np.isnan(net) else "",
                "CoT": cot if not np.isnan(cot) else "",
                "failure": s.get("failure", ""),
                "alternating_touchdowns": s.get("alternating_touchdowns", 0),
                "quasi_passive": s.get("quasi_passive", False),
                "pure_passive": s.get("pure_passive", False),
            }
        )
    with table_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(table_rows[0].keys()))
        writer.writeheader()
        writer.writerows(table_rows)
    print(f"[ok] wrote {table_path}")

    # 2) 机械能时序：V09 / V10 / V11_flat
    fig, axes = plt.subplots(len(ENERGY_GROUP), 1, figsize=(9, 7), sharex=False)
    if len(ENERGY_GROUP) == 1:
        axes = [axes]
    for ax, k in zip(axes, ENERGY_GROUP):
        rows = rows_by_key.get(k, [])
        m = mass_by_key.get(k, 0.0)
        if not rows or m <= 0:
            ax.text(
                0.5,
                0.5,
                f"{k}: 数据缺失",
                ha="center",
                va="center",
                transform=ax.transAxes,
            )
            continue
        s = mechanical_energy_series(rows, mass_kg=m)
        ax.plot(s["time"], s["ke"], label="KE", color=PALETTE["left"], lw=1.0)
        ax.plot(s["time"], s["pe"], label="PE", color=PALETTE["warn"], lw=1.0)
        ax.plot(s["time"], s["total"], label="KE+PE", color=PALETTE["neutral"], lw=1.2)
        v_meta = next(v for v in VERSIONS if v["key"] == k)
        ax.set_title(f"{v_meta['label']}（hip 平动能量近似，m={m:.2f} kg）")
        ax.set_ylabel("能量 [J]")
        ax.legend(loc="upper right", fontsize=8)
    axes[-1].set_xlabel("时间 [s]")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "v12_mechanical_energy.png")
    plt.close(fig)
    print("[ok] wrote v12_mechanical_energy.png")

    # 3) 碰撞损耗柱状图
    fig, ax = plt.subplots(figsize=(9, 4.5))
    bar_x: list[str] = []
    bar_means: list[float] = []
    bar_stds: list[float] = []
    bar_colors: list[str] = []
    for k in COLLISION_GROUP:
        rows = rows_by_key.get(k, [])
        m = mass_by_key.get(k, 0.0)
        v_meta = next(v for v in VERSIONS if v["key"] == k)
        if not rows or m <= 0:
            continue
        events = collision_loss_per_step(rows, mass_kg=m)
        if not events:
            mean = 0.0
            std = 0.0
        else:
            dEs = np.array([e["dE_J"] for e in events])
            mean = float(dEs.mean())
            std = float(dEs.std())
        bar_x.append(v_meta["label"])
        bar_means.append(mean)
        bar_stds.append(std)
        bar_colors.append(v_meta["color"])
    xs = np.arange(len(bar_x))
    ax.bar(xs, bar_means, yerr=bar_stds, color=bar_colors, alpha=0.85, capsize=4)
    ax.set_xticks(xs)
    ax.set_xticklabels(bar_x, rotation=18, ha="right")
    ax.set_ylabel("每步总能量跳变 ΔE [J]（正=损失）")
    ax.set_title("V07-V11 每步碰撞 / 步态过渡能量跳变（hip 平动近似）")
    ax.axhline(0, color="k", lw=0.6)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "v12_collision_loss_per_step.png")
    plt.close(fig)
    print("[ok] wrote v12_collision_loss_per_step.png")

    # 4) CoT 横向对比柱状图
    fig, ax = plt.subplots(figsize=(9, 4.5))
    cot_rows = [r for r in table_rows if r["CoT"] != "" and r["failure"] != "fall_down"]
    xs = np.arange(len(cot_rows))
    cots = [r["CoT"] for r in cot_rows]
    labels = [r["label"] for r in cot_rows]
    colors = [
        next(v for v in VERSIONS if v["key"] == r["version"])["color"] for r in cot_rows
    ]
    bars = ax.bar(xs, cots, color=colors, alpha=0.85)
    for bar, c in zip(bars, cots):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            c,
            f"{c:.3f}",
            ha="center",
            va="bottom",
            fontsize=9,
        )
    ax.set_xticks(xs)
    ax.set_xticklabels(labels, rotation=18, ha="right")
    ax.set_ylabel("CoT = E / (m g d)")
    ax.set_title("V08-V11 准被动 Cost of Transport 对比（V07 / V11_hard 不计：失败）")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "v12_cot_comparison.png")
    plt.close(fig)
    print("[ok] wrote v12_cot_comparison.png")

    # 控制台摘要
    print("\n=== V12 CoT / 能量摘要 ===")
    for r in table_rows:
        cot_s = f"{r['CoT']:.4f}" if isinstance(r["CoT"], float) else "N/A"
        E_s = (
            f"{r['active_input_energy_j']:.2f}J"
            if isinstance(r["active_input_energy_j"], float)
            else "—"
        )
        print(
            f"  {r['version']:<11} m={r['mass_kg']:>4.2f}kg  d={r['distance_m']:>5.2f}m  E={E_s:>8}  CoT={cot_s}  failure={r['failure']}"
        )


if __name__ == "__main__":
    main()
