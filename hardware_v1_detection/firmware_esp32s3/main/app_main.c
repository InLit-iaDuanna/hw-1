#include <stdbool.h>
#include <string.h>

#include "bmi160.h"
#include "bmx055.h"
#include "driver/usb_serial_jtag.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "esp_now.h"
#include "esp_wifi.h"
#include "esp_rom_sys.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "hwv1_types.h"
#include "i2c_bus.h"
#include "nvs_flash.h"
#include "packet.h"
#include "tca9548a.h"

#if CONFIG_HWV11_HUB_ENABLE_LOCAL_I2C
static const char *TAG = "hwv1";
static const uint8_t BMI_CHANNELS[HWV1_BMI_SENSOR_COUNT] = {0, 1, 2, 3, 4, 5};
static const uint8_t BMX_CHANNEL = 6;
#endif
static const uint8_t HWV11_NODE_ID_LEFT_FOOT = 1;
static const int64_t HWV11_NODE_STALE_US = 100000;
static const uint16_t HWV11_NODE_PACKET_MAGIC = 0xC301;
static const uint8_t HWV11_NODE_PACKET_VERSION = 1;
static const uint8_t HWV11_C3_NODE_MAC[ESP_NOW_ETH_ALEN] = {
    0x14, 0x63, 0x93, 0x93, 0xd8, 0x64,
};

static hwv1_imu6_raw_t s_last_bmi[HWV1_BMI_SENSOR_COUNT];
static hwv1_imu9_raw_t s_last_bmx;
static uint16_t s_init_status = HWV1_STATUS_INIT_INCOMPLETE;
static portMUX_TYPE s_node_lock = portMUX_INITIALIZER_UNLOCKED;
static hwv1_imu6_raw_t s_left_foot_node_imu;
static uint32_t s_left_foot_node_seq = 0;
static uint64_t s_left_foot_node_ts_us = 0;
static uint64_t s_left_foot_node_rx_us = 0;
static int16_t s_left_foot_node_temp_centi_c = INT16_MIN;
static uint8_t s_left_foot_node_status = 1;
static bool s_left_foot_node_seen = false;

typedef struct __attribute__((packed)) {
    uint16_t magic;
    uint8_t version;
    uint8_t node_id;
    uint8_t status;
    uint32_t seq;
    uint64_t ts_us;
    hwv1_imu6_raw_t imu;
    int16_t temp_centi_c;
} hwv11_node_packet_t;

static void serial_init(void)
{
    usb_serial_jtag_driver_config_t config = USB_SERIAL_JTAG_DRIVER_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(usb_serial_jtag_driver_install(&config));
}

static void nvs_init_for_wifi(void)
{
    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        err = nvs_flash_init();
    }
    ESP_ERROR_CHECK(err);
}

static void espnow_recv_cb(const esp_now_recv_info_t *info, const uint8_t *data, int len)
{
    (void)info;
    if (len != sizeof(hwv11_node_packet_t)) {
        return;
    }

    hwv11_node_packet_t packet;
    memcpy(&packet, data, sizeof(packet));
    if (packet.magic != HWV11_NODE_PACKET_MAGIC ||
        packet.version != HWV11_NODE_PACKET_VERSION ||
        packet.node_id != HWV11_NODE_ID_LEFT_FOOT) {
        return;
    }

    portENTER_CRITICAL(&s_node_lock);
    s_left_foot_node_imu = packet.imu;
    s_left_foot_node_seq = packet.seq;
    s_left_foot_node_ts_us = packet.ts_us;
    s_left_foot_node_rx_us = (uint64_t)esp_timer_get_time();
    s_left_foot_node_temp_centi_c = packet.temp_centi_c;
    s_left_foot_node_status = packet.status;
    s_left_foot_node_seen = true;
    portEXIT_CRITICAL(&s_node_lock);
}

static void espnow_init_hub(void)
{
    nvs_init_for_wifi();
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));
    ESP_ERROR_CHECK(esp_wifi_set_storage(WIFI_STORAGE_RAM));
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_start());
    ESP_ERROR_CHECK(esp_wifi_set_channel(1, WIFI_SECOND_CHAN_NONE));
    ESP_ERROR_CHECK(esp_now_init());
    ESP_ERROR_CHECK(esp_now_register_recv_cb(espnow_recv_cb));

    esp_now_peer_info_t peer = {0};
    memcpy(peer.peer_addr, HWV11_C3_NODE_MAC, ESP_NOW_ETH_ALEN);
    peer.channel = 1;
    peer.ifidx = WIFI_IF_STA;
    peer.encrypt = false;
    esp_err_t err = esp_now_add_peer(&peer);
    if (err != ESP_OK && err != ESP_ERR_ESPNOW_EXIST) {
        ESP_ERROR_CHECK(err);
    }
}

