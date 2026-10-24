import base64, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
F = os.path.join(HERE, "morph_report")
OUT = "C:/Users/enact/Projects/qt-panda/TeamUpdate/data/2026-Oct-22/MORPHOLOGY-2026-10-22.html"


def img(n):
    return "data:image/png;base64," + base64.b64encode(open(os.path.join(F, n), "rb").read()).decode()


m = json.load(open(os.path.join(F, "metrics.json")))
rows = "".join(
    f"<tr><td>#{p['a']} → #{p['b']}</td><td>{'▲' if p['dir'] == 'up' else '▼'}</td><td>{p['dt_s']:.0f}</td>"
    f"<td>{p['dx']:+.0f}, {p['dy']:+.0f}</td><td>{p['corr_S_aligned']:.2f}</td>"
    f"<td>{p['corr_B_aligned']:.2f}</td><td>{p['corr_L_aligned']:.2f}</td></tr>"
    for p in m["pairs"])

CSS = """
:root{--bg:#fbfaf8;--fg:#1d1d1f;--mut:#5f6368;--line:#e2dfd9;--card:#fff;--acc:#b4531a}
@media (prefers-color-scheme:dark){:root{--bg:#16171a;--fg:#e8e6e3;--mut:#a3a3a3;--line:#33353a;--card:#1e2024;--acc:#f0a46a}}
body{background:var(--bg);color:var(--fg);font:15px/1.55 system-ui,"Segoe UI",sans-serif;margin:0}
main{max-width:1080px;margin:0 auto;padding:28px 16px 60px}
h1{font-size:26px;margin:0 0 4px} h2{font-size:18px;margin:34px 0 8px;border-bottom:1px solid var(--line);padding-bottom:4px}
.sub{color:var(--mut);margin-bottom:18px} .card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:14px 16px;margin:12px 0}
.verdict{border-left:4px solid var(--acc)}
img{max-width:100%;height:auto;background:#fff;border-radius:4px} figure{margin:10px 0} figcaption{color:var(--mut);font-size:13px;margin-top:4px}
table{border-collapse:collapse;font-size:13px;width:100%} td,th{border-bottom:1px solid var(--line);padding:4px 6px;text-align:left}
.scroll{overflow-x:auto} code{font-size:13px}
.data{font-size:13px;color:var(--mut);margin:-2px 0 10px;padding:3px 8px;border-left:3px solid var(--line)}
"""

html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Oct 22 Morphology Report</title><style>{CSS}</style></head><body><main>
<h1>Oct 22 morphology, drift and KIGA sweep</h1>
<div class="sub">qt-panda STM · 30 nm, 256 × 256, ~10.5 Hz lines · tip-check scan and KIGA sweep 19:24–19:34 · generated 2026-10-23</div>

