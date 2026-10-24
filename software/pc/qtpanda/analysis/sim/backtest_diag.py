"""Back-test diagnosis: amplitudes of the lag part L and surface part S, and how much of L is
line-locked (the mean line profile repeated on every line).  Real in Z units; sim converted to
Z units with the same gain, so the two are directly comparable."""
import os, sys, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import scan_sim as M, truths as T, backtest_sep24 as B
import scan_paths as SP


def parts(zt, zr):
    a, b = T._rowlev(zt), T._rowlev(zr)
    L, S = (a - b) / 2, (a + b) / 2
    prof = L.mean(0)
    return dict(L_rms=float(L.std()), S_rms=float(S.std()), L_locked=float(prof.var() / L.var()),
                S_locked=float(S.mean(0).var() / S.var()), raw_span=float(np.ptp(np.percentile(zt, [2, 98]))))


def main():
    import sweep_player as sp
    D = sp.DayData("2026-Sep-24")
    real = [parts(T._fill(D.image(i, "z_trace")[0]), T._fill(D.image(i, "z_retrace")[0]))
            for i in range(1586, 1600) if not D.sweeps[i][2]["partial"]]
    med = {k: float(np.median([r[k] for r in real])) for k in real[0]}
    print("real Sep 24 median (Z units):", {k: round(v, 3) for k, v in med.items()})
    g = M.LS.z_gain_A_per_unit(M.PHYS["kappa"])
    out = {"real_median": med}
    for name, targs, extra in (("cal x1 + tilt", dict(scale=1.0, tilt=True), None),
                               ("cal x1, no tilt", dict(scale=1.0, tilt=False), None),
                               ("cal x1 + tilt, no noise", dict(scale=1.0, tilt=True), {"adc_noise": 0.0}),
                               ("cal x1 + tilt, KIGA x4", dict(scale=1.0, tilt=True), "kiga4")):
        truth, info = T.sep24(**targs)
        spec = SP.Spec(spp=3, bins=512, scan_size=262144)
        phys = dict(M.PHYS, drift_nm_s=(0.12 * info["scan_nm"] / 256, -0.23 * info["scan_nm"] / 256), **(extra if isinstance(extra, dict) else {}))
        loop = dict(M.LOOP, kiga=1.1444 * (4 if extra == "kiga4" else 1), setpoint_pa=1000.0)
        fo = M.simulate(truth, SP.default_block(spec), info["scan_nm"], phys, loop, verbose=False)[0]
        zunits = -fo["z_A"] / g
        up = zunits[:256]
        p = parts(up[:, :256], up[:, 256:][:, ::-1])
        out[name] = p
        print(f"sim {name:26s}", {k: round(v, 3) for k, v in p.items()})
    json.dump(out, open(os.path.join(HERE, "backtest_diag.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
