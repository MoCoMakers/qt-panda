import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
MARK = "SW = [i for i in range(12, 32) if D.sweeps"
src = open("patch_track.py", encoding="utf-8").read().split(MARK)[0]
ns = {"__file__": os.path.abspath("patch_track.py")}; exec(compile(src, "pt", "exec"), ns)
np, D = ns["np"], ns["D"]; inner = ns["ns"]
print("tip-switch test: abrupt step in the row-mean of Z (trace and retrace agree) that persists >= 8 rows")
for i in (20, 21, 22, 23, 25, 26, 27, 28, 30, 31):
    zt = inner["fill_rows"](D.image(i, "z_trace")[0]); zr = inner["fill_rows"](D.image(i, "z_retrace")[0])
    mt, mr = zt.mean(1), zr.mean(1)
    def steps(m):
        d = m[8:] - m[:-8]                       # level change over 8 rows
        mad = np.median(np.abs(d - np.median(d))) + 1e-9
        return set(np.flatnonzero(np.abs(d - np.median(d)) > 8 * mad))
    both = steps(mt) & steps(mr)
    # collapse neighbouring indices into events
    ev = 0; last = -99
    for k in sorted(both):
        if k - last > 8: ev += 1
        last = k
    print(f"  #{i}: {ev} abrupt events (rows {sorted(both)[:6]}{'...' if len(both) > 6 else ''})")
