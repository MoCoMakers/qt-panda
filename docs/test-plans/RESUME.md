# Resume here (living)

**Purpose:** if a session ends mid-work, the next one starts from this file. Update it after every step.
**Last updated:** 2026-10-23, session building the approved software items.

## Where things stand

- **Git:** `main` = `origin/main` at `89da33b` (three "before changes" milestone commits by the operator: GUI settings store/defaults, replay, docs). New work is uncommitted until the operator commits it; Claude never commits.
- **Firmware:** source = FW 5.6 (`90aae7c`) + uncommitted F2 retract fix (not flashed). Flashed version not confirmed since Sep 24 (send `VERS` at the next session).
- **Plans:** `docs/test-plans/roadmap.html` (scored items, start here), `docs/test-plans/2026-10-23-open-issues-and-tests.md` (detail), `docs/test-plans/phantom-offset-handoff.md`.
- **Shared report:** v2 https://claude.ai/artifact/LqRJEE9pjqCwkczBi2iM6p (local `TeamUpdate/data/2026-Oct-22/report_v2/`); v1 https://claude.ai/artifact/9aZPBvpbLL48iMj1j89Rxy is the frozen reference (local `report/`). Do not republish v1.

## Work queue for this session (simulation first, then build + test on the emulator)

| # | Item | Roadmap ID | Status | Notes / where |
|---|---|---|---|---|
| 0 | Move scratchpad tools into the repo | — | **done** | `software/pc/qtpanda/analysis/` (`fiducial_drift.py`, `oct22/` archive, README) |
| 1 | Feedback-loop simulator: test abs()/offset and zero-substitution fixes before touching firmware | F4, I-1 | **done** | `analysis/sim/loop_sim.py` + README: offset fix wins; low-setpoint trap found (< ~170 pA) |
| 2 | Stage-tracking controller simulation (replay Oct 22 with a virtual lock) | G-ST1/2 | **done** | `analysis/sim/tracking_sim.py`: alpha-beta + feed-forward holds ~0.7 nm; step correction 4× worse |
| 3 | RTRC → fully retracted, integrator synced (approved) | F2 | **built, flash pending** | `stm_firmware.hpp` `retract()` → DAC 0 + `z_pos`/`iTermISR` = −MAX; emulator RTRC → Z 0; `tests/test_retract.py` (2 tests) pass; compile clean (59.5 KB). Flash only with the operator, then verify: RTRC from Z≈30k → status Z = 0 |
| 4 | Explicit scan mode at RUN + sustained-clip guard at fixed Z | F1 | **built, bench check pending** | `clip_guard.py` + `tests/test_clip_guard.py` (10 pass); `main.py` RUN mode dialog + `_clip_guard_tick`; `copilot_bridge.py` `/scan/run` needs `mode` when CC off; offscreen GUI check 16/16 (scratchpad `gui_f1_check.py`, `gui_f1_dialog.py`) |
| 5 | Display convention: dark = valleys (live + replay) | I-10 | **built** (report figures pending) | `live_raster.py` (`_z_display`/`_e_display`, "Peaks bright" checkbox, ini key `peaks_bright`), `replay/sweep_player.py` (`_disp`, "peaks bright"); offscreen check 10/10 (scratchpad `gui_i10_check.py`) |
| 6 | Report revision for first-time team members (operator feedback 2026-10-23) | — | **done** (artifact v3) | all 9 checklist points; builders in `analysis/oct22/` (`revise_v3.py`, `live_trail_frame.py`) |

## Item 6: report revision checklist (operator feedback)

