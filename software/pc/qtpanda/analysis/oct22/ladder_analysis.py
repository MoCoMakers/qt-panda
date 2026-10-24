"""Like-for-like post analysis of the 2026-10-22 KIGA ladder.

Images: split by Y half (line# < H = Y+, else Y-, row = 2H-1-line) and by
Y-cycle (line-number wrap).  Trace and retrace are kept separate except in
the direction-flip (lag) measure, which needs both.
Holds: raw 100 kHz blocks sliced to each hold window by pc_time.
"""
import glob, json, os, re, struct, sys
import numpy as np

D = "C:/Users/enact/Projects/qt-panda/TeamUpdate/data/2026-Oct-22/"
J = D + "session_1792709026869.jsonl"
FH = struct.Struct('<BdHH'); RH = struct.Struct('<BdHHII')
RAW_DT = np.dtype([('adc', '>i2'), ('z', '>i4'), ('err', '>i4')])

# ---- rung windows from journal notes
ev = [json.loads(l) for l in open(J, encoding="utf-8")]
notes = [(e["t"], e["data"].get("text", "")) for e in ev if e["type"] == "note"]
rungs = {}
for t, txt in notes:
    m = re.match(r"Claude KI-ladder: KIGA ([\d.]+) (start|hold done|scan done)", txt)
    if m:
        rungs.setdefault(float(m.group(1)), {})[m.group(2)] = t
    if "ABORT" in txt and "KI-ladder" in txt:
        last = max(rungs); rungs[last].setdefault("scan done", t)


def level(a):
    x = np.arange(a.shape[-1]); A = np.vstack([x, np.ones_like(x)]).T
    c, *_ = np.linalg.lstsq(A, a.T, rcond=None)
    return a - (A @ c).T


def corr(a, b):
    a = a - a.mean(); b = b - b.mean()
    return float((a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum()))


def load_lines(t0, t1):
    out = []
    for f in sorted(glob.glob(D + "scan_*.frames")):
        st = int(os.path.basename(f).split("_")[1]) / 1000
        if st > t1 or st < t0 - 3600:
            continue
        with open(f, "rb") as fh:
            while True:
                h = fh.read(FH.size)
                if len(h) < FH.size: break
                m, t, ln, n = FH.unpack(h); p = fh.read(8 * n)
                if len(p) < 8 * n: break
                if t0 <= t <= t1:
                    out.append((t, ln, np.frombuffer(p[:4*n], '<i4').astype(float),
                                np.frombuffer(p[4*n:], '<i4').astype(float)))
    return out


def images(lines):
    """-> list of dicts {cycle, half, trace z, retrace z (X order), trace e, rows}"""
    n = len(lines[0][2]); N = n // 2; H = N
    cyc = 0; prev = None; buckets = {}
    for t, ln, z, e in lines:
        if prev is not None and ln < prev - H:   # wrapped to a new Y cycle
            cyc += 1
        prev = ln
        half = "Y+" if ln < H else "Y-"
        row = ln if ln < H else 2 * H - 1 - ln
        b = buckets.setdefault((cyc, half), {})
        b[row] = (z[:N], z[N:][::-1], e[:N])
    ims = []
    for (c, h), b in sorted(buckets.items()):
        rows = sorted(b)
        if len(rows) < 0.8 * H:      # incomplete half-sweep
            continue
        zt = np.full((H, N), np.nan); zr = zt.copy(); et = zt.copy()
        for r in rows:
            zt[r], zr[r], et[r] = b[r]
        ims.append(dict(cycle=c, half=h, zt=zt, zr=zr, et=et, nrows=len(rows)))
    return ims, H


def fill(a):
    m = np.isnan(a).any(1)
    a = a.copy(); a[m] = np.nanmean(a[~m], 0) if (~m).any() else 0
    return a


def score_image(im):
    zt, zr = level(fill(im["zt"])), level(fill(im["zr"]))
    L, S = (zt - zr) / 2, (zt + zr) / 2
    prof = zt.mean(0); res = zt - prof
    rr = np.mean([corr(res[i], res[i+1]) for i in range(len(res) - 1)])
    return dict(lag=L.var() / (L.var() + S.var()), locked=prof.var() / zt.var(),
                row_r=rr, z_std=zt.std(), S=S, L=L, zt=zt)


