import os, json
os.environ["QT_QPA_PLATFORM"] = "offscreen"
MARK = "SW = [i for i in range(12, 32) if D.sweeps"
src = open("patch_track.py", encoding="utf-8").read().split(MARK)[0]
ns = {"__file__": os.path.abspath("patch_track.py")}; exec(compile(src, "pt", "exec"), ns)
np, D = ns["np"], ns["D"]
rows = json.load(open("morph_report/blob_metrics.json"))["rows"]
allv = np.concatenate([ns["ns"]["fill_rows"](D.image(i, "e_trace")[0]).ravel() for i in (20, 25, 30)])
lo_clip = np.min(allv); hi_clip = np.max(allv)
print("raw e_trace global min/max across sweeps:", lo_clip, hi_clip)
for r in rows:
    i = r["sweep"]
    e = ns["ns"]["fill_rows"](D.image(i, "e_trace")[0])
    y, x = int(round(r["centre_row"])), int(round(r["centre_col"]))
    win = e[max(0, y-40):y+40, max(0, x-40):x+40]
    lo = np.min(e)
    at_floor = np.mean(win <= lo + 0.02 * (np.max(e) - lo))
    at_floor_all = np.mean(e <= lo + 0.02 * (np.max(e) - lo))
    # row-wise flatness: fraction of window pixels whose value is exactly the sweep's minimum code
    exact = np.mean(win == lo)
    print(f"#{i}: window share at the error floor {at_floor:.0%} (whole sweep {at_floor_all:.0%}), exactly-min {exact:.0%}, floor value {lo:.0f}")
