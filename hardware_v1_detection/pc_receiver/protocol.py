"""Binary protocol parser for Hardware V1 ESP32-S3 sensor frames."""

from __future__ import annotations

import struct
import time
from collections.abc import Iterable
from dataclasses import dataclass, field

MAGIC = 0xA55A
MAGIC_BYTES = struct.pack("<H", MAGIC)
VERSION = 1
FRAME_TYPE_SAMPLE = 0x01
FRAME_TYPE_NODE_DEBUG = 0x11
HEADER_FORMAT = "<HBBHIQH"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
CRC_SIZE = 2
BMI_SENSOR_COUNT = 6
SAMPLE_VALUE_COUNT = BMI_SENSOR_COUNT * 6 + 9
SAMPLE_PAYLOAD_FORMAT = "<" + "h" * SAMPLE_VALUE_COUNT
SAMPLE_PAYLOAD_SIZE = struct.calcsize(SAMPLE_PAYLOAD_FORMAT)
NODE_DEBUG_PAYLOAD_FORMAT_V1 = "<BBHIQQhhhhhh"
NODE_DEBUG_PAYLOAD_SIZE_V1 = struct.calcsize(NODE_DEBUG_PAYLOAD_FORMAT_V1)
NODE_DEBUG_PAYLOAD_FORMAT = NODE_DEBUG_PAYLOAD_FORMAT_V1 + "h"
NODE_DEBUG_PAYLOAD_SIZE = struct.calcsize(NODE_DEBUG_PAYLOAD_FORMAT)
MAX_PAYLOAD_SIZE = 512

SENSOR_NAMES = (
    "left_foot",
    "right_foot",
    "left_shank",
    "right_shank",
    "left_thigh",
    "right_thigh",
    "pelvis",
)
BMI_SENSOR_NAMES = SENSOR_NAMES[:BMI_SENSOR_COUNT]

BMI_ACCEL_LSB_PER_G = 4096.0
BMI_GYRO_LSB_PER_DPS = 32.768
BMX_ACCEL_LSB_PER_G = 256.0
BMX_GYRO_LSB_PER_DPS = 32.768

STATUS_BITS = {
    0: "left_foot_fail",
    1: "right_foot_fail",
    2: "left_shank_fail",
    3: "right_shank_fail",
    4: "left_thigh_fail",
    5: "right_thigh_fail",
    6: "pelvis_fail",
    15: "init_incomplete",
}


def crc16_ccitt(data: bytes | bytearray | memoryview) -> int:
    """CRC-16/CCITT-FALSE, matching the ESP-IDF firmware."""

    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


@dataclass(frozen=True)
class Imu6:
    ax: int
    ay: int
    az: int
    gx: int
    gy: int
    gz: int


@dataclass(frozen=True)
class Imu9:
    ax: int
    ay: int
    az: int
    gx: int
    gy: int
    gz: int
    mx: int
    my: int
    mz: int


@dataclass(frozen=True)
class SampleFrame:
    version: int
    frame_type: int
    seq: int
    ts_us: int
    status: int
    bmi: tuple[Imu6, ...]
    pelvis: Imu9
    received_at: float = field(default_factory=time.time)

    @classmethod
    def from_payload(
        cls,
        version: int,
        frame_type: int,
        seq: int,
        ts_us: int,
        status: int,
        payload: bytes,
    ) -> SampleFrame:
        if frame_type != FRAME_TYPE_SAMPLE:
            raise ValueError(f"unsupported frame type: {frame_type}")
        if len(payload) != SAMPLE_PAYLOAD_SIZE:
            raise ValueError(
                f"sample payload must be {SAMPLE_PAYLOAD_SIZE} bytes, got {len(payload)}"
            )
        values = struct.unpack(SAMPLE_PAYLOAD_FORMAT, payload)
        bmi = []
        cursor = 0
        for _ in range(BMI_SENSOR_COUNT):
            bmi.append(Imu6(*values[cursor : cursor + 6]))
            cursor += 6
        pelvis = Imu9(*values[cursor : cursor + 9])
        return cls(
            version=version,
            frame_type=frame_type,
            seq=seq,
            ts_us=ts_us,
            status=status,
            bmi=tuple(bmi),
            pelvis=pelvis,
        )

    def status_names(self) -> list[str]:
        return [name for bit, name in STATUS_BITS.items() if self.status & (1 << bit)]

    def raw_values(self) -> tuple[int, ...]:
        values: list[int] = []
        for imu in self.bmi:
            values.extend((imu.ax, imu.ay, imu.az, imu.gx, imu.gy, imu.gz))
        values.extend(
            (
                self.pelvis.ax,
                self.pelvis.ay,
                self.pelvis.az,
                self.pelvis.gx,
                self.pelvis.gy,
                self.pelvis.gz,
                self.pelvis.mx,
                self.pelvis.my,
                self.pelvis.mz,
            )
        )
        return tuple(values)


