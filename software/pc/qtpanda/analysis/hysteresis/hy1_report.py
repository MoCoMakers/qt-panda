"""HY1 summary: figure + hy1_results.json from hy1_sweeps.json (hy1.py), the constant-height
profiles of Sep 24 #931/#932, and the simulator's hysteresis mapping."""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ["QTPANDA_SETTINGS"] = os.path.join(HERE, "scratch_settings.ini"); os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.join(HERE, "..", "sim")); sys.path.insert(0, os.path.join(HERE, "..", "..")); sys.path.insert(0, os.path.join(HERE, "..", "..", "replay"))
import numpy as np
from scipy.ndimage import gaussian_filter
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
import scan_sim as M
import sweep_player as sp

R = json.load(open(os.path.join(HERE, "hy1_sweeps.json")))


def cls(r):
    s = r["cc_share"]
    if s is None or (isinstance(s, float) and np.isnan(s)) or r["n_status"] < 20: return "unknown"
    return "CH" if s < 0.05 else ("CC" if s > 0.95 else "mixed")


def prof(r, ch):
    return np.array([np.nan if v is None else v for v in r[ch]["shifts"]], float)


u8 = (np.arange(8) + 0.5) / 8
groups = {
    "CC error, Sep 24 30 nm, 31 ms lines (#1572-#1586)": [r for r in R if r["day"] == "2026-Sep-24" and 1570 <= r["sweep"] <= 1590 and cls(r) == "CC" and r["e"] and r["e"].get("n_ok", 0) >= 6],
    "CC error, Oct 22 30 nm, 97 ms lines (#12, #23, #27)": [r for r in R if r["day"] == "2026-Oct-22" and cls(r) == "CC" and r["e"] and r["e"].get("n_ok", 0) >= 6],
    "CC Z, Sep 24 33 nm, 20-21 ms lines": [r for r in R if r["day"] == "2026-Sep-24" and abs((r["scan_nm"] or 0) - 33.0) < 0.1 and cls(r) == "CC" and r["z"] and r["z"].get("n_ok", 0) >= 6],
    "CC Z, Sep 24 8.9 nm, 7-8 ms lines": [r for r in R if r["day"] == "2026-Sep-24" and abs((r["scan_nm"] or 0) - 8.866) < 0.05 and cls(r) == "CC" and r["z"] and r["z"].get("n_ok", 0) >= 6 and 6.5 < r["line_period_ms"] < 8.5],
}
summary = {}
fig, ax = plt.subplots(1, 3, figsize=(17, 4.6))
for (name, g), col in zip(groups.items(), ("#d62728", "#ff7f0e", "#1f77b4", "#2ca02c")):
    if not g: continue
    ch = "e" if "error" in name else "z"
    P = np.array([prof(r, ch) for r in g]); med = np.nanmedian(P, 0)
    px = g[0]["px"]
    c = np.array([r[ch]["c"] for r in g]); a = np.array([r[ch]["a"] for r in g]); b = np.array([r[ch]["b"] for r in g])
    summary[name] = dict(n=len(g), px_per_direction=px, scan_nm=g[0]["scan_nm"], line_period_ms=float(np.median([r["line_period_ms"] for r in g])),
                         median_profile_px=[None if np.isnan(v) else float(v) for v in med],
                         dome_c_px_median=float(np.median(c)), dome_c_px_iqr=[float(np.percentile(c, 25)), float(np.percentile(c, 75))],
                         const_a_px_median=float(np.median(a)), linear_b_px_median=float(np.median(b)),
                         dome_pct_of_span=float(np.median(c) / px * 100), sweeps=[f"{r['day']}#{r['sweep']}" for r in g])
    ax[0].plot(u8, med / px * 100, "o-", color=col, label=f"{name} (n={len(g)})")
ax[0].axhline(0, color="k", lw=0.5); ax[0].set_xlabel("position along the line (0 = left turnaround)")
ax[0].set_ylabel("retrace - trace shift (% of line width)"); ax[0].set_title("Constant current: median shift profiles", fontsize=10)
ax[0].legend(fontsize=7)

