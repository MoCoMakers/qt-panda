"""KIGA sweep report with drift compensation as the first pass -> KIGA-SWEEP-2026-10-22.html"""
import os, json, base64
HERE = os.path.dirname(os.path.abspath(__file__)); F = os.path.join(HERE, "morph_report")
OUT = "C:/Users/enact/Projects/qt-panda/TeamUpdate/data/2026-Oct-22/KIGA-SWEEP-2026-10-22.html"
img = lambda n: "data:image/png;base64," + base64.b64encode(open(os.path.join(F, n), "rb").read()).decode()
k = json.load(open(os.path.join(F, "kiga_dc.json")))
G = k["gain"]; X = k["cross_gain"]
rng = lambda v: "—" if not v else (f"{v[0]:.2f}" if abs(v[0] - v[1]) < 0.005 else f"{v[0]:.2f}–{v[1]:.2f}")
lag = lambda g: f"{min(G[g]['lag_share']):.2f}–{max(G[g]['lag_share']):.2f}"
hz = lambda g: f"{G[g]['hold_z_100_300']:.1e}"
base = G["1.14"]["hold_z_100_300"]

CSS = """
:root{--bg:#fbfaf8;--fg:#1d1d1f;--mut:#5f6368;--line:#e2dfd9;--card:#fff;--acc:#b4531a;--ok:#2a7a3a;--warn:#a0601a}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#16171a;--fg:#e8e6e3;--mut:#a3a3a3;--line:#33353a;--card:#1e2024;--acc:#f0a46a;--ok:#7bc88a;--warn:#e0a060}}
:root[data-theme="dark"]{--bg:#16171a;--fg:#e8e6e3;--mut:#a3a3a3;--line:#33353a;--card:#1e2024;--acc:#f0a46a;--ok:#7bc88a;--warn:#e0a060}
body{background:var(--bg);color:var(--fg);font:15px/1.55 system-ui,"Segoe UI",sans-serif;margin:0}
main{max-width:1100px;margin:0 auto;padding:28px 16px 60px}
h1{font-size:26px;margin:0 0 4px} h2{font-size:18px;margin:32px 0 8px;border-bottom:1px solid var(--line);padding-bottom:4px}
.sub{color:var(--mut);margin-bottom:16px} .card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:14px 16px;margin:12px 0}
.verdict{border-left:4px solid var(--acc)} .q{border-left:4px solid var(--warn)}
img{max-width:100%;height:auto;background:#fff;border-radius:4px} figure{margin:10px 0} figcaption{color:var(--mut);font-size:13px;margin-top:4px}
table{border-collapse:collapse;font-size:13.5px;width:100%} td,th{border-bottom:1px solid var(--line);padding:5px 7px;text-align:left;vertical-align:top}
th{font-weight:600} .scroll{overflow-x:auto} code{font-size:13px} b.best{color:var(--ok)}
"""

