import math
import os
import time
import numpy as np
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton
)
from PySide6.QtCore import Slot, Signal, QSettings
import pyqtgraph as pg
import tifffile

import data_paths
import session_journal


ROW_ALIGN_METHODS = ("Median of diffs", "Median", "Poly deg 5")


def _row_align(arr, method):
    """Gwyddion-style per-row background removal (display/post only — raw
    buffers and .frames stay verbatim).

    Median          — subtract each row's median (kills row offsets AND any
                      real slow-axis gradient).
    Median of diffs — offset each row by the cumulative median of its
                      point-wise difference to the previous row; robust to
                      features crossing rows, preserves in-row structure.
    Poly deg 5      — subtract a degree-5 polynomial fitted to each row
                      (also flattens in-row bow/tilt).
    """
    a = np.asarray(arr, dtype=np.float64).copy()
    if a.ndim != 2 or a.shape[0] < 2:
        return arr
    if method == "Median":
        a -= np.median(a, axis=1, keepdims=True)
    elif method == "Median of diffs":
        d = np.median(np.diff(a, axis=0), axis=1)
        # Accumulate only jumps that beat the in-row pixel noise: a plain
        # cumsum random-walks on noise-dominated frames and paints a fake
        # vertical ramp.  Expected noise of a median-of-W-diffs is
        # ~1.253*sigma_pix*sqrt(2)/sqrt(W); gate at 5x that (a single
        # false pass would step every row after it, so keep P tiny).
        res = a - np.median(a, axis=1, keepdims=True)
        sigma_pix = 1.4826 * np.median(np.abs(res))
        gate = 5.0 * 1.253 * sigma_pix * np.sqrt(2.0 / a.shape[1])
        d = np.where(np.abs(d) > gate, d, 0.0)
        off = np.concatenate(([0.0], np.cumsum(d)))
        a -= (off - off.mean())[:, None]
    elif method == "Poly deg 5":
        x = np.linspace(-1.0, 1.0, a.shape[1])
        V = np.vander(x, 6)
        coef, *_ = np.linalg.lstsq(V, a.T, rcond=None)
        a -= (V @ coef).T
    return a.astype(np.float32)


