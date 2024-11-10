
from ssl import OP_NO_RENEGOTIATION
from tkinter import N
import configparser

from PyQt5.QtWidgets import (QComboBox, QFileDialog, QFrame, QHBoxLayout, QTextEdit,
                             QLabel, QLineEdit, QPushButton, QVBoxLayout, QDialog, QDialogButtonBox,)

from PyQt5.QtCore import pyqtSlot, pyqtSignal, QTimer, Qt

from sqlalchemy.orm import Session

from InfraView.widgets import IPUtils
from infrapy.utils import database

from InfraView.widgets import IPBaseWidgets

class IPDatabaseSettingsWidget(IPBaseWidgets.IPSettingsWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.connect_widget = IPDatabaseConnectWidget(parent=self, title='Connection')

        layout = QHBoxLayout()
        layout.addWidget(self.connect_widget)
        layout.addStretch()

        self.setLayout(layout)


class IPDatabaseConnectWidget(IPBaseWidgets.IPSettingsGroupBox):

    sig_session_created = pyqtSignal(Session)
        
    def __init__(self, parent=None, title=""):
        super().__init__(parent=parent, title=title)

        self.session = None
        self.config_filename = ""

        self.buildUI()
        
    def buildUI(self):

        self.load_config_button = QPushButton("Load Config...")
        # This will be the font we will use through the widget...

        self.save_current_button = QPushButton("Save Config...")
        self.save_current_button.setEnabled(False)

        self.table_dialog = IPTableDialog(self)
        self.show_tables_button = QPushButton("Tables...")

        self.env_vars_dialog = IPEnvVarDialog(self)
        self.show_env_vars_button = QPushButton("Env Vars...")

        self.schema_type_combo = QComboBox()
        self.schema_type_combo.addItem("KBCore")
        self.schema_type_combo.addItem("CSS3")

        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("URL")
        self.url_edit.setMinimumWidth(500)
        self.url_edit.setMaximumWidth(500)

        self.create_session_button = QPushButton("Create Session")

        self.close_session_button = QPushButton("Clear Session")

        self.test_connection_button = QPushButton("Test Connection")

        row1_layout = QHBoxLayout()
        row1_layout.addWidget(self.load_config_button)
        row1_layout.addWidget(self.save_current_button)
        row1_layout.addStretch()

        row2_layout = QHBoxLayout()
        row2_layout.addWidget(self.show_tables_button)
        row2_layout.addWidget(self.show_env_vars_button)
        row2_layout.addWidget(self.schema_type_combo)
        row2_layout.addStretch()

        row3_layout = QHBoxLayout()
        row3_layout.addWidget(self.url_edit)
        row3_layout.addWidget(self.create_session_button)
        row3_layout.addWidget(self.test_connection_button)
        row3_layout.addStretch()

        # row4_layout = QHBoxLayout()
        # row4_layout.addWidget(self.create_session_button)
        # row4_layout.addWidget(self.test_connection_button)
        # row4_layout.addStretch()

        main_layout = QVBoxLayout()
        main_layout.addLayout(row1_layout)
        main_layout.addLayout(row2_layout)
        main_layout.addLayout(row3_layout)
        # main_layout.addLayout(row4_layout)
        main_layout.addStretch()

        self.setLayout(main_layout)

        # create dialogs here
        self.config_file_dialog = QFileDialog()
        self.config_file_dialog.setFileMode(QFileDialog.ExistingFile)
        self.config_file_dialog.setNameFilter("(*.ini)")

        self.table_dialog = IPTableDialog(self)

        self.env_vars_dialog = IPEnvVarDialog(self)

        # connect signals and slots
        self.connect_signals_and_slots()

    def connect_signals_and_slots(self):
        self.load_config_button.clicked.connect(self.load_config_file)
        self.save_current_button.clicked.connect(self.save_current_config)
        self.show_tables_button.clicked.connect(self.show_tables_dialog)
        self.show_env_vars_button.clicked.connect(self.show_env_vars_dialog)
        self.create_session_button.clicked.connect(self.create_session)
        self.test_connection_button.pressed.connect(self.check_connection)

    @pyqtSlot()
    def load_config_file(self):
        if self.config_file_dialog.exec_():
            self.config_filename = self.config_file_dialog.selectedFiles()[0]
            try:
                config = configparser.ConfigParser()
                config.read(self.config_filename)
                self.schema_type_combo.setCurrentText(config['DATABASE']['schema'])
                self.url_edit.setText(config['DATABASE']['url'])

                self.table_dialog.set_text_from_table_dict(config['DBTABLES'])

                self.env_vars_dialog.set_text_from_vars_dict(config['DBENVIRONMENTVARS'])

                self.save_current_button.setEnabled(False)

            except Exception as e:
                IPUtils.errorPopup("Error reading config file \n{}".format(str(e)))

    @pyqtSlot()
    def save_current_config(self):
        pass

    @pyqtSlot()
    def show_tables_dialog(self):
        if self.table_dialog.exec_():
            self.save_current_button.setEnabled(True)

    @pyqtSlot()
    def show_env_vars_dialog(self):
        if self.env_vars_dialog.exec_():
            self.save_current_button.setEnabled(True)

    @pyqtSlot()
    def create_session(self):
        # first, if there is already an active session, close it...
        self.close_session()

        # make sure any environment variables are loaded.
        env_vars = self.env_vars_dialog.get_vars_from_text()
        if env_vars:
            database.set_db_env_variables(env_vars)

        url = self.url_edit.text()

        try:
            self.session = database.db_connect_url(url)
            self.sig_session_created.emit(self.session)
            self.url_edit.setStyleSheet("color: green")
        except ValueError as e:
            self.session = None
            self.url_edit.setStyleSheet("color: red")
            IPUtils.errorPopup("Error creating session.  \nMake sure you can reach the database and that the displayed url is correct.")
    
    def close_session(self):
        if self.session is not None:
            self.session.close()
            self.url_edit.setStyleSheet("color: black")
            self.session = None

    @pyqtSlot()
    def clear_form(self):
        if self.session is not None:
            self.close_session()

        self.schema_type_combo.setCurrentIndex(0)
        self.url_edit.setText("")

    @pyqtSlot()
    def reset_connection_colors(self):
        self.test_connection_button.setText('Test Connection')
        self.test_connection_button.setStyleSheet('QPushButton {color: black}')

    @pyqtSlot()
    def check_connection(self):
        if self.session is not None:
            if database.check_connection(self.session):
                self.test_connection_button.setText("Good Connection")
                self.test_connection_button.setStyleSheet('QPushButton {color: green}')
                QTimer.singleShot(3000, self.reset_connection_colors)
            else:
                self.test_connection_button.setText("Bad Connection")
                self.test_connection_button.setStyleSheet('QPushButton {color: red}')

                QTimer.singleShot(3000, self.reset_connection_colors)
        else:
            self.test_connection_button.setText("No active session")
            QTimer.singleShot(3000, self.reset_connection_colors)




class IPTableDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.buildUI()
    
    def buildUI(self):
        self.setWindowTitle("InfraView: Table Editor")
        self.tables_textEdit = QTextEdit()

        descriptor_label = QLabel('''The format for the tables should take the form of\nsite_descriptor: owner.tablename\n\n\tsite: global.site\n\twfdisc: global.wfdisc_raw\n\torigin: myorigin.origin\n\tevent: myevent.event\n''')
        
        # OK and Cancel buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        vlayout = QVBoxLayout()
        vlayout.addWidget(self.tables_textEdit)
        vlayout.addWidget(descriptor_label)
        vlayout.addWidget(buttons)

        self.setLayout(vlayout)

    def exec_(self):
        self.initial_text = self.tables_textEdit.toPlainText().rstrip()       
        return super().exec_()

    def reset(self):
        self.tables_textEdit.setText(self.initial_text)
    
    def set_text_from_table_dict(self, tables):
        # set the text of the table editor from a dictionary of tables
        text = ""
        for key, value in tables.items():
            text += key + ':' + value + '\n'

        self.tables_textEdit.setText(text.rstrip())

    def get_tables_from_text(self):
        text = self.tables_textEdit.toPlainText().rstrip()      # the rstrip removes trailing newlines etc
        lines = text.split("\n")
        table_dict = {}
        for line in lines:
            key_val = line.split(':')
            try:
                table_dict[key_val[0]] = key_val[1]
            except IndexError:
                pass

        return table_dict

    def reject(self):
        self.reset()
        super().reject()

class IPEnvVarDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.buildUI()
    
    def buildUI(self):
        self.setWindowTitle("InfraView: Database Env Variables")
        self.vars_textEdit = QTextEdit()

        descriptor_label = QLabel("Enter database specific environment variables here.\nThese can be entered here or in the appropriate shell rc file.\nIf entered here, they will last only for the duration of the session.")
        entry_label = QLabel("Entries should have the variable and value seperated by a colon:\n\n\tTNS_ADMIN: $ORACLE_HOME/network/admin\n\tORACLE_PORT: 1523\n")
        # OK and Cancel buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        vlayout = QVBoxLayout()
        vlayout.addWidget(self.vars_textEdit)
        vlayout.addWidget(descriptor_label)
        vlayout.addWidget(entry_label)
        vlayout.addWidget(buttons)

        self.setLayout(vlayout)

    def exec_(self):
        self.initial_text = self.vars_textEdit.toPlainText().rstrip()       
        return super().exec_()

    def reset(self):
        self.vars_textEdit.setText(self.initial_text)
    
    def set_text_from_vars_dict(self, vars):
        # set the text of the table editor from a dictionary of tables
        text = ""
        for key, value in vars.items():
            text += key + ':' + value + '\n'

        self.vars_textEdit.setText(text.rstrip())

    def get_vars_from_text(self):
        text = self.vars_textEdit.toPlainText().rstrip()      # the rstrip removes trailing newlines etc
        lines = text.split("\n")
        vars_dict = {}

        for line in lines:
            key_val = line.split(':')
            try:
                vars_dict[key_val[0]] = key_val[1].strip()
            except IndexError as e:
                pass

        return vars_dict

    def reject(self):
        self.reset()
        super().reject()