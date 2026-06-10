"""
Unit tests for Phase State Machine (phase_fsm.py)

Tests cover:
- State transitions (normal flow)
- Event detection (contact-driven transitions)
- Phase timing and timeouts
- Edge cases (missed contact, rapid transitions, reset)
"""

import unittest
import time
from unittest.mock import Mock
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from phase_fsm import PhaseStateMachine, PhaseState


class TestPhaseStateMachine(unittest.TestCase):
    """Test suite for PhaseStateMachine"""

    def setUp(self):
        """Create fresh FSM instance before each test"""
        self.log_mock = Mock()
        self.fsm = PhaseStateMachine(log_callback=self.log_mock)

    def test_initial_state(self):
        """FSM should start in STANCE_EARLY"""
        self.assertEqual(self.fsm.current_phase, PhaseState.STANCE_EARLY)
        phase_id, phase_time = self.fsm.get_current_phase()
        self.assertEqual(phase_id, 0)
        self.assertGreaterEqual(phase_time, 0.0)
        self.assertLess(phase_time, 0.01)  # Should be near zero

    def test_stance_early_to_stance_late_timeout(self):
        """STANCE_EARLY -> STANCE_LATE after duration threshold"""
        # Wait for transition threshold
        threshold = PhaseStateMachine.PHASE_DURATIONS[PhaseState.STANCE_EARLY]
        time.sleep(threshold + 0.01)

        # Update with contact still true
        transitioned = self.fsm.update(contact=True)

        self.assertTrue(transitioned)
        self.assertEqual(self.fsm.current_phase, PhaseState.STANCE_LATE)
        self.assertEqual(self.fsm.transition_count, 1)

    def test_stance_late_to_swing_thrust_on_toe_off(self):
        """STANCE_LATE -> SWING_THRUST on contact loss (toe-off)"""
        # Force to STANCE_LATE
        self.fsm.current_phase = PhaseState.STANCE_LATE
        self.fsm.phase_start_time = time.perf_counter()

        # Lose contact (toe-off event)
        transitioned = self.fsm.update(contact=False)

        self.assertTrue(transitioned)
        self.assertEqual(self.fsm.current_phase, PhaseState.SWING_THRUST)

    def test_stance_late_to_swing_thrust_timeout(self):
        """STANCE_LATE -> SWING_THRUST on timeout even with contact"""
        # Force to STANCE_LATE
        self.fsm.current_phase = PhaseState.STANCE_LATE
        self.fsm.phase_start_time = time.perf_counter()

        # Wait for timeout
        threshold = PhaseStateMachine.PHASE_DURATIONS[PhaseState.STANCE_LATE]
        time.sleep(threshold + 0.01)

        # Update with contact still true (timeout should trigger)
        transitioned = self.fsm.update(contact=True)

        self.assertTrue(transitioned)
        self.assertEqual(self.fsm.current_phase, PhaseState.SWING_THRUST)

    def test_swing_thrust_to_swing_retract_timeout(self):
        """SWING_THRUST -> SWING_RETRACT after duration threshold"""
        # Force to SWING_THRUST
        self.fsm.current_phase = PhaseState.SWING_THRUST
        self.fsm.phase_start_time = time.perf_counter()

        # Wait for transition
        threshold = PhaseStateMachine.PHASE_DURATIONS[PhaseState.SWING_THRUST]
        time.sleep(threshold + 0.01)

        transitioned = self.fsm.update(contact=False)

        self.assertTrue(transitioned)
        self.assertEqual(self.fsm.current_phase, PhaseState.SWING_RETRACT)

    def test_swing_retract_to_stance_early_on_heel_strike(self):
        """SWING_RETRACT -> STANCE_EARLY on contact (heel strike)"""
        # Force to SWING_RETRACT
        self.fsm.current_phase = PhaseState.SWING_RETRACT
        self.fsm.phase_start_time = time.perf_counter()

        # Heel strike (contact event)
        transitioned = self.fsm.update(contact=True)

        self.assertTrue(transitioned)
        self.assertEqual(self.fsm.current_phase, PhaseState.STANCE_EARLY)

    def test_swing_retract_to_stance_early_timeout(self):
        """SWING_RETRACT -> STANCE_EARLY on timeout (missed heel strike)"""
        # Force to SWING_RETRACT
        self.fsm.current_phase = PhaseState.SWING_RETRACT
        self.fsm.phase_start_time = time.perf_counter()

        # Wait for timeout
        threshold = PhaseStateMachine.PHASE_DURATIONS[PhaseState.SWING_RETRACT]
        time.sleep(threshold + 0.01)

        # No contact, but timeout should trigger
        transitioned = self.fsm.update(contact=False)

        self.assertTrue(transitioned)
        self.assertEqual(self.fsm.current_phase, PhaseState.STANCE_EARLY)

    def test_full_gait_cycle(self):
        """Complete gait cycle: all 4 phases in sequence"""
        expected_sequence = [
            PhaseState.STANCE_EARLY,
            PhaseState.STANCE_LATE,
            PhaseState.SWING_THRUST,
            PhaseState.SWING_RETRACT,
            PhaseState.STANCE_EARLY,  # Back to start
        ]

        phase_sequence = [self.fsm.current_phase]

        # STANCE_EARLY -> STANCE_LATE
        time.sleep(0.16)
        self.fsm.update(contact=True)
        phase_sequence.append(self.fsm.current_phase)

        # STANCE_LATE -> SWING_THRUST (toe-off)
        self.fsm.update(contact=False)
        phase_sequence.append(self.fsm.current_phase)

        # SWING_THRUST -> SWING_RETRACT
        time.sleep(0.21)
        self.fsm.update(contact=False)
        phase_sequence.append(self.fsm.current_phase)

        # SWING_RETRACT -> STANCE_EARLY (heel strike)
        self.fsm.update(contact=True)
        phase_sequence.append(self.fsm.current_phase)

        self.assertEqual(phase_sequence, expected_sequence)
        self.assertEqual(self.fsm.transition_count, 4)

    def test_no_transition_when_conditions_not_met(self):
        """No transition when timing and contact conditions not met"""
        # Start in STANCE_EARLY, not enough time passed
        transitioned = self.fsm.update(contact=True)
        self.assertFalse(transitioned)
        self.assertEqual(self.fsm.current_phase, PhaseState.STANCE_EARLY)

        # Force to STANCE_LATE, contact still present
        self.fsm.current_phase = PhaseState.STANCE_LATE
        self.fsm.phase_start_time = time.perf_counter()
        transitioned = self.fsm.update(contact=True)
        self.assertFalse(transitioned)
        self.assertEqual(self.fsm.current_phase, PhaseState.STANCE_LATE)

    def test_phase_time_tracking(self):
        """Phase time should increase monotonically within phase"""
        time.sleep(0.05)
        t1 = self.fsm.get_phase_time()

        time.sleep(0.05)
        t2 = self.fsm.get_phase_time()

        self.assertGreater(t2, t1)
        self.assertAlmostEqual(t2 - t1, 0.05, delta=0.02)

    def test_phase_progress_calculation(self):
        """Phase progress should be normalized to [0.0, 1.0]"""
        # At start of phase
        progress_start = self.fsm.get_phase_progress()
        self.assertGreaterEqual(progress_start, 0.0)
        self.assertLess(progress_start, 0.1)

        # Halfway through STANCE_EARLY (0.15s duration)
        time.sleep(0.075)
        progress_mid = self.fsm.get_phase_progress()
        self.assertGreater(progress_mid, 0.4)
        self.assertLess(progress_mid, 0.6)

        # After timeout (can exceed 1.0)
        time.sleep(0.10)
        progress_over = self.fsm.get_phase_progress()
        self.assertGreater(progress_over, 1.0)

    def test_transition_logging(self):
        """Log callback should be called on transitions"""
        # Trigger a transition
        self.fsm.current_phase = PhaseState.STANCE_LATE
        self.fsm.phase_start_time = time.perf_counter()
        self.fsm.update(contact=False)

        # Check log was called
        self.log_mock.assert_called_once()
        call_args = self.log_mock.call_args[0][0]
        self.assertIn("STANCE_LATE", call_args)
        self.assertIn("SWING_THRUST", call_args)
        self.assertIn("duration:", call_args)

    def test_phase_counts_tracking(self):
        """Phase counts should track visits to each phase"""
        # Initial: STANCE_EARLY count = 1
        self.assertEqual(self.fsm.phase_counts[PhaseState.STANCE_EARLY], 1)
        self.assertEqual(self.fsm.phase_counts[PhaseState.STANCE_LATE], 0)

        # Transition to STANCE_LATE
        time.sleep(0.16)
        self.fsm.update(contact=True)
        self.assertEqual(self.fsm.phase_counts[PhaseState.STANCE_LATE], 1)

        # Complete cycle back to STANCE_EARLY
        self.fsm.update(contact=False)  # -> SWING_THRUST
        time.sleep(0.21)
        self.fsm.update(contact=False)  # -> SWING_RETRACT
        self.fsm.update(contact=True)   # -> STANCE_EARLY

        self.assertEqual(self.fsm.phase_counts[PhaseState.STANCE_EARLY], 2)
        self.assertEqual(self.fsm.phase_counts[PhaseState.SWING_THRUST], 1)
        self.assertEqual(self.fsm.phase_counts[PhaseState.SWING_RETRACT], 1)

    def test_reset_functionality(self):
        """Reset should return FSM to STANCE_EARLY"""
        # Move to different phase
        self.fsm.current_phase = PhaseState.SWING_THRUST
        self.fsm.transition_count = 5

        # Reset
        self.fsm.reset()

        self.assertEqual(self.fsm.current_phase, PhaseState.STANCE_EARLY)
        phase_time = self.fsm.get_phase_time()
        self.assertLess(phase_time, 0.01)

        # Should log reset
        self.log_mock.assert_called()
        call_args = self.log_mock.call_args[0][0]
        self.assertIn("reset", call_args.lower())

    def test_statistics_output(self):
        """Get statistics should return complete diagnostic info"""
        # Advance through some phases
        time.sleep(0.16)
        self.fsm.update(contact=True)
        self.fsm.update(contact=False)

        stats = self.fsm.get_statistics()

        self.assertIn('current_phase', stats)
        self.assertIn('phase_time', stats)
        self.assertIn('phase_progress', stats)
        self.assertIn('total_transitions', stats)
        self.assertIn('phase_counts', stats)

        self.assertEqual(stats['current_phase'], 'SWING_THRUST')
        self.assertEqual(stats['total_transitions'], 2)
        self.assertIsInstance(stats['phase_counts'], dict)

    def test_edge_case_missed_toe_off(self):
        """Timeout should handle missed toe-off sensor event"""
        # In STANCE_LATE, contact sensor stuck at True
        self.fsm.current_phase = PhaseState.STANCE_LATE
        self.fsm.phase_start_time = time.perf_counter()

        # Wait for timeout
        time.sleep(0.26)

        # Should transition even without toe-off event
        transitioned = self.fsm.update(contact=True)

        self.assertTrue(transitioned)
        self.assertEqual(self.fsm.current_phase, PhaseState.SWING_THRUST)

    def test_edge_case_missed_heel_strike(self):
        """Timeout should handle missed heel strike sensor event"""
        # In SWING_RETRACT, contact sensor stuck at False
        self.fsm.current_phase = PhaseState.SWING_RETRACT
        self.fsm.phase_start_time = time.perf_counter()

        # Wait for timeout
        time.sleep(0.21)

        # Should transition even without heel strike event
        transitioned = self.fsm.update(contact=False)

        self.assertTrue(transitioned)
        self.assertEqual(self.fsm.current_phase, PhaseState.STANCE_EARLY)

    def test_edge_case_rapid_updates(self):
        """Multiple rapid updates should not cause spurious transitions"""
        # Rapid updates within same phase
        for _ in range(10):
            transitioned = self.fsm.update(contact=True)
            self.assertFalse(transitioned)

        self.assertEqual(self.fsm.current_phase, PhaseState.STANCE_EARLY)
        self.assertEqual(self.fsm.transition_count, 0)

    def test_edge_case_contact_bounce(self):
        """Contact sensor bounce should not trigger premature transitions"""
        # In SWING_THRUST, brief contact should not transition
        self.fsm.current_phase = PhaseState.SWING_THRUST
        self.fsm.phase_start_time = time.perf_counter()

        # Brief contact
        transitioned = self.fsm.update(contact=True)

        # Should NOT transition (SWING_THRUST only transitions on time)
        self.assertFalse(transitioned)
        self.assertEqual(self.fsm.current_phase, PhaseState.SWING_THRUST)

    def test_multiple_complete_cycles(self):
        """Multiple gait cycles should maintain correct count"""
        cycles = 3
        expected_transitions = cycles * 4  # 4 transitions per cycle

        for _ in range(cycles):
            # STANCE_EARLY -> STANCE_LATE
            time.sleep(0.16)
            self.fsm.update(contact=True)

            # STANCE_LATE -> SWING_THRUST
            self.fsm.update(contact=False)

            # SWING_THRUST -> SWING_RETRACT
            time.sleep(0.21)
            self.fsm.update(contact=False)

            # SWING_RETRACT -> STANCE_EARLY
            self.fsm.update(contact=True)

        self.assertEqual(self.fsm.transition_count, expected_transitions)
        self.assertEqual(self.fsm.current_phase, PhaseState.STANCE_EARLY)
        self.assertEqual(self.fsm.phase_counts[PhaseState.STANCE_EARLY], cycles + 1)

    def test_fsm_without_log_callback(self):
        """FSM should work without log callback"""
        fsm_no_log = PhaseStateMachine(log_callback=None)

        # Should not raise exception
        time.sleep(0.16)
        transitioned = fsm_no_log.update(contact=True)

        self.assertTrue(transitioned)
        self.assertEqual(fsm_no_log.current_phase, PhaseState.STANCE_LATE)


class TestPhaseStateEnum(unittest.TestCase):
    """Test PhaseState enum properties"""

    def test_phase_values(self):
        """Phase enum should have correct integer values"""
        self.assertEqual(PhaseState.STANCE_EARLY, 0)
        self.assertEqual(PhaseState.STANCE_LATE, 1)
        self.assertEqual(PhaseState.SWING_THRUST, 2)
        self.assertEqual(PhaseState.SWING_RETRACT, 3)

    def test_phase_names(self):
        """Phase enum should have correct names"""
        self.assertEqual(PhaseState.STANCE_EARLY.name, "STANCE_EARLY")
        self.assertEqual(PhaseState.STANCE_LATE.name, "STANCE_LATE")
        self.assertEqual(PhaseState.SWING_THRUST.name, "SWING_THRUST")
        self.assertEqual(PhaseState.SWING_RETRACT.name, "SWING_RETRACT")


if __name__ == '__main__':
    unittest.main(verbosity=2)
