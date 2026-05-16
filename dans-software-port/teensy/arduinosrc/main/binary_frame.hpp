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
