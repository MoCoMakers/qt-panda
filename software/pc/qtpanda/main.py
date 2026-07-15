# This Python file uses the following encoding: utf-8


import sys
from PySide6 import QtCore, QtGui

# MUST be before QApplication AND before any Qt widgets import
QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_UseDesktopOpenGL)

fmt = QtGui.QSurfaceFormat()
fmt.setVersion(2, 1)
fmt.setProfile(QtGui.QSurfaceFormat.CompatibilityProfile)
fmt.setDepthBufferSize(24)
QtGui.QSurfaceFormat.setDefaultFormat(fmt)

from PySide6.QtWidgets import QApplication
from PySide6 import QtWidgets, QtCore, QtGui

import plotframe
from datetime import datetime
import numpy as np
import stm_control
import stab_metrics
import time
import csv
import json
import threading
import pyqtgraph as pg
import STMBoxWidget
import GridSpectroWorker
from PySide6.QtCore import Slot, QTimer, QSettings, Qt
from PySide6.QtWidgets import (QApplication,  QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSizePolicy,
    QSpacerItem, QSpinBox, QTabWidget, QVBoxLayout,
    QWidget, QDoubleSpinBox, QGroupBox, QFormLayout,
    QComboBox, QProgressBar, QGridLayout, QSlider)
import serial.tools.list_ports
import calibration
from ui_form import Ui_Widget
import os
import logging
from qt_log_handler import QtLogHandler
import tifffile
import gwyfile
from gwyfile.objects import GwyContainer
from PySide6.QtCore import QObject, QThread, Signal
from PySide6 import QtCore
from PySide6 import QtWidgets, QtCore, QtGui

from PySide6.QtOpenGLWidgets import QOpenGLWidget
print("OpenGL widget import OK")

import scan_controller
import live_raster
import stab_runner
import session_journal
import frame_logger
import raw_logger
import status_logger
import drift_hold
import dac_restore
import superscan
from collections import deque

os.makedirs("./images", exist_ok=True)
print("Profile:",
      QtGui.QSurfaceFormat.defaultFormat().profile())

