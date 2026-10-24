"""v4: add the operator's reading as the default mode.
Cross-section per sweep = bright (not-dark) region inside the dark structure's convex hull, within the carried circle (×1.3),
stacked in sweep order with #20 at the top.  Full source frames drawn with that contour."""
import os, json, io, base64
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "contour_stack.py"), encoding="utf-8").read().split("# figure: contours, stack height map")[0]
src = src.replace('fig.savefig(os.path.join(OUT, "figC0_fullframes.png"), dpi=80)', 'pass')
cs = {"__file__": os.path.join(HERE, "contour_stack.py")}; exec(compile(src, "cs", "exec"), cs)
np, plt, ndi = cs["np"], cs["plt"], cs["ndi"]; g = cs["g"]; D = g["D"]; inner = g["ns"]["ns"]
R0, R1, C0, C1 = cs["R0"], cs["R1"], cs["C0_"], cs["C1_"]; PX = cs["PX"]
import matplotlib.patches as mpatches
v = json.load(open(os.path.join(HERE, "morph_report", "mound_v3.json")))
CY, CX, HR, HC = cs["CIRC"]
yy, xx = np.mgrid[R0:R1, C0:C1]
ell = ((yy - CY) / (HR * 1.3)) ** 2 + ((xx - CX) / (HC * 1.3)) ** 2 <= 1.0        # in #20 coordinates (ROI)

def png(fig):
    b = io.BytesIO(); fig.savefig(b, format="png", dpi=110); plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()

def segs_of(mask):
    fig, ax = plt.subplots(); c = ax.contour(mask.astype(float), levels=[0.5]); s = [q for q in c.allsegs[0] if len(q) >= 6]; plt.close(fig); return s

def frame(img, i, segs, lohi):
    dy, dx = g["shift_from_20"](i)
    fig, ax = plt.subplots(figsize=(4.6, 4.6))
    ax.imshow(img, cmap="inferno", vmin=lohi[0], vmax=lohi[1], interpolation="nearest")
    ax.add_patch(mpatches.Ellipse((CX + dx, CY + dy), 2 * HC, 2 * HR, fill=False, ec="#39ff14", lw=1.6, ls="-" if i == 20 else "--"))
    ax.add_patch(mpatches.Ellipse((CX + dx, CY + dy), 2 * HC * 1.3, 2 * HR * 1.3, fill=False, ec="white", lw=0.8, ls=":"))
    for s in segs: ax.plot(s[:, 0] + C0 + dx, s[:, 1] + R0 + dy, color="cyan", lw=1.6)
    ax.set_xlim(-0.5, 255.5); ax.set_ylim(255.5, -0.5); ax.set_xticks([]); ax.set_yticks([]); fig.subplots_adjust(0, 0, 1, 1)
    return png(fig)

order = [20, 21, 22, 23, 25, 26, 27, 28, 30]
masks = {}
for i in order:
    E = g["IMG"][i][0]; E20 = cs["to20"](E, i)[R0:R1, C0:C1]
    valid = np.isfinite(E20)
    darkc = cs["masks"]["dark"][i]["mask"] & ell                      # the dark structure around the circle
    hull = np.zeros_like(darkc)
    py, px_ = np.nonzero(darkc)
    if len(py) > 3:
        from scipy.spatial import ConvexHull
        from matplotlib.path import Path
        hv = ConvexHull(np.c_[px_, py]).vertices
        poly = Path(np.c_[px_[hv], py[hv]])
        gy, gx = np.mgrid[0:darkc.shape[0], 0:darkc.shape[1]]
        hull = poly.contains_points(np.c_[gx.ravel(), gy.ravel()]).reshape(darkc.shape)
    bright = valid & hull & ell & (np.nan_to_num(E20, nan=-1e12) >= np.percentile(E, 20))
    bright = ndi.binary_opening(bright, iterations=1)
    masks[i] = bright
    segs = segs_of(bright)
    raw = inner["fill_rows"](D.image(i, "e_trace")[0])
    v["sweeps"][str(i)]["yours"] = dict(area_nm2=round(float(bright.sum()) * PX ** 2, 1),
                                        ell_nm2=round(float((ell & valid).sum()) * PX ** 2, 1),
                                        segs=[np.round(s, 1).tolist() for s in segs],
                                        raw=frame(raw, i, segs, np.nanpercentile(raw, [2, 98])),
                                        analysed=frame(E, i, segs, np.percentile(E, [1, 99])))
n = len(order); h = np.zeros(ell.shape)
for k, i in enumerate(order):
    h = np.maximum(h, (n - k) * masks[i])       # #20 = highest level
nest = [round(float((masks[a] & masks[b]).sum() / max(masks[a].sum(), 1)), 2) for a, b in zip(order, order[1:])]
v["orders"]["yours"] = order
v["heights"]["yours"] = np.round(ndi.gaussian_filter(h, 1.2), 2).tolist()
v["nesting"]["yours"] = nest
json.dump(v, open(os.path.join(HERE, "morph_report", "mound_v4.json"), "w"))
for i in order: print(f"#{i}: bright inside circle {v['sweeps'][str(i)]['yours']['area_nm2']} nm2 of {v['sweeps'][str(i)]['yours']['ell_nm2']} nm2")
print("nesting (share of each slice inside the next one down):", nest)
