"""scan_sim — image a known surface along any scan path, tick by tick, and rebuild the image.

Chain (docs/test-plans/scan-path-design.md §9):
  bit-exact commanded positions (scan_paths) -> lateral piezo (hysteresis play operator,
  158.7 Hz resonance, amplifier lag) -> X-Y stage drift -> surface height under the tip ->
  Z drift -> tunnelling current -> preamp low-pass -> ADC (offset, noise, clip, one-tick delay)
  -> firmware feedback loop (port of loop_sim / controlTick) -> bins exactly as the firmware
  sends them -> reconstruction on a grid from the commanded-position map (optionally drift
  corrected) -> scores against the truth.

Every physical number below is a stated assumption with its source; they are meant to be
re-scaled as calibrations arrive (operator, 2026-10-23).
"""
import os, sys, math, time
import numpy as np
from scipy import ndimage as ndi
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
QT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, QT); sys.path.insert(0, HERE)
import scan_paths as SP
import loop_sim as LS

# ------------------------------------------------------------------ assumptions (edit, don't hide)
PHYS = dict(
    tick_us=10.0,             # FW SETD 10 (Oct 22, Sep 24 journals)
    res_hz=158.7,             # halted-hold Z resonance (Oct 22); assumed to act laterally too
    res_zeta=0.05,            # ASSUMED damping (Q = 10); fit from the peak width later
    amp_hz=3000.0,            # ASSUMED high-voltage amplifier bandwidth
    hyst_nm=0.5,              # single play operator width (used when hyst_frac == 0)
    hyst_frac=0.0,            # Prandtl-Ishlinskii loop: max play width as a fraction of the
                              #   commanded span (typical open-loop piezo 0.10-0.15); 0 = off
    hyst_ops=8,               # number of play operators in the PI model
    drift_nm_s=(0.0, -0.066), # X-Y stage drift, sample relative to scan frame (Oct 22: content
                              #   moves up the frame at 66 pm/s; up = -y in image rows)
    zdrift_A_s=0.0,           # Z drift (Å/s) of the surface away from the tip; set per run
    preamp_hz=6000.0,         # preamp bandwidth: PR1 (2026-10-23) bounds f3dB >= ~6-16 kHz from real edge
                              #   widths; the earlier 400 Hz guess is ruled out (DECISIONS A4)
    adc_noise=4.0,            # counts rms (loop_sim calibration)
    scan_offset=-55.0,        # phantom ADC offset while scanning (OI-3)
    pa_per_count=3.125,       # 1X preamp
    kappa=1.025,              # 1/Å, ~1 decade of current per Å (loop_sim)
)
LOOP = dict(kiga=4.6, setpoint_pa=500.0, bias_mv=49.6)


def nm_per_unit(scan_nm, spec):
    return scan_nm / spec.scan_size                   # scan_size position units span scan_nm


def _play(x, w):
    """Play (backlash) operator: output follows the input only after it moves w/2 past it."""
    y = np.empty_like(x); h = w / 2.0; cur = float(x[0])
    for i in range(len(x)):
        v = x[i]
        if v > cur + h: cur = v - h
        elif v < cur - h: cur = v + h
        y[i] = cur
    return y


def _pi(x, wmax, n):
    """Prandtl-Ishlinskii hysteresis: average of play operators with widths spread over
    (0, wmax].  Gives a smooth loop whose width grows with the reversal amplitude."""
    return np.mean([_play(x, wmax * (k + 1) / n) for k in range(n)], axis=0)


def lateral(xc, yc, fs, phys, decim=10):
    """Commanded (nm, per tick) -> actual (nm, per tick).  Dynamics run at fs/decim."""
    fsd = fs / decim
    xs, ys = xc[::decim].astype(float), yc[::decim].astype(float)
    w0 = 2 * math.pi * phys["res_hz"]; z = phys["res_zeta"]
    b, a = signal.bilinear([w0 * w0], [1, 2 * z * w0, w0 * w0], fs=fsd)
    ba, aa = signal.bilinear([2 * math.pi * phys["amp_hz"]], [1, 2 * math.pi * phys["amp_hz"]], fs=fsd)
    out = []
    for s in (xs, ys):
        if phys.get("hyst_frac", 0) > 0:
            s = _pi(s, phys["hyst_frac"] * float(np.ptp(s)), int(phys.get("hyst_ops", 8)))
        elif phys["hyst_nm"] > 0:
            s = _play(s, phys["hyst_nm"])
        zi = signal.lfilter_zi(b, a) * s[0]; s = signal.lfilter(b, a, s, zi=zi)[0]
        zi = signal.lfilter_zi(ba, aa) * s[0]; s = signal.lfilter(ba, aa, s, zi=zi)[0]
        out.append(s)
    tt = np.arange(len(xc)); td = np.arange(0, len(xc), decim)
    return np.interp(tt, td, out[0]), np.interp(tt, td, out[1])


