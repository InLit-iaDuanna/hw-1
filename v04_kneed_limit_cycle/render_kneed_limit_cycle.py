from __future__ import annotations

from pathlib import Path

import imageio.v2 as imageio
import mujoco
import numpy as np
from simulate_kneed_limit_cycle import MODEL_TEMPLATE, OUT_DIR

QPOS_KEYS = ["hip_x", "hip_z", "left_thigh", "left_knee", "right_thigh", "right_knee"]


def load_numeric_csv(path: Path) -> dict[str, np.ndarray]:
    import csv

    with path.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    data: dict[str, list[float]] = {key: [] for key in QPOS_KEYS + ["time"]}
    for row in rows:
        for key in data:
            data[key].append(float(row[key]))
    return {key: np.array(value) for key, value in data.items()}


def qpos_at(t: float, data: dict[str, np.ndarray]) -> list[float]:
    return [float(np.interp(t, data["time"], data[key])) for key in QPOS_KEYS]


def main() -> None:
    data = load_numeric_csv(OUT_DIR / "kneed_limit_cycle_data.csv")
    model = mujoco.MjModel.from_xml_path(str(MODEL_TEMPLATE))
    sim_data = mujoco.MjData(model)

    width, height, fps = 1280, 720, 60
    renderer = mujoco.Renderer(model, height=height, width=width)
    camera = mujoco.MjvCamera()
    camera.type = mujoco.mjtCamera.mjCAMERA_FREE
    camera.distance = 2.9
    camera.azimuth = 66
    camera.elevation = -18

    frames = []
    duration = float(data["time"][-1])
    total_frames = int(duration * fps)
    for frame in range(total_frames):
        t = frame / fps
        sim_data.qpos[:] = qpos_at(t, data)
        sim_data.qvel[:] = 0.0
        mujoco.mj_forward(model, sim_data)
        camera.lookat[:] = [float(sim_data.qpos[0]) + 0.18, 0.0, 0.48]
        renderer.update_scene(sim_data, camera=camera)
        frames.append(renderer.render())

    video_path = OUT_DIR / "kneed_limit_cycle.mp4"
    imageio.mimsave(video_path, frames, fps=fps)
    print(video_path)


if __name__ == "__main__":
    main()
