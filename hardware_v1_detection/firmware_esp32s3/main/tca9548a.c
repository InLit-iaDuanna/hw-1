#include "tca9548a.h"

#include "i2c_bus.h"

esp_err_t tca9548a_select(uint8_t channel)
{
    if (channel > 7) {
        return ESP_ERR_INVALID_ARG;
    }
    uint8_t mask = (uint8_t)(1u << channel);
    return hwv1_i2c_write(HWV1_TCA9548A_ADDR, &mask, 1);
}

esp_err_t tca9548a_disable_all(void)
{
    uint8_t mask = 0;
    return hwv1_i2c_write(HWV1_TCA9548A_ADDR, &mask, 1);
}

