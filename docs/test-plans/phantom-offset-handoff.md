# Handoff: the "phantom" ADC offset while scanning

**For:** anyone picking this up without the Oct 22 context. **Status:** open (OI-3 in `2026-10-23-open-issues-and-tests.md`).
**Data:** `TeamUpdate/data/2026-Oct-22/image_stability_1792709026870_s1792709026869.csv` (200 Hz status stream: ADC, Z DAC, feedback and scan flags). Bias DAC 33310 (reported −49.6 mV), setpoint 160 ADC counts (500 pA), preamp 1X.

## 1 · What the ADC is and how the firmware uses it

1. The tunnelling current goes through the preamp into a 16-bit ADC. Reading range −32768 … +32767; +32767 is full scale (clipped, about 102 nA at 1X).
2. Every 10 µs the firmware reads the ADC and computes the feedback error from the **magnitude** of the reading:
   ```
   adc = read_ADC()                                  # signed
   if feedback_on and adc == 0 and Z not at its limit:
       adc = 32767                                   # treat exactly 0 as clipped
   err = setpointLog - logTable[abs(adc)]            # log of |current|
   Z  += Ki * err                                    # err > 0: extend toward the sample
   ```
3. `abs()` exists so the same loop works for either bias polarity (the current's sign follows the bias).
4. Consequence: any offset in the ADC reading is treated as real current, whatever its sign.

## 2 · Objective data points (Oct 22)

"No-current cluster" = samples below −20 counts (tunnelling current reads positive in these conditions).

| # | Condition | Time | Samples | ADC p5 / median / p95 | No-current cluster: share, median (IQR) | Z DAC |
|---|---|---|---|---|---|---|
| A | Tip far, not scanning, feedback off | 19:03–19:04 | 6,299 | −21 / −15 / −6 | 5%, −22 (−22…−21) | 10,000 |
| B | Tip far, not scanning, approach steps | 19:08–19:09 | 6,300 | −29 / −22 / −11 | 63%, −25 (−27…−23) | 10,000 |
| C | **Halted, feedback on, tunnelling** | 19:22–19:24 | 32,250 | +15 / **+184** / +549 | 0% | 25,604 |
| D | Halted holds between KIGA steps | 19:25:39–19:26:10 | 6,200 | −19 / +179 / +4,087 | 4%, −23 | 29,706 |
| E | **Scanning, feedback on, KIGA 2.3** | 19:28:43–19:30:22 | 39,006 | −64 / −46 / 32,767 | **61%, −55 (−60…−49)** | 29,389 |
| F | Scanning, feedback on, KIGA 4.6 | 19:31:00–19:32:40 | 39,337 | −62 / −30 / 32,767 | 53%, −52 (−57…−44) | 33,327 |
| G | **Scanning, feedback on, Z at its extended limit** (surface mostly out of reach) | 19:42–19:51 | 111,523 | −64 / −46 / 5,694 | **60%, −55 (−60…−50)** | ~64,000 |
| H | Scanning, Z fully retracted, ADC reading exactly 0 | 19:51–19:52 | 17,120 | 0 / 0 / 0 | — | 0–1 |

Key observations:
1. **Not scanning** (A, B, C, D), no-current readings sit at **−15 to −25**.
2. **Scanning** (E, F, G), no-current readings sit at **−50 to −64**, about 30–40 counts more negative.
3. G shows it with the surface mostly out of reach, so it is not caused by tunnelling.
4. It appears at every gain tested (E, F; also KIGA 1.14 and 9).
5. H is a separate event: the ADC read exactly 0 for over a minute at the end of the session; the 0 → 32767 substitution then drove Z to full retract. Cause unknown (analog power-down?).

## 3 · Why it matters

1. With `abs()`, a no-current reading of −55 counts as 55 counts of current: a phantom ~170 pA, about a third of the 160 setpoint.
2. When the tip loses the surface during a scan, the loop therefore pushes back toward it only weakly (error ≈ +54,000 instead of ≈ +119,000 for a −15 reading).
3. Clipping pulls back very strongly (error −268,052). An integrator balancing weak push against strong pull spends far more time lost than clipped: a rough model predicts ~5×; observed 8–9×.
4. Both mid-tone and dark pixels become ambiguous: a no-current −55 and a real +55 give the same error value.

## 4 · Hypotheses, each with a test signature

| # | Hypothesis | What it predicts | How to check |
|---|---|---|---|
| H1 | Capacitive pickup from the X/Y scan drive (I = C·dV/dt) | Offset changes sign or size between trace and retrace; scales with line rate | Needs 100 kHz data during scanning, which Oct 22 lacks (raw recorded only while halted; I-9). Bench: T2 at two line rates |
| H2 | Pickup from Z motion (the loop moves Z quickly while scanning) | Offset follows Z velocity; vanishes when Z is held (feedback off) | Bench: T2 retracted scans, feedback off vs on |
| H3 | Ground or reference shift while the scan DACs are active | Constant offset regardless of direction, line rate or Z motion | Bench: T2; also scan with X/Y amplitude zero |

## 5 · Design questions for the group

1. Should the firmware subtract a measured idle offset (per bias polarity) instead of using `abs()`?
2. If the offset is scan-dependent (H1, H2), should it be measured per line (e.g. at the turnaround) and subtracted live, or removed at the source (shielding, layout)?
3. Should the 0 → 32767 substitution stay? It assumes the ADC outputs 0 when clipped, but on Oct 22 clipping read 32767 and the only long run of zeros (H) came at the end of the session. It did retract the tip safely there.
4. Should frame files carry per-pixel counts of clipped and no-current samples, so every image says which pixels were which?
