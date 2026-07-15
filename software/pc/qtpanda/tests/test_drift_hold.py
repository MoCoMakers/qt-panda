"""drift_hold — slow anti-drift Z servo rules."""
from drift_hold import nudge, FLOOR_ADC


def test_open_junction_never_seeks():
    # Below floor: freeze, even though current is far below target.
    assert nudge(0, 320) == 0
    assert nudge(FLOOR_ADC - 1, 320) == 0
    assert nudge(-(FLOOR_ADC - 1), 320) == 0


def test_over_current_retracts():
    # 65 nA contact vs 1 nA target -> negative (retract), capped.
    assert nudge(20800, 320) == -15


def test_under_current_extends_gently():
    # In-band but below target -> small positive (extend), capped.
    assert nudge(100, 320) == 2          # err=-220 * 0.01 -> +2.2 -> +2
    assert nudge(FLOOR_ADC, 20000) == 15  # deep under target -> cap


def test_at_target_is_quiet():
    assert nudge(320, 320) == 0
    assert nudge(325, 320) == 0           # sub-LSB error rounds to zero


def test_sign_symmetric_for_negative_currents():
    # Negative-bias junctions read negative ADC; magnitude rules apply.
    assert nudge(-20800, 320) == -15
    assert nudge(-320, 320) == 0
