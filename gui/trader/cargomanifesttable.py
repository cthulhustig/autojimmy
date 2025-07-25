import app
import enum
import gui
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

    def setHexTooltipProvider(
            self,
            provider: typing.Optional[gui.HexTooltipProvider]
            ) -> None:
        self._hexTooltipProvider = provider

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