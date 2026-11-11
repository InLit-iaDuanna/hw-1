"""V21 扰动测试可视化：渲染 roll 扰动梯度和失败模式的 MP4 动画。

用法：
  # 生成扰动梯度动画（0.5°, 1.0°, 1.5°）
  python render_v21.py --mode cascade --output v21_perturbation_cascade.mp4

  # 生成失败模式集合（0°, +1°, +2°, +3°）
  python render_v21.py --mode failures --output v21_failure_modes.mp4

  # 单个配置渲染
  python render_v21.py --mode single --init-roll 2.0 --output v21_roll_2deg.mp4
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import imageio.v2 as imageio
import mujoco
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from simulate_v21_perturbation import (
    PerturbationScenario,
)  # noqa: E402

from v19_hip_abduction_active.model_3d_v19 import (
    MODEL_PATH,
    V19Params,
    write_model,
)  # noqa: E402

OUT_DIR = ROOT / "out"
FONT = Path("C:/Windows/Fonts/msyh.ttc")


def _jaddr(model, name):
    jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)
    return model.jnt_qposadr[jid], model.jnt_dofadr[jid]


def _ramp_h(x, gamma):
    return -math.tan(gamma) * x


def simulate_and_record(p: V19Params, scenario: PerturbationScenario, dt=0.001):
    """运行仿真并记录完整轨迹。"""
    from dataclasses import replace

    from simulate_v21_perturbation import (
        _contacts,
        _jaddr,
        _lpd,
        _smoothstep,
    )

    from common import disturbance

    # 覆盖 init_hip_roll_deg
    p = replace(p, init_hip_roll_deg=scenario.init_hip_roll_deg)

    write_model(p)
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    data = mujoco.MjData(model)

    hx_q, hx_v = _jaddr(model, "hip_x")
    hy_q, hy_v = _jaddr(model, "hip_y")
    hz_q, hz_v = _jaddr(model, "hip_z")
    hr_q, hr_v = _jaddr(model, "hip_roll")
    lh_q, lh_v = _jaddr(model, "left_hip")
    lk_q, lk_v = _jaddr(model, "left_knee")
    rh_q, rh_v = _jaddr(model, "right_hip")
    rk_q, rk_v = _jaddr(model, "right_knee")
    la_q, la_v = _jaddr(model, "left_hip_abd")
    ra_q, ra_v = _jaddr(model, "right_hip_abd")

    # 初始化
    u0 = _smoothstep(p.release_phase)
    alpha = math.asin(p.step_length / (2.0 * p.leg_length))
    sz = -math.tan(p.gamma) * 0.0 + p.foot_radius / max(0.2, math.cos(p.gamma))
    lhi = p.gamma + alpha - 2.0 * alpha * u0
    hxi = p.leg_length * math.sin(lhi)
    hzi = sz + p.leg_length * math.cos(lhi)
    px, pz = hxi - p.swing_foot_x, hzi - (sz + p.swing_foot_clearance)
    d = float(
        np.clip(
            math.hypot(px, pz),
            abs(p.thigh_length - p.shank_length) + 1e-5,
            p.leg_length - 1e-5,
        )
    )
    cd = (p.thigh_length**2 + d**2 - p.shank_length**2) / (2.0 * p.thigh_length * d)
    rhi = math.atan2(px, pz) - math.acos(float(np.clip(cd, -1.0, 1.0)))
    kx = hxi - p.thigh_length * math.sin(rhi)
    kz = hzi - p.thigh_length * math.cos(rhi)
    rki = float(
        np.clip(
            math.atan2(kx - p.swing_foot_x, kz - (sz + p.swing_foot_clearance)) - rhi,
            0.0,
            math.radians(p.knee_limit_deg),
        )
    )

    data.qpos[hx_q] = hxi
    data.qpos[hy_q] = p.init_hip_y
    data.qpos[hz_q] = hzi
    data.qpos[hr_q] = math.radians(p.init_hip_roll_deg)
    data.qpos[la_q] = 0.0
    data.qpos[ra_q] = 0.0
    data.qpos[lh_q] = lhi
    data.qpos[lk_q] = 0.0
    data.qpos[rh_q] = rhi
    data.qpos[rk_q] = rki
    data.qvel[hx_v] = p.initial_vx
    data.qvel[hz_v] = -math.tan(p.gamma) * p.initial_vx
    data.qvel[lh_v] = 0.04
    data.qvel[rh_v] = p.swing_hip_vel
    data.qvel[rk_v] = p.swing_knee_vel
    data.ctrl[:] = 0.0
    mujoco.mj_forward(model, data)

    impulse_spec = disturbance.ImpulseSpec(
        body_name="hip",
        force_xyz=(0.0, scenario.lateral_impulse_n, 0.0),
        t_start_s=scenario.impulse_t_s,
        duration_s=scenario.impulse_duration_s,
    )

    wind_rng = (
        np.random.default_rng(scenario.wind_seed)
        if scenario.random_wind_std_n > 0.0
        else None
    )

    support = "left"
    burst_t = -p.gait_period
    last_ev = -1.0
    alternations = 0
    accepted = ""
    cand = {"left": None, "right": None}
    crep = {"left": False, "right": False}
    failure = ""
    start_x = float(data.qpos[hx_q])
    max_x = start_x
    abd_tgt = math.radians(p.abd_target_deg)

    # 记录轨迹
    trajectory = []
    max_steps = int(p.duration / p.timestep)

    for step in range(max_steps):
        t = step * p.timestep
        hx = float(data.qpos[hx_q])
        hz = float(data.qpos[hz_q])
        u = min(max((t - burst_t) / max(p.gait_period, 1e-6), 0.0), 1.0)
        if hz - (-math.tan(p.gamma) * hx) < p.recovery_clearance:
            u = min(u, 0.55)
        s = _smoothstep(u)
        st = p.gamma + math.radians(
            p.stance_front_deg + (p.stance_back_deg - p.stance_front_deg) * s
        )
        sw = p.gamma + math.radians(
            p.swing_back_deg + (p.swing_front_deg - p.swing_back_deg) * s
        )
        skn = math.radians(p.swing_knee_flex_deg * math.sin(math.pi * u))
        skst = math.radians(p.stance_knee_deg)
        ls = support == "left"
        lh_t = _lpd(
            float(data.qpos[lh_q]),
            float(data.qvel[lh_v]),
            st if ls else sw,
            p.hip_kp,
            p.hip_kd,
            p.hip_torque_limit,
        )
        lk_t = _lpd(
            float(data.qpos[lk_q]),
            float(data.qvel[lk_v]),
            skst if ls else skn,
            p.knee_kp,
            p.knee_kd,
            p.knee_torque_limit,
        )
        rh_t = _lpd(
            float(data.qpos[rh_q]),
            float(data.qvel[rh_v]),
            st if not ls else sw,
            p.hip_kp,
            p.hip_kd,
            p.hip_torque_limit,
        )
        rk_t = _lpd(
            float(data.qpos[rk_q]),
            float(data.qvel[rk_v]),
            skst if not ls else skn,
            p.knee_kp,
            p.knee_kd,
            p.knee_torque_limit,
        )

        # V19 主动髋外展控制
        hip_y_err = float(data.qpos[hy_q])
        hip_y_vel = float(data.qvel[hy_v])
        lat_correction = p.abd_kp * hip_y_err + p.abd_kd * hip_y_vel
        lat_correction = float(
            np.clip(lat_correction, -p.abd_torque_limit, p.abd_torque_limit)
        )
        if ls:
            la_t = -lat_correction
            ra_t = _lpd(
                float(data.qpos[ra_q]),
                float(data.qvel[ra_v]),
                abd_tgt,
                p.abd_kp * 0.3,
                p.abd_kd * 0.3,
                p.abd_torque_limit,
            )
        else:
            la_t = _lpd(
                float(data.qpos[la_q]),
                float(data.qvel[la_v]),
                abd_tgt,
                p.abd_kp * 0.3,
                p.abd_kd * 0.3,
                p.abd_torque_limit,
            )
            ra_t = lat_correction
        data.ctrl[:] = (lh_t, lk_t, rh_t, rk_t, la_t, ra_t)

        # 施加扰动
        disturbance.apply_impulse(model, data, impulse_spec, t)
        if wind_rng is not None:
            hip_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "hip")
            wind_fx = float(wind_rng.normal(0.0, scenario.random_wind_std_n))
            wind_fy = float(wind_rng.normal(0.0, scenario.random_wind_std_n))
            data.xfrc_applied[hip_id, 0] += wind_fx
            data.xfrc_applied[hip_id, 1] += wind_fy

        mujoco.mj_step(model, data)
        max_x = max(max_x, float(data.qpos[hx_q]))
        roll = abs(float(data.qpos[hr_q]))
        hy = abs(float(data.qpos[hy_q]))

        # 记录状态
        trajectory.append(
            {
                "t": t,
                "qpos": data.qpos.copy(),
                "qvel": data.qvel.copy(),
                "alternations": alternations,
                "roll_deg": math.degrees(roll),
                "hip_y": hy,
            }
        )

        lc, rc = _contacts(model, data)
        for foot, has_c in (("left", lc), ("right", rc)):
            if has_c:
                if cand[foot] is None:
                    cand[foot] = t
                    crep[foot] = False
                if t - float(cand[foot]) >= p.stable_contact_time:
                    if (
                        not crep[foot]
                        and foot != accepted
                        and t - last_ev > p.min_event_interval
                    ):
                        if accepted in {"left", "right"}:
                            alternations += 1
                        accepted = foot
                        support = foot
                        burst_t = t
                        last_ev = t
                        crep[foot] = True
            else:
                cand[foot] = None
                crep[foot] = False

        if not np.all(np.isfinite(data.qpos)):
            failure = "nan_or_unstable"
            break
        if roll > math.radians(45):
            failure = "lateral_fall"
            break
        if hy > 0.5:
            failure = "lateral_drift"
            break
        if hz - (-math.tan(p.gamma) * hx) < 0.22:
            failure = "fall_down"
            break
        if t > 4.0 and float(data.qpos[hx_q]) - start_x < 0.20:
            failure = "stuck"
            break

    return {
        "trajectory": trajectory,
        "alternations": alternations,
        "failure": failure or "completed",
        "sim_time": t,
        "forward_distance": max_x - start_x,
    }


def annotate_frame(frame, t, state, scenario, result, mode="single") -> np.ndarray:
    """为帧添加标注信息。"""
    img = Image.fromarray(frame)
    draw = ImageDraw.Draw(img, "RGBA")
    title_font = ImageFont.truetype(str(FONT), 28)
    font = ImageFont.truetype(str(FONT), 18)

    # 背景框
    draw.rectangle((20, 18, 1100, 178), fill=(8, 14, 24, 220))

    # 标题
    if mode == "cascade":
        title = f"V21 扰动梯度 — roll={scenario.init_hip_roll_deg:+.1f}°"
    elif mode == "failures":
        title = f"V21 失败模式 — roll={scenario.init_hip_roll_deg:+.1f}°"
    else:
        title = f"V21 扰动测试 — roll={scenario.init_hip_roll_deg:+.1f}°"

    draw.text((36, 28), title, font=title_font, fill=(255, 255, 255))

    # 配置信息
    draw.text(
        (38, 70),
        "V19 配置: abd_kp=40.0  abd_kd=4.0  abd_τ_limit=6.0 N·m",
        font=font,
        fill=(232, 238, 244),
    )

    # 状态信息
    roll_color = (255, 172, 172) if state["roll_deg"] > 15 else (232, 238, 244)
    hy_color = (255, 172, 172) if state["hip_y"] > 0.3 else (232, 238, 244)

    draw.text(
        (38, 100),
        f"t={t:5.2f}s  触地数={state['alternations']}  roll={state['roll_deg']:5.1f}°  hip_y={state['hip_y']:.3f}m",
        font=font,
        fill=(232, 238, 244),
    )

    # 结果状态
    if result["failure"] == "completed":
        status = f"✓ 完成 ({result['alternations']} alt)"
        status_color = (172, 255, 191)
    else:
        status = f"✗ {result['failure']} ({result['alternations']} alt)"
        status_color = (255, 172, 172)

    draw.text((38, 130), status, font=font, fill=status_color)

    # 非单调响应警告（仅 cascade 模式）
    if mode == "cascade" and abs(scenario.init_hip_roll_deg) > 0:
        draw.text(
            (38, 155),
            "非单调响应：初始扰动 < 1° 即影响性能",
            font=font,
            fill=(255, 200, 100),
        )

    return np.array(img)


def render_single(init_roll_deg: float, output: str, fps=60):
    """渲染单个扰动配置。"""
    p = V19Params(
        abd_kp=40.0,
        abd_kd=4.0,
        abd_torque_limit=6.0,
        duration=10.0,
    )

    scenario = PerturbationScenario(init_hip_roll_deg=init_roll_deg)

    print(f"正在仿真 roll={init_roll_deg:+.1f}° ...")
    result = simulate_and_record(p, scenario)

    write_model(p)
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    data = mujoco.MjData(model)
    renderer = mujoco.Renderer(model, height=720, width=1280)
    camera = mujoco.MjvCamera()
    camera.distance = 3.5
    camera.azimuth = 75
    camera.elevation = -15

    print(f"正在渲染 {len(result['trajectory'])} 帧...")
    frames = []
    trajectory = result["trajectory"]

    for i, state in enumerate(trajectory):
        if i % max(1, len(trajectory) // (int(result["sim_time"] * fps) + 1)) != 0:
            continue

        data.qpos[:] = state["qpos"]
        data.qvel[:] = state["qvel"]
        mujoco.mj_forward(model, data)

        camera.lookat[:] = [float(data.qpos[0]) + 0.3, 0.0, 0.6]
        renderer.update_scene(data, camera=camera)
        frame = renderer.render()
        frames.append(
            annotate_frame(frame, state["t"], state, scenario, result, "single")
        )

    out_path = OUT_DIR / output
    imageio.mimsave(out_path, frames, fps=fps)
    print(f"-> {out_path}")


def render_cascade(output: str, fps=60):
    """渲染扰动梯度动画（0.5°, 1.0°, 1.5°）并排对比。"""
    p = V19Params(
        abd_kp=40.0,
        abd_kd=4.0,
        abd_torque_limit=6.0,
        duration=3.0,  # 限制为 3 秒内失败
    )

    perturbations = [0.5, 1.0, 1.5]
    results = {}

    for roll_deg in perturbations:
        scenario = PerturbationScenario(init_hip_roll_deg=roll_deg)
        print(f"正在仿真 roll={roll_deg:+.1f}° ...")
        results[roll_deg] = simulate_and_record(p, scenario)

    # 找最长时长
    max_time = max(r["sim_time"] for r in results.values())
    n_frames = int(max_time * fps)

    write_model(p)
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    data = mujoco.MjData(model)
    renderer = mujoco.Renderer(model, height=720, width=1280)
    camera = mujoco.MjvCamera()
    camera.distance = 3.5
    camera.azimuth = 75
    camera.elevation = -15

    print(f"正在渲染 {n_frames} 帧并排对比...")
    combined_frames = []

    for frame_idx in range(n_frames):
        t = frame_idx / fps
        sub_frames = []

        for roll_deg in perturbations:
            result = results[roll_deg]
            scenario = PerturbationScenario(init_hip_roll_deg=roll_deg)
            trajectory = result["trajectory"]

            # 找到最近的时间点
            if t <= result["sim_time"]:
                state_idx = min(
                    range(len(trajectory)),
                    key=lambda i: abs(trajectory[i]["t"] - t),
                )
                state = trajectory[state_idx]

                data.qpos[:] = state["qpos"]
                data.qvel[:] = state["qvel"]
                mujoco.mj_forward(model, data)

                camera.lookat[:] = [float(data.qpos[0]) + 0.3, 0.0, 0.6]
                renderer.update_scene(data, camera=camera)
                frame = renderer.render()
                sub_frames.append(
                    annotate_frame(frame, t, state, scenario, result, "cascade")
                )
            else:
                # 失败后显示最后一帧
                state = trajectory[-1]
                data.qpos[:] = state["qpos"]
                data.qvel[:] = state["qvel"]
                mujoco.mj_forward(model, data)

                camera.lookat[:] = [float(data.qpos[0]) + 0.3, 0.0, 0.6]
                renderer.update_scene(data, camera=camera)
                frame = renderer.render()
                sub_frames.append(
                    annotate_frame(
                        frame, result["sim_time"], state, scenario, result, "cascade"
                    )
                )

        # 水平拼接（如果想并排显示，可以用 np.hstack）
        # 这里简化为逐个播放
        combined_frames.extend(sub_frames)

    out_path = OUT_DIR / output
    imageio.mimsave(out_path, combined_frames, fps=fps)
    print(f"-> {out_path}")


def render_failures(output: str, fps=60):
    """渲染失败模式集合（0°, +1°, +2°, +3°）。"""
    p = V19Params(
        abd_kp=40.0,
        abd_kd=4.0,
        abd_torque_limit=6.0,
        duration=3.0,
    )

    perturbations = [0.0, 1.0, 2.0, 3.0]
    results = {}

    for roll_deg in perturbations:
        scenario = PerturbationScenario(init_hip_roll_deg=roll_deg)
        print(f"正在仿真 roll={roll_deg:+.1f}° ...")
        results[roll_deg] = simulate_and_record(p, scenario)

    write_model(p)
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    data = mujoco.MjData(model)
    renderer = mujoco.Renderer(model, height=720, width=1280)
    camera = mujoco.MjvCamera()
    camera.distance = 3.5
    camera.azimuth = 75
    camera.elevation = -15

    print("正在渲染失败模式集合...")
    all_frames = []

    for roll_deg in perturbations:
        result = results[roll_deg]
        scenario = PerturbationScenario(init_hip_roll_deg=roll_deg)
        trajectory = result["trajectory"]

        for i, state in enumerate(trajectory):
            if i % max(1, len(trajectory) // (int(result["sim_time"] * fps) + 1)) != 0:
                continue

            data.qpos[:] = state["qpos"]
            data.qvel[:] = state["qvel"]
            mujoco.mj_forward(model, data)

            camera.lookat[:] = [float(data.qpos[0]) + 0.3, 0.0, 0.6]
            renderer.update_scene(data, camera=camera)
            frame = renderer.render()
            all_frames.append(
                annotate_frame(frame, state["t"], state, scenario, result, "failures")
            )

    out_path = OUT_DIR / output
    imageio.mimsave(out_path, all_frames, fps=fps)
    print(f"-> {out_path}")


def main():
    parser = argparse.ArgumentParser(description="V21 扰动测试可视化")
    parser.add_argument(
        "--mode",
        choices=["single", "cascade", "failures"],
        default="single",
        help="渲染模式",
    )
    parser.add_argument(
        "--init-roll",
        type=float,
        default=0.0,
        help="初始 roll 扰动（仅 single 模式）",
    )
    parser.add_argument("--output", required=True, help="输出文件名")
    parser.add_argument("--fps", type=int, default=60, help="帧率")
    args = parser.parse_args()

    OUT_DIR.mkdir(exist_ok=True)

    if args.mode == "single":
        render_single(args.init_roll, args.output, args.fps)
    elif args.mode == "cascade":
        render_cascade(args.output, args.fps)
    elif args.mode == "failures":
        render_failures(args.output, args.fps)


if __name__ == "__main__":
    main()
