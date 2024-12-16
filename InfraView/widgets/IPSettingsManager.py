from PyQt5.QtWidgets import QStackedWidget, QWidget, QPushButton, QHBoxLayout, QVBoxLayout, QFrame
from PyQt5.QtCore import Qt, pyqtSlot

import traceback, yaml

from InfraView.widgets.settings_widgets import IPBeamformingSettingsWidget
from InfraView.widgets.settings_widgets import IPSpectrogramSettingsWidget
from InfraView.widgets.settings_widgets import IPLocationSettingsWidget
from InfraView.widgets.settings_widgets import IPWaveformSettingsWidget
from InfraView.widgets.settings_widgets import IPDatabaseSettingsWidget

class IPSettingsManager(QFrame):
    def __init__(self, parent):
        super().__init__(parent)

        self.settings_widget_dict = {}

        self.initialize_settings_widgets()

        self.settings_stack = QStackedWidget(self)
        self.insert_settings_widgets()

        hide_layout = QVBoxLayout()
        self.hide_button = QPushButton('Hide')
        self.hide_button.clicked.connect(self.hide)
        self.save_button = QPushButton('Save')
        self.save_button.clicked.connect(self.save_settings)
        hide_layout.addWidget(self.hide_button)
        hide_layout.addWidget(self.save_button)
        hide_layout.addStretch()

        layout = QHBoxLayout()
        layout.addWidget(self.settings_stack)
        layout.addStretch()
        layout.addLayout(hide_layout)

        self.setLayout(layout)

        self.setObjectName("settingsManager")
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setStyleSheet("#settingsManager {border: 1px solid #777;} ")

        self.setVisible(False)

    def hide(self):
        self.setVisible(False)

    def initialize_settings_widgets(self):
        
        self.settings_widget_dict['database'] = IPDatabaseSettingsWidget.IPDatabaseSettingsWidget(self)
        self.settings_widget_dict['waveforms'] = IPWaveformSettingsWidget.IPWaveformSettingsWidget(self)
        self.settings_widget_dict['spectral'] = IPSpectrogramSettingsWidget.IPSpectrogramSettingsWidget(self)
        self.settings_widget_dict['location'] = IPLocationSettingsWidget.IPLocationSettingsWidget(parent=self)
        self.settings_widget_dict['beamforming'] = IPBeamformingSettingsWidget.IPBeamformingSettingsWidget(self)


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
            except Exception as e:
                import traceback
                traceback.print_exc()

                print("{} doesn't have set_controlling_widget method yet".format(type(widget_dict[key])))

    def insert_settings_widgets(self):
        for _, value in self.settings_widget_dict.items():
            self.settings_stack.addWidget(value)

        self.settings_stack.setCurrentWidget(self.settings_widget_dict['waveforms'])

    @pyqtSlot(str)
    def widget_changed(self, widget_name):
        # someone clicked a action to change the active, so we need to change the settings widget to match
        try:
            self.settings_stack.setCurrentWidget(self.settings_widget_dict[widget_name.lower()])
        except KeyError:
            print("{} settings not found".format(widget_name))
            
    def toggle_visibility(self):
        self.setVisible(self.isHidden())

    def save_settings(self):
        # collect settings dictionaries from all of the widgets, and save them to an infrapy file
        settings_dict = {}
        for key, value in self.settings_widget_dict.items():
            try:
                settings_dict[key+'_widget'] = value.to_dict()
            except AttributeError as e:
                #print(traceback.format_exc())
                print("{} doesn't have a to_dict method yet".format(value))
        print(yaml.dump(settings_dict, allow_unicode=True, default_flow_style=False))
        cli_dict = self.map_infraview_settings_to_cli(settings_dict)

    def map_infraview_settings_to_cli(self, settings_dict):

        # Dictionary of dictionaries to store mapping; the keys are the CLI nodes
        # TODO: We can write a function to generate this dictionary directly from the "default.config" file
        # This will make sure the default values, if not the keys, are updated.
        cli_template_dict = {
            "FK": {"freq_min": 0.5, "freq_max": 5.0, "back_az_min": -180.0, "back_az_max": 180.0, "back_az_step": 2.0,
                   "trace_vel_min": 300.0, "trace_vel_max": 600.0, "trace_vel_step": 2.5, "method": "bartlett",
                   "signal_start": None, "signal_end": None, "noise_start": None, "noise_end": None, "window_len": 10,
                   "sub_window_len": None, "window_step": 5, "cpu_cnt": None},
            "FD": {"window_len": 3600, "p_value": 0.01, "min_duration": 10, "back_az_width": 15.0, "fixed_thresh": None,
                   "thresh_ceil": None, "return_thresh": False, "merge_dets": False},
            "SD": {"spectral_option": "spectrogram", "morlet_omega0": 12.0, "freq_min": 1.0, "freq_max": 20.0,
                   "window_len": 900.0, "window_step": 450.0, "p_value": 0.01, "smoothing": None,
                   "freq_tm_factor": 35.0, "cluster_eps": 10.0, "cluster_min_samples": 40},
            "ASSOC": {"back_az_width": 10.0, "range_max": 2000.0, "resolution": 180, "distance_matrix_max": 8.0,
                      "cluster_linkage": "weighted", "cluster_threshold": 5.0, "trimming_threshold": 3.8,
                      "event_population_min": 3, "event_station_min": 2, "multithread": False, "cpu_cnt": None},
            "LOC": {"back_az_width": 10.0, "range_max": 2000.0, "latlon_resol": 0.04, "tm_resol": 20.0,
                    "src_est": None, "pgm_model": None},
            "YIELD": {"source_loc": [30.0, -105.0], "freq_min": 0.25, "freq_max": 1.0, "yld_min": 1, "yld_max": 1e3,
                      "ref_rng": 1.0, "resolution": 200, "noise_option": "post", "window_buffer": 0.2,
                      "amb_press": 101.325, "amb_temp": 288.15, "grnd_burst": True, "exp_type": "chemical"},
            "VISUALIZATION": {"offline_maps_dir": None}
        }

        # infraview_widget_list = ["database_widget", "waveforms_widget",
        #                          "spectral_widget", "location_widget",
        #                          "beamforming_widget"]
        
        # updated_keys = {}

        # FK node
        cli_template_dict["FK"]["freq_min"] = settings_dict["waveforms_widget"]["filter_dict"]["highpass"]
        cli_template_dict["FK"]["freq_max"] = settings_dict["waveforms_widget"]["filter_dict"]["lowpass"]
        cli_template_dict["FK"]["back_az_min"] = settings_dict["beamforming_widget"]["backAz_start"]
        cli_template_dict["FK"]["back_az_max"] = settings_dict["beamforming_widget"]["backAz_end"]
        cli_template_dict["FK"]["back_az_step"] = settings_dict["beamforming_widget"]["backAz_resolution"]
        cli_template_dict["FK"]["trace_vel_min"] = settings_dict["beamforming_widget"]["traceV_min"]
        cli_template_dict["FK"]["trace_vel_max"] = settings_dict["beamforming_widget"]["traceV_max"]
        cli_template_dict["FK"]["trace_vel_step"] = settings_dict["beamforming_widget"]["traceV_resolution"]
        cli_template_dict["FK"]["method"] = settings_dict["beamforming_widget"]["method"]
        cli_template_dict["FK"]["signal_start"] = None  # Default
        cli_template_dict["FK"]["signal_end"] = None  # Default
        cli_template_dict["FK"]["noise_start"] = None  # Default
        cli_template_dict["FK"]["noise_end"] = None  # Default
        cli_template_dict["FK"]["window_len"] = settings_dict["beamforming_widget"]["win_length"]
        cli_template_dict["FK"]["sub_window_len"] = settings_dict["beamforming_widget"]["sub_win_length"]
        cli_template_dict["FK"]["window_step"] = settings_dict["beamforming_widget"]["win_step"]
        cli_template_dict["FK"]["cpu_cnt"] = 1  # Default
        # FD node
        cli_template_dict["FD"]["window_len"] = None  # Default
        cli_template_dict["FD"]["p_value"] = settings_dict["beamforming_widget"]["detector_settings"]["pval"]
        cli_template_dict["FD"]["min_duration"] = settings_dict["beamforming_widget"]["detector_settings"]["min_peak_width"]
        cli_template_dict["FD"]["back_az_width"] = settings_dict["beamforming_widget"]["detector_settings"]["back_az_limit"]
        cli_template_dict["FD"]["fixed_thresh"] = False
        cli_template_dict["FD"]["thresh_ceil"] = None  # Default
        cli_template_dict["FD"]["return_thresh"] = True
        cli_template_dict["FD"]["merge_dets"] = settings_dict["beamforming_widget"]["detector_settings"]["merge"]
        # SD node
        # Spectrogram v. spectrogram - check string sanitization
        cli_template_dict["SD"]["spectral_option"] = settings_dict["spectral_widget"]["spec_type"]
        cli_template_dict["SD"]["morlet_omega0"] = settings_dict["spectral_widget"]["omega0"]
        cli_template_dict["SD"]["freq_min"] = settings_dict["spectral_widget"]["fmin"]
        cli_template_dict["SD"]["freq_max"] = settings_dict["spectral_widget"]["fmax"]
        cli_template_dict["SD"]["window_len"] = settings_dict["spectral_widget"]["adapt_win_len"]
        cli_template_dict["SD"]["window_step"]
        cli_template_dict["SD"]["p_value"] = settings_dict["spectral_widget"]["pval"]
        cli_template_dict["SD"]["smoothing"] 
        cli_template_dict["SD"]["freq_tm_factor"]
        cli_template_dict["SD"]["cluster_eps"] = settings_dict["spectral_widget"]["cluster_eps"]
        cli_template_dict["SD"]["cluster_min_samples"] = settings_dict["spectral_widget"]["cluster_min_samples"]
        # ASSOC node
        cli_template_dict["ASSOC"]["back_az_width"] = settings_dict["location_widget"]["bisl_dict"]["bisl_bm_width"]
        cli_template_dict["ASSOC"]["range_max"] = settings_dict["location_widget"]["bisl_dict"]["bisl_rng_max"]
        cli_template_dict["ASSOC"]["resolution"] = settings_dict["location_widget"]["bisl_dict"]["bisl_resolution"]
        cli_template_dict["ASSOC"]["distance_matrix_max"] =
        cli_template_dict["ASSOC"]["cluster_linkage"] =
        cli_template_dict["ASSOC"]["cluster_threshold"] =
        cli_template_dict["ASSOC"]["trimming_threshold"] =
        cli_template_dict["ASSOC"]["event_population_min"] =
        cli_template_dict["ASSOC"]["event_station_min"] =
        cli_template_dict["ASSOC"]["multithread"] = False  # Default
        cli_template_dict["ASSOC"]["cpu_cnt"] = None  # Default
        # LOC node
        cli_template_dict["LOC"]["back_az_width"] = settings_dict["location_widget"]["bisl_dict"]["bisl_bm_width"]
        cli_template_dict["LOC"]["range_max"] = settings_dict["location_widget"]["bisl_dict"]["bisl_rng_max"]
        
        print(cli_template_dict)
                
        return cli_template_dict