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
