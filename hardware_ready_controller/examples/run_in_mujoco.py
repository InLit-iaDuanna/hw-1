"""
MuJoCo Demo for Hardware-Ready Controller

Easy-to-run simulation demonstrating the hw-1 gait controller in MuJoCo.
Visualizes controller states, computes performance metrics, and saves results.

Usage:
    python run_in_mujoco.py

Requirements:
    - mujoco >= 3.0.0
    - numpy
    - matplotlib
"""

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
import numpy as np

# Add parent directory to path to import controller
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import mujoco
    import mujoco.viewer
except ImportError:
    print("ERROR: mujoco package not found. Install with: pip install mujoco")
    sys.exit(1)

from controller import (
    FSMConfig,
    HardwareReadyController,
    MotorSpec,
    PhaseConfig,
    SensorData,
)


@dataclass
class SimulationMetrics:
    """Performance metrics for controller evaluation"""

    time: List[float] = field(default_factory=list)
    forward_velocity: List[float] = field(default_factory=list)
    mechanical_energy: List[float] = field(default_factory=list)
    hip_height: List[float] = field(default_factory=list)

    # Phase tracking
    phase_history: List[str] = field(default_factory=list)
    step_count: List[int] = field(default_factory=list)

    # Torque tracking
    left_hip_torque: List[float] = field(default_factory=list)
    left_knee_torque: List[float] = field(default_factory=list)
    right_hip_torque: List[float] = field(default_factory=list)
    right_knee_torque: List[float] = field(default_factory=list)

    # Joint angles
    left_hip_angle: List[float] = field(default_factory=list)
    left_knee_angle: List[float] = field(default_factory=list)
    right_hip_angle: List[float] = field(default_factory=list)
    right_knee_angle: List[float] = field(default_factory=list)

    # Contact states
    left_foot_contact: List[bool] = field(default_factory=list)
    right_foot_contact: List[bool] = field(default_factory=list)


class MuJoCoControllerDemo:
    """Wrapper for running hardware controller in MuJoCo simulation"""

    def __init__(self, model_path: str, controller: HardwareReadyController):
        self.model = mujoco.MjModel.from_xml_path(model_path)
        self.data = mujoco.MjData(self.model)
        self.controller = controller

        # Find joint indices
        self.joint_ids = {
            "left_hip": mujoco.mj_name2id(
                self.model, mujoco.mjtObj.mjOBJ_JOINT, "left_hip"
            ),
            "left_knee": mujoco.mj_name2id(
                self.model, mujoco.mjtObj.mjOBJ_JOINT, "left_knee"
            ),
            "right_hip": mujoco.mj_name2id(
                self.model, mujoco.mjtObj.mjOBJ_JOINT, "right_hip"
            ),
            "right_knee": mujoco.mj_name2id(
                self.model, mujoco.mjtObj.mjOBJ_JOINT, "right_knee"
            ),
            "hip_x": mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, "hip_x"),
            "hip_z": mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, "hip_z"),
        }

        # Find actuator indices (if model uses actuators)
        self.has_actuators = self.model.nu > 0
        if self.has_actuators:
            try:
                self.actuator_ids = {
                    "left_hip": mujoco.mj_name2id(
                        self.model, mujoco.mjtObj.mjOBJ_ACTUATOR, "left_hip"
                    ),
                    "left_knee": mujoco.mj_name2id(
                        self.model, mujoco.mjtObj.mjOBJ_ACTUATOR, "left_knee"
                    ),
                    "right_hip": mujoco.mj_name2id(
                        self.model, mujoco.mjtObj.mjOBJ_ACTUATOR, "right_hip"
                    ),
                    "right_knee": mujoco.mj_name2id(
                        self.model, mujoco.mjtObj.mjOBJ_ACTUATOR, "right_knee"
                    ),
                }
            except:
                self.has_actuators = False

        # Find contact sensor sites
        try:
            self.left_foot_geom = mujoco.mj_name2id(
                self.model, mujoco.mjtObj.mjOBJ_GEOM, "left_sole"
            )
            self.right_foot_geom = mujoco.mj_name2id(
                self.model, mujoco.mjtObj.mjOBJ_GEOM, "right_sole"
            )
        except:
            # Fallback to alternative names
            try:
                self.left_foot_geom = mujoco.mj_name2id(
                    self.model, mujoco.mjtObj.mjOBJ_GEOM, "left_foot"
                )
                self.right_foot_geom = mujoco.mj_name2id(
                    self.model, mujoco.mjtObj.mjOBJ_GEOM, "right_foot"
                )
            except:
                print(
                    "Warning: Could not find foot contact geoms. Using dummy contact detection."
                )
                self.left_foot_geom = None
                self.right_foot_geom = None

        # Metrics storage
        self.metrics = SimulationMetrics()

        # Initial pose: standing with slight knee flexion
        self._set_initial_pose()

        print(f"MuJoCo model loaded: {Path(model_path).name}")
        print(f"  Timestep: {self.model.opt.timestep:.4f}s")
        print(f"  Control frequency: {1.0/self.model.opt.timestep:.1f}Hz")
        print(f"  Joints found: {list(self.joint_ids.keys())}")
        print(f"  Using actuators: {self.has_actuators}")

    def _set_initial_pose(self):
        """Set initial robot configuration"""
        # Set hip position
        if "hip_x" in self.joint_ids:
            self.data.qpos[self.joint_ids["hip_x"]] = 0.0
        if "hip_z" in self.joint_ids:
            self.data.qpos[self.joint_ids["hip_z"]] = 0.95  # Standing height

        # Set joint angles (slight knee flexion for stability)
        joint_angles_deg = {
            "left_hip": 0.0,
            "left_knee": 5.0,
            "right_hip": 0.0,
            "right_knee": 5.0,
        }

        for joint_name, angle_deg in joint_angles_deg.items():
            if joint_name in self.joint_ids:
                qpos_idx = self.model.jnt_qposadr[self.joint_ids[joint_name]]
                self.data.qpos[qpos_idx] = np.deg2rad(angle_deg)

        # Forward kinematics to update positions
        mujoco.mj_forward(self.model, self.data)

    def _get_sensor_data(self) -> SensorData:
        """Extract sensor data from MuJoCo simulation state"""

        # Get joint positions and velocities
        def get_joint_state(joint_name):
            joint_id = self.joint_ids[joint_name]
            qpos_idx = self.model.jnt_qposadr[joint_id]
            qvel_idx = self.model.jnt_dofadr[joint_id]
            return self.data.qpos[qpos_idx], self.data.qvel[qvel_idx]

        left_hip_pos, left_hip_vel = get_joint_state("left_hip")
        left_knee_pos, left_knee_vel = get_joint_state("left_knee")
        right_hip_pos, right_hip_vel = get_joint_state("right_hip")
        right_knee_pos, right_knee_vel = get_joint_state("right_knee")

        # Get hip position and velocity (CoM)
        hip_x_vel = 0.0
        hip_height = 0.9
        if "hip_x" in self.joint_ids:
            hip_x_vel = self.data.qvel[self.model.jnt_dofadr[self.joint_ids["hip_x"]]]
        if "hip_z" in self.joint_ids:
            hip_height = self.data.qpos[self.joint_ids["hip_z"]]

        # Detect foot contacts
        left_contact = self._check_contact(self.left_foot_geom)
        right_contact = self._check_contact(self.right_foot_geom)

        return SensorData(
            time=self.data.time,
            left_hip_pos=left_hip_pos,
            left_hip_vel=left_hip_vel,
            left_knee_pos=left_knee_pos,
            left_knee_vel=left_knee_vel,
            right_hip_pos=right_hip_pos,
            right_hip_vel=right_hip_vel,
            right_knee_pos=right_knee_pos,
            right_knee_vel=right_knee_vel,
            left_foot_contact=left_contact,
            right_foot_contact=right_contact,
            hip_height=hip_height,
            hip_velocity_x=hip_x_vel,
        )

    def _check_contact(self, geom_id) -> bool:
        """Check if geom is in contact with ground"""
        if geom_id is None:
            # Fallback: use simple height threshold
            return False

        for i in range(self.data.ncon):
            contact = self.data.contact[i]
            if contact.geom1 == geom_id or contact.geom2 == geom_id:
                # Check contact force magnitude
                force = np.linalg.norm(contact.frame[:3])
                if force > 0.5:  # Threshold for "real" contact
                    return True
        return False

    def _apply_torques(self, left_hip, left_knee, right_hip, right_knee):
        """Apply control torques to the model"""
        if self.has_actuators:
            # Use actuators
            self.data.ctrl[self.actuator_ids["left_hip"]] = left_hip
            self.data.ctrl[self.actuator_ids["left_knee"]] = left_knee
            self.data.ctrl[self.actuator_ids["right_hip"]] = right_hip
            self.data.ctrl[self.actuator_ids["right_knee"]] = right_knee
        else:
            # Direct torque application
            qvel_indices = {
                "left_hip": self.model.jnt_dofadr[self.joint_ids["left_hip"]],
                "left_knee": self.model.jnt_dofadr[self.joint_ids["left_knee"]],
                "right_hip": self.model.jnt_dofadr[self.joint_ids["right_hip"]],
                "right_knee": self.model.jnt_dofadr[self.joint_ids["right_knee"]],
            }

            self.data.qfrc_applied[qvel_indices["left_hip"]] = left_hip
            self.data.qfrc_applied[qvel_indices["left_knee"]] = left_knee
            self.data.qfrc_applied[qvel_indices["right_hip"]] = right_hip
            self.data.qfrc_applied[qvel_indices["right_knee"]] = right_knee

    def _record_metrics(self, sensors: SensorData, control_output):
        """Record timestep data for analysis"""
        self.metrics.time.append(sensors.time)
        self.metrics.forward_velocity.append(sensors.hip_velocity_x)
        self.metrics.mechanical_energy.append(
            control_output.diagnostics.get("mechanical_energy", 0)
        )
        self.metrics.hip_height.append(sensors.hip_height)

        self.metrics.phase_history.append(control_output.phase)
        self.metrics.step_count.append(control_output.diagnostics.get("step_count", 0))

        self.metrics.left_hip_torque.append(control_output.left_hip_torque)
        self.metrics.left_knee_torque.append(control_output.left_knee_torque)
        self.metrics.right_hip_torque.append(control_output.right_hip_torque)
        self.metrics.right_knee_torque.append(control_output.right_knee_torque)

        self.metrics.left_hip_angle.append(np.rad2deg(sensors.left_hip_pos))
        self.metrics.left_knee_angle.append(np.rad2deg(sensors.left_knee_pos))
        self.metrics.right_hip_angle.append(np.rad2deg(sensors.right_hip_pos))
        self.metrics.right_knee_angle.append(np.rad2deg(sensors.right_knee_pos))

        self.metrics.left_foot_contact.append(sensors.left_foot_contact)
        self.metrics.right_foot_contact.append(sensors.right_foot_contact)

    def run_simulation(self, duration_sec: float = 10.0, visualize: bool = True):
        """Run simulation with controller"""
        print(f"\nStarting simulation for {duration_sec:.1f}s...")
        print("Press ESC to stop visualization early\n")

        self.controller.reset()

        if visualize:
            with mujoco.viewer.launch_passive(self.model, self.data) as viewer:
                viewer.cam.distance = 4.0
                viewer.cam.azimuth = 90
                viewer.cam.elevation = -10

                start_time = time.time()
                while self.data.time < duration_sec:
                    # Get sensor readings
                    sensors = self._get_sensor_data()

                    # Compute control
                    control_output = self.controller.compute_control(sensors)

                    # Apply torques
                    self._apply_torques(
                        control_output.left_hip_torque,
                        control_output.left_knee_torque,
                        control_output.right_hip_torque,
                        control_output.right_knee_torque,
                    )

                    # Record metrics
                    self._record_metrics(sensors, control_output)

                    # Step simulation
                    mujoco.mj_step(self.model, self.data)
                    viewer.sync()

                    # Real-time pacing
                    elapsed = time.time() - start_time
                    if elapsed < self.data.time:
                        time.sleep(self.data.time - elapsed)

                    # Status update every second
                    if int(self.data.time) != int(
                        self.data.time - self.model.opt.timestep
                    ):
                        print(
                            f"  t={self.data.time:.1f}s | Phase: {control_output.phase:15s} | "
                            f"Steps: {control_output.diagnostics.get('step_count', 0):2d} | "
                            f"Velocity: {sensors.hip_velocity_x:.3f} m/s"
                        )
        else:
            # Headless simulation
            while self.data.time < duration_sec:
                sensors = self._get_sensor_data()
                control_output = self.controller.compute_control(sensors)

                self._apply_torques(
                    control_output.left_hip_torque,
                    control_output.left_knee_torque,
                    control_output.right_hip_torque,
                    control_output.right_knee_torque,
                )

                self._record_metrics(sensors, control_output)
                mujoco.mj_step(self.model, self.data)

                if int(self.data.time) != int(self.data.time - self.model.opt.timestep):
                    print(
                        f"  t={self.data.time:.1f}s | Phase: {control_output.phase:15s} | "
                        f"Steps: {control_output.diagnostics.get('step_count', 0):2d}"
                    )

        print("\nSimulation complete!")

    def compute_performance_metrics(self) -> Dict:
        """Compute summary performance metrics"""
        metrics = self.metrics

        # Average velocity (after 2s warmup)
        warmup_idx = np.searchsorted(metrics.time, 2.0)
        avg_velocity = (
            np.mean(metrics.forward_velocity[warmup_idx:])
            if len(metrics.forward_velocity) > warmup_idx
            else 0
        )

        # Total distance traveled
        total_distance = (
            self.data.qpos[self.joint_ids["hip_x"]] if "hip_x" in self.joint_ids else 0
        )

        # Step count
        total_steps = metrics.step_count[-1] if metrics.step_count else 0

        # Average step frequency
        sim_duration = metrics.time[-1] - 2.0 if len(metrics.time) > 0 else 0
        step_frequency = total_steps / sim_duration if sim_duration > 0 else 0

        # Energy metrics
        avg_energy = (
            np.mean(metrics.mechanical_energy[warmup_idx:])
            if len(metrics.mechanical_energy) > warmup_idx
            else 0
        )

        # Torque statistics
        torques = np.array(
            [
                metrics.left_hip_torque,
                metrics.left_knee_torque,
                metrics.right_hip_torque,
                metrics.right_knee_torque,
            ]
        )
        rms_torque = np.sqrt(np.mean(torques**2))
        peak_torque = np.max(np.abs(torques))

        # Controller diagnostics
        controller_diag = self.controller.get_diagnostics()

        results = {
            "avg_velocity_m_s": float(avg_velocity),
            "total_distance_m": float(total_distance),
            "total_steps": int(total_steps),
            "step_frequency_hz": float(step_frequency),
            "avg_mechanical_energy_j": float(avg_energy),
            "rms_torque_nm": float(rms_torque),
            "peak_torque_nm": float(peak_torque),
            "saturation_events": controller_diag["saturation_count"],
            "phase_transitions": controller_diag["phase_transitions"],
            "simulation_duration_s": float(metrics.time[-1]) if metrics.time else 0,
        }

        return results

    def plot_results(self, save_path: str = None, show: bool = False):
        """Generate visualization plots"""
        metrics = self.metrics
        time = np.array(metrics.time)

        fig, axes = plt.subplots(3, 2, figsize=(14, 10))
        fig.suptitle(
            "Hardware Controller MuJoCo Simulation Results",
            fontsize=14,
            fontweight="bold",
        )

        # Plot 1: Forward velocity
        ax = axes[0, 0]
        ax.plot(time, metrics.forward_velocity, "b-", linewidth=1.5)
        ax.set_ylabel("Velocity [m/s]")
        ax.set_title("Forward Velocity")
        ax.grid(True, alpha=0.3)
        ax.axhline(
            np.mean(metrics.forward_velocity[len(time) // 4 :]),
            color="r",
            linestyle="--",
            alpha=0.5,
            label="Mean (after warmup)",
        )
        ax.legend()

        # Plot 2: Hip height
        ax = axes[0, 1]
        ax.plot(time, metrics.hip_height, "g-", linewidth=1.5)
        ax.set_ylabel("Height [m]")
        ax.set_title("Hip Height")
        ax.grid(True, alpha=0.3)

        # Plot 3: Joint angles
        ax = axes[1, 0]
        ax.plot(time, metrics.left_hip_angle, "b-", label="Left Hip", alpha=0.7)
        ax.plot(time, metrics.right_hip_angle, "r-", label="Right Hip", alpha=0.7)
        ax.plot(time, metrics.left_knee_angle, "b--", label="Left Knee", alpha=0.7)
        ax.plot(time, metrics.right_knee_angle, "r--", label="Right Knee", alpha=0.7)
        ax.set_ylabel("Angle [deg]")
        ax.set_title("Joint Angles")
        ax.legend(loc="upper right", fontsize=8)
        ax.grid(True, alpha=0.3)

        # Plot 4: Torques
        ax = axes[1, 1]
        ax.plot(time, metrics.left_hip_torque, "b-", label="Left Hip", alpha=0.7)
        ax.plot(time, metrics.right_hip_torque, "r-", label="Right Hip", alpha=0.7)
        ax.plot(time, metrics.left_knee_torque, "b--", label="Left Knee", alpha=0.7)
        ax.plot(time, metrics.right_knee_torque, "r--", label="Right Knee", alpha=0.7)
        ax.set_ylabel("Torque [Nm]")
        ax.set_title("Control Torques")
        ax.legend(loc="upper right", fontsize=8)
        ax.grid(True, alpha=0.3)

        # Plot 5: Phase and contacts
        ax = axes[2, 0]
        # Contact visualization
        left_contact = np.array(metrics.left_foot_contact, dtype=float)
        right_contact = np.array(metrics.right_foot_contact, dtype=float)
        ax.fill_between(
            time,
            0,
            left_contact,
            where=left_contact > 0,
            alpha=0.3,
            color="blue",
            label="Left Contact",
        )
        ax.fill_between(
            time,
            0,
            right_contact,
            where=right_contact > 0,
            alpha=0.3,
            color="red",
            label="Right Contact",
        )
        ax.set_ylabel("Contact State")
        ax.set_xlabel("Time [s]")
        ax.set_title("Foot Contacts")
        ax.legend()
        ax.set_ylim([-0.1, 1.1])
        ax.grid(True, alpha=0.3)

        # Plot 6: Mechanical energy
        ax = axes[2, 1]
        ax.plot(time, metrics.mechanical_energy, "purple", linewidth=1.5)
        ax.set_ylabel("Energy [J]")
        ax.set_xlabel("Time [s]")
        ax.set_title("Mechanical Energy")
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
            print(f"Plot saved to: {save_path}")

        if show:
            plt.show()
        else:
            plt.close(fig)

    def save_results(self, output_dir: str):
        """Save simulation results and metrics"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Save performance metrics
        perf_metrics = self.compute_performance_metrics()
        metrics_file = output_path / "performance_metrics.json"
        with open(metrics_file, "w") as f:
            json.dump(perf_metrics, f, indent=2)
        print(f"Performance metrics saved to: {metrics_file}")

        # Save time-series data
        data_file = output_path / "simulation_data.npz"
        np.savez(
            data_file,
            time=self.metrics.time,
            forward_velocity=self.metrics.forward_velocity,
            hip_height=self.metrics.hip_height,
            left_hip_angle=self.metrics.left_hip_angle,
            left_knee_angle=self.metrics.left_knee_angle,
            right_hip_angle=self.metrics.right_hip_angle,
            right_knee_angle=self.metrics.right_knee_angle,
            left_hip_torque=self.metrics.left_hip_torque,
            left_knee_torque=self.metrics.left_knee_torque,
            right_hip_torque=self.metrics.right_hip_torque,
            right_knee_torque=self.metrics.right_knee_torque,
            left_foot_contact=self.metrics.left_foot_contact,
            right_foot_contact=self.metrics.right_foot_contact,
            mechanical_energy=self.metrics.mechanical_energy,
            phase_history=self.metrics.phase_history,
        )
        print(f"Time-series data saved to: {data_file}")

        # Save plot
        plot_file = output_path / "simulation_plots.png"
        self.plot_results(save_path=str(plot_file), show=False)

        # Print summary
        print("\n" + "=" * 60)
        print("PERFORMANCE SUMMARY")
        print("=" * 60)
        print(f"Average velocity:       {perf_metrics['avg_velocity_m_s']:.3f} m/s")
        print(f"Total distance:         {perf_metrics['total_distance_m']:.2f} m")
        print(f"Total steps:            {perf_metrics['total_steps']}")
        print(f"Step frequency:         {perf_metrics['step_frequency_hz']:.2f} Hz")
        print(
            f"Average energy:         {perf_metrics['avg_mechanical_energy_j']:.2f} J"
        )
        print(f"RMS torque:             {perf_metrics['rms_torque_nm']:.3f} Nm")
        print(f"Peak torque:            {perf_metrics['peak_torque_nm']:.3f} Nm")
        print(f"Phase transitions:      {perf_metrics['phase_transitions']}")
        print(f"Saturation events:      {perf_metrics['saturation_events']}")
        print("=" * 60)


def create_default_controller() -> HardwareReadyController:
    """Create controller with default V13.7 parameters"""
    print("Creating controller with default parameters...")

    hip_motor = MotorSpec()
    knee_motor = MotorSpec()

    fsm_config = FSMConfig(
        stance_early=PhaseConfig(
            k_E=0.0, k_PD=30.0, tau_max=4.0, kd=6.0, E_target=52.66
        ),
        stance_late=PhaseConfig(
            k_E=0.0, k_PD=30.0, tau_max=4.0, kd=6.0, E_target=52.66
        ),
        swing_thrust=PhaseConfig(
            k_E=7.5, k_PD=10.0, tau_max=4.0, kd=6.0, E_target=52.66
        ),
        swing_retract=PhaseConfig(
            k_E=0.0, k_PD=30.0, tau_max=3.0, kd=6.0, E_target=52.66
        ),
    )

    controller = HardwareReadyController(
        hip_motor=hip_motor,
        knee_motor=knee_motor,
        fsm_config=fsm_config,
        total_mass_kg=6.08,
        compensate_friction=True,
    )

    return controller


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Run the hardware controller MuJoCo demo."
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=2.0,
        help="Simulation duration in seconds. Defaults to a short smoke run.",
    )
    parser.add_argument(
        "--visualize",
        action="store_true",
        help="Open the interactive MuJoCo viewer. Headless mode is the default.",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("HW-1 Hardware Controller - MuJoCo Demo")
    print("=" * 60)

    # Find model file
    script_dir = Path(__file__).parent.parent.parent
    model_path = (
        script_dir
        / "v13_7_friction_compensation"
        / "out"
        / "v13_7_models"
        / "friction_comp_walker.xml"
    )

    if not model_path.exists():
        print(f"\nModel file not found: {model_path}")
        print("Please provide the correct path to the MuJoCo XML model.")
        return

    # Create controller
    controller = create_default_controller()

    # Create demo
    demo = MuJoCoControllerDemo(str(model_path), controller)

    # Run simulation
    demo.run_simulation(duration_sec=args.duration, visualize=args.visualize)

    # Save results
    output_dir = Path(__file__).parent / "demo_results"
    demo.save_results(str(output_dir))

    print("\nDemo complete! Results saved to:", output_dir.absolute())


if __name__ == "__main__":
    main()
