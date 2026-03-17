import logging
from PySide6.QtCore import QObject, Signal


class QtLogHandler(logging.Handler, QObject):

    log_signal = Signal(str)

    def __init__(self):
        logging.Handler.__init__(self)
        QObject.__init__(self)

    def emit(self, record):
        msg = self.format(record)
        self.log_signal.emit(msg)
