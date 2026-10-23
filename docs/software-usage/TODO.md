# Software to-do (operator-facing)

Usability gaps found while using the software. Each item says what is missing, what exists now, and a suggested fix. Add new items at the top.

Related lists (not copied here, to keep one source each):
- Firmware safety and correctness fixes (retract direction, setpoint clamp, BUSY wait, line numbering): `docs/meetings/2026-10-streak-followup-plan.md` §3.
- Bench and hardware experiments: the scan-resolution report, Section 5 action items. The software and firmware ones are items 2–6 below; report item numbers are given as "(report #n)".

## 6. Move or split the per-line USB transmission (report #17)

**Added:** 2026-10-16. **Priority:** low; do only if the report's #10 (STRM 0 / 512 vs 256 px test) shows line-locked marks.

Find out whether sending each finished line over USB leaves a mark in the image. If it does, move the send to the line turnaround or split it across ticks. A whole-frame buffer pushed at the Y turnaround (report #18) needs PSRAM for 1 MB frames and is the fallback.

## 5. DIAG: log the real X extent per line (report #16)

**Added:** 2026-10-16. **Priority:** low, cheap.

**What DIAG does now:** since FW 5.4, `DIAG` reports ISR timing only: `dt_us`, `isr_max_us`, `isr_overruns`, `dropped_lines` (`main.ino:240`). That part is done; it validated the 100 kHz tick on 2026-07-31 and needs no more work.

**What is still missing:** the actual minimum and maximum X DAC codes reached on each line (and the Y range per half-cycle), reported by DIAG or stamped into the line frame. The zoom test (report §3.6, measured ÷ commanded 1.07 and 0.96) has since shown the zoom tracks the command, so this is no longer urgent. It is still worth adding because it checks the commanded size directly instead of through image features, and it would have caught the 16× unit bug of July on the first scan.

**Also for DIAG:** the code review's line-numbering fix (followup plan §3 item 2) suggests a resync-mismatch counter reported here.

## 4. Line rate: round instead of truncate, and show the realized rate (new)

**Added:** 2026-10-16. **Priority:** medium; it silently changed the Sept 24 data.

**The bug:** `updateStepSizes()` (`stm_firmware.hpp:494`) computes samples per pixel as `(unsigned int)(1e6 / (lineRate × dt × pixels))`, which truncates. When the exact answer is a whole number, float error can land just below it and the cast drops a whole sample. At 10 µs ticks and 512 pixels per line, a request of 97.66 Hz gives 1.9999… → 1 sample per pixel, so the scan **ran at 195.3 Hz, twice the request**. On Sept 24, most sweeps ran at 195.3 Hz for this reason.

**Fix:**
1. Firmware: round to nearest (`+ 0.5f`) before the cast.
2. Firmware: echo the realized line rate (`1e6 / (spp × dt × pixels)`) after LRAT, SPPX or pixel changes.
3. GUI and replay: display and record the realized rate next to the requested one, and flag when they differ by more than 1%.

## 3. Line-rate and KIGA helper from the loop simulation (report #3)

**Added:** 2026-10-16. **Priority:** medium; it picks the bench settings before bench time.

The loop simulation and lag/drift trade-off from the scan-resolution report (Section 3.4a, Appendix A) predict the lag tail for any KIGA, line rate and scan size, and give the best line rate, f* = √(vN / (2τL)), about 5–19 Hz with today's numbers. Turn this into a small tool or GUI panel: given scan size, pixels and KIGA, show the predicted lag as a percentage of a row, the suggested line rate, and the realized rate the firmware will actually run (item 4). The analysis scripts are in the 2026-10-15 session scratchpad (`sep24/loop_sim`, `lag_explainer`) and should be moved into the repo first.

**Also needed for it:** a lateral drift measurement in replay (track a feature's position across sweeps). The Sept 24 attempt only bounded drift to 10–60 pm/s, and f* depends on it.

## 2. "Is this surface?" checks in replay (report #15)

**Added:** 2026-10-16. **Priority:** high; highest-impact software item in the report.

Build the report's checks into the sweep player so every image gets them without a custom script:
- **Repeat:** correlation of the same stream across consecutive sweeps.
- **Fold:** trace vs retrace and scan up vs scan down agreement (cancels the feedback lag; see item 1).
- **Both Y halves:** the feature appears in scan up and scan down.
- **Zoom:** the feature scales with the commanded window instead of staying at the same pixel position. This is the check that showed the 10.5 nm "cleanest" image was not surface.

Show a pass/fail line per check next to the A pane. Item 1 (trace and retrace side by side) is the manual first step towards the fold check.

## 1. Compare trace and retrace side by side (live GUI and replay)

**Added:** 2026-10-16. **Priority:** medium.

**Need:** an easy way to look at trace and retrace of the same rows together, in both the live GUI and the sweep player. Trace vs retrace is the main check for feedback lag, hysteresis and tip artefacts (see [01 · Scan data streams](01-scan-data-streams.md)), and right now neither tool makes it easy.

**What exists now:**
- **Live GUI** (`software/pc/qtpanda/live_raster.py`): shows the **trace only**, for Z and error. The retrace images are still built every line (`_img_zr`, `_img_er`, fed by `_z_retrace` / `_e_retrace`) but were taken off-screen on 2026-07-15 because they looked like near-duplicates of the trace (comment near line 362). There is no toggle to bring them back or to switch focus to retrace. The panel label says "(forward trace; retrace kept in saved frames)".
- **Sweep player** (`software/pc/qtpanda/replay/sweep_player.py`): the A and B panes share **one** channel dropdown (`e_trace`, `e_retrace`, `z_trace`, `z_retrace`), so you can see trace or retrace, never both at once. Comparing means flipping the dropdown back and forth.

**Suggested fixes:**
1. **Replay, smallest change:** give pane B its own channel choice, or add a "B = other pass" option, so A can show `z_trace` and B `z_retrace` of the **same** sweep (B follows A, offset 0). Keep the shared histogram so brightness stays comparable.
2. **Replay, better:** a difference view (trace minus retrace, after putting the retrace back in X order, which `sweep_image()` already does) and a line-profile overlay: click a row and plot trace and retrace on one axis. The overlay is the clearest way to see lag, because the retrace profile is shifted by roughly line rate × loop delay.
3. **Live GUI:** a "Show" selector on the raster: trace / retrace / both (both = the old 2 × 2 layout with the retrace twins back on screen). Default stays trace-only, which is why the twins were hidden in July.
4. **Both tools:** a live or replay line-profile strip under the image showing the current row's trace and retrace together. This is the fastest check during a scan, and needs no extra image panes.

**Done when:** from either tool, an operator can see trace and retrace of the same row together in one click, without exporting data.
