"""session_journal — append-only per-session event log (roadmap J1).

One JSONL file, one JSON object per line, flushed per write so a crash loses at
most one line.  This is the forensically-complete record the 2026-07-02 bench
session lacked (which command, which settings, which sample, when).

Qt-free and dependency-free.  A module-level singleton lets the single command
choke point (``STM.send_cmd``) journal with one line and no dependency
injection:

    import session_journal
    session_journal.log_command("MTMV -5")      # src defaults to 'human'

The GUI drives the lifecycle:

    session_journal.start(settings=..., firmware=...)   # begin a session
    session_journal.log_sample({...}, tm=firmware_ms)   # each GSTS reply
    session_journal.note("near sample")                 # human annotation
    session_journal.stop()

Every record has: t (PC wall clock, epoch s), type, src (human|agent|auto),
data; and optionally tm (firmware time_millis) so PC-time and firmware-time
stay cross-mapped.  All loggers are **no-ops when no session is active**, so
hooks are safe to leave in place permanently.
"""
import json
import os
import threading
import time

import data_paths

_active = None
_lock = threading.Lock()
_last_tm = None          # most recent firmware time_millis seen (for alignment)


class SessionJournal:
    def __init__(self, path, sid):
        self.path = path
        self.sid = sid            # epoch-ms session id (the journal's stamp)
        self._f = open(path, "a", buffering=1)   # line-buffered

    def log(self, rec_type, data, src="auto", t=None, tm=None):
        rec = {
            "t": time.time() if t is None else t,
            "type": rec_type,
            "src": src,
            "data": data,
        }
        if tm is not None:
            rec["tm"] = tm
        line = json.dumps(rec, separators=(",", ":"))
        with _lock:
            self._f.write(line + "\n")

    def close(self):
        try:
            self._f.close()
        except OSError:
            pass


def start(log_dir=None, **session_meta):
    """Open a new session journal and return its path (closing any prior
    one).  ``log_dir`` defaults to today's data_paths day folder."""
    global _active
    stop()
    log_dir = log_dir or data_paths.day_dir()
    os.makedirs(log_dir, exist_ok=True)
    sid = int(time.time() * 1000)
    path = os.path.join(log_dir, f"session_{sid}.jsonl")
    _active = SessionJournal(path, sid)
    _active.log("session_start", session_meta, src="auto")
    return path


def stop():
    global _active
    if _active is not None:
        _active.log("session_end", {}, src="auto")
        _active.close()
        _active = None


def is_active():
    return _active is not None


def active_path():
    return _active.path if _active is not None else None


def session_id():
    """Epoch-ms id of the active session (the journal filename's stamp),
    or None.  This is THE correlation key across a crash-resume day."""
    return _active.sid if _active is not None else None


def tag():
    """Filename suffix ``_s<sessionId>`` binding an artifact to its GUI
    session, so every file of one run shares a visible token even after
    the GUI crashes and resumes several times a day.  Empty string when no
    session is active.  Always placed AFTER the capture timestamp, so the
    first 13-digit run in a filename remains the capture time."""
    return f"_s{_active.sid}" if _active is not None else ""


# --- convenience loggers (all no-op when no session is active) --------------
def mark_time(tm):
    """Record the most recent firmware time_millis (call on every status
    sample).  Subsequent commands are stamped with it, anchoring them to the
    instrument clock so journal and raw readings align without host-clock drift."""
    global _last_tm
    _last_tm = tm


def log_command(cmd, src="human"):
    if _active is not None:
        _active.log("command", {"cmd": cmd}, src=src, tm=_last_tm)


def log_sample(data, tm=None):
    if _active is not None:
        _active.log("sample", data, src="auto", tm=tm)


# All of these stamp tm (latest firmware time_millis) like log_command does,
# so every journal event — a note, a gain change, a capture start — is
# anchored to the instrument clock and can be located inside the raw stream.
def note(text, src="human", t=None):
    if _active is not None:
        _active.log("note", {"text": text}, src=src, t=t, tm=_last_tm)


def snapshot(event, settings, src="auto"):
    if _active is not None:
        _active.log("snapshot", {"event": event, "settings": settings},
                    src=src, tm=_last_tm)


def record(event, path=None, src="auto"):
    if _active is not None:
        _active.log("record", {"event": event, "path": path}, src=src,
                    tm=_last_tm)


def setting(name, old, new, src="human"):
    if _active is not None:
        _active.log("setting", {"name": name, "old": old, "new": new},
                    src=src, tm=_last_tm)
