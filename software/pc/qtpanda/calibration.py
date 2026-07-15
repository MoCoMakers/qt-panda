"""
Physical-unit calibration model for the qt-panda STM.

All conversions are linear and symmetric (no offset).  The default
constants are derived from datasheet values and can be overridden by
editing calibration.json in the same directory.

Hardware summary
----------------
  DAC X/Y bias : AD5761, ±5 V full-scale (config 0b0000000000000101)
  DAC Z        : AD5761, ±10 V full-scale (config 0b0000000000000000)
  ADC          : LTC2326-16, ±10.24 V input range
  Preamp       : transimpedance, 100 MΩ feedback

Physical-unit conventions
--------------------------
  z_nm   : sample-tip gap in nanometres (positive = tip farther from sample)
  x_nm   : fast-scan axis position in nm
  y_nm   : slow-scan axis position in nm
  bias_v : sample bias in volts (positive bias = sample positive)
  current_pa : tunnel current in pA
"""

import json
import os

from PySide6.QtCore import QObject, Signal

_HERE = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_PATH = os.path.join(_HERE, "calibration.json")

# Canonical field order — drives the Calibration tab UI and JSON round-trip.
FIELDS = (
    "dac_x_v_per_lsb",
    "dac_y_v_per_lsb",
    "dac_z_v_per_lsb",
    "dac_bias_v_per_lsb",
    "piezo_x_nm_per_v",
    "piezo_y_nm_per_v",
    "piezo_z_nm_per_v",
    "adc_v_per_lsb",
    "preamp_a_per_v",
    "preamp_v_per_a",
)

_DEFAULTS = {
    "dac_x_v_per_lsb":       10.0 / 65536,    # ±5 V / 2^16
    "dac_y_v_per_lsb":       10.0 / 65536,
    "dac_z_v_per_lsb":       20.0 / 65536,    # ±10 V / 2^16
    "dac_bias_v_per_lsb":    10.0 / 65536,
    "piezo_x_nm_per_v":       5.0,             # typical at room temp; calibrate per tip
    "piezo_y_nm_per_v":       5.0,
    "piezo_z_nm_per_v":       3.0,
    "adc_v_per_lsb":         20.48 / 65536,   # ±10.24 V / 2^16
    "preamp_a_per_v":         1.0 / 100e6,    # 1/R_fb = 1 / 100 MΩ
    "preamp_v_per_a":       100e6             # R_fb = 100 MΩ
}


class Calibration(QObject):
    """
    Container for LSB ↔ physical-unit conversion factors.

    The UI is the source of truth; calibration.json is persistence only.
    Any field mutation emits `changed` so dependent widgets refresh.

    Usage
    -----
    >>> cal = Calibration.from_json()          # loads calibration.json
    >>> nm  = cal.dac_lsb_to_nm_z(32768)      # midpoint → 0 V → 0 nm
    >>> lsb = cal.nm_to_dac_lsb_z(1.5)
    >>> cal.set_field("piezo_z_nm_per_v", 4.2) # emits changed
    >>> cal.to_json()                          # persists for next session
    """

    changed = Signal()

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent)
        cfg = {**_DEFAULTS, **kwargs}
        for name in FIELDS:
            setattr(self, name, cfg[name])

    # -------------------------------------------------------------------------
    # Mutation
    # -------------------------------------------------------------------------

    def set_field(self, name: str, value: float):
        """Update one constant and notify listeners. No-op if name unknown."""
        if name not in FIELDS:
            return
        if getattr(self, name) == value:
            return
        setattr(self, name, value)
        self.changed.emit()

    def reset_defaults(self):
        """Restore in-memory defaults (does NOT write JSON)."""
        for name in FIELDS:
            setattr(self, name, _DEFAULTS[name])
        self.changed.emit()

    def as_dict(self) -> dict:
        return {name: getattr(self, name) for name in FIELDS}

    # -------------------------------------------------------------------------
    # Factory / persistence
    # -------------------------------------------------------------------------

    @classmethod
    def from_json(cls, path: str = _DEFAULT_PATH) -> "Calibration":
        if os.path.exists(path):
            with open(path, "r") as fh:
                data = json.load(fh)
            return cls(**data)
        return cls()

    def to_json(self, path: str = _DEFAULT_PATH):
        with open(path, "w") as fh:
            json.dump(self.as_dict(), fh, indent=2)

    # -------------------------------------------------------------------------
    # DAC → physical units  (16-bit unsigned code, midpoint = 32768 = 0 V)
    # -------------------------------------------------------------------------

    def dac_lsb_to_v_x(self, lsb: int) -> float:
        return (lsb - 32768) * self.dac_x_v_per_lsb

    def dac_lsb_to_v_y(self, lsb: int) -> float:
        return (lsb - 32768) * self.dac_y_v_per_lsb

    def dac_lsb_to_v_z(self, lsb: int) -> float:
        return (lsb - 32768) * self.dac_z_v_per_lsb

    def dac_lsb_to_v_bias(self, lsb: int) -> float:
        return (lsb - 32768) * self.dac_bias_v_per_lsb

    def dac_lsb_to_nm_x(self, lsb: int) -> float:
        return self.dac_lsb_to_v_x(lsb) * self.piezo_x_nm_per_v

    def dac_lsb_to_nm_y(self, lsb: int) -> float:
        return self.dac_lsb_to_v_y(lsb) * self.piezo_y_nm_per_v

    def dac_lsb_to_nm_z(self, lsb: int) -> float:
        return self.dac_lsb_to_v_z(lsb) * self.piezo_z_nm_per_v

    # -------------------------------------------------------------------------
    # Physical units → DAC LSB
    # -------------------------------------------------------------------------

    def nm_to_dac_lsb_x(self, nm: float) -> int:
        v = nm / self.piezo_x_nm_per_v
        return int(v / self.dac_x_v_per_lsb) + 32768

    def nm_to_dac_lsb_y(self, nm: float) -> int:
        v = nm / self.piezo_y_nm_per_v
        return int(v / self.dac_y_v_per_lsb) + 32768

    def nm_to_dac_lsb_z(self, nm: float) -> int:
        v = nm / self.piezo_z_nm_per_v
        return int(v / self.dac_z_v_per_lsb) + 32768

    def v_to_dac_lsb_bias(self, v: float) -> int:
        return int(v / self.dac_bias_v_per_lsb) + 32768

    # -------------------------------------------------------------------------
    # ADC → current
    # -------------------------------------------------------------------------

    def adc_lsb_to_v(self, lsb: int) -> float:
        return (lsb - 32768) * self.adc_v_per_lsb

    def adc_lsb_to_pa(self, lsb: int) -> float:
        v = self.adc_lsb_to_v(lsb)
        return v * self.preamp_a_per_v * 1e12  # amperes → pA

    # -------------------------------------------------------------------------
    # ISR integer position → nm  (20-bit signed, range ±524287)
    # -------------------------------------------------------------------------

    def isr_pos_to_nm_z(self, pos: int) -> float:
        """Convert the ISR's 20-bit z_pos to nanometres."""
        v = (pos / 524287.0) * 10.0   # ±10 V full-scale for Z DAC
        return v * self.piezo_z_nm_per_v
