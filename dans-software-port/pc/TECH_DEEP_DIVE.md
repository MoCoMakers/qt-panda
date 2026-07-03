# qt-panda STM — Technical Deep-Dive (Dan-style port)

Audience: engineers extending or debugging the system. This explains *how*
the control architecture works and *why* the design decisions were made.
For operation see [`USER_GUIDE.md`](USER_GUIDE.md); for the build flow and
wire protocol see [`../README.md`](../README.md).

---

## 1. System architecture
 
```
   PC (PySide6)                          Teensy 4.1 @ 600 MHz
 ┌───────────────────┐   USB-Serial    ┌──────────────────────────────┐
 │ widget.py (UI)     │   921600 baud   │ main.ino  (4-char cmd parser)│
 │  ├ ScanController  │ ───ASCII cmd──▶ │  loop(): checkSerial,        │
 │  │   (unit conv)   │                 │          emitPendingLine,    │
 │  ├ SerialReader     │ ◀─bin 'L'/'M'─ │          approach            │
 │  │   QThread        │ ◀─ASCII rows── │                              │
 │  ├ LiveRaster       │                 │ IntervalTimer ISR @ 40 µs:   │
 │  └ Calibration      │                 │  controlTick() — scan, PI,   │
 └───────────────────┘                 │  sigma-delta, pixel buffers   │
                                         └──────────────────────────────┘
```

The instrument is the same qt-panda hardware as v1 (Teensy 4.1, 4× AD5761
single-channel 16-bit DACs on SPI0, LTC2326-16 16-bit ADC on SPI1,
ULN2003 stepper). The port changes only *algorithms*, never hardware.

Five behavioural pillars, all adopted from Dan Berard's published design:

1. Deterministic ISR control loop at fixed `dt`.
2. Log-domain PI on tunnel current.
3. Sigma-delta dither: 16-bit DAC → effective 20-bit position.
4. Ping-pong line buffers decoupling acquisition from USB.
5. Continuous bidirectional scan (trace + retrace per line).

---

## 2. Firmware

### 2.1 Deterministic control loop

v1 ran the control work cooperatively from `loop()` at whatever cadence
the serial/USB stack allowed — non-deterministic jitter directly modulates
a feedback loop that is trying to hold a tunnel gap stable to picometres.

The port moves the inner loop into an `IntervalTimer` ISR:

```cpp
void controlISR() { stm.controlTick(); }   // main.ino
controlTimer.begin(controlISR, control_dt_us);   // default 40 µs = 25 kHz
```

`controlTick()` executes a fixed sequence every tick:

1. `if (blockISRControl) return;` — cooperative yield for long main-thread ops.
2. Scan-counter increment (if `scanningEnabled`).
3. ADC read + saturation compensation + log-domain error.
4. Integer PI → `z_pos` (if `pidEnabled`).
5. `ltc2326.convert()` — start the *next* conversion now so data is ready
   next tick (one-tick pipeline; the ADC conversion overlaps compute).
6. Sigma-delta on Z (if `pidEnabled`) and X/Y (if `scanningEnabled`) → DACs.
7. Pixel accumulation → `writePixel` → on line complete, swap ping-pong
   buffer and set `sendData`.

`SETD <µs>` makes the period runtime-tunable (`stopControlLoop` →
update `control_dt_us` → `startControlLoop`).

### 2.2 Log-domain integer PI

Tunnel current is exponential in gap distance, so the loop regulates
`log(|I|)` rather than `I` — this linearises the plant and gives roughly
distance-proportional error. `logTable[]` is a precomputed lookup
(`logTable.hpp`), so the log costs one array access in the ISR.

The PI math is **pure integer / fixed-point** (no float in the ISR — the
Cortex-M7 FPU is fast but float in an ISR invites torn 64-bit reads):

```cpp
int err      = logTable[abs(adc_val)] - setpointLog;
int64_t pT   = (int64_t)Kp_isr * (int64_t)err;
iTermISR    += (int64_t)Ki_isr * (int64_t)err;        // clamp ±MAX_ITERM
z_pos = (int)(((pT + iTermISR) >> 32) & 0xFFFFFFFF);  // clamp ±MAX_Z_POS
```

