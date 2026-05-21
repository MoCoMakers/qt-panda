/**************************************************************************/
/*

STM Firmware for Teensy 4.1 — Dan-style port (Phases 1-4)

Differences from v1 (pc/qtpanda, teensy/arduinosrc):
  - IntervalTimer ISR at 40 µs drives ADC reads and PI feedback
  - Sigma-delta converts 16-bit AD5761s to effective 20-bit resolution
  - Continuous bidirectional scan with ping-pong line buffers
  - Binary 'L' line frame for streaming; binary 'M' frame for lock-in
  - Legacy SCST/spectroscopy paths still work (blockISRControl flag)

*/
/**************************************************************************/

#ifndef STM_FIRMWARE_H
#define STM_FIRMWARE_H

#include <Arduino.h>
#include <SPI.h>
#include "LTC2326_16.hpp"
#include "EfficientStepper.hpp"
#include "AD5761.hpp"
#include "logTable.hpp"
#include "sigma_delta.hpp"
#include "line_buffer.hpp"
#include "binary_frame.hpp"

// ---- Pin assignments -------------------------------------------------------
#define CS_ADC   38
#define ADC_MISO 39
#define CNV      19
#define BUSY     18
#define SERIAL_LED 0
#define TUNNEL_LED 1

// DAC chip-select pins (AD5761, one per channel)
#define DAC_1  7   // X
#define DAC_3  8   // Z
#define DAC_2  9   // Y
#define DAC_4 10   // Bias

// ---- Resolution ------------------------------------------------------------
#define DAC_BITS      16
#define POSITION_BITS 20
#define ADC_BITS      16

const unsigned int SIGMA_SHIFT = POSITION_BITS - DAC_BITS;   // = 4
const int MAX_DAC_OUT = (1 << (DAC_BITS - 1)) - 1;           // 32767
const int MIN_DAC_OUT = -(1 << (DAC_BITS - 1));              // -32768
const int MAX_Z_POS   = (1 << (POSITION_BITS - 1)) - 1;      // 524287

// ---- Scan constants --------------------------------------------------------
#define SCAN_COUNTER_LIMIT 0x40000000   // 2^30

// ---- ISR timing ------------------------------------------------------------
// Default period; runtime-settable via SETD <us> command.
#define DEFAULT_CONTROL_DT_US 40

// ---- Motor -----------------------------------------------------------------
#define IN1 33
#define IN2 34
#define IN3 35
#define IN4 36
#define STEPS_PER_REVOLUTION 4096

// ---- Protocol --------------------------------------------------------------
#define CMD_LENGTH 4

// ---- Default PID values ----------------------------------------------------
#define INIT_KP 2.0
#define INIT_KI 1.0
#define INIT_KD 1.0

#define MOVE_SPEED 1

// ============================================================================

class STMStatus {
public:
    volatile int      bias          = 0;
    volatile int      dac_z         = 0;
    volatile int      dac_x         = 0;
    volatile int      dac_y         = 0;
    volatile int      adc           = 0;
    int               steps         = 0;
    volatile bool     is_approaching    = false;
    volatile bool     is_const_current  = false;
    volatile bool     is_scanning       = false;
    volatile uint32_t time_millis       = 0;

    void to_char(char *buffer) {
        sprintf(buffer, "%d,%d,%d,%d,%d,%d,%d,%d,%d,%lu",
                bias, dac_z, dac_x, dac_y, adc, steps,
                is_approaching, is_const_current, is_scanning, time_millis);
    }
};

struct Approach_Config {
    int target_dac;
    int max_steps;
    int step_interval;
};

static double clamp_value(double value, double min_value, double max_value) {
    if (value > max_value) return max_value;
    if (value < min_value) return min_value;
    return value;
}

// ============================================================================

class STM {
public:
    // ---- Legacy scan arrays (used by SCST one-shot scan) -------------------
    int scan_image_z[2048];
    int scan_image_adc[2048];
    int scan_image_noise[2048];

    EfficientStepper stepper_motor = EfficientStepper(STEPS_PER_REVOLUTION, IN1, IN3, IN2, IN4);

    int iv_bias[1000];
    int iv_adc[1000];
    int iv_N;
    int di_z[1000];
    int di_adc[1000];
    int di_N;

    int bias_settle_uS;
    int piezo_x_settle_uS;
    int piezo_y_settle_uS;
    int piezo_z_settle_uS;

    // ---- Legacy double-precision PI (used by SCST/spectroscopy path) -------
    bool   is_const_current = false;
    int    adc_set_value;
    volatile double adc_set_value_log, adc_real_value_log, dac_z_control_value;
    double Kp = 0.0, Ki = 0.0, Kd = 0.0;
    volatile double pTerm, iTerm;
    int    MotorDirection;

    // ---- ISR control flag --------------------------------------------------
    // When true the ISR returns immediately; main thread owns ADC + SPI.
    volatile bool blockISRControl = false;

