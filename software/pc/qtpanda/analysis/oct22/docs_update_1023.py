"""Docs update 2026-10-23: learnings, priorities, OI-17 scan paths, roadmap items."""
import os
TP = "C:/Users/enact/Projects/qt-panda/docs/test-plans"
s = ""


def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:70])
    s = s.replace(a, b)


p = os.path.join(TP, "2026-10-23-open-issues-and-tests.md"); s = open(p, encoding="utf-8").read()
rep("3. Proposal: make cross-hatch a milestone (section 4) after the firmware safety fixes.",
    "3. ~~Proposal: make cross-hatch a milestone after the firmware safety fixes.~~ **2026-10-23:** cross-hatch is now a *sequence* inside the scan-path work (OI-17, `scan-path-design.md`): the fast axis swaps between frames on the same area, and the pair is merged using the line-by-line drift registration.")
rep("### OI-15 · Getting 3D intentionally", """### OI-17 · Scan paths (experimental option) · `designed` (operator 2026-10-23)
A "Scan path" dropdown in Continuous Scan: today's raster stays the default and is untouched. Options: rotated raster (15°, 45°, 90°), cross-hatch sequence, Archimedean and Fermat spirals (out, in, out-in pairs), centre-return loops, spokes, rose / figure-8 with precession, and later a Custom file. Every named path lives in code, versioned and bit-exact between firmware and Python; every recording carries what is needed to reconstruct each sample's position (no orphan frames). Simulate first, against Sep 24 ground truth, with a piezo model and the measured drifts; firmware only when the operator chooses. Priority relative to calibration is open. Full design and contract: [scan-path-design.md](scan-path-design.md).

### OI-15 · Getting 3D intentionally""")
rep("2. **Firmware milestone:** safety fixes (RTRC direction, setpoint clamp), RUN requires feedback (or GUI gate), KIGA-only command path, offset handling decided from T2, optionally cross-hatch `SWXY` (OI-14).",
    "2. **Firmware milestone (one flash):** F2 retract fix (built), F8 tick timestamps (approved), F9 DAC-write guards, setpoint clamp, KIGA-only command path, offset handling decided from T2 (F4). Optional, if the operator chooses by then: the scan-path modes (OI-17), with mode 0 bit-identical to today. RUN mode choice and the clip guard (F1) are GUI-side and already built.")
