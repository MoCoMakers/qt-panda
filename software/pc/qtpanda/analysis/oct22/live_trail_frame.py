"""F2 figure: the live drift trail (left, from live_trail.json, same frames and timing as
live_trail.gif) next to the whole error frame of the sweep being registered (right), with the
operator's circle carried by the drift model and the contour found inside it (the bright opening
inside the dark structure, the default reading of the 3D mound page). Output: live_trail2.gif."""
import os, io, json
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "contour_stack.py"), encoding="utf-8").read().split("# figure: contours, stack height map")[0]
src = src.replace('fig.savefig(os.path.join(OUT, "figC0_fullframes.png"), dpi=80)', 'pass')
cs = {"__file__": os.path.join(HERE, "contour_stack.py")}; exec(compile(src, "cs", "exec"), cs)
np, plt, ndi = cs["np"], cs["plt"], cs["ndi"]; g = cs["g"]; D = g["D"]; inner = g["ns"]["ns"]
R0, R1, C0, C1 = cs["R0"], cs["R1"], cs["C0_"], cs["C1_"]; PX = cs["PX"]
CY, CX, HR, HC = cs["CIRC"]
import matplotlib.patches as mpatches
from scipy.spatial import ConvexHull
from matplotlib.path import Path
from PIL import Image

yy, xx = np.mgrid[R0:R1, C0:C1]
ell = ((yy - CY) / (HR * 1.3)) ** 2 + ((xx - CX) / (HC * 1.3)) ** 2 <= 1.0


def contour_segs(i):
    """Same construction as mound_v4_data.py: bright region inside the dark structure's hull."""
    E = g["IMG"][i][0]; E20 = cs["to20"](E, i)[R0:R1, C0:C1]
    valid = np.isfinite(E20)
    darkc = cs["masks"]["dark"][i]["mask"] & ell
    hull = np.zeros_like(darkc); py, px_ = np.nonzero(darkc)
    if len(py) > 3:
        hv = ConvexHull(np.c_[px_, py]).vertices; poly = Path(np.c_[px_[hv], py[hv]])
        gy, gx = np.mgrid[0:darkc.shape[0], 0:darkc.shape[1]]
        hull = poly.contains_points(np.c_[gx.ravel(), gy.ravel()]).reshape(darkc.shape)
    bright = ndi.binary_opening(valid & hull & ell & (np.nan_to_num(E20, nan=-1e12) >= np.percentile(E, 20)), iterations=1)
    f, a = plt.subplots(); c = a.contour(bright.astype(float), levels=[0.5]); s = [q for q in c.allsegs[0] if len(q) >= 6]; plt.close(f)
    return s


L = json.load(open(os.path.join(HERE, "morph_report", "live_trail.json")))["updates"]
track = []; pos = np.zeros(2); last_t = 0.0; vel = np.array([0.0, 0.0])
for u in L:                                       # identical to live_trail.py
    if u["ok"]: vel = 0.5 * vel + 0.5 * np.array([u["vy"], -u["vx"]]) if track else np.array([u["vy"], -u["vx"]])
    pos = pos + vel * (u["t"] - last_t); last_t = u["t"]
    track.append(dict(t=u["t"], y=float(pos[0]), x=float(pos[1]), ok=u["ok"], vy=float(vel[0]), vx=float(vel[1]),
                      sweep=u["sweep"], dir=u["dir"], rows=u["rows"]))

SEGS = {i: contour_segs(i) for i in sorted({q["sweep"] for q in track})}
RAW = {i: g["IMG"][i][0] for i in SEGS}                     # row-levelled error trace, as in Section C
frames = []; TAIL = 8
for k in range(len(track)):
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(8.6, 4.6), dpi=90, gridspec_kw=dict(width_ratios=[1, 1]))
    # ---- left: the trail, unchanged from live_trail.py
    ax.set_xlim(-15, 15); ax.set_ylim(-15, 15); ax.set_aspect("equal")
    ax.add_patch(plt.Rectangle((-15, -15), 30, 30, fill=False, ec="#888", lw=1))
    ax.axhline(0, color="#ddd", lw=0.6); ax.axvline(0, color="#ddd", lw=0.6)
    seg = track[max(0, k - TAIL):k + 1]
    pts = [(-q["x"] * PX, q["y"] * PX) for q in seg]
    for j in range(1, len(pts)):
        age = len(pts) - 1 - j; alpha = 0.15 + 0.85 * (1 - age / TAIL)
        ax.annotate("", xy=pts[j], xytext=pts[j - 1], arrowprops=dict(arrowstyle="->", color="#1f77b4", alpha=alpha, lw=1 + 1.5 * (1 - age / TAIL)))
    for j, (x, y) in enumerate(pts[:-1]):
        age = len(pts) - 1 - j; ax.plot(x, y, "o", color="#1f77b4", alpha=0.15 + 0.85 * (1 - age / TAIL), ms=4)
    q = track[k]; ax.plot(*pts[-1], "o", color="#e4572e" if q["ok"] else "#999", ms=11, mec="k")
    sp_ = np.hypot(q["vy"], q["vx"]) * PX * 1000
    ax.set_title(f"drift trail · t = {q['t']:.0f} s\n{'LOCKED' if q['ok'] else 'coasting (no lock)'} · {sp_:.0f} pm/s, "
                 f"{np.degrees(np.arctan2(q['vy'], -q['vx'])):.0f}°", fontsize=9, color="#063" if q["ok"] else "#a00")
    ax.set_xlabel("x drift (nm)"); ax.set_ylabel("y drift (nm, up)")
    # ---- right: the whole frame, carried circle, contour, band used for this update
    i = q["sweep"]; raw = RAW[i]; dy, dx = g["shift_from_20"](i)
    bx.imshow(raw, cmap="inferno", vmin=np.nanpercentile(raw, 1), vmax=np.nanpercentile(raw, 99), interpolation="nearest")
    bx.add_patch(mpatches.Ellipse((CX + dx, CY + dy), 2 * HC, 2 * HR, fill=False, ec="#39ff14", lw=1.8, ls="--"))
    for s in SEGS[i]: bx.plot(s[:, 0] + C0 + dx, s[:, 1] + R0 + dy, color="cyan", lw=1.6)
    bx.add_patch(plt.Rectangle((-0.5, q["rows"] - 0.5), 256, 96, fill=False, ec="white", lw=1.2, ls="--"))
    bx.set_xlim(-0.5, 255.5); bx.set_ylim(255.5, -0.5); bx.set_xticks([]); bx.set_yticks([])
    bx.set_title(f"sweep #{i} {'▲' if q['dir'] == 'up' else '▼'} · KIGA {g['RUNG'][i]} · error channel, 30 nm\n"
                 "green: circled spot (drift model) · cyan: contour · white: band", fontsize=9)
    plt.tight_layout(); b = io.BytesIO(); fig.savefig(b, format="png"); plt.close(fig)
    frames.append(Image.open(io.BytesIO(b.getvalue())).convert("P", palette=Image.ADAPTIVE))
out = os.path.join(HERE, "morph_report", "live_trail2.gif")
frames[0].save(out, save_all=True, append_images=frames[1:], duration=600, loop=0)
frames[12].convert("RGB").save(os.path.join(HERE, "morph_report", "live_trail2_check.png"))
print("gif:", out, len(frames), "frames", os.path.getsize(out) // 1000, "kB")
