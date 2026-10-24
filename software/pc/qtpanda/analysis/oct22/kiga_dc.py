"""KIGA sweep re-analysis with drift compensation as the first pass (2026-Oct-22).

Every sweep #20-#31 is mapped into #20's sample coordinates with the fitted drift model
(steady drift + up/down-sweep offset + small gain-change jumps) on an extended canvas.
Then: per-gain drift-corrected averages and a stitched sample map; repeatability on the
same patch; cross-gain similarity; streak anisotropy; loop statistics; hold spectra.
"""
import os, json, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "blob_case.py"), encoding="utf-8").read().split("\nrows = []")[0]
g = {"__file__": os.path.join(HERE, "blob_case.py")}; exec(compile(src, "bc", "exec"), g)
np, plt, D = g["np"], g["plt"], g["D"]
inner = g["ns"]["ns"]
from scipy import ndimage as ndi
import matplotlib.patches as mpatches
OUT = os.path.join(HERE, "morph_report")
PX = 30.0 / 256
RUNG = g["RUNG"]
SEQ = [20, 21, 22, 23, 25, 26, 27, 28, 30, 31]
GAINS = ["2.3", "4.6", "9"]
Y0, Y1, X0, X1 = -40, 440, -40, 300          # canvas in #20 pixel coordinates


def zs(a):
    a = a - np.nanmean(a); return a / (np.nanstd(a) + 1e-12)


def to_canvas(img, i):
    """canvas(y,x) = img(y+dy, x+dx) where content at (y,x) in #20 sits at (y+dy, x+dx) in sweep i."""
    dy, dx = g["shift_from_20"](i); iy, ix = int(round(dy)), int(round(dx))
    out = np.full((Y1 - Y0, X1 - X0), np.nan)
    H, W = img.shape
    for_y = np.arange(Y0, Y1); for_x = np.arange(X0, X1)
    sy = for_y + iy; sx = for_x + ix
    vy = (sy >= 0) & (sy < H); vx = (sx >= 0) & (sx < W)
    out[np.ix_(vy, vx)] = img[np.ix_(sy[vy], sx[vx])]
    return out


CAN = {"err": {}, "S": {}}
for i in SEQ:
    E, S = g["IMG"][i]
    CAN["err"][i] = to_canvas(zs(E), i); CAN["S"][i] = to_canvas(zs(S), i)


def ocorr(A, B, min_px=4000):
    m = np.isfinite(A) & np.isfinite(B)
    if m.sum() < min_px: return np.nan, int(m.sum())
    a, b = A[m] - A[m].mean(), B[m] - B[m].mean()
    return float((a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum())), int(m.sum())


direction = lambda i: D.sweeps[i][2]["dir"]
res = {"pairs": [], "gain": {}}
# repeatability on the same patch: consecutive sweeps, same direction and opposite direction
for ch in ("err", "S"):
    for a in SEQ:
        for b in SEQ:
            if b <= a: continue
            same = direction(a) == direction(b)
            nxt_same = [k for k in SEQ if k > a and direction(k) == direction(a)]
            nxt_any = [k for k in SEQ if k > a]
            if not ((same and nxt_same and b == nxt_same[0]) or (b == nxt_any[0])): continue
            c, n = ocorr(CAN[ch][a], CAN[ch][b])
            res["pairs"].append(dict(ch=ch, a=a, b=b, kind="same direction" if same else "up/down", ga=RUNG[a], gb=RUNG[b],
                                     corr=c, overlap_nm2=n * PX ** 2))