- `iTermISR` is `int64_t`; the `>> 32` is a Q32 fixed-point divide, so
  the integral term has 32 fractional bits of headroom against drift.
- `MAX_ITERM = MAX_Z_POS * 2^32` is the anti-windup clamp.
- Defaults: `Kp_isr = 0`, `Ki_isr = 300000` — a pure-I controller,
  matching Dan's reference.
- The `& 0xFFFFFFFF` + `(int)` cast round-trips the sign correctly on a
  two's-complement machine (verified: a negative Q32 value masked to 32
  bits and reinterpreted as `int` yields the correct negative result).

The legacy double-precision PI (`control_current()`) is retained but only
runs inside legacy `SCST`/spectroscopy paths, which set
`blockISRControl = true` so the two controllers never run simultaneously.

### 2.3 Sigma-delta dither

A 16-bit DAC has ~150 µV steps on a ±5 V range. Dan's trick: maintain a
20-bit *virtual* position and dither the bottom 4 bits across successive
DAC writes; the analog reconstruction filter averages them, yielding ~9 µV
effective resolution. This is the entire reason the ISR must write the
DACs *every tick* even when a value is unchanged.

```cpp
inline int sigmaDelta(int in, volatile int *sigma, unsigned int shift) {
    *sigma += in;
    int out = *sigma >> shift;     // shift = POSITION_BITS - DAC_BITS = 4
    *sigma -= out << shift;
    return out;                    // 16-bit code; -32768..32767
}
```

It's a first-order error-feedback modulator (Tim Wescott's technique).
`sigma` is `volatile` because it lives in the `STM` object and the ISR
mutates it (the `volatile int*` parameter was a deliberate signature
choice to silence the `-fpermissive` conversion).

> **Intentional divergence from Dan:** Dan writes all three DACs every
> tick unconditionally. The port writes Z only when `pidEnabled` and X/Y
> only when `scanningEnabled`. This is correct for the qt-panda hybrid:
> when idle, manual `DACX/Y/Z`/`BIAS` writes must *persist* rather than be
> overwritten by a zero-position dither. The cost is a sub-100-µs
> sigma-delta convergence transient on re-engagement — negligible.

### 2.4 Bidirectional scan counters

Position is generated by a free-running counter, not a ramp, so trace and
retrace are exactly symmetric:

```cpp
if (xCount <= -SCAN_COUNTER_LIMIT || xCount >= SCAN_COUNTER_LIMIT-1-dx)
    dx = -dx;                                   // reverse at line ends
xCount += dx;
x_pos = (int)(((int64_t)xCount * (int64_t)scanSize) >> 31) + xo;
```

`SCAN_COUNTER_LIMIT = 2^30`; the counter sweeps ±2^30 regardless of scan
size, and `scanSize` (LSB) scales the projection. `xo`/`yo` are added as a
pan offset.

`updateStepSizes()` derives the increments:

```
samplesPerPixel = 1e6 / (lineRate · dt_µs · pixelsPerLine)   // clamp [1, 4000]
dx = (SCAN_COUNTER_LIMIT-1) / (samplesPerPixel · pixelsPerLine) · 4
dy = dx / pixelsPerLine
```

**Bootstrap subtlety (a real bug found and fixed in review):** the sign of
`dx` must be chosen with strict `> 0`, not `>= 0`. `resetScanCounters()`
zeroes `dx` then calls `updateStepSizes()`; with `dx == 0` the strict test
picks `-new_dx`, so the very first ISR tick (`xCount == -LIMIT`) hits the
reversal and flips `dx` positive — the scan ramps *up* correctly. The
`>= 0` variant produced a two-tick oscillation pinned at the bottom-left
corner. `resetScanCounters()` therefore *must* zero `dx,dy` before
`updateStepSizes()`.

`samplesPerPixel` is clamped to ≤ 4000 because the per-pixel accumulator
`zAvg` is `int32`: `4000 × MAX_Z_POS (524287) ≈ 2.1e9 < 2^31`.

### 2.5 Ping-pong line buffers

```cpp
uint8_t data1[16386], data2[16386];      // 2 + 8·MAX_PIXELS_PER_LINE
volatile bool fillData1, sendData;
volatile uint16_t pendingLineNumber;
```

