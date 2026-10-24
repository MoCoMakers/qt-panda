"""Offscreen mockup of an 'Enable Stage Tracking' panel in the real GUI.
No serial port is opened (nothing is recorded or actuated); recorded Oct 22 lines are fed
into the live raster; the panel is added at runtime only; no source file is modified."""
import os, sys, json, io
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QT_QPA_FONTDIR"] = "C:/Windows/Fonts"
SHOW = os.environ.get("SHOW_FID", "0") == "1"
QT = "C:/Users/enact/Projects/qt-panda/software/pc/qtpanda"
HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(QT); sys.path.insert(0, QT + "/replay"); sys.path.insert(0, QT)
import numpy as np
from PySide6 import QtWidgets, QtGui, QtCore
import pyqtgraph as pg
app = QtWidgets.QApplication([])
import main as gui
import frame_logger, sweep_player as sp

w = gui.Widget(); w.resize(1840, 1120)
tabs = w.ui.tabWidget
for k in range(tabs.count()):
    if tabs.tabText(k) == "Continuous Scan": tabs.setCurrentIndex(k)
w._cs_pixels.setValue(512); w._cs_scansize.setValue(30.0)
w._cs_ki.setValue(3.067)
R = w._cs_raster; R.resize_buffers(256, 512)

# feed recorded lines of the KIGA 4.6 run up to the end of #28 (as the live view would have seen them)
D = sp.DayData("2026-Oct-22")
fp = D.sweeps[28][0]; t_end = D.sweeps[28][2]["t_end"]
for t, ln, z, e in frame_logger.read_frames(fp):
    if t > t_end: break
    R.update_line(int(ln), z, e)
R.auto_range()
QtWidgets.QApplication.processEvents()

# --- the mock panel: compact, beside a narrower log (bottom of the left column) ------------
box = QtWidgets.QGroupBox("Stage tracking")
box.setStyleSheet("QGroupBox{font-weight:bold;border:2px solid #2a9d4b;border-radius:5px;margin-top:7px;padding-top:4px}"
                  "QGroupBox::title{subcontrol-origin:margin;left:6px;padding:0 3px;color:#2a9d4b}")
box.setFixedWidth(222)
v = QtWidgets.QVBoxLayout(box); v.setContentsMargins(6, 4, 6, 4); v.setSpacing(2)
top = QtWidgets.QHBoxLayout(); chk = QtWidgets.QCheckBox("Enable"); chk.setChecked(True); chk.setStyleSheet("font-weight:bold")
mode = QtWidgets.QComboBox(); mode.addItems(["Monitor only", "Correct offset"]); mode.setCurrentIndex(1)
top.addWidget(chk); top.addWidget(mode); v.addLayout(top)
def line(txt, color=None, bold=True):
    l = QtWidgets.QLabel(txt); l.setStyleSheet(("font-weight:600;" if bold else "color:#555;") + (f"color:{color};" if color else "")); v.addWidget(l)
line("● LOCKED · 4/6 fiducials", "#1a7f37")
line("60 pm/s ↑ 87° · 22 updates")
line("offset X −0.4  Y −10.6 nm", bold=False)
line("up/down 0.7 nm · last hop 41 s", bold=False)
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
tr = json.load(open(os.path.join(HERE, "morph_report", "live_trail.json")))["updates"]
PX = 30 / 256; pos = np.zeros(2); vel = None; last = tr[0]["t"]; pts = []
for u in tr:
    if u["ok"]:
        vv = np.array([-u["dy"], u["dx"]]) / u["dt_ref"]; vel = vv if vel is None else 0.6 * vel + 0.4 * vv
    if vel is not None: pos = pos + vel * (u["t"] - last)
    last = u["t"]; pts.append((pos[1] * PX * -1, pos[0] * PX))
fig, ax = plt.subplots(figsize=(2.35, 1.75), dpi=90)
tail = pts[-9:]
for j in range(1, len(tail)):
    ax.annotate("", xy=tail[j], xytext=tail[j - 1], arrowprops=dict(arrowstyle="->", color="#1f77b4", alpha=0.2 + 0.8 * j / (len(tail) - 1), lw=1 + j * 0.15))
