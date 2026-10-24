"""Back-test: does the simulator reproduce what the real raster recorded on the good-tip day?

Real: Sep 24 #1586-#1599 (24.79 nm, 512 px/line, 3 ticks/pixel = 15.4 ms lines, KIGA 1.144,
1000 pA, -49.6 mV, ISR 10 us), image statistics per full sweep.
Sim: raster v1 over the Sep 24 truth with the same settings and Sep 24 drift, same statistics.
Statistics (all on Z, line-levelled as the analysis tools do):
  lag share      var(L) / (var(L) + var(S)), L = (trace - retrace)/2, S = (trace + retrace)/2
  S anisotropy   row-to-row / column-to-column gradient energy of S
  jitter share   share of S power along Y at 2-4-row periods (64-128 cycles per 256 rows)
  trace-retrace  correlation between line-levelled trace and retrace
"""
import os, sys, json, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import scan_sim as M, truths as T
import scan_paths as SP


def stats(zt, zr):
    a, b = T._rowlev(zt), T._rowlev(zr)
    L, S = (a - b) / 2, (a + b) / 2
    gy, gx = np.diff(S, axis=0), np.diff(S, axis=1)
    f = np.fft.rfft((S - S.mean(0)) * np.hanning(S.shape[0])[:, None], axis=0)
    P = (np.abs(f) ** 2).mean(1); n = S.shape[0]
    return dict(lag_share=float(L.var() / (L.var() + S.var())), s_aniso=float(np.mean(gy ** 2) / np.mean(gx ** 2)),
                jitter_share=float(P[n // 4:].sum() / P[3:].sum()), trace_retrace_corr=float(np.corrcoef(a.ravel(), b.ravel())[0, 1]))


def real_stats(ids):
    import sweep_player as sp
    D = sp.DayData("2026-Sep-24")
    out = {}
    for i in ids:
        if D.sweeps[i][2]["partial"]: continue
        out[i] = stats(T._fill(D.image(i, "z_trace")[0]), T._fill(D.image(i, "z_retrace")[0]))
    return out


def sim_stats(truth, scan_nm, kiga=1.1444, setpoint=1000.0, spp=3, rms=1.0, extra=None):
    spec = SP.Spec(spp=spp, bins=512, scan_size=262144)
    blk = SP.default_block(spec)
    phys = dict(M.PHYS, drift_nm_s=(0.12 * scan_nm / 256, -0.23 * scan_nm / 256), **(extra or {}))
    loop = dict(M.LOOP, kiga=kiga, setpoint_pa=setpoint)
    fo = M.simulate(truth, blk, scan_nm, phys, loop, frames=(0,), verbose=False)[0]
    z = fo["z_A"]                                       # (512 segments, 512 bins), height = -Z
    up, down = z[:256], z[256:][::-1]                   # segment = true line index (no line-number slip)
    out = {}
    for nm, img in (("up", up), ("down", down)):
        out[nm] = stats(-img[:, :256], -img[:, 256:][:, ::-1])      # back to Z sign, trace / retrace
    return out


if __name__ == "__main__":
    ids = list(range(1586, 1600))
    t0 = time.time()
    R = real_stats(ids)
    keys = ["lag_share", "s_aniso", "jitter_share", "trace_retrace_corr"]
    summ = {"real": {k: [float(np.min([r[k] for r in R.values()])), float(np.median([r[k] for r in R.values()])),
                         float(np.max([r[k] for r in R.values()]))] for k in keys}}
    res = {}
    runs = [("rms1.0, no tilt", dict(rms_A=1.0), None),
            ("cal x1 + tilt", dict(scale=1.0, tilt=True), None),
            ("cal x0.3 + tilt", dict(scale=0.3, tilt=True), None),
            ("cal x1 + tilt, no hysteresis", dict(scale=1.0, tilt=True), {"hyst_nm": 0.0}),
            ("cal x1 + tilt, hysteresis 2 nm", dict(scale=1.0, tilt=True), {"hyst_nm": 2.0}),
            ("cal x1 + tilt, PI 5%", dict(scale=1.0, tilt=True), {"hyst_frac": 0.05}),
            ("cal x1 + tilt, PI 10%", dict(scale=1.0, tilt=True), {"hyst_frac": 0.10}),
            ("cal x1 + tilt, PI 15%", dict(scale=1.0, tilt=True), {"hyst_frac": 0.15}),
            ("cal x0.3 + tilt, PI 10%", dict(scale=0.3, tilt=True), {"hyst_frac": 0.10}),
            ("cal x3 + tilt, PI 10%", dict(scale=3.0, tilt=True), {"hyst_frac": 0.10})]
    for name, targs, extra in runs:
        truth, info = T.sep24(**targs)
        s = sim_stats(truth, info["scan_nm"], extra=extra)
        res[name] = s
        print(f"sim {name:30s}", {k: [round(s['up'][k], 3), round(s['down'][k], 3)] for k in keys}, flush=True)
    print("real Sep 24 (min, median, max):", {k: [round(v, 3) for v in summ['real'][k]] for k in keys})
    json.dump(dict(real=R, real_summary=summ, sim=res), open(os.path.join(HERE, "backtest_sep24.json"), "w"), indent=1, default=float)
    print(f"done in {time.time() - t0:.0f} s")
