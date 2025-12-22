from typing import Optional, Union
import pandas as pd

from PyQt5.QtWidgets import QMenu, QTableView, QAbstractItemView, QWidget
from PyQt5 import QtCore
from PyQt5.QtCore import QAbstractTableModel, Qt, pyqtSignal, pyqtSlot, QPoint


class IPDetectionTableView(QTableView):
    """
    class for detection table view
    """
    signal_delete_detections = pyqtSignal(list)

    columns = ['Name',
               'Time (UTC)',
               'F Stat.',
               'Trace Vel. (m/s)',
               'Back Azimuth',
               'Latitude',
               'Longitude',
               'Elevation (m)',
               'Start',
               'End',
               'Freq Range',
               'Array Dim.',
               'Method',
               'Event',
               'Note']

    def __init__(self, parent: QWidget = None):
        """
        initialize detection table view

        :param parent: parent widget
        """
        super().__init__(parent)

        self.parent = parent

        # initialize with empty dataframe
        self.pandas_table_model = IPPandasTableModel(pd.DataFrame(columns=self.columns))
        self.setModel(self.pandas_table_model)

        self.setContextMenuPolicy(Qt.CustomContextMenu)

        # hide the last column since it has reference to the line object
        # self.hideColumn(self.pandas_table_model.columnCount() - 1)

        self.horizontalHeader().setStretchLastSection(True)

        # we want to have a custom menu pop up when someone clicks on the row headers
        self._vertHeader = self.verticalHeader()
        self._vertHeader.setContextMenuPolicy(Qt.CustomContextMenu)
        self._vertHeader.setToolTip('You can click, Ctrl+click, or Shift+click the row\n'
                                    'number to select row(s). Then right click the row \n'
                                    'header to delete the detections')

        # set up a selection model for the table
        self.setSelectionBehavior(QAbstractItemView.SelectRows)

        # connect signals and slots
        self.connect_signals_and_slots()

    def connect_signals_and_slots(self):
        """
        connect signals to widgets
        """
        # decide if you want to be able to sort columns...
        # self.horizontalHeader().sectionClicked.connect(self.sort)

        self.signal_delete_detections.connect(self.pandas_table_model.delete_rows)
        self.customContextMenuRequested.connect(self.showContextMenu)
        self._vertHeader.customContextMenuRequested.connect(self.showHeaderContextMenu)

    def showContextMenu(self, position):
        return

    def showHeaderContextMenu(self, position: QPoint):
        """
        show context menu for the row header

        :param position: position of the context menu
        """
        row = self._vertHeader.logicalIndexAt(position)

        menu = QMenu()

        deleteRows = menu.addAction("Delete Selected")
        ret = menu.exec_(self.mapToGlobal(position))
        if ret == deleteRows:
            # get the indexes of the selected rows
            rows_to_delete = [row]
            if self.selectionModel.hasSelection():
                selection = self.selectionModel.selectedRows()
                for item in selection:
                    if item.row() not in rows_to_delete:
                        rows_to_delete.append(item.row())
            # tell the pandas model to drop those rows, and update
            self.signal_delete_detections.emit(rows_to_delete)
            self.clearSelection()

    @pyqtSlot(int)
    def sort(self, idx: int):
        """
        sort the table by column denoted by idx

        :param idx: column index to sort by
        """
        self.pandas_table_model.sort(idx, Qt.DescendingOrder)

    def get_model(self):
        """
        :return: the pandas table model
        """
        return self.pandas_table_model

    def get_dataframe(self):
        """
        :return: the dataframe in the model
        """
        return self.pandas_table_model._df

    def set_data(self, new_data: pd.DataFrame):
        """
        set the data in the table

        :param new_data: new data as pandas DataFrame
        """
        self.pandas_table_model.set_data(new_data)


