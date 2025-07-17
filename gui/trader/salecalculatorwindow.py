import app
import common
import enum
import gui
import logging
import logic
import traveller
import travellermap
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

_WelcomeMessage = """
    <html>
    <p>The Sale Calculator window is a tool for Referees to use when a player is selling trade goods
    on a given world. It takes the list of trade goods the player has and rolls virtual dice to
    calculate the price that a buyer would pay for them.<p>
    <p>Currently, only Mongoose 1e & 2e rules are supported. Which rules are used can be selected in
    the Configuration dialog. Data from Traveller Map is used to calculate the Purchase DMs for the
    trade goods.</p>
    </html>
"""

class _CustomColumns(enum.Enum):
    SalePricePerTon = 'Sale Price\n(Cr per Ton)'
    TotalSalePrice = 'Total Sale Price\n(Cr)'
    PurchasePricePerTon = 'Purchase Price\n(Cr per Ton)'
    TotalPurchasePrice = 'Total Purchase Price\n(Cr)'


_SaleCargoColumns = [
    gui.CargoRecordTable.ColumnType.TradeGood,
    gui.CargoRecordTable.ColumnType.SetQuantity
]

_SalePriceColumns = [
    gui.CargoRecordTable.ColumnType.TradeGood,
    gui.CargoRecordTable.ColumnType.BasePricePerTon,
    _CustomColumns.SalePricePerTon,
    gui.CargoRecordTable.ColumnType.SetQuantity,
    _CustomColumns.TotalSalePrice,
]

class _CustomCargoRecordTable(gui.CargoRecordTable):
    def __init__(
            self,
            outcomeColours: app.OutcomeColours,
            columns: typing.Iterable[typing.Union[_CustomColumns, gui.CargoRecordTable.ColumnType]]
            ) -> None:
        super().__init__(
            outcomeColours=outcomeColours,
            columns=columns)

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
            super()._fillRow(row, cargoRecord)

            pricePerTon = cargoRecord.pricePerTon()
            totalPrice = cargoRecord.totalPrice()

            for column in range(self.columnCount()):
                columnType = self.columnHeader(column)
                tableItem = None
                if columnType == _CustomColumns.TotalPurchasePrice or \
                        columnType == _CustomColumns.TotalSalePrice:
                    # We'd expect this to be a scalar value but use the average in case a range sneaks in
                    tableItem = gui.FormattedNumberTableWidgetItem(totalPrice.averageCaseCalculation())
                elif columnType == _CustomColumns.PurchasePricePerTon or \
                        columnType == _CustomColumns.SalePricePerTon:
                    # We'd expect this to be a scalar value but use the average in case a range sneaks in
                    tableItem = gui.FormattedNumberTableWidgetItem(pricePerTon.averageCaseCalculation())

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

