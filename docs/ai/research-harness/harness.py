#!/usr/bin/env python
"""qt-panda research harness -- ask a physics question, get a grounded report.

Pipeline:
    question (query module)
      -> physics  (closed-form NumPy)
      -> figures  (Matplotlib) + ASCII schematics
      -> report.html (self-contained, reload any time)
      -> review manifest (for the agent-review loop; see review/CHECKLIST.md)

Usage:
    python harness.py                       # run the default reference query
    python harness.py --list                # list available queries
    python harness.py --query tip-displacement-length
    python harness.py --theta 2 --lengths 1 10
    python harness.py --ask "...1mm vs 10mm ... 2 degree offset"   # NL shortcut

The natural-language path is a light keyword matcher, not an LLM -- it just
routes the sentence to a registered query and pulls out numbers. The science
lives in the physics modules, so every answer stays reproducible.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from queries import REGISTRY  # noqa: E402
from rendering.report import build_report  # noqa: E402

OUTPUT_DIR = HERE / "output"


def parse_natural_language(text: str):
    """Very small heuristic router: text -> (slug, kwargs).

    Deliberately dumb and transparent. If it can't confidently match, it
    falls back to the reference query with any numbers it found.
    """
    t = text.lower()
    kwargs = {}

    # angle: "2 degree", "2 deg", "2°"
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:degree|deg|°)", t)
    if m:
        kwargs["theta_deg"] = float(m.group(1))

    # lengths: collect "N mm" tokens
    lengths = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s*mm", t)]
    if lengths:
        kwargs["lengths_mm"] = tuple(lengths)

    # temperature: "300 k", "293K", or "room temperature"
    mt = re.search(r"(\d+(?:\.\d+)?)\s*k\b", t)
    if mt:
        kwargs["temperature_K"] = float(mt.group(1))

    # route by keywords -- wedge/clamshell gearing first (it also mentions "piezo")
    if any(w in t for w in ("wedge", "clamshell", "hinge", "lever", "per step")):
        kwargs.pop("theta_deg", None)
        kwargs.pop("temperature_K", None)
        if "lengths_mm" in kwargs:
            kwargs = {"lengths_mm": kwargs["lengths_mm"]}
        return "wedge-lever-gearing", kwargs
    # thermal/brownian/gold-atom question next
    if any(w in t for w in ("brownian", "thermal", "vibrat", "atom", "gold")):
        kwargs.pop("theta_deg", None)
        kwargs.pop("lengths_mm", None)
        return "thermal-displacement-gold", kwargs
    if "tip" in t or "piezo" in t or "offset" in t:
        kwargs.pop("temperature_K", None)
        return "tip-displacement-length", kwargs
    return "tip-displacement-length", kwargs


def write_review_manifest(inv, out_dir: Path, report_path: Path) -> Path:
    """Emit a machine-readable manifest the agent-review loop consumes."""
    manifest = {
        "slug": inv.slug,
        "title": re.sub("<[^>]+>", "", inv.title),
        "question": inv.question,
        "report_html": str(report_path),
        "figures": [
            {"name": f["name"], "path": str(f["path"]), "caption": f["caption"]}
            for f in inv.figures
        ],
        "review_criteria": ["professionalism", "scientific_accuracy", "presentation"],
    }
    path = out_dir / "review_manifest.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return path


def build_index(reports: list[dict]) -> Path:
    """Write output/index.html linking every report that has been generated."""
    cards = ""
    for r in sorted(reports, key=lambda d: d["title"]):
        cards += (
            f'<a class="card" href="{r["slug"]}/report.html">'
            f'<h2>{r["title"]}</h2><p>{r["question"]}</p>'
            f'<span class="go">open report &rarr;</span></a>'
        )
    html_doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>qt-panda research harness — reports</title><style>
body{{margin:0;background:#eef1f4;font:16px/1.6 -apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#1b1f24}}
.wrap{{max-width:860px;margin:0 auto;padding:40px 20px 70px}}
h1{{font-size:26px}} .sub{{color:#5b6670;margin-top:-8px}}
.card{{display:block;background:#fff;border:1px solid #e3e7eb;border-radius:14px;
padding:22px 24px;margin:18px 0;text-decoration:none;color:inherit;
box-shadow:0 2px 8px rgba(15,20,25,.05);transition:transform .08s,box-shadow .08s}}
.card:hover{{transform:translateY(-2px);box-shadow:0 8px 22px rgba(15,20,25,.12)}}
.card h2{{margin:0 0 8px;font-size:19px;color:#0072B2}}
.card p{{margin:0 0 12px;color:#444;font-size:14.5px}}
.go{{color:#0072B2;font-weight:600;font-size:14px}}
footer{{color:#5b6670;font-size:12.5px;text-align:center;margin-top:30px}}
</style></head><body><div class="wrap">
<h1>qt-panda research harness</h1>
<p class="sub">Grounded physics &middot; computed with Python &middot; reload any time.</p>
{cards}
<footer>Static index — regenerate with <code>python harness.py</code>.</footer>
</div></body></html>"""
    path = OUTPUT_DIR / "index.html"
    path.write_text(html_doc, encoding="utf-8")
    return path


