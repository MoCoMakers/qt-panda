"""sweep_index — derived per-sweep index over logged continuous-scan frames.

FIRST step of the day-wrap-up chain — authoritative runbook:
TIMELINE_SKILL.md (this folder).  Order: sweep_index.py → /timeline
skill → daylog.py --write → scan-notes summary → make_bundle.py.

The .frames files already hold everything needed for sweep-level replay:
every line carries its own pc_time, and the Y triangle folds one
line-counter cycle (0..2H-1) into an up sweep then a mirrored down sweep
(same mapping as LiveRaster/replay_frames, corrected 2026-07-15).  This
module segments a .frames file into completed sweeps — each with start/end
timestamps, line count, direction, and a partial flag — entirely offline
(no hardware, no COM port; days later is the design case).

The index is DERIVED and regenerable; it never modifies the verbatim data.
Written as <base>.sweeps.json next to the .frames file.

Geometry changes (pixels-per-line) mid-file split the index into epochs;
sweeps only stack within an epoch.  Partial sweeps (scan started/halted
mid-pass, or dropped lines) stay in the index flagged partial — viewable,
not stackable; the raw ISR tap holds their ground truth.

CLI:
    python sweep_index.py <file.frames | day-folder> [--height H]
"""
import json
import os
import re
import sys

import numpy as np

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import frame_logger
import reconstruct

# v2 (2026-10-23): segmentation/fold via reconstruct.py; slip-corrected rows (D34) with frozen
# sweep numbering (D39) and a <base>.corrections.json change-log.  Older indexes are rebuilt.
INDEX_VERSION = 2
DEFAULT_LINE_INDEX = "slip_corrected"

DEFAULT_HEIGHT = 256
_SID_RE = re.compile(r"_s(\d{13})")


def _session_of(path):
    m = _SID_RE.search(os.path.basename(path))
    return int(m.group(1)) if m else None


def load_frames(frames_path):
    """All line records of a file in memory: list of (t, line, z, e).
    A one-hour run at ~4 Hz lines is tens of MB — fine to hold."""
    return list(frame_logger.read_frames(frames_path))


def _scsz_timeline(frames_path, sidecar):
    """Journaled scan-size changes [(t, nm), ...] covering this run.

    The sidecar's scan_size_nm is captured once at RUN; mid-scan zooms
    only exist as journaled SCSZ commands (20-bit firmware units).
    Convert with the sidecar's own calibration: X-DAC volts per 16-bit
    LSB × piezo nm/V ÷ 16 (20-bit position → 16-bit DAC)."""
    cal = (sidecar.get("settings") or {}).get("calibration") or {}
    v_lsb, nm_v = cal.get("dac_x_v_per_lsb"), cal.get("piezo_x_nm_per_v")
    if not (v_lsb and nm_v):
        return []
    sid = _session_of(frames_path)
    jpath = (os.path.join(os.path.dirname(os.path.abspath(frames_path)),
                          f"session_{sid}.jsonl") if sid else None)
    if not (jpath and os.path.isfile(jpath)):   # bundle moved: try sidecar's
        jpath = (sidecar.get("settings") or {}).get("journal")
    if not (jpath and os.path.isfile(jpath)):
        return []
    out = []
    with open(jpath, errors="replace") as f:
        for ln in f:
            try:
                rec = json.loads(ln)
            except ValueError:
                continue
            if rec.get("type") != "command":
                continue
            cmd = str(rec.get("data", {}).get("cmd", ""))
            if cmd.startswith("SCSZ "):
                try:
                    units = float(cmd.split()[1])
                except (IndexError, ValueError):
                    continue
                out.append((rec.get("t", 0.0),
                            round(units * v_lsb * nm_v / 16.0, 4)))
    return out


