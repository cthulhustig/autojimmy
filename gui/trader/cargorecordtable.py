import app
import common
import enum
import gui
import json
import logic
import logging
import traveller
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

class CargoRecordTable(gui.FrozenColumnListTable):
    class ColumnType(enum.Enum):
        TradeGood = 'Trade Good'
        BasePricePerTon = 'Base Price\n(Cr per Ton)'
        # Average case columns
        AverageTotalPrice = 'Avg Total Price\n(Cr)'
        AveragePricePerTon = 'Avg Price\n(Cr per Ton)'
        AverageQuantity = 'Avg Quantity\n(Tons)'
        # Worst case columns
        WorstTotalPrice = 'Worst Total Price\n(Cr)'
        WorstPricePerTon = 'Worst Price\n(Cr per Ton)'
        WorstQuantity = 'Worst Quantity\n(Tons)'
        # Best case columns
        BestTotalPrice = 'Best Total Price\n(Cr)'
        BestPricePerTon = 'Best Price\n(Cr per Ton)'
        BestQuantity = 'Best Quantity\n(Tons)'
        # Set value columns
        SetTotalPrice = 'Total Price\n(Cr)'
        SetPricePerTon = 'Price\n(Cr per Ton)'
        SetQuantity = 'Quantity\n(Tons)'

    AllCaseColumns = [
        ColumnType.TradeGood,
        ColumnType.BasePricePerTon,
        ColumnType.AveragePricePerTon,
        ColumnType.AverageQuantity,
        ColumnType.WorstPricePerTon,
        ColumnType.WorstQuantity,
        ColumnType.BestPricePerTon,
        ColumnType.BestQuantity
    ]

    AvgCaseColumns = [
        ColumnType.TradeGood,
        ColumnType.BasePricePerTon,
        ColumnType.AveragePricePerTon,
        ColumnType.AverageQuantity
    ]

    WorstCaseColumns = [
        ColumnType.TradeGood,
        ColumnType.BasePricePerTon,
        ColumnType.WorstPricePerTon,
        ColumnType.WorstQuantity
    ]

    BestCaseColumns = [
        ColumnType.TradeGood,
        ColumnType.BasePricePerTon,
        ColumnType.BestPricePerTon,
        ColumnType.BestQuantity
    ]

    KnownValueColumns = [
        ColumnType.TradeGood,
        ColumnType.BasePricePerTon,
        ColumnType.SetPricePerTon,
        ColumnType.SetQuantity
    ]

    # v1: Initial version
    # v2: Updated cargo record (de)serialization to include rule system
    # as part of config overhaul that made rules changeable at runtime
    _ContentVersion = 'v2'

    def __init__(
            self,
            outcomeColours: app.OutcomeColours,
            columns: typing.Iterable[ColumnType] = AllCaseColumns
            ) -> None:
        super().__init__()

        self._outcomeColours = app.OutcomeColours(outcomeColours)

        self._showSelectedCalculationsAction = QtWidgets.QAction('Show Selected Calculations...', self)
        self._showSelectedCalculationsAction.setEnabled(False) # No content to copy
        self._showSelectedCalculationsAction.triggered.connect(self.showSelectedCalculations)

        self._showAllCalculationsAction = QtWidgets.QAction('Show All Calculations...', self)
        self._showAllCalculationsAction.setEnabled(False) # No content to copy
        self._showAllCalculationsAction.triggered.connect(self.showAllCalculations)

        self.setColumnHeaders(columns)
        self.setUserColumnHiding(True)
        self.resizeColumnsToContents() # Size columns to header text
        self.setSizeAdjustPolicy(
            QtWidgets.QAbstractScrollArea.SizeAdjustPolicy.AdjustToContentsOnFirstShow)
        for column, columnType in enumerate(columns):
            if columnType == self.ColumnType.TradeGood:
                self.setColumnWidth(column, 200)

    def outcomeColours(self) -> app.OutcomeColours:
        return app.OutcomeColours(self._outcomeColours)

    def setOutcomeColours(self, colours: app.OutcomeColours) -> None:
        if colours == self._outcomeColours:
            return
        self._outcomeColours = app.OutcomeColours(colours)
        self._syncContent()

    def cargoRecord(self, row: int) -> typing.Optional[logic.CargoRecord]:
        tableItem = self.item(row, 0)
        if not tableItem:
            return None
        return tableItem.data(QtCore.Qt.ItemDataRole.UserRole)

    def cargoRecords(self) -> typing.List[logic.CargoRecord]:
        cargoRecords = []
        for row in range(self.rowCount()):
            cargoRecord = self.cargoRecord(row)
            if not cargoRecord:
                continue
            cargoRecords.append(cargoRecord)
        return cargoRecords

    def cargoRecordCount(self) -> int:
        return self.rowCount()

    def cargoRecordAt(self, y: int) -> typing.Optional[logic.CargoRecord]:
        row = self.rowAt(y)
        return self.cargoRecord(row) if row >= 0 else None

    def insertCargoRecord(
            self,
            row: int,
            cargoRecord: logic.CargoRecord
            ) -> int:
        self.insertRow(row)
        return self._fillRow(row, cargoRecord)

    def setCargoRecord(
            self,
            row: int,
            cargoRecord: logic.CargoRecord
            ) -> int:
        return self._fillRow(row, cargoRecord)

    def setCargoRecords(
            self,
            cargoRecords: typing.Optional[typing.Iterable[logic.CargoRecord]]
            ) -> None:
        self.removeAllRows()
        if cargoRecords:
            self.addCargoRecords(cargoRecords=cargoRecords)

    def addCargoRecord(
            self,
            cargoRecord: logic.CargoRecord
            ) -> int:
        return self.insertCargoRecord(self.rowCount(), cargoRecord)

    def addCargoRecords(
            self,
            cargoRecords: typing.Iterable[logic.CargoRecord]
            ) -> None:
        # Temporarily disable sorting to prevent resorting every time a row is added
        sortingEnabled = self.isSortingEnabled()
        self.setSortingEnabled(False)

        try:
            for cargoRecord in cargoRecords:
                self.addCargoRecord(cargoRecord=cargoRecord)
        finally:
            self.setSortingEnabled(sortingEnabled)

    def replaceCargoRecords(
            self,
            replacements: typing.Dict[logic.CargoRecord, logic.CargoRecord]
            ) -> None:
        # Temporarily disable sorting to prevent resorting every time a row is added
        sortingEnabled = self.isSortingEnabled()
        self.setSortingEnabled(False)

        try:
            for row in range(self.rowCount()):
                currentCargoRecord = self.cargoRecord(row)
                if currentCargoRecord in replacements:
                    newCargoRecord = replacements[currentCargoRecord]
                    self._fillRow(row, newCargoRecord)
        finally:
            self.setSortingEnabled(sortingEnabled)

    def currentCargoRecord(self) -> typing.Optional[logic.CargoRecord]:
        row = self.currentRow()
        if row < 0:
            return None
        return self.cargoRecord(row)

    def hasCargoRecordForTradeGood(
            self,
            tradeGood: traveller.TradeGood
            ) -> bool:
        for row in range(self.rowCount()):
            cargoRecord = self.cargoRecord(row)
            if cargoRecord.tradeGood() == tradeGood:
                return True
        return False

    def selectedCargoRecords(self) -> typing.List[logic.CargoRecord]:
        cargoRecords = []
        for row in range(self.rowCount()):
            if self.isRowSelected(row):
                cargoRecord = self.cargoRecord(row)
                if cargoRecord:
                    cargoRecords.append(cargoRecord)
        return cargoRecords

    def showSelectedCalculations(self) -> None:
        calculations = self._gatherCalculations(selectedOnly=True)
        if not calculations:
            return
        self._showCalculations(calculations=calculations)

    def showAllCalculations(self) -> None:
        calculations = self._gatherCalculations(selectedOnly=False)
        if not calculations:
            return
        self._showCalculations(calculations=calculations)

    def showSelectedCalculationsAction(self) -> QtWidgets.QAction:
        return self._showSelectedCalculationsAction

    def setShowSelectedCalculationsAction(
            self,
            action: QtWidgets.QAction
            ) -> None:
        self._showSelectedCalculationsAction = action

    def showAllCalculationsAction(self) -> QtWidgets.QAction:
        return self._showAllCalculationsAction

    def setShowAllCalculationsAction(
            self,
            action: QtWidgets.QAction
            ) -> None:
        self._showAllCalculationsAction = action

    def fillContextMenu(self, menu: QtWidgets.QMenu) -> None:
        # Add base classes context menu (export, copy to clipboard etc)
        super().fillContextMenu(menu)

        menu.addSeparator()
        menu.addAction(self.showSelectedCalculationsAction())
        menu.addAction(self.showAllCalculationsAction())

    def saveContent(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(CargoRecordTable._ContentVersion)

        data = logic.serialiseCargoRecordList(cargoRecords=self.cargoRecords())
        stream.writeQString(json.dumps(data))

        return state

    def restoreContent(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != CargoRecordTable._ContentVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore CargoRecordTable content (Incorrect version)')
            return False

        try:
            data = json.loads(stream.readQString())
            cargoRecords = logic.deserialiseCargoRecordList(data=data)
            for cargoRecord in cargoRecords:
                self.addCargoRecord(cargoRecord)
        except Exception as ex:
            logging.warning(f'Failed to deserialise CargoRecordTable world list', exc_info=ex)
            return False

        return True

    def isEmptyChanged(self) -> None:
        super().isEmptyChanged()
        self._syncCargoRecordTableActions()

    def selectionChanged(
            self,
            selected: QtCore.QItemSelection,
            deselected: QtCore.QItemSelection
            ) -> None:
        super().selectionChanged(selected, deselected)
        self._syncCargoRecordTableActions()

    def _fillRow(
            self,
            row: int,
            cargoRecord: logic.CargoRecord
            ) -> int:
        # Workaround for the issue covered here, re-enabled after setting items
        # https://stackoverflow.com/questions/7960505/strange-qtablewidget-behavior-not-all-cells-populated-after-sorting-followed-b
        sortingEnabled = self.isSortingEnabled()
        self.setSortingEnabled(False)

        try:
            tradeGood = cargoRecord.tradeGood()
            pricePerTon = cargoRecord.pricePerTon()
            quantity = cargoRecord.quantity()
            totalPrice = cargoRecord.totalPrice()

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
                elif columnType == self.ColumnType.BasePricePerTon:
                    tableItem = gui.FormattedNumberTableWidgetItem(tradeGood.basePrice())
                elif columnType == self.ColumnType.AverageTotalPrice:
                    tableItem = gui.FormattedNumberTableWidgetItem(totalPrice.averageCaseCalculation())
                    tableItem.setBackground(averageCaseColour)
                elif columnType == self.ColumnType.AveragePricePerTon:
                    tableItem = gui.FormattedNumberTableWidgetItem(pricePerTon.averageCaseCalculation())
                    tableItem.setBackground(averageCaseColour)
                elif columnType == self.ColumnType.AverageQuantity:
                    tableItem = gui.FormattedNumberTableWidgetItem(quantity.averageCaseCalculation())
                    tableItem.setBackground(averageCaseColour)
                elif columnType == self.ColumnType.WorstTotalPrice:
                    tableItem = gui.FormattedNumberTableWidgetItem(totalPrice.worstCaseCalculation())
                    tableItem.setBackground(worstCaseColour)
                elif columnType == self.ColumnType.WorstPricePerTon:
                    tableItem = gui.FormattedNumberTableWidgetItem(pricePerTon.worstCaseCalculation())
                    tableItem.setBackground(worstCaseColour)
                elif columnType == self.ColumnType.WorstQuantity:
                    tableItem = gui.FormattedNumberTableWidgetItem(quantity.worstCaseCalculation())
                    tableItem.setBackground(worstCaseColour)
                elif columnType == self.ColumnType.BestTotalPrice:
                    tableItem = gui.FormattedNumberTableWidgetItem(totalPrice.bestCaseCalculation())
                    tableItem.setBackground(bestCaseColour)
                elif columnType == self.ColumnType.BestPricePerTon:
                    tableItem = gui.FormattedNumberTableWidgetItem(pricePerTon.bestCaseCalculation())
                    tableItem.setBackground(bestCaseColour)
                elif columnType == self.ColumnType.BestQuantity:
                    tableItem = gui.FormattedNumberTableWidgetItem(quantity.bestCaseCalculation())
                    tableItem.setBackground(bestCaseColour)
                elif columnType == self.ColumnType.SetTotalPrice:
                    # We'd expect this to be a scalar value but use the average in case a range sneaks in
                    tableItem = gui.FormattedNumberTableWidgetItem(totalPrice.averageCaseCalculation())
                elif columnType == self.ColumnType.SetPricePerTon:
                    # We'd expect this to be a scalar value but use the average in case a range sneaks in
                    tableItem = gui.FormattedNumberTableWidgetItem(pricePerTon.averageCaseCalculation())
                elif columnType == self.ColumnType.SetQuantity:
                    # We'd expect this to be a scalar value but use the average in case a range sneaks in
                    tableItem = gui.FormattedNumberTableWidgetItem(quantity.averageCaseCalculation())

                if tableItem:
                    self.setItem(row, column, tableItem)
                    tableItem.setData(QtCore.Qt.ItemDataRole.UserRole, cargoRecord)

            # Take note of the sort column item so we can determine which row index after the table
            # has been sorted
            sortItem = self.item(row, self.horizontalHeader().sortIndicatorSection())
        finally:
            self.setSortingEnabled(sortingEnabled)

        # If we don't have a sort item we assume a derived class has overridden _fillRow to add custom
        # columns and the table is currently sorted by one of those columns. In this the expectation is
        # the derived class will be handling working out the post sort row index.
        return sortItem.row() if sortItem else row

    def _syncContent(self) -> None:
        # Disable sorting during sync then re-enable after so sort is
        # only performed once rather than per row
        sortingEnabled = self.isSortingEnabled()
        self.setSortingEnabled(False)

        try:
            for row in range(self.rowCount()):
                self._fillRow(row=row, cargoRecord=self.cargoRecord(row=row))
        finally:
            self.setSortingEnabled(sortingEnabled)

    def _syncCargoRecordTableActions(self):
        if self._showSelectedCalculationsAction:
            self._showSelectedCalculationsAction.setEnabled(self.hasSelection())
        if self._showAllCalculationsAction:
            self._showAllCalculationsAction.setEnabled(not self.isEmpty())

    def _gatherCalculations(
            self,
            selectedOnly: bool
            ) -> typing.List[common.Calculation]:
        rowIter = self.selectedRows() if selectedOnly else range(self.rowCount())
        calculations = []
        for row in rowIter:
            cargoRecord = self.cargoRecord(row)
            if cargoRecord:
                calculations.append(cargoRecord.pricePerTon())
                calculations.append(cargoRecord.quantity())
        return calculations

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