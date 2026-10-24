"""loop_sim — tick-level simulation of the firmware constant-current loop (FW 5.6).

Ports the per-tick path of controlTick() (stm_firmware.hpp:296-334):
    adc = read_ADC();  if feedback and adc == 0 and Z not at limit: adc = 32767
    err = setpointLog - logTable[abs(adc)];  iTerm += Ki_isr * err;  z_pos = iTerm >> 32
and adds the physics around it: a tip scanning a synthetic rough surface at the Oct 22
settings, tunnelling current I = V / (Rc * exp(2*kappa*gap)), the ADC (1X preamp, 3.125 pA per
count, clip at 32767), ADC noise, and an ADC offset that is larger while scanning (the
"phantom offset", OI-3).  Firmware variants test candidate fixes (roadmap F4) before any
firmware change.

Height scale: z_pos units are converted to Angstrom with the gain that reproduces the
report's loop-crossover estimate (15.7 Hz per unit KIGA at 100 kHz).
"""
import os, re, math, json, argparse
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
LOGTABLE = os.path.join(REPO, "software", "firmware", "arduinosrc", "main", "logTable.hpp")

F_ISR = 100_000.0
PA_PER_COUNT = 3.125           # 1X preamp: 160 counts = 500 pA
RC = 12906.0                   # point-contact resistance (ohm)
MAX_Z = (1 << 19) - 1


def load_logtable():
    s = open(LOGTABLE).read()
    v = np.array([int(x) for x in re.findall(r"-?\d+", s.split("{", 1)[1])][:32768], dtype=np.int64)
    return v


LT = load_logtable()


def z_gain_A_per_unit(kappa):
    """Angstrom per z_pos unit so that crossover = 15.7 Hz per unit KIGA (report estimate)."""
    per_ln = (LT[1000] - LT[160]) / math.log(1000 / 160)            # log-table units per ln(I)
    loop_per_A = (F_ISR / 65536.0) * per_ln * 2 * kappa             # rad/s per (KIGA * A/unit)
    return 2 * math.pi * 15.7 / loop_per_A


def surface(seed=1, n=256, amp=6.0, mounds=18):
    """Height map (Angstrom), 30 nm square: smooth roughness plus Gaussian mounds."""
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:n, 0:n] / n * 30.0
    h = np.zeros((n, n))
    for _ in range(mounds):
        cx, cy = rng.uniform(0, 30, 2); w = rng.uniform(1.5, 5.0); a = rng.uniform(0.3, 1.0) * amp
        h += a * np.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (2 * w * w))
    f = np.fft.fft2(rng.normal(size=(n, n)))
    k = np.hypot(*np.meshgrid(np.fft.fftfreq(n), np.fft.fftfreq(n)))
    rough = np.real(np.fft.ifft2(f * np.exp(-(k / 0.03) ** 2)))
    h += rough / rough.std() * amp * 0.25
    return h - h.mean()