    // ---- Continuous-scan parameters (Phase 2+) ----------------------------
    volatile int   scanSize     = 100000;  // Scan range in LSBs (~160 nm at typical calibration)
    volatile int   xo = 0, yo  = 0;       // Scan offsets in LSBs
    float          lineRate     = 1.0f;    // Lines per second
    bool           invertZ      = false;   // Set true if hardware inverts Z polarity
    int            control_dt_us = DEFAULT_CONTROL_DT_US;

    // ---- ISR scan counters -------------------------------------------------
    volatile int   xCount = -SCAN_COUNTER_LIMIT;
    volatile int   yCount = -SCAN_COUNTER_LIMIT;
    volatile int   dx = 0, dy = 0;

    // ---- ISR 20-bit virtual positions (sigma-delta input) ------------------
    volatile int   x_pos = 0, y_pos = 0, z_pos = 0;

    // ---- ISR sigma-delta integrators ---------------------------------------
    volatile int   sigmaX = 0, sigmaY = 0, sigmaZ = 0;

    // ---- ISR accumulation state (for averaging samples per pixel) ----------
    volatile unsigned int sampleCounter = 0;
    volatile unsigned int pixelCounter  = 0;
    volatile uint16_t     lineCounter   = 0;
    volatile unsigned int pixelsPerLine = 512;   // = imagePixels * 2
    volatile unsigned int samplesPerPixel = 24;
    volatile int32_t      zAvg = 0, eAvg = 0;

    // ---- ISR mode flags ---------------------------------------------------
    volatile bool scanningEnabled = false;
    volatile bool pidEnabled      = false;

    // ---- ISR integer PI ---------------------------------------------------
    volatile int     setpointLog = 0;
    volatile int     Kp_isr     = 0;
    volatile int     Ki_isr     = 300000;  // Dan's default (pure-I controller)
    volatile int64_t iTermISR   = 0;

    // ---- IntervalTimer ----------------------------------------------------
    IntervalTimer controlTimer;

    // =========================================================================
    // Setup helpers
    // =========================================================================

    void SetDefaults() {
        bias_settle_uS     = 100;
        piezo_x_settle_uS  = 5;
        piezo_y_settle_uS  = 5;
        piezo_z_settle_uS  = 5;
        MotorDirection     = 1;
    }

    // =========================================================================
    // ISR — called every control_dt_us by IntervalTimer
    // =========================================================================

    void controlTick() {
        if (blockISRControl) return;

        // 1. Increment scan counters -----------------------------------------
        if (scanningEnabled) {
            if (xCount <= -SCAN_COUNTER_LIMIT || xCount >= SCAN_COUNTER_LIMIT - 1 - dx)
                dx = -dx;
            xCount += dx;
            x_pos = (int)(((int64_t)xCount * (int64_t)scanSize) >> 31) + xo;

            if (yCount <= -SCAN_COUNTER_LIMIT || yCount >= SCAN_COUNTER_LIMIT - 1 - dy)
                dy = -dy;
            yCount += dy;
            y_pos = (int)(((int64_t)yCount * (int64_t)scanSize) >> 31) + yo;

            if (yCount <= -SCAN_COUNTER_LIMIT) lineCounter = 0; // resync guard
        }

        // 2. Read ADC ---------------------------------------------------------
        int adc_val = ltc2326.read();
        stm_status.adc = adc_val;

        // ADC saturation compensation (LTC2326-16 outputs 0 when clipping).
        // Only meaningful when PI is engaged — without PI, an ADC=0 reading
        // is just "no tunneling current" (tip not engaged).  Apply only when
        // we're actively tracking the surface.
        if (pidEnabled && adc_val == 0 && z_pos != -MAX_Z_POS) adc_val = 32767;

        int err = logTable[abs(adc_val)] - setpointLog;

        // 3. Integer PI -------------------------------------------------------
        if (pidEnabled) {
            int64_t pTerm_i = (int64_t)Kp_isr * (int64_t)err;
            iTermISR += (int64_t)Ki_isr * (int64_t)err;
            const int64_t MAX_ITERM = (int64_t)MAX_Z_POS * (int64_t)0x100000000LL;
            if      (iTermISR >  MAX_ITERM) iTermISR =  MAX_ITERM;
            else if (iTermISR < -MAX_ITERM) iTermISR = -MAX_ITERM;
            z_pos = (int)(((pTerm_i + iTermISR) >> 32) & 0xFFFFFFFF);
            if (z_pos >  MAX_Z_POS) z_pos =  MAX_Z_POS;
            if (z_pos < -MAX_Z_POS) z_pos = -MAX_Z_POS;
        }

        // 4. Start next ADC conversion ----------------------------------------
        ltc2326.convert();

        // 5. Sigma-delta → DAC writes -----------------------------------------
        // Z: always written when PI is enabled
        if (pidEnabled) {
            int zout = sigmaDelta(z_pos, &sigmaZ, SIGMA_SHIFT);
            if (invertZ) zout = -zout;
            if (zout >  MAX_DAC_OUT) zout =  MAX_DAC_OUT;
            if (zout < MIN_DAC_OUT)  zout =  MIN_DAC_OUT;
            dac_z.write(CMD_WR_UPDATE_DAC_REG, (uint16_t)(zout + 32768));
            stm_status.dac_z = (uint16_t)(zout + 32768);
        }

        // X/Y: only during continuous scan
        if (scanningEnabled) {
            int xout = sigmaDelta(x_pos, &sigmaX, SIGMA_SHIFT);
            if (xout >  MAX_DAC_OUT) xout =  MAX_DAC_OUT;
            if (xout < MIN_DAC_OUT)  xout =  MIN_DAC_OUT;
            dac_x.write(CMD_WR_UPDATE_DAC_REG, (uint16_t)(xout + 32768));
            stm_status.dac_x = (uint16_t)(xout + 32768);

            int yout = sigmaDelta(y_pos, &sigmaY, SIGMA_SHIFT);
            if (yout >  MAX_DAC_OUT) yout =  MAX_DAC_OUT;
            if (yout < MIN_DAC_OUT)  yout =  MIN_DAC_OUT;
            dac_y.write(CMD_WR_UPDATE_DAC_REG, (uint16_t)(yout + 32768));
            stm_status.dac_y = (uint16_t)(yout + 32768);
        }

        // 6. Accumulate pixel data -------------------------------------------
        if (scanningEnabled) {
            zAvg += z_pos;
            eAvg += err;
            sampleCounter++;

            if (sampleCounter >= samplesPerPixel) {
                int32_t zMean = zAvg / (int)samplesPerPixel;
                int32_t eMean = eAvg / (int)samplesPerPixel;

                uint8_t *buf = fillData1 ? data1 : data2;
                writePixel(buf, pixelCounter, pixelsPerLine, zMean, eMean);

                pixelCounter++;
                sampleCounter = 0;
                zAvg = 0;
                eAvg = 0;

                if (pixelCounter >= pixelsPerLine) {
                    // Stamp line number into buffer header
                    buf[0] = (uint8_t)((lineCounter >> 8) & 0xFF);
                    buf[1] = (uint8_t)( lineCounter        & 0xFF);

                    pixelCounter    = 0;
                    fillData1       = !fillData1;
                    pendingLineNumber = lineCounter;
                    sendData        = true;
                    lineCounter++;
                    if (lineCounter >= pixelsPerLine) lineCounter = 0;
                }
            }
        }

        stm_status.time_millis = millis();
    }

