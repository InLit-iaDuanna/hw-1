"""V14 摆臂质量对比渲染：左侧 arm_mass=0.001（成功）vs 右侧 arm_mass=0.1（失败）。"""

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
    if len(data["time"]) == 0:
        return [0.0] * len(QPOS_KEYS)
    t = min(max(t, 0.0), float(data["time"][-1]))
    return [float(np.interp(t, data["time"], data[k])) for k in QPOS_KEYS]


def render_frame(model, sim, renderer, cam, data, t, summary, params):
    """渲染单帧并返回 numpy 数组。"""
    sim.qpos[:] = qpos_at(t, data)
    sim.qvel[:] = 0.0
    mujoco.mj_forward(model, sim)
    cam.lookat[:] = [float(sim.qpos[0]) + 0.25, 0.0, 0.55]
    renderer.update_scene(sim, camera=cam)
    frame = renderer.render()

    # 叠加摆臂信息
    img = Image.fromarray(frame)
    draw = ImageDraw.Draw(img, "RGBA")
    font = ImageFont.truetype(str(FONT), 16)

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

    status = "✓ 成功" if summary["success"] else f"✗ {summary['failure']}"
    color = (172, 255, 191) if summary["success"] else (255, 100, 100)

    draw.rectangle((10, 10, 630, 100), fill=(8, 14, 24, 188))
    draw.text(
        (20, 15),
        f"arm_mass={params['arm_mass']:.3f} kg | {status}",
        font=font,
        fill=color,
    )
    draw.text(
        (20, 40),
        f"接触: {contact} | 髋高 {clr:.2f}m | 能量 {e:.2f}J",
        font=font,
        fill=(232, 238, 244),
    )
    draw.text(
        (20, 65),
        f"左臂 {la:+.1f}° | 右臂 {ra:+.1f}° | 触地 {summary['alternating_touchdowns']}次",
        font=font,
        fill=(232, 238, 244),
    )

    return np.array(img)


def main() -> None:
    # 加载两个案例的数据
    baseline_summary = json.loads(
        (OUT_DIR / "v14_baseline_summary.json").read_text(encoding="utf-8")
    )
    fail_summary = json.loads(
        (OUT_DIR / "v14_fail_fall_summary.json").read_text(encoding="utf-8")
    )

    baseline_params = PassiveArmsParams(**baseline_summary["params"])
    fail_params = PassiveArmsParams(**fail_summary["params"])

    baseline_data = load_rows(OUT_DIR / "v14_baseline_data.csv")
    fail_data = load_rows(OUT_DIR / "v14_fail_fall_data.csv")

    # 创建两个渲染器
    write_model(baseline_params)
    baseline_model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    baseline_sim = mujoco.MjData(baseline_model)
    baseline_renderer = mujoco.Renderer(baseline_model, height=540, width=640)

    write_model(fail_params)
    fail_model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    fail_sim = mujoco.MjData(fail_model)
    fail_renderer = mujoco.Renderer(fail_model, height=540, width=640)

    # 相机设置
    cam = mujoco.MjvCamera()
    cam.distance = 3.4
    cam.azimuth = 66
    cam.elevation = -18

    # 渲染参数
    fps = 60
    duration = min(
        float(baseline_data["time"][-1]),
        float(fail_data["time"][-1]),
    )

    frames = []
    for idx in range(max(1, int(duration * fps))):
        t = idx / fps

        # 渲染左侧（baseline）和右侧（fail）
        left_frame = render_frame(
            baseline_model,
            baseline_sim,
            baseline_renderer,
            cam,
            baseline_data,
            t,
            baseline_summary,
            baseline_summary["params"],
        )
        right_frame = render_frame(
            fail_model,
            fail_sim,
            fail_renderer,
            cam,
            fail_data,
            t,
            fail_summary,
            fail_summary["params"],
        )

        # 合成左右并排图像
        combined = np.hstack([left_frame, right_frame])

        # 添加全局标题
        img = Image.fromarray(combined)
        draw = ImageDraw.Draw(img, "RGBA")
        title_font = ImageFont.truetype(str(FONT), 24)
        draw.rectangle((0, 0, 1280, 50), fill=(8, 14, 24, 220))
        draw.text(
            (20, 10),
            "V14 摆臂质量对比：arm_mass=0.001kg（左，稳定）vs arm_mass=0.1kg（右，跌倒）",
            font=title_font,
            fill=(255, 255, 255),
        )

        frames.append(np.array(img))

    out = OUT_DIR / "v14_arm_mass_comparison.mp4"
    imageio.mimsave(out, frames, fps=fps)
    print(f"已生成对比视频: {out}")


if __name__ == "__main__":
    main()