T1 = f"""<table>
<tr><th>KIGA</th><th>Outcome</th><th>Halted-hold Z power 100–300 Hz (×1.14)</th><th>Direction-flip (lag) share</th><th>Same patch, same direction: error / Z</th><th>Same patch, up ↔ down: error / Z</th><th>Z streak anisotropy</th><th>Tunnelling / no current / clipped</th></tr>
<tr><td>1.14</td><td>clean</td><td>{hz('1.14')} (1×)</td><td>{lag('1.14')}</td><td colspan="4">not drift-corrected: no trackable structure in #12–#18</td></tr>
<tr><td>2.3</td><td>clean</td><td>{hz('2.3')} ({G['2.3']['hold_z_100_300']/base:.1f}×)</td><td>{lag('2.3')}</td><td>{rng(G['2.3']['repeat_err_same direction'])} / {rng(G['2.3']['repeat_S_same direction'])}</td><td>{rng(G['2.3']['repeat_err_up/down'])} / {rng(G['2.3']['repeat_S_up/down'])}</td><td>{G['2.3']['streak_aniso_z']:.0f}</td><td>31% / 69% / 8.4%</td></tr>
<tr><td>4.6</td><td>clean, last stable</td><td>{hz('4.6')} ({G['4.6']['hold_z_100_300']/base:.0f}×)</td><td><b class="best">{lag('4.6')}</b></td><td><b class="best">{rng(G['4.6']['repeat_err_same direction'])} / {rng(G['4.6']['repeat_S_same direction'])}</b></td><td>{rng(G['4.6']['repeat_err_up/down'])} / <b class="best">{rng(G['4.6']['repeat_S_up/down'])}</b></td><td>{G['4.6']['streak_aniso_z']:.0f}</td><td>40% / 60% / 7.2%</td></tr>
<tr><td>9</td><td><b>oscillated</b>, Z-guard abort</td><td>{hz('9')} ({G['9']['hold_z_100_300']/base:.0f}×)</td><td>{lag('9')}</td><td>— (one cycle only)</td><td>{rng(G['9']['repeat_err_up/down'])} / {rng(G['9']['repeat_S_up/down'])}</td><td>{G['9']['streak_aniso_z']:.0f}</td><td>39% / 61% / 6.7%</td></tr>
</table>
<div class="sub" style="margin:8px 0 0">30 nm, 512 px/line (256 × 256), ~10.5 Hz lines, 500 pA, Kp 0, 100 kHz loop. Repeatability = correlation of drift-corrected images over the overlapping sample area (700–880 nm² per pair; flipped-image null ≈ 0). Streak anisotropy = row-to-row ÷ column-to-column gradient energy of the raw Z trace (1 = no streaks); the error channel sits at ~8 for every gain. Last column: share of scan samples with tunnelling current (ADC ≥ −20), with no current (ADC −50…−64, see Q4), and clipped (32767).</div>"""

html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Oct 22 KIGA Sweep</title><style>{CSS}</style></head><body><main>
<h1>KIGA sweep, Oct 22: drift-corrected</h1>
<div class="sub">qt-panda STM · gain steps 1.14 → 2.3 → 4.6 → 9, 19:25–19:34 · drift compensation applied to every sweep before comparison · generated 2026-10-23 · companion pages: <code>MORPHOLOGY-2026-10-22.html</code>, <code>MOUND-3D-2026-10-22.html</code></div>

<div class="card verdict"><b>Results.</b>
<ul>
<li><b>Stability:</b> 4.6 is the last stable gain; 9 oscillated against the <b>158.7 Hz</b> Z resonance (current flipping between none and clipped, Z swinging ~11,000 codes) until the Z guard stopped it. The resonance's Z power in the halted holds grows {G['2.3']['hold_z_100_300']/base:.1f}× at 2.3 and {G['4.6']['hold_z_100_300']/base:.0f}× at 4.6 relative to 1.14.</li>
<li><b>Image quality, now on the same patch of sample:</b> after drift compensation, sweeps in the same direction repeat at <b>0.49–0.54 (error) and 0.46–0.62 (Z) at KIGA 4.6</b>, against 0.31–0.40 and 0.26–0.33 at 2.3. 4.6 is the best gain tested, by about 0.15–0.3 in correlation.</li>
<li><b>The same morphology at every gain:</b> the per-gain drift-corrected averages agree with each other (Z: {X['S 2.3|4.6']['corr']:.2f} for 2.3 vs 4.6, {X['S 4.6|9']['corr']:.2f} for 4.6 vs 9, {X['S 2.3|9']['corr']:.2f} for 2.3 vs 9; flipped nulls −0.18 to 0.03). What the images show is on the sample, not produced by the loop.</li>
<li><b>Still lag-dominated:</b> 79–84% of each image flips with scan direction even at 4.6, against 87–94% at 1.14. At 10.5 Hz lines the loop is still the main limit; slower lines are the next lever.</li>
<li><b>Z streaks grow slightly with gain</b> (anisotropy {G['2.3']['streak_aniso_z']:.0f} → {G['4.6']['streak_aniso_z']:.0f} → {G['9']['streak_aniso_z']:.0f}), consistent with more of the 158.7 Hz resonance passing into Z.</li>
<li><b>Default:</b> the running GUI was left at KIGA 3.07 (⅔ of 4.6). On this evidence 4.6 itself images better, but sits close enough to the resonance that ⅔ remains the safer default until a good tip confirms it.</li>
</ul>
<b>Caveat:</b> the tip had crashed at 19:10:30, before the sweep. Repeatability is about half a good tip's (Sep 24: 0.74–0.98), so the gain ranking should be confirmed with a recovered tip.</div>

