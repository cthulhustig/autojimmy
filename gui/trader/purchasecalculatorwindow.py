import app
import common
import gui
import logging
import logic
import traveller
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

# TODO: I need to add a vertical splitter or something as the new world select control
# is drawn way to small
class PurchaseCalculatorWindow(gui.WindowWidget):
    def __init__(self) -> None:
        super().__init__(
            title='Purchase Calculator',
            configSection='PurchaseCalculatorWindow')

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

        windowLayout = QtWidgets.QHBoxLayout()
        windowLayout.addLayout(leftLayout, 0)
        windowLayout.addWidget(self._resultsSplitter, 1)

        self.setLayout(windowLayout)

    def firstShowEvent(self, e: QtGui.QShowEvent) -> None:
        QtCore.QTimer.singleShot(0, self._showWelcomeMessage)
        return super().firstShowEvent(e)

    def _setupWorldSelectControls(self) -> None:
        self._purchaseWorldWidget = gui.WorldSelectWidget()
        self._purchaseWorldWidget.enableMapSelectButton(True)
        self._purchaseWorldWidget.enableShowInfoButton(True)
        self._purchaseWorldWidget.selectionChanged.connect(self._purchaseWorldChanged)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self._purchaseWorldWidget)

        self._worldGroupBox = QtWidgets.QGroupBox('Purchase World')
        self._worldGroupBox.setLayout(layout)

    def _setupConfigurationControls(self) -> None:
        self._playerBrokerDmSpinBox = gui.SpinBoxEx()
        self._playerBrokerDmSpinBox.setRange(app.MinPossibleDm, app.MaxPossibleDm)
        self._playerBrokerDmSpinBox.setValue(1)
        self._playerBrokerDmSpinBox.setToolTip(gui.PlayerBrokerDmToolTip)

        self._localBrokerWidget = gui.LocalBrokerWidget()

        self._sellerDmSpinBox = gui.SpinBoxEx()
        self._sellerDmSpinBox.setRange(app.MinPossibleDm, app.MaxPossibleDm)
        self._sellerDmSpinBox.setValue(2) # Default for MGT 2022 so just use as default for everything
        self._sellerDmSpinBox.setToolTip(gui.createStringToolTip('Seller\'s DM bonus'))

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
        layout.addRow('Local Purchase Broker:', self._localBrokerWidget)
        layout.addRow('Seller DM:', self._sellerDmSpinBox)
        layout.addRow('Black Market Seller:', self._blackMarketCheckBox)
        layout.addRow('Price Scale (%):', self._priceScaleSpinBox)
        layout.addRow('Availability Scale (%):', self._availabilityScaleSpinBox)

        self._configurationGroupBox = QtWidgets.QGroupBox('Configuration')
        self._configurationGroupBox.setDisabled(True)
        self._configurationGroupBox.setLayout(layout)

    def _setupAvailableCargoControls(self) -> None:
        self._generateButton = QtWidgets.QPushButton('Generate Available Cargo')
        self._generateButton.clicked.connect(self._generateAvailableCargo)

        self._cargoTable = gui.CargoRecordTable(
            columns=gui.CargoRecordTable.KnownValueColumns)
        self._cargoTable.setMinimumHeight(200)
        self._cargoTable.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self._cargoTable.customContextMenuRequested.connect(self._showCargoTableContextMenu)
        self._cargoTable.keyPressed.connect(self._cargoTableKeyPressed)
        self._cargoTable.doubleClicked.connect(self._editCargo)

        self._exportButton = QtWidgets.QPushButton('Export...')
        self._exportButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)
        self._exportButton.clicked.connect(self._exportCargo)

        self._addButton = QtWidgets.QPushButton('Add...')
        self._addButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)
        self._addButton.clicked.connect(self._addCargo)

        self._editButton = QtWidgets.QPushButton('Edit...')
        self._editButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)
        self._editButton.clicked.connect(self._editCargo)

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
            self._localBrokerWidget.restoreState(storedValue)

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
            key='DiceRollTableContent',
            type=QtCore.QByteArray)
        if storedValue:
            self._diceRollTable.restoreContent(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='ResultsSplitterState',
            type=QtCore.QByteArray)
        if storedValue:
            self._resultsSplitter.restoreState(storedValue)

        self._settings.endGroup()

    def saveSettings(self) -> None:
        self._settings.beginGroup(self._configSection)

        self._settings.setValue('PurchaseWorldState', self._purchaseWorldWidget.saveState())
        self._settings.setValue('PlayerBrokerDMState', self._playerBrokerDmSpinBox.saveState())
        self._settings.setValue('LocalBrokerState', self._localBrokerWidget.saveState())
        self._settings.setValue('SellerDmState', self._sellerDmSpinBox.saveState())
        self._settings.setValue('PriceScaleState', self._priceScaleSpinBox.saveState())
        self._settings.setValue('AvailabilityScaleState', self._availabilityScaleSpinBox.saveState())
        self._settings.setValue('BlackMarketState', self._blackMarketCheckBox.saveState())
        self._settings.setValue('CargoTableState', self._cargoTable.saveState())
        self._settings.setValue('CargoTableContent', self._cargoTable.saveContent())
        self._settings.setValue('DiceRollTableState', self._diceRollTable.saveState())
        self._settings.setValue('DiceRollTableContent', self._diceRollTable.saveContent())
        self._settings.setValue('ResultsSplitterState', self._resultsSplitter.saveState())

        self._settings.endGroup()

        super().saveSettings()

    def _purchaseWorldChanged(self) -> None:
        disable = not self._purchaseWorldWidget.hasSelection()
        self._configurationGroupBox.setDisabled(disable)
        self._cargoGroupBox.setDisabled(disable)
        self._diceRollGroupBox.setDisabled(disable)

    def _generateAvailableCargo(self) -> None:
        self._cargoTable.removeAllRows()

        diceRoller = common.DiceRoller()

        cargoRecords, localBrokerIsInformant = logic.generateRandomPurchaseCargo(
            rules=app.Config.instance().rules(),
            world=self._purchaseWorldWidget.world(),
            playerBrokerDm=self._playerBrokerDmSpinBox.value(),
            useLocalBroker=self._localBrokerWidget.isChecked(),
            localBrokerDm=self._localBrokerWidget.value(),
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

    def _addCargo(self) -> None:
        # Ignore trade goods that have already been added from the list
        ignoreTradeGoods = []
        for row in range(self._cargoTable.rowCount()):
            cargoRecord = self._cargoTable.cargoRecord(row)
            ignoreTradeGoods.append(cargoRecord.tradeGood())

        tradeGoods = traveller.tradeGoodList(
            rules=app.Config.instance().rules(),
            excludeTradeGoods=ignoreTradeGoods)

        if not tradeGoods:
            gui.MessageBoxEx.information(
                parent=self,
                text='All trade good types have been added already')
            return

        dlg = gui.ScalarCargoDetailsDialog(
            parent=self,
            title='Add Available Cargo',
            world=self._purchaseWorldWidget.world(),
            selectableTradeGoods=tradeGoods)
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return

        self._cargoTable.addCargoRecord(
            cargoRecord=logic.CargoRecord(
                tradeGood=dlg.tradeGood(),
                pricePerTon=dlg.pricePerTon(),
                quantity=dlg.quantity()))

    def _editCargo(self) -> None:
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
            world=self._purchaseWorldWidget.world(),
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
        try:
            traderWindow = gui.WindowManager.instance().showWorldTradeOptionsWindow()
            traderWindow.configureControls(
                purchaseWorld=self._purchaseWorldWidget.world(),
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

    def _showCargoTableContextMenu(self, position: QtCore.QPoint) -> None:
        cargoRecord = self._cargoTable.cargoRecordAt(position)

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
            ),
            None, # Separator
            gui.MenuItem(
                text='Find Trade Options for Selected Cargo...',
                callback=lambda: self._findTradeOptionsForCargo(self._cargoTable.selectedCargoRecords()),
                enabled=self._cargoTable.hasSelection()
            ),
            gui.MenuItem(
                text='Find Trade Options for All Cargo...',
                callback=lambda: self._findTradeOptionsForCargo(self._cargoTable.cargoRecords()),
                enabled=not self._cargoTable.isEmpty()
            ),
            None, # Separator
            gui.MenuItem(
                text='Show Calculations...',
                callback=lambda: self._showCalculations(cargoRecord),
                enabled=cargoRecord != None
            )
        ]

        gui.displayMenu(
            self,
            menuItems,
            self._cargoTable.viewport().mapToGlobal(position)
        )

    def _cargoTableKeyPressed(self, key: int) -> None:
        if key == QtCore.Qt.Key.Key_Delete:
            self._cargoTable.removeSelectedRows()

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
