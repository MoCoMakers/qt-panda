"""reconstruct — the shared "Run" pipeline for live view, replay and analysis (pipeline v2).

Decisions: D31 (live view and replay share one pipeline), D34 (legacy line-number slip
correction with a change-log trail), D38 (build behind toggles; default = today's behaviour,
backbone cut-overs proved by equivalence tests).  Design: docs/test-plans/data-pipeline-v2-design.md,
build plan: docs/test-plans/pipeline-v2-build-plan.md.

One place for what used to be copied six times:
  * the raster Y fold: a line-counter cycle 0..2H-1 is one Y triangle; lines 0..H-1 go one way,
    H..2H-1 come back over the same rows (row = raw if raw < H else 2H-1-raw);
  * the trace / retrace split of a line (trace = first half, retrace = second half reversed);
  * sweep segmentation of a recording (the replay index);
  * the display transforms (peaks bright, error linearisation, row alignment).

Line index modes (`line_index`):
  "stamped"         the firmware's stamped number, exactly as before (reproduces old images)
  "slip_corrected"  undo the FW <= 5.6 slip: the Y-bottom resync fired on the tick that completed
                    the last line, so the first Y-cycle after RUN stamps 0..bins-2 then 0 (that 0
                    is line bins-1), and every later line is stamped one too high.  Rule: before
                    the slip, identity; the stamp 0 that follows a stamp >= bins/2 within the
                    first cycle is line bins-1; from then on true = (stamped - 1) mod bins.  The
                    slip phase is also recognised by any stamp == bins-1 (impossible before it).
  "tick"            v2 frames: the index comes from the microcontroller tick (exact).
Raw .frames are never modified; corrections are logged to <base>.corrections.json.

Naming (D9): the first half of each Y-cycle (raw < H) is the UP sweep, the second the DOWN sweep,
as in the replay viewer.
"""
import datetime as _dt
import json
import math
import os

import numpy as np

ALGO_VERSION = 1
LINE_INDEX_MODES = ("stamped", "slip_corrected", "tick")
LOG_K = (2 ** 19 - 1) / math.log(2 ** 15 + 1)      # firmware logTable scale (log-table units per ln)


# ----------------------------------------------------------------------------- fold primitives
def fold_row(raw, H):
    """Physical row of a line-counter value raw in 0..2H-1."""
    return raw if raw < H else (2 * H - 1 - raw)


def split_line(vals, half):
    """(trace, retrace-in-X-order) of one line's 2*half values."""
    return vals[:half], vals[half:2 * half][::-1]


def direction(raw, H):
    return "up" if raw < H else "down"


# ----------------------------------------------------------------------------- slip correction
def slip_correct(stamps, bins):
    """Map FW <= 5.6 stamped line numbers (one RUN, one geometry) to true line indices.
    Returns (true_lines, info).  info records where the slip phase began."""
    stamps = [int(s) for s in stamps]
    out = []
    shifted = False
    started_at = None
    prev = None
    for k, s in enumerate(stamps):
        if not shifted:
            if s == bins - 1:                         # only possible once the slip is active
                shifted, started_at = True, k
            elif s == 0 and prev is not None and prev >= bins // 2:
                out.append(bins - 1)                  # the end of the first Y-cycle
                shifted, started_at = True, k + 1
                prev = s
                continue
        out.append((s - 1) % bins if shifted else s)
        prev = s
    info = {"slip_phase_from_record": started_at, "n_records": len(stamps),
            "n_remapped": int(sum(o != t for o, t in zip(out, stamps)))}
    return out, info


# ----------------------------------------------------------------------------- display transforms
ROW_ALIGN_METHODS = ("Median of diffs", "Median", "Poly deg 5")


def row_align(arr, method):
    """Gwyddion-style per-row background removal (display/post only; raw data stays verbatim).
    Moved unchanged from live_raster._row_align (equivalence-tested)."""
    a = np.asarray(arr, dtype=np.float64).copy()
    if a.ndim != 2 or a.shape[0] < 2:
        return arr
    if method == "Median":
        a -= np.median(a, axis=1, keepdims=True)
    elif method == "Median of diffs":
        d = np.median(np.diff(a, axis=0), axis=1)
        res = a - np.median(a, axis=1, keepdims=True)
        sigma_pix = 1.4826 * np.median(np.abs(res))
        gate = 5.0 * 1.253 * sigma_pix * np.sqrt(2.0 / a.shape[1])
        d = np.where(np.abs(d) > gate, d, 0.0)
        off = np.concatenate(([0.0], np.cumsum(d)))
        a -= (off - off.mean())[:, None]
    elif method == "Poly deg 5":
        x = np.linspace(-1.0, 1.0, a.shape[1])
        V = np.vander(x, 6)
        coef, *_ = np.linalg.lstsq(V, a.T, rcond=None)
        a -= (V @ coef).T
    return a.astype(np.float32)


