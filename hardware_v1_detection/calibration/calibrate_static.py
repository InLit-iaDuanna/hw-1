"""Static gyro-bias calibration for Hardware V1.

Keep all five sensors still during the capture. The script writes gyro_bias.json
that can be passed to serial_capture.py or the PyQt demo.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hardware_v1_detection.pc_receiver.protocol import BMI_SENSOR_NAMES, FrameParser, SampleFrame


def require_pyserial():
    try:
        import serial  # type: ignore
    except ImportError as exc:  # pragma: no cover - environment guard
        raise SystemExit(
            "Missing dependency: pyserial. Install with "
            "`.venv-mujoco\\Scripts\\python.exe -m pip install -r "
            "hardware_v1_detection\\requirements.txt`."
        ) from exc
    return serial


def calibrate(port: str, baud: int, duration_s: float, output: str | Path) -> Path:
    serial = require_pyserial()
    parser = FrameParser()
    samples = {name: {"gx": [], "gy": [], "gz": []} for name in (*BMI_SENSOR_NAMES, "pelvis")}
    deadline = time.time() + duration_s

    with serial.Serial(port, baudrate=baud, timeout=0.1) as ser:
        while time.time() < deadline:
            for frame in parser.feed(ser.read(4096)):
                if not isinstance(frame, SampleFrame):
                    continue
                for name, imu in zip(BMI_SENSOR_NAMES, frame.bmi):
                    samples[name]["gx"].append(imu.gx)
                    samples[name]["gy"].append(imu.gy)
                    samples[name]["gz"].append(imu.gz)
                samples["pelvis"]["gx"].append(frame.pelvis.gx)
                samples["pelvis"]["gy"].append(frame.pelvis.gy)
                samples["pelvis"]["gz"].append(frame.pelvis.gz)

    bias = {}
    for name, axes in samples.items():
        bias[name] = {
            axis: statistics.fmean(values) if values else 0.0
            for axis, values in axes.items()
        }

    result = {
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "duration_s": duration_s,
        "frames": parser.stats.frames_ok,
        "gyro_bias_raw": bias,
    }
    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--port", required=True)
    p.add_argument("--baud", type=int, default=921600)
    p.add_argument("--duration", type=float, default=10.0)
    p.add_argument("--output", default="hardware_v1_detection/calibration/gyro_bias.json")
    args = p.parse_args(argv)
    out = calibrate(args.port, args.baud, args.duration, args.output)
    print(f"saved calibration: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
