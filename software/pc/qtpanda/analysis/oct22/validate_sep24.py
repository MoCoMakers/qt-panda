import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
src = open("morph_report.py", encoding="utf-8").read().split("SW = [i for i")[0]
src = src.replace('D = sp.DayData("2026-Oct-22")', '')
ns = {"__file__": os.path.abspath("morph_report.py")}; exec(compile(src, "mr_helpers", "exec"), ns)
sp = ns["sp"]
D = sp.DayData("2026-Sep-24")
cand = [(i, s) for i, (fp, idx, s) in enumerate(D.sweeps)
        if s.get("scan_size_nm") and 24 <= float(s["scan_size_nm"]) <= 31 and not s["partial"]]
print("sep24 full sweeps 24-31 nm:", len(cand))
def prep(i):
    zt = ns["fill_rows"](D.image(i, "z_trace")[0]); zr = ns["fill_rows"](D.image(i, "z_retrace")[0])
    Bt, Br = ns["rowlev"](zt), ns["rowlev"](zr); return (Bt + Br) / 2, (Bt - Br) / 2
by = {}
for i, s in cand: by.setdefault((s["dir"], round(float(s["scan_size_nm"]), 1)), []).append(i)
for key, seq in by.items():
    for a, b in list(zip(seq, seq[1:]))[:4]:
        Sa, La = prep(a); Sb, Lb = prep(b)
        if Sa.shape != Sb.shape: continue
        dy, dx, pk = ns["phase_shift"](Sa, Sb)
        print(key, f"#{a}->#{b} shift dx {dx:6.1f} dy {dy:6.1f} peak {pk:5.1f}  S aligned {ns['overlap_corr'](Sa,Sb,dy,dx):.2f}  L {ns['overlap_corr'](La,Lb,dy,dx):.2f}")
