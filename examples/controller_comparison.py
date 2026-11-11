"""Controller comparison: Passive, PD, FSM v13.6, and FSM v13.7 side-by-side.

Demonstrates progressive controller complexity and performance:
1. Passive (no control) - baseline dynamics
2. PD control - simple position tracking
3. FSM v13.6 - event-driven 4-phase gait control
4. FSM v13.7 - v13.6 + L1 motor dynamics + friction compensation

Outputs:
- Side-by-side metrics table
- Comparison plots (distance, CoT, success rate)
- Detailed HTML report with phase timelines
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import mujoco
import numpy as np

# Setup paths
ROOT = Path(__file__).resolve().parent
HW1_ROOT = ROOT.parent
V10_DIR = HW1_ROOT / "v10_rolling_foot_biomimetic_gait"
V136_DIR = HW1_ROOT / "v13_6_event_driven_fsm"
V137_DIR = HW1_ROOT / "v13_7_friction_compensation"
V14_DIR = HW1_ROOT / "v14_passive_arms"

sys.path.insert(0, str(V10_DIR))
sys.path.insert(0, str(V136_DIR))
sys.path.insert(0, str(V137_DIR))
sys.path.insert(0, str(V14_DIR))
sys.path.insert(0, str(HW1_ROOT))

from simulate_rolling_foot_gait_v10 import (
    MODEL_PATH,
    SUCCESS_FORWARD,
    SUCCESS_TIME,
    SUCCESS_TOUCHDOWNS,
    RollingFootParams as V10Params,
    classify_failure,
    contact_flags,
    initialize as initialize_v10,
    write_model,
)
from simulate_passive_arms_v14 import (
    initialize as initialize_v14,
)
from simulate_v13_6 import V136Params, _mechanical_energy, control_v136
from simulate_v13_7 import V137Params, MODEL_PATH as V137_MODEL_PATH, write_model_v137

from common.comparison_tool import ComparisonTool, ControllerResult
from common.controllers import PassiveController, PDController
from common.motor_dynamics import PRESETS as MOTOR_PRESETS, L1MotorActuator
from common.simulation_framework import (
    Callback,
    Controller,
    EnergyStats,
)
from common.simulation_runner import SimulationRunner

OUT_DIR = ROOT / "controller_comparison_out"
OUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# Controller Wrappers
# ============================================================================


class PassiveControllerWrapper(Controller):
    """Passive controller - no actuation, natural dynamics only."""

    def __init__(self, base_params: V10Params):
        self.base_params = base_params
        self.passive = PassiveController()

    def compute_control(
        self,
        model: mujoco.MjModel,
        data: mujoco.MjData,
        t: float,
        context: dict[str, Any],
    ) -> tuple[np.ndarray, dict[str, Any]]:
        """Return zero torques for all actuators."""
        tau = np.zeros(4)  # [l_hip, l_knee, r_hip, r_knee]

        info = {
            "mode": "passive",
            "left_phase": "none",
            "right_phase": "none",
        }

        return tau, info


class PDControllerWrapper(Controller):
    """Simple PD controller with fixed targets."""

    def __init__(self, base_params: V10Params, kp: float = 50.0, kd: float = 10.0):
        self.base_params = base_params
        self.kp = kp
        self.kd = kd
        self.hip_controller = PDController(kp=kp, kd=kd, torque_limit=10.0)
        self.knee_controller = PDController(kp=kp * 0.5, kd=kd * 0.5, torque_limit=5.0)

        # Fixed target angles (deg -> rad)
        self.hip_target = np.radians(0.0)  # Neutral hip
        self.knee_target = np.radians(0.0)  # Straight knee

    def compute_control(
        self,
        model: mujoco.MjModel,
        data: mujoco.MjData,
        t: float,
        context: dict[str, Any],
    ) -> tuple[np.ndarray, dict[str, Any]]:
        """Compute PD control for all joints."""
        # Joint indices
        l_hip_id = model.joint("left_hip").id
        l_knee_id = model.joint("left_knee").id
        r_hip_id = model.joint("right_hip").id
        r_knee_id = model.joint("right_knee").id

        # Get joint states
        l_hip_q = data.qpos[l_hip_id]
        l_hip_qd = data.qvel[l_hip_id]
        l_knee_q = data.qpos[l_knee_id]
        l_knee_qd = data.qvel[l_knee_id]
        r_hip_q = data.qpos[r_hip_id]
        r_hip_qd = data.qvel[r_hip_id]
        r_knee_q = data.qpos[r_knee_id]
        r_knee_qd = data.qvel[r_knee_id]

        # Compute control torques
        l_hip_tau = self.hip_controller.compute_torque(
            l_hip_q, l_hip_qd, self.hip_target
        )
        l_knee_tau = self.knee_controller.compute_torque(
            l_knee_q, l_knee_qd, self.knee_target
        )
        r_hip_tau = self.hip_controller.compute_torque(
            r_hip_q, r_hip_qd, self.hip_target
        )
        r_knee_tau = self.knee_controller.compute_torque(
            r_knee_q, r_knee_qd, self.knee_target
        )

        tau = np.array([l_hip_tau, l_knee_tau, r_hip_tau, r_knee_tau])

        info = {
            "mode": "pd",
            "left_phase": "tracking",
            "right_phase": "tracking",
            "kp": self.kp,
            "kd": self.kd,
        }

        return tau, info


class V136ControllerWrapper(Controller):
    """V13.6 FSM controller wrapper."""

    def __init__(self, params: V136Params):
        self.params = params

    def compute_control(
        self,
        model: mujoco.MjModel,
        data: mujoco.MjData,
        t: float,
        context: dict[str, Any],
    ) -> tuple[np.ndarray, dict[str, Any]]:
        """Compute V13.6 FSM control."""
        support_foot = context.get("support_foot", "left")
        burst_start_t = context.get("burst_start_t", 0.0)
        E_current = _mechanical_energy(self.params.base, data)

        # V13.6 FSM control
        tau_result = control_v136(
            self.params, data, t, support_foot, burst_start_t, E_current
        )
        l_hip, l_knee, r_hip, r_knee = (
            tau_result[0],
            tau_result[1],
            tau_result[2],
            tau_result[3],
        )
        mode_label = tau_result[4]
        left_phase = tau_result[5]
        right_phase = tau_result[6]

        tau = np.array([l_hip, l_knee, r_hip, r_knee])

        info = {
            "mode": mode_label,
            "left_phase": left_phase,
            "right_phase": right_phase,
            "energy": E_current,
        }

        return tau, info


class V137ControllerWrapper(Controller):
    """V13.7 FSM + L1 motor + friction compensation wrapper."""

    def __init__(self, params: V137Params):
        self.params = params

        # Motor actuators
        self.actuators = {
            "left_hip": L1MotorActuator(params.hip_motor),
            "left_knee": L1MotorActuator(params.knee_motor),
            "right_hip": L1MotorActuator(params.hip_motor),
            "right_knee": L1MotorActuator(params.knee_motor),
        }

    def compute_control(
        self,
        model: mujoco.MjModel,
        data: mujoco.MjData,
        t: float,
        context: dict[str, Any],
    ) -> tuple[np.ndarray, dict[str, Any]]:
        """Compute V13.7 FSM control with motor dynamics and friction compensation."""
        support_foot = context.get("support_foot", "left")
        burst_start_t = context.get("burst_start_t", 0.0)
        E_current = _mechanical_energy(self.params.fsm.base, data)

        # V13.6.1 FSM control (base control law)
        tau_result = control_v136(
            self.params.fsm, data, t, support_foot, burst_start_t, E_current
        )
        tau_desired = np.array(
            [tau_result[0], tau_result[1], tau_result[2], tau_result[3]]
        )
        mode_label = tau_result[4]
        left_phase = tau_result[5]
        right_phase = tau_result[6]

        # Get joint velocities
        l_hip_id = model.joint("left_hip").id
        l_knee_id = model.joint("left_knee").id
        r_hip_id = model.joint("right_hip").id
        r_knee_id = model.joint("right_knee").id

        qd = np.array(
            [
                data.qvel[l_hip_id],
                data.qvel[l_knee_id],
                data.qvel[r_hip_id],
                data.qvel[r_knee_id],
            ]
        )

        # Apply motor dynamics with friction compensation
        tau_motor = np.zeros(4)
        actuator_names = ["left_hip", "left_knee", "right_hip", "right_knee"]

        for i, name in enumerate(actuator_names):
            actuator = self.actuators[name]
            # Motor dynamics handles torque saturation and coulomb friction internally
            tau_motor[i], _ = actuator.compute_actual_torque(tau_desired[i], qd[i])

        info = {
            "mode": mode_label,
            "left_phase": left_phase,
            "right_phase": right_phase,
            "energy": E_current,
            "tau_desired": tau_desired.copy(),
            "tau_motor": tau_motor.copy(),
        }

        return tau_motor, info


# ============================================================================
# Simulation Callback
# ============================================================================


class ComparisonCallback(Callback):
    """Unified callback for all controllers."""

    def __init__(
        self, controller: Controller, base_params: V10Params, controller_type: str
    ):
        self.controller = controller
        self.base_params = base_params
        self.controller_type = controller_type

        # Initialize subsystems
        self.energy = EnergyStats()
        self.rows = []  # Simple list to store data rows

        # Simple contact tracking
        self.touchdown_count = 0
        self.alternation_count = 0
        self.last_left_contact = False
        self.last_right_contact = False

        # FSM state tracking
        self.support_foot = "left"
        self.burst_start_t = 0.0
        self.context: dict[str, Any] = {}

        # Simple failure tracking
        self.is_failed = False
        self.failure_reason = "none"

    def on_step(
        self,
        model: mujoco.MjModel,
        data: mujoco.MjData,
        t: float,
        step: int,
    ) -> None:
        """Called at each simulation step."""
        # Update context
        self.context = {
            "support_foot": self.support_foot,
            "burst_start_t": self.burst_start_t,
        }

        # Compute control
        tau, info = self.controller.compute_control(model, data, t, self.context)

        # Apply control to actuators
        data.ctrl[:] = tau

        # Step simulation
        mujoco.mj_step(model, data)

        # Update contact state (simple touchdown detection)
        left_contact, right_contact = contact_flags(model, data)

        # Detect touchdowns (rising edge)
        left_touchdown = left_contact and not self.last_left_contact
        right_touchdown = right_contact and not self.last_right_contact

        if left_touchdown or right_touchdown:
            self.touchdown_count += 1

            # Detect alternations (foot switching)
            if left_touchdown and self.support_foot == "right":
                self.alternation_count += 1
            elif right_touchdown and self.support_foot == "left":
                self.alternation_count += 1

        self.last_left_contact = left_contact
        self.last_right_contact = right_contact

        # Update energy stats
        E = _mechanical_energy(self.base_params, data)
        self.energy.update(E, model.opt.timestep)

        # Get phase info
        left_phase = info.get("left_phase", "unknown")
        right_phase = info.get("right_phase", "unknown")

        # Event detection: touchdown triggers support foot switch (for FSM controllers)
        if self.controller_type in ["v136", "v137"]:
            if left_touchdown:
                self.support_foot = "right"
                self.burst_start_t = t
            elif right_touchdown:
                self.support_foot = "left"
                self.burst_start_t = t

        # Get CoM position
        hip_body_id = model.body("hip").id
        x_hip = data.xpos[hip_body_id, 0]

        # Record metrics
        self.rows.append(
            {
                "t": t,
                "x_hip": x_hip,
                "energy": E,
                "mode": info.get("mode", "none"),
                "left_phase": left_phase,
                "right_phase": right_phase,
                "left_contact": left_contact,
                "right_contact": right_contact,
                "touchdowns": self.touchdown_count,
            }
        )

        # Simple failure detection
        if not self.is_failed:
            # Check for fall (hip height too low)
            hip_z = data.xpos[hip_body_id, 2]
            if hip_z < 0.3:
                self.is_failed = True
                self.failure_reason = "fall"
            # Check for backward motion
            elif x_hip < -0.5:
                self.is_failed = True
                self.failure_reason = "backward"

    def get_summary(self) -> dict[str, Any]:
        """Return summary metrics."""
        if not self.rows:
            return {}

        final_x = self.rows[-1]["x_hip"]
        final_t = self.rows[-1]["t"]
        total_energy = self.energy.positive_input_energy
        cot = (
            total_energy / (final_x * self.base_params.hip_mass * 9.81)
            if final_x > 0.1
            else np.inf
        )

        # Determine success
        success = (
            final_x >= SUCCESS_FORWARD
            and final_t >= SUCCESS_TIME
            and self.touchdown_count >= SUCCESS_TOUCHDOWNS
            and not self.is_failed
        )

        return {
            "forward_distance": final_x,
            "simulation_time": final_t,
            "touchdowns": self.touchdown_count,
            "total_energy": total_energy,
            "cot": cot,
            "success": success,
            "failure_reason": self.failure_reason if self.is_failed else "none",
            "alternations": self.alternation_count,
        }


# ============================================================================
# Run Single Controller
# ============================================================================


def run_controller(
    controller_name: str,
    controller: Controller,
    base_params: V10Params,
    controller_type: str,
    model_path: Path,
    duration: float = 20.0,
    render: bool = False,
    use_v14_init: bool = False,
) -> ControllerResult:
    """Run simulation with a single controller."""
    print(f"\n{'='*60}")
    print(f"Running: {controller_name}")
    print(f"{'='*60}")

    # Load model
    model = mujoco.MjModel.from_xml_path(str(model_path))
    data = mujoco.MjData(model)

    # Initialize with appropriate function
    if use_v14_init:
        initialize_v14(model, data, base_params)
    else:
        initialize_v10(model, data, base_params)

    # Create callback
    callback = ComparisonCallback(controller, base_params, controller_type)

    # Create runner
    runner = SimulationRunner(
        model=model,
        data=data,
        callbacks=[callback],
    )

    # Run simulation
    result = runner.run(duration=duration)

    # Get summary
    summary = callback.get_summary()

    # Print results
    print(f"\nResults for {controller_name}:")
    print(f"  Forward distance:  {summary['forward_distance']:.3f} m")
    print(f"  Simulation time:   {summary['simulation_time']:.2f} s")
    print(f"  Touchdowns:        {summary['touchdowns']}")
    print(f"  Alternations:      {summary['alternations']}")
    print(f"  Total energy:      {summary['total_energy']:.2f} J")
    print(f"  CoT:               {summary['cot']:.4f}")
    print(f"  Success:           {summary['success']}")
    if not summary["success"]:
        print(f"  Failure reason:    {summary['failure_reason']}")

    # Extract time series
    rows = callback.rows
    time_array = np.array([r["t"] for r in rows])
    energy_array = np.array([r["energy"] for r in rows])
    x_array = np.array([r["x_hip"] for r in rows])

    # Create result
    result = ControllerResult(
        name=controller_name,
        metrics={
            "forward_distance": summary["forward_distance"],
            "cot": summary["cot"],
            "total_energy": summary["total_energy"],
            "touchdowns": summary["touchdowns"],
            "alternations": summary["alternations"],
            "success_rate": 1.0 if summary["success"] else 0.0,
        },
        time_series={
            "time": time_array,
            "energy": energy_array,
            "position": x_array,
        },
        metadata={
            "controller_type": callback.controller_type,
            "duration": duration,
            "failure_reason": (
                summary["failure_reason"] if not summary["success"] else None
            ),
        },
    )

    return result


# ============================================================================
# Main Comparison
# ============================================================================


def main():
    """Run controller comparison."""
    import argparse

    parser = argparse.ArgumentParser(description="Compare controllers side-by-side")
    parser.add_argument(
        "--duration", type=float, default=20.0, help="Simulation duration (s)"
    )
    parser.add_argument("--render", action="store_true", help="Enable rendering")
    parser.add_argument("--slope", type=float, default=0.0, help="Slope angle (deg)")
    args = parser.parse_args()

    print("Controller Comparison: Passive vs PD vs FSM v13.6 vs FSM v13.7")
    print("=" * 60)

    # Base parameters (V10)
    v10_params = V10Params(slope_deg=args.slope)

    # V13.6 parameters
    v136_params = V136Params(base=v10_params)

    # V13.7 parameters (needs PassiveArmsParams base)
    from simulate_passive_arms_v14 import PassiveArmsParams

    v14_base = PassiveArmsParams(
        hip_mass=v10_params.hip_mass,
        torso_mass=v10_params.torso_mass,
        slope_deg=v10_params.slope_deg,
    )
    v137_params = V137Params(
        base=v14_base,
        fsm=v136_params,
        hip_motor=MOTOR_PRESETS["mx64ar"],
        knee_motor=MOTOR_PRESETS["mx64ar"],
    )

    # Write models
    v10_model_path = OUT_DIR / "model_v10.xml"
    v137_model_path = OUT_DIR / "model_v137.xml"
    write_model(v10_params, v10_model_path)
    write_model_v137(v137_params, v137_model_path)

    # Create comparison tool
    comparison = ComparisonTool(
        name="Controller Comparison",
        output_dir=OUT_DIR,
    )

    # ========================================================================
    # 1. Passive Controller
    # ========================================================================
    passive_controller = PassiveControllerWrapper(v10_params)
    passive_result = run_controller(
        "Passive (No Control)",
        passive_controller,
        v10_params,
        "passive",
        v10_model_path,
        duration=args.duration,
        render=args.render,
    )
    comparison.add_result(passive_result)

    # ========================================================================
    # 2. PD Controller
    # ========================================================================
    pd_controller = PDControllerWrapper(v10_params, kp=50.0, kd=10.0)
    pd_result = run_controller(
        "PD Control (kp=50, kd=10)",
        pd_controller,
        v10_params,
        "pd",
        v10_model_path,
        duration=args.duration,
        render=args.render,
    )
    comparison.add_result(pd_result)

    # ========================================================================
    # 3. V13.6 FSM Controller
    # ========================================================================
    v136_controller = V136ControllerWrapper(v136_params)
    v136_result = run_controller(
        "FSM v13.6 (Event-Driven)",
        v136_controller,
        v10_params,
        "v136",
        v10_model_path,
        duration=args.duration,
        render=args.render,
    )
    comparison.add_result(v136_result)

    # ========================================================================
    # 4. V13.7 FSM + Motor + Friction Controller
    # ========================================================================
    v137_controller = V137ControllerWrapper(v137_params)
    v137_result = run_controller(
        "FSM v13.7 (Motor + Friction)",
        v137_controller,
        v14_base,
        "v137",
        v137_model_path,
        duration=args.duration,
        render=args.render,
        use_v14_init=True,
    )
    comparison.add_result(v137_result)

    # ========================================================================
    # Generate Comparison Report
    # ========================================================================
    print(f"\n{'='*60}")
    print("COMPARISON SUMMARY")
    print(f"{'='*60}\n")

    # Print comparison table
    comparison.generate_comparison_table()

    # Generate plots
    print("\nGenerating comparison plots...")
    comparison.plot_metrics_comparison(
        metrics=["forward_distance", "cot", "success_rate"],
    )
    plt.savefig(OUT_DIR / "metrics_comparison.png", dpi=150)
    plt.close()

    # Plot time series
    fig, axes = plt.subplots(2, 1, figsize=(12, 8))

    for result in comparison.results:
        time = result.time_series.get("time", np.array([]))
        position = result.time_series.get("position", np.array([]))
        energy = result.time_series.get("energy", np.array([]))

        if len(time) > 0:
            axes[0].plot(time, position, label=result.name, linewidth=2)
            axes[1].plot(time, energy, label=result.name, linewidth=2)

    axes[0].set_xlabel("Time (s)")
    axes[0].set_ylabel("Forward Distance (m)")
    axes[0].set_title("Forward Distance vs Time")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    axes[1].set_xlabel("Time (s)")
    axes[1].set_ylabel("Mechanical Energy (J)")
    axes[1].set_title("Mechanical Energy vs Time")
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(OUT_DIR / "time_series_comparison.png", dpi=150)
    print(f"  Saved: {OUT_DIR / 'time_series_comparison.png'}")

    # Export to formats
    comparison.export_to_json(OUT_DIR / "comparison_results.json")
    comparison.export_to_html(OUT_DIR / "comparison_report.html")

    print(f"\nAll outputs saved to: {OUT_DIR}")
    print("\nFiles generated:")
    print(f"  - metrics_comparison.png")
    print(f"  - time_series_comparison.png")
    print(f"  - comparison_table.csv")
    print(f"  - comparison_results.json")
    print(f"  - comparison_report.html")


if __name__ == "__main__":
    main()
