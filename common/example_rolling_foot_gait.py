"""Example usage of RollingFootGait model.

This script demonstrates how to:
1. Create a RollingFootGait instance with custom parameters
2. Run a simulation with the model
3. Track contact events and energy metrics
4. Save simulation results
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import mujoco

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from common.rolling_foot_gait import RollingFootGait, RollingFootParams


def run_simulation_example(
    params: RollingFootParams,
    output_prefix: str | None = None,
) -> dict:
    """Run a simulation with the RollingFootGait model.

    Args:
        params: Model parameters
        output_prefix: Optional prefix for output files

    Returns:
        Summary dictionary with simulation results
    """
    print("Initializing RollingFootGait model...")
    print(f"  Slope: {params.slope_deg} degrees")
    print(f"  Duration: {params.duration}s")
    print(f"  Timestep: {params.timestep}s")
    print()

    # Create model and initialize
    gait = RollingFootGait(params)
    gait.initialize()

    model = gait.model
    data = gait.data

    # Simulation tracking
    start_x = float(data.qpos[0])
    max_x = start_x
    support_foot = "left"
    burst_start_t = -params.gait_period
    contact_events = []
    alternations = 0
    last_event_t = -1.0

    # Contact state tracking
    candidate_start_t = {"left": None, "right": None}
    contact_reported = {"left": False, "right": False}
    accepted_contact = ""

    # Energy tracking
    positive_input_energy = 0.0
    net_work = 0.0

    # Data recording
    sample_hz = 120.0
    sample_stride = max(1, int(round(1.0 / (params.timestep * sample_hz))))
    rows = []

    print("Running simulation...")
    n_steps = int(params.duration / params.timestep)

    for step in range(n_steps):
        t = step * params.timestep

        # Compute control
        left_hip_tau, left_knee_tau, right_hip_tau, right_knee_tau, mode = (
            gait.compute_control(t, support_foot, burst_start_t)
        )
        data.ctrl[:] = [left_hip_tau, left_knee_tau, right_hip_tau, right_knee_tau]

        # Calculate power and energy
        input_power = (
            float(data.ctrl[0]) * float(data.qvel[2])
            + float(data.ctrl[1]) * float(data.qvel[3])
            + float(data.ctrl[2]) * float(data.qvel[5])
            + float(data.ctrl[3]) * float(data.qvel[6])
        )
        positive_input_energy += max(0.0, input_power) * params.timestep
        net_work += input_power * params.timestep

        # Step simulation
        mujoco.mj_step(model, data)

        # Update max distance
        max_x = max(max_x, float(data.qpos[0]))

        # Contact detection
        left_contact, right_contact = gait.contact_flags()
        contacts = {"left": left_contact, "right": right_contact}

        # Stable contact detection
        stable_feet = []
        for foot, has_contact in contacts.items():
            if has_contact:
                if candidate_start_t[foot] is None:
                    candidate_start_t[foot] = t
                    contact_reported[foot] = False
                if t - float(candidate_start_t[foot]) >= params.stable_contact_time:
                    stable_feet.append(foot)
            else:
                candidate_start_t[foot] = None
                contact_reported[foot] = False

        # Process contact events
        for foot in stable_feet:
            if (
                not contact_reported[foot]
                and foot != accepted_contact
                and t - last_event_t > params.min_event_interval
            ):
                if accepted_contact in {"left", "right"}:
                    alternations += 1
                accepted_contact = foot
                support_foot = foot
                burst_start_t = t
                last_event_t = t
                contact_reported[foot] = True
                contact_events.append({"time": t, "foot": foot})
                print(
                    f"  t={t:.3f}s: {foot} foot touchdown (alternation #{alternations})"
                )
                break

        # Record data
        if step % sample_stride == 0:
            detail = gait.foot_contact_detail()
            rows.append(
                {
                    "time": t,
                    "hip_x": float(data.qpos[0]),
                    "hip_z": float(data.qpos[1]),
                    "left_hip": float(data.qpos[2]),
                    "left_knee": float(data.qpos[3]),
                    "left_ankle": float(data.qpos[4]),
                    "right_hip": float(data.qpos[5]),
                    "right_knee": float(data.qpos[6]),
                    "right_ankle": float(data.qpos[7]),
                    "left_contact": int(left_contact),
                    "right_contact": int(right_contact),
                    "left_heel_contact": int(detail["left_heel"]),
                    "left_sole_contact": int(detail["left_sole"]),
                    "left_toe_contact": int(detail["left_toe"]),
                    "right_heel_contact": int(detail["right_heel"]),
                    "right_sole_contact": int(detail["right_sole"]),
                    "right_toe_contact": int(detail["right_toe"]),
                    "support_foot": support_foot,
                    "mode": mode,
                    "left_hip_tau": left_hip_tau,
                    "left_knee_tau": left_knee_tau,
                    "right_hip_tau": right_hip_tau,
                    "right_knee_tau": right_knee_tau,
                    "input_power": input_power,
                    "input_energy": positive_input_energy,
                }
            )

        # Check for failure
        failure = gait.classify_failure(start_x, t)
        if failure:
            print(f"  Simulation stopped at t={t:.3f}s: {failure}")
            break

    # Summary
    simulated_time = t
    forward_distance = max_x - start_x

    print()
    print("Simulation completed!")
    print(f"  Simulated time: {simulated_time:.3f}s")
    print(f"  Forward distance: {forward_distance:.3f}m")
    print(f"  Alternating touchdowns: {alternations}")
    print(f"  Contact events: {len(contact_events)}")
    print(f"  Positive input energy: {positive_input_energy:.3f}J")
    print(f"  Net work: {net_work:.3f}J")
    if alternations > 0:
        print(f"  Energy per alternation: {positive_input_energy / alternations:.3f}J")
    print()

    summary = {
        "params": params.to_dict(),
        "simulated_time": simulated_time,
        "forward_distance": forward_distance,
        "alternating_touchdowns": alternations,
        "contact_events": contact_events,
        "positive_input_energy": positive_input_energy,
        "net_work": net_work,
        "energy_per_alternation": positive_input_energy / max(1, alternations),
        "failure": failure if failure else "completed",
        "num_samples": len(rows),
    }

    # Save results if output prefix provided
    if output_prefix:
        output_dir = ROOT / "common" / "out"
        output_dir.mkdir(exist_ok=True)

        # Save CSV
        csv_path = output_dir / f"{output_prefix}_data.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            if rows:
                writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)
        print(f"Data saved to: {csv_path}")

        # Save JSON summary
        json_path = output_dir / f"{output_prefix}_summary.json"
        with json_path.open("w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        print(f"Summary saved to: {json_path}")
        print()

    return summary


def main():
    """Run example simulations."""
    print("=" * 60)
    print("RollingFootGait Model - Usage Example")
    print("=" * 60)
    print()

    # Example 1: Default parameters on flat ground
    print("Example 1: Default parameters (flat ground)")
    print("-" * 60)
    params1 = RollingFootParams(duration=10.0)
    summary1 = run_simulation_example(params1, output_prefix="example_flat")

    # Example 2: Walking on a slope
    print("Example 2: Walking on 3-degree slope")
    print("-" * 60)
    params2 = RollingFootParams(slope_deg=3.0, duration=10.0)
    summary2 = run_simulation_example(params2, output_prefix="example_slope")

    # Example 3: Custom parameters
    print("Example 3: Custom parameters (heavier walker, longer gait period)")
    print("-" * 60)
    params3 = RollingFootParams(
        hip_mass=7.0,
        gait_period=1.2,
        duration=8.0,
    )
    summary3 = run_simulation_example(params3, output_prefix="example_custom")

    # Print comparison
    print("=" * 60)
    print("Comparison Summary")
    print("=" * 60)
    examples = [
        ("Flat ground", summary1),
        ("3° slope", summary2),
        ("Custom params", summary3),
    ]

    for name, summary in examples:
        print(f"\n{name}:")
        print(f"  Distance: {summary['forward_distance']:.3f}m")
        print(f"  Touchdowns: {summary['alternating_touchdowns']}")
        print(f"  Energy: {summary['positive_input_energy']:.3f}J")
        print(f"  Status: {summary['failure']}")

    print()


if __name__ == "__main__":
    sys.exit(main())