The ISR fills one buffer; when a line completes it stamps the line number
into the header, flips `fillData1`, latches `pendingLineNumber`, and sets
`sendData`. `loop()`'s `emitPendingLine()` reads the *other* buffer and
streams it. The ISR never blocks on USB; `loop()` never sees a torn line.

Timing margin at defaults (40 µs, 512 ppl, spp≈48): line period ≈ 983 ms,
serial emit of ~4.1 kB at 921600 baud ≈ 45 ms → ~20× headroom. Line loss
only becomes possible at sub-100-µs line periods, far outside the
realistic envelope.

### 2.6 SPI arbitration

The ISR owns SPI1 (ADC) and SPI0 (DACs) during normal scanning. Any
main-thread operation that also needs the bus must not be preempted:

- **Short writes** (`set_dac_*`, `set_dac_bias`): wrapped in
  `noInterrupts()/interrupts()`.
- **Long operations** (`start_scan`, all spectroscopy, `approach`,
  `test_piezo`, `ADCR`, lock-in): set `blockISRControl = true` for their
  duration. `controlTick()`'s first line is the cooperative yield. On
  exit they restore the prior flag and, where relevant, call `_syncZPos()`
  so the ISR resumes from the correct Z.

`ADCR` racing the ISR on SPI1 was a concurrency bug found in review and
fixed by wrapping its handler in the `blockISRControl` save/restore.

### 2.7 Bumpless transfer

Switching Z authority between the legacy 16-bit DAC-code controller and
the ISR's 20-bit integer PI must not jerk the tip. `engage()` and
`turn_on_const_current()` preload the integral term from the current DAC
code:

```cpp
int z_sync = (int)(((int64_t)stm_status.dac_z - 32768) << 4); // 16→20-bit
z_pos      = z_sync;
iTermISR   = (int64_t)z_sync << 32;     // Q32: first PI tick reproduces Z
```

`engage()` additionally **refuses if `setpointLog == 0`** (no setpoint
programmed) — without it, a zero setpoint drives the integrator full-tilt
until the tip retracts to its stop. This is a safety interlock, surfaced
in the UI as the realistic-default-setpoint rule.

### 2.8 ADC saturation compensation

The LTC2326-16 reads `0x0000` when its input clips. Treating that as
"zero current" would make the loop drive the tip *into* the sample. So:

```cpp
if (pidEnabled && adc_val == 0 && z_pos != -MAX_Z_POS) adc_val = 32767;
```

Gated on `pidEnabled` (review fix): when not engaged, `adc == 0` is
legitimately "no tunnelling", and forcing 32767 would pollute the error
image with synthetic saturation.

### 2.9 Wire formats

Hybrid protocol — ASCII for control and all legacy back-compat paths,
binary for high-throughput streaming:

- **`'L'` frame** (continuous scan line): `0x4C`, uint16 line#, uint16
  pixels, `int32 z[N]` big-endian, `int32 err[N]` big-endian, `0x0A`.
  `5 + 8N + 1` bytes. Pixels are packed big-endian *in the buffer* by
  `writePixel()` so emission is a single `Serial.write(buf+2, 8N)`.
- **`'M'` frame** (lock-in dI/dV point): `0x4D`, uint16 idx, int32 bias,
  int32 in-phase, int32 quadrature, `0x0A`. 16 bytes.

Big-endian was chosen to match Dan's convention and because `writePixel`
packs MSB-first directly, avoiding any per-emit byte-swap.

**Old-firmware fingerprint (`STAT:` prefix).** The pre-Phase-3 firmware
(commit `e077127` era) prefixes its GSTS reply with `STAT:`
(`STAT:0,0,0,0,-37,…`); the current firmware prints the bare CSV. This is
undocumented on the wire but load-bearing: that old build has **no `RUN `
handler and no binary `'L'` frames** (its `start_continuous_scan()` took
`x_start/x_end/…` arguments on a different command), so a board still
flashed with it accepts GSTS/legacy commands normally while silently
ignoring `RUN ` — the Continuous Scan tab stays blank with no error.
Verified by probing a live board on COM5 (2026-07-02): GSTS answered with
the `STAT:` tag, `RUN ` streamed 0 bytes in 5 s. The PC side now records
the tag (`STM.firmware_tagged_status`), refuses RUN with an explanatory
status message when it was seen, and independently warns if no `'L'`
frame arrives within 3 s of RUN. Remedy: reflash
`teensy/arduinosrc/main`.

