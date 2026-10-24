"""fiducial_drift — automatic drift measurement by fiducial hopping (no starting feature needed).

For a run of sweeps with the same scan geometry:
  1. every sweep is cut into a grid of 96 x 96 px candidate fiducials (stride 32);
  2. each candidate is searched for in the other sweep of a pair (normalized cross-
     correlation), separately in the error and Z channels, and scored against a null
     (the same search in a flipped frame);
  3. a pair locks when the fiducials agreeing on one displacement form a consensus in each
     channel and the two channels' consensuses agree (independent confirmation);
  4. pairs are consecutive sweeps plus skip-one pairs (same Y direction), so the
     displacements over-determine the path and chain-consistency can be checked;
  5. fit  displacement(a->b) = v*(t_b - t_a) + offset*(down_b - down_a) + jump*(restarts between)
  6. the example reference: the strongest supporting fiducial, followed from pair to pair;
     when it leaves scope or stops supporting the consensus, hop to the supporting
     fiducial nearest to it (fiducial hopping).

Displacement sign: where a feature moved within the frame, new - old position (rows, cols).
Usage:  python fiducial_drift.py <day> <first_sweep> <last_sweep>
"""
import os, sys, json, argparse
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, "C:/Users/enact/Projects/qt-panda/software/pc/qtpanda/replay")
sys.path.insert(0, "C:/Users/enact/Projects/qt-panda/software/pc/qtpanda")
import numpy as np
from scipy import ndimage as ndi
from scipy.signal import fftconvolve
import sweep_player as sp

TPL, STRIDE, TOL, AGREE = 96, 32, 5, 8


def fill_rows(a):
    a = a.astype(float).copy(); bad = np.isnan(a).any(1); good = np.flatnonzero(~bad)
    for r in np.flatnonzero(bad): a[r] = a[good[np.argmin(np.abs(good - r))]]
    return a


def rowlev(a):
    x = np.arange(a.shape[1]); A = np.vstack([x, np.ones_like(x)]).T
    c, *_ = np.linalg.lstsq(A, a.T, rcond=None); return a - (A @ c).T


def prep(a):
    a = np.clip(a, *np.percentile(a, [2, 98])); return ndi.gaussian_filter(a, 1.0)


def ncc_map(img, tpl):
    t = tpl - tpl.mean(); tn = np.sqrt((t * t).sum()) + 1e-12
    num = fftconvolve(img, t[::-1, ::-1], mode="valid"); ones = np.ones_like(tpl)
    s1 = fftconvolve(img, ones, mode="valid"); s2 = fftconvolve(img * img, ones, mode="valid")
    return num / (np.sqrt(np.clip(s2 - s1 * s1 / tpl.size, 1e-12, None)) * tn)


def match_pair(A, B):
    """fiducials cut from A (older), found in B (newer). Returns list of dicts."""
    H, W = A.shape; out = []; Bf = B[::-1, ::-1]
    for y in range(0, H - TPL + 1, STRIDE):
        for x in range(0, W - TPL + 1, STRIDE):
            tpl = A[y:y + TPL, x:x + TPL]
            if tpl.std() < 0.35 * A.std(): continue           # featureless: not a fiducial
            m = ncc_map(B, tpl); py, px = np.unravel_index(np.argmax(m), m.shape)
            out.append(dict(y=y, x=x, ny=int(py), nx=int(px), dy=int(py - y), dx=int(px - x),
                            peak=float(m[py, px]), null=float(ncc_map(Bf, tpl).max())))
    return out


def consensus(recs):
    if not recs: return None
    best = []
    for r in recs:
        sup = [q for q in recs if abs(q["dy"] - r["dy"]) <= TOL and abs(q["dx"] - r["dx"]) <= TOL]
        if len(sup) > len(best): best = sup
    dy = float(np.median([q["dy"] for q in best])); dx = float(np.median([q["dx"] for q in best]))
    agree = [q for q in recs if abs(q["dy"] - dy) <= TOL and abs(q["dx"] - dx) <= TOL]
    return dict(dy=dy, dx=dx, n=len(recs), n_agree=len(agree), agree=agree,
                beat_null=float(np.mean([q["peak"] > q["null"] for q in agree])))


