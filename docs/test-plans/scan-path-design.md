# Scan paths: design and reconstruction contract (living)

**Status:** experimental, agreed 2026-10-23. Built as an **option**: the default scan is unchanged and nothing here is required for normal imaging. Whether it ranks above or below the calibration steps (T8, M6) is the operator's call and still open. Roadmap: SP1 (paths), F8 (tick timestamps), F9 (DAC write guards), F6 (cross-hatch, now a sequence inside SP1).

## 1 · Why

- **Streaks and banding are tied to the slow axis.** Oct 22 Z has no single overlay frequency; 39% of the slow-axis power is line-to-line jitter at 2–4-row periods (OI-14). A frame with the fast axis swapped carries that noise along the other direction, so an orthogonal pair can be merged to remove it.
- **Drift distorts each path differently.** A raster gets a shear; a spiral gets off-centre rings; paths that revisit the centre measure drift as they go. Orthogonal pairs are an established way to undo drift distortion (Ophus, Ciston and Nelson, Ultramicroscopy 2016, STEM and scanning probe; to verify under I-6).
- **Smooth motion is kinder to the stage.** Triangle rasters put energy into every odd harmonic and ring the 158.7 Hz mode at each turnaround; paths built from a few sines (figure-8, rose, circles) can stay far below it.

## 2 · Principles (operator, 2026-10-23)

1. **Every named path lives in code.** Each path the dropdown offers is defined in the repo (Python generator + firmware mode), versioned, readable and testable, so a future reader (person or LLM) can audit exactly what the tip did. No path exists only as data.
2. **Custom paths are allowed, but travel with the data.** A "Custom" option reads a path file in the standard below; the file is copied into the recording folder and its hash goes in the sidecar.
3. **No orphan frames.** A `.frames` file must never exist without everything needed to rebuild every sample's commanded X/Y. That means the path ID, generator version, all parameters, firmware version and capabilities, tick period, samples per bin, scan size, offsets, calibration snapshot and the per-frame sequence state. Recordings without these fields are, by definition, `raster v1` (FW 5.6), today's path.
4. **Released generators are never edited in place.** A change makes a new version (`spiral_fermat v2`); old versions stay in the code so old recordings still reconstruct.
5. **Bit-exact by construction.** Firmware generators use integer phase counters and a sine look-up table (no floating-point `sinf`). The Python generator reproduces every position bit for bit, and golden test vectors in the repo are checked against the emulator and against a firmware dump command.
6. **Commanded is not physical.** The reconstruction map gives commanded positions. Piezo dynamics, hysteresis and drift corrections are separate, versioned post-processing layers, never baked into raw data.
7. **Mode 0 is today's raster, untouched.** Existing recordings, tools and assumptions keep working.

## 3 · Layers

| Layer | What it is | Where |
|---|---|---|
| Path | the shape of one frame: commanded (x, y) for every tick | `scan_paths.py` (PC), `SPTH` modes (firmware) |
| Sequence | what changes between frames: fast-axis swap (cross-hatch), spiral out/in, rotation per frame | same; the sequence state is stamped per frame |
| Bins and segments | a **segment** is the path's equivalent of a line: a fixed number of bins, each the average of a fixed number of ticks; firmware sends one `L` frame per segment, with the segment index in the line field | firmware, unchanged wire format (plus F8 tick) |
| Reconstruction map | (frame, segment, bin) → commanded x, y in nm, and the tick | `scan_paths.reconstruct()` from the sidecar alone |
| Gridding | samples → image, with a coverage map (hits, first and last visit per pixel) | PC |
| Physical model | commanded → actual position (resonance, hysteresis, creep, amplifier lag) | simulator first; optional correction layer later |
| Drift registration | actual → sample frame, using each sample's time (v2's line-by-line method, generalised per sample) | `v2_core.py` → library |

## 4 · Path catalogue (first set; parameters fixed in simulation)

