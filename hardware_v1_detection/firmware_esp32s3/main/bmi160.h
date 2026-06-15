#pragma once

#include "esp_err.h"
#include "hwv1_types.h"

#define BMI160_I2C_ADDR 0x68
#define BMI160_CHIP_ID_EXPECTED 0xD1

esp_err_t bmi160_init(void);
esp_err_t bmi160_read_raw(hwv1_imu6_raw_t *out);

