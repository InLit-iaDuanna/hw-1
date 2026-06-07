"""V13.6 离线渲染（mp4），在每帧叠加当前 phase 标注。

依赖 imageio + Pillow（已在主项目 requirements 中）。
读取 out/v13_6_baseline_data.csv + _summary.json。
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import imageio.v2 as imageio
import mujoco
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
V10_DIR = ROOT.parent / "v10_rolling_foot_biomimetic_gait"
sys.path.insert(0, str(V10_DIR))
sys.path.insert(0, str(ROOT))

from simulate_rolling_foot_gait_v10 import (
    MODEL_PATH,
    QPOS_KEYS,
    RollingFootParams,
    write_model,
)  # noqa: E402

OUT_DIR = ROOT / "out"
FONT = Path("C:/Windows/Fonts/msyh.ttc")

PHASE_CN = {
    "stance_early": "支撑期早段",
    "stance_late": "支撑期晚段(push-off 准备)",
    "swing_thrust": "摆动期推力段(能量注入)",
    "swing_retract": "摆动期收回段(被动)",
}


def load_rows(path: Path):
    with path.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    # 数值列
    nkeys = [
        "time",
        *QPOS_KEYS,
        "hip_clearance",
        "input_energy",
        "E_current",
        "e_E_swing",
        "A_swing",
    ]
    out = {}
    for k in nkeys:
        out[k] = np.array([float(r[k]) for r in rows])
    out["left_phase"] = [r["left_phase"] for r in rows]
    out["right_phase"] = [r["right_phase"] for r in rows]
    return out


def qpos_at(t: float, data) -> list[float]:
    t = min(max(t, 0.0), float(data["time"][-1]))
    return [float(np.interp(t, data["time"], data[key])) for key in QPOS_KEYS]


def phase_at(t: float, data) -> tuple[str, str]:
    idx = int(np.argmin(np.abs(data["time"] - t)))
    return data["left_phase"][idx], data["right_phase"][idx]


def annotate(frame: np.ndarray, t: float, data, summary: dict) -> np.ndarray:
    image = Image.fromarray(frame)
    draw = ImageDraw.Draw(image, "RGBA")
    title_font = ImageFont.truetype(str(FONT), 28)
    font = ImageFont.truetype(str(FONT), 20)
    lp, rp = phase_at(t, data)
    clearance = float(np.interp(t, data["time"], data["hip_clearance"]))
    E_cur = float(np.interp(t, data["time"], data["E_current"]))
    A_sw = float(np.interp(t, data["time"], data["A_swing"]))
    draw.rectangle((24, 22, 1180, 174), fill=(8, 14, 24, 200))
    draw.text(
        (42, 30), "V13.6 事件驱动 FSM hip 控制律", font=title_font, fill=(255, 255, 255)
    )
    draw.text(
        (44, 72),
        f"左腿 phase: {PHASE_CN.get(lp, lp)}  |  右腿 phase: {PHASE_CN.get(rp, rp)}",
        font=font,
        fill=(232, 238, 244),
    )
    draw.text(
        (44, 102),
        f"E = {E_cur:5.2f} J (target 52.66)  |  swing 推力幅 A = {A_sw:4.2f} Nm  |  髋高 {clearance:.2f} m",
        font=font,
        fill=(172, 255, 191),
    )
    draw.text(
        (44, 132),
        "康复对位: stance_early=Loading/Mid-Stance, stance_late=Pre-Swing, swing_thrust=Initial Swing, swing_retract=Terminal Swing",
        font=font,
        fill=(200, 220, 240),
    )
    return np.array(image)


def main() -> None:
    summary = json.loads(
        (OUT_DIR / "v13_6_baseline_summary.json").read_text(encoding="utf-8")
    )
    params = RollingFootParams(**summary["params"])
    write_model(params)
    data = load_rows(OUT_DIR / "v13_6_baseline_data.csv")
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    sim_data = mujoco.MjData(model)
    renderer = mujoco.Renderer(model, height=720, width=1280)
    camera = mujoco.MjvCamera()
    camera.distance = 3.2
    camera.azimuth = 66
    camera.elevation = -18
    fps = 60
    duration = float(data["time"][-1])
    frames = []
    for idx in range(max(1, int(duration * fps))):
        t = idx / fps
        sim_data.qpos[:] = qpos_at(t, data)
        sim_data.qvel[:] = 0.0
        mujoco.mj_forward(model, sim_data)
        camera.lookat[:] = [float(sim_data.qpos[0]) + 0.25, 0.0, 0.55]
        renderer.update_scene(sim_data, camera=camera)
        frames.append(annotate(renderer.render(), t, data, summary))
    out = OUT_DIR / "v13_6_baseline_walk.mp4"
    imageio.mimsave(out, frames, fps=fps)
    imageio.imwrite(
        OUT_DIR / "v13_6_baseline_preview.png", frames[min(len(frames) - 1, 120)]
    )
    print(out)


if __name__ == "__main__":
    main()
