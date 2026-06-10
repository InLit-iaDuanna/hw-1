"""Debug contact detection timing around 1.3s"""

import sys
import numpy as np
from pathlib import Path
import mujoco

HW1_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HW1_ROOT))

from rl_training.test_v137_identity import V137IdentitySimulator
from rl_training.train_residual_rl_v2 import ResidualRLEnvV2
from simulate_passive_arms_v14 import contact_flags

def debug_contact_timing():
    """对比baseline和V2在1.28-1.32s的接触检测"""

    print("=" * 80)
    print("Contact Detection Timing Debug (1.28s - 1.32s)")
    print("=" * 80)

    # === BASELINE ===
    baseline_sim = V137IdentitySimulator()
    from simulate_passive_arms_v14 import initialize
    from simulate_v13_6 import control_v136, _mechanical_energy

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

    # Run baseline to 1.28s
    for step in range(1280):
        t = step * 0.001
        E_current_base = _mechanical_energy(p_base, baseline_sim.data)
        tau_base = control_v136(fsm_base, baseline_sim.data, t, support_foot_base, burst_start_t_base, E_current_base)

        l_hip_des, l_knee_des, r_hip_des, r_knee_des = tau_base[0], tau_base[1], tau_base[2], tau_base[3]

        if baseline_sim.params.compensate_friction:
            l_hip_des = baseline_sim._compensate(l_hip_des, float(baseline_sim.data.qvel[baseline_sim.qvel_addr["left_hip"]]), baseline_sim.params.hip_motor)
            l_knee_des = baseline_sim._compensate(l_knee_des, float(baseline_sim.data.qvel[baseline_sim.qvel_addr["left_knee"]]), baseline_sim.params.knee_motor)
            r_hip_des = baseline_sim._compensate(r_hip_des, float(baseline_sim.data.qvel[baseline_sim.qvel_addr["right_hip"]]), baseline_sim.params.hip_motor)
            r_knee_des = baseline_sim._compensate(r_knee_des, float(baseline_sim.data.qvel[baseline_sim.qvel_addr["right_knee"]]), baseline_sim.params.knee_motor)

        l_hip_out, _ = baseline_sim.actuators["left_hip"].compute_actual_torque(l_hip_des, float(baseline_sim.data.qvel[baseline_sim.qvel_addr["left_hip"]]))
        l_knee_out, _ = baseline_sim.actuators["left_knee"].compute_actual_torque(l_knee_des, float(baseline_sim.data.qvel[baseline_sim.qvel_addr["left_knee"]]))
        r_hip_out, _ = baseline_sim.actuators["right_hip"].compute_actual_torque(r_hip_des, float(baseline_sim.data.qvel[baseline_sim.qvel_addr["right_hip"]]))
        r_knee_out, _ = baseline_sim.actuators["right_knee"].compute_actual_torque(r_knee_des, float(baseline_sim.data.qvel[baseline_sim.qvel_addr["right_knee"]]))

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
                if t - float(candidate_start_t_base[foot]) >= p_base.stable_contact_time:
                    stable_feet_base.append(foot)
            else:
                candidate_start_t_base[foot] = None
                contact_reported_base[foot] = False
        for foot in stable_feet_base:
            if (not contact_reported_base[foot] and foot != accepted_contact_base and t - last_event_t_base > p_base.min_event_interval):
                accepted_contact_base = foot
                support_foot_base = foot
                burst_start_t_base = t
                last_event_t_base = t
                contact_reported_base[foot] = True
                break

    # === V2 ===
    env_v2 = ResidualRLEnvV2(residual_scale=0.05, inner_steps=1, max_steps=10000)
    obs, info = env_v2.reset(seed=0)

    # Run V2 to 1.28s
    for step in range(1280):
        action = np.array([0.0, 0.0], dtype=np.float32)
        obs, reward, terminated, truncated, info = env_v2.step(action)

    print("\nDetailed contact detection from 1.28s to 1.32s (40ms):")
    print("-" * 80)

    # Now step through 40ms (1.28-1.32s) with detailed logging
    for step in range(40):
        t = 1.280 + step * 0.001

        # === BASELINE ===
        E_current_base = _mechanical_energy(p_base, baseline_sim.data)
        tau_base = control_v136(fsm_base, baseline_sim.data, t, support_foot_base, burst_start_t_base, E_current_base)

        l_hip_des, l_knee_des, r_hip_des, r_knee_des = tau_base[0], tau_base[1], tau_base[2], tau_base[3]

        if baseline_sim.params.compensate_friction:
            l_hip_des = baseline_sim._compensate(l_hip_des, float(baseline_sim.data.qvel[baseline_sim.qvel_addr["left_hip"]]), baseline_sim.params.hip_motor)
            l_knee_des = baseline_sim._compensate(l_knee_des, float(baseline_sim.data.qvel[baseline_sim.qvel_addr["left_knee"]]), baseline_sim.params.knee_motor)
            r_hip_des = baseline_sim._compensate(r_hip_des, float(baseline_sim.data.qvel[baseline_sim.qvel_addr["right_hip"]]), baseline_sim.params.hip_motor)
            r_knee_des = baseline_sim._compensate(r_knee_des, float(baseline_sim.data.qvel[baseline_sim.qvel_addr["right_knee"]]), baseline_sim.params.knee_motor)

        l_hip_out, _ = baseline_sim.actuators["left_hip"].compute_actual_torque(l_hip_des, float(baseline_sim.data.qvel[baseline_sim.qvel_addr["left_hip"]]))
        l_knee_out, _ = baseline_sim.actuators["left_knee"].compute_actual_torque(l_knee_des, float(baseline_sim.data.qvel[baseline_sim.qvel_addr["left_knee"]]))
        r_hip_out, _ = baseline_sim.actuators["right_hip"].compute_actual_torque(r_hip_des, float(baseline_sim.data.qvel[baseline_sim.qvel_addr["right_hip"]]))
        r_knee_out, _ = baseline_sim.actuators["right_knee"].compute_actual_torque(r_knee_des, float(baseline_sim.data.qvel[baseline_sim.qvel_addr["right_knee"]]))

        baseline_sim.data.ctrl[:] = (l_hip_out, l_knee_out, r_hip_out, r_knee_out)
        mujoco.mj_step(baseline_sim.model, baseline_sim.data)

        left_c_base, right_c_base = contact_flags(baseline_sim.model, baseline_sim.data)

        # Baseline FSM update
        contacts_base = {"left": left_c_base, "right": right_c_base}
        stable_feet_base = []
        for foot, has_contact in contacts_base.items():
            if has_contact:
                if candidate_start_t_base[foot] is None:
                    candidate_start_t_base[foot] = t
                    contact_reported_base[foot] = False
                if t - float(candidate_start_t_base[foot]) >= p_base.stable_contact_time:
                    stable_feet_base.append(foot)
            else:
                candidate_start_t_base[foot] = None
                contact_reported_base[foot] = False

        switched_base = False
        for foot in stable_feet_base:
            if (not contact_reported_base[foot] and foot != accepted_contact_base and t - last_event_t_base > p_base.min_event_interval):
                accepted_contact_base = foot
                support_foot_base = foot
                burst_start_t_base = t
                last_event_t_base = t
                contact_reported_base[foot] = True
                switched_base = True
                break

        # === V2 ===
        action = np.array([0.0, 0.0], dtype=np.float32)
        obs, reward, terminated, truncated, info = env_v2.step(action)

        from simulate_passive_arms_v14 import contact_flags as cf_v2
        left_c_v2, right_c_v2 = cf_v2(env_v2.model, env_v2.data)

        print(f"t={t:.3f}s:")
        print(f"  Baseline: L={int(left_c_base)} R={int(right_c_base)} | candidate_R={candidate_start_t_base['right']} | support={support_foot_base} | switched={switched_base}")
        print(f"  V2:       L={int(left_c_v2)} R={int(right_c_v2)} | candidate_R={env_v2.candidate_start_t['right']} | support={env_v2.support_foot}")

    print("-" * 80)
    print()

    env_v2.close()

if __name__ == "__main__":
    debug_contact_timing()