def raw_hold(t0, t1):
    segs = []
    for f in sorted(glob.glob(D + "raw_*.raw")):
        st = int(os.path.basename(f).split("_")[1]) / 1000
        if st > t1: continue
        meta = json.load(open(f[:-4] + ".json"))
        if meta.get("t_end", 1e12) < t0: continue
        fs = meta["meta"]["nominal_sample_hz"]
        d = open(f, "rb").read(); i = 0; cur = []; prev = None
        while i + RH.size <= len(d):
            m, pc, seq, cnt, tt0, dr = RH.unpack_from(d, i)
            if cnt == 0 or cnt > 512: break
            blk = np.frombuffer(d[i+RH.size:i+RH.size+cnt*10], RAW_DT); i += RH.size + cnt * 10
            if not (t0 <= pc <= t1):
                prev = None; continue
            if prev is not None and (seq - prev) % 65536 != 1 and cur:
                segs.append(np.concatenate(cur)); cur = []
            cur.append(blk); prev = seq
        if cur: segs.append(np.concatenate(cur))
    if not segs: return None
    nseg = 1 << 15; acc = {"adc": None, "z": None}; k = 0
    for s in segs:
        for j in range(0, len(s) - nseg + 1, nseg // 2):
            w = np.hanning(nseg)
            for ch in acc:
                x = s[ch][j:j+nseg].astype(float); x = x - x.mean()
                p = np.abs(np.fft.rfft(x * w)) ** 2
                acc[ch] = p if acc[ch] is None else acc[ch] + p
            k += 1
    fr = np.fft.rfftfreq(nseg, 1 / fs)
    out = {"segments": k, "seconds": sum(len(s) for s in segs) / fs}
    for ch in acc:
        p = acc[ch] / k
        def bp(a, b): m = (fr >= a) & (fr <= b); return float(p[m].mean())
        band = (fr >= 100) & (fr <= 300)
        idx = np.argsort(p[band])[::-1]
        peaks = []
        for ii in idx:
            f0 = fr[band][ii]
            if all(abs(f0 - q) > 8 for q, _ in peaks):
                peaks.append((round(float(f0), 1), round(float(p[band][ii] / np.median(p[band])), 1)))
            if len(peaks) == 3: break
        out[ch] = {"b20_100": bp(20, 100), "b100_300": bp(100, 300), "b300_1k": bp(300, 1000),
                   "peaks_100_300(hz,x_median)": peaks}
    return out


res = {}
per_im = {}
for ki in sorted(rungs):
    w = rungs[ki]
    r = {"ki": ki}
    if "start" in w and "hold done" in w:
        r["hold"] = raw_hold(w["start"] + 3, w["hold done"])
    if "hold done" in w and "scan done" in w:
        lines = load_lines(w["hold done"] + 1, w["scan done"])
        if lines:
            ims, H = images(lines)
            r["images"] = []
            for im in ims:
                sc = score_image(im)
                per_im[(ki, im["cycle"], im["half"])] = sc
                r["images"].append({"cycle": im["cycle"], "half": im["half"], "rows": im["nrows"],
                                    "lag_share": round(sc["lag"], 3), "row_locked": round(sc["locked"], 3),
                                    "row_r": round(sc["row_r"], 3), "z_std": round(sc["z_std"], 1)})
            rep = {}
            for h in ("Y+", "Y-"):
                cs = sorted(c for (k2, c, hh) in per_im if k2 == ki and hh == h)
                if len(cs) >= 2:
                    a, b = per_im[(ki, cs[0], h)], per_im[(ki, cs[1], h)]
                    rep[h] = {"trace": round(corr(a["zt"], b["zt"]), 3),
                              "S_folded": round(corr(a["S"], b["S"]), 3),
                              "L_lag": round(corr(a["L"], b["L"]), 3)}
            r["repeat_cycle_to_cycle"] = rep
    res[ki] = r

# cross-rung, same half, same direction: folded S of first full cycle vs KIGA 1.1444
base = min(res)
cross = {}
for ki in sorted(res):
    for h in ("Y+", "Y-"):
        a = [v for (k2, c, hh), v in per_im.items() if k2 == base and hh == h]
        b = [v for (k2, c, hh), v in per_im.items() if k2 == ki and hh == h]
        if a and b:
            cross.setdefault(ki, {})[h] = {"S_vs_base": round(corr(a[0]["S"], b[0]["S"]), 3),
                                          "trace_vs_base": round(corr(a[0]["zt"], b[0]["zt"]), 3)}
out = {"rungs": res, "cross_rung_vs_1.1444": cross}
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ladder_analysis.json"), "w"),
          indent=1, default=float)
for ki, r in res.items():
    print(f"\n=== KIGA {ki}")
    for im in r.get("images", []): print("  ", im)
    print("   repeat:", r.get("repeat_cycle_to_cycle"))
    print("   cross :", cross.get(ki))
    h = r.get("hold")
    if h:
        print(f"   hold {h['seconds']:.1f}s  adc 100-300 {h['adc']['b100_300']:.3g}  peaks {h['adc']['peaks_100_300(hz,x_median)']}")
        print(f"        z   100-300 {h['z']['b100_300']:.3g}  20-100 {h['z']['b20_100']:.3g}  peaks {h['z']['peaks_100_300(hz,x_median)']}")
