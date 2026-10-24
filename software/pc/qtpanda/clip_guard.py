"""clip_guard — sustained-clip protection while Z is fixed (roadmap F1).

Oct 22 2026: the tip crashed at 19:10:30 while parked at fixed Z with
feedback off.  Drift closed the gap and the current sat at the ADC clip
(32767, ~102 nA, near point contact) for 30 s before anyone acted, and the
19:12 scan then ran on the crashed junction.  With feedback off nothing in
the firmware reacts to clipping.

Rule: when the firmware loop does NOT own Z (CC off, not approaching) and
most of the last second of status samples sit at the clip, halt any scan
and step Z away from the sample.  Repeat once per second while still
clipped.  Only ever retracts (lower Z DAC = away), so it can never become
an approach.  With CC on the firmware loop handles clipping itself.
"""

CLIP_ADC = 32000        # |ADC| at or above this = clipped (full scale 32767)
WINDOW_MS = 1000        # judge the last second of status samples
MIN_SAMPLES = 20        # 200 Hz status -> ~200 per window; need some data
TRIP_FRACTION = 0.8     # Oct 22 crash: 23% -> 100% clipped within 30 s
DEFAULT_STEP = 2000     # Z DAC codes per retract step (Oct 22: clipped at
                        # 48,600, 2.9 nA at 35,012)


class ClipGuard:
    def __init__(self, step=DEFAULT_STEP, window_ms=WINDOW_MS,
                 trip_fraction=TRIP_FRACTION):
        self.step = step
        self.window_ms = window_ms
        self.trip_fraction = trip_fraction
        self._last_action_ms = None
        self.trips = 0

    def reset(self):
        self._last_action_ms = None

    def check(self, samples, is_const_current, is_approaching):
        """samples: iterable of (time_ms, adc), oldest first.

        Returns the signed Z-DAC change to apply now: 0 (no action) or
        -step (retract).  A trip also means "halt any running scan".
        Only samples taken after the previous action are judged, so each
        step is seen to take effect before the next one.
        """
        if is_const_current or is_approaching:
            self.reset()
            return 0
        s = list(samples)
        if not s:
            return 0
        now = s[-1][0]
        lo = now - self.window_ms
        if self._last_action_ms is not None:
            lo = max(lo, self._last_action_ms)
        recent = [a for (t, a) in s if t > lo]
        if len(recent) < MIN_SAMPLES:
            return 0
        clipped = sum(1 for a in recent if abs(a) >= CLIP_ADC)
        if clipped < self.trip_fraction * len(recent):
            return 0
        self._last_action_ms = now
        self.trips += 1
        return -self.step
