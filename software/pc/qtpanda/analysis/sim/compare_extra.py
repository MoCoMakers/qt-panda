"""Speed-matched controls added to compare_paths results (same settings): at equal time the raster
moves the tip ~290 nm/s (trace + retrace), the 128-turn spiral ~110 nm/s; a 320-turn spiral and
96 -> 240-loop centre-return run near raster speed, separating 'slower' from 'better shape'."""
import os, sys, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import compare_paths as C, scan_sim as M, truths as T
import scan_paths as SP

EXTRA = [("spiral_arch_fast", "Archimedean spiral at raster speed (320 turns)", SP.make_block("spiral_arch", {"speed": "clv", "turns": 320}, C.SPEC), (0,)),
         ("loops_centre_fast", "Centre-return loops at ~raster speed (240 loops)", SP.make_block("loops_centre", {"loops": 240}, C.SPEC), (0,))]

def run(truth_names=("sep24err", "synthetic")):
    R = json.load(open(os.path.join(HERE, "compare_paths.json")))
    I = dict(np.load(os.path.join(HERE, "compare_paths_imgs.npz")))
    fs = 1e6 / C.PHYS["tick_us"]
    for tn in truth_names:
        truth = T.synthetic() if tn == "synthetic" else T.sep24_error()[0]
        for key, label, blk, frames in EXTRA:
            fo = M.simulate(truth, blk, C.SCAN_NM, C.PHYS, C.LOOP, frames=frames, verbose=False)
            t_ref = float(np.concatenate([f["t_s"].ravel() for f in fo]).mean())
            ref = M.truth_grid(truth, C.SCAN_NM, C.NPX, t_ref, C.PHYS["drift_nm_s"])
            for f in fo:
                f["z_dc"] = f["z_A"] + C.PHYS["zdrift_A_s"] * (f["t_s"] - t_ref)
                f["h_dc"] = f["h_comb"] + C.PHYS["zdrift_A_s"] * (f["t_s"] - t_ref)
            kw = dict(drift=C.PHYS["drift_nm_s"], t_ref=t_ref)
            _, cnt = M.grid(fo, C.SCAN_NM, C.NPX, **kw)
            regz, _ = M.grid(fo, C.SCAN_NM, C.NPX, channel="h_dc", pos=("xa_nm", "ya_nm"), method="hybrid", **kw)
            reg, _ = M.grid(fo, C.SCAN_NM, C.NPX, channel="h_dc", method="hybrid", **kw)
            raw, _ = M.grid(fo, C.SCAN_NM, C.NPX, channel="z_dc", **kw)
            sc = M.scores(regz, cnt, ref, blk, fo, C.SCAN_NM, fs)
            R[f"{tn}/{key}"] = dict(label=label, truth=tn, frames=1, seconds=C.SPEC.ticks_per_frame * 1e-5, registered=sc,
                                    xy_only=M.scores(reg, cnt, ref, blk, fo, C.SCAN_NM, fs),
                                    raw=M.scores(raw, cnt, ref, blk, fo, C.SCAN_NM, fs))
            I[f"{tn}/{key}/recon"] = regz.astype(np.float32); I[f"{tn}/{key}/raw"] = raw.astype(np.float32)
            I[f"{tn}/{key}/cnt"] = cnt.astype(np.float32); I[f"{tn}/{key}/truth"] = ref.astype(np.float32)
            I[f"{tn}/{key}/path_x0"] = fo[0]["xc"][::max(1, len(fo[0]["xc"]) // 20000)].astype(np.float32)
            I[f"{tn}/{key}/path_y0"] = fo[0]["yc"][::max(1, len(fo[0]["yc"]) // 20000)].astype(np.float32)
            print(f"{tn:9s} {key:18s} corr {sc['corr']:.3f} rmse {sc['rmse_A']:.2f} aniso {sc['resid_aniso']:.2f} cov {sc['coverage']:.3f} "
                  f"speed p5-p95 {sc['speed_nm_s_p5_p95'][0]:.0f}-{sc['speed_nm_s_p5_p95'][1]:.0f} nm/s", flush=True)
    for tn in truth_names:
        for k in ("raster", "spiral_arch", "loops_centre"):
            sp_ = R[f"{tn}/{k}"]["registered"]["speed_nm_s_p5_p95"]
            print(f"   reference {tn} {k}: speed p5-p95 {sp_[0]:.0f}-{sp_[1]:.0f} nm/s, corr {R[f'{tn}/{k}']['registered']['corr']:.3f}")
    json.dump(R, open(os.path.join(HERE, "compare_paths.json"), "w"), indent=1)
    np.savez_compressed(os.path.join(HERE, "compare_paths_imgs.npz"), **I)


if __name__ == "__main__":
    run()
