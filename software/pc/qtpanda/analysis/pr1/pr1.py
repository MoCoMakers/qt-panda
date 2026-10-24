"""PR1: is the speed-dependent trace/retrace shift in the error channel a first-order FILTER (shifts
AND blurs edges by ~v*tau) or a LATENCY / position lag (shifts without blurring)?

Per sweep group (same scan size and line period):
  shift   trace vs retrace, whole-line cross-correlation of the surface content (line-locked profile
          removed), search +-120 px, sub-pixel.  Converted to an equivalent delay tau_shift = shift/(2 v).
  widths  10-90 % widths of step edges from erf fits: along X in the trace and the retrace (fast axis,
          where a filter acts) and along Y (slow axis: one row per line period, so a sub-ms filter
          cannot widen it -> intrinsic width reference).
A first-order filter of time constant tau adds ~2.197*v*tau (10-90 %) to every X width and shifts
trace vs retrace by 2*v*tau.  A latency or a position lag (amplifier, piezo) shifts by 2*v*tau and
adds no width.  v = scan size / half-line time.
Outputs: pr1_results.json, figures, PR1_RESULTS.md (written separately).
"""
import os, sys, json
os.environ["QT_QPA_PLATFORM"] = "offscreen"
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ["QTPANDA_SETTINGS"] = os.path.join(HERE, "scratch_settings.ini")
QT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(QT, "replay")); sys.path.insert(0, QT)
import numpy as np
from scipy.ndimage import gaussian_filter
from scipy.optimize import curve_fit
from scipy.special import erf
import sweep_player as sp

# (label, day, sweeps, feedback state) -- groups chosen from analysis/hysteresis/hy1_sweeps.json
GROUPS = [
    ("Sep24 30nm 5ms CC", "2026-Sep-24", [744, 749, 750, 751, 752, 753, 754, 755], "CC"),
    ("Sep24 30nm 10ms CC", "2026-Sep-24", [3059, 3061, 3062, 3063, 3065, 3066], "CC"),
    ("Sep24 30nm 15ms CH", "2026-Sep-24", [1260, 1261, 1262], "CH"),
    ("Sep24 30nm 20ms CC", "2026-Sep-24", [832, 834, 835, 836, 837, 838], "CC"),
    ("Sep24 30nm 31ms CC", "2026-Sep-24", [1568, 1570, 1571, 1572, 1573, 1575], "CC"),
    ("Sep24 30nm 31ms CH", "2026-Sep-24", [1483, 1485, 1497, 3040, 3041], "CH"),
    ("Sep24 27nm 5ms CC (#1808)", "2026-Sep-24", [1802, 1804, 1806, 1808, 1810, 1812], "CC"),
    ("Sep24 50nm 5ms CC", "2026-Sep-24", [2636, 2637, 2638, 2642, 2644, 2646], "CC"),
    ("Oct22 30nm 97ms CC", "2026-Oct-22", [12, 15, 17, 18, 23, 27], "CC"),
]
MAXLAG = 120
LN9 = np.log(9.0)
ERF2W = 2.5631  # 10-90 % width of an erf step = 2.5631 * sigma


def fill_rows(a):
    a = a.astype(float).copy(); bad = np.isnan(a).any(1); good = np.flatnonzero(~bad)
    if len(good) < 8: return None
    for r in np.flatnonzero(bad): a[r] = a[good[np.argmin(np.abs(good - r))]]
    return a


def rowlev(a):
    x = np.arange(a.shape[1]); A = np.vstack([x, np.ones_like(x)]).T
    c, *_ = np.linalg.lstsq(A, a.T, rcond=None); return a - (A @ c).T


def line_period(D, i):
    fp, idx, s = D.sweeps[i]
    rec = D.records(fp)[s["first_record"]:s["last_record"] + 1]
    t = np.array([r[0] for r in rec])
    return (t[-1] - t[0]) / max(1, len(t) - 1)


