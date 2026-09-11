"""sweep_player — offline radio-style replay of a day's continuous scans.

Renders the output of the day-wrap-up chain — authoritative runbook:
TIMELINE_SKILL.md (this folder).  If the timeline looks empty/plain,
the /timeline skill hasn't run for that day yet.

Fully offline: reads only the day folder (.frames + .sweeps.json indexes +
session journals).  No hardware, no COM port — built to work days later.

    python sweep_player.py 2026-Jul-15            # a day (name or path)
    python sweep_player.py path\\to\\scan_x.frames  # a single run

Layout:
  * A/B panes side by side, each showing one completed sweep with its
    direction, completion timestamps, geometry, and session id.
  * Transport: play/pause (space), step (arrow keys / buttons), speed.
    Playback paces itself by the real gaps between sweep completions.
  * Timeline across the bottom: every sweep is a dot (up=above axis,
    down=below; partial sweeps orange), journal events are vertical lines
    (notes yellow, settings magenta, session boundaries white).  Click to
    seek A to the nearest sweep.
  * "B follows A" locks B at a sweep offset for side-by-side comparison;
    uncheck to park B anywhere (e.g. compare 19:07 against 20:31).
  * Shared display levels (2–98 percentile of A) so A/B compare honestly.
    Missing lines in partial sweeps render at the low level and the label
    says PARTIAL n/H.
"""
import os
import sys
import json
import time
from datetime import datetime

import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets
import pyqtgraph as pg

# replay/ tools import the instrument-side modules (data_paths,
# frame_logger, session_journal) from the qtpanda folder above; harmless
# in the flat team bundle where everything shares one folder.
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import data_paths
import frame_logger
import sweep_index
import timeline_doc

MARKER_COLORS = {"note": (240, 220, 60), "setting": (220, 80, 220),
                 "session_start": (255, 255, 255),
                 "session_end": (255, 255, 255), "record": (130, 130, 130)}
# TIMELINE.json narrative rendering: region bands and important events.
REGION_BRUSH = {"session":   (255, 255, 255, 18),
                "scanning":  (70, 140, 255, 60),
                "stability": (60, 200, 120, 45),
                "raw":       (170, 110, 255, 45),
                "approach":  (255, 90, 90, 60),
                "legacy":    (255, 200, 60, 55)}
EVENT_PENS = {"note": (240, 220, 60), "setting": (220, 80, 220),
              "milestone": (90, 255, 90), "crash": (255, 60, 60)}
CHANNELS = ["e_trace", "e_retrace", "z_trace", "z_retrace"]


def _fmt(ts):
    return datetime.fromtimestamp(ts).strftime("%H:%M:%S")


