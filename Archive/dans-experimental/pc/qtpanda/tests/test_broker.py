"""DataBroker core (Phase 4) — pub/sub, drop-oldest, journaled send. No GUI.

Exercises the critical non-blocking-view logic without the Qt reader thread:
the reader->publish wiring is validated separately against the emulator.
"""
import json

import data_broker
import session_journal as sj


class FakeSerial:
    """Captures writes; enough for the broker's command path."""
    def __init__(self):
        self.written = []

    def write(self, b):
        self.written.append(b)
        return len(b)


def test_drop_oldest_bounded_delivery():
    b = data_broker.DataBroker(FakeSerial())
    sub = b.subscribe("line", maxlen=3)
    for i in range(5):
        b.publish("line", i)
    assert sub.poll() == [2, 3, 4]      # oldest two dropped, never blocked
    assert sub.dropped == 2


def test_latest_only_topic():
    b = data_broker.DataBroker(FakeSerial())
    s = b.subscribe("status", latest_only=True)
    for i in range(4):
        b.publish("status", i)
    assert s.latest() == 3 and len(s) == 1


def test_slow_subscriber_does_not_affect_others():
    b = data_broker.DataBroker(FakeSerial())
    slow = b.subscribe("line", maxlen=2)      # will overflow
    fast = b.subscribe("line", maxlen=100)    # keeps up
    for i in range(10):
        b.publish("line", i)
    assert slow.dropped == 8 and len(slow) == 2
    assert fast.dropped == 0 and len(fast) == 10   # unaffected by the slow one


def test_send_writes_and_journals_except_gsts(tmp_path):
    fake = FakeSerial()
    b = data_broker.DataBroker(fake)
    p = sj.start(log_dir=str(tmp_path))
    b.send("ENGA")
    b.send("GSTS")                       # poll: written but not journaled
    b.send("MTMV -5", src="agent")
    sj.stop()

    assert fake.written == [b"ENGA", b"GSTS", b"MTMV -5"]
    recs = [json.loads(ln) for ln in open(p)]
    cmds = [(r["data"]["cmd"], r["src"]) for r in recs if r["type"] == "command"]
    assert cmds == [("ENGA", "human"), ("MTMV -5", "agent")]


def test_unsubscribe():
    b = data_broker.DataBroker(FakeSerial())
    sub = b.subscribe("line")
    b.unsubscribe(sub)
    b.publish("line", 1)
    assert len(sub) == 0
