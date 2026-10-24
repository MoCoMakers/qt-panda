"""Verification ladder: add one physical effect at a time and measure how well the truth is
recreated, so every lost percentage point has a named cause.

L0  geometry only: the true height at each bin's commanded position -> grid.  Tests the path
    generator, the reconstruction map and the gridding.  Must be >= 0.99.
L1  + firmware feedback loop, ideal electronics (no noise, no preamp lag, no offset, no zero
    substitution).  Rebuilt from Z alone, and from Z + current (combined: h = tip - gap(I)).
L2  + ADC noise (4 counts rms)
L3  + preamp bandwidth (400 Hz)
L4  + phantom offset (-55 counts) and zero substitution, offset KNOWN to the reconstruction
L4u   same, offset NOT known (reconstruction assumes 0)
L5  + lateral piezo (5% PI hysteresis, 158.7 Hz resonance, 3 kHz amp): commanded positions,
L5a   and actual positions (lateral model known)
L6  + X-Y stage drift 66 pm/s, registered with the known drift (actual positions)
L7  + Z drift 0.39 Å/s, removed with the known rate (= everything, as in the comparison run)
Score: Pearson correlation on the inscribed disc after plane removal, and RMS error / truth rms
after a linear fit.  99% recreation = corr >= 0.99.
"""
import os, sys, json, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import scan_sim as M, truths as T
import scan_paths as SP

SCAN_NM, NPX = 14.0, 256
SPEC = SP.Spec(spp=19, bins=512, segments=512, scan_size=262144)
LOOP = dict(M.LOOP, kiga=4.6, setpoint_pa=500.0)
IDEAL = dict(M.PHYS, adc_noise=0.0, preamp_hz=None, scan_offset=0.0, zero_sub=False, lateral=False,
             drift_nm_s=(0.0, 0.0), zdrift_A_s=0.0, hyst_frac=0.05)

LAYERS = [
    ("L1", "loop, ideal electronics", {}, "cmd"),
    ("L2", "+ ADC noise", {"adc_noise": 4.0}, "cmd"),
    ("L3", "+ preamp 400 Hz", {"adc_noise": 4.0, "preamp_hz": 400.0}, "cmd"),
    ("L4", "+ phantom offset, zero subst. (offset known)", {"adc_noise": 4.0, "preamp_hz": 400.0, "scan_offset": -55.0, "zero_sub": True}, "cmd"),
    ("L4u", "  same, offset unknown", {"adc_noise": 4.0, "preamp_hz": 400.0, "scan_offset": -55.0, "zero_sub": True, "offset_known": 0.0}, "cmd"),
    ("L5", "+ lateral piezo, commanded positions", {"adc_noise": 4.0, "preamp_hz": 400.0, "scan_offset": -55.0, "zero_sub": True, "lateral": True}, "cmd"),
    ("L5a", "  same, actual positions (model known)", {"adc_noise": 4.0, "preamp_hz": 400.0, "scan_offset": -55.0, "zero_sub": True, "lateral": True}, "act"),
    ("L6", "+ X-Y stage drift (registered)", {"adc_noise": 4.0, "preamp_hz": 400.0, "scan_offset": -55.0, "zero_sub": True, "lateral": True, "drift_nm_s": (0.0, -0.066)}, "act"),
    ("L7", "+ Z drift (removed) = full physics", {"adc_noise": 4.0, "preamp_hz": 400.0, "scan_offset": -55.0, "zero_sub": True, "lateral": True, "drift_nm_s": (0.0, -0.066), "zdrift_A_s": 0.39}, "act"),
]
TECHS = [("raster", SP.default_block(SPEC), (0,)),
         ("raster15", SP.make_block("raster", {}, SPEC, rotation_deg=15.0), (0,)),
         ("crosshatch", SP.make_block("raster", {}, SPEC, sequence="crosshatch"), (0, 1)),
         ("spiral_fast", SP.make_block("spiral_arch", {"speed": "clv", "turns": 320}, SPEC), (0,))]


def score(img, ref):
    npx = img.shape[0]; yy, xx = np.mgrid[0:npx, 0:npx]
    disc = (yy - (npx - 1) / 2) ** 2 + (xx - (npx - 1) / 2) ** 2 <= (0.48 * npx) ** 2
    m = disc & np.isfinite(img) & np.isfinite(ref)
    a, b = M._plane(np.nan_to_num(img), m), M._plane(np.nan_to_num(ref), m)
    c = float(np.corrcoef(a[m], b[m])[0, 1])
    k = np.polyfit(a[m], b[m], 1); r = b[m] - np.polyval(k, a[m])
    return dict(corr=c, nrmse=float(r.std() / b[m].std()))


def run(truth_name):
    truth = T.sep24_error()[0] if truth_name == "sep24err" else T.synthetic()
    res = {}
    for tk, blk, frames in TECHS:
        # L0: geometry only
        fo = M.simulate(truth, blk, SCAN_NM, IDEAL, LOOP, frames=frames, verbose=False)
        t_ref = float(np.concatenate([f["t_s"].ravel() for f in fo]).mean())
        ref = M.truth_grid(truth, SCAN_NM, NPX, t_ref, (0.0, 0.0))
        g0, _ = M.grid(fo, SCAN_NM, NPX, channel="h_true")
        res[f"{tk}/L0"] = dict(geometry=score(g0, ref))
        print(f"{truth_name:9s} {tk:12s} L0  geometry only                          corr {res[f'{tk}/L0']['geometry']['corr']:.4f}", flush=True)
        for lid, label, over, posmode in LAYERS:
            phys = dict(IDEAL, **over)
            fo = M.simulate(truth, blk, SCAN_NM, phys, LOOP, frames=frames, verbose=False)
            t_ref = float(np.concatenate([f["t_s"].ravel() for f in fo]).mean())
            dr = phys["drift_nm_s"]
            ref = M.truth_grid(truth, SCAN_NM, NPX, t_ref, dr)
            pos = ("xa_nm", "ya_nm") if posmode == "act" else ("x_nm", "y_nm")
            zr = phys["zdrift_A_s"]
            for f in fo:
                for ch in ("z_A", "h_comb", "h_true"):
                    f[ch + "_c"] = f[ch] + zr * (f["t_s"] - t_ref)
            kw = dict(drift=dr, t_ref=t_ref, pos=pos)
            out = {}
            for ch, name in (("z_A_c", "z_only"), ("h_comb_c", "combined"), ("h_true_c", "true_height_at_bins")):
                img, cnt = M.grid(fo, SCAN_NM, NPX, channel=ch, **kw)
                out[name] = score(img, ref)
            out["valid_share"] = float(np.mean(np.concatenate([f["h_valid"].ravel() for f in fo])))
            res[f"{tk}/{lid}"] = dict(label=label, **out)
            print(f"{truth_name:9s} {tk:12s} {lid:4s}{label:42s} Z-only {out['z_only']['corr']:.4f}  combined {out['combined']['corr']:.4f}  "
                  f"(true-at-bins {out['true_height_at_bins']['corr']:.4f}, current usable {out['valid_share']*100:.0f}%)", flush=True)
    return res


if __name__ == "__main__":
    t0 = time.time()
    allres = {tn: run(tn) for tn in ("sep24err", "synthetic")}
    json.dump(allres, open(os.path.join(HERE, "ladder.json"), "w"), indent=1)
    print(f"done in {time.time() - t0:.0f} s")
