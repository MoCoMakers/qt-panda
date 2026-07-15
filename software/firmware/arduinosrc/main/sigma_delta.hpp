#ifndef SIGMA_DELTA_H
#define SIGMA_DELTA_H

// Three-state first-order sigma-delta. Increases effective DAC resolution
// by POSITION_BITS - DAC_BITS = 4 bits (16-bit DAC → 20-bit virtual position).
// Based on Tim Wescott's technique; identical to Dan Berard's STM_Controller.ino.
inline int sigmaDelta(int in, volatile int *sigma, unsigned int shift) {
    int out;
    *sigma += in;
    out = *sigma >> shift;
    *sigma -= out << shift;
    return out;
}

#endif // SIGMA_DELTA_H
