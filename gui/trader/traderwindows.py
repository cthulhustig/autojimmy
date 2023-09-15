import app
import common
import gui
import jobs
import logging
import logic
import traveller
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

def _worldSaleScoreTableColumns(
        originalColumns: typing.List[gui.WorldTable.ColumnType]
        ) -> typing.List[typing.Union[gui.WorldTradeScoreTableColumnType, gui.WorldTable.ColumnType]]:
    columns = originalColumns.copy()
    if gui.WorldTradeScoreTableColumnType.PurchaseScore in columns:
        columns.remove(gui.WorldTradeScoreTableColumnType.PurchaseScore)
    return columns

class _WorldSaleScoreTable(gui.WorldTradeScoreTable):
    AllColumns = _worldSaleScoreTableColumns(gui.WorldTradeScoreTable.AllColumns)
    SystemColumns = _worldSaleScoreTableColumns(gui.WorldTradeScoreTable.SystemColumns)
    UWPColumns = _worldSaleScoreTableColumns(gui.WorldTradeScoreTable.UWPColumns)
    EconomicsColumns = _worldSaleScoreTableColumns(gui.WorldTradeScoreTable.EconomicsColumns)
    CultureColumns = _worldSaleScoreTableColumns(gui.WorldTradeScoreTable.CultureColumns)
    RefuellingColumns = _worldSaleScoreTableColumns(gui.WorldTradeScoreTable.RefuellingColumns)

    def __init__(
            self,
            columns: typing.Iterable[typing.Union[gui.WorldTradeScoreTableColumnType, gui.WorldTable.ColumnType]] = AllColumns) -> None:
        super().__init__(columns)


# ███████████                                ███████████                         █████
#░░███░░░░░███                              ░█░░░███░░░█                        ░░███
# ░███    ░███  ██████    █████   ██████    ░   ░███  ░  ████████   ██████    ███████   ██████  ████████
# ░██████████  ░░░░░███  ███░░   ███░░███       ░███    ░░███░░███ ░░░░░███  ███░░███  ███░░███░░███░░███
# ░███░░░░░███  ███████ ░░█████ ░███████        ░███     ░███ ░░░   ███████ ░███ ░███ ░███████  ░███ ░░░
# ░███    ░███ ███░░███  ░░░░███░███░░░         ░███     ░███      ███░░███ ░███ ░███ ░███░░░   ░███
# ███████████ ░░████████ ██████ ░░██████        █████    █████    ░░████████░░████████░░██████  █████
#░░░░░░░░░░░   ░░░░░░░░ ░░░░░░   ░░░░░░        ░░░░░    ░░░░░      ░░░░░░░░  ░░░░░░░░  ░░░░░░  ░░░░░

class _BaseTraderWindow(gui.WindowWidget):
    def __init__(
            self,
            title: str,
            configSection: str
            ) -> None:
        super().__init__(title=title, configSection=configSection)
        self._traderJob = None

    def loadSettings(self) -> None:
        super().loadSettings()

        self._settings.beginGroup(self._configSection)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='TradeOptionCalculationModeState',
            type=QtCore.QByteArray)
        if storedValue:
            self._tradeOptionCalculationModeTabs.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='TradeOptionTableState',
            type=QtCore.QByteArray)
        if storedValue:
            self._tradeOptionsTable.restoreState(storedValue)

        self._settings.endGroup()

    def saveSettings(self) -> None:
        self._settings.beginGroup(self._configSection)

        self._settings.setValue('TradeOptionCalculationModeState', self._tradeOptionCalculationModeTabs.saveState())
        self._settings.setValue('TradeOptionTableState', self._tradeOptionsTable.saveState())

        self._settings.endGroup()

        super().saveSettings()

    def firstShowEvent(self, e: QtGui.QShowEvent) -> None:
        QtCore.QTimer.singleShot(0, self._showWelcomeMessage)
        super().firstShowEvent(e)

    def closeEvent(self, e: QtGui.QCloseEvent):
        if self._traderJob:
            self._traderJob.cancel(block=True)
            self._traderJob = None
        return super().closeEvent(e)

    def _setupConfigurationControls(self) -> None:
        # Left column of controls
        self._availableFundsSpinBox = gui.SharedAvailableFundsSpinBox()

        self._playerBrokerDmSpinBox = gui.SharedPlayerBrokerDMSpinBox()
        self._playerBrokerDmSpinBox.valueChanged.connect(self._playerBrokerDmChanged)

        self._sellerDmRangeWidget = gui.SharedSellerDMRangeWidget()
        self._sellerDmRangeWidget.rangeChanged.connect(self._sellerDmChanged)

        self._buyerDmRangeWidget = gui.SharedBuyerDMRangeWidget()
        self._buyerDmRangeWidget.rangeChanged.connect(self._buyerDmChanged)

        self._localPurchaseBrokerWidget = gui.SharedLocalPurchaseBrokerSpinBox()
        self._localPurchaseBrokerWidget.valueChanged.connect(self._localPurchaseBrokerDmChanged)

        self._localSaleBrokerWidget = gui.SharedLocalSaleBrokerSpinBox()
        self._localSaleBrokerWidget.valueChanged.connect(self._localSaleBrokerDmChanged)

        self._leftOptionsLayout = gui.FormLayoutEx()
        self._leftOptionsLayout.setContentsMargins(0, 0, 0, 0)
        self._leftOptionsLayout.addRow('Available Funds:', self._availableFundsSpinBox)
        self._leftOptionsLayout.addRow('Player\'s Broker DM:', self._playerBrokerDmSpinBox)
        self._leftOptionsLayout.addRow('Seller DM Range:', self._sellerDmRangeWidget)
        self._leftOptionsLayout.addRow('Buyer DM Range:', self._buyerDmRangeWidget)
        self._leftOptionsLayout.addRow('Local Purchase Broker:', self._localPurchaseBrokerWidget)
        self._leftOptionsLayout.addRow('Local Sale Broker:', self._localSaleBrokerWidget)

        # Center column of controls
        self._shipTonnageSpinBox = gui.SharedShipTonnageSpinBox()
        self._shipJumpRatingSpinBox = gui.SharedJumpRatingSpinBox()
        self._shipFuelCapacitySpinBox = gui.SharedFuelCapacitySpinBox()
        self._shipCurrentFuelSpinBox = gui.SharedCurrentFuelSpinBox()
        self._shipFuelPerParsecSpinBox = gui.SharedFuelPerParsecSpinBox()
        self._freeCargoSpaceSpinBox = gui.SharedFreeCargoSpaceSpinBox()

        self._centerOptionsLayout = gui.FormLayoutEx()
        self._centerOptionsLayout.setContentsMargins(0, 0, 0, 0)
        self._centerOptionsLayout.addRow('Ship Total Tonnage:', self._shipTonnageSpinBox)
        self._centerOptionsLayout.addRow('Ship Jump Rating:', self._shipJumpRatingSpinBox)
        self._centerOptionsLayout.addRow('Ship Fuel Capacity:', self._shipFuelCapacitySpinBox)
        self._centerOptionsLayout.addRow('Ship Current Fuel:', self._shipCurrentFuelSpinBox)
        self._centerOptionsLayout.addRow('Ship Fuel Per Parsec:', self._shipFuelPerParsecSpinBox)
        self._centerOptionsLayout.addRow('Free Cargo Space:', self._freeCargoSpaceSpinBox)

        # Right column of controls
        self._refuellingStrategyComboBox = gui.SharedRefuellingStrategyComboBox()
        self._routeOptimisationComboBox = gui.SharedRouteOptimisationComboBox()
        self._perJumpOverheadsSpinBox = gui.SharedJumpOverheadSpinBox()
        self._includeStartWorldBerthingCheckBox = gui.SharedIncludeStartBerthingCheckBox()
        self._includeFinishWorldBerthingCheckBox = gui.SharedIncludeFinishBerthingCheckBox()
        self._includeLogisticsCostsCheckBox = gui.SharedIncludeLogisticsCostsCheckBox()
        self._includeUnprofitableTradesCheckBox = gui.SharedIncludeUnprofitableCheckBox()

        self._rightOptionsLayout = gui.FormLayoutEx()
        self._rightOptionsLayout.setContentsMargins(0, 0, 0, 0)
        self._rightOptionsLayout.addRow('Route Optimisation:', self._routeOptimisationComboBox)
        self._rightOptionsLayout.addRow('Refuelling Strategy:', self._refuellingStrategyComboBox)
        self._rightOptionsLayout.addRow('Per Jump Overheads:', self._perJumpOverheadsSpinBox)
        self._rightOptionsLayout.addRow('Start World Berthing:', self._includeStartWorldBerthingCheckBox)
        self._rightOptionsLayout.addRow('Finish World Berthing:', self._includeFinishWorldBerthingCheckBox)
        self._rightOptionsLayout.addRow('Include Logistics Costs:', self._includeLogisticsCostsCheckBox)
        self._rightOptionsLayout.addRow('Include Unprofitable Trades:', self._includeUnprofitableTradesCheckBox)

        optionsLayout = QtWidgets.QHBoxLayout()
        optionsLayout.addLayout(self._leftOptionsLayout)
        optionsLayout.addLayout(self._centerOptionsLayout)
        optionsLayout.addLayout(self._rightOptionsLayout)
        optionsLayout.addStretch()

        self._configurationGroupBox = QtWidgets.QGroupBox('Configuration')
        self._configurationGroupBox.setLayout(optionsLayout)

    def _setupTradeOptionControls(self) -> None:
        self._calculateTradeOptionsButton = gui.DualTextPushButton(
            primaryText='Calculate Trade Options',
            secondaryText='Cancel')
        self._calculateTradeOptionsButton.clicked.connect(self._calculateTradeOptions)

        self._progressLabel = gui.PrefixLabel(prefix='Processed Trade Options: ')
        self._tradeOptionCountLabel = gui.PrefixLabel(prefix='Filtered Trade Options: ')

        labelLayout = QtWidgets.QHBoxLayout()
        labelLayout.setContentsMargins(0, 0, 0, 0)
        labelLayout.addWidget(self._progressLabel)
        labelLayout.addWidget(self._tradeOptionCountLabel)

        self._tradeOptionCalculationModeTabs = gui.CalculationModeTabBar()
        self._tradeOptionCalculationModeTabs.currentChanged.connect(self._updateTradeOptionTableColumns)

        self._tradeOptionsTable = gui.TradeOptionsTable()
        self._tradeOptionsTable.setVisibleColumns(self._tradeOptionColumns())
        self._tradeOptionsTable.sortByColumnHeader(
            self._tradeOptionDefaultSortColumn(),
            QtCore.Qt.SortOrder.DescendingOrder)
        self._tradeOptionsTable.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self._tradeOptionsTable.customContextMenuRequested.connect(self._showTradeOptionsTableContextMenu)

        tableLayout = QtWidgets.QVBoxLayout()
        tableLayout.setContentsMargins(0, 0, 0, 0)
        tableLayout.setSpacing(0)
        tableLayout.addWidget(self._tradeOptionCalculationModeTabs)
        tableLayout.addWidget(self._tradeOptionsTable)

        self._createCargoManifestButton = QtWidgets.QPushButton('Create Cargo Manifest...')
        self._createCargoManifestButton.clicked.connect(self._createCargoManifest)

        tradeOptionsLayout = QtWidgets.QVBoxLayout()
        tradeOptionsLayout.addWidget(self._calculateTradeOptionsButton)
        tradeOptionsLayout.addLayout(labelLayout)
        tradeOptionsLayout.addLayout(tableLayout)
        tradeOptionsLayout.addWidget(self._createCargoManifestButton)

        self._tradeOptionsGroupBox = QtWidgets.QGroupBox('Trade Options')
        self._tradeOptionsGroupBox.setLayout(tradeOptionsLayout)

    def _setupTradeInfoControls(self) -> None:
        self._tradeInfoEditBox = QtWidgets.QPlainTextEdit()
        self._tradeInfoEditBox.setReadOnly(True)

    # This should be implemented by the derived class
    def _enableDisableControls(self) -> None:
        pass

    def _tradeOptionColumns(self) -> typing.List[gui.TradeOptionsTable.ColumnType]:
        calculationMode = self._tradeOptionCalculationModeTabs.currentCalculationMode()
        if calculationMode == gui.CalculationModeTabBar.CalculationMode.AverageCase:
            return gui.TradeOptionsTable.AverageCaseColumns
        elif calculationMode == gui.CalculationModeTabBar.CalculationMode.WorstCase:
            return gui.TradeOptionsTable.WorstCaseColumns
        elif calculationMode == gui.CalculationModeTabBar.CalculationMode.BestCase:
            return gui.TradeOptionsTable.BestCaseColumns
        else:
            assert(False) # I missed a case

    def _tradeOptionDefaultSortColumn(self) -> gui.TradeOptionsTable.ColumnType:
        calculationMode = self._tradeOptionCalculationModeTabs.currentCalculationMode()
        if calculationMode == gui.CalculationModeTabBar.CalculationMode.AverageCase:
            return gui.TradeOptionsTable.ColumnType.AverageNetProfit
        elif calculationMode == gui.CalculationModeTabBar.CalculationMode.WorstCase:
            return gui.TradeOptionsTable.ColumnType.WorstNetProfit
        elif calculationMode == gui.CalculationModeTabBar.CalculationMode.BestCase:
            return gui.TradeOptionsTable.ColumnType.BestNetProfit
        else:
            assert(False) # I missed a case

    def _addTradeOptions(self, tradeOptions: typing.List[logic.TradeOption]) -> None:
        self._tradeOptionsTable.addTradeOptions(tradeOptions)
        self._tradeOptionCountLabel.setNum(self._tradeOptionsTable.rowCount())

    def _addTraderInfo(self, tradeInfoList: typing.List[str]) -> None:
        concatenated = ''
        for tradeInfo in tradeInfoList:
            concatenated += tradeInfo + '\n'

        # Remove the last \n from the string, it looks like appendPlainText automatically adds a one
        concatenated = concatenated[:-1]

        self._tradeInfoEditBox.appendPlainText(concatenated)

    def _planJumpRoute(
            self,
            tradeOption: logic.TradeOption
            ) -> None:
        try:
            jumpRouteWindow = gui.WindowManager.instance().showJumpRouteWindow()
            jumpRouteWindow.configureControls(
                startWorld=tradeOption.purchaseWorld(),
                finishWorld=tradeOption.saleWorld(),
                shipTonnage=self._shipTonnageSpinBox.value(),
                shipJumpRating=self._shipJumpRatingSpinBox.value(),
                shipFuelCapacity=self._shipFuelCapacitySpinBox.value(),
                shipCurrentFuel=self._shipCurrentFuelSpinBox.value(),
                perJumpOverheads=self._perJumpOverheadsSpinBox.value(),
                refuellingStrategy=self._refuellingStrategyComboBox.currentEnum(),
                routeOptimisation=self._routeOptimisationComboBox.currentEnum(),
                includeStartWorldBerthingCosts=self._includeStartWorldBerthingCheckBox.isChecked(),
                includeFinishWorldBerthingCosts=self._includeFinishWorldBerthingCheckBox.isChecked())
        except Exception as ex:
            message = 'Failed to show jump route window'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)

    def _showWorldDetails(
            self,
            worlds: typing.Iterable[traveller.World]
            ) -> None:
        detailsWindow = gui.WindowManager.instance().showWorldDetailsWindow()
        detailsWindow.addWorlds(worlds=worlds)

    def _showTradeOptionCalculations(
            self,
            tradeOption: logic.TradeOption
            ) -> None:
        try:
            calculationWindow = gui.WindowManager.instance().showCalculationWindow()
            calculationWindow.showCalculation(calculation=tradeOption.returnOnInvestment())
        except Exception as ex:
            message = 'Failed to show trade option calculations'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)

    def _showJumpRouteInTravellerMap(
            self,
            jumpRoute: logic.JumpRoute
            ) -> None:
        try:
            mapWindow = gui.WindowManager.instance().showTravellerMapWindow()
            mapWindow.showJumpRoute(
                jumpRoute=jumpRoute,
                clearOverlays=True)
        except Exception as ex:
            message = 'Failed to show jump route in Traveller Map'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)

    def _showWorldsInTravellerMap(
            self,
            worlds: typing.Iterable[traveller.World]
            ) -> None:
        try:
            mapWindow = gui.WindowManager.instance().showTravellerMapWindow()
            mapWindow.centerOnWorlds(
                worlds=worlds,
                clearOverlays=True,
                highlightWorlds=True)
        except Exception as ex:
            message = 'Failed to show world(s) in Traveller Map'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)

    def _playerBrokerDmChanged(
            self,
            brokerSkill: int
            ) -> None:
        pass

    def _localPurchaseBrokerDmChanged(
            self,
            brokerSkill: typing.Optional[int]
            ) -> None:
        pass

    def _localSaleBrokerDmChanged(
            self,
            brokerSkill: typing.Optional[int]
            ) -> None:
        pass

    def _sellerDmChanged(
            self,
            minValue: int,
            maxValue: int
            ) -> None:
        pass

    def _buyerDmChanged(
            self,
            minValue: int,
            maxValue: int) -> None:
        pass

    # This should be implemented by the derived class
    def _calculateTradeOptions(self) -> None:
        pass

    def _updateTraderProgress(
            self,
            optionsProcessed: int,
            optionsToProcess: int
            ) -> None:
        self._progressLabel.setText(common.formatNumber(optionsProcessed) + '/' + common.formatNumber(optionsToProcess))

    def _traderFinished(self, result: typing.Union[str, Exception]) -> None:
        if isinstance(result, Exception):
            message = 'Failed to calculate trade options'
            logging.error(message, exc_info=result)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=result)
        elif self._traderJob and self._traderJob.isCancelled():
            pass
        else:
            if self._tradeOptionsTable.rowCount() == 0:
                gui.MessageBoxEx.information(
                    parent=self,
                    text='No trade options found')

        self._traderJob = None
        self._calculateTradeOptionsButton.showPrimaryText()
        self._enableDisableControls()

    def _updateTradeOptionTableColumns(self, index: int) -> None:
        self._tradeOptionsTable.setVisibleColumns(self._tradeOptionColumns())

    def _showTradeOptionsTableContextMenu(self, position: QtCore.QPoint) -> None:
        clickedTradeOption = self._tradeOptionsTable.tradeOptionAt(position)
        selectedTradeOptions = self._tradeOptionsTable.selectedTradeOptions()
        selectedPurchaseWorlds = None
        selectedSaleWorlds = None
        selectedSaleAndPurchaseWorlds = None
        if selectedTradeOptions:
            selectedPurchaseWorlds = set([tradeOption.purchaseWorld() for tradeOption in selectedTradeOptions])
            selectedSaleWorlds = set([tradeOption.saleWorld() for tradeOption in selectedTradeOptions])
            selectedSaleAndPurchaseWorlds = selectedPurchaseWorlds.union(selectedSaleWorlds)

        menuItems = [
            gui.MenuItem(
                text='Plan Jump Route Between Worlds...',
                callback=lambda: self._planJumpRoute(clickedTradeOption),
                enabled=clickedTradeOption != None
            ),
            None, # Separator
            gui.MenuItem(
                text='Show Selected Purchase World Details...',
                callback=lambda: self._showWorldDetails(selectedPurchaseWorlds),
                enabled=selectedPurchaseWorlds != None
            ),
            gui.MenuItem(
                text='Show Selected Sale World Details...',
                callback=lambda: self._showWorldDetails(selectedSaleWorlds),
                enabled=selectedSaleWorlds != None
            ),
            gui.MenuItem(
                text='Show Selected Purchase && Sale World Details...',
                callback=lambda: self._showWorldDetails(selectedSaleAndPurchaseWorlds),
                enabled=selectedSaleAndPurchaseWorlds != None
            ),
            None, # Separator
            gui.MenuItem(
                text='Show Selected Purchase Worlds in Traveller Map...',
                callback=lambda: self._showWorldsInTravellerMap(selectedPurchaseWorlds),
                enabled=selectedPurchaseWorlds != None
            ),
            gui.MenuItem(
                text='Show Selected Sale Worlds in Traveller Map...',
                callback=lambda: self._showWorldsInTravellerMap(selectedSaleWorlds),
                enabled=selectedSaleWorlds != None
            ),
            gui.MenuItem(
                text='Show Selected Sale && Purchase Worlds in Traveller Map...',
                callback=lambda: self._showWorldsInTravellerMap(selectedSaleAndPurchaseWorlds),
                enabled=selectedSaleAndPurchaseWorlds != None
            ),
            gui.MenuItem(
                text='Show Jump Route in Traveller Map...',
                callback=lambda: self._showJumpRouteInTravellerMap(clickedTradeOption.jumpRoute()),
                enabled=clickedTradeOption != None
            ),
            None, # Separator
            gui.MenuItem(
                text='Show Trade Option Calculations...',
                callback=lambda: self._showTradeOptionCalculations(clickedTradeOption),
                enabled=clickedTradeOption != None
            )
        ]

        gui.displayMenu(
            self,
            menuItems,
            self._tradeOptionsTable.viewport().mapToGlobal(position)
        )

    def _createCargoManifest(self) -> None:
        # This should be implemented by the derived class
        assert(False)

    def _showWelcomeMessage(self) -> None:
        # This should be implemented by the derived class
        assert(False)