### 2.10 Hardware delta vs Dan

Dan drives one DAC8814 (shared CS, daisy-chained). qt-panda has 4× AD5761
(SPI0, mode 2, 40 MHz, 3-byte command frame, **independent CS per
channel**). The only cost is per-channel CS toggling inside the ISR — a
small constant (a few hundred ns) versus Dan's single shared transaction.
At 600 MHz with a 40 µs budget and measured ISR runtime well under 20 µs,
this is immaterial. No hardware change was in scope or required.

---

## 3. PC software

### 3.1 Threading model

USB-Serial is read on a dedicated `QThread` so the GUI never blocks:

```
SerialReaderThread.run()  [worker thread]
   read 1 byte → 0x4C? parse 'L' frame  → lineFrame  signal
                 0x4D? parse 'M' frame  → lockInPoint signal
                 else  read to '\n'     → asciiLine   signal
        │
        ▼ (Qt queued connection — auto-marshals to main thread)
ScanController  [main thread]  → re-emits as lineReady / zUpdated / …
        │
        ▼
LiveRaster.update_line / Z gauge / status   [main thread]
```

Qt's default cross-thread `connect` is a *queued* connection: signal
arguments are copied into the receiving thread's event loop, so numpy
buffers are only ever touched by the main thread. No locks needed.

### 3.2 The reader-vs-synchronous-read hazard

The legacy `STM.get_status()` does a synchronous `send('GSTS')` +
`readline()`. While `SerialReaderThread` is running it consumes *all*
inbound bytes, so a concurrent `readline()` would hang for the full 1 s
pyserial timeout — on a 100 ms QTimer, that freezes the UI.

Resolution: `update_real_time()` early-returns when
`self._scan_ctrl.is_running()`. During continuous scan, status flows
instead from the binary frames and the `asciiLine` passthrough. The
reader thread is also cleanly stopped/joined on `HALT` and before any
restart (no two-readers-one-port race).

### 3.3 ScanController — translation + unit conversion

`ScanController` is the single chokepoint between UI intent and firmware
commands. UI slots take **physical units**; conversion to LSB happens here
against the shared `Calibration`:

```python
# XY span/offset (a delta — no 32768 midpoint offset)
lsb = round( nm / piezo_x_nm_per_v / dac_x_v_per_lsb )
# setpoint
lsb = round( pA·1e-12 · preamp_v_per_a / adc_v_per_lsb )
# line rate → firmware LRAT integer in 0.01-Hz units
LRAT = round(hz · 100)
```

`zUpdated` maps the 20-bit `z_pos` from each line back to a 16-bit DAC
code (`(z_pos >> 4) + 32768`, clamped) to drive the Z-piezo gauge with a
value the operator can reason about.

### 3.4 LiveRaster rendering

Four independent buffers (`z_trace`, `z_retrace`, `e_trace`,
`e_retrace`) — the firmware sends `pixelsPerLine = imagePixels·2`
(forward then reverse, the reverse already order-flipped in firmware, so
the PC un-reverses with `[half:2·half][::-1]`).

Two `pg.HistogramLUTItem`s (the same widget `plotframe.py` uses for legacy
images — deliberate reuse). One binds to the trace image; its
`sigLevelsChanged`/`sigLookupTableChanged` mirror levels + LUT onto the
retrace twin so both halves share a colour scale automatically.

Right-click on a Z image maps scene→view→pixel→fraction-of-scan→nm and
emits `scanOffsetRequested`; the widget writes the offset spinboxes and
re-sends, recentring the scan in one gesture.

### 3.5 Calibration model

`Calibration(QObject)` is the single source of truth; `calibration.json`
is *only* persistence. `set_field()`/`reset_defaults()` emit `changed`,
which the widget connects so every physical-unit display refreshes live.
`from_json()` loads at startup, `to_json()` is the only disk-write path
(Save button). The constants span ~1e-4 … 1e8, so the editor uses
validated free-text fields, not spin boxes.

