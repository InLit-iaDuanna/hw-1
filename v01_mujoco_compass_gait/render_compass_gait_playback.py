from __future__ import annotations

import imageio.v2 as imageio
import mujoco
from simulate_compass_gait import OUT_DIR, Params
from view_compass_gait import playback_qpos, write_playback_model


def main() -> None:
    params = Params()
    model_path = OUT_DIR / "_playback_compass_gait.xml"
    write_playback_model(params, model_path)
    model = mujoco.MjModel.from_xml_path(str(model_path))
    data = mujoco.MjData(model)

    width, height, fps = 1280, 720, 60
    renderer = mujoco.Renderer(model, height=height, width=width)
    camera = mujoco.MjvCamera()
    camera.type = mujoco.mjtCamera.mjCAMERA_FREE
    camera.distance = 2.7
    camera.azimuth = 65
    camera.elevation = -18

    frames = []
    duration = 6.6
    total_frames = int(duration * fps)
    for frame in range(total_frames):
        t = frame / fps
        data.qpos[:] = playback_qpos(t, params)
        data.qvel[:] = 0.0
        mujoco.mj_forward(model, data)
        camera.lookat[:] = [float(data.qpos[0]) + 0.2, 0.0, 0.45]
        renderer.update_scene(data, camera=camera)
        frames.append(renderer.render())

    video_path = OUT_DIR / "compass_gait_playback.mp4"
    imageio.mimsave(video_path, frames, fps=fps)
    print(video_path)


if __name__ == "__main__":
    main()
