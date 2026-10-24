import v2_core as V
np = V.np
P = []; Pt = []
for i in V.SEQ:
    zt = V.fill_rows(V.D.image(i, "z_trace")[0]); zr = V.fill_rows(V.D.image(i, "z_retrace")[0])
    S = (V.rowlev(zt) + V.rowlev(zr)) / 2
    S = S - np.polyval(np.polyfit(np.arange(256), S.mean(1), 0), 0)
    f = np.fft.rfft((S - S.mean(0)) * np.hanning(256)[:, None], axis=0); P.append((np.abs(f) ** 2).mean(1))
    # trace minus retrace (lag part) for comparison
    L = (V.rowlev(zt) - V.rowlev(zr)) / 2
    f2 = np.fft.rfft((L - L.mean(0)) * np.hanning(256)[:, None], axis=0); Pt.append((np.abs(f2) ** 2).mean(1))
P = np.mean(P, 0); Pt = np.mean(Pt, 0)
def rep(P, nm):
    base = np.array([np.median(P[max(3, j - 6):j + 7]) for j in range(len(P))])
    ratio = P / base; k = [j for j in np.argsort(ratio[5:])[::-1][:4] + 5]
    print(nm, "local peaks (cycles/frame: x above neighbourhood):", [(int(j), round(float(ratio[j]), 1)) for j in k],
          "| power share in 64–128 cycles/frame (row-to-row):", f"{P[64:].sum() / P[3:].sum() * 100:.0f}%")
rep(P, "folded S (surface part)  ")
rep(Pt, "trace−retrace (lag part) ")