#if CONFIG_HWV11_HUB_ENABLE_LOCAL_I2C
static uint16_t status_bit_for_bmi(size_t index)
{
    return (uint16_t)(1u << index);
}
#endif

static void init_sensors(void)
{
#if CONFIG_HWV11_HUB_ENABLE_LOCAL_I2C
    uint16_t status = 0;

    for (size_t i = 0; i < HWV1_BMI_SENSOR_COUNT; ++i) {
        esp_err_t err = tca9548a_select(BMI_CHANNELS[i]);
        if (err == ESP_OK) {
            err = bmi160_init();
        }
        if (err != ESP_OK) {
            status |= status_bit_for_bmi(i);
            ESP_LOGW(TAG, "BMI160 ch%u init failed: %s", BMI_CHANNELS[i], esp_err_to_name(err));
        }
    }

    esp_err_t err = tca9548a_select(BMX_CHANNEL);
    if (err == ESP_OK) {
        err = bmx055_init();
    }
    if (err != ESP_OK) {
        status |= HWV1_STATUS_PELVIS_FAIL;
        ESP_LOGW(TAG, "BMX055 ch%u init failed: %s", BMX_CHANNEL, esp_err_to_name(err));
    }
    s_init_status = status;
#else
    s_init_status = HWV1_STATUS_LEFT_FOOT_FAIL |
                    HWV1_STATUS_RIGHT_FOOT_FAIL |
                    HWV1_STATUS_LEFT_SHANK_FAIL |
                    HWV1_STATUS_RIGHT_SHANK_FAIL |
                    HWV1_STATUS_LEFT_THIGH_FAIL |
                    HWV1_STATUS_RIGHT_THIGH_FAIL |
                    HWV1_STATUS_PELVIS_FAIL;
#endif
}

static uint16_t read_all_sensors(hwv1_sample_t *sample)
{
    uint16_t status = s_init_status;

#if CONFIG_HWV11_HUB_ENABLE_LOCAL_I2C
    for (size_t i = 0; i < HWV1_BMI_SENSOR_COUNT; ++i) {
        esp_err_t err = tca9548a_select(BMI_CHANNELS[i]);
        if (err == ESP_OK) {
            err = bmi160_read_raw(&sample->bmi[i]);
        }
        if (err == ESP_OK) {
            s_last_bmi[i] = sample->bmi[i];
        } else {
            sample->bmi[i] = s_last_bmi[i];
            status |= status_bit_for_bmi(i);
        }
    }

    esp_err_t err = tca9548a_select(BMX_CHANNEL);
    if (err == ESP_OK) {
        err = bmx055_read_raw(&sample->bmx);
    }
    if (err == ESP_OK) {
        s_last_bmx = sample->bmx;
    } else {
        sample->bmx = s_last_bmx;
        status |= HWV1_STATUS_PELVIS_FAIL;
    }
#else
    for (size_t i = 0; i < HWV1_BMI_SENSOR_COUNT; ++i) {
        sample->bmi[i] = s_last_bmi[i];
    }
    sample->bmx = s_last_bmx;
#endif

    const int64_t now_us = esp_timer_get_time();
    portENTER_CRITICAL(&s_node_lock);
    const bool node_seen = s_left_foot_node_seen;
    const uint64_t node_rx_us = s_left_foot_node_rx_us;
    const hwv1_imu6_raw_t node_imu = s_left_foot_node_imu;
    const uint8_t node_status = s_left_foot_node_status;
    portEXIT_CRITICAL(&s_node_lock);

    if (node_seen && now_us >= (int64_t)node_rx_us &&
        now_us - (int64_t)node_rx_us <= HWV11_NODE_STALE_US &&
        node_status == 0) {
        sample->bmi[0] = node_imu;
        s_last_bmi[0] = node_imu;
        status &= (uint16_t)~HWV1_STATUS_LEFT_FOOT_FAIL;
    }

    return status;
}

