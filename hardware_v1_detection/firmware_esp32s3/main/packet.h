#pragma once

#include <stddef.h>
#include <stdint.h>

#include "hwv1_types.h"

#define HWV1_PACKET_MAGIC 0xA55A
#define HWV1_PACKET_VERSION 1
#define HWV1_PACKET_TYPE_SAMPLE 0x01
#define HWV1_PACKET_TYPE_NODE_DEBUG 0x11
#define HWV1_NODE_DEBUG_PAYLOAD_SIZE 38
#define HWV1_PACKET_HEADER_SIZE 20
#define HWV1_PACKET_CRC_SIZE 2
#define HWV1_MAX_PAYLOAD_SIZE HWV1_SAMPLE_PAYLOAD_SIZE
#define HWV1_PACKET_MAX_SIZE (HWV1_PACKET_HEADER_SIZE + HWV1_MAX_PAYLOAD_SIZE + HWV1_PACKET_CRC_SIZE)

uint16_t hwv1_crc16_ccitt(const uint8_t *data, size_t len);
size_t hwv1_encode_sample_payload(const hwv1_sample_t *sample, uint8_t *out, size_t out_cap);
size_t hwv1_encode_node_debug_payload(uint8_t node_id, uint8_t node_status,
                                      uint16_t age_ms, uint32_t c3_seq,
                                      uint64_t c3_ts_us, uint64_t s3_rx_ts_us,
                                      const hwv1_imu6_raw_t *imu,
                                      int16_t temp_centi_c,
                                      uint8_t *out, size_t out_cap);
size_t hwv1_packet_encode(uint8_t type, uint32_t seq, uint64_t ts_us, uint16_t status,
                          const uint8_t *payload, uint16_t payload_len,
                          uint8_t *out, size_t out_cap);
