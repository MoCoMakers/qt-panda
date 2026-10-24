import json, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
rows = json.load(open("morph_report/blob_metrics.json"))["rows"]
sat = {18: 0, 20: 33, 21: 21, 22: 17, 23: 12, 25: 16, 26: 12, 27: 18, 28: 17, 30: 6, 31: 3}
t0 = next(r["t"] for r in rows if r["sweep"] == 20)
tt = [r["t"] - t0 for r in rows]; col = ["#1f77b4" if r["dir"] == "up" else "#ff7f0e" for r in rows]
fig, ax = plt.subplots(1, 3, figsize=(15, 3.7))
def lab(a, ys):
    for r, x, y in zip(rows, tt, ys):
        a.annotate(f"#{r['sweep']} K{r['kiga']}", (x, y), fontsize=6, xytext=(2, 3), textcoords="offset points")
ys = [r.get("area_nm2", np.nan) for r in rows]
ax[0].scatter(tt, ys, c=col, s=40); lab(ax[0], ys)
ax[0].set_title("Dark (high-current) region area, nm²  (blue ▲, orange ▼)", fontsize=9); ax[0].set_xlabel("s since #20")
ys = [sat[r["sweep"]] for r in rows]
ax[1].scatter(tt, ys, c=col, s=40); lab(ax[1], ys)
ax[1].set_title("Share of the 9 × 9 nm window clipped at\nthe current limit (>102 nA), %", fontsize=9); ax[1].set_xlabel("s since #20")
ax2 = ax[2]; ys = [r.get("z_in_minus_ring", np.nan) for r in rows]
ax2.scatter(tt, ys, c=col, s=40); lab(ax2, ys); ax2.axhline(0, color="k", lw=0.5)
ax2.set_ylabel("Z inside outline − ring around (rel.)", fontsize=8); ax2.set_xlabel("s since #20")
ax3 = ax2.twinx(); ax3.plot(tt, [r["z_mean"] for r in rows], "k--", lw=1); ax3.set_ylabel("mean Z DAC (dashed)", fontsize=8)
ax2.set_title("Z rises over the feature as the gain goes up;\nmean Z drifts +9,700 codes", fontsize=9)
plt.tight_layout(); fig.savefig("morph_report/figC2_blob_metrics.png", dpi=95)
