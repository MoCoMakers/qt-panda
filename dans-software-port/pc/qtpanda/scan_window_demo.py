"""Demo: recover the scan-window (size/offset/pixels/rate) at a reading's time.

Scan-window params are NOT in the per-sample GSTS row; they're set by commands
(SCSZ/XOFS/YOFS/IPLN/LRAT).  Because every command is journaled with its firmware
time_millis, the window in effect at any reading is reconstructed from the log:
find the latest scan-param command at-or-before that reading's tm.
"""
import argparse
import json
import os
import sys
import time

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.setdefault("STM_MODE", "tunnel")
sys.path.insert(0, "/emu")

import numpy as np

import data_broker
import session_journal
from copilot_demo import PhysicsSerial, COUNTS_PER_AMP  # noqa: F401

SCAN_CMDS = {"SCSZ": "scan_size", "IPLN": "pixels",
             "XOFS": "x_offset", "YOFS": "y_offset", "LRAT": "line_rate_cHz"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/out/scanwin")
    ap.add_argument("--rate", type=float, default=9.0)
    args = ap.parse_args()
    period = 1.0 / max(args.rate, 0.1)

    ser = PhysicsSerial()
    broker = data_broker.DataBroker(ser)
    out_dir = os.path.dirname(args.out) or "."
    os.makedirs(out_dir, exist_ok=True)
    jpath = session_journal.start(log_dir=out_dir, demo="scan_window")

    T = []

    def poll():
        broker.send("GSTS", src="agent")
        p = ser.readline().decode("ascii", "replace").strip().split(",")
        if len(p) >= 10:
            session_journal.mark_time(int(p[9]))
            T.append(int(p[9]))

    def poll_for(seconds):
        t_end = time.monotonic() + seconds
        while time.monotonic() < t_end:
            poll()
            time.sleep(period)

    poll_for(1.0)                                    # baseline: establish fw clock

    for c in ("SCSZ 12000", "IPLN 256", "XOFS 1000", "YOFS -500", "LRAT 100"):
        broker.send(c, src="agent")                  # scan window A
    session_journal.note("scan window A (size 12000, off 1000,-500, 256px, 1Hz)",
                         src="agent")
    poll_for(2.0)

    for c in ("SCSZ 6000", "XOFS 0", "YOFS 0"):
        broker.send(c, src="agent")                  # scan window B (zoom in, centre)
    session_journal.note("scan window B (size 6000, centred)", src="agent")
    poll_for(2.0)

    session_journal.stop()

    # ---- reconstruct the window at chosen reading times, from the journal ----
    recs = [json.loads(ln) for ln in open(jpath) if ln.strip()]

    def window_at(target_tm):
        win = {}
        for r in recs:
            if (r["type"] == "command" and r.get("tm") is not None
                    and r["tm"] <= target_tm):
                cmd = r["data"]["cmd"]
                key = cmd[:4]
                if key in SCAN_CMDS:
                    try:
                        win[SCAN_CMDS[key]] = int(cmd[4:].strip())
                    except ValueError:
                        pass
        return win

    T = np.asarray(T)
    rel = (T - T.max()) / 1000.0
    print(f"{T.size} readings; scan window recovered from the journal:")
    for target in (-3.0, -0.4):
        i = int(np.argmin(np.abs(rel - target)))
        tm = int(T[i])
        print(f"  reading @ t={rel[i]:+.2f}s (time_millis={tm}): "
              f"window = {window_at(tm) or '(none set yet)'}")


if __name__ == "__main__":
    main()
