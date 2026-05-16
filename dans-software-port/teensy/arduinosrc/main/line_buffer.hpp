#ifndef LINE_BUFFER_H
#define LINE_BUFFER_H

#include <Arduino.h>

// Maximum image pixels per line (per direction). Each pixel costs 8 bytes
// (4 bytes Z + 4 bytes error), plus 2 bytes for the line-number header.
#define MAX_PIXELS_PER_LINE 2048
#define LINE_BUFFER_SIZE (2 + 8 * MAX_PIXELS_PER_LINE)  // 16386 bytes

// Ping-pong buffer pair — ISR fills one while loop() emits the other.
uint8_t data1[LINE_BUFFER_SIZE];
uint8_t data2[LINE_BUFFER_SIZE];
volatile bool     fillData1        = true;   // ISR writes into data1 when true
volatile bool     sendData         = false;  // Set by ISR when a line is ready
volatile uint16_t pendingLineNumber = 0;     // Line counter snapshot taken by ISR

// Write one averaged pixel into the current buffer.
// Layout (identical to Dan's): bytes 0-1 = line number;
// bytes 2..2+4*N-1 = int32 z[N] big-endian;
// bytes 2+4*N..2+8*N-1 = int32 err[N] big-endian.
inline void writePixel(uint8_t *buf,
                       unsigned int pixIdx,
                       unsigned int pixelsPerLine,
                       int32_t z, int32_t err) {
    unsigned int idxZ = (pixIdx << 2) + 2;
    unsigned int idxE = idxZ + (pixelsPerLine << 2);
    buf[idxZ]   = (uint8_t)((z   >> 24) & 0xFF);
    buf[idxZ+1] = (uint8_t)((z   >> 16) & 0xFF);
    buf[idxZ+2] = (uint8_t)((z   >>  8) & 0xFF);
    buf[idxZ+3] = (uint8_t)( z          & 0xFF);
    buf[idxE]   = (uint8_t)((err >> 24) & 0xFF);
    buf[idxE+1] = (uint8_t)((err >> 16) & 0xFF);
    buf[idxE+2] = (uint8_t)((err >>  8) & 0xFF);
    buf[idxE+3] = (uint8_t)( err        & 0xFF);
}

#endif // LINE_BUFFER_H
