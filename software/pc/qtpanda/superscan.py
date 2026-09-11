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


def fold_frame(lines, image_height, forward_only=True):
    """Assemble one Y-folded frame image from a list of (line_number, trace)
    tuples spanning one-plus line-counter cycle.  A cycle is 2H lines; the
    descending half covers the SAME rows as the ascending half.

    forward_only (default): keep only the ascending pass, matching what the
    live raster displays.  Letting the descending pass overwrite made each
    frame a patchwork of two lateral registrations (the up/down offset the
    Drift-corr X/Y spinboxes exist to correct) — stacking those blurred
    the superscan into smooth blobs while the live panel stayed sharp
    (diagnosed 2026-07-31)."""
    H = image_height
    W = len(lines[0][1])
    img = np.full((H, W), np.nan, np.float64)
    for ln, tr in lines:
        raw = ln % (2 * H)
        if forward_only and raw >= H:
            continue
        row = raw if raw < H else (2 * H - 1 - raw)
        img[row] = tr
    # Fill untouched rows from the NEAREST valid row.  The old version
    # copied only from r-1, so a run of empty rows propagated NaN (and a
    # leading empty row copied a still-empty neighbour) — with
    # forward_only the first, partial cycle has many empty rows, and the
    # NaNs reached the stack and rendered blank (bench 2026-07-31).
    valid = [r for r in range(H) if not np.isnan(img[r]).all()]
    if not valid:
        return None                       # nothing usable in this cycle
    if len(valid) < H:
        for r in range(H):
            if np.isnan(img[r]).all():
                img[r] = img[min(valid, key=lambda v: abs(v - r))]
    # any remaining holes inside a row: fill with that row's median
    if np.isnan(img).any():
        for r in range(H):
            m = np.isnan(img[r])
            if m.any():
                img[r][m] = np.nanmedian(img[r]) if (~m).any() else 0.0
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


def row_shifts(ref, img, max_px=6):
    """Per-row lateral offsets aligning img's rows to ref's (after global
    registration).  A raster under lateral jitter is rigid per ROW, not
    per frame — stacking globally-registered frames motion-blurs at the
    jitter amplitude (bench 2026-07-31: 10-frame drizzle at 4.6 nm came
    out WORSE than one fast frame).  1-D cross-correlation per row with
    parabolic sub-pixel refine; rows with weak structure or implausible
    lags keep shift 0."""
    H, W = ref.shape
    out = np.zeros(H)
    for r in range(H):
        a = ref[r] - ref[r].mean()
        b = img[r] - img[r].mean()
        sa, sb = a.std(), b.std()
        if sa < 1e-9 or sb < 1e-9:
            continue
        c = np.correlate(a, b, 'full')
        k = int(np.argmax(c))
        lag = k - (W - 1)          # b must shift by +lag to match a
        if abs(lag) > max_px:
            continue
        if 0 < k < len(c) - 1:
            denom = c[k - 1] - 2 * c[k] + c[k + 1]
            if abs(denom) > 1e-30:
                frac = 0.5 * (c[k - 1] - c[k + 1]) / denom
                if abs(frac) <= 1.0:
                    lag += frac
        out[r] = lag
    return out


def drizzle(frames, shifts, up=2, per_row=None):
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
    for i, (f, (dy, dx)) in enumerate(zip(frames, shifts)):
        if not (np.isfinite(dy) and np.isfinite(dx)):
            dy = dx = 0.0
        # Bilinear splat: each source pixel deposits area-weighted onto
        # its 4 nearest fine-grid cells.  Point (rint) deposition left
        # 3/4 of cells per frame empty; when shift fractions clustered,
        # whole parity classes stayed uncovered and were mean-filled —
        # the persistent checkerboard/"moiré" grid on every superscan
        # (diagnosed 2026-07-31).
        fy = (ys - dy) * up
        fx = (xs - dx) * up
        if per_row is not None:
            # Per-row shear correction (X only).  row_shifts() returns
            # -lag for features moved +lag, so ADD to land each row's
            # content at its reference x (sign verified synthetically,
            # 2026-07-31).
            fx = fx + (-per_row[i][:, None]) * up
        y0 = np.floor(fy).astype(int)
        x0 = np.floor(fx).astype(int)
        wy = fy - y0
        wx = fx - x0
        for ddy, ddx, w in ((0, 0, (1 - wy) * (1 - wx)),
                            (0, 1, (1 - wy) * wx),
                            (1, 0, wy * (1 - wx)),
                            (1, 1, wy * wx)):
            oy = y0 + ddy
            ox = x0 + ddx
            m = (oy >= 0) & (oy < oh) & (ox >= 0) & (ox < ow) & (w > 0)
            np.add.at(acc, (oy[m], ox[m]), f[m] * w[m])
            np.add.at(wt, (oy[m], ox[m]), w[m])
    out = np.divide(acc, wt, out=np.zeros_like(acc), where=wt > 0)
    if (wt == 0).any():
        base = np.kron(np.mean(frames, axis=0), np.ones((up, up)))
        out[wt == 0] = base[wt == 0]
    return out, wt