class Truth:
    """Height map (Å) in the sample frame; pixel size px_nm; origin at the map centre."""

    def __init__(self, h, px_nm, name):
        self.h, self.px, self.name = np.asarray(h, float), float(px_nm), name

    def at(self, x_nm, y_nm):
        r = y_nm / self.px + (self.h.shape[0] - 1) / 2.0
        c = x_nm / self.px + (self.h.shape[1] - 1) / 2.0
        return ndi.map_coordinates(self.h, [r, c], order=1, mode="reflect")


def run_loop(h, phys, loop, z_gain, seed=1):
    """Firmware constant-current loop over per-tick surface heights h (Å, with drift).
    Returns per-tick z_pos (int), err (int) and hc (float): the COMBINED height estimate
    h = tip height - gap, with the gap recovered from the measured current
    (gap = ln(V / (I R_c)) / 2 kappa).  hc[t] belongs to the position of tick t (the current read
    on tick t+1 is the conversion started on tick t).  NaN where the current carries no height
    information: no current (within 5 sigma of the offset) or clipped.
    Optional phys switches (verification ladder): preamp_hz None = no preamp lag; zero_sub False;
    offset_known = the offset the reconstruction subtracts (default: the true scan_offset)."""
    rng = np.random.default_rng(seed)
    n = len(h)
    sig = phys["adc_noise"]
    noise = rng.normal(0, sig, n) if sig > 0 else np.zeros(n)
    LT = LS.LT
    sp_counts = int(round(loop["setpoint_pa"] / phys["pa_per_count"]))
    sp_log = int(LT[sp_counts]); ki = int(loop["kiga"] * 65536.0)
    V = loop["bias_mv"] / 1000.0; RC = LS.RC; k2 = 2 * phys["kappa"]
    s_set = math.log((V / (sp_counts * phys["pa_per_count"] * 1e-12)) / RC) / k2
    z_tip0 = float(h[0]) + s_set
    ph = phys.get("preamp_hz")
    alpha = 1.0 if not ph else 1 - math.exp(-2 * math.pi * ph * phys["tick_us"] * 1e-6)
    off = phys["scan_offset"]; ppc = phys["pa_per_count"] * 1e-12
    off_k = phys.get("offset_known", off); lo_ok = max(5 * sig, 2.0); zsub = phys.get("zero_sub", True)
    MAXZ = LS.MAX_Z; lim = MAXZ << 32
    iterm = 0; z_pos = 0; i_f = sp_counts * ppc; gap_prev = s_set; tip_prev = z_tip0
    zo = np.empty(n, np.int64); eo = np.empty(n, np.int64)
    meas = np.empty(n); tipv = np.empty(n)
    hv = h.tolist(); nz = noise.tolist(); exp = math.exp
    for t in range(n):
        # ADC on tick t reads the conversion started on tick t-1 (gap of the previous tick)
        I = V / (RC * exp(k2 * gap_prev))
        i_f += alpha * (I - i_f)
        araw = i_f / ppc + off + nz[t]
        adc = 32767 if araw > 32767 else (-32768 if araw < -32768 else int(round(araw)))
        meas[t] = adc - off_k                                       # raw ADC, offset removed
        if zsub and adc == 0 and z_pos != -MAXZ: adc = 32767      # firmware zero substitution (FW 5.6)
        a = adc if adc >= 0 else -adc
        if a > 32767: a = 32767
        err = sp_log - int(LT[a])
        iterm += ki * err
        if iterm > lim: iterm = lim
        elif iterm < -lim: iterm = -lim
        z_pos = iterm >> 32
        tip_prev = z_tip0 - z_gain * z_pos
        g = tip_prev - hv[t]
        gap_prev = 0.3 if g < 0.3 else (60.0 if g > 60.0 else g)
        zo[t] = z_pos; eo[t] = err; tipv[t] = tip_prev
    # ---- combined height estimate (reconstruction side, vectorised)
    # meas[t] measures the gap of tick t-1; optionally undo the known first-order preamp filter
    # (i_f[t] = i_f[t-1] + a (I - i_f[t-1])  =>  I = (i_f[t] - (1-a) i_f[t-1]) / a), smoothed over
    # `preamp_inv_avg` ticks to limit the noise the inversion amplifies.
    ok_raw = (meas > lo_ok) & (meas < 32000 - off_k)
    cur = meas.copy()
    if phys.get("preamp_inverse") and alpha < 1.0:
        inv = np.empty(n); inv[0] = meas[0]
        inv[1:] = (meas[1:] - (1 - alpha) * meas[:-1]) / alpha
        okp = ok_raw.copy(); okp[1:] &= ok_raw[:-1]                 # the inversion uses two ticks
        w = int(phys.get("preamp_inv_avg", 1))
        if w > 1:
            # average only over windows whose ticks are ALL valid: a clipped or lost tick carries
            # no height information and must not leak into its neighbours
            k = np.ones(w)
            wsum = np.convolve(np.where(okp, inv, 0.0), k, mode="same")
            wcnt = np.convolve(okp.astype(float), k, mode="same")
            inv = np.where(wcnt > w - 0.5, wsum / np.maximum(wcnt, 1), np.nan)
            okp &= np.isfinite(inv)
        cur = inv
        ok_raw = okp
    hc = np.full(n, np.nan)
    good = ok_raw[1:] & (cur[1:] > lo_ok)
    with np.errstate(invalid="ignore", divide="ignore"):
        gap = np.log(V / (np.where(good, cur[1:], 1.0) * ppc * RC)) / k2
    hc[:-1] = np.where(good, tipv[:-1] - gap, np.nan)
    if phys.get("fallback") == "bound":
        # where the current carries no height information, use the tightest bound it does give:
        # clipped -> gap <= gap at the clip level; no current -> gap >= gap at the loss threshold
        g_clip = math.log(V / ((32000 - off_k) * ppc * RC)) / k2
        g_lost = math.log(V / (lo_ok * ppc * RC)) / k2
        m = meas[1:]
        fb = np.where(m >= 32000 - off_k, tipv[:-1] - g_clip, tipv[:-1] - g_lost)
        hc[:-1] = np.where(np.isfinite(hc[:-1]), hc[:-1], fb)
    return zo, eo, hc


