from PyQt5.QtWidgets import QWidget, QSizePolicy, QGroupBox, QMenu
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
        self.setFont(font)

        self.setAutoFillBackground(True)
        pal = self.palette()
        pal.setColor(QPalette.Window, QColor('#f0f0f0'))
        self.setPalette(pal)

        self.active = True
        self.setVisible(self.active)

    def is_active(self):
        return self.active
    
    def set_active(self, active):
        # active is a bool
        self.active = active

class IPSettingsGroupBox(QGroupBox):
    def __init__(self, title, parent=None):
        super().__init__(title, parent)

class IPMenu(QMenu):
    def __init__(self, parent):
        super().__init__(parent)

