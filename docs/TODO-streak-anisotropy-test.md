# TODO — streak anisotropy test: temporal vs spatial (preamp discriminator)

Status: **proposed, not yet run** (concept note, 2026-07-27)
Context: single-row horizontal streaks/blobs in open-loop constant-height
scans (canonical example: `TeamUpdate/data/2026-Jul-16/scan_1784247518574.frames`,
sweeps #38▲/#39▼, 1 nm view, 20.45 ms/line). Question: are the streaks
temporal events (junction telegraph + preamp bandwidth smear) or spatial
surface features? The answer decides how much the new preamp
(higher bandwidth + dynamic range) will fix vs what needs CC + drift settling.

## Hypothesis

Streak length is set by event *duration* (~ms), not by feature *size*.
If so: streak length is constant in **milliseconds** across scan sizes and
line rates, and scales proportionally in **nm** with scan speed.

## Test 1 — replay only, no bench time

In sweep_player, measure typical streak length (px) for:
- a 1 nm scan (e.g. the file above) and a 30 nm scan from the same era.
- Convert: px × dwell (fast axis: line_period / pixels_per_line per px;
  at 30 Hz / 512 px ≈ 65 µs/px trace).
- **Temporal** verdict: lengths agree in ms (≈0.5–3 ms expected), differ ~30× in nm.
- **Spatial** verdict: lengths agree in nm, differ in ms.

## Test 2 — bench A/B, same area, one knob

Same region, same bias/setpoint; halve the line rate (30 → 15 Hz):
- Temporal streaks halve in *pixel* length; spatial features stay put.
- Bonus: engage the FW 5.2 constant-current loop on one pass — if rows
  become vertically continuous, single-row-ness was the Z window
  (jitter ~48 pm RMS vs 4 pm row step), not Y drift.

## Test 3 — drift by cross-sweep blob registration (quantified 2026-07-27)

Method: match a compact blob between a consecutive up/down sweep pair;
drift = Δ(commanded position) / Δ(wall-clock) between observations.
Worked example (sweeps #38/#39 above, "circled element"):
A (row 228, col 15) → B (row 97, col 5); Δt = 3.79 s
→ displacement ≈ 0.51 nm (Y-dominant), drift ≈ 0.135 nm/s,
≈ 0.71× the slow-axis scan velocity (0.191 nm/s) — see analysis note in
session log. Repeat over several pairs to get a drift-vs-time curve
(creep decay after approach).

## Expected outcomes / decision

- Mostly temporal → new preamp attacks streak smear + rail clipping;
  keep 1 nm frames but expect single-row blobs until CC is engaged.
- Mostly spatial → XY calibration is suspect (~5× if 11 px pitch is a
  0.25 nm lattice); prioritize calibration scan on known lattice.
