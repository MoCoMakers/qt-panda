"""status_logger — true-time status CSV writer on its own thread.

Samples travel serial-reader thread -> thread-safe queue -> dedicated writer
thread.  The GUI main thread is never in the data path, so rendering,
histogram math, or even a hung event loop cannot stall or lose the record
(operator requirement 2026-07-14: logging is high-speed and separate from
any data processing/interpretation the GUI does).

Row format matches the historical stability CSV so every existing consumer
(stab_runner, stab_metrics, archive tooling) keeps working unchanged.
"""
import csv
import os
import queue
import threading

HEADER = [
    "elapsed_s", "time_millis", "adc", "current_A",
    "dac_z", "bias", "steps",
    "is_scanning", "is_const_current", "is_approaching",
]

# Status-frame flag bits (same encoding as binary_frame.hpp 'S' frames).
FLAG_APPROACHING = 0x01
FLAG_CONST_CURRENT = 0x02
FLAG_SCANNING = 0x04


def pack_flags(is_approaching, is_const_current, is_scanning):
    return ((FLAG_APPROACHING if is_approaching else 0)
            | (FLAG_CONST_CURRENT if is_const_current else 0)
            | (FLAG_SCANNING if is_scanning else 0))


class StatusLogger:
    """Queue-fed CSV writer.  ``put()`` is safe from any thread and never
    blocks the caller; a daemon thread drains to disk and flushes whenever
    the queue empties (so an unclean shutdown keeps the data)."""

    def __init__(self, amp_of_adc):
        self._amp = amp_of_adc          # adc counts -> amps converter
        self._q = None
        self._thread = None
        self.path = None
        self.n_rows = 0

    def is_active(self):
        return self._thread is not None and self._thread.is_alive()

    def start(self, path):
        self.stop()
        parent = os.path.dirname(os.path.abspath(path))
        os.makedirs(parent, exist_ok=True)
        self.path = path
        self.n_rows = 0
        self._q = queue.Queue()
        self._thread = threading.Thread(
            target=self._run, args=(path, self._q),
            name="StatusLogger", daemon=True)
        self._thread.start()
        return path

    def put(self, tm, adc, dac_z, bias, steps, flags):
        """Enqueue one sample.  Callable from any thread; no-op when the
        logger is not running."""
        q = self._q
        if q is not None:
            q.put((tm, adc, dac_z, bias, steps, flags))

    def stop(self):
        q, t = self._q, self._thread
        self._q = None
        self._thread = None
        if q is not None:
            q.put(None)                  # sentinel: drain then exit
        if t is not None:
            t.join(2.0)

    # -- writer thread ------------------------------------------------------
    def _run(self, path, q):
        t0 = None
        try:
            f = open(path, "w", newline="")
        except Exception as e:
            print(f"[REC] WARNING: could not open status log {path}: {e}")
            return
        with f:
            w = csv.writer(f)
            w.writerow(HEADER)
            f.flush()
            while True:
                item = q.get()
                if item is None:
                    break
                tm, adc, dac_z, bias, steps, flags = item
                if t0 is None:
                    t0 = tm
                try:
                    w.writerow([
                        f"{(tm - t0) / 1000.0:.3f}", tm, adc,
                        f"{self._amp(adc):.6e}", dac_z, bias, steps,
                        int(bool(flags & FLAG_SCANNING)),
                        int(bool(flags & FLAG_CONST_CURRENT)),
                        int(bool(flags & FLAG_APPROACHING)),
                    ])
                    self.n_rows += 1
                    if q.empty():
                        f.flush()
                except Exception as e:
                    print(f"[REC] WARNING: status log write failed: {e}")
