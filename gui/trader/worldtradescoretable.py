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
        index = columns.index(gui.HexTable.ColumnType.Subsector) + 1
    except ValueError:
        index = len(columns)
    columns.insert(index, WorldTradeScoreTableColumnType.SaleScore)
    columns.insert(index, WorldTradeScoreTableColumnType.PurchaseScore)
    return columns

# TODO: I think I need to move calculation of the trade score into the
# table so the score can be updated if the milieu changes
# TODO: This needs updated to handle the rules and desirable tag colour changing
class WorldTradeScoreTable(gui.HexTable):
    AllColumns = _customWorldTableColumns(gui.HexTable.AllColumns)
    SystemColumns = _customWorldTableColumns(gui.HexTable.SystemColumns)
    UWPColumns = _customWorldTableColumns(gui.HexTable.UWPColumns)
    EconomicsColumns = _customWorldTableColumns(gui.HexTable.EconomicsColumns)
    CultureColumns = _customWorldTableColumns(gui.HexTable.CultureColumns)
    RefuellingColumns = _customWorldTableColumns(gui.HexTable.RefuellingColumns)

    def __init__(
            self,
            milieu: travellermap.Milieu,
            rules: traveller.Rules,
            columns: typing.Iterable[typing.Union[WorldTradeScoreTableColumnType, gui.HexTable.ColumnType]] = AllColumns
            ) -> None:
        super().__init__(milieu=milieu, rules=rules, columns=columns)

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
                self._fillRow(row, self.hex(row))
        finally:
            self.setSortingEnabled(sortingEnabled)

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
                rules=app.Config.instance().value(option=app.ConfigOption.Rules),
                world=world,
                tradeGoods=self._tradeGoods)

        # Disable sorting while updating a row. We don't want any sorting to occur until all columns
        # have been updated
        sortingEnabled = self.isSortingEnabled()
        self.setSortingEnabled(False)

        try:
            super()._fillRow(row, hex)

            if world:
                for column in range(self.columnCount()):
                    columnType = self.columnHeader(column)
                    tableItem = None
                    if columnType == WorldTradeScoreTableColumnType.PurchaseScore or \
                            columnType == WorldTradeScoreTableColumnType.SaleScore:
                        tradeScore: logic.TradeScore = self._tradeScoreMap[hex]
                        if columnType == WorldTradeScoreTableColumnType.PurchaseScore:
                            tradeScore = tradeScore.totalPurchaseScore()
                        else:
                            tradeScore = tradeScore.totalSaleScore()
                        tableItem = gui.FormattedNumberTableWidgetItem(
                            value=tradeScore,
                            alwaysIncludeSign=True)
                        scoreValue = tradeScore.value()
                        if scoreValue > 0:
                            tableItem.setBackground(QtGui.QColor(app.Config.instance().value(
                                option=app.ConfigOption.DesirableTagColour)))

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
