"""Session journal (J1) + reconstruct (J3) regression — pure, no GUI."""
import json

import session_journal as sj
import stab_runner
import synth_source as ss


def test_journal_roundtrip(tmp_path):
    p = sj.start(log_dir=str(tmp_path), csv="s.csv")
    sj.log_command("MTMV -5")
    sj.log_command("ENGA")
    sj.note("near sample", src="human")
    sj.record("stab_stop", path="s.csv")
    sj.stop()

    recs = [json.loads(ln) for ln in open(p)]
    types = [r["type"] for r in recs]
    assert types[0] == "session_start" and types[-1] == "session_end"
    assert any(r["type"] == "command" and r["data"]["cmd"] == "ENGA"
               for r in recs)
    assert any(r["type"] == "note" for r in recs)
    for r in recs:                      # every record has the core fields
        assert "t" in r and "src" in r and "data" in r
    assert not sj.is_active()


def test_loggers_are_noop_when_inactive():
    sj.stop()                           # ensure no active session
    sj.log_command("XXXX")              # must not raise
    sj.note("y")
    sj.record("z")
    assert not sj.is_active()


def test_reconstruct_grades_linked_csv(tmp_path, capsys):
    csv = tmp_path / "demo_stability_1000000000000.csv"
    ss.write_csv(str(csv), ss.generate(kind="tunneling", n=300, seed=0))
    p = sj.start(log_dir=str(tmp_path), csv=csv.name)
    sj.record("stab_stop", path=csv.name)
    sj.stop()

    assert stab_runner.reconstruct(p) == 0
    out = capsys.readouterr().out
    assert "session_start" in out
    assert "TUNNELING_LIKE" in out      # linked CSV graded during replay
