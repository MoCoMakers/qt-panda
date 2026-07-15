"""Pure, Qt-free stability / drift mathematics.

Single source of truth shared by the live GUI (``main.py``) and the
software-mockup driver (``docs/ai/research-harness/software-mockup``), so the
Arduino emulator validates *exactly* the math the real application runs.

Physics: tunneling current is exponential in the gap, ``I = I0 * exp(-2*kappa*z)``.
Working in ``ln|I|`` linearises gap motion:
  * a constant z-drift ``v_z`` makes ``ln|I|`` linear in time with
    slope ``-2*kappa*v_z``  ->  ``v_z = -(1/2kappa) * d(lnI)/dt``;
  * the spread of ``ln|I|`` maps to a mechanical z-jitter amplitude
    ``sigma_z = std(lnI) / (2*kappa)``.
"""

import numpy as np


def kappa_per_m(work_function_eV: float = 4.0) -> float:
    """Tunneling decay constant kappa in 1/m.

    kappa = sqrt(2 m phi)/hbar ~= 0.5123 * sqrt(phi[eV])  [1/Angstrom].
    Multiply by 1e10 to convert 1/Angstrom -> 1/m.
    """
    return 0.5123e10 * (work_function_eV ** 0.5)


def pm_per_ln(work_function_eV: float = 4.0) -> float:
    """Picometres of gap motion per unit change in ln(I) = 1/(2*kappa).

    For phi = 4 eV this is ~48.8 pm (a decade of current ~= 1.1 Angstrom).
    """
    return 1e12 / (2.0 * kappa_per_m(work_function_eV))


