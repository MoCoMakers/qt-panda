"""v3: per-slice FULL source frames (raw as in the replay player, and as analysed), exact
contour + region drawn, #18 included as context.  Reuses v2 data for heights/orders."""
import os, json, io, base64
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "contour_stack.py"), encoding="utf-8").read().split("# figure: contours, stack height map")[0]
src = src.replace('fig.savefig(os.path.join(OUT, "figC0_fullframes.png"), dpi=80)', 'pass')
cs = {"__file__": os.path.join(HERE, "contour_stack.py")}; exec(compile(src, "cs", "exec"), cs)
np, plt = cs["np"], cs["plt"]; g = cs["g"]; D = g["D"]; inner = g["ns"]["ns"]
R0, R1, C0, C1 = cs["R0"], cs["R1"], cs["C0_"], cs["C1_"]
import matplotlib.patches as mpatches
v2 = json.load(open(os.path.join(HERE, "morph_report", "mound_v2.json")))

def png(fig):
    b = io.BytesIO(); fig.savefig(b, format="png", dpi=110); plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()

def frame(img, i, segs, lohi):
    dy, dx = g["shift_from_20"](i)
    fig, ax = plt.subplots(figsize=(4.6, 4.6))
    ax.imshow(img, cmap="inferno", vmin=lohi[0], vmax=lohi[1], interpolation="nearest")
    ax.add_patch(mpatches.Rectangle((C0 + dx - 0.5, R0 + dy - 0.5), C1 - C0, R1 - R0, fill=False, ec="white", lw=1, ls="--"))
    cy, cx, hr, hc = cs["CIRC"]
    ax.add_patch(mpatches.Ellipse((cx + dx, cy + dy), 2 * hc, 2 * hr, fill=False, ec="#39ff14", lw=1.6, ls="-" if i == 20 else "--"))
    for s in segs:
        s = np.array(s); ax.plot(s[:, 0] + C0 + dx, s[:, 1] + R0 + dy, color="cyan", lw=1.5)
    ax.set_xlim(-0.5, 255.5); ax.set_ylim(255.5, -0.5); ax.set_xticks([]); ax.set_yticks([])
    fig.subplots_adjust(0, 0, 1, 1)
    return png(fig)

for sid in list(v2["sweeps"].keys()) + ["18"]:
    i = int(sid)
    raw = inner["fill_rows"](D.image(i, "e_trace")[0])
    segs = v2["sweeps"][sid]["segs"] if sid in v2["sweeps"] else []
    raw_png = frame(raw, i, segs, np.nanpercentile(raw, [2, 98]))       # replay-player style: raw, 2-98 % levels
    E = g["IMG"][i][0]
    ana_png = frame(E, i, segs, np.percentile(E, [1, 99]))
    if sid in v2["sweeps"]:
        v2["sweeps"][sid].update(raw=raw_png, analysed=ana_png); v2["sweeps"][sid].pop("full", None); v2["sweeps"][sid].pop("crop", None)
    else:
        import datetime as dt
        v2["context18"] = dict(id=18, dir="▼", kiga="1.14", time=dt.datetime.fromtimestamp(g["t"](18)).strftime("%H:%M:%S"),
                               raw=raw_png, analysed=ana_png)
json.dump(v2, open(os.path.join(HERE, "morph_report", "mound_v3.json"), "w"))
print("ok", len(v2["sweeps"]))
