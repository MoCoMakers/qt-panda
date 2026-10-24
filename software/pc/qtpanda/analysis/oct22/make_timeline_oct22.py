"""Write TIMELINE.json for 2026-Oct-22 from the draft + journal facts."""
import json, time, datetime as dt

DAY = "C:/Users/enact/Projects/qt-panda/TeamUpdate/data/2026-Oct-22/"
draft = json.load(open(DAY + "TIMELINE.draft.json"))


def T(hms):
    h, m, s = map(int, hms.split(":"))
    return dt.datetime(2026, 10, 22, h, m, s).timestamp()


def find(kind, t0):
    """Exact draft region timestamps for a region starting at hh:mm:ss."""
    for r in draft["regions"]:
        if r["kind"] == kind and abs(r["t0"] - T(t0)) < 1.5:
            return r["t0"], r["t1"]
    raise KeyError((kind, t0))


R = []
def reg(kind, t0, t1, label, detail=""):
    R.append({"t0": t0, "t1": t1, "kind": kind, "label": label, **({"detail": detail} if detail else {})})

# ---- sessions (backbone)
s1 = find("session", "18:22:28"); s2 = find("session", "18:34:28")
s3 = find("session", "18:40:12"); s4 = find("session", "18:43:46")
END = T("19:52:04")
reg("session", *s1, "bias setup, first approach tries (clean close)",
    "RSET x2, bias 40282 then 33310, APRH 20 / APRH 90. session_end written.")
reg("session", *s2, "relaunch; [FW] garbage lines investigated",
    "Raw ISR stream desync printed binary sample bytes as [FW] text. No session_end (exited unexpectedly).")
reg("session", *s3, "relaunch; exited after ~2 min (no session_end)")
reg("session", s4[0], END, "approach, tip contact, KIGA ladder, operator scan",
    "Launched in a persistent cmd window. Journal records stop at 19:42:09 although the scan "
    ".frames and status CSV continue to 19:52:04 with no stop event; GUI process still open at export.")

# ---- stability + raw (keep, honest labels)
for r in draft["regions"]:
    if r["kind"] == "stability":
        reg("stability", r["t0"], min(r["t1"], END), "status stream 200 Hz recording")
raw_lossy = {"18:22:28": "6.0%", "18:34:28": "4.0%", "18:40:12": "9.2%"}
for r in draft["regions"]:
    if r["kind"] != "raw":
        continue
    hms = dt.datetime.fromtimestamp(r["t0"]).strftime("%H:%M:%S")
    if hms in raw_lossy:
        reg("raw", r["t0"], r["t1"], f"raw tap 100 kHz, {raw_lossy[hms]} blocks lost (desync)")
    elif hms == "18:43:46":
        reg("raw", r["t0"], r["t1"], "raw tap 100 kHz, lossy (desync, [FW] spam)",
            "Session-long capture; firmware dropped ~1.0M samples; block gaps include seq resets.")
    else:
        reg("raw", r["t0"], r["t1"], "raw tap 100 kHz, 0 blocks lost")

# ---- real approaches (APRH from journal), replacing 'firmware activity' bands
reg("approach", T("18:29:42"), T("18:29:51"), "tip approach, 2 APRH attempts")
reg("approach", T("18:47:59"), T("19:09:15"), "tip approach, APRH x10 (Approached! 18:47, 19:04, 19:06)",
    "APRH 90 1 repeated 18:47-19:07; bias briefly 45704 at 18:59. 19:06:02 approached (Z 43600), intermittent "
    "tunnelling to 19:07:45, then re-approach +10,000 motor steps (65069 -> 75069) ending 19:09:15.")
reg("approach", T("19:11:00"), T("19:12:23"), "motor retract 1,826 steps after crash (+ APRH 19:11:34)",
    "Steps 75069 -> 73243 via MTMV -10 clicks; APRH at 19:11:34 reported Approached! immediately because the "
    "current was already saturated (Z set to 48600).")

