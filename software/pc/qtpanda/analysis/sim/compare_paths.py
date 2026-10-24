"""Scan-path comparison on two truths at Oct-22-like settings (10 Hz lines -> 19 ticks/bin,
512 bins x 512 segments = 49.8 s per frame, KIGA 4.6, 500 pA), with X-Y stage drift (66 pm/s up
the frame) and Z drift (0.39 Å/s: Oct 22 same-sample 39 codes/s x placeholder calibration).
Single paths get one frame; pairs (raster x2, cross-hatch) get two frames: equal time per group.
Reconstruction: commanded-position map -> 256 x 256 grid over the 14 nm scan square, both raw and
drift-registered (known drift; an upper bound on what estimated registration can do).
Scores on the inscribed disc.  Outputs: compare_paths.json, compare_paths_imgs.npz."""
import os, sys, json, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import scan_sim as M, truths as T
import scan_paths as SP

SCAN_NM = 14.0
NPX = 256
SPEC = SP.Spec(spp=19, bins=512, segments=512, scan_size=262144)
PHYS = dict(M.PHYS, hyst_frac=0.05, zdrift_A_s=0.39, preamp_inverse=True, preamp_inv_avg=19)
# Reconstruction (after the verification ladder, scan-path-design 8.4): combined height
# (Z + current, preamp filter undone), interpolated to pixel centres, drifts registered.
#   registered = actual tip positions (lateral piezo calibrated)
#   xy_only    = commanded positions (piezo not calibrated)  [key name kept for the viewer]
#   raw        = the old method: Z alone, commanded positions, binned
LOOP = dict(M.LOOP, kiga=4.6, setpoint_pa=500.0)


def techniques():
    raster = SP.default_block(SPEC)
    cust = SP.raster_to_custom(SPEC)
    return [
        ("raster", "Raster (default, FW 5.6)", raster, (0,)),
        ("custom_raster", "Custom file = raster (validation)", SP.make_block("custom", {}, SPEC, custom=cust), (0,)),
        ("raster15", "Raster rotated 15°", SP.make_block("raster", {}, SPEC, rotation_deg=15.0), (0,)),
        ("raster45", "Raster rotated 45°", SP.make_block("raster", {}, SPEC, rotation_deg=45.0), (0,)),
        ("spiral_arch", "Archimedean spiral, out-in, ~constant tip speed", SP.make_block("spiral_arch", {"speed": "clv", "turns": 128}, SPEC), (0,)),
        ("spiral_fermat", "Fermat spiral, out-in", SP.make_block("spiral_fermat", {"turns": 128}, SPEC), (0,)),
        ("loops_centre", "Centre-return loops", SP.make_block("loops_centre", {"loops": 96}, SPEC), (0,)),
        ("spokes", "Spokes (star)", SP.make_block("spokes", {"spokes": 512}, SPEC), (0,)),
        ("rose", "Rose / figure-8, precessing", SP.make_block("rose", {"loops": 512}, SPEC), (0,)),
        ("raster_x2", "Raster, two frames averaged", raster, (0, 1)),
        ("crosshatch", "Cross-hatch pair (X-fast, then Y-fast)", SP.make_block("raster", {}, SPEC, sequence="crosshatch"), (0, 1)),
    ]


