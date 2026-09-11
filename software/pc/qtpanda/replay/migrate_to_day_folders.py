"""migrate_to_day_folders — one-time move of scattered data into DATA_ROOT.

Layout change 2026-07-25 (see data_paths.py): everything the instrument
saves lives flat in per-day folders under TeamUpdate/data.  This script
rehomes the historical scatter:

    qtpanda/raw/*      qtpanda/scans/*     qtpanda/logs/*
    qtpanda/images/*   TeamUpdate/data/<top-level files>

Placement: the first 13-digit epoch-milliseconds run in the filename wins
(that is the capture time every logger embeds); files without one fall
back to their mtime.  Related files (CSV + _verdict.json + _summary.json,
scan_X.frames + sidecar + replay PNGs) share the same embedded stamp, so
groups land in the same day automatically.

stab_sessions_ledger.jsonl stays at DATA_ROOT top level — it is the
cross-day ledger, not a day's capture.

Dry-run by default; pass --apply to move.  Never overwrites: a name
collision gets a _dupN suffix and is reported.
"""
import argparse
import os
import re
import shutil
import sys
import time

_QTPANDA = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _QTPANDA)

import data_paths

# the historical scatter lived next to the instrument code (qtpanda/)
SOURCES = [os.path.join(_QTPANDA, d)
           for d in ("raw", "scans", "logs", "images")]
KEEP_AT_ROOT = {"stab_sessions_ledger.jsonl", "README.md"}

_MS_RE = re.compile(r"(\d{13})")


def capture_time_s(path):
    m = _MS_RE.search(os.path.basename(path))
    if m:
        return int(m.group(1)) / 1000.0
    return os.path.getmtime(path)


def plan(extra_dirs=()):
    moves = []          # (src, day_name)
    # 1) the four legacy folders next to the code, plus any stray folders
    #    passed on the command line (e.g. an old sticky live-raster target)
    for src_dir in list(SOURCES) + [os.path.abspath(d) for d in extra_dirs]:
        if not os.path.isdir(src_dir):
            continue
        for name in sorted(os.listdir(src_dir)):
            p = os.path.join(src_dir, name)
            if os.path.isfile(p):
                moves.append((p, data_paths.day_name(capture_time_s(p))))
    # 2) loose files at DATA_ROOT top level (pre-layout stability CSVs etc.)
    root = data_paths.DATA_ROOT
    if os.path.isdir(root):
        for name in sorted(os.listdir(root)):
            p = os.path.join(root, name)
            if os.path.isfile(p) and name not in KEEP_AT_ROOT:
                moves.append((p, data_paths.day_name(capture_time_s(p))))
    return moves


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="actually move files (default: dry-run report)")
    ap.add_argument("--extra", nargs="*", default=[], metavar="DIR",
                    help="additional stray folders to fold in")
    args = ap.parse_args()

    moves = plan(args.extra)
    per_day = {}
    for src, day in moves:
        per_day.setdefault(day, []).append(src)

    print(f"DATA_ROOT: {data_paths.DATA_ROOT}")
    for day in sorted(per_day):
        print(f"  {day}: {len(per_day[day])} files")
    print(f"  total: {len(moves)} files")

    if not args.apply:
        print("\nDry-run only.  Re-run with --apply to move.")
        return 0

    moved, dups, failed = 0, 0, []
    for src, day in moves:
        dst_dir = os.path.join(data_paths.DATA_ROOT, day)
        os.makedirs(dst_dir, exist_ok=True)
        dst = os.path.join(dst_dir, os.path.basename(src))
        if os.path.abspath(src) == os.path.abspath(dst):
            continue
        n = 0
        while os.path.exists(dst):
            n += 1
            root_, ext = os.path.splitext(os.path.basename(src))
            dst = os.path.join(dst_dir, f"{root_}_dup{n}{ext}")
        try:
            shutil.move(src, dst)
            moved += 1
            dups += 1 if n else 0
        except OSError as e:
            failed.append((src, str(e)))   # e.g. an open live file: skip, keep
    for d in SOURCES:
        try:
            if os.path.isdir(d) and not os.listdir(d):
                os.rmdir(d)
        except OSError:
            pass
    print(f"\nmoved {moved} files ({dups} renamed as _dupN)")
    if failed:
        print(f"SKIPPED {len(failed)} (left in place):")
        for src, err in failed:
            print(f"  {src}: {err}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
