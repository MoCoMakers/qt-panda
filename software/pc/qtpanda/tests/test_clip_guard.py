"""clip_guard — sustained-clip protection at fixed Z (F1)."""
from clip_guard import ClipGuard, CLIP_ADC, DEFAULT_STEP


def stream(t0, n, adc, dt=5):
    """n status samples at 200 Hz starting at t0 ms."""
    return [(t0 + i * dt, adc) for i in range(n)]


def test_sustained_clip_retracts():
    g = ClipGuard()
    assert g.check(stream(0, 200, 32767), False, False) == -DEFAULT_STEP


def test_negative_clip_also_trips():
    g = ClipGuard()
    assert g.check(stream(0, 200, -32768), False, False) == -DEFAULT_STEP


def test_normal_tunnelling_is_quiet():
    g = ClipGuard()
    assert g.check(stream(0, 200, 160), False, False) == 0


def test_brief_clipping_is_quiet():
    # 30% clipped (Oct 22 just before the crash): watch, don't act.
    s = stream(0, 140, 200) + stream(700, 60, 32767)
    assert ClipGuard().check(s, False, False) == 0


def test_feedback_on_stands_down():
    # CC owns Z: the firmware loop handles clipping.
    assert ClipGuard().check(stream(0, 200, 32767), True, False) == 0


def test_approach_stands_down():
    assert ClipGuard().check(stream(0, 200, 32767), False, True) == 0


def test_waits_for_fresh_samples_after_each_step():
    g = ClipGuard()
    s = stream(0, 200, 32767)
    assert g.check(s, False, False) == -DEFAULT_STEP
    # Same data again: nothing new since the step -> no second step.
    assert g.check(s, False, False) == 0
    # A further second still clipped -> step again.
    s2 = s + stream(1000, 200, 32767)
    assert g.check(s2, False, False) == -DEFAULT_STEP
    assert g.trips == 2


def test_cleared_after_retract_is_quiet():
    g = ClipGuard()
    s = stream(0, 200, 32767)
    g.check(s, False, False)
    assert g.check(s + stream(1000, 200, 900), False, False) == 0


def test_never_extends():
    g = ClipGuard()
    for adc in (-32768, -100, 0, 100, CLIP_ADC - 1, CLIP_ADC, 32767):
        assert g.check(stream(0, 200, adc), False, False) <= 0
        g.reset()


def test_too_few_samples_is_quiet():
    assert ClipGuard().check(stream(0, 5, 32767), False, False) == 0
