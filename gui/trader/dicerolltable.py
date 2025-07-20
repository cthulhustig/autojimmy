import common
import enum
import gui
import typing
from PyQt5 import QtWidgets, QtCore

class DiceRollTable(gui.ListTable):
    class ColumnType(enum.Enum):
        Description = 'Description'
        RollResult = 'Roll Result'
        DieCount = 'Die Count'

    AllColumns = [
        ColumnType.Description,
        ColumnType.RollResult,
        ColumnType.DieCount
    ]

    def __init__(
            self,
            columns: typing.Iterable[ColumnType] = AllColumns,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self.setColumnHeaders(columns)
        self.resizeColumnsToContents() # Size columns to header text
        self.setSizeAdjustPolicy(
            QtWidgets.QAbstractScrollArea.SizeAdjustPolicy.AdjustToContentsOnFirstShow)

        # Disable sorting as dice rolls should be kept in the order the occurred in
        self.setSortingEnabled(False)

    def diceRoll(self, row: int) -> typing.Optional[common.DiceRollResult]:
        tableItem = self.item(row, 0)
        if not tableItem:
            return None
        return tableItem.data(QtCore.Qt.ItemDataRole.UserRole)

    def diceRolls(self) -> typing.Iterable[common.DiceRollResult]:
        diceRolls = []
        for row in range(self.rowCount()):
            diceRoll = self.diceRoll(row)
            if not diceRoll:
                continue
            diceRolls.append(diceRoll)
        return diceRolls

    def insertDiceRoll(self, row: int, diceRoll: common.DiceRollResult) -> int:
        self.insertRow(row)
        return self._fillRow(row, diceRoll)

    def addDiceRoll(
            self,
            diceRoll: common.DiceRollResult
            ) -> int:
        return self.insertDiceRoll(self.rowCount(), diceRoll)

    def addDiceRolls(
            self,
            diceRolls: typing.Iterable[common.DiceRollResult]
            ) -> None:
        for diceRoll in diceRolls:
            self.addDiceRoll(diceRoll)

    def setDiceRolls(
            self,
            diceRolls: typing.Iterable[common.DiceRollResult]
            ) -> None:
        self.removeAllRows()
        self.addDiceRolls(diceRolls)

    def _fillRow(
            self,
            row: int,
            diceRoll: common.DiceRollResult
            ) -> int:
        # Workaround for the issue covered here, re-enabled after setting items
        # https://stackoverflow.com/questions/7960505/strange-qtablewidget-behavior-not-all-cells-populated-after-sorting-followed-b
        sortingEnabled = self.isSortingEnabled()
        self.setSortingEnabled(False)

        try:
            for column in range(self.columnCount()):
                columnType = self.columnHeader(column)
                tableItem = None
                if columnType == self.ColumnType.Description:
                    tableItem = QtWidgets.QTableWidgetItem(diceRoll.name())
                elif columnType == self.ColumnType.DieCount:
                    tableItem = gui.FormattedNumberTableWidgetItem(diceRoll.dieCount())
                elif columnType == self.ColumnType.RollResult:
                    tableItem = gui.FormattedNumberTableWidgetItem(diceRoll.result())

                if tableItem:
                    self.setItem(row, column, tableItem)
                    tableItem.setData(QtCore.Qt.ItemDataRole.UserRole, diceRoll)

            # Take note of the sort column item so we can determine which row index after the table
            # has been sorted
            sortItem = self.item(row, self.horizontalHeader().sortIndicatorSection())
        finally:
            self.setSortingEnabled(sortingEnabled)

        # If we don't have a sort item we assume a derived class has overridden _fillRow to add custom
        # columns and the table is currently sorted by one of those columns. In this the expectation is
        # the derived class will be handling working out the post sort row index.
        return sortItem.row() if sortItem else row
