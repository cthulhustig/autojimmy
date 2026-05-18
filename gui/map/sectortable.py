import astronomer
import enum
import gui
import logging
import typing
from PyQt5 import QtWidgets, QtCore

class SectorTable(gui.ListTable):
    class ColumnType(enum.Enum):
        Name = 'Name'
        Position = 'Position'
        Custom = 'Custom'

    AllColumns = list(ColumnType)

    _StateVersion = 'SectorTable_v1'

    def __init__(
            self,
            universe: astronomer.Universe,
            milieu: astronomer.Milieu,
            columns: typing.Iterable[ColumnType] = AllColumns
            ) -> None:
        super().__init__()

        self._universe = universe
        self._milieu = milieu

        self.setColumnHeaders(columns)
        self.resizeColumnsToContents() # Size columns to header text
        self.setSizeAdjustPolicy(
            QtWidgets.QAbstractScrollArea.SizeAdjustPolicy.AdjustToContentsOnFirstShow)
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.DefaultContextMenu)
        for column, columnType in enumerate(columns):
            if columnType == self.ColumnType.Name:
                self.setColumnWidth(column, 200)
        self._updateContent()

    def universe(self) -> astronomer.Universe:
        return self._universe

    def setUniverse(
            self,
            universe: astronomer.Universe
            ) -> None:
        if universe == self._universe:
            return

        self._universe = universe
        self._updateContent()

    def milieu(self) -> astronomer.Milieu:
        return self._milieu

    def setMilieu(
            self,
            milieu: astronomer.Milieu
            ) -> None:
        if milieu is self._milieu:
            return

        self._milieu = milieu
        self._updateContent()

    def sector(self, row: int) -> typing.Optional[astronomer.Sector]:
        tableItem = self.item(row, 0)
        if not tableItem:
            return None
        return tableItem.data(QtCore.Qt.ItemDataRole.UserRole)

    def currentSector(self) -> typing.Optional[astronomer.Sector]:
        row = self.currentRow()
        if row < 0:
            return None
        return self.sector(row)

    def setCurrentSector(self, sector: typing.Optional[astronomer.Sector]) -> None:
        if not sector:
            self.setCurrentRow(-1)
            return

        for row in range(self.rowCount()):
            if sector == self.sector(row):
                self.setCurrentRow(row)
                break

    def setCurrentSectorByPosition(self, position: typing.Optional[astronomer.SectorPosition]) -> None:
        if not position:
            self.setCurrentRow(-1)
            return

        for row in range(self.rowCount()):
            sector = self.sector(row)
            if position == sector.position():
                self.setCurrentRow(row)
                break

    def scrollToSector(
            self,
            sector: astronomer.Sector,
            hint: QtWidgets.QAbstractItemView.ScrollHint = QtWidgets.QAbstractItemView.ScrollHint.EnsureVisible
            ) -> None:
        target = None
        for row in range(self.rowCount()):
            if sector == self.sector(row):
                target = self.indexFromItem(self.item(row, 0))
                break
        if target is None:
            return

        super().scrollTo(target, hint)

    def scrollToPosition(
            self,
            position: astronomer.SectorPosition,
            hint: QtWidgets.QAbstractItemView.ScrollHint = QtWidgets.QAbstractItemView.ScrollHint.EnsureVisible
            ) -> None:
        target = None
        for row in range(self.rowCount()):
            sector = self.sector(row)
            if position == sector.position():
                target = self.indexFromItem(self.item(row, 0))
                break
        if target is None:
            return

        super().scrollTo(target, hint)

    # TODO: Implement save/restore state. Probably just store the hex of the
    # currently selected hex
    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(SectorTable._StateVersion)

        baseState = super().saveState()
        stream.writeUInt32(baseState.count() if baseState else 0)
        if baseState:
            stream.writeRawData(baseState.data())

        return state

    def restoreState(self, state: QtCore.QByteArray) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != SectorTable._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore SectorTable state (Incorrect version)')
            return False

        count = stream.readUInt32()
        if count <= 0:
            return True
        baseState = QtCore.QByteArray(stream.readRawData(count))
        if not super().restoreState(baseState):
            return False

        return True

    def _updateContent(self) -> None:
        newSectors = set(self._universe.sectors(milieu=self._milieu))
        currentSectors = set()

        # Remove any rows for goods not in the new list
        for row in range(self.rowCount() - 1, -1, -1):
            sector = self.sector(row)
            if sector not in newSectors:
                self.removeRow(row)
            else:
                currentSectors.add(sector)

        # Add rows for new goods. Sorting is turned off then
        # re-enabled at the end so it's only performed once
        sortingEnabled = self.isSortingEnabled()
        self.setSortingEnabled(False)

        try:
            sortedSectors = sorted(newSectors, key=lambda s: s.name())
            for sector in sortedSectors:
                if sector not in currentSectors:
                    row = self.rowCount()
                    self.insertRow(row)
                    self._fillRow(row, sector)
        finally:
            self.setSortingEnabled(sortingEnabled)

    def _fillRow(
            self,
            row: int,
            sector: astronomer.Sector
            ) -> int:
        # Workaround for the issue covered here, re-enabled after setting items
        # https://stackoverflow.com/questions/7960505/strange-qtablewidget-behavior-not-all-cells-populated-after-sorting-followed-b
        sortingEnabled = self.isSortingEnabled()
        self.setSortingEnabled(False)

        try:
            for column in range(self.columnCount()):
                columnType = self.columnHeader(column)
                tableItem = None
                if columnType == self.ColumnType.Name:
                    tableItem = QtWidgets.QTableWidgetItem(sector.name())
                elif columnType == self.ColumnType.Position:
                    position = sector.position()
                    tableItem = QtWidgets.QTableWidgetItem(f'({position.sectorX()}, {position.sectorY()})')
                elif columnType == self.ColumnType.Custom:
                    tableItem = QtWidgets.QTableWidgetItem('*' if sector.isCustom() else '')

                if tableItem:
                    self.setItem(row, column, tableItem)
                    tableItem.setData(QtCore.Qt.ItemDataRole.UserRole, sector)

            # Take note of the sort column item so we can determine which row index after the table
            # has been sorted
            sortItem = self.item(row, self.horizontalHeader().sortIndicatorSection())
        finally:
            self.setSortingEnabled(sortingEnabled)

        # If we don't have a sort item we assume a derived class has overridden _fillRow to add custom
        # columns and the table is currently sorted by one of those columns. In this the expectation is
        # the derived class will be handling working out the post sort row index.
        return sortItem.row() if sortItem else row
