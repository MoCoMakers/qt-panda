"""Co-pilot API layer (Phase 6 core) — observe/annotate/verdict, no MCP/GUI."""
import json

import copilot_api
import data_broker
import session_journal as sj
import synth_source as ss


class FakeSerial:
    def write(self, b):
        return len(b)


def test_add_note_is_agent_attributed(tmp_path):
    api = copilot_api.CopilotAPI()
    p = sj.start(log_dir=str(tmp_path))
    api.add_note("no current response to -1 step")
    sj.stop()
    recs = [json.loads(ln) for ln in open(p)]
    notes = [r for r in recs if r["type"] == "note"]
    assert notes and notes[0]["src"] == "agent"


def test_run_verdict(tmp_path):
    csv = tmp_path / "s_1000000000000.csv"
    ss.write_csv(str(csv), ss.generate(kind="tunneling", n=300, seed=0))
    assert copilot_api.CopilotAPI().run_verdict(str(csv))["verdict"] == "TUNNELING_LIKE"


def test_journal_tail(tmp_path):
    api = copilot_api.CopilotAPI()
    sj.start(log_dir=str(tmp_path))
    api.add_note("a")
    api.add_note("b")
    tail = api.journal_tail(n=2)
    sj.stop()
    assert [r["type"] for r in tail][-1] == "note"


def test_get_recent_samples_from_broker():
    b = data_broker.DataBroker(FakeSerial())
    api = copilot_api.CopilotAPI(broker=b)
    for i in range(5):
        b.publish("sample", {"i": i})
    got = api.get_recent_samples(n=10)
    assert [s["i"] for s in got] == [0, 1, 2, 3, 4]
