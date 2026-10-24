"""Report revision for first-time readers (operator feedback 2026-10-23), applied to
build_morph_html.py: orientation section, per-section data lines, linear order
(D -> C -> K -> F -> Q -> first pass), self-contained captions, 2.3 vs 4.6 explanation,
autocorrelation figure removed, C4 reminder strip, first-pass relevance note.
Every replacement must match exactly once."""
import os, re
HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, "build_morph_html.py")
s = open(P, encoding="utf-8").read()
assert "REVISION v3" not in s, "already applied"


def once(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:80])
    s = s.replace(old, new)


def cap(fig, text):
    """Replace the caption of the figure whose image is img('fig')."""
    global s
    pat = re.compile(r"(img\('" + re.escape(fig) + r"'\)\}\"[^>]*>\s*<figcaption>).*?(</figcaption>)", re.S)
    assert len(pat.findall(s)) == 1, fig
    s = pat.sub(lambda m: m.group(1) + text + m.group(2), s)


LOOK = "<i>Look at:</i>"

# ---------------------------------------------------------------- CSS for data lines
once(".scroll{overflow-x:auto} code{font-size:13px}",
     ".scroll{overflow-x:auto} code{font-size:13px}\n"
     ".data{font-size:13px;color:var(--mut);margin:-2px 0 10px;padding:3px 8px;border-left:3px solid var(--line)}")

# ---------------------------------------------------------------- orientation (new section 0)
ORIENT = """<h2>0 · Start here: the instrument, the day, and how to read this report</h2>
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
"""
once('<div class="card verdict"><b>Revised verdict', ORIENT + '<div class="card verdict"><b>Revised verdict')
once("Sections 1–6 below are that first pass, kept for the record.</div>",
     "That first pass is kept near the end, with a note on what still applies.</div>")

# drop the old table of contents and the old colours card (both now in section 0)
s = re.sub(r"<!--MERGE-TOC-START-->.*?<!--MERGE-TOC-END-->\n", "", s, count=1, flags=re.S)
s, n = re.subn(r'<div class="card" style="border-left:4px solid var\(--acc\)"><b>How to read the colours in this report\.</b>.*?</div>\n', "", s, count=1, flags=re.S)
assert n == 1

# ---------------------------------------------------------------- captions: D
cap("figD1_inset_proof.png",
    "<b>A piece of one sweep can be found again in the previous sweep, slightly shifted: consecutive images share real content that moves.</b> "
    "Each row tests one pair of sweeps. Column 1: a 96 × 96 px rectangle (cyan) cut from the later sweep. Column 2: where a search found it in the earlier sweep "
    "(cyan; dashed white = same position, i.e. no movement; small arrow = the shift). Columns 3–4: the two patches enlarged side by side. Column 5: the match score at every "
    "position of the earlier sweep (red + = best). Column 6: the same search in an unrelated frame (the null). Top row: Sep 24 good-tip control, score 0.97 against 0.30 in the null. "
    "Oct 22 rows: 0.67–0.79 against 0.28–0.42, in both channels and across a gain change. "
    f"{LOOK} columns 3 and 4 look alike; column 5 has one clear peak where column 6 has none; the arrows point up the frame, as the drift model predicts.")
cap("figD2_vectors.png",
    "<b>From #20 on, all templates in a pair move together; before #20 they do not, so #12–#18 have no trackable structure.</b> "
    "Each panel is one pair of consecutive sweeps (error channel). Each arrow runs from a template's position in the later sweep to where it was found in the earlier one. "
    "Cyan: agrees with the pair's consensus shift within 5 px; red: disagrees. Panel titles give the consensus shift in the error and Z channels. "
    f"{LOOK} the share of cyan arrows and whether they are parallel. Many parallel arrows mean the whole field moved; scattered red arrows mean nothing locked.")
cap("figD3_track_chain.png",
    "<b>The measured shifts add up the way real motion does, so they are not chance matches.</b> "
    "Left: the feature's displacement since #20 from the fitted drift model (lines), with the 13 cross-checked measured shifts as arrows. Right: chain test. "
    "For three consecutive sweeps A, B, C, the shift A→C measured directly is plotted against A→B plus B→C; real motion lands on the diagonal. "
    f"{LOOK} on the left, the steady climb (drift up the frame) and the zig-zag (the up/down-sweep offset); on the right, #20–#31 on the diagonal (misses 3–9 px) and #12–#18 far off it (24–179 px).")
