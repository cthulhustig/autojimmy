import common
import gui
import logging
import logic
import traveller
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

_WelcomeMessage = """
    <html>
    <p>The Cargo Manifest window takes Trade Options created by the trading engine for speculative
    or available cargo and generates Cargo Manifests that would make optimal use of available funds
    and cargo space.</p>
    <p>Unlike the Trade Options generated by the trading engine, where each option is for a single
    type of Trade Good and logistics costs are applied for each one. Cargo Manifests can contain
    multiple types of Trade Good and logistics costs are only applied once for the manifest as a
    whole.</p>
    </html>
"""

class CargoManifestDialog(gui.DialogEx):
    _AverageCaseTradeOptionColumns = [
        gui.TradeOptionsTable.ColumnType.TradeGood,
        gui.TradeOptionsTable.ColumnType.AverageGrossProfit,
        gui.TradeOptionsTable.ColumnType.AverageProfitPerTon,
        gui.TradeOptionsTable.ColumnType.AveragePurchasePricePerTon,
        gui.TradeOptionsTable.ColumnType.AverageSalePricePerTon,
        gui.TradeOptionsTable.ColumnType.AverageQuantity
    ]
    _WorstCaseTradeOptionColumns = [
        gui.TradeOptionsTable.ColumnType.TradeGood,
        gui.TradeOptionsTable.ColumnType.WorstGrossProfit,
        gui.TradeOptionsTable.ColumnType.WorstProfitPerTon,
        gui.TradeOptionsTable.ColumnType.WorstPurchasePricePerTon,
        gui.TradeOptionsTable.ColumnType.WorstSalePricePerTon,
        gui.TradeOptionsTable.ColumnType.WorstQuantity
    ]
    _BestCaseTradeOptionColumns = [
        gui.TradeOptionsTable.ColumnType.TradeGood,
        gui.TradeOptionsTable.ColumnType.BestGrossProfit,
        gui.TradeOptionsTable.ColumnType.BestProfitPerTon,
        gui.TradeOptionsTable.ColumnType.BestPurchasePricePerTon,
        gui.TradeOptionsTable.ColumnType.BestSalePricePerTon,
        gui.TradeOptionsTable.ColumnType.BestQuantity
    ]

    def __init__(
            self,
            availableFunds: int,
            freeCargoSpace: int,
            tradeOptions: typing.Iterable[logic.TradeOption],
            speculativePurchase: bool = False,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            title='Cargo Manifest',
            configSection='CargoManifestDialog',
            parent=parent)

        self._availableFunds = availableFunds
        self._freeCargoSpace = freeCargoSpace
        self._tradeOptions = tradeOptions

        self._setupConfigurationControls(speculativePurchase)
        self._setupManifestControls()
        self._setupActionControls(speculativePurchase)

        dialogLayout = QtWidgets.QVBoxLayout()
        dialogLayout.addWidget(self._configurationGroupBox)
        dialogLayout.addWidget(self._cargoManifestGroupBox)
        dialogLayout.addLayout(self._buttonLayout)

        self.setLayout(dialogLayout)
        self.setWindowFlag(QtCore.Qt.WindowType.WindowMaximizeButtonHint, True)
        self.resize(800, 600)

        self._generateCargoManifests()

    def isPurchaseSelectedChecked(self) -> bool:
        if not self._purchaseSelectedCheckBox:
            return False
        return self._purchaseSelectedCheckBox.isChecked()

    def selectedCargoManifest(self) -> logic.CargoManifest:
        return self._cargoManifestsTable.currentCargoManifest()

    def firstShowEvent(self, e: QtGui.QShowEvent) -> None:
        QtCore.QTimer.singleShot(0, self._showWelcomeMessage)
        super().firstShowEvent(e)

    def loadSettings(self) -> None:
        super().loadSettings()

        self._settings.beginGroup(self._configSection)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='PurchaseLogicState',
            type=QtCore.QByteArray)
        if storedValue:
            self._purchaseLogicComboBox.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='LogisticsLogicState',
            type=QtCore.QByteArray)
        if storedValue:
            self._logisticsLogicComboBox.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='CargoManifestDisplayModeState',
            type=QtCore.QByteArray)
        if storedValue:
            self._cargoManifestDisplayModeTabs.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='CargoManifestTableState',
            type=QtCore.QByteArray)
        if storedValue:
            self._cargoManifestsTable.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='CargoBreakdownTableState',
            type=QtCore.QByteArray)
        if storedValue:
            self._cargoBreakdownTable.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='CargoManifestSplitterState',
            type=QtCore.QByteArray)
        if storedValue:
            self._cargoManifestSplitter.restoreState(storedValue)

        self._settings.endGroup()

    def saveSettings(self) -> None:
        self._settings.beginGroup(self._configSection)

        self._settings.setValue('PurchaseLogicState', self._purchaseLogicComboBox.saveState())
        self._settings.setValue('LogisticsLogicState', self._logisticsLogicComboBox.saveState())
        self._settings.setValue('CargoManifestDisplayModeState', self._cargoManifestDisplayModeTabs.saveState())
        self._settings.setValue('CargoManifestTableState', self._cargoManifestsTable.saveState())
        self._settings.setValue('CargoBreakdownTableState', self._cargoBreakdownTable.saveState())
        self._settings.setValue('CargoManifestSplitterState', self._cargoManifestSplitter.saveState())

        self._settings.endGroup()

        super().saveSettings()

    def _setupConfigurationControls(
            self,
            speculativePurchase: bool
            ) -> None:
        self._purchaseLogicComboBox = gui.ProbabilityCaseComboBox(
            value=logic.ProbabilityCase.AverageCase)
        self._purchaseLogicComboBox.activated.connect(self._logicSelectionChanged)
        self._purchaseLogicComboBox.setToolTip(
            gui.createStringToolTip(
                '<p>In order to create a cargo manifest from speculative cargo, the system ' \
                'must be told which purchase price and availability it should base its ' \
                'calculations on. This lets you choose if it should be based on the values ' \
                'from average, worst or best case dice rolls. This will determine how much ' \
                'cargo the calculations will expect you to be able to buy.</p>' \
                '<p>It\'s recommended to leave this set to average case. If you were to roll ' \
                'significantly below average you\'d walk away from the deal rather than buy ' \
                'at massively inflated prices.</p>',
                escape=False))
        if not speculativePurchase:
            # Selecting the purchase logic only makes sense when using speculative purchase price
            # and availability
            self._purchaseLogicComboBox.hide()

        # Defaulting logistics logic to worst case is the safe option as it avoids purchasing so
        # much you risk running out of funds on route
        self._logisticsLogicComboBox = gui.ProbabilityCaseComboBox(
            value=logic.ProbabilityCase.WorstCase)
        self._logisticsLogicComboBox.activated.connect(self._logicSelectionChanged)
        self._logisticsLogicComboBox.setToolTip(
            gui.createStringToolTip(
                '<p>In order to create a cargo manifest the system must be told which logistics ' \
                'costs it should base its calculations on. This lets you choose if it should ' \
                'be based on the values from average, worst or best case dice rolls. This will ' \
                'determine how much of your available funds the system will allocate for cargo. ' \
                'This is done to prevent there being insufficient funds left to travel to the ' \
                'sale world once the cargo has been purchased.</p>' \
                '<p>Using worst case logistics costs is recommended as it avoids the risk of running ' \
                'out of funds en route due to bad dice rolls.</p>',
                escape=False))

        groupLayout = QtWidgets.QHBoxLayout()
        if speculativePurchase:
            groupLayout.addLayout(gui.createLabelledWidgetLayout(
                'Purchase Logic:',
                self._purchaseLogicComboBox))
        groupLayout.addLayout(gui.createLabelledWidgetLayout(
            'Logistics Logic:',
            self._logisticsLogicComboBox))
        groupLayout.addStretch(1)

        self._configurationGroupBox = QtWidgets.QGroupBox('Configuration')
        self._configurationGroupBox.setLayout(groupLayout)

    def _setupManifestControls(self):
        self._cargoManifestDisplayModeTabs = gui.CalculationModeTabBar()
        self._cargoManifestDisplayModeTabs.currentChanged.connect(
            self._cargoManifestDisplayModeChanged)

        self._cargoManifestsTable = gui.CargoManifestTable()
        self._cargoManifestsTable.setVisibleColumns(self._cargoManifestColumns())
        self._cargoManifestsTable.sortByColumnHeader(
            self._cargoManifestDefaultSortColumn(),
            QtCore.Qt.SortOrder.DescendingOrder)
        self._cargoManifestsTable.setContextMenuPolicy(
            QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self._cargoManifestsTable.selectionModel().selectionChanged.connect(
            self._cargoManifestTableSelectionChanged)
        self._cargoManifestsTable.customContextMenuRequested.connect(
            self._showCargoManifestTableContextMenu)
        self._cargoManifestsTable.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)

        self._cargoBreakdownTable = gui.TradeOptionsTable()
        self._cargoBreakdownTable.setVisibleColumns(self._cargoBreakdownColumns())
        self._cargoBreakdownTable.sortByColumnHeader(
            self._cargoBreakdownDefaultSortColumn(),
            QtCore.Qt.SortOrder.DescendingOrder)
        self._cargoBreakdownTable.setContextMenuPolicy(
            QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self._cargoBreakdownTable.customContextMenuRequested.connect(
            self._showCargoBreakdownTableContextMenu)

        self._cargoManifestSplitter = QtWidgets.QSplitter(
            QtCore.Qt.Orientation.Vertical)
        self._cargoManifestSplitter.addWidget(self._cargoManifestsTable)
        self._cargoManifestSplitter.addWidget(self._cargoBreakdownTable)

        groupLayout = QtWidgets.QVBoxLayout()
        groupLayout.setSpacing(0)
        groupLayout.addWidget(self._cargoManifestDisplayModeTabs)
        groupLayout.addWidget(self._cargoManifestSplitter)

        self._cargoManifestGroupBox = QtWidgets.QGroupBox('Cargo Manifests')
        self._cargoManifestGroupBox.setLayout(groupLayout)

    def _setupActionControls(
            self,
            speculativePurchase: bool
            ) -> None:
        self._purchaseSelectedCheckBox = gui.CheckBoxEx(
            'Purchase the selected cargo manifest')
        if speculativePurchase:
            # Purchasing the cargo only makes sense when the purchase price and availability are known
            self._purchaseSelectedCheckBox.hide()

        self._closeButton = QtWidgets.QPushButton('Close')
        self._closeButton.setDefault(True)
        self._closeButton.clicked.connect(self.close)

        self._buttonLayout = QtWidgets.QHBoxLayout()
        self._buttonLayout.addStretch()
        self._buttonLayout.addWidget(self._purchaseSelectedCheckBox)
        self._buttonLayout.addWidget(self._closeButton)

    def _showWorldDetails(
            self,
            worlds: typing.Iterable[traveller.World]
            ) -> None:
        detailsWindow = gui.WindowManager.instance().showWorldDetailsWindow()
        detailsWindow.addWorlds(worlds=worlds)

    def _cargoManifestColumns(self) -> typing.List[gui.CargoManifestTable.ColumnType]:
        calculationMode = self._cargoManifestDisplayModeTabs.currentCalculationMode()
        if calculationMode == gui.CalculationModeTabBar.CalculationMode.AverageCase:
            return gui.CargoManifestTable.AverageCaseColumns
        elif calculationMode == gui.CalculationModeTabBar.CalculationMode.WorstCase:
            return gui.CargoManifestTable.WorstCaseColumns
        elif calculationMode == gui.CalculationModeTabBar.CalculationMode.BestCase:
            return gui.CargoManifestTable.BestCaseColumns
        else:
            assert(False) # I missed a case

    def _cargoManifestDefaultSortColumn(self) -> gui.CargoManifestTable.ColumnType:
        calculationMode = self._cargoManifestDisplayModeTabs.currentCalculationMode()
        if calculationMode == gui.CalculationModeTabBar.CalculationMode.AverageCase:
            return gui.CargoManifestTable.ColumnType.AverageNetProfit
        elif calculationMode == gui.CalculationModeTabBar.CalculationMode.WorstCase:
            return gui.CargoManifestTable.ColumnType.WorstNetProfit
        elif calculationMode == gui.CalculationModeTabBar.CalculationMode.BestCase:
            return gui.CargoManifestTable.ColumnType.BestNetProfit
        else:
            assert(False) # I missed a case

    def _cargoBreakdownColumns(self) -> typing.List[gui.TradeOptionsTable.ColumnType]:
        calculationMode = self._cargoManifestDisplayModeTabs.currentCalculationMode()
        if calculationMode == gui.CalculationModeTabBar.CalculationMode.AverageCase:
            return CargoManifestDialog._AverageCaseTradeOptionColumns
        elif calculationMode == gui.CalculationModeTabBar.CalculationMode.WorstCase:
            return CargoManifestDialog._WorstCaseTradeOptionColumns
        elif calculationMode == gui.CalculationModeTabBar.CalculationMode.BestCase:
            return CargoManifestDialog._BestCaseTradeOptionColumns
        else:
            assert(False) # I missed a case

    def _cargoBreakdownDefaultSortColumn(self) -> gui.TradeOptionsTable.ColumnType:
        calculationMode = self._cargoManifestDisplayModeTabs.currentCalculationMode()
        if calculationMode == gui.CalculationModeTabBar.CalculationMode.AverageCase:
            return gui.TradeOptionsTable.ColumnType.AverageGrossProfit
        elif calculationMode == gui.CalculationModeTabBar.CalculationMode.WorstCase:
            return gui.TradeOptionsTable.ColumnType.WorstGrossProfit
        elif calculationMode == gui.CalculationModeTabBar.CalculationMode.BestCase:
            return gui.TradeOptionsTable.ColumnType.BestGrossProfit
        else:
            assert(False) # I missed a case

    def _showCalculations(
            self,
            calculation: typing.Union[common.ScalarCalculation, common.RangeCalculation]
            ) -> None:
        try:
            calculationWindow = gui.WindowManager.instance().showCalculationWindow()
            calculationWindow.showCalculation(calculation=calculation)
        except Exception as ex:
            message = 'Failed to show calculations'
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

    def _generateCargoManifests(self) -> None:
        self._cargoManifestsTable.removeAllRows()

        # If the purchase logic combo box isn't shown then it means we're using known
        # purchase price and availability. In this case just specify average purchase
        # logic but it shouldn't matter
        probabilityLogic = self._purchaseLogicComboBox.currentCase() if self._purchaseLogicComboBox.isEnabled() else logic.ProbabilityCase.AverageCase

        try:
            cargoManifests = logic.generateCargoManifests(
                availableFunds=self._availableFunds,
                shipCargoCapacity=self._freeCargoSpace,
                tradeOptions=self._tradeOptions,
                purchaseLogic=probabilityLogic,
                logisticsLogic=self._logisticsLogicComboBox.currentCase())
        except Exception as ex:
            message = 'Failed to generate cargo manifest'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

        if not cargoManifests:
            gui.MessageBoxEx.critical(
                parent=self,
                text='No affordable cargo manifests found.')
            return

        for cargoManifest in cargoManifests:
            self._cargoManifestsTable.addCargoManifest(cargoManifest)

    def _logicSelectionChanged(self, index: int) -> None:
        self._generateCargoManifests()

    def _cargoManifestDisplayModeChanged(self, index: int) -> None:
        self._cargoManifestsTable.setVisibleColumns(self._cargoManifestColumns())
        self._cargoBreakdownTable.setVisibleColumns(self._cargoBreakdownColumns())

    def _cargoManifestTableSelectionChanged(self) -> None:
        self._cargoBreakdownTable.removeAllRows()

        cargoManifest = self._cargoManifestsTable.currentCargoManifest()
        if not cargoManifest:
            return

        for tradeOption in cargoManifest.tradeOptions():
            self._cargoBreakdownTable.addTradeOption(tradeOption)

    def _showCargoManifestTableContextMenu(self, position: QtCore.QPoint) -> None:
        cargoManifest = self._cargoManifestsTable.cargoManifestAt(position)

        menuItems = [
            gui.MenuItem(
                text='Show Purchase World Details...',
                callback=lambda: self._showWorldDetails([cargoManifest.purchaseWorld()]),
                enabled=cargoManifest != None
            ),
            gui.MenuItem(
                text='Show Sale World Details...',
                callback=lambda: self._showWorldDetails([cargoManifest.saleWorld()]),
                enabled=cargoManifest != None
            ),
            gui.MenuItem(
                text='Show Purchase && Sale World Details...',
                callback=lambda: self._showWorldDetails([cargoManifest.purchaseWorld(), cargoManifest.saleWorld()]),
                enabled=cargoManifest != None
            ),
            None, # Separator
            gui.MenuItem(
                text='Show Purchase World in Traveller Map...',
                callback=lambda: self._showWorldsInTravellerMap([cargoManifest.purchaseWorld()]),
                enabled=cargoManifest != None
            ),
            gui.MenuItem(
                text='Show Sale World in Traveller Map...',
                callback=lambda: self._showWorldsInTravellerMap([cargoManifest.saleWorld()]),
                enabled=cargoManifest != None
            ),
            gui.MenuItem(
                text='Show Purchase && Sale Worlds in Traveller Map...',
                callback=lambda: self._showWorldsInTravellerMap([cargoManifest.purchaseWorld(), cargoManifest.saleWorld()]),
                enabled=cargoManifest != None
            ),
            gui.MenuItem(
                text='Show Jump Route in Traveller Map...',
                callback=lambda: self._showJumpRouteInTravellerMap(cargoManifest.jumpRoute()),
                enabled=cargoManifest != None
            ),
            None, # Separator
            gui.MenuItem(
                text='Show Cargo Manifest Calculations...',
                callback=lambda: self._showCalculations(cargoManifest.netProfit()),
                enabled=cargoManifest != None
            )
        ]

        gui.displayMenu(
            self,
            menuItems,
            self._cargoManifestsTable.viewport().mapToGlobal(position))

    def _showCargoBreakdownTableContextMenu(self, position: QtCore.QPoint) -> None:
        tradeOption = self._cargoBreakdownTable.tradeOptionAt(position)

        menuItems = [
            # When showing trade option calculation we show the calculation for the gross profit
            # (rather than net profit) as logistics don't apply to individual trade options when
            # working with a cargo manifest
            gui.MenuItem(
                text='Show Trade Option Calculations...',
                callback=lambda: self._showCalculations(tradeOption.grossProfit()),
                enabled=tradeOption != None
            )
        ]

        gui.displayMenu(
            self,
            menuItems,
            self._cargoBreakdownTable.viewport().mapToGlobal(position))

    def _showWelcomeMessage(self) -> None:
        message = gui.InfoDialog(
            title=self.windowTitle(),
            html=_WelcomeMessage,
            noShowAgainId='CargoManifestWelcome')
        message.exec()