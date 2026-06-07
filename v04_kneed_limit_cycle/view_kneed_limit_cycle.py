from __future__ import annotations

import time

import mujoco
import mujoco.viewer
from render_kneed_limit_cycle import load_numeric_csv, qpos_at
from simulate_kneed_limit_cycle import MODEL_TEMPLATE, OUT_DIR


def main() -> None:
    data = load_numeric_csv(OUT_DIR / "kneed_limit_cycle_data.csv")
    model = mujoco.MjModel.from_xml_path(str(MODEL_TEMPLATE))
    sim_data = mujoco.MjData(model)

    with mujoco.viewer.launch_passive(model, sim_data) as viewer:
        viewer.cam.distance = 2.9
        viewer.cam.azimuth = 66
        viewer.cam.elevation = -18
        duration = float(data["time"][-1])
        playback_t = 0.0
        target_frame_dt = 1.0 / 60.0
        last_tick = time.monotonic()

        while viewer.is_running():
            frame_start = time.monotonic()
            elapsed = min(frame_start - last_tick, 1.0 / 30.0)
            last_tick = frame_start
            playback_t = (playback_t + elapsed) % duration
            sim_data.qpos[:] = qpos_at(playback_t, data)
            sim_data.qvel[:] = 0.0
            mujoco.mj_forward(model, sim_data)
            viewer.cam.lookat[:] = [float(sim_data.qpos[0]) + 0.18, 0.0, 0.48]
            viewer.sync()
            sleep_time = target_frame_dt - (time.monotonic() - frame_start)
            if sleep_time > 0:
                time.sleep(sleep_time)


if __name__ == "__main__":
    main()
