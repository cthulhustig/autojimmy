import enum
import gui
import json
import logging
import logic
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
        index = columns.index(gui.HexTable.ColumnType.Sector) + 1
    except ValueError:
        index = len(columns)
    columns.insert(index, WaypointTableColumnType.BerthingRequired)
    return columns

# TODO: This needs updated to (optionally) support selecting dead space waypoints
# TODO: The check boxes should be disabled if the row is for dead space
class WaypointTable(gui.HexTable):
    AllColumns = _customWorldTableColumns(gui.HexTable.AllColumns)
    SystemColumns = _customWorldTableColumns(gui.HexTable.SystemColumns)
    UWPColumns = _customWorldTableColumns(gui.HexTable.UWPColumns)
    EconomicsColumns = _customWorldTableColumns(gui.HexTable.EconomicsColumns)
    CultureColumns = _customWorldTableColumns(gui.HexTable.CultureColumns)
    RefuellingColumns = _customWorldTableColumns(gui.HexTable.RefuellingColumns)

    _ContentVersion = 'v1'

    # Store checked state as an object rather than just a bool so the check
    # box widget callbacks can be configured to update the object so they
    # don't need updated if the associated row changes
    class _BerthingState(object):
        def __init__(self):
            self.checked = False

    def __init__(
            self,
            columns: typing.Iterable[typing.Union[WaypointTableColumnType, gui.HexTable.ColumnType]] = AllColumns
            ) -> None:
        super().__init__(columns=columns)
        self._berthingStates: typing.List[WaypointTable._BerthingState] = []

    def isBerthingChecked(self, row: int) -> bool:
        return self._berthingStates[row].checked

    def setBerthingChecked(
            self,
            row: int,
            checked: bool
            ) -> None:
        self._berthingStates[row].checked = checked
        for column in range(self.columnCount()):
            columnType = self.columnHeader(column)
            if columnType == WaypointTableColumnType.BerthingRequired:
                widget = self.cellWidget(row, column)
                assert(isinstance(widget, _CentredCheckBoxWidget))
                widget.setCheckState(QtCore.Qt.CheckState.Checked if checked else QtCore.Qt.CheckState.Unchecked)

    def insertHex(
            self,
            row: int,
            pos: typing.Union[travellermap.HexPosition, traveller.World]
            ) -> int:
        self._berthingStates.insert(row, WaypointTable._BerthingState())
        return super().insertHex(row, pos)

    def setHex(
            self,
            row: int,
            pos: typing.Union[travellermap.HexPosition, traveller.World]
            ) -> int:
        self._berthingStates[row].checked = False
        return super().setHex(row, pos)

    def removeRow(self, row: int) -> None:
        self._berthingStates.pop(row)
        return super().removeRow(row)

    def removeAllRows(self) -> None:
        self._berthingStates.clear()
        return super().removeAllRows()

    def moveSelectionUp(self) -> typing.Iterable[typing.Tuple[int, int]]:
        swappedRows = super().moveSelectionUp()
        self._swapBerthingChecks(swappedRows)
        return swappedRows

    def moveSelectionDown(self) -> typing.Iterable[typing.Tuple[int, int]]:
        swappedRows = super().moveSelectionDown()
        self._swapBerthingChecks(swappedRows)
        return swappedRows

    def setFrozenColumnVisualIndex(
            self,
            visualIndex: typing.Optional[int]
            ) -> None:
        self._removeBerthingCheckBoxes()
        result = super().setFrozenColumnVisualIndex(visualIndex)
        self._restoreBerthingCheckBoxes()
        return result

    def saveContent(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(WaypointTable._ContentVersion)

        # TODO: Disabled until I update serialisation
        #items = []
        #for row in range(self.rowCount()):
        #    world = self.world(row)
        #    worldData = logic.serialiseWorld(world=world)
        #    worldData['berthing'] = self.isBerthingChecked(row)
        #    items.append(worldData)
        #stream.writeQString(json.dumps({'worlds': items}))

        return state

    def restoreContent(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != WaypointTable._ContentVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore WaypointTable content (Incorrect version)')
            return False

        # TODO: Disabled until I update serialisation
        #try:
        #    data = json.loads(stream.readQString())
        #    items = data.get('worlds')
        #    if items == None:
        #        raise RuntimeError('WaypointTable world list is missing worlds element')
        #
        #    for item in items:
        #        world = logic.deserialiseWorld(data=item)
        #        if not world:
        #            continue
        #        berthing = item.get('berthing')
        #        if berthing == None:
        #            raise RuntimeError('WaypointTable world list item is missing berthing element')
        #
        #        row = self.addWorld(world)
        #        self.setBerthingChecked(row=row, checked=berthing)
        #except Exception as ex:
        #    logging.warning(f'Failed to deserialise WorldTable world list', exc_info=ex)
        #    return False

        return True

    def _fillRow(
            self,
            row: int,
            pos: travellermap.HexPosition,
            world: typing.Optional[traveller.World]
            ) -> int:
        # Disable sorting while updating a row. We don't want any sorting to occur until all columns
        # have been updated
        sortingEnabled = self.isSortingEnabled()
        self.setSortingEnabled(False)

        try:
            super()._fillRow(row, pos, world)

            if world:
                for column in range(self.columnCount()):
                    columnType = self.columnHeader(column)
                    if columnType == WaypointTableColumnType.BerthingRequired:
                        tableItem = QtWidgets.QTableWidgetItem()
                        tableItem.setData(QtCore.Qt.ItemDataRole.UserRole, (pos, world))
                        self.setItem(row, column, tableItem)
                        self._createBerthingCheckBox(row=row, column=column)

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
            column: int
            ) -> _CentredCheckBoxWidget:
        berthingState = self._berthingStates[row]
        checkBox = _CentredCheckBoxWidget()
        checkBox.stateChanged.connect(lambda checkedState: self._berthingCheckChanged(berthingState, checkedState))
        checkBox.setCheckState(QtCore.Qt.CheckState.Checked if berthingState.checked else QtCore.Qt.CheckState.Unchecked)
        self.setCellWidget(row, column, checkBox)

    def _removeBerthingCheckBoxes(self) -> None:
        for column in range(self.columnCount()):
            columnType = self.columnHeader(column)
            if columnType == WaypointTableColumnType.BerthingRequired:
                for row in range(self.rowCount()):
                    self.removeCellWidget(row, column)

    def _restoreBerthingCheckBoxes(self) -> None:
        for column in range(self.columnCount()):
            columnType = self.columnHeader(column)
            if columnType == WaypointTableColumnType.BerthingRequired:
                for row in range(self.rowCount()):
                    self._createBerthingCheckBox(row=row, column=column)

    def _swapBerthingChecks(self, swappedRows: typing.Iterable[typing.Tuple[int, int]]) -> None:
        berthingColumn = self.columnHeaderIndex(WaypointTableColumnType.BerthingRequired)
        if berthingColumn < 0:
            return

        for oldRow, newRow in swappedRows:
            oldCheckBox = self.cellWidget(oldRow, berthingColumn)
            assert(isinstance(oldCheckBox, _CentredCheckBoxWidget))
            newCheckBox = self.cellWidget(newRow, berthingColumn)
            assert(isinstance(newCheckBox, _CentredCheckBoxWidget))
            oldCheckState = oldCheckBox.checkState()
            newCheckState = newCheckBox.checkState()
            oldCheckBox.setCheckState(newCheckState)
            newCheckBox.setCheckState(oldCheckState)

    def _berthingCheckChanged(
            self,
            berthingState: 'WaypointTable._BerthingState',
            checkedState: int
            ) -> None:
        berthingState.checked = QtCore.Qt.CheckState(checkedState) == QtCore.Qt.CheckState.Checked
