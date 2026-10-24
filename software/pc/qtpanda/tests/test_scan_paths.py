"""scan_paths — bit-exactness against the literal firmware port, custom-file equivalence,
transforms, determinism and the recording contract."""
import hashlib
import json

import numpy as np
import pytest

import scan_paths as S

SMALL = [S.Spec(spp=3, bins=16, scan_size=100000), S.Spec(spp=5, bins=22, scan_size=77777, xo=1234, yo=-999),
         S.Spec(spp=1, bins=10, scan_size=524287, line_repeat=2)]


@pytest.mark.parametrize("spec", SMALL)
def test_raster_matches_literal_firmware_port(spec):
    ref = S.FirmwareRasterRef(spec)
    N = spec.ticks_per_frame * 2 + 7                      # two frames and a bit: wraps and resyncs
    rx, ry = zip(*[ref.tick()[:2] for _ in range(N)])
    blk = S.default_block(spec)
    n = np.arange(1, N + 1)
    x, y = S.ticks(blk, n)
    assert np.array_equal(x, rx) and np.array_equal(y, ry)


def test_raster_matches_port_at_oct22_settings():
    spec = S.Spec(spp=19, bins=512, scan_size=262144)      # 10 Hz lines, 512 px, 10 us ticks
    ref = S.FirmwareRasterRef(spec)
    N = 60000                                               # ~6 lines, several turnarounds
    rx, ry = zip(*[ref.tick()[:2] for _ in range(N)])
    x, y = S.ticks(S.default_block(spec), np.arange(1, N + 1))
    assert np.array_equal(x, rx) and np.array_equal(y, ry)


@pytest.mark.parametrize("spec", SMALL[:2] + [S.Spec(spp=19, bins=64, scan_size=262144)])
def test_custom_file_of_the_raster_is_bit_exact(spec):
    cust = S.raster_to_custom(spec)
    cust = json.loads(json.dumps(cust))                     # survives a file round trip
    a = S.frame_ticks(S.default_block(spec))
    b = S.frame_ticks(S.make_block("custom", {}, spec, custom=cust))
    assert np.array_equal(a[1], b[1]) and np.array_equal(a[2], b[2])


def test_rotation_zero_is_identity_and_ninety_is_exact():
    spec = SMALL[1]
    base = S.frame_ticks(S.default_block(spec))
    r0 = S.frame_ticks(S.make_block("raster", {}, spec, rotation_deg=0.0))
    assert np.array_equal(base[1], r0[1]) and np.array_equal(base[2], r0[2])
    r90 = S.frame_ticks(S.make_block("raster", {}, spec, rotation_deg=90.0))
    assert np.array_equal(r90[1] - spec.xo, -(base[2] - spec.yo))
    assert np.array_equal(r90[2] - spec.yo, base[1] - spec.xo)


def test_crosshatch_transposes_odd_frames_and_joins_seamlessly():
    spec = SMALL[0]
    blk = S.make_block("raster", {}, spec, sequence="crosshatch")
    _, x0, y0 = S.frame_ticks(blk, 0)
    _, x1, y1 = S.frame_ticks(blk, 1)
    assert np.array_equal(x1 - spec.xo, y0 - spec.yo) and np.array_equal(y1 - spec.yo, x0 - spec.xo)
    # the frame ends at the (-L, -L) corner, which the transpose maps onto itself
    assert x0[-1] == y0[-1]


@pytest.mark.parametrize("name,params", [("spiral_arch", {"speed": "cav"}), ("spiral_arch", {"speed": "clv"}),
                                         ("spiral_fermat", {}), ("loops_centre", {}), ("spokes", {}), ("rose", {})])
def test_paths_deterministic_and_in_range(name, params):
    spec = S.Spec(spp=4, bins=64, segments=64, scan_size=200000)
    blk = S.make_block(name, params, spec)
    a = S.frame_ticks(blk); b = S.frame_ticks(json.loads(json.dumps(blk)))
    assert np.array_equal(a[1], b[1]) and np.array_equal(a[2], b[2])
    R = spec.scan_size // 2
    assert np.abs(a[1] - spec.xo).max() <= R + 1 and np.abs(a[2] - spec.yo).max() <= R + 1


def test_isqrt_exact():
    v = np.array([0, 1, 2, 3, 4, 15, 16, 17, (1 << 32), (1 << 52) + 12345, (1 << 62) - 1], dtype=np.int64)
    import math
    assert [int(r) for r in S.isqrt_vec(v)] == [math.isqrt(int(t)) for t in v]


def test_sine_table_frozen():
    # The firmware will embed these exact values; a change here must be a new path version.
    h = hashlib.sha256(S.SIN_TABLE.astype("<i8").tobytes()).hexdigest()
    assert h == S_TABLE_SHA


def test_reconstruct_shapes_and_legacy_default():
    spec = SMALL[0]
    m = S.reconstruct(S.read_block({}, spec_if_missing=spec))
    assert m["x"].shape == (spec.segments, spec.bins)
    assert m["tick0"][0, 0] == 1 and m["tick0"][-1, -1] == spec.ticks_per_frame - spec.spp + 1
    with pytest.raises(ValueError):
        S.read_block({})


S_TABLE_SHA = "d0c9d680b3c45f3fe9e123c3f5b9ec6dfb0c40cd837b1e6f8e51a7234ae528f9"   # frozen 2026-10-23


@pytest.mark.parametrize("name,params", [("spiral_fermat", {"turns": 128}), ("spiral_arch", {"turns": 128}),
                                         ("rose", {"loops": 1024}), ("loops_centre", {"loops": 200})])
def test_no_int64_overflow_at_full_size(name, params):
    spec = S.Spec(spp=19, bins=512, segments=512, scan_size=262144)       # 49.8 s frame
    n, x, y = S.frame_ticks(S.make_block(name, params, spec))
    R = spec.scan_size // 2
    assert np.abs(x).max() <= R + 1 and np.abs(y).max() <= R + 1
    assert np.isfinite(x.astype(float)).all()
