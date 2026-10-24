"""Patch (template) tracking between consecutive sweeps, 2026-Oct-22 #12-#31.

For each pair (prev N, next N+1): cut a grid of 48x48 templates from N+1,
search each over the whole of N with normalized cross-correlation (NCC).
Null: the same template searched in N flipped in both axes (same texture
statistics, no spatial correspondence) and in a Sep 24 sweep.
A rigid stage shift shows as many templates agreeing on one displacement
with peaks well above the null.  Outputs metrics JSON + figures.
"""
import os, json, datetime as dt
os.environ["QT_QPA_PLATFORM"] = "offscreen"
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "morph_report.py"), encoding="utf-8").read().split("SW = [i for i")[0]
ns = {"__file__": os.path.join(HERE, "morph_report.py")}; exec(compile(src, "h", "exec"), ns)
np, D, sp, plt = ns["np"], ns["D"], ns["sp"], ns["plt"]
from scipy.ndimage import gaussian_filter
from scipy.signal import fftconvolve
import matplotlib.patches as mpatches

OUT = os.path.join(HERE, "morph_report")
PS, STRIDE, SIG = 48, 26, 2.0
RUNG = {}
for i in (12, 13, 14): RUNG[i] = "tip check 1.14"
for i in range(15, 20): RUNG[i] = "1.14"
for i in range(20, 25): RUNG[i] = "2.3"
for i in range(25, 30): RUNG[i] = "4.6"
for i in range(30, 33): RUNG[i] = "9"


def prep_err(Dd, i):
    a = ns["rowlev"](ns["fill_rows"](Dd.image(i, "e_trace")[0]))
    a = np.clip(a, *np.percentile(a, [2, 98]))
    return gaussian_filter(a, SIG)


def prep_S(Dd, i):
    zt = ns["fill_rows"](Dd.image(i, "z_trace")[0]); zr = ns["fill_rows"](Dd.image(i, "z_retrace")[0])
    S = (ns["rowlev"](zt) + ns["rowlev"](zr)) / 2
    S = np.clip(S, *np.percentile(S, [2, 98]))
    return gaussian_filter(S, SIG)


def ncc_map(img, tpl):
    """valid-mode normalized cross-correlation map (like skimage match_template)."""
    t = tpl - tpl.mean(); tn = np.sqrt((t * t).sum())
    num = fftconvolve(img, t[::-1, ::-1], mode="valid")
    ones = np.ones_like(tpl)
    s1 = fftconvolve(img, ones, mode="valid"); s2 = fftconvolve(img * img, ones, mode="valid")
    n = tpl.size
    var = np.clip(s2 - s1 * s1 / n, 1e-12, None)
    return num / (np.sqrt(var) * tn + 1e-12)


def track(prev, nxt, null_imgs):
    H, W = nxt.shape
    out = []
    for y in range(0, H - PS + 1, STRIDE):
        for x in range(0, W - PS + 1, STRIDE):
            tpl = nxt[y:y + PS, x:x + PS]
            if tpl.std() < 0.35 * nxt.std():        # featureless patch: skip
                continue
            m = ncc_map(prev, tpl)
            py, px = np.unravel_index(np.argmax(m), m.shape)
            nulls = [float(ncc_map(z, tpl).max()) for z in null_imgs]
            out.append(dict(y=y, x=x, py=int(py), px=int(px), dy=int(py - y), dx=int(px - x),
                            peak=float(m[py, px]), null=max(nulls)))
    return out


def consensus(recs, tol=4):
    """Most-supported displacement (dy, dx) and the fraction of patches within tol px."""
    if not recs: return None
    best = None
    for r in recs:
        sup = [q for q in recs if abs(q["dy"] - r["dy"]) <= tol and abs(q["dx"] - r["dx"]) <= tol]
        if best is None or len(sup) > len(best):
            best = sup
    dy = float(np.median([q["dy"] for q in best])); dx = float(np.median([q["dx"] for q in best]))
    agree = [q for q in recs if abs(q["dy"] - dy) <= tol and abs(q["dx"] - dx) <= tol]
    return dict(dy=dy, dx=dx, frac=len(agree) / len(recs), n=len(recs), n_agree=len(agree),
                peak_agree=float(np.median([q["peak"] for q in agree])),
                null_med=float(np.median([q["null"] for q in recs])),
                null_p95=float(np.percentile([q["null"] for q in recs], 95)),
                beat_null=float(np.mean([q["peak"] > q["null"] for q in agree])) if agree else 0.0)


