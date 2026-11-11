"""
Visualize Control Policies for Algorithm Comparison
Generates publication-quality figures comparing torque profiles, phase portraits,
Poincare sections, and control effort across different algorithms.
"""

import sys
from pathlib import Path
from typing import Dict

import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Ellipse

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Set publication style
plt.rcParams.update(
    {
        "font.size": 10,
        "font.family": "serif",
        "axes.labelsize": 11,
        "axes.titlesize": 12,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 9,
        "figure.titlesize": 13,
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "axes.grid": True,
        "grid.alpha": 0.3,
        "lines.linewidth": 1.5,
    }
)

# Color palette for algorithms
ALGORITHM_COLORS = {
    "V10_PD": "#1f77b4",  # Blue
    "V13_FSM": "#ff7f0e",  # Orange
    "RL_PPO": "#2ca02c",  # Green
    "RL_SAC": "#d62728",  # Red
    "Trajectory_Opt": "#9467bd",  # Purple
    "Virtual_Constraints": "#8c564b",  # Brown
}


class PolicyDataCollector:
    """Collect trajectory data for policy visualization"""

    def __init__(self, model_path: str):
        """Initialize with MuJoCo model"""
        import mujoco
        from benchmark_suite import (
            V10PDController,
            V13FSMController,
            VirtualConstraintsController,
        )

        self.model = mujoco.MjModel.from_xml_path(model_path)
        self.data = mujoco.MjData(self.model)
        self.mujoco = mujoco

        # Initialize controllers
        self.controllers = {
            "V10_PD": V10PDController(),
            "V13_FSM": V13FSMController(),
            "Virtual_Constraints": VirtualConstraintsController(),
        }

        # Try to load RL models
        self._load_rl_models()

    def _load_rl_models(self):
        """Load RL models if available"""
        try:
            from stable_baselines3 import PPO, SAC

            base_dir = Path(__file__).parent

            ppo_path = base_dir / "trained_models" / "ppo_biped_final.zip"
            sac_path = base_dir / "trained_models" / "sac_biped_final.zip"

            if ppo_path.exists():
                self.controllers["RL_PPO"] = PPO.load(str(ppo_path))
            if sac_path.exists():
                self.controllers["RL_SAC"] = SAC.load(str(sac_path))
        except ImportError:
            print("Warning: RL models not available")

    def reset_simulation(self):
        """Reset simulation to initial state"""
        self.mujoco.mj_resetData(self.model, self.data)
        self.data.qpos[2] = 0.9  # Height
        self.data.qpos[7] = 0.1  # Left hip
        self.data.qpos[8] = -0.2  # Left knee
        self.data.qpos[9] = -0.1  # Right hip
        self.data.qpos[10] = -0.2  # Right knee

    def get_contact_forces(self) -> np.ndarray:
        """Get contact forces for both feet"""
        left_contact = 0.0
        right_contact = 0.0

        for i in range(self.data.ncon):
            if i < self.data.ncon // 2:
                left_contact += abs(self.data.contact[i].dist)
            else:
                right_contact += abs(self.data.contact[i].dist)

        return np.array([max(left_contact, 0), max(right_contact, 0)])

    def collect_trajectory(self, algorithm: str, num_steps: int = 1000) -> Dict:
        """Collect full trajectory data for an algorithm"""
        print(f"Collecting trajectory for {algorithm}...")

        self.reset_simulation()
        controller = self.controllers.get(algorithm)

        if controller is None:
            print(f"Warning: {algorithm} not available")
            return None

        # Storage
        trajectory = {
            "time": [],
            "qpos": [],
            "qvel": [],
            "torques": [],
            "contact": [],
            "phase": [],
        }

        dt = self.model.opt.timestep

        for step in range(num_steps):
            # Get contact forces
            contact_forces = self.get_contact_forces()

            # Get action from controller
            if algorithm in ["RL_PPO", "RL_SAC"]:
                obs = np.concatenate(
                    [self.data.qpos[:11], self.data.qvel[:10], contact_forces]
                )
                action, _ = controller.predict(obs, deterministic=True)
            elif algorithm == "Virtual_Constraints" or algorithm == "V13_FSM":
                action = controller.get_action(
                    self.data.qpos, self.data.qvel, contact_forces
                )
            else:  # V10_PD
                phase = (step % 100) / 100.0  # Approximate phase
                action = controller.get_action(self.data.qpos, self.data.qvel, phase)

            # Store data
            trajectory["time"].append(step * dt)
            trajectory["qpos"].append(self.data.qpos.copy())
            trajectory["qvel"].append(self.data.qvel.copy())
            trajectory["torques"].append(action.copy())
            trajectory["contact"].append(contact_forces.copy())

            # Estimate phase from contacts
            if contact_forces[0] > contact_forces[1]:
                phase_est = 0.0
            else:
                phase_est = 0.5
            trajectory["phase"].append(phase_est)

            # Apply action and step
            self.data.ctrl[:] = action
            self.mujoco.mj_step(self.model, self.data)

            # Check for fall
            if self.data.qpos[2] < 0.3:
                print(f"  {algorithm} fell at step {step}")
                break

        # Convert to numpy arrays
        for key in trajectory:
            trajectory[key] = np.array(trajectory[key])

        return trajectory


