"""Turn the single-file Oct 22 report into a publishable artifact folder (local copy kept in the
day folder): index.html (report + roadmap at the bottom), figs/*.png, live_trail.gif, mound.html,
and REPORT-TEXT.md (plain-text extract for future sessions)."""
import os, re, base64, html, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
DAY = "C:/Users/enact/Projects/qt-panda/TeamUpdate/data/2026-Oct-22"
OUT = os.path.join(DAY, "report"); os.makedirs(os.path.join(OUT, "figs"), exist_ok=True)
src = open(os.path.join(DAY, "MORPHOLOGY-2026-10-22.html"), encoding="utf-8").read()
road = open("C:/Users/enact/Projects/qt-panda/docs/test-plans/roadmap.html", encoding="utf-8").read()

# ---- figures out of data URIs
n = [0]; seen = {}
def ext_img(m):
    kind, b64 = m.group(1), m.group(2)
    data = base64.b64decode(b64); h = hashlib.md5(data).hexdigest()[:6]
    if h in seen: return seen[h]                       # same figure used twice: one file
    n[0] += 1
    name = seen[h] = f"figs/fig{n[0]:02d}_{h}.{kind}"
    open(os.path.join(OUT, name), "wb").write(data); return name
src = re.sub(r"data:image/(png|gif);base64,([A-Za-z0-9+/=]+)", ext_img, src)
# ---- 3D mound as its own file
m = re.search(r'<iframe title="Interactive 3D mound"([^>]*?)srcdoc="([^"]*)"></iframe>', src, re.S)
open(os.path.join(OUT, "mound.html"), "w", encoding="utf-8").write(html.unescape(m.group(2)))
src = src.replace(m.group(0), '<iframe title="Interactive 3D mound" src="mound.html" style="width:100%;height:860px;border:1px solid var(--line);border-radius:8px;background:var(--card)"></iframe>')

# ---- body content and CSS from the report
body = src.split("<main>", 1)[1].rsplit("</main>", 1)[0]
# ---- roadmap content (inside its <main>), its table script, its CSS (scoped under #roadmap)
rmain = road.split("<main>", 1)[1].split("</main>", 1)[0]
rmain = re.sub(r"<h1>.*?</h1>", "", rmain, count=1, flags=re.S)
rmain = rmain.replace("<h2>", "<h3>").replace("</h2>", "</h3>")
rmain = re.sub(r'<li><a href="[^"]*">([^<]*)</a></li>', r"<li>\1</li>", rmain)    # repo links don't work inside the artifact
rscript = road.split("</main>", 1)[1].split("<script>", 1)[1].split("</script>", 1)[0]

