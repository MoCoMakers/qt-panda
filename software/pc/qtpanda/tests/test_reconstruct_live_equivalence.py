"""Gates 2 and 4 (pipeline v2, D38): reconstruct.LiveFold reproduces LiveRaster.update_line's
buffers exactly (with and without drift correction), and the shared display functions reproduce
LiveRaster's transforms.  Runs the real widget offscreen with an isolated settings file."""
import os
import tempfile

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["QTPANDA_SETTINGS"] = os.path.join(tempfile.mkdtemp(), "test_settings.ini")

from PySide6.QtWidgets import QApplication  # noqa: E402

import calibration  # noqa: E402
import live_raster  # noqa: E402
import reconstruct as R  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _lines(n, ppl, seed=1):
    rng = np.random.default_rng(seed)
    for k in range(n):
        yield k, rng.integers(-50_000, 50_000, ppl).astype(np.int32), rng.integers(-50_000, 50_000, ppl).astype(np.int32)


@pytest.mark.parametrize("dx,dy", [(0, 0), (3, -2), (-1, 4)])
def test_gate2_livefold_equals_liveraster(app, dx, dy):
    H, ppl = 16, 32
    lr = live_raster.LiveRaster(calibration.Calibration(), image_height=H, pixels_per_line=ppl)
    lr._drift_dx, lr._drift_dy = dx, dy
    lf = R.LiveFold(H, ppl // 2, drift_dx=dx, drift_dy=dy)
    for k, z, e in _lines(3 * 2 * H + 5, ppl):
        lr.update_line(k, z, e)
        lf.add_line(k, z, e)
    for name in ("z_trace", "z_retrace", "e_trace", "e_retrace"):
        np.testing.assert_array_equal(getattr(lr, "_" + name), getattr(lf, name))
    np.testing.assert_array_equal(lr._painted, lf.painted)
    np.testing.assert_array_equal(lr._paint_seq, lf.paint_seq)


def test_gate4_display_functions_identical(app):
    rng = np.random.default_rng(2)
    a = rng.normal(size=(24, 40)).astype(np.float32) * 1000
    for m in R.ROW_ALIGN_METHODS:
        np.testing.assert_array_equal(live_raster._row_align(a, m), R.row_align(a, m))
    lr = live_raster.LiveRaster(calibration.Calibration(), image_height=8, pixels_per_line=16)
    for pb in (True, False):
        lr._peaks_bright = pb
        lr._lin_mode = False
        np.testing.assert_array_equal(lr._z_display(a), R.z_display(a, pb))
        np.testing.assert_array_equal(lr._e_display(a), R.e_display(a, pb))
    lr.set_current_display(True, 160)
    np.testing.assert_allclose(lr._e_display(a), R.e_display(a, linear=True, setlog=R.setlog_of(160)), rtol=0, atol=0)
