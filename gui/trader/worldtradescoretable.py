import app
import astronomer
import common
import enum
import gui
import logging
import logic
import traveller
import typing
from PyQt5 import QtWidgets, QtCore

class WorldTradeScoreTableColumnType(enum.Enum):
    PurchaseScore = 'Purchase Score'
    SaleScore = 'Sale Score'

def _customWorldTableColumns(
        originalColumns: typing.List[gui.HexTable.ColumnType]
        ) -> typing.List[typing.Union[WorldTradeScoreTableColumnType, gui.HexTable.ColumnType]]:
    columns = originalColumns.copy()
    try:
        index = columns.index(gui.HexTable.ColumnType.Subsector) + 1
    except ValueError:
        index = len(columns)
    columns.insert(index, WorldTradeScoreTableColumnType.SaleScore)
    columns.insert(index, WorldTradeScoreTableColumnType.PurchaseScore)
    return columns

class WorldTradeScoreTable(gui.HexTable):
    AllColumns = _customWorldTableColumns(gui.HexTable.AllColumns)
    SystemColumns = _customWorldTableColumns(gui.HexTable.SystemColumns)
    UWPColumns = _customWorldTableColumns(gui.HexTable.UWPColumns)
    EconomicsColumns = _customWorldTableColumns(gui.HexTable.EconomicsColumns)
    CultureColumns = _customWorldTableColumns(gui.HexTable.CultureColumns)
    RefuellingColumns = _customWorldTableColumns(gui.HexTable.RefuellingColumns)

    class MenuAction(enum.Enum):
        ShowSelectedCalculations = enum.auto()
        ShowAllCalculations = enum.auto()

    def __init__(
            self,
            universe: astronomer.Universe,
            rules: traveller.Rules,
            worldTagging: typing.Optional[logic.WorldTagging] = None,
            taggingColours: typing.Optional[app.TaggingColours] = None,
            columns: typing.Iterable[typing.Union[WorldTradeScoreTableColumnType, gui.HexTable.ColumnType]] = AllColumns
            ) -> None:
        super().__init__(
            universe=universe,
            rules=rules,
            worldTagging=worldTagging,
            taggingColours=taggingColours,
            columns=columns)

        self._tradeGoods: typing.Set[logic.TradeGood] = set()
        self._hexToTradeScoreMap: typing.Dict[astronomer.HexPosition, typing.Optional[logic.TradeScore]] = {}

        action = QtWidgets.QAction('Show Calculations...', self)
        action.setEnabled(False) # No selection
        action.triggered.connect(self.showSelectedCalculations)
        self.setMenuAction(WorldTradeScoreTable.MenuAction.ShowSelectedCalculations, action)

        action = QtWidgets.QAction('Show All Calculations...', self)
        action.setEnabled(False) # No content
        action.triggered.connect(self.showAllCalculations)
        self.setMenuAction(WorldTradeScoreTable.MenuAction.ShowAllCalculations, action)

    def setRules(self, rules: traveller.Rules) -> None:
        if rules == self._rules:
            return

        # Update the trade currently set trade goods, removing any that
        # aren't for the rule system about to be set. This MUST be done
        # before passing the rules onto the base class as it will trigger
        # a recalculation of the trade scores when updating the rows
        ruleSystem = rules.system()
        self._tradeGoods = set([tradeGood for tradeGood in self._tradeGoods if tradeGood.ruleSystem() is ruleSystem])

        return super().setRules(rules)

    def setTradeGoods(
            self,
            tradeGoods: typing.Iterable[logic.TradeGood]
            ) -> None:
        ruleSystem = self._rules.system()
        tradeGoods = set([tradeGood for tradeGood in tradeGoods if tradeGood.ruleSystem() is ruleSystem])
        if tradeGoods == self._tradeGoods:
            return

        self._tradeGoods = tradeGoods
        self._syncContent()

    def tradeScore(
            self,
            row: int
            ) -> typing.Optional[logic.TradeScore]:
        hex = self.hex(row)
        if hex is None:
            return None
        # NOTE: Use -1 to check for no entry in the map as None is
        # a valid entry if the hex has no world in it.
        tradeScore = self._hexToTradeScoreMap.get(hex, -1)
        if tradeScore == -1:
            tradeScore = self._cacheTradeScore(hex)
        return tradeScore

    def removeRow(self, row: int):
        hex = self.hex(row)
        if hex in self._hexToTradeScoreMap:
            # NOTE: The hex could be in the table multiple times and we're only removing
            # one of them so deleting the trade score isn't the obvious thing to do here.
            # However, in practice it's rare for tables to have the same hex in them
            # multiple times. Rather than check the full table every time a hex is removed
            # or add some other method of tracking when the trade score is no longer
            # required, we just delete the trade score on the assumption it isn't needed
            # any more, if it turns it we were wrong then it will just be recalculated
            # when it's next needed.
            del self._hexToTradeScoreMap[hex]
        super().removeRow(row)

    def removeAllRows(self) -> None:
        self._hexToTradeScoreMap.clear()
        super().removeAllRows()

    def showSelectedCalculations(self) -> None:
        calculations = []
        for row in self.selectedRows():
            tradeScore = self.tradeScore(row)
            if tradeScore:
                calculations.append(tradeScore.totalPurchaseScore())
                calculations.append(tradeScore.totalSaleScore())
        if not calculations:
            return
        self._showCalculations(calculations=calculations)

    def showAllCalculations(self) -> None:
        calculations = []
        for row in range(self.rowCount()):
            tradeScore = self.tradeScore(row)
            if tradeScore:
                calculations.append(tradeScore.totalPurchaseScore())
                calculations.append(tradeScore.totalSaleScore())
        if not calculations:
            return
        self._showCalculations(calculations=calculations)

    def fillContextMenu(self, menu: QtWidgets.QMenu) -> None:
        # Add base class menu options (export, show on map etc)
        super().fillContextMenu(menu)

        if not menu.isEmpty():
            menu.addSeparator()

        action = self.menuAction(WorldTradeScoreTable.MenuAction.ShowSelectedCalculations)
        if action:
            menu.addAction(action)

        action = self.menuAction(WorldTradeScoreTable.MenuAction.ShowAllCalculations)
        if action:
            menu.addAction(action)

    def isEmptyChanged(self) -> None:
        super().isEmptyChanged()
        self._syncWorldTradeScoreTableActions()

    def selectionChanged(
            self,
            selected: QtCore.QItemSelection,
            deselected: QtCore.QItemSelection
            ) -> None:
        super().selectionChanged(selected, deselected)
        self._syncWorldTradeScoreTableActions()

    def _createToolTip(
            self,
            item: QtWidgets.QTableWidgetItem
            ) -> typing.Optional[str]:
        columnType = self.columnHeader(item.column())
        if columnType == WorldTradeScoreTableColumnType.PurchaseScore:
            tradeScore = self.tradeScore(item.row())
            return gui.createPurchaseTradeScoreToolTip(tradeScore) if tradeScore else None
        elif columnType == WorldTradeScoreTableColumnType.SaleScore:
            tradeScore = self.tradeScore(item.row())
            return gui.createSaleTradeScoreToolTip(tradeScore) if tradeScore else None

        return super()._createToolTip(item=item)

    def _fillRow(
            self,
            row: int,
            hex: astronomer.HexPosition
            ) -> int:
        tradeScore = self._hexToTradeScoreMap.get(hex, -1)
        if tradeScore == -1:
            tradeScore = self._cacheTradeScore(hex)
        world = tradeScore.world() if tradeScore is not None else None

        # Disable sorting while updating a row. We don't want any sorting to occur until all columns
        # have been updated
        sortingEnabled = self.isSortingEnabled()
        self.setSortingEnabled(False)

        try:
            super()._fillRow(row, hex)

            for column in range(self.columnCount()):
                columnType = self.columnHeader(column)
                tableItem = None
                if columnType == WorldTradeScoreTableColumnType.PurchaseScore or \
                        columnType == WorldTradeScoreTableColumnType.SaleScore:
                    if tradeScore:
                        if columnType == WorldTradeScoreTableColumnType.PurchaseScore:
                            columnScore = tradeScore.totalPurchaseScore()
                        else:
                            columnScore = tradeScore.totalSaleScore()
                        tableItem = gui.FormattedNumberTableWidgetItem(
                            value=columnScore,
                            alwaysIncludeSign=True)
                    else:
                        # Dead space has no trade score
                        tableItem = gui.TableWidgetItemEx()

                if tableItem:
                    self.setItem(row, column, tableItem)
                    tableItem.setData(QtCore.Qt.ItemDataRole.UserRole, (hex, world))

            # Take note of the sort column item so we can determine which row index after the table
            # has been sorted
            sortItem = self.item(row, self.horizontalHeader().sortIndicatorSection())
        finally:
            self.setSortingEnabled(sortingEnabled)

        # If we don't have a sort item we assume a derived class has overridden _fillRow to add custom
        # columns and the table is currently sorted by one of those columns. In this the expectation is
        # the derived class will be handling working out the post sort row index.
        return sortItem.row() if sortItem else row

    def _cacheTradeScore(self, hex: astronomer.HexPosition) -> logic.TradeScore:
        world = self._universe.worldByPosition(hex=hex)
        tradeScore = None
        if world is not None:
            tradeScore = logic.TradeScore(
                rules=self._rules,
                world=world,
                tradeGoods=self._tradeGoods)

        self._hexToTradeScoreMap[hex] = tradeScore
        return tradeScore

    def _syncContent(self):
        # Clear the trade score map so the scores will be recalculated when the
        # underlying table triggers a refill of all rows as part of the sync
        self._hexToTradeScoreMap.clear()
        return super()._syncContent()

    def _syncWorldTradeScoreTableActions(self) -> None:
        action = self.menuAction(WorldTradeScoreTable.MenuAction.ShowSelectedCalculations)
        if action:
            action.setEnabled(self.hasSelection())

        action = self.menuAction(WorldTradeScoreTable.MenuAction.ShowAllCalculations)
        if action:
            action.setEnabled(not self.isEmpty())

    def _showCalculations(
            self,
            calculations: typing.Iterable[common.ScalarCalculation]
            ) -> None:
        try:
            calculationWindow = gui.WindowManager.instance().showCalculationWindow()
            calculationWindow.showCalculations(
                calculations=calculations,
                decimalPlaces=2)
        except Exception as ex:
            message = 'Failed to show Trade Score calculations'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
