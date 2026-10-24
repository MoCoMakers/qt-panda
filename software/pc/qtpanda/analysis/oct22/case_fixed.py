"""Segmentation-free case-study metrics: a fixed sample window that follows the drift model.

Window: 9 x 9 nm (77 px) centred on the #20 blob, carried into each sweep by the drift model.
  clipped share  = fraction of raw error pixels at exactly the clip value (current > ~102 nA)
  dark share     = fraction of the window in the darkest 20% of that sweep's error values
  Z centre-surround = mean Z (folded S) in the central 4 x 4 nm minus the rest of the window
"""
import os, json
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "blob_case.py"), encoding="utf-8").read().split("\nrows = []")[0]
g = {"__file__": os.path.join(HERE, "blob_case.py")}; exec(compile(src, "bc", "exec"), g)
np, plt, D = g["np"], g["plt"], g["D"]
inner = g["ns"]["ns"]
import matplotlib.patches as mpatches
PX = 30.0 / 256
W, C = 77, 34                    # 9 nm window, 4 nm centre

rows = []
for i in g["ORDER"]:
    dy, dx = g["shift_from_20"](i)
    cy_, cx_ = g["C0"][0] + dy, g["C0"][1] + dx
    raw = inner["fill_rows"](D.image(i, "e_trace")[0])
    lo = raw.min()
    E, S = g["IMG"][i]
    def win(a, half):
        y, x = int(round(cy_)), int(round(cx_))
        ys, ye, xs, xe = max(0, y - half), min(a.shape[0], y + half), max(0, x - half), min(a.shape[1], x + half)
        return a[ys:ye, xs:xe], (ye - ys) * (xe - xs) / (2 * half) ** 2
    rw, cov = win(raw, W // 2)
    ew, _ = win(E, W // 2)
    sw, _ = win(S, W // 2); sc, _ = win(S, C // 2)
    rec = dict(sweep=i, kiga=g["RUNG"][i], dir=D.sweeps[i][2]["dir"], t=g["t"](i), coverage=cov,
               centre=(cy_, cx_))
    if cov > 0.5:
        rec["clipped_pct"] = 100 * float(np.mean(rw == lo))
        rec["dark_pct"] = 100 * float(np.mean(ew < np.percentile(E, 20)))
        rec["z_centre_minus_window"] = float(np.mean(sc) - np.mean(sw))
    rec["z_mean"] = g["zstats"](i)[0]
    rows.append(rec)
    print({k: (round(v, 1) if isinstance(v, float) else v) for k, v in rec.items() if k not in ("t", "centre")})
json.dump(rows, open(os.path.join(HERE, "morph_report", "case_fixed.json"), "w"), indent=1, default=float)

# Figure C1 (redrawn): crops with the fixed analysis windows, no segmentation
order = g["ORDER"]; n = len(order)
fig, axes = plt.subplots(2, n, figsize=(1.8 * n, 4.6))
for k, i in enumerate(order):
    E, S = g["IMG"][i]
    dy, dx = g["shift_from_20"](i); c = (g["C0"][0] + dy, g["C0"][1] + dx)
    ce, cs = g["crop"](E, c), g["crop"](S, c)
    lo_, hi_ = np.percentile(E, [1, 99])
    r = next(q for q in rows if q["sweep"] == i)
    for row, (img, l, h_) in enumerate(((ce, lo_, hi_), (cs, *np.nanpercentile(cs, [1, 99])))):
        ax = axes[row, k]; ax.imshow(img, cmap="inferno", vmin=l, vmax=h_, interpolation="nearest")
        ax.add_patch(mpatches.Rectangle((60 - W / 2, 60 - W / 2), W, W, fill=False, ec="cyan", lw=1))
        ax.add_patch(mpatches.Rectangle((60 - C / 2, 60 - C / 2), C, C, fill=False, ec="white", lw=1, ls="--"))
        ax.set_xticks([]); ax.set_yticks([])
    note = " (edge)" if i == 18 else ""
    clip = f"{r['clipped_pct']:.0f}% clipped" if "clipped_pct" in r else "off frame"
    axes[0, k].set_title(f"#{i} {'▲' if r['dir']=='up' else '▼'} K{r['kiga']}{note}\n{clip}", fontsize=7.5)
    zc = f"Z centre {r['z_centre_minus_window']:+.0f}" if "z_centre_minus_window" in r else ""
    axes[1, k].set_title(zc, fontsize=7.5)
axes[0, 0].set_ylabel("error", fontsize=8); axes[1, 0].set_ylabel("Z folded S", fontsize=8)
fig.suptitle("Same sample patch in every sweep (crop 14 × 14 nm, carried by the drift model). "
             "Cyan: fixed 9 × 9 nm analysis window; dashed: 4 × 4 nm centre", fontsize=8.5)
fig.subplots_adjust(left=0.02, right=0.99, top=0.8, bottom=0.02, wspace=0.05, hspace=0.3)
fig.savefig(os.path.join(HERE, "morph_report", "figC1_blob_crops.png"), dpi=95); plt.close(fig)

# Figure C2 (redrawn): fixed-window metrics
ok = [r for r in rows if "clipped_pct" in r]
t20 = g["t"](20)
tt = [r["t"] - t20 for r in ok]; col = ["#1f77b4" if r["dir"] == "up" else "#ff7f0e" for r in ok]
fig, ax = plt.subplots(1, 3, figsize=(15, 3.6))
for a, key, ttl in ((ax[0], "clipped_pct", "Share of the 9 × 9 nm window clipped (>102 nA), %"),
                    (ax[1], "dark_pct", "Share of the window in the sweep's darkest 20% of error, %"),
                    (ax[2], "z_centre_minus_window", "Z (folded S): 4 × 4 nm centre minus 9 × 9 nm window")):
    ys = [r[key] for r in ok]; a.scatter(tt, ys, c=col, s=40)
    for r, x, y in zip(ok, tt, ys): a.annotate(f"#{r['sweep']} K{r['kiga']}", (x, y), fontsize=6, xytext=(2, 3), textcoords="offset points")
    a.set_title(ttl, fontsize=9); a.set_xlabel("s since #20")
ax[2].axhline(0, color="k", lw=0.5)
plt.tight_layout(); fig.savefig(os.path.join(HERE, "morph_report", "figC2_blob_metrics.png"), dpi=95); plt.close(fig)
print("figures done")
