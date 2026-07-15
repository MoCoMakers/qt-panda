# CHANGELOG — hard-won learnings

Not a release log — a record of the **big aha's and non-obvious fixes** so
the next person (or LLM) doesn't re-derive them the hard way. Newest first.

## 2026-07-15 — the marathon session

### The defining bug: continuous scans swept 1/16 the commanded area
`scan_controller._nm_to_xy_lsb_span` converted nm → **16-bit DAC LSB**, but
the firmware's scan positions live in **20-bit sigma-delta space** (position
unit = DAC LSB × 16). So every continuous scan physically covered **1/16**
of what was asked — a "30 nm" scan was really ~1.9 nm, a featureless patch,
which is why continuous scans showed only noise stripes while the legacy
engine (which drives DACs directly in 16-bit units) found real morphology.
Fix: ×16 in the nm→units conversion. **This was the root cause behind weeks
of "continuous can't reproduce the legacy image."**

### The continuous Y geometry: fold, don't flip
`dy = dx / pixelsPerLine`, so **one line-counter cycle (2·H lines) is a full
Y up-AND-down triangle**: lines `0..H-1` ascend, `H..2H-1` descend back over
the *same* rows. The display/replay must **fold** the descending half onto
the ascending rows. An earlier "flip alternate frames" model was wrong and
painted every feature twice, mirrored — producing a fake breathing
"accordion" that looked like piezo hysteresis. True Y hysteresis is ~1 row.
Frame geometry: image is `(px/2)×(px/2)`; Dan's 512-px default → 256×256.

### The Err channel was rendering morphology *inverted*
Constant-height display used the firmware's **log-error** channel
(`log|I| − log setpoint`), which shows real structure with inverted,
log-compressed contrast (correlation −0.99 vs. ground truth in simulation).
Linearizing it back to current (through the firmware's exact log table)
restores a pixel-perfect match (+1.00). Display now linearizes in
constant-height mode and shows raw feedback-error only when CC is engaged.

### Feedback sign was inverted → constant-current was a plunge machine
The ISR integer-PI error term was `measured − setpoint`; the proven legacy
convention is `setpoint − measured`. The flip made constant-current
**positive feedback**: engaging CC in contact railed Z to full extension and
drove the tip into the sample (~950 motor steps of stored elastic strain
that kept re-pressing for minutes). Fixed in firmware (FW 5.2). Feedback-
armed approach (engage CC + single motor steps) is now the safe approach.

### Z direction: high DAC = toward the sample
The firmware approach sweeps the Z DAC **upward** to find the surface, so
**higher DAC = smaller gap = more current**. The Z slider was first labeled
backwards (called the crash direction "Retracted"). Corrected labels
(▲ Away / ▼ Toward sample) and inverted the slider so **down = toward the
sample**, matching intuition and the hardware.

### Every pixel must be reconstructible from disk
The most-trusted images (legacy scans) were the *only* data never saved —
parsed, drawn, and discarded. General principle now enforced: **log the raw
stream verbatim at the parse choke point, before rendering, with per-record
flushing**, plus a sidecar of all machine state (geometry, bias, Z, current,
gain) needed to reproduce the view. Added `scst_logger` (legacy),
`frame_logger` (continuous), `status_logger` (200 Hz true-time thread),
`raw_logger` (25 kHz). Never screenshot as a substitute for recording.

### Recording is an independent service, not a viewer feature
Recording is tied to the **serial port being open**, not to any tab. The
Stability tab is a *consumer* of the same feed, manually triggered. Writes
happen on a dedicated thread fed from the serial reader, so GUI load,
rendering, or a hung event loop can't stall or lose data. Timestamps are the
firmware clock, so gaps never distort time.

### One firmware state, faithfully mirrored everywhere
Widgets used to show "what I last typed," not what the hardware actually is —
so a stale on-screen bias got fired at the DAC (a plunge setup), and the Z
spinbox read 32768 while real Z was 53150. Now the firmware status stream is
the single source of truth; every DAC/bias widget mirrors it live (backing
off only while the operator is actively editing).

### Single reader per serial port
Two `SerialReaderThread`s on one port race `read()` and corrupt both streams
(a dual-reader race once froze the GUI at 19 GB from a runaway allocation off
a garbage frame header). Scans hand the port between readers; the recorder
re-arms after. Reader has desync guards (reject impossible frame sizes).

### Preamp gain is an operator setting, not a magic number
`adc_to_amp` multiplies by a **preamp-gain** class attribute set from a GUI
dropdown (1X / 5X), persisted. At 5X the same current gives 5× the counts and
the ADC rails at ~20 nA instead of ~102 nA. A wrong gain silently 5×-scales
every reported current.

### Bench realities that masked software (worth ruling out first)
- A **missing grounding clip** turned the rig into an antenna: ±65 nA
  bipolar telegraph noise, mains-locked vertical streaks. Reattaching it
  dropped peak disturbance ~2000×. Check the ground before blaming code.
- **Blunt/crashed tips** convolve away everything below ~10–20 nm and give
  bistable snap-in contact (no stable open-loop gap). A sharp tip is the real
  resolution upgrade; software only manages around a bad one.
- **5–10 Hz floor/building vibration** dominates the current spectrum and
  paints jittery horizontal texture — feedback (constant current) absorbs it
  into Z; averaging (Samples/px) does not (wrong timescale).
- Horizontal "distortion" in raster images is usually **line-to-line
  baseline drift** (1/f), fixed by Gwyddion's *Align Rows*, not an X-axis
  problem.

### Operational
- **Graceful-quit the app; never force-kill** — a hard kill mid-transmission
  wedges the Teensy USB serial (spews `0x7f`, clock frozen). Recovery: a
  firmware **reflash reboots it** without touching the board.
- Firmware command framing is fragile (4-char, no terminator/checksum); a
  garbage serial burst can be misparsed as a command. Magnitude sanity limits
  on MTMV are a pending firmware hardening.
- The **research harness** models beat guessing: it correctly showed preamp
  bandwidth alone doesn't erase morphology at the tested scan size, redirecting
  the hunt to the real (16×) bug.
