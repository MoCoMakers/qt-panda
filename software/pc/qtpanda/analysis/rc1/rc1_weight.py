"""RC1 follow-up: repeatability of h_w = w * tip(Z) - gap(current) against the weight w of the Z term.
w = 1 is the nominal combined height (g = 0.00063 Å/unit, kappa = 1.025/Å).  If the repeat peaks
far from w = 1, the assumed Z gain or kappa ratio is off (only the ratio g * 2 kappa matters)."""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
import rc1_combined as R

W = [0.0, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0]



def weighted_sets(D, ids, sp_counts, bias, skip_partial=True):
    out = {}
    for i in ids:
        if skip_partial and D.sweeps[i][2]["partial"]: continue
        zt, zr = R.fill_rows(D.image(i, "z_trace")[0]), R.fill_rows(D.image(i, "z_retrace")[0])
        et, er = R.fill_rows(D.image(i, "e_trace")[0]), R.fill_rows(D.image(i, "e_retrace")[0])
        lnVR = np.log(abs(bias) / R.RC)
        tip = (R.rowlev(-zt * R.G) + R.rowlev(-zr * R.G)) / 2
        gaps = []
        for e in (et, er):
            I = np.clip(R.counts_from_err(e, sp_counts), 1e-3, None) * R.PPC
            gaps.append(R.rowlev((lnVR - np.log(I)) / (2 * R.KAPPA)))
        out[i] = (tip, (gaps[0] + gaps[1]) / 2)
    return out


if __name__ == "__main__":
    res = {}
    D = R.sp.DayData("2026-Sep-24")
    S = weighted_sets(D, range(1802, 1813), 320, -0.0496)
    ids = sorted(S); ups = [i for i in ids if D.sweeps[i][2]["dir"] == "up"]
    rows = {}
    for w in W:
        cs = []
        for a, b in zip(ups, ups[1:]):
            ha, hb = w * S[a][0] - S[a][1], w * S[b][0] - S[b][1]
            dy, dx = R.shift_pc(-S[a][1], -S[b][1])
            A, B = R.overlap(ha, hb, dy, dx); cs.append(R.corr(A, B))
        rows[w] = float(np.median(cs))
    res["Sep 24 #1802-#1812"] = rows
    print("Sep 24 #1802-#1812 repeat vs w:", {k: round(v, 3) for k, v in rows.items()})
    sys.path.insert(0, "C:/Users/enact/AppData/Local/Temp/claude/C--Users-enact-Projects-qt-panda/817c62e4-40fb-43d6-a2a9-c40c37909d37/scratchpad")
    import v2_core as V
    S = weighted_sets(V.D, V.SEQ, 160, -0.0496, skip_partial=False)
    reg = {i: (V.register(S[i][0], i, True), V.register(S[i][1], i, True)) for i in V.SEQ}
    rows = {}
    for w in W:
        cs = []
        for a, b in zip(V.SEQ, V.SEQ[2:]):
            if V.S_(a)["dir"] != V.S_(b)["dir"] or V.RUNG[a] != V.RUNG[b]: continue
            cs.append(R.corr(w * reg[a][0] - reg[a][1], w * reg[b][0] - reg[b][1]))
        rows[w] = float(np.median(cs))
    res["Oct 22 #20-#31"] = rows
    print("Oct 22 #20-#31 repeat vs w:", {k: round(v, 3) for k, v in rows.items()})
    json.dump(res, open(os.path.join(HERE, "rc1_weight.json"), "w"), indent=1)
