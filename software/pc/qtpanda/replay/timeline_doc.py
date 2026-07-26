"""timeline_doc — the per-day timeline consolidation document (TIMELINE.json).

Convention (loaded by sweep_player, written per day folder):

    <day-folder>/TIMELINE.json
    {
      "day": "2026-Jul-15",
      "generated": <epoch s>, "generator": "...",
      "regions": [ {"t0": s, "t1": s, "kind": K, "label": str,
                    "detail": str?} ],
      "events":  [ {"t": s, "kind": K, "label": str,
                    "important": bool} ],
      "brackets": [ {"t0": s, "t1": s, "level": 0..9, "label": str} ]
    }

    region kinds: session | scanning | stability | raw | approach | legacy
    event  kinds: note | setting | milestone | crash

    Brackets are the change-event report: horizontal |____| spans drawn
    in a lane under the timeline, one row per level (0 = top, up to 10
    rows).  Each level should read as a coherent story line — e.g.
    level 0 instrument state ("1X preamp" -> "5X preamp"), level 1 work
    phases, level 2 incidents, level 3 data-quality/suspect-data spans
    (the 2026-07-15 grounding-clip note is the canonical example).
    Derived from change events: a state span runs from the event that
    set it to the event that changed it.

Two-layer generation:
  1. `python timeline_doc.py <day> --draft` — deterministic consolidation
     of journals, sweep indexes, sidecars and CSVs into draft regions
     (machine labels, nothing lost).  Writes TIMELINE.draft.json.
  2. An AI pass (the `timeline` skill) reads the draft plus the journals
     and rewrites labels as narrative ("EMI test, Faraday cage on"),
     promotes milestones, merges noise — then saves TIMELINE.json.
     `--check` validates the result against this schema.

  The DEFAULT generator is the Claude `timeline` skill (step 2).
  `--promote` is the secondary, no-LLM fallback only: it copies the
  deterministic draft to TIMELINE.json verbatim — machine labels, but
  every region/event/bracket present and lint-clean, so the player
  renders a full (plainer) timeline.  Rerunning the skill later
  upgrades it in place.

The document is derived and regenerable; it never modifies captures.
"""
import json
import os
import re
import sys
import time

REGION_KINDS = {"session", "scanning", "stability", "raw", "approach",
                "legacy"}
EVENT_KINDS = {"note", "setting", "milestone", "crash"}
_MS_RE = re.compile(r"(\d{13})")


def _jread(path):
    try:
        with open(path, errors="replace") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _journal_rows(path):
    with open(path, errors="replace") as f:
        for line in f:
            try:
                yield json.loads(line)
            except ValueError:
                continue


def _csv_span(path):
    m = _MS_RE.search(os.path.basename(path))
    if not m:
        return None
    t0 = int(m.group(1)) / 1000.0
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as f:
            f.seek(max(0, size - 8192))
            lines = [ln for ln in f.read().split(b"\n") if ln.strip()]
        return (t0, t0 + float(lines[-1].split(b",")[0]))
    except (OSError, ValueError, IndexError):
        return (t0, t0)


