"""Build the Oct 22 report v2 (new artifact; v1 stays as the reference):
drift registration line by line as the central thread, peaks bright everywhere, registered 3D height.
Output: TeamUpdate/data/2026-Oct-22/report_v2/ (index.html, mound.html, figs/, REPORT-TEXT.md)."""
import os, re, json, shutil, html
HERE = os.path.dirname(os.path.abspath(__file__))
DAY = "C:/Users/enact/Projects/qt-panda/TeamUpdate/data/2026-Oct-22"
OUT = os.path.join(DAY, "report_v2"); FIGS = os.path.join(OUT, "figs")
if os.path.isdir(FIGS): shutil.rmtree(FIGS)
os.makedirs(FIGS)
V1_URL = "https://claude.ai/artifact/9aZPBvpbLL48iMj1j89Rxy"
M2 = os.path.join(HERE, "morph_report_v2"); M1 = os.path.join(HERE, "morph_report")
for src, name in ((os.path.join(M2, "v2_register.png"), "register.png"), (os.path.join(M2, "v2_timelapse.gif"), "timelapse.gif"),
                  (os.path.join(M2, "v2_feature.png"), "feature.png"), (os.path.join(M2, "v2_crater.png"), "hollow_test.png"),
                  (os.path.join(M2, "v2_gain.png"), "gain.png"), (os.path.join(M1, "live_trail_v2.gif"), "live_trail.gif"),
                  (os.path.join(M1, "figD3_track_chain.png"), "drift_chain.png"), (os.path.join(M1, "figD4_model_test.png"), "drift_predict.png"),
                  (os.path.join(M1, "figK2_driftpath.png"), "drift_path.png")):
    shutil.copy(src, os.path.join(FIGS, name))
page3d = open(os.path.join(HERE, "mound_v5_template.html"), encoding="utf-8").read().replace(
    "__DATA__", open(os.path.join(M2, "v2_3d.json"), encoding="utf-8").read())
open(os.path.join(OUT, "mound.html"), "w", encoding="utf-8").write(page3d)
met = json.load(open(os.path.join(M2, "v2_metrics.json")))
rim = met["rim"]

road = open("C:/Users/enact/Projects/qt-panda/docs/test-plans/roadmap.html", encoding="utf-8").read()
rmain = road.split("<main>", 1)[1].split("</main>", 1)[0]
rmain = re.sub(r"<h1>.*?</h1>", "", rmain, count=1, flags=re.S).replace("<h2>", "<h3>").replace("</h2>", "</h3>")
rmain = re.sub(r'<li><a href="[^"]*">([^<]*)</a></li>', r"<li>\1</li>", rmain)
rscript = road.split("</main>", 1)[1].split("<script>", 1)[1].split("</script>", 1)[0]
CSS = re.search(r'CSS = """(.*?)"""', open(os.path.join(HERE, "build_artifact.py"), encoding="utf-8").read(), re.S).group(1)
CSS += "\n.data{font-size:13px;color:var(--mut);margin:-2px 0 10px;padding:3px 8px;border-left:3px solid var(--acc)}\n"


def fig(name, alt, cap, w=None):
    st = f' style="max-width:{w}px;width:100%"' if w else ""
    return f'<figure><img src="figs/{name}" alt="{html.escape(alt)}"{st}><figcaption>{cap}</figcaption></figure>'


def data(t): return f'<p class="data"><b>Data:</b> {t}</p>'


LOOK = "<i>Look at:</i>"
rows_rim = "".join(
    f"<tr><td>{n}</td><td>#{i}</td><td>{'▲' if i in (20, 22, 25, 27, 30) else '▼'}</td><td>{k}</td>"
    f"<td>{rim[str(i)]['err']:+.2f} ({rim[str(i)]['err_pct']:.0f}th)</td><td>{rim[str(i)]['z']:+.2f} ({rim[str(i)]['z_pct']:.0f}th)</td></tr>"
    for n, (i, k) in enumerate(((20, "2.3"), (21, "2.3"), (22, "2.3"), (23, "2.3"), (25, "4.6"), (26, "4.6"), (27, "4.6"), (28, "4.6"), (30, "9"), (31, "9")), 1))