# █████   ███   █████                    ████      █████    ███████████                         █████
#░░███   ░███  ░░███                    ░░███     ░░███    ░█░░░███░░░█                        ░░███
# ░███   ░███   ░███   ██████  ████████  ░███   ███████    ░   ░███  ░  ████████   ██████    ███████   ██████  ████████
# ░███   ░███   ░███  ███░░███░░███░░███ ░███  ███░░███        ░███    ░░███░░███ ░░░░░███  ███░░███  ███░░███░░███░░███
# ░░███  █████  ███  ░███ ░███ ░███ ░░░  ░███ ░███ ░███        ░███     ░███ ░░░   ███████ ░███ ░███ ░███████  ░███ ░░░
#  ░░░█████░█████░   ░███ ░███ ░███      ░███ ░███ ░███        ░███     ░███      ███░░███ ░███ ░███ ░███░░░   ░███
#    ░░███ ░░███     ░░██████  █████     █████░░████████       █████    █████    ░░████████░░████████░░██████  █████
#     ░░░   ░░░       ░░░░░░  ░░░░░     ░░░░░  ░░░░░░░░       ░░░░░    ░░░░░      ░░░░░░░░  ░░░░░░░░  ░░░░░░  ░░░░░

_WorldWelcomeMessage = """
    <html>
    <p>The World Trader window is intended as an aid to help players speculatively trading between
    their current world and other surrounding worlds. It can be used to give a guide to the profit
    they could expect to see and how it would be affected by different variables in the trading
    process.</p>
    <p>Currently, only Mongoose 1e & 2e rules are supported. Which rules are used can be selected in
    the Configuration dialog. Data from Traveller Map is used for calculating Sale & Purchase DMs
    for the worlds and logistics costs for travel between them.</p>
    <p>Although the Mongoose rules are simple enough that they can be condensed onto a few pages,
    they are complex enough that predicting if a trade even has a chance of being profitable can
    be non-trivial. This is especially true when you introduce things like local brokers and
    logistics costs.<br>
    To help with this problem, {name} uses an implementation of the trading rules to estimate the
    profit/loss the player would expect to see if the player were to make the worst case, best case
    and average dice rolls at all points in the trading process.<br>
    The most interesting of the 3 values is the average value as this can be used to gauge if a
    trade is likely to be profitable or not. The worst case and best case dice roll values are less
    interesting, however they can be used as a guide to the range of profit/loss the player would
    expect to see.</p>
    <p>The seller and buyer DM bonuses used in the trading processes are determined by the Referee
    rather than dice rolls. In order to take these values into account, {name} allows the player to
    specify ranges of what they expect these values to be. For "professional" sellers/buyers it
    would seem logical that these values would generally fall in the range 0-4, however they can
    be changed based on player experience. The lower extent, upper extent and average of the
    specified ranges are used by the trading engine when estimating the best case, worst
    case and average case profits respectively.
    <p>There are 3 types of cargo that can be specified, with the different types determining the
    quantity of cargo and purchase price used by the trading engine. Once the quantity and price are
    known the process is the same for all the cargo types. For each selected sale world, the trading
    engine uses the player's broker skill, the buyer DM range and the sale world trade codes to
    estimates how much the quantity of cargo could be sold for, with the purchase price (and any
    logistics costs) then used to estimate profit.</p>
    <p><b>Speculative Cargo</b> is intended to be used before you've found a seller on the current
    world (possibly before you've even reached the world). For each selected Trade Good, the players
    broker skill, seller DM range and purchase worlds trade codes are used to determine the worst
    case, best case and average purchase price and available tonnage. The trading engine determines
    how much of this potentially available cargo could be purchased based on available funds and
    ship cargo capacity.</p>
    <p><b>Available Cargo</b> is intended to be used at the point you've found a seller on the
    current world and know the availability and cost of the Trade Goods they're selling. The trading
    engine determines how much of the available cargo could be purchases based on available funds
    and ship cargo capacity.</p>
    <p><b>Current Cargo</b> is intended to be used after you've already purchased cargo (or obtained
    it by nefarious means). In this case the quantity and purchase price are both known, so the
    trading engine can simply estimate the sale price and profit. If the goods were "obtained" rather
    than purchased, then a purchase price of 0 can be used.</p>
    </html>
""".format(name=app.AppName)

