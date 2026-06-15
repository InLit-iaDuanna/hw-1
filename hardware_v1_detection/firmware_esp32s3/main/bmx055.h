#pragma once

#include "esp_err.h"
#include "hwv1_types.h"

#define BMX055_GYRO_ADDR 0x68

esp_err_t bmx055_init(void);
esp_err_t bmx055_read_raw(hwv1_imu9_raw_t *out);

