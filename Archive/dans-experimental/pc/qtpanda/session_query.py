"""session_query — answer "what was the full state at time T?" from a session.

Joins the two recorded artifacts on the firmware clock:
  * readings CSV  -> native per-sample fields (current, Z, bias, steps, flags)
  * journal JSONL -> reconstructed settings (scan window, setpoint, gains, dt)

Also provides the PC<->firmware clock fit (for sub-poll command alignment) and
timing-epoch segmentation (constant-rate spans).  Pure/Qt-free; runs in Docker
and feeds both the co-pilot (query_point) and offline post-processing.

    python session_query.py <journal.jsonl> --at <time_millis>
    python session_query.py <journal.jsonl> --clock-fit --epochs
"""
import argparse
import csv
import json
import os

import numpy as np

# 4-char command -> reconstructed setting name (settings not in the reading row).
CMD_PARAM = {
    "SETP": "setpoint", "SCSZ": "scan_size", "IPLN": "pixels",
    "XOFS": "x_offset", "YOFS": "y_offset", "LRAT": "line_rate_cHz",
    "SETD": "control_dt_us", "KPGA": "kp", "KIGA": "ki",
}
# Subset whose changes define constant-rate epochs for post-processing.
TIMING = {"SETD": "control_dt_us", "LRAT": "line_rate_cHz", "IPLN": "pixels"}
READING_FIELDS = ("time_millis", "current_A", "adc", "dac_z", "bias", "steps",
                  "is_scanning", "is_const_current", "is_approaching")


def _num(s):
    try:
        f = float(s)
        return int(f) if f.is_integer() else f
    except (TypeError, ValueError):
        return s


def load(journal_path, csv_path=None):
    """Return (journal_records, reading_rows).  Finds the linked CSV from the
    journal if not given, resolving it beside the journal if needed."""
    recs = [json.loads(ln) for ln in open(journal_path) if ln.strip()]
    if csv_path is None:
        for r in reversed(recs):
            d = r.get("data", {})
            p = d.get("path") or d.get("csv")
            if p and str(p).endswith(".csv"):
                csv_path = p
                break
    rows = []
    if csv_path:
        if not os.path.exists(csv_path):
            alt = os.path.join(os.path.dirname(os.path.abspath(journal_path)),
                               os.path.basename(csv_path))
            csv_path = alt if os.path.exists(alt) else csv_path
        if os.path.exists(csv_path):
            with open(csv_path, newline="") as f:
                rows = list(csv.DictReader(f))
    return recs, rows


def settings_at(recs, target_tm):
    """Reconstruct settings in effect at target_tm (last command <= tm wins)."""
    out = {}
    for r in recs:
        if (r["type"] == "command" and r.get("tm") is not None
                and r["tm"] <= target_tm):
            cmd = r["data"]["cmd"]
            key = cmd[:4]
            if key in CMD_PARAM:
                out[CMD_PARAM[key]] = _num(cmd[4:].strip())
    return out


def state_at(recs, rows, target_tm):
    """Full state at target_tm: nearest reading row + reconstructed settings."""
    out = {"query_tm": target_tm}
    if rows:
        best = min(rows, key=lambda r: abs(float(r["time_millis"]) - target_tm))
        out["reading"] = {k: _num(best.get(k)) for k in READING_FIELDS}
    out["settings"] = settings_at(recs, target_tm)
    return out


def clock_fit(recs):
    """Linear PC->firmware clock fit from records carrying both t and tm.
    Returns {a, b, rms_ms, n}: firmware_tm ~= a*pc_t + b."""
    pairs = [(r["t"], r["tm"]) for r in recs
             if r.get("tm") is not None and "t" in r]
    if len(pairs) < 2:
        return None
    t = np.array([p[0] for p in pairs], float)
    tm = np.array([p[1] for p in pairs], float)
    a, b = np.polyfit(t, tm, 1)
    rms = float(np.sqrt(np.mean((tm - (a * t + b)) ** 2)))
    return {"a": float(a), "b": float(b), "rms_ms": rms, "n": len(pairs)}


def epochs(recs):
    """Timing change-points (SETD/LRAT/IPLN) on the firmware clock — the
    boundaries that delimit constant-rate spans for post-processing."""
    changes = []
    active = {}
    for r in recs:
        if r["type"] == "command" and r.get("tm") is not None:
            key = r["data"]["cmd"][:4]
            if key in TIMING:
                val = _num(r["data"]["cmd"][4:].strip())
                if active.get(TIMING[key]) != val:
                    changes.append({"tm": r["tm"], "param": TIMING[key],
                                    "value": val})
                    active[TIMING[key]] = val
    return changes


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("journal")
    ap.add_argument("--csv", help="explicit readings CSV (else auto from journal)")
    ap.add_argument("--at", type=int, action="append", default=[],
                    help="time_millis to query full state at (repeatable)")
    ap.add_argument("--clock-fit", action="store_true")
    ap.add_argument("--epochs", action="store_true")
    args = ap.parse_args(argv)

    recs, rows = load(args.journal, args.csv)
    for tm in args.at:
        print(json.dumps(state_at(recs, rows, tm), indent=2))
    if args.clock_fit:
        print("clock_fit:", json.dumps(clock_fit(recs)))
    if args.epochs:
        print("epochs:", json.dumps(epochs(recs)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