CSS = """
/* Layout: one reading column, figures full width, roadmap appended as the last section. */
:root{--bg:#f7f8f6;--fg:#1b2024;--mut:#59626a;--line:#d9ded9;--card:#ffffff;--acc:#a8501c;--hi:#e6f2e8;--warn:#9a5b12;
  --ff-body:"Source Sans 3",system-ui,"Segoe UI",sans-serif;--ff-mono:"JetBrains Mono",ui-monospace,Consolas,monospace}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#131619;--fg:#e6e8e6;--mut:#a2aaa6;--line:#30363a;--card:#1b1f22;--acc:#ef9f66;--hi:#1d3123;--warn:#e0a060;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#131619;--fg:#e6e8e6;--mut:#a2aaa6;--line:#30363a;--card:#1b1f22;--acc:#ef9f66;--hi:#1d3123;--warn:#e0a060;color-scheme:dark}
body{background:var(--bg);color:var(--fg);font:15px/1.6 var(--ff-body);
  padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
main{max-width:1100px;margin:0 auto;padding-block:28px 64px}
h1{font-size:28px;line-height:1.2;margin:0 0 6px;text-wrap:balance} h2{font-size:19px;margin:36px 0 10px;border-bottom:1px solid var(--line);padding-bottom:5px;text-wrap:balance}
h3{font-size:15.5px;margin:22px 0 8px}
.sub,.mut{color:var(--mut);font-size:13px} .card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:14px 16px;margin:12px 0;min-width:0}
.verdict{border-left:4px solid var(--acc)} .q{border-left:4px solid var(--warn)}
img{max-width:100%;height:auto;background:#fff;border-radius:4px} figure{margin:12px 0} figcaption{color:var(--mut);font-size:13px;margin-top:4px}
table{border-collapse:collapse;font-size:13.5px;width:100%;font-variant-numeric:tabular-nums} td,th{border-bottom:1px solid var(--line);padding:5px 7px;text-align:left;vertical-align:top}
.scroll{overflow-x:auto} code{font:12.5px var(--ff-mono)} a{color:var(--acc)}
.data{font-size:13px;color:var(--mut);margin:-2px 0 10px;padding:3px 8px;border-left:3px solid var(--acc)}
:focus-visible{outline:2px solid var(--acc);outline-offset:2px}
#roadmap{border-top:3px solid var(--acc);margin-top:48px;padding-top:6px}
#roadmap .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:10px}
#roadmap .g,#roadmap .m{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px 12px;min-width:0}
#roadmap .m{cursor:pointer} #roadmap .m.sel{outline:2px solid var(--acc)} #roadmap .cnt{font-size:12px;color:var(--acc);margin-top:4px}
#roadmap .bar{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:8px 0}
#roadmap select,#roadmap input{font:inherit;font-size:13px;padding:3px 6px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--fg)}
#roadmap th[data-k]{cursor:pointer;white-space:nowrap} #roadmap td.n{text-align:center}
#roadmap tr.top td{background:var(--hi)} #roadmap .pill{font-size:11.5px;border:1px solid var(--line);border-radius:10px;padding:0 6px;white-space:nowrap}
@media (prefers-reduced-motion:reduce){*{scroll-behavior:auto}}
"""
page = f"""<title>Oct 22 Morphology Report</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;600;700&family=JetBrains+Mono:wght@400&display=swap">
<style>{CSS}</style>
<main>
{body}
<section id="roadmap">
<h2>Roadmap: goals, milestones and next steps</h2>
{rmain}
</section>
</main>
<script>{rscript}</script>
"""
page = page.replace("<code>docs/test-plans/roadmap.html</code> (goals, milestones, every item scored, gap calculator)",
                    "the Roadmap section at the bottom of this page (goals, milestones, every item scored, gap calculator)")
open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(page)

# ---- plain-text extract for future sessions
t = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", page, flags=re.S)
t = re.sub(r"<h1[^>]*>", "\n# ", t); t = re.sub(r"<h2[^>]*>", "\n## ", t); t = re.sub(r"<h3[^>]*>", "\n### ", t)
t = re.sub(r"<tr[^>]*>", "\n| ", t); t = re.sub(r"</t[dh]>", " | ", t)
t = re.sub(r"<li[^>]*>", "\n- ", t); t = re.sub(r"<(p|div|figcaption|br)[^>]*>", "\n", t)
t = re.sub(r'<img[^>]*src="([^"]*)"[^>]*>', r"[figure: \1]", t)
t = html.unescape(re.sub(r"<[^>]+>", "", t)); t = re.sub(r"\n\s*\n\s*\n+", "\n\n", t)
open(os.path.join(OUT, "REPORT-TEXT.md"), "w", encoding="utf-8").write(
    "<!-- Plain-text extract of the published Oct 22 report (index.html in this folder). Regenerated by build_artifact.py. -->\n" + t)
tot = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(OUT) for f in fs)
print("index.html", os.path.getsize(os.path.join(OUT, "index.html")) // 1000, "kB | figures", n[0],
      "| mound.html", os.path.getsize(os.path.join(OUT, "mound.html")) // 1000, "kB | total", tot // 1000, "kB")
