from __future__ import annotations

import time

import mujoco
import mujoco.viewer
from playback_utils import OUT_DIR, load_playback_data, qpos_smooth_visual_at

MODEL_PATH = OUT_DIR.parent / "models" / "hybrid_compass_visual.xml"


def main() -> None:
    playback = load_playback_data()
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    data = mujoco.MjData(model)

    with mujoco.viewer.launch_passive(model, data) as viewer:
        viewer.cam.distance = 2.8
        viewer.cam.azimuth = 66
        viewer.cam.elevation = -18
        sim_t = 0.0
        dt = 1.0 / 120.0
        speed = 0.75

        while viewer.is_running():
            start = time.time()
            sim_t += dt * speed
            data.qpos[:] = qpos_smooth_visual_at(sim_t, playback)
            data.qvel[:] = 0.0
            mujoco.mj_forward(model, data)
            viewer.cam.lookat[:] = [float(data.qpos[0]) + 0.20, 0.0, 0.42]
            viewer.sync()
            sleep_time = dt - (time.time() - start)
            if sleep_time > 0:
                time.sleep(sleep_time)


if __name__ == "__main__":
    main()
