"""status_logger — true-time threaded CSV writer."""
import csv
import time

from status_logger import StatusLogger, pack_flags, HEADER


def _amp(adc):
    return adc * 3.125e-12


def _wait_rows(logger, n, timeout=2.0):
    t0 = time.time()
    while logger.n_rows < n and time.time() - t0 < timeout:
        time.sleep(0.01)


def test_writes_rows_and_header(tmp_path):
    lg = StatusLogger(_amp)
    p = str(tmp_path / "s.csv")
    lg.start(p)
    lg.put(1000, 5, 10000, 35014, 42, pack_flags(True, False, True))
    lg.put(1005, -3, 10000, 35014, 42, 0)
    _wait_rows(lg, 2)
    lg.stop()
    rows = list(csv.reader(open(p)))
    assert rows[0] == HEADER
    assert len(rows) == 3
    # elapsed from first sample's firmware clock
    assert rows[1][0] == "0.000" and rows[2][0] == "0.005"
    assert rows[1][2] == "5" and rows[2][2] == "-3"
    # flags unpacked into is_scanning / is_const_current / is_approaching
    assert rows[1][7:10] == ["1", "0", "1"]
    assert rows[2][7:10] == ["0", "0", "0"]


def test_put_before_start_and_after_stop_is_noop(tmp_path):
    lg = StatusLogger(_amp)
    lg.put(1, 2, 3, 4, 5, 0)          # no crash, silently dropped
    p = str(tmp_path / "s.csv")
    lg.start(p)
    lg.put(1000, 1, 0, 0, 0, 0)
    _wait_rows(lg, 1)
    lg.stop()
    lg.put(1010, 2, 0, 0, 0, 0)       # dropped
    rows = list(csv.reader(open(p)))
    assert len(rows) == 2


def test_restart_replaces_file(tmp_path):
    lg = StatusLogger(_amp)
    p1 = str(tmp_path / "a.csv")
    p2 = str(tmp_path / "b.csv")
    lg.start(p1)
    lg.put(1000, 1, 0, 0, 0, 0)
    _wait_rows(lg, 1)
    lg.start(p2)                       # implicit stop of the first
    lg.put(2000, 2, 0, 0, 0, 0)
    _wait_rows(lg, 1)
    lg.stop()
    assert len(list(csv.reader(open(p1)))) == 2
    assert len(list(csv.reader(open(p2)))) == 2


def test_creates_missing_directory(tmp_path):
    lg = StatusLogger(_amp)
    p = str(tmp_path / "sub" / "dir" / "s.csv")
    lg.start(p)
    lg.put(1000, 1, 0, 0, 0, 0)
    _wait_rows(lg, 1)
    lg.stop()
    assert len(list(csv.reader(open(p)))) == 2


def test_high_rate_burst_no_loss(tmp_path):
    lg = StatusLogger(_amp)
    p = str(tmp_path / "s.csv")
    lg.start(p)
    n = 5000
    for i in range(n):
        lg.put(1000 + 5 * i, i % 100, 10000, 35014, 0, 0)
    _wait_rows(lg, n, timeout=5.0)
    lg.stop()
    rows = list(csv.reader(open(p)))
    assert len(rows) == n + 1
