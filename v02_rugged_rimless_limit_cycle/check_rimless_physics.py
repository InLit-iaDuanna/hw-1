from __future__ import annotations

import mujoco
import numpy as np
from view_rimless_physics import MODEL_PATH, initialize, ramp_height


def main() -> None:
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    data = mujoco.MjData(model)
    initialize(model, data)
    ramp = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "ramp")
    contacts = 0
    min_clearance = 999.0
    max_x = float(data.qpos[0])
    for _ in range(8000):
        mujoco.mj_step(model, data)
        max_x = max(max_x, float(data.qpos[0]))
        min_clearance = min(
            min_clearance, float(data.qpos[1]) - ramp_height(float(data.qpos[0]))
        )
        for i in range(data.ncon):
            con = data.contact[i]
            if con.geom1 == ramp or con.geom2 == ramp:
                contacts += 1
    print("nu=", model.nu)
    print("contacts=", contacts)
    print("forward_x=", max_x)
    print("min_hub_clearance=", min_clearance)
    print(
        "finite=",
        bool(np.all(np.isfinite(data.qpos)) and np.all(np.isfinite(data.qvel))),
    )


if __name__ == "__main__":
    main()
