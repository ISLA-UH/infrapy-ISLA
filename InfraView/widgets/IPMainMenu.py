import platform

from PyQt5 import QtCore
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QAction, QMenuBar, QMenu
from PyQt5.QtCore import pyqtSlot, pyqtSignal

class IPMainMenuBar(QMenuBar):

    sig_settings_updated = pyqtSignal(str)

    def __init__(self, parent, widget_dict):
        super().__init__(parent)

        self.main_window = widget_dict['app_window']

        if platform.system() == 'Darwin':
           self.setNativeMenuBar(False)  # This is because I couldn't get the normal mac menu to work...

        self.make_base_menu()
    
    def make_base_menu(self):
        # This is where we create the menus/actions that will be visible 
        # for all of the tabs

        # File Menu #############
        self.file_menu = QMenu('&File', self)
        self.file_menu.addAction(self.tr(' New Project...'), self.main_window.filemenu_NewProject)
        self.file_menu.addAction(self.tr(' Load Project...'), self.main_window.filemenu_LoadProject)
        self.file_menu.addAction(self.tr(' Close Project'), self.main_window.filemenu_CloseProject)

        self.file_menu.addSeparator()

        self.file_menu.addAction(self.tr(' Load Waveform File(s)...'), self.main_window.filemenu_Open)
        self.file_menu.addAction(self.tr(' Import from FDSN...'), self.main_window.filemenu_import)
        self.file_menu.addAction(self.tr(' Clear Waveform(s)'), self.main_window.filemenu_ClearWaveforms)
        self.file_menu.addAction(self.tr(' Save Waveform(s)...'), self.main_window.filemenu_saveAllWaveforms)

        self.file_menu.addSeparator()

        self.file_menu.addAction(self.tr(' &Exit'), 
                                 self.main_window.filemenu_Quit, 
                                 QtCore.Qt.CTRL + QtCore.Qt.Key_Q)

        # View Menu ############
        self.view_menu = QMenu('View', self)

        self.view_menu.addAction(self.tr(' Toggle Fullscreen'), 
                                 self.main_window.viewmenu_toggle_fullscreen, 
                                 shortcut=QKeySequence.FullScreen)

        # Help Menu ############
        self.help_menu = QMenu('&Help', self)
        self.help_menu.addAction(self.tr(' &About'), self.main_window.helpmenu_about)

        self.addMenu(self.file_menu)
        self.addMenu(self.view_menu)
        self.addSeparator()
        self.addAction(self.tr('Control Panel'), self.main_window.toggle_settings)
        self.addAction(self.tr('Waveforms'))
        self.addAction(self.tr('Beamforming'))
        self.addAction(self.tr('Location'))
        self.addAction(self.tr('Database'))
        self.addAction(self.tr('Spectral'))
        self.addSeparator()
        self.addMenu(self.help_menu)

        # Create Actions for various tabs
        # self.create_singleSensorActions()
        # self.create_locationActions()
        # self.create_beamformerActions()


    # @pyqtSlot(str)
    # def update_tab(self, tt):
    #     # tt is the tab text
    #     tt = tt.lower()

    #     if tt == 'waveforms':
    #         self.add_waveform_actions()
    #     elif tt == 'spectral':
    #         self.add_ss_actions()
    #     elif tt == 'location':
    #         self.add_loc_actions()
    #     elif tt == 'beamforming':
    #         self.add_beam_actions()
    #     elif tt == 'database':
    #         self.add_db_actions()

    # def emit_settings_info(self, name):
    #     # name is the name of the settings tab, should be the same as in main_window.settings_dict
    #     self.sig_settings_updated.emit(name)

    # # Create Custom Actions for different Tabs here ###############

    # def clear_custom_actions(self):
    #     # clear out whatever custom actions are visible so that we can display just the current ones
    #     self.remove_ss_actions()
    #     self.remove_loc_actions()
    #     self.remove_beam_actions()

    # # Waveform Tab ##################
    # def create_waveformActions(self):
    #     pass

    # @pyqtSlot()
    # def add_waveform_actions(self):
    #     self.clear_custom_actions()

    #     for act in self.wave_actions:
    #         self.insertAction(self.help_menu.menuAction(), act)

    # @pyqtSlot()
    # def remove_waveform_actions(self):
    #     for act in self.wave_actions:
    #         self.removeAction(act)

    # # Database Tab ##################
    # def create_dbActions(self):
    #     pass

    # @pyqtSlot()
    # def add_db_actions(self):
    #     self.clear_custom_actions()

    #     for act in self.db_actions:
    #         self.insertAction(self.help_menu.menuAction(), act)

    # @pyqtSlot()
    # def remove_db_actions(self):
    #     for act in self.db_actions:
    #         self.removeAction(act)

    # # Beamforming Tab ###############
    # def create_beamformerActions(self):
    #     # we create the beamformer menu actions here, once. Later, we can add them or remove them 
    #     # when the beamformer tab is clicked.
    #     # This should be called ONCE at init
    #     action_beam_settings = QAction(self.tr(' Beamformer Settings'))
    #     action_beam_settings.triggered.connect(self.beam_widget.showhide_bfsettings)
    #     self.beam_actions.append(action_beam_settings)

    #     action_beam_detector_settings = QAction(self.tr(' Detector Settings'))
    #     action_beam_detector_settings.triggered.connect(self.beam_widget.showhide_detsettings)
    #     self.beam_actions.append(action_beam_detector_settings)

    #     action_beam_reset_zoom = QAction(self.tr(' Reset Zoom'))
    #     action_beam_reset_zoom.triggered.connect(self.beam_widget.reset_zoom)
    #     self.beam_actions.append(action_beam_reset_zoom)

    #     action_beam_export = QAction(self.tr(' Export Results'))
    #     action_beam_export.triggered.connect(self.beam_widget.exportResults)
    #     self.beam_actions.append(action_beam_export)
        
    #     action_beam_slowness_settings = QAction(self.tr(' Slowness Settings'))
    #     action_beam_slowness_settings.triggered.connect(self.beam_widget.showhide_slownessSettings)
    #     self.beam_actions.append(action_beam_slowness_settings)

    # @pyqtSlot()
    # def add_beam_actions(self):
    #     self.clear_custom_actions()
    #     for act in self.beam_actions:
    #         self.insertAction(self.help_menu.menuAction(), act)   

    # @pyqtSlot()
    # def remove_beam_actions(self):
    #     for act in self.beam_actions:
    #         self.removeAction(act)

    # # Location Tab ##################
    # def create_locationActions(self):
    #     # we create the single sensor menu actions here, once. Later, we can add them or remove them 
    #     # when the single sensor tab is clicked.
    #     # This should be called ONCE at init
    #     action_loc_mapSettings = QAction(self.tr(' Map Settings'))
    #     action_loc_mapSettings.triggered.connect(self.loc_widget.mapWidget.showhide_map_settings_widget)
    #     self.loc_actions.append(action_loc_mapSettings)

    #     action_loc_extent = QAction(self.tr(' Map Extent'))
    #     action_loc_extent.triggered.connect(self.loc_widget.mapWidget.showhide_extent_widget)
    #     self.loc_actions.append(action_loc_extent)

    #     action_loc_export_map = QAction(self.tr('Export Map'))
    #     action_loc_export_map.triggered.connect(self.loc_widget.mapWidget.map_export_dialog.exec_)
    #     self.loc_actions.append(action_loc_export_map)

    # @pyqtSlot()
    # def add_loc_actions(self):
    #     self.clear_custom_actions()

    #     for act in self.loc_actions:
    #         self.insertAction(self.help_menu.menuAction(), act)

    # @pyqtSlot()
    # def remove_loc_actions(self):
    #     for act in self.loc_actions:
    #         self.removeAction(act)

    # # Single Sensor Tab #####################
    # def create_singleSensorActions(self):
    #     # we create the single sensor menu actions here, once. Later, we can add them or remove them 
    #     # when the single sensor tab is clicked.
    #     # This should be called ONCE at init
    #     action_ss_settings = QAction(self.tr(' Spectral Settings'))
    #     action_ss_settings.triggered.connect(self.show_ss_settings)
    #     self.ss_actions.append(action_ss_settings)

    # @pyqtSlot()
    # def add_ss_actions(self):
    #     self.clear_custom_actions()

    #     for act in self.ss_actions:
    #         self.insertAction(self.help_menu.menuAction(), act)

    # @pyqtSlot()
    # def remove_ss_actions(self):
    #     for act in self.ss_actions:
    #         self.removeAction(act)

    # def show_ss_settings(self):
    #     self.sig_settings_updated.emit('single_sensor_settings')

    

