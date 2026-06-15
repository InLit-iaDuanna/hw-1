#pragma once

#include <stdint.h>

#include "esp_err.h"

#define HWV1_TCA9548A_ADDR 0x70

esp_err_t tca9548a_select(uint8_t channel);
esp_err_t tca9548a_disable_all(void);