<h2>1 · First pass: drift compensation</h2>
<div class="card"><p>The sample drifted steadily relative to the scan: <b>67 pm/s, almost straight up the frame</b> (19.8 nm up and 2.1 nm left over the 300 s from #20 to #31). Measured by tracking small image rectangles from sweep to sweep (validated on Sep 24, cross-checked between error and Z channels, chain-consistent within 3–9 px), then fitted as one steady drift plus two scanner effects:</p>
<ul>
<li><b>Up/down-sweep offset:</b> up-sweep (▲) and down-sweep (▼) images sit 8.4 px (~1.0 nm) apart (piezo hysteresis), so the feature appears to step 22.4 px from an up sweep to the next down sweep but only 5.5 px from a down sweep to the next up sweep. Over a full cycle the rate is constant.</li>
<li><b>Gain-change jumps:</b> each gain change (which halted and restarted the scan) adds a small jump of about 4 px down and 5 px left; the drift continued through the 30 s halts.</li>
</ul>
<p>Fit residual: 5.1 px vertical, 2.6 px sideways (~0.6 / 0.3 nm) over 13 cross-checked sweep pairs. The nm figures use the uncalibrated 5 nm/V lateral placeholder; the pixel figures don't depend on it. Every sweep below is mapped into #20's coordinates with this model before any comparison.</p></div>
<figure><img src="{img('figK2_driftpath.png')}" alt="Drift path of the circled feature">
<figcaption>Left: the circled feature's position in the frame against time, coloured by gain. Right: its path within the 30 nm frame. The small zig-zag is the up/down-sweep offset; the two sideways jogs are the gain changes.</figcaption></figure>

<h2>2 · Per-gain results, drift-corrected</h2>
<div class="card scroll">{T1}</div>

<h2>3 · The same patch of sample at each gain</h2>
<figure><img src="{img('figK1_maps.png')}" alt="Drift-corrected per-gain maps">
<figcaption>All sweeps mapped into #20's coordinates and averaged per gain (error channel top, Z bottom); right column stitches all 10 sweeps. Grey: not scanned at that gain, because the sample drifted through the scan window, the stitched map covers about 30 × 45 nm. Green: the circled feature from the morphology case study. The diagonal band through the circle and the structures to its lower right appear at every gain in the same place.</figcaption></figure>

<h2>4 · Morphology carried over</h2>
<div class="card"><ul>
<li><b>Persistent structure, proven by tracking.</b> Rectangles cut from one sweep are found again in the previous one at the predicted shift (match 0.67–0.79 against 0.28–0.42 in unrelated frames). See the morphology report, section D1.</li>
<li><b>The circled feature (case study).</b> A dark dot in #20 (already present and clipping in #18) opens into a ring (#21) and an A-shape (#22–#23) at the same sample position. Inside a fixed 9 × 9 nm window carried by the drift model, the clipped share falls smoothly 34 → 21 → 17 → 12% through the KIGA 2.3 sweeps, holds at 11–20% through 4.6, and drops to 3–6% at 9. No abrupt tip changes occurred near it.</li>
<li><b>Mound reconstructions.</b> Stacking each sweep's outline as a contour gives an elongated ridge ~15.6 nm long. Two readings are built into the 3D page: the operator's (#20 = summit, the bright opening inside the dark structure as the cross-section, growing 14 → 18 → 33 → 29 → 30 → 45 nm² from #20 to #26) and the analysis reading (dark outlines by size). See Q1–Q2 below.</li>
</ul></div>
<figure><img src="{img('figC0_fullframes.png')}" alt="The circled feature carried forward">
<figcaption>Full frames, error channel: the circled feature in #20 and the same sample spot carried forward by the drift model.</figcaption></figure>

<h2>5 · Open questions for discussion</h2>
<div class="card q"><p><b>Q1 · What dark means in the error image.</b> Operator reading: dark is the absence of measurement (a valley), so the dot is the top of the mountain. Analysis reading: dark is the highest current. Evidence for the analysis reading: the firmware's error is setpoint − log(current) (<code>stm_firmware.hpp:323</code>), so its lowest (darkest) value is the most current; the darkest pixels sit at exactly the value for ADC 32767; the status stream shows the ADC reading exactly 32767 in 6.4–9.8% of scan samples, before any firmware substitution; and 32767 is the reading the tip gave in contact during the 19:10–19:21 crash. Real tunnelling reads positive (halted-hold median +194 against a 160 setpoint); no current reads near or below the −15 idle, which displays bright. <i>Proposed bench check:</i> at a fixed position, step Z toward and away from the sample with feedback off and watch which way the error colour goes.</p>
<p><b>Q2 · Which way the slices run.</b> Operator: #20 is the summit and each later sweep is a slice further down, with the cross-section growing. Analysis: by dark area #20 is the widest cut, and later cuts are smaller, so the cut rose over time. Both depend on Q1. Under the operator's reading the bright opening inside the dark structure does grow and nest (64–71%) from #21 to #26, so that picture is self-consistent over that range; it breaks at #20→#21 (14%) and from #27 on.</p>
<p><b>Q3 · Whether Z drift moves the slice.</b> The loop's Z output ramped 14–49 codes/s during the sweep. Operator correction (accepted): that ramp is the loop's action, not a direct measurement of sample drift, because the loop does not hold a fixed gap when the current is absent most of the time. Separating them needs the 3D model (mound + tunnelling + clip + firmware loop) proposed in the morphology report, C3.</p>
<p><b>Q4 · A phantom current during scanning (new).</b> While scanning, the samples without tunnelling read −50 to −64 on the ADC, about 40 LSB below the −15 idle seen with the tip far away; this only happens while the scan moves. The firmware takes the absolute value (<code>logTable[abs(adc_val)]</code>), so the loop reads those samples as ~55 LSB of current, about a third of the 160 setpoint, and extends Z more slowly than it should when it has lost the surface. Candidates: capacitive pickup of the X/Y drive into the preamp, or a ground shift while scanning. Worth discussing whether the firmware should subtract a measured offset instead of taking the absolute value.</p>
<p><b>Q5 · Up/down naming in the live view.</b> This report and the replay viewer call the first half of each Y-cycle the up sweep (▲). The live raster calls it the down sweep (plan item 5d). Until that is changed, live and replay labels are reversed.</p></div>

<h2>6 · Next</h2>
<div class="card"><ul>
<li>Recover or replace the tip, then repeat KIGA 2.3 and 4.6 (and 3.07) on one area with feedback engaged before scanning; judge with drift-corrected same-direction repeatability (target ≥ ~0.7).</li>
<li>Try slower lines (5 Hz) at 4.6: the lag share is still ~80%.</li>
<li>Run the Q1 bench check and decide the error-colour convention before the next morphology discussion.</li>
<li>Look into Q4 (scan-induced ADC offset) before trusting the loop's behaviour when the current is lost.</li>
</ul></div>

<h2>Method</h2>
<div class="card" style="font-size:13px">Images: replay-player loader (<code>sweep_player.DayData</code>), rows levelled, σ = 1 px smoothing for the maps and repeatability (raw for streak anisotropy). Drift model: least-squares fit of steady drift, up/down-sweep offset and gain-change jump to 13 template-tracking shifts where the error and Z channels agree (<code>drift_proof.py</code>, <code>drift_model.py</code>). Mapping: integer-pixel shift into #20's coordinates on a 480 × 340 px canvas (<code>kiga_dc.py</code>). Repeatability: Pearson correlation of z-scored images over the overlap, consecutive sweeps only. Hold spectra: 100 kHz raw tap during each 30 s halted hold, Z channel, 100–300 Hz band (<code>ladder_analysis.py</code>). Loop statistics: 200 Hz status stream during each gain's scans.</div>
</main></body></html>"""
open(OUT, "w", encoding="utf-8").write(html)
print(OUT, os.path.getsize(OUT) // 1000, "kB")
