"""V2 report figures (peaks bright, line-by-line drift registration) + 3D data.
Outputs in morph_report_v2/."""
import os, io, json, base64
HERE = os.path.dirname(os.path.abspath(__file__))
import v2_core as V
np = V.np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
import matplotlib.patches as mp
from PIL import Image
OUT = os.path.join(HERE, "morph_report_v2"); os.makedirs(OUT, exist_ok=True)
SEQ, S_, PX = V.SEQ, V.S_, V.PX_NM
CY, CX, HR, HC = V.CIRC
YOFF = -V.Y0                                       # canvas row of sample row 0
CM = "inferno"
arrow = lambda i: "▲" if S_(i)["dir"] == "up" else "▼"
REG = {i: V.reg(i, True) for i in SEQ}
OWN = {i: V.images(i) for i in SEQ}


def lims(a):
    f = a[np.isfinite(a)]; return np.percentile(f, [1, 99])


def show(ax, a, title=None, lo_hi=None, extent=None):
    lo, hi = lo_hi if lo_hi is not None else lims(a)
    ax.imshow(np.ma.masked_invalid(a), cmap=CM, vmin=lo, vmax=hi, interpolation="nearest", extent=extent)
    ax.set_facecolor("#cfcfcf"); ax.set_xticks([]); ax.set_yticks([])
    if title: ax.set_title(title, fontsize=9)


def circle(ax, cy, cx, ls="--", sc=1.0):
    ax.add_patch(mp.Ellipse((cx, cy), 2 * HC * sc, 2 * HR * sc, fill=False, ec="#39ff14", lw=1.5, ls=ls))


def nanmean_stack(arrs):
    st = np.stack(arrs); n = np.isfinite(st).sum(0)
    with np.errstate(invalid="ignore"): m = np.nansum(st, 0) / n
    m[n == 0] = np.nan; return m, n


# ---------------------------------------------------------------- 1. registration demo
avgE, nE = nanmean_stack([REG[i][0] for i in SEQ]); avgS, _ = nanmean_stack([REG[i][1] for i in SEQ])
rows = np.flatnonzero((nE >= 3).any(1)); r0, r1 = rows[0], rows[-1] + 1
uE = np.mean([OWN[i][0] for i in SEQ], 0); uS = np.mean([OWN[i][1] for i in SEQ], 0)
fig, ax = plt.subplots(2, 3, figsize=(12, 10.5), gridspec_kw=dict(height_ratios=[1, 1]))
for r, (one, avg, un, nm) in enumerate(((REG[20][0], avgE, uE, "−error"), (REG[20][1], avgS, uS, "−Z (folded S)"))):
    show(ax[r, 0], one[r0:r1], f"#20 alone, {nm}")
    show(ax[r, 1], avg[r0:r1], f"10 sweeps, drift-registered line by line, {nm}")
    show(ax[r, 2], un, f"10 sweeps averaged as scanned (no correction), {nm}")
    circle(ax[r, 0], CY + YOFF - r0, CX); circle(ax[r, 1], CY + YOFF - r0, CX)
fig.suptitle("Oct 22 #20–#31 · peaks bright · left and middle in the sample frame (#20's coordinates; grey = never scanned)", fontsize=10)
plt.tight_layout(); fig.savefig(os.path.join(OUT, "v2_register.png"), dpi=72); plt.close(fig)

# ---------------------------------------------------------------- 2. time-lapse GIF: as scanned vs registered
def carried(i):
    t = V.row_times(i); r = CY
    for _ in range(3):
        dy, dx = V.dy_dx(i, t[int(np.clip(round(r), 0, 255))]); r = CY + float(dy)
    return r, CX + dx


frames = []
loE = np.nanpercentile(np.concatenate([OWN[i][0].ravel() for i in SEQ]), [1, 99])
for i in SEQ:
    fig, (a, b) = plt.subplots(1, 2, figsize=(9.2, 6.2), gridspec_kw=dict(width_ratios=[1, 1.15]))
    show(a, OWN[i][0], f"#{i} {arrow(i)} KIGA {V.RUNG[i]} · as scanned\n(the window's own coordinates)", loE)
    cy, cx = carried(i); circle(a, cy, cx)
    show(b, REG[i][0][r0:r1], f"#{i} · drift-registered (sample frame)\nthe feature stays put; the window moves", loE)
    circle(b, CY + YOFF - r0, CX)
    for ax_ in (a, b):
        ax_.text(4, 12 if ax_ is a else 12, f"t = {np.mean(V.row_times(i)) - V.T20 + 12.4:.0f} s", color="w", fontsize=9)
    plt.tight_layout(); bb = io.BytesIO(); fig.savefig(bb, format="png", dpi=72); plt.close(fig)
    frames.append(Image.open(io.BytesIO(bb.getvalue())).convert("P", palette=Image.ADAPTIVE))
frames[0].save(os.path.join(OUT, "v2_timelapse.gif"), save_all=True, append_images=frames[1:], duration=900, loop=0)

# ---------------------------------------------------------------- 3. the feature, registered crops
HALF = 60
def crop(a, cy=CY, cx=CX):
    y = int(round(cy)) + YOFF; return a[y - HALF:y + HALF, cx - HALF:cx + HALF]

fig, ax = plt.subplots(2, len(SEQ), figsize=(2.05 * len(SEQ), 4.6))
for k, i in enumerate(SEQ):
    for r in range(2):
        show(ax[r, k], crop(REG[i][r]))
        circle(ax[r, k], HALF, HALF)
    ax[0, k].set_title(f"#{i} {arrow(i)} {V.RUNG[i]}", fontsize=9)
ax[0, 0].set_ylabel("−error"); ax[1, 0].set_ylabel("−Z (folded S)")
plt.tight_layout(); fig.savefig(os.path.join(OUT, "v2_feature.png"), dpi=72); plt.close(fig)

# ---------------------------------------------------------------- 4. crater test
# centre: the darkest point (lowest -error) inside the circle in the #21-#23 registered average
m23, _ = nanmean_stack([REG[i][0] for i in (21, 22, 23)])
from scipy import ndimage as ndi
sm = ndi.gaussian_filter(np.nan_to_num(m23, nan=np.nanmean(m23)), 3)
yy, xx = np.mgrid[0:sm.shape[0], 0:sm.shape[1]]
inside = ((yy - (CY + YOFF)) / HR) ** 2 + ((xx - CX) / HC) ** 2 <= 0.6
cyc, cxc = np.unravel_index(np.argmin(np.where(inside, sm, np.inf)), sm.shape)
RC, RA0, RA1 = 8, 14, 26                                   # px: centre disk, annulus (≈0.9, 1.6–3.0 nm)
dd = np.hypot(yy - cyc, xx - cxc)
cen, ann = dd <= RC, (dd >= RA0) & (dd <= RA1)

def rim_minus_centre(a, c_y, c_x):
    d = np.hypot(yy - c_y, xx - c_x); ce, an = d <= RC, (d >= RA0) & (d <= RA1)
    v1, v2 = a[ce], a[an]
    if np.isfinite(v1).mean() < 0.9 or np.isfinite(v2).mean() < 0.9: return np.nan
    return float((np.nanmean(v2) - np.nanmean(v1)) / np.nanstd(a))   # in units of the sweep's spread

rng = np.random.default_rng(1)
res = {}
for i in SEQ:
    E, Sz = REG[i]
    ctrl = {0: [], 1: []}
    ok = np.argwhere(np.isfinite(E))
    for _ in range(400):
        y, x = ok[rng.integers(len(ok))]
        if np.hypot(y - cyc, x - cxc) < 40: continue
        for ch, A in ((0, E), (1, Sz)):
            v = rim_minus_centre(A, y, x)
            if np.isfinite(v): ctrl[ch].append(v)
    res[i] = dict(err=rim_minus_centre(E, cyc, cxc), z=rim_minus_centre(Sz, cyc, cxc),
                  err_ctrl=np.percentile(ctrl[0], [5, 50, 95]).tolist(), z_ctrl=np.percentile(ctrl[1], [5, 50, 95]).tolist(),
                  err_pct=float(np.mean(np.array(ctrl[0]) < rim_minus_centre(E, cyc, cxc)) * 100),
                  z_pct=float(np.mean(np.array(ctrl[1]) < rim_minus_centre(Sz, cyc, cxc)) * 100))
fig, ax = plt.subplots(1, 2, figsize=(11, 3.8), sharey=True)
xs = np.arange(len(SEQ))
for k, (key, nm) in enumerate((("err", "−error (current-like)"), ("z", "−Z folded S (height)"))):
    lo = [res[i][key + "_ctrl"][0] for i in SEQ]; hi = [res[i][key + "_ctrl"][2] for i in SEQ]
    ax[k].fill_between(xs, lo, hi, color="#bbb", alpha=0.6, label="random places, 5–95%")
    for j, i in enumerate(SEQ):
        ax[k].plot(j, res[i][key], "^" if S_(i)["dir"] == "up" else "v", ms=10,
                   color="#1f77b4" if S_(i)["dir"] == "up" else "#ff7f0e")
    ax[k].plot(xs, [res[i][key] for i in SEQ], color="#555", lw=0.8)
    ax[k].axhline(0, color="k", lw=0.6)
    ax[k].set_xticks(xs); ax[k].set_xticklabels([f"#{i}\n{V.RUNG[i]}" for i in SEQ], fontsize=8)
    ax[k].set_title(nm, fontsize=10)
    for x0, x1 in ((3.5, 3.5), (7.5, 7.5)): ax[k].axvline(x0, color="#999", ls=":", lw=0.8)
ax[0].set_ylabel("rim − centre (in units of the sweep's spread)\n> 0: centre lower than rim (crater) · < 0: centre higher (dome)")
ax[0].legend(fontsize=8, loc="lower left")
plt.tight_layout(); fig.savefig(os.path.join(OUT, "v2_crater.png"), dpi=80); plt.close(fig)