class WorldTraderWindow(_BaseTraderWindow):
    def __init__(self) -> None:
        super().__init__(
            title='World Trader',
            configSection='WorldTraderWindow')

        self._setupPurchaseWorldControls()
        self._setupConfigurationControls()
        self._setupCargoControls()
        self._setupSaleWorldControls()
        self._setupTradeOptionControls()
        self._setupTradeInfoControls()

        self._enableDisableControls()

        self._tableSplitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        self._tableSplitter.addWidget(self._cargoGroupBox)
        self._tableSplitter.addWidget(self._saleWorldsGroupBox)

        configurationLayout = QtWidgets.QVBoxLayout()
        configurationLayout.setContentsMargins(0, 0, 0, 0)
        configurationLayout.addWidget(self._purchaseWorldGroupBox, 0)
        configurationLayout.addWidget(self._configurationGroupBox, 0)
        configurationLayout.addWidget(self._tableSplitter, 1)
        configurationWidget = QtWidgets.QWidget()
        configurationWidget.setLayout(configurationLayout)

        self._mainSplitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self._mainSplitter.addWidget(configurationWidget)
        self._mainSplitter.addWidget(self._tradeOptionsGroupBox)

        self._tradeInfoSplitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        self._tradeInfoSplitter.addWidget(self._mainSplitter)
        self._tradeInfoSplitter.addWidget(self._tradeInfoEditBox)

        windowLayout = QtWidgets.QVBoxLayout()
        windowLayout.addWidget(self._tradeInfoSplitter)

        self.setLayout(windowLayout)

    def configureControls(
            self,
            purchaseWorld: typing.Optional[traveller.World] = None,
            saleWorlds: typing.Optional[typing.Iterable[traveller.World]] = None,
            playerBrokerDm: typing.Optional[int] = None,
            minSellerDm: typing.Optional[int] = None,
            maxSellerDm: typing.Optional[int] = None,
            minBuyerDm: typing.Optional[int] = None,
            maxBuyerDm: typing.Optional[int] = None,
            availableFunds: typing.Optional[int] = None,
            shipTonnage: typing.Optional[int] = None,
            shipJumpRating: typing.Optional[int] = None,
            freeCargoSpace: typing.Optional[int] = None,
            shipFuelCapacity: typing.Optional[int] = None,
            shipCurrentFuel: typing.Optional[int] = None,
            perJumpOverheads: typing.Optional[int] = None,
            refuellingStrategy: typing.Optional[logic.RefuellingStrategy] = None,
            speculativeCargo: typing.Optional[typing.Iterable[logic.CargoRecord]] = None,
            availableCargo: typing.Optional[typing.Iterable[logic.CargoRecord]] = None,
            currentCargo: typing.Optional[typing.Iterable[logic.CargoRecord]] = None
            ) -> None:
        if self._traderJob:
            raise RuntimeError('Unable to setup trader window while a trade options job is in progress')

        # If we know we're going to be clearing out the cargo and/or sale worlds list, do it early
        # to prevent the user being prompted if they want to change them (if the purchase world is also
        # changed). No mater what they chose the list would still be cleared. This just stops the prompt
        # from being displayed
        if speculativeCargo:
            self._removeAllSpeculativeCargo()
        if availableCargo:
            self._removeAllAvailableCargo()
        if currentCargo:
            self._removeAllCurrentCargo()
        if saleWorlds:
            self._saleWorldsWidget.removeAllWorlds()

        if purchaseWorld != None:
            self._purchaseWorldWidget.setWorld(world=purchaseWorld)
        if playerBrokerDm != None:
            self._playerBrokerDmSpinBox.setValue(int(playerBrokerDm))
        if minSellerDm != None:
            self._sellerDmRangeWidget.setLowerValue(int(minSellerDm))
        if maxSellerDm != None:
            self._sellerDmRangeWidget.setUpperValue(int(maxSellerDm))
        if minBuyerDm != None:
            self._buyerDmRangeWidget.setLowerValue(int(minBuyerDm))
        if maxBuyerDm != None:
            self._buyerDmRangeWidget.setUpperValue(int(maxBuyerDm))
        if availableFunds != None:
            self._availableFundsSpinBox.setValue(int(availableFunds))
        if shipTonnage != None:
            self._shipTonnageSpinBox.setValue(int(shipTonnage))
        if shipJumpRating != None:
            self._shipJumpRatingSpinBox.setValue(int(shipJumpRating))
        if shipFuelCapacity != None:
            self._shipFuelCapacitySpinBox.setValue(int(shipFuelCapacity))
        if shipCurrentFuel != None:
            self._shipCurrentFuelSpinBox.setValue(int(shipCurrentFuel))
        if freeCargoSpace != None:
            self._freeCargoSpaceSpinBox.setValue(int(freeCargoSpace))
        if refuellingStrategy != None:
            self._refuellingStrategyComboBox.setCurrentEnum(refuellingStrategy)
        if perJumpOverheads != None:
            self._perJumpOverheadsSpinBox.setValue(int(perJumpOverheads))
        if speculativeCargo != None:
            for cargoRecord in speculativeCargo:
                self._addSpeculativeCargo(cargoRecord=cargoRecord)
        if availableCargo != None:
            for cargoRecord in availableCargo:
                self._addAvailableCargo(cargoRecord=cargoRecord)
        if currentCargo != None:
            for cargoRecord in currentCargo:
                self._addCurrentCargo(cargoRecord=cargoRecord)
        if saleWorlds != None:
            self._saleWorldsWidget.addWorlds(worlds=saleWorlds)

    def loadSettings(self) -> None:
        self._settings.beginGroup(self._configSection)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='PurchaseWorldState',
            type=QtCore.QByteArray)
        if storedValue:
            self._purchaseWorldWidget.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='CargoRecordsDisplayModeState',
            type=QtCore.QByteArray)
        if storedValue:
            self._cargoRecordDisplayModeTabView.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='SpeculativeCargoTableState',
            type=QtCore.QByteArray)
        if storedValue:
            self._speculativeCargoTable.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='SpeculativeCargoTableContent',
            type=QtCore.QByteArray)
        if storedValue:
            self._speculativeCargoTable.restoreContent(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='AvailableCargoTableState',
            type=QtCore.QByteArray)
        if storedValue:
            self._availableCargoTable.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='AvailableCargoTableContent',
            type=QtCore.QByteArray)
        if storedValue:
            self._availableCargoTable.restoreContent(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='CurrentCargoTableState',
            type=QtCore.QByteArray)
        if storedValue:
            self._currentCargoTable.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='CurrentCargoTableContent',
            type=QtCore.QByteArray)
        if storedValue:
            self._currentCargoTable.restoreContent(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='SaleWorldsTableState',
            type=QtCore.QByteArray)
        if storedValue:
            self._saleWorldsWidget.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='SaleWorldsTableContent',
            type=QtCore.QByteArray)
        if storedValue:
            self._saleWorldsWidget.restoreContent(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='MainSplitterState',
            type=QtCore.QByteArray)
        if storedValue:
            self._mainSplitter.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='TableSplitterState',
            type=QtCore.QByteArray)
        if storedValue:
            self._tableSplitter.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='TradeInfoSplitterState',
            type=QtCore.QByteArray)
        if storedValue:
            self._tradeInfoSplitter.restoreState(storedValue)

        self._settings.endGroup()

        # Force an update of the sale world trade scores to sync them with any
        # loaded cargo
        self._updateSaleWorldTradeScores()

        # Call base implementation after setting purchase world as it avoids a prompt
        # asking if the user wants to clear the sale world list if one was restored
        super().loadSettings()

    def saveSettings(self) -> None:
        self._settings.beginGroup(self._configSection)

        self._settings.setValue('CargoRecordsDisplayModeState', self._cargoRecordDisplayModeTabView.saveState())
        self._settings.setValue('SpeculativeCargoTableState', self._speculativeCargoTable.saveState())
        self._settings.setValue('SpeculativeCargoTableContent', self._speculativeCargoTable.saveContent())
        self._settings.setValue('AvailableCargoTableState', self._availableCargoTable.saveState())
        self._settings.setValue('AvailableCargoTableContent', self._availableCargoTable.saveContent())
        self._settings.setValue('SaleWorldsTableState', self._saleWorldsWidget.saveState())
        self._settings.setValue('SaleWorldsTableContent', self._saleWorldsWidget.saveContent())
        self._settings.setValue('CurrentCargoTableState', self._currentCargoTable.saveState())
        self._settings.setValue('CurrentCargoTableContent', self._currentCargoTable.saveContent())
        self._settings.setValue('PurchaseWorldState', self._purchaseWorldWidget.saveState())
        self._settings.setValue('MainSplitterState', self._mainSplitter.saveState())
        self._settings.setValue('TableSplitterState', self._tableSplitter.saveState())
        self._settings.setValue('TradeInfoSplitterState', self._tradeInfoSplitter.saveState())

        self._settings.endGroup()

        super().saveSettings()

    def _setupPurchaseWorldControls(self) -> None:
        self._purchaseWorldWidget = gui.WorldSelectWidget()
        self._purchaseWorldWidget.selectionChanged.connect(self._purchaseWorldChanged)

        purchaseWorldLayout = QtWidgets.QVBoxLayout()
        purchaseWorldLayout.addWidget(self._purchaseWorldWidget)

        self._purchaseWorldGroupBox = QtWidgets.QGroupBox('Purchase World')
        self._purchaseWorldGroupBox.setLayout(purchaseWorldLayout)

    def _setupSaleWorldControls(self) -> None:
        self._saleWorldsTable = _WorldSaleScoreTable()

        self._saleWorldsWidget = gui.WorldTableManagerWidget(
            worldTable=self._saleWorldsTable,
            allowWorldCallback=self._allowSaleWorld)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self._saleWorldsWidget)

        self._saleWorldsGroupBox = QtWidgets.QGroupBox('Sale Worlds')
        self._saleWorldsGroupBox.setLayout(layout)

    def _setupCargoControls(self) -> None:
        self._cargoRecordDisplayModeTabView = gui.TabWidgetEx()
        self._cargoRecordDisplayModeTabView.setTabPosition(QtWidgets.QTabWidget.TabPosition.West)

        # Speculative cargo controls
        self._speculativeCargoTable = gui.CargoRecordTable(
            columns=gui.CargoRecordTable.AllCaseColumns)
        self._speculativeCargoTable.setMinimumHeight(100)
        self._speculativeCargoTable.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self._speculativeCargoTable.customContextMenuRequested.connect(self._showSpeculativeCargoTableContextMenu)
        self._speculativeCargoTable.keyPressed.connect(self._speculativeCargoTableKeyPressed)

        self._addWorldSpeculativeCargoButton = QtWidgets.QPushButton('Add World Options...')
        self._addWorldSpeculativeCargoButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)
        self._addWorldSpeculativeCargoButton.clicked.connect(self._generateSpeculativeCargoForWorld)

        self._addSpeculativeCargoButton = QtWidgets.QPushButton('Add...')
        self._addSpeculativeCargoButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)
        self._addSpeculativeCargoButton.clicked.connect(self._promptAddSpeculativeCargo)

        self._removeSpeculativeCargoButton = QtWidgets.QPushButton('Remove')
        self._removeSpeculativeCargoButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)
        self._removeSpeculativeCargoButton.clicked.connect(self._removeSelectedSpeculativeCargo)

        self._removeAllSpeculativeCargoButton = QtWidgets.QPushButton('Remove All')
        self._removeAllSpeculativeCargoButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)
        self._removeAllSpeculativeCargoButton.clicked.connect(self._removeAllSpeculativeCargo)

        buttonLayout = QtWidgets.QHBoxLayout()
        buttonLayout.setContentsMargins(0, 0, 0, 0)
        buttonLayout.addWidget(self._addWorldSpeculativeCargoButton)
        buttonLayout.addStretch()
        buttonLayout.addWidget(self._addSpeculativeCargoButton)
        buttonLayout.addWidget(self._removeSpeculativeCargoButton)
        buttonLayout.addWidget(self._removeAllSpeculativeCargoButton)

        paneLayout = QtWidgets.QVBoxLayout()
        paneLayout.setContentsMargins(0, 0, 0, 0)
        paneLayout.addWidget(self._speculativeCargoTable)
        paneLayout.addLayout(buttonLayout)
        paneWidget = QtWidgets.QWidget()
        paneWidget.setLayout(paneLayout)

        tabIndex = self._cargoRecordDisplayModeTabView.addTab(paneWidget, 'Speculative')
        self._cargoRecordDisplayModeTabView.setTabToolTip(
            tabIndex,
            gui.createStringToolTip(
                '<p>Cargo for purely speculative trading</p>' \
                '<p>This view can be used to speculate on potential profit before you know the ' \
                'price or availability of the cargo (i.e. before you\'ve found a seller). The ' \
                'results can be used to gauge if it\'s worth spending the time finding one.</p>' \
                '<p>Trade options generated for this cargo will speculate on availability, ' \
                'purchase price, sale price and logistics costs. The purchase price and ' \
                'availability ranges for cargo is calculated from on the trade codes for ' \
                'the current world.</p>',
                escape=False))

        # Available cargo controls
        self._availableCargoTable = gui.CargoRecordTable(
            columns=[
                gui.CargoRecordTable.ColumnType.TradeGood,
                gui.CargoRecordTable.ColumnType.BasePricePerTon,
                gui.CargoRecordTable.ColumnType.SetPricePerTon,
                gui.CargoRecordTable.ColumnType.SetQuantity])
        self._availableCargoTable.setMinimumHeight(100)
        self._availableCargoTable.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self._availableCargoTable.customContextMenuRequested.connect(self._showAvailableCargoTableContextMenu)
        self._availableCargoTable.doubleClicked.connect(self._promptEditAvailableCargo)
        self._availableCargoTable.keyPressed.connect(self._availableCargoTableKeyPressed)

        self._importAvailableCargoButton = QtWidgets.QPushButton('Import...')
        self._importAvailableCargoButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)
        self._importAvailableCargoButton.clicked.connect(self._importAvailableCargo)

        self._purchaseAvailableCargoButton = QtWidgets.QPushButton('Purchase...')
        self._purchaseAvailableCargoButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)
        self._purchaseAvailableCargoButton.clicked.connect(self._purchaseAvailableCargo)

        self._addAvailableCargoButton = QtWidgets.QPushButton('Add...')
        self._addAvailableCargoButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)
        self._addAvailableCargoButton.clicked.connect(self._promptAddAvailableCargo)

        self._editAvailableCargoButton = QtWidgets.QPushButton('Edit...')
        self._editAvailableCargoButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)
        self._editAvailableCargoButton.clicked.connect(self._promptEditAvailableCargo)

        self._removeAvailableCargoButton = QtWidgets.QPushButton('Remove')
        self._removeAvailableCargoButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)
        self._removeAvailableCargoButton.clicked.connect(self._removeSelectedAvailableCargo)

        self._removeAllAvailableCargoButton = QtWidgets.QPushButton('Remove All')
        self._removeAllAvailableCargoButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)
        self._removeAllAvailableCargoButton.clicked.connect(self._removeAllAvailableCargo)

        buttonLayout = QtWidgets.QHBoxLayout()
        buttonLayout.setContentsMargins(0, 0, 0, 0)
        buttonLayout.addWidget(self._importAvailableCargoButton)
        buttonLayout.addWidget(self._purchaseAvailableCargoButton)
        buttonLayout.addStretch()
        buttonLayout.addWidget(self._addAvailableCargoButton)
        buttonLayout.addWidget(self._editAvailableCargoButton)
        buttonLayout.addWidget(self._removeAvailableCargoButton)
        buttonLayout.addWidget(self._removeAllAvailableCargoButton)

        paneLayout = QtWidgets.QVBoxLayout()
        paneLayout.setContentsMargins(0, 0, 0, 0)
        paneLayout.addWidget(self._availableCargoTable)
        paneLayout.addLayout(buttonLayout)
        paneWidget = QtWidgets.QWidget()
        paneWidget.setLayout(paneLayout)

        tabIndex = self._cargoRecordDisplayModeTabView.addTab(paneWidget, 'Available')
        self._cargoRecordDisplayModeTabView.setTabToolTip(
            tabIndex,
            gui.createStringToolTip(
                '<p>Cargo available for purchase</p>' \
                '<p>This view can be used to speculate on available cargo that has been generated ' \
                'by the Referee for a seller. The results can be used to gauge if it\'s worth ' \
                'purchasing the goods and, if you do, where is best to sell them.</p>' \
                '<p>Trade options generated for this cargo will speculate on sale price and ' \
                'logistics costs. The quantity of the cargo used for speculating will be ' \
                'determined by the quantity available for purchase, the per ton purchase price, ' \
                'your available funds and logistics costs.</p>',
                escape=False))

        # Current cargo controls
        self._currentCargoTable = gui.CargoRecordTable(
            columns=[
                gui.CargoRecordTable.ColumnType.TradeGood,
                gui.CargoRecordTable.ColumnType.SetTotalPrice,
                gui.CargoRecordTable.ColumnType.SetPricePerTon,
                gui.CargoRecordTable.ColumnType.SetQuantity])
        self._currentCargoTable.setMinimumHeight(100)
        self._currentCargoTable.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self._currentCargoTable.customContextMenuRequested.connect(self._showCurrentCargoTableContextMenu)
        self._currentCargoTable.doubleClicked.connect(self._promptEditCurrentCargo)
        self._currentCargoTable.keyPressed.connect(self._currentCargoTableKeyPressed)

        self._importCurrentCargoButton = QtWidgets.QPushButton('Import...')
        self._importCurrentCargoButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)
        self._importCurrentCargoButton.clicked.connect(self._importCurrentCargo)

        self._exportCurrentCargoButton = QtWidgets.QPushButton('Export...')
        self._exportCurrentCargoButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)
        self._exportCurrentCargoButton.clicked.connect(self._exportCurrentCargo)

        self._addCurrentCargoButton = QtWidgets.QPushButton('Add...')
        self._addCurrentCargoButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)
        self._addCurrentCargoButton.clicked.connect(self._promptAddCurrentCargo)

        self._editCurrentCargoButton = QtWidgets.QPushButton('Edit...')
        self._editCurrentCargoButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)
        self._editCurrentCargoButton.clicked.connect(self._promptEditCurrentCargo)

        self._removeCurrentCargoButton = QtWidgets.QPushButton('Remove')
        self._removeCurrentCargoButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)
        self._removeCurrentCargoButton.clicked.connect(self._removeSelectedCurrentCargo)

        self._removeAllCurrentCargoButton = QtWidgets.QPushButton('Remove All')
        self._removeAllCurrentCargoButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)
        self._removeAllCurrentCargoButton.clicked.connect(self._removeAllCurrentCargo)

        buttonLayout = QtWidgets.QHBoxLayout()
        buttonLayout.setContentsMargins(0, 0, 0, 0)
        buttonLayout.addWidget(self._importCurrentCargoButton)
        buttonLayout.addWidget(self._exportCurrentCargoButton)
        buttonLayout.addStretch()
        buttonLayout.addWidget(self._addCurrentCargoButton)
        buttonLayout.addWidget(self._editCurrentCargoButton)
        buttonLayout.addWidget(self._removeCurrentCargoButton)
        buttonLayout.addWidget(self._removeAllCurrentCargoButton)

        paneLayout = QtWidgets.QVBoxLayout()
        paneLayout.setContentsMargins(0, 0, 0, 0)
        paneLayout.addWidget(self._currentCargoTable)
        paneLayout.addLayout(buttonLayout)
        paneWidget = QtWidgets.QWidget()
        paneWidget.setLayout(paneLayout)

        tabIndex = self._cargoRecordDisplayModeTabView.addTab(paneWidget, 'Current')
        self._cargoRecordDisplayModeTabView.setTabToolTip(
            tabIndex,
            gui.createStringToolTip(
                '<p>Cargo that you currently own</p>' \
                '<p>This view can be used to speculate on the sale of the cargo you currently own.' \
                'The results can be used to gauge where you\'re best to go to offload your cargo.</p>' \
                '<p>Trade options generated for this cargo will speculate on sale price and ' \
                'logistics costs.</p>',
                escape=False))

        # Group box
        groupBoxLayout = QtWidgets.QVBoxLayout()
        groupBoxLayout.addWidget(self._cargoRecordDisplayModeTabView)

        self._cargoGroupBox = QtWidgets.QGroupBox('Cargo')
        self._cargoGroupBox.setLayout(groupBoxLayout)

    def _enableDisableControls(self) -> None:
        if not self._traderJob:
            self._purchaseWorldGroupBox.setDisabled(False)

            # Disable all other controls until purchase world is selected
            disable = not self._purchaseWorldWidget.hasSelection()
            self._configurationGroupBox.setDisabled(disable)
            self._cargoGroupBox.setDisabled(disable)
            self._saleWorldsGroupBox.setDisabled(disable)
            self._tradeOptionsGroupBox.setDisabled(disable)
            self._createCargoManifestButton.setDisabled(disable)
        else:
            # Disable configuration controls while trade option job is running
            self._purchaseWorldGroupBox.setDisabled(True)
            self._configurationGroupBox.setDisabled(True)
            self._cargoGroupBox.setDisabled(True)
            self._saleWorldsGroupBox.setDisabled(True)
            self._createCargoManifestButton.setDisabled(True)

    def _addSpeculativeCargo(
            self,
            cargoRecord: logic.CargoRecord
            ) -> None:
        tradeGood = cargoRecord.tradeGood()
        if self._speculativeCargoTable.hasCargoRecordForTradeGood(tradeGood):
            return
        self._speculativeCargoTable.addCargoRecord(cargoRecord)
        self._updateSaleWorldTradeScores()

    def _removeSelectedSpeculativeCargo(self) -> None:
        if not self._speculativeCargoTable.hasSelection():
            return
        self._speculativeCargoTable.removeSelectedRows()
        self._updateSaleWorldTradeScores()

    def _removeAllSpeculativeCargo(self) -> None:
        if self._speculativeCargoTable.isEmpty():
            return
        self._speculativeCargoTable.removeAllRows()
        self._updateSaleWorldTradeScores()

    def _addAvailableCargo(
            self,
            cargoRecord: logic.CargoRecord
            ) -> None:
        tradeGood = cargoRecord.tradeGood()
        if self._availableCargoTable.hasCargoRecordForTradeGood(tradeGood):
            return
        self._availableCargoTable.addCargoRecord(cargoRecord)
        self._updateSaleWorldTradeScores()

    def _removeSelectedAvailableCargo(self) -> None:
        if not self._availableCargoTable.hasSelection():
            return
        self._availableCargoTable.removeSelectedRows()
        self._updateSaleWorldTradeScores()

    def _removeAllAvailableCargo(self) -> None:
        if self._availableCargoTable.isEmpty():
            return
        self._availableCargoTable.removeAllRows()
        self._updateSaleWorldTradeScores()

    def _addCurrentCargo(
            self,
            cargoRecord: logic.CargoRecord
            ) -> None:
        self._currentCargoTable.addCargoRecord(cargoRecord)
        self._updateSaleWorldTradeScores()

    def _removeSelectedCurrentCargo(self) -> None:
        if not self._currentCargoTable.hasSelection():
            return
        self._currentCargoTable.removeSelectedRows()
        self._updateSaleWorldTradeScores()

    def _removeAllCurrentCargo(self) -> None:
        if self._currentCargoTable.isEmpty():
            return
        self._currentCargoTable.removeAllRows()
        self._updateSaleWorldTradeScores()

    def _regenerateSpeculativeCargo(self):
        world = self._purchaseWorldWidget.world()
        if not world:
            self._removeAllSpeculativeCargo()
            return

        replacements = {}
        for currentCargoRecord in self._speculativeCargoTable.cargoRecords():
            cargoRecords = logic.generateSpeculativePurchaseCargo(
                rules=app.Config.instance().rules(),
                world=world,
                playerBrokerDm=self._playerBrokerDmSpinBox.value(),
                useLocalBroker=self._localPurchaseBrokerWidget.isChecked(),
                localBrokerDm=self._localPurchaseBrokerWidget.value(),
                minSellerDm=self._sellerDmRangeWidget.lowerValue(),
                maxSellerDm=self._sellerDmRangeWidget.upperValue(),
                tradeGoods=[currentCargoRecord.tradeGood()])
            assert(len(cargoRecords) == 1)
            newCargoRecord = cargoRecords[0]
            replacements[currentCargoRecord] = newCargoRecord

        if not replacements:
            return # Nothing to do

        self._speculativeCargoTable.replaceCargoRecords(replacements=replacements)
        self._updateSaleWorldTradeScores()

    def _showCargoRecordCalculations(
            self,
            cargoRecord: logic.CargoRecord
            ) -> None:
        try:
            calculationWindow = gui.WindowManager.instance().showCalculationWindow()
            calculationWindow.showCalculations(calculations=[
                cargoRecord.pricePerTon(),
                cargoRecord.quantity()])
        except Exception as ex:
            message = 'Failed to show cargo record calculations'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)

    def _loadCargoRecordPrompt(self) -> typing.Optional[typing.Iterable[logic.CargoRecord]]:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            'Open File',
            QtCore.QDir.homePath(),
            'JSON Files(*.json)')
        if not path:
            return None

        try:
            cargoRecords = logic.readCargoRecordList(
                rules=app.Config.instance().rules(),
                filePath=path)
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

    def _allowSaleWorld(self, world: traveller.World) -> bool:
        # Silently ignore worlds that are already in the table
        return not self._saleWorldsWidget.containsWorld(world)

    def _updateSaleWorldTradeScores(self) -> None:
        tradeGoods = set()
        for tradeOption in self._speculativeCargoTable.cargoRecords():
            tradeGoods.add(tradeOption.tradeGood())
        for tradeOption in self._availableCargoTable.cargoRecords():
            tradeGoods.add(tradeOption.tradeGood())
        for tradeOption in self._currentCargoTable.cargoRecords():
            tradeGoods.add(tradeOption.tradeGood())
        self._saleWorldsTable.setTradeGoods(tradeGoods)

    def _playerBrokerDmChanged(
            self,
            brokerSkill: int
            ) -> None:
        super()._playerBrokerDmChanged(brokerSkill)
        self._regenerateSpeculativeCargo()

    def _localPurchaseBrokerDmChanged(
            self,
            brokerSkill: typing.Optional[int]
            ) -> None:
        super()._localPurchaseBrokerDmChanged(brokerSkill)
        self._regenerateSpeculativeCargo()

    def _sellerDmChanged(
            self,
            minValue: int,
            maxValue: int
            ) -> None:
        super()._sellerDmChanged(minValue, maxValue)
        self._regenerateSpeculativeCargo()

    def _purchaseWorldChanged(self) -> None:
        self._enableDisableControls()

        self._saleWorldsWidget.setRelativeWorld(world=self._purchaseWorldWidget.world())

        if not self._speculativeCargoTable.isEmpty():
            answer = gui.MessageBoxEx.question(
                parent=self,
                text='Clear speculative cargo?')
            if answer == QtWidgets.QMessageBox.StandardButton.Yes:
                self._removeAllSpeculativeCargo()

        if not self._availableCargoTable.isEmpty():
            answer = gui.MessageBoxEx.question(
                parent=self,
                text='Clear available cargo?')
            if answer == QtWidgets.QMessageBox.StandardButton.Yes:
                self._removeAllAvailableCargo()

        if not self._saleWorldsWidget.isEmpty():
            answer = gui.MessageBoxEx.question(
                parent=self,
                text='Clear sale worlds?')
            if answer == QtWidgets.QMessageBox.StandardButton.Yes:
                self._saleWorldsWidget.removeAllWorlds()

        # Always clear trade options as they're invalid now the purchase world has changed
        self._tradeOptionsTable.removeAllRows()

    def _generateSpeculativeCargoForWorld(self) -> None:
        if not self._speculativeCargoTable.isEmpty():
            answer = gui.MessageBoxEx.question(
                parent=self,
                text='This will replace the current speculative cargo.\nDo you ant to continue?')
            if answer != QtWidgets.QMessageBox.StandardButton.Yes:
                return

        includeIllegal = gui.MessageBoxEx.question(
            parent=self,
            text='Include illegal trade goods?') == QtWidgets.QMessageBox.StandardButton.Yes

        cargoRecords = logic.generateSpeculativePurchaseCargo(
            rules=app.Config.instance().rules(),
            world=self._purchaseWorldWidget.world(),
            playerBrokerDm=self._playerBrokerDmSpinBox.value(),
            useLocalBroker=self._localPurchaseBrokerWidget.isChecked(),
            localBrokerDm=self._localPurchaseBrokerWidget.value(),
            minSellerDm=self._sellerDmRangeWidget.lowerValue(),
            maxSellerDm=self._sellerDmRangeWidget.upperValue(),
            includeLegal=True,
            includeIllegal=includeIllegal)

        self._removeAllSpeculativeCargo()
        for cargoRecord in cargoRecords:
            self._addSpeculativeCargo(cargoRecord)

    def _promptAddSpeculativeCargo(self) -> None:
        # Don't list exotics. We can't generate speculate trade options for them so there's no
        # reason to add them here
        ignoreTradeGoods = [traveller.tradeGoodFromId(
            rules=app.Config.instance().rules(),
            tradeGoodId=traveller.TradeGoodIds.Exotics)]

        # Don't list trade goods that have already been added to the list
        for row in range(self._speculativeCargoTable.rowCount()):
            cargoRecord = self._speculativeCargoTable.cargoRecord(row)
            ignoreTradeGoods.append(cargoRecord.tradeGood())

        tradeGoods = traveller.tradeGoodList(
            rules=app.Config.instance().rules(),
            excludeTradeGoods=ignoreTradeGoods)

        if not tradeGoods:
            gui.MessageBoxEx.information(
                parent=self,
                text='Cargo records for all trade goods have already been added')
            return

        dlg = gui.TradeGoodMultiSelectDialog(selectableTradeGoods=tradeGoods)
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return

        cargoRecords = logic.generateSpeculativePurchaseCargo(
            rules=app.Config.instance().rules(),
            world=self._purchaseWorldWidget.world(),
            playerBrokerDm=self._playerBrokerDmSpinBox.value(),
            useLocalBroker=self._localPurchaseBrokerWidget.isChecked(),
            localBrokerDm=self._localPurchaseBrokerWidget.value(),
            minSellerDm=self._sellerDmRangeWidget.lowerValue(),
            maxSellerDm=self._sellerDmRangeWidget.upperValue(),
            tradeGoods=dlg.selectedTradeGoods())

        for cargoRecord in cargoRecords:
            self._addSpeculativeCargo(cargoRecord)

    def _showSpeculativeCargoTableContextMenu(self, position: QtCore.QPoint) -> None:
        menuItems = [
            gui.MenuItem(
                text='Add Current World Cargo...',
                callback=lambda: self._generateSpeculativeCargoForWorld(),
                enabled=True
            ),
            gui.MenuItem(
                text='Add Cargo...',
                callback=lambda: self._promptAddSpeculativeCargo(),
                enabled=True
            ),
            gui.MenuItem(
                text='Remove Selected Cargo',
                callback=lambda: self._removeSelectedSpeculativeCargo(),
                enabled=self._speculativeCargoTable.hasSelection()
            ),
            gui.MenuItem(
                text='Remove All Cargo',
                callback=lambda: self._removeAllSpeculativeCargo(),
                enabled=not self._speculativeCargoTable.isEmpty()
            ),
            None, # Separator
            gui.MenuItem(
                text='Show Calculations...',
                callback=lambda: self._showCargoRecordCalculations(self._speculativeCargoTable.currentCargoRecord()),
                enabled=self._speculativeCargoTable.hasSelection()
            )
        ]

        gui.displayMenu(
            self,
            menuItems,
            self._speculativeCargoTable.viewport().mapToGlobal(position)
        )

    def _speculativeCargoTableKeyPressed(self, key: int) -> None:
        if key == QtCore.Qt.Key.Key_Delete:
            self._removeSelectedSpeculativeCargo()

    def _importAvailableCargo(self) -> None:
        if not self._availableCargoTable.isEmpty():
            answer = gui.MessageBoxEx.question(
                parent=self,
                text='This will replace the available cargo.\nDo you want to continue?')
            if answer != QtWidgets.QMessageBox.StandardButton.Yes:
                return

        cargoRecords = self._loadCargoRecordPrompt()
        if not cargoRecords:
            # The user cancelled the load at the file dialog
            return

        self._removeAllAvailableCargo()
        for cargoRecord in cargoRecords:
            pricePerTon = cargoRecord.pricePerTon().averageCaseCalculation()
            quantity = cargoRecord.quantity().averageCaseCalculation()

            if quantity.value() <= 0:
                # Silently ignore trade goods with no availability
                continue

            newCargoRecord = logic.CargoRecord(
                tradeGood=cargoRecord.tradeGood(),
                pricePerTon=pricePerTon,
                quantity=quantity)
            self._addAvailableCargo(cargoRecord=newCargoRecord)

    def _promptAddAvailableCargo(self) -> None:
        # Don't list trade goods that have already been added to the list
        ignoreTradeGoods = []
        for row in range(self._availableCargoTable.rowCount()):
            cargoRecord = self._availableCargoTable.cargoRecord(row)
            ignoreTradeGoods.append(cargoRecord.tradeGood())

        tradeGoods = traveller.tradeGoodList(
            rules=app.Config.instance().rules(),
            excludeTradeGoods=ignoreTradeGoods)

        if not tradeGoods:
            gui.MessageBoxEx.information(
                parent=self,
                text='All trade goods have already been added')
            return

        dlg = gui.ScalarCargoDetailsDialog(
            title='Add Available Cargo',
            world=self._purchaseWorldWidget.world(),
            selectableTradeGoods=tradeGoods)
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return

        cargoRecord = logic.CargoRecord(
            tradeGood=dlg.tradeGood(),
            pricePerTon=dlg.pricePerTon(),
            quantity=dlg.quantity())

        self._addAvailableCargo(cargoRecord)

    def _promptEditAvailableCargo(self) -> None:
        row = self._availableCargoTable.currentRow()
        if row < 0:
            gui.MessageBoxEx.information(
                parent=self,
                text='Select the cargo to edit')
            return

        cargoRecord = self._availableCargoTable.cargoRecord(row)
        pricePerTon = cargoRecord.pricePerTon()
        assert(isinstance(pricePerTon, common.ScalarCalculation))
        quantity = cargoRecord.quantity()
        assert(isinstance(quantity, common.ScalarCalculation))

        dlg = gui.ScalarCargoDetailsDialog(
            title='Edit Available Cargo',
            world=self._purchaseWorldWidget.world(),
            editTradeGood=cargoRecord.tradeGood(),
            editPricePerTon=pricePerTon,
            editQuantity=quantity)
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return

        cargoRecord = logic.CargoRecord(
            tradeGood=dlg.tradeGood(),
            pricePerTon=dlg.pricePerTon(),
            quantity=dlg.quantity())

        self._availableCargoTable.setCargoRecord(row, cargoRecord)
        self._updateSaleWorldTradeScores()

    def _purchaseAvailableCargo(self) -> None:
        if self._availableCargoTable.isEmpty():
            gui.MessageBoxEx.information(
                parent=self,
                text='No cargo available for purchase')
            return

        affordableCargo = []
        for cargoRecord in self._availableCargoTable.cargoRecords():
            if cargoRecord.pricePerTon().value() > self._availableFundsSpinBox.value():
                continue
            affordableCargo.append(cargoRecord)

        if not affordableCargo:
            gui.MessageBoxEx.information(
                parent=self,
                text='You can\'t afford any of the available cargo')
            return

        if not self._freeCargoSpaceSpinBox.value():
            gui.MessageBoxEx.information(
                parent=self,
                text='You have no free cargo space')
            return

        dlg = gui.PurchaseCargoDialog(
            world=self._purchaseWorldWidget.world(),
            availableCargo=affordableCargo,
            availableFunds=self._availableFundsSpinBox.value(),
            freeCargoCapacity=self._freeCargoSpaceSpinBox.value())
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return

        totalCost = 0
        totalQuantity = 0
        for cargoRecord in dlg.purchasedCargo():
            pricePerTon = cargoRecord.pricePerTon().value()
            quantity = cargoRecord.quantity().value()
            totalCost += pricePerTon * quantity
            totalQuantity += quantity

            self._addCurrentCargo(cargoRecord)

        remainingCargo = {cargoRecord.tradeGood(): cargoRecord for cargoRecord in dlg.remainingCargo()}
        for row in range(self._availableCargoTable.rowCount()):
            existingCargoRecord = self._availableCargoTable.cargoRecord(row=row)
            replacementCargoRecord = remainingCargo.get(existingCargoRecord.tradeGood())
            if replacementCargoRecord:
                self._availableCargoTable.setCargoRecord(row=row, cargoRecord=replacementCargoRecord)

        # Update available funds and cargo capacity
        self._availableFundsSpinBox.setValue(
            self._availableFundsSpinBox.value() - int(totalCost))
        self._freeCargoSpaceSpinBox.setValue(
            self._freeCargoSpaceSpinBox.value() - int(totalQuantity))

    def _showAvailableCargoTableContextMenu(self, position: QtCore.QPoint) -> None:
        menuItems = [
            gui.MenuItem(
                text='Add Cargo...',
                callback=lambda: self._promptAddAvailableCargo(),
                enabled=True
            ),
            gui.MenuItem(
                text='Edit Cargo...',
                callback=lambda: self._promptEditAvailableCargo(),
                enabled=self._availableCargoTable.hasSelection()
            ),
            gui.MenuItem(
                text='Remove Selected Cargo',
                callback=lambda: self._removeSelectedAvailableCargo(),
                enabled=self._availableCargoTable.hasSelection()
            ),
            gui.MenuItem(
                text='Remove All Cargo',
                callback=lambda: self._removeAllAvailableCargo(),
                enabled=not self._availableCargoTable.isEmpty()
            ),
            None, # Separator
            gui.MenuItem(
                text='Purchase Cargo...',
                callback=lambda: self._purchaseAvailableCargo(),
                enabled=self._availableCargoTable.hasSelection()
            ),
            None, # Separator
            gui.MenuItem(
                text='Show Calculations...',
                callback=lambda: self._showCargoRecordCalculations(self._availableCargoTable.currentCargoRecord()),
                enabled=self._availableCargoTable.hasSelection()
            )
        ]

        gui.displayMenu(
            self,
            menuItems,
            self._availableCargoTable.viewport().mapToGlobal(position)
        )

    def _availableCargoTableKeyPressed(self, key: int) -> None:
        if key == QtCore.Qt.Key.Key_Delete:
            self._removeSelectedAvailableCargo()

    def _importCurrentCargo(self) -> None:
        if not self._currentCargoTable.isEmpty():
            answer = gui.MessageBoxEx.question(
                parent=self,
                text='This will replace the current cargo.\nDo you want to continue?')
            if answer != QtWidgets.QMessageBox.StandardButton.Yes:
                return

        cargoRecords = self._loadCargoRecordPrompt()
        if not cargoRecords:
            return

        self._removeAllCurrentCargo()
        for cargoRecord in cargoRecords:
            pricePerTon = cargoRecord.pricePerTon().averageCaseCalculation()
            quantity = cargoRecord.quantity().averageCaseCalculation()

            if quantity.value() <= 0:
                # Silently ignore cargo with no quantity
                continue

            newCargoRecord = logic.CargoRecord(
                tradeGood=cargoRecord.tradeGood(),
                pricePerTon=pricePerTon,
                quantity=quantity)
            self._addCurrentCargo(cargoRecord=newCargoRecord)

    def _exportCurrentCargo(self) -> None:
        if self._currentCargoTable.isEmpty():
            gui.MessageBoxEx.information(
                parent=self,
                text='No cargo to export')
            return

        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            'Save File',
            QtCore.QDir.homePath() + '/cargo.json',
            'JSON Files(*.json)')
        if not path:
            return

        try:
            logic.writeCargoRecordList(
                self._currentCargoTable.cargoRecords(),
                path)
        except Exception as ex:
            message = f'Failed to write cargo to "{path}"'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)

    def _promptAddCurrentCargo(self) -> None:
        dlg = gui.ScalarCargoDetailsDialog(
            title='Add Current Cargo',
            world=self._purchaseWorldWidget.world())
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return

        cargoRecord = logic.CargoRecord(
            tradeGood=dlg.tradeGood(),
            pricePerTon=dlg.pricePerTon(),
            quantity=dlg.quantity())

        self._addCurrentCargo(cargoRecord)

    def _promptEditCurrentCargo(self) -> None:
        row = self._currentCargoTable.currentRow()
        if row < 0:
            gui.MessageBoxEx.information(
                parent=self,
                text='Select the cargo to edit')
            return

        cargoRecord = self._currentCargoTable.cargoRecord(row)
        pricePerTon = cargoRecord.pricePerTon()
        assert(isinstance(pricePerTon, common.ScalarCalculation))
        quantity = cargoRecord.quantity()
        assert(isinstance(quantity, common.ScalarCalculation))

        dlg = gui.ScalarCargoDetailsDialog(
            title='Edit Current Cargo',
            world=self._purchaseWorldWidget.world(),
            editTradeGood=cargoRecord.tradeGood(),
            editPricePerTon=pricePerTon,
            editQuantity=quantity)
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return

        cargoRecord = logic.CargoRecord(
            tradeGood=dlg.tradeGood(),
            pricePerTon=dlg.pricePerTon(),
            quantity=dlg.quantity())

        self._currentCargoTable.setCargoRecord(row, cargoRecord)
        self._updateSaleWorldTradeScores()

    def _showCurrentCargoTableContextMenu(self, position: QtCore.QPoint) -> None:
        menuItems = [
            gui.MenuItem(
                text='Add Cargo...',
                callback=lambda: self._promptAddCurrentCargo(),
                enabled=True
            ),
            gui.MenuItem(
                text='Edit Cargo...',
                callback=lambda: self._promptEditCurrentCargo(),
                enabled=self._currentCargoTable.hasSelection()
            ),
            gui.MenuItem(
                text='Remove Selected Cargo',
                callback=lambda: self._removeSelectedCurrentCargo(),
                enabled=self._currentCargoTable.hasSelection()
            ),
            gui.MenuItem(
                text='Remove All Cargo',
                callback=lambda: self._removeAllCurrentCargo(),
                enabled=not self._currentCargoTable.isEmpty()
            ),
            None, # Separator
            gui.MenuItem(
                text='Show Calculations...',
                callback=lambda: self._showCargoRecordCalculations(self._currentCargoTable.currentCargoRecord()),
                enabled=self._currentCargoTable.hasSelection()
            )
        ]

        gui.displayMenu(
            self,
            menuItems,
            self._currentCargoTable.viewport().mapToGlobal(position)
        )

    def _currentCargoTableKeyPressed(self, key: int) -> None:
        if key == QtCore.Qt.Key.Key_Delete:
            self._removeSelectedCurrentCargo()

    def _calculateTradeOptions(self) -> None:
        if self._traderJob:
            # A trade option job is already running so cancel it
            self._traderJob.cancel()
            return

        if self._speculativeCargoTable.isEmpty() and \
                self._availableCargoTable.isEmpty() and \
                self._currentCargoTable.isEmpty():
            gui.MessageBoxEx.information(
                parent=self,
                text='No cargo added')
            return

        if not self._speculativeCargoTable.isEmpty() or not self._availableCargoTable.isEmpty():
            if self._availableFundsSpinBox.value() <= 0:
                gui.MessageBoxEx.information(
                    parent=self,
                    text='Available funds can\'t be zero when calculating trade options for speculative and available cargo')
                return
            if self._freeCargoSpaceSpinBox.value() <= 0:
                gui.MessageBoxEx.information(
                    parent=self,
                    text='Free cargo can\'t be zero when calculating trade options for speculative and available cargo')
                return

        if self._saleWorldsWidget.isEmpty():
            gui.MessageBoxEx.information(
                parent=self,
                text='No sale worlds selected')
            return

        if self._shipFuelCapacitySpinBox.value() > self._shipTonnageSpinBox.value():
            gui.MessageBoxEx.information(
                parent=self,
                text='Ship\'s fuel capacity can\'t be larger than its total tonnage')
            return
        if self._shipCurrentFuelSpinBox.value() > self._shipFuelCapacitySpinBox.value():
            gui.MessageBoxEx.information(
                parent=self,
                text='Ship\'s current fuel can\'t be larger than its fuel capacity')
            return
        if self._freeCargoSpaceSpinBox.value() > self._shipTonnageSpinBox.value():
            gui.MessageBoxEx.information(
                parent=self,
                text='Ship\'s free cargo capacity can\'t be larger than its total tonnage')
            return
        if (self._shipFuelCapacitySpinBox.value() + self._freeCargoSpaceSpinBox.value()) > \
                self._shipTonnageSpinBox.value():
            gui.MessageBoxEx.information(
                parent=self,
                text='Ship\'s combined fuel and free cargo capacities can\'t be larger than its total tonnage')
            return
        
        # Flag cases where the purchase world doesn't match the refuelling strategy. No options will be
        # generated unless the ship has enough current fuel
        if not logic.selectRefuellingType(
                world=self._purchaseWorldWidget.world(),
                refuellingStrategy=self._refuellingStrategyComboBox.currentEnum()):
            message = f'The purchase world doesn\'t support the selected refuelling strategy. ' \
                'It will only be possibly to generate trade options for sale worlds where a route can be found with the specified current fuel amount.'  

            answer = gui.MessageBoxEx.question(
                parent=self,
                text=message + '\n\nDo you want to continue?') 
            if answer == QtWidgets.QMessageBox.StandardButton.No:
                return        

        # Create a jump cost calculator for the selected route optimisation
        routeOptimisation = self._routeOptimisationComboBox.currentEnum()
        if routeOptimisation == logic.RouteOptimisation.ShortestDistance:
            jumpCostCalculator = logic.ShortestDistanceCostCalculator()
        elif routeOptimisation == logic.RouteOptimisation.ShortestTime:
            jumpCostCalculator = logic.ShortestTimeCostCalculator()
        elif routeOptimisation == logic.RouteOptimisation.LowestCost:
            jumpCostCalculator = logic.CheapestRouteCostCalculator(
                shipTonnage=self._shipTonnageSpinBox.value(),
                shipFuelCapacity=self._shipFuelCapacitySpinBox.value(),
                shipCurrentFuel=self._shipCurrentFuelSpinBox.value(),
                shipFuelPerParsec=self._shipFuelPerParsecSpinBox.value(),
                refuellingStrategy=self._refuellingStrategyComboBox.currentEnum(),
                perJumpOverheads=self._perJumpOverheadsSpinBox.value())
        else:
            assert(False) # I've missed an enum

        self._progressLabel.clear()
        self._tradeOptionCountLabel.clear()
        self._tradeOptionsTable.removeAllRows()
        self._tradeInfoEditBox.clear()

        try:
            self._traderJob = jobs.SingleWorldTraderJob(
                parent=self,
                rules=app.Config.instance().rules(),
                purchaseWorld=self._purchaseWorldWidget.world(),
                saleWorlds=self._saleWorldsWidget.worlds(),
                currentCargo=self._currentCargoTable.cargoRecords(),
                possibleCargo=self._speculativeCargoTable.cargoRecords() + self._availableCargoTable.cargoRecords(),
                playerBrokerDm=self._playerBrokerDmSpinBox.value(),
                useLocalSaleBroker=self._localSaleBrokerWidget.isChecked(),
                localSaleBrokerDm=self._localSaleBrokerWidget.value(),
                minBuyerDm=self._buyerDmRangeWidget.lowerValue(),
                maxBuyerDm=self._buyerDmRangeWidget.upperValue(),
                availableFunds=self._availableFundsSpinBox.value(),
                shipTonnage=self._shipTonnageSpinBox.value(),
                shipJumpRating=self._shipJumpRatingSpinBox.value(),
                shipFuelCapacity=self._shipFuelCapacitySpinBox.value(),
                shipStartingFuel=self._shipCurrentFuelSpinBox.value(),
                shipFuelPerParsec=self._shipFuelPerParsecSpinBox.value(),
                shipCargoCapacity=self._freeCargoSpaceSpinBox.value(),
                perJumpOverheads=self._perJumpOverheadsSpinBox.value(),
                jumpCostCalculator=jumpCostCalculator,
                refuellingStrategy=self._refuellingStrategyComboBox.currentEnum(),
                includePurchaseWorldBerthing=self._includeStartWorldBerthingCheckBox.isChecked(),
                includeSaleWorldBerthing=self._includeFinishWorldBerthingCheckBox.isChecked(),
                includeUnprofitableTrades=self._includeUnprofitableTradesCheckBox.isChecked(),
                includeLogisticsCosts=self._includeLogisticsCostsCheckBox.isChecked(),
                tradeOptionCallback=self._addTradeOptions,
                tradeInfoCallback=self._addTraderInfo,
                progressCallback=self._updateTraderProgress,
                finishedCallback=self._traderFinished)
        except Exception as ex:
            message = 'Failed to start trader job'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

        self._calculateTradeOptionsButton.showSecondaryText()
        self._enableDisableControls()

    def _createCargoManifest(self) -> None:
        speculativeCargoLookup = set(self._speculativeCargoTable.cargoRecords())
        availableCargoLookup = set(self._availableCargoTable.cargoRecords())

        speculativeCargoTrades = []
        availableCargoTrades = []
        for tradeOption in self._tradeOptionsTable.tradeOptions():
            cargoRecord = tradeOption.originalCargoRecord()
            if cargoRecord in speculativeCargoLookup:
                speculativeCargoTrades.append(tradeOption)
            elif cargoRecord in availableCargoLookup:
                availableCargoTrades.append(tradeOption)

        if not speculativeCargoTrades and not availableCargoTrades:
            gui.MessageBoxEx.information(
                parent=self,
                text='No trade options for speculative or available cargo to generate cargo manifest from')
            return
        if speculativeCargoTrades and availableCargoTrades:
            gui.MessageBoxEx.information(
                parent=self,
                text='You can\'t create a cargo manifest from trade options generated using both speculative and available cargo')
            return

        dlg = gui.CargoManifestDialog(
            availableFunds=self._availableFundsSpinBox.value(),
            freeCargoSpace=self._freeCargoSpaceSpinBox.value(),
            tradeOptions=availableCargoTrades if availableCargoTrades else speculativeCargoTrades,
            speculativePurchase=not availableCargoTrades,
            parent=self)
        dlg.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        dlg.finished.connect(lambda result: self._cargoManifestDialogClosed(dlg, result))
        dlg.open()

    def _cargoManifestDialogClosed(
            self,
            dlg: gui.CargoManifestDialog,
            result: int
            ) -> None:
        if not dlg.isPurchaseSelectedChecked():
            return # Nothing more to do

        cargoManifest = dlg.selectedCargoManifest()
        if not cargoManifest:
            gui.MessageBoxEx.information(
                parent=self,
                text='No cargo manifest selected')
            return

        for tradeOption in cargoManifest.tradeOptions():
            cargoRecord = logic.CargoRecord(
                tradeGood=tradeOption.tradeGood(),
                pricePerTon=tradeOption.purchasePricePerTon(),
                quantity=tradeOption.cargoQuantity())
            self._addCurrentCargo(cargoRecord)

        # This function should only ever be called when available cargo has been used to generate
        # the cargo manifest and therefore, the total cargo cost and quantity should be known values
        assert(isinstance(cargoManifest.cargoCost(), common.ScalarCalculation))
        assert(isinstance(cargoManifest.cargoQuantity(), common.ScalarCalculation))

        # Update available funds and cargo capacity
        self._availableFundsSpinBox.setValue(
            self._availableFundsSpinBox.value() - int(cargoManifest.cargoCost().value()))
        self._freeCargoSpaceSpinBox.setValue(
            self._freeCargoSpaceSpinBox.value() - int(cargoManifest.cargoQuantity().value()))

    def _showWelcomeMessage(self) -> None:
        message = gui.InfoDialog(
            title=self.windowTitle(),
            html=_WorldWelcomeMessage,
            noShowAgainId='WorldTraderWelcome')
        message.exec()


