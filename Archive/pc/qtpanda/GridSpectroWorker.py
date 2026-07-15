# This Python file uses the following encoding: utf-8
from PySide6.QtCore import QObject,Signal

class GridSpectroWorker(QObject):

    progress = Signal(int)
    finished = Signal(object)  # emits grid_cube

    def __init__(self, stm, params):
        super().__init__()
        self.stm = stm
        self.params = params

    def run(self):

        def progress_cb(line_index):
            self.progress.emit(line_index)

        grid = self.stm.startGridSpectroscopy(
            *self.params,
            progress_callback=progress_cb
        )

        self.finished.emit(grid)
