"""Pure, Qt-free stability / drift mathematics.

Single source of truth shared by the live GUI (``widget.py``) and the
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
