import common
import copy
import diceroller
import enum
import gui
import logging
import typing
from PyQt5 import QtWidgets, QtCore

class DiceRollHistoryWidget(QtWidgets.QWidget):
    resultSelected = QtCore.pyqtSignal([diceroller.DiceRoller, diceroller.DiceRollResult])

    class _ColumnType(enum.Enum):
        Timestamp = 'Timestamp'
        Roller = 'Roller'
        Rolls = 'Rolls'
        Modifiers = 'Modifiers'
        Result = 'Result'
        Effect = 'Effect'

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
            elif column == DiceRollHistoryWidget._ColumnType.Roller or \
                column == DiceRollHistoryWidget._ColumnType.Effect:
                self._historyTable.setColumnWidth(index, 300)
        self._historyTable.selectionModel().selectionChanged.connect(
            self._selectionChanged)

        widgetLayout = QtWidgets.QVBoxLayout()
        widgetLayout.setContentsMargins(0, 0, 0, 0)
        widgetLayout.addWidget(self._historyTable)

        self.setLayout(widgetLayout)

    def addResult(
        self,
        roller: diceroller.DiceRoller,
        result: diceroller.DiceRollResult
        ) -> None:
        roller = copy.deepcopy(roller)
        result = copy.deepcopy(result)
        self._historyTable.insertRow(0)
        self._fillTableRow(0, roller, result)
        self._historyTable.selectRow(0)

    def purgeHistory(
        self,
        roller: diceroller.DiceRoller
        ) -> None:
        pass

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
            roller: diceroller.DiceRoller,
            result: diceroller.DiceRollResult
            ) -> None:
        itemData = (roller, result)
        for column in range(self._historyTable.columnCount()):
            columnType = self._historyTable.columnHeader(column)
            tableItem = None
            if columnType == DiceRollHistoryWidget._ColumnType.Timestamp:
                itemText = common.utcnow().astimezone().strftime('%c')
                tableItem = gui.TableWidgetItemEx(itemText)
            elif columnType == DiceRollHistoryWidget._ColumnType.Roller:
                tableItem = gui.TableWidgetItemEx(roller.name())
            elif columnType == DiceRollHistoryWidget._ColumnType.Rolls:
                usedRolls = []
                ignoredRolls = []
                for roll, ignored in result.yieldRolls():
                    if ignored:
                        ignoredRolls.append(str(roll.value()))
                    else:
                        usedRolls.append(str(roll.value()))
                itemText = ','.join(usedRolls)
                if ignoredRolls:
                    itemText += ' ({ignored})'.format(
                        ignored=','.join(ignoredRolls))
                tableItem = gui.TableWidgetItemEx(itemText)
            elif columnType == DiceRollHistoryWidget._ColumnType.Modifiers:
                itemText = ''
                for modifier, _ in result.yieldModifiers():
                    itemText += common.formatNumber(
                        number=modifier.value(),
                        alwaysIncludeSign=len(itemText) > 0)
                tableItem = gui.TableWidgetItemEx(itemText)
            elif columnType == DiceRollHistoryWidget._ColumnType.Result:
                tableItem = gui.FormattedNumberTableWidgetItem(
                    value=result.total())
            elif columnType == DiceRollHistoryWidget._ColumnType.Effect:
                effectType = result.effectType()
                itemText = ''
                if effectType:
                    itemText = effectType.value
                    effectValue = result.effectValue()
                    itemText += f' (Effect: {effectValue.value()})'
                tableItem = gui.TableWidgetItemEx(itemText)

            if tableItem:
                tableItem.setTextAlignment(int(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter))
                tableItem.setData(QtCore.Qt.ItemDataRole.UserRole, itemData)
                self._historyTable.setItem(row, column, tableItem)

    def _selectionChanged(self) -> None:
        rows = self._historyTable.selectedRows()
        if not rows:
            return
        item = self._historyTable.item(rows[0], 0)
        if not item:
            return
        roller, result = item.data(QtCore.Qt.ItemDataRole.UserRole)
        self.resultSelected.emit(roller, result)
