"""Frozen-reference check after the B5 migration (pipeline v2): the migrated LiveRaster must
paint exactly what the pre-migration update_line painted.  The reference below is a verbatim
copy of the old algorithm (buffers only; snapshots and repaint timing are UI)."""
import os
import tempfile

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["QTPANDA_SETTINGS"] = os.path.join(tempfile.mkdtemp(), "test_settings.ini")

from PySide6.QtWidgets import QApplication  # noqa: E402

import calibration  # noqa: E402
import live_raster  # noqa: E402


def _old_update(state, line_number, z_arr, err_arr):
    H, half, dx, dy = state["H"], state["half"], state["dx"], state["dy"]
    raw = line_number % (2 * H)
    state["last"] = raw
    row = raw if raw < H else (2 * H - 1 - raw)
    if len(z_arr) < 2 * half:
        return
    zt, zr = z_arr[:half], z_arr[half:2 * half][::-1]
    et, er = err_arr[:half], err_arr[half:2 * half][::-1]
    if raw >= H:
        row -= dy
        if not (0 <= row < H):
            return
        if dx:
            zt = np.roll(zt, -dx); zr = np.roll(zr, -dx); et = np.roll(et, -dx); er = np.roll(er, -dx)
    for k, v in (("zt", zt), ("zr", zr), ("et", et), ("er", er)):
        state[k][row, :] = v.astype(np.float32)
    state["painted"][row] = True


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize("dx,dy,short_every", [(0, 0, 0), (2, -3, 7), (-4, 5, 0)])
def test_migrated_liveraster_matches_frozen_reference(app, dx, dy, short_every):
    H, ppl = 12, 24
    lr = live_raster.LiveRaster(calibration.Calibration(), image_height=H, pixels_per_line=ppl)
    lr._drift_dx, lr._drift_dy = dx, dy
    st = {"H": H, "half": ppl // 2, "dx": dx, "dy": dy, "last": -1, "painted": np.zeros(H, bool)}
    for k in ("zt", "zr", "et", "er"):
        st[k] = np.zeros((H, ppl // 2), np.float32)
    rng = np.random.default_rng(4)
    for n in range(5 * 2 * H + 3):
        m = ppl - 3 if (short_every and n % short_every == 0) else ppl     # some short lines
        z = rng.integers(-9999, 9999, m).astype(np.int32); e = rng.integers(-9999, 9999, m).astype(np.int32)
        lr.update_line(n, z, e)
        _old_update(st, n, z, e)
    np.testing.assert_array_equal(lr._z_trace, st["zt"]); np.testing.assert_array_equal(lr._z_retrace, st["zr"])
    np.testing.assert_array_equal(lr._e_trace, st["et"]); np.testing.assert_array_equal(lr._e_retrace, st["er"])
    np.testing.assert_array_equal(lr._painted, st["painted"])
    lr.resize_buffers(8, 16)                                   # geometry change keeps working
    assert lr._z_trace.shape == (8, 8) and lr._last_raw_row == -1
