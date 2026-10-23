# Investigation targets: where does the ~400 µs time constant live?

**Status:** mechanism class identified, location unresolved
**Raised:** 2026-09-18
**Companions:** `preamp-bandwidth-smear.md`, `stretch-compensation.md`

---

## What is actually established

Measured from `2026-Sep-17` frames, independent of any model:

1. **A directional lag exists.** Trace and retrace are displaced in opposite
   directions. Removing the per-line ramp *strengthens* it (correlation gain
   +0.118 → +0.148), so it is not a Z-drift artifact.
2. **The lag is a fixed TIME, not a fixed fraction of the scan range.**

   | era | line rate | measured lag (% of field) |
   |---|---|---|
   | scan1 30 nm, CC **off** | 24.5 Hz | 3.9% |
   | scan1 11.56 nm, CC **off** | 46.3 Hz | 7.0% |
   | scan2 32.98 nm, CC on | 48.8 Hz | 7.8% |

   Double the line rate, double the lag fraction (ratio 2.00 against a
   line-rate ratio of 1.99). A fixed time constant predicts exactly this.

3. **Noise correlation half-length 611 µs**, from the along-row vs across-row
   decomposition — same order as the lag, derived without any lag assumption.

## What this rules OUT

- **Piezo hysteresis.** It is a fixed fraction of range, so it predicts a
  constant percentage regardless of line rate. Measured ratio is 2.0, not 1.0.
- **The Z feedback loop.** The lag appears in the CC-**off** eras too, where
  the loop is not closed at all. (Weak correlation gain there, so treat as
  suggestive rather than conclusive.)
- **Data post-processing.** `SPPX = 0` → one ISR tick per pixel, so no firmware
  pixel averaging. `LRPT` averages passes 20.5 ms apart, which cannot smear
  along a line. `sweep_image()` is a pure reshape with no interpolation, and
  rendering is nearest-neighbour. Decisive check: `z_trace` shows only 2–3 px
  quantisation repeats through the *identical* code path where `e_trace` shows
  730 long clamp runs.
- **Firmware sigma-delta.** First-order, `SIGMA_SHIFT = 4`, one tick ≈ **40 µs**
  — an order of magnitude short of 400 µs.

## What remains — and they are equally likely on current evidence

Everything below produces a fixed time constant and is therefore consistent
with all three measurements above. Nothing in the data distinguishes them.

### A. Preamp electrical (transimpedance stage)

τ = R_f × C_f. R_f = 100 MΩ (`preamp_v_per_a = 1e8`); a few pF of feedback and
stray capacitance gives hundreds of µs. Input capacitance from the tip cable
forces a larger compensation capacitor, so cable length converts directly into
τ.

**Bias note:** earlier write-ups in this folder favoured this explanation
without justification. It is one candidate among several, not the default.

### B. Piezo drive chain (HV amplifier + cabling into a capacitive load)

Completely unexamined so far, and a strong candidate. Piezo capacitance is
commonly 1–100 nF. Driving that through any output series resistance, or
through an HV amplifier that slew-limits into a capacitive load, lands squarely
in the hundreds-of-µs range. The commanded X position would then be correct
while the *actual* voltage on the piezo lags.

### C. Piezo ceramic / mechanical settling

A damped mechanical response or a low stack resonance also gives a fixed time
constant. 400 µs corresponds to ~400 Hz — low for a compact scanner, but
plausible for a large plate/wedge stack like ours
(see `wedge-assembly/`).

### D. ADC sample-and-hold / anti-alias filtering

Least likely given the LTC2326-16's specifications, but not yet excluded by
measurement.

## Inputs to gather

The blocker is missing hardware information, not missing analysis. Nothing
below requires taking the instrument apart.

### Preamp side (candidate A)

- [ ] Feedback resistor: value, package, whether it is a single part or series
      segments
- [ ] Feedback capacitor: value if fitted deliberately
- [ ] Op-amp part number (input capacitance and GBW set the compensation floor)
- [ ] Tip cable: type, length, capacitance per metre (coax is ~100 pF/m)
- [ ] Is the shield driven/bootstrapped or grounded?
- [ ] Physical distance from tip to first stage
- [ ] Schematic or photo of the input stage

### Piezo drive side (candidate B) — **highest value, currently zero data**

- [ ] HV amplifier part number and supply rails
- [ ] Output series resistance between amplifier and piezo (often present for
      stability, and directly sets τ with the piezo's capacitance)
- [ ] Piezo capacitance per axis — measured, or part number + geometry
- [ ] Any deliberate filter on the X drive line
- [ ] Cable length and type from driver to piezo
- [ ] Amplifier slew rate, and its rated capacitive load

### Piezo ceramic (candidate C)

- [ ] PZT formulation / part number
- [ ] Tube or stack geometry and electrode arrangement
- [ ] Mounting stiffness and preload
- [ ] Manufacturer resonance figure, if any

### Already known (no action needed)

- Control ISR 25 kHz / 40 µs; DAC 16-bit over ±5 V
  (`dac_x_v_per_lsb = 1.5259e-4`)
- Position resolution 20-bit, sigma-delta shift 4
- X sensitivity 5.0 nm/V (`piezo_x_nm_per_v`)
- `line_rate_ceiling_hz = 390`

## Experiments, by information gained per unit effort

### 1. Square-wave current injection at the preamp input — **do this first**

Tip stationary, known current step, measure rise time at the ADC. This
exercises **only** the electrical measurement path.

- τ ≈ 400 µs → candidate A confirmed, B and C become irrelevant
- τ ≈ tens of µs → A excluded, and every preamp remedy proposed in
  `preamp-bandwidth-smear.md` is wasted effort

One afternoon. It cleanly halves the hypothesis space.

### 2. Piezo voltage monitoring

Probe the actual voltage at the piezo electrode while commanding an X step, and
compare against the commanded DAC value. Separates candidate B (electrical lag
in the drive) from candidate C (mechanical lag in the ceramic): if the voltage
tracks the command but the image still lags, the delay is mechanical.

### 3. Line-rate sweep with good signal

Image one stable field at 6, 12, 24 and 48 Hz back to back and fit lag vs rate.
Already partly done from archive data, but never as a controlled experiment
with adequate SNR. Confirms the fixed-time-constant model and pins τ far more
precisely than three scattered archive eras can.

### 4. Scan-size sweep at constant line rate

A fixed time constant predicts lag in **nanometres** proportional to scan size
and lag in **percent** constant. Hysteresis predicts the opposite. A second,
independent check on the conclusion already drawn.

## Discrimination table

| observation | preamp RC | drive chain | ceramic mech. | hysteresis | post-proc |
|---|---|---|---|---|---|
| lag ∝ line rate | ✓ | ✓ | ✓ | ✗ | ✗ |
| present with CC off | ✓ | ✓ | ✓ | ✓ | ✗ |
| absent in `z_trace` quantisation | ✓ | ✓ | ✓ | ✓ | ✗ |
| survives ramp removal | ✓ | ✓ | ✓ | ✓ | — |
| **square-wave test slow** | ✓ | ✗ | ✗ | — | — |
| **piezo voltage lags command** | ✗ | ✓ | ✗ | — | — |

The bottom two rows are the experiments that have not been run. Everything
above them is already measured and does not separate the first three columns.

## Consequence for interpretation

Until experiment 1 is run, statements of the form "the preamp is too slow"
should read "**something in the chain has a ~400 µs time constant**". The
remedies differ completely: shorter tip cable and split feedback resistor for
A; series resistance and amplifier headroom for B; mechanical redesign for C.
