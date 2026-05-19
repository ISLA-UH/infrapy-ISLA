
from PyQt5.QtWidgets import (QCheckBox, QComboBox, QLabel, QDoubleSpinBox, QHBoxLayout,
                             QSpinBox, QPushButton, QFormLayout, QGridLayout, QListWidget,
                             QListWidgetItem, QVBoxLayout, QAbstractSpinBox)

from PyQt5.QtCore import pyqtSignal, pyqtSlot, QSettings, Qt

from InfraView.widgets import IPBaseWidgets

class IPWaveformSettingsWidget(IPBaseWidgets.IPSettingsWidget):

    def __init__(self, parent):
        super().__init__(parent=parent)
        self.parent = parent
        self.buildUI()

    def buildUI(self):
        self.filterSettingsWidget = IPFilterSettingsWidget(parent=self, title='Filter')
        self.psdSettingsWidget = IPPSDSettingsWidget(title="PSD")
        self.decimateSettingsWidget = IPDecimateSettingsWidget(parent=self, title='Decimate')

        layout = QHBoxLayout()
        layout.addWidget(self.filterSettingsWidget)
        layout.addWidget(self.decimateSettingsWidget)
        layout.addWidget(self.psdSettingsWidget)
        layout.addStretch()

        self.setLayout(layout)

    @pyqtSlot(tuple)
    def update_signal_range(self, r):
        self.sig_range = r

    @pyqtSlot(tuple)
    def update_noise_range(self, r):
        self.noise_range = r
        
    def to_dict(self):
        # used when saving to config settings
        psd_dict = self.psdSettingsWidget.to_dict()
        filter_dict = self.filterSettingsWidget.to_dict()
        decimate_dict = self.decimateSettingsWidget.to_dict()
        return {'psd_dict': psd_dict, 'filter_dict': filter_dict, 'decimate_dict': decimate_dict}

    def from_dict(self, s_dict):
        sd = s_dict['waveforms_widget']
        # used when loading new config settings
        self.psdSettingsWidget.from_dict(sd)
        self.filterSettingsWidget.from_dict(sd)
        if 'decimate_dict' in sd:
            self.decimateSettingsWidget.from_dict(sd)

class IPPSDSettingsWidget(IPBaseWidgets.IPSettingsGroupBox):

    def __init__(self, parent=None, title=""):
        super().__init__()
        self.parent=parent
        self.setTitle(title)
        self. windows = ['hann', 'hamming', 'boxcar', 'bartlett', 'blackman']
        self.buildUI()

    def buildUI(self):
        label_fft_N = QLabel(self.tr('fft window (N): '))
        label_fft_N.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.fft_N_Spin = QSpinBox()
        self.fft_N_Spin.setMinimum(4)
        self.fft_N_Spin.setMaximum(2**20)
        self.fft_N_Spin.setValue(1024)

        label_fs = QLabel(self.tr('Sampling Freq.: '))
        label_fs.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.fs_Spin = QDoubleSpinBox()
        self.fs_Spin.setMaximum(1000000.0)
        self.fs_Spin.setMinimum(0.0)
        self.fs_Spin.setValue(20.0)
        self.fs_Spin.setReadOnly(True)
        self.fs_Spin.setSuffix(' Hz')
        self.fs_Spin.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.fs_Spin.setEnabled(False)

        label_fft_time = QLabel(self.tr('fft window: '))
        label_fft_time.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.fft_T_Spin = QDoubleSpinBox()
        self.fft_T_Spin.setMaximum(10000.)
        self.fft_T_Spin.setMinimum(0.1)
        self.fft_T_Spin.setValue(1.0)
        self.fft_T_Spin.setSuffix(' s')

        self.fft_N_Spin.valueChanged.connect(self.updateFFtT)
        self.fft_T_Spin.valueChanged.connect(self.updateFFtN)

        label_window = QLabel(self.tr('Window: '))
        label_window.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.window_cb = QComboBox()
        for window in self.windows:
            self.window_cb.addItem(window)

        parametersLayout = QFormLayout()
        parametersLayout.addRow(label_fs, self.fs_Spin)
        parametersLayout.addRow(label_fft_N, self.fft_N_Spin)
        parametersLayout.addRow(label_fft_time, self.fft_T_Spin)
        parametersLayout.addRow(label_window, self.window_cb)

        self.setLayout(parametersLayout)

    def to_dict(self):
        s_dict = {}
        s_dict['fft_n'] = self.fft_N_Spin.value()
        #s_dict['fs'] = self.fs_Spin.value()
        #s_dict['fft_T'] = self.fft_T_Spin.value() 
        s_dict['window'] = self.window_cb.currentText()
        return s_dict

    def from_dict(self, s_dict):
        sd = s_dict['psd_dict']
        self.fft_N_Spin.setValue(int(sd['fft_n']))
        # self.fs_Spin.setValue(s_dict['fs'])
        # self.fft_T_Spin.setValue(s_dict['fft_T'])
        self.window_cb.setCurrentText(sd['window'])

    def set_fs(self, fs):
        self.fs_Spin.setValue(fs)
        self.updateFFtT()

    def updateFFtT(self):
        self.fft_T_Spin.setValue(self.fft_N_Spin.value() / self.fs_Spin.value())

    def updateFFtN(self):
        self.fft_N_Spin.setValue(int(self.fft_T_Spin.value() * self.fs_Spin.value()))

    

