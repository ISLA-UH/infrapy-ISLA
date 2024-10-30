import platform

from PyQt5 import QtCore
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QAction, QActionGroup, QMenuBar, QMenu, QLabel
from PyQt5.QtCore import pyqtSlot, pyqtSignal

class IPMenuLabel(QLabel):
    def __init__(self, text, parent):
        super().__init__(text, parent)


class IPMainMenuBar(QMenuBar):

    sig_activate_widget = pyqtSignal(str)

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

        self.action_control = QAction(self.tr('Control Panel \u2193'), self)
        self.action_control.setObjectName('fred')
        self.action_control.setCheckable(True)
        self.action_control.toggled.connect(self.main_window.toggle_settings)
        self.action_control.toggled.connect(self.control_toggled)

        self.action_waveforms = QAction(self.tr('Waveforms'), self)
        self.action_waveforms.setCheckable(True)
        self.action_waveforms.triggered.connect(self.activate_waveforms)

        self.action_beamforming = QAction(self.tr('Beamforming'), self)
        self.action_beamforming.setCheckable(True)
        self.action_beamforming.triggered.connect(self.activate_beamforming)

        self.action_location = QAction(self.tr('Location'), self)
        self.action_location.setCheckable(True)
        self.action_location.triggered.connect(self.activate_location)

        self.action_database = QAction(self.tr('Database'), self)
        self.action_database.setCheckable(True)
        self.action_database.triggered.connect(self.activate_database)

        self.action_spectral = QAction(self.tr('Spectral'), self)
        self.action_spectral.setCheckable(True)
        self.action_spectral.triggered.connect(self.activate_spectral)

        self.action_dict = {'waveforms': self.action_waveforms,
                            'beamforming': self.action_beamforming,
                            'location': self.action_location,
                            'spectral': self.action_spectral,
                            'database': self.action_database}
        
        self.toggle_enable('waveforms')

        widget_group = QActionGroup(self)
        widget_group.addAction(self.action_waveforms)
        widget_group.addAction(self.action_beamforming)
        widget_group.addAction(self.action_location)
        widget_group.addAction(self.action_database)
        widget_group.addAction(self.action_spectral)

        self.addAction(self.action_control)
        self.addAction(self.action_waveforms)
        self.addAction(self.action_beamforming)
        self.addAction(self.action_location)
        self.addAction(self.action_spectral)
        self.addAction(self.action_database)

        self.insertSeparator(self.action_waveforms)

        self.addMenu(self.help_menu)

        self.sig_activate_widget.connect(self.toggle_enable)

    @pyqtSlot(bool)
    def control_toggled(self, checked):
        if checked:
            self.action_control.setText("Control Panel \u2191")
        else:
            self.action_control.setText("Control Panel \u2193")

    @pyqtSlot(str)
    def toggle_enable(self, active_action):
        for key, value in self.action_dict.items():
            value.setEnabled(key != active_action)

    @pyqtSlot(bool)
    def activate_waveforms(self, checked):
        self.sig_activate_widget.emit('waveforms')

    @pyqtSlot(bool)
    def activate_beamforming(self, checked):
        self.sig_activate_widget.emit('beamforming')

    @pyqtSlot(bool)
    def activate_location(self, checked):
        self.sig_activate_widget.emit('location')

    @pyqtSlot(bool)
    def activate_database(self, checked):
        self.sig_activate_widget.emit('database')

    @pyqtSlot(bool)
    def activate_spectral(self, checked):
        self.sig_activate_widget.emit('spectral')

