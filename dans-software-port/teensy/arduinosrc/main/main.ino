#include <Arduino.h>
#include <SPI.h>
#include "stm_firmware.hpp"

#define CMD_LENGTH 4
STM stm = STM();

// ISR wrapper — called by IntervalTimer every control_dt_us microseconds.
void controlISR() { stm.controlTick(); }

// ============================================================================
// Serial command dispatcher
// ============================================================================

void serialCommand(String command, STM &stm)
{
    if (command.length() != CMD_LENGTH) return;

    // ---- Reset ---------------------------------------------------------------
    if (command == "RSET") {
        stm.reset();
    }
    // ---- Bias ----------------------------------------------------------------
    else if (command == "BIAS") {
        int value = Serial.parseInt();
        stm.set_dac_bias(value);
    }
    // ---- Stepper motor -------------------------------------------------------
    else if (command == "MTMV") {
        int value = Serial.parseInt();
        stm.move_motor(value);
    }
    else if (command == "MTOF") {
        stm.motoroff();
    }
    else if (command == "MTDR") {
        int direction = Serial.parseInt();
        stm.setMotorDirection(direction);
    }
    // ---- DAC direct writes ---------------------------------------------------
    else if (command == "DACX") {
        int value = Serial.parseInt();
        stm.set_dac_x(value);
    }
    else if (command == "DACY") {
        int value = Serial.parseInt();
        stm.set_dac_y(value);
    }
    else if (command == "DACZ") {
        int value = Serial.parseInt();
        stm.set_dac_z(value);
    }
    // ---- ADC read ------------------------------------------------------------
    else if (command == "ADCR") {
        // Block the ISR while we own SPI1; the ISR's adc.read()/convert()
        // would otherwise race with read_adc()'s SPI traffic.
        bool savedBlock = stm.blockISRControl;
        stm.blockISRControl = true;
        int val = stm.read_adc();
        stm.blockISRControl = savedBlock;
        Serial.println(val);
    }
    // ---- Status --------------------------------------------------------------
    else if (command == "GSTS") {
        char buffer[100];
        stm.get_status().to_char(buffer);
        Serial.println(buffer);
    }
    // ---- Approach ------------------------------------------------------------
    else if (command == "APRH") {
        int adc_target = Serial.parseInt();
        int steps      = Serial.parseInt();
        stm.start_approach(adc_target, 10000, steps);
    }
    // ---- IV / dIdV -----------------------------------------------------------
    else if (command == "IVME") {
        int bias_start = Serial.parseInt();
        int bias_end   = Serial.parseInt();
        int bias_step  = Serial.parseInt();
        stm.generate_iv_didv_curve(bias_start, bias_end, bias_step);
    }
    else if (command == "IVGE") {
        stm.send_iv_didv_curve();
    }
    // ---- dIdZ ----------------------------------------------------------------
    else if (command == "DIME") {
        int z_start = Serial.parseInt();
        int z_end   = Serial.parseInt();
        int z_step  = Serial.parseInt();
        stm.generate_dIdZ_curve(z_start, z_end, z_step);
    }
    else if (command == "DIGE") {
        stm.send_dIdZ_curve();
    }
    // ---- Noise scan ----------------------------------------------------------
    else if (command == "NOIS") {
        int xres = Serial.parseInt();
        int yres = Serial.parseInt();
        int spp  = Serial.parseInt();
        int uS   = Serial.parseInt();
        stm.noise_scan(xres, yres, spp, uS);
    }
    // ---- Grid spectroscopy ---------------------------------------------------
    else if (command == "GSPC") {
        int x_start      = Serial.parseInt();
        int x_end        = Serial.parseInt();
        int x_res        = Serial.parseInt();
        int y_start      = Serial.parseInt();
        int y_end        = Serial.parseInt();
        int y_res        = Serial.parseInt();
        int bias_start   = Serial.parseInt();
        int bias_end     = Serial.parseInt();
        int bias_points  = Serial.parseInt();
        int mode         = Serial.parseInt();
        stm.start_grid_spectroscopy(x_start, x_end, x_res,
                                    y_start, y_end, y_res,
                                    bias_start, bias_end, bias_points, mode);
    }
    // ---- Const-current (legacy CCON/CCOF) ------------------------------------
    else if (command == "CCON") {
        int adc_target = Serial.parseInt();
        stm.turn_on_const_current(adc_target);
    }
    else if (command == "CCOF") {
        stm.turn_off_const_current();
    }
    // ---- PID gains (legacy PIDS — also updates ISR gains) --------------------
    else if (command == "PIDS") {
        double Kp = Serial.parseFloat();
        double Ki = Serial.parseFloat();
        double Kd = Serial.parseFloat();
        stm.Kp = Kp;
        stm.Ki = Ki;
        stm.Kd = Kd;
        stm.setIsrGains(Kp, Ki);
    }
    // ---- One-shot scan (SCST — deprecated, retained for backward compat) -----
    else if (command == "SCST") {
        int x_start      = Serial.parseInt();
        int x_end        = Serial.parseInt();
        int x_resolution = Serial.parseInt();
        int y_start      = Serial.parseInt();
        int y_end        = Serial.parseInt();
        int y_resolution = Serial.parseInt();
        int spp          = Serial.parseInt();
        stm.start_scan(x_start, x_end, x_resolution,
                       y_start, y_end, y_resolution, spp);
    }
    // ---- Piezo test ----------------------------------------------------------
    else if (command == "TEST") {
        stm.test_piezo();
    }
    // ---- Stop all modes ------------------------------------------------------
    else if (command == "STOP") {
        stm.stm_status.is_approaching    = false;
        stm.stm_status.is_const_current  = false;
        stm.stm_status.is_scanning       = false;
        stm.stop_continuous_scan();
        stm.turn_off_const_current();
    }
    // ---- Settle times --------------------------------------------------------
    else if (command == "SETL") {
        stm.piezo_x_settle_uS = Serial.parseInt();
        stm.piezo_y_settle_uS = Serial.parseInt();
        stm.piezo_z_settle_uS = Serial.parseInt();
        stm.bias_settle_uS    = Serial.parseInt();
    }

    // ==========================================================================
    // Phase 2+ commands — continuous scan control
    // ==========================================================================

    // ---- Start / stop continuous scan ----------------------------------------
    else if (command == "RUN ") {
        stm.start_continuous_scan();
    }
    else if (command == "HALT") {
        stm.stop_continuous_scan();
    }
    // ---- Tip engage / retract ------------------------------------------------
    else if (command == "ENGA") {
        // engage() returns false (and prints its own message) if there is
        // no setpoint — refuse silently here, don't ack with "OK".
        if (stm.engage()) Serial.println("ENGA OK");
    }
    else if (command == "RTRC") {
        stm.retract();
    }
    // ---- Scan geometry -------------------------------------------------------
    else if (command == "SCSZ") {
        stm.scanSize = Serial.parseInt();
        stm.updateStepSizes();
    }
    else if (command == "IPLN") {
        int v = Serial.parseInt();
        if (v < 2) v = 2;
        if (v > MAX_PIXELS_PER_LINE) v = MAX_PIXELS_PER_LINE;
        stm.pixelsPerLine = (unsigned int)v;
        stm.updateStepSizes();
    }
    else if (command == "LRAT") {
        // Line rate in units of 0.01 Hz (e.g., 100 = 1.00 Hz)
        int v = Serial.parseInt();
        stm.lineRate = v / 100.0f;
        stm.updateStepSizes();
    }
    else if (command == "XOFS") {
        stm.xo = Serial.parseInt();
    }
    else if (command == "YOFS") {
        stm.yo = Serial.parseInt();
    }
    // ---- Feedback parameters -------------------------------------------------
    else if (command == "SETP") {
        stm.setSetpoint(Serial.parseInt());
    }
    else if (command == "KPGA") {
        stm.Kp = Serial.parseFloat();
        stm.setIsrGains(stm.Kp, stm.Ki);
    }
    else if (command == "KIGA") {
        stm.Ki = Serial.parseFloat();
        stm.setIsrGains(stm.Kp, stm.Ki);
    }
    // ---- ISR period (SETD <microseconds>) ------------------------------------
    else if (command == "SETD") {
        int us = Serial.parseInt();
        if (us < 10) us = 10;
        if (us > 1000) us = 1000;
        stm.stopControlLoop();
        stm.control_dt_us = us;
        stm.startControlLoop(controlISR);
        stm.updateStepSizes();
    }
    // ---- Phase 4: lock-in dI/dV ----------------------------------------------
    else if (command == "LIDV") {
        int bias_center  = Serial.parseInt();
        int bias_amp     = Serial.parseInt();
        int freq_hz      = Serial.parseInt();
        int n_periods    = Serial.parseInt();
        stm.lock_in_didv(bias_center, bias_amp, freq_hz, n_periods);
    }
}

// ============================================================================

void checkSerial(STM &stm)
{
    if (Serial.available() < CMD_LENGTH) return;

    String serialString;
    for (int i = 0; i < CMD_LENGTH; i++) {
        serialString += (char)Serial.read();
    }
    serialCommand(serialString, stm);
}

// ============================================================================

void setup()
{
    Serial.begin(921600);
    // PC commands carry no line terminator (the fixed CMD_LENGTH reader in
    // checkSerial() forbids one — a stray '\n' would corrupt the next 4-char
    // read). Without a trailing delimiter, Serial.parseInt()/parseFloat()
    // cannot return early and blocks for the full Stream timeout. The 1000 ms
    // default would stall loop() — and therefore emitPendingLine() — long
    // enough to overrun the ping-pong buffers on any mid-scan parameter
    // change (SMOKE_TEST.md D2/D6). At 921600 baud a whole command arrives in
    // well under 1 ms, so 20 ms is ample headroom while bounding the stall.
    Serial.setTimeout(20);
    SPI.begin();
    SPI1.setSCK(27);
    SPI1.setCS(38);
    SPI1.setMISO(39);
    SPI1.begin();
    stm.reset();
    stm.SetDefaults();
    stm.startControlLoop(controlISR);
}

void loop()
{
    checkSerial(stm);

    // Emit any completed scan line (set by ISR via sendData flag)
    stm.emitPendingLine();

    // Approach runs cooperatively from loop() — uses blockISRControl internally
    if (stm.stm_status.is_approaching) {
        stm.approach();
    }
}