def build_index(frames_path, image_height=None, records=None, line_index=DEFAULT_LINE_INDEX):
    """Segment a .frames file into sweeps.  Returns the index dict."""
    sidecar = frame_logger.read_sidecar(frames_path) or {}
    settings = sidecar.get("settings", {})
    records = load_frames(frames_path) if records is None else records
    # Derive H from the DATA when not told: the sidecar has no
    # "image_height" key, so the old DEFAULT_HEIGHT fallback folded every
    # non-512-px recording at the wrong period — daylog, sweep_player and
    # the timeline draft then saw 0 full sweeps in a 128-px file that
    # really holds 168 (audit 2026-07-31).
    H = reconstruct.derive_height(settings, records, image_height, DEFAULT_HEIGHT)
    # Sweep identity (numbering) always comes from the STAMPED line numbers (D39): references
    # like "#1808" stay valid.  The slip correction only changes where rows are placed.
    sweeps, epochs = reconstruct.build_sweeps(records, H)
    lines, li_info = reconstruct.line_indices(records, H, line_index)
    if line_index == "slip_corrected" and frames_path and records:
        n_remap = sum(e.get("n_remapped", 0) for e in li_info.get("epochs", []))
        if n_remap:                          # trail details; written by write_index only
            stamps = [r[1] for r in records]
            changed = [k for k, (a, b) in enumerate(zip(stamps, lines)) if a != b]
            li_info["affected_sweeps"] = [s["i"] for s in sweeps if s["last_record"] >= changed[0]]
            li_info["mapping"] = "records >= slip_phase_from_record: corrected = (stamped - 1) mod bins"
            li_info["examples"] = [[k, stamps[k], lines[k]] for k in changed[:8]]

    # per-sweep physical scale: last journaled SCSZ at or before each
    # sweep's start (mid-scan zooms make the sidecar's single value stale)
    scsz = _scsz_timeline(frames_path, sidecar)
    for s in sweeps:
        nm = None
        for t, v in scsz:
            if t <= s["t_start"]:
                nm = v
            else:
                break
        if nm is not None:
            s["scan_size_nm"] = nm

    return {
        "index_version": INDEX_VERSION,
        "line_index": line_index,
        "line_index_info": li_info,
        "source": os.path.basename(frames_path),
        "session": _session_of(frames_path),
        "image_height": H,
        "settings": settings,
        "t_start": records[0][0] if records else None,
        "t_end": records[-1][0] if records else None,
        "n_records": len(records),
        "epochs": epochs,
        "sweeps": sweeps,
    }


def index_path(frames_path):
    return frames_path[:-len(".frames")] + ".sweeps.json"


def write_index(frames_path, image_height=None):
    idx = build_index(frames_path, image_height)
    with open(index_path(frames_path), "w") as f:
        json.dump(idx, f, indent=1)
    # D34 change-log trail beside the persisted index (build_index alone stays read-only)
    if idx["line_index_info"].get("affected_sweeps"):
        reconstruct.write_corrections(frames_path, idx["line_index_info"])
    return idx


def load_or_build(frames_path, image_height=None):
    """Cached index, rebuilt automatically when the .frames file is newer
    than its index — so reviewing TODAY mid-session always sees the
    sweeps recorded since the last build."""
    p = index_path(frames_path)
    try:
        if os.path.getmtime(p) >= os.path.getmtime(frames_path):
            with open(p) as f:
                idx = json.load(f)
            if idx.get("index_version") == INDEX_VERSION:
                return idx
    except (OSError, ValueError):
        pass
    return write_index(frames_path, image_height)


def sweep_image(records, sweep, H, half, channel="z_trace", lines=None):
    """(H, half) float32 image of one sweep; NaN rows = lines never
    received (partial sweep / drops), so viewers can show them distinctly.
    channel: z_trace | z_retrace | e_trace | e_retrace.  `lines` = corrected
    line indices (line_indices_for); None = stamped (the pre-v2 behaviour)."""
    return reconstruct.sweep_image(records, sweep, H, half, channel, lines)


def line_indices_for(records, idx, mode=None):
    """Line indices for a recording's records under the index's mode (or `mode`)."""
    mode = mode or idx.get("line_index", "stamped")
    lines, _ = reconstruct.line_indices(records, idx["image_height"], mode)
    return lines


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    height = None
    if "--height" in sys.argv:
        height = int(sys.argv[sys.argv.index("--height") + 1])
    files = ([target] if target.endswith(".frames") else
             sorted(os.path.join(target, n) for n in os.listdir(target)
                    if n.endswith(".frames")))
    total = 0
    for fp in files:
        idx = write_index(fp, height)
        full = sum(1 for s in idx["sweeps"] if not s["partial"])
        part = len(idx["sweeps"]) - full
        total += len(idx["sweeps"])
        print(f"{os.path.basename(fp)}: {full} full + {part} partial sweeps, "
              f"{len(idx['epochs'])} epoch(s)")
    print(f"indexed {len(files)} files, {total} sweeps")


if __name__ == "__main__":
    main()
