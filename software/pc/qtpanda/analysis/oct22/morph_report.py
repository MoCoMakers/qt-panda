"""Morphology persistence across sweeps #12-#32 (2026-Oct-22).

Row-alignment variants, folded (trace+retrace) surface estimate, drift
by phase correlation between same-direction sweeps, and repeatability
after registration.  Writes PNG figures + metrics JSON to OUT.
"""
import os, sys, json
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, "C:/Users/enact/Projects/qt-panda/software/pc/qtpanda/replay")
sys.path.insert(0, "C:/Users/enact/Projects/qt-panda/software/pc/qtpanda")
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import sweep_player as sp

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "morph_report")
os.makedirs(OUT, exist_ok=True)
D = sp.DayData("2026-Oct-22")

RUNG = {}  # sweep -> label
for i in (12, 13, 14): RUNG[i] = "tip check 1.14"
for i in range(15, 20): RUNG[i] = "KIGA 1.14"
for i in range(20, 25): RUNG[i] = "KIGA 2.3"
for i in range(25, 30): RUNG[i] = "KIGA 4.6"
for i in range(30, 33): RUNG[i] = "KIGA 9"
RCOL = {"tip check 1.14": "#888", "KIGA 1.14": "#1f77b4", "KIGA 2.3": "#2ca02c",
        "KIGA 4.6": "#ff7f0e", "KIGA 9": "#d62728"}


def fill_rows(a):
    a = a.astype(float).copy()
    bad = np.isnan(a).any(1)
    if bad.all(): return None
    good = np.flatnonzero(~bad)
    for r in np.flatnonzero(bad):
        a[r] = a[good[np.argmin(np.abs(good - r))]]
    return a


def plane(a):
    H, W = a.shape; y, x = np.mgrid[:H, :W]
    A = np.c_[x.ravel(), y.ravel(), np.ones(a.size)]
    c, *_ = np.linalg.lstsq(A, a.ravel(), rcond=None)
    return a - (A @ c).reshape(a.shape)


def rowlev(a):
    x = np.arange(a.shape[1]); A = np.vstack([x, np.ones_like(x)]).T
    c, *_ = np.linalg.lstsq(A, a.T, rcond=None)
    return a - (A @ c).T


def mdiff(a):
    a = plane(a)
    d = np.median(np.diff(a, axis=0), axis=1)
    off = np.r_[0, np.cumsum(d)]
    return a - off[:, None]


def corr(a, b):
    a = a - a.mean(); b = b - b.mean()
    den = np.sqrt((a * a).sum() * (b * b).sum())
    return float((a * b).sum() / den) if den else np.nan


def phase_shift(ref, img):
    """(dy, dx, peak) shift that maps img onto ref (img moved by +dx -> ref)."""
    w = np.outer(np.hanning(ref.shape[0]), np.hanning(ref.shape[1]))
    F1 = np.fft.fft2((ref - ref.mean()) * w); F2 = np.fft.fft2((img - img.mean()) * w)
    R = F1 * np.conj(F2); R /= np.abs(R) + 1e-12
    r = np.fft.ifft2(R).real
    p = np.unravel_index(np.argmax(r), r.shape)
    H, W = r.shape
    def sub(c, n, axis):
        cm = r[((c - 1) % n, p[1])] if axis == 0 else r[(p[0], (c - 1) % n)]
        cp = r[((c + 1) % n, p[1])] if axis == 0 else r[(p[0], (c + 1) % n)]
        c0 = r[p]; den = cm - 2 * c0 + cp
        return c + (0.5 * (cm - cp) / den if den else 0)
    dy = sub(p[0], H, 0); dx = sub(p[1], W, 1)
    if dy > H / 2: dy -= H
    if dx > W / 2: dx -= W
    return float(dy), float(dx), float(r[p] / (np.abs(r).mean() * 1.0 + 1e-12))


def overlap_corr(ref, img, dy, dx):
    iy, ix = int(round(dy)), int(round(dx))
    H, W = ref.shape
    ys = slice(max(0, iy), min(H, H + iy)); xs = slice(max(0, ix), min(W, W + ix))
    ys2 = slice(max(0, -iy), min(H, H - iy)); xs2 = slice(max(0, -ix), min(W, W - ix))
    a = ref[ys, xs]; b = img[ys2, xs2]
    return corr(a, b) if a.size > 1000 else np.nan


def load(i):
    out = {}
    for ch in ("z_trace", "z_retrace", "e_trace", "e_retrace"):
        img, idx, s = D.image(i, ch)
        out[ch] = fill_rows(img)
    _, _, s = D.sweeps[i]
    out["dir"] = s["dir"]; out["t"] = s["t_start"]; out["lines"] = s["lines"]
    return out