cap("figD4_model_test.png",
    "<b>The drift model predicts where the surface will be without any search: the structure is on the sample and moves with it.</b> "
    "For every pair in #20–#31, the correlation between the two sweeps when aligned only by the model's predicted shift (blue), left fixed in the frame (orange), shifted by a random "
    "amount of the same size (grey, 95th percentile of 50 tries), or compared with a flipped frame (red), against the time between the sweeps. "
    f"{LOOK} blue above orange and red everywhere and mostly above grey. A loop artefact is fixed to the scan and would favour orange. "
    "Blue falls with time (0.4–0.6 at 25 s, 0.1–0.3 at 250 s): the structure is real but slowly changes.")
cap("figD5_corrected_stack.png",
    "<b>Averaging ten sweeps sharpens the image only when the drift is corrected. The middle panel is this report's reference view of the patch.</b> "
    "All panels in #20's coordinates. Left: #20 alone. Middle: #20–#31 mapped with the drift model (steady drift, up/down-sweep offset, gain-change jumps) and averaged. "
    "Right: the same 10 sweeps averaged without correction. "
    f"{LOOK} the diagonal band and the structure around it stay sharp in the middle and smear on the right. "
    "Limit: each sweep gets one shift, but the drift continues during the 25 s sweep (~14 px top to bottom), so features near the top or bottom edge can be off by up to ~7 px.")

# ---------------------------------------------------------------- captions: K, F
cap("figK1_maps.png",
    "<b>Every gain shows the same features at the same place on the sample: the morphology belongs to the sample, not to the loop.</b> "
    "All sweeps mapped into #20's coordinates and averaged per gain: error channel on top, Z folded S below. The right column stitches all 10 sweeps, covering ~30 × 45 nm "
    "of sample from a 30 nm window because the sample drifted through it. Grey: not scanned at that gain. Green: the circled feature of Section C. Colours as stored "
    "(error: dark = high point; Z: bright = low point). "
    f"{LOOK} the long diagonal ridge through the green circle, present at 2.3, 4.6 and 9. 2.3 renders it smoothest, 4.6 with the most detail, 9 noisiest (see “Why 2.3 looks prettier” above).")
cap("figK2_driftpath.png",
    "<b>The sample drifted steadily, about 67 pm/s almost straight up the frame.</b> "
    "The circled feature's position against time (left) and its path within the frame (right): 19.8 nm up and 2.1 nm left in 300 s. "
    f"{LOOK} the straight overall trend with no sudden jumps; the zig-zag is the ~1 nm up/down-sweep offset and the two small sideways jogs are the gain changes. "
    "At this rate a feature crosses the whole 30 nm window in about 7 minutes, which is why stage tracking (F2, roadmap G-ST) matters.")
cap("fiducial_drift_2026-Oct-22_20-31.png",
    "<b>The automatic tool recovers the drift without being told where to look.</b> "
    "Oct 22 #20–#31, one panel per sweep. Coloured square: the example reference fiducial and where it was found; the next template cut from it is also marked. "
    "The reference is followed from #22 through #23, #25 and #26, then hops (colour change) at #27 to a nearby fiducial and continues to #28. "
    f"{LOOK} the square stays on the same piece of surface while that surface moves up the frame, and a hop replaces the reference without breaking the chain. "
    "Result (table above): 0.52 px/s, against 0.56 px/s from the hand-built analysis.")
cap("fiducial_drift_2026-Sep-24_1586-1599.png",
    "<b>The same tool on a good-tip day: a tighter fit and slower drift.</b> "
    "Sep 24 #1586–#1599 (24.8 nm window). The reference follows the up sweeps #1586 → #1588 → #1590 → #1592, the chain breaks once, and a new reference covers #1594 → #1596 → #1598. "
    f"{LOOK} how sharp and repeatable the features are with a good tip: the standard Oct 22 should reach after a tip change. Fit residual 1.5 / 2.5 px here against 6.0 / 2.2 px on Oct 22.")

