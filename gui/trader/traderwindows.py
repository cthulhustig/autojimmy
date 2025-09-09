import app
import common
import gui
import jobs
import logging
import logic
import traveller
import multiverse
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

def _worldSaleScoreTableColumns(
        originalColumns: typing.List[gui.HexTable.ColumnType]
        ) -> typing.List[typing.Union[gui.WorldTradeScoreTableColumnType, gui.HexTable.ColumnType]]:
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
            milieu: multiverse.Milieu,
            rules: traveller.Rules,
            worldTagging: typing.Optional[logic.WorldTagging] = None,
            taggingColours: typing.Optional[app.TaggingColours] = None,
            columns: typing.Iterable[typing.Union[gui.WorldTradeScoreTableColumnType, gui.HexTable.ColumnType]] = AllColumns) -> None:
        super().__init__(
            milieu=milieu,
            rules=rules,
            worldTagging=worldTagging,
            taggingColours=taggingColours,
            columns=columns)


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

        self._hexTooltipProvider = gui.HexTooltipProvider(
            milieu=app.Config.instance().value(option=app.ConfigOption.Milieu),
            rules=app.Config.instance().value(option=app.ConfigOption.Rules),
            showImages=app.Config.instance().value(option=app.ConfigOption.ShowToolTipImages),
            mapStyle=app.Config.instance().value(option=app.ConfigOption.MapStyle),
            mapOptions=app.Config.instance().value(option=app.ConfigOption.MapOptions),
            worldTagging=app.Config.instance().value(option=app.ConfigOption.WorldTagging),
            taggingColours=app.Config.instance().value(option=app.ConfigOption.TaggingColours))

        self._traderJob: typing.Optional[jobs.TraderJobBase] = None

        app.Config.instance().configChanged.connect(self._appConfigChanged)

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
        self._availableFundsSpinBox = gui.AvailableFundsSpinBox(
            value=app.Config.instance().value(option=app.ConfigOption.AvailableFunds))
        self._availableFundsSpinBox.valueChanged.connect(self._availableFundsChanged)

        self._maxCargoTonnageSpinBox = gui.MaxCargoTonnageSpinBox(
            value=app.Config.instance().value(option=app.ConfigOption.MaxCargoTonnage))
        self._maxCargoTonnageSpinBox.valueChanged.connect(self._maxCargoTonnageChanged)

        self._playerBrokerDmSpinBox = gui.SkillSpinBox(
            value=app.Config.instance().value(option=app.ConfigOption.PlayerBrokerDM))
        self._playerBrokerDmSpinBox.valueChanged.connect(self._playerBrokerDmChanged)

        self._sellerDmRangeWidget = gui.SellerDMRangeWidget(
            lowerValue=app.Config.instance().value(option=app.ConfigOption.MinSellerDM),
            upperValue=app.Config.instance().value(option=app.ConfigOption.MaxSellerDM))
        self._sellerDmRangeWidget.rangeChanged.connect(self._sellerDmChanged)

        self._buyerDmRangeWidget = gui.BuyerDMRangeWidget(
            lowerValue=app.Config.instance().value(option=app.ConfigOption.MinBuyerDM),
            upperValue=app.Config.instance().value(option=app.ConfigOption.MaxBuyerDM))
        self._buyerDmRangeWidget.rangeChanged.connect(self._buyerDmChanged)

        self._localPurchaseBrokerWidget = gui.LocalBrokerSpinBox(
            enabled=app.Config.instance().value(option=app.ConfigOption.UsePurchaseBroker),
            value=app.Config.instance().value(option=app.ConfigOption.PurchaseBrokerDmBonus),
            rules=app.Config.instance().value(option=app.ConfigOption.Rules))
        self._localPurchaseBrokerWidget.valueChanged.connect(self._localPurchaseBrokerDmChanged)

        self._localSaleBrokerWidget = gui.LocalBrokerSpinBox(
            enabled=app.Config.instance().value(option=app.ConfigOption.UseSaleBroker),
            value=app.Config.instance().value(option=app.ConfigOption.SaleBrokerDmBonus),
            rules=app.Config.instance().value(option=app.ConfigOption.Rules))
        self._localSaleBrokerWidget.valueChanged.connect(self._localSaleBrokerDmChanged)

        leftLayout = gui.FormLayoutEx()
        leftLayout.setContentsMargins(0, 0, 0, 0)
        leftLayout.addRow('Available Funds:', self._availableFundsSpinBox)
        leftLayout.addRow('Max Cargo Tonnage:', self._maxCargoTonnageSpinBox)
        leftLayout.addRow('Player\'s Broker DM:', self._playerBrokerDmSpinBox)
        leftLayout.addRow('Seller DM Range:', self._sellerDmRangeWidget)
        leftLayout.addRow('Buyer DM Range:', self._buyerDmRangeWidget)
        leftLayout.addRow('Local Purchase Broker:', self._localPurchaseBrokerWidget)
        leftLayout.addRow('Local Sale Broker:', self._localSaleBrokerWidget)

        self._routingTypeComboBox = gui.RoutingTypeComboBox(
            value=app.Config.instance().value(option=app.ConfigOption.RoutingType))
        self._routingTypeComboBox.currentEnumChanged.connect(self._routingTypeChanged)

        self._routeOptimisationComboBox = gui.RouteOptimisationComboBox(
            value=app.Config.instance().value(option=app.ConfigOption.RouteOptimisation))
        self._routeOptimisationComboBox.currentEnumChanged.connect(self._routeOptimisationChanged)

        self._perJumpOverheadsSpinBox = gui.JumpOverheadsSpinBox(
            value=app.Config.instance().value(option=app.ConfigOption.PerJumpOverhead))
        self._perJumpOverheadsSpinBox.valueChanged.connect(self._perJumpOverheadsChanged)

        self._includeStartWorldBerthingCheckBox = gui.IncludeStartBerthingCheckBox(
           value=app.Config.instance().value(option=app.ConfigOption.IncludeStartBerthing))
        self._includeStartWorldBerthingCheckBox.stateChanged.connect(self._includeStartWorldBerthingToggled)

        self._includeFinishWorldBerthingCheckBox = gui.IncludeFinishBerthingCheckBox(
            value=app.Config.instance().value(option=app.ConfigOption.IncludeFinishBerthing))
        self._includeFinishWorldBerthingCheckBox.stateChanged.connect(self._includeFinishWorldBerthingToggled)

        self._refuellingStrategyComboBox = gui.RefuellingStrategyComboBox(
            value=app.Config.instance().value(option=app.ConfigOption.RefuellingStrategy))
        self._refuellingStrategyComboBox.currentEnumChanged.connect(self._refuellingStrategyChanged)

        self._useFuelCachesCheckBox = gui.UseFuelCachesCheckBox(
            value=app.Config.instance().value(option=app.ConfigOption.UseFuelCaches))
        self._useFuelCachesCheckBox.stateChanged.connect(self._useFuelCachesToggled)

        self._useAnomalyRefuellingCheckBox = gui.UseAnomalyRefuellingCheckBox(
            value=app.Config.instance().value(option=app.ConfigOption.UseAnomalyRefuelling))
        self._useAnomalyRefuellingCheckBox.stateChanged.connect(self._anomalyRefuellingToggled)

        self._anomalyFuelCostSpinBox = gui.AnomalyFuelCostSpinBox(
            value=app.Config.instance().value(option=app.ConfigOption.AnomalyFuelCost))
        self._anomalyFuelCostSpinBox.valueChanged.connect(self._anomalyFuelCostChanged)

        self._anomalyBerthingCostSpinBox = gui.AnomalyBerthingCostSpinBox(
            value=app.Config.instance().value(option=app.ConfigOption.AnomalyBerthingCost))
        self._anomalyBerthingCostSpinBox.valueChanged.connect(self._anomalyBerthingCostChanged)

        centerLayout = gui.FormLayoutEx()
        centerLayout.setContentsMargins(0, 0, 0, 0)
        centerLayout.addRow('Routing Type:', self._routingTypeComboBox)
        centerLayout.addRow('Route Optimisation:', self._routeOptimisationComboBox)
        centerLayout.addRow('Per Jump Overheads:', self._perJumpOverheadsSpinBox)
        centerLayout.addRow('Start World Berthing:', self._includeStartWorldBerthingCheckBox)
        centerLayout.addRow('Finish World Berthing:', self._includeFinishWorldBerthingCheckBox)

        self._includeLogisticsCostsCheckBox = gui.IncludeLogisticsCostsCheckBox(
            value=app.Config.instance().value(option=app.ConfigOption.IncludeLogisticsCosts))
        self._includeLogisticsCostsCheckBox.stateChanged.connect(self._includeLogisticsCostsToggled)

        self._showUnprofitableTradesCheckBox = gui.ShowUnprofitableTradesCheckBox(
            value=app.Config.instance().value(option=app.ConfigOption.ShowUnprofitableTrades))
        self._showUnprofitableTradesCheckBox.stateChanged.connect(self._showUnprofitableTradesToggled)

        rightLayout = gui.FormLayoutEx()
        rightLayout.setContentsMargins(0, 0, 0, 0)
        rightLayout.addRow('Refuelling Strategy:', self._refuellingStrategyComboBox)
        rightLayout.addRow('Use Fuel Caches:', self._useFuelCachesCheckBox)
        rightLayout.addRow('Use Anomaly Refuelling:', self._useAnomalyRefuellingCheckBox)
        rightLayout.addRow('Anomaly Fuel Cost:', self._anomalyFuelCostSpinBox)
        rightLayout.addRow('Anomaly Berthing Cost:', self._anomalyBerthingCostSpinBox)
        rightLayout.addRow('Include Logistics Costs:', self._includeLogisticsCostsCheckBox)
        rightLayout.addRow('Show Unprofitable Trades:', self._showUnprofitableTradesCheckBox)

        traderLayout = QtWidgets.QHBoxLayout()
        traderLayout.addLayout(leftLayout)
        traderLayout.addLayout(centerLayout)
        traderLayout.addLayout(rightLayout)
        traderLayout.addStretch()

        #
        # Ship Configuration
        #
        self._shipTonnageSpinBox = gui.ShipTonnageSpinBox(
            value=app.Config.instance().value(option=app.ConfigOption.ShipTonnage))
        self._shipTonnageSpinBox.valueChanged.connect(self._shipTonnageChanged)

        self._shipJumpRatingSpinBox = gui.JumpRatingSpinBox(
            value=app.Config.instance().value(option=app.ConfigOption.ShipJumpRating))
        self._shipJumpRatingSpinBox.valueChanged.connect(self._shipJumpRatingChanged)

        self._shipFuelCapacitySpinBox = gui.FuelCapacitySpinBox(
            value=app.Config.instance().value(option=app.ConfigOption.ShipFuelCapacity))
        self._shipFuelCapacitySpinBox.valueChanged.connect(self._shipFuelCapacityChanged)

        self._shipCurrentFuelSpinBox = gui.CurrentFuelSpinBox(
            value=app.Config.instance().value(option=app.ConfigOption.ShipCurrentFuel))
        self._shipCurrentFuelSpinBox.valueChanged.connect(self._shipCurrentFuelChanged)

        self._shipFuelPerParsecSpinBox = gui.FuelPerParsecSpinBox(
            enabled=app.Config.instance().value(option=app.ConfigOption.UseShipFuelPerParsec),
            value=app.Config.instance().value(option=app.ConfigOption.ShipFuelPerParsec))
        self._shipFuelPerParsecSpinBox.valueChanged.connect(self._shipFuelPerParsecChanged)

        shipLayout = gui.FormLayoutEx()
        shipLayout.setContentsMargins(0, 0, 0, 0)
        shipLayout.addRow('Ship Total Tonnage:', self._shipTonnageSpinBox)
        shipLayout.addRow('Ship Jump Rating:', self._shipJumpRatingSpinBox)
        shipLayout.addRow('Ship Fuel Capacity:', self._shipFuelCapacitySpinBox)
        shipLayout.addRow('Ship Current Fuel:', self._shipCurrentFuelSpinBox)
        shipLayout.addRow('Ship Fuel Per Parsec:', self._shipFuelPerParsecSpinBox)

        #
        # Configuration Stack
        #
        self._configurationStack = gui.TabWidgetEx()
        self._configurationStack.addTab(
            gui.LayoutWrapperWidget(layout=traderLayout),
            'Trader')
        self._configurationStack.addTab(
            gui.LayoutWrapperWidget(layout=shipLayout),
            'Ship')

        configurationLayout = QtWidgets.QHBoxLayout()
        configurationLayout.addWidget(self._configurationStack)

        self._configurationGroupBox = QtWidgets.QGroupBox('Configuration')
        self._configurationGroupBox.setLayout(configurationLayout)

    def _setupTradeOptionControls(self) -> None:
        outcomeColours = app.Config.instance().value(option=app.ConfigOption.OutcomeColours)
        worldTagging = app.Config.instance().value(option=app.ConfigOption.WorldTagging)
        taggingColours = app.Config.instance().value(option=app.ConfigOption.TaggingColours)

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

        self._tradeOptionsTable = gui.TradeOptionsTable(
            outcomeColours=outcomeColours,
            worldTagging=worldTagging,
            taggingColours=taggingColours)
        self._tradeOptionsTable.setHexTooltipProvider(
            provider=self._hexTooltipProvider)
        self._tradeOptionsTable.setActiveColumns(self._tradeOptionColumns())
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

    def _appConfigChanged(
            self,
            option: app.ConfigOption,
            oldValue: typing.Any,
            newValue: typing.Any
            ) -> None:
        if option is app.ConfigOption.Milieu:
            self._hexTooltipProvider.setMilieu(milieu=newValue)
            # Changing milieu invalidates existing trade options as the world
            # data they were generated from has changed
            self._clearTradeOptions()
        elif option is app.ConfigOption.Rules:
            self._hexTooltipProvider.setRules(rules=newValue)
            self._localPurchaseBrokerWidget.setRules(rules=newValue)
            self._localSaleBrokerWidget.setRules(rules=newValue)

            # Changing the rules invalidates existing trade options as the
            # trade goods they use are tied to a rule system and the starport
            # refuelling type configuration may have been used when generating
            # them
            self._clearTradeOptions()
        elif option is app.ConfigOption.MapStyle:
            self._hexTooltipProvider.setMapStyle(style=newValue)
        elif option is app.ConfigOption.MapOptions:
            self._hexTooltipProvider.setMapOptions(options=newValue)
        elif option is app.ConfigOption.ShowToolTipImages:
            self._hexTooltipProvider.setShowImages(show=newValue)
        elif option is app.ConfigOption.OutcomeColours:
            self._tradeOptionsTable.setOutcomeColours(colours=newValue)
        elif option is app.ConfigOption.WorldTagging:
            self._hexTooltipProvider.setWorldTagging(tagging=newValue)
            self._tradeOptionsTable.setWorldTagging(tagging=newValue)
        elif option is app.ConfigOption.TaggingColours:
            self._hexTooltipProvider.setTaggingColours(colours=newValue)
            self._tradeOptionsTable.setTaggingColours(colours=newValue)
        elif option is app.ConfigOption.AvailableFunds:
            self._availableFundsSpinBox.setValue(newValue)
        elif option is app.ConfigOption.MaxCargoTonnage:
            self._maxCargoTonnageSpinBox.setValue(newValue)
        elif option is app.ConfigOption.PlayerBrokerDM:
            self._playerBrokerDmSpinBox.setValue(newValue)
        elif option is app.ConfigOption.MinSellerDM:
            self._sellerDmRangeWidget.setLowerValue(newValue)
        elif option is app.ConfigOption.MaxSellerDM:
            self._sellerDmRangeWidget.setUpperValue(newValue)
        elif option is app.ConfigOption.MinBuyerDM:
            self._buyerDmRangeWidget.setLowerValue(newValue)
        elif option is app.ConfigOption.MaxBuyerDM:
            self._buyerDmRangeWidget.setUpperValue(newValue)
        elif option is app.ConfigOption.UsePurchaseBroker:
            self._localPurchaseBrokerWidget.setChecked(newValue)
        elif option is app.ConfigOption.PurchaseBrokerDmBonus:
            self._localPurchaseBrokerWidget.setValue(newValue)
        elif option is app.ConfigOption.UseSaleBroker:
            self._localSaleBrokerWidget.setChecked(newValue)
        elif option is app.ConfigOption.SaleBrokerDmBonus:
            self._localSaleBrokerWidget.setValue(newValue)
        elif option is app.ConfigOption.RoutingType:
            self._routingTypeComboBox.setCurrentEnum(newValue)
            self._enableDisableControls()
        elif option is app.ConfigOption.RouteOptimisation:
            self._routeOptimisationComboBox.setCurrentEnum(newValue)
        elif option is app.ConfigOption.PerJumpOverhead:
            self._perJumpOverheadsSpinBox.setValue(newValue)
        elif option is app.ConfigOption.IncludeStartBerthing:
            self._includeStartWorldBerthingCheckBox.setChecked(newValue)
        elif option is app.ConfigOption.IncludeFinishBerthing:
            self._includeFinishWorldBerthingCheckBox.setChecked(newValue)
        elif option is app.ConfigOption.RefuellingStrategy:
            self._refuellingStrategyComboBox.setCurrentEnum(newValue)
        elif option is app.ConfigOption.UseFuelCaches:
            self._useFuelCachesCheckBox.setChecked(newValue)
        elif option is app.ConfigOption.UseAnomalyRefuelling:
            self._useAnomalyRefuellingCheckBox.setChecked(newValue)
            self._enableDisableControls()
        elif option is app.ConfigOption.AnomalyFuelCost:
            self._anomalyFuelCostSpinBox.setValue(newValue)
        elif option is app.ConfigOption.AnomalyBerthingCost:
            self._anomalyBerthingCostSpinBox.setValue(newValue)
        elif option is app.ConfigOption.IncludeLogisticsCosts:
            self._includeLogisticsCostsCheckBox.setChecked(newValue)
        elif option is app.ConfigOption.ShowUnprofitableTrades:
            self._showUnprofitableTradesCheckBox.setChecked(newValue)
        elif option is app.ConfigOption.ShipTonnage:
            self._shipTonnageSpinBox.setValue(newValue)
        elif option is app.ConfigOption.ShipJumpRating:
            self._shipJumpRatingSpinBox.setValue(newValue)
        elif option is app.ConfigOption.ShipFuelCapacity:
            self._shipFuelCapacitySpinBox.setValue(newValue)
        elif option is app.ConfigOption.ShipCurrentFuel:
            self._shipCurrentFuelSpinBox.setValue(newValue)
        elif option is app.ConfigOption.UseShipFuelPerParsec:
            self._shipFuelPerParsecSpinBox.setChecked(newValue)
        elif option is app.ConfigOption.ShipFuelPerParsec:
            self._shipFuelPerParsecSpinBox.setValue(newValue)

    def _enableDisableControls(self) -> None:
        isFuelAwareRouting = self._routingTypeComboBox.currentEnum() is not logic.RoutingType.Basic
        isAnomalyRefuelling = isFuelAwareRouting and self._useAnomalyRefuellingCheckBox.isChecked()
        self._refuellingStrategyComboBox.setEnabled(isFuelAwareRouting)
        self._useFuelCachesCheckBox.setEnabled(isFuelAwareRouting)
        self._useAnomalyRefuellingCheckBox.setEnabled(isFuelAwareRouting)
        self._anomalyFuelCostSpinBox.setEnabled(isAnomalyRefuelling)
        self._anomalyBerthingCostSpinBox.setEnabled(isAnomalyRefuelling)

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

    def _clearTradeOptions(self) -> None:
        if self._traderJob:
            self._traderJob.cancel()
            self._traderJob = None
        self._tradeOptionsTable.removeAllRows()
        self._progressLabel.clear()
        self._tradeOptionCountLabel.clear()

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
            jumpRouteWindow.setRoute(
                route=tradeOption.jumpRoute(),
                logistics=tradeOption.routeLogistics())
        except Exception as ex:
            message = 'Failed to show jump route window'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)

    def _playerBrokerDmChanged(
            self,
            brokerSkill: int
            ) -> None:
        app.Config.instance().setValue(
            option=app.ConfigOption.PlayerBrokerDM,
            value=brokerSkill)

    def _localPurchaseBrokerDmChanged(
            self,
            brokerSkill: typing.Optional[int]
            ) -> None:
        useBroker = brokerSkill is not None
        app.Config.instance().setValue(
            option=app.ConfigOption.UsePurchaseBroker,
            value=useBroker)
        if useBroker:
            app.Config.instance().setValue(
                option=app.ConfigOption.PurchaseBrokerDmBonus,
                value=brokerSkill)

    def _localSaleBrokerDmChanged(
            self,
            brokerSkill: typing.Optional[int]
            ) -> None:
        useBroker = brokerSkill is not None
        app.Config.instance().setValue(
            option=app.ConfigOption.UseSaleBroker,
            value=useBroker)
        if useBroker:
            app.Config.instance().setValue(
                option=app.ConfigOption.SaleBrokerDmBonus,
                value=brokerSkill)

    def _sellerDmChanged(
            self,
            minValue: int,
            maxValue: int
            ) -> None:
        app.Config.instance().setValue(
            option=app.ConfigOption.MinSellerDM,
            value=minValue)
        app.Config.instance().setValue(
            option=app.ConfigOption.MaxSellerDM,
            value=maxValue)

    def _buyerDmChanged(
            self,
            minValue: int,
            maxValue: int) -> None:
        app.Config.instance().setValue(
            option=app.ConfigOption.MinBuyerDM,
            value=minValue)
        app.Config.instance().setValue(
            option=app.ConfigOption.MaxBuyerDM,
            value=maxValue)

    def _availableFundsChanged(self, availableFunds: int) -> None:
        app.Config.instance().setValue(
            option=app.ConfigOption.AvailableFunds,
            value=availableFunds)

    def _maxCargoTonnageChanged(self, cargoCapacity: int) -> None:
        app.Config.instance().setValue(
            option=app.ConfigOption.MaxCargoTonnage,
            value=cargoCapacity)

    def _routingTypeChanged(
            self,
            routingType: typing.Optional[logic.RoutingType]
            ) -> None:
        if not routingType:
            return
        app.Config.instance().setValue(
            option=app.ConfigOption.RoutingType,
            value=routingType)

    def _routeOptimisationChanged(
            self,
            routeOptimisation: typing.Optional[logic.RouteOptimisation]
            ) -> None:
        if not routeOptimisation:
            return
        app.Config.instance().setValue(
            option=app.ConfigOption.RouteOptimisation,
            value=routeOptimisation)

    def _perJumpOverheadsChanged(self, jumpOverheads: int) -> None:
        app.Config.instance().setValue(
            option=app.ConfigOption.PerJumpOverhead,
            value=jumpOverheads)

    def _includeStartWorldBerthingToggled(
            self,
            checkedState: QtCore.Qt.CheckState
            ) -> None:
        app.Config.instance().setValue(
            option=app.ConfigOption.IncludeStartBerthing,
            value=checkedState == QtCore.Qt.CheckState.Checked)

    def _includeFinishWorldBerthingToggled(
            self,
            checkedState: QtCore.Qt.CheckState
            ) -> None:
        app.Config.instance().setValue(
            option=app.ConfigOption.IncludeFinishBerthing,
            value=checkedState == QtCore.Qt.CheckState.Checked)

    def _refuellingStrategyChanged(
            self,
            strategy: typing.Optional[logic.RefuellingStrategy]
            ) -> None:
        if not strategy:
            return
        app.Config.instance().setValue(
            option=app.ConfigOption.RefuellingStrategy,
            value=strategy)

    def _useFuelCachesToggled(self, checkedState: QtCore.Qt.CheckState) -> None:
        app.Config.instance().setValue(
            option=app.ConfigOption.UseFuelCaches,
            value=checkedState == QtCore.Qt.CheckState.Checked)

    def _anomalyRefuellingToggled(self, checkedState: QtCore.Qt.CheckState) -> None:
        app.Config.instance().setValue(
            option=app.ConfigOption.UseAnomalyRefuelling,
            value=checkedState == QtCore.Qt.CheckState.Checked)

    def _anomalyFuelCostChanged(self, fuelCost: int) -> None:
        app.Config.instance().setValue(
            option=app.ConfigOption.AnomalyFuelCost,
            value=fuelCost)

    def _anomalyBerthingCostChanged(self, berthingCost: int) -> None:
        app.Config.instance().setValue(
            option=app.ConfigOption.AnomalyBerthingCost,
            value=berthingCost)

    def _includeLogisticsCostsToggled(self, checkedState: QtCore.Qt.CheckState) -> None:
        app.Config.instance().setValue(
            option=app.ConfigOption.IncludeLogisticsCosts,
            value=checkedState == QtCore.Qt.CheckState.Checked)

    def _showUnprofitableTradesToggled(self, checkedState: QtCore.Qt.CheckState) -> None:
        app.Config.instance().setValue(
            option=app.ConfigOption.ShowUnprofitableTrades,
            value=checkedState == QtCore.Qt.CheckState.Checked)

    def _shipTonnageChanged(self, shipTonnage: int) -> None:
        app.Config.instance().setValue(
            option=app.ConfigOption.ShipTonnage,
            value=shipTonnage)

    def _shipJumpRatingChanged(self, jumpRating: int) -> None:
        app.Config.instance().setValue(
            option=app.ConfigOption.ShipJumpRating,
            value=jumpRating)

    def _shipFuelCapacityChanged(self, fuelCapacity: int) -> None:
        app.Config.instance().setValue(
            option=app.ConfigOption.ShipFuelCapacity,
            value=fuelCapacity)

    def _shipCurrentFuelChanged(self, currentFuel: float) -> None:
        app.Config.instance().setValue(
            option=app.ConfigOption.ShipCurrentFuel,
            value=currentFuel)

    def _shipFuelPerParsecChanged(
            self,
            fuelPerParsec: typing.Optional[float]
            ) -> None:
        useFuelPerParsec = fuelPerParsec is not None
        app.Config.instance().setValue(
            option=app.ConfigOption.UseShipFuelPerParsec,
            value=useFuelPerParsec)
        if useFuelPerParsec:
            app.Config.instance().setValue(
                option=app.ConfigOption.ShipFuelPerParsec,
                value=fuelPerParsec)

    # This should be implemented by the derived class
    def _calculateTradeOptions(self) -> None:
        pass

    def _updateTraderProgress(
            self,
            optionsProcessed: int,
            optionsToProcess: int
            ) -> None:
        self._progressLabel.setText(common.formatNumber(optionsProcessed) + '/' + common.formatNumber(optionsToProcess))

    def _traderJobStart(self) -> None:
        if not self._traderJob:
            return

        try:
            self._traderJob.start()
        except Exception as ex:
            self._traderJob = None
            self._calculateTradeOptionsButton.showPrimaryText()
            self._enableDisableControls()

            message = 'Failed to start trader job'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)

    def _traderJobFinished(self, result: typing.Union[str, Exception]) -> None:
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
        self._tradeOptionsTable.setActiveColumns(self._tradeOptionColumns())

    def _showTradeOptionsTableContextMenu(self, point: QtCore.QPoint) -> None:
        singleRowSelected = len(self._tradeOptionsTable.selectedRows()) == 1
        currentOption = self._tradeOptionsTable.currentTradeOption()

        planJumpRouteAction = QtWidgets.QAction('Plan Jump Route Between Worlds...', self)
        planJumpRouteAction.setEnabled(singleRowSelected)
        planJumpRouteAction.triggered.connect(lambda: self._planJumpRoute(currentOption))

        menu = QtWidgets.QMenu()
        menu.addAction(planJumpRouteAction)
        menu.addSeparator()
        self._tradeOptionsTable.fillContextMenu(menu)
        menu.exec(self._tradeOptionsTable.viewport().mapToGlobal(point))

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
        self._mainSplitter.setStretchFactor(0, 1)
        self._mainSplitter.setStretchFactor(1, 100)

        self._tradeInfoSplitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        self._tradeInfoSplitter.addWidget(self._mainSplitter)
        self._tradeInfoSplitter.addWidget(self._tradeInfoEditBox)

        windowLayout = QtWidgets.QVBoxLayout()
        windowLayout.addWidget(self._tradeInfoSplitter)

        self.setLayout(windowLayout)

    def configureControls(
            self,
            purchaseWorld: typing.Optional[multiverse.World] = None,
            saleWorlds: typing.Optional[typing.Iterable[multiverse.World]] = None,
            playerBrokerDm: typing.Optional[int] = None,
            minSellerDm: typing.Optional[int] = None,
            maxSellerDm: typing.Optional[int] = None,
            minBuyerDm: typing.Optional[int] = None,
            maxBuyerDm: typing.Optional[int] = None,
            availableFunds: typing.Optional[int] = None,
            maxCargoTonnage: typing.Optional[int] = None,
            shipTonnage: typing.Optional[int] = None,
            shipJumpRating: typing.Optional[int] = None,
            shipFuelCapacity: typing.Optional[int] = None,
            shipCurrentFuel: typing.Optional[float] = None,
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
            self._saleWorldsWidget.removeAllRows()

        if purchaseWorld != None:
            self._purchaseWorldWidget.setSelectedHex(
                hex=purchaseWorld.hex() if purchaseWorld else None)
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
            self._shipCurrentFuelSpinBox.setValue(float(shipCurrentFuel))
        if maxCargoTonnage != None:
            self._maxCargoTonnageSpinBox.setValue(int(maxCargoTonnage))
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
            for world in saleWorlds:
                self._saleWorldsWidget.addHex(hex=world.hex())

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
            key='ConfigurationTabBarState',
            type=QtCore.QByteArray)
        if storedValue:
            self._configurationStack.restoreState(storedValue)

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

        self._settings.setValue('PurchaseWorldState', self._purchaseWorldWidget.saveState())
        self._settings.setValue('ConfigurationTabBarState', self._configurationStack.saveState())
        self._settings.setValue('CargoRecordsDisplayModeState', self._cargoRecordDisplayModeTabView.saveState())
        self._settings.setValue('SpeculativeCargoTableState', self._speculativeCargoTable.saveState())
        self._settings.setValue('SpeculativeCargoTableContent', self._speculativeCargoTable.saveContent())
        self._settings.setValue('AvailableCargoTableState', self._availableCargoTable.saveState())
        self._settings.setValue('AvailableCargoTableContent', self._availableCargoTable.saveContent())
        self._settings.setValue('SaleWorldsTableState', self._saleWorldsWidget.saveState())
        self._settings.setValue('SaleWorldsTableContent', self._saleWorldsWidget.saveContent())
        self._settings.setValue('CurrentCargoTableState', self._currentCargoTable.saveState())
        self._settings.setValue('CurrentCargoTableContent', self._currentCargoTable.saveContent())
        self._settings.setValue('MainSplitterState', self._mainSplitter.saveState())
        self._settings.setValue('TableSplitterState', self._tableSplitter.saveState())
        self._settings.setValue('TradeInfoSplitterState', self._tradeInfoSplitter.saveState())

        self._settings.endGroup()

        super().saveSettings()

    def eventFilter(self, object: object, event: QtCore.QEvent) -> bool:
        if object == self._speculativeCargoTable:
            if event.type() == QtCore.QEvent.Type.KeyPress:
                assert(isinstance(event, QtGui.QKeyEvent))
                if event.key() == QtCore.Qt.Key.Key_Delete:
                    self._removeSelectedSpeculativeCargo()
                    event.accept()
                    return True
        elif object == self._availableCargoTable:
            if event.type() == QtCore.QEvent.Type.KeyPress:
                assert(isinstance(event, QtGui.QKeyEvent))
                if event.key() == QtCore.Qt.Key.Key_Delete:
                    self._removeSelectedAvailableCargo()
                    event.accept()
                    return True
        elif object == self._currentCargoTable:
            if event.type() == QtCore.QEvent.Type.KeyPress:
                assert(isinstance(event, QtGui.QKeyEvent))
                if event.key() == QtCore.Qt.Key.Key_Delete:
                    self._removeSelectedCurrentCargo()
                    event.accept()
                    return True

        return super().eventFilter(object, event)

    def _setupPurchaseWorldControls(self) -> None:
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

        purchaseWorldLayout = QtWidgets.QVBoxLayout()
        purchaseWorldLayout.addWidget(self._purchaseWorldWidget)

        self._purchaseWorldGroupBox = QtWidgets.QGroupBox('Purchase World')
        self._purchaseWorldGroupBox.setLayout(purchaseWorldLayout)

    def _setupSaleWorldControls(self) -> None:
        milieu = app.Config.instance().value(option=app.ConfigOption.Milieu)
        rules = app.Config.instance().value(option=app.ConfigOption.Rules)
        mapStyle = app.Config.instance().value(option=app.ConfigOption.MapStyle)
        mapOptions = app.Config.instance().value(option=app.ConfigOption.MapOptions)
        mapRendering = app.Config.instance().value(option=app.ConfigOption.MapRendering)
        mapAnimations = app.Config.instance().value(option=app.ConfigOption.MapAnimations)
        worldTagging = app.Config.instance().value(option=app.ConfigOption.WorldTagging)
        taggingColours = app.Config.instance().value(option=app.ConfigOption.TaggingColours)

        self._saleWorldsTable = _WorldSaleScoreTable(
            milieu=milieu,
            rules=rules,
            worldTagging=worldTagging,
            taggingColours=taggingColours)
        self._saleWorldsWidget = gui.HexTableManagerWidget(
            milieu=milieu,
            rules=rules,
            mapStyle=mapStyle,
            mapOptions=mapOptions,
            mapRendering=mapRendering,
            mapAnimations=mapAnimations,
            worldTagging=worldTagging,
            taggingColours=taggingColours,
            hexTable=self._saleWorldsTable,
            allowHexCallback=self._allowSaleWorld)
        self._saleWorldsWidget.setHexTooltipProvider(
            provider=self._hexTooltipProvider)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self._saleWorldsWidget)

        self._saleWorldsGroupBox = QtWidgets.QGroupBox('Sale Worlds')
        self._saleWorldsGroupBox.setLayout(layout)

    def _setupCargoControls(self) -> None:
        outcomeColours = app.Config.instance().value(
            option=app.ConfigOption.OutcomeColours)

        self._cargoRecordDisplayModeTabView = gui.ItemCountTabWidget()
        self._cargoRecordDisplayModeTabView.setTabPosition(QtWidgets.QTabWidget.TabPosition.West)

        # Speculative cargo controls
        self._speculativeCargoTable = gui.CargoRecordTable(
            outcomeColours=outcomeColours,
            columns=gui.CargoRecordTable.AllCaseColumns)
        self._speculativeCargoTable.setMinimumHeight(100)
        self._speculativeCargoTable.installEventFilter(self)
        self._speculativeCargoTable.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self._speculativeCargoTable.customContextMenuRequested.connect(self._showSpeculativeCargoTableContextMenu)

        self._addWorldSpeculativeCargoButton = QtWidgets.QPushButton('Generate...')
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
        speculativeCargoPaneWidget = QtWidgets.QWidget()
        speculativeCargoPaneWidget.setLayout(paneLayout)

        tabIndex = self._cargoRecordDisplayModeTabView.addTab(speculativeCargoPaneWidget, 'Speculative')
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
        self._cargoRecordDisplayModeTabView.setWidgetItemCount(speculativeCargoPaneWidget, 0)
        self._speculativeCargoTable.model().rowsInserted.connect(
            lambda: self._cargoRecordDisplayModeTabView.setWidgetItemCount(
                speculativeCargoPaneWidget,
                self._speculativeCargoTable.rowCount()))
        self._speculativeCargoTable.model().rowsRemoved.connect(
            lambda: self._cargoRecordDisplayModeTabView.setWidgetItemCount(
                speculativeCargoPaneWidget,
                self._speculativeCargoTable.rowCount()))

        # Available cargo controls
        self._availableCargoTable = gui.CargoRecordTable(
            outcomeColours=outcomeColours,
            columns=[
                gui.CargoRecordTable.ColumnType.TradeGood,
                gui.CargoRecordTable.ColumnType.BasePricePerTon,
                gui.CargoRecordTable.ColumnType.SetPricePerTon,
                gui.CargoRecordTable.ColumnType.SetQuantity])
        self._availableCargoTable.setMinimumHeight(100)
        self._availableCargoTable.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self._availableCargoTable.installEventFilter(self)
        self._availableCargoTable.customContextMenuRequested.connect(self._showAvailableCargoTableContextMenu)
        self._availableCargoTable.doubleClicked.connect(self._promptEditAvailableCargo)

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
        availableCargoPaneWidget = QtWidgets.QWidget()
        availableCargoPaneWidget.setLayout(paneLayout)

        tabIndex = self._cargoRecordDisplayModeTabView.addTab(availableCargoPaneWidget, 'Available')
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
        self._cargoRecordDisplayModeTabView.setWidgetItemCount(availableCargoPaneWidget, 0)
        self._availableCargoTable.model().rowsInserted.connect(
            lambda: self._cargoRecordDisplayModeTabView.setWidgetItemCount(
                availableCargoPaneWidget,
                self._availableCargoTable.rowCount()))
        self._availableCargoTable.model().rowsRemoved.connect(
            lambda: self._cargoRecordDisplayModeTabView.setWidgetItemCount(
                availableCargoPaneWidget,
                self._availableCargoTable.rowCount()))

        # Current cargo controls
        self._currentCargoTable = gui.CargoRecordTable(
            outcomeColours=outcomeColours,
            columns=[
                gui.CargoRecordTable.ColumnType.TradeGood,
                gui.CargoRecordTable.ColumnType.SetTotalPrice,
                gui.CargoRecordTable.ColumnType.SetPricePerTon,
                gui.CargoRecordTable.ColumnType.SetQuantity])
        self._currentCargoTable.setMinimumHeight(100)
        self._currentCargoTable.installEventFilter(self)
        self._currentCargoTable.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self._currentCargoTable.customContextMenuRequested.connect(self._showCurrentCargoTableContextMenu)
        self._currentCargoTable.doubleClicked.connect(self._promptEditCurrentCargo)

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
        currentCargoPaneWidget = QtWidgets.QWidget()
        currentCargoPaneWidget.setLayout(paneLayout)

        tabIndex = self._cargoRecordDisplayModeTabView.addTab(currentCargoPaneWidget, 'Current')
        self._cargoRecordDisplayModeTabView.setTabToolTip(
            tabIndex,
            gui.createStringToolTip(
                '<p>Cargo that you currently own</p>' \
                '<p>This view can be used to speculate on the sale of the cargo you currently own.' \
                'The results can be used to gauge where you\'re best to go to offload your cargo.</p>' \
                '<p>Trade options generated for this cargo will speculate on sale price and ' \
                'logistics costs.</p>',
                escape=False))
        self._cargoRecordDisplayModeTabView.setWidgetItemCount(currentCargoPaneWidget, 0)
        self._currentCargoTable.model().rowsInserted.connect(
            lambda: self._cargoRecordDisplayModeTabView.setWidgetItemCount(
                currentCargoPaneWidget,
                self._currentCargoTable.rowCount()))
        self._currentCargoTable.model().rowsRemoved.connect(
            lambda: self._cargoRecordDisplayModeTabView.setWidgetItemCount(
                currentCargoPaneWidget,
                self._currentCargoTable.rowCount()))

        # Group box
        groupBoxLayout = QtWidgets.QVBoxLayout()
        groupBoxLayout.addWidget(self._cargoRecordDisplayModeTabView)

        self._cargoGroupBox = QtWidgets.QGroupBox('Cargo')
        self._cargoGroupBox.setLayout(groupBoxLayout)

    def _enableDisableControls(self) -> None:
        super()._enableDisableControls()

        if not self._traderJob:
            self._purchaseWorldGroupBox.setDisabled(False)

            # Disable all other controls until purchase world is selected
            disable = not self._purchaseWorldWidget.selectedWorld()
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
        world = self._purchaseWorldWidget.selectedWorld()
        if not world:
            self._removeAllSpeculativeCargo()
            return

        rules = app.Config.instance().value(option=app.ConfigOption.Rules)
        replacements = {}
        for currentCargoRecord in self._speculativeCargoTable.cargoRecords():
            cargoRecords = logic.generateSpeculativePurchaseCargo(
                ruleSystem=rules.system(),
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

    def _allowSaleWorld(self, hex: multiverse.HexPosition) -> bool:
        # Silently ignore worlds that are already in the table
        return not self._saleWorldsWidget.containsHex(hex)

    def _updateSaleWorldTradeScores(self) -> None:
        tradeGoods = set()
        for tradeOption in self._speculativeCargoTable.cargoRecords():
            tradeGoods.add(tradeOption.tradeGood())
        for tradeOption in self._availableCargoTable.cargoRecords():
            tradeGoods.add(tradeOption.tradeGood())
        for tradeOption in self._currentCargoTable.cargoRecords():
            tradeGoods.add(tradeOption.tradeGood())
        self._saleWorldsTable.setTradeGoods(tradeGoods)

    def _appConfigChanged(
            self,
            option: app.ConfigOption,
            oldValue: typing.Any,
            newValue: typing.Any
            ) -> None:
        super()._appConfigChanged(
            option=option,
            oldValue=oldValue,
            newValue=newValue)

        if option is app.ConfigOption.Milieu:
            self._purchaseWorldWidget.setMilieu(milieu=newValue)
            self._saleWorldsWidget.setMilieu(milieu=newValue)
        elif option is app.ConfigOption.Rules:
            self._purchaseWorldWidget.setRules(rules=newValue)
            self._saleWorldsWidget.setRules(rules=newValue)
        elif option is app.ConfigOption.MapStyle:
            self._purchaseWorldWidget.setMapStyle(style=newValue)
            self._saleWorldsWidget.setMapStyle(style=newValue)
        elif option is app.ConfigOption.MapOptions:
            self._purchaseWorldWidget.setMapOptions(options=newValue)
            self._saleWorldsWidget.setMapOptions(options=newValue)
        elif option is app.ConfigOption.MapRendering:
            self._purchaseWorldWidget.setMapRendering(rendering=newValue)
            self._saleWorldsWidget.setMapRendering(rendering=newValue)
        elif option is app.ConfigOption.MapAnimations:
            self._purchaseWorldWidget.setMapAnimations(enabled=newValue)
            self._saleWorldsWidget.setMapAnimations(enabled=newValue)
        elif option is app.ConfigOption.OutcomeColours:
            self._speculativeCargoTable.setOutcomeColours(colours=newValue)
            self._availableCargoTable.setOutcomeColours(colours=newValue)
            self._currentCargoTable.setOutcomeColours(colours=newValue)
        elif option is app.ConfigOption.WorldTagging:
            self._purchaseWorldWidget.setWorldTagging(tagging=newValue)
            self._saleWorldsWidget.setWorldTagging(tagging=newValue)
        elif option is app.ConfigOption.TaggingColours:
            self._purchaseWorldWidget.setTaggingColours(colours=newValue)
            self._saleWorldsWidget.setTaggingColours(colours=newValue)

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
        purchaseWorld = self._purchaseWorldWidget.selectedWorld()
        if purchaseWorld:
            self._saleWorldsWidget.setRelativeWorld(world=purchaseWorld)

    def _generateSpeculativeCargoForWorld(self) -> None:
        if not self._speculativeCargoTable.isEmpty():
            answer = gui.AutoSelectMessageBox.question(
                parent=self,
                text='This will replace the existing speculative cargo.\nDo you ant to continue?',
                stateKey='WorldTraderReplaceSpeculativeCargo',
                # Only remember if the user clicked yes
                rememberState=QtWidgets.QMessageBox.StandardButton.Yes)
            if answer != QtWidgets.QMessageBox.StandardButton.Yes:
                return

        includeIllegal = gui.MessageBoxEx.question(
            parent=self,
            text='Include illegal trade goods?') == QtWidgets.QMessageBox.StandardButton.Yes

        rules = app.Config.instance().value(option=app.ConfigOption.Rules)
        cargoRecords = logic.generateSpeculativePurchaseCargo(
            ruleSystem=rules.system(),
            world=self._purchaseWorldWidget.selectedWorld(),
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
        rules = app.Config.instance().value(option=app.ConfigOption.Rules)

        # Don't list exotics. We can't generate speculate trade options for them so there's no
        # reason to add them here
        ignoreTradeGoods = [traveller.tradeGoodFromId(
            ruleSystem=rules.system(),
            tradeGoodId=traveller.TradeGoodIds.Exotics)]

        # Don't list trade goods that have already been added to the list
        for row in range(self._speculativeCargoTable.rowCount()):
            cargoRecord = self._speculativeCargoTable.cargoRecord(row)
            ignoreTradeGoods.append(cargoRecord.tradeGood())

        tradeGoods = traveller.tradeGoodList(
            ruleSystem=rules.system(),
            excludeTradeGoods=ignoreTradeGoods)

        if not tradeGoods:
            gui.MessageBoxEx.information(
                parent=self,
                text='Cargo records for all trade goods have already been added')
            return

        tradeGoods = set(tradeGoods) # Convert to a set for fast lookup in callback
        dlg = gui.TradeGoodSelectDialog(
            rules=rules,
            filterCallback=lambda tradeGood: tradeGood in tradeGoods,
            parent=self)
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return

        cargoRecords = logic.generateSpeculativePurchaseCargo(
            ruleSystem=rules.system(),
            world=self._purchaseWorldWidget.selectedWorld(),
            playerBrokerDm=self._playerBrokerDmSpinBox.value(),
            useLocalBroker=self._localPurchaseBrokerWidget.isChecked(),
            localBrokerDm=self._localPurchaseBrokerWidget.value(),
            minSellerDm=self._sellerDmRangeWidget.lowerValue(),
            maxSellerDm=self._sellerDmRangeWidget.upperValue(),
            tradeGoods=dlg.selectedTradeGoods())

        for cargoRecord in cargoRecords:
            self._addSpeculativeCargo(cargoRecord)

    def _showSpeculativeCargoTableContextMenu(self, point: QtCore.QPoint) -> None:
        addCargoAction = QtWidgets.QAction('Add...', self)
        addCargoAction.triggered.connect(
            self._promptAddSpeculativeCargo)

        addCurrentWorldCargoAction = QtWidgets.QAction('Generate for World...', self)
        addCurrentWorldCargoAction.triggered.connect(
            self._generateSpeculativeCargoForWorld)

        removeSelectedCargoAction = QtWidgets.QAction('Remove', self)
        removeSelectedCargoAction.setEnabled(self._speculativeCargoTable.hasSelection())
        removeSelectedCargoAction.triggered.connect(
            self._removeSelectedSpeculativeCargo)

        removeAllCargoAction = QtWidgets.QAction('Remove All', self)
        removeAllCargoAction.setEnabled(not self._speculativeCargoTable.isEmpty())
        removeAllCargoAction.triggered.connect(
            self._removeAllSpeculativeCargo)

        menu = QtWidgets.QMenu()
        menu.addAction(addCargoAction)
        menu.addAction(addCurrentWorldCargoAction)
        menu.addSeparator()
        menu.addAction(removeSelectedCargoAction)
        menu.addAction(removeAllCargoAction)
        menu.addSeparator()
        self._speculativeCargoTable.fillContextMenu(menu)
        menu.exec(self._speculativeCargoTable.viewport().mapToGlobal(point))

    def _importAvailableCargo(self) -> None:
        if not self._availableCargoTable.isEmpty():
            answer = gui.AutoSelectMessageBox.question(
                parent=self,
                text='This will replace the existing available cargo.\nDo you want to continue?',
                stateKey='WorldTraderReplaceAvailableCargo',
                # Only remember if the user clicked yes
                rememberState=QtWidgets.QMessageBox.StandardButton.Yes)
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

        rules = app.Config.instance().value(option=app.ConfigOption.Rules)
        tradeGoods = traveller.tradeGoodList(
            ruleSystem=rules.system(),
            excludeTradeGoods=ignoreTradeGoods)

        if not tradeGoods:
            gui.MessageBoxEx.information(
                parent=self,
                text='All trade goods have already been added')
            return

        dlg = gui.ScalarCargoDetailsDialog(
            parent=self,
            title='Add Available Cargo',
            world=self._purchaseWorldWidget.selectedWorld(),
            rules=rules,
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
            parent=self,
            title='Edit Available Cargo',
            world=self._purchaseWorldWidget.selectedWorld(),
            rules=app.Config.instance().value(option=app.ConfigOption.Rules),
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

        dlg = gui.PurchaseCargoDialog(
            parent=self,
            world=self._purchaseWorldWidget.selectedWorld(),
            rules=app.Config.instance().value(option=app.ConfigOption.Rules),
            availableCargo=affordableCargo,
            availableFunds=self._availableFundsSpinBox.value(),
            freeCargoCapacity=self._maxCargoTonnageSpinBox.value(),
            outcomeColours=app.Config.instance().value(option=app.ConfigOption.OutcomeColours))
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

    def _showAvailableCargoTableContextMenu(self, point: QtCore.QPoint) -> None:
        hasContent = not self._availableCargoTable.isEmpty()
        hasSelection = self._availableCargoTable.hasSelection()
        hasSingleSelection = len(self._availableCargoTable.selectedRows()) == 1

        addCargoAction = QtWidgets.QAction('Add...', self)
        addCargoAction.triggered.connect(self._promptAddAvailableCargo)

        editCargoAction = QtWidgets.QAction('Edit...', self)
        editCargoAction.setEnabled(hasSingleSelection)
        editCargoAction.triggered.connect(self._promptEditAvailableCargo)

        removeSelectedCargoAction = QtWidgets.QAction('Remove', self)
        removeSelectedCargoAction.setEnabled(hasSelection)
        removeSelectedCargoAction.triggered.connect(self._removeSelectedAvailableCargo)

        removeAllCargoAction = QtWidgets.QAction('Remove All', self)
        removeAllCargoAction.setEnabled(hasContent)
        removeAllCargoAction.triggered.connect(self._removeAllAvailableCargo)

        purchaseCargoAction = QtWidgets.QAction('Purchase...', self)
        purchaseCargoAction.setEnabled(hasContent)
        purchaseCargoAction.triggered.connect(self._purchaseAvailableCargo)

        menu = QtWidgets.QMenu()
        menu.addAction(addCargoAction)
        menu.addAction(editCargoAction)
        menu.addSeparator()
        menu.addAction(removeSelectedCargoAction)
        menu.addAction(removeAllCargoAction)
        menu.addSeparator()
        menu.addAction(purchaseCargoAction)
        menu.addSeparator()
        self._availableCargoTable.fillContextMenu(menu)
        menu.exec(self._availableCargoTable.viewport().mapToGlobal(point))

    def _importCurrentCargo(self) -> None:
        if not self._currentCargoTable.isEmpty():
            answer = gui.AutoSelectMessageBox.question(
                parent=self,
                text='This will replace the existing current cargo.\nDo you want to continue?',
                stateKey='WorldTraderReplaceCurrentCargo',
                # Only remember if the user clicked yes
                rememberState=QtWidgets.QMessageBox.StandardButton.Yes)
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
            'JSON (*.json)')
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
            parent=self,
            title='Add Current Cargo',
            world=self._purchaseWorldWidget.selectedWorld(),
            rules=app.Config.instance().value(option=app.ConfigOption.Rules))
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
            parent=self,
            title='Edit Current Cargo',
            world=self._purchaseWorldWidget.selectedWorld(),
            rules=app.Config.instance().value(option=app.ConfigOption.Rules),
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

    def _showCurrentCargoTableContextMenu(self, point: QtCore.QPoint) -> None:
        hasContent = not self._currentCargoTable.isEmpty()
        hasSelection = self._currentCargoTable.hasSelection()
        hasSingleSelection = len(self._currentCargoTable.selectedRows()) == 1

        addCargoAction = QtWidgets.QAction('Add...', self)
        addCargoAction.triggered.connect(self._promptAddCurrentCargo)

        editCargoAction = QtWidgets.QAction('Edit...', self)
        editCargoAction.setEnabled(hasSingleSelection)
        editCargoAction.triggered.connect(self._promptEditCurrentCargo)

        removeSelectedCargoAction = QtWidgets.QAction('Remove', self)
        removeSelectedCargoAction.setEnabled(hasSelection)
        removeSelectedCargoAction.triggered.connect(self._removeSelectedCurrentCargo)

        removeAllCargoAction = QtWidgets.QAction('Remove All', self)
        removeAllCargoAction.setEnabled(hasContent)
        removeAllCargoAction.triggered.connect(self._removeAllCurrentCargo)

        menu = QtWidgets.QMenu()
        menu.addAction(addCargoAction)
        menu.addAction(editCargoAction)
        menu.addSeparator()
        menu.addAction(removeSelectedCargoAction)
        menu.addAction(removeAllCargoAction)
        menu.addSeparator()
        self._currentCargoTable.fillContextMenu(menu)
        menu.exec(self._currentCargoTable.viewport().mapToGlobal(point))

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
            if self._maxCargoTonnageSpinBox.value() <= 0:
                gui.MessageBoxEx.information(
                    parent=self,
                    text='Max cargo tonnage can\'t be zero when calculating trade options for speculative and available cargo')
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
        if self._maxCargoTonnageSpinBox.value() > self._shipTonnageSpinBox.value():
            gui.MessageBoxEx.information(
                parent=self,
                text='Max cargo tonnage can\'t be larger than the total ship tonnage')
            return
        if (self._shipFuelCapacitySpinBox.value() + self._maxCargoTonnageSpinBox.value()) > \
                self._shipTonnageSpinBox.value():
            gui.MessageBoxEx.information(
                parent=self,
                text='Max cargo tonnage plus ship\'s fuel capacity can\'t be larger than the total ship tonnage')
            return

        if self._shipJumpRatingSpinBox.value() >= app.ConsideredVeryHighJumpRating:
            message = \
                'Your ship has a very high jump rating. This can significantly increase ' \
                'the time it takes to calculate trade options.\n\n' \
                'Do you want to continue?'
            answer = gui.AutoSelectMessageBox.question(
                parent=self,
                text=message,
                stateKey='WorldTraderHighJumpRatingWarning',
                # Only remember if the user clicked yes
                rememberState=QtWidgets.QMessageBox.StandardButton.Yes)
            if answer == QtWidgets.QMessageBox.StandardButton.No:
                return

        if self._includeLogisticsCostsCheckBox.isChecked() and \
                self._routingTypeComboBox.currentEnum() == logic.RoutingType.Basic:
            message = 'Using basic routing is not recommended when calculating trade options as the accuracy of logistics estimations is reduced.'
            answer = gui.AutoSelectMessageBox.question(
                parent=self,
                text=message + '\n\nDo you want to continue?',
                stateKey='WorldTraderBasicRoutingWarning',
                # Only remember if the user clicked yes
                rememberState=QtWidgets.QMessageBox.StandardButton.Yes)
            if answer == QtWidgets.QMessageBox.StandardButton.No:
                return

        milieu = app.Config.instance().value(option=app.ConfigOption.Milieu)
        rules = app.Config.instance().value(option=app.ConfigOption.Rules)
        routingType = self._routingTypeComboBox.currentEnum()
        pitCostCalculator = None
        if routingType is not logic.RoutingType.Basic:
            useAnomalyRefuelling = self._useAnomalyRefuellingCheckBox.isChecked()
            pitCostCalculator = logic.PitStopCostCalculator(
                refuellingStrategy=self._refuellingStrategyComboBox.currentEnum(),
                useFuelCaches=self._useFuelCachesCheckBox.isChecked(),
                anomalyFuelCost=self._anomalyFuelCostSpinBox.value() if useAnomalyRefuelling else None,
                anomalyBerthingCost=self._anomalyBerthingCostSpinBox.value() if useAnomalyRefuelling else None,
                rules=rules)

            # Flag cases where the purchase world doesn't match the refuelling
            # strategy. No options will be generated unless the ship has enough
            #current fuel
            if not pitCostCalculator.refuellingType(
                    world=self._purchaseWorldWidget.selectedWorld()):
                message = \
                    'The purchase world doesn\'t support the selected refuelling ' \
                    'strategy. It will only be possibly to generate trade ' \
                    'options for sale worlds where a route can be found with the ' \
                    'fuel currently in the ship.'

                answer = gui.AutoSelectMessageBox.question(
                    parent=self,
                    text=message + '\n\nDo you want to continue?',
                    stateKey='WorldTraderPurchaseWorldRefuellingStrategy',
                    # Only remember if the user clicked yes
                    rememberState=QtWidgets.QMessageBox.StandardButton.Yes)
                if answer == QtWidgets.QMessageBox.StandardButton.No:
                    return

        # Create a jump cost calculator for the selected route optimisation
        routeOptimisation = self._routeOptimisationComboBox.currentEnum()
        if routeOptimisation == logic.RouteOptimisation.ShortestDistance:
            jumpCostCalculator = logic.ShortestDistanceCostCalculator()
        elif routeOptimisation == logic.RouteOptimisation.ShortestTime:
            jumpCostCalculator = logic.ShortestTimeCostCalculator(
                shipJumpRating=self._shipJumpRatingSpinBox.value())
        elif routeOptimisation == logic.RouteOptimisation.LowestCost:
            jumpCostCalculator = logic.CheapestRouteCostCalculator(
                shipTonnage=self._shipTonnageSpinBox.value(),
                shipFuelCapacity=self._shipFuelCapacitySpinBox.value(),
                shipCurrentFuel=self._shipCurrentFuelSpinBox.value(),
                shipFuelPerParsec=self._shipFuelPerParsecSpinBox.value(),
                shipJumpRating=self._shipJumpRatingSpinBox.value(),
                pitCostCalculator=pitCostCalculator,
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
                rules=rules,
                milieu=milieu,
                purchaseWorld=self._purchaseWorldWidget.selectedWorld(),
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
                shipCargoCapacity=self._maxCargoTonnageSpinBox.value(),
                perJumpOverheads=self._perJumpOverheadsSpinBox.value(),
                routingType=routingType,
                jumpCostCalculator=jumpCostCalculator,
                pitCostCalculator=pitCostCalculator,
                includePurchaseWorldBerthing=self._includeStartWorldBerthingCheckBox.isChecked(),
                includeSaleWorldBerthing=self._includeFinishWorldBerthingCheckBox.isChecked(),
                includeUnprofitableTrades=self._showUnprofitableTradesCheckBox.isChecked(),
                includeLogisticsCosts=self._includeLogisticsCostsCheckBox.isChecked(),
                tradeOptionCallback=self._addTradeOptions,
                tradeInfoCallback=self._addTraderInfo,
                progressCallback=self._updateTraderProgress,
                finishedCallback=self._traderJobFinished)
        except Exception as ex:
            message = 'Failed to create trader job'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

        self._calculateTradeOptionsButton.showSecondaryText()
        self._enableDisableControls()

        # Start job after a delay to give the ui time to update
        QtCore.QTimer.singleShot(200, self._traderJobStart)

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
            freeCargoSpace=self._maxCargoTonnageSpinBox.value(),
            tradeOptions=availableCargoTrades if availableCargoTrades else speculativeCargoTrades,
            speculativePurchase=not availableCargoTrades,
            parent=self)
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

    def _showWelcomeMessage(self) -> None:
        message = gui.InfoDialog(
            parent=self,
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
        self._mainSplitter.setStretchFactor(0, 1)
        self._mainSplitter.setStretchFactor(1, 100)

        self._tradeInfoSplitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        self._tradeInfoSplitter.addWidget(self._mainSplitter)
        self._tradeInfoSplitter.addWidget(self._tradeInfoEditBox)

        windowLayout = QtWidgets.QVBoxLayout()
        windowLayout.addWidget(self._tradeInfoSplitter)

        self.setLayout(windowLayout)

    def configureControls(
            self,
            purchaseWorlds: typing.Optional[typing.Iterable[multiverse.World]] = None,
            saleWorlds: typing.Optional[typing.Iterable[multiverse.World]] = None,
            playerBrokerDm: typing.Optional[int] = None,
            minSellerDm: typing.Optional[int] = None,
            maxSellerDm: typing.Optional[int] = None,
            minBuyerDm: typing.Optional[int] = None,
            maxBuyerDm: typing.Optional[int] = None,
            availableFunds: typing.Optional[int] = None,
            shipTonnage: typing.Optional[int] = None,
            shipJumpRating: typing.Optional[int] = None,
            maxCargoTonnage: typing.Optional[int] = None,
            shipFuelCapacity: typing.Optional[int] = None,
            shipCurrentFuel: typing.Optional[float] = None,
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
            self._shipCurrentFuelSpinBox.setValue(float(shipCurrentFuel))
        if maxCargoTonnage != None:
            self._maxCargoTonnageSpinBox.setValue(int(maxCargoTonnage))
        if refuellingStrategy != None:
            self._refuellingStrategyComboBox.setCurrentEnum(refuellingStrategy)
        if perJumpOverheads != None:
            self._perJumpOverheadsSpinBox.setValue(int(perJumpOverheads))
        if purchaseWorlds != None:
            self._purchaseWorldsWidget.removeAllRows()
            for world in purchaseWorlds:
                self._purchaseWorldsWidget.addHex(hex=world.hex())
        if saleWorlds != None:
            self._saleWorldsWidget.removeAllRows()
            for world in saleWorlds:
                self._saleWorldsWidget.addHex(hex=world.hex())

    def loadSettings(self) -> None:
        super().loadSettings()

        self._settings.beginGroup(self._configSection)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='ConfigurationTabBarState',
            type=QtCore.QByteArray)
        if storedValue:
            self._configurationStack.restoreState(storedValue)

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
        self._settings.setValue('ConfigurationTabBarState', self._configurationStack.saveState())
        self._settings.setValue('PurchaseWorldsTableState', self._purchaseWorldsWidget.saveState())
        self._settings.setValue('PurchaseWorldsTableContent', self._purchaseWorldsWidget.saveContent())
        self._settings.setValue('SaleWorldsTableState', self._saleWorldsWidget.saveState())
        self._settings.setValue('SaleWorldsTableContent', self._saleWorldsWidget.saveContent())
        self._settings.setValue('MainSplitterState', self._mainSplitter.saveState())
        self._settings.setValue('TableSplitterState', self._tableSplitter.saveState())
        self._settings.setValue('TradeInfoSplitterState', self._tradeInfoSplitter.saveState())
        self._settings.endGroup()

        super().saveSettings()

    def _setupSaleWorldControls(self) -> None:
        milieu = app.Config.instance().value(option=app.ConfigOption.Milieu)
        rules = app.Config.instance().value(option=app.ConfigOption.Rules)
        mapStyle = app.Config.instance().value(option=app.ConfigOption.MapStyle)
        mapOptions = app.Config.instance().value(option=app.ConfigOption.MapOptions)
        mapRendering = app.Config.instance().value(option=app.ConfigOption.MapRendering)
        mapAnimations = app.Config.instance().value(option=app.ConfigOption.MapAnimations)
        worldTagging = app.Config.instance().value(option=app.ConfigOption.WorldTagging)
        taggingColours = app.Config.instance().value(option=app.ConfigOption.TaggingColours)

        self._saleWorldsWidget = gui.HexTableManagerWidget(
            milieu=milieu,
            rules=rules,
            mapStyle=mapStyle,
            mapOptions=mapOptions,
            mapRendering=mapRendering,
            mapAnimations=mapAnimations,
            worldTagging=worldTagging,
            taggingColours=taggingColours,
            allowHexCallback=self._allowSaleWorld)
        self._saleWorldsWidget.setHexTooltipProvider(
            provider=self._hexTooltipProvider)
        self._saleWorldsWidget.setContextMenuPolicy(
            QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self._saleWorldsWidget.customContextMenuRequested.connect(
            self._showSaleWorldTableContextMenu)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self._saleWorldsWidget)

        self._saleWorldsGroupBox = QtWidgets.QGroupBox('Sale Worlds')
        self._saleWorldsGroupBox.setLayout(layout)

    def _setupPurchaseWorldControls(self) -> None:
        milieu = app.Config.instance().value(option=app.ConfigOption.Milieu)
        rules = app.Config.instance().value(option=app.ConfigOption.Rules)
        mapStyle = app.Config.instance().value(option=app.ConfigOption.MapStyle)
        mapOptions = app.Config.instance().value(option=app.ConfigOption.MapOptions)
        mapRendering = app.Config.instance().value(option=app.ConfigOption.MapRendering)
        mapAnimations = app.Config.instance().value(option=app.ConfigOption.MapAnimations)
        worldTagging = app.Config.instance().value(option=app.ConfigOption.WorldTagging)
        taggingColours = app.Config.instance().value(option=app.ConfigOption.TaggingColours)

        self._purchaseWorldsWidget = gui.HexTableManagerWidget(
            milieu=milieu,
            rules=rules,
            mapStyle=mapStyle,
            mapOptions=mapOptions,
            mapRendering=mapRendering,
            mapAnimations=mapAnimations,
            worldTagging=worldTagging,
            taggingColours=taggingColours,
            allowHexCallback=self._allowPurchaseWorld)
        self._purchaseWorldsWidget.setHexTooltipProvider(
            provider=self._hexTooltipProvider)
        self._purchaseWorldsWidget.setContextMenuPolicy(
            QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self._purchaseWorldsWidget.customContextMenuRequested.connect(
            self._showPurchaseWorldTableContextMenu)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self._purchaseWorldsWidget)

        self._purchaseWorldsGroupBox = QtWidgets.QGroupBox('Purchase Worlds')
        self._purchaseWorldsGroupBox.setLayout(layout)

    def _appConfigChanged(
            self,
            option: app.ConfigOption,
            oldValue: typing.Any,
            newValue: typing.Any
            ) -> None:
        super()._appConfigChanged(
            option=option,
            oldValue=oldValue,
            newValue=newValue)

        if option is app.ConfigOption.Milieu:
            self._purchaseWorldsWidget.setMilieu(milieu=newValue)
            self._saleWorldsWidget.setMilieu(milieu=newValue)
        elif option is app.ConfigOption.Rules:
            self._purchaseWorldsWidget.setRules(rules=newValue)
            self._saleWorldsWidget.setRules(rules=newValue)
        elif option is app.ConfigOption.MapStyle:
            self._purchaseWorldsWidget.setMapStyle(style=newValue)
            self._saleWorldsWidget.setMapStyle(style=newValue)
        elif option is app.ConfigOption.MapOptions:
            self._purchaseWorldsWidget.setMapOptions(options=newValue)
            self._saleWorldsWidget.setMapOptions(options=newValue)
        elif option is app.ConfigOption.MapRendering:
            self._purchaseWorldsWidget.setMapRendering(rendering=newValue)
            self._saleWorldsWidget.setMapRendering(rendering=newValue)
        elif option is app.ConfigOption.MapAnimations:
            self._purchaseWorldsWidget.setMapAnimations(enabled=newValue)
            self._saleWorldsWidget.setMapAnimations(enabled=newValue)
        elif option is app.ConfigOption.WorldTagging:
            self._purchaseWorldsWidget.setWorldTagging(tagging=newValue)
            self._saleWorldsWidget.setWorldTagging(tagging=newValue)
        elif option is app.ConfigOption.TaggingColours:
            self._purchaseWorldsWidget.setTaggingColours(colours=newValue)
            self._saleWorldsWidget.setTaggingColours(colours=newValue)

    def _enableDisableControls(self) -> None:
        super()._enableDisableControls()

        # Disable configuration controls while trade option job is running
        self._configurationGroupBox.setDisabled(self._traderJob != None)
        self._purchaseWorldsGroupBox.setDisabled(self._traderJob != None)
        self._saleWorldsGroupBox.setDisabled(self._traderJob != None)

    def _allowPurchaseWorld(self, hex: multiverse.HexPosition) -> bool:
        # Silently ignore worlds that are already in the table
        return not self._purchaseWorldsWidget.containsHex(hex)

    def _allowSaleWorld(self, hex: multiverse.HexPosition) -> bool:
        # Silently ignore worlds that are already in the table
        return not self._saleWorldsWidget.containsHex(hex)

    def _copyBetweenWorldWidgets(
            self,
            srcWidget: gui.HexTableManagerWidget,
            dstWidget: gui.HexTableManagerWidget
            ) -> None:
        if dstWidget.rowCount() > 0:
            answer = gui.MessageBoxEx.question(
                parent=self,
                text='Remove current worlds before copying?')
            if answer == QtWidgets.QMessageBox.StandardButton.Yes:
                dstWidget.removeAllRows()
        dstWidget.addHexes(hexes=srcWidget.hexes())

    def _showPurchaseWorldTableContextMenu(self, pos: QtCore.QPoint) -> None:
        copyFromSaleWorldsAction = QtWidgets.QAction('Copy from Sale Worlds', self)
        copyFromSaleWorldsAction.setEnabled(not self._saleWorldsWidget.isEmpty())
        copyFromSaleWorldsAction.triggered.connect(
            lambda: self._copyBetweenWorldWidgets(srcWidget=self._saleWorldsWidget, dstWidget=self._purchaseWorldsWidget))

        copyToSaleWorldsAction = QtWidgets.QAction('Copy to Sale Worlds', self)
        copyToSaleWorldsAction.setEnabled(not self._purchaseWorldsWidget.isEmpty())
        copyToSaleWorldsAction.triggered.connect(
            lambda: self._copyBetweenWorldWidgets(srcWidget=self._purchaseWorldsWidget, dstWidget=self._saleWorldsWidget))

        menu = QtWidgets.QMenu()
        self._purchaseWorldsWidget.fillContextMenu(menu)
        beforeAction = self._purchaseWorldsWidget.menuAction(gui.HexTable.MenuAction.ShowSelectionDetails)
        menu.insertAction(
            beforeAction,
            copyFromSaleWorldsAction)
        menu.insertAction(
            beforeAction,
            copyToSaleWorldsAction)
        menu.insertSeparator(
            beforeAction)
        menu.exec(self._purchaseWorldsWidget.mapToGlobal(pos))

    def _showSaleWorldTableContextMenu(self, pos: QtCore.QPoint) -> None:
        copyFromPurchaseWorldsAction = QtWidgets.QAction('Copy from Purchase Worlds', self)
        copyFromPurchaseWorldsAction.setEnabled(not self._purchaseWorldsWidget.isEmpty())
        copyFromPurchaseWorldsAction.triggered.connect(
            lambda: self._copyBetweenWorldWidgets(srcWidget=self._purchaseWorldsWidget, dstWidget=self._saleWorldsWidget))

        copyToPurchaseWorldsAction = QtWidgets.QAction('Copy to Purchase Worlds', self)
        copyToPurchaseWorldsAction.setEnabled(not self._saleWorldsWidget.isEmpty())
        copyToPurchaseWorldsAction.triggered.connect(
            lambda: self._copyBetweenWorldWidgets(srcWidget=self._saleWorldsWidget, dstWidget=self._purchaseWorldsWidget))

        menu = QtWidgets.QMenu()
        self._saleWorldsWidget.fillContextMenu(menu)
        beforeAction = self._purchaseWorldsWidget.menuAction(gui.HexTable.MenuAction.ShowSelectionDetails)
        menu.insertAction(
            beforeAction,
            copyFromPurchaseWorldsAction)
        menu.insertAction(
            beforeAction,
            copyToPurchaseWorldsAction)
        menu.insertSeparator(
            beforeAction)
        menu.exec(self._saleWorldsWidget.mapToGlobal(pos))

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
        if self._maxCargoTonnageSpinBox.value() > self._shipTonnageSpinBox.value():
            gui.MessageBoxEx.information(
                parent=self,
                text='Max cargo tonnage can\'t be larger than the total ship tonnage')
            return
        if (self._shipFuelCapacitySpinBox.value() + self._maxCargoTonnageSpinBox.value()) > \
                self._shipTonnageSpinBox.value():
            gui.MessageBoxEx.information(
                parent=self,
                text='Max cargo tonnage plus ship\'s fuel capacity can\'t be larger than the total ship tonnage')
            return

        if self._shipJumpRatingSpinBox.value() >= app.ConsideredVeryHighJumpRating:
            message = \
                'Your ship has a very high jump rating. This can significantly increase ' \
                'the time it takes to calculate trade options.\n\n' \
                'Do you want to continue?'
            answer = gui.AutoSelectMessageBox.question(
                parent=self,
                text=message,
                stateKey='MultiTraderHighJumpRatingWarning',
                # Only remember if the user clicked yes
                rememberState=QtWidgets.QMessageBox.StandardButton.Yes)
            if answer == QtWidgets.QMessageBox.StandardButton.No:
                return

        if self._includeLogisticsCostsCheckBox.isChecked() and \
                self._routingTypeComboBox.currentEnum() == logic.RoutingType.Basic:
            message = 'Using basic routing is not recommended when calculating trade options as the accuracy of logistics estimations is reduced.'
            answer = gui.AutoSelectMessageBox.question(
                parent=self,
                text=message + '\n\nDo you want to continue?',
                stateKey='MultiTraderBasicRoutingWarning',
                # Only remember if the user clicked yes
                rememberState=QtWidgets.QMessageBox.StandardButton.Yes)
            if answer == QtWidgets.QMessageBox.StandardButton.No:
                return

        milieu = app.Config.instance().value(option=app.ConfigOption.Milieu)
        rules = app.Config.instance().value(option=app.ConfigOption.Rules)
        routingType = self._routingTypeComboBox.currentEnum()
        pitCostCalculator = None
        if routingType is not logic.RoutingType.Basic:
            useAnomalyRefuelling = self._useAnomalyRefuellingCheckBox.isChecked()
            pitCostCalculator = logic.PitStopCostCalculator(
                refuellingStrategy=self._refuellingStrategyComboBox.currentEnum(),
                useFuelCaches=self._useFuelCachesCheckBox.isChecked(),
                anomalyFuelCost=self._anomalyFuelCostSpinBox.value() if useAnomalyRefuelling else None,
                anomalyBerthingCost=self._anomalyBerthingCostSpinBox.value() if useAnomalyRefuelling else None,
                rules=rules)

            # Flag cases where purchase worlds don't match the refuelling strategy. No options will be
            # generated for those worlds unless the ship has enough current fuel
            fuelIssueWorldStrings = []
            for world in self._purchaseWorldsWidget.worlds():
                if not pitCostCalculator.refuellingType(world=world):
                    fuelIssueWorldStrings.append(world.name())

            if fuelIssueWorldStrings:
                worldListString = common.humanFriendlyListString(fuelIssueWorldStrings)
                if len(fuelIssueWorldStrings) == 1:
                    message = f'Purchase world {worldListString} doesn\'t support the selected refuelling strategy. '
                else:
                    message = f'Purchase worlds {worldListString} don\'t support the selected refuelling strategy. '
                message += 'It will only be possibly to generate trade options for sale worlds where a route can be found with fuel currently in the ship.'

                answer = gui.AutoSelectMessageBox.question(
                    parent=self,
                    text=message + '\n\nDo you want to continue?',
                    stateKey='MultiTraderPurchaseWorldRefuellingStrategy',
                    # Only remember if the user clicked yes
                    rememberState=QtWidgets.QMessageBox.StandardButton.Yes)
                if answer == QtWidgets.QMessageBox.StandardButton.No:
                    return

        # Create a jump cost calculator for the selected route optimisation
        routeOptimisation = self._routeOptimisationComboBox.currentEnum()
        if routeOptimisation == logic.RouteOptimisation.ShortestDistance:
            jumpCostCalculator = logic.ShortestDistanceCostCalculator()
        elif routeOptimisation == logic.RouteOptimisation.ShortestTime:
            jumpCostCalculator = logic.ShortestTimeCostCalculator(
                shipJumpRating=self._shipJumpRatingSpinBox.value())
        elif routeOptimisation == logic.RouteOptimisation.LowestCost:
            jumpCostCalculator = logic.CheapestRouteCostCalculator(
                shipTonnage=self._shipTonnageSpinBox.value(),
                shipFuelCapacity=self._shipFuelCapacitySpinBox.value(),
                shipCurrentFuel=self._shipCurrentFuelSpinBox.value(),
                shipFuelPerParsec=self._shipFuelPerParsecSpinBox.value(),
                shipJumpRating=self._shipJumpRatingSpinBox.value(),
                pitCostCalculator=pitCostCalculator,
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
                rules=rules,
                milieu=milieu,
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
                shipCargoCapacity=self._maxCargoTonnageSpinBox.value(),
                routingType=routingType,
                perJumpOverheads=self._perJumpOverheadsSpinBox.value(),
                jumpCostCalculator=jumpCostCalculator,
                pitCostCalculator=pitCostCalculator,
                includeIllegal=True, # Always include illegal trade options for multi-world
                includePurchaseWorldBerthing=self._includeStartWorldBerthingCheckBox.isChecked(),
                includeSaleWorldBerthing=self._includeFinishWorldBerthingCheckBox.isChecked(),
                includeUnprofitableTrades=self._showUnprofitableTradesCheckBox.isChecked(),
                includeLogisticsCosts=self._includeLogisticsCostsCheckBox.isChecked(),
                tradeOptionCallback=self._addTradeOptions,
                tradeInfoCallback=self._addTraderInfo,
                progressCallback=self._updateTraderProgress,
                finishedCallback=self._traderJobFinished)
        except Exception as ex:
            message = 'Failed to create trader job'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

        self._calculateTradeOptionsButton.showSecondaryText()
        self._enableDisableControls()

        # Start job after a delay to give the ui time to update
        QtCore.QTimer.singleShot(200, self._traderJobStart)

    def _createCargoManifest(self) -> None:
        if self._tradeOptionsTable.isEmpty():
            gui.MessageBoxEx.information(
                parent=self,
                text='No trade options to generate cargo manifest from')
            return

        dlg = gui.CargoManifestDialog(
            parent=self,
            availableFunds=self._availableFundsSpinBox.value(),
            freeCargoSpace=self._maxCargoTonnageSpinBox.value(),
            tradeOptions=self._tradeOptionsTable.tradeOptions(),
            speculativePurchase=True) # Multi world trade option calculations are always speculative
        dlg.exec()

    def _showWelcomeMessage(self) -> None:
        message = gui.InfoDialog(
            parent=self,
            title=self.windowTitle(),
            html=_MultiWorldWelcomeMessage,
            noShowAgainId='MultiWorldTraderWelcome')
        message.exec()
