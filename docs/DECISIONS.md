# Decisions and assumptions log (living)

**Purpose.** Session conversations are ephemeral. This file keeps **what was decided, by whom, why, and on which assumptions**, so new code can be audited against it later and questions can be traced to their origin. Code comments say *how*; this file says *why* and *on what basis*.

**Rules.**
- **Add, don't rewrite.** A changed decision gets a new entry that supersedes the old one (`supersedes D7`), and the old one is marked `superseded`.
- **Every entry carries its owner and its basis.** Owner: operator decision, operator-approved proposal, or Claude proposal pending. Basis: the evidence or assumption it rests on, with links.
- **Assumptions get their own register** (section 3), with how each one would be checked. Physics parameters live in [`PHYSICS_MODELS.md`](PHYSICS_MODELS.md) and are only referenced here.
- When code implements a decision, cite the decision ID in the commit message or the module docstring.

Status: `active`, `pending` (awaiting the operator), `superseded`, `built` (implemented, not yet on hardware), `done`.

---

## 1 · Decisions

### Safety and control

| ID | Date | Decision | Owner | Basis | Status |
|---|---|---|---|---|---|
| D1 | 2026-10-23 | RTRC drives Z to the fully retracted end (DAC 0, same as the live Z slider at "Away") and syncs the integrator; it never moves toward the sample | operator | Old RTRC jumped to absolute 50000, toward the sample whenever Z < 50000 (`stm_firmware.hpp`) | built (F2), not flashed |
| D2 | 2026-10-23 | RUN with feedback off must state the mode: "engage, then run" or "constant height on purpose"; the copilot must pass `mode: cc\|ch` | operator (scope) | The Oct 22 crash happened parked at fixed Z; a hard feedback gate would block constant height | built (F1) |
| D3 | 2026-10-23 | Clip guard default on: sustained clipping with feedback off → halt and step Z away; only ever retracts | Claude, approved under F1 | Oct 22 crash timeline (23% → 100% clipped in 30 s) | built (F1) |
| D4 | — | Claude never approaches the sample, never flashes or actuates hardware without the operator; the emulator first | operator (standing) | safety | active |
| D5 | 2026-10-23 | Refuse DACX/DACY writes during a scan and DACZ while feedback owns Z (they last one tick today) | Claude proposal | Timing audit | pending (F9) |
| D6 | — | Setpoint stays ≥ ~200 pA until the offset fix (F4) | Claude, from simulation | `loop_sim`: runaway below ~170 pA | active (rule 0.7) |
| D7 | 2026-10-22 | Running KIGA default 3.07 (⅔ of 4.6) until a good tip confirms 4.6 | operator | Oct 22 sweep: 4.6 last stable, 9 oscillates | active |

### Display and naming

| ID | Date | Decision | Owner | Basis | Status |
|---|---|---|---|---|---|
| D8 | 2026-10-23 | Dark always means valleys: show −Z and −error (peaks bright) in live view, replay and reports; raw data and TIFF/GSF exports stay raw | operator | Stored Z and error both put peaks low (OI-4) | built (I-10) |
| D9 | 2026-10-23 | Sweep halves are named up sweep (▲) and down sweep (▼), as in the replay viewer | operator | live and replay used opposite names (5d) | active (F7 pending in live view) |
| D10 | 2026-10-23 | Stage tracking: monitor mode first; correct mode needs the operator; "Show fiducials" in the raster toolbar, default off | operator | mockups | active |

### Reports and collaboration

| ID | Date | Decision | Owner | Basis | Status |
|---|---|---|---|---|---|
| D11 | 2026-10-23 | One shared artifact per review, roadmap at the bottom; keep a local copy (folder, REPORT-TEXT.md, README with URL) | operator | — | active |
| D12 | 2026-10-23 | Oct 22 report v1 is a frozen reference; v2 is a separate artifact | operator | — | active |
| D13 | — | Claude never runs `git commit`; prepares groups and commands, the operator commits | operator | — | active |
| D14 | 2026-10-23 | The Oct 15 "Scan Resolution Limits" report is a historical reference; current priorities live in the roadmap and plan §6.1 | operator | priorities were updated by later work | active |
| D15 | 2026-10-23 | Decisions and assumptions are written to this file as they are made (sessions are ephemeral) | operator | — | active |

### Timing and data