| ID | Path | Parameters | Notes |
|---|---|---|---|
| `raster` v1 | today's trace/retrace with a continuously rising Y (lines slightly diagonal) | as today | mode 0, untouched |
| `raster_rot` v1 | today's raster rotated by θ: x = xo + u·cosθ − v·sinθ, y = yo + u·sinθ + v·cosθ, with u, v today's triangle values and cos/sin as Q15 table entries | θ: 15°, 45°, 90°, custom | a rotated square of side s needs s·√2 of range; GUI clamps |
| `crosshatch` (sequence) | `raster` and the fast-axis swap (transpose) alternating per frame | swap or rotate-90 (they differ by a mirror; recorded) | replaces F6/SWXY |
| `spiral_arch` v1 | Archimedean spiral, even ring spacing | pitch (nm), turns, CW/CCW, out / in / out-in pair, constant angular or constant tip speed | out-in pairs cross each radius both ways (lag cancellation, like trace/retrace) |
| `spiral_fermat` v1 | Fermat spiral, r ∝ √θ: even area per turn | as above | most even sampling density |
| `loops_centre` v1 | circles of growing radius, each reached and left along a radial spoke through the centre | loops, radius step, rotation per loop | centre revisit every loop = drift reading |
| `spokes` v1 | radial lines through the centre at rotating angles | spokes per frame, rotation per frame | simplest centre-return path; centre heavily oversampled |
| `rose` v1 | rose / figure-8 (x = A sin t, y = B sin 2t, and r = cos kθ), precessing a small angle per loop to fill a disc | k or ratio, precession, sine drive or constant speed | smoothest drive; passes the centre at speed |
| `custom` v1 | vertices from a path file (section 6) | file | needs a firmware table mode; simulation-only until then |

Spirograph curves (hypotrochoids) are a later candidate in the same family as `rose`.

## 5 · Recording contract (sidecar `scan_path` block)

```json
"scan_path": {
  "id": "spiral_fermat", "version": 1,
  "params": {"pitch_nm": 0.35, "turns": 40, "sense": "ccw", "direction": "out-in", "speed": "constant_tip"},
  "sequence": {"id": "none", "version": 1},
  "segments_per_frame": 256, "bins_per_segment": 512, "ticks_per_bin": 19,
  "tick_period_us": 10, "scan_size_nm": 30.0, "offset_nm": [0.0, 0.0],
  "firmware": "QTPANDA-FW 5.7 CAPS:...,SPTH,TICK", "generator_sha256": "…",
  "custom_file": null, "calibration": {"…": "snapshot as today"}
}
```

Plus, per frame and per segment (F8): the firmware tick at the segment's first bin, and the sequence state. Plus a **position self-check**: each frame, the firmware sends a few (tick, commanded x, commanded y) checkpoints, and reconstruction verifies them against its own map. A mismatch is reported, never ignored.

## 6 · Custom path file standard (draft)

JSON, versioned: `{"format": "qtpanda-path", "version": 1, "units": "nm", "closed": false, "speed_nm_s": …, "bins_per_segment": …, "vertices": [[x, y], …]}`. The firmware plays the vertices at constant speed with linear interpolation, in integer steps, so the PC can reproduce every tick. It is stored next to the recording and hashed into the sidecar.

## 7 · What the timing audit found (2026-10-23)

- **Exact:** the commanded position at tick n depends only on n and the settings (integer counters with exact rational steps). Timer jitter moves *when* a tick fires by microseconds, never *where* it points. Pixel bins are fixed tick counts, and lost line frames are counted.
- **Constant delays, correctable:** the ADC reading belongs to the previous tick (10 µs). The preamp (~400 Hz) and the high-voltage amplifier and piezo add lag that is linear and modelable.
- **Not exact:**
  - PC receive timestamps jitter by milliseconds, so tick counts must be the time base (F8).
  - Main-thread DAC writes (manual sliders, drift hold, clip guard, retract, approach) mask interrupts for about 1 µs and can delay one tick. They never touch the fast axis, which the ISR writes on every tick.
  - Manual DACX/DACY during a scan, or DACZ under feedback, lasts one tick before the ISR overwrites it (F9).
  - `micros()` is 1 µs coarse; ISR timing should use the cycle counter.
  - Settings changes land at arbitrary ticks and should be acknowledged with their tick (F8).
- **Room:** code is 59.5 KB of ~7.9 MB flash. The ISR took 2–5 µs of its 10 µs budget (Jul 31 DIAG). A generator costs well under 1 µs.

### 7.1 Time base across resets (operator, 2026-10-23)

