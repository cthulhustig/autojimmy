import enum
import gui
import logging
import traveller
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

class TradeGoodTable(gui.ListTable):
    class ColumnType(enum.Enum):
        Name = 'Name'
        BasePricePerTon = 'Base Price\n(Cr per Ton)'

    AllColumns = [
        ColumnType.Name,
        ColumnType.BasePricePerTon
    ]

    _StateVersion = 'TradeGoodTable_v1'

    def __init__(
            self,
            rules: traveller.Rules,
            filterCallback: typing.Optional[typing.Callable[[traveller.TradeGood], bool]] = None,
            columns: typing.Iterable[ColumnType] = AllColumns
            ) -> None:
        super().__init__()

        self._rules = traveller.Rules(rules)
        self._filterCallback = filterCallback
        self._checkable = False

        self.setColumnHeaders(columns)
        self.resizeColumnsToContents() # Size columns to header text
        self.setSizeAdjustPolicy(
            QtWidgets.QAbstractScrollArea.SizeAdjustPolicy.AdjustToContentsOnFirstShow)
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.DefaultContextMenu)
        for column, columnType in enumerate(columns):
            if columnType == self.ColumnType.Name:
                self.setColumnWidth(column, 200)
        self._updateContent()

    def rules(self) -> traveller.Rules:
        return traveller.Rules(self._rules)

    def setRules(
            self,
            rules: traveller.Rules
            ) -> None:
        if rules == self._rules:
            return

        self._rules = traveller.Rules(rules)
        self._updateContent()

    def filterCallback(self) ->typing.Optional[typing.Callable[[traveller.TradeGood], bool]]:
        return self._filterCallback

    def setFilterCallback(
            self,
            callback: typing.Optional[typing.Callable[[traveller.TradeGood], bool]]
            ) -> None:
        self._filterCallback = callback
        self._updateContent()

    def tradeGood(self, row: int) -> typing.Optional[traveller.TradeGood]:
        tableItem = self.item(row, 0)
        if not tableItem:
            return None
        return tableItem.data(QtCore.Qt.ItemDataRole.UserRole)

    def tradeGoods(self) -> typing.List[traveller.TradeGood]:
        tradeGoods = []
        for row in range(self.rowCount()):
            tradeGood = self.tradeGood(row)
            if not tradeGood:
                continue
            tradeGoods.append(tradeGood)
        return tradeGoods

    def tradeGoodCount(self) -> int:
        return self.rowCount()

    def tradeGoodAt(
            self,
            y: int
            ) -> typing.Optional[traveller.TradeGood]:
        row = self.itemAt(y)
        return self.tradeGood(row) if row >= 0 else None

    def currentTradeGood(self) -> typing.Optional[traveller.TradeGood]:
        row = self.currentRow()
        if row < 0:
            return None
        return self.tradeGood(row)

    def selectedTradeGoods(self) -> typing.List[traveller.TradeGood]:
        tradeGoods = []
        for index in self.selectedIndexes():
            if index.column() == 0:
                tradeGood = self.tradeGood(index.row())
                if tradeGood:
                    tradeGoods.append(tradeGood)
        return tradeGoods

    def setCheckable(
            self,
            enable
            ) -> None:
        self._checkable = enable
        for row in range(self.rowCount()):
            item = self.item(row, 0)
            if enable:
                item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsUserCheckable)
                # NOTE: You need to explicitly set the check state for the check boxes to
                # be displayed. I think there is a requirement that the CheckStateRole
                # data must be set for it to be shown
                item.setCheckState(QtCore.Qt.CheckState.Unchecked)
            else:
                item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsUserCheckable)

    def isRowChecked(
            self,
            row: int
            ) -> bool:
        if not self._checkable:
            return False
        item = self.item(row, 0)
        return item.checkState() == QtCore.Qt.CheckState.Checked

    def setRowCheckState(
            self,
            row: int,
            checkState: bool
            ) -> None:
        if not self._checkable:
            return
        item = self.item(row, 0)
        item.setCheckState(QtCore.Qt.CheckState.Checked if checkState else QtCore.Qt.CheckState.Unchecked)

    def setTradeGoodCheckState(
            self,
            tradeGood: traveller.TradeGood,
            checkState: bool
            ) -> None:
        if not self._checkable:
            return
        for row in range(self.rowCount()):
            if tradeGood == self.tradeGood(row):
                self.setRowCheckState(row, checkState)

    def setSelectionCheckState(
            self,
            checkState: bool
            ) -> None:
        if not self._checkable:
            return
        for item in self.selectedItems():
            if item.column() != 0:
                continue
            item.setCheckState(QtCore.Qt.CheckState.Checked if checkState else QtCore.Qt.CheckState.Unchecked)

    def setAllRowCheckState(
            self,
            checkState: bool
            ) -> None:
        if not self._checkable:
            return
        for row in range(self.rowCount()):
            item = self.item(row, 0)
            item.setCheckState(QtCore.Qt.CheckState.Checked if checkState else QtCore.Qt.CheckState.Unchecked)

    def setCheckStateAbove(
            self,
            row: int,
            checkState: bool,
            inclusive: bool = True
            ) -> None:
        if not self._checkable:
            return
        if not inclusive:
            row -= 1
        while row >= 0:
            item = self.item(row, 0)
            item.setCheckState(QtCore.Qt.CheckState.Checked if checkState else QtCore.Qt.CheckState.Unchecked)
            row -= 1

    def setCheckStateBelow(
            self,
            row: int,
            checkState: bool,
            inclusive: bool = True
            ) -> None:
        if not self._checkable:
            return
        if not inclusive:
            row += 1
        rowCount = self.rowCount()
        while row < rowCount:
            item = self.item(row, 0)
            item.setCheckState(QtCore.Qt.CheckState.Checked if checkState else QtCore.Qt.CheckState.Unchecked)
            row += 1

    def checkedTradeGoods(self) -> typing.Iterable[traveller.TradeGood]:
        checked = []
        for row in range(self.rowCount()):
            item = self.item(row, 0)
            if item.checkState() == QtCore.Qt.CheckState.Checked:
                checked.append(self.tradeGood(row))
        return checked

    # TODO: This will probably need work
    def contextMenuEvent(self, event: QtGui.QContextMenuEvent) -> None:
        if not self._checkable:
            # The menu options only apply when checkable is enabled
            return super().contextMenuEvent(event)

        position = event.pos()
        row = self.rowAt(position.y())
        tradeGood = self.tradeGood(row)

        menuItems = [
            gui.MenuItem(
                text='Check All',
                callback=lambda: self.setAllRowCheckState(checkState=True),
                enabled=tradeGood != None
            ),
            gui.MenuItem(
                text='Check Selected',
                callback=lambda: self.setSelectionCheckState(checkState=True),
                enabled=tradeGood != None
            ),
            gui.MenuItem(
                text='Check Upwards',
                callback=lambda: self.setCheckStateAbove(row=row, checkState=True),
                enabled=tradeGood != None
            ),
            gui.MenuItem(
                text='Check Downwards',
                callback=lambda: self.setCheckStateBelow(row=row, checkState=True),
                enabled=tradeGood != None
            ),
            None, # Separator
            gui.MenuItem(
                text='Uncheck All',
                callback=lambda: self.setAllRowCheckState(checkState=False),
                enabled=tradeGood != None
            ),
            gui.MenuItem(
                text='Uncheck Selected',
                callback=lambda: self.setSelectionCheckState(checkState=False),
                enabled=tradeGood != None
            ),
            gui.MenuItem(
                text='Uncheck Upwards',
                callback=lambda: self.setCheckStateAbove(row=row, checkState=False),
                enabled=tradeGood != None
            ),
            gui.MenuItem(
                text='Uncheck Downwards',
                callback=lambda: self.setCheckStateBelow(row=row, checkState=False),
                enabled=tradeGood != None
            ),
        ]

        gui.displayMenu(
            self,
            menuItems,
            self.viewport().mapToGlobal(position))

        # Don't call base class as we've handled the event
        #return super().contextMenuEvent(event)

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(TradeGoodTable._StateVersion)

        baseState = super().saveState()
        stream.writeUInt32(baseState.count() if baseState else 0)
        if baseState:
            stream.writeRawData(baseState.data())

        checkedTradeGoods = self.checkedTradeGoods()
        stream.writeUInt32(len(checkedTradeGoods))
        for tradeGood in checkedTradeGoods:
            stream.writeUInt32(tradeGood.id())

        return state

    def restoreState(self, state: QtCore.QByteArray) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != TradeGoodTable._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore TradeGoodTable state (Incorrect version)')
            return False

        count = stream.readUInt32()
        if count <= 0:
            return True
        baseState = QtCore.QByteArray(stream.readRawData(count))
        if not super().restoreState(baseState):
            return False

        checkedTradeGoods = set()
        count = stream.readUInt32()
        for _ in range(count):
            id = stream.readUInt32()
            tradeGood = traveller.tradeGoodFromId(ruleSystem=self._rules.system(), tradeGoodId=id)
            if not tradeGood:
                logging.warning(f'Failed to restore NearbyWorldWindow TradeGoodTable state (Unknown ID "{id}")')
                continue
            checkedTradeGoods.add(tradeGood)
        for row in range(self.rowCount()):
            tradeGood = self.tradeGood(row=row)
            self.setRowCheckState(
                row=row,
                checkState=tradeGood in checkedTradeGoods)

        return True

    def _updateContent(self) -> None:
        newGoods = traveller.tradeGoodList(ruleSystem=self._rules.system())
        if self._filterCallback:
            newGoods = [tradeGood for tradeGood in newGoods if self._filterCallback(tradeGood)]
        newGoods = set(newGoods)
        currentGoods = set()

        # Remove any rows for goods not in the new list
        for row in range(self.rowCount() - 1, -1, -1):
            tradeGood = self.tradeGood(row)
            if tradeGood not in newGoods:
                self.removeRow(row)
            else:
                currentGoods.add(tradeGood)

        # Add rows for new goods. Sorting is turned off then
        # re-enabled at the end so it's only performed once
        sortingEnabled = self.isSortingEnabled()
        self.setSortingEnabled(False)

        try:
            for tradeGood in newGoods:
                if tradeGood not in currentGoods:
                    row = self.rowCount()
                    self.insertRow(row)
                    self._fillRow(row, tradeGood)
        finally:
            self.setSortingEnabled(sortingEnabled)

    def _fillRow(
            self,
            row: int,
            tradeGood: traveller.TradeGood
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
                    tableItem = QtWidgets.QTableWidgetItem()
                    tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, f'{tradeGood.id()}: {tradeGood.name()}')
                    if self._checkable:
                        tableItem.setFlags(tableItem.flags() | QtCore.Qt.ItemFlag.ItemIsUserCheckable)
                        tableItem.setCheckState(QtCore.Qt.CheckState.Unchecked)
                elif columnType == self.ColumnType.BasePricePerTon:
                    tableItem = gui.FormattedNumberTableWidgetItem(tradeGood.basePrice())

                if tableItem:
                    self.setItem(row, column, tableItem)
                    tableItem.setData(QtCore.Qt.ItemDataRole.UserRole, tradeGood)

            # Take note of the sort column item so we can determine which row index after the table
            # has been sorted
            sortItem = self.item(row, self.horizontalHeader().sortIndicatorSection())
        finally:
            self.setSortingEnabled(sortingEnabled)

        # If we don't have a sort item we assume a derived class has overridden _fillRow to add custom
        # columns and the table is currently sorted by one of those columns. In this the expectation is
        # the derived class will be handling working out the post sort row index.
        return sortItem.row() if sortItem else row
