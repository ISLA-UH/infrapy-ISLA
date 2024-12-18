from PyQt5.QtWidgets import (QGroupBox, QComboBox, QCheckBox, QLabel, QDoubleSpinBox, QSpinBox,
                             QHBoxLayout, QFormLayout, QFrame, QPushButton)
from PyQt5 import QtCore

import pyqtgraph as pg

from InfraView.widgets import IPBaseWidgets
from InfraView.widgets import IPPolarPlot
from InfraView.widgets import IPDetectorSettingsWidget

class IPBeamformingSettingsWidget(IPBaseWidgets.IPSettingsWidget):

    def __init__(self, parent):
        super().__init__()

        self.buildUI()

    def buildUI(self):

        self.windowLength_spin = QDoubleSpinBox()
        self.windowLength_spin.setMaximumWidth(60)
        self.windowLength_spin.setSuffix(' s')
        self.windowLength_spin.setMinimum(0.0)
        self.windowLength_spin.setMaximum(1000000)

        self.windowStep_spin = QDoubleSpinBox()
        self.windowStep_spin.setMaximumWidth(60)
        self.windowStep_spin.setSuffix(' s')
        self.windowStep_spin.setMinimum(0.01)
        self.windowStep_spin.setMaximum(1000000)

        self.numSigs_spin = QSpinBox()
        self.numSigs_spin.setMaximumWidth(40)
        self.numSigs_spin.setMinimum(1)
        self.numSigs_spin.setEnabled(False)

        self.method_cb = QComboBox()
        self.method_cb.addItem('bartlett')
        self.method_cb.addItem('gls')
        self.method_cb.addItem('bartlett_covar')
        #self.method_cb.addItem('capon')
        #self.method_cb.addItem('music')
        self.method_cb.currentTextChanged.connect(self.methodChanged)

        self.fmin_label = QLabel("0.5 Hz") # if changed here, make sure you change in the IPPSDWidget
        self.fmin_label.setMinimumWidth(90)
        self.fmax_label = QLabel("5.0 Hz")
        self.fmax_label.setMinimumWidth(90)   

        self.noiseStart_label = QLabel("0.0")
        self.noiseDuration_label = QLabel("0.0")

        self.sigStart_label = QLabel("0.0")
        self.sigDuration_label = QLabel("0.0")

        self.subwindow_cb = QCheckBox()
        self.subwindow_cb.stateChanged.connect(self.updateSubwindow)

        self.subWinLength_spin = QDoubleSpinBox()
        self.subWinLength_spin.setMaximumWidth(60)
        self.subWinLength_spin.setMinimum(0.0)
        self.subWinLength_spin.setMaximum(1000000)
        self.subWinLength_spin.setSuffix(' s')
        self.subWinLength_spin.setEnabled(False)

        self.backaz_resol_spin = QDoubleSpinBox()
        self.backaz_resol_spin.setMinimum(0.1)
        self.backaz_resol_spin.setMaximum(20.)
        self.backaz_resol_spin.setSuffix(' deg')

        self.tracev_resol_spin = QDoubleSpinBox()
        self.tracev_resol_spin.setMinimum(0.1)
        self.tracev_resol_spin.setMaximum(500.)
        self.tracev_resol_spin.setSuffix(' m/s')

        self.backaz_start_spin = QDoubleSpinBox()
        self.backaz_start_spin.setMinimum(-180.0)
        self.backaz_start_spin.setMaximum(179.0)
        self.backaz_start_spin.setSuffix(' deg')
        self.backaz_start_spin.editingFinished.connect(self.checkBackAzRange)

        self.backaz_end_spin = QDoubleSpinBox()
        self.backaz_end_spin.setMinimum(-179.0)
        self.backaz_end_spin.setMaximum(180.0)
        self.backaz_end_spin.setSuffix(' deg')
        self.backaz_end_spin.editingFinished.connect(self.checkBackAzRange)

        self.tracev_min_spin = QDoubleSpinBox()
        self.tracev_min_spin.setMinimum(1)
        self.tracev_min_spin.setMaximum(20000.)
        self.tracev_min_spin.setSuffix(' m/s')
        self.tracev_min_spin.editingFinished.connect(self.checkTraceVRange)
        
        self.tracev_max_spin = QDoubleSpinBox()
        self.tracev_max_spin.setMinimum(2)
        self.tracev_max_spin.setMaximum(20000.)
        self.tracev_max_spin.setSuffix(' m/s')
        self.tracev_max_spin.editingFinished.connect(self.checkTraceVRange)

        #slowness colormap
        self.colormap_cb = QComboBox()
        available_maps = pg.colormap.listMaps(source='matplotlib')
        self.colormap_cb.addItems(available_maps)
        self.colormap_cb.setCurrentText('jet')

        # set everything to default settings
        self.set_defaults()

        self.reset_button = QPushButton("Reset")
        self.reset_button.setToolTip("Reset to default values")
        self.reset_button.clicked.connect(self.set_defaults)

        formlayout_col2 = QFormLayout()
        formlayout_col2.addRow("Window Length: ", self.windowLength_spin)
        formlayout_col2.addRow("Window Step: ", self.windowStep_spin)
        sub_win_layout = QHBoxLayout()
        sub_win_layout.addWidget(self.subWinLength_spin)
        sub_win_layout.addWidget(self.subwindow_cb)
        formlayout_col2.addRow("Subwindow Length: ", sub_win_layout)
        formlayout_col2.addRow("Method: ", self.method_cb)

        formlayout_col6 = QFormLayout()
        formlayout_col6.addRow("Back Az. Resolution: ", self.backaz_resol_spin)
        formlayout_col6.addRow("Back Az. Start Angle: ", self.backaz_start_spin)
        formlayout_col6.addRow("Back Az. End Angle: ", self.backaz_end_spin)
        formlayout_col6.addRow("Slowness Color Map: ", self.colormap_cb)

        formlayout_col7 = QFormLayout()
        formlayout_col7.addRow("Trace Vel. Resolution: ", self.tracev_resol_spin)
        formlayout_col7.addRow("Trace Vel Min: ", self.tracev_min_spin)
        formlayout_col7.addRow("Trace Vel Max: ", self.tracev_max_spin)
        formlayout_col7.addRow("", self.reset_button)

        horizLayoutA = QHBoxLayout()
        horizLayoutA.addLayout(formlayout_col2)
        horizLayoutA.addLayout(formlayout_col6)
        horizLayoutA.addLayout(formlayout_col7)

        analysis_gb = QGroupBox('Analysis Settings')
        analysis_gb.setLayout(horizLayoutA)
        # removed col3

        formlayout_col4 = QFormLayout()
        formlayout_col4.addRow("Freq Min: ", self.fmin_label)
        formlayout_col4.addRow("Noise Range Start: ", self.noiseStart_label)
        formlayout_col4.addRow("Signal Range Start: ", self.sigStart_label)

        formlayout_col5 = QFormLayout()
        formlayout_col5.addRow("Freq Max: ", self.fmax_label)
        formlayout_col5.addRow("Duration: ", self.noiseDuration_label)
        formlayout_col5.addRow("Duration: ", self.sigDuration_label)

        horizLayoutB = QHBoxLayout()
        horizLayoutB.addLayout(formlayout_col4)
        horizLayoutB.addLayout(formlayout_col5)

        values_gb = QGroupBox("Current Values")
        values_gb.setLayout(horizLayoutB)
        values_gb.setVisible(False)

        self.detector_settings = IPDetectorSettingsWidget.IPDetectorSettingsWidget(self)

        #self.slowness_settings = IPPolarPlot.IPSlownessSettingsWidget(self)
        #self.slowness_settings = IPSlownessSettingsWidget(self)

        main_layout = QHBoxLayout()
        main_layout.addWidget(analysis_gb)
        main_layout.addWidget(values_gb)
        main_layout.addWidget(self.detector_settings)
        #main_layout.addWidget(self.slowness_settings)
        main_layout.addStretch()

        self.setLayout(main_layout)

    def to_dict(self):
        print(self.sigStart_label.text())
        s_dict = {}
        s_dict['win_length']  = self.windowLength_spin.value()
        s_dict['win_step'] = self.windowStep_spin.value()
        s_dict['num_sigs'] = self.numSigs_spin.value()
        s_dict['method'] = self.method_cb.currentText()
        s_dict['sub_win_check'] = self.subwindow_cb.isChecked()
        s_dict['sub_win_length'] = self.subWinLength_spin.value()
        s_dict['backAz_resolution'] = self.backaz_resol_spin.value()
        s_dict['backAz_start'] = self.backaz_start_spin.value()
        s_dict['backAz_end'] = self.backaz_end_spin.value()
        s_dict['traceV_resolution'] = self.tracev_resol_spin.value()
        s_dict['traceV_min'] = self.tracev_min_spin.value()
        s_dict['traceV_max'] = self.tracev_max_spin.value()
        s_dict['signal_start'] = self.sigStart_label.text()
        s_dict['signal_end'] = float(self.sigStart_label.text()) + float(self.sigDuration_label.text())
        s_dict['noise_start'] = self.noiseStart_label.text()
        s_dict['noise_end'] = float(self.noiseStart_label.text()) + float(self.noiseDuration_label.text())
        s_dict['colormap'] = self.colormap_cb.currentText()
        s_dict['detector_settings'] = self.detector_settings.to_dict()

        return s_dict


    def set_defaults(self):
        default_settings = {'winlen_spin': 10.0,
                    'winstep_spin': 2.5,
                    'numSigs_spin': 1,
                    'method_cb': 'bartlett',
                    'subwin_cb_enabled': False,
                    'backazRes_spin': 3.0,
                    'backazStart_spin': -180.0,
                    'backazEnd_spin': 180.0,
                    'traceVelRes_spin': 5.0,
                    'traceVelmin_spin': 300.0,
                    'traceVelmax_spin': 750.0
                    }
        
        self.windowLength_spin.setValue(default_settings['winlen_spin'])
        self.windowStep_spin.setValue(default_settings['winstep_spin'])
        self.numSigs_spin.setValue(default_settings['numSigs_spin'])
        self.method_cb.setCurrentText(default_settings['method_cb'])
        self.subwindow_cb.setEnabled(default_settings['subwin_cb_enabled'])

        self.subWinLength_spin.setValue(self.windowLength_spin.value())
        self.backaz_resol_spin.setValue(default_settings['backazRes_spin'])
        self.backaz_start_spin.setValue(default_settings['backazStart_spin'])
        self.backaz_end_spin.setValue(default_settings['backazEnd_spin'])
        self.tracev_resol_spin.setValue(default_settings['traceVelRes_spin'])
        self.tracev_min_spin.setValue(default_settings['traceVelmin_spin'])
        self.tracev_max_spin.setValue(default_settings['traceVelmax_spin'])
        


    def HLine(self):
        hl = QFrame()
        hl.setFrameShape(QFrame.HLine)
        hl.setFrameShadow(QFrame.Sunken)
        return hl

    def VLine(self):
        vl = QFrame()
        vl.setFrameShape(QFrame.VLine)
        vl.setFrameShadow(QFrame.Sunken)
        return vl

    def setFmin(self, min):
        self.fmin_label.setText("{:.5f} Hz".format(min))

    def setFmax(self, max):
        self.fmax_label.setText("{:.5f} Hz".format(max))

    def getNoiseRange(self):
        return (float(self.noiseStart_label.text()), float(self.noiseStart_label.text()) + float(self.noiseDuration_label.text()))

    def getSignalRange(self):
        return (float(self.sigStart_label.text()), float(self.sigStart_label.text()) + float(self.sigDuration_label.text()))

    def getFreqRange(self):
        # we need to remove the " Hz" from the label strings...
        min = float(self.fmin_label.text()[:-3])
        max = float(self.fmax_label.text()[:-3])
        return (min, max)

    def getWinLength(self):
        return self.windowLength_spin.value()

    def getSubWinLength(self):
        if self.subWinLength_spin.isEnabled():
            return self.subWinLength_spin.value()
        else:
            return None

    def updateSubwindow(self, state):
        self.subWinLength_spin.setEnabled(state)

    def getNumSigs(self):
        if self.numSigs_spin.isEnabled():
            return self.numSigs_spin.value()
        else:
            return 1

    def getWinStep(self):
        return self.windowStep_spin.value()

    def getMethod(self):
        return self.method_cb.currentText()


    def getBackAzResolution(self):
        return self.backaz_resol_spin.value()

    def getBackAzRange(self):
        return (self.backaz_start_spin.value(), self.backaz_end_spin.value())

    @QtCore.pyqtSlot()
    def checkBackAzRange(self):
        start,stop = self.getBackAzRange()
        if start >= stop:
            self.backaz_start_spin.setStyleSheet("color: rgb(200,0,0); ")
            self.backaz_end_spin.setStyleSheet("color: rgb(200,0,0); ")
        else:
            self.backaz_start_spin.setStyleSheet("color: rgb(0, 0, 0);")
            self.backaz_end_spin.setStyleSheet("color: rgb(0, 0, 0);")

    def getTraceVelResolution(self):
        return self.tracev_resol_spin.value()

    def getTraceVRange(self):
        return (self.tracev_min_spin.value(), self.tracev_max_spin.value())

    @QtCore.pyqtSlot()
    def checkTraceVRange(self):
        min, max = self.getTraceVRange()
        if min >= max:
            self.tracev_min_spin.setStyleSheet("color: rgb(200,0,0);")
            self.tracev_max_spin.setStyleSheet("color: rgb(200,0,0);")
        else:
            self.tracev_min_spin.setStyleSheet("color: rgb(0,0,0);")
            self.tracev_max_spin.setStyleSheet("color: rgb(0,0,0);")

    @QtCore.pyqtSlot(tuple)
    def setNoiseValues(self, values):   # values is a tuple containing (start, stop)
        self.noiseStart_label.setText("{:.2f}".format(values[0]))
        self.noiseDuration_label.setText("{:.2f}".format(values[1] - values[0]))

    @QtCore.pyqtSlot(tuple)
    def setSignalValues(self, values):   # values is a tuple containing (start, stop)
        self.sigStart_label.setText("{:.2f}".format(values[0]))
        self.sigDuration_label.setText("{:.2f}".format(values[1] - values[0]))

    @QtCore.pyqtSlot(tuple)
    def setFreqValues(self, IPLinearRegionItem):
        values = IPLinearRegionItem.getRegion()
        self.fmin_label.setText("{:.5f} Hz".format(10**values[0]))
        self.fmax_label.setText("{:.5f} Hz".format(10**values[1]))

    @QtCore.pyqtSlot(str)
    def methodChanged(self, newMethod):
        if newMethod == 'music':
            self.numSigs_spin.setEnabled(True)
        else:
            self.numSigs_spin.setValue(1)
            self.numSigs_spin.setEnabled(False)

        if newMethod == 'music' or newMethod == 'capon' or newMethod == 'bartlett_covar':
            self.subwindow_cb.setEnabled(True)
            self.subWinLength_spin.setEnabled(self.subwindow_cb.isChecked())
        else:
            self.subwindow_cb.setChecked(False)
            self.subwindow_cb.setEnabled(False)
            self.subWinLength_spin.setEnabled(False)



