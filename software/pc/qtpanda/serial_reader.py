import struct
import numpy as np
from PySide6.QtCore import QThread, Signal


# Raw ISR-tap sample layout inside an 'R' frame: interleaved, big-endian.
RAW_DTYPE = np.dtype([('adc', '>i2'), ('z', '>i4'), ('err', '>i4')])


def decode_raw_header(hdr: bytes):
    """Decode the 12 header bytes after an 'R' magic:
    (seq, count, t0_millis, dropped_samples).  Pure — unit-testable."""
    return struct.unpack('>HHII', hdr)


def decode_status_frame(payload: bytes):
    """Decode the 15 payload bytes of an 'S' status frame (magic and 0x0A
    terminator already stripped).  Returns
    (time_millis, adc, dac_z, bias, steps, flags).  Pure — unit-testable."""
    time_millis, adc, dac_z, bias, steps, flags = struct.unpack(
        '>IhHHiB', payload)
    return time_millis, adc, dac_z, bias, steps, flags


class SerialReaderThread(QThread):
    """
    Reads the hybrid binary/ASCII byte stream from the STM firmware.

    Supported frame types:
      0x4C ('L') — continuous-scan line frame (binary)
      0x4D ('M') — lock-in dI/dV point (binary)
      0x53 ('S') — push-mode status frame (binary, STRM command)
      other      — ASCII line, emitted as-is via asciiLine
    """

    lineFrame   = Signal(int, object, object)  # (line_number, z_arr, err_arr)
    lockInPoint = Signal(int, int, int, int)   # (point_idx, bias_lsb, in_phase, quad)
    statusFrame = Signal(int, int, int, int, int, int)
    # (time_millis, adc, dac_z, bias, steps, flags)
    rawBlock    = Signal(int, int, int, object)
    # (seq, t0_millis, dropped_samples, structured array of RAW_DTYPE)
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
                # Desync guard: firmware caps pixels/line at 512; a larger
                # value means we're parsing mid-stream garbage (two readers
                # raced the port on 2026-07-14 and runaway allocations from
                # bogus headers froze the GUI at 19 GB).  Skip the byte and
                # let the parser re-find a real frame boundary.
                if pixels_per_line == 0 or pixels_per_line > 2048:
                    continue
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
            # Binary 'R' frame — raw ISR-tap block (RAWD)
            # ----------------------------------------------------------------
            elif magic == 0x52:
                hdr = self._read_exact(12)
                if len(hdr) < 12:
                    break
                seq, count, t0, dropped = decode_raw_header(hdr)
                # Desync guard: firmware raw blocks are exactly 512 samples.
                if count == 0 or count > 512:
                    continue
                payload = self._read_exact(10 * count)
                if len(payload) < 10 * count:
                    break
                self._read_exact(1)  # 0x0A terminator
                samples = np.frombuffer(payload, dtype=RAW_DTYPE)
                self.rawBlock.emit(seq, t0, dropped, samples)

            # ----------------------------------------------------------------
            # Binary 'S' frame — push-mode status (STRM)
            # ----------------------------------------------------------------
            elif magic == 0x53:
                payload = self._read_exact(15)  # tm(4)+adc(2)+z(2)+bias(2)+steps(4)+flags(1)
                if len(payload) < 15:
                    break
                self._read_exact(1)  # 0x0A terminator
                self.statusFrame.emit(*decode_status_frame(payload))

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
