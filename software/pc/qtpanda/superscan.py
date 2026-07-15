"""superscan — multi-frame super-resolution for continuous-scan images.

Fuses N drift-jittered continuous-scan frames of the same region into one
higher-definition image (the "drift is the dither" idea from
documentation/docs-for-ai/stm-super-resolution-reconstruction.md).

Pure NumPy/SciPy, Qt-free and hardware-free so it is unit-testable; the GUI
collects frames and hands them here.

Pipeline: per-frame Y-fold (matches live_raster) -> log-err linearize ->
sub-pixel phase-correlation registration to the first frame -> weighted
deposition ("shift-and-add" drizzle) onto an up x finer grid -> normalize.
"""
import math

import numpy as np

LOG_K = (2 ** 19 - 1) / math.log(2 ** 15 + 1)


def linearize_err(err_line, setpoint_lsb):
    """Firmware log-error channel -> linear current counts (see live_raster)."""
    setlog = round(math.log(abs(setpoint_lsb) + 1) * LOG_K)
    return np.exp((setlog - np.asarray(err_line, float)) / LOG_K) - 1.0


def fold_frame(lines, image_height):
    """Assemble one Y-folded frame image from a list of (line_number, trace)
    tuples spanning one-plus line-counter cycle.  Matches the live raster:
    a cycle is 2H lines; the descending half mirrors onto the ascending
    rows.  Latest sample per (row) wins."""
    H = image_height
    W = len(lines[0][1])
    img = np.full((H, W), np.nan, np.float64)
    for ln, tr in lines:
        raw = ln % (2 * H)
        row = raw if raw < H else (2 * H - 1 - raw)
        img[row] = tr
    # fill any untouched rows by nearest-neighbor down the column
    if np.isnan(img).any():
        for r in range(H):
            if np.isnan(img[r]).all():
                src = r - 1 if r > 0 else r + 1
                img[r] = img[min(max(src, 0), H - 1)]
    return img


