"""V13 交互式 viewer：playback 由 replay_cell_v13.py 产出的 v13_<tag>_data.csv。

用法：
  python view_v13.py --tag v13_baseline
  python view_v13.py --tag v13_C_foot_leg_3_3
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from dataclasses import fields
from pathlib import Path

import mujoco
import mujoco.viewer
import numpy as np

ROOT = Path(__file__).resolve().parent
V10_DIR = ROOT.parent / "v10_rolling_foot_biomimetic_gait"
sys.path.insert(0, str(V10_DIR))

from simulate_rolling_foot_gait_v10 import (
    MODEL_PATH,
    QPOS_KEYS,
    RollingFootParams,
    write_model,
)  # noqa: E402

OUT_DIR = ROOT / "out"


def load_rows(tag: str):
    path = OUT_DIR / f"{tag}_data.csv"
    if not path.exists():
        raise SystemExit(f"{path} not found — run replay_cell_v13.py first")
    with path.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return {k: np.array([float(r[k]) for r in rows]) for k in ["time", *QPOS_KEYS]}


def load_params(tag: str) -> RollingFootParams:
    import json

    summary = json.loads((OUT_DIR / f"{tag}_summary.json").read_text(encoding="utf-8"))
    p = summary["params"]
    valid = {f.name for f in fields(RollingFootParams)}
    return RollingFootParams(**{k: v for k, v in p.items() if k in valid})


def qpos_at(t: float, data) -> list[float]:
    t = min(max(t, 0.0), float(data["time"][-1]))
    return [float(np.interp(t, data["time"], data[k])) for k in QPOS_KEYS]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default="v13_baseline")
    args = parser.parse_args()

    write_model(load_params(args.tag))
    data = load_rows(args.tag)
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    sim = mujoco.MjData(model)
    duration = float(data["time"][-1])
    print(f"[viewer] {args.tag} duration={duration:.2f}s")
    with mujoco.viewer.launch_passive(model, sim) as viewer:
        start = time.time()
        while viewer.is_running():
            t = (time.time() - start) % duration
            sim.qpos[:] = qpos_at(t, data)
            mujoco.mj_forward(model, sim)
            viewer.cam.lookat[:] = [float(sim.qpos[0]) + 0.25, 0.0, 0.55]
            viewer.cam.distance = 3.2
            viewer.sync()
            time.sleep(1 / 60)


if __name__ == "__main__":
    main()
