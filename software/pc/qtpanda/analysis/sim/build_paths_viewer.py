"""Local viewer for the scan-path simulation: scan_paths_viewer.html (self-contained).
Per truth and technique: truth, drift-registered reconstruction, raw reconstruction, difference,
coverage, and the commanded path (animated); a sortable score table with a 1..N count column;
the validation gate and the back-test summary.  Peaks bright, valleys dark."""
import os, io, json, base64, html
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(HERE, "compare_paths.json")))
I = np.load(os.path.join(HERE, "compare_paths_imgs.npz"))
BT = json.load(open(os.path.join(HERE, "backtest_diag.json")))
BS = json.load(open(os.path.join(HERE, "backtest_sep24.json")))
PD = json.load(open(os.path.join(HERE, "phantom_direction.json")))


def png(a, cmap="inferno", lo_hi=None, w=3.0):
    fig, ax = plt.subplots(figsize=(w, w)); ax.set_axis_off(); fig.subplots_adjust(0, 0, 1, 1)
    f = a[np.isfinite(a)]
    lo, hi = lo_hi if lo_hi else (np.percentile(f, [1, 99]) if f.size else (0, 1))
    ax.imshow(np.ma.masked_invalid(a), cmap=cmap, vmin=lo, vmax=hi, interpolation="nearest")
    ax.set_facecolor("#bbb")
    b = io.BytesIO(); fig.savefig(b, format="png", dpi=86); plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()


def plane(a):
    m = np.isfinite(a); yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]]
    A = np.c_[yy[m], xx[m], np.ones(m.sum())]; c, *_ = np.linalg.lstsq(A, a[m], rcond=None)
    return a - (c[0] * yy + c[1] * xx + c[2])


