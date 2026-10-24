"""Drift-accounted image-to-image analysis, 2026-Oct-22 #12-#31 (validated settings).

Templates 96x96 px (stride 32), Gaussian sigma 1, both channels (error trace,
Z folded S).  For each pair: consensus shift, agreement, peak vs null.
Joint evidence = both channels agree on the shift within 6 px.
Chain check: shift(a->c) vs shift(a->b)+shift(b->c).
"""
import os, json, datetime as dt
os.environ["QT_QPA_PLATFORM"] = "offscreen"
HERE = os.path.dirname(os.path.abspath(__file__))
MARK = "SW = [i for i in range(12, 32) if D.sweeps"
src = open(os.path.join(HERE, "patch_track.py"), encoding="utf-8").read().split(MARK)[0]
ns = {"__file__": os.path.join(HERE, "patch_track.py")}; exec(compile(src, "pt", "exec"), ns)
np, sp, plt, D = ns["np"], ns["sp"], ns["plt"], ns["D"]
import matplotlib.patches as mpatches
ns["PS"], ns["SIG"], ns["STRIDE"] = 96, 1.0, 32
PS = 96
OUT = os.path.join(HERE, "morph_report")
RUNG = ns["RUNG"]
DS = sp.DayData("2026-Sep-24")

SW = [i for i in range(12, 32) if D.sweeps[i][2]["lines"] >= 250]
IM = {"err": {i: ns["prep_err"](D, i) for i in SW}, "S": {i: ns["prep_S"](D, i) for i in SW}}
NULL = {"err": ns["prep_err"](DS, 1806), "S": ns["prep_S"](DS, 1806)}
CTRL = {"err": {i: ns["prep_err"](DS, i) for i in (1806, 1808)}}


def pair(a, b, chan, imgs=None, null=None):
    imgs = imgs or IM[chan]
    recs = ns["track"](imgs[a], imgs[b], [imgs[a][::-1, ::-1], null if null is not None else NULL[chan]])
    c = ns["consensus"](recs, tol=5) or {}
    c["recs"] = recs
    return c


def t(i): return D.sweeps[i][2]["t_start"]


pairs = list(zip(SW, SW[1:])) + list(zip(SW, SW[2:]))
R = {}
for a, b in pairs:
    e, s = pair(a, b, "err"), pair(a, b, "S")
    joint = abs(e["dy"] - s["dy"]) <= 6 and abs(e["dx"] - s["dx"]) <= 6
    strong = lambda c: c["frac"] >= 0.3 and c["peak_agree"] > c["null_p95"]
    R[(a, b)] = dict(a=a, b=b, ga=RUNG[a], gb=RUNG[b], dt=t(b) - t(a), err=e, S=s, joint=bool(joint),
                     verdict=("LOCKED (both channels)" if joint and (strong(e) or strong(s))
                              else "locked (one channel)" if strong(e) or strong(s) else "no lock"))
    r = R[(a, b)]
    print(f"#{a}->#{b} ({r['ga']}->{r['gb']}, {r['dt']:4.0f}s)  err dy {e['dy']:+5.1f} dx {e['dx']:+5.1f} "
          f"{e['n_agree']}/{e['n']} pk {e['peak_agree']:.2f} null95 {e['null_p95']:.2f} | "
          f"S dy {s['dy']:+5.1f} dx {s['dx']:+5.1f} {s['n_agree']}/{s['n']} pk {s['peak_agree']:.2f} null95 {s['null_p95']:.2f} "
          f"| {r['verdict']}", flush=True)

# chain consistency for skip-one pairs
chain = []
for a, b, c in zip(SW, SW[1:], SW[2:]):
    for ch in ("err", "S"):
        ab, bc, ac = R[(a, b)][ch], R[(b, c)][ch], R[(a, c)][ch]
        pred = (ab["dy"] + bc["dy"], ab["dx"] + bc["dx"])
        chain.append(dict(a=a, b=b, c=c, ch=ch, pred_dy=pred[0], pred_dx=pred[1], meas_dy=ac["dy"], meas_dx=ac["dx"],
                          err_px=float(np.hypot(pred[0] - ac["dy"], pred[1] - ac["dx"]))))
