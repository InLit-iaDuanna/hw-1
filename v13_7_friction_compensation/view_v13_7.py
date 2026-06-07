"""V13.7 interactive MuJoCo viewer."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import mujoco
import mujoco.viewer

ROOT = Path(__file__).resolve().parent
HW1_ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))

from simulate_v13_7 import (  # noqa: E402
    MODEL_PATH,
    PassiveArmsParams,
    V137Params,
    make_v137_fsm,
    write_model_v137,
)

from common.motor_dynamics import PRESETS  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--motor-preset", choices=list(PRESETS.keys()), default="mx64ar"
    )
    parser.add_argument("--no-compensate", action="store_true")
    parser.add_argument("--duration", type=float, default=12.0)
    args = parser.parse_args()

    from dataclasses import replace

    base0 = PassiveArmsParams()
    base = replace(
        base0,
        duration=args.duration,
        arm_mass=0.01,
        arm_length=0.40,
        arm_damping=0.02,
        arm_stiffness=0.0,
        foot_radius=0.042,
        thigh_length=base0.thigh_length * 1.02,
        shank_length=base0.shank_length * 1.02,
        step_length=base0.step_length * 1.02,
    )
    motor = PRESETS[args.motor_preset]
    params = V137Params(
        base=base,
        fsm=make_v137_fsm(base),
        hip_motor=motor,
        knee_motor=motor,
        compensate_friction=not args.no_compensate,
    )
    write_model_v137(params)
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    data = mujoco.MjData(model)
    mujoco.viewer.launch(model, data)


if __name__ == "__main__":
    main()
