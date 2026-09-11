# QT-Panda Replay & Timeline — Feature Scope

*What was built in the 2026-07-25/26 session, with explicit guarantees.
Per the standing-invariants rule, every claim below is marked
**guaranteed**, **conditional** (with the condition), or **impossible**
(with why). Companion: `replay-usability-guide.md`.*

## 1. Data layout (the foundation)

- **Guaranteed:** every save lands flat in `TeamUpdate/data/<2026-Jul-DD>/`.
  `data_paths.py` is the only path authority (absolute root, env override
  `QTPANDA_DATA`, or a `data/` folder beside the scripts in a bundle);
  day folder resolved at capture *start*, so overnight runs split at
  midnight. All 1,355 historical files were migrated by embedded
  epoch-ms timestamps.
- **Guaranteed:** filenames carry type prefix + capture epoch-ms +
  `_s<sessionId>` (the journal's stamp), so one GUI run's files share a
  visible token across a crash-resume day. Crashes are detectable
  (journal without `session_end`; sidecar without `t_end` → mtime is the
  true end of coverage).
- **Conditional:** an *absolute* path typed into a save box is respected
  verbatim — the one deliberate escape hatch.

## 2. Recording posture

- **Guaranteed (from 2026-07-26 forward):** journal + 200 Hz status CSV
  + 25 kHz RAWD raw tap all auto-start at port open; a 2 s watchdog
  re-arms stream and raw tap if they drop. One continuous raw file per
  capture — **never rotated, split, or pruned** (operator hard rule).
  All journal record types are tm-anchored (firmware millis); raw
  sidecar records `control_dt_us`, decim, preamp gain. GUI shows a
  `REC ● RAW ●` indicator.
- **Conditional:** legacy synchronous ops (SCST/noise/spectroscopy)
  pause binary streams — protocol limit; those scans are captured
  verbatim by `scst_logger` instead.
- **Impossible:** raw ground truth before 2026-07-26 outside the
  manually-armed windows — coverage is ~0 % there. Known, documented;
  `daylog.py --coverage` makes any day's holes explicit.

## 3. Sweep index (`sweep_index.py`)

- **Guaranteed:** every `.frames` file segments into per-sweep records
  (direction, start/end pc-time, line count, partial flag) — derived,
  regenerable, never mutates captures; auto-rebuilds when the frames
  file is newer (mid-day review sees fresh sweeps). Geometry changes
  split epochs; stacking is only valid within an epoch. Retroactive:
  works on every frames file ever logged (4,232 sweeps recovered for
  Jul-15 alone).
- **Conditional:** absolute per-sample physical scale needs
  `scan_size_nm` in the run's sidecar — shown as “~N nm (suspected)”;
  runs without it say “scan size unknown”, never guessed.
- **Impossible:** sweep-level replay of legacy SCST scans (row-time
  resolution only) — their verbatim `.scst` logs rebuild images but not
  the sweep timeline.

## 4. Player (`sweep_player.py`)

Fully offline, file-based, read-only (works days later, no COM port —
design requirement). Features: A/B panes with shared viridis
histogram + auto-levels toggle; transport (space/arrows, 0.25–999×
speed); draggable A/B playheads (B-drag adjusts offset when locked);
clock-time timeline with narrative regions/events + raw-marker toggle;
10-row bracket lane with numbered color-coded rows and per-row hiding;
vertical splitter (default proportions on launch/maximize); title-bar
timeline stamp; exports (GSF with real nm axes / float32 TIFF /
as-displayed PNG / GIF A→B with fps prompt).

- **Conditional:** GSF physical axes require sidecar `scan_size_nm`
  (else exported with an explicit "axes not physical" warning). GIF/PNG
  reflect *current* levels — uncheck auto-levels for fixed-scale clips.
- **Impossible:** editing or writing instrument data from the player —
  it opens everything read-only by design.

## 5. Timeline convention (`TIMELINE.json` + `/timeline` skill + linter)

- **Guaranteed:** per-day narrative document — `regions` (session,
  scanning, stability, raw, approach, legacy), `events` (note, setting,
  milestone, crash + `important` flag), `brackets` (levels 0–9:
  state / phases / incidents / data-quality / uptime / px eras /
  verdicts / sub-experiments / raw coverage / setup). Deterministic
  draft first (`--draft`, nothing lost), then an LLM pass writes the
  narrative. **Human-note content is never compressed** (scope words,
  mechanisms, quantities survive; labels to 120 chars) and
  retrospective claims get honest spans ("last ~15 runs" is counted
  back, not stamped). Lint gate: `timeline_doc.py <day> --check` must
  print `OK … PLAYER-LOAD OK` (schema, kinds, day-bounds, labels, and
  the player's own load path) before the skill is done. The Claude
  skill is the DEFAULT generator; `--promote` (draft copied verbatim,
  machine labels) is the secondary no-LLM fallback, upgraded in place
  whenever the skill next runs.
- **Conditional:** narrative quality is bounded by the journals — days
  before rich journaling get thinner stories. Rows with no supporting
  data are omitted (no padding).
- **Impossible:** facts not present in journals/notes — uncertainty is
  hedged in the label (e.g. "gold sample? (per 07-14)"), never invented.

## 6. Query & sharing

*(These tools live in `software/pc/qtpanda/replay/` — a standalone
module; the instrument GUI's Review Day button launches it as a separate
process.)*

- `daylog.py` — day inventory, `--at <instant>` (capture + journal
  context + reconstruction command), `--coverage` (percent + HOLEs per
  stream per port-open window).
- `make_bundle.py <days> [--zip]` — self-contained team bundle (scripts
  above, `data/<day>/` below, README/requirements/launcher). Verified:
  runs from inside the bundle with zero repo dependency. Deps: numpy,
  PySide6, pyqtgraph (+Pillow, tifffile for exports). Jul-16 bundle:
  735 MB, 124 MB zipped.

## 7. Known limitations / next candidates

- Single-instance player not enforced — stale windows possible (title
  stamp mitigates; auto-takeover offered, not yet approved).
- Level-6/7 brackets (verdict state, sub-experiments) were hand-derived
  for the exemplar days; the skill reproduces them from notes, but no
  deterministic extractor yet.
- No A−B difference pane, marker-type filter, or sweep-range
  stack/average button yet (all cheap once wanted).
- Player embedding as a qtpanda tab (same engine) deferred until the
  standalone has bench mileage.
- GIF renders on the GUI thread — a many-hundred-frame export briefly
  freezes the window (progress prints to console).
