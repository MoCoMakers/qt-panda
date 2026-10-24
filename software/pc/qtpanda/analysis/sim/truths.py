"""Ground-truth surfaces for scan_sim (heights in Å; stated assumptions, re-scalable later).

sep24   : good-tip Sep 24 #1586-#1599 (24.79 nm; last good-tip scan day on disk, repeat 0.88-0.98),
          up sweeps' folded Z, plane-levelled, aligned by phase correlation and averaged.  Z is
          uncalibrated: the placeholder calibration implies ~0.05 Å rms, so the map is RESCALED to a
          stated rms (default 1 Å).  Raster-acquired, so it is a raster-biased truth.
synthetic: 60 nm field: monatomic step (2.35 Å), 0.288 nm hexagonal lattice patch (0.3 Å),
          mounds (3-8 Å), an Oct-22-like hollow (rim + 4 Å pit), 0.3 Å smooth roughness.
"""
import os, sys
import numpy as np
from scipy import ndimage as ndi
HERE = os.path.dirname(os.path.abspath(__file__))
QT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, QT); sys.path.insert(0, os.path.join(QT, "replay")); sys.path.insert(0, HERE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import scan_sim as M


def _fill(a):
    a = a.astype(float).copy(); bad = np.isnan(a).any(1); good = np.flatnonzero(~bad)
    for r in np.flatnonzero(bad): a[r] = a[good[np.argmin(np.abs(good - r))]]
    return a


def _rowlev(a):
    x = np.arange(a.shape[1]); A = np.vstack([x, np.ones_like(x)]).T
    c, *_ = np.linalg.lstsq(A, a.T, rcond=None); return a - (A @ c).T


def _plane(a):
    yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]]
    A = np.c_[yy.ravel(), xx.ravel(), np.ones(a.size)]
    c, *_ = np.linalg.lstsq(A, a.ravel(), rcond=None)
    return a - (A @ c).reshape(a.shape)


def _shift(a, b):
    """Integer (dy, dx) that aligns b onto a (phase correlation)."""
    F = np.fft.fft2(a - a.mean()) * np.conj(np.fft.fft2(b - b.mean()))
    c = np.fft.ifft2(F / (np.abs(F) + 1e-9)).real
    dy, dx = np.unravel_index(np.argmax(c), c.shape)
    H, W = a.shape
    return (dy if dy <= H // 2 else dy - H), (dx if dx <= W // 2 else dx - W)


def sep24(ids=(1586, 1588, 1590, 1592, 1594, 1596, 1598), rms_A=1.0, scale=None, tilt=False):
    """rms_A: rescale features to this rms (stated assumption).  scale: instead multiply the
    placeholder calibration by `scale` (features AND tilt on one consistent scale).
    tilt: add back the measured plane of the raw Z (median over the sweeps)."""
    import sweep_player as sp
    D = sp.DayData("2026-Sep-24")
    S = []; planes = []
    for i in ids:
        zt = _fill(D.image(i, "z_trace")[0]); zr = _fill(D.image(i, "z_retrace")[0])
        S.append(_plane((zt + zr) / 2))               # plane only: keep structure along Y
        planes.append((zt + zr) / 2 - S[-1])
    ref = S[0]; acc = np.zeros_like(ref); cnt = np.zeros_like(ref)
    for s in S:
        dy, dx = _shift(ref, s)
        sh = ndi.shift(s, (dy, dx), order=0, mode="constant", cval=np.nan)
        m = np.isfinite(sh); acc[m] += sh[m]; cnt[m] += 1
    avg = np.where(cnt > 0, acc / np.maximum(cnt, 1), np.nan)
    avg = np.where(np.isfinite(avg), avg, np.nanmedian(avg))
    g = M.LS.z_gain_A_per_unit(M.PHYS["kappa"])
    h = -_plane(avg)                                   # peaks up (Z extends into valleys)
    native = h.std() * g                               # what the placeholder calibration implies
    if scale is not None:
        h = h * g * scale
        if tilt:
            h = h - np.median(np.stack(planes), 0) * g * scale
    else:
        h = h / h.std() * rms_A                        # STATED ASSUMPTION: rescaled to rms_A
    h -= np.median(h)
    size = D.sweeps[ids[0]][2]["scan_size_nm"]
    return M.Truth(h, size / h.shape[1], "Sep 24 good tip (#1586-#1598 up, averaged)"), dict(z_gain_A=g, scan_nm=size, native_rms_A=float(native), rms_A=rms_A)


def sep24_error(ids=(1586, 1588, 1590, 1592, 1594, 1596, 1598), scale=1.0):
    """Morphology truth from the ERROR channel (operator, 2026-10-23: best morphology), Sep 24 good tip.
    Up sweeps' line-levelled error traces are aligned by phase correlation and averaged.  Height from
    the error's own physics: err = log(setpoint) - log(I) in log-table units (LOG_K per ln unit) and
    I ~ exp(-2 kappa gap), so h = -err / (LOG_K * 2 kappa) Å (constant-height reading of the error
    image; `scale` re-scales it later)."""
    import sweep_player as sp
    D = sp.DayData("2026-Sep-24")
    E = [_rowlev(_fill(D.image(i, "e_trace")[0])) for i in ids]
    ref = E[0]; acc = np.zeros_like(ref); cnt = np.zeros_like(ref)
    for e in E:
        dy, dx = _shift(ref, e)
        sh = ndi.shift(e, (dy, dx), order=0, mode="constant", cval=np.nan)
        m = np.isfinite(sh); acc[m] += sh[m]; cnt[m] += 1
    avg = np.where(cnt > 0, acc / np.maximum(cnt, 1), np.nan)
    avg = np.where(np.isfinite(avg), avg, np.nanmedian(avg))
    LOG_K = (2 ** 19 - 1) / np.log(2 ** 15 + 1)
    h = -avg / (LOG_K * 2 * M.PHYS["kappa"]) * scale
    h -= np.median(h)
    size = D.sweeps[ids[0]][2]["scan_size_nm"]
    return M.Truth(h, size / h.shape[1], "Sep 24 good tip, error channel (#1586-#1598 up, averaged)"), dict(scan_nm=size, n=len(ids))


def sep24_error(ref_id=1808, ids=(1808,), scale=1.0):
    """Morphology truth from the ERROR channel (operator, 2026-10-23: the error channel has the best
    morphology; #1808 looked best in the morphology report).  Sep 24 good tip, 27.1 nm, up sweeps
    #1808 alone by default (averaging shifted frames left coverage seams); with more ids they are
    line-levelled, aligned onto #1808 by phase correlation and averaged.
    Height from the error's own physics: err = log(setpoint) - log(I) in log-table units (LOG_K per
    ln unit) and I ~ exp(-2 kappa gap), so h = -err / (LOG_K * 2 kappa) Å: the constant-height
    reading of the error image.  `scale` re-scales it when calibrations arrive."""
    import sweep_player as sp
    D = sp.DayData("2026-Sep-24")
    ref = _rowlev(_fill(D.image(ref_id, "e_trace")[0]))
    acc = np.zeros_like(ref); cnt = np.zeros_like(ref)
    for i in ids:
        e = _rowlev(_fill(D.image(i, "e_trace")[0]))
        dy, dx = _shift(ref, e)
        sh = ndi.shift(e, (dy, dx), order=0, mode="constant", cval=np.nan)
        m = np.isfinite(sh); acc[m] += sh[m]; cnt[m] += 1
    avg = np.where(cnt > 0, acc / np.maximum(cnt, 1), np.nan)
    avg = np.where(np.isfinite(avg), avg, np.nanmedian(avg))
    LOG_K = (2 ** 19 - 1) / np.log(2 ** 15 + 1)
    h = -avg / (LOG_K * 2 * M.PHYS["kappa"]) * scale
    h -= np.median(h)
    size = D.sweeps[ref_id][2]["scan_size_nm"]
    return (M.Truth(h, size / h.shape[1], f"Sep 24 good tip, error channel (#{ref_id} frame; #{ids[0]}-#{ids[-1]} up averaged)"),
            dict(scan_nm=size, n=len(ids), ref=ref_id))


def synthetic(size_nm=60.0, px_nm=0.05, seed=3):
    n = int(round(size_nm / px_nm))
    u = (np.arange(n) - (n - 1) / 2) * px_nm
    X, Y = np.meshgrid(u, u)
    h = np.zeros((n, n))
    h += 2.35 * (X * 0.8 + Y * 0.6 > 3.0)                                  # monatomic step
    a = 0.288; k = 4 * np.pi / (np.sqrt(3) * a)                             # hexagonal lattice
    lat = sum(np.cos(k * (X * np.cos(t) + Y * np.sin(t))) for t in (0, 2 * np.pi / 3, 4 * np.pi / 3)) / 3
    patch = np.exp(-(((X + 4) ** 2 + (Y - 4) ** 2) / (2 * 3.5 ** 2)) ** 3)
    h += 0.3 * lat * patch
    rng = np.random.default_rng(seed)
    for _ in range(9):
        cx, cy = rng.uniform(-9, 9, 2); w = rng.uniform(0.8, 2.5); amp = rng.uniform(3, 8)
        h += amp * np.exp(-((X - cx) ** 2 + (Y - cy) ** 2) / (2 * w * w))
    r = np.hypot(X - 3.5, Y + 3.0)                                           # hollow: rim + pit
    h += 5.0 * np.exp(-((r - 1.6) ** 2) / (2 * 0.45 ** 2)) - 4.0 * np.exp(-(r ** 2) / (2 * 0.7 ** 2))
    f = np.fft.fft2(rng.normal(size=(n, n)))
    kk = np.hypot(*np.meshgrid(np.fft.fftfreq(n), np.fft.fftfreq(n)))
    rough = np.real(np.fft.ifft2(f * np.exp(-(kk / 0.01) ** 2)))
    h += rough / rough.std() * 0.3
    return M.Truth(h - np.median(h), px_nm, "synthetic: step, lattice patch, mounds, hollow")


if __name__ == "__main__":
    t, info = sep24(); print(t.name, t.h.shape, f"{t.px:.4f} nm/px", f"rms {t.h.std():.2f} Å", info)
    s = synthetic(); print(s.name, s.h.shape, f"rms {s.h.std():.2f} Å")
