"""Docs: tick epochs across resets, line-number slip, sidecar spp bug, back-test findings."""
TP = "C:/Users/enact/Projects/qt-panda/docs/test-plans"
s = ""


def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:70])
    s = s.replace(a, b)


p = TP + "/scan-path-design.md"; s = open(p, encoding="utf-8").read()
rep("## 8 · Physics between the DAC and the image", """### 7.1 Time base across resets (operator, 2026-10-23)

The microcontroller's tick count is the gold standard. The PC clock is only a reference. The Teensy is reset or power-cycled often during live runs, so:
- **Free-running counter.** The tick counter counts from boot and is never reset by RUN. Every line frame and status record carries the tick count and a **boot ID** (random at boot, from the hardware RNG).
- **Epochs on the PC.** Each boot is an epoch. Within it, the PC fits PC time = a + b·tick, robustly over many frames, and unwraps 32-bit wraps (every 11.9 h at 100 kHz). A new boot ID, or a tick going backwards, starts a new epoch. Recordings never mix epochs silently.
- **PC jitter is real.** On Oct 22 the *median* PC gap between line frames was 91–94 ms while the *mean* was 97.5 ms, which matches 512 px × 19 ticks × 10 µs. PC receive times are batched, so they are not a time base.

### 7.2 Findings from the bit-exact port (2026-10-23)

1. **Line-number slip (R19, now concrete).** At the end of each Y-cycle the resync resets the line counter one tick *before* the last line is stamped:
   - The first frame after RUN is stamped 0…510 and then 0 again.
   - Every later frame stamps true line L as L+1 (mod lines).

   Confirmed in the Oct 22 recording: …509, 510, **0**, 1… in the first cycle, then …510, 511, 0… every cycle after. The replay places rows by stamped number, so **every up/down pair carries a hidden 2-row offset** (about 0.23 nm at 30 nm), opposite in up and down sweeps. That is part of the 8.4 px "hysteresis" offset.
   - **Fixes:**
     - Tick stamps (segment = tick ÷ (spp × bins)) make the index exact.
     - A firmware fix moves the resync to the line boundary.
     - For legacy files, a PC correction rule (first cycle: the second 0 is line 511; afterwards stamped − 1) can be applied, but only with the operator's agreement, since it shifts every historical image by one row.
2. **The sidecar records the wrong samples-per-pixel.** Oct 22 says `derived_samples_per_pixel: 4`, but the firmware used 19: the GUI derives it assuming the old 25 kHz ISR. This is exactly the orphan-frame risk. The `scan_path` block stores the spec the firmware actually ran (and, with F8, the firmware echoes it).

""")
rep("## 9 · Simulation before firmware", """## 8.1 Back-test against the good-tip day (2026-10-23)

The simulator (`analysis/sim/scan_sim.py`) imaged the Sep 24 truth with today's raster at Sep 24's settings (512 px, 3 ticks/px, KIGA 1.144, 1000 pA). Line-levelled Z statistics were then compared with the real sweeps #1586–#1599 (`backtest_sep24.py`, `backtest_diag.py`).

| | Real Sep 24 | Simulator (best variants) |
|---|---|---|
| Lag share | 0.95 (0.83–0.97) | 0.6–0.89 |
| Trace/retrace correlation | −0.91 | −0.2 to −0.81 |
| Lag part L rms / line-locked share | 110 units / 70% | 8–16 units / 21–28% |
| Raw Z span (tilt) | 58,600 | 51,500 |

- **Reproduced:** tilt and raw span. **Not reproduced:** the dominant real artefact.
- **The artefact:** a smooth, symmetric, scan-synchronous **dome in (trace − retrace)**, 190–800 units peak-to-peak and 99% cubic. It persists on sweeps with ~zero X slope.
- **Ruled out:**
  - tilt × hysteresis (X slope 0–1.4 units/px is far too small);
  - loop lag (wrong symmetry);
  - 158.7 Hz ringing (no ringing in the profile);
  - direction-flipping pickup: the no-current ADC offset is −53 on trace vs −52 on retrace (`phantom_direction.py`), so the OI-3 offset does not flip with scan direction.
- **Status:** an open physical question (new item: OI-18 in the plan). Until it's explained, simulated image fidelity is *relative, under the modelled physics*, and understates what cross-hatch pairs can remove. Kinematic scores (coverage, drive energy near 158.7 Hz, acceleration, bit-exact reconstruction, drift recovery) do not depend on it.
- **Stated assumptions:**
  - Z is uncalibrated: the placeholder calibration implies ~6 Å rms for the plane-levelled Sep 24 map. The truth is rescaled to 1 Å rms (sensitivity runs at 0.3 Å and at calibration ×0.3 / ×1 / ×3).
  - Hysteresis: Prandtl–Ishlinskii, 5% of span.
  - Resonance damping ζ = 0.05; amplifier 3 kHz.
  - Z drift 0.39 Å/s (39 codes/s × placeholder calibration).

## 9 · Simulation before firmware""")
open(p, "w", encoding="utf-8").write(s)

p = TP + "/2026-10-23-open-issues-and-tests.md"; s = open(p, encoding="utf-8").read()
rep("### OI-15 · Getting 3D intentionally", """### OI-18 · A scan-synchronous trace/retrace dome in Z · `open` (found 2026-10-23)
On the good-tip day (Sep 24 #1586–#1599) the line-levelled lag part of Z, L = (trace − retrace)/2, is dominated by a smooth symmetric dome:
- 190–800 Z units peak-to-peak, the same on every line (70% line-locked);
- present even where the X slope is ~0.

The scan simulator cannot reproduce it. Ruled out: tilt × hysteresis, loop lag, 158.7 Hz ringing, and direction-flipping pickup (the no-current offset is −53 trace vs −52 retrace).

Candidates to test:
- (a) X–Z coupling of the scanner tube, acting through its own hysteresis;
- (b) a position-dependent electrical pickup into Z or the current;
- (c) creep after each turnaround;
- (d) the 2-row line-number slip mixing neighbouring lines (check first: re-run with the corrected line index).

Tests:
- a non-tunnelling scan (T2), which shows any pure electrical part;
- the dome versus scan size and line rate;
- the same scan rotated 90° (scan paths, OI-17).

Scripts: `analysis/sim/backtest_diag.py`, `phantom_direction.py`.

### OI-15 · Getting 3D intentionally""")
rep("9. **Tooling lessons:**", """9. **Determinism findings:**
   - The line-number slip gives a hidden 2-row up/down offset in all recordings (R19, scan-path-design 7.2).
   - The sidecar's `derived_samples_per_pixel` is wrong at 100 kHz.
   - PC frame times are batched (median 91 vs mean 97.5 ms).
   - Ticks are the gold time base, kept as free-running epochs across resets.
10. **Back-test:** the simulator reproduces tilt but not the real scan-synchronous trace/retrace dome (OI-18). The OI-3 offset does not flip with scan direction, which rules out simple X-drive pickup.
11. **Tooling lessons:**""")
open(p, "w", encoding="utf-8").write(s)
print("ok")
