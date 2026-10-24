"""RTRC must leave Z at the fully retracted end (DAC 0), like the Z slider at "Away" (F2).

The old firmware wrote an absolute 50000, which moved the tip TOWARD the sample
whenever Z was below 50000. The emulator mirrors FW retract().
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "emulator"))
from firmware_emulator import EmulatedSerial  # noqa: E402


def _z(ser):
    return int(ser._status_line().split(",")[1])


def test_retract_goes_fully_away_from_any_z():
    for start in (0, 12000, 32768, 49999, 50000, 65535):
        ser = EmulatedSerial(timeout=0.1)
        ser.write(f"DACZ{start}".encode())
        ser.write(b"SETP160"); ser.write(b"ENGA")
        ser.write(b"RTRC")
        assert _z(ser) == 0, start
        assert ser._status_line().split(",")[7] == "0"        # constant current off
        ser.close()


def test_retract_never_moves_toward_sample():
    # Higher DAC = toward the sample, so RTRC may only lower Z.
    for start in range(0, 65536, 4096):
        ser = EmulatedSerial(timeout=0.1)
        ser.write(f"DACZ{start}".encode())
        ser.write(b"RTRC")
        assert _z(ser) <= start
        ser.close()
