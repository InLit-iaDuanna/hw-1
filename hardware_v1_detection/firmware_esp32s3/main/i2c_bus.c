#include "i2c_bus.h"

#include "driver/gpio.h"
#include "freertos/FreeRTOS.h"

esp_err_t hwv1_i2c_init(void)
{
    i2c_config_t conf = {
        .mode = I2C_MODE_MASTER,
        .sda_io_num = CONFIG_HWV1_I2C_SDA_GPIO,
        .scl_io_num = CONFIG_HWV1_I2C_SCL_GPIO,
        .sda_pullup_en = GPIO_PULLUP_ENABLE,
        .scl_pullup_en = GPIO_PULLUP_ENABLE,
        .master.clk_speed = CONFIG_HWV1_I2C_FREQ_HZ,
        .clk_flags = 0,
    };

    esp_err_t err = i2c_param_config(HWV1_I2C_PORT, &conf);
    if (err != ESP_OK) {
        return err;
    }
    return i2c_driver_install(HWV1_I2C_PORT, conf.mode, 0, 0, 0);
}

esp_err_t hwv1_i2c_write(uint8_t addr, const uint8_t *data, size_t len)
{
    return i2c_master_write_to_device(
        HWV1_I2C_PORT, addr, data, len, pdMS_TO_TICKS(20));
}

esp_err_t hwv1_i2c_write_reg(uint8_t addr, uint8_t reg, uint8_t value)
{
    uint8_t data[2] = {reg, value};
    return hwv1_i2c_write(addr, data, sizeof(data));
}

esp_err_t hwv1_i2c_read_reg(uint8_t addr, uint8_t reg, uint8_t *data, size_t len)
{
    return i2c_master_write_read_device(
        HWV1_I2C_PORT, addr, &reg, 1, data, len, pdMS_TO_TICKS(20));
}
