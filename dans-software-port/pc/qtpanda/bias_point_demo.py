"""Demo: retrieve the bias reading at any point on the red current trace.

Every GSTS sample records the full state (current AND bias) at one time_millis,
so a point in the current-vs-time trace maps to its exact bias.  Here we change
the bias mid-capture, then read the bias back at chosen points on the trace.

(The physics emulator doesn't couple bias -> current, so current stays put while
bias steps; real hardware would move the current. The point is the recorded
per-sample correspondence.)
"""
import argparse
import os
import sys
import time

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.setdefault("STM_MODE", "tunnel")
os.environ.setdefault("STM_SETPOINT_PA", "400")
sys.path.insert(0, "/emu")

import numpy as np
from PySide6 import QtWidgets

import data_broker
import render_screens
import session_journal
from copilot_demo import PhysicsSerial, COUNTS_PER_AMP


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/out/bias_point")
    ap.add_argument("--rate", type=float, default=9.0)
    args = ap.parse_args()
    period = 1.0 / max(args.rate, 0.1)

    ser = PhysicsSerial()
    broker = data_broker.DataBroker(ser)
    out_dir = os.path.dirname(args.out) or "."
    os.makedirs(out_dir, exist_ok=True)
    session_journal.start(log_dir=out_dir, demo="bias_point")

    T, C, B = [], [], []

    def poll():
        broker.send("GSTS", src="agent")
        p = ser.readline().decode("ascii", "replace").strip().split(",")
        if len(p) >= 10:
            bias, adc, tm = int(p[0]), int(p[4]), int(p[9])
            session_journal.mark_time(tm)
            T.append(tm)
            C.append(adc / COUNTS_PER_AMP)
            B.append(bias)

    def poll_for(seconds):
        t_end = time.monotonic() + seconds
        while time.monotonic() < t_end:
            poll()
            time.sleep(period)

    broker.send("BIAS 40000", src="agent")
    session_journal.note("bias set to 40000", src="agent")
    poll_for(3.0)

    broker.send("BIAS 20000", src="agent")
    session_journal.note("bias changed -> 20000", src="agent")
    poll_for(3.0)

    session_journal.stop()

    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    render_screens.render_timeseries(np.asarray(T, float),
                                     np.asarray(C, float), args.out)

    # Read the bias back at chosen points on the trace (x = s relative to now).
    T = np.asarray(T, float)
    rel = (T - T.max()) / 1000.0
    print(f"{len(T)} samples; querying bias at points on the trace:")
    for target in (-4.0, -1.0):
        i = int(np.argmin(np.abs(rel - target)))
        print(f"  point @ t={rel[i]:+.2f}s : current={C[i] * 1e12:7.1f} pA "
              f"| bias={B[i]}  (time_millis={int(T[i])})")
    print("trace PNG:", args.out + "_current.png")


if __name__ == "__main__":
    main()