data = {}
for key, r in R.items():
    tn, tk = key.split("/")
    truth = plane(I[f"{key}/truth"]); rec = plane(I[f"{key}/recon"]); raw = plane(I[f"{key}/raw"])
    m = np.isfinite(rec)
    k = np.polyfit(rec[m], truth[m], 1); diff = np.where(m, truth - np.polyval(k, rec), np.nan)
    lt = np.percentile(truth[np.isfinite(truth)], [1, 99])
    cnt = I[f"{key}/cnt"]
    paths = []
    for k_ in range(4):
        if f"{key}/path_x{k_}" not in I: break
        px, py = I[f"{key}/path_x{k_}"], I[f"{key}/path_y{k_}"]
        st = max(1, len(px) // 4000)
        paths.append([np.round(px[::st], 3).tolist(), np.round(py[::st], 3).tolist()])
    frames_img = [png(np.polyval(k, plane(I[f"{key}/recon_f{k_}"])), lo_hi=tuple(lt)) for k_ in range(4) if f"{key}/recon_f{k_}" in I]
    data[key] = dict(truth=tn, key=tk, label=r["label"], frames=r["frames"], seconds=round(r["seconds"], 1),
                     reg=r["registered"], xy=r["xy_only"], raw=r["raw"],
                     img=dict(truth=png(truth, lo_hi=tuple(lt)), rec=png(np.polyval(k, rec), lo_hi=tuple(lt)),
                              raw=png(raw), diff=png(diff, "RdBu_r", (-np.nanpercentile(np.abs(diff), 99), np.nanpercentile(np.abs(diff), 99))),
                              cov=png(np.where(cnt > 0, np.log10(np.maximum(cnt, 1)), np.nan), "viridis")),
                     paths=paths, frames_img=frames_img)

val = {tn: bool(np.array_equal(np.nan_to_num(I[f"{tn}/raster/recon"]), np.nan_to_num(I[f"{tn}/custom_raster/recon"])))
       for tn in {k.split("/")[0] for k in R}}

page = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Scan Path Simulator</title><style>
:root{--bg:#f6f6f3;--fg:#1c1d1f;--mut:#5d6166;--line:#d8d6cf;--card:#fff;--acc:#b4531a;--ok:#1d7a3a;--bad:#a12a2a}
@media (prefers-color-scheme:dark){:root{--bg:#141518;--fg:#e7e6e3;--mut:#a3a3a3;--line:#33353a;--card:#1d1f23;--acc:#f0a46a;--ok:#6fd08f;--bad:#f08080}}
body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.5 system-ui,"Segoe UI",sans-serif}
main{max-width:1320px;margin:0 auto;padding:20px 16px 60px} h1{font-size:22px;margin:0 0 4px} h2{font-size:16px;margin:26px 0 8px}
.mut{color:var(--mut);font-size:12.5px} .card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px 14px;margin:10px 0}
.row{display:flex;gap:6px;flex-wrap:wrap;margin:6px 0} button{font:inherit;font-size:12.5px;padding:4px 9px;border:1px solid var(--line);border-radius:6px;background:transparent;color:var(--fg);cursor:pointer}
button.on{border-color:var(--acc);color:var(--acc);font-weight:600}
.panels{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:8px} .panels figure{margin:0} .panels img,.panels canvas{width:100%;border-radius:4px;border:1px solid var(--line);display:block;background:#fff}
.panels figcaption{font-size:11.5px;color:var(--mut)} @media (max-width:900px){.panels{grid-template-columns:repeat(2,minmax(0,1fr))}}
table{border-collapse:collapse;width:100%;font-size:12.5px;font-variant-numeric:tabular-nums} td,th{border-bottom:1px solid var(--line);padding:3px 6px;text-align:left} th{cursor:pointer;white-space:nowrap}
tr.sel td{background:rgba(180,83,26,.12)} .ok{color:var(--ok);font-weight:600} .bad{color:var(--bad);font-weight:600} .scroll{overflow-x:auto}
</style></head><body><main>
<h1>Scan paths: simulated, reconstructed and scored</h1>
<div class="mut">qt-panda · generated 2026-10-23 · peaks bright, valleys dark · local file (analysis/sim/scan_paths_viewer.html)</div>
<div class="card"><b>Read this first.</b> Every path is generated tick by tick, bit-exact with the firmware arithmetic (scan_paths.py). Each run then goes through the modelled piezo (5% Prandtl–Ishlinskii hysteresis, 158.7 Hz resonance, 3 kHz amplifier), the measured X-Y stage drift (66 pm/s up the frame) and Z drift (0.39 Å/s), the tunnelling current and preamp, and the firmware feedback loop at Oct-22-like settings (19 ticks per bin, KIGA 4.6, 500 pA). The result is rebuilt from Z plus the measured current (combined height), with the preamp filter undone, at the piezo's actual positions, with both drifts removed; the commanded-position score is shown alongside. Full method: docs/SIMULATION.md. <b>Equal time:</b> single paths 49.8 s, pairs 99.6 s. <b>Caveat:</b> the back-test (bottom) shows the simulator does not reproduce the dominant real line artefact (a scan-synchronous trace/retrace dome, OI-18), so imaging scores are relative under the modelled physics and understate what cross-hatch removes. Kinematic scores (coverage, holes, drive near 158.7 Hz, acceleration) are exact.<br><br><b>Truths.</b> (1) <b>Sep 24 #1808, error channel</b> (operator's pick: good tip, gold terraces and step edges), converted to height with the error's own physics (h = −error / (log-table scale × 2κ)). That reading gives terrace steps of ~0.5–1 Å instead of gold's 2.35 Å, because the loop already followed part of each step, so the heights are a lower bound (×~2.6 would match 2.35 Å). The 14 nm scan window sits at the centre of the 27.1 nm image. (2) <b>Synthetic</b>: step, 0.288 nm lattice patch, mounds, an Oct-22-like hollow.</div>
<div class="card" style="border-left:4px solid var(--acc)"><b>What this run says (2026-10-23, final reconstruction).</b><ol>
<li><b>The truth is recreated.</b> With every physical effect switched on and the piezo's actual positions known, the default raster recreates Sep 24 #1808 at <b>0.995</b> and the synthetic surface at <b>0.991</b>; the custom-file copy of the raster gives the identical result (your validation gate). Every other path also reaches ≥ 0.99, except the rose on the synthetic surface (0.943, coverage gaps).</li>
<li><b>What made the difference:</b> rebuilding from Z <i>plus the current</i> (height = tip height − gap from the current) instead of Z alone; undoing the known preamp filter; dropping ticks where the current was lost or clipped; interpolating where samples are dense. The old Z-only method gives 0.78 on the same data.</li>
<li><b>The biggest real-world lever is the piezo calibration:</b> placing samples at the <i>commanded</i> positions gives 0.79 on #1808. That figure assumes 5% hysteresis, which our Sep 24 constant-height data suggest is too large; measuring it is roadmap HY1 (offline, next).</li>
<li><b>Path choice no longer decides accuracy</b> (all ~0.99). It decides smoothness (curved paths: ~100× less drive near 158.7 Hz, 6–60× lower acceleration), streaks, coverage (loops, spokes and rose leave 13–27% unvisited) and drift sensing.</li>
<li><b>Caveats:</b> heights are a stated scale (#1808 from the error channel: a lower bound); the simulator still under-produces the Sep 24 lag dome (OI-18), which does not affect the combined reconstruction; preamp bandwidth is assumed (400 Hz) until measured (CN5).</li>
</ol></div>
<div class="card"><b>Validation gate (your test):</b> the same raster expressed as a custom path file gives an identical reconstruction: VALGATE</div>
<h2>Technique</h2>
<div class="row" id="truthBtns"></div><div class="row" id="techBtns"></div>
<div class="card" id="stats"></div>
<div class="panels">
<figure><img id="iTruth"><figcaption>Truth at the reference time (sample frame)</figcaption></figure>
<figure><img id="iRec"><figcaption>Rebuilt: Z + current, preamp undone, drifts registered, piezo calibrated (same colour scale)</figcaption></figure>
<figure><img id="iRaw"><figcaption>Old method for comparison: Z alone, commanded positions</figcaption></figure>
<figure><img id="iDiff"><figcaption>Truth − rebuilt (red: rebuilt too low)</figcaption></figure>
<figure><img id="iCov"><figcaption>Coverage: log10 hits per pixel (grey: never visited)</figcaption></figure>
<figure><canvas id="cPath" width="400" height="400"></canvas><figcaption id="pathCap">Commanded path, animated</figcaption></figure>
</div>
<div class="panels" id="framePanels" style="margin-top:8px"></div>
<h2>Scores (click a header to sort; click a row to view)</h2>
<div class="scroll"><table id="tbl"><thead><tr><th>#</th><th data-k="key">ID</th><th data-k="label">Technique</th><th data-k="seconds">Time (s)</th>
<th data-k="corr">Corr with truth ▾</th><th data-k="rmse">RMSE (Å)</th><th data-k="cmd">Corr, piezo not calibrated</th><th data-k="raw">Corr, old method (Z only)</th><th data-k="aniso">Residual anisotropy</th>
<th data-k="cov">Coverage</th><th data-k="hole">Largest hole (nm)</th><th data-k="cv">Hit CV</th><th data-k="drive">Drive 100–300 Hz</th><th data-k="acc">Peak acc. (µm/s²)</th></tr></thead><tbody></tbody></table></div>
<div class="mut">Corr: Pearson on the inscribed disc after plane removal. Residual anisotropy: row-to-row ÷ column-to-column gradient energy of (truth − rebuilt); 1 = no line streaks. Drive 100–300 Hz: share of the commanded motion's power near the 158.7 Hz resonance. Peak acceleration: 99.9th percentile of the commanded path.</div>
<h2>Verification ladder: is the truth recreated when the physics is known?</h2>
<div class="card">LADDER</div>
<h2>Back-test: does the simulator reproduce the good-tip day?</h2>
<div class="card">BACKTEST</div>
</main><script>
const D = DATA;
const truths = [...new Set(Object.values(D).map(d => d.truth))];
let tSel = truths[0], kSel = 'raster', key = 'corr', dir = -1, anim = null;
const fmt = (v, p = 3) => (v === null || v === undefined || Number.isNaN(v)) ? '—' : (Math.abs(v) >= 1e4 || (Math.abs(v) < 1e-2 && v !== 0) ? v.toExponential(1) : v.toFixed(p));
function btn(host, label, on, fn) { const b = document.createElement('button'); b.textContent = label; if (on) b.className = 'on'; b.onclick = fn; host.appendChild(b); }
function drawBtns() {
  const tb = document.getElementById('truthBtns'); tb.innerHTML = '<span class="mut" style="align-self:center">Truth:</span>';
  truths.forEach(t => btn(tb, t === 'sep24err' ? 'Sep 24 #1808 error channel (good tip)' : 'Synthetic: step, lattice, mounds, hollow', t === tSel, () => { tSel = t; show(); }));
  const kb = document.getElementById('techBtns'); kb.innerHTML = '<span class="mut" style="align-self:center">Technique:</span>';
  Object.values(D).filter(d => d.truth === tSel).forEach(d => btn(kb, d.label, d.key === kSel, () => { kSel = d.key; show(); }));
}
function rows() { return Object.values(D).filter(d => d.truth === tSel).map(d => ({ d, key: d.key, label: d.label, seconds: d.seconds, corr: d.reg.corr, rmse: d.reg.rmse_A, cmd: d.xy.corr, raw: d.raw.corr, aniso: d.reg.resid_aniso, cov: d.reg.coverage, hole: d.reg.largest_hole_nm, cv: d.reg.hit_cv, drive: d.reg.drive_100_300Hz, acc: d.reg.peak_acc_um_s2 })); }
function table() {
  const rs = rows(); rs.sort((a, b) => (a[key] > b[key] ? 1 : a[key] < b[key] ? -1 : 0) * dir);
  document.querySelector('#tbl tbody').innerHTML = rs.map((r, i) => `<tr class="${r.key === kSel ? 'sel' : ''}" data-k="${r.key}"><td>${i + 1}</td><td>${r.key}</td><td>${r.label}</td><td>${r.seconds}</td><td><b>${fmt(r.corr)}</b></td><td>${fmt(r.rmse, 2)}</td><td>${fmt(r.cmd)}</td><td>${fmt(r.raw)}</td><td>${fmt(r.aniso, 2)}</td><td>${fmt(r.cov)}</td><td>${fmt(r.hole, 2)}</td><td>${fmt(r.cv, 2)}</td><td>${fmt(r.drive)}</td><td>${fmt(r.acc, 0)}</td></tr>`).join('');
  document.querySelectorAll('#tbl tbody tr').forEach(tr => tr.onclick = () => { kSel = tr.dataset.k; show(); });
}
document.querySelectorAll('#tbl th[data-k]').forEach(th => th.onclick = () => { const k = th.dataset.k; dir = k === key ? -dir : (['corr', 'raw', 'cov'].includes(k) ? -1 : 1); key = k;
  document.querySelectorAll('#tbl th').forEach(t => t.textContent = t.textContent.replace(/ [▾▴]$/, '')); th.textContent += dir < 0 ? ' ▾' : ' ▴'; table(); });
const PCOL = ['#b4531a', '#1f6fd1', '#2a9d4b', '#8e44ad'];
function path(d) {
  // every frame's commanded path, drawn one after another (pairs: frame 1 orange, frame 2 blue)
  const c = document.getElementById('cPath'), g = c.getContext('2d');
  const all = d.paths.flatMap(p => p[0].concat(p[1]).map(Math.abs));
  const m = Math.max(...all) * 1.05 || 1, sc = v => (v / m * 0.5 + 0.5) * c.width;
  if (anim) cancelAnimationFrame(anim);
  g.fillStyle = '#fff'; g.fillRect(0, 0, c.width, c.height); g.strokeStyle = '#ccc'; g.strokeRect(sc(-7), sc(-7), sc(7) - sc(-7), sc(7) - sc(-7));
  g.lineWidth = 0.6; let f = 0, i = 1;
  document.getElementById('pathCap').textContent = d.paths.length > 1
    ? `Commanded paths of all ${d.paths.length} frames, animated in order: frame 1 orange (X fast), frame 2 blue (Y fast)`
    : 'Commanded path, animated';
  (function step() {
    const [xs, ys] = d.paths[f], n = xs.length, j = Math.min(n, i + Math.ceil(n / 200));
    g.strokeStyle = PCOL[f % PCOL.length]; g.globalAlpha = 0.75; g.beginPath(); g.moveTo(sc(xs[i - 1]), sc(ys[i - 1]));
    for (let k = i; k < j; k++) g.lineTo(sc(xs[k]), sc(ys[k])); g.stroke(); i = j;
    if (i >= n) { f++; i = 1; }
    if (f < d.paths.length) anim = requestAnimationFrame(step); else g.globalAlpha = 1;
  })();
  const fp = document.getElementById('framePanels');
  fp.innerHTML = (d.frames_img || []).map((src, k) => `<figure><img src="${src}"><figcaption>Frame ${k + 1} rebuilt on its own (${k === 0 ? 'X fast' : 'Y fast'} for cross-hatch), same colour scale</figcaption></figure>`).join('');
}
function show() {
  const d = Object.values(D).find(x => x.truth === tSel && x.key === kSel) || Object.values(D).find(x => x.truth === tSel);
  kSel = d.key; drawBtns(); table();
  for (const [id, k] of [['iTruth', 'truth'], ['iRec', 'rec'], ['iRaw', 'raw'], ['iDiff', 'diff'], ['iCov', 'cov']]) document.getElementById(id).src = d.img[k];
  document.getElementById('stats').innerHTML = `<b>${d.label}</b> · ${d.frames} frame(s), ${d.seconds} s · corr with truth <b>${fmt(d.reg.corr)}</b> (piezo not calibrated ${fmt(d.xy.corr)}, old Z-only method ${fmt(d.raw.corr)}) · RMSE ${fmt(d.reg.rmse_A, 2)} Å · coverage ${fmt(d.reg.coverage)} · largest hole ${fmt(d.reg.largest_hole_nm, 2)} nm · drive near 158.7 Hz ${fmt(d.reg.drive_100_300Hz)} · tip speed 5–95%: ${d.reg.speed_nm_s_p5_p95.map(v => v.toFixed(0)).join('–')} nm/s`;
  path(d);
}
show();
</script></body></html>"""

bt_rows = "".join(f"<tr><td>{html.escape(k)}</td>" + "".join(f"<td>{v[x]:.3g}</td>" for x in ("L_rms", "L_locked", "S_rms", "raw_span")) + "</tr>"
                  for k, v in BT.items())
rs = BS["real_summary"]["real"]
bt = (f"<p>Real Sep 24 #1586–#1599 vs simulated raster at the same settings (line-levelled Z, Z units). Real median: lag share {rs['lag_share'][1]:.2f}, trace/retrace correlation {rs['trace_retrace_corr'][1]:.2f}.</p>"
      "<div class='scroll'><table><tr><th>Run</th><th>L rms</th><th>L line-locked share</th><th>S rms</th><th>Raw span</th></tr>" + bt_rows + "</table></div>"
      f"<p>The real L is a smooth symmetric dome, the same on every line (OI-18). The simulator reproduces the tilt (raw span) but not this dome. The no-current ADC offset does not flip with scan direction: trace {PD['Oct 22 #20-#31']['trace_median']:.0f} vs retrace {PD['Oct 22 #20-#31']['retrace_median']:.0f} counts, so it is not X-drive pickup.</p>")
vg = " · ".join(f"{t}: " + ("<span class='ok'>identical</span>" if v else "<span class='bad'>DIFFERENT</span>") for t, v in sorted(val.items()))
LD = json.load(open(os.path.join(HERE, "ladder.json")))
LF = json.load(open(os.path.join(HERE, "ladder_fixes.json")))
lay = ["L0", "L1", "L2", "L3", "L4", "L4u", "L5", "L5a", "L6", "L7"]
names = {"L0": "geometry only", "L1": "+ feedback loop, ideal electronics", "L2": "+ ADC noise", "L3": "+ preamp 400 Hz",
         "L4": "+ phantom offset, zero substitution (offset known)", "L4u": "  same, offset unknown",
         "L5": "+ lateral piezo, commanded positions", "L5a": "  same, actual positions known", "L6": "+ X-Y stage drift, registered", "L7": "+ Z drift, removed (all physics)"}
techs = ["raster", "raster15", "crosshatch", "spiral_fast"]
def cell(tn, tk, l):
    r = LD[tn].get(f"{tk}/{l}")
    if r is None: return "<td>—</td>"
    if l == "L0": return f"<td><b>{r['geometry']['corr']:.4f}</b></td>"
    return f"<td><b>{r['combined']['corr']:.4f}</b> <span class='mut'>(Z only {r['z_only']['corr']:.3f})</span></td>"
lad = ("<p>Each layer adds one physical effect. Each is rebuilt from the <b>combined estimate</b> (height = tip height − gap from the current measured on every tick); Z alone is shown in brackets. "
       "Correlation with the truth on the inscribed disc.</p>")
for tn, tl in (("sep24err", "Sep 24 #1808 error channel"), ("synthetic", "Synthetic")):
    lad += f"<h3>{tl}</h3><div class='scroll'><table><tr><th>#</th><th>Layer</th>" + "".join(f"<th>{t}</th>" for t in techs) + "</tr>"
    lad += "".join(f"<tr><td>{i + 1}</td><td>{l} {names[l]}</td>" + "".join(cell(tn, t, l) for t in techs) + "</tr>" for i, l in enumerate(lay)) + "</table></div>"
lad += ("<h3>The two reconstruction fixes (Sep 24 #1808)</h3><div class='scroll'><table><tr><th>#</th><th>Case</th><th>Raster, binned</th><th>Raster, interpolated</th><th>Spiral, binned</th><th>Spiral, interpolated</th></tr>"
        + "".join(f"<tr><td>{i + 1}</td><td>{c}</td><td>{LF['raster/' + c]['bin']:.4f}</td><td>{LF['raster/' + c]['interp']:.4f}</td><td>{LF['spiral_fast/' + c]['bin']:.4f}</td><td>{LF['spiral_fast/' + c]['interp']:.4f}</td></tr>"
                  for i, c in enumerate([k.split('/', 1)[1] for k in LF if k.startswith('raster/')])) + "</table></div>"
        "<p><b>Reading it.</b> (1) Where the physics is known the rebuild is exact: geometry and the feedback loop reach 0.999 for the raster and the cross-hatch, and the combined estimate loses nothing. Z alone does (0.89). "
        "(2) Undoing the known preamp filter (19-tick average) restores 0.996; tick-by-tick inversion amplifies noise. "
        "(3) The lateral piezo costs 15–20 points unless the actual tip positions are known; with them, full physics reaches <b>0.993 (raster) and 0.995 (spiral)</b>. That part is a calibration task (hysteresis, resonance), not an algorithm limit. "
        "(4) The spiral's geometry-only 0.98 is sampling: #1808 has pixel-scale speckle below the sampling limit (the Oct 15 report's 5–6 px per atom). Softening the truth by 0.7 px gives 0.998, 1 px gives 1.000.</p>")
page = page.replace("LADDER", lad)
page = page.replace("DATA", json.dumps(data)).replace("VALGATE", vg).replace("BACKTEST", bt)
out = os.path.join(HERE, "scan_paths_viewer.html")
open(out, "w", encoding="utf-8").write(page)
print(out, os.path.getsize(out) // 1000, "kB; validation", val)
