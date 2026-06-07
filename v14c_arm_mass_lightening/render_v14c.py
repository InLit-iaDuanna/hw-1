"""Offline MP4 renderer for V14c simulation outputs."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import imageio.v2 as imageio
import mujoco
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from simulate_v14c import MODEL_PATH, OUT_DIR, QPOS_KEYS, PassiveArmsParams, write_model

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
    out = {}
    for key in numeric:
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
    title = _font(28)
    font = _font(20)
    left = int(round(float(np.interp(t, data["time"], data["left_contact"]))))
    right = int(round(float(np.interp(t, data["time"], data["right_contact"]))))
    contact = (
        "left"
        if left and not right
        else "right" if right and not left else "double" if left and right else "flight"
    )
    clearance = float(np.interp(t, data["time"], data["hip_clearance"]))
    energy = float(np.interp(t, data["time"], data["input_energy"]))
    arm_l = np.degrees(float(np.interp(t, data["time"], data["left_arm"])))
    arm_r = np.degrees(float(np.interp(t, data["time"], data["right_arm"])))
    lp, rp = phase_at(t, data)
    params = summary["params"]

    draw.rectangle((24, 22, 1210, 176), fill=(8, 14, 24, 195))
    draw.text(
        (42, 30),
        "V14c = lightened passive arms + V13.6.1 best FSM hip",
        font=title,
        fill=(255, 255, 255),
    )
    draw.text(
        (44, 72),
        f"contact: {contact} | left phase: {lp} | right phase: {rp} | hip clearance {clearance:.2f} m",
        font=font,
        fill=(232, 238, 244),
    )
    draw.text(
        (44, 104),
        f"input energy {energy:.2f} J | alt touchdowns {summary['alternating_touchdowns']} | success {summary['success']}",
        font=font,
        fill=(172, 255, 191),
    )
    draw.text(
        (44, 136),
        f"hip+knee active, arms passive | left arm {arm_l:+.1f} deg | right arm {arm_r:+.1f} deg | mass {params['arm_mass']:.3f} kg | length {params['arm_length']:.2f} m",
        font=font,
        fill=(255, 220, 160),
    )
    return np.array(image)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default="v14c_baseline")
    parser.add_argument("--fps", type=int, default=60)
    args = parser.parse_args()

    summary = json.loads(
        (OUT_DIR / f"{args.tag}_summary.json").read_text(encoding="utf-8")
    )
    params = PassiveArmsParams(**summary["params"])
    write_model(params)
    data = load_rows(OUT_DIR / f"{args.tag}_data.csv")
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    sim = mujoco.MjData(model)
    renderer = mujoco.Renderer(model, height=720, width=1280)
    camera = mujoco.MjvCamera()
    camera.distance = 3.4
    camera.azimuth = 66
    camera.elevation = -18
    duration = max(float(data["time"][-1]), 1.0 / max(1, args.fps))
    frame_count = max(1, int(duration * args.fps))
    out = OUT_DIR / f"{args.tag}.mp4"
    preview_frame = None
    with imageio.get_writer(out, fps=args.fps) as writer:
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
    print(out)


if __name__ == "__main__":
    main()
