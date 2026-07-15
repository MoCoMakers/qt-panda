"""session_query (A) — state-at-T, clock fit, timing epochs. Pure, no GUI."""
import session_journal as sj
import session_query
import synth_source as ss


def test_state_and_settings_at(tmp_path):
    csvp = tmp_path / "s_1000000000000.csv"
    ss.write_csv(str(csvp), ss.generate(kind="tunneling", n=100, seed=0))

    jp = sj.start(log_dir=str(tmp_path), csv=csvp.name)
    sj.mark_time(1000); sj.log_command("SCSZ 12000")
    sj.mark_time(2000); sj.log_command("SETP 500")
    sj.record("x", path=str(csvp))
    sj.stop()

    recs, rows = session_query.load(jp, str(csvp))
    late = session_query.state_at(recs, rows, 2500)
    assert late["settings"]["scan_size"] == 12000
    assert late["settings"]["setpoint"] == 500
    assert "current_A" in late["reading"]

    early = session_query.state_at(recs, rows, 1500)      # before SETP
    assert early["settings"]["scan_size"] == 12000
    assert "setpoint" not in early["settings"]


def test_clock_fit_and_epochs(tmp_path):
    jp = sj.start(log_dir=str(tmp_path))
    for i in range(6):
        sj.mark_time(1000 + i * 100)
        sj.log_command(f"DACZ {40000 - i}")
    sj.mark_time(2000); sj.log_command("SETD 40")
    sj.mark_time(3000); sj.log_command("SETD 80")
    sj.stop()

    recs, _ = session_query.load(jp)
    cf = session_query.clock_fit(recs)
    assert cf is not None and cf["n"] >= 6

    eps = [(e["param"], e["value"]) for e in session_query.epochs(recs)]
    assert ("control_dt_us", 40) in eps and ("control_dt_us", 80) in eps
