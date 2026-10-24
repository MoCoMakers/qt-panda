# Physics models (living registry)

**What this is.** Every physical model the qt-panda analysis and simulation code relies on: the equation, the parameter values, where each value came from, how confident we are, and how to improve it. Models are meant to evolve: when a calibration or measurement arrives, update the value here **and** in the code, and note the date.

**Status tags.**
- `measured`: from our own data, with the source named.
- `estimated`: derived from our data indirectly.
- `assumed`: a textbook or typical value, not yet checked on this rig.
- `hypothesis`: a candidate explanation still under test.

**Caveat on "common practice".** The sections marked *Common STM practice* are written from general knowledge, not yet checked against primary sources. Verifying them is investigation I-6 (`docs/test-plans/2026-10-23-open-issues-and-tests.md`), which should also add references.

Related:
- [`SIMULATION.md`](SIMULATION.md): the scan simulator that uses these models.
- [`stm-techniques-backlog.md`](stm-techniques-backlog.md): techniques to borrow.
- [`test-plans/scan-path-design.md`](test-plans/scan-path-design.md): scan paths and the reconstruction contract.

---

## 1 · Tunnelling junction

**Model.** I = V / (R_c · exp(2κ·s)): bias V, gap s (Å), point-contact resistance R_c, decay constant κ (Å⁻¹).

| Parameter | Value | Status | Source / note |
|---|---|---|---|
| R_c | 12.9 kΩ | assumed | quantum point contact, h/2e² |
| κ | 1.025 Å⁻¹ (~1 decade of current per 1.1 Å) | assumed | equals an apparent barrier of ~4 eV; `loop_sim.py` |
| Bias | −49.6 mV | measured | Oct 22 / Sep 24 journals |
| Setpoint | 500 pA (Oct 22), 1000 pA (Sep 24) | measured | sidecars |
| Gap at setpoint | ~4.4 Å above point contact at 100 MΩ | estimated | report v1, gap calculator |

**How to improve.** Measure the apparent barrier with I(z) spectroscopy: current against tip height at a fixed point, where the slope of ln I gives 2κ. Common STM practice treats the apparent barrier as a check on tip and surface cleanliness. In air and ambient conditions it is often well below the work function (gold ≈ 5.3 eV).

## 2 · Current measurement chain

| Element | Model | Value | Status | Source |
|---|---|---|---|---|
| Preamp | 100 MΩ transimpedance, 1st-order low-pass | f3dB **≳ 6–16 kHz** (PR1 edge-width bound); 400 Hz ruled out for the current channel | estimated (PR1, 2026-10-23) | Sep 17 ~400 µs constant (`docs/ai/hypotheses/time-artifacts-piezo-vs-preamp.md`); the scan-dwell fidelity report sweeps C = 0.3–10 pF (1 pF → 1.6 kHz, 10 pF → 159 Hz) |
| ADC | 3.125 pA per count (1X preamp), ±32767 | | measured | firmware, preamp notes |
| ADC noise | 4 counts rms (5 at the quiet bench) | | measured | loop_sim calibration; research harness |
| Clip | 32767 counts ≈ 102 nA | | measured | Oct 22 contact readings |
| Scan-time offset ("phantom") | −50 to −64 counts while scanning, −15 idle; does **not** flip with scan direction (−53 trace vs −52 retrace) | | measured | OI-3, `analysis/sim/phantom_direction.py` |
| Firmware abs() and zero substitution | err = log(setpoint) − log\|ADC\|; ADC 0 → 32767 under feedback | | measured (code) | `stm_firmware.hpp` |
| ADC timing | the value read on tick n is the conversion started on tick n−1 | | measured (code) | controlTick |

**Resolved by PR1 (2026-10-23, `software/pc/qtpanda/analysis/pr1/PR1_RESULTS.md`).** Edges in the error channel stay 0.26–0.61 nm sharp at 10–20 µm/s, where a 400 Hz filter would add 9–17 nm: a slow filter is ruled out and the preamp f3dB is ≳ 6–16 kHz. The trace/retrace shift is a ~1–3 nm direction-dependent **position offset** (constant across a 30× speed range and present at constant height), not a latency. It belongs with hysteresis and lateral calibration (§5). The paragraph below is kept for the record.

