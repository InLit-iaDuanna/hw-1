from __future__ import annotations

import csv
import json
from pathlib import Path

import imageio.v2 as imageio
import mujoco
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from simulate_rolling_foot_gait_v10 import (
    MODEL_PATH,
    OUT_DIR,
    QPOS_KEYS,
    RollingFootParams,
    write_model,
)

FONT = Path("C:/Windows/Fonts/msyh.ttc")


def load_rows(path: Path) -> dict[str, np.ndarray]:
    with path.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    keys = [
        "time",
        *QPOS_KEYS,
        "left_contact",
        "right_contact",
        "left_heel_contact",
        "left_sole_contact",
        "left_toe_contact",
        "right_heel_contact",
        "right_sole_contact",
        "right_toe_contact",
        "hip_clearance",
        "input_energy",
    ]
    return {key: np.array([float(row[key]) for row in rows]) for key in keys}


def qpos_at(t: float, data: dict[str, np.ndarray]) -> list[float]:
    t = min(max(t, 0.0), float(data["time"][-1]))
    return [float(np.interp(t, data["time"], data[key])) for key in QPOS_KEYS]


def phase_text(t: float, data: dict[str, np.ndarray]) -> str:
    heel = int(
        round(float(np.interp(t, data["time"], data["left_heel_contact"])))
    ) or int(round(float(np.interp(t, data["time"], data["right_heel_contact"]))))
    sole = int(
        round(float(np.interp(t, data["time"], data["left_sole_contact"])))
    ) or int(round(float(np.interp(t, data["time"], data["right_sole_contact"]))))
    toe = int(
        round(float(np.interp(t, data["time"], data["left_toe_contact"])))
    ) or int(round(float(np.interp(t, data["time"], data["right_toe_contact"]))))
    if heel and not toe:
        return "脚跟接触"
    if sole and toe:
        return "足底滚动"
    if toe:
        return "脚趾离地"
    return "摆动离地"


def annotate(
    frame: np.ndarray, t: float, data: dict[str, np.ndarray], summary: dict
) -> np.ndarray:
    image = Image.fromarray(frame)
    draw = ImageDraw.Draw(image, "RGBA")
    title_font = ImageFont.truetype(str(FONT), 30)
    font = ImageFont.truetype(str(FONT), 20)
    left = int(round(float(np.interp(t, data["time"], data["left_contact"]))))
    right = int(round(float(np.interp(t, data["time"], data["right_contact"]))))
    contact = (
        "左脚"
        if left and not right
        else "右脚" if right and not left else "双脚" if left and right else "无接触"
    )
    clearance = float(np.interp(t, data["time"], data["hip_clearance"]))
    energy = float(np.interp(t, data["time"], data["input_energy"]))
    draw.rectangle((24, 22, 1040, 154), fill=(8, 14, 24, 188))
    draw.text((42, 34), "V10 足踝滚动仿生步态版", font=title_font, fill=(255, 255, 255))
    draw.text(
        (44, 82),
        f"真实 MuJoCo 接触 | 当前接触：{contact} | 足部相位：{phase_text(t, data)} | 髋部高度：{clearance:.2f} m",
        font=font,
        fill=(232, 238, 244),
    )
    draw.text(
        (44, 116),
        f"髋膝主动稳定 + 踝部被动弹簧阻尼 | 输入能量：{energy:.2f} J | 交替触地：{summary['alternating_touchdowns']} 次",
        font=font,
        fill=(172, 255, 191),
    )
    return np.array(image)


def main() -> None:
    summary = json.loads((OUT_DIR / "v10_best_params.json").read_text(encoding="utf-8"))
    params = RollingFootParams(**summary["params"])
    write_model(params)
    data = load_rows(OUT_DIR / "v10_rolling_foot_walk_data.csv")
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
    out = OUT_DIR / "v10_rolling_foot_walk.mp4"
    imageio.mimsave(out, frames, fps=fps)
    imageio.imwrite(
        OUT_DIR / "v10_rolling_foot_walk_preview.png", frames[min(len(frames) - 1, 120)]
    )
    print(out)


if __name__ == "__main__":
    main()