body = f"""
<h1>Oct 22 report v2: the sample frame, peaks bright</h1>
<div class="sub">qt-panda STM · Oct 22, 2026 · 30 nm, 256 × 256, ~10.5 Hz lines · revised 2026-10-23 · v1 (reference, unchanged): <a href="{V1_URL}">Oct 22 Morphology Report</a></div>

<div class="card verdict"><b>What is new in v2.</b><ul>
<li><b>Peaks bright, valleys dark, in every image.</b> The stored error and Z both put a peak low, so v1 showed high points dark. v2 shows −error and −Z throughout, as the live raster and replay now do (roadmap I-10).</li>
<li><b>Every line is placed by its own time.</b> v1 gave each sweep one drift shift; the sample keeps drifting during the 25 s sweep (~14 px top to bottom). Correcting line by line raises the up ↔ down sweep agreement by ~0.07 (Section 2).</li>
<li><b>The circled dot is a summit that becomes a hollow.</b> In #20 the dot is high. From #21 its centre reads no current at all while a ring around it clips: a hollow at least ~0.4 nm deep, ringed by high ground (Section 3). The “A” is that rim plus the ridge beside it.</li>
<li><b>The 3D view now shows measured height</b> (−Z, drift-registered, per sweep, with a time slider) instead of stacking outlines by rank (Section 4).</li>
</ul></div>

<h2>0 · Start here: the instrument, the day, and how to read this report</h2>
<div class="card">
<p><b>The instrument.</b> qt-panda is a home-built scanning tunnelling microscope (STM). A sharp metal tip is held a few ångströms above a conducting sample with a small bias voltage between them (−50 mV here), so a tunnelling current flows (setpoint 500 pA). The current changes about tenfold per ångström of gap, which makes it a very sensitive height probe. A feedback loop (<b>constant-current mode</b>) moves the tip up and down (<b>Z</b>) to hold the current at the setpoint while the tip rasters across a 30 × 30 nm square. How fast the loop reacts is set by its integral gain, <b>KIGA</b>.</p>
<p><b>The images.</b> One <b>sweep</b> is one full image: 256 lines × 256 pixels (1 px = 0.117 nm), about 25 s. The slow (Y) scan goes one way and comes back; the first half of each Y-cycle is the <b>up sweep (▲)</b>, the second the <b>down sweep (▼)</b>. Each line is scanned left to right (<b>trace</b>) and back (<b>retrace</b>). Two channels: <b>Z</b>, the tip height the loop chose, and <b>error</b> = log(setpoint) − log|current|. When the loop lags, trace and retrace shift in opposite directions; their average (<b>folded S</b>) cancels the lag and is the best height estimate.</p>
<p><b>Colours (v2).</b> Bright = high (surface closer to the tip, more current), dark = low, in both channels. Error images are shown as −error, so bright = more current; Z images as −Z, so bright = higher surface. With this slow loop the error image is close to a constant-height cut through the surface: only a ~0.38 nm band of heights is visible, from “no current” (darkest) to “clipped at ~100 nA” (brightest).</p>
<p><b>The sample frame.</b> The sample drifts under the tip at ~66 pm/s, mostly up the frame. All “registered” images place every line where that piece of sample was at the middle of #20, so a feature stays put while the scan window moves over the sample.</p>
<p><b>The day: Oct 22, 2026, 18:22–19:52.</b></p>
<div class="scroll"><table>
<tr><th>Sweeps</th><th>Time</th><th>What happened</th><th>Used here</th></tr>
<tr><td>—</td><td>18:44–19:09</td><td>Tip approach</td><td>—</td></tr>
<tr><td>—</td><td>19:10:30</td><td><b>Tip crash</b> while parked at fixed Z with feedback off. Every image below is from this damaged tip.</td><td>—</td></tr>
<tr><td>#0–#11</td><td>19:12–19:16</td><td>Scan at fixed Z, mostly saturated; halted</td><td>no</td></tr>
<tr><td>#12–#19</td><td>19:24–19:28</td><td>Tip check and KIGA 1.14: nothing trackable</td><td>drift fit only</td></tr>
<tr><td>#20–#24</td><td>19:28–19:30</td><td>KIGA 2.3</td><td>all sections</td></tr>
<tr><td>#25–#29</td><td>19:31–19:32</td><td>KIGA 4.6 (last stable gain)</td><td>all sections</td></tr>
<tr><td>#30–#32</td><td>19:33–19:34</td><td>KIGA 9, oscillated, aborted</td><td>all sections</td></tr>
<tr><td>#33–#56</td><td>19:42–19:52</td><td>Operator scan at KIGA 3.07</td><td>no</td></tr>
</table></div>
<p class="sub" style="margin:6px 0 0">Partial sweeps (#24, #29, #32) are left out, so the series is the 10 full sweeps #20–#23, #25–#28, #30, #31.</p>
<p><b>Reading path.</b> 1 drift measured → 2 drift removed → 3 the feature, followed in the sample frame → 4 registered 3D height → 5 which gain → 6 drift tracked live → 7 open questions → 8 next tests → roadmap.</p>
</div>

<h2>1 · The sample drifts: measured from the images</h2>
{data("Oct 22 #12–#31; model fitted to 13 cross-checked pairs within #20–#31")}
<div class="card"><p>Small 96 × 96 px rectangles cut from each sweep are found again in the previous sweep. A pair counts only when the error and Z channels agree on the shift. The shifts then chain consistently (A→C = A→B + B→C) and predict where the surface will be without searching. The fitted model: content moves <b>0.56 px/s ≈ 66 pm/s up the frame</b>, sideways ≈ 0; up and down sweeps sit <b>8.4 px ≈ 1 nm</b> apart (scanner hysteresis); each gain change adds a jump of ~4 px. Residual: 5.1 px vertical, 2.6 px sideways. The step-by-step proof (template insets, every vector) is in v1, sections D1–D6.</p></div>
{fig("drift_path.png", "Drift path of the circled feature",
     f"<b>The sample drifted steadily, about 67 pm/s almost straight up the frame.</b> The circled feature's position against time (left) and its path within the frame (right): 19.8 nm up and 2.1 nm left in 300 s. {LOOK} the straight trend with no sudden jumps; the zig-zag is the ~1 nm up/down offset and the two sideways jogs are the gain changes. At this rate a feature crosses the 30 nm window in about 7 minutes.")}
{fig("drift_chain.png", "Chain consistency",
     f"<b>The measured shifts add up the way real motion does.</b> Left: displacement since #20 from the model (lines) with the 13 measured shifts (arrows). Right: shift A→C measured directly against A→B + B→C; real motion lands on the diagonal. {LOOK} #20–#31 on the diagonal (misses 3–9 px); #12–#18 far off it, so those sweeps have no trackable structure.")}
{fig("drift_predict.png", "Prediction-only test",
     f"<b>The model predicts where the surface will be without any search, so the structure is on the sample.</b> Correlation of every pair in #20–#31 aligned only by the predicted shift (blue), left fixed in the frame (orange), shifted at random by the same amount (grey, 95th percentile) or against a flipped frame (red). {LOOK} blue above the rest; it falls with time (0.4–0.6 at 25 s, 0.1–0.3 at 250 s): real structure that slowly changes.")}

<h2>2 · Removing the drift, line by line</h2>
{data("Oct 22, the 10 full sweeps #20–#31, both channels")}
<div class="card"><p>Each scanned line has a recorded time. Its rows are placed in the sample frame at <code>row − dy(t)</code>, where dy(t) is the drift model at that line's own time (plus the up/down offset and gain-change jumps), and its columns are shifted by the sideways drift. Grey in the figures = parts of the sample never scanned.</p>
<div class="scroll"><table>
<tr><th>Mean correlation between registered sweeps</th><th>one shift per sweep (v1)</th><th>line by line (v2)</th></tr>
<tr><td>up ↔ down neighbours, error / Z (9 pairs)</td><td>0.42 / 0.46</td><td><b>0.49 / 0.47</b></td></tr>
<tr><td>same direction, error / Z (8 pairs)</td><td>0.38 / 0.41</td><td>0.39 / 0.42</td></tr>
</table></div>
<p class="sub" style="margin:8px 0 0">Line-by-line placement mainly fixes the up ↔ down pairs: an up and a down sweep are sheared in opposite directions by the drift during the sweep, which one shift per sweep cannot undo. Same-direction pairs share the same shear, so they barely change. This also means v1's 8.4 px up/down offset partly contained this shear.</p></div>
{fig("register.png", "Registered average vs uncorrected",
     f"<b>In the sample frame, ten sweeps average into a sharper picture; averaged as scanned they blur.</b> Top: −error; bottom: −Z (folded S). Left: #20 alone in the sample frame. Middle: all 10 sweeps registered line by line and averaged; the frame is taller than 30 nm because the window drifted ~20 nm over the sample. Right: the same sweeps averaged as scanned. Green: the circled feature. {LOOK} the bright ridge and the ring at the circle stay sharp in the middle and smear on the right.")}
{fig("timelapse.gif", "Time-lapse: as scanned vs registered",
     f"<b>Registered, the feature stays still while the window moves; as scanned, the feature climbs the frame.</b> Each frame is one sweep (#20 → #31, 0.9 s per frame), −error, peaks bright. Left: the sweep as scanned, green circle carried by the drift model. Right: the same sweep in the sample frame, circle fixed. {LOOK} on the right, the circle stays on the same piece of surface while the scanned area slides down the canvas; this is what a drift-registered replay mode would show.", 900)}

<h2>3 · The circled feature: a summit that becomes a hollow</h2>
{data("Oct 22 #20–#31 in the sample frame; ADC values for #22 from the stored error (exact inverse of error = log(setpoint) − log|ADC|)")}
{fig("feature.png", "The feature in every sweep, registered",
     f"<b>The dot in #20 is high; from #21 on its centre is low and ringed by high ground.</b> The same 14 × 14 nm patch of sample in every sweep, drift-registered line by line; −error on top, −Z (folded S) below; green = the circle drawn on #20. {LOOK} #20: a bright dot (high). #21–#26: a dark centre inside a bright ring, with the long bright ridge running down the left (the “A”). #27–#31: the ring fades and the ridge dominates. Z shows weaker, noisier contrast and only partly agrees.")}
<div class="card"><p><b>What the ADC reads there (#22).</b></p>
<div class="scroll"><table>
<tr><th>Place (drift-registered)</th><th>|ADC| per pixel</th><th>Meaning</th></tr>
<tr><td>Centre of the hollow (cyan + in Section 4), r ≤ 0.9 nm</td><td><b>~50 counts</b>; 99% of pixels at or below 64</td><td>No tunnelling at all: the scan-time ADC offset (raw ≈ −50) read through abs(), not real current</td></tr>
<tr><td>Brightest 20% of the ring 1.6–3.0 nm out</td><td><b>~31,800 counts</b> (~100 nA); 49% at the 32,767 clip</td><td>Near point contact: the highest ground</td></tr>
<tr><td>Centre of the circle drawn on #20</td><td>~27,500 counts; 39% clipped</td><td>On the bright left ridge (the A's leg), 2.7 nm left of the hollow</td></tr>
<tr><td>Whole #22 frame</td><td>median 57; 58% no current, 5% clipped</td><td></td></tr>
</table></div>
<p class="sub" style="margin:8px 0 0">So the hollow and its rim span the entire visible band, from no current to clipped. If Z stayed roughly level over those ~3 nm, the hollow is at least ~0.4 nm deeper than the rim; both ends are off-scale, so that is a lower bound.</p></div>
{fig("hollow_test.png", "Hollow test per sweep",
     f"<b>The error channel shows a dome at #20, a hollow from #21 to #26 that fades through KIGA 4.6, and no consistent signal in Z.</b> For each sweep: rim (1.6–3.0 nm) minus centre (≤ 0.9 nm) around the hollow centre, in units of that sweep's spread; above 0 = centre lower than the rim. Grey: 5–95% of the same measure at 400 random places in the same sweep. {LOOK} left: #20 below the grey band (a dome, 1st percentile), #21–#26 at or above its top (94th–100th percentile); right: Z wanders inside the band.")}
<div class="card scroll"><table><tr><th>#</th><th>Sweep</th><th>Dir</th><th>KIGA</th><th>Hollow, −error (percentile)</th><th>Hollow, −Z (percentile)</th></tr>{rows_rim}</table></div>
<div class="card"><p><b>Reading it.</b></p><ul>
<li><b>The summit went first.</b> The tip passed this top at near point contact (~0.5 MΩ) on every line of #20. 25 s later the top reads no current and a rim around it clips. Pressing a soft or loosely bound top into a rim would do exactly this. This is the leading explanation, and the footprint test (Section 8) can confirm it.</li>
<li><b>Why Z barely shows it.</b> The loop is slow (lag is 80–90% of the image), so Z cannot follow a 3 nm hollow within a line; the current swings instead, which is why the error image carries the shape. Z repeats only 0.3–0.6 between sweeps with this tip.</li>
<li><b>Alternatives still open.</b> The slice level creeping as the loop's on/off balance shifts (it would change the whole patch, not just this spot) and the gain changes (the ring fades through 4.6 and is gone at 9).</li>
<li><b>Ruled out in v1:</b> a double tip (no fixed-offset repeat in the autocorrelation) and abrupt tip changes during #20–#23 (no level steps in trace and retrace near the feature).</li>
</ul></div>

<h2>4 · Registered 3D height</h2>
{data("Oct 22, the 10 full sweeps; ~17.6 × 17.8 nm window around the feature, sample frame")}
<div class="card"><p><b>What changed from v1.</b> v1 stacked each sweep's dark outline as a contour and counted how many enclose a point, offering three competing orderings because the meaning of dark was disputed. With the colour question settled and drift removed line by line, v2 shows what was measured: each sweep's own −Z surface (trace and retrace averaged), in the sample frame, step by step in time. Colour can be −error (current) or height. The panel beside it shows the sweep as scanned and the registered window, so you can check that the feature stays put.</p>
<p><b>How to use it.</b> Drag the slider or press Play to step through time; the averages per gain smooth what does not repeat. Cyan + = the hollow centre; green = the circle from #20. Needs internet access for three.js.</p></div>
<iframe title="Registered 3D height" src="mound.html" style="width:100%;height:860px;border:1px solid var(--line);border-radius:8px;background:var(--card)"></iframe>

<h2>5 · Which gain images best</h2>
{data("Oct 22 · #20–#31 at KIGA 2.3, 4.6, 9; #15–#18 at 1.14; 30 s halted holds before each step (19:25–19:35)")}
<div class="card"><div class="scroll"><table>
<tr><th>KIGA</th><th>Outcome</th><th>Halted-hold Z power 100–300 Hz (×1.14)</th><th>Lag share</th><th>Same patch, same direction: error / Z</th></tr>
<tr><td>1.14</td><td>clean</td><td>1×</td><td>0.87–0.94</td><td>no trackable structure</td></tr>
<tr><td>2.3</td><td>clean</td><td>4.5×</td><td>0.88–0.91</td><td>0.31–0.40 / 0.26–0.33</td></tr>
<tr><td>4.6</td><td>clean, last stable</td><td>19×</td><td><b>0.79–0.84</b></td><td><b>0.49–0.54 / 0.46–0.62</b></td></tr>
<tr><td>9</td><td>oscillated, aborted</td><td>20×</td><td>0.85–0.86</td><td>— (one cycle)</td></tr>
</table></div>
<p><b>Why 2.3 looks smoother yet 4.6 is recommended.</b> A slower loop smooths the image, and 88–91% of the 2.3 image is the loop's own lag pattern: smooth and mirror-symmetric between trace and retrace. 4.6 follows more of the surface: less lag, and the same patch repeats better. The loop simulator agrees (Z follows the true surface 0.27 vs 0.12). The cost is roughness from the 158.7 Hz resonance, which takes over at 9. Judge gain by repeatability on the same patch. The default stays at KIGA 3.07 until a good tip confirms 4.6.</p></div>
{fig("gain.png", "Registered averages per gain",
     f"<b>Every gain shows the same features at the same place in the sample frame: the morphology belongs to the sample.</b> Line-by-line registered averages per gain, −error (top) and −Z (bottom), peaks bright; right column: all 10 sweeps. Grey: not scanned at that gain. {LOOK} the bright ridge through the green circle at 2.3, 4.6 and 9; the hollow inside the circle is clearest at 2.3 and fades by 9.")}

<h2>6 · Tracking the drift live</h2>
{data("Oct 22 #22–#31 replayed as if live (#20→#22 is the first same-direction pair)")}
<div class="card"><ul>
<li><b>Bands as they arrive:</b> each sweep is registered in bands of 96 lines (~9 s) against the previous same-direction sweep; ~90 ms per update (worst 280 ms) for both channels. Processing is not the limit.</li>
<li><b>Lock:</b> after the first lock, 2 of 3 bands lock; velocity 0.51 px/s up the frame, matching the whole-sweep fit. The bottom band never locks because the sample moves up: those rows are new territory.</li>
<li><b>Holding the patch (simulation):</b> an alpha-beta estimator with continuous feed-forward, seeded at the first lock, holds the patch to ~0.7 nm; a per-sweep step correction holds ~3 nm with 3× larger jumps; uncorrected it wanders ~13 nm (roadmap G-ST2).</li>
</ul></div>
{fig("live_trail.gif", "Live drift trail beside the frame",
     f"<b>The live tracker recovers the drift of the feature you first used as a bearing.</b> Left: the frame-drift trail (orange = locked, grey = coasting; fading arrows = last 8 updates). Right, same moment: the whole frame (−error, peaks bright) with the circle carried by the drift model (green), the contour inside it (cyan) and the band used for this update (white). {LOOK} the circle climbs the frame while the trail heads up at the same rate.", 860)}

<h2>7 · Open questions</h2>
{data("Oct 22, whole session")}
<div class="card q"><ul>
<li><b>Q1 · Dark in the error image (resolved).</b> Stored error is log(setpoint) − log|current|: its darkest value is the most current, a high point. v1 showed it as stored; v2 shows −error, so high is bright. About 2% of pixels are false specks where an exact-zero ADC reading was repainted as clipped.</li>
<li><b>Q2 · Is the hollow pressed in by the tip?</b> Leading explanation; settle it with the footprint test (Section 8).</li>
<li><b>Q3 · The scan-time ADC offset.</b> With no current the ADC reads −50 to −64 while scanning (−15 idle). Through abs() the loop reads that as ~55 counts of current, a third of the setpoint, and the hollow's centre is exactly that value. Fix planned (roadmap F4); until then keep the setpoint at or above ~200 pA.</li>
<li><b>Q4 · Z drift vs loop balance.</b> The loop's Z ramp (14–49 codes/s) is the loop's action, not a direct measurement of sample drift; separating them needs the full loop model.</li>
</ul></div>

<h2>8 · Next tests</h2>
<div class="card"><ul>
<li><b>Footprint test:</b> scan a small window for a few minutes, then zoom out 2–3×. A changed square where the tip worked means the tip reshapes the surface (Q2).</li>
<li><b>Setpoint steps as a slice selector:</b> at fixed KIGA, scan the same feature at 250, 500 and 1000 pA. Each doubling moves the visible ~0.38 nm height band by ~0.3 Å, so the outline's change per step maps the shape in calibrated height. Not below ~200 pA until the offset fix.</li>
<li><b>Stop clipping:</b> lower the setpoint (≥ 200 pA) or the bias so the top of a feature stays inside the ADC range; clipping hides the top and may be what reshapes it.</li>
<li><b>New tip, then repeat KIGA 2.3 → 4.6</b> with feedback engaged before scanning (Run now asks for the mode) and use registered repeat ≥ 0.7 as the acceptance check.</li>
<li><b>Drift-registered replay mode</b> (Section 2's method in the viewer) and stage tracking in monitor mode first.</li>
</ul></div>

<h2>Method</h2>
<div class="card" style="font-size:13px">Images from the replay loader (<code>sweep_player.DayData.image</code>); missing rows filled from the nearest row; each line levelled (offset and slope); 2–98% clip; Gaussian σ = 1 px. Folded S = mean of levelled trace and retrace Z. Display: −error, −S. Registration: per-line times from the frame records; drift model from v1 (<code>model_metrics.json</code>: 0.561 px/s, 8.38 px up/down, −3.61 px per gain change vertically; 0.026 px/s, −0.75 px, 5.27 px sideways); linear interpolation along rows, sub-pixel sideways shift. Hollow test: rim 14–26 px, centre ≤ 8 px around the darkest point inside the circle in the #21–#23 registered average; normalised by the sweep's standard deviation; control = 400 random places ≥ 40 px away. ADC from error: exact inverse via the firmware log table (setpoint 160 counts = 500 pA). Scripts: <code>v2_core.py</code>, <code>v2_figs.py</code>, <code>adc_22.py</code>, <code>live_trail_frame_v2.py</code>, <code>build_v2.py</code> (archived in <code>software/pc/qtpanda/analysis/oct22/</code>).</div>
"""

