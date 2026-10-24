"""Data for the v2 3D mound page: per-sweep source images with the exact contour used,
terrace height maps for two slice orders (time order = operator's sequence; size order)."""
import os, json, io, base64, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "contour_stack.py"), encoding="utf-8").read().split("# figure: contours, stack height map")[0]
src = src.replace('fig.savefig(os.path.join(OUT, "figC0_fullframes.png"), dpi=80)', 'pass')
cs = {"__file__": os.path.join(HERE, "contour_stack.py")}; exec(compile(src, "cs", "exec"), cs)
np, ndi, plt = cs["np"], cs["ndi"], cs["plt"]
g = cs["g"]; D = g["D"]; PX = cs["PX"]
R0, R1, C0, C1 = cs["R0"], cs["R1"], cs["C0_"], cs["C1_"]
import matplotlib.patches as mpatches

M = cs["masks"]["dark"]
usable = [i for i in cs["SEQ"] if M[i]["coverage"] > 0.85 and M[i]["area_px"] > 20]
time_order = sorted(usable, key=g["t"])                       # operator's sequence: #20 first = summit
size_order = sorted(usable, key=lambda i: M[i]["area_px"])     # smallest dark outline = summit


def png(fig):
    b = io.BytesIO(); fig.savefig(b, format="png", dpi=100); plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()


def contour_segs(mask):
    fig, ax = plt.subplots()
    cset = ax.contour(mask.astype(float), levels=[0.5])
    segs = [s for s in cset.allsegs[0] if len(s) >= 6]
    plt.close(fig)
    return segs                                                  # arrays of (x=col, y=row) in ROI coords


sweeps = []
for i in usable:
    mask = M[i]["mask"]
    segs = contour_segs(mask)
    filled = ndi.binary_fill_holes(mask)
    dy, dx = g["shift_from_20"](i)
    E = g["IMG"][i][0]; lo, hi = np.percentile(E, [1, 99])
    d = D.sweeps[i][2]["dir"]
    # full original frame with the region used and the exact contour, in the sweep's own coordinates
    fig, ax = plt.subplots(figsize=(3.4, 3.4))
    ax.imshow(E, cmap="inferno", vmin=lo, vmax=hi, interpolation="nearest")
    ax.add_patch(mpatches.Rectangle((C0 + dx, R0 + dy), C1 - C0, R1 - R0, fill=False, ec="white", lw=1, ls="--"))
    for s in segs:
        ax.plot(s[:, 0] + C0 + dx, s[:, 1] + R0 + dy, color="cyan", lw=1.4)
    ax.set_xlim(-0.5, 255.5); ax.set_ylim(255.5, -0.5); ax.set_xticks([]); ax.set_yticks([])
    fig.subplots_adjust(0, 0, 1, 1)
    full_png = png(fig)
    # the drift-corrected crop that went into the stack, with the same contour
    crop = cs["to20"](E, i)[R0:R1, C0:C1]
    fig, ax = plt.subplots(figsize=(3.4, 3.4 * (R1 - R0) / (C1 - C0)))
    ax.imshow(crop, cmap="inferno", vmin=lo, vmax=hi, interpolation="nearest")
    for s in segs:
        ax.plot(s[:, 0], s[:, 1], color="cyan", lw=1.4)
    ax.set_xticks([]); ax.set_yticks([]); fig.subplots_adjust(0, 0, 1, 1)
    crop_png = png(fig)
    sweeps.append(dict(id=i, dir="▲" if d == "up" else "▼", kiga=g["RUNG"][i],
                       time=dt.datetime.fromtimestamp(g["t"](i)).strftime("%H:%M:%S"),
                       dark_nm2=round(float(mask.sum()) * PX ** 2, 1),
                       extent_nm2=round(float(filled.sum()) * PX ** 2, 1),
                       segs=[np.round(s, 1).tolist() for s in segs], full=full_png, crop=crop_png))


def terrace(order):
    """top of the order = highest level; height = highest level whose outline contains the point."""
    n = len(order); h = np.zeros(M[order[0]]["mask"].shape)
    for k, i in enumerate(order):
        lev = n - k                                    # first = summit = n
        h = np.maximum(h, lev * M[i]["mask"])
    return ndi.gaussian_filter(h, 1.2)


def nesting(order):
    out = []
    for a, b in zip(order, order[1:]):                 # a above b: share of a's outline inside b's
        A, B = M[a]["mask"], M[b]["mask"]; out.append(round(float((A & B).sum() / max(A.sum(), 1)), 2))
    return out


data = dict(rows=R1 - R0, cols=C1 - C0, px_nm=PX,
            circle=[cs["CIRC"][0] - R0, cs["CIRC"][1] - C0, cs["CIRC"][2], cs["CIRC"][3]],
            orders={"time": [int(i) for i in time_order], "size": [int(i) for i in size_order]},
            heights={"time": np.round(terrace(time_order), 2).tolist(), "size": np.round(terrace(size_order), 2).tolist()},
            nesting={"time": nesting(time_order), "size": nesting(size_order)},
            sweeps={str(s["id"]): s for s in sweeps})
json.dump(data, open(os.path.join(HERE, "morph_report", "mound_v2.json"), "w"))
print("time order:", time_order, "nesting", data["nesting"]["time"])
print("size order:", size_order, "nesting", data["nesting"]["size"])
for s in sweeps: print(f"#{s['id']} {s['time']} K{s['kiga']} dark {s['dark_nm2']} nm2, outer extent {s['extent_nm2']} nm2, {len(s['segs'])} contour pieces")
