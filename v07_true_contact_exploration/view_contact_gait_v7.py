from __future__ import annotations

import json
import time

import mujoco
import mujoco.viewer
from simulate_contact_gait_v7 import (
    MODEL_PATH,
    OUT_DIR,
    ContactParams,
    initialize,
    write_model,
)


def main() -> None:
    best_path = OUT_DIR / "v7_best_params.json"
    if best_path.exists():
        payload = json.loads(best_path.read_text(encoding="utf-8"))
        params = ContactParams(**payload["params"])
    else:
        params = ContactParams()
    write_model(params)
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    data = mujoco.MjData(model)
    initialize(model, data, params)

    with mujoco.viewer.launch_passive(model, data) as viewer:
        viewer.cam.distance = 3.1
        viewer.cam.azimuth = 66
        viewer.cam.elevation = -18
        while viewer.is_running():
            frame_start = time.monotonic()
            for _ in range(4):
                mujoco.mj_step(model, data)
            viewer.cam.lookat[:] = [float(data.qpos[0]) + 0.2, 0.0, 0.50]
            viewer.sync()
            sleep_time = 1.0 / 60.0 - (time.monotonic() - frame_start)
            if sleep_time > 0:
                time.sleep(sleep_time)


if __name__ == "__main__":
    main()
