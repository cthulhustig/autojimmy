import app
import common
import enum
import gui
import logging
import logic
import traveller
import travellermap
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
            milieu: travellermap.Milieu,
            rules: traveller.Rules,
            worldTagging: typing.Optional[logic.WorldTagging] = None,
            taggingColours: typing.Optional[app.TaggingColours] = None,
            columns: typing.Iterable[typing.Union[WorldTradeScoreTableColumnType, gui.HexTable.ColumnType]] = AllColumns
            ) -> None:
        super().__init__(
            milieu=milieu,
            rules=rules,
            worldTagging=worldTagging,
            taggingColours=taggingColours,
            columns=columns)

        self._tradeGoods = set()
        self._tradeScoreMap = {}

        action = QtWidgets.QAction('Show Selected Calculations...', self)
        action.setEnabled(False) # No content to copy
        action.triggered.connect(self.showSelectedCalculations)
        self.setMenuAction(WorldTradeScoreTable.MenuAction.ShowSelectedCalculations, action)

        action = QtWidgets.QAction('Show All Calculations...', self)
        action.setEnabled(False) # No content to copy
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
            tradeGoods: typing.Iterable[traveller.TradeGood]
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
        return self._tradeScoreMap.get(hex)

    def removeRow(self, row: int):
        hex = self.hex(row)
        if hex in self._tradeScoreMap:
            del self._tradeScoreMap[hex]
        super().removeRow(row)

    def removeAllRows(self) -> None:
        self._tradeScoreMap.clear()
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

    def showSelectedCalculationsAction(self) -> QtWidgets.QAction:
        return self._showSelectedCalculationsAction

    def setShowSelectedCalculationsAction(self, action: QtWidgets.QAction) -> None:
        self._showSelectedCalculationsAction = action

    def showAllCalculationsAction(self) -> QtWidgets.QAction:
        return self._showAllCalculationsAction

    def setShowAllCalculationsAction(self, action: QtWidgets.QAction) -> None:
        self._showAllCalculationsAction = action

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
            return gui.createPurchaseTradeScoreToolTip(self.tradeScore(item.row()))
        elif columnType == WorldTradeScoreTableColumnType.SaleScore:
            return gui.createSaleTradeScoreToolTip(self.tradeScore(item.row()))

        return super()._createToolTip(item=item)

    def _fillRow(
            self,
            row: int,
            hex: travellermap.HexPosition
            ) -> int:
        world = traveller.WorldManager.instance().worldByPosition(
            milieu=self._milieu,
            hex=hex)

        # Always generate the trade score for a world if they aren't in the maps, even if those
        # columns aren't being displayed. We want them to be available if the get function is called
        if world and (hex not in self._tradeScoreMap):
            self._tradeScoreMap[hex] = logic.TradeScore(
                world=world,
                ruleSystem=self._rules.system(),
                tradeGoods=self._tradeGoods)

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
                    if world:
                        tradeScore: logic.TradeScore = self._tradeScoreMap[hex]
                        if columnType == WorldTradeScoreTableColumnType.PurchaseScore:
                            tradeScore = tradeScore.totalPurchaseScore()
                        else:
                            tradeScore = tradeScore.totalSaleScore()
                        tableItem = gui.FormattedNumberTableWidgetItem(
                            value=tradeScore,
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

    def _syncContent(self):
        # Clear the trade score map so the scores will be recalculated when the
        # underlying table triggers a refill of all rows as part of the sync
        self._tradeScoreMap.clear()
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