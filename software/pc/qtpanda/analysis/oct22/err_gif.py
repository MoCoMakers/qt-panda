"""GIF of the error-trace channel, sweeps #12-#32, plus error-channel repeat metrics."""
import os, datetime as dt
os.environ["QT_QPA_PLATFORM"] = "offscreen"
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "morph_report.py"),
           encoding="utf-8").read().split("SW = [i for i")[0]
ns = {"__file__": os.path.abspath(__file__)}; exec(compile(src, "h", "exec"), ns)
np, D = ns["np"], ns["D"]
from PIL import Image, ImageDraw, ImageFont
from matplotlib import cm

RUNG = {12: "tip check KIGA 1.14", 13: "tip check KIGA 1.14", 14: "tip check KIGA 1.14"}
for i in range(15, 20): RUNG[i] = "KIGA 1.14"
for i in range(20, 25): RUNG[i] = "KIGA 2.3"
for i in range(25, 30): RUNG[i] = "KIGA 4.6"
for i in range(30, 33): RUNG[i] = "KIGA 9"

frames, err = [], {}
try:
    font = ImageFont.truetype("arialbd.ttf", 15); small = ImageFont.truetype("arial.ttf", 12)
except OSError:
    font = small = ImageFont.load_default()
for i in range(12, 33):
    img, idx, s = D.image(i, "e_trace")
    lines = s["lines"]
    if lines < 120:
        continue                      # tiny partial sweeps: mostly empty
    a = ns["fill_rows"](img); a = ns["rowlev"](a)
    if lines >= 250: err[i] = a
    lo, hi = np.percentile(a, [1, 99])
    rgb = (cm.inferno(np.clip((a - lo) / (hi - lo), 0, 1))[:, :, :3] * 255).astype(np.uint8)
    im = Image.fromarray(rgb).resize((512, 512), Image.NEAREST)
    canvas = Image.new("RGB", (512, 560), (20, 20, 24)); canvas.paste(im, (0, 48))
    d = ImageDraw.Draw(canvas)
    arrow = "up (Y+)" if s["dir"] == "up" else "down (Y-)"
    t = dt.datetime.fromtimestamp(s["t_start"]).strftime("%H:%M:%S")
    d.text((8, 4), f"#{i}  {arrow}  {RUNG[i]}", fill=(255, 255, 255), font=font)
    d.text((8, 25), f"{t}  error trace, rows levelled  30 nm  " + ("" if lines >= 250 else f"PARTIAL {lines}/256"),
           fill=(190, 190, 190), font=small)
    frames.append(canvas)

out = "C:/Users/enact/Projects/qt-panda/TeamUpdate/data/2026-Oct-22/err_trace_12-32.gif"
frames[0].save(out, save_all=True, append_images=frames[1:], duration=700, loop=0)
print(out, len(frames), "frames")

# error-channel repeat, same direction, after alignment
for dname in ("up", "down"):
    seq = [i for i in sorted(err) if D.sweeps[i][2]["dir"] == dname]
    for a, b in zip(seq, seq[1:]):
        dy, dx, pk = ns["phase_shift"](err[a], err[b])
        print(f"{dname:4} #{a}->#{b} shift dx {dx:+6.1f} dy {dy:+6.1f}  peak {pk:5.1f}  "
              f"raw corr {ns['corr'](err[a], err[b]):+.2f}  aligned {ns['overlap_corr'](err[a], err[b], dy, dx):+.2f}")
