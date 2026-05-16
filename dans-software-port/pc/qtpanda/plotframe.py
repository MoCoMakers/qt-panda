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
