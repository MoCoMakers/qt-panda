"""Double-tip test: a second tip apex images every feature twice at a fixed offset, which
shows as a secondary autocorrelation peak at the same vector in every sweep (tip-fixed,
independent of stage drift).  Compare Oct 22 #20-#31 with the Sep 24 good tip."""
import os, json
os.environ["QT_QPA_PLATFORM"] = "offscreen"
HERE = os.path.dirname(os.path.abspath(__file__))
MARK = "SW = [i for i in range(12, 32) if D.sweeps"
src = open(os.path.join(HERE, "patch_track.py"), encoding="utf-8").read().split(MARK)[0]
ns = {"__file__": os.path.join(HERE, "patch_track.py")}; exec(compile(src, "pt", "exec"), ns)
np, plt, D, sp = ns["np"], ns["plt"], ns["D"], ns["sp"]
ns["SIG"] = 1.0
from scipy.ndimage import maximum_filter


def acorr(a):
    a = a - a.mean(); a = a * np.outer(np.hanning(a.shape[0]), np.hanning(a.shape[1]))
    F = np.fft.fft2(a, s=(2 * a.shape[0], 2 * a.shape[1]))
    r = np.fft.fftshift(np.fft.ifft2(np.abs(F) ** 2).real)
    return r / r.max()


def secondary(r, excl=10, rowband=4):
    """strongest local maxima away from the centre and away from the horizontal axis
    (row streaks put a ridge along dy=0)."""
    c = np.array(r.shape) // 2
    loc = (r == maximum_filter(r, size=9))
    yy, xx = np.nonzero(loc)
    out = []
    for y, x in zip(yy, xx):
        dy, dx = y - c[0], x - c[1]
        if np.hypot(dy, dx) < excl or abs(dy) <= rowband or abs(dy) > 120 or abs(dx) > 120: continue
        if dy < 0 or (dy == 0 and dx < 0): continue          # symmetric: keep one half
        out.append((float(r[y, x]), int(dy), int(dx)))
    return sorted(out, reverse=True)[:3]


res = {}
SW = [20, 21, 22, 23, 25, 26, 27, 28, 30, 31]
for i in SW:
    for ch, prep in (("err", ns["prep_err"]), ("S", ns["prep_S"])):
        r = acorr(prep(D, i)); res[(i, ch)] = (r, secondary(r))
DS = sp.DayData("2026-Sep-24")
for i in (1806, 1808, 1588):
    r = acorr(ns["prep_err"](DS, i)); res[(i, "err")] = (r, secondary(r))
for k, (r, pk) in res.items():
    print(k, [(round(v, 2), dy, dx) for v, dy, dx in pk])

fig, axes = plt.subplots(2, 7, figsize=(17, 5.6))
show_list = [(20, "err"), (21, "err"), (22, "err"), (25, "err"), (27, "err"), (30, "err"), (31, "err"),
             (21, "S"), (22, "S"), (27, "S"), (31, "S"), (1806, "err"), (1808, "err"), (1588, "err")]
for ax, key in zip(axes.flat, show_list):
    r, pk = res[key]; c = np.array(r.shape) // 2
    sub = r[c[0] - 100:c[0] + 101, c[1] - 100:c[1] + 101]
    ax.imshow(sub, cmap="magma", vmin=-0.2, vmax=0.6, extent=(-100, 100, 100, -100))
    for v, dy, dx in pk[:2]:
        ax.plot([dx, -dx], [dy, -dy], "c+", ms=10, mew=1.5)
    day = "Sep 24 good tip" if key[0] > 1000 else "Oct 22"
    ax.set_title(f"{day} #{key[0]} {key[1]}\npeak {pk[0][0]:.2f} at ({pk[0][1]:+d},{pk[0][2]:+d})" if pk else f"#{key[0]}", fontsize=7)
    ax.set_xticks([-100, 0, 100]); ax.set_yticks([-100, 0, 100]); ax.tick_params(labelsize=6)
fig.suptitle("Image autocorrelation (dy, dx in px). A double tip adds the same off-centre peak in every sweep.", fontsize=9)
plt.tight_layout(); fig.savefig(os.path.join(HERE, "morph_report", "figC3_autocorr.png"), dpi=85)
json.dump({f"{k[0]}_{k[1]}": v[1] for k, v in res.items()}, open(os.path.join(HERE, "morph_report", "autocorr.json"), "w"), indent=1)
