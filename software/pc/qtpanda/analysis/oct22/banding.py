"""Row banding in Oct 22 Z: is it a periodic 'overlay frequency' or broadband line-to-line noise?"""
import v2_core as V
np = V.np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
P = []; aniso = []; lp = []
for i in V.SEQ:
    zt = V.fill_rows(V.D.image(i, "z_trace")[0]); zr = V.fill_rows(V.D.image(i, "z_retrace")[0])
    t = V.row_times(i); lp.append(np.median(np.abs(np.diff(t))))
    S = (V.rowlev(zt) + V.rowlev(zr)) / 2
    raw_mean = (zt.mean(1) + zr.mean(1)) / 2                       # each line's offset (what levelling removes)
    x = raw_mean - np.polyval(np.polyfit(np.arange(256), raw_mean, 2), np.arange(256))
    f = np.fft.rfft(x * np.hanning(256)); P.append(np.abs(f) ** 2)
    gy = np.diff(S, axis=0); gx = np.diff(S, axis=1)
    aniso.append(np.mean(gy ** 2) / np.mean(gx ** 2))
P = np.mean(P, 0); lp = float(np.median(lp)); fr = np.fft.rfftfreq(256, d=lp)     # Hz along slow axis (cycles per s)
k = np.argsort(P[3:])[::-1][:5] + 3
print(f"line period {lp*1000:.1f} ms; row-to-row / column-to-column gradient energy in folded S: {np.min(aniso):.0f}–{np.max(aniso):.0f}")
print("top row-offset spectral peaks (cycles per frame, Hz in time, power vs median):",
      [(int(j), round(fr[j], 2), round(P[j] / np.median(P[3:]), 1)) for j in k])
lo = P[3:20].sum() / P[3:].sum()
print(f"share of row-offset power below 20 cycles/frame (slower than ~{fr[20]:.1f} Hz): {lo*100:.0f}%")
fig, ax = plt.subplots(figsize=(7, 3)); ax.semilogy(np.arange(len(P)), P); ax.set_xlabel("cycles per frame (row direction)"); ax.set_ylabel("row-offset power")
plt.tight_layout(); fig.savefig("banding_spectrum.png", dpi=80)
