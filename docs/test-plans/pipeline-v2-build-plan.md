# Plan: unified scan pipeline v2: build everything now, behind toggles

## Context
Today's session established, through simulation and offline analysis, what the instrument's data path needs:
- an exact time base (microcontroller ticks);
- richer line frames (signed current, valid/clipped/lost counts);
- a correct line index (the R19 slip shifts every up/down pair by 2 rows);
- auditable scan paths (`scan_paths.py`, bit-exact, 22 tests);
- a reconstruction that can use Z + current;
- one shared pipeline for the live view and replay.

The audits also found real bugs:
- HALT never parks X/Y; RUN jumps X/Y to the corner in one tick.
- `emitPendingLine` can tear or drop lines.
- KPGA alone zeroes the integral gain.
- The sidecar records samples/pixel 4× low (40 µs hard-code at `main.py:3747`, `raw_scan_reconstruct.py:99`).
- The line-to-row fold is copied 6× (`live_raster.py:485-527`, `replay/sweep_index.py:130,196-212`, `superscan.py:27-65`, `replay_frames.py:27-63`, `main.py:3527`, `lattice_fft.py`), and live and replay disagree on what "up" means.
- The emulator has no 'S' frames and wraps line numbers at 0xFFFF.

**Operator direction (2026-10-23).** Build everything now.
- **Default route** = today's scanning, reproduced exactly.
- **Everything that needs testing** (scan paths, combined height, modelled corrections) is selectable through options.
- **Backbone pieces** cut over to the new methods, each with an equivalence test against the old method.

Decisions D16–D37 in `docs/DECISIONS.md` govern this.

## Principles
1. **Default = today.** With every toggle at its default, firmware positions, line timing and the images shown are identical to FW 5.6 / the current GUI (proved by tests, §Verification).
2. **Toggles are explicit and recorded.** Every option (firmware or PC) is written into the recording sidecar and into each image's provenance. The GUI labels experimental options.
3. **Backbone cut-over = new code plus an equivalence gate.** Each replaced function keeps its old implementation in tests as the reference until the gate passes on emulator data and on all recorded days.
4. **Firmware:** compile-checked, emulator-mirrored, flashed only with the operator (D4); one flash for the whole milestone.
5. Decisions go to `docs/DECISIONS.md` as they are made (D15); no git commits by Claude (D13).

## A. Firmware FW 5.7 (`software/firmware/arduinosrc/main/`), mirrored in `software/pc/qtpanda/emulator/firmware_emulator.py`

| ID | Change | Default | Kind |
|---|---|---|---|
| A1 | `volatile uint32_t tickCount` incremented at the top of `controlTick` after the `blockISRControl` return; boot ID (u16 from the hardware RNG) at `setup()`; VERS caps add `TICK,LFMT2,SPTH,PROT2,PDMP` | always on (no effect on existing frames) | backbone |
| A2 | Line frame v2, new magic `'V'` (`binary_frame.hpp`, `line_buffer.hpp`, `writePixel`). Header: u16 line, u16 bins, u32 tick at the first bin, u16 boot ID, u8 flags (crosshatch swap, pass, torn, path id), u16 sequence. Per bin: i32 z, i32 err, i32 Σ signed ADC, i32 Σ logTable over valid ticks, u8 n_valid, u8 n_clip, u8 n_lost. `LFMT 1\|2` selects v1 `'L'` (default) or v2 `'V'`. Thresholds via `VTHR lo hi` (defaults 64 / 32000) | `LFMT 1` until the cut-over gate passes, then 2 | backbone (gated) |
| A3 | R19 line-number fix: stamp the line before applying the Y-bottom resync (`stm_firmware.hpp:287-301` vs `:405-422`). The v2 header also carries the tick, so the segment index = tick ÷ (spp × bins) | fixed | backbone |
| A4 | CR3: torn/dropped lines. Sequence-check the buffer swap in `emitPendingLine` (`stm:643-652`), set the torn flag, never clear the next line's `sendData` | fixed | backbone |
| A5 | F9: DACX/DACY refused while scanning, DACZ refused while PID is on → reply `ERR busy <cmd>` (`main.ino:41-52`) | on | backbone (safety) |
| A6 | CR1: ramp X/Y to the scan start at RUN (speed-limited, before scanning begins) and park at the offsets on HALT (`stm:562-577`) | on | backbone (the image is unchanged after the ramp) |
| A7 | KPGA/KIGA consistency: initialise `Ki` from `Ki_isr`, so KPGA alone keeps the integral (`stm:138,205,634`) | fixed | bug |
| A8 | CR8: echo the realised line rate after LRAT/IPLN/SPPX/SETD/LRPT (`RATE <hz> SPP <n>`); rounding mode `SPPR 0\|1` (0 = truncate, today) | echo on; `SPPR 0` | backbone (echo) / toggle (rounding) |
| A9 | CR2: newline-terminated commands with `OK <cmd>` / `ERR` replies when `PROT 2` (4-char commands still accepted) | `PROT 1` | toggle → backbone after the GUI gate |
| A10 | SPTH scan-path modes: case 0 = today's step-1 code moved verbatim. Modes: rotation (Q15 cos/sin), transpose sequence (cross-hatch at frame end), Archimedean/Fermat spirals, centre-return loops, spokes, rose. Integer phase counters and a sine table generated from `scan_paths.SIN_TABLE`. `PDMP n` dumps (tick, x_pos, y_pos) for tests. `SPTH` is refused while scanning | mode 0 | experimental |
| A11 | DIAG: cycle-counter ISR timing (`ARM_DWT_CYCCNT`) plus tick and boot ID | on | backbone |

