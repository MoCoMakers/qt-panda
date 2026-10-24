"""Consolidated roadmap -> roadmap.html. Edit GOALS / MS / I / SESSIONS below, then run: python build_roadmap.py"""
import json, html

import os
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "roadmap.html")

GOALS = [
    ("G1", "Resolve real surface structure at ≤ 10 nm windows", "Images whose features repeat after drift correction (≥ 0.7) and scale correctly with zoom."),
    ("G2", "Safe, repeatable automated scanning", "AI-driven sweeps on request, with guards; no tip crashes from procedure."),
    ("G3", "Trustworthy numbers", "Calibrated nm, a known meaning for every colour, clean signal chain."),
    ("G4", "Drift-locked imaging", "Stage tracking that measures drift live and, when in-zone, holds the patch in place."),
]
MS = [
    ("M1", "Safety and control", "Firmware/GUI fixes that make automated runs safe: retract direction, RUN needs feedback, setpoint clamp, KIGA-only changes, line numbering."),
    ("M2", "Diagnostics session (bench A)", "What dark means, the phantom offset, the 158.7 Hz source. No imaging quality needed."),
    ("M3", "Signal integrity", "Offset/abs() handling, zero substitution, raw-capture losses, colour scaling."),
    ("M4", "Imaging session (bench B)", "KIGA retest done properly, gap-resistance ladder, setpoint steps, 10-minute hold. Needs a recovered tip."),
    ("M5", "Stage tracking", "Monitor mode in the GUI first, then correction with an in-zone gate."),
    ("M6", "Calibration and zoom", "Known-lattice calibration, then graded zoom ladders."),
    ("M7", "Streak suppression and scan paths", "Cross-hatch pairs, streak anisotropy test, slower/adaptive lines; experimental scan paths (rotated, spiral, centre-return, rose) behind an option."),
    ("M8", "Mechanics", "158.7 Hz mode, isolation, cables, stiffer head."),
]
# id, title, type, milestone, status, lead, ease, impact, source, next / notes
# Scores 1-3: lead = likely to find or fix a main limit; ease = 3 analysis/setting, 2 bench/small code, 1 hardware/large firmware;
# impact = how much a positive result changes design or defaults. "orig" = Oct 15 report total, where it exists.
I = [
    # ---- Oct 15 resolution report action items
    ("R1", "KIGA sweep on one area", "bench", "M4", "first pass done", 3, 3, 3, "Oct 15 report #1 (9)", "Oct 22: 4.6 last stable, 9 oscillated; confounded by crashed tip and restarts → retest T3"),
    ("R2", "Slower lines (≤ 10 Hz)", "bench", "M4", "partial", 3, 3, 3, "Oct 15 #2 (9); streak plan 2b", "Oct 22 ran ~10.5 Hz only. Streak plan 2b grid still to run: 32.55 / 10.28 / 5.01 / 3.005 / 2.83 / 3.20 Hz (3 Hz brackets the ~3 Hz row wobble, CN3); add 5 Hz at KIGA 4.6 in T3"),
    ("R3", "Loop simulation to pick settings", "analysis", "M4", "available", 3, 3, 2, "Oct 15 #3 (8)", "Use before T3"),
    ("R4", "Halted tunnelling raw captures", "bench", "M2", "done", 3, 3, 3, "Oct 15 #4 (8)", "Oct 22 holds identified 158.7 Hz"),
    ("R5", "Tap test (lever, plate, frame, table)", "bench", "M8", "planned", 3, 3, 3, "Oct 15 #5 (9)", "= T7"),
    ("R6", "Isolation-plate friction test", "bench", "M8", "planned", 2, 3, 2, "Oct 15 #6 (8)", "With T7"),
    ("R7", "384 px scan to split 159.5 vs 231 Hz", "analysis", "M8", "superseded", 1, 3, 1, "Oct 15 #7 (6)", "Halted holds show 158.7 Hz directly"),
    ("R8", "Sound sweep 100–300 Hz near the rig", "bench", "M8", "planned", 2, 3, 2, "Oct 15 #8 (7)", "With T7"),
    ("R9", "Laptop on battery (ground loop)", "bench", "M3", "planned", 2, 3, 2, "Oct 15 #9 (6)", "With T2"),
    ("R10", "Status stream off; pixel-count A/B", "bench", "M3", "planned", 1, 3, 2, "Oct 15 #10 (5)", "With T2"),
    ("R11", "Non-tunnelling scan (electrical pickup)", "bench", "M3", "planned", 3, 3, 3, "Oct 15 #11 (5)", "Now also the phantom-offset test = T2"),
    ("R12", "Graded zoom ladders", "bench", "M6", "planned", 2, 2, 2, "Oct 15 #12 (6)", "After T8"),
    ("R13", "Lateral calibration on a known lattice", "bench", "M6", "planned", 2, 2, 3, "Oct 15 #13 (6)", "= T8"),
    ("R14", "Z sine-sweep (transfer function)", "firmware", "M8", "not started", 3, 1, 3, "Oct 15 #14 (8)", "Firmware milestone"),
    ("R15", "Fold / repeat / both-halves / zoom checks in replay", "analysis", "M5", "partial", 3, 2, 3, "Oct 15 #15 (7)", "Fiducial drift tool built; integrate into replay"),
    ("R16", "Log real X min/max per line (DIAG)", "firmware", "M1", "not started", 1, 2, 2, "Oct 15 #16 (5)", ""),
    ("R17", "Move/split per-line USB transmission", "firmware", "M3", "not started", 1, 2, 1, "Oct 15 #17 (4)", "After OI-11"),
    ("R18", "Whole-frame buffer push", "firmware", "M3", "not started", 1, 1, 1, "Oct 15 #18 (3)", "Only if R17 shows an effect"),
    ("R19", "Code-review fixes (retract, setpoint clamp, BUSY, line numbering)", "firmware", "M1", "open", 2, 2, 3, "Oct 15 #19 (5); streak plan items 1–3", "Before long automated runs. Retract done as F2. Line numbering = streak plan item 2 (found Oct 1 with fwsim.py); confirmed in Oct 22 recordings 2026-10-23 (first cycle …510, 0, 1…; later every line +1). After the fix, recalibrate drift_corr_y (−4 may absorb 2 rows) and decide the +1 correction for old .frames. SETD floor 10 µs + ADC BUSY check"),
    ("R20", "Softer / strain-relieved cables", "hardware", "M8", "not started", 2, 2, 2, "Oct 15 #20 (6)", ""),
    ("R21", "Stiffer head (wedge assembly)", "hardware", "M8", "future", 3, 1, 3, "Oct 15 #21 (6)", ""),
    ("R22", "Document isolation box, preamp version and gain", "doc", "M3", "open", 1, 3, 2, "Oct 15 #22 (5)", ""),
    # ---- new bench tests
    ("T1", "What dark means (Z steps, feedback off)", "bench", "M2", "planned", 3, 3, 3, "test plan T1", "Decides how every image is read"),
    ("T2", "Phantom offset (retracted-tip scans)", "bench", "M2", "planned", 3, 3, 3, "test plan T2; phantom-offset handoff", "Trace vs retrace, line rate, Z motion; needs I-9 for in-line detail"),
    ("T3", "KIGA retest, continuous scanning, KIGA-only changes", "bench", "M4", "planned", 3, 2, 3, "test plan T3", "Needs recovered tip, KIGA-only command"),
    ("T4", "Gap-resistance ladder (1 GΩ → 14 MΩ)", "bench", "M4", "planned", 3, 2, 3, "test plan T4", "Tests 'lower bias = better precision'"),
    ("T5", "Setpoint-step contour calibration", "bench", "M4", "planned", 2, 3, 2, "test plan T5", "Controlled 3D contour stack"),
    ("T6", "10-minute hold with tracking (monitor)", "bench", "M5", "planned", 2, 3, 2, "test plan T6", ""),
    ("T7", "158.7 Hz source (taps, damping, mass)", "bench", "M8", "planned", 3, 3, 3, "test plan T7", "Covers R5, R6, R8"),
    ("T8", "Lateral and Z calibration", "bench", "M6", "planned", 2, 2, 3, "test plan T8", "Covers R13"),
    ("T9", "Raw-capture losses vs security software", "bench", "M3", "planned", 2, 2, 1, "test plan T9", "Needs an IT decision"),
    # ---- firmware / GUI work
    ("F1", "Explicit scan mode at RUN (constant current or constant height on purpose) + clip guard when Z is fixed", "GUI", "M1", "built, bench check pending", 3, 3, 3, "Oct 22 crash; test plan §0.2", "Built 2026-10-23: RUN with feedback off asks for the mode (engage then run, or constant height on purpose; copilot /scan/run needs mode cc|ch); clip guard (clip_guard.py, checkbox default on) halts + steps Z away 2000 codes/s while clipped at fixed Z, stands down under CC/approach. Tests: tests/test_clip_guard.py + offscreen GUI check. Bench: confirm on the next parked tunnelling"),
    ("F2", "RTRC button: do what the live-scan Z slider does when pulled fully to Away (Z to its retracted end), instead of jumping to DAC 50000", "firmware", "M1", "built, flash pending", 2, 2, 3, "streak plan item 1; stm_firmware.hpp:604", "Lower Z = away (Oct 22 data, GUI slider labels); RTRC jumps to 50000, toward the sample whenever Z is below it (tunnelling Z was 25k–38k). The GUI Z slider is fine. Built 2026-10-23: retract() writes DAC 0 + syncs the integrator; emulator + tests/test_retract.py; compile clean; flash with the operator"),
    ("F3", "AI tooling: change Ki live without halting, as the operator does", "AI tooling", "M1", "open", 2, 3, 2, "OI-6, I-5", "Not a firmware/GUI gap: the Oct 22 script halted and re-sent everything; the operator keeps scanning"),
    ("F4", "ADC offset instead of abs(); revisit 0→32767", "firmware", "M3", "open", 3, 2, 3, "OI-2, OI-3, I-8; analysis/sim", "Simulated: no-current 64%→34%, Z tracking 0.27→0.52 at KIGA 4.6; pair with a lower setpoint to hold clipping; T2 confirms the offset model"),
    ("F5", "Per-pixel clipped / no-current counts in frames", "firmware", "M3", "open", 2, 2, 2, "OI-4", ""),
    ("F6", "Cross-hatch scanning (SWXY)", "firmware", "M7", "merged into SP1 (sequence)", 2, 1, 3, "streak plan §4; OI-14", "Now the cross-hatch sequence of SP1: fast axis swaps between frames on the same area; merged with line-by-line drift registration. Oct 22 banding is broadband line-to-line jitter (OI-14), which this targets"),
    ("F7", "Live raster up/down naming matches replay", "GUI", "M1", "open", 1, 3, 1, "streak plan 5d", ""),
    ("F8", "Tick-count timestamps in line frames, status and settings acks; cycle-counter ISR timing in DIAG", "firmware", "M1", "approved (operator 2026-10-23)", 3, 2, 3, "scan-path determinism audit 2026-10-23", "Ticks are the exact time base (PC receive times jitter by ms). Line header gets a 32-bit tick; settings changes ack with the tick they took effect; DIAG uses the cycle counter (micros() is 1 µs coarse). Versioned via VERS caps; decoders accept old and new. Bundle with the F2 flash"),
    ("F9", "Refuse DACX/DACY during continuous scan and DACZ while CC owns Z", "firmware", "M1", "open", 2, 3, 2, "scan-path determinism audit 2026-10-23", "Today such a write lands for one 10 µs tick, then the ISR overwrites it (and status shows the stale value briefly). Reply with a refusal line instead; GUI greys the sliders in those states"),
    ("ZD1", "Map the Z drift: same-sample Z rate vs tilt part, gain vs time, temperature, settling vs thermal", "measurement", "M5", "first split done", 3, 2, 3, "OI-16; operator 2026-10-23", "Oct 22: same-sample +39 codes/s (gap opens), tilt part -7 codes/s; gain and time confounded. Next: alternate-gain session, T6 holds after motor moves, temperature logging, Z calibration"),
    ("CR1", "Ramp X/Y to the scan start at RUN and park on HALT; report X/Y in the status frame", "firmware", "M1", "open", 2, 2, 3, "streak plan item 5 (high)", "Today X/Y jump to the scan corner in one tick at RUN and are not parked on HALT; the GUI X/Y mirror drifts from the real DACs after HALT, grid spectroscopy or TEST"),
    ("CR2", "Newline-terminated commands with echo / ERR reply (parser resync)", "firmware", "M1", "open", 2, 2, 3, "streak plan 5c", "A dropped byte desynchronises the 4-character parser silently; AI-run sweeps need every command confirmed"),
    ("CR3", "Detect torn / garbled scan lines (sequence-check the buffer swap); show dropped rows", "firmware", "M3", "open", 2, 2, 2, "streak plan 5b", "A USB stall can send a garbled line and drop the next; Sep 24 real run had 1634 dropped lines; torn lines look like streaks"),
    ("CR4", "KIGA in units of 1/s (SETD currently changes the loop gain)", "firmware", "M1", "open", 2, 2, 2, "streak plan item 5", "Gain is applied per ISR tick, so changing the tick period silently rescales KIGA"),
    ("CR5", "Geometry change mid-scan: GUI does HALT -> RUN, or firmware refuses", "GUI", "M3", "open", 1, 2, 2, "streak plan item 5", "Leaves the trace/retrace split misaligned until the next RUN"),
    ("CR6", "Right-click recenter off in X by up to a quarter scan (live_raster.py)", "GUI", "M3", "open", 1, 3, 1, "streak plan item 5 (quick)", "px/self._half − 0.5"),
    ("CR7", "Recordings store the real scan settings (samples/pixel recorded 4× low; requested, not real, line rate)", "GUI", "M1", "open", 3, 3, 3, "streak plan item 5; confirmed 2026-10-23 (Oct 22 sidecar: 4 vs 19)", "Part of the no-orphan-frames contract; with F8 the firmware echoes its settings"),
    ("CR8", "Line rate: round samples/pixel instead of truncating; echo and record the realised rate", "firmware", "M1", "open", 2, 3, 2, "software-usage/TODO.md #4 (2026-10-16)", "Truncation silently changed the Sep 24 line rates; GUI and replay show realised vs requested, flag >1% difference"),
    ("CR9", "Trace and retrace side by side in the live GUI and replay", "GUI", "M3", "open", 2, 3, 2, "software-usage/TODO.md #1", "Main manual check for feedback lag, hysteresis and tip artefacts; first step towards the automatic fold check (R15, CN2)"),
    ("HY1", "Measure fast-axis hysteresis from existing constant-height frames (trace vs retrace shift along X, several scan sizes)", "analysis", "M6", "offline done; bench next", 3, 3, 3, "PHYSICS_MODELS.md §5; analysis/hysteresis/HY1_RESULTS.md", "Two constant-height frames: ~3% mid-line (0–6%), so 5% is plausible (the 0 ± 1 px was a line average). Bench: constant-height frames on a flat terrace, slow lines, 10/30/60 nm, VERS recorded"),
    ("HY2", "Slow-axis hysteresis: re-measure the up/down offset after the R19 line-number fix, drift removed line by line", "analysis", "M6", "after R19", 2, 3, 2, "PHYSICS_MODELS.md §5", "Today 8.4 px mixes the 2-row slip, in-sweep shear and Y hysteresis"),
    ("HY3", "Creep: step the scan offset, track a feature for minutes, fit a logarithmic law", "bench", "M6", "planned", 2, 2, 2, "PHYSICS_MODELS.md §5", "Also tells how long to wait after offset or zoom changes"),
    ("HY4", "Cross-hatch pair on one area: X vs Y hysteresis and scale", "bench", "M7", "after SP1 firmware", 2, 1, 2, "PHYSICS_MODELS.md §5", ""),
    ("RC1", "Apply the combined height estimate (Z + current, preamp undone) to real recordings", "analysis", "M4", "v1 done: no gain; retry with PL2", 3, 2, 3, "SIMULATION.md §2, §5.1; DECISIONS D35-D36", "On v1 frames combined ≈ error (Sep 24 0.78 vs 0.79); only 44–50% of pixels carry usable current. Needs frame v2 fields, the preamp f3dB (CN5) and in-range scans"),
    ("PL1", "Shared reconstruction module (reconstruct.py) used by live view, replay and analysis: one \"Run\" pipeline", "GUI", "M3", "approved (D31)", 3, 2, 3, "data-pipeline-v2-design.md §2-3", "Position map -> combined height -> drift registration -> hybrid gridding; versioned; provenance on every image"),
    ("PL2", "Frame format v2: tick + boot ID, valid/clipped/lost counts, signed log-current per bin; readers accept v1 and v2", "firmware", "M1", "proposed (D33)", 3, 2, 3, "data-pipeline-v2-design.md §1", "Bundle with the one-flash milestone (F2, F8, F9)"),
    ("PL3", "Height (Z + current) channel and validity colours in live view and replay", "GUI", "M3", "after PL1", 3, 2, 3, "data-pipeline-v2-design.md §3", "Same channels and overlays in both"),
    ("UI1", "GUI mockup: scan-path dropdown first, mode settings below, derived read-only numbers (realised rate, px/atom, coverage, drive near 158.7 Hz)", "GUI", "M7", "requested", 2, 3, 2, "data-pipeline-v2-design.md §4; D32", "Before building the settings panel"),
    ("SM1", "Calibrate the simulator's usable-current fraction to real scans (truth height scale, loop), then re-run the ladder", "analysis", "M4", "in progress", 3, 3, 3, "DECISIONS A12; SIMULATION.md §5.1-5.2", "Real Sep 24: 44–50% usable; simulation 82–100% even at 8× height. Found: sharp Sep 24 error images imply preamp ≳ 5 kHz, not 400 Hz (A4)"),
    ("PR1", "Delay or filter? Edge 10–90% width vs trace/retrace shift in the error channel (#1808 and other speeds)", "analysis", "M3", "next (offline)", 3, 3, 3, "PHYSICS_MODELS.md §2 conflict; HY1 + SM1", "HY1: a speed-dependent ~0.3–0.5 ms shift; SM1: sharp images need ≳ 5 kHz. A first-order filter shifts and blurs equally; a latency or loop lag only shifts"),
    ("CN1", "Choose windows ≥ 2 × Lc (decoherence: surface relief vs row noise, Lc ≈ 2–5 nm on Sep 24)", "analysis", "M4", "guideline", 3, 3, 2, "Oct 15 report §4", "r = 1/(1 + (Lc/L)^2α); below Lc each row is mostly its own noise. Re-measure Lc after loop and noise fixes"),
    ("CN2", "Morphology acceptance test: survives folding, repeats, both Y halves, and SCALES WITH ZOOM", "analysis", "M5", "adopt", 3, 3, 3, "Oct 15 report §3.6b", "Test 4 is the only one separating sample from scan-fixed patterns (Sep 24 folded band passed 1–3, failed 4). Add to replay checks (R15, I-11) and to the scan-path scorecard"),
    ("CN3", "~3 Hz row wobble: find its source", "measurement", "M8", "open", 2, 2, 2, "Oct 15 report §3.3, §3.7", "Seen at 130, 195 and 390 Hz lines at ~3 Hz; part of the row-to-row noise floor (with the 158.7 Hz tone); candidate for the broadband line-to-line banding (OI-14)"),
    ("CN4", "Switch-off and line checks: stepper-driver holding current, fans/HVAC; raw-tap lines 202.9 Hz (status stream? vary STRM) and 61.5 Hz", "bench", "M8", "planned", 2, 3, 2, "Oct 15 report §4.1", "With T7 and R10"),
    ("CN5", "Reconcile the 400 µs signal-chain constant (Sep 17) with the loop-following offset (Sep 24)", "analysis", "M3", "open", 2, 3, 2, "streak plan cross-check; ai/hypotheses/time-artifacts-piezo-vs-preamp.md", "Deciding measurement (scan-dwell fidelity report, research harness 2026-07-15): read the preamp f3dB from the roll-off of a halted raw-capture noise spectrum. It decides whether preamp blur matters at our speeds (1 pF: 1.6 kHz, harmless; 10 pF: 159 Hz, blurs ~5 nm at fast lines). Before attributing streaks to the preamp or drive chain; the simulator assumes 400 Hz"),
    ("CN6", "Replay index bugs: 1024-px sweeps get the wrong row count; 34 Sep 24 sweeps have timestamps >30% off the line rate", "GUI", "M3", "open", 1, 3, 2, "Oct 15 report App. C", "Excluded from Oct 15 fits; fix in sweep_index"),
    ("CN7", "Rail headroom (setpoint/Z headroom check)", "bench", "M4", "planned", 1, 3, 1, "streak plan 2c", "Small effect; run with T3"),
    ("I-11", "Drift-registered replay mode (line by line, as in report v2)", "GUI", "M5", "proposed", 3, 2, 3, "report v2 Section 2", "Feature stays put while stepping; A/B compare the same sample patch; basis for the cross-hatch merge"),
    ("SP0", "Scan-path library + reconstruction contract + simulator (PC only)", "analysis", "M7", "designed", 3, 3, 2, "scan-path-design.md §9–10", "Generators, reconstruct(), coverage map, golden vectors, piezo model, scorecard on Sep 24 truth; no hardware"),
    ("SP1", "Scan-path modes (SPTH): rotated raster, cross-hatch sequence, spirals, rose / figure-8, centre-return loops", "firmware", "M7", "experimental option; priority vs calibration open", 3, 1, 3, "operator 2026-10-23; scan-path-design.md", "Every named path in code, versioned, bit-exact; recordings carry the reconstruction recipe (no orphan frames); Custom via a path file copied into the recording. Mode 0 = today's raster, untouched. Integer phase counters + sine LUT so Python reproduces positions bit for bit. Order: Python generators, piezo model (158.7 Hz, hysteresis, creep, preamp lag), simulator on Sep 24 ground truth, emulator playback, then firmware"),
    ("G-ST1", "Stage tracking, monitor mode (compact panel, Show fiducials off by default)", "GUI", "M5", "designed", 3, 2, 3, "mockups; MORPHOLOGY report F/F2", ""),
    ("G-ST2", "Stage tracking, correct mode with in-zone gate", "GUI", "M5", "designed + simulated", 3, 1, 3, "OI-8; analysis/sim/tracking_sim.py", "Alpha-beta + feed-forward holds ~0.7 nm in simulation (vs ~13 nm uncorrected); after G-ST1 and F1"),
    ("G-TR", "Trace/retrace handling (offset record, compensation, which stream to track)", "analysis", "M3", "to scope", 2, 2, 2, "OI-7", "Scope first, then approve"),
    ("G-CL", "Fixed colour scale + clipped/no-current colours", "GUI", "M3", "open", 2, 3, 2, "OI-4, I-7", ""),
    # ---- offline investigations
    ("I-1", "Loop simulator: test firmware fixes before changing firmware", "analysis", "M3", "done", 3, 3, 2, "analysis/sim/loop_sim.py", "Calibrated to Oct 22; found the low-setpoint trap (< ~170 pA runs away)"),
    ("I-2", "Phantom offset signature in existing raw data", "analysis", "M3", "blocked", 3, 3, 2, "test plan I-2", "Oct 22 raw capture has no data during scanning; needs I-9 or T2"),
    ("I-3", "Trace-only rerun of fiducial tracking", "analysis", "M5", "queued", 1, 3, 1, "test plan I-3", ""),
    ("I-4", "158.7 Hz section in the morphology report", "doc", "M8", "queued", 1, 3, 1, "test plan I-4", ""),
    ("I-6", "Verify the STM techniques backlog with sources", "analysis", "M3", "queued", 2, 3, 2, "techniques backlog", ""),
    ("I-7", "Audit auto colour levels (live and replay)", "analysis", "M3", "queued", 2, 3, 2, "test plan I-7", ""),
    ("I-8", "ADC overrange behaviour; zero-substitution impact", "analysis", "M3", "in progress", 2, 3, 2, "test plan I-8, OI-2.6", "Substitution fires on 0.1% of scan samples: ~2% of pixels get false dark specks"),
    ("I-9", "Raw capture during scanning (blocks only arrive while halted)", "analysis", "M3", "queued", 3, 2, 3, "test plan I-9", "Unblocks I-2 and in-scan spectra"),
    ("I-10", "Standardise display: dark = valleys in live, replay and reports", "GUI", "M3", "built (live + replay); report figures pending", 3, 3, 3, "test plan OI-4", "Built 2026-10-23: live raster and replay show -Z and -error (peaks bright) by default, 'Peaks bright' checkbox to see raw; linearized-current view unchanged; saved data and TIFF/GSF exports stay raw. Report figures still show stored values (stated in the report's Section 0)"),
    ("TIP", "Recover or replace the tip", "bench", "M4", "open", 3, 2, 3, "OI-13", "Prerequisite for M4"),
]
SESSIONS = [
    ("1", "Bench A: diagnostics", "T1, T2 (with R9–R11), T7 (with R5, R6, R8)", "M2"),
    ("2", "Firmware/GUI milestone", "F1, F2, F3, R19, F4 (after T2), optional F6", "M1, M3, M7"),
    ("3", "Bench B: imaging (recovered tip)", "T3 (+R2 at 5 Hz), T4, T5, T6", "M4, M5"),
    ("4", "Bench C: calibration and zoom", "T8, R12", "M6"),
]
DOCS = [
    ("Test plan (detailed, living)", "2026-10-23-open-issues-and-tests.md"),
    ("Phantom-offset handoff", "phantom-offset-handoff.md"),
    ("STM techniques backlog", "../stm-techniques-backlog.md"),
    ("Streak follow-up meeting plan", "../meetings/2026-10-streak-followup-plan.md"),
    ("Oct 22 morphology, drift and KIGA report", "../../TeamUpdate/data/2026-Oct-22/MORPHOLOGY-2026-10-22.html"),
    ("Stage tracking mockup", "../mockup-stage-tracking-compact-v2.png"),
]
rows = [dict(id=a, title=b, type=c, ms=d, status=e, lead=f, ease=g, impact=h, score=f + g + h, source=i, note=j) for a, b, c, d, e, f, g, h, i, j in I]
e = html.escape
goals = "".join(f'<div class="g"><b>{e(a)} · {e(b)}</b><div class="mut">{e(c)}</div></div>' for a, b, c in GOALS)
ms = "".join(f'<div class="m"><b>{e(a)} · {e(b)}</b><div class="mut">{e(c)}</div><div class="cnt" data-ms="{e(a)}"></div></div>' for a, b, c in MS)
sess = "".join(f"<tr><td>{e(a)}</td><td>{e(b)}</td><td>{e(c)}</td><td>{e(d)}</td></tr>" for a, b, c, d in SESSIONS)
docs = "".join(f'<li><a href="{e(h)}">{e(t)}</a></li>' for t, h in DOCS)

