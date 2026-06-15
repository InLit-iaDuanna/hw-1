#pragma once

#include <stdint.h>

#define HWV11_NODE_PACKET_MAGIC 0xC301
#define HWV11_NODE_PACKET_VERSION 1

typedef struct {
    int16_t ax;
    int16_t ay;
    int16_t az;
    int16_t gx;
    int16_t gy;
    int16_t gz;
} hwv11_imu6_raw_t;

typedef struct __attribute__((packed)) {
    uint16_t magic;
    uint8_t version;
    uint8_t node_id;
    uint8_t status;
    uint32_t seq;
    uint64_t ts_us;
    hwv11_imu6_raw_t imu;
    int16_t temp_centi_c;
} hwv11_node_packet_t;
