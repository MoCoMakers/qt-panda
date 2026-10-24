"""#22: ADC at the crater centre vs the bright rim spots.
(a) per pixel, from the stored error: err = setpointLog - logTable[|adc|]  ->  |adc| (exact inverse; the
    pixel value is an average over the samples in that pixel, so this is a log-mean of |adc|)
(b) raw signed ADC from the 200 Hz status record, each sample placed at its scan position."""
import os, re, json
HERE = os.path.dirname(os.path.abspath(__file__))
import v2_core as V
np = V.np
FW = "C:/Users/enact/Projects/qt-panda/software/firmware/arduinosrc/main/logTable.hpp"
LT = np.array([int(x) for x in re.findall(r"-?\d+", open(FW).read().split("{", 1)[1])][:32768], dtype=np.int64)
I = 22
fp, idx, s = V.D.sweeps[I]
print("sidecar setpoint fields:", {k: v for k, v in (idx.get("settings") or {}).items() if "set" in k.lower() or "pa" in k.lower()})
SP_COUNTS = 160                                        # 500 pA at 3.125 pA/count
spl = LT[SP_COUNTS]
inv = lambda err: np.searchsorted(LT, spl - err)       # |adc| whose log equals setpointLog - err

# ---- (a) per-pixel from stored error, registered into the sample frame (raw error, no levelling)
e = V.fill_rows(V.D.image(I, "e_trace")[0])
adc_img = inv(np.round(e).astype(np.int64)).astype(float)
R = V.register(adc_img, I, True)
YOFF = -V.Y0
m = json.load(open(os.path.join(HERE, "morph_report_v2", "v2_metrics.json")))
cy, cx = m["centre_sample_rc"]; cy += YOFF
ccy, ccx = V.CIRC[0] + YOFF, V.CIRC[1]
yy, xx = np.mgrid[0:R.shape[0], 0:R.shape[1]]
def ring(y0, x0, a, b): d = np.hypot(yy - y0, xx - x0); return (d >= a) & (d <= b) & np.isfinite(R)
cen = ring(cy, cx, 0, 8); ann = ring(cy, cx, 14, 26)
top = ann & (R >= np.nanpercentile(R[ann], 80))
frame = np.isfinite(R)
q = lambda v: np.percentile(v, [10, 50, 90])
pa = lambda c: c * 3.125
out = {}
for nm, mk in (("crater centre (r ≤ 0.9 nm)", cen), ("rim annulus 1.6–3.0 nm, all", ann), ("rim: brightest 20% (the yellow high spots)", top),
               ("whole #22 frame", frame), ("operator circle centre (r ≤ 0.9 nm)", ring(ccy, ccx, 0, 8))):
    v = R[mk]; out[nm] = q(v)
    print(f"(a) {nm:45s} |ADC| median {np.median(v):7.0f} counts ({pa(np.median(v)):8.0f} pA), 10–90%: {q(v)[0]:.0f}–{q(v)[2]:.0f}; "
          f"share ≤ 64 counts (no-current level) {np.mean(v <= 64) * 100:3.0f}%, share ≥ 32000 (clip) {np.mean(v >= 32000) * 100:3.0f}%  [{mk.sum()} px]")

# ---- (b) raw signed ADC from the status CSV, placed by time
csv = np.genfromtxt(os.path.join(V.D.folder, "image_stability_1792709026870_s1792709026869.csv"), delimiter=",", skip_header=1)
ct = 1792709026.870 + csv[:, 0]; adc = csv[:, 2]
recs = V.D.records(fp)[s["first_record"]:s["last_record"] + 1]
lt = np.array([r[0] for r in recs]); ln = np.array([r[1] for r in recs])
per = np.median(np.diff(lt))
sel = (ct >= lt[0] - per) & (ct <= lt[-1])
Ys, Xs, A = [], [], []
H = V.H
for t, a in zip(ct[sel], adc[sel]):
    k = np.searchsorted(lt, t)                       # record time = end of that line (trace + retrace)
    if k >= len(lt): continue
    f = 1 - (lt[k] - t) / per                        # fraction through the line
    if not (0 <= f < 0.5): continue                   # trace half only (matches e_trace)
    raw = ln[k] % (2 * H); row = raw if raw < H else 2 * H - 1 - raw
    col = f / 0.5 * 255
    dy, dx = V.dy_dx(I, np.array([t]))
    Ys.append(row - dy[0] + YOFF); Xs.append(col - dx); A.append(a)
Ys, Xs, A = map(np.array, (Ys, Xs, A))
d = np.hypot(Ys - cy, Xs - cx)
# rim bright spots: samples that fall on the top-20% rim pixels
ti = (np.clip(np.round(Ys).astype(int), 0, R.shape[0] - 1), np.clip(np.round(Xs).astype(int), 0, R.shape[1] - 1))
on_top = top[ti]
for nm, mk in (("crater centre (r ≤ 0.9 nm)", d <= 8), ("crater centre, wider (r ≤ 1.4 nm)", d <= 12),
               ("rim annulus 1.6–3.0 nm", (d >= 14) & (d <= 26)), ("rim: on the brightest-20% pixels", on_top), ("whole #22 trace", np.ones_like(d, bool))):
    v = A[mk]
    if len(v) == 0: print(f"(b) {nm}: no samples"); continue
    print(f"(b) {nm:45s} n={len(v):4d}  signed ADC median {np.median(v):7.0f}, 10–90%: {np.percentile(v, 10):.0f}–{np.percentile(v, 90):.0f}; "
          f"≤ −16 (no current, phantom) {np.mean(v <= -16) * 100:3.0f}%, > 64 (tunnelling) {np.mean(v > 64) * 100:3.0f}%, ≥ 32000 {np.mean(v >= 32000) * 100:3.0f}%")