rep("| I-10 | Standardise the display convention (dark = valley) in live raster, replay and reports (OI-4) | live + replay built 2026-10-23; reports pending |",
    """| I-10 | Standardise the display convention (dark = valley) in live raster, replay and reports (OI-4) | live + replay built 2026-10-23; report v2 uses it; v1 left as stored values (reference) |
| I-11 | Drift-registered replay mode: v2's line-by-line registration in the viewer (feature stays put, A/B compare the same sample patch) | proposed |
| I-12 | Scan-path library, reconstruction contract and simulator (OI-17 steps 1–2) | designed |
| I-13 | Z-drift split as a routine metric (same-sample Z rate, tilt part, time to the Z rail) (OI-16) | first split done (`analysis/oct22/z_drift_split.py`) |""")
s = s.rstrip() + "\n" + """
---

## 6 · Learnings and decisions, 2026-10-23

1. **Dark means valleys, now in software.** Stored Z and stored error both put a peak *low*. The live raster and replay now show −Z and −error by default ("Peaks bright"); saved data and TIFF/GSF exports stay raw (I-10).
2. **The circled Oct 22 dot was a summit that became a hollow.** In #20 it is high; from #21 its centre reads no current (~50 counts, the phantom offset through abs()) while a ring around it clips (~31,800 counts). The hollow is at least ~0.4 nm deep against its rim. It shows in the error channel at the 94th–100th percentile in #21–#26 and not consistently in Z. The leading explanation is the top pressed in at near point contact; the footprint test settles it (report v2, Section 3).
3. **Drift should be removed line by line.** Placing each line by its own time raises up ↔ down sweep agreement (error 0.42 → 0.49). Part of v1's 8.4 px up/down offset was in-sweep shear (report v2, Section 2).
4. **The setpoint selects a layer; it is not a contrast knob.** In the formula it is a constant offset. Through the loop it sets which ~0.38 nm band of heights sits between "no current" and "clipped". Setpoint steps are therefore a contour selector (T5); keep it at or above ~200 pA until F4.
5. **Horizontal banding is broadband line-to-line jitter, not an overlay tone** (OI-14). That is the case for cross-hatch pairs.
6. **Two kinds of drift, named separately.** X-Y stage drift is measured routinely by feature tracking. Z thermal drift (the tip leaving the Z range, stepper needed) is the operator's long-standing observation. A first split of the Oct 22 Z ramp gives ~+39 codes/s at the same sample points and −7 codes/s from tilt; the components are not yet mapped (OI-16).
7. **The firmware is deterministic in ticks.** The commanded position per tick is exact; PC timestamps are not a time base. Tick timestamps in frames and acknowledgements (F8) and DAC-write guards (F9) follow. Every recording must carry its reconstruction recipe (OI-17 principles).
8. **Software built today (uncommitted until the operator commits):**
   - F2: RTRC to the fully retracted end (firmware, not flashed).
   - F1: RUN asks for the scan mode; clip guard at fixed Z.
   - I-10: peaks-bright display.
   - Report v2 published as a separate artifact; v1 kept as the reference.
9. **Tooling lessons:**
   - Offscreen GUI tests must point `QTPANDA_SETTINGS` at a scratch file; one run overwrote the operator's Row align setting.
   - Shell heredocs mangle non-ASCII text on Windows, so patch scripts go in files.

### 6.1 Priorities after 2026-10-23

| Order | Track | Items | Why now |
|---|---|---|---|
| 1 | Safety and timing firmware (one flash, with the operator) | F2 (built), F8, F9, setpoint clamp | safe automated runs; exact time base for everything after |
| 2 | Diagnostics bench session A | T1, T2, T7 | settles dark, the phantom offset and the 158.7 Hz source; unblocks F4 |
| 3 | Imaging session B with a recovered tip | TIP, T3–T6, ZD1 steps 2–3 | KIGA confirmation, setpoint contours, 10-minute hold, Z drift time course |
| 4 | Calibration | T8, R13 | nm for X, Y and Z |
| open | Scan paths (experimental option) | SP0 and SP1 (OI-17); the PC-only steps can run any time, the firmware modes ride a flash only when chosen | may rank above or below calibration: operator's call |
| ongoing | Offline | I-11 drift-registered replay, I-13 Z-drift metric, I-7 colour levels, report figures | no hardware needed |
"""
open(p, "w", encoding="utf-8").write(s)

p = os.path.join(TP, "build_roadmap.py"); s = open(p, encoding="utf-8").read()
rep('"firmware", "M7", "design agreed; simulate first", 3, 1, 3, "operator 2026-10-23", "Mode 0 = today',
    '"firmware", "M7", "experimental option; priority vs calibration open", 3, 1, 3, "operator 2026-10-23; scan-path-design.md", "Every named path in code, versioned, bit-exact; recordings carry the reconstruction recipe (no orphan frames); Custom via a path file copied into the recording. Mode 0 = today')
rep('("F6", "Cross-hatch scanning (SWXY)", "firmware", "M7", "go/no-go open", 2, 1, 3, "streak plan §4; OI-14", "Bundle with M1 firmware flash"),',
    '("F6", "Cross-hatch scanning (SWXY)", "firmware", "M7", "merged into SP1 (sequence)", 2, 1, 3, "streak plan §4; OI-14", "Now the cross-hatch sequence of SP1: fast axis swaps between frames on the same area; merged with line-by-line drift registration. Oct 22 banding is broadband line-to-line jitter (OI-14), which this targets"),')
