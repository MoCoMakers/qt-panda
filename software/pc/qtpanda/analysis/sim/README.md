# Simulations

**Overview and results:** [`docs/SIMULATION.md`](../../../../../docs/SIMULATION.md). **Models and their status:** [`docs/PHYSICS_MODELS.md`](../../../../../docs/PHYSICS_MODELS.md).

| Script | What |
|---|---|
| `scan_sim.py` | Scan simulator engine: lateral piezo, drift, tunnelling, preamp, ADC, firmware loop; combined height estimate; gridding (bin / interp / hybrid); scores |
| `truths.py` | Ground truths: Sep 24 #1808 error channel; synthetic set |
| `ladder.py`, `ladder_fixes.py` | Verification ladder (one effect per layer) and the reconstruction-fix check |
| `backtest_sep24.py`, `backtest_diag.py`, `phantom_direction.py` | Back-test against real Sep 24 data; phantom offset vs scan direction |
| `compare_paths.py`, `compare_extra.py`, `build_paths_viewer.py` | Technique comparison and the local viewer `scan_paths_viewer.html` |
| `check_error_truth.py` | Check of the error-channel truth (image, terrace levels) |


## `loop_sim.py`: firmware constant-current loop, tick by tick

Python port of the FW 5.6 per-tick feedback path (`stm_firmware.hpp:296–334`: zero substitution, `logTable[abs(adc)]`, integer integrator, `z_pos = iTerm >> 32`) driving a tip over a synthetic rough surface at the Oct 22 settings (30 nm, 256 px, 10.5 Hz lines, −49.6 mV, 1X preamp, 3.125 pA/count, clip at 32767), with ADC noise and the scan-time ADC offset (−55 counts while scanning, −15 idle; OI-3). Height scale from the report's loop-crossover estimate (15.7 Hz per unit KIGA). Firmware variants: `as_is`, `no_substitution`, `offset_corrected` (subtract the measured offset, keep `abs()`), `offset_corrected_no_sub`, `signed` (subtract the offset, use the bias sign: only positive readings are current).

**Calibration** (surface roughness 15 Å, 3 seeds × 32 lines): as-is firmware reproduces the Oct 22 current statistics without fitting the second gain: KIGA 2.3 no-current 61% / clipped 9.1% (measured 61% / 8.4%), KIGA 4.6 57% / 7.2% (measured 53% / 7.2%); halted with feedback on, 100% in range (measured 99%). Not modelled: the 158.7 Hz resonance, ~400 Hz preamp bandwidth, piezo dynamics, so simulated lag shares are lower than measured (0.74 vs ~0.9 at 2.3). Use the comparison between variants, not the absolute image-quality numbers.

### Results (2026-10-23; `loop_sim_variants.json`, `loop_sim_setpoint.json`)

At 500 pA:

| Variant | KIGA | No current | Clipped | In range | Z vs true surface | Lag share |
|---|---|---|---|---|---|---|
| as_is | 2.3 | 67% | 11.3% | 22% | 0.12 | 0.86 |
| offset_corrected | 2.3 | 42% | 24.0% | 34% | 0.17 | 0.74 |
| signed | 2.3 | 41% | 24.9% | 35% | 0.18 | 0.72 |
| as_is | 4.6 | 64% | 10.0% | 26% | 0.27 | 0.69 |
| offset_corrected | 4.6 | 36% | 19.5% | 45% | 0.49 | 0.48 |
| signed | 4.6 | 34% | 20.1% | 46% | 0.52 | 0.46 |

`no_substitution` is identical to `as_is`, and `offset_corrected_no_sub` to `offset_corrected` (the substitution fires on 0.04–0.1% of ticks).

Setpoint at KIGA 4.6:

| Setpoint | as_is: no current / clipped / Z vs true | signed: no current / clipped / Z vs true |
|---|---|---|
| 500 pA | 64% / 10.0% / 0.27 | 34% / 20.1% / 0.52 |
| 250 pA | 80% / 1.8% / 0.18 | 43% / 15.2% / 0.47 |
| 100 pA | **100% / 0.1% / 0.06 (runaway)** | 54% / 9.7% / 0.37 |

### Conclusions

1. The scan-time offset with `abs()` is the main loop defect: removing it cuts no-current time by ~40% and roughly doubles how well Z follows the surface.
2. With the offset removed the loop finds the surface again properly, so clipping rises; a lower setpoint brings it back (signed at 100 pA clips like today's firmware at 500 pA, while following the surface better).
3. **Low-setpoint trap in today's firmware:** below ~170 pA (the phantom 55 counts), lost current reads as "too much current", so the loop retracts without limit once it loses the surface while scanning. Avoid setpoints below ~200 pA until F4 is in.
4. The zero substitution does not affect image quality; change it only for sustained-zero faults.

Run: `python -c "import loop_sim as L; print(L.run('signed', kiga=4.6, amp=15, setpoint_counts=80))"`

## `tracking_sim.py`: stage-tracking (drift lock) controllers on the Oct 22 drift

Truth: Oct 22 #20–#31 drift (0.56 px/s up the frame, ~3.6 px jump at each gain change; optional +30% speed-up after 200 s). Measurements: the patch's offset from its primed reference, only at the times the simulated live band tracker locked on Oct 22 (`live_trail_updates.json`: a seed at 50 s, then 11 locks from ~150 s), noise σ = 3 px. 5 seeds.

| Controller | Patch wander, whole run | Steady state (first lock + 60 s) | Largest offset move |
|---|---|---|---|
| none (today) | 94 px | 115 px (~13 nm) | — |
| step correction at each Y turnaround | 22 px | 24 px | 49 px |
| **alpha-beta with velocity feed-forward** (velocity seeded from the first lock) | **10 px** | **5.8 px (~0.7 nm)** | **15 px** |

Same with the +30% speed-up (5.7 px steady). Conclusion: implement correct mode (G-ST2) as an alpha-beta estimator with continuous feed-forward ramps, seeded from the first whole-sweep lock; avoid per-sweep steps (3× larger moves, 4× worse holding). Output: `tracking_sim.png`, `tracking_sim.json`.