**Conflicting evidence (2026-10-23), since resolved.** HY1 measured a direction-dependent shift in the constant-current error channel that grows with line speed: a delay of roughly 0.3–0.5 ms, close to the Sep 17 ~400 µs. That speaks *for* a slow element. SM1 (below) speaks *against* a slow first-order filter. Deciding test, offline on #1808: a first-order filter shifts **and blurs** edges by about the same amount, while a pure latency or loop lag shifts without blurring. Compare edge 10–90% widths with the trace/retrace shift.

**Evidence against 400 Hz (2026-10-23, SM1).** Simulating Sep 24 at its own settings (tip 10.6 µm/s), the error channel only reaches the sharpness of the real Sep 24 images (repeat 0.79–0.89) if f3dB ≳ 5 kHz. At 400 Hz the images would be smeared by ~4 nm along the line (`SIMULATION.md` §5.2). Treat 400 Hz as unlikely for the current channel; working value for simulation ≥ 5 kHz until measured.

**Deciding measurement (open).** Read f3dB from the roll-off of a halted raw-capture noise spectrum (roadmap CN5). It decides whether preamp blur matters at our speeds. Common practice is to know the current amplifier's bandwidth before choosing line rates; it is one of the hard limits on scan speed.

## 3 · Feedback loop (firmware FW 5.6)

**Model.** Integer PI, run every 10 µs: err = setpointLog − logTable[\|adc\|]; iTerm += KIGA·65536·err; z_pos = iTerm >> 32. Ported tick for tick in `analysis/sim/loop_sim.py` and `scan_sim.run_loop`.

| Parameter | Value | Status | Source |
|---|---|---|---|
| Crossover | ~15.7 Hz per unit KIGA (≈18 Hz at 1.14, 72 Hz at 4.6) | estimated | Sep 24 diagnosis; not measured directly |
| Z per position unit | 0.00063 Å (loop estimate) vs 0.00057 Å (placeholder calibration, 3 nm/V) | estimated / assumed | agree within 10%; both await a gold-step calibration |
| Loop time constant at KIGA 1.14 | ~9 ms, longer than a 5.1 ms line | estimated | Oct 15 report, rank-1 limit |
| Stability limit | KIGA 4.6 clean, 9 oscillates | measured | Oct 22 sweep |

**Validated:** the as-is firmware model reproduces the Oct 22 current statistics (no current 61% vs 61%, clipped 9.1% vs 8.4% at KIGA 2.3).

**Not yet reproduced:** the Sep 24 trace/retrace lag dome (L rms 110 units, 70% line-locked; OI-18). The simulator's lag is ~14× too small, so the loop gain or what it is following is mis-modelled.

*Common STM practice:*
- Tune the gain by raising it until the trace and retrace line profiles overlap, then back off at the first ringing.
- Keep the crossover well below the lowest mechanical resonance.
- Record both channels (topography and current/error) in both directions.
- With a slow loop, the current image carries the fine morphology. This matches Oct 15 §3.3: Z varied only 4–6 pm on gold while the morphology sat in the error channel.

## 4 · Lateral scanner (piezo disc, X/Y)

| Effect | Model in the simulator | Value | Status |
|---|---|---|---|
| Sensitivity | linear | 5 nm/V (X, Y) placeholder | assumed: calibrate on a lattice (T8) |
| Mechanical resonance | 2nd-order low-pass | 158.7 Hz, ζ = 0.05 | frequency **measured in Z** (Oct 22 halted holds); applying it laterally and the damping are **assumed** |
| HV amplifier | 1st-order | 3 kHz | assumed |
| **Hysteresis** | Prandtl–Ishlinskii: average of 8 play operators, maximum width 5% of span | | **assumed and probably too large**; see section 5 |
| Creep | not modelled | | open |
| Commanded position | exact (bit-exact port of the firmware) | | measured (code); `scan_paths.py`, 22 tests |

