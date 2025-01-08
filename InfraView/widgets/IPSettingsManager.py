from PyQt5.QtWidgets import QStackedWidget, QWidget, QPushButton, QHBoxLayout, QVBoxLayout, QFrame
from PyQt5.QtCore import Qt, pyqtSlot

import traceback, yaml
import configparser

from pathlib import Path

from InfraView.widgets.settings_widgets import IPBeamformingSettingsWidget
from InfraView.widgets.settings_widgets import IPSpectrogramSettingsWidget
from InfraView.widgets.settings_widgets import IPLocationSettingsWidget
from InfraView.widgets.settings_widgets import IPWaveformSettingsWidget
from InfraView.widgets.settings_widgets import IPDatabaseSettingsWidget

class IPSettingsManager(QFrame):
    def __init__(self, parent):
        super().__init__(parent)

        self.setObjectName("settingsManager")
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setStyleSheet("#settingsManager {border: 1px solid #777;} ")

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
        # print(yaml.dump(settings_dict, allow_unicode=True, default_flow_style=False))
        cli_dict = self.map_infraview_settings_to_cli(settings_dict)

    def load_settings(self):
        pass

    def ini_to_dict(self, ini_filename):
        # ini_filename is the absolute path to the ini file to read
        config = configparser.ConfigParser()
        config.read(ini_filename)
        
        ini_dict = {}
        for section in config.sections():
            ini_dict[section] = {}
            #print(section)
            for option in config.options(section):
                #print(option)
                ini_dict[section][option] = config.get(section, option)
        return ini_dict

    def map_cli_to_infraview_settings(self, cli_dict):
        # This would primarily be for reading in ini files and setting appropriate elements of the gui
        
        #FK
        settings_dict["waveforms_widget"]["filter_dict"]["highpass"] = cli_dict["FK"]["freq_min"]
        settings_dict["waveforms_widget"]["filter_dict"]["lowpass"] = cli_dict["FK"]["freq_max"]
        settings_dict["beamforming_widget"]["signal_start"] = cli_dict["FK"]["signal_start"]
        settings_dict["beamforming_widget"]["signal_end"] = cli_dict["FK"]["signal_end"]
        settings_dict["beamforming_widget"]["noise_start"] = cli_dict["FK"]["noise_start"]
        settings_dict["beamforming_widget"]["noise_end"] = cli_dict["FK"]["noise_end"]
        settings_dict["beamforming_widget"]["backAz_start"] = cli_dict["FK"]["back_az_min"]
        settings_dict["beamforming_widget"]["backAz_end"] = cli_dict["FK"]["back_az_max"]
        settings_dict["beamforming_widget"]["backAz_resolution"] = cli_dict["FK"]["back_az_step"] 
        settings_dict["beamforming_widget"]["traceV_min"] = cli_dict["FK"]["trace_vel_min"]
        settings_dict["beamforming_widget"]["traceV_max"] = cli_dict["FK"]["trace_vel_max"]
        settings_dict["beamforming_widget"]["traceV_resolution"] = cli_dict["FK"]["trace_vel_step"]
        settings_dict["beamforming_widget"]["method"] = cli_dict["FK"]["method"]
        settings_dict["beamforming_widget"]["win_length"] = cli_dict["FK"]["window_len"]
        settings_dict["beamforming_widget"]["sub_win_length"] = cli_dict["FK"]["sub_window_len"]
        settings_dict["beamforming_widget"]["win_step"] = cli_dict["FK"]["window_step"]
        #cli_template_dict["FK"]["cpu_cnt"] # GUI doesn't save cpu cnt

        # FD node
        settings_dict["beamforming_widget"]["detector_settings"]["window_len"] = cli_dict["FD"]["window_len"]
        settings_dict["beamforming_widget"]["detector_settings"]["thresh_ceil"] = cli_dict["FD"]["thresh_ceil"]
        settings_dict["beamforming_widget"]["detector_settings"]["pval"] = cli_dict["FD"]["p_value"]
        settings_dict["beamforming_widget"]["detector_settings"]["min_peak_width"] = cli_dict["FD"]["min_duration"]
        settings_dict["beamforming_widget"]["detector_settings"]["back_az_limit"] = cli_dict["FD"]["back_az_width"]
        settings_dict["beamforming_widget"]["detector_settings"]["manual_level"] = cli_dict["FD"]["fixed_thresh"]
        settings_dict["beamforming_widget"]["detector_settings"]["merge"] = cli_dict["FD"]["merge_dets"]

        # SD node
        # Spectrogram v. spectrogram - check string sanitization
        settings_dict["spectral_widget"]["spec_type"] = cli_dict["SD"]["spectral_option"]
        settings_dict["spectral_widget"]["omega0"] = cli_dict["SD"]["morlet_omega0"]
        settings_dict["spectral_widget"]["fmin"] = cli_dict["SD"]["freq_min"]
        settings_dict["spectral_widget"]["fmax"] = cli_dict["SD"]["freq_max"]
        settings_dict["spectral_widget"]["adapt_win_len"] = cli_dict["SD"]["window_len"]  
        # cli_dict["SD"]["window_step"].  GUI autmatically calulates window_step from window length
        settings_dict["spectral_widget"]["pval"] = cli_dict["SD"]["p_value"] 
        settings_dict["spectral_widget"]["cwt_cluster_freq_scale"] = cli_dict["SD"]["freq_tm_factor"] 
        settings_dict["spectral_widget"]["cluster_eps"] = cli_dict["SD"]["cluster_eps"]
        settings_dict["spectral_widget"]["cluster_min_samples"] = cli_dict["SD"]["cluster_min_samples"]

        settings_dict["spectral_widget"]["cwt_fmin"] = cli_dict["SD-CWT"]["freq_min"]
        settings_dict["spectral_widget"]["cwt_fmax"] = cli_dict["SD-CWT"]["freq_max"]
        settings_dict["spectral_widget"]["cwt_adapt_win_len"] = cli_dict["SD-CWT"]["window_len"]
        # cli_dict["SD-CWT"]["window_step"] GUI automatically calculates window step from window length 
        settings_dict["spectral_widget"]["cwt_pval"] = cli_dict["SD-CWT"]["p_value"]
        settings_dict["spectral_widget"]["cwt_cluster_freq_scale"] = cli_dict["SD-CWT"]["freq_tm_factor"]
        settings_dict["spectral_widget"]["cluster_eps"] = cli_dict["SD-CWT"]["cluster_eps"]
        settings_dict["spectral_widget"]["cluster_min_samples"] = cli_dict["SD-CWT"]["cluster_min_samples"]

        # ASSOC node
        settings_dict["location_widget"]["bisl_dict"]["bisl_bm_width"] = cli_dict["ASSOC"]["back_az_width"]
        settings_dict["location_widget"]["bisl_dict"]["bisl_rng_max"] = cli_dict["ASSOC"]["range_max"]
        settings_dict["location_widget"]["bisl_dict"]["bisl_resolution"] = cli_dict["ASSOC"]["resolution"]
        # cli_dict["ASSOC"]["cpu_cnt"] GUI doesn't save cpu cnt

        # LOC node
        settings_dict["location_widget"]["bisl_dict"]["bisl_bm_width"] = cli_dict["LOC"]["back_az_width"]
        settings_dict["location_widget"]["bisl_dict"]["bisl_rng_max"] = cli_dict["LOC"]["range_max"]


    def map_infraview_settings_to_cli(self, settings_dict):
        # This is used mainly when saving settings to a ini file

        # load infrapy defaults, then if there's something we don't write over, it will automatically have the default value
        default_config_path = Path(__file__).parent.parent.parent /"infrapy" / "resources" / "default.config"
        if default_config_path.exists():
            print("Reading: {}".format(str(default_config_path)))
            cli_template_dict = self.ini_to_dict(str(default_config_path))
        else:
            raise FileNotFoundError
        print(cli_template_dict)
       
        # FK node
        cli_template_dict["FK"]["freq_min"] = settings_dict["waveforms_widget"]["filter_dict"]["highpass"]
        cli_template_dict["FK"]["freq_max"] = settings_dict["waveforms_widget"]["filter_dict"]["lowpass"]
        cli_template_dict["FK"]["signal_start"] = settings_dict["beamforming_widget"]["signal_start"]
        cli_template_dict["FK"]["signal_end"] = settings_dict["beamforming_widget"]["signal_end"]
        cli_template_dict["FK"]["noise_start"] = settings_dict["beamforming_widget"]["noise_start"]
        cli_template_dict["FK"]["noise_end"] = settings_dict["beamforming_widget"]["noise_end"]
        cli_template_dict["FK"]["back_az_min"] = settings_dict["beamforming_widget"]["backAz_start"]
        cli_template_dict["FK"]["back_az_max"] = settings_dict["beamforming_widget"]["backAz_end"]
        cli_template_dict["FK"]["back_az_step"] = settings_dict["beamforming_widget"]["backAz_resolution"]
        cli_template_dict["FK"]["trace_vel_min"] = settings_dict["beamforming_widget"]["traceV_min"]
        cli_template_dict["FK"]["trace_vel_max"] = settings_dict["beamforming_widget"]["traceV_max"]
        cli_template_dict["FK"]["trace_vel_step"] = settings_dict["beamforming_widget"]["traceV_resolution"]
        cli_template_dict["FK"]["method"] = settings_dict["beamforming_widget"]["method"]

        cli_template_dict["FK"]["window_len"] = settings_dict["beamforming_widget"]["win_length"]
        cli_template_dict["FK"]["sub_window_len"] = settings_dict["beamforming_widget"]["sub_win_length"]
        cli_template_dict["FK"]["window_step"] = settings_dict["beamforming_widget"]["win_step"]
        cli_template_dict["FK"]["cpu_cnt"] = None  # # GUI doesn't save cpu cnt

        # FD node
        cli_template_dict["FD"]["window_len"] = None  # Default
        cli_template_dict["FD"]["p_value"] = settings_dict["beamforming_widget"]["detector_settings"]["pval"]
        cli_template_dict["FD"]["min_duration"] = settings_dict["beamforming_widget"]["detector_settings"]["min_peak_width"]
        cli_template_dict["FD"]["back_az_width"] = settings_dict["beamforming_widget"]["detector_settings"]["back_az_limit"]
        cli_template_dict["FD"]["fixed_thresh"] = settings_dict["beamforming_widget"]["detector_settings"]["manual_level"]
        cli_template_dict["FD"]["thresh_ceil"] = None  # Default
        cli_template_dict["FD"]["merge_dets"] = settings_dict["beamforming_widget"]["detector_settings"]["merge"]

        # SD node
        # Spectrogram v. spectrogram - check string sanitization
        cli_template_dict["SD"]["spectral_option"] = settings_dict["spectral_widget"]["spec_type"]
        cli_template_dict["SD"]["morlet_omega0"] = settings_dict["spectral_widget"]["omega0"]
        cli_template_dict["SD"]["freq_min"] = settings_dict["spectral_widget"]["fmin"]
        cli_template_dict["SD"]["freq_max"] = settings_dict["spectral_widget"]["fmax"]
        cli_template_dict["SD"]["window_len"] = settings_dict["spectral_widget"]["adapt_win_len"]   # 900 default
        cli_template_dict["SD"]["window_step"] = settings_dict["spectral_widget"]["adapt_win_len"] / 2.
        cli_template_dict["SD"]["p_value"] = settings_dict["spectral_widget"]["pval"]
        cli_template_dict["SD"]["freq_tm_factor"] = settings_dict["spectral_widget"]["cwt_cluster_freq_scale"]
        cli_template_dict["SD"]["cluster_eps"] = settings_dict["spectral_widget"]["cluster_eps"]
        cli_template_dict["SD"]["cluster_min_samples"] = settings_dict["spectral_widget"]["cluster_min_samples"]

        cli_template_dict["SD-CWT"]["freq_min"] = settings_dict["spectral_widget"]["cwt_fmin"]
        cli_template_dict["SD-CWT"]["freq_max"] = settings_dict["spectral_widget"]["cwt_fmax"]
        cli_template_dict["SD-CWT"]["window_len"] = settings_dict["spectral_widget"]["cwt_adapt_win_len"]   # 900 default
        cli_template_dict["SD-CWT"]["window_step"] = settings_dict["spectral_widget"]["adapt_win_len"] / 2.
        cli_template_dict["SD-CWT"]["p_value"] = settings_dict["spectral_widget"]["cwt_pval"]
        cli_template_dict["SD-CWT"]["freq_tm_factor"] = settings_dict["spectral_widget"]["cwt_cluster_freq_scale"]
        cli_template_dict["SD-CWT"]["cluster_eps"] = settings_dict["spectral_widget"]["cluster_eps"]
        cli_template_dict["SD-CWT"]["cluster_min_samples"] = settings_dict["spectral_widget"]["cluster_min_samples"]

        # ASSOC node
        cli_template_dict["ASSOC"]["back_az_width"] = settings_dict["location_widget"]["bisl_dict"]["bisl_bm_width"]
        cli_template_dict["ASSOC"]["range_max"] = settings_dict["location_widget"]["bisl_dict"]["bisl_rng_max"]
        cli_template_dict["ASSOC"]["resolution"] = settings_dict["location_widget"]["bisl_dict"]["bisl_resolution"]
        cli_template_dict["ASSOC"]["cpu_cnt"] = None  # GUI doesn't save cpu cnt

        # LOC node
        cli_template_dict["LOC"]["back_az_width"] = settings_dict["location_widget"]["bisl_dict"]["bisl_bm_width"]
        cli_template_dict["LOC"]["range_max"] = settings_dict["location_widget"]["bisl_dict"]["bisl_rng_max"]
        # cli_template_dict["LOC"]["latlon_resol"] = 
        # cli_template_dict["LOC"]["tm_resol"] =
        # cli_template_dict["LOC"]["src_est"] = 
        # cli_template_dict["pgm_model"] = 
                
        return cli_template_dict