"""
Unit tests for Kalman Filter State Estimator
Hardware-ready implementation for hw-1 gait rehabilitation device

Test Coverage:
- Kalman filter with known trajectories
- Noise reduction verification
- Encoder quantization handling
- Based on V17 test cases and specifications
"""

import sys
from pathlib import Path

import numpy as np
import pytest

# Add repository root to path for package imports.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from hardware_ready_controller.state_estimator import (
    ContactDetector,
    ForwardKinematics,
    JointStateEstimator,
    KalmanConfig,
    KalmanFilter,
    StateEstimator,
    encoder_counts_to_radians,
    estimate_velocity_finite_diff,
)


class TestEncoderUtilities:
    """Test encoder conversion utilities."""

    def test_encoder_counts_to_radians_full_revolution(self):
        """Full revolution should equal 2π radians."""
        cpr = 4096  # V17 specification
        angle = encoder_counts_to_radians(cpr, cpr)
        assert np.isclose(angle, 2 * np.pi, atol=1e-6)

    def test_encoder_counts_to_radians_half_revolution(self):
        """Half revolution should equal π radians."""
        cpr = 4096
        angle = encoder_counts_to_radians(cpr // 2, cpr)
        assert np.isclose(angle, np.pi, atol=1e-6)

    def test_encoder_counts_to_radians_zero(self):
        """Zero counts should equal zero radians."""
        angle = encoder_counts_to_radians(0, 4096)
        assert angle == 0.0

    def test_encoder_quantization_error(self):
        """Quantization error should match V17 specification."""
        cpr = 4096
        quantization_step_rad = 2 * np.pi / cpr
        max_quantization_error_rad = quantization_step_rad / 2
        # Expected from V17: 4096 CPR has ~0.77 mrad maximum half-count error.
        assert np.isclose(max_quantization_error_rad, 0.77e-3, atol=1e-5)

    def test_finite_diff_velocity(self):
        """Finite difference should compute velocity correctly."""
        angle_prev = 0.0
        angle_curr = 0.1  # radians
        dt = 0.001  # 1ms
        velocity = estimate_velocity_finite_diff(angle_curr, angle_prev, dt)
        expected = 100.0  # rad/s
        assert np.isclose(velocity, expected, atol=1e-6)


class TestKalmanFilterBasics:
    """Test basic Kalman filter operations."""

    @pytest.fixture
    def kalman_filter(self):
        """Create a default Kalman filter."""
        config = KalmanConfig()
        return KalmanFilter(config, dt=0.001)

    def test_kalman_filter_initialization(self, kalman_filter):
        """Filter should initialize with zero state."""
        angle, velocity = kalman_filter.get_state()
        assert angle == 0.0
        assert velocity == 0.0

    def test_kalman_filter_reset(self, kalman_filter):
        """Reset should restore initial state."""
        # Change state
        kalman_filter.step(1.0)
        kalman_filter.step(2.0)

        # Reset
        kalman_filter.reset(angle=0.5, velocity=1.0)
        angle, velocity = kalman_filter.get_state()

        assert np.isclose(angle, 0.5)
        assert np.isclose(velocity, 1.0)

    def test_kalman_filter_predict_only(self, kalman_filter):
        """Prediction should propagate state forward."""
        # Set initial state
        kalman_filter.reset(angle=0.0, velocity=1.0)

        # Predict (no measurement update)
        dt = 0.001
        predicted = kalman_filter.predict()

        # Expected: angle += velocity * dt
        expected_angle = 0.0 + 1.0 * dt
        assert np.isclose(predicted[0], expected_angle, atol=1e-6)
        assert np.isclose(predicted[1], 1.0, atol=1e-3)

    def test_kalman_filter_update_only(self, kalman_filter):
        """Update should correct state with measurement."""
        # Set state with some error
        kalman_filter.x = np.array([0.1, 0.0])

        # Perfect measurement
        measurement = 0.0
        updated = kalman_filter.update(measurement)

        # State should move toward measurement
        assert abs(updated[0]) < 0.1


class TestKalmanFilterKnownTrajectory:
    """Test Kalman filter with known trajectories (V17 requirement)."""

    def test_constant_position_trajectory(self):
        """Filter should track constant position."""
        config = KalmanConfig()
        kf = KalmanFilter(config, dt=0.001)

        # Constant angle with small noise
        true_angle = 1.0
        noise_std = 0.001
        np.random.seed(42)

        angles = []
        for _ in range(1000):
            measurement = true_angle + np.random.normal(0, noise_std)
            angle, _ = kf.step(measurement)
            angles.append(angle)

        # After convergence, should be close to true value
        final_estimates = angles[-100:]
        mean_estimate = np.mean(final_estimates)
        assert np.isclose(mean_estimate, true_angle, atol=0.01)

    def test_constant_velocity_trajectory(self):
        """Filter should track constant velocity motion."""
        config = KalmanConfig()
        kf = KalmanFilter(config, dt=0.001)

        # Linear motion: angle = velocity * time
        velocity_true = 2.0  # rad/s
        dt = 0.001
        noise_std = 0.001
        np.random.seed(42)

        estimated_velocities = []
        for i in range(2000):
            time = i * dt
            true_angle = velocity_true * time
            measurement = true_angle + np.random.normal(0, noise_std)

            angle, velocity = kf.step(measurement)

            if i > 500:  # After convergence
                estimated_velocities.append(velocity)

        # Velocity estimate should converge to true value
        mean_velocity = np.mean(estimated_velocities)
        assert np.isclose(mean_velocity, velocity_true, atol=0.1)

    def test_sinusoidal_trajectory(self):
        """Filter should track sinusoidal motion (gait-like)."""
        config = KalmanConfig()
        kf = KalmanFilter(config, dt=0.001)

        # Sinusoidal trajectory: angle = A * sin(ω * t)
        amplitude = 0.5  # rad
        frequency = 1.0  # Hz
        omega = 2 * np.pi * frequency
        dt = 0.001
        noise_std = 0.005
        np.random.seed(42)

        errors = []
        for i in range(3000):
            time = i * dt
            true_angle = amplitude * np.sin(omega * time)
            measurement = true_angle + np.random.normal(0, noise_std)

            estimated_angle, _ = kf.step(measurement)

            if i > 1000:  # After initial convergence
                errors.append(abs(estimated_angle - true_angle))

        # Mean tracking error should be small
        mean_error = np.mean(errors)
        assert mean_error < 0.01  # < 10 mrad average error


class TestKalmanFilterNoiseReduction:
    """Test noise reduction capabilities (V17 requirement)."""

    def test_noise_reduction_quantification(self):
        """Kalman filter should reduce measurement noise."""
        config = KalmanConfig()
        kf = KalmanFilter(config, dt=0.001)

        # Constant position with significant noise
        true_angle = 1.0
        noise_std = 0.01  # 10 mrad noise
        np.random.seed(42)

        measurements = []
        estimates = []

        for _ in range(2000):
            measurement = true_angle + np.random.normal(0, noise_std)
            measurements.append(measurement)

            angle, _ = kf.step(measurement)
            estimates.append(angle)

        # Compare noise after convergence
        measurement_std = np.std(measurements[-500:])
        estimate_std = np.std(estimates[-500:])

        # Filter should reduce noise significantly
        noise_reduction_ratio = estimate_std / measurement_std
        assert noise_reduction_ratio < 0.3  # At least 70% reduction

    def test_velocity_smoothing(self):
        """Filtered velocity should be smoother than finite difference."""
        config = KalmanConfig()
        kf = KalmanFilter(config, dt=0.001)
        dt = 0.001

        # Generate constant velocity with noisy measurements
        true_velocity = 1.5  # rad/s
        noise_std = 0.005
        np.random.seed(42)

        finite_diff_velocities = []
        kalman_velocities = []
        prev_measurement = 0.0

        for i in range(2000):
            time = i * dt
            true_angle = true_velocity * time
            measurement = true_angle + np.random.normal(0, noise_std)

            # Finite difference velocity
            fd_velocity = estimate_velocity_finite_diff(
                measurement, prev_measurement, dt
            )
            finite_diff_velocities.append(fd_velocity)
            prev_measurement = measurement

            # Kalman filtered velocity
            _, kalman_velocity = kf.step(measurement)
            kalman_velocities.append(kalman_velocity)

        # Compare smoothness (standard deviation of differences)
        fd_smoothness = np.std(np.diff(finite_diff_velocities[500:]))
        kalman_smoothness = np.std(np.diff(kalman_velocities[500:]))

        # Kalman should be significantly smoother
        assert kalman_smoothness < fd_smoothness * 0.5


class TestEncoderQuantization:
    """Test handling of encoder quantization (V17 requirement)."""

    def test_quantization_noise_handling(self):
        """Filter should handle encoder quantization correctly."""
        # V17 specification: 4096 CPR encoder
        cpr = 4096
        quantization_rad = 2 * np.pi / cpr  # ~0.77 mrad

        config = KalmanConfig(measurement_noise_encoder=quantization_rad**2)
        kf = KalmanFilter(config, dt=0.001)

        # Simulate quantized encoder readings
        true_angle = 1.0

        # Simulate slow motion through quantization levels
        estimates = []
        for i in range(1000):
            # Quantize the angle
            counts = int((true_angle + i * 0.0001) / quantization_rad)
            quantized_angle = counts * quantization_rad

            angle, _ = kf.step(quantized_angle)
            estimates.append(angle)

        # Filter should smooth out quantization steps
        estimate_changes = np.abs(np.diff(estimates[100:]))
        max_change = np.max(estimate_changes)

        # Maximum single-step change should be small (smooth interpolation)
        assert max_change < 0.001  # < 1 mrad per step

    def test_stationary_quantization(self):
        """Filter should handle stationary quantized signal."""
        cpr = 4096
        quantization_rad = 2 * np.pi / cpr

        config = KalmanConfig()
        kf = KalmanFilter(config, dt=0.001)

        # Stationary angle (quantized)
        counts = 1000
        quantized_angle = counts * quantization_rad

        velocities = []
        for _ in range(500):
            _, velocity = kf.step(quantized_angle)
            velocities.append(velocity)

        # Velocity should converge to zero
        final_velocity = np.mean(velocities[-100:])
        assert abs(final_velocity) < 0.01  # Nearly zero velocity


class TestJointStateEstimator:
    """Test multi-joint state estimator."""

    @pytest.fixture
    def joint_estimator(self):
        """Create joint state estimator."""
        return JointStateEstimator(dt=0.001)

    def test_multi_joint_initialization(self, joint_estimator):
        """All joints should initialize correctly."""
        states = joint_estimator.get_all_states()
        assert "hip" in states
        assert "knee" in states
        assert "ankle" in states

        for joint_name, (angle, velocity) in states.items():
            assert angle == 0.0
            assert velocity == 0.0

    def test_independent_joint_filtering(self, joint_estimator):
        """Each joint should filter independently."""
        # Update each joint with different values
        hip_state = joint_estimator.update_joint("hip", 0.5)
        knee_state = joint_estimator.update_joint("knee", 1.0)
        ankle_state = joint_estimator.update_joint("ankle", -0.3)

        # States should be different
        assert not np.isclose(hip_state[0], knee_state[0])
        assert not np.isclose(knee_state[0], ankle_state[0])

    def test_update_all_joints(self, joint_estimator):
        """Should update all joints simultaneously."""
        states = joint_estimator.update_all_joints(
            hip_angle=0.5, knee_angle=1.0, ankle_angle=-0.3
        )

        assert "hip" in states
        assert "knee" in states
        assert "ankle" in states

        # Each should have filtered the input
        hip_angle, _ = states["hip"]
        assert hip_angle != 0.0  # Changed from initial zero

    def test_reset_all_joints(self, joint_estimator):
        """Reset should clear all joint states."""
        # Set states
        joint_estimator.update_all_joints(1.0, 2.0, 3.0)

        # Reset
        joint_estimator.reset_all()

        states = joint_estimator.get_all_states()
        for joint_name, (angle, velocity) in states.items():
            assert angle == 0.0
            assert velocity == 0.0


class TestForwardKinematics:
    """Test forward kinematics calculations."""

    @pytest.fixture
    def fk(self):
        """Create forward kinematics calculator."""
        return ForwardKinematics(thigh_length=0.4, shank_length=0.4)

    def test_straight_leg_upright(self, fk):
        """Straight leg should give vertical hip position."""
        hip_angle = 0.0
        knee_angle = 0.0
        ankle_angle = 0.0

        x_hip, y_hip = fk.compute_hip_position(hip_angle, knee_angle, ankle_angle)

        # Should be directly above ankle
        assert np.isclose(x_hip, 0.0, atol=1e-6)
        # Height = thigh + shank length
        expected_height = fk.L_thigh + fk.L_shank
        assert np.isclose(y_hip, expected_height, atol=1e-6)

    def test_knee_flexion(self, fk):
        """Knee flexion should reduce hip height."""
        hip_angle = 0.0
        knee_angle_straight = 0.0
        knee_angle_flexed = np.pi / 4  # 45 degrees
        ankle_angle = 0.0

        _, y_straight = fk.compute_hip_position(
            hip_angle, knee_angle_straight, ankle_angle
        )
        _, y_flexed = fk.compute_hip_position(hip_angle, knee_angle_flexed, ankle_angle)

        # Flexed knee should lower hip
        assert y_flexed < y_straight

    def test_hip_velocity_zero_when_stationary(self, fk):
        """Zero joint velocities should give zero hip velocity."""
        angles = [0.1, 0.2, 0.3]  # arbitrary angles
        velocities = [0.0, 0.0, 0.0]  # zero velocities

        vx, vy = fk.compute_hip_velocity(*angles, *velocities)

        assert np.isclose(vx, 0.0, atol=1e-6)
        assert np.isclose(vy, 0.0, atol=1e-6)

    def test_hip_velocity_nonzero_when_moving(self, fk):
        """Non-zero joint velocities should produce hip velocity."""
        angles = [0.0, 0.0, 0.0]
        velocities = [0.0, 1.0, 0.0]  # knee moving

        vx, vy = fk.compute_hip_velocity(*angles, *velocities)

        # Should have some velocity component
        velocity_magnitude = np.sqrt(vx**2 + vy**2)
        assert velocity_magnitude > 0.0


class TestContactDetector:
    """Test contact detection with debouncing."""

    @pytest.fixture
    def contact_detector(self):
        """Create contact detector."""
        config = KalmanConfig(contact_force_threshold=5.0, contact_debounce_samples=3)
        return ContactDetector(config, dt=0.001)

    def test_no_contact_initially(self, contact_detector):
        """Should report no contact initially."""
        assert contact_detector.contact_state == False

    def test_contact_detection_with_threshold(self, contact_detector):
        """Should detect contact above threshold."""
        # Apply force above threshold consistently
        for i in range(5):
            time = i * 0.001
            contact = contact_detector.update(10.0, time)  # 10N > 5N threshold

        # After debouncing period, should detect contact
        assert contact == True

    def test_contact_debouncing(self, contact_detector):
        """Should debounce noisy contact signal."""
        # Single spike should not trigger contact
        contact_detector.update(10.0, 0.0)
        assert contact_detector.contact_state == False  # Not enough samples

        contact_detector.update(0.0, 0.001)
        contact_detector.update(10.0, 0.002)
        # Still inconsistent, should not confirm contact
        assert contact_detector.contact_state == False

    def test_delay_compensation(self, contact_detector):
        """Should buffer force data for delay compensation."""
        # Apply increasing force
        for i in range(20):
            time = i * 0.001
            force = i * 1.0  # 0, 1, 2, ... N
            contact_detector.update(force, time)

        # Should have buffer for delay compensation
        assert len(contact_detector.force_buffer) > 0

    def test_reset_contact_detector(self, contact_detector):
        """Reset should clear contact state."""
        # Establish contact
        for i in range(5):
            contact_detector.update(10.0, i * 0.001)

        # Reset
        contact_detector.reset()

        assert contact_detector.contact_state == False
        assert len(contact_detector.contact_history) == 0
        assert len(contact_detector.force_buffer) == 0


class TestStateEstimator:
    """Test complete state estimator integration."""

    @pytest.fixture
    def state_estimator(self):
        """Create complete state estimator."""
        return StateEstimator(config=None, dt=0.001, thigh_length=0.4, shank_length=0.4)

    def test_complete_state_update(self, state_estimator):
        """Should update complete state from sensor inputs."""
        result = state_estimator.update(
            hip_angle=0.1, knee_angle=0.2, ankle_angle=0.05, ground_force=10.0
        )

        # Should have all expected keys
        assert "joints" in result
        assert "hip_position" in result
        assert "hip_velocity" in result
        assert "contact" in result
        assert "timestamp" in result

    def test_joint_states_in_result(self, state_estimator):
        """Result should contain filtered joint states."""
        result = state_estimator.update(0.1, 0.2, 0.05, 10.0)

        assert "hip" in result["joints"]
        assert "knee" in result["joints"]
        assert "ankle" in result["joints"]

        # Each joint should have angle and velocity
        hip_state = result["joints"]["hip"]
        assert "angle" in hip_state
        assert "velocity" in hip_state

    def test_hip_position_computed(self, state_estimator):
        """Should compute hip position via forward kinematics."""
        result = state_estimator.update(0.0, 0.0, 0.0, 10.0)

        hip_pos = result["hip_position"]
        assert "x" in hip_pos
        assert "y" in hip_pos

        # For zero angles (straight leg), should be directly above
        assert np.isclose(hip_pos["x"], 0.0, atol=0.01)

    def test_hip_velocity_computed(self, state_estimator):
        """Should compute hip velocity via Jacobian."""
        # Run multiple steps to establish velocity
        for _ in range(10):
            result = state_estimator.update(0.0, 0.0, 0.0, 10.0)

        hip_vel = result["hip_velocity"]
        assert "x" in hip_vel
        assert "y" in hip_vel

    def test_contact_state_in_result(self, state_estimator):
        """Should include contact detection result."""
        result = state_estimator.update(0.1, 0.2, 0.05, 15.0)

        contact = result["contact"]
        assert "state" in contact
        assert "force" in contact
        assert isinstance(contact["state"], bool)
        assert contact["force"] == 15.0

    def test_timestamp_increments(self, state_estimator):
        """Timestamp should increment with each update."""
        result1 = state_estimator.update(0.1, 0.2, 0.05, 10.0)
        result2 = state_estimator.update(0.1, 0.2, 0.05, 10.0)

        assert result2["timestamp"] > result1["timestamp"]
        assert np.isclose(result2["timestamp"] - result1["timestamp"], 0.001)

    def test_state_estimator_reset(self, state_estimator):
        """Reset should restore initial conditions."""
        # Run several updates
        for _ in range(100):
            state_estimator.update(0.1, 0.2, 0.05, 10.0)

        # Reset
        state_estimator.reset()

        # Should be back to initial state
        assert state_estimator.current_time == 0.0


class TestV17IntegrationScenarios:
    """Integration tests based on V17 test cases."""

    def test_gait_cycle_simulation(self):
        """Simulate a complete gait cycle with realistic joint angles."""
        estimator = StateEstimator(dt=0.001, thigh_length=0.48, shank_length=0.52)

        # Simulate 1 second of gait (1 Hz = 1 cycle/s)
        frequency = 1.0  # Hz
        omega = 2 * np.pi * frequency
        dt = 0.001

        hip_positions = []

        for i in range(1000):
            time = i * dt

            # Sinusoidal joint angles (simplified gait)
            hip_angle = 0.3 * np.sin(omega * time)
            knee_angle = 0.5 * np.sin(omega * time + np.pi / 4)
            ankle_angle = 0.2 * np.sin(omega * time - np.pi / 4)

            # Ground force (alternating contact)
            ground_force = 20.0 if np.sin(omega * time) > 0 else 0.0

            result = estimator.update(hip_angle, knee_angle, ankle_angle, ground_force)
            hip_positions.append(result["hip_position"]["y"])

        # Hip height should vary periodically
        hip_std = np.std(hip_positions)
        assert hip_std > 0.01  # Significant variation in gait

    def test_noise_robustness_v17(self):
        """Test robustness to sensor noise (V17 specification)."""
        config = KalmanConfig()
        estimator = StateEstimator(config=config, dt=0.001)

        np.random.seed(42)
        noise_std = 0.005  # 5 mrad noise

        # Constant joint angles with noise
        true_angles = [0.5, 1.0, 0.2]

        raw_measurements = []
        filtered_estimates = []

        for _ in range(1000):
            # Add noise to measurements
            noisy_angles = [
                angle + np.random.normal(0, noise_std) for angle in true_angles
            ]
            raw_measurements.append(noisy_angles[0])

            result = estimator.update(*noisy_angles, ground_force=10.0)
            filtered_estimates.append(result["joints"]["hip"]["angle"])

        # Filtered estimates should be less noisy
        raw_std = np.std(raw_measurements[500:])
        filtered_std = np.std(filtered_estimates[500:])

        assert filtered_std < raw_std * 0.5  # At least 50% noise reduction

    def test_real_time_performance(self):
        """Verify computational efficiency for real-time control."""
        import time

        estimator = StateEstimator(dt=0.001)

        # Warm-up
        for _ in range(100):
            estimator.update(0.1, 0.2, 0.05, 10.0)

        # Time the estimation
        iterations = 1000
        start_time = time.perf_counter()

        for _ in range(iterations):
            estimator.update(0.1, 0.2, 0.05, 10.0)

        elapsed = time.perf_counter() - start_time
        avg_time_ms = (elapsed / iterations) * 1000

        # Should be well under 1ms per update (V17 requirement: 1kHz control)
        assert avg_time_ms < 0.5  # Conservative margin


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
