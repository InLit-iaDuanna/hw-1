# Hardware V1 Quickstart

For the ESP32-C3 wireless node test, see
[V1_1_ESPNOW_C3_TEST.md](V1_1_ESPNOW_C3_TEST.md).

## 1. Build Firmware

```powershell
cd D:\Dunna\Documents\hw-1\hardware_v1_detection\firmware_esp32s3
idf.py set-target esp32s3
idf.py menuconfig
idf.py build
idf.py -p COM5 flash
```

If your board uses different I2C pins, change them in `Hardware V1 gait detection`.

## 2. Capture Raw Data

```powershell
cd D:\Dunna\Documents\hw-1
.\.venv-mujoco\Scripts\python.exe -m hardware_v1_detection.pc_receiver.serial_capture --port COM5 --duration 60 --output hardware_v1_sessions
```

Outputs:

- `raw.csv`: raw int16 rows, one row per sensor per frame
- `scaled.csv`: engineering units for plotting
- `raw.npz`: compact numeric archive
- `session_summary.json`: frame rate, dropped frames, CRC errors, status counts

Current output is still sensor-level engineering data, not joint angles or
clinical gait metrics. See [DATA_BOUNDARY.md](DATA_BOUNDARY.md).

## 3. Static Gyro Calibration

Keep all sensors still:

```powershell
.\.venv-mujoco\Scripts\python.exe hardware_v1_detection\calibration\calibrate_static.py --port COM5 --duration 10 --output hardware_v1_detection\calibration\gyro_bias.json
```

Use it during capture:

```powershell
.\.venv-mujoco\Scripts\python.exe -m hardware_v1_detection.pc_receiver.serial_capture --port COM5 --calibration hardware_v1_detection\calibration\gyro_bias.json
```

## 4. Demo UI

```powershell
.\.venv-mujoco\Scripts\python.exe hardware_v1_detection\demo_app\app.py
```

Install GUI dependencies if needed:

```powershell
.\.venv-mujoco\Scripts\python.exe -m pip install pyserial PyQt5 pyqtgraph
```
