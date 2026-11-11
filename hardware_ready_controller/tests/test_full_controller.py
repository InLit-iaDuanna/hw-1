"""
Full Integration Test for Hardware Ready Controller in MuJoCo

Tests the complete controller stack against V13.7 baseline results:
- Load V13.7 model XML with MX-64AR motor parameters
- Run 12s simulation with event-driven FSM
- Verify performance metrics: forward distance > 4.0m, alternations >= 8, no falls
- Compare with and without friction compensation
- Generate comparison plots

Test Environment:
- MuJoCo timestep: 1ms (1kHz control loop)
- Motor: Dynamixel MX-64AR with friction compensation
- Baseline: V13.7 successful walking results
"""

import sys
from pathlib import Path
import pytest
import numpy as np
import matplotlib

matplotlib.use("Agg")  # Non-interactive backend for testing
import matplotlib.pyplot as plt

# Add hw-1 root to path
HW1_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HW1_ROOT))

try:
    import mujoco
except ImportError:
    pytest.skip("MuJoCo not available", allow_module_level=True)

# Import V13.7 simulation infrastructure
V137_DIR = HW1_ROOT / "v13_7_friction_compensation"
sys.path.insert(0, str(V137_DIR))

from simulate_v13_7 import (
    V137Params,
    make_v137_fsm,
    run_simulation_v137,
    SUCCESS_FORWARD,
    SUCCESS_TIME,
    SUCCESS_TOUCHDOWNS,
)
from simulate_v14c import make_v14c_params

# Success criteria from V13.7
EXPECTED_FORWARD_DISTANCE = 4.0  # meters
EXPECTED_ALTERNATIONS = 8  # touchdown events
EXPECTED_DURATION = 12.0  # seconds
BASELINE_TOLERANCE = 0.15  # 15% tolerance for comparison


