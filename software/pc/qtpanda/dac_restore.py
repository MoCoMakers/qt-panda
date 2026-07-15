"""dac_restore — sanity rules for persisting/restoring DAC operating points.

Only X and Y are ever persisted/restored.  Z is the crash axis (restoring a
stale Z could drive the tip into a surface that has since drifted closer)
and bias is an operator decision per session — both are deliberately
excluded (operator directive 2026-07-15).
"""

DAC_MIN = 1          # 0 = rail / never-set: not a real operating point
DAC_MAX = 65534      # 65535 = rail


def restorable(value):
    """Return the value as an int if it is a sane persisted DAC operating
    point (1..65534), else None.  Tolerates the string form QSettings may
    return on some platforms."""
    try:
        v = int(value)
    except (TypeError, ValueError):
        return None
    if DAC_MIN <= v <= DAC_MAX:
        return v
    return None
