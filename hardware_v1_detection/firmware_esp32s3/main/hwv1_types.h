#pragma once

#include <stdint.h>

#define HWV1_BMI_SENSOR_COUNT 6
#define HWV1_SENSOR_COUNT 7
#define HWV1_SAMPLE_VALUE_COUNT (HWV1_BMI_SENSOR_COUNT * 6 + 9)
#define HWV1_SAMPLE_PAYLOAD_SIZE (HWV1_SAMPLE_VALUE_COUNT * sizeof(int16_t))

#define HWV1_STATUS_LEFT_FOOT_FAIL   (1u << 0)
#define HWV1_STATUS_RIGHT_FOOT_FAIL  (1u << 1)
#define HWV1_STATUS_LEFT_SHANK_FAIL  (1u << 2)
#define HWV1_STATUS_RIGHT_SHANK_FAIL (1u << 3)
#define HWV1_STATUS_LEFT_THIGH_FAIL  (1u << 4)
#define HWV1_STATUS_RIGHT_THIGH_FAIL (1u << 5)
#define HWV1_STATUS_PELVIS_FAIL      (1u << 6)
#define HWV1_STATUS_INIT_INCOMPLETE  (1u << 15)

typedef struct {
    int16_t ax;
    int16_t ay;
    int16_t az;
    int16_t gx;
    int16_t gy;
    int16_t gz;
} hwv1_imu6_raw_t;

typedef struct {
    int16_t ax;
    int16_t ay;
    int16_t az;
    int16_t gx;
    int16_t gy;
    int16_t gz;
    int16_t mx;
    int16_t my;
    int16_t mz;
} hwv1_imu9_raw_t;

typedef struct {
    hwv1_imu6_raw_t bmi[HWV1_BMI_SENSOR_COUNT];
    hwv1_imu9_raw_t bmx;
} hwv1_sample_t;
