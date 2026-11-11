"""Step-by-step comparison: ResidualRLEnvV2 vs test_v137_identity.

This script intentionally uses ResidualRLEnvV2(inner_steps=1) so each env.step()
is one MuJoCo/control millisecond, matching the V13.7 identity loop exactly.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import mujoco
import numpy as np

HW1_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HW1_ROOT))
sys.path.insert(0, str(HW1_ROOT / "rl_training"))

from rl_training.test_v137_identity import V137IdentitySimulator
from rl_training.train_residual_rl_v2 import ResidualRLEnvV2
from simulate_passive_arms_v14 import contact_flags, initialize
from simulate_v13_6 import _mechanical_energy, control_v136


def _fmt_bool_pair(left: bool, right: bool) -> str:
    return f"{int(left)}/{int(right)}"


def _fmt_reported(reported: dict[str, bool]) -> str:
    return f"{int(reported['left'])}/{int(reported['right'])}"


def _fmt_torque(torque: np.ndarray) -> str:
    return "[" + ",".join(f"{x:+.3f}" for x in torque) + "]"


def _make_identity() -> tuple[V137IdentitySimulator, dict[str, Any]]:
    sim = V137IdentitySimulator()
    p = sim.params.base
    initialize(sim.model, sim.data, p)

    for act in sim.actuators.values():
        act.saturation_count = 0

    state: dict[str, Any] = {
        "support_foot": "left",
        "accepted_contact": "",
        "candidate_start_t": {"left": None, "right": None},
        "contact_reported": {"left": False, "right": False},
        "last_event_t": -1.0,
        "burst_start_t": -p.gait_period,
    }
    return sim, state


def _identity_step(
    sim: V137IdentitySimulator, state: dict[str, Any], step: int
) -> dict[str, Any]:
    p = sim.params.base
    t = step * p.timestep
    e_current = _mechanical_energy(p, sim.data)
    tau = control_v136(
        sim.params.fsm,
        sim.data,
        t,
        state["support_foot"],
        state["burst_start_t"],
        e_current,
    )

    desired = list(tau[:4])
    if sim.params.compensate_friction:
        desired[0] = sim._compensate(
            desired[0],
            float(sim.data.qvel[sim.qvel_addr["left_hip"]]),
            sim.params.hip_motor,
        )
        desired[1] = sim._compensate(
            desired[1],
            float(sim.data.qvel[sim.qvel_addr["left_knee"]]),
            sim.params.knee_motor,
        )
        desired[2] = sim._compensate(
            desired[2],
            float(sim.data.qvel[sim.qvel_addr["right_hip"]]),
            sim.params.hip_motor,
        )
        desired[3] = sim._compensate(
            desired[3],
            float(sim.data.qvel[sim.qvel_addr["right_knee"]]),
            sim.params.knee_motor,
        )

    actual = np.array(
        [
            sim.actuators["left_hip"].compute_actual_torque(
                desired[0], float(sim.data.qvel[sim.qvel_addr["left_hip"]])
            )[0],
            sim.actuators["left_knee"].compute_actual_torque(
                desired[1], float(sim.data.qvel[sim.qvel_addr["left_knee"]])
            )[0],
            sim.actuators["right_hip"].compute_actual_torque(
                desired[2], float(sim.data.qvel[sim.qvel_addr["right_hip"]])
            )[0],
            sim.actuators["right_knee"].compute_actual_torque(
                desired[3], float(sim.data.qvel[sim.qvel_addr["right_knee"]])
            )[0],
        ],
        dtype=np.float64,
    )

    sim.data.ctrl[:] = actual
    mujoco.mj_step(sim.model, sim.data)

    left_contact, right_contact = contact_flags(sim.model, sim.data)
    contacts = {"left": left_contact, "right": right_contact}
    stable_feet: list[str] = []
    for foot, has_contact in contacts.items():
        if has_contact:
            if state["candidate_start_t"][foot] is None:
                state["candidate_start_t"][foot] = t
                state["contact_reported"][foot] = False
            if t - float(state["candidate_start_t"][foot]) >= p.stable_contact_time:
                stable_feet.append(foot)
        else:
            state["candidate_start_t"][foot] = None
            state["contact_reported"][foot] = False

    touchdown = ""
    for foot in stable_feet:
        if (
            not state["contact_reported"][foot]
            and foot != state["accepted_contact"]
            and t - state["last_event_t"] > p.min_event_interval
        ):
            state["accepted_contact"] = foot
            state["support_foot"] = foot
            state["burst_start_t"] = t
            state["last_event_t"] = t
            state["contact_reported"][foot] = True
            touchdown = foot
            break

    return {
        "t": t,
        "hip_x": float(sim.data.qpos[0]),
        "support_foot": state["support_foot"],
        "phase": f"{tau[5]}/{tau[6]}",
        "contact_reported": dict(state["contact_reported"]),
        "base_torque": actual,
        "left_contact": left_contact,
        "right_contact": right_contact,
        "touchdown": touchdown,
    }


def _v2_step(env: ResidualRLEnvV2, action: np.ndarray) -> dict[str, Any]:
    prev_last_event_t = env.last_event_t
    _obs, _reward, terminated, truncated, info = env.step(action)
    left_contact, right_contact = contact_flags(env.model, env.data)
    touchdown = env.support_foot if env.last_event_t != prev_last_event_t else ""
    return {
        "t": env.last_control_t,
        "hip_x": float(env.data.qpos[0]),
        "support_foot": env.support_foot,
        "phase": f"{env.last_left_phase_label}/{env.last_right_phase_label}",
        "contact_reported": dict(env.contact_reported),
        "base_torque": env.last_base_torques.astype(np.float64),
        "left_contact": left_contact,
        "right_contact": right_contact,
        "touchdown": touchdown,
        "terminated": terminated,
        "truncated": truncated,
        "info": info,
    }


def _first_divergence(identity: dict[str, Any], v2: dict[str, Any]) -> str:
    checks = [
        ("hip_x", abs(identity["hip_x"] - v2["hip_x"]) > 1e-9),
        ("support_foot", identity["support_foot"] != v2["support_foot"]),
        ("phase", identity["phase"] != v2["phase"]),
        ("contact_reported", identity["contact_reported"] != v2["contact_reported"]),
        (
            "base_torque",
            not np.allclose(identity["base_torque"], v2["base_torque"], atol=1e-7),
        ),
        ("left_contact", identity["left_contact"] != v2["left_contact"]),
        ("right_contact", identity["right_contact"] != v2["right_contact"]),
        ("touchdown", identity["touchdown"] != v2["touchdown"]),
    ]
    for name, diverged in checks:
        if diverged:
            return name
    return ""


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare V2 against V13.7 identity for the first second."
    )
    parser.add_argument("--seconds", type=float, default=1.0)
    parser.add_argument(
        "--stride",
        type=int,
        default=1,
        help="Print every N milliseconds; default prints every step.",
    )
    args = parser.parse_args()

    identity, identity_state = _make_identity()
    env = ResidualRLEnvV2(
        residual_scale=0.05, inner_steps=1, max_steps=int(args.seconds * 1000)
    )
    env.reset(seed=0)
    action = np.zeros(2, dtype=np.float32)

    n_steps = int(round(args.seconds / identity.params.base.timestep))
    first_divergence: tuple[int, float, str] | None = None

    print("=" * 160)
    print("DEBUG: ResidualRLEnvV2 vs test_v137_identity.py")
    print("=" * 160)
    print(
        "Fields: contact and contact_reported are left/right. base_torque is [Lhip,Lknee,Rhip,Rknee]."
    )
    print(
        f"{'step':>4} {'t':>7} | "
        f"{'hip_x identity':>14} {'hip_x V2':>14} {'diff':>10} | "
        f"{'support':>11} {'phase identity':>30} {'phase V2':>30} | "
        f"{'reported':>11} {'torque identity':>33} {'torque V2':>33} | "
        f"{'contact':>11} {'touchdown':>11}"
    )
    print("-" * 160)

    for step in range(n_steps):
        i = _identity_step(identity, identity_state, step)
        v = _v2_step(env, action)
        diff = abs(i["hip_x"] - v["hip_x"])
        divergence = _first_divergence(i, v)
        if divergence and first_divergence is None:
            first_divergence = (step, i["t"], divergence)

        if step % max(1, args.stride) == 0:
            support = f"{i['support_foot']}/{v['support_foot']}"
            reported = f"{_fmt_reported(i['contact_reported'])}/{_fmt_reported(v['contact_reported'])}"
            contact = (
                f"{_fmt_bool_pair(i['left_contact'], i['right_contact'])}/"
                f"{_fmt_bool_pair(v['left_contact'], v['right_contact'])}"
            )
            touchdown = f"{i['touchdown'] or '-'}/{v['touchdown'] or '-'}"
            marker = (
                f"  <-- first divergence: {divergence}"
                if first_divergence == (step, i["t"], divergence)
                else ""
            )
            print(
                f"{step:4d} {i['t']:7.3f} | "
                f"{i['hip_x']:14.9f} {v['hip_x']:14.9f} {diff:10.2e} | "
                f"{support:>11} {i['phase']:>30} {v['phase']:>30} | "
                f"{reported:>11} {_fmt_torque(i['base_torque']):>33} {_fmt_torque(v['base_torque']):>33} | "
                f"{contact:>11} {touchdown:>11}"
                f"{marker}"
            )

        if v["terminated"] or v["truncated"]:
            break

    print("-" * 160)
    if first_divergence is None:
        print(f"[OK] No divergence detected in the first {args.seconds:.3f}s.")
    else:
        step, t, field = first_divergence
        print(f"[DIVERGENCE] first mismatch at step={step}, t={t:.3f}s, field={field}.")

    env.close()
    return 0 if first_divergence is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