    // =========================================================================
    // Control loop management
    // =========================================================================

    void startControlLoop(void (*fn)()) {
        _controlCallback  = fn;
        controlTimer.priority(0);
        controlTimer.begin(fn, (float)control_dt_us);
        _controlLoopRunning = true;
    }

    void stopControlLoop() {
        controlTimer.end();
        _controlLoopRunning = false;
    }

    // =========================================================================
    // Continuous scan management (Phase 2+)
    // =========================================================================

    void updateStepSizes() {
        // Guard the divisor — lineRate may briefly be 0 while the user types
        // a new value through SETP/LRAT.
        float divisor = lineRate * (float)control_dt_us * (float)pixelsPerLine;
        if (divisor < 1.0f) divisor = 1.0f;
        unsigned int new_spp = (unsigned int)(1000000.0f / divisor);
        if (new_spp < 1) new_spp = 1;
        // Clamp samplesPerPixel so zAvg (int32) cannot overflow:
        //   max |zAvg| = samplesPerPixel * MAX_Z_POS (~524287)
        //   int32 limit is 2^31 - 1, so cap at ~4000.
        if (new_spp > 4000) new_spp = 4000;
        unsigned int denom = new_spp * (unsigned int)pixelsPerLine;
        if (denom == 0) denom = 1;
        int new_dx = (SCAN_COUNTER_LIMIT - 1) / (int)denom * 4;
        int new_dy = new_dx / (int)pixelsPerLine;
        if (new_dx < 1) new_dx = 1;
        if (new_dy < 1) new_dy = 1;

        noInterrupts();
        samplesPerPixel = new_spp;
        // Strict > 0 matches Dan's reference: when dx is 0 (post-reset), we
        // pick the negative branch so the very-first ISR tick (xCount = -LIMIT)
        // reverses dx to positive and the scan ramps up correctly.
        dx = (dx > 0) ?  new_dx : -new_dx;
        dy = (dy > 0) ?  new_dy : -new_dy;
        interrupts();
    }

    void resetScanCounters() {
        noInterrupts();
        xCount       = -SCAN_COUNTER_LIMIT;
        yCount       = -SCAN_COUNTER_LIMIT;
        dx            = 0;          // Must be 0 before updateStepSizes (see above)
        dy            = 0;
        sampleCounter = 0;
        pixelCounter  = 0;
        lineCounter   = 0;
        zAvg          = 0;
        eAvg          = 0;
        sigmaX        = 0;
        sigmaY        = 0;
        sigmaZ        = 0;
        fillData1     = true;
        sendData      = false;
        interrupts();
        updateStepSizes();
    }