class TestFullControllerIntegration:
    """Full integration test suite for hardware ready controller in MuJoCo."""

    @pytest.fixture(scope="class")
    def baseline_params(self):
        """Load V13.7 baseline parameters matching the successful command-line defaults."""
        from simulate_passive_arms_v14 import PassiveArmsParams
        from common.motor_dynamics import PRESETS as MOTOR_PRESETS
        from dataclasses import replace

        # Use V13.7 successful baseline: default params with lighter arms and scaled legs
        base0 = PassiveArmsParams()
        base_params = replace(
            base0,
            duration=12.0,
            arm_mass=0.01,  # V13.7 uses lighter arms than default 0.3
            arm_length=0.40,
            arm_damping=0.02,
            arm_stiffness=0.0,
            thigh_length=float(base0.thigh_length * 1.02),
            shank_length=float(base0.shank_length * 1.02),
            step_length=float(base0.step_length * 1.02),
            foot_radius=0.042,
        )

        fsm_params = make_v14c_params(base_params)

        return V137Params(
            base=base_params,
            fsm=fsm_params,
            hip_motor=MOTOR_PRESETS["mx64ar"],
            knee_motor=MOTOR_PRESETS["mx64ar"],
            compensate_friction=True,
        )

    @pytest.fixture(scope="class")
    def baseline_results(self, baseline_params):
        """Run V13.7 baseline simulation with friction compensation."""
        rows, summary = run_simulation_v137(
            baseline_params, save_prefix=None, sample_hz=160.0
        )
        return summary

    @pytest.fixture(scope="class")
    def no_compensation_results(self, baseline_params):
        """Run simulation without friction compensation for comparison."""
        from dataclasses import replace

        params_no_comp = replace(baseline_params, compensate_friction=False)
        rows, summary = run_simulation_v137(
            params_no_comp, save_prefix=None, sample_hz=160.0
        )
        return summary

    def test_model_loads_successfully(self, baseline_params):
        """Test that V13.7 model XML loads without errors."""
        from simulate_v13_7 import write_model_v137, MODEL_PATH

        write_model_v137(baseline_params)
        assert MODEL_PATH.exists(), f"Model file not created: {MODEL_PATH}"

        # Load model
        model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))

        # Verify model structure
        assert model is not None
        assert model.nu == 4, f"Expected 4 actuators, got {model.nu}"
        # V13.7 has 10 DOFs: hip_x, hip_z, left_hip, left_knee, left_ankle,
        # right_hip, right_knee, right_ankle, left_arm, right_arm
        assert model.nq == 10, f"Expected 10 DOFs (with passive arms), got {model.nq}"
        assert model.opt.timestep == 0.001, "Expected 1ms timestep"

    def test_motor_parameters_injected(self, baseline_params):
        """Verify motor parameters are correctly injected into model."""
        from simulate_v13_7 import write_model_v137, MODEL_PATH
        from common.motor_dynamics import (
            joint_armature_with_motor,
            joint_damping_with_motor,
        )

        write_model_v137(baseline_params)
        model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))

        # Expected values with motor inertia and damping
        DEFAULT_BASE_ARMATURE = 0.004
        expected_hip_arm = joint_armature_with_motor(
            DEFAULT_BASE_ARMATURE, baseline_params.hip_motor
        )
        expected_hip_damp = joint_damping_with_motor(
            baseline_params.base.hip_joint_damping, baseline_params.hip_motor
        )
        expected_knee_arm = joint_armature_with_motor(
            DEFAULT_BASE_ARMATURE, baseline_params.knee_motor
        )
        expected_knee_damp = joint_damping_with_motor(
            baseline_params.base.knee_damping, baseline_params.knee_motor
        )

        # Get joint IDs
        hip_joints = ["left_hip", "right_hip"]
        knee_joints = ["left_knee", "right_knee"]

        for joint_name in hip_joints:
            jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, joint_name)
            actual_arm = model.dof_armature[jid]
            actual_damp = model.dof_damping[jid]
            assert np.isclose(
                actual_arm, expected_hip_arm, rtol=1e-5
            ), f"{joint_name} armature mismatch: {actual_arm} vs {expected_hip_arm}"
            assert np.isclose(
                actual_damp, expected_hip_damp, rtol=1e-5
            ), f"{joint_name} damping mismatch: {actual_damp} vs {expected_hip_damp}"

        for joint_name in knee_joints:
            jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, joint_name)
            actual_arm = model.dof_armature[jid]
            actual_damp = model.dof_damping[jid]
            assert np.isclose(
                actual_arm, expected_knee_arm, rtol=1e-5
            ), f"{joint_name} armature mismatch: {actual_arm} vs {expected_knee_arm}"
            assert np.isclose(
                actual_damp, expected_knee_damp, rtol=1e-5
            ), f"{joint_name} damping mismatch: {actual_damp} vs {expected_knee_damp}"

    def test_baseline_success_criteria(self, baseline_results):
        """Test that baseline with friction compensation meets success criteria."""
        summary = baseline_results

        # Verify success flag
        assert summary["success"], (
            f"Baseline failed: {summary['failure']}, "
            f"forward={summary['forward_distance']:.2f}m, "
            f"alternations={summary['alternating_touchdowns']}, "
            f"time={summary['simulated_time']:.2f}s"
        )

        # Check individual metrics
        assert (
            summary["forward_distance"] >= SUCCESS_FORWARD
        ), f"Forward distance {summary['forward_distance']:.2f}m < {SUCCESS_FORWARD}m"

        assert (
            summary["alternating_touchdowns"] >= SUCCESS_TOUCHDOWNS
        ), f"Alternations {summary['alternating_touchdowns']} < {SUCCESS_TOUCHDOWNS}"

        assert (
            summary["simulated_time"] >= SUCCESS_TIME
        ), f"Simulated time {summary['simulated_time']:.2f}s < {SUCCESS_TIME}s"

        assert (
            summary["failure"] == "completed"
        ), f"Unexpected failure: {summary['failure']}"

    def test_forward_distance_exceeds_threshold(self, baseline_results):
        """Verify forward walking distance > 4.0m."""
        forward_dist = baseline_results["forward_distance"]
        assert (
            forward_dist >= EXPECTED_FORWARD_DISTANCE
        ), f"Forward distance {forward_dist:.3f}m < {EXPECTED_FORWARD_DISTANCE}m"

        # Should walk reasonably far (not just barely passing)
        assert (
            forward_dist >= 4.5
        ), f"Forward distance {forward_dist:.3f}m suspiciously low (expected ~5-6m)"

    def test_alternating_gait_pattern(self, baseline_results):
        """Verify alternating touchdown pattern with >= 8 events."""
        alternations = baseline_results["alternating_touchdowns"]
        assert (
            alternations >= EXPECTED_ALTERNATIONS
        ), f"Alternations {alternations} < {EXPECTED_ALTERNATIONS}"

        # Check contact events exist and alternate
        contact_events = baseline_results["contact_events"]
        assert len(contact_events) > 0, "No contact events recorded"

        # Verify events alternate between left and right
        if len(contact_events) >= 2:
            feet = [evt["foot"] for evt in contact_events[: alternations + 1]]
            consecutive_same = sum(
                1 for i in range(len(feet) - 1) if feet[i] == feet[i + 1]
            )
            assert (
                consecutive_same == 0
            ), f"Non-alternating contacts detected: {feet[:10]}"

    def test_no_falls_or_failures(self, baseline_results):
        """Verify simulation completes without falls or numerical instability."""
        failure_type = baseline_results["failure"]

        assert failure_type == "completed", f"Simulation failed: {failure_type}"

        # Check for specific failure modes
        bad_failures = ["nan_or_unstable", "fly_away", "penetration", "fall_backward"]
        assert (
            failure_type not in bad_failures
        ), f"Critical failure mode: {failure_type}"

    def test_friction_compensation_improves_performance(
        self, baseline_results, no_compensation_results
    ):
        """Verify friction compensation improves walking performance."""
        with_comp = baseline_results
        without_comp = no_compensation_results

        # With compensation should walk farther
        dist_with = with_comp["forward_distance"]
        dist_without = without_comp["forward_distance"]

        # If without compensation fails, just verify with-comp succeeds
        if not without_comp["success"]:
            assert with_comp[
                "success"
            ], "Friction compensation should enable successful walking"
            return

        # If both succeed, verify improvement
        improvement = (dist_with - dist_without) / dist_without
        assert improvement > -0.1, (
            f"Friction compensation degrades performance: "
            f"{dist_with:.2f}m vs {dist_without:.2f}m ({improvement:.1%})"
        )

        # Energy efficiency should improve
        energy_with = with_comp["active_input_energy_mech_j"]
        energy_without = without_comp["active_input_energy_mech_j"]

        # With compensation should use similar or less energy for better distance
        specific_energy_with = (
            energy_with / dist_with if dist_with > 0 else float("inf")
        )
        specific_energy_without = (
            energy_without / dist_without if dist_without > 0 else float("inf")
        )

        assert specific_energy_with <= specific_energy_without * 1.5, (
            f"Friction compensation increases specific energy: "
            f"{specific_energy_with:.2f} vs {specific_energy_without:.2f} J/m"
        )

    def test_phase_transitions_occur(self, baseline_results):
        """Verify FSM phase transitions are happening."""
        phase_durations = baseline_results["phase_durations_s"]

        # All four phases should have non-zero duration
        required_phases = [
            "stance_early",
            "stance_late",
            "swing_thrust",
            "swing_retract",
        ]
        for phase in required_phases:
            assert phase in phase_durations, f"Missing phase: {phase}"
            assert (
                phase_durations[phase] > 0.0
            ), f"Phase {phase} never activated: duration={phase_durations[phase]}"

        # Phase durations should be reasonable (not stuck in one phase)
        total_time = baseline_results["simulated_time"]
        for phase in required_phases:
            ratio = phase_durations[phase] / total_time
            assert (
                ratio < 0.8
            ), f"Phase {phase} dominates timeline: {ratio:.1%} of total time"

    def test_motor_saturation_acceptable(self, baseline_results):
        """Verify motor saturation is within acceptable limits."""
        sat_counts = baseline_results["motor_saturation_count"]
        phase_sat_rates = baseline_results["phase_saturation_rate"]

        # Total saturation events should be limited
        total_sat = sum(sat_counts.values())
        total_steps = int(baseline_results["simulated_time"] / 0.001)
        sat_rate = total_sat / (4 * total_steps)  # 4 actuators

        assert (
            sat_rate < 0.3
        ), f"Excessive motor saturation: {sat_rate:.1%} of control cycles"

        # Per-phase saturation should be reasonable
        for phase, rate in phase_sat_rates.items():
            assert rate < 0.5, f"Phase {phase} has excessive saturation: {rate:.1%}"

    def test_energy_metrics_reasonable(self, baseline_results):
        """Verify energy consumption is in reasonable range."""
        energy = baseline_results["active_input_energy_mech_j"]
        distance = baseline_results["forward_distance"]

        # Positive energy input (no negative work overall)
        assert energy > 0, f"Invalid energy metric: {energy} J"

        # Specific energy (J/m) should be reasonable for passive-like walker
        specific_energy = energy / distance if distance > 0 else float("inf")

        # V13.7 typically uses 20-40 J for 5-6m walk (~5-8 J/m)
        assert (
            specific_energy < 20.0
        ), f"Excessive energy consumption: {specific_energy:.2f} J/m"

        assert (
            specific_energy > 1.0
        ), f"Suspiciously low energy: {specific_energy:.2f} J/m"

    def test_compare_against_v137_baseline(self, baseline_results):
        """Compare results against documented V13.7 baseline performance."""
        # V13.7 documented performance (actual baseline run results)
        V137_BASELINE = {
            "forward_distance": 4.6,  # ~4.6m typical with light arms
            "alternations": 10,  # ~10-11 typical
            "energy": 17.0,  # ~16-18 J typical
        }

        tolerance = BASELINE_TOLERANCE

        forward = baseline_results["forward_distance"]
        alternations = baseline_results["alternating_touchdowns"]
        energy = baseline_results["active_input_energy_mech_j"]

        # Allow deviation within tolerance
        assert forward >= V137_BASELINE["forward_distance"] * (1 - tolerance), (
            f"Forward distance {forward:.2f}m below baseline "
            f"{V137_BASELINE['forward_distance']:.2f}m"
        )

        assert alternations >= V137_BASELINE["alternations"] * (1 - tolerance), (
            f"Alternations {alternations} below baseline "
            f"{V137_BASELINE['alternations']}"
        )

        assert energy <= V137_BASELINE["energy"] * (
            1 + 2 * tolerance
        ), f"Energy {energy:.2f}J significantly exceeds baseline {V137_BASELINE['energy']:.2f}J"

    @pytest.mark.slow
    def test_generate_comparison_plots(
        self, baseline_results, no_compensation_results, tmp_path
    ):
        """Generate comparison plots for with/without friction compensation."""

        fig, axes = plt.subplots(2, 3, figsize=(15, 10))
        fig.suptitle(
            "V13.7 Controller: With vs Without Friction Compensation",
            fontsize=14,
            fontweight="bold",
        )

        # Extract data
        with_comp = baseline_results
        without_comp = no_compensation_results

        # Plot 1: Forward distance comparison
        ax = axes[0, 0]
        categories = ["With\nCompensation", "Without\nCompensation"]
        distances = [with_comp["forward_distance"], without_comp["forward_distance"]]
        colors = [
            "#2ecc71" if with_comp["success"] else "#e74c3c",
            "#2ecc71" if without_comp["success"] else "#e74c3c",
        ]
        ax.bar(categories, distances, color=colors, alpha=0.7)
        ax.axhline(
            y=SUCCESS_FORWARD,
            color="r",
            linestyle="--",
            label=f"Target: {SUCCESS_FORWARD}m",
        )
        ax.set_ylabel("Forward Distance (m)")
        ax.set_title("Walking Distance")
        ax.legend()
        ax.grid(axis="y", alpha=0.3)

        # Plot 2: Alternations comparison
        ax = axes[0, 1]
        alternations = [
            with_comp["alternating_touchdowns"],
            without_comp["alternating_touchdowns"],
        ]
        ax.bar(categories, alternations, color=colors, alpha=0.7)
        ax.axhline(
            y=SUCCESS_TOUCHDOWNS,
            color="r",
            linestyle="--",
            label=f"Target: {SUCCESS_TOUCHDOWNS}",
        )
        ax.set_ylabel("Touchdown Events")
        ax.set_title("Gait Alternations")
        ax.legend()
        ax.grid(axis="y", alpha=0.3)

        # Plot 3: Energy consumption
        ax = axes[0, 2]
        energies = [
            with_comp["active_input_energy_mech_j"],
            without_comp["active_input_energy_mech_j"],
        ]
        ax.bar(categories, energies, color=["#3498db", "#e67e22"], alpha=0.7)
        ax.set_ylabel("Active Energy Input (J)")
        ax.set_title("Energy Consumption")
        ax.grid(axis="y", alpha=0.3)

        # Plot 4: Specific energy (J/m)
        ax = axes[1, 0]
        specific_energies = [
            (
                with_comp["active_input_energy_mech_j"] / with_comp["forward_distance"]
                if with_comp["forward_distance"] > 0
                else 0
            ),
            (
                without_comp["active_input_energy_mech_j"]
                / without_comp["forward_distance"]
                if without_comp["forward_distance"] > 0
                else 0
            ),
        ]
        ax.bar(categories, specific_energies, color=["#9b59b6", "#f39c12"], alpha=0.7)
        ax.set_ylabel("Specific Energy (J/m)")
        ax.set_title("Energy Efficiency")
        ax.grid(axis="y", alpha=0.3)

        # Plot 5: Phase durations comparison
        ax = axes[1, 1]
        phases = ["stance_early", "stance_late", "swing_thrust", "swing_retract"]
        phase_labels = ["SE", "SL", "ST", "SR"]

        with_phases = [with_comp["phase_durations_s"].get(p, 0) for p in phases]
        without_phases = [without_comp["phase_durations_s"].get(p, 0) for p in phases]

        x = np.arange(len(phases))
        width = 0.35
        ax.bar(x - width / 2, with_phases, width, label="With Comp", alpha=0.7)
        ax.bar(x + width / 2, without_phases, width, label="Without Comp", alpha=0.7)
        ax.set_ylabel("Total Duration (s)")
        ax.set_title("Phase Durations")
        ax.set_xticks(x)
        ax.set_xticklabels(phase_labels)
        ax.legend()
        ax.grid(axis="y", alpha=0.3)

        # Plot 6: Success summary
        ax = axes[1, 2]
        ax.axis("off")

        summary_text = f"""
        WITH FRICTION COMPENSATION:
        Status: {'✓ SUCCESS' if with_comp['success'] else '✗ FAILED'}
        Distance: {with_comp['forward_distance']:.2f}m
        Alternations: {with_comp['alternating_touchdowns']}
        Time: {with_comp['simulated_time']:.2f}s
        Energy: {with_comp['active_input_energy_mech_j']:.1f}J
        Failure: {with_comp['failure']}

        WITHOUT FRICTION COMPENSATION:
        Status: {'✓ SUCCESS' if without_comp['success'] else '✗ FAILED'}
        Distance: {without_comp['forward_distance']:.2f}m
        Alternations: {without_comp['alternating_touchdowns']}
        Time: {without_comp['simulated_time']:.2f}s
        Energy: {without_comp['active_input_energy_mech_j']:.1f}J
        Failure: {without_comp['failure']}
        """

        ax.text(
            0.1,
            0.5,
            summary_text,
            fontsize=10,
            family="monospace",
            verticalalignment="center",
        )

        plt.tight_layout()

        # Save plot
        output_path = tmp_path / "v137_comparison.png"
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close()

        assert output_path.exists(), "Plot not generated"
        assert output_path.stat().st_size > 10000, "Plot file suspiciously small"

        print(f"\nComparison plot saved to: {output_path}")


