from typing import Optional, Tuple
import pyqtgraph as pg

from pyqtgraph.graphicsItems.InfiniteLine import InfLineLabel
from pyqtgraph import LinearRegionItem

from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt, QPoint
from PyQt5.QtGui import QPen
from PyQt5.QtWidgets import QMenu


class IPPickLine(pg.InfiniteLine):
    """
    class for pick lines
    """
    sigPickLineMoving = pyqtSignal(pg.InfiniteLine, float)
    sigPickLineMoved = pyqtSignal(float)
    sigCopyPickLine = pyqtSignal(pg.InfiniteLine)
    sigDeleteMe = pyqtSignal(pg.InfiniteLine)
    sigStartEndBarsChanged = pyqtSignal(pg.InfiniteLine, list)  # emit when there are any changes to the start end bars
    sigCreateStartEndBars = pyqtSignal(pg.InfiniteLine)  # emit when you want to create new start end (bars)
    sigRemoveStartEndBars = pyqtSignal(pg.InfiniteLine)    # emit when the picklines start end bars are removed

    _note = ''
    _Name = ''
    start_end_bars = None
    start_end = None

    def __init__(self, pickItem, starting_pos=None):
        """
        initialize

        :param pickItem: DetectionItem that holds the information for the line
        :param starting_pos: number of seconds from earliest_start_time that the detection occurs
        """
        super().__init__(angle=90, movable=True, pen='r', label='')

        self._Name = pickItem.name
        self._note = pickItem.note

        if starting_pos is not None:
            self.setPos(starting_pos)

        if pickItem.start is not None and pickItem.end is not None:
            self.start_end = [pickItem.start, pickItem.end]
            self.addStartEndBars(self.start_end)
        self.setZValue(20)

        self.label = InfLineLabel(self, text=self._Name, movable=True, color=(0, 0, 0))
        self.label.fill = pg.mkBrush(255, 255, 255, 0)
        self.label.setPosition(0.90)
        self.label.setZValue(20)

        self.setHoverPen('r', width=3)

    def showMenu(self, position):
        """
        show menu

        :param position: position to show menu
        """
        menu = QMenu()

        # menu actions
        action_addStartEndBars = None
        action_removeStartEndBars = None

        if self.start_end_bars is None:
            action_addStartEndBars = menu.addAction("Add Start/End Bars")
        else:
            action_removeStartEndBars = menu.addAction("Remove Start/End Bars")

        action_deletePick = menu.addAction("Delete Detection")

        ret = menu.exec_(QPoint(position.x(), position.y()))

        if ret is None:
            return  # Do nothing
        elif ret == action_deletePick:
            self.sigDeleteMe.emit(self)
        elif ret == action_addStartEndBars:
            # creation of the startEnd bars requires knowledge of the current views range,
            # so emit a signal here and let the detectionwidget do the work
            self.sigCreateStartEndBars.emit(self)
        elif ret == action_removeStartEndBars:
            self.removeStartEndBars()
        self.sigCopyPickLine.emit(self)

    def mousePressEvent(self, evt):
        """
        handles mouse press events

        :param evt: mouse event
        """
        if evt.button() == Qt.RightButton:
            evt.accept()
            self.showMenu(evt.screenPos())
        elif evt.button() == Qt.LeftButton:
            if self.start_end_bars is not None:
                startEndRange = self.start_end_bars.getRegion()
                self.start_end = [startEndRange[0] - self.pos().x(), startEndRange[1] - self.pos().x()]
            super().mousePressEvent(evt)

    def mouseDragEvent(self, ev):
        """
        handles mouse drag events

        :param ev: mouse event
        """
        if self.movable and ev.button() == QtCore.Qt.LeftButton:
            super().mouseDragEvent(ev)
            pos = self.getXPos()
            self.sigPickLineMoving.emit(self, pos)

            if ev.isFinish():
                # the super() sigPositionChangeFinished doesn't include the position, so we make our own
                self.sigPickLineMoved.emit(pos)

            if self.start_end_bars is not None:
                self.start_end_bars.setRegion((pos + self.start_end[0], pos + self.start_end[1]))

    def setColor(self, color):
        """
        set color of the pick line

        :param color: QColor object
        """
        self.setPen(QPen(color))
        self.setHoverPen(color, width=3)

    def hoverEnterEvent(self, evt):
        """
        hover enter event

        :param evt: hover event (not used)
        """
        if self._note != '':
            self.label.setText(self._Name + '  [' + self._note + ']')

    def hoverLeaveEvent(self, evt):
        """
        hover leave event

        :param evt: hover event (not used)
        """
        self.label.setText(self._Name)

    def addStartEndBars(self, start_end: Optional[Tuple[float, float]] = None):
        """
        add start/end bars

        :param start_end: tuple of two floats indicating start and end in seconds from pickline position
        """
        if start_end is None:
            start_end = (-10, 10)
        self.start_end = start_end
        self.start_end_bars = IPStartEndRegionItem(self,
                                                   values=[self.getXPos() + start_end[0],
                                                           self.getXPos() + start_end[1]])
        self.start_end_bars.sigRegionChanged.connect(self.startEndRegionChanged)

    def removeStartEndBars(self):
        """
        remove start/end bars
        """
        self.start_end_bars = None
        self.start_end = None
        self.sigRemoveStartEndBars.emit(self)

    def startEndBars(self):
        """
        return start/end bars
        """
        return self.start_end_bars

    @pyqtSlot(object)
    def startEndRegionChanged(self, startEndRegion):
        startEndRange = self.start_end_bars.getRegion()
        self._start_end = [startEndRange[0] - self.getXPos(), startEndRange[1] - self.getXPos()]
        self.sigStartEndBarsChanged.emit(self, self._start_end)


class IPStartEndRegionItem(LinearRegionItem):
    """
    class for start/end region
    """
    mirror = False

    def __init__(self, pickline, values: Tuple[float, float] = (0, 1), orientation: str = 'vertical',
                 brush: Optional[QtGui.QBrush] = None, hoverBrush: Optional[QtGui.QBrush] = None,
                 hoverPen: Optional[QtGui.QPen] = None, pen: Tuple[int, int, int] = (120, 80, 80),
                 movable: bool = True):
        """
        initialize
        """
        super().__init__(values, orientation, brush, hoverBrush, hoverPen, pen, movable)
        self.swapMode = 'block'
        self.pickline = pickline    # reference to the pickline that 'owns' this lri
        self.setZValue(self.pickline.zValue() - 1)
        brush = QtGui.QBrush(QtGui.QColor(200, 200, 200, 50))
        self.setBrush(brush)

        self.lines[0].sigPositionChanged.connect(lambda: self.lineMoved(0))
        self.lines[1].sigPositionChanged.connect(lambda: self.lineMoved(1))

    def hideMe(self):
        """
        hide the region
        """
        self.setVisible(False)

    def showMe(self):
        """
        show the region
        """
        self.setVisible(True)

    def lineMoved(self, i):
        """
        handle line moved

        param i: index of line moved (0 or 1)
        """
        if self.blockLineSignal:
            return
        pos = self.pickline.pos().x()
        if i == 0:
            if self.mirror:
                delta = pos - self.lines[0].value()
                self.lines[1].setValue(pos + delta)
        if i == 1:
            if self.mirror:
                delta = pos - self.lines[1].value()
                self.lines[0].setValue(pos + delta)

        # self.prepareGeometryChange()
        self.sigRegionChanged.emit(self)