@dataclass(frozen=True)
class NodeDebugFrame:
    version: int
    frame_type: int
    seq: int
    ts_us: int
    status: int
    node_id: int
    node_status: int
    age_ms: int
    c3_seq: int
    c3_ts_us: int
    s3_rx_ts_us: int
    imu: Imu6
    temp_centi_c: int | None = None
    received_at: float = field(default_factory=time.time)

    @property
    def temp_c(self) -> float | None:
        if self.temp_centi_c is None or self.temp_centi_c == -32768:
            return None
        return self.temp_centi_c / 100.0

    @classmethod
    def from_payload(
        cls,
        version: int,
        frame_type: int,
        seq: int,
        ts_us: int,
        status: int,
        payload: bytes,
    ) -> NodeDebugFrame:
        if frame_type != FRAME_TYPE_NODE_DEBUG:
            raise ValueError(f"unsupported node debug frame type: {frame_type}")
        if len(payload) not in (NODE_DEBUG_PAYLOAD_SIZE_V1, NODE_DEBUG_PAYLOAD_SIZE):
            raise ValueError(
                "node debug payload must be "
                f"{NODE_DEBUG_PAYLOAD_SIZE_V1} or {NODE_DEBUG_PAYLOAD_SIZE} bytes, "
                f"got {len(payload)}"
            )
        unpacked = struct.unpack(
            (
                NODE_DEBUG_PAYLOAD_FORMAT
                if len(payload) == NODE_DEBUG_PAYLOAD_SIZE
                else NODE_DEBUG_PAYLOAD_FORMAT_V1
            ),
            payload,
        )
        (
            node_id,
            node_status,
            age_ms,
            c3_seq,
            c3_ts_us,
            s3_rx_ts_us,
            ax,
            ay,
            az,
            gx,
            gy,
            gz,
            *tail,
        ) = unpacked
        temp_centi_c = tail[0] if tail else None
        return cls(
            version=version,
            frame_type=frame_type,
            seq=seq,
            ts_us=ts_us,
            status=status,
            node_id=node_id,
            node_status=node_status,
            age_ms=age_ms,
            c3_seq=c3_seq,
            c3_ts_us=c3_ts_us,
            s3_rx_ts_us=s3_rx_ts_us,
            imu=Imu6(ax, ay, az, gx, gy, gz),
            temp_centi_c=temp_centi_c,
        )


ParsedFrame = SampleFrame | NodeDebugFrame


@dataclass
class ParserStats:
    bytes_in: int = 0
    frames_ok: int = 0
    crc_errors: int = 0
    version_errors: int = 0
    length_errors: int = 0
    resync_bytes: int = 0
    sample_frames: int = 0
    node_debug_frames: int = 0