SW = [i for i in range(12, 32) if D.sweeps[i][2]["lines"] >= 250]
DS = sp.DayData("2026-Sep-24")
NULL_SEP = prep_err(DS, 1806)

res = {"err": [], "S": []}
store = {}
for chan, prep in (("err", prep_err), ("S", prep_S)):
    imgs = {i: prep(D, i) for i in SW}
    store[chan] = imgs
    for a, b in zip(SW, SW[1:]):
        nulls = [imgs[a][::-1, ::-1], NULL_SEP if chan == "err" else prep_S(DS, 1806)]
        recs = track(imgs[a], imgs[b], nulls)
        c = consensus(recs)
        # shear check: displacement of agreeing patches vs row
        agree = [q for q in recs if c and abs(q["dy"] - c["dy"]) <= 4 and abs(q["dx"] - c["dx"]) <= 4]
        if len(agree) >= 4:
            rows = np.array([q["y"] + PS / 2 for q in agree]); dys = np.array([q["dy"] for q in agree], float)
            slope = float(np.polyfit(rows, dys, 1)[0]) if np.ptp(rows) > 50 else None
        else:
            slope = None
        res[chan].append(dict(a=a, b=b, ga=RUNG[a], gb=RUNG[b],
                              dir_a=D.sweeps[a][2]["dir"], dir_b=D.sweeps[b][2]["dir"],
                              dt=D.sweeps[b][2]["t_start"] - D.sweeps[a][2]["t_start"],
                              shear_px_per_row=slope, **(c or {}), recs=recs))
        r = res[chan][-1]
        print(f"{chan:3} #{a}->#{b} ({r['ga']}->{r['gb']}) shift dy {r.get('dy',0):+5.1f} dx {r.get('dx',0):+5.1f} "
              f"agree {r.get('n_agree',0)}/{r.get('n',0)} ({r.get('frac',0):.0%}) peak {r.get('peak_agree',0):.2f} "
              f"null med {r.get('null_med',0):.2f} p95 {r.get('null_p95',0):.2f} beat {r.get('beat_null',0):.0%} "
              f"shear {slope if slope is None else round(slope,3)}")

# ---- drift track (chain consensus shifts where the pair is trustworthy)
def trusted(r): return r.get("frac", 0) >= 0.4 and r.get("n_agree", 0) >= 6 and r.get("beat_null", 0) >= 0.8
track_pts = []
pos = np.array([0.0, 0.0]); t0 = D.sweeps[SW[0]][2]["t_start"]
track_pts.append((SW[0], 0.0, 0.0, 0.0, True))
for r in res["err"]:
    ok = trusted(r)
    if ok: pos = pos + np.array([r["dy"], r["dx"]])
    track_pts.append((r["b"], D.sweeps[r["b"]][2]["t_start"] - t0, pos[0], pos[1], ok))

# ---- drift-corrected image-to-image matrix (err), using best NCC of a central crop
def best_shift_corr(A, B, crop=160):
    """Search the central crop of B anywhere in A; return peak NCC and shift."""
    H, W = B.shape; y0 = (H - crop) // 2; x0 = (W - crop) // 2
    m = ncc_map(A, B[y0:y0 + crop, x0:x0 + crop])
    py, px = np.unravel_index(np.argmax(m), m.shape)
    return float(m[py, px]), int(py - y0), int(px - x0)

mat = {}
for chan in ("err", "S"):
    imgs = store[chan]
    M = np.zeros((len(SW), len(SW))); Z = np.zeros_like(M)
    for ii, a in enumerate(SW):
        for jj, b in enumerate(SW):
            if ii == jj: M[ii, jj] = 1; continue
            M[ii, jj], _, _ = best_shift_corr(imgs[a], imgs[b])
            Z[ii, jj] = best_shift_corr(imgs[a][::-1, ::-1], imgs[b])[0]   # null: flipped
    mat[chan] = (M, Z)

# ---------------------------------------------------------------- figures
def show(ax, a, title=None):
    lo, hi = np.percentile(a, [1, 99]); ax.imshow(a, cmap="inferno", vmin=lo, vmax=hi, interpolation="nearest")
    ax.set_xticks([]); ax.set_yticks([])
    if title: ax.set_title(title, fontsize=8)

# Fig P1: inset proof for selected pairs
picks = [(27, 28), (28, 30), (21, 22), (23, 25), (13, 15)]
fig, axes = plt.subplots(len(picks), 5, figsize=(15, 3.1 * len(picks)),
                         gridspec_kw=dict(width_ratios=[1, 1, 0.55, 0.55, 1]))
