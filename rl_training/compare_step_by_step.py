"""Side-by-side comparison of baseline vs V2 at same timesteps"""

import sys
from pathlib import Path

import mujoco
import numpy as np

HW1_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HW1_ROOT))

from rl_training.test_v137_identity import V137IdentitySimulator
from rl_training.train_residual_rl_v2 import ResidualRLEnvV2


def compare_baseline_vs_v2():
    """精确对比baseline和V2环境的每一步"""

    print("=" * 80)
    print("Baseline vs V2 Step-by-Step Comparison")
    print("=" * 80)

    # === BASELINE ===
    baseline_sim = V137IdentitySimulator()
    from simulate_passive_arms_v14 import contact_flags, initialize
    from simulate_v13_6 import _mechanical_energy, control_v136

    p_base = baseline_sim.params.base
    fsm_base = baseline_sim.params.fsm

    initialize(baseline_sim.model, baseline_sim.data, p_base)
    for act in baseline_sim.actuators.values():
        act.saturation_count = 0

    support_foot_base = "left"
    accepted_contact_base = ""
    candidate_start_t_base = {"left": None, "right": None}
    contact_reported_base = {"left": False, "right": False}
    last_event_t_base = -1.0
    burst_start_t_base = -p_base.gait_period

    # === V2 ===
    env_v2 = ResidualRLEnvV2(
        residual_scale=0.05, inner_steps=1, max_steps=10000
    )  # 1ms steps
    obs, info = env_v2.reset(seed=0)

    print("\nComparing first 4000ms (4000 steps):")
    print("-" * 80)

    n_steps = 4000
    max_diff = 0.0
    max_diff_step = 0

    for step in range(n_steps):
        t = step * 0.001

        # === BASELINE STEP ===
        E_current_base = _mechanical_energy(p_base, baseline_sim.data)
        tau_base = control_v136(
            fsm_base,
            baseline_sim.data,
            t,
            support_foot_base,
            burst_start_t_base,
            E_current_base,
        )

        l_hip_des, l_knee_des, r_hip_des, r_knee_des = (
            tau_base[0],
            tau_base[1],
            tau_base[2],
            tau_base[3],
        )

        if baseline_sim.params.compensate_friction:
            l_hip_des = baseline_sim._compensate(
                l_hip_des,
                float(baseline_sim.data.qvel[baseline_sim.qvel_addr["left_hip"]]),
                baseline_sim.params.hip_motor,
            )
            l_knee_des = baseline_sim._compensate(
                l_knee_des,
                float(baseline_sim.data.qvel[baseline_sim.qvel_addr["left_knee"]]),
                baseline_sim.params.knee_motor,
            )
            r_hip_des = baseline_sim._compensate(
                r_hip_des,
                float(baseline_sim.data.qvel[baseline_sim.qvel_addr["right_hip"]]),
                baseline_sim.params.hip_motor,
            )
            r_knee_des = baseline_sim._compensate(
                r_knee_des,
                float(baseline_sim.data.qvel[baseline_sim.qvel_addr["right_knee"]]),
                baseline_sim.params.knee_motor,
            )

        l_hip_out, _ = baseline_sim.actuators["left_hip"].compute_actual_torque(
            l_hip_des, float(baseline_sim.data.qvel[baseline_sim.qvel_addr["left_hip"]])
        )
        l_knee_out, _ = baseline_sim.actuators["left_knee"].compute_actual_torque(
            l_knee_des,
            float(baseline_sim.data.qvel[baseline_sim.qvel_addr["left_knee"]]),
        )
        r_hip_out, _ = baseline_sim.actuators["right_hip"].compute_actual_torque(
            r_hip_des,
            float(baseline_sim.data.qvel[baseline_sim.qvel_addr["right_hip"]]),
        )
        r_knee_out, _ = baseline_sim.actuators["right_knee"].compute_actual_torque(
            r_knee_des,
            float(baseline_sim.data.qvel[baseline_sim.qvel_addr["right_knee"]]),
        )

        baseline_sim.data.ctrl[:] = (l_hip_out, l_knee_out, r_hip_out, r_knee_out)
        mujoco.mj_step(baseline_sim.model, baseline_sim.data)

        # Baseline FSM update
        left_c_base, right_c_base = contact_flags(baseline_sim.model, baseline_sim.data)
        contacts_base = {"left": left_c_base, "right": right_c_base}
        stable_feet_base = []
        for foot, has_contact in contacts_base.items():
            if has_contact:
                if candidate_start_t_base[foot] is None:
                    candidate_start_t_base[foot] = t
                    contact_reported_base[foot] = False
                if (
                    t - float(candidate_start_t_base[foot])
                    >= p_base.stable_contact_time
                ):
                    stable_feet_base.append(foot)
            else:
                candidate_start_t_base[foot] = None
                contact_reported_base[foot] = False
        for foot in stable_feet_base:
            if (
                not contact_reported_base[foot]
                and foot != accepted_contact_base
                and t - last_event_t_base > p_base.min_event_interval
            ):
                accepted_contact_base = foot
                support_foot_base = foot
                burst_start_t_base = t
                last_event_t_base = t
                contact_reported_base[foot] = True
                break

        # === V2 STEP ===
        action = np.array([0.0, 0.0], dtype=np.float32)
        obs, reward, terminated, truncated, info = env_v2.step(action)

        # === COMPARE ===
        hip_x_base = float(baseline_sim.data.qpos[0])
        hip_x_v2 = float(env_v2.data.qpos[0])
        diff = abs(hip_x_base - hip_x_v2)

        if diff > max_diff:
            max_diff = diff
            max_diff_step = step

        if step % 100 == 0 or diff > 0.01:
            print(f"Step {step} (t={t:.3f}s):")
            print(
                f"  Baseline hip_x: {hip_x_base:.5f}m, support: {support_foot_base}, burst_t: {burst_start_t_base:.4f}"
            )
            print(
                f"  V2       hip_x: {hip_x_v2:.5f}m, support: {env_v2.support_foot}, burst_t: {env_v2.burst_start_t:.4f}"
            )
            print(f"  Diff: {diff:.5f}m")
            print()

        if terminated or truncated:
            print(f"V2 terminated at step {step}")
            break

    print("-" * 80)
    print(
        f"\nMaximum deviation: {max_diff:.5f}m at step {max_diff_step} (t={max_diff_step * 0.001:.3f}s)"
    )
    print()

    env_v2.close()


if __name__ == "__main__":
    compare_baseline_vs_v2()
