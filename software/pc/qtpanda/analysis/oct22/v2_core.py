"""V2 core: drift registration of Oct 22 sweeps into one sample frame, line by line.

v1 gave each sweep one shift.  Drift continues during the ~25 s sweep (0.56 px/s, ~14 px
top to bottom), so here every line is placed by its own recorded time:
    content at sample position (Y, X) appears in sweep i at row r = Y + dy(i, t_r), col = X + dx(i)
    dy(i, t) = -(vy * (t - T20) + offy * (h_i - h_20)/2 + jumpy * gain_changes(20 -> i))
with the drift model fitted in v1 (model_metrics.json).  T20 = mean line time of #20, so the
sample frame is #20's, at the middle of #20.  Display convention: peaks bright (I-10):
height = -Z, current-like = -error.
"""
import os, json
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
HERE = os.path.dirname(os.path.abspath(__file__))
import sys
QT = "C:/Users/enact/Projects/qt-panda/software/pc/qtpanda"
sys.path.insert(0, QT + "/replay"); sys.path.insert(0, QT)
import numpy as np
from scipy import ndimage as ndi
import sweep_player as sp

D = sp.DayData("2026-Oct-22")
H = W = 256
PX_NM = 30.0 / 256
SEQ = [20, 21, 22, 23, 25, 26, 27, 28, 30, 31]
RUNG = {**{i: "1.14" for i in range(15, 20)}, **{i: "2.3" for i in range(20, 25)},
        **{i: "4.6" for i in range(25, 30)}, **{i: "9" for i in range(30, 33)}}
mm = json.load(open(os.path.join(HERE, "morph_report", "model_metrics.json")))
CY = np.array([mm["model_y"]["drift_px_s"], mm["model_y"]["offset_px"], mm["model_y"]["gain_jump_px"]])
CX = np.array([mm["model_x"]["drift_px_s"], mm["model_x"]["offset_px"], mm["model_x"]["gain_jump_px"]])
CIRC = (220, 135, 36, 35)          # operator's circle in #20: row, col, half-height, half-width


def S_(i): return D.sweeps[i][2]
def hdir(i): return 1 if S_(i)["dir"] == "down" else -1


def nchg(a, b):
    lo, hi = sorted((S_(a)["t_start"], S_(b)["t_start"]))
    return len({RUNG[k] for k in SEQ if lo <= S_(k)["t_start"] <= hi}) - 1


def row_times(i):
    fp, idx, s = D.sweeps[i]
    t = np.full(H, np.nan)
    for tt, line, z, e in D.records(fp)[s["first_record"]:s["last_record"] + 1]:
        raw = line % (2 * H); row = raw if raw < H else 2 * H - 1 - raw
        t[row] = tt
    ok = np.isfinite(t)
    return np.interp(np.arange(H), np.flatnonzero(ok), t[ok])


T20 = float(np.mean(row_times(20)))


def dy_dx(i, t):
    s = 1 if S_(i)["t_start"] >= S_(20)["t_start"] else -1
    f2 = (hdir(i) - hdir(20)) / 2; j = s * max(nchg(20, i), 0)
    dy = -(CY[0] * (np.asarray(t) - T20) + CY[1] * f2 + CY[2] * j)
    dx = -(CX[0] * (float(np.mean(t)) - T20) + CX[1] * f2 + CX[2] * j)
    return dy, dx


def fill_rows(a):
    a = a.astype(float).copy(); bad = np.isnan(a).any(1); good = np.flatnonzero(~bad)
    for r in np.flatnonzero(bad): a[r] = a[good[np.argmin(np.abs(good - r))]]
    return a


def rowlev(a):
    x = np.arange(a.shape[1]); A = np.vstack([x, np.ones_like(x)]).T
    c, *_ = np.linalg.lstsq(A, a.T, rcond=None); return a - (A @ c).T


def prep(a, sig=1.0):
    return ndi.gaussian_filter(np.clip(a, *np.percentile(a, [2, 98])), sig)


def images(i):
    """Peaks-bright display arrays in the sweep's own frame: (-error, -Z folded S, raw error)."""
    e = fill_rows(D.image(i, "e_trace")[0])
    zt = fill_rows(D.image(i, "z_trace")[0]); zr = fill_rows(D.image(i, "z_retrace")[0])
    return -prep(rowlev(e)), -prep((rowlev(zt) + rowlev(zr)) / 2), e


# sample-frame canvas: rows Y0..Y1 (in #20 row units), cols 0..W
Y0, Y1 = -40, 256 + 200


def register(a, i, per_line=True):
    """Resample sweep i's array into the sample frame (rows Y0..Y1); NaN where not scanned."""
    t = row_times(i)
    if not per_line:
        t = np.full(H, float(np.mean(t)))
    dy, dx = dy_dx(i, t)
    yr = np.arange(H) - dy                         # sample row of each scanned row
    order = np.argsort(yr); yr, src = yr[order], a[order]
    Ys = np.arange(Y0, Y1)
    out = np.full((len(Ys), W), np.nan)
    inside = (Ys >= yr[0]) & (Ys <= yr[-1])
    for c in range(W):
        out[inside, c] = np.interp(Ys[inside], yr, src[:, c])
    # sideways: content at X sits at X + dx in the sweep -> sample column X = col - dx
    m = np.isfinite(out)
    sh = ndi.shift(np.nan_to_num(out), (0, -dx), order=1, mode="constant", cval=np.nan)
    mk = ndi.shift(m.astype(float), (0, -dx), order=0, mode="constant", cval=0) > 0.5
    sh[~mk] = np.nan
    return sh


def corr(a, b):
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < 500: return np.nan
    return float(np.corrcoef(a[m], b[m])[0, 1])


_cache = {}


def reg(i, per_line=True):
    k = (i, per_line)
    if k not in _cache:
        E, S, raw = images(i)
        _cache[k] = (register(E, i, per_line), register(S, i, per_line))
    return _cache[k]


if __name__ == "__main__":
    print("T20", T20, "row time span #20 (s):", np.ptp(row_times(20)))
    print("pair            per-sweep  per-line   (error / Z), registered overlap")
    res = []
    for a, b in zip(SEQ, SEQ[2:]):
        if S_(a)["dir"] != S_(b)["dir"]: continue
        r = []
        for pl in (False, True):
            Ea, Sa = reg(a, pl); Eb, Sb = reg(b, pl)
            r.append((corr(Ea, Eb), corr(Sa, Sb)))
        res.append((a, b, r))
        print(f"#{a}->#{b} {S_(a)['dir']:>4}   {r[0][0]:.2f}/{r[0][1]:.2f}   {r[1][0]:.2f}/{r[1][1]:.2f}")
    for a, b in zip(SEQ, SEQ[1:]):
        if S_(a)["dir"] == S_(b)["dir"]: continue
        r = [(corr(reg(a, pl)[0], reg(b, pl)[0]), corr(reg(a, pl)[1], reg(b, pl)[1])) for pl in (False, True)]
        print(f"#{a}->#{b} up/down {r[0][0]:.2f}/{r[0][1]:.2f}   {r[1][0]:.2f}/{r[1][1]:.2f}")
