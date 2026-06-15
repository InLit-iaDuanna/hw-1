#pragma once

#include <stddef.h>
#include <stdint.h>

#include "driver/i2c.h"
#include "esp_err.h"

#define HWV1_I2C_PORT ((i2c_port_t)CONFIG_HWV1_I2C_PORT)

esp_err_t hwv1_i2c_init(void);
esp_err_t hwv1_i2c_write(uint8_t addr, const uint8_t *data, size_t len);
esp_err_t hwv1_i2c_write_reg(uint8_t addr, uint8_t reg, uint8_t value);
esp_err_t hwv1_i2c_read_reg(uint8_t addr, uint8_t reg, uint8_t *data, size_t len);

