# Scan data streams: trace, retrace, scan up, scan down

**Status:** started 2026-10-16. The terminology section is a recommendation for the team to agree; the code still uses the older names listed below.

## The short version

Every continuous scan records **four images of the same area** in each complete Y cycle, for both the Z (height) and error (current) channels. Two independent directions combine:

- **Within each row (fast axis, X):** the tip goes left to right, then straight back right to left. These are the **trace** and the **retrace**. Both are recorded.
- **Across the rows (slow axis, Y):** the rows march up the scan area, then turn around and march back down over the same rows. These are **scan up** and **scan down**. Each one is a complete image.

| | Trace (X− → X+) | Retrace (X+ → X−) |
|---|---|---|
| **Scan up** (Y rising) | image 1 | image 2 |
| **Scan down** (Y falling) | image 3 | image 4 |

So "up and down" and "trace and retrace" are separate choices, and every image is one of each.

## How the tip moves

```
 scan up (rows 0 → 255)                 scan down (rows 255 → 0)

 row 255  → → → → → → →  trace           row 255  → → → → → → →  first
          ← ← ← ← ← ← ←  retrace                  ← ← ← ← ← ← ←
   ...         ↑                            ...         ↓
 row 1    → → → → → → →                  row 1    → → → → → → →
          ← ← ← ← ← ← ←                           ← ← ← ← ← ← ←
 row 0    → → → → → → →  start            row 0    → → → → → → →  last
          ← ← ← ← ← ← ←                           ← ← ← ← ← ← ←
         X−            X+                         X−            X+
```

- Each row is a trace out and a retrace back. "Pixels/line" in the GUI counts both, so 512 pixels/line gives a 256 × 256 image.
- Y moves continuously, a tiny step every control tick, so each row tilts by half a row over its length, and the retrace runs half a row above its trace. This is invisible at normal row counts.
- At the top, Y reverses and the same rows are scanned again in the opposite order. The tip never jumps.
- The report's interactive Figure 2 (scan-resolution report, section 1.2) animates this with all four streams coloured.

## What each tool shows

| Tool | What you see | How to get the others |
|---|---|---|
| **Live view** (main GUI) | **Trace only**, Z and error. Scan up and scan down are drawn into the same rows, so the image alternates between image 1 and image 3, shifted by the "drift corr Y" setting | Retrace is kept in saved frames and can be viewed in replay |
| **Sweep player** (replay) | One stream at a time. **Channel** dropdown: `e_trace`, `e_retrace`, `z_trace`, `z_retrace` (error or Z, trace or retrace). **Sweeps** dropdown: both directions, "▲ up only", "▼ down only" | Pick the channel and direction you want; each listed sweep is one scan up or one scan down |
| **Saved frame files** | All four streams, both channels | — |

Neither tool can show trace and retrace together yet; see [TODO item 1](TODO.md#1-compare-trace-and-retrace-side-by-side-live-gui-and-replay).

To compare like with like over time, use **the same channel, trace, and the same scan direction** (for example `e_trace`, "▲ up only"). Trace and retrace differ by hysteresis and feedback lag, and scan up and scan down differ by creep and drift, so mixing them adds differences that aren't on the sample.

## Names: what the code says now, and what we recommend

The same four streams currently have different names in different places, and one of them is the wrong way round:

| Thing | Replay (`sweep_index`, `sweep_player`) | Live raster (`live_raster.py`) | Scan-resolution report | **Recommended** |
|---|---|---|---|---|
| Row direction X− → X+ | `trace` | trace | trace | **trace** (standard SPM term; "forward" in some packages) |
| Row direction X+ → X− | `retrace` | retrace | retrace | **retrace** ("backward" in some packages) |
| Rows advancing, Y DAC rising | "▲ up" (`dir = "up"`) | **"down sweep"** (named from the flipped on-screen view) | Y+ half-sweep | **scan up** |
| Rows returning, Y DAC falling | "▼ down" (`dir = "down"`) | **"up sweep"** | Y− half-sweep | **scan down** |

Recommendation:
1. **Keep "trace" and "retrace"** for the fast axis. They are the standard terms in scanning probe microscopy and our tools already agree on them. Explain once that "retrace" means the return pass, not the tip retracting from the sample.
2. **Use "scan up" and "scan down"** for the slow axis, defined by the hardware: scan up = Y DAC rising. This matches replay's existing ▲/▼ labels and the usual up/down terms in SPM software, so replay needs no change.
3. **Drop "Y+ / Y−"** (used informally in the report) and fix the live raster's names, which are reversed because they were taken from the flipped on-screen picture (code-review item 5d in `docs/meetings/2026-10-streak-followup-plan.md`).
4. **Make the screen agree with the names:** scan up should draw from the bottom of the window to the top in every tool. The display flip should be a separate, labelled option.
5. **Name a stream as direction + pass:** for example "scan up, trace" (image 1) or "scan down, retrace" (image 4). In files and code: `up_trace`, `up_retrace`, `down_trace`, `down_retrace`.

## Where this lives in the code

- `software/pc/qtpanda/replay/sweep_index.py`: splits recordings into sweeps and labels each `up` or `down` from the line counter; `sweep_image()` returns trace or retrace (retrace is put back into X order).
- `software/pc/qtpanda/replay/sweep_player.py`: the channel list (`CHANNELS`) and the direction filter (`DIR_FILTERS`).
- `software/pc/qtpanda/live_raster.py`: the live view; around line 469 it saves the "End of down sweep" snapshot when the line counter crosses the halfway point, which is the reversed naming above.
- Firmware `stm_firmware.hpp`, `controlTick()`: X reflects at its limits every line; Y advances a little every tick and reflects once per half-cycle.