def _sweep_residual(D, U, maxshift=32):
    """Return (dx, dy, r): the shift such that U[row+dy, col+dx] best
    matches D[row, col] — i.e. the drift-corr spin-box increment that would
    align the up-sweep image U onto the down-sweep image D — plus the
    correlation r at that shift.  Separable search, wrap edges tolerated."""
    Dm = D - D.mean()
    def score(A):
        Am = A - A.mean()
        den = Dm.std() * Am.std()
        return float((Dm * Am).mean() / den) if den else -2.0
    # keep shifts under half the axis length: a full-wrap roll is an
    # identity and would tie with (and mask) the true shift
    my = min(maxshift, (D.shape[0] - 1) // 2)
    mx = min(maxshift, (D.shape[1] - 1) // 2)
    best_dy, b = 0, -2.0
    for dy in range(-my, my + 1):
        s = score(np.roll(U, -dy, axis=0))
        if s > b:
            b, best_dy = s, dy
    Ur = np.roll(U, -best_dy, axis=0)
    best_dx, b2 = 0, -2.0
    for dx in range(-mx, mx + 1):
        s = score(np.roll(Ur, -dx, axis=1))
        if s > b2:
            b2, best_dx = s, dx
    return best_dx, best_dy, b2


class SweepSnapshotWindow(QWidget):
    """Floating window with the Err image frozen at the two sweep boundaries:
    left panel is the frame as the down half completed, right panel as the up
    half terminated (line-counter wrap).  Fed by LiveRaster.update_line; each
    panel keeps the levels/LUT that were on screen at its capture instant."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Compare Sweeps")
        self.resize(900, 500)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        glw = pg.GraphicsLayoutWidget()
        lay.addWidget(glw)
        self._lbls, self._imgs, self._vbs = {}, {}, {}
        for col, (key, title) in enumerate((("down", "End of down sweep"),
                                            ("up", "End of up sweep"))):
            self._lbls[key] = glw.addLabel(f"{title} — waiting…",
                                           row=0, col=col)
            vb = glw.addViewBox(row=1, col=col)
            vb.setAspectLocked(True)
            vb.invertY(True)
            img = pg.ImageItem()
            img.setOpts(axisOrder='row-major')
            vb.addItem(img)
            self._vbs[key], self._imgs[key] = vb, img
        self._lbl_rec = glw.addLabel(
            "Recommended drift corr: waiting for a full cycle…",
            row=2, col=0, colspan=2)
        self.last_rec = None

    def set_recommendation(self, dx, dy, r):
        """Update the recommended spin-box values (absolute, i.e. current
        setting + measured residual between the two panels)."""
        self.last_rec = (dx, dy, r)
        self._lbl_rec.setText(
            f"Recommended drift corr:  X = {dx}   Y = {dy}   "
            f"(match r={r:.2f})")

    def take(self, key, arr, levels, lut):
        img = self._imgs[key]
        img.setImage(arr, autoLevels=False)
        img.setRect(pg.QtCore.QRectF(0, 0, arr.shape[1], arr.shape[0]))
        img.setLevels(levels)
        img.setLookupTable(lut)
        title = "End of down sweep" if key == "down" else "End of up sweep"
        stamp = datetime.now().strftime("%H:%M:%S")
        self._lbls[key].setText(f"{title} — {stamp}")
        self._vbs[key].autoRange(padding=0.02)


class LiveRaster(QWidget):
    """
    2x2 live image grid for the continuous-scan stream:

        +-----------+-----------+   [Z hist]
        | Z trace   | Z retrace |
        +-----------+-----------+   [err hist]
        | err trace | err retrc |
        +-----------+-----------+
        |   Z-trace 1D (latest line)   |
        +------------------------------+

    Pixel convention: firmware sends pixelsPerLine = imagePixels*2 samples
    per line; [0..N/2-1] is the forward trace, [N/2..N-1] is the reverse
    retrace (already reversed in firmware order, so we un-reverse it).

    Right-clicking either Z image recenters the scan there
    (emits scanOffsetRequested with absolute nm offsets).
    """

    scanOffsetRequested = Signal(float, float)  # (xo_nm, yo_nm)

    # Firmware logTable scale: logTable[a] = round(ln(a+1) * LOG_K); the err
    # channel is (setpointLog - logTable[|adc|]) averaged per pixel, so it is
    # exactly invertible back to linear current (ADC counts).
    LOG_K = (2 ** 19 - 1) / math.log(2 ** 15 + 1)

    def __init__(self, cal, image_height: int = 256,
                 pixels_per_line: int = 512, parent=None):
        super().__init__(parent)
        self._cal   = cal
        self._H     = image_height
        self._half  = pixels_per_line // 2

        # Scan geometry mirror (kept in sync by widget via set_scan_geometry)
        self._scan_size_nm = 160.0
        self._xo_nm        = 0.0
        self._yo_nm        = 0.0

        self._settings = QSettings("qt-panda", "dans-port")

        self._z_trace   = np.zeros((self._H, self._half), dtype=np.float32)
        self._z_retrace = np.zeros((self._H, self._half), dtype=np.float32)
        self._e_trace   = np.zeros((self._H, self._half), dtype=np.float32)
        self._e_retrace = np.zeros((self._H, self._half), dtype=np.float32)
        self._painted   = np.zeros(self._H, dtype=bool)  # rows written this scan
        self._paint_seq = np.zeros(self._H, dtype=np.int64)  # recency, see autolevel
        self._paint_counter = 0

        # Y-parity tracking (alternating-direction frames; see update_line).
        self._pass_parity = False
        self._last_raw_row = -1

        # Err-channel DISPLAY transform (raw buffers above stay verbatim):
        # in constant-height mode the log-error channel renders morphology
        # with INVERTED, log-compressed contrast (proven r=-0.99 vs ground
        # truth in the 2026-07-15 pipeline A/B sim); linearizing it back to
        # current restores a pixel-perfect match (r=+1.0000).
        self._lin_mode = False
        self._setlog = 0

        self._snap_win = None

        # Up/down sweep drift correction (display-time, pixels): descending-
        # half lines are shifted by (-dx, -dy) onto the ascending pass's
        # frame of reference before painting.  0/0 = verbatim, no correction.
        # Raw .frames on disk are never touched.  Persisted in QSettings.
        self._drift_dx = int(self._settings.value("drift_corr_x", 0))
        self._drift_dy = int(self._settings.value("drift_corr_y", -4))

        self._build_ui()

    def set_current_display(self, linear: bool, setpoint_lsb: int):
        """linear=True (constant height): show err as linearized current.
        linear=False (CC engaged): show the raw feedback-error channel."""
        setlog = int(round(math.log(abs(setpoint_lsb) + 1) * self.LOG_K))
        if (linear, setlog) == (self._lin_mode, self._setlog):
            return
        self._lin_mode, self._setlog = linear, setlog
        self._lbl_desc.setText(self._desc_text())
        self._push_all_images(auto=True)

    def _desc_text(self):
        err = ("Err: CURRENT, linearized (ADC counts)" if self._lin_mode
               else "Err: feedback error (log units)")
        return (f"Z: topography   {err}   "
                "(forward trace; retrace kept in saved frames)")

    def _e_display(self, arr):
        if not self._lin_mode:
            return arr
        return (np.exp((self._setlog - arr.astype(np.float64)) / self.LOG_K)
                - 1.0).astype(np.float32)

    # -------------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(3)

        # ---- Top control bar -------------------------------------------------
        bar = QHBoxLayout()
        bar.setSpacing(6)
        self._lbl_desc = QLabel(self._desc_text())
        bar.addWidget(self._lbl_desc)
        bar.addStretch()

        self._btn_autolevel = QPushButton("Auto levels")
        self._btn_autolevel.setMaximumWidth(90)
        self._btn_autolevel.clicked.connect(self._do_autolevel)
        bar.addWidget(self._btn_autolevel)

        # Level-tracking mode (operator 2026-07-15): how the color range is
        # maintained as frames stream.
        #   per_cycle (default) — auto-level once each completed Y cycle
        #   continuous          — auto-level on every line (live tracking)
        #   off                 — never auto (manual histogram only)
        from PySide6.QtWidgets import QRadioButton, QButtonGroup
        self._lvl_group = QButtonGroup(self)
        self._rb_lvl_cycle = QRadioButton("Auto/cycle")
        self._rb_lvl_cont = QRadioButton("Continuous")
        self._rb_lvl_off = QRadioButton("No tracking")
        self._rb_lvl_cycle.setChecked(True)
        for _rb in (self._rb_lvl_cycle, self._rb_lvl_cont, self._rb_lvl_off):
            self._lvl_group.addButton(_rb)
            bar.addWidget(_rb)
        self._rb_lvl_cycle.setToolTip("Auto-level once per completed scan cycle (default)")
        self._rb_lvl_cont.setToolTip("Auto-level on every line — live level tracking")
        self._rb_lvl_off.setToolTip("Never auto-level — use the histogram sliders manually")
        # Manual mode freezes the histogram's own view range so wheel-zoom
        # near a level spike survives the ~50 Hz per-line image updates.
        self._rb_lvl_off.toggled.connect(self._on_lvl_mode_changed)

        from PySide6.QtWidgets import QSpinBox, QCheckBox, QComboBox
        self._chk_rowalign = QCheckBox("Row align")
        self._chk_rowalign.setToolTip(
            "Apply Gwyddion-style row alignment to the displayed Z/Err "
            "images and to superscan input frames (raw data untouched)")
        self._chk_rowalign.setChecked(
            self._settings.value("row_align_on", "false") == "true")
        bar.addWidget(self._chk_rowalign)
        self._cmb_rowalign = QComboBox()
        self._cmb_rowalign.addItems(ROW_ALIGN_METHODS)
        self._cmb_rowalign.setCurrentText(
            str(self._settings.value("row_align_method",
                                     ROW_ALIGN_METHODS[0])))
        self._cmb_rowalign.setMaximumWidth(130)
        bar.addWidget(self._cmb_rowalign)
        self._chk_rowalign.toggled.connect(self._row_align_changed)
        self._cmb_rowalign.currentTextChanged.connect(
            self._row_align_changed)

        bar.addWidget(QLabel("Drift corr X:"))
        self._sb_drift_x = QSpinBox()
        self._sb_drift_x.setRange(-128, 128)
        self._sb_drift_x.setValue(self._drift_dx)
        self._sb_drift_x.setToolTip(
            "Shift up-sweep lines this many pixels along the fast axis to "
            "align them with the down sweep (0 = off)")
        bar.addWidget(self._sb_drift_x)
        bar.addWidget(QLabel("Y:"))
        self._sb_drift_y = QSpinBox()
        self._sb_drift_y.setRange(-128, 128)
        self._sb_drift_y.setValue(self._drift_dy)
        self._sb_drift_y.setToolTip(
            "Shift up-sweep lines this many rows to align them with the "
            "down sweep (0 = off)")
        bar.addWidget(self._sb_drift_y)
        for sb in (self._sb_drift_x, self._sb_drift_y):
            sb.valueChanged.connect(self._set_drift)

        self._btn_snaps = QPushButton("Compare Sweeps")
        self._btn_snaps.setMaximumWidth(110)
        self._btn_snaps.setToolTip(
            "Open a window that freezes the Err image at the end of each "
            "down sweep and each up sweep, with a recommended drift-corr "
            "X/Y computed every cycle")
        self._btn_snaps.clicked.connect(self._show_snap_window)
        bar.addWidget(self._btn_snaps)

        self._btn_save = QPushButton("Save frame")
        self._btn_save.setMaximumWidth(80)
        self._btn_save.clicked.connect(self._do_save)
        bar.addWidget(self._btn_save)

        root.addLayout(bar)

        # ---- 2x2 grid + histograms + 1D plot --------------------------------
        glw = pg.GraphicsLayoutWidget()
        root.addWidget(glw, stretch=1)

        cm = pg.colormap.get('CET-L1')

        def _img_view(row, col):
            vb = glw.addViewBox(row=row, col=col)
            vb.setAspectLocked(True)
            vb.invertY(True)
            img = pg.ImageItem()
            # Row-major: array rows (scan lines) render horizontally, the
            # fast axis along screen-X.  pyqtgraph's col-major default drew
            # the raster TRANSPOSED (lines as vertical stripes), so pixel/
            # line changes looked like height changes (bench 2026-07-15).
            img.setOpts(axisOrder='row-major')
            img.setColorMap(cm)
            vb.addItem(img)
            return vb, img

        # Z and Err panels SIDE BY SIDE (horizontal) to use the wide screen
        # instead of stacking vertically with big empty margins (operator
        # 2026-07-15): Z img | Z hist | Err img | Err hist, all in row 0.
        self._vb_zt, self._img_zt = _img_view(0, 0)
        self._hist_z = pg.HistogramLUTItem()
        glw.addItem(self._hist_z, row=0, col=1)
        self._hist_z.setImageItem(self._img_zt)
        self._hist_z.gradient.loadPreset("viridis")

        self._vb_et, self._img_et = _img_view(0, 2)
        self._hist_e = pg.HistogramLUTItem()
        glw.addItem(self._hist_e, row=0, col=3)
        self._hist_e.setImageItem(self._img_et)
        self._hist_e.gradient.loadPreset("viridis")

        # Retrace twins are OFF-SCREEN now — they were near-duplicates of
        # the trace images (bench request 2026-07-15).  The buffers still
        # update every line and 'Save frame' still writes them to disk, so
        # no data is lost; they're just not displayed.
        self._img_zr = pg.ImageItem()
        self._img_zr.setOpts(axisOrder='row-major')
        self._img_er = pg.ImageItem()
        self._img_er.setOpts(axisOrder='row-major')

        # Mirror one histogram's levels+LUT to its retrace twin.
        self._hist_z.sigLevelsChanged.connect(self._mirror_z)
        self._hist_z.sigLookupTableChanged.connect(self._mirror_z)
        self._hist_e.sigLevelsChanged.connect(self._mirror_e)
        self._hist_e.sigLookupTableChanged.connect(self._mirror_e)

        # Grabbing a level triangle switches to "No tracking" — otherwise
        # Auto/cycle re-levels seconds later and yanks the handles back
        # ("the triangles won't drag", bench 2026-07-31).  pyqtgraph 0.14
        # has no sigRegionChangeStarted, so distinguish user drags from
        # the auto-leveler's programmatic setLevels via the region/line
        # `moving` flags, which are True only during a mouse drag.
        self._hist_z.region.sigRegionChanged.connect(
            lambda r: self._user_grabbed_levels(r))
        self._hist_e.region.sigRegionChanged.connect(
            lambda r: self._user_grabbed_levels(r))

        # Z-trace 1D plot (latest line)
        self._plt_line = glw.addPlot(row=1, col=0, colspan=4)
        self._plt_line.setLabel('bottom', 'X', units='nm')
        self._plt_line.setLabel('left', 'Z', units='LSB')
        self._plt_line.setMaximumHeight(140)
        self._curve = self._plt_line.plot(pen=pg.mkPen('y', width=1))

        self._apply_physical_rects()
        self._push_all_images(auto=True)

        # Right-click anywhere in the Z viewboxes recenters the scan.
        glw.scene().sigMouseClicked.connect(self._on_scene_clicked)

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def set_scan_geometry(self, scan_size_nm: float,
                          xo_nm: float, yo_nm: float):
        self._scan_size_nm = scan_size_nm
        self._xo_nm = xo_nm
        self._yo_nm = yo_nm

    def auto_range(self):
        """Fit both image viewboxes to their content ('View All')."""
        for vb in (self._vb_zt, self._vb_et):
            vb.autoRange(padding=0.02)

    def _apply_physical_rects(self):
        """Map each image buffer onto physically-true coordinates so the
        locked aspect renders a nm equally in X and Y (no stretching).
        Units are line-heights: the frame is pixels_per_line lines tall and
        exactly as wide (the firmware scans a square, dy = dx/pixelsPerLine),
        so the half-line-resolution image spans (2*half) wide x H tall."""
        # With Y-folding, one frame = H rows covering the same physical span
        # as the half-line's `_half` columns -> square pixels (H == px/2).
        rect = pg.QtCore.QRectF(0, 0, float(self._half), float(self._H))
        for img in (self._img_zt, self._img_zr, self._img_et, self._img_er):
            img.setRect(rect)

    def resize_buffers(self, image_height: int, pixels_per_line: int):
        self._H    = image_height
        self._half = pixels_per_line // 2
        shape = (self._H, self._half)
        self._z_trace   = np.zeros(shape, dtype=np.float32)
        self._z_retrace = np.zeros(shape, dtype=np.float32)
        self._e_trace   = np.zeros(shape, dtype=np.float32)
        self._e_retrace = np.zeros(shape, dtype=np.float32)
        self._painted = np.zeros(shape[0], dtype=bool)  # rows written this scan
        self._paint_seq = np.zeros(shape[0], dtype=np.int64)
        self._paint_counter = 0
        self._pass_parity = False
        self._last_raw_row = -1
        self._apply_physical_rects()
        self._push_all_images(auto=False)
        self.auto_range()   # buffers/rects changed — refit the view

    def clear(self):
        for buf in (self._z_trace, self._z_retrace,
                    self._e_trace, self._e_retrace):
            buf[:] = 0
        self._painted[:] = False
        self._paint_seq[:] = 0
        self._push_all_images(auto=False)

    @Slot(int, object, object)
    def update_line(self, line_number: int,
                     z_arr: np.ndarray, err_arr: np.ndarray):
        # Y FOLD (corrected 2026-07-15, second iteration): dy = dx/px, so
        # ONE line-counter cycle (0..2H-1) contains a full Y triangle —
        # lines 0..H-1 ascend, lines H..2H-1 descend back over the SAME
        # physical rows.  Fold the descending half onto the ascending rows.
        # (The earlier per-cycle flip assumed one direction per cycle and
        # painted every band twice, mirrored — the operator's "accordion".)
        raw = line_number % (2 * self._H)
        wrapped = raw < self._last_raw_row
        half_done = self._last_raw_row < self._H <= raw
        # Snapshot the Err frame at the sweep boundaries BEFORE this line is
        # painted (the buffer still holds the just-completed sweep) and before
        # any autolevel, so each panel shows exactly what was on screen.
        if self._snap_win is not None and self._snap_win.isVisible():
            if half_done:
                self._take_snapshot("down")
            if wrapped:
                self._take_snapshot("up")
        if wrapped and self._rb_lvl_cycle.isChecked():
            # cycle wrapped: one full up+down Y triangle completed
            self._do_autolevel()
        self._last_raw_row = raw
        row = raw if raw < self._H else (2 * self._H - 1 - raw)
        half = self._half
        if len(z_arr) < 2 * half:
            return  # short/garbled frame; skip

        zt, zr = z_arr[:half], z_arr[half:2 * half][::-1]
        et, er = err_arr[:half], err_arr[half:2 * half][::-1]

        # Drift correction: re-target descending-half (up-sweep) lines onto
        # the ascending pass's frame of reference.  With 0/0 this block is a
        # no-op and painting is verbatim.
        if raw >= self._H:
            row -= self._drift_dy
            if not (0 <= row < self._H):
                return  # corrected row falls outside the frame; drop
            if self._drift_dx:
                zt = np.roll(zt, -self._drift_dx)
                zr = np.roll(zr, -self._drift_dx)
                et = np.roll(et, -self._drift_dx)
                er = np.roll(er, -self._drift_dx)

        self._z_trace[row, :]   = zt.astype(np.float32)
        self._z_retrace[row, :] = zr.astype(np.float32)
        self._e_trace[row, :]   = et.astype(np.float32)
        self._e_retrace[row, :] = er.astype(np.float32)
        self._painted[row] = True
        self._paint_counter += 1
        self._paint_seq[row] = self._paint_counter

        # Row-aligned display is expensive (H degree-5 polyfits per channel
        # per repaint), so with Row align on, full-image repaints cap at
        # ~10 Hz.  The buffers above always update — no data is skipped,
        # the next repaint catches up.
        now = time.monotonic()
        if (not self._chk_rowalign.isChecked()
                or now - getattr(self, "_last_repaint", 0.0) > 0.1):
            self._last_repaint = now
            self._img_zt.setImage(self._z_disp(self._z_trace), autoLevels=False)
            self._img_zr.setImage(self._z_retrace, autoLevels=False)
            self._img_et.setImage(self._e_disp(self._e_trace), autoLevels=False)
            self._img_er.setImage(self._e_display(self._e_retrace),
                                  autoLevels=False)

        # Continuous level tracking: re-level when selected — but at most
        # ~2 Hz.  _do_autolevel row-aligns both channels (H polyfits each)
        # since the displayed-data fix; per-line at scan line rates that
        # saturated the GUI thread (freeze: Continuous + Row align + CC,
        # 2026-07-31).
        if self._rb_lvl_cont.isChecked():
            now = time.monotonic()
            if now - getattr(self, "_last_autolevel", 0.0) > 0.5:
                self._last_autolevel = now
                self._do_autolevel(recent=True)

        # 1D Z-trace of the most recent line, x-axis in nm.
        x_nm = np.linspace(0.0, self._scan_size_nm, half)
        self._curve.setData(x_nm, z_arr[:half])

    # -------------------------------------------------------------------------
    # Internal
    # -------------------------------------------------------------------------

    def _set_drift(self):
        self._drift_dx = self._sb_drift_x.value()
        self._drift_dy = self._sb_drift_y.value()
        self._settings.setValue("drift_corr_x", self._drift_dx)
        self._settings.setValue("drift_corr_y", self._drift_dy)

    def _show_snap_window(self):
        if self._snap_win is None:
            self._snap_win = SweepSnapshotWindow()
        self._snap_win.show()
        self._snap_win.raise_()

    def _take_snapshot(self, key):
        arr = np.array(self._e_disp(self._e_trace), copy=True)
        self._snap_win.take(
            key, arr,
            self._hist_e.getLevels(),
            self._hist_e.gradient.getLookupTable(512))
        # Once per cycle (at the up capture) compute the residual shift
        # between the two corrected panels; the recommendation is absolute:
        # current spin values + residual, so "dialed in" reads back your
        # own settings.
        if key == "down":
            self._snap_down = arr
        elif (getattr(self, "_snap_down", None) is not None
                and self._snap_down.shape == arr.shape):
            dx, dy, r = _sweep_residual(self._snap_down, arr)
            self._snap_win.set_recommendation(
                self._drift_dx + dx, self._drift_dy + dy, r)

    def _row_align_changed(self, *_):
        self._settings.setValue(
            "row_align_on",
            "true" if self._chk_rowalign.isChecked() else "false")
        self._settings.setValue(
            "row_align_method", self._cmb_rowalign.currentText())
        self._push_all_images(auto=True)

    def row_align_params(self):
        """(enabled, method) — read by the superscan build in main.py."""
        return (self._chk_rowalign.isChecked(),
                self._cmb_rowalign.currentText())

    def _z_disp(self, arr):
        if self._chk_rowalign.isChecked():
            return _row_align(arr, self._cmb_rowalign.currentText())
        return arr

    def _e_disp(self, arr):
        a = self._e_display(arr)
        if self._chk_rowalign.isChecked():
            a = _row_align(a, self._cmb_rowalign.currentText())
        return a

    def _push_all_images(self, auto: bool):
        self._img_zt.setImage(self._z_disp(self._z_trace), autoLevels=auto)
        self._img_zr.setImage(self._z_retrace, autoLevels=auto)
        self._img_et.setImage(self._e_disp(self._e_trace), autoLevels=auto)
        self._img_er.setImage(self._e_display(self._e_retrace), autoLevels=auto)

    def _user_grabbed_levels(self, region):
        """A histogram level triangle is being dragged by the mouse: go
        manual so the auto-leveler stops fighting the user's hands.
        `moving` is True only during mouse drags — programmatic
        setLevels (the auto-leveler) never sets it."""
        dragging = getattr(region, "moving", False) or any(
            getattr(ln, "moving", False)
            for ln in getattr(region, "lines", ()))
        if dragging and not self._rb_lvl_off.isChecked():
            self._rb_lvl_off.setChecked(True)
            print("[RASTER] histogram handle grabbed - level tracking off")

    def _on_lvl_mode_changed(self, manual: bool):
        """No-tracking mode: freeze histogram view ranges so zoom sticks;
        auto modes: give the ranges back to pyqtgraph."""
        for hist in (self._hist_z, self._hist_e):
            try:
                if manual:
                    hist.vb.disableAutoRange()
                else:
                    hist.vb.enableAutoRange()
            except Exception:
                pass  # pyqtgraph internals moved; never break the raster

    def _mirror_z(self):
        lo, hi = self._hist_z.getLevels()
        self._img_zr.setLevels((lo, hi))
        self._img_zr.setLookupTable(self._hist_z.gradient.getLookupTable(512))

    def _mirror_e(self):
        lo, hi = self._hist_e.getLevels()
        self._img_er.setLevels((lo, hi))
        self._img_er.setLookupTable(self._hist_e.gradient.getLookupTable(512))

    def _on_scene_clicked(self, ev):
        if ev.button() != 2:  # right button only
            return
        sp = ev.scenePos()
        for vb, is_z in ((self._vb_zt, True),):
            if not vb.sceneBoundingRect().contains(sp):
                continue
            pt = vb.mapSceneToView(sp)
            px, py = pt.x(), pt.y()
            # View coords are physical rect units (width 2*half, height H)
            # → fraction of scan, centered on current offset.
            frac_x = (px / (2 * self._half)) - 0.5
            frac_y = (py / self._H) - 0.5
            new_xo = self._xo_nm + frac_x * self._scan_size_nm
            new_yo = self._yo_nm + frac_y * self._scan_size_nm
            self.scanOffsetRequested.emit(new_xo, new_yo)
            return

    # -------------------------------------------------------------------------
    # Buttons
    # -------------------------------------------------------------------------

    def _do_autolevel(self, recent=False):
        # Level on exactly what the images DISPLAY (row-align included).
        # Leveling the raw buffer while the view showed row-aligned data
        # put the window tens of thousands of counts off the visible
        # histogram whenever CC held Z at a big DC value (bench bug,
        # 2026-07-31).  Also skip rows not yet painted this scan — their
        # allocation zeros drag the percentiles toward 0.
        zd = self._z_disp(self._z_trace)
        ed = self._e_disp(self._e_trace)
        painted = getattr(self, "_painted", None)
        # Continuous mode levels on the most RECENT quarter of painted
        # rows: with CC tracking drift, old rows sit hundreds of counts
        # away, and a full-frame percentile spans the drift ramp — the
        # live rows then all clip to one end (solid-yellow Z map, bench
        # 2026-07-31).
        if recent and painted is not None and painted.any():
            seq = self._paint_seq
            thr = np.percentile(seq[painted], 75)
            mask = painted & (seq >= thr)
            if mask.sum() >= 4:
                painted = mask
        if painted is not None and painted.any() and not painted.all():
            zd, ed = zd[painted], ed[painted]
        lo_z, hi_z = np.percentile(zd, [2, 98])
        lo_e, hi_e = np.percentile(ed, [2, 98])
        self._hist_z.setLevels(float(lo_z), float(hi_z))
        self._hist_e.setLevels(float(lo_e), float(hi_e))

    def _do_save(self):
        # Convention, always: frames go to today's centralized data folder.
        # (Operator decision 2026-07-26 — no folder picking; the sticky
        # QSettings target is how the stray 'Saved' folder happened.)
        folder = data_paths.day_dir()

        ts   = datetime.now().strftime("%Y%m%d_%H%M%S") + session_journal.tag()
        base = self._settings.value("save/basename", "scan", type=str)

        tifffile.imwrite(f"{folder}/{base}_z_trace_{ts}.tiff",     self._z_trace)
        tifffile.imwrite(f"{folder}/{base}_z_retrace_{ts}.tiff",   self._z_retrace)
        tifffile.imwrite(f"{folder}/{base}_err_trace_{ts}.tiff",   self._e_trace)
        tifffile.imwrite(f"{folder}/{base}_err_retrace_{ts}.tiff", self._e_retrace)

        # Raw binary: per row, uint16 line + int32 z[W] + int32 err[W] (trace).
        with open(f"{folder}/{base}_raw_{ts}.bin", 'wb') as fh:
            for row in range(self._H):
                fh.write(row.to_bytes(2, 'little'))
                self._z_trace[row].astype('<f4').tofile(fh)
                self._e_trace[row].astype('<f4').tofile(fh)

        print(f"[LiveRaster] saved to {folder}/{base}_*_{ts}.*")
