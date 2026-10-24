import os, datetime as dt
os.environ["QT_QPA_PLATFORM"] = "offscreen"
src = open("morph_report.py", encoding="utf-8").read().split("SW = [i for i")[0]
ns = {"__file__": os.path.abspath("morph_report.py")}; exec(compile(src, "h", "exec"), ns)
np, D = ns["np"], ns["D"]
from scipy.ndimage import gaussian_filter
SW = [i for i in range(12, 32) if D.sweeps[i][2]["lines"] >= 250]
E = {}
for i in SW:
    a = ns["rowlev"](ns["fill_rows"](D.image(i, "e_trace")[0]))
    a = np.clip(a, *np.percentile(a, [2, 98]))
    E[i] = gaussian_filter(a, 4)          # suppress row streaks / pixel noise
ref = 22
print("dark-structure tracking, smoothed error trace (sigma 4 px); shift of each sweep vs #22, and vs previous sweep (any direction)")
prev = None
for i in SW:
    dy, dx, pk = ns["phase_shift"](E[ref], E[i]); c = ns["overlap_corr"](E[ref], E[i], dy, dx)
    line = f"#{i:2d} {'up  ' if D.sweeps[i][2]['dir']=='up' else 'down'} {dt.datetime.fromtimestamp(D.sweeps[i][2]['t_start']).strftime('%H:%M:%S')}  vs#22: dx {dx:+6.1f} dy {dy:+6.1f} corr {c:+.2f}"
    if prev is not None:
        dy2, dx2, _ = ns["phase_shift"](E[prev], E[i]); c2 = ns["overlap_corr"](E[prev], E[i], dy2, dx2)
        line += f"   vs prev #{prev}: dx {dx2:+6.1f} dy {dy2:+6.1f} corr {c2:+.2f} (unaligned {ns['corr'](E[prev], E[i]):+.2f})"
    print(line); prev = i
