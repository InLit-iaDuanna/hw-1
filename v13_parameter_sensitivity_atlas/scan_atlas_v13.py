"""V13 参数图集扫描器。

四张 2D 切片（slice A/B/C/D），每张产出 CSV + 二维栅格，供 analyze/render 消费。
默认 6x6 栅格 + 12 s/点。可用 --grid 4 跑粗 smoke 测试。
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from dataclasses import replace
from pathlib import Path

from simulate_v13 import evaluate, make_params

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "out"


def linspace(a: float, b: float, n: int) -> list[float]:
    if n <= 1:
        return [a]
    return [a + (b - a) * i / (n - 1) for i in range(n)]


SLICES = {
    "A_slope_foot": {
        "x": ("slope_deg", -1.0, 1.0),
        "y": ("foot_radius", 0.030, 0.050),
        "title": "slope_deg vs foot_radius",
    },
    "B_slope_leg": {
        "x": ("slope_deg", -1.0, 1.0),
        "y": ("leg_scale", 0.90, 1.10),
        "title": "slope_deg vs leg_scale",
    },
    "C_foot_leg": {
        "x": ("foot_radius", 0.030, 0.050),
        "y": ("leg_scale", 0.90, 1.10),
        "title": "foot_radius vs leg_scale",
    },
    "D_slope_torso": {
        "x": ("slope_deg", -1.0, 1.0),
        "y": ("torso_ratio", 0.005, 0.050),
        "title": "slope_deg vs torso_ratio (m_torso / m_hip)",
    },
    "E_hip_gains": {
        "x": ("hip_kp", 15.0, 45.0),
        "y": ("hip_kd", 3.0, 9.0),
        "title": "hip_kp vs hip_kd (slope=0, geometry=baseline)",
    },
    "F_kp_ratio": {
        "x": ("hip_kp", 15.0, 45.0),
        "y": ("hip_kd_ratio", 0.10, 0.30),
        "title": "hip_kp vs hip_kd/hip_kp ratio",
    },
    "G_kp_torque": {
        "x": ("hip_kp", 15.0, 45.0),
        "y": ("hip_torque_limit", 4.0, 20.0),
        "title": "hip_kp vs hip_torque_limit (ratio=0.20 fixed)",
        "fixed": {"hip_kd_ratio": 0.20},
    },
}


def run_slice(name: str, grid: int, duration: float) -> Path:
    spec = SLICES[name]
    xkey, x0, x1 = spec["x"]
    ykey, y0, y1 = spec["y"]
    fixed = spec.get("fixed", {})
    xs = linspace(x0, x1, grid)
    ys = linspace(y0, y1, grid)

    rows: list[dict] = []
    t0 = time.time()
    total = grid * grid
    print(f"[{name}] grid={grid}x{grid} = {total} pts, duration={duration}s/pt")

    for ix, xv in enumerate(xs):
        for iy, yv in enumerate(ys):
            kwargs = {xkey: xv, ykey: yv, **fixed}
            params = replace(make_params(**kwargs), duration=duration)
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
                }
            r["slice"] = name
            r["ix"] = ix
            r["iy"] = iy
            r[xkey + "_x"] = xv
            r[ykey + "_y"] = yv
            rows.append(r)
            elapsed = time.time() - t0
            done = ix * grid + iy + 1
            eta = elapsed / done * (total - done)
            print(
                f"  [{done}/{total}] {xkey}={xv:.3f} {ykey}={yv:.3f} "
                f"success={r['success']} td={r['alternating_touchdowns']} "
                f"cot={r['cot']:.3f} ({elapsed:.0f}s elapsed, ETA {eta:.0f}s)"
            )

    OUT_DIR.mkdir(exist_ok=True)
    csv_path = OUT_DIR / f"v13_{name}.csv"
    fieldnames = sorted({k for r in rows for k in r.keys()})
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    meta = {
        "slice": name,
        "grid": grid,
        "duration": duration,
        "x": spec["x"],
        "y": spec["y"],
        "title": spec["title"],
    }
    (OUT_DIR / f"v13_{name}_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[{name}] -> {csv_path}")
    return csv_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--grid", type=int, default=6, help="N x N 栅格分辨率")
    parser.add_argument("--duration", type=float, default=12.0, help="单点仿真秒数")
    parser.add_argument(
        "--slice", type=str, default="all", choices=["all", *SLICES.keys()]
    )
    args = parser.parse_args()

    names = list(SLICES.keys()) if args.slice == "all" else [args.slice]
    for name in names:
        run_slice(name, args.grid, args.duration)


if __name__ == "__main__":
    main()