The microcontroller's tick count is the gold standard. The PC clock is only a reference. The Teensy is reset or power-cycled often during live runs, so:
- **Free-running counter.** The tick counter counts from boot and is never reset by RUN. Every line frame and status record carries the tick count and a **boot ID** (random at boot, from the hardware RNG).
- **Epochs on the PC.** Each boot is an epoch. Within it, the PC fits PC time = a + b·tick, robustly over many frames, and unwraps 32-bit wraps (every 11.9 h at 100 kHz). A new boot ID, or a tick going backwards, starts a new epoch. Recordings never mix epochs silently.
- **PC jitter is real.** On Oct 22 the *median* PC gap between line frames was 91–94 ms while the *mean* was 97.5 ms, which matches 512 px × 19 ticks × 10 µs. PC receive times are batched, so they are not a time base.

### 7.2 Findings from the bit-exact port (2026-10-23)

1. **Line-number slip (R19; streak-plan item 2, found Oct 1 with fwsim.py; confirmed here).** At the end of each Y-cycle the resync resets the line counter one tick *before* the last line is stamped:
   - The first frame after RUN is stamped 0…510 and then 0 again.
   - Every later frame stamps true line L as L+1 (mod lines).

   Confirmed in the Oct 22 recording: …509, 510, **0**, 1… in the first cycle, then …510, 511, 0… every cycle after. The replay places rows by stamped number, so **every up/down pair carries a hidden 2-row offset** (about 0.23 nm at 30 nm), opposite in up and down sweeps. That is part of the 8.4 px "hysteresis" offset.
   - **Fixes:**
     - Tick stamps (segment = tick ÷ (spp × bins)) make the index exact.
     - A firmware fix moves the resync to the line boundary.
     - For legacy files, a PC correction rule (first cycle: the second 0 is line 511; afterwards stamped − 1) can be applied, but only with the operator's agreement, since it shifts every historical image by one row.
2. **The sidecar records the wrong samples-per-pixel** (streak-plan item 5; CR7). Oct 22 says `derived_samples_per_pixel: 4`, but the firmware used 19: the GUI derives it assuming the old 25 kHz ISR. This is exactly the orphan-frame risk. The `scan_path` block stores the spec the firmware actually ran (and, with F8, the firmware echoes it).



| Effect | Model | Parameters from existing data |
|---|---|---|
| Stage resonance | 2nd-order system | 158.7 Hz from halted holds; damping from the peak width |
| Hysteresis | Prandtl–Ishlinskii or Bouc–Wen | loop width from the 8.4 px up/down offset (~3% of range) |
| Creep | logarithmic after large moves | settling after offset changes |
| Amplifier lag | 1st-order low-pass | ~400 Hz preamp; trace/retrace shift |
| **X-Y stage drift** | measured model: 0.56 px/s up the frame, ~1 nm up/down offset, jumps at gain changes; constant and decaying variants | V2 registration |
| **Z drift** (OI-16) | vertical ramp at the same-sample rate, kept separate from the tilt coupling | Oct 22: ~39 codes/s same-sample, −7 codes/s tilt part; gain and time still confounded |
| Feedback loop | `loop_sim.py` (tick-level port of the firmware) | KIGA, setpoint, phantom offset |

Thermal drift on this rig is mainly a **Z** effect: the tip leaves the Z range and needs stepper moves to recover. The lateral drift measured from images is a different phenomenon (X-Y stage drift), and the two are named and modelled separately.

## 8.1 Back-test against the good-tip day (2026-10-23)

The simulator (`analysis/sim/scan_sim.py`) imaged the Sep 24 truth with today's raster at Sep 24's settings (512 px, 3 ticks/px, KIGA 1.144, 1000 pA). Line-levelled Z statistics were then compared with the real sweeps #1586–#1599 (`backtest_sep24.py`, `backtest_diag.py`).

| | Real Sep 24 | Simulator (best variants) |
|---|---|---|
| Lag share | 0.95 (0.83–0.97) | 0.6–0.89 |
| Trace/retrace correlation | −0.91 | −0.2 to −0.81 |
| Lag part L rms / line-locked share | 110 units / 70% | 8–16 units / 21–28% |
| Raw Z span (tilt) | 58,600 | 51,500 |

- **Reproduced:** tilt and raw span. **Not reproduced:** the dominant real artefact.
- **The artefact:** a smooth, symmetric, scan-synchronous **dome in (trace − retrace)**, 190–800 units peak-to-peak and 99% cubic. It persists on sweeps with ~zero X slope. **Correction:** this is the Oct 15 report's rank-1 limit, the feedback loop (~9 ms) slower than a 5.1 ms line, with the retrace mirroring the trace (−0.98). The 'loop lag' exclusion below was wrong. The simulator's loop or drive is mis-modelled (OI-18).
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

