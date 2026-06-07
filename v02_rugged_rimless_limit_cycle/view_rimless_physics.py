from __future__ import annotations

import math
import time
from pathlib import Path

import mujoco
import mujoco.viewer

ROOT = Path(__file__).resolve().parent
MODEL_PATH = ROOT / "models" / "rimless_wheel_physics.xml"
SLOPE_DEG = 5.0
FOOT_RADIUS = 0.045
LEG_LENGTH = 1.0
ALPHA = math.pi / 8.0


def ramp_height(x: float) -> float:
    return -math.tan(math.radians(SLOPE_DEG)) * x


def initialize(model: mujoco.MjModel, data: mujoco.MjData) -> None:
    theta = 0.0
    stance_foot_x = 0.0
    stance_foot_z = ramp_height(stance_foot_x) + FOOT_RADIUS / math.cos(
        math.radians(SLOPE_DEG)
    )
    hub_x = stance_foot_x + LEG_LENGTH * math.sin(theta)
    hub_z = stance_foot_z + LEG_LENGTH * math.cos(theta)
    data.qpos[:] = [hub_x, hub_z, theta]
    data.qvel[:] = [0.0, 0.0, 0.10]
    mujoco.mj_forward(model, data)


def main() -> None:
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    data = mujoco.MjData(model)
    initialize(model, data)

    with mujoco.viewer.launch_passive(model, data) as viewer:
        viewer.cam.distance = 3.0
        viewer.cam.azimuth = 66
        viewer.cam.elevation = -18
        last_reset = time.monotonic()

        while viewer.is_running():
            frame_start = time.monotonic()
            for _ in range(4):
                mujoco.mj_step(model, data)

            # Keep the demo readable: reset only after a fall or after it rolls
            # far past the camera, not every gait event.
            hip_clearance = float(data.qpos[1]) - ramp_height(float(data.qpos[0]))
            if (
                hip_clearance < 0.2
                or abs(float(data.qvel[2])) > 12
                or time.monotonic() - last_reset > 35
            ):
                initialize(model, data)
                last_reset = time.monotonic()

            viewer.cam.lookat[:] = [
                float(data.qpos[0]) + 0.25,
                0.0,
                float(data.qpos[1]) - 0.45,
            ]
            viewer.sync()
            sleep_time = 1.0 / 60.0 - (time.monotonic() - frame_start)
            if sleep_time > 0:
                time.sleep(sleep_time)


if __name__ == "__main__":
    main()
