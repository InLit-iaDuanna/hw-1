"""Simple V20 renderer using imageio."""

import argparse
import math
import sys
from pathlib import Path

import imageio.v2 as imageio
import mujoco
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import simulate_v20
from model_3d_v20 import MODEL_PATH, V20Params, write_model

from common import (
    get_contact_flags,
    get_joint_address,
    limited_pd,
    ramp_height,
    smoothstep,
)

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "out"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default="v20_baseline")
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--duration", type=float, default=8.0)
    parser.add_argument("--step-width-kp", type=float, default=0.0)
    parser.add_argument("--step-width-kd", type=float, default=0.0)
    args = parser.parse_args()

    # Setup parameters
    params = V20Params(
        step_width_kp=args.step_width_kp,
        step_width_kd=args.step_width_kd,
        duration=args.duration,
    )

    write_model(params)
    print(f"Running V20 simulation (duration={args.duration}s)...")
    summary = simulate_v20.run_simulation_v20(params, save_prefix=args.tag)

    print(f"Simulation complete: {summary['alternating_touchdowns']} alternations")
    print(f"Success: {summary['success']}, Failure: {summary['failure']}")

    # Re-simulate with video recording
    print("Re-simulating with video recording...")

    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    data = mujoco.MjData(model)
    renderer = mujoco.Renderer(model, height=720, width=1280)

    p = params
    hx_q, hx_v = get_joint_address(model, "hip_x")
    hy_q, hy_v = get_joint_address(model, "hip_y")
    hz_q, hz_v = get_joint_address(model, "hip_z")
    hr_q, _ = get_joint_address(model, "hip_roll")
    lh_q, lh_v = get_joint_address(model, "left_hip")
    lk_q, lk_v = get_joint_address(model, "left_knee")
    rh_q, rh_v = get_joint_address(model, "right_hip")
    rk_q, rk_v = get_joint_address(model, "right_knee")
    la_q, la_v = get_joint_address(model, "left_hip_abd")
    ra_q, ra_v = get_joint_address(model, "right_hip_abd")

    # Initialize
    u0 = smoothstep(p.release_phase)
    alpha = math.asin(p.step_length / (2.0 * p.leg_length))
    sz = ramp_height(0.0, p.gamma) + p.foot_radius / max(0.2, math.cos(p.gamma))
    lhi = p.gamma + alpha - 2.0 * alpha * u0
    hxi = p.leg_length * math.sin(lhi)
    hzi = sz + p.leg_length * math.cos(lhi)

    # Simple 2D IK for swing leg
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

    support = "left"
    burst_t = -p.gait_period
    last_ev = -1.0
    alternations = 0
    accepted = ""
    cand = {"left": None, "right": None}
    crep = {"left": False, "right": False}
    start_x = float(data.qpos[hx_q])
    abd_tgt = math.radians(p.abd_target_deg)

    frames = []
    record_stride = max(1, int((1.0 / args.fps) / p.timestep))

    for step in range(int(args.duration / p.timestep)):
        t = step * p.timestep
        hx = float(data.qpos[hx_q])
        hy = float(data.qpos[hy_q])
        hz = float(data.qpos[hz_q])
        vy = float(data.qvel[hy_v])
        u = min(max((t - burst_t) / max(p.gait_period, 1e-6), 0.0), 1.0)

        if hz - ramp_height(hx, p.gamma) < p.recovery_clearance:
            u = min(u, 0.55)
        s = smoothstep(u)

        st = p.gamma + math.radians(
            p.stance_front_deg + (p.stance_back_deg - p.stance_front_deg) * s
        )
        sw = p.gamma + math.radians(
            p.swing_back_deg + (p.swing_front_deg - p.swing_back_deg) * s
        )
        skn = math.radians(p.swing_knee_flex_deg * math.sin(math.pi * u))
        skst = math.radians(p.stance_knee_deg)
        ls = support == "left"

        lh_t = limited_pd(
            float(data.qpos[lh_q]),
            float(data.qvel[lh_v]),
            st if ls else sw,
            p.hip_kp,
            p.hip_kd,
            p.hip_torque_limit,
        )
        lk_t = limited_pd(
            float(data.qpos[lk_q]),
            float(data.qvel[lk_v]),
            skst if ls else skn,
            p.knee_kp,
            p.knee_kd,
            p.knee_torque_limit,
        )
        rh_t = limited_pd(
            float(data.qpos[rh_q]),
            float(data.qvel[rh_v]),
            st if not ls else sw,
            p.hip_kp,
            p.hip_kd,
            p.hip_torque_limit,
        )
        rk_t = limited_pd(
            float(data.qpos[rk_q]),
            float(data.qvel[rk_v]),
            skst if not ls else skn,
            p.knee_kp,
            p.knee_kd,
            p.knee_torque_limit,
        )

        # V20 step width control (baseline: hip_y feedback like V19)
        hip_y_err = hy
        lat_correction = p.abd_kp * hip_y_err + p.abd_kd * vy
        lat_correction = float(
            np.clip(lat_correction, -p.abd_torque_limit, p.abd_torque_limit)
        )

        if ls:
            la_t = -lat_correction
            ra_t = limited_pd(
                float(data.qpos[ra_q]),
                float(data.qvel[ra_v]),
                abd_tgt,
                p.abd_kp * 0.3,
                p.abd_kd * 0.3,
                p.abd_torque_limit,
            )
        else:
            la_t = limited_pd(
                float(data.qpos[la_q]),
                float(data.qvel[la_v]),
                abd_tgt,
                p.abd_kp * 0.3,
                p.abd_kd * 0.3,
                p.abd_torque_limit,
            )
            ra_t = lat_correction

        data.ctrl[:] = (lh_t, lk_t, rh_t, rk_t, la_t, ra_t)

        mujoco.mj_step(model, data)

        left_geoms = ["left_heel", "left_sole", "left_toe", "left_sole_lat"]
        right_geoms = ["right_heel", "right_sole", "right_toe", "right_sole_lat"]
        lc, rc = get_contact_flags(model, data, "ramp", left_geoms, right_geoms)

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

        if step % record_stride == 0:
            renderer.update_scene(data)
            frames.append(renderer.render())

        if not np.all(np.isfinite(data.qpos)):
            break
        roll = abs(float(data.qpos[hr_q]))
        if roll > math.radians(45):
            break
        hy_abs = abs(float(data.qpos[hy_q]))
        if hy_abs > 0.5:
            break
        if hz - ramp_height(hx, p.gamma) < 0.22:
            break
        if t > 4.0 and float(data.qpos[hx_q]) - start_x < 0.20:
            break

    OUT_DIR.mkdir(exist_ok=True)
    out = OUT_DIR / f"{args.tag}.mp4"
    imageio.mimsave(str(out), frames, fps=args.fps)
    print(f"Video saved: {out}")
    print(f"Frames: {len(frames)}, Alternations: {alternations}")


if __name__ == "__main__":
    main()
