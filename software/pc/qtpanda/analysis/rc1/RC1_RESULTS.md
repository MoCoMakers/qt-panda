# RC1 · Combined height on existing v1 recordings (2026-10-23)

**Question.** In simulation, rebuilding height from Z plus the current (h = tip height − gap(I)) recreated a known truth at 0.999, against 0.89 from Z alone (`docs/SIMULATION.md`). Does that gain show up on **real** v1 recordings? Real data has no truth, so the measure is **repeatability** on the same patch: neighbouring same-direction sweeps after alignment, and up/down agreement.

**Scripts:** `rc1_combined.py` (channels, repeat, up/down, figures) and `rc1_weight.py` (weight of the Z term). **Outputs:** `rc1_results.json`, `rc1_weight.json`, `rc1_channels.png`, `rc1_repeat.png`.

## Method (v1 approximation, assumption A5)

v1 frames hold the per-pixel **mean** z_pos and **mean** error, where error = setpointLog − logTable[\|adc\|].
- Mean log-current ≈ (setpointLog − error)/LOG_K.
- Gap = (ln(V/R_c) − ln I)/2κ, with κ = 1.025/Å, R_c = 12.9 kΩ, V = 49.6 mV and I = counts × 3.125 pA.
- Tip = −z·g, with g = 0.00063 Å per unit.
- Every channel is line-levelled (offset and slope per line) and folded: (trace + retrace)/2.

**Variants:**
- **masked:** drop pixels whose implied \|adc\| ≤ 64 (no-current level) or ≥ 32000 (clipped);
- **preamp-inverted:** first-order inversion along each line's time order, τ = 400 µs, at pixel level;
- **"no profile":** the mean row profile (the line-locked pattern) removed, because a pattern fixed in the scan frame repeats whether or not it is surface.

**Alignment:**
- Sep 24: phase correlation on the error channel, with the same shift applied to every channel.
- Oct 22: report v2's line-by-line drift registration (scratchpad `v2_core.py`; drift model `model_metrics.json`).

## Results (median correlation)

| Data | Usable current | Tip term rms / gap term rms | Z | Error | **Combined** | Combined, masked | Combined, preamp-inverted |
|---|---|---|---|---|---|---|---|
| Sep 24 #1802–#1812, 27.1 nm: repeat | 50% | 0.04 / 0.86 Å | 0.94 | 0.79 | **0.78** | 0.31 | 0.19 |
| same: up/down | | | 0.50 | 0.42 | 0.41 | 0.14 | 0.08 |
| Sep 24 #1586–#1599, 24.8 nm: repeat | 44% | 0.07 / 0.84 Å | 0.85 | 0.89 | **0.89** | 0.61 | 0.31 |
| same: up/down | | | 0.11 | 0.26 | 0.26 | 0.15 | 0.05 |
| Oct 22 #20–#31, 30 nm: repeat | 27% | 1.64 / 1.04 Å | 0.29 | 0.36 | **0.33** | 0.09 | 0.08 |
| same: up/down | | | 0.34 | 0.42 | 0.38 | 0.13 | 0.14 |

With the line-locked profile removed (repeat, median):

| Data | Z | Error | Combined |
|---|---|---|---|
| Sep 24 #1802–#1812 | 0.88 | 0.76 | 0.75 |
| Sep 24 #1586–#1599 | 0.84 | 0.86 | 0.85 |
| Oct 22 #20–#31 | 0.22 | 0.34 | 0.29 |

Weight sweep, h_w = w·tip − gap (repeat, median):

| w | 0 | 0.25 | 0.5 | 1 | 2 | 4 | 8 | 16 |
|---|---|---|---|---|---|---|---|---|
| Sep 24 #1802–#1812 | 0.787 | 0.786 | 0.785 | 0.783 | 0.779 | 0.770 | 0.749 | 0.692 |
| Oct 22 #20–#31 | 0.359 | 0.355 | 0.349 | 0.334 | 0.335 | 0.322 | 0.305 | 0.296 |

## Findings

1. **On v1 data the combined height does not beat the error channel.** It reproduces it.
   - On Sep 24 the Z term is ~20× smaller than the gap term (0.04–0.07 vs ~0.85 Å rms), so combined ≈ error (0.78 vs 0.79; 0.89 vs 0.89). The loop barely moved Z within a line. This matches the Oct 15 finding that Z carries only tilt and the morphology sits in the error channel.
   - On Oct 22 the Z term is larger, and adding it **lowers** the repeat (0.36 → 0.33).
2. **Adding Z never helps:** repeat falls monotonically as its weight grows, on both days. In these recordings Z and the gap term are not two consistent views of one height. Z holds the line-locked lag pattern and slow-axis structure; error holds the morphology.
3. **Z's high repeat on Sep 24 #1802–#1812 (0.94) is mostly the line-locked lag band:** the vertical bright band in `rc1_channels.png`, the Oct 15 rank-1 artefact. It falls to 0.88 with the profile removed, and its up/down agreement is only 0.50.
4. **Half the Sep 24 pixels carry no usable current** (44–50% within the no-current to clipped window; Oct 22: 27%). In `rc1_channels.png` the masked panels lose the lower terraces entirely: the loop did not hold the current there, so those pixels read the no-current level. That is **real information loss in the recordings**, which no reconstruction can recover. The simulator's 0.999 assumed current in range almost everywhere.
5. **Masking and pixel-level preamp inversion make things worse on v1 data.**
   - Masking removes half the image, which ruins alignment-based correlation.
   - Inverting a per-pixel *mean of logs* with an assumed τ amplifies noise.

   Both need what v1 frames lack: signed current with the offset removed, valid/clipped/lost counts per bin, and exact per-tick timing (frame format v2, `docs/test-plans/data-pipeline-v2-design.md`).

## What this means

- **The simulation's gain does not transfer to v1 recordings**, for three reasons:
  - abs() folds no-current ticks (phantom offset ≈ −55 counts) into "current";
  - there are no per-bin validity counts;
  - most importantly, the loop let the current leave the measurable range over half the image.

  The combined estimate is only as good as the fraction of samples whose current is in range.
- **On existing data, the error channel is already the best single morphology channel.** The combined height adds nothing and Z subtracts. Keep using the error channel for v1 analysis (consistent with D27).
- **For new data, the order that matters:**
  1. keep the current in range: gain, line rate, setpoint, and the offset fix (F4);
  2. record signed current and validity per bin (frame v2);
  3. measure the preamp bandwidth (CN5).

  Only then can the combined estimate add the Z information.

## Caveats

- **A5 is a strong approximation:** a mean of logs is not the log of a mean, abs() contaminates, and v1 has no clip or loss counts.
- **Sep 24 alignment uses the error channel's shift for every channel.** That could favour error slightly, but Z still wins one set (27.1 nm) on raw repeat.
- **κ, g and τ are assumed** (`docs/PHYSICS_MODELS.md`). Only the ratio g·2κ sets the Z-term weight, and the weight sweep shows no weight helps.
- **Oct 22 is a damaged tip.**
- Repeatability rewards anything stable, including scan-fixed patterns. The "no profile" rows reduce, but do not remove, that bias.
