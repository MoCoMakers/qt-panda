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
import time
import csv
import threading
import pyqtgraph as pg
import STMBoxWidget
import GridSpectroWorker
from PySide6.QtCore import Slot, QTimer, QSettings, Qt
from PySide6.QtWidgets import (QApplication,  QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSizePolicy,
    QSpacerItem, QSpinBox, QTabWidget, QVBoxLayout,
    QWidget, QDoubleSpinBox, QGroupBox, QFormLayout,
    QComboBox, QProgressBar, QGridLayout)
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

        # Swap the free-text port field for an enumerated combo + Refresh
        self._install_port_combo()
        self._refresh_ports()
        last_port = self._settings.value("serial/port", "", type=str)
        if last_port:
            idx = self.ui.lePort.findText(last_port)
            if idx >= 0:
                self.ui.lePort.setCurrentIndex(idx)


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

    @Slot()
    def on_cmdOpen_clicked(self):
        port = self.ui.lePort.currentText().strip()
        if not port:
            print("[CMD] OPEN  no port selected")
            return
        print(f"[CMD] OPEN  port={port}")
        self.stm.open(port)
        self._settings.setValue("serial/port", port)

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


    @Slot()
    def on_cmdReset_clicked(self):
        print("[CMD] RESET")
        self.stm.reset()


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

    @Slot()
    def on_cmdMotUp_clicked(self):
        amount = self.ui.spnMot.value()
        print(f"MTMV {amount}")
        self.stm.send_cmd(f"MTMV {amount}")

    @Slot()
    def on_cmdMotDown_clicked(self):
        amount = self.ui.spnMot.value()
        print(f"MTMV {amount}")
        self.stm.send_cmd(f"MTMV -{amount}")

    @Slot()
    def on_cmdMotOff_clicked(self):
        print(f"MTOF") # MOTOR OFF
        self.stm.send_cmd(f"MTOF")

    # ----------------------
    # SCAN
    # ----------------------

    @Slot()
    def on_cmdScan_clicked(self):
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
        self.ui.spnDACZ.setValue(value)
        print(value)


    # ----------------------
    # Real-Time Updates
    # ----------------------

    def update_real_time(self):
        #print("update_real_time running")
        if self.stm.busy:
            return

        # While continuous-scan reader owns the serial port, polling GSTS
        # would race with the binary-frame parser and hang the UI for a full
        # 1 s readline timeout.  Skip polling; status comes from frames /
        # asciiLine instead during continuous scan.
        if getattr(self, "_scan_ctrl", None) and self._scan_ctrl.is_running():
            return

        status = self.stm.get_status()

        if status is None:
            return

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
    # ----------------------
    # Image Updates
    # ----------------------

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
        self._cs_linerate.setValue(1.0)
        self._cs_linerate.setSuffix(" Hz")
        geo_form.addRow("Line rate:", self._cs_linerate)

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

        top_row.addWidget(fb_box)

        # ---- Z-piezo position gauge -----------------------------------------
        gauge_box = QGroupBox("Z-piezo")
        gauge_layout = QVBoxLayout(gauge_box)
        gauge_layout.setSpacing(2)
        gauge_layout.addWidget(QLabel("Extended"),
                                alignment=Qt.AlignHCenter)
        self._cs_zgauge = QProgressBar()
        self._cs_zgauge.setOrientation(Qt.Vertical)
        self._cs_zgauge.setRange(0, 65535)
        self._cs_zgauge.setValue(32768)
        self._cs_zgauge.setTextVisible(True)
        self._cs_zgauge.setFormat("%p%")
        gauge_layout.addWidget(self._cs_zgauge,
                               alignment=Qt.AlignHCenter)
        gauge_layout.addWidget(QLabel("Retracted"),
                               alignment=Qt.AlignHCenter)
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

        act_layout.addStretch()

        self._cs_status_lbl = QLabel("Idle")
        act_layout.addWidget(self._cs_status_lbl)

        top_row.addWidget(act_box)
        tab_layout.addLayout(top_row)

        # ---- Live raster images ---------------------------------------------
        self._cs_raster = live_raster.LiveRaster(
            self._cal,
            image_height=256,
            pixels_per_line=self._cs_pixels.value(),
            parent=tab
        )
        tab_layout.addWidget(self._cs_raster, stretch=1)

        # Wire ScanController → LiveRaster / gauge / status
        self._scan_ctrl.lineReady.connect(self._cs_raster.update_line)
        self._scan_ctrl.zUpdated.connect(self._cs_zgauge.setValue)
        self._scan_ctrl.engaged.connect(
            lambda: self._cs_status_lbl.setText("Engaged"))
        self._scan_ctrl.retracted.connect(
            lambda: self._cs_status_lbl.setText("Retracted"))
        self._scan_ctrl.asciiLine.connect(self._on_ascii_during_scan)
        self._scan_ctrl.runningChanged.connect(self._on_scan_running_changed)
        # Right-click-to-pan: raster → offset spinboxes → firmware
        self._cs_raster.scanOffsetRequested.connect(self._on_cs_offset_picked)

        self.ui.tabWidget.addTab(tab, "Continuous Scan")

    # ---- Continuous-scan slot handlers ---------------------------------------

    @Slot()
    def _on_cs_apply_settings(self):
        """Push all current UI values (physical units) to the firmware."""
        self._scan_ctrl.set_scan_size(self._cs_scansize.value())
        n = self._cs_pixels.value()
        self._scan_ctrl.set_pixels_per_line(n)
        self._scan_ctrl.set_line_rate(self._cs_linerate.value())
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
        self._cs_raster.resize_buffers(256, n)
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

    @Slot()
    def _on_cs_run(self):
        if not self.stm.is_opened:
            self._cs_status_lbl.setText("Serial not open")
            return
        self._on_cs_apply_settings()
        self._scan_ctrl.start_run()
        self._cs_status_lbl.setText("Running…")

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

    @Slot(bool)
    def _on_scan_running_changed(self, running: bool):
        """When continuous scan starts/stops, update the UI to reflect it."""
        if running:
            self._cs_btn_run.setEnabled(False)
            self._cs_btn_halt.setEnabled(True)
        else:
            self._cs_btn_run.setEnabled(True)
            self._cs_btn_halt.setEnabled(True)

    def _halt_continuous_if_running(self):
        """Stop a live continuous scan before a legacy serial-reading op.

        The legacy SCST/spectroscopy/noise paths read the serial port
        synchronously; if the SerialReaderThread is still running it would
        consume their responses and the synchronous readline() would hang.
        Guard every legacy entry point with this.
        """
        if getattr(self, "_scan_ctrl", None) and self._scan_ctrl.is_running():
            print("[auto-HALT] stopping continuous scan before legacy op")
            self._scan_ctrl.halt()
            self._cs_status_lbl.setText("Halted (legacy op)")

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
            edit = QLineEdit(repr(getattr(self._cal, name)))
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

    app = QApplication(sys.argv)
    widget = Widget()
    widget.show()
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