SW = [i for i in range(12, 33) if D.sweeps[i][2]["lines"] >= 250]
data = {}
for i in SW:
    r = load(i)
    zt, zr = r["z_trace"], r["z_retrace"]
    B_t, B_r = rowlev(zt), rowlev(zr)
    S = (B_t + B_r) / 2; L = (B_t - B_r) / 2
    S_flat = S - S.mean(0)
    data[i] = dict(dir=r["dir"], t=r["t"], A=plane(zt), B=B_t, C=mdiff(zt), S=S, L=L,
                   E=S_flat, err=rowlev(r["e_trace"]))


def show(ax, a, title=None):
    lo, hi = np.percentile(a, [1, 99])
    ax.imshow(a, cmap="inferno", vmin=lo, vmax=hi, interpolation="nearest")
    ax.set_xticks([]); ax.set_yticks([])
    if title: ax.set_title(title, fontsize=7)


# ---- Fig 1: processing variants grid
cols = [("A", "plane only"), ("B", "row offset+slope"), ("C", "median row diff"),
        ("S", "folded S (trace+retrace)"), ("E", "S minus avg row"), ("err", "error trace")]
fig, axes = plt.subplots(len(SW), len(cols), figsize=(len(cols) * 1.55, len(SW) * 1.6))
for r, i in enumerate(SW):
    for c, (k, name) in enumerate(cols):
        show(axes[r, c], data[i][k], name if r == 0 else None)
    axes[r, 0].set_ylabel(f"#{i} {'▲' if data[i]['dir']=='up' else '▼'}\n{RUNG[i]}", fontsize=7,
                          rotation=0, ha="right", va="center", color=RCOL[RUNG[i]])
plt.tight_layout(pad=0.2)
fig.savefig(os.path.join(OUT, "fig1_variants.png"), dpi=90); plt.close(fig)

# ---- drift + persistence, same direction
metrics = {"pairs": [], "ref": [], "lag_share": {}}
for dname in ("up", "down"):
    seq = [i for i in SW if data[i]["dir"] == dname]
    ref = seq[0]
    for a, b in zip(seq, seq[1:]):
        dy, dx, pk = phase_shift(data[a]["S"], data[b]["S"])
        rec = {"a": a, "b": b, "dir": dname, "dt_s": data[b]["t"] - data[a]["t"],
               "dy": dy, "dx": dx, "peak": pk}
        for k in ("B", "S", "E", "L"):
            rec["corr_" + k] = corr(data[a][k], data[b][k])
            rec["corr_" + k + "_aligned"] = overlap_corr(data[a][k], data[b][k], dy, dx)
        metrics["pairs"].append(rec)
    for b in seq:
        dy, dx, pk = phase_shift(data[ref]["S"], data[b]["S"])
        metrics["ref"].append({"ref": ref, "b": b, "dir": dname, "t": data[b]["t"],
                               "dy": dy, "dx": dx, "peak": pk,
                               "corr_S_aligned": overlap_corr(data[ref]["S"], data[b]["S"], dy, dx)})
for i in SW:
    L, S = data[i]["L"], data[i]["S"]
    metrics["lag_share"][i] = float(L.var() / (L.var() + S.var()))

# Y+ vs Y- within each Y-cycle (same area, opposite Y direction, ~25 s apart)
metrics["updown"] = []
for a in SW:
    b = a + 1
    if data[a]["dir"] == "up" and b in data and data[b]["dir"] == "down":
        dy, dx, pk = phase_shift(data[a]["S"], data[b]["S"])
        metrics["updown"].append({"a": a, "b": b, "dy": dy, "dx": dx, "peak": pk,
                                  "corr_S": corr(data[a]["S"], data[b]["S"]),
                                  "corr_S_aligned": overlap_corr(data[a]["S"], data[b]["S"], dy, dx)})

t0 = min(data[i]["t"] for i in SW)
# ---- Fig 2: drift vs time
fig, ax = plt.subplots(1, 2, figsize=(11, 3.4))
for dname, mk in (("up", "^"), ("down", "v")):
    rs = [r for r in metrics["ref"] if r["dir"] == dname]
    tt = [r["t"] - t0 for r in rs]
    ax[0].plot(tt, [r["dx"] for r in rs], mk + "-", label=f"dx {dname}")
    ax[0].plot(tt, [r["dy"] for r in rs], mk + "--", label=f"dy {dname}")
    ax[1].plot(tt, [r["corr_S_aligned"] for r in rs], mk + "-", label=f"{dname} vs first {dname}")
for a in (ax[0], ax[1]):
    for i in SW:
        a.axvline(data[i]["t"] - t0, color=RCOL[RUNG[i]], alpha=0.15, lw=6)
ax[0].set_title("Shift vs first same-direction sweep (px, 0.117 nm/px)", fontsize=9)
ax[0].set_xlabel("s since #12"); ax[0].legend(fontsize=7); ax[0].axhline(0, color="k", lw=0.5)
ax[1].set_title("Folded S correlation with first sweep, after alignment", fontsize=9)
ax[1].set_xlabel("s since #12"); ax[1].set_ylim(-0.3, 1); ax[1].axhline(0, color="k", lw=0.5); ax[1].legend(fontsize=7)
plt.tight_layout(); fig.savefig(os.path.join(OUT, "fig2_drift.png"), dpi=100); plt.close(fig)