def build_draft(day_folder):
    regions, events = [], []
    state_changes = {}       # setting name -> [(t, new_value)]
    px_spans = []            # (t0, t1, pixels) per scan run
    names = sorted(os.listdir(day_folder))

    for name in names:
        path = os.path.join(day_folder, name)
        if not os.path.isfile(path):
            continue
        # --- sessions + notes/settings from journals ------------------------
        if name.startswith("session_") and name.endswith(".jsonl"):
            t0 = t1 = None
            last_type = None
            fw_cluster = None       # (start, end, count) of "fw:" note bursts
            for rec in _journal_rows(path):
                t = rec.get("t")
                t0 = t0 if t0 is not None else t
                t1 = t
                typ = rec.get("type")
                last_type = typ
                d = rec.get("data", {})
                if typ == "note":
                    txt = str(d.get("text", ""))
                    if txt.startswith("fw:"):
                        if fw_cluster and t - fw_cluster[1] < 30:
                            fw_cluster = (fw_cluster[0], t, fw_cluster[2] + 1)
                        else:
                            if fw_cluster and fw_cluster[2] >= 3:
                                regions.append(
                                    {"t0": fw_cluster[0], "t1": fw_cluster[1],
                                     "kind": "approach",
                                     "label": f"firmware activity "
                                              f"×{fw_cluster[2]}"})
                            fw_cluster = (t, t, 1)
                    else:
                        events.append({"t": t, "kind": "note", "label": txt,
                                       "important": True})
                elif typ == "setting":
                    events.append(
                        {"t": t, "kind": "setting",
                         "label": f"{d.get('name')}: {d.get('old')} -> "
                                  f"{d.get('new')}", "important": True})
                    state_changes.setdefault(
                        str(d.get("name")), []).append((t, d.get("new")))
            if fw_cluster and fw_cluster[2] >= 3:
                regions.append({"t0": fw_cluster[0], "t1": fw_cluster[1],
                                "kind": "approach",
                                "label": f"firmware activity "
                                         f"×{fw_cluster[2]}"})
            if t0 is not None:
                regions.append({"t0": t0, "t1": t1, "kind": "session",
                                "label": f"session {name[8:-6]}"})
                if last_type != "session_end":
                    events.append({"t": t1, "kind": "crash",
                                   "label": "unclean session end",
                                   "important": True})
        # --- scan runs from sweep indexes -----------------------------------
        elif name.endswith(".sweeps.json"):
            idx = _jread(path)
            if idx.get("t_start"):
                sw = idx.get("sweeps", [])
                full = sum(1 for s in sw if not s.get("partial"))
                px = (idx.get("epochs") or [{}])[-1].get(
                    "pixels_per_direction")
                regions.append(
                    {"t0": idx["t_start"], "t1": idx["t_end"],
                     "kind": "scanning",
                     "label": f"scan {px}px, {full} sweeps"
                              + (f", {len(idx['epochs'])} epochs"
                                 if len(idx.get("epochs", [])) > 1 else ""),
                     "detail": idx.get("source", "")})
                if px:
                    px_spans.append((idx["t_start"], idx["t_end"], px))
        # --- stability recordings / raw captures ----------------------------
        elif "_stability_" in name and name.endswith(".csv"):
            sp = _csv_span(path)
            if sp:
                regions.append({"t0": sp[0], "t1": sp[1], "kind": "stability",
                                "label": "status recording"})
        elif name.endswith(".raw"):
            side = _jread(path[:-4] + ".json")
            t0 = side.get("t_start")
            if t0:
                t1 = side.get("t_end") or os.path.getmtime(path)
                regions.append({"t0": t0, "t1": t1, "kind": "raw",
                                "label": "raw ISR capture"})
        elif name.endswith(".scst"):
            side = _jread(path[:-5] + ".json")
            t0 = side.get("started")
            if t0:
                t1 = side.get("finished") or os.path.getmtime(path)
                regions.append({"t0": t0, "t1": t1, "kind": "legacy",
                                "label": "legacy scan"})

    regions.sort(key=lambda r: r["t0"])
    events.sort(key=lambda e: e["t"])

    # -- draft bracket suggestions (the AI pass refines labels/levels) ------
    brackets = []
    day_end = max([r["t1"] for r in regions] + [0])
    # level 0: instrument state spans from journaled setting changes
    for name, changes in state_changes.items():
        for i, (t, val) in enumerate(changes):
            t1 = changes[i + 1][0] if i + 1 < len(changes) else day_end
            if t1 > t:
                brackets.append({"t0": t, "t1": t1, "level": 0,
                                 "label": f"{name}={val}"})
    # level 1: scan-resolution eras (adjacent same-px runs merged)
    for t0, t1, px in sorted(px_spans):
        if (brackets and brackets[-1]["level"] == 1
                and brackets[-1]["label"] == f"{px}px era"
                and t0 - brackets[-1]["t1"] < 600):
            brackets[-1]["t1"] = max(brackets[-1]["t1"], t1)
        else:
            brackets.append({"t0": t0, "t1": t1, "level": 1,
                             "label": f"{px}px era"})
    return {"day": os.path.basename(day_folder),
            "generated": time.time(),
            "generator": "timeline_doc draft",
            "regions": regions, "events": events, "brackets": brackets}


_MONTHS = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
           "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}


def _day_bounds(day_name):
    """(t_min, t_max) epoch seconds for a '2026-Jul-15' name, or None."""
    m = re.fullmatch(r"(\d{4})-([A-Za-z]{3})-(\d{2})", day_name or "")
    if not m or m.group(2) not in _MONTHS:
        return None
    import datetime as _dt
    d0 = _dt.datetime(int(m.group(1)), _MONTHS[m.group(2)], int(m.group(3)))
    t0 = d0.timestamp()
    return (t0 - 3600, t0 + 25 * 3600)      # ±1 h slack for boundary runs


