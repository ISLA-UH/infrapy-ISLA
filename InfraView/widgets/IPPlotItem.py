from typing import Optional, Tuple
import numpy as np

import pyqtgraph as pg
from pyqtgraph import LinearRegionItem

from PyQt5.QtGui import QCursor, QColor, QBrush, QFont
from PyQt5.QtWidgets import QMenu, QAction
from PyQt5.QtCore import pyqtSignal, QPoint, Qt

from obspy.core import UTCDateTime


class NonScientific(pg.AxisItem):
    """
    class for NonScientific axis
    """
    # def __init__(self, *args, **kwargs):
    #    super(NonScientific, self).__init__(*args, **kwargs)

    def tickStrings(self, values: list, scale, spacing):
        """
        :param values: list of values

        :return: list of strings for axis labels
        """
        # This line return the NonScientific notation value
        return ["%0.1f" % x for x in np.array(values).astype(float)]


class IPWaveformTimeAxis(pg.AxisItem):
    """
    subclass the basic axis item, mainly to make custom time axis
    """
    def __init__(self, est, *args, **kwargs):
        """
        initialize

        :param est: earliest start time as UTCDateTime
        :param args: additional args for pg.AxisItem
        :param kwargs: additional kwargs pg.AxisItem
        """
        super().__init__(orientation='bottom', *args, **kwargs)
        # est is the "earliest_start_time"
        self.set_earliest_start_time(est)

        # make font size smaller
        # font = QFont()
        # font.setPointSize(12)
        # self.setTickFont(font)

    def tickStrings(self, values: list, scale, spacing):
        """
        :param values: list of values
        :return: list of strings for axis labels
        """
        return [(self.earliest_start_time + value).strftime("%H:%M:%S") for value in values]

    def set_earliest_start_time(self, est: UTCDateTime):
        """
        set earliest start time

        :param est: earliest start time as UTCDateTime
        """
        self.earliest_start_time = est

    def get_start_time(self):
        """
        :return: earliest start time as UTCDateTime
        """
        return self.earliest_start_time


class IPSpectrogramTimeAxis(pg.AxisItem):
    """
    subclass the basic axis item, mainly to make custom time axis
    """
    def __init__(self, *args, **kwargs):
        """
        initialize

        :param args: additional args for pg.AxisItem
        :param kwargs: additional kwargs pg.AxisItem
        """
        super().__init__(orientation='bottom', *args, **kwargs)
        # st: (UTCDateTime) is the start_time of the window which will be the earliest start
        # time of the waveforms plus the offset seconds of the signal/noise window
        self.set_start_time(UTCDateTime(0))

    def tickStrings(self, values: list, scale, spacing):
        """
        :param values: list of values
        :return: list of strings for axis labels
        """
        return [(self.start_time + value).strftime("%H:%M:%S") for value in values]

    def set_start_time(self, st: UTCDateTime):
        """
        set start time

        :param st: start time as UTCDateTime
        """
        self.start_time = st


class IPCustomViewBox(pg.ViewBox):
    """
    class for custom view box
    """
    def __init__(self, parent=None):
        """
        initialize

        :param parent: parent widget
        """
        super(IPCustomViewBox, self).__init__(parent)

        self.menu = None    # override pyqtgraph viewboxmenu
        self.menu = self.getMenu()

    def raiseContextMenu(self, ev):
        """
        raise context menu

        ev: event
        """
        if not self.menuEnabled():
            return
        menu = self.getMenu()
        pos = ev.screenPos()
        menu.popup(QPoint(pos.x(), pos.y()))

    def getMenu(self):
        """
        :return: context menu
        """
        if self.menu is None:
            self.menu = QMenu()
            self.exportImage = QAction("Export Image", self.menu)
            self.menu.addAction(self.exportImage)
        return self.menu


