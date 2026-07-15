"""procedure_runner — headless guarded approach + record (Phase 5+6 integration).

Ties the offline cores together into one supervised procedure against the
emulator, the stand-in for the live co-pilot loop:

  baseline -> estimate floor -> guarded approach (ApproachFSM: coarse steps far
  out, single steps near the window, ENGAGE in-window, HARD RETRACT on rail;
  watchdogs run every sample) -> record the hold -> grade + capture -> journal.

No hardware: DACZ closes the gap in the emulator's exponential-gap model, so the
whole safety loop is exercised deterministically.  Every decision is journaled.
"""
import argparse
import csv
import os
import sys
import time

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.setdefault("STM_MODE", "tunnel")
os.environ.setdefault("STM_SETPOINT_PA", "1000")
os.environ.setdefault("STM_JITTER_PM", "5")
sys.path.insert(0, "/emu")

import numpy as np

import data_broker
import render_screens
import session_journal
import stab_runner
import watchdogs as wd
from approach_fsm import ApproachFSM
from copilot_demo import PhysicsSerial, COUNTS_PER_AMP


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/out/procedure")
    ap.add_argument("--rate", type=float, default=9.0)
    args = ap.parse_args()
    period = 1.0 / max(args.rate, 0.1)

    ser = PhysicsSerial()
    broker = data_broker.DataBroker(ser)
    out_dir = os.path.dirname(args.out) or "."
    os.makedirs(out_dir, exist_ok=True)
    session_journal.start(log_dir=out_dir, demo="guarded_procedure")

    T, C, Z, B = [], [], [], []

    def poll():
        broker.send("GSTS", src="agent")
        p = ser.readline().decode("ascii", "replace").strip().split(",")
        if len(p) < 10:
            return None
        z, adc, tm, bias = int(p[1]), int(p[4]), int(p[9]), int(p[0])
        cur = adc / COUNTS_PER_AMP
        session_journal.mark_time(tm)
        session_journal.log_sample({"current_A": cur, "adc": adc, "dac_z": z,
                                    "bias": bias}, tm=tm)          # inline sample (J1)
        T.append(tm); C.append(cur); Z.append(z); B.append(bias)
        return adc, cur

    # 1) Baseline -> robust floor estimate.
    broker.send("DACZ 41000", src="agent")
    session_journal.note("baseline: tip retracted", src="agent")
    base = []
    t_end = time.monotonic() + 2.0
    while time.monotonic() < t_end:
        r = poll()
        if r:
            base.append(r[1])
        time.sleep(period)
    base = np.asarray(base)
    offset = float(np.median(base))
    sigma = float(np.median(np.abs(base - offset))) * 1.4826 or float(base.std())
    session_journal.snapshot("baseline", {"offset_pA": offset * 1e12,
                                          "sigma_pA": sigma * 1e12}, src="auto")

    # 2) Guarded approach.
    fsm = ApproachFSM(offset, sigma)
    guards = wd.WatchdogSet([
        wd.SaturationWatchdog(window=6, frac=0.5),
        wd.EMIWatchdog(window=40, sigmas=6.0, min_exc=4),
    ])
    dac_z = 41000
    outcome = "no_engage"
    for _ in range(400):
        r = poll()
        time.sleep(period)
        if not r:
            continue
        adc, cur = r
        for a in guards.update(cur, adc):
            session_journal.note(f"WATCHDOG {a['watchdog']}: {a['msg']}", src="auto")
        action = fsm.update(cur, adc)
        if action == "engage":
            broker.send("ENGA", src="agent")
            session_journal.note(f"ENGAGE at dac_z={dac_z} "
                                 f"(dev>={fsm.engage_sigmas:.0f}sigma)", src="agent")
            outcome = "engaged"
            break
        if action == "retract":
            broker.send("DACZ 45000", src="agent")
            session_journal.note("HARD RETRACT (rail/contact) — aborting", src="agent")
            outcome = "retracted"
            break
        step = 100 if action == "step_in_single" else 300   # interlock near window
        dac_z = max(dac_z - step, 30000)
        broker.send(f"DACZ {dac_z}", src="agent")
        if dac_z <= 30000:
            session_journal.note("reached Z travel limit without engaging", src="agent")
            break

    # 3) Record the hold (if engaged).
    if outcome == "engaged":
        session_journal.note("recording hold", src="agent")
        t_end = time.monotonic() + 3.0
        while time.monotonic() < t_end:
            poll()
            time.sleep(period)

    # 4) Save CSV, grade, capture, journal.
    csv_path = f"{args.out}_stability_1000000000000.csv"
    t0 = T[0] if T else 0
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["elapsed_s", "time_millis", "adc", "current_A", "dac_z",
                    "bias", "steps", "is_scanning", "is_const_current",
                    "is_approaching"])
        for tm, cur, z, bias in zip(T, C, Z, B):
            adc = int(round(cur * COUNTS_PER_AMP))
            w.writerow([f"{(tm - t0) / 1000:.3f}", tm, adc, f"{cur:.6e}",
                        z, bias, 0, 0, int(outcome == "engaged"), 1])
    session_journal.record("procedure_samples", path=csv_path)

    from PySide6 import QtWidgets
    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    render_screens.render_timeseries(np.asarray(T, float), np.asarray(C, float),
                                     args.out, logy=True, suffix="_current_log")
    verdict = stab_runner.analyze(csv_path)
    session_journal.note(f"outcome={outcome}; verdict={verdict['verdict']}", src="agent")
    session_journal.stop()

    print(f"outcome={outcome}; {len(T)} samples; "
          f"floor sigma={sigma * 1e12:.0f} pA; verdict={verdict['verdict']}")
    print("trace:", args.out + "_current_log.png")


if __name__ == "__main__":
    main()
