"""CopilotAPI.query_point (A) — full state at T via journal+CSV join. No GUI."""
import copilot_api
import session_journal as sj
import synth_source as ss


def test_query_point_joins_reading_and_settings(tmp_path):
    csvp = tmp_path / "s_1000000000000.csv"
    ss.write_csv(str(csvp), ss.generate(kind="tunneling", n=100, seed=0))

    jp = sj.start(log_dir=str(tmp_path), csv=csvp.name)
    sj.mark_time(1500); sj.log_command("SETP 700")
    sj.record("x", path=str(csvp))
    sj.stop()

    st = copilot_api.CopilotAPI().query_point(2000, journal_path=jp,
                                              csv_path=str(csvp))
    assert st["settings"]["setpoint"] == 700
    assert "current_A" in st["reading"] and "dac_z" in st["reading"]
