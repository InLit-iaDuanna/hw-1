"""Interactive MuJoCo playback for V14b CSV outputs."""

from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path

import mujoco
import mujoco.viewer
import numpy as np
from simulate_passive_arms_v136 import (
    MODEL_PATH,
    OUT_DIR,
    QPOS_KEYS,
    PassiveArmsParams,
    write_model,
)


def load_rows(path: Path):
    with path.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return {
        key: np.array([float(row[key]) for row in rows]) for key in ["time", *QPOS_KEYS]
    }


def qpos_at(t: float, data) -> list[float]:
    t = min(max(t, 0.0), float(data["time"][-1]))
    return [float(np.interp(t, data["time"], data[key])) for key in QPOS_KEYS]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default="v14b_critical")
    args = parser.parse_args()

    summary = json.loads(
        (OUT_DIR / f"{args.tag}_summary.json").read_text(encoding="utf-8")
    )
    write_model(PassiveArmsParams(**summary["params"]))
    data = load_rows(OUT_DIR / f"{args.tag}_data.csv")
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    sim = mujoco.MjData(model)
    duration = max(float(data["time"][-1]), 1 / 60)
    with mujoco.viewer.launch_passive(model, sim) as viewer:
        start = time.time()
        while viewer.is_running():
            t = (time.time() - start) % duration
            sim.qpos[:] = qpos_at(t, data)
            mujoco.mj_forward(model, sim)
            viewer.cam.lookat[:] = [float(sim.qpos[0]) + 0.25, 0.0, 0.55]
            viewer.cam.distance = 3.4
            viewer.sync()
            time.sleep(1 / 60)


if __name__ == "__main__":
    main()