# constant height #931 / #932 (lag-free)
D = sp.DayData("2026-Sep-24")
def seg_profile(T, R_, nseg, maxlag=10):
    T = gaussian_filter(T - T.mean(0), 1); R_ = gaussian_filter(R_ - R_.mean(0), 1)
    W = T.shape[1]; sw = W // nseg; out = []
    for k in range(nseg):
        a0 = T[:, k * sw:(k + 1) * sw]; b0 = R_[:, k * sw:(k + 1) * sw]; cc = []
        for L in range(-maxlag, maxlag + 1):
            a = a0[:, max(0, -L):sw - max(0, L)]; b = b0[:, max(0, L):sw - max(0, -L)]
            a = a - a.mean(1, keepdims=True); b = b - b.mean(1, keepdims=True)
            cc.append(float((a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum())))
        cc = np.array(cc); i = int(np.argmax(cc)); off = 0.0
        if 0 < i < len(cc) - 1:
            d = cc[i - 1] - 2 * cc[i] + cc[i + 1]; off = 0.5 * (cc[i - 1] - cc[i + 1]) / d if d else 0.0
        out.append((None if i in (0, len(cc) - 1) else float(i - maxlag + off), float(cc[i])))
    return out
ch_prof = {}
for i, col in ((931, "#9467bd"), (932, "#8c564b")):
    T = D.image(i, "e_trace")[0]; Rr = D.image(i, "e_retrace")[0]
    T = np.nan_to_num(T, nan=np.nanmean(T)); Rr = np.nan_to_num(Rr, nan=np.nanmean(Rr))
    for nseg, mk in ((3, "s--"), (4, "o-")):
        p = seg_profile(T, Rr, nseg); ch_prof[f"#{i}/{nseg}seg"] = p
        uu = (np.arange(nseg) + 0.5) / nseg
        ax[1].plot(uu, [np.nan if s is None else s / T.shape[1] * 100 for s, c in p], mk, color=col, label=f"#{i}, {nseg} segments")
ax[1].axhline(0, color="k", lw=0.5); ax[1].set_ylim(-8, 8)
ax[1].set_title("Constant height (no loop lag): Sep 24 #931/#932, 30 nm, 128 px", fontsize=10)
ax[1].set_xlabel("position along the line"); ax[1].set_ylabel("% of line width"); ax[1].legend(fontsize=7)

# simulator mapping
W = 256; xs = np.concatenate([np.linspace(0, W, 2000), np.linspace(W, 0, 2000)] * 4)
mapping = {}
for hf, col in ((0.005, "#2ca02c"), (0.01, "#1f77b4"), (0.02, "#ff7f0e"), (0.05, "#d62728")):
    y = M._pi(xs, hf * W, 8)[-4000:]; sep = (y[2000:][::-1] - y[:2000]) / W * 100
    mapping[hf] = dict(mid_pct=float(sep[1000]), end_pct=float(sep[20]))
    ax[2].plot(np.linspace(0, 1, 2000), sep, color=col, label=f"hyst_frac {hf}")
ax[2].set_title("Simulator: trace/retrace separation for hyst_frac", fontsize=10)
ax[2].set_xlabel("position along the line"); ax[2].set_ylabel("% of line width"); ax[2].legend(fontsize=7)
plt.tight_layout(); fig.savefig(os.path.join(HERE, "hy1_profiles.png"), dpi=80)

out = dict(groups=summary, constant_height_profiles=ch_prof, simulator_mapping=mapping,
           classification_counts={k: v for k, v in __import__("collections").Counter(cls(r) for r in R).items()},
           recommendation=dict(hyst_frac_central=0.005, hyst_frac_range=[0.0, 0.02], previous_assumption=0.05,
                               basis="constant-height #931 flat within ~0.4 px (0.3% of span); #932 <= ~2-3%; CC Z at 33 nm dome ~0 (IQR <= 1.3%); CC error-channel domes scale with line speed (time delay / loop lag, not hysteresis)"))
json.dump(out, open(os.path.join(HERE, "hy1_results.json"), "w"), indent=1)
print(json.dumps({k: {kk: v[kk] for kk in ("n", "line_period_ms", "dome_c_px_median", "dome_pct_of_span", "const_a_px_median")} for k, v in summary.items()}, indent=1))
print(mapping)
