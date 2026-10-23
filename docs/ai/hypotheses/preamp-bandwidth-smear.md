# Hypothesis: horizontal streaks are bandwidth smear, not bad pixels

**Status:** the *smear* is established; blaming the *preamp* specifically is NOT

> **Correction 2026-09-18 (same day).** This document attributes the time
> constant to the preamp throughout. That attribution is not established —
> the piezo drive chain and mechanical settling fit every measurement equally
> well, and the drive chain had not even been considered when this was
> written. Read "preamp" below as "**something in the chain with a ~400 µs
> time constant**". See `time-artifacts-piezo-vs-preamp.md` for the candidate
> list, the evidence that rules out hysteresis and post-processing, and the
> experiment that would decide it.
**Raised:** 2026-09-18, from the 2026-Sep-17 bench data
**Data:** `TeamUpdate/data/2026-Sep-17/scan_1789688023145_s1789684257556.frames`,
26 sweeps at 32.98 nm / 128 px per direction (day-global sweeps #70–98)

---

## The observation

Operator, watching the replay: a single pixel looks smeared roughly 10% of the
image width, ending abruptly, with the rows directly above and below unaffected.

> "one row of pixels in the middle is so bright, with no bleeding directly above
> and below it. It's always in the horizontal direction, never vertical, and
> never diagonal."

The "never vertical, never diagonal" part is the diagnostic clue.

## The claim

The streaks are **not** bad pixels, not an ADC fault, and not a rendering
artifact. They are the current preamplifier's finite bandwidth: the tip sweeps
across X faster than the preamp can follow, so each reported pixel is a lagged,
smeared average of the current over the preceding few hundred microseconds.

In a raster, **at the line timescale the vertical axis is time.** Two pixels
side by side are 80 µs apart; two pixels stacked vertically are 20.5 ms apart —
the same 0.258 nm of sample, 256× further apart in time. Anything whose
correlation time falls between those two numbers paints horizontal streaks and
*cannot* paint vertical or diagonal ones. A vertical stripe would require a
disturbance locked to X *position*; a diagonal would require a narrowband tone
drifting in phase against the line rate.

## Evidence

### 1. The anisotropy is large and matches the prediction

Adjacent-pixel correlation, median over 26 sweeps, `e_trace`:

| direction | r |
|---|---|
| along a row (80 µs apart) | **+0.91** |
| across rows (20.5 ms apart) | **+0.39** |
| diagonal | +0.38 |

Diagonal equals vertical — no preferred diagonal, exactly as reported.

### 2. Same spatial separation isolates the temporal component

Along-row and across-row pairs at equal pixel offset span **identical sample
distance** but wildly different elapsed time. The difference is therefore purely
temporal — i.e. noise:

| offset | spatial | Δt along | Δt across | r along | r across | noise |
|---|---|---|---|---|---|---|
| 1 px | 0.26 nm | 80 µs | 20.5 ms | +0.91 | +0.39 | +0.52 |
| 2 px | 0.52 nm | 160 µs | 41 ms | +0.86 | +0.44 | +0.42 |
| 4 px | 1.03 nm | 320 µs | 82 ms | +0.78 | +0.42 | +0.36 |
| 8 px | 2.06 nm | 640 µs | 164 ms | +0.55 | +0.30 | +0.25 |
| 16 px | 4.13 nm | 1.28 ms | 328 ms | +0.17 | +0.13 | +0.04 |

The noise column dies out by ~1.3 ms; half-correlation at **7.6 px = 611 µs**.
That length — 8 to 13 px — *is* the streak the operator sees. The streak length
is the instrument's correlation time drawn in pixels.

### 3. The bright rows are not anomalies

In sweep #77, **no row is more than 3σ from its neighbours** (most extreme
+1.49σ). Rows look like discrete stripes because they are internally smooth
(r = 0.91) while being weakly tied to each other (r = 0.39), not because any
individual row is defective.

### 4. The lag is direction-dependent — the decisive test

