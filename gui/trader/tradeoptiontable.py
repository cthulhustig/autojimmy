import app
import common
import enum
import gui
import logging
import logic
import traveller
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

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
            outcomeColours: app.OutcomeColours,
            worldTagging: typing.Optional[logic.WorldTagging] = None,
            taggingColours: typing.Optional[app.TaggingColours] = None,
            columns: typing.Iterable[ColumnType] = AllColumns
            ) -> None:
        super().__init__()

        self._outcomeColours = app.OutcomeColours(outcomeColours)
        self._worldTagging = logic.WorldTagging(worldTagging) if worldTagging else None
        self._taggingColours = app.TaggingColours(taggingColours) if taggingColours else None
        self._hexTooltipProvider = None

        # TODO: The text for these actions need rewording as they are way to long
        # - This is probably true of other menus as well
        self._showSelectedPurchaseWorldDetailsAction =  QtWidgets.QAction('Show Selected Purchase World Details...', self)
        self._showSelectedPurchaseWorldDetailsAction.setEnabled(False) # No selection
        self._showSelectedPurchaseWorldDetailsAction.triggered.connect(self.showSelectedPurchaseWorldDetails)

        self._showSelectedSaleWorldDetailsAction =  QtWidgets.QAction('Show Selected Sale World Details...', self)
        self._showSelectedSaleWorldDetailsAction.setEnabled(False) # No selection
        self._showSelectedSaleWorldDetailsAction.triggered.connect(self.showSelectedSaleWorldDetails)

        self._showSelectedWorldDetailsAction =  QtWidgets.QAction('Show Selected World Details...', self)
        self._showSelectedWorldDetailsAction.setEnabled(False) # No selection
        self._showSelectedWorldDetailsAction.triggered.connect(self.showSelectedWorldDetails)

        self._showSelectedWorldDetailsAction =  QtWidgets.QAction('Show Selected World Details...', self)
        self._showSelectedWorldDetailsAction.setEnabled(False) # No selection
        self._showSelectedWorldDetailsAction.triggered.connect(self.showSelectedWorldDetails)

        self._showSelectedPurchaseWorldsOnMapAction =  QtWidgets.QAction('Show Selected Purchase Worlds on Map...', self)
        self._showSelectedPurchaseWorldsOnMapAction.setEnabled(False) # No selection
        self._showSelectedPurchaseWorldsOnMapAction.triggered.connect(self.showSelectedPurchaseWorldsOnMap)

        self._showSelectedSaleWorldsOnMapAction =  QtWidgets.QAction('Show Selected Sale Worlds on Map...', self)
        self._showSelectedSaleWorldsOnMapAction.setEnabled(False) # No selection
        self._showSelectedSaleWorldsOnMapAction.triggered.connect(self.showSelectedSaleWorldsOnMap)

        self._showSelectedWorldsOnMapAction =  QtWidgets.QAction('Show Selected Worlds on Map...', self)
        self._showSelectedWorldsOnMapAction.setEnabled(False) # No selection
        self._showSelectedWorldsOnMapAction.triggered.connect(self.showSelectedWorldsOnMap)

        # TODO: This needs to support muli-select where the routes for all
        # worlds are shown on the map
        self._showSelectedJumpRouteOnMapAction =  QtWidgets.QAction('Show Selected Jump Route on Map...', self)
        self._showSelectedJumpRouteOnMapAction.setEnabled(False) # No selection
        self._showSelectedJumpRouteOnMapAction.triggered.connect(self.showSelectedJumpRouteOnMap)

        self._showSelectedCalculationsAction = QtWidgets.QAction('Show Selected Calculations...', self)
        self._showSelectedCalculationsAction.setEnabled(False) # No content to copy
        self._showSelectedCalculationsAction.triggered.connect(self.showSelectedCalculations)

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

    def outcomeColours(self) -> app.OutcomeColours:
        return app.OutcomeColours(self._outcomeColours)

    def setOutcomeColours(self, colours: app.OutcomeColours) -> None:
        if colours == self._outcomeColours:
            return
        self._outcomeColours = app.OutcomeColours(colours)
        self._syncContent()

    def worldTagging(self) -> typing.Optional[logic.WorldTagging]:
        return logic.WorldTagging(self._worldTagging) if self._worldTagging else None

    def setWorldTagging(
            self,
            tagging: typing.Optional[logic.WorldTagging],
            ) -> None:
        if tagging == self._worldTagging:
            return
        self._worldTagging = logic.WorldTagging(tagging) if tagging else None
        self._syncContent()

    def taggingColours(self) -> typing.Optional[app.TaggingColours]:
        return app.TaggingColours(self._taggingColours) if self._taggingColours else None

    def setTaggingColours(
            self,
            colours: typing.Optional[app.TaggingColours]
            ) -> None:
        if colours == self._taggingColours:
            return
        self._taggingColours = app.TaggingColours(colours) if colours else None
        self._syncContent()

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

    def uniqueWorlds(self, selectedOnly: bool = False) -> typing.Set[traveller.World]:
        rowsIter = self.selectedRows() if selectedOnly else range(self.rowCount())
        worlds = set()
        for row in rowsIter:
            tradeOption = self.tradeOption(row)
            if tradeOption:
                worlds.add(tradeOption.purchaseWorld())
                worlds.add(tradeOption.saleWorld())
        return worlds

    def uniquePurchaseWorlds(self, selectedOnly: bool = False) -> typing.Set[traveller.World]:
        rowsIter = self.selectedRows() if selectedOnly else range(self.rowCount())
        worlds = set()
        for row in rowsIter:
            tradeOption = self.tradeOption(row)
            if tradeOption:
                worlds.add(tradeOption.purchaseWorld())
        return worlds

    def uniqueSaleWorlds(self, selectedOnly: bool = False) -> typing.Set[traveller.World]:
        rowsIter = self.selectedRows() if selectedOnly else range(self.rowCount())
        worlds = set()
        for row in rowsIter:
            tradeOption = self.tradeOption(row)
            if tradeOption:
                worlds.add(tradeOption.saleWorld())
        return worlds

    def setHexTooltipProvider(
            self,
            provider: typing.Optional[gui.HexTooltipProvider]
            ) -> None:
        self._hexTooltipProvider = provider

    def insertRow(self, row: int) -> None:
        super().insertRow(row)
        self._syncTradeOptionTableActions()

    def removeRow(self, row: int) -> None:
        super().removeRow(row)
        self._syncTradeOptionTableActions()

    def setRowCount(self, count: int) -> None:
        super().setRowCount(count)
        self._syncTradeOptionTableActions()

    def selectionChanged(
            self,
            selected: QtCore.QItemSelection,
            deselected: QtCore.QItemSelection
            ) -> None:
        super().selectionChanged(selected, deselected)
        self._syncTradeOptionTableActions()

    def showSelectedPurchaseWorldDetails(self) -> None:
        worlds = self.uniquePurchaseWorlds(selectedOnly=True)
        if not worlds:
            return
        self._showWorldDetails(worlds=worlds)

    def showSelectedSaleWorldDetails(self) -> None:
        worlds = self.uniqueSaleWorlds(selectedOnly=True)
        if not worlds:
            return
        self._showWorldDetails(worlds=worlds)

    def showSelectedWorldDetails(self) -> None:
        worlds = self.uniqueWorlds(selectedOnly=True)
        if not worlds:
            return
        self._showWorldDetails(worlds=worlds)

    def showSelectedPurchaseWorldsOnMap(self) -> None:
        worlds = self.uniquePurchaseWorlds(selectedOnly=True)
        if not worlds:
            return
        self._showWorldsOnMap(worlds=worlds)

    def showSelectedSaleWorldsOnMap(self) -> None:
        worlds = self.uniqueSaleWorlds(selectedOnly=True)
        if not worlds:
            return
        self._showWorldsOnMap(worlds=worlds)

    def showSelectedWorldsOnMap(self) -> None:
        worlds = self.uniqueWorlds(selectedOnly=True)
        if not worlds:
            return
        self._showWorldsOnMap(worlds=worlds)

    # TODO: This needs updated to handle multiselect
    def showSelectedJumpRouteOnMap(self) -> None:
        row = self.currentRow()
        if row < 0:
            return
        tradeOption = self.tradeOption(row)
        if not tradeOption:
            return
        route = tradeOption.jumpRoute()
        if not route:
            return

        self._showJumpRouteOnMap(route=route)

    def showSelectedCalculations(self) -> None:
        calculations = []
        for row in self.selectedRows():
            tradeOption = self.tradeOption(row)
            if tradeOption:
                calculations.append(tradeOption.returnOnInvestment())
        self._showCalculations(calculations=calculations)

    def showSelectedPurchaseWorldDetailsAction(self) -> QtWidgets.QAction:
        return self._showSelectedPurchaseWorldDetailsAction

    def setShowSelectedPurchaseWorldDetailsAction(self, action: QtWidgets.QAction) -> None:
        self._showSelectedPurchaseWorldDetailsAction = action

    def showSelectedSaleWorldDetailsAction(self) -> QtWidgets.QAction:
        return self._showSelectedSaleWorldDetailsAction

    def setShowSelectedSaleWorldDetailsAction(self, action: QtWidgets.QAction) -> None:
        self._showSelectedSaleWorldDetailsAction = action

    def showSelectedWorldDetailsAction(self) -> QtWidgets.QAction:
        return self._showSelectedWorldDetailsAction

    def setShowSelectedWorldDetailsAction(self, action: QtWidgets.QAction) -> None:
        self._showSelectedWorldDetailsAction = action

    def showSelectedPurchaseWorldsOnMapAction(self) -> QtWidgets.QAction:
        return self._showSelectedPurchaseWorldsOnMapAction

    def setShowSelectedPurchaseWorldsOnMapAction(self, action: QtWidgets.QAction) -> None:
        self._showSelectedPurchaseWorldsOnMapAction = action

    def showSelectedSaleWorldsOnMapAction(self) -> QtWidgets.QAction:
        return self._showSelectedSaleWorldsOnMapAction

    def setShowSelectedSaleWorldsOnMapAction(self, action: QtWidgets.QAction) -> None:
        self._showSelectedSaleWorldsOnMapAction = action

    def showSelectedWorldsOnMapAction(self) -> QtWidgets.QAction:
        return self._showSelectedWorldsOnMapAction

    def setShowSelectedWorldsOnMapAction(self, action: QtWidgets.QAction) -> None:
        self._showSelectedWorldsOnMapAction = action

    def showSelectedJumpRouteOnMapAction(self) -> QtWidgets.QAction:
        return self._showSelectedJumpRouteOnMapAction

    def setShowSelectedJumpRouteOnMapAction(self, action: QtWidgets.QAction) -> None:
        self._showSelectedJumpRouteOnMapAction = action

    def showSelectedCalculationsAction(self) -> None:
        return self._showSelectedCalculationsAction

    def setShowSelectedCalculationsAction(self, action: QtWidgets.QAction) -> None:
        self._showSelectedCalculationsAction = action

    def fillContextMenu(self, menu: QtWidgets.QMenu) -> None:
        menu.addAction(self.showSelectedPurchaseWorldDetailsAction())
        menu.addAction(self.showSelectedSaleWorldDetailsAction())
        menu.addAction(self.showSelectedWorldDetailsAction())
        menu.addSeparator()
        menu.addAction(self.showSelectedPurchaseWorldsOnMapAction())
        menu.addAction(self.showSelectedSaleWorldsOnMapAction())
        menu.addAction(self.showSelectedWorldsOnMapAction())
        menu.addAction(self.showSelectedJumpRouteOnMapAction())
        menu.addSeparator()

        # Add base class menu options (export, copy to clipboard etc)
        super().fillContextMenu(menu)

        menu.addSeparator()
        menu.addAction(self.showSelectedCalculationsAction())

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

            purchaseWorldTagColour = saleWorldTagColour = None
            if self._worldTagging and self._taggingColours:
                tagLevel = self._worldTagging.calculateWorldTagLevel(purchaseWorld)
                if tagLevel:
                    purchaseWorldTagColour = self._taggingColours.colour(level=tagLevel)

                tagLevel = self._worldTagging.calculateWorldTagLevel(saleWorld)
                if tagLevel:
                    saleWorldTagColour = self._taggingColours.colour(level=tagLevel)

            averageCaseColour = QtGui.QColor(self._outcomeColours.colour(
                outcome=logic.RollOutcome.AverageCase))
            worstCaseColour = QtGui.QColor(self._outcomeColours.colour(
                outcome=logic.RollOutcome.WorstCase))
            bestCaseColour = QtGui.QColor(self._outcomeColours.colour(
                outcome=logic.RollOutcome.BestCase))

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
                    if noteCount and self._taggingColours:
                        tableItem.setBackground(QtGui.QColor(self._taggingColours.colour(logic.TagLevel.Warning)))
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
            return gui.createLogisticsToolTip(
                routeLogistics=tradeOption.routeLogistics(),
                worldTagging=self._worldTagging,
                taggingColours=self._taggingColours)

        return None

    def _syncContent(self) -> None:
        # Disable sorting during sync then re-enable after so sort is
        # only performed once rather than per row
        sortingEnabled = self.isSortingEnabled()
        self.setSortingEnabled(False)

        try:
            for row in range(self.rowCount()):
                self._fillRow(row=row, tradeOption=self.tradeOption(row=row))
        finally:
            self.setSortingEnabled(sortingEnabled)

    def _syncTradeOptionTableActions(self) -> None:
        hasSelection = self.hasSelection()
        if self._showSelectedPurchaseWorldDetailsAction:
            self._showSelectedPurchaseWorldDetailsAction.setEnabled(hasSelection)
        if self._showSelectedSaleWorldDetailsAction:
            self._showSelectedSaleWorldDetailsAction.setEnabled(hasSelection)
        if self._showSelectedWorldDetailsAction:
            self._showSelectedWorldDetailsAction.setEnabled(hasSelection)
        if self._showSelectedPurchaseWorldsOnMapAction:
            self._showSelectedPurchaseWorldsOnMapAction.setEnabled(hasSelection)
        if self._showSelectedSaleWorldsOnMapAction:
            self._showSelectedSaleWorldsOnMapAction.setEnabled(hasSelection)
        if self._showSelectedWorldsOnMapAction:
            self._showSelectedWorldsOnMapAction.setEnabled(hasSelection)
        if self._showSelectedJumpRouteOnMapAction:
            self._showSelectedJumpRouteOnMapAction.setEnabled(hasSelection)
        if self._showSelectedCalculationsAction:
            self._showSelectedCalculationsAction.setEnabled(hasSelection)

    def _showWorldDetails(
            self,
            worlds: typing.Iterable[traveller.World]
            ) -> None:
        detailsWindow = gui.WindowManager.instance().showHexDetailsWindow()
        detailsWindow.addHexes(hexes=[world.hex() for world in worlds])

    def _showWorldsOnMap(
            self,
            worlds: typing.Iterable[traveller.World]
            ) -> None:
        try:
            mapWindow = gui.WindowManager.instance().showUniverseMapWindow()
            mapWindow.clearOverlays()
            mapWindow.highlightHexes(hexes=[world.hex() for world in worlds])
        except Exception as ex:
            message = 'Failed to show world(s) on map'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)

    def _showJumpRouteOnMap(
            self,
            route: logic.JumpRoute
            ) -> None:
        try:
            mapWindow = gui.WindowManager.instance().showUniverseMapWindow()
            mapWindow.clearOverlays()
            mapWindow.setJumpRoute(jumpRoute=route)
        except Exception as ex:
            message = 'Failed to show jump route on map'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)

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
            message = 'Failed to show calculations'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
