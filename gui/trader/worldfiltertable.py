import app
import enum
import gui
import json
import logic
import logging
import typing
from PyQt5 import QtWidgets, QtCore

class WorldFilterTable(gui.ListTable):
    class ColumnType(enum.Enum):
        Type = 'Type'
        Description = 'Description'

    _ContentVersion = 'v1'

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self.setColumnHeaders(WorldFilterTable.ColumnType)
        self.horizontalHeader().setStretchLastSection(True)

    def filter(self, row: int) -> typing.Optional[logic.WorldFilter]:
        tableItem = self.item(row, 0)
        if not tableItem:
            return None
        return tableItem.data(QtCore.Qt.ItemDataRole.UserRole)

    def filters(self) -> typing.Iterable[logic.WorldFilter]:
        worlds = []
        for row in range(self.rowCount()):
            world = self.filter(row)
            if not world:
                continue
            worlds.append(world)
        return worlds

    def filterAt(self, position: QtCore.QPoint) -> typing.Optional[logic.WorldFilter]:
        item = self.itemAt(position)
        if not item:
            return None
        return self.filter(item.row())

    def insertFilter(self, row: int, filter: logic.WorldFilter) -> int:
        self.insertRow(row)
        return self._fillRow(row, filter)

    def setFilter(self, row: int, filter: logic.WorldFilter) -> int:
        return self._fillRow(row, filter)

    def addFilter(self, filter: logic.WorldFilter) -> int:
        return self.insertFilter(self.rowCount(), filter)

    def addFilters(self, filters: typing.Iterable[logic.WorldFilter]) -> None:
        # Disable sorting while inserting multiple rows then sort once after they've
        # all been added
        sortingEnabled = self.isSortingEnabled()
        self.setSortingEnabled(False)

        try:
            for filter in filters:
                self.insertFilter(self.rowCount(), filter)
        finally:
            self.setSortingEnabled(sortingEnabled)

    def removeFilter(self, filter: logic.WorldFilter) -> bool:
        removed = False
        for row in range(self.rowCount() - 1, -1, -1):
            if filter == self.filter(row):
                self.removeRow(row)
                removed = True
        return removed

    def currentFilter(self) -> typing.Optional[logic.WorldFilter]:
        row = self.currentRow()
        if row < 0:
            return None
        return self.filter(row)

    def selectedRowCount(self) -> int:
        selection = self.selectedIndexes()
        if not selection:
            return 0
        count = 0
        for index in selection:
            if index.column() == 0:
                count += 1
        return count

    def selectedFilters(self) -> typing.Iterable[logic.WorldFilter]:
        selection = self.selectedIndexes()
        if not selection:
            return None
        worlds = []
        for index in selection:
            if index.column() == 0:
                world = self.filter(index.row())
                worlds.append(world)
        return worlds

    def saveContent(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(WorldFilterTable._ContentVersion)

        data = logic.serialiseWorldFilterList(worldFilters=self.filters())
        stream.writeQString(json.dumps(data))

        return state

    def restoreContent(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != WorldFilterTable._ContentVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore WorldFilterTable content (Incorrect version)')
            return False

        try:
            data = json.loads(stream.readQString())
            self.addFilters(logic.deserialiseWorldFiltersList(
                data=data,
                rules=app.Config.instance().rules()))
        except Exception as ex:
            logging.warning(f'Failed to deserialise WorldFilterTable filter list', exc_info=ex)
            return False

        return True

    def _fillRow(
            self,
            row: int,
            filter: logic.WorldFilter
            ) -> int:
        # Workaround for the issue covered here, re-enabled after setting items
        # https://stackoverflow.com/questions/7960505/strange-qtablewidget-behavior-not-all-cells-populated-after-sorting-followed-b
        sortingEnabled = self.isSortingEnabled()
        self.setSortingEnabled(False)

        try:
            for column in range(self.columnCount()):
                columnType = self.columnHeader(column)
                if columnType == self.ColumnType.Type:
                    tableItem = QtWidgets.QTableWidgetItem()
                    if isinstance(filter, logic.NameFiler):
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, 'Name')
                    elif isinstance(filter, logic.TagLevelFiler):
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, 'Tag Level')
                    elif isinstance(filter, logic.ZoneFiler):
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, 'Zone')
                    elif isinstance(filter, logic.UWPFilter):
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, 'UWP')
                    elif isinstance(filter, logic.EconomicsFilter):
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, 'Economics')
                    elif isinstance(filter, logic.CultureFilter):
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, 'Culture')
                    elif isinstance(filter, logic.RefuellingFilter):
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, 'Refuelling')
                    elif isinstance(filter, logic.AllegianceFilter):
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, 'Allegiance')
                    elif isinstance(filter, logic.SophontFilter):
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, 'Sophont')
                    elif isinstance(filter, logic.BaseFilter):
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, 'Bases')
                    elif isinstance(filter, logic.NobilityFilter):
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, 'Nobilities')
                    elif isinstance(filter, logic.RemarksFilter):
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, 'Remarks')
                    elif isinstance(filter, logic.TradeCodeFilter):
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, 'Trade Codes')
                    elif isinstance(filter, logic.PBGFilter):
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, 'PBG')
                    else:
                        tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, 'Unknown')
                elif columnType == self.ColumnType.Description:
                    description = filter.description()
                    tableItem = QtWidgets.QTableWidgetItem()
                    tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, description)
                    tableItem.setData(QtCore.Qt.ItemDataRole.ToolTipRole, description)

                if tableItem:
                    self.setItem(row, column, tableItem)
                    tableItem.setData(QtCore.Qt.ItemDataRole.UserRole, filter)

            # Take note of the sort column item so we can determine which row index after the table
            # has been sorted
            sortItem = self.item(row, self.horizontalHeader().sortIndicatorSection())
        finally:
            self.setSortingEnabled(sortingEnabled)

        # If we don't have a sort item we assume a derived class has overridden _fillRow to add custom
        # columns and the table is currently sorted by one of those columns. In this the expectation is
        # the derived class will be handling working out the post sort row index.
        return sortItem.row() if sortItem else row
