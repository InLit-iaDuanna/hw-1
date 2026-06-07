"""V14 离线渲染 mp4（标注摆臂相位、CoT、能量）。"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import imageio.v2 as imageio
import mujoco
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from simulate_passive_arms_v14 import (
    MODEL_PATH,
    OUT_DIR,
    QPOS_KEYS,
    PassiveArmsParams,
    write_model,
)

FONT = Path("C:/Windows/Fonts/msyh.ttc")
PREFIX = "v14_baseline"


def load_rows(path: Path):
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


def qpos_at(t: float, data) -> list[float]:
    t = min(max(t, 0.0), float(data["time"][-1]))
    return [float(np.interp(t, data["time"], data[k])) for k in QPOS_KEYS]


def annotate(frame, t, data, summary, params):
    img = Image.fromarray(frame)
    draw = ImageDraw.Draw(img, "RGBA")
    title = ImageFont.truetype(str(FONT), 30)
    font = ImageFont.truetype(str(FONT), 20)
    left = int(round(float(np.interp(t, data["time"], data["left_contact"]))))
    right = int(round(float(np.interp(t, data["time"], data["right_contact"]))))
    contact = (
        "左脚"
        if left and not right
        else "右脚" if right and not left else "双脚" if left and right else "腾空"
    )
    clr = float(np.interp(t, data["time"], data["hip_clearance"]))
    e = float(np.interp(t, data["time"], data["input_energy"]))
    la = np.degrees(float(np.interp(t, data["time"], data["left_arm"])))
    ra = np.degrees(float(np.interp(t, data["time"], data["right_arm"])))
    draw.rectangle((24, 22, 1080, 168), fill=(8, 14, 24, 188))
    draw.text(
        (42, 32),
        "V14 被动摆臂版（hip+knee 主动 / 摆臂被动）",
        font=title,
        fill=(255, 255, 255),
    )
    draw.text(
        (44, 78),
        f"接触：{contact} | 髋部高度 {clr:.2f} m | 输入能量 {e:.2f} J | 交替触地 {summary['alternating_touchdowns']} 次",
        font=font,
        fill=(232, 238, 244),
    )
    draw.text(
        (44, 108),
        f"左臂 {la:+.1f}° | 右臂 {ra:+.1f}° | 摆臂质量 {params['arm_mass']:.2f} kg | 长度 {params['arm_length']:.2f} m | 阻尼 {params['arm_damping']:.3f}",
        font=font,
        fill=(172, 255, 191),
    )
    draw.text(
        (44, 138),
        f"控制律继承 V10 hip_kp={params['hip_kp']} hip_kd={params['hip_kd']}（V13 标记为孤立点解，本版机构扰动测试）",
        font=font,
        fill=(255, 220, 160),
    )
    return np.array(img)


def main() -> None:
    summary = json.loads(
        (OUT_DIR / f"{PREFIX}_summary.json").read_text(encoding="utf-8")
    )
    params = PassiveArmsParams(**summary["params"])
    write_model(params)
    data = load_rows(OUT_DIR / f"{PREFIX}_data.csv")
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    sim = mujoco.MjData(model)
    renderer = mujoco.Renderer(model, height=720, width=1280)
    cam = mujoco.MjvCamera()
    cam.distance = 3.4
    cam.azimuth = 66
    cam.elevation = -18
    fps = 60
    duration = float(data["time"][-1])
    frames = []
    for idx in range(max(1, int(duration * fps))):
        t = idx / fps
        sim.qpos[:] = qpos_at(t, data)
        sim.qvel[:] = 0.0
        mujoco.mj_forward(model, sim)
        cam.lookat[:] = [float(sim.qpos[0]) + 0.25, 0.0, 0.55]
        renderer.update_scene(sim, camera=cam)
        frames.append(annotate(renderer.render(), t, data, summary, summary["params"]))
    out = OUT_DIR / f"{PREFIX}.mp4"
    imageio.mimsave(out, frames, fps=fps)
    imageio.imwrite(
        OUT_DIR / f"{PREFIX}_preview.png", frames[min(len(frames) - 1, 120)]
    )
    print(out)


if __name__ == "__main__":
    main()
