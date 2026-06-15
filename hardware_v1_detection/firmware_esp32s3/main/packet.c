#include "packet.h"

static void put_u16(uint8_t *out, size_t *pos, uint16_t value)
{
    out[(*pos)++] = (uint8_t)(value & 0xFFu);
    out[(*pos)++] = (uint8_t)((value >> 8) & 0xFFu);
}

static void put_i16(uint8_t *out, size_t *pos, int16_t value)
{
    put_u16(out, pos, (uint16_t)value);
}

static void put_u32(uint8_t *out, size_t *pos, uint32_t value)
{
    for (int i = 0; i < 4; ++i) {
        out[(*pos)++] = (uint8_t)((value >> (8 * i)) & 0xFFu);
    }
}

static void put_u64(uint8_t *out, size_t *pos, uint64_t value)
{
    for (int i = 0; i < 8; ++i) {
        out[(*pos)++] = (uint8_t)((value >> (8 * i)) & 0xFFu);
    }
}

uint16_t hwv1_crc16_ccitt(const uint8_t *data, size_t len)
{
    uint16_t crc = 0xFFFFu;
    for (size_t i = 0; i < len; ++i) {
        crc ^= (uint16_t)data[i] << 8;
        for (int bit = 0; bit < 8; ++bit) {
            if (crc & 0x8000u) {
                crc = (uint16_t)((crc << 1) ^ 0x1021u);
            } else {
                crc = (uint16_t)(crc << 1);
            }
        }
    }
    return crc;
}

static void encode_imu6(const hwv1_imu6_raw_t *imu, uint8_t *out, size_t *pos)
{
    put_i16(out, pos, imu->ax);
    put_i16(out, pos, imu->ay);
    put_i16(out, pos, imu->az);
    put_i16(out, pos, imu->gx);
    put_i16(out, pos, imu->gy);
    put_i16(out, pos, imu->gz);
}

size_t hwv1_encode_sample_payload(const hwv1_sample_t *sample, uint8_t *out, size_t out_cap)
{
    if (out_cap < HWV1_SAMPLE_PAYLOAD_SIZE) {
        return 0;
    }
    size_t pos = 0;
    for (int i = 0; i < HWV1_BMI_SENSOR_COUNT; ++i) {
        encode_imu6(&sample->bmi[i], out, &pos);
    }
    put_i16(out, &pos, sample->bmx.ax);
    put_i16(out, &pos, sample->bmx.ay);
    put_i16(out, &pos, sample->bmx.az);
    put_i16(out, &pos, sample->bmx.gx);
    put_i16(out, &pos, sample->bmx.gy);
    put_i16(out, &pos, sample->bmx.gz);
    put_i16(out, &pos, sample->bmx.mx);
    put_i16(out, &pos, sample->bmx.my);
    put_i16(out, &pos, sample->bmx.mz);
    return pos;
}

size_t hwv1_encode_node_debug_payload(uint8_t node_id, uint8_t node_status,
                                      uint16_t age_ms, uint32_t c3_seq,
                                      uint64_t c3_ts_us, uint64_t s3_rx_ts_us,
                                      const hwv1_imu6_raw_t *imu,
                                      int16_t temp_centi_c,
                                      uint8_t *out, size_t out_cap)
{
    if (out_cap < HWV1_NODE_DEBUG_PAYLOAD_SIZE) {
        return 0;
    }
    size_t pos = 0;
    out[pos++] = node_id;
    out[pos++] = node_status;
    put_u16(out, &pos, age_ms);
    put_u32(out, &pos, c3_seq);
    put_u64(out, &pos, c3_ts_us);
    put_u64(out, &pos, s3_rx_ts_us);
    encode_imu6(imu, out, &pos);
    put_i16(out, &pos, temp_centi_c);
    return pos;
}

size_t hwv1_packet_encode(uint8_t type, uint32_t seq, uint64_t ts_us, uint16_t status,
                          const uint8_t *payload, uint16_t payload_len,
                          uint8_t *out, size_t out_cap)
{
    const size_t total = HWV1_PACKET_HEADER_SIZE + payload_len + HWV1_PACKET_CRC_SIZE;
    if (out_cap < total) {
        return 0;
    }

    size_t pos = 0;
    put_u16(out, &pos, HWV1_PACKET_MAGIC);
    out[pos++] = HWV1_PACKET_VERSION;
    out[pos++] = type;
    put_u16(out, &pos, payload_len);
    put_u32(out, &pos, seq);
    put_u64(out, &pos, ts_us);
    put_u16(out, &pos, status);

    for (uint16_t i = 0; i < payload_len; ++i) {
        out[pos++] = payload[i];
    }

    const uint16_t crc = hwv1_crc16_ccitt(out, pos);
    put_u16(out, &pos, crc);
    return pos;
}