---

## 4. Concurrency & safety summary

| Boundary | Mechanism |
|---|---|
| ISR ↔ main-thread SPI | `noInterrupts()` (short) / `blockISRControl` (long) |
| ISR ↔ main 64-bit `iTermISR` | all main-side access inside `noInterrupts()` |
| Ping-pong buffer | `fillData1` flip + latched `pendingLineNumber` |
| Reader thread ↔ GUI | Qt queued signals (arg copy, single-writer buffers) |
| Reader vs synchronous readline | poll suppressed while scan running |
| Reader restart | stop + `wait()` + signal-disconnect before replace |
| Tip-crash interlocks | bumpless transfer; `ENGA` setpoint refusal; Z gauge |

Numeric safety, verified by analysis: `zAvg` int32 (spp ≤ 4000),
`iTermISR` int64 (±MAX_Z_POS·2^32 ≪ 2^63), `dx` fits signed int for
`pixelsPerLine ≥ 2`, sign-preserving Q32 cast.

---

## 5. Design decisions & trade-offs

- **Parallel-and-frozen fork.** v1 (`pc/`, `teensy/`) is untouched;
  the port evolves in `dans-software-port/`. Lets the instrument keep
  working on v1 while the rewrite is validated; cutover is a separate,
  later decision.
- **Hybrid protocol, not all-binary.** Keeping ASCII for control + all
  legacy commands means the existing spectroscopy/scan code and parsers
  work unchanged; only the throughput-critical line stream is binary.
- **Physical units in the new UI only.** The continuous-scan and
  calibration tabs are operator-grade (nm/pA/Hz); legacy tabs stay in LSB
  to remain bit-identical to v1 behaviour and avoid reworking validated
  code.
- **Reuse over reinvention.** Histogram LUT, click-on-image handling, and
  unit-conversion patterns were lifted from existing `plotframe.py` /
  widget code rather than rebuilt.
- **Hybrid UI construction.** Legacy layout stays Qt-Designer-generated
  (`form.ui` → `ui_form.py`); only the two new tabs are hand-built in
  `widget.py`. The project is *not* fully decoupled from Qt Designer and
  `ui_form.py` remains load-bearing.

### Known limitations (documented, not bugs)

- `Ki` is not `dt`-independent: `Ki_isr` scales by 65536, not by
  `control_dt_us`, so changing `SETD` shifts loop response. Default
  `Ki = 4.5776` is calibrated for `dt = 40 µs`.
- Mid-scan `IPLN/SCSZ/LRAT` changes glitch exactly one line.
- Legacy scan/spectroscopy while a continuous scan is RUNning races the
  port; the UI does not yet auto-`HALT` (operator must stop first).
- Lock-in dI/dV firmware (`'M'` frame) is complete but has no UI consumer
  yet (deferred in `SMOKE_TEST.md`).
- All timing/feedback numbers are analysis- and emulation-validated only;
  picometre-level behaviour requires the bench (see `SMOKE_TEST.md`).

---

## 6. File map

| File | Role |
|---|---|
| `teensy/.../main.ino` | 4-char command dispatcher, `loop()`, ISR shim |
| `teensy/.../stm_firmware.hpp` | `STM` class: ISR, PI, scan, legacy paths |
| `teensy/.../sigma_delta.hpp` | dither modulator |
| `teensy/.../line_buffer.hpp` | ping-pong buffers, `writePixel` |
| `teensy/.../binary_frame.hpp` | `'L'`/`'M'` emitters |
| `pc/qtpanda/widget.py` | UI; legacy (Qt-Designer) + new tabs (code) |
| `pc/qtpanda/scan_controller.py` | unit conversion + command translation |
| `pc/qtpanda/serial_reader.py` | `QThread` hybrid parser |
| `pc/qtpanda/live_raster.py` | 2×2 live imaging, histograms, pan |
| `pc/qtpanda/calibration.py` | calibration model + JSON persistence |
| `pc/qtpanda/stm_control.py` | `STM` command sender + ASCII parsers |
| `pc/qtpanda/ui_form.py` | generated legacy UI (load-bearing) |