print("\nchain consistency (|predicted a->c minus measured a->c|, px):")
for q in chain:
    print(f"  #{q['a']}->#{q['b']}->#{q['c']} {q['ch']:3}  predicted ({q['pred_dy']:+.0f},{q['pred_dx']:+.0f}) "
          f"measured ({q['meas_dy']:+.0f},{q['meas_dx']:+.0f})  miss {q['err_px']:.1f}")

# drift track from consecutive pairs: average the two channels when they agree, else the stronger one
pos = np.zeros(2); track = [(SW[0], 0.0, 0.0, 0.0, "start")]
for a, b in zip(SW, SW[1:]):
    r = R[(a, b)]
    if r["verdict"] == "no lock":
        track.append((b, t(b) - t(SW[0]), pos[0], pos[1], "gap")); continue
    e, s = r["err"], r["S"]
    if r["joint"]:
        d = np.array([(e["dy"] + s["dy"]) / 2, (e["dx"] + s["dx"]) / 2])
    else:
        best = e if e["peak_agree"] - e["null_p95"] >= s["peak_agree"] - s["null_p95"] else s
        d = np.array([best["dy"], best["dx"]])
    pos = pos + d
    track.append((b, t(b) - t(SW[0]), pos[0], pos[1], r["verdict"]))
print("\ntrack:", [(p[0], round(p[2], 1), round(p[3], 1), p[4]) for p in track])


def show(ax, a, title=None):
    lo, hi = np.percentile(a, [1, 99]); ax.imshow(a, cmap="inferno", vmin=lo, vmax=hi, interpolation="nearest")
    ax.set_xticks([]); ax.set_yticks([])
    if title: ax.set_title(title, fontsize=8)


def proof_row(axes, A, B, a, b, tpl_rec, cons, label, null_img):
    q = tpl_rec
    show(axes[0], B, f"{label}\n#{b} (next): template")
    axes[0].add_patch(mpatches.Rectangle((q["x"], q["y"]), PS, PS, fill=False, ec="cyan", lw=2))
    show(axes[1], A, f"#{a} (prior): where it was found")
    axes[1].add_patch(mpatches.Rectangle((q["x"], q["y"]), PS, PS, fill=False, ec="white", lw=1, ls="--"))
    axes[1].add_patch(mpatches.Rectangle((q["px"], q["py"]), PS, PS, fill=False, ec="cyan", lw=2))
    axes[1].annotate("", xy=(q["px"] + PS / 2, q["py"] + PS / 2), xytext=(q["x"] + PS / 2, q["y"] + PS / 2),
                     arrowprops=dict(arrowstyle="->", color="cyan", lw=1.5))
    show(axes[2], B[q["y"]:q["y"] + PS, q["x"]:q["x"] + PS], "template (zoom)")
    show(axes[3], A[q["py"]:q["py"] + PS, q["px"]:q["px"] + PS], f"found in #{a} (zoom)")
    m = ns["ncc_map"](A, B[q["y"]:q["y"] + PS, q["x"]:q["x"] + PS])
    mn = ns["ncc_map"](null_img, B[q["y"]:q["y"] + PS, q["x"]:q["x"] + PS])
    axes[4].imshow(m, cmap="viridis", vmin=-0.3, vmax=1); axes[4].plot(q["px"], q["py"], "r+", ms=14, mew=2)
    axes[4].set_xticks([]); axes[4].set_yticks([])
    axes[4].set_title(f"NCC search over #{a}: peak {m.max():.2f}\n"
                      f"same search in unrelated frame: {mn.max():.2f}", fontsize=8)
    axes[5].imshow(mn, cmap="viridis", vmin=-0.3, vmax=1); axes[5].set_xticks([]); axes[5].set_yticks([])
    axes[5].set_title(f"null map (unrelated frame)\nconsensus shift dy {cons['dy']:+.0f}, dx {cons['dx']:+.0f} px; "
                      f"{cons['n_agree']}/{cons['n']} templates agree", fontsize=8)