# ██████   ██████            ████   █████     ███     █████   ███   █████                    ████      █████    ███████████                         █████
#░░██████ ██████            ░░███  ░░███     ░░░     ░░███   ░███  ░░███                    ░░███     ░░███    ░█░░░███░░░█                        ░░███
# ░███░█████░███  █████ ████ ░███  ███████   ████     ░███   ░███   ░███   ██████  ████████  ░███   ███████    ░   ░███  ░  ████████   ██████    ███████   ██████  ████████
# ░███░░███ ░███ ░░███ ░███  ░███ ░░░███░   ░░███     ░███   ░███   ░███  ███░░███░░███░░███ ░███  ███░░███        ░███    ░░███░░███ ░░░░░███  ███░░███  ███░░███░░███░░███
# ░███ ░░░  ░███  ░███ ░███  ░███   ░███     ░███     ░░███  █████  ███  ░███ ░███ ░███ ░░░  ░███ ░███ ░███        ░███     ░███ ░░░   ███████ ░███ ░███ ░███████  ░███ ░░░
# ░███      ░███  ░███ ░███  ░███   ░███ ███ ░███      ░░░█████░█████░   ░███ ░███ ░███      ░███ ░███ ░███        ░███     ░███      ███░░███ ░███ ░███ ░███░░░   ░███
# █████     █████ ░░████████ █████  ░░█████  █████       ░░███ ░░███     ░░██████  █████     █████░░████████       █████    █████    ░░████████░░████████░░██████  █████
#░░░░░     ░░░░░   ░░░░░░░░ ░░░░░    ░░░░░  ░░░░░         ░░░   ░░░       ░░░░░░  ░░░░░     ░░░░░  ░░░░░░░░       ░░░░░    ░░░░░      ░░░░░░░░  ░░░░░░░░  ░░░░░░  ░░░░░

