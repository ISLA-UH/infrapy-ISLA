#!/usr/bin/env python

from PyQt5 import QtWidgets
from PyQt5.QtGui import QIcon

import os
import sys
import platform

from pathlib import Path
from InfraView.widgets.IPApplicationWindow import *


def main():
    progname = "InfraView"
    progversion = "0.4.1"

    my_system = platform.system()
    my_release = platform.release()

    qApp = QtWidgets.QApplication(sys.argv)
    icon_file = str(Path(__file__).parent / 'resources' / 'graphics' / 'icons' / 'start_64')
    qApp.setWindowIcon(QIcon(icon_file))

    aw = IPApplicationWindow(qApp, progname, progversion)
    aw.show()

    sys.exit(qApp.exec())


if __name__ == '__main__':
    main()
