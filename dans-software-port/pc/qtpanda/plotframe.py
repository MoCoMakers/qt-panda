from PySide6 import QtWidgets, QtCore
import pyqtgraph as pg
import pyqtgraph.exporters


class PlotFrame(QtWidgets.QWidget):

    levelsChanged = QtCore.Signal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)

        # --------------------------
        # Layout
        # --------------------------
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # --------------------------
        # Graphics View
        # --------------------------
        self.graphics = pg.GraphicsLayoutWidget()
        self.graphics.setBackground("w")

        self.graphics.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding
        )

        self.layout.addWidget(self.graphics, 1)


        # --------------------------
        # Plot elements
        # --------------------------
        self.plot_item = None
        self.curve = None
        self.image_item = None
        self.bars = None
        self.arrow = None
        self.marker = None
        self.marker_text = None
        self._extra_curves = {}

    # --------------------------
    # Line Plot
    # --------------------------

    def add_plot(self, label=None, xlabel=None, ylabel=None, pen=None):

        self.plot_item = self.graphics.addPlot()

        if xlabel:
            self.plot_item.setLabel('bottom', xlabel)

        if ylabel:
            self.plot_item.setLabel('left', ylabel)

        #self.plot_item.getAxis('bottom').setHeight(80)

        if label:
            self.plot_item.addLegend()

        if pen is None:
            pen = pg.mkPen(width=2)

        self.curve = self.plot_item.plot(
            [0, 1],
            [0, 0],
            name=label,
            pen=pen
        )

        self.plot_item.setMouseEnabled(x=False, y=False)
        self.plot_item.enableAutoRange()

    # --------------------------
    # Histogram Plot
    # --------------------------

    def add_histogram(self, label=None, xlabel=None, ylabel=None, brush=None):

        self.plot_item = self.graphics.addPlot()

        if xlabel:
            self.plot_item.setLabel('bottom', xlabel)

        if ylabel:
            self.plot_item.setLabel('left', ylabel)

        if label:
            self.plot_item.setTitle(label)

        if brush is None:
            brush = (80, 140, 255, 200)

        # Bars: filled in live via update_histogram()
        self.bars = pg.BarGraphItem(
            x=[0], height=[0], width=1.0, brush=brush
        )
        self.plot_item.addItem(self.bars)

        # Arrow marking the bin the most recent sample landed in.
        # angle=-90 -> tip points straight down onto the bar top.
        self.arrow = pg.ArrowItem(
            angle=-90, tipAngle=45, headLen=18,
            pen=pg.mkPen('r'), brush='r'
        )
        self.arrow.setVisible(False)
        self.plot_item.addItem(self.arrow)

        self.plot_item.setMouseEnabled(x=False, y=False)
        self.plot_item.enableAutoRange()

    def update_histogram(self, centers, counts, current_index=None):

        if self.bars is None:
            return

        if len(centers) == 0:
            return

        width = (centers[1] - centers[0]) if len(centers) > 1 else 1.0

        self.bars.setOpts(x=centers, height=counts, width=width * 0.9)

        # Position the "currently growing bar" arrow
        if (self.arrow is not None and
                current_index is not None and
                0 <= current_index < len(counts)):

            peak = max(counts) if len(counts) else 0
            headroom = max(peak * 0.06, 1)

            self.arrow.setPos(
                centers[current_index],
                counts[current_index] + headroom
            )
            self.arrow.setVisible(True)
        elif self.arrow is not None:
            self.arrow.setVisible(False)

    # --------------------------
    # Log-log / multi-curve helpers (Fourier Analysis tab)
    # --------------------------

    def set_log_mode(self, x=False, y=False):
        if self.plot_item is not None:
            self.plot_item.setLogMode(x=x, y=y)

    def disable_si_prefix(self):
        """Turn off pyqtgraph's auto-SI prefix on both axes.  With no units
        set, the auto-scaler rescales tick values and appends '(x1e+09)' to
        the axis label, which is wrong on log axes (Allan tau axis showed
        nanoseconds-style scaling for a range that is actually seconds)."""
        if self.plot_item is None:
            return
        for name in ("bottom", "left"):
            self.plot_item.getAxis(name).enableAutoSIPrefix(False)

    def mark_point(self, x, y, text=None, color='r'):
        """Draw (or move) a single marker + optional text label."""
        if self.plot_item is None:
            return
        if self.marker is None:
            self.marker = pg.ScatterPlotItem(
                size=10, brush=pg.mkBrush(color), pen=pg.mkPen('k', width=1)
            )
            self.plot_item.addItem(self.marker)
        self.marker.setData([x], [y])
        if text:
            if self.marker_text is None:
                self.marker_text = pg.TextItem(color=color, anchor=(0, 1))
                self.plot_item.addItem(self.marker_text)
            self.marker_text.setText(text)
            self.marker_text.setPos(x, y)

    def clear_marker(self):
        if self.marker is not None:
            self.marker.setData([], [])
        if self.marker_text is not None:
            self.marker_text.setText("")

    def add_extra_curve(self, name, pen=None, label=None):
        """Add an additional named line to the current plot_item, alongside
        the primary curve managed by update_plot() (e.g. reference/guide
        lines). Addressable later via update_extra_curve(name, ...)."""
        if self.plot_item is None:
            return None
        if pen is None:
            pen = pg.mkPen(width=1, style=QtCore.Qt.PenStyle.DashLine)
        curve = self.plot_item.plot([], [], name=label, pen=pen)
        self._extra_curves[name] = curve
        return curve

    def update_extra_curve(self, name, x_data, y_data):
        curve = self._extra_curves.get(name)
        if curve is not None:
            curve.setData(x_data, y_data)

    # --------------------------
    # Image Plot
    # --------------------------

    def add_image(self, image, label = None):

        self.plot_item = self.graphics.addPlot()

        self.image_item = pg.ImageItem(image)

        # Default levels for 16-bit STM data
        self.image_item.setLevels([0, 65535])

        self.plot_item.addItem(self.image_item)

        # --------------------------
        # Histogram / LUT
        # --------------------------
        self.hist_lut = pg.HistogramLUTWidget()
        self.hist_lut.setMinimumWidth(120)

        self.layout.addWidget(self.hist_lut)

        # STM style origin
        self.plot_item.invertY(True)

        self.plot_item.enableAutoRange()

        # Connect histogram
        self.hist_lut.setImageItem(self.image_item)

        # Default colormap
        self.hist_lut.gradient.loadPreset("viridis")

        # Forward histogram level changes
        self.hist_lut.item.sigLevelsChanged.connect(self._hist_levels_changed)

    # --------------------------
    # Histogram Level Callback
    # --------------------------

    def _hist_levels_changed(self):
        if self.image_item is None:
            return

        levels = self.image_item.getLevels()

        if levels is None:
            return

        low, high = levels
        self.levelsChanged.emit(low, high)

    # --------------------------
    # Update Line Plot
    # --------------------------

    def update_plot(self, x_data, y_data):

        if self.curve is not None:
            self.curve.setData(x_data, y_data)

    # --------------------------
    # Update Image
    # --------------------------

    def update_image(self, image_data, extent=None):

        if self.image_item is None:
            return

        self.image_item.setImage(image_data, autoLevels=False)

        if extent:
            y_start, y_end, x_start, x_end = extent

            rect = QtCore.QRectF(
                y_start,
                x_start,
                y_end - y_start,
                x_end - x_start
            )

            self.image_item.setRect(rect)

    # --------------------------
    # Set Levels (slider control)
    # --------------------------

    def set_levels(self, low, high):

        if self.image_item is None:
            return

        self.image_item.setLevels([low, high])

    # --------------------------
    # Get Levels
    # --------------------------

    def get_levels(self):

        if self.image_item is None:
            return None

        return self.image_item.getLevels()

    # --------------------------
    # Auto Levels
    # --------------------------

    def auto_levels(self):

        if self.image_item is None:
            return

        self.image_item.setAutoLevels()

    # --------------------------
    # Colormap Control
    # --------------------------

    def set_colormap(self, name):

        try:
            self.hist_lut.gradient.loadPreset(name)
        except Exception:
            print(f"Unknown colormap: {name}")

    # --------------------------
    # Save Image
    # --------------------------

    def save_figure(self, image_path):

        exporter = pyqtgraph.exporters.ImageExporter(
            self.graphics.scene()
        )

        exporter.export(image_path)
