"""HY1: fast-axis (X) piezo hysteresis from existing recordings.

For every full sweep: classify feedback state from the 200 Hz status CSV (share of samples with
is_const_current = 1 during the sweep), then measure the trace-vs-retrace shift as a function of X.
Each line is split into SEG segments; per segment the cross-correlation of the line-levelled trace and
retrace (retrace already in X order) is summed over all rows, and its peak (parabolic sub-pixel) is
the shift there.  Fit shift(u) = a + b*u + c*dome(u), u = x/W in [0, 1], dome = 4u(1-u):
  a  constant shift  -> lag / delay (preamp, loop)
  b  linear          -> scale mismatch between directions
  c  dome amplitude  -> hysteresis signature (largest mid-line, zero at the turnarounds)
Shift sign: + = retrace features sit at larger X than trace features.
Outputs (this folder): hy1_results.json, hy1_sweeps.csv, figures.
"""
import os, sys, json, glob, csv
os.environ["QT_QPA_PLATFORM"] = "offscreen"
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ["QTPANDA_SETTINGS"] = os.path.join(HERE, "scratch_settings.ini")
QT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(QT, "replay")); sys.path.insert(0, QT)
import numpy as np
import sweep_player as sp

SEG = 8
MAXLAG = 16
DAYS = ["2026-Sep-17", "2026-Sep-24", "2026-Oct-08", "2026-Oct-22"]


def fill_rows(a):
    a = a.astype(float).copy(); bad = np.isnan(a).any(1); good = np.flatnonzero(~bad)
    if len(good) == 0: return None
    for r in np.flatnonzero(bad): a[r] = a[good[np.argmin(np.abs(good - r))]]
    return a


def rowlev(a):
    x = np.arange(a.shape[1]); A = np.vstack([x, np.ones_like(x)]).T
    c, *_ = np.linalg.lstsq(A, a.T, rcond=None); return a - (A @ c).T


def load_status(folder):
    out = []
    for f in sorted(glob.glob(os.path.join(folder, "image_stability_*.csv"))):
        base = os.path.basename(f)
        try:
            t0 = int(base.split("_")[2].split("_")[0]) / 1000.0
        except Exception:
            continue
        try:
            d = np.genfromtxt(f, delimiter=",", skip_header=1, usecols=(0, 2, 8), invalid_raise=False)
        except Exception:
            continue
        if d.ndim != 2 or len(d) == 0: continue
        out.append((t0 + d[:, 0], d[:, 1], d[:, 2]))
    return out


def cc_share(status, t_start, t_end):
    v = []
    for t, adc, cc in status:
        m = (t >= t_start) & (t <= t_end)
        if m.any(): v.append(cc[m])
    if not v: return np.nan, 0
    v = np.concatenate(v)
    return float(np.mean(v > 0.5)), len(v)


def _detrend_rows(a):
    x = np.arange(a.shape[1]); A = np.vstack([x, np.ones_like(x)]).T
    c, *_ = np.linalg.lstsq(A, a.T, rcond=None); return a - (A @ c).T


def prep(img):
    """Remove the line-locked profile (the repeated lag pattern, Oct 15 report: 78-98% of variance)
    so only row-varying structure (surface) is correlated; light smoothing."""
    from scipy.ndimage import gaussian_filter
    a = img - img.mean(0, keepdims=True)
    return gaussian_filter(a, 1.0)


