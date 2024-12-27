import app
import enum
import gui
import logic
import traveller
import travellermap
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

class WorldTradeScoreTableColumnType(enum.Enum):
    PurchaseScore = 'Purchase Score'
    SaleScore = 'Sale Score'

def _customWorldTableColumns(
        originalColumns: typing.List[gui.HexTable.ColumnType]
        ) -> typing.List[typing.Union[WorldTradeScoreTableColumnType, gui.HexTable.ColumnType]]:
    columns = originalColumns.copy()
    try:
        index = columns.index(gui.HexTable.ColumnType.Sector) + 1
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

    def __init__(
            self,
            columns: typing.Iterable[typing.Union[WorldTradeScoreTableColumnType, gui.HexTable.ColumnType]] = AllColumns
            ) -> None:
        super().__init__(columns=columns)

        self._tradeGoods = []
        self._tradeScoreMap = {}

    def setTradeGoods(
            self,
            tradeGoods: typing.Iterable[traveller.TradeGood]
            ) -> None:
        self._tradeGoods = tradeGoods
        self._tradeScoreMap.clear()

        # Disable sorting while updating a row. We don't want any sorting to occur
        # until all rows have been updated
        sortingEnabled = self.isSortingEnabled()
        self.setSortingEnabled(False)

        try:
            for row in range(self.rowCount()):
                world = self.world(row)
                self._fillRow(row, world)
        finally:
            self.setSortingEnabled(sortingEnabled)

    def tradeScore(
            self,
            world: traveller.World
            ) -> logic.TradeScore:
        return self._tradeScoreMap[world]

    def removeRow(self, row: int):
        world = self.world(row)
        if world in self._tradeScoreMap:
            del self._tradeScoreMap[world]
        super().removeRow(row)

    def removeAllRows(self) -> None:
        self._tradeScoreMap.clear()
        super().removeAllRows()

    def _createToolTip(
            self,
            item: QtWidgets.QTableWidgetItem
            ) -> typing.Optional[str]:
        world = self.world(item.row())

        if world:
            columnType = self.columnHeader(item.column())
            if columnType == WorldTradeScoreTableColumnType.PurchaseScore:
                return gui.createPurchaseTradeScoreToolTip(self.tradeScore(world))
            elif columnType == WorldTradeScoreTableColumnType.SaleScore:
                return gui.createSaleTradeScoreToolTip(self.tradeScore(world))

        return super()._createToolTip(item=item)

    def _fillRow(
            self,
            row: int,
            pos: travellermap.HexPosition,
            world: typing.Optional[traveller.World]
            ) -> int:
        # Always generate the trade score for a world if they aren't in the maps, even if those
        # columns aren't being displayed. We want them to be available if the get function is called
        if world and (world not in self._tradeScoreMap):
            self._tradeScoreMap[world] = logic.TradeScore(
                rules=app.Config.instance().rules(),
                world=world,
                tradeGoods=self._tradeGoods)

        # Disable sorting while updating a row. We don't want any sorting to occur until all columns
        # have been updated
        sortingEnabled = self.isSortingEnabled()
        self.setSortingEnabled(False)

        try:
            super()._fillRow(row, pos, world)

            if world:
                for column in range(self.columnCount()):
                    columnType = self.columnHeader(column)
                    tableItem = None
                    if columnType == WorldTradeScoreTableColumnType.PurchaseScore or \
                            columnType == WorldTradeScoreTableColumnType.SaleScore:
                        tradeScore: logic.TradeScore = self._tradeScoreMap[world]
                        if columnType == WorldTradeScoreTableColumnType.PurchaseScore:
                            tradeScore = tradeScore.totalPurchaseScore()
                        else:
                            tradeScore = tradeScore.totalSaleScore()
                        tableItem = gui.FormattedNumberTableWidgetItem(
                            value=tradeScore,
                            alwaysIncludeSign=True)
                        scoreValue = tradeScore.value()
                        if scoreValue > 0:
                            tableItem.setBackground(QtGui.QColor(app.Config.instance().tagColour(app.TagLevel.Desirable)))
                        """
                        elif scoreValue < 0:
                            tableItem.setBackground(QtGui.QColor(app.Config.instance().tagColour(app.TagLevel.Warning)))
                        """

                    if tableItem:
                        self.setItem(row, column, tableItem)
                        tableItem.setData(QtCore.Qt.ItemDataRole.UserRole, (pos, world))

            # Take note of the sort column item so we can determine which row index after the table
            # has been sorted
            sortItem = self.item(row, self.horizontalHeader().sortIndicatorSection())
        finally:
            self.setSortingEnabled(sortingEnabled)

        # If we don't have a sort item we assume a derived class has overridden _fillRow to add custom
        # columns and the table is currently sorted by one of those columns. In this the expectation is
        # the derived class will be handling working out the post sort row index.
        return sortItem.row() if sortItem else row
