"""daylog — deterministic index/query helper over the per-day data folders.

Part of the day-wrap-up chain — authoritative runbook: TIMELINE_SKILL.md
(this folder).  Order: sweep_index.py → /timeline skill → daylog.py
--write → scan-notes summary → make_bundle.py.

The narrative layer is LLM-driven (Claude via the copilot bridge or CLI);
this tool is what the LLM calls so it never has to grope through a
thousand files by hand.  Works over the folders data_paths.py owns
(layout 2026-07-25: everything flat in <DATA_ROOT>/<2026-Jul-25>/).

1. Day inventory — chronological timeline of sessions, notes, scans, raw
   captures, stability runs (with verdicts), superscans, images:
       python daylog.py                # today
       python daylog.py 2026-Jul-15    # any day (2026-07-15 also accepted)
   Add --write to also drop the timeline as DAYLOG.md into the folder
   (e.g. for a TeamUpdate snapshot).

2. Point-in-time query — "what was happening at exactly this moment?":
       python daylog.py --at 1783834730467          # epoch ms (filenames)
       python daylog.py --at "2026-07-15 14:32:05"  # local wall clock
   Finds the session journal covering that instant, the nearest journal
   events either side, and every capture whose recording window spans it —
   each with the ready-to-run reconstruction command.

Qt-free; reads only filenames, JSON sidecars, and session journals.
"""
import argparse
import json
import os
import re
import sys
import time
from datetime import datetime

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import data_paths

_MS_RE = re.compile(r"(\d{13})")

# capture kinds by filename prefix: label + how to rebuild/inspect one
KINDS = {
    "raw_":        ("raw ISR capture",
                    "python raw_scan_reconstruct.py {p} <scan.frames> <spp> <px>"),
    "scan_":       ("continuous-scan frames",
                    "python replay_frames.py {p}"),
    "scst_":       ("legacy scan (verbatim)",
                    'python -c "import scst_logger,sys;'
                    "print(scst_logger.rebuild(sys.argv[1]))\" {p}"),
    "superscan_":  ("superscan", "load .npz (full data) / open .gsf in Gwyddion"),
    "gspc_":       ("grid spectroscopy cube", "np.load('{p}')"),
    "image_":      ("scan image save", "open .gsf/.tiff; .txt is raw ADC"),
    "session_":    ("session journal", "python daylog.py --at <t>"),
    "copilot_screen_": ("copilot screenshot", ""),
    "IVCurve":     ("IV curve", "Gwyddion ASCII curve"),
    "dIdVCurve":   ("dI/dV curve", "Gwyddion ASCII curve"),
}

# primary extension per family; everything else with the same stem is an
# artifact of it (sidecars, replay PNGs, npz, tiff...)
PRIMARY_EXT = {".frames", ".raw", ".scst", ".jsonl", ".csv", ".npz", ".txt",
               ".png", ".gsf"}


def _fmt_t(ts):
    return time.strftime("%H:%M:%S", time.localtime(ts))


def _file_ts(name, path):
    m = _MS_RE.search(name)
    return int(m.group(1)) / 1000.0 if m else os.path.getmtime(path)


def _kind_of(name):
    if "_stability_" in name:
        return "stability recording", "python stab_runner.py --verdict-only {p}"
    for prefix, (label, hint) in KINDS.items():
        if name.startswith(prefix) or prefix in name:
            return label, hint
    return "file", ""


def _sidecar_span(stem):
    """Best-effort [t_start, t_end] from a JSON sidecar next to the stem."""
    for ext in (".json",):
        try:
            with open(stem + ext) as f:
                side = json.load(f)
        except (OSError, ValueError):
            continue
        t0 = side.get("t_start") or side.get("started")
        t1 = side.get("t_end") or side.get("finished")
        return t0, t1, side
    return None, None, {}


def scan_day(day_folder):
    """Group the day's files into capture families keyed by timestamp stem."""
    families = {}   # stem -> {"ts", "files", "primary"}
    for name in sorted(os.listdir(day_folder)):
        path = os.path.join(day_folder, name)
        if not os.path.isfile(path) or name == "DAYLOG.md":
            continue
        m = _MS_RE.search(name)
        stem = (name[:m.end()] if m else os.path.splitext(name)[0])
        fam = families.setdefault(stem, {
            "ts": _file_ts(name, path), "files": [], "stem": stem})
        fam["files"].append(name)
    return sorted(families.values(), key=lambda f: f["ts"])