def main(truth_names=("sep24err", "synthetic")):
    results, imgs = {}, {}
    fs = 1e6 / PHYS["tick_us"]
    for tn in truth_names:
        truth = T.synthetic() if tn == "synthetic" else T.sep24_error()[0]
        for key, label, blk, frames in techniques():
            t0 = time.time()
            fo = M.simulate(truth, blk, SCAN_NM, PHYS, LOOP, frames=frames, verbose=False)
            t_all = np.concatenate([f["t_s"].ravel() for f in fo])
            t_ref = float(t_all.mean())
            ref = M.truth_grid(truth, SCAN_NM, NPX, t_ref, PHYS["drift_nm_s"])
            _, cnt = M.grid(fo, SCAN_NM, NPX, drift=PHYS["drift_nm_s"], t_ref=t_ref)
            # Z drift: remove each bin's ramp (the loop's same-sample rate, known in this test)
            for f in fo:
                f["z_dc"] = f["z_A"] + PHYS["zdrift_A_s"] * (f["t_s"] - t_ref)
                f["h_dc"] = f["h_comb"] + PHYS["zdrift_A_s"] * (f["t_s"] - t_ref)
            kw = dict(drift=PHYS["drift_nm_s"], t_ref=t_ref)
            regz, _ = M.grid(fo, SCAN_NM, NPX, channel="h_dc", pos=("xa_nm", "ya_nm"), method="hybrid", **kw)
            reg, _ = M.grid(fo, SCAN_NM, NPX, channel="h_dc", method="hybrid", **kw)
            raw, _ = M.grid(fo, SCAN_NM, NPX, channel="z_dc", **kw)
            sc = M.scores(regz, cnt, ref, blk, fo, SCAN_NM, fs)
            sc_raw = M.scores(raw, cnt, ref, blk, fo, SCAN_NM, fs)
            sc_regxy = M.scores(reg, cnt, ref, blk, fo, SCAN_NM, fs)
            results[f"{tn}/{key}"] = dict(label=label, truth=tn, frames=len(frames), seconds=len(frames) * SPEC.ticks_per_frame * 1e-5,
                                          registered=sc, xy_only=sc_regxy, raw=sc_raw, sim_s=round(time.time() - t0, 1))
            imgs[f"{tn}/{key}/recon"] = regz.astype(np.float32); imgs[f"{tn}/{key}/raw"] = raw.astype(np.float32)
            imgs[f"{tn}/{key}/cnt"] = cnt.astype(np.float32); imgs[f"{tn}/{key}/truth"] = ref.astype(np.float32)
            for k_, f in enumerate(fo):                       # every frame's commanded path (pairs: both)
                st_ = max(1, len(f["xc"]) // 20000)
                imgs[f"{tn}/{key}/path_x{k_}"] = f["xc"][::st_].astype(np.float32)
                imgs[f"{tn}/{key}/path_y{k_}"] = f["yc"][::st_].astype(np.float32)
                if len(fo) > 1:                                   # each frame rebuilt on its own
                    one, _ = M.grid([f], SCAN_NM, NPX, channel="h_dc", pos=("xa_nm", "ya_nm"), method="hybrid", **kw)
                    imgs[f"{tn}/{key}/recon_f{k_}"] = one.astype(np.float32)
            print(f"{tn:9s} {key:14s} corr {sc['corr']:.3f} (commanded pos {sc_regxy['corr']:.3f}, old Z-only {sc_raw['corr']:.3f})  rmse {sc['rmse_A']:.2f} Å  "
                  f"aniso {sc['resid_aniso']:.2f}  cov {sc['coverage']:.3f} hole {sc['largest_hole_nm']:.2f} nm  "
                  f"drive100-300 {sc['drive_100_300Hz']:.2e}  acc99.9 {sc['peak_acc_um_s2']:.0f} µm/s²  [{time.time() - t0:.0f} s]", flush=True)
            json.dump(results, open(os.path.join(HERE, "compare_paths.json"), "w"), indent=1)
    np.savez_compressed(os.path.join(HERE, "compare_paths_imgs.npz"), **imgs)
    # validation gate: custom file of the raster must give the identical image
    for tn in truth_names:
        a, b = imgs[f"{tn}/raster/recon"], imgs[f"{tn}/custom_raster/recon"]
        print(f"VALIDATION {tn}: custom-file raster identical to raster: {bool(np.array_equal(np.nan_to_num(a), np.nan_to_num(b)))}")
    import compare_extra; compare_extra.run(truth_names)


if __name__ == "__main__":
    main()