class DayData:
    """All sweeps of a day (or one file), lazily loading frame records."""

    def __init__(self, target, height=None):
        if target.endswith(".frames"):
            self.folder = os.path.dirname(os.path.abspath(target))
            files = [os.path.abspath(target)]
        else:
            self.folder = (target if os.path.isdir(target)
                           else os.path.join(data_paths.DATA_ROOT, target))
            files = sorted(os.path.join(self.folder, n)
                           for n in os.listdir(self.folder)
                           if n.endswith(".frames"))
        self._records = {}
        self.sweeps = []          # (frames_path, index_meta, sweep_dict)
        for fp in files:
            idx = sweep_index.load_or_build(fp, height)
            for s in idx["sweeps"]:
                self.sweeps.append((fp, idx, s))
        self.sweeps.sort(key=lambda x: x[2]["t_start"])
        self.markers = self._load_markers()
        self.timeline = timeline_doc.load(self.folder)   # None if absent

    def _load_markers(self):
        out = []
        try:
            names = os.listdir(self.folder)
        except OSError:
            return out
        for name in sorted(names):
            if not (name.startswith("session_") and name.endswith(".jsonl")):
                continue
            with open(os.path.join(self.folder, name), errors="replace") as f:
                for line in f:
                    try:
                        rec = json.loads(line)
                    except ValueError:
                        continue
                    typ = rec.get("type")
                    if typ in MARKER_COLORS:
                        d = rec.get("data", {})
                        txt = (d.get("text") or d.get("name")
                               or d.get("event") or typ)
                        out.append((rec.get("t", 0), typ, str(txt)))
        return out

    def records(self, fp):
        if fp not in self._records:
            self._records[fp] = sweep_index.load_frames(fp)
        return self._records[fp]

    def image(self, i, channel):
        fp, idx, s = self.sweeps[i]
        H = idx["image_height"]
        half = next(e["pixels_per_direction"] for e in idx["epochs"]
                    if e["epoch"] == s["epoch"])
        return sweep_index.sweep_image(self.records(fp), s, H, half or 1,
                                       channel), idx, s

    def label(self, i):
        fp, idx, s = self.sweeps[i]
        arrow = "▲" if s["dir"] == "up" else "▼"
        part = ("" if not s["partial"]
                else f"  PARTIAL {s['lines']}/{idx['image_height']}")
        sid = f"  s{idx['session']}" if idx.get("session") else ""
        # Physical scale: per-sweep (journaled SCSZ, follows mid-scan
        # zooms — sweep_index stamps it), falling back to the sidecar's
        # capture-time value for indexes built before 2026-07-31.
        size_nm = (s.get("scan_size_nm")
                   or (idx.get("settings") or {}).get("scan_size_nm"))
        if size_nm:
            half = next((e["pixels_per_direction"] for e in idx["epochs"]
                         if e["epoch"] == s["epoch"]), None) or 1
            nm = (f"  ·  ~{float(size_nm):g} nm across "
                  f"({float(size_nm) / half:.3f} nm/px)")
        else:
            nm = "  ·  scan size unknown"
        return (f"#{i}  {arrow}  {_fmt(s['t_start'])}–{_fmt(s['t_end'])}"
                f"{nm}{part}{sid}  [{os.path.basename(fp)}]")


