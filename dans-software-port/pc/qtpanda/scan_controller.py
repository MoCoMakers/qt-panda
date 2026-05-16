from typing import Optional
from PySide6.QtCore import QObject, Signal, Slot
import stm_control
from calibration import Calibration
from serial_reader import SerialReaderThread


class ScanController(QObject):
    """
    Owns a SerialReaderThread and translates UI interactions into
    4-char firmware commands, relaying parsed frames as Qt signals.

    UI-facing slots accept physical units (nm, pA, Hz); conversion to
    firmware LSB happens here via the shared Calibration instance.

    The reader thread is created lazily on start_run() so the controller
    can be instantiated before the serial port is opened.
    """

    lineReady    = Signal(int, object, object)  # (line_number, z_arr, err_arr)
    lockInPoint  = Signal(int, int, int, int)   # (idx, bias_lsb, in_phase, quad)
    asciiLine    = Signal(str)                  # passthrough for status/IV/etc.
    zUpdated     = Signal(int)                  # latest Z as 16-bit DAC code (0..65535)
    engaged      = Signal()
    retracted    = Signal()
    runningChanged = Signal(bool)               # True when scan stream is live

    # Sigma-delta shift: 20-bit z_pos → 16-bit DAC code (POSITION_BITS-DAC_BITS).
    _Z_POS_TO_DAC_SHIFT = 4

    def __init__(self, stm: stm_control.STM,
                 cal: Calibration, parent=None):
        super().__init__(parent)
        self._stm    = stm
        self._cal    = cal
        self._reader: Optional[SerialReaderThread] = None

        # Last commanded values, in physical units (source of truth for UI).
        self.scan_size_nm    = 160.0   # ~100000 LSB at default calibration
        self.pixels_per_line = 512
        self.line_rate_hz    = 1.0
        self.xo_nm           = 0.0
        self.yo_nm           = 0.0
        self.setpoint_pa     = 1.0
        self.kp              = 0.0
        self.ki              = 4.577   # Ki_isr = 300000 / 65536
        # Bias is owned by the left-panel control (spnBias); not duplicated here.

    # -------------------------------------------------------------------------
    # Unit conversions (physical → firmware LSB)
    # -------------------------------------------------------------------------

    def _nm_to_xy_lsb_span(self, nm: float) -> int:
        """Convert an XY *span/offset* in nm to LSB counter units.

        This is a delta (no 32768 midpoint offset): the firmware adds
        scanSize/xo directly into the scan-counter projection.
        """
        v = nm / self._cal.piezo_x_nm_per_v
        return int(round(v / self._cal.dac_x_v_per_lsb))

    def _pa_to_setpoint_lsb(self, pa: float) -> int:
        """Convert a tunnel-current setpoint in pA to ADC LSB magnitude."""
        amps = pa * 1e-12
        volts = amps * self._cal.preamp_v_per_a
        return abs(int(round(volts / self._cal.adc_v_per_lsb)))

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _send(self, cmd: str):
        self._stm.send_cmd(cmd)

    def _ensure_reader(self) -> bool:
        """Start the reader thread if needed.  Returns True on success."""
        if not self._stm.is_opened or not hasattr(self._stm, 'stm_serial'):
            print("[ScanController] cannot start reader: serial port not open")
            return False

        # If a previous thread is still alive, stop and join it before
        # creating a replacement.  Otherwise two threads would race on
        # the same serial port.
        if self._reader is not None:
            if self._reader.isRunning():
                self._reader.stop()
                self._reader.wait(2000)
            try:
                self._reader.lineFrame.disconnect()
                self._reader.lockInPoint.disconnect()
                self._reader.asciiLine.disconnect()
            except (RuntimeError, TypeError):
                pass
            self._reader = None

        self._reader = SerialReaderThread(self._stm.stm_serial)
        self._reader.lineFrame.connect(self._on_line_frame)
        self._reader.lockInPoint.connect(self.lockInPoint)
        self._reader.asciiLine.connect(self.asciiLine)
        self._reader.start()
        self.runningChanged.emit(True)
        return True

    def _stop_reader(self):
        if self._reader and self._reader.isRunning():
            self._reader.stop()
            self._reader.wait(2000)
            self.runningChanged.emit(False)

    def _on_line_frame(self, line_number, z_arr, err_arr):
        self.lineReady.emit(line_number, z_arr, err_arr)
        # Drive the Z-piezo gauge with the most recent sample, mapped from
        # the 20-bit z_pos space to the 16-bit DAC code the gauge displays.
        try:
            if z_arr is not None and len(z_arr):
                z_pos = int(z_arr[-1])
                dac_code = (z_pos >> self._Z_POS_TO_DAC_SHIFT) + 32768
                dac_code = max(0, min(65535, dac_code))
                self.zUpdated.emit(dac_code)
        except (TypeError, ValueError):
            pass

    # -------------------------------------------------------------------------
    # Scan control
    # -------------------------------------------------------------------------

    @Slot()
    def start_run(self):
        """Send RUN  and start the background reader thread."""
        if not self._ensure_reader():
            return
        self._send('RUN ')

    @Slot()
    def halt(self):
        """Send HALT and stop the background reader thread."""
        self._send('HALT')
        self._stop_reader()

    @Slot()
    def engage(self):
        self._send('ENGA')
        self.engaged.emit()

    @Slot()
    def retract(self):
        self._send('RTRC')
        self.retracted.emit()

    # -------------------------------------------------------------------------
    # Scan geometry (physical units in; LSB out)
    # -------------------------------------------------------------------------

    @Slot(float)
    def set_scan_size(self, nm: float):
        self.scan_size_nm = nm
        self._send(f'SCSZ {self._nm_to_xy_lsb_span(nm)}')

    @Slot(int)
    def set_pixels_per_line(self, n: int):
        self.pixels_per_line = n
        self._send(f'IPLN {n}')

    @Slot(float)
    def set_line_rate(self, hz: float):
        """Line rate in Hz; firmware LRAT takes 0.01-Hz integer units."""
        self.line_rate_hz = hz
        self._send(f'LRAT {int(round(hz * 100))}')

    @Slot(float, float)
    def set_offsets(self, xo_nm: float, yo_nm: float):
        self.xo_nm = xo_nm
        self.yo_nm = yo_nm
        self._send(f'XOFS {self._nm_to_xy_lsb_span(xo_nm)}')
        self._send(f'YOFS {self._nm_to_xy_lsb_span(yo_nm)}')

    # -------------------------------------------------------------------------
    # Feedback parameters
    # -------------------------------------------------------------------------

    @Slot(float)
    def set_setpoint(self, pa: float):
        self.setpoint_pa = pa
        self._send(f'SETP {self._pa_to_setpoint_lsb(pa)}')

    @Slot(float)
    def set_kp(self, v: float):
        self.kp = v
        self._send(f'KPGA {v}')

    @Slot(float)
    def set_ki(self, v: float):
        self.ki = v
        self._send(f'KIGA {v}')

    # -------------------------------------------------------------------------
    # Reader accessor (for bytes_pending display)
    # -------------------------------------------------------------------------

    @property
    def bytes_pending(self) -> int:
        if self._reader:
            return self._reader.bytes_pending
        return 0

    def is_running(self) -> bool:
        return self._reader is not None and self._reader.isRunning()
