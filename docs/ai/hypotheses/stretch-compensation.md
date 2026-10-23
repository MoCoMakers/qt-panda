# Can the horizontal smear be undone? Mostly yes — it is convolution, not loss

**Status:** shift correction measured; **does not survive end-to-end testing**

> **Correction 2026-09-18 (same day).** "Level 1 — lag correction (measured,
> works)" below overstates it. A split-half test of the full pipeline puts the
> lag correction's contribution at **+0.006** (0.784 → 0.790) — i.e. nothing.
> Folding trace and retrace already centres the two opposite lags, so the net
> position is right and only the blur remains, which the reproducibility metric
> cannot see. The stages that *do* earn their place are frame registration
> (+0.085) and trace/retrace folding (+0.046); masking clamped samples measured
> **negative** (−0.026). An attempt to build a sharpness metric to catch the
> residual blur failed — at 25× oversampling it scored misalignment as
> "sharper" — and was discarded rather than reported.
**Raised:** 2026-09-18
**Companion:** `preamp-bandwidth-smear.md` (why the smear exists)

---

## The operator's question

> "knowing there is 'wrong sampling' in this stretch, is there like a
> compensation squish we could do to restore good x-y data, or do we suspect we
> swung too quickly in horizontal (aka could not sample fast enough) and we just
> have missing data pockets?"

## Short answer

**Not missing data.** The framing "could not sample fast enough" is backwards:
the ADC sampled *far too fast*, not too slow. Pixel rate is 12.5 kHz against a
preamp corner near 400 Hz — roughly **25× oversampled**. There is no aliasing
and there are no empty pockets. Consecutive pixels are not independent
measurements; about five of them are one measurement, lagged and smeared.

That distinction decides everything:

| mechanism | invertible? | present here |
|---|---|---|
| undersampling / aliasing | **no** — information genuinely gone | not happening |
| low-pass smear (convolution) | **yes**, up to the noise floor | yes, dominant |
| clipping / railing | **no** — nonlinear, destroyed | yes, ~19% of the window |

So most of the image is recoverable. The railed parts are not, ever.

## Why it is a shift, not a squish

A causal filter delays by a fixed time τ. That becomes a fixed *distance* only
where tip velocity is constant. With a triangle X sweep, velocity is constant
through the middle of the line and reverses at the ends, so:

- through the bulk of the line, the correction is a **pure translation**
- near the turnarounds, velocity → 0, so the spatial lag collapses to zero

Hence "squish" is the wrong mental model for the middle of the image and the
right one only at the edges. The clean way to think about it: **resample in
time, not in space.** Every sample already carries its own timestamp, so the
correction is well posed.

## Level 1 — lag correction (measured, works)

Shift trace and retrace toward each other by the measured delay. One global
parameter across all 3,328 lines of the 32.98 nm run:

```
lag   0 px : trace/retrace r = +0.269
lag -10 px : trace/retrace r = +0.402     <- best
```

τ (one-way) = 5 px = 400 µs = 1.29 nm. A ~50% improvement in agreement from a
single number, no per-line fitting.

This is **self-calibrating** and needs no external reference: trace and retrace
image the same ground, so the correct τ is simply the one that maximises their
agreement. It can be re-measured on every scan, and it doubles as an instrument
health metric — if trace/retrace agreement stops improving under any shift,
something other than lag is wrong.

Cost: none. No noise amplification, no model assumptions beyond "the delay is
causal and roughly constant".

## Level 2 — deconvolution (untested, higher ceiling)

A shift fixes *registration* but not *amplitude*: a one-pole low-pass also
attenuates high spatial frequencies. The discrete inverse of a single-pole RC is

```
true[n] ≈ measured[n] + (τ/Δt) · (measured[n] − measured[n−1])
```

which removes the lag **and** restores the attenuated high-frequency content in
one step. With τ/Δt ≈ 5, that boost factor is large.

The catch: it amplifies high-frequency *noise* by the same factor, and because
the data is 25× oversampled, nearly everything above the corner **is** noise.
So it must be regularised — Wiener deconvolution, boosting only where SNR > 1 —
and it should be validated the same way as Level 1: does trace/retrace
agreement improve beyond +0.402? If it does not, the extra complexity is not
earning anything.

Do Level 1 first. It is most of the benefit for none of the risk.

## Level 3 — what cannot be recovered

Wherever the current railed, `err` clipped to the constant −233257 and the
underlying value is gone. Clipping is nonlinear; no inverse filter reconstructs
it. On 2026-Sep-17 that is ~19% of the gif window, and those runs should be
**masked out before any deconvolution**, not fed through it — a clipped plateau
put through a derivative-boosting filter produces spectacular fake edges at both
of its ends.

Detection is exact and cheap: flag runs of samples equal to the clamp constant.

## The better fix: stop needing the correction

Compensation recovers what a better acquisition would never have lost.

1. **Match pixel rate to preamp bandwidth.** At a ~400 Hz corner, useful pixel
   rates are ~800 Hz. Today's is 12.5 kHz. Either slow the line rate or cut
   pixels-per-line — extra pixels beyond the preamp's bandwidth are free noise,
   not free resolution.
2. **Average instead of oversample.** `LRPT` (line repeat) and `SPPX`
   (samples per pixel) both average. Lines are 20.5 ms apart and the noise
   decorrelates within ~1.3 ms, so repeat passes are genuinely independent:
   LRPT 8 buys ≈ 2.8×.
3. **Raise the corner** — shorter tip cable, guarding, lower stray capacitance.
   This is the only option that actually buys resolution rather than trading
   time for it. (Capacitance work deferred by operator 2026-09-18.)

## Suggested implementation order

1. Add τ estimation to the replay tools — maximise trace/retrace correlation
   over a global lag, report τ in px, µs and nm. Read-only, no data touched.
2. Apply the shift as a **display/analysis option**, never to the logged
   `.frames` (same rule `live_raster`'s row-align follows: raw stays verbatim).
3. Add clamp-run masking, since it is needed for honest statistics anyway.
4. Only then consider regularised deconvolution, gated on whether it beats
   +0.402.

## Open questions

- Is τ constant across scan sizes and line rates? Prediction: constant in
  **seconds**, therefore varying in px and nm. Cheap to test on existing data
  from other days.
- How much of τ is electrical (preamp RC) versus mechanical (piezo response)?
  The square-wave injection test in `preamp-bandwidth-smear.md` separates them.
- Does the Z channel show the same lag? It should show *more*, since the
  feedback loop adds its own delay on top.
