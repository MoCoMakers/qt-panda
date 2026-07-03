#!/usr/bin/env python3
"""Headless PC-side driver for the software mockup.

Uses the REAL ``stm_control.STM`` (mounted from ``pc/qtpanda``) to talk to the
Arduino emulator over the bridged serial port, then runs the SAME
``stab_metrics`` math the Stability tab uses. This proves the whole stack —
protocol, streaming, raw CSV logging, and the live drift/jitter estimate —
without needing a display or Qt.

Env:
  STM_SERIAL_PORT   serial device to open (default /tmp/stm_pty from socat)
  RUN_SECONDS       how long to stream           (default 30)
  POLL_HZ           status polls per second       (default 20)
  OUT_CSV           raw-log output path           (default /out/mockup_stability.csv)
"""

import csv
import os
import sys
import time

# pc/qtpanda is mounted here and put on sys.path by the entrypoint.
import stm_control
import stab_metrics


def main():
    port = os.environ.get("STM_SERIAL_PORT", "/tmp/stm_pty")
    run_seconds = float(os.environ.get("RUN_SECONDS", "30"))
    poll_hz = float(os.environ.get("POLL_HZ", "20"))
    out_csv = os.environ.get("OUT_CSV", "/out/mockup_stability.csv")
    period = 1.0 / poll_hz if poll_hz > 0 else 0.05

    print(f"[driver] opening {port} …", flush=True)
    stm = stm_control.STM()
    for attempt in range(40):
        try:
            stm.open(port)
            break
        except Exception as e:
            print(f"[driver] waiting for serial ({attempt}): {e}", flush=True)
            time.sleep(0.5)
    else:
        print("[driver] ERROR: could not open serial port", flush=True)
        return 1

    times_ms, amps = [], []
    pm_per_ln = stab_metrics.pm_per_ln(4.0)

    os.makedirs(os.path.dirname(out_csv) or ".", exist_ok=True)
    with open(out_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["elapsed_s", "time_millis", "adc", "current_A",
                    "dac_z", "bias", "is_scanning", "is_const_current"])
        t_end = time.time() + run_seconds
        last = None
        while time.time() < t_end:
            st = stm.get_status()
            if st is not None and st.time_millis != last:
                last = st.time_millis
                amp = stm_control.STM_Status.adc_to_amp(st.adc)
                times_ms.append(st.time_millis)
                amps.append(amp)
                w.writerow([f"{st.time_millis/1000.0:.3f}", st.time_millis,
                            st.adc, f"{amp:.6e}", st.dac_z, st.bias,
                            int(st.is_scanning), int(st.is_const_current)])
            time.sleep(period)

    n = len(amps)
    print(f"[driver] collected {n} samples -> {out_csv}", flush=True)
    if n:
        import numpy as np
        a = np.abs(np.asarray(amps))
        print(f"[driver] mean={np.mean(amps):.3e} A  std={np.std(amps):.3e} A", flush=True)
        m = stab_metrics.drift_metrics(times_ms, amps, pm_per_ln)
        if m:
            print("[driver] DRIFT READOUT (same math as the GUI):", flush=True)
            print(f"           v_z      = {m['vz_pm_s']:+.2f} pm/s  (R2={m['r2']:.2f})", flush=True)
            print(f"           jitter   = {m['jitter_pm']:.1f} pm  (sigma_z)", flush=True)
            print(f"           skew(lnI)= {m['skew']:+.2f}", flush=True)
            print(f"           usable n = {m['n']}  over {m['span_s']:.1f} s", flush=True)
        else:
            print("[driver] not enough in-tunneling data for a drift estimate", flush=True)
    print("[driver] done.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