class PolicyVisualizer:
    """Generate publication-quality visualizations of control policies"""

    def __init__(self, output_dir: str = None):
        """Initialize visualizer"""
        if output_dir is None:
            self.output_dir = Path(__file__).parent / "figures"
        else:
            self.output_dir = Path(output_dir)

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.trajectories = {}

    def load_trajectories(self, trajectories: Dict[str, Dict]):
        """Load trajectory data"""
        self.trajectories = trajectories

    def plot_torque_profiles(self):
        """Plot torque profiles over gait cycle for each algorithm"""
        print("Generating torque profile comparison...")

        fig = plt.figure(figsize=(12, 8))
        gs = gridspec.GridSpec(2, 2, hspace=0.3, wspace=0.3)

        joint_names = ["Left Hip", "Left Knee", "Right Hip", "Right Knee"]

        for idx, joint_name in enumerate(joint_names):
            ax = fig.add_subplot(gs[idx // 2, idx % 2])

            for algo_name, traj in self.trajectories.items():
                if traj is None:
                    continue

                torques = traj["torques"][:, idx]
                time = traj["time"]

                # Normalize time to gait cycles
                gait_cycle_duration = 1.0  # seconds
                normalized_time = (
                    (time % gait_cycle_duration) / gait_cycle_duration * 100
                )

                # Plot torque profile
                color = ALGORITHM_COLORS.get(algo_name, "gray")
                ax.plot(
                    normalized_time[:500],
                    torques[:500],
                    label=algo_name.replace("_", " "),
                    color=color,
                    alpha=0.8,
                )

            ax.set_xlabel("Gait Cycle (%)")
            ax.set_ylabel("Torque (Nm)")
            ax.set_title(joint_name)
            ax.legend(loc="best", framealpha=0.9)
            ax.set_xlim(0, 100)
            ax.axhline(y=0, color="k", linestyle="--", linewidth=0.8, alpha=0.3)

        fig.suptitle("Torque Profiles Over Gait Cycle", fontsize=14, fontweight="bold")

        output_path = self.output_dir / "torque_profiles.png"
        plt.savefig(output_path)
        print(f"  Saved: {output_path}")
        plt.close()

    def plot_phase_portraits(self):
        """Plot phase portraits (joint angle vs velocity) comparison"""
        print("Generating phase portrait comparison...")

        fig = plt.figure(figsize=(14, 10))
        gs = gridspec.GridSpec(2, 2, hspace=0.3, wspace=0.3)

        joint_names = ["Left Hip", "Left Knee", "Right Hip", "Right Knee"]
        joint_indices = [0, 1, 2, 3]  # Indices in qpos[7:11] and qvel[6:10]

        for idx, (joint_name, j_idx) in enumerate(zip(joint_names, joint_indices)):
            ax = fig.add_subplot(gs[idx // 2, idx % 2])

            for algo_name, traj in self.trajectories.items():
                if traj is None:
                    continue

                # Extract joint angles and velocities
                angles = traj["qpos"][:, 7 + j_idx]
                velocities = traj["qvel"][:, 6 + j_idx]

                color = ALGORITHM_COLORS.get(algo_name, "gray")
                ax.plot(
                    angles,
                    velocities,
                    label=algo_name.replace("_", " "),
                    color=color,
                    alpha=0.7,
                    linewidth=1.2,
                )

            ax.set_xlabel("Joint Angle (rad)")
            ax.set_ylabel("Joint Velocity (rad/s)")
            ax.set_title(f"{joint_name} Phase Portrait")
            ax.legend(loc="best", framealpha=0.9, fontsize=8)
            ax.axhline(y=0, color="k", linestyle="--", linewidth=0.8, alpha=0.3)
            ax.axvline(x=0, color="k", linestyle="--", linewidth=0.8, alpha=0.3)

        fig.suptitle("Phase Portraits Comparison", fontsize=14, fontweight="bold")

        output_path = self.output_dir / "phase_portraits.png"
        plt.savefig(output_path)
        print(f"  Saved: {output_path}")
        plt.close()

    def plot_poincare_sections(self):
        """Plot Poincare sections overlay (state at heel strikes)"""
        print("Generating Poincare sections...")

        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        axes = axes.flatten()

        state_pairs = [
            ("Left Hip Angle", "Left Hip Velocity", 7, 6),
            ("Left Knee Angle", "Left Knee Velocity", 8, 7),
            ("Right Hip Angle", "Right Hip Velocity", 9, 8),
            ("Right Knee Angle", "Right Knee Velocity", 10, 9),
        ]

        for idx, (x_label, y_label, q_idx, v_idx) in enumerate(state_pairs):
            ax = axes[idx]

            for algo_name, traj in self.trajectories.items():
                if traj is None:
                    continue

                # Detect heel strikes (contact force threshold crossings)
                contacts = traj["contact"]
                if contacts.shape[0] == 0:
                    continue

                # Left foot contact increases
                left_contact = contacts[:, 0]
                heel_strikes = []

                for i in range(1, len(left_contact) - 1):
                    if left_contact[i - 1] < 5 and left_contact[i] > 10:
                        heel_strikes.append(i)

                if len(heel_strikes) < 2:
                    continue

                # Extract states at heel strikes
                x_coords = traj["qpos"][heel_strikes, q_idx]
                y_coords = traj["qvel"][heel_strikes, v_idx]

                color = ALGORITHM_COLORS.get(algo_name, "gray")
                ax.scatter(
                    x_coords,
                    y_coords,
                    label=algo_name.replace("_", " "),
                    color=color,
                    alpha=0.7,
                    s=50,
                    edgecolors="white",
                    linewidths=0.5,
                )

                # Add ellipse to show cluster
                if len(x_coords) > 2:
                    try:
                        cov = np.cov(x_coords, y_coords)
                        lambda_, v = np.linalg.eig(cov)
                        lambda_ = np.sqrt(lambda_)

                        ellipse = Ellipse(
                            xy=(np.mean(x_coords), np.mean(y_coords)),
                            width=lambda_[0] * 4,
                            height=lambda_[1] * 4,
                            angle=np.rad2deg(np.arctan2(v[1, 0], v[0, 0])),
                            facecolor="none",
                            edgecolor=color,
                            linewidth=1.5,
                            linestyle="--",
                            alpha=0.5,
                        )
                        ax.add_patch(ellipse)
                    except:
                        pass  # Skip if covariance is singular

            ax.set_xlabel(x_label)
            ax.set_ylabel(y_label)
            ax.set_title(f"{x_label} at Heel Strike")
            ax.legend(loc="best", framealpha=0.9, fontsize=8)
            ax.grid(True, alpha=0.3)

        fig.suptitle(
            "Poincaré Sections (State at Heel Strikes)", fontsize=14, fontweight="bold"
        )
        plt.tight_layout()

        output_path = self.output_dir / "poincare_sections.png"
        plt.savefig(output_path)
        print(f"  Saved: {output_path}")
        plt.close()

    def plot_control_effort(self):
        """Plot control effort (RMS torque) bar chart"""
        print("Generating control effort comparison...")

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

        algorithms = []
        rms_torques = []
        peak_torques = []
        colors = []

        for algo_name, traj in self.trajectories.items():
            if traj is None:
                continue

            torques = traj["torques"]

            # Compute RMS torque (overall control effort)
            rms = np.sqrt(np.mean(torques**2))

            # Compute peak torque
            peak = np.max(np.abs(torques))

            algorithms.append(algo_name.replace("_", " "))
            rms_torques.append(rms)
            peak_torques.append(peak)
            colors.append(ALGORITHM_COLORS.get(algo_name, "gray"))

        # Sort by RMS torque
        sorted_indices = np.argsort(rms_torques)
        algorithms = [algorithms[i] for i in sorted_indices]
        rms_torques = [rms_torques[i] for i in sorted_indices]
        peak_torques = [peak_torques[i] for i in sorted_indices]
        colors = [colors[i] for i in sorted_indices]

        # RMS torque bar chart
        bars1 = ax1.barh(
            algorithms, rms_torques, color=colors, alpha=0.8, edgecolor="black"
        )
        ax1.set_xlabel("RMS Torque (Nm)")
        ax1.set_title("Control Effort (RMS Torque)", fontweight="bold")
        ax1.grid(axis="x", alpha=0.3)

        # Add value labels
        for i, (bar, val) in enumerate(zip(bars1, rms_torques)):
            ax1.text(val + 0.5, i, f"{val:.2f}", va="center", fontsize=9)

        # Peak torque bar chart
        bars2 = ax2.barh(
            algorithms, peak_torques, color=colors, alpha=0.8, edgecolor="black"
        )
        ax2.set_xlabel("Peak Torque (Nm)")
        ax2.set_title("Maximum Torque Magnitude", fontweight="bold")
        ax2.grid(axis="x", alpha=0.3)

        # Add value labels
        for i, (bar, val) in enumerate(zip(bars2, peak_torques)):
            ax2.text(val + 1, i, f"{val:.2f}", va="center", fontsize=9)

        plt.tight_layout()

        output_path = self.output_dir / "control_effort.png"
        plt.savefig(output_path)
        print(f"  Saved: {output_path}")
        plt.close()

    def plot_joint_specific_effort(self):
        """Plot control effort broken down by joint"""
        print("Generating joint-specific control effort...")

        joint_names = ["Left Hip", "Left Knee", "Right Hip", "Right Knee"]

        # Prepare data
        data = []
        for algo_name, traj in self.trajectories.items():
            if traj is None:
                continue

            torques = traj["torques"]

            for j_idx, joint_name in enumerate(joint_names):
                rms = np.sqrt(np.mean(torques[:, j_idx] ** 2))
                data.append(
                    {
                        "Algorithm": algo_name.replace("_", " "),
                        "Joint": joint_name,
                        "RMS Torque": rms,
                    }
                )

        df = pd.DataFrame(data)

        # Create grouped bar chart
        fig, ax = plt.subplots(figsize=(12, 6))

        x = np.arange(len(joint_names))
        width = 0.15

        algorithms = df["Algorithm"].unique()
        for i, algo in enumerate(algorithms):
            algo_data = df[df["Algorithm"] == algo]
            values = [
                (
                    algo_data[algo_data["Joint"] == joint]["RMS Torque"].values[0]
                    if len(algo_data[algo_data["Joint"] == joint]) > 0
                    else 0
                )
                for joint in joint_names
            ]

            color = ALGORITHM_COLORS.get(algo.replace(" ", "_"), "gray")
            offset = (i - len(algorithms) / 2) * width
            ax.bar(
                x + offset,
                values,
                width,
                label=algo,
                color=color,
                alpha=0.8,
                edgecolor="black",
            )

        ax.set_xlabel("Joint")
        ax.set_ylabel("RMS Torque (Nm)")
        ax.set_title("Joint-Specific Control Effort", fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels(joint_names)
        ax.legend(loc="best", framealpha=0.9)
        ax.grid(axis="y", alpha=0.3)

        plt.tight_layout()

        output_path = self.output_dir / "joint_control_effort.png"
        plt.savefig(output_path)
        print(f"  Saved: {output_path}")
        plt.close()

    def plot_comprehensive_summary(self):
        """Create a comprehensive summary figure"""
        print("Generating comprehensive summary...")

        fig = plt.figure(figsize=(16, 10))
        gs = gridspec.GridSpec(3, 3, hspace=0.4, wspace=0.4)

        # 1. Torque time series (left hip)
        ax1 = fig.add_subplot(gs[0, :2])
        for algo_name, traj in self.trajectories.items():
            if traj is None:
                continue
            time = traj["time"][:500]
            torques = traj["torques"][:500, 0]  # Left hip
            color = ALGORITHM_COLORS.get(algo_name, "gray")
            ax1.plot(
                time, torques, label=algo_name.replace("_", " "), color=color, alpha=0.8
            )
        ax1.set_xlabel("Time (s)")
        ax1.set_ylabel("Left Hip Torque (Nm)")
        ax1.set_title("A. Torque Time Series", loc="left", fontweight="bold")
        ax1.legend(loc="upper right", fontsize=8)
        ax1.grid(True, alpha=0.3)

        # 2. Control effort bar chart
        ax2 = fig.add_subplot(gs[0, 2])
        algorithms = []
        rms_torques = []
        colors_list = []
        for algo_name, traj in self.trajectories.items():
            if traj is None:
                continue
            rms = np.sqrt(np.mean(traj["torques"] ** 2))
            algorithms.append(algo_name.replace("_", "\n"))
            rms_torques.append(rms)
            colors_list.append(ALGORITHM_COLORS.get(algo_name, "gray"))

        ax2.bar(
            range(len(algorithms)),
            rms_torques,
            color=colors_list,
            alpha=0.8,
            edgecolor="black",
        )
        ax2.set_xticks(range(len(algorithms)))
        ax2.set_xticklabels(algorithms, fontsize=7)
        ax2.set_ylabel("RMS Torque (Nm)")
        ax2.set_title("B. Control Effort", loc="left", fontweight="bold")
        ax2.grid(axis="y", alpha=0.3)

        # 3-4. Phase portraits (left hip and knee)
        for idx, (joint_name, q_idx, v_idx) in enumerate(
            [("Left Hip", 7, 6), ("Left Knee", 8, 7)]
        ):
            ax = fig.add_subplot(gs[1, idx])
            for algo_name, traj in self.trajectories.items():
                if traj is None:
                    continue
                angles = traj["qpos"][:, q_idx]
                velocities = traj["qvel"][:, v_idx]
                color = ALGORITHM_COLORS.get(algo_name, "gray")
                ax.plot(
                    angles,
                    velocities,
                    color=color,
                    alpha=0.7,
                    linewidth=1.0,
                    label=algo_name.replace("_", " "),
                )
            ax.set_xlabel("Angle (rad)", fontsize=9)
            ax.set_ylabel("Velocity (rad/s)", fontsize=9)
            ax.set_title(
                f"{'C' if idx == 0 else 'D'}. {joint_name} Phase",
                loc="left",
                fontweight="bold",
            )
            if idx == 0:
                ax.legend(loc="best", fontsize=7)
            ax.grid(True, alpha=0.3)

        # 5. Torque distribution
        ax5 = fig.add_subplot(gs[1, 2])
        for algo_name, traj in self.trajectories.items():
            if traj is None:
                continue
            torques_flat = traj["torques"].flatten()
            color = ALGORITHM_COLORS.get(algo_name, "gray")
            ax5.hist(
                torques_flat,
                bins=30,
                alpha=0.5,
                color=color,
                label=algo_name.replace("_", " "),
                density=True,
            )
        ax5.set_xlabel("Torque (Nm)")
        ax5.set_ylabel("Density")
        ax5.set_title("E. Torque Distribution", loc="left", fontweight="bold")
        ax5.legend(loc="best", fontsize=7)
        ax5.grid(axis="y", alpha=0.3)

        # 6-8. Joint angles over time
        joint_names = ["Left Hip", "Left Knee", "Right Hip"]
        q_indices = [7, 8, 9]
        for idx, (joint_name, q_idx) in enumerate(zip(joint_names, q_indices)):
            ax = fig.add_subplot(gs[2, idx])
            for algo_name, traj in self.trajectories.items():
                if traj is None:
                    continue
                time = traj["time"][:500]
                angles = traj["qpos"][:500, q_idx]
                color = ALGORITHM_COLORS.get(algo_name, "gray")
                ax.plot(time, angles, color=color, alpha=0.7, linewidth=1.0)
            ax.set_xlabel("Time (s)", fontsize=9)
            ax.set_ylabel("Angle (rad)", fontsize=9)
            ax.set_title(
                f"{'F' if idx == 0 else 'G' if idx == 1 else 'H'}. {joint_name} Trajectory",
                loc="left",
                fontweight="bold",
            )
            ax.grid(True, alpha=0.3)

        fig.suptitle(
            "Control Policy Comparison - Comprehensive Summary",
            fontsize=15,
            fontweight="bold",
            y=0.995,
        )

        output_path = self.output_dir / "comprehensive_summary.png"
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        print(f"  Saved: {output_path}")
        plt.close()

    def generate_all_figures(self):
        """Generate all visualization figures"""
        print("\n" + "=" * 80)
        print("GENERATING POLICY VISUALIZATIONS")
        print("=" * 80)

        self.plot_torque_profiles()
        self.plot_phase_portraits()
        self.plot_poincare_sections()
        self.plot_control_effort()
        self.plot_joint_specific_effort()
        self.plot_comprehensive_summary()

        print("\n" + "=" * 80)
        print(f"All figures saved to: {self.output_dir}")
        print("=" * 80)


def main():
    """Main entry point"""
    # Find model file
    base_dir = Path(__file__).parent.parent
    model_path = base_dir / "biped_model_V13.xml"

    if not model_path.exists():
        print("Looking for model files...")
        alternatives = list(base_dir.glob("biped_model_V*.xml"))
        if alternatives:
            model_path = alternatives[-1]
            print(f"Using: {model_path}")
        else:
            print("Error: No model files found!")
            return

    # Collect trajectory data
    collector = PolicyDataCollector(str(model_path))

    trajectories = {}
    for algorithm in collector.controllers.keys():
        traj = collector.collect_trajectory(algorithm, num_steps=1000)
        if traj is not None:
            trajectories[algorithm] = traj

    if not trajectories:
        print("Error: No trajectories collected!")
        return

    # Generate visualizations
    visualizer = PolicyVisualizer()
    visualizer.load_trajectories(trajectories)
    visualizer.generate_all_figures()

    print("\nVisualization complete!")


if __name__ == "__main__":
    main()