once('<figure><!--LIVETRAIL--><figcaption>Frame-drift trail: the lead point (orange when locked, grey when coasting on the last velocity) and the last 8 updates as fading arrows; title gives the current speed and direction. Drift is drawn as the feature\'s motion within the frame (up = up the frame).</figcaption></figure>',
     '<figure><!--LIVETRAIL--><figcaption><b>Drift can be tracked live from bands of lines as they arrive, at ~90 ms of computing per update.</b> '
     'Oct 22 #22–#31 replayed as if live, one frame per band update (600 ms per frame). Left: the frame-drift trail. The lead point is orange when the band locked and grey when '
     'coasting on the last velocity; fading arrows are the last 8 updates; the title gives speed and direction. Drift is drawn as the feature\'s motion within the frame (up = up the frame). '
     'Right, at the same moment: the whole error frame being registered, with the operator\'s circle carried by the hand-built drift model (green dashed, Section D), the contour found '
     'inside it (cyan: the bright opening inside the dark structure, the default reading of the 3D mound in C5) and the 96-row band used for this update (white dashed). '
     f'{LOOK} the circle and contour climb the frame with the feature while the trail on the left heads up at the same rate: the live tracker, which never sees the circle, '
     'recovers the motion of the feature the operator first used as a bearing. The bottom band never locks because the sample moves up: those rows are new territory.</figcaption></figure>')

# ---------------------------------------------------------------- captions and edits: C
cap("figC0_fullframes.png",
    "<b>The circled dot opens into a ring, a loop and an arch (“A”) at the same spot on the sample.</b> "
    "Full 30 nm frames, error channel, Oct 22 #20–#27 (KIGA 2.3 and 4.6). Solid green: the operator's circle in #20. Dashed green: the same sample spot carried forward by the drift model. "
    f"{LOOK} the shape inside the circle: dot (#20), ring (#21), loop (#22), arch (#23); in #25 and #27 the circle sits on the A's left leg. "
    "The circle climbs the frame with the drift yet stays on the feature, so the “A” forms where the dot was.")
cap("figC1_blob_crops.png",
    "<b>On the same patch of sample, the feature's darkest, clipped core shrinks smoothly within KIGA 2.3 and an outline replaces the solid blob.</b> "
    "The same 14 × 14 nm sample patch in every sweep from #18 to #31, located with the drift model; error channel on top, Z folded S below. Cyan square: the fixed 9 × 9 nm analysis "
    "window; dashed: its 4 × 4 nm centre. Titles: share of the window clipped at the current limit. White: outside the scanned frame (in #18 only 60% of the window is in frame). "
    f"{LOOK} the clipped area from #20 to #23 and the outline that remains; the Z row shows the same patch with weaker contrast.")
cap("figC2_blob_metrics.png",
    "<b>The clipped share falls smoothly from 34% to 12% at KIGA 2.3, holds at 4.6 and drops at 9; Z shows no usable trend.</b> "
    "All three panels use the same fixed 9 × 9 nm sample window carried by the drift model, with no outline-finding. Left: share of pixels at exactly the clip value "
    "(ADC 32767, above ~102 nA). Middle: share in the darkest 20% of that sweep's error values. Right: Z in the 4 × 4 nm centre minus the whole window. Blue ▲, orange ▼. "
    f"{LOOK} the smooth fall within KIGA 2.3, a gradual process rather than a tip jump, and the Z panel flipping sign between ▲ and ▼, which is lag, not height.")
cap("figC4_stack_dark.png",
    "<b>Read as a contour map, the outlines stack into an elongated ridge with the circled dot near its summit.</b> "
    "Oct 22 #20–#30: each sweep's dark outline mapped into #20's coordinates. Left: the outlines over the #20 image (purple = smallest, yellow = largest). Middle-left: stacked "
    "height = the number of outlines enclosing each point (contour steps, not nm). Middle-right: the implied mound, smoothed. Right: outline areas from summit to base, with the "
    "share of each outline inside the next larger one (red). "
    f"{LOOK} the ridge running lower left to upper right, and the red nesting values (43–77%, against 21–37% by chance): the outlines partly nest, as contour lines should, but not perfectly.")

# C3 autocorrelation figure removed; the double-tip conclusion stays as one sentence
s, n = re.subn(r"<figure><img src=\"\{img\('figC3_autocorr\.png'\)\}\".*?</figure>\n", "", s, count=1, flags=re.S)
assert n == 1
once("which would draw an “A” from a single edge. The image autocorrelation (Figure C3) shows no fixed-offset secondary peak across sweeps; its off-centre peaks fall at 23–71 px along the diagonal of the bands, which is what elongated diagonal features produce.",
     "which could draw an “A” from a single edge. An image autocorrelation check found no repeat at a fixed offset across sweeps, which rules out a double tip.")