# ---------------------------------------------------------------- 5. per-gain registered averages
groups = [("2.3", [20, 21, 22, 23]), ("4.6", [25, 26, 27, 28]), ("9", [30, 31]), ("all 10", SEQ)]
fig, ax = plt.subplots(2, 4, figsize=(13, 9))
for k, (nm, sw) in enumerate(groups):
    for r in range(2):
        m, n = nanmean_stack([REG[i][r] for i in sw])
        show(ax[r, k], m[r0:r1], f"{'−error' if r == 0 else '−Z (folded S)'} · KIGA {nm} · {len(sw)} sweeps" if nm != "all 10" else
             f"{'−error' if r == 0 else '−Z (folded S)'} · all 10 sweeps")
        circle(ax[r, k], CY + YOFF - r0, CX)
fig.suptitle("Drift-registered averages per gain, sample frame (grey = not scanned at that gain) · peaks bright", fontsize=10)
plt.tight_layout(); fig.savefig(os.path.join(OUT, "v2_gain.png"), dpi=72); plt.close(fig)

# ---------------------------------------------------------------- 6. 3D data: registered height (-Z folded S) around the feature
R0_, R1_, C0_, C1_ = CY - 80, CY + 72, CX - 75, CX + 75          # sample rows / cols (~17.8 x 17.6 nm)
DS = 2
def win(a): return a[R0_ + YOFF:R1_ + YOFF, C0_:C1_]

def png_uri(fig):
    b = io.BytesIO(); fig.savefig(b, format="png", dpi=80); plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()

def norm(a):
    lo, hi = lims(a); return np.clip((a - lo) / (hi - lo + 1e-9), 0, 1)

sweeps = {}
for i in SEQ:
    E, Sz = REG[i]
    h = ndi.gaussian_filter(np.nan_to_num(win(Sz), nan=np.nanmedian(win(Sz))), 1.5)[::DS, ::DS]
    c = np.nan_to_num(norm(win(E)), nan=0.5)[::DS, ::DS]
    valid = np.isfinite(win(Sz))[::DS, ::DS]
    # side images: as scanned, with carried circle; registered window
    f1, a1 = plt.subplots(figsize=(4.4, 4.4)); show(a1, OWN[i][0]); cy, cx = carried(i); circle(a1, cy, cx)
    a1.add_patch(mp.Rectangle((C0_ + (cx - CX) - 0.5, R0_ + (cy - CY) - 0.5), C1_ - C0_, R1_ - R0_, fill=False, ec="cyan", lw=1, ls=":"))
    f1.subplots_adjust(0, 0, 1, 1)
    f2, a2 = plt.subplots(figsize=(4.4, 4.4)); show(a2, win(E)); circle(a2, CY - R0_, CX - C0_); f2.subplots_adjust(0, 0, 1, 1)
    sweeps[str(i)] = dict(id=i, dir=S_(i)["dir"], kiga=V.RUNG[i],
                          t=round(float(np.mean(V.row_times(i)) - V.T20 + 12.4), 1),
                          h=np.round(h, 1).tolist(), c=np.round(c, 3).tolist(), v=valid.astype(int).tolist(),
                          scanned=png_uri(f1), registered=png_uri(f2), rim=res[i])
avg = {}
for nm, sw in groups:
    m, n = nanmean_stack([win(REG[i][1]) for i in sw]); me, _ = nanmean_stack([win(REG[i][0]) for i in sw])
    avg[nm] = dict(h=np.round(ndi.gaussian_filter(np.nan_to_num(m, nan=np.nanmedian(m)), 1.5)[::DS, ::DS], 1).tolist(),
                   c=np.round(np.nan_to_num(norm(me), nan=0.5)[::DS, ::DS], 3).tolist(), sweeps=sw)
data = dict(rows=len(sweeps["20"]["h"]), cols=len(sweeps["20"]["h"][0]), px_nm=PX * DS, order=SEQ,
            circle=[(CY - R0_) / DS, (CX - C0_) / DS, HR / DS, HC / DS],
            centre=[(cyc - YOFF - R0_) / DS, (cxc - C0_) / DS], sweeps=sweeps, avg=avg)
json.dump(data, open(os.path.join(OUT, "v2_3d.json"), "w"))
json.dump(dict(centre_sample_rc=[int(cyc - YOFF), int(cxc)], rim=res,
               canvas_rows=[int(r0 - YOFF), int(r1 - YOFF)]), open(os.path.join(OUT, "v2_metrics.json"), "w"), indent=1)
print("crater centre (sample row, col):", int(cyc - YOFF), int(cxc), "| circle centre", CY, CX)
for i in SEQ:
    print(f"#{i} {S_(i)['dir']:>4} {V.RUNG[i]:>4}  rim-centre err {res[i]['err']:+.2f} (pct {res[i]['err_pct']:.0f})  Z {res[i]['z']:+.2f} (pct {res[i]['z_pct']:.0f})")