def refresh_index() -> Path:
    """Rebuild the index from whatever reports currently exist on disk."""
    found = []
    for mod in REGISTRY.values():
        slug = mod.SLUG
        rep = OUTPUT_DIR / slug / "report.html"
        man = OUTPUT_DIR / slug / "review_manifest.json"
        if rep.exists() and man.exists():
            meta = json.loads(man.read_text(encoding="utf-8"))
            found.append({"slug": slug, "title": meta["title"],
                          "question": meta["question"]})
    return build_index(found)


def run_query(slug: str, **kwargs):
    if slug not in REGISTRY:
        raise SystemExit(f"Unknown query '{slug}'. Use --list to see options.")
    mod = REGISTRY[slug]
    out_dir = OUTPUT_DIR / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    inv = mod.run(out_dir, **kwargs)

    report_path = build_report(inv, out_dir / "report.html")
    manifest_path = write_review_manifest(inv, out_dir, report_path)
    index_path = refresh_index()

    print(f"[harness] query   : {slug}")
    for k, v in kwargs.items():
        print(f"[harness]   {k} = {v}")
    print(f"[harness] figures : {len(inv.figures)} -> {out_dir/'figures'}")
    print(f"[harness] report  : {report_path}")
    print(f"[harness] manifest: {manifest_path}")
    print(f"[harness] index   : {index_path}")
    print("\n" + inv.table_text + "\n")
    print(f"Open in a browser:  file:///{report_path.as_posix()}")
    return inv


def main(argv=None):
    p = argparse.ArgumentParser(description="qt-panda physics research harness")
    p.add_argument("--list", action="store_true", help="list available queries")
    p.add_argument("--query", default="tip-displacement-length", help="query slug to run")
    p.add_argument("--ask", help="natural-language question (keyword routed)")
    p.add_argument("--theta", type=float, help="angular offset in degrees")
    p.add_argument("--lengths", type=float, nargs="+", help="tip lengths in mm")
    p.add_argument("--temperature", type=float, help="temperature in K (thermal query)")
    args = p.parse_args(argv)

    if args.list:
        print("Available queries:")
        for slug in REGISTRY:
            print(f"  - {slug}")
        return 0

    if args.ask:
        slug, kwargs = parse_natural_language(args.ask)
    else:
        slug, kwargs = args.query, {}

    if args.theta is not None:
        kwargs["theta_deg"] = args.theta
    if args.lengths:
        kwargs["lengths_mm"] = tuple(args.lengths)
    if args.temperature is not None:
        kwargs["temperature_K"] = args.temperature

    run_query(slug, **kwargs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
