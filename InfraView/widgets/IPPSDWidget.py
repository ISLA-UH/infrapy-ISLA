from typing import Tuple
from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel,  QDoubleSpinBox, QPushButton)
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtGui import QPalette

import pyqtgraph as pg

import numpy as np
from scipy import signal

from InfraView.widgets.IPPlotItem import IPPlotItem
import InfraView.widgets.IPUtils as utils


class IPPSDWidget(QWidget):
    """
    class for PSD widget
    """
    windows = ['hann', 'hamming', 'boxcar', 'bartlett', 'blackman']

    noiseCurve = None
    signalCurve = None

    currentSignalData = None
    currentNoiseData = None

    blue_pen = pg.mkPen(color=utils.lanl_blue, width=1)
    red_pen = pg.mkPen(color=utils.lanl_red, width=1)

    def __init__(self, parent):
        """
        initialize

        :param parent: parent widget
        """
        super().__init__()

        self.parent = parent
        self.buildUI()
        self.show()

    def buildUI(self):
        """
        build the UI
        """
        # self.setAutoFillBackground(True)
        # pal = self.palette()
        # pal.setColor(QPalette.Window, Qt.white)
        # self.setPalette(pal)

        self.plotLayoutWidget = pg.GraphicsLayoutWidget()
        self.psdPlot = IPPlotItem(mode='PSD')

        self.psdPlot.setLabel('bottom', 'f (Hz)')
        self.psdPlot.setLabel('left', 'Power Spectral Density (dB)')
        self.psdPlot.setTitle("...")

        initdata = np.array([1])

        self.noiseCurve = self.psdPlot.plot(x=initdata, y=initdata, pen=self.red_pen, name="Noise")
        self.signalCurve = self.psdPlot.plot(x=initdata, y=initdata, pen=self.blue_pen, name="Signal")

        self.plotLayoutWidget.addItem(self.psdPlot, 0, 0)

        label_f1 = QLabel('f1')
        label_f1.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.f1_Spin = QDoubleSpinBox()
        self.f1_Spin.setDecimals(5)
        self.f1_Spin.setMinimum(0.00001)
        self.f1_Spin.setMaximum(10000)
        self.f1_Spin.setSingleStep(0.1)
        self.f1_Spin.setSuffix(' Hz')
        self.f1_Spin.setValue(10**(self.psdPlot.getFreqRegion().getRegion()[0]))

        label_f2 = QLabel('f2')
        label_f2.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.f2_Spin = QDoubleSpinBox()
        self.f2_Spin.setDecimals(5)
        self.f2_Spin.setMinimum(0.00002)
        self.f2_Spin.setMaximum(10000)
        self.f2_Spin.setSingleStep(0.1)
        self.f2_Spin.setSuffix(' Hz')
        self.f2_Spin.setValue(10**(self.psdPlot.getFreqRegion().getRegion()[1]))

        set_filter_button = QPushButton('<- Set filter to ->')
        set_filter_button.clicked.connect(self.setFilterFromPSD)

        f_indicator_layout = QHBoxLayout()
        f_indicator_layout.addWidget(label_f1)
        f_indicator_layout.addWidget(self.f1_Spin)
        f_indicator_layout.addStretch()
        f_indicator_layout.addWidget(set_filter_button)
        f_indicator_layout.addStretch()
        f_indicator_layout.addWidget(label_f2)
        f_indicator_layout.addWidget(self.f2_Spin)

        mainLayout = QVBoxLayout()
        mainLayout.addWidget(self.plotLayoutWidget)
        mainLayout.addLayout(f_indicator_layout)

        self.setLayout(mainLayout)

        self.connectSignalsAndSlots()

    def update_theme(self, t: str):
        """
        update the theme of the widget

        :param t: 'light' or 'dark'
        """
        if t == 'light':
            self.plotLayoutWidget.setBackground((255, 255, 255))
        elif t == 'dark':
            self.plotLayoutWidget.setBackground(utils.ip_dark_grey)

    def set_controlling_widget(self, widget):
        """
        set the controlling settings widget

        :param widget: settings widget
        """
        self.settings_widget = widget

    def connectSignalsAndSlots(self):
        """
        connect signals with widgets
        """
        self.psdPlot.getFreqRegion().sigRegionChanged.connect(self.updateFrequencyIndicators)
        self.f1_Spin.editingFinished.connect(self.updateLinearFrequencyIndicators)
        self.f2_Spin.editingFinished.connect(self.updateLinearFrequencyIndicators)

    def updatePSDs(self):
        """
        Use this convenience method to update both PSDs when parameters in this widget are changed
        Use the other individual functions for passing data when the waveform linearregionitems are resized
        or when a different plot is activated
        """
        self.updateSignalPSD()
        self.updateNoisePSD()

    def updateNoisePSD(self, data=None):
        """
        update the noise PSD

        :param data: optional new data to use
        """
        # if new data is passed, use that, otherwise use what we have
        if data is not None:
            self.currentNoiseData = data.copy()

        if self.currentNoiseData is not None:
            f, pxx = self.calculate_psd(self.currentNoiseData)
            self.noiseCurve.setData(f, 10*np.log10(pxx), pen=self.red_pen)

    def updateSignalPSD(self, data=None):
        """
        update the signal PSD

        :param data: optional new data to use
        """
        # if new data s passed, use that, otherwise use what we have
        if data is not None:
            self.currentSignalData = data.copy()

        if self.currentSignalData is not None:
            f, pxx = self.calculate_psd(self.currentSignalData)
            self.signalCurve.setData(f, 10*np.log10(pxx), pen=self.blue_pen)

    def calculate_psd(self, data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        calculate the PSD of the data

        :param data: data to calculate PSD for
        :return: frequencies and PSD values
        """
        if data is not None:
            my_window = self.settings_widget.window_cb.currentText()

            my_nperseg = self.settings_widget.fft_N_Spin.value()
            if my_nperseg > len(data):
                my_nperseg = len(data)

            my_fs = self.settings_widget.fs_Spin.value()

            my_noverlap = int(my_nperseg / 2)

            f, pxx = signal.welch(data, my_fs, my_window, nperseg=my_nperseg, noverlap=my_noverlap)

            return f, pxx
        # if here, data is invalid
        return None, None

    def set_title(self, title: str):
        """
        set the title of the PSD plot

        :param title: title string
        """
        self.psdPlot.setTitle(title)

    @pyqtSlot(tuple)
    def updateFrequencyIndicators(self, region):
        """
        update the frequency indicators based on the region

        :param region: region object
        """
        r = region.getRegion()
        self.f1_Spin.setValue(10**r[0])
        self.f2_Spin.setValue(10**r[1])

    def updateLinearFrequencyIndicators(self):
        """
        update the frequency indicators
        """
        self.psdPlot.getFreqRegion().setRegion([np.log10(self.f1_Spin.value()), np.log10(self.f2_Spin.value())])

    def updateFreqRange(self, rgn: Tuple[float, float]):
        """
        update the frequency range

        :param rgn: range tuple
        """
        self.f1_Spin.setValue(rgn[0])
        self.f2_Spin.setValue(rgn[1])
        self.psdPlot.getFreqRegion().setRegion([np.log10(self.f1_Spin.value()), np.log10(self.f2_Spin.value())])

    def setFilterFromPSD(self):
        """
        set the filter settings from the PSD frequency region
        """
        filterSettings = self.parent.filterSettingsWidget.get_filter_settings()
        _ = self.parent.filterSettingsWidget.get_filter_display_settings()
        filterSettings['type'] = 'Band Pass'
        filterSettings['F_low'] = self.f2_Spin.value()
        filterSettings['F_high'] = self.f1_Spin.value()
        self.parent.filterSettingsWidget.set_filter_settings(filterSettings)

    def clearPlot(self):
        """
        clear plot
        """
        self.noiseCurve.setData([1], [1])
        self.signalCurve.setData([1], [1])
        self.set_title('...')
