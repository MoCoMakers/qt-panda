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
from PySide6.QtCore import Slot, QTimer
from PySide6.QtWidgets import (QApplication,QVBoxLayout,QWidget)
from ui_form import Ui_Widget
import os
import logging
from qt_log_handler import QtLogHandler
import tifffile
from PySide6.QtCore import  QThread

print("OpenGL widget import OK")

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
        port = self.ui.lePort.text()
        print(f"[CMD] OPEN  port={port}")
        self.stm.open(port)


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