def _overlap_crop(shifts, H, W, up):
    """Common-coverage rectangle of the aligned stack, in output px.

    Register alignment shrinks the trustworthy field: a frame shifted by
    (dy, dx) only covers output rows (-dy .. H-1-dy)*up, and the stack is
    fully sampled only where EVERY frame contributes.  The stacked result
    is therefore smaller than a single input frame (operator observation
    2026-07-31); everything outside this rectangle was extrapolated or
    under-sampled and is cropped away rather than presented as data."""
    dys = [dy for dy, _ in shifts]
    dxs = [dx for _, dx in shifts]
    y0 = max(0.0, max(-dy for dy in dys))
    y1 = min(H - 1.0, min(H - 1 - dy for dy in dys))
    x0 = max(0.0, max(-dx for dx in dxs))
    x1 = min(W - 1.0, min(W - 1 - dx for dx in dxs))
    oy0 = int(math.ceil(y0 * up)); oy1 = int(math.floor(y1 * up)) + 1
    ox0 = int(math.ceil(x0 * up)); ox1 = int(math.floor(x1 * up)) + 1
    return (oy0, max(oy1, oy0 + 1), ox0, max(ox1, ox0 + 1))


# Reconstruction modes offered in the GUI dropdown.  key -> (label, up).
MODES = {
    "drizzle":    ("Variable-Pixel Linear Reconstruction (Drizzle)", 2),
    "shiftadd":   ("Shift-and-Add average", 1),
    "median":     ("Robust median stack", 1),
    "drizzle4x":  ("Drizzle 4x (slow, sharp)", 4),
    # "drizzle_rowreg" exists in superscan() but is deliberately NOT
    # offered: per-row registration tested WORSE than plain drizzle on
    # synthetic shear (row-lag estimation noise > shear removed;
    # 2026-07-31).  Under lateral jitter, prefer "median" + fast frames.
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
    wt = None
    rms_shear = None
    if mode in ("drizzle", "drizzle4x", "drizzle_rowreg"):
        pr = None
        if mode == "drizzle_rowreg":
            aligned = [_bilinear_shift(f, dy, dx)
                       for f, (dy, dx) in zip(frames, shifts)]
            # Row-align against the MEDIAN stack, not frame 0: frame 0 is
            # itself jittered, and aligning to it bakes its shear into
            # every frame (v1 underperformed plain drizzle, 2026-07-31).
            ref = np.median(np.stack(aligned), axis=0)
            pr = [row_shifts(ref, a) for a in aligned]
            rms_shear = float(np.sqrt(np.mean(np.square(pr))))
        hi, wt = drizzle(frames, shifts, up=up, per_row=pr)
    elif mode == "median":
        aligned = [_bilinear_shift(f, dy, dx) for f, (dy, dx) in zip(frames, shifts)]
        hi = np.median(np.stack(aligned), axis=0)
        up = 1
    else:  # shiftadd
        aligned = [_bilinear_shift(f, dy, dx) for f, (dy, dx) in zip(frames, shifts)]
        hi = np.mean(np.stack(aligned), axis=0)
        up = 1
    # Honest output: crop to the region every registered frame covers.
    H, W = frames[0].shape
    full_shape = hi.shape
    oy0, oy1, ox0, ox1 = _overlap_crop(shifts, H, W, up)
    hi = hi[oy0:oy1, ox0:ox1]
    if wt is not None:
        wt = wt[oy0:oy1, ox0:ox1]
    mags = [math.hypot(dy, dx) for dy, dx in shifts]
    stats = {
        "mode": mode, "mode_label": label,
        "n_frames": len(frames), "up": up, "shifts": shifts,
        "max_drift_px": max(mags) if mags else 0.0,
        "single_frame_std": float(np.std(frames[0])),
        "superscan_std": float(np.std(hi)),
        "full_shape": full_shape,          # pre-crop output grid
        "crop_px": (oy0, oy1, ox0, ox1),   # kept rectangle on that grid
        "weight": wt,                      # per-cell coverage (drizzle)
        "coverage_min": float(wt.min()) if wt is not None else None,
        "coverage_median": float(np.median(wt)) if wt is not None else None,
        "rms_row_shear_px": rms_shear,
    }
    return hi, shifts, stats