def _fam_sidecar(day_folder, fam):
    """(t0, t1, sidecar) for a family — looks for the family's own .json
    member (filenames may carry a _s<sessionId> suffix after the capture
    stamp, so the stem alone is not the sidecar name)."""
    for n in fam["files"]:
        if n.endswith(".json") and not n.endswith(
                ("_verdict.json", "_summary.json", ".sweeps.json")):
            return _sidecar_span(os.path.join(day_folder, n[:-5]))
    return _sidecar_span(os.path.join(day_folder, fam["stem"]))


def _session_of(fam):
    m = re.search(r"_s(\d{13})", fam["files"][0])
    return m.group(1) if m else None


def _family_line(day_folder, fam):
    lead = fam["files"][0]
    label, hint = _kind_of(lead)
    extras = []
    sid = _session_of(fam)
    if sid:
        extras.append(f"session {sid}")
    t0, t1, side = _fam_sidecar(day_folder, fam)
    if t0 and t1:
        extras.append(f"{t1 - t0:.0f}s")
    for k in ("rows", "n_frames", "n_blocks", "n_samples"):
        v = side.get(k)
        if v is not None:
            extras.append(f"{k}={v}")
    # stability verdict, if graded
    for name in fam["files"]:
        if name.endswith("_verdict.json"):
            try:
                with open(os.path.join(day_folder, name)) as f:
                    v = json.load(f)
                g = v.get("verdict") or v.get("grade") or v.get("pass")
                if g is not None:
                    extras.append(f"verdict={g}")
            except (OSError, ValueError):
                pass
    exts = ",".join(sorted({os.path.splitext(n)[1] or n for n in fam["files"]}))
    line = f"{_fmt_t(fam['ts'])}  {label:<26} {fam['stem']}  [{exts}]"
    if extras:
        line += "  (" + ", ".join(extras) + ")"
    if hint:
        line += f"\n          ↳ {hint.format(p=os.path.join(day_folder, lead))}"
    return line


def _journal_events(day_folder):
    """Notable rows from every session journal in the folder (skips the
    high-rate sample/command noise; commands are summarized per session)."""
    events = []
    for name in sorted(os.listdir(day_folder)):
        if not (name.startswith("session_") and name.endswith(".jsonl")):
            continue
        path = os.path.join(day_folder, name)
        n_cmd = n_sample = 0
        t_first = t_last = None
        last_type = None
        with open(path, errors="replace") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                t = rec.get("t")
                t_first = t_first if t_first is not None else t
                t_last = t
                typ = rec.get("type")
                last_type = typ
                if typ == "command":
                    n_cmd += 1
                elif typ == "sample":
                    n_sample += 1
                elif typ in ("session_start", "session_end", "note",
                             "snapshot", "setting", "record"):
                    d = rec.get("data", {})
                    if typ == "note":
                        txt = f'NOTE: "{d.get("text", "")}"'
                    elif typ == "record":
                        txt = f'{d.get("event")}: {os.path.basename(str(d.get("path")))}'
                    elif typ == "setting":
                        txt = f'setting {d.get("name")}: {d.get("old")} -> {d.get("new")}'
                    elif typ == "snapshot":
                        txt = f'snapshot: {d.get("event")}'
                    else:
                        txt = typ
                    events.append((t, f"{txt}   [{name}]"))
        if t_first is not None:
            end = (f"closes {_fmt_t(t_last)}" if last_type == "session_end"
                   else f"UNCLEAN END {_fmt_t(t_last)} — crash?")
            events.append((t_first,
                           f"journal {name} opens ({n_cmd} commands, "
                           f"{n_sample} samples, {end})"))
    return events