def simulate(truth, block, scan_nm, phys=PHYS, loop=LOOP, frames=(0,), seed=1, t0_s=0.0, verbose=True):
    """Image `truth` along `block` for the given frame indices.  Returns a list of dicts with
    per-bin commanded positions (nm), bin times (s), mean Z (Å, height = -z*g) and err."""
    spec = SP.Spec.from_dict(block["spec"])
    upn = nm_per_unit(scan_nm, spec)
    fs = 1e6 / phys["tick_us"]
    g = LS.z_gain_A_per_unit(phys["kappa"])
    # the firmware loop runs continuously across frames: build every frame's heights, then run
    # one loop over all ticks (restarting it per frame would reset Z and fake offsets)
    t_start = time.time()
    per, hs_all = [], []
    for f in frames:
        n, x, y = SP.frame_ticks(block, f)
        xc = (x - spec.xo) * upn; yc = (y - spec.yo) * upn
        if phys.get("lateral", True):
            xa, ya = lateral(xc, yc, fs, phys)
        else:
            xa, ya = xc.astype(float), yc.astype(float)
        tsec = t0_s + (f * spec.ticks_per_frame + n) * phys["tick_us"] * 1e-6
        dx, dy = phys["drift_nm_s"]
        hs_all.append(truth.at(xa - dx * tsec, ya - dy * tsec) - phys["zdrift_A_s"] * tsec)
        per.append((f, tsec, xc, yc, xa, ya))
    hs_cat = np.concatenate(hs_all)
    zt_all, et_all, hc_all = run_loop(hs_cat, phys, loop, g, seed)
    out = []
    shp = (spec.segments, spec.bins, spec.spp)
    for k, (f, tsec, xc, yc, xa, ya) in enumerate(per):
        sl = slice(k * spec.ticks_per_frame, (k + 1) * spec.ticks_per_frame)
        zt, et, hc, ht = zt_all[sl], et_all[sl], hc_all[sl].reshape(shp), hs_cat[sl]
        m = SP.reconstruct(block, f)
        with np.errstate(invalid="ignore"):
            hcm = np.nanmean(hc, -1) if np.isfinite(hc).any() else np.full(shp[:2], np.nan)
        out.append(dict(frame=f, x_nm=(m["x"] - spec.xo) * upn, y_nm=(m["y"] - spec.yo) * upn,
                        xa_nm=xa.reshape(shp).mean(-1), ya_nm=ya.reshape(shp).mean(-1),
                        t_s=tsec.reshape(shp).mean(-1), z_A=-(zt.reshape(shp).mean(-1)) * g,
                        h_comb=hcm, h_valid=np.isfinite(hc).mean(-1), h_true=ht.reshape(shp).mean(-1),
                        err=et.reshape(shp).mean(-1), xc=xc[::50], yc=yc[::50], g=g))
    if verbose:
        print(f"   {len(frames)} frame(s), {len(frames) * spec.ticks_per_frame} ticks in {time.time() - t_start:.0f} s", flush=True)
    return out


