import numpy as np

from hardware_v1_detection.pc_receiver.protocol import (
    BMI_SENSOR_NAMES,
    CaptureStats,
    FrameParser,
    Imu6,
    NODE_DEBUG_PAYLOAD_SIZE,
    SAMPLE_PAYLOAD_SIZE,
    SAMPLE_VALUE_COUNT,
    SENSOR_NAMES,
    crc16_ccitt,
    encode_node_debug_frame,
    encode_sample_frame,
)
from hardware_v1_detection.pc_receiver.session import SessionWriter


def test_sample_frame_round_trip():
    values = list(range(-16, -16 + SAMPLE_VALUE_COUNT))
    packet = encode_sample_frame(seq=7, ts_us=123456, status=0x0012, values=values)

    parser = FrameParser()
    frames = parser.feed(packet)

    assert len(frames) == 1
    frame = frames[0]
    assert SAMPLE_VALUE_COUNT == 45
    assert SAMPLE_PAYLOAD_SIZE == 90
    assert len(BMI_SENSOR_NAMES) == 6
    assert len(SENSOR_NAMES) == 7
    assert len(frame.bmi) == 6
    assert frame.seq == 7
    assert frame.ts_us == 123456
    assert frame.status == 0x0012
    assert frame.raw_values() == tuple(values)
    assert parser.stats.frames_ok == 1
    assert crc16_ccitt(packet[:-2]) == int.from_bytes(packet[-2:], "little")


def test_parser_resyncs_after_junk_and_bad_crc():
    values = [100] * SAMPLE_VALUE_COUNT
    good = encode_sample_frame(seq=1, ts_us=5000, status=0, values=values)
    bad = bytearray(good)
    bad[-1] ^= 0xFF

    parser = FrameParser()
    frames = parser.feed(b"junk" + bad + good)

    assert len(frames) == 1
    assert frames[0].seq == 1
    assert parser.stats.crc_errors >= 1
    assert parser.stats.resync_bytes >= 4 + len(bad)


def test_parser_skips_corrupt_candidate_frame_in_one_step():
    values = [42] * SAMPLE_VALUE_COUNT
    good = encode_sample_frame(seq=2, ts_us=10000, status=0, values=values)
    bad = bytearray(encode_sample_frame(seq=1, ts_us=5000, status=0, values=values))
    bad[-1] ^= 0xFF

    parser = FrameParser()
    frames = parser.feed(bytes(bad) + good)

    assert [frame.seq for frame in frames] == [2]
    assert parser.stats.crc_errors == 1
    assert parser.stats.resync_bytes == len(bad)


def test_capture_stats_detects_dropped_seq_and_jitter():
    parser = FrameParser()
    stats = CaptureStats()
    values = [0] * SAMPLE_VALUE_COUNT
    packets = encode_sample_frame(
        seq=10, ts_us=0, status=0, values=values
    ) + encode_sample_frame(seq=12, ts_us=5000, status=1, values=values)

    frames = parser.feed(packets)
    for idx, frame in enumerate(frames):
        stats.update(frame, pc_time=float(idx))

    assert stats.frames == 2
    assert stats.dropped_frames == 1
    assert stats.status_counts["left_foot_fail"] == 1
    assert stats.mcu_frame_rate_hz == 200.0
    assert stats.p95_jitter_ms == 0.0


def test_status_bits_include_thighs_and_pelvis():
    parser = FrameParser()
    values = [0] * SAMPLE_VALUE_COUNT
    status = (1 << 4) | (1 << 5) | (1 << 6)
    frame = parser.feed(
        encode_sample_frame(seq=1, ts_us=0, status=status, values=values)
    )[0]

    assert frame.status_names() == [
        "left_thigh_fail",
        "right_thigh_fail",
        "pelvis_fail",
    ]


def test_node_debug_frame_round_trip():
    imu = Imu6(ax=1, ay=2, az=3, gx=4, gy=5, gz=6)
    packet = encode_node_debug_frame(
        seq=99,
        ts_us=123000,
        status=0,
        node_id=1,
        node_status=0,
        age_ms=7,
        c3_seq=42,
        c3_ts_us=100000,
        s3_rx_ts_us=120000,
        imu=imu,
    )

    parser = FrameParser()
    frames = parser.feed(packet)

    assert NODE_DEBUG_PAYLOAD_SIZE == 36
    assert len(frames) == 1
    frame = frames[0]
    assert frame.node_id == 1
    assert frame.node_status == 0
    assert frame.age_ms == 7
    assert frame.c3_seq == 42
    assert frame.imu == imu
    assert parser.stats.node_debug_frames == 1


def test_session_writer_creates_expected_artifacts(tmp_path):
    values = [0] * SAMPLE_VALUE_COUNT
    frame = FrameParser().feed(
        encode_sample_frame(seq=1, ts_us=5000, status=0, values=values)
    )[0]
    parser = FrameParser()

    writer = SessionWriter(output_dir=tmp_path)
    writer.append_frame(frame)
    session_dir = writer.close(parser)

    assert (session_dir / "raw.csv").exists()
    assert (session_dir / "scaled.csv").exists()
    assert (session_dir / "node_raw.csv").exists()
    assert (session_dir / "raw.npz").exists()
    assert (session_dir / "session_summary.json").exists()

    data = np.load(session_dir / "raw.npz")
    assert data["values"].shape == (1, 45)
    assert data["sensor_names"].tolist() == list(SENSOR_NAMES)


def test_session_writer_records_node_debug_summary(tmp_path):
    node_frame = FrameParser().feed(
        encode_node_debug_frame(
            seq=2,
            ts_us=10000,
            status=0,
            node_id=1,
            node_status=0,
            age_ms=9,
            c3_seq=4,
            c3_ts_us=9000,
            s3_rx_ts_us=9500,
            imu=Imu6(1, 2, 3, 4, 5, 6),
        )
    )[0]
    parser = FrameParser()

    writer = SessionWriter(output_dir=tmp_path)
    writer.append_node_frame(node_frame)
    session_dir = writer.close(parser)

    assert (session_dir / "node_raw.csv").read_text(encoding="utf-8").count("\n") == 2
    summary = (session_dir / "session_summary.json").read_text(encoding="utf-8")
    assert '"espnow_packets": 1' in summary
    assert '"node_drops": 0' in summary
    assert '"node_age_ms_p95": 9.0' in summary
