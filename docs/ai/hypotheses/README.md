# Hypotheses

Bench observations worked up into testable claims, with the measurement that
supports them and the experiment that would settle them. Written to be picked
up weeks later — each one states its status, its numbers, and what is still
open.

These are **hypotheses, not conclusions.** Where a number is inferred rather
than measured directly, it says so.

| doc | claim | status |
|---|---|---|
| [`preamp-bandwidth-smear.md`](preamp-bandwidth-smear.md) | The horizontal streaks are bandwidth smear — the tip sweeps X faster than the measurement chain can follow — not bad pixels, ADC faults or rendering | smear established; **preamp attribution retracted** |
| [`stretch-compensation.md`](stretch-compensation.md) | That smear is convolution, not lost data, and a shift recovers much of it | shift real, but **worth +0.006 end-to-end** — registration and folding are what help |
| [`time-artifacts-piezo-vs-preamp.md`](time-artifacts-piezo-vs-preamp.md) | The ~400 µs delay is a fixed time constant (hysteresis and post-processing ruled out), but preamp / piezo drive chain / ceramic are indistinguishable on current data | **open — start here**; lists the hardware inputs to gather |

**Read the corrections.** The first two documents carry same-day correction
notices at the top where later measurement contradicted the original claim.
They are kept rather than rewritten so the reasoning trail stays visible.

## Conventions

- State the **observation** in the operator's own words before interpreting it.
- Give the **measurement**, with the script or data path, not just the conclusion.
- Name the **one experiment** that would settle the question.
- Flag anything **deferred** explicitly, with the date, so it reads as a
  decision rather than an omission.
