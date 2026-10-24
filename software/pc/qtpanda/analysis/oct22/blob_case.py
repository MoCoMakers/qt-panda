"""Case study: the dark blob in #20 (rows ~185-256, cols ~100-170) that turns into an
arch/'A' outline.  Follows the same sample patch through #18-#31 with the drift model,
measures its size/shape in the error channel and its height in Z, and compares its growth
with the whole image's scale change (affine fit of matched templates) and with Z position.
"""
import os, json, datetime as dt
os.environ["QT_QPA_PLATFORM"] = "offscreen"
HERE = os.path.dirname(os.path.abspath(__file__))
MARK = "SW = [i for i in range(12, 32) if D.sweeps"
src = open(os.path.join(HERE, "patch_track.py"), encoding="utf-8").read().split(MARK)[0]
ns = {"__file__": os.path.join(HERE, "patch_track.py")}; exec(compile(src, "pt", "exec"), ns)
np, plt, D = ns["np"], ns["plt"], ns["D"]
from scipy import ndimage as ndi
ns["SIG"] = 1.0
RUNG = ns["RUNG"]
PX_NM = 30.0 / 256
mm = json.load(open(os.path.join(HERE, "morph_report", "model_metrics.json")))
cy = np.array([mm["model_y"]["drift_px_s"], mm["model_y"]["offset_px"], mm["model_y"]["gain_jump_px"]])
cx = np.array([mm["model_x"]["drift_px_s"], mm["model_x"]["offset_px"], mm["model_x"]["gain_jump_px"]])
t = lambda i: D.sweeps[i][2]["t_start"]
h = lambda i: 1 if D.sweeps[i][2]["dir"] == "down" else -1
SEG = [20, 21, 22, 23, 25, 26, 27, 28, 30, 31]
ORDER = [18] + SEG


def nchg(a, b):
    lo, hi = min(t(a), t(b)), max(t(a), t(b))
    return len({RUNG[k] for k in SEG if lo <= t(k) <= hi}) - 1


def shift_from_20(i):
    """content at (y,x) in #20 sits at (y+dy, x+dx) in sweep i."""
    if i == 18:
        return 32.5, 21.0                         # measured #18->#20: content at (y,x) in #20 is at (y+32.5, x+21) in #18
    s = 1 if t(i) >= t(20) else -1
    f = np.array([t(i) - t(20), (h(i) - h(20)) / 2, s * max(nchg(20, i), 0)])
    return -(f @ cy), -(f @ cx)


# sign check: predict(a,b) in drift_model = content at (y,x) in b is at (y+dy) in a.
# Here we want position in i of content at (y,x) in #20 = (y - pred(i,20) ...). Use the pair
# definition directly: pred(20, i) gives content at (y,x) in i found at (y+dy, x+dx) in 20,
# so content at Y in 20 is at Y - dy in i.  shift_from_20 returns -(f@c) with f built for (20 -> i).

C0 = (220, 135)          # blob centre in #20 (row, col)
HALF = 60
IMG = {i: (ns["prep_err"](D, i), ns["prep_S"](D, i)) for i in ORDER}


def crop(a, cyx):
    y, x = int(round(cyx[0])), int(round(cyx[1]))
    out = np.full((2 * HALF, 2 * HALF), np.nan)
    ys, ye, xs, xe = y - HALF, y + HALF, x - HALF, x + HALF
    sy, sx = max(0, ys), max(0, xs); ey, ex = min(a.shape[0], ye), min(a.shape[1], xe)
    out[sy - ys:ey - ys, sx - xs:ex - xs] = a[sy:ey, sx:ex]
    return out


# Z position per sweep from the 200 Hz status CSV
csv = np.genfromtxt(os.path.join(D.folder, "image_stability_1792709026870_s1792709026869.csv"),
                    delimiter=",", skip_header=1)
ct = 1792709026.870 + csv[:, 0]


def zstats(i):
    s = D.sweeps[i][2]; m = (ct >= s["t_start"]) & (ct <= s["t_end"])
    z = csv[m, 4]; a = csv[m, 2]
    return float(np.mean(z)), float(np.max(z) - np.min(z)), float(np.mean(a >= 32000)), float(np.mean(a <= 16))


