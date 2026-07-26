"""make_bundle — self-contained team share of the offline replay tools.

Produces exactly the layout Matt proposed (2026-07-26): the python files
on top, the day folder(s) under a local ``data/``, plus README,
requirements and a double-click launcher.  A teammate needs Python 3.10+
and ``pip install -r requirements.txt`` — nothing else (no hardware, no
serial, read-only).

    python make_bundle.py 2026-Jul-16 [more days...] [--out DIR] [--zip]

Default output: TeamUpdate/DataSyncArchive/replay-bundle-<firstday>/
"""
import argparse
import os
import shutil
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))       # .../qtpanda/replay
_QTPANDA = os.path.dirname(_HERE)                        # .../qtpanda
sys.path.insert(0, _QTPANDA)

import data_paths

# Frame-based viewer chain only (no serial imports anywhere); bundles
# stay FLAT — replay tools and their qtpanda-side deps in one folder.
FILES = [(_HERE, n) for n in
         ("sweep_player.py", "sweep_index.py", "timeline_doc.py",
          "daylog.py")] + \
        [(_QTPANDA, n) for n in
         ("frame_logger.py", "session_journal.py", "data_paths.py",
          "replay_frames.py")]

REQUIREMENTS = """\
numpy
PySide6
pyqtgraph
Pillow      # optional: PNG + GIF export
tifffile    # optional: TIFF export
"""

README = """\
# QT-Panda offline replay bundle — {days}

Sweep-by-sweep replay of continuous-scan data, fully offline (no
hardware, read-only).

## Run (any OS)
    pip install -r requirements.txt      (once; needs Python 3.10+)
    python main.py                       (auto-opens the bundled day)
    python main.py 2026-Jul-15           (pick a day if several bundled)
Windows: double-click run_player.bat.   Linux/macOS: sh run_player.sh

## What you get
* A/B side-by-side sweeps, play/step/scrub (drag the red A / blue B
  lines), viridis + histogram levels, ~nm scale per sweep.
* Timeline with the day's narrative (TIMELINE.json): colored activity
  regions, key operator notes, crash markers, and the bracket rows
  (state / phases / incidents / data-quality / ...).  "Visible
  Sections" menu hides rows; drag the splitter to enlarge images.
* Export menu: Gwyddion .gsf (real nm axes embedded), float32 TIFF,
  PNG, and GIF animation from sweep A to B.
* `python daylog.py {first}` — day inventory; `--at <time>` = what was
  recording at that instant; `--coverage` = per-stream coverage/holes.

## Layout
    *.py            the tools (data_paths auto-detects ./data)
    data/{first}/   everything recorded that day, flat, self-describing
"""

RUN_BAT = """\
@echo off
cd /d "%~dp0"
python main.py %*
pause
"""

RUN_SH = """\
#!/usr/bin/env sh
# works via `sh run_player.sh` even without the exec bit (zip loses it)
cd "$(dirname "$0")"
python3 main.py "$@"
"""

# The bundle's entry point.  Generated (not copied) because in the repo
# main.py is the instrument GUI — inside a bundle there is no collision.
MAIN_PY = '''\
"""Bundle entry point: ``python main.py [day]`` from this folder (or by
full path — it chdirs itself).  With no argument it opens the bundled
day, or the newest one if several are bundled."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.chdir(HERE)

import sweep_player


def main():
    args = sys.argv[1:]
    if not args:
        droot = os.path.join(HERE, "data")
        days = (sorted(d for d in os.listdir(droot)
                       if os.path.isdir(os.path.join(droot, d)))
                if os.path.isdir(droot) else [])
        if not days:
            raise SystemExit("no day folders under ./data — "
                             "pass one explicitly")
        args = [days[-1]]
        print(f"[main] opening {args[0]} "
              f"(bundled: {', '.join(days)})")
    sys.argv = [sys.argv[0]] + args
    sweep_player.main()


if __name__ == "__main__":
    main()
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("days", nargs="+", help="day folder names, e.g. 2026-Jul-16")
    ap.add_argument("--out", default=None)
    ap.add_argument("--zip", action="store_true")
    args = ap.parse_args()

    first = args.days[0]
    # DataSyncArchive sits next to the data root (TeamUpdate/...), so
    # derive it from data_paths — correct from any code location.
    out = args.out or os.path.join(
        os.path.dirname(data_paths.DATA_ROOT), "DataSyncArchive",
        f"replay-bundle-{first}")
    os.makedirs(out, exist_ok=True)

    for src_dir, name in FILES:
        shutil.copy2(os.path.join(src_dir, name), out)
    total = 0
    for day in args.days:
        src = os.path.join(data_paths.DATA_ROOT, day)
        if not os.path.isdir(src):
            raise SystemExit(f"no such day folder: {src}")
        dst = os.path.join(out, "data", day)
        if os.path.isdir(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        total += sum(os.path.getsize(os.path.join(r, f))
                     for r, _, fs in os.walk(dst) for f in fs)
    days = ", ".join(args.days)
    with open(os.path.join(out, "requirements.txt"), "w",
              encoding="utf-8") as f:
        f.write(REQUIREMENTS)
    with open(os.path.join(out, "README.md"), "w", encoding="utf-8") as f:
        f.write(README.format(days=days, first=first))
    with open(os.path.join(out, "run_player.bat"), "w",
              encoding="ascii") as f:
        f.write(RUN_BAT)
    with open(os.path.join(out, "run_player.sh"), "w", newline="\n",
              encoding="ascii") as f:
        f.write(RUN_SH)
    with open(os.path.join(out, "main.py"), "w", encoding="utf-8") as f:
        f.write(MAIN_PY)

    # strip any bytecode caches (e.g. from a local test run) so the
    # bundle/zip ship clean
    for root, dirs, _files in os.walk(out):
        if "__pycache__" in dirs:
            shutil.rmtree(os.path.join(root, "__pycache__"))
            dirs.remove("__pycache__")
    print(f"bundle: {out}  ({total / 1e6:.1f} MB data, "
          f"{len(FILES)} scripts)")
    if args.zip:
        z = shutil.make_archive(out, "zip", out)
        print(f"zip:    {z}  ({os.path.getsize(z) / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
