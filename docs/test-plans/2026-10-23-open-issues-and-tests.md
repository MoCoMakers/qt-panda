# Open issues and test plan after the Oct 22 KIGA sweep

**Status:** living document, started 2026-10-23. Update each item in place as tests run.
**Background:** `TeamUpdate/data/2026-Oct-22/MORPHOLOGY-2026-10-22.html` (single report), `docs/meetings/2026-10-streak-followup-plan.md` (bench plan; 2a results), the Oct 15 resolution report "What limits our scan resolution" (action items 1–22), `docs/test-plans/phantom-offset-handoff.md`, `docs/stm-techniques-backlog.md`.

---

## 0 · Safety rules for every test below

1. **The Retract (RTRC) button jumps Z to the fixed value 50000** (`stm_firmware.hpp:604–615`). Lower Z is away from the sample (Oct 22: contact at 48,600, backing off lowered it; the GUI slider is labelled 'Away (low, safe)'), so RTRC moves the tip toward the sample whenever Z is below 50,000, as it was throughout Oct 22 tunnelling (25k–38k). The GUI Z slider is correct; use it, or the motor, to back off. **Decided 2026-10-23 (F2, approved):** RTRC will do what the live-scan Z slider does when pulled fully to "Away": feedback off, Z to its fully retracted end.
2. **Continuous-scan RUN does not engage feedback, and nothing guards a fixed-Z tip.** On Oct 22 the tip crashed at 19:10:30 while parked at fixed Z after the approach (before any RUN), and the 19:12 scan then ran at fixed Z on the crashed junction. Choose the mode deliberately at RUN (engage for constant current; constant height only on purpose), and watch for sustained clipping whenever Z is fixed. Planned: explicit mode at RUN plus a sustained-clip guard (F1).
3. **Approach and engage stay with the operator.** Claude runs scans and settings changes only when the operator says so, and never approaches.
4. **Guards for any automated scan:** halt on ADC clipped > 0.75 s; halt on Z beyond a set limit toward the sample; halt when the share of no-current samples in a 2 s window exceeds a threshold (not "continuously lost for 5 s", which missed the KIGA 9 oscillation); halt if feedback drops out. Guards halt; they never move Z.
5. **Power order:** analog supply about 5 s before the Teensy, then Reset (`docs/DAC_BOOT_ORDER.md`).
6. **Small gap resistance means a close tip.** At −50 mV and 500 pA the gap is ~100 MΩ; the clip (102 nA) corresponds to ~0.5 MΩ, near point contact. Treat very low bias (below ~20 mV) as a crash-risk setting (OI-5).

---

## 1 · Control process

### 1.1 How sweeps will run
Sweeps run as an AI-driven process when the operator says "run the next sweep": Claude sends settings, RUN, KIGA changes and journal notes through the copilot bridge, with the guards in 0.4. The GUI states below are what the operator sees either way.

| State | Entered by | Shown in GUI | Notes |
|---|---|---|---|
| Idle | port open | status line | recording runs whenever the port is open |
| Approach | operator only | approach progress | |
| Mode chosen | Engage (ENGA) for constant current, or constant height selected on purpose | feedback indicator / mode label | RUN asks for the mode; a sustained-clip guard protects any fixed-Z state (F1) |
| Scanning | RUN | sweep counter | KIGA changes applied **without halting** (KIGA-only command at the next Y turnaround, OI-6) |
| Primed | first 2 sweeps of the same direction | fiducials found | trace-only images (OI-7) |
| Tracking (monitor) | "Enable stage tracking" | compact tracker beside the log; "Show fiducials" checkbox in the raster toolbar, default **off** | measures and displays drift; moves nothing |
| Tracking (correct) | operator switches mode | applied offset | once per sweep at the Y turnaround, only while **in-zone** (OI-8) |

Mockups: `docs/mockup-stage-tracking-compact-v2.png` (default, fiducials hidden), `docs/mockup-stage-tracking-compact.png` (fiducials shown).