class IPFilterSettingsWidget(IPBaseWidgets.IPSettingsGroupBox):

    filterChanged = pyqtSignal()
    sig_filter_changed = pyqtSignal(dict)
    sig_filter_display_changed = pyqtSignal(dict)

    filter_display_settings = {}  # Holder of the current filter display settings

    filter_display_settings_default = {'apply': False, 'showUnfiltered': False}

    filter_settings = {}  # Holder of the current filter settings

    filter_settings_default = {'type': 'Band Pass', 'F_low': 5.0, 'F_high': .5,
                                'order': 4, 'zphase': False}

    def __init__(self, parent=None, title=""):

        super().__init__()

        self.parent = parent
        self.setTitle(title)
        self.filter_settings = self.filter_settings_default.copy()
        self.filter_display_settings = self.filter_display_settings_default.copy()
        self.__buildUI__()
        self.show()

    def __buildUI__(self):

        self.applyFilter_checkbox = QCheckBox('Apply Filter?')
        self.applyFilter_checkbox.setChecked(self.filter_display_settings['apply'])
        self.applyFilter_checkbox.stateChanged.connect(self.apply_filter)

        self.showUnfiltered = QCheckBox('Show Unfiltered?')
        self.showUnfiltered.setChecked(self.filter_display_settings['showUnfiltered'])
        self.showUnfiltered.stateChanged.connect(self.onActivated_showUnfiltered)

        self.cb_filter_type = QComboBox()
        #self.cb_filter_type.addItem('Low Pass')
        #self.cb_filter_type.addItem('High Pass')
        self.cb_filter_type.addItem('Band Pass')

        cb_idx = self.cb_filter_type.findText(self.filter_settings['type'])
        self.cb_filter_type.setCurrentIndex(cb_idx)
        self.cb_filter_type.currentIndexChanged[str].connect(self.onActivated_cb)

        self.label_lowpassFreq = QLabel(self.tr('Low Pass F: '))
        self.lowpassSpin = QDoubleSpinBox()
        self.lowpassSpin.setDecimals(5)
        self.lowpassSpin.setValue(self.filter_settings['F_low'])
        self.lowpassSpin.setMaximum(100000)
        self.lowpassSpin.setMinimum(.00002)
        self.lowpassSpin.setSingleStep(.1)
        self.lowpassSpin.setSuffix(' Hz')
        self.lowpassSpin.valueChanged.connect(self.onActivated_lpSpin)

        self.label_highpassFreq = QLabel(self.tr('High Pass F: '))
        self.highpassSpin = QDoubleSpinBox()
        self.highpassSpin.setDecimals(5)
        self.highpassSpin.setValue(self.filter_settings['F_high'])
        self.highpassSpin.setMaximum(100000)
        self.highpassSpin.setMinimum(.00001)
        self.highpassSpin.setSingleStep(.1)
        self.highpassSpin.setSuffix(' Hz')
        self.highpassSpin.valueChanged.connect(self.onActivated_hpSpin)

        self.label_order = QLabel(self.tr('Order: '))
        self.orderSpin = QSpinBox()
        self.orderSpin.setMinimum(1)
        self.orderSpin.setValue(self.filter_settings['order'])

        self.zeroPhase_checkbox = QCheckBox(self.tr('Zero Phase'))
        self.zeroPhase_checkbox.setChecked(self.filter_settings['zphase'])

        self.update_Button = QPushButton('Update')
        self.update_Button.setMaximumWidth(200)
        self.update_Button.clicked.connect(self.update_clicked)

        col1_layout = QFormLayout()
        cm = col1_layout.contentsMargins()
        cm.setRight(40)
        col1_layout.setContentsMargins(cm)
        col1_layout.addRow(self.tr('Type: '), self.cb_filter_type)
        col1_layout.addRow(self.tr('High Pass F: '), self.highpassSpin)
        col1_layout.addRow(self.tr('Low Pass F: '), self.lowpassSpin)
        col1_layout.addRow(self.tr('Order: '), self.orderSpin)

        col2_layout = QVBoxLayout()
        col2_layout.addWidget(self.applyFilter_checkbox)
        col2_layout.addWidget(self.zeroPhase_checkbox)
        col2_layout.addWidget(self.showUnfiltered)
        col2_layout.addWidget(self.update_Button)
        col2_layout.addStretch()

        layout = QHBoxLayout()
        # default layout seems to squish the columns together too close, 
        # so lets increase the right content margin
        layout.addLayout(col1_layout)
        layout.addLayout(col2_layout)

        self.setLayout(layout)

        # default setting is to disable all inputs except for the applyFilter checkbox
        self.disableAll()

    def to_dict(self):
        s_dict = {}
        s_dict['apply_filter'] = self.applyFilter_checkbox.isChecked()
        s_dict['show_unfiltered'] = self.showUnfiltered.isChecked()
        s_dict['filter_type'] = self.cb_filter_type.currentText()
        s_dict['lowpass'] = self.lowpassSpin.value()
        s_dict['highpass'] = self.highpassSpin.value()
        s_dict['order'] = self.orderSpin.value()
        s_dict['zero_phase'] = self.zeroPhase_checkbox.isChecked()
        return s_dict

    def from_dict(self, s_dict):
        bool_map = {"True": True, "False": False}

        sd = s_dict['filter_dict']
        self.applyFilter_checkbox.setChecked(bool_map[sd['apply_filter']])
        self.cb_filter_type.setCurrentText(sd['filter_type'])
        self.orderSpin.setValue(int(sd['order']))
        self.zeroPhase_checkbox.setChecked(bool_map[sd['zero_phase']])
        self.showUnfiltered.setChecked(bool_map[sd['show_unfiltered']])

        # self.lowpassSpin.setValue(s_dict['lowpass'])
        # self.highpassSpin.setValue(s_dict['highpass'])
        

    def onActivated_cb(self, text):
        self.filter_settings['type'] = text

        if text == 'Low Pass' or text == 'Low Pass Cheby2' or text == 'Low Pass Fir':
            # disable the highpass freq. spin
            self.label_highpassFreq.setEnabled(False)
            self.highpassSpin.setEnabled(False)
            # make sure the lowpass freq. spin is enabled
            self.label_lowpassFreq.setEnabled(True)
            self.lowpassSpin.setEnabled(True)
        elif text == 'High Pass':
            # enable the high pass freq. spin
            self.label_highpassFreq.setEnabled(True)
            self.highpassSpin.setEnabled(True)
            # make sure the lowpass freq. spin is disabled
            self.label_lowpassFreq.setEnabled(False)
            self.lowpassSpin.setEnabled(False)
        elif text == 'Band Pass':
            # enable bothsts, sts_filtered, normalize=False
            self.label_highpassFreq.setEnabled(True)
            self.highpassSpin.setEnabled(True)
            self.label_lowpassFreq.setEnabled(True)
            self.lowpassSpin.setEnabled(True)
        else:
            # something weird is happening, just bail
            return

        # since something changed, we need to make sure the update button is enabled    
        self.update_Button.setEnabled(True)

    def onActivated_showUnfiltered(self):
        self.filter_display_settings['showUnfiltered'] = self.showUnfiltered.isChecked()
        self.sig_filter_display_changed.emit(self.filter_display_settings)

    def update_clicked(self):
        self.sig_filter_changed.emit(self.filter_settings)
        # self.parent.spectraWidget.updateFreqRange((self.highpassSpin.value(), self.lowpassSpin.value()))
    
    def onActivated_zeroPhase(self, int):
        self.filter_settings['zphase'] = self.zeroPhase_checkbox.isChecked()

    def onActivated_lpSpin(self, float):
        self.filter_settings['F_low'] = self.lowpassSpin.value()

    def onActivated_hpSpin(self, float):
        self.filter_settings['F_high'] = self.highpassSpin.value()

    def enableAll(self):
        # This enables all of the appropriate inputs
        self.cb_filter_type.setEnabled(True)
        self.label_order.setEnabled(True)
        self.orderSpin.setEnabled(True)
        self.onActivated_cb(self.filter_settings['type'])
        self.zeroPhase_checkbox.setEnabled(True)
        self.showUnfiltered.setEnabled(True)
        self.update_Button.setEnabled(True)

    def disableAll(self):
        # This disables all the inputs EXCEPT for the applyFilter checkbox
        self.cb_filter_type.setEnabled(False)
        self.lowpassSpin.setEnabled(False)
        self.highpassSpin.setEnabled(False)
        self.label_highpassFreq.setEnabled(False)
        self.label_lowpassFreq.setEnabled(False)
        self.label_order.setEnabled(False)
        self.orderSpin.setEnabled(False)
        self.zeroPhase_checkbox.setEnabled(False)
        self.showUnfiltered.setEnabled(False)
        self.update_Button.setEnabled(False)

    def apply_filter(self, state):

        if state == 2:
            self.filter_display_settings['apply'] = True
            self.enableAll()
        else:
            self.filter_display_settings['apply'] = False

        self.sig_filter_changed.emit(self.filter_settings)
        self.sig_filter_display_changed.emit(self.filter_display_settings)

    def resetfilter_settings(self):
        self.filter_settings = self.filter_settings_default.copy()
        self.filter_display_settings = self.filter_display_settings_default.copy()

        self.updateWidget()
        self.disableAll()

    def get_filter_settings(self):
        return self.filter_settings

    def get_filter_display_settings(self):
        return self.filter_display_settings

    def set_filter_settings(self, settings):
        self.filter_settings = settings
        self.sig_filter_changed.emit(settings)
        self.update_widget()

    def update_widget(self):
        # when filter settings are changed programatically, update the widget to show current settings

        self.applyFilter_checkbox.setChecked(self.filter_display_settings['apply'])
        self.showUnfiltered.setChecked(self.filter_display_settings['showUnfiltered'])

        cb_idx = self.cb_filter_type.findText(self.filter_settings['type'])
        self.cb_filter_type.setCurrentIndex(cb_idx)

        self.lowpassSpin.setValue(self.filter_settings['F_low'])
        self.highpassSpin.setValue(self.filter_settings['F_high'])
        self.orderSpin.setValue(self.filter_settings['order'])
        self.zeroPhase_checkbox.setChecked(self.filter_settings['zphase'])

    def save_current_filter(self):
        newSettings = QSettings('LANL', 'IPView')
        newFilterName = "Billy"
        newFilterKey = newFilterName + "/FilterType"
        newSettings.setValue("newFilterKey", "Butterworth")

    def refresh_filter_entries(self):
        self.cb_filter_type.setCurrentText(self.filter_settings['type'])
        self.lowpassSpin.setValue(self.filter_settings['F_low'])
        self.highpassSpin.setValue(self.filter_settings['F_high'])
        self.orderSpin.setValue(self.filter_settings['order'])
        self.zeroPhase_checkbox.setChecked(self.filter_settings['zphase'])


