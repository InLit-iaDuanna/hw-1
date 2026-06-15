#include "bmi160.h"

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "i2c_bus.h"

#define BMI160_REG_CHIP_ID 0x00
#define BMI160_REG_DATA_GYR_X_LSB 0x0C
#define BMI160_REG_ACC_CONF 0x40
#define BMI160_REG_ACC_RANGE 0x41
#define BMI160_REG_GYR_CONF 0x42
#define BMI160_REG_GYR_RANGE 0x43
#define BMI160_REG_CMD 0x7E

#define BMI160_CMD_ACC_NORMAL 0x11
#define BMI160_CMD_GYR_NORMAL 0x15

static int16_t le_i16(const uint8_t *p)
{
    return (int16_t)((uint16_t)p[0] | ((uint16_t)p[1] << 8));
}

esp_err_t bmi160_init(void)
{
    uint8_t chip_id = 0;
    esp_err_t err = hwv1_i2c_read_reg(BMI160_I2C_ADDR, BMI160_REG_CHIP_ID, &chip_id, 1);
    if (err != ESP_OK) {
        return err;
    }
    if (chip_id != BMI160_CHIP_ID_EXPECTED) {
        return ESP_ERR_INVALID_RESPONSE;
    }

    err = hwv1_i2c_write_reg(BMI160_I2C_ADDR, BMI160_REG_CMD, BMI160_CMD_ACC_NORMAL);
    if (err != ESP_OK) {
        return err;
    }
    vTaskDelay(pdMS_TO_TICKS(10));

    err = hwv1_i2c_write_reg(BMI160_I2C_ADDR, BMI160_REG_CMD, BMI160_CMD_GYR_NORMAL);
    if (err != ESP_OK) {
        return err;
    }
    vTaskDelay(pdMS_TO_TICKS(80));

    /* 200 Hz ODR, normal bandwidth; accel +/-8g, gyro +/-1000 dps. */
    err = hwv1_i2c_write_reg(BMI160_I2C_ADDR, BMI160_REG_ACC_CONF, 0x29);
    if (err != ESP_OK) {
        return err;
    }
    err = hwv1_i2c_write_reg(BMI160_I2C_ADDR, BMI160_REG_ACC_RANGE, 0x08);
    if (err != ESP_OK) {
        return err;
    }
    err = hwv1_i2c_write_reg(BMI160_I2C_ADDR, BMI160_REG_GYR_CONF, 0x29);
    if (err != ESP_OK) {
        return err;
    }
    return hwv1_i2c_write_reg(BMI160_I2C_ADDR, BMI160_REG_GYR_RANGE, 0x01);
}

esp_err_t bmi160_read_raw(hwv1_imu6_raw_t *out)
{
    uint8_t data[12] = {0};
    esp_err_t err = hwv1_i2c_read_reg(
        BMI160_I2C_ADDR, BMI160_REG_DATA_GYR_X_LSB, data, sizeof(data));
    if (err != ESP_OK) {
        return err;
    }

    out->gx = le_i16(&data[0]);
    out->gy = le_i16(&data[2]);
    out->gz = le_i16(&data[4]);
    out->ax = le_i16(&data[6]);
    out->ay = le_i16(&data[8]);
    out->az = le_i16(&data[10]);
    return ESP_OK;
}

