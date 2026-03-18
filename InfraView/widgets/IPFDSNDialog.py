import obspy
from obspy.clients.fdsn import Client
from obspy.clients.seedlink import Client as SeedlinkClient
from obspy.core import UTCDateTime
from obspy.clients.fdsn.header import URL_MAPPINGS
from obspy.core.stream import Stream
from obspy.core.trace import Trace
from obspy.core.inventory import Inventory

import numpy as np

from PyQt5.QtWidgets import (QDialog, QDialogButtonBox, QWidget, QAbstractItemView, QLineEdit, QFormLayout,
                             QComboBox, QLabel, QVBoxLayout, QHBoxLayout,
                             QGroupBox, QPushButton, QDateEdit, QTimeEdit,
                             QSizePolicy, QSpinBox, QListWidget, QFileDialog)

from PyQt5.QtCore import pyqtSignal, pyqtSlot, QDate, Qt, QDateTime, QTime

from InfraView.widgets import IPStationBrowser
from InfraView.widgets import IPUtils


class IPFDSNDialog(QDialog):
    """
    class for fdsn dialog
    """
    fdsnWidget = None

    def __init__(self, parent: QWidget):
        """
        initialize

        :param parent: parent widget
        """
        super(IPFDSNDialog, self).__init__(parent)
        self.buildUI()

    def buildUI(self):
        """
        build UI
        """
        self.setWindowTitle(self.tr('InfraView: FDSN Import'))

        self.fdsnWidget = IPFDSNWidget()

        # OK and Cancel buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(self.fdsnWidget)
        layout.addWidget(buttons)

        self.setLayout(layout)

        self.resize(400, self.height())

    def getStreams(self) -> Stream:
        """
        :return: stream of waveforms
        """
        # pass through to get the stream info
        return self.fdsnWidget.getStreams()

    def getInventory(self) -> Inventory:
        """
        :return: inventory of station
        """
        # pass through to get the inventory info out
        return self.fdsnWidget.getInventory()


class IPNewFDSNDialog(QDialog):
    """
    class for new fdsn dialog
    """
    def __init__(self, parent: QWidget):
        """
        initialize

        :param parent: parent widget
        """
        super().__init__()
        self.buildUI()

    def buildUI(self):
        """
        build UI
        """
        self.setWindowTitle("InfraView: Add FDSN Service")
        form_layout = QFormLayout()
        name_label = QLabel("Service Name")
        self.service_name_edit = QLineEdit()
        url_label = QLabel("Service URL")
        self.service_url_edit = QLineEdit()
        self.service_url_edit.setPlaceholderText("ex: http://service.iris.edu")
        self.service_url_edit.setMinimumWidth(220)

        form_layout.addRow(name_label, self.service_name_edit)
        form_layout.addRow(url_label, self.service_url_edit)

        # OK and Cancel buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        main_layout = QVBoxLayout()
        main_layout.addLayout(form_layout)
        main_layout.addWidget(buttons)

        self.setLayout(main_layout)

    def get_service(self):
        return self.service_name_edit.text(), self.service_url_edit.text()


