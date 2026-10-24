"""Hysteresis sensitivity (HY1 recommendation): default raster, #1808 truth, full physics,
final reconstruction, hysteresis 1% / 5% / 12%: commanded vs actual positions."""
import os, sys, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import scan_sim as M, truths as T, ladder as L
truth = T.sep24_error()[0]
FULL = dict(adc_noise=4.0, preamp_hz=400.0, scan_offset=-55.0, zero_sub=True, lateral=True,
            drift_nm_s=(0.0, -0.066), zdrift_A_s=0.39, preamp_inverse=True, preamp_inv_avg=19)
out = {}
for hf in (0.01, 0.05, 0.12):
    phys = dict(L.IDEAL, **FULL, hyst_frac=hf)
    tk, blk, frames = L.TECHS[0]
    fo = M.simulate(truth, blk, L.SCAN_NM, phys, L.LOOP, frames=frames, verbose=False)
    t_ref = float(fo[0]["t_s"].mean())
    for f in fo: f["h_c"] = f["h_comb"] + 0.39 * (f["t_s"] - t_ref)
    ref = M.truth_grid(truth, L.SCAN_NM, L.NPX, t_ref, (0.0, -0.066))
    r = {}
    for nm, pos in (("commanded", ("x_nm", "y_nm")), ("actual", ("xa_nm", "ya_nm"))):
        img, _ = M.grid(fo, L.SCAN_NM, L.NPX, channel="h_c", drift=(0.0, -0.066), t_ref=t_ref, pos=pos, method="hybrid")
        r[nm] = L.score(img, ref)["corr"]
    out[str(hf)] = r
    print(f"hysteresis {hf*100:4.0f}%: commanded positions {r['commanded']:.3f}   actual positions {r['actual']:.3f}", flush=True)
json.dump(out, open(os.path.join(HERE, "hy_sensitivity.json"), "w"), indent=1)