class IPPandasTableModel(QAbstractTableModel):
    """
    class for pandas table model
    """
    _current_sort_column = 1
    _current_sort_order = Qt.AscendingOrder
    _column_order = None

    _df = None

    def __init__(self, df: pd.DataFrame, parent: Optional[QWidget] = None):
        """
        initialize pandas table model

        :param df: pandas DataFrame to use as the table data
        :param parent: parent widget
        """
        QAbstractTableModel.__init__(self, parent=parent)
        self._df = df
        # this sets the column order to the default order defined in the detectionview
        self._column_order = list(self._df.columns)

    def headerData(self, section: int, orientation: Qt.Orientation = QtCore.Qt.Horizontal,
                   role: Qt.ItemDataRole = QtCore.Qt.DisplayRole) -> Optional[str]:
        """
        get the header data

        :param section: section index
        :param orientation: orientation of the header
        :param role: role of the header
        :return: header data or None
        """
        if role != QtCore.Qt.DisplayRole:
            return None

        if orientation == QtCore.Qt.Horizontal:
            try:
                return self._df.columns.tolist()[section]
            except IndexError:
                return None

        elif orientation == QtCore.Qt.Vertical:
            try:
                return self._df.index.tolist()[section]
            except IndexError:
                return None

        # if not index.isValid():
        #     return None

        # if self._df is None:
        #     return None

        # return str(self._df.iloc[index.row(), index.column()])

    def data(self, index, role: Qt.ItemDataRole = QtCore.Qt.DisplayRole) -> Optional[str]:
        """
        :param index: model index
        :param role: data role
        :return: data at the given index or None
        """
        if role != QtCore.Qt.DisplayRole:
            return None

        if not index.isValid():
            return None

        if self._df is None:
            return None

        return str(self._df.iloc[index.row(), index.column()])

    @pyqtSlot(pd.DataFrame)
    def set_data(self, new_df: pd.DataFrame):
        """
        set the data in the model

        :param new_df: new pandas DataFrame
        """
        self.layoutAboutToBeChanged.emit()

        self._df = new_df
        # self.sort(self._current_sort_column, self._current_sort_order)
        # self.setColumnOrder()

        self.layoutChanged.emit()

    def rowCount(self, parent=QtCore.QModelIndex()) -> int:
        """
        :return: number of rows in the model
        """
        return len(self._df.index)

    def columnCount(self, parent=QtCore.QModelIndex()) -> int:
        """
        :return: number of columns in the model
        """
        return len(self._df.columns)

    def sort(self, column: int, order: Qt.SortOrder):
        """
        sort the model by the given column and order

        :param column: column index to sort by
        :param order: sort order (Qt.AscendingOrder or Qt.DescendingOrder)
        """
        colnames = self._df.columns.tolist()[int(column)]

        # flip the sort order if a column is reclicked
        if self._current_sort_column == column:
            if self._current_sort_order == Qt.AscendingOrder:
                self._current_sort_order = Qt.DescendingOrder
            elif self._current_sort_order == Qt.DescendingOrder:
                self._current_sort_order = Qt.AscendingOrder
        else:
            self._current_sort_column = column
            self._current_sort_order = order

        self.layoutAboutToBeChanged.emit()

        self._df.sort_values(colnames, ascending=self._current_sort_order, inplace=True)
        self._df.reset_index(inplace=True, drop=True)

        self.layoutChanged.emit()

    def append(self, arrival: dict):
        """
        append a new arrival to the model

        :param arrival: arrival data as a dictionary
        """
        # build a temp dataframe from the arrival
        df_new = pd.DataFrame([arrival], columns=arrival.keys())

        self.layoutAboutToBeChanged.emit()

        self._df = pd.concat([self._df, df_new], axis=0).reset_index()

        # re-sort so new value will be in correct place
        # self.sort(self._current_sort_column, self._current_sort_order)
        # self.setColumnOrder()

        self.layoutChanged.emit()

    @pyqtSlot(list)
    def delete_rows(self, rows: Union[list, str]):
        """
        delete rows from the model

        :param rows: single label or list of row indices to delete
        """
        self.layoutAboutToBeChanged.emit()

        self._df = self._df.drop(rows)
        self._df.reset_index(inplace=True, drop=True)

        self.layoutChanged.emit()

    def setColumnOrder(self):
        """
        set the column order to the predefined order
        """
        self._df = self._df[self._column_order]
