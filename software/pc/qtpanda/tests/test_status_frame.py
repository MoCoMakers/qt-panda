"""'S' status-frame decode — layout must match firmware emitStatusFrame()."""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from serial_reader import decode_status_frame


def _encode(tm, adc, dac_z, bias, steps, flags):
    """Mirror of firmware emitStatusFrame() payload (bytes 1..15)."""
    return struct.pack('>IhHHiB', tm, adc, dac_z, bias, steps, flags)


def test_roundtrip_typical():
    payload = _encode(143487, -20752, 32768, 35014, -1115, 0x05)
    assert decode_status_frame(payload) == (143487, -20752, 32768, 35014,
                                            -1115, 0x05)


def test_extremes():
    payload = _encode(0xFFFFFFFF, -32768, 65535, 0, -2**31, 0xFF)
    tm, adc, dac_z, bias, steps, flags = decode_status_frame(payload)
    assert tm == 0xFFFFFFFF
    assert adc == -32768
    assert dac_z == 65535
    assert bias == 0
    assert steps == -2**31
    assert flags == 0xFF


def test_payload_is_15_bytes():
    assert len(_encode(0, 0, 0, 0, 0, 0)) == 15


def test_flags_bits():
    _, _, _, _, _, flags = decode_status_frame(_encode(1, 2, 3, 4, 5, 0b101))
    assert bool(flags & 0x01)          # approaching
    assert not bool(flags & 0x02)      # const current
    assert bool(flags & 0x04)          # scanning