# C4: reminder of the frames below the 3D-form figure
once("""share of each outline inside the next larger one (red). <i>Look at:</i> the ridge running lower left to upper right, and the red nesting values (43–77%, against 21–37% by chance): the outlines partly nest, as contour lines should, but not perfectly.</figcaption></figure>""",
     """share of each outline inside the next larger one (red). <i>Look at:</i> the ridge running lower left to upper right, and the red nesting values (43–77%, against 21–37% by chance): the outlines partly nest, as contour lines should, but not perfectly.</figcaption></figure>
<figure><img src="{img('figC0_fullframes.png')}" alt="Reminder: the full frames the outlines come from">
<figcaption><b>Reminder: what the frames behind these outlines look like.</b> Repeated from the start of Section C: #20 with the operator's circle (solid green) and the same sample spot carried into #21–#27 (dashed). The ridge in the stack above is the long dark diagonal running through the circle; the outlines are the dark shapes inside and around it.</figcaption></figure>""")
once("Interactive 3D version: <code>MOUND-3D-2026-10-22.html</code> in this folder.", "Interactive 3D version: Section C5.")
once("Both readings are switchable in <code>MOUND-3D-2026-10-22.html</code>.", "Both readings are switchable in the 3D mound (C5).")

# ---------------------------------------------------------------- K: why 2.3 looks prettier
once(" Standalone extract: <code>KIGA-SWEEP-2026-10-22.html</code>.", "")
once("<li>The running default was left at KIGA 3.07 (⅔ of 4.6) until a good tip confirms 4.6.</li>\n</ul></div>",
     """<li>The running default was left at KIGA 3.07 (⅔ of 4.6) until a good tip confirms 4.6.</li>
</ul></div>
<div class="card verdict"><p><b>Why KIGA 2.3 looks smoother and more symmetric than 4.6, yet 4.6 is recommended.</b></p><ul>
<li><b>A slower loop smooths the image.</b> At 2.3 the loop reacts more slowly, so Z changes gently along each line. That filters out noise and real fine detail alike, and the image looks clean.</li>
<li><b>Most of what the 2.3 image shows is the loop itself.</b> 88–91% of it is the direction-flip (lag) pattern: a large, smooth swing that trace and retrace draw as mirror images (first-pass Section 6 shows the profiles). Smooth and symmetric is what lag looks like, not what this surface looks like.</li>
<li><b>4.6 follows more of the real surface, plus more noise.</b> The lag share drops to 79–84%, and the same patch repeats better between sweeps (error 0.49–0.54, Z 0.46–0.62, against 0.31–0.40 and 0.26–0.33 at 2.3). Repeatable detail is surface; that is the test that matters. The cost is visible roughness: the 158.7 Hz Z resonance is ~19× stronger in the halted hold at 4.6 than at 1.14 (4.5× at 2.3), and it ripples into the image.</li>
<li><b>The loop simulator agrees.</b> Replaying today's firmware loop over a known synthetic surface, Z follows the true surface about twice as well at 4.6 as at 2.3 (correlation 0.27 against 0.12).</li>
<li><b>So judge a gain by repeatability on the same patch, not by how smooth one image looks.</b> KIGA 9 shows where the trade-off ends: the resonance takes over and the loop oscillates. With this damaged tip the margin is modest, so the default stays at 3.07 until a good tip confirms 4.6.</li>
</ul></div>""")

# ---------------------------------------------------------------- reorder: C before K and F
c0 = s.index("<h2>C · Case study")
c1 = s.index("<!--MOUND3D-->\n") + len("<!--MOUND3D-->\n")
cblock = s[c0:c1]; s = s[:c0] + s[c1:]
k0 = s.index("<!--MERGE-KF-START-->")
s = s[:k0] + cblock + s[k0:]