def whole_shift(T, R):
    """Retrace relative to trace (px): + = retrace features at larger X."""
    a = gaussian_filter(T - T.mean(0, keepdims=True), 1.0); b = gaussian_filter(R - R.mean(0, keepdims=True), 1.0)
    a = rowlev(a); b = rowlev(b)
    W = a.shape[1]; lags = np.arange(-MAXLAG, MAXLAG + 1); cc = np.full(len(lags), np.nan)
    for j, L in enumerate(lags):
        if abs(L) > W - 32: continue
        x, y = (a[:, :W - L], b[:, L:]) if L >= 0 else (a[:, -L:], b[:, :W + L])
        cc[j] = (x * y).sum() / (np.sqrt((x * x).sum() * (y * y).sum()) + 1e-12)
    i = int(np.nanargmax(cc))
    off = 0.0
    if 0 < i < len(cc) - 1 and np.isfinite(cc[i - 1]) and np.isfinite(cc[i + 1]):
        d = cc[i - 1] - 2 * cc[i] + cc[i + 1]
        off = 0.5 * (cc[i - 1] - cc[i + 1]) / d if d != 0 else 0.0
    return float(lags[i] + off), float(cc[i])


def _step(x, a, k, b, x0, s):
    return a + k * (x - x0) + b * erf((x - x0) / (np.sqrt(2) * s))


def edge_widths(img, axis, max_lines=80, per_line=3, win=10, min_proj=0.5):
    """Edge widths PERPENDICULAR to the edge (px, 10-90 %).  Edges are found and fitted along
    `axis` (1 = X within a row, 0 = Y within a column); the fitted width along that axis is
    multiplied by |cos| of the angle between the axis and the edge normal (local 2-D gradient), so
    X and Y measurements of the same kind of edge are comparable.  Only edges whose normal is within
    60 deg of the axis (|cos| >= min_proj) are kept."""
    B = rowlev(img) if axis == 1 else rowlev(img.T).T
    gy2, gx2 = np.gradient(gaussian_filter(B, 1.5))
    A = B if axis == 1 else B.T
    proj_map = np.abs(gx2) if axis == 1 else np.abs(gy2)
    proj_map = proj_map / (np.hypot(gx2, gy2) + 1e-12)
    if axis == 0: proj_map = proj_map.T
    sm = gaussian_filter(A, (0, 0.6))
    g = np.gradient(sm, axis=1)
    noise = 1.4826 * np.median(np.abs(np.diff(A, axis=1))) / np.sqrt(2) + 1e-12
    gs = 1.4826 * np.median(np.abs(g - np.median(g))) + 1e-12
    out = []
    rows = np.linspace(0, A.shape[0] - 1, min(max_lines, A.shape[0])).astype(int)
    x_all = np.arange(A.shape[1])
    for r in rows:
        gr = np.abs(g[r])
        cand = np.flatnonzero((gr > 5 * gs) & (gr >= np.roll(gr, 1)) & (gr >= np.roll(gr, -1)))
        cand = cand[(cand > win) & (cand < A.shape[1] - win - 1)]
        cand = cand[np.argsort(-gr[cand])][:per_line]
        for c in cand:
            pr = proj_map[r, c]
            if pr < min_proj: continue
            xs = x_all[c - win:c + win + 1].astype(float); ys = A[r, c - win:c + win + 1]
            b0 = (ys[-3:].mean() - ys[:3].mean()) / 2
            try:
                p, _ = curve_fit(_step, xs, ys, p0=[ys.mean(), 0.0, b0, c, 1.0],
                                 bounds=([-np.inf, -np.inf, -np.inf, c - 4, 0.25], [np.inf, np.inf, np.inf, c + 4, 12.0]), maxfev=3000)
            except Exception:
                continue
            res = ys - _step(xs, *p)
            if abs(2 * p[2]) < 8 * noise or res.std() > 0.35 * abs(p[2]):
                continue
            out.append(ERF2W * p[4] * pr)
    return np.array(out)


