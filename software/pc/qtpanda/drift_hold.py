"""drift_hold — slow software Z baseline servo for constant-height mode.

Anti-drift by timescale separation: a nudge every ~0.5 s with a small step
cap gives the correction loop a bandwidth of ~0.1 Hz — far below the line
rate, so scan features (line rate and above) pass through untouched while
thermal/creep drift (sub-0.01 Hz) is cancelled.  This is NOT feedback
imaging: within a line the height is constant; only the baseline moves.

Safety rule (bench 2026-07-15, bistable junction): the servo may HOLD a
junction, never SEEK one.  Below FLOOR_ADC the junction is open and the
correct anti-drift action is to freeze — extending to "find" current again
would be a slow automatic approach, which is exactly what this must never
become.
"""

FLOOR_ADC = 32          # ~0.1 nA @ 3.125 pA/LSB: below this = open junction
DEFAULT_GAIN = 0.01     # LSB of Z per ADC count of error
DEFAULT_MAX_STEP = 15   # max Z LSB per tick (~0.1 Hz bandwidth at 2 Hz tick)


def nudge(mean_adc, target_adc, gain=DEFAULT_GAIN, max_step=DEFAULT_MAX_STEP):
    """Return the signed Z-DAC correction (LSB) for one servo tick.

    Convention: higher Z DAC = extend toward sample = more current.
    More current than target -> retract (negative return value).
    Open junction (|mean| below floor) -> 0: never seek.
    """
    a = abs(mean_adc)
    if a < FLOOR_ADC:
        return 0
    err = a - abs(target_adc)
    step = err * gain
    if step > max_step:
        step = max_step
    elif step < -max_step:
        step = -max_step
    return -int(round(step))