# ---------------------------------------------------------------- first pass: what still applies
once('<h2 style="margin-top:46px">First pass (superseded where noted above)</h2>',
     """<h2 style="margin-top:46px">First pass (superseded where noted above)</h2>
<p class="data"><b>Data:</b> Oct 22 #12–#32 (tip check, KIGA 1.14 → 9) and Sep 24 good-tip controls · analysed before the drift was measured</p>
<div class="card q"><p><b>What still applies from this first pass.</b> It compared whole frames without correcting for drift. Some of it stands and is used above; some is superseded.</p><ul>
<li><b>Still valid:</b> the folded-S method (trace + retrace cancels lag) and the split into surface and lag (Sections 2 and 6); the finding that similarity between raw images is mostly lag; the Sep 24 good-tip baseline (repeat ~0.9) as the acceptance target; the dark diagonal band persisting within each gain step (4b); the lag profile changing with gain (6), which explains why images seem to jump at each gain change and why 2.3 looks smooth (K); and the next steps in 7, with the repeat test now done after drift correction.</li>
<li><b>Superseded:</b> “no persistent morphology” (1, 4, 5): drift moves the sample ~25 px per Y-cycle and whole-frame alignment could not follow it (Section D). The whole-frame shifts in 3 are not a drift measurement; Section D measures 0.56 px/s. “The pattern resets at each gain change” (4b, 5): with drift corrected, the same morphology survives every gain change (D6, K).</li>
</ul></div>""")

# ---------------------------------------------------------------- captions: first pass
cap("fig0_control.png",
    "<b>The repeat test works on a good tip; on Oct 22, without drift correction, it finds almost nothing.</b> "
    "Folded surface estimate S of two consecutive same-direction sweeps, the second aligned onto the first by whole-frame search, and their difference. "
    "Top: Sep 24 (good tip): features line up and cancel in the difference (repeat 0.91). Middle and bottom: Oct 22, the best pair (KIGA 4.6, 0.27) and a typical one (KIGA 2.3, 0.09). "
    f"{LOOK} the nearly empty Sep 24 difference against the Oct 22 differences full of row streaks. "
    "Partly superseded: drift defeated the whole-frame alignment; aligned by the drift model, Oct 22 pairs repeat at 0.4–0.6 (Section D).")
cap("fig3_persistence.png",
    "<b>In uncorrected images, what repeats is the loop's lag pattern, not the surface.</b> "
    "Each point compares a sweep with the previous sweep of the same direction, after whole-frame alignment. Blue: folded S, the surface estimate. Green: S with the average row removed. "
    "Grey: trace only, rows levelled. Red: the part that flips with scan direction (lag). "
    f"{LOOK} grey moves with red, not with blue: raw-trace similarity comes from lag. Still valid; the low blue values are superseded by Section D's drift-corrected 0.4–0.6.")
cap("fig2_drift.png",
    "<b>Whole-frame alignment returned random shifts: there was nothing to lock onto at full-frame scale, so this is not a drift measurement.</b> "
    "Left: shift of each sweep against the first sweep of its direction, from phase correlation. Right: S correlation after that alignment. "
    f"{LOOK} shifts jumping 30–80 px with no trend and correlations near zero; on Sep 24 the same method gives small, consistent shifts. "
    "Superseded: local templates (Section D) do measure the drift, 0.56 px/s up the frame.")
cap("fig1_variants.png",
    "<b>Without drift correction, no processing choice makes a feature persist from sweep to sweep.</b> "
    "Each row is one sweep and each column one processing: plane only; each row's offset and slope removed; median of row differences; folded S; S with the average row removed; "
    "error channel. Each panel has its own 1–99% stretch. "
    f"{LOOK} whether any feature can be followed down a column. Useful as a guide to what each processing does; the conclusion is superseded, because the sample moves about 3 px per sweep and ~25 px per Y-cycle.")
cap("err_montage.png",
    "<b>Smoothed error images show a dark diagonal band that recurs in every sweep from #20 to #31.</b> "
    "Error trace, rows levelled, each sweep from #12 to #32 in time order. "
    f"{LOOK} the near-vertical diagonal band at about 55–75% across, in both up and down sweeps. This was the first sign of persistent structure; "
    "it is the dark band through the circled feature of Section C (compare Figure K1).")
cap("fig4_rung_avgs.png",
    "<b>Per-gain averages looked unrelated because the drift was not corrected.</b> "
    "Top: all full sweeps of each gain step aligned by whole-frame search and averaged (folded S). Bottom: the same with the average row removed. "
    "Aligned correlations between steps: −0.18 to 0.21. "
    f"{LOOK} how little the averages resemble each other. Superseded by Figure K1: with drift corrected, the per-gain averages agree (Z 0.40–0.52).")
