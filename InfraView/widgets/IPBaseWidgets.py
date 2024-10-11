from PyQt5.QtWidgets import QWidget, QSizePolicy, QGroupBox
from PyQt5.QtGui import QPalette, QColor

class IPSettingsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setSizePolicy(QSizePolicy.Expanding,
                           QSizePolicy.Maximum)
        font = self.font()
        fontsize = font.pointSize()
        if fontsize > 10:
            font.setPointSize(fontsize-2)
        # font.setFamily("monospace")
        self.setFont(font)

        pal = self.palette()
        pal.setColor(QPalette.Window, QColor(64,64,64))
        pal.setColor(QPalette.WindowText, QColor(255, 255, 255))
        self.setAutoFillBackground(True)
        self.setPalette(pal)

class IPSettingsGroupBox(QGroupBox):
    def __init__(self, title, parent=None):
        super().__init__(title, parent)

        pal = self.palette()
        pal.setColor(QPalette.WindowText, QColor(255, 255, 255))
        self.setPalette(pal)