from __future__ import annotations

import csv
from pathlib import Path

import imageio.v2 as imageio
import mujoco
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from simulate_contact_gait_v7 import MODEL_PATH, OUT_DIR, QPOS_KEYS

FONT = Path("C:/Windows/Fonts/msyh.ttc")


def load_rows(path: Path) -> dict[str, np.ndarray]:
    with path.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    keys = ["time", *QPOS_KEYS, "left_contact", "right_contact", "hip_clearance"]
    data = {key: np.array([float(row[key]) for row in rows]) for key in keys}
    return data


def qpos_at(t: float, data: dict[str, np.ndarray]) -> list[float]:
    t = min(max(t, 0.0), float(data["time"][-1]))
    return [float(np.interp(t, data["time"], data[key])) for key in QPOS_KEYS]


def annotate(frame: np.ndarray, t: float, data: dict[str, np.ndarray]) -> np.ndarray:
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
    draw.rectangle((24, 22, 760, 132), fill=(8, 14, 24, 178))
    draw.text(
        (42, 34), "V7 真实 MuJoCo 接触探索版", font=title_font, fill=(255, 255, 255)
    )
    draw.text(
        (44, 82),
        f"无驱动自由动力学 | 当前接触：{contact} | 髋部离坡面：{clearance:.2f} m",
        font=font,
        fill=(230, 236, 240),
    )
    draw.text(
        (44, 108),
        "说明：这是接触探索，不替代 V5 的 Poincare 极限环证明",
        font=font,
        fill=(230, 236, 240),
    )
    return np.array(image)


def main() -> None:
    data = load_rows(OUT_DIR / "v7_best_attempt_data.csv")
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    sim_data = mujoco.MjData(model)
    width, height, fps = 1280, 720, 60
    renderer = mujoco.Renderer(model, height=height, width=width)
    camera = mujoco.MjvCamera()
    camera.type = mujoco.mjtCamera.mjCAMERA_FREE
    camera.distance = 3.1
    camera.azimuth = 66
    camera.elevation = -18

    duration = float(data["time"][-1])
    frames = []
    for idx in range(max(1, int(duration * fps))):
        t = idx / fps
        sim_data.qpos[:] = qpos_at(t, data)
        sim_data.qvel[:] = 0.0
        mujoco.mj_forward(model, sim_data)
        camera.lookat[:] = [float(sim_data.qpos[0]) + 0.2, 0.0, 0.50]
        renderer.update_scene(sim_data, camera=camera)
        frames.append(annotate(renderer.render(), t, data))

    out = OUT_DIR / "v7_best_attempt.mp4"
    imageio.mimsave(out, frames, fps=fps)
    imageio.imwrite(
        OUT_DIR / "v7_best_attempt_preview.png", frames[min(len(frames) - 1, 60)]
    )
    print(out)


if __name__ == "__main__":
    main()
