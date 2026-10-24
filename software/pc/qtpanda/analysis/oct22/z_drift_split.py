"""Split the loop's Z ramp on Oct 22 into
   (a) Z change at the SAME sample points (drift-registered)  -> vertical drift of tip vs sample
                                                                 (Z thermal + stage Z + creep + loop balance)
   (b) frame-mean Z change (what the loop did over the moving window)
   (b) - (a) = geometric part: the window sliding over a tilted / curved sample (tilt x lateral drift).
Raw folded Z (no line levelling), consecutive sweeps within one gain only (gain changes shift loop balance)."""
import v2_core as V
np = V.np
SEQ = V.SEQ
Zf = {}
for i in SEQ:
    zt = V.fill_rows(V.D.image(i, "z_trace")[0]); zr = V.fill_rows(V.D.image(i, "z_retrace")[0])
    Zf[i] = (zt + zr) / 2
REGZ = {i: V.register(Zf[i], i, True) for i in SEQ}
tm = {i: float(np.mean(V.row_times(i))) for i in SEQ}
rows = []
for a, b in zip(SEQ, SEQ[1:]):
    if V.RUNG[a] != V.RUNG[b]: continue
    dt = tm[b] - tm[a]
    m = np.isfinite(REGZ[a]) & np.isfinite(REGZ[b])
    same = float(np.mean(REGZ[b][m] - REGZ[a][m])) / dt
    frame = float(np.mean(Zf[b]) - np.mean(Zf[a])) / dt
    rows.append((a, b, V.RUNG[a], dt, m.mean(), frame, same, frame - same))
print("pair      KIGA   dt(s) overlap  frame-mean dZ/dt  same-sample dZ/dt  geometric (frame - same)   [Z units/s]")
for a, b, k, dt, ov, fr, sa, ge in rows:
    print(f"#{a}->#{b:<3} {k:>4} {dt:6.1f}  {ov*100:4.0f}%   {fr:+8.1f}          {sa:+8.1f}           {ge:+8.1f}")
fr = np.array([r[5] for r in rows]); sa = np.array([r[6] for r in rows]); ge = np.array([r[7] for r in rows])
print(f"median: frame {np.median(fr):+.1f}, same-sample {np.median(sa):+.1f}, geometric {np.median(ge):+.1f} Z units/s")
# tilt of the sample along the drift direction, from the registered average (sample frame)
st = np.stack([REGZ[i] for i in SEQ]); n = np.isfinite(st).sum(0)
with np.errstate(invalid="ignore"): avg = np.nansum(st, 0) / n
ok = n >= 3
yy, xx = np.mgrid[0:avg.shape[0], 0:avg.shape[1]]
A = np.c_[yy[ok], xx[ok], np.ones(ok.sum())]
c, *_ = np.linalg.lstsq(A, avg[ok], rcond=None)
vy = V.CY[0]
print(f"sample-frame plane: {c[0]:+.2f} Z units per row (down the frame), {c[1]:+.2f} per column")
print(f"window moves {vy:.2f} rows/s further down the sample (content moves up the frame), so tilt alone predicts {c[0]*vy:+.1f} Z units/s")
# what are the Z units? frames carry z_pos (20-bit position units); 16 per Z-DAC code
print("Z units: firmware z_pos (20-bit); 16 units = 1 Z-DAC code")
