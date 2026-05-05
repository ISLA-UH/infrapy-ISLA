from PyQt5.QtWidgets import (QWidget, QCheckBox, QLabel, QSpinBox, QGridLayout,
                             QGroupBox, QPushButton, QVBoxLayout, QHBoxLayout,
                             QListWidget, QListWidgetItem)

from PyQt5.QtCore import pyqtSignal, Qt


class IPDecimateWidget(QWidget):
    """
    Widget for Decimation settings.

    Supports multiple sequential decimation passes.
    Settings are emitted via sig_decimate_changed as a dict with keys:
        'apply'   : bool
        'factors' : list of int  (applied in order)
    """

    sig_decimate_changed = pyqtSignal(dict)

    decimate_settings_default = {
        'apply': False,
        'factors': [],
    }

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.parent = parent
        self.decimate_settings = self.decimate_settings_default.copy()
        self.decimate_settings['factors'] = []
        self.__buildUI__()
        self.show()

    def __buildUI__(self):
        # --- top-level apply checkbox (always enabled) ---
        self.applyDecimate_checkbox = QCheckBox('Apply Decimate?')
        self.applyDecimate_checkbox.setChecked(self.decimate_settings['apply'])
        self.applyDecimate_checkbox.stateChanged.connect(self._on_apply_changed)

        # --- factor entry ---
        self.label_factor = QLabel(self.tr('Factor:'))
        self.factorSpin = QSpinBox()
        self.factorSpin.setMinimum(2)
        self.factorSpin.setMaximum(100)
        self.factorSpin.setValue(2)
        self.factorSpin.setToolTip('Integer decimation factor to add as the next pass')

        self.addFactor_button = QPushButton('Add Pass')
        self.addFactor_button.setToolTip('Append this factor as a new decimation pass')
        self.addFactor_button.clicked.connect(self._on_add_factor)

        self.removeLast_button = QPushButton('Remove Last')
        self.removeLast_button.setToolTip('Remove the last decimation pass')
        self.removeLast_button.clicked.connect(self._on_remove_last)

        self.clearAll_button = QPushButton('Clear All')
        self.clearAll_button.setToolTip('Remove all decimation passes')
        self.clearAll_button.clicked.connect(self._on_clear_all)

        # --- list of current passes ---
        self.label_passes = QLabel(self.tr('Passes (in order):'))
        self.passesList = QListWidget()
        self.passesList.setMaximumHeight(120)
        self.passesList.setToolTip('Decimation factors applied sequentially')

        # --- update button ---
        self.update_button = QPushButton('Update')
        self.update_button.setMaximumWidth(200)
        self.update_button.clicked.connect(self._on_update_clicked)

        # --- grid layout for settingsBox ---
        grid = QGridLayout()

        grid.addWidget(self.label_factor, 0, 0, alignment=Qt.AlignRight)
        grid.addWidget(self.factorSpin, 0, 1)
        grid.addWidget(self.addFactor_button, 0, 2)

        grid.addWidget(self.label_passes, 1, 0, 1, 3)
        grid.addWidget(self.passesList, 2, 0, 1, 3)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.removeLast_button)
        btn_row.addWidget(self.clearAll_button)
        grid.addLayout(btn_row, 3, 0, 1, 3)

        grid.addWidget(self.update_button, 4, 1)

        self.settingsBox = QGroupBox('Settings:')
        self.settingsBox.setLayout(grid)

        # --- outer vbox ---
        qvbox = QVBoxLayout()
        qvbox.addWidget(self.applyDecimate_checkbox)
        qvbox.addWidget(self.settingsBox)
        qvbox.addStretch()

        self.disableAll()
        self.setLayout(qvbox)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _refresh_passes_list(self):
        self.passesList.clear()
        for i, f in enumerate(self.decimate_settings['factors']):
            self.passesList.addItem(QListWidgetItem(f'Pass {i + 1}: factor = {f}'))

    # ------------------------------------------------------------------
    # Slot handlers
    # ------------------------------------------------------------------

    def _on_apply_changed(self, state: int):
        if state == Qt.Checked:
            self.decimate_settings['apply'] = True
            self.enableAll()
        else:
            self.decimate_settings['apply'] = False
            self.disableAll()
        self.sig_decimate_changed.emit(self.decimate_settings)

    def _on_add_factor(self):
        factor = self.factorSpin.value()
        self.decimate_settings['factors'].append(factor)
        self._refresh_passes_list()
        self.update_button.setEnabled(True)

    def _on_remove_last(self):
        if self.decimate_settings['factors']:
            self.decimate_settings['factors'].pop()
            self._refresh_passes_list()

    def _on_clear_all(self):
        self.decimate_settings['factors'] = []
        self._refresh_passes_list()

    def _on_update_clicked(self):
        self.sig_decimate_changed.emit(self.decimate_settings)

    # ------------------------------------------------------------------
    # Enable / disable
    # ------------------------------------------------------------------

    def enableAll(self):
        self.label_factor.setEnabled(True)
        self.factorSpin.setEnabled(True)
        self.addFactor_button.setEnabled(True)
        self.removeLast_button.setEnabled(True)
        self.clearAll_button.setEnabled(True)
        self.label_passes.setEnabled(True)
        self.passesList.setEnabled(True)
        self.update_button.setEnabled(True)

    def disableAll(self):
        self.label_factor.setEnabled(False)
        self.factorSpin.setEnabled(False)
        self.addFactor_button.setEnabled(False)
        self.removeLast_button.setEnabled(False)
        self.clearAll_button.setEnabled(False)
        self.label_passes.setEnabled(False)
        self.passesList.setEnabled(False)
        self.update_button.setEnabled(False)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_decimate_settings(self) -> dict:
        return self.decimate_settings

    def set_decimate_settings(self, settings: dict):
        self.decimate_settings = settings
        self.update_widget()
        self.sig_decimate_changed.emit(self.decimate_settings)

    def update_widget(self):
        self.applyDecimate_checkbox.setChecked(self.decimate_settings['apply'])
        self._refresh_passes_list()
        if self.decimate_settings['apply']:
            self.enableAll()
        else:
            self.disableAll()

    def reset_decimate_settings(self):
        self.decimate_settings = self.decimate_settings_default.copy()
        self.decimate_settings['factors'] = []
        self.update_widget()
        self.disableAll()
