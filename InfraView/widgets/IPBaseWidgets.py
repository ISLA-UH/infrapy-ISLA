from PyQt5.QtWidgets import QWidget, QSizePolicy, QGroupBox, QMenu, QSplitter
from PyQt5.QtGui import QPalette, QColor

class IPWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        

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

        self.setVisible(False)

    def set_controlled_widget(self, widget):
        self.controlled_widget = widget

class IPSettingsGroupBox(QGroupBox):
    def __init__(self, title, parent=None):
        super().__init__(title, parent)

class IPMenu(QMenu):
    def __init__(self, parent):
        super().__init__(parent)

class IPSplitter(QSplitter):
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)

        self.setStyleSheet("QSplitter::handle{ background-color: #888; width: 50; height: 1;}")