**Emulator:**
- 'V' and 'S' frames (`STRM`), the line-number behaviour per firmware version, and LRPT/SPPX/RAWD handlers.
- SPTH via `scan_paths` (the emulator computes positions with the same Python code).
- Line wrap at bins, not 0xFFFF.

## B. PC backbone (`software/pc/qtpanda/`)

| ID | Change | Gate |
|---|---|---|
| B1 | `serial_reader.py`: decode `'V'` into a `LineRecord` dataclass (line, z, err, optional tick/boot/flags/seq/sums/counts). New signal `lineRecord(object)`; keep `lineFrame(int, z, err)` for v1-compatible consumers | the existing reader tests pass unchanged; golden 'V' tests (new builder in `tests/conftest.py`) |
| B2 | `frame_logger.py` v2: record magic `'G'` storing every LineRecord field + pc_time. `read_frames()` still yields `(t, line, z, e)` for any version; new `read_records()`. Sidecar `format_version: 2`, firmware VERS, boot ID, `scan_path` block (`scan_paths.make_block`), `image_height`, the **real** settings: spp from `control_rate_hz` + SPPX + the firmware echo (fixes `main.py:3747`), calibration, toggle states | the same stream logged v1 vs v2 → `read_frames` identical |
| B3 | `timebase.py`: per-boot epochs, robust fit pc = a + b·tick, 32-bit unwrap; v1 falls back to pc times | unit tests with simulated resets and wraps |
| B4 | `reconstruct.py` (the shared "Run"):<br>• `Run(block, spec)`, with `add_record()` (live) and `from_frames()` (replay); raster fold via the `scan_paths` map (segment = line); per-sweep images (z/err trace/retrace; optional height, validity, coverage); sweep segmentation (replaces `sweep_index` logic).<br>• Pure display functions moved from `live_raster.py:22-57,238-245,612-622` (row align, peaks bright, linearise).<br>• Options: `line_index` = `stamped` (default for v1) / `slip_corrected` / `tick` (v2); drift registration (line by line); `height` (Z + current; v2 exact, v1 approximate, labelled); `preamp_inverse`; `lateral_model`; `zdrift`. Each defaults to today's behaviour | **Equivalence gate 1:** in `line_index=stamped` mode, pixel-identical (incl. NaN masks) to `sweep_index.sweep_image` on every recorded `.frames` (all days); `slip_corrected` mode = stamped mode remapped by the documented rule (test), with the change-log written. **Gate 2:** identical to the `live_raster` buffers fed the same lines (drift 0). **Gate 3:** identical to `superscan.fold_frame` / `replay_frames.rebuild_images`. **Gate 4:** display functions identical to the old ones |
| B5 | Migrate the consumers to B4:<br>• `live_raster` (keeps the widget, delegates fold/transforms);<br>• `replay/sweep_index` + `sweep_player.DayData.image`;<br>• `superscan`;<br>• `replay_frames`;<br>• `lattice_fft`;<br>• `raw_scan_reconstruct` (fix the 40 µs).<br>Up/down naming per D9 (fix the live raster's reversed snapshot keys) | gates 1–4 re-run after migration; the existing tests pass |
| B6 | Replay "Run" mode: `sweep_player` renders through the B4 Run with the same option model as live; `replay_frames.replay_live` uses it too | replay of an emulator session == the live buffers captured during it |
| B7 | `sweep_index` index version field; rebuild on version change | the new `tests/test_sweep_index.py` |

## C. GUI (`main.py`, `live_raster.py`, `replay/sweep_player.py`, `copilot_bridge.py`); no `ui_form` regeneration

| ID | Change |
|---|---|
| C0 | **Mockup first (UI1):** an offscreen screenshot of the new panel, using the `analysis/oct22/mock_stage_tracking_v3.py` pattern, before building C1. Operator checkpoint |
| C1 | Continuous Scan: a new "Scan" group box at the front of `top_row` (before `geo_box`, `main.py:2998`). Contents:<br>• **Scan path combo first** (Raster default; others marked experimental, enabled only when VERS caps include SPTH, or on the emulator);<br>• common settings (the existing `geo_form` widgets);<br>• a `QStackedWidget` of mode settings;<br>• derived read-only numbers: realised rate (firmware echo), tip speed, px/atom across/along, frame time, coverage, drive near 158.7 Hz (via `scan_paths` + `analysis/sim/scan_sim.scores` kinematics).<br>`_on_cs_apply_settings` / `_cs_start_run` send SPTH/LFMT and write the `scan_path` block |
| C2 | Live non-raster display: gridding through the B4 Run, coverage overlay; `LiveRaster` takes a Run/Spec instead of the hard-coded `n//2, n` (`main.py:3226,3319`) |
| C3 | Channel/option toggles shared by live and replay: Height (Z + current), validity colours (v2 counts), drift-registered view, preamp inversion, lateral correction, Z-drift removal; each labelled "experimental" or "default" and written to provenance |
| C4 | Fixes: right-click recenter X (`live_raster.py:664-679`, CR6); a geometry change mid-scan → HALT/RUN (CR5); live naming per D9 |
| C5 | Copilot bridge: `/scan/path` get/set, and `mode` + path in `/scan/run` |

## D. Docs (as work lands)
- **DECISIONS.md:** each cut-over and toggle default.
- **Design docs:**
  - `data-pipeline-v2-design.md`: final frame v2 layout;
  - `scan-path-design.md`: SPTH command spec;
  - `SIMULATION.md` / `PHYSICS_MODELS.md`, where options map to models.
- **Operational:** RESUME after each step; `analysis/sim/README` links.

## Operator answers (2026-10-23), built into this plan
1. **Legacy line numbers: correct them, with a revert trail.** The slip mechanism is proven (literal firmware port + real Oct 22 stamps …510, 0, 1… then …511, 0…), so for v1 recordings the default `line_index` = `slip_corrected`.
   - **Rule:** the first Y-cycle after RUN, the second stamp 0 = line bins−1; afterwards, stamped − 1 (mod bins).
   - **Trail:** every corrected recording gets a change-log sidecar `<base>.corrections.json` recording:
     - the rule and the algorithm version;
     - the affected sweeps and lines, with the stamped → corrected mapping;
     - the date.
   - **Raw `.frames` are never modified.**
   - **Revert:** set `line_index = stamped` (per view or globally), which reproduces the old images exactly (gate 1 runs in stamped mode).
   - **Index version:** sweep indexes get a version bump, so they rebuild.
   - **Decision entry:** D34 resolved in DECISIONS.md. Reports already published keep their old images (v1/v2 artifacts noted).
2. **Frame format:** firmware emits v2 by default **after** the bench gate passes; v1 stays selectable (`LFMT 1`) and readable.
3. **Mockup first:** C0 is a hard checkpoint before C1–C5; backbone and firmware work continue meanwhile.

## Step 0 (carry-over, docs only)
- **PR1:** write `software/pc/qtpanda/analysis/pr1/PR1_RESULTS.md` from `pr1_results.json`. Findings:
  - the current channel's preamp f3dB ≳ 6–16 kHz (edges stay 0.26–0.61 nm sharp at 10–20 µm/s, where a 400 Hz filter would add 9–17 nm);
  - the trace/retrace shift is a ~1–3 nm direction-dependent **position offset**, not a latency (it holds across a 30× speed range, including constant height).
- **Record PR1 in the docs:** PHYSICS_MODELS §2/§5, DECISIONS A4 (resolved: not a slow filter) and A3 (the offset feeds hysteresis), SIMULATION §5.2 note.
- **Simulator:** set the preamp working value to ≥ 6 kHz in `analysis/sim/scan_sim.py` PHYS (re-run the ladder later).

## Order (each step ends with its gate green)
1. B4 + its equivalence gates against the existing recordings and code (pure PC, no behaviour change). Then B5 migrations (gates re-run), B7.
2. A1–A11 in firmware + emulator; compile-only checks; `PDMP` position dumps against `scan_paths` (bit-exact, modes 0 and all SPTH).
3. B1–B3 (v2 decode/log/timebase) against the emulator: v1 vs v2 logs → `read_frames` identical; `tick` line index == `slip_corrected` index.
4. B6 Run mode; then C0 mockup → operator checkpoint → C1–C5.
5. Operator bench session: flash FW 5.7; verify VERS/DIAG; RUN with defaults → images match a FW 5.6-style reference scan; switch on LFMT 2 → gate (`read_frames` identical); then exercise toggles (SPTH modes, PROT 2, SPPR 1) one at a time.

## Verification
- `pytest software/pc/qtpanda/tests` (existing suite; the 5 known pre-existing failures stay documented), plus the new tests:
  - `test_reconstruct_equivalence.py` (gates 1–4 on synthetic and on all `TeamUpdate/data/*/*.frames`, skipping if absent);
  - `test_frame_v2.py` (golden 'V', logger v1/v2 equivalence);
  - `test_timebase.py`;
  - `test_sweep_index.py`;
  - `test_emulator_pipeline.py` (emulator RUN → logger → Run → replay == live);
  - `test_scan_paths.py` extended with firmware `PDMP` vectors from the emulator.
- Firmware: `arduino-cli compile` (bundled CLI, `teensy:avr:teensy41`, the `--libraries` flag). No upload without the operator.
- Offscreen GUI checks with `QTPANDA_SETTINGS` pointing at a scratch ini (memory rule): the panel builds, the combo toggles the stacked settings, apply sends the expected commands to a fake serial.
- Bench (operator): defaults reproduce today's scanning; each toggle exercised and recorded.

## Critical files
- **Firmware:** `stm_firmware.hpp`, `main.ino`, `binary_frame.hpp`, `line_buffer.hpp`.
- **Emulator:** `emulator/firmware_emulator.py`.
- **PC data path:** `serial_reader.py`, `scan_controller.py`, `frame_logger.py`, new `reconstruct.py` and `timebase.py`.
- **Consumers:** `live_raster.py`, `replay/sweep_index.py`, `replay/sweep_player.py`, `superscan.py`, `replay_frames.py`, `lattice_fft.py`, `raw_scan_reconstruct.py`.
- **GUI and bridge:** `main.py` (`_build_continuous_scan_tab` :2857, `_on_cs_apply_settings` :3298, `_scan_frame_settings` :3744), `copilot_bridge.py`.
- **Tests:** `tests/conftest.py` + the new test files.
- **Reuse:** `scan_paths.py` (`make_block`, `read_block`, `reconstruct`, `SIN_TABLE`, `FirmwareRasterRef`), `analysis/sim/scan_sim.py` (gridding, combined height, scores).

## Risks
- **USB bandwidth for v2 at fast lines** (~19 B/bin: 196 lines/s × 512 bins ≈ 1.9 MB/s). The Teensy native USB copes; the PC read stalls seen with security software could drop lines. Mitigation: torn/drop flags (A4), v2 opt-in until checked.
- **Shared control:** never restart the operator's GUI without asking; test offscreen.
- **The analysis scripts' hand-rolled `.frames` parsers** (`analysis/oct22/ki_ladder.py`, `ladder_analysis.py`) still read v1 only; v2 files carry a different record magic, so they fail loudly rather than misread.