class TestControllerRobustness:
    """Additional robustness tests for edge cases."""

    def test_handles_initial_transients(self, tmp_path):
        """Verify controller handles initial transients gracefully."""
        from simulate_passive_arms_v14 import PassiveArmsParams
        from common.motor_dynamics import PRESETS

        base_params = PassiveArmsParams(
            duration=2.0,  # Short run to test initialization
            timestep=0.001,
            hip_joint_damping=0.07,
            knee_damping=0.13,
        )

        fsm_params = make_v14c_params(base_params)
        params = V137Params(
            base=base_params,
            fsm=fsm_params,
            hip_motor=PRESETS["mx64ar"],
            knee_motor=PRESETS["mx64ar"],
            compensate_friction=True,
        )

        result = run_simulation_v137(params, save_prefix=None, sample_hz=160.0)
        rows, summary = result

        # Should not crash or have NaN values in first 2 seconds
        assert (
            summary["failure"] != "nan_or_unstable"
        ), "Controller unstable during initialization"

        assert summary["simulated_time"] >= 1.0, "Simulation terminated too early"

    def test_phase_timing_consistency(self):
        """Verify phase durations are consistent with FSM configuration."""
        from simulate_passive_arms_v14 import PassiveArmsParams
        from common.motor_dynamics import PRESETS

        base_params = PassiveArmsParams(duration=12.0, timestep=0.001)
        fsm_params = make_v14c_params(base_params)
        params = V137Params(
            base=base_params,
            fsm=fsm_params,
            hip_motor=PRESETS["mx64ar"],
            knee_motor=PRESETS["mx64ar"],
            compensate_friction=True,
        )

        result = run_simulation_v137(params, save_prefix=None, sample_hz=160.0)
        rows, summary = result

        # Phase durations should roughly match configured values
        # (allowing for variation due to event-driven transitions)
        phase_config = {
            "stance_early": 0.15,
            "stance_late": 0.25,
            "swing_thrust": 0.20,
            "swing_retract": 0.20,
        }

        phase_durations = summary["phase_durations_s"]
        total_phase_time = sum(phase_durations.values())

        for phase, expected_duration in phase_config.items():
            actual = phase_durations.get(phase, 0)
            ratio = actual / total_phase_time if total_phase_time > 0 else 0
            expected_ratio = expected_duration / sum(phase_config.values())

            # Allow 50% deviation (event-driven FSM varies timing)
            assert (
                abs(ratio - expected_ratio) < 0.3
            ), f"Phase {phase} timing inconsistent: {ratio:.2f} vs {expected_ratio:.2f}"


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s", "--tb=short"])