| ID | Date | Decision | Owner | Basis | Status |
|---|---|---|---|---|---|
| D16 | 2026-10-23 | The microcontroller tick is the gold-standard time base; PC time is a reference only | operator | PC frame times are batched (Oct 22 median 91 ms vs mean 97.5 ms) | active (F8 approved) |
| D17 | 2026-10-23 | Tick counter free-running from boot, plus a boot ID in every frame and status record; the PC treats each boot as its own epoch and fits PC time = a + b·tick | operator (resets are frequent) | — | approved, not built |
| D18 | 2026-10-23 | X-Y stage drift and Z thermal drift are distinct phenomena, named and modelled separately; the Z component is not yet mapped (OI-16) | operator | rig experience; first split on Oct 22 | active |

### Scan paths

| ID | Date | Decision | Owner | Basis | Status |
|---|---|---|---|---|---|
| D19 | 2026-10-23 | Scan paths are an experimental **option**; the default raster stays unchanged (firmware mode 0 bit-identical to FW 5.6) | operator | — | active |
| D20 | 2026-10-23 | Every named path lives in code, versioned and auditable; released versions are never edited | operator | auditability by people and LLMs | active |
| D21 | 2026-10-23 | A Custom path option is allowed; the file is copied into the recording and hashed | operator | — | built (PC library) |
| D22 | 2026-10-23 | No orphan frames: every recording carries what is needed to rebuild each sample's position | operator | — | designed (scan-path-design §5) |
| D23 | 2026-10-23 | Firmware gets runtime-selectable path modes (`SPTH`) rather than a general path table; a table mode only if Custom needs it on hardware | operator | Timing and smooth-motion concerns about a general engine | designed |
| D24 | 2026-10-23 | Cross-hatch is a *sequence* (fast-axis swap by transpose at frame end, which keeps the shared corner seamless), not a path | operator / Claude | — | built (PC library) |
| D25 | 2026-10-23 | Simulate before any firmware: bit-exact generators, physics model, scorecard, emulator playback | operator | — | in progress |
| D26 | 2026-10-23 | Raster-as-custom-file must reproduce the raster bit for bit (validation gate) | operator | — | done (tests + simulation) |
| D27 | 2026-10-23 | Simulation truth is the **error channel** of Sep 24 #1808 (operator's pick); the smooth averaged-Z truth was withdrawn | operator | the error channel carries the morphology; Z barely moves on gold (Oct 15 §3.3) | active |
| D28 | 2026-10-23 | Standard of proof: a reconstruction must recreate a known truth at ≥ 99% where the physics is known, shown with a one-effect-per-layer verification ladder | operator | — | active (met: `SIMULATION.md`) |
| D29 | 2026-10-23 | Priority of scan paths relative to calibration | operator | — | **pending** |

### Reconstruction and pipeline

| ID | Date | Decision | Owner | Basis | Status |
|---|---|---|---|---|---|
| D30 | 2026-10-23 | Reconstruct height from Z **plus current** (combined estimate); undo the preamp filter (one-bin average, valid windows only); drop ticks with no height information; hybrid gridding; actual positions when calibrated | Claude, from the ladder | `SIMULATION.md` §2–3 | active for simulation; real data via RC1 |
| D31 | 2026-10-23 | **Live view and replay share one reconstruction pipeline ("Run" mode)**: replay = running the recorded stream through the same code the live view uses | operator | consistency; one place to audit | approved, not built (`data-pipeline-v2-design.md`) |
| D32 | 2026-10-23 | **Scan settings panel: the scan-path dropdown is the first setting**; the settings below populate for the selected mode (mostly shared for now) | operator | settings differ by path | approved, mockup requested |
| D33 | 2026-10-23 | Frame format v2: tick, boot ID, valid/clipped/lost counts and signed log-current per bin; readers accept v1 and v2 | Claude proposal | §1 of `data-pipeline-v2-design.md` | proposed |
| D34 | 2026-10-23 | Correct the line-number slip in **legacy** `.frames` by default in the new shared pipeline (rule: first Y-cycle after RUN, the second stamp 0 = line bins−1; afterwards stamped − 1 mod bins). Every corrected recording gets a `<base>.corrections.json` change-log; raw `.frames` are never modified; `line_index = stamped` reverts exactly. Published reports keep their old images | operator ("correct if confident, leave a change-log trail so spot changes can be reverted") | firmware port + real Oct 22 stamps | approved (pipeline v2) |
| D35 | 2026-10-23 | For **existing v1 recordings** the error channel stays the morphology channel; the combined height is not used on v1 data | Claude, from RC1 | RC1: combined ≈ error (Sep 24 0.78 vs 0.79, 0.89 vs 0.89), Z term ~20× smaller than the gap term, only 44–50% of pixels carry usable current; masking and pixel-level preamp inversion make it worse (`software/pc/qtpanda/analysis/rc1/RC1_RESULTS.md`) | active |
| D36 | 2026-10-23 | The combined height (D30) is applied to real data only once frames carry signed current, valid/clipped/lost counts and tick time (PL2), and scans keep the current in range (gain, line rate, setpoint, F4) | Claude proposal | RC1 + SIMULATION.md | proposed |

