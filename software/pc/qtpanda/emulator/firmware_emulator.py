"""Software emulator of the dans-software-port Teensy firmware.

Purpose
-------
Everything in `SMOKE_TEST.md` is gated on physical hardware. This module lets
the *software* continuous-scan path — `stm_control` → `SerialReaderThread` →
`ScanController` → `live_raster` — be exercised end-to-end with no instrument,
so the C/D/E test groups can be rehearsed (and regression-tested) off the bench.

Scope / fidelity
----------------
`EmulatedSerial` is a drop-in for `serial.Serial` (the subset the codebase
actually uses: ``write``, ``read``, ``readline``, ``in_waiting`` /
``inWaiting()``, ``cancel_read``, ``close``, ``is_open``, ``timeout``). It
models the *protocol and frame bytes* faithfully — byte-exact to
``binary_frame.hpp`` and the `main.ino` command dispatcher — and the *state
machine* (setpoint gate on `ENGA`, `is_scanning` flag, mid-scan parameter
changes). It does **not** model analog physics: the topography is a fixed
synthetic surface. It is a wiring/throughput/UI harness, not a control-loop
simulator, and is no substitute for the bench.

Usage
-----
GUI:           open the serial port with device name ``EMU`` (see
               ``stm_control.STM_Control.open``).
Headless demo: ``python emulator/firmware_emulator.py``  (drives a full
               C5→E2 cycle through the real ``SerialReaderThread`` and
               prints frame stats).

Note
----
This folder is a transient development harness. It is **excluded from the
public repo** (see ``emulator/README.md`` and the ``.gitignore`` entry).
``stm_control`` imports it lazily and only when the device name is ``EMU``,
so deleting this folder cannot affect the shippable code.
"""
from __future__ import annotations

import math
import struct
import threading
import time

# Faithful to teensy/arduinosrc/main/main.ino:checkSerial()
CMD_LENGTH = 4

# z_pos amplitude (20-bit-ish). Kept well inside int32 and inside the
# >>shift+32768 mapping ScanController applies to drive the Z gauge.
_Z_BASE = 0
_Z_AMPL = 180_000


def _build_L_frame(line_no: int, z, err) -> bytes:
    """0x4C | u16 line | u16 pixels | i32 z[N] BE | i32 err[N] BE | 0x0A.

    Identical layout to binary_frame.hpp::emitBinaryFrame and to the
    tests/conftest.py::build_L_frame the parser tests already lock down.
    """
    assert len(z) == len(err)
    n = len(z)
    out = bytearray()
    out.append(0x4C)
    out += struct.pack(">H", line_no & 0xFFFF)
    out += struct.pack(">H", n & 0xFFFF)
    out += b"".join(struct.pack(">i", int(v)) for v in z)
    out += b"".join(struct.pack(">i", int(v)) for v in err)
    out.append(0x0A)
    return bytes(out)


def _build_M_frame(idx: int, bias: int, in_phase: int, quad: int) -> bytes:
    """0x4D | u16 idx | i32 bias | i32 in | i32 quad | 0x0A."""
    out = bytearray()
    out.append(0x4D)
    out += struct.pack(">H", idx & 0xFFFF)
    out += struct.pack(">i", int(bias))
    out += struct.pack(">i", int(in_phase))
    out += struct.pack(">i", int(quad))
    out.append(0x0A)
    return bytes(out)