ax.plot(*tail[-1], "o", color="#e4572e", ms=8, mec="k")
cx, cy = tail[-1]; ax.set_xlim(cx - 3, cx + 3); ax.set_ylim(cy - 4.5, cy + 1.5); ax.set_aspect("equal")
ax.tick_params(labelsize=5, length=2); ax.set_title("frame drift (nm), last 8", fontsize=6.5, pad=2)
plt.tight_layout(pad=0.2); buf = io.BytesIO(); fig.savefig(buf, format="png"); plt.close(fig)
pm = QtGui.QPixmap(); pm.loadFromData(buf.getvalue()); lbl = QtWidgets.QLabel(); lbl.setPixmap(pm); v.addWidget(lbl)
btns = QtWidgets.QHBoxLayout(); btns.addWidget(QtWidgets.QPushButton("Re-prime")); btns.addWidget(QtWidgets.QPushButton("Pause")); v.addLayout(btns)
v.addStretch(1)
# swap the log for [narrower log | tracker]
vl = w.ui.verticalLayout_2; log = w.ui.txtLog; i_ = vl.indexOf(log); vl.removeWidget(log)
holder = QtWidgets.QWidget(); h = QtWidgets.QHBoxLayout(holder); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(6)
h.addWidget(log, 1); h.addWidget(box, 0); vl.insertWidget(i_, holder, 1)
for msg in ("OPEN ok  device=COM5", "Continuous scan: RUN (KIGA 3.067)", "[track] primed: 6 fiducials, reference #25-#26",
            "[track] locked: 60 pm/s up, 87 deg", "[track] hop: fiducial 3 -> 5 (left top edge)", "[track] offset Y -0.4 nm (feed-forward)"):
    log.append(msg)

# fiducial boxes on the live Err image (raster coords: col, row); taken from the tracker's #27->#28 match
fd = json.load(open(os.path.join(HERE, "morph_report", "fiducial_drift_2026-Oct-22_20-31.json")))
ref = [r for r in fd["reference"] if "y" in r and r["b"] == 28]
# orientation check: compare the raster's error buffer with the analysis image of #28
an = D.image(28, "e_trace")[0]; buf_e = R._e_trace
def cc(a, b):
    a = np.nan_to_num(a - np.nanmean(a)); b = np.nan_to_num(b - np.nanmean(b)); return float((a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum()))
flip = cc(buf_e[::-1], an) > cc(buf_e, an)
print("raster vs analysis orientation: flipped" if flip else "same orientation")
def to_raster(y): return 256 - y - 96 if flip else y
fid_items = []
for vb in (R._vb_et,):                                   # error trace only
    for r_ in ref:
        it = QtWidgets.QGraphicsRectItem(QtCore.QRectF(r_["nx"], to_raster(r_["ny"]), 96, 96))
        it.setPen(pg.mkPen("#39ff14", width=3)); vb.addItem(it); fid_items.append(it)
    for (x, y) in [(40, 30), (150, 40), (120, 120)]:
        it = QtWidgets.QGraphicsRectItem(QtCore.QRectF(x, to_raster(y), 96, 96)); it.setPen(pg.mkPen("#ffffff", width=1, style=QtCore.Qt.DashLine))
        vb.addItem(it); fid_items.append(it)
show_fid = QtWidgets.QCheckBox("Show fiducials"); show_fid.setChecked(SHOW)
for it in fid_items: it.setVisible(SHOW)
show_fid.toggled.connect(lambda on: [it.setVisible(on) for it in fid_items])
save_btn = next(b_ for b_ in R.findChildren(QtWidgets.QPushButton) if b_.text().startswith("Save frame"))
tb = save_btn.parentWidget().layout()
def find_layout(l, wdg):
    for k_ in range(l.count()):
        itm = l.itemAt(k_)
        if itm.widget() is wdg: return l, k_
        if itm.layout():
            r2 = find_layout(itm.layout(), wdg)
            if r2: return r2
    return None
lay_, pos_ = find_layout(tb, save_btn)
show_fid.setStyleSheet("color:#2a9d4b;font-weight:bold")
lay_.insertWidget(pos_, show_fid)

QtWidgets.QApplication.processEvents(); QtWidgets.QApplication.processEvents()
out = os.path.join(HERE, "morph_report", "mock_stage_tracking_v3{}.png".format("_fid_on" if SHOW else ""))
w.grab().save(out)
print(out)
