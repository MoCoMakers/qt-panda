"""frame_logger / replay_frames roundtrip, drop accounting, crash tolerance."""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import frame_logger
import replay_frames


def _mk_frame(line, ppl=32, seed=0):
    rng = np.random.RandomState(seed + line)
    z = rng.randint(-500000, 500000, ppl).astype(np.int32)
    e = rng.randint(-500000, 500000, ppl).astype(np.int32)
    return z, e


def test_roundtrip_verbatim(tmp_path):
    fl = frame_logger.FrameLogger(log_dir=str(tmp_path))
    path = fl.start({"scan_size_nm": 30.0, "pixels_per_line": 32})
    sent = []
    for line in range(10):
        z, e = _mk_frame(line)
        fl.on_line(line, z, e)
        sent.append((line, z, e))
    fl.stop()

    got = list(frame_logger.read_frames(path))
    assert len(got) == 10
    for (t, line, z, e), (sline, sz, se) in zip(got, sent):
        assert line == sline
        assert np.array_equal(z, sz)
        assert np.array_equal(e, se)
        assert t > 0

    sc = frame_logger.read_sidecar(path)
    assert sc["settings"]["scan_size_nm"] == 30.0
    assert sc["n_frames"] == 10
    assert sc["n_dropped_lines"] == 0
    assert "t_end" in sc


def test_drop_detection(tmp_path):
    fl = frame_logger.FrameLogger(log_dir=str(tmp_path))
    path = fl.start()
    for line in (0, 1, 2, 5, 6):          # 3 and 4 dropped
        z, e = _mk_frame(line)
        fl.on_line(line, z, e)
    fl.stop()
    assert fl.n_dropped == 2
    assert frame_logger.read_sidecar(path)["n_dropped_lines"] == 2


def test_drop_detection_across_wrap(tmp_path):
    fl = frame_logger.FrameLogger(log_dir=str(tmp_path))
    fl.start()
    # wrap at 8 lines: ...6,7,0,1  then jump 1 -> 4 (2,3 dropped)
    for line in (5, 6, 7, 0, 1, 4):
        z, e = _mk_frame(line)
        fl.on_line(line, z, e)
    fl.stop()
    assert fl._wrap == 8
    assert fl.n_dropped == 2


def test_truncated_trailing_record(tmp_path):
    fl = frame_logger.FrameLogger(log_dir=str(tmp_path))
    path = fl.start()
    for line in range(3):
        z, e = _mk_frame(line)
        fl.on_line(line, z, e)
    fl.stop()
    # Simulate a crash mid-write: chop the last record in half.
    size = os.path.getsize(path)
    with open(path, "r+b") as f:
        f.truncate(size - 40)
    got = list(frame_logger.read_frames(path))
    assert len(got) == 2                  # clean stop, no exception


def test_replay_matches_liveraster_mapping(tmp_path):
    """rebuild_images must apply the exact update_line math, INCLUDING the
    Y-parity rule (2026-07-15): the firmware's Y triangle mirrors alternate
    passes, so after a line-number wrap rows map bottom-up."""
    H, ppl = 4, 8
    fl = frame_logger.FrameLogger(log_dir=str(tmp_path))
    path = fl.start()
    frames = {}
    for line in range(6):     # lines 4,5 start the mirrored second pass
        z, e = _mk_frame(line, ppl=ppl)
        fl.on_line(line, z, e)
        frames[line] = (z, e)
    fl.stop()

    out = replay_frames.rebuild_images(path, image_height=H)
    half = ppl // 2
    # Y FOLD: one cycle = 2H lines (H=4): ascending lines 0..3 -> rows
    # 0..3; descending lines 4,5 mirror back -> rows 3,2 (overwriting).
    expected = {0: 0, 1: 1, 5: 2, 4: 3}
    for line, row in expected.items():
        z, e = frames[line]
        assert np.array_equal(out["z_trace"][row], z[:half].astype(np.float32))
        assert np.array_equal(out["z_retrace"][row],
                              z[half:2 * half][::-1].astype(np.float32))
        assert np.array_equal(out["e_trace"][row], e[:half].astype(np.float32))
        assert np.array_equal(out["e_retrace"][row],
                              e[half:2 * half][::-1].astype(np.float32))
    assert out["n_frames"] == 6


def test_start_closes_prior_run(tmp_path):
    fl = frame_logger.FrameLogger(log_dir=str(tmp_path))
    p1 = fl.start()
    z, e = _mk_frame(0)
    fl.on_line(0, z, e)
    p2 = fl.start()                       # implicit stop of run 1
    fl.stop()
    assert p1 != p2
    assert frame_logger.read_sidecar(p1)["n_frames"] == 1
    assert list(frame_logger.read_frames(p2)) == []
