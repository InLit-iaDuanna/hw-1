# Hardware V1.1 ESP-NOW C3 IMU Test

V1.1 validates one remote ESP32-C3 node reading one BMI160 and sending raw IMU
samples to the waist ESP32-S3 hub over ESP-NOW. The S3 remains the only PC
connection over USB serial.

## Topology

```text
BMI160 -> ESP32-C3 node -> ESP-NOW channel 1 -> ESP32-S3 hub -> USB -> PC
```

The first C3 node maps to `left_foot` / aggregate sample slot `CH0`.

## C3 BMI160 Wiring

```text
BMI160 VIN or 3.3V -> C3 3.3V
BMI160 GND         -> C3 GND
BMI160 SDA         -> C3 GPIO4
BMI160 SCL         -> C3 GPIO5
BMI160 CS          -> C3 3.3V
BMI160 SAO         -> C3 GND
BMI160 INT1/INT2   -> not connected
```

`CS` must be high for I2C mode. `SAO` is tied low so the BMI160 address is
`0x68`.

## Build And Flash

Flash the C3 node first:

```powershell
cd D:\Dunna\Documents\hw-1\hardware_v1_detection\firmware_esp32c3_node
idf.py set-target esp32c3
idf.py build
idf.py -p COM_C3 flash
```

Flash the S3 hub:

```powershell
cd D:\Dunna\Documents\hw-1\hardware_v1_detection\firmware_esp32s3
idf.py set-target esp32s3
idf.py build
idf.py -p COM_S3 flash
```

Both devices use ESP-NOW channel `1`. The S3 still streams PC frames at
`921600` baud.

## PC Capture

```powershell
cd D:\Dunna\Documents\hw-1
.\.venv-mujoco\Scripts\python.exe -m hardware_v1_detection.pc_receiver.serial_capture --port COM_S3 --duration 60 --output hardware_v1_sessions
```

Expected V1.1 outputs:

- `raw.csv`, `scaled.csv`, `raw.npz`: existing aggregate `45×int16` stream.
- `node_raw.csv`: C3 node debug stream.
- `session_summary.json`: includes `espnow_packets`, `node_drops`, and
  `node_age_ms_p95`.

For a healthy single-node test, `left_foot_fail` should be `0`,
`espnow_packets` should be greater than `0`, and `node_age_ms_p95` should be
under `50ms`.
