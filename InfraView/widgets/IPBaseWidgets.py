from PyQt5.QtWidgets import QWidget, QLabel, QSizePolicy, QGroupBox, QMenu, QSplitter, QPushButton
from PyQt5.QtGui import QColor, QPaintEvent, QPainter
from PyQt5.QtCore import QSize, QRect


class IPColorButton(QPushButton):
    current_color = QColor(255, 0, 0)

    def __init__(self, color):
        super().__init__()
        self.current_color = color
        size = QSize(self.height(), self.height())
        self.setFixedSize(QSize(26,26))

    def paintEvent(self, a0: QPaintEvent) -> None:
        super().paintEvent(a0)
        r = QRect(0, 0, self.width() * 0.75, self.height() * 0.75)
        r.moveTo(self.rect().center() - r.center())
        painter = QPainter(self)
        painter.setBrush(self.current_color)
        painter.drawRect(r)

    def set_color(self, new_color):
        # new color should be a QColor type
        self.current_color = new_color

    def color(self):
        return QColor(self.current_color)
    
    def color_str(self):
        return self.color().name()
    

class IPMenu(QMenu):
    def __init__(self, parent):
        super().__init__(parent)


class IPSettingsGroupBox(QGroupBox):
    def __init__(self, title="", parent=None):
        super().__init__()
        self.setTitle(title)


class IPSettingsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__()

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


class IPSplitter(QSplitter):
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)

        self.setHandleWidth(1)

class IPWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

#class IPElidedLabel(QLabel):

        