rep('("M7", "Streak suppression", "Cross-hatch scanning, streak anisotropy test, slower/adaptive lines."),',
    '("M7", "Streak suppression and scan paths", "Cross-hatch pairs, streak anisotropy test, slower/adaptive lines; experimental scan paths (rotated, spiral, centre-return, rose) behind an option."),')
rep('    ("SP1", ',
    '    ("I-11", "Drift-registered replay mode (line by line, as in report v2)", "GUI", "M5", "proposed", 3, 2, 3, "report v2 Section 2", "Feature stays put while stepping; A/B compare the same sample patch; basis for the cross-hatch merge"),\n'
    '    ("SP0", "Scan-path library + reconstruction contract + simulator (PC only)", "analysis", "M7", "designed", 3, 3, 2, "scan-path-design.md §9–10", "Generators, reconstruct(), coverage map, golden vectors, piezo model, scorecard on Sep 24 truth; no hardware"),\n'
    '    ("SP1", ')
open(p, "w", encoding="utf-8").write(s)

p = os.path.join(TP, "README.md"); s = open(p, encoding="utf-8").read()
rep("| [phantom-offset-handoff.md](phantom-offset-handoff.md) |",
    "| [scan-path-design.md](scan-path-design.md) | Experimental scan paths (rotated, cross-hatch, spirals, centre-return, rose): principles, reconstruction contract, timing audit, physics model, simulation plan |\n"
    "| [RESUME.md](RESUME.md) | Where multi-session build work stands; read first when resuming |\n"
    "| [phantom-offset-handoff.md](phantom-offset-handoff.md) |")
s = s.rstrip() + "\n\nShared reports for Oct 22: v2 (current, peaks bright, drift removed line by line) https://claude.ai/artifact/LqRJEE9pjqCwkczBi2iM6p; v1 (reference, unchanged) https://claude.ai/artifact/9aZPBvpbLL48iMj1j89Rxy. Section 6 of the open-issues file holds the 2026-10-23 learnings and current priorities.\n"
open(p, "w", encoding="utf-8").write(s)

p = "C:/Users/enact/Projects/qt-panda/docs/stm-techniques-backlog.md"; s = open(p, encoding="utf-8").read()
rep("| Slope / tilt feed-forward |",
    "| Orthogonal-scan drift correction | Scan the same area with the fast axis along X, then along Y; drift distorts the two differently and can be solved for (reported for STEM and scanning probe images, Ophus et al., Ultramicroscopy 2016, to verify) | Our cross-hatch sequence (OI-17) | partial (designed) |\n"
    "| Line-by-line drift registration | Place each scan line by its own time instead of one shift per frame | Report v2: up ↔ down agreement 0.42 → 0.49 | rediscovered |\n"
    "| Slope / tilt feed-forward |")
s = s.rstrip() + """

## Scan paths

| Technique | What it is | Why it matters | Status |
|---|---|---|---|
| Rotated raster | Scan at an angle to the stage axes | Separates sample features from axis-bound artefacts; reveals X/Y calibration mismatch as shear | not yet (OI-17) |
| Spiral scanning | Archimedean or Fermat spirals driven by smooth sines, popular for fast scanning because there are no turnarounds | Smooth drive below the 158.7 Hz mode; loses trace/retrace lag cancellation unless run as out-in pairs | not yet (OI-17) |
| Lissajous / rose scanning | Each axis a pure sine; the pattern precesses to fill the area | Smoothest drive; uneven density; frequent centre crossings measure drift | not yet (OI-17) |
| Input shaping | Pre-filter the drive to cancel a known resonance | Lets rasters and returns run faster without ringing the 158.7 Hz mode | not yet |
| Piezo hysteresis models | Prandtl–Ishlinskii, Bouc–Wen: history-dependent commanded → actual position | Up/down offset and path-dependent distortion in the simulator | not yet |
"""
open(p, "w", encoding="utf-8").write(s)
print("docs updated")
