# Hardware V1.1 ESP32-C3 Node Firmware

Single BMI160 satellite node for Hardware V1.1.

Defaults:

- Target: `esp32c3`
- I2C: `SDA=GPIO4`, `SCL=GPIO5`, `400kHz`
- Sample rate: `100Hz`
- Node ID: `1` (`left_foot`)
- ESP-NOW channel: `1`

Build and flash:

```powershell
idf.py set-target esp32c3
idf.py build
idf.py -p COM_C3 flash
```

BMI160 wiring:

```text
VIN/3.3V -> C3 3.3V
GND      -> C3 GND
SDA      -> C3 GPIO4
SCL      -> C3 GPIO5
CS       -> C3 3.3V
SAO      -> C3 GND
```
