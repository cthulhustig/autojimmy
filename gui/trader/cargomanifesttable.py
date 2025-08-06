import app
import common
import enum
import gui
import logging
import logic
import traveller
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

class CargoManifestTable(gui.FrozenColumnListTable):
    # The indices of the ColumnId must match the table row
    class ColumnType(enum.Enum):
        PurchaseWorld = 'Purchase World'
        PurchaseSector = 'Purchase Sector'
        PurchaseSubsector = 'Purchase Subsector'
        SaleWorld = 'Sale World'
        SaleSector = 'Sale Sector'
        SaleSubsector = 'Sale Subsector'
        Logistics = 'Logistics\n(Jumps)'
        CargoQuantity = 'Quantity\n(Tons)'

        # Average case columns
        AverageNetProfit = 'Avg Net Profit\n(Cr)'
        AverageGrossProfit = 'Avg Gross Profit\n(Cr)'
        AverageCargoCosts = 'Avg Cargo Costs\n(Cr)'
        AverageLogisticsCosts = 'Avg Logistics Costs\n(Cr)'

        # Worst case columns
        # Highest costs and lowest sale price
        WorstNetProfit = 'Worst Net Profit\n(Cr)'
        WorstGrossProfit = 'Worst Gross Profit\n(Cr)'
        WorstCargoCosts = 'Worst Cargo Costs\n(Cr)'
        WorstLogisticsCosts = 'Worst Logistics Costs\n(Cr)'

        # Best case columns
        # Lowest costs and highest sale price
        BestNetProfit = 'Best Net Profit\n(Cr)'
        BestGrossProfit = 'Best Gross Profit\n(Cr)'
        BestCargoCosts = 'Best Cargo Costs\n(Cr)'
        BestLogisticsCosts = 'Best Logistics Costs\n(Cr)'

    AllColumns = [
        ColumnType.PurchaseWorld,
        ColumnType.PurchaseSector,
        ColumnType.PurchaseSubsector,
        ColumnType.SaleWorld,
        ColumnType.SaleSector,
        ColumnType.SaleSubsector,
        ColumnType.Logistics,
        ColumnType.CargoQuantity,
        ColumnType.AverageNetProfit,
        ColumnType.AverageGrossProfit,
        ColumnType.AverageLogisticsCosts,
        ColumnType.AverageCargoCosts,
        ColumnType.WorstNetProfit,
        ColumnType.WorstGrossProfit,
        ColumnType.WorstLogisticsCosts,
        ColumnType.WorstCargoCosts,
        ColumnType.BestNetProfit,
        ColumnType.BestGrossProfit,
        ColumnType.BestLogisticsCosts,
        ColumnType.BestCargoCosts,
    ]

    # Results when using average values for dice rolls
    AverageCaseColumns = [
        ColumnType.PurchaseWorld,
        ColumnType.PurchaseSector,
        ColumnType.PurchaseSubsector,
        ColumnType.SaleWorld,
        ColumnType.SaleSector,
        ColumnType.SaleSubsector,
        ColumnType.Logistics,
        ColumnType.CargoQuantity,
        ColumnType.AverageNetProfit,
        ColumnType.AverageGrossProfit,
        ColumnType.AverageLogisticsCosts,
        ColumnType.AverageCargoCosts
    ]

    # Highest purchase price and lowest sale price
    WorstCaseColumns = [
        ColumnType.PurchaseWorld,
        ColumnType.PurchaseSector,
        ColumnType.PurchaseSubsector,
        ColumnType.SaleWorld,
        ColumnType.SaleSector,
        ColumnType.SaleSubsector,
        ColumnType.Logistics,
        ColumnType.CargoQuantity,
        ColumnType.WorstNetProfit,
        ColumnType.WorstGrossProfit,
        ColumnType.WorstLogisticsCosts,
        ColumnType.WorstCargoCosts
    ]

    # Lowest purchase price and highest sale price
    BestCaseColumns = [
        ColumnType.PurchaseWorld,
        ColumnType.PurchaseSector,
        ColumnType.PurchaseSubsector,
        ColumnType.SaleWorld,
        ColumnType.SaleSector,
        ColumnType.SaleSubsector,
        ColumnType.Logistics,
        ColumnType.CargoQuantity,
        ColumnType.BestNetProfit,
        ColumnType.BestGrossProfit,
        ColumnType.BestLogisticsCosts,
        ColumnType.BestCargoCosts
    ]

    class MenuAction(enum.Enum):
        ShowSelectedPurchaseWorldDetails = enum.auto()
        ShowSelectedSaleWorldDetails = enum.auto()
        ShowSelectedWorldDetails = enum.auto()
        ShowSelectedPurchaseWorldsOnMap = enum.auto()
        ShowSelectedSaleWorldsOnMap = enum.auto()
        ShowSelectedWorldsOnMap = enum.auto()
        ShowSelectedJumpRouteOnMap = enum.auto()
        ShowSelectedCalculations = enum.auto()

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
        # TODO: This needs support for operating on all rows as well as the selected rows
        action =  QtWidgets.QAction('Show Selected Purchase World Details...', self)
        action.setEnabled(False) # No selection
        action.triggered.connect(self.showSelectedPurchaseWorldDetails)
        self.setMenuAction(CargoManifestTable.MenuAction.ShowSelectedPurchaseWorldDetails, action)

        action =  QtWidgets.QAction('Show Selected Sale World Details...', self)
        action.setEnabled(False) # No selection
        action.triggered.connect(self.showSelectedSaleWorldDetails)
        self.setMenuAction(CargoManifestTable.MenuAction.ShowSelectedSaleWorldDetails, action)

        action =  QtWidgets.QAction('Show Selected World Details...', self)
        action.setEnabled(False) # No selection
        action.triggered.connect(self.showSelectedWorldDetails)
        self.setMenuAction(CargoManifestTable.MenuAction.ShowSelectedWorldDetails, action)

        action =  QtWidgets.QAction('Show Selected Purchase Worlds on Map...', self)
        action.setEnabled(False) # No selection
        action.triggered.connect(self.showSelectedPurchaseWorldsOnMap)
        self.setMenuAction(CargoManifestTable.MenuAction.ShowSelectedPurchaseWorldsOnMap, action)

        action =  QtWidgets.QAction('Show Selected Sale Worlds on Map...', self)
        action.setEnabled(False) # No selection
        action.triggered.connect(self.showSelectedSaleWorldsOnMap)
        self.setMenuAction(CargoManifestTable.MenuAction.ShowSelectedSaleWorldsOnMap, action)

        action =  QtWidgets.QAction('Show Selected Worlds on Map...', self)
        action.setEnabled(False) # No selection
        action.triggered.connect(self.showSelectedWorldsOnMap)
        self.setMenuAction(CargoManifestTable.MenuAction.ShowSelectedWorldsOnMap, action)

        action =  QtWidgets.QAction('Show Selected Jump Route on Map...', self)
        action.setEnabled(False) # No selection
        action.triggered.connect(self.showSelectedJumpRouteOnMap)
        self.setMenuAction(CargoManifestTable.MenuAction.ShowSelectedJumpRouteOnMap, action)

        action = QtWidgets.QAction('Show Selected Calculations...', self)
        action.setEnabled(False) # No content to copy
        action.triggered.connect(self.showSelectedCalculations)
        self.setMenuAction(CargoManifestTable.MenuAction.ShowSelectedCalculations, action)

        self.setColumnHeaders(columns)
        self.setUserColumnHiding(True)
        self.resizeColumnsToContents() # Size columns to header text
        self.setSizeAdjustPolicy(
            QtWidgets.QAbstractScrollArea.SizeAdjustPolicy.AdjustToContentsOnFirstShow)
        for column, columnType in enumerate(columns):
            if columnType == self.ColumnType.PurchaseWorld or \
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

    def cargoManifest(self, row: int) -> typing.Optional[logic.CargoManifest]:
        tableItem = self.item(row, 0)
        if not tableItem:
            return None
        return tableItem.data(QtCore.Qt.ItemDataRole.UserRole)

    def cargoManifests(self) -> typing.List[logic.CargoManifest]:
        manifests = []
        for row in range(self.rowCount()):
            cargoManifest = self.cargoManifest(row)
            if not cargoManifest:
                continue
            manifests.append(cargoManifest)
        return manifests

    def cargoManifestAt(self, y: int) -> typing.Optional[logic.CargoManifest]:
        row = self.rowAt(y)
        return self.cargoManifest(row) if row >= 0 else None

    def insertCargoManifest(self, row: int, cargoManifest: logic.CargoManifest) -> int:
        self.insertRow(row)
        return self._fillRow(row, cargoManifest)

    def setCargoManifest(self, row: int, cargoManifest: logic.CargoManifest) -> int:
        return self._fillRow(row, cargoManifest)

    def addCargoManifest(self, cargoManifest: logic.CargoManifest) -> int:
        return self.insertCargoManifest(self.rowCount(), cargoManifest)

    def currentCargoManifest(self):
        row = self.currentRow()
        if row < 0:
            return None
        return self.cargoManifest(row)

    def uniqueWorlds(self, selectedOnly: bool = False) -> typing.Set[traveller.World]:
        rowsIter = self.selectedRows() if selectedOnly else range(self.rowCount())
        worlds = set()
        for row in rowsIter:
            cargoManifest = self.cargoManifest(row)
            if cargoManifest:
                worlds.add(cargoManifest.purchaseWorld())
                worlds.add(cargoManifest.saleWorld())
        return worlds

    def uniquePurchaseWorlds(self, selectedOnly: bool = False) -> typing.Set[traveller.World]:
        rowsIter = self.selectedRows() if selectedOnly else range(self.rowCount())
        worlds = set()
        for row in rowsIter:
            cargoManifest = self.cargoManifest(row)
            if cargoManifest:
                worlds.add(cargoManifest.purchaseWorld())
        return worlds

    def uniqueSaleWorlds(self, selectedOnly: bool = False) -> typing.Set[traveller.World]:
        rowsIter = self.selectedRows() if selectedOnly else range(self.rowCount())
        worlds = set()
        for row in rowsIter:
            cargoManifest = self.cargoManifest(row)
            if cargoManifest:
                worlds.add(cargoManifest.saleWorld())
        return worlds

    def setHexTooltipProvider(
            self,
            provider: typing.Optional[gui.HexTooltipProvider]
            ) -> None:
        self._hexTooltipProvider = provider

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

    def showSelectedJumpRouteOnMap(self) -> None:
        row = self.currentRow()
        if row < 0:
            return
        cargoManifest = self.cargoManifest(row)
        if not cargoManifest:
            return
        route = cargoManifest.jumpRoute()
        if not route:
            return

        self._showJumpRouteOnMap(route=route)

    def showSelectedCalculations(self) -> None:
        calculations = []
        for row in self.selectedRows():
            cargoManifest = self.cargoManifest(row)
            if cargoManifest:
                calculations.append(cargoManifest.netProfit())
        self._showCalculations(calculations=calculations)

    def fillContextMenu(self, menu: QtWidgets.QMenu) -> None:
        needsSeparator = False

        action = self.menuAction(CargoManifestTable.MenuAction.ShowSelectedPurchaseWorldDetails)
        if action:
            menu.addAction(action)
            needsSeparator = True

        action = self.menuAction(CargoManifestTable.MenuAction.ShowSelectedSaleWorldDetails)
        if action:
            menu.addAction(action)
            needsSeparator = True

        action = self.menuAction(CargoManifestTable.MenuAction.ShowSelectedWorldDetails)
        if action:
            menu.addAction(action)
            needsSeparator = True

        if needsSeparator:
            menu.addSeparator()
            needsSeparator = False

        action = self.menuAction(CargoManifestTable.MenuAction.ShowSelectedPurchaseWorldsOnMap)
        if action:
            menu.addAction(action)
            needsSeparator = True

        action = self.menuAction(CargoManifestTable.MenuAction.ShowSelectedSaleWorldsOnMap)
        if action:
            menu.addAction(action)
            needsSeparator = True

        action = self.menuAction(CargoManifestTable.MenuAction.ShowSelectedWorldsOnMap)
        if action:
            menu.addAction(action)
            needsSeparator = True

        action = self.menuAction(CargoManifestTable.MenuAction.ShowSelectedJumpRouteOnMap)
        if action:
            menu.addAction(action)
            needsSeparator = True

        if needsSeparator:
            menu.addSeparator()
            needsSeparator = False

        # Add base class menu options (export, copy to clipboard etc)
        beforeCount = len(menu.actions())
        super().fillContextMenu(menu)

        if len(menu.actions()) > beforeCount:
            menu.addSeparator()

        action = self.menuAction(CargoManifestTable.MenuAction.ShowSelectedCalculations)
        if action:
            menu.addAction(action)

    def isEmptyChanged(self) -> None:
        super().isEmptyChanged()
        self._syncCargoManifestTableActions()

    def selectionChanged(
            self,
            selected: QtCore.QItemSelection,
            deselected: QtCore.QItemSelection
            ) -> None:
        super().selectionChanged(selected, deselected)
        self._syncCargoManifestTableActions()

    def _fillRow(
            self,
            row: int,
            cargoManifest: logic.CargoManifest
            ) -> int:
        # Workaround for the issue covered here, re-enabled after setting items
        # https://stackoverflow.com/questions/7960505/strange-qtablewidget-behavior-not-all-cells-populated-after-sorting-followed-b
        sortingEnabled = self.isSortingEnabled()
        self.setSortingEnabled(False)

        try:
            purchaseWorld = cargoManifest.purchaseWorld()
            saleWorld = cargoManifest.saleWorld()
            netProfit = cargoManifest.netProfit()
            grossProfit = cargoManifest.grossProfit()
            cargoCost = cargoManifest.cargoCost()
            logisticsCost = cargoManifest.logisticsCosts()

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
                if columnType == self.ColumnType.PurchaseWorld:
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
                elif columnType == self.ColumnType.Logistics:
                    tableItem = gui.FormattedNumberTableWidgetItem(cargoManifest.jumpCount())
                elif columnType == self.ColumnType.CargoQuantity:
                    tableItem = gui.FormattedNumberTableWidgetItem(cargoManifest.cargoQuantity())
                #
                # Average case values
                #
                elif columnType == self.ColumnType.AverageNetProfit:
                    tableItem = gui.FormattedNumberTableWidgetItem(netProfit.averageCaseValue())
                    tableItem.setBackground(averageCaseColour)
                elif columnType == self.ColumnType.AverageGrossProfit:
                    tableItem = gui.FormattedNumberTableWidgetItem(grossProfit.averageCaseValue())
                    tableItem.setBackground(averageCaseColour)
                elif columnType == self.ColumnType.AverageCargoCosts:
                    tableItem = gui.FormattedNumberTableWidgetItem(cargoCost.averageCaseValue())
                    tableItem.setBackground(averageCaseColour)
                elif columnType == self.ColumnType.AverageLogisticsCosts:
                    tableItem = gui.FormattedNumberTableWidgetItem(logisticsCost.averageCaseValue())
                    tableItem.setBackground(averageCaseColour)
                #
                # Worst case values
                #
                elif columnType == self.ColumnType.WorstNetProfit:
                    tableItem = gui.FormattedNumberTableWidgetItem(netProfit.worstCaseValue())
                    tableItem.setBackground(worstCaseColour)
                elif columnType == self.ColumnType.WorstGrossProfit:
                    tableItem = gui.FormattedNumberTableWidgetItem(grossProfit.worstCaseValue())
                    tableItem.setBackground(worstCaseColour)
                elif columnType == self.ColumnType.WorstCargoCosts:
                    tableItem = gui.FormattedNumberTableWidgetItem(cargoCost.worstCaseValue())
                    tableItem.setBackground(worstCaseColour)
                elif columnType == self.ColumnType.WorstLogisticsCosts:
                    tableItem = gui.FormattedNumberTableWidgetItem(logisticsCost.worstCaseValue())
                    tableItem.setBackground(worstCaseColour)
                #
                # Best case values
                #
                elif columnType == self.ColumnType.BestNetProfit:
                    tableItem = gui.FormattedNumberTableWidgetItem(netProfit.bestCaseValue())
                    tableItem.setBackground(bestCaseColour)
                elif columnType == self.ColumnType.BestGrossProfit:
                    tableItem = gui.FormattedNumberTableWidgetItem(grossProfit.bestCaseValue())
                    tableItem.setBackground(bestCaseColour)
                elif columnType == self.ColumnType.BestCargoCosts:
                    tableItem = gui.FormattedNumberTableWidgetItem(cargoCost.bestCaseValue())
                    tableItem.setBackground(bestCaseColour)
                elif columnType == self.ColumnType.BestLogisticsCosts:
                    tableItem = gui.FormattedNumberTableWidgetItem(logisticsCost.bestCaseValue())
                    tableItem.setBackground(bestCaseColour)
                assert(tableItem) # Check for missed enum

                if tableItem:
                    self.setItem(row, column, tableItem)
                    tableItem.setData(QtCore.Qt.ItemDataRole.UserRole, cargoManifest)

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
        cargoManifest = self.cargoManifest(item.row())
        if not cargoManifest:
            return None

        columnType = self.columnHeader(item.column())

        if columnType == self.ColumnType.PurchaseWorld or columnType == self.ColumnType.PurchaseSector or \
            columnType == self.ColumnType.PurchaseSubsector:
            purchaseWorld = cargoManifest.purchaseWorld()
            if self._hexTooltipProvider:
                return self._hexTooltipProvider.tooltip(hex=purchaseWorld.hex())
            else:
                return traveller.WorldManager.instance().canonicalHexName(
                    milieu=purchaseWorld.milieu(),
                    hex=purchaseWorld.hex())
        elif columnType == self.ColumnType.SaleWorld or columnType == self.ColumnType.SaleSector or \
            columnType == self.ColumnType.SaleSubsector:
            saleWorld = cargoManifest.saleWorld()
            if self._hexTooltipProvider:
                return self._hexTooltipProvider.tooltip(hex=saleWorld.hex())
            else:
                return traveller.WorldManager.instance().canonicalHexName(
                    milieu=saleWorld.milieu(),
                    hex=saleWorld.hex())
        elif columnType == self.ColumnType.Logistics:
            return gui.createLogisticsToolTip(
                routeLogistics=cargoManifest.routeLogistics(),
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
                self._fillRow(row=row, cargoManifest=self.cargoManifest(row=row))
        finally:
            self.setSortingEnabled(sortingEnabled)

    def _syncCargoManifestTableActions(self) -> None:
        selectionCount = len(self.selectedRows())
        hasSelection = selectionCount > 0
        hasSingleSelection = selectionCount == 1

        action = self.menuAction(CargoManifestTable.MenuAction.ShowSelectedPurchaseWorldDetails)
        if action:
            action.setEnabled(hasSelection)

        action = self.menuAction(CargoManifestTable.MenuAction.ShowSelectedSaleWorldDetails)
        if action:
            action.setEnabled(hasSelection)

        action = self.menuAction(CargoManifestTable.MenuAction.ShowSelectedWorldDetails)
        if action:
            action.setEnabled(hasSelection)

        action = self.menuAction(CargoManifestTable.MenuAction.ShowSelectedPurchaseWorldsOnMap)
        if action:
            action.setEnabled(hasSelection)

        action = self.menuAction(CargoManifestTable.MenuAction.ShowSelectedSaleWorldsOnMap)
        if action:
            action.setEnabled(hasSelection)

        action = self.menuAction(CargoManifestTable.MenuAction.ShowSelectedWorldsOnMap)
        if action:
            action.setEnabled(hasSelection)

        action = self.menuAction(CargoManifestTable.MenuAction.ShowSelectedJumpRouteOnMap)
        if action:
            # Map currently only supports a single jump route so only
            # enable the action when there is only one route to avoid
            # ambiguity
            action.setEnabled(hasSingleSelection)

        action = self.menuAction(CargoManifestTable.MenuAction.ShowSelectedCalculations)
        if action:
            action.setEnabled(hasSelection)

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