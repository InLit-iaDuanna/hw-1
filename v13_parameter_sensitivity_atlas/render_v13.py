"""V13 渲染 MP4：把 replay_cell_v13.py 的 CSV + summary 渲染成带标注的 MP4。

用法：
  python render_v13.py --tag v13_baseline
  python render_v13.py --tag v13_C_foot_leg_3_3 --label "C(3,3) foot=0.042 leg=1.02"
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import fields
from pathlib import Path

import imageio.v2 as imageio
import mujoco
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
V10_DIR = ROOT.parent / "v10_rolling_foot_biomimetic_gait"
sys.path.insert(0, str(V10_DIR))

from simulate_rolling_foot_gait_v10 import (
    MODEL_PATH,
    QPOS_KEYS,
    RollingFootParams,
    write_model,
)  # noqa: E402

OUT_DIR = ROOT / "out"
FONT = Path("C:/Windows/Fonts/msyh.ttc")


def load_rows(tag: str):
    path = OUT_DIR / f"{tag}_data.csv"
    if not path.exists():
        raise SystemExit(f"{path} not found — run replay_cell_v13.py first")
    with path.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    keys = [
        "time",
        *QPOS_KEYS,
        "left_contact",
        "right_contact",
        "hip_clearance",
        "input_energy",
    ]
    return {k: np.array([float(r[k]) for r in rows]) for k in keys}


def load_summary(tag: str) -> dict:
    return json.loads((OUT_DIR / f"{tag}_summary.json").read_text(encoding="utf-8"))


def qpos_at(t: float, data) -> list[float]:
    t = min(max(t, 0.0), float(data["time"][-1]))
    return [float(np.interp(t, data["time"], data[k])) for k in QPOS_KEYS]


def annotate(frame, t, data, summary, label: str) -> np.ndarray:
    img = Image.fromarray(frame)
    draw = ImageDraw.Draw(img, "RGBA")
    title_font = ImageFont.truetype(str(FONT), 28)
    font = ImageFont.truetype(str(FONT), 18)
    p = summary["params"]
    left = int(round(float(np.interp(t, data["time"], data["left_contact"]))))
    right = int(round(float(np.interp(t, data["time"], data["right_contact"]))))
    contact = (
        "左"
        if left and not right
        else "右" if right and not left else "双" if left and right else "无"
    )
    clearance = float(np.interp(t, data["time"], data["hip_clearance"]))
    energy = float(np.interp(t, data["time"], data["input_energy"]))
    ok = "✓ success" if summary["success"] else f"✗ {summary['failure']}"
    color = (172, 255, 191) if summary["success"] else (255, 172, 172)
    draw.rectangle((20, 18, 1100, 168), fill=(8, 14, 24, 200))
    draw.text(
        (36, 28), f"V13 atlas replay — {label}", font=title_font, fill=(255, 255, 255)
    )
    draw.text(
        (38, 70),
        f"slope={p['slope_deg']:.2f}°  foot_r={p['foot_radius']:.3f}m  thigh={p['thigh_length']:.2f}m  "
        f"kp={p['hip_kp']:.1f} kd={p['hip_kd']:.2f}  τ={p.get('torso_mass', 0):.3f}kg",
        font=font,
        fill=(232, 238, 244),
    )
    draw.text(
        (38, 100),
        f"t={t:5.2f}s  接触={contact}  髋高={clearance:.2f}m  输入能={energy:.2f}J  触地数={summary['alternating_touchdowns']}",
        font=font,
        fill=(232, 238, 244),
    )
    draw.text((38, 130), ok, font=font, fill=color)
    return np.array(img)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", required=True)
    parser.add_argument("--label", default=None, help="标题副标题；默认就是 tag")
    parser.add_argument("--fps", type=int, default=60)
    args = parser.parse_args()

    summary = load_summary(args.tag)
    valid = {f.name for f in fields(RollingFootParams)}
    params = RollingFootParams(
        **{k: v for k, v in summary["params"].items() if k in valid}
    )
    write_model(params)

    data = load_rows(args.tag)
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    sim = mujoco.MjData(model)
    renderer = mujoco.Renderer(model, height=720, width=1280)
    camera = mujoco.MjvCamera()
    camera.distance = 3.2
    camera.azimuth = 66
    camera.elevation = -18

    duration = float(data["time"][-1])
    label = args.label or args.tag
    frames = []
    n = max(1, int(duration * args.fps))
    for idx in range(n):
        t = idx / args.fps
        sim.qpos[:] = qpos_at(t, data)
        sim.qvel[:] = 0.0
        mujoco.mj_forward(model, sim)
        camera.lookat[:] = [float(sim.qpos[0]) + 0.25, 0.0, 0.55]
        renderer.update_scene(sim, camera=camera)
        frames.append(annotate(renderer.render(), t, data, summary, label))

    out = OUT_DIR / f"{args.tag}.mp4"
    imageio.mimsave(out, frames, fps=args.fps)
    preview = OUT_DIR / f"{args.tag}_preview.png"
    imageio.imwrite(preview, frames[min(len(frames) - 1, 120)])
    print(f"-> {out}")
    print(f"-> {preview}")


if __name__ == "__main__":
    main()
