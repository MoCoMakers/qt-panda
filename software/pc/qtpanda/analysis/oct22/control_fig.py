import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
src = open("morph_report.py", encoding="utf-8").read().split("SW = [i for i")[0].replace('D = sp.DayData("2026-Oct-22")', '')
ns = {"__file__": os.path.abspath("morph_report.py")}; exec(compile(src, "h", "exec"), ns)
sp, plt, np = ns["sp"], ns["plt"], ns["np"]
def show(ax, a, title=None):
    lo, hi = np.percentile(a, [1, 99]); ax.imshow(a, cmap="inferno", vmin=lo, vmax=hi, interpolation="nearest")
    ax.set_xticks([]); ax.set_yticks([])
    if title: ax.set_title(title, fontsize=7)
ns["show"] = show
def S_of(D, i):
    zt = ns["fill_rows"](D.image(i, "z_trace")[0]); zr = ns["fill_rows"](D.image(i, "z_retrace")[0])
    return (ns["rowlev"](zt) + ns["rowlev"](zr)) / 2
pairs = [("2026-Sep-24", 1806, 1808, "Sep 24 · good tip · 27 nm"), ("2026-Oct-22", 25, 27, "Oct 22 · post-crash · 30 nm · KIGA 4.6 (best pair)"),
         ("2026-Oct-22", 20, 22, "Oct 22 · KIGA 2.3")]
fig, ax = plt.subplots(len(pairs), 3, figsize=(8.4, 2.9 * len(pairs)))
for r, (day, a, b, title) in enumerate(pairs):
    D = sp.DayData(day); Sa, Sb = S_of(D, a), S_of(D, b)
    dy, dx, _ = ns["phase_shift"](Sa, Sb)
    Sb_al = np.roll(np.roll(Sb, int(round(dy)), 0), int(round(dx)), 1)
    c = ns["overlap_corr"](Sa, Sb, dy, dx)
    ns["show"](ax[r, 0], Sa, f"#{a}")
    ns["show"](ax[r, 1], Sb_al, f"#{b} aligned (dx {dx:.0f}, dy {dy:.0f} px)")
    ns["show"](ax[r, 2], Sa - Sb_al * (Sa.std() / Sb_al.std()), f"difference · repeat corr {c:.2f}")
    ax[r, 0].set_ylabel(title, fontsize=8)
plt.tight_layout(pad=0.4); fig.savefig("morph_report/fig0_control.png", dpi=95)
print("ok")
