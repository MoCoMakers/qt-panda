# QT-Panda Replay & Timeline — Usability Guide

*Session build 2026-07-25/26. Operator-facing: how to drive everything.
For what exists and its guarantees, see `replay-feature-scope.md`.*

## Launching the player

| From | How |
|---|---|
| The instrument GUI | **Review Day** button (next to REC/RAW indicator) — opens today's folder, every session since midnight. Independent process; cannot touch the port or live GUI. |
| Command line | `cd software\pc\qtpanda\replay` then `python sweep_player.py 2026-Jul-15` (day name, day path, or a single `.frames` file) |
| A team bundle | unzip → `python main.py` (auto-opens the bundled day); Windows `run_player.bat`, Linux/macOS `sh run_player.sh` |

**How the tools find data — fully automatic:** every replay tool uses
the same `data_paths.py` as the instrument writers, resolving in order:
`QTPANDA_DATA` env var → a `data\` folder beside the scripts (bundles) →
upward search to the repo's `TeamUpdate\data` → auto-created if absent.
A bare day name like `2026-Jul-15` therefore always means the same
folder the instrument saved into; no flags or configuration.

**Freshness check:** the title bar shows `· timeline HH:MM:SS` — the
generation time of the narrative document it loaded. If you have several
windows open, trust the newest stamp and close the rest (stale windows
were our #1 source of confusion this session).

## The player, top to bottom

**A/B panes** — two sweeps side by side, viridis colormap, one shared
scale (the histogram on the right drives both, so brightness differences
are real). Labels show sweep #, direction ▲▼, completion timestamps,
**~nm across** (the calibrated red-box size at capture time — suspected,
not verified), partial status, session id, and source file. Partial
sweeps render missing lines at the floor color.

**Histogram (right of panes)** — drag the region handles to re-level;
right-click the gradient for other colormaps. **auto levels** checkbox
(transport bar): on = re-level 2–98 % of A every sweep (like the live
raster); off = your manual levels hold while stepping/playing — use off
for honest A-vs-B or GIF export.

**Transport bar** — `◀ ▶play ▶|` (also **space** / **arrow keys**),
speed 0.25–999× (type any value; adaptive click-steps), channel
(`e_trace`, `e_retrace`, `z_trace`, `z_retrace`), **B follows A** with
offset, **all raw markers** (re-show the unconsolidated journal lines),
**Visible Sections ▾**, **Export ▾**.

**Timeline** — clock-time axis. Blue dots = completed sweeps (up above /
down below the axis), orange = partials. Colored bands = the day's
narrative regions; vertical lines = important events (green milestones,
red crashes, magenta settings). Hover anything for full text. Click
anywhere to seek. **Drag the red A or blue B line to scrub at any
speed** — while "B follows A" is on, dragging B changes the offset
instead. Mouse-drag/zoom the axis to zoom in time.

**Bracket lane** — the change-event report: up to 10 `|____|` rows,
numbered and color-coded at the left edge. Rows follow a convention
(state / phases / incidents / data-quality / uptime / resolution eras /
verdicts / sub-experiments / raw coverage / setup). **Visible Sections ▾**
toggles rows (matching color swatch + number); hidden rows compact away.

**Splitter** — drag the divider under the images to give them any size;
launch and maximize restore the default proportions.

## Export ▾

| Item | What you get |
|---|---|
| Export A / Export B | Save dialog, three formats: **.gsf** — Gwyddion Simple Field, float32 with the sweep's real nm axes + offsets embedded (opens at true scale; warns if the run never recorded its size); **.tiff** — raw float32 + metadata (sweep, channel, times, session); **.png** — exactly what's on screen (levels + colormap). |
| GIF A → B | Animates every sweep from A to B (backward if B < A). Popup asks fps (default 10) and shows the frame count first; frames use the *current* channel/levels/colormap, fixed for the whole clip. |

## Asking questions of a day (`daylog.py`)

```
python daylog.py 2026-Jul-15              # chronological inventory (--write drops DAYLOG.md)
python daylog.py --at 1783834735000       # what was recording at this exact instant
python daylog.py --at "2026-07-15 03:20"  #   (epoch ms or local wall clock)
python daylog.py 2026-Jul-15 --coverage   # per-stream % recorded vs port-open, with HOLEs
```
`--at` prints every capture whose window spans the instant, each with its
ready-to-run reconstruction command, plus surrounding journal context.

## The timeline narrative (`/timeline` skill)

Say `/timeline 2026-Jul-17` (or "prep the timeline for …") and Claude:
draft-consolidates the day (`timeline_doc.py --draft`), reads the
journals, writes `TIMELINE.json` (regions, important events, bracket
report — human notes carried verbatim, never compressed), and must pass
the linter (`timeline_doc.py <day> --check` → `OK … PLAYER-LOAD OK`)
plus an offscreen render before it counts as done. Regenerating later
with better knowledge is always safe — the document is derived.

The skill's canonical definition is version-controlled at
`software/pc/qtpanda/replay/TIMELINE_SKILL.md`; the live copy
(`.claude/skills/timeline/SKILL.md`) is gitignored, so on a fresh
machine/session: copy the canonical file to that path and `/timeline`
works.

## Sharing with the team (`make_bundle.py`)

```
python make_bundle.py 2026-Jul-16 --zip     # add more day names to bundle several
```
Produces `DataSyncArchive/replay-bundle-<day>/` (+ `.zip`): scripts on
top, `data/<day>/` underneath, README, `requirements.txt`,
`run_player.bat`. A teammate needs Python 3.10+ and
`pip install -r requirements.txt` — 3 packages to view (numpy, PySide6,
pyqtgraph), 2 optional for exports (Pillow, tifffile). No hardware, no
serial, strictly read-only.
