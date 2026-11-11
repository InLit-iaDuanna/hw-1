"""A-track validation: simulation-driven round-trip verification.

This package synthesizes Hardware V1 ``SampleFrame`` streams from validated
simulation joint-angle trajectories (e.g. V13.7), feeds them through the *same*
``RealtimePipeline`` the live dashboard uses, and compares the recovered L1-L4
outputs against the simulation ground truth.

Scope and academic-integrity note
----------------------------------
This is a **functional / self-consistency** test of the algorithm chain:

* L1 — can the complementary filter recover the segment/joint angles that were
  used to synthesize the IMU frames?
* L2 — do detected heel-strike / toe-off events align with the contact-edge
  times that were injected?
* L3/L4 — are cadence / stance / ROM / symmetry computed correctly from those?

It does **not** verify real-sensor noise robustness (no IMU noise model is the
default) and it does **not** establish clinical validity. Clinical validity
still requires real patient data. Keep these claims separate in any report.
"""

from .runner import EventScore, JointError, ValidationReport, run_validation
from .synth import (
    SynthConfig,
    TrajectorySample,
    TrajectorySynthesizer,
    load_trajectory_csv,
)

__all__ = [
    "TrajectorySynthesizer",
    "SynthConfig",
    "TrajectorySample",
    "load_trajectory_csv",
    "run_validation",
    "ValidationReport",
    "JointError",
    "EventScore",
]
