"""Live watchdogs (Phase 5 v1) — pure, no GUI."""
import watchdogs as wd


def test_saturation_trips_once_on_rail():
    w = wd.SaturationWatchdog(window=10, frac=0.5)
    alerts = [w.update(1e-7, wd.ADC_RAIL) for _ in range(20)]
    hits = [a for a in alerts if a]
    assert len(hits) == 1 and hits[0]["level"] == "critical"


def test_saturation_quiet_when_not_railed():
    w = wd.SaturationWatchdog(window=10, frac=0.5)
    assert all(w.update(3e-11, 20) is None for _ in range(30))


def test_emi_detects_bipolar_bursts():
    w = wd.EMIWatchdog(window=40, sigmas=5.0, min_exc=4)
    import random
    rng = random.Random(0)
    alert = None
    for i in range(80):
        cur = rng.gauss(0, 30e-12)
        if i % 8 == 0:
            cur += (6e-9 if (i // 8) % 2 == 0 else -6e-9)   # bipolar bursts
        a = w.update(cur, 100)
        alert = alert or a
    assert alert and alert["watchdog"] == "emi"


def test_signal_loss_after_engage():
    w = wd.SignalLossWatchdog(engage_A=100e-12, floor_A=45e-12, window=5)
    for _ in range(6):            # engage
        w.update(150e-12, 500)
    got = None
    for _ in range(6):            # drop to floor
        got = got or w.update(10e-12, 5)
    assert got and got["watchdog"] == "signal_loss"


def test_watchdog_set_aggregates():
    s = wd.WatchdogSet([wd.SaturationWatchdog(window=3, frac=0.9)])
    out = []
    for _ in range(5):
        out += s.update(1e-7, wd.ADC_RAIL)
    assert any(a["watchdog"] == "saturation" for a in out)