cap("fig5_profiles.png",
    "<b>The loop's lag draws a large, smooth pattern into every line, and its shape changes with the gain. At low gain this pattern, not the surface, dominates the image.</b> "
    "Each curve is the average of all lines in one sweep (rows levelled), trace in blue (left to right) and retrace in orange (right to left), one panel per gain step. "
    "A real surface feature appears at the same position in trace and retrace; lag pushes the two in opposite directions, so lag shows up as blue and orange curves that mirror each other. "
    f"{LOOK} in every panel the blue and orange curves roughly mirror each other and repeat from sweep to sweep within a step: that is lag (88–91% of the image at 2.3, 79–84% at 4.6; Section K). "
    "Between steps the shape and the position of the hump change, so the image seems to move at each gain change although the sample did not. At 9 the curves turn irregular as the loop oscillates. Still valid.")

# ---------------------------------------------------------------- method pointer
once("in the session scratchpad.</div>", "archived in <code>software/pc/qtpanda/analysis/oct22/</code>.</div>")

# ---------------------------------------------------------------- per-section data lines (applied to the rendered page)
DATA = {
    "D1": "Oct 22 · pairs #21→#22, #23→#25, #27→#28, #30→#31 (KIGA 2.3, 4.6, 9) · control: Sep 24 #1806→#1808 (good tip)",
    "D2": "Oct 22 · every consecutive pair from #12 to #31 (tip check, then KIGA 1.14 → 9) · error and Z channels",
    "D3": "Oct 22 · #12–#31; drift model fitted to 13 cross-checked pairs within #20–#31",
    "D4": "Oct 22 · all pairs within #20–#31 (KIGA 2.3, 4.6, 9)",
    "D5": "Oct 22 · the 10 full sweeps #20–#31, shown in #20's coordinates",
    "D6": "Oct 22 · neighbouring sweeps ≤ 55 s apart within #20–#31",
    "D7": "Conclusions from D1–D6 (Oct 22 #20–#31)",
    "C": "Oct 22 · #18–#31, focus on #20–#23 (KIGA 2.3) · error channel unless noted",
    "C1": "Oct 22 #20–#31 and the status record during the sweep (19:25–19:35)",
    "C2": "Oct 22 #20–#31 · loop Z output 19:21–19:40",
    "C3": "Proposed tests: no data yet",
    "C4": "Oct 22 · 9 outlines, from #20, #21, #22, #23, #25, #26, #27, #28, #30",
    "C5": "Oct 22 · the same 9 sweeps as C4, plus #18 for context",
    "K": "Oct 22 · #20–#31 at KIGA 2.3, 4.6, 9 and #15–#18 at 1.14, each step preceded by a 30 s halted hold (19:25–19:35)",
    "F": "Oct 22 #20–#31 · Sep 24 #1586–#1599 (good tip, 24.8 nm)",
    "F2": "Oct 22 #22–#31 replayed as if live (#20→#22 is the first same-direction pair)",
    "Q": "Oct 22, whole session (18:22–19:52)",
    "1": "Sep 24 good-tip pair · Oct 22 pairs at KIGA 4.6 and 2.3",
    "2": "Oct 22 · same-direction pairs within #12–#31",
    "3": "Oct 22 #12–#31",
    "4": "Oct 22 #12–#31, one row per sweep",
    "4b": "Oct 22 #12–#32",
    "5": "Oct 22 · full sweeps of each gain step, #12–#31",
    "6": "Oct 22 #12–#31, one curve per sweep",
}
once('open(OUT, "w", encoding="utf-8").write(html)',
     "# REVISION v3: per-section data lines\n"
     "import re as _re\n"
     f"DATA = {DATA!r}\n"
     "for _k, _v in DATA.items():\n"
     "    html, _n = _re.subn(r'(<h2>' + _re.escape(_k) + r' ·.*?</h2>)', lambda m: m.group(1) + '\\n<p class=\"data\"><b>Data:</b> ' + _v + '</p>', html, count=1, flags=_re.S)\n"
     "    assert _n == 1, _k\n"
     'open(OUT, "w", encoding="utf-8").write(html)')

open(P, "w", encoding="utf-8").write(s)
print("revised", P)
