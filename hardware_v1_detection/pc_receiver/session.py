"""Session logging for Hardware V1 captures."""

from __future__ import annotations

import csv
import json
import time
from pathlib import Path

import numpy as np

from .protocol import (
    BMI_SENSOR_NAMES,
    SENSOR_NAMES,
    CaptureStats,
    FrameParser,
    Imu6,
    NodeDebugFrame,
    SampleFrame,
    scale_sensor,
)


def timestamped_session_dir(root: str | Path | None = None) -> Path:
    base = Path(root or Path.cwd() / "hardware_v1_sessions")
    name = time.strftime("session_%Y%m%d_%H%M%S")
    path = base / name
    path.mkdir(parents=True, exist_ok=False)
    return path


def load_gyro_bias(path: str | Path | None) -> dict:
    if path is None:
        return {}
    with Path(path).open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("gyro_bias_raw", data)


class SessionWriter:
    def __init__(
        self, output_dir: str | Path | None = None, calibration: dict | None = None
    ):
        self.path = timestamped_session_dir(output_dir)
        self.calibration = calibration or {}
        self.stats = CaptureStats()
        self._seq: list[int] = []
        self._ts_us: list[int] = []
        self._status: list[int] = []
        self._raw_values: list[tuple[int, ...]] = []
        self._node_packets = 0
        self._node_drops = 0
        self._node_last_seq: dict[int, int] = {}
        self._node_age_ms: list[int] = []
        self._node_temp_c: list[float] = []

        self._raw_file = (self.path / "raw.csv").open("w", newline="", encoding="utf-8")
        self._scaled_file = (self.path / "scaled.csv").open(
            "w", newline="", encoding="utf-8"
        )
        self._node_file = (self.path / "node_raw.csv").open(
            "w", newline="", encoding="utf-8"
        )
        self._raw_writer = csv.DictWriter(
            self._raw_file,
            fieldnames=[
                "seq",
                "ts_us",
                "sensor_name",
                "ax",
                "ay",
                "az",
                "gx",
                "gy",
                "gz",
                "mx",
                "my",
                "mz",
                "status",
            ],
        )
        self._scaled_writer = csv.DictWriter(
            self._scaled_file,
            fieldnames=[
                "seq",
                "ts_us",
                "sensor_name",
                "ax_g",
                "ay_g",
                "az_g",
                "gx_dps",
                "gy_dps",
                "gz_dps",
                "mx_raw",
                "my_raw",
                "mz_raw",
                "status",
            ],
        )
        self._node_writer = csv.DictWriter(
            self._node_file,
            fieldnames=[
                "hub_seq",
                "hub_ts_us",
                "hub_status",
                "node_id",
                "node_status",
                "age_ms",
                "c3_seq",
                "c3_ts_us",
                "s3_rx_ts_us",
                "ax",
                "ay",
                "az",
                "gx",
                "gy",
                "gz",
                "temp_c",
            ],
        )
        self._raw_writer.writeheader()
        self._scaled_writer.writeheader()
        self._node_writer.writeheader()

    def append_frame(self, frame: SampleFrame) -> None:
        self.stats.update(frame)
        self._seq.append(frame.seq)
        self._ts_us.append(frame.ts_us)
        self._status.append(frame.status)
        self._raw_values.append(frame.raw_values())

        for sensor_name, imu in zip(BMI_SENSOR_NAMES, frame.bmi):
            self._write_imu6(frame, sensor_name, imu)
        self._write_pelvis(frame)

    def append_node_frame(self, frame: NodeDebugFrame) -> None:
        self._node_packets += 1
        previous_seq = self._node_last_seq.get(frame.node_id)
        if previous_seq is not None and frame.c3_seq > previous_seq + 1:
            self._node_drops += frame.c3_seq - previous_seq - 1
        self._node_last_seq[frame.node_id] = frame.c3_seq
        self._node_age_ms.append(frame.age_ms)
        temp_c = frame.temp_c
        if temp_c is not None:
            self._node_temp_c.append(temp_c)
        imu = frame.imu
        self._node_writer.writerow(
            {
                "hub_seq": frame.seq,
                "hub_ts_us": frame.ts_us,
                "hub_status": frame.status,
                "node_id": frame.node_id,
                "node_status": frame.node_status,
                "age_ms": frame.age_ms,
                "c3_seq": frame.c3_seq,
                "c3_ts_us": frame.c3_ts_us,
                "s3_rx_ts_us": frame.s3_rx_ts_us,
                "ax": imu.ax,
                "ay": imu.ay,
                "az": imu.az,
                "gx": imu.gx,
                "gy": imu.gy,
                "gz": imu.gz,
                "temp_c": "" if temp_c is None else f"{temp_c:.2f}",
            }
        )

    def _write_imu6(self, frame: SampleFrame, sensor_name: str, imu: Imu6) -> None:
        self._raw_writer.writerow(
            {
                "seq": frame.seq,
                "ts_us": frame.ts_us,
                "sensor_name": sensor_name,
                "ax": imu.ax,
                "ay": imu.ay,
                "az": imu.az,
                "gx": imu.gx,
                "gy": imu.gy,
                "gz": imu.gz,
                "mx": "",
                "my": "",
                "mz": "",
                "status": frame.status,
            }
        )
        scaled = scale_sensor(sensor_name, imu, self.calibration)
        self._scaled_writer.writerow(
            {
                "seq": frame.seq,
                "ts_us": frame.ts_us,
                "sensor_name": sensor_name,
                **scaled,
                "mx_raw": "",
                "my_raw": "",
                "mz_raw": "",
                "status": frame.status,
            }
        )

    def _write_pelvis(self, frame: SampleFrame) -> None:
        imu = frame.pelvis
        self._raw_writer.writerow(
            {
                "seq": frame.seq,
                "ts_us": frame.ts_us,
                "sensor_name": "pelvis",
                "ax": imu.ax,
                "ay": imu.ay,
                "az": imu.az,
                "gx": imu.gx,
                "gy": imu.gy,
                "gz": imu.gz,
                "mx": imu.mx,
                "my": imu.my,
                "mz": imu.mz,
                "status": frame.status,
            }
        )
        scaled = scale_sensor("pelvis", imu, self.calibration)
        self._scaled_writer.writerow(
            {
                "seq": frame.seq,
                "ts_us": frame.ts_us,
                "sensor_name": "pelvis",
                **scaled,
                "status": frame.status,
            }
        )

    def close(
        self, parser: FrameParser | None = None, extra: dict | None = None
    ) -> Path:
        self._raw_file.flush()
        self._scaled_file.flush()
        self._node_file.flush()
        self._raw_file.close()
        self._scaled_file.close()
        self._node_file.close()

        np.savez_compressed(
            self.path / "raw.npz",
            seq=np.asarray(self._seq, dtype=np.uint32),
            ts_us=np.asarray(self._ts_us, dtype=np.uint64),
            status=np.asarray(self._status, dtype=np.uint16),
            values=np.asarray(self._raw_values, dtype=np.int16),
            sensor_names=np.asarray(SENSOR_NAMES),
        )

        summary = self.stats.to_dict(parser.stats if parser else None)
        summary["espnow_packets"] = self._node_packets
        summary["node_drops"] = self._node_drops
        summary["node_age_ms_p95"] = self._node_age_p95()
        if self._node_temp_c:
            summary["node_temp_c_last"] = self._node_temp_c[-1]
            summary["node_temp_c_max"] = max(self._node_temp_c)
        summary["session_dir"] = str(self.path)
        summary["calibration_loaded"] = bool(self.calibration)
        if extra:
            summary.update(extra)
        with (self.path / "session_summary.json").open("w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        return self.path

    def __enter__(self) -> SessionWriter:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _node_age_p95(self) -> float:
        if not self._node_age_ms:
            return 0.0
        values = sorted(self._node_age_ms)
        index = min(len(values) - 1, int(round(0.95 * (len(values) - 1))))
        return float(values[index])
