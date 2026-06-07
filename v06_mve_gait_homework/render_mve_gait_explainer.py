from __future__ import annotations

import csv
from pathlib import Path

import imageio.v2 as imageio
import mujoco
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from simulate_mve_gait_v6 import MODEL_PATH, OUT_DIR

QPOS_KEYS = ["hip_x", "hip_z", "left_thigh", "left_knee", "right_thigh", "right_knee"]
FONT = Path("C:/Windows/Fonts/msyh.ttc")


def load_csv(path: Path) -> dict[str, np.ndarray]:
    with path.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    data: dict[str, list[float] | list[str]] = {"time": []}
    for key in QPOS_KEYS + ["phase", "swing_clearance", "poincare_error"]:
        data[key] = []
    data["phase_label"] = []
    data["support"] = []
    for row in rows:
        for key in QPOS_KEYS + ["time", "phase", "swing_clearance", "poincare_error"]:
            data[key].append(float(row[key]))  # type: ignore[index]
        data["phase_label"].append(row["phase_label"])  # type: ignore[index]
        data["support"].append(row["support"])  # type: ignore[index]
    return {key: np.array(value) for key, value in data.items()}


def interp_text(t: float, data: dict[str, np.ndarray], key: str) -> str:
    idx = int(np.searchsorted(data["time"], t, side="right") - 1)
    idx = max(0, min(idx, len(data["time"]) - 1))
    return str(data[key][idx])


def qpos_at(t: float, data: dict[str, np.ndarray]) -> list[float]:
    duration = float(data["time"][-1])
    t = min(max(t, 0.0), duration)
    return [float(np.interp(t, data["time"], data[key])) for key in QPOS_KEYS]


def number_at(t: float, data: dict[str, np.ndarray], key: str) -> float:
    return float(np.interp(t, data["time"], data[key]))


def draw_badge(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int],
) -> None:
    x, y = xy
    box = draw.textbbox((x, y), text, font=font)
    pad_x, pad_y = 14, 8
    rect = (box[0] - pad_x, box[1] - pad_y, box[2] + pad_x, box[3] + pad_y)
    draw.rounded_rectangle(rect, radius=7, fill=fill)
    draw.text((x, y), text, font=font, fill=(255, 255, 255))


def annotate(frame: np.ndarray, t: float, data: dict[str, np.ndarray]) -> np.ndarray:
    image = Image.fromarray(frame)
    draw = ImageDraw.Draw(image, "RGBA")
    title_font = ImageFont.truetype(str(FONT), 30)
    font = ImageFont.truetype(str(FONT), 22)
    small = ImageFont.truetype(str(FONT), 18)

    label = interp_text(t, data, "phase_label")
    support = "左腿" if interp_text(t, data, "support") == "left" else "右腿"
    clearance = number_at(t, data, "swing_clearance")
    err = number_at(t, data, "poincare_error")

    draw.rectangle((24, 22, 642, 152), fill=(8, 14, 24, 178))
    draw.text(
        (42, 34),
        "V6 被动极限环步态：仿生 MVE 展示层",
        font=title_font,
        fill=(255, 255, 255),
    )
    draw.text(
        (44, 82),
        "证明来自 V5 Poincare 收敛；MuJoCo 仅做无驱动结构回放",
        font=small,
        fill=(224, 232, 236),
    )
    draw.text(
        (44, 112),
        f"支撑脚锁定：{support}    摆动脚离地：{clearance:.2f} m    截面误差：{err:.3f}",
        font=small,
        fill=(224, 232, 236),
    )

    draw_badge(draw, (34, 632), "支撑脚锁定", font, (28, 88, 98, 218))
    draw_badge(draw, (220, 632), label, font, (178, 70, 46, 218))
    draw_badge(draw, (502, 632), "触地换腿后进入下一周期", font, (88, 76, 110, 218))
    return np.array(image)


def main() -> None:
    data = load_csv(OUT_DIR / "v6_mve_gait_data.csv")
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    sim_data = mujoco.MjData(model)

    width, height, fps = 1280, 720, 60
    renderer = mujoco.Renderer(model, height=height, width=width)
    camera = mujoco.MjvCamera()
    camera.type = mujoco.mjtCamera.mjCAMERA_FREE
    camera.distance = 3.0
    camera.azimuth = 66
    camera.elevation = -18

    duration = float(data["time"][-1])
    frames = []
    for frame_idx in range(int(duration * fps)):
        t = frame_idx / fps
        sim_data.qpos[:] = qpos_at(t, data)
        sim_data.qvel[:] = 0.0
        mujoco.mj_forward(model, sim_data)
        camera.lookat[:] = [float(sim_data.qpos[0]) + 0.20, 0.0, 0.50]
        renderer.update_scene(sim_data, camera=camera)
        frame = annotate(renderer.render(), t, data)
        frames.append(frame)

    out = OUT_DIR / "v6_mve_gait_explainer.mp4"
    imageio.mimsave(out, frames, fps=fps)
    imageio.imwrite(
        OUT_DIR / "v6_mve_gait_preview.png", frames[min(len(frames) - 1, 150)]
    )
    print(out)


if __name__ == "__main__":
    main()