def build_daylog(day_folder):
    day = os.path.basename(day_folder)
    fams = scan_day(day_folder)
    entries = [(f["ts"], _family_line(day_folder, f)) for f in fams
               if not f["files"][0].startswith("session_")]
    entries += _journal_events(day_folder)
    entries.sort(key=lambda e: (e[0] if e[0] is not None else 0))
    n_files = sum(len(f["files"]) for f in fams)
    lines = [f"# Day log — {day}",
             f"{n_files} files, {len(fams)} captures/records.  "
             f"Generated {datetime.now():%Y-%m-%d %H:%M:%S} by daylog.py.",
             ""]
    for t, txt in entries:
        lines.append((f"- {_fmt_t(t)}  " if txt[:8].count(":") < 2 else "- ")
                     + txt.replace("\n", "\n  "))
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------- --coverage

def _csv_span(path):
    """(t_start, t_end) of a stability CSV: filename stamp + last row's
    elapsed_s, read from the tail so multi-GB files stay cheap."""
    m = _MS_RE.search(os.path.basename(path))
    if not m:
        return None
    t0 = int(m.group(1)) / 1000.0
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as f:
            f.seek(max(0, size - 8192))
            lines = [ln for ln in f.read().split(b"\n") if ln.strip()]
        last = lines[-1].split(b",")[0]
        return (t0, t0 + float(last))
    except (OSError, ValueError, IndexError):
        return (t0, t0)


def _journal_span(path):
    t0 = t1 = None
    with open(path, errors="replace") as f:
        for line in f:
            try:
                t = json.loads(line).get("t")
            except ValueError:
                continue
            t0 = t0 if t0 is not None else t
            t1 = t
    return (t0, t1) if t0 is not None else None


def _subtract(base, covers):
    """Sub-intervals of ``base`` (t0,t1) not covered by any of ``covers``."""
    holes, cur = [], base[0]
    for c0, c1 in sorted(covers):
        if c1 <= cur:
            continue
        if c0 > base[1]:
            break
        if c0 > cur:
            holes.append((cur, min(c0, base[1])))
        cur = max(cur, c1)
    if cur < base[1]:
        holes.append((cur, base[1]))
    return [(a, b) for a, b in holes if b - a > 2.0]   # ignore <2 s seams


def coverage(day_folder):
    """Per stream: when was it writing, vs. when the port was open?"""
    sessions, streams = [], {"status": [], "raw": [], "frames": [], "scst": []}
    for name in sorted(os.listdir(day_folder)):
        path = os.path.join(day_folder, name)
        if not os.path.isfile(path):
            continue
        if name.startswith("session_") and name.endswith(".jsonl"):
            sp = _journal_span(path)
            if sp:
                sessions.append(sp)
        elif "_stability_" in name and name.endswith(".csv"):
            sp = _csv_span(path)
            if sp:
                streams["status"].append(sp)
        elif name.endswith((".raw", ".frames", ".scst")):
            kind = {".raw": "raw", ".frames": "frames", ".scst": "scst"}[
                os.path.splitext(name)[1]]
            stem = os.path.join(day_folder,
                                name.rsplit(".", 1)[0])
            t0, t1, _ = _sidecar_span(stem)
            if t0:
                # Sidecar without t_end = capture never finalized (crash);
                # the file's mtime is the last flushed write, i.e. the
                # true end of coverage.
                if not t1:
                    try:
                        t1 = os.path.getmtime(path)
                    except OSError:
                        t1 = t0
                streams[kind].append((t0, t1))
    print(f"# Coverage — {os.path.basename(day_folder)}")
    if not sessions:
        print("no session journals: port-open windows unknown; "
              "stream spans listed raw:")
        for kind, spans in streams.items():
            for a, b in spans:
                print(f"  {kind:<7} {_fmt_t(a)}–{_fmt_t(b)}")
        return
    for s0, s1 in sessions:
        dur = s1 - s0
        print(f"\nport-open {_fmt_t(s0)}–{_fmt_t(s1)}  ({dur/60:.1f} min)")
        for kind in ("status", "raw", "frames", "scst"):
            spans = streams[kind]
            holes = _subtract((s0, s1), spans)
            covered = dur - sum(b - a for a, b in holes)
            pct = 100.0 * covered / dur if dur > 0 else 0.0
            note = "" if kind in ("status", "raw") else "  (scan-time only)"
            print(f"  {kind:<7} {pct:5.1f}% covered{note}")
            for a, b in (holes if kind in ("status", "raw") else []):
                print(f"          HOLE {_fmt_t(a)}–{_fmt_t(b)} "
                      f"({(b - a)/60:.1f} min)")