class FrameParser:
    """Streaming parser with magic-byte resynchronization."""

    def __init__(self) -> None:
        self.buffer = bytearray()
        self.stats = ParserStats()

    def _drop_bad_candidate(self, payload_len: int | None = None) -> None:
        """Drop a corrupt frame candidate without byte-by-byte rescanning."""

        drop_len = len(MAGIC_BYTES)
        if payload_len is not None and payload_len <= MAX_PAYLOAD_SIZE:
            total_len = HEADER_SIZE + payload_len + CRC_SIZE
            if len(self.buffer) >= total_len:
                drop_len = total_len
        del self.buffer[:drop_len]
        self.stats.resync_bytes += drop_len

    def feed(self, data: bytes | bytearray | memoryview) -> list[ParsedFrame]:
        self.stats.bytes_in += len(data)
        self.buffer.extend(data)
        frames: list[ParsedFrame] = []

        while True:
            magic_at = self.buffer.find(MAGIC_BYTES)
            if magic_at < 0:
                if self.buffer:
                    self.stats.resync_bytes += len(self.buffer)
                    self.buffer.clear()
                break
            if magic_at > 0:
                del self.buffer[:magic_at]
                self.stats.resync_bytes += magic_at

            if len(self.buffer) < HEADER_SIZE:
                break

            magic, version, frame_type, payload_len, seq, ts_us, status = struct.unpack(
                HEADER_FORMAT, self.buffer[:HEADER_SIZE]
            )
            if magic != MAGIC:
                self._drop_bad_candidate()
                continue
            if version != VERSION:
                self.stats.version_errors += 1
                self._drop_bad_candidate(payload_len)
                continue
            if payload_len > MAX_PAYLOAD_SIZE:
                self.stats.length_errors += 1
                self._drop_bad_candidate()
                continue

            total_len = HEADER_SIZE + payload_len + CRC_SIZE
            if len(self.buffer) < total_len:
                break

            packet = bytes(self.buffer[:total_len])
            expected_crc = struct.unpack("<H", packet[-CRC_SIZE:])[0]
            actual_crc = crc16_ccitt(packet[:-CRC_SIZE])
            if expected_crc != actual_crc:
                self.stats.crc_errors += 1
                self._drop_bad_candidate(payload_len)
                continue

            payload = packet[HEADER_SIZE:-CRC_SIZE]
            if frame_type == FRAME_TYPE_SAMPLE:
                frame = SampleFrame.from_payload(
                    version, frame_type, seq, ts_us, status, payload
                )
                self.stats.sample_frames += 1
            elif frame_type == FRAME_TYPE_NODE_DEBUG:
                frame = NodeDebugFrame.from_payload(
                    version, frame_type, seq, ts_us, status, payload
                )
                self.stats.node_debug_frames += 1
            else:
                self.stats.length_errors += 1
                self._drop_bad_candidate(payload_len)
                continue
            frames.append(frame)
            self.stats.frames_ok += 1
            del self.buffer[:total_len]

        return frames


@dataclass
class CaptureStats:
    expected_sample_rate_hz: float = 200.0
    frames: int = 0
    dropped_frames: int = 0
    status_counts: dict[str, int] = field(
        default_factory=lambda: dict.fromkeys(STATUS_BITS.values(), 0)
    )
    first_seq: int | None = None
    last_seq: int | None = None
    first_ts_us: int | None = None
    last_ts_us: int | None = None
    first_pc_time: float | None = None
    last_pc_time: float | None = None
    timestamp_deltas_us: list[int] = field(default_factory=list)

    def update(self, frame: SampleFrame, pc_time: float | None = None) -> None:
        now = time.time() if pc_time is None else pc_time
        if self.frames == 0:
            self.first_seq = frame.seq
            self.first_ts_us = frame.ts_us
            self.first_pc_time = now
        else:
            if self.last_seq is not None and frame.seq > self.last_seq + 1:
                self.dropped_frames += frame.seq - self.last_seq - 1
            if self.last_ts_us is not None and frame.ts_us >= self.last_ts_us:
                self.timestamp_deltas_us.append(frame.ts_us - self.last_ts_us)

        self.frames += 1
        self.last_seq = frame.seq
        self.last_ts_us = frame.ts_us
        self.last_pc_time = now
        for bit, name in STATUS_BITS.items():
            if frame.status & (1 << bit):
                self.status_counts[name] += 1

    @property
    def duration_s(self) -> float:
        if self.first_pc_time is None or self.last_pc_time is None:
            return 0.0
        return max(0.0, self.last_pc_time - self.first_pc_time)

    @property
    def pc_frame_rate_hz(self) -> float:
        if self.duration_s <= 0:
            return 0.0
        return self.frames / self.duration_s

    @property
    def mcu_frame_rate_hz(self) -> float:
        if self.first_ts_us is None or self.last_ts_us is None or self.frames < 2:
            return 0.0
        elapsed_s = (self.last_ts_us - self.first_ts_us) / 1_000_000.0
        return (self.frames - 1) / elapsed_s if elapsed_s > 0 else 0.0

    @property
    def p95_jitter_ms(self) -> float:
        if not self.timestamp_deltas_us:
            return 0.0
        expected_us = 1_000_000.0 / self.expected_sample_rate_hz
        jitters = sorted(
            abs(delta - expected_us) / 1000.0 for delta in self.timestamp_deltas_us
        )
        index = min(len(jitters) - 1, int(round(0.95 * (len(jitters) - 1))))
        return jitters[index]

    def to_dict(self, parser: ParserStats | None = None) -> dict:
        total_expected = self.frames + self.dropped_frames
        valid_ratio = self.frames / total_expected if total_expected else 0.0
        data = {
            "frames": self.frames,
            "dropped_frames": self.dropped_frames,
            "valid_frame_ratio": valid_ratio,
            "duration_s": self.duration_s,
            "pc_frame_rate_hz": self.pc_frame_rate_hz,
            "mcu_frame_rate_hz": self.mcu_frame_rate_hz,
            "p95_jitter_ms": self.p95_jitter_ms,
            "first_seq": self.first_seq,
            "last_seq": self.last_seq,
            "first_ts_us": self.first_ts_us,
            "last_ts_us": self.last_ts_us,
            "status_counts": self.status_counts,
        }
        if parser is not None:
            data["parser"] = parser.__dict__.copy()
        return data


