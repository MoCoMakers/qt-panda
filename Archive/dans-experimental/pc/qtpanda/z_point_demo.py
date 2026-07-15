"""Demo: the Z-piezo position (dac_z) at the time of a reading.

Unlike scan-window params, Z IS a native per-sample status field, so every
reading row carries its dac_z at the same time_millis as the current.  Here we
drive an approach (ramp Z to close the gap) and read Z back at the baseline,
tunneling, and contact points of the trace -- showing Z drives the current.
"""
import os
import sys
import time

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.setdefault("STM_MODE", "tunnel")
os.environ.setdefault("STM_SETPOINT_PA", "500")
os.environ.setdefault("STM_JITTER_PM", "8")
sys.path.insert(0, "/emu")

import numpy as np

import data_broker
import session_journal
from copilot_demo import PhysicsSerial, COUNTS_PER_AMP


def main():
    ser = PhysicsSerial()
    broker = data_broker.DataBroker(ser)
    session_journal.start(log_dir="/out/harness-screens", demo="z_point")
    period = 1.0 / 9.0
    T, C, Z = [], [], []

    def poll():
        broker.send("GSTS", src="agent")
        p = ser.readline().decode("ascii", "replace").strip().split(",")
        if len(p) >= 10:
            z, adc, tm = int(p[1]), int(p[4]), int(p[9])   # p[1] = dac_z
            session_journal.mark_time(tm)
            T.append(tm)
            C.append(adc / COUNTS_PER_AMP)
            Z.append(z)

    def poll_for(seconds):
        t_end = time.monotonic() + seconds
        while time.monotonic() < t_end:
            poll()
            time.sleep(period)

    broker.send("DACZ 41000", src="agent")             # tip retracted
    poll_for(2.0)
    for dacz in range(40000, 31500, -400):             # approach: close the gap
        broker.send(f"DACZ {dacz}", src="agent")
        poll()
        time.sleep(period)
    poll_for(2.0)                                       # contact hold
    session_journal.stop()

    T, C, Z = np.asarray(T), np.asarray(C), np.asarray(Z)
    rel = (T - T.max()) / 1000.0

    def report(label, i):
        print(f"  {label:9s} @ t={rel[i]:+.2f}s (time_millis={int(T[i])}): "
              f"current={C[i] * 1e12:9.1f} pA | Z(dac_z)={int(Z[i])}")

    print(f"{T.size} readings; Z read directly from each reading row:")
    report("baseline", int(np.argmin(np.abs(C[:15]))))                    # near-zero
    tun = np.where((np.abs(C) >= 1e-10) & (np.abs(C) <= 5e-8))[0]
    if tun.size:
        report("tunneling", int(tun[0]))
    contact = np.where(C >= 1e-7)[0]
    if contact.size:
        report("contact", int(contact[0]))


if __name__ == "__main__":
    main()