    void start_continuous_scan() {
        resetScanCounters();
        noInterrupts();
        scanningEnabled         = true;
        stm_status.is_scanning  = true;
        interrupts();
    }

    void stop_continuous_scan() {
        noInterrupts();
        scanningEnabled         = false;
        stm_status.is_scanning  = false;
        // Park X/Y at their offsets so the tip stops moving mid-line.
        // (Z is left under PI control if pidEnabled.)
        interrupts();
    }

    // Engage the PI loop with bumpless transfer.
    // Returns false (and refuses to engage) if no setpoint has been programmed —
    // PI with setpointLog=0 would integrate at full rate until the tip retracts
    // to its stop, so we treat "no setpoint" as a safety abort.
    bool engage() {
        if (setpointLog == 0) {
            Serial.println("ENGA refused: no setpoint (use SETP first)");
            return false;
        }

        // Bumpless transfer: preload z_pos and iTermISR from the current
        // 16-bit DAC code so the first PI tick reproduces the present Z.
        int z_sync = (int)(((int64_t)stm_status.dac_z - 32768) << 4);
        if (z_sync >  MAX_Z_POS) z_sync =  MAX_Z_POS;
        if (z_sync < -MAX_Z_POS) z_sync = -MAX_Z_POS;

        noInterrupts();
        z_pos                       = z_sync;
        iTermISR                    = (int64_t)z_sync << 32;
        pidEnabled                  = true;
        stm_status.is_const_current = true;
        interrupts();
        return true;
    }

    void retract() {
        noInterrupts();
        pidEnabled                  = false;
        scanningEnabled             = false;
        stm_status.is_const_current = false;
        stm_status.is_scanning      = false;
        interrupts();
        // Move Z to safe-retracted position using legacy path
        bool savedBlock = blockISRControl;
        blockISRControl = true;
        set_dac_z(50000);
        blockISRControl = savedBlock;
    }

    void setSetpoint(int sp) {
        noInterrupts();
        setpointLog = logTable[abs(sp)];
        interrupts();
    }

    // Convert legacy double gains (from PIDS command) to ISR integer gains.
    // Scaling: ISR z = (Kp*err + Ki*err*accumulation) >> 32.
    // A reasonable default scale maps to similar step sizes as the double PI.
    void setIsrGains(double kp, double ki) {
        noInterrupts();
        Kp_isr = (int)(kp * 65536.0);
        Ki_isr = (int)(ki * 65536.0);
        interrupts();
    }

    // Emit a completed line buffer over serial (called from loop()).
    // Phase 3: binary 'L' frame. Phase 2 ASCII path is commented below.
    void emitPendingLine() {
        if (!sendData) return;

        // The just-filled buffer is the one that was NOT switched to:
        // After fillData1 flips, the freshly-filled buffer is the OLD side.
        uint8_t *buf = fillData1 ? data2 : data1;
        emitBinaryFrame(buf, pendingLineNumber, pixelsPerLine);

        sendData = false;
    }

    // =========================================================================
    // Phase 4 — Lock-in dI/dV
    // Modulates bias at freq_hz, demodulates synchronously, returns (X, Y).
    // =========================================================================
    void lock_in_didv(int bias_center, int bias_amp_lsb,
                      int freq_hz, int n_periods) {
        // Bounds-check inputs to avoid divide-by-zero / overflow.
        if (freq_hz       <= 0) freq_hz       = 1000;
        if (bias_settle_uS <= 0) bias_settle_uS = 10;
        if (n_periods     <= 0) n_periods     = 1;

        bool savedBlock = blockISRControl;
        blockISRControl = true;

        // Steps per period: sample-rate / modulation-rate.
        int sample_rate_hz = 1000000 / bias_settle_uS;   // safe: settle > 0
        int steps_per_period = sample_rate_hz / freq_hz;
        if (steps_per_period < 2) steps_per_period = 2;

        // Use int32_t to avoid int16_t overflow when n_periods * spp > 32767.
        int32_t total_points = (int32_t)n_periods * (int32_t)steps_per_period;

        int64_t sumX = 0, sumY = 0;
        int saved_bias = stm_status.bias;

        for (int32_t pt = 0; pt < total_points; pt++) {
            // Sine-wave bias modulation (integer approximation)
            // Phase angle: 2*pi*pt / steps_per_period
            // sin ~ (pt % steps_per_period < steps_per_period/2) ? +1 : -1 (square wave)
            int half = steps_per_period / 2;
            int phase_pos = pt % steps_per_period;
            int mod = (phase_pos < half) ? bias_amp_lsb : -bias_amp_lsb;
            set_dac_bias(bias_center + mod);
            delayMicroseconds(bias_settle_uS);

            int adc = read_adc_raw();

            // Demodulate: reference is square wave ±1
            int ref = (phase_pos < half) ? 1 : -1;
            sumX += (int64_t)adc * ref;   // in-phase
            // Quadrature: 90° shifted
            int q_pos = (phase_pos + steps_per_period / 4) % steps_per_period;
            int qref = (q_pos < half) ? 1 : -1;
            sumY += (int64_t)adc * qref;

            // Emit one 'M' frame per period boundary
            if (phase_pos == steps_per_period - 1) {
                int32_t X = (int32_t)(sumX / steps_per_period);
                int32_t Y = (int32_t)(sumY / steps_per_period);
                emitLockInFrame((uint16_t)(pt / steps_per_period),
                                (int32_t)bias_center, X, Y);
                sumX = 0;
                sumY = 0;
            }
        }

        set_dac_bias(saved_bias);
        blockISRControl = savedBlock;
    }