class Widget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        self.setWindowTitle("Moco Makers Lab STM")
        # ----------------------
        # STM Interface
        # ----------------------
        self.stm = stm_control.STM()

        # ----------------------
        # Setup Plots
        # ----------------------
        self.pltCurrent = plotframe.PlotFrame()
        layout = QVBoxLayout(self.ui.pltCurrent)
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.pltCurrent)

        self.pltSteps = plotframe.PlotFrame()
        layout1 = QVBoxLayout(self.ui.pltSteps)
        layout1.setContentsMargins(0,0,0,0)
        layout1.addWidget(self.pltSteps)

        self.pltIV = plotframe.PlotFrame()
        layout2 = QVBoxLayout(self.ui.pltIV)
        layout2.setContentsMargins(0,0,0,0)
        layout2.addWidget(self.pltIV)

        self.pltdIdV = plotframe.PlotFrame()
        layout6 = QVBoxLayout(self.ui.pltdIdV)
        layout6.setContentsMargins(0,0,0,0)
        layout6.addWidget(self.pltdIdV)

        self.pltDAC = plotframe.PlotFrame()
        layout3 = QVBoxLayout(self.ui.pltDAC)
        layout3.setContentsMargins(0,0,0,0)
        layout3.addWidget(self.pltDAC)

        self.pltVals = plotframe.PlotFrame()
        layout4 = QVBoxLayout(self.ui.pltVals)
        layout4.setContentsMargins(0,0,0,0)
        layout4.addWidget(self.pltVals)

        self.pltdIdZ = plotframe.PlotFrame()
        layout5 = QVBoxLayout(self.ui.pltdIdZ)
        layout5.setContentsMargins(0,0,0,0)
        layout5.addWidget(self.pltdIdZ)

        self.pltGridImage = plotframe.PlotFrame()
        layout7 = QVBoxLayout(self.ui.pltGridImage)
        layout7.setContentsMargins(0,0,0,0)
        layout7.addWidget(self.pltGridImage)

        self.pltGridChart = plotframe.PlotFrame()
        layout8 = QVBoxLayout(self.ui.pltGridChart)
        layout8.setContentsMargins(0,0,0,0)
        layout8.addWidget(self.pltGridChart)

        self.pltNoise = plotframe.PlotFrame()
        layout9 = QVBoxLayout(self.ui.pltNoise)
        layout9.setContentsMargins(0,0,0,0)
        layout9.addWidget(self.pltNoise)



        # initialize scan images
        init_img = np.random.rand(10, 10)
        self.pltDAC.add_image(init_img,label = "DAC Values")
        self.pltVals.add_image(init_img,label = "ADC Values")
        self.pltNoise.add_image(init_img,label = "Noise Values")
        self.pltGridImage.add_image(init_img, label="dI/dV & dI/dZ")

        # Create pens
        red_pen = pg.mkPen("r", width=3)
        green_pen = pg.mkPen("g", width=3)
        blue_pen = pg.mkPen("b", width=3)

        # Create plots with pens
        self.pltCurrent.add_plot("Current", "time(s)", "amp", pen=red_pen)
        self.pltSteps.add_plot("Steps", "time(s)", "steps", pen=green_pen)
        self.pltIV.add_plot("IV Curve", "Bias", "Current", pen=blue_pen)
        self.pltdIdV.add_plot("dIdV Curve", "Bias", "Current", pen=green_pen)
        self.pltdIdZ.add_plot("dIdZ Curve", "Z", "Current", pen=blue_pen)
        self.pltGridChart.add_plot("dIdV dIdZ ", "Bias", "Current", pen=blue_pen)


        #self.pltVals.add_surface3d()

        self.wgtscanctl = STMBoxWidget.STMBoxWidget()
        layout5 = QVBoxLayout(self.ui.wgtscanctl)
        layout5.setContentsMargins(0,0,0,0)
        layout5.addWidget(self.wgtscanctl)

        self.wgtscanctl.boxChanged.connect(self.on_scan_box_changed)
        self.wgtscanctl.show()

        #self.ui.pltVals3d.setVisible(False);

        # ----------------------
        # Timer Updates
        # ----------------------

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_real_time)
        self.timer.start(100)

        self.image_timer = QTimer()
        self.image_timer.timeout.connect(self.update_images)
        self.image_timer.start(100)

        # ----------------------
        # Log Handling
        # ----------------------

        self.qt_log_handler = QtLogHandler()
        formatter = logging.Formatter(
            "%(asctime)s  %(message)s",
            datefmt="%H:%M:%S"
        )
        self.qt_log_handler.setFormatter(formatter)
        logging.getLogger("stm").addHandler(self.qt_log_handler)
        self.qt_log_handler.log_signal.connect(self.append_log)

        # ----------------------
        # Shared state: calibration model + persistent settings
        # ----------------------
        self._settings = QSettings("qt-panda", "dans-port")
        self._cal = calibration.Calibration.from_json()
        self._cal.changed.connect(self._on_calibration_changed)

        # ----------------------
        # Continuous-scan + Calibration tabs (Dan-style)
        # ----------------------
        self._scan_ctrl = scan_controller.ScanController(
            self.stm, self._cal, parent=self)
        self._build_continuous_scan_tab()
        self._build_calibration_tab()

        # Main-tab layout: restructure the 2x2 grid into two columns so the
        # scan image (right, tall) and the live current scroll (top-left)
        # get real vertical height instead of a cramped half-row each
        # (operator 2026-07-15).  Reparent the existing plot containers —
        # never regenerate ui_form.
        from PySide6.QtWidgets import QSplitter as _QSp
        _left = _QSp(Qt.Vertical)
        _left.addWidget(self.ui.pltCurrent)   # live current scroll (top)
        _left.addWidget(self.ui.pltSteps)     # steps (below)
        _left.setSizes([600, 300])
        _right = _QSp(Qt.Vertical)
        _right.addWidget(self.ui.pltVals)     # scan ADC image (dominant)
        _right.addWidget(self.ui.pltDAC)      # DAC-Z image (small)
        _right.setSizes([680, 220])
        _main = _QSp(Qt.Horizontal)
        _main.addWidget(_left)
        _main.addWidget(_right)
        _main.setSizes([460, 560])
        self.ui.verticalLayout_7.insertWidget(0, _main, 1)
        self.ui.splitter_3.setParent(None)    # retire the old 2x2 splitter

        # Main-tab shortcuts to the scan raster's actions (bench request
        # 2026-07-15) — same buttons as on the Continuous Scan tab.
        self._btn_main_autolevel = QPushButton("Auto Levels",
                                               self.ui.wgtAutoLevels)
        self._btn_main_autolevel.clicked.connect(self._main_auto_levels)
        self._btn_main_save = QPushButton("Save Frame",
                                          self.ui.wgtAutoLevels)
        self._btn_main_save.clicked.connect(self._cs_raster._do_save)
        self.ui.horizontalLayout_12.insertWidget(0, self._btn_main_autolevel)
        self.ui.horizontalLayout_12.insertWidget(1, self._btn_main_save)

        # Preamp gain selector (operator-set; NOT a code magic number).
        # At NX gain the same current gives N× the ADC counts, so the
        # current conversion divides by this.  Persisted across sessions.
        from PySide6.QtWidgets import QComboBox as _QCB
        self._preamp_gain = _QCB()
        for label, g in (("1X", 1.0), ("5X", 5.0)):
            self._preamp_gain.addItem(f"Preamp {label}", g)
        saved_g = float(self._settings.value("preamp/gain", 1.0, type=float))
        gi = 1 if abs(saved_g - 5.0) < 0.1 else 0
        self._preamp_gain.setCurrentIndex(gi)
        stm_control.STM_Status.preamp_gain = self._preamp_gain.currentData()
        self._preamp_gain.currentIndexChanged.connect(self._on_preamp_gain)
        # Sits on the bias-controls row, right of Set Bias.
        self.ui.horizontalLayout_3.addWidget(self._preamp_gain)

        # Operator-set startup defaults (2026-07-15) — overriding the
        # ui_form values here rather than regenerating the .ui.
        self.ui.spnMot.setValue(5)          # motor Retract/Approach amount
        self.ui.spnMot.setSingleStep(5)     # arrows step by 5, not 1
        self.ui.leTargetDAC.setText("20")   # Auto Approach current threshold
        self.ui.leSamples.setText("3")      # Scanning-tab Samples/Pix

        # Context-aware Info button in the tab-bar corner: shows plain-
        # language help for the current tab (hidden on Main / Continuous
        # Scan).  One button, adapts per tab (operator 2026-07-15).
        import tab_help
        self._tab_help = tab_help
        self._btn_tabinfo = QPushButton("ⓘ Info")
        self._btn_tabinfo.clicked.connect(self._show_tab_info)
        self.ui.tabWidget.setCornerWidget(self._btn_tabinfo, Qt.TopRightCorner)
        self.ui.tabWidget.currentChanged.connect(self._update_tab_info_btn)
        self._update_tab_info_btn(self.ui.tabWidget.currentIndex())

        # Swap the free-text port field for an enumerated combo + Refresh
        self._install_port_combo()
        self._refresh_ports()
        last_port = self._settings.value("serial/port", "", type=str)
        if last_port:
            idx = self.ui.lePort.findText(last_port)
            if idx >= 0:
                self.ui.lePort.setCurrentIndex(idx)

        # ----------------------
        # Stability Histogram
        # ----------------------
        # NOTE: samples only accumulate while self.stm.history is being
        # populated by GSTS polling, i.e. NOT while the continuous-scan
        # reader owns the serial port (see update_real_time's early-out).
        # That's the intended use case: monitoring drift while idle /
        # holding position, not mid-raster.
        self.stab_samples = []        # accumulated current samples (amps)
        self.stab_times = []          # parallel time_millis for each sample
        self.stab_running = False     # is the stream being recorded?
        self.stab_last_t = None       # last consumed status time_millis
        self.stab_t0 = None           # time_millis of first logged sample
        self.stab_log_file = None     # open CSV file handle while recording
        self.stab_log_writer = None   # csv.writer bound to stab_log_file
        self.stab_log_path = None     # path of the current log file
        self._stab_reader = None      # SerialReaderThread while streaming
        self._stab_streaming = False  # True when STRM push mode owns the port
        self._stab_stream_frames = 0  # frames received (stream watchdog)
        self._raw_logger = raw_logger.RawLogger(log_dir="raw")
        self._raw_reader = None       # dedicated reader if nothing else runs
        self._raw_decim = 0
        self.build_stability_tab()
        self.timer.timeout.connect(self.update_stability)
        # Recording service (independent of the viewer above): a dedicated
        # writer thread fed straight from the serial-reader thread, so the
        # GUI is never in the data path (true-time requirement 2026-07-14).
        # update_recording on the GUI timer is only the old-firmware
        # fallback when no push stream exists.
        self._status_logger = status_logger.StatusLogger(
            stm_control.STM_Status.adc_to_amp)
        self._rec_last_t = None
        self._recording = False
        self.timer.timeout.connect(self.update_recording)

        # Z drag-bar send throttle (real-time DACZ while dragging).
        self._dacz_pending = None
        self._dacz_send_timer = QTimer(self)
        self._dacz_send_timer.setSingleShot(True)
        self._dacz_send_timer.timeout.connect(self._send_pending_dacz)

        # Log pane: bounded scrollback (viewer, not record).
        self.ui.txtLog.document().setMaximumBlockCount(400)

        # One-state principle (operator 2026-07-15): firmware is the single
        # source of truth for Z/bias/X/Y; every widget mirrors it unless the
        # operator is actively composing an edit (focus/drag/3 s grace).
        self._mirror_updating = False
        self._dac_edit_t = 0.0
        for _sp in (self.ui.spnDACZ, self.ui.spnBias,
                    self.ui.spnDACX, self.ui.spnDACY):
            _sp.valueChanged.connect(self._mark_dac_edit)

        # Red-box <-> Continuous Scan geometry sync (nm authoritative).
        self._box_sync = False
        self._cs_geom_timer = QTimer(self)
        self._cs_geom_timer.setSingleShot(True)
        self._cs_geom_timer.timeout.connect(self._push_cs_geometry)

        # Legacy-op recovery watchdog: legacy synchronous ops silence the
        # 200 Hz recording stream and nothing used to re-arm it (bench
        # 2026-07-14: Stability Start after a Noise Scan showed "nothing
        # happening" — the feed was down to the 9 Hz poll).  Re-arm once
        # the port has been quiet for two consecutive checks.
        self._rearm_quiet = 0
        self._rearm_timer = QTimer(self)
        self._rearm_timer.timeout.connect(self._rearm_stream_check)
        self._rearm_timer.start(2000)

        # Persist the DACX/DACY operating point every 30 s (low-frequency
        # QSettings writes only) so the next launch can restore it — Matt
        # 2026-07-15: "at boot it should set to the near-zero [volt] values
        # we had before."  Z/bias are deliberately NOT persisted (see
        # dac_restore.py).
        self._dac_save_timer = QTimer(self)
        self._dac_save_timer.timeout.connect(self._save_dac_xy)
        self._dac_save_timer.start(30000)

        # ----------------------
        # Fourier Analysis (populated when Stability recording is Stopped)
        # ----------------------
        self.build_fourier_tab()


    # ----------------------
    # Custom Box control
    # ----------------------
    def on_scan_box_changed(self, box):
        x, y, w, h = box
        x_start = x
        x_end = x + w
        y_start = y
        y_end = y + h

        widgets = [
            self.ui.leXStart,
            self.ui.leXEnd,
            self.ui.leYStart,
            self.ui.leYEnd
        ]

        for w in widgets:
            w.blockSignals(True)

        self.ui.leXStart.setText(str(x_start))
        self.ui.leXEnd.setText(str(x_end))
        self.ui.leYStart.setText(str(y_start))
        self.ui.leYEnd.setText(str(y_end))

        for w in widgets:
            w.blockSignals(False)

        # Cohesion: the red rectangle is the shared truth for scan
        # geometry — mirror it into the Continuous Scan controls too
        # (nm units; continuous scans are square, so the box WIDTH rules).
        # Guarded against sync loops with _box_sync; if a continuous scan
        # is running the new geometry is pushed live (throttled).
        if not getattr(self, "_box_sync", False) \
                and getattr(self, "_cs_scansize", None) is not None:
            self._box_sync = True
            try:
                nm_per_lsb = (self._cal.dac_x_v_per_lsb
                              * self._cal.piezo_x_nm_per_v)
                width = x_end - x_start
                self._cs_scansize.setValue(width * nm_per_lsb)
                self._cs_xofs.setValue(
                    ((x_start + x_end) / 2.0 - 32768) * nm_per_lsb)
                self._cs_yofs.setValue(
                    ((y_start + y_end) / 2.0 - 32768) * nm_per_lsb)
                if self._scan_ctrl.is_running():
                    self._arm_cs_geometry_push()
            finally:
                self._box_sync = False


    def _arm_cs_geometry_push(self):
        """Coalesce live geometry pushes while dragging the red box —
        newest value wins, sent at most every 150 ms (same pattern as the
        Z drag bar's throttle)."""
        if not self._cs_geom_timer.isActive():
            self._cs_geom_timer.start(150)

    def _push_cs_geometry(self):
        sc = self._scan_ctrl
        sc.set_scan_size(self._cs_scansize.value())
        sc.set_offsets(self._cs_xofs.value(), self._cs_yofs.value())
        self._cs_raster.set_scan_geometry(self._cs_scansize.value(),
                                          self._cs_xofs.value(),
                                          self._cs_yofs.value())

    def _update_box_from_cs(self):
        """Continuous Scan spinboxes -> red rectangle.  The nm values stay
        authoritative (typing '1 nm' is exact); the box is a live mirror."""
        if getattr(self, "_box_sync", False):
            return
        self._box_sync = True
        try:
            nm_per_lsb = (self._cal.dac_x_v_per_lsb
                          * self._cal.piezo_x_nm_per_v)
            span = max(1, int(round(self._cs_scansize.value() / nm_per_lsb)))
            span = min(span, 65535)
            cx = 32768 + self._cs_xofs.value() / nm_per_lsb
            cy = 32768 + self._cs_yofs.value() / nm_per_lsb
            x = int(round(cx - span / 2.0))
            y = int(round(cy - span / 2.0))
            x = max(0, min(65535 - span, x))
            y = max(0, min(65535 - span, y))
            self.wgtscanctl.SetValues(x, y, span, span)
            if self._scan_ctrl.is_running():
                self._arm_cs_geometry_push()
        finally:
            self._box_sync = False

    @Slot() #need to hook up these line edit boxes to change the values of the stmBoxWidget
    def on_leXStart_editingFinished(self):
        self.UpdateBoxFromText()

    @Slot()
    def on_leYStart_editingFinished(self):
        self.UpdateBoxFromText()

    @Slot()
    def on_leXEnd_editingFinished(self):
        self.UpdateBoxFromText()

    @Slot()
    def on_leYEnd_editingFinished(self):
        self.UpdateBoxFromText()

    def UpdateBoxFromText(self):
        x = int(self.ui.leXStart.text())
        y = int(self.ui.leYStart.text())
        w = int(self.ui.leXEnd.text()) - x
        h = int(self.ui.leYEnd.text()) -y
        self.wgtscanctl.SetValues(x,y,w,h)
    # ----------------------
    # Button Handlers
    # ----------------------

    @Slot()
    def on_cmdNoiseScan_clicked(self):
        self._halt_continuous_if_running()
        xres = self.ui.spnNoiseX.value()
        yres = self.ui.spnNoiseY.value()
        samples = self.ui.spnNoiseSamples.value()
        uS = self.ui.spnNoiseDelay.value()
        #self.stm.start_noise_scan(xres,yres,samples,uS)
        threading.Thread(
            target=self.stm.start_noise_scan,
            args=(xres,yres,samples,uS),
            daemon=True
        ).start()

    @Slot()
    def on_cmdSettle_clicked(self):
        xsettle = self.ui.spnXSettle.value()
        ysettle = self.ui.spnYSettle.value()
        zsettle = self.ui.spnZSettle.value()
        biassettle = self.ui.spnBiasSettle.value()
        print("[CMD] SETL")
        print(f"  X: {xsettle}")
        print(f"  Y: {ysettle}")
        print(f"  Z: {zsettle}")
        print(f"  Bias: {biassettle}")
        self.stm.set_settle(xsettle,ysettle,zsettle,biassettle)


    @Slot()
    def on_cmdGridSpectro_clicked(self):
        self._halt_continuous_if_running()

        xs = int(self.ui.leXStart.text())
        ys = int(self.ui.leYStart.text())
        xe = int(self.ui.leXEnd.text())
        ye = int(self.ui.leYEnd.text())
        xr = int(self.ui.leXRes.text())
        yr = int(self.ui.leYRes.text())

        bias_start = int(self.ui.leGridBiasStart.text())
        bias_end = int(self.ui.leGridBiasEnd.text())
        bias_points = int(self.ui.leGridBiasPoints.text())

        mode = self.ui.cmbGridSpectChoice.currentIndex()

        print("[CMD] GRID SPECTRO")
        print(f"  X: {xs}->{xe}  res={xr}")
        print(f"  Y: {ys}->{ye}  res={yr}")
        print(f"  Bias: {bias_start}->{bias_end}  points={bias_points}")
        print(f"  Mode: {mode}")

        params = (
            xs, xe, xr,
            ys, ye, yr,
            bias_start, bias_end,
            bias_points,
            mode
        )

        self.thread = QThread()
        self.worker = GridSpectroWorker.GridSpectroWorker(self.stm, params)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self._update_progress)
        self.worker.finished.connect(self._grid_finished)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def _update_progress(self, value):
        self.ui.progressBar.setValue(value)

    def _grid_finished(self, grid):

        self.grid_cube = grid
        print("Scan complete")
        if self.grid_cube is None:
            print("No grid data returned")
            return
        # Expect shape (xr, yr, bias_points)
        print("Grid shape:", self.grid_cube.shape)
        # --------------------------------------------------
        # Configure slider
        # --------------------------------------------------
        bias_points = int(self.ui.leGridBiasPoints.text())
        self.ui.sldGridBias.setMinimum(0)
        self.ui.sldGridBias.setMaximum(bias_points - 1)
        self.ui.sldGridBias.setValue(0)

        # Display first slice
        self.pltGridImage.update_image(grid[:, :, 0].T)#, autoLevels=True)
        # --------------------------------------------------
        # Connect slider (only connect once ideally)
        # --------------------------------------------------
        try:
            self.ui.sldGridBias.valueChanged.disconnect()
        except:
            pass

        self.ui.sldGridBias.valueChanged.connect(self._update_grid_slice)

        # --------------------------------------------------
        # Connect click on image
        # --------------------------------------------------
        try:
            self.pltGridImage.graphics.scene().sigMouseClicked.disconnect()
        except:
            pass

        self.pltGridImage.graphics.scene().sigMouseClicked.connect(self._grid_image_clicked)

    #helper function for the 3d slice of data
    def _update_grid_slice(self, bias_index):
        if self.grid_cube is None:
            return
        slice2d = self.grid_cube[:, :, bias_index]
        # Transpose for display (pyqtgraph uses row-major)
        self.pltGridImage.update_image(slice2d.T)#, autoLevels=False)


    def _grid_image_clicked(self, event):
        pos = event.scenePos()
        if not self.pltGridImage.sceneBoundingRect().contains(pos):
            return
        mouse_point = self.pltGridImage.getView().mapSceneToView(pos)
        x = int(mouse_point.x())
        y = int(mouse_point.y())
        if (x < 0 or y < 0 or
            x >= self.grid_cube.shape[0] or
            y >= self.grid_cube.shape[1]):
            return

        # Extract spectrum at selected pixel
        spectrum = self.grid_cube[x, y, :]
        bias_axis = np.arange(self.grid_cube.shape[2])
        self.pltGridChart.clear()
        self.pltGridChart.plot(bias_axis, spectrum)

    def _save_dac_xy(self):
        """Persist the current DACX/DACY operating point (firmware truth).
        X/Y only — Z is the crash axis and bias is a per-session operator
        decision; restoring either automatically would be unsafe/wrong."""
        if not self.stm.is_opened:
            return
        st = self.stm.status
        for key, val in (("dac/x", st.dac_x), ("dac/y", st.dac_y)):
            if dac_restore.restorable(val) is not None:
                self._settings.setValue(key, int(val))

    def closeEvent(self, event):
        self._save_dac_xy()
        super().closeEvent(event)

    def _restore_dac_xy(self):
        """Send the persisted DACX/DACY back to the firmware at port-open.
        The one-state mirrors pick the values up from status automatically;
        no widget poking needed."""
        sent = {}
        for key, cmd in (("dac/x", "DACX"), ("dac/y", "DACY")):
            v = dac_restore.restorable(self._settings.value(key))
            if v is not None:
                self.stm.send_cmd(f"{cmd} {v}", src="auto")
                sent[cmd] = v
        if sent:
            session_journal.note(
                f"restored DACX/DACY operating point from last session: "
                f"{sent}", src="auto")
            print(f"[DAC] restored operating point {sent}")

    @Slot()
    def on_cmdOpen_clicked(self):
        port = self.ui.lePort.currentText().strip()
        if not port:
            print("[CMD] OPEN  no port selected")
            return
        print(f"[CMD] OPEN  port={port}")
        try:
            self.stm.open(port)
        except Exception as e:
            print(f"[CMD] OPEN failed: {e}")
            return
        self._settings.setValue("serial/port", port)
        # Recording posture (operator directive 2026-07-14): record ALL data
        # at ALL times while the COM port is working — journal + 200 Hz
        # status stream start with the port, not on demand, so any hour of
        # bench work is replayable.  Scans still auto-stop/restart the
        # stream (single-reader rule); the journal never stops.
        if self.stm.is_opened:
            if not session_journal.is_active():
                session_journal.start(port=port)
            session_journal.record("port_open", path=port)
            self._start_session_recording()
            self._restore_dac_xy()

    # ----------------------
    # Serial port combo (replaces the form.ui QLineEdit)
    # ----------------------

    def _install_port_combo(self):
        old = self.ui.lePort
        parent = old.parentWidget()
        layout = parent.layout() if parent else None

        combo = QComboBox(parent)
        combo.setEditable(True)  # still allow a hand-typed path (e.g. /dev/tty*)
        combo.setMinimumWidth(old.width() or 120)

        btn = QPushButton("Refresh", parent)
        btn.setMaximumWidth(70)
        btn.clicked.connect(self._refresh_ports)

        if layout is not None and layout.replaceWidget(old, combo) is not None:
            old.deleteLater()
            # Drop the Refresh button immediately after the combo.
            idx = layout.indexOf(combo)
            if hasattr(layout, "insertWidget") and idx >= 0:
                layout.insertWidget(idx + 1, btn)
            else:
                layout.addWidget(btn)
        else:
            # Fallback: no layout — at least keep the combo usable.
            combo.setParent(parent)
            combo.show()

        self.ui.lePort = combo
        self._btn_port_refresh = btn

    @Slot()
    def _refresh_ports(self):
        combo = self.ui.lePort
        current = combo.currentText()
        combo.blockSignals(True)
        combo.clear()
        for p in serial.tools.list_ports.comports():
            combo.addItem(p.device)
        if current:
            idx = combo.findText(current)
            combo.setCurrentIndex(idx if idx >= 0 else -1)
            if idx < 0:
                combo.setEditText(current)
        combo.blockSignals(False)


    @Slot()
    def on_cmdStop_clicked(self):
        print("[CMD] STOP")
        self.stm.stop()
        # Stop must also de-energize the coils: an interrupted approach
        # otherwise leaves holding current flowing — heat right at the tip
        # -> thermal expansion (bench request 2026-07-14).  Reuse the
        # settle-watching auto-MTOF so a still-finishing motor burst isn't
        # cut short.
        self._arm_auto_mtof()


    @Slot()
    def on_cmdReset_clicked(self):
        print("[CMD] RESET")
        self.stm.reset()
        # Post-reset the DAC registers physically sit at 0 (= the -5 V
        # rails); the old GUI merely DISPLAYED 32768.  Make the historical
        # expectation true: drive all axes + bias to mid-scale (0 V)
        # (operator observation 2026-07-15).
        for cmd in ("DACX 32768", "DACY 32768", "DACZ 32768",
                    "BIAS 32768"):
            self.stm.send_cmd(cmd, src="auto")


    @Slot()
    def on_cmdClear_clicked(self):
        print("[CMD] CLEAR")
        self.stm.clear()

    @Slot()
    def on_cmdSendBias_clicked(self):
        bias = self.ui.spnBias.value()
        bias_v = stm_control.STM_Status.dac_to_bias_volts(bias)
        print("[CMD] SET_BIAS")
        print(f"      Bias DAC={bias}  ({bias_v:.4f} V)")
        print("      -> set_bias")
        self.stm.set_bias(bias)
        time.sleep(0.01)

    @Slot()
    def on_cmdSetDAC_clicked(self):

        bias = self.ui.spnBias.value()
        dacx = self.ui.spnDACX.value()
        dacy = self.ui.spnDACY.value()
        dacz = self.ui.spnDACZ.value()

        bias_v = stm_control.STM_Status.dac_to_bias_volts(bias)
        dacx_v = stm_control.STM_Status.dac_to_dacx_volts(dacx)
        dacy_v = stm_control.STM_Status.dac_to_dacy_volts(dacy)
        dacz_v = stm_control.STM_Status.dac_to_dacz_volts(dacz)

        print("[CMD] SET_DAC")
        print(f"      Bias DAC={bias}  ({bias_v:.4f} V)")
        print(f"      DACX DAC={dacx}  ({dacx_v:.4f} V)")
        print(f"      DACY DAC={dacy}  ({dacy_v:.4f} V)")
        print(f"      DACZ DAC={dacz}  ({dacz_v:.4f} V)")

        print("      -> set_bias")
        self.stm.set_bias(bias)
        time.sleep(0.01)

        print("      -> set_dacz")
        self.stm.set_dacz(dacz)
        time.sleep(0.01)

        print("      -> set_dacx")
        self.stm.set_dacx(dacx)
        time.sleep(0.01)

        print("      -> set_dacy")
        self.stm.set_dacy(dacy)


    @Slot()
    def on_cmdApproach_clicked(self):

        targetdac = int(self.ui.leTargetDAC.text() or 0)
        steps = int(self.ui.leSteps.text())
        print(f"[CMD] APPROACH  steps={steps}  targetdac={targetdac}")
        self.stm.approach(targetdac,steps)

    @Slot(bool)
    def on_chkConstCurrent_toggled(self, checked):
        if checked:
            # It's safer to get the value directly from the UI here
            try:
                target = int(self.ui.leCCVal.text())
                print(f"[CMD] CONST_CURRENT_ON target_adc={target}")
                self.stm.turn_on_const_current(target)
            except ValueError:
                print("Error: Invalid target value in leCCVal")
        else:
            print("[CMD] CONST_CURRENT_OFF")
            self.stm.turn_off_const_current()

    @Slot()
    def on_cmdCCOn_clicked(self):
        target = int(self.ui.leCCVal.text())
        print(f"[CMD] CONST_CURRENT_ON  target_adc={target}")
        self.stm.turn_on_const_current(target)

    @Slot()
    def on_cmdCCOff_clicked(self):
        print("[CMD] CONST_CURRENT_OFF")
        self.stm.turn_off_const_current()


    # ----------------------
    # MOTOR MOVEMENT
    # ----------------------

    def motor_move(self, steps, src="human"):
        """Single choke point for MTMV: move, then ALWAYS de-energize the
        coils (MTOF) once the move finishes.  The driver otherwise leaves
        holding current flowing after every move — heat + magnetic noise
        right at the tip (bench issue, 2026-07-09)."""
        print(f"MTMV {steps}")
        self.stm.send_cmd(f"MTMV {steps}", src=src)
        self._arm_auto_mtof()

    def _arm_auto_mtof(self):
        # MTMV executes asynchronously in the firmware (GSTS keeps flowing
        # during the move), so an immediate MTOF would cut the move short.
        # Instead watch the steps counter from the status poll and send MTOF
        # once it has been stable for ~1 s (or after a 30 s hard cap).
        self._mtof_last_steps = None
        self._mtof_stable = 0
        self._mtof_polls = 0
        if getattr(self, "_mtof_timer", None) is None:
            self._mtof_timer = QTimer(self)
            self._mtof_timer.timeout.connect(self._mtof_poll)
        self._mtof_timer.start(300)

    def _mtof_poll(self):
        self._mtof_polls += 1
        cur = self.stm.status.steps
        self._mtof_stable = (self._mtof_stable + 1
                             if cur == self._mtof_last_steps else 0)
        self._mtof_last_steps = cur
        if self._mtof_stable >= 3 or self._mtof_polls > 100:
            self._mtof_timer.stop()
            print("[MOTOR] move settled — auto MTOF")
            self.stm.send_cmd("MTOF", src="auto")

    @Slot()
    def on_cmdMotUp_clicked(self):
        amount = self.ui.spnMot.value()
        self.motor_move(amount)

    @Slot()
    def on_cmdMotDown_clicked(self):
        amount = self.ui.spnMot.value()
        self.motor_move(-amount)

    @Slot()
    def on_cmdMotOff_clicked(self):
        print(f"MTOF") # MOTOR OFF
        self.stm.send_cmd(f"MTOF")

    # ----------------------
    # SCAN
    # ----------------------

    @Slot()
    def on_cmdScan_clicked(self):
        if self.stm.busy:
            # Single-flight: a second scan thread would race the first on
            # the serial port and corrupt both (bench 2026-07-15).
            print("[CMD] SCAN refused — a legacy operation is already "
                  "reading the port")
            return
        self._halt_continuous_if_running()

        x_start = int(self.ui.leXStart.text())
        x_end = int(self.ui.leXEnd.text())
        x_res = int(self.ui.leXRes.text())

        y_start = int(self.ui.leYStart.text())
        y_end = int(self.ui.leYEnd.text())
        y_res = int(self.ui.leYRes.text())

        samples = int(self.ui.leSamples.text())

        print("[CMD] SCAN")
        print(f"      X: start={x_start} end={x_end} res={x_res}")
        print(f"      Y: start={y_start} end={y_end} res={y_res}")
        print(f"      samples={samples}")
        print("      -> starting scan thread")

        threading.Thread(
            target=self.stm.start_scan,
            args=(x_start, x_end, x_res, y_start, y_end, y_res, samples),
            daemon=True
        ).start()

    @Slot()
    def on_cmdSaveScan_clicked(self):
        self.save_scan_image(self.ui.leSave.text())

    @Slot()
    def on_cmdScanMulti_clicked(self):
        if self.stm.busy:
            print("[CMD] MULTI_SCAN refused — a legacy operation is "
                  "already reading the port")
            return
        self._halt_continuous_if_running()
        count = int(self.ui.leMultiScanTimes.text())
        x_start = int(self.ui.leXStart.text())
        x_end = int(self.ui.leXEnd.text())
        x_res = int(self.ui.leXRes.text())
        y_start = int(self.ui.leYStart.text())
        y_end = int(self.ui.leYEnd.text())
        y_res = int(self.ui.leYRes.text())
        samples = int(self.ui.leSamples.text())

        print("[CMD] MULTI_SCAN")
        print(f"      scans={count}")
        print(f"      X: start={x_start} end={x_end} res={x_res}")
        print(f"      Y: start={y_start} end={y_end} res={y_res}")
        print(f"      samples={samples}")

        def worker(): #local thread worker function
            print("[THREAD] Multi-scan worker started")
            for i in range(count):
                print(f"[SCAN] Starting scan {i+1}/{count}")
                self.stm.start_scan(
                    x_start, x_end, x_res,
                    y_start, y_end, y_res,
                    samples
                )
                while self.stm.busy:
                    print("[SCAN] Waiting for scan to finish...")
                    time.sleep(0.5)

                print("[SCAN] Scan finished — saving image")
                self.save_scan_image(self.ui.leSave.text())
                time.sleep(1)
            print("[SCAN] All scans complete")

        threading.Thread(target=worker, daemon=True).start()


    #Log handling
    def append_log(self, message):
        # The pane is a viewer, not the record (files/journal hold the full
        # data).  Unbounded appends of 4 KB scan rows made the whole GUI
        # progressively jumpy (bench 2026-07-15): truncate long lines; the
        # block cap is set once at init.
        if len(message) > 200:
            message = message[:200] + f" …[{len(message)} chars]"
        self.ui.txtLog.append(message)

    @Slot(str)
    def on_cmbColorPal_currentTextChanged(self,text):
        self.pltVals.set_colormap(text)

    @Slot(str)
    def on_cmbGridColorPal_currentTextChanged(self,text):
        self.pltGridImage.set_colormap(text)

    @Slot(str)
    def on_cmbMotDir_currentTextChanged(self,text):
        idx = self.ui.cmbMotDir.currentIndex()
        dir = 1 # assume forward
        if(idx == 0):
            dir = 1
        else :
            dir = -1
        print(f"[Motor Direction] {text} : {dir}")
        self.stm.send_cmd(f"MTDR {dir}")


    # ----------------------
    # IV CURVE
    # ----------------------
    @Slot()
    def on_cmdScanIV_clicked(self):
        self._halt_continuous_if_running()

        start = int(self.ui.leIVStart.text())
        end   = int(self.ui.leIVEnd.text())
        step  = int(self.ui.leIVStep.text())

        print("[CMD] IV_SCAN")
        print(f"      IV Start = {start}")
        print(f"      IV End   = {end}")
        print(f"      IV Step  = {step}")

        # New hybrid return
        bias_adc, current_adc, didv_adc = self.stm.measure_iv_curve(start, end, step)

        if bias_adc is None or len(bias_adc) == 0:
            print("[IV] No data received")
            return

        # Convert units
        bias = [
            stm_control.STM_Status.dac_to_bias_volts(dac)
            for dac in bias_adc
        ]

        current = [
            stm_control.STM_Status.adc_to_amp(adc)
            for adc in current_adc
        ]

        # Optional: convert dIdV to physical units
        # If your derivative is ADC-per-DAC, convert to A/V:
        didv = []

        for i in range(len(didv_adc)):
            # Convert derivative properly:
            # (dI/dV) = (adc_to_amp(delta_adc)) / (dac_to_bias_volts(delta_dac))
            # If firmware already divided by DAC step:
            amp = stm_control.STM_Status.adc_to_amp(didv_adc[i])
            didv.append(amp)

        print(f"[IV] points_collected = {len(bias)}")

        # Plot IV
        self.pltIV.update_plot(bias, current)

        # Plot dI/dV
        self.pltdIdV.update_plot(bias, didv)

    @Slot()
    def on_cmdSaveIV_clicked(self):

        prefix = self.ui.leIVFilename.text()

        print(f"[CMD] SAVE_IV  prefix={prefix}")

        iv_curve_values = self.stm.get_iv_curve()

        x_value = iv_curve_values[::2]
        y_value = iv_curve_values[1::2]

        print(f"[IV] saving {len(x_value)} points")

        self.save_iv_ascii(prefix, x_value, y_value)


    # ----------------------
    # dIdZ CURVE
    # ----------------------

    @Slot()
    def on_cmdScandIdZ_clicked(self):
        self._halt_continuous_if_running()

        start = int(self.ui.ledIdZStart.text())
        end = int(self.ui.ledIdZEnd.text())
        step = int(self.ui.ledIdZStep.text())

        print("[CMD] dIdZ_SCAN")
        print(f"      dIdZ Start ={start}")
        print(f"      dIdZ End ={end}")
        print(f"      dIdZ Step ={step}")

        dIdZ_values = self.stm.measure_dIdZ_curve(start, end, step)

        x_value = dIdZ_values[::2]
        y_value = dIdZ_values[1::2]

        current = [
            stm_control.STM_Status.adc_to_amp(adc)
            for adc in y_value
        ]

        bias = [
            stm_control.STM_Status.dac_to_bias_volts(dac)
            for dac in x_value
        ]

        print(f"[dIdZ] points_collected={len(bias)}")

        self.pltdIdZ.update_plot(bias, current)
    # ----------------------
    # Send Raw Command
    # ----------------------

    @Slot()
    def on_cmdSend_clicked(self):

        cmd = self.ui.leCommand.text()

        print(f"{cmd.strip()}")
        #self.send_cmd(f"DACX {value}")
        self.stm.send_cmd(f"{cmd.strip()}")



    # ----------------------
    # SpinBox Handlers
    # ----------------------

    @Slot(int)
    def on_spnBias_valueChanged(self, value):
        volts = stm_control.STM_Status.dac_to_bias_volts(value)
        self.ui.lblBiasVal.setText(f"{volts:.4f} V")

    @Slot(int)
    def on_spnDACX_valueChanged(self, value):
        volts = stm_control.STM_Status.dac_to_dacx_volts(value)
        self.ui.lblDACXVal.setText(f"{volts:.4f} V")

    @Slot(int)
    def on_spnDACY_valueChanged(self, value):
        volts = stm_control.STM_Status.dac_to_dacy_volts(value)
        self.ui.lblDACYVal.setText(f"{volts:.4f} V")

    @Slot(int)
    def on_spnDACZ_valueChanged(self, value):
        volts = stm_control.STM_Status.dac_to_dacz_volts(value)
        self.ui.lblDACZVal.setText(f"{volts:.4f} V")
        # Keep the drag bar tracking the spinbox (blockSignals prevents the
        # bar's echo from re-triggering a send).
        self.ui.scr_DACZ.blockSignals(True)
        self.ui.scr_DACZ.setValue(value)
        self.ui.scr_DACZ.blockSignals(False)

    @Slot(int)
    def on_scr_Bias_valueChanged(self, value):
        print(value)
        self.ui.spnBias.setValue(value)
        self.on_spnBias_valueChanged(value)

    @Slot(int)
    def on_scr_DACX_valueChanged(self, value):
        self.ui.spnDACX.setValue(value)
        print(value)

    @Slot(int)
    def on_scr_DACY_valueChanged(self, value):
        self.ui.spnDACY.setValue(value)
        print(value)

    @Slot(int)
    def on_scr_DACZ_valueChanged(self, value):
        """Real-time Z-baseline drag bar: follow with the spinbox AND stream
        DACZ to the firmware while dragging (restored 2026-07-14 — the
        handler previously only updated the display).  Sends are coalesced
        to the newest value at most every 50 ms so a fast drag can't flood
        the serial port."""
        self.ui.spnDACZ.setValue(value)
        self._dacz_pending = value
        if not self._dacz_send_timer.isActive():
            self._dacz_send_timer.start(50)

    def _send_pending_dacz(self):
        value = self._dacz_pending
        self._dacz_pending = None
        if value is None or not self.stm.is_opened:
            return
        self.stm.set_dacz(value)

    @Slot()
    def _drift_hold_tick(self):
        """One tick of the slow anti-drift Z servo (constant-height mode).
        Hard rules: real feedback (CC/ENGA) owns Z -> stand down; legacy op
        busy -> stand down; open junction -> freeze (never seek)."""
        if not self._cs_drift_hold.isChecked():
            self._drift_hist.clear()
            self._cs_drift_lbl.setText("drift: —")
            return
        st = self.stm.status
        if (not self.stm.is_opened or self.stm.busy
                or st.is_const_current or st.is_approaching):
            return
        hist = list(self.stm.history)[-256:]
        if len(hist) < 20:
            return
        mean_adc = sum(h.adc for h in hist) / len(hist)
        target = self._scan_ctrl._pa_to_setpoint_lsb(
            self._cs_setpoint.value())
        dz = drift_hold.nudge(mean_adc, target)
        if dz:
            v = max(0, min(65535, int(st.dac_z) + dz))
            self.stm.send_cmd(f"DACZ {v}", src="auto")
            self._drift_dz_total += dz
        # Rate readout: correction slope over the last ~60 s IS the
        # measured drift velocity (with sign: + = surface receding).
        now = time.time()
        self._drift_hist.append((now, self._drift_dz_total))
        old = next(((t, z) for (t, z) in self._drift_hist
                    if now - t <= 60), None)
        if old and now - old[0] > 5:
            lsb_min = (self._drift_dz_total - old[1]) / (now - old[0]) * 60
            nm_v = getattr(self._cal, "piezo_z_nm_per_v",
                           getattr(self._cal, "piezo_x_nm_per_v", 0.0))
            nm_min = lsb_min * self._cal.dac_x_v_per_lsb * nm_v
            self._cs_drift_lbl.setText(
                f"drift: {lsb_min:+.0f} LSB/min ({nm_min:+.2f} nm/min)")

    @Slot(int)
    def _update_tab_info_btn(self, idx):
        title = self.ui.tabWidget.tabText(idx)
        has = (title not in self._tab_help.NO_INFO
               and title in self._tab_help.HELP)
        self._btn_tabinfo.setVisible(bool(has))

    @Slot()
    def _show_tab_info(self):
        title = self.ui.tabWidget.tabText(self.ui.tabWidget.currentIndex())
        entry = self._tab_help.HELP.get(title)
        if not entry:
            return
        from PySide6.QtWidgets import QDialog, QTextBrowser
        dlg = QDialog(self)
        dlg.setWindowTitle(f"About: {title}")
        dlg.resize(560, 640)
        lay = QVBoxLayout(dlg)
        tb = QTextBrowser()
        terms = "".join(
            f"<li><b>{k}</b> — {v}</li>" for k, v in entry["terms"].items())
        tb.setHtml(
            f"<h2>{title}</h2>"
            f"<h3>What it is</h3><p>{entry['what']}</p>"
            f"<h3>How to use it</h3><p>{entry['how']}</p>"
            f"<h3>Key terms</h3><ul>{terms}</ul>")
        lay.addWidget(tb)
        close = QPushButton("Close")
        close.clicked.connect(dlg.accept)
        lay.addWidget(close)
        dlg.show()
        self._ss_popups.append(dlg)

    @Slot(int)
    def _on_preamp_gain(self, _idx):
        g = float(self._preamp_gain.currentData())
        stm_control.STM_Status.preamp_gain = g
        self._settings.setValue("preamp/gain", g)
        session_journal.note(f"preamp gain set to {g:g}X", src="human")
        print(f"[PREAMP] gain = {g:g}X (current conversion now /{g:g})")

    @Slot()
    def _mark_dac_edit(self):
        """Timestamp user-originated edits of the DAC/bias spins so the
        one-state mirror backs off while the operator is composing."""
        if not self._mirror_updating:
            self._dac_edit_t = time.time()

    @Slot(int)
    def _on_cs_zslider_changed(self, value):
        """User drag on the Continuous Scan Z slider — same throttled
        real-time DACZ path as the Configuration-tab drag bar."""
        self._cs_zval.setText(str(value))
        self.on_scr_DACZ_valueChanged(value)

    @Slot(int)
    def _set_cs_zslider_from_scan(self, dac_code):
        """Scan-line Z (ISR z_pos) -> slider, ONLY when feedback owns Z.
        In constant-height mode z_pos is a stale variable that no longer
        drives the DAC (frozen at its last feedback value), so displaying
        it made the handle 'move by itself' while the real Z held rock
        steady (bench 2026-07-14, proven from the 200 Hz record)."""
        if self.stm.status.is_const_current:
            self._set_cs_zslider_from_stream(dac_code)

    @Slot(int)
    def _set_cs_zslider_from_stream(self, dac_code):
        """Live Z readout onto the slider — skipped while the operator is
        dragging so the stream can't yank the handle out of their hand."""
        if self._cs_zslider.isSliderDown():
            return
        v = max(0, min(65535, int(dac_code)))
        self._cs_zslider.blockSignals(True)
        self._cs_zslider.setValue(v)
        self._cs_zslider.blockSignals(False)
        self._cs_zval.setText(str(v))


    # ----------------------
    # Stability Histogram Tab
    # ----------------------

    # Tunneling gap sensitivity: I = I0 * exp(-2*kappa*z).
    #   kappa = sqrt(2 m phi)/hbar ~= 0.5123 * sqrt(phi[eV])  [1/Angstrom]
    # For a work function phi ~= 4 eV, kappa ~= 1.025 /A, so 2*kappa ~= 2.05 /A
    # and a change of one unit in ln(I) corresponds to ~48.8 pm of gap motion
    # (a decade of current ~= 1.1 A).  These let us translate the log-current
    # slope into a physical z-drift velocity and the log-current spread into a
    # mechanical jitter amplitude.
    # Canonical math lives in stab_metrics.py (Qt-free, shared with the
    # docker software-mockup so the emulator validates the same code).
    STAB_WORK_FUNCTION_EV = 4.0
    STAB_KAPPA_PER_M = stab_metrics.kappa_per_m(STAB_WORK_FUNCTION_EV)  # 1/m
    STAB_PM_PER_LN = stab_metrics.pm_per_ln(STAB_WORK_FUNCTION_EV)      # pm per unit ln(I)

    def build_stability_tab(self):
        """Programmatically add a 'Stability' tab with a live, growing
        histogram of the tunneling current. Built in code so the generated
        ui_form.py is never touched."""

        tab = QWidget()
        outer = QVBoxLayout(tab)
        outer.setContentsMargins(4, 4, 4, 4)

        # --- control row -------------------------------------------------
        ctl = QHBoxLayout()

        self.cmdStabStart = QPushButton("Start")
        self.cmdStabStop = QPushButton("Stop")
        self.cmdStabClear = QPushButton("Clear")
        self.cmdStabStop.setEnabled(False)

        ctl.addWidget(self.cmdStabStart)
        ctl.addWidget(self.cmdStabStop)
        ctl.addWidget(self.cmdStabClear)

        ctl.addSpacing(16)
        ctl.addWidget(QLabel("Bins:"))
        self.spnStabBins = QtWidgets.QSpinBox()
        self.spnStabBins.setRange(5, 500)
        self.spnStabBins.setValue(60)
        ctl.addWidget(self.spnStabBins)

        ctl.addSpacing(8)
        ctl.addWidget(QLabel("Outlier cutoff (N·MAD):"))
        self.spnStabNmad = QtWidgets.QDoubleSpinBox()
        self.spnStabNmad.setRange(0.5, 20.0)
        self.spnStabNmad.setSingleStep(0.5)
        self.spnStabNmad.setValue(5.0)
        self.spnStabNmad.setToolTip(
            "Samples farther than N scaled median-absolute-deviations "
            "from the median are excluded from the histogram."
        )
        ctl.addWidget(self.spnStabNmad)

        ctl.addStretch(1)
        outer.addLayout(ctl)

        # --- readout row -------------------------------------------------
        self.lblStabStats = QLabel("No data yet.")
        self.lblStabStats.setStyleSheet("font-family: monospace;")
        outer.addWidget(self.lblStabStats)

        # Live drift / jitter readout derived from the log-current fit.
        self.lblStabDrift = QLabel("")
        self.lblStabDrift.setStyleSheet("font-family: monospace; color: #1a3;")
        self.lblStabDrift.setToolTip(
            "drift v_z: z-velocity from the slope of ln|I| vs time "
            "(sign: + = gap opening / current shrinking).  "
            "R2: how linear (drift-like) the trend is.  "
            "jitter: mechanical z-noise from the spread of ln|I|.  "
            "skew: asymmetry of the ln|I| distribution."
        )
        outer.addWidget(self.lblStabDrift)

        # --- histogram plot ---------------------------------------------
        self.pltStability = plotframe.PlotFrame()
        self.pltStability.add_histogram(
            label="Tunneling current distribution",
            xlabel="Current (A)",
            ylabel="Count",
        )
        outer.addWidget(self.pltStability, 1)

        # --- wiring ------------------------------------------------------
        self.cmdStabStart.clicked.connect(self.stab_start)
        # Explicit kwargs: clicked(bool) would otherwise land its checked=
        # False in show_fourier and silently kill the manual-Stop jump to
        # the Fourier tab (found in the 2026-07-15 tab sweep).
        self.cmdStabStop.clicked.connect(
            lambda checked=False: self.stab_stop(show_fourier=True))
        self.cmdStabClear.clicked.connect(self.stab_clear)
        self.spnStabBins.valueChanged.connect(self.refresh_histogram)
        self.spnStabNmad.valueChanged.connect(self.refresh_histogram)

        self.ui.tabWidget.addTab(tab, "Stability")

    # --- session recording service (independent of every viewer) ----------
    # Operator posture 2026-07-14: recording is a background service tied to
    # the port, never to a consuming tab/figure.  It owns the journal, the
    # 200 Hz STRM stream, and the status CSV.  The Stability tab is just one
    # consumer of the same feed and is manually triggered.

    def _start_session_recording(self):
        if self._recording:
            return
        history = self.stm.history
        self._rec_last_t = history[-1].time_millis if history else None
        # True-time writer: its own thread, fed straight from the serial
        # reader thread — the GUI event loop is never in the data path.
        try:
            prefix = self.ui.leSave.text().strip()
        except Exception:
            prefix = ""
        prefix = prefix or "stability"
        ts = int(datetime.timestamp(datetime.now()) * 1000)
        self.stab_log_path = f"{prefix}_stability_{ts}.csv"
        self._status_logger.start(self.stab_log_path)
        if not session_journal.is_active():
            session_journal.start(csv=self.stab_log_path)
        session_journal.record("recording_start", path=self.stab_log_path)
        self._suppress_auto_record = False
        self._recording = True
        # Prefer firmware push-mode status (STRM, ~200 Hz) over the 9 Hz
        # GSTS poll; falls back automatically if the firmware is old.
        self._start_stab_stream()
        print(f"[REC] session recording started -> {self.stab_log_path}")

    def _stop_session_recording(self):
        if not self._recording:
            return
        self._recording = False
        self._stop_stab_stream()
        session_journal.record("recording_stop", path=self.stab_log_path)
        self._status_logger.stop()
        print(f"[REC] session recording stopped "
              f"({self._status_logger.n_rows} rows)")

    @Slot(int, int, int, int, int, int)
    def _log_status_direct(self, tm, adc, dac_z, bias, steps, flags):
        """DirectConnection slot: runs ON the serial-reader thread and only
        enqueues to the writer thread.  Must never touch GUI state."""
        if self._recording:
            self._status_logger.put(tm, adc, dac_z, bias, steps, flags)

    @Slot()
    def stab_start(self):
        """Stability tab Start: begin a histogram/analysis WINDOW.  Viewer
        only — the underlying recording service is untouched."""
        # Consume only samples newer than the latest one we have, so we
        # don't re-ingest the existing history buffer.
        history = self.stm.history
        self.stab_last_t = history[-1].time_millis if history else None
        session_journal.record("stab_window_start", path=self.stab_log_path)
        self.stab_running = True
        self.cmdStabStart.setEnabled(False)
        self.cmdStabStop.setEnabled(True)
        print(f"[STAB] histogram window started "
              f"({len(self.stab_samples)} samples kept)")

    # --- STRM push-mode streaming (Phase 5) -------------------------------
    # During a stability recording the firmware pushes binary 'S' status
    # frames at STAB_STREAM_HZ instead of being polled at 9 Hz — Nyquist
    # rises from ~4.5 Hz to 100 Hz, so mains EMI is finally unaliased.
    STAB_STREAM_HZ = 200

    def _start_stab_stream(self):
        if self._scan_ctrl.is_running() or not self.stm.is_opened:
            return
        from serial_reader import SerialReaderThread
        self._stab_stream_frames = 0
        self._stab_reader = SerialReaderThread(self.stm.stm_serial)
        self._stab_reader.statusFrame.connect(self._on_status_frame)
        # True-time logging tap: DirectConnection keeps this on the reader
        # thread; it enqueues to the writer thread without touching the GUI.
        self._stab_reader.statusFrame.connect(
            self._log_status_direct, QtCore.Qt.DirectConnection)
        self._stab_reader.asciiLine.connect(self._on_fw_ascii)
        # Permanent raw tap (no-op unless a raw capture is active).
        self._stab_reader.rawBlock.connect(
            self._raw_logger.on_block, QtCore.Qt.DirectConnection)
        self._stab_reader.start()
        self._stab_streaming = True
        self.stm.hist_length = 20000       # keep ~100 s at 200 Hz for plots
        self.stm.send_cmd(f"STRM {self.STAB_STREAM_HZ}", src="auto")
        QTimer.singleShot(1500, self._check_stab_stream_alive)
        print(f"[STAB] streaming status at {self.STAB_STREAM_HZ} Hz (STRM)")

    def _check_stab_stream_alive(self):
        if self._stab_streaming and self._stab_stream_frames == 0:
            print("[STAB] no STRM frames after 1.5 s (old firmware?) — "
                  "falling back to GSTS polling")
            self._stop_stab_stream()

    def _rearm_stream_check(self):
        """Whenever the recording's 200 Hz push stream is down and the port
        is quiet (not busy, no scan reader) for two consecutive 2 s checks,
        re-arm it.  Covers legacy-op completions (including worker threads)
        AND a failed startup: garbage in the RX buffer once made the STRM
        watchdog falsely fall back to 9 Hz for a whole session (bench
        2026-07-15) — now it retries instead of giving up forever.  A
        failed attempt backs off ~20 s via the negative counter reset."""
        if (self._recording
                and not self._stab_streaming
                and not self.stm.busy
                and self.stm.is_opened
                and not self._scan_ctrl.is_running()):
            self._rearm_quiet += 1
            if self._rearm_quiet >= 2:
                self._rearm_quiet = -8   # cooldown before any retry
                self._suppress_auto_record = False
                print("[REC] stream down and port quiet — (re)arming "
                      "200 Hz stream")
                self._start_stab_stream()
        else:
            self._rearm_quiet = 0

    def _pause_stab_stream_for_scan(self):
        """Stop only the recording's reader thread, keeping firmware STRM
        enabled — the scan reader picks up the pushed 'S' frames and feeds
        the same writer thread, so the record has no gap in ownership."""
        self._stab_streaming = False
        if self._stab_reader is not None:
            self._stab_reader.stop()
            self._stab_reader.wait(2000)
            self._stab_reader = None
        session_journal.record("stream_handoff_to_scan")

    def _stop_stab_stream(self):
        if not self._stab_streaming:
            return
        self._stab_streaming = False
        self.stm.send_cmd("STRM 0", src="auto")
        if self._stab_reader is not None:
            self._stab_reader.stop()
            self._stab_reader.wait(2000)
            self._stab_reader = None
        self.stm.hist_length = 1000
        # Drain stray frames still in flight so the next GSTS readline
        # doesn't land mid-frame.
        try:
            time.sleep(0.1)
            self.stm.stm_serial.reset_input_buffer()
        except Exception:
            pass
        print("[STAB] status streaming stopped")

    @Slot(int, int, int, int, int, int)
    def _on_status_frame(self, tm, adc, dac_z, bias, steps, flags):
        """One pushed 'S' frame → same shape the GSTS poll produced, so the
        whole downstream pipeline (history, CSV, histogram) is unchanged."""
        # Validity gate: a 0x53 byte inside post-scan buffer garbage parses
        # as a bogus frame whose random time_millis zig-zags the amp plot
        # (bench 2026-07-15).  Real frames use only 3 flag bits, and their
        # tm advances in lock-step with wall time (any gap length is fine —
        # the anchor is wall-clock, so a 69 s legacy scan doesn't trip it).
        # 10 consecutive rejects reset the anchor so a genuine firmware
        # reboot (tm restart) recovers automatically.
        if flags & ~0x07:
            return
        now = time.time()
        anchor = getattr(self, "_tm_anchor", None)
        if anchor is not None:
            expect = anchor[0] + (now - anchor[1]) * 1000.0
            if abs(tm - expect) > 3000:
                self._tm_rejects = getattr(self, "_tm_rejects", 0) + 1
                if self._tm_rejects < 10:
                    return
        self._tm_rejects = 0
        self._tm_anchor = (tm, now)
        self._stab_stream_frames += 1
        st = stm_control.STM_Status(
            bias=bias, dac_z=dac_z,
            dac_x=self.stm.status.dac_x, dac_y=self.stm.status.dac_y,
            adc=adc, steps=steps,
            is_approaching=bool(flags & 0x01),
            is_const_current=bool(flags & 0x02),
            is_scanning=bool(flags & 0x04),
            time_millis=tm)
        self.stm.status = st
        self.stm.history.append(st)
        while len(self.stm.history) > self.stm.hist_length:
            self.stm.history.popleft()
        session_journal.mark_time(tm)

    @Slot(str)
    def _on_fw_ascii(self, line: str):
        """Firmware ASCII prints (e.g. 'Approached!' and the trigger ADC
        value) arriving on a push-mode reader.  Journal them — approach
        trigger forensics were lost on 2026-07-14 because these lines were
        emitted with no listener."""
        print(f"[FW] {line}")
        session_journal.note(f"fw: {line}", src="auto")

    # --- RAWD raw ISR-tap capture (Phase 5) --------------------------------
    # Every 40 µs ISR sample (adc, z, err) streamed in 512-sample blocks and
    # written to disk verbatim.  decim=1 -> 25 kHz (~250 KB/s).

    def _active_reader(self):
        """Whichever SerialReaderThread currently owns the port, or None."""
        if self._scan_ctrl.is_running():
            return self._scan_ctrl._reader
        if self._stab_streaming:
            return self._stab_reader
        return self._raw_reader

    def raw_start(self, decim=1, src="human"):
        if self._raw_logger.is_active():
            return self._raw_logger.status()
        decim = max(1, int(decim))
        if self._active_reader() is None:
            # Nothing owns the port: start a dedicated reader for the capture.
            from serial_reader import SerialReaderThread
            self._raw_reader = SerialReaderThread(self.stm.stm_serial)
            self._raw_reader.asciiLine.connect(self._on_fw_ascii)
            # rawBlock is connected PERMANENTLY at every reader's creation
            # (on_block no-ops while the logger is inactive), so a capture
            # survives port-ownership transitions (scan start/halt, stream
            # re-arm) instead of silently losing blocks — audit 2026-07-14.
            self._raw_reader.rawBlock.connect(
                self._raw_logger.on_block, QtCore.Qt.DirectConnection)
            self._raw_reader.start()
        fs = 1e6 / (40.0 * decim)     # nominal (control_dt_us default 40)
        self._raw_logger.start({
            "decim": decim,
            "nominal_sample_hz": fs,
            "bias_dac": self.ui.spnBias.value(),
        })
        self._raw_decim = decim
        self.stm.send_cmd(f"RAWD {decim}", src=src)
        print(f"[RAW] capture started at ~{fs:.0f} Hz "
              f"-> {self._raw_logger.base_path}.raw")
        return self._raw_logger.status()

    def raw_stop(self, src="human"):
        if not self._raw_logger.is_active():
            return None
        self.stm.send_cmd("RAWD 0", src=src)
        # No disconnects: rawBlock stays permanently wired on every reader;
        # closing the logger makes on_block a no-op.
        path = self._raw_logger.stop()
        if self._raw_reader is not None:
            self._raw_reader.stop()
            self._raw_reader.wait(2000)
            self._raw_reader = None
            # Dedicated reader owned the port: clear stray frames before the
            # GSTS poll resumes.
            try:
                time.sleep(0.1)
                self.stm.stm_serial.reset_input_buffer()
            except Exception:
                pass
        self._raw_decim = 0
        st = self._raw_logger.status()
        print(f"[RAW] capture closed: {path} ({st['samples']} samples, "
              f"fw_dropped={st['fw_dropped_samples']}, "
              f"gaps={st['seq_gap_blocks']})")
        return path

    @Slot()
    def stab_stop(self, show_fourier=True):
        """Stability tab Stop: close the histogram/analysis WINDOW and grade
        it.  Viewer only — the recording service and its stream/CSV/journal
        keep running untouched.  ``show_fourier=False`` for automatic stop
        paths — only a manual Stop click steals focus to the Fourier view."""
        self.stab_running = False
        # PSD / Allan are computed once here and handed to both the summary
        # writer and the Fourier tab, instead of each recomputing them.
        psd = stab_metrics.power_spectrum(self.stab_times, self.stab_samples)
        allan = stab_metrics.allan_deviation(self.stab_times, self.stab_samples)
        self._save_stab_summary(psd, allan)
        self.cmdStabStart.setEnabled(True)
        self.cmdStabStop.setEnabled(False)
        print(f"[STAB] histogram window closed ({len(self.stab_samples)} samples)")
        # Grade the just-saved session with the real stab_runner logic so the
        # operator gets an unambiguous "are we tunneling?" verdict, not just raw
        # metrics.  Graded from the CSV (it has adc/bias for the rail/bias checks
        # the in-memory current-only buffer can't provide).
        verdict = None
        try:
            verdict = stab_runner.analyze(self.stab_log_path)
        except Exception as e:
            print(f"[STAB] verdict unavailable: {e}")
        session_journal.record("stab_window_stop", path=self.stab_log_path)
        if verdict is not None:
            session_journal.note(f"verdict={verdict['verdict']}", src="auto")
        self.refresh_fourier_analysis(psd, allan, verdict)
        if show_fourier:
            self.ui.tabWidget.setCurrentWidget(self._fourierTab)

    @Slot()
    def stab_clear(self):
        self.stab_samples = []
        self.stab_times = []
        self.stab_last_t = (
            self.stm.history[-1].time_millis if self.stm.history else None
        )
        self.pltStability.update_histogram([], [], None)
        self.lblStabStats.setText("No data yet.")
        self.lblStabDrift.setText("")
        print("[STAB] cleared")

        self.pltFourierPsd.update_plot([], [])
        self.pltFourierPsd.clear_marker()
        self.pltFourierAllan.update_plot([], [])
        self.pltFourierAllan.update_extra_curve("white", [], [])
        self.pltFourierAllan.update_extra_curve("randomwalk", [], [])
        self.pltFourierAllan.update_extra_curve("drift", [], [])
        self.pltFourierAllan.clear_marker()
        self.lblFourierStats.setText(
            "No data yet — record a Stability session, then press Stop."
        )

    # --- raw-session logging -------------------------------------------------
    # The in-memory history is a bounded, self-erasing deque, so a long drift
    # run would silently lose its early samples.  We stream every raw sample to
    # a timestamped CSV so the full (time-ordered) session survives on disk for
    # offline analysis (Allan deviation, spread-vs-time, drift velocity, PSD).

    def _save_stab_summary(self, psd, allan):
        """Write a companion _summary.json alongside the CSV with all derived
        metrics so sessions can be compared without reprocessing raw data.
        ``psd`` / ``allan`` are the results already computed in stab_stop()
        (either may be None when the recording was too short)."""
        if not self.stab_log_path or not self.stab_samples:
            return

        summary_path = self.stab_log_path.replace(".csv", "_summary.json")
        data = np.asarray(self.stab_samples, dtype=float)

        # Robust (MAD) outlier rejection matching refresh_histogram().
        med = float(np.median(data))
        mad = float(np.median(np.abs(data - med)))
        n_mad = self.spnStabNmad.value()
        if mad > 0:
            spread = 1.4826 * mad
            kept = data[(data >= med - n_mad * spread) & (data <= med + n_mad * spread)]
        else:
            kept = data

        histogram = {
            "n_total": int(data.size),
            "n_excluded": int(data.size - kept.size),
            "mean_A": float(kept.mean()) if kept.size else None,
            "std_A": float(kept.std()) if kept.size else None,
            "median_A": float(np.median(kept)) if kept.size else None,
            "latest_A": float(data[-1]),
            "n_mad_cutoff": float(n_mad),
        }

        drift = stab_metrics.drift_metrics(
            self.stab_times, self.stab_samples, self.STAB_PM_PER_LN
        )

        psd_summary = None
        if psd is not None:
            psd_summary = {
                "peak_freq_hz": psd["peak_freq_hz"],
                "peak_power": psd["peak_power"],
                "peak_snr": psd["peak_snr"],
                "peak_snr_threshold": psd["peak_snr_threshold"],
                "peak_significant": psd["peak_significant"],
                "fs_hz": psd["fs_hz"],
                "n_samples": psd["n"],
            }

        allan_summary = None
        if allan is not None:
            allan_summary = {
                "slope": allan["slope"],
                "noise_type": stab_metrics.classify_allan_slope(allan["slope"]),
                "tau_opt_s": allan["tau_opt_s"],
                "sigma_min": allan["sigma_min"],
                # Gap-jitter equivalent; None when not tunneling (mean
                # current ~0 or fluctuations comparable to the mean).
                "sigma_min_pm": stab_metrics.sigma_to_pm(
                    allan["sigma_min"], histogram["mean_A"], self.STAB_PM_PER_LN
                ),
            }

        summary = {
            "csv_file": self.stab_log_path,
            "work_function_eV": self.STAB_WORK_FUNCTION_EV,
            "histogram": histogram,
            "drift": drift,
            "psd": psd_summary,
            "allan": allan_summary,
        }

        try:
            with open(summary_path, "w") as f:
                json.dump(summary, f, indent=2)
            print(f"[STAB] summary saved to {summary_path}")
        except Exception as e:
            print(f"[STAB] WARNING: could not write summary: {e}")

    def _open_stab_log(self):
        prefix = ""
        try:
            prefix = self.ui.leSave.text().strip()
        except Exception:
            prefix = ""
        prefix = prefix or "stability"
        ts = int(datetime.timestamp(datetime.now()) * 1000)
        self.stab_log_path = f"{prefix}_stability_{ts}.csv"
        self.stab_t0 = None
        try:
            self.stab_log_file = open(self.stab_log_path, "w", newline="")
            self.stab_log_writer = csv.writer(self.stab_log_file)
            self.stab_log_writer.writerow([
                "elapsed_s", "time_millis", "adc", "current_A",
                "dac_z", "bias", "steps",
                "is_scanning", "is_const_current", "is_approaching",
            ])
            self.stab_log_file.flush()
            print(f"[STAB] logging raw samples to {self.stab_log_path}")
        except Exception as e:
            self.stab_log_file = None
            self.stab_log_writer = None
            print(f"[STAB] WARNING: could not open log file: {e}")

    def _close_stab_log(self):
        if self.stab_log_file is not None:
            try:
                self.stab_log_file.flush()
                self.stab_log_file.close()
                print(f"[STAB] log closed: {self.stab_log_path}")
            except Exception as e:
                print(f"[STAB] WARNING: error closing log: {e}")
        self.stab_log_file = None
        self.stab_log_writer = None

    def _log_stab_samples(self, samples):
        """Append a batch of raw STM_Status samples to the open CSV."""
        if self.stab_log_writer is None:
            return
        try:
            for h in samples:
                if self.stab_t0 is None:
                    self.stab_t0 = h.time_millis
                elapsed = (h.time_millis - self.stab_t0) / 1000.0
                self.stab_log_writer.writerow([
                    f"{elapsed:.3f}", h.time_millis, h.adc,
                    f"{stm_control.STM_Status.adc_to_amp(h.adc):.6e}",
                    h.dac_z, h.bias, h.steps,
                    int(h.is_scanning), int(h.is_const_current),
                    int(h.is_approaching),
                ])
            # Flush every batch so an unclean shutdown keeps the data.
            self.stab_log_file.flush()
        except Exception as e:
            print(f"[STAB] WARNING: log write failed: {e}")

    def update_recording(self):
        """FALLBACK recorder for old firmware only (no STRM push stream).
        When streaming is active the reader thread feeds the writer thread
        directly (_log_status_direct) and this is a no-op.  Here we batch
        the GSTS-poll history into the same writer from the GUI timer."""
        # Skip whenever ANY push-mode reader is feeding _log_status_direct
        # (stab stream or scan reader) — logging here too would duplicate
        # every row (seen live 2026-07-14: ~420 rows/s instead of 200).
        if (not self._recording or self._stab_streaming
                or self._scan_ctrl.is_running()):
            return
        history = self.stm.history
        if not history:
            return
        new = [
            h for h in history
            if self._rec_last_t is None or h.time_millis > self._rec_last_t
        ]
        if not new:
            return
        self._rec_last_t = new[-1].time_millis
        for h in new:
            self._status_logger.put(
                h.time_millis, h.adc, h.dac_z, h.bias, h.steps,
                status_logger.pack_flags(h.is_approaching,
                                         h.is_const_current,
                                         h.is_scanning))

    def update_stability(self):
        """Stability tab VIEWER: pull new status samples into the histogram
        accumulator and redraw.  Manually triggered (Start/Stop); consumes
        the same status feed the recording service logs, but never controls
        the recording itself."""
        if not self.stab_running:
            return

        history = self.stm.history
        if not history:
            return

        # Append only samples we haven't consumed yet.
        new = [
            h for h in history
            if self.stab_last_t is None or h.time_millis > self.stab_last_t
        ]
        if not new:
            return

        self.stab_last_t = new[-1].time_millis
        for h in new:
            self.stab_samples.append(stm_control.STM_Status.adc_to_amp(h.adc))
            self.stab_times.append(h.time_millis)

        self.refresh_histogram()

    def refresh_histogram(self):
        """Recompute the histogram from accumulated samples with robust
        (median ± N·MAD) outlier rejection and update the arrow."""
        if not self.stab_samples:
            return

        data = np.asarray(self.stab_samples, dtype=float)

        # --- robust outlier rejection (MAD) -----------------------------
        med = np.median(data)
        mad = np.median(np.abs(data - med))
        n_mad = self.spnStabNmad.value()

        if mad > 0:
            # 1.4826 scales MAD to be a consistent estimator of std
            # for normally-distributed data.
            spread = 1.4826 * mad
            lo = med - n_mad * spread
            hi = med + n_mad * spread
            mask = (data >= lo) & (data <= hi)
            kept = data[mask]
        else:
            kept = data

        if kept.size == 0:
            return

        bins = self.spnStabBins.value()
        counts, edges = np.histogram(kept, bins=bins)
        centers = (edges[:-1] + edges[1:]) / 2.0

        # Which bin is the most recent (non-outlier) sample growing?
        latest = data[-1]
        cur_idx = None
        if edges[0] <= latest <= edges[-1]:
            cur_idx = int(np.clip(np.digitize(latest, edges) - 1,
                                  0, len(counts) - 1))

        self.pltStability.update_histogram(centers, counts, cur_idx)

        # --- readout -----------------------------------------------------
        n_out = data.size - kept.size
        self.lblStabStats.setText(
            "N={total}  (excluded {out})   "
            "mean={mean:.3e} A   std={std:.3e} A   "
            "median={median:.3e} A   latest={latest:.3e} A".format(
                total=data.size, out=n_out,
                mean=kept.mean(), std=kept.std(),
                median=np.median(kept), latest=latest,
            )
        )

        # --- live drift / jitter estimate --------------------------------
        self._update_drift_readout()

    def _update_drift_readout(self):
        """Estimate z-drift velocity and mechanical jitter from the
        time-ordered log-current, and show them live.

        Because I = I0*exp(-2*kappa*z), we work in ln|I|:
          * a constant gap drift v_z makes ln|I| linear in time with
            slope = -2*kappa*v_z, so v_z = -(1/2kappa)*d(lnI)/dt;
          * the spread of ln|I| maps to a mechanical z-jitter amplitude
            sigma_z = std(lnI)/(2*kappa).
        """
        m = self._stab_drift_metrics(self.stab_times, self.stab_samples)
        if m is None:
            self.lblStabDrift.setText("drift: need more in-tunneling samples")
            return
        self.lblStabDrift.setText(
            "drift v_z={vz:+.2f} pm/s  (R2={r2:.2f})   "
            "jitter sigma_z~{jit:.1f} pm   "
            "skew(lnI)={skew:+.2f}   [n={n} usable, dt={span:.1f}s]".format(
                vz=m["vz_pm_s"], r2=m["r2"], jit=m["jitter_pm"],
                skew=m["skew"], n=m["n"], span=m["span_s"],
            )
        )

    def _stab_drift_metrics(self, times_ms, amps):
        """Drift/jitter metrics from parallel (time_millis, amp) arrays, or
        None if there isn't enough usable in-tunneling data. Delegates to the
        shared, Qt-free stab_metrics module (single source of truth)."""
        return stab_metrics.drift_metrics(times_ms, amps, self.STAB_PM_PER_LN)

    # ----------------------
    # Fourier Analysis Tab
    # ----------------------
    # Populated from the just-finished Stability recording when its Stop
    # button is pressed (see stab_stop()). Two panels: a PSD of the raw
    # tunneling current (peak-marked resonance, e.g. tip/collet ringing) and
    # an Allan deviation (classifies white-noise vs random-walk vs linear
    # drift, and predicts the best achievable dwell time before drift
    # dominates). Math lives in stab_metrics.py.

    def build_fourier_tab(self):
        """Programmatically add a 'Fourier Analysis' tab: PSD (with peak
        marker) + Allan deviation (with noise-type reference slopes)."""

        tab = QWidget()
        outer = QVBoxLayout(tab)
        outer.setContentsMargins(4, 4, 4, 4)

        self.lblFourierStats = QLabel(
            "No data yet — record a Stability session, then press Stop."
        )
        self.lblFourierStats.setStyleSheet("font-family: monospace;")
        outer.addWidget(self.lblFourierStats)

        row = QHBoxLayout()

        self.pltFourierPsd = plotframe.PlotFrame()
        self.pltFourierPsd.add_plot(
            label="PSD", xlabel="Frequency (Hz)", ylabel="Power (A^2/Hz)",
            pen=pg.mkPen("b", width=2),
        )
        self.pltFourierPsd.set_log_mode(x=True, y=True)
        self.pltFourierPsd.disable_si_prefix()
        row.addWidget(self.pltFourierPsd, 1)

        self.pltFourierAllan = plotframe.PlotFrame()
        self.pltFourierAllan.add_plot(
            label="Allan deviation", xlabel="Averaging time tau (s)",
            ylabel="sigma_A (A)", pen=pg.mkPen("b", width=2),
        )
        self.pltFourierAllan.set_log_mode(x=True, y=True)
        self.pltFourierAllan.disable_si_prefix()
        self.pltFourierAllan.add_extra_curve(
            "white", label="white noise (-1/2)",
            pen=pg.mkPen("g", width=1, style=QtCore.Qt.PenStyle.DashLine))
        self.pltFourierAllan.add_extra_curve(
            "randomwalk", label="random-walk (+1/2)",
            pen=pg.mkPen((255, 140, 0), width=1, style=QtCore.Qt.PenStyle.DashLine))
        self.pltFourierAllan.add_extra_curve(
            "drift", label="linear drift (+1)",
            pen=pg.mkPen("r", width=1, style=QtCore.Qt.PenStyle.DashLine))
        row.addWidget(self.pltFourierAllan, 1)

        outer.addLayout(row, 1)

        self._fourierTab = tab
        self.ui.tabWidget.addTab(tab, "Fourier Analysis")

    _VERDICT_LABELS = {
        "TUNNELING_LIKE": "TUNNELING-LIKE",
        "NOISE_ONLY": "NOISE ONLY (electronics floor, not the junction)",
        "CONTACT": "CONTACT (tip railed against surface)",
        "EMI_CONTAMINATED": "EMI CONTAMINATED (bench interference)",
        "INSUFFICIENT": "INSUFFICIENT DATA",
    }
    _VERDICT_COLORS = {
        "TUNNELING_LIKE": "#1a7f2e",   # green
        "INSUFFICIENT": "#8a6d00",     # amber
    }

    def _fourier_verdict_banner(self, verdict):
        """(banner_text, css_color) for the tunneling verdict, or ('', black)."""
        if not verdict:
            return "", "black"
        name = verdict.get("verdict", "?")
        label = self._VERDICT_LABELS.get(name, name)
        crit = verdict.get("criteria", {})
        mos = crit.get("signed_mean_over_sigma")
        detail = ""
        if mos is not None:
            need = crit.get("required_sigmas", 3.0)
            detail = f"  (signed mean/sigma={mos:.2f}, need >={need:.0f})"
        color = self._VERDICT_COLORS.get(name, "#b00020")   # default red
        return f"VERDICT: {label}{detail}\n", color

    def refresh_fourier_analysis(self, psd, allan, verdict=None):
        """Populate the tab from the PSD + Allan results computed at Stop
        time in stab_stop() (either may be None if the recording was too
        short for that analysis).  ``verdict`` is the stab_runner grading of
        the session, surfaced as an unambiguous tunneling banner."""
        banner, color = self._fourier_verdict_banner(verdict)
        self.lblFourierStats.setStyleSheet(
            f"font-family: monospace; font-weight: bold; color: {color};")
        if psd is None and allan is None:
            self.lblFourierStats.setText(
                banner +
                "Not enough data for Fourier analysis "
                "(need a longer Stability recording)."
            )
            return

        if psd is not None:
            self.pltFourierPsd.update_plot(psd["freqs_hz"][1:], psd["psd"][1:])
            # Only mark the peak when it stands clear of the broadband
            # floor — the argmax of a flat spectrum is not a resonance.
            if psd["peak_significant"]:
                self.pltFourierPsd.mark_point(
                    psd["peak_freq_hz"], psd["peak_power"],
                    text=f'{psd["peak_freq_hz"]:.2f} Hz '
                         f'({psd["peak_snr"]:.1f}x floor)',
                )
            else:
                self.pltFourierPsd.clear_marker()

        if allan is not None:
            self.pltFourierAllan.update_plot(allan["taus_s"], allan["sigma_a"])
            self.pltFourierAllan.update_extra_curve(
                "white", allan["taus_s"], allan["ref_white"])
            self.pltFourierAllan.update_extra_curve(
                "randomwalk", allan["taus_s"], allan["ref_randomwalk"])
            self.pltFourierAllan.update_extra_curve(
                "drift", allan["taus_s"], allan["ref_drift"])
            self.pltFourierAllan.mark_point(
                allan["tau_opt_s"], allan["sigma_min"],
                text=f'best dwell ~{allan["tau_opt_s"]:.2f}s',
            )

        if psd is None:
            peak_txt = "n/a"
        elif not psd["peak_significant"]:
            peak_txt = (
                f'none (max bin {psd["peak_snr"]:.1f}x floor, '
                f'noise needs >{psd["peak_snr_threshold"]:.1f}x)'
            )
        else:
            peak_txt = (
                f'{psd["peak_freq_hz"]:.2f} Hz '
                f'(P={psd["peak_power"]:.2e} A^2/Hz, '
                f'{psd["peak_snr"]:.1f}x floor)'
            )

        if allan is None:
            allan_txt = "Allan: n/a"
        else:
            sigma_txt = f'{allan["sigma_min"]:.2e} A'
            # |mean of signed samples|, NOT mean(|samples|): for zero-mean
            # noise mean(|x|) ~ 0.8*sigma, which fakes a "mean current" and
            # yields a bogus pm conversion when there is no tunneling.
            mean_a = abs(float(np.mean(self.stab_samples)))
            sigma_pm = stab_metrics.sigma_to_pm(
                allan["sigma_min"], mean_a, self.STAB_PM_PER_LN
            )
            if sigma_pm is not None:
                sigma_txt += f' (~{sigma_pm:.1f} pm)'
            allan_txt = (
                f'Allan slope={allan["slope"]:+.2f} '
                f'(~{stab_metrics.classify_allan_slope(allan["slope"])})   '
                f'best dwell~{allan["tau_opt_s"]:.2f}s   '
                f'sigma_min={sigma_txt}'
            )

        self.lblFourierStats.setText(
            banner +
            f"PSD peak={peak_txt}   {allan_txt}   [n={len(self.stab_samples)}]"
        )

    # ----------------------
    # Real-Time Updates
    # ----------------------

    def update_real_time(self):
        #print("update_real_time running")
        if self.stm.busy:
            return

        # While any reader thread owns the serial port (scan reader, STRM
        # stream, dedicated raw capture), polling GSTS would race the
        # binary-frame parser on the wire and corrupt both streams.  Use the
        # cached status instead — it keeps updating via pushed 'S' frames
        # (forwarded by the scan reader during scans), so the Main tab amp
        # scroll runs always, no matter what else is going on.
        scan_owns_port = (getattr(self, "_scan_ctrl", None)
                          and self._scan_ctrl.is_running())
        if scan_owns_port or self._stab_streaming \
                or self._raw_reader is not None:
            status = self.stm.status
        else:
            status = self.stm.get_status()

        if status is None:
            return

        # Keep the Continuous Scan Z slider tracking the TRUE Z DAC.  The
        # scan-line feed (zUpdated) only takes over when feedback owns Z —
        # in constant-height scans status.dac_z is the honest source.
        if not (scan_owns_port and status.is_const_current):
            self._set_cs_zslider_from_stream(status.dac_z)

        # One-state mirrors: reflect firmware truth into every DAC/bias
        # widget.  Skipped while the operator is composing (any of these
        # spins was user-edited <3 s ago, has focus, or a bar is mid-drag)
        # so typing "35014 then Set Bias" is never clobbered mid-flight.
        # The spin handlers are display-only (labels/bar echoes), so
        # mirroring through them sends nothing.
        composing = (time.time() - self._dac_edit_t < 3.0
                     or any(sp.hasFocus() for sp in
                            (self.ui.spnDACZ, self.ui.spnBias,
                             self.ui.spnDACX, self.ui.spnDACY))
                     or self.ui.scr_DACZ.isSliderDown()
                     or self.ui.scr_Bias.isSliderDown()
                     or self._cs_zslider.isSliderDown())
        if not composing:
            self._mirror_updating = True
            try:
                self.ui.spnDACZ.setValue(int(status.dac_z))
                self.ui.spnBias.setValue(int(status.bias))
                self.ui.spnDACX.setValue(int(status.dac_x))
                self.ui.spnDACY.setValue(int(status.dac_y))
                for bar, val in ((self.ui.scr_Bias, status.bias),
                                 (self.ui.scr_DACX, status.dac_x),
                                 (self.ui.scr_DACY, status.dac_y)):
                    bar.blockSignals(True)
                    bar.setValue(int(val))
                    bar.blockSignals(False)
            finally:
                self._mirror_updating = False

        # Display truth: firmware constant-current state is also set by
        # ENGA and SURVIVES a scan HALT (only RTRC/CCOF clear it), so the
        # checkbox must mirror the firmware, not just its own clicks
        # (bench 2026-07-15: box unchecked while a legacy scan audibly ran
        # Z feedback).  blockSignals: mirroring must not re-send CCON/CCOF.
        if self.ui.chkConstCurrent.isChecked() != status.is_const_current:
            self.ui.chkConstCurrent.blockSignals(True)
            self.ui.chkConstCurrent.setChecked(status.is_const_current)
            self.ui.chkConstCurrent.blockSignals(False)

        # Z ownership: with feedback engaged (constant-current mode) the ISR
        # PI rewrites the Z DAC every tick, so manual Z is meaningless —
        # grey the manual Z controls.  In constant-height mode (feedback
        # off) they stay live: the slider IS the flying-height control.
        z_manual = not status.is_const_current
        # Err-channel display mode follows the true feedback state:
        # constant height -> linearized current (real topology contrast,
        # proven in the 2026-07-15 pipeline A/B); CC -> raw feedback error.
        self._cs_raster.set_current_display(
            z_manual,
            self._scan_ctrl._pa_to_setpoint_lsb(self._cs_setpoint.value()))
        self._cs_zowner.setText(
            "" if z_manual else
            "Z owned by feedback\n(Constant Current ON —\nRetract or CC-off "
            "to control Z)")
        if self._cs_zslider.isEnabled() != z_manual:
            self._cs_zslider.setEnabled(z_manual)
            self.ui.scr_DACZ.setEnabled(z_manual)
            tip = ("" if z_manual else
                   "Z is owned by the feedback loop (constant-current mode)"
                   " — Retract/CC-off to control Z manually")
            self._cs_zslider.setToolTip(tip)
            self.ui.scr_DACZ.setToolTip(tip)

        history = self.stm.history

        if not history:
            return

        plot_x = [h.time_millis for h in history]
        max_time = max(plot_x)

        cutoff = max_time - 60000

        recent = [h for h in history if h.time_millis >= cutoff]

        plot_x = [(h.time_millis - max_time) / 1000.0 for h in recent]

        plot_adc = [
            stm_control.STM_Status.adc_to_amp(h.adc)
            for h in recent
        ]

        plot_steps = [h.steps for h in recent]

        #print(f"[PLOT] points={len(plot_x)} adc={plot_adc[-1] if plot_adc else 'n/a'}")

        self.pltCurrent.update_plot(plot_x, plot_adc)
        self.pltSteps.update_plot(plot_x, plot_steps)
        if getattr(self, "_cs_amp", None) is not None:
            self._cs_amp.update_plot(plot_x, plot_adc)
    # ----------------------
    # Image Updates
    # ----------------------

    @Slot()
    def _main_auto_levels(self):
        """Auto-level the Main tab's own image panels (2–98 percentile).
        View-specific by design (operator 2026-07-15): this button levels
        what the Main tab shows; the Continuous Scan tab has its own
        Auto-levels for the raster.  (PlotFrame.auto_levels() was calling
        a nonexistent pyqtgraph API, so Main-tab leveling never worked.)"""
        for pf in (self.pltVals, self.pltDAC, self.pltNoise):
            img = getattr(getattr(pf, "image_item", None), "image", None)
            if img is None or getattr(img, "size", 0) == 0:
                continue
            lo, hi = np.percentile(img, [2, 98])
            if hi <= lo:
                hi = lo + 1.0
            try:
                # Drive the histogram region — it propagates to the image.
                pf.hist_lut.item.setLevels(float(lo), float(hi))
            except Exception:
                pf.set_levels(float(lo), float(hi))

    def update_images(self):

        if not hasattr(self.stm, "scan_config"):
            return

        x_start, x_end, x_res, y_start, y_end, y_res = self.stm.scan_config

        self.pltVals.update_image(
            self.stm.scan_adc.T,
            extent=[y_start, y_end, x_start, x_end]
        )

        self.pltNoise.update_image(
            self.stm.scan_noise,
            extent=[y_start, y_end, x_start, x_end]
        )

        self.pltDAC.update_image(
            self.stm.scan_dacz.T,
            extent=[y_start, y_end, x_start, x_end]
        )
    #---------------------------
    # data file saving
    #---------------------------

    # this function saves the IV data to a text file.
    def save_data_to_file(self,filename_prefix, data_to_store):
        ts = int(datetime.timestamp(datetime.now()) * 1000)
        with open(f"{filename_prefix}_{ts}.csv", 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            for data in data_to_store:
                writer.writerow(data)

    def save_iv_ascii(self,prefix, x, y):
        #ts = int(datetime.datetime.now().timestamp() * 1000)
        ts = int(datetime.timestamp(datetime.now()) * 1000)
        filename = f"{prefix}_{ts}.txt"

        with open(filename, "w") as f:
            f.write("# Gwyddion ASCII curve\n")
            f.write("# XUnit=V\n")
            f.write("# YUnit=A\n")
            f.write("# Title=IV Curve\n")
            for xv, yv in zip(x, y):
                f.write(f"{xv} {yv}\n")

        print(f"[IV] Saved ASCII curve: {filename}")


    def save_gsf(self,filename, image, x_real, y_real,
                 x_offset=0.0, y_offset=0.0,
                 xy_units="m", z_units="A",
                 title="STM Scan"):

        image = np.asarray(image, dtype=np.float32)

        yres, xres = image.shape

        header = [
            "Gwyddion Simple Field 1.0",
            f"XRes = {xres}",
            f"YRes = {yres}",
            f"XReal = {x_real}",
            f"YReal = {y_real}",
            f"XOffset = {x_offset}",
            f"YOffset = {y_offset}",
            f"XYUnits = {xy_units}",
            f"ZUnits = {z_units}",
            f"Title = {title}",
            ""
        ]

        header_str = "\n".join(header)

        # Pad header to multiple of 4 bytes
        header_bytes = header_str.encode("utf-8")
        padding = (4 - (len(header_bytes) % 4)) % 4
        header_bytes += b"\0" * padding

        with open(filename, "wb") as f:
            f.write(header_bytes)
            image.astype("<f4").tofile(f)

    # ----------------------
    # Save Scan Image
    # ----------------------

    def save_scan_image(self, prefix):
        print(prefix)
        x_start, x_end, x_res, y_start, y_end, y_res = self.stm.scan_config
        ts = int(datetime.timestamp(datetime.now()) * 1000)
        np.savetxt(f"{prefix}_adc_{ts}.txt", self.stm.scan_adc)
        print(f"{prefix}_adc_{ts}.txt")
        #now as tiff
        self.pltVals.save_figure(f"{prefix}_adc_{ts}.png")
        print(f"{prefix}_adc_{ts}.png")

        bias = self.ui.spnBias.value()
        tifffile.imwrite(
            f"{prefix}_adc_{ts}.tiff",
            self.stm.scan_adc.astype(np.uint16),
            metadata={
                "XStart": x_start,
                "XEnd": x_end,
                "YStart": y_start,
                "YEnd": y_end,
                "Bias": bias
            }
        )
        print(f"{prefix}_adc_{ts}.tiff")
        self.save_gsf(
            f"{prefix}_adc_{ts}.gsf",
            self.stm.scan_adc,
            x_real=500e-9,
            y_real=500e-9,
            xy_units="m",
            z_units="A",
            title="Tunneling Current"
        )

        print(f"{prefix}_adc_{ts}.gsf")
        self.save_gsf(
            f"{prefix}_topography_{ts}.gsf",
            self.stm.scan_dacz.T,
            x_real=500e-9,
            y_real=500e-9,
            xy_units="m",
            z_units="m",
            title="Topography"
        )
        print(f"{prefix}_topography_{ts}.gsf")


    # =========================================================================
    # Continuous-scan tab (Dan-style, Phase 3)
    # =========================================================================

    def _build_continuous_scan_tab(self):
        """Build the 'Continuous Scan' tab and wire it to ScanController."""

        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(4, 4, 4, 4)
        tab_layout.setSpacing(4)

        top_row = QHBoxLayout()

        # ---- Scan geometry (physical units) ---------------------------------
        geo_box = QGroupBox("Scan geometry")
        geo_form = QFormLayout(geo_box)

        self._cs_scansize = QDoubleSpinBox()
        self._cs_scansize.setRange(0.1, 10000.0)
        self._cs_scansize.setDecimals(2)
        # 30 nm stays within a ±5 V DAC at the default 5 nm/V piezo cal
        self._cs_scansize.setValue(30.0)
        self._cs_scansize.setSuffix(" nm")
        geo_form.addRow("Scan size:", self._cs_scansize)

        self._cs_pixels = QSpinBox()
        self._cs_pixels.setRange(2, 2048)
        self._cs_pixels.setValue(512)
        self._cs_pixels.setSingleStep(64)
        geo_form.addRow("Pixels/line:", self._cs_pixels)

        self._cs_linerate = QDoubleSpinBox()
        self._cs_linerate.setRange(0.01, 50.0)
        self._cs_linerate.setDecimals(2)
        self._cs_linerate.setValue(30.0)
        self._cs_linerate.setSuffix(" Hz")
        geo_form.addRow("Line rate:", self._cs_linerate)

        # Explicit sample density (FW 5.2 SPPX): 0 = auto-derived from
        # line rate x pixels/line; >0 pins samples averaged per pixel —
        # the continuous-scan equivalent of the Scanning tab's Samples/Pix.
        self._cs_spp = QSpinBox()
        self._cs_spp.setRange(0, 4000)
        self._cs_spp.setValue(0)
        self._cs_spp.setSpecialValueText("auto")
        self._cs_spp.setToolTip(
            "Samples averaged per pixel (SPPX).  auto = derived from line "
            "rate and pixels/line; pinning it changes the true line rate.")
        geo_form.addRow("Samples/px:", self._cs_spp)

        self._cs_xofs = QDoubleSpinBox()
        self._cs_xofs.setRange(-5000.0, 5000.0)
        self._cs_xofs.setDecimals(2)
        self._cs_xofs.setValue(0.0)
        self._cs_xofs.setSuffix(" nm")
        geo_form.addRow("X offset:", self._cs_xofs)

        self._cs_yofs = QDoubleSpinBox()
        self._cs_yofs.setRange(-5000.0, 5000.0)
        self._cs_yofs.setDecimals(2)
        self._cs_yofs.setValue(0.0)
        self._cs_yofs.setSuffix(" nm")
        geo_form.addRow("Y offset:", self._cs_yofs)

        top_row.addWidget(geo_box)

        # ---- Feedback (Bias lives on the left-panel spnBias — not duplicated)
        fb_box = QGroupBox("Feedback")
        fb_form = QFormLayout(fb_box)

        self._cs_setpoint = QDoubleSpinBox()
        self._cs_setpoint.setRange(0.0, 100000.0)
        self._cs_setpoint.setDecimals(1)
        # 1000 pA = 1 nA — a realistic STM setpoint (Dan's default ≈ 1 nA).
        # Sub-nA values round to 0 LSB at a 100 MΩ preamp and would trip
        # the firmware's "ENGA refused: no setpoint" safety check.
        self._cs_setpoint.setValue(1000.0)
        self._cs_setpoint.setSuffix(" pA")
        fb_form.addRow("Setpoint:", self._cs_setpoint)

        self._cs_kp = QDoubleSpinBox()
        self._cs_kp.setRange(0.0, 1e6)
        self._cs_kp.setDecimals(4)
        self._cs_kp.setValue(0.0)
        fb_form.addRow("Kp:", self._cs_kp)

        self._cs_ki = QDoubleSpinBox()
        self._cs_ki.setRange(0.0, 1e6)
        self._cs_ki.setDecimals(4)
        self._cs_ki.setValue(4.5776)
        fb_form.addRow("Ki:", self._cs_ki)

        # Slow anti-drift Z servo for constant-height mode (~0.1 Hz
        # bandwidth: cancels thermal/creep drift of the baseline without
        # touching in-line features).  Holds a junction, never seeks one.
        from PySide6.QtWidgets import QCheckBox
        self._cs_drift_hold = QCheckBox("Drift hold (slow Z)")
        self._cs_drift_hold.setToolTip(
            "Constant-height anti-drift: nudges the Z baseline every 0.5 s "
            "(capped, ~0.1 Hz bandwidth) to keep the mean current at the "
            "Setpoint.  Freezes if the junction opens — never approaches. "
            "Disabled while real feedback (CC/ENGA) owns Z.")
        fb_form.addRow("", self._cs_drift_hold)
        self._cs_drift_lbl = QLabel("drift: —")
        fb_form.addRow("", self._cs_drift_lbl)

        top_row.addWidget(fb_box)

        # ---- Z-piezo position gauge -----------------------------------------
        gauge_box = QGroupBox("Z-piezo")
        gauge_layout = QVBoxLayout(gauge_box)
        gauge_layout.setSpacing(2)
        # Labels reflect the TIP-SAMPLE GAP, not raw piezo extension: on
        # this geometry higher DAC = smaller gap = toward contact (firmware
        # approach sweeps DAC UP to find the surface, stm_firmware:815).
        # The old "Extended"(top)/"Retracted"(bottom) was dangerously
        # backwards — it labeled the crash direction "Retracted" (operator
        # caught this 2026-07-15).
        _lbl_up = QLabel("▲ Away (low I, safe)")
        _lbl_up.setStyleSheet("color: #2a7;")
        gauge_layout.addWidget(_lbl_up, alignment=Qt.AlignHCenter)
        # Z-piezo slider: live Z readout AND a real drag handle (the old
        # QProgressBar had no handle and rendered as a hairline on Windows —
        # bench 2026-07-14).  Dragging streams DACZ through the same
        # throttled sender as the Configuration-tab drag bar; incoming
        # stream updates leave the handle alone while it is being dragged.
        self._cs_zslider = QSlider(Qt.Vertical)
        self._cs_zslider.setRange(0, 65535)
        self._cs_zslider.setValue(32768)
        self._cs_zslider.setSingleStep(10)
        self._cs_zslider.setPageStep(1000)
        self._cs_zslider.setMinimumWidth(28)
        # Inverted appearance so the MAX (high DAC = toward sample = more
        # current, per the firmware approach sweeping DAC up) sits at the
        # BOTTOM.  Result: dragging DOWN moves the tip toward the sample
        # (intuitive, like a physical Z knob) and matches the ▲Away/
        # ▼Toward-sample labels.  My first labeling was inverted — operator
        # caught it 2026-07-15.
        self._cs_zslider.setInvertedAppearance(True)
        self._cs_zslider.valueChanged.connect(self._on_cs_zslider_changed)
        gauge_layout.addWidget(self._cs_zslider,
                               alignment=Qt.AlignHCenter)
        self._cs_zval = QLabel("—")
        gauge_layout.addWidget(self._cs_zval, alignment=Qt.AlignHCenter)
        _lbl_dn = QLabel("▼ Toward sample (contact)")
        _lbl_dn.setStyleSheet("color: #c33;")
        gauge_layout.addWidget(_lbl_dn, alignment=Qt.AlignHCenter)
        # Loud ownership banner: greyed-out alone was too subtle
        # (operator 2026-07-15: "can't even drag the slider").
        self._cs_zowner = QLabel("")
        self._cs_zowner.setStyleSheet("color: #d07000; font-weight: bold;")
        self._cs_zowner.setWordWrap(True)
        gauge_layout.addWidget(self._cs_zowner, alignment=Qt.AlignHCenter)
        top_row.addWidget(gauge_box)

        # ---- Actions --------------------------------------------------------
        act_box = QGroupBox("Control")
        act_layout = QVBoxLayout(act_box)

        self._cs_btn_apply = QPushButton("Apply settings")
        self._cs_btn_apply.clicked.connect(self._on_cs_apply_settings)
        act_layout.addWidget(self._cs_btn_apply)

        self._cs_btn_engage = QPushButton("Engage (ENGA)")
        self._cs_btn_engage.clicked.connect(self._scan_ctrl.engage)
        act_layout.addWidget(self._cs_btn_engage)

        self._cs_btn_retract = QPushButton("Retract (RTRC)")
        self._cs_btn_retract.clicked.connect(self._scan_ctrl.retract)
        act_layout.addWidget(self._cs_btn_retract)

        self._cs_btn_run = QPushButton("▶  RUN")
        self._cs_btn_run.setStyleSheet("background-color: #4CAF50; color: white;")
        self._cs_btn_run.clicked.connect(self._on_cs_run)
        act_layout.addWidget(self._cs_btn_run)

        self._cs_btn_halt = QPushButton("■  HALT")
        self._cs_btn_halt.setStyleSheet("background-color: #f44336; color: white;")
        self._cs_btn_halt.clicked.connect(self._on_cs_halt)
        act_layout.addWidget(self._cs_btn_halt)

        # ---- Superscan: fuse N drift-jittered frames into one HD image ----
        from PySide6.QtWidgets import QComboBox as _QCB
        self._cs_super_mode = _QCB()
        for key, (label, _up) in superscan.MODES.items():
            self._cs_super_mode.addItem(label, key)
        self._cs_super_mode.setCurrentIndex(
            list(superscan.MODES).index(superscan.DEFAULT_MODE))
        act_layout.addWidget(self._cs_super_mode)

        self._cs_btn_super = QPushButton("Build Superscan (10)")
        self._cs_btn_super.setToolTip(
            "Capture 10 continuous-scan frames and reconstruct one "
            "higher-definition image (drift = dither).  Opens in a popup.")
        self._cs_btn_super.clicked.connect(self._on_build_superscan)
        act_layout.addWidget(self._cs_btn_super)

        act_layout.addStretch()

        self._cs_status_lbl = QLabel("Idle")
        act_layout.addWidget(self._cs_status_lbl)

        top_row.addWidget(act_box)

        # ---- Live current scroll (copy of the Main tab amp display) ------
        # Fed from the same status history in update_real_time, which keeps
        # flowing during scans via the forwarded 'S' frames — so the current
        # trace is visible right next to the scan controls (bench request
        # 2026-07-14).
        amp_box = QGroupBox("Current (live)")
        amp_layout = QVBoxLayout(amp_box)
        self._cs_amp = plotframe.PlotFrame()
        self._cs_amp.add_plot("Current", "time(s)", "amp",
                              pen=pg.mkPen("r", width=2))
        amp_layout.addWidget(self._cs_amp)
        # Narrow horizontal strip: the pyqtgraph widget otherwise expands
        # square-ish and inflates the whole top row (bench 2026-07-14).
        # Width stays responsive (stretch=1); height is capped so the top
        # row keeps the height the groupboxes set on their own.
        amp_box.setMaximumHeight(235)
        self._cs_amp.setMinimumHeight(80)
        top_row.addWidget(amp_box, stretch=1)

        tab_layout.addLayout(top_row)

        # ---- Live raster images ---------------------------------------------
        self._cs_raster = live_raster.LiveRaster(
            self._cal,
            # One frame = pixels/line ÷ 2 physical rows: a line-counter
            # cycle holds a full Y up+down triangle (dy = dx/px), folded
            # onto px/2 rows; trace half gives px/2 columns -> true square
            # (corrected 2026-07-15).
            image_height=self._cs_pixels.value() // 2,
            pixels_per_line=self._cs_pixels.value(),
            parent=tab
        )
        tab_layout.addWidget(self._cs_raster, stretch=1)

        # Wire ScanController → frame log / LiveRaster / gauge / status.
        # The frame logger MUST be connected first: Qt invokes slots in
        # connection order, so every line is on disk before it is drawn.
        self._frame_logger = frame_logger.FrameLogger(log_dir="scans")
        self._scan_ctrl.lineReady.connect(self._frame_logger.on_line)
        self._scan_ctrl.lineReady.connect(self._cs_raster.update_line)
        self._cs_frames_since_run = 0
        self._scan_ctrl.lineReady.connect(self._on_cs_frame_seen)
        self._scan_ctrl.zUpdated.connect(self._set_cs_zslider_from_scan)
        self._scan_ctrl.engaged.connect(
            lambda: self._cs_status_lbl.setText("Engaged"))
        self._scan_ctrl.retracted.connect(
            lambda: self._cs_status_lbl.setText("Retracted"))
        self._scan_ctrl.asciiLine.connect(self._on_ascii_during_scan)
        # STRM 'S' frames keep arriving during a scan; forward them so the
        # session recording and the Main amp scroll never pause.  The
        # logging tap is a DirectConnection (stays on the reader thread).
        self._scan_ctrl.statusFrame.connect(self._on_status_frame)
        self._scan_ctrl.statusFrame.connect(
            self._log_status_direct, QtCore.Qt.DirectConnection)

        # Geometry spinboxes -> red rectangle (live mirror; typing nm stays
        # exact/authoritative — the box is a view of the same truth).
        for _sb in (self._cs_scansize, self._cs_xofs, self._cs_yofs):
            _sb.valueChanged.connect(self._update_box_from_cs)
        self._update_box_from_cs()   # initial mirror at startup

        # Superscan capture state.
        self._ss_active = False
        self._ss_frames = []
        self._ss_cur_lines = []
        self._ss_last_raw = -1
        self._ss_H = 128
        self._ss_target = 10
        self._ss_popups = []

        # Anti-drift servo tick (2 Hz; the step cap sets the ~0.1 Hz
        # correction bandwidth, well below any line rate).
        self._drift_hist = deque(maxlen=240)   # (wall_t, cumulative_dz)
        self._drift_dz_total = 0
        self._drift_timer = QTimer(self)
        self._drift_timer.timeout.connect(self._drift_hold_tick)
        self._drift_timer.start(500)
        self._scan_ctrl.runningChanged.connect(self._on_scan_running_changed)
        # Right-click-to-pan: raster → offset spinboxes → firmware
        self._cs_raster.scanOffsetRequested.connect(self._on_cs_offset_picked)

        self._cs_tab = tab
        self.ui.tabWidget.addTab(tab, "Continuous Scan")
        # Auto 'View All' whenever this tab is shown — stale viewbox zoom
        # after rect/buffer changes otherwise needs a manual right-click
        # (bench 2026-07-15).
        self.ui.tabWidget.currentChanged.connect(self._on_tab_changed_cs)

    # ---- Continuous-scan slot handlers ---------------------------------------

    @Slot()
    def _on_cs_apply_settings(self):
        """Push all current UI values (physical units) to the firmware."""
        self._scan_ctrl.set_scan_size(self._cs_scansize.value())
        n = self._cs_pixels.value()
        self._scan_ctrl.set_pixels_per_line(n)
        self._scan_ctrl.set_line_rate(self._cs_linerate.value())
        self._scan_ctrl.set_samples_per_pixel(self._cs_spp.value())
        self._scan_ctrl.set_offsets(self._cs_xofs.value(),
                                    self._cs_yofs.value())
        self._scan_ctrl.set_setpoint(self._cs_setpoint.value())
        self._scan_ctrl.set_kp(self._cs_kp.value())
        self._scan_ctrl.set_ki(self._cs_ki.value())
        # Keep the raster's geometry mirror current (for right-click panning)
        self._cs_raster.set_scan_geometry(
            self._cs_scansize.value(),
            self._cs_xofs.value(),
            self._cs_yofs.value())
        self._cs_raster.resize_buffers(n // 2, n)  # Y-folded square (N/2 x N/2)
        self._cs_status_lbl.setText("Settings applied")

    @Slot(float, float)
    def _on_cs_offset_picked(self, xo_nm: float, yo_nm: float):
        """Right-click on the Z image recentered the scan."""
        self._cs_xofs.setValue(xo_nm)
        self._cs_yofs.setValue(yo_nm)
        self._scan_ctrl.set_offsets(xo_nm, yo_nm)
        self._cs_raster.set_scan_geometry(
            self._cs_scansize.value(), xo_nm, yo_nm)
        self._cs_status_lbl.setText(
            f"Recentered ({xo_nm:.1f}, {yo_nm:.1f}) nm")

    @Slot(int)
    def _on_tab_changed_cs(self, index):
        if self.ui.tabWidget.widget(index) is getattr(self, "_cs_tab", None):
            self._cs_raster.auto_range()

    @Slot()
    def _on_cs_run(self):
        if not self.stm.is_opened:
            self._cs_status_lbl.setText("Serial not open")
            return
        if self.stm.firmware_tagged_status:
            # "STAT:"-tagged GSTS replies fingerprint the pre-Phase-3
            # firmware, which has no RUN handler / 'L' frames — a RUN would
            # be silently ignored and the raster would stay blank.
            self._cs_status_lbl.setText(
                "Old firmware detected (STAT:-tagged status) — no "
                "continuous-scan support. Reflash teensy/arduinosrc/main."
            )
            print("[ContinuousScan] REFUSED: firmware speaks the old "
                  "protocol (STAT: prefix); RUN would be ignored.")
            return
        if self._stab_streaming:
            # Single-reader rule: hand the port from the recording's stream
            # reader to the scan reader (two readers race read() and corrupt
            # each other — GUI freeze + 19 GB runaway, bench 2026-07-14).
            # RECORDING CONTINUES: firmware STRM keeps pushing and the scan
            # reader forwards 'S' frames to the same writer thread.
            print("[ContinuousScan] port handoff: recording stream reader "
                  "-> scan reader (recording continues)")
            self._pause_stab_stream_for_scan()
        self._on_cs_apply_settings()
        self._cs_frames_since_run = 0
        self._scan_ctrl.start_run()
        self._cs_status_lbl.setText("Running…")
        # Watchdog: if the firmware never streams a frame, say so instead
        # of leaving a silently blank raster.
        QtCore.QTimer.singleShot(3000, self._cs_check_stream_alive)

    @Slot(int, object, object)
    def _on_cs_frame_seen(self, *_):
        self._cs_frames_since_run += 1

    # ---- Superscan capture + reconstruct -------------------------------
    def _on_build_superscan(self):
        """Capture N continuous-scan frames (countdown), reconstruct, popup.
        Frames are collected by folding one Y-triangle cycle per frame from
        the live lineReady stream — same math as the raster/superscan."""
        if self._ss_active:
            return
        if not self._scan_ctrl.is_running():
            self._cs_status_lbl.setText("Superscan: press RUN first")
            return
        self._ss_target = 10
        self._ss_H = self._cs_pixels.value() // 2
        self._ss_frames = []
        self._ss_cur_lines = []
        self._ss_last_raw = -1
        self._ss_active = True
        self._cs_btn_super.setEnabled(False)
        self._scan_ctrl.lineReady.connect(self._ss_on_line)
        self._cs_status_lbl.setText(f"Superscan: capturing 10…")

    @Slot(int, object, object)
    def _ss_on_line(self, line_number, z_arr, err_arr):
        half = len(err_arr) // 2
        self._ss_cur_lines.append((line_number, np.asarray(err_arr[:half],
                                                            dtype=np.float64)))
        raw = line_number % (2 * self._ss_H)
        if raw < self._ss_last_raw:      # one Y up+down cycle completed
            lines, self._ss_cur_lines = self._ss_cur_lines[:-1], \
                [self._ss_cur_lines[-1]]
            if len(lines) > self._ss_H:
                setp = self._scan_ctrl._pa_to_setpoint_lsb(
                    self._cs_setpoint.value())
                folded = superscan.fold_frame(
                    [(ln, superscan.linearize_err(tr, setp))
                     for ln, tr in lines], self._ss_H)
                self._ss_frames.append(folded)
                left = self._ss_target - len(self._ss_frames)
                self._cs_status_lbl.setText(
                    f"Superscan: capturing {left}…" if left > 0
                    else "Superscan: reconstructing…")
                if len(self._ss_frames) >= self._ss_target:
                    self._ss_finish()
        self._ss_last_raw = raw

    def _ss_finish(self):
        try:
            self._scan_ctrl.lineReady.disconnect(self._ss_on_line)
        except (RuntimeError, TypeError):
            pass
        self._ss_active = False
        self._cs_btn_super.setEnabled(True)
        mode = self._cs_super_mode.currentData()
        try:
            hi, shifts, stats = superscan.superscan(self._ss_frames, mode=mode)
        except Exception as e:
            self._cs_status_lbl.setText(f"Superscan failed: {e}")
            return
        session_journal.note(
            f"superscan {mode}: {stats['n_frames']} frames, "
            f"max drift {stats['max_drift_px']:.1f}px, "
            f"std {stats['single_frame_std']:.0f}->{stats['superscan_std']:.0f}",
            src="agent")
        self._cs_status_lbl.setText(
            f"Superscan done ({stats['mode_label']})")
        self._show_superscan_popup(hi, stats)

    def _show_superscan_popup(self, hi, stats):
        from PySide6.QtWidgets import QDialog
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Superscan — {stats['mode_label']}")
        dlg.resize(720, 780)
        lay = QVBoxLayout(dlg)
        pf = plotframe.PlotFrame()
        lo, hival = np.percentile(hi, [2, 98])
        pf.add_image(hi.T, label="Superscan (current, ADC counts)")
        lay.addWidget(pf)
        try:
            pf.set_levels(float(lo), float(hival))
        except Exception:
            pass
        drift = stats["max_drift_px"]
        gain = (stats["single_frame_std"] / stats["superscan_std"]
                if stats["superscan_std"] else 0)
        lay.addWidget(QLabel(
            f"{stats['n_frames']} frames · {stats['up']}× grid · "
            f"max drift {drift:.1f} px · size {hi.shape[1]}×{hi.shape[0]}"))
        row = QHBoxLayout()
        # Physical scale: the folded frame spans the commanded scan size in
        # BOTH axes (square), independent of the up-sampling factor.
        scan_nm = float(self._cs_scansize.value())
        scan_m = scan_nm * 1e-9
        nm_per_px = scan_nm / hi.shape[1]   # after up-sampling
        # ADC counts -> amps for a physically-labelled Z channel.
        amp_img = (hi * stm_control.STM_Status.adc_to_amp(1)).astype(np.float32)
        lay.addWidget(QLabel(
            f"pixel size {nm_per_px:.4f} nm/px · scan {scan_nm:.2f} nm "
            f"(embedded in .gsf)"))

        save = QPushButton("Save .gsf (scaled) + .npz")
        def _save():
            ts = int(datetime.timestamp(datetime.now()) * 1000)
            base = os.path.join("scans", f"superscan_{ts}")
            # A few saturation-rail pixels (~±102 nA) blow Gwyddion's linear
            # min->max color range, crushing the real 0.5-1 nA signal to
            # black (operator 2026-07-15).  The .gsf is the VIEW copy:
            # clip to robust [p0.5, p99.5] so it opens looking like the
            # popup.  The .npz keeps the FULL unclipped data for analysis.
            lo_c, hi_c = np.percentile(amp_img, [0.5, 99.5])
            gsf_img = np.clip(amp_img, lo_c, hi_c).astype(np.float32)
            n_clip = int((amp_img != gsf_img).sum())
            # Gwyddion Simple Field: physical units embedded (meters + amps),
            # so it opens at the true nm scale.
            self.save_gsf(base + ".gsf", gsf_img, scan_m, scan_m,
                          xy_units="m", z_units="A",
                          title=f"Superscan {stats['mode_label']}")
            np.savez_compressed(
                base + ".npz", image=hi, current_A=amp_img,
                shifts=np.array(stats["shifts"]),
                scan_size_nm=scan_nm, nm_per_pixel=nm_per_px,
                x_offset_nm=float(self._cs_xofs.value()),
                y_offset_nm=float(self._cs_yofs.value()),
                clip_range_A=np.array([lo_c, hi_c]),
                mode=stats["mode"], up=stats["up"])
            self._cs_status_lbl.setText(
                f"Superscan saved: {base}.gsf "
                f"({n_clip} rail px clipped for view; full data in .npz)")
        save.clicked.connect(_save)
        row.addWidget(save); row.addStretch()
        lay.addLayout(row)
        dlg.show()          # modeless: keep scanning underneath
        self._ss_popups.append(dlg)

    def _cs_check_stream_alive(self):
        if self._scan_ctrl.is_running() and self._cs_frames_since_run == 0:
            self._cs_status_lbl.setText(
                "RUN sent, but no scan frames after 3 s — firmware not "
                "streaming (old firmware flashed, or scan not producing "
                "lines). Check firmware version / reflash."
            )
            print("[ContinuousScan] WARNING: no 'L' frames within 3 s "
                  "of RUN.")

    @Slot()
    def _on_cs_halt(self):
        self._scan_ctrl.halt()
        self._cs_status_lbl.setText("Halted")

    @Slot(str)
    def _on_ascii_during_scan(self, line: str):
        """ASCII responses arriving while continuous scan is running.
        Parse known prefixes; ignore the rest."""
        try:
            parsed = self.stm.parse_ascii_line(line)
        except Exception:
            return
        # If a GSTS-style status row arrives, update STM.status so other
        # widgets remain consistent.
        if parsed.get('type') == 'unknown':
            raw = parsed.get('raw', '')
            parts = raw.split(',')
            if len(parts) == 10:
                try:
                    vals = [int(x) for x in parts]
                    self.stm.status = stm_control.STM_Status.from_list(vals)
                except ValueError:
                    pass

    def _scan_frame_settings(self):
        """Snapshot everything needed for faithful replay of a frame log."""
        sc = self._scan_ctrl
        spp = int(1e6 / max(sc.line_rate_hz * 40.0 * sc.pixels_per_line, 1.0))
        cal = {name: getattr(self._cal, name) for name in calibration.FIELDS}
        return {
            "scan_size_nm": sc.scan_size_nm,
            "pixels_per_line": sc.pixels_per_line,
            "line_rate_hz": sc.line_rate_hz,
            "x_offset_nm": sc.xo_nm,
            "y_offset_nm": sc.yo_nm,
            "setpoint_pa": sc.setpoint_pa,
            "kp": sc.kp,
            "ki": sc.ki,
            # firmware derives samples/pixel; clamps to >=1 (see updateStepSizes)
            "derived_samples_per_pixel": max(spp, 1),
            "bias_dac": self.ui.spnBias.value(),
            "bias_V": stm_control.STM_Status.dac_to_bias_volts(
                self.ui.spnBias.value()),
            # Physical state at scan start — required to interpret the
            # frames later (audit 2026-07-15: tonight's Z mystery had to be
            # reconstructed from screenshots because this was missing).
            "dac_z_at_start": self.stm.status.dac_z,
            "adc_at_start": self.stm.status.adc,
            "steps_at_start": self.stm.status.steps,
            "cc_engaged": self.stm.status.is_const_current,
            "calibration": cal,
            "journal": session_journal.active_path(),
        }

    @Slot(bool)
    def _on_scan_running_changed(self, running: bool):
        """When continuous scan starts/stops, update the UI to reflect it,
        and start/stop the verbatim frame log alongside the stream."""
        if running:
            self._cs_btn_run.setEnabled(False)
            self._cs_btn_halt.setEnabled(True)
            path = self._frame_logger.start(self._scan_frame_settings())
            print(f"[FRAMES] logging scan frames to {path}")
        else:
            self._cs_btn_run.setEnabled(True)
            self._cs_btn_halt.setEnabled(True)
            path = self._frame_logger.stop()
            if path:
                print(f"[FRAMES] frame log closed: {path} "
                      f"({self._frame_logger.n_frames} frames, "
                      f"{self._frame_logger.n_dropped} dropped)")
            # Hand the port back: restart the recording's stream reader once
            # the scan reader has released it — EXCEPT when a legacy
            # synchronous op is about to read the port (_suppress_auto_record).
            def _resume_recording():
                if (self.stm.is_opened and self._recording
                        and not self._stab_streaming
                        and not self._scan_ctrl.is_running()
                        and not getattr(self, "_suppress_auto_record", False)):
                    print("[REC] resuming recording stream reader after scan")
                    self._start_stab_stream()
            QTimer.singleShot(500, _resume_recording)

    def _halt_continuous_if_running(self):
        """Stop a live continuous scan before a legacy serial-reading op.

        The legacy SCST/spectroscopy/noise paths read the serial port
        synchronously; if the SerialReaderThread is still running it would
        consume their responses and the synchronous readline() would hang.
        Guard every legacy entry point with this.
        """
        # Silence the push stream: the legacy op is about to read the port
        # synchronously and 200 Hz 'S' frames would corrupt its replies.
        # The recording service stays nominally on (journal/CSV open) but
        # gets no rows until the stream is re-armed; _suppress_auto_record
        # blocks the post-scan auto-resume until then.
        self._suppress_auto_record = True
        if self._stab_streaming:
            print("[auto-STOP] silencing recording stream before legacy op "
                  "(STRM 0)")
            self._stop_stab_stream()
        if getattr(self, "_scan_ctrl", None) and self._scan_ctrl.is_running():
            print("[auto-HALT] stopping continuous scan before legacy op")
            self._scan_ctrl.halt()
            self._cs_status_lbl.setText("Halted (legacy op)")
        # Silence push traffic UNCONDITIONALLY: during a continuous scan the
        # stream reader is handed off (_stab_streaming False) but firmware
        # STRM keeps pushing — those 'S' frames corrupted a legacy Scan's
        # ASCII reads (bench 2026-07-15, '47400A' parse error).
        self.stm.send_cmd("STRM 0", src="auto")
        if self._raw_logger.is_active():
            self.raw_stop(src="auto")
        # Drain leftover binary frames still in the OS buffer so the legacy
        # op's synchronous readline doesn't land mid-frame (bench 2026-07-14:
        # first Noise Scan after HALT returned garbage; took 4 attempts).
        try:
            time.sleep(0.1)
            self.stm.stm_serial.reset_input_buffer()
        except Exception:
            pass

    # =========================================================================
    # Calibration tab (UI is source of truth; calibration.json is persistence)
    # =========================================================================

    def _build_calibration_tab(self):
        tab = QWidget()
        root = QVBoxLayout(tab)
        root.setContentsMargins(8, 8, 8, 8)

        # Constants editor. These span ~1e-4 .. 1e8, so QLineEdit with a
        # float validator is used rather than QDoubleSpinBox (which cannot
        # sensibly display both magnitudes with one decimals setting).
        validator = QtGui.QDoubleValidator(-1e15, 1e15, 15, self)
        validator.setNotation(QtGui.QDoubleValidator.ScientificNotation)

        box = QGroupBox("Hardware calibration constants")
        form = QFormLayout(box)
        self._cal_edits = {}
        for name in calibration.FIELDS:
            # Plain decimal (not scientific) for consistency across fields —
            # preamp_a_per_v = 1e-8 was the odd one out (operator
            # 2026-07-15).  format_float_positional keeps full precision
            # with no exponent.
            edit = QLineEdit(np.format_float_positional(
                getattr(self._cal, name), trim="-"))
            edit.setValidator(validator)
            form.addRow(name, edit)
            self._cal_edits[name] = edit
        root.addWidget(box)

        # Live conversion examples so the operator can sanity-check.
        self._cal_examples = QLabel()
        self._cal_examples.setStyleSheet("font-family: monospace;")
        ex_box = QGroupBox("Examples (live)")
        ex_layout = QVBoxLayout(ex_box)
        ex_layout.addWidget(self._cal_examples)
        root.addWidget(ex_box)

        btn_row = QHBoxLayout()
        btn_apply = QPushButton("Apply")
        btn_apply.clicked.connect(self._on_cal_apply)
        btn_save = QPushButton("Save to JSON")
        btn_save.clicked.connect(self._on_cal_save)
        btn_reset = QPushButton("Reset defaults")
        btn_reset.clicked.connect(self._on_cal_reset)
        btn_row.addWidget(btn_apply)
        btn_row.addWidget(btn_save)
        btn_row.addWidget(btn_reset)
        btn_row.addStretch()
        root.addLayout(btn_row)
        root.addStretch()

        self.ui.tabWidget.addTab(tab, "Calibration")
        self._refresh_cal_examples()

    def _on_cal_apply(self):
        for name, edit in self._cal_edits.items():
            try:
                self._cal.set_field(name, float(edit.text()))
            except ValueError:
                pass  # invalid entry left as-is; keep prior value

    def _on_cal_save(self):
        self._on_cal_apply()
        self._cal.to_json()
        print("[Calibration] saved to calibration.json")

    def _on_cal_reset(self):
        self._cal.reset_defaults()
        for name, edit in self._cal_edits.items():
            edit.setText(repr(getattr(self._cal, name)))

    def _refresh_cal_examples(self):
        c = self._cal
        scan_lsb = self._scan_ctrl._nm_to_xy_lsb_span(30.0)
        sp_lsb   = self._scan_ctrl._pa_to_setpoint_lsb(1000.0)
        z_nm     = c.dac_lsb_to_nm_z(50000)
        self._cal_examples.setText(
            f"Scan 30 nm        → {scan_lsb} LSB span\n"
            f"Setpoint 1000 pA  → {sp_lsb} LSB (≈ 1 nA)\n"
            f"Z DAC code 50000  → {z_nm:.4f} nm")

    @Slot()
    def _on_calibration_changed(self):
        """Calibration constants changed — refresh editors and examples."""
        if hasattr(self, "_cal_edits"):
            for name, edit in self._cal_edits.items():
                if not edit.hasFocus():
                    edit.setText(repr(getattr(self._cal, name)))
        if hasattr(self, "_cal_examples"):
            self._refresh_cal_examples()


if __name__ == "__main__":
    # Console prints must never kill the app: serial garbage can contain
    # bytes cp1252 can't encode, and an unhandled UnicodeEncodeError inside
    # a Qt timer slot crashed the whole GUI (bench 2026-07-15).
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            try:
                _stream.reconfigure(errors="replace")
            except Exception:
                pass
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", default=None,
                        help="serial port to open at startup "
                             "(COM5, EMU, socket://host:9000, ...)")
    parser.add_argument("--copilot", type=int, default=0, metavar="HTTP_PORT",
                        help="start the copilot bridge on this localhost "
                             "port (0 = off)")
    args, qt_args = parser.parse_known_args()

    app = QApplication(sys.argv[:1] + qt_args)
    widget = Widget()
    widget.show()

    if args.port:
        idx = widget.ui.lePort.findText(args.port)
        if idx >= 0:
            widget.ui.lePort.setCurrentIndex(idx)
        else:
            widget.ui.lePort.setEditText(args.port)
        widget.on_cmdOpen_clicked()

    if args.copilot:
        import copilot_bridge
        widget._copilot_bridge = copilot_bridge.start(widget,
                                                      port=args.copilot)

    sys.exit(app.exec())

""" //for use with the toml
def main():
    import sys
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    widget = Widget()
    widget.show()
    sys.exit(app.exec())
"""