# ---- Fig 3: consecutive persistence
fig, ax = plt.subplots(figsize=(11, 3.4))
for k, c in (("B", "#555"), ("S", "#1f77b4"), ("E", "#2ca02c"), ("L", "#d62728")):
    xs = [p["b"] for p in metrics["pairs"]]
    ys = [p["corr_" + k + "_aligned"] for p in metrics["pairs"]]
    ax.plot(xs, ys, "o", color=c, label={"B": "trace, row-levelled", "S": "folded S (surface est.)",
                                         "E": "S minus avg row", "L": "direction-flip part (lag)"}[k])
ax.set_xticks([p["b"] for p in metrics["pairs"]])
ax.set_xlabel("sweep # (compared with previous same-direction sweep, after alignment)")
ax.set_ylabel("correlation"); ax.axhline(0.5, ls="--", color="k", lw=0.6); ax.set_ylim(-0.3, 1.0)
ax.legend(fontsize=7, ncol=4); ax.set_title("Does the image repeat? consecutive same-direction pairs", fontsize=9)
plt.tight_layout(); fig.savefig(os.path.join(OUT, "fig3_persistence.png"), dpi=100); plt.close(fig)

# ---- Fig 4: registered averages per rung (S), plus first vs last individual
rungs = ["tip check 1.14", "KIGA 1.14", "KIGA 2.3", "KIGA 4.6", "KIGA 9"]
fig, axes = plt.subplots(2, len(rungs), figsize=(len(rungs) * 2.3, 4.9))
avg = {}
for c, rg in enumerate(rungs):
    mem = [i for i in SW if RUNG[i] == rg]
    ref = data[mem[0]]["S"]; acc = np.zeros_like(ref); n = 0
    for i in mem:
        dy, dx, _ = phase_shift(ref, data[i]["S"])
        acc += np.roll(np.roll(data[i]["S"], int(round(dy)), 0), int(round(dx)), 1); n += 1
    avg[rg] = acc / n
    show(axes[0, c], avg[rg], f"{rg}: avg of {n} (aligned S)")
    show(axes[1, c], avg[rg] - avg[rg].mean(0), "same, minus avg row")
plt.tight_layout(pad=0.3); fig.savefig(os.path.join(OUT, "fig4_rung_avgs.png"), dpi=100); plt.close(fig)
rung_cross = {}
for a in rungs:
    for b in rungs:
        if a < b:
            dy, dx, _ = phase_shift(avg[a], avg[b])
            rung_cross[f"{a} | {b}"] = {"dx": dx, "dy": dy, "corr_aligned": overlap_corr(avg[a], avg[b], dy, dx)}
metrics["rung_cross"] = rung_cross

# ---- Fig 5: average row profiles trace vs retrace per rung (the lag shape)
fig, ax = plt.subplots(1, len(rungs), figsize=(len(rungs) * 2.3, 2.4), sharey=False)
for c, rg in enumerate(rungs):
    mem = [i for i in SW if RUNG[i] == rg]
    for i in mem:
        ax[c].plot(data[i]["B"].mean(0), color="#1f77b4", alpha=0.5, lw=0.8)
        ax[c].plot((data[i]["B"] - 2 * data[i]["L"]).mean(0), color="#ff7f0e", alpha=0.5, lw=0.8)
    ax[c].set_title(rg, fontsize=8); ax[c].set_xticks([]); ax[c].tick_params(labelsize=6)
plt.tight_layout(pad=0.3); fig.savefig(os.path.join(OUT, "fig5_profiles.png"), dpi=100); plt.close(fig)

json.dump(metrics, open(os.path.join(OUT, "metrics.json"), "w"), indent=1, default=float)
print("sweeps", SW)
for p in metrics["pairs"]:
    print(f"#{p['a']}->#{p['b']} {p['dir']:4} dt {p['dt_s']:5.0f}s  shift dx {p['dx']:6.1f} dy {p['dy']:6.1f}  "
          f"peak {p['peak']:5.1f}  S {p['corr_S']:.2f}->{p['corr_S_aligned']:.2f}  E {p['corr_E_aligned']:.2f}  "
          f"B {p['corr_B_aligned']:.2f}  L {p['corr_L_aligned']:.2f}")
print("updown", [(u["a"], round(u["dx"], 1), round(u["dy"], 1), round(u["corr_S_aligned"], 2)) for u in metrics["updown"]])
print("lag", {k: round(v, 2) for k, v in metrics["lag_share"].items()})
print("rung cross", {k: (round(v["dx"], 1), round(v["dy"], 1), round(v["corr_aligned"], 2)) for k, v in rung_cross.items()})