def grid(frames_out, scan_nm, npx=256, drift=None, t_ref=None, channel="z_A", pos=("x_nm", "y_nm"), method="bin"):
    """Bin samples onto an npx x npx grid over the scan square (nm, centre origin).
    drift=(dx, dy) nm/s: place each bin where its piece of sample was at t_ref (registration).
    pos: which per-bin positions to use (commanded x_nm/y_nm, or actual xa_nm/ya_nm when the
    lateral model is known).  NaN samples (no height information) are skipped."""
    acc = np.zeros((npx, npx)); cnt = np.zeros((npx, npx)); pts_all, val_all = [], []
    for fo in frames_out:
        x, y, v = fo[pos[0]].ravel(), fo[pos[1]].ravel(), fo[channel].ravel()
        keep = np.isfinite(v); x, y, v = x[keep], y[keep], v[keep]
        tt = fo["t_s"].ravel()[keep]
        if drift is not None:
            dt = tt - t_ref
            x, y = x - drift[0] * dt, y - drift[1] * dt
        c = np.floor((x / scan_nm + 0.5) * npx).astype(int); r = np.floor((y / scan_nm + 0.5) * npx).astype(int)
        ok = (c >= 0) & (c < npx) & (r >= 0) & (r < npx)
        np.add.at(acc, (r[ok], c[ok]), v[ok]); np.add.at(cnt, (r[ok], c[ok]), 1)
        pts_all.append(np.c_[x, y]); val_all.append(v)
    if method == "hybrid":
        # interpolate to pixel centres where samples are dense (a sample within 3/4 pixel of the
        # centre); elsewhere (holes from lost / clipped current) keep the binned, filled value
        from scipy.interpolate import griddata
        from scipy.spatial import cKDTree
        u = (np.arange(npx) + 0.5) / npx * scan_nm - scan_nm / 2
        X, Y = np.meshgrid(u, u)
        P = np.concatenate(pts_all); V_ = np.concatenate(val_all)
        gi = griddata(P, V_, (X, Y), method="linear")
        d, _ = cKDTree(P).query(np.c_[X.ravel(), Y.ravel()])
        near = (d.reshape(X.shape) <= 0.75 * scan_nm / npx) & np.isfinite(gi)
        binned = np.where(cnt > 0, acc / np.maximum(cnt, 1), np.nan)
        w = (cnt > 0).astype(float); s = np.nan_to_num(binned)
        num = ndi.gaussian_filter(s * w, 1.0); den = ndi.gaussian_filter(w, 1.0)
        filled = np.where(cnt > 0, binned, np.where(den > 0.05, num / np.maximum(den, 1e-9), np.nan))
        return np.where(near, gi, filled), cnt
    if method == "interp":
        # linear interpolation of the scattered samples to the pixel CENTRES (exact positions kept;
        # binning to pixels instead puts each sample at its pixel's centre, an error up to half a
        # pixel that curved paths do not cancel).  Pixels outside the sampled hull stay NaN.
        from scipy.interpolate import griddata
        u = (np.arange(npx) + 0.5) / npx * scan_nm - scan_nm / 2
        X, Y = np.meshgrid(u, u)
        P = np.concatenate(pts_all); V_ = np.concatenate(val_all)
        img = griddata(P, V_, (X, Y), method="linear")
        return img, cnt
    img = np.where(cnt > 0, acc / np.maximum(cnt, 1), np.nan)
    # fill unvisited pixels by normalised Gaussian smoothing (gaps stay visible in `cnt`)
    w = (cnt > 0).astype(float); s = np.nan_to_num(img)
    num = ndi.gaussian_filter(s * w, 1.0); den = ndi.gaussian_filter(w, 1.0)
    filled = np.where(cnt > 0, img, np.where(den > 0.05, num / np.maximum(den, 1e-9), np.nan))
    return filled, cnt