# ---- scans
sc = lambda t: find("scanning", t)
a = sc("19:12:33")
reg("scanning", *a, "operator scan, CC off, started on a crashed junction",
    "30 nm, KIGA 4.0, 512->256 px/line at 19:12:52. Continuous-Scan RUN does not send ENGA, so the scan ran at fixed Z. "
    "The tip had already crashed at 19:10:30; the current was 30-50% saturated when the scan began and mostly saturated "
    "(>102 nA) throughout. Claude halted at 19:16:32.")
b = sc("19:24:05")
reg("scanning", *b, "post-contact tip check scan, KIGA 1.14, CC on",
    "1 Y-cycle, 30 nm. 0 tip-switch row jumps; Y+/Y- corr 0.64; lag share 0.78.")
for t0, ki, txt in [("19:26:10", "1.14", "clean; lag share 0.87-0.94"),
                    ("19:28:43", "2.3", "clean; Z tracking ~2x"),
                    ("19:31:00", "4.6", "clean, last stable; lag share 0.79-0.84")]:
    reg("scanning", *sc(t0), f"KIGA ladder: KIGA {ki} rung ({txt.split(';')[0]})",
        f"30 nm, 512 px/line, 10 Hz requested, 500 pA, Kp 0, CC on, 2 Y-cycles. {txt}.")
reg("scanning", *sc("19:33:18"), "KIGA ladder: KIGA 9 rung, loop oscillated",
    "Current lost 60% / saturated 6.8% of the time, Z swung ~11,000 codes (max 48452); Z guard (46000) halted the scan after 69 s.")
reg("scanning", sc("19:42:10")[0], END, "operator scan at KIGA 3.07, 22 sweeps",
    "30 nm, 512 px/line. A Claude status check during this scan read Z 63023 (near full extension) and ADC -60: no tunnelling at that moment.")

# ---- events
E = []
def ev(t, kind, label, imp):
    E.append({"t": t, "kind": kind, "label": label, "important": imp})

for e in draft["events"]:
    lab = e["label"]
    if e["kind"] == "crash":
        if abs(e["t"] - T("19:42:09")) < 2:
            ev(e["t"], "crash", "journal silent after 19:42:09 (no session_end; scan/CSV data continue to 19:52:04)", True)
        else:
            ev(e["t"], "crash", "unclean session end (GUI exited, no session_end)", True)
    elif lab.startswith("restored DACX") or lab.startswith("frame log") \
            or "start (halted hold" in lab or "hold done" in lab or "scan done" in lab \
            or "scored:" in lab or lab.startswith("Claude KI-ladder: settings"):
        ev(e["t"], "note", lab, False)
    else:
        ev(e["t"], "note", lab, True)

ev(T("18:23:14"), "setting", "RSET (DAC reset) x2", False)
ev(T("19:09:15"), "milestone", "approach complete; tunnelling at fixed Z (CC off), up to ~3-4 nA, ~50% of samples <50 pA", True)
ev(T("19:10:30"), "milestone", "TIP CRASH at fixed Z (CC off): current saturates, 23% -> 100% of samples by 19:11:00; Z did not move", True)
ev(T("19:12:33"), "milestone", "operator RUN with CC off (RUN never sends ENGA) on the already-crashed junction: fixed-Z scan, KIGA 4.0, 30 nm", True)
ev(T("19:21:19"), "milestone", "CC engaged (ENGA, setpoint 500 pA): loop backed Z off ~10,000 codes from 35012 to ~24,900", True)
ev(T("19:25:36"), "milestone", "automated KIGA ladder starts (1.14 -> 2.3 -> 4.6 -> 9), 30 s halted hold + 2 Y-cycles per rung", True)
ev(T("19:28:09"), "milestone", "KIGA 1.14 rung clean: lag share 0.87-0.94; halted hold shows sharp 158.7 Hz line in Z and current", True)
ev(T("19:30:26"), "milestone", "KIGA 2.3 rung clean: Z variation ~2x baseline; 158.7 Hz Z power 4.5x", True)
ev(T("19:32:44"), "milestone", "KIGA 4.6 rung clean (last stable): lag share 0.79-0.84; 158.7 Hz Z power ~20x baseline", True)
ev(T("19:34:26"), "milestone", "KIGA 9 unstable: loop oscillated (crossover ~141 Hz vs 158.7 Hz resonance); Z guard abort", True)
ev(T("19:34:47"), "milestone", "running default KIGA set to 3.07 (2/3 of last clean 4.6); code default 4.0 unchanged", True)
ev(T("19:42:09"), "milestone", "operator RUN at KIGA 3.07 (CC engaged)", True)