_MultiWorldWelcomeMessage = """
    <html>
    <p>The Multi World Trade window is intended as an aid to help players find potential trade
    routes between a set of worlds. It can be used to give a guide to the profit they could expect
    to see and how it would be affected by different variables in the trading process.</p>
    <p>Currently, only Mongoose 1e & 2e rules are supported. Which rules are used can be selected in
    the Configuration dialog. Data from Traveller Map is used for calculating Sale & Purchase DMs
    for the worlds and logistics costs for travel between them.</p>
    <p>Although the Mongoose rules are simple enough that they can be condensed onto a few pages,
    they are complex enough that predicting if a trade even has a chance of being profitable can
    be non-trivial. This is especially true when you introduce things like local brokers and
    logistics costs.<br>
    To help with this problem, {name} uses an implementation of the trading rules to estimate the
    profit/loss the player would expect to see if the player were to make the worst case, best case
    and average dice rolls at all points in the trading process.<br>
    The most interesting of the 3 values is the average value as this can be used to gauge if a
    trade is likely to be profitable or not. The worst case and best case dice roll values are less
    interesting, however they can be used as a guide to the range of profit/loss the player would
    expect to see.</p>
    <p>The seller and buyer DM bonuses used in the trading processes are determined by the Referee
    rather than dice rolls. In order to take these values into account, {name} allows the player to
    specify ranges of what they expect these values to be. For "professional" sellers/buyers it
    would seem logical that these values would generally fall in the range 0-4. The lower extent,
    upper extent and average of the specified ranges are used by the trading engine when estimating
    estimating the best case, worst case and average case profits respectively.
    <pr>For each selected purchase world, its Trade Codes are used to determine what Trade Goods
    will generally be available (randomly available Trade Goods aren't included). The players broker
    skill, seller DM range and the purchase world's Trade Codes are then used to estimate the worst
    case, best case and average purchase price and available tonnage for those Trade Goods. The
    trading engine determines how much of this potentially available cargo could be purchased based
    on available funds and ship cargo capacity. Then for each of the selected sale worlds it uses
    the player's broker skill, buyer DM range and sale world Trade Codes to estimates how much the
    quantity of cargo could be sold for, with the purchase price (and any logistics costs) then used
    to estimate profit.</p>
    </html>
""".format(name=app.AppName)

class MultiWorldTraderWindow(_BaseTraderWindow):
    def __init__(self) -> None:
        super().__init__(
            title='Multi World Trader',
            configSection='MultiWorldTraderWindow')

        self._setupConfigurationControls()
        self._setupPurchaseWorldControls()
        self._setupSaleWorldControls()
        self._setupTradeOptionControls()
        self._setupTradeInfoControls()

        self._enableDisableControls()

        self._tableSplitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        self._tableSplitter.addWidget(self._purchaseWorldsGroupBox)
        self._tableSplitter.addWidget(self._saleWorldsGroupBox)

        leftLayout = QtWidgets.QVBoxLayout()
        leftLayout.setContentsMargins(0, 0, 0, 0)
        leftLayout.addWidget(self._configurationGroupBox, 0)
        leftLayout.addWidget(self._tableSplitter, 1)
        leftWidget = QtWidgets.QWidget()
        leftWidget.setLayout(leftLayout)

        self._mainSplitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self._mainSplitter.addWidget(leftWidget)
        self._mainSplitter.addWidget(self._tradeOptionsGroupBox)

        self._tradeInfoSplitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        self._tradeInfoSplitter.addWidget(self._mainSplitter)
        self._tradeInfoSplitter.addWidget(self._tradeInfoEditBox)

        windowLayout = QtWidgets.QVBoxLayout()
        windowLayout.addWidget(self._tradeInfoSplitter)

        self.setLayout(windowLayout)

    def configureControls(
            self,
            purchaseWorlds: typing.Optional[typing.Iterable[traveller.World]] = None,
            saleWorlds: typing.Optional[typing.Iterable[traveller.World]] = None,
            playerBrokerDm: typing.Optional[int] = None,
            minSellerDm: typing.Optional[int] = None,
            maxSellerDm: typing.Optional[int] = None,
            minBuyerDm: typing.Optional[int] = None,
            maxBuyerDm: typing.Optional[int] = None,
            availableFunds: typing.Optional[int] = None,
            shipTonnage: typing.Optional[int] = None,
            shipJumpRating: typing.Optional[int] = None,
            freeCargoSpace: typing.Optional[int] = None,
            shipFuelCapacity: typing.Optional[int] = None,
            shipCurrentFuel: typing.Optional[int] = None,
            perJumpOverheads: typing.Optional[int] = None,
            refuellingStrategy: typing.Optional[logic.RefuellingStrategy] = None
            ) -> None:
        if self._traderJob:
            raise RuntimeError('Unable to setup trader window while a trade options job is in progress')

        if playerBrokerDm != None:
            self._playerBrokerDmSpinBox.setValue(int(playerBrokerDm))
        if minSellerDm != None:
            self._sellerDmRangeWidget.setLowerValue(int(minSellerDm))
        if maxSellerDm != None:
            self._sellerDmRangeWidget.setUpperValue(int(maxSellerDm))
        if minBuyerDm != None:
            self._buyerDmRangeWidget.setLowerValue(int(minBuyerDm))
        if maxBuyerDm != None:
            self._buyerDmRangeWidget.setUpperValue(int(maxBuyerDm))
        if availableFunds != None:
            self._availableFundsSpinBox.setValue(int(availableFunds))
        if shipTonnage != None:
            self._shipTonnageSpinBox.setValue(int(shipTonnage))
        if shipJumpRating != None:
            self._shipJumpRatingSpinBox.setValue(int(shipJumpRating))
        if shipFuelCapacity != None:
            self._shipFuelCapacitySpinBox.setValue(int(shipFuelCapacity))
        if shipCurrentFuel != None:
            self._shipCurrentFuelSpinBox.setValue(int(shipCurrentFuel))
        if freeCargoSpace != None:
            self._freeCargoSpaceSpinBox.setValue(int(freeCargoSpace))
        if refuellingStrategy != None:
            self._refuellingStrategyComboBox.setCurrentEnum(refuellingStrategy)
        if perJumpOverheads != None:
            self._perJumpOverheadsSpinBox.setValue(int(perJumpOverheads))
        if purchaseWorlds != None:
            self._purchaseWorldsWidget.removeAllWorlds()
            self._purchaseWorldsWidget.addWorlds(worlds=purchaseWorlds)
        if saleWorlds != None:
            self._saleWorldsWidget.removeAllWorlds()
            self._saleWorldsWidget.addWorlds(worlds=saleWorlds)

    def loadSettings(self) -> None:
        super().loadSettings()

        self._settings.beginGroup(self._configSection)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='IncludeIllegal',
            type=QtCore.QByteArray)
        if storedValue:
            self._includeIllegalTradeGoodsCheckBox.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='PurchaseWorldsTableState',
            type=QtCore.QByteArray)
        if storedValue:
            self._purchaseWorldsWidget.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='PurchaseWorldsTableContent',
            type=QtCore.QByteArray)
        if storedValue:
            self._purchaseWorldsWidget.restoreContent(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='SaleWorldsTableState',
            type=QtCore.QByteArray)
        if storedValue:
            self._saleWorldsWidget.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='SaleWorldsTableContent',
            type=QtCore.QByteArray)
        if storedValue:
            self._saleWorldsWidget.restoreContent(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='MainSplitterState',
            type=QtCore.QByteArray)
        if storedValue:
            self._mainSplitter.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='TableSplitterState',
            type=QtCore.QByteArray)
        if storedValue:
            self._tableSplitter.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='TradeInfoSplitterState',
            type=QtCore.QByteArray)
        if storedValue:
            self._tradeInfoSplitter.restoreState(storedValue)

        self._settings.endGroup()

    def saveSettings(self) -> None:
        self._settings.beginGroup(self._configSection)
        self._settings.setValue('IncludeIllegal', self._includeIllegalTradeGoodsCheckBox.saveState())
        self._settings.setValue('PurchaseWorldsTableState', self._purchaseWorldsWidget.saveState())
        self._settings.setValue('PurchaseWorldsTableContent', self._purchaseWorldsWidget.saveContent())
        self._settings.setValue('SaleWorldsTableState', self._saleWorldsWidget.saveState())
        self._settings.setValue('SaleWorldsTableContent', self._saleWorldsWidget.saveContent())
        self._settings.setValue('MainSplitterState', self._mainSplitter.saveState())
        self._settings.setValue('TableSplitterState', self._tableSplitter.saveState())
        self._settings.setValue('TradeInfoSplitterState', self._tradeInfoSplitter.saveState())
        self._settings.endGroup()

        super().saveSettings()

    def _setupConfigurationControls(self) -> None:
        super()._setupConfigurationControls()

        # An an include illegal check box before the include unprofitable check box in the options
        # layout. This is not a shared check box as there are no other widgets to share it with
        self._includeIllegalTradeGoodsCheckBox = gui.CheckBoxEx()
        self._rightOptionsLayout.insertRow(
            self._rightOptionsLayout.rowCount() - 1,
            QtWidgets.QLabel('Include Illegal Trade Goods:'),
            self._includeIllegalTradeGoodsCheckBox)

    def _setupSaleWorldControls(self) -> None:
        self._saleWorldsWidget = gui.WorldTableManagerWidget(
            allowWorldCallback=self._allowSaleWorld)
        self._saleWorldsWidget.enableContextMenuEvent(True)
        self._saleWorldsWidget.contextMenuRequested.connect(self._showSaleWorldTableContextMenu)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self._saleWorldsWidget)

        self._saleWorldsGroupBox = QtWidgets.QGroupBox('Sale Worlds')
        self._saleWorldsGroupBox.setLayout(layout)

    def _setupPurchaseWorldControls(self) -> None:
        self._purchaseWorldsWidget = gui.WorldTableManagerWidget(
            allowWorldCallback=self._allowPurchaseWorld)
        self._purchaseWorldsWidget.enableContextMenuEvent(True)
        self._purchaseWorldsWidget.contextMenuRequested.connect(self._showPurchaseWorldTableContextMenu)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self._purchaseWorldsWidget)

        self._purchaseWorldsGroupBox = QtWidgets.QGroupBox('Purchase Worlds')
        self._purchaseWorldsGroupBox.setLayout(layout)

    def _enableDisableControls(self) -> None:
        if not self._traderJob:
            self._configurationGroupBox.setDisabled(False)
            self._purchaseWorldsGroupBox.setDisabled(False)
            self._saleWorldsGroupBox.setDisabled(False)
        else:
            # Disable configuration controls while trade option job is running
            self._configurationGroupBox.setDisabled(True)
            self._purchaseWorldsGroupBox.setDisabled(True)
            self._saleWorldsGroupBox.setDisabled(True)

    def _allowPurchaseWorld(self, world: traveller.World) -> bool:
        # Silently ignore worlds that are already in the table
        return not self._purchaseWorldsWidget.containsWorld(world)

    def _allowSaleWorld(self, world: traveller.World) -> bool:
        # Silently ignore worlds that are already in the table
        return not self._saleWorldsWidget.containsWorld(world)

    def _copyBetweenWorldWidgets(
            self,
            srcWidget: gui.WorldTableManagerWidget,
            dstWidget: gui.WorldTableManagerWidget
            ) -> None:
        if dstWidget.worldCount() > 0:
            answer = gui.MessageBoxEx.question(
                parent=self,
                text='Remove current worlds before copying?')
            if answer == QtWidgets.QMessageBox.StandardButton.Yes:
                dstWidget.removeAllWorlds()
        dstWidget.addWorlds(worlds=srcWidget.worlds())

    def _showPurchaseWorldTableContextMenu(self, position: QtCore.QPoint) -> None:
        world = self._purchaseWorldsWidget.worldAt(position=position)

        menuItems = [
            gui.MenuItem(
                text='Select Worlds with Traveller Map...',
                callback=lambda: self._purchaseWorldsWidget.promptSelectWithTravellerMap(),
                enabled=True
            ),
            None, # Separator
            gui.MenuItem(
                text='Add World...',
                callback=lambda: self._purchaseWorldsWidget.promptAddWorld(),
                enabled=True
            ),
            gui.MenuItem(
                text='Add Nearby Worlds...',
                callback=lambda: self._purchaseWorldsWidget.promptAddNearbyWorlds(initialWorld=world),
                enabled=True
            ),
            gui.MenuItem(
                text='Remove Selected Worlds',
                callback=lambda: self._purchaseWorldsWidget.removeSelectedWorlds(),
                enabled=self._purchaseWorldsWidget.hasSelection()
            ),
            gui.MenuItem(
                text='Remove All Worlds',
                callback=lambda: self._purchaseWorldsWidget.removeAllWorlds(),
                enabled=self._purchaseWorldsWidget.worldCount() > 0
            ),
            None, # Separator
            gui.MenuItem(
                text='Copy Sale Worlds',
                callback=lambda: self._copyBetweenWorldWidgets(srcWidget=self._saleWorldsWidget, dstWidget=self._purchaseWorldsWidget),
                enabled=self._saleWorldsWidget.worldCount() > 0
            ),
            None, # Separator
            gui.MenuItem(
                text='Show Selected World Details...',
                callback=lambda: self._showWorldDetails(worlds=self._purchaseWorldsWidget.selectedWorlds()),
                enabled=self._purchaseWorldsWidget.hasSelection()
            ),
            gui.MenuItem(
                text='Show All World Details...',
                callback=lambda: self._showWorldDetails(worlds=self._purchaseWorldsWidget.worlds()),
                enabled=self._purchaseWorldsWidget.worldCount() > 0
            ),
            None, # Separator
            gui.MenuItem(
                text='Show Selected Worlds in Traveller Map...',
                callback=lambda: self._showWorldsInTravellerMap(worlds=self._purchaseWorldsWidget.selectedWorlds()),
                enabled=self._purchaseWorldsWidget.hasSelection()
            ),
            gui.MenuItem(
                text='Show All Worlds in Traveller Map...',
                callback=lambda: self._showWorldsInTravellerMap(worlds=self._purchaseWorldsWidget.worlds()),
                enabled=self._purchaseWorldsWidget.worldCount() > 0
            )
        ]

        gui.displayMenu(
            self,
            menuItems,
            self._purchaseWorldsWidget.mapToGlobal(position)
        )

    def _showSaleWorldTableContextMenu(self, position: QtCore.QPoint) -> None:
        world = self._saleWorldsWidget.worldAt(position=position)

        menuItems = [
            gui.MenuItem(
                text='Select Worlds with Traveller Map...',
                callback=lambda: self._saleWorldsWidget.promptSelectWithTravellerMap(),
                enabled=True
            ),
            None, # Separator
            gui.MenuItem(
                text='Add World...',
                callback=lambda: self._saleWorldsWidget.promptAddWorld(),
                enabled=True
            ),
            gui.MenuItem(
                text='Add Nearby Worlds...',
                callback=lambda: self._saleWorldsWidget.promptAddNearbyWorlds(initialWorld=world),
                enabled=True
            ),
            gui.MenuItem(
                text='Remove Selected Worlds',
                callback=lambda: self._saleWorldsWidget.removeSelectedWorlds(),
                enabled=self._saleWorldsWidget.hasSelection()
            ),
            gui.MenuItem(
                text='Remove All Worlds',
                callback=lambda: self._saleWorldsWidget.removeAllWorlds(),
                enabled=self._saleWorldsWidget.worldCount() > 0
            ),
            None, # Separator
            gui.MenuItem(
                text='Copy Purchase Worlds',
                callback=lambda: self._copyBetweenWorldWidgets(srcWidget=self._purchaseWorldsWidget, dstWidget=self._saleWorldsWidget),
                enabled=self._purchaseWorldsWidget.worldCount() > 0
            ),
            None, # Separator
            gui.MenuItem(
                text='Show Selected World Details...',
                callback=lambda: self._showWorldDetails(worlds=self._saleWorldsWidget.selectedWorlds()),
                enabled=self._saleWorldsWidget.hasSelection()
            ),
            gui.MenuItem(
                text='Show All World Details...',
                callback=lambda: self._showWorldDetails(worlds=self._saleWorldsWidget.worlds()),
                enabled=self._saleWorldsWidget.worldCount() > 0
            ),
            None, # Separator
            gui.MenuItem(
                text='Show Selected Worlds in Traveller Map...',
                callback=lambda: self._showWorldsInTravellerMap(worlds=self._saleWorldsWidget.selectedWorlds()),
                enabled=self._saleWorldsWidget.hasSelection()
            ),
            gui.MenuItem(
                text='Show All Worlds in Traveller Map...',
                callback=lambda: self._showWorldsInTravellerMap(worlds=self._saleWorldsWidget.worlds()),
                enabled=self._saleWorldsWidget.worldCount() > 0
            )
        ]

        gui.displayMenu(
            self,
            menuItems,
            self._saleWorldsWidget.mapToGlobal(position)
        )

    def _calculateTradeOptions(self) -> None:
        if self._traderJob:
            # A trade option job is already running so cancel it
            self._traderJob.cancel()
            return

        if self._availableFundsSpinBox.value() <= 0:
            gui.MessageBoxEx.information(
                parent=self,
                text='Available funds can\'t be zero')
            return

        if self._purchaseWorldsWidget.isEmpty():
            gui.MessageBoxEx.information(
                parent=self,
                text='No purchase worlds selected')
            return

        if self._saleWorldsWidget.isEmpty():
            gui.MessageBoxEx.information(
                parent=self,
                text='No sale worlds selected')
            return

        if self._freeCargoSpaceSpinBox.value() <= 0:
            gui.MessageBoxEx.information(
                parent=self,
                text='No free cargo space')
            return

        if self._shipFuelCapacitySpinBox.value() > self._shipTonnageSpinBox.value():
            gui.MessageBoxEx.information(
                parent=self,
                text='Ship\'s fuel capacity can\'t be larger than its total tonnage')
            return
        if self._shipCurrentFuelSpinBox.value() > self._shipFuelCapacitySpinBox.value():
            gui.MessageBoxEx.information(
                parent=self,
                text='Ship\'s current fuel can\'t be larger than its fuel capacity')
            return
        if self._freeCargoSpaceSpinBox.value() > self._shipTonnageSpinBox.value():
            gui.MessageBoxEx.information(
                parent=self,
                text='Ship\'s free cargo capacity can\'t be larger than its total tonnage')
            return
        if (self._shipFuelCapacitySpinBox.value() + self._freeCargoSpaceSpinBox.value()) > \
                self._shipTonnageSpinBox.value():
            gui.MessageBoxEx.information(
                parent=self,
                text='Ship\'s combined fuel and free cargo capacities can\'t be larger than its total tonnage')
            return
        
        # Flag cases where purchase worlds don't match the refuelling strategy. No options will be
        # generated for those worlds unless the ship has enough current fuel
        fuelIssueWorldStrings = []
        for world in self._purchaseWorldsWidget.worlds():
            if not logic.selectRefuellingType(
                    world=world,
                    refuellingStrategy=self._refuellingStrategyComboBox.currentEnum()):
                fuelIssueWorldStrings.append(world.name())

        if fuelIssueWorldStrings:
            worldListString = common.humanFriendlyListString(fuelIssueWorldStrings)
            if len(fuelIssueWorldStrings) == 1:
                message = f'Waypoint {worldListString} doesn\'t support the selected refuelling strategy. '
            else:
                message = f'Waypoints {worldListString} don\'t support the selected refuelling strategy. '
            message += 'It will only be possibly to generate trade options for sale worlds where a route can be found with the specified current fuel amount.'  

            answer = gui.MessageBoxEx.question(
                parent=self,
                text=message + '\n\nDo you want to continue?')
            if answer == QtWidgets.QMessageBox.StandardButton.No:
                return
            
        # Create a jump cost calculator for the selected route optimisation
        routeOptimisation = self._routeOptimisationComboBox.currentEnum()
        if routeOptimisation == logic.RouteOptimisation.ShortestDistance:
            jumpCostCalculator = logic.ShortestDistanceCostCalculator()
        elif routeOptimisation == logic.RouteOptimisation.ShortestTime:
            jumpCostCalculator = logic.ShortestTimeCostCalculator()
        elif routeOptimisation == logic.RouteOptimisation.LowestCost:
            jumpCostCalculator = logic.CheapestRouteCostCalculator(
                shipTonnage=self._shipTonnageSpinBox.value(),
                shipFuelCapacity=self._shipFuelCapacitySpinBox.value(),
                shipCurrentFuel=self._shipCurrentFuelSpinBox.value(),
                shipFuelPerParsec=self._shipFuelPerParsecSpinBox.value(),
                refuellingStrategy=self._refuellingStrategyComboBox.currentEnum(),
                perJumpOverheads=self._perJumpOverheadsSpinBox.value())
        else:
            assert(False) # I've missed an enum

        self._progressLabel.clear()
        self._tradeOptionCountLabel.clear()
        self._tradeOptionsTable.removeAllRows()
        self._tradeInfoEditBox.clear()

        try:
            self._traderJob = jobs.MultiWorldTraderJob(
                parent=self,
                rules=app.Config.instance().rules(),
                purchaseWorlds=self._purchaseWorldsWidget.worlds(),
                saleWorlds=self._saleWorldsWidget.worlds(),
                playerBrokerDm=self._playerBrokerDmSpinBox.value(),
                useLocalPurchaseBroker=self._localPurchaseBrokerWidget.isChecked(),
                localPurchaseBrokerDm=self._localPurchaseBrokerWidget.value(),
                useLocalSaleBroker=self._localSaleBrokerWidget.isChecked(),
                localSaleBrokerDm=self._localSaleBrokerWidget.value(),
                minSellerDm=self._sellerDmRangeWidget.lowerValue(),
                maxSellerDm=self._sellerDmRangeWidget.upperValue(),
                minBuyerDm=self._buyerDmRangeWidget.lowerValue(),
                maxBuyerDm=self._buyerDmRangeWidget.upperValue(),
                availableFunds=self._availableFundsSpinBox.value(),
                shipTonnage=self._shipTonnageSpinBox.value(),
                shipJumpRating=self._shipJumpRatingSpinBox.value(),
                shipFuelCapacity=self._shipFuelCapacitySpinBox.value(),
                shipStartingFuel=self._shipCurrentFuelSpinBox.value(),
                shipFuelPerParsec=self._shipFuelPerParsecSpinBox.value(),
                shipCargoCapacity=self._freeCargoSpaceSpinBox.value(),
                perJumpOverheads=self._perJumpOverheadsSpinBox.value(),
                jumpCostCalculator=jumpCostCalculator,
                refuellingStrategy=self._refuellingStrategyComboBox.currentEnum(),
                includeIllegal=self._includeIllegalTradeGoodsCheckBox.isChecked(),
                includePurchaseWorldBerthing=self._includeStartWorldBerthingCheckBox.isChecked(),
                includeSaleWorldBerthing=self._includeFinishWorldBerthingCheckBox.isChecked(),
                includeUnprofitableTrades=self._includeUnprofitableTradesCheckBox.isChecked(),
                includeLogisticsCosts=self._includeLogisticsCostsCheckBox.isChecked(),
                tradeOptionCallback=self._addTradeOptions,
                tradeInfoCallback=self._addTraderInfo,
                progressCallback=self._updateTraderProgress,
                finishedCallback=self._traderFinished)
        except Exception as ex:
            message = 'Failed to start trader job'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

        self._calculateTradeOptionsButton.showSecondaryText()
        self._enableDisableControls()

    def _createCargoManifest(self) -> None:
        if self._tradeOptionsTable.isEmpty():
            gui.MessageBoxEx.information(
                parent=self,
                text='No trade options to generate cargo manifest from')
            return

        dlg = gui.CargoManifestDialog(
            availableFunds=self._availableFundsSpinBox.value(),
            freeCargoSpace=self._freeCargoSpaceSpinBox.value(),
            tradeOptions=self._tradeOptionsTable.tradeOptions(),
            speculativePurchase=True) # Multi world trade option calculations are always speculative
        dlg.exec()

    def _showWelcomeMessage(self) -> None:
        message = gui.InfoDialog(
            title=self.windowTitle(),
            html=_MultiWorldWelcomeMessage,
            noShowAgainId='MultiWorldTraderWelcome')
        message.exec()