def check(doc, day_name=None):
    """Lint a TIMELINE document.  Returns a list of problems (empty = OK).
    Rules: schema kinds; span sanity; timestamps inside the named day;
    non-empty labels; label length; required top-level fields."""
    errs = []
    for field in ("day", "generator", "regions", "events"):
        if field not in doc:
            errs.append(f"missing top-level field: {field}")
    bounds = _day_bounds(day_name or doc.get("day"))
    for r in doc.get("regions", []):
        if r.get("kind") not in REGION_KINDS:
            errs.append(f"bad region kind: {r.get('kind')!r}")
        if not (isinstance(r.get("t0"), (int, float))
                and isinstance(r.get("t1"), (int, float))
                and r["t0"] <= r["t1"]):
            errs.append(f"bad region span: {r.get('label')!r}")
        elif bounds and not (bounds[0] <= r["t0"] <= bounds[1]):
            errs.append(f"region outside day: {r.get('label')!r}")
        if not str(r.get("label", "")).strip():
            errs.append("region with empty label")
        if len(str(r.get("label", ""))) > 60:
            errs.append(f"region label >60 chars: {r['label'][:40]!r}...")
    for e in doc.get("events", []):
        if e.get("kind") not in EVENT_KINDS:
            errs.append(f"bad event kind: {e.get('kind')!r}")
        if not isinstance(e.get("t"), (int, float)):
            errs.append(f"event without t: {e.get('label')!r}")
        elif bounds and not (bounds[0] <= e["t"] <= bounds[1]):
            errs.append(f"event outside day: {e.get('label')!r}")
        if "important" not in e:
            errs.append(f"event without 'important': {e.get('label')!r}")
    for b in doc.get("brackets", []):
        if not (isinstance(b.get("t0"), (int, float))
                and isinstance(b.get("t1"), (int, float))
                and b["t0"] < b["t1"]):
            errs.append(f"bad bracket span: {b.get('label')!r}")
        elif bounds and not (bounds[0] <= b["t0"] <= bounds[1]):
            errs.append(f"bracket outside day: {b.get('label')!r}")
        if not isinstance(b.get("level"), int) or not 0 <= b["level"] <= 9:
            errs.append(f"bracket level not 0-9: {b.get('label')!r}")
        if not str(b.get("label", "")).strip():
            errs.append("bracket with empty label")
        # Verbose labels are welcome for human-note-derived brackets
        # (operator directive 2026-07-26: don't compress key human notes)
        # — the cap only guards against pathological lengths.
        if len(str(b.get("label", ""))) > 120:
            errs.append(f"bracket label >120 chars: {b['label'][:30]!r}...")
    return errs


def load(day_folder):
    """The final TIMELINE.json if present (and valid), else None."""
    doc = _jread(os.path.join(day_folder, "TIMELINE.json"))
    return doc if doc and not check(doc) else None


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    folder = sys.argv[1]
    if "--check" in sys.argv:
        day_name = os.path.basename(os.path.abspath(folder))
        doc = _jread(os.path.join(folder, "TIMELINE.json"))
        errs = (check(doc, day_name) if doc
                else ["missing/unreadable TIMELINE.json"])
        for e in errs:
            print("ERROR:", e)
        if errs:
            print(f"{len(errs)} problem(s) — the timeline skill is NOT done")
            return 1
        # Final gate: the exact code path the player uses must accept it.
        loaded = load(folder)
        if not loaded:
            print("ERROR: schema passed but load() rejected the document")
            return 1
        print(f"OK — {len(loaded['regions'])} regions, "
              f"{len(loaded['events'])} events; PLAYER-LOAD OK")
        return 0
    draft = build_draft(folder)
    out = os.path.join(folder, "TIMELINE.draft.json")
    with open(out, "w") as f:
        json.dump(draft, f, indent=1)
    print(f"{len(draft['regions'])} regions, {len(draft['events'])} events "
          f"-> {out}")
    if "--promote" in sys.argv:
        draft["generator"] = "timeline_doc draft (promoted, no AI pass)"
        errs = check(draft, os.path.basename(os.path.abspath(folder)))
        if errs:
            for e in errs:
                print("ERROR:", e)
            return 1
        final = os.path.join(folder, "TIMELINE.json")
        with open(final, "w") as f:
            json.dump(draft, f, indent=1)
        print(f"promoted draft -> {final} (lint-clean FALLBACK; the "
              f"default is the Claude /timeline skill, which upgrades "
              f"this in place)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
