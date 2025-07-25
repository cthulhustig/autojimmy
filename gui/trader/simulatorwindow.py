import app
import common
import gui
import jobs
import logging
import logic
import math
import random
import traveller
import travellermap
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

_WelcomeMessage = """
    <html>
    <p>The Trade Simulator is an <b>incredibly basic</b> simulation of a trader travelling the
    universe, following the Mongoose rules to buy and sell goods. It was initially created
    as a hack to prove that, at least in theory, the results from the trading engine could be used
    to make a profit. I mainly left it in the app as I couldn't bring myself to delete it.</p>
    <p>You can pick a start world and configure various starting parameters, set it going then lean
    back and watch it try to make some credits. The AI (I use that term in the loosest possible way)
    will follow the rules from the Mongoose core rules for finding a seller, calculating what goods
    they have available along with quantities and prices. This information is passed to the trading
    engine which will estimate potential profits and generate Cargo Manifests for trading with all
    the worlds in the surrounding area (including reselling the goods on the current world). The AI
    then purchases cargo based on which Cargo Manifest has the best estimated average profit and
    jumps to the sale world for said manifest. When it reaches its destination, it follows the
    Mongoose core rules for finding a buyer, sells the cargo it has and repeats the process.</p>
    <p>Some things worth knowing about the way the simulation works</p>
    <ul style="margin-left:15px; -qt-list-indent:0;">
    <li>The AI operates in a completely unrealistic version of the Traveller universe. Nothing
    <b>ever</b> goes wrong. The ship never breaks down, the trader the AI is dealing with never
    tries to rip it off and most importantly it never gets boarded by a psionic cult and made to
    take them to a zombie hell world.</li>
    <li>Other than the Trade Codes that determine potential profit, the AI doesn't take any other
    information about the destination world into account when selecting a Cargo Manifest. It could
    be a penal colony or have just 10 people living there, if it has the most potential for profit
    then it doesn't care. As it's just following the basic trading rules as written, these other
    world attributes don't affect it.</li>
    <li>The AI acts as if it's actually multiple crew members. When trying to find a buyer or
    seller it assumes there are 3 crew members and each one can use a different skill (broker,
    streetwise and admin) to find one.</li>
    <li>The AI will never sell at a loss. If it finds a seller, but selling would result in a loss,
    it follows the Mongoose rules for finding a new seller. However, it's also not picky about how
    much profit it has to make, as long as the profit is over 0 it will sell its cargo.</li>
    <li>It doesn't take ship servicing into account directly. This can be accounted for using the
    per-jump overhead.</li>
    <li>The simulation doesn't account for the time taken to travel between jump points and the
    system worlds. I've not found a central source for the system information that would be required
    to calculate this.</li>
    <li>There are probably a lot of other inaccuracies in how the rules are implemented, it was
    just intended to be the bare minimum for what was needed at the time.</li>
    </ul></p>
    <p>{name} integrates with Traveller Map in order to show the virtual traveller moving around the
    universe. This feature requires an internet connection.</p>
    </html>
""".format(name=app.AppName)

class _RandomSeedWidget(QtWidgets.QWidget):
    def __init__(
            self,
            maxDigits: int,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self._maxDigits = maxDigits

        self._numberLineEdit = gui.IntegerLineEdit(
            minValue=0,
            maxValue=int('9' * self._maxDigits))
        self._numberLineEdit.setNumber(self._generateRandomSeed())

        self._newSeedButton = QtWidgets.QPushButton()
        self._newSeedButton.setIcon(gui.loadIcon(gui.Icon.Reload))
        self._newSeedButton.clicked.connect(self._newSeedButtonClicked)
        self._newSeedButton.setFixedSize(
            self._numberLineEdit.height(),
            self._numberLineEdit.height())

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._numberLineEdit)
        layout.addWidget(self._newSeedButton)
        layout.addStretch()

        self.setLayout(layout)

    def number(self) -> int:
        return self._numberLineEdit.number()

    def saveState(self) -> QtCore.QByteArray:
        return self._numberLineEdit.saveState()

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        return self._numberLineEdit.restoreState(state=state)

    def _newSeedButtonClicked(self) -> None:
        self._numberLineEdit.setNumber(self._generateRandomSeed())

    def _generateRandomSeed(self) -> int:
        return random.randint(
            int('1' + ('0' * (self._maxDigits - 1))),
            int('9' * self._maxDigits))

