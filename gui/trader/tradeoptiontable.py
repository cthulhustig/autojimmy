import app
import enum
import gui
import logic
import traveller
import travellermap
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

# TODO: This needs updated to handle the avg/worst/best colour changing
class TradeOptionsTable(gui.FrozenColumnListTable):
    # The indices of the ColumnId must match the table row
    class ColumnType(enum.Enum):
        TradeGood = 'Trade Good'
        PurchaseWorld = 'Purchase World'
        PurchaseSector = 'Purchase Sector'
        PurchaseSubsector = 'Purchase Subsector'
        SaleWorld = 'Sale World'
        SaleSector = 'Sale Sector'
        SaleSubsector = 'Sale Subsector'
        Notes = 'Notes\n(Count)'
        Jumps = 'Jumps\n(Count)'
        Owned = 'Owned'
        # Average case columns
        AverageROI = 'Avg ROI\n(%)'
        AverageNetProfit = 'Avg Net Profit\n(Cr)'
        AverageGrossProfit = 'Avg Gross Profit\n(Cr)'
        AverageInvestment = 'Avg Investment\n(Cr)'
        AverageLogisticsCosts = 'Avg Logistics\n(Cr)'
        AverageQuantity = 'Avg Quantity\n(Tons)'
        AverageProfitPerTon = 'Avg Profit\n(Cr per Ton)'
        AverageSalePricePerTon = 'Avg Sale Price\n(Cr per Ton)'
        AveragePurchasePricePerTon = 'Avg Purchase Price\n(Cr per Ton)'
        # Worst case columns
        WorstROI = 'Worst ROI\n(%)'
        WorstNetProfit = 'Worst Net Profit\n(Cr)'
        WorstGrossProfit = 'Worst Gross Profit\n(Cr)'
        WorstInvestment = 'Worst Investment\n(Cr)'
        WorstLogisticsCosts = 'Worst Logistics\n(Cr)'
        WorstQuantity = 'Worst Quantity\n(Tons)'
        WorstProfitPerTon = 'Worst Profit\n(Cr per Ton)'
        WorstSalePricePerTon = 'Worst Sale Price\n(Cr per Ton)'
        WorstPurchasePricePerTon = 'Worst Purchase Price\n(Cr per Ton)'
        # Best case columns
        BestROI = 'Best ROI\n(%)'
        BestNetProfit = 'Best Net Profit\n(Cr)'
        BestGrossProfit = 'Best Gross Profit\n(Cr)'
        BestInvestment = 'Best Investment\n(Cr)'
        BestLogisticsCosts = 'Best Logistics\n(Cr)'
        BestQuantity = 'Best Quantity\n(Tons)'
        BestProfitPerTon = 'Best Profit\n(Cr per Ton)'
        BestSalePricePerTon = 'Best Sale Price\n(Cr per Ton)'
        BestPurchasePricePerTon = 'Best Purchase Price\n(Cr per Ton)'

    AllColumns = [
        ColumnType.TradeGood,
        ColumnType.PurchaseWorld,
        ColumnType.PurchaseSector,
        ColumnType.PurchaseSubsector,
        ColumnType.SaleWorld,
        ColumnType.SaleSector,
        ColumnType.SaleSubsector,
        ColumnType.Notes,
        ColumnType.Jumps,
        ColumnType.Owned,
        ColumnType.AverageROI,
        ColumnType.AverageNetProfit,
        ColumnType.AverageGrossProfit,
        ColumnType.AverageInvestment,
        ColumnType.AverageLogisticsCosts,
        ColumnType.AverageQuantity,
        ColumnType.AverageProfitPerTon,
        ColumnType.AverageSalePricePerTon,
        ColumnType.AveragePurchasePricePerTon,
        ColumnType.WorstROI,
        ColumnType.WorstNetProfit,
        ColumnType.WorstGrossProfit,
        ColumnType.WorstInvestment,
        ColumnType.WorstLogisticsCosts,
        ColumnType.WorstQuantity,
        ColumnType.WorstProfitPerTon,
        ColumnType.WorstSalePricePerTon,
        ColumnType.WorstPurchasePricePerTon,
        ColumnType.BestROI,
        ColumnType.BestNetProfit,
        ColumnType.BestGrossProfit,
        ColumnType.BestInvestment,
        ColumnType.BestLogisticsCosts,
        ColumnType.BestQuantity,
        ColumnType.BestProfitPerTon,
        ColumnType.BestSalePricePerTon,
        ColumnType.BestPurchasePricePerTon,
    ]

    AverageCaseColumns = [
        ColumnType.TradeGood,
        ColumnType.PurchaseWorld,
        ColumnType.PurchaseSector,
        ColumnType.PurchaseSubsector,
        ColumnType.SaleWorld,
        ColumnType.SaleSector,
        ColumnType.SaleSubsector,
        ColumnType.Notes,
        ColumnType.Jumps,
        ColumnType.Owned,
        ColumnType.AverageROI,
        ColumnType.AverageNetProfit,
        ColumnType.AverageGrossProfit,
        ColumnType.AverageInvestment,
        ColumnType.AverageLogisticsCosts,
        ColumnType.AverageQuantity,
        ColumnType.AverageProfitPerTon,
        ColumnType.AverageSalePricePerTon,
        ColumnType.AveragePurchasePricePerTon,
    ]

    WorstCaseColumns = [
        ColumnType.TradeGood,
        ColumnType.PurchaseWorld,
        ColumnType.PurchaseSector,
        ColumnType.PurchaseSubsector,
        ColumnType.SaleWorld,
        ColumnType.SaleSector,
        ColumnType.SaleSubsector,
        ColumnType.Notes,
        ColumnType.Jumps,
        ColumnType.Owned,
        ColumnType.WorstROI,
        ColumnType.WorstNetProfit,
        ColumnType.WorstGrossProfit,
        ColumnType.WorstInvestment,
        ColumnType.WorstLogisticsCosts,
        ColumnType.WorstQuantity,
        ColumnType.WorstProfitPerTon,
        ColumnType.WorstSalePricePerTon,
        ColumnType.WorstPurchasePricePerTon,
    ]

    BestCaseColumns = [
        ColumnType.TradeGood,
        ColumnType.PurchaseWorld,
        ColumnType.PurchaseSector,
        ColumnType.PurchaseSubsector,
        ColumnType.SaleWorld,
        ColumnType.SaleSector,
        ColumnType.SaleSubsector,
        ColumnType.Notes,
        ColumnType.Jumps,
        ColumnType.Owned,
        ColumnType.BestROI,
        ColumnType.BestNetProfit,
        ColumnType.BestGrossProfit,
        ColumnType.BestInvestment,
        ColumnType.BestLogisticsCosts,
        ColumnType.BestQuantity,
        ColumnType.BestProfitPerTon,
        ColumnType.BestSalePricePerTon,
        ColumnType.BestPurchasePricePerTon,
    ]

    def __init__(
            self,
            columns: typing.Iterable[ColumnType] = AllColumns
            ) -> None:
        super().__init__()

        self._hexTooltipProvider = None

        self.setColumnHeaders(columns)
        self.setUserColumnHiding(True)
        self.resizeColumnsToContents() # Size columns to header text
        self.setSizeAdjustPolicy(
            QtWidgets.QAbstractScrollArea.SizeAdjustPolicy.AdjustToContentsOnFirstShow)
        for column, columnType in enumerate(columns):
            if columnType == self.ColumnType.TradeGood:
                self.setColumnWidth(column, 200)
            elif columnType == self.ColumnType.PurchaseWorld or \
                    columnType == self.ColumnType.PurchaseSector or \
                    columnType == self.ColumnType.PurchaseSubsector or \
                    columnType == self.ColumnType.SaleWorld or \
                    columnType == self.ColumnType.SaleSector or \
                    columnType == self.ColumnType.SaleSubsector:
                self.setColumnWidth(column, 100)

    def tradeOption(self, row: int) -> typing.Optional[logic.TradeOption]:
        tableItem = self.item(row, 0)
        if not tableItem:
            return None
        return tableItem.data(QtCore.Qt.ItemDataRole.UserRole)

    def tradeOptions(self) -> typing.List[logic.TradeOption]:
        options = []
        for row in range(self.rowCount()):
            tradeOption = self.tradeOption(row)
            if not tradeOption:
                continue
            options.append(tradeOption)
        return options

    def tradeOptionAt(self, y: int) -> typing.Optional[logic.TradeOption]:
        row = self.rowAt(y)
        return self.tradeOption(row) if row >= 0 else None

    def insertTradeOption(self, row: int, tradeOption: logic.TradeOption) -> int:
        self.insertRow(row)
        return self._fillRow(row, tradeOption)

    def setTradeOption(self, row: int, tradeOption: logic.TradeOption) -> int:
        return self._fillRow(row, tradeOption)

    def addTradeOption(self, tradeOption: logic.TradeOption) -> int:
        return self.insertTradeOption(self.rowCount(), tradeOption)

    def addTradeOptions(self, tradeOptions: typing.Iterable[logic.TradeOption]):
        # Disable sorting while inserting multiple rows then sort once after they've
        # all been added
        sortingEnabled = self.isSortingEnabled()
        self.setSortingEnabled(False)

        try:
            for tradeOption in tradeOptions:
                self.insertTradeOption(self.rowCount(), tradeOption)
        finally:
            self.setSortingEnabled(sortingEnabled)

    def currentTradeOption(self):
        row = self.currentRow()
        if row < 0:
            return None
        return self.tradeOption(row)

    def hasSelection(self) -> bool:
        return self.selectionModel().hasSelection()

    def selectedTradeOptions(self) -> typing.Iterable[logic.TradeOption]:
        tradeOptions = []
        for index in self.selectedIndexes():
            if index.column() == 0:
                tradeOption = self.tradeOption(index.row())
                if tradeOption:
                    tradeOptions.append(tradeOption)
        return tradeOptions

    def setHexTooltipProvider(
            self,
            provider: typing.Optional[gui.HexTooltipProvider]
            ) -> None:
        self._hexTooltipProvider = provider

    def _fillRow(
            self,
            row: int,
            tradeOption: logic.TradeOption
            ) -> int:
        # Workaround for the issue covered here, re-enabled after setting items
        # https://stackoverflow.com/questions/7960505/strange-qtablewidget-behavior-not-all-cells-populated-after-sorting-followed-b
        sortingEnabled = self.isSortingEnabled()
        self.setSortingEnabled(False)

        try:
            tradeGood = tradeOption.tradeGood()
            purchaseWorld = tradeOption.purchaseWorld()
            saleWorld = tradeOption.saleWorld()
            cargoQuantity = tradeOption.cargoQuantity()
            profitPerTon = tradeOption.profitPerTon()
            purchasePricePerTon = tradeOption.purchasePricePerTon()
            salePricePerTon = tradeOption.salePricePerTon()
            logisticsCosts = tradeOption.logisticsCosts()
            investment = tradeOption.investment()
            netProfit = tradeOption.netProfit()
            grossProfit = tradeOption.grossProfit()
            returnOnInvestment = tradeOption.returnOnInvestment()

            purchaseWorldTagColour = app.tagColour(app.calculateWorldTagLevel(purchaseWorld))
            saleWorldTagColour = app.tagColour(app.calculateWorldTagLevel(saleWorld))

            averageCaseColour = QtGui.QColor(app.Config.instance().value(
                option=app.ConfigOption.AverageCaseColour))
            worstCaseColour = QtGui.QColor(app.Config.instance().value(
                option=app.ConfigOption.WorstCaseColour))
            bestCaseColour = QtGui.QColor(app.Config.instance().value(
                option=app.ConfigOption.BestCaseColour))

            for column in range(self.columnCount()):
                columnType = self.columnHeader(column)
                tableItem = None
                if columnType == self.ColumnType.TradeGood:
                    tableItem = QtWidgets.QTableWidgetItem()
                    tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, f'{tradeGood.id()}: {tradeGood.name()}')
                elif columnType == self.ColumnType.PurchaseWorld:
                    tableItem = QtWidgets.QTableWidgetItem()
                    tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, purchaseWorld.name())
                    if purchaseWorldTagColour:
                        tableItem.setBackground(QtGui.QColor(purchaseWorldTagColour))
                elif columnType == self.ColumnType.PurchaseSector:
                    tableItem = QtWidgets.QTableWidgetItem()
                    tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, purchaseWorld.sectorName())
                    if purchaseWorldTagColour:
                        tableItem.setBackground(QtGui.QColor(purchaseWorldTagColour))
                elif columnType == self.ColumnType.PurchaseSubsector:
                    tableItem = QtWidgets.QTableWidgetItem()
                    tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, purchaseWorld.subsectorName())
                    if purchaseWorldTagColour:
                        tableItem.setBackground(QtGui.QColor(purchaseWorldTagColour))
                elif columnType == self.ColumnType.SaleWorld:
                    tableItem = QtWidgets.QTableWidgetItem()
                    tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, saleWorld.name())
                    if saleWorldTagColour:
                        tableItem.setBackground(QtGui.QColor(saleWorldTagColour))
                elif columnType == self.ColumnType.SaleSector:
                    tableItem = QtWidgets.QTableWidgetItem()
                    tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, saleWorld.sectorName())
                    if saleWorldTagColour:
                        tableItem.setBackground(QtGui.QColor(saleWorldTagColour))
                elif columnType == self.ColumnType.SaleSubsector:
                    tableItem = QtWidgets.QTableWidgetItem()
                    tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, saleWorld.subsectorName())
                    if saleWorldTagColour:
                        tableItem.setBackground(QtGui.QColor(saleWorldTagColour))
                elif columnType == self.ColumnType.Notes:
                    notes = tradeOption.tradeNotes()
                    noteCount = None
                    if notes:
                        noteCount = len(notes) if notes else None
                    tableItem = gui.FormattedNumberTableWidgetItem(noteCount)
                    if noteCount:
                        tableItem.setBackground(QtGui.QColor(app.tagColour(app.TagLevel.Warning)))
                elif columnType == self.ColumnType.Jumps:
                    tableItem = gui.FormattedNumberTableWidgetItem(tradeOption.jumpCount())
                elif columnType == self.ColumnType.Owned:
                    tableItem = QtWidgets.QTableWidgetItem()
                    tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, 'yes' if tradeOption.isAlreadyOwned() else 'no')
                #
                # Average case values
                #
                elif columnType == self.ColumnType.AverageROI:
                    tableItem = gui.FormattedNumberTableWidgetItem(returnOnInvestment.averageCaseValue())
                    tableItem.setBackground(averageCaseColour)
                elif columnType == self.ColumnType.AverageNetProfit:
                    tableItem = gui.FormattedNumberTableWidgetItem(netProfit.averageCaseValue())
                    tableItem.setBackground(averageCaseColour)
                elif columnType == self.ColumnType.AverageGrossProfit:
                    tableItem = gui.FormattedNumberTableWidgetItem(grossProfit.averageCaseValue())
                    tableItem.setBackground(averageCaseColour)
                elif columnType == self.ColumnType.AverageInvestment:
                    tableItem = gui.FormattedNumberTableWidgetItem(investment.averageCaseValue())
                    tableItem.setBackground(averageCaseColour)
                elif columnType == self.ColumnType.AverageLogisticsCosts:
                    tableItem = gui.FormattedNumberTableWidgetItem(logisticsCosts.averageCaseValue())
                    tableItem.setBackground(averageCaseColour)
                elif columnType == self.ColumnType.AverageProfitPerTon:
                    tableItem = gui.FormattedNumberTableWidgetItem(profitPerTon.averageCaseValue())
                    tableItem.setBackground(averageCaseColour)
                elif columnType == self.ColumnType.AveragePurchasePricePerTon:
                    tableItem = gui.FormattedNumberTableWidgetItem(purchasePricePerTon.averageCaseValue())
                    tableItem.setBackground(averageCaseColour)
                elif columnType == self.ColumnType.AverageSalePricePerTon:
                    tableItem = gui.FormattedNumberTableWidgetItem(salePricePerTon.averageCaseValue())
                    tableItem.setBackground(averageCaseColour)
                elif columnType == self.ColumnType.AverageQuantity:
                    tableItem = gui.FormattedNumberTableWidgetItem(cargoQuantity.averageCaseValue())
                    tableItem.setBackground(averageCaseColour)
                #
                # Worst case values
                #
                elif columnType == self.ColumnType.WorstROI:
                    tableItem = gui.FormattedNumberTableWidgetItem(returnOnInvestment.worstCaseValue())
                    tableItem.setBackground(worstCaseColour)
                elif columnType == self.ColumnType.WorstNetProfit:
                    tableItem = gui.FormattedNumberTableWidgetItem(netProfit.worstCaseValue())
                    tableItem.setBackground(worstCaseColour)
                elif columnType == self.ColumnType.WorstGrossProfit:
                    tableItem = gui.FormattedNumberTableWidgetItem(grossProfit.worstCaseValue())
                    tableItem.setBackground(worstCaseColour)
                elif columnType == self.ColumnType.WorstInvestment:
                    tableItem = gui.FormattedNumberTableWidgetItem(investment.worstCaseValue())
                    tableItem.setBackground(worstCaseColour)
                elif columnType == self.ColumnType.WorstLogisticsCosts:
                    tableItem = gui.FormattedNumberTableWidgetItem(logisticsCosts.worstCaseValue())
                    tableItem.setBackground(worstCaseColour)
                elif columnType == self.ColumnType.WorstProfitPerTon:
                    tableItem = gui.FormattedNumberTableWidgetItem(profitPerTon.worstCaseValue())
                    tableItem.setBackground(worstCaseColour)
                elif columnType == self.ColumnType.WorstPurchasePricePerTon:
                    tableItem = gui.FormattedNumberTableWidgetItem(purchasePricePerTon.worstCaseValue())
                    tableItem.setBackground(worstCaseColour)
                elif columnType == self.ColumnType.WorstSalePricePerTon:
                    tableItem = gui.FormattedNumberTableWidgetItem(salePricePerTon.worstCaseValue())
                    tableItem.setBackground(worstCaseColour)
                elif columnType == self.ColumnType.WorstQuantity:
                    tableItem = gui.FormattedNumberTableWidgetItem(cargoQuantity.worstCaseValue())
                    tableItem.setBackground(worstCaseColour)
                #
                # Best case values
                #
                elif columnType == self.ColumnType.BestROI:
                    tableItem = gui.FormattedNumberTableWidgetItem(returnOnInvestment.bestCaseValue())
                    tableItem.setBackground(bestCaseColour)
                elif columnType == self.ColumnType.BestNetProfit:
                    tableItem = gui.FormattedNumberTableWidgetItem(netProfit.bestCaseValue())
                    tableItem.setBackground(bestCaseColour)
                elif columnType == self.ColumnType.BestGrossProfit:
                    tableItem = gui.FormattedNumberTableWidgetItem(grossProfit.bestCaseValue())
                    tableItem.setBackground(bestCaseColour)
                elif columnType == self.ColumnType.BestInvestment:
                    tableItem = gui.FormattedNumberTableWidgetItem(investment.bestCaseValue())
                    tableItem.setBackground(bestCaseColour)
                elif columnType == self.ColumnType.BestLogisticsCosts:
                    tableItem = gui.FormattedNumberTableWidgetItem(logisticsCosts.bestCaseValue())
                    tableItem.setBackground(bestCaseColour)
                elif columnType == self.ColumnType.BestProfitPerTon:
                    tableItem = gui.FormattedNumberTableWidgetItem(profitPerTon.bestCaseValue())
                    tableItem.setBackground(bestCaseColour)
                elif columnType == self.ColumnType.BestPurchasePricePerTon:
                    tableItem = gui.FormattedNumberTableWidgetItem(purchasePricePerTon.bestCaseValue())
                    tableItem.setBackground(bestCaseColour)
                elif columnType == self.ColumnType.BestSalePricePerTon:
                    tableItem = gui.FormattedNumberTableWidgetItem(salePricePerTon.bestCaseValue())
                    tableItem.setBackground(bestCaseColour)
                elif columnType == self.ColumnType.BestQuantity:
                    tableItem = gui.FormattedNumberTableWidgetItem(cargoQuantity.bestCaseValue())
                    tableItem.setBackground(bestCaseColour)

                if tableItem:
                    self.setItem(row, column, tableItem)
                    tableItem.setData(QtCore.Qt.ItemDataRole.UserRole, tradeOption)

            # Take note of the sort column item so we can determine which row index after the table
            # has been sorted
            sortItem = self.item(row, self.horizontalHeader().sortIndicatorSection())
        finally:
            self.setSortingEnabled(sortingEnabled)

        # If we don't have a sort item we assume a derived class has overridden _fillRow to add custom
        # columns and the table is currently sorted by one of those columns. In this the expectation is
        # the derived class will be handling working out the post sort row index.
        return sortItem.row() if sortItem else row

    def _createToolTip(
            self,
            item: QtWidgets.QTableWidgetItem
            ) -> typing.Optional[str]:
        tradeOption = self.tradeOption(item.row())
        if not tradeOption:
            return None

        columnType = self.columnHeader(item.column())

        if columnType == self.ColumnType.PurchaseWorld or columnType == self.ColumnType.PurchaseSector or \
            columnType == self.ColumnType.PurchaseSubsector:
            purchaseWorld = tradeOption.purchaseWorld()
            if self._hexTooltipProvider:
                return self._hexTooltipProvider.tooltip(hex=purchaseWorld.hex())
            else:
                return traveller.WorldManager.instance().canonicalHexName(
                    milieu=purchaseWorld.milieu(),
                    hex=purchaseWorld.hex())
        elif columnType == self.ColumnType.SaleWorld or columnType == self.ColumnType.SaleSector or \
            columnType == self.ColumnType.SaleSubsector:
            saleWorld = tradeOption.saleWorld()
            if self._hexTooltipProvider:
                return self._hexTooltipProvider.tooltip(hex=saleWorld.hex())
            else:
                return traveller.WorldManager.instance().canonicalHexName(
                    milieu=saleWorld.milieu(),
                    hex=saleWorld.hex())
        elif columnType == self.ColumnType.Notes:
            notes = tradeOption.tradeNotes()
            if notes:
                return gui.createListToolTip(title='Notes:', strings=notes)
            else:
                return gui.createStringToolTip('No notes')
        elif columnType == self.ColumnType.Jumps:
            return gui.createLogisticsToolTip(routeLogistics=tradeOption.routeLogistics())

        return None
