# HY1: fast-axis (X) hysteresis from existing recordings (2026-10-23)

**Question.** The scan simulator assumes Prandtl–Ishlinskii hysteresis with `hyst_frac = 0.05` (PHYSICS_MODELS.md §5, DECISIONS.md A3). The parent session expected the real value to be much smaller, based on "Sep 24 #932: trace vs retrace 0 ± 1 px at constant height". Measure it from existing data.

**Short answer.** The existing data **do not pin the value down**. The direct, lag-free evidence (constant-height frames) points to a mid-line trace/retrace separation of roughly **3% of the line width (range 0–6%)**. That is about what `hyst_frac = 0.05` produces (2.8%). **The "0 ± 1 px" reading of #932 is a whole-line average that hides a mid-line separation of several percent, so it does not show that hysteresis is small.** Recommendation: keep 0.05 as the central value, run sensitivity at 0.01 and 0.12, and get a dedicated bench measurement (below).

Scripts:
- `hy1.py` measures every full sweep on Sep 17, Sep 24, Oct 8 and Oct 22 (2,458 sweeps) → `hy1_sweeps.json`.
- `hy1_report.py` produces the figure and summary → `hy1_profiles.png`, `hy1_results.json`.

## Method

1. **Feedback state per sweep** comes from the 200 Hz status CSV: the share of samples with `is_const_current = 1` during the sweep. Constant height (CH) is < 5%, constant current (CC) is > 95%. Result: 553 CH sweeps, 1,895 CC.
2. **Trace vs retrace shift as a function of X:**
   - Each line is split into segments (8; 3–4 for CH).
   - The line-locked mean profile is removed first. It is the lag pattern, which carries 78–98% of the variance (Oct 15 report), and without removing it the correlation locks onto it.
   - Each segment's rows are detrended and lightly smoothed (σ = 1 px).
   - The cross-correlation is summed over rows; the peak is found with sub-pixel interpolation.
   - Peaks at the search limit are rejected.
3. **Fit:** shift(u) = a + b·u + c·4u(1−u), where a is a constant shift (delay or lag), b is linear (scale mismatch) and c is a dome.
   - **Correction found along the way:** the simulator's PI model gives a **flat** separation along a full-span line, not a dome (`hy1_profiles.png`, right). So the right quantity to compare is the **total mid-line separation**, not c alone.

## Findings

1. **Constant-height sweeps rarely carry matchable morphology.** The median segment correlation is 0.04, because a fixed-Z current image is mostly lost or clipped current. Only Sep 24 **#931 and #932** (30 nm, 128 px per direction, ~8 ms lines) match well at whole-line scale: correlation 0.83 and 0.80.
2. **Their whole-line shift is ~0 px (#931: 0, #932: −1), which is where the "0 ± 1 px" came from. Along the line it is not flat:**

   | Frame | Segments | Shift by position (% of line width) | Correlation |
   |---|---|---|---|
   | #931 | 4 | +0.2, −0.3, −0.1, −0.1 | 0.19–0.57 |
   | #931 | 3 | +1.6, −3.2, +0.1 | 0.31–0.60 |
   | #932 | 4 | −1.7, **−6.0**, −0.3, −0.9 | 0.30–0.53 |
   | #932 | 3 | −1.9, −2.6, −0.2 | 0.33–0.53 |

   The mid-line separation is about −3% ± 2.5% (noisy, two frames). There is no loop in these frames, so this is position error: hysteresis plus any constant delay, the delay being small at 8 ms lines and 30 µs per pixel.
3. **Constant-current error channel (30 nm, 256 px):** a dome with ~−1% at the turnarounds and −3 to −5% mid-line.
   - Sep 24 #1572–#1586 at 31 ms lines: c = −9.8 px = −3.8%, n = 5.
   - Oct 22 #12/#23/#27 at 97 ms lines: c = −5.6 px = −2.2%, n = 3.

   It is larger at the faster line rate and is out of the ±16 px search at 5–20 ms lines. So most of it is **time delay / loop lag** (speed-dependent), consistent with the Sep 17 ~400 µs constant (roadmap CN5), and not a clean hysteresis measure. What remains at the slowest rate (2.2%) is an upper bound on hysteresis for that day.
4. **Constant-current Z channel:** a **flat −6.8% to −7.0% offset** at 128 px per direction, the same in pixels at 8.9 nm with 7.6 ms lines (n = 50) and at 33 nm with 20–21 ms lines (n = 10). It scales with neither speed nor scan size. That rules out a time delay. It could be hysteresis (a fraction of span, flat, like the PI model) or a **pixel-indexing effect in the firmware** that ran that day. The good-tip run's session has no `VERS` record: Sep 24 morning sessions reported FW 5.3, then 5.6, and FW < 5.6 truncated the X step. **Unresolved; see next steps.** The dome part in Z is ~0 (n = 50: c = −0.12 px).
5. **Size dependence:** not determinable. No scan size has enough clean frames in both feedback states.

## Recommendation for `scan_sim.PHYS`

- **`hyst_frac = 0.05` stays as the central value.** It gives a 2.8% mid-line separation, against about 3% ± 2.5% measured at constant height. It is not shown to be too large; the earlier "probably too large" (DECISIONS.md A3) is not supported.
- **Sensitivity runs:** 0.01 (0.6% separation) and 0.12 (~7%, if the flat CC-Z offset is real hysteresis).
- The model's shape is unverified: real piezo loops are usually curved (dome), while the PI model with small widths is flat. A Preisach-style curvature option may be needed once data exist.

## Next steps to settle it (bench, short)

1. **Constant-height hysteresis scans with tunnelling morphology everywhere:**
   - fixed Z near a flat terrace, setpoint-level current, so the current stays in range;
   - slow lines (≥ 100 ms), to make any delay negligible;
   - three scan sizes (10, 30, 60 nm);
   - both channels saved, ≥ 10 frames each.

   Measure the separation profile per size.
2. **Check the flat CC-Z offset against the firmware:** run the same settings on FW 5.6 with a `VERS` record, and compare the bit-exact pixel map (`scan_paths.py`) with what the frames show.
3. **Measure the delay separately** (CN5 preamp f3dB), so the speed-dependent part can be subtracted from constant-current data.

## Caveats

- Two usable constant-height frames: the central value is uncertain by a factor of ~2.
- Segment cross-correlation on images dominated by lag patterns is fragile. Values at the search limit were rejected, but the remaining CC error-channel profiles still mix lag with position error.
- The firmware version for the Sep 24 good-tip run is not recorded.