1. Linear, self-contained progression for someone with no data familiarity: say which day and which sweeps every section uses (e.g. "Oct 22, sweeps #20–#31") and add a short orientation section first (what was done that day, what the instrument is, how to read the images).
2. F2: next to the drift-trail GIF, same timing, show the whole frame with the drift-carried circle and the detected contour (the operator's original bearing for path tracing).
3. Remove the image-autocorrelation figure (C3); keep one sentence that it ruled out a double tip.
4. C4: repeat the top-row image strip from C below the 3D-form figures as a reminder.
5. "First pass (superseded)": state what is still worth keeping or relevant, and what is superseded.
6. Rename "Gap calculator: bias, current and tip height" to "EXTRA: Gap calculator: bias, current and tip height".
7. Rewrite figure captions as self-contained science captions: what is shown, the take-home message, what to look at (e.g. Figure 6 is too literal).
8. Explain in K why KIGA 2.3 looks smooth and symmetric while 4.6 looks rougher yet is recommended.
9. Keep the local copy (`TeamUpdate/data/2026-Oct-22/report/`) + REPORT-TEXT.md in sync and republish to the same URL.

## Rules that apply

- Never commit; prepare commit groups and commands for the operator.
- Test on the emulator (`software/pc/qtpanda/emulator/`, `socket://127.0.0.1:9000`) before hardware. No flashing or hardware actuation without the operator.
- Every change gets a test and a line here.

## Log

- 2026-10-23: tools copied to `software/pc/qtpanda/analysis/`; resume doc created.
- 2026-10-23: loop simulator built and calibrated (Oct 22 stats reproduced at both gains). Offset removal: no-current 64%→34%, Z tracking 0.27→0.52 at KIGA 4.6; clipping doubles unless setpoint lowered. Found: today's firmware runs away below ~170 pA setpoint. Plan OI-2.9 + safety rule 0.7 + roadmap F4/I-1 updated.
- 2026-10-23: tracking controller simulated on Oct 22 drift + lock times: alpha-beta with velocity feed-forward (seeded at first lock) → 5.8 px steady rms, moves ≤ 15 px; per-sweep step → 24 px, 49 px moves; none → 115 px. Plan OI-8.4, roadmap G-ST2 updated.
- 2026-10-23: operator feedback on the report queued as item 6 (9-point checklist). Continuing item 3 (RTRC) first.
- 2026-10-23: F2 built. retract() now drives Z to DAC 0 (slider "Away") and syncs the integrator; emulator mirrors; tests/test_retract.py passes; compile-only check clean. Plan + roadmap (F2 "built, flash pending") updated. Next: item 6 (report revision), then items 4, 5.
- 2026-10-23: item 6 done. Report v3 published to the same URL: Section 0 orientation + day table, Data line per section, D→C→K→F→Q order, take-home captions, F2 two-panel GIF (trail + whole frame with carried circle and contour, same frames), C3 autocorr figure removed, C4 reminder strip, K card on 2.3 vs 4.6, first-pass relevance card, EXTRA gap calculator (roadmap). Local copy + REPORT-TEXT regenerated. Next: item 4 (F1), then 5 (I-10).
- 2026-10-23: F1 built. RUN with CC off asks for the mode (GUI dialog / copilot `mode`), engage path runs only if ENGA took; clip guard halts + retracts 2000 codes/s at sustained clip with CC off. Unit + offscreen GUI checks pass. Full suite: 5 failures pre-exist at HEAD (calibration field count, frame_logger wrap, 3 superscan) plus one flaky frame_logger test; none touch F1. Next: item 5 (I-10).
- 2026-10-23: I-10 built in live raster and replay (peaks bright by default, raw on untick; exports TIFF/GSF raw). Incident: the first I-10 harness run wrote the operator's real `qtpanda.ini` (Row align persisted off; previous value unknown). Harnesses now set `QTPANDA_SETTINGS` to a scratch ini; real ini verified unchanged on re-run. Queue items 0–6 done except bench checks (F2 flash, F1 bench) and report figures under I-10.
- 2026-10-23: report v2 published as a NEW artifact (v1 untouched by operator request): line-by-line drift registration (up/down agreement 0.42→0.49 error), peaks bright, dot = summit → hollow (#22 centre ~50 counts no current, rim ~31,800 clipped; hollow test 94–100th pct #21–#26 in error, not in Z), registered 3D height (mound_v5). Pending: drift-registered replay mode in sweep_player (proposed, not built).
- 2026-10-23: banding check (OI-14 note): no overlay tone; broadband line-to-line jitter, 39% of slow-axis Z power at 2–4-row periods. F6 cross-hatch currently ranks 40/48 (score 6, M7, go/no-go open). Roadmap + v2 tables got a plain 1..N count column next to IDs; roadmap safety rules updated for F1/F2 built. v2 republished (version 2).
- 2026-10-23: scan-path design agreed (SPTH firmware modes, bit-exact generators, simulate first). Added roadmap F8 (tick timestamps, approved), F9 (refuse DACX/DACY while scanning, DACZ under CC), SP1 (scan paths).
- 2026-10-23: OI-16 Z drift added (operator: Z component unmapped, may overlap Z thermal). First split on Oct 22: same-sample Z +39 codes/s, tilt part -7 codes/s; roadmap ZD1.
- 2026-10-23: docs updated: scan-path-design.md (experimental option, principles: named paths in code, no orphan frames, bit-exact, versioned generators), open-issues §6 learnings + §6.1 priorities, OI-17, I-11..I-13, roadmap SP0/I-11, F6 merged into SP1, backlog scan-path section.
- 2026-10-23: scan_paths.py (raster bit-exact vs literal FW port; custom file of raster bit-exact; transforms; spirals/loops/spokes/rose; 18 tests). Simulator scan_sim.py + truths.py (Sep 24 last good-tip day; synthetic). Back-test: tilt reproduced, scan-synchronous trace/retrace dome NOT (OI-18); phantom offset does not flip with direction. Found: line-number slip = hidden 2-row up/down offset (R19); sidecar spp wrong at 100 kHz; PC frame times batched. Comparison batch compare_paths.py running.
- 2026-10-23: comparison batch 1 had two bugs, both fixed: loop restarted per frame in the simulator (faked offsets in pairs) and int64 overflow in fermat/rose generators at full size (new tests). Validation gate (custom-file raster == raster) passed on both truths. Batch re-running; viewer builder analysis/sim/build_paths_viewer.py ready.
- 2026-10-23: comparison complete + speed-matched controls; viewer analysis/sim/scan_paths_viewer.html opened in Edge. Findings in scan-path-design §8.2: validation gate passed; drift removal dominant; speed (not shape) decides fidelity at equal time; curved paths remove streaks and resonance drive; cross-hatch best pair; loops/spokes/rose leave gaps.
- 2026-10-23: operator rejected the smooth Sep 24 Z truth; re-ran on Sep 24 #1808 ERROR channel (operator's pick). Viewer now shows both cross-hatch frames (paths + per-frame reconstructions); findings rewritten; opened in Edge. Results in scan-path-design §8.3.
- 2026-10-23: operator expects ~99% recreation of a theoretical truth. Added the combined height estimate (Z + current: h = tip - gap(I)) to scan_sim and a verification ladder (analysis/sim/ladder.py: L0 geometry -> L7 full physics, one effect at a time). Smoke test: Z-only 0.43 vs combined 0.940 = geometry limit. Full ladder running.
- 2026-10-23: audit of past work (Oct 15 report, streak plan): added CR1-CR7 (code-review fixes not individually tracked) and CN1-CN7 (concepts: Lc window, zoom-scaling acceptance test, 3 Hz wobble, switch-off checks, 400 us question, index bugs, rail headroom); corrected OI-18 (dome = Oct 15 rank-1 feedback lag; simulator gap) and credited line-number slip / spp bug to earlier reviews. Plan section 6.2.
- 2026-10-23: audit part 2 (software-usage/TODO, research harness, hypotheses): added CR8 (round spp, realised line rate), CR9 (trace/retrace side by side); CN5 now names the preamp f3dB measurement; deconvolution logged in backlog.
- 2026-10-23: ladder done (scan-path-design 8.4): reconstruction exact (99.9%) where physics known; Z-only loses (0.89); remaining losses = curved-path binning (fix: interpolate), preamp lag (fix: invert filter), lateral piezo (needs calibration). ladder_fixes.py running.
- 2026-10-23: new docs/SIMULATION.md and docs/PHYSICS_MODELS.md (model registry with status, hysteresis section, common STM practice). Reconstruction final: combined Z+current, masked preamp inversion (19 ticks), drop invalid ticks, hybrid gridding -> >=0.99 on both truths with full physics + calibrated positions. Roadmap HY1-HY4, RC1. Comparison batch re-running with final reconstruction.
- 2026-10-23: final comparison: all paths >= 0.99 with full physics + calibrated positions (raster 0.995 #1808, 0.991 synthetic; custom = raster identical); viewer rebuilt (findings rewritten); SIMULATION.md section 5 updated.
- 2026-10-23: docs/DECISIONS.md (decision log D1-D34 + assumptions register A1-A11) and data-pipeline-v2-design.md (frame v2, shared reconstruction, Run mode for live+replay, mode-first settings) written; roadmap PL1-PL3, UI1. Offline HY1 (hysteresis) and RC1 (combined height on real data) running in background; outputs in analysis/hysteresis/ and analysis/rc1/.
- 2026-10-23: RC1 done (analysis/rc1/RC1_RESULTS.md): combined height on v1 frames = error channel, no gain; only 44-50% usable current on Sep 24 vs ~100% in simulation -> simulator optimistic (A12), next fix SM1. D35-D36 added. HY1 still running.
- 2026-10-23: SM1 (analysis/sim/sm1_*): at Sep 24 settings Z flat (matches real); sharp real error images imply preamp >= ~5 kHz, contradicting the 400 Hz assumption (A4); usable-current mismatch persists (A12). Waiting on HY1.
- 2026-10-23: HY1 done (analysis/hysteresis/HY1_RESULTS.md): constant-height mid-line separation ~3% (0-6%) -> 5% plausible; my earlier 'much smaller' claim was wrong (line average). Error channel has a speed-dependent ~0.3-0.5 ms shift, conflicting with SM1's >=5 kHz inference -> PR1 (edge width vs shift). Z flat -7% offset unresolved. Hysteresis sensitivity (1/5/12%) running.
- 2026-10-23: hysteresis sensitivity: commanded positions 0.869/0.785/0.706 at 1/5/12% (actual 0.994-0.996); lateral dynamics (assumed resonance + amp) cost ~13 points even at 1%. SIMULATION 5.3, PHYSICS_MODELS updated. PR1 still running.
- 2026-10-23: D37 readiness split proposed (infrastructure now; modelled corrections behind switches until bench-confirmed).

## Pipeline v2 build (approved 2026-10-23; plan: pipeline-v2-build-plan.md)

| Step | What | Status |
|---|---|---|
| 0 | PR1 write-up + docs (preamp >= 6-16 kHz; shift = position offset); D34 resolved, D38 | done |
| 1 | B4 reconstruct.py + equivalence gates 1-4; B5 migrations; B7 index version | done (2026-10-23) |
| 2 | A1-A11 firmware + emulator, compile checks, PDMP vectors | next |
| 3 | B1-B3 v2 decode/log/timebase vs emulator | queued |
| 4 | B6 Run mode; C0 mockup -> operator checkpoint -> C1-C5 | queued |
| 5 | Operator bench: flash FW 5.7, gates on hardware | operator |
- 2026-10-23: KPGA bug assessed against all journals: historical data not affected (A13); fix A7 in FW 5.7.
- 2026-10-23: step 1 progress: reconstruct.py + equivalence gates pass (stamped identical on all 32 recordings; corrected = truth on port data). D39 frozen sweep numbering, D40 deterministic GUI hooks. Next: gate 2 (LiveFold vs LiveRaster), gate 4 (display fns), then B5 migrations.
- 2026-10-23: step 1 DONE. Live raster, sweep_index (INDEX_VERSION 2, rebuilds old indexes), sweep_player ("rows" combo: slip-corrected default / stamped revert; `--stamped` CLI), superscan.fold_frame, replay_frames.rebuild_images all on reconstruct.py; lattice_fft inherits via sweep_index (stamped rows). `write_index` writes `<base>.corrections.json` (affected sweeps, examples, revert); build_index stays read-only. CR7: sidecar spp from control_rate_hz + SPPX (+ isr_rate_hz, realised_line_rate_hz, image_height, settings_version 2); raw_scan_reconstruct takes isr_hz (no fixed 40 us). Gates: numbering identical to existing on-disk indexes on all 32 recordings; frozen references for live raster, sweep_image, build_sweeps, replay_frames. Suite: 114 pass + 5 known pre-existing failures. Pre-migration backups in session scratchpad. On-disk indexes rebuild (and change-logs appear) the first time the player/sweep_index opens each day.