def seg_shifts(T, R):
    """Per-segment shift (px) of retrace relative to trace, summed cross-correlation over rows.
    A peak at the search limit is rejected (NaN)."""
    T, R = prep(T), prep(R)
    H, W = T.shape; sw = W // SEG
    shifts, quals = [], []
    for k in range(SEG):
        a = _detrend_rows(T[:, k * sw:(k + 1) * sw]); b = _detrend_rows(R[:, k * sw:(k + 1) * sw])
        lags = np.arange(-MAXLAG, MAXLAG + 1); cc = np.zeros(len(lags))
        for j, L in enumerate(lags):
            if L >= 0:
                x, y = a[:, :sw - L], b[:, L:]
            else:
                x, y = a[:, -L:], b[:, :sw + L]
            num = (x * y).sum(); den = np.sqrt((x * x).sum() * (y * y).sum()) + 1e-12
            cc[j] = num / den
        i = int(np.argmax(cc))
        if 0 < i < len(cc) - 1:
            d = cc[i - 1] - 2 * cc[i] + cc[i + 1]
            off = 0.5 * (cc[i - 1] - cc[i + 1]) / d if d != 0 else 0.0
        else:
            off = 0.0
        if i in (0, len(cc) - 1) or abs(lags[i]) >= MAXLAG - 1:
            shifts.append(np.nan); quals.append(0.0)
        else:
            shifts.append(float(lags[i] + off)); quals.append(float(cc[i]))
    return np.array(shifts), np.array(quals)


def fit(shifts, quals, W):
    u = (np.arange(SEG) + 0.5) / SEG
    ok = np.isfinite(shifts) & (quals > 0.3)
    if ok.sum() < 5:
        return dict(a=np.nan, b=np.nan, c=np.nan, resid_rms=np.nan, n_ok=int(ok.sum()))
    shifts = np.where(ok, shifts, 0.0)
    w = np.where(ok, np.clip(quals, 0, 1) ** 2, 0.0)
    A = np.c_[np.ones(SEG), u, 4 * u * (1 - u)]
    Aw = A * w[:, None]; c, *_ = np.linalg.lstsq(Aw, shifts * w, rcond=None)
    res = shifts - A @ c
    return dict(a=float(c[0]), b=float(c[1]), c=float(c[2]), resid_rms=float(np.sqrt(np.average(res ** 2, weights=w + 1e-9))), n_ok=int(ok.sum()))


def main():
    rows = []
    for day in DAYS:
        try:
            D = sp.DayData(day)
        except Exception as e:
            print(day, "load failed:", e); continue
        status = load_status(D.folder)
        n = len(D.sweeps)
        for i in range(n):
            fp, idx, s = D.sweeps[i]
            if s.get("partial"): continue
            try:
                recs = D.records(fp)[s["first_record"]:s["last_record"] + 1]
                if len(recs) < 32: continue
                lt = np.array([r[0] for r in recs]); line_period = (lt[-1] - lt[0]) / max(1, len(lt) - 1)
                share, nstat = cc_share(status, s["t_start"], s["t_end"])
                res = {}
                for ch in ("e", "z"):
                    T = fill_rows(D.image(i, f"{ch}_trace")[0]); R = fill_rows(D.image(i, f"{ch}_retrace")[0])
                    if T is None or R is None or T.shape[1] < 64 or np.nanstd(T) == 0: res[ch] = None; continue
                    T, R = rowlev(T), rowlev(R)
                    sh, q = seg_shifts(T, R)
                    f = fit(sh, q, T.shape[1])
                    res[ch] = dict(shifts=[None if not np.isfinite(v) else v for v in sh], qual=q.tolist(), q_med=float(np.median(q)), **f)
            except Exception as e:
                continue
            W = None
            for ch in ("e", "z"):
                if res.get(ch): W = len(res[ch]["shifts"]) and None
            half = D.image(i, "e_trace")[0].shape[1]
            nm = s.get("scan_size_nm") or (idx.get("settings") or {}).get("scan_size_nm")
            rows.append(dict(day=day, sweep=i, dir=s["dir"], scan_nm=nm, px=half, line_period_ms=1000 * line_period,
                             cc_share=share, n_status=nstat, e=res.get("e"), z=res.get("z")))
        print(day, "sweeps measured:", sum(1 for r in rows if r["day"] == day), flush=True)
    json.dump(rows, open(os.path.join(HERE, "hy1_sweeps.json"), "w"), default=float)
    print("total", len(rows))


if __name__ == "__main__":
    main()
