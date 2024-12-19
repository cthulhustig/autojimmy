import diceroller
import enum
import gui
import logging
import objectdb
import typing
from PyQt5 import QtWidgets, QtCore

class DiceRollHistoryWidget(QtWidgets.QWidget):
    class _ColumnType(enum.Enum):
        Timestamp = 'Timestamp'
        Label = 'Label'
        Total = 'Total'
        ResultType = 'Result Type'
        EffectValue = 'Effect Value'
        DieType = 'Die Type'
        RollTotal = 'Roll Total'
        RollDetails = 'Roll Details'
        ExtraDieType = 'Extra Die Type'
        ExtraDieRoll = 'Extra Die Roll'
        FluxType = 'Flux Type'
        FluxTotal = 'Flux Total'
        FluxRoll = 'Flux Roll'
        ModifiersTotal = 'DM Total'
        ModifiersDetails = 'DM Details'
        TargetType = 'Target Type'
        TargetNumber = 'Target Number'

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
        self._historyTable.setSortingEnabled(True)
        self._historyTable.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding)
        self._historyTable.setTextElideMode(QtCore.Qt.TextElideMode.ElideNone)
        self._historyTable.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self._historyTable.customContextMenuRequested.connect(self._showContextMenu)

        for index, column in enumerate(DiceRollHistoryWidget._ColumnType):
            if column == DiceRollHistoryWidget._ColumnType.Timestamp or \
                    column == DiceRollHistoryWidget._ColumnType.ResultType:
                self._historyTable.setColumnWidth(index, 200)
            elif column == DiceRollHistoryWidget._ColumnType.Label:
                self._historyTable.setColumnWidth(index, 300)

        widgetLayout = QtWidgets.QVBoxLayout()
        widgetLayout.setContentsMargins(0, 0, 0, 0)
        widgetLayout.addWidget(self._historyTable)

        self.setLayout(widgetLayout)

        self._loadData()
        self._insertedCbToken = objectdb.ObjectDbManager.instance().connectChangeCallback(
            operation=objectdb.ObjectDbOperation.Insert,
            key=diceroller.DiceRollResult,
            callback=self._handleDatabaseInsert)
        self._deletedCbToken = objectdb.ObjectDbManager.instance().connectChangeCallback(
            operation=objectdb.ObjectDbOperation.Delete,
            key=diceroller.DiceRollResult,
            callback=self._handleDatabaseDelete)

    def results(self) -> typing.Iterable[diceroller.DiceRollResult]:
        results = []
        for index in range(self._historyTable.rowCount()):
            item = self._historyTable.item(index, 0)
            result = item.data(QtCore.Qt.ItemDataRole.UserRole)
            if result:
                results.append(result)
        return results

    def resultCount(self) -> int:
        return self._historyTable.rowCount()

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
            ) -> int:
        # Workaround for the issue covered here, re-enabled after setting items
        # https://stackoverflow.com/questions/7960505/strange-qtablewidget-behavior-not-all-cells-populated-after-sorting-followed-b
        sortingEnabled = self._historyTable.isSortingEnabled()
        self._historyTable.setSortingEnabled(False)

        try:
            for column in range(self._historyTable.columnCount()):
                columnType = self._historyTable.columnHeader(column)
                tableItem = None
                if columnType == DiceRollHistoryWidget._ColumnType.Timestamp:
                    tableItem = gui.LocalTimestampTableWidgetItem(
                        timestamp=result.timestamp())
                elif columnType == DiceRollHistoryWidget._ColumnType.Label:
                    tableItem = gui.TableWidgetItemEx(result.label())
                elif columnType == DiceRollHistoryWidget._ColumnType.Total:
                    tableItem = gui.FormattedNumberTableWidgetItem(
                        value=result.total())
                elif columnType == DiceRollHistoryWidget._ColumnType.ResultType:
                    resultType = result.resultType()
                    if resultType != None:
                        tableItem = gui.TableWidgetItemEx(resultType.value)
                elif columnType == DiceRollHistoryWidget._ColumnType.EffectValue:
                    effectValue = result.effectValue()
                    if effectValue != None:
                        tableItem = gui.FormattedNumberTableWidgetItem(
                            value=effectValue)
                elif columnType == DiceRollHistoryWidget._ColumnType.DieType:
                    tableItem = gui.TableWidgetItemEx(result.dieType().value)
                elif columnType == DiceRollHistoryWidget._ColumnType.RollTotal:
                    tableItem = gui.FormattedNumberTableWidgetItem(
                        value=result.rolledTotal())
                elif columnType == DiceRollHistoryWidget._ColumnType.RollDetails:
                    rollStrings = []
                    for roll, ignored in result.rolls():
                        if not ignored:
                            rollStrings.append(str(roll))
                    if rollStrings:
                        tableItem = gui.TableWidgetItemEx(', '.join(rollStrings))
                elif columnType == DiceRollHistoryWidget._ColumnType.ExtraDieType:
                    extraDie = result.extraDie()
                    if extraDie != None:
                        tableItem = gui.TableWidgetItemEx(extraDie.value)
                elif columnType == DiceRollHistoryWidget._ColumnType.ExtraDieRoll:
                    extraDieRoll = result.extraDieRoll()
                    if extraDieRoll != None:
                        tableItem = gui.FormattedNumberTableWidgetItem(
                            value=extraDieRoll)
                elif columnType == DiceRollHistoryWidget._ColumnType.FluxType:
                    fluxType = result.fluxType()
                    if fluxType != None:
                        tableItem = gui.TableWidgetItemEx(fluxType.value)
                elif columnType == DiceRollHistoryWidget._ColumnType.FluxTotal:
                    fluxTotal = result.fluxTotal()
                    if fluxTotal != None:
                        tableItem = gui.FormattedNumberTableWidgetItem(
                            value=fluxTotal)
                elif columnType == DiceRollHistoryWidget._ColumnType.FluxRoll:
                    fluxRolls = result.fluxRolls()
                    if fluxRolls != None:
                        rollStrings = []
                        for roll in fluxRolls:
                            rollStrings.append(str(roll))
                        if rollStrings:
                            tableItem = gui.TableWidgetItemEx(', '.join(rollStrings))
                elif columnType == DiceRollHistoryWidget._ColumnType.ModifiersTotal:
                    tableItem = gui.FormattedNumberTableWidgetItem(
                        value=result.modifiersTotal())
                elif columnType == DiceRollHistoryWidget._ColumnType.ModifiersDetails:
                    modifierStrings = []
                    for _, modifier in result.modifiers():
                        modifierStrings.append(f'{modifier:+}')
                    if modifierStrings:
                        tableItem = gui.TableWidgetItemEx(', '.join(modifierStrings))
                elif columnType == DiceRollHistoryWidget._ColumnType.TargetType:
                    targetType = result.targetType()
                    if targetType != None:
                        tableItem = gui.TableWidgetItemEx(targetType.value)
                elif columnType == DiceRollHistoryWidget._ColumnType.TargetNumber:
                    targetNumber = result.targetNumber()
                    if targetNumber != None:
                        tableItem = gui.FormattedNumberTableWidgetItem(
                            value=targetNumber)

                if not tableItem:
                    tableItem = gui.TableWidgetItemEx()
                tableItem.setTextAlignment(int(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter))
                tableItem.setData(QtCore.Qt.ItemDataRole.UserRole, result)
                self._historyTable.setItem(row, column, tableItem)

            # Take note of the sort column item so we can determine which row index after the table
            # has been sorted
            sortItem = self._historyTable.item(
                row,
                self._historyTable.horizontalHeader().sortIndicatorSection())
        finally:
            self._historyTable.setSortingEnabled(sortingEnabled)

        # If we don't have a sort item we assume a derived class has overridden _fillRow to add custom
        # columns and the table is currently sorted by one of those columns. In this the expectation is
        # the derived class will be handling working out the post sort row index.
        return sortItem.row() if sortItem else row

    def _loadData(self) -> None:
        try:
            exceptionList: typing.List[Exception] = []
            results = objectdb.ObjectDbManager.instance().readObjects(
                classType=diceroller.DiceRollResult,
                bestEffort=True,
                exceptionList=exceptionList)

            if exceptionList:
                for ex in exceptionList:
                    logging.error('An error occurred while loading roll history from the database', exc_info=ex)
                gui.MessageBoxEx.critical(f'Failed to load some roll history data from database, consult log for more details.')
        except Exception as ex:
            message = 'Failed to load roll history from database'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(parent=self, text=message, exception=ex)
            return

        selection = set()
        for item in self._historyTable.selectedItems():
            result = item.data(QtCore.Qt.ItemDataRole.UserRole)
            assert(isinstance(result, diceroller.DiceRollResult))
            selection.add(result.id())
        self._historyTable.clearSelection()

        sortingEnabled = self._historyTable.isSortingEnabled()
        self._historyTable.setSortingEnabled(False)
        try:
            for row, result in enumerate(reversed(results)):
                if row >= self._historyTable.rowCount():
                    self._historyTable.insertRow(row)
                self._fillTableRow(row, result)
                assert(isinstance(result, diceroller.DiceRollResult))
                if result.id() in selection:
                    self._historyTable.selectRow(row)

            while self._historyTable.rowCount() > len(results):
                self._historyTable.removeRow(self._historyTable.rowCount() - 1)
        finally:
            self._historyTable.setSortingEnabled(sortingEnabled)

    def _handleDatabaseInsert(
            self,
            operation: objectdb.ObjectDbOperation,
            entity: str,
            entityType: typing.Type[objectdb.DatabaseEntity]
            ) -> None:
        try:
            result = objectdb.ObjectDbManager.instance().readObject(id=entity)

            sortingEnabled = self._historyTable.isSortingEnabled()
            self._historyTable.setSortingEnabled(False)
            try:
                self._historyTable.insertRow(0)
                self._fillTableRow(row=0, result=result)
            finally:
                self._historyTable.setSortingEnabled(sortingEnabled)
        except Exception as ex:
            message = f'Failed update history widget in response to insert of result {entity}'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(parent=self, text=message, exception=ex)

    def _handleDatabaseDelete(
            self,
            operation: objectdb.ObjectDbOperation,
            entity: str,
            entityType: typing.Type[objectdb.DatabaseEntity]
            ) -> None:
        try:
            for row in range(self._historyTable.rowCount()):
                item = self._historyTable.item(row, 0)
                result = item.data(QtCore.Qt.ItemDataRole.UserRole)
                assert(isinstance(result, diceroller.DiceRollResult))
                if result.id() == entity:
                    self._historyTable.removeRow(row)
                    return
        except Exception as ex:
            message = f'Failed update history widget in response to delete of result {entity}'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(parent=self, text=message, exception=ex)

    def _showContextMenu(
            self,
            position: QtCore.QPoint
            ) -> None:
        menuItems = [
            gui.MenuItem(
                text='Copy as HTML',
                callback=self._copyToClipboard),
            None,
            gui.MenuItem(
                text='Clear History...',
                callback=self._promptClearResults)]

        gui.displayMenu(
            self,
            menuItems,
            self._historyTable.viewport().mapToGlobal(position))

    def _copyToClipboard(self) -> None:
        clipboard = QtWidgets.QApplication.clipboard()
        if not clipboard:
            return

        content = self._historyTable.contentToHtml()
        if content:
            clipboard.setText(content)

    def _promptClearResults(self) -> None:
        results = self.results()
        if not results:
            return # Nothing to do
        count = len(results)
        answer = gui.AutoSelectMessageBox.question(
            text=f'This will permanently delete {count} historic results.\nDo you want to continue?',
            stateKey='DiceRollHistoryWidgetClearResults',
            rememberState=QtWidgets.QMessageBox.StandardButton.Yes)
        if answer != QtWidgets.QMessageBox.StandardButton.Yes:
            return # User cancelled

        try:
            objectdb.ObjectDbManager.instance().deleteObjects(
                type=diceroller.DiceRollResult)
        except Exception as ex:
            logging.error('Failed to clear history', exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text='Failed to clear history',
                exception=ex)
            return

        self._loadData()