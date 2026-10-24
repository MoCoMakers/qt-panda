"""(1) Full-frame view of the circled feature: #20 with the operator's circle, the same
sample circle carried into later sweeps by the drift model.
(2) Contour-stack mound: map every sweep into #20 coordinates, take its clipped (and dark)
region as one contour, order by area (smallest = summit), and build a height map by
counting how many contours enclose each pixel.  Nestedness tests the assumption."""
import os, json
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "blob_case.py"), encoding="utf-8").read().split("\nrows = []")[0]
g = {"__file__": os.path.join(HERE, "blob_case.py")}; exec(compile(src, "bc", "exec"), g)
np, plt, D = g["np"], g["plt"], g["D"]
inner = g["ns"]["ns"]
from scipy import ndimage as ndi
import matplotlib.patches as mpatches
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
OUT = os.path.join(HERE, "morph_report")
PX = 30.0 / 256
CIRC = (220, 135, 36, 35)            # operator's circle in #20: centre row, col, half-height, half-width
SEQ = [20, 21, 22, 23, 25, 26, 27, 28, 30, 31]

# ---------------- (1) full frames with the carried circle
show_set = [20, 21, 22, 23, 25, 27]
fig, axes = plt.subplots(1, len(show_set), figsize=(4.0 * len(show_set), 4.6))
for ax, i in zip(axes, show_set):
    E = g["IMG"][i][0]; lo, hi = np.percentile(E, [1, 99])
    ax.imshow(E, cmap="inferno", vmin=lo, vmax=hi, interpolation="nearest")
    dy, dx = g["shift_from_20"](i)
    cy, cx = CIRC[0] + dy, CIRC[1] + dx
    ax.add_patch(mpatches.Ellipse((cx, cy), 2 * CIRC[3], 2 * CIRC[2], fill=False, ec="#39ff14",
                                  lw=2.5, ls="-" if i == 20 else "--"))
    ax.set_xlim(0, 255); ax.set_ylim(255, 0); ax.set_xticks([]); ax.set_yticks([])
    d = D.sweeps[i][2]["dir"]
    ax.set_title(f"#{i} {'▲' if d == 'up' else '▼'}  KIGA {g['RUNG'][i]}  {g['rows'][0] if False else ''}"
                 f"\n{'your circle' if i == 20 else 'same sample spot (drift model)'}", fontsize=10)
fig.suptitle("Error channel, full 30 nm frames. Green: the circled feature in #20 and where the drift model puts that same spot later", fontsize=11)
plt.tight_layout(); fig.savefig(os.path.join(OUT, "figC0_fullframes.png"), dpi=80); plt.close(fig)

# ---------------- (2) contour stack in #20 coordinates
def to20(a, i):
    """resample sweep i into #20 coordinates: out(y,x) = a(y+dy, x+dx)."""
    dy, dx = g["shift_from_20"](i)
    out = np.full(a.shape, np.nan)
    iy, ix = int(round(dy)), int(round(dx)); H, W = a.shape
    ys, ye = max(0, -iy), min(H, H - iy); xs, xe = max(0, -ix), min(W, W - ix)
    out[ys:ye, xs:xe] = a[ys + iy:ye + iy, xs + ix:xe + ix]
    return out

R0, R1, C0_, C1_ = 140, 256, 70, 210        # region of interest in #20 coordinates
masks = {}
for kind in ("clipped", "dark"):
    masks[kind] = {}
    for i in SEQ:
        raw = inner["fill_rows"](D.image(i, "e_trace")[0])
        if kind == "clipped":
            m = (raw == raw.min()).astype(float)
        else:
            E = g["IMG"][i][0]; m = (E < np.percentile(E, 20)).astype(float)
        m20 = to20(m, i)[R0:R1, C0_:C1_]
        valid = np.isfinite(m20)
        mb = np.nan_to_num(m20) > 0.5
        mb = ndi.binary_closing(ndi.binary_opening(mb, iterations=1), iterations=2)
        # keep the components that touch the operator's circle (in ROI coords)
        lab, n = ndi.label(mb)
        yy, xx = np.mgrid[R0:R1, C0_:C1_]
        circ = ((yy - CIRC[0]) / CIRC[2]) ** 2 + ((xx - CIRC[1]) / CIRC[3]) ** 2 <= 1.6
        keep = np.isin(lab, np.unique(lab[circ & (lab > 0)]))
        masks[kind][i] = dict(mask=keep, valid=valid, area_px=int(keep.sum()), coverage=float(valid.mean()))

summary = {}
for kind in ("clipped", "dark"):
    M = masks[kind]
    usable = [i for i in SEQ if M[i]["coverage"] > 0.85 and M[i]["area_px"] > 20]
    order = sorted(usable, key=lambda i: M[i]["area_px"])            # smallest = summit
    # nestedness: share of each smaller contour inside the next larger one
    nest = []
    for a, b in zip(order, order[1:]):
        A, B = M[a]["mask"], M[b]["mask"]
        nest.append(float((A & B).sum() / max(A.sum(), 1)))
    height = np.zeros_like(M[order[0]]["mask"], dtype=float)
    for i in order: height += M[i]["mask"]
    summary[kind] = dict(order=order, areas_nm2=[M[i]["area_px"] * PX ** 2 for i in order],
                         nestedness=nest, median_nest=float(np.median(nest)) if nest else None, height=height)
    print(kind, "order (summit first):", order)
    print("   areas nm2:", [round(x, 1) for x in summary[kind]["areas_nm2"]])
    print("   nestedness (share of smaller inside next larger):", [round(x, 2) for x in nest])

# figure: contours, stack height map, 3D surface
for kind in ("clipped", "dark"):
    S_ = summary[kind]; M = masks[kind]; order = S_["order"]; hmap = S_["height"]
    fig = plt.figure(figsize=(17, 4.8))
    ax0 = fig.add_subplot(1, 4, 1)
    base = g["IMG"][20][0][R0:R1, C0_:C1_]
    ax0.imshow(base, cmap="gray", vmin=np.percentile(base, 1), vmax=np.percentile(base, 99))
    cmap = plt.get_cmap("viridis")
    for k, i in enumerate(order):
        ax0.contour(M[i]["mask"].astype(float), levels=[0.5], colors=[cmap(k / max(1, len(order) - 1))], linewidths=1.3)
    ax0.set_title(f"{kind} outline of each sweep in #20 coordinates\n(yellow = largest, purple = smallest)", fontsize=8)
    ax0.set_xticks([]); ax0.set_yticks([])
    ax1 = fig.add_subplot(1, 4, 2)
    im = ax1.imshow(hmap, cmap="terrain"); ax1.contour(hmap, levels=np.arange(0.5, len(order)), colors="k", linewidths=0.4)
    ax1.set_title(f"stacked height = number of outlines enclosing each pixel\n(0 … {len(order)} contour steps)", fontsize=8)
    ax1.set_xticks([]); ax1.set_yticks([]); plt.colorbar(im, ax=ax1, fraction=0.046)
    ax2 = fig.add_subplot(1, 4, 3, projection="3d")
    hs = ndi.gaussian_filter(hmap, 2)
    yy, xx = np.mgrid[0:hs.shape[0], 0:hs.shape[1]]
    ax2.plot_surface(xx * PX, yy * PX, hs, cmap="terrain", linewidth=0, antialiased=True, rstride=2, cstride=2)
    ax2.set_xlabel("x (nm)", fontsize=7); ax2.set_ylabel("y (nm)", fontsize=7); ax2.set_zlabel("contour steps", fontsize=7)
    ax2.view_init(elev=38, azim=-60); ax2.tick_params(labelsize=6)
    ax2.set_title("the implied mound (smoothed)", fontsize=8)
    ax3 = fig.add_subplot(1, 4, 4)
    ax3.bar(range(len(order)), S_["areas_nm2"], color=[cmap(k / max(1, len(order) - 1)) for k in range(len(order))])
    ax3.set_xticks(range(len(order))); ax3.set_xticklabels([f"#{i}" for i in order], fontsize=7)
    for k, v in enumerate(S_["nestedness"]):
        ax3.annotate(f"{v:.0%}", (k + 0.5, max(S_["areas_nm2"]) * 0.95), fontsize=6, ha="center", color="#a00")
    ax3.set_ylabel("outline area (nm²)"); ax3.set_title("outline area, summit → base; red = share of each\noutline inside the next larger one (nesting)", fontsize=8)
    plt.tight_layout(); fig.savefig(os.path.join(OUT, f"figC4_stack_{kind}.png"), dpi=85); plt.close(fig)

json.dump({k: {kk: vv for kk, vv in v.items() if kk != "height"} for k, v in summary.items()},
          open(os.path.join(OUT, "contour_stack.json"), "w"), indent=1, default=float)
print("done")
