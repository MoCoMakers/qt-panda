# Review log

Append one entry per agent-review pass. Entries are the audit trail showing
the graphics were checked for professionalism, scientific accuracy, and
presentation before the report was considered done.

---

## 2026-06-25 — query `tip-displacement-length` (θ=2°, L=1 & 10 mm)

Reviewer: Claude Code (Opus 4.8), reading each PNG directly.

### Pass 1
| figure | verdict | notes |
|---|---|---|
| bars.png | PASS | Clean grouped bars, value labels, correct magnitudes (34.90 / 348.99 / 0.61 / 6.09 µm). |
| length_sweep.png | PASS | Linear scaling clear; markers at L=1,10 mm match table. |
| angle_sweep.png | PASS | Log-y appropriate; operating point at 2° marked; both curves correct. |
| geometry.png | **FAIL** | (1) Top Δx annotations collided with the title and legend. (2) The 1 mm tip was hidden under the 10 mm tip — true-scale tilt at 2° is invisible. (3) Annotations overlapped each other. |

Action: redesigned `fig_geometry_schematic` → two panels (one per length),
tilt drawn exaggerated to 18° **and labelled as such**, tips normalised to
equal length, displacement arrows + non-overlapping Δx/Δz callouts.

### Pass 2
| figure | verdict | notes |
|---|---|---|
| geometry.png | minor | Layout fixed, but "ideal axis" label overlapped the Δx callout, and the bottom note was clipped at both edges. |

Action: moved "ideal axis" label to mid-height (rotated, left of the dashed
line); shortened the footnote so it fits within the figure width.

### Pass 3
| figure | verdict | notes |
|---|---|---|
| geometry.png | PASS | No collisions; caption fully visible; exaggeration clearly labelled; values exact. |

Result: all four figures pass all three criteria. Scientific accuracy
double-checked against closed form: Δx = L·sin2° → 1 mm = 34.899 µm,
10 mm = 348.995 µm; Δz = L(1−cos2°) → 0.609 / 6.092 µm. ✔

---

## 2026-06-25 — query `thermal-displacement-gold` (Au, T=293 K)

Reviewer: Claude Code (Opus 4.8), reading each PNG directly.

### Pass 1
| figure | verdict | notes |
|---|---|---|
| distribution.png | **minor** | Left Gaussian + right Maxwell both correct; but the "most probable" marker label overlapped the curve crest in the right panel. |
| temperature.png | PASS | Classical √T vs full Debye diverge at low T showing the zero-point floor (5.8 pm); room-T and melting-point markers clean, no collisions. |
| scale.png | PASS | Atom (r=144 pm) and neighbour drawn to scale at the density-derived 288 pm spacing; tiny 15.5 pm RMS envelope clearly called out; Lindemann note correct. |
| lindemann.png | PASS | Ratio crosses the 10–15% melt band exactly at Tm (11.4%); room-T at 5.4%. |

Action: moved the three magnitude-marker labels (most-probable/mean/rms) into a
colour-coded stacked block in the upper-right corner, away from the curve.

### Pass 2
| figure | verdict | notes |
|---|---|---|
| distribution.png | PASS | No overlap; labels carry both value and formula (√2σ, √(8/π)σ, √3σ). |

Scientific accuracy cross-checks (all ✔):
- nn spacing from **density** (19.30 g/cm³): n = ρN_A/M = 5.90e28 /m³ →
  FCC a = 407.7 pm → d_nn = 288.3 pm (matches literature 288.4 pm).
- Room-T: mean |u| = 14.3 pm, 3-D RMS = 15.5 pm, σ/axis = 9.0 pm
  (per-axis matches X-ray Debye–Waller ⟨u²⟩ for Au, ~8.5 pm).
- Classical (15.45 pm) vs full quantum Debye (15.52 pm) agree to <0.5% at 293 K
  (T > Θ_D = 165 K); zero-point floor 5.8 pm at 0 K.
- Lindemann ratio = 0.114 at Tm = 1337 K → matches empirical 10–15% melt rule.

## 2026-07-06 — wedge-lever-gearing (initial build)

Reviewed 4 figures against CHECKLIST.md:
- `geometry.png` — PASS (minor label crowding near piezo center accepted; schematic to scale).
- `length_sweep.png` — FAIL→FIXED: "best documented longboard" reference label was hidden
  behind the legend (upper-left). Moved right-aligned under its guide line.
- `wedge_sizes.png` — FAIL→FIXED (2 passes): legend overlapped M10/M16 bar value labels →
  ylim 0–22 + 3-column upper-center legend; "~1 nm tunneling window" caption crossed the
  M8 bar → white backing box.
- `budget.png` — PASS.

Numbers cross-checked by hand: 122.07 × tan(7.26°) × (56.65/72.65) = 12.13 nm/step ✓;
lever ratios 0.780/0.827/0.870 ✓.

## 2026-07-06 — wedge-lever-gearing (as-built v14 refresh)

