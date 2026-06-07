"""V13.6 交互式回放（mujoco viewer），读取 out/v13_6_baseline_data.csv 重放。

用法：直接运行，弹出 viewer 窗口循环播放。
"""

from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path

import mujoco
import mujoco.viewer
import numpy as np

ROOT = Path(__file__).resolve().parent
V10_DIR = ROOT.parent / "v10_rolling_foot_biomimetic_gait"
sys.path.insert(0, str(V10_DIR))
sys.path.insert(0, str(ROOT))

from simulate_rolling_foot_gait_v10 import (
    MODEL_PATH,
    QPOS_KEYS,
    RollingFootParams,
    write_model,
)  # noqa: E402

OUT_DIR = ROOT / "out"


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
    summary = json.loads(
        (OUT_DIR / "v13_6_baseline_summary.json").read_text(encoding="utf-8")
    )
    write_model(RollingFootParams(**summary["params"]))
    data = load_rows(OUT_DIR / "v13_6_baseline_data.csv")
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
