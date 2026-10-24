"""Does the scan-time ADC offset (OI-3) depend on scan direction?  Capacitive pickup of the X drive
(C dV/dt) flips sign between trace and retrace; a ground shift would not.
Each 200 Hz status sample is placed in its line by the line records' timing: first half = trace,
second half = retrace.  Only no-current samples (raw ADC < 0) are used.  Placement uses PC times,
so a few samples near the turnarounds are misassigned; samples within 10% of a turnaround are
dropped."""
import os, sys, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
QT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(QT, "replay"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import sweep_player as sp


def run(day, csv_name, t0_csv, sweeps):
    D = sp.DayData(day)
    csv = np.genfromtxt(os.path.join(D.folder, csv_name), delimiter=",", skip_header=1)
    ct = t0_csv + csv[:, 0]; adc = csv[:, 2]
    tr, rt = [], []
    for i in sweeps:
        fp, idx, s = D.sweeps[i]
        rec = D.records(fp)[s["first_record"]:s["last_record"] + 1]
        lt = np.array([r[0] for r in rec])
        per = (lt[-1] - lt[0]) / max(1, len(lt) - 1)            # mean line period (PC receive times jitter)
        m = (ct > lt[0]) & (ct < lt[-1])
        for t, a in zip(ct[m], adc[m]):
            k = np.searchsorted(lt, t)
            f = 1 - (lt[k] - t) / per
            if not (0 <= f < 1) or a >= 0: continue
            if 0.05 < f < 0.45: tr.append(a)
            elif 0.55 < f < 0.95: rt.append(a)
    tr, rt = np.array(tr), np.array(rt)
    return dict(n_trace=len(tr), n_retrace=len(rt), trace_median=float(np.median(tr)), retrace_median=float(np.median(rt)),
                trace_mean=float(tr.mean()), retrace_mean=float(rt.mean()),
                diff_mean=float(tr.mean() - rt.mean()),
                diff_se=float(np.sqrt(tr.var() / len(tr) + rt.var() / len(rt))))


if __name__ == "__main__":
    out = {}
    out["Oct 22 #20-#31"] = run("2026-Oct-22", "image_stability_1792709026870_s1792709026869.csv", 1792709026.870,
                                [20, 21, 22, 23, 25, 26, 27, 28, 30, 31])
    for k, v in out.items():
        print(k, {a: (round(b, 2) if isinstance(b, float) else b) for a, b in v.items()})
    json.dump(out, open(os.path.join(HERE, "phantom_direction.json"), "w"), indent=1)