for row, (a, b) in enumerate(picks):
    r = next(q for q in res["err"] if q["a"] == a and q["b"] == b)
    A, B = store["err"][a], store["err"][b]
    agree = [q for q in r["recs"] if abs(q["dy"] - r["dy"]) <= 4 and abs(q["dx"] - r["dx"]) <= 4]
    pool = agree if agree else r["recs"]
    q = max(pool, key=lambda z: z["peak"])        # strongest supporting template
    show(axes[row, 0], B, f"#{b} (next, KIGA {RUNG[b]}): template")
    axes[row, 0].add_patch(mpatches.Rectangle((q["x"], q["y"]), PS, PS, fill=False, ec="cyan", lw=2))
    show(axes[row, 1], A, f"#{a} (prior, KIGA {RUNG[a]}): best match")
    axes[row, 1].add_patch(mpatches.Rectangle((q["px"], q["py"]), PS, PS, fill=False, ec="cyan", lw=2))
    axes[row, 1].add_patch(mpatches.Rectangle((q["x"], q["y"]), PS, PS, fill=False, ec="white", lw=1, ls="--"))
    show(axes[row, 2], B[q["y"]:q["y"] + PS, q["x"]:q["x"] + PS], "template (zoom)")
    show(axes[row, 3], A[q["py"]:q["py"] + PS, q["px"]:q["px"] + PS], f"found in #{a} (zoom)")
    m = ncc_map(A, B[q["y"]:q["y"] + PS, q["x"]:q["x"] + PS])
    axes[row, 4].imshow(m, cmap="viridis", vmin=-0.4, vmax=1)
    axes[row, 4].plot(q["px"], q["py"], "r+", ms=14, mew=2)
    axes[row, 4].set_xticks([]); axes[row, 4].set_yticks([])
    axes[row, 4].set_title(f"NCC map: peak {q['peak']:.2f}, null {q['null']:.2f}\n"
                           f"pair consensus dy {r['dy']:+.0f}, dx {r['dx']:+.0f} px; "
                           f"{r['n_agree']}/{r['n']} templates agree", fontsize=8)
plt.tight_layout(pad=0.4); fig.savefig(os.path.join(OUT, "figP1_insets.png"), dpi=80); plt.close(fig)

# Fig P2: per-patch displacement vectors for every pair (err)
n = len(res["err"]); cols = 5; rows_ = (n + cols - 1) // cols
fig, axes = plt.subplots(rows_, cols, figsize=(3.0 * cols, 3.1 * rows_))
for k, r in enumerate(res["err"]):
    ax = axes.flat[k]
    show(ax, store["err"][r["b"]])
    for q in r["recs"]:
        ok = abs(q["dy"] - r["dy"]) <= 4 and abs(q["dx"] - r["dx"]) <= 4
        cx, cy = q["x"] + PS / 2, q["y"] + PS / 2
        ax.annotate("", xy=(cx + q["dx"], cy + q["dy"]), xytext=(cx, cy),
                    arrowprops=dict(arrowstyle="->", color="cyan" if ok else "red", lw=1.3 if ok else 0.8))
    ax.set_title(f"#{r['a']}→#{r['b']} ({r['ga']}→{r['gb']})  {r['n_agree']}/{r['n']} agree\n"
                 f"shift dy {r['dy']:+.0f} dx {r['dx']:+.0f} · {'TRUSTED' if trusted(r) else 'no lock'}", fontsize=7)
for k in range(n, rows_ * cols): axes.flat[k].axis("off")
plt.tight_layout(pad=0.3); fig.savefig(os.path.join(OUT, "figP2_vectors.png"), dpi=80); plt.close(fig)

# Fig P3: drift track + agreement vs null
fig, ax = plt.subplots(1, 2, figsize=(12, 3.6))
tt = [p[1] for p in track_pts]
ax[0].plot(tt, [p[2] for p in track_pts], "o-", label="dy (rows)")
ax[0].plot(tt, [p[3] for p in track_pts], "s-", label="dx (columns)")
for p in track_pts:
    if not p[4]: ax[0].plot(p[1], p[2], "x", color="red", ms=10)
    ax[0].annotate(f"#{p[0]}", (p[1], p[2]), fontsize=6, xytext=(2, 4), textcoords="offset points")