def truth_grid(truth, scan_nm, npx, t_s=0.0, drift=(0.0, 0.0)):
    """The truth as it sits in the scan frame at time t_s."""
    u = (np.arange(npx) + 0.5) / npx * scan_nm - scan_nm / 2
    X, Y = np.meshgrid(u, u)
    return truth.at(X - drift[0] * t_s, Y - drift[1] * t_s)


def _plane(a, m):
    yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]]
    A = np.c_[yy[m], xx[m], np.ones(m.sum())]
    c, *_ = np.linalg.lstsq(A, a[m], rcond=None)
    return a - (c[0] * yy + c[1] * xx + c[2])


def scores(img, cnt, ref, block, fo_list, scan_nm, fs):
    npx = img.shape[0]
    yy, xx = np.mgrid[0:npx, 0:npx]
    disc = (yy - (npx - 1) / 2) ** 2 + (xx - (npx - 1) / 2) ** 2 <= (0.48 * npx) ** 2
    m = disc & np.isfinite(img)
    a, b = _plane(np.nan_to_num(img), m), _plane(ref, m)
    corr = float(np.corrcoef(a[m], b[m])[0, 1])
    k = np.polyfit(a[m], b[m], 1); resid = np.where(m, b - np.polyval(k, a), 0)
    rmse = float(np.sqrt(np.mean(resid[m] ** 2)))
    gy = np.diff(resid, axis=0)[m[1:] & m[:-1]]; gx = np.diff(resid, axis=1)[m[:, 1:] & m[:, :-1]]
    aniso = float(np.mean(gy ** 2) / max(np.mean(gx ** 2), 1e-12))
    cov = float((cnt[disc] > 0).mean())
    hole = float(ndi.distance_transform_edt(~(cnt > 0) & disc).max() * scan_nm / npx)
    hits = cnt[disc & (cnt > 0)]; cv = float(hits.std() / hits.mean()) if hits.size else np.nan
    # drive: commanded positions (decimated x50 -> fs/50)
    xc = np.concatenate([f["xc"] for f in fo_list]); yc = np.concatenate([f["yc"] for f in fo_list])
    fsd = fs / 50
    def band(s):
        P = np.abs(np.fft.rfft((s - s.mean()) * np.hanning(len(s)))) ** 2; fr = np.fft.rfftfreq(len(s), 1 / fsd)
        return P[(fr >= 100) & (fr <= 300)].sum() / P[fr > 0].sum()
    drive = float(max(band(xc), band(yc)))
    vx = np.gradient(xc) * fsd; vy = np.gradient(yc) * fsd
    acc = np.hypot(np.gradient(vx) * fsd, np.gradient(vy) * fsd)
    return dict(corr=corr, rmse_A=rmse, resid_aniso=aniso, coverage=cov, largest_hole_nm=hole, hit_cv=cv,
                drive_100_300Hz=drive, peak_acc_um_s2=float(np.percentile(acc, 99.9) / 1000),
                speed_nm_s_p5_p95=[float(np.percentile(np.hypot(vx, vy), 5)), float(np.percentile(np.hypot(vx, vy), 95))])
