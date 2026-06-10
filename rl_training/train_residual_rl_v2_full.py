"""Compatibility entry point for the Residual RL V2 sanity training run."""

from __future__ import annotations

import sys
from pathlib import Path

HW1_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HW1_ROOT))

from rl_training.train_sanity_100k import main


if __name__ == "__main__":
    raise SystemExit(main())
