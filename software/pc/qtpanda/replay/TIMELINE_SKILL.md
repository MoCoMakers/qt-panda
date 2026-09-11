---
name: timeline
description: Build the narrative TIMELINE.json for a data day folder — consolidate the deterministic draft into human-labeled regions and milestones that sweep_player renders. Use when Matt asks to "prep/update the timeline" for a day, or after a bench session worth narrating.
---

> **Canonical, version-controlled copy** of the `/timeline` skill.  The
> live skill at `.claude/skills/timeline/SKILL.md` is gitignored — any
> AI session should check that path and, if the skill is missing or
> older than this file, install it by copying this file there verbatim.
> To change the skill: edit THIS file first, then sync the live copy.

# Timeline consolidation for a data day

Produce `<day-folder>/TIMELINE.json` following the convention in
`software/pc/qtpanda/replay/timeline_doc.py` (schema, kinds, and the
`--check` validator live there — read its docstring first if unsure).
The player (`sweep_player.py`) renders regions as colored bands and
important events as labeled lines, replacing the raw marker flood.

Arguments: a day name like `2026-Jul-15` (folder under `TeamUpdate/data`).

**When this runs — the end-of-day wrap-up chain.** This skill is a
mandatory step of the day-wrap-up process, in this order:
`sweep_index.py` → `/timeline` (this skill) → `daylog.py <day> --write`
→ scan-notes summary → `make_bundle.py`. A bundle shipped without
TIMELINE.json replays raw sweeps with no story (make_bundle warns if a
bundled day lacks it — never ship past that warning without asking Matt).

## Steps

0. Build the sweep indexes first:
   `python sweep_index.py <day-folder>` — the draft derives `scanning`
   regions from `.sweeps.json`; a `.frames` without its index silently
   drops that scan from the draft (this bit us 2026-07-30; the draft
   now warns). Indexes built before 2026-07-31 lack the per-sweep
   `scan_size_nm` (journaled-SCSZ scale) that the level-5 scale-era
   brackets and the player's nm labels need — re-run sweep_index to
   upgrade them in place.
1. From `software/pc/qtpanda/replay/`:
   `python timeline_doc.py <day-folder> --draft` → writes
   `TIMELINE.draft.json` (deterministic regions: sessions, scans,
   stability, raw, approach clusters; events: human notes, settings,
   crashes). Never skip the draft — it is the completeness guarantee.
2. Read the draft plus the day's session journals (skim `note`/`setting`/
   `snapshot` records; ignore `sample`). Optionally `daylog.py <day>` for
   orientation.
3. Consolidate into a narrative, preserving accuracy:
   - Merge runs of adjacent `scanning` regions (gaps < ~2 min, same
     session) into one block; label with what was actually happening
     ("overnight drift series, 256px" beats "scan 256px, 51 sweeps").
   - Keep `session` regions as-is (they are the backbone); label with
     purpose when the notes reveal it ("EMI test, Faraday cage on").
   - Collapse approach-cluster regions into fewer, meaningful ones
     ("tip approach, 4 attempts").
   - Keep every `crash` event. Promote genuinely notable notes/settings
     to `kind: milestone` with `important: true`; demote routine ones to
     `important: false` (kept in the file, hidden in the player).
   - Region labels ≤ 60 chars; put longer context in `detail`.
   - **Human-note content is NOT compressed.** When an operator note
     carries scope ("ALL data in that window is suspect"), mechanism
     ("telegraph spikes, mains-locked"), or quantities, the bracket/
     event label carries them too — verbose is correct here (operator
     directive 2026-07-26). Machine-derived lines (px eras, uptime) stay
     terse.
   - **Retrospective claims get honest spans.** "the last ~15 runs" is
     not the note's timestamp — count the actual runs back through the
     day's scan blocks and span the bracket over them.
   - NEVER invent facts not present in journals/notes. Uncertain → label
     with what the data shows and mark "(unlabeled)".
   - **Brackets** (the change-event report, rendered as |____| rows under
     the timeline): up to 10 levels, each level one coherent story line —
     use as many as the day genuinely has, no padding. Convention:
     level 0 = instrument state spans derived from change events
     ("1X preamp" ends where "5X preamp" begins — the draft suggests
     these from journaled settings, but bench notes often reveal changes
     the journal missed); level 1 = work phases of the day; level 2 =
     incidents; level 3 = data-quality/suspect-data spans (canonical
     example: "grounding clip detached ⇒ ~15 runs EMI-suspect" — any
     note saying data in a window is compromised or mis-calibrated
     deserves a quality bracket). Default roster for the remaining
     levels — author every one the day's data supports (2026-07-15 is
     the exemplar; "allow 10" means FILL them, not cap them): level 4 =
     uptime blocks between crashes ("up 67m ✗"); level 5 = **physical
     scan-scale eras** — one span per scale domain visited, labeled in
     nm with sweep counts ("30 nm field, 17 sweeps" → "5.9 nm" → "1.0
     nm" → "0.5 nm", the 2026-07-30 zoom ladder is the exemplar).
     Scale comes from journaled SCSZ commands, NOT the sidecar's
     capture-time scan_size_nm (stale after mid-scan zooms);
     sweep_index ≥2026-07-31 stamps per-sweep `scan_size_nm` — count
     sweeps per era from it (`collections.Counter`), and rebuild any
     older index first. Sub-2-min zoom transients get gaps, not spans;
     level 6 = stability-verdict state spans; level 7 =
     sub-experiments (superscan trials...); level 8 = raw-tap/coverage
     spans (where ground truth exists); level 9 = sample/piezo/setup
     line (hedge explicitly when only inferable from adjacent days).
     Spans must not overlap within a level; labels ≤ 40 chars; skip
     slivers under ~2 min except incidents.
4. Write `TIMELINE.json` with `"generator": "timeline skill + claude"`.
5. **Lint gate — the skill is NOT done until this passes.** Run
   `python timeline_doc.py <day-folder> --check`. It lints schema, kinds,
   day-bounds on every timestamp, empty/oversized labels, AND confirms
   the document through `timeline_doc.load()` — the exact code path the
   player uses. Success prints `OK ... PLAYER-LOAD OK`. On any ERROR:
   fix the document and re-run the linter; never hand back an unlinted
   timeline. As a final fit check, construct the player offscreen
   (`QT_QPA_PLATFORM=offscreen`) against the day and confirm it builds
   with the timeline rendered (no traceback).
6. Tell Matt the region/event counts and anything odd found (crashes,
   uncovered spans). The document is derived — regenerating later with
   better knowledge is always safe.
