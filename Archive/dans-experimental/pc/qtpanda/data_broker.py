"""data_broker — single-owner serial hub with pub/sub + journaling (Phase 4).

FIRST-SHOT / ADDITIVE: this is the core of the non-blocking-view architecture.
It does **not** yet replace the existing STM/reader wiring — swapping the tabs
over to subscriptions and retiring ``get_status``'s synchronous ``readline`` is
the GUI-interactive step (done against the EMU emulator with the live app).
What lands here is the port-owning hub whose logic is unit-testable offline:

  * **one place that writes commands** (``send``) -> journaled at the choke
    point, so no view issues a wire action that escapes the log;
  * **topic pub/sub with bounded, drop-oldest delivery** so a slow or hidden
    subscriber can never stall the broker or the other views (the tab-freeze
    root cause);
  * the reader thread feeding topics (``line`` / ``lockin`` / ``ascii``).

Qt is imported lazily (inside ``start``) so the pub/sub + command core imports
and tests without PySide6.
"""
from collections import defaultdict, deque
import threading

import session_journal


class Subscription:
    """A bounded, drop-oldest queue for one subscriber of one topic.

    ``latest_only`` keeps just the newest item (gauges/status, where stale
    intermediate values are worthless).  Otherwise up to ``maxlen`` items are
    buffered and the oldest is dropped when full — delivery never blocks the
    publisher, and dropped items are counted (so truncation is never silent)."""

    def __init__(self, topic, maxlen=256, latest_only=False):
        self.topic = topic
        self.latest_only = latest_only
        self._q = deque(maxlen=1 if latest_only else maxlen)
        self.dropped = 0

    def _offer(self, item):
        if not self.latest_only and len(self._q) == self._q.maxlen:
            self.dropped += 1                 # oldest is about to fall off
        self._q.append(item)                  # deque(maxlen) auto-drops oldest

    def poll(self):
        """Drain and return all buffered items, oldest first."""
        items = list(self._q)
        self._q.clear()
        return items

    def latest(self):
        return self._q[-1] if self._q else None

    def __len__(self):
        return len(self._q)


class DataBroker:
    """Owns the serial port; publishes parsed frames to topic subscribers and
    serializes all outbound commands through one journaled choke point."""

    def __init__(self, serial_port, journal=session_journal):
        self._serial = serial_port
        self._journal = journal
        self._subs = defaultdict(list)
        self._write_lock = threading.Lock()
        self._reader = None

    # --- pub/sub ---------------------------------------------------------
    def subscribe(self, topic, maxlen=256, latest_only=False):
        sub = Subscription(topic, maxlen, latest_only)
        self._subs[topic].append(sub)
        return sub

    def unsubscribe(self, sub):
        try:
            self._subs.get(sub.topic, []).remove(sub)
        except ValueError:
            pass

    def publish(self, topic, item):
        # Never blocks on a slow subscriber: each just buffers (drop-oldest).
        for sub in self._subs.get(topic, ()):
            sub._offer(item)

    # --- commands (single choke point) -----------------------------------
    def send(self, cmd, src="human"):
        data = cmd.encode() if isinstance(cmd, str) else cmd
        with self._write_lock:
            self._serial.write(data)
        # Journal every command except the ~9 Hz GSTS poll (its reply is a
        # 'sample'); no-op when no session is active.
        if not str(cmd).strip().upper().startswith("GSTS"):
            self._journal.log_command(cmd, src=src)

    # --- reader lifecycle (Qt imported lazily) ---------------------------
    def start(self):
        from serial_reader import SerialReaderThread
        self._reader = SerialReaderThread(self._serial)
        self._reader.lineFrame.connect(self._on_line)
        self._reader.lockInPoint.connect(self._on_lockin)
        self._reader.asciiLine.connect(self._on_ascii)
        self._reader.start()

    def stop(self):
        if self._reader is not None:
            self._reader.stop()
            self._reader.wait(2000)
            self._reader = None

    def _on_line(self, line_number, z_arr, err_arr):
        self.publish("line", (line_number, z_arr, err_arr))

    def _on_lockin(self, idx, bias, in_phase, quad):
        self.publish("lockin", (idx, bias, in_phase, quad))

    def _on_ascii(self, line):
        self.publish("ascii", line)
