"""scst_logger — verbatim log of legacy (SCST) scan data + faithful rebuild.

Closes the last unrecorded data path (found 2026-07-15): legacy Scan rows
were parsed, displayed, and DISCARDED — the most-trusted images in the
instrument were the only ones that never reached disk.

Design mirrors frame_logger: log-before-parse at the single choke point,
one verbatim ASCII line per record, flushed per line (a crash loses at most
one row), plus a JSON sidecar with everything needed to reconstruct the
display offline — scan geometry, samples/pixel, bias, Z, feedback state.

Module-level singleton (like session_journal) so the Qt-free serial layer
can call it with no dependency injection.
"""
import json
import os
import time

_f = None
_path = None
_rows = 0


def start(settings, log_dir="scans"):
    """Open a new .scst/.json pair; returns the log path."""
    global _f, _path, _rows
    stop()
    os.makedirs(log_dir, exist_ok=True)
    _path = os.path.join(log_dir, f"scst_{int(time.time() * 1000)}")
    with open(_path + ".json", "w") as sf:
        json.dump({"started": time.time(), "settings": settings}, sf,
                  indent=2)
    _f = open(_path + ".scst", "w", buffering=1)   # line-buffered
    _rows = 0
    return _path + ".scst"


def log_line(line):
    """Verbatim append of one complete ASCII line (no-op when inactive)."""
    global _rows
    if _f is not None:
        _f.write(line.rstrip("\r\n") + "\n")
        _rows += 1


def stop():
    """Finalize: close the log and stamp the sidecar with the row count."""
    global _f, _path, _rows
    if _f is None:
        return None
    _f.close()
    _f = None
    path = _path
    try:
        with open(path + ".json") as sf:
            meta = json.load(sf)
        meta["finished"] = time.time()
        meta["rows"] = _rows
        with open(path + ".json", "w") as sf:
            json.dump(meta, sf, indent=2)
    except OSError:
        pass
    _path = None
    return path + ".scst"


def is_active():
    return _f is not None


# --- offline rebuild ---------------------------------------------------------

def rebuild(scst_path):
    """Reconstruct the legacy-scan arrays from a verbatim log.

    Returns {"adc": dict row->values, "dacz": ..., "noise": ...,
    "curves": [raw curve rows], "settings": sidecar dict}.  Rows are keyed
    by row index because a truncated log (crash mid-scan) legitimately
    holds a partial image.
    """
    adc, dacz, noise, curves = {}, {}, {}, []
    with open(scst_path) as f:
        for line in f:
            parts = line.rstrip("\n").split(",")
            if parts and parts[0] in ("IVD", "IV", "DI"):
                curves.append(line.rstrip("\n"))
                continue
            if len(parts) < 3 or parts[0] not in ("A", "Z", "N"):
                continue
            try:
                row = int(parts[1])
                vals = [int(x) for x in parts[2:] if x != ""]
            except ValueError:
                continue   # garbled row: verbatim log keeps it, rebuild skips
            {"A": adc, "Z": dacz, "N": noise}[parts[0]][row] = vals
    side = {}
    try:
        with open(scst_path[:-5] + ".json") as sf:
            side = json.load(sf)
    except (OSError, ValueError):
        pass
    return {"adc": adc, "dacz": dacz, "noise": noise, "curves": curves,
            "settings": side}
