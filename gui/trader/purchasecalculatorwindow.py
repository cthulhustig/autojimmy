import app
import common
import gui
import logging
import logic
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

_WelcomeMessage = """
    <html>
    <p>The Purchase Calculator is a tool for Referees to use when a player is purchasing trade goods
    on a given world. It rolls virtual dice to generate the list of goods the seller has available
    along with quantities and prices for each of them.<p>
    <p>Currently, only Mongoose 1e & 2e rules are supported. Which rules are used can be selected in
    the Configuration dialog. Data from Traveller Map is used to calculate trade good which trade
    goods area available and the Sale DMs for said trade goods.</p>
    </html>
"""

class PurchaseCalculatorWindow(gui.WindowWidget):
    def __init__(self) -> None:
        super().__init__(
            title='Purchase Calculator',
            configSection='PurchaseCalculatorWindow')

        self._randomGenerator = common.RandomGenerator()

        self._hexTooltipProvider = gui.HexTooltipProvider(
            milieu=app.Config.instance().value(option=app.ConfigOption.Milieu),
            rules=app.Config.instance().value(option=app.ConfigOption.Rules),
            mapStyle=app.Config.instance().value(option=app.ConfigOption.MapStyle),
            mapOptions=app.Config.instance().value(option=app.ConfigOption.MapOptions),
            worldTagging=app.Config.instance().value(option=app.ConfigOption.WorldTagging),
            taggingColours=app.Config.instance().value(option=app.ConfigOption.TaggingColours))

        self._setupWorldSelectControls()
        self._setupConfigurationControls()
        self._setupAvailableCargoControls()
        self._setupDiceRollControls()

        leftLayout = QtWidgets.QVBoxLayout()
        leftLayout.setContentsMargins(0, 0, 0, 0)
        leftLayout.addWidget(self._worldGroupBox)
        leftLayout.addWidget(self._configurationGroupBox)
        leftLayout.addStretch()

        self._resultsSplitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        self._resultsSplitter.addWidget(self._cargoGroupBox)
        self._resultsSplitter.addWidget(self._diceRollGroupBox)

        self._horizontalSplitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self._horizontalSplitter.addWidget(gui.LayoutWrapperWidget(layout=leftLayout))
        self._horizontalSplitter.addWidget(self._resultsSplitter)

        windowLayout = QtWidgets.QHBoxLayout()
        windowLayout.addWidget(self._horizontalSplitter)

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
            key='PurchaseWorldState',
            type=QtCore.QByteArray)
        if storedValue:
            self._purchaseWorldWidget.restoreState(storedValue)

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
            key='SellerDmState',
            type=QtCore.QByteArray)
        if storedValue:
            self._sellerDmSpinBox.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='PriceScaleState',
            type=QtCore.QByteArray)
        if storedValue:
            self._priceScaleSpinBox.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='AvailabilityScaleState',
            type=QtCore.QByteArray)
        if storedValue:
            self._availabilityScaleSpinBox.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='BlackMarketState',
            type=QtCore.QByteArray)
        if storedValue:
            self._blackMarketCheckBox.restoreState(storedValue)

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
            key='HorizontalSplitterState',
            type=QtCore.QByteArray)
        if storedValue:
            self._horizontalSplitter.restoreState(storedValue)

        self._settings.endGroup()

    def saveSettings(self) -> None:
        self._settings.beginGroup(self._configSection)

        self._settings.setValue('PurchaseWorldState', self._purchaseWorldWidget.saveState())
        self._settings.setValue('PlayerBrokerDMState', self._playerBrokerDmSpinBox.saveState())
        self._settings.setValue('LocalBrokerState', self._localBrokerSpinBox.saveState())
        self._settings.setValue('SellerDmState', self._sellerDmSpinBox.saveState())
        self._settings.setValue('PriceScaleState', self._priceScaleSpinBox.saveState())
        self._settings.setValue('AvailabilityScaleState', self._availabilityScaleSpinBox.saveState())
        self._settings.setValue('BlackMarketState', self._blackMarketCheckBox.saveState())
        self._settings.setValue('CargoTableState', self._cargoTable.saveState())
        self._settings.setValue('DiceRollTableState', self._diceRollTable.saveState())
        self._settings.setValue('ResultsSplitterState', self._resultsSplitter.saveState())
        self._settings.setValue('HorizontalSplitterState', self._horizontalSplitter.saveState())

        self._settings.endGroup()

        super().saveSettings()

    def eventFilter(self, object: object, event: QtCore.QEvent) -> bool:
        if object == self._cargoTable:
            if event.type() == QtCore.QEvent.Type.KeyPress:
                assert(isinstance(event, QtGui.QKeyEvent))
                if event.key() == QtCore.Qt.Key.Key_Delete:
                    self._cargoTable.removeSelectedRows()
                    event.accept()
                    return True

        return super().eventFilter(object, event)

    def _setupWorldSelectControls(self) -> None:
        milieu = app.Config.instance().value(option=app.ConfigOption.Milieu)
        rules = app.Config.instance().value(option=app.ConfigOption.Rules)
        mapStyle = app.Config.instance().value(option=app.ConfigOption.MapStyle)
        mapOptions = app.Config.instance().value(option=app.ConfigOption.MapOptions)
        mapRendering = app.Config.instance().value(option=app.ConfigOption.MapRendering)
        mapAnimations = app.Config.instance().value(option=app.ConfigOption.MapAnimations)
        worldTagging = app.Config.instance().value(option=app.ConfigOption.WorldTagging)
        taggingColours = app.Config.instance().value(option=app.ConfigOption.TaggingColours)

        self._purchaseWorldWidget = gui.HexSelectToolWidget(
            milieu=milieu,
            rules=rules,
            mapStyle=mapStyle,
            mapOptions=mapOptions,
            mapRendering=mapRendering,
            mapAnimations=mapAnimations,
            worldTagging=worldTagging,
            taggingColours=taggingColours,
            labelText='Select World:')
        self._purchaseWorldWidget.setHexTooltipProvider(
            provider=self._hexTooltipProvider)
        self._purchaseWorldWidget.enableMapSelectButton(True)
        self._purchaseWorldWidget.enableShowInfoButton(True)
        self._purchaseWorldWidget.selectionChanged.connect(self._purchaseWorldChanged)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self._purchaseWorldWidget)

        self._worldGroupBox = QtWidgets.QGroupBox('Purchase World')
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

        self._sellerDmSpinBox = gui.SkillSpinBox(
            value=2, # Default for MGT 2022 so just use as default for everything
            toolTip=gui.createStringToolTip('Seller\'s DM bonus'))

        self._blackMarketCheckBox = gui.CheckBoxEx()

        self._priceScaleSpinBox = gui.SpinBoxEx()
        self._priceScaleSpinBox.setRange(1, 1000)
        self._priceScaleSpinBox.setValue(100)
        self._priceScaleSpinBox.setToolTip(gui.createStringToolTip(
            '<p>Purchase price scale percentage</p>' \
            '<p>This allows GMs to increase/decrease the standard purchase price of all trade goods on a world for whatever in game reasons they see fit</p>',
            escape=False))

        self._availabilityScaleSpinBox = gui.SpinBoxEx()
        self._availabilityScaleSpinBox.setRange(1, 1000)
        self._availabilityScaleSpinBox.setValue(100)
        self._availabilityScaleSpinBox.setToolTip(gui.createStringToolTip(
            '<p>Availability scale percentage</p>' \
            '<p>This allows GMs to increase/decrease the standard availability of all trade goods on a world for whatever in game reasons they see fit</p>',
            escape=False))

        layout = gui.FormLayoutEx()
        layout.addRow('Player\'s broker DM:', self._playerBrokerDmSpinBox)
        layout.addRow('Local Purchase Broker:', self._localBrokerSpinBox)
        layout.addRow('Seller DM:', self._sellerDmSpinBox)
        layout.addRow('Black Market Seller:', self._blackMarketCheckBox)
        layout.addRow('Price Scale (%):', self._priceScaleSpinBox)
        layout.addRow('Availability Scale (%):', self._availabilityScaleSpinBox)

        self._configurationGroupBox = QtWidgets.QGroupBox('Configuration')
        self._configurationGroupBox.setDisabled(True)
        self._configurationGroupBox.setLayout(layout)

    def _setupAvailableCargoControls(self) -> None:
        outcomeColours = app.Config.instance().value(
            option=app.ConfigOption.OutcomeColours)

        self._generateButton = QtWidgets.QPushButton('Generate Available Cargo')
        self._generateButton.clicked.connect(self._generateAvailableCargo)

        self._cargoTable = gui.CargoRecordTable(
            outcomeColours=outcomeColours,
            columns=gui.CargoRecordTable.KnownValueColumns)
        self._cargoTable.setMinimumHeight(200)
        self._cargoTable.installEventFilter(self)
        self._cargoTable.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self._cargoTable.customContextMenuRequested.connect(self._showCargoTableContextMenu)
        self._cargoTable.doubleClicked.connect(self._promptEditCargo)

        self._exportButton = QtWidgets.QPushButton('Export...')
        self._exportButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)
        self._exportButton.clicked.connect(self._exportCargo)

        self._addButton = QtWidgets.QPushButton('Add...')
        self._addButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)
        self._addButton.clicked.connect(self._promptAddCargo)

        self._editButton = QtWidgets.QPushButton('Edit...')
        self._editButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)
        self._editButton.clicked.connect(self._promptEditCargo)

        self._removeButton = QtWidgets.QPushButton('Remove')
        self._removeButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)
        self._removeButton.clicked.connect(self._cargoTable.removeSelectedRows)

        self._removeAllButton = QtWidgets.QPushButton('Remove All')
        self._removeAllButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)
        self._removeAllButton.clicked.connect(self._cargoTable.removeAllRows)

        buttonLayout = QtWidgets.QHBoxLayout()
        buttonLayout.setContentsMargins(0, 0, 0, 0)
        buttonLayout.addWidget(self._exportButton)
        buttonLayout.addStretch()
        buttonLayout.addWidget(self._addButton)
        buttonLayout.addWidget(self._editButton)
        buttonLayout.addWidget(self._removeButton)
        buttonLayout.addWidget(self._removeAllButton)

        mainLayout = QtWidgets.QVBoxLayout()
        mainLayout.addWidget(self._generateButton)
        mainLayout.addWidget(self._cargoTable)
        mainLayout.addLayout(buttonLayout)

        self._cargoGroupBox = QtWidgets.QGroupBox('Available Cargo')
        self._cargoGroupBox.setDisabled(True)
        self._cargoGroupBox.setLayout(mainLayout)

    def _setupDiceRollControls(self) -> None:
        self._diceRollTable = gui.DiceRollTable()

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self._diceRollTable)

        self._diceRollGroupBox = QtWidgets.QGroupBox('Dice Rolls')
        self._diceRollGroupBox.setDisabled(True)
        self._diceRollGroupBox.setLayout(layout)

    def _appConfigChanged(
            self,
            option: app.ConfigOption,
            oldValue: typing.Any,
            newValue: typing.Any
            ) -> None:
        if option is app.ConfigOption.Milieu:
            self._hexTooltipProvider.setMilieu(milieu=newValue)
            self._purchaseWorldWidget.setMilieu(milieu=newValue)
        elif option is app.ConfigOption.Rules:
            self._hexTooltipProvider.setRules(rules=newValue)
            self._purchaseWorldWidget.setRules(rules=newValue)
            self._localBrokerSpinBox.setRules(rules=newValue)
        elif option is app.ConfigOption.MapStyle:
            self._hexTooltipProvider.setMapStyle(style=newValue)
            self._purchaseWorldWidget.setMapStyle(style=newValue)
        elif option is app.ConfigOption.MapOptions:
            self._hexTooltipProvider.setMapOptions(options=newValue)
            self._purchaseWorldWidget.setMapOptions(options=newValue)
        elif option is app.ConfigOption.MapRendering:
            self._purchaseWorldWidget.setMapRendering(rendering=newValue)
        elif option is app.ConfigOption.MapAnimations:
            self._purchaseWorldWidget.setMapAnimations(enabled=newValue)
        elif option is app.ConfigOption.OutcomeColours:
            self._cargoTable.setOutcomeColours(colours=newValue)
        elif option is app.ConfigOption.WorldTagging:
            self._hexTooltipProvider.setWorldTagging(tagging=newValue)
            self._purchaseWorldWidget.setWorldTagging(tagging=newValue)
        elif option is app.ConfigOption.TaggingColours:
            self._hexTooltipProvider.setTaggingColours(colours=newValue)
            self._purchaseWorldWidget.setTaggingColours(colours=newValue)

    def _purchaseWorldChanged(self) -> None:
        disable = not self._purchaseWorldWidget.selectedWorld()
        self._configurationGroupBox.setDisabled(disable)
        self._cargoGroupBox.setDisabled(disable)
        self._diceRollGroupBox.setDisabled(disable)

    def _generateAvailableCargo(self) -> None:
        purchaseWorld = self._purchaseWorldWidget.selectedWorld()
        if not purchaseWorld:
            return

        self._cargoTable.removeAllRows()

        diceRoller = common.DiceRoller(
            randomGenerator=self._randomGenerator)

        rules = app.Config.instance().value(option=app.ConfigOption.Rules)
        cargoRecords, localBrokerIsInformant = logic.generateRandomPurchaseCargo(
            rules=rules,
            world=purchaseWorld,
            playerBrokerDm=self._playerBrokerDmSpinBox.value(),
            useLocalBroker=self._localBrokerSpinBox.isChecked(),
            localBrokerDm=self._localBrokerSpinBox.value(),
            sellerDm=self._sellerDmSpinBox.value(),
            blackMarket=self._blackMarketCheckBox.isChecked(),
            diceRoller=diceRoller)

        priceScale = self._priceScaleSpinBox.value()
        if priceScale == 100:
            priceScale = None
        else:
            priceScale = common.ScalarCalculation(
                value=priceScale / 100,
                name='Custom Price Scale')

        availabilityScale = self._availabilityScaleSpinBox.value()
        if availabilityScale == 100:
            availabilityScale = None
        else:
            availabilityScale = common.ScalarCalculation(
                value=availabilityScale / 100,
                name='Custom Availability Scale')

        for cargoRecord in cargoRecords:
            if priceScale or availabilityScale:
                pricePerTon = cargoRecord.pricePerTon()
                if priceScale:
                    pricePerTon = common.Calculator.multiply(
                        lhs=pricePerTon,
                        rhs=priceScale,
                        name='Scaled Purchase Price')

                availability = cargoRecord.quantity()
                if availabilityScale:
                    # Round down to be pessimistic
                    availability = common.Calculator.floor(
                        value=common.Calculator.multiply(
                            lhs=availability,
                            rhs=availabilityScale),
                        name='Scaled Availability')

                cargoRecord = logic.CargoRecord(
                    tradeGood=cargoRecord.tradeGood(),
                    pricePerTon=pricePerTon,
                    quantity=availability)

            self._cargoTable.addCargoRecord(cargoRecord)

        self._diceRollTable.setDiceRolls(diceRolls=diceRoller.rolls())

        if localBrokerIsInformant:
            gui.MessageBoxEx.information(
                parent=self,
                text=f'The local black market fixer that was hired is an informant')

        if not cargoRecords:
            gui.MessageBoxEx.information(
                parent=self,
                text=f'The seller has no goods available at this time.\nThis can happen due to world specific modifiers (e.g. for low population worlds).')

    def _promptAddCargo(self) -> None:
        purchaseWorld = self._purchaseWorldWidget.selectedWorld()
        if not purchaseWorld:
            return

        # Ignore trade goods that have already been added from the list
        ignoreTradeGoods = []
        for row in range(self._cargoTable.rowCount()):
            cargoRecord = self._cargoTable.cargoRecord(row)
            ignoreTradeGoods.append(cargoRecord.tradeGood())

        rules = app.Config.instance().value(option=app.ConfigOption.Rules)
        tradeGoods = logic.tradeGoodList(
            ruleSystem=rules.system(),
            excludeTradeGoods=ignoreTradeGoods)

        if not tradeGoods:
            gui.MessageBoxEx.information(
                parent=self,
                text='All trade good types have been added already')
            return

        dlg = gui.ScalarCargoDetailsDialog(
            parent=self,
            title='Add Available Cargo',
            world=purchaseWorld,
            rules=rules,
            selectableTradeGoods=tradeGoods)
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return

        self._cargoTable.addCargoRecord(
            cargoRecord=logic.CargoRecord(
                tradeGood=dlg.tradeGood(),
                pricePerTon=dlg.pricePerTon(),
                quantity=dlg.quantity()))

    def _promptEditCargo(self) -> None:
        purchaseWorld = self._purchaseWorldWidget.selectedWorld()
        if not purchaseWorld:
            return

        row = self._cargoTable.currentRow()
        if row < 0:
            gui.MessageBoxEx.information(
                parent=self,
                text='Select cargo to edit')
            return

        cargoRecord = self._cargoTable.cargoRecord(row)

        dlg = gui.ScalarCargoDetailsDialog(
            parent=self,
            title='Edit Available Cargo',
            world=purchaseWorld,
            rules=app.Config.instance().value(option=app.ConfigOption.Rules),
            editTradeGood=cargoRecord.tradeGood(),
            editPricePerTon=cargoRecord.pricePerTon(),
            editQuantity=cargoRecord.quantity())
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return

        cargoRecord = logic.CargoRecord(
            tradeGood=dlg.tradeGood(),
            pricePerTon=dlg.pricePerTon(),
            quantity=dlg.quantity())

        self._cargoTable.setCargoRecord(row, cargoRecord)

    def _findTradeOptionsForCargo(
            self,
            cargoRecords: typing.Iterable[logic.CargoRecord]
            ) -> None:
        purchaseWorld = self._purchaseWorldWidget.selectedWorld()
        if not purchaseWorld:
            return

        try:
            traderWindow = gui.WindowManager.instance().showWorldTradeOptionsWindow()
            traderWindow.configureControls(
                purchaseWorld=purchaseWorld,
                availableCargo=cargoRecords,
                playerBrokerDm=self._playerBrokerDmSpinBox.value(),
                minSellerDm=self._sellerDmSpinBox.value(),
                maxSellerDm=self._sellerDmSpinBox.value())
        except Exception as ex:
            message = 'Failed to show trade options window'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)

    def _exportCargo(self) -> None:
        if self._cargoTable.isEmpty():
            gui.MessageBoxEx.information(
                parent=self,
                text='No cargo to export')
            return

        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            'Save File',
            QtCore.QDir.homePath() + '/cargo.json',
            'JSON (*.json)')
        if not path:
            return

        try:
            logic.writeCargoRecordList(
                self._cargoTable.cargoRecords(),
                path)
        except Exception as ex:
            message = f'Failed to write cargo to "{path}"'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)

    def _clearCargo(self) -> None:
        self._cargoTable.removeAllRows()
        self._diceRollTable.removeAllRows()

    def _showCargoTableContextMenu(self, point: QtCore.QPoint) -> None:
        hasContent = not self._cargoTable.isEmpty()
        hasSelection = self._cargoTable.hasSelection()
        hasSingleSelection = len(self._cargoTable.selectedRows()) == 1

        addCargoAction = QtWidgets.QAction('Add...', self)
        addCargoAction.triggered.connect(self._promptAddCargo)

        editCargoAction = QtWidgets.QAction('Edit...', self)
        editCargoAction.setEnabled(hasSingleSelection)
        editCargoAction.triggered.connect(self._promptEditCargo)

        removeSelectedCargoAction = QtWidgets.QAction('Remove', self)
        removeSelectedCargoAction.setEnabled(hasSelection)
        removeSelectedCargoAction.triggered.connect(self._cargoTable.removeSelectedRows)

        removeAllCargoAction = QtWidgets.QAction('Remove All', self)
        removeAllCargoAction.setEnabled(hasContent)
        removeAllCargoAction.triggered.connect(self._cargoTable.removeAllRows)

        findTradeOptionsForSelectedCargoAction = QtWidgets.QAction(
            'Find Trade Options...',
            self)
        findTradeOptionsForSelectedCargoAction.setEnabled(hasSelection)
        findTradeOptionsForSelectedCargoAction.triggered.connect(
            lambda: self._findTradeOptionsForCargo(self._cargoTable.selectedCargoRecords()))

        findTradeOptionsForAllCargoAction = QtWidgets.QAction(
            'Find Trade Options for All...',
            self)
        findTradeOptionsForAllCargoAction.setEnabled(hasContent)
        findTradeOptionsForAllCargoAction.triggered.connect(
            lambda: self._findTradeOptionsForCargo(self._cargoTable.cargoRecords()))

        menu = QtWidgets.QMenu()
        menu.addAction(addCargoAction)
        menu.addAction(editCargoAction)
        menu.addSeparator()
        menu.addAction(removeSelectedCargoAction)
        menu.addAction(removeAllCargoAction)
        menu.addSeparator()
        menu.addAction(findTradeOptionsForSelectedCargoAction)
        menu.addAction(findTradeOptionsForAllCargoAction)
        menu.addSeparator()
        self._cargoTable.fillContextMenu(menu)
        menu.exec(self._cargoTable.viewport().mapToGlobal(point))

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

    def _showWelcomeMessage(self) -> None:
        message = gui.InfoDialog(
            parent=self,
            title=self.windowTitle(),
            html=_WelcomeMessage,
            noShowAgainId='PurchaseCalculatorWelcome')
        message.exec()