class IPDecimateSettingsWidget(IPBaseWidgets.IPSettingsGroupBox):
    """
    Decimation settings widget.

    Emits sig_decimate_changed(dict) with keys:
        'apply'  : bool
        'passes' : list of dicts, each with keys:
                     'factor'           : int
                     'detrend_type'     : str
                     'taper_type'       : str
                     'taper_percentage' : float
    """

    sig_decimate_changed = pyqtSignal(dict)

    decimate_settings_default = {
        'apply': False,
        'passes': [],
    }

    def __init__(self, parent=None, title=''):
        super().__init__()
        self.parent = parent
        self.setTitle(title)
        self.decimate_settings = self.decimate_settings_default.copy()
        self.decimate_settings['passes'] = []
        self.__buildUI__()
        self.show()

    def __buildUI__(self):
        self.applyDecimate_checkbox = QCheckBox('Apply Decimate?')
        self.applyDecimate_checkbox.setChecked(self.decimate_settings['apply'])
        self.applyDecimate_checkbox.stateChanged.connect(self._on_apply_changed)

        label_factor = QLabel(self.tr('Factor:'))
        self.factorSpin = QSpinBox()
        self.factorSpin.setMinimum(2)
        self.factorSpin.setMaximum(16)
        self.factorSpin.setValue(2)

        self.detrendType_cb = QComboBox()
        self.detrendType_cb.addItems(['none', 'linear', 'demean', 'simple'])
        self.detrendType_cb.setCurrentText('linear')

        self.taperType_cb = QComboBox()
        self.taperType_cb.addItems(['none', 'cosine', 'hann', 'hamming', 'boxcar', 'bartlett', 'blackman'])
        self.taperType_cb.setCurrentText('hann')
        self.taperType_cb.currentTextChanged.connect(self._on_taper_type_changed)

        self.taperPercentage_spin = QDoubleSpinBox()
        self.taperPercentage_spin.setDecimals(3)
        self.taperPercentage_spin.setMinimum(0.0)
        self.taperPercentage_spin.setMaximum(0.5)
        self.taperPercentage_spin.setSingleStep(0.01)
        self.taperPercentage_spin.setValue(0.05)

        self.addFactor_button = QPushButton('Add Iteration')
        self.addFactor_button.clicked.connect(self._on_add_factor)

        self.removeLast_button = QPushButton('Remove Last')
        self.removeLast_button.clicked.connect(self._on_remove_last)

        self.clearAll_button = QPushButton('Clear All')
        self.clearAll_button.clicked.connect(self._on_clear_all)

        self.passesList = QListWidget()
        self.passesList.setMaximumHeight(100)

        self.update_button = QPushButton('Update')
        self.update_button.setMaximumWidth(200)
        self.update_button.clicked.connect(self._on_update_clicked)

        col1 = QFormLayout()
        cm = col1.contentsMargins()
        cm.setRight(40)
        col1.setContentsMargins(cm)
        col1.addRow(QLabel('Detrend:'), self.detrendType_cb)
        col1.addRow(QLabel('Taper:'), self.taperType_cb)
        self.taperPercentage_label = QLabel('Taper %:')
        col1.addRow(self.taperPercentage_label, self.taperPercentage_spin)
        col1.addRow(label_factor, self.factorSpin)
        col1.addRow(QLabel('Iterations:'), self.passesList)

        col2 = QVBoxLayout()
        col2.addWidget(self.applyDecimate_checkbox)
        col2.addWidget(self.addFactor_button)
        col2.addWidget(self.removeLast_button)
        col2.addWidget(self.clearAll_button)
        col2.addWidget(self.update_button)
        col2.addStretch()

        layout = QHBoxLayout()
        layout.addLayout(col1)
        layout.addLayout(col2)
        self.setLayout(layout)

        self.disableAll()

    # --- internal helpers ---

    def _refresh_passes_list(self):
        self.passesList.clear()
        for i, p in enumerate(self.decimate_settings['passes']):
            taper = p.get('taper_type', 'none')
            taper_pct = p.get('taper_percentage', 0.05)
            taper_str = f'{taper}({taper_pct * 100:.1f}%)' if taper != 'none' else 'none'
            detrend = p.get('detrend_type', 'none')
            factor = p.get('factor', 2)
            self.passesList.addItem(QListWidgetItem(f'I{i + 1}: ×{factor} | {detrend} | {taper_str}'))

    # --- slots ---

    def _on_apply_changed(self, state: int):
        if state == 2:
            self.decimate_settings['apply'] = True
            self.enableAll()
        else:
            self.decimate_settings['apply'] = False
            self.disableAll()
        self.sig_decimate_changed.emit(self.decimate_settings)

    def _on_add_factor(self):
        self.decimate_settings['passes'].append({
            'factor': self.factorSpin.value(),
            'detrend_type': self.detrendType_cb.currentText(),
            'taper_type': self.taperType_cb.currentText(),
            'taper_percentage': self.taperPercentage_spin.value(),
        })
        self._refresh_passes_list()
        self.update_button.setEnabled(True)

    def _on_remove_last(self):
        if self.decimate_settings['passes']:
            self.decimate_settings['passes'].pop()
            self._refresh_passes_list()

    def _on_clear_all(self):
        self.decimate_settings['passes'] = []
        self._refresh_passes_list()

    def _on_update_clicked(self):
        self.sig_decimate_changed.emit(self.decimate_settings)

    def _on_taper_type_changed(self, taper_type: str):
        self._update_taper_percentage_enabled()

    def _update_taper_percentage_enabled(self):
        taper_enabled = self.applyDecimate_checkbox.isChecked() and self.taperType_cb.currentText() != 'none'
        self.taperPercentage_spin.setEnabled(taper_enabled)
        self.taperPercentage_label.setEnabled(taper_enabled)

    # --- enable / disable ---

    def enableAll(self):
        self.detrendType_cb.setEnabled(True)
        self.taperType_cb.setEnabled(True)
        self.factorSpin.setEnabled(True)
        self.addFactor_button.setEnabled(True)
        self.removeLast_button.setEnabled(True)
        self.clearAll_button.setEnabled(True)
        self.passesList.setEnabled(True)
        self.update_button.setEnabled(True)
        self._update_taper_percentage_enabled()

    def disableAll(self):
        self.detrendType_cb.setEnabled(False)
        self.taperType_cb.setEnabled(False)
        self.taperPercentage_spin.setEnabled(False)
        self.taperPercentage_label.setEnabled(False)
        self.factorSpin.setEnabled(False)
        self.addFactor_button.setEnabled(False)
        self.removeLast_button.setEnabled(False)
        self.clearAll_button.setEnabled(False)
        self.passesList.setEnabled(False)
        self.update_button.setEnabled(False)

    # --- public API ---

    def get_decimate_settings(self) -> dict:
        return self.decimate_settings

    def update_widget(self):
        self.applyDecimate_checkbox.setChecked(self.decimate_settings['apply'])
        self._refresh_passes_list()
        if self.decimate_settings['apply']:
            self.enableAll()
        else:
            self.disableAll()
        self._update_taper_percentage_enabled()

    def reset_decimate_settings(self):
        self.decimate_settings = self.decimate_settings_default.copy()
        self.decimate_settings['passes'] = []
        self.update_widget()
        self.disableAll()

    def to_dict(self) -> dict:
        return {
            'apply': self.applyDecimate_checkbox.isChecked(),
            'passes': [dict(p) for p in self.decimate_settings['passes']],
        }

    def from_dict(self, s_dict: dict):
        bool_map = {'True': True, 'False': False}
        sd = s_dict.get('decimate_dict', {})
        if not sd:
            return
        apply_val = sd.get('apply', False)
        if isinstance(apply_val, str):
            apply_val = bool_map.get(apply_val, False)
        self.decimate_settings['apply'] = apply_val
        # Support old format where 'factors' was a flat list of ints
        if 'passes' in sd:
            passes = []
            for p in sd['passes']:
                try:
                    taper_pct = float(p.get('taper_percentage', 0.05))
                except (TypeError, ValueError):
                    taper_pct = 0.05
                passes.append({
                    'factor': int(p.get('factor', 2)),
                    'detrend_type': p.get('detrend_type', 'linear'),
                    'taper_type': p.get('taper_type', 'hann'),
                    'taper_percentage': taper_pct,
                })
            self.decimate_settings['passes'] = passes
        elif 'factors' in sd:
            # Backward-compat: promote old flat factors to passes with defaults
            self.decimate_settings['passes'] = [
                {'factor': int(f), 'detrend_type': 'linear', 'taper_type': 'hann', 'taper_percentage': 0.05}
                for f in sd.get('factors', [])
            ]
        self.update_widget()