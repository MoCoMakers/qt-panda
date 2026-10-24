"""Check the two reconstruction fixes on the #1808 truth:
(1) interpolate samples to pixel centres instead of binning (curved paths), and
(2) undo the known first-order preamp filter before reading the gap from the current."""
import os, sys, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ladder as L, scan_sim as M, truths as T

truth = T.sep24_error()[0]
FULL = dict(adc_noise=4.0, preamp_hz=400.0, scan_offset=-55.0, zero_sub=True, lateral=True,
            drift_nm_s=(0.0, -0.066), zdrift_A_s=0.39)
cases = [("L0 geometry", {}, "h_true", "cmd"),
         ("L3 preamp, no inversion", {"adc_noise": 4.0, "preamp_hz": 400.0}, "h_comb", "cmd"),
         ("L3 preamp, inversion avg 1", {"adc_noise": 4.0, "preamp_hz": 400.0, "preamp_inverse": True, "preamp_inv_avg": 1}, "h_comb", "cmd"),
         ("L3 preamp, inversion avg 7", {"adc_noise": 4.0, "preamp_hz": 400.0, "preamp_inverse": True, "preamp_inv_avg": 7}, "h_comb", "cmd"),
         ("L3 preamp, inversion avg 19", {"adc_noise": 4.0, "preamp_hz": 400.0, "preamp_inverse": True, "preamp_inv_avg": 19}, "h_comb", "cmd"),
         ("L7 full, actual positions, inversion", dict(FULL, preamp_inverse=True, preamp_inv_avg=7), "h_comb", "act")]
out = {}
for tk, blk, frames in [L.TECHS[0], L.TECHS[3]]:
    for name, over, ch, posmode in cases:
        phys = dict(L.IDEAL, **over)
        fo = M.simulate(truth, blk, L.SCAN_NM, phys, L.LOOP, frames=frames, verbose=False)
        t_ref = float(np.concatenate([f["t_s"].ravel() for f in fo]).mean())
        dr = phys["drift_nm_s"]; zr = phys["zdrift_A_s"]
        ref = M.truth_grid(truth, L.SCAN_NM, L.NPX, t_ref, dr)
        for f in fo: f[ch + "_c"] = f[ch] + zr * (f["t_s"] - t_ref)
        pos = ("xa_nm", "ya_nm") if posmode == "act" else ("x_nm", "y_nm")
        r = {}
        for meth in ("bin", "interp"):
            img, _ = M.grid(fo, L.SCAN_NM, L.NPX, channel=ch + "_c", drift=dr, t_ref=t_ref, pos=pos, method=meth)
            r[meth] = L.score(img, ref)["corr"]
        out[f"{tk}/{name}"] = r
        print(f"{tk:12s} {name:40s} binned {r['bin']:.4f}   interpolated {r['interp']:.4f}", flush=True)
json.dump(out, open(os.path.join(HERE, "ladder_fixes.json"), "w"), indent=1)