| D39 | 2026-10-23 | **Sweep numbering is frozen** (addendum to D34): sweep identity (which records form sweep #i) always comes from the stamped segmentation, so sweep numbers in reports, timelines and notes never change. Corrected line indices only place rows, and each sweep image borrows one record either side for its boundary line | Claude (operator's revert/trail requirement) | Slip correction changed the sweep count in 5 of 32 recordings (incl. the Sep 24 files with #1586 and #1808), which would renumber later sweeps; corrected images on the frozen numbering equal the ground truth (test) | active |
| D40 | 2026-10-23 | **Deterministic hooks, not runbooks:** everything the pipeline needs (sweep index, slip correction and its change-log, sidecar settings, format checks, validation status) runs automatically from GUI actions (live Run/Halt, opening a recording in replay), with visible status. LLM runbooks are for local testing only | operator | future teams may not use an assistant; deterministic code is auditable | active |
| D38 | 2026-10-23 | **Build everything now, behind toggles** (supersedes the build-later half of D37): default route = today's scanning exactly; experimental routes selectable; backbone cut-overs each with an equivalence gate. Frame v2 becomes the firmware default after the bench gate; a GUI mockup checkpoint precedes the new settings panel. Plan: `docs/test-plans/pipeline-v2-build-plan.md` | operator | — | approved, in progress |
| D37 | 2026-10-23 | **Readiness split.** Build now: measurement infrastructure (firmware: F8 tick + boot ID, PL2 frame v2 fields, R19 line-number fix, F9, CR1, CR2, CR8; PC: frame v2 reader/writer, CR7 real settings, `scan_path` block, the shared reconstruction module carrying only today's **proven** channels plus line-by-line drift registration, "Run" mode for live view and replay). Keep behind versioned, labelled switches until confirmed on the bench: combined height, preamp inversion, lateral (hysteresis and dynamics) correction, Z-drift removal, non-raster firmware modes | Claude proposal | Simulation corrections are perfect by construction (the same model injects and removes the error). Only drift registration is demonstrated on real data; RC1 showed no combined-height gain on v1 data | proposed |
| D41 | 2026-10-23 | **Replay default rows = slip-corrected (v1 data)**, switchable in the player ("rows" combo, `--stamped`); change-log `<base>.corrections.json` written only when an index is persisted (`write_index`/`load_or_build`), never by read-only analysis (`build_index`, lattice_fft). lattice_fft keeps stamped rows (FFT is shift-insensitive). Sidecar `derived_samples_per_pixel` now from `control_rate_hz` + SPPX (CR7); recordings made before this keep the 4x-low value — use `isr_rate_hz` presence (settings_version 2) to tell them apart | Claude (implements D34/D39 under D38) | equivalence tests (`tests/test_sweep_index.py`, `test_reconstruct_equivalence.py`) | active |

## 2 · Open decision queue (operator)

1. D29: scan paths before or after calibration.
2. D34: legacy line-number correction.
3. Which paths reach the dropdown after the scorecard; constant angular vs constant tip speed for spirals.
4. Timing of the one-flash firmware milestone: F2, F8, F9, CR1–CR4, CR8, optionally SPTH.
5. Frame format v2 contents (D33).

## 3 · Assumptions register (non-physics; physics in `PHYSICS_MODELS.md`)

| ID | Assumption | Used by | Risk if wrong | How to check | Status |
|---|---|---|---|---|---|
| A1 | Sep 24 is the last good-tip scanning day on disk (Oct 1 and Oct 15 have no scan files locally) | simulation truth, repeat targets | a better reference is missed | operator: point to other storage | open |
| A2 | Heights from the #1808 error channel are a lower bound (terraces 0.5–1 Å vs gold 2.35 Å) | simulation scale | absolute numbers off; ranking unaffected | Z calibration (T8), I(z) | stated |
| A3 | Hysteresis 5% of span (Prandtl–Ishlinskii) in the simulator (PR1 adds: a ~1–3 nm direction-dependent position offset in the error channel, constant across speeds) | piezo-calibration lever (0.79 → 0.99) | the lever's size depends on it | HY1 done: constant-height mid-line separation ~3% (0–6%, two frames); **5% is plausible**. The earlier claim that #932 shows it is much smaller was wrong (it was a line average). Sensitivity 1–12%; bench measurement | **plausible; uncertain ×2** |
| A4 | Preamp 400 Hz first order | preamp inversion, simulator | inversion wrong on real data | CN5; PR1 edge-width test | **resolved (PR1): wrong.** f3dB ≳ 6–16 kHz; the trace/retrace shift is a ~1–3 nm position offset, not a delay. Simulator working value ≥ 6 kHz; no 400 µs inversion on real data |
| A5 | v1 frames' mean error per pixel approximates mean log-current | legacy combined height (RC1) | abs() mixes no-current ticks in; no clip/loss counts | compare with raw tap where both exist; v2 format | **checked by RC1: too crude to add information beyond the error channel** (D35) |
| A6 | Drift is linear in time within a run (plus up/down offset and gain jumps) | registration, simulator | curvature or decay after motor moves (settling) | T6 10-minute hold; decaying variant in simulation | partly checked (Oct 22 fit residual 5 px) |
| A7 | Line timing from PC receive times is adequate for drift registration | report v2 | ms jitter; fine for drift, not for sub-line work | F8 tick stamps | accepted for now |
| A8 | 1 px = 0.117 nm at 30 nm / 256, with the 5 nm/V placeholder | all nm values | scale error (zoom matched commands within 5–10%) | T8 lattice | stated |
| A9 | The scan simulator's Z-only behaviour need not match reality, because the combined estimate is lag-insensitive | conclusions in `SIMULATION.md` | if real lag effects leak into the current too, combined results degrade | OI-18; RC1 on real data | stated |
| A13 | Historical recordings were not affected by the KPGA bug (KPGA alone after boot sets the ISR integral gain to 0, because the firmware's `Ki` copy starts at 0 while `Ki_isr` starts at 300000) | trust in all past data | a scan with a zero integral (frozen Z) misread as surface | **checked 2026-10-23 against every session journal:** 13 sessions with gain commands; no lone KPGA (the GUI always sends KPGA then KIGA, `main.py:3312-3313`); no ENGA/CCON/RUN in that state. One near miss: Sep 24 session 1790289638729 sent `CCON 320` 2 s before its first KIGA, so the loop ran on the boot preset (KIGA ≈ 4.58, not 0). Fix A7 in FW 5.7 | checked: not affected |
| A12 | The simulator's current stays mostly in range (usable ~100% on the #1808 truth at stated scale) | the ≥ 99% recreation results | **wrong for real data: Sep 24 had only 44–50% usable current, Oct 22 27%**; the stated height scale (error-channel lower bound) is too small | calibrate the simulator's height scale (and loop) so its usable-current fraction matches the real one, then re-run the ladder | **open: next simulator fix** |
| A10 | Path comparisons are only fair at matched tip speed | scan-path scorecard | slower paths look better | — | rule |
| A11 | The GUI's derived samples-per-pixel assumes a 40 µs ISR (records 4× low at 10 µs) | old sidecars | wrong timing metadata | CR7 | known bug |

## 4 · Where things are recorded

- **Physics models and their status:** `PHYSICS_MODELS.md`.
- **Simulator, reconstruction, ladder, results:** `SIMULATION.md`.
- **Scan paths and the recording contract:** `test-plans/scan-path-design.md`.
- **Frame format v2, shared pipeline, GUI and replay:** `test-plans/data-pipeline-v2-design.md`.
- **Work items and priorities:** `test-plans/roadmap.html` (source `build_roadmap.py`); plan §6.
- **Session resume state:** `test-plans/RESUME.md`.