def setlog_of(setpoint_lsb):
    return int(round(math.log(abs(setpoint_lsb) + 1) * LOG_K))


def linearize_err(arr, setlog):
    """Feedback-error (log units) -> linear current counts (constant-height display)."""
    return (np.exp((setlog - np.asarray(arr, np.float64)) / LOG_K) - 1.0).astype(np.float32)


def z_display(arr, peaks_bright=True):
    """D8: raw Z puts a peak LOW; show -Z so peaks are bright."""
    return -arr if peaks_bright else arr


def e_display(arr, peaks_bright=True, linear=False, setlog=0):
    """D8: raw error puts a peak LOW; show -error.  Linear mode is already peaks-bright."""
    if linear:
        return linearize_err(arr, setlog)
    return -arr if peaks_bright else arr


# ----------------------------------------------------------------------------- live accumulation
class LiveFold:
    """Line-by-line accumulation into the four (H, half) buffers, exactly as LiveRaster did
    (including its display-time drift correction of the second-half lines).  Pure (no Qt)."""

    def __init__(self, H, half, drift_dx=0, drift_dy=0):
        self.H, self.half = int(H), int(half)
        self.drift_dx, self.drift_dy = int(drift_dx), int(drift_dy)
        shape = (self.H, self.half)
        self.z_trace = np.zeros(shape, np.float32); self.z_retrace = np.zeros(shape, np.float32)
        self.e_trace = np.zeros(shape, np.float32); self.e_retrace = np.zeros(shape, np.float32)
        self.painted = np.zeros(self.H, bool)
        self.paint_seq = np.zeros(self.H, np.int64)
        self.paint_counter = 0
        self.last_raw_row = -1

    def peek(self, line_number):
        """The sweep-boundary events this line WOULD trigger, without changing state (the live
        view snapshots and autolevels before the line is painted)."""
        raw = line_number % (2 * self.H)
        return {"raw": raw, "wrapped": raw < self.last_raw_row,
                "half_done": self.last_raw_row < self.H <= raw}

    def add_line(self, line_number, z_arr, err_arr):
        """Returns dict(raw, row, wrapped, half_done, painted) — the events LiveRaster reacts to."""
        H = self.H
        raw = line_number % (2 * H)
        wrapped = raw < self.last_raw_row
        half_done = self.last_raw_row < H <= raw
        self.last_raw_row = raw
        ev = {"raw": raw, "row": None, "wrapped": wrapped, "half_done": half_done, "painted": False}
        row = fold_row(raw, H)
        half = self.half
        if len(z_arr) < 2 * half:
            return ev
        zt, zr = split_line(z_arr, half)
        et, er = split_line(err_arr, half)
        if raw >= H:
            row -= self.drift_dy
            if not (0 <= row < H):
                return ev
            if self.drift_dx:
                zt = np.roll(zt, -self.drift_dx); zr = np.roll(zr, -self.drift_dx)
                et = np.roll(et, -self.drift_dx); er = np.roll(er, -self.drift_dx)
        self.z_trace[row, :] = zt.astype(np.float32); self.z_retrace[row, :] = zr.astype(np.float32)
        self.e_trace[row, :] = et.astype(np.float32); self.e_retrace[row, :] = er.astype(np.float32)
        self.painted[row] = True
        self.paint_counter += 1
        self.paint_seq[row] = self.paint_counter
        ev.update(row=row, painted=True)
        return ev

    def reset(self):
        for b in (self.z_trace, self.z_retrace, self.e_trace, self.e_retrace):
            b[:] = 0
        self.painted[:] = False
        self.paint_seq[:] = 0


