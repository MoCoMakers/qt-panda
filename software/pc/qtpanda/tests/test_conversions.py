"""Unit-conversion correctness: calibration model + ScanController.

The physical<->LSB math is easy to get wrong (we already found two bad
defaults by hand). These lock the round-trips and the firmware-facing
formulas.
"""
import json

import pytest

import calibration
import stm_control
from scan_controller import ScanController


# --- calibration.py ------------------------------------------------------

def test_calibration_defaults_loaded():
    c = calibration.Calibration()
    assert len(calibration.FIELDS) == 10
    for name in calibration.FIELDS:
        assert getattr(c, name) == calibration._DEFAULTS[name]


def test_z_nm_roundtrip():
    c = calibration.Calibration()
    for lsb in (0, 12345, 32768, 50000, 65535):
        nm = c.dac_lsb_to_nm_z(lsb)
        back = c.nm_to_dac_lsb_z(nm)
        assert abs(back - lsb) <= 1, (lsb, nm, back)


def test_adc_to_pa_sign_and_scale():
    c = calibration.Calibration()
    # Midpoint (32768) is zero current; symmetric about it.
    assert c.adc_lsb_to_pa(32768) == pytest.approx(0.0, abs=1e-6)
    hi = c.adc_lsb_to_pa(40000)
    lo = c.adc_lsb_to_pa(32768 - (40000 - 32768))
    assert hi == pytest.approx(-lo, rel=1e-9)


def test_set_field_emits_changed():
    c = calibration.Calibration()
    hits = []
    c.changed.connect(lambda: hits.append(1))
    c.set_field("piezo_z_nm_per_v", 4.2)
    assert c.piezo_z_nm_per_v == 4.2
    assert hits == [1]
    # No-op when value unchanged → no emit.
    c.set_field("piezo_z_nm_per_v", 4.2)
    assert hits == [1]
    # Unknown field → ignored, no emit, no crash.
    c.set_field("does_not_exist", 9)
    assert hits == [1]


def test_json_roundtrip(tmp_path):
    c = calibration.Calibration()
    c.set_field("piezo_x_nm_per_v", 7.5)
    c.set_field("adc_v_per_lsb", 1.23e-4)
    p = tmp_path / "cal.json"
    c.to_json(str(p))
    d = json.loads(p.read_text())
    assert set(d.keys()) == set(calibration.FIELDS)
    c2 = calibration.Calibration.from_json(str(p))
    assert c2.piezo_x_nm_per_v == 7.5
    assert c2.adc_v_per_lsb == pytest.approx(1.23e-4)


def test_reset_defaults():
    c = calibration.Calibration()
    c.set_field("piezo_z_nm_per_v", 99.0)
    c.reset_defaults()
    assert c.piezo_z_nm_per_v == calibration._DEFAULTS["piezo_z_nm_per_v"]


# --- scan_controller.py firmware-facing formulas -------------------------

@pytest.fixture
def sc():
    return ScanController(stm_control.STM(), calibration.Calibration())


def test_xy_span_is_a_delta_no_midpoint_offset(sc):
    # 0 nm span must map to 0 LSB (it's a delta, not an absolute code).
    assert sc._nm_to_xy_lsb_span(0.0) == 0
    # Sign preserved.
    assert sc._nm_to_xy_lsb_span(-10.0) == -sc._nm_to_xy_lsb_span(10.0)


def test_xy_span_matches_calibration(sc):
    c = sc._cal
    nm = 30.0
    # Firmware scan positions are 20-bit sigma-delta units = DAC LSB x 16.
    # (16-bit units here swept 1/16 of the commanded size — root cause of
    # "continuous never finds the morphology", fixed 2026-07-15.)
    expected = round(nm / c.piezo_x_nm_per_v / c.dac_x_v_per_lsb * 16)
    assert sc._nm_to_xy_lsb_span(nm) == expected
    # Sanity: 30 nm at defaults stays within the 20-bit position span.
    assert 0 < sc._nm_to_xy_lsb_span(30.0) < 16 * 65535


def test_setpoint_pa_matches_calibration(sc):
    c = sc._cal
    pa = 1000.0  # 1 nA
    expected = abs(round(pa * 1e-12 * c.preamp_v_per_a / c.adc_v_per_lsb))
    assert sc._pa_to_setpoint_lsb(pa) == expected
    # 1 nA should land near Dan's ~328 default, not 0.
    assert 250 < sc._pa_to_setpoint_lsb(1000.0) < 400


def test_setpoint_subnA_rounds_low_but_nonnegative(sc):
    # Documented degeneracy: sub-nA rounds toward 0 at a 100 MOhm preamp.
    assert sc._pa_to_setpoint_lsb(1.0) >= 0


def test_zUpdated_maps_zpos_to_dac_code(sc, qapp):
    import numpy as np
    seen = []
    sc.zUpdated.connect(lambda v: seen.append(v))
    # z_pos = 0 -> mid code 32768; >>4 then +32768.
    sc._on_line_frame(0, np.array([0], dtype=np.int32),
                      np.array([0], dtype=np.int32))
    assert seen[-1] == 32768
    sc._on_line_frame(1, np.array([16 * 1000], dtype=np.int32),
                      np.array([0], dtype=np.int32))
    assert seen[-1] == 32768 + 1000
    # Saturates into [0, 65535].
    sc._on_line_frame(2, np.array([10 ** 9], dtype=np.int32),
                      np.array([0], dtype=np.int32))
    assert 0 <= seen[-1] <= 65535


def test_line_rate_command_units(sc, monkeypatch):
    sent = []
    monkeypatch.setattr(sc, "_send", lambda c: sent.append(c))
    sc.set_line_rate(1.0)
    assert sent == ["LRAT 100"]   # firmware takes 0.01-Hz integer units
    sent.clear()
    sc.set_line_rate(2.5)
    assert sent == ["LRAT 250"]