page = f"""<title>Oct 22 Report v2</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;600;700&family=JetBrains+Mono:wght@400&display=swap">
<style>{CSS}</style>
<main>
{body}
<section id="roadmap">
<h2>Roadmap: goals, milestones and next steps</h2>
{rmain}
</section>
</main>
<script>{rscript}</script>
"""
open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(page)
t = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", page, flags=re.S)
t = re.sub(r"<h1[^>]*>", "\n# ", t); t = re.sub(r"<h2[^>]*>", "\n## ", t); t = re.sub(r"<h3[^>]*>", "\n### ", t)
t = re.sub(r"<tr[^>]*>", "\n| ", t); t = re.sub(r"</t[dh]>", " | ", t)
t = re.sub(r"<li[^>]*>", "\n- ", t); t = re.sub(r"<(p|div|figcaption|br)[^>]*>", "\n", t)
t = re.sub(r'<img[^>]*src="([^"]*)"[^>]*>', r"[figure: \1]", t)
t = html.unescape(re.sub(r"<[^>]+>", "", t)); t = re.sub(r"\n\s*\n\s*\n+", "\n\n", t)
open(os.path.join(OUT, "REPORT-TEXT.md"), "w", encoding="utf-8").write(
    "<!-- Plain-text extract of the published Oct 22 report v2 (index.html in this folder). Regenerated by build_v2.py. -->\n" + t)
tot = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(OUT) for f in fs)
print("index", os.path.getsize(os.path.join(OUT, "index.html")) // 1000, "kB | mound", os.path.getsize(os.path.join(OUT, "mound.html")) // 1000,
      "kB | total", tot // 1000, "kB |", sorted(os.listdir(FIGS)))