class SimulatorWindow(gui.WindowWidget):
    _RandomSeedMaxDigits = 8

    def __init__(self) -> None:
        super().__init__(
            title='Trade Simulator',
            configSection='SimulatorWindow')

        self._currentHex = None
        self._parsecsTravelled = 0
        self._simulatorJob = None

        self._hexTooltipProvider = gui.HexTooltipProvider(
            milieu=app.Config.instance().value(option=app.ConfigOption.Milieu),
            rules=app.Config.instance().value(option=app.ConfigOption.Rules),
            showImages=app.Config.instance().value(option=app.ConfigOption.ShowToolTipImages),
            mapStyle=app.Config.instance().value(option=app.ConfigOption.MapStyle),
            mapOptions=app.Config.instance().value(option=app.ConfigOption.MapOptions),
            worldTagging=app.Config.instance().value(option=app.ConfigOption.WorldTagging),
            taggingColours=app.Config.instance().value(option=app.ConfigOption.TaggingColours))

        self._setupConfigControls()
        self._setupSimulationControls()
        self._setupMessageControls()

        self._enableDisableControls()

        leftLayout = QtWidgets.QVBoxLayout()
        leftLayout.setContentsMargins(0, 0, 0, 0)
        leftLayout.addWidget(self._configGroupBox)
        leftLayout.addStretch()
        leftWidget = QtWidgets.QWidget()
        leftWidget.setLayout(leftLayout)

        self._leftRightSplitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self._leftRightSplitter.addWidget(leftWidget)
        self._leftRightSplitter.addWidget(self._simulationGroupBox)
        self._leftRightSplitter.setStretchFactor(0, 1)
        self._leftRightSplitter.setStretchFactor(1, 100)

        self._topBottomSplitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        self._topBottomSplitter.addWidget(self._leftRightSplitter)
        self._topBottomSplitter.addWidget(self._simInfoEditBox)

        windowLayout = QtWidgets.QVBoxLayout()
        windowLayout.addWidget(self._topBottomSplitter)

        self.setLayout(windowLayout)

        app.Config.instance().configChanged.connect(self._appConfigChanged)

    def firstShowEvent(self, e: QtGui.QShowEvent) -> None:
        QtCore.QTimer.singleShot(0, self._showWelcomeMessage)

        super().firstShowEvent(e)

        # Center the map on the start hex if one is selected. This must be done
        # after the base firstShowEvent is called as it loads the window
        # settings including the previously selected start world
        currentHex = self._startWorldWidget.selectedHex()
        if currentHex:
            self._mapWidget.centerOnHex(
                hex=currentHex,
                 # Immediate to prevent ugly scrolling from current map position
                immediate=True)

    def loadSettings(self) -> None:
        super().loadSettings()

        self._settings.beginGroup(self._configSection)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='StartWorldState',
            type=QtCore.QByteArray)
        if storedValue:
            self._startWorldWidget.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='RandomSeed',
            type=QtCore.QByteArray)
        if storedValue:
            self._randomSeedWidget.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='StartingFundsState',
            type=QtCore.QByteArray)
        if storedValue:
            self._startingFundsSpinBox.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='PlayerBrokerDMState',
            type=QtCore.QByteArray)
        if storedValue:
            self._playerBrokerDmSpinBox.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='PlayerStreetwiseDMState',
            type=QtCore.QByteArray)
        if storedValue:
            self._playerStreetwiseDmSpinBox.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='PlayerAdminDMState',
            type=QtCore.QByteArray)
        if storedValue:
            self._playerAdminDmSpinBox.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='SellerDmRangeState',
            type=QtCore.QByteArray)
        if storedValue:
            self._sellerDmRangeWidget.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='ShipTonnageState',
            type=QtCore.QByteArray)
        if storedValue:
            self._shipTonnageSpinBox.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='ShipJumpRatingState',
            type=QtCore.QByteArray)
        if storedValue:
            self._shipJumpRatingSpinBox.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='ShipCargoCapacityState',
            type=QtCore.QByteArray)
        if storedValue:
            self._shipCargoCapacitySpinBox.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='ShipFuelCapacityState',
            type=QtCore.QByteArray)
        if storedValue:
            self._shipFuelCapacitySpinBox.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='ShipFuelPerParsec',
            type=QtCore.QByteArray)
        if storedValue:
            self._shipFuelPerParsecSpinBox.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='PerJumpOverheadsState',
            type=QtCore.QByteArray)
        if storedValue:
            self._perJumpOverheadsSpinBox.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='BuyerDmRangeState',
            type=QtCore.QByteArray)
        if storedValue:
            self._buyerDmRangeWidget.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='RefuellingStrategyState',
            type=QtCore.QByteArray)
        if storedValue:
            self._refuellingStrategyComboBox.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='UseFuelCachesState',
            type=QtCore.QByteArray)
        if storedValue:
            self._useFuelCachesCheckBox.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='UseAnomalyRefuellingState',
            type=QtCore.QByteArray)
        if storedValue:
            self._useAnomalyRefuellingCheckBox.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='AnomalyFuelCostState',
            type=QtCore.QByteArray)
        if storedValue:
            self._anomalyFuelCostSpinBox.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='AnomalyBerthingCostState',
            type=QtCore.QByteArray)
        if storedValue:
            self._anomalyBerthingCostSpinBox.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='RouteOptimisationState',
            type=QtCore.QByteArray)
        if storedValue:
            self._routeOptimisationComboBox.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='SearchRadiusState',
            type=QtCore.QByteArray)
        if storedValue:
            self._searchRadiusSpinBox.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='MapWidgetState',
            type=QtCore.QByteArray)
        if storedValue:
            self._mapWidget.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='LeftRightSplitterState',
            type=QtCore.QByteArray)
        if storedValue:
            self._leftRightSplitter.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='TopBottomSplitterState',
            type=QtCore.QByteArray)
        if storedValue:
            self._topBottomSplitter.restoreState(storedValue)

        self._settings.endGroup()

    def saveSettings(self) -> None:
        self._settings.beginGroup(self._configSection)

        self._settings.setValue('StartWorldState', self._startWorldWidget.saveState())
        self._settings.setValue('RandomSeed', self._randomSeedWidget.saveState())
        self._settings.setValue('StartingFundsState', self._startingFundsSpinBox.saveState())
        self._settings.setValue('PlayerBrokerDMState', self._playerBrokerDmSpinBox.saveState())
        self._settings.setValue('PlayerStreetwiseDMState', self._playerStreetwiseDmSpinBox.saveState())
        self._settings.setValue('PlayerAdminDMState', self._playerAdminDmSpinBox.saveState())
        self._settings.setValue('SellerDmRangeState', self._sellerDmRangeWidget.saveState())
        self._settings.setValue('BuyerDmRangeState', self._buyerDmRangeWidget.saveState())
        self._settings.setValue('ShipTonnageState', self._shipTonnageSpinBox.saveState())
        self._settings.setValue('ShipJumpRatingState', self._shipJumpRatingSpinBox.saveState())
        self._settings.setValue('ShipCargoCapacityState', self._shipCargoCapacitySpinBox.saveState())
        self._settings.setValue('ShipFuelCapacityState', self._shipFuelCapacitySpinBox.saveState())
        self._settings.setValue('ShipFuelPerParsec', self._shipFuelPerParsecSpinBox.saveState())
        self._settings.setValue('PerJumpOverheadsState', self._perJumpOverheadsSpinBox.saveState())
        self._settings.setValue('RefuellingStrategyState', self._refuellingStrategyComboBox.saveState())
        self._settings.setValue('UseFuelCachesState', self._useFuelCachesCheckBox.saveState())
        self._settings.setValue('UseAnomalyRefuellingState', self._useAnomalyRefuellingCheckBox.saveState())
        self._settings.setValue('AnomalyFuelCostState', self._anomalyFuelCostSpinBox.saveState())
        self._settings.setValue('AnomalyBerthingCostState', self._anomalyBerthingCostSpinBox.saveState())
        self._settings.setValue('RouteOptimisationState', self._routeOptimisationComboBox.saveState())
        self._settings.setValue('SearchRadiusState', self._searchRadiusSpinBox.saveState())
        self._settings.setValue('MapWidgetState', self._mapWidget.saveState())
        self._settings.setValue('LeftRightSplitterState', self._leftRightSplitter.saveState())
        self._settings.setValue('TopBottomSplitterState', self._topBottomSplitter.saveState())

        self._settings.endGroup()

        super().saveSettings()

    def closeEvent(self, e: QtGui.QCloseEvent):
        if self._simulatorJob:
            self._simulatorJob.cancel(block=True)
            self._simulatorJob = None
        return super().closeEvent(e)

    def _setupConfigControls(self) -> None:
        milieu = app.Config.instance().value(option=app.ConfigOption.Milieu)
        rules = app.Config.instance().value(option=app.ConfigOption.Rules)
        mapStyle = app.Config.instance().value(option=app.ConfigOption.MapStyle)
        mapOptions = app.Config.instance().value(option=app.ConfigOption.MapOptions)
        mapRendering = app.Config.instance().value(option=app.ConfigOption.MapRendering)
        mapAnimations = app.Config.instance().value(option=app.ConfigOption.MapAnimations)
        worldTagging = app.Config.instance().value(option=app.ConfigOption.WorldTagging)
        taggingColours = app.Config.instance().value(option=app.ConfigOption.TaggingColours)

        self._startWorldWidget = gui.HexSelectToolWidget(
            milieu=milieu,
            rules=rules,
            mapStyle=mapStyle,
            mapOptions=mapOptions,
            mapRendering=mapRendering,
            mapAnimations=mapAnimations,
            worldTagging=worldTagging,
            taggingColours=taggingColours,
            labelText='Start World:')
        self._startWorldWidget.setHexTooltipProvider(
            provider=self._hexTooltipProvider)
        self._startWorldWidget.enableShowHexButton(True)
        self._startWorldWidget.enableShowInfoButton(True)
        self._startWorldWidget.selectionChanged.connect(self._startWorldChanged)
        self._startWorldWidget.showHex.connect(self._showOnMap)

        self._randomSeedWidget = _RandomSeedWidget(
            maxDigits=SimulatorWindow._RandomSeedMaxDigits)

        self._startingFundsSpinBox = gui.SpinBoxEx()
        self._startingFundsSpinBox.setRange(0, app.MaxPossibleCredits)
        self._startingFundsSpinBox.setValue(0)
        self._startingFundsSpinBox.setToolTip(
            gui.createStringToolTip('Starting funds available to the Traveller'))

        self._playerBrokerDmSpinBox = gui.SpinBoxEx()
        self._playerBrokerDmSpinBox.setRange(app.MinPossibleDm, app.MaxPossibleDm)
        self._playerBrokerDmSpinBox.setValue(1)
        self._playerBrokerDmSpinBox.setToolTip(gui.PlayerBrokerDmToolTip)

        self._playerStreetwiseDmSpinBox = gui.SpinBoxEx()
        self._playerStreetwiseDmSpinBox.setRange(app.MinPossibleDm, app.MaxPossibleDm)
        self._playerStreetwiseDmSpinBox.setValue(1)
        self._playerStreetwiseDmSpinBox.setToolTip(gui.PlayerStreetWiseDmToolTip)

        self._playerAdminDmSpinBox = gui.SpinBoxEx()
        self._playerAdminDmSpinBox.setRange(app.MinPossibleDm, app.MaxPossibleDm)
        self._playerAdminDmSpinBox.setValue(-3)
        self._playerAdminDmSpinBox.setToolTip(gui.PlayerAdminDmToolTip)

        self._sellerDmRangeWidget = gui.RangeSpinBoxWidget()
        self._sellerDmRangeWidget.setLimits(app.MinPossibleDm, app.MaxPossibleDm)
        self._sellerDmRangeWidget.setValues(1, 4)
        self._sellerDmRangeWidget.setToolTip(
            gui.createStringToolTip('DM bonus range of the sellers the Traveller will encounter in the simulation'))

        self._buyerDmRangeWidget = gui.RangeSpinBoxWidget()
        self._buyerDmRangeWidget.setLimits(app.MinPossibleDm, app.MaxPossibleDm)
        self._buyerDmRangeWidget.setValues(1, 4)
        self._buyerDmRangeWidget.setToolTip(
            gui.createStringToolTip('DM bonus range of the buyers the Traveller will encounter in the simulation'))

        leftLayout = gui.FormLayoutEx()
        leftLayout.setContentsMargins(0, 0, 0, 0)
        leftLayout.addRow('Random Seed:', self._randomSeedWidget)
        leftLayout.addRow('Starting Funds:', self._startingFundsSpinBox)
        leftLayout.addRow('Player\'s Broker DM:', self._playerBrokerDmSpinBox)
        leftLayout.addRow('Player\'s Streetwise DM:', self._playerStreetwiseDmSpinBox)
        leftLayout.addRow('Player\'s Admin DM:', self._playerAdminDmSpinBox)
        leftLayout.addRow('Seller DM Range:', self._sellerDmRangeWidget)
        leftLayout.addRow('Buyer DM Range:', self._buyerDmRangeWidget)

        # Set default ship tonnage, jump rating, cargo and fuel capacities to the values for a standard Scout ship
        self._shipTonnageSpinBox = gui.SpinBoxEx()
        self._shipTonnageSpinBox.setRange(app.MinPossibleShipTonnage, app.MaxPossibleShipTonnage)
        self._shipTonnageSpinBox.setValue(100)
        self._shipTonnageSpinBox.setToolTip(gui.ShipTonnageToolTip)

        self._shipJumpRatingSpinBox = gui.SpinBoxEx()
        self._shipJumpRatingSpinBox.setRange(app.MinPossibleJumpRating, app.MaxPossibleJumpRating)
        self._shipJumpRatingSpinBox.setValue(2)
        self._shipJumpRatingSpinBox.setToolTip(gui.ShipJumpRatingToolTip)

        self._shipCargoCapacitySpinBox = gui.SpinBoxEx()
        self._shipCargoCapacitySpinBox.setRange(1, app.MaxPossibleShipTonnage)
        self._shipCargoCapacitySpinBox.setValue(12)
        self._shipCargoCapacitySpinBox.setToolTip('<p>Cargo capacity available for trade cargo</p>')

        self._shipFuelCapacitySpinBox = gui.SpinBoxEx()
        self._shipFuelCapacitySpinBox.setRange(1, app.MaxPossibleShipTonnage)
        self._shipFuelCapacitySpinBox.setValue(23)
        self._shipFuelCapacitySpinBox.setToolTip(gui.ShipFuelCapacityToolTip)

        self._shipFuelPerParsecSpinBox = gui.TogglableDoubleSpinBox()
        self._shipFuelPerParsecSpinBox.setRange(1.0, app.MaxPossibleShipTonnage)
        self._shipFuelPerParsecSpinBox.setValue(10.0)
        self._shipFuelPerParsecSpinBox.setChecked(False)
        self._shipFuelPerParsecSpinBox.setToolTip(gui.ShipFuelPerParsecToolTip)

        self._refuellingStrategyComboBox = gui.EnumComboBox(
            type=logic.RefuellingStrategy,
            value=logic.RefuellingStrategy.WildernessPreferred)
        self._refuellingStrategyComboBox.setToolTip(gui.RefuellingStrategyToolTip)

        self._useFuelCachesCheckBox = gui.CheckBoxEx()
        self._useFuelCachesCheckBox.setChecked(True)
        self._useFuelCachesCheckBox.setToolTip(gui.UseFuelCachesToolTip)

        self._useAnomalyRefuellingCheckBox = gui.CheckBoxEx()
        self._useAnomalyRefuellingCheckBox.setChecked(True)
        self._useAnomalyRefuellingCheckBox.setToolTip(gui.AnomalyRefuellingToolTip)
        self._useAnomalyRefuellingCheckBox.stateChanged.connect(self._enableDisableControls)

        self._anomalyFuelCostSpinBox = gui.SpinBoxEx()
        self._anomalyFuelCostSpinBox.setRange(0, app.MaxPossibleCredits)
        self._anomalyFuelCostSpinBox.setValue(1000)
        self._anomalyFuelCostSpinBox.setToolTip(gui.AnomalyFuelCostToolTip)
        self._anomalyFuelCostSpinBox.setEnabled(
            self._useAnomalyRefuellingCheckBox.isChecked())

        self._anomalyBerthingCostSpinBox = gui.SpinBoxEx()
        self._anomalyBerthingCostSpinBox.setRange(0, app.MaxPossibleCredits)
        self._anomalyBerthingCostSpinBox.setValue(5000)
        self._anomalyBerthingCostSpinBox.setToolTip(gui.AnomalyBerthingCostToolTip)
        self._anomalyBerthingCostSpinBox.setEnabled(
            self._useAnomalyRefuellingCheckBox.isChecked())

        self._routeOptimisationComboBox = gui.EnumComboBox(
            type=logic.RouteOptimisation,
            value=logic.RouteOptimisation.ShortestDistance)
        self._routeOptimisationComboBox.setToolTip(gui.RouteOptimisationToolTip)

        self._perJumpOverheadsSpinBox = gui.SpinBoxEx()
        self._perJumpOverheadsSpinBox.setRange(0, app.MaxPossibleCredits)
        self._perJumpOverheadsSpinBox.setValue(1000)
        self._perJumpOverheadsSpinBox.setToolTip(gui.PerJumpOverheadsToolTip)

        self._searchRadiusSpinBox = gui.SpinBoxEx()
        self._searchRadiusSpinBox.setRange(app.MinPossibleJumpRating, app.MaxSearchRadius)
        self._searchRadiusSpinBox.setValue(self._shipJumpRatingSpinBox.value())
        self._searchRadiusSpinBox.setToolTip(
            gui.createStringToolTip('Radius in parsecs around their current world that the simulated Traveller will check for sale worlds'))

        rightLayout = gui.FormLayoutEx()
        rightLayout.setContentsMargins(0, 0, 0, 0)
        rightLayout.addRow('Ship Total Tonnage:', self._shipTonnageSpinBox)
        rightLayout.addRow('Ship Jump Rating:', self._shipJumpRatingSpinBox)
        rightLayout.addRow('Ship Cargo Capacity:', self._shipCargoCapacitySpinBox)
        rightLayout.addRow('Ship Fuel Capacity:', self._shipFuelCapacitySpinBox)
        rightLayout.addRow('Ship Fuel Per Parsec:', self._shipFuelPerParsecSpinBox)
        rightLayout.addRow('Route Optimisation:', self._routeOptimisationComboBox)
        rightLayout.addRow('Refuelling Strategy:', self._refuellingStrategyComboBox)
        rightLayout.addRow('Use Fuel Caches:', self._useFuelCachesCheckBox)
        rightLayout.addRow('Use Anomaly Refuelling:', self._useAnomalyRefuellingCheckBox)
        rightLayout.addRow('Anomaly Fuel Cost:', self._anomalyFuelCostSpinBox)
        rightLayout.addRow('Anomaly Berthing Cost:', self._anomalyBerthingCostSpinBox)
        rightLayout.addRow('Per Jump Overheads:', self._perJumpOverheadsSpinBox)
        rightLayout.addRow('Search Radius (Parsecs):', self._searchRadiusSpinBox)

        optionsLayout = QtWidgets.QHBoxLayout()
        optionsLayout.setContentsMargins(0, 0, 0, 0)
        optionsLayout.addLayout(leftLayout)
        optionsLayout.addLayout(rightLayout)
        optionsLayout.addStretch()

        configLayout = QtWidgets.QVBoxLayout()
        configLayout.addWidget(self._startWorldWidget)
        configLayout.addLayout(optionsLayout)

        self._configGroupBox = QtWidgets.QGroupBox('Configuration')
        self._configGroupBox.setLayout(configLayout)

    def _setupSimulationControls(self) -> None:
        self._runSimulationButton = gui.DualTextPushButton(
            primaryText='Run Simulation',
            secondaryText='Cancel')
        self._runSimulationButton.clicked.connect(self._runSimulation)

        self._simulationDayLabel = QtWidgets.QLabel('Day:')
        self._simulationFundsLabel = QtWidgets.QLabel('Funds:')
        self._simulationTravelledLabel = QtWidgets.QLabel('Travelled:')

        labelLayout = QtWidgets.QHBoxLayout()
        labelLayout.setContentsMargins(0, 0, 0, 0)
        labelLayout.addWidget(self._simulationDayLabel)
        labelLayout.addWidget(self._simulationFundsLabel)
        labelLayout.addWidget(self._simulationTravelledLabel)

        milieu = app.Config.instance().value(option=app.ConfigOption.Milieu)
        rules = app.Config.instance().value(option=app.ConfigOption.Rules)
        mapStyle = app.Config.instance().value(option=app.ConfigOption.MapStyle)
        mapOptions = app.Config.instance().value(option=app.ConfigOption.MapOptions)
        mapRendering = app.Config.instance().value(option=app.ConfigOption.MapRendering)
        mapAnimations = app.Config.instance().value(option=app.ConfigOption.MapAnimations)
        worldTagging = app.Config.instance().value(option=app.ConfigOption.WorldTagging)
        taggingColours = app.Config.instance().value(option=app.ConfigOption.TaggingColours)

        self._mapWidget = gui.MapWidgetEx(
            milieu=milieu,
            rules=rules,
            style=mapStyle,
            options=mapOptions,
            rendering=mapRendering,
            animated=mapAnimations,
            worldTagging=worldTagging,
            taggingColours=taggingColours)
        self._mapWidget.mapStyleChanged.connect(self._mapStyleChanged)
        self._mapWidget.mapOptionsChanged.connect(self._mapOptionsChanged)
        self._mapWidget.mapRenderingChanged.connect(self._mapRenderingChanged)
        self._mapWidget.mapAnimationChanged.connect(self._mapAnimationChanged)

        simulationLayout = QtWidgets.QVBoxLayout()
        simulationLayout.addWidget(self._runSimulationButton, 0)
        simulationLayout.addLayout(labelLayout, 0)
        simulationLayout.addWidget(self._mapWidget, 1)

        self._simulationGroupBox = QtWidgets.QGroupBox('Simulation')
        self._simulationGroupBox.setLayout(simulationLayout)

    def _setupMessageControls(self) -> None:
        self._simInfoEditBox = QtWidgets.QPlainTextEdit()
        self._simInfoEditBox.setReadOnly(True)

    def _enableDisableControls(self) -> None:
        if self._simulatorJob:
            self._configGroupBox.setDisabled(True)
            self._simulationGroupBox.setDisabled(False)
        else:
            self._configGroupBox.setDisabled(False)
            self._simulationGroupBox.setDisabled(not self._startWorldWidget.selectedWorld())

        anomalyRefuelling = self._useAnomalyRefuellingCheckBox.isChecked()
        self._anomalyFuelCostSpinBox.setEnabled(anomalyRefuelling)
        self._anomalyBerthingCostSpinBox.setEnabled(anomalyRefuelling)

    def _startWorldChanged(self) -> None:
        startWorld = self._startWorldWidget.selectedWorld()
        if startWorld:
            self._mapWidget.clearHexHighlights()
            self._mapWidget.highlightHex(hex=startWorld.hex())
            self._mapWidget.centerOnHex(hex=startWorld.hex())

        self._enableDisableControls()

    def _appConfigChanged(
            self,
            option: app.ConfigOption,
            oldValue: typing.Any,
            newValue: typing.Any
            ) -> None:
        if option is app.ConfigOption.Milieu:
            self._hexTooltipProvider.setMilieu(milieu=newValue)
            self._startWorldWidget.setMilieu(milieu=newValue)
            self._mapWidget.setMilieu(milieu=newValue)
        elif option is app.ConfigOption.Rules:
            self._hexTooltipProvider.setRules(rules=newValue)
            self._startWorldWidget.setRules(rules=newValue)
            self._mapWidget.setRules(rules=newValue)
        elif option is app.ConfigOption.MapStyle:
            self._hexTooltipProvider.setMapStyle(style=newValue)
            self._startWorldWidget.setMapStyle(style=newValue)
            self._mapWidget.setStyle(style=newValue)
        elif option is app.ConfigOption.MapOptions:
            self._hexTooltipProvider.setMapOptions(options=option)
            self._startWorldWidget.setMapOptions(options=newValue)
            self._mapWidget.setOptions(options=newValue)
        elif option is app.ConfigOption.MapRendering:
            self._startWorldWidget.setMapRendering(rendering=newValue)
            self._mapWidget.setRendering(rendering=newValue)
        elif option is app.ConfigOption.MapAnimations:
            self._startWorldWidget.setMapAnimations(enabled=newValue)
            self._mapWidget.setAnimated(animated=newValue)
        elif option is app.ConfigOption.ShowToolTipImages:
            self._hexTooltipProvider.setShowImages(show=newValue)
        elif option is app.ConfigOption.WorldTagging:
            self._hexTooltipProvider.setWorldTagging(tagging=newValue)
            self._startWorldWidget.setWorldTagging(tagging=newValue)
            self._mapWidget.setWorldTagging(tagging=newValue)
        elif option is app.ConfigOption.TaggingColours:
            self._hexTooltipProvider.setTaggingColours(colours=newValue)
            self._startWorldWidget.setTaggingColours(colours=newValue)
            self._mapWidget.setTaggingColours(colours=newValue)

    def _mapStyleChanged(
            self,
            style: travellermap.Style
            ) -> None:
        app.Config.instance().setValue(
            option=app.ConfigOption.MapStyle,
            value=style)

    def _mapOptionsChanged(
            self,
            options: typing.Iterable[travellermap.Option]
            ) -> None:
        app.Config.instance().setValue(
            option=app.ConfigOption.MapOptions,
            value=options)

    def _mapRenderingChanged(
            self,
            renderingType: app.MapRendering,
            ) -> None:
        app.Config.instance().setValue(
            option=app.ConfigOption.MapRendering,
            value=renderingType)

    def _mapAnimationChanged(
            self,
            animations: bool
            ) -> None:
        app.Config.instance().setValue(
            option=app.ConfigOption.MapAnimations,
            value=animations)

    def _runSimulation(self) -> None:
        if self._simulatorJob:
            # A trade option job is already running so cancel it
            self._stopSimulator()
            return

        startWorld = self._startWorldWidget.selectedWorld()
        if not startWorld:
            gui.MessageBoxEx.information(
                parent=self,
                text='Select a starting location')
            return

        if self._startingFundsSpinBox.value() <= 0:
            gui.MessageBoxEx.information(
                parent=self,
                text='You\'re not going to get far without any starting funds')
            return

        if self._shipFuelCapacitySpinBox.value() > self._shipTonnageSpinBox.value():
            gui.MessageBoxEx.information(
                parent=self,
                text='Ship\'s fuel capacity can\'t be larger than its total tonnage')
            return
        if self._shipCargoCapacitySpinBox.value() > self._shipTonnageSpinBox.value():
            gui.MessageBoxEx.information(
                parent=self,
                text='Ship\'s cargo capacity can\'t be larger than its total tonnage')
            return
        if (self._shipFuelCapacitySpinBox.value() + self._shipCargoCapacitySpinBox.value()) > \
                self._shipTonnageSpinBox.value():
            gui.MessageBoxEx.information(
                parent=self,
                text='Ship\'s combined fuel and cargo capacities can\'t be larger than its total tonnage')
            return

        milieu = app.Config.instance().value(option=app.ConfigOption.Milieu)
        rules = app.Config.instance().value(option=app.ConfigOption.Rules)
        useAnomalyRefuelling = self._useAnomalyRefuellingCheckBox.isChecked()
        pitCostCalculator = logic.PitStopCostCalculator(
            refuellingStrategy=self._refuellingStrategyComboBox.currentEnum(),
            useFuelCaches=self._useFuelCachesCheckBox.isChecked(),
            anomalyFuelCost=self._anomalyFuelCostSpinBox.value() if useAnomalyRefuelling else None,
            anomalyBerthingCost=self._anomalyBerthingCostSpinBox.value() if useAnomalyRefuelling else None,
            rules=rules)
        if startWorld and not pitCostCalculator.refuellingType(world=startWorld):
            gui.MessageBoxEx.information(
                parent=self,
                text='The start world must allow the selected refuelling strategy')
            return

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
                shipCurrentFuel=0, # Simulator doesn't support starting fuel
                shipFuelPerParsec=self._shipFuelPerParsecSpinBox.value(),
                shipJumpRating=self._shipJumpRatingSpinBox.value(),
                pitCostCalculator=pitCostCalculator,
                perJumpOverheads=self._perJumpOverheadsSpinBox.value())
        else:
            assert(False) # I've missed an enum

        self._currentHex = None
        self._parsecsTravelled = 0
        self._simInfoEditBox.clear()

        self._simulationDayLabel.setText('Day:')
        self._simulationFundsLabel.setText('Funds:')
        self._simulationTravelledLabel.setText('Travelled:')

        try:
            self._simulatorJob = jobs.SimulatorJob(
                parent=self,
                rules=rules,
                milieu=milieu,
                startHex=startWorld.hex(),
                startingFunds=self._startingFundsSpinBox.value(),
                shipTonnage=self._shipTonnageSpinBox.value(),
                shipJumpRating=self._shipJumpRatingSpinBox.value(),
                shipCargoCapacity=self._shipCargoCapacitySpinBox.value(),
                shipFuelCapacity=self._shipFuelCapacitySpinBox.value(),
                shipFuelPerParsec=self._shipFuelPerParsecSpinBox.value(),
                perJumpOverheads=self._perJumpOverheadsSpinBox.value(),
                jumpCostCalculator=jumpCostCalculator,
                pitCostCalculator=pitCostCalculator,
                deadSpaceRouting=False,
                searchRadius=self._searchRadiusSpinBox.value(),
                playerBrokerDm=self._playerBrokerDmSpinBox.value(),
                playerStreetwiseDm=self._playerStreetwiseDmSpinBox.value(),
                playerAdminDm=self._playerAdminDmSpinBox.value(),
                minSellerDm=self._sellerDmRangeWidget.lowerValue(),
                maxSellerDm=self._sellerDmRangeWidget.upperValue(),
                minBuyerDm=self._buyerDmRangeWidget.lowerValue(),
                maxBuyerDm=self._buyerDmRangeWidget.upperValue(),
                randomSeed=self._randomSeedWidget.number(),
                simulationLength=None,
                eventCallback=self._simulatorJobEvent,
                finishedCallback=self._simulatorJobFinished)
        except Exception as ex:
            message = 'Failed to create simulator job'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

        self._runSimulationButton.showSecondaryText()
        self._enableDisableControls()

        # Start job after a delay to give the ui time to update
        QtCore.QTimer.singleShot(200, self._simulatorJobStart)

    def _simulatorJobStart(self) -> None:
        if not self._simulatorJob:
            return

        try:
            self._simulatorJob.start()
        except Exception as ex:
            self._simulatorJob = None
            self._runSimulationButton.showPrimaryText()
            self._enableDisableControls()

            message = 'Failed to start simulator job'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)

    def _simulatorJobEvent(self, event: logic.Simulator.Event) -> None:
        day = int(math.floor(event.timestamp() / 24))
        self._simulationDayLabel.setText(f'Day: {common.formatNumber(day)}')

        if event.type() == logic.Simulator.Event.Type.FundsUpdate:
            # Data is the current funds (as an int)
            availableFunds: int = event.data()
            self._simulationFundsLabel.setText(f'Funds: Cr{common.formatNumber(availableFunds)}')
            self._simInfoEditBox.appendPlainText(f'Day {common.formatNumber(day)}: Available funds = Cr{common.formatNumber(availableFunds)}')
        elif event.type() == logic.Simulator.Event.Type.HexUpdate:
            # Data is the new world object
            currentHex: travellermap.HexPosition = event.data()
            if currentHex and self._currentHex != currentHex:
                if self._currentHex:
                    self._parsecsTravelled += self._currentHex.parsecsTo(currentHex)
                    self._simulationTravelledLabel.setText(f'Travelled: {common.formatNumber(self._parsecsTravelled)} parsecs')
                self._currentHex = currentHex

            if self._currentHex:
                self._mapWidget.clearHexHighlights()
                self._mapWidget.highlightHex(hex=self._currentHex)
                self._mapWidget.centerOnHex(
                    hex=self._currentHex,
                    linearScale=None) # Keep current scale
                self._mapWidget.setInfoHex(hex=self._currentHex)
        elif event.type() == logic.Simulator.Event.Type.InfoMessage:
            # Data is a string containing the message
            self._simInfoEditBox.appendPlainText(f'Day {common.formatNumber(day)}: {event.data()}')

    def _simulatorJobFinished(self, result: typing.Union[str, Exception]) -> None:
        if isinstance(result, Exception):
            message = 'Simulation exception'
            logging.error(message, exc_info=result)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=result)
        elif self._simulatorJob and self._simulatorJob.isCancelled():
            pass

        self._simulatorJob = None
        self._runSimulationButton.showPrimaryText()
        self._enableDisableControls()

    def _stopSimulator(self) -> None:
        if self._simulatorJob:
            self._simulatorJob.cancel()
            self._simulatorJob = None
        self._runSimulationButton.showPrimaryText()

    def _showOnMap(
            self,
            hex: travellermap.HexPosition
            ) -> None:
        try:
            self._mapWidget.centerOnHex(hex=hex)
        except Exception as ex:
            message = 'Failed to show location on map'
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
            noShowAgainId='SimulatorWelcome')
        message.exec()
