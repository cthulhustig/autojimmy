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
    universe, following the Mongoose 2e rules to buy and sell goods. It was initially created
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

        self._currentWorld = None
        self._parsecsTravelled = 0
        self._jumpRoute = []
        self._simulatorJob = None

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

        self._topBottomSplitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        self._topBottomSplitter.addWidget(self._leftRightSplitter)
        self._topBottomSplitter.addWidget(self._simInfoEditBox)

        windowLayout = QtWidgets.QVBoxLayout()
        windowLayout.addWidget(self._topBottomSplitter)

        self.setLayout(windowLayout)

    def firstShowEvent(self, e: QtGui.QShowEvent) -> None:
        QtCore.QTimer.singleShot(0, self._showWelcomeMessage)
        super().firstShowEvent(e)

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
        self._startWorldWidget = gui.WorldSelectWidget(
            labelText='Start',
            noSelectionText='Select a starting world to continue')
        self._startWorldWidget.selectionChanged.connect(self._startWorldChanged)

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

        self._anomalyFuelCostSpinBox = gui.TogglableSpinBox()
        self._anomalyFuelCostSpinBox.setRange(0, app.MaxPossibleCredits)
        self._anomalyFuelCostSpinBox.setChecked(False)
        self._anomalyFuelCostSpinBox.setValue(1000)
        self._anomalyFuelCostSpinBox.setToolTip(gui.AnomalyRefuellingToolTip)

        self._anomalyBerthingCostSpinBox = gui.TogglableSpinBox()
        self._anomalyBerthingCostSpinBox.setRange(0, app.MaxPossibleCredits)
        self._anomalyBerthingCostSpinBox.setChecked(False)
        self._anomalyBerthingCostSpinBox.setValue(5000)
        self._anomalyBerthingCostSpinBox.setToolTip(gui.AnomalyBerthingToolTip)

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
        self._runSimulationButton = QtWidgets.QPushButton('Run Simulation')
        self._runSimulationButton.clicked.connect(self._runSimulation)

        self._simulationDayLabel = QtWidgets.QLabel('Day:')
        self._simulationFundsLabel = QtWidgets.QLabel('Funds:')
        self._simulationTravelledLabel = QtWidgets.QLabel('Travelled:')

        labelLayout = QtWidgets.QHBoxLayout()
        labelLayout.setContentsMargins(0, 0, 0, 0)
        labelLayout.addWidget(self._simulationDayLabel)
        labelLayout.addWidget(self._simulationFundsLabel)
        labelLayout.addWidget(self._simulationTravelledLabel)

        self._mapWidget = gui.TravellerMapWidget()

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
            self._simulationGroupBox.setDisabled(not self._startWorldWidget.hasSelection())

    def _startWorldChanged(self) -> None:
        world = self._startWorldWidget.world()
        if world:
            self._mapWidget.centerOnWorld(
                world=world,
                clearOverlays=True,
                highlightWorld=True)

        self._enableDisableControls()

    def _runSimulation(self) -> None:
        if self._simulatorJob:
            # A trade option job is already running so cancel it
            self._simulatorJob.cancel()
            return

        if not self._startWorldWidget.hasSelection():
            gui.MessageBoxEx.information(
                parent=self,
                text='Select a start world')
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

        pitCostCalculator = logic.PitStopCostCalculator(
            refuellingStrategy=self._refuellingStrategyComboBox.currentEnum(),
            useFuelCaches=self._useFuelCachesCheckBox.isChecked(),
            anomalyFuelCost=self._anomalyFuelCostSpinBox.value(),
            anomalyBerthingCost=self._anomalyBerthingCostSpinBox.value(),
            rules=app.Config.instance().rules())
        if not pitCostCalculator.refuellingType(
                world=self._startWorldWidget.world()):
            gui.MessageBoxEx.information(
                parent=self,
                text='The start world must allow the selected refuelling strategy')
            return

        routeOptimisation = self._routeOptimisationComboBox.currentEnum()
        if routeOptimisation == logic.RouteOptimisation.ShortestDistance:
            jumpCostCalculator = logic.ShortestDistanceCostCalculator()
        elif routeOptimisation == logic.RouteOptimisation.ShortestTime:
            jumpCostCalculator = logic.ShortestTimeCostCalculator()
        elif routeOptimisation == logic.RouteOptimisation.LowestCost:
            jumpCostCalculator = logic.CheapestRouteCostCalculator(
                shipTonnage=self._shipTonnageSpinBox.value(),
                shipFuelCapacity=self._shipFuelCapacitySpinBox.value(),
                shipCurrentFuel=0, # Simulator doesn't support starting fuel
                shipFuelPerParsec=self._shipFuelPerParsecSpinBox.value(),
                pitCostCalculator=pitCostCalculator,
                perJumpOverheads=self._perJumpOverheadsSpinBox.value())
        else:
            assert(False) # I've missed an enum

        self._currentWorld = None
        self._parsecsTravelled = 0
        self._jumpRoute.clear()
        self._simInfoEditBox.clear()

        self._simulationDayLabel.setText('Day:')
        self._simulationFundsLabel.setText('Funds:')
        self._simulationTravelledLabel.setText('Travelled:')

        try:
            self._simulatorJob = jobs.SimulatorJob(
                parent=self,
                rules=app.Config.instance().rules(),
                startingWorld=self._startWorldWidget.world(),
                startingFunds=self._startingFundsSpinBox.value(),
                shipTonnage=self._shipTonnageSpinBox.value(),
                shipJumpRating=self._shipJumpRatingSpinBox.value(),
                shipCargoCapacity=self._shipCargoCapacitySpinBox.value(),
                shipFuelCapacity=self._shipFuelCapacitySpinBox.value(),
                shipFuelPerParsec=self._shipFuelPerParsecSpinBox.value(),
                perJumpOverheads=self._perJumpOverheadsSpinBox.value(),
                jumpCostCalculator=jumpCostCalculator,
                pitCostCalculator=pitCostCalculator,
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
                eventCallback=self._simulationEvent,
                finishedCallback=self._simulationFinished)
        except Exception as ex:
            message = 'Failed to start simulator job'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

        self._runSimulationButton.setText('Cancel')
        self._enableDisableControls()

    def _simulationEvent(self, event: logic.Simulator.Event) -> None:
        day = int(math.floor(event.timestamp() / 24))
        self._simulationDayLabel.setText(f'Day: {common.formatNumber(day)}')

        if event.type() == logic.Simulator.Event.Type.FundsUpdate:
            # Data is the current funds (as an int)
            availableFunds: int = event.data()
            self._simulationFundsLabel.setText(f'Funds: Cr{common.formatNumber(availableFunds)}')
            self._simInfoEditBox.appendPlainText(f'Day {common.formatNumber(day)}: Available funds = Cr{common.formatNumber(availableFunds)}')
        elif event.type() == logic.Simulator.Event.Type.WorldUpdate:
            # Data is the new world object
            world: traveller.World = event.data()
            if self._currentWorld and self._currentWorld != world:
                self._parsecsTravelled += travellermap.hexDistance(
                    self._currentWorld.absoluteX(),
                    self._currentWorld.absoluteY(),
                    world.absoluteX(),
                    world.absoluteY())
            self._currentWorld = world
            self._jumpRoute.append(world)
            self._simulationTravelledLabel.setText(f'Travelled: {common.formatNumber(self._parsecsTravelled)} parsecs')
            self._mapWidget.centerOnWorld(
                world=world,
                clearOverlays=True,
                highlightWorld=True,
                linearScale=None) # Keep current scale
            self._mapWidget.setInfoWorld(world=world)
        elif event.type() == logic.Simulator.Event.Type.InfoMessage:
            # Data is a string containing the message
            self._simInfoEditBox.appendPlainText(f'Day {common.formatNumber(day)}: {event.data()}')

    def _simulationFinished(self, result: typing.Union[str, Exception]) -> None:
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
        self._runSimulationButton.setText('Run simulation')
        self._enableDisableControls()

    def _showWelcomeMessage(self) -> None:
        message = gui.InfoDialog(
            parent=self,
            title=self.windowTitle(),
            html=_WelcomeMessage,
            noShowAgainId='SimulatorWelcome')
        message.exec()