class EmulatedSerial:
    """pyserial-compatible emulator of the STM firmware."""

    def __init__(self, timeout: float = 1.0):
        self.timeout = timeout
        self.is_open = True

        # --- emulated firmware state -------------------------------------
        self._bias = 32768
        self._dac_x = 32768
        self._dac_y = 32768
        self._dac_z = 32768
        self._adc = 0
        self._steps = 0
        self._is_approaching = False
        self._is_const_current = False
        self._is_scanning = False
        self._t0 = time.monotonic()

        self._setpoint = None          # None until SETP — gates ENGA (C5)
        self._engaged = False
        self._kp = 0.0
        self._ki = 0.0
        self._scan_size = 50_000
        self._pixels_per_line = 256    # IPLN; even by convention
        self._line_rate_hz = 1.0       # LRAT / 100
        self._x_ofs = 0
        self._y_ofs = 0
        self._control_dt_us = 40       # SETD

        # --- I/O plumbing ------------------------------------------------
        self._out = bytearray()
        self._lock = threading.Lock()
        self._data_ready = threading.Condition(self._lock)
        self._cancelled = False

        self._scan_thread = None
        self._scan_stop = threading.Event()
        self._line_no = 0

    # ====================================================================
    # pyserial surface
    # ====================================================================
    def write(self, data: bytes) -> int:
        # The PC sends exactly one command per write() (stm_control.send_cmd);
        # mirror checkSerial(): first CMD_LENGTH bytes are the command, the
        # remainder is the parseInt/parseFloat argument tail.
        if not data or len(data) < CMD_LENGTH:
            return len(data or b"")
        text = data.decode("ascii", errors="replace")
        cmd, args = text[:CMD_LENGTH], text[CMD_LENGTH:].strip()
        self._dispatch(cmd, args)
        return len(data)

    def read(self, n: int = 1) -> bytes:
        """Block up to ``timeout`` for data; return what's available (or b'')."""
        deadline = time.monotonic() + (self.timeout or 0)
        with self._data_ready:
            while not self._out and not self._cancelled and self.is_open:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return b""
                self._data_ready.wait(remaining)
            if self._cancelled:
                self._cancelled = False
                return b""
            chunk = bytes(self._out[:n])
            del self._out[:n]
            return chunk

    def readline(self) -> bytes:
        """Read up to and including the next 0x0A, or until timeout."""
        deadline = time.monotonic() + (self.timeout or 0)
        line = bytearray()
        while True:
            with self._data_ready:
                idx = self._out.find(b"\n")
                if idx != -1:
                    line += self._out[: idx + 1]
                    del self._out[: idx + 1]
                    return bytes(line)
                if self._out:
                    line += self._out
                    self._out.clear()
                remaining = deadline - time.monotonic()
                if remaining <= 0 or not self.is_open:
                    return bytes(line)
                self._data_ready.wait(remaining)

    @property
    def in_waiting(self) -> int:
        with self._lock:
            return len(self._out)

    def inWaiting(self) -> int:          # legacy pyserial spelling (stm_control)
        return self.in_waiting

    def cancel_read(self):
        with self._data_ready:
            self._cancelled = True
            self._data_ready.notify_all()

    def reset_input_buffer(self):
        with self._lock:
            self._out.clear()

    def close(self):
        self._stop_scan()
        with self._data_ready:
            self.is_open = False
            self._data_ready.notify_all()

    # ====================================================================
    # internals
    # ====================================================================
    def _emit(self, data: bytes):
        with self._data_ready:
            self._out += data
            self._data_ready.notify_all()

    def _emit_ascii(self, line: str):
        self._emit((line + "\n").encode("ascii"))

    def _arg_ints(self, args: str):
        out = []
        for tok in args.split():
            try:
                out.append(int(float(tok)))
            except ValueError:
                pass
        return out

    def _dispatch(self, cmd: str, args: str):
        ints = self._arg_ints(args)

        def a(i, default=0):
            return ints[i] if i < len(ints) else default

        if cmd == "RSET":
            self.__init__(timeout=self.timeout)        # full reset
        elif cmd == "GSTS":
            self._emit_ascii(self._status_line())
        elif cmd == "BIAS":
            self._bias = a(0)
        elif cmd == "DACX":
            self._dac_x = a(0)
        elif cmd == "DACY":
            self._dac_y = a(0)
        elif cmd == "DACZ":
            self._dac_z = a(0)
        elif cmd == "ADCR":
            self._emit_ascii(str(self._adc))
        elif cmd == "MTMV":
            self._steps += a(0)
        elif cmd in ("MTOF", "MTDR"):
            pass
        elif cmd == "APRH":
            self._adc = a(0)
            self._emit_ascii("Approached!")
            self._emit_ascii(str(self._adc))
        elif cmd == "CCON":
            self._is_const_current = True
            self._setpoint = a(0)
        elif cmd == "CCOF":
            self._is_const_current = False
        elif cmd in ("PIDS", "SETL"):
            pass
        elif cmd == "STOP":
            self._stop_scan()
            self._is_const_current = False

        # ---- new continuous-scan command set -----------------------------
        elif cmd == "SETP":
            self._setpoint = a(0)
        elif cmd == "KPGA":
            self._kp = float(args) if args else 0.0
        elif cmd == "KIGA":
            self._ki = float(args) if args else 0.0
        elif cmd == "SCSZ":
            self._scan_size = a(0)
        elif cmd == "IPLN":
            self._pixels_per_line = max(2, a(0, 256))
        elif cmd == "LRAT":
            self._line_rate_hz = max(0.01, a(0, 100) / 100.0)
        elif cmd == "XOFS":
            self._x_ofs = a(0)
        elif cmd == "YOFS":
            self._y_ofs = a(0)
        elif cmd == "SETD":
            self._control_dt_us = min(1000, max(10, a(0, 40)))
        elif cmd == "ENGA":
            if self._setpoint is None:
                self._emit_ascii("ENGA refused: no setpoint (use SETP first)")
            else:
                self._engaged = True
                self._is_const_current = True
                self._emit_ascii("ENGA OK")
        elif cmd == "RTRC":
            self._engaged = False
            self._is_const_current = False
            self._stop_scan()
        elif cmd == "RUN ":
            self._start_scan()
        elif cmd == "HALT":
            self._stop_scan()
        elif cmd == "LIDV":
            self._lock_in_didv(*(ints + [0, 0, 0, 0])[:4])
        # Unknown / unmodelled commands are silently ignored, exactly like
        # serialCommand()'s final no-op branch.

    def _status_line(self) -> str:
        t_ms = int((time.monotonic() - self._t0) * 1000)
        vals = [self._bias, self._dac_z, self._dac_x, self._dac_y,
                self._adc, self._steps,
                int(self._is_approaching), int(self._is_const_current),
                int(self._is_scanning), t_ms]
        return ",".join(str(v) for v in vals)

    # ---- continuous scan -------------------------------------------------
    def _start_scan(self):
        if self._is_scanning:
            return
        self._is_scanning = True
        self._scan_stop.clear()
        self._scan_thread = threading.Thread(
            target=self._scan_loop, name="EmuScan", daemon=True)
        self._scan_thread.start()

    def _stop_scan(self):
        self._is_scanning = False
        self._scan_stop.set()
        t = self._scan_thread
        if t and t.is_alive() and t is not threading.current_thread():
            t.join(timeout=2.0)
        self._scan_thread = None

    def _scan_loop(self):
        while not self._scan_stop.is_set() and self.is_open:
            n = self._pixels_per_line          # re-read each line: D2/D6 live
            period = max(1.0 / self._line_rate_hz, 0.005)
            z, err = self._synthetic_line(self._line_no, n)
            self._emit(_build_L_frame(self._line_no, z, err))
            self._line_no = (self._line_no + 1) & 0xFFFF
            self._scan_stop.wait(period)

    def _synthetic_line(self, line_no: int, n: int):
        """A fixed bumpy surface. First half = trace, second = retrace
        (reversed) so the live raster's Direction toggle shows the same
        features. err = small bounded residual."""
        half = max(1, n // 2)
        y = line_no
        trace = []
        for i in range(half):
            zx = math.sin(2 * math.pi * i / 37.0) * math.cos(2 * math.pi * y / 53.0)
            zx += 0.35 * math.sin(2 * math.pi * i / 7.0)
            trace.append(int(_Z_BASE + _Z_AMPL * zx))
        retrace = list(reversed(trace))
        z = trace + retrace
        if len(z) < n:                      # odd n: pad (asymmetric, like fw)
            z += [z[-1]] * (n - len(z))
        err = [((v >> 9) % 2001) - 1000 for v in z]   # deterministic ±1000
        return z, err

    # ---- lock-in dI/dV ---------------------------------------------------
    def _lock_in_didv(self, bias_center, bias_amp, freq_hz, n_periods):
        n_periods = max(0, int(n_periods))
        for k in range(n_periods):
            phase = 2 * math.pi * k / max(1, n_periods)
            bias = int(bias_center + bias_amp * math.sin(phase))
            in_phase = int(bias_amp * math.cos(phase) * 0.5)
            quad = int(bias_amp * math.sin(phase) * 0.1)
            self._emit(_build_M_frame(k, bias, in_phase, quad))


# ========================================================================
# Headless self-demo: a real SerialReaderThread driven by the emulator,
# walking SMOKE_TEST.md C2→C8 + E1 without hardware or a GUI.
# ========================================================================
def _demo():
    import os
    import sys

    # This module lives in the isolated dans-software-port/emulator/ folder;
    # the package under test is over in ../pc/qtpanda/.
    _here = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, os.path.normpath(os.path.join(_here, "..", "pc", "qtpanda")))
    from PySide6.QtCore import QCoreApplication, Qt
    from serial_reader import SerialReaderThread

    QCoreApplication.instance() or QCoreApplication([])
    emu = EmulatedSerial(timeout=0.2)
    reader = SerialReaderThread(emu)

    stats = {"lines": 0, "px": None, "lock": 0, "ascii": []}
    reader.lineFrame.connect(
        lambda ln, z, e: stats.update(lines=stats["lines"] + 1,
                                      px=len(z)), Qt.DirectConnection)
    reader.lockInPoint.connect(
        lambda *a: stats.update(lock=stats["lock"] + 1), Qt.DirectConnection)
    reader.asciiLine.connect(
        lambda s: stats["ascii"].append(s), Qt.DirectConnection)
    reader.start()

    def send(c):
        emu.write(c.encode())

    print("C5  ENGA before SETP ->", end=" ")
    send("ENGA"); time.sleep(0.1)
    print(stats["ascii"][-1] if stats["ascii"] else "(no reply)")

    send("SETP 1000")
    send("KPGA 0"); send("KIGA 4.5776")
    send("SCSZ 50000"); send("IPLN 256"); send("LRAT 1000")
    send("ENGA"); time.sleep(0.1)
    print("C4  ENGA with setpoint ->", stats["ascii"][-1])

    print("C6  RUN  (1 s of frames @ 10 Hz)...")
    send("RUN ")
    time.sleep(1.0)
    send("IPLN 512"); time.sleep(0.5)   # D2: mid-scan resolution change
    send("HALT"); time.sleep(0.2)
    print(f"C7  is_scanning during run: frames={stats['lines']} "
          f"last_px={stats['px']} (expect 512 after D2)")

    send("LIDV 0 1000 1000 5"); time.sleep(0.2)
    print(f"E1  LIDV -> {stats['lock']} 'M' frames (expect 5)")

    send("LIDV 0 0 0 0"); time.sleep(0.1)
    print("E2  LIDV zero-args: no crash")

    reader.stop(); reader.wait(2000); emu.close()
    print(f"\nTOTAL  L frames={stats['lines']}  M frames={stats['lock']}  "
          f"ascii={stats['ascii']}")


if __name__ == "__main__":
    _demo()
