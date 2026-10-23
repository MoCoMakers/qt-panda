# Streak follow-up: experiments and code fixes

**Status:** planned. Items run at the next bench meeting, then get results filled in below.
**Written:** 2026-10-08, from the Sept 24 streak diagnosis and the FW 5.6 code review.
**Live checklist:** [Streak Follow-up Plan](https://claude.ai/artifact/A1qjZQyKMdVhdqWRzhQkpi?sk=K0H7yxmbCg9doQIxh-K_9w). Ticks in it are saved only in each viewer's own browser, so record outcomes here.
**Background:** [Sept 24 streak diagnosis report](https://claude.ai/artifact/9g7nEdVj63QNofbMQq2vQc)
**Related:** [TODO-streak-anisotropy-test.md](../TODO-streak-anisotropy-test.md), [ai/hypotheses/](../ai/hypotheses/)

The horizontal streaks in the Sept 24 constant-current scans come from a feedback loop that is too slow for the scan. KIGA 1.1444 gives a crossover of about 18 Hz against 32.55 Hz lines. Each step leaves a lag tail of about 150 px, and that tail lands slightly differently on every line. Inside those lag bands, pixels differ from row to row about 40× more than along the row. On settled terrace the noise is the same in both directions. This meeting tests that on the bench and works through the code review findings.

> **Before anyone touches the rig.** Don't press Retract (RTRC). The firmware
> sends Z to DAC 50000, which is the fully extended end, so it drives the tip
> **toward** the sample (`stm_firmware.hpp:614`). To back off, turn constant
> current off and lower Z by hand, or retract with the motor. Power the analog
> supply about 5 s before the Teensy, then click Reset (see
> [DAC_BOOT_ORDER.md](../DAC_BOOT_ORDER.md)).

## Agenda

| Block | What | Output |
|---|---|---|
| 1 | Decide the KIGA default (code review item 4) | One value to use on the bench |
| 2 | Bench: gain sweep, line-rate sweep (including 3 Hz), setpoint headroom | Frames tagged in the journal, plus a halted-tunneling baseline |
| 3 | Code review follow-ups: items 2, 3 and the item-5 group | An owner and order for each fix |
| 4 | Cross-hatch scanning: go or no-go on the build | Decision, and a scope if it's go |

---

## 1 · Decision: KIGA default (review item 4)

The code now defaults to KIGA 4.0 at 100 kHz (`main.py`, Ki box; 25 kHz base 16.0), a crossover of about 60 Hz. The reviewer's point: a pure integrator crossing over at f_c stays stable against a Z resonance at f_r only while that resonance's Q < f_r / f_c. At 60 Hz and a 100–300 Hz resonance, that means Q below 1.7–5. Piezo Z modes often have Q of 10 or more. We measured a broad bump at 100–300 Hz, which suggests low Q, and a sharp 198 Hz line, which could be a high-Q mode. We don't yet know which one governs.

| Option | Crossover | Tolerates resonance Q up to | Notes |
|---|---|---|---|
| Keep 4.0 | ~60 Hz | ~1.7–5 | Fastest. Every Apply or RUN sends this value, and it hasn't been checked on the rig |
| **Drop to 2.3 (recommended)** | ~36 Hz | ~3–8 | 2× faster than before; revisit after the gain sweep |
| Revert to 1.1444 | ~18 Hz | ~5.5–16 | Known stable, but this is the setting that produced the streaks |

- [ ] Pick the default and record the reason in the session journal. To set 2.3, change the Ki box's 25 kHz base to 9.2.
- [ ] Re-decide with the gain-sweep results at the end of the meeting.

**Decision:** _
**Reason:** _

---

## 2 · Bench experiments

Use one area for every run: a step edge like Sept 24 #1572, 30 nm field. Keep the tip, bias and area fixed. Change one setting at a time. For each run, add a journal note when it starts and when it stops, so the replay timeline can bracket it.

### 2a · Loop-gain sweep (no code needed)

- [ ] Step KIGA 1.14 → 2.3 → 4.6 → 9 on the same area, with at least two full sweeps at each value.
  - Watch the tails in the error channel shrink and the steps appear in Z.
  - Stop at the first sign of ringing near 200 Hz. It shows up as fine diagonal striping along the line: about 84 px per cycle at 32.55 Hz, or about 24 px at 10 Hz on 256 px.
  - Note the last clean KIGA, and use about ⅔ of it as the default.

| KIGA | Line rate | Tail width (px) | Steps visible in Z? | Ringing? | Frames / journal time |
|---|---|---|---|---|---|
| 1.14 | | | | | |
| 2.3 | | | | | |
| 4.6 | | | | | |
| 9 | | | | | |

#### 2a results · 2026-10-22, 19:25–19:34 (automated, copilot bridge)

Conditions: 30 nm, 512 px/line (256 × 256), 10 Hz requested (10.45–10.71 Hz measured), 500 pA, Kp 0, 100 kHz ISR. Each step: 30 s halted hold (CC on, raw tap 100 kHz), then two Y-cycles. Tip had touched the sample at ~19:13, so the junction was noisy throughout (current ln-std ≈ 1.0–1.4 at rest). Journal: `session_1792709026869.jsonl`, notes prefixed "Claude KI-ladder".

| KIGA | Direction-flip (lag) share, per image | Z std (rel.) | Halted hold: Z power 100–300 Hz | Sharp line | Outcome |
|---|---|---|---|---|---|
| 1.14 | 0.87–0.94 | ~870 | 3.1e10 | 158.7 Hz | clean |
| 2.3 | 0.88–0.91 | ~1,670 | 1.4e11 | 158.7 Hz | clean |
| 4.6 | 0.79–0.84 | ~2,660 | 5.9e11 | 158.7 Hz | clean (last clean) |
| 9 | 0.85 (1 cycle) | ~5,260 | 6.3e11 | 158.7 Hz | **unstable while scanning**: current lost 60% / saturated 7% of the time, Z swung ~11,000 codes; Z guard (46,000) halted it after 69 s |

- **Default set:** KIGA 3.07 (⅔ of 4.6), applied to the running GUI at 19:35. The code default (4.0) was not changed.
- **The resonance is 158.7 Hz.** It is the sharpest line in Z and current at every step of the halted holds (up to 50× the band median in Z). This settles the 159.5 vs 231 Hz ambiguity in the resolution report in favour of ~159 Hz. Its Z power grew ~20× from 1.14 to 4.6, and the loop went unstable once the estimated crossover (~141 Hz at 9) approached it.
- **Image quality: weak, and only judgeable after drift correction.** Without drift correction the folded (surface) part repeated at only 0.04–0.20. With stage drift measured by template tracking (66 pm/s up the frame, ~1.0 nm hysteresis offset between up and down sweeps), neighbouring sweeps repeat at 0.18–0.57 (2.3), 0.37–0.62 (4.6) and 0.39–0.45 (9): real surface, about half a good tip's repeatability, KIGA 4.6 slightly best. Details: `TeamUpdate/data/2026-Oct-22/MORPHOLOGY-2026-10-22.html`. The tip had crashed at 19:10:30, before the sweep. Repeat steps 1.14 → 2.3 → 4.6 with a recovered tip, comparing sweeps only after drift correction.
- **Drift-corrected comparison:** `TeamUpdate/data/2026-Oct-22/KIGA-SWEEP-2026-10-22.html` repeats the comparison on the same patch of sample after drift compensation (67 pm/s up the frame): same-direction repeatability is best at KIGA 4.6 (error 0.49–0.54, Z 0.46–0.62, vs 0.31–0.40 / 0.26–0.33 at 2.3), and the per-gain averages show the same morphology at every gain. It also lists the open questions on how to read the error colour.
- **Guard lesson:** the "current lost for 5 s continuously" guard never fired at KIGA 9, because the current was flipping on and off rapidly. Trigger on the dropout fraction in a window instead.

### 2b · Line-rate sweep, including 3 Hz

The requested and real line rates differ, because the firmware rounds samples per pixel down to a whole number (100 kHz ISR, 512 px per line):

| Requested | Samples/pixel | Real line rate | 256-line sweep takes | Why this rate |
|---|---|---|---|---|
| 30 Hz | 6 | 32.55 Hz | 7.9 s | The Sept 24 condition |
| 10 Hz | 19 | 10.28 Hz | 25 s | The new default |
| 5 Hz | 39 | 5.01 Hz | 51 s | Tails should be ~6× shorter than at 30 Hz |
| **3 Hz** | 65 | **3.005 Hz** | 85 s | Sits on the 3.05 Hz disturbance |
| 2.8 Hz | 69 | 2.83 Hz | 90 s | Just below 3 Hz |
| 3.2 Hz | 61 | 3.20 Hz | 80 s | Just above 3 Hz |

- [ ] Run 30 → 10 → 5 Hz at a fixed KIGA. The tails should shrink in pixels roughly in proportion to the line rate. Note the real rate (the GUI's "Realized" label) in each journal note.
- [ ] Run 3 Hz, with 2.8 and 3.2 Hz on either side.
  - At 3.005 Hz lines, a 3.05 Hz disturbance arrives at almost the same phase on every line. If the ~3 Hz source is real, the row-to-row wobble should mostly disappear, and a slowly drifting tilted band pattern should appear instead.
  - The beat is 3.05 − 3.005 = 0.045 Hz, so the pattern should repeat about every 22 s, roughly every 66 lines.
  - At 2.83 and 3.20 Hz the beat should speed up to about 0.22 and 0.15 Hz, a repeat every ~13–20 lines, with the bands leaning opposite ways.
  - If the wobble follows these predictions, the 3 Hz source is confirmed. If it doesn't change, the 3 Hz idea is wrong.
  - Each sweep takes 85 s, so thermal drift will show. Consider 128 px per line here.
- [ ] Record a clean noise baseline: scan halted, tip tunneling, 2 minutes or more. Raw capture only runs while the scan is halted. The 19:29 window in the Sept 24 report had a loop that hadn't settled, so it isn't a reliable baseline. This recording replaces it and settles whether the 3.05 Hz and 198 Hz lines are always present.

| Real line rate | Tail width (px) | Row wobble period (rows) | Pattern seen | Frames / journal time |
|---|---|---|---|---|
| 32.55 Hz | | | | |
| 10.28 Hz | | | | |
| 5.01 Hz | | | | |
| 3.005 Hz | | | | |
| 2.83 Hz | | | | |
| 3.20 Hz | | | | |

### 2c · Rail headroom (small effect)

- [ ] Compare setpoints of 1 nA, 500 pA and 100 pA at the same KIGA and line rate. A lower setpoint leaves more room before the ADC saturates (current > ~102 nA), so Z can retract faster on a step:
  - 1 nA (320 LSB): ln(32767/320) = 4.63 ln of room.
  - 500 pA (160 LSB): 5.32 ln, about 15% faster.
  - 100 pA (32 LSB): 6.93 ln, about 50% faster. An earlier figure of "5.8 ln, about 25%" used 100 LSB instead of 100 pA.
  - At 100 pA, check that the current noise floor (about 20 pA rms raw) doesn't take over.

---

## 3 · Code review follow-ups

Source: the FW 5.6 code review of 2026-10-01. Each fix is checked on the Docker emulator first (`socket://127.0.0.1:9000`). Flash only when the rig is free and the GUI's serial port is closed. Claude prepares changes and commit commands; the operator runs the commits.

### Safety item: blocks rig work

- [ ] **Item 1 · Make RTRC retract away from the sample.**
  - In `stm_firmware.hpp:614`, ramp Z to a low code (0 or 10000) instead of jumping to 50000.
  - Sync `z_pos` and the integrator state so turning constant current back on doesn't jump.
  - The copilot's `/scan/retract` uses the same path.

### Item 2 · Line-number bug at the bottom of each Y cycle

- [ ] Move the Y-bottom resync after line stamping, or make it a mismatch counter reported by DIAG.
  - **The bug:** since FW 5.6, the resync fires on the same ISR tick as the last pixel of the last line. From the second cycle on, every line is numbered one too high. With line repeat above 1, adjacent rows get mixed.
  - **Check:** first with `fwsim.py` (the reviewer's port of the firmware counters, in the 2026-10-01 session scratchpad), then on the emulator.
  - **Afterwards:** re-measure the up/down row offset. The `drift_corr_y = −4` default may have been absorbing 2 rows of this bug, so recalibrate it.
  - **Open question:** whether to correct old `.frames` files in the replay index with a known +1 shift. The raw data stays unmodified.

### Item 3 · Setpoint bounds and the "no setpoint" check

- [ ] Clamp the setpoint to 1–32767 in `setSetpoint()` (`stm_firmware.hpp:620`) and `turn_on_const_current()` (line 986), and reject 0.
  - Today, SETP or CCON above 32768 (above about 20 nA at 5X gain) reads past the log table, and Z can run to full extension.
  - The engage check compares `setpointLog` against 0, but `logTable[0] = 34952`, so SETP 0 is accepted.
- [ ] Add the matching clamp to the GUI's setpoint box, taking preamp gain into account.

### Item 5 · The remaining findings

| Done | Finding | Where | Suggested fix | Priority |
|---|---|---|---|---|
| [ ] | X/Y jump to the scan corner in one tick at RUN, and aren't parked on HALT | firmware | Ramp to the scan start and park on stop; report X/Y in the status frame | high |
| [ ] | A USB stall can send a garbled scan line and silently drop the next one (5b below) | firmware `emitPendingLine()` | Sequence-check the buffer swap and flag torn lines; show dropped rows in the image | medium |
| [ ] | The 4-character command parser can't resynchronise after a dropped byte (5c below) | firmware + GUI | Newline-terminated commands with an echo or error reply | medium |
| [ ] | Live raster and replay call the sweep halves "up" and "down" the opposite way round (5d below) | GUI + replay | One naming convention everywhere, documented | medium |
| [ ] | Right-click recenter is off in X by up to a quarter of the scan | `live_raster.py:644` | `px/self._half − 0.5` | quick |
| [ ] | Changing geometry mid-scan leaves the trace/retrace split misaligned until the next RUN | GUI + firmware | GUI does HALT → RUN on geometry change, or firmware refuses it while scanning | medium |
| [ ] | Frames metadata assumes a 40 µs ISR, so samples/pixel is recorded 4× low and the requested (not real) line rate is stored | `main.py:3651`, `raw_scan_reconstruct.py` | Firmware reports its actual scan settings; add a tick count to each line | medium |
| [ ] | KIGA is applied per ISR tick, so changing SETD silently changes the loop gain | firmware `setIsrGains` | KIGA in units of 1/s, scaled by dt in firmware | medium |
| [ ] | The SETD floor of 5 µs is too fast for the ADC: no BUSY check, and the read can come before conversion finishes | `main.ino:230` | Raise the floor to 10 µs; write the DACs before starting the conversion | quick |
| [ ] | The GUI's X/Y mirror drifts from the real DAC values after HALT, grid spectroscopy or TEST | `stm_control.py:316` | Fixed by reporting X/Y in the status frame (first row) | medium |

#### 5b · A USB stall can send a garbled scan line

- **How it works now.** The firmware has two line buffers. The ISR fills one while the main loop sends the other. When a line finishes, the ISR swaps buffers and sets a "send me" flag. The main loop writes the finished buffer to USB (512 px × 8 bytes ≈ 4 KB) and clears the flag (`emitPendingLine()`, `stm_firmware.hpp:636`).
- **What goes wrong.** The main loop can be delayed for longer than one line period:
  - the PC isn't reading;
  - a burst of raw-tap or status frames is going out;
  - a command whose argument takes up to the 20 ms parse timeout.

  In that time the ISR finishes the next line, swaps again, and starts writing into the buffer that's still being sent. The PC receives a line that starts as one row and ends as a later one, under the old row's number. The flag is then cleared, so the line that finished in the meantime is never sent. All that remains is the `droppedLineFrames` count.
- **Why it matters here.** A torn line shows as a single-row seam, which looks like a streak. The Sept 24 real-run scan file has 1634 dropped lines, and each one may have a torn neighbour. At 120 Hz lines a line lasts only 7.7 ms, so a single command sent mid-scan (20 ms parse timeout) is enough to cause one. At 3 Hz lines the risk is much lower.
- **Fix.**
  - Snapshot the buffer pointer, line number and a swap counter before sending, and compare the counter afterwards.
  - If it changed, mark the line as torn (a header bit) so the PC drops or flags it.
  - Show dropped and torn rows in the live and replay images instead of hiding them.

#### 5c · The command parser can't resynchronise after a dropped byte

- **How it works now.** Commands have no end marker. Once 4 bytes are waiting, `checkSerial()` (`main.ino`) takes exactly those 4 as the command name. Arguments are then read with `parseInt`/`parseFloat`, which skip anything that isn't a digit and wait up to 20 ms. An unknown 4-character name is ignored with no reply.
- **What goes wrong.** If one byte is lost or an extra one sneaks in (a stray newline, a malformed argument), every later 4-byte read starts in the wrong place:

  ```
  sent:      SETP 160KIGA 2.3HALT
  off by 1:  ETP  | 160K | IGA  | 2.3H | ALT…   → nothing matches, nothing reported
  ```

  Every following command, including STOP, is silently misread until a reboot. A second route: if an argument arrives more than 20 ms after its command name (a split USB packet on a busy host), `parseInt` returns 0. That gives `SETP 0`, which item 3 lets through. The late digits then become the start of the next "command".
- **Why it matters here.** The GUI believes every command landed. A desync during a gain sweep would invalidate the experiment without anyone noticing, and STOP or HALT might not get through.
- **Fix.** End every command with a newline. The firmware reads the whole line and replies with the command echoed and OK, or ERR. A bad line then costs only itself, and the GUI can confirm every setting. The firmware and the GUI's sender have to change together.

#### 5d · "Up" and "down" mean opposite things in live and replay

- **How it works now.** The firmware's line counter runs 0 … 2H−1 for each Y cycle. In the first half the Y DAC increases; in the second half it decreases over the same rows.
  - **Replay** (`sweep_index`, `sweep_player`) calls the first half "▲ up" and the second "▼ down".
  - **Live raster** calls the first half the "down sweep": it saves the "End of down sweep" snapshot when the counter crosses H (`live_raster.py:469`). It applies drift correction to the second half, which it calls the "up sweep".

  The live view flips Y on screen, so increasing Y draws downward. Each tool named the halves from a different reference.
- **What goes wrong.** Drift correction tuned on "up-sweep lines" in the live view is applied to what replay calls ▼ down. Choosing "▲ up only" in replay gives the other half. Comparisons of up/down offsets between the tools, including the 2-row offset from the item 2 bug, are comparing swapped halves.
- **Fix.** Name the halves after the hardware, for example "Y+ sweep" (first half, Y DAC rising) and "Y− sweep". Use those names in the live raster, the replay tool, the drift-correction tooltips and the docs. Keep the on-screen flip as a separate display setting.

---

## 4 · Cross-hatch scanning (proposed build)

- [ ] Go or no-go on building X/Y swap scanning.

**Idea.** Alternate which axis is the fast axis between back-to-back frames, then merge the pair. The streaks and the lag tails both follow the fast axis, while the real surface stays where it is.

**Scope if it's a go:**

| Part | Change |
|---|---|
| Firmware | `SWXY 0\|1\|2` swaps which DAC the fast counter drives, with offsets staying on their physical axes. Mode 2 toggles at every Y-cycle bottom |
| Wire | Bit 15 of the line header carries the orientation flag. Line counters are at most 1024, so the bit is free |
| Replay | `sweep_index` rotates swapped sweeps back by 90° and tags them with their orientation |
| Merge | Register the pair (shift plus skew), then blend them in Fourier space using wedge weights, so each frame's streak band (kx ≈ 0) is filled from the other frame |

**Limits:** it can't recover detail lost while the ADC was saturated, so fix the loop first (blocks 1 and 2). Bundle these firmware changes with the item 1, 2 and 3 firmware fixes so there's only one flash.

**Decision:** _

---

## Decisions to record at the end

- [ ] The final KIGA default, backed by the gain-sweep frames.
- [ ] Is the 3 Hz disturbance confirmed or ruled out, and what's the next step on its source (isolation stage, building)?
- [ ] The firmware fix bundle and flash date: items 1, 2, 3, the torn-line flag and the parser, plus cross-hatch if it's a go.
- [x] The sweep naming convention: **up sweep (▲) and down sweep (▼)**, as the replay viewer names them (decided 2026-10-23). The live raster still uses the opposite names, so item 5d remains to change it.

## Open cross-check with earlier hypotheses

[`ai/hypotheses/time-artifacts-piezo-vs-preamp.md`](../ai/hypotheses/time-artifacts-piezo-vs-preamp.md) describes a fixed ~400 µs time constant in the Sept 17 data. On Sept 24 the picture is different:
- Constant-height frame #932 (120 Hz lines, ~30 µs/px) showed a trace/retrace offset of only 0 ± 1 px.
- The constant-current frames #1572–1578 showed a flat 12–13 px (≈1.5 nm) offset along the whole line, which disappears when the loop is off.

So on Sept 24 most of the offset follows the feedback loop, not a fixed delay. Reconcile the two days before attributing streaks to the preamp or the drive chain.