page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>qt-panda Roadmap</title>
<style>
:root{{--bg:#fbfaf8;--fg:#1d1d1f;--mut:#5f6368;--line:#e2dfd9;--card:#fff;--acc:#b4531a;--hi:#e8f4ea}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#16171a;--fg:#e8e6e3;--mut:#a3a3a3;--line:#33353a;--card:#1e2024;--acc:#f0a46a;--hi:#1f3324}}}}
:root[data-theme="dark"]{{--bg:#16171a;--fg:#e8e6e3;--mut:#a3a3a3;--line:#33353a;--card:#1e2024;--acc:#f0a46a;--hi:#1f3324}}
body{{background:var(--bg);color:var(--fg);font:14.5px/1.5 system-ui,"Segoe UI",sans-serif;margin:0}}
main{{max-width:1240px;margin:0 auto;padding:26px 16px 60px}}
h1{{font-size:25px;margin:0 0 4px}} h2{{font-size:17px;margin:28px 0 8px;border-bottom:1px solid var(--line);padding-bottom:4px}}
.mut{{color:var(--mut);font-size:13px}} .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:10px}}
.g,.m{{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px 12px}} .m{{cursor:pointer}} .m.sel{{outline:2px solid var(--acc)}}
.cnt{{font-size:12px;color:var(--acc);margin-top:4px}}
.bar{{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:8px 0}}
select,input{{font:inherit;font-size:13px;padding:3px 6px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--fg)}}
.scroll{{overflow-x:auto}} table{{border-collapse:collapse;width:100%;font-size:13px}}
th,td{{border-bottom:1px solid var(--line);padding:5px 6px;text-align:left;vertical-align:top}}
th{{cursor:pointer;white-space:nowrap;position:sticky;top:0;background:var(--bg)}} td.n{{text-align:center}}
tr.top td{{background:var(--hi)}} .pill{{font-size:11.5px;border:1px solid var(--line);border-radius:10px;padding:0 6px;white-space:nowrap}}
</style></head><body><main>
<h1>qt-panda roadmap</h1>
<div class="mut">Goals, milestones and every open item in one place · consolidated 2026-10-23 from the Oct 15 resolution report (action items, their original scores in brackets), the streak follow-up meeting plan, the Oct 22 KIGA sweep and morphology work, and the new test plan. Living document: update scores and status as results come in.</div>

<h2>Goals</h2><div class="grid">{goals}</div>

<h2>Milestones</h2><div class="mut">Click a milestone to filter the table below; click again to clear.</div><div class="grid" style="margin-top:6px">{ms}</div>

<h2>All items, scored</h2>
<div class="mut">Scores 1–3, as in the Oct 15 report. <b>Lead:</b> how likely it finds or fixes a main limit. <b>Ease:</b> 3 = analysis or a setting, 2 = bench session or small code change, 1 = hardware or large firmware. <b>Impact:</b> how much a positive result changes the design or defaults. Totals for new items are estimates to revise together; highlighted rows score 8–9.</div>
<div class="bar">
<label>Type <select id="fType"><option value="">all</option></select></label>
<label>Status <select id="fStatus"><option value="">all</option></select></label>
<label>Search <input id="fText" placeholder="word…"></label>
<span class="mut" id="nShown"></span>
</div>
<div class="scroll"><table id="tbl"><thead><tr>
<th title="Position in the current sort and filter">#</th><th data-k="id">ID</th><th data-k="title">Item</th><th data-k="type">Type</th><th data-k="ms">Milestone</th><th data-k="status">Status</th>
<th data-k="lead">Lead</th><th data-k="ease">Ease</th><th data-k="impact">Impact</th><th data-k="score">Score ▾</th><th data-k="source">Source</th><th data-k="note">Next / notes</th>
</tr></thead><tbody></tbody></table></div>

<!--CALC-->
<h2>Proposed order of sessions</h2>
<div class="scroll"><table><tr><th>#</th><th>Session</th><th>Items</th><th>Milestones</th></tr>{sess}</table></div>

<h2>Safety rules (apply to every session)</h2>
<ol>
<li>Until the new firmware is flashed, the Retract (RTRC) button jumps Z to 50000, toward the sample whenever Z is below that (lower Z = away). Back off with the GUI Z slider or the motor. The fix (F2: Z to the fully retracted end) is built, not flashed.</li>
<li>Choose the scan mode deliberately: with feedback off, RUN now asks (engage first, or constant height on purpose), and the clip guard steps Z away at sustained clipping (F1, built; needs a GUI relaunch to take effect). The Oct 22 crash happened parked at fixed Z.</li>
<li>Approach and engage stay with the operator; Claude never approaches.</li>
<li>Automated scans run with guards that halt (never move Z): clipping, Z limit, no-current share, feedback dropout.</li>
<li>Analog supply on ~5 s before the Teensy, then Reset.</li>
<li>Very low bias (below ~20 mV) brings the tip close; treat it as crash-risk.</li>
</ol>

<h2>Detailed documents</h2><ul>{docs}</ul>
</main>
<script>
const ROWS = {json.dumps(rows)};
let key = 'score', dir = -1, msSel = '';
const tb = document.querySelector('#tbl tbody');
const uniq = k => [...new Set(ROWS.map(r => r[k]))].sort();
for (const [id, k] of [['fType', 'type'], ['fStatus', 'status']]) {{
  const s = document.getElementById(id); uniq(k).forEach(v => s.add(new Option(v, v))); s.onchange = draw;
}}
document.getElementById('fText').oninput = draw;
document.querySelectorAll('th[data-k]').forEach(th => th.onclick = () => {{
  const k = th.dataset.k; dir = (k === key) ? -dir : (['lead', 'ease', 'impact', 'score'].includes(k) ? -1 : 1); key = k;
  document.querySelectorAll('th[data-k]').forEach(t => t.textContent = t.textContent.replace(/ [▾▴]$/, ''));
  th.textContent += dir < 0 ? ' ▾' : ' ▴'; draw();
}});
document.querySelectorAll('.m').forEach(m => m.onclick = () => {{
  const id = m.querySelector('b').textContent.split(' ')[0];
  msSel = msSel === id ? '' : id;
  document.querySelectorAll('.m').forEach(x => x.classList.toggle('sel', x === m && msSel)); draw();
}});
document.querySelectorAll('.cnt').forEach(c => {{
  const n = ROWS.filter(r => r.ms === c.dataset.ms), open = n.filter(r => !/done|superseded/.test(r.status));
  c.textContent = `${{n.length}} items · ${{open.length}} open`;
}});
const esc = s => String(s).replace(/[&<>]/g, ch => ({{'&': '&amp;', '<': '&lt;', '>': '&gt;'}}[ch]));
function draw() {{
  const ft = document.getElementById('fType').value, fs = document.getElementById('fStatus').value, q = document.getElementById('fText').value.toLowerCase();
  const rs = ROWS.filter(r => (!ft || r.type === ft) && (!fs || r.status === fs) && (!msSel || r.ms === msSel) &&
    (!q || JSON.stringify(r).toLowerCase().includes(q)));
  rs.sort((a, b) => (a[key] > b[key] ? 1 : a[key] < b[key] ? -1 : 0) * dir || b.score - a.score);
  tb.innerHTML = rs.map((r, i) => `<tr class="${{r.score >= 8 ? 'top' : ''}}"><td class="n">${{i + 1}}</td><td>${{esc(r.id)}}</td><td>${{esc(r.title)}}</td><td><span class="pill">${{esc(r.type)}}</span></td>
    <td>${{esc(r.ms)}}</td><td>${{esc(r.status)}}</td><td class="n">${{r.lead}}</td><td class="n">${{r.ease}}</td><td class="n">${{r.impact}}</td>
    <td class="n"><b>${{r.score}}</b></td><td class="mut">${{esc(r.source)}}</td><td>${{esc(r.note)}}</td></tr>`).join('');
  document.getElementById('nShown').textContent = `${{rs.length}} of ${{ROWS.length}} items`;
}}
draw();
</script></body></html>"""

CALC = """<h2>EXTRA: Gap calculator: bias, current and tip height</h2>
<div class="g" style="max-width:none">
<div class="mut">Tunnel-junction (gap) resistance R = |bias| ÷ current is set by the vacuum gap, not by the preamp's fixed 100 MΩ feedback resistor (which only sets the gain). Tip height above point contact from R = R<sub>c</sub>·e<sup>2κs</sup>, with R<sub>c</sub> ≈ 12.9 kΩ (one conductance quantum) and κ = 0.512·√φ Å⁻¹. Gold's own resistance is negligible. Heights are relative to point contact and depend on the barrier φ; an I(z) measurement would calibrate it. Valid at low bias (|V| ≪ φ).</div>
<div class="bar" style="margin-top:10px">
<label>Bias (mV) <input id="cV" type="number" value="-49.6" step="1" style="width:90px"></label>
<label>Setpoint (pA) <input id="cI" type="number" value="500" step="10" style="width:90px"></label>
<label>Barrier φ (eV) <input id="cP" type="number" value="4.0" step="0.1" min="0.5" max="6" style="width:70px"></label>
<label>Preamp gain <select id="cG"><option>1</option><option>5</option><option>10</option><option>100</option></select>×</label>
</div>
<div class="scroll"><table id="cOut"></table></div>
<div class="mut" style="margin-top:6px">Rule of thumb from the formula: the distance margin to the clip depends only on the ratio of clip current to setpoint, not on the bias; bias moves the whole working height. Each factor of 2 in current is a fixed height step.</div>
<h3 style="font-size:14px;margin:12px 0 4px">T4 ladder at this setpoint</h3>
<div class="scroll"><table id="cLad"></table></div>
</div>
<script>
(function(){
  const Rc = 12906, CLIP1X = 102.4e-9, LSB_PER_PA_1X = 0.32;
  const $ = id => document.getElementById(id);
  const fmtR = r => r >= 1e9 ? (r/1e9).toFixed(2)+' GΩ' : r >= 1e6 ? (r/1e6).toFixed(1)+' MΩ' : r >= 1e3 ? (r/1e3).toFixed(1)+' kΩ' : r.toFixed(0)+' Ω';
  function calc(Vmv, IpA, phi, gain){
    const V = Math.abs(Vmv)/1000, I = IpA*1e-12, k = 0.5123*Math.sqrt(phi);
    const R = V/I, s = Math.log(R/Rc)/(2*k), Iclip = CLIP1X/gain, margin = Math.log(Iclip/I)/(2*k);
    return {R, s, k, Iclip, margin, lsb: IpA*LSB_PER_PA_1X*gain, step2: Math.log(2)/(2*k)};
  }
  function draw(){
    const V = +$('cV').value, I = +$('cI').value, P = +$('cP').value, G = +$('cG').value;
    if (!(I > 0) || !(P > 0) || V === 0){ $('cOut').innerHTML = '<tr><td>enter a non-zero bias and a positive current</td></tr>'; return; }
    const c = calc(V, I, P, G);
    const warn = c.margin < 1.5 ? ' style="color:#c0392b;font-weight:600"' : '';
    $('cOut').innerHTML =
      `<tr><th>Gap resistance</th><td><b>${fmtR(c.R)}</b></td><th>Tip height above point contact</th><td><b>${c.s.toFixed(2)} Å</b></td></tr>`+
      `<tr><th>Setpoint in ADC counts</th><td>${c.lsb.toFixed(0)}</td><th>Clip current at ${G}× (ADC 32767)</th><td>${(c.Iclip*1e9).toFixed(1)} nA</td></tr>`+
      `<tr><th>Height margin before clipping</th><td${warn}>${c.margin.toFixed(2)} Å</td><th>Height per factor of 2 in current</th><td>${c.step2.toFixed(2)} Å</td></tr>`+
      `<tr><th>Decay constant κ</th><td>${c.k.toFixed(2)} Å⁻¹</td><th>Current change per 1 Å</th><td>× ${Math.exp(2*c.k).toFixed(1)}</td></tr>`;
    const lad = [500, 150, 50, 15, 7].map(mv => { const r = calc(mv, I, P, G); return `<tr><td>${mv} mV</td><td>${fmtR(r.R)}</td><td>${r.s.toFixed(2)} Å</td><td>${(r.s - c.s >= 0 ? '+' : '') + (r.s - c.s).toFixed(2)} Å vs current setting</td></tr>`; });
    $('cLad').innerHTML = '<tr><th>Bias</th><th>Gap resistance</th><th>Height above contact</th><th>Change</th></tr>' + lad.join('');
  }
  ['cV','cI','cP','cG'].forEach(id => $(id).addEventListener('input', draw)); draw();
})();
</script>
"""
page = page.replace("<!--CALC-->", CALC)
open(OUT, "w", encoding="utf-8").write(page)
print(OUT, len(rows), "items")
