"""watchdogs — live-stream safety monitors for stability recording (Phase 5 v1).

Fed one sample at a time during a recording, each watchdog maintains a rolling
window and returns an alert dict (or None).  Pure/Qt-free, so they run in the
GUI, headless, or inside stab_runner, and are tested against synthetic streams.

  * SaturationWatchdog — ADC railed for too much of the recent window (contact).
  * EMIWatchdog        — bipolar zero-mean excursion bursts (bench interference).
  * SignalLossWatchdog — current fell back to the floor after engaging (drift-out).
"""
from collections import deque

import numpy as np

ADC_RAIL = 32767


class Watchdog:
    name = "base"

    def update(self, current_A, adc):
        return None

    def reset(self):
        pass


class SaturationWatchdog(Watchdog):
    """Trips when >= frac of the last `window` samples are ADC-railed."""
    name = "saturation"

    def __init__(self, window=20, frac=0.5):
        self._w = deque(maxlen=window)
        self.frac = frac
        self.tripped = False

    def update(self, current_A, adc):
        self._w.append(1 if adc >= ADC_RAIL else 0)
        railed = len(self._w) == self._w.maxlen and \
            sum(self._w) / len(self._w) >= self.frac
        if railed and not self.tripped:
            self.tripped = True
            return {"watchdog": self.name, "level": "critical",
                    "msg": f"ADC railed for >={self.frac:.0%} of last "
                           f"{self._w.maxlen} samples (tip in contact)"}
        if not railed:
            self.tripped = False
        return None


class EMIWatchdog(Watchdog):
    """Trips on bipolar, zero-mean excursion bursts beyond `sigmas` (robust)."""
    name = "emi"

    def __init__(self, window=60, sigmas=5.0, min_exc=5):
        self._w = deque(maxlen=window)
        self.sigmas = sigmas
        self.min_exc = min_exc

    def update(self, current_A, adc):
        self._w.append(current_A)
        if len(self._w) < self._w.maxlen:
            return None
        a = np.asarray(self._w)
        off = float(np.median(a))
        sig = float(np.median(np.abs(a - off))) * 1.4826 or float(a.std())
        if sig <= 0:
            return None
        exc = a[np.abs(a - off) > self.sigmas * sig]
        if (exc.size >= self.min_exc and (exc > off).any() and (exc < off).any()
                and abs(float(exc.mean()) - off) < 0.5 * float(exc.std())):
            return {"watchdog": self.name, "level": "warning",
                    "msg": f"{exc.size} bipolar excursions > {self.sigmas:.0f} "
                           f"sigma in last {self._w.maxlen} (EMI/bench activity)"}
        return None


class SignalLossWatchdog(Watchdog):
    """Trips when the rolling mean falls back to the floor after engaging."""
    name = "signal_loss"

    def __init__(self, engage_A, floor_A, window=10):
        self.engage_A = engage_A
        self.floor_A = floor_A
        self._w = deque(maxlen=window)
        self._engaged = False

    def update(self, current_A, adc):
        self._w.append(abs(current_A))
        m = sum(self._w) / len(self._w)
        if m >= self.engage_A:
            self._engaged = True
        elif self._engaged and m <= self.floor_A:
            self._engaged = False
            return {"watchdog": self.name, "level": "warning",
                    "msg": "current dropped to the floor after engaging "
                           "(tip drifted out / lost tunneling)"}
        return None


class WatchdogSet:
    """Fan a sample out to several watchdogs; collect any alerts."""

    def __init__(self, watchdogs):
        self.watchdogs = list(watchdogs)

    def update(self, current_A, adc):
        alerts = []
        for w in self.watchdogs:
            a = w.update(current_A, adc)
            if a:
                alerts.append(a)
        return alerts
