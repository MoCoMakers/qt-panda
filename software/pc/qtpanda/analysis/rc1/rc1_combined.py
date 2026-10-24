"""RC1: does the combined height (tip height - gap(current)) repeat better between sweeps than Z
alone or the error channel alone, on EXISTING v1 recordings?  (DECISIONS D30, SIMULATION.md §2)

Per pixel (v1 frames carry the per-pixel MEAN z_pos and MEAN err):
  error   err = setpointLog - logTable[|adc|]           (log-table units, LOG_K per ln unit)
  current ln(|adc|+1) ~ (setpointLog - err) / LOG_K      (assumption A5: mean of logs ~ log of current)
  gap     (ln(V/R_c) - ln I) / (2 kappa)                 kappa 1.025 / Å, R_c 12.9 kOhm, I = counts * 3.125 pA
  tip     -z * g                                         g = 0.00063 Å per z_pos unit (loop estimate)
  height  tip - gap                                      (peaks up)
Variants: masked (drop pixels whose implied |adc| <= 64 counts = no-current level, or >= 32000 =
clipped) and preamp-inverted (first-order, tau 400 µs, along each line's time order; pixel level).
Channels are line-levelled (offset + slope per line) and folded: (trace + retrace) / 2.
Repeat = Pearson correlation of neighbouring same-direction sweeps after alignment (Sep 24: phase
correlation on the error channel, the same shift for every channel; Oct 22: report v2's line-by-line
drift registration).  Up/down = neighbouring up vs down sweep, aligned the same way.
"""
import os, sys, json, math
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault("QTPANDA_SETTINGS", os.path.join(HERE, "_scratch_settings.ini"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
QT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(QT, "replay")); sys.path.insert(0, QT)
import numpy as np
from scipy import ndimage as ndi
import sweep_player as sp

LOG_K = (2 ** 19 - 1) / math.log(2 ** 15 + 1)
KAPPA, RC, PPC, G = 1.025, 12906.0, 3.125e-12, 0.00063
TAU = 400e-6


def fill_rows(a):
    a = a.astype(float).copy(); bad = np.isnan(a).any(1); good = np.flatnonzero(~bad)
    for r in np.flatnonzero(bad): a[r] = a[good[np.argmin(np.abs(good - r))]]
    return a


def rowlev(a):
    out = a.copy(); x = np.arange(a.shape[1])
    for r in range(a.shape[0]):
        m = np.isfinite(a[r])
        if m.sum() > 3:
            c = np.polyfit(x[m], a[r, m], 1); out[r] = a[r] - np.polyval(c, x)
    return out


def counts_from_err(err, sp_counts):
    spl = LOG_K * math.log(sp_counts + 1)
    return np.exp((spl - err) / LOG_K) - 1.0


def preamp_invert(cnt, pix_dt, forward=True):
    """first-order inversion along time order, per line (rows); cnt in counts."""
    a = 1 - math.exp(-pix_dt / TAU)
    c = cnt if forward else cnt[:, ::-1]
    inv = c.copy(); inv[:, 1:] = (c[:, 1:] - (1 - a) * c[:, :-1]) / a
    return inv if forward else inv[:, ::-1]


def channels(D, i, sp_counts, bias_v):
    s = D.sweeps[i][2]
    zt, zr = fill_rows(D.image(i, "z_trace")[0]), fill_rows(D.image(i, "z_retrace")[0])
    et, er = fill_rows(D.image(i, "e_trace")[0]), fill_rows(D.image(i, "e_retrace")[0])
    lines = zt.shape[0]
    pix_dt = (s["t_end"] - s["t_start"]) / lines / (2 * zt.shape[1])
    lnVR = math.log(abs(bias_v) / RC)
    out = {}
    def comb(z, cnt, mask):
        I = np.clip(cnt, 1e-3, None) * PPC
        h = -z * G - (lnVR - np.log(I)) / (2 * KAPPA)
        return np.where(mask, h, np.nan)
    halves = {}
    for nm, z, e, fwd in (("t", zt, et, True), ("r", zr, er, False)):
        cnt = counts_from_err(e, sp_counts)
        ok = (cnt > 64) & (cnt < 32000)
        inv = preamp_invert(cnt, pix_dt, forward=fwd)
        okinv = ok & (inv > 64) & (inv < 32000)
        halves[nm] = dict(Z=-z, Err=-e, Combined=comb(z, cnt, np.ones_like(ok)),
                          Combined_masked=comb(z, cnt, ok), Combined_preamp_inv=comb(z, inv, okinv),
                          usable=ok.mean())
    for k in ("Z", "Err", "Combined", "Combined_masked", "Combined_preamp_inv"):
        a, b = rowlev(halves["t"][k]), rowlev(halves["r"][k])
        out[k] = np.nanmean(np.stack([a, b]), 0)
        # same, with the line-locked profile (mean over rows of each column) removed: a pattern fixed
        # in the scan frame repeats whether or not it is surface (Oct 15 report: 78-98% of variance)
        out[k + "_noprofile"] = out[k] - np.nanmean(out[k], axis=0, keepdims=True)
    out["_usable"] = float((halves["t"]["usable"] + halves["r"]["usable"]) / 2)
    # size of the two terms of the combined height (folded, line-levelled), in Å
    zt_ = rowlev(-zt * G); gap_t = rowlev(halves["t"]["Combined"] + zt * G)
    out["_tip_rms_A"] = float(np.nanstd(zt_)); out["_gap_rms_A"] = float(np.nanstd(gap_t))
    return out


def clip(a):
    f = a[np.isfinite(a)]
    lo, hi = np.percentile(f, [1, 99]) if f.size else (0, 1)
    return np.clip(a, lo, hi)


def corr(a, b):
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < 500: return float("nan")
    return float(np.corrcoef(clip(a)[m], clip(b)[m])[0, 1])


def shift_pc(a, b):
    a = np.nan_to_num(a - np.nanmean(a)); b = np.nan_to_num(b - np.nanmean(b))
    F = np.fft.fft2(a) * np.conj(np.fft.fft2(b))
    c = np.fft.ifft2(F / (np.abs(F) + 1e-9)).real
    dy, dx = np.unravel_index(np.argmax(c), c.shape); H, W = a.shape
    return (dy if dy <= H // 2 else dy - H), (dx if dx <= W // 2 else dx - W)


def overlap(a, b, dy, dx):
    H, W = a.shape
    A = a[max(0, dy):H + min(0, dy), max(0, dx):W + min(0, dx)]
    B = b[max(0, -dy):H + min(0, -dy), max(0, -dx):W + min(0, -dx)]
    return A, B


KEYS = ["Z", "Err", "Combined", "Combined_masked", "Combined_preamp_inv",
        "Z_noprofile", "Err_noprofile", "Combined_noprofile"]


def sep24(ids, sp_counts=320, bias=-0.0496):
    D = sp.DayData("2026-Sep-24")
    ids = [i for i in ids if not D.sweeps[i][2]["partial"]]
    C = {i: channels(D, i, sp_counts, bias) for i in ids}
    dirs = {i: D.sweeps[i][2]["dir"] for i in ids}
    rep = {k: [] for k in KEYS}; ud = {k: [] for k in KEYS}; usable = [C[i]["_usable"] for i in ids]
    for a in ids:
        for b in ids:
            if b <= a: continue
            same = dirs[a] == dirs[b]
            if same and b != min([x for x in ids if x > a and dirs[x] == dirs[a]], default=-1): continue
            if not same and b != a + 1: continue
            dy, dx = shift_pc(C[a]["Err"], C[b]["Err"])
            if abs(dy) > 60 or abs(dx) > 60: continue
            for k in KEYS:
                A, B = overlap(C[a][k], C[b][k], dy, dx)
                (rep if same else ud)[k].append(corr(A, B))
    return C, rep, ud, usable


def oct22():
    SP_DIR = "C:/Users/enact/AppData/Local/Temp/claude/C--Users-enact-Projects-qt-panda/817c62e4-40fb-43d6-a2a9-c40c37909d37/scratchpad"
    sys.path.insert(0, SP_DIR)
    import v2_core as V
    D = V.D
    C = {i: channels(D, i, 160, -0.0496) for i in V.SEQ}
    R = {i: {k: V.register(np.nan_to_num(C[i][k], nan=np.nan), i, True) for k in KEYS} for i in V.SEQ}
    rep = {k: [] for k in KEYS}; ud = {k: [] for k in KEYS}
    for a, b in zip(V.SEQ, V.SEQ[2:]):
        if V.S_(a)["dir"] != V.S_(b)["dir"] or V.RUNG[a] != V.RUNG[b]: continue
        for k in KEYS: rep[k].append(corr(R[a][k], R[b][k]))
    for a, b in zip(V.SEQ, V.SEQ[1:]):
        if V.RUNG[a] != V.RUNG[b]: continue
        for k in KEYS: ud[k].append(corr(R[a][k], R[b][k]))
    return C, rep, ud, [C[i]["_usable"] for i in V.SEQ]


def summ(d):
    return {k: dict(median=float(np.nanmedian(v)) if v else None, min=float(np.nanmin(v)) if v else None,
                    max=float(np.nanmax(v)) if v else None, n=len(v)) for k, v in d.items()}


if __name__ == "__main__":
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    res = {}; figs = {}
    for name, fn in (("Sep 24 #1802-#1812 (27.1 nm)", lambda: sep24(range(1802, 1813))),
                     ("Sep 24 #1586-#1599 (24.8 nm)", lambda: sep24(range(1586, 1600))),
                     ("Oct 22 #20-#31 (30 nm, drift-registered)", oct22)):
        C, rep, ud, usable = fn()
        res[name] = dict(repeat=summ(rep), updown=summ(ud), usable_median=float(np.median(usable)),
                         tip_rms_A=float(np.median([C[i]["_tip_rms_A"] for i in C])), gap_rms_A=float(np.median([C[i]["_gap_rms_A"] for i in C])))
        figs[name] = C
        print(name, "usable %.0f%%" % (100 * np.median(usable)), "| tip-term rms %.3f A, gap-term rms %.3f A" % (res[name]["tip_rms_A"], res[name]["gap_rms_A"]))
        for k in KEYS:
            print(f"   {k:20s} repeat median {res[name]['repeat'][k]['median']}  up/down median {res[name]['updown'][k]['median']}")
    json.dump(res, open(os.path.join(HERE, "rc1_results.json"), "w"), indent=1)
    # figure 1: channels for one sweep per data set
    fig, ax = plt.subplots(3, 5, figsize=(16, 9.6))
    for r, (name, C) in enumerate(figs.items()):
        i = sorted(C)[2]
        for c, k in enumerate(KEYS[:5]):
            a = C[i][k]; f = a[np.isfinite(a)]
            ax[r, c].imshow(a, cmap="inferno", vmin=np.percentile(f, 1), vmax=np.percentile(f, 99))
            ax[r, c].set_xticks([]); ax[r, c].set_yticks([])
            ax[r, c].set_title(f"{k}\n{name.split('(')[0]}#{i}", fontsize=8)
    plt.tight_layout(); fig.savefig(os.path.join(HERE, "rc1_channels.png"), dpi=60); plt.close(fig)
    # figure 2: repeat bars
    fig, ax = plt.subplots(1, 2, figsize=(13, 4))
    w = 0.1; xs = np.arange(len(res))
    for j, k in enumerate(KEYS):
        ax[0].bar(xs + j * w, [res[n]["repeat"][k]["median"] or 0 for n in res], w, label=k)
        ax[1].bar(xs + j * w, [res[n]["updown"][k]["median"] or 0 for n in res], w, label=k)
    for a_, t in zip(ax, ("same-direction repeat (median)", "up/down agreement (median)")):
        a_.set_xticks(xs + 3.5 * w); a_.set_xticklabels([n.split(" (")[0] for n in res], fontsize=8); a_.set_title(t); a_.axhline(0, color="k", lw=0.5)
    ax[0].legend(fontsize=7)
    plt.tight_layout(); fig.savefig(os.path.join(HERE, "rc1_repeat.png"), dpi=70)
