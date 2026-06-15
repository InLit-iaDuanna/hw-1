#include <inttypes.h>
#include <stdbool.h>
#include <string.h>

#include "bmi160.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_now.h"
#include "esp_rom_sys.h"
#include "esp_wifi.h"
#include "esp_netif.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "hwv11_node_types.h"
#include "i2c_bus.h"
#include "nvs_flash.h"
#include "driver/temperature_sensor.h"

static const char *TAG = "hwv11_c3";
static const uint8_t HUB_MAC[ESP_NOW_ETH_ALEN] = {
    0x28, 0x84, 0x85, 0x50, 0x3e, 0xac,
};
static volatile uint32_t s_send_ok_count = 0;
static volatile uint32_t s_send_fail_count = 0;
static volatile bool s_send_in_flight = false;
static temperature_sensor_handle_t s_temp_sensor = NULL;

static void nvs_init_for_wifi(void)
{
    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        err = nvs_flash_init();
    }
    ESP_ERROR_CHECK(err);
}

static void espnow_send_cb(const esp_now_send_info_t *tx_info, esp_now_send_status_t status)
{
    (void)tx_info;
    if (status == ESP_NOW_SEND_SUCCESS) {
        ++s_send_ok_count;
    } else {
        ++s_send_fail_count;
    }
    s_send_in_flight = false;
}

static void espnow_init_node(void)
{
    nvs_init_for_wifi();
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));
    ESP_ERROR_CHECK(esp_wifi_set_storage(WIFI_STORAGE_RAM));
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_start());
    ESP_ERROR_CHECK(esp_wifi_set_channel(CONFIG_HWV11_C3_ESPNOW_CHANNEL, WIFI_SECOND_CHAN_NONE));

    ESP_ERROR_CHECK(esp_now_init());
    ESP_ERROR_CHECK(esp_now_register_send_cb(espnow_send_cb));
    esp_now_peer_info_t peer = {0};
    memcpy(peer.peer_addr, HUB_MAC, ESP_NOW_ETH_ALEN);
    peer.channel = CONFIG_HWV11_C3_ESPNOW_CHANNEL;
    peer.ifidx = WIFI_IF_STA;
    peer.encrypt = false;
    ESP_ERROR_CHECK(esp_now_add_peer(&peer));
}

static void temp_sensor_init(void)
{
    temperature_sensor_config_t cfg = TEMPERATURE_SENSOR_CONFIG_DEFAULT(50, 125);
    esp_err_t err = temperature_sensor_install(&cfg, &s_temp_sensor);
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "temperature sensor install failed: %s", esp_err_to_name(err));
        s_temp_sensor = NULL;
        return;
    }
    err = temperature_sensor_enable(s_temp_sensor);
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "temperature sensor enable failed: %s", esp_err_to_name(err));
        s_temp_sensor = NULL;
    }
}

static int16_t read_chip_temp_centi_c(bool *ok)
{
    float temp_c = 0.0f;
    if (s_temp_sensor == NULL ||
        temperature_sensor_get_celsius(s_temp_sensor, &temp_c) != ESP_OK) {
        if (ok != NULL) {
            *ok = false;
        }
        return INT16_MIN;
    }
    if (ok != NULL) {
        *ok = true;
    }
    return (int16_t)(temp_c * 100.0f);
}

