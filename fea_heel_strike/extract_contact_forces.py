"""
Generic MuJoCo contact force extraction for FEA boundary conditions.

Extracts contact forces, positions, and time histories from any hw-1 version
that uses the standard data_io.py CSV format or legacy CSV with contact sensors.

Usage:
    python extract_contact_forces.py --csv path/to/sim_data.csv --output forces.json
    python extract_contact_forces.py --version v10 --event heel_strike
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np


@dataclass
class ContactEvent:
    """Single contact event with peak force."""

    time: float
    foot: Literal["left", "right"]
    force_normal: float
    force_tangential: float
    contact_position_x: float
    contact_position_z: float
    body_velocity_x: float
    body_velocity_z: float
    event_type: Literal["heel_strike", "toe_off", "steady_contact"]


@dataclass
class ContactForceHistory:
    """Time history of contact forces for FEA input."""

    times: list[float]
    forces_normal: list[float]
    forces_tangential: list[float]
    contact_positions_x: list[float]
    contact_positions_z: list[float]
    foot: str
    start_time: float
    end_time: float
    peak_force: float
    peak_time: float
    impulse: float  # integral of force over time


def load_csv_data(csv_path: Path) -> dict[str, np.ndarray]:
    """Load CSV with automatic column detection."""
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        raise ValueError(f"CSV file {csv_path} is empty")

    # Convert to column arrays
    data = {}
    for key in rows[0].keys():
        try:
            data[key] = np.array([float(row[key]) for row in rows])
        except (ValueError, KeyError):
            # Skip non-numeric columns
            continue

    return data


def detect_contact_events(
    data: dict[str, np.ndarray],
    foot: str = "left",
    force_threshold: float = 50.0,
    event_type: str = "heel_strike",
) -> list[ContactEvent]:
    """
    Detect contact events from simulation data.

    Args:
        data: Dictionary with time, contact, force, velocity columns
        foot: "left" or "right"
        force_threshold: Minimum normal force to count as contact (N)
        event_type: "heel_strike", "toe_off", or "steady_contact"

    Returns:
        List of detected contact events
    """
    time = data.get("time")
    if time is None:
        raise ValueError("CSV must contain 'time' column")

    # Try to find contact force column (various naming conventions)
    force_col_options = [
        f"{foot}_contact_force_z",
        f"{foot}_force_normal",
        f"{foot}_fz",
        "contact_force_z",
        "force_normal",
    ]

    force_normal = None
    for col in force_col_options:
        if col in data:
            force_normal = np.abs(data[col])
            break

    if force_normal is None:
        # Try binary contact detection
        contact_col = f"{foot}_contact" if f"{foot}_contact" in data else "contact"
        if contact_col in data:
            # Binary contact -> estimate force from acceleration
            contact_binary = data[contact_col] > 0.5
            # Placeholder: assume constant force during contact
            force_normal = contact_binary.astype(float) * 100.0  # rough estimate
        else:
            raise ValueError(f"No contact force data found for {foot} foot")

    # Detect events based on type
    events = []

    if event_type == "heel_strike":
        # Find force peaks (heel strikes)
        # Peak = local maximum with force > threshold
        for i in range(1, len(force_normal) - 1):
            if force_normal[i] > force_threshold:
                if (
                    force_normal[i] > force_normal[i - 1]
                    and force_normal[i] >= force_normal[i + 1]
                ):
                    # Local maximum - heel strike
                    event = _create_event(data, i, foot, "heel_strike")
                    if event:
                        events.append(event)

    elif event_type == "toe_off":
        # Find force drops (end of contact)
        in_contact = False
        for i in range(1, len(force_normal)):
            was_contact = force_normal[i - 1] > force_threshold
            is_contact = force_normal[i] > force_threshold

            if was_contact and not is_contact:
                event = _create_event(data, i - 1, foot, "toe_off")
                if event:
                    events.append(event)

    else:  # steady_contact
        # Find all time points in contact
        for i in range(len(force_normal)):
            if force_normal[i] > force_threshold:
                event = _create_event(data, i, foot, "steady_contact")
                if event:
                    events.append(event)

    return events


def _create_event(
    data: dict[str, np.ndarray], idx: int, foot: str, event_type: str
) -> ContactEvent | None:
    """Create ContactEvent from data at given index."""
    try:
        # Required: time
        time = float(data["time"][idx])

        # Try to get force components
        force_normal = 0.0
        force_tangent = 0.0

        for key in data:
            if foot in key or "contact" in key:
                if "force_z" in key or "force_normal" in key or "fz" in key:
                    force_normal = abs(float(data[key][idx]))
                elif "force_x" in key or "force_tangent" in key or "fx" in key:
                    force_tangent = float(data[key][idx])

        # Contact position (foot endpoint)
        pos_x = data.get(
            f"{foot}_foot_x", data.get("hip_x", np.zeros(len(data["time"])))
        )[idx]
        pos_z = data.get(f"{foot}_foot_z", np.zeros(len(data["time"])))[idx]

        # Body velocities
        vel_x = data.get(
            f"{foot}_foot_vel_x", data.get("hip_x_vel", np.zeros(len(data["time"])))
        )[idx]
        vel_z = data.get(
            f"{foot}_foot_vel_z", data.get("hip_z_vel", np.zeros(len(data["time"])))
        )[idx]

        return ContactEvent(
            time=time,
            foot=foot,
            force_normal=force_normal,
            force_tangential=force_tangent,
            contact_position_x=pos_x,
            contact_position_z=pos_z,
            body_velocity_x=vel_x,
            body_velocity_z=vel_z,
            event_type=event_type,
        )
    except (KeyError, IndexError) as e:
        print(f"Warning: Could not create event at index {idx}: {e}")
        return None


def extract_contact_history(
    data: dict[str, np.ndarray],
    foot: str,
    start_time: float,
    duration: float,
) -> ContactForceHistory:
    """
    Extract contact force time history for a specific time window.

    Args:
        data: Simulation data
        foot: "left" or "right"
        start_time: Start of extraction window (s)
        duration: Duration of extraction (s)

    Returns:
        ContactForceHistory with force vs time data
    """
    time = data["time"]
    mask = (time >= start_time) & (time <= start_time + duration)

    times = time[mask].tolist()

    # Extract force components
    force_col_z = (
        f"{foot}_contact_force_z"
        if f"{foot}_contact_force_z" in data
        else "contact_force_z"
    )
    force_col_x = (
        f"{foot}_contact_force_x"
        if f"{foot}_contact_force_x" in data
        else "contact_force_x"
    )

    forces_normal = np.abs(data.get(force_col_z, np.zeros(len(time))))[mask].tolist()
    forces_tangent = data.get(force_col_x, np.zeros(len(time)))[mask].tolist()

    # Contact positions
    pos_x = data.get(f"{foot}_foot_x", data.get("hip_x", np.zeros(len(time))))[
        mask
    ].tolist()
    pos_z = data.get(f"{foot}_foot_z", np.zeros(len(time)))[mask].tolist()

    # Find peak
    forces_array = np.array(forces_normal)
    if len(forces_array) > 0 and forces_array.max() > 0:
        peak_idx = np.argmax(forces_array)
        peak_force = forces_array[peak_idx]
        peak_time = times[peak_idx]
    else:
        peak_force = 0.0
        peak_time = start_time

    # Calculate impulse (trapezoidal integration)
    impulse = np.trapz(forces_array, np.array(times)) if len(times) > 1 else 0.0

    return ContactForceHistory(
        times=times,
        forces_normal=forces_normal,
        forces_tangential=forces_tangent,
        contact_positions_x=pos_x,
        contact_positions_z=pos_z,
        foot=foot,
        start_time=start_time,
        end_time=start_time + duration,
        peak_force=peak_force,
        peak_time=peak_time,
        impulse=impulse,
    )


def extract_from_version(
    version_dir: Path,
    event_type: str = "heel_strike",
    foot: str = "left",
    num_events: int = 4,
) -> dict:
    """
    Extract contact events from a standard version directory.

    Args:
        version_dir: Path to version directory (e.g., v10_rolling_foot_biomimetic_gait)
        event_type: Type of event to extract
        foot: Which foot to analyze
        num_events: Number of events to extract (latest steady-state events)

    Returns:
        Dictionary with events and summary statistics
    """
    # Look for CSV in out/ subdirectory
    out_dir = version_dir / "out"
    csv_files = list(out_dir.glob("*.csv"))

    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {out_dir}")

    # Use the first (or most recent) CSV
    csv_path = csv_files[0]
    print(f"Loading data from {csv_path}")

    data = load_csv_data(csv_path)
    events = detect_contact_events(data, foot=foot, event_type=event_type)

    # Take last N events (steady state)
    if len(events) > num_events:
        events = events[-num_events:]

    # Calculate statistics
    forces = [e.force_normal for e in events]
    velocities_z = [e.body_velocity_z for e in events]

    result = {
        "version": version_dir.name,
        "csv_file": csv_path.name,
        "event_type": event_type,
        "foot": foot,
        "num_events": len(events),
        "events": [
            {
                "time": e.time,
                "force_normal_N": round(e.force_normal, 2),
                "force_tangential_N": round(e.force_tangential, 2),
                "contact_position_x": round(e.contact_position_x, 4),
                "contact_position_z": round(e.contact_position_z, 4),
                "velocity_x_m_s": round(e.body_velocity_x, 4),
                "velocity_z_m_s": round(e.body_velocity_z, 4),
            }
            for e in events
        ],
        "statistics": {
            "peak_force_avg_N": round(np.mean(forces), 2) if forces else 0.0,
            "peak_force_std_N": round(np.std(forces), 2) if forces else 0.0,
            "velocity_z_avg_m_s": (
                round(np.mean(velocities_z), 4) if velocities_z else 0.0
            ),
            "velocity_z_std_m_s": (
                round(np.std(velocities_z), 4) if velocities_z else 0.0
            ),
        },
    }

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Extract contact forces from MuJoCo simulation for FEA"
    )
    parser.add_argument("--csv", type=Path, help="Path to simulation CSV file")
    parser.add_argument(
        "--version", type=str, help="Version directory name (e.g., v10)"
    )
    parser.add_argument(
        "--event",
        type=str,
        default="heel_strike",
        choices=["heel_strike", "toe_off", "steady_contact"],
        help="Type of contact event to extract",
    )
    parser.add_argument(
        "--foot",
        type=str,
        default="left",
        choices=["left", "right"],
        help="Which foot to analyze",
    )
    parser.add_argument("--output", type=Path, help="Output JSON file path")
    parser.add_argument(
        "--history", action="store_true", help="Extract full time history"
    )
    parser.add_argument(
        "--start-time", type=float, help="Start time for history extraction (s)"
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=0.01,
        help="Duration for history extraction (s)",
    )

    args = parser.parse_args()

    if args.version:
        # Extract from version directory
        hw1_root = Path(__file__).parent.parent
        version_dir = hw1_root / args.version

        if not version_dir.exists():
            # Try with pattern matching
            matches = list(hw1_root.glob(f"{args.version}*"))
            if matches:
                version_dir = matches[0]
            else:
                raise FileNotFoundError(f"Version directory not found: {args.version}")

        result = extract_from_version(
            version_dir, event_type=args.event, foot=args.foot
        )

        output_path = (
            args.output
            or Path(__file__).parent / "out" / f"{args.version}_contact_forces.json"
        )

    elif args.csv:
        # Extract from specific CSV
        data = load_csv_data(args.csv)

        if args.history and args.start_time is not None:
            # Extract time history
            history = extract_contact_history(
                data, args.foot, args.start_time, args.duration
            )
            result = {
                "source": str(args.csv),
                "foot": history.foot,
                "start_time": history.start_time,
                "end_time": history.end_time,
                "peak_force_N": round(history.peak_force, 2),
                "peak_time": round(history.peak_time, 6),
                "impulse_N_s": round(history.impulse, 4),
                "time_history": {
                    "times": [round(t, 6) for t in history.times],
                    "forces_normal_N": [round(f, 2) for f in history.forces_normal],
                    "forces_tangential_N": [
                        round(f, 2) for f in history.forces_tangential
                    ],
                },
            }
        else:
            # Extract events
            events = detect_contact_events(data, foot=args.foot, event_type=args.event)
            result = {
                "source": str(args.csv),
                "event_type": args.event,
                "foot": args.foot,
                "num_events": len(events),
                "events": [
                    {
                        "time": e.time,
                        "force_normal_N": round(e.force_normal, 2),
                        "force_tangential_N": round(e.force_tangential, 2),
                        "velocity_z_m_s": round(e.body_velocity_z, 4),
                    }
                    for e in events
                ],
            }

        output_path = (
            args.output or Path(__file__).parent / "out" / "contact_forces.json"
        )

    else:
        parser.error("Must specify either --csv or --version")
        return

    # Save results
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)

    print("\n=== Contact Force Extraction ===")
    if "statistics" in result:
        stats = result["statistics"]
        print(f"  Events: {result['num_events']}")
        print(f"  Peak force (avg): {stats['peak_force_avg_N']:.1f} N")
        print(f"  Impact velocity (avg): {stats['velocity_z_avg_m_s']:.4f} m/s")
    elif "peak_force_N" in result:
        print(f"  Peak force: {result['peak_force_N']:.1f} N")
        print(f"  Impulse: {result['impulse_N_s']:.4f} N·s")
        print(f"  Time points: {len(result['time_history']['times'])}")

    print(f"  Saved to: {output_path}")


if __name__ == "__main__":
    main()