### 1.2 Tips when running sweeps yourself
1. Engage feedback before RUN, and confirm the feedback indicator.
2. Let the head settle after approach or motor moves (Oct 22 drifted 4 nm/min right after the crash and retract). A few minutes of halted tunnelling with feedback on is cheap insurance.
3. Change one thing per sweep pair, and change it at a Y turnaround, not mid-sweep.
4. Prefer changing KIGA alone over "Apply settings", which re-sends everything (geometry included).
5. Add a journal note at each change; the timeline and replay rely on them.
6. Raw capture (100 kHz) currently records only while the scan is halted, not during scanning (I-9). Plan short halted holds where raw data is needed.
7. Note your trace/retrace overlap (Drift corr X/Y) setting in a journal note when you change it; replay cannot recover it otherwise (OI-7).
8. Avoid the lowest bias settings on an unknown or freshly crashed tip; start at a larger gap and step closer (T4).

---

## 2 · Open issues

### OI-1 · Most scan samples have no tunnelling current · `investigating`
1. Status-stream ADC (200 Hz), share of samples with no current (ADC below −20), in range, and clipped (32767):

| Phase | No current | In range | Clipped |
|---|---|---|---|
| Tip far (19:03) | 5% | 95% | 0% |
| Pre-crash tunnelling, feedback off (19:09–19:10) | 43% | 57% | 0% |
| **Halted, feedback on (19:22–19:24)** | **0%** | **99%** | 0.1% |
| Tip-check scan #12–#13, KIGA 1.14 | 56% | 38% | 5.5% |
| KIGA 1.14 / 2.3 / 4.6 / 9 scans | 65 / 61 / 53 / 55% | 25 / 31 / 40 / 39% | 9.7 / 8.4 / 7.2 / 6.7% |
| Operator scan, KIGA 3.07 (19:42–19:52) | 52% | 47% | 1.4% |

2. "Halted" means the scan is stopped and the tip sits at one X/Y spot with feedback holding the current. No image is formed then; it only shows that the loop can hold the current perfectly when the tip doesn't move laterally.
3. Images come only from scanning, and while scanning the loop loses the current in more than half the samples. In the error image those samples are the **bright majority** (error = setpoint − log|current| is high when the current is missing); the **dark minority** is where the tip came close (high or clipped current). This is the analysis reading; OI-4 and T1 settle it.
4. Contributors: the loop is slower than one line (~80% direction-flip share), the post-crash surface, and the ADC offset with `abs()` (OI-2, OI-3).

