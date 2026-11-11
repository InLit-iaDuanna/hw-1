"""CLI capture tool for Hardware V1 USB serial binary frames."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from .protocol import FrameParser, NodeDebugFrame, SampleFrame
from .session import SessionWriter, load_gyro_bias


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


def list_serial_ports() -> list[str]:
    try:
        from serial.tools import list_ports  # type: ignore
    except ImportError:
        return []
    return [port.device for port in list_ports.comports()]


def capture(
    port: str,
    baud: int,
    duration_s: float | None,
    output_dir: str | Path | None,
    calibration_path: str | Path | None = None,
) -> Path:
    serial = require_pyserial()
    parser = FrameParser()
    calibration = load_gyro_bias(calibration_path)
    writer = SessionWriter(output_dir=output_dir, calibration=calibration)
    start = time.time()
    last_print = start

    try:
        with serial.Serial(port, baudrate=baud, timeout=0.1) as ser:
            while True:
                if duration_s is not None and time.time() - start >= duration_s:
                    break
                chunk = ser.read(4096)
                if not chunk:
                    continue
                for frame in parser.feed(chunk):
                    if isinstance(frame, SampleFrame):
                        writer.append_frame(frame)
                    elif isinstance(frame, NodeDebugFrame):
                        writer.append_node_frame(frame)

                now = time.time()
                if now - last_print >= 1.0:
                    stats = writer.stats
                    print(
                        f"frames={stats.frames} rate={stats.mcu_frame_rate_hz:.1f}Hz "
                        f"drop={stats.dropped_frames} crc={parser.stats.crc_errors}",
                        flush=True,
                    )
                    last_print = now
    except KeyboardInterrupt:
        print("capture stopped by user", file=sys.stderr)
    finally:
        session_dir = writer.close(parser)

    return session_dir


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--port", help="Serial port, e.g. COM5")
    p.add_argument("--baud", type=int, default=921600)
    p.add_argument(
        "--duration", type=float, default=None, help="Capture duration in seconds"
    )
    p.add_argument("--output", default=None, help="Output root directory")
    p.add_argument(
        "--calibration", default=None, help="gyro_bias.json from calibration"
    )
    p.add_argument(
        "--list-ports", action="store_true", help="List serial ports and exit"
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if args.list_ports:
        for port in list_serial_ports():
            print(port)
        return 0
    if not args.port:
        ports = ", ".join(list_serial_ports()) or "none"
        print(f"--port is required. Available ports: {ports}", file=sys.stderr)
        return 2
    session_dir = capture(
        args.port, args.baud, args.duration, args.output, args.calibration
    )
    print(f"saved session: {session_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
