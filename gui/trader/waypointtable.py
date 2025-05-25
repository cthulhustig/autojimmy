import enum
import gui
import logging
import traveller
import travellermap
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

class _CentredCheckBoxWidget(QtWidgets.QWidget):
    stateChanged = QtCore.pyqtSignal([int])

    def __init__(self) -> None:
        super().__init__()

        self._checkBox = gui.CheckBoxEx()
        self._checkBox.stateChanged.connect(lambda state: self.stateChanged.emit(state))

        if gui.isDarkModeEnabled():
            # In dark mode put an outline around the check box as they have a tendency to blend into
            # the background
            palette = self._checkBox.palette()
            palette.setColor(
                QtGui.QPalette.ColorGroup.Active,
                self.backgroundRole(),
                palette.color(QtGui.QPalette.ColorRole.WindowText))
            self._checkBox.setPalette(palette)

        layout = QtWidgets.QHBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._checkBox)

        self.setLayout(layout)

    def setCheckState(self, state: QtCore.Qt.CheckState) -> None:
        self._checkBox.setCheckState(state)

    def checkState(self) -> QtCore.Qt.CheckState:
        return self._checkBox.checkState()

class WaypointTableColumnType(enum.Enum):
    BerthingRequired = 'Berthing'

def _customWorldTableColumns(
        originalColumns: typing.List[gui.HexTable.ColumnType]
        ) -> typing.List[typing.Union[WaypointTableColumnType, gui.HexTable.ColumnType]]:
    columns = originalColumns.copy()
    try:
        index = columns.index(gui.HexTable.ColumnType.Subsector) + 1
    except ValueError:
        index = len(columns)
    columns.insert(index, WaypointTableColumnType.BerthingRequired)
    return columns