def build_sample_payload(values: Iterable[int]) -> bytes:
    values_tuple = tuple(values)
    if len(values_tuple) != SAMPLE_VALUE_COUNT:
        raise ValueError(f"sample payload needs {SAMPLE_VALUE_COUNT} int16 values")
    return struct.pack(SAMPLE_PAYLOAD_FORMAT, *values_tuple)


def encode_frame(
    frame_type: int,
    seq: int,
    ts_us: int,
    status: int,
    payload: bytes,
    version: int = VERSION,
) -> bytes:
    header = struct.pack(
        HEADER_FORMAT, MAGIC, version, frame_type, len(payload), seq, ts_us, status
    )
    packet_without_crc = header + payload
    return packet_without_crc + struct.pack("<H", crc16_ccitt(packet_without_crc))


def encode_sample_frame(
    seq: int, ts_us: int, status: int, values: Iterable[int]
) -> bytes:
    return encode_frame(
        FRAME_TYPE_SAMPLE, seq, ts_us, status, build_sample_payload(values)
    )


def build_node_debug_payload(
    node_id: int,
    node_status: int,
    age_ms: int,
    c3_seq: int,
    c3_ts_us: int,
    s3_rx_ts_us: int,
    imu: Imu6,
    temp_centi_c: int | None = None,
) -> bytes:
    if temp_centi_c is None:
        return struct.pack(
            NODE_DEBUG_PAYLOAD_FORMAT_V1,
            node_id,
            node_status,
            age_ms,
            c3_seq,
            c3_ts_us,
            s3_rx_ts_us,
            imu.ax,
            imu.ay,
            imu.az,
            imu.gx,
            imu.gy,
            imu.gz,
        )
    return struct.pack(
        NODE_DEBUG_PAYLOAD_FORMAT,
        node_id,
        node_status,
        age_ms,
        c3_seq,
        c3_ts_us,
        s3_rx_ts_us,
        imu.ax,
        imu.ay,
        imu.az,
        imu.gx,
        imu.gy,
        imu.gz,
        temp_centi_c,
    )


def encode_node_debug_frame(
    seq: int,
    ts_us: int,
    status: int,
    node_id: int,
    node_status: int,
    age_ms: int,
    c3_seq: int,
    c3_ts_us: int,
    s3_rx_ts_us: int,
    imu: Imu6,
    temp_centi_c: int | None = None,
) -> bytes:
    return encode_frame(
        FRAME_TYPE_NODE_DEBUG,
        seq,
        ts_us,
        status,
        build_node_debug_payload(
            node_id,
            node_status,
            age_ms,
            c3_seq,
            c3_ts_us,
            s3_rx_ts_us,
            imu,
            temp_centi_c,
        ),
    )


def scale_sensor(
    sensor_name: str, values: Imu6 | Imu9, gyro_bias: dict | None = None
) -> dict:
    """Return engineering units for display while preserving raw data elsewhere."""

    if sensor_name == "pelvis":
        accel_scale = BMX_ACCEL_LSB_PER_G
        gyro_scale = BMX_GYRO_LSB_PER_DPS
    else:
        accel_scale = BMI_ACCEL_LSB_PER_G
        gyro_scale = BMI_GYRO_LSB_PER_DPS

    bias = (gyro_bias or {}).get(sensor_name, {})
    gx = values.gx - float(bias.get("gx", 0.0))
    gy = values.gy - float(bias.get("gy", 0.0))
    gz = values.gz - float(bias.get("gz", 0.0))

    result = {
        "ax_g": values.ax / accel_scale,
        "ay_g": values.ay / accel_scale,
        "az_g": values.az / accel_scale,
        "gx_dps": gx / gyro_scale,
        "gy_dps": gy / gyro_scale,
        "gz_dps": gz / gyro_scale,
    }
    if isinstance(values, Imu9):
        result.update({"mx_raw": values.mx, "my_raw": values.my, "mz_raw": values.mz})
    return result
