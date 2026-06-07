"""V13 视化辅助：从切片 CSV 取一格 params，重跑 V10 simulate 并写 v13_<tag>_data.csv。

view_v13 / render_v13 都依赖这个产出的 CSV 做 playback。

用法：
  python replay_cell_v13.py --slice C_foot_leg --ix 3 --iy 3        # 重跑该格
  python replay_cell_v13.py --tag baseline                          # 重跑 baseline
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from dataclasses import fields
from pathlib import Path

ROOT = Path(__file__).resolve().parent
V10_DIR = ROOT.parent / "v10_rolling_foot_biomimetic_gait"
sys.path.insert(0, str(V10_DIR))

from simulate_rolling_foot_gait_v10 import (
    OUT_DIR as V10_OUT,
)  # noqa: E402
from simulate_rolling_foot_gait_v10 import (
    RollingFootParams,
    run_simulation,
)

OUT_DIR = ROOT / "out"


def load_cell(slice_name: str, ix: int, iy: int) -> tuple[RollingFootParams, dict]:
    csv_path = OUT_DIR / f"v13_{slice_name}.csv"
    with csv_path.open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if int(row["ix"]) == ix and int(row["iy"]) == iy:
                valid = {f.name for f in fields(RollingFootParams)}
                kwargs = {}
                for k, v in row.items():
                    if k not in valid:
                        continue
                    try:
                        kwargs[k] = float(v)
                    except (TypeError, ValueError):
                        pass
                return RollingFootParams(**kwargs), row
    raise SystemExit(f"cell ({ix},{iy}) not found in {csv_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slice", default=None)
    parser.add_argument("--ix", type=int, default=None)
    parser.add_argument("--iy", type=int, default=None)
    parser.add_argument(
        "--tag",
        default=None,
        help="自定义保存前缀；默认 v13_{slice}_{ix}_{iy} 或 v13_baseline",
    )
    parser.add_argument(
        "--baseline", action="store_true", help="重跑 baseline 而非切片格"
    )
    parser.add_argument("--duration", type=float, default=12.0)
    args = parser.parse_args()

    if args.baseline or args.slice is None:
        from simulate_v13 import BASELINE

        params = BASELINE
        tag = args.tag or "v13_baseline"
        meta = {"source": "baseline"}
    else:
        if args.ix is None or args.iy is None:
            raise SystemExit("need --ix and --iy when --slice given")
        params, meta = load_cell(args.slice, args.ix, args.iy)
        tag = args.tag or f"v13_{args.slice}_{args.ix}_{args.iy}"

    OUT_DIR.mkdir(exist_ok=True)
    print(
        f"[{tag}] running with slope={params.slope_deg:.2f} foot_r={params.foot_radius:.3f} "
        f"thigh={params.thigh_length:.2f} kp={params.hip_kp:.1f} kd={params.hip_kd:.2f}"
    )
    rows, summary = run_simulation(params, save_prefix=tag, sample_hz=160.0)
    summary["replay_meta"] = meta
    for suffix in ("_data.csv", "_summary.json"):
        src = V10_OUT / f"{tag}{suffix}"
        if src.exists():
            shutil.move(str(src), str(OUT_DIR / f"{tag}{suffix}"))
    (OUT_DIR / f"{tag}_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"  success={summary['success']} td={summary['alternating_touchdowns']} "
        f"dist={summary['forward_distance']:.2f} fail={summary['failure']}"
    )
    print(f"  -> {OUT_DIR / (tag + '_data.csv')}")


if __name__ == "__main__":
    main()
