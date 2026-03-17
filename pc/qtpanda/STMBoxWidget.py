from PySide6 import QtWidgets, QtGui, QtCore


class STMBoxWidget(QtWidgets.QLabel):

    boxChanged = QtCore.Signal(tuple)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setMinimumSize(100, 100)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding
        )

        self.box = (10000, 10000, 50000, 50000)

        self.dragging = False
        self.setMouseTracking(True)

        self.setText("")
        self.setStyleSheet("background-color: white;")

    # --------------------------------
    # Square drawing region
    # --------------------------------

    def get_square_rect(self):

        w = self.width()
        h = self.height()

        size = min(w, h)

        x = (w - size) // 2
        y = (h - size) // 2

        return QtCore.QRect(x, y, size, size)

    # --------------------------------
    # Coordinate scaling
    # --------------------------------

    def stm_to_widget(self, x_stm, y_stm, w_stm=0, h_stm=0):

        square = self.get_square_rect()
        size = square.width()

        x_pix = square.left() + (x_stm / 65535) * size
        y_pix = square.top() + (y_stm / 65535) * size

        w_pix = (w_stm / 65535) * size
        h_pix = (h_stm / 65535) * size

        return x_pix, y_pix, w_pix, h_pix

    def widget_delta_to_stm(self, dx_pix, dy_pix):

        square = self.get_square_rect()
        size = square.width()

        dx_stm = int(dx_pix / size * 65535)
        dy_stm = int(dy_pix / size * 65535)

        return dx_stm, dy_stm

    # --------------------------------
    # Paint
    # --------------------------------

    def paintEvent(self, event):

        super().paintEvent(event)

        with QtGui.QPainter(self) as painter:

            painter.setRenderHint(QtGui.QPainter.Antialiasing)

            square = self.get_square_rect()

            # draw STM area border
            painter.setPen(QtGui.QPen(QtCore.Qt.black, 2))
            painter.drawRect(square)

            # draw scan box
            pen = QtGui.QPen(QtCore.Qt.red, 2)
            painter.setPen(pen)

            brush = QtGui.QBrush(QtGui.QColor(255, 0, 0, 50))
            painter.setBrush(brush)

            x, y, w, h = self.box

            x_pix, y_pix, w_pix, h_pix = self.stm_to_widget(x, y, w, h)

            painter.drawRect(x_pix, y_pix, w_pix, h_pix)

    # --------------------------------
    # Mouse events
    # --------------------------------

    def mousePressEvent(self, event):

        x, y, w, h = self.box

        x_pix, y_pix, w_pix, h_pix = self.stm_to_widget(x, y, w, h)

        rect = QtCore.QRectF(x_pix, y_pix, w_pix, h_pix)

        if rect.contains(event.position()):

            self.dragging = True
            self.press_pos = event.position()
            self.press_box = self.box

    def mouseMoveEvent(self, event):

        if not self.dragging:
            return

        dx_pix = event.position().x() - self.press_pos.x()
        dy_pix = event.position().y() - self.press_pos.y()

        dx_stm, dy_stm = self.widget_delta_to_stm(dx_pix, dy_pix)

        x0, y0, w, h = self.press_box

        new_x = x0 + dx_stm
        new_y = y0 + dy_stm

        new_x = max(0, min(65535 - w, new_x))
        new_y = max(0, min(65535 - h, new_y))

        self.box = (new_x, new_y, w, h)

        self.boxChanged.emit(self.box)

        self.update()

    def mouseReleaseEvent(self, event):

        self.dragging = False

    # --------------------------------
    # Wheel scaling
    # --------------------------------

    def wheelEvent(self, event):

        delta = event.angleDelta().y() / 120

        scale_factor = 1.1 ** delta

        x, y, w, h = self.box

        new_w = max(1, int(w * scale_factor))
        new_h = max(1, int(h * scale_factor))

        new_w = min(new_w, 65535)
        new_h = min(new_h, 65535)

        center_x = x + w // 2
        center_y = y + h // 2

        new_x = max(0, min(65535 - new_w, center_x - new_w // 2))
        new_y = max(0, min(65535 - new_h, center_y - new_h // 2))

        self.box = (new_x, new_y, new_w, new_h)

        self.boxChanged.emit(self.box)

        self.update()