def _phase_shift(ref, img, max_shift=None):
    """Sub-pixel (dy, dx) that best aligns img onto ref, via the phase-
    correlation peak with a parabolic refinement.

    max_shift bounds the search: STM frames are seconds apart so real drift
    is small (a few px).  Without a bound, noise on nearly-identical frames
    produces spurious large peaks that MISALIGN the stack (verified
    2026-07-15) — the physical prior is also the robust one."""
    a = ref - ref.mean()
    b = img - img.mean()
    Fa = np.fft.fft2(a)
    Fb = np.fft.fft2(b)
    R = Fa * np.conj(Fb)
    R /= np.abs(R) + 1e-9
    c = np.fft.ifft2(R).real
    if max_shift is None:
        max_shift = max(4, min(c.shape) // 6)
    # Mask everything outside +/- max_shift (in wrapped coords) before argmax.
    mask = np.zeros_like(c, bool)
    s = int(max_shift)
    for dy in range(-s, s + 1):
        for dx in range(-s, s + 1):
            mask[dy % c.shape[0], dx % c.shape[1]] = True
    c = np.where(mask, c, -np.inf)
    peak = np.unravel_index(np.argmax(c), c.shape)

    def refine(axis, p):
        n = c.shape[axis]
        pm = list(peak); pp = list(peak)
        pm[axis] = (p - 1) % n
        pp[axis] = (p + 1) % n
        ym, y0, yp = c[tuple(pm)], c[peak], c[tuple(pp)]
        # Neighbors may be -inf (masked outside max_shift) — only refine
        # sub-pixel when all three are finite; otherwise use the integer
        # peak.  Clamp the correction to +/-1 so a tiny denominator can
        # never blow the shift up (caused a NaN->huge-index crash in
        # shift-and-add, 2026-07-15).
        d = 0.0
        if np.isfinite(ym) and np.isfinite(y0) and np.isfinite(yp):
            denom = (ym - 2 * y0 + yp)
            if denom != 0:
                d = float(np.clip(0.5 * (ym - yp) / denom, -1.0, 1.0))
        shift = p + d
        if shift > n / 2:
            shift -= n
        return float(shift)

    dy, dx = refine(0, peak[0]), refine(1, peak[1])
    lim = float(max_shift) + 1.0
    dy = 0.0 if not np.isfinite(dy) else float(np.clip(dy, -lim, lim))
    dx = 0.0 if not np.isfinite(dx) else float(np.clip(dx, -lim, lim))
    return dy, dx


def register(frames, max_shift=None):
    """Return per-frame (dy, dx) shifts aligning each to frames[0]."""
    ref = frames[0]
    return [(0.0, 0.0)] + [_phase_shift(ref, f, max_shift) for f in frames[1:]]


def drizzle(frames, shifts, up=2):
    """Weighted deposition of shifted frames onto an up-times-finer grid.

    Each source pixel is added to its (shifted, upscaled) location with a
    unit weight; the accumulator is normalized by the weight map.  Empty
    output cells (no contributor) are filled from the plain upscaled mean
    so the result is always complete.
    """
    H, W = frames[0].shape
    oh, ow = H * up, W * up
    acc = np.zeros((oh, ow), np.float64)
    wt = np.zeros((oh, ow), np.float64)
    ys, xs = np.mgrid[0:H, 0:W]
    for f, (dy, dx) in zip(frames, shifts):
        if not (np.isfinite(dy) and np.isfinite(dx)):
            dy = dx = 0.0
        oy = np.rint((ys - dy) * up).astype(int)
        ox = np.rint((xs - dx) * up).astype(int)
        m = (oy >= 0) & (oy < oh) & (ox >= 0) & (ox < ow)
        np.add.at(acc, (oy[m], ox[m]), f[m])
        np.add.at(wt, (oy[m], ox[m]), 1.0)
    out = np.divide(acc, wt, out=np.zeros_like(acc), where=wt > 0)
    if (wt == 0).any():
        base = np.kron(np.mean(frames, axis=0), np.ones((up, up)))
        out[wt == 0] = base[wt == 0]
    return out


# Reconstruction modes offered in the GUI dropdown.  key -> (label, up).
MODES = {
    "drizzle":    ("Variable-Pixel Linear Reconstruction (Drizzle)", 2),
    "shiftadd":   ("Shift-and-Add average", 1),
    "median":     ("Robust median stack", 1),
    "drizzle4x":  ("Drizzle 4x (slow, sharp)", 4),
}
DEFAULT_MODE = "drizzle"


def _bilinear_shift(f, dy, dx):
    """Shift a frame by (dy, dx) with bilinear interpolation (edge-clamped).
    Non-finite shifts are treated as zero — clip(NaN) leaks NaN into the
    int index and overflows (crash guard, 2026-07-15)."""
    if not (np.isfinite(dy) and np.isfinite(dx)):
        dy = dx = 0.0
    H, W = f.shape
    ys, xs = np.mgrid[0:H, 0:W]
    sy = np.clip(ys - dy, 0, H - 1)
    sx = np.clip(xs - dx, 0, W - 1)
    y0 = np.floor(sy).astype(int); x0 = np.floor(sx).astype(int)
    y1 = np.clip(y0 + 1, 0, H - 1); x1 = np.clip(x0 + 1, 0, W - 1)
    fy = sy - y0; fx = sx - x0
    return (f[y0, x0] * (1 - fy) * (1 - fx) + f[y0, x1] * (1 - fy) * fx +
            f[y1, x0] * fy * (1 - fx) + f[y1, x1] * fy * fx)


def superscan(frames, mode=DEFAULT_MODE, up=None):
    """frames: list of 2-D float arrays (already folded + linearized).
    mode: one of MODES.  Returns (hi_res_image, shifts, stats)."""
    frames = [np.asarray(f, float) for f in frames]
    label, mode_up = MODES.get(mode, MODES[DEFAULT_MODE])
    if up is None:
        up = mode_up
    shifts = register(frames)
    if mode in ("drizzle", "drizzle4x"):
        hi = drizzle(frames, shifts, up=up)
    elif mode == "median":
        aligned = [_bilinear_shift(f, dy, dx) for f, (dy, dx) in zip(frames, shifts)]
        hi = np.median(np.stack(aligned), axis=0)
        up = 1
    else:  # shiftadd
        aligned = [_bilinear_shift(f, dy, dx) for f, (dy, dx) in zip(frames, shifts)]
        hi = np.mean(np.stack(aligned), axis=0)
        up = 1
    mags = [math.hypot(dy, dx) for dy, dx in shifts]
    stats = {
        "mode": mode, "mode_label": label,
        "n_frames": len(frames), "up": up, "shifts": shifts,
        "max_drift_px": max(mags) if mags else 0.0,
        "single_frame_std": float(np.std(frames[0])),
        "superscan_std": float(np.std(hi)),
    }
    return hi, shifts, stats
