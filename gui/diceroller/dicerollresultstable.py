import common
import diceroller
import enum
import gui
import logging
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

        self._rollResults = None

        self.setColumnHeaders(DiceRollResultsTable.ColumnType)
        self.resizeColumnsToContents() # Size columns to header text
        self.resizeRowsToContents()
        self.setSizeAdjustPolicy(
            QtWidgets.QAbstractScrollArea.SizeAdjustPolicy.AdjustToContentsOnFirstShow)
        self.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.verticalHeader().setMinimumSectionSize(1)
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._showContextMenu)
        self.setWordWrap(True)

        self.setAlternatingRowColors(False)

        # Disable sorting as manifests should be kept in the order the occurred in
        self.setSortingEnabled(False)

        self.installEventFilter(self)

    def setResults(
            self,
            rollResults: typing.Optional[diceroller.DiceRollResult]
            ) -> None:
        self._rollResults = rollResults
        self.update()

    def update(self) -> None:
        self.removeAllRows()
        if not self._rollResults:
            self.resizeRowsToContents()
            return

        usedRolls = []
        for index, (roll, ignored) in enumerate(self._rollResults.yieldRolls()):
            row = self.rowCount()
            self.insertRow(row)
            self._fillRollRow(
                row=row,
                index=index + 1,
                value=roll,
                ignored=ignored)
            if not ignored:
                usedRolls.append(roll)

        if usedRolls:
            rollTotal = common.Calculator.sum(
                values=usedRolls,
                name='Dice Roll Total')
        else:
            rollTotal = common.ScalarCalculation(value=0)

        row = self.rowCount()
        self.insertRow(row)
        self._fillRollTotalRow(
            row=row,
            total=rollTotal)

        usedModifiers = []
        for modifier, name in self._rollResults.yieldModifiers():
            row = self.rowCount()
            self.insertRow(row)
            self._fillModifierRow(
                row=row,
                modifierName=name,
                modifierValue=modifier)
            usedModifiers.append(modifier)

        if usedModifiers:
            modifiersTotal = common.Calculator.sum(
                values=usedModifiers,
                name='Modifiers Total')
        else:
            modifiersTotal = common.ScalarCalculation(value=0)

        row = self.rowCount()
        self.insertRow(row)
        self._fillModifiersTotalRow(
            row=row,
            total=modifiersTotal)

        row = self.rowCount()
        self.insertRow(row)
        self._fillTotalRow(
            row=row,
            total=self._rollResults.total())

        effect = self._rollResults.effect()
        if effect:
            row = self.rowCount()
            self.insertRow(row)
            self._fillEffectRow(
                row=row,
                effect=effect)

    def eventFilter(self, object: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if object == self:
            if event.type() == QtCore.QEvent.Type.KeyPress:
                assert(isinstance(event, QtGui.QKeyEvent))
                if event.matches(QtGui.QKeySequence.StandardKey.Copy):
                    self._copyToClipboard()
                    event.accept()
                    return True

        return super().eventFilter(object, event)

    def _fillRollRow(
            self,
            row: int,
            index: int,
            value: common.ScalarCalculation,
            ignored: bool
            ) -> None:
        for column in range(self.columnCount()):
            columnType = self.columnHeader(column)
            tableItem = None
            if columnType == DiceRollResultsTable.ColumnType.Name:
                tableItem = gui.TableWidgetItemEx(f'Die Roll #{index}')
            elif columnType == DiceRollResultsTable.ColumnType.Value:
                tableItem = gui.FormattedNumberTableWidgetItem(
                    value=value.value())

            if tableItem:
                tableItem.setStrikeOut(ignored)
                self.setItem(row, column, tableItem)
        self.resizeRowToContents(row)

    def _fillRollTotalRow(
            self,
            row: int,
            total: common.ScalarCalculation
            ) -> None:
        bkColour = QtWidgets.QApplication.palette().color(
            QtGui.QPalette.ColorRole.AlternateBase)
        for column in range(self.columnCount()):
            columnType = self.columnHeader(column)
            tableItem = None
            if columnType == DiceRollResultsTable.ColumnType.Name:
                tableItem = gui.TableWidgetItemEx(f'Die Roll Total')
            elif columnType == DiceRollResultsTable.ColumnType.Value:
                tableItem = gui.FormattedNumberTableWidgetItem(
                    value=total.value())

            if tableItem:
                tableItem.setBold(True)
                tableItem.setBackground(bkColour)
                self.setItem(row, column, tableItem)
        self.resizeRowToContents(row)

    def _fillModifierRow(
            self,
            row: int,
            modifierName: str,
            modifierValue: common.ScalarCalculation,
            ) -> None:
        for column in range(self.columnCount()):
            columnType = self.columnHeader(column)
            tableItem = None
            if columnType == DiceRollResultsTable.ColumnType.Name:
                tableItem = gui.TableWidgetItemEx(modifierName if modifierName else 'Unnamed Modifier')
            elif columnType == DiceRollResultsTable.ColumnType.Value:
                tableItem = gui.FormattedNumberTableWidgetItem(
                    value=modifierValue.value(),
                    alwaysIncludeSign=True)

            if tableItem:
                self.setItem(row, column, tableItem)
        self.resizeRowToContents(row)

    def _fillModifiersTotalRow(
            self,
            row: int,
            total: common.ScalarCalculation
            ) -> None:
        bkColour = QtWidgets.QApplication.palette().color(
            QtGui.QPalette.ColorRole.AlternateBase)
        for column in range(self.columnCount()):
            columnType = self.columnHeader(column)
            tableItem = None
            if columnType == DiceRollResultsTable.ColumnType.Name:
                tableItem = gui.TableWidgetItemEx(f'Modifiers Total')
            elif columnType == DiceRollResultsTable.ColumnType.Value:
                tableItem = gui.FormattedNumberTableWidgetItem(
                    value=total.value())

            if tableItem:
                tableItem.setBold(True)
                tableItem.setBackground(bkColour)
                self.setItem(row, column, tableItem)
        self.resizeRowToContents(row)

    def _fillTotalRow(
            self,
            row: int,
            total: common.ScalarCalculation
            ) -> None:
        bkColour = QtWidgets.QApplication.palette().color(
            QtGui.QPalette.ColorRole.AlternateBase)
        for column in range(self.columnCount()):
            columnType = self.columnHeader(column)
            tableItem = None
            if columnType == DiceRollResultsTable.ColumnType.Name:
                tableItem = gui.TableWidgetItemEx(f'Total')
            elif columnType == DiceRollResultsTable.ColumnType.Value:
                tableItem = gui.FormattedNumberTableWidgetItem(
                    value=total.value())

            if tableItem:
                tableItem.setBold(True)
                tableItem.setBackground(bkColour)
                self.setItem(row, column, tableItem)
        self.resizeRowToContents(row)

    def _fillEffectRow(
            self,
            row: int,
            effect: common.ScalarCalculation
            ) -> None:
        bkColour = QtWidgets.QApplication.palette().color(
            QtGui.QPalette.ColorRole.AlternateBase)
        for column in range(self.columnCount()):
            columnType = self.columnHeader(column)
            tableItem = None
            if columnType == DiceRollResultsTable.ColumnType.Name:
                tableItem = gui.TableWidgetItemEx(f'Effect')
            elif columnType == DiceRollResultsTable.ColumnType.Value:
                tableItem = gui.FormattedNumberTableWidgetItem(
                    value=effect.value())

            if tableItem:
                tableItem.setBold(True)
                tableItem.setBackground(bkColour)
                self.setItem(row, column, tableItem)
        self.resizeRowToContents(row)

    def _showContextMenu(
            self,
            position: QtCore.QPoint
            ) -> None:
        menuItems = [
            gui.MenuItem(
                text='Show Calculations...',
                callback=self._showCalculations
            ),
            None,
            gui.MenuItem(
                text='Copy as HTML',
                callback=self._copyToClipboard
            )
        ]

        gui.displayMenu(
            self,
            menuItems,
            self.viewport().mapToGlobal(position))

    def _showCalculations(self) -> None:
        try:
            calculationWindow = gui.WindowManager.instance().showCalculationWindow()
            calculationWindow.showCalculation(
                calculation=self._rollResults.total())
        except Exception as ex:
            message = 'Failed to show calculations'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)

    def _copyToClipboard(self) -> None:
        clipboard = QtWidgets.QApplication.clipboard()
        if not clipboard:
            return

        content = self.contentToHtml()
        if content:
            clipboard.setText(content)
