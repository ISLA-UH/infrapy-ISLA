import platform, platform

from PyQt5 import QtCore
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QAction, QActionGroup, QMenuBar, QMenu, QLabel
from PyQt5.QtCore import pyqtSlot, pyqtSignal

class IPMenuLabel(QLabel):
    def __init__(self, text, parent):
        super().__init__(text, parent)


class IPMainMenuBar(QMenuBar):

    sig_activate_widget = pyqtSignal(str)
    sig_set_theme = pyqtSignal(str)

    def __init__(self, parent, widget_dict):
        super().__init__(parent)

        self.main_window = widget_dict['app_window']

        if platform.system() == 'Darwin':
           self.setNativeMenuBar(False)  # This is because I couldn't get the normal mac menu to work correctly...

        self.apply_stylesheet()

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
        if platform.system() == 'Linux':
            self.dark_action = QAction(self.tr('Dark'), self)
            self.dark_action.setCheckable(True)

            self.light_action = QAction(self.tr('Light'), self)
            self.light_action.setCheckable(True)
            self.light_action.setChecked(True)

            self.auto_action = QAction(self.tr('Auto'), self)
            self.auto_action.setCheckable(True)

            theme_actiongroup = QActionGroup(self)
            theme_actiongroup.addAction(self.dark_action)
            theme_actiongroup.addAction(self.light_action)
            theme_actiongroup.addAction(self.auto_action)
            theme_actiongroup.triggered.connect(self.change_theme)

        self.view_menu.addSection("Theme")
        self.view_menu.addAction(self.dark_action)
        self.view_menu.addAction(self.light_action)
        self.view_menu.addAction(self.auto_action)
        self.view_menu.addSeparator()
        self.view_menu.addAction(self.tr(' Toggle Fullscreen'), 
                                 self.main_window.viewmenu_toggle_fullscreen, 
                                 shortcut=QKeySequence.FullScreen)

        # Help Menu ############
        self.help_menu = QMenu('&Help', self)
        self.help_menu.addAction(self.tr(' &About'), self.main_window.helpmenu_about)

        self.addMenu(self.file_menu)
        self.addMenu(self.view_menu)
        self.addSeparator()

        self.action_control = QAction(self.tr('Settings \u2193'), self)
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

    @pyqtSlot(QAction)
    def change_theme(self, source):
        if source == self.dark_action:
            self.sig_set_theme.emit('dark')
        elif source == self.light_action:
            self.sig_set_theme.emit('light')
        elif source == self.auto_action:
            self.sig_set_theme.emit('auto')

    def apply_stylesheet(self):
        '''manually set the stylesheet of the menu'''

        menu_style = '''
        QMenuBar::item:hover{
            background-color: #0F0;
        }

        QMenuBar::item:selected {
            background-color: #0070C1;
            color: #FFF
        }

        QMenuBar::item:pressed{
            background-color: #E17800;
            color: #FFF
        }


        QMenuBar::item:checked {
            background-color: #0000FF
        }'''

        self.setStyleSheet(menu_style)


    @pyqtSlot(bool)
    def control_toggled(self, checked):
        if checked:
            self.action_control.setText("Settings \u2191") # up arrow
        else:
            self.action_control.setText("Settings \u2193") # down arrow

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