void app_main(void)
{
    ESP_ERROR_CHECK(hwv11_i2c_init());
    temp_sensor_init();
    espnow_init_node();

    bool imu_ready = bmi160_init() == ESP_OK;
    if (!imu_ready) {
        ESP_LOGW(TAG, "BMI160 init failed; packets will carry node status=1");
    }

    hwv11_imu6_raw_t last_imu = {0};
    uint32_t seq = 0;
    uint32_t loop_count = 0;
    uint32_t retry_counter = 0;
    uint32_t last_log_seq = 0;
    uint32_t skipped_sends = 0;
    int64_t last_send_start_us = 0;
    int64_t last_temp_read_us = 0;
    int16_t cached_temp_centi_c = INT16_MIN;
    const int64_t period_us = 1000000LL / CONFIG_HWV11_C3_SAMPLE_RATE_HZ;
    int64_t next_us = esp_timer_get_time();

    while (true) {
        ++loop_count;
        const int64_t loop_ts_us = esp_timer_get_time();
        if (loop_ts_us - last_temp_read_us >= 1000000LL) {
            cached_temp_centi_c = read_chip_temp_centi_c(NULL);
            last_temp_read_us = loop_ts_us;
        }
        hwv11_node_packet_t packet = {
            .magic = HWV11_NODE_PACKET_MAGIC,
            .version = HWV11_NODE_PACKET_VERSION,
            .node_id = (uint8_t)CONFIG_HWV11_C3_NODE_ID,
            .status = 0,
            .seq = seq,
            .ts_us = (uint64_t)loop_ts_us,
            .imu = last_imu,
            .temp_centi_c = cached_temp_centi_c,
        };

        if (!imu_ready && retry_counter++ >= CONFIG_HWV11_C3_SAMPLE_RATE_HZ) {
            retry_counter = 0;
            imu_ready = bmi160_init() == ESP_OK;
            if (imu_ready) {
                ESP_LOGI(TAG, "BMI160 init recovered");
            }
        }

        if (imu_ready) {
            esp_err_t err = bmi160_read_raw(&last_imu);
            if (err == ESP_OK) {
                packet.imu = last_imu;
            } else {
                packet.status = 1;
                imu_ready = false;
            }
        } else {
            packet.status = 1;
        }

        esp_err_t send_err = ESP_OK;
        const int64_t now_us = esp_timer_get_time();
        const int64_t send_age_us = now_us - last_send_start_us;
        if (!s_send_in_flight || send_age_us > 50000) {
            s_send_in_flight = true;
            last_send_start_us = now_us;
            send_err = esp_now_send(HUB_MAC, (const uint8_t *)&packet, sizeof(packet));
            if (send_err != ESP_OK) {
                s_send_in_flight = false;
            } else {
                ++seq;
            }
        } else {
            ++skipped_sends;
            send_err = ESP_ERR_INVALID_STATE;
        }

        if (send_err != ESP_OK && send_err != ESP_ERR_INVALID_STATE) {
            ESP_LOGW(TAG, "esp_now_send failed: %s", esp_err_to_name(send_err));
        }

        if (loop_count - last_log_seq >= CONFIG_HWV11_C3_SAMPLE_RATE_HZ) {
            last_log_seq = loop_count;
            const bool temp_ok = packet.temp_centi_c != INT16_MIN;
            const float temp_c = packet.temp_centi_c / 100.0f;
            ESP_LOGI(TAG,
                     "loop=%" PRIu32 " seq=%" PRIu32 " bmi=%d status=%u temp=%s%.1fC send_err=%s ok=%" PRIu32 " fail=%" PRIu32
                     " skip=%" PRIu32
                     " raw=[%d,%d,%d,%d,%d,%d]",
                     loop_count, seq, imu_ready ? 1 : 0, packet.status,
                     temp_ok ? "" : "n/a/", temp_ok ? temp_c : 0.0f,
                     esp_err_to_name(send_err),
                     (uint32_t)s_send_ok_count, (uint32_t)s_send_fail_count,
                     skipped_sends,
                     last_imu.ax, last_imu.ay, last_imu.az,
                     last_imu.gx, last_imu.gy, last_imu.gz);
        }

        next_us += period_us;
        const int64_t after_send_us = esp_timer_get_time();
        if (next_us < after_send_us) {
            next_us = after_send_us + period_us;
        }
        while (true) {
            const int64_t now = esp_timer_get_time();
            const int64_t remaining = next_us - now;
            if (remaining <= 0) {
                break;
            }
            if (remaining > 1000) {
                vTaskDelay(pdMS_TO_TICKS((uint32_t)(remaining / 1000)));
            } else {
                esp_rom_delay_us((uint32_t)remaining);
            }
        }
    }
}