rows = []
crops = {}
for i in ORDER:
    dy, dx = shift_from_20(i)
    c = (C0[0] + dy, C0[1] + dx)
    E, S = crop(IMG[i][0], c), crop(IMG[i][1], c)
    crops[i] = (E, S, c)
    full = IMG[i][0]
    thr = np.percentile(full, 20)                 # dark = lowest 20% of this sweep's error values
    dark = np.nan_to_num(E, nan=np.inf) < thr
    dark = ndi.binary_opening(dark, iterations=1)
    lab, n = ndi.label(dark)
    # component closest to crop centre
    best, bd = None, 1e9
    for k in range(1, n + 1):
        yy, xx = np.nonzero(lab == k)
        if len(yy) < 30: continue
        d = np.min(np.hypot(yy - HALF, xx - HALF))
        if d < bd: bd, best = d, k
    rec = dict(sweep=i, kiga=RUNG[i], dir=D.sweeps[i][2]["dir"], t=t(i), time=dt.datetime.fromtimestamp(t(i)).strftime("%H:%M:%S"),
               centre_row=c[0], centre_col=c[1], lines=D.sweeps[i][2]["lines"])
    if best is not None and bd < 25:
        comp = lab == best
        filled = ndi.binary_fill_holes(comp)
        holes = int(ndi.label(filled & ~comp)[1])
        yy, xx = np.nonzero(comp)
        hull_area = filled.sum()
        rec.update(area_px=int(comp.sum()), area_nm2=float(comp.sum() * PX_NM ** 2), filled_px=int(hull_area),
                   enclosed_frac=float((filled & ~comp).sum() / hull_area), holes=holes,
                   height_px=int(np.ptp(yy) + 1), width_px=int(np.ptp(xx) + 1))
        # Z inside the filled outline vs a 6 px ring outside it
        ring = ndi.binary_dilation(filled, iterations=6) & ~filled
        if np.isfinite(S[filled]).any() and np.isfinite(S[ring]).any():
            rec["z_in_minus_ring"] = float(np.nanmean(S[filled]) - np.nanmean(S[ring]))
        crops[i] = (E, S, c, comp)
    else:
        rec.update(area_px=0)
    rec["z_mean"], rec["z_span"], rec["sat_frac"], rec["lost_frac"] = zstats(i)
    rows.append(rec)
    print({k: (round(v, 2) if isinstance(v, float) else v) for k, v in rec.items() if k not in ("t",)})

# global scale between consecutive sweeps: affine fit to template matches that beat the null
ns["PS"], ns["STRIDE"] = 64, 24
def affine(a, b):
    A_, B_ = IMG[a][0], IMG[b][0]
    recs = ns["track"](A_, B_, [A_[::-1, ::-1]])
    good = [q for q in recs if q["peak"] > q["null"] + 0.08]
    if len(good) < 8: return None
    P = np.array([[q["y"] + 32, q["x"] + 32] for q in good], float)
    Q = np.array([[q["py"] + 32, q["px"] + 32] for q in good], float)
    # robust: iteratively drop outliers
    keep = np.ones(len(P), bool)
    for _ in range(4):
        M = np.c_[P[keep], np.ones(keep.sum())]
        coef, *_ = np.linalg.lstsq(M, Q[keep], rcond=None)
        r = np.linalg.norm(np.c_[P, np.ones(len(P))] @ coef - Q, axis=1)
        keep = r < max(6, np.percentile(r[keep], 70))
    sc_y, sc_x = coef[0, 0], coef[1, 1]
    return dict(n=int(keep.sum()), scale_y=float(sc_y), scale_x=float(sc_x),
                area_scale=float(abs(np.linalg.det(coef[:2, :2]))), resid=float(np.median(r[keep])))
glob = {}
for a, b in zip(SEG, SEG[1:]):
    r = affine(a, b)
    glob[(a, b)] = r
    print(f"global affine #{a}->#{b}: {r}")

