# from abc import ABC, abstractmethod
from typing import Optional

from PyQt5.QtWidgets import QWidget, QLabel, QSizePolicy, QGroupBox, QMenu, QSplitter, QPushButton, QDialog, \
                            QDialogButtonBox, QVBoxLayout
from PyQt5.QtGui import QColor, QPaintEvent, QPainter
from PyQt5.QtCore import QSize, QRect, Qt


class IPContinueDialog(QDialog):
    """
    Class for continue dialog
    """
    def __init__(self, parent: QWidget, message: str, title: str = ""):
        """
        Initialize continue dialog

        :param parent: parent widget
        :param message: message to display
        :param title: dialog title
        """
        super().__init__(parent)
        self.setWindowTitle(title)
        self.message = message
        self.buildUI()

    def buildUI(self):
        """
        build the UI
        """
        qbtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel

        self.buttonBox = QDialogButtonBox(qbtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        layout = QVBoxLayout()
        message_label = QLabel(self.message)
        layout.addWidget(message_label)
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)


class IPColorButton(QPushButton):
    """
    class for color button
    """
    current_color = QColor(255, 0, 0)

    def __init__(self, color: QColor):
        """
        initialize color button

        :param color: initial color as QColor object
        """
        super().__init__()
        self.current_color = color
        self.size = QSize(self.height(), self.height())
        self.setFixedSize(QSize(26, 26))

    def paintEvent(self, a0: QPaintEvent) -> None:
        """
        paint event
        """
        super().paintEvent(a0)
        r = QRect(0, 0, self.width() * 0.75, self.height() * 0.75)
        r.moveTo(self.rect().center() - r.center())
        painter = QPainter(self)
        painter.setBrush(self.current_color)
        painter.drawRect(r)

    def set_color(self, new_color: QColor):
        """
        set current color

        :param new_color: new color as QColor object
        """
        # new color should be a QColor type
        self.current_color = new_color
        self.update()

    def set_color_from_str(self, new_color_str: str):
        """
        set current color from string ie: "#RRGGBB"

        :param new_color_str: color as string
        """
        self.set_color(QColor(new_color_str))

    def color(self):
        """
        :return: current color as QColor object
        """
        return QColor(self.current_color)

    def color_str(self):
        """
        :return: current color as string ie: "#RRGGBB"
        """
        return self.color().name()


class IPMenu(QMenu):
    """
    class for IPMenu
    """
    def __init__(self, parent: QWidget):
        """
        initialize IPMenu

        :param parent: parent widget
        """
        super().__init__(parent)


class IPSettingsGroupBox(QGroupBox):
    """
    class for settings group box
    """
    def __init__(self, title: str = ""):
        """
        initialize settings group box

        :param title: group box title
        :param parent: parent widget
        """
        super().__init__()
        self.setTitle(title)


class IPSettingsWidget(QWidget):
    """
    class for settings widget
    """
    def __init__(self):
        """
        initialize settings widget
        """
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

    def set_controlled_widget(self, widget: QWidget):
        """
        set the controlled widget

        :param widget: controlled widget
        """
        self.controlled_widget = widget

    # def to_dict(self):
    #    pass

    # def from_dict(self, sd):
    #     pass


class IPSplitter(QSplitter):
    """
    class for IP Splitter
    """
    def __init__(self, orientation: Qt.Orientation, parent: Optional[QWidget] = None):
        """
        initialize IP Splitter

        :param orientation: splitter orientation
        :param parent: parent widget
        """
        super().__init__(orientation, parent)

        self.setHandleWidth(1)


class IPWidget(QWidget):
    """
    class for IP Widget
    """
    def __init__(self, parent: Optional[QWidget] = None):
        """
        initialize IP Widget

        :param parent: parent widget
        """
        super().__init__(parent)

# class IPElidedLabel(QLabel):
