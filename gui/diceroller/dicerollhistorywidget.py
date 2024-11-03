import copy
import diceroller
import enum
import gui
import logging
import typing
from PyQt5 import QtWidgets, QtCore

class DiceRollHistoryWidget(QtWidgets.QWidget):
    class _ColumnType(enum.Enum):
        Timestamp = 'Timestamp'
        Label = 'Label'
        Result = 'Result'
        Effect = 'Effect'
        Rolled = 'Rolls'
        BoonBane = 'Boon/Bane'
        Flux = 'Flux'
        Modifiers = 'Modifiers'

    _StateVersion = 'DiceRollHistoryWidget_v1'

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self._historyTable = gui.ListTable()
        self._historyTable.setColumnHeaders(DiceRollHistoryWidget._ColumnType)
        self._historyTable.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self._historyTable.setAlternatingRowColors(False)
        self._historyTable.setSortingEnabled(False)
        self._historyTable.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding)
        self._historyTable.setTextElideMode(QtCore.Qt.TextElideMode.ElideNone)
        for index, column in enumerate(DiceRollHistoryWidget._ColumnType):
            if column == DiceRollHistoryWidget._ColumnType.Timestamp:
                self._historyTable.setColumnWidth(index, 200)
            elif column == DiceRollHistoryWidget._ColumnType.Label or \
                    column == DiceRollHistoryWidget._ColumnType.Effect:
                self._historyTable.setColumnWidth(index, 300)

        widgetLayout = QtWidgets.QVBoxLayout()
        widgetLayout.setContentsMargins(0, 0, 0, 0)
        widgetLayout.addWidget(self._historyTable)

        self.setLayout(widgetLayout)

    def addResult(
            self,
            result: diceroller.DiceRollResult
            ) -> None:
        result = copy.deepcopy(result)
        self._historyTable.insertRow(0)
        self._fillTableRow(0, result)
        self._historyTable.selectRow(0)

    def clearResults(self) -> None:
        self._historyTable.removeAllRows()

    def clearSelection(self) -> None:
        self._historyTable.clearSelection()

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(self._StateVersion)

        statsState = self._historyTable.saveState()
        stream.writeUInt32(statsState.count() if statsState else 0)
        if statsState:
            stream.writeRawData(statsState.data())

        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != self._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug('Failed to restore DiceRollHistoryWidget state (Incorrect version)')
            return False

        count = stream.readUInt32()
        if count <= 0:
            return True
        statsState = QtCore.QByteArray(stream.readRawData(count))
        if not self._historyTable.restoreState(statsState):
            return False

        return True

    def _fillTableRow(
            self,
            row: int,
            result: diceroller.DiceRollResult
            ) -> None:
        for column in range(self._historyTable.columnCount()):
            columnType = self._historyTable.columnHeader(column)
            tableItem = None
            if columnType == DiceRollHistoryWidget._ColumnType.Timestamp:
                itemText = result.timestamp().astimezone().strftime('%c')
                tableItem = gui.TableWidgetItemEx(itemText)
            elif columnType == DiceRollHistoryWidget._ColumnType.Label:
                tableItem = gui.TableWidgetItemEx(result.label())
            elif columnType == DiceRollHistoryWidget._ColumnType.Rolled:
                usedRolls = []
                for roll, ignored in result.rolls():
                    if not ignored:
                        usedRolls.append(str(roll))
                itemText = '{total} (Rolls: {rolls})'.format(
                    total=result.rolledTotal(),
                    rolls=', '.join(usedRolls))
                tableItem = gui.TableWidgetItemEx(itemText)
            elif columnType == DiceRollHistoryWidget._ColumnType.BoonBane:
                # TODO: Implement this column or remove it
                tableItem = gui.TableWidgetItemEx('')
            elif columnType == DiceRollHistoryWidget._ColumnType.Flux:
                fluxType = result.fluxType()
                if fluxType != None:
                    fluxRolls = []
                    for roll in result.fluxRolls():
                        fluxRolls.append(str(roll))
                    itemText = '{total} (Type: {type}, Rolls: {rolls})'.format(
                        total=result.fluxTotal(),
                        type='Flux' if fluxType == diceroller.FluxType.Neutral else f'{fluxType.value} Flux',
                        rolls=', '.join(fluxRolls))
                    tableItem = gui.TableWidgetItemEx(itemText)
            elif columnType == DiceRollHistoryWidget._ColumnType.Modifiers:
                if result.modifierCount():
                    modifiers = []
                    for _, modifier in result.modifiers():
                        modifiers.append(f'{modifier:+}')
                    itemText = '{total:+} (DMs: {rolls})'.format(
                        total=result.modifiersTotal(),
                        rolls=', '.join(modifiers))
                    tableItem = gui.TableWidgetItemEx(itemText)
            elif columnType == DiceRollHistoryWidget._ColumnType.Result:
                tableItem = gui.FormattedNumberTableWidgetItem(
                    value=result.total())
            elif columnType == DiceRollHistoryWidget._ColumnType.Effect:
                effectType = result.effectType()
                itemText = ''
                if effectType:
                    itemText = effectType.value
                    itemText += f' (Effect: {result.effectValue()})'
                tableItem = gui.TableWidgetItemEx(itemText)

            if tableItem:
                tableItem.setTextAlignment(int(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter))
                self._historyTable.setItem(row, column, tableItem)
