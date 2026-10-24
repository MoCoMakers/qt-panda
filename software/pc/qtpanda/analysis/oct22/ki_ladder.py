"""Automated KIGA ladder via the copilot bridge (2026-10-22).

Per rung: set KIGA (halted, CC engaged) -> 30 s halted hold with raw capture
(decim 4, 25 kHz) -> RUN two full Y-cycles (raw off) -> HALT -> score.
Guards never move Z: on any trip the scan is halted and the ladder stops,
leaving CC (feedback) engaged so the loop itself retracts on overcurrent.
"""
import json, os, struct, sys, time, urllib.request
import numpy as np

B = "http://127.0.0.1:8765"
LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ki_ladder.log")
RUNGS = [1.1444, 2.3, 4.6, 9.0]
SET = dict(scan_size_nm=30.0, pixels_per_line=512, line_rate_hz=10.0,
           setpoint_pa=500.0, kp=0.0)
SP_LSB = 160
HOLD_S = 30
YCYCLES = 2
Z_MAX = 46000          # earlier contact at 48600 (higher = toward sample)
Z_MIN = 1500           # retract rail: can't tunnel
ADC_SAT = 32000
ADC_LOST = 16          # ~50 pA


def log(msg):
    line = f"{time.strftime('%H:%M:%S')}  {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def req(path, body=None, timeout=15):
    data = None if body is None else json.dumps(body).encode()
    r = urllib.request.Request(B + path, data=data, method="GET" if body is None else "POST",
                               headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def status():
    return req("/status")["status"]


def note(text):
    req("/note", {"text": f"Claude KI-ladder: {text}", "src": "claude"})
    log(f"NOTE {text}")


class Abort(Exception):
    pass


def halt_and_abort(why):
    try:
        req("/scan/halt", {})
    except Exception as e:
        log(f"halt failed: {e}")
    try:
        req("/raw/stop", {})
    except Exception:
        pass
    note(f"ABORT: {why}. Scan halted; CC left engaged; Z not moved by Claude.")
    raise Abort(why)


def guard_check(s, scanning, noise_ref=None, ki=None):
    adc, z = s["adc"], s["dac_z"]
    if z > Z_MAX:
        halt_and_abort(f"dac_z {z} > {Z_MAX} (toward earlier contact)")
    if z < Z_MIN:
        halt_and_abort(f"dac_z {z} < {Z_MIN} (retract rail, cannot tunnel)")
    if not s["is_const_current"]:
        halt_and_abort("constant current dropped out")


def watch(seconds, scanning, noise_ref=None, ki=None):
    """Poll 4x/s for `seconds`; returns list of (adc, z) samples."""
    sat = lost = 0
    out = []
    t_end = time.time() + seconds
    last_noise = time.time()
    while time.time() < t_end:
        s = status()
        out.append((s["adc"], s["dac_z"]))
        guard_check(s, scanning)
        sat = sat + 1 if s["adc"] >= ADC_SAT else 0
        lost = lost + 1 if s["adc"] <= ADC_LOST else 0
        if sat >= 3:
            halt_and_abort(f"ADC saturated ({s['adc']}) for 0.75 s")
        if lost >= 20:
            halt_and_abort(f"current lost (adc {s['adc']}) for 5 s")
        if scanning and noise_ref and time.time() - last_noise > 2:
            last_noise = time.time()
            smp = req("/samples?n=400").get("samples") or []
            a = np.array([x["adc"] for x in smp if x.get("is_scanning")], float)
            if len(a) > 100:
                nz = float(np.std(np.log(np.clip(a, 1, None))))
                if nz > 4 * noise_ref and nz > 0.5:
                    halt_and_abort(f"live current noise {nz:.2f} > 4x baseline "
                                   f"{noise_ref:.2f} at KIGA {ki} (ringing?)")
        time.sleep(0.25)
    return out


def live_noise(n=400):
    smp = req("/samples?n=%d" % n).get("samples") or []
    a = np.array([x["adc"] for x in smp if x.get("is_scanning")], float)
    return float(np.std(np.log(np.clip(a, 1, None)))) if len(a) > 100 else None


# ---------------------------------------------------------------- analysis
FH = struct.Struct('<BdHH')
RH = struct.Struct('<BdHHII')


def read_lines(path, t0, t1):
    rows = []
    with open(path, "rb") as f:
        while True:
            h = f.read(FH.size)
            if len(h) < FH.size:
                break
            m, t, ln, n = FH.unpack(h)
            p = f.read(8 * n)
            if len(p) < 8 * n:
                break
            if t0 <= t <= t1:
                rows.append((t, ln, np.frombuffer(p[:4*n], '<i4').astype(float),
                             np.frombuffer(p[4*n:], '<i4').astype(float)))
    return rows


def level(a):
    x = np.arange(a.shape[-1])
    out = np.empty_like(a)
    for i, r in enumerate(a):
        c = np.polyfit(x, r, 1)
        out[i] = r - np.polyval(c, x)
    return out


def score_scan(path, t0, t1):
    rows = read_lines(path, t0, t1)
    if len(rows) < 50:
        return {"lines": len(rows)}
    t = np.array([r[0] for r in rows])
    f_line = 1.0 / np.median(np.diff(t))
    n = len(rows[0][2]); N = n // 2
    Z = np.array([r[2] for r in rows if len(r[2]) == n])
    E = np.array([r[3] for r in rows if len(r[3]) == n])
    zt, zr = level(Z[:, :N]), level(Z[:, N:][:, ::-1])
    L, S = (zt - zr) / 2, (zt + zr) / 2
    lag_share = float(L.var() / (L.var() + S.var()))
    prof = zt.mean(0)
    pix_locked = float(np.var(np.broadcast_to(prof, zt.shape)) / zt.var())
    res = zt - prof
    r_adj = float(np.mean([np.corrcoef(res[i], res[i+1])[0, 1] for i in range(len(res) - 1)]))
    # ringing: error trace rows, temporal freq along the row
    et = level(E[:, :N])
    spec = (np.abs(np.fft.rfft(et * np.hanning(N), axis=1)) ** 2).mean(0)
    dwell = (1.0 / (2 * f_line)) / N
    fr = np.fft.rfftfreq(N, dwell)
    band = (fr >= 140) & (fr <= 260)
    ref = (fr >= 300) & (fr <= 700)
    ring = float(spec[band].mean() / spec[ref].mean()) if band.any() and ref.any() else None
    peak = float(fr[band][np.argmax(spec[band])]) if band.any() else None
    pk_ratio = float(spec[band].max() / np.median(spec[band])) if band.any() else None
    # lag tail in px: where |mean trace-retrace difference| falls below 1/e of its start
    d = np.abs(L.mean(0))
    return {"lines": len(rows), "f_line": round(f_line, 2), "lag_share": round(lag_share, 3),
            "pix_locked": round(pix_locked, 3), "row_r": round(r_adj, 3),
            "z_rms_pm_rel": round(float(zt.std()), 1),
            "ring_band_ratio": None if ring is None else round(ring, 2),
            "ring_peak_hz": None if peak is None else round(peak, 1),
            "ring_peak_sharp": None if pk_ratio is None else round(pk_ratio, 1)}


def score_raw(path, fs):
    d = open(path, "rb").read()
    i = 0; segs = []; cur = []; prev = None
    while i + RH.size <= len(d):
        m, pc, seq, cnt, t0, dr = RH.unpack_from(d, i)
        if cnt == 0 or cnt > 512:
            break
        blk = np.frombuffer(d[i+RH.size:i+RH.size+cnt*10],
                            np.dtype([('adc', '>i2'), ('z', '>i4'), ('err', '>i4')]))
        i += RH.size + cnt * 10
        if prev is not None and (seq - prev) % 65536 != 1:
            if cur: segs.append(np.concatenate(cur)); cur = []
        cur.append(blk); prev = seq
    if cur: segs.append(np.concatenate(cur))
    nseg = 8192
    acc = None; k = 0
    for s in segs:
        a = s['adc'].astype(float)
        for j in range(0, len(a) - nseg + 1, nseg // 2):
            x = a[j:j+nseg]; x = x - x.mean()
            p = np.abs(np.fft.rfft(x * np.hanning(nseg))) ** 2
            acc = p if acc is None else acc + p; k += 1
    if not k:
        return {"segments": 0}
    psd = acc / k
    fr = np.fft.rfftfreq(nseg, 1 / fs)
    def bp(a, b): m = (fr >= a) & (fr <= b); return float(psd[m].mean())
    band = (fr >= 140) & (fr <= 260)
    return {"segments": k, "band140_260": bp(140, 260), "ref300_700": bp(300, 700),
            "lowband20_100": bp(20, 100),
            "peak_hz": round(float(fr[band][np.argmax(psd[band])]), 1),
            "peak_sharp": round(float(psd[band].max() / np.median(psd[band])), 1)}


# ---------------------------------------------------------------- ladder
def main():
    log("=== KI ladder start ===")
    s = status()
    log(f"pre: adc={s['adc']} z={s['dac_z']} cc={s['is_const_current']} scan={s['is_scanning']}")
    if s["is_scanning"]:
        req("/scan/halt", {})
    if s["adc"] >= ADC_SAT:
        raise SystemExit("refusing: current saturated before start")
    req("/scan/settings", {**SET, "ki": RUNGS[0]})
    note(f"settings {SET}, KIGA {RUNGS[0]}; engaging CC (current {s['adc']} LSB vs setpoint {SP_LSB})")
    req("/scan/engage", {})
    w = watch(4, False)
    s = status()
    if not s["is_const_current"]:
        halt_and_abort("ENGA did not turn on constant current")
    def median_adc():
        smp = req("/samples?n=400").get("samples") or []
        return float(np.median([x["adc"] for x in smp])) if smp else -1
    m = median_adc()
    log(f"engaged: median adc={m} z={s['dac_z']}")
    if not (40 <= m <= 640):
        watch(6, False); m = median_adc()
        if not (40 <= m <= 640):
            halt_and_abort(f"not settled at setpoint after engage (median adc {m})")

    results = []
    noise_ref = None
    last_clean = None
    for ki in RUNGS:
        if ki == 9.0:
            prev = results[-1] if results else None
            if not prev or prev.get("ringing"):
                log("skip KIGA 9: previous rung not clean"); break
        req("/scan/settings", {**SET, "ki": ki})
        note(f"KIGA {ki} start (halted hold {HOLD_S}s, raw decim 4)")
        watch(3, False)
        rs = req("/raw/start", {"decim": 4})
        th0 = time.time()
        watch(HOLD_S, False)
        rstop = req("/raw/stop", {})
        raw_path = rstop.get("path") or rs.get("path") or ""
        if raw_path and not raw_path.endswith(".raw"):
            raw_path = raw_path + ".raw"
        note(f"KIGA {ki} hold done; RUN {YCYCLES} Y-cycles")
        r = req("/scan/run", {})
        frames_path = (r.get("frames") or {}).get("path")
        ts0 = time.time()
        time.sleep(4)
        if noise_ref is None:
            noise_ref = live_noise()
            log(f"live noise ref (KIGA {ki}) = {noise_ref}")
        f_line = 10.28
        scan_s = YCYCLES * 512 / f_line + 3
        watch(scan_s - 4, True, noise_ref=noise_ref, ki=ki)
        req("/scan/halt", {})
        ts1 = time.time()
        note(f"KIGA {ki} scan done")
        sc = score_scan(frames_path, ts0 + 2, ts1) if frames_path else {}
        try:
            rw = score_raw(raw_path, 25000.0) if raw_path and os.path.exists(raw_path) else {}
        except Exception as e:
            rw = {"error": str(e)}
        res = {"ki": ki, "scan": sc, "raw": rw}
        if results:
            b = results[0]
            ring_scan = (sc.get("ring_band_ratio") and b["scan"].get("ring_band_ratio")
                         and sc["ring_band_ratio"] > 3 * b["scan"]["ring_band_ratio"]
                         and (sc.get("ring_peak_sharp") or 0) > 5)
            ring_raw = (rw.get("band140_260") and b["raw"].get("band140_260")
                        and rw["band140_260"] > 3 * b["raw"]["band140_260"]
                        and (rw.get("peak_sharp") or 0) > 5)
            res["ringing"] = bool(ring_scan or ring_raw)
        else:
            res["ringing"] = False
        results.append(res)
        log("RESULT " + json.dumps(res))
        note(f"KIGA {ki} scored: {json.dumps(res)}")
        with open(LOG.replace(".log", "_results.json"), "w") as f:
            json.dump(results, f, indent=1)
        if res["ringing"]:
            log(f"ringing detected at KIGA {ki}; stopping ladder"); break
        last_clean = ki

    final = round((last_clean or RUNGS[0]) * 2 / 3, 3) if last_clean and last_clean > RUNGS[0] else RUNGS[0]
    req("/scan/settings", {**SET, "ki": final})
    note(f"ladder complete. last clean KIGA {last_clean}; set KIGA {final} (~2/3). Halted, CC engaged.")
    log(f"=== done: last_clean={last_clean} final={final} ===")


if __name__ == "__main__":
    try:
        main()
    except Abort as e:
        log(f"=== ABORTED: {e} ===")
        sys.exit(2)