# ---- brackets
B = []
def br(level, t0, t1, label):
    B.append({"t0": t0, "t1": t1, "level": level, "label": label})

# 0 instrument state (bias; preamp 1X from raw metadata)
br(0, T("18:23:34"), T("18:29:28"), "bias DAC 40282")
br(0, T("18:29:28"), s1[1], "bias 33310 (-50 mV)")
br(0, T("18:44:21"), T("18:59:18"), "bias DAC 33155")
br(0, T("18:59:40"), END, "bias 33310 (-50 mV), preamp 1X")
# 1 work phases
br(1, s1[0], s4[0], "GUI relaunches, [FW] garbage diagnosis")
br(1, s4[0], T("19:09:15"), "tip approach (APRH x10)")
br(1, T("19:09:15"), T("19:10:30"), "tunnelling, CC off")
br(1, T("19:10:30"), T("19:12:33"), "crash + motor retract 1,826 steps")
br(1, T("19:12:33"), T("19:16:32"), "CC-off scan, still in contact")
br(1, T("19:16:32"), T("19:24:05"), "recovery: Z backed off, CC engaged")
br(1, T("19:24:05"), T("19:34:47"), "KIGA ladder (automated, copilot)")
br(1, T("19:42:09"), END, "operator scan, KIGA 3.07")
# 2 incidents
br(2, T("19:10:30"), T("19:21:19"), "tip crash 19:10:30, contact to CC 19:21")
br(2, T("19:33:18"), T("19:34:47"), "KIGA 9 loop oscillation")
# 3 data quality
br(3, T("19:09:15"), T("19:10:30"), "last pre-crash tunnelling (good start)")
br(3, T("19:10:30"), T("19:28:43"), "post-crash: no trackable structure")
br(3, T("19:28:43"), T("19:34:26"), "weak surface tracked; drift 66 pm/s")
br(3, T("19:42:09"), END, "Z 63023, no current at one check")
# 4 uptime
br(4, s1[0], s1[1], "up 11m, clean close")
br(4, s2[0], s2[1], "up 5m, exited")
br(4, s3[0], s3[1], "up 2m, exited")
br(4, s4[0], END, "up 68m+, journal silent 19:42")
# 5 scan-scale eras (journaled SCSZ 629146 = 30 nm throughout)
br(5, a[0], a[1], "30 nm field, 12 sweeps")
br(5, b[0], T("19:34:26"), "30 nm field, 21 sweeps")
br(5, T("19:42:10"), END, "30 nm field, 24 sweeps")
# 7 sub-experiments
br(7, T("19:24:05"), T("19:24:58"), "tip-check scan KIGA 1.14")
br(7, T("19:25:36"), T("19:28:09"), "KIGA 1.14 clean")
br(7, T("19:28:09"), T("19:30:26"), "KIGA 2.3 clean")
br(7, T("19:30:26"), T("19:32:44"), "KIGA 4.6 clean, last stable")
br(7, T("19:32:44"), T("19:34:26"), "KIGA 9 oscillated, abort")
# 8 raw-tap coverage
br(8, s1[0], T("19:26:10"), "raw tap lossy: desync, [FW] spam")
br(8, T("19:26:12"), T("19:42:09"), "raw tap clean, 0 lost blocks")
# 9 setup
br(9, s1[0], END, "preamp 1X (raw meta); sample not journaled")

doc = {"day": "2026-Oct-22", "generated": time.time(), "generator": "timeline skill + claude",
       "regions": sorted(R, key=lambda r: r["t0"]), "events": sorted(E, key=lambda e: e["t"]),
       "brackets": B}
json.dump(doc, open(DAY + "TIMELINE.json", "w"), indent=1)
print(len(R), "regions", len(E), "events", len(B), "brackets")