<h2>0 · Start here: the instrument, the day, and how to read this report</h2>
<div class="card">
<p><b>The instrument.</b> qt-panda is a home-built scanning tunnelling microscope (STM). A sharp metal tip is held a few ångströms above a conducting sample with a small bias voltage between them (−50 mV here), so a tunnelling current flows (setpoint 500 pA). The current changes about tenfold per ångström of gap, which makes it a very sensitive height probe. A feedback loop (<b>constant-current mode</b>) moves the tip up and down (<b>Z</b>) to hold the current at the setpoint while the tip rasters across a 30 × 30 nm square. How fast the loop reacts is set by its integral gain, <b>KIGA</b>.</p>
<p><b>The images.</b> One <b>sweep</b> is one full image: 256 lines × 256 pixels (1 px = 0.117 nm), about 25 s. The slow (Y) scan goes one way and comes back; the first half of each Y-cycle is the <b>up sweep (▲)</b>, the second the <b>down sweep (▼)</b>, as in the replay viewer. Each line is scanned left to right (<b>trace</b>) and back (<b>retrace</b>). Two channels are recorded: <b>Z</b>, the tip height the loop chose, and <b>error</b>, how far the current was from the setpoint (log scale). When the loop lags, trace and retrace are shifted in opposite directions; their average, called <b>folded S</b> in this report, cancels that lag and is the best surface estimate. Sweeps are numbered #0, #1, … through the day.</p>
<p><b>The day: Oct 22, 2026, 18:22–19:52.</b> All Oct 22 numbers below refer to this table.</p>
<div class="scroll"><table>
<tr><th>Sweeps</th><th>Time</th><th>What happened</th><th>Used in</th></tr>
<tr><td>—</td><td>18:44–19:09</td><td>Tip approach (motor steps plus Z)</td><td>—</td></tr>
<tr><td>—</td><td>19:10:30</td><td><b>Tip crash</b> while parked at fixed Z with feedback off. Every image below is from this damaged tip.</td><td>—</td></tr>
<tr><td>#0–#11</td><td>19:12–19:16</td><td>Scan at fixed Z (Run did not engage feedback), mostly saturated; halted</td><td>not analysed</td></tr>
<tr><td>#12–#14</td><td>19:24</td><td>Tip check with feedback on, KIGA 1.14</td><td>D2, D3, first pass</td></tr>
<tr><td>#15–#19</td><td>19:26–19:28</td><td>KIGA sweep, step 1: KIGA 1.14</td><td>D2, D3, K, first pass</td></tr>
<tr><td>#20–#24</td><td>19:28–19:30</td><td>Step 2: KIGA 2.3</td><td>all sections</td></tr>
<tr><td>#25–#29</td><td>19:31–19:32</td><td>Step 3: KIGA 4.6 (last stable gain)</td><td>all sections</td></tr>
<tr><td>#30–#32</td><td>19:33–19:34</td><td>Step 4: KIGA 9, loop oscillated, scan aborted by the Z guard</td><td>all sections</td></tr>
<tr><td>#33–#56</td><td>19:42–19:52</td><td>Operator scan at KIGA 3.07</td><td>not analysed here</td></tr>
</table></div>
<p class="sub" style="margin:6px 0 10px">Before each step the loop was held for 30 s with the scan halted (the "halted hold") to measure its noise. Partial sweeps (#14, #19, #24, #29, #32) are left out of image comparisons. Comparison data from a good-tip day: Sep 24, 2026, sweeps #1586–#1599 and #1802–#1811.</p>
<p><b>How to read the colours.</b> Figures show the channels as stored. In <b>error</b> images, dark = high tunnelling current = the surface closest to the tip, i.e. <b>high points</b>. In <b>Z</b> images, bright = Z extended toward the sample, i.e. <b>low points</b>. Both are therefore inverted relative to the usual convention (bright = peaks, dark = valleys); standardising every view to dark = valleys is planned (roadmap I-10). About 2% of error-image pixels are false dark specks from a firmware substitution (Q1).</p>
<p><b>Reading path.</b> <b>D</b>: is anything in these images real? Measure how the sample drifts and use that to compare sweeps. → <b>C</b>: one feature followed in detail (a dot that opens into an “A”) and the mound it implies. → <b>K</b>: which gain images best, judged on the same patch of sample. → <b>F</b>: the drift method made general and live. → <b>Q</b>: open questions. → <b>First pass</b>: the earlier analysis, with what still applies. → <b>Roadmap</b> at the bottom. Each section opens with a <i>Data</i> line naming the day and sweeps it uses, and every figure caption states its take-home message first.</p>
</div>

<h2>Summary</h2>
<div class="card verdict"><b>Revised verdict (drift accounted for): from #20 to #31 there IS persistent structure, and it moves with the sample.</b>
<ul>
<li><b>Stage drift is measured, not assumed.</b> Small rectangles cut from each sweep are found again in the previous sweep (Figure D1). The shifts they report chain consistently (A→C equals A→B plus B→C within 3–9 px) and agree between two independent channels, error and Z (Figure D3). Random matches would do neither.</li>
<li><b>Drift model, fitted to 13 cross-checked pairs:</b> content moves up the frame at <b>0.56 px/s ≈ 66 pm/s</b>; sideways drift ≈ 0 (3 pm/s). Up-sweep (▲) and down-sweep (▼) images are offset by <b>8.4 px ≈ 1.0 nm</b> (piezo hysteresis), which is why ▲→▼ pairs show ~+22 px while ▼→▲ pairs show ~0. Each gain change adds a small jump of about 4 px down and 5 px left (the automatic tool in F agrees on the direction: down and left). Residual: 5.1 px vertical, 2.6 px sideways.</li>
<li><b>It is surface, not the feedback loop.</b> Aligning sweeps with only the model's predicted shift (no search) gives correlations of 0.25–0.6; leaving them fixed in the frame gives ≈ 0 (Figure D4). A loop-lag pattern is tied to the scan and cannot slide 20+ px between frames. The structure also survives every gain change once drift is accounted for (0.25–0.55 vs 0.0–0.16 unshifted).</li>
<li><b>Proof by averaging:</b> mapping #20–#31 into one frame with the model and averaging gives a sharper image with a clear diagonal band; the same sweeps averaged without correction blur out (Figure D5).</li>
<li><b>But the signal is weak.</b> Drift-corrected repeat between neighbouring sweeps is 0.4–0.6 (best at KIGA 4.6: Z 0.40–0.62), against 0.9+ on Sep 24 with a good tip. It decays to ~0.1–0.3 over 4–5 minutes. Before #20 (tip check and KIGA 1.14, #12–#18) nothing locks: no consistent shift and no chain consistency, so there is no trackable structure there. The one exception is #18→#20, where both channels independently report the same jump (+33, +21 px, content moving up and left), matching your observation, though below the strict match threshold.</li>
</ul>
<b>What this corrects.</b> My first pass compared whole frames at full resolution without accounting for drift and concluded "no persistent morphology" and "the pattern resets at each gain change". Both were wrong for #20–#31: the structure is there, it is weak relative to row noise, and it moves about 2–3 nm per Y-cycle. That first pass is kept near the end, with a note on what still applies.</div>


<h2>D · Is the structure real? Measure the drift first</h2>
<div class="card"><p>To ask whether a feature persists, two sweeps have to be compared at the same place on the sample. The sample drifts slowly under the tip, so the same feature sits somewhere else in each image, and comparing whole frames as they are finds nothing (that was the first pass). This section measures the drift from the images themselves: small rectangles from one sweep are found again in the previous sweep (D1–D3). It then tests the result (D4–D5) and measures how well the surface repeats once the drift is removed (D6). Chance matches would not agree between the error and Z channels, would not add up over three sweeps, and could not predict where the surface will be next; these shifts do all three.</p></div>
<h2>D1 · Inset proof: the next frame's rectangle, found in the prior frame</h2>
<figure><img src="{img('figD1_inset_proof.png')}" alt="Template rectangles and where they were found">
<figcaption><b>A piece of one sweep can be found again in the previous sweep, slightly shifted: consecutive images share real content that moves.</b> Each row tests one pair of sweeps. Column 1: a 96 × 96 px rectangle (cyan) cut from the later sweep. Column 2: where a search found it in the earlier sweep (cyan; dashed white = same position, i.e. no movement; small arrow = the shift). Columns 3–4: the two patches enlarged side by side. Column 5: the match score at every position of the earlier sweep (red + = best). Column 6: the same search in an unrelated frame (the null). Top row: Sep 24 good-tip control, score 0.97 against 0.30 in the null. Oct 22 rows: 0.67–0.79 against 0.28–0.42, in both channels and across a gain change. <i>Look at:</i> columns 3 and 4 look alike; column 5 has one clear peak where column 6 has none; the arrows point up the frame, as the drift model predicts.</figcaption></figure>

<h2>D2 · Every template, every pair</h2>
<figure><img src="{img('figD2_vectors.png')}" alt="Displacement vectors for all templates">
<figcaption><b>From #20 on, all templates in a pair move together; before #20 they do not, so #12–#18 have no trackable structure.</b> Each panel is one pair of consecutive sweeps (error channel). Each arrow runs from a template's position in the later sweep to where it was found in the earlier one. Cyan: agrees with the pair's consensus shift within 5 px; red: disagrees. Panel titles give the consensus shift in the error and Z channels. <i>Look at:</i> the share of cyan arrows and whether they are parallel. Many parallel arrows mean the whole field moved; scattered red arrows mean nothing locked.</figcaption></figure>

<h2>D3 · Accumulated drift and chain consistency</h2>
<figure><img src="{img('figD3_track_chain.png')}" alt="Drift track and chain consistency">
<figcaption><b>The measured shifts add up the way real motion does, so they are not chance matches.</b> Left: the feature's displacement since #20 from the fitted drift model (lines), with the 13 cross-checked measured shifts as arrows. Right: chain test. For three consecutive sweeps A, B, C, the shift A→C measured directly is plotted against A→B plus B→C; real motion lands on the diagonal. <i>Look at:</i> on the left, the steady climb (drift up the frame) and the zig-zag (the up/down-sweep offset); on the right, #20–#31 on the diagonal (misses 3–9 px) and #12–#18 far off it (24–179 px).</figcaption></figure>

<h2>D4 · Testing the drift model with prediction only</h2>
<figure><img src="{img('figD4_model_test.png')}" alt="Correlation using predicted shift vs nulls">
<figcaption><b>The drift model predicts where the surface will be without any search: the structure is on the sample and moves with it.</b> For every pair in #20–#31, the correlation between the two sweeps when aligned only by the model's predicted shift (blue), left fixed in the frame (orange), shifted by a random amount of the same size (grey, 95th percentile of 50 tries), or compared with a flipped frame (red), against the time between the sweeps. <i>Look at:</i> blue above orange and red everywhere and mostly above grey. A loop artefact is fixed to the scan and would favour orange. Blue falls with time (0.4–0.6 at 25 s, 0.1–0.3 at 250 s): the structure is real but slowly changes.</figcaption></figure>

<h2>D5 · Drift-corrected average (standard reference view)</h2>
<figure><img src="{img('figD5_corrected_stack.png')}" alt="Drift-corrected average vs uncorrected">
<figcaption><b>Averaging ten sweeps sharpens the image only when the drift is corrected. The middle panel is this report's reference view of the patch.</b> All panels in #20's coordinates. Left: #20 alone. Middle: #20–#31 mapped with the drift model (steady drift, up/down-sweep offset, gain-change jumps) and averaged. Right: the same 10 sweeps averaged without correction. <i>Look at:</i> the diagonal band and the structure around it stay sharp in the middle and smear on the right. Limit: each sweep gets one shift, but the drift continues during the 25 s sweep (~14 px top to bottom), so features near the top or bottom edge can be off by up to ~7 px.</figcaption></figure>

<h2>D6 · Repeatability per gain step, drift accounted for (first estimate; Section K is definitive)</h2>
<div class="card scroll"><table>
<tr><th>Gain</th><th>Error channel (neighbouring sweeps)</th><th>Z folded S</th></tr>
<tr><td>2.3 (#20–#23)</td><td>0.31–0.57</td><td>0.18–0.49</td></tr>
<tr><td>4.6 (#25–#28)</td><td>0.37–0.54</td><td><b>0.40–0.62</b></td></tr>
<tr><td>9 (#30–#31)</td><td>0.39</td><td>0.45</td></tr>
<tr><td>across gain changes</td><td>0.25–0.39 (unshifted 0.0–0.08)</td><td>0.33–0.55 (unshifted 0.0–0.32)</td></tr>
</table>
<div class="sub" style="margin:8px 0 0">Correlation after alignment by the drift model, sweeps ≤ 55 s apart. Individual pairs beat the random-shift 95th percentile by 0–0.13, so single pairs are weak evidence; the conclusion rests on the chain consistency, the two-channel agreement, the prediction-only test and the sharper average together. KIGA 4.6 is slightly the best, consistent with the gain sweep, but the margin is small with this tip.</div></div>

<h2>D7 · What this means</h2>
<div class="card"><ul>
<li><b>The tip still images something real after the crash</b>, at roughly half the repeatability of a good tip. It is good enough to measure drift, not good enough to judge fine morphology.</li>
<li><b>Drift must be corrected before comparing sweeps.</b> At 66 pm/s a 30 nm window moves ~3 px per sweep and ~25 px per Y-cycle; uncorrected comparisons understate persistence badly. A replay "drift-corrected" mode using this method would make that routine.</li>
<li><b>Up and down sweeps should not be compared without the ~1 nm hysteresis offset.</b> The live raster's drift_corr_y setting exists for this; today's offset was 8.4 rows at 256 rows by hand, 5.7 rows by the automatic tool (F).</li>
<li><b>Gain changes barely move the image</b> (≈ 4–5 px); KIGA can be stepped mid-session without losing registration.</li>
<li><b>Next:</b> recover or replace the tip, repeat KIGA 1.14 → 2.3 → 4.6 with feedback engaged before scanning, and use the drift-corrected repeat (≥ ~0.7) as the acceptance check. The offset test (move XOFS/YOFS a few nm) remains the cleanest confirmation that tracked structure is surface.</li>
</ul></div>

<h2>C · Case study: the dark blob that opens into an “A”</h2>
<div class="card"><p><b>The feature.</b> In #20 (first KIGA 2.3 sweep) a dark blob about 11 nm across sits at the bottom centre (rows ~185–256, columns ~100–170). It is already present in #18, cut off at the bottom edge exactly where the measured #18→#20 shift puts it, and already clipping there (32% of the visible window). In #21–#23 it opens into a dark outline around a brighter interior, an arch or capital-A shape. Its share of a fixed sample window that is dark or clipped falls smoothly through the KIGA 2.3 sweeps, holds through 4.6, and drops at 9. Dark in the error channel means more current than the setpoint, i.e. the tip is closer than the loop wants.</p>
<p><b>Working interpretation tested (operator):</b> the imaging acts like an elevation contour map. The error/current image shows a horizontal cross-section of a mound; the flat top is the sensor clipping, not a real plateau; and Z drift moves the slice up or down the mound, so the same morphology appears wider (more base, wider loop) when the tip is effectively closer and smaller when further away. If so, modelling the mound could turn the cross-section size into a Z-drift rate.</p></div>

<figure><img src="{img('figC0_fullframes.png')}" alt="Full frames with the circled feature carried forward">
<figcaption><b>The circled dot opens into a ring, a loop and an arch (“A”) at the same spot on the sample.</b> Full 30 nm frames, error channel, Oct 22 #20–#27 (KIGA 2.3 and 4.6). Solid green: the operator's circle in #20. Dashed green: the same sample spot carried forward by the drift model. <i>Look at:</i> the shape inside the circle: dot (#20), ring (#21), loop (#22), arch (#23); in #25 and #27 the circle sits on the A's left leg. The circle climbs the frame with the drift yet stays on the feature, so the “A” forms where the dot was.</figcaption></figure>
<figure><img src="{img('figC1_blob_crops.png')}" alt="The same sample patch followed through every sweep">
<figcaption><b>On the same patch of sample, the feature's darkest, clipped core shrinks smoothly within KIGA 2.3 and an outline replaces the solid blob.</b> The same 14 × 14 nm sample patch in every sweep from #18 to #31, located with the drift model; error channel on top, Z folded S below. Cyan square: the fixed 9 × 9 nm analysis window; dashed: its 4 × 4 nm centre. Titles: share of the window clipped at the current limit. White: outside the scanned frame (in #18 only 60% of the window is in frame). <i>Look at:</i> the clipped area from #20 to #23 and the outline that remains; the Z row shows the same patch with weaker contrast.</figcaption></figure>
<figure><img src="{img('figC2_blob_metrics.png')}" alt="Area, clipped share and Z over the feature">
<figcaption><b>The clipped share falls smoothly from 34% to 12% at KIGA 2.3, holds at 4.6 and drops at 9; Z shows no usable trend.</b> All three panels use the same fixed 9 × 9 nm sample window carried by the drift model, with no outline-finding. Left: share of pixels at exactly the clip value (ADC 32767, above ~102 nA). Middle: share in the darkest 20% of that sweep's error values. Right: Z in the 4 × 4 nm centre minus the whole window. Blue ▲, orange ▼. <i>Look at:</i> the smooth fall within KIGA 2.3, a gradual process rather than a tip jump, and the Z panel flipping sign between ▲ and ▼, which is lag, not height.</figcaption></figure>

<div class="card scroll"><table>
<tr><th>Sweep</th><th>KIGA</th><th>Clipped share of window</th><th>Darkest-20% share of window</th><th>Mean Z DAC</th></tr>
<tr><td>#18 ▼ (60% of window in frame)</td><td>1.14</td><td>32%</td><td>57%</td><td>28,090</td></tr>
<tr><td>#20 ▲</td><td>2.3</td><td><b>34%</b></td><td>69%</td><td>28,650</td></tr>
<tr><td>#21 ▼</td><td>2.3</td><td>21%</td><td>43%</td><td>29,270</td></tr>
<tr><td>#22 ▲</td><td>2.3</td><td>17%</td><td>31%</td><td>29,710</td></tr>
<tr><td>#23 ▼</td><td>2.3</td><td>12%</td><td>30%</td><td>30,500</td></tr>
<tr><td>#25 / #26 / #27 / #28</td><td>4.6</td><td>17 / 11 / 20 / 19%</td><td>36 / 32 / 45 / 45%</td><td>31,800–35,400</td></tr>
<tr><td>#30 ▲ / #31 ▼</td><td>9</td><td>6% / 3%</td><td>19% / 12%</td><td>37,870 / 38,400</td></tr>
</table>
<div class="sub" style="margin:8px 0 0"><b>Correction:</b> an earlier version of this section reported dark-region areas in nm² (72 → 14 nm²) and a Z “inside minus ring” trend (−116 → +979). Both came from an automatic outline that latched onto the blob in #20 but onto the long diagonal band (the A's leg) from #21 on, so they compared different objects. They are replaced by the fixed-window measures above.</div></div>

<h2>C1 · What holds up</h2>
<div class="card"><ul>
<li><b>Contour-map imaging: confirmed.</b> During these sweeps the 61–69% of scan samples had no tunnelling current (ADC at or below the idle level; see Q4) and 6.7–8.4% were clipped. With the loop this slow the error/current image is close to a constant-height slice, and the current only spans a ~0.38 nm band of tip height between “lost” (50 pA) and “clipped” (102 nA), a factor of ~2,000 at a typical decay of about one decade per Å.</li>
<li><b>The flat top is the sensor clipping: confirmed.</b> In #20, 33% of the window around the feature sits at exactly the clip value (10% across the whole sweep). That share falls smoothly to 12% over the four KIGA 2.3 sweeps, holds near 11–20% at 4.6, and is 3–6% at 9. At −50 mV bias, 102 nA is about 0.5 MΩ: near point contact. The tip was skimming this mound's top on every pass.</li>
<li><b>Same morphology, different cross-section: supported.</b> The feature stays at the same sample position (it moves with the drift model) and keeps its orientation, while its outline changes size and shape.</li>
</ul></div>

<h2>C2 · Challenges and their limits</h2>
<div class="card"><ul>
<li><b>Z drift is not directly measured here (operator's correction).</b> With feedback on, the loop's Z output climbed steadily: 4.5 codes/s just after engaging (19:21–19:24), 20 codes/s during the sweep (19:25–19:34), 18 codes/s afterwards; with the placeholder calibration that is ~9–18 pm/s. But that ramp is what the loop did, not the sample's drift. It equals drift only if the loop holds a fixed gap, and with the current lost ~60% and clipped ~7% of the time the loop runs almost on/off, so the ramp mixes real drift with shifts in the loop's balance as the scene under the tip changes. Separating them needs a 3D model: mound shape, tunnelling current, clip limits and the loop, simulated sweep by sweep and fitted to the observed cross-sections (C3).</li>
<li><b>What the loop can and cannot cancel.</b> A linear loop would cancel drift this slow (~10⁻⁴ Hz, far below the 36–72 Hz crossover) to ~0.1 pm. This loop is not linear here (clipped both ways), so that bound does not hold, and the slice level it maintains can wander. This is the opening for the operator's interpretation.</li>
<li><b>What does hold.</b> The loop moved Z by ~10,600 codes (several nm on any plausible calibration) while the feature stayed inside the ~0.38 nm band of tip height where current is visible. Whatever drove the ramp, the loop followed it to within a fraction of a nanometre; it did not leave the slice behind by nanometres. Changes in the cross-section therefore reflect sub-0.4 nm shifts of the effective slice, changes in the loop's behaviour, or changes in the mound.</li>
<li><b>So the slice moves for other reasons.</b> (1) <b>Loop gain:</b> at higher KIGA, Z rides up over the mound within each line, so less of it reaches the clip. The clipped share holds at 11–20% through KIGA 4.6 and drops to 3–6% at KIGA 9, the one step that coincides with a gain change. (2) <b>A smooth change at fixed gain:</b> within KIGA 2.3 the feature goes from dot (#20) to ring (#21) to “A” (#22–#23) over ~75 s while the clipped share of the fixed window falls smoothly 34 → 21 → 17 → 12% and the dark share 69 → 30%; through KIGA 4.6 both hold steady. The change is gradual, so it is a time process, not a tip event: a row-by-row search for abrupt tip switches (a level step in both trace and retrace lasting ≥ 8 rows) finds none in #20, #22 or #23, and the only two in #21 sit at rows 24–42, far from the feature. The damaged tip behaved as a consistent imager here (operator's point, confirmed). Leading candidate: <b>the mound itself being reshaped</b>, since its top was taken to near point contact (~0.5 MΩ) on every pass; repeated pressing could dent the top into a rim, which would image as a ring and then an “A”. Second candidate: <b>the slice level creeping</b>. The linear-loop argument above assumes the loop holds a fixed level, but with the current lost 60% of the time and clipped 7% the loop runs almost bang-bang, and the level it settles at depends on the balance of clipped errors along each line, so it can shift slowly as the scene changes. That partly reopens the operator's interpretation, though as a loop-balance effect rather than uncorrected drift.</li>
<li><b>Why the “A” rather than a solid blob.</b> In the error channel a slow loop marks a feature's slopes, where it lags, more than its top, where it has time to catch up. A wide, flat-topped mound therefore draws as an outline with a brighter interior, and the outline thins as the gain rises. That fits #21–#23 (KIGA 2.3) turning into narrower bands at 4.6 and 9.</li>
<li><b>Ruled out: double tip.</b> A crashed tip with two apexes images every edge twice at a fixed offset, which could draw an “A” from a single edge. An image autocorrelation check found no repeat at a fixed offset across sweeps, which rules out a double tip.</li>
<li><b>Ruled out: scanner magnification change.</b> The whole-image scale between sweeps is dominated by the shear from lateral drift (▲→▼ vertical ≈ 0.84) and shows no consistent overall magnification change tied to Z.</li>
</ul></div>

<h2>C3 · How to settle it, and how to get your drift-from-mound estimate</h2>
<div class="card"><ul>
<li><b>Calibrate the contour map with setpoint steps.</b> At fixed KIGA and line rate, scan the same mound at 250, 500 and 1000 pA. Each factor of two moves the tip by a known ~0.35 Å, so the cross-section's area against setpoint gives the mound's shape dA/dz directly. That is the mound model built from measurement rather than assumption.</li>
<li><b>Then hold everything fixed for 10 minutes.</b> If the cross-section keeps changing at fixed gain and setpoint, convert the change into an equivalent height with the calibration above and compare it with the Z-DAC drift. If it tracks the drift, your interpretation wins; if it is stable, the changes here came from the gain; if it changes but not with drift, it is the tip or the mound.</li>
<li><b>Footprint test for reshaping.</b> After scanning a small window for a few minutes, zoom out 2–3×. If the previously scanned square stands out from its surroundings, the tip modified the surface. If it doesn't, the slice-level explanation gains ground.</li>
<li><b>Stop clipping.</b> Lower the setpoint (the plan's 2c item: 100–500 pA) or the bias so the mound's top stays inside the ADC range. Clipping at near point contact both hides the top and risks modifying it.</li>
<li><b>Build the 3D model (operator's proposal).</b> Model the mound as a height map h(x, y) (start from a Gaussian or flat-topped mesa), the current as I = I₀·exp(−2κ(z_tip − h)) with the ADC clip at 102 nA and the 50 pA floor, and the firmware loop (integrator, KIGA, 100 kHz ticks, 10.5 Hz lines, trace/retrace raster with the measured lateral drift). Simulate each sweep, then fit the mound shape and a slice-level trajectory so the simulated error images reproduce the dot → ring → A sequence. The fitted slice trajectory, minus what the loop alone would produce, is the Z drift estimate you asked for, and the fit says whether that drift is thermal in scale.</li>
<li><b>Calibrate Z.</b> A gold monatomic step (0.235 nm) converts Z codes to nm for both the model and the ramp.</li>
</ul></div>

<h2>C4 · The mound implied by stacking the outlines</h2>
<div class="card"><p>Taking the contour-map interpretation literally: each sweep's dark (high-current) outline around the feature, mapped into #20's coordinates with the drift model, is treated as one contour line; the smallest is the summit and each larger one sits lower down. Height at each point = how many outlines enclose it (contour steps, not nm). Interactive 3D version: Section C5.</p>
<ul>
<li><b>Counting method: the circled dot is the summit.</b> Its centre is enclosed by 6 of the 9 outlines on average, the ring around it by 3.3, and the surroundings by 1.9. The terrace method (height = the highest slice whose outline contains a point) disagrees: it puts the summit where the late, small outlines sit, up the ridge from the circle, because the outlines only partly nest. Both are shown in the interactive model (C5).</li>
<li><b>Shape: an elongated ridge</b>, about 15.6 nm long and 5.5 nm wide at mid-height, narrowing to about 2 nm near the top, with its long axis about 59° from horizontal (lower left to upper right in the frame), plus a lower shoulder to the right. The “A” is where a cut crosses the ridge and its shoulder: the legs are the ridge flanks.</li>
<li><b>Ordering in time:</b> outline area shrinks almost steadily from #20 (83 nm², widest) to #30 (17 nm², smallest). Under this interpretation the cut climbs the ridge over time (the tip sees less of it), most steeply across the gain changes.</li>
<li><b>Self-consistency:</b> each outline lies 43–77% inside the next larger one, against 21–37% expected by chance, so the stack is partly, not fully, nested. Clipped-only outlines are too small and patchy to nest (11–37%).</li>
<li><b>Depends on how dark is read (Q1, Q2).</b> This stack uses the analysis reading (dark = most current, smallest dark outline = summit). The operator's reading (#20 = summit, the bright opening inside the dark structure as the cross-section, growing 14 → 18 → 33 → 29 → 30 → 45 nm² from #20 to #26) is the default view in the 3D page.</li>
<li><b>Limits:</b> levels are ranks with equal spacing assumed; gain changes alter the outlines as well as height. The setpoint-step calibration or the 3D loop model (C3) would turn ranks into nanometres.</li>
</ul></div>
<figure><img src="{img('figC4_stack_dark.png')}" alt="Contour stack and implied mound">
<figcaption><b>Read as a contour map, the outlines stack into an elongated ridge with the circled dot near its summit.</b> Oct 22 #20–#30: each sweep's dark outline mapped into #20's coordinates. Left: the outlines over the #20 image (purple = smallest, yellow = largest). Middle-left: stacked height = the number of outlines enclosing each point (contour steps, not nm). Middle-right: the implied mound, smoothed. Right: outline areas from summit to base, with the share of each outline inside the next larger one (red). <i>Look at:</i> the ridge running lower left to upper right, and the red nesting values (43–77%, against 21–37% by chance): the outlines partly nest, as contour lines should, but not perfectly.</figcaption></figure>
<figure><img src="{img('figC0_fullframes.png')}" alt="Reminder: the full frames the outlines come from">
<figcaption><b>Reminder: what the frames behind these outlines look like.</b> Repeated from the start of Section C: #20 with the operator's circle (solid green) and the same sample spot carried into #21–#27 (dashed). The ridge in the stack above is the long dark diagonal running through the circle; the outlines are the dark shapes inside and around it.</figcaption></figure>

<h2>C5 · Interactive 3D mound</h2>
<div class="card"><p>The mound reconstructions, explorable: drag to orbit, scroll to zoom. The slider runs from the summit down; each slice shows its full source frame (as recorded, or as analysed) with the exact contour used. Three orderings: the operator's reading (#20 = summit, bright opening as the cross-section; default), dark outlines by size, and dark outlines by time. A #18 button shows where the sequence started. Needs internet access for three.js.</p></div>
<!--MOUND3D-->
<!--MERGE-KF-START--><h2>K · The KIGA sweep, drift-corrected</h2>
<div class="card"><p>Every sweep #20–#31 was mapped into #20's coordinates with the drift model (Section D) before comparison, so each gain is judged on the same patch of sample.</p>
<div class="scroll"><table>
<tr><th>KIGA</th><th>Outcome</th><th>Halted-hold Z power 100–300 Hz (×1.14)</th><th>Direction-flip (lag) share</th><th>Same patch, same direction: error / Z</th><th>Same patch, up ↔ down: error / Z</th><th>Z streak anisotropy</th></tr>
<tr><td>1.14</td><td>clean</td><td>1×</td><td>0.87–0.94</td><td colspan="3">no trackable structure in #12–#18</td></tr>
<tr><td>2.3</td><td>clean</td><td>4.5×</td><td>0.88–0.91</td><td>0.31–0.40 / 0.26–0.33</td><td>0.40–0.57 / 0.18–0.49</td><td>107</td></tr>
<tr><td>4.6</td><td>clean, last stable</td><td>19×</td><td><b>0.79–0.84</b></td><td><b>0.49–0.54 / 0.46–0.62</b></td><td>0.36–0.51 / <b>0.41–0.58</b></td><td>113</td></tr>
<tr><td>9</td><td>oscillated, Z-guard abort</td><td>20×</td><td>0.85–0.86</td><td>— (one cycle)</td><td>0.39 / 0.45</td><td>122</td></tr>
</table></div>
<ul>
<li><b>4.6 images best</b> on the same patch, by about 0.15–0.3 in correlation over 2.3; 9 oscillated against the 158.7 Hz resonance.</li>
<li><b>The same morphology at every gain:</b> the per-gain drift-corrected averages agree (Z: 0.51 for 2.3 vs 4.6, 0.52 for 4.6 vs 9, 0.40 for 2.3 vs 9; flipped nulls −0.18 to 0.03). The structure is on the sample, not produced by the loop.</li>
<li><b>Still lag-dominated</b> (79–84% even at 4.6): slower lines are the next lever. Z streaking rises slightly with gain (107 → 113 → 122).</li>
<li>The running default was left at KIGA 3.07 (⅔ of 4.6) until a good tip confirms 4.6.</li>
</ul></div>
<div class="card verdict"><p><b>Why KIGA 2.3 looks smoother and more symmetric than 4.6, yet 4.6 is recommended.</b></p><ul>
<li><b>A slower loop smooths the image.</b> At 2.3 the loop reacts more slowly, so Z changes gently along each line. That filters out noise and real fine detail alike, and the image looks clean.</li>
<li><b>Most of what the 2.3 image shows is the loop itself.</b> 88–91% of it is the direction-flip (lag) pattern: a large, smooth swing that trace and retrace draw as mirror images (first-pass Section 6 shows the profiles). Smooth and symmetric is what lag looks like, not what this surface looks like.</li>
<li><b>4.6 follows more of the real surface, plus more noise.</b> The lag share drops to 79–84%, and the same patch repeats better between sweeps (error 0.49–0.54, Z 0.46–0.62, against 0.31–0.40 and 0.26–0.33 at 2.3). Repeatable detail is surface; that is the test that matters. The cost is visible roughness: the 158.7 Hz Z resonance is ~19× stronger in the halted hold at 4.6 than at 1.14 (4.5× at 2.3), and it ripples into the image.</li>
<li><b>The loop simulator agrees.</b> Replaying today's firmware loop over a known synthetic surface, Z follows the true surface about twice as well at 4.6 as at 2.3 (correlation 0.27 against 0.12).</li>
<li><b>So judge a gain by repeatability on the same patch, not by how smooth one image looks.</b> KIGA 9 shows where the trade-off ends: the resonance takes over and the loop oscillates. With this damaged tip the margin is modest, so the default stays at 3.07 until a good tip confirms 4.6.</li>
</ul></div>
<figure><img src="{img('figK1_maps.png')}" alt="Drift-corrected per-gain maps">
<figcaption><b>Every gain shows the same features at the same place on the sample: the morphology belongs to the sample, not to the loop.</b> All sweeps mapped into #20's coordinates and averaged per gain: error channel on top, Z folded S below. The right column stitches all 10 sweeps, covering ~30 × 45 nm of sample from a 30 nm window because the sample drifted through it. Grey: not scanned at that gain. Green: the circled feature of Section C. Colours as stored (error: dark = high point; Z: bright = low point). <i>Look at:</i> the long diagonal ridge through the green circle, present at 2.3, 4.6 and 9. 2.3 renders it smoothest, 4.6 with the most detail, 9 noisiest (see “Why 2.3 looks prettier” above).</figcaption></figure>
<figure><img src="{img('figK2_driftpath.png')}" alt="Drift path">
<figcaption><b>The sample drifted steadily, about 67 pm/s almost straight up the frame.</b> The circled feature's position against time (left) and its path within the frame (right): 19.8 nm up and 2.1 nm left in 300 s. <i>Look at:</i> the straight overall trend with no sudden jumps; the zig-zag is the ~1 nm up/down-sweep offset and the two small sideways jogs are the gain changes. At this rate a feature crosses the whole 30 nm window in about 7 minutes, which is why stage tracking (F2, roadmap G-ST) matters.</figcaption></figure>

<h2>F · General drift tool: fiducial hopping</h2>
<div class="card"><p>The hand-built result started from the feature the operator circled. <code>fiducial_drift.py &lt;day&gt; &lt;first&gt; &lt;last&gt;</code> does the same without a starting feature: it cuts every sweep into a grid of 96 × 96 px candidate fiducials, finds each in the neighbouring sweep, and accepts a pair only when the error and Z channels independently agree on the shift (≥ 5 agreeing fiducials each). Skip-one pairs (up with up, down with down) add redundancy, and a robust fit drops pairs that disagree with the rest. One example reference fiducial is followed from sweep to sweep; when it leaves the window or stops agreeing, the chain hops to the nearest agreeing fiducial.</p>
<table>
<tr><th>Run</th><th>Drift (px/s, rows / cols)</th><th>Up/down-sweep offset</th><th>Fit rms (rows / cols)</th><th>Pairs used</th></tr>
<tr><td>Oct 22 #20–#31 (no hints)</td><td>-0.52 / -0.01</td><td>5.7 px</td><td>6.0 / 2.2 px</td><td>9</td></tr>
<tr><td>Oct 22, hand-built from the circle (D)</td><td>−0.56 / −0.03</td><td>8.4 px</td><td>5.1 / 2.6 px</td><td>13</td></tr>
<tr><td>Sep 24 #1586–#1599 (good tip, 24.8 nm)</td><td>-0.23 / +0.12</td><td>not determinable (no up↔down pair locked at those fast lines)</td><td>1.5 / 2.5 px</td><td>9</td></tr>
</table>
<p class="sub" style="margin:8px 0 0">Negative rows = content moving up the frame. Limits: stretches with no trackable structure don't lock (Oct 22 #20–#21, #30–#31); when up and down sweeps look too different, only same-direction pairs lock and the offset is reported as not determinable rather than 0.</p></div>
<figure><img src="{img('fiducial_drift_2026-Oct-22_20-31.png')}" alt="Fiducial hopping, Oct 22">
<figcaption><b>The automatic tool recovers the drift without being told where to look.</b> Oct 22 #20–#31, one panel per sweep. Coloured square: the example reference fiducial and where it was found; the next template cut from it is also marked. The reference is followed from #22 through #23, #25 and #26, then hops (colour change) at #27 to a nearby fiducial and continues to #28. <i>Look at:</i> the square stays on the same piece of surface while that surface moves up the frame, and a hop replaces the reference without breaking the chain. Result (table above): 0.52 px/s, against 0.56 px/s from the hand-built analysis.</figcaption></figure>
<figure><img src="{img('fiducial_drift_2026-Sep-24_1586-1599.png')}" alt="Fiducial hopping, Sep 24">
<figcaption><b>The same tool on a good-tip day: a tighter fit and slower drift.</b> Sep 24 #1586–#1599 (24.8 nm window). The reference follows the up sweeps #1586 → #1588 → #1590 → #1592, the chain breaks once, and a new reference covers #1594 → #1596 → #1598. <i>Look at:</i> how sharp and repeatable the features are with a good tip: the standard Oct 22 should reach after a tip change. Fit residual 1.5 / 2.5 px here against 6.0 / 2.2 px on Oct 22.</figcaption></figure>
<h2>F2 · Toward live drift: a frame-drift trail</h2>
<div class="card"><p>Simulated on Oct 22 as if live: each sweep is registered in bands of 96 rows (~9 s of scanning) against the previous sweep of the same direction, as the lines arrive. After the first lock the search is limited to ±22 px around the position the current velocity predicts (tracking mode).</p>
<ul><li><b>Speed:</b> ~90 ms per update (worst 280 ms) for both channels, against a new band every ~9 s. Processing is not the limit.</li>
<li><b>Data:</b> the GUI already receives every line as it arrives; trace and retrace for error and Z are all that is needed.</li>
<li><b>Lock:</b> after the first lock, 2 of every 3 bands lock, an update every ~9–12 s; velocity 0.51 px/s up the frame (60 pm/s), sideways ≈ 0, matching the whole-sweep result. The bottom band of each sweep never locks because the sample moves up: those rows are new territory the previous sweep never saw. That is fiducial hopping at band scale, and live it should be labelled as such rather than as a lost lock.</li>
<li><b>Slow start:</b> blind search on bands did not lock until #25 (~2.5 min in), so the trail under-reports the early drift. Seeding it from a whole-sweep fiducial match after the second same-direction sweep (~50 s) would fix that.</li></ul></div>
<figure><!--LIVETRAIL--><figcaption><b>Drift can be tracked live from bands of lines as they arrive, at ~90 ms of computing per update.</b> Oct 22 #22–#31 replayed as if live, one frame per band update (600 ms per frame). Left: the frame-drift trail. The lead point is orange when the band locked and grey when coasting on the last velocity; fading arrows are the last 8 updates; the title gives speed and direction. Drift is drawn as the feature's motion within the frame (up = up the frame). Right, at the same moment: the whole error frame being registered, with the operator's circle carried by the hand-built drift model (green dashed, Section D), the contour found inside it (cyan: the bright opening inside the dark structure, the default reading of the 3D mound in C5) and the 96-row band used for this update (white dashed). <i>Look at:</i> the circle and contour climb the frame with the feature while the trail on the left heads up at the same rate: the live tracker, which never sees the circle, recovers the motion of the feature the operator first used as a bearing. The bottom band never locks because the sample moves up: those rows are new territory.</figcaption></figure>
<!--MERGE-KF-END-->
<!--MERGE-Q-START--><h2>Q · Open questions for discussion</h2>
<div class="card" style="border-left:4px solid var(--acc)">
<p><b>Q1 · What dark means in the error image (largely resolved: a display inversion).</b> The firmware's error is setpoint − log(current) (<code>stm_firmware.hpp:323</code>), so its darkest value is the most current: the surface closest to the tip, a <b>high point</b>. The darkest pixels sit at exactly the value for ADC 32767, read before any substitution, the same reading the tip gave in contact during the 19:10 crash; real tunnelling reads positive (halted median +184 against a 160 setpoint) and no current reads at or below the idle level, displayed bright. So the dot and the "A" are high points, which matches the operator's reading of the dot as the top of the mound; the disagreement was that the stored error (and Z) images are inverted relative to the convention bright = peaks, dark = valleys. Exceptions: ~2% of pixels are false dark specks where an exact-zero reading (no signal) was repainted as clipped. Bench confirmation planned (T1); display standardisation planned (I-10).</p>
<p><b>Q2 · Which way the slices run.</b> Operator: #20 is the summit and later sweeps are slices further down. Analysis: by dark area #20 is the widest cut and later cuts are smaller. Both depend on Q1. Under the operator's reading, the bright opening inside the dark structure grows and nests (64–71%) from #21 to #26; it breaks at #20→#21 (14%) and from #27 on. Both readings are switchable in the 3D mound (C5).</p>
<p><b>Q3 · Whether Z drift moves the slice.</b> The loop's Z output ramped 14–49 codes/s during the sweep. Operator correction (accepted): that ramp is the loop's action, not a direct measurement of sample drift, because the loop does not hold a fixed gap while the current is absent most of the time. Separating them needs the 3D model of mound, tunnelling, clipping and the firmware loop (C3).</p>
<p><b>Q4 · A phantom current while scanning (new).</b> While scanning, samples without tunnelling read −50 to −64 on the ADC, about 40 LSB below the −15 idle with the tip far away; this only happens while the scan moves. The firmware takes the absolute value (<code>logTable[abs(adc_val)]</code>), so the loop reads those samples as ~55 LSB of current, about a third of the 160 setpoint. Candidates: capacitive pickup of the X/Y drive or a ground shift. Should the firmware subtract a measured offset instead?</p>
<p><b>Q5 · Up/down naming in the live view.</b> This report and the replay viewer call the first half of each Y-cycle the up sweep (▲); the live raster calls it the down sweep (plan item 5d), so live and replay labels are currently reversed.</p></div>
<!--MERGE-Q-END-->
<h2 style="margin-top:46px">First pass (superseded where noted above)</h2>
<p class="data"><b>Data:</b> Oct 22 #12–#32 (tip check, KIGA 1.14 → 9) and Sep 24 good-tip controls · analysed before the drift was measured</p>
<div class="card q"><p><b>What still applies from this first pass.</b> It compared whole frames without correcting for drift. Some of it stands and is used above; some is superseded.</p><ul>
<li><b>Still valid:</b> the folded-S method (trace + retrace cancels lag) and the split into surface and lag (Sections 2 and 6); the finding that similarity between raw images is mostly lag; the Sep 24 good-tip baseline (repeat ~0.9) as the acceptance target; the dark diagonal band persisting within each gain step (4b); the lag profile changing with gain (6), which explains why images seem to jump at each gain change and why 2.3 looks smooth (K); and the next steps in 7, with the repeat test now done after drift correction.</li>
<li><b>Superseded:</b> “no persistent morphology” (1, 4, 5): drift moves the sample ~25 px per Y-cycle and whole-frame alignment could not follow it (Section D). The whole-frame shifts in 3 are not a drift measurement; Section D measures 0.56 px/s. “The pattern resets at each gain change” (4b, 5): with drift corrected, the same morphology survives every gain change (D6, K).</li>
</ul></div>

<h2>1 · Control: the same test on a known-good day</h2>
<figure><img src="{img('fig0_control.png')}" alt="Sep 24 and Oct 22 sweep pairs aligned and differenced">
<figcaption><b>The repeat test works on a good tip; on Oct 22, without drift correction, it finds almost nothing.</b> Folded surface estimate S of two consecutive same-direction sweeps, the second aligned onto the first by whole-frame search, and their difference. Top: Sep 24 (good tip): features line up and cancel in the difference (repeat 0.91). Middle and bottom: Oct 22, the best pair (KIGA 4.6, 0.27) and a typical one (KIGA 2.3, 0.09). <i>Look at:</i> the nearly empty Sep 24 difference against the Oct 22 differences full of row streaks. Partly superseded: drift defeated the whole-frame alignment; aligned by the drift model, Oct 22 pairs repeat at 0.4–0.6 (Section D).</figcaption></figure>

<h2>2 · Does the image repeat?</h2>
<figure><img src="{img('fig3_persistence.png')}" alt="Repeat correlation per sweep pair">
<figcaption><b>In uncorrected images, what repeats is the loop's lag pattern, not the surface.</b> Each point compares a sweep with the previous sweep of the same direction, after whole-frame alignment. Blue: folded S, the surface estimate. Green: S with the average row removed. Grey: trace only, rows levelled. Red: the part that flips with scan direction (lag). <i>Look at:</i> grey moves with red, not with blue: raw-trace similarity comes from lag. Still valid; the low blue values are superseded by Section D's drift-corrected 0.4–0.6.</figcaption></figure>
<div class="card scroll"><table><tr><th>Pair</th><th>Dir</th><th>Δt (s)</th><th>Shift dx, dy (px)</th><th>S repeat</th><th>Trace repeat</th><th>Lag repeat</th></tr>{rows}</table>
<div class="sub" style="margin:8px 0 0">1 px = 0.117 nm. Sep 24 reference pairs: S repeat 0.74–0.98, with shifts of a few px.</div></div>

<h2>3 · Does the field move?</h2>
<figure><img src="{img('fig2_drift.png')}" alt="Shift and correlation against the first sweep">
<figcaption><b>Whole-frame alignment returned random shifts: there was nothing to lock onto at full-frame scale, so this is not a drift measurement.</b> Left: shift of each sweep against the first sweep of its direction, from phase correlation. Right: S correlation after that alignment. <i>Look at:</i> shifts jumping 30–80 px with no trend and correlations near zero; on Sep 24 the same method gives small, consistent shifts. Superseded: local templates (Section D) do measure the drift, 0.56 px/s up the frame.</figcaption></figure>

<h2>4 · Row alignment and processing variants</h2>
<figure><img src="{img('fig1_variants.png')}" alt="Grid of sweeps processed six ways">
<figcaption><b>Without drift correction, no processing choice makes a feature persist from sweep to sweep.</b> Each row is one sweep and each column one processing: plane only; each row's offset and slope removed; median of row differences; folded S; S with the average row removed; error channel. Each panel has its own 1–99% stretch. <i>Look at:</i> whether any feature can be followed down a column. Useful as a guide to what each processing does; the conclusion is superseded, because the sample moves about 3 px per sweep and ~25 px per Y-cycle.</figcaption></figure>

<h2>4b · Error channel, smoothed: structure that persists within a gain step</h2>
<figure><img src="{img('err_montage.png')}" alt="Error trace frames 12 to 32">
<figcaption><b>Smoothed error images show a dark diagonal band that recurs in every sweep from #20 to #31.</b> Error trace, rows levelled, each sweep from #12 to #32 in time order. <i>Look at:</i> the near-vertical diagonal band at about 55–75% across, in both up and down sweeps. This was the first sign of persistent structure; it is the dark band through the circled feature of Section C (compare Figure K1).</figcaption></figure>
<div class="card"><p>With row streaks smoothed out (Gaussian, σ = 4 px), neighbouring sweeps correlate <b>0.41–0.68 within the 2.3, 4.6 and 9 steps</b> (and 0.69 for #16 → #17), in both up and down sweeps. Across a gain change the correlation drops to <b>0.02–0.11</b>. Measured shifts: horizontal about 0 px throughout; vertical 11–26 px (about 1.3–3 nm) at 1.14 (#17), 4.6 (#28) and 9 (#30, #31).</p>
<p><b>Surface or loop?</b> Not separable from this data. A loop-lag pattern is fixed in the frame and resets when the gain changes, which matches. A real surface edge would also render differently in the error channel at each gain. The deciding test is the offset test from the resolution report: move the scan offset by a few nm; a surface feature moves by that amount in the image, a loop pattern stays put.</p></div>

<h2>5 · Averaged per gain step</h2>
<figure><img src="{img('fig4_rung_avgs.png')}" alt="Aligned averages per gain step">
<figcaption><b>Per-gain averages looked unrelated because the drift was not corrected.</b> Top: all full sweeps of each gain step aligned by whole-frame search and averaged (folded S). Bottom: the same with the average row removed. Aligned correlations between steps: −0.18 to 0.21. <i>Look at:</i> how little the averages resemble each other. Superseded by Figure K1: with drift corrected, the per-gain averages agree (Z 0.40–0.52).</figcaption></figure>

<h2>6 · The lag profile changes with gain</h2>
<figure><img src="{img('fig5_profiles.png')}" alt="Average row profiles per gain step">
<figcaption><b>The loop's lag draws a large, smooth pattern into every line, and its shape changes with the gain. At low gain this pattern, not the surface, dominates the image.</b> Each curve is the average of all lines in one sweep (rows levelled), trace in blue (left to right) and retrace in orange (right to left), one panel per gain step. A real surface feature appears at the same position in trace and retrace; lag pushes the two in opposite directions, so lag shows up as blue and orange curves that mirror each other. <i>Look at:</i> in every panel the blue and orange curves roughly mirror each other and repeat from sweep to sweep within a step: that is lag (88–91% of the image at 2.3, 79–84% at 4.6; Section K). Between steps the shape and the position of the hump change, so the image seems to move at each gain change although the sample did not. At 9 the curves turn irregular as the loop oscillates. Still valid.</figcaption></figure>

<h2>7 · What to do next</h2>
<div class="card"><ul>
<li>Recover or replace the tip, then repeat KIGA 1.14 → 2.3 → 4.6, with feedback engaged before any scan.</li>
<li>Run the offset test (move XOFS/YOFS a few nm between sweeps at fixed gain) to tell whether the error-channel band is surface or loop.</li>
<li>Use this repeat test as the acceptance check before judging gain: S repeat of about 0.7 or more between consecutive same-direction sweeps, as on Sep 24.</li>
<li>Take a scan during the first clean tunnelling after approach, with CC engaged, so a reference image exists before anything goes wrong.</li>
</ul></div>

<h2>Method</h2>
<div class="card" style="font-size:13px">Images come from the replay player's own loader (<code>sweep_player.DayData.image</code>), so sweep numbers and orientation match the player. Missing rows are filled from the nearest received row. Folded S = (trace + retrace)/2 after each row's offset and slope are removed; the lag part = (trace − retrace)/2. Shifts come from Hann-windowed phase correlation on S with sub-pixel peak fitting; correlations are Pearson correlations over the overlap after the integer shift. Partial sweeps (#14, #19, #24, #29, #32) are excluded. Sep 24 control pairs: #1586–#1599 (24.8 nm) and #1802–#1811 (27.1 nm). Z units are relative. Drift analysis: 96 × 96 px templates (stride 32) on row-levelled, lightly smoothed (σ = 1 px) images, normalized cross-correlation over the whole prior frame, consensus within 5 px, nulls from a flipped frame and a Sep 24 frame; validated on Sep 24 pairs #1806→#1808 and #1588→#1590. Case study: <code>blob_case.py</code>, <code>blob_sat.py</code>, <code>blob_fig2.py</code>, <code>double_tip.py</code>, <code>tip_jumps.py</code>, <code>case_fixed.py</code>, <code>contour_stack.py</code>, <code>stack_shape.py</code>. Scripts: <code>patch_track.py</code>, <code>patch_validate.py</code>, <code>drift_proof.py</code>, <code>drift_model.py</code>, <code>morph_report.py</code>, <code>validate_sep24.py</code>, <code>control_fig.py</code>, <code>build_morph_html.py</code> archived in <code>software/pc/qtpanda/analysis/oct22/</code>.</div>
</main></body></html>"""

# REVISION v3: per-section data lines
import re as _re
DATA = {'D': 'Oct 22 · #12–#31 (tip check, then KIGA 1.14 → 9); Sep 24 good-tip pairs as controls', 'D1': 'Oct 22 · pairs #21→#22, #23→#25, #27→#28, #30→#31 (KIGA 2.3, 4.6, 9) · control: Sep 24 #1806→#1808 (good tip)', 'D2': 'Oct 22 · every consecutive pair from #12 to #31 (tip check, then KIGA 1.14 → 9) · error and Z channels', 'D3': 'Oct 22 · #12–#31; drift model fitted to 13 cross-checked pairs within #20–#31', 'D4': 'Oct 22 · all pairs within #20–#31 (KIGA 2.3, 4.6, 9)', 'D5': "Oct 22 · the 10 full sweeps #20–#31, shown in #20's coordinates", 'D6': 'Oct 22 · neighbouring sweeps ≤ 55 s apart within #20–#31', 'D7': 'Conclusions from D1–D6 (Oct 22 #20–#31)', 'C': 'Oct 22 · #18–#31, focus on #20–#23 (KIGA 2.3) · error channel unless noted', 'C1': 'Oct 22 #20–#31 and the status record during the sweep (19:25–19:35)', 'C2': 'Oct 22 #20–#31 · loop Z output 19:21–19:40', 'C3': 'Proposed tests: no data yet', 'C4': 'Oct 22 · 9 outlines, from #20, #21, #22, #23, #25, #26, #27, #28, #30', 'C5': 'Oct 22 · the same 9 sweeps as C4, plus #18 for context', 'K': 'Oct 22 · #20–#31 at KIGA 2.3, 4.6, 9 and #15–#18 at 1.14, each step preceded by a 30 s halted hold (19:25–19:35)', 'F': 'Oct 22 #20–#31 · Sep 24 #1586–#1599 (good tip, 24.8 nm)', 'F2': 'Oct 22 #22–#31 replayed as if live (#20→#22 is the first same-direction pair)', 'Q': 'Oct 22, whole session (18:22–19:52)', '1': 'Sep 24 good-tip pair · Oct 22 pairs at KIGA 4.6 and 2.3', '2': 'Oct 22 · same-direction pairs within #12–#31', '3': 'Oct 22 #12–#31', '4': 'Oct 22 #12–#31, one row per sweep', '4b': 'Oct 22 #12–#32', '5': 'Oct 22 · full sweeps of each gain step, #12–#31', '6': 'Oct 22 #12–#31, one curve per sweep'}
for _k, _v in DATA.items():
    html, _n = _re.subn(r'(<h2>' + _re.escape(_k) + r' ·.*?</h2>)', lambda m: m.group(1) + '\n<p class="data"><b>Data:</b> ' + _v + '</p>', html, count=1, flags=_re.S)
    assert _n == 1, _k
open(OUT, "w", encoding="utf-8").write(html)
print(OUT, os.path.getsize(OUT) // 1000, "kB")
