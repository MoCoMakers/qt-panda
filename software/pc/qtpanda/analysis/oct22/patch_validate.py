import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
MARK = "SW = [i for i in range(12, 32) if D.sweeps"
src = open("patch_track.py", encoding="utf-8").read().split(MARK)[0]
ns = {"__file__": os.path.abspath("patch_track.py")}; exec(compile(src, "pt", "exec"), ns)
np, sp = ns["np"], ns["sp"]
DO = ns["D"]; DS = sp.DayData("2026-Sep-24")

CASES = ((DS, 1806, 1808, "Sep24 good"), (DS, 1588, 1590, "Sep24 good"),
         (DO, 21, 22, "Oct22 2.3"), (DO, 27, 28, "Oct22 4.6"), (DO, 30, 31, "Oct22 9"),
         (DO, 23, 25, "Oct22 2.3->4.6"))
for PS, SIG in ((48, 2.0), (64, 1.0), (96, 1.0), (128, 1.0)):
    ns["PS"], ns["SIG"], ns["STRIDE"] = PS, SIG, max(16, PS // 2)
    for Dd, a, b, tag in CASES:
        for chan in ("err", "S"):
            prep = ns["prep_err"] if chan == "err" else ns["prep_S"]
            other = (DO, 22) if Dd is DS else (DS, 1806)
            A, B, N = prep(Dd, a), prep(Dd, b), prep(*other)
            c = ns["consensus"](ns["track"](A, B, [A[::-1, ::-1], N]))
            print(f"PS {PS:3d} sig {SIG}  {tag:15} #{a}->#{b} {chan:3}  shift dy {c['dy']:+5.1f} dx {c['dx']:+5.1f}  "
                  f"agree {c['n_agree']:2d}/{c['n']:2d} ({c['frac']:.0%})  peak {c['peak_agree']:.2f}  "
                  f"null p95 {c['null_p95']:.2f}  beat {c['beat_null']:.0%}", flush=True)
