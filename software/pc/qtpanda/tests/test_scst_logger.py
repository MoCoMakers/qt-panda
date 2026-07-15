"""scst_logger — verbatim legacy-scan log + faithful rebuild."""
import json

import scst_logger


def test_roundtrip_rebuild(tmp_path):
    p = scst_logger.start({"x_res": 3, "samples_per_pixel": 2,
                           "bias_dac": 35014}, log_dir=str(tmp_path))
    scst_logger.log_line("A,0,10,20,30\r")
    scst_logger.log_line("Z,0,101,102,103\r")
    scst_logger.log_line("A,1,11,21,31\r")
    scst_logger.log_line("Z,1,111,112,113\r")
    scst_logger.log_line("D\r")
    done = scst_logger.stop()
    assert done == p

    out = scst_logger.rebuild(p)
    assert out["adc"][0] == [10, 20, 30]
    assert out["adc"][1] == [11, 21, 31]
    assert out["dacz"][1] == [111, 112, 113]
    assert out["settings"]["settings"]["bias_dac"] == 35014
    assert out["settings"]["rows"] == 5


def test_garbled_rows_kept_verbatim_but_skipped_in_rebuild(tmp_path):
    p = scst_logger.start({}, log_dir=str(tmp_path))
    scst_logger.log_line("A,0,1,2")
    scst_logger.log_line("47400A,,junk")          # corruption survives on disk
    scst_logger.log_line("A,notanint,5,6")
    scst_logger.stop()
    raw = open(p).read().splitlines()
    assert len(raw) == 3                          # verbatim: everything kept
    out = scst_logger.rebuild(p)
    assert list(out["adc"].keys()) == [0]         # rebuild: only valid rows


def test_partial_scan_still_rebuilds(tmp_path):
    # Crash mid-scan: no stop() finalization of the row count, file still
    # line-flushed -> partial image recoverable.
    p = scst_logger.start({"x_res": 2}, log_dir=str(tmp_path))
    scst_logger.log_line("A,0,7,8")
    out = scst_logger.rebuild(p)
    assert out["adc"][0] == [7, 8]
    scst_logger.stop()


def test_inactive_log_line_is_noop():
    scst_logger.log_line("A,0,1")   # no crash when no log is open
    assert not scst_logger.is_active()
