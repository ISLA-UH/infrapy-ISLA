from PyQt5.QtWidgets import QStackedWidget, QWidget
from PyQt5.QtCore import pyqtSignal, pyqtSlot

from InfraView.widgets import IPBaseWidgets
from InfraView.widgets import IPSingleSensorWidget
from InfraView.widgets import IPBeamformingSettingsWidget
from InfraView.widgets.settings import IPLocationSettingsWidget

class IPSettingsManager(QStackedWidget):
    def __init__(self, parent):
        super().__init__(parent)

        self.settings_widget_dict = {}

        self.initialize_settings_widgets()
        self.insert_settings_widgets()

        self.setVisible(False)

    def initialize_settings_widgets(self):
        self.settings_widget_dict['waveforms'] = IPBaseWidgets.IPSettingsWidget(self)
        self.settings_widget_dict['database'] = IPBaseWidgets.IPSettingsWidget(self)

        # create instances of the settings widgets, and put them in a dictionary 
        self.spectra_settings = IPSingleSensorWidget.IPSpectrogramSettingsWidget(self)
        self.settings_widget_dict['spectral'] = self.spectra_settings

        self.location_settings = IPLocationSettingsWidget.IPLocationSettingsWidget(parent=self)
        self.settings_widget_dict['location'] = self.location_settings

        self.beamforming_settings = IPBeamformingSettingsWidget.IPBeamformingSettingsWidget(self)
        self.settings_widget_dict['beamforming'] = self.beamforming_settings

    def connect_widgets_and_settings(self, widget_dict):
        # settings widgets need to have a reference to the widgets they control, and vice-versa
        for key, value in widget_dict.items():
            try:
                self.settings_widget_dict[key].set_controlled_widget(value)
            except  KeyError:
                pass    # probably the App window, which isn't a settings widget

        for key, value in self.settings_widget_dict.items():
            try: 
                widget_dict[key].set_controlling_widget(value)
            except AttributeError:
                print("{} doesn't have set_controlling_widget method yet".format(type(value)))

    def insert_settings_widgets(self):
        for _, value in self.settings_widget_dict.items():
            self.addWidget(value)

    @pyqtSlot(str)
    def widget_changed(self, widget_name):
        # someone clicked a action to change the active, so we need to change the settings widget to match
        try:
            self.setCurrentWidget(self.settings_widget_dict[widget_name.lower()])
        except KeyError:
            print("{} settings not found".format(widget_name))
            
    def toggle_visibility(self):
        self.setVisible(self.isHidden())



