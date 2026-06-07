"""V17 offline MP4 renderer：可视化传感器噪声 + 状态估计闭环步态。"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import imageio.v2 as imageio
import mujoco
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
HW1_ROOT = ROOT.parent
V14_DIR = HW1_ROOT / "v14_passive_arms"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(V14_DIR))

from simulate_passive_arms_v14 import QPOS_KEYS  # noqa: E402
from simulate_v17 import (  # noqa: E402
    MODEL_PATH,
    OUT_DIR,
    PassiveArmsParams,
    V17Params,
    make_v17_fsm,
    write_model_v17,
)

sys.path.insert(0, str(HW1_ROOT))
from sensor_model import SensorNoiseParams  # noqa: E402

from common.motor_dynamics import PRESETS  # noqa: E402

FONT = Path("C:/Windows/Fonts/msyh.ttc")


def load_rows(path: Path):
    with path.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    numeric = [
        "time",
        *QPOS_KEYS,
        "left_contact",
        "right_contact",
        "hip_clearance",
        "input_energy",
    ]
    out = {}
    for key in numeric:
        out[key] = np.array([float(row.get(key, 0.0) or 0.0) for row in rows])
    return out


def qpos_at(t: float, data) -> list[float]:
    t = min(max(t, 0.0), float(data["time"][-1]))
    return [float(np.interp(t, data["time"], data[key])) for key in QPOS_KEYS]


def _font(size: int):
    if FONT.exists():
        return ImageFont.truetype(str(FONT), size)
    return ImageFont.load_default()


def annotate(frame: np.ndarray, t: float, data, summary: dict) -> np.ndarray:
    image = Image.fromarray(frame)
    draw = ImageDraw.Draw(image, "RGBA")
    title_font = _font(28)
    info_font = _font(20)

    left = int(round(float(np.interp(t, data["time"], data["left_contact"]))))
    right = int(round(float(np.interp(t, data["time"], data["right_contact"]))))
    contact = (
        "left"
        if left and not right
        else "right" if right and not left else "double" if left and right else "flight"
    )
    clearance = float(np.interp(t, data["time"], data["hip_clearance"]))
    energy = float(np.interp(t, data["time"], data["input_energy"]))

    noise_scale = summary.get("sensor_noise_scale", 1.0)
    rmse_vx = summary.get("estimation_rmse_vx", 0.0)
    rmse_hip = summary.get("estimation_rmse_hip_x", 0.0)

    title = (
        f"V17 State Estimation | noise_scale={noise_scale:.1f} | mx64ar + friction comp"
    )

    draw.rectangle((24, 22, 1250, 186), fill=(8, 14, 24, 195))
    draw.text((42, 30), title, font=title_font, fill=(255, 255, 255))
    draw.text(
        (44, 68),
        f"contact: {contact} | clearance {clearance:.2f} m | E_in {energy:.2f} J",
        font=info_font,
        fill=(232, 238, 244),
    )
    draw.text(
        (44, 98),
        f"RMSE vx {rmse_vx:.4f} m/s | RMSE hip_x {rmse_hip:.4f} m | encoder 4096 CPR + Kalman",
        font=info_font,
        fill=(172, 255, 191),
    )
    draw.text(
        (44, 128),
        f"alt_td {summary['alternating_touchdowns']} | fwd {summary['forward_distance']:.2f} m | "
        f"success {summary['success']} | failure: {summary.get('failure', '?')}",
        font=info_font,
        fill=(255, 220, 160),
    )
    return np.array(image)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default="v17_mx64ar_noise1")
    parser.add_argument("--fps", type=int, default=60)
    args = parser.parse_args()

    summary_path = OUT_DIR / f"{args.tag}_summary.json"
    data_path = OUT_DIR / f"{args.tag}_data.csv"
    if not summary_path.exists():
        print(f"ERROR: {summary_path} not found. Run simulate_v17.py first.")
        sys.exit(1)
    if not data_path.exists():
        print("No data.csv found, re-running simulation to generate it...")
        from dataclasses import replace as dreplace

        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        base0 = PassiveArmsParams()
        base = dreplace(
            base0,
            duration=12.0,
            arm_mass=0.01,
            arm_length=0.40,
            arm_damping=0.02,
            arm_stiffness=0.0,
            foot_radius=0.042,
            thigh_length=base0.thigh_length * 1.02,
            shank_length=base0.shank_length * 1.02,
            step_length=base0.step_length * 1.02,
        )
        noise_scale = summary.get("sensor_noise_scale", 1.0)
        motor = PRESETS["mx64ar"]
        params = V17Params(
            base=base,
            fsm=make_v17_fsm(base),
            hip_motor=motor,
            knee_motor=motor,
            compensate_friction=True,
            sensor_noise=SensorNoiseParams(noise_scale=noise_scale),
        )
        from simulate_v17 import run_simulation_v17

        run_simulation_v17(params, save_prefix=args.tag, sample_hz=160.0)

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    data = load_rows(data_path)

    base0 = PassiveArmsParams()
    from dataclasses import replace as dreplace

    base = dreplace(
        base0,
        duration=12.0,
        arm_mass=0.01,
        arm_length=0.40,
        arm_damping=0.02,
        arm_stiffness=0.0,
        foot_radius=0.042,
        thigh_length=base0.thigh_length * 1.02,
        shank_length=base0.shank_length * 1.02,
        step_length=base0.step_length * 1.02,
    )
    motor = PRESETS["mx64ar"]
    params = V17Params(
        base=base,
        fsm=make_v17_fsm(base),
        hip_motor=motor,
        knee_motor=motor,
        compensate_friction=True,
        sensor_noise=SensorNoiseParams(
            noise_scale=summary.get("sensor_noise_scale", 1.0)
        ),
    )
    write_model_v17(params)

    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    sim = mujoco.MjData(model)
    renderer = mujoco.Renderer(model, height=720, width=1280)
    camera = mujoco.MjvCamera()
    camera.distance = 3.4
    camera.azimuth = 66
    camera.elevation = -18

    duration = max(float(data["time"][-1]), 1.0 / max(1, args.fps))
    frame_count = max(1, int(duration * args.fps))
    out_path = OUT_DIR / f"{args.tag}.mp4"
    preview_frame = None

    with imageio.get_writer(out_path, fps=args.fps) as writer:
        for idx in range(frame_count):
            t = idx / args.fps
            sim.qpos[:] = qpos_at(t, data)
            sim.qvel[:] = 0.0
            mujoco.mj_forward(model, sim)
            camera.lookat[:] = [float(sim.qpos[0]) + 0.25, 0.0, 0.55]
            renderer.update_scene(sim, camera=camera)
            frame = annotate(renderer.render(), t, data, summary)
            writer.append_data(frame)
            if idx == min(frame_count - 1, 120):
                preview_frame = frame

    if preview_frame is not None:
        imageio.imwrite(OUT_DIR / f"{args.tag}_preview.png", preview_frame)
    print(f"Rendered: {out_path}")


if __name__ == "__main__":
    main()