def drift_metrics(times_ms, amps, pm_per_ln_value, mad_n: float = 5.0, min_n: int = 8):
    """Estimate z-drift velocity and mechanical jitter from parallel
    (time_millis, current-in-amps) arrays.

    Robust (median +/- N*MAD in log space) so a tip crash / noise spike does
    not corrupt the least-squares slope. Returns a dict, or ``None`` when there
    is not enough usable in-tunneling data.

    Keys: vz_pm_s, r2, jitter_pm, skew, n, span_s.
    """
    if times_ms is None or len(times_ms) < min_n:
        return None

    t = np.asarray(times_ms, dtype=float)
    a = np.abs(np.asarray(amps, dtype=float))

    # Only samples with real (positive-magnitude) current can go to log.
    good = a > 0
    if good.sum() < min_n:
        return None
    t = (t[good] - t[good][0]) / 1000.0     # seconds from first usable sample
    ln_i = np.log(a[good])

    # Robust rejection of log-space outliers.
    med = np.median(ln_i)
    mad = np.median(np.abs(ln_i - med))
    if mad > 0:
        keep = np.abs(ln_i - med) <= mad_n * 1.4826 * mad
        t, ln_i = t[keep], ln_i[keep]
    if ln_i.size < min_n:
        return None

    span = t[-1] - t[0]
    if span <= 0:
        return None

    # Linear fit ln_i = slope*t + b  ->  drift velocity.
    slope, b = np.polyfit(t, ln_i, 1)
    fit = slope * t + b
    ss_res = float(np.sum((ln_i - fit) ** 2))
    ss_tot = float(np.sum((ln_i - ln_i.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    # v_z = -(1/2kappa) d(lnI)/dt ; pm_per_ln_value is 1/(2kappa) in pm.
    vz_pm_s = -slope * pm_per_ln_value
    jitter_pm = float(ln_i.std()) * pm_per_ln_value

    sd = ln_i.std()
    skew = float(np.mean(((ln_i - ln_i.mean()) / sd) ** 3)) if sd > 0 else 0.0

    return {
        "vz_pm_s": vz_pm_s, "r2": r2, "jitter_pm": jitter_pm,
        "skew": skew, "n": int(ln_i.size), "span_s": span,
    }


def resample_uniform(times_ms, amps, min_n=16):
    """Resample an irregularly-polled (time_millis, amp) series onto a
    uniform time grid (linear interpolation) at the median sample rate.

    Necessary because GSTS polling arrives at whatever cadence the firmware
    round-trip actually delivers (subject to jitter and occasional dropped
    replies), while FFT/Allan-deviation both assume evenly spaced samples.

    Returns (t_uniform_s, y_uniform, fs_hz), or None if there is not enough
    data to resample meaningfully.
    """
    if times_ms is None or len(times_ms) < min_n:
        return None
    t = np.asarray(times_ms, dtype=float)
    y = np.asarray(amps, dtype=float)
    order = np.argsort(t)
    t, y = t[order], y[order]
    t = (t - t[0]) / 1000.0

    dt = np.diff(t)
    dt = dt[dt > 0]
    if dt.size == 0:
        return None
    dt_median = np.median(dt)
    if dt_median <= 0:
        return None
    fs = 1.0 / dt_median

    n = int(t[-1] / dt_median)
    if n < min_n:
        return None
    t_uniform = np.arange(n) * dt_median
    y_uniform = np.interp(t_uniform, t, y)
    return t_uniform, y_uniform, fs


def power_spectrum(times_ms, amps, min_n=16):
    """One-sided power spectral density of the current stream.

    Linearly detrends first (removes DC and any steady drift ramp, which
    would otherwise dominate the low-frequency bins), then applies a Hann
    window before an FFT periodogram, so a genuine mechanical resonance
    (tip/collet ringing) shows up as a clean peak rather than being buried
    under drift.

    Returns a dict (freqs_hz, psd, peak_freq_hz, peak_power, peak_snr,
    peak_snr_threshold, peak_significant, fs_hz, n), or None if there is not
    enough data.

    ``peak_snr`` is the peak power over the median of the (non-DC) spectrum.
    The argmax of even a perfectly flat noise spectrum is just the tallest
    random fluctuation, and for exponentially-distributed periodogram bins
    the tallest of n_bins is *expected* at ~log2(n_bins) times the median —
    so significance cannot be a fixed ratio.  ``peak_snr_threshold`` is set
    from the false-alarm probability P(max > x*median) = 1-(1-2^-x)^n_bins,
    solved for x at P=1%: x = log2(n_bins/0.01).  ``peak_significant`` is
    True only when the peak clears that, i.e. a <1% chance the "resonance"
    is pure noise.
    """
    resampled = resample_uniform(times_ms, amps, min_n=min_n)
    if resampled is None:
        return None
    t, y, fs = resampled
    n = y.size

    slope, intercept = np.polyfit(t, y, 1)
    y_detrended = y - (slope * t + intercept)

    window = np.hanning(n)
    y_windowed = y_detrended * window

    spectrum = np.fft.rfft(y_windowed)
    freqs = np.fft.rfftfreq(n, d=1.0 / fs)
    if freqs.size < 2:
        return None

    # Periodogram scaling (power per Hz); fold negative-frequency energy
    # into the one-sided spectrum (all bins except DC and, for even n, Nyquist).
    psd = (np.abs(spectrum) ** 2) / (fs * np.sum(window ** 2))
    fold_end = -1 if n % 2 == 0 else None
    psd[1:fold_end] *= 2.0

    # Exclude the DC bin when hunting for a resonance peak.
    peak_idx = 1 + int(np.argmax(psd[1:]))
    n_bins = psd[1:].size
    floor = float(np.median(psd[1:]))
    peak_snr = float(psd[peak_idx] / floor) if floor > 0 else float("inf")
    snr_threshold = float(np.log2(n_bins / 0.01))

    return {
        "freqs_hz": freqs, "psd": psd, "fs_hz": fs, "n": n,
        "peak_freq_hz": float(freqs[peak_idx]),
        "peak_power": float(psd[peak_idx]),
        "peak_snr": peak_snr,
        "peak_snr_threshold": snr_threshold,
        "peak_significant": bool(peak_snr >= snr_threshold),
    }


def allan_deviation(times_ms, amps, min_n=32, n_taus=20):
    """Non-overlapping Allan deviation sigma_A(tau) vs averaging time tau.

    Classifies the noise: white noise gives a -1/2 log-log slope, random-walk
    (Brownian) wander gives +1/2, and linear (deterministic) drift gives +1.
    The minimum of sigma_A(tau) predicts the best achievable integration /
    scan-line dwell time before drift dominates.

    Returns a dict (taus_s, sigma_a, ref_white, ref_randomwalk, ref_drift,
    slope, tau_opt_s, sigma_min), or None if there is not enough data.
    """
    resampled = resample_uniform(times_ms, amps, min_n=min_n)
    if resampled is None:
        return None
    t, y, fs = resampled
    n = y.size
    dt = 1.0 / fs

    max_m = max(n // 4, 1)
    ms = np.unique(np.round(np.logspace(0, np.log10(max_m), n_taus)).astype(int))
    ms = ms[ms >= 1]

    taus, sigmas = [], []
    for m in ms:
        n_clusters = n // m
        if n_clusters < 3:
            continue
        trimmed = y[: n_clusters * m].reshape(n_clusters, m)
        cluster_means = trimmed.mean(axis=1)
        diffs = np.diff(cluster_means)
        avar = 0.5 * np.mean(diffs ** 2)
        taus.append(m * dt)
        sigmas.append(np.sqrt(avar))

    if len(taus) < 3:
        return None

    taus = np.asarray(taus)
    sigmas = np.asarray(sigmas)

    # Apparent log-log slope over the observed range (noise-type classifier).
    log_t, log_s = np.log10(taus), np.log10(sigmas)
    slope, intercept = np.polyfit(log_t, log_s, 1)

    # Reference guide lines anchored to the first point, for overlay.
    ref = sigmas[0]
    ref_white = ref * (taus / taus[0]) ** -0.5
    ref_randomwalk = ref * (taus / taus[0]) ** 0.5
    ref_drift = ref * (taus / taus[0]) ** 1.0

    tau_opt_idx = int(np.argmin(sigmas))

    return {
        "taus_s": taus, "sigma_a": sigmas,
        "ref_white": ref_white, "ref_randomwalk": ref_randomwalk, "ref_drift": ref_drift,
        "slope": float(slope),
        "tau_opt_s": float(taus[tau_opt_idx]),
        "sigma_min": float(sigmas[tau_opt_idx]),
    }


def sigma_to_pm(sigma_A, mean_current_A, pm_per_ln_value, max_ratio=0.5):
    """Convert a current-noise amplitude (e.g. Allan sigma_min, in Amps) to
    the equivalent gap jitter in pm.

    Small-signal linearisation of I = I0*exp(-2*kappa*z):
      dI/|I| ~= d(lnI) = -2*kappa*dz  ->  sigma_z = (sigma_I/|I|) / (2*kappa).

    Only meaningful while tunneling: returns None when the mean current is
    zero/non-finite, or when sigma_I/|I| exceeds ``max_ratio`` (fluctuations
    comparable to the mean break the linearisation — e.g. an air scan where
    the "current" is just amplifier noise around zero).
    """
    if mean_current_A is None:
        return None
    mean_abs = abs(float(mean_current_A))
    if not np.isfinite(mean_abs) or mean_abs <= 0:
        return None
    ratio = float(sigma_A) / mean_abs
    if ratio > max_ratio:
        return None
    return ratio * pm_per_ln_value


def classify_allan_slope(slope):
    """Map an observed Allan-deviation log-log slope to the nearest
    canonical noise type (white / random-walk / linear-drift)."""
    candidates = {
        "white noise": -0.5,
        "random-walk (Brownian)": 0.5,
        "linear drift": 1.0,
    }
    return min(candidates, key=lambda k: abs(candidates[k] - slope))
