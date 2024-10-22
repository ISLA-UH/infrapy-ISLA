from PyQt5.QtWidgets import QStackedWidget
from PyQt5.QtCore import pyqtSignal, pyqtSlot

from InfraView.widgets import IPSingleSensorWidget
from InfraView.widgets import IPMapWidget
from InfraView.widgets import IPBeamformingSettingsWidget

class IPSettingsManager(QStackedWidget):
    def __init__(self, parent, widget_dict):
        super().__init__(parent)

        self.widget_dict = widget_dict
        self.settings_widget_dict = {}

        self.initialize_settings_widgets()
        self.insert_settings_widgets()

        self.setVisible(False)

    def initialize_settings_widgets(self):
        # create instances of the settings widgets, and put them in a dictionary 
        self.spectra_settings = IPSingleSensorWidget.IPSpectrogramSettingsWidget(self)
        self.settings_widget_dict['spectral'] = self.spectra_settings

        self.location_settings = IPMapWidget.IPMapSettingsWidget(self)
        self.settings_widget_dict['location'] = self.location_settings

        self.beamforming_settings = IPBeamformingSettingsWidget.IPBeamformingSettingsWidget(self)
        self.settings_widget_dict['beamforming'] = self.beamforming_settings


    def insert_settings_widgets(self):
        for _, value in self.settings_widget_dict.items():
            self.addWidget(value)

    @pyqtSlot(str)
    def tabs_changed(self, tab_name):
        # someone clicked a tab, so we need to change the settings widget to match
        tab_name = tab_name.lower()
        try:
            self.setCurrentWidget(self.settings_widget_dict[tab_name])
            self.setVisible(self.settings_widget_dict[tab_name].is_active())
            
        except KeyError:
            print("settings not found")
            self.setVisible(False)
            
    def toggle_visibility(self):
        self.setVisible(self.isHidden())



