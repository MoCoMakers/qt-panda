# PR1: delay or filter? Edge width versus trace/retrace shift (2026-10-23)

**Question.** HY1 found a direction-dependent trace/retrace shift in the error channel that seemed to grow with line speed (~0.3–0.5 ms). SM1 inferred the current-channel preamp must be ≳ 5 kHz, because Sep 24 error images are sharp. A first-order filter both **shifts and blurs** edges by about v·τ; a pure latency or loop lag only **shifts**. Which is it?

**Scripts:** `pr1_calibrate.py` (synthetic edges: metric calibration), `pr1.py` (real data). **Data:** `pr1_calibration.json`, `pr1_results.json`, `pr1.log`.

## 1. The metric is calibrated
On synthetic step edges:
- a first-order filter widens the X edge as expected (intrinsic 1.3 px → 3.7, 7.6, 10.9 px for τ = 2, 5, 10 px of travel);
- a pure latency leaves the width at 1.3 px.

Shift is recovered exactly for latency, and for small filter τ. **The X edge width discriminates filter from latency.**

## 2. Real data
Median 10–90% edge width perpendicular to the edge, over hundreds to ~1,400 edges per group:

| Group | Line period | Tip speed | X edge width | Shift trace vs retrace | Extra width a 0.4 ms filter would add |
|---|---|---|---|---|---|
| Sep 24, 30 nm, CC | 5.1 ms | 11.8 µm/s | **0.26 nm** | −0.46 nm | ~10 nm |
| Sep 24, 27 nm (#1808), CC | 5.1 ms | 10.6 µm/s | **0.57 nm** | −2.76 nm | ~9 nm |
| Sep 24, 50 nm, CC | 5.1 ms | 19.5 µm/s | **0.61 nm** | −2.83 nm | ~17 nm |
| Sep 24, 30 nm, CC | 10.2 ms | 5.9 µm/s | 0.38 nm | −1.08 nm | |
| Sep 24, 30 nm, CC | 30.7 ms | 1.95 µm/s | 0.71 nm | −1.57 nm | |
| Sep 24, 30 nm, constant height | 30.7 ms | 1.95 µm/s | 0.70 nm | −2.69 nm | |
| Oct 22, 30 nm, CC | 97.5 ms | 0.62 µm/s | 0.26 nm | −0.77 nm | |

## 3. Findings
1. **A slow filter on the current channel is ruled out** (confidence high: three independent 5 ms groups, ~2,400 edges, calibrated metric).
   - At the fastest lines the edges stay 0.26–0.61 nm sharp, against the 9–17 nm a 400 Hz filter would add.
   - Even if all the measured width were filter blur, τ ≤ 0.01–0.025 ms, so **preamp f3dB ≳ 6–16 kHz**.
   - This confirms SM1.
2. **The shift is not a consistent latency either** (confidence medium).
   - It stays at ~0.5–2.8 nm while tip speed changes 30×; a time delay would scale with speed.
   - It is also present at constant height (−2.7 nm, no loop).
   - It is better described as a direction-dependent **position offset of ~1–3 nm**: piezo hysteresis or scan nonlinearity, or the Z-channel pixel-indexing question left open by HY1.
   - This reinterprets HY1's "grows with speed" error-channel dome, whose fast-line points ran off its ±16 px search range.
3. **Implications:**
   - Do not apply preamp inversion with τ ≈ 400 µs to real data.
   - The simulator's preamp working value becomes ≥ 6 kHz.
   - The direction-dependent offset is a position effect, and belongs with the hysteresis and lateral-calibration work (HY bench tests).

## 4. Caveats
- **Unreliable groups:** two groups gave implausible values and are excluded (15 ms constant height: +79 px; 20 ms CC: +18.5 px with only 114 edges). Whole-line correlation can lock onto the wrong feature at large lags.
- **Y widths not usable:** Y-direction widths are unreliable as an intrinsic reference (they often fit row-to-row steps), so the bound uses X widths alone. That is conservative.
- **Groups not comparable:** they differ in area, day and tip state.
