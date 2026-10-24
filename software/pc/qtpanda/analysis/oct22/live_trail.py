"""Simulated live drift trail: register 64-row bands of each sweep (as they would arrive
live) against the previous sweep of the same direction; time each update; render a
'frame drift' widget with a decaying tail as an animated GIF."""
import os, sys, time, json
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np
import fiducial_drift as fd
import sweep_player as sp
D = sp.DayData("2026-Oct-22"); PX = 30.0 / 256
SEQ = [20, 21, 22, 23, 25, 26, 27, 28, 30, 31]
BAND, BW, BSTEP, TOL, WIN = 96, 96, 32, 5, 22
E, S, T0, T1, DIR = {}, {}, {}, {}, {}
for i in SEQ:
    E[i] = fd.prep(fd.rowlev(fd.fill_rows(D.image(i, "e_trace")[0])))
    S[i] = fd.prep((fd.rowlev(fd.fill_rows(D.image(i, "z_trace")[0])) + fd.rowlev(fd.fill_rows(D.image(i, "z_retrace")[0]))) / 2)
    s = D.sweeps[i][2]; T0[i], T1[i], DIR[i] = s["t_start"], s["t_end"], s["dir"]


def band_shift(A, B, r0, pred=None):
    """blocks from rows r0..r0+BAND of B (new) searched in A (old): new - old displacement.
    With a prediction, search only within +-WIN px of it (tracking mode)."""
    out = []
    for c0 in range(0, 256 - BW + 1, BSTEP):
        tpl = B[r0:r0 + BAND, c0:c0 + BW]
        if tpl.std() < 0.35 * B.std(): continue
        if pred is None:
            y0, x0, sub = 0, 0, A
        else:
            cy, cx = r0 - pred[0], c0 - pred[1]                  # where the block should sit in A
            y0, x0 = int(max(0, cy - WIN)), int(max(0, cx - WIN))
            y1, x1 = int(min(256, cy + BAND + WIN)), int(min(256, cx + BW + WIN))
            if y1 - y0 < BAND + 4 or x1 - x0 < BW + 4: continue
            sub = A[y0:y1, x0:x1]
        m = fd.ncc_map(sub, tpl); py, px = np.unravel_index(np.argmax(m), m.shape)
        out.append((r0 - (py + y0), c0 - (px + x0), float(m[py, px])))
    if len(out) < 3: return None
    best = []
    for q in out:
        sup = [w for w in out if abs(w[0] - q[0]) <= TOL and abs(w[1] - q[1]) <= TOL]
        if len(sup) > len(best): best = sup
    return (float(np.median([w[0] for w in best])), float(np.median([w[1] for w in best])), len(best), len(out))


updates, timings = [], []
vel = None                                                       # px/s, new - old (rows, cols)
for b in SEQ:
    prev = [a for a in SEQ if a < b and DIR[a] == DIR[b]]
    if not prev: continue
    a = prev[-1]; dt_ref = T0[b] - T0[a]
    for r0 in (0, 80, 160):
        t_ready = T0[b] + (r0 + BAND) / 256.0 * (T1[b] - T0[b])
        pred = None if vel is None else (vel[0] * dt_ref, vel[1] * dt_ref)
        t0 = time.perf_counter()
        re_, rs_ = band_shift(E[a], E[b], r0, pred), band_shift(S[a], S[b], r0, pred)
        timings.append(time.perf_counter() - t0)
        both = re_ and rs_ and re_[2] >= 3 and rs_[2] >= 3 and abs(re_[0] - rs_[0]) <= 8 and abs(re_[1] - rs_[1]) <= 8
        strong = [r for r in (re_, rs_) if r and r[2] >= 4 and r[2] >= 0.6 * r[3]]
        contra = re_ and rs_ and (abs(re_[0] - rs_[0]) > 12 or abs(re_[1] - rs_[1]) > 12) and min(re_[2], rs_[2]) >= 4
        one = bool(strong) and not contra and pred is not None
        ok = bool(both or one)
        if both: d = ((re_[0] + rs_[0]) / 2, (re_[1] + rs_[1]) / 2)
        elif one: d = (strong[0][0], strong[0][1])
        else: d = None
        if ok:
            v = np.array(d) / dt_ref; vel = v if vel is None else 0.6 * vel + 0.4 * v
        updates.append(dict(sweep=b, ref=a, dir=DIR[b], rows=r0, t=t_ready - T0[20], dt_ref=dt_ref, ok=ok,
                            mode="blind" if pred is None else "tracking", how="both" if both else ("one" if one else "none"),
                            dy=None if d is None else d[0], dx=None if d is None else d[1]))
tm = np.array(timings) * 1000
print(f"band updates: {len(updates)}, locked {sum(u['ok'] for u in updates)}; compute per update: median {np.median(tm):.0f} ms, max {tm.max():.0f} ms (full-frame search, both channels)")
# velocity per update = displacement / time between the same rows in the two same-direction sweeps
for u in updates:
    if u["ok"]: u["vy"] = -u["dy"] / u["dt_ref"]; u["vx"] = -u["dx"] / u["dt_ref"]     # +vy = moving up the frame
ok = [u for u in updates if u["ok"]]
print("velocity up the frame (px/s): median %.2f, IQR %.2f–%.2f; sideways median %.2f" % (
    np.median([u['vy'] for u in ok]), *np.percentile([u['vy'] for u in ok], [25, 75]), np.median([u['vx'] for u in ok])))
json.dump(dict(updates=updates, ms_median=float(np.median(tm)), ms_max=float(tm.max())),
          open(os.path.join(HERE, "morph_report", "live_trail.json"), "w"), indent=1, default=float)

# ---- integrate a drift position track (feature displacement in the frame) from the velocities
track = []; pos = np.zeros(2); last_t = 0.0; vel = np.array([0.0, 0.0])
for u in updates:
    if u["ok"]: vel = 0.5 * vel + 0.5 * np.array([u["vy"], -u["vx"]]) if track else np.array([u["vy"], -u["vx"]])
    pos = pos + vel * (u["t"] - last_t); last_t = u["t"]
    track.append(dict(t=u["t"], y=float(pos[0]), x=float(pos[1]), ok=u["ok"], vy=float(vel[0]), vx=float(vel[1]), sweep=u["sweep"], dir=u["dir"]))

# ---- render the widget as an animated GIF
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from PIL import Image
import io
frames = []; TAIL = 8
for k in range(len(track)):
    fig, ax = plt.subplots(figsize=(4.2, 4.6), dpi=90)
    ax.set_xlim(-15, 15); ax.set_ylim(-15, 15); ax.set_aspect("equal")
    ax.add_patch(plt.Rectangle((-15, -15), 30, 30, fill=False, ec="#888", lw=1))
    ax.axhline(0, color="#ddd", lw=0.6); ax.axvline(0, color="#ddd", lw=0.6)
    seg = track[max(0, k - TAIL):k + 1]
    pts = [(-q["x"] * PX, q["y"] * PX) for q in seg]          # nm; +y = up the frame, -x = left
    for j in range(1, len(pts)):
        age = len(pts) - 1 - j; alpha = 0.15 + 0.85 * (1 - age / TAIL)
        ax.annotate("", xy=pts[j], xytext=pts[j - 1], arrowprops=dict(arrowstyle="->", color="#1f77b4", alpha=alpha, lw=1 + 1.5 * (1 - age / TAIL)))
    for j, (x, y) in enumerate(pts[:-1]):
        age = len(pts) - 1 - j; ax.plot(x, y, "o", color="#1f77b4", alpha=0.15 + 0.85 * (1 - age / TAIL), ms=4)
    q = track[k]; lead = pts[-1]
    ax.plot(*lead, "o", color="#e4572e" if q["ok"] else "#999", ms=11, mec="k")
    sp_ = np.hypot(q["vy"], q["vx"]) * PX * 1000
    ax.set_title(f"sweep #{q['sweep']} {'▲' if q['dir'] == 'up' else '▼'} · t = {q['t']:.0f} s\n"
                 f"{'LOCKED' if q['ok'] else 'coasting (no lock)'} · {sp_:.0f} pm/s, {np.degrees(np.arctan2(q['vy'], -q['vx'])):.0f}°", fontsize=9,
                 color="#063" if q["ok"] else "#a00")
    ax.set_xlabel("x drift (nm)"); ax.set_ylabel("y drift (nm, up)")
    plt.tight_layout(); b = io.BytesIO(); fig.savefig(b, format="png"); plt.close(fig)
    frames.append(Image.open(io.BytesIO(b.getvalue())).convert("P", palette=Image.ADAPTIVE))
out = os.path.join(HERE, "morph_report", "live_trail.gif")
frames[0].save(out, save_all=True, append_images=frames[1:], duration=600, loop=0)
print("gif:", out, len(frames), "frames")