class IPFDSNWidget(QWidget):

    sigTracesReplaced = pyqtSignal(Stream, Inventory)
    sigTracesAppended = pyqtSignal(Stream, Inventory)

    stream = None
    inventory = None

    def __init__(self, parent=None):
        super().__init__()
        self.parent = parent
        self.buildUI()

    def buildUI(self):
        """
        build UI
        """
        # Put together the options container
        formLayout = QFormLayout()
        optionsContainer = QWidget()
        optionsContainer.setLayout(formLayout)

        # --- Source selector (FDSN vs SeedLink) ---
        self.source_combo = QComboBox()
        self.source_combo.addItems(['FDSN', 'SeedLink'])
        self.source_combo.setCurrentText('FDSN')
        self.source_combo.currentTextChanged.connect(self.source_changed)
        label_source = QLabel(self.tr('Source:'))
        formLayout.addRow(label_source, self.source_combo)

        # in order to allow for custom fdsn servers, we have to make our own fdsn dictionary that we can append to
        self.fdsn_dictionary = URL_MAPPINGS
        # self.fdsn_dictionary.update({'BEER':'https://fdsnws.ilikebeer.com'})

        # First lets populate the client drop down
        self.cb = QComboBox()
        self.cb.setMinimumWidth(150)
        self.cb.currentTextChanged.connect(self.service_changed)
        self.label_service_name = QLabel(self.tr('Service:'))

        self.cb.addItems(self.fdsn_dictionary.keys())
        self.cb.setCurrentText('IRIS')
        self.cb.setToolTip(self.fdsn_dictionary['IRIS'])
        self.cb.currentIndexChanged[str].connect(self.onActivated_cb)

        # add button for new fdsn service
        self.new_service_button = QPushButton("+")
        self.new_service_button.setToolTip("Add an FDSN service")
        self.new_service_button.clicked.connect(self.add_service)

        service_layout = QHBoxLayout()
        service_layout.addWidget(self.cb)
        service_layout.addWidget(self.new_service_button)

        # --- SeedLink-specific fields ---
        self.label_seedlink_ip = QLabel(self.tr('SeedLink IP:'))
        self.seedlink_ip_edit = QLineEdit()
        self.seedlink_ip_edit.setMinimumWidth(170)
        self.seedlink_ip_edit.setPlaceholderText('e.g. 192.168.1.100')
        self.seedlink_ip_edit.setToolTip('IP address or hostname of the SeedLink server')

        self.label_seedlink_port = QLabel(self.tr('SeedLink Port:'))
        self.seedlink_port_spin = QSpinBox()
        self.seedlink_port_spin.setMinimumWidth(170)
        self.seedlink_port_spin.setMinimum(1)
        self.seedlink_port_spin.setMaximum(65535)
        self.seedlink_port_spin.setValue(18000)
        self.seedlink_port_spin.setToolTip('Port number for the SeedLink server (default: 18000)')

        self.label_stationxml = QLabel(self.tr('Station XML:'))
        self.stationxml_path_edit = QLineEdit()
        self.stationxml_path_edit.setMinimumWidth(170)
        self.stationxml_path_edit.setReadOnly(True)
        self.stationxml_path_edit.setPlaceholderText('(optional) Load StationXML for inventory')
        self.stationxml_browse_button = QPushButton('Browse...')
        self.stationxml_browse_button.setToolTip('Load a StationXML file for station metadata (optional). '
                                                 'If not provided, inventory will be fetched from IRIS.')
        self.stationxml_browse_button.clicked.connect(self.browseStationXML)
        stationxml_layout = QHBoxLayout()
        stationxml_layout.addWidget(self.stationxml_path_edit)
        stationxml_layout.addWidget(self.stationxml_browse_button)

        validator = IPUtils.CapsValidator(self)

        label_network_name = QLabel(self.tr('Network: '))
        self.networkNameBox = QLineEdit()
        self.networkNameBox.setMinimumWidth(170)
        self.networkNameBox.setToolTip('Wildcards OK \nCan be SEED network codes or data center defined codes.'
                                       '\nMultiple codes are comma-separated (e.g. "IU,TA").')
        self.networkNameBox.setValidator(validator)

        label_station_name = QLabel(self.tr('Station: '))
        self.stationNameBox = QLineEdit()
        self.stationNameBox.setMinimumWidth(170)
        self.stationNameBox.setToolTip('Wildcards OK \nOne or more SEED station codes. \nMultiple codes are '
                                       'comma-separated (e.g. "ANMO,PFO")')
        self.stationNameBox.setValidator(validator)

        label_location_str = QLabel(self.tr('Location:'))
        self.location_Box = QLineEdit('*')
        self.location_Box.setMinimumWidth(170)
        self.location_Box.setToolTip('Wildcards OK \nOne or more SEED location identifiers. \nMultiple identifiers '
                                     'are comma-separated (e.g. "00,01"). \nAs a special case “--“ (two dashes) will '
                                     'be translated to a string of two space characters to match blank location IDs.')
        self.location_Box.setValidator(validator)

        label_channel_str = QLabel(self.tr('Channel:'))
        self.channel_Box = QLineEdit('BDF')
        self.channel_Box.setMinimumWidth(170)
        self.channel_Box.setToolTip('Wildcards OK \nOne or more SEED channel codes. \nMultiple codes are '
                                    'comma-separated (e.g. "BHZ,HHZ")')
        self.channel_Box.setValidator(validator)

        label_startDate = QLabel(self.tr('Start Date (UTC):'))
        self.startDate_edit = QDateEdit()
        self.startDate_edit.setMinimumWidth(170)
        self.startDate_edit.setMinimumDate(QDate(1900, 1, 1))
        self.startDate_edit.setDisplayFormat('yyyy-MM-dd')
        self.startDate_edit.setDate(QDateTime.currentDateTimeUtc().date().addDays(-1))

        label_startTime = QLabel(self.tr('Start Time (UTC):'))
        self.startTime_edit = QTimeEdit()
        self.startTime_edit.setTime(QTime())
        self.startTime_edit.setMinimumWidth(170)
        self.startTime_edit.setDisplayFormat('HH:mm:ss.zzz')

        label_traceLength = QLabel(self.tr('Trace Length (s)'))
        self.traceLength_t = QSpinBox()
        self.traceLength_t.setMinimumWidth(170)
        self.traceLength_t.setMinimum(1)
        self.traceLength_t.setMaximum(999999999)
        self.traceLength_t.setValue(3600)

        replaceWaveButton = QPushButton('Replace')
        replaceWaveButton.clicked.connect(self.onClicked_replace)
        appendWaveButton = QPushButton('Append')
        appendWaveButton.clicked.connect(self.onClicked_append)

        self.stationListWidget = QListWidget()
        self.stationListWidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.stationListWidget.itemSelectionChanged.connect(self.populateStationInfoFromStationList)

        self.browserButton = QPushButton('Station Browser')
        self.browserButton.clicked.connect(self.onClicked_browserButton)

        formLayout.addRow(self.label_service_name, service_layout)

        # SeedLink fields (hidden by default)
        formLayout.addRow(self.label_seedlink_ip, self.seedlink_ip_edit)
        formLayout.addRow(self.label_seedlink_port, self.seedlink_port_spin)
        formLayout.addRow(self.label_stationxml, stationxml_layout)

        horizontalLineWidget = QWidget()
        horizontalLineWidget.setFixedHeight(2)
        horizontalLineWidget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        formLayout.addWidget(horizontalLineWidget)

        formLayout.addRow(label_network_name, self.networkNameBox)
        formLayout.addRow(label_station_name, self.stationNameBox)
        formLayout.addRow(label_location_str, self.location_Box)
        formLayout.addRow(label_channel_str, self.channel_Box)
        formLayout.addRow(label_startDate, self.startDate_edit)
        formLayout.addRow(label_startTime, self.startTime_edit)
        formLayout.addRow(label_traceLength, self.traceLength_t)

        horzLayout = QHBoxLayout(self)
        horzLayout.addWidget(replaceWaveButton)
        horzLayout.addWidget(appendWaveButton)
        addGroupBox = QGroupBox("Get Waveform(s)")
        addGroupBox.setLayout(horzLayout)

        vertlayout = QVBoxLayout(self)
        vertlayout.addWidget(optionsContainer)
        vertlayout.addWidget(addGroupBox)
        vertlayout.addWidget(self.stationListWidget)
        vertlayout.addWidget(self.browserButton)

        self.setLayout(vertlayout)

        # create dialogs here so that you only create it once, from here on you just run exec_() to make it pop up
        self.stationDialog = IPStationBrowser.IPStationDialog(self)
        self.add_serviceDialog = IPNewFDSNDialog(self)

        self.stationDialog.stationBrowser.channel_edit.textChanged.connect(self.channel_Box.setText)
        self.channel_Box.textChanged.connect(self.stationDialog.stationBrowser.channel_edit.textChanged)

        # Initialize field visibility to FDSN mode
        self.source_changed('FDSN')

    def source_changed(self, source):
        """
        Toggle visibility of FDSN vs SeedLink fields based on the selected source.

        :param source: 'FDSN' or 'SeedLink'
        """
        is_fdsn = (source == 'FDSN')
        is_seedlink = (source == 'SeedLink')

        # FDSN-specific widgets
        self.label_service_name.setVisible(is_fdsn)
        self.cb.setVisible(is_fdsn)
        self.new_service_button.setVisible(is_fdsn)
        self.browserButton.setVisible(is_fdsn)
        self.stationListWidget.setVisible(is_fdsn)

        # SeedLink-specific widgets
        self.label_seedlink_ip.setVisible(is_seedlink)
        self.seedlink_ip_edit.setVisible(is_seedlink)
        self.label_seedlink_port.setVisible(is_seedlink)
        self.seedlink_port_spin.setVisible(is_seedlink)
        self.label_stationxml.setVisible(is_seedlink)
        self.stationxml_path_edit.setVisible(is_seedlink)
        self.stationxml_browse_button.setVisible(is_seedlink)

    def browseStationXML(self):
        """
        Open a file dialog to select a StationXML file for SeedLink inventory.
        """
        fname, _ = QFileDialog.getOpenFileName(
            self, 'Select StationXML File', '', 'StationXML Files (*.xml);;All Files (*)'
        )
        if fname:
            self.stationxml_path_edit.setText(fname)

    def add_service(self):
        """
        add fdsn service
        """
        if self.add_serviceDialog.exec_():
            name, url = self.add_serviceDialog.get_service()
            self.fdsn_dictionary[name] = url
            self.cb.addItem(name)
            self.cb.setCurrentText(name)
            self.cb.setToolTip(url)

    @pyqtSlot(str)
    def service_changed(self, name):
        """
        function to handle service change
        """
        self.cb.setToolTip(self.fdsn_dictionary[name])

    def onClicked_browserButton(self):
        """
        function to handle browser button click
        """
        if self.stationDialog.exec_(self.startDate_edit.date(),
                                    network=self.networkNameBox.text(),
                                    station=self.stationNameBox.text(),
                                    location=self.location_Box.text(),
                                    channel=self.channel_Box.text()):
            self.inventory = self.stationDialog.getInventory()

            inv_contents = self.inventory.get_contents()
            stationList = []

            # fill up the stationList with stations
            for item in inv_contents['stations']:
                stationList.append(item.strip())
            self.stationListWidget.clear()
            self.stationListWidget.addItems(stationList)

            if self.stationDialog.getStartDate() is not None:
                self.startDate_edit.setDate(self.stationDialog.getStartDate())

    # def populateWithEventInfo(self):
    #     if self.parent.eventWidget.hasValidEvent():
    #         self.currentEvent = self.parent.eventWidget.Dict()
    #     else:
    #         msgBox = QMessageBox()
    #         msgBox.setIcon(QMessageBox.Warning)
    #         msgBox.setText('There is not a valid event in the Event Tab')
    #         msgBox.setWindowTitle("Oops...")
    #         msgBox.exec_()
    #         return

    #     if self.currentEvent is not None:
    #         date = self.currentEvent['UTC Date']
    #         time = self.currentEvent['UTC Time'][0:5]

    #     qdate = QDate.fromString(date, 'yyyy-MM-dd')
    #     qtime = QTime.fromString(time, 'HH:mm')
    #     qtime.addSecs(-5*60)  # start about 5 minutes before event

    #     self.startDate_edit.setDate(qdate)
    #     self.startTime_edit.setTime(qtime)

    #     self.eventInfoPopulated = True

    # # if someone edits the event info, reflect the changes here
    # @QtCore.pyqtSlot(dict)
    # def updateEventInfo(self, event):
    #     if not self.eventInfoPopulated:
    #         return

    #     if self.parent.eventWidget.hasValidEvent():
    #         self.currentEvent = event

    #     if self.currentEvent is not None:
    #         date = event['UTC Date']
    #         time = event['UTC Time'][0:5]

    #     qdate = QDate.fromString(date, 'yyyy-MM-dd')
    #     qtime = QTime.fromString(time, 'HH:mm')
    #     qtime.addSecs(-5*60)  # start about 5 minutes before event

    #     self.startDate_edit.setDate(qdate)
    #     self.startTime_edit.setTime(qtime)

    def populateStationInfoFromStationList(self):
        """
        populate station info from station list
        """
        items = self.stationListWidget.selectedItems()
        if len(items) < 1:
            return  # nothing to do

        netList = []
        staList = []

        for item in items:
            text = item.text()
            text = text.split(' ')[0]
            netSta = text.split('.')

            netList.append(netSta[0])
            staList.append(netSta[1])

            netList = list(set(netList))
            staList = list(set(staList))

            netString = ''
            for net in netList:
                netString = netString + net + ', '
            staString = ''
            for sta in staList:
                staString = staString + sta + ', '

        self.networkNameBox.setText(netString[:-2])
        self.stationNameBox.setText(staString[:-2])

    def onActivated_cb(self, key):
        """
        function to handle combo box activation
        """
        if (key != 'choose...'):
            url = URL_MAPPINGS[key]

    def onClicked_replace(self):
        """
        function to handle click on replace button
        """
        self.downloadWaveforms()
        if self.stream is not None and self.inventory is not None:
            self.sigTracesReplaced.emit(self.stream, self.inventory)

    def onClicked_append(self):
        """
        function to handle click on append button
        """
        self.downloadWaveforms()
        if self.stream is not None and self.inventory is not None:
            self.sigTracesAppended.emit(self.stream, self.inventory)

    @pyqtSlot(str, str)
    def add_custom_fdsn(self, name: str, url: str):
        """
        function to add custom fdsn service

        :param name: name of service
        :param url: url of service
        """
        self.fdsn_dictionary.update({name: url})
        # for brevity, lets just clear the combobox and repopulate it
        self.cb.clear()
        for key in sorted(self.fdsn_dictionary.keys()):
            self.cb.addItem(key)
        self.cb.setCurrentText(name)

    # get waveform button was clicked
    def downloadWaveforms(self):
        """
        function to handle download waveforms
        """
        source = self.source_combo.currentText()

        # Clear old streams because we don't need them anymore
        self.clearWaveforms()

        # Collect shared fields
        network = self.networkNameBox.text().upper().replace(' ', '')
        self.networkNameBox.setText(network)
        station = self.stationNameBox.text().upper().replace(' ', '')
        self.stationNameBox.setText(station)
        location = self.location_Box.text().upper().replace(' ', '')
        self.location_Box.setText(location)
        channel = self.channel_Box.text().upper().replace(' ', '')
        self.channel_Box.setText(channel)
        date = self.startDate_edit.date().toPyDate()
        time = self.startTime_edit.time().toPyTime()
        traceLength = self.traceLength_t.value()
        utcString = str(date) + 'T' + str(time)
        startTime = UTCDateTime(utcString)
        endTime = startTime + traceLength

        # Check for unfilled boxes
        if (network == '' or station == '' or channel == ''):
            IPUtils.errorPopup('You are missing some important info...\nNetwork, Station, Location, and Channel are '
                               'all required data.')
            return

        if source == 'SeedLink':
            self._downloadFromSeedLink(network, station, location, channel, startTime, endTime)
        else:
            self._downloadFromFDSN(network, station, location, channel, startTime, endTime)

    def _downloadFromFDSN(self, network, station, location, channel, startTime, endTime):
        """
        Download waveforms and inventory from an FDSN service.
        """
        service = self.cb.currentText()
        if (service == 'choose...'):
            IPUtils.errorPopup('Please select a service to search')
            return

        client = Client(self.fdsn_dictionary[service])

        try:
            self.stream = client.get_waveforms(network, station, location, channel, startTime, endTime)
        except Exception:
            IPUtils.errorPopup('Failure loading waveform. \nDouble check that the values you entered are valid and '
                               'the time and date are appropriate.')
            return

        for trace in self.stream:
            trace.data = trace.data - np.mean(trace.data)
        self.stream.merge(fill_value=0)

        # Now get the corresponding stations
        try:
            self.inventory = client.get_stations(network=network, station=station, channel=channel,
                                                 starttime=startTime, endtime=endTime, level='channel')
        except Exception:
            IPUtils.errorPopup('Failure loading Inventory.  \nDouble check that the values you entered are valid and '
                               'the time and date are appropriate.')
            return

    def _downloadFromSeedLink(self, network, station, location, channel, startTime, endTime):
        """
        Download waveforms from a SeedLink server and load inventory from
        a StationXML file or fall back to IRIS.
        """
        ip = self.seedlink_ip_edit.text().strip()
        port = self.seedlink_port_spin.value()

        if not ip:
            IPUtils.errorPopup('Please enter a SeedLink server IP address.')
            return

        try:
            sl_client = SeedlinkClient(ip, port=port, timeout=180)
        except Exception as e:
            IPUtils.errorPopup(f'Failed to connect to SeedLink server at {ip}:{port}\n{e}')
            return

        try:
            self.stream = sl_client.get_waveforms(network, station, location, channel, startTime, endTime)
        except Exception as e:
            IPUtils.errorPopup(f'Failure loading waveforms from SeedLink.\n{e}')
            return

        if self.stream is None or len(self.stream) == 0:
            IPUtils.errorPopup('No waveforms returned from SeedLink server.')
            return

        for trace in self.stream:
            trace.data = trace.data - np.mean(trace.data)
        self.stream.merge(fill_value=0)

        # Load inventory: prefer StationXML file if provided, otherwise fall back to IRIS
        xml_path = self.stationxml_path_edit.text().strip()
        if xml_path:
            try:
                self.inventory = obspy.read_inventory(xml_path)
            except Exception as e:
                IPUtils.errorPopup(f'Failed to read StationXML file:\n{xml_path}\n{e}')
                return
        else:
            try:
                self.inventory = Client('IRIS').get_stations(
                    network=network, station=station, channel=channel,
                    starttime=startTime, endtime=endTime, level='channel'
                )
            except Exception as e:
                IPUtils.errorPopup(f'No StationXML file provided and failed to fetch inventory from IRIS.\n{e}')
                return

    def getStreams(self) -> Stream:
        """
        :return: stream of waveforms
        """
        return self.stream

    def getInventory(self) -> Inventory:
        """
        :return: inventory of station
        """
        return self.inventory

    def getService(self) -> str:
        """
        :return: selected service
        """
        return self.cb.currentText()

    def clearWaveforms(self):
        """
        clear waveforms
        """
        self.stream = None
        self.inventory = None

    def clear(self):
        """
        reset all fields to defaults
        """
        self.clearWaveforms()
        self.stationListWidget.clear()
        self.cb.setCurrentText('IRIS')  # default to IRIS because why the hell not?
        self.networkNameBox.clear()
        self.stationNameBox.clear()
        self.location_Box.setText('*')
        self.channel_Box.setText('*')
        self.startDate_edit.setDate(self.startDate_edit.minimumDate())
        self.startTime_edit.setTime(self.startTime_edit.minimumTime())
        self.traceLength_t.setValue(3600)
