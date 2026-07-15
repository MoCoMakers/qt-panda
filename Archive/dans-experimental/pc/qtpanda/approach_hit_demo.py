"""Approach-to-hit demo: baseline noise -> tunneling -> tip contact, captured.

Runs ~10 s: a few seconds with the tip retracted (baseline ~+/-50 pA at the
10^-12 floor), then an approach that closes the fine-Z gap step by step, so the
current climbs exponentially through the tunneling regime (10^-10..10^-9 A) and
rails on contact (the 'hit').  Renders the Main-tab current trace so the hit is
visible as the sharp rise, and grades/journals the session.

Uses the physics emulator (exponential-gap model), driven through the broker/
journal.  Run in qtpanda-gui with the emulator dir at /emu.
"""
import argparse
import os
import sys
import time

# Set the signal model BEFORE importing copilot_demo (its setdefault won't
# override these), so the emulator uses our approach-friendly parameters.
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["STM_MODE"] = "tunnel"          # gap set by DACZ; no drift term
os.environ["STM_SETPOINT_PA"] = "500"      # tunneling current at zero gap
os.environ["STM_JITTER_PM"] = "8"          # low jitter -> clean transition
sys.path.insert(0, "/emu")

import numpy as np
from PySide6 import QtWidgets

import data_broker
import render_screens
import session_journal
import stab_runner
from copilot_demo import PhysicsSerial, COUNTS_PER_AMP


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/out/approach_hit")
    ap.add_argument("--rate", type=float, default=9.0)
    args = ap.parse_args()
    period = 1.0 / max(args.rate, 0.1)

    ser = PhysicsSerial()
    broker = data_broker.DataBroker(ser)
    out_dir = os.path.dirname(args.out) or "."
    os.makedirs(out_dir, exist_ok=True)
    session_journal.start(log_dir=out_dir, demo="approach_hit")

    times_ms, adcs, currents = [], [], []

    def poll():
        broker.send("GSTS", src="agent")
        parts = ser.readline().decode("ascii", "replace").strip().split(",")
        if len(parts) >= 10:
            adcs.append(int(parts[4]))
            times_ms.append(int(parts[9]))
            currents.append(int(parts[4]) / COUNTS_PER_AMP)
            session_journal.mark_time(int(parts[9]))   # anchor cmds to fw clock

    def poll_for(seconds):
        t_end = time.monotonic() + seconds
        while time.monotonic() < t_end:
            poll()
            time.sleep(period)

    # 1) Tip retracted: fine-Z far out -> only the electronics floor.
    broker.send("DACZ 41000", src="agent")
    session_journal.note("baseline: tip retracted (~+/-50 pA floor)", src="agent")
    poll_for(3.0)

    # 2) Approach: coarse step, then close the gap in fine-Z increments.  As the
    #    gap shrinks the current climbs exponentially -> tunneling -> contact.
    broker.send("MTMV 5", src="agent")
    session_journal.note("approaching: closing gap (watch for the hit)", src="agent")
    for dacz in range(40000, 31500, -400):
        broker.send(f"DACZ {dacz}", src="agent")
        poll()
        time.sleep(period)

    # 3) Hold on contact and keep reading.
    session_journal.note("post-hit readings (tip in contact)", src="agent")
    poll_for(3.0)

    # Save CSV + render the Main-tab current trace (the 'hit' is the rise).
    csv_path = f"{args.out}_stability_1000000000000.csv"
    t0 = times_ms[0] if times_ms else 0
    with open(csv_path, "w", newline="") as f:
        import csv as _csv
        w = _csv.writer(f)
        w.writerow(["elapsed_s", "time_millis", "adc", "current_A", "dac_z",
                    "bias", "steps", "is_scanning", "is_const_current",
                    "is_approaching"])
        for tm, adc, cur in zip(times_ms, adcs, currents):
            w.writerow([f"{(tm - t0) / 1000:.3f}", tm, adc, f"{cur:.6e}",
                        0, 32768, 5, 0, 0, 1])
    session_journal.record("approach_hit_samples", path=csv_path)

    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    tms = np.asarray(times_ms, float)
    cur = np.asarray(currents, float)
    render_screens.render_timeseries(tms, cur, args.out)                    # linear
    render_screens.render_timeseries(tms, cur, args.out, logy=True,
                                     suffix="_current_log")                 # log decades
    verdict = stab_runner.analyze(csv_path)
    session_journal.note(f"verdict={verdict['verdict']}", src="agent")
    session_journal.stop()

    peak_na = max(currents) * 1e9 if currents else 0.0
    floor_pa = float(np.median(currents[:20])) * 1e12 if len(currents) > 20 else 0.0
    span = (times_ms[-1] - times_ms[0]) / 1000.0 if len(times_ms) > 1 else 0.0
    print(f"{len(currents)} samples over {span:.1f}s; baseline~{floor_pa:.0f} pA "
          f"-> peak {peak_na:.1f} nA (hit); verdict={verdict['verdict']}")
    print("current-trace PNG:", args.out + "_current.png")


if __name__ == "__main__":
    main()
