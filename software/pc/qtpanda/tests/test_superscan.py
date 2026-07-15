"""superscan — multi-frame drift super-resolution."""
import numpy as np

import superscan


def _synthetic(H=48, W=48):
    yy, xx = np.mgrid[0:H, 0:W] / H
    img = np.zeros((H, W))
    img += 100 * np.exp(-(((xx - 0.4) ** 2 + (yy - 0.5) ** 2) / 0.01))
    img += 60 * (xx > 0.6)
    return img


def _shift(img, dy, dx):
    return np.roll(np.roll(img, int(round(dy)), 0), int(round(dx)), 1)


def test_register_recovers_known_shift():
    base = _synthetic()
    frames = [base, _shift(base, 3, -2), _shift(base, -1, 4)]
    shifts = superscan.register(frames)
    # frame k should register back to ref by the OPPOSITE of the applied roll
    assert abs(shifts[1][0] + 3) < 1.0 and abs(shifts[1][1] - 2) < 1.0
    assert abs(shifts[2][0] - 1) < 1.0 and abs(shifts[2][1] + 4) < 1.0


def test_superscan_output_shape_and_completeness():
    base = _synthetic()
    frames = [base, _shift(base, 1, 1), _shift(base, -1, 2), _shift(base, 2, -1)]
    hi, shifts, stats = superscan.superscan(frames, up=2)
    assert hi.shape == (96, 96)
    assert np.isfinite(hi).all()          # no holes
    assert stats["n_frames"] == 4 and stats["up"] == 2


def test_superscan_reduces_noise_vs_single_frame():
    rng = np.random.default_rng(0)
    base = _synthetic()
    frames = [base + rng.normal(0, 15, base.shape) for _ in range(8)]
    hi, _, _ = superscan.superscan(frames, up=1)   # up=1 -> pure averaging
    # averaged noise std should be well below a single noisy frame's residual
    single_res = (frames[0] - base).std()
    hi_res = (hi - base).std()
    assert hi_res < single_res * 0.6


def test_fold_frame_mirrors_descending_half():
    H, W = 4, 6
    lines = [(i, np.full(W, float(i))) for i in range(2 * H)]  # 0..7
    img = superscan.fold_frame(lines, H)
    # ascending 0..3 -> rows 0..3; descending 4..7 -> rows 3,2,1,0 (overwrite)
    assert np.allclose(img[3], 4)   # line 4 landed on row 3
    assert np.allclose(img[0], 7)   # line 7 landed on row 0


def test_all_modes_survive_flat_and_noisy_frames():
    # Flat/degenerate frames give ill-conditioned registration; every mode
    # must still return a finite image, no index overflow (bench crash
    # "index out of bounds for axis 1 with size 256", 2026-07-15).
    rng = np.random.default_rng(1)
    flat = [np.full((32, 32), 5.0) + rng.normal(0, 0.01, (32, 32))
            for _ in range(6)]
    for mode in superscan.MODES:
        hi, _, _ = superscan.superscan(flat, mode=mode)
        assert np.isfinite(hi).all()


def test_linearize_monotonic():
    # higher err (log domain) -> lower current; check monotonic decrease
    vals = superscan.linearize_err([0, 100000, 300000], 320)
    assert vals[0] > vals[1] > vals[2]