A causal filter delays the signal *in the direction of travel*. Trace runs
left→right and retrace right→left, so the same feature must appear displaced in
opposite directions, separated by twice the lag.

Measured over 3,328 line pairs, applying **one global shift** to every line of
every sweep — a single free parameter, so no overfitting:

| global lag | median r |
|---|---|
| +4 px | +0.189 |
| 0 px | **+0.269** |
| −4 px | +0.345 |
| −8 px | +0.387 |
| **−10 px** | **+0.402** |
| −14 px | +0.384 |

A clear, broad, monotonic peak. Implied one-way delay
**τ ≈ 5 px = 400 µs = 1.29 nm of tip travel**, determined to about ±1 px.

(Fitting a *separate* best lag per line reaches r = 0.630, but that figure is
inflated by selection — 3,328 free parameters. The honest number is the global
one: **+0.269 → +0.402**.)

This is the signature of a lag, and nothing else produces it: sample noise,
vibration and drift are all direction-independent.

`raw_scan_reconstruct.py` already names this quantity in its docstring — "best
lag = measured system delay (preamp RC + piezo response) in samples and nm" —
so the concept predates this hypothesis; what is new is measuring it from the
frames and tying it to the visible streaks.

## Numbers

- Line rate 48.8 Hz → one line 20.5 ms; 128 px per direction → 80 µs per pixel
- Tip speed across the sample: 32.98 nm in ~10.25 ms = **3.22 nm/ms**
- Measured one-way delay τ ≈ 400 µs → spatial smear = 3.22 × 0.40 ≈ **1.29 nm**
- Rendered pixel size 0.258 nm → **oversampled ~5× relative to true resolution**
- τ = 400 µs implies a corner near 1/(2πτ) ≈ **400 Hz**

Note the corner estimated from the noise correlation half-length (611 µs) lands
lower, in the 180–800 Hz range depending on the assumed filter shape. The two
estimates bracket each other but do not agree precisely, which is expected if
more than one pole contributes (preamp RC *plus* piezo mechanical response).

**Capacitance is deliberately left open here** — see *Outstanding test*.

## What this predicts

1. Trace/retrace registration improves by a fixed shift, independent of scan
   size, and the shift in **pixels** scales with pixel rate while the shift in
   **nanometres** scales with tip speed. Testable by repeating at a different
   line rate: τ in seconds should stay constant.
2. Slowing the scan reduces the smear in nm proportionally.
3. Raising pixels-per-line without slowing the line rate buys nothing — the
   extra pixels are not independent measurements.

## Outstanding test (the one that would settle it)

Inject a **known square-wave current** at the preamp input and measure the rise
time at the ADC. That pins the corner frequency directly instead of inferring
it from correlation lengths, and separates the electrical pole from the piezo's
mechanical one. Only then is it worth back-solving stray capacitance from
`f = 1/(2π R C)` with R = 100 MΩ (`preamp_v_per_a = 1e8`) — a corner anywhere
in 180–800 Hz implies roughly 2–9 pF, which is too wide a range to act on.

*(Operator 2026-09-18: picofarads to be revisited later — deferred deliberately,
not forgotten.)*

## Consequences for existing data

- The smear is a **convolution**, so it is recoverable in principle (see
  `stretch-compensation.md`).
- Where the current **railed**, the error signal clipped at a constant
  (−233257 = `logTable[320] − logTable[32767]`) and that information is
  destroyed — no amount of processing recovers it. ~19% of this window.
- Effective resolution on 2026-Sep-17 was ~1.3 nm, not the 0.258 nm the pixel
  grid implies. Any feature claimed below ~1 nm from that day is suspect.

## Related

- `stretch-compensation.md` — can the smear be undone?
- Day write-up: `TeamUpdate/data/2026-Sep-17/SCAN-NOTES-2026-09-17.md`
- The setpoint bug found alongside this (CCON sent un-gain-corrected, 320
  instead of 1600) is a separate defect; it does not cause the smear but it
  guaranteed the loop could not recover from saturation.
