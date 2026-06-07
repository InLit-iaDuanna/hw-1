from __future__ import annotations

import csv
import json
import time

import mujoco
import mujoco.viewer
import numpy as np
from simulate_rolling_foot_gait_v10 import (
    MODEL_PATH,
    OUT_DIR,
    QPOS_KEYS,
    RollingFootParams,
    write_model,
)


def load_rows():
    with (OUT_DIR / "v10_rolling_foot_walk_data.csv").open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return {
        key: np.array([float(row[key]) for row in rows]) for key in ["time", *QPOS_KEYS]
    }


def qpos_at(t: float, data: dict[str, np.ndarray]) -> list[float]:
    t = min(max(t, 0.0), float(data["time"][-1]))
    return [float(np.interp(t, data["time"], data[key])) for key in QPOS_KEYS]


def main() -> None:
    summary = json.loads((OUT_DIR / "v10_best_params.json").read_text(encoding="utf-8"))
    write_model(RollingFootParams(**summary["params"]))
    data = load_rows()
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    sim_data = mujoco.MjData(model)
    duration = float(data["time"][-1])
    with mujoco.viewer.launch_passive(model, sim_data) as viewer:
        start = time.time()
        while viewer.is_running():
            t = (time.time() - start) % duration
            sim_data.qpos[:] = qpos_at(t, data)
            mujoco.mj_forward(model, sim_data)
            viewer.cam.lookat[:] = [float(sim_data.qpos[0]) + 0.25, 0.0, 0.55]
            viewer.cam.distance = 3.2
            viewer.sync()
            time.sleep(1 / 60)


if __name__ == "__main__":
    main()
