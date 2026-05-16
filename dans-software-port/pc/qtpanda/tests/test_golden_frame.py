"""Golden-frame contract test.

Proves the PC parser decodes a buffer laid out *exactly* as the firmware
emits it (binary_frame.hpp + writePixel byte packing). This is the only
software-side check that the firmware emitter and PC parser agree without
the bench.

Firmware reference (binary_frame.hpp / line_buffer.hpp):
  'L' frame: 0x4C, u16 line BE, u16 pixels BE,
             then the buffer body which writePixel() packs as
             int32 z[pixels] big-endian followed by int32 err[pixels]
             big-endian, then 0x0A.
"""
import struct
import numpy as np

from conftest import run_reader


def _firmware_writepixel_buffer(z_vals, err_vals) -> bytes:
    """Reproduce writePixel()'s exact big-endian layout:
       byte 0..3   z[0]   (MSB first)
       ...
       then err[] block, same packing.
    """
    body = bytearray()
    for v in z_vals:
        u = v & 0xFFFFFFFF
        body += bytes(((u >> 24) & 0xFF, (u >> 16) & 0xFF,
                       (u >> 8) & 0xFF, u & 0xFF))
    for v in err_vals:
        u = v & 0xFFFFFFFF
        body += bytes(((u >> 24) & 0xFF, (u >> 16) & 0xFF,
                       (u >> 8) & 0xFF, u & 0xFF))
    return bytes(body)


def _emit_binary_frame(line_no, z_vals, err_vals) -> bytes:
    """Reproduce emitBinaryFrame(): magic, BE header, body, 0x0A."""
    n = len(z_vals)
    out = bytearray([0x4C])
    out += struct.pack(">H", line_no)
    out += struct.pack(">H", n)
    out += _firmware_writepixel_buffer(z_vals, err_vals)
    out.append(0x0A)
    return bytes(out)


def test_golden_L_frame_contract(qapp):
    line_no = 1234
    z   = [0, 1, -1, 2147483647, -2147483648, 123456, -123456]
    err = [-7, 7, 0, 1000, -1000, 2147483647, -2147483648]

    frame = _emit_binary_frame(line_no, z, err)
    # Sanity: total length == 5 + 8*N + 1 (the firmware's stated size).
    assert len(frame) == 5 + 8 * len(z) + 1

    got = run_reader(qapp, frame, expect=1)
    assert len(got["line"]) == 1
    ln, zarr, earr = got["line"][0]
    assert ln == line_no
    np.testing.assert_array_equal(zarr, np.array(z, dtype=np.int32))
    np.testing.assert_array_equal(earr, np.array(err, dtype=np.int32))


def test_golden_frame_signed_extremes_survive(qapp):
    # The int32 sign boundary is the classic break point for a
    # big-endian / mask / cast round-trip.
    z = [-2147483648, 2147483647, -1, 0]
    err = [0, -1, 2147483647, -2147483648]
    got = run_reader(qapp, _emit_binary_frame(9, z, err), expect=1)
    _, zarr, earr = got["line"][0]
    assert zarr.dtype == np.int32 and earr.dtype == np.int32
    assert list(zarr) == z
    assert list(earr) == err