class IPSlownessSettingsWidget(QGroupBox):

    def __init__(self, parent):
        super().__init__(parent)
        self.setTitle("Slowness Plot")
        self.beamformingWidget = parent

        self.buildUI()

    def buildUI(self):
        
        colormap_label = QLabel("Color Map: ")
        self.colormap_cb = QComboBox()

        available_maps = pg.colormap.listMaps(source='matplotlib')
        self.colormap_cb.addItems(available_maps)
        self.colormap_cb.setCurrentText('jet')

        #TODO:  Hardwire resolution?  Currently not displayed
        resolution_label = QLabel("Resolution:")
        self.resolution_spin = QSpinBox()
        self.resolution_spin.setRange(10,1000)
        self.resolution_spin.setMaximumWidth(70)
        self.resolution_spin.setValue(300)
        self.resolution_spin.setToolTip("Number of points (horizontal and vertical) that make up the slowness image.\nIf you want to 'smooth' the plot, reduce the size of the trace velocity step \nsize and the azimuth step size in the beamformer settings.")

        form1_layout = QFormLayout()
        form1_layout.addRow(colormap_label, self.colormap_cb)

        self.setLayout(form1_layout)

    def settings(self):
        '''returns the current settings'''
        settings = {'cmap': self.colormap_cb.currentText()}

        return settings