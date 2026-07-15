# Smoke test & next-steps — dans-software-port

> **Status:** transient / working document.
> **Last code update:** 2026-05-15.
> **Audience:** hardware team running async bench validation.
>
> All code paths described below compile cleanly (Arduino IDE → Teensy 4.1, 56 KB flash + 213 KB RAM1) and pass static review, but **nothing in this document has been confirmed on a physical instrument**. This file documents what to check, in what order, and what each result means. Delete or fold into the main docs once validation is complete.

## TL;DR for the bench

Before running anything new:

1. Flash `dans-software-port/teensy/arduinosrc/main/main.ino`.
2. Launch `dans-software-port/pc/qtpanda/widget.py`.
3. Confirm v1-equivalent behavior **first** (legacy commands), then test the new continuous-scan path.

If anything in the legacy column behaves differently from v1, **stop and report** — the port was meant to be backward-compatible.

## What is unverified on hardware

These are the design changes that have NOT been validated at the bench yet:

| Area | Change | Risk |
|---|---|---|
| Control loop | Moved from `loop()` to `IntervalTimer` ISR at 40 µs | Real-time ISR budget |
| SPI arbitration | `noInterrupts()` around all main-thread DAC writes; `blockISRControl` flag during long ops | Race conditions under load |
| Scan path | Continuous bidirectional scan with sigma-delta dither | Many new code paths |
| Streaming | Binary `'L'` frame at 921 600 baud | USB-Serial throughput |
| PC threading | `SerialReaderThread` (QThread) replaces synchronous reads during continuous scan | UI responsiveness |
| New commands | `RUN `, `HALT`, `ENGA`, `RTRC`, `SCSZ`, `IPLN`, `LRAT`, `XOFS`, `YOFS`, `SETP`, `KPGA`, `KIGA`, `SETD`, `LIDV` | Logic correctness |
| Bumpless transfer | `engage()` and `CCON` preload `z_pos` and `iTermISR` | Tip-safety in mode transitions |
| ADC saturation | Compensation now gated on `pidEnabled` | Subtle behavior change vs v1 |

## Test plan

Run in order. Each test gates the next one. If a test fails, stop and capture the firmware + PC output for triage.

### A. Cold-power sanity (no tip motion, no engagement)

| Step | Command | Expected |
|---|---|---|
| A1 | Power up Teensy, open serial monitor at 921 600 | No spontaneous bytes; firmware silent |
| A2 | `GSTS` | 10 comma-separated ints; `is_approaching=0 is_const_current=0 is_scanning=0` |
| A3 | Toggle Teensy pin 2 inside `controlTick()` (temp instrumentation) and scope it | 40 µs ± few µs period, stable |
| A4 | `BIAS 32768` | Bias DAC output ≈ 0 V (or mid-rail, per calibration) |
| A5 | `DACX 50000`, then `DACX 15000` | X DAC follows |
| A6 | `ADCR` | Returns a sensible int (depends on whatever the ADC pin sees) |

**Fail mode for A3:** if jitter > a few µs, look for long-running interrupt handlers or `Serial.write` in `loop()` being slow.

### B. v1 parity (the things that must not regress)

| Step | Command | Expected |
|---|---|---|
| B1 | `MTMV 100`, then `MTOF` | Stepper moves identically to v1 |
| B2 | `APRH 1000 5000` (or your usual approach target) | Coarse approach converges; firmware prints `Approached!` followed by ADC value |
| B3 | `CCON 1000` → wait 30 s → `CCOF` | Tip holds setpoint; Z drift no worse than v1 over 30 s |
| B4 | `IVME -1000 1000 50` then `IVGE` | `IVD,...` ASCII line identical in format to v1 |
| B5 | Run a `SCST` scan on a known sample via the v1-style "Scan" button | Image visually identical to v1 |

**B3 is the critical regression check.** If Z drift or noise is materially worse than v1, the ISR PI math is probably off.

### C. New continuous-scan path

Pre-conditions: B passed. Tip is approached. ADC reads stable tunneling current at setpoint.

| Step | Command (or UI action) | Expected |
|---|---|---|
| C1 | `SETP 1000` | No response; `GSTS` shows no obvious change |
| C2 | `KPGA 0` then `KIGA 4.5776` | Same |
| C3 | `SCSZ 50000`, `IPLN 256`, `LRAT 100` | Same |
| C4 | `ENGA` | Firmware prints `ENGA OK`; tip enters PI control with bumpless transfer (no Z jump) |
| C5 | `ENGA` *before* any `SETP` (test from cold) | Firmware prints `ENGA refused: no setpoint (use SETP first)` |
| C6 | `RUN ` (with trailing space) | Binary bytes start flowing; first byte of each frame is `0x4C` |
| C7 | `GSTS` while running | Shows `is_scanning=1` |
| C8 | `HALT` | Byte flow stops; tip remains engaged at last X,Y position |
| C9 | `RTRC` | PI disengages; Z parked at retracted position |

**Use the continuous-scan tab in `widget.py`** to drive C1–C9 graphically. Watch the live raster:

- Forward trace and reverse retrace should show the same surface features (toggle the "Direction" combo).
- Z and error images update once per scanned line.
- Halting cleanly stops the image from updating.

### D. Stress / robustness

| Step | Action | Expected |
|---|---|---|
| D1 | Start continuous scan, drag the window around | UI stays responsive (this is what `SerialReaderThread` is for) |
| D2 | Change `IPLN` from 256 → 512 during a scan | **One** transient bad line, then clean scan at new resolution |
| D3 | `HALT` then immediately `RUN ` | Reader thread restarts cleanly (no two-readers race) |
| D4 | Unplug USB during scan | PC reader thread exits cleanly; reconnecting and pressing RUN works again |
| D5 | Send `SCST` while continuous scan is running | Continuous scan resumes after SCST completes (documented behavior; widget does not auto-HALT — to be added) |
| D6 | `SETD 80` (double the ISR period) while scanning | Scan continues, slower; **one** transient line |

> **D2/D6 fail mode:** if you see *many* corrupted lines (not just one) on a
> mid-scan parameter change, the firmware in flash predates the
> `Serial.setTimeout(20)` fix in `setup()`. Parameterized commands carry no
> line terminator, so `Serial.parseInt()` blocks for the whole Stream timeout;
> at the 1000 ms default this stalls `loop()`/`emitPendingLine()` long enough
> to overrun the ping-pong buffers. Re-flash from current source and retest.

### E. Lock-in dI/dV (Phase 4 firmware only — no UI yet)

| Step | Command | Expected |
|---|---|---|
| E1 | With tip engaged, `LIDV 0 1000 1000 5` | 5 binary `'M'` frames at 16 bytes each (5 periods of 1 kHz mod) |
| E2 | `LIDV 0 0 0 0` | No crash (input bounds clamping); produces minimal data |

The PC reader parses these into the `lockInPoint` Qt signal, but **no UI consumes it yet**. Verify on serial monitor or hex-dump.

## What's NOT done yet (post-validation backlog)

These items are intentionally out of scope until smoke tests pass:

- **Lock-in dI/dV UI tab** — `serial_reader.py` parses `'M'` frames into the `lockInPoint` signal, but `widget.py` has no consumer. Add a tab with frequency/amplitude/setpoint controls and a result plot.
- **Calibration preferences pane** — `calibration.py` and `calibration.json` exist, but the UI shows LSBs only. Add a pane that displays physical-unit equivalents alongside the LSB fields.
- **Setpoint autotuner** — `tuning.py` from the plan was not created. Defer until Ki/Kp tuning by hand reveals what the user actually wants.
- **Auto-HALT on legacy operations** — currently, pressing legacy "Scan" or "Grid Spectro" buttons during a continuous scan races for the serial port. The widget should call `_scan_ctrl.halt()` automatically at the top of those handlers.
- **`Ki` rescaling on `SETD`** — `Ki_isr` is currently fixed-scaled by 65536, not by `control_dt_us`. Changing the ISR period changes the loop response. Either rescale on `SETD` or document.

## Known small things to watch for

- **First-tick PI transient on `ENGA`** — bumpless transfer initializes `iTermISR`, but `sigmaZ` is frozen from its last value when PI was off. Expect ≤ 100 µs of imperfect DAC dither at the engagement instant.
- **`pixelsPerLine` should be even** — odd values produce asymmetric trace/retrace splits. Not enforced by firmware; widget defaults to even values.
- **Status fields `is_scanning`/`is_const_current`** — both flags update from the new code paths. The PC's `STM_Status.from_list` already accepts the 10-field response.
- **Mid-stream `IPLN`/`SCSZ`/`LRAT`** — one transient bad line during the change; the buffer briefly overlaps Z and error regions. This assumes `Serial.setTimeout(20)` is active (set in `setup()`); see the D2/D6 fail-mode note above for why.
- **No command line terminator (by design)** — `checkSerial()` reads exactly `CMD_LENGTH` bytes, so the PC must *not* append `\n`/`\r` (a stray byte would corrupt the next 4-char read). The cost is that `parseInt()`/`parseFloat()` always run to the Stream timeout; this is pre-existing v1 behavior, now bounded to 20 ms. Do not "fix" it by adding a terminator on the PC side.

## Smoke-test sign-off template

Copy this into your bench log; one line per test:

```
[ ] A1  power-up silent
[ ] A2  GSTS sane defaults
[ ] A3  ISR period 40 µs ± _____ µs
[ ] A4  bias mid-rail
[ ] A5  DACX follows
[ ] A6  ADCR returns _____ at idle

[ ] B1  stepper unchanged
[ ] B2  approach converges at _____ steps
[ ] B3  CCON 30 s drift = _____ pm/s (v1 baseline _____ pm/s)
[ ] B4  IV curve format unchanged
[ ] B5  SCST scan matches v1

[ ] C1-3  settings round-trip
[ ] C4   ENGA bumpless (no Z jump observed visually)
[ ] C5   ENGA refused with no SETP
[ ] C6   RUN  starts 'L' frames
[ ] C7   GSTS shows is_scanning=1
[ ] C8   HALT stops cleanly
[ ] C9   RTRC retracts cleanly

[ ] D1   UI responsive during scan
[ ] D2   IPLN change recovers after 1 line
[ ] D3   HALT/RUN cycle clean
[ ] D4   USB unplug recovery
[ ] D5   SCST during scan: behavior matches doc
[ ] D6   SETD change clean

[ ] E1   LIDV emits 5 'M' frames
[ ] E2   LIDV with zero-args doesn't crash
```

When all rows are checked: replace this document with a normal "release notes" entry in the main README and merge `dans-software-port` toward eventual v2 cutover.