# ---------------------------------------------------------------- --at query

def _parse_at(s):
    s = s.strip()
    if re.fullmatch(r"\d{13}", s):
        return int(s) / 1000.0
    if re.fullmatch(r"\d{9,11}(\.\d+)?", s):
        return float(s)
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(s, fmt).timestamp()
        except ValueError:
            pass
    raise SystemExit(f"cannot parse --at time: {s!r}")


def query_at(t):
    day_folder = os.path.join(data_paths.DATA_ROOT, data_paths.day_name(t))
    print(f"@ {datetime.fromtimestamp(t):%Y-%m-%d %H:%M:%S.%f} local "
          f"(epoch_ms {int(t * 1000)})  ->  {day_folder}")
    if not os.path.isdir(day_folder):
        print("no data folder for that day")
        return
    # captures whose recorded window spans t (sidecar span, else ±5 min of
    # the filename stamp for span-less saves)
    print("\n== captures covering this instant ==")
    hits = 0
    for fam in scan_day(day_folder):
        t0, t1, _ = _fam_sidecar(day_folder, fam)
        if t0 is None:
            t0, t1 = fam["ts"], fam["ts"] + 1
        if (t0 or 0) - 2 <= t <= (t1 or t0 or 0) + 2:
            print(_family_line(day_folder, fam))
            hits += 1
    if not hits:
        print("(none — nearest captures below)")
        fams = scan_day(day_folder)
        for fam in sorted(fams, key=lambda f: abs(f["ts"] - t))[:3]:
            print(_family_line(day_folder, fam))
    # journal context: nearest events either side
    print("\n== journal context ==")
    rows = []
    for name in sorted(os.listdir(day_folder)):
        if not (name.startswith("session_") and name.endswith(".jsonl")):
            continue
        with open(os.path.join(day_folder, name), errors="replace") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                if rec.get("type") == "sample":
                    continue
                rows.append((rec.get("t", 0), name, rec))
    rows.sort(key=lambda r: r[0])
    before = [r for r in rows if r[0] <= t][-6:]
    after = [r for r in rows if r[0] > t][:6]
    for tt, name, rec in before + [(t, "", {"type": ">>> QUERY TIME <<<"})] + after:
        d = rec.get("data", {})
        detail = d.get("cmd") or d.get("text") or d.get("event") or ""
        print(f"  {_fmt_t(tt)}  {rec.get('type', ''):<14} {detail}   {name}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("day", nargs="?",
                    help="day folder name (2026-Jul-15) or ISO date; default today")
    ap.add_argument("--at", metavar="T",
                    help="epoch ms / epoch s / 'YYYY-MM-DD HH:MM[:SS]' — "
                         "show what was happening at that instant")
    ap.add_argument("--write", action="store_true",
                    help="also write the timeline as DAYLOG.md in the folder")
    ap.add_argument("--coverage", action="store_true",
                    help="report per-stream recording coverage vs port-open "
                         "time, with explicit holes")
    args = ap.parse_args()

    if args.at:
        query_at(_parse_at(args.at))
        return 0

    if args.day:
        m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", args.day)
        name = (data_paths.day_name(datetime(int(m.group(1)), int(m.group(2)),
                                             int(m.group(3)), 12).timestamp())
                if m else args.day)
    else:
        name = data_paths.day_name()
    day_folder = os.path.join(data_paths.DATA_ROOT, name)
    if not os.path.isdir(day_folder):
        raise SystemExit(f"no such day folder: {day_folder}")
    if args.coverage:
        coverage(day_folder)
        return 0
    text = build_daylog(day_folder)
    print(text)
    if args.write:
        with open(os.path.join(day_folder, "DAYLOG.md"), "w",
                  encoding="utf-8") as f:
            f.write(text)
        print(f"[daylog] written to {os.path.join(day_folder, 'DAYLOG.md')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
