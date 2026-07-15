"""Scan-speed fidelity: preamp bandwidth, pixel dwell, and what a scan can resolve.

Physical picture (bench session 2026-07-15)
-------------------------------------------
The tunneling current is converted to a voltage by a 100 MOhm transimpedance
preamp.  Any transimpedance stage is a first-order low-pass: the feedback
resistor R and the (stray + feedback) capacitance C across it give

    f_3dB = 1 / (2 pi R C)          tau = R C

With R = 100 MOhm, C = 0.3..3 pF spans f_3dB ~ 5.3 kHz .. 530 Hz
(tau = 30 us .. 300 us).  THIS FILTERING HAPPENS BEFORE THE ADC — no amount
of digital averaging can recover what the RC already removed.

While scanning, the tip moves at

    v = 2 * scan_size * line_rate        (trace + retrace per line period)

so the RC time constant smears the current record over a *spatial* length

    L_blur = v * tau

and a feature of size d (spatial frequency f_s = 1/(2d), temporal frequency
f_t = v * f_s) is attenuated by the first-order MTF

    |H| = 1 / sqrt(1 + (f_t / f_3dB)^2) = 1 / sqrt(1 + (2 pi v tau f_s)^2).

The MTF>0.5 criterion gives the smallest resolvable feature

    d_min = pi * v * tau / sqrt(3)  ~=  1.814 * v * tau,

floored by the pixel grid at 2 pixels (Nyquist).

Firmware truth (stm_firmware.hpp / updateStepSizes, FW 5.2)
-----------------------------------------------------------
The ISR ticks every 40 us (25 kHz).  Samples averaged per pixel derive from
the REQUESTED line rate:

    spp = trunc( 1e6 / (line_rate * 40 * pixels_per_line) ),  clamped 1..4000
    (SPPX <n> overrides spp directly; 0 = auto)

and the TRUE line rate is then set by the tick budget, not the request:

    true_line_rate = 1e6 / (40 * pixels_per_line * spp)

This is the "30 Hz -> 48.8 Hz" effect: at 30 Hz x 512 px the derived spp is
1.63 -> truncates to 1, and the scan actually runs 48.83 Hz.

Noise: ADC floor sigma ~ 5 counts rms (3.125 pA/LSB -> ~15.6 pA); averaging
spp samples reduces it by sqrt(spp).  Tonight's contact-map signal band was
0..1700 counts (0..5.3 nA); the per-pixel SNR below is quoted for a 1 nA
(320-count) feature.

Legacy SCST scans STEP the tip and dwell: measured tonight, 69 s for a
256 x 256 frame with 2-sample averaging -> 1.05 ms/pixel.  With dwell >> tau
the preamp settles (residual exp(-dwell/tau)) and resolution is pixel-limited.

Region calibration: tonight's shared region was 39,322 LSB; the session
journal shows SCSZ 13107 <-> 10.00 nm, so 1 LSB = 7.6295e-4 nm and the
region is 30.0 nm square.

All lengths nm, times s, frequencies Hz at the boundaries unless noted.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# --- preamp -------------------------------------------------------------------
R_FEEDBACK_OHM = 100e6          # transimpedance resistor
C_NOMINAL_PF = 1.0              # nominal stray+feedback capacitance (ASSUMPTION)
C_SWEEP_PF = (0.3, 1.0, 3.0, 10.0)   # plausible homebrew band incl. cabled worst case

# --- firmware timing (FW 5.2) ---------------------------------------------------
ISR_TICK_US = 40.0              # control_dt_us default -> 25 kHz
SPP_MAX = 4000                  # zAvg int32 overflow clamp in updateStepSizes

# --- ADC / signal scale ---------------------------------------------------------
PA_PER_LSB = 3.125              # LTC2326-16 with the 1X preamp chain
ADC_FLOOR_SIGMA_LSB = 5.0       # observed quiet-floor rms, counts
SIGNAL_REFERENCE_NA = 1.0       # SNR quoted for a 1 nA feature
CONTACT_BAND_LSB = 1700         # tonight's morphology image spanned 0..~1700 counts

# --- tonight's shared region -----------------------------------------------------
NM_PER_LSB = 10.0 / 13107.0     # journal: SCSZ 13107 == 10.00 nm scan size
REGION_LSB = 39322              # journal: SCSZ 39322 (box 13107..52429)
REGION_NM = REGION_LSB * NM_PER_LSB   # = 30.0 nm

# --- legacy SCST measured timing -------------------------------------------------
LEGACY_FRAME_S = 69.0           # measured: SCST 02:02:42 -> 02:03:51
LEGACY_PIXELS = 256             # 256 x 256 grid
LEGACY_DWELL_S = LEGACY_FRAME_S / (LEGACY_PIXELS * LEGACY_PIXELS)  # 1.05 ms


def preamp_tau_s(c_pf: float = C_NOMINAL_PF, r_ohm: float = R_FEEDBACK_OHM) -> float:
    """RC time constant of the transimpedance stage."""
    return r_ohm * c_pf * 1e-12


def preamp_f3db_hz(c_pf: float = C_NOMINAL_PF, r_ohm: float = R_FEEDBACK_OHM) -> float:
    """-3 dB bandwidth of the transimpedance stage."""
    return 1.0 / (2.0 * math.pi * preamp_tau_s(c_pf, r_ohm))


def derived_spp(line_rate_hz: float, pixels_per_line: int) -> int:
    """Firmware-derived samples/pixel for a REQUESTED line rate (SPPX 0)."""
    raw = 1e6 / (line_rate_hz * ISR_TICK_US * pixels_per_line)
    return max(1, min(SPP_MAX, int(raw)))          # C truncation, then clamps


def true_line_rate_hz(pixels_per_line: int, spp: int) -> float:
    """The line rate the ISR actually produces for a given spp."""
    return 1e6 / (ISR_TICK_US * pixels_per_line * spp)


def tip_velocity_nm_s(scan_size_nm: float, line_rate_hz: float) -> float:
    """Tip speed along the fast axis: trace + retrace each line period."""
    return 2.0 * scan_size_nm * line_rate_hz


def blur_length_nm(v_nm_s: float, c_pf: float = C_NOMINAL_PF) -> float:
    """Spatial smear of the current record: L = v * tau."""
    return v_nm_s * preamp_tau_s(c_pf)


def mtf(feature_nm: float, v_nm_s: float, c_pf: float = C_NOMINAL_PF) -> float:
    """First-order attenuation of a feature of size d at tip speed v.

    Feature -> spatial frequency f_s = 1/(2d); temporal f_t = v*f_s;
    |H| = 1/sqrt(1+(f_t/f_3dB)^2).
    """
    tau = preamp_tau_s(c_pf)
    f_t = v_nm_s / (2.0 * feature_nm)
    return 1.0 / math.sqrt(1.0 + (2.0 * math.pi * f_t * tau) ** 2)


def d_min_mtf50_nm(v_nm_s: float, c_pf: float = C_NOMINAL_PF) -> float:
    """Smallest feature with MTF > 0.5:  d = pi*v*tau/sqrt(3) = 1.814 v tau."""
    return math.pi * v_nm_s * preamp_tau_s(c_pf) / math.sqrt(3.0)


def max_line_rate_hz(feature_nm: float, scan_size_nm: float,
                     c_pf: float = C_NOMINAL_PF) -> float:
    """Fastest line rate that still resolves ``feature_nm`` at MTF > 0.5.

    From d_min = 1.814 * v * tau and v = 2 * S * lr.
    """
    tau = preamp_tau_s(c_pf)
    v_max = math.sqrt(3.0) * feature_nm / (math.pi * tau)
    return v_max / (2.0 * scan_size_nm)


def snr_per_pixel(spp: int, signal_na: float = SIGNAL_REFERENCE_NA) -> float:
    """Per-pixel SNR for a given signal after spp-sample averaging."""
    signal_lsb = signal_na * 1000.0 / PA_PER_LSB
    return signal_lsb * math.sqrt(spp) / ADC_FLOOR_SIGMA_LSB


@dataclass(frozen=True)
class ScanConfig:
    """One resolved scan configuration over a square region."""

    label: str
    engine: str                # "legacy SCST" | "continuous"
    scan_size_nm: float
    pixels_per_line: int       # continuous: trace+retrace; legacy: grid width
    requested_line_rate_hz: float | None
    spp: int
    true_line_rate_hz: float
    dwell_s: float             # time spent generating one pixel's value
    v_nm_s: float              # tip speed (0-order for legacy stepping: ~0 at dwell)
    stepped: bool              # True = settle-then-sample (legacy)

    @property
    def pixels_across(self) -> int:
        """Image pixels across the scan width (continuous halves the line)."""
        return self.pixels_per_line if self.stepped else self.pixels_per_line // 2

    @property
    def pixel_nm(self) -> float:
        return self.scan_size_nm / self.pixels_across

    @property
    def nyquist_nm(self) -> float:
        return 2.0 * self.pixel_nm

    def blur_nm(self, c_pf: float = C_NOMINAL_PF) -> float:
        if self.stepped:
            return 0.0          # settled point sample (dwell >> tau; see residual)
        return blur_length_nm(self.v_nm_s, c_pf)

    def settle_residual(self, c_pf: float = C_NOMINAL_PF) -> float:
        """Stepped mode: fraction of the previous pixel still in the reading."""
        return math.exp(-self.dwell_s / preamp_tau_s(c_pf))

    def d_min_nm(self, c_pf: float = C_NOMINAL_PF) -> float:
        """Smallest resolvable feature: max(preamp MTF>0.5 limit, 2 pixels)."""
        if self.stepped:
            return self.nyquist_nm
        return max(d_min_mtf50_nm(self.v_nm_s, c_pf), self.nyquist_nm)

    def snr(self, signal_na: float = SIGNAL_REFERENCE_NA) -> float:
        return snr_per_pixel(self.spp, signal_na)

    @property
    def frame_time_s(self) -> float:
        if self.stepped:
            return self.dwell_s * self.pixels_per_line * self.pixels_per_line
        # continuous frame = pixels_per_line lines (square scan)
        return self.pixels_per_line / self.true_line_rate_hz


def legacy_config(scan_size_nm: float = REGION_NM,
                  pixels: int = LEGACY_PIXELS,
                  dwell_s: float = LEGACY_DWELL_S,
                  samples: int = 2,
                  label: str | None = None) -> ScanConfig:
    """The measured legacy SCST configuration (step, settle, average)."""
    return ScanConfig(
        label=label or f"legacy SCST {pixels}px, {samples} samples",
        engine="legacy SCST",
        scan_size_nm=scan_size_nm,
        pixels_per_line=pixels,
        requested_line_rate_hz=None,
        spp=samples,
        true_line_rate_hz=1.0 / (dwell_s * pixels),
        dwell_s=dwell_s,
        v_nm_s=0.0,
        stepped=True,
    )


def continuous_config(scan_size_nm: float = REGION_NM,
                      pixels_per_line: int = 512,
                      requested_line_rate_hz: float = 30.0,
                      sppx: int = 0,
                      label: str | None = None) -> ScanConfig:
    """A continuous-scan configuration resolved through the firmware rules.

    ``sppx`` = 0 derives spp from the requested line rate (with the clamp
    that produced the 30->48.8 Hz surprise); > 0 pins it, and the true line
    rate follows from the tick budget REGARDLESS of the requested value.
    """
    if sppx > 0:
        spp = min(SPP_MAX, sppx)
    else:
        spp = derived_spp(requested_line_rate_hz, pixels_per_line)
    lr = true_line_rate_hz(pixels_per_line, spp)
    v = tip_velocity_nm_s(scan_size_nm, lr)
    if label is None:
        src = f"SPPX {sppx}" if sppx > 0 else f"req {requested_line_rate_hz:g} Hz, auto"
        label = f"continuous {pixels_per_line}px, {src}"
    return ScanConfig(
        label=label,
        engine="continuous",
        scan_size_nm=scan_size_nm,
        pixels_per_line=pixels_per_line,
        requested_line_rate_hz=requested_line_rate_hz,
        spp=spp,
        true_line_rate_hz=lr,
        dwell_s=spp * ISR_TICK_US * 1e-6,
        v_nm_s=v,
        stepped=False,
    )


def step_edge_response(x_nm, v_nm_s: float, c_pf: float = C_NOMINAL_PF):
    """1-D response of the preamp to a unit step edge at x = 0, while moving
    at v: y(x) = 1 - exp(-x / (v tau)) for x > 0 (numpy-friendly)."""
    import numpy as np
    L = max(v_nm_s * preamp_tau_s(c_pf), 1e-12)
    x = np.asarray(x_nm, dtype=float)
    return np.where(x <= 0.0, 0.0, 1.0 - np.exp(-x / L))
