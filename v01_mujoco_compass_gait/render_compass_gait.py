from __future__ import annotations

import json
from pathlib import Path

import imageio.v2 as imageio
import mujoco
import numpy as np
from simulate_compass_gait import OUT_DIR, Params, initialize_state, write_param_model

ROOT = Path(__file__).resolve().parent


def load_best_params() -> Params:
    report = json.loads((OUT_DIR / "best_params.json").read_text(encoding="utf-8"))
    return Params(**report["best_params"])


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    params = load_best_params()
    model_path = OUT_DIR / "_render_compass_gait.xml"
    write_param_model(params, model_path)
    model = mujoco.MjModel.from_xml_path(str(model_path))
    data = mujoco.MjData(model)
    initialize_state(model, data, params)

    width, height, fps = 1280, 720, 30
    renderer = mujoco.Renderer(model, height=height, width=width)
    frames = []
    duration = 8.0
    next_frame = 0.0
    camera = mujoco.MjvCamera()
    camera.type = mujoco.mjtCamera.mjCAMERA_FREE
    camera.distance = 3.1
    camera.azimuth = 65
    camera.elevation = -14

    while data.time < duration:
        mujoco.mj_step(model, data)
        if data.time >= next_frame:
            camera.lookat[:] = [float(data.qpos[0]) + 0.25, 0.0, 0.45]
            renderer.update_scene(data, camera=camera)
            frame = renderer.render()
            frames.append(frame)
            next_frame += 1 / fps
        if not np.all(np.isfinite(data.qpos)) or abs(float(data.qvel[0])) > 25:
            break

    video_path = OUT_DIR / "passive_compass_gait.mp4"
    imageio.mimsave(video_path, frames, fps=fps)
    print(video_path)


if __name__ == "__main__":
    main()
