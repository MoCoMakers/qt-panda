"""dac_restore — sanity rules for the persisted DACX/DACY operating point."""
from dac_restore import restorable, DAC_MIN, DAC_MAX


def test_accepts_operating_points():
    assert restorable(32768) == 32768
    assert restorable(DAC_MIN) == DAC_MIN
    assert restorable(DAC_MAX) == DAC_MAX


def test_coerces_qsettings_string_form():
    # QSettings can return strings on some platforms/backends.
    assert restorable("32768") == 32768


def test_rejects_rails_and_unset():
    assert restorable(0) is None          # rail / never-set
    assert restorable(65535) is None      # rail
    assert restorable(-5) is None
    assert restorable(70000) is None


def test_rejects_junk():
    assert restorable(None) is None
    assert restorable("") is None
    assert restorable("mid") is None
