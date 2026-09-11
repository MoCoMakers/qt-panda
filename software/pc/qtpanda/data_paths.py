"""data_paths — the single authority for where instrument data lives.

Every writer (raw_logger, frame_logger, scst_logger, session_journal,
status CSVs, scan images, IV curves, superscans, grid cubes, screenshots)
asks this module for its directory instead of inventing one.  Design
decision 2026-07-25: one per-day folder holds EVERYTHING captured that
day, flat, e.g.

    <DATA_ROOT>/2026-Jul-25/raw_1783836780472.raw
                            scan_1783834730467.frames
                            session_1783834729000.jsonl
                            image_adc_1784096611150.gsf
                            superscan_1784096600000.npz
                            ...

Filenames already carry a type prefix and an epoch-ms timestamp, so a flat
day folder stays self-describing and archiving a day is one drag (the
DataSyncArchive workflow).

Rules:
  * DATA_ROOT is ABSOLUTE — launching the GUI from a different working
    directory can no longer fork the data tree.  Override with the
    QTPANDA_DATA environment variable.
  * The day folder is resolved at each capture START (not app launch), so
    an overnight session files a 00:05 scan under the new day.
  * Qt-free, dependency-free (importable from the serial layer).
"""
import os
import time

_HERE = os.path.dirname(os.path.abspath(__file__))


def _default_root():
    # 1) a 'data' folder NEXT TO the scripts — the self-contained
    #    team-share bundle layout (make_bundle.py)
    local = os.path.join(_HERE, "data")
    if os.path.isdir(local):
        return local
    # 2) walk upward to the repo's TeamUpdate/data — works wherever the
    #    code tree lives (software/pc/qtpanda is canonical; TeamUpdate is
    #    DATA-ONLY per operator 2026-07-26)
    d = _HERE
    for _ in range(6):
        cand = os.path.join(d, "TeamUpdate", "data")
        if os.path.isdir(cand):
            return cand
        d = os.path.dirname(d)
    # 3) last resort: create the canonical location relative to the repo
    return os.path.abspath(
        os.path.join(_HERE, "..", "..", "..", "TeamUpdate", "data"))


DATA_ROOT = os.environ.get("QTPANDA_DATA", _default_root())

# %b gives locale month abbreviation; force the English form so folder
# names are stable across machines.
_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def day_name(t=None):
    """Folder name for the day containing epoch-seconds ``t`` (local time),
    e.g. '2026-Jul-25'.  Defaults to now."""
    lt = time.localtime(time.time() if t is None else t)
    return f"{lt.tm_year}-{_MONTHS[lt.tm_mon - 1]}-{lt.tm_mday:02d}"


def day_dir(t=None):
    """Absolute path of the day folder (created on demand)."""
    d = os.path.join(DATA_ROOT, day_name(t))
    os.makedirs(d, exist_ok=True)
    return d


def day_path(name, t=None):
    """Absolute path for ``name`` inside the day folder."""
    return os.path.join(day_dir(t), name)


def stamp():
    """Canonical epoch-milliseconds filename timestamp."""
    return int(time.time() * 1000)


def resolve_prefix(prefix, default_base="image"):
    """Turn a user-typed save prefix into an absolute day-folder prefix.

    The GUI's save box historically held relative prefixes like
    './images/image'; only the basename is kept and rehomed into today's
    folder.  An absolute prefix is respected verbatim (explicit operator
    choice wins).
    """
    prefix = (prefix or "").strip()
    if os.path.isabs(prefix):
        return prefix
    base = os.path.basename(prefix.replace("\\", "/")) or default_base
    return day_path(base)
