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
    ("M7", "Streak suppression", "Cross-hatch scanning, streak anisotropy test, slower/adaptive lines."),
    ("M8", "Mechanics", "158.7 Hz mode, isolation, cables, stiffer head."),
]
# id, title, type, milestone, status, lead, ease, impact, source, next / notes
# Scores 1-3: lead = likely to find or fix a main limit; ease = 3 analysis/setting, 2 bench/small code, 1 hardware/large firmware;
# impact = how much a positive result changes design or defaults. "orig" = Oct 15 report total, where it exists.
I = [
    # ---- Oct 15 resolution report action items
    ("R1", "KIGA sweep on one area", "bench", "M4", "first pass done", 3, 3, 3, "Oct 15 report #1 (9)", "Oct 22: 4.6 last stable, 9 oscillated; confounded by crashed tip and restarts → retest T3"),
    ("R2", "Slower lines (≤ 10 Hz)", "bench", "M4", "partial", 3, 3, 3, "Oct 15 #2 (9)", "Oct 22 ran ~10.5 Hz only; add 5 Hz at KIGA 4.6 in T3"),
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
    ("R19", "Code-review fixes (retract, setpoint clamp, BUSY, line numbering)", "firmware", "M1", "open", 2, 2, 3, "Oct 15 #19 (5); streak plan items 1–3", "Before long automated runs"),
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
    ("F1", "Explicit scan mode at RUN (constant current or constant height on purpose) + clip guard when Z is fixed", "GUI", "M1", "open", 3, 3, 3, "Oct 22 crash; test plan §0.2", "The 19:10 crash happened parked at fixed Z: a sustained-clip guard (small retract) addresses it; a hard feedback gate would block constant height"),
    ("F2", "RTRC button: do what the live-scan Z slider does when pulled fully to Away (Z to its retracted end), instead of jumping to DAC 50000", "firmware", "M1", "approved", 2, 2, 3, "streak plan item 1; stm_firmware.hpp:604", "Lower Z = away (Oct 22 data, GUI slider labels); RTRC jumps to 50000, toward the sample whenever Z is below it (tunnelling Z was 25k–38k). The GUI Z slider is fine"),
    ("F3", "AI tooling: change Ki live without halting, as the operator does", "AI tooling", "M1", "open", 2, 3, 2, "OI-6, I-5", "Not a firmware/GUI gap: the Oct 22 script halted and re-sent everything; the operator keeps scanning"),
    ("F4", "ADC offset instead of abs(); revisit 0→32767", "firmware", "M3", "open", 3, 2, 3, "OI-2, OI-3, I-8", "After T2 and I-8; also removes the ~2% false dark specks"),
    ("F5", "Per-pixel clipped / no-current counts in frames", "firmware", "M3", "open", 2, 2, 2, "OI-4", ""),
    ("F6", "Cross-hatch scanning (SWXY)", "firmware", "M7", "go/no-go open", 2, 1, 3, "streak plan §4; OI-14", "Bundle with M1 firmware flash"),
    ("F7", "Live raster up/down naming matches replay", "GUI", "M1", "open", 1, 3, 1, "streak plan 5d", ""),
    ("G-ST1", "Stage tracking, monitor mode (compact panel, Show fiducials off by default)", "GUI", "M5", "designed", 3, 2, 3, "mockups; MORPHOLOGY report F/F2", ""),
    ("G-ST2", "Stage tracking, correct mode with in-zone gate", "GUI", "M5", "designed", 3, 1, 3, "OI-8", "After G-ST1 and F1"),
    ("G-TR", "Trace/retrace handling (offset record, compensation, which stream to track)", "analysis", "M3", "to scope", 2, 2, 2, "OI-7", "Scope first, then approve"),
    ("G-CL", "Fixed colour scale + clipped/no-current colours", "GUI", "M3", "open", 2, 3, 2, "OI-4, I-7", ""),
    # ---- offline investigations
    ("I-1", "Test the lost-vs-clipped loop model on raw data", "analysis", "M3", "next", 3, 3, 2, "test plan I-1", ""),
    ("I-2", "Phantom offset signature in existing raw data", "analysis", "M3", "blocked", 3, 3, 2, "test plan I-2", "Oct 22 raw capture has no data during scanning; needs I-9 or T2"),
    ("I-3", "Trace-only rerun of fiducial tracking", "analysis", "M5", "queued", 1, 3, 1, "test plan I-3", ""),
    ("I-4", "158.7 Hz section in the morphology report", "doc", "M8", "queued", 1, 3, 1, "test plan I-4", ""),
    ("I-6", "Verify the STM techniques backlog with sources", "analysis", "M3", "queued", 2, 3, 2, "techniques backlog", ""),
    ("I-7", "Audit auto colour levels (live and replay)", "analysis", "M3", "queued", 2, 3, 2, "test plan I-7", ""),
    ("I-8", "ADC overrange behaviour; zero-substitution impact", "analysis", "M3", "in progress", 2, 3, 2, "test plan I-8, OI-2.6", "Substitution fires on 0.1% of scan samples: ~2% of pixels get false dark specks"),
    ("I-9", "Raw capture during scanning (blocks only arrive while halted)", "analysis", "M3", "queued", 3, 2, 3, "test plan I-9", "Unblocks I-2 and in-scan spectra"),
    ("I-10", "Standardise display: dark = valleys in live, replay and reports", "GUI", "M3", "open", 3, 3, 3, "test plan OI-4", "Error and Z are inverted today; the live error panel flips convention between CC and constant height"),
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
<th data-k="id">ID</th><th data-k="title">Item</th><th data-k="type">Type</th><th data-k="ms">Milestone</th><th data-k="status">Status</th>
<th data-k="lead">Lead</th><th data-k="ease">Ease</th><th data-k="impact">Impact</th><th data-k="score">Score ▾</th><th data-k="source">Source</th><th data-k="note">Next / notes</th>
</tr></thead><tbody></tbody></table></div>

<!--CALC-->
<h2>Proposed order of sessions</h2>
<div class="scroll"><table><tr><th>#</th><th>Session</th><th>Items</th><th>Milestones</th></tr>{sess}</table></div>

<h2>Safety rules (apply to every session)</h2>
<ol>
<li>The Retract (RTRC) button jumps Z to 50000, toward the sample whenever Z is below that (lower Z = away). Back off with the GUI Z slider or the motor.</li>
<li>RUN does not engage feedback and nothing guards a fixed-Z tip: choose the mode deliberately and watch for sustained clipping (the Oct 22 crash happened parked at fixed Z).</li>
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
  tb.innerHTML = rs.map(r => `<tr class="${{r.score >= 8 ? 'top' : ''}}"><td>${{esc(r.id)}}</td><td>${{esc(r.title)}}</td><td><span class="pill">${{esc(r.type)}}</span></td>
    <td>${{esc(r.ms)}}</td><td>${{esc(r.status)}}</td><td class="n">${{r.lead}}</td><td class="n">${{r.ease}}</td><td class="n">${{r.impact}}</td>
    <td class="n"><b>${{r.score}}</b></td><td class="mut">${{esc(r.source)}}</td><td>${{esc(r.note)}}</td></tr>`).join('');
  document.getElementById('nShown').textContent = `${{rs.length}} of ${{ROWS.length}} items`;
}}
draw();
</script></body></html>"""

CALC = """<h2>Gap calculator: bias, current and tip height</h2>
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