    // =========================================================================
    // Motor control
    // =========================================================================

    void setMotorDirection(int dir) { MotorDirection = dir; }

    void move_motor(int steps) {
        steps = steps * MotorDirection;
        stepper_motor.step(steps);
        stm_status.steps     = stepper_motor.get_total_steps();
        stm_status.time_millis = millis();
        //stepper_motor.disable();
    }

    void motoroff() { stepper_motor.disable(); }

    // =========================================================================
    // Reset
    // =========================================================================

    void reset() {
        bool wasRunning = _controlLoopRunning;
        if (wasRunning) stopControlLoop();

        stepper_motor.setSpeed(2);
        stepper_motor.reset();
        dac_x.reset();
        dac_y.reset();
        dac_z.reset();
        dac_bias.reset();
        stm_status = STMStatus();

        scanningEnabled = false;
        pidEnabled      = false;
        blockISRControl = false;

        ltc2326.convert();

        if (wasRunning && _controlCallback) startControlLoop(_controlCallback);
    }

    // =========================================================================
    // DAC writes — guarded so ISR cannot preempt a main-thread SPI transaction
    // =========================================================================

    void set_dac_z(int value) {
        noInterrupts();
        dac_z.write(CMD_WR_UPDATE_DAC_REG, value);
        interrupts();
        stm_status.dac_z   = value;
        stm_status.time_millis = millis();
    }
    void set_dac_x(int value) {
        noInterrupts();
        dac_x.write(CMD_WR_UPDATE_DAC_REG, value);
        interrupts();
        stm_status.dac_x   = value;
        stm_status.time_millis = millis();
    }
    void set_dac_y(int value) {
        noInterrupts();
        dac_y.write(CMD_WR_UPDATE_DAC_REG, value);
        interrupts();
        stm_status.dac_y   = value;
        stm_status.time_millis = millis();
    }
    void set_dac_bias(int value) {
        noInterrupts();
        dac_bias.write(CMD_WR_UPDATE_DAC_REG, value);
        interrupts();
        stm_status.bias    = value;
        stm_status.time_millis = millis();
    }

    // =========================================================================
    // ADC — safe to call when blockISRControl = true (ISR won't contest SPI1)
    // =========================================================================

    int read_adc_raw() {
        int start_time = millis();
        while (ltc2326.busy() && millis() - start_time <= 1) {}
        int val = ltc2326.read();
        _add_adc_value(val);
        ltc2326.convert();
        return val;
    }
    int read_adc() {
        read_adc_raw();
        return _get_adc_avg();
    }
    void update() {
        int adc_val = read_adc_raw();
        stm_status.adc     = adc_val;
        stm_status.time_millis = millis();
    }

    STMStatus get_status() { return stm_status; }

    // =========================================================================
    // Approach
    // =========================================================================

    Approach_Config approach_config = Approach_Config();

    void start_approach(int target_adc, int max_motor_steps, int step_interval) {
        approach_config.max_steps    = stepper_motor.get_total_steps() + max_motor_steps;
        approach_config.step_interval = step_interval;
        approach_config.target_dac   = target_adc;
        stm_status.is_approaching    = true;
    }

    bool approach() {
        int adc_val;
        if (!stm_status.is_approaching) return false;

        bool savedBlock = blockISRControl;
        blockISRControl = true;

        set_dac_z(10000);
        delayMicroseconds(piezo_z_settle_uS);

        if (stepper_motor.get_total_steps() < approach_config.max_steps) {
            move_motor(approach_config.step_interval);
            delay(2);
            for (int z_value = 10000; z_value <= 50000; z_value += 100) {
                set_dac_z(z_value);
                delayMicroseconds(piezo_z_settle_uS);
                update();
                adc_val = read_adc();
                if (adc_val > approach_config.target_dac ||
                    adc_val < -approach_config.target_dac) {
                    Serial.println("Approached!");
                    Serial.println(stm_status.adc);
                    stm_status.is_approaching = false;
                    stepper_motor.disable();
                    _syncZPos();
                    blockISRControl = savedBlock;
                    return true;
                }
            }
            for (int z_value = 50000; z_value > 10000; z_value -= 100) {
                set_dac_z(z_value);
                delayMicroseconds(piezo_z_settle_uS);
                update();
            }
            set_dac_z(10000);
            delayMicroseconds(piezo_z_settle_uS);
        } else {
            stm_status.is_approaching = false;
            blockISRControl = savedBlock;
            return false;
        }

        blockISRControl = savedBlock;
        return false;
    }

    // =========================================================================
    // Legacy const-current (CCON/CCOF) — used by SCST scan loop
    // =========================================================================

    void turn_on_const_current(int target_adc) {
        this->adc_set_value = target_adc;
        double log_val = static_cast<double>(logTable[abs(target_adc)]);
        double z_val   = static_cast<double>(stm_status.dac_z);

        // Sync ISR integer PI setpoint & pre-load iTerm for bumpless transfer
        int z_sync = (int)(((int64_t)stm_status.dac_z - 32768) << 4);
        if (z_sync >  MAX_Z_POS) z_sync =  MAX_Z_POS;
        if (z_sync < -MAX_Z_POS) z_sync = -MAX_Z_POS;

        noInterrupts();
        this->adc_set_value_log  = log_val;
        this->dac_z_control_value = z_val;
        this->pTerm              = 0.0;
        this->iTerm              = 0.0;
        this->setpointLog        = logTable[abs(target_adc)];
        this->z_pos              = z_sync;
        this->iTermISR           = (int64_t)z_sync << 32;
        this->pidEnabled         = true;
        this->stm_status.is_const_current = true;
        interrupts();
    }

    // Legacy double-precision PI — called from start_scan() when blockISRControl = true
    int control_current(int adc_value) {
        this->adc_real_value_log = static_cast<double>(logTable[abs(adc_value)]);
        double error = this->adc_set_value_log - this->adc_real_value_log;
        pTerm  = Kp * error;
        iTerm += Ki * error;
        iTerm  = clamp_value(iTerm, -32768, 32768);
        int z  = static_cast<int>(pTerm + iTerm) + 32768;
        if (z > 50000) z = 50000;
        if (z < 10000) z = 10000;
        this->set_dac_z(z);
        return static_cast<int>(error);
    }

    void turn_off_const_current() {
        noInterrupts();
        this->stm_status.is_const_current = false;
        this->pidEnabled = false;
        interrupts();
    }

    // =========================================================================
    // Spectroscopy
    // =========================================================================

    void generate_iv_curve(int bias_start, int bias_end, int bias_step) {
        bool savedBlock = blockISRControl;
        blockISRControl = true;

        int i = 0;
        int init_bias = stm_status.bias;
        for (int bias = bias_start; bias < bias_end; bias += bias_step) {
            if (i >= 1000) break;
            set_dac_bias(bias);
            delayMicroseconds(bias_settle_uS);
            int adc = read_adc();
            iv_adc[i]  = adc;
            iv_bias[i] = bias;
            i++;
        }
        iv_N = i;
        set_dac_bias(init_bias);

        blockISRControl = savedBlock;
    }

    void send_iv_curve() {
        Serial.print("IV,");
        for (int i = 0; i < iv_N; ++i) {
            Serial.print(iv_bias[i]);
            Serial.print(",");
            Serial.print(iv_adc[i]);
            if (i < iv_N - 1) Serial.print(",");
        }
        Serial.print("\r\n");
    }

    void generate_iv_didv_curve(int bias_start, int bias_end, int bias_step) {
        bool savedBlock = blockISRControl;
        blockISRControl = true;

        int i = 0;
        int init_bias = stm_status.bias;

        for (int bias = bias_start; bias <= bias_end; bias += bias_step) {
            if (i >= 1000) break;
            set_dac_bias(bias);
            delayMicroseconds(bias_settle_uS);
            int adc = read_adc();
            iv_bias[i] = bias;
            iv_adc[i]  = adc;
            i++;
        }
        iv_N = i;

        for (int j = 1; j < iv_N - 1; j++) {
            int dI = iv_adc[j+1] - iv_adc[j-1];
            int dV = iv_bias[j+1] - iv_bias[j-1];
            di_adc[j] = (dV != 0) ? dI / dV : 0;
            di_z[j]   = iv_bias[j];
        }
        if (iv_N > 1) {
            di_adc[0]      = (iv_adc[1] - iv_adc[0]) / (iv_bias[1] - iv_bias[0]);
            di_adc[iv_N-1] = (iv_adc[iv_N-1] - iv_adc[iv_N-2]) /
                              (iv_bias[iv_N-1] - iv_bias[iv_N-2]);
        }
        di_N = iv_N;
        set_dac_bias(init_bias);

        blockISRControl = savedBlock;
    }

    void send_iv_didv_curve() {
        Serial.print("IVD,");
        Serial.print(iv_N);
        Serial.print(",");
        for (int i = 0; i < iv_N; i++) {
            Serial.print(iv_bias[i]);
            Serial.print(",");
            Serial.print(iv_adc[i]);
            Serial.print(",");
            Serial.print(di_adc[i]);
            if (i < iv_N - 1) Serial.print(",");
        }
        Serial.print("\r\n");
    }

    void generate_dIdZ_curve(int z_start, int z_end, int z_step) {
        bool savedBlock = blockISRControl;
        blockISRControl = true;

        int i = 0;
        const int delta_z = 100;

        for (int z = z_start; z < z_end; z += z_step) {
            if (i >= 1000) break;
            set_dac_z(z + delta_z);
            delayMicroseconds(piezo_z_settle_uS);
            int I_plus = read_adc();
            set_dac_z(z - delta_z);
            delayMicroseconds(piezo_z_settle_uS);
            int I_minus = read_adc();
            set_dac_z(z);
            delayMicroseconds(piezo_z_settle_uS);
            di_z[i]   = z;
            di_adc[i] = (I_plus - I_minus) / (2 * delta_z);
            i++;
        }
        di_N = i;

        blockISRControl = savedBlock;
    }

    void send_dIdZ_curve() {
        Serial.print("DI,");
        for (int i = 0; i < di_N; ++i) {
            Serial.print(di_z[i]);
            Serial.print(",");
            Serial.print(di_adc[i]);
            if (i < di_N - 1) Serial.print(",");
        }
        Serial.print("\r\n");
    }

    void start_grid_spectroscopy(int x_start, int x_end, int x_res,
                                  int y_start, int y_end, int y_res,
                                  int bias_start, int bias_end, int bias_points,
                                  uint8_t mode) {
        bool savedBlock = blockISRControl;
        blockISRControl = true;

        bool feedback_was = stm_status.is_const_current;
        int  saved_sp     = adc_set_value;
        turn_off_const_current();

        uint32_t x_step    = (x_end - x_start) / (x_res - 1);
        uint32_t y_step    = (y_end - y_start) / (y_res - 1);
        uint32_t bias_step = (bias_end - bias_start) / (bias_points - 1);

        for (int y = 0; y < y_res; y++) {
            set_dac_y(y_start + y * y_step);
            delayMicroseconds(piezo_y_settle_uS);
            for (int x = 0; x < x_res; x++) {
                set_dac_x(x_start + x * x_step);
                delayMicroseconds(piezo_x_settle_uS);

                Serial.write('P'); Serial.write('X');
                Serial.write((uint8_t *)&x, 2);
                Serial.write((uint8_t *)&y, 2);
                Serial.write((uint8_t *)&bias_points, 2);
                Serial.write(mode);

                uint16_t prev_adc = 0;
                for (int i = 0; i < bias_points; i++) {
                    set_dac_bias(bias_start + i * bias_step);
                    delayMicroseconds(bias_settle_uS);
                    uint16_t adc = (uint16_t)read_adc();
                    if (mode == 0) {
                        Serial.write((uint8_t *)&adc, 2);
                    } else {
                        uint16_t didv = (i > 0) ? (adc - prev_adc) : 0;
                        prev_adc = adc;
                        Serial.write((uint8_t *)&didv, 2);
                    }
                }
            }
        }
        if (feedback_was) turn_on_const_current(saved_sp);

        blockISRControl = savedBlock;
    }

    // =========================================================================
    // Legacy one-shot scan (SCST) — unchanged from v1 semantics
    // =========================================================================

    void noise_scan(int x_resolution, int y_resolution,
                    int sample_per_pixel, int usDelay) {
        bool savedBlock = blockISRControl;
        blockISRControl = true;

        x_resolution   = 256; y_resolution   = 256;
        sample_per_pixel = 10; usDelay = 10;

        for (int x_i = 0; x_i < x_resolution; ++x_i) {
            delayMicroseconds(usDelay);
            int sample_count = 0, err_sum = 0;
            for (int y_i = 0; y_i < y_resolution * sample_per_pixel; ++y_i) {
                delayMicroseconds(usDelay);
                int adc_value = read_adc_raw();
                if (stm_status.is_const_current) adc_value = control_current(adc_value);
                err_sum += adc_value;
                sample_count++;
                if (sample_count == sample_per_pixel) {
                    scan_image_noise[y_i / sample_per_pixel] = err_sum / sample_per_pixel;
                    sample_count = 0; err_sum = 0;
                }
            }
            send_scan_line("N", x_i, scan_image_noise, y_resolution);
            for (int y_i = y_resolution * sample_per_pixel - 1; y_i >= 0; --y_i) {
                delayMicroseconds(usDelay);
                if (stm_status.is_const_current) control_current(read_adc_raw());
            }
        }
        Serial.println("D");

        blockISRControl = savedBlock;
    }

    void start_scan(int x_start, int x_end, int x_resolution,
                    int y_start, int y_end, int y_resolution,
                    int sample_per_pixel) {
        bool savedBlock = blockISRControl;
        blockISRControl = true;

        move_to(x_start, y_start);
        double x_step = 1.0f * (x_end - x_start) / x_resolution;
        double y_step = 1.0f * (y_end - y_start) / y_resolution / sample_per_pixel;

        for (int x_i = 0; x_i < x_resolution; ++x_i) {
            set_dac_x((int)(x_start + x_i * x_step));
            delayMicroseconds(piezo_x_settle_uS);
            int sample_count = 0, err_sum = 0, dacz_sum = 0;
            for (int y_i = 0; y_i < y_resolution * sample_per_pixel; ++y_i) {
                set_dac_y((int)(y_start + y_i * y_step));
                delayMicroseconds(piezo_y_settle_uS);
                int adc_value = read_adc_raw();
                if (stm_status.is_const_current) adc_value = control_current(adc_value);
                err_sum  += adc_value;
                dacz_sum += stm_status.dac_z;
                sample_count++;
                if (sample_count == sample_per_pixel) {
                    scan_image_adc[y_i / sample_per_pixel] = err_sum  / sample_per_pixel;
                    scan_image_z[y_i / sample_per_pixel]   = dacz_sum / sample_per_pixel;
                    sample_count = 0; err_sum = 0; dacz_sum = 0;
                }
            }
            send_scan_line("A", x_i, scan_image_adc, y_resolution);
            send_scan_line("Z", x_i, scan_image_z,   y_resolution);
            for (int y_i = y_resolution * sample_per_pixel - 1; y_i >= 0; --y_i) {
                set_dac_y((int)(y_start + y_i * y_step));
                delayMicroseconds(piezo_y_settle_uS);
                if (stm_status.is_const_current) control_current(read_adc_raw());
            }
        }
        Serial.println("D");

        // Sync z_pos with final scan DAC value for smooth ISR handoff
        _syncZPos();
        blockISRControl = savedBlock;
    }

    void send_scan_line(String prefix, int x_i, int *data, int num_points) {
        Serial.print(prefix);
        Serial.printf(",%d,", x_i);
        for (int i = 0; i < num_points; ++i) {
            Serial.print(data[i]);
            if (i < num_points - 1) Serial.print(",");
        }
        Serial.print("\r\n");
    }

    void move_to(int target_x, int target_y) {
        while (target_x != stm_status.dac_x) {
            if (stm_status.is_const_current) control_current(read_adc_raw());
            int diff = target_x - stm_status.dac_x;
            if (abs(diff) < MOVE_SPEED) set_dac_x(target_x);
            else set_dac_x(stm_status.dac_x + ((diff > 0) ? MOVE_SPEED : -MOVE_SPEED));
        }
        while (target_y != stm_status.dac_y) {
            if (stm_status.is_const_current) control_current(read_adc_raw());
            int diff = target_y - stm_status.dac_y;
            if (abs(diff) < MOVE_SPEED) set_dac_y(target_y);
            else set_dac_y(stm_status.dac_y + ((diff > 0) ? MOVE_SPEED : -MOVE_SPEED));
        }
    }

    void test_piezo() {
        bool savedBlock = blockISRControl;
        blockISRControl = true;
        for (int i = 0; i < 500; i++) { set_dac_z(50000); delayMicroseconds(500); set_dac_z(0); delayMicroseconds(500); }
        delay(1000);
        for (int i = 0; i < 500; i++) { set_dac_x(50000); delayMicroseconds(500); set_dac_x(0); delayMicroseconds(500); }
        delay(1000);
        for (int i = 0; i < 500; i++) { set_dac_y(50000); delayMicroseconds(500); set_dac_y(0); delayMicroseconds(500); }
        blockISRControl = savedBlock;
    }

    STMStatus stm_status = STMStatus();

private:
    AD5761 dac_x    = AD5761(DAC_1, 0b0000000000000101);  // ±5 V
    AD5761 dac_y    = AD5761(DAC_2, 0b0000000000000101);  // ±5 V
    AD5761 dac_z    = AD5761(DAC_3, 0b0000000000000000);  // ±10 V
    AD5761 dac_bias = AD5761(DAC_4, 0b0000000000000101);  // ±5 V

    LTC2326_16 ltc2326 = LTC2326_16(CS_ADC, CNV, BUSY);

    int _adc_buffer[5];
    int _current_index = 0;
    int _adc_sum = 0;
    void _add_adc_value(int value) {
        _current_index = (_current_index + 1) % 5;
        _adc_sum -= _adc_buffer[_current_index];
        _adc_buffer[_current_index] = value;
        _adc_sum += value;
    }
    int _get_adc_avg() { return static_cast<int>(_adc_sum / 5.0); }

    void (*_controlCallback)() = nullptr;
    bool _controlLoopRunning   = false;

    // Sync ISR z_pos from the current 16-bit DAC code for bumpless transfer
    void _syncZPos() {
        if (!pidEnabled) return;
        int z_sync = (int)(((int64_t)stm_status.dac_z - 32768) << 4);
        if (z_sync >  MAX_Z_POS) z_sync =  MAX_Z_POS;
        if (z_sync < -MAX_Z_POS) z_sync = -MAX_Z_POS;
        noInterrupts();
        z_pos    = z_sync;
        iTermISR = (int64_t)z_sync << 32;
        interrupts();
    }
};

#endif // STM_FIRMWARE_H
