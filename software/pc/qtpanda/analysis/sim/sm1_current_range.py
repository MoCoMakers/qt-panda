"""SM1: calibrate the simulator's height scale so its usable-current fraction matches real scans.

Real (RC1): Sep 24 #1802-#1812 had usable current (between the no-current level and clipping) in
50% of pixels.  The simulator at the stated #1808 error-channel scale had ~100%.  Here the #1808
truth is scaled by k at Sep 24's own settings (27.1 nm, 512 px/line, 1 tick/pixel, KIGA 1.1444,
1000 pA, -49.6 mV, Sep 24 drift), the usable fraction is measured per pixel exactly as RC1 did
(implied |ADC| between 64 and 32000 counts from the per-pixel mean error), and the full-physics
recreation (calibrated positions, final reconstruction) is scored at each k."""
import os, sys, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import scan_sim as M, truths as T, ladder as L
import scan_paths as SP

LOG_K = (2 ** 19 - 1) / np.log(2 ** 15 + 1)
SPEC = SP.Spec(spp=1, bins=512, segments=512, scan_size=262144)
LOOP = dict(M.LOOP, kiga=1.1444, setpoint_pa=1000.0)
SCAN_NM = 27.112
PHYS = dict(M.PHYS, hyst_frac=0.05, preamp_inverse=True, preamp_inv_avg=3, drift_nm_s=(0.12 * SCAN_NM / 256, -0.23 * SCAN_NM / 256), zdrift_A_s=0.0)
sp_counts = int(round(LOOP["setpoint_pa"] / PHYS["pa_per_count"])); SPLOG = M.LS.LT[sp_counts]


def usable(err_mean):
    a = np.exp((SPLOG - err_mean) / LOG_K) - 1          # implied |ADC| from the mean error (as RC1)
    return float(np.mean((a > 64) & (a < 32000)))


base = T.sep24_error()[0]
out = {}
blk = SP.default_block(SPEC)
for k in (1.0, 2.0, 2.6, 3.5, 5.0, 8.0):
    tr = M.Truth(base.h * k, base.px, base.name)
    fo = M.simulate(tr, blk, SCAN_NM, PHYS, LOOP, frames=(0,), verbose=False)
    f = fo[0]
    u_pix = usable(f["err"])
    u_tick = float(np.mean(f["h_valid"]))
    t_ref = float(f["t_s"].mean())
    ref = M.truth_grid(tr, SCAN_NM, 256, t_ref, PHYS["drift_nm_s"])
    kw = dict(drift=PHYS["drift_nm_s"], t_ref=t_ref)
    rec, _ = M.grid(fo, SCAN_NM, 256, channel="h_comb", pos=("xa_nm", "ya_nm"), method="hybrid", **kw)
    zon, _ = M.grid(fo, SCAN_NM, 256, channel="z_A", pos=("xa_nm", "ya_nm"), **kw)
    for ff in fo: ff["negerr"] = -ff["err"]
    ern, _ = M.grid(fo, SCAN_NM, 256, channel="negerr", pos=("xa_nm", "ya_nm"), **kw)
    r = dict(usable_pixels=u_pix, usable_ticks=u_tick, combined=L.score(rec, ref)["corr"], z_only=L.score(zon, ref)["corr"],
             error_only=L.score(ern, ref)["corr"], truth_rms_A=float(tr.h.std()))
    out[str(k)] = r
    print(f"k={k:4.1f}  truth rms {r['truth_rms_A']:.2f} Å  usable current: pixels {u_pix*100:3.0f}% ticks {u_tick*100:3.0f}%   "
          f"recreation: combined {r['combined']:.3f}  Z only {r['z_only']:.3f}  error only {r['error_only']:.3f}", flush=True)
json.dump(out, open(os.path.join(HERE, "sm1_current_range.json"), "w"), indent=1)