### OI-2 · The `abs()` in the error, and the zero substitution · `investigating`
1. Pseudo-code and numbers: `docs/test-plans/phantom-offset-handoff.md` §1 and §3.
2. **Why `abs()`:** the current's sign follows the bias sign; the magnitude lets one loop serve both polarities.
3. **Why 0 → 32767 (original thinking):** added in the July 15 continuous-scan milestone with the comment "LTC2326-16 outputs 0 when clipping". If an overranged ADC returned 0, the loop would read "no current", extend toward the sample and plunge. Mapping 0 to full scale makes overrange retract instead: a safety patch.
4. **What Oct 22 shows:** clipping read **32767** (6–10% of scan samples), not 0; exact zeros were 0.0–0.1% during the sweep. The one long run of zeros came at 19:51, at the end of the session (ADC exactly 0 for over a minute, Z near its extended limit); the substitution then slewed Z to full retract. So the zero-means-clipped assumption does not match how clipping looked on Oct 22, but the patch did act as a safety net at 19:51. The ADC's real overrange behaviour needs checking (I-8).
6. **Measured impact on scan data (status stream, ADC before substitution, #12–#31):** the ADC reads exactly 0 on **0.1% of scan samples**, mostly as a no-current signal (neighbouring readings around −27 to −58) crosses zero. Each is repainted as full-scale current: at ~19 samples per pixel, **~2% of image pixels get a false dark speck** (~3% of the error range each), and the loop gets a one-tick full-strength retract kick. These specks are absence of signal shown as dark, so for them the operator's "dark = absence" reading is literally right.
7. **Blast radius on Z** (operator question): one substituted tick moves Z by KIGA × 268,052 ÷ 65,536 position units (`stm_firmware.hpp:328–332`): ~9 units at KIGA 2.3, about 0.6 of a Z-DAC count, against normal scan motion of up to ~2,900 counts in 0.1 s. During #12–#31 there were 299 isolated zero readings (single 5 ms status samples): small jolts, ~1% shift in the loop's balance. **Sustained zeros are different:** the 47 s run from 19:51:16 drove Z from fully extended (65,468) to fully retracted (0) within 0.2 s, ending that scan. Any sustained zero run mid-scan would cost the rest of the scan and a re-engage. Proposal: only treat 0 as clipped if the previous readings were high (a real overrange), and flag sustained zeros as an ADC/analog fault instead of retracting silently.
5. **Model to test:** with the scan-time offset, the loop pushes back weakly when lost and pulls hard when clipped, predicting ~5× more time lost than clipped (observed 8–9×). Offline test: I-1.

8. **The error is signed, and the loop uses the sign** (values from `logTable.hpp`, setpointLog = 256,233):

| Situation | ADC | Error | Loop action |
|---|---|---|---|
| Clipped (> 102 nA) | 32767 | −268,052 | pull back hard |
| 10× too much current | 1600 | −115,826 | pull back |
| 2× too much (tip ~0.34 Å too close) | 320 | −34,795 | pull back |
| At setpoint (500 pA) | 160 | 0 | hold |
| 2× too little (tip ~0.34 Å too far) | 80 | +34,640 | push forward |
| 10× too little | 16 | +113,367 | push forward |
| No current while scanning | −55 → abs 55 | +53,252 | push forward, weakly |
| No current, idle | −15 → abs 15 | +116,424 | push forward |
| ADC exactly 0 (substituted) | 0 → 32767 | −268,052 | pull back hard (wrong sign) |

   Equal size, opposite sign = the same height error (log feedback). Images store this signed error per pixel: dark = most negative (too close), bright = most positive (too far). Weak spots: beyond the clip or the noise floor the size is lost (direction only); `abs()` loses the current's sign so no-current pushes weakly; the zero substitution gives the wrong sign; and a pixel averaging "too close" and "too far" ticks can land at a middle colour that looks like "at setpoint".

### OI-3 · The phantom offset while scanning · `open`
Standalone write-up with all data points, hypotheses and design questions: `docs/test-plans/phantom-offset-handoff.md`. Summary: no-current readings sit at −15 to −25 when not scanning and −50 to −64 while scanning, including with the surface out of reach. Tests: I-2, T2.

### OI-4 · Display convention: dark must always mean valleys · `open` (fix: I-10; audit: I-7)
1. **Standard to adopt:** bright = high (peaks), dark = low (valleys), in every view and every report.
2. **What each view shows today** (`live_raster.py:211–234`; replay and reports show raw values):

| View | Channel shown | A peak (surface closer to the tip) appears | Meets standard? |
|---|---|---|---|
| Live, constant height | error converted back to current | bright | yes |
| Live, constant current | raw feedback error = setpoint − log of current | **dark** | no, inverted |
| Live, Z panel | raw Z (higher = extended toward the sample) | **dark** (valleys bright) | no, inverted |
| Replay viewer, MORPHOLOGY report | raw error and raw Z | **dark** | no, inverted |

   This is why the meaning of dark appeared to switch between constant current and constant height.
3. **Fix:** display height as −Z and the error channel as −error (equivalently, log current), so a peak is bright in both; keep the linearized-current view for constant height (already correct). Apply in live raster, replay and report figures (I-10).
4. **Reading Oct 22 under the standard:** the dark dot and "A" in the error images are high current, i.e. where the surface came closest to the tip: **high points**. Displayed to the standard they would be bright. This agrees with the operator's reading that the dot is the top of the mound; the earlier disagreement was the display inversion, not the physics. Exception: ~2% of pixels are false dark specks from the zero substitution (OI-2.6).
5. **Other ways colour can mislead:** `abs()` makes a no-current −55 and a real +55 identical (OI-2); auto colour levels (live "Auto/cycle", replay "auto levels" 2–98%) re-stretch every frame, so a colour is relative to that frame (I-7).
6. **Proposals:** fixed-scale option; explicit colours for clipped and no-current pixels; per-pixel clipped/no-current counts in frame files.
7. **Bench confirmation:** T1.

### OI-5 · Bias, gap resistance and gain · `planned`
1. **Two different resistances:**
   - The **preamp feedback resistor** (100 MΩ here) is a fixed part. It sets the preamp gain: how many volts (ADC counts) per amp of current.
   - The **gap resistance** R = bias ÷ tunnelling current is a property of the vacuum gap between tip and sample. The feedback loop holds it constant by adjusting the tip height. It changes whenever bias or setpoint changes.
   - On Oct 22 they happened to be the same number: 49.6 mV ÷ 500 pA ≈ 100 MΩ.
2. **Tip height follows the gap resistance:** lower R = closer tip. At ~7 mV and 500 pA, R ≈ 14 MΩ, about 7× closer in conductance than Oct 22.
3. **Closer (low R):** sharper lateral resolution and stronger contrast, but more tip–sample force, more clipping and more crash risk. Consistent with the experience that lowest bias gives better images.
4. **Further (high R):** wider effective probe (more lateral averaging), more stable, less contrast. Bias selects which electronic states contribute (an energy window), not depth.
5. **Gains, kept separate:** loop gain (KIGA: Z response speed), preamp gain (1X: current per count), and setpoint (current the loop holds). A higher preamp gain lets a smaller setpoint be measured, so the tip can sit further away at the same bias.
6. Unverified: the bias DAC → volts mapping and sign (tunnelling reads positive at a reported negative bias). T1 and T4.

### OI-6 · KIGA test design: the scan stopped at every step · `planned`
The Oct 22 script halted for 30 s, re-sent every setting and restarted the scan at each gain. The live view looked stopped, sweeps were lost for fiducial analysis, and gain was confounded with restart effects (X/Y jump at RUN, creep). Fix: change KIGA **while scanning**, KIGA-only, at a Y turnaround. Raw capture does not record during scans (I-9), so keep a short halted hold only where a spectrum is needed. Retest: T3. Command path: I-5.

### OI-7 · Trace and retrace · `to scope`
1. Trace and retrace are mirrors of each other, but only after their offset is compensated. The live GUI does that by hand (Drift corr X/Y); **nothing in post-processing applies it**, and the setting is not recorded with the data, so any analysis that uses retrace must compensate deliberately.
2. Oct 22 tracking used trace only for the error channel, but averaged trace and retrace without compensation for the Z channel. Change: trace-only in both channels (I-3); treat retrace as a separate stream until a compensation step exists.
3. Proposal: journal the trace/retrace offset whenever it changes, and add a measured compensation step (cross-correlate trace with flipped retrace per sweep) to replay and analysis.

### OI-8 · Stage correction vs constant current · `open`
1. Time scales separate: the current loop crosses over at 36–72 Hz; a stage correction once per sweep is ~0.04 Hz. Apply each correction as a short ramp at the Y turnaround.
2. **Controller:** no full PID needed. A sampled estimator of position and velocity (an alpha-beta or simple Kalman filter, i.e. proportional plus integral on the measured offset, with velocity feed-forward) is enough. A derivative term would amplify measurement noise.
3. **In-zone flag** before any correction: lock confirmed (≥ N fiducials, both channels agree); in-range current share above a threshold; clipped share below a threshold; Z within its safe range; no abrupt tip event in the last sweep. Out of zone: monitor only, coast on the last velocity.

### OI-9 · The 158.7 Hz resonance · `open`
1. **Evidence:** sharpest line in both Z and current in every halted hold at every gain (not a scan artifact); Z power grows ~4.5× at KIGA 2.3 and ~19× at 4.6 relative to 1.14; the loop went unstable at KIGA 9, whose crossover (~141 Hz) approaches it; the Oct 15 analysis of Sep 24 streaks independently predicted ~159.5 Hz. Bin width 3.05 Hz, so 157–160 Hz.
2. **Coincidence check:** not mains (120 / 180 Hz), not the status stream (200 Hz), not the raw-tap block rate (195 Hz), not the line rate.
3. **Confidence:** high that it is a real oscillation in the tip–sample (Z) path; moderate that it is mechanical.
4. **Leading hypothesis:** a mode of the larger structures, the lever or the eddy-current-damped plate on brass posts; the piezo disc with stem (~3–4 kHz) is far too stiff.
5. Tests: T7. Report section: I-4.

### OI-10 · Calibration · `open`
Lateral 5 nm/V and Z 3 nm/V are placeholders; every nm, pm/s and nm² figure scales with them. T8.

### OI-11 · Raw-capture losses · `open`
Early Oct 22 sessions lost 4–9% of raw blocks; from 19:26 on, 0%. Mechanism: when the PC stops reading for 120 ms, the Teensy discards the rest of a frame. The working suspicion is security software (firewall / real-time scanning) slowing the PC's reads or writes. T9 compares capture with that software's scanning relaxed for the data folder, or capture redirected.

### OI-12 · Software · `open`
1. GUI exits without a clean close (twice on Oct 22), and a journal silent after 19:42 while recording continued.
2. Live raster labels up/down the opposite way to replay (streak plan 5d).
3. Line-numbering bug (sweeps marked PARTIAL 255/256; streak plan item 2).
4. Importing the GUI creates an empty day folder with `stm.log`.

### OI-13 · Tip state · `open`
Every quality number after 19:10:30 on Oct 22 is on a crashed tip. Recover or replace before T3–T6.

### OI-14 · Horizontal streaks and cross-hatch scanning · `open` (existing plan)
1. Already planned elsewhere:
   - `docs/meetings/2026-10-streak-followup-plan.md` §4, **cross-hatch scanning (proposed build)**: firmware `SWXY` swaps the fast axis between frames, a bit in the line header flags orientation, replay rotates swapped sweeps back, and the pair is merged in Fourier space so each frame's horizontal-streak band is filled from the other. Go/no-go decision still open; to be bundled with firmware fixes 1–3.
   - `docs/TODO-streak-anisotropy-test.md`: whether streaks are temporal events or spatial features.
2. Oct 22 numbers that bear on it: Z streak anisotropy (row-to-row ÷ column-to-column gradient energy) 107–122; error channel ~8, at every gain.
3. Proposal: make cross-hatch a milestone (section 4) after the firmware safety fixes.

### OI-15 · Getting 3D intentionally · `open`
The contour-based 3D on Oct 22 depended on the slice level moving for uncontrolled reasons. Deliberate options:
1. **Registered Z topography (routine):** with feedback following the surface, the Z image is the height map; lateral tracking keeps the same patch registered across sweeps. Limited today by the ~80% lag share.
2. **Tip-Z steps with feedback off:** constant-height slices at known Z offsets, each a contour at a known height. Direct, but at crash risk; small steps away from the sample first.
3. **Setpoint steps with feedback on:** each factor of 2 in current ≈ 0.35 Å of tip height (T5). Safe and controlled.
4. **Bias steps:** change both the gap and which electronic states contribute, so geometry and electronics mix. Useful for spectroscopic maps, less clean for shape.
5. **I(z) spectroscopy on a grid:** current vs height at each point; a full 3D current map and the real decay constant for converting 2–4 into nm.

---

## 3 · Test sequences (bench)

Each: safety checks, procedure, measurement, decision. Record results in place.

### T1 · What dark means · `planned`
1. Safety: rules 0.1–0.6; feedback **off**; tip tunnelling, not in contact; first Z step away from the sample.
2. Procedure: at a fixed X/Y, halted, raw tap on. Step Z by small known amounts away from and toward the sample (smallest step first), dwelling a few seconds each.
3. Measurement: ADC sign and value vs Z; which colour each state shows in live (both display modes) and replay.
4. Decision: settles OI-4 and the bias sign (OI-5).

### T2 · Phantom offset · `planned`
1. Safety: tip well retracted (ADC at idle, no tunnelling possible).
2. Procedure: normal scan with the tip retracted: (a) feedback off, Z fixed; (b) feedback on (Z rails, no current); (c) two line rates; (d) X/Y scan amplitude zero. Needs 100 kHz data during scanning (I-9); until then, use the 200 Hz status stream, which can show the offset level but not its shape within a line.
3. Measurement: offset on trace vs retrace, vs line rate, with vs without Z motion (`phantom-offset-handoff.md` §4).
4. Decision: identifies the cause; informs the firmware offset fix.

### T3 · KIGA retest, done properly · `planned`
1. Prerequisites: recovered tip (OI-13); T1 if possible.
2. Safety: engage before RUN; guards 0.4; Z limit set from the engaged position.
3. Procedure: one area, 30 nm, fixed bias and setpoint; RUN once and keep scanning; change KIGA only at Y turnarounds: 2.3 → 3.07 → 4.6, ≥ 2 Y-cycles each; one short halted hold per gain if the 158.7 Hz amplitude is wanted (raw records only while halted, I-9); stage tracking in monitor mode.
4. Measurement: drift-corrected same-direction repeatability (target ≥ 0.7), direction-flip share, 158.7 Hz amplitude, in-range / clipped / no-current shares.
5. Decision: default KIGA.

### T4 · Gap-resistance ladder · `planned`
1. Safety: start at the largest gap and step closer; stop at the first clipping above a few %; nothing below ~14 MΩ without the operator's call.
2. Procedure: fixed KIGA and line rate, same patch (tracking on), setpoint 500 pA, bias for R ≈ 1 GΩ (0.5 V), 300 MΩ (0.15 V), 100 MΩ (0.05 V), 30 MΩ (0.015 V), 14 MΩ (0.007 V); 2 Y-cycles each. Optionally repeat at a second setpoint to separate bias from R.
3. Measurement: in-range / clipped / no-current shares, drift-corrected repeatability, edge sharpness, noise.
4. Decision: working gap for imaging; tests "lower bias = better precision".

### T5 · Setpoint-step contour calibration · `planned`
Fixed KIGA and bias, tracking on; setpoint 250 → 500 → 1000 pA, 2 Y-cycles each. Cross-section area vs setpoint for a tracked feature: a controlled contour stack (OI-15.3).

### T6 · 10-minute hold with tracking (monitor) · `planned`
Fixed everything, tracking in monitor mode, 10 minutes. Drift path and velocity stability; cross-section stability; Z ramp vs registered Z of the same patch.

### T7 · 158.7 Hz source · `planned`
Halted, feedback on, raw tap on; 30 s baseline; gentle taps on lever, sample plate, frame and table in turn; then added damping or mass on one part at a time. Which tap excites 157–160 Hz; whether damping or mass shifts it.

### T8 · Lateral and Z calibration · `planned`
Graphite lattice (0.246 nm) or a gold monatomic step (0.235 nm).

### T9 · Raw-capture losses · `planned` (needs an IT decision)
Same capture with the data folder's real-time scanning relaxed, or capture redirected; compare lost blocks and firmware drop counts.

---

## 4 · Milestones

### 4.1 Resolution-report action items (Oct 15), status after Oct 22

| # | Action | Status | Next |
|---|---|---|---|
| 1 | KIGA sweep 1.14 → 9 | **done (Oct 22, first pass)**: 4.6 last stable, 9 oscillated; quality confounded by crashed tip and restarts | T3 |
| 2 | Slower lines (≤ 10 Hz) | ran at ~10.5 Hz only | T3 extension: 5 Hz at 4.6 |
| 3 | Loop simulation to pick settings | in report (Fig. 14b) | use before T3 |
| 4 | Halted tunnelling raw captures | **done** (30 s holds): 158.7 Hz identified | T7 |
| 5 | Tap test | not run | T7 |
| 6 | Isolation-plate friction test | not run | with T7 |
| 7 | 384 px scan to split 159.5 vs 231 Hz | superseded: halted holds show 158.7 Hz | drop |
| 8 | Sound sweep 100–300 Hz | not run | with T7 |
| 9 | Laptop on battery (ground loop) | not run | with T2 |
| 10 | Status stream off / pixel-count A/B | not run | with T2 |
| 11 | Non-tunnelling scan (electrical pickup) | not run; now also the phantom-offset test | T2 |
| 12 | Graded zoom ladders | not run | after T8 |
| 13 | Lateral calibration on a known lattice | not run | T8 |
| 14 | Z sine-sweep firmware test | not run | firmware milestone |
| 15 | Fold + repeat + both-halves + zoom checks in replay | partly: fiducial drift tool (`fiducial_drift.py`) | integrate into replay |
| 16 | Log real X min/max per line (DIAG) | not run | firmware milestone |
| 17–18 | Move/split per-line USB transmission; frame buffer | not run | after OI-11 |
| 19 | Code-review fixes (retract direction, setpoint clamp, BUSY wait, line numbering) | open | firmware milestone, before long automated runs |
| 20 | Softer cables | not run | hardware |
| 21 | Stiffer head (wedge assembly) | future | hardware |
| 22 | Documentation (isolation box, preamp version and gain) | open | |

### 4.2 Proposed order of bench sessions
1. **Session A (diagnostics, no imaging quality needed):** T1 (what dark means), T2 (phantom offset), T7 (158.7 Hz taps), action items 8–10.
2. **Firmware milestone:** safety fixes (RTRC direction, setpoint clamp), RUN requires feedback (or GUI gate), KIGA-only command path, offset handling decided from T2, optionally cross-hatch `SWXY` (OI-14).
3. **Session B (imaging, recovered tip):** T3 (KIGA retest, continuous), T4 (gap ladder), T5 (setpoint steps), T6 (10-minute hold with tracking).
4. **Session C:** T8 calibration, then zoom ladders (item 12).

---

## 5 · Offline investigations (no hardware)

| ID | What | Status |
|---|---|---|
| I-1 | Test the OI-2 lost-vs-clipped model against the 100 kHz raw tap | next |
| I-2 | Phantom offset in existing raw data | **blocked**: Oct 22 raw capture has no data during scanning (blocks only while halted). Needs I-9 or T2 |
| I-3 | Rerun fiducial tracking with trace-only Z (OI-7) | queued |
| I-4 | Add a 158.7 Hz section to the morphology report (OI-9) | queued |
| I-5 | AI tooling: change Ki live through the bridge without halting or re-sending other settings, as the operator does (OI-6) | queued |
| I-6 | Verify `docs/stm-techniques-backlog.md` against primary sources; add references | queued |
| I-7 | Audit auto colour levels in live raster and replay: algorithm, per-frame vs shared, how they change what dark means | queued |
| I-8 | ADC overrange behaviour: what the LTC2326-16 outputs when overranged (datasheet + T1/T2 data); revisit the 0 → 32767 substitution | in progress: substitution impact measured (OI-2.6) |
| I-9 | Why raw capture records no blocks during scanning (file open, blocks only while halted); fix so the 100 kHz tap covers scans | queued |
| I-10 | Standardise the display convention (dark = valley) in live raster, replay and reports (OI-4) | queued |