class Player(QtWidgets.QWidget):
    def __init__(self, data):
        super().__init__()
        self.data = data
        self.a = 0
        self.b = min(1, len(data.sweeps) - 1)
        self._bks = (data.timeline or {}).get("brackets", [])
        self._hidden_levels = set()
        gen = (data.timeline or {}).get("generated")
        stamp = (time.strftime(" · timeline %H:%M:%S", time.localtime(gen))
                 if gen else " · no timeline doc")
        self.setWindowTitle(f"sweep player — {os.path.basename(data.folder)} "
                            f"({len(data.sweeps)} sweeps){stamp}")
        root = QtWidgets.QVBoxLayout(self)
        # Vertical splitter: images above, transport/timeline/brackets
        # below.  Launch and maximize keep the classic proportions (via
        # setSizes + stretch factors); dragging the divider gives the
        # image panes any size — the bottom area shrinks to make room.
        self._split = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        root.addWidget(self._split)

        # -- A/B panes -------------------------------------------------------
        glw = pg.GraphicsLayoutWidget()
        self.img_a, self.img_b = pg.ImageItem(), pg.ImageItem()
        self.lbl_a = glw.addLabel("", col=0)
        self.lbl_b = glw.addLabel("", col=1)
        glw.nextRow()
        for col, item in ((0, self.img_a), (1, self.img_b)):
            vb = glw.addViewBox(col=col, lockAspect=True, invertY=True)
            vb.addItem(item)
        # Histogram + LUT to the right of the rasters — same viridis and
        # auto-adjust behaviour as the live continuous-scan view.  It
        # drives A; levels/LUT mirror onto B so A/B stay comparable.
        self.hist = pg.HistogramLUTItem()
        self.hist.setImageItem(self.img_a)
        self.hist.gradient.loadPreset("viridis")
        self.hist.sigLevelsChanged.connect(self._sync_b_lut)
        self.hist.gradient.sigGradientChanged.connect(self._sync_b_lut)
        glw.addItem(self.hist, col=2)
        self._split.addWidget(glw)
        bottom = QtWidgets.QWidget()
        self._bottom = QtWidgets.QVBoxLayout(bottom)
        self._bottom.setContentsMargins(0, 0, 0, 0)
        self._split.addWidget(bottom)
        self._split.setStretchFactor(0, 5)   # extra space -> images
        self._split.setStretchFactor(1, 1)
        self._split.setCollapsible(0, False)

        # -- transport -------------------------------------------------------
        bar = QtWidgets.QHBoxLayout()
        self.btn_prev = QtWidgets.QPushButton("◀")
        self.btn_play = QtWidgets.QPushButton("▶ play")
        self.btn_next = QtWidgets.QPushButton("▶|")
        for b in (self.btn_prev, self.btn_play, self.btn_next):
            b.setMaximumWidth(70)
            bar.addWidget(b)
        bar.addWidget(QtWidgets.QLabel("speed"))
        self.spin_speed = QtWidgets.QDoubleSpinBox()
        self.spin_speed.setRange(0.25, 999.0)
        self.spin_speed.setDecimals(1)
        # Adaptive steps (1→2→5→10→20...) so reaching high speed is a few
        # clicks, and the field accepts any typed value directly.
        self.spin_speed.setStepType(
            QtWidgets.QAbstractSpinBox.AdaptiveDecimalStepType)
        self.spin_speed.setValue(4.0)
        self.spin_speed.setKeyboardTracking(False)
        bar.addWidget(self.spin_speed)
        bar.addWidget(QtWidgets.QLabel("channel"))
        self.cmb_chan = QtWidgets.QComboBox()
        self.cmb_chan.addItems(CHANNELS)
        bar.addWidget(self.cmb_chan)
        self.chk_auto = QtWidgets.QCheckBox("auto levels")
        self.chk_auto.setChecked(True)
        self.chk_auto.setToolTip(
            "Re-level (2–98 percentile of A) on every sweep, like the "
            "live raster's autolevel.  Uncheck to hold your manual "
            "histogram levels while stepping/playing.")
        bar.addWidget(self.chk_auto)
        self.chk_lock = QtWidgets.QCheckBox("B follows A, offset")
        self.chk_lock.setChecked(True)
        bar.addWidget(self.chk_lock)
        self.spin_off = QtWidgets.QSpinBox()
        self.spin_off.setRange(-9999, 9999)
        self.spin_off.setValue(1)
        bar.addWidget(self.spin_off)
        self.chk_raw_markers = QtWidgets.QCheckBox("all raw markers")
        bar.addWidget(self.chk_raw_markers)
        self.btn_export = QtWidgets.QToolButton()
        self.btn_export.setText("Export ▾")
        self.btn_export.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        emenu = QtWidgets.QMenu(self)
        emenu.addAction("Export A (left)…").triggered.connect(
            lambda: self._export("A"))
        emenu.addAction("Export B (right)…").triggered.connect(
            lambda: self._export("B"))
        emenu.addAction("GIF A → B…").triggered.connect(self._export_gif)
        self.btn_export.setMenu(emenu)
        bar.addWidget(self.btn_export)
        if self._bks:
            # Per-row visibility: hidden rows compact away and the lane
            # shrinks, reclaiming height for the image panes.
            self.btn_rows = QtWidgets.QToolButton()
            self.btn_rows.setText("Visible Sections ▾")
            self.btn_rows.setPopupMode(
                QtWidgets.QToolButton.InstantPopup)
            menu = QtWidgets.QMenu(self)
            self._row_actions = {}
            first = {}
            for b in sorted(self._bks, key=lambda x: x["t0"]):
                first.setdefault(b["level"], str(b["label"]))
            for lvl in sorted(first):
                # Color swatch matching the lane's bracket color, and the
                # same 1-based number painted at the lane's left edge.
                pm = QtGui.QPixmap(14, 14)
                pm.fill(QtGui.QColor(
                    *self.BRACKET_PENS[lvl % len(self.BRACKET_PENS)]))
                act = menu.addAction(QtGui.QIcon(pm),
                                     f"{lvl + 1}: {first[lvl][:34]}")
                act.setCheckable(True)
                act.setChecked(True)
                act.toggled.connect(
                    lambda on, l=lvl: self._toggle_level(l, on))
                self._row_actions[lvl] = act
            menu.addSeparator()
            menu.addAction("show all").triggered.connect(
                lambda: self._set_all_rows(True))
            menu.addAction("hide all").triggered.connect(
                lambda: self._set_all_rows(False))
            self.btn_rows.setMenu(menu)
            bar.addWidget(self.btn_rows)
        bar.addStretch()
        self._bottom.addLayout(bar)

        # -- timeline --------------------------------------------------------
        self.tl = pg.PlotWidget(
            axisItems={"bottom": pg.DateAxisItem(orientation="bottom")})
        self.tl.setMaximumHeight(150)
        self.tl.setMinimumHeight(60)
        self.tl.hideAxis("left")
        self.tl.setMouseEnabled(x=True, y=False)
        self.tl.scene().sigMouseClicked.connect(self._tl_click)
        self._draw_timeline()
        self._bottom.addWidget(self.tl)

        # -- bracket lane: the change-event report under the timeline --------
        # Horizontal |____| spans from TIMELINE.json "brackets", one row
        # per level (0..3), x-linked to the timeline so zoom/pan stay in
        # step.  Click seeks, same as the timeline.
        self.br = None
        self.br_cur_a = self.br_cur_b = None
        if self._bks:
            self.br = pg.PlotWidget()
            self.br.hideAxis("left")
            self.br.hideAxis("bottom")
            self.br.setMouseEnabled(x=True, y=False)
            self.br.setXLink(self.tl)
            self.br.scene().sigMouseClicked.connect(self._br_click)
            self._bottom.addWidget(self.br)
            self._row_nums = []
            self.br.getViewBox().sigXRangeChanged.connect(
                lambda *_: self._pin_row_nums())
            self._rebuild_bracket_lane()

        # -- wiring ----------------------------------------------------------
        self.timer = QtCore.QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._tick)
        self.btn_play.clicked.connect(self._toggle_play)
        self.btn_prev.clicked.connect(lambda: self.seek(self.a - 1))
        self.btn_next.clicked.connect(lambda: self.seek(self.a + 1))
        self.cmb_chan.currentIndexChanged.connect(lambda _:
                                                  self.seek(self.a))
        self.spin_off.valueChanged.connect(lambda _: self.seek(self.a))
        self.chk_lock.toggled.connect(lambda _: self.seek(self.a))
        self.chk_raw_markers.toggled.connect(
            lambda _: (self._draw_timeline(), self.seek(self.a)))
        self.playing = False
        # Default proportions at launch (and scaled up on maximize via
        # the stretch factors): ~60% images, ~40% bottom.
        self._split.setSizes([600, 400])
        self.seek(0)

    # -- timeline drawing ----------------------------------------------------
    def _draw_timeline(self):
        """Rebuild the timeline.  With a TIMELINE.json narrative: colored
        region bands (scanning/stability/raw/approach/legacy/session) plus
        only the important events.  Raw journal markers are opt-in via the
        'all raw markers' checkbox (always the fallback when no narrative
        document exists)."""
        self.tl.clear()
        doc = self.data.timeline
        if doc:
            for r in doc.get("regions", []):
                kind = r.get("kind", "session")
                reg = pg.LinearRegionItem((r["t0"], r["t1"]), movable=False,
                                          brush=REGION_BRUSH.get(
                                              kind, (150, 150, 150, 40)))
                reg.setZValue(-10)
                for ln in reg.lines:
                    ln.setPen(pg.mkPen(None))
                reg.setToolTip(f"{_fmt(r['t0'])}–{_fmt(r['t1'])} [{kind}] "
                               f"{r.get('label', '')}\n{r.get('detail', '')}")
                self.tl.addItem(reg)
            for e in doc.get("events", []):
                if not e.get("important"):
                    continue
                ln = pg.InfiniteLine(
                    e["t"], angle=90,
                    pen=pg.mkPen(EVENT_PENS.get(e.get("kind", "note"),
                                                (200, 200, 200)), width=2),
                    label=str(e.get("label", "")),
                    labelOpts={"rotateAxis": (1, 0), "position": 0.92,
                               "anchors": [(0, 0), (0, 0)]})
                ln.setToolTip(f"{_fmt(e['t'])} {e.get('kind')}: "
                              f"{e.get('label', '')}")
                self.tl.addItem(ln)
        if self.chk_raw_markers.isChecked() or not doc:
            for t, typ, txt in self.data.markers:
                ln = pg.InfiniteLine(t, angle=90,
                                     pen=pg.mkPen(MARKER_COLORS[typ], width=1,
                                                  style=QtCore.Qt.DashLine))
                ln.setToolTip(f"{_fmt(t)} {typ}: {txt}")
                self.tl.addItem(ln)
        full = [(s[2]["t_end"], 1 if s[2]["dir"] == "up" else -1)
                for s in self.data.sweeps if not s[2]["partial"]]
        part = [(s[2]["t_end"], 1 if s[2]["dir"] == "up" else -1)
                for s in self.data.sweeps if s[2]["partial"]]
        if full:
            self.tl.plot([t for t, _ in full], [y for _, y in full],
                         pen=None, symbol="o", symbolSize=4,
                         symbolBrush=(90, 180, 255))
        if part:
            self.tl.plot([t for t, _ in part], [y for _, y in part],
                         pen=None, symbol="o", symbolSize=5,
                         symbolBrush=(255, 150, 40))
        # High-visibility playheads: thick, labeled, drawn above everything,
        # and DRAGGABLE — grab A or B and scrub at any speed (snaps to the
        # nearest completed sweep as it moves).
        self.cur_a = pg.InfiniteLine(
            0, angle=90, movable=True,
            pen=pg.mkPen((255, 40, 40), width=4),
            hoverPen=pg.mkPen((255, 120, 120), width=7),
            label="A", labelOpts={"position": 0.06, "color": (255, 80, 80),
                                  "fill": (0, 0, 0, 160)})
        self.cur_b = pg.InfiniteLine(
            0, angle=90, movable=True,
            pen=pg.mkPen((60, 140, 255), width=4),
            hoverPen=pg.mkPen((130, 190, 255), width=7),
            label="B", labelOpts={"position": 0.14, "color": (110, 170, 255),
                                  "fill": (0, 0, 0, 160)})
        self.cur_a.sigDragged.connect(self._drag_a)
        self.cur_b.sigDragged.connect(self._drag_b)
        for c in (self.cur_a, self.cur_b):
            c.setZValue(20)
            self.tl.addItem(c)

    BRACKET_PENS = [(120, 220, 255), (255, 200, 90), (255, 140, 200),
                    (140, 255, 160), (200, 160, 255), (255, 120, 90),
                    (90, 200, 200), (255, 240, 130), (170, 190, 255),
                    (180, 180, 180)]

    ROW = 1.45          # vertical units per bracket level

    def _toggle_level(self, lvl, on):
        (self._hidden_levels.discard if on
         else self._hidden_levels.add)(lvl)
        self._rebuild_bracket_lane()
        self.seek(self.a)

    def _set_all_rows(self, on):
        for act in self._row_actions.values():
            act.blockSignals(True)
            act.setChecked(on)
            act.blockSignals(False)
        self._hidden_levels = (set() if on
                               else set(self._row_actions))
        self._rebuild_bracket_lane()
        self.seek(self.a)

    def _rebuild_bracket_lane(self):
        """Redraw the lane with hidden levels removed and the remaining
        rows compacted; the widget height tracks the visible row count
        (zero rows -> lane fully hidden, height reclaimed)."""
        if self.br is None:
            return
        self.br.clear()
        self.br_cur_a = self.br_cur_b = None
        vis = sorted({b["level"] for b in self._bks}
                     - self._hidden_levels)
        if not vis:
            self.br.setVisible(False)
            return
        self.br.setVisible(True)
        rowmap = {lvl: i for i, lvl in enumerate(vis)}
        n = len(vis)
        # Min stays small so the splitter can squeeze the lane when the
        # operator drags the images bigger; max sets the default size.
        self.br.setMinimumHeight(36)
        self.br.setMaximumHeight(40 + 44 * n)
        self.br.setYRange(-(n - 1) * self.ROW - 0.5, 1.35, padding=0)
        self._draw_brackets(
            [b for b in self._bks if b["level"] in rowmap], rowmap)
        # Section numbers (1-based, level-colored) pinned to the left
        # edge — same number and color as the Visible Sections menu.
        self._row_nums = []
        for lvl, i in rowmap.items():
            color = self.BRACKET_PENS[lvl % len(self.BRACKET_PENS)]
            t = pg.TextItem(str(lvl + 1), color=color, anchor=(0.0, 0.5))
            self.br.addItem(t)
            self._row_nums.append((t, -i * self.ROW + 0.15))
        self._pin_row_nums()

    def _pin_row_nums(self):
        if not getattr(self, "_row_nums", None):
            return
        (x0, _x1), _ = self.br.viewRange()
        for t, y in self._row_nums:
            t.setPos(x0, y)

    def _draw_brackets(self, bks, rowmap):
        h = 0.30                       # end-tick height
        # Stagger neighbouring labels within a level between two heights
        # so adjacent brackets can't overprint each other's text.
        order = {}
        for b in sorted(bks, key=lambda x: (x["level"], x["t0"])):
            k = order[b["level"]] = order.get(b["level"], -1) + 1
            y = -float(rowmap[b["level"]]) * self.ROW
            color = self.BRACKET_PENS[b["level"] % len(self.BRACKET_PENS)]
            curve = pg.PlotCurveItem(
                [b["t0"], b["t0"], b["t1"], b["t1"]],
                [y + h, y, y, y + h],
                pen=pg.mkPen(color, width=2))
            curve.setToolTip(f"{_fmt(b['t0'])}–{_fmt(b['t1'])}  "
                             f"{b['label']}")
            self.br.addItem(curve)
            txt = pg.TextItem(b["label"], color=color, anchor=(0.5, 1.0))
            txt.setPos((b["t0"] + b["t1"]) / 2.0,
                       y + h + (0.0 if k % 2 == 0 else 0.55))
            self.br.addItem(txt)
        self.br_cur_a = pg.InfiniteLine(
            0, angle=90, pen=pg.mkPen((255, 40, 40, 140), width=2))
        self.br_cur_b = pg.InfiniteLine(
            0, angle=90, pen=pg.mkPen((60, 140, 255, 140), width=2))
        self.br.addItem(self.br_cur_a)
        self.br.addItem(self.br_cur_b)

    # -- behavior ------------------------------------------------------------
    def seek(self, i):
        n = len(self.data.sweeps)
        if n == 0:
            return
        self.a = max(0, min(n - 1, i))
        if self.chk_lock.isChecked():
            self.b = max(0, min(n - 1, self.a + self.spin_off.value()))
        chan = self.cmb_chan.currentText()
        img_a, _, sa = self.data.image(self.a, chan)
        img_b, _, sb = self.data.image(self.b, chan)
        lo, hi = np.nanpercentile(img_a, [2, 98])
        if not np.isfinite(lo) or hi <= lo:
            lo, hi = 0.0, 1.0
        for item, img in ((self.img_a, img_a), (self.img_b, img_b)):
            item.setImage(np.nan_to_num(img, nan=lo).T, autoLevels=False)
        if self.chk_auto.isChecked():
            self.hist.setLevels(lo, hi)
        self._sync_b_lut()
        self.lbl_a.setText("A  " + self.data.label(self.a))
        self.lbl_b.setText("B  " + self.data.label(self.b))
        self.cur_a.setValue(sa["t_end"])
        self.cur_b.setValue(sb["t_end"])
        if self.br_cur_a is not None:
            self.br_cur_a.setValue(sa["t_end"])
            self.br_cur_b.setValue(sb["t_end"])

    def _sync_b_lut(self, *_):
        """Mirror the histogram's levels and colormap onto pane B (the
        histogram is wired to A) so the two rasters always share one
        scale — same pattern as the live raster's retrace panes."""
        self.img_b.setLevels(self.hist.getLevels())
        self.img_b.setLookupTable(self.hist.gradient.getLookupTable(512))

    # -- export --------------------------------------------------------------
    def _export(self, which):
        i = self.a if which == "A" else self.b
        chan = self.cmb_chan.currentText()
        img, idx, s = self.data.image(i, chan)
        default = os.path.join(
            self.data.folder,
            f"export_sweep{i}_{chan}_{int(s['t_end'] * 1000)}.gsf")
        path, _flt = QtWidgets.QFileDialog.getSaveFileName(
            self, f"Export {which} — sweep #{i} ({chan})", default,
            "Gwyddion GSF, physical axes (*.gsf);;"
            "TIFF float32, raw data (*.tiff *.tif);;"
            "PNG, as displayed (*.png)")
        if not path:
            return
        try:
            note = self._write_export(path, img, idx, s, chan)
            QtWidgets.QToolTip.showText(
                QtGui.QCursor.pos(), f"Exported: {path}\n{note}", self)
            print(f"[EXPORT] {which} sweep#{i} {chan} -> {path}  {note}")
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Export failed", str(e))

    def _write_export(self, path, img, idx, s, chan):
        """Returns a one-line note about what was written."""
        arr = np.asarray(img, np.float32)
        finite = arr[np.isfinite(arr)]
        fill = float(finite.min()) if finite.size else 0.0
        data = np.nan_to_num(arr, nan=fill)
        ext = os.path.splitext(path)[1].lower()
        settings = idx.get("settings") or {}
        # per-sweep scale first — the sidecar value is stale after
        # mid-scan zooms (see label())
        size_nm = s.get("scan_size_nm") or settings.get("scan_size_nm")
        title = (f"{idx.get('source', '')} sweep#{s['i']} {s['dir']} {chan} "
                 f"{_fmt(s['t_start'])}-{_fmt(s['t_end'])}")
        if ext == ".png":
            # Visual export: the screen's current levels + colormap.
            from PIL import Image
            Image.fromarray(self._render_rgb(data)).save(path)
            return "8-bit render at current levels/colormap"
        if ext in (".tif", ".tiff"):
            import tifffile
            meta = {"channel": chan, "sweep": s["i"], "dir": s["dir"],
                    "t_start": s["t_start"], "t_end": s["t_end"],
                    "source": idx.get("source", ""),
                    "session": idx.get("session")}
            if size_nm:
                meta["scan_size_nm"] = size_nm
            tifffile.imwrite(path, data, metadata=meta)
            return "float32 raw data + metadata"
        if ext == ".gsf":
            if size_nm:
                xr = yr = float(size_nm) * 1e-9
                note = f"physical axes embedded: {size_nm} nm"
            else:
                xr = yr = 1.0
                title += " [scan size UNKNOWN - axes not physical]"
                note = "WARNING: no scan_size_nm in sidecar; axes not physical"
            self._write_gsf(
                path, data, xr, yr,
                x_off=float(settings.get("x_offset_nm") or 0.0) * 1e-9,
                y_off=float(settings.get("y_offset_nm") or 0.0) * 1e-9,
                title=title)
            return note
        raise ValueError(f"unsupported file type: {ext}")

    def _render_rgb(self, data):
        """uint8 RGB of an array at the screen's current levels + LUT."""
        lo, hi = self.hist.getLevels()
        span = (hi - lo) or 1.0
        arr = np.nan_to_num(np.asarray(data, np.float32), nan=lo)
        norm = np.clip((arr - lo) / span * 255.0, 0, 255).astype(int)
        lut = self.hist.gradient.getLookupTable(256)
        return lut[norm][..., :3].astype(np.uint8)

    def _export_gif(self):
        """Animate sweep A -> B (either direction) at the current channel,
        levels and colormap; asks for a frame rate, then a save path."""
        from PIL import Image
        i0, i1 = self.a, self.b
        step = 1 if i1 >= i0 else -1
        idxs = list(range(i0, i1 + step, step))
        n = len(idxs)
        if n < 2:
            QtWidgets.QMessageBox.information(
                self, "GIF A → B", "A and B are the same sweep — move one "
                "playhead first.")
            return
        fps, ok = QtWidgets.QInputDialog.getDouble(
            self, "GIF A → B",
            f"{n} frames (sweep #{i0} → #{i1}, "
            f"{self.cmb_chan.currentText()}, current levels/colormap)\n"
            "Frame rate (fps):", 10.0, 0.5, 60.0, 1)
        if not ok:
            return
        chan = self.cmb_chan.currentText()
        default = os.path.join(self.data.folder,
                               f"anim_sweep{i0}-{i1}_{chan}.gif")
        path, _f = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save GIF", default, "GIF animation (*.gif)")
        if not path:
            return
        try:
            frames = []
            for k, i in enumerate(idxs):
                img, _idx, _s = self.data.image(i, chan)
                frames.append(Image.fromarray(self._render_rgb(img)))
                if k % 100 == 99:
                    print(f"[GIF] rendered {k + 1}/{n}")
            frames[0].save(path, save_all=True, append_images=frames[1:],
                           duration=max(20, int(1000.0 / fps)), loop=0)
            QtWidgets.QToolTip.showText(
                QtGui.QCursor.pos(),
                f"GIF saved: {path}\n{n} frames @ {fps:g} fps", self)
            print(f"[GIF] {n} frames @ {fps:g} fps -> {path}")
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "GIF failed", str(e))

    @staticmethod
    def _write_gsf(path, image, x_real, y_real, x_off=0.0, y_off=0.0,
                   title="sweep"):
        """Gwyddion Simple Field, byte-identical format to the instrument
        GUI's save_gsf (header + NUL pad to 4 bytes + <f4 data)."""
        image = np.asarray(image, dtype=np.float32)
        yres, xres = image.shape
        header = "\n".join([
            "Gwyddion Simple Field 1.0",
            f"XRes = {xres}", f"YRes = {yres}",
            f"XReal = {x_real}", f"YReal = {y_real}",
            f"XOffset = {x_off}", f"YOffset = {y_off}",
            "XYUnits = m",
            f"Title = {title}", ""]).encode("utf-8")
        header += b"\0" * (4 - (len(header) % 4))
        with open(path, "wb") as f:
            f.write(header)
            image.astype("<f4").tofile(f)

    def _toggle_play(self):
        self.playing = not self.playing
        self.btn_play.setText("⏸ pause" if self.playing else "▶ play")
        if self.playing:
            self._tick()
        else:
            self.timer.stop()

    def _tick(self):
        if not self.playing:
            return
        if self.a >= len(self.data.sweeps) - 1:
            self._toggle_play()
            return
        t_now = self.data.sweeps[self.a][2]["t_end"]
        self.seek(self.a + 1)
        t_next = self.data.sweeps[self.a][2]["t_end"]
        delay = (t_next - t_now) / max(self.spin_speed.value(), 0.01)
        self.timer.start(int(max(0.02, min(delay, 2.0)) * 1000))

    def _nearest(self, t):
        return min(range(len(self.data.sweeps)),
                   key=lambda i: abs(self.data.sweeps[i][2]["t_end"] - t))

    def _seek_time(self, t):
        self.seek(self._nearest(t))

    def _drag_a(self, line):
        i = self._nearest(line.value())
        if i != self.a:
            self.seek(i)

    def _drag_b(self, line):
        i = self._nearest(line.value())
        if self.chk_lock.isChecked():
            # B is locked to A: dragging B adjusts the offset instead.
            if i - self.a != self.spin_off.value():
                self.spin_off.setValue(i - self.a)   # triggers a refresh
        elif i != self.b:
            self.b = i
            self.seek(self.a)

    def _tl_click(self, ev):
        self._seek_time(
            self.tl.getPlotItem().vb.mapSceneToView(ev.scenePos()).x())

    def _br_click(self, ev):
        self._seek_time(
            self.br.getPlotItem().vb.mapSceneToView(ev.scenePos()).x())

    def keyPressEvent(self, ev):
        if ev.key() == QtCore.Qt.Key_Space:
            self._toggle_play()
        elif ev.key() == QtCore.Qt.Key_Left:
            self.seek(self.a - 1)
        elif ev.key() == QtCore.Qt.Key_Right:
            self.seek(self.a + 1)
        else:
            super().keyPressEvent(ev)


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    target = sys.argv[1]
    height = None
    if "--height" in sys.argv:
        height = int(sys.argv[sys.argv.index("--height") + 1])
    data = DayData(target, height)
    if not data.sweeps:
        raise SystemExit(f"no sweeps found under {target}")
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    w = Player(data)
    w.resize(1250, 1000)
    w.show()
    app.exec()


if __name__ == "__main__":
    main()
