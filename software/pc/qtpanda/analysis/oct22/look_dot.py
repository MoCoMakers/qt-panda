"""Peaks-bright look at the circled feature, #18-#27: raw error, -error, -Z folded S, clipped mask."""
import os
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "blob_case.py"), encoding="utf-8").read().split("\nrows = []")[0]
g = {"__file__": os.path.join(HERE, "blob_case.py")}; exec(compile(src, "bc", "exec"), g)
np, plt, D = g["np"], g["plt"], g["D"]; inner = g["ns"]["ns"]
import matplotlib.patches as mp
SW = [20, 21, 22, 23, 25, 27]
fig, ax = plt.subplots(4, len(SW), figsize=(3.0 * len(SW), 12))
for k, i in enumerate(SW):
    dy, dx = g["shift_from_20"](i); c = (220 + dy, 135 + dx)
    raw = inner["fill_rows"](D.image(i, "e_trace")[0])
    E, S = g["crop"](g["IMG"][i][0], c), g["crop"](g["IMG"][i][1], c)
    R = g["crop"](raw, c); clip = (R == np.nanmax(raw)).astype(float)
    for r, (a, ttl, cm) in enumerate(((E, "error as stored", "inferno"), (-E, "−error (peaks bright)", "inferno"),
                                      (-S, "−Z folded S (peaks bright)", "inferno"), (clip, "clipped (white)", "gray"))):
        ax[r, k].imshow(a, cmap=cm, interpolation="nearest"); ax[r, k].set_xticks([]); ax[r, k].set_yticks([])
        ax[r, k].add_patch(mp.Ellipse((60, 60), 70, 72, fill=False, ec="#39ff14", lw=1.5, ls="--"))
        if k == 0: ax[r, k].set_ylabel(ttl)
    ax[0, k].set_title(f"#{i} KIGA {g['RUNG'][i]}")
plt.tight_layout(); fig.savefig(os.path.join(HERE, "look_dot.png"), dpi=70)