static size_t encode_latest_node_debug(uint32_t *last_emitted_c3_seq,
                                       uint8_t *payload, size_t payload_cap)
{
    hwv1_imu6_raw_t imu;
    uint32_t seq;
    uint64_t c3_ts_us;
    uint64_t rx_us;
    int16_t temp_centi_c;
    uint8_t node_status;
    bool seen;

    portENTER_CRITICAL(&s_node_lock);
    imu = s_left_foot_node_imu;
    seq = s_left_foot_node_seq;
    c3_ts_us = s_left_foot_node_ts_us;
    rx_us = s_left_foot_node_rx_us;
    temp_centi_c = s_left_foot_node_temp_centi_c;
    node_status = s_left_foot_node_status;
    seen = s_left_foot_node_seen;
    portEXIT_CRITICAL(&s_node_lock);

    if (!seen) {
        return 0;
    }
    if (seq == *last_emitted_c3_seq) {
        return 0;
    }

    const uint64_t now_us = (uint64_t)esp_timer_get_time();
    uint64_t age_ms64 = 0;
    if (now_us >= rx_us) {
        age_ms64 = (now_us - rx_us) / 1000u;
    }
    if (age_ms64 > UINT16_MAX) {
        age_ms64 = UINT16_MAX;
    }

    const size_t payload_len = hwv1_encode_node_debug_payload(
        HWV11_NODE_ID_LEFT_FOOT, node_status, (uint16_t)age_ms64,
        seq, c3_ts_us, rx_us, &imu, temp_centi_c, payload, payload_cap);
    if (payload_len > 0) {
        *last_emitted_c3_seq = seq;
    }
    return payload_len;
}

static void wait_until_us(int64_t target_us)
{
    while (true) {
        const int64_t now = esp_timer_get_time();
        const int64_t remaining = target_us - now;
        if (remaining <= 0) {
            return;
        }
        if (remaining > 1000) {
            vTaskDelay(pdMS_TO_TICKS((uint32_t)(remaining / 1000)));
        } else {
            esp_rom_delay_us((uint32_t)remaining);
        }
    }
}

void app_main(void)
{
    memset(s_last_bmi, 0, sizeof(s_last_bmi));
    memset(&s_last_bmx, 0, sizeof(s_last_bmx));

    serial_init();
    espnow_init_hub();
#if CONFIG_HWV11_HUB_ENABLE_LOCAL_I2C
    ESP_ERROR_CHECK(hwv1_i2c_init());
#endif
    init_sensors();

    esp_log_level_set("*", ESP_LOG_ERROR);

    uint8_t payload[HWV1_SAMPLE_PAYLOAD_SIZE];
    uint8_t frame[HWV1_PACKET_MAX_SIZE];
    uint32_t seq = 0;
    uint32_t node_debug_seq = 0;
    uint32_t last_debug_c3_seq = UINT32_MAX;
    const int64_t period_us = 1000000LL / CONFIG_HWV1_SAMPLE_RATE_HZ;
    int64_t next_us = esp_timer_get_time();

    while (true) {
        hwv1_sample_t sample;
        memset(&sample, 0, sizeof(sample));
        const uint16_t status = read_all_sensors(&sample);
        const uint64_t ts_us = (uint64_t)esp_timer_get_time();

        const size_t payload_len = hwv1_encode_sample_payload(&sample, payload, sizeof(payload));
        const size_t frame_len = hwv1_packet_encode(
            HWV1_PACKET_TYPE_SAMPLE, seq++, ts_us, status,
            payload, (uint16_t)payload_len, frame, sizeof(frame));
        if (frame_len > 0) {
            usb_serial_jtag_write_bytes(frame, frame_len, pdMS_TO_TICKS(20));
        }

        const size_t node_payload_len = encode_latest_node_debug(
            &last_debug_c3_seq, payload, sizeof(payload));
        if (node_payload_len > 0) {
            const size_t node_frame_len = hwv1_packet_encode(
                HWV1_PACKET_TYPE_NODE_DEBUG, node_debug_seq++, ts_us, status,
                payload, (uint16_t)node_payload_len, frame, sizeof(frame));
            if (node_frame_len > 0) {
                usb_serial_jtag_write_bytes(frame, node_frame_len, pdMS_TO_TICKS(20));
            }
        }

        next_us += period_us;
        const int64_t after_send_us = esp_timer_get_time();
        if (next_us < after_send_us) {
            next_us = after_send_us + period_us;
        }
        wait_until_us(next_us);
    }
}