# per-gain averages on the canvas
AVG = {ch: {} for ch in ("err", "S")}
for ch in ("err", "S"):
    for gn in GAINS:
        mem = [i for i in SEQ if RUNG[i] == gn]
        st = np.array([CAN[ch][i] for i in mem]); n = np.sum(np.isfinite(st), 0)
        av = np.nanmean(st, 0); av[n < max(2, len(mem) // 2)] = np.nan
        AVG[ch][gn] = av
cross = {}
for ch in ("err", "S"):
    for a in GAINS:
        for b in GAINS:
            if a < b or a == b: continue
    for a, b in (("2.3", "4.6"), ("4.6", "9"), ("2.3", "9")):
        c, n = ocorr(AVG[ch][a], AVG[ch][b], 2000)
        # null: same comparison with one map flipped (keeps texture, destroys correspondence)
        cn, _ = ocorr(AVG[ch][a], AVG[ch][b][::-1, ::-1], 2000)
        cross[f"{ch} {a}|{b}"] = dict(corr=c, null=cn, overlap_nm2=n * PX ** 2)

# streak anisotropy: row-to-row vs column-to-column gradient energy (unsmoothed, row-levelled)
def aniso(img):
    a = inner["rowlev"](inner["fill_rows"](img))
    gy = np.diff(a, axis=0); gx = np.diff(a, axis=1)
    return float(np.mean(gy ** 2) / np.mean(gx ** 2))
for gn in GAINS:
    mem = [i for i in SEQ if RUNG[i] == gn]
    r = dict(sweeps=mem)
    r["streak_aniso_err"] = float(np.median([aniso(D.image(i, "e_trace")[0]) for i in mem]))
    r["streak_aniso_z"] = float(np.median([aniso(D.image(i, "z_trace")[0]) for i in mem]))
    # loop statistics during the scans of this gain
    c = np.genfromtxt(os.path.join(D.folder, "image_stability_1792709026870_s1792709026869.csv"), delimiter=",", skip_header=1) if gn == "2.3" else c
    tt = 1792709026.870 + c[:, 0]
    m = np.zeros(len(tt), bool)
    for i in mem:
        s = D.sweeps[i][2]; m |= (tt >= s["t_start"]) & (tt <= s["t_end"])
    a = c[m, 2]
    r["lost_pct"] = float(100 * np.mean(np.abs(a) <= 30)); r["low_pct"] = float(100 * np.mean(np.abs(a) <= 16))
    r["clip_pct"] = float(100 * np.mean(a >= 32000)); r["adc_median"] = float(np.median(a))
    r["z_rate_codes_s"] = float(np.polyfit(tt[m] - tt[m][0], c[m, 4], 1)[0])
    rp = [p for p in res["pairs"] if p["ga"] == gn and p["gb"] == gn]
    for ch in ("err", "S"):
        for kind in ("same direction", "up/down"):
            v = [p["corr"] for p in rp if p["ch"] == ch and p["kind"] == kind and np.isfinite(p["corr"])]
            r[f"repeat_{ch}_{kind}"] = (float(np.min(v)), float(np.max(v))) if v else None
    res["gain"][gn] = r
la = json.load(open(os.path.join(HERE, "ladder_analysis.json")))["rungs"]
for gn, key in (("2.3", "2.3"), ("4.6", "4.6"), ("9", "9.0")):
    r = la[key]
    res["gain"][gn]["lag_share"] = [im["lag_share"] for im in r.get("images", [])]
    h = r.get("hold") or {}
    res["gain"][gn]["hold_z_100_300"] = h.get("z", {}).get("b100_300")
    res["gain"][gn]["hold_z_peaks"] = h.get("z", {}).get("peaks_100_300(hz,x_median)")
res["gain"]["1.14"] = dict(lag_share=[im["lag_share"] for im in la["1.1444"]["images"]],
                           hold_z_100_300=la["1.1444"]["hold"]["z"]["b100_300"],
                           hold_z_peaks=la["1.1444"]["hold"]["z"]["peaks_100_300(hz,x_median)"])
res["cross_gain"] = cross

# ---------------- figures
def show(ax, a, title, circle=None, lohi=None):
    lo, hi = lohi or np.nanpercentile(a, [1, 99])
    ax.imshow(a, cmap="inferno", vmin=lo, vmax=hi, interpolation="nearest",
              extent=(X0 - 0.5, X1 - 0.5, Y1 - 0.5, Y0 - 0.5))
    ax.set_facecolor("#ddd"); ax.set_xticks([]); ax.set_yticks([]); ax.set_title(title, fontsize=9)
    if circle:
        cy, cx, hr, hc = g["CIRC"] if "CIRC" in g else (220, 135, 36, 35)
        ax.add_patch(mpatches.Ellipse((135, 220), 70, 72, fill=False, ec="#39ff14", lw=1.5))
    ax.set_xlim(X0, X1); ax.set_ylim(Y1, Y0)

# K1: per-gain drift-corrected averages (both channels) + all-sweep stitched map
fig, axes = plt.subplots(2, 4, figsize=(17, 11.5))
for r, ch in enumerate(("err", "S")):
    for k, gn in enumerate(GAINS):
        n = len(res["gain"][gn]["sweeps"])
        show(axes[r, k], AVG[ch][gn], f"{'error' if ch == 'err' else 'Z (folded S)'} · KIGA {gn} · {n} sweeps averaged", circle=True)
    st = np.array([CAN[ch][i] for i in SEQ]); allavg = np.nanmean(st, 0)
    allavg[np.sum(np.isfinite(st), 0) < 2] = np.nan
    show(axes[r, 3], allavg, f"{'error' if ch == 'err' else 'Z'} · all 10 sweeps stitched", circle=True)
for ax in axes.flat:
    ax.plot([X0, X0 + 85.4], [Y1 - 12, Y1 - 12], color="white", lw=3)        # 10 nm bar
    ax.text(X0 + 2, Y1 - 18, "10 nm", color="white", fontsize=8)
fig.suptitle("Drift-corrected sample maps, all in #20's coordinates (grey = not scanned at that gain). Green: the circled feature.", fontsize=11)
fig.subplots_adjust(left=0.01, right=0.99, top=0.94, bottom=0.01, wspace=0.04, hspace=0.08)
fig.savefig(os.path.join(OUT, "figK1_maps.png"), dpi=70); plt.close(fig)

# K2: drift path of the circle centre
tc = lambda i: (D.sweeps[i][2]["t_start"] + D.sweeps[i][2]["t_end"]) / 2
cen = [(i, tc(i) - tc(20), g["C0"][0] + g["shift_from_20"](i)[0], g["C0"][1] + g["shift_from_20"](i)[1]) for i in SEQ]
fig, ax = plt.subplots(1, 2, figsize=(13, 4))
for gn, col in (("2.3", "#2ca02c"), ("4.6", "#ff7f0e"), ("9", "#d62728")):
    pts = [q for q in cen if RUNG[q[0]] == gn]
    ax[0].plot([(256 - q[2]) * PX for q in pts], [q[1] for q in pts], "o", color=col, label=f"KIGA {gn}")
ax[0].plot([(256 - q[2]) * PX for q in cen], [q[1] for q in cen], "-", color="#999", lw=0.8, zorder=0)
for q in cen: ax[0].annotate(f"#{q[0]} {'▲' if direction(q[0]) == 'up' else '▼'}", ((256 - q[2]) * PX, q[1]), fontsize=7, xytext=(4, -2), textcoords="offset points")
ax[0].set_xlabel("feature height in frame, nm from bottom edge"); ax[0].set_ylabel("time since #20 (s)"); ax[0].legend(fontsize=7)
ax[0].set_title("Circle centre moves up the frame: 19.8 nm in 300 s (67 pm/s)", fontsize=9)
ax[1].plot([q[3] * PX for q in cen], [(256 - q[2]) * PX for q in cen], "k.-")
for q in cen: ax[1].annotate(f"#{q[0]}", (q[3] * PX, (256 - q[2]) * PX), fontsize=7, xytext=(4, -2), textcoords="offset points")
ax[1].set_xlim(0, 30); ax[1].set_ylim(0, 30); ax[1].set_aspect("equal")
ax[1].set_xlabel("x in frame (nm)"); ax[1].set_ylabel("y in frame (nm, up)"); ax[1].set_title("Path within the 30 nm frame (2.1 nm left in total)", fontsize=9)
plt.tight_layout(); fig.savefig(os.path.join(OUT, "figK2_driftpath.png"), dpi=90); plt.close(fig)

json.dump(res, open(os.path.join(OUT, "kiga_dc.json"), "w"), indent=1, default=float)
for p in res["pairs"]:
    print(f"{p['ch']:3} #{p['a']}->#{p['b']} {p['kind']:14} K{p['ga']}->{p['gb']}: corr {p['corr']:.2f} over {p['overlap_nm2']:.0f} nm2")
for gn, r in res["gain"].items(): print(gn, {k: v for k, v in r.items() if k not in ("sweeps",)})
print(json.dumps(cross, indent=0, default=float))
