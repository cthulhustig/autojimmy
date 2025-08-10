import diceroller
import enum
import gui
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

class DiceRollResultsTable(gui.ListTable):
    class ColumnType(enum.Enum):
        Name = 'Name'
        Value = 'Value'

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent=parent)

        self._results = None

        self.setColumnHeaders(DiceRollResultsTable.ColumnType)
        self.resizeColumnsToContents() # Size columns to header text
        self.resizeRowsToContents()
        self.setSizeAdjustPolicy(
            QtWidgets.QAbstractScrollArea.SizeAdjustPolicy.AdjustToContentsOnFirstShow)
        self.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.verticalHeader().setMinimumSectionSize(1)
        self.setWordWrap(True)

        self.setAlternatingRowColors(False)

        # Disable sorting as manifests should be kept in the order the occurred in
        self.setSortingEnabled(False)

    def setResults(
            self,
            results: typing.Optional[diceroller.DiceRollResult]
            ) -> None:
        self._results = results
        self.removeAllRows()
        if not self._results:
            self.resizeRowsToContents()
            return

        for index, (roll, ignored) in enumerate(self._results.rolls()):
            row = self.rowCount()
            self.insertRow(row)
            self._fillRollRow(
                row=row,
                index=index + 1,
                value=roll,
                ignored=ignored)

        row = self.rowCount()
        self.insertRow(row)
        self._fillRollTotalRow(
            row=row,
            total=self._results.rolledTotal())

        fluxRolls = self._results.fluxRolls()
        if fluxRolls:
            for index, roll in enumerate(fluxRolls):
                row = self.rowCount()
                self.insertRow(row)
                self._fillFluxRow(
                    row=row,
                    index=index + 1,
                    value=roll)

            row = self.rowCount()
            self.insertRow(row)
            self._fillFluxTotalRow(
                row=row,
                total=self._results.fluxTotal())

        for name, modifier in self._results.modifiers():
            row = self.rowCount()
            self.insertRow(row)
            self._fillModifierRow(
                row=row,
                modifierName=name,
                modifierValue=modifier)

        row = self.rowCount()
        self.insertRow(row)
        self._fillModifiersTotalRow(
            row=row,
            total=self._results.modifiersTotal())

        row = self.rowCount()
        self.insertRow(row)
        self._fillTotalRow(
            row=row,
            total=self._results.total())

        effect = self._results.effectValue()
        if effect != None:
            row = self.rowCount()
            self.insertRow(row)
            self._fillEffectRow(
                row=row,
                effect=effect)

    def _fillRollRow(
            self,
            row: int,
            index: int,
            value: int,
            ignored: bool
            ) -> None:
        for column in range(self.columnCount()):
            columnType = self.columnHeader(column)
            tableItem = None
            if columnType == DiceRollResultsTable.ColumnType.Name:
                tableItem = gui.TableWidgetItemEx(f'Die Roll #{index}')
            elif columnType == DiceRollResultsTable.ColumnType.Value:
                tableItem = gui.FormattedNumberTableWidgetItem(
                    value=value)

            if tableItem:
                tableItem.setStrikeOut(ignored)
                self.setItem(row, column, tableItem)
        self.resizeRowToContents(row)

    def _fillRollTotalRow(
            self,
            row: int,
            total: int
            ) -> None:
        self._fillGenericTotalRow(
            row=row,
            name=f'Dice Roll Total',
            total=total)

    def _fillFluxRow(
            self,
            row: int,
            index: int,
            value: int
            ) -> None:
        for column in range(self.columnCount()):
            columnType = self.columnHeader(column)
            tableItem = None
            if columnType == DiceRollResultsTable.ColumnType.Name:
                tableItem = gui.TableWidgetItemEx(f'Flux Roll #{index}')
            elif columnType == DiceRollResultsTable.ColumnType.Value:
                tableItem = gui.FormattedNumberTableWidgetItem(
                    value=value)

            if tableItem:
                self.setItem(row, column, tableItem)
        self.resizeRowToContents(row)

    def _fillFluxTotalRow(
            self,
            row: int,
            total: int
            ) -> None:
        self._fillGenericTotalRow(
            row=row,
            name=f'Flux Total',
            total=total)

    def _fillModifierRow(
            self,
            row: int,
            modifierName: str,
            modifierValue: int,
            ) -> None:
        for column in range(self.columnCount()):
            columnType = self.columnHeader(column)
            tableItem = None
            if columnType == DiceRollResultsTable.ColumnType.Name:
                tableItem = gui.TableWidgetItemEx(modifierName if modifierName else 'Unnamed Modifier')
            elif columnType == DiceRollResultsTable.ColumnType.Value:
                tableItem = gui.FormattedNumberTableWidgetItem(
                    value=modifierValue,
                    alwaysIncludeSign=True)

            if tableItem:
                self.setItem(row, column, tableItem)
        self.resizeRowToContents(row)

    def _fillModifiersTotalRow(
            self,
            row: int,
            total: int
            ) -> None:
        self._fillGenericTotalRow(
            row=row,
            name='Modifiers Total',
            total=total)

    def _fillTotalRow(
            self,
            row: int,
            total: int
            ) -> None:
        self._fillGenericTotalRow(
            row=row,
            name='Total',
            total=total)

    def _fillGenericTotalRow(
            self,
            row: int,
            name: str,
            total: int
            ) -> None:
        bkColour = QtWidgets.QApplication.palette().color(
            QtGui.QPalette.ColorRole.AlternateBase)
        for column in range(self.columnCount()):
            columnType = self.columnHeader(column)
            tableItem = None
            if columnType == DiceRollResultsTable.ColumnType.Name:
                tableItem = gui.TableWidgetItemEx(name)
            elif columnType == DiceRollResultsTable.ColumnType.Value:
                tableItem = gui.FormattedNumberTableWidgetItem(value=total)

            if tableItem:
                tableItem.setBold(True)
                tableItem.setBackground(bkColour)
                self.setItem(row, column, tableItem)
        self.resizeRowToContents(row)

    def _fillEffectRow(
            self,
            row: int,
            effect: int
            ) -> None:
        bkColour = QtWidgets.QApplication.palette().color(
            QtGui.QPalette.ColorRole.AlternateBase)
        for column in range(self.columnCount()):
            columnType = self.columnHeader(column)
            tableItem = None
            if columnType == DiceRollResultsTable.ColumnType.Name:
                tableItem = gui.TableWidgetItemEx(f'Effect')
            elif columnType == DiceRollResultsTable.ColumnType.Value:
                tableItem = gui.FormattedNumberTableWidgetItem(value=effect)

            if tableItem:
                tableItem.setBold(True)
                tableItem.setBackground(bkColour)
                self.setItem(row, column, tableItem)
        self.resizeRowToContents(row)
