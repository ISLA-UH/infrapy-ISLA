#!/usr/bin/env python

from multiprocessing import context
import ssl

from PyQt5 import QtWidgets
from PyQt5.QtGui import QIcon

import os
import sys
import platform

from pathlib import Path

import certifi

from InfraView.widgets.IPApplicationWindow import IPApplicationWindow


def main():
    progname = "InfraView"
    progversion = "0.4.1.0"
    context = ssl.create_default_context(cafile=certifi.where())
    ssl._create_default_https_context = lambda: context

    my_system = platform.system()
    my_release = platform.release()

    qApp = QtWidgets.QApplication(sys.argv)
    icon_file = os.path.join(os.getcwd(), 'InfraView', 'resources', 'graphics', 'icons', 'start_64')
    qApp.setWindowIcon(QIcon(icon_file))

    aw = IPApplicationWindow(qApp, progname, progversion)
    aw.show()

    sys.exit(qApp.exec())


if __name__ == '__main__':
    main()
