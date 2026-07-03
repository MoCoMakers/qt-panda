"""Synthesize a single self-contained ``report.html`` from an Investigation.

Design choices:
* PNG figures are embedded as base64 so the file is portable -- copy it
  anywhere, open offline, no broken relative paths.
* No external CDNs/fonts/JS -> it renders identically with no network.
* Equations are rendered as styled Unicode HTML (not LaTeX) to stay offline.
"""

from __future__ import annotations

import base64
import datetime as _dt
import html
from pathlib import Path

from models import Investigation


def _img_data_uri(path: Path) -> str:
    data = base64.b64encode(Path(path).read_bytes()).decode("ascii")
    return f"data:image/png;base64,{data}"


_CSS = """
:root{
  --bg:#0f1419; --panel:#ffffff; --ink:#1b1f24; --muted:#5b6670;
  --accent:#0072B2; --accent2:#D55E00; --line:#e3e7eb; --code:#f4f6f8;
}
*{box-sizing:border-box}
body{margin:0;background:#eef1f4;color:var(--ink);
  font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:960px;margin:0 auto;padding:32px 20px 80px}
header.hero{background:linear-gradient(135deg,#0f1419,#1f3a4d);color:#fff;
  border-radius:16px;padding:34px 34px 30px;box-shadow:0 10px 30px rgba(15,20,25,.25)}
header.hero .kicker{text-transform:uppercase;letter-spacing:.14em;font-size:12px;
  color:#7fd1ff;margin:0 0 10px}
header.hero h1{margin:0 0 12px;font-size:30px;line-height:1.2}
header.hero .q{font-size:17px;color:#d7e3ec;font-style:italic;
  border-left:3px solid #7fd1ff;padding-left:14px;margin:14px 0 0}
.meta{margin-top:18px;font-size:13px;color:#9fb3c1}
section{background:var(--panel);border:1px solid var(--line);border-radius:14px;
  padding:26px 30px;margin:22px 0;box-shadow:0 2px 8px rgba(15,20,25,.05)}
h2{font-size:21px;margin:0 0 16px;padding-bottom:10px;border-bottom:2px solid var(--line)}
h3{font-size:16px;color:var(--muted);margin:22px 0 8px;text-transform:uppercase;letter-spacing:.04em}
.answer{font-size:18px;line-height:1.7}
.findings{list-style:none;padding:0;margin:0}
.findings li{padding:10px 0 10px 30px;position:relative;border-bottom:1px dashed var(--line)}
.findings li:last-child{border-bottom:0}
.findings li:before{content:"\\2192";position:absolute;left:4px;color:var(--accent);font-weight:700}
.eq{background:var(--code);border-left:4px solid var(--accent);border-radius:6px;
  padding:12px 16px;margin:10px 0;font-family:"Cambria Math","Times New Roman",Georgia,serif;
  font-size:18px}
.eq .desc{display:block;font-family:inherit;font-size:13px;color:var(--muted);margin-top:6px}
figure{margin:24px 0;text-align:center}
figure img{max-width:100%;height:auto;border:1px solid var(--line);border-radius:10px;
  box-shadow:0 4px 14px rgba(15,20,25,.10)}
figcaption{font-size:13.5px;color:var(--muted);margin-top:10px}
pre{background:#0f1419;color:#d7e3ec;border-radius:10px;padding:16px 18px;overflow:auto;
  font:13px/1.5 "SFMono-Regular",Consolas,"Liberation Mono",monospace}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:20px}
@media(max-width:760px){.grid2{grid-template-columns:1fr}}
ul.plain{margin:0;padding-left:20px}
ul.plain li{margin:6px 0}
footer{color:var(--muted);font-size:12.5px;text-align:center;margin-top:30px}
.badge{display:inline-block;background:#e7f3fb;color:var(--accent);border:1px solid #bfe0f5;
  border-radius:999px;padding:3px 11px;font-size:12px;margin-right:6px;font-weight:600}
table.params{border-collapse:collapse;font-size:14px}
table.params td{padding:4px 14px 4px 0;color:var(--muted)}
table.params td b{color:var(--ink)}
"""


def build_report(inv: Investigation, out_path: Path) -> Path:
    ts = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    esc = html.escape

    # params chips
    param_rows = "".join(
        f"<tr><td>{esc(str(k))}</td><td><b>{esc(str(v))}</b></td></tr>"
        for k, v in inv.params.items()
    )

    findings = "".join(f"<li>{f}</li>" for f in inv.findings)

    equations = "".join(
        f'<div class="eq">{eq}<span class="desc">{esc(desc)}</span></div>'
        for eq, desc in inv.equations
    )

    figures = ""
    for fig in inv.figures:
        uri = _img_data_uri(fig["path"])
        figures += (
            f'<figure><img alt="{esc(fig["caption"])}" src="{uri}">'
            f'<figcaption><b>Fig.</b> {esc(fig["caption"])}</figcaption></figure>'
        )

    ascii_blocks = ""
    for title, body in inv.ascii_blocks:
        ascii_blocks += f"<h3>{esc(title)}</h3><pre>{esc(body)}</pre>"

    assumptions = "".join(f"<li>{esc(a)}</li>" for a in inv.assumptions)
    references = "".join(f"<li>{esc(r)}</li>" for r in inv.references)

    doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(inv.title)}</title>
<style>{_CSS}</style></head>
<body><div class="wrap">
<header class="hero">
  <p class="kicker">qt-panda research harness</p>
  <h1>{esc(inv.title)}</h1>
  <p class="q">&ldquo;{esc(inv.question)}&rdquo;</p>
  <p class="meta">Generated {ts} &middot; grounded in closed-form physics, computed with NumPy, rendered with Matplotlib</p>
</header>

<section>
  <h2>Answer</h2>
  <p class="answer">{inv.summary}</p>
  <h3>Key findings</h3>
  <ul class="findings">{findings}</ul>
</section>

<section>
  <h2>The physics</h2>
  {equations}
  <h3>Parameters</h3>
  <table class="params">{param_rows}</table>
  <h3>Assumptions &amp; scope</h3>
  <ul class="plain">{assumptions}</ul>
</section>

<section>
  <h2>Figures</h2>
  {figures}
</section>

<section>
  <h2>Numbers &amp; schematic</h2>
  {ascii_blocks}
</section>

<section>
  <h2>References &amp; model basis</h2>
  <ul class="plain">{references}</ul>
</section>

<footer>
  Static report &mdash; reload this file any time to view the latest run.
  Self-contained (images embedded); no network required.
</footer>
</div></body></html>"""

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(doc, encoding="utf-8")
    return out_path
