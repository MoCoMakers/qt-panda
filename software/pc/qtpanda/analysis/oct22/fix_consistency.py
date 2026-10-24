"""Consistency fixes: rebuild D3 (drift path from the cross-checked model) and D5 (standard
side-by-side with the all-10-sweep drift-corrected reference in #20 coordinates); save the
reference so later figures can be shown next to it."""
import os, json
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "morph_report")
src = open(os.path.join(HERE, "kiga_dc.py"), encoding="utf-8").read().split("# ---------------- figures")[0]
k = {"__file__": os.path.join(HERE, "kiga_dc.py")}; exec(compile(src, "kd", "exec"), k)
np, plt, D, g = k["np"], k["plt"], k["D"], k["g"]
CAN, SEQ, X0, X1, Y0, Y1 = k["CAN"], k["SEQ"], k["X0"], k["X1"], k["Y0"], k["Y1"]
PX = 30.0 / 256
import matplotlib.patches as mpatches

# ---- the standing reference: all 10 sweeps, drift-corrected, #20 coordinates
REF = {}
for ch in ("err", "S"):
    st = np.array([CAN[ch][i] for i in SEQ]); n = np.sum(np.isfinite(st), 0)
    av = np.nanmean(st, 0); av[n < 2] = np.nan; REF[ch] = av
np.savez_compressed(os.path.join(OUT, "reference_all10_20coords.npz"), err=REF["err"], S=REF["S"],
                    canvas=np.array([Y0, Y1, X0, X1]), sweeps=np.array(SEQ))

# uncorrected: the same sweeps averaged with no shift (placed at #20's position)
UNC = {}
for ch in ("err", "S"):
    st = []
    for i in SEQ:
        a = np.full((Y1 - Y0, X1 - X0), np.nan); img = k["zs"](g["IMG"][i][0 if ch == "err" else 1])
        a[-Y0:-Y0 + 256, -X0:-X0 + 256] = img; st.append(a)
    UNC[ch] = np.nanmean(np.array(st), 0)
single = {ch: CAN[ch][20] for ch in ("err", "S")}


def show(ax, a, title):
    lo, hi = np.nanpercentile(a, [1, 99])
    ax.imshow(a, cmap="inferno", vmin=lo, vmax=hi, interpolation="nearest", extent=(X0 - 0.5, X1 - 0.5, Y1 - 0.5, Y0 - 0.5))
    ax.set_facecolor("#ddd"); ax.set_xticks([]); ax.set_yticks([]); ax.set_title(title, fontsize=9)
    ax.add_patch(mpatches.Ellipse((135, 220), 70, 72, fill=False, ec="#39ff14", lw=1.5))
    ax.plot([X0 + 4, X0 + 4 + 85.4], [Y1 - 12, Y1 - 12], color="white", lw=3); ax.text(X0 + 6, Y1 - 18, "10 nm", color="white", fontsize=8)
    ax.set_xlim(X0, X1); ax.set_ylim(Y1, Y0)

fig, axes = plt.subplots(2, 3, figsize=(13.5, 11.5))
for r, ch in enumerate(("err", "S")):
    nm = "error" if ch == "err" else "Z (folded S)"
    show(axes[r, 0], single[ch], f"{nm}: #20 alone")
    show(axes[r, 1], REF[ch], f"{nm}: all 10 sweeps, drift-corrected (reference)")
    show(axes[r, 2], UNC[ch], f"{nm}: same 10 sweeps, no correction")
fig.suptitle("Standard view in #20's coordinates (grey = not scanned). Green: the circled feature.", fontsize=11)
fig.subplots_adjust(left=0.01, right=0.99, top=0.94, bottom=0.01, wspace=0.04, hspace=0.08)
fig.savefig(os.path.join(OUT, "figD5_corrected_stack.png"), dpi=70); plt.close(fig)

# ---- D3: drift path from the model vs the cross-checked measured pairs, and chain consistency
mm = json.load(open(os.path.join(OUT, "model_metrics.json"))); dm = json.load(open(os.path.join(OUT, "drift_metrics.json")))
tc = lambda i: (D.sweeps[i][2]["t_start"] + D.sweeps[i][2]["t_end"]) / 2
mod = {i: (-g["shift_from_20"](i)[0], -g["shift_from_20"](i)[1]) for i in SEQ}   # content moved: up = positive
fig, ax = plt.subplots(1, 2, figsize=(12.5, 3.9))
T = [tc(i) - tc(20) for i in SEQ]
ax[0].plot(T, [mod[i][0] for i in SEQ], "o-", color="#1f77b4", label="up the frame (model)")
ax[0].plot(T, [mod[i][1] for i in SEQ], "s-", color="#ff7f0e", label="left (model)")
for a, b, dy, dx in mm["used"]:
    if a in mod and b in mod:
        ax[0].annotate("", xy=(tc(b) - tc(20), mod[a][0] + dy), xytext=(tc(a) - tc(20), mod[a][0]),
                       arrowprops=dict(arrowstyle="->", color="#555", lw=0.8))
for i in SEQ: ax[0].annotate(f"#{i}", (tc(i) - tc(20), mod[i][0]), fontsize=6, xytext=(2, 4), textcoords="offset points")
ax[0].set_xlabel("s since #20"); ax[0].set_ylabel("feature displacement since #20 (px; 1 px = 0.117 nm)")
ax[0].set_title("Drift path (lines: fitted model; grey arrows: the 13 cross-checked measured shifts)", fontsize=9); ax[0].legend(fontsize=7)
ch = dm["chain"]
ax[1].scatter([q["pred_dy"] for q in ch], [q["meas_dy"] for q in ch], c=["#1f77b4" if q["ch"] == "err" else "#ff7f0e" for q in ch], s=18)
lim = [-80, 80]; ax[1].plot(lim, lim, "k--", lw=0.7); ax[1].set_xlim(lim); ax[1].set_ylim(lim)
ax[1].set_xlabel("predicted a→c = (a→b) + (b→c), px"); ax[1].set_ylabel("measured a→c, px")
ax[1].set_title("Chain consistency, vertical (blue error, orange Z): on the diagonal = self-consistent", fontsize=8)
plt.tight_layout(); fig.savefig(os.path.join(OUT, "figD3_track_chain.png"), dpi=90); plt.close(fig)
print("D3, D5 rebuilt; reference saved")
