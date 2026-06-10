"""Debug FSM transitions in test_v137_identity.py baseline"""

import sys
from pathlib import Path

HW1_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HW1_ROOT))

from rl_training.test_v137_identity import V137IdentitySimulator

def debug_baseline_fsm():
    """运行baseline并打印FSM状态转换"""

    print("=" * 80)
    print("FSM Transition Debug for test_v137_identity.py (BASELINE)")
    print("=" * 80)

    simulator = V137IdentitySimulator()

    # 手动运行仿真循环以追踪FSM
    from simulate_passive_arms_v14 import initialize, contact_flags
    from simulate_v13_6 import control_v136, _mechanical_energy

    p = simulator.params.base
    fsm = simulator.params.fsm

    initialize(simulator.model, simulator.data, p)

    for act in simulator.actuators.values():
        act.saturation_count = 0

    start_x = float(simulator.data.qpos[0])
    support_foot = "left"
    accepted_contact = ""
    candidate_start_t = {"left": None, "right": None}
    contact_reported = {"left": False, "right": False}
    last_event_t = -1.0
    burst_start_t = -p.gait_period

    print(f"\nInitial state:")
    print(f"  support_foot: {support_foot}")
    print(f"  burst_start_t: {burst_start_t:.4f}")
    print(f"  accepted_contact: '{accepted_contact}'")
    print(f"  last_event_t: {last_event_t:.4f}")
    print()

    print("FSM Transitions:")
    print("-" * 80)

    n_steps = int(4.0 / p.timestep)  # 4秒

    for step in range(n_steps):
        t = step * p.timestep

        E_current = _mechanical_energy(p, simulator.data)

        tau = control_v136(fsm, simulator.data, t, support_foot, burst_start_t, E_current)
        l_hip_des, l_knee_des, r_hip_des, r_knee_des = tau[0], tau[1], tau[2], tau[3]

        if simulator.params.compensate_friction:
            l_hip_des = simulator._compensate(
                l_hip_des, float(simulator.data.qvel[simulator.qvel_addr["left_hip"]]), simulator.params.hip_motor
            )
            l_knee_des = simulator._compensate(
                l_knee_des, float(simulator.data.qvel[simulator.qvel_addr["left_knee"]]), simulator.params.knee_motor
            )
            r_hip_des = simulator._compensate(
                r_hip_des, float(simulator.data.qvel[simulator.qvel_addr["right_hip"]]), simulator.params.hip_motor
            )
            r_knee_des = simulator._compensate(
                r_knee_des, float(simulator.data.qvel[simulator.qvel_addr["right_knee"]]), simulator.params.knee_motor
            )

        l_hip_out, _ = simulator.actuators["left_hip"].compute_actual_torque(
            l_hip_des, float(simulator.data.qvel[simulator.qvel_addr["left_hip"]])
        )
        l_knee_out, _ = simulator.actuators["left_knee"].compute_actual_torque(
            l_knee_des, float(simulator.data.qvel[simulator.qvel_addr["left_knee"]])
        )
        r_hip_out, _ = simulator.actuators["right_hip"].compute_actual_torque(
            r_hip_des, float(simulator.data.qvel[simulator.qvel_addr["right_hip"]])
        )
        r_knee_out, _ = simulator.actuators["right_knee"].compute_actual_torque(
            r_knee_des, float(simulator.data.qvel[simulator.qvel_addr["right_knee"]])
        )

        simulator.data.ctrl[:] = (l_hip_out, l_knee_out, r_hip_out, r_knee_out)

        import mujoco
        mujoco.mj_step(simulator.model, simulator.data)

        left_contact, right_contact = contact_flags(simulator.model, simulator.data)

        # FSM更新
        contacts = {"left": left_contact, "right": right_contact}
        stable_feet = []

        for foot, has_contact in contacts.items():
            if has_contact:
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
                print(f"[{t:.4f}s] FSM Event: {accepted_contact} -> {foot}")
                if accepted_contact in {"left", "right"}:
                    pass  # alternation
                accepted_contact = foot
                support_foot = foot
                burst_start_t = t
                last_event_t = t
                contact_reported[foot] = True
                break

    print("-" * 80)
    print(f"\nFinal Results:")
    print(f"  Sim time: {t:.2f}s")
    hip_x = float(simulator.data.qpos[0])
    print(f"  Distance: {hip_x - start_x:.3f}m")
    print(f"  Final accepted_contact: '{accepted_contact}'")
    print(f"  Final support_foot: '{support_foot}'")
    print()

if __name__ == "__main__":
    debug_baseline_fsm()
