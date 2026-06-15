# Hardware V1 Wiring

## I2C Bus

Default ESP32-S3 pins:

| Signal | GPIO |
|---|---:|
| SDA | 8 |
| SCL | 9 |
| 3V3 | 3.3V |
| GND | GND |

Use short twisted SDA/GND and SCL/GND runs where possible. Keep foot IMU wiring short and strain-relieved.

## TCA9548A Channel Map

| Mux channel | Sensor | Role | Expected address |
|---:|---|---|---|
| CH0 | BMI160 | left foot | `0x68` |
| CH1 | BMI160 | right foot | `0x68` |
| CH2 | BMI160 | left shank | `0x68` |
| CH3 | BMI160 | right shank | `0x68` |
| CH4 | BMI160 | left thigh | `0x68` |
| CH5 | BMI160 | right thigh | `0x68` |
| CH6 | BMX055 | pelvis | gyro `0x68`, accel `0x18/0x19`, mag `0x10/0x13` |

CH6 must be isolated because BMX055 gyro and BMI160 can both use `0x68`.

## Bring-Up Order

1. Connect ESP32-S3 + TCA9548A only and confirm firmware boots.
2. Add one BMI160 on CH0 and confirm static accel norm is near 1g.
3. Add CH1-CH3 one at a time.
4. Add CH4-CH5 thigh BMI160 sensors.
5. Add BMX055 on CH6 last.
5. Run a 60 second PC capture before mounting sensors on straps.
