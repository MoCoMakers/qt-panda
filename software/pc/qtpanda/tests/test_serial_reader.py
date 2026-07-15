"""SerialReaderThread parser — synthetic byte-stream edge cases."""
import numpy as np

from conftest import build_L_frame, build_M_frame, run_reader


def test_single_L_frame(qapp):
    z   = [10, -20, 30, -40]
    err = [1, 2, 3, 4]
    got = run_reader(qapp, build_L_frame(7, z, err), expect=1)
    assert len(got["line"]) == 1
    ln, zarr, earr = got["line"][0]
    assert ln == 7
    np.testing.assert_array_equal(zarr, np.array(z, dtype=np.int32))
    np.testing.assert_array_equal(earr, np.array(err, dtype=np.int32))


def test_single_M_frame(qapp):
    got = run_reader(qapp, build_M_frame(3, -1000, 555, -777), expect=1)
    assert got["lock"] == [(3, -1000, 555, -777)]


def test_ascii_line(qapp):
    got = run_reader(qapp, b"100,200,0,0,1,5,0,1,0,1234\n", expect=1)
    assert got["ascii"] == ["100,200,0,0,1,5,0,1,0,1234"]


def test_ascii_then_binary_interleaved(qapp):
    stream = b"Approached!\n" + build_L_frame(1, [9], [8])
    got = run_reader(qapp, stream, expect=2)
    assert "Approached!" in got["ascii"]
    assert len(got["line"]) == 1
    assert got["line"][0][0] == 1


def test_binary_then_ascii(qapp):
    stream = build_M_frame(0, 1, 2, 3) + b"D\n"
    got = run_reader(qapp, stream, expect=2)
    assert got["lock"] == [(0, 1, 2, 3)]
    assert got["ascii"] == ["D"]


def test_newline_inside_int32_payload_is_not_a_terminator(qapp):
    # z value 0x0A0A0A0A contains 0x0A bytes; must be read as payload,
    # never mistaken for an ASCII line terminator.
    val = 0x0A0A0A0A
    got = run_reader(qapp, build_L_frame(2, [val], [0]), expect=1)
    assert len(got["line"]) == 1
    assert int(got["line"][0][1][0]) == val


def test_truncated_frame_emits_nothing(qapp):
    # Header says 4 pixels but payload is short → parser must not emit
    # a bogus line and must not crash.
    good = build_L_frame(5, [1, 2, 3, 4], [5, 6, 7, 8])
    truncated = good[:10]  # magic+header + a few payload bytes only
    got = run_reader(qapp, truncated, expect=1, timeout_s=1.0)
    assert got["line"] == []
    assert got["lock"] == []


def test_garbage_byte_before_valid_ascii(qapp):
    # A stray non-magic byte starts an ASCII accumulation; the line is
    # still delivered (possibly with the stray prefix).
    got = run_reader(qapp, b"\x01hello\n", expect=1)
    assert len(got["ascii"]) == 1
    assert got["ascii"][0].endswith("hello")


def test_multiple_back_to_back_L_frames(qapp):
    stream = (build_L_frame(0, [1], [1])
              + build_L_frame(1, [2], [2])
              + build_L_frame(2, [3], [3]))
    got = run_reader(qapp, stream, expect=3)
    assert [g[0] for g in got["line"]] == [0, 1, 2]


def test_large_frame_roundtrip(qapp):
    n = 1024
    z = list(range(-n // 2, n // 2))
    err = list(range(n))
    got = run_reader(qapp, build_L_frame(42, z, err), expect=1)
    ln, zarr, earr = got["line"][0]
    assert ln == 42
    np.testing.assert_array_equal(zarr, np.array(z, dtype=np.int32))
    np.testing.assert_array_equal(earr, np.array(err, dtype=np.int32))
