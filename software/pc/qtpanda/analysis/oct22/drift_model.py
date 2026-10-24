"""Fit drift + Y+/Y- offset to the measured pair shifts, then test the model by
aligning frames with the PREDICTED shift only (no search) and comparing with a null.

Model per axis:  shift(a->b) = v * (t_b - t_a) + O * (h_b - h_a) / 2 + J * [gain step a != b]
  h = +1 for Y- (down) sweeps, -1 for Y+ (up) sweeps; O = Y-/Y+ image offset;
  J = extra jump at a gain change (KIGA changed between sweeps, scan restarted).
"""
import os, json, itertools
os.environ["QT_QPA_PLATFORM"] = "offscreen"
HERE = os.path.dirname(os.path.abspath(__file__))
MARK = "SW = [i for i in range(12, 32) if D.sweeps"
src = open(os.path.join(HERE, "patch_track.py"), encoding="utf-8").read().split(MARK)[0]
ns = {"__file__": os.path.join(HERE, "patch_track.py")}; exec(compile(src, "pt", "exec"), ns)
np, plt, D = ns["np"], ns["plt"], ns["D"]
ns["SIG"] = 1.0
RUNG = ns["RUNG"]
dm = json.load(open(os.path.join(HERE, "morph_report", "drift_metrics.json")))
t = lambda i: D.sweeps[i][2]["t_start"]
h = lambda i: 1 if D.sweeps[i][2]["dir"] == "down" else -1

SEG = [20, 21, 22, 23, 25, 26, 27, 28, 30, 31]          # the tracked segment
rows_y, rows_x, obs_y, obs_x, used = [], [], [], [], []
for p in dm["pairs"]:
    a, b = p["a"], p["b"]
    if a not in SEG or b not in SEG: continue
    e, s = p["err"], p["S"]
    if abs(e["dy"] - s["dy"]) > 8 or abs(e["dx"] - s["dx"]) > 8:   # use only cross-channel-agreeing pairs
        continue
    dy, dx = (e["dy"] + s["dy"]) / 2, (e["dx"] + s["dx"]) / 2
    feat = [t(b) - t(a), (h(b) - h(a)) / 2, 1.0 if RUNG[a] != RUNG[b] else 0.0]
    rows_y.append(feat); obs_y.append(dy); rows_x.append(feat); obs_x.append(dx); used.append((a, b, dy, dx))
Ay, Ax = np.array(rows_y), np.array(rows_x)
cy, *_ = np.linalg.lstsq(Ay, np.array(obs_y), rcond=None)
cx, *_ = np.linalg.lstsq(Ax, np.array(obs_x), rcond=None)
res_y = np.array(obs_y) - Ay @ cy; res_x = np.array(obs_x) - Ax @ cx
print(f"pairs used: {len(used)}")
print(f"Y: drift {cy[0]:.3f} px/s ({cy[0]*0.117*1000:.0f} pm/s), Y-/Y+ offset {cy[1]:+.1f} px ({cy[1]*0.117:.2f} nm), "
      f"gain-change jump {cy[2]:+.1f} px; residual rms {np.sqrt((res_y**2).mean()):.1f} px")
print(f"X: drift {cx[0]:.3f} px/s ({cx[0]*0.117*1000:.0f} pm/s), Y-/Y+ offset {cx[1]:+.1f} px, "
      f"gain-change jump {cx[2]:+.1f} px; residual rms {np.sqrt((res_x**2).mean()):.1f} px")
for (a, b, dy, dx), ry, rx in zip(used, res_y, res_x):
    print(f"  #{a}->#{b}: measured ({dy:+.1f},{dx:+.1f})  residual ({ry:+.1f},{rx:+.1f})")


def predict(a, b):
    f = np.array([t(b) - t(a), (h(b) - h(a)) / 2, 1.0 if RUNG[a] != RUNG[b] else 0.0])
    # gain-change jumps accumulate once per change crossed
    nchg = len({RUNG[k] for k in SEG if t(a) <= t(k) <= t(b)}) - 1
    f[2] = max(nchg, 0)
    return float(f @ cy), float(f @ cx)


IM = {"err": {i: ns["prep_err"](D, i) for i in SEG}, "S": {i: ns["prep_S"](D, i) for i in SEG}}


def shifted_corr(A, B, dy, dx):
    """corr of B against A where content at (y,x) in B sits at (y+dy, x+dx) in A."""
    iy, ix = int(round(dy)), int(round(dx)); H, W = A.shape
    ya, yb = max(0, iy), max(0, -iy); xa, xb = max(0, ix), max(0, -ix)
    hh, ww = H - abs(iy), W - abs(ix)
    if hh < 64 or ww < 64: return np.nan
    return ns["ns"]["corr"](A[ya:ya + hh, xa:xa + ww], B[yb:yb + hh, xb:xb + ww])


rng = np.random.default_rng(1)
pairs = list(itertools.combinations(SEG, 2))
table = []
for ch in ("err", "S"):
    for a, b in pairs:
        dy, dx = predict(a, b)
        c_model = shifted_corr(IM[ch][a], IM[ch][b], dy, dx)
        c_zero = shifted_corr(IM[ch][a], IM[ch][b], 0, 0)
        # null: same predicted shift, prior frame flipped; and 50 random shifts of the same size
        c_flip = shifted_corr(IM[ch][a][::-1, ::-1], IM[ch][b], dy, dx)
        rnd = []
        for _ in range(50):
            ang = rng.uniform(0, 2 * np.pi); mag = max(15, np.hypot(dy, dx))
            rnd.append(shifted_corr(IM[ch][a], IM[ch][b], mag * np.sin(ang), mag * np.cos(ang)))
        table.append(dict(ch=ch, a=a, b=b, dt=t(b) - t(a), pred_dy=dy, pred_dx=dx, model=c_model, zero=c_zero,
                          flip=c_flip, rnd_med=float(np.nanmedian(rnd)), rnd_p95=float(np.nanpercentile(rnd, 95))))
for ch in ("err", "S"):
    T = [r for r in table if r["ch"] == ch]
    beat = np.mean([r["model"] > r["rnd_p95"] for r in T])
    print(f"{ch}: predicted-shift corr median {np.median([r['model'] for r in T]):.2f} | zero-shift {np.median([r['zero'] for r in T]):.2f} "
          f"| random-shift p95 median {np.median([r['rnd_p95'] for r in T]):.2f} | flipped {np.median([r['flip'] for r in T]):.2f} "
          f"| pairs beating random-p95: {beat:.0%} of {len(T)}")

# figure: corr vs time separation, model vs zero vs null
fig, axes = plt.subplots(1, 2, figsize=(12, 3.8))
for ax, ch, ttl in ((axes[0], "err", "error channel"), (axes[1], "S", "Z folded S")):
    T = [r for r in table if r["ch"] == ch]
    ax.scatter([r["dt"] for r in T], [r["model"] for r in T], s=20, c="#1f77b4", label="aligned with PREDICTED shift (no search)")
    ax.scatter([r["dt"] for r in T], [r["zero"] for r in T], s=14, c="#ff7f0e", marker="x", label="no shift (fixed in frame)")
    ax.scatter([r["dt"] for r in T], [r["rnd_p95"] for r in T], s=10, c="#999", marker="_", label="random shift, 95th pct")
    ax.scatter([r["dt"] for r in T], [r["flip"] for r in T], s=10, c="#d62728", marker=".", label="flipped frame (null)")
    ax.axhline(0, color="k", lw=0.5); ax.set_xlabel("time between sweeps (s)"); ax.set_ylabel("correlation")
    ax.set_title(f"{ttl}: every pair in #20–#31", fontsize=9); ax.legend(fontsize=7)
plt.tight_layout(); fig.savefig(os.path.join(HERE, "morph_report", "figD4_model_test.png"), dpi=95); plt.close(fig)

# figure: drift-corrected stack, all frames #20-#31 mapped into #31's frame and averaged
ref = 31
def to_ref(ch, i):
    dy, dx = predict(i, ref)                # content at (y,x) in ref is at (y+dy, x+dx) in i
    A = IM[ch][i]; out = np.full_like(A, np.nan); iy, ix = int(round(dy)), int(round(dx)); H, W = A.shape
    ys, ye = max(0, -iy), min(H, H - iy); xs, xe = max(0, -ix), min(W, W - ix)
    out[ys:ye, xs:xe] = A[ys + iy:ye + iy, xs + ix:xe + ix]
    return out
fig, axes = plt.subplots(2, 3, figsize=(12, 8))
for r, ch in enumerate(("err", "S")):
    stack = np.array([to_ref(ch, i) for i in SEG])
    avg = np.nanmean(stack, 0); n_ = np.sum(~np.isnan(stack), 0)
    avg[n_ < 5] = np.nan
    ns_show = lambda ax, a, ttl: (ax.imshow(a, cmap="inferno", vmin=np.nanpercentile(a, 1), vmax=np.nanpercentile(a, 99)),
                                  ax.set_xticks([]), ax.set_yticks([]), ax.set_title(ttl, fontsize=8))
    ns_show(axes[r, 0], IM[ch][ref], f"{ch}: #31 alone")
    ns_show(axes[r, 1], avg, f"{ch}: #20–#31 drift-corrected average ({len(SEG)} sweeps)")
    raw_avg = np.mean([IM[ch][i] for i in SEG], 0)
    ns_show(axes[r, 2], raw_avg, f"{ch}: same sweeps averaged WITHOUT correction")
plt.tight_layout(pad=0.4); fig.savefig(os.path.join(HERE, "morph_report", "figD5_corrected_stack.png"), dpi=80); plt.close(fig)

json.dump(dict(model_y=dict(drift_px_s=cy[0], offset_px=cy[1], gain_jump_px=cy[2], rms=float(np.sqrt((res_y ** 2).mean()))),
               model_x=dict(drift_px_s=cx[0], offset_px=cx[1], gain_jump_px=cx[2], rms=float(np.sqrt((res_x ** 2).mean()))),
               used=used, table=table), open(os.path.join(HERE, "morph_report", "model_metrics.json"), "w"), indent=1, default=float)
print("done")
