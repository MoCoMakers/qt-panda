# Scan simulation and reconstruction (living)

**What this is.** How we simulate the instrument imaging a known surface, tick by tick, and how we rebuild the image. It covers how we verified that the rebuild is right, and what the results mean for scan paths and for the real rig. Physics models and their status are in [`PHYSICS_MODELS.md`](PHYSICS_MODELS.md). The scan-path design and the recording contract are in [`test-plans/scan-path-design.md`](test-plans/scan-path-design.md).

**Code:** `software/pc/qtpanda/scan_paths.py` (paths, bit-exact) and `software/pc/qtpanda/analysis/sim/`. The viewer is `analysis/sim/scan_paths_viewer.html`: a local file that opens in a browser.

---

## 1 · The chain

```
truth height map (Å)
  -> commanded X/Y for every 10 µs tick      scan_paths.py: bit-exact with the firmware arithmetic
  -> lateral piezo                           hysteresis, 158.7 Hz resonance, amplifier lag
  -> X-Y stage drift, Z drift                measured rates
  -> tunnelling current I(gap)               I = V / (R_c e^{2 kappa gap})
  -> preamp low-pass, ADC                    offset, noise, clip, one-tick delay
  -> firmware feedback loop                  integer PI, abs(), zero substitution
  -> bins exactly as the firmware sends them (L frames)
  -> RECONSTRUCTION -> image -> scores against the truth
```

## 2 · Reconstruction (what to use, and why)

1. **Use the combined height, not Z alone.** On every tick, height = tip height − gap, where the gap follows from the measured current: gap = ln(V / (I·R_c)) / 2κ. A slow loop leaves Z behind the surface, but the current reports exactly how far behind, so the combined estimate does not care how slow the loop is.
   - Z alone tops out at 0.89 on #1808, against 0.999 combined, with the same data.
   - This matches the Oct 15 report's finding that our morphology lives in the error channel.
2. **Undo the known preamp filter** before converting current to gap: I = (i[t] − (1−a)·i[t−1]) / a. Average over one bin (19 ticks), but only across windows where every tick is valid, so a clipped or lost tick can't leak into its neighbours. Tick-by-tick inversion amplifies noise.
3. **Ticks without height information** (current lost or clipped) are dropped, not replaced. Using the clip or loss bound instead biases tall features.
4. **Grid with the hybrid rule:**
   - interpolate to pixel centres where a sample lies within ¾ pixel (this fixes curved paths, whose samples fall between pixels);
   - bin and smooth-fill elsewhere (interpolating across holes is wrong).
5. **Place every sample where the tip really was:**
   - actual piezo position, once hysteresis and resonance are calibrated; until then, the commanded position;
   - shifted by the X-Y drift at its own time (line by line);
   - with the Z-drift ramp removed.

## 3 · Verification ladder: is the truth recreated when the physics is known?

Operator's standard (2026-10-23): no algorithm should fail to recreate an objective truth. Script `analysis/sim/ladder.py` adds one effect per layer, so each lost point has a named cause.

Results with the first reconstruction (combined estimate; Z alone in brackets). Truths: Sep 24 #1808 error channel / synthetic.

| # | Layer | Raster (default) | Cross-hatch | Spiral at raster speed |
|---|---|---|---|---|
| 1 | Geometry only | 0.999 / 1.000 | 0.999 / 1.000 | 0.976 / 1.000 |
| 2 | + feedback loop | 0.999 (0.89) / 1.000 (0.97) | 0.999 / 1.000 | 0.976 / 0.999 |
| 3 | + ADC noise | 0.999 / 1.000 | 0.999 / 1.000 | 0.975 / 0.999 |
| 4 | + preamp 400 Hz | 0.94 / 0.99 | 0.95 / 0.99 | 0.91 / 0.99 |
| 5 | + phantom offset | 0.94 / 0.98 | 0.95 / 0.98 | 0.91 / 0.98 |
| 6 | + lateral piezo, commanded positions | 0.77 / 0.93 | 0.82 / 0.93 | 0.77 / 0.92 |
| 7 | + lateral piezo, actual positions | 0.91 / 0.97 | 0.93 / 0.97 | 0.91 / 0.98 |
| 8 | + X-Y and Z drift, registered | 0.92 / 0.98 | 0.96 / 0.99 | 0.93 / 0.99 |

**After the reconstruction fixes in §2** (preamp inversion, invalid-tick masking, hybrid gridding), with full physics and actual positions:

| | Raster | Spiral at raster speed |
|---|---|---|
| Sep 24 #1808 | **0.995** | **0.997** |
| Synthetic | **0.991** | **0.993** |

**What the ladder proves:**
1. Path generation, the reconstruction map, gridding and the combined estimate are exact where the physics is known (0.999).
2. The default raster and its custom-file copy give identical results.
3. Drift registration costs nothing when the drift is known.

