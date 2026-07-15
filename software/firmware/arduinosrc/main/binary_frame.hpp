#ifndef BINARY_FRAME_H
#define BINARY_FRAME_H

#include <Arduino.h>

// Binary 'L' frame format (Phase 3 continuous-scan streaming):
//
//   Byte 0       : 0x4C ('L') magic
//   Bytes 1-2    : uint16 line_number  (big-endian)
//   Bytes 3-4    : uint16 pixels_per_line (big-endian)
//   Bytes 5..    : int32  z[pixels_per_line]   (big-endian)
//   ...          : int32  err[pixels_per_line] (big-endian)
//   Last byte    : 0x0A newline terminator
//
// Total = 5 + 8*pixels_per_line + 1 bytes.
// The pixel data in buf[] is already packed big-endian by writePixel().
inline void emitBinaryFrame(const uint8_t *buf,
                             uint16_t lineNumber,
                             uint16_t pixelsPerLine) {
    // Header
    Serial.write(0x4C);
    Serial.write((uint8_t)((lineNumber    >> 8) & 0xFF));
    Serial.write((uint8_t)( lineNumber          & 0xFF));
    Serial.write((uint8_t)((pixelsPerLine >> 8) & 0xFF));
    Serial.write((uint8_t)( pixelsPerLine        & 0xFF));
    // Payload: z block then err block, already big-endian in buf[2..]
    Serial.write(buf + 2, (size_t)(8 * pixelsPerLine));
    // Terminator
    Serial.write(0x0A);
}

// Binary 'S' frame (Phase 5 push-mode status streaming, STRM command):
//
//   Byte 0    : 0x53 ('S') magic
//   Bytes 1-4 : uint32 time_millis (big-endian)
//   Bytes 5-6 : int16  adc
//   Bytes 7-8 : uint16 dac_z
//   Bytes 9-10: uint16 bias
//   Bytes 11-14: int32 steps
//   Byte 15   : flags (bit0 approaching, bit1 const_current, bit2 scanning)
//   Byte 16   : 0x0A terminator
//
// Total = 17 bytes; at the 500 Hz cap this is ~8.5 KB/s.
inline void emitStatusFrame(uint32_t timeMillis, int16_t adc,
                             uint16_t dacZ, uint16_t bias,
                             int32_t steps, uint8_t flags) {
    uint8_t buf[17];
    buf[0]  = 0x53;
    buf[1]  = (uint8_t)((timeMillis >> 24) & 0xFF);
    buf[2]  = (uint8_t)((timeMillis >> 16) & 0xFF);
    buf[3]  = (uint8_t)((timeMillis >>  8) & 0xFF);
    buf[4]  = (uint8_t)( timeMillis        & 0xFF);
    buf[5]  = (uint8_t)(((uint16_t)adc >> 8) & 0xFF);
    buf[6]  = (uint8_t)( (uint16_t)adc       & 0xFF);
    buf[7]  = (uint8_t)((dacZ >> 8) & 0xFF);
    buf[8]  = (uint8_t)( dacZ       & 0xFF);
    buf[9]  = (uint8_t)((bias >> 8) & 0xFF);
    buf[10] = (uint8_t)( bias       & 0xFF);
    buf[11] = (uint8_t)(((uint32_t)steps >> 24) & 0xFF);
    buf[12] = (uint8_t)(((uint32_t)steps >> 16) & 0xFF);
    buf[13] = (uint8_t)(((uint32_t)steps >>  8) & 0xFF);
    buf[14] = (uint8_t)( (uint32_t)steps        & 0xFF);
    buf[15] = flags;
    buf[16] = 0x0A;
    Serial.write(buf, sizeof(buf));
}

// Binary 'M' frame (Phase 4 lock-in dI/dV measurement point):
//
//   Byte 0   : 0x4D ('M') magic
//   Bytes 1-2: uint16 point_index (big-endian)
//   Bytes 3-6: int32 bias_lsb (big-endian)
//   Bytes 7-10: int32 in_phase (big-endian)
//   Bytes 11-14: int32 quadrature (big-endian)
//   Byte 15  : 0x0A terminator
inline void emitLockInFrame(uint16_t idx,
                             int32_t biasLsb,
                             int32_t inPhase,
                             int32_t quad) {
    Serial.write(0x4D);
    Serial.write((uint8_t)((idx     >> 8) & 0xFF));
    Serial.write((uint8_t)( idx           & 0xFF));
    Serial.write((uint8_t)((biasLsb >> 24) & 0xFF));
    Serial.write((uint8_t)((biasLsb >> 16) & 0xFF));
    Serial.write((uint8_t)((biasLsb >>  8) & 0xFF));
    Serial.write((uint8_t)( biasLsb        & 0xFF));
    Serial.write((uint8_t)((inPhase >> 24) & 0xFF));
    Serial.write((uint8_t)((inPhase >> 16) & 0xFF));
    Serial.write((uint8_t)((inPhase >>  8) & 0xFF));
    Serial.write((uint8_t)( inPhase        & 0xFF));
    Serial.write((uint8_t)((quad    >> 24) & 0xFF));
    Serial.write((uint8_t)((quad    >> 16) & 0xFF));
    Serial.write((uint8_t)((quad    >>  8) & 0xFF));
    Serial.write((uint8_t)( quad           & 0xFF));
    Serial.write(0x0A);
}

#endif // BINARY_FRAME_H