class SaleCalculatorWindow(gui.WindowWidget):
    def __init__(self) -> None:
        super().__init__(
            title='Sale Calculator',
            configSection='SaleCalculatorWindow')

        self._randomGenerator = common.RandomGenerator()

        self._hexTooltipProvider = gui.HexTooltipProvider(
            milieu=app.Config.instance().value(option=app.ConfigOption.Milieu),
            rules=app.Config.instance().value(option=app.ConfigOption.Rules),
            showImages=app.Config.instance().value(option=app.ConfigOption.ShowToolTipImages),
            mapStyle=app.Config.instance().value(option=app.ConfigOption.MapStyle),
            mapOptions=app.Config.instance().value(option=app.ConfigOption.MapOptions),
            worldTagging=app.Config.instance().value(option=app.ConfigOption.WorldTagging),
            taggingColours=app.Config.instance().value(option=app.ConfigOption.TaggingColours))

        self._setupWorldSelectControls()
        self._setupConfigurationControls()
        self._setupCargoControls()
        self._setupSalePriceControls()
        self._setupDiceRollControls()

        leftLayout = QtWidgets.QVBoxLayout()
        leftLayout.setContentsMargins(0, 0, 0, 0)
        leftLayout.addWidget(self._worldGroupBox)
        leftLayout.addWidget(self._configurationGroupBox)
        leftLayout.addWidget(self._cargoGroupBox)
        leftWidget = QtWidgets.QWidget()
        leftWidget.setLayout(leftLayout)

        self._resultsSplitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        self._resultsSplitter.addWidget(self._salePriceGroupBox)
        self._resultsSplitter.addWidget(self._diceRollGroupBox)

        self._leftRightSplitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self._leftRightSplitter.addWidget(leftWidget)
        self._leftRightSplitter.addWidget(self._resultsSplitter)

        windowLayout = QtWidgets.QVBoxLayout()
        windowLayout.addWidget(self._leftRightSplitter)

        self.setLayout(windowLayout)

        app.Config.instance().configChanged.connect(self._appConfigChanged)

    def firstShowEvent(self, e: QtGui.QShowEvent) -> None:
        QtCore.QTimer.singleShot(0, self._showWelcomeMessage)
        return super().firstShowEvent(e)

    def loadSettings(self) -> None:
        super().loadSettings()

        self._settings.beginGroup(self._configSection)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='SaleWorldState',
            type=QtCore.QByteArray)
        if storedValue:
            self._saleWorldWidget.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='PlayerBrokerDMState',
            type=QtCore.QByteArray)
        if storedValue:
            self._playerBrokerDmSpinBox.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='LocalBrokerState',
            type=QtCore.QByteArray)
        if storedValue:
            self._localBrokerSpinBox.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='BuyerDmState',
            type=QtCore.QByteArray)
        if storedValue:
            self._buyerDmSpinBox.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='BlackMarketState',
            type=QtCore.QByteArray)
        if storedValue:
            self._blackMarketCheckBox.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='PriceScaleState',
            type=QtCore.QByteArray)
        if storedValue:
            self._priceScaleSpinBox.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='CargoTableState',
            type=QtCore.QByteArray)
        if storedValue:
            self._cargoTable.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='CargoTableContent',
            type=QtCore.QByteArray)
        if storedValue:
            self._cargoTable.restoreContent(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='SalePriceTableState',
            type=QtCore.QByteArray)
        if storedValue:
            self._salePricesTable.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='SalePriceTableContent',
            type=QtCore.QByteArray)
        if storedValue:
            self._salePricesTable.restoreContent(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='DiceRollTableState',
            type=QtCore.QByteArray)
        if storedValue:
            self._diceRollTable.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='ResultsSplitterState',
            type=QtCore.QByteArray)
        if storedValue:
            self._resultsSplitter.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='LeftRightsSplitterState',
            type=QtCore.QByteArray)
        if storedValue:
            self._leftRightSplitter.restoreState(storedValue)

        self._settings.endGroup()

    def saveSettings(self) -> None:
        self._settings.beginGroup(self._configSection)

        self._settings.setValue('SaleWorldState', self._saleWorldWidget.saveState())
        self._settings.setValue('PlayerBrokerDMState', self._playerBrokerDmSpinBox.saveState())
        self._settings.setValue('LocalBrokerState', self._localBrokerSpinBox.saveState())
        self._settings.setValue('BuyerDmState', self._buyerDmSpinBox.saveState())
        self._settings.setValue('BlackMarketState', self._blackMarketCheckBox.saveState())
        self._settings.setValue('PriceScaleState', self._priceScaleSpinBox.saveState())
        self._settings.setValue('CargoTableState', self._cargoTable.saveState())
        self._settings.setValue('SalePriceTableState', self._salePricesTable.saveState())
        self._settings.setValue('DiceRollTableState', self._diceRollTable.saveState())
        self._settings.setValue('ResultsSplitterState', self._resultsSplitter.saveState())
        self._settings.setValue('LeftRightsSplitterState', self._leftRightSplitter.saveState())

        self._settings.endGroup()

        super().saveSettings()

    def _setupWorldSelectControls(self) -> None:
        milieu = app.Config.instance().value(option=app.ConfigOption.Milieu)
        rules = app.Config.instance().value(option=app.ConfigOption.Rules)
        mapStyle = app.Config.instance().value(option=app.ConfigOption.MapStyle)
        mapOptions = app.Config.instance().value(option=app.ConfigOption.MapOptions)
        mapRendering = app.Config.instance().value(option=app.ConfigOption.MapRendering)
        mapAnimations = app.Config.instance().value(option=app.ConfigOption.MapAnimations)
        worldTagging = app.Config.instance().value(option=app.ConfigOption.WorldTagging)
        taggingColours = app.Config.instance().value(option=app.ConfigOption.TaggingColours)

        self._saleWorldWidget = gui.HexSelectToolWidget(
            milieu=milieu,
            rules=rules,
            mapStyle=mapStyle,
            mapOptions=mapOptions,
            mapRendering=mapRendering,
            mapAnimations=mapAnimations,
            worldTagging=worldTagging,
            taggingColours=taggingColours,
            labelText='Select World:')
        self._saleWorldWidget.setHexTooltipProvider(
            provider=self._hexTooltipProvider)
        self._saleWorldWidget.enableMapSelectButton(True)
        self._saleWorldWidget.enableShowInfoButton(True)
        self._saleWorldWidget.selectionChanged.connect(self._saleWorldChanged)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self._saleWorldWidget)

        self._worldGroupBox = QtWidgets.QGroupBox('Sale World')
        self._worldGroupBox.setLayout(layout)

    def _setupConfigurationControls(self) -> None:
        rules = app.Config.instance().value(option=app.ConfigOption.Rules)

        self._playerBrokerDmSpinBox = gui.SkillSpinBox(
            value=1,
            toolTip=gui.PlayerBrokerDmToolTip)

        self._localBrokerSpinBox = gui.LocalBrokerSpinBox(
            enabled=False,
            value=0,
            rules=rules)

        self._buyerDmSpinBox = gui.SkillSpinBox(
            value=2, # Default for MGT 2022 so just use as default for everything
            toolTip=gui.createStringToolTip('Buyer\'s DM bonus'))

        self._blackMarketCheckBox = gui.CheckBoxEx()

        self._priceScaleSpinBox = gui.SpinBoxEx()
        self._priceScaleSpinBox.setRange(1, 1000)
        self._priceScaleSpinBox.setValue(100)
        self._priceScaleSpinBox.setToolTip(gui.createStringToolTip(
            '<p>Sale price scale percentage</p>' \
            '<p>This allows GMs to increase/decrease the standard sale price of all trade goods on a world for whatever in game reasons they see fit</p>',
            escape=False))

        layout = gui.FormLayoutEx()
        layout.addRow('Player\'s Broker DM:', self._playerBrokerDmSpinBox)
        layout.addRow('Local Sale Broker:', self._localBrokerSpinBox)
        layout.addRow('Buyer DM:', self._buyerDmSpinBox)
        layout.addRow('Black Market Buyer:', self._blackMarketCheckBox)
        layout.addRow('Price Scale (%):', self._priceScaleSpinBox)

        self._configurationGroupBox = QtWidgets.QGroupBox('Configuration')
        self._configurationGroupBox.setDisabled(True)
        self._configurationGroupBox.setLayout(layout)

    def _setupCargoControls(self) -> None:
        outcomeColours = app.Config.instance().value(
            option=app.ConfigOption.OutcomeColours)

        self._cargoTable = _CustomCargoRecordTable(
            outcomeColours=outcomeColours,
            columns=_SaleCargoColumns)
        self._cargoTable.setMinimumHeight(200)
        self._cargoTable.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self._cargoTable.customContextMenuRequested.connect(self._showCargoTableContextMenu)
        self._cargoTable.keyPressed.connect(self._cargoTableKeyPressed)
        self._cargoTable.doubleClicked.connect(self._editCargo)

        self._importCargoButton = QtWidgets.QPushButton('Import...')
        self._importCargoButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)
        self._importCargoButton.clicked.connect(self._importCargo)

        self._addCargoButton = QtWidgets.QPushButton('Add...')
        self._addCargoButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)
        self._addCargoButton.clicked.connect(self._addCargo)

        self._editCargoButton = QtWidgets.QPushButton('Edit...')
        self._editCargoButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)
        self._editCargoButton.clicked.connect(self._editCargo)

        self._removeCargoButton = QtWidgets.QPushButton('Remove')
        self._removeCargoButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)
        self._removeCargoButton.clicked.connect(self._cargoTable.removeSelectedRows)

        self._removeAllCargoButton = QtWidgets.QPushButton('Remove All')
        self._removeAllCargoButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)
        self._removeAllCargoButton.clicked.connect(self._cargoTable.removeAllRows)

        buttonLayout = QtWidgets.QHBoxLayout()
        buttonLayout.setContentsMargins(0, 0, 0, 0)
        buttonLayout.addWidget(self._importCargoButton)
        buttonLayout.addStretch()
        buttonLayout.addWidget(self._addCargoButton)
        buttonLayout.addWidget(self._editCargoButton)
        buttonLayout.addWidget(self._removeCargoButton)
        buttonLayout.addWidget(self._removeAllCargoButton)

        mainLayout = QtWidgets.QVBoxLayout()
        mainLayout.addWidget(self._cargoTable)
        mainLayout.addLayout(buttonLayout)

        self._cargoGroupBox = QtWidgets.QGroupBox('Cargo to Sell')
        self._cargoGroupBox.setDisabled(True)
        self._cargoGroupBox.setLayout(mainLayout)

    def _setupSalePriceControls(self) -> None:
        outcomeColours = app.Config.instance().value(
            option=app.ConfigOption.OutcomeColours)

        self._generateButton = QtWidgets.QPushButton('Generate Sale Prices')
        self._generateButton.clicked.connect(self._generateSalePrices)

        self._totalSalePriceLabel = gui.PrefixLabel('Total Sale Price: ')

        self._salePricesTable = _CustomCargoRecordTable(
            outcomeColours=outcomeColours,
            columns=_SalePriceColumns)
        self._salePricesTable.setMinimumHeight(200)
        self._salePricesTable.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self._salePricesTable.customContextMenuRequested.connect(self._showSalePricesTableContextMenu)
        self._salePricesTable.keyPressed.connect(self._salePricesTableKeyPressed)
        self._salePricesTable.doubleClicked.connect(self._editSalePrice)

        self._editSalePriceButton = QtWidgets.QPushButton('Edit...')
        self._editSalePriceButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)
        self._editSalePriceButton.clicked.connect(self._editSalePrice)

        self._removeSalePriceButton = QtWidgets.QPushButton('Remove')
        self._removeSalePriceButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)
        self._removeSalePriceButton.clicked.connect(self._salePricesTable.removeSelectedRows)

        self._removeAllSalePricesButton = QtWidgets.QPushButton('Remove All')
        self._removeAllSalePricesButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)
        self._removeAllSalePricesButton.clicked.connect(self._salePricesTable.removeAllRows)

        buttonLayout = QtWidgets.QHBoxLayout()
        buttonLayout.setContentsMargins(0, 0, 0, 0)
        buttonLayout.addStretch()
        buttonLayout.addWidget(self._editSalePriceButton)
        buttonLayout.addWidget(self._removeSalePriceButton)
        buttonLayout.addWidget(self._removeAllSalePricesButton)

        mainLayout = QtWidgets.QVBoxLayout()
        mainLayout.addWidget(self._generateButton)
        mainLayout.addWidget(self._totalSalePriceLabel)
        mainLayout.addWidget(self._salePricesTable)
        mainLayout.addLayout(buttonLayout)

        self._salePriceGroupBox = QtWidgets.QGroupBox('Sale Prices')
        self._salePriceGroupBox.setDisabled(True)
        self._salePriceGroupBox.setLayout(mainLayout)

    def _setupDiceRollControls(self) -> None:
        self._diceRollTable = gui.DiceRollTable()

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self._diceRollTable)

        self._diceRollGroupBox = QtWidgets.QGroupBox('Dice Rolls')
        self._diceRollGroupBox.setDisabled(True)
        self._diceRollGroupBox.setLayout(layout)

    def _showCalculations(
            self,
            cargoRecord: logic.CargoRecord
            ) -> None:
        try:
            calculationWindow = gui.WindowManager.instance().showCalculationWindow()
            calculationWindow.showCalculations(calculations=[
                cargoRecord.pricePerTon(),
                cargoRecord.quantity()])
        except Exception as ex:
            message = 'Failed to show calculations'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)

    def _updateTotalSalePrice(self) -> None:
        if self._salePricesTable.isEmpty():
            self._totalSalePriceLabel.setText('')

        total = 0
        for salePrice in self._salePricesTable.cargoRecords():
            total += salePrice.totalPrice().value()
        self._totalSalePriceLabel.setText(common.formatNumber(number=total, infix='Cr'))

    def _loadCargoRecordsPrompt(self) -> typing.Optional[typing.Iterable[logic.CargoRecord]]:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            'Open File',
            QtCore.QDir.homePath(),
            'JSON (*.json)')
        if not path:
            return None

        try:
            cargoRecords = logic.readCargoRecordList(filePath=path)
        except Exception as ex:
            message = f'Failed to load cargo records from "{path}"'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return None

        if not cargoRecords:
            gui.MessageBoxEx.critical(
                parent=self,
                text=f'File "{path}" contains no cargo records')
            return None

        return cargoRecords

    def _appConfigChanged(
            self,
            option: app.ConfigOption,
            oldValue: typing.Any,
            newValue: typing.Any
            ) -> None:
        if option is app.ConfigOption.Milieu:
            self._hexTooltipProvider.setMilieu(milieu=newValue)
            self._saleWorldWidget.setMilieu(milieu=newValue)
        elif option is app.ConfigOption.Rules:
            self._hexTooltipProvider.setRules(rules=newValue)
            self._saleWorldWidget.setRules(rules=newValue)
            self._localBrokerSpinBox.setRules(rules=newValue)
        elif option is app.ConfigOption.MapStyle:
            self._hexTooltipProvider.setMapStyle(style=newValue)
            self._saleWorldWidget.setMapStyle(style=newValue)
        elif option is app.ConfigOption.MapOptions:
            self._hexTooltipProvider.setMapOptions(options=newValue)
            self._saleWorldWidget.setMapOptions(options=newValue)
        elif option is app.ConfigOption.MapRendering:
            self._saleWorldWidget.setMapRendering(rendering=newValue)
        elif option is app.ConfigOption.MapAnimations:
            self._saleWorldWidget.setMapAnimations(enabled=newValue)
        elif option is app.ConfigOption.ShowToolTipImages:
            self._hexTooltipProvider.setShowImages(show=newValue)
        elif option is app.ConfigOption.OutcomeColours:
            self._cargoTable.setOutcomeColours(colours=newValue)
            self._salePricesTable.setOutcomeColours(colours=newValue)
        elif option is app.ConfigOption.WorldTagging:
            self._hexTooltipProvider.setWorldTagging(tagging=newValue)
            self._saleWorldWidget.setWorldTagging(tagging=newValue)
        elif option is app.ConfigOption.TaggingColours:
            self._hexTooltipProvider.setTaggingColours(colours=newValue)
            self._saleWorldWidget.setTaggingColours(colours=newValue)

    def _saleWorldChanged(self) -> None:
        disable = not self._saleWorldWidget.selectedWorld()
        self._configurationGroupBox.setDisabled(disable)
        self._cargoGroupBox.setDisabled(disable)
        self._salePriceGroupBox.setDisabled(disable)
        self._diceRollGroupBox.setDisabled(disable)

    def _importCargo(self) -> None:
        if not self._cargoTable.isEmpty():
            answer = gui.AutoSelectMessageBox.question(
                parent=self,
                text='This will replace the existing cargo.\nDo you want to continue?',
                stateKey='SaleCalculatorReplaceCargo',
                # Only remember if the user clicked yes
                rememberState=QtWidgets.QMessageBox.StandardButton.Yes)
            if answer != QtWidgets.QMessageBox.StandardButton.Yes:
                return

        cargoRecords = self._loadCargoRecordsPrompt()
        if not cargoRecords:
            # The user cancelled the load at the file dialog
            return

        rules = app.Config.instance().value(option=app.ConfigOption.Rules)
        exoticsTradeGood = traveller.tradeGoodFromId(
            ruleSystem=rules.system(),
            tradeGoodId=traveller.TradeGoodIds.Exotics)

        # There might be multiple cargo records for a given trade good. Condense it down to the
        # tonnage for each trade good. We loose the purchase prices from the original options but
        # they don't mater here.
        # Any exotics in imported cargo are dropped as selling them requires role playing
        ignoredExotics = False
        cargoQuantities = {}
        for cargoRecord in cargoRecords:
            tradeGood = cargoRecord.tradeGood()
            if tradeGood == exoticsTradeGood:
                ignoredExotics = True
                continue

            quantity = cargoRecord.quantity()
            quantity = quantity.averageCaseValue()
            if quantity <= 0:
                continue

            total = cargoQuantities.get(tradeGood, 0)
            cargoQuantities[tradeGood] = total + quantity

        self._cargoTable.removeAllRows()
        for tradeGood, quantity in cargoQuantities.items():
            self._cargoTable.addCargoRecord(logic.CargoRecord(
                tradeGood=tradeGood,
                pricePerTon=common.ScalarCalculation(
                    value=0,
                    name='Null Price Per Ton'),
                quantity=common.ScalarCalculation(
                    value=quantity,
                    name='Quantity')))

        if ignoredExotics:
            gui.MessageBoxEx.information(
                parent=self,
                text='Ignored exotic cargo when importing.\nSale of exotic cargo requires role playing so can\'t be automated')

    def _addCargo(self) -> None:
        rules = app.Config.instance().value(option=app.ConfigOption.Rules)

        # Don't list exotics. Calculating their sale price requires role playing rather than dice
        # rolling
        ignoreTradeGoods = [traveller.tradeGoodFromId(
            ruleSystem=rules.system(),
            tradeGoodId=traveller.TradeGoodIds.Exotics)]

        # Don't list trade goods that have already been added to the list
        for row in range(self._cargoTable.rowCount()):
            cargoRecord = self._cargoTable.cargoRecord(row)
            ignoreTradeGoods.append(cargoRecord.tradeGood())

        tradeGoods = traveller.tradeGoodList(
            ruleSystem=rules.system(),
            excludeTradeGoods=ignoreTradeGoods)

        if not tradeGoods:
            gui.MessageBoxEx.information(
                parent=self,
                text='All trade good types have been added already')
            return

        dlg = gui.TradeGoodQuantityDialog(
            parent=self,
            title='Add Sale Good',
            selectableTradeGoods=tradeGoods)
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return

        # Note that price per ton is 0 as we don't care about the purchase price of the sale good
        # for what we're doing.
        cargoRecord = logic.CargoRecord(
            tradeGood=dlg.tradeGood(),
            pricePerTon=common.ScalarCalculation(0),
            quantity=dlg.quantity())

        self._cargoTable.addCargoRecord(cargoRecord)

    def _editCargo(self) -> None:
        row = self._cargoTable.currentRow()
        if row < 0:
            gui.MessageBoxEx.information(
                parent=self,
                text='Select cargo to edit')
            return

        cargoRecord = self._cargoTable.cargoRecord(row)

        dlg = gui.TradeGoodQuantityDialog(
            parent=self,
            title='Edit Sale Good',
            editTradeGood=cargoRecord.tradeGood(),
            editQuantity=cargoRecord.quantity())
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return

        # Note that price per ton is 0 as we don't care about the purchase price of the sale good
        # for what we're doing.
        cargoRecord = logic.CargoRecord(
            tradeGood=dlg.tradeGood(),
            pricePerTon=common.ScalarCalculation(0),
            quantity=dlg.quantity())

        self._cargoTable.setCargoRecord(row, cargoRecord)

    def _clearCargo(self) -> None:
        self._cargoTable.removeAllRows()
        self._diceRollTable.removeAllRows()
        self._salePricesTable.removeAllRows()

    def _showCargoTableContextMenu(self, point: QtCore.QPoint) -> None:
        cargoRecord = self._cargoTable.cargoRecordAt(point.y())

        menuItems = [
            gui.MenuItem(
                text='Add Cargo...',
                callback=lambda: self._addCargo(),
                enabled=True
            ),
            gui.MenuItem(
                text='Edit Cargo...',
                callback=lambda: self._editCargo(),
                enabled=cargoRecord != None
            ),
            gui.MenuItem(
                text='Remove Selected Cargo',
                callback=lambda: self._cargoTable.removeSelectedRows(),
                enabled=self._cargoTable.hasSelection()
            ),
            gui.MenuItem(
                text='Remove All Cargo',
                callback=lambda: self._cargoTable.removeAllRows(),
                enabled=not self._cargoTable.isEmpty()
            )
        ]

        gui.displayMenu(
            self,
            menuItems,
            self._cargoTable.viewport().mapToGlobal(point))

    def _cargoTableKeyPressed(self, key: int) -> None:
        if key == QtCore.Qt.Key.Key_Delete:
            self._cargoTable.removeSelectedRows()

    def _generateSalePrices(self) -> None:
        saleWorld = self._saleWorldWidget.selectedWorld()
        if not saleWorld:
            return

        self._salePricesTable.removeAllRows()

        blackMarket = self._blackMarketCheckBox.isChecked()
        cargoRecords = []
        for cargoRecord in self._cargoTable.cargoRecords():
            tradeGood = cargoRecord.tradeGood()

            if tradeGood.id() != traveller.TradeGoodIds.Exotics:
                # Only generate prices for goods that match the selected legality
                isIllegal = tradeGood.isIllegal(world=saleWorld)
                if blackMarket == isIllegal:
                    cargoRecords.append(cargoRecord)
            else:
                # Exotics can be legal or illegal. The easiest way to handle this is to
                # always generate sale prices for them and let the user decide if it
                # makes sense in the game.
                cargoRecords.append(cargoRecord)

        if not cargoRecords:
            gui.MessageBoxEx.information(
                parent=self,
                text=f'You must have some {"illegal" if blackMarket else "legal"} cargo to deal with a {"black market" if blackMarket else "legal"} buyer')
            return

        diceRoller = common.DiceRoller(
            randomGenerator=self._randomGenerator)

        rules = app.Config.instance().value(option=app.ConfigOption.Rules)
        saleCargo, localBrokerIsInformant = logic.generateRandomSaleCargo(
            ruleSystem=rules.system(),
            world=saleWorld,
            currentCargo=cargoRecords,
            playerBrokerDm=self._playerBrokerDmSpinBox.value(),
            useLocalBroker=self._localBrokerSpinBox.isChecked(),
            localBrokerDm=self._localBrokerSpinBox.value(),
            buyerDm=self._buyerDmSpinBox.value(),
            blackMarket=blackMarket,
            diceRoller=diceRoller)

        priceScale = self._priceScaleSpinBox.value()
        if priceScale == 100:
            priceScale = None
        else:
            priceScale = common.ScalarCalculation(
                value=priceScale / 100,
                name='Custom Price Scale')

        for cargoRecord in saleCargo:
            if priceScale:
                pricePerTon = cargoRecord.pricePerTon()
                pricePerTon = common.Calculator.multiply(
                    lhs=pricePerTon,
                    rhs=priceScale,
                    name='Scaled Purchase Price')

                cargoRecord = logic.CargoRecord(
                    tradeGood=cargoRecord.tradeGood(),
                    pricePerTon=pricePerTon,
                    quantity=cargoRecord.quantity())

            self._salePricesTable.addCargoRecord(cargoRecord)

        self._updateTotalSalePrice()
        self._diceRollTable.setDiceRolls(diceRolls=diceRoller.rolls())

        if localBrokerIsInformant:
            gui.MessageBoxEx.information(
                parent=self,
                text=f'The local black market fixer that was hired is an informant')

    def _editSalePrice(self) -> None:
        saleWorld = self._saleWorldWidget.selectedWorld()
        if not saleWorld:
            return

        row = self._salePricesTable.currentRow()
        if row < 0:
            gui.MessageBoxEx.information(
                parent=self,
                text='Select a sale price to edit')
            return

        salePrice = self._salePricesTable.cargoRecord(row)

        saleCargo = None
        for cargoRecord in self._cargoTable.cargoRecords():
            if cargoRecord.tradeGood() == salePrice.tradeGood():
                saleCargo = cargoRecord
                break

        dlg = gui.ScalarCargoDetailsDialog(
            parent=self,
            title='Edit Sale Details',
            world=saleWorld,
            rules=app.Config.instance().value(option=app.ConfigOption.Rules),
            editTradeGood=salePrice.tradeGood(),
            editPricePerTon=salePrice.pricePerTon(),
            editQuantity=salePrice.quantity(),
            limitQuantity=saleCargo.quantity() if saleCargo else None)
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return

        salePrice = logic.CargoRecord(
            tradeGood=dlg.tradeGood(),
            pricePerTon=dlg.pricePerTon(),
            quantity=dlg.quantity())

        self._salePricesTable.setCargoRecord(row, salePrice)
        self._updateTotalSalePrice()

    def _removeSelectedSalePrices(self) -> None:
        self._salePricesTable.removeSelectedRows()
        self._updateTotalSalePrice()

    def _removeAllSalePrices(self) -> None:
        self._salePricesTable.removeAllRows()
        self._updateTotalSalePrice()

    def _showSalePricesTableContextMenu(self, point: QtCore.QPoint) -> None:
        salePrice = self._salePricesTable.cargoRecordAt(point.y())

        menuItems = [
            gui.MenuItem(
                text='Edit Sale Price...',
                callback=self._editSalePrice,
                enabled=salePrice != None
            ),
            gui.MenuItem(
                text='Remove Selected Sale Prices',
                callback=self._removeSelectedSalePrices,
                enabled=self._salePricesTable.hasSelection()
            ),
            gui.MenuItem(
                text='Remove All Sale Prices',
                callback=self._removeAllSalePrices,
                enabled=not self._salePricesTable.isEmpty()
            ),
            None, # Separator
            gui.MenuItem(
                text='Show Calculations...',
                callback=lambda: self._showCalculations(salePrice),
                enabled=salePrice != None
            )
        ]

        gui.displayMenu(
            self,
            menuItems,
            self._salePricesTable.viewport().mapToGlobal(point))

    def _salePricesTableKeyPressed(self, key: int) -> None:
        if key == QtCore.Qt.Key.Key_Delete:
            self._removeAllSalePrices()

    def _showWelcomeMessage(self) -> None:
        message = gui.InfoDialog(
            parent=self,
            title=self.windowTitle(),
            html=_WelcomeMessage,
            noShowAgainId='SaleCalculatorWelcome')
        message.exec()
