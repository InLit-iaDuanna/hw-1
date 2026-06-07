from __future__ import annotations

import imageio.v2 as imageio
import mujoco
from playback_utils import OUT_DIR, load_playback_data, qpos_smooth_visual_at

MODEL_PATH = OUT_DIR.parent / "models" / "hybrid_compass_visual.xml"


def main() -> None:
    playback = load_playback_data()
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    data = mujoco.MjData(model)

    width, height, fps = 1280, 720, 30
    renderer = mujoco.Renderer(model, height=height, width=width)
    camera = mujoco.MjvCamera()
    camera.type = mujoco.mjtCamera.mjCAMERA_FREE
    camera.distance = 2.8
    camera.azimuth = 66
    camera.elevation = -18

    duration = 16.0
    frames = []
    for frame in range(int(duration * fps)):
        t = frame / fps
        data.qpos[:] = qpos_smooth_visual_at(t, playback)
        data.qvel[:] = 0.0
        mujoco.mj_forward(model, data)
        camera.lookat[:] = [float(data.qpos[0]) + 0.20, 0.0, 0.42]
        renderer.update_scene(data, camera=camera)
        frames.append(renderer.render())

    out = OUT_DIR / "hybrid_compass_mujoco.mp4"
    imageio.mimsave(out, frames, fps=fps)
    imageio.imwrite(
        OUT_DIR / "hybrid_compass_preview.png", frames[min(60, len(frames) - 1)]
    )
    print(out)


if __name__ == "__main__":
    main()
