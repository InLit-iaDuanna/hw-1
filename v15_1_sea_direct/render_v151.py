"""V15.1 offline MP4 renderer：可视化 SEA direct-drive 步态。"""

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
sys.path.insert(0, str(HW1_ROOT))

from simulate_v151 import (  # noqa: E402
    QPOS_KEYS_V151,
)

FONT = Path("C:/Windows/Fonts/msyh.ttc")


def load_rows(path: Path):
    with path.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    numeric = [
        "time",
        *QPOS_KEYS_V151,
        "left_contact",
        "right_contact",
        "hip_clearance",
        "input_energy",
        "q_link_left_deg",
        "q_link_right_deg",
        "spring_PE_link_J",
    ]
    out = {}
    for key in numeric:
        out[key] = np.array([float(row.get(key, 0.0) or 0.0) for row in rows])
    out["left_phase"] = [row.get("left_phase", "") for row in rows]
    out["right_phase"] = [row.get("right_phase", "") for row in rows]
    return out


def qpos_at(t: float, data, nq: int) -> list[float]:
    t = min(max(t, 0.0), float(data["time"][-1]))
    return [float(np.interp(t, data["time"], data[key])) for key in QPOS_KEYS_V151]


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
    q_link_l = float(np.interp(t, data["time"], data["q_link_left_deg"]))
    q_link_r = float(np.interp(t, data["time"], data["q_link_right_deg"]))
    spring_pe = float(np.interp(t, data["time"], data["spring_PE_link_J"]))
    lp, rp = phase_at(t, data)

    k_sea = summary.get("k_sea", summary.get("v151_extra", {}).get("k_sea", 0.0))

    draw.rectangle((24, 22, 1250, 196), fill=(8, 14, 24, 195))
    draw.text(
        (42, 30),
        f"V15.1 SEA Direct-Drive | k_sea={k_sea:.0f} N*m/rad",
        font=title_font,
        fill=(255, 255, 255),
    )
    draw.text(
        (44, 68),
        f"contact: {contact} | L phase: {lp} | R phase: {rp} | clearance {clearance:.2f} m",
        font=info_font,
        fill=(232, 238, 244),
    )
    draw.text(
        (44, 100),
        f"spring defl L:{q_link_l:+.2f} R:{q_link_r:+.2f} deg | PE {spring_pe:.3f} J | E_in {energy:.1f} J",
        font=info_font,
        fill=(172, 255, 191),
    )
    draw.text(
        (44, 132),
        f"alt_td {summary.get('alternating_touchdowns', '?')} | "
        f"fwd {summary.get('forward_distance', 0):.2f} m | {summary.get('failure', '?')}",
        font=info_font,
        fill=(255, 220, 160),
    )
    return np.array(image)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default="v151_smoke_k00500")
    parser.add_argument("--fps", type=int, default=60)
    args = parser.parse_args()

    summary_path = ROOT / "out" / f"{args.tag}_summary.json"
    data_path = ROOT / "out" / f"{args.tag}_data.csv"
    if not summary_path.exists():
        print(f"ERROR: {summary_path} not found.")
        sys.exit(1)
    if not data_path.exists():
        print(f"ERROR: {data_path} not found.")
        sys.exit(1)

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    data = load_rows(data_path)

    model = mujoco.MjModel.from_xml_path(
        str(ROOT / "out" / "v151_models" / "sea_direct_walker.xml")
    )
    sim = mujoco.MjData(model)
    renderer = mujoco.Renderer(model, height=720, width=1280)
    camera = mujoco.MjvCamera()
    camera.distance = 3.4
    camera.azimuth = 66
    camera.elevation = -18

    duration = max(float(data["time"][-1]), 1.0 / max(1, args.fps))
    frame_count = max(1, int(duration * args.fps))
    out_path = ROOT / "out" / f"{args.tag}.mp4"
    preview_frame = None

    with imageio.get_writer(out_path, fps=args.fps) as writer:
        for idx in range(frame_count):
            t = idx / args.fps
            sim.qpos[:] = qpos_at(t, data, model.nq)
            sim.qvel[:] = 0.0
            mujoco.mj_forward(model, sim)
            camera.lookat[:] = [float(sim.qpos[0]) + 0.25, 0.0, 0.55]
            renderer.update_scene(sim, camera=camera)
            frame = annotate(renderer.render(), t, data, summary)
            writer.append_data(frame)
            if idx == min(frame_count - 1, 120):
                preview_frame = frame

    if preview_frame is not None:
        imageio.imwrite(ROOT / "out" / f"{args.tag}_preview.png", preview_frame)
    print(f"Rendered: {out_path}")


if __name__ == "__main__":
    main()
