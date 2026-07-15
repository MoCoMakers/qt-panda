"""End-to-end demo: an instructed sequence run through the broker/journal
against the physics emulator, producing a stability histogram PNG.

Emulates the exact ask "approach N steps, then take M stability samples":
  * command issued via DataBroker.send  -> real serial round-trip + journaled
  * samples polled via GSTS             -> parsed current, like the Stability tab
  * histogram rendered via render_screens (Tier-1 capture)  -> PNG to audit
  * session graded via stab_runner and noted on the journal

Uses the mockup physics emulator (stm_emulator.Emulator: real electronics noise
+ exponential-gap tunneling), so the histogram reflects a real signal model, not
a stub.  Run in the qtpanda-gui image with the emulator dir mounted at /emu.
"""
import argparse
import csv
import os
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("STM_MODE", "tunnel")
os.environ.setdefault("STM_SETPOINT_PA", "300")

sys.path.insert(0, "/emu")          # mounted mockup emulator dir

import numpy as np
import stm_emulator
from PySide6 import QtWidgets

import data_broker
import render_screens
import session_journal
import stab_runner

COUNTS_PER_AMP = stm_emulator.COUNTS_PER_AMP


class _Sock:
    def __init__(self):
        self.buf = bytearray()

    def sendall(self, b):
        self.buf.extend(b)


class PhysicsSerial:
    """pyserial-like adapter over the physics Emulator (real command round-trip)."""

    def __init__(self):
        self.emu = stm_emulator.Emulator()
        self._sock = _Sock()
        self._in = bytearray()
        self.timeout = 1
        self.is_open = True

    def write(self, data):
        line = data.decode("ascii", "replace").strip()
        cmd, rest = line[:4].strip(), line[4:].strip()
        iargs = []                       # emulator.handle expects parsed ints
        for tok in rest.split():
            try:
                iargs.append(int(float(tok)))
            except ValueError:
                pass
        self.emu.handle(cmd, iargs, self._sock)
        self._in.extend(self._sock.buf)
        self._sock.buf.clear()
        return len(data)

    def readline(self):
        nl = self._in.find(b"\n")
        if nl < 0:
            out = bytes(self._in)
            self._in.clear()
            return out
        out = bytes(self._in[:nl + 1])
        del self._in[:nl + 1]
        return out

    def read(self, n=1):
        chunk = bytes(self._in[:n])
        del self._in[:n]
        return chunk

    def cancel_read(self):
        pass

    @property
    def in_waiting(self):
        return len(self._in)

    def close(self):
        self.is_open = False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=5)
    ap.add_argument("--samples", type=int, default=100)
    ap.add_argument("--seconds", type=float, default=0.0,
                    help="if >0, poll for this many seconds at --rate Hz")
    ap.add_argument("--rate", type=float, default=9.0,
                    help="GSTS poll rate (Hz) for timed runs (~bench cadence)")
    ap.add_argument("--out", default="/out/demo")
    args = ap.parse_args()

    ser = PhysicsSerial()
    broker = data_broker.DataBroker(ser)
    out_dir = os.path.dirname(args.out) or "."
    os.makedirs(out_dir, exist_ok=True)
    session_journal.start(log_dir=out_dir, demo="approach+stability")

    # 1) "approach N steps" — through the single journaled writer.
    broker.send(f"MTMV {args.steps}", src="agent")
    session_journal.note(f"approached {args.steps} steps", src="agent")

    # 2) "stability samples" — poll GSTS, parse current like the tab.  A timed
    # run (--seconds) polls at ~bench cadence so the trace spans real seconds.
    times_ms, adcs, currents = [], [], []

    def poll_once():
        broker.send("GSTS", src="agent")          # poll (filtered from journal)
        parts = ser.readline().decode("ascii", "replace").strip().split(",")
        if len(parts) >= 10:
            adcs.append(int(parts[4]))
            times_ms.append(int(parts[9]))
            currents.append(int(parts[4]) / COUNTS_PER_AMP)

    if args.seconds > 0:
        period = 1.0 / max(args.rate, 0.1)
        t_end = time.monotonic() + args.seconds
        while time.monotonic() < t_end:
            poll_once()
            time.sleep(period)
    else:
        for _ in range(args.samples):
            poll_once()

    # Write a Stability CSV (widget format) so the same grader/renderer apply.
    csv_path = f"{args.out}_stability_1000000000000.csv"
    t0 = times_ms[0] if times_ms else 0
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["elapsed_s", "time_millis", "adc", "current_A", "dac_z",
                    "bias", "steps", "is_scanning", "is_const_current",
                    "is_approaching"])
        for tm, adc, cur in zip(times_ms, adcs, currents):
            w.writerow([f"{(tm - t0) / 1000:.3f}", tm, adc, f"{cur:.6e}",
                        32768, 32768, args.steps, 0, 0, 0])
    session_journal.record("stab_samples", path=csv_path)

    # 3) Render the histogram PNG (Tier-1 capture) + grade the session.
    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    render_screens.render_histogram(np.asarray(currents, float), args.out)
    render_screens.render_timeseries(np.asarray(times_ms, float),
                                     np.asarray(currents, float), args.out)
    verdict = stab_runner.analyze(csv_path)
    session_journal.note(f"verdict={verdict['verdict']}", src="agent")
    session_journal.stop()

    span_s = (times_ms[-1] - times_ms[0]) / 1000.0 if len(times_ms) > 1 else 0.0
    mean_pa = float(np.mean(currents)) * 1e12 if currents else 0.0
    print(f"approached {args.steps} steps; {len(currents)} samples over "
          f"{span_s:.1f}s; mean={mean_pa:.1f} pA; verdict={verdict['verdict']}")
    print("current-trace PNG:", args.out + "_current.png")
    print("histogram PNG:", args.out + "_hist.png")


if __name__ == "__main__":
    main()
