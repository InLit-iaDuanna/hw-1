"""V11 MuJoCo Viewer：回放已录的崎岖地形仿真。

用法：先用 simulate_rugged_gait_v11.py 跑出 out/v11_single_data.csv 与 _summary.json，
然后运行本脚本进入交互查看。
"""

from __future__ import annotations

import csv
import json
import time
from dataclasses import asdict

import mujoco
import mujoco.viewer
import numpy as np
from simulate_rugged_gait_v11 import (
    MODEL_PATH,
    OUT_DIR,
    RuggedScenario,
    load_v10_best_params,
    run_rugged_simulation,
    write_model_rugged,
)

from common import terrain
from v10_rolling_foot_biomimetic_gait.simulate_rolling_foot_gait_v10 import (
    QPOS_KEYS,
    RollingFootParams,
)


def load_rows(prefix: str = "v11_single"):
    path = OUT_DIR / f"{prefix}_data.csv"
    with path.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return {
        key: np.array([float(row[key]) for row in rows]) for key in ["time", *QPOS_KEYS]
    }


def qpos_at(t: float, data) -> list[float]:
    t = min(max(t, 0.0), float(data["time"][-1]))
    return [float(np.interp(t, data["time"], data[key])) for key in QPOS_KEYS]


def main(prefix: str = "v11_single") -> None:
    summary_path = OUT_DIR / f"{prefix}_summary.json"
    data_path = OUT_DIR / f"{prefix}_data.csv"
    if not summary_path.exists() or not data_path.exists():
        print(
            f"[view] 未找到 {summary_path.name}，自动跑一次默认场景生成 prefix={prefix} ..."
        )
        params = load_v10_best_params()
        params = params.__class__(**{**asdict(params), "duration": 12.0})
        scenario = RuggedScenario(
            terrain_amplitude_m=0.020,
            terrain_seed=1,
            impulse_force_n=30.0,
            impulse_t_s=4.0,
            impulse_duration_s=0.05,
        )
        run_rugged_simulation(params, scenario, save_prefix=prefix)

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    params = RollingFootParams(**summary["params"])
    scenario_raw = summary["scenario"]
    scenario_raw["impulse_dir"] = tuple(scenario_raw["impulse_dir"])
    scenario = RuggedScenario(**scenario_raw)
    write_model_rugged(params, scenario)

    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    if scenario.terrain_amplitude_m > 0.0:
        profile = terrain.generate_profile(
            scenario.terrain_amplitude_m,
            scenario.terrain_wavelength_m,
            length_m=90.0,
            seed=scenario.terrain_seed,
        )
        terrain.fill_hfield_data(model, profile)
    sim_data = mujoco.MjData(model)

    rows = load_rows(prefix)
    duration = float(rows["time"][-1])
    with mujoco.viewer.launch_passive(model, sim_data) as viewer:
        start = time.time()
        while viewer.is_running():
            t = (time.time() - start) % duration
            sim_data.qpos[:] = qpos_at(t, rows)
            mujoco.mj_forward(model, sim_data)
            viewer.cam.lookat[:] = [float(sim_data.qpos[0]) + 0.25, 0.0, 0.55]
            viewer.cam.distance = 3.2
            viewer.sync()
            time.sleep(1 / 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--prefix", default="v11_single")
    args = parser.parse_args()
    main(args.prefix)