# ----------------------------------------------------------------------------- recordings
def derive_height(settings, records, image_height=None, default=256):
    """H used to fold a recording (same precedence as the old sweep_index)."""
    return int(image_height or settings.get("image_height")
               or (int(settings.get("pixels_per_line", 0)) // 2)
               or (len(records[0][2]) // 2 if records else default))


def line_indices(records, H, mode="stamped", firmware=None):
    """Line index of every record under `mode`.  Returns (lines, info).  Slip correction is
    applied per geometry epoch (a change in pixels per line restarts the rule), and only to
    recordings from firmware that has the slip (FW <= 5.6, or unknown = all existing data)."""
    stamps = [r[1] for r in records]
    if mode == "stamped":
        return stamps, {"mode": "stamped"}
    if mode == "tick":
        raise NotImplementedError("tick line index needs v2 records (frame format v2)")
    if mode != "slip_corrected":
        raise ValueError(mode)
    if firmware and not _has_slip(firmware):
        return stamps, {"mode": "slip_corrected", "skipped": f"firmware {firmware} has no slip"}
    out, epochs = [], []
    start = 0
    for k in range(1, len(records) + 1):
        if k == len(records) or len(records[k][2]) != len(records[start][2]):
            bins = len(records[start][2])           # pixels per line = line-counter wrap
            seg, info = slip_correct(stamps[start:k], bins)
            out.extend(seg)
            info.update(first_record=start, last_record=k - 1, bins=bins)
            epochs.append(info)
            start = k
    return out, {"mode": "slip_corrected", "epochs": epochs}


def _has_slip(firmware):
    try:
        v = str(firmware).split("FW", 1)[-1].strip().split()[0]
        major, minor = (int(x) for x in v.split(".")[:2])
        return (major, minor) <= (5, 6)
    except Exception:
        return True


def build_sweeps(records, H, lines=None):
    """Segment records into sweeps (identical logic to the old sweep_index.build_index loop,
    driven by the chosen line indices).  Returns (sweeps, epochs)."""
    if lines is None:
        lines = [r[1] for r in records]
    epochs, sweeps = [], []
    cur = None
    prev_raw = None
    half = None
    epoch_id = 0

    def close(reason):
        nonlocal cur
        if cur is None:
            return
        cur["partial"] = cur["lines"] < H
        cur["end_reason"] = reason
        sweeps.append(cur)
        cur = None

    for idx, ((t, _stamp, z, e), line) in enumerate(zip(records, lines)):
        h2 = len(z) // 2
        if half is None:
            half = h2
        if h2 != half:
            close("geometry_change")
            epochs.append({"epoch": epoch_id, "pixels_per_direction": half})
            epoch_id += 1
            half = h2
            prev_raw = None
        raw = line % (2 * H)
        d = direction(raw, H)
        wrapped = prev_raw is not None and raw < prev_raw
        if cur is None or d != cur["dir"] or wrapped:
            close("boundary")
            cur = {"i": len(sweeps), "epoch": epoch_id, "dir": d,
                   "t_start": t, "t_end": t, "lines": 0,
                   "first_record": idx, "last_record": idx}
        cur["t_end"] = t
        cur["last_record"] = idx
        cur["lines"] += 1
        prev_raw = raw
    close("end_of_file")
    epochs.append({"epoch": epoch_id, "pixels_per_direction": half})
    return sweeps, epochs


def sweep_image(records, sweep, H, half, channel="z_trace", lines=None):
    """(H, half) float32 image of one sweep; NaN rows = lines never received.
    channel: z_trace | z_retrace | e_trace | e_retrace.  Identical to the old
    sweep_index.sweep_image when `lines` is None (stamped).

    With corrected `lines`, sweep identity (which records form sweep #i) stays the STAMPED
    segmentation, so sweep numbers used in reports and timelines never change (decision D34
    addendum); rows are placed by the corrected index.  The slip moves one boundary line into
    the neighbouring stamped sweep, so the image also looks one record either side and keeps
    only lines whose corrected index belongs to this sweep's direction."""
    img = np.full((H, half), np.nan, np.float32)
    src_z = channel.startswith("z")
    retrace = channel.endswith("retrace")
    a, b = sweep["first_record"], sweep["last_record"] + 1
    if lines is not None:
        a, b = max(0, a - 1), min(len(records), b + 1)
    for k in range(a, b):
        t, stamp, z, e = records[k]
        line = stamp if lines is None else lines[k]
        if len(z) < 2 * half:
            continue
        raw = line % (2 * H)
        if lines is not None and direction(raw, H) != sweep["dir"]:
            continue
        row = fold_row(raw, H)
        vals = (z if src_z else e)
        tr, rt = split_line(vals, half)
        img[row, :] = rt if retrace else tr
    return img


def corrections_path(frames_path):
    return frames_path[:-len(".frames")] + ".corrections.json"


def write_corrections(frames_path, info):
    """Change-log trail for a derived correction (D34).  Raw data is never modified; delete this
    file or use line_index='stamped' to revert."""
    rec = {"frames": os.path.basename(frames_path), "algorithm": "reconstruct.slip_correct",
           "algo_version": ALGO_VERSION, "rule": slip_correct.__doc__.strip().splitlines()[0],
           "rule_detail": "first Y-cycle after RUN: identity, then the stamp 0 that follows a stamp >= bins/2 "
                          "is line bins-1; afterwards true = (stamped - 1) mod bins",
           "created": _dt.datetime.now().isoformat(timespec="seconds"),
           "revert": "use line_index='stamped' (reproduces the old images exactly) or delete this file",
           "decision": "D34", "info": info}
    with open(corrections_path(frames_path), "w") as f:
        json.dump(rec, f, indent=1)
    return rec
