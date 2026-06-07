"""V11 离线渲染 MP4：在已录数据上叠加扰动场景信息。"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path

import imageio.v2 as imageio
import mujoco
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from simulate_rugged_gait_v11 import (
    MODEL_PATH,
    OUT_DIR,
    RuggedScenario,
    load_v10_best_params,
    run_rugged_simulation,
    write_model_rugged,
)

from common import terrain
from v10_rolling_foot_biomimetic_gait.simulate_rolling_foot_gait_v10 import (
    QPOS_KEYS,
    RollingFootParams,
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
    return {key: np.array([float(row[key]) for row in rows]) for key in keys}


def qpos_at(t, data):
    t = min(max(t, 0.0), float(data["time"][-1]))
    return [float(np.interp(t, data["time"], data[key])) for key in QPOS_KEYS]


def annotate(frame, t, data, summary):
    image = Image.fromarray(frame)
    draw = ImageDraw.Draw(image, "RGBA")
    title_font = ImageFont.truetype(str(FONT), 28)
    font = ImageFont.truetype(str(FONT), 19)
    sc = summary["scenario"]
    amp = sc["terrain_amplitude_m"] * 1000.0
    imp = sc["impulse_force_n"]
    clearance = float(np.interp(t, data["time"], data["hip_clearance"]))
    energy = float(np.interp(t, data["time"], data["input_energy"]))
    impulse_active = (
        sc["impulse_t_s"] <= t < (sc["impulse_t_s"] + sc["impulse_duration_s"])
    )
    draw.rectangle((24, 22, 1080, 168), fill=(8, 14, 24, 188))
    draw.text(
        (42, 32),
        "V11 鲁棒性 / 崎岖地形 + 外力脉冲",
        font=title_font,
        fill=(255, 255, 255),
    )
    draw.text(
        (44, 76),
        f"地形振幅 {amp:.1f} mm | 脉冲 {imp:.0f} N @ {sc['impulse_t_s']:.1f}s | 髋部 {clearance:.2f} m | 输入能量 {energy:.2f} J",
        font=font,
        fill=(232, 238, 244),
    )
    status = summary["failure"]
    color = (172, 255, 191) if status == "completed" else (255, 170, 170)
    draw.text(
        (44, 108),
        f"触地 {summary['alternating_touchdowns']} 次 | 前进 {summary['forward_distance']:.2f} m | 结局：{status}",
        font=font,
        fill=color,
    )
    if impulse_active:
        draw.text((44, 138), "⚡ 外力脉冲施加中", font=font, fill=(255, 220, 100))
    return np.array(image)


def main(prefix: str = "v11_single") -> None:
    summary_path = OUT_DIR / f"{prefix}_summary.json"
    data_path = OUT_DIR / f"{prefix}_data.csv"
    if not summary_path.exists() or not data_path.exists():
        print(
            f"[render] 未找到 {summary_path.name}，自动跑一次默认场景生成 prefix={prefix} ..."
        )
        params = load_v10_best_params()
        params = params.__class__(**{**asdict(params), "duration": 12.0})
        scenario = RuggedScenario(
            terrain_amplitude_m=0.020,
            terrain_seed=1,
            impulse_force_n=30.0,
            impulse_t_s=4.0,
            impulse_duration_s=0.05,
        )
        run_rugged_simulation(params, scenario, save_prefix=prefix)

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    params = RollingFootParams(**summary["params"])
    scenario_raw = summary["scenario"]
    scenario_raw["impulse_dir"] = tuple(scenario_raw["impulse_dir"])
    scenario = RuggedScenario(**scenario_raw)
    write_model_rugged(params, scenario)
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    if scenario.terrain_amplitude_m > 0.0:
        profile = terrain.generate_profile(
            scenario.terrain_amplitude_m,
            scenario.terrain_wavelength_m,
            length_m=90.0,
            seed=scenario.terrain_seed,
        )
        terrain.fill_hfield_data(model, profile)

    sim_data = mujoco.MjData(model)
    data = load_rows(OUT_DIR / f"{prefix}_data.csv")
    renderer = mujoco.Renderer(model, height=720, width=1280)
    camera = mujoco.MjvCamera()
    camera.distance = 3.4
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
    out = OUT_DIR / f"{prefix}_rugged_walk.mp4"
    imageio.mimsave(out, frames, fps=fps)
    imageio.imwrite(
        OUT_DIR / f"{prefix}_rugged_walk_preview.png", frames[min(len(frames) - 1, 120)]
    )
    print(out)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--prefix", default="v11_single")
    args = parser.parse_args()
    main(args.prefix)