def main():
    res = []
    cache = {}
    for label, day, sw, mode in GROUPS:
        if day not in cache:
            cache[day] = sp.DayData(day)
        D = cache[day]
        shifts, qual, wxt, wxr, wy, lps = [], [], [], [], [], []
        size = px = None
        for i in sw[:4]:
            try:
                fp, idx, s = D.sweeps[i]
            except Exception:
                continue
            if s["partial"]: continue
            T = fill_rows(D.image(i, "e_trace")[0]); R = fill_rows(D.image(i, "e_retrace")[0])
            if T is None or R is None: continue
            size = s.get("scan_size_nm") or 30.0; px = T.shape[1]
            lps.append(line_period(D, i))
            sh, q = whole_shift(T, R); shifts.append(sh); qual.append(q)
            wxt.append(edge_widths(T, 1)); wxr.append(edge_widths(R, 1)); wy.append(edge_widths(T, 0))
        if not shifts:
            print(label, "no data"); continue
        lp = float(np.mean(lps)); half_s = lp / 2.0
        px_nm = size / px; v = size / half_s                      # nm/s along the fast axis
        wxt_a, wxr_a, wy_a = np.concatenate(wxt), np.concatenate(wxr), np.concatenate(wy)
        sh_med = float(np.median(shifts))
        wx_med = float(np.median(np.r_[wxt_a, wxr_a])) if len(wxt_a) + len(wxr_a) else np.nan
        wy_med = float(np.median(wy_a)) if len(wy_a) else np.nan
        # filter time constant implied by extra X width (quadrature excess over the slow-axis width)
        excess_nm = np.sqrt(max(wx_med ** 2 - wy_med ** 2, 0.0)) * px_nm if np.isfinite(wx_med) and np.isfinite(wy_med) else np.nan
        tau_width_ms = excess_nm / (2.197 * v) * 1e3 if np.isfinite(excess_nm) else np.nan
        tau_shift_ms = abs(sh_med) * px_nm / (2 * v) * 1e3
        r = dict(label=label, day=day, mode=mode, sweeps=sw, scan_nm=size, px=px, line_period_ms=lp * 1e3,
                 tip_speed_um_s=v / 1e3, px_nm=px_nm,
                 shift_px_median=sh_med, shift_px_all=[float(x) for x in shifts], shift_corr=[float(x) for x in qual],
                 shift_nm=sh_med * px_nm, tau_shift_ms=tau_shift_ms,
                 width_x_trace_px=float(np.median(wxt_a)) if len(wxt_a) else np.nan,
                 width_x_retrace_px=float(np.median(wxr_a)) if len(wxr_a) else np.nan,
                 width_x_px=wx_med, width_y_px=wy_med, n_edges_x=int(len(wxt_a) + len(wxr_a)), n_edges_y=int(len(wy_a)),
                 width_x_nm=wx_med * px_nm, width_y_nm=wy_med * px_nm,
                 excess_x_nm=excess_nm, tau_width_ms=tau_width_ms,
                 predicted_extra_width_nm_if_filter_tau_shift=2.197 * v * tau_shift_ms / 1e3)
        res.append(r)
        print(f"{label:28s} lines {lp*1e3:6.1f} ms  v {v/1e3:6.2f} um/s  shift {sh_med:7.1f} px = {sh_med*px_nm:6.2f} nm  "
              f"(tau_shift {tau_shift_ms:5.3f} ms)  widths X {wx_med:5.2f} px / Y {wy_med:5.2f} px  "
              f"(X {wx_med*px_nm:5.2f} nm, Y {wy_med*px_nm:5.2f} nm, n {len(wxt_a)+len(wxr_a)}/{len(wy_a)})  "
              f"tau_width {tau_width_ms:5.3f} ms; a filter with tau_shift would add {2.197*v*tau_shift_ms/1e3:6.2f} nm", flush=True)
    json.dump(res, open(os.path.join(HERE, "pr1_results.json"), "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
