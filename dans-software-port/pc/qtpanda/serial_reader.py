import struct
import numpy as np
from PySide6.QtCore import QThread, Signal


class SerialReaderThread(QThread):
    """
    Reads the hybrid binary/ASCII byte stream from the STM firmware.

    Supported frame types:
      0x4C ('L') — continuous-scan line frame (binary)
      0x4D ('M') — lock-in dI/dV point (binary)
      other      — ASCII line, emitted as-is via asciiLine
    """

    lineFrame   = Signal(int, object, object)  # (line_number, z_arr, err_arr)
    lockInPoint = Signal(int, int, int, int)   # (point_idx, bias_lsb, in_phase, quad)
    asciiLine   = Signal(str)

    def __init__(self, serial_port, parent=None):
        super().__init__(parent)
        self._serial = serial_port
        self._stop   = False

    def stop(self):
        self._stop = True
        try:
            self._serial.cancel_read()
        except Exception:
            pass

    @property
    def bytes_pending(self) -> int:
        try:
            return self._serial.in_waiting
        except Exception:
            return 0

    def _read_exact(self, n: int) -> bytes:
        buf = b''
        while len(buf) < n and not self._stop:
            try:
                chunk = self._serial.read(n - len(buf))
            except Exception:
                return buf
            if chunk:
                buf += chunk
        return buf

    def run(self):
        self._stop = False
        while not self._stop:
            try:
                byte = self._serial.read(1)
            except Exception:
                break
            if not byte:
                continue

            magic = byte[0]

            # ----------------------------------------------------------------
            # Binary 'L' frame — continuous scan line
            # ----------------------------------------------------------------
            if magic == 0x4C:
                hdr = self._read_exact(4)
                if len(hdr) < 4:
                    break
                line_number     = struct.unpack('>H', hdr[0:2])[0]
                pixels_per_line = struct.unpack('>H', hdr[2:4])[0]
                payload = self._read_exact(8 * pixels_per_line)
                if len(payload) < 8 * pixels_per_line:
                    break
                self._read_exact(1)  # 0x0A terminator
                split = 4 * pixels_per_line
                z_arr   = np.frombuffer(payload[:split],  dtype='>i4').astype(np.int32)
                err_arr = np.frombuffer(payload[split:],  dtype='>i4').astype(np.int32)
                self.lineFrame.emit(line_number, z_arr, err_arr)

            # ----------------------------------------------------------------
            # Binary 'M' frame — lock-in dI/dV point
            # ----------------------------------------------------------------
            elif magic == 0x4D:
                payload = self._read_exact(14)  # idx(2)+bias(4)+in(4)+quad(4)
                if len(payload) < 14:
                    break
                self._read_exact(1)  # terminator
                idx      = struct.unpack('>H', payload[0:2])[0]
                bias_lsb = struct.unpack('>i', payload[2:6])[0]
                in_phase = struct.unpack('>i', payload[6:10])[0]
                quad     = struct.unpack('>i', payload[10:14])[0]
                self.lockInPoint.emit(idx, bias_lsb, in_phase, quad)

            # ----------------------------------------------------------------
            # ASCII line — accumulate until \n, emit stripped
            # ----------------------------------------------------------------
            else:
                line_bytes = bytearray([magic])
                while not self._stop:
                    try:
                        b = self._serial.read(1)
                    except Exception:
                        break
                    if not b:
                        continue
                    if b[0] == 0x0A:
                        break
                    line_bytes += b
                try:
                    line = line_bytes.decode('ascii', errors='replace').rstrip('\r')
                    if line:
                        self.asciiLine.emit(line)
                except Exception:
                    pass
