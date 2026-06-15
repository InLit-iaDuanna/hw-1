# Hardware V1 Acceptance Test

## Short Stability Test

Run:

```powershell
.\.venv-mujoco\Scripts\python.exe -m hardware_v1_detection.pc_receiver.serial_capture --port COM5 --duration 60 --output hardware_v1_sessions
```

Pass criteria:

- `session_summary.json` shows `mcu_frame_rate_hz` between 198 and 202 Hz.
- `parser.crc_errors` is 0.
- `valid_frame_ratio` is at least 0.995.
- All seven sensor status counts remain 0 after initialization.

## Long Stability Test

Run for 10 minutes:

```powershell
.\.venv-mujoco\Scripts\python.exe -m hardware_v1_detection.pc_receiver.serial_capture --port COM5 --duration 600 --output hardware_v1_sessions
```

Pass criteria:

- `valid_frame_ratio >= 0.995`
- `p95_jitter_ms <= 1.0`
- No PC receiver crash.
- CSV and NPZ files are readable.

## Disconnect Tolerance

During a capture, unplug one IMU channel after confirming the system is running.

Expected:

- Capture continues.
- Only the corresponding status bit count increases.
- Other channels continue to update.
- The PyQt UI stays responsive.