class IPPlotItem(pg.PlotItem):
    """
    class for plot item
    """
    sigNoiseRegionChanged = pyqtSignal(tuple)
    sigSignalRegionChanged = pyqtSignal(tuple)
    sigFreqRegionChanged = pyqtSignal(tuple)

    def __init__(self, mode: str = 'plain', y_label_format: str = "", pickable: bool = False,
                 est: Optional[UTCDateTime] = None, lris: bool = True):
        '''
        :param mode: mode of plot.  Allowed values are 'waveform' or 'PSD' or 'Plain' or 'Spectrogram'
        :param y_label_format: format for y labels.  Allowed values are 'nonscientific'
        :param pickable: Allow click on plot to make a pick.  Default False
        :param est: Earliest Start Time as UTCDateTime
        :param lris: Enable Linear Region Items. Default True
        '''
        self.noise_region = None
        self.signal_region = None
        self.freq_region = None
        self.pickable = False
        self.labi = None

        if y_label_format == 'nonscientific':
            super().__init__(axisItems={'left': NonScientific(orientation='left')})

        if mode == 'waveform':
            if est is None:
                est = UTCDateTime(0)
            super().__init__(axisItems={'bottom': IPWaveformTimeAxis(est=est)})
        elif mode == 'spectrogram':
            if est is None:
                est = UTCDateTime(0)
            super().__init__(axisItems={'bottom': IPSpectrogramTimeAxis(est=est)})
        elif mode == 'PSD':
            super().__init__()
            self.enableAutoRange(self.xaxis(), enable=True)
            self.enableAutoRange(self.yaxis(), enable=True)
            self.setLogMode(x=True, y=False)
        else:
            super().__init__()

        # self.autoDownsample = True
        # self.setDownsampling(auto=True, ds=1000)
        # self.setClipToView(True)

        # this will tell the widget if you can click on it and generate a 'pick'
        self.pickable = pickable

        self.showAxis('right')
        self.getAxis('right').setTicks('')
        self.showAxis('top')
        self.getAxis('top').setTicks('')

        self.getAxis('left').setWidth(80)
        # font = QFont()
        # font.setPointSize(10)
        # self.getAxis('left').setTickFont(font)
        # self.getAxis('bottom').setTickFont(font)

        if lris:
            if mode == 'waveform':
                self.noise_region = IPLinearRegionItem_Noise()
                self.signal_region = IPLinearRegionItem_Signal()
                self.addItem(self.noise_region)
                self.addItem(self.signal_region)

            elif mode == 'PSD':
                self.freq_region = IPFreqLinearRegionItem()
                self.addItem(self.freq_region)

            elif mode == 'plain':
                pass

    # def setBackgroundColor(self, r, g, b):
    #     self.vb.setBackgroundColor(QColor(r, g, b))

    def setBackgroundColor(self, color):
        """
        set the background color of the viewbox
        """
        self.vb.setBackgroundColor(color)

    def backgroundColor(self):
        """
        :return: the current background color of the viewbox
        """
        return self.vb.state['background']

    def setEarliestStartTime(self, est: UTCDateTime):
        """
        set earliest start time

        est: earliest start time as UTCDateTime
        """
        self.getAxis('bottom').set_earliest_start_time(est)

    def get_start_time(self) -> UTCDateTime:
        """
        :return: earliest start time as UTCDateTime
        """
        return self.getAxis('bottom').get_start_time()

    def setPlotLabel(self, text: str):
        """
        set plot label

        :param text: text for plot label
        """
        if self.labi is not None:
            self.vb.removeItem(self.labi)
        self.labi = pg.LabelItem(text=text)
        self.labi.setParentItem(self.vb)
        self.labi.anchor(itemPos=(0.0, 0.0), parentPos=(0.0, 0.0))

    def clearPlotLabel(self):
        """
        clear plot label
        """
        if self.labi is not None:
            self.vb.removeItem(self.labi)
        self.labi = None

    def xaxis(self):
        """
        :return: x axis
        """
        return self.vb.XAxis

    def yaxis(self):
        """
        :return: y axis
        """
        return self.vb.YAxis

    def mouseClickEvent(self, evt):
        """
        mouse click event

        :param evt: mouse event
        """
        if evt.button() == Qt.RightButton:
            if self.pickable:
                if evt.button() == Qt.LeftButton:
                    _ = QCursor.pos()   # This is the global coordinate of the mouse
                    scene_pos = evt.scenePos()

                    mousepoint = self.vb.mapSceneToView(scene_pos)
                    _ = mousepoint.x()
                    evt.accept()
        else:
            evt.accept()

    def mouseDragEvent(self, evt):
        """
        mouse drag event

        :param evt: mouse event
        """
        if evt.button() == Qt.RightButton:
            evt.ignore()
        else:
            pass

    def getNoiseRegion(self):
        """
        :return: noise region
        """
        return self.noise_region

    def getSignalRegion(self):
        """
        :return: signal region
        """
        return self.signal_region

    def getFreqRegion(self):
        """
        :return: frequency region
        """
        return self.freq_region

    def getNoiseRegionRange(self):
        """
        :return: noise region range if exists, else None
        """
        if self.noise_region is not None:
            return self.noise_region.getRegion()
        else:
            return None

    def getSignalRegionRange(self):
        """
        :return: signal region range if exists, else None
        """
        if self.signal_region is not None:
            return self.signal_region.getRegion()
        else:
            return None

    def getFreqRegionRange(self):
        """
        :return: frequency region range if exists, else None
        """
        if self.freq_region is not None:
            return self.freq_region.getRegion()
        else:
            return None

    def setNoiseRegionRange(self, range):
        """
        set noise region range

        :param range: range to set
        """
        if self.noise_region is not None:
            self.noise_region.setRegion(range)

    def setSignalRegionRange(self, range):
        """
        set signal region range

        :param range: range to set
        """
        if self.signal_region is not None:
            self.signal_region.setRegion(range)

    def setFreqRegionRange(self, range):
        """
        set frequency region range

        :param range: range to set
        """
        if self.freq_region is not None:
            self.freq_region.setRegion(range)

    def copySignalRange(self, sourceSigRegion):
        """
        copy signal range from another region

        :param sourceSigRegion: source signal region
        """
        reg = sourceSigRegion.getRegion()
        self.signal_region.setRegion(reg)

    def copyNoiseRange(self, sourceNoiseRegion):
        """
        copy noise range from another region

        :param sourceNoiseRegion: source noise region
        """
        reg = sourceNoiseRegion.getRegion()
        self.noise_region.setRegion(reg)


