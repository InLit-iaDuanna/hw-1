# Hardware V1 ESP32-S3 Firmware

ESP-IDF firmware for the wired Hardware V1 gait detection prototype.

## Build

```powershell
cd hardware_v1_detection\firmware_esp32s3
idf.py set-target esp32s3
idf.py menuconfig
idf.py build
idf.py -p COMx flash
```

## Defaults

- I2C SDA: GPIO8
- I2C SCL: GPIO9
- I2C clock: 400 kHz
- Serial baud: 921600
- Sample rate: 200 Hz
- Mux: TCA9548A at `0x70`

Change board-specific pins in `idf.py menuconfig` under `Hardware V1 gait detection`.