**What it says still needs work on the real rig:**
1. **Lateral piezo calibration:** the largest lever in the simulation (0.79 → 0.99). That figure rests on an assumed 5% hysteresis, which our data suggest is too large; see `PHYSICS_MODELS.md` §5 for the plan to measure it (HY1–HY4).
2. **Preamp bandwidth:** must be measured (CN5) before the inversion can be applied to real data.
3. **ADC dynamic range:** tall or steep features drive the current out of range (clipped or lost). That information is gone, and only slower scans, higher gain or another setpoint or preamp range recover it.
4. **Sampling:** detail below ~5–6 px per atom (the Oct 15 rule) is lost for any path. On #1808, softening the truth by 0.7 px raised the spiral's geometry score from 0.981 to 0.998.

## 4 · Back-test against the real good-tip day (Sep 24)

`analysis/sim/backtest_sep24.py`, `backtest_diag.py`.
- **Reproduced:** the raw Z span (tilt).
- **Not reproduced:** the trace/retrace lag dome that dominates real Sep 24 Z images (L rms 110 units, 70% line-locked). The Oct 15 report already explained that dome as the loop (~9 ms) being slower than a 5.1 ms line (rank-1 limit). The simulator's lag is ~14× too small, so its loop gain, or what the loop is following, is mis-modelled (OI-18).

Until this is fixed, simulated **Z-only** images look better than real ones. The combined estimate is insensitive to loop lag, so the reconstruction conclusions stand.

## 5 · Scan-path comparison (equal time, Oct-22-like settings)

`compare_paths.py`, `compare_extra.py`. Truths: Sep 24 #1808 error channel and synthetic. 14 nm window, 49.8 s per frame (pairs 99.6 s). Full results and images are in the viewer.

- **With the full reconstruction and calibrated positions, every path reaches ~0.99 on #1808.** Path choice then matters for smoothness, streaks and drift sensing, not for accuracy.
- **Smoothness:** curved paths put ~100× less drive energy near 158.7 Hz and have 6–60× lower peak acceleration.
- **Coverage:** centre-return loops, spokes and rose leave 13–27% of the area unvisited.
- **Speed confound:** at equal time, slower paths look better under the old Z-only method. Always compare at matched tip speed.

Final run (2026-10-23), full physics, piezo calibrated (in brackets: commanded positions / old Z-only method):

| Path | Sep 24 #1808 | Synthetic |
|---|---|---|
| Raster (default) and custom-file raster (identical) | **0.995** (0.785 / 0.775) | **0.991** (0.954 / 0.878) |
| Raster 15° / 45° | 0.996 / 0.997 | 0.992 / 0.992 |
| Archimedean / Fermat spiral | 0.998 / 0.998 | 1.000 / 0.999 |
| Spiral at raster speed | 0.997 | 0.992 |
| Centre-return loops / spokes | 0.990 / 0.991 | 0.999 / 0.999 |
| Rose | 0.987 | 0.943 (coverage gaps) |
| Raster × 2 / cross-hatch pair | 0.996 / 0.996 | 0.997 / 0.995 |

By eye, the default raster's rebuild of #1808 matches the truth, including step edges and single speckles (`analysis/sim/final_check.png`).

## 5.1 Reality check on existing recordings (RC1, 2026-10-23)

`software/pc/qtpanda/analysis/rc1/RC1_RESULTS.md`: the combined height computed from v1 frames (legacy approximation A5) was compared, by repeat correlation between neighbouring same-direction sweeps, with Z and the error channel.

| Data | Usable current | Z | Error | Combined |
|---|---|---|---|---|
| Sep 24 #1802–#1812 | 50% | 0.94 (mostly the scan-fixed lag band) | 0.79 | 0.78 |
| Sep 24 #1586–#1599 | 44% | 0.85 | 0.89 | 0.89 |
| Oct 22 #20–#31 | 27% | 0.29 | 0.36 | 0.33 |

1. **On v1 data the combined height reproduces the error channel and adds nothing.** The Z term is ~20× smaller than the gap term on Sep 24. Masking and pixel-level preamp inversion make it worse, because they need the v2 fields.
2. **The simulator was optimistic about the current range.** Real Sep 24 scans had usable current in only 44–50% of pixels; the simulation had nearly 100%. The stated height scale (an error-channel lower bound) keeps the simulated current in range. **Next fix:** scale the simulated truth (and check the loop) until the simulated usable-current fraction matches the real one, then re-run the ladder. Expect the recreation to drop where the current leaves the range. That is real information loss, recoverable only by keeping the current in range.
3. **Consequence:** the ≥ 99% results hold for the regime where the current stays in range. Getting real scans into that regime (gain, line rate, setpoint, offset fix F4) is a precondition for the combined height to pay off (D36).

## 5.2 Simulating Sep 24 at its own settings (SM1, 2026-10-23)