def run(variant="as_is", kiga=2.3, amp=6.0, lines=24, px=256, line_hz=10.5, bias_mv=49.6,
        setpoint_counts=160, kappa=1.025, scan_offset=-55.0, idle_offset=-15.0, noise=4.0,
        scanning=True, seed=1, ff_slope=False):
    """Simulate `lines` scan lines (trace + retrace each). Returns per-tick stats and images."""
    rng = np.random.default_rng(seed + 7)
    H = surface(seed, px, amp)
    g = z_gain_A_per_unit(kappa)
    ki_isr = int(kiga * 65536.0)
    sp_log = LT[setpoint_counts]
    off = scan_offset if scanning else idle_offset
    ticks_line = int(F_ISR / line_hz); half = ticks_line // 2
    V = bias_mv / 1000.0
    # start the tip at the setpoint gap above the first pixel
    s_set = math.log((V / (setpoint_counts * PA_PER_COUNT * 1e-12)) / RC) / (2 * kappa)
    z_tip0 = H[0, 0] + s_set                       # Angstrom; tip height = z_tip0 - g*z_pos (extend lowers the tip)
    iterm = 0; z_pos = 0
    n_lost = n_clip = n_sub = n_in = 0; tot = 0
    img_z = np.zeros((lines, 2 * px)); img_e = np.zeros((lines, 2 * px)); acc_z = np.zeros(2 * px); acc_e = np.zeros(2 * px); cnt = np.zeros(2 * px)
    true_line = np.zeros((lines, px))
    for ln in range(lines):
        row = ln % px
        acc_z[:] = 0; acc_e[:] = 0; cnt[:] = 0
        hrow = H[row]
        true_line[ln] = hrow
        for t in range(ticks_line):
            # tip x position: trace left->right, retrace right->left
            if scanning:
                u = t / half if t < half else 2 - t / half
                xi = min(px - 1, int(u * (px - 1) + 0.5)); col = t * 2 * px // ticks_line
            else:
                xi = 0; col = 0
            h = hrow[xi]
            tip = z_tip0 - g * z_pos
            gap = tip - h
            if gap < 0.3: gap = 0.3                 # contact floor
            if gap > 60.0: gap = 60.0               # far away: current is effectively zero
            I = V / (RC * math.exp(2 * kappa * gap))
            adc = I * 1e12 / PA_PER_COUNT + off + rng.normal(0, noise)
            adc = int(min(32767, max(-32768, round(adc))))
            # ---- firmware variants
            if variant in ("as_is", "no_substitution"):
                a = adc
                if variant == "as_is" and adc == 0 and z_pos != -MAX_Z:
                    a = 32767; n_sub += 1
                mag = abs(a)
            elif variant in ("offset_corrected", "offset_corrected_no_sub"):
                a = adc - int(round(off))           # subtract the measured offset (live, per state)
                if variant == "offset_corrected" and adc == 0 and z_pos != -MAX_Z:
                    a = 32767; n_sub += 1
                mag = abs(a)
            elif variant == "signed":
                a = adc - int(round(off))           # offset removed, bias sign known: only positive = current
                mag = a if a > 0 else 0
            else:
                raise ValueError(variant)
            mag = min(32767, mag)
            err = int(sp_log - LT[mag])
            iterm += ki_isr * err
            lim = MAX_Z << 32
            iterm = max(-lim, min(lim, iterm))
            z_pos = iterm >> 32
            # ---- statistics on the TRUE current
            true_counts = I * 1e12 / PA_PER_COUNT
            if adc >= 32767: n_clip += 1
            elif true_counts < 5: n_lost += 1
            else: n_in += 1
            tot += 1
            acc_z[col] += z_pos; acc_e[col] += err; cnt[col] += 1
        img_z[ln] = acc_z / np.maximum(cnt, 1); img_e[ln] = acc_e / np.maximum(cnt, 1)
    # image quality: trace Z vs true surface, after per-line offset/slope removal
    zt = -img_z[:, :px] * g; zr = -img_z[:, px:][:, ::-1] * g
    def lev(a):
        x = np.arange(a.shape[1]); A = np.vstack([x, np.ones_like(x)]).T
        c, *_ = np.linalg.lstsq(A, a.T, rcond=None); return a - (A @ c).T
    tl, rl, hl = lev(zt), lev(zr), lev(true_line)
    corr = float(np.corrcoef(tl.ravel(), hl.ravel())[0, 1])
    L, S = (tl - rl) / 2, (tl + rl) / 2
    return dict(variant=variant, kiga=kiga, amp=amp, scanning=scanning,
                lost_pct=100 * n_lost / tot, clip_pct=100 * n_clip / tot, in_pct=100 * n_in / tot,
                substituted_pct=100 * n_sub / tot, z_vs_true_corr=corr,
                lag_share=float(L.var() / (L.var() + S.var())), z_follow=float(tl.std() / hl.std()))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--mode", default="calibrate")
    a = ap.parse_args()
    print(f"z gain {z_gain_A_per_unit(1.025)*1000:.3f} mA per z_pos unit")
