This is the new UI for the QT Panda STM project. This software is loosely based on the older python project that used matplotlib.

This software is also written in python, It uses QT5 for the UI
It has a number of additions to the functionality, including a grid spectroscopy mode to scan dI/dV and dI/dZ curves at each x/y grid location
It adds a noise scan to detemine noise in the system. It adds settle times for piezo x/y/z movements as well as bias.
It uses the following dependencies:
    PySide6>=6.5
    pyqtgraph>=0.13
    numpy>=1.24
    tifffile
    pyserial
    h5py
    gwyfile
