"""Build the single Oct 22 report: run build_morph_html.py, then embed the interactive 3D
mound page as an iframe (srcdoc) at the <!--MOUND3D--> marker."""
import os, subprocess, sys, html
HERE = os.path.dirname(os.path.abspath(__file__))
REPORT = "C:/Users/enact/Projects/qt-panda/TeamUpdate/data/2026-Oct-22/MORPHOLOGY-2026-10-22.html"
subprocess.run([sys.executable, os.path.join(HERE, "build_morph_html.py")], check=True)
page = open(os.path.join(HERE, "mound_v4_template.html"), encoding="utf-8").read().replace(
    "__DATA__", open(os.path.join(HERE, "morph_report", "mound_v4.json"), encoding="utf-8").read())
frame = ('<iframe title="Interactive 3D mound" style="width:100%;height:860px;border:1px solid #ccc;border-radius:8px;background:#fff" '
         f'srcdoc="{html.escape(page, quote=True)}"></iframe>')
r = open(REPORT, encoding="utf-8").read()
assert r.count("<!--MOUND3D-->") == 1
import base64
gif = "data:image/gif;base64," + base64.b64encode(open(os.path.join(HERE, "morph_report", "live_trail2.gif"), "rb").read()).decode()
r = r.replace("<!--LIVETRAIL-->", f'<img src="{gif}" alt="Live drift trail beside the frame being registered" style="max-width:860px;width:100%">')
open(REPORT, "w", encoding="utf-8").write(r.replace("<!--MOUND3D-->", frame))
print(REPORT, os.path.getsize(REPORT) // 1000, "kB")
