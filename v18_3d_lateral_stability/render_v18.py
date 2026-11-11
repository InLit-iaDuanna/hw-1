"""V18 offline MP4 renderer - replays simulation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import imageio.v2 as imageio
import mujoco
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from model_3d import MODEL_PATH, Lateral3DParams, write_model

from common.mujoco_utils import get_joint_address

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "out"
FONT = Path("C:/Windows/Fonts/msyh.ttc")


def _font(size: int):
    if FONT.exists():
        return ImageFont.truetype(str(FONT), size)
    return ImageFont.load_default()


class SimRecorder:
    """Records simulation state for replay."""

    def __init__(self, model, data, params):
        self.model = model
        self.data = data
        self.params = params
        self.frames_data = []

        # Get joint addresses
        self.hx_q, _ = get_joint_address(model, "hip_x")
        self.hy_q, _ = get_joint_address(model, "hip_y")
        self.hz_q, _ = get_joint_address(model, "hip_z")
        self.hr_q, _ = get_joint_address(model, "hip_roll")

    def record(
        self,
        t: float,
        left_contact: bool,
        right_contact: bool,
        support_foot: str,
        alternations: int,
    ):
        """Record current frame state."""
        self.frames_data.append(
            {
                "time": t,
                "qpos": self.data.qpos.copy(),
                "qvel": self.data.qvel.copy(),
                "hip_x": float(self.data.qpos[self.hx_q]),
                "hip_y": float(self.data.qpos[self.hy_q]),
                "hip_z": float(self.data.qpos[self.hz_q]),
                "hip_roll": float(self.data.qpos[self.hr_q]),
                "left_contact": left_contact,
                "right_contact": right_contact,
                "support_foot": support_foot,
                "alternations": alternations,
            }
        )


def run_and_record_v18(params: Lateral3DParams, target_duration: float = 8.0):
    """Run V18 simulation with recording."""
    import numpy as np

    from common.control_utils import limited_pd, ramp_height, smoothstep
    from common.mujoco_utils import get_contact_flags, get_joint_address

    write_model(params)
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    data = mujoco.MjData(model)
    recorder = SimRecorder(model, data, params)

    # Initialize (copied from simulate_v18.py)
    hx_q, hx_v = get_joint_address(model, "hip_x")
    hy_q, hy_v = get_joint_address(model, "hip_y")
    hz_q, hz_v = get_joint_address(model, "hip_z")
    hr_q, hr_v = get_joint_address(model, "hip_roll")
    lh_q, lh_v = get_joint_address(model, "left_hip")
    lk_q, lk_v = get_joint_address(model, "left_knee")
    la_q, la_v = get_joint_address(model, "left_ankle")
    rh_q, rh_v = get_joint_address(model, "right_hip")
    rk_q, rk_v = get_joint_address(model, "right_knee")
    ra_q, ra_v = get_joint_address(model, "right_ankle")
    la_abd_q, _ = get_joint_address(model, "left_hip_abd")
    ra_abd_q, _ = get_joint_address(model, "right_hip_abd")

    p = params
    u0 = smoothstep(p.release_phase)
    alpha = np.arcsin(p.step_length / (2.0 * p.leg_length))
    support_z = ramp_height(0.0, gamma=p.gamma) + p.foot_radius / max(
        0.2, np.cos(p.gamma)
    )
    left_hip_init = p.gamma + alpha - 2.0 * alpha * u0
    hip_x_init = p.leg_length * np.sin(left_hip_init)
    hip_z_init = support_z + p.leg_length * np.cos(left_hip_init)

    # Swing leg IK
    px = hip_x_init - p.swing_foot_x
    pz = hip_z_init - (support_z + p.swing_foot_clearance)
    d = np.hypot(px, pz)
    d = float(
        np.clip(d, abs(p.thigh_length - p.shank_length) + 1e-5, p.leg_length - 1e-5)
    )
    base = np.arctan2(px, pz)
    cos_delta = (p.thigh_length**2 + d**2 - p.shank_length**2) / (
        2.0 * p.thigh_length * d
    )
    delta = np.arccos(float(np.clip(cos_delta, -1.0, 1.0)))
    right_hip_init = base - delta
    thigh_angle = right_hip_init
    knee_x = hip_x_init - p.thigh_length * np.sin(thigh_angle)
    knee_z = hip_z_init - p.thigh_length * np.cos(thigh_angle)
    shank_angle = np.arctan2(
        knee_x - p.swing_foot_x, knee_z - (support_z + p.swing_foot_clearance)
    )
    right_knee_init = float(
        np.clip(shank_angle - thigh_angle, 0.0, np.radians(p.knee_limit_deg))
    )

    data.qpos[hx_q] = hip_x_init
    data.qpos[hy_q] = p.init_hip_y
    data.qpos[hz_q] = hip_z_init
    data.qpos[hr_q] = np.radians(p.init_hip_roll_deg)
    data.qpos[la_abd_q] = 0.0
    data.qpos[ra_abd_q] = 0.0
    data.qpos[lh_q] = left_hip_init
    data.qpos[lk_q] = 0.0
    data.qpos[rh_q] = right_hip_init
    data.qpos[rk_q] = right_knee_init

    data.qvel[hx_v] = p.initial_vx
    data.qvel[hz_v] = -np.tan(p.gamma) * p.initial_vx
    data.qvel[lh_v] = 0.04
    data.qvel[rh_v] = p.swing_hip_vel
    data.qvel[rk_v] = p.swing_knee_vel
    data.ctrl[:] = 0.0
    mujoco.mj_forward(model, data)

    # Simulation loop
    support_foot = "left"
    burst_start_t = -p.gait_period
    last_event_t = -1.0
    alternations = 0
    accepted_contact = ""
    candidate_start_t = {"left": None, "right": None}
    contact_reported = {"left": False, "right": False}
    start_x = float(data.qpos[hx_q])

    record_stride = max(1, int(0.016 / p.timestep))  # ~60 fps

    for step in range(int(target_duration / p.timestep)):
        t = step * p.timestep

        # V10 control
        hip_x = float(data.qpos[hx_q])
        hip_z = float(data.qpos[hz_q])
        clearance = hip_z - ramp_height(hip_x, gamma=p.gamma)
        u = min(max((t - burst_start_t) / max(p.gait_period, 1e-6), 0.0), 1.0)
        if clearance < p.recovery_clearance:
            u = min(u, 0.55)
        s = smoothstep(u)
        offset = p.gamma
        stance_target = offset + np.radians(
            p.stance_front_deg + (p.stance_back_deg - p.stance_front_deg) * s
        )
        swing_target = offset + np.radians(
            p.swing_back_deg + (p.swing_front_deg - p.swing_back_deg) * s
        )
        swing_knee = np.radians(p.swing_knee_flex_deg * np.sin(np.pi * u))
        stance_knee = np.radians(p.stance_knee_deg)

        left_is_support = support_foot == "left"
        lh_tau = limited_pd(
            float(data.qpos[lh_q]),
            float(data.qvel[lh_v]),
            stance_target if left_is_support else swing_target,
            p.hip_kp,
            p.hip_kd,
            p.hip_torque_limit,
        )
        lk_tau = limited_pd(
            float(data.qpos[lk_q]),
            float(data.qvel[lk_v]),
            stance_knee if left_is_support else swing_knee,
            p.knee_kp,
            p.knee_kd,
            p.knee_torque_limit,
        )
        rh_tau = limited_pd(
            float(data.qpos[rh_q]),
            float(data.qvel[rh_v]),
            stance_target if not left_is_support else swing_target,
            p.hip_kp,
            p.hip_kd,
            p.hip_torque_limit,
        )
        rk_tau = limited_pd(
            float(data.qpos[rk_q]),
            float(data.qvel[rk_v]),
            stance_knee if not left_is_support else swing_knee,
            p.knee_kp,
            p.knee_kd,
            p.knee_torque_limit,
        )
        data.ctrl[:] = (lh_tau, lk_tau, rh_tau, rk_tau)

        mujoco.mj_step(model, data)

        # Contact detection
        left_c, right_c = get_contact_flags(
            model,
            data,
            "ramp",
            ["left_heel", "left_sole", "left_toe", "left_sole_lat"],
            ["right_heel", "right_sole", "right_toe", "right_sole_lat"],
        )

        contacts = {"left": left_c, "right": right_c}
        stable_feet = []
        for foot, has_c in contacts.items():
            if has_c:
                if candidate_start_t[foot] is None:
                    candidate_start_t[foot] = t
                    contact_reported[foot] = False
                if t - float(candidate_start_t[foot]) >= p.stable_contact_time:
                    stable_feet.append(foot)
            else:
                candidate_start_t[foot] = None
                contact_reported[foot] = False

        for foot in stable_feet:
            if (
                not contact_reported[foot]
                and foot != accepted_contact
                and t - last_event_t > p.min_event_interval
            ):
                if accepted_contact in {"left", "right"}:
                    alternations += 1
                accepted_contact = foot
                support_foot = foot
                burst_start_t = t
                last_event_t = t
                contact_reported[foot] = True
                break

        # Record frame
        if step % record_stride == 0:
            recorder.record(t, left_c, right_c, support_foot, alternations)

        # Early termination checks
        if not np.all(np.isfinite(data.qpos)):
            break
        roll = abs(float(data.qpos[hr_q]))
        if roll > np.radians(45):
            break
        if hip_z - ramp_height(hip_x, gamma=p.gamma) < 0.22:
            break
        if t > 4.0 and float(data.qpos[hx_q]) - start_x < 0.20:
            break

    return recorder.frames_data


def annotate(
    frame: np.ndarray, frame_data: dict, params: Lateral3DParams, view_name: str = ""
) -> np.ndarray:
    """Add Chinese annotations to frame."""
    import numpy as np

    image = Image.fromarray(frame)
    draw = ImageDraw.Draw(image, "RGBA")
    title_font = _font(32)
    font = _font(24)
    small_font = _font(20)

    t = frame_data["time"]
    roll_deg = np.degrees(frame_data["hip_roll"])
    hip_y = frame_data["hip_y"]
    alternations = frame_data["alternations"]

    # Status colors
    roll_color = (255, 100, 100) if abs(roll_deg) > 15 else (100, 255, 150)
    hip_y_color = (255, 100, 100) if abs(hip_y) > 0.15 else (100, 255, 150)

    # Main info box
    draw.rectangle((20, 20, 450, 180), fill=(0, 0, 0, 200))
    draw.text((35, 30), f"时间: {t:.2f}s", font=title_font, fill=(255, 255, 255))
    draw.text((35, 70), f"Roll角度: {roll_deg:+.1f}°", font=font, fill=roll_color)
    draw.text((35, 105), f"侧向位移: {hip_y*1000:+.0f}mm", font=font, fill=hip_y_color)
    draw.text((35, 140), f"步数: {alternations}", font=font, fill=(255, 255, 150))

    # Parameters box
    draw.rectangle((image.width - 380, 20, image.width - 20, 120), fill=(0, 0, 0, 200))
    draw.text(
        (image.width - 360, 30),
        f"Roll刚度: {params.hip_roll_stiffness:.0f}",
        font=small_font,
        fill=(150, 200, 255),
    )
    draw.text(
        (image.width - 360, 60),
        f"Roll阻尼: {params.hip_roll_damping:.1f}",
        font=small_font,
        fill=(150, 200, 255),
    )
    draw.text(
        (image.width - 360, 90),
        f"初始扰动: {params.init_hip_roll_deg:.1f}°",
        font=small_font,
        fill=(150, 200, 255),
    )

    # View label
    if view_name:
        draw.rectangle(
            (
                image.width // 2 - 100,
                image.height - 60,
                image.width // 2 + 100,
                image.height - 20,
            ),
            fill=(0, 0, 0, 180),
        )
        draw.text(
            (image.width // 2 - 80, image.height - 50),
            view_name,
            font=title_font,
            fill=(255, 255, 255),
        )

    return np.array(image)


def render_view(
    frames_data: list,
    params: Lateral3DParams,
    view_mode: str,
    width: int = 1280,
    height: int = 720,
) -> list:
    """Render frames for a specific view."""

    write_model(params)
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    sim = mujoco.MjData(model)
    renderer = mujoco.Renderer(model, height=height, width=width)

    camera = mujoco.MjvCamera()
    if view_mode == "sagittal":
        camera.distance = 3.0
        camera.azimuth = 90
        camera.elevation = -10
        view_label = "侧视图 (Sagittal)"
    elif view_mode == "frontal":
        camera.distance = 2.5
        camera.azimuth = 0
        camera.elevation = 0
        view_label = "前视图 (Frontal)"
    else:
        camera.distance = 3.5
        camera.azimuth = 45
        camera.elevation = -15
        view_label = "斜视图"

    rendered_frames = []
    for frame_data in frames_data:
        sim.qpos[:] = frame_data["qpos"]
        sim.qvel[:] = frame_data["qvel"]
        mujoco.mj_forward(model, sim)

        # Camera follows hip
        hip_x = frame_data["hip_x"]
        if view_mode == "sagittal" or view_mode == "frontal":
            camera.lookat[:] = [hip_x, 0.0, 0.5]
        else:
            camera.lookat[:] = [hip_x, 0.0, 0.5]

        renderer.update_scene(sim, camera=camera)
        frame = renderer.render()
        annotated = annotate(frame, frame_data, params, view_label)
        rendered_frames.append(annotated)

    renderer.close()
    return rendered_frames


def render_comparison(
    frames_list: list,
    params_list: list,
    labels: list,
    width: int = 1280,
    height: int = 720,
) -> list:
    """Render side-by-side comparison video."""
    import numpy as np

    n = len(frames_list)
    tile_width = width // n

    # Render each condition
    all_rendered = []
    for frames_data, params, label in zip(frames_list, params_list, labels):
        rendered = render_view(frames_data, params, "sagittal", tile_width, height)
        all_rendered.append(rendered)

    # Pad to same length
    max_len = max(len(r) for r in all_rendered)
    for rendered in all_rendered:
        while len(rendered) < max_len:
            rendered.append(rendered[-1])

    # Composite frames
    composite_frames = []
    title_font = _font(36)

    for i in range(max_len):
        tiles = []
        for j, (rendered, label) in enumerate(zip(all_rendered, labels)):
            tile = Image.fromarray(rendered[i])
            draw = ImageDraw.Draw(tile, "RGBA")

            # Condition label at bottom
            draw.rectangle(
                (10, height - 70, tile_width - 10, height - 10), fill=(0, 0, 0, 220)
            )
            draw.text((20, height - 60), label, font=title_font, fill=(255, 255, 255))

            tiles.append(np.array(tile))

        composite_frames.append(np.hstack(tiles))

    return composite_frames


def main():
    import numpy as np

    parser = argparse.ArgumentParser(description="V18 渲染脚本")
    parser.add_argument(
        "--mode", choices=["single", "dual", "comparison"], default="single"
    )
    parser.add_argument("--fps", type=int, default=60)
    parser.add_argument("--duration", type=float, default=8.0)
    parser.add_argument("--roll-perturb", type=float, default=3.0)
    parser.add_argument("--roll-stiffness", type=float, default=100.0)
    args = parser.parse_args()

    OUT_DIR.mkdir(exist_ok=True)

    if args.mode == "single":
        # Single condition rendering
        params = Lateral3DParams(
            duration=args.duration,
            init_hip_roll_deg=args.roll_perturb,
            hip_roll_stiffness=args.roll_stiffness,
        )

        print(f"运行仿真 (roll_k={args.roll_stiffness})...")
        frames_data = run_and_record_v18(params, target_duration=args.duration)
        print(f"记录 {len(frames_data)} 帧")

        print("渲染侧视图...")
        frames_sag = render_view(frames_data, params, "sagittal")
        out_sag = OUT_DIR / f"v18_rollk{int(args.roll_stiffness)}_sagittal.mp4"
        with imageio.get_writer(out_sag, fps=args.fps, codec="libx264", quality=8) as w:
            for f in frames_sag:
                w.append_data(f)
        print(f"[OK] 保存: {out_sag}")

        print("渲染前视图...")
        frames_front = render_view(frames_data, params, "frontal")
        out_front = OUT_DIR / f"v18_rollk{int(args.roll_stiffness)}_frontal.mp4"
        with imageio.get_writer(
            out_front, fps=args.fps, codec="libx264", quality=8
        ) as w:
            for f in frames_front:
                w.append_data(f)
        print(f"[OK] 保存: {out_front}")

    elif args.mode == "dual":
        # Dual view (sagittal + frontal side by side)
        params = Lateral3DParams(
            duration=args.duration,
            init_hip_roll_deg=args.roll_perturb,
            hip_roll_stiffness=args.roll_stiffness,
        )

        print(f"运行仿真 (roll_k={args.roll_stiffness})...")
        frames_data = run_and_record_v18(params, target_duration=args.duration)
        print(f"记录 {len(frames_data)} 帧")

        print("渲染双视角...")
        frames_sag = render_view(frames_data, params, "sagittal", 640, 720)
        frames_front = render_view(frames_data, params, "frontal", 640, 720)

        import numpy as np

        composite = [np.hstack([s, f]) for s, f in zip(frames_sag, frames_front)]

        out = OUT_DIR / f"v18_rollk{int(args.roll_stiffness)}_dual.mp4"
        with imageio.get_writer(out, fps=args.fps, codec="libx264", quality=8) as w:
            for f in composite:
                w.append_data(f)
        print(f"[OK] 保存: {out}")

    elif args.mode == "comparison":
        # Comparison: roll_k=100 (fail) vs roll_k=500 (stable)
        print("=" * 60)
        print("对比渲染: roll_k=100 vs roll_k=500")
        print("=" * 60)

        params_fail = Lateral3DParams(
            duration=args.duration,
            init_hip_roll_deg=args.roll_perturb,
            hip_roll_stiffness=100.0,
            hip_roll_damping=0.5,
        )

        params_stable = Lateral3DParams(
            duration=args.duration,
            init_hip_roll_deg=args.roll_perturb,
            hip_roll_stiffness=500.0,
            hip_roll_damping=2.0,
        )

        print("\n[1/2] 仿真 roll_k=100 (失败)...")
        frames_fail = run_and_record_v18(params_fail, target_duration=args.duration)
        print(
            f"  记录 {len(frames_fail)} 帧, 最终步数={frames_fail[-1]['alternations']}"
        )

        print("\n[2/2] 仿真 roll_k=500 (稳定)...")
        frames_stable = run_and_record_v18(params_stable, target_duration=args.duration)
        print(
            f"  记录 {len(frames_stable)} 帧, 最终步数={frames_stable[-1]['alternations']}"
        )

        print("\n渲染对比视频...")
        composite = render_comparison(
            [frames_fail, frames_stable],
            [params_fail, params_stable],
            ["roll_k=100 (失败)", "roll_k=500 (稳定)"],
        )

        out = OUT_DIR / "v18_comparison.mp4"
        with imageio.get_writer(out, fps=args.fps, codec="libx264", quality=8) as w:
            for f in composite:
                w.append_data(f)
        print(f"[OK] 保存: {out}")

        # Save metadata
        metadata = {
            "fail_case": {
                "roll_stiffness": params_fail.hip_roll_stiffness,
                "final_steps": frames_fail[-1]["alternations"],
                "final_roll_deg": float(np.degrees(frames_fail[-1]["hip_roll"])),
                "final_hip_y": float(frames_fail[-1]["hip_y"]),
            },
            "stable_case": {
                "roll_stiffness": params_stable.hip_roll_stiffness,
                "final_steps": frames_stable[-1]["alternations"],
                "final_roll_deg": float(np.degrees(frames_stable[-1]["hip_roll"])),
                "final_hip_y": float(frames_stable[-1]["hip_y"]),
            },
        }
        metadata_path = OUT_DIR / "v18_comparison_metadata.json"
        metadata_path.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"[OK] 元数据: {metadata_path}")

    print("\n渲染完成！")


if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()