## 5 · Hysteresis: what we know, what we don't, how to find out

**Why it matters.** Hysteresis means that for the same commanded voltage the piezo sits at a different place depending on the direction it was moving. When a sample is placed at its *commanded* position, trace and retrace (and up and down sweeps) put the same feature in different places. Combining them then smears or doubles it.
- **Simulation:** with an assumed 5% loop, the default raster drops from **0.995 to 0.785** correlation with the truth, the largest single loss in the verification ladder (`SIMULATION.md`). Knowing the actual positions recovers it.
- **Caution:** that number is only as good as the 5% assumption.

**What our data say so far.**

| Observation | What it implies | Source |
|---|---|---|
| Constant-height frames #931/#932 (Sep 24, 30 nm, 128 px): trace vs retrace offset **0 ± 1 px averaged over the line**, but a **dome along the line: about −3% of line width mid-line (0 to −6%), ~0 at the turnarounds** | consistent with ~3–5% fast-axis hysteresis; the earlier reading "far below 5%" (from the line average) was **wrong** | HY1, `software/pc/qtpanda/analysis/hysteresis/HY1_RESULTS.md` (2026-10-23) |
| Constant current, error channel, 30 nm, 256 px: mid-line separation −2.2% at 97 ms lines (Oct 22), −3.8% at 31 ms (Sep 24), beyond the search range at 5–20 ms lines | grows with line speed, so mostly a time delay or loop lag (~0.3–0.5 ms); at most ~2% can be hysteresis | HY1 |
| Constant current, Z channel, 128 px: a **flat** −6.8 to −7.0% offset, the same in pixels at 8.9 nm / 7.6 ms lines and 33 nm / 20 ms lines | not a delay; either hysteresis or a pixel-indexing artefact (firmware version of that run not recorded) | HY1 |
| Constant-current frames #1572–1578: a flat 12–13 px offset that **disappears with the loop off** | that offset is feedback lag, not piezo position | same |
| Up/down sweep offset 8.4 px (Oct 22, 30 nm) | mixes the 2-row line-number slip (R19), in-sweep drift shear (removed line by line in report v2) and the remaining slow-axis (Y) hysteresis | report v1/v2, scan-path-design 7.2 |
| Zoom steps matched commands within 5–10% (Sep 24 ladder) | scale or nonlinearity error, not direction-dependent | Oct 15 report §3.6a |
| ~400 µs time constant (Sep 17) | could be the preamp, the drive chain or the ceramic; not hysteresis (ruled out there) | `docs/ai/hypotheses/time-artifacts-piezo-vs-preamp.md` |

**Simulator model note (HY1).** The single Prandtl–Ishlinskii setting used produces a *flat* trace/retrace separation, while real piezo loops are usually curved (a dome). Compare with data at mid-line, and treat the model's shape as unverified.

**Sensitivity (simulation, 2026-10-23):** placing samples at commanded positions costs 13 / 21 / 29 points at 1 / 5 / 12% hysteresis on #1808; even 1% loses 13, because the modelled lateral resonance and amplifier lag (both assumed) also shift positions (`SIMULATION.md` §5.3). Calibrating lateral **dynamics** matters as much as hysteresis.

**What we don't know.**
- Loop width against scan size (hysteresis usually grows with the range).
- Slow axis against fast axis.
- Creep after offset or zoom changes (time constant, size).
- Sensitivity nonlinearity across the voltage range.
- Cross-coupling between X and Z (bow) for a disc scanner rather than a tube.

**How to find out (cheapest first; roadmap HY1–HY4).**
1. **HY1, offline: done 2026-10-23.** Only two usable constant-height frames exist. Result: ~3% mid-line (0–6%). Keep `hyst_frac` = 0.05 as the central value with sensitivity cases at 0.01 and 0.12. **Bench follow-up:** constant-height frames on a flat terrace, slow lines (≥ 100 ms), 10, 30 and 60 nm, a `VERS` record, both channels. Also measure the preamp bandwidth (CN5), so delay can be separated from hysteresis.
2. **HY2, after the R19 line-number fix:** re-measure the up/down offset with line-by-line drift registration. The remainder is slow-axis hysteresis.
3. **HY3, bench:** creep. Step the scan offset by a few nm, then track a feature's position for several minutes by registration. Fit a logarithmic creep law.
4. **HY4, bench:** a cross-hatch pair on the same area (scan paths). X-fast and Y-fast frames give the X and Y hysteresis and scale against each other.
5. Then T8: a known lattice for absolute scale (HOPG 0.246 nm, Au(111) 0.288 nm) and gold steps (2.35 Å) for Z.

*Common STM practice for hysteresis, creep and nonlinearity:*
- Open-loop piezos typically show hysteresis of roughly 10–15% of the range and logarithmic creep after large moves. Both shrink with smaller scan ranges.
- **Remedies, from simplest:**
  - use a single scan direction for measurements (trace-only images);
  - overscan and discard the turnaround regions;
  - wait for creep to settle after offset or zoom changes (often minutes);
  - keep scan size and direction consistent between frames that are compared;
  - calibrate with gratings or atomic lattices;
  - apply an inverse-model feed-forward (Prandtl–Ishlinskii or Bouc–Wen);
  - use closed-loop scanners with capacitive or strain sensors. These are common in AFM and large-range scanners, much rarer in compact STMs.
- Orthogonal (cross-hatch) scan pairs are also used to separate drift and scanner distortions.

## 6 · Drift

| Component | Model | Value | Status | Source |
|---|---|---|---|---|
| X-Y stage drift | position = v·t + up/down offset + jump per gain change; applied line by line by each line's time | 0.56 px/s ≈ 66 pm/s up the frame (Oct 22); 0.23 px/s (Sep 24) | measured | report v1 §D, v2 §2 |
| Z drift, same sample point | vertical ramp | +39 codes/s (gap opening), Oct 22 | measured (first split) | OI-16, `z_drift_split.py` |
| Tilt × lateral drift | geometric | −7 codes/s | measured | same |
| Z thermal drift (operator) | slow ramp that leaves the Z range | rig experience | observed | memory note; not yet separated from the above |

**Distinction to keep.** X-Y stage drift is measured routinely by feature tracking. Z thermal drift is a different phenomenon. The two are named and modelled separately.

*Common STM practice:*
- Let the instrument reach thermal equilibrium after approach or motor moves.
- Measure drift by image registration.
- Correct it either by feed-forward offset ramps or by atom/feature tracking.

## 7 · Image formation and sampling

| Model | Statement | Status | Source |
|---|---|---|---|
| Sampling | ~5–6 px per atom spacing before atoms render evenly; between 2 and ~5, sampling-phase scatter | estimated (model + Sep 24) | Oct 15 report §2 |
| Speed limit | features shorter than ~1.8 · v · τ are blurred by the preamp (MTF > 0.5 limit) | estimated | research harness, scan-dwell fidelity |
| Decoherence | adjacent-row correlation r = 1 / (1 + (L_c/L)^{2α}); L_c ≈ 2–5 nm on Sep 24 | estimated | Oct 15 report §4 (roadmap CN1) |
| Fold | S = (trace + retrace)/2 cancels the loop lag; L = (trace − retrace)/2 holds it | measured (works) | Oct 15 §3.4 |
| Combined height | h = tip height − gap(I): uses the current on every tick, so loop lag does not limit it | validated in simulation (0.999 where physics known) | `SIMULATION.md` |
| Morphology acceptance | survives the fold, repeats, appears in both Y halves, **scales with zoom** | adopted | Oct 15 §3.6b (CN2) |

## 8 · Changing a model

1. Update the value and status here, with the date and source.
2. Update the code constant and its comment:
   - `analysis/sim/scan_sim.py` (`PHYS`, `LOOP`);
   - `analysis/sim/loop_sim.py`;
   - `scan_paths.py` (path versions).
3. Re-run the back-test (`backtest_sep24.py`) and the ladder (`ladder.py`), and record the changes in `SIMULATION.md`.
