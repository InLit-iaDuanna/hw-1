#include "bmx055.h"

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "i2c_bus.h"

#define BMX055_ACCEL_CHIP_ID 0xFA
#define BMX055_GYRO_CHIP_ID 0x0F
#define BMX055_MAG_CHIP_ID 0x32

#define BMA_REG_CHIP_ID 0x00
#define BMA_REG_DATA_X_LSB 0x02
#define BMA_REG_RANGE 0x0F
#define BMA_REG_BW 0x10

#define BMG_REG_CHIP_ID 0x00
#define BMG_REG_DATA_X_LSB 0x02
#define BMG_REG_RANGE 0x0F
#define BMG_REG_BW 0x10

#define BMM_REG_CHIP_ID 0x40
#define BMM_REG_DATA_X_LSB 0x42
#define BMM_REG_POWER 0x4B
#define BMM_REG_OPMODE 0x4C
#define BMM_REG_REP_XY 0x51
#define BMM_REG_REP_Z 0x52

static uint8_t s_accel_addr = 0x18;
static uint8_t s_mag_addr = 0x10;

static int16_t le_i16(const uint8_t *p)
{
    return (int16_t)((uint16_t)p[0] | ((uint16_t)p[1] << 8));
}

static int16_t sign_extend_u16(uint16_t raw, uint8_t bits)
{
    const uint16_t mask = (uint16_t)(1u << (bits - 1));
    raw = (uint16_t)(raw & ((1u << bits) - 1u));
    return (int16_t)((raw ^ mask) - mask);
}

static esp_err_t detect_addr(const uint8_t *candidates, size_t count, uint8_t reg,
                             uint8_t expected, uint8_t *selected)
{
    for (size_t i = 0; i < count; ++i) {
        uint8_t value = 0;
        esp_err_t err = hwv1_i2c_read_reg(candidates[i], reg, &value, 1);
        if (err == ESP_OK && value == expected) {
            *selected = candidates[i];
            return ESP_OK;
        }
    }
    return ESP_ERR_NOT_FOUND;
}

esp_err_t bmx055_init(void)
{
    static const uint8_t accel_candidates[] = {0x18, 0x19};
    static const uint8_t mag_candidates[] = {0x10, 0x13};
    uint8_t gyro_id = 0;

    esp_err_t err = detect_addr(
        accel_candidates, sizeof(accel_candidates), BMA_REG_CHIP_ID,
        BMX055_ACCEL_CHIP_ID, &s_accel_addr);
    if (err != ESP_OK) {
        return err;
    }
    err = hwv1_i2c_read_reg(BMX055_GYRO_ADDR, BMG_REG_CHIP_ID, &gyro_id, 1);
    if (err != ESP_OK) {
        return err;
    }
    if (gyro_id != BMX055_GYRO_CHIP_ID) {
        return ESP_ERR_INVALID_RESPONSE;
    }

    err = hwv1_i2c_write_reg(s_accel_addr, BMA_REG_RANGE, 0x08);
    if (err != ESP_OK) {
        return err;
    }
    err = hwv1_i2c_write_reg(s_accel_addr, BMA_REG_BW, 0x0C);
    if (err != ESP_OK) {
        return err;
    }
    err = hwv1_i2c_write_reg(BMX055_GYRO_ADDR, BMG_REG_RANGE, 0x01);
    if (err != ESP_OK) {
        return err;
    }
    err = hwv1_i2c_write_reg(BMX055_GYRO_ADDR, BMG_REG_BW, 0x04);
    if (err != ESP_OK) {
        return err;
    }

    (void)hwv1_i2c_write_reg(mag_candidates[0], BMM_REG_POWER, 0x01);
    vTaskDelay(pdMS_TO_TICKS(5));
    err = detect_addr(
        mag_candidates, sizeof(mag_candidates), BMM_REG_CHIP_ID,
        BMX055_MAG_CHIP_ID, &s_mag_addr);
    if (err != ESP_OK) {
        return err;
    }
    err = hwv1_i2c_write_reg(s_mag_addr, BMM_REG_OPMODE, 0x00);
    if (err != ESP_OK) {
        return err;
    }
    err = hwv1_i2c_write_reg(s_mag_addr, BMM_REG_REP_XY, 0x04);
    if (err != ESP_OK) {
        return err;
    }
    return hwv1_i2c_write_reg(s_mag_addr, BMM_REG_REP_Z, 0x0F);
}

esp_err_t bmx055_read_raw(hwv1_imu9_raw_t *out)
{
    uint8_t accel[6] = {0};
    uint8_t gyro[6] = {0};
    uint8_t mag[8] = {0};

    esp_err_t err = hwv1_i2c_read_reg(s_accel_addr, BMA_REG_DATA_X_LSB, accel, sizeof(accel));
    if (err != ESP_OK) {
        return err;
    }
    err = hwv1_i2c_read_reg(BMX055_GYRO_ADDR, BMG_REG_DATA_X_LSB, gyro, sizeof(gyro));
    if (err != ESP_OK) {
        return err;
    }
    err = hwv1_i2c_read_reg(s_mag_addr, BMM_REG_DATA_X_LSB, mag, sizeof(mag));
    if (err != ESP_OK) {
        return err;
    }

    out->ax = sign_extend_u16((uint16_t)(le_i16(&accel[0]) >> 4), 12);
    out->ay = sign_extend_u16((uint16_t)(le_i16(&accel[2]) >> 4), 12);
    out->az = sign_extend_u16((uint16_t)(le_i16(&accel[4]) >> 4), 12);
    out->gx = le_i16(&gyro[0]);
    out->gy = le_i16(&gyro[2]);
    out->gz = le_i16(&gyro[4]);
    out->mx = sign_extend_u16((uint16_t)(le_i16(&mag[0]) >> 3), 13);
    out->my = sign_extend_u16((uint16_t)(le_i16(&mag[2]) >> 3), 13);
    out->mz = sign_extend_u16((uint16_t)(le_i16(&mag[4]) >> 1), 15);
    return ESP_OK;
}

