#pragma once

#include "esp_err.h"
#include "hwv11_node_types.h"

#define BMI160_I2C_ADDR 0x68
#define BMI160_CHIP_ID_EXPECTED 0xD1

esp_err_t bmi160_init(void);
esp_err_t bmi160_read_raw(hwv11_imu6_raw_t *out);