`analysis/sim/sm1_current_range.py`, `sm1_current_range.json`, `sm1_preamp.json`. Settings: 27.1 nm, 512 px, 1 tick per pixel (196 lines/s, tip ≈ 10.6 µm/s), KIGA 1.144, 1000 pA, truth = #1808 error channel.

1. **Z is flat in simulation** (Z-only ≈ 0), as in the real data (Z moved 4–6 pm on gold; Oct 15 §3.3). The loop cannot follow at this speed.
2. **The preamp must be much faster than the assumed 400 Hz.** The simulated error channel matches the truth only if f3dB ≳ 5 kHz:

   | Preamp f3dB | Blur at this speed | Simulated error channel vs truth |
   |---|---|---|
   | 400 Hz | 4.2 nm | 0.28 |
   | 1.6 kHz | 1.1 nm | 0.61 |
   | 5 kHz | 0.34 nm | 0.79 |
   | 20 kHz | 0.08 nm | 0.84 |

   Real Sep 24 error images are sharp and repeat at 0.79–0.89, so a 400 Hz preamp is inconsistent with them. **Confirmed directly by PR1** (edge widths in real data): f3dB ≳ 6–16 kHz. The simulator's working value is now 6 kHz. The Sep 17 ~400 µs constant is probably not the preamp acting on the current channel. This is inferred through the simulator; the direct check is the trace-vs-retrace shift of the error channel (a 400 Hz preamp would separate them by ~40 px).
3. **Usable current still disagrees:** simulation 82–100% of pixels, real 44–50%. Scaling the truth up to 8× only lowers it to 69%. The real scans lose current over larger areas than the model produces: candidates are real relief larger than the error-channel lower bound in places, the phantom offset and abs(), or tip state. Open (A12).

## 5.3 How much does piezo calibration matter? (hysteresis sensitivity, 2026-10-23)

`analysis/sim/hy_sensitivity.py`: default raster, #1808 truth, full physics, final reconstruction.

| Hysteresis (mid-line ~half of this) | Commanded positions | Actual positions |
|---|---|---|
| 1% | 0.869 | 0.994 |
| 5% | 0.785 | 0.995 |
| 12% | 0.706 | 0.996 |

Even at 1% hysteresis, commanded positions lose ~13 points: the rest comes from the modelled lateral **dynamics** (158.7 Hz resonance applied laterally, 3 kHz amplifier lag), which are themselves assumptions. So the calibration lever is 13–29 points depending on hysteresis and lateral dynamics. Both need measuring (HY bench, lateral resonance and amplifier response). With actual positions known, the result is insensitive to hysteresis (0.994–0.996).

## 6 · Common practice in simulation, and how we apply it

*General practice, not yet checked against sources (I-6):*
1. **Verify before you validate.** First prove the code reproduces a known truth exactly where the physics is known (the ladder). Then check it against real data (the back-test).
2. **Add one effect at a time.** Otherwise losses can't be attributed.
3. **Separate identification from prediction.** Fit parameters (hysteresis, preamp f3dB, damping) on one data set, predict another.
4. **Keep the truth independent of the method under test.** A raster-made truth flatters the raster: Sep 24 is raster-acquired, which is why a synthetic truth is kept.
5. **Report the uncertainty of assumptions.** Every parameter carries a status in `PHYSICS_MODELS.md`. Rerun the sensitivity cases (for example hysteresis 0–15%) before drawing conclusions.
6. **Version the models.** Path generators are versioned in code; physics changes are logged in `PHYSICS_MODELS.md` with a date.

## 7 · How to run

```
cd software/pc/qtpanda/analysis/sim
python ladder.py            # verification ladder (~40 min)
python ladder_fixes.py      # reconstruction fixes check
python backtest_sep24.py    # back-test against Sep 24 (~1 min)
python compare_paths.py     # technique comparison (~20 min), then:
python build_paths_viewer.py
```

Tests: `software/pc/qtpanda/tests/test_scan_paths.py` (22 tests: bit-exact against a literal firmware port, custom file = raster, transforms, no overflow at full size).

## 8 · Open items

| ID | What | Where |
|---|---|---|
| HY1–HY4 | Measure hysteresis (fast axis, slow axis, creep, cross-hatch) and set the simulator to it | `PHYSICS_MODELS.md` §5 |
| CN5 | Measure preamp f3dB from raw-capture noise | roadmap |
| OI-18 | Make the simulator reproduce the Sep 24 lag dome | plan |
| SP0/SP1 | Scan-path library done; GUI dropdown, emulator playback, firmware modes pending | `scan-path-design.md` |
| RC1 | Combined estimate on real recordings: **done on v1, adds nothing beyond the error channel** (§5.1); retry with frame v2 and in-range scans | done / follow-up |
| A12 | Calibrate the simulator's usable-current fraction to real scans (height scale, loop), re-run the ladder | DECISIONS.md A12 |
