"""
Phase State Machine for Gait Training Device
Based on V13.6 event-driven FSM with 4-phase structure
"""

import time
from enum import IntEnum
from typing import Callable, Optional


class PhaseState(IntEnum):
    """4-phase gait cycle states"""

    STANCE_EARLY = 0  # Heel strike to mid-stance
    STANCE_LATE = 1  # Mid-stance to toe-off
    SWING_THRUST = 2  # Initial swing with thrust assist
    SWING_RETRACT = 3  # Leg retraction and positioning


class PhaseStateMachine:
    """
    Event-driven phase state machine for gait cycle control.

    Transitions based on:
    - Contact sensor events (heel strike, toe-off)
    - Phase duration thresholds (safety timeouts)
    """

    # Phase duration thresholds from V13.6.1 optimal values (seconds)
    PHASE_DURATIONS = {
        PhaseState.STANCE_EARLY: 0.15,  # Early stance phase
        PhaseState.STANCE_LATE: 0.25,  # Late stance phase
        PhaseState.SWING_THRUST: 0.20,  # Swing thrust phase
        PhaseState.SWING_RETRACT: 0.20,  # Swing retract phase
    }

    def __init__(self, log_callback: Optional[Callable[[str], None]] = None):
        """
        Initialize phase state machine.

        Args:
            log_callback: Optional function to call for logging phase transitions
        """
        self.current_phase = PhaseState.STANCE_EARLY
        self.phase_start_time = time.perf_counter()
        self.log_callback = log_callback

        # Transition counters for diagnostics
        self.transition_count = 0
        self.phase_counts = dict.fromkeys(PhaseState, 0)
        self.phase_counts[PhaseState.STANCE_EARLY] = 1

    def update(self, contact: bool) -> bool:
        """
        Update state machine based on contact sensor and time.

        Args:
            contact: True if foot is in contact with ground

        Returns:
            True if phase transition occurred
        """
        phase_time = self.get_phase_time()
        old_phase = self.current_phase
        new_phase = None

        # Event-driven transition logic
        if self.current_phase == PhaseState.STANCE_EARLY:
            # Transition to STANCE_LATE after duration threshold
            if phase_time >= self.PHASE_DURATIONS[PhaseState.STANCE_EARLY]:
                new_phase = PhaseState.STANCE_LATE

        elif self.current_phase == PhaseState.STANCE_LATE:
            # Transition to SWING_THRUST on toe-off (contact lost) or timeout
            if (
                not contact
                or phase_time >= self.PHASE_DURATIONS[PhaseState.STANCE_LATE]
            ):
                new_phase = PhaseState.SWING_THRUST

        elif self.current_phase == PhaseState.SWING_THRUST:
            # Transition to SWING_RETRACT after thrust duration
            if phase_time >= self.PHASE_DURATIONS[PhaseState.SWING_THRUST]:
                new_phase = PhaseState.SWING_RETRACT

        elif self.current_phase == PhaseState.SWING_RETRACT:
            # Transition to STANCE_EARLY on heel strike (contact) or timeout
            if contact or phase_time >= self.PHASE_DURATIONS[PhaseState.SWING_RETRACT]:
                new_phase = PhaseState.STANCE_EARLY

        # Execute transition if triggered
        if new_phase is not None:
            self._transition_to(new_phase)
            return True

        return False

    def _transition_to(self, new_phase: PhaseState):
        """
        Execute phase transition with logging.

        Args:
            new_phase: Target phase state
        """
        old_phase = self.current_phase
        phase_duration = self.get_phase_time()

        self.current_phase = new_phase
        self.phase_start_time = time.perf_counter()
        self.transition_count += 1
        self.phase_counts[new_phase] += 1

        # Log transition
        if self.log_callback:
            log_msg = (
                f"Phase transition: {old_phase.name} -> {new_phase.name} "
                f"(duration: {phase_duration:.3f}s, count: {self.transition_count})"
            )
            self.log_callback(log_msg)

    def get_current_phase(self) -> tuple[int, float]:
        """
        Get current phase state and time in phase.

        Returns:
            Tuple of (phase_id, phase_time)
            - phase_id: Integer phase identifier (0-3)
            - phase_time: Time elapsed in current phase (seconds)
        """
        return int(self.current_phase), self.get_phase_time()

    def get_phase_time(self) -> float:
        """
        Get time elapsed in current phase.

        Returns:
            Time in seconds since phase start
        """
        return time.perf_counter() - self.phase_start_time

    def get_phase_progress(self) -> float:
        """
        Get normalized progress through current phase.

        Returns:
            Progress in range [0.0, 1.0], may exceed 1.0 if phase overruns
        """
        phase_time = self.get_phase_time()
        expected_duration = self.PHASE_DURATIONS[self.current_phase]
        return phase_time / expected_duration if expected_duration > 0 else 0.0

    def reset(self):
        """Reset state machine to initial stance phase."""
        old_phase = self.current_phase
        self.current_phase = PhaseState.STANCE_EARLY
        self.phase_start_time = time.perf_counter()

        if self.log_callback and old_phase != PhaseState.STANCE_EARLY:
            self.log_callback(f"Phase FSM reset to {PhaseState.STANCE_EARLY.name}")

    def get_statistics(self) -> dict:
        """
        Get state machine diagnostic statistics.

        Returns:
            Dictionary with transition counts and phase visit counts
        """
        return {
            "current_phase": self.current_phase.name,
            "phase_time": self.get_phase_time(),
            "phase_progress": self.get_phase_progress(),
            "total_transitions": self.transition_count,
            "phase_counts": {
                phase.name: count for phase, count in self.phase_counts.items()
            },
        }


# Example usage
if __name__ == "__main__":

    def log_transition(msg: str):
        print(f"[{time.perf_counter():.3f}] {msg}")

    fsm = PhaseStateMachine(log_callback=log_transition)

    print("Phase State Machine Test")
    print(f"Initial phase: {fsm.current_phase.name}\n")

    # Simulate gait cycle with contact patterns
    contact_sequence = [
        (0.05, True),  # Early stance
        (0.10, True),  # Early stance continuing
        (0.16, True),  # Transition to late stance
        (0.30, True),  # Late stance
        (0.41, False),  # Toe-off -> swing thrust
        (0.50, False),  # Swing thrust
        (0.62, False),  # Swing retract
        (0.75, False),  # Swing retract continuing
        (0.83, True),  # Heel strike -> stance early
    ]

    start_time = time.perf_counter()
    for delay, contact in contact_sequence:
        # Wait to simulate real-time
        while time.perf_counter() - start_time < delay:
            time.sleep(0.001)

        # Update FSM
        transitioned = fsm.update(contact)
        phase_id, phase_time = fsm.get_current_phase()

        print(
            f"t={delay:.2f}s contact={contact} -> Phase {phase_id} ({PhaseState(phase_id).name}), "
            f"time={phase_time:.3f}s, progress={fsm.get_phase_progress():.1%}"
        )

    print("\nStatistics:")
    stats = fsm.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")
