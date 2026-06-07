from __future__ import annotations

import math
import time
from pathlib import Path

import mujoco
import mujoco.viewer
from simulate_compass_gait import (
    LEG_LENGTH,
    OUT_DIR,
    Params,
    ramp_height,
    write_param_model,
)

PLAYBACK_LEG_OFFSET = 0.095
HIP_SOCKET_DROP = 0.07


def playback_qpos(t: float, params: Params) -> list[float]:
    step_length = 0.34
    step_time = 0.74
    foot_radius = params.foot_radius
    step_index = int(t // step_time)
    phase = (t % step_time) / step_time
    stance_s = step_index * step_length
    stance_limit = math.asin(step_length / (2.0 * LEG_LENGTH))

    # Keep nonzero stance angular speed, like an inverted pendulum rolling over
    # the support foot. The impact switches legs, but the hip should not pause.
    stance_q = -stance_limit + 2.0 * stance_limit * phase
    swing_q = stance_limit - 2.0 * stance_limit * phase
    swing_q -= 0.14 * math.sin(math.pi * phase)

    hip_x = stance_s + LEG_LENGTH * math.sin(stance_q)
    ramp_x = stance_s + phase * step_length
    hip_z = (
        ramp_height(ramp_x, math.radians(params.slope_deg))
        + foot_radius
        + LEG_LENGTH * math.cos(stance_q)
    )

    if step_index % 2 == 0:
        return [hip_x, hip_z, stance_q, swing_q]
    return [hip_x, hip_z, swing_q, stance_q]


def write_playback_model(params: Params, target: Path) -> None:
    write_param_model(params, target)
    xml = target.read_text(encoding="utf-8")
    xml = xml.replace(
        '<body name="left_leg" pos="0 -0.035 0">',
        f'<body name="left_leg" pos="0 -{PLAYBACK_LEG_OFFSET:.3f} 0">',
    )
    xml = xml.replace(
        '<body name="right_leg" pos="0 0.035 0">',
        f'<body name="right_leg" pos="0 {PLAYBACK_LEG_OFFSET:.3f} 0">',
    )
    xml = xml.replace(
        '<geom name="left_shank" type="capsule" fromto="0 0 0 0 0 -1.0"',
        f'<geom name="left_shank" type="capsule" fromto="0 0 -{HIP_SOCKET_DROP:.3f} 0 0 -1.0"',
    )
    xml = xml.replace(
        '<geom name="right_shank" type="capsule" fromto="0 0 0 0 0 -1.0"',
        f'<geom name="right_shank" type="capsule" fromto="0 0 -{HIP_SOCKET_DROP:.3f} 0 0 -1.0"',
    )
    target.write_text(xml, encoding="utf-8")


def main() -> None:
    params = Params()
    model_path = OUT_DIR / "_viewer_compass_gait.xml"
    write_playback_model(params, model_path)
    model = mujoco.MjModel.from_xml_path(str(model_path))
    data = mujoco.MjData(model)

    with mujoco.viewer.launch_passive(model, data) as viewer:
        viewer.cam.distance = 2.7
        viewer.cam.azimuth = 65
        viewer.cam.elevation = -18
        duration = 6.6
        sim_t = 0.0
        target_frame_dt = 1.0 / 60.0
        last_tick = time.monotonic()

        while viewer.is_running():
            frame_start = time.monotonic()
            elapsed = min(frame_start - last_tick, 1.0 / 30.0)
            last_tick = frame_start
            sim_t = (sim_t + elapsed) % duration
            data.qpos[:] = playback_qpos(sim_t, params)
            data.qvel[:] = 0.0
            mujoco.mj_forward(model, data)
            viewer.cam.lookat[:] = [float(data.qpos[0]) + 0.2, 0.0, 0.45]
            viewer.sync()
            sleep_time = target_frame_dt - (time.monotonic() - frame_start)
            if sleep_time > 0:
                time.sleep(sleep_time)


if __name__ == "__main__":
    main()
