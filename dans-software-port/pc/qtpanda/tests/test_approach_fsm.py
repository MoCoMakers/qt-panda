"""Guarded-approach FSM (Phase 5 v2 logic) — pure, no hardware."""
import pytest

from approach_fsm import ApproachFSM


def _fsm():
    # floor: offset 0, sigma 40 pA; near at 2σ=80pA, engage at 3σ=120pA
    return ApproachFSM(floor_offset_A=0.0, floor_sigma_A=40e-12)


def test_coarse_then_single_then_engage_then_hold():
    f = _fsm()
    assert f.update(20e-12, 100) == "step_in"          # < 2σ: coarse ok
    assert f.update(90e-12, 400) == "step_in_single"   # >= 2σ: single steps
    assert f.state == ApproachFSM.NEAR
    assert f.update(150e-12, 700) == "engage"          # >= 3σ: in window
    assert f.state == ApproachFSM.ENGAGED
    assert f.update(150e-12, 700) == "hold"            # stays engaged


def test_hard_retract_on_rail_is_terminal():
    f = _fsm()
    assert f.update(30e-12, 100) == "step_in"
    assert f.update(1e-6, 32767) == "retract"          # railed -> retract
    assert f.state == ApproachFSM.RETRACTED
    assert f.update(30e-12, 100) == "retract"          # terminal, stays


def test_rejects_zero_sigma():
    with pytest.raises(ValueError):
        ApproachFSM(0.0, 0.0)
