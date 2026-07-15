"""frame_logger — verbatim capture of continuous-scan line frames (roadmap L1).

The continuous-scan push stream (binary 'L' frames: line number + per-pixel
averaged Z and error, up to ~48.8 Hz at 512 px) previously painted the raster
and evaporated — the 2026-07-09 EMI test frames survive only as screenshots.
This module writes every frame verbatim to disk, before any GUI fan-out, so a
run can be replayed pixel-identically (see replay_frames.py) and analyzed raw.

Qt-free.  The GUI connects ``on_line`` to ScanController.lineReady *ahead of*
the LiveRaster connection (Qt invokes slots in connection order), so a frame
is on disk before it is drawn.

File pair per run:
  <base>.frames — binary, little-endian records:
        magic 'F' (1B) | pc_time f64 | line_number u16 | pixels u16
        | z int32[pixels] | err int32[pixels]
  <base>.json   — sidecar: settings snapshot at start, then finalized at stop
        with n_frames / drop stats / t_end (rewritten in place, so a crash
        mid-run leaves the start-time sidecar plus all frames flushed so far).

Drop detection: firmware line numbers increment and wrap at the line count;
any jump is counted (dropped = (line - last - 1) mod wrap) — truncation is
never silent (same principle as the broker's drop counters).
"""
import json
import os
import struct
import time

import numpy as np

import session_journal

_REC_HEAD = struct.Struct('<BdHH')   # magic, pc_time, line_number, pixels
_MAGIC = 0x46                        # 'F'


class FrameLogger:
    def __init__(self, log_dir="scans"):
        self.log_dir = log_dir
        self._f = None
        self.base_path = None
        self._sidecar = None
        self.n_frames = 0
        self.n_dropped = 0
        self._last_line = None
        self._wrap = None

    # -- lifecycle ---------------------------------------------------------
    def start(self, settings=None):
        """Open a new .frames/.json pair; ``settings`` is a plain dict snapshot
        of everything needed for faithful replay (geometry, feedback, bias,
        calibration...).  Closes any prior run first."""
        self.stop()
        os.makedirs(self.log_dir, exist_ok=True)
        base = os.path.join(self.log_dir, f"scan_{int(time.time() * 1000)}")
        self.base_path = base
        self._f = open(base + ".frames", "ab")
        self.n_frames = 0
        self.n_dropped = 0
        self._last_line = None
        self._wrap = None
        self._sidecar = {
            "t_start": time.time(),
            "settings": settings or {},
            "format": "F:<BdHH then z:int32[pixels] then err:int32[pixels], "
                      "little-endian",
        }
        self._write_sidecar()
        session_journal.record("scan_frames_start", path=base + ".frames")
        return base + ".frames"

    def stop(self):
        if self._f is None:
            return None
        path = self.base_path + ".frames"
        try:
            self._f.close()
        except OSError:
            pass
        self._f = None
        self._sidecar.update({
            "t_end": time.time(),
            "n_frames": self.n_frames,
            "n_dropped_lines": self.n_dropped,
        })
        self._write_sidecar()
        session_journal.record("scan_frames_stop", path=path)
        if self.n_dropped:
            session_journal.note(
                f"frame log {os.path.basename(path)}: "
                f"{self.n_dropped} dropped line(s) detected", src="auto")
        return path

    def is_active(self):
        return self._f is not None

    def status(self):
        return {
            "active": self.is_active(),
            "path": (self.base_path + ".frames") if self.base_path else None,
            "frames": self.n_frames,
            "dropped_lines": self.n_dropped,
        }

    def _write_sidecar(self):
        with open(self.base_path + ".json", "w") as f:
            json.dump(self._sidecar, f, indent=2)

    # -- per-frame sink (connect to lineReady, BEFORE the raster) ----------
    def on_line(self, line_number, z_arr, err_arr):
        if self._f is None:
            return
        z = np.asarray(z_arr, dtype='<i4')
        e = np.asarray(err_arr, dtype='<i4')
        n = int(min(len(z), len(e)))
        self._f.write(_REC_HEAD.pack(_MAGIC, time.time(),
                                     int(line_number) & 0xFFFF, n))
        self._f.write(z[:n].tobytes())
        self._f.write(e[:n].tobytes())
        self._f.flush()               # a crash loses at most one frame
        self.n_frames += 1

        # Drop accounting.  The firmware wraps its line counter at the line
        # count; infer the wrap from the largest line number seen + 1 once a
        # wrap occurs, and count any forward jump as dropped lines.
        if self._last_line is not None:
            if line_number > self._last_line:
                gap = line_number - self._last_line - 1
            elif self._wrap:
                gap = (line_number - self._last_line - 1) % self._wrap
            else:
                gap = 0               # first wrap with unknown modulus
            if gap:
                self.n_dropped += gap
        if self._wrap is None and self._last_line is not None \
                and line_number < self._last_line:
            self._wrap = self._last_line + 1
        self._last_line = line_number


# -- reading back -----------------------------------------------------------
def read_frames(path):
    """Yield (pc_time, line_number, z int32[], err int32[]) from a .frames
    file.  Stops cleanly at a truncated trailing record (crash mid-write)."""
    with open(path, "rb") as f:
        while True:
            head = f.read(_REC_HEAD.size)
            if len(head) < _REC_HEAD.size:
                return
            magic, t, line, n = _REC_HEAD.unpack(head)
            if magic != _MAGIC:
                raise ValueError(f"bad record magic {magic:#x} in {path}")
            payload = f.read(8 * n)
            if len(payload) < 8 * n:
                return
            z = np.frombuffer(payload[:4 * n], dtype='<i4')
            e = np.frombuffer(payload[4 * n:], dtype='<i4')
            yield t, line, z, e


def read_sidecar(frames_path):
    """The sidecar dict for a .frames path (or {} if absent)."""
    path = frames_path.replace(".frames", ".json")
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}
