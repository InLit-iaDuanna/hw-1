# Hardware V1 Data Boundary

Hardware V1 currently exports engineering prototype sensor data. It does not
yet export joint angles, gait events, clinical diagnoses, or rehabilitation
recommendations.

## What Is Available Now

- Raw signed 16-bit IMU counts from six BMI160 sensors and one BMX055 sensor.
- Scaled accelerometer and gyroscope columns for plotting.
- Optional static gyroscope zero-bias subtraction from `calibration/gyro_bias.json`.
- Link-quality metrics: frame rate, sequence drops, CRC errors, timestamp jitter,
  and per-channel status-bit counts.

## What Is Not Available Yet

- Per-sensor mounting-orientation calibration.
- Alignment of all IMU frames into a shared body or pelvis coordinate system.
- Roll/pitch/yaw or quaternion attitude estimates.
- Ankle, knee, hip, or pelvis joint-angle estimates.
- Heel-strike, toe-off, stance/swing timing, or left/right symmetry metrics.
- Clinical classification of foot drop, hip hiking, circumduction, or recovery
  progress.

## Required Before Clinical-Style Metrics

1. Add installation-orientation calibration for each IMU.
2. Align left/right foot and shank IMU frames to a shared pelvis BMX055 reference.
3. Add attitude estimation and drift handling.
4. Detect gait events from foot/shank IMU signals, then validate them against
   video or pressure-sensor ground truth.
5. Only after those steps, compute symmetry and foot-drop metrics.