ax[0].set_xlabel("s since #12"); ax[0].set_ylabel("cumulative shift (px, 0.117 nm/px)")
ax[0].set_title("Stage drift from trusted pairs (red x = no lock, shift not added)", fontsize=9); ax[0].legend(fontsize=7)
lab = [f"{r['a']}→{r['b']}" for r in res["err"]]
ax[1].bar(np.arange(n) - 0.2, [r.get("peak_agree", 0) for r in res["err"]], 0.4, label="agreeing templates: median NCC")
ax[1].bar(np.arange(n) + 0.2, [r.get("null_p95", 0) for r in res["err"]], 0.4, label="null (no correspondence): 95th pct")
ax[1].plot(np.arange(n), [r.get("frac", 0) for r in res["err"]], "k.-", label="fraction of templates agreeing")
ax[1].set_xticks(np.arange(n)); ax[1].set_xticklabels(lab, rotation=60, fontsize=7); ax[1].set_ylim(0, 1)
ax[1].legend(fontsize=7); ax[1].set_title("Match strength vs chance", fontsize=9)
plt.tight_layout(); fig.savefig(os.path.join(OUT, "figP3_drift.png"), dpi=95); plt.close(fig)

# Fig P4: drift-tolerant similarity matrix
fig, ax = plt.subplots(1, 3, figsize=(15, 4.6))
labels = [f"#{i} {RUNG[i]}" for i in SW]
for k, (chan, ttl) in enumerate((("err", "error channel"), ("S", "Z folded S"))):
    M, Z = mat[chan]
    im = ax[k].imshow(M, cmap="magma", vmin=0, vmax=1)
    ax[k].set_xticks(range(len(SW))); ax[k].set_xticklabels(labels, rotation=90, fontsize=6)
    ax[k].set_yticks(range(len(SW))); ax[k].set_yticklabels(labels, fontsize=6)
    ax[k].set_title(f"{ttl}: best NCC of central 160 px of column sweep\nanywhere in row sweep (shift-tolerant)", fontsize=8)
    for j in range(len(SW)):
        for i2 in range(len(SW)):
            if i2 != j: ax[k].text(j, i2, f"{M[i2, j]:.2f}", ha="center", va="center", fontsize=4.5,
                                   color="w" if M[i2, j] < 0.6 else "k")
plt.colorbar(im, ax=ax[1], fraction=0.046)
M, Z = mat["err"]
same, cross, nulls = [], [], []
for ii, a in enumerate(SW):
    for jj, b in enumerate(SW):
        if ii == jj: continue
        (same if RUNG[a] == RUNG[b] else cross).append(M[ii, jj]); nulls.append(Z[ii, jj])
ax[2].hist(nulls, bins=30, range=(0, 1), alpha=0.6, label="null (flipped)", color="#888")
ax[2].hist(cross, bins=30, range=(0, 1), alpha=0.6, label="different gain step", color="#d62728")
ax[2].hist(same, bins=30, range=(0, 1), alpha=0.6, label="same gain step", color="#1f77b4")
ax[2].legend(fontsize=7); ax[2].set_title("error channel: pair similarity distributions", fontsize=8)
plt.tight_layout(); fig.savefig(os.path.join(OUT, "figP4_matrix.png"), dpi=90); plt.close(fig)

summary = {
    "pairs": {ch: [{k: v for k, v in r.items() if k != "recs"} for r in res[ch]] for ch in res},
    "track": [dict(sweep=p[0], t=p[1], dy=p[2], dx=p[3], trusted=p[4]) for p in track_pts],
    "matrix_err_same_med": float(np.median(same)), "matrix_err_cross_med": float(np.median(cross)),
    "matrix_err_null_med": float(np.median(nulls)), "matrix_err_null_p95": float(np.percentile(nulls, 95)),
    "matrix_S": {"same_med": None},
}
MS, ZS = mat["S"]
sS, cS, nS = [], [], []
for ii, a in enumerate(SW):
    for jj, b in enumerate(SW):
        if ii == jj: continue
        (sS if RUNG[a] == RUNG[b] else cS).append(MS[ii, jj]); nS.append(ZS[ii, jj])
summary["matrix_S"] = dict(same_med=float(np.median(sS)), cross_med=float(np.median(cS)),
                           null_med=float(np.median(nS)), null_p95=float(np.percentile(nS, 95)))
json.dump(summary, open(os.path.join(OUT, "patch_metrics.json"), "w"), indent=1, default=float)
print("track", [(p[0], round(p[2], 1), round(p[3], 1), p[4]) for p in track_pts])
print("err matrix: same-step median %.2f, cross-step %.2f, null median %.2f p95 %.2f" %
      (summary["matrix_err_same_med"], summary["matrix_err_cross_med"], summary["matrix_err_null_med"], summary["matrix_err_null_p95"]))
print("S matrix:", summary["matrix_S"])