json.dump(dict(rows=rows, affine={f"{a}->{b}": v for (a, b), v in glob.items()}),
          open(os.path.join(HERE, "morph_report", "blob_metrics.json"), "w"), indent=1, default=float)

# ---------------- figures
def show(ax, a, title=None, lo=None, hi=None):
    if lo is None: lo, hi = np.nanpercentile(a, [1, 99])
    ax.imshow(a, cmap="inferno", vmin=lo, vmax=hi, interpolation="nearest")
    ax.set_xticks([]); ax.set_yticks([])
    if title: ax.set_title(title, fontsize=8)

n = len(ORDER)
fig, axes = plt.subplots(2, n, figsize=(1.75 * n, 4.3))
for k, i in enumerate(ORDER):
    E, S = crops[i][0], crops[i][1]
    full = IMG[i][0]; lo, hi = np.percentile(full, [1, 99])
    r = next(q for q in rows if q["sweep"] == i)
    note = " (edge)" if i == 18 else ""
    show(axes[0, k], E, f"#{i} {'▲' if r['dir']=='up' else '▼'} K{r['kiga']}{note}\n{r['time']} · {r.get('area_nm2', 0):.0f} nm²", lo, hi)
    if len(crops[i]) == 4:
        axes[0, k].contour(crops[i][3], levels=[0.5], colors="cyan", linewidths=0.8)
    show(axes[1, k], S, f"Z: inside−ring {r.get('z_in_minus_ring', float('nan')):+.0f}")
axes[0, 0].set_ylabel("error", fontsize=8); axes[1, 0].set_ylabel("Z folded S", fontsize=8)
fig.suptitle("Same sample patch (14 × 14 nm), followed with the drift model; cyan = segmented dark region", fontsize=9)
fig.subplots_adjust(left=0.02, right=0.99, top=0.82, bottom=0.02, wspace=0.05, hspace=0.32)
fig.savefig(os.path.join(HERE, "morph_report", "figC1_blob_crops.png"), dpi=95); plt.close(fig)

# metrics plot
fig, ax = plt.subplots(1, 3, figsize=(15, 3.6))
tt = [(q["t"] - t(20)) for q in rows]
area = [q.get("area_nm2", np.nan) for q in rows]
cols = ["#1f77b4" if q["dir"] == "up" else "#ff7f0e" for q in rows]
ax[0].scatter(tt, area, c=cols, s=40)
for q, x_, y_ in zip(rows, tt, area): ax[0].annotate(f"#{q['sweep']} K{q['kiga']}", (x_, y_), fontsize=6, xytext=(2, 3), textcoords="offset points")
ax[0].set_xlabel("s since #20"); ax[0].set_ylabel("dark-region area (nm²)"); ax[0].set_title("Blob area (blue ▲, orange ▼)", fontsize=9)
ax[1].scatter(tt, [q["z_mean"] for q in rows], c=cols, s=40); ax[1].set_xlabel("s since #20"); ax[1].set_ylabel("mean Z DAC during sweep")
ax[1].set_title("Z position (toward sample = higher)", fontsize=9)
pairs = [(a, b) for a, b in zip(SEG, SEG[1:]) if glob[(a, b)]]
ga = np.cumprod([glob[p]["area_scale"] for p in pairs])
tb = [t(b) - t(20) for a, b in pairs]
ax[2].plot([0] + tb, [1] + list(ga), "k.-", label="whole image (affine, cumulative)")
a0 = next(q.get("area_nm2") for q in rows if q["sweep"] == 20)
ax[2].plot(tt, [x / a0 if a0 else np.nan for x in area], "o", color="#d62728", label="blob area / blob area in #20")
ax[2].set_yscale("log"); ax[2].set_xlabel("s since #20"); ax[2].legend(fontsize=7)
ax[2].set_title("Does the blob grow faster than the whole image?", fontsize=9)
plt.tight_layout(); fig.savefig(os.path.join(HERE, "morph_report", "figC2_blob_metrics.png"), dpi=95); plt.close(fig)
print("done")