# TODO: Not sure what to do about waypoints in dead space if dead space
# is disabled. I suspect this code shouldn't be dead space aware and
# it should be the owner that is responsible for removing hexes if the
# should be removed
class WaypointTable(gui.HexTable):
    AllColumns = _customWorldTableColumns(gui.HexTable.AllColumns)
    SystemColumns = _customWorldTableColumns(gui.HexTable.SystemColumns)
    UWPColumns = _customWorldTableColumns(gui.HexTable.UWPColumns)
    EconomicsColumns = _customWorldTableColumns(gui.HexTable.EconomicsColumns)
    CultureColumns = _customWorldTableColumns(gui.HexTable.CultureColumns)
    RefuellingColumns = _customWorldTableColumns(gui.HexTable.RefuellingColumns)

    # Version 1 format used a world list rather than a hex list. Note that
    # this just used 'v1' for the format string rather than 'WaypointTable_v1'
    # Version 2 format was added when the table was switched from using worlds
    # to hexes as part of support for dead space routing
    _ContentVersion = 'WaypointTable_v2'

    def __init__(
            self,
            milieu: travellermap.Milieu,
            rules: traveller.Rules,
            columns: typing.Iterable[typing.Union[WaypointTableColumnType, gui.HexTable.ColumnType]] = AllColumns
            ) -> None:
        super().__init__(milieu=milieu, rules=rules, columns=columns)

        # Disable sorting as it doesn't make sense for a list of waypoint as
        # they're listed in order of travel. It would also break the way rows
        # are being mapped to check boxes
        self.setSortingEnabled(False)

    def isBerthingChecked(self, row: int) -> bool:
        if row < 0 or row >= self.rowCount():
            return False

        column = self.columnHeaderIndex(WaypointTableColumnType.BerthingRequired)
        checkBox: typing.Optional[_CentredCheckBoxWidget] = self.cellWidget(row, column)
        if not checkBox:
            return False
        return checkBox.checkState() == QtCore.Qt.CheckState.Checked

    def setBerthingChecked(
            self,
            row: int,
            checked: bool
            ) -> None:
        if row < 0 or row >= self.rowCount():
            return

        column = self.columnHeaderIndex(WaypointTableColumnType.BerthingRequired)
        checkBox: typing.Optional[_CentredCheckBoxWidget] = self.cellWidget(row, column)
        if checkBox:
            checkBox.setCheckState(QtCore.Qt.CheckState.Checked if checked else QtCore.Qt.CheckState.Unchecked)

    def insertHex(
            self,
            row: int,
            hex: travellermap.HexPosition
            ) -> int:
        return super().insertHex(row, hex)

    def setHex(
            self,
            row: int,
            hex: travellermap.HexPosition
            ) -> int:
        return super().setHex(row, hex)

    def removeRow(self, row: int) -> None:
        return super().removeRow(row)

    def removeAllRows(self) -> None:
        return super().removeAllRows()

    def moveSelectionUp(self) -> typing.Iterable[typing.Tuple[int, int]]:
        swappedRows = super().moveSelectionUp()
        self._swapBerthingChecks(swappedRows)
        return swappedRows

    def moveSelectionDown(self) -> typing.Iterable[typing.Tuple[int, int]]:
        swappedRows = super().moveSelectionDown()
        self._swapBerthingChecks(swappedRows)
        return swappedRows

    # NOTE: Switching the berthing column between frozen/unfrozen causes
    # the berthing check boxes to be removed. This function works around
    # this by forcing the removal of the check boxes and re-adding them.
    # If the frozen/unfrozen state of the berthing column has changed,
    # this will result in them being removed from the frozen/unfrozen table
    # and added to the other table.
    def setFrozenColumnVisualIndex(
            self,
            visualIndex: typing.Optional[int]
            ) -> None:
        column = self.columnHeaderIndex(WaypointTableColumnType.BerthingRequired)
        checkedRows = set()

        for row in range(self.rowCount()):
            if self.isBerthingChecked(row):
                checkedRows.add(row)
            self.removeCellWidget(row, column)

        super().setFrozenColumnVisualIndex(visualIndex)

        for row in range(self.rowCount()):
            self._createBerthingCheckBox(
                row=row,
                column=column,
                checked=row in checkedRows)

    def saveContent(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(WaypointTable._ContentVersion)

        bytes = super().saveContent()
        stream.writeUInt32(bytes.count() if bytes else 0)
        if bytes:
            stream.writeRawData(bytes.data())

        berthing = [self.isBerthingChecked(row=row) for row in range(self.rowCount())]
        stream.writeUInt32(len(berthing) if berthing else 0)
        for checked in berthing:
            stream.writeBool(checked)

        return state

    def restoreContent(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != WaypointTable._ContentVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore WaypointTable content (Unsupported version)')
            return False

        count = stream.readUInt32()
        if count:
            bytes = QtCore.QByteArray(stream.readRawData(count))
            if not super().restoreContent(bytes):
                return False

        count = stream.readUInt32()
        for row in range(count):
            self.setBerthingChecked(row=row, checked=stream.readBool())

        return True

    def _fillRow(
            self,
            row: int,
            hex: travellermap.HexPosition
            ) -> int:
        world = traveller.WorldManager.instance().worldByPosition(
            milieu=self._milieu,
            hex=hex)

        # Disable sorting while updating a row. We don't want any sorting to occur until all columns
        # have been updated
        sortingEnabled = self.isSortingEnabled()
        self.setSortingEnabled(False)

        try:
            super()._fillRow(row, hex)

            for column in range(self.columnCount()):
                columnType = self.columnHeader(column)
                if columnType == WaypointTableColumnType.BerthingRequired:
                    tableItem = QtWidgets.QTableWidgetItem()
                    tableItem.setData(QtCore.Qt.ItemDataRole.UserRole, (hex, world))
                    self.setItem(row, column, tableItem)
                    self._createBerthingCheckBox(row=row, column=column, checked=False)

            # Take note of the sort column item so we can determine which row index after the table
            # has been sorted
            sortItem = self.item(row, self.horizontalHeader().sortIndicatorSection())
        finally:
            self.setSortingEnabled(sortingEnabled)

        # If we don't have a sort item we assume a derived class has overridden _fillRow to add custom
        # columns and the table is currently sorted by one of those columns. In this the expectation is
        # the derived class will be handling working out the post sort row index.
        return sortItem.row() if sortItem else row

    def _createToolTip(self, item: QtWidgets.QTableWidgetItem) -> typing.Optional[str]:
        world = self.world(item.row())

        if world:
            columnType = self.columnHeader(item.column())
            if columnType == WaypointTableColumnType.BerthingRequired:
                return gui.createStringToolTip(
                    '<p>Specify if you plan to berth at this waypoint</p>' \
                    '<p>This information is used when calculating the logistics costs of the route</p>',
                    escape=False)

        return super()._createToolTip(item)

    def _createBerthingCheckBox(
            self,
            row: int,
            column: int,
            checked: bool
            ) -> None:
        world = self.world(row)
        if not world:
            return # Don't create check box for dead space

        checkBox = _CentredCheckBoxWidget()
        checkBox.setCheckState(QtCore.Qt.CheckState.Checked if checked else QtCore.Qt.CheckState.Unchecked)
        self.setCellWidget(row, column, checkBox)

    def _swapBerthingChecks(
            self,
            swappedRows: typing.Iterable[typing.Tuple[int, int]]
            ) -> None:
        column = self.columnHeaderIndex(WaypointTableColumnType.BerthingRequired)
        if column < 0:
            return

        for oldRow, newRow in swappedRows:
            newRowCheckBox: typing.Optional[_CentredCheckBoxWidget] = self.cellWidget(newRow, column)
            oldRowCheckBox: typing.Optional[_CentredCheckBoxWidget] = self.cellWidget(oldRow, column)

            newRowState = oldRowCheckBox.checkState() if oldRowCheckBox else QtCore.Qt.CheckState.Unchecked
            oldRowState = newRowCheckBox.checkState() if newRowCheckBox else QtCore.Qt.CheckState.Unchecked

            newRowWorld = self.world(newRow)
            if newRowWorld:
                if newRowCheckBox:
                    newRowCheckBox.setCheckState(newRowState)
                else:
                    self._createBerthingCheckBox(newRow, column, checked=newRowState == QtCore.Qt.CheckState.Checked)
            elif newRowCheckBox:
                self.removeCellWidget(newRow, column)

            oldRowWorld = self.world(oldRow)
            if oldRowWorld:
                if oldRowCheckBox:
                    oldRowCheckBox.setCheckState(oldRowState)
                else:
                    self._createBerthingCheckBox(oldRow, column, checked=oldRowState == QtCore.Qt.CheckState.Checked)
            elif oldRowCheckBox:
                self.removeCellWidget(oldRow, column)