def best_tpl(c):
    ag = [q for q in c["recs"] if abs(q["dy"] - c["dy"]) <= 5 and abs(q["dx"] - c["dx"]) <= 5]
    return max(ag or c["recs"], key=lambda z: z["peak"] - z["null"])


rows = [("ctrl", 1806, 1808, "err", "CONTROL Sep 24 good tip"),
        ("oct", 27, 28, "err", "Oct 22 KIGA 4.6, error"),
        ("oct", 27, 28, "S", "Oct 22 KIGA 4.6, Z (folded S)"),
        ("oct", 30, 31, "err", "Oct 22 KIGA 9, error"),
        ("oct", 23, 25, "err", "Oct 22 across gain 2.3 -> 4.6, error"),
        ("oct", 21, 22, "err", "Oct 22 KIGA 2.3, error")]
fig, axes = plt.subplots(len(rows), 6, figsize=(17, 3.15 * len(rows)),
                         gridspec_kw=dict(width_ratios=[1, 1, 0.6, 0.6, 1, 1]))
for k, (src_, a, b, ch, label) in enumerate(rows):
    if src_ == "ctrl":
        c = pair(a, b, "err", imgs=CTRL["err"], null=IM["err"][22]); A, B = CTRL["err"][a], CTRL["err"][b]; nul = IM["err"][22]
    else:
        c = R[(a, b)][ch]; A, B = IM[ch][a], IM[ch][b]; nul = NULL[ch]
    proof_row(axes[k], A, B, a, b, best_tpl(c), c, label, nul)
plt.tight_layout(pad=0.4); fig.savefig(os.path.join(OUT, "figD1_inset_proof.png"), dpi=72); plt.close(fig)

# long-range proof: template from #31 found in #25 (6 min of drift later?) at the chained prediction
def long_proof(a, b, ch):
    c = pair(a, b, ch)
    pred = [p for p in track if p[0] == b][0][2:4] - np.array([p for p in track if p[0] == a][0][2:4])
    return c, pred
lr = []
for a, b in ((25, 28), (25, 31), (21, 23), (17, 22)):
    for ch in ("err", "S"):
        c, pred = long_proof(a, b, ch)
        lr.append(dict(a=a, b=b, ch=ch, meas_dy=c["dy"], meas_dx=c["dx"], pred_dy=float(pred[0]), pred_dx=float(pred[1]),
                       agree=f"{c['n_agree']}/{c['n']}", peak=c["peak_agree"], null95=c["null_p95"]))
        print(f"long #{a}->#{b} {ch}: measured ({c['dy']:+.0f},{c['dx']:+.0f}) chained-track prediction "
              f"({pred[0]:+.0f},{pred[1]:+.0f})  agree {c['n_agree']}/{c['n']} pk {c['peak_agree']:.2f} null95 {c['null_p95']:.2f}")

