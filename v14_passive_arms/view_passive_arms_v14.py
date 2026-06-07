"""V14 mujoco 交互式回放（读 simulate 写出的 csv）。"""

from __future__ import annotations

import csv
import json
import time

import mujoco
import mujoco.viewer
import numpy as np
from simulate_passive_arms_v14 import (
    MODEL_PATH,
    OUT_DIR,
    QPOS_KEYS,
    PassiveArmsParams,
    write_model,
)

PREFIX = "v14_baseline"


def load_rows():
    p = OUT_DIR / f"{PREFIX}_data.csv"
    with p.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return {k: np.array([float(r[k]) for r in rows]) for k in ["time", *QPOS_KEYS]}


def qpos_at(t: float, data) -> list[float]:
    t = min(max(t, 0.0), float(data["time"][-1]))
    return [float(np.interp(t, data["time"], data[k])) for k in QPOS_KEYS]


def main() -> None:
    summary = json.loads(
        (OUT_DIR / f"{PREFIX}_summary.json").read_text(encoding="utf-8")
    )
    write_model(PassiveArmsParams(**summary["params"]))
    data = load_rows()
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    sim = mujoco.MjData(model)
    duration = float(data["time"][-1])
    with mujoco.viewer.launch_passive(model, sim) as v:
        start = time.time()
        while v.is_running():
            t = (time.time() - start) % duration
            sim.qpos[:] = qpos_at(t, data)
            mujoco.mj_forward(model, sim)
            v.cam.lookat[:] = [float(sim.qpos[0]) + 0.25, 0.0, 0.55]
            v.cam.distance = 3.4
            v.sync()
            time.sleep(1 / 60)


if __name__ == "__main__":
    main()