def run(day, first, last, outdir):
    D = sp.DayData(day)
    idx = [i for i in range(first, last + 1) if D.sweeps[i][2]["lines"] >= 0.95 * D.sweeps[i][1]["image_height"]]
    E, S = {}, {}
    for i in idx:
        E[i] = prep(rowlev(fill_rows(D.image(i, "e_trace")[0])))
        S[i] = prep((rowlev(fill_rows(D.image(i, "z_trace")[0])) + rowlev(fill_rows(D.image(i, "z_retrace")[0]))) / 2)
    t = {i: (D.sweeps[i][2]["t_start"] + D.sweeps[i][2]["t_end"]) / 2 for i in idx}
    down = {i: 1.0 if D.sweeps[i][2]["dir"] == "down" else 0.0 for i in idx}
    restarts = {}; k = 0
    for a, b in zip(idx, idx[1:]):
        restarts[a] = k
        if D.sweeps[a][0] != D.sweeps[b][0] or t[b] - t[a] > 1.6 * (D.sweeps[b][2]["t_end"] - D.sweeps[b][2]["t_start"]): k += 1
    restarts[idx[-1]] = k
    plist = list(zip(idx, idx[1:])) + [(a, c) for a, c in zip(idx, idx[2:]) if down[a] == down[c]]
    pairs = []
    for a, b in plist:
        ce, cs = consensus(match_pair(E[a], E[b])), consensus(match_pair(S[a], S[b]))
        joint = ce and cs and abs(ce["dy"] - cs["dy"]) <= AGREE and abs(ce["dx"] - cs["dx"]) <= AGREE \
            and ce["n_agree"] >= 5 and cs["n_agree"] >= 5
        pairs.append(dict(a=a, b=b, dt=t[b] - t[a], consecutive=(idx.index(b) == idx.index(a) + 1),
                          restarts=restarts[b] - restarts[a], ddown=down[b] - down[a],
                          err=dict(dy=ce["dy"], dx=ce["dx"], agree=f"{ce['n_agree']}/{ce['n']}"),
                          Z=dict(dy=cs["dy"], dx=cs["dx"], agree=f"{cs['n_agree']}/{cs['n']}"),
                          locked=bool(joint), dy=(ce["dy"] + cs["dy"]) / 2 if joint else None,
                          dx=(ce["dx"] + cs["dx"]) / 2 if joint else None, _fid=ce["agree"] if joint else []))
    L = [p for p in pairs if p["locked"]]
    fit = {}
    if len(L) >= 4:
        keep = np.ones(len(L), bool)
        A = np.array([[p["dt"], p["ddown"], p["restarts"]] for p in L])
        Y = np.array([[p["dy"], p["dx"]] for p in L])
        for _ in range(5):                                   # robust: drop pairs that disagree with the rest
            C, *_ = np.linalg.lstsq(A[keep], Y[keep], rcond=None)
            r = np.linalg.norm(A @ C - Y, axis=1)
            new = r <= max(6.0, 3.0 * np.median(r[keep]))
            if (new == keep).all(): break
            keep = new
        for j, p in enumerate(L): p["used_in_fit"] = bool(keep[j]); p["fit_residual_px"] = float(r[j])
        has_off, has_jump = bool(np.any(A[keep, 1] != 0)), bool(np.any(A[keep, 2] != 0))
        for k_, name in ((0, "y"), (1, "x")):
            fit[name] = dict(drift_px_s=float(C[0, k_]),
                             down_offset_px=float(C[1, k_]) if has_off else None,     # None = no up<->down pair locked
                             restart_jump_px=float(C[2, k_]) if has_jump else None,  # None = no restart inside the run
                             rms_px=float(np.sqrt(np.mean((A[keep] @ C[:, k_] - Y[keep, k_]) ** 2))))
        fit["pairs_used"] = int(keep.sum()); fit["pairs_rejected"] = [(L[j]["a"], L[j]["b"]) for j in np.flatnonzero(~keep)]
    # chain consistency
    chain_chk = []
    for a, b, c in zip(idx, idx[1:], idx[2:]):
        P = {(p["a"], p["b"]): p for p in L}
        if (a, b) in P and (b, c) in P and (a, c) in P:
            pr = np.array([P[(a, b)]["dy"] + P[(b, c)]["dy"], P[(a, b)]["dx"] + P[(b, c)]["dx"]])
            chain_chk.append(dict(a=a, b=b, c=c, miss_px=float(np.hypot(*(pr - [P[(a, c)]["dy"], P[(a, c)]["dx"]])))))
    # example reference with hopping: walk forward through locked pairs, nearest in time first
    ref = []; cur = None; lockd = {}
    for p in pairs:
        if p["locked"] and p.get("used_in_fit", True): lockd.setdefault(p["a"], []).append(p)
    walk = []; s_ = idx[0]
    while True:
        nxt = sorted(lockd.get(s_, []), key=lambda q: q["b"])
        if nxt: walk.append(nxt[0]); s_ = nxt[0]["b"]; continue
        later = [k for k in idx if k > s_ and k in lockd]
        if not later: break
        walk.append(dict(a=s_, b=later[0], locked=False)); s_ = later[0]
    for p in walk:
        if not p["locked"]: cur = None; ref.append(dict(a=p["a"], b=p["b"], hop="chain broken")); continue
        fid = p["_fid"]
        if cur is not None:
            near = min(fid, key=lambda q: np.hypot(q["y"] - cur[0], q["x"] - cur[1]))
            hop = np.hypot(near["y"] - cur[0], near["x"] - cur[1]) > STRIDE
        else:
            near = max(fid, key=lambda q: q["peak"] - q["null"]); hop = True
        ref.append(dict(a=p["a"], b=p["b"], y=near["y"], x=near["x"], ny=near["ny"], nx=near["nx"],
                        peak=near["peak"], null=near["null"], hop=("start" if cur is None else ("hop" if hop else "same"))))
        cur = (near["ny"], near["nx"])
    for p in pairs: p.pop("_fid", None)
    res = dict(day=day, sweeps=idx, pairs=pairs, fit=fit, chain_check=chain_chk, reference=ref,
               scan_size_nm=D.sweeps[idx[0]][2].get("scan_size_nm"), pixels=int(E[idx[0]].shape[1]))
    os.makedirs(outdir, exist_ok=True)
    tag = f"{day}_{first}-{last}"
    json.dump(res, open(os.path.join(outdir, f"fiducial_drift_{tag}.json"), "w"), indent=1, default=float)
    figure(D, E, res, os.path.join(outdir, f"fiducial_drift_{tag}.png"))
    return res