# vector field + drift track figure
cons_pairs = list(zip(SW, SW[1:]))
fig, axes = plt.subplots(3, 5, figsize=(16, 11.4))
for k, (a, b) in enumerate(cons_pairs):
    ax = axes.flat[k]; r = R[(a, b)]; c = r["err"]
    show(ax, IM["err"][b])
    for q in c["recs"]:
        ok = abs(q["dy"] - c["dy"]) <= 5 and abs(q["dx"] - c["dx"]) <= 5
        cx, cy = q["x"] + PS / 2, q["y"] + PS / 2
        ax.annotate("", xy=(cx + q["dx"], cy + q["dy"]), xytext=(cx, cy),
                    arrowprops=dict(arrowstyle="->", color="cyan" if ok else "red", lw=1.6 if ok else 0.8))
    ax.text(4, 14, f"#{b}", color="white", fontsize=15, fontweight="bold",
            bbox=dict(facecolor="black", alpha=0.6, pad=2, lw=0))
    sg = lambda g: g.replace("tip check ", "")
    ax.set_title(f"shown: #{b} · pair #{a}→#{b} · KIGA {sg(r['ga'])}→{sg(r['gb'])}\n"
                 f"shift err {c['dy']:+.0f},{c['dx']:+.0f} · Z {r['S']['dy']:+.0f},{r['S']['dx']:+.0f} px\n{r['verdict']}",
                 fontsize=8.5, pad=4, color="#063" if r["verdict"].startswith("LOCKED") else ("#850" if r["verdict"].startswith("locked") else "#a00"))
for k in range(len(cons_pairs), 15): axes.flat[k].axis("off")
fig.subplots_adjust(left=0.01, right=0.99, top=0.94, bottom=0.01, wspace=0.10, hspace=0.30)
fig.savefig(os.path.join(OUT, "figD2_vectors.png"), dpi=80); plt.close(fig)

fig, ax = plt.subplots(1, 2, figsize=(12, 3.8))
tt = [p[1] for p in track]
ax[0].plot(tt, [p[2] for p in track], "o-", label="dy: rows (+ = content moves up the frame)")
ax[0].plot(tt, [p[3] for p in track], "s-", label="dx: columns (+ = content moves left)")
for p in track:
    ax[0].annotate(f"#{p[0]}", (p[1], p[2]), fontsize=6, xytext=(2, 4), textcoords="offset points")
    if p[4] == "gap": ax[0].plot(p[1], p[2], "x", color="red", ms=10, mew=2)
for i in SW:
    ax[0].axvspan(t(i) - t(SW[0]), t(i) - t(SW[0]) + 24.5, color={"tip check 1.14": "#999", "1.14": "#1f77b4", "2.3": "#2ca02c", "4.6": "#ff7f0e", "9": "#d62728"}[RUNG[i]], alpha=0.07)
ax[0].set_xlabel("s since #12"); ax[0].set_ylabel("cumulative content shift (px; 1 px = 0.117 nm)")
ax[0].legend(fontsize=7); ax[0].set_title("Accumulated stage drift (red x: pair did not lock, shift not added)", fontsize=9)
ax[1].scatter([q["pred_dy"] for q in chain], [q["meas_dy"] for q in chain], c=["#1f77b4" if q["ch"] == "err" else "#ff7f0e" for q in chain], s=18, label="dy")
ax[1].scatter([q["pred_dx"] for q in chain], [q["meas_dx"] for q in chain], marker="s", facecolors="none",
              edgecolors=["#1f77b4" if q["ch"] == "err" else "#ff7f0e" for q in chain], s=22, label="dx")
lim = [-80, 80]; ax[1].plot(lim, lim, "k--", lw=0.7); ax[1].set_xlim(lim); ax[1].set_ylim(lim)
ax[1].set_xlabel("predicted a→c = (a→b) + (b→c)  (px)"); ax[1].set_ylabel("measured a→c (px)")
ax[1].set_title("Chain consistency (blue err, orange S): points on the diagonal = real, self-consistent motion", fontsize=8)
plt.tight_layout(); fig.savefig(os.path.join(OUT, "figD3_track_chain.png"), dpi=90); plt.close(fig)

out = {"pairs": [{k: (v if k not in ("err", "S") else {kk: vv for kk, vv in v.items() if kk != "recs"}) for k, v in r.items()} for r in R.values()],
       "chain": chain, "track": [dict(sweep=p[0], t=p[1], dy=p[2], dx=p[3], status=p[4]) for p in track], "long": lr}
json.dump(out, open(os.path.join(OUT, "drift_metrics.json"), "w"), indent=1, default=float)
print("done")
