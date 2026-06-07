"""V13.5 方案 C 切片扫描器。

主交付：在 V13 切片 C `foot_radius × leg_scale` 同栅格（6x6=36 点）跑 plan C，
直接对比成功率（V13 plan C 输出 success rate vs V13 V10 的 16.7%）。

副产品：k_E × E_star 6x6 调参图（看 plan C 自身参数对成功率的敏感性）。

输出：
  out/v13_5_planC_C_foot_leg.csv + meta.json
  out/v13_5_planC_kE_Estar.csv  + meta.json
  out/v13_5_planC_vs_v10.json   横向对比表
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from dataclasses import asdict, replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HW1_ROOT = ROOT.parent
V10_DIR = HW1_ROOT / "v10_rolling_foot_biomimetic_gait"
sys.path.insert(0, str(V10_DIR))
sys.path.insert(0, str(HW1_ROOT))
sys.path.insert(0, str(ROOT))

from simulate_v13_5_planC import (
    V135ParamsC,
    _baseline_v10,
    run_simulation,
)  # noqa: E402

from common.energy_metrics import cost_of_transport  # noqa: E402

OUT_DIR = ROOT / "out"


def linspace(a: float, b: float, n: int) -> list[float]:
    if n <= 1:
        return [a]
    return [a + (b - a) * i / (n - 1) for i in range(n)]


def make_v135c_params(
    *,
    foot_radius: float | None = None,
    leg_scale: float | None = None,
    E_star: float = 52.66,
    k_E: float = 7.5,
    duration: float = 12.0,
) -> V135ParamsC:
    base = _baseline_v10()
    kwargs: dict[str, float] = {"duration": duration}
    if foot_radius is not None:
        kwargs["foot_radius"] = float(foot_radius)
    if leg_scale is not None:
        kwargs["thigh_length"] = float(base.thigh_length * leg_scale)
        kwargs["shank_length"] = float(base.shank_length * leg_scale)
        kwargs["step_length"] = float(base.step_length * leg_scale)
    base_eff = replace(base, **kwargs)
    return V135ParamsC(base=base_eff, E_star=E_star, k_E=k_E)


def evaluate(params: V135ParamsC, sample_hz: float = 40.0) -> dict:
    rows, summary = run_simulation(params, sample_hz=sample_hz)
    p = params.base
    mass = p.hip_mass + 2 * p.torso_mass
    cot = (
        cost_of_transport(
            summary["active_input_energy_j"], mass, summary["forward_distance"]
        )
        if summary["success"]
        else float("nan")
    )
    return {
        **asdict(p),
        "E_star": params.E_star,
        "k_E": params.k_E,
        "success": bool(summary["success"]),
        "alternating_touchdowns": int(summary["alternating_touchdowns"]),
        "forward_distance": float(summary["forward_distance"]),
        "simulated_time": float(summary["simulated_time"]),
        "active_input_energy_j": float(summary["active_input_energy_j"]),
        "failure": str(summary["failure"]),
        "cot": float(cot),
        "score": float(summary["score"]),
        "mean_energy_error_J": float(summary["v135c_extra"]["mean_energy_error_J"]),
        "hip_active_duty": float(summary["v135c_extra"]["hip_active_duty"]),
    }


def run_slice_C_foot_leg(
    grid: int, duration: float, E_star: float, k_E: float
) -> tuple[Path, list[dict]]:
    """主交付：与 V13 切片 C 同栅格 foot_radius x leg_scale 6x6。"""
    name = "C_foot_leg"
    xs = linspace(0.030, 0.050, grid)  # foot_radius
    ys = linspace(0.90, 1.10, grid)  # leg_scale
    rows: list[dict] = []
    t0 = time.time()
    total = grid * grid
    print(
        f"[planC.{name}] grid={grid}x{grid} = {total} pts, duration={duration}s/pt, "
        f"E_star={E_star}, k_E={k_E}"
    )

    for ix, xv in enumerate(xs):
        for iy, yv in enumerate(ys):
            params = make_v135c_params(
                foot_radius=xv, leg_scale=yv, E_star=E_star, k_E=k_E, duration=duration
            )
            try:
                r = evaluate(params)
            except Exception as exc:  # noqa: BLE001
                r = {
                    "success": False,
                    "failure": f"exception:{exc.__class__.__name__}",
                    "cot": float("nan"),
                    "alternating_touchdowns": 0,
                    "forward_distance": 0.0,
                    "simulated_time": 0.0,
                    "active_input_energy_j": 0.0,
                    "score": -1e6,
                    "mean_energy_error_J": float("nan"),
                    "hip_active_duty": 0.0,
                    "E_star": E_star,
                    "k_E": k_E,
                }
            r["slice"] = "planC_" + name
            r["ix"] = ix
            r["iy"] = iy
            r["foot_radius_x"] = xv
            r["leg_scale_y"] = yv
            rows.append(r)
            elapsed = time.time() - t0
            done = ix * grid + iy + 1
            eta = elapsed / done * (total - done)
            print(
                f"  [{done}/{total}] foot_radius={xv:.3f} leg_scale={yv:.3f} "
                f"success={r['success']} td={r['alternating_touchdowns']} "
                f"e_E={r['mean_energy_error_J']:.3f} duty={r['hip_active_duty']:.2f} "
                f"({elapsed:.0f}s elapsed, ETA {eta:.0f}s)"
            )

    OUT_DIR.mkdir(exist_ok=True)
    csv_path = OUT_DIR / f"v13_5_planC_{name}.csv"
    fieldnames = sorted({k for r in rows for k in r.keys()})
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    meta = {
        "slice": "planC_" + name,
        "grid": grid,
        "duration": duration,
        "x": ("foot_radius", 0.030, 0.050),
        "y": ("leg_scale", 0.90, 1.10),
        "E_star": E_star,
        "k_E": k_E,
        "title": "[plan C] foot_radius vs leg_scale (energy-shaping bang-bang hip)",
    }
    (OUT_DIR / f"v13_5_planC_{name}_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[planC.{name}] -> {csv_path}")
    return csv_path, rows


def run_slice_kE_Estar(grid: int, duration: float) -> tuple[Path, list[dict]]:
    """副产品：plan C 自身参数 k_E x E_star 敏感性，baseline 物理。"""
    name = "kE_Estar"
    xs = linspace(3.0, 15.0, grid)  # k_E
    ys = linspace(50.0, 56.0, grid)  # E_star
    rows: list[dict] = []
    t0 = time.time()
    total = grid * grid
    print(
        f"[planC.{name}] grid={grid}x{grid} = {total} pts, duration={duration}s/pt, "
        f"baseline foot_radius=0.04 leg_scale=1.0"
    )

    for ix, xv in enumerate(xs):
        for iy, yv in enumerate(ys):
            params = make_v135c_params(E_star=yv, k_E=xv, duration=duration)
            try:
                r = evaluate(params)
            except Exception as exc:  # noqa: BLE001
                r = {
                    "success": False,
                    "failure": f"exception:{exc.__class__.__name__}",
                    "cot": float("nan"),
                    "alternating_touchdowns": 0,
                    "forward_distance": 0.0,
                    "simulated_time": 0.0,
                    "active_input_energy_j": 0.0,
                    "score": -1e6,
                    "mean_energy_error_J": float("nan"),
                    "hip_active_duty": 0.0,
                    "E_star": yv,
                    "k_E": xv,
                }
            r["slice"] = "planC_" + name
            r["ix"] = ix
            r["iy"] = iy
            r["k_E_x"] = xv
            r["E_star_y"] = yv
            rows.append(r)
            elapsed = time.time() - t0
            done = ix * grid + iy + 1
            eta = elapsed / done * (total - done)
            print(
                f"  [{done}/{total}] k_E={xv:.2f} E*={yv:.2f} "
                f"success={r['success']} td={r['alternating_touchdowns']} "
                f"duty={r['hip_active_duty']:.2f} ({elapsed:.0f}s elapsed, ETA {eta:.0f}s)"
            )

    OUT_DIR.mkdir(exist_ok=True)
    csv_path = OUT_DIR / f"v13_5_planC_{name}.csv"
    fieldnames = sorted({k for r in rows for k in r.keys()})
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    meta = {
        "slice": "planC_" + name,
        "grid": grid,
        "duration": duration,
        "x": ("k_E", 3.0, 15.0),
        "y": ("E_star", 50.0, 56.0),
        "title": "[plan C] k_E vs E_star (baseline geometry)",
    }
    (OUT_DIR / f"v13_5_planC_{name}_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[planC.{name}] -> {csv_path}")
    return csv_path, rows


def write_comparison(rows_C: list[dict], rows_kE: list[dict] | None = None) -> Path:
    """对比 plan C vs V10 在切片 C 上的成功率。"""
    n_C = len(rows_C)
    succ_C = sum(1 for r in rows_C if r["success"])
    rate_C = succ_C / max(1, n_C) * 100.0
    # V13 切片 C 对照基线（plan V10）的硬编码值（从已存档 csv 读出）
    v10_C_rate = 16.7  # 6/36
    v10_C_succ_cells = [
        ("0.034", "0.90"),
        ("0.038", "0.90"),
        ("0.038", "0.94"),
        ("0.038", "0.98"),
        ("0.046", "1.06"),
        ("0.046", "1.10"),
    ]
    delta = rate_C - v10_C_rate

    succ_cells = [
        (f"{r['foot_radius_x']:.3f}", f"{r['leg_scale_y']:.3f}")
        for r in rows_C
        if r["success"]
    ]
    out = {
        "slice": "C_foot_leg",
        "grid": 6,
        "n_total": n_C,
        "v13_v10_baseline_success": "6/36 = 16.7%",
        "v13_v10_success_cells": v10_C_succ_cells,
        "v13_5_planC_success": f"{succ_C}/{n_C} = {rate_C:.1f}%",
        "v13_5_planC_success_cells": succ_cells,
        "delta_pp": delta,  # percentage points
        "verdict": (
            "improved"
            if delta > 5.0
            else ("regressed" if delta < -5.0 else "comparable")
        ),
    }
    if rows_kE is not None:
        n_kE = len(rows_kE)
        succ_kE = sum(1 for r in rows_kE if r["success"])
        out["v13_5_planC_kE_Estar_success"] = (
            f"{succ_kE}/{n_kE} = {succ_kE/max(1,n_kE)*100:.1f}%"
        )

    path = OUT_DIR / "v13_5_planC_vs_v10.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[planC.compare] -> {path}")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--grid", type=int, default=6)
    parser.add_argument("--duration", type=float, default=12.0)
    parser.add_argument("--E_star", type=float, default=52.66)
    parser.add_argument("--k_E", type=float, default=7.5)
    parser.add_argument(
        "--skip-kE-scan",
        action="store_true",
        help="跳过 k_E x E_star 副扫描（只跑主交付切片 C）",
    )
    args = parser.parse_args()

    OUT_DIR.mkdir(exist_ok=True)
    _, rows_C = run_slice_C_foot_leg(args.grid, args.duration, args.E_star, args.k_E)
    rows_kE = None
    if not args.skip_kE_scan:
        _, rows_kE = run_slice_kE_Estar(args.grid, args.duration)
    summary_path = write_comparison(rows_C, rows_kE)

    # 终端最后一行决议
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    delta = summary["delta_pp"]
    n_succ = sum(1 for r in rows_C if r["success"])
    if delta > 5.0:
        verdict = f"方案 C 改善 {delta:+.1f} pp（{n_succ}/36 vs V10 6/36 = 16.7%）"
    elif delta < -5.0:
        verdict = f"方案 C 反而降低 {delta:+.1f} pp（{n_succ}/36 vs V10 6/36 = 16.7%）"
    else:
        verdict = (
            f"方案 C 与 V10 持平 {delta:+.1f} pp（{n_succ}/36 vs V10 6/36 = 16.7%）"
        )
    print("=" * 70)
    print(f"DECISION: {verdict}")
    print("=" * 70)


if __name__ == "__main__":
    main()