class IPLinearRegionItem_Noise(LinearRegionItem):
    """
    class for linear region noise
    """
    sig_IPRegion_Change_finished = pyqtSignal(tuple)

    def __init__(self, values: Tuple[float, float] = (0, 1), orientation=LinearRegionItem.Vertical,
                 brush=None, movable: bool = True, bounds=None, swapMode: str = "block"):
        """
        initialize

        :param values: Tuple of 2 floats for region
        :param orientation: orientation of region
        :param brush: brush for region
        :param movable: whether region is movable.  Default True
        :param bounds: bounds for region
        :param swapMode: swap mode for region.  Default "block"
        """
        super().__init__(values=values, orientation=orientation, brush=brush, movable=movable, bounds=bounds,
                         swapMode=swapMode)
        self.setZValue(15)
        brush = QBrush(QColor(255, 71, 71, 50))
        self.setBrush(brush)

    def mouseClickEvent(self, ev):
        """
        handle mouse click event

        :param ev: event
        """
        if ev.button() == Qt.RightButton:
            ev.accept()
            pos = ev.screenPos()
            self.showMenu(pos)

    def showMenu(self, position):
        """
        show context menu

        :param position: position to show menu
        """
        menu = QMenu()
        _ = menu.addAction("Remove Selection", self.hideMe)
        _ = menu.exec_(QPoint(position.x(), position.y()))

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

    def lineMovedFinished(self):
        """
        handle line moved
        """
        self.sig_IPRegion_Change_finished.emit(self.getRegion())
        super().lineMovedFinished()


class IPLinearRegionItem_Signal(LinearRegionItem):
    """
    class for linear region signal
    """
    sig_IPRegion_Change_finished = pyqtSignal(tuple)

    def __init__(self, values: Tuple[float, float] = (0, 1), orientation=LinearRegionItem.Vertical, brush=None,
                 movable: bool = True, bounds=None, swapMode: str = "block"):
        """
        initialize

        :param values: Tuple of 2 floats for region
        :param orientation: orientation of region
        :param brush: brush for region
        :param movable: whether region is movable.  Default True
        :param bounds: bounds for region
        :param swapMode: swap mode for region.  Default "block"
        """
        super().__init__(values=values, orientation=orientation, brush=brush, movable=movable, bounds=bounds,
                         swapMode=swapMode)
        self.setZValue(15)
        brush = QBrush(QColor(80, 159, 250, 100))
        self.setBrush(brush)

    def mouseClickEvent(self, ev):
        """
        handle mouse click event

        :param ev: event
        """
        if ev.button() == Qt.RightButton:
            ev.accept()
            pos = ev.screenPos()
            self.showMenu(pos)

    def showMenu(self, position):
        """
        show context menu

        :param position: position to show menu
        """
        menu = QMenu()
        _ = menu.addAction("Remove Selection", self.hideMe)
        _ = menu.exec_(QPoint(position.x(), position.y()))

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

    def lineMovedFinished(self):
        """
        handle line moved
        """
        print("move finished")
        self.sig_IPRegion_Change_finished.emit(self.getRegion())
        super().lineMovedFinished()


class IPFreqLinearRegionItem(LinearRegionItem):
    """
    class for frequency linear region
    """
    def __init__(self, values: Tuple[float, float] = (np.log10(0.5), np.log10(5)),
                 orientation=LinearRegionItem.Vertical, brush=None, movable: bool = True,
                 bounds=None, swapMode: str = "block"):
        """
        initialize

        :param values: Tuple of 2 floats for region
        :param orientation: orientation of region
        :param brush: brush for region
        :param movable: whether region is movable.  Default True
        :param bounds: bounds for region
        :param swapMode: swap mode for region.  Default "block"
        """
        super().__init__(values=values, orientation=orientation, brush=brush, movable=movable, bounds=bounds,
                         swapMode=swapMode)
        self.setZValue(15)
        brush = QBrush(QColor(200, 200, 200, 50))
        self.setBrush(brush)

    def mouseClickEvent(self, ev):
        """
        handle mouse click event

        :param ev: event
        """
        if ev.button() == Qt.RightButton:
            ev.accept()
            pos = ev.screenPos()
            self.showMenu(pos)

    def showMenu(self, position):
        """
        show menu

        :param position: position to show menu
        """
        menu = QMenu()
        # delete_selection = menu.addAction("Remove Selection", self.hideMe)
        _ = menu.exec_(QPoint(position.x(), position.y()))

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