Report updated to the as-built configuration (lid lip rides the wedge, d_w=120.15 mm →
9.92 nm/step; ratio 0.638; full-run 2.23 mm; contact 1.67°). Table gained an AS-BUILT
row; summary/findings/schematic/references rewritten; `length_sweep.png` gained a green
as-built star marker with annotation — reviewed, no overlaps, PASS. Other 3 figures
unchanged from previous PASS state.

## 2026-07-07 — wedge-lever-gearing (session-8 as-built REDO, step-by-step)

Full rebuild at user request ("use this rig exactly as we have it now; clearer,
step-by-step; the figure is bad"). Physics updated to the measured WedgeDesign v37:
RACK_PITCH 3.00→π (Pinion_v3 = true involute m=1 z=10 → 31.4159 mm/rev), lever
r_p 76.65→76.26 (disc axis as seated), wedge angle = atan(3.5/27.5) = 7.2527°.
Report restructured as a linear 4-stage chain (motor → pinion/rack → wedge → lever),
nominal AND true-gearbox columns.

Figures reviewed against CHECKLIST.md:
- `chain.png` (NEW, lead figure) — FAIL→FIXED: stage-2 value collided with its
  right-aligned label → values moved above bar ends. PASS.
- `geometry.png` (rebuilt as-built) — FAIL→FIXED (2 passes): lid rotated the WRONG
  direction (dipped into the sample plate; rotation sign), title clipped, collet label
  crossed the sample-plate text. Now drawn TO SCALE at the true 1.669° contact pose
  (lip corner exactly on the 3.5 mm crest), labels separated. PASS.
- `budget.png` (rebuilt as-built) — PASS: cumulative line 0→3,585 steps → 2.221 mm
  with handoff-zone shading; log bars as-built (24/81 steps) vs leadscrew (1,521/5,071).
- `wedge_sizes.png`, `length_sweep.png` — retitled APPENDIX (design space, leadscrew
  baseline); as-built star re-keyed to leadscrew drive at the measured geometry
  (9.86 nm/step). PASS.

Numbers cross-checked by hand: 31,415,927 nm/4096 = 7,669.9 ✓; ×0.127273 = 976.2 ✓;
×(76.26/120.15 = 0.63470) = 619.6 nm/step ✓ (true gearbox 4075.77 → 622.7 ✓);
Abbe 976.2×8/120.15 = 65.0 ✓; 27.5 mm/7.6699 µm = 3,585.4 steps ✓;
full range 3.5×0.6347 = 2.221 mm ✓; leadscrew 122.07×0.127273×0.63470 = 9.861 ✓.

---

## 2026-07-15 — query `scan-dwell-fidelity` (30 nm region, 5 configurations)

Reviewer: Claude Code (Fable 5), reading each PNG directly.

### Pass 1
| figure | verdict | notes |
|---|---|---|
| blur_vs_linerate.png | **minor** | 48.8 Hz config label clipped at the right axes edge. |
| mtf.png | **minor** | Title second line clipped right; "MTF = 0.5" label clipped at the left edge. |
| snr.png | **FAIL** | Low-spp cluster labels collided (legacy vs 48.8 Hz vs SPPX 5); legacy label overlapped the y-axis label. |
| step_edge.png | PASS | Both panels correct; 1 pF vs 10 pF contrast clear; blur values in legend match table. |
| speed_limit.png | PASS | Log-y curves correct (d_min = 1.814 vτ inverted); config lines labelled without collisions. |

Action: right-aligned the fastest config's annotation (blur fig); shortened the
MTF title and moved the 0.5 label inside via the y-axis transform; SNR figure
switched to short colour-keyed annotations ("spp N → SNR M") with a marker
legend carrying the full config names.

### Pass 2
| figure | verdict | notes |
|---|---|---|
| blur_vs_linerate.png | PASS | Label inside the axes; slight brush with the C=3 pF curve but fully legible. |
| mtf.png | PASS | Title fits; MTF=0.5 label inside; curves cut at each config's Nyquist floor as captioned. |
| snr.png | PASS | No collisions; all five configs identifiable via the legend. |

Result: five figures pass all three criteria. Scientific spot-checks: f3dB(1 pF)
= 1/(2π·1e8·1e-12) = 1591.5 Hz ✔; 30 Hz × 512 px → spp trunc(1.628) = 1 → true
rate 1e6/(40·512) = 48.83 Hz ✔ (matches the firmware behaviour observed on the
bench); v(48.83 Hz, 30 nm) = 2930 nm/s → blur 0.293 nm @1 pF, 2.93 nm @10 pF ✔;
d_min = π·v·τ/√3 = 0.531 nm @1 pF ✔; SNR(1 nA, spp 1) = 320/5 = 64 ✔.
Honest-verdict note: the model CORRECTS the original bench hypothesis — at
nominal 1 pF the preamp does not erase 30 nm-scale morphology; the C
measurement (RAWD FFT roll-off) is flagged as the deciding experiment.
