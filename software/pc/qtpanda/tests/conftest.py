"""Shared fixtures and helpers for the qt-panda port test suite.

These tests exercise pure logic only — no hardware, no GUI windows.
They are the software-side bug-coverage net before bench validation.
"""
import os
import sys
import struct
import time

import pytest

# Make the package modules importable (tests/ is a subdir of qtpanda/).
_PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PKG not in sys.path:
    sys.path.insert(0, _PKG)


@pytest.fixture(scope="session")
def qapp():
    """A single QCoreApplication for QThread-based tests."""
    from PySide6.QtCore import QCoreApplication
    app = QCoreApplication.instance() or QCoreApplication([])
    yield app


class FakeSerial:
    """Minimal pyserial stand-in.

    Yields a fixed byte buffer, then returns b'' (like a read timeout)
    so a reader loop spins harmlessly until stop() is called.
    """

    def __init__(self, data: bytes = b""):
        self._buf = bytearray(data)
        self._pos = 0
        self.timeout = 1
        self.is_open = True

    def feed(self, data: bytes):
        self._buf.extend(data)

    def read(self, n: int = 1) -> bytes:
        if self._pos >= len(self._buf):
            return b""
        chunk = bytes(self._buf[self._pos:self._pos + n])
        self._pos += len(chunk)
        return chunk

    @property
    def in_waiting(self) -> int:
        return max(0, len(self._buf) - self._pos)

    def cancel_read(self):
        pass

    def close(self):
        self.is_open = False


# --- Frame builders: byte-exact to binary_frame.hpp ----------------------

def build_L_frame(line_no: int, z, err) -> bytes:
    """0x4C | u16 line | u16 pixels | i32 z[N] BE | i32 err[N] BE | 0x0A"""
    assert len(z) == len(err)
    n = len(z)
    out = bytearray()
    out.append(0x4C)
    out += struct.pack(">H", line_no)
    out += struct.pack(">H", n)
    out += b"".join(struct.pack(">i", int(v)) for v in z)
    out += b"".join(struct.pack(">i", int(v)) for v in err)
    out.append(0x0A)
    return bytes(out)


def build_M_frame(idx: int, bias: int, in_phase: int, quad: int) -> bytes:
    """0x4D | u16 idx | i32 bias | i32 in | i32 quad | 0x0A"""
    out = bytearray()
    out.append(0x4D)
    out += struct.pack(">H", idx)
    out += struct.pack(">i", bias)
    out += struct.pack(">i", in_phase)
    out += struct.pack(">i", quad)
    out.append(0x0A)
    return bytes(out)


def run_reader(qapp, data: bytes, expect: int, timeout_s: float = 3.0):
    """Run SerialReaderThread over `data`, collecting emitted signals.

    Returns dict with keys 'line', 'lock', 'ascii' -> lists.
    Signals are taken with DirectConnection so collectors run in the
    worker thread (no event loop needed); lists are append-only.
    """
    from PySide6.QtCore import Qt
    from serial_reader import SerialReaderThread

    fake = FakeSerial(data)
    reader = SerialReaderThread(fake)
    got = {"line": [], "lock": [], "ascii": []}
    reader.lineFrame.connect(
        lambda ln, z, e: got["line"].append((ln, z, e)), Qt.DirectConnection)
    reader.lockInPoint.connect(
        lambda *a: got["lock"].append(a), Qt.DirectConnection)
    reader.asciiLine.connect(
        lambda s: got["ascii"].append(s), Qt.DirectConnection)

    reader.start()
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        total = len(got["line"]) + len(got["lock"]) + len(got["ascii"])
        if total >= expect:
            break
        time.sleep(0.01)
    # Give the parser a beat to finish any in-flight frame, then stop.
    time.sleep(0.05)
    reader.stop()
    reader.wait(2000)
    return got
