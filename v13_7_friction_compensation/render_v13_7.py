"""V13.7 offline MP4 renderer：可视化摩擦补偿前后的步态对比。"""

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
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HW1_ROOT / "v14_passive_arms"))

from simulate_passive_arms_v14 import QPOS_KEYS  # noqa: E402
from simulate_v13_7 import (  # noqa: E402
    MODEL_PATH,
    OUT_DIR,
    PassiveArmsParams,
    V137Params,
    make_v137_fsm,
    write_model_v137,
)

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
        "E_current",
        "A_swing",
    ]
    extra_numeric = [
        "tau_l_hip_des",
        "tau_r_hip_des",
        "tau_l_hip_out",
        "tau_r_hip_out",
        "P_elec",
    ]
    out = {}
    for key in numeric + extra_numeric:
        out[key] = np.array([float(row.get(key, 0.0) or 0.0) for row in rows])
    out["left_phase"] = [row.get("left_phase", "") for row in rows]
    out["right_phase"] = [row.get("right_phase", "") for row in rows]
    return out


def qpos_at(t: float, data) -> list[float]:
    t = min(max(t, 0.0), float(data["time"][-1]))
    return [float(np.interp(t, data["time"], data[key])) for key in QPOS_KEYS]


def phase_at(t: float, data) -> tuple[str, str]:
    idx = int(np.argmin(np.abs(data["time"] - t)))
    return data["left_phase"][idx], data["right_phase"][idx]


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
    tau_l = float(np.interp(t, data["time"], data["tau_l_hip_out"]))
    tau_r = float(np.interp(t, data["time"], data["tau_r_hip_out"]))
    lp, rp = phase_at(t, data)

    compensate = summary.get("compensate_friction", True)
    motor_name = summary.get("v13_7_motor", {}).get("hip", {}).get("name", "?")
    tau_C = summary.get("v13_7_motor", {}).get("hip", {}).get("joint_tau_C_eff", 0.0)

    comp_label = "ON" if compensate else "OFF"
    title = f"V13.7 Friction Compensation [{comp_label}] | {motor_name}"

    draw.rectangle((24, 22, 1250, 186), fill=(8, 14, 24, 195))
    draw.text((42, 30), title, font=title_font, fill=(255, 255, 255))
    draw.text(
        (44, 68),
        f"contact: {contact} | L phase: {lp} | R phase: {rp} | clearance {clearance:.2f} m",
        font=info_font,
        fill=(232, 238, 244),
    )
    draw.text(
        (44, 98),
        f"tau_L_hip {tau_l:+.2f} Nm | tau_R_hip {tau_r:+.2f} Nm | tau_C_eff {tau_C:.3f} Nm | E_in {energy:.2f} J",
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
    parser.add_argument("--tag", default="v13_7_smoke_compensated_mx64ar")
    parser.add_argument("--fps", type=int, default=60)
    args = parser.parse_args()

    summary_path = OUT_DIR / f"{args.tag}_summary.json"
    data_path = OUT_DIR / f"{args.tag}_data.csv"
    if not summary_path.exists():
        print(f"ERROR: {summary_path} not found. Run smoke_v13_7.py first.")
        sys.exit(1)

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    base = PassiveArmsParams(**summary["params"])
    motor_preset = summary.get("v13_7_motor", {}).get("hip", {}).get("name", "MX-64AR")
    motor_key = "mx64ar"
    for k, v in PRESETS.items():
        if v.name == motor_preset:
            motor_key = k
            break
    motor = PRESETS[motor_key]
    compensate = summary.get("compensate_friction", True)
    params = V137Params(
        base=base,
        fsm=make_v137_fsm(base),
        hip_motor=motor,
        knee_motor=motor,
        compensate_friction=compensate,
    )
    write_model_v137(params)

    data = load_rows(data_path)
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
