import math
import os
import numpy as np
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog
)
from PySide6.QtCore import Slot, Signal, QSettings
import pyqtgraph as pg
import tifffile


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

        self._btn_folder = QPushButton("Change folder…")
        self._btn_folder.setMaximumWidth(110)
        self._btn_folder.clicked.connect(self._choose_folder)
        bar.addWidget(self._btn_folder)

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
        self._pass_parity = False
        self._last_raw_row = -1
        self._apply_physical_rects()
        self._push_all_images(auto=False)
        self.auto_range()   # buffers/rects changed — refit the view

    def clear(self):
        for buf in (self._z_trace, self._z_retrace,
                    self._e_trace, self._e_retrace):
            buf[:] = 0
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
        if raw < self._last_raw_row and self._rb_lvl_cycle.isChecked():
            # cycle wrapped: one full up+down Y triangle completed
            self._do_autolevel()
        self._last_raw_row = raw
        row = raw if raw < self._H else (2 * self._H - 1 - raw)
        half = self._half
        if len(z_arr) < 2 * half:
            return  # short/garbled frame; skip

        self._z_trace[row, :]   = z_arr[:half].astype(np.float32)
        self._z_retrace[row, :] = z_arr[half:2 * half][::-1].astype(np.float32)
        self._e_trace[row, :]   = err_arr[:half].astype(np.float32)
        self._e_retrace[row, :] = err_arr[half:2 * half][::-1].astype(np.float32)

        self._img_zt.setImage(self._z_trace,   autoLevels=False)
        self._img_zr.setImage(self._z_retrace, autoLevels=False)
        self._img_et.setImage(self._e_display(self._e_trace),   autoLevels=False)
        self._img_er.setImage(self._e_display(self._e_retrace), autoLevels=False)

        # Continuous level tracking: re-level every line when selected.
        if self._rb_lvl_cont.isChecked():
            self._do_autolevel()

        # 1D Z-trace of the most recent line, x-axis in nm.
        x_nm = np.linspace(0.0, self._scan_size_nm, half)
        self._curve.setData(x_nm, z_arr[:half])

    # -------------------------------------------------------------------------
    # Internal
    # -------------------------------------------------------------------------

    def _push_all_images(self, auto: bool):
        self._img_zt.setImage(self._z_trace,   autoLevels=auto)
        self._img_zr.setImage(self._z_retrace, autoLevels=auto)
        self._img_et.setImage(self._e_display(self._e_trace),   autoLevels=auto)
        self._img_er.setImage(self._e_display(self._e_retrace), autoLevels=auto)

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

    def _do_autolevel(self):
        lo_z, hi_z = np.percentile(self._z_trace, [2, 98])
        lo_e, hi_e = np.percentile(self._e_display(self._e_trace), [2, 98])
        self._hist_z.setLevels(float(lo_z), float(hi_z))
        self._hist_e.setLevels(float(lo_e), float(hi_e))

    def _saved_folder(self) -> str:
        return self._settings.value("save/folder", "", type=str)

    def _choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Save frames to…")
        if folder:
            self._settings.setValue("save/folder", folder)

    def _do_save(self):
        folder = self._saved_folder()
        if not folder or not os.path.isdir(folder):
            self._choose_folder()
            folder = self._saved_folder()
        if not folder:
            return

        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
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