## 8.4 Verification ladder (2026-10-23, operator: "no algorithm should be unable to recreate objective truth")

Script `analysis/sim/ladder.py`: one effect added per layer, and each layer rebuilt three ways: from Z alone, from the **combined estimate** (h = tip height − gap(I), using the current measured on every tick) and from the true height at the bins.

| Layer | Raster (#1808 / synthetic) | Cross-hatch | Spiral at raster speed |
|---|---|---|---|
| L0 geometry only | 0.999 / 1.000 | 0.999 / 1.000 | 0.976 / 1.000 |
| L1 loop, combined (Z alone) | 0.999 (0.89) / 1.000 (0.97) | 0.999 / 1.000 | 0.976 / 0.999 |
| L2 + ADC noise | 0.999 / 1.000 | 0.999 / 1.000 | 0.975 / 0.999 |
| L3 + preamp 400 Hz | 0.94 / 0.99 | 0.95 / 0.99 | 0.91 / 0.99 |
| L4 + phantom offset | 0.94 / 0.98 | 0.95 / 0.98 | 0.91 / 0.98 |
| L5 + lateral piezo, commanded positions | 0.77 / 0.93 | 0.82 / 0.93 | 0.77 / 0.92 |
| L5a same, actual positions known | 0.91 / 0.97 | 0.93 / 0.97 | 0.91 / 0.98 |
| L7 all physics, drifts registered | 0.92 / 0.98 | 0.96 / 0.99 | 0.93 / 0.99 |

1. **The reconstruction is exact where the physics is known.** Path generator, map, gridding and the combined estimate reach 99.9% on the raster and cross-hatch.
2. **Z alone throws information away** (0.89): always rebuild from Z plus current.
3. **Remaining losses, by cause:**
   - binning curved-path samples to pixels (spiral geometry 0.976): a reconstruction fix, interpolate to pixel centres;
   - preamp lag (−6 points): a reconstruction fix, invert the known filter;
   - **lateral piezo dynamics (−15 to −20 points):** a calibration need. Most of it comes back when actual positions are known.
4. **Drift registration costs nothing** when the drift is known; cross-hatch gains most from it.

Fix check: `analysis/sim/ladder_fixes.py`.

## 8.3 Re-run on real morphology (2026-10-23, operator: the first truth was not representative)

**Truth: Sep 24 #1808, error channel.** The operator's pick: good tip, gold terraces and step edges. It is used on its own, because averaging neighbours left seams. It is converted to height by the error's own physics, which gives 0.5–1 Å steps instead of 2.35 Å, so the heights are a lower bound. The 14 nm window sits at the image centre. The earlier "Sep 24" truth (averaged plane-levelled Z) was a smooth gradient and is withdrawn.

1. **Validation gate passed** again on both truths.
2. **Z drift dominates.** Correcting X-Y drift alone is worse than raw (raster −0.27 vs 0.59). With X-Y and Z drift removed the raster reaches 0.78. Mapping Z drift (OI-16) is a prerequisite.
3. **Every non-raster path matches or beats the raster:**

   | Path | Correlation with truth |
   |---|---|
   | 15° raster | 0.81 |
   | 45° raster | 0.80 |
   | Fermat spiral | 0.82 |
   | Archimedean spiral | 0.82 |
   | Archimedean spiral at raster speed | 0.80 |
   | Raster | 0.78 |
   | Loops | 0.74 |
   | Rose | 0.73 |

   Loops and rose leave gaps.
4. **Streak anisotropy** falls from 1.90 (raster) to 1.2–1.4.
5. **Cross-hatch:** 0.793 vs 0.783 for two raster frames, anisotropy 1.56 vs 1.96. Each frame is shown separately in the viewer: X-fast frames carry horizontal streaks, Y-fast frames vertical ones, and the merge is cleaner than either.

## 8.2 First comparison run (2026-10-23)

Settings: Oct-22-like (19 ticks/bin, KIGA 4.6, 500 pA), a 14 nm scan, X-Y drift 66 pm/s, Z drift 0.39 Å/s, 49.8 s per frame. Script: `analysis/sim/compare_paths.py` + `compare_extra.py`. Viewer: `analysis/sim/scan_paths_viewer.html`.

1. **Validation gate passed.** The raster written as a custom path file gives an identical reconstruction on both truths, and positions are identical tick for tick with the literal firmware port (`tests/test_scan_paths.py`, 22 tests).
2. **Drift removal matters most.** Raster on the synthetic truth: correlation 0.54 raw → 0.88 with X-Y and Z drift removed (0.47 with X-Y only).
3. **Speed, not shape, decides fidelity at equal time.**
   - At equal time the 128-turn spiral (70–160 nm/s) and centre-return loops (56 nm/s) score above the raster (288 nm/s).
   - At raster speed the spiral scores below it: 0.81 vs 0.88.
4. **Curved paths buy smoothness and no streaks, not accuracy:**
   - residual streak anisotropy ~1 vs 5.9 for the raster;
   - ~100× less drive energy near 158.7 Hz;
   - 6–60× lower peak acceleration.

   A 15° rotated raster removes most of the streak signature for almost nothing (0.87).
5. **Cross-hatch** is the best two-frame option (0.947 vs 0.935), with the caveat that the model lacks the real line artefact (OI-18).
6. **Loops, spokes and rose leave 13–27% of the disc unvisited.** They are useful as drift sensors, not imagers, at these settings.

## 9 · Simulation before firmware

1. Ground truth: the good-tip Sep 24 series (#1586–#1599, repeat 0.9+, registered and averaged) and synthetic surfaces. Sep 24 was itself scanned with the raster, so the raster's score against it is partly circular; the synthetic surfaces are the fair test.
2. Chain: truth → bit-exact path → physical model → tip over the surface → current → firmware loop → binned stream exactly as the firmware sends it → reconstruction → compare with the truth.
3. Scorecard per path:
   - correlation with the truth and recovered resolution;
   - streak and lag-smear measures;
   - coverage after N seconds and the largest unvisited hole;
   - hit-count uniformity and revisit interval;
   - peak acceleration and drive energy near 158.7 Hz;
   - range of tip speed along the path.
4. **Pixels-per-atom audit (operator, 2026-10-23).** The Oct 15 resolution report ("What limits our scan resolution") requires ~5–6 px per atom spacing before atoms render evenly. Between 2 and ~5 px, sampling-phase scatter makes atoms unevenly bright. Every path must be checked in the **sample frame**, both across the path (line or ring spacing) and along it (tip speed × bin time), together with the report's speed limit (atoms per second against the signal-chain bandwidth). First numbers, at the simulation settings (14 nm, 512 bins, 19 ticks per bin, Au(111) 0.288 nm):
   - Raster: 0.055 nm pitch both ways, so 5.2 px/atom (borderline).
   - Spiral at raster speed: 0.055 nm ring spacing (5.2 px/atom across). Along the path the 190 µs bins cover 33–76 pm, so 3.8–8.7 px/atom, *below* 5 near the edge.
   - Centre-return loops, spokes and rose: their unvisited gaps (up to 0.66 nm) fail the rule outright.
   - Rotated rasters keep the raster's pitch.

   Add px/atom (across and along, worst case) and atoms/s to the scorecard.
5. Overlap versus new pixels is counted in the **drift-registered sample frame**. Revisits average out noise and measure change; new pixels extend coverage.
6. Emulator playback: the emulator serves the simulated stream, so the live GUI's gridding and display are tested end to end.

## 10 · Build order (each step usable on its own)

1. `scan_paths.py`: generators for the catalogue, `reconstruct()`, coverage map, golden test vectors; reader support for the `scan_path` block (absent = `raster v1`). PC only, no risk.
2. Physical model and simulator with the scorecard (section 9).
3. GUI: "Scan path" dropdown (default Raster; the other entries labelled experimental), live gridded display and coverage overlay; replay reads the path block.
4. Emulator: `SPTH` modes and the F8 tick fields, checked against the golden vectors.
5. Firmware: F8 + F9 + the `SPTH` modes in one flash with the pending F2 retract fix, only when the operator chooses. Mode 0 stays bit-identical; a firmware position dump is compared with the Python vectors.

## 11 · Open decisions

1. Priority relative to calibration (T8 / M6).
2. Which paths reach the dropdown after the scorecard.
3. Whether a firmware table mode (`custom`) is wanted, or the named paths are enough.
4. Constant angular speed versus constant tip speed for spirals and roses (smoothness versus even density).