def figure(D, E, res, path):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    idx = res["sweeps"]; n = len(idx); cols = min(n, 6); rows = (n + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(3.1 * cols, 3.5 * rows), squeeze=False)
    colors = ["#39ff14", "#00e5ff", "#ff4fd8", "#ffd400", "#ff7a00", "#ffffff"]
    seg = 0; boxes = {}
    for r in res["reference"]:
        if r["hop"] in ("start", "hop", "chain broken"): seg += 1
        if "y" in r:
            boxes.setdefault(r["a"], []).append((r["y"], r["x"], colors[seg % len(colors)], r["hop"]))
            boxes.setdefault(r["b"], []).append((r["ny"], r["nx"], colors[seg % len(colors)], ""))
    for k, i in enumerate(idx):
        ax = axes.flat[k]; a = E[i]
        ax.imshow(a, cmap="inferno", vmin=np.percentile(a, 1), vmax=np.percentile(a, 99)); ax.set_xticks([]); ax.set_yticks([])
        for (y, x, col, hop) in boxes.get(i, []):
            ax.add_patch(plt.Rectangle((x, y), TPL, TPL, fill=False, ec=col, lw=2, ls="-" if hop != "hop" else "--"))
        p = next((q for q in res["reference"] if q["b"] == i and "y" in q), None)
        step = "" if p is None else f"from #{p['a']}: {p['ny'] - p['y']:+d},{p['nx'] - p['x']:+d} px"
        ax.set_title(f"#{i} {'▲' if D.sweeps[i][2]['dir'] == 'up' else '▼'}  {step}", fontsize=8)
    for k in range(n, rows * cols): axes.flat[k].axis("off")
    fy, fx = res["fit"].get("y"), res["fit"].get("x")
    f = lambda v: "n/a" if v is None else f"{v:+.1f}"
    ftxt = "not enough locked pairs to fit" if not fy else (f"drift {fy['drift_px_s']:+.3f} px/s rows, {fx['drift_px_s']:+.3f} px/s cols · "
                                                            f"down-sweep offset {f(fy['down_offset_px'])} px · restart jump {f(fy['restart_jump_px'])}/{f(fx['restart_jump_px'])} px · "
                                                            f"rms {fy['rms_px']:.1f}/{fx['rms_px']:.1f} px")
    fig.suptitle(f"{res['day']} #{idx[0]}–#{idx[-1]} · example drift reference: coloured square followed sweep to sweep (colour changes at a hop) · {ftxt}", fontsize=9)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.9, bottom=0.01, wspace=0.05, hspace=0.2)
    fig.savefig(path, dpi=80); plt.close(fig)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("day"); ap.add_argument("first", type=int); ap.add_argument("last", type=int)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "morph_report"))
    a = ap.parse_args(); r = run(a.day, a.first, a.last, a.out)
    for p in r["pairs"]:
        print(f"#{p['a']}->#{p['b']} {'consec' if p['consecutive'] else 'skip1 '} restarts {p['restarts']} dt {p['dt']:5.1f}s  "
              f"err {p['err']['dy']:+.0f},{p['err']['dx']:+.0f} ({p['err']['agree']})  Z {p['Z']['dy']:+.0f},{p['Z']['dx']:+.0f} ({p['Z']['agree']})  "
              + (f"LOCK ({p['dy']:+.1f},{p['dx']:+.1f})" if p["locked"] else "no lock"))
    print("fit:", json.dumps(r["fit"])); print("chain check:", [(c['a'], c['b'], c['c'], round(c['miss_px'], 1)) for c in r["chain_check"]])
    print("reference:", [(q['a'], q['b'], q['hop']) for q in r["reference"]])
