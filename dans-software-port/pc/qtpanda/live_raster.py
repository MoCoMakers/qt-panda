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

        self._build_ui()

    # -------------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(3)

        # ---- Top control bar -------------------------------------------------
        bar = QHBoxLayout()
        bar.setSpacing(6)
        bar.addWidget(QLabel("Z: topography (trace | retrace)   "
                             "Err: current error (trace | retrace)"))
        bar.addStretch()

        self._btn_autolevel = QPushButton("Auto levels")
        self._btn_autolevel.setMaximumWidth(90)
        self._btn_autolevel.clicked.connect(self._do_autolevel)
        bar.addWidget(self._btn_autolevel)

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
            img.setColorMap(cm)
            vb.addItem(img)
            return vb, img

        self._vb_zt, self._img_zt = _img_view(0, 0)
        self._vb_zr, self._img_zr = _img_view(0, 1)
        self._hist_z = pg.HistogramLUTItem()
        glw.addItem(self._hist_z, row=0, col=2)
        self._hist_z.setImageItem(self._img_zt)
        self._hist_z.gradient.loadPreset("viridis")

        self._vb_et, self._img_et = _img_view(1, 0)
        self._vb_er, self._img_er = _img_view(1, 1)
        self._hist_e = pg.HistogramLUTItem()
        glw.addItem(self._hist_e, row=1, col=2)
        self._hist_e.setImageItem(self._img_et)
        self._hist_e.gradient.loadPreset("viridis")

        # Mirror one histogram's levels+LUT to its retrace twin.
        self._hist_z.sigLevelsChanged.connect(self._mirror_z)
        self._hist_z.sigLookupTableChanged.connect(self._mirror_z)
        self._hist_e.sigLevelsChanged.connect(self._mirror_e)
        self._hist_e.sigLookupTableChanged.connect(self._mirror_e)

        # Z-trace 1D plot (latest line)
        self._plt_line = glw.addPlot(row=2, col=0, colspan=3)
        self._plt_line.setLabel('bottom', 'X', units='nm')
        self._plt_line.setLabel('left', 'Z', units='LSB')
        self._plt_line.setMaximumHeight(140)
        self._curve = self._plt_line.plot(pen=pg.mkPen('y', width=1))

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

    def resize_buffers(self, image_height: int, pixels_per_line: int):
        self._H    = image_height
        self._half = pixels_per_line // 2
        shape = (self._H, self._half)
        self._z_trace   = np.zeros(shape, dtype=np.float32)
        self._z_retrace = np.zeros(shape, dtype=np.float32)
        self._e_trace   = np.zeros(shape, dtype=np.float32)
        self._e_retrace = np.zeros(shape, dtype=np.float32)
        self._push_all_images(auto=False)

    def clear(self):
        for buf in (self._z_trace, self._z_retrace,
                    self._e_trace, self._e_retrace):
            buf[:] = 0
        self._push_all_images(auto=False)

    @Slot(int, object, object)
    def update_line(self, line_number: int,
                     z_arr: np.ndarray, err_arr: np.ndarray):
        row  = line_number % self._H
        half = self._half
        if len(z_arr) < 2 * half:
            return  # short/garbled frame; skip

        self._z_trace[row, :]   = z_arr[:half].astype(np.float32)
        self._z_retrace[row, :] = z_arr[half:2 * half][::-1].astype(np.float32)
        self._e_trace[row, :]   = err_arr[:half].astype(np.float32)
        self._e_retrace[row, :] = err_arr[half:2 * half][::-1].astype(np.float32)

        self._img_zt.setImage(self._z_trace,   autoLevels=False)
        self._img_zr.setImage(self._z_retrace, autoLevels=False)
        self._img_et.setImage(self._e_trace,   autoLevels=False)
        self._img_er.setImage(self._e_retrace, autoLevels=False)

        # 1D Z-trace of the most recent line, x-axis in nm.
        x_nm = np.linspace(0.0, self._scan_size_nm, half)
        self._curve.setData(x_nm, z_arr[:half])

    # -------------------------------------------------------------------------
    # Internal
    # -------------------------------------------------------------------------

    def _push_all_images(self, auto: bool):
        self._img_zt.setImage(self._z_trace,   autoLevels=auto)
        self._img_zr.setImage(self._z_retrace, autoLevels=auto)
        self._img_et.setImage(self._e_trace,   autoLevels=auto)
        self._img_er.setImage(self._e_retrace, autoLevels=auto)

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
        for vb, is_z in ((self._vb_zt, True), (self._vb_zr, True)):
            if not vb.sceneBoundingRect().contains(sp):
                continue
            pt = vb.mapSceneToView(sp)
            px, py = pt.x(), pt.y()
            # Image pixel → fraction of scan, centered on current offset.
            frac_x = (px / self._half) - 0.5
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
        lo_e, hi_e = np.percentile(self._e_trace, [2, 98])
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
