import app
import common
import enum
import gui
import jobs
import logging
import logic
import traveller
import travellermap
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

_WelcomeMessage = """
    <html>
    <p>The Jump Route Planner allows you to create complex jump routes between worlds. It also has
    experimental features to generate refuelling plans for the route and estimate the logistics
    costs based on average, worst and best case dice rolls.</p>
    <p>The jump route generation is based on the logic used by Traveller Map, so should be compatible
    with most Traveller rule systems. The logistics cost calculations use Mongoose Traveller rules,
    so compatibility with other rule systems will vary. If you're not using Mongoose Traveller
    rules, cost values can simply be ignored as they don't affect the generated route (unless lowest
    cost route optimisation is used).</p>
    <p>Waypoint worlds can be added to create a multipoint route. This includes the creation of
    circular routes.<p>
    <p>Avoid worlds can be added to, as the name suggests, avoid specific world. This can either
    be done by specifying specific worlds or by adding filters which allow worlds to be avoided
    based on their attributes (e.g. avoid worlds that have specific allegiances if you've made some
    enemies or worlds with an imperial bases or a law level over 5 if you're trying to lie low).</p>
    <p>{name} can integrate with Traveller Map in order to display calculated jump routes. This
    feature requires an internet connection.</p>
    </html>
""".format(name=app.AppName)

def _formatRefuellingTypeString(
        pitStop: logic.PitStop
        ) -> str:
    refuellingType = pitStop.refuellingType()
    world = pitStop.world()

    if refuellingType == logic.RefuellingType.Refined:
        text = 'Star Port (Refined)'
    elif refuellingType == logic.RefuellingType.Unrefined:
        text = 'Star Port (Unrefined)'
    elif refuellingType == logic.RefuellingType.Wilderness:
        text = 'Wilderness'
        if world.hasGasGiantRefuelling() and world.hasWaterRefuelling():
            pass # Just leave it as wilderness refuelling
        elif world.hasGasGiantRefuelling():
            text += ' (Gas Giant Only)'
        elif world.hasWaterRefuelling():
            text += ' (Water Only)'
        else:
            text += ' (Unknown)'
    elif refuellingType == logic.RefuellingType.FuelCache:
        text = 'Fuel Cache'
    elif refuellingType == logic.RefuellingType.Anomaly:
        text = 'Anomaly'
    else:
        text = 'No Refuelling'

    return text

def _formatBerthingTypeString(
        pitStop: logic.PitStop
        ) -> str:
    if not pitStop.hasBerthing():
        return 'No Berthing'

    world = pitStop.world()

    if world.hasStarPort():
        starPortCode = world.uwp().code(traveller.UWP.Element.StarPort)
        return f'Class {starPortCode} Star Port'
    elif world.isFuelCache():
        return 'Fuel Cache'
    elif world.isAnomaly():
        return 'Anomaly'

    return 'No Star Port'

# TODO: This will need updated to allow avoiding dead space sectors
class _HexFilter(logic.HexFilterInterface):
    def __init__(
            self,
            avoidWorlds: typing.List[traveller.World],
            avoidFilters: typing.List[traveller.World],
            avoidFilterLogic: logic.FilterLogic
            ) -> None:
        if avoidWorlds:
            # Copy avoid worlds into a set for quick lookup
            self._avoidWorlds = set()
            for world in avoidWorlds:
                self._avoidWorlds.add(world)
        else:
            self._avoidWorlds = None

        if avoidFilters:
            self._avoidFilter = logic.WorldSearch()
            self._avoidFilter.setLogic(filterLogic=avoidFilterLogic)
            self._avoidFilter.setFilters(filters=avoidFilters)
        else:
            self._avoidFilter = None

    # IMPORTANT: This will be called from the route planner job thread
    def match(
            self,
            hex: travellermap.HexPosition,
            world: typing.Optional[traveller.World]
            ) -> bool:
        # TODO: This will need updated for avoiding dead space hexes
        if not world:
            # No world so nothing to filter
            return True

        if self._avoidWorlds and world in self._avoidWorlds:
            # Filter out worlds on the avoid list
            return False

        if self._avoidFilter and self._avoidFilter.checkWorld(world=world):
            # Filter out worlds that MATCH the avoid filter
            return False

        return True

class _RefuellingPlanTableColumnType(enum.Enum):
    RefuellingType = 'Refuelling Type'
    FuelTons = 'Fuel Amount\n(Tons)'
    FuelCost = 'Fuel Cost\n(Cr)'
    BerthingType = 'Berthing Type'
    AverageCaseBerthingCost = 'Avg Berthing Cost\n(Cr)'
    WorstCaseBerthingCost = 'Worst Berthing Cost\n(Cr)'
    BestCaseBerthingCost = 'Best Berthing Cost\n(Cr)'

class _RefuellingPlanTable(gui.WorldTable):
    AllColumns = [
        gui.WorldTable.ColumnType.World,
        gui.WorldTable.ColumnType.Sector,
        _RefuellingPlanTableColumnType.RefuellingType,
        _RefuellingPlanTableColumnType.FuelTons,
        _RefuellingPlanTableColumnType.FuelCost,
        _RefuellingPlanTableColumnType.BerthingType,
        _RefuellingPlanTableColumnType.AverageCaseBerthingCost,
        _RefuellingPlanTableColumnType.WorstCaseBerthingCost,
        _RefuellingPlanTableColumnType.BestCaseBerthingCost,
        gui.WorldTable.ColumnType.StarPort,
        gui.WorldTable.ColumnType.GasGiantCount,
        gui.WorldTable.ColumnType.Hydrographics
    ]

    def __init__(
            self,
            columns: typing.Iterable[typing.Union[_RefuellingPlanTableColumnType, gui.WorldTable.ColumnType]] = AllColumns
            ) -> None:
        super().__init__(columns=columns)
        self.setSortingEnabled(False)
        self._pitStops: typing.List[logic.PitStop] = []

    def setPitStops(
            self,
            pitStops: typing.Optional[typing.Iterable[logic.PitStop]]
            ) -> None:
        self.removeAllRows()
        if pitStops:
            self._pitStops = list(pitStops)
        else:
            self._pitStops.clear()

        for pitStop in self._pitStops:
            self.addWorld(world=pitStop.world())

    def pitStopAt(self, position: QtCore.QPoint) -> typing.Optional[logic.PitStop]:
        item = self.itemAt(position)
        if not item:
            return None
        if item.row() < 0 or item.row() >= len(self._pitStops):
            return None
        return self._pitStops[item.row()]

    def _fillRow(
            self,
            row: int,
            world: traveller.World
            ) -> int:
        # Disable sorting while updating a row. We don't want any sorting to occur
        # until all columns have been updated
        sortingEnabled = self.isSortingEnabled()
        self.setSortingEnabled(False)

        try:
            super()._fillRow(row, world)

            pitStop = self._pitStops[row]
            for column in range(self.columnCount()):
                columnType = self.columnHeader(column)

                tableItem = None
                if columnType == _RefuellingPlanTableColumnType.RefuellingType:
                    tableItem = QtWidgets.QTableWidgetItem(
                        _formatRefuellingTypeString(pitStop) if pitStop and pitStop.hasRefuelling() else '')
                elif columnType == _RefuellingPlanTableColumnType.FuelTons:
                    tableItem = gui.FormattedNumberTableWidgetItem(pitStop.tonsOfFuel() if pitStop else None)
                elif columnType == _RefuellingPlanTableColumnType.FuelCost:
                    tableItem = gui.FormattedNumberTableWidgetItem(pitStop.fuelCost() if pitStop else None)
                elif columnType == _RefuellingPlanTableColumnType.BerthingType:
                    tableItem = QtWidgets.QTableWidgetItem(
                        _formatBerthingTypeString(pitStop) if pitStop and pitStop.hasBerthing() else '')
                elif columnType == _RefuellingPlanTableColumnType.AverageCaseBerthingCost:
                    tableItem = gui.FormattedNumberTableWidgetItem(pitStop.berthingCost().averageCaseValue() if pitStop and pitStop.berthingCost() else None)
                    tableItem.setBackground(QtGui.QColor(app.Config.instance().averageCaseColour()))
                elif columnType == _RefuellingPlanTableColumnType.WorstCaseBerthingCost:
                    tableItem = gui.FormattedNumberTableWidgetItem(pitStop.berthingCost().worstCaseValue() if pitStop and pitStop.berthingCost() else None)
                    tableItem.setBackground(QtGui.QColor(app.Config.instance().worstCaseColour()))
                elif columnType == _RefuellingPlanTableColumnType.BestCaseBerthingCost:
                    tableItem = gui.FormattedNumberTableWidgetItem(pitStop.berthingCost().bestCaseValue() if pitStop and pitStop.berthingCost() else None)
                    tableItem.setBackground(QtGui.QColor(app.Config.instance().bestCaseColour()))

                if tableItem:
                    self.setItem(row, column, tableItem)
                    tableItem.setData(QtCore.Qt.ItemDataRole.UserRole, world)

            # Take note of the sort column item so we can determine which row index after the table
            # has been sorted
            sortItem = self.item(row, self.horizontalHeader().sortIndicatorSection())
        finally:
            self.setSortingEnabled(sortingEnabled)

        # If we don't have a sort item we assume a derived class has overridden _fillRow to add custom
        # columns and the table is currently sorted by one of those columns. In this the expectation is
        # the derived class will be handling working out the post sort row index.
        return sortItem.row() if sortItem else row

class _StartFinishWorldsSelectWidget(QtWidgets.QWidget):
    selectionChanged = QtCore.pyqtSignal()
    showWorldRequested = QtCore.pyqtSignal(traveller.World)

    _StateVersion = '_StartFinishWorldsSelectWidget_v1'

    def __init__(self):
        super().__init__()

        self._startWorldWidget = gui.WorldSelectWidget(text=None)
        self._startWorldWidget.enableShowWorldButton(True)
        self._startWorldWidget.enableShowInfoButton(True)
        self._startWorldWidget.selectionChanged.connect(self.selectionChanged.emit)
        self._startWorldWidget.showWorld.connect(self._showStartWorldClicked)

        self._finishWorldWidget = gui.WorldSelectWidget(text=None)
        self._finishWorldWidget.enableShowWorldButton(True)
        self._finishWorldWidget.enableShowInfoButton(True)
        self._finishWorldWidget.selectionChanged.connect(self.selectionChanged.emit)
        self._finishWorldWidget.showWorld.connect(self._showFinishWorldClicked)

        widgetLayout = gui.FormLayoutEx()
        widgetLayout.setContentsMargins(0, 0, 0, 0)
        widgetLayout.addRow('Start World:', self._startWorldWidget)
        widgetLayout.addRow('Finish World:', self._finishWorldWidget)

        self.setLayout(widgetLayout)

    def startWorld(self) -> typing.Optional[traveller.World]:
        return self._startWorldWidget.world()

    def finishWorld(self) -> typing.Optional[traveller.World]:
        return self._finishWorldWidget.world()

    def worlds(self) -> typing.Tuple[typing.Optional[traveller.World], typing.Optional[traveller.World]]:
        return (self.startWorld(), self.finishWorld())

    def setStartWorld(self, world: typing.Optional[traveller.World]):
        self._startWorldWidget.setWorld(world)

    def setFinishWorld(self, world: typing.Optional[traveller.World]):
        self._finishWorldWidget.setWorld(world)

    def setStartFinishWorlds(
            self,
            startWorld: typing.Optional[traveller.World],
            finishWorld: typing.Optional[traveller.World]
            ) -> None:
        updated = False

        # Block signals so we can manually generate a single selection changed event. There is not
        # noting of the current signal blocked state as nothing else should be modifying it
        self._startWorldWidget.blockSignals(True)
        self._finishWorldWidget.blockSignals(True)
        try:
            if startWorld != self._startWorldWidget.world():
                self._startWorldWidget.setWorld(startWorld)
                updated = True

            if finishWorld != self._finishWorldWidget.world():
                self._finishWorldWidget.setWorld(finishWorld)
                updated = True
        finally:
            self._startWorldWidget.blockSignals(False)
            self._finishWorldWidget.blockSignals(False)

        if updated:
            self.selectionChanged.emit()

    def hasStartWorldSelection(self) -> bool:
        return self._startWorldWidget.hasSelection()

    def hasFinishWorldSelected(self) -> bool:
        return self._finishWorldWidget.hasSelection()

    def hasStartFinishWorldsSelection(self) -> bool:
        return self.hasStartWorldSelection() and self.hasFinishWorldSelected()

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(_StartFinishWorldsSelectWidget._StateVersion)

        childState = self._startWorldWidget.saveState()
        stream.writeUInt32(childState.count() if childState else 0)
        if childState:
            stream.writeRawData(childState.data())

        childState = self._finishWorldWidget.saveState()
        stream.writeUInt32(childState.count() if childState else 0)
        if childState:
            stream.writeRawData(childState.data())

        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != _StartFinishWorldsSelectWidget._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore _StartFinishWorldsSelectWidget state (Incorrect version)')
            return False

        count = stream.readUInt32()
        if count > 0:
            childState = QtCore.QByteArray(stream.readRawData(count))
            if not self._startWorldWidget.restoreState(childState):
                return False

        count = stream.readUInt32()
        if count > 0:
            childState = QtCore.QByteArray(stream.readRawData(count))
            if not self._finishWorldWidget.restoreState(childState):
                return False

        return True

    def _handleShowWorld(self, world: traveller.World) -> None:
        if world:
            self.showWorldRequested.emit(world)

    def _showStartWorldClicked(self) -> None:
        self._handleShowWorld(
            world=self._startWorldWidget.world())

    def _showFinishWorldClicked(self) -> None:
        self._handleShowWorld(
            world=self._finishWorldWidget.world())

class JumpRouteWindow(gui.WindowWidget):
    _JumpRatingOverlayDarkStyleColour = '#9D03FC'
    _JumpRatingOverlayLightStyleColour = '#4A03FC'
    _JumpRatingOverlayLineWidth = 6

    def __init__(self) -> None:
        super().__init__(
            title='Jump Route Planner',
            configSection='JumpRouteWindow')

        self._jumpRouteJob = None
        self._jumpRoute = None
        self._routeLogistics = None
        self._zoomToJumpRoute = False
        self._jumpOverlayHandles = set()

        self._setupJumpWorldsControls()
        self._setupConfigurationControls()
        self._setupWaypointWorldsControls()
        self._setupAvoidWorldsControls()
        self._setupJumpRouteControls()

        self._tableSplitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        self._tableSplitter.addWidget(self._waypointWorldsGroupBox)
        self._tableSplitter.addWidget(self._avoidWorldsGroupBox)

        configurationLayout = QtWidgets.QVBoxLayout()
        configurationLayout.setContentsMargins(0, 0, 0, 0)
        configurationLayout.addWidget(self._jumpWorldsGroupBox, 0)
        configurationLayout.addWidget(self._configurationGroupBox, 0)
        configurationLayout.addWidget(self._tableSplitter, 1)
        configurationWidget = QtWidgets.QWidget()
        configurationWidget.setLayout(configurationLayout)

        self._mainSplitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self._mainSplitter.addWidget(configurationWidget)
        self._mainSplitter.addWidget(self._plannedRouteGroupBox)
        self._mainSplitter.setStretchFactor(0, 1)
        self._mainSplitter.setStretchFactor(1, 100)

        windowLayout = QtWidgets.QVBoxLayout()
        windowLayout.addWidget(self._mainSplitter)

        self.setLayout(windowLayout)

    def loadSettings(self) -> None:
        super().loadSettings()

        self._settings.beginGroup(self._configSection)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='StartFinishWorldsState',
            type=QtCore.QByteArray)
        if storedValue:
            self._startFinishWorldsWidget.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='ConfigurationTabBarState',
            type=QtCore.QByteArray)
        if storedValue:
            self._configurationStack.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='WaypointWorldTableState',
            type=QtCore.QByteArray)
        if storedValue:
            self._waypointWorldsWidget.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='WaypointWorldTableContent',
            type=QtCore.QByteArray)
        if storedValue:
            self._waypointWorldsWidget.restoreContent(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='AvoidWorldTableState',
            type=QtCore.QByteArray)
        if storedValue:
            self._avoidWorldsWidget.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='AvoidWorldTableContent',
            type=QtCore.QByteArray)
        if storedValue:
            self._avoidWorldsWidget.restoreContent(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='AvoidFilterTableState',
            type=QtCore.QByteArray)
        if storedValue:
            self._avoidWorldsFilterWidget.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='AvoidFilterTableContent',
            type=QtCore.QByteArray)
        if storedValue:
            self._avoidWorldsFilterWidget.restoreContent(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='AvoidTabBarState',
            type=QtCore.QByteArray)
        if storedValue:
            self._avoidWorldsTabWidget.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='MapWidgetState',
            type=QtCore.QByteArray)
        if storedValue:
            self._travellerMapWidget.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='ResultsDisplayModeState',
            type=QtCore.QByteArray)
        if storedValue:
            self._resultsDisplayModeTabView.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='JumpRouteDisplayModeState',
            type=QtCore.QByteArray)
        if storedValue:
            self._jumpRouteDisplayModeTabBar.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='JumpRouteTableState',
            type=QtCore.QByteArray)
        if storedValue:
            self._jumpRouteTable.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='RefuellingPlanTableState',
            type=QtCore.QByteArray)
        if storedValue:
            self._refuellingPlanTable.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='TableSplitterState',
            type=QtCore.QByteArray)
        if storedValue:
            self._tableSplitter.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='MainSplitterState',
            type=QtCore.QByteArray)
        if storedValue:
            self._mainSplitter.restoreState(storedValue)

        self._jumpRatingOverlayAction.setChecked(
            gui.safeLoadSetting(
                settings=self._settings,
                key='ShowJumpRatingOverlay',
                type=bool,
                default=False))

        self._worldTaggingOverlayAction.setChecked(
            gui.safeLoadSetting(
                settings=self._settings,
                key='ShowWorldTaggingOverlay',
                type=bool,
                default=False))

        self._settings.endGroup()

        self._updateTravellerMapOverlays()

    def saveSettings(self) -> None:
        self._settings.beginGroup(self._configSection)

        self._settings.setValue('StartFinishWorldsState', self._startFinishWorldsWidget.saveState())
        self._settings.setValue('ConfigurationTabBarState', self._configurationStack.saveState())
        self._settings.setValue('WaypointWorldTableState', self._waypointWorldsWidget.saveState())
        self._settings.setValue('WaypointWorldTableContent', self._waypointWorldsWidget.saveContent())
        self._settings.setValue('AvoidWorldTableState', self._avoidWorldsWidget.saveState())
        self._settings.setValue('AvoidWorldTableContent', self._avoidWorldsWidget.saveContent())
        self._settings.setValue('AvoidFilterTableState', self._avoidWorldsFilterWidget.saveState())
        self._settings.setValue('AvoidFilterTableContent', self._avoidWorldsFilterWidget.saveContent())
        self._settings.setValue('AvoidTabBarState', self._avoidWorldsTabWidget.saveState())
        self._settings.setValue('MapWidgetState', self._travellerMapWidget.saveState())
        self._settings.setValue('ResultsDisplayModeState', self._resultsDisplayModeTabView.saveState())
        self._settings.setValue('JumpRouteTableState', self._jumpRouteTable.saveState())
        self._settings.setValue('JumpRouteDisplayModeState', self._jumpRouteDisplayModeTabBar.saveState())
        self._settings.setValue('RefuellingPlanTableState', self._refuellingPlanTable.saveState())
        self._settings.setValue('TableSplitterState', self._tableSplitter.saveState())
        self._settings.setValue('MainSplitterState', self._mainSplitter.saveState())
        self._settings.setValue('ShowJumpRatingOverlay', self._jumpRatingOverlayAction.isChecked())
        self._settings.setValue('ShowWorldTaggingOverlay', self._worldTaggingOverlayAction.isChecked())

        self._settings.endGroup()

        super().saveSettings()

    def configureControls(
            self,
            startWorld: typing.Optional[traveller.World] = None,
            finishWorld: typing.Optional[traveller.World] = None,
            shipTonnage: typing.Optional[int] = None,
            shipJumpRating: typing.Optional[int] = None,
            shipFuelCapacity: typing.Optional[int] = None,
            shipCurrentFuel: typing.Optional[float] = None,
            routeOptimisation: typing.Optional[logic.RouteOptimisation] = None,
            perJumpOverheads: typing.Optional[int] = None,
            refuellingStrategy: typing.Optional[logic.RefuellingStrategy] = None,
            includeStartWorldBerthingCosts: typing.Optional[bool] = None,
            includeFinishWorldBerthingCosts: typing.Optional[bool] = None,
            ) -> None:
        if self._jumpRouteJob:
            raise RuntimeError('Unable to setup jump route window while a jump route job is in progress')

        if (startWorld != None) and (finishWorld != None):
            # Set the start and finish worlds at the same time. If either of them
            # is None then the current world will be kept. This is done so that the
            # user doesn't get prompted twice about clearing the waypoint and avoid
            # worlds if both the start and finish worlds have changed
            self._startFinishWorldsWidget.setStartFinishWorlds(
                startWorld=startWorld,
                finishWorld=finishWorld)
        elif startWorld != None:
            self._startFinishWorldsWidget.setStartWorld(world=startWorld)
        elif finishWorld != None:
            self._startFinishWorldsWidget.setFinishWorld(world=finishWorld)

        if shipTonnage != None:
            self._shipTonnageSpinBox.setValue(int(shipTonnage))
        if shipJumpRating != None:
            self._shipJumpRatingSpinBox.setValue(int(shipJumpRating))
        if shipFuelCapacity != None:
            self._shipFuelCapacitySpinBox.setValue(int(shipFuelCapacity))
        if shipCurrentFuel != None:
            self._shipCurrentFuelSpinBox.setValue(float(shipCurrentFuel))
        if refuellingStrategy != None:
            self._refuellingStrategyComboBox.setCurrentEnum(refuellingStrategy)
        if routeOptimisation != None:
            self._routeOptimisationComboBox.setCurrentEnum(routeOptimisation)
        if perJumpOverheads != None:
            self._perJumpOverheadsSpinBox.setValue(int(perJumpOverheads))
        if includeStartWorldBerthingCosts != None:
            self._includeStartWorldBerthingCheckBox.setChecked(includeStartWorldBerthingCosts)
        if includeFinishWorldBerthingCosts != None:
            self._includeFinishWorldBerthingCheckBox.setChecked(includeFinishWorldBerthingCosts)

    def firstShowEvent(self, e: QtGui.QShowEvent) -> None:
        # Schedule the Traveller Map init fix to be run shortly after the window is displayed. We
        # can't run it directly here as the window won't have finished being resized (after loading
        # the saved window layout) so the fix won't work.
        QtCore.QTimer.singleShot(1000, self._travellerMapInitFix)
        QtCore.QTimer.singleShot(0, self._showWelcomeMessage)
        return super().firstShowEvent(e)

    def closeEvent(self, e: QtGui.QCloseEvent):
        if self._jumpRouteJob:
            self._jumpRouteJob.cancel(block=True)
            self._jumpRouteJob = None
        return super().closeEvent(e)

    # This is a MASSIVE hack. It works around the fact the Traveller Map widget isn't resized until
    # its tab is displayed. This caused zooming to the jump route to not zoom to the correct area
    # if the route was calculated before the widget was displayed for the first time. The hack works
    # by checking if the Traveller Map widget is not the displayed widget and forces a resize if
    # it's not.
    def _travellerMapInitFix(self) -> None:
        currentWidget = self._resultsDisplayModeTabView.currentWidget()
        if currentWidget != self._travellerMapWidget:
            size = currentWidget.size()
            self._travellerMapWidget.resize(size)
            self._travellerMapWidget.show()

    def _setupJumpWorldsControls(self) -> None:
        # TODO: I will probably need to update this to allow the start/finish to be
        # in dead space
        self._startFinishWorldsWidget = _StartFinishWorldsSelectWidget()
        self._startFinishWorldsWidget.selectionChanged.connect(self._startFinishWorldsChanged)
        self._startFinishWorldsWidget.showWorldRequested.connect(self._showWorldInTravellerMap)

        groupLayout = QtWidgets.QVBoxLayout()
        groupLayout.addWidget(self._startFinishWorldsWidget)

        self._jumpWorldsGroupBox = QtWidgets.QGroupBox('Jump Worlds')
        self._jumpWorldsGroupBox.setLayout(groupLayout)

    def _setupConfigurationControls(self) -> None:
        #
        # Route Configuration
        #
        self._routeOptimisationComboBox = gui.SharedRouteOptimisationComboBox()

        self._fuelBasedRoutingCheckBox = gui.SharedFuelBasedRoutingCheckBox()
        self._fuelBasedRoutingCheckBox.stateChanged.connect(
            self._fuelBasedRoutingToggled)

        self._refuellingStrategyComboBox = gui.SharedRefuellingStrategyComboBox()
        self._refuellingStrategyComboBox.setEnabled(
            self._fuelBasedRoutingCheckBox.isChecked())

        self._useFuelCachesCheckBox = gui.SharedUseFuelCachesCheckBox()
        self._useFuelCachesCheckBox.setEnabled(
            self._fuelBasedRoutingCheckBox.isChecked())

        self._useAnomalyRefuellingCheckBox = gui.SharedUseAnomalyRefuellingCheckBox()
        self._useAnomalyRefuellingCheckBox.setEnabled(
            self._fuelBasedRoutingCheckBox.isChecked())
        self._useAnomalyRefuellingCheckBox.stateChanged.connect(self._anomalyRefuellingToggled)

        self._anomalyFuelCostSpinBox = gui.SharedAnomalyFuelCostSpinBox()
        self._anomalyFuelCostSpinBox.setEnabled(
            self._fuelBasedRoutingCheckBox.isChecked() and
            self._useAnomalyRefuellingCheckBox.isChecked())

        self._anomalyBerthingCostSpinBox = gui.SharedAnomalyBerthingCostSpinBox()
        self._anomalyBerthingCostSpinBox.setEnabled(
            self._fuelBasedRoutingCheckBox.isChecked() and
            self._useAnomalyRefuellingCheckBox.isChecked())

        self._perJumpOverheadsSpinBox = gui.SharedJumpOverheadSpinBox()

        self._includeStartWorldBerthingCheckBox = gui.SharedIncludeStartBerthingCheckBox()
        self._includeFinishWorldBerthingCheckBox = gui.SharedIncludeFinishBerthingCheckBox()

        leftLayout = gui.FormLayoutEx()
        leftLayout.setContentsMargins(0, 0, 0, 0)
        leftLayout.addRow('Route Optimisation:', self._routeOptimisationComboBox)
        leftLayout.addRow('Fuel Based Routing:', self._fuelBasedRoutingCheckBox)
        leftLayout.addRow('Per Jump Overheads:', self._perJumpOverheadsSpinBox)
        leftLayout.addRow('Start World Berthing:', self._includeStartWorldBerthingCheckBox)
        leftLayout.addRow('Finish World Berthing:', self._includeFinishWorldBerthingCheckBox)

        rightLayout = gui.FormLayoutEx()
        rightLayout.setContentsMargins(0, 0, 0, 0)
        rightLayout.addRow('Refuelling Strategy:', self._refuellingStrategyComboBox)
        rightLayout.addRow('Use Fuel Caches:', self._useFuelCachesCheckBox)
        rightLayout.addRow('Use Anomaly Refuelling:', self._useAnomalyRefuellingCheckBox)
        rightLayout.addRow('Anomaly Fuel Cost:', self._anomalyFuelCostSpinBox)
        rightLayout.addRow('Anomaly Berthing Cost:', self._anomalyBerthingCostSpinBox)

        routingLayout = QtWidgets.QHBoxLayout()
        routingLayout.addLayout(leftLayout)
        routingLayout.addLayout(rightLayout)
        routingLayout.addStretch()

        #
        # Ship Configuration
        #
        self._shipTonnageSpinBox = gui.SharedShipTonnageSpinBox()
        self._shipJumpRatingSpinBox = gui.SharedJumpRatingSpinBox()
        self._shipJumpRatingSpinBox.valueChanged.connect(self._shipJumpRatingChanged)
        self._shipFuelCapacitySpinBox = gui.SharedFuelCapacitySpinBox()
        self._shipCurrentFuelSpinBox = gui.SharedCurrentFuelSpinBox()
        self._shipFuelPerParsecSpinBox = gui.SharedFuelPerParsecSpinBox()

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
            gui.LayoutWrapperWidget(layout=routingLayout),
            'Route')
        self._configurationStack.addTab(
            gui.LayoutWrapperWidget(layout=shipLayout),
            'Ship')

        configurationLayout = QtWidgets.QHBoxLayout()
        configurationLayout.addWidget(self._configurationStack)

        self._configurationGroupBox = QtWidgets.QGroupBox('Configuration')
        self._configurationGroupBox.setLayout(configurationLayout)

    def _setupWaypointWorldsControls(self) -> None:
        # TODO: This will need updated to handle waypoints in dead space
        # - IMPORTANT: Need to handle the case where users have waypoint lists already
        #   configured
        self._waypointWorldTable = gui.WorldBerthingTable()
        self._waypointWorldsWidget = gui.WorldTableManagerWidget(
            worldTable=self._waypointWorldTable,
            isOrderedList=True, # List order determines order waypoints are to be travelled to
            showSelectInTravellerMapButton=False, # The windows Traveller Map widget should be used to select worlds
            showAddNearbyWorldsButton=False) # Adding nearby worlds doesn't make sense for waypoints
        self._waypointWorldsWidget.contentChanged.connect(self._updateTravellerMapOverlays)
        self._waypointWorldsWidget.enableDisplayModeChangedEvent(enable=True)
        self._waypointWorldsWidget.displayModeChanged.connect(self._waypointsTableDisplayModeChanged)
        self._waypointWorldsWidget.enableShowInTravellerMapEvent(enable=True)
        self._waypointWorldsWidget.showInTravellerMap.connect(self._showWorldsInTravellerMap)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self._waypointWorldsWidget)

        self._waypointWorldsGroupBox = QtWidgets.QGroupBox('Waypoint Worlds')
        self._waypointWorldsGroupBox.setLayout(layout)

    def _setupAvoidWorldsControls(self) -> None:
        # TODO: Not sure if it make sense to allow avoiding dead space hexes
        self._avoidWorldsWidget = gui.WorldTableManagerWidget(
            allowWorldCallback=self._allowAvoidWorld,
            showSelectInTravellerMapButton=False) # The windows Traveller Map widget should be used to select worlds
        self._avoidWorldsWidget.contentChanged.connect(self._updateTravellerMapOverlays)
        self._avoidWorldsWidget.enableShowInTravellerMapEvent(enable=True)
        self._avoidWorldsWidget.showInTravellerMap.connect(self._showWorldsInTravellerMap)

        self._avoidWorldsFilterWidget = gui.WorldFilterTableManagerWidget()

        self._avoidWorldsTabWidget = gui.TabWidgetEx()
        self._avoidWorldsTabWidget.setTabPosition(QtWidgets.QTabWidget.TabPosition.West)
        self._avoidWorldsTabWidget.addTab(self._avoidWorldsWidget, 'Worlds')
        self._avoidWorldsTabWidget.addTab(self._avoidWorldsFilterWidget, 'Filters')

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self._avoidWorldsTabWidget)

        self._avoidWorldsGroupBox = QtWidgets.QGroupBox('Avoid Worlds')
        self._avoidWorldsGroupBox.setLayout(layout)

    def _setupJumpRouteControls(self) -> None:
        self._calculateRouteButton = gui.DualTextPushButton(
            primaryText='Calculate Jump Route',
            secondaryText='Cancel')
        self._calculateRouteButton.clicked.connect(self._calculateJumpRoute)

        self._processedRoutesLabel = gui.PrefixLabel(prefix='Processed Routes: ')
        self._jumpCountLabel = gui.PrefixLabel(prefix='Jumps: ')
        self._routeLengthLabel = gui.PrefixLabel(prefix='Parsecs: ')

        self._avgRouteCostLabel = gui.PrefixLabel(prefix='Avg Cost: ')
        self._minRouteCostLabel = gui.PrefixLabel(prefix='Min Cost: ')
        self._maxRouteCostLabel = gui.PrefixLabel(prefix='Max Cost: ')

        labelLayout = QtWidgets.QHBoxLayout()
        labelLayout.setContentsMargins(0, 0, 0, 0)
        labelLayout.setSpacing(int(15 * app.Config.instance().interfaceScale()))
        labelLayout.addWidget(self._processedRoutesLabel)
        labelLayout.addWidget(self._jumpCountLabel)
        labelLayout.addWidget(self._routeLengthLabel)
        labelLayout.addWidget(self._avgRouteCostLabel)
        labelLayout.addWidget(self._minRouteCostLabel)
        labelLayout.addWidget(self._maxRouteCostLabel)

        self._jumpRouteDisplayModeTabBar = gui.WorldTableTabBar()
        self._jumpRouteDisplayModeTabBar.currentChanged.connect(self._updateWorldTableColumns)

        # TODO: This will need a new table type that deals with nodes instead of worlds
        self._jumpRouteTable = gui.WorldTable()
        self._jumpRouteTable.setVisibleColumns(self._jumpRouteColumns())
        self._jumpRouteTable.setMinimumHeight(100)
        self._jumpRouteTable.setSortingEnabled(False) # Disable sorting as we only want to display in jump route order
        self._jumpRouteTable.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self._jumpRouteTable.customContextMenuRequested.connect(self._showJumpWorldsTableContextMenu)

        jumpRouteLayout = QtWidgets.QVBoxLayout()
        jumpRouteLayout.setContentsMargins(0, 0, 0, 0)
        jumpRouteLayout.setSpacing(0) # No spacing between tabs and table
        jumpRouteLayout.addWidget(self._jumpRouteDisplayModeTabBar)
        jumpRouteLayout.addWidget(self._jumpRouteTable)
        jumpRouteWidget = QtWidgets.QWidget()
        jumpRouteWidget.setLayout(jumpRouteLayout)

        self._refuellingPlanTable = _RefuellingPlanTable()
        self._refuellingPlanTable.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self._refuellingPlanTable.customContextMenuRequested.connect(self._showRefuellingPlanTableContextMenu)

        self._travellerMapWidget = gui.TravellerMapWidget()
        self._travellerMapWidget.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self._travellerMapWidget.setToolTipCallback(self._formatMapToolTip)
        self._travellerMapWidget.rightClicked.connect(self._showTravellerMapContextMenu)

        self._jumpRatingOverlayAction = QtWidgets.QAction('Jump Rating', self)
        self._jumpRatingOverlayAction.setCheckable(True)
        self._jumpRatingOverlayAction.setChecked(False)
        self._jumpRatingOverlayAction.triggered.connect(
            self._updateJumpOverlays)
        self._worldTaggingOverlayAction = QtWidgets.QAction('World Tagging', self)
        self._worldTaggingOverlayAction.setCheckable(True)
        self._worldTaggingOverlayAction.setChecked(False)
        self._worldTaggingOverlayAction.triggered.connect(
            self._updateJumpOverlays)
        self._travellerMapWidget.addConfigActions(
            section='Jump Overlays',
            actions=[self._jumpRatingOverlayAction, self._worldTaggingOverlayAction])

        self._resultsDisplayModeTabView = gui.TabWidgetEx()
        self._resultsDisplayModeTabView.setTabPosition(QtWidgets.QTabWidget.TabPosition.East)
        self._resultsDisplayModeTabView.addTab(jumpRouteWidget, 'Jump Route')
        self._resultsDisplayModeTabView.addTab(self._refuellingPlanTable, 'Refuelling Plan')
        self._resultsDisplayModeTabView.addTab(self._travellerMapWidget, 'Traveller Map')

        routeLayout = QtWidgets.QVBoxLayout()
        routeLayout.addWidget(self._calculateRouteButton)
        routeLayout.addLayout(labelLayout)
        routeLayout.addWidget(self._resultsDisplayModeTabView)

        self._plannedRouteGroupBox = QtWidgets.QGroupBox('Jump Route')
        self._plannedRouteGroupBox.setLayout(routeLayout)

    def _clearJumpRoute(self):
        self._jumpRouteTable.removeAllRows()
        self._refuellingPlanTable.removeAllRows()
        self._processedRoutesLabel.clear()
        self._jumpCountLabel.clear()
        self._routeLengthLabel.clear()
        self._avgRouteCostLabel.clear()
        self._minRouteCostLabel.clear()
        self._maxRouteCostLabel.clear()
        self._jumpRoute = None
        self._routeLogistics = None
        self._updateTravellerMapOverlays()

    def _startFinishWorldsChanged(self) -> None:
        # Always clear the current jump route as it's invalid if the finish world changes
        self._clearJumpRoute()

        self._updateTravellerMapOverlays()

        # When a new route is calculated for the first time after a start/finish world has been
        # changed, the Traveller Map widget should be zoomed to show the route as it may be
        # displaying a completely different location. After the first route has been calculated
        # for this start/finish pair the view is left as is as it's assumed the user is doing
        # something like adding a waypoint world
        self._zoomToJumpRoute = True

    def _waypointsTableDisplayModeChanged(self, displayMode: gui.WorldTableTabBar.DisplayMode) -> None:
        columns = None
        if displayMode == gui.WorldTableTabBar.DisplayMode.AllColumns:
            columns = gui.WorldBerthingTable.AllColumns
        elif displayMode == gui.WorldTableTabBar.DisplayMode.SystemColumns:
            columns = gui.WorldBerthingTable.SystemColumns
        elif displayMode == gui.WorldTableTabBar.DisplayMode.UWPColumns:
            columns = gui.WorldBerthingTable.UWPColumns
        elif displayMode == gui.WorldTableTabBar.DisplayMode.EconomicsColumns:
            columns = gui.WorldBerthingTable.EconomicsColumns
        elif displayMode == gui.WorldTableTabBar.DisplayMode.CultureColumns:
            columns = gui.WorldBerthingTable.CultureColumns
        elif displayMode == gui.WorldTableTabBar.DisplayMode.RefuellingColumns:
            columns = gui.WorldBerthingTable.RefuellingColumns
        else:
            assert(False) # I missed a case
        self._waypointWorldsWidget.setVisibleColumns(columns)

    # TODO: This will need various updates to allow the start/finish/waypoints to be
    # in dead space
    def _calculateJumpRoute(self) -> None:
        if self._jumpRouteJob:
            # A trade option job is already running so cancel it
            self._jumpRouteJob.cancel()
            return

        self._clearJumpRoute()

        startWorld, finishWorld = self._startFinishWorldsWidget.worlds()
        if not startWorld or not finishWorld:
            if not startWorld and not finishWorld:
                message = 'You need to select a start and finish world before calculating a route.'
            elif not startWorld:
                message = 'You need to select a start world before calculating a route.'
            else:
                message = 'You need to select a finish world before calculating a route.'
            gui.MessageBoxEx.information(parent=self, text=message)
            return

        # Fuel based route calculation
        pitCostCalculator = None
        if self._fuelBasedRoutingCheckBox.isChecked():
            useAnomalyRefuelling = self._useAnomalyRefuellingCheckBox.isChecked()
            pitCostCalculator = logic.PitStopCostCalculator(
                refuellingStrategy=self._refuellingStrategyComboBox.currentEnum(),
                useFuelCaches=self._useFuelCachesCheckBox.isChecked(),
                anomalyFuelCost=self._anomalyFuelCostSpinBox.value() if useAnomalyRefuelling else None,
                anomalyBerthingCost=self._anomalyBerthingCostSpinBox.value() if useAnomalyRefuelling else None,
                rules=app.Config.instance().rules())

            # Highlight cases where start world or waypoints don't support the
            # refuelling strategy
            if not pitCostCalculator.refuellingType(world=startWorld):
                message = 'Fuel based route calculation is enabled but the start world doesn\'t support the selected refuelling strategy.'
                if self._shipCurrentFuelSpinBox.value() <= 0:
                    message += ' In order to calculate a route, you must specify the amount of fuel that is currently in the ship.'
                    gui.MessageBoxEx.information(parent=self, text=message)
                    return

                message += 'The ability to generate a route and refuelling plan will be limited by the the amount of fuel the ship currently has.\n\nDo you want to continue?'
                answer = gui.AutoSelectMessageBox.question(
                    parent=self,
                    text=message,
                    stateKey='JumpRouteStartRefuellingStrategy',
                    # Only remember if the user clicked yes
                    rememberState=QtWidgets.QMessageBox.StandardButton.Yes)
                if answer == QtWidgets.QMessageBox.StandardButton.No:
                    return

            fuelIssueWorldStrings = []
            for waypointWorld in self._waypointWorldsWidget.worlds():
                if not pitCostCalculator.refuellingType(world=waypointWorld):
                    fuelIssueWorldStrings.append(waypointWorld.name())

            if fuelIssueWorldStrings:
                worldListString = common.humanFriendlyListString(fuelIssueWorldStrings)
                if len(fuelIssueWorldStrings) == 1:
                    message = f'Fuel based route calculation is enabled but waypoint {worldListString} doesn\'t support the selected refuelling strategy. '
                else:
                    message = f'Fuel based route calculation is enabled but waypoints {worldListString} don\'t support the selected refuelling strategy. '
                message += 'This may prevent the generation of a route and/or refuelling plan.'

                answer = gui.AutoSelectMessageBox.question(
                    parent=self,
                    text=message + '\n\nDo you want to continue?',
                    stateKey='JumpRouteWaypointRefuellingStrategy',
                    # Only remember if the user clicked yes
                    rememberState=QtWidgets.QMessageBox.StandardButton.Yes)
                if answer == QtWidgets.QMessageBox.StandardButton.No:
                    return

        worldList = [startWorld]
        worldList.extend(self._waypointWorldsWidget.worlds())
        worldList.append(finishWorld)

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

        hexFilter = _HexFilter(
            avoidWorlds=self._avoidWorldsWidget.worlds(),
            avoidFilters=self._avoidWorldsFilterWidget.filters(),
            avoidFilterLogic=self._avoidWorldsFilterWidget.filterLogic())

        try:
            self._jumpRouteJob = jobs.RoutePlannerJob(
                parent=self,
                worldSequence=worldList,
                shipTonnage=self._shipTonnageSpinBox.value(),
                shipJumpRating=self._shipJumpRatingSpinBox.value(),
                shipFuelCapacity=self._shipFuelCapacitySpinBox.value(),
                shipCurrentFuel=self._shipCurrentFuelSpinBox.value(),
                shipFuelPerParsec=self._shipFuelPerParsecSpinBox.value(),
                jumpCostCalculator=jumpCostCalculator,
                pitCostCalculator=pitCostCalculator,
                hexFilter=hexFilter,
                progressCallback=self._jumpRouteJobProgressUpdate,
                finishedCallback=self._jumpRouteJobFinished)
        except Exception as ex:
            message = 'Failed to start route planner job'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

        self._calculateRouteButton.showSecondaryText()
        self._enableDisableControls()

    def _jumpRouteJobProgressUpdate(self, routeCount: int) -> None:
        self._processedRoutesLabel.setNum(routeCount)

    def _jumpRouteJobFinished(self, result: typing.Union[typing.Optional[logic.JumpRoute], Exception]) -> None:
        if isinstance(result, Exception):
            startWorld, finishWorld = self._startFinishWorldsWidget.worlds()
            message = 'Failed to calculate jump route between {start} and {finish}'.format(
                start=startWorld.name(includeSubsector=True) if startWorld else 'Unknown',
                finish=finishWorld.name(includeSubsector=True) if finishWorld else 'Unknown')
            logging.error(message, exc_info=result)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=result)
        elif self._jumpRouteJob and self._jumpRouteJob.isCancelled():
            pass
        else:
            self._setJumpRoute(result)

        self._jumpRouteJob = None
        self._calculateRouteButton.showPrimaryText()
        self._enableDisableControls()

    def _updateWorldTableColumns(self, index: int) -> None:
        self._jumpRouteTable.setVisibleColumns(self._jumpRouteColumns())

    def _jumpRouteColumns(self) -> typing.List[gui.WorldTable.ColumnType]:
        displayMode = self._jumpRouteDisplayModeTabBar.currentDisplayMode()
        if displayMode == gui.WorldTableTabBar.DisplayMode.AllColumns:
            return gui.WorldTable.AllColumns
        elif displayMode == gui.WorldTableTabBar.DisplayMode.SystemColumns:
            return gui.WorldTable.SystemColumns
        elif displayMode == gui.WorldTableTabBar.DisplayMode.UWPColumns:
            return gui.WorldTable.UWPColumns
        elif displayMode == gui.WorldTableTabBar.DisplayMode.EconomicsColumns:
            return gui.WorldTable.EconomicsColumns
        elif displayMode == gui.WorldTableTabBar.DisplayMode.CultureColumns:
            return gui.WorldTable.CultureColumns
        elif displayMode == gui.WorldTableTabBar.DisplayMode.RefuellingColumns:
            return gui.WorldTable.RefuellingColumns
        else:
            assert(False) # I missed a case

    # TODO: This will need updated to account for the fact the "jump worlds table"
    # will actually be dealing with nodes so some options might not apply (e.g.
    # show world details only makes sense if a world node is selected)
    def _showJumpWorldsTableContextMenu(self, position: QtCore.QPoint) -> None:
        menuItems = [
            gui.MenuItem(
                text='Add Selected Worlds to Waypoints',
                callback=lambda: [self._waypointWorldsWidget.addWorld(world) for world in self._jumpRouteTable.selectedWorlds()],
                enabled=self._jumpRouteTable.hasSelection()
            ),
            gui.MenuItem(
                text='Add Selected Worlds to Avoid Worlds',
                callback=lambda: [self._avoidWorldsWidget.addWorld(world) for world in self._jumpRouteTable.selectedWorlds()],
                enabled=self._jumpRouteTable.hasSelection()
            ),
            None, # Separator
            gui.MenuItem(
                text='Show Selected World Details...',
                callback=lambda: self._showWorldDetails(self._jumpRouteTable.selectedWorlds()),
                enabled=self._jumpRouteTable.hasSelection()
            ),
            gui.MenuItem(
                text='Show All World Details...',
                callback=lambda: self._showWorldDetails(self._jumpRouteTable.worlds()),
                enabled=not self._jumpRouteTable.isEmpty()
            ),
            None, # Separator
            gui.MenuItem(
                text='Show Selected Worlds in Traveller Map',
                callback=lambda: self._showWorldsInTravellerMap(self._jumpRouteTable.selectedWorlds()),
                enabled=self._jumpRouteTable.hasSelection()
            ),
            gui.MenuItem(
                text='Show All Worlds in Traveller Map',
                callback=lambda: self._showWorldsInTravellerMap(self._jumpRouteTable.worlds()),
                enabled=not self._jumpRouteTable.isEmpty()
            )
        ]

        gui.displayMenu(
            self,
            menuItems,
            self._jumpRouteTable.viewport().mapToGlobal(position)
        )

    def _showRefuellingPlanTableContextMenu(self, position: QtCore.QPoint) -> None:
        menuItems = [
            gui.MenuItem(
                text='Add Selected Worlds to Waypoints',
                callback=lambda: [self._waypointWorldsWidget.addWorld(world) for world in self._refuellingPlanTable.selectedWorlds()],
                enabled=self._refuellingPlanTable.hasSelection()
            ),
            gui.MenuItem(
                text='Add Selected Worlds to Avoid Worlds',
                callback=lambda: [self._avoidWorldsWidget.addWorld(world) for world in self._refuellingPlanTable.selectedWorlds()],
                enabled=self._refuellingPlanTable.hasSelection()
            ),
            None, # Separator
            gui.MenuItem(
                text='Show Selected world details...',
                callback=lambda: self._showWorldDetails(self._refuellingPlanTable.selectedWorlds()),
                enabled=self._refuellingPlanTable.hasSelection()
            ),
            gui.MenuItem(
                text='Show All World Details...',
                callback=lambda: self._showWorldDetails(self._refuellingPlanTable.worlds()),
                enabled=not self._refuellingPlanTable.isEmpty()
            ),
            None, # Separator
            gui.MenuItem(
                text='Show Selected Worlds in Traveller Map',
                callback=lambda: self._showWorldsInTravellerMap(self._refuellingPlanTable.selectedWorlds()),
                enabled=self._refuellingPlanTable.hasSelection()
            ),
            gui.MenuItem(
                text='Show All Worlds in Traveller Map',
                callback=lambda: self._showWorldsInTravellerMap(self._refuellingPlanTable.worlds()),
                enabled=not self._refuellingPlanTable.isEmpty()
            ),
            None, # Separator
            gui.MenuItem(
                text='Show Pit Stop Calculations...',
                callback=lambda: self._showCalculations(self._refuellingPlanTable.pitStopAt(position).totalCost()),
                enabled=self._refuellingPlanTable.pitStopAt(position) != None
            ),
            gui.MenuItem(
                text='Show All Refuelling Calculations...',
                callback=lambda: self._showCalculations(self._routeLogistics.totalCosts()),
                enabled=self._routeLogistics != None
            ),
        ]

        gui.displayMenu(
            self,
            menuItems,
            self._refuellingPlanTable.viewport().mapToGlobal(position)
        )

    # TODO: This will need updated to allow setting start/finish/waypoints
    # to dead space
    def _showTravellerMapContextMenu(
            self,
            sectorHex: str
            ) -> None:
        clickedWorld = None
        try:
            if sectorHex:
                clickedWorld = traveller.WorldManager.instance().world(sectorHex=sectorHex)
        except Exception as ex:
            logging.warning(
                f'An exception occurred while resolving sector hex "{sectorHex}" to world for context menu',
                exc_info=ex)

        startWorld, finishWorld = self._startFinishWorldsWidget.worlds()

        menuItems = []

        action = QtWidgets.QAction('Recalculate Jump Route', self)
        menuItems.append(action)
        action.triggered.connect(self._calculateJumpRoute)
        action.setEnabled((startWorld != None) and (finishWorld != None))

        action = QtWidgets.QAction('Show World Details...', self)
        menuItems.append(action)
        action.triggered.connect(lambda: self._showWorldDetails([clickedWorld]))
        action.setEnabled(clickedWorld != None)

        menu = QtWidgets.QMenu('Start/Finish Worlds', self)
        menuItems.append(menu)
        action = menu.addAction('Set Start World')
        action.triggered.connect(lambda: self._startFinishWorldsWidget.setStartWorld(clickedWorld))
        action.setEnabled(clickedWorld != None)
        action = menu.addAction('Set Finish World')
        action.triggered.connect(lambda: self._startFinishWorldsWidget.setFinishWorld(clickedWorld))
        action.setEnabled(clickedWorld != None)
        action = menu.addAction('Swap Start && Finish Worlds')
        action.triggered.connect(lambda: self._startFinishWorldsWidget.setStartFinishWorlds(startWorld=finishWorld, finishWorld=startWorld))
        action.setEnabled((startWorld != None) and (finishWorld != None))

        menu = QtWidgets.QMenu('Waypoint Worlds', self)
        menuItems.append(menu)
        action = menu.addAction('Add World')
        action.triggered.connect(lambda: self._waypointWorldsWidget.addWorld(clickedWorld))
        action.setEnabled(clickedWorld != None and not self._waypointWorldsWidget.containsWorld(clickedWorld))
        action = menu.addAction('Remove World')
        action.triggered.connect(lambda: self._waypointWorldsWidget.removeWorld(clickedWorld))
        action.setEnabled(clickedWorld != None and self._waypointWorldsWidget.containsWorld(clickedWorld))

        menu = QtWidgets.QMenu('Avoid Worlds', self)
        menuItems.append(menu)
        action = menu.addAction('Add World')
        action.triggered.connect(lambda: self._avoidWorldsWidget.addWorld(clickedWorld))
        action.setEnabled(clickedWorld != None and not self._avoidWorldsWidget.containsWorld(clickedWorld))
        action = menu.addAction('Remove World')
        action.triggered.connect(lambda: self._avoidWorldsWidget.removeWorld(clickedWorld))
        action.setEnabled(clickedWorld != None and self._avoidWorldsWidget.containsWorld(clickedWorld))

        menu = QtWidgets.QMenu('Zoom To', self)
        menuItems.append(menu)
        action = menu.addAction('Start World')
        action.triggered.connect(lambda: self._showWorldInTravellerMap(startWorld))
        action.setEnabled(startWorld != None)
        action = menu.addAction('Finish World')
        action.triggered.connect(lambda: self._showWorldInTravellerMap(finishWorld))
        action.setEnabled(finishWorld != None)
        action = menu.addAction('Jump Route')
        action.triggered.connect(lambda: self._showWorldsInTravellerMap(self._jumpRoute))
        action.setEnabled(self._jumpRoute != None)

        menu = QtWidgets.QMenu('Export', self)
        menuItems.append(menu)
        action = menu.addAction('Jump Route...')
        action.triggered.connect(self._exportJumpRoute)
        action.setEnabled(self._jumpRoute != None)
        action = menu.addAction('Screenshot...')
        action.setEnabled(True)
        action.triggered.connect(self._exportMapScreenshot)

        gui.displayMenu(
            parent=self,
            items=menuItems,
            globalPosition=QtGui.QCursor.pos())

    def _formatMapToolTip(
            self,
            sectorHex: typing.Optional[str]
            ) -> typing.Optional[str]:
        if not sectorHex:
            return None

        hoverWorld = traveller.WorldManager.instance().world(sectorHex=sectorHex)
        if not hoverWorld:
            return None

        # TODO: This will need updated to account for the fact start/finish/waypoints
        # can be in dead space
        if not self._jumpRoute:
            toolTip = ''
            if hoverWorld == self._startFinishWorldsWidget.startWorld() and \
                    hoverWorld == self._startFinishWorldsWidget.finishWorld():
                return gui.createStringToolTip('<nobr>Start &amp; Finish World</nobr>', escape=False)
            elif hoverWorld == self._startFinishWorldsWidget.startWorld():
                return gui.createStringToolTip('<nobr>Start World</nobr>', escape=False)
            elif hoverWorld == self._startFinishWorldsWidget.finishWorld():
                return gui.createStringToolTip('<nobr>Finish World</nobr>', escape=False)
            elif self._waypointWorldsWidget.containsWorld(hoverWorld):
                return gui.createStringToolTip('<nobr>Waypoint World</nobr>', escape=False)
            elif self._avoidWorldsWidget.containsWorld(hoverWorld):
                return gui.createStringToolTip('<nobr>Avoid World</nobr>', escape=False)
            return None

        # TODO: This will need updated to get the world for the node
        # and use it for the comparison
        jumpNodes: typing.Dict[int, typing.Optional[logic.PitStop]] = {}
        for node in range(self._jumpRoute.worldCount()):
            if self._jumpRoute[node] == hoverWorld:
                jumpNodes[node] = None

        if self._routeLogistics:
            refuellingPlan = self._routeLogistics.refuellingPlan()
            if refuellingPlan:
                for pitStop in refuellingPlan:
                    if pitStop.jumpIndex() in jumpNodes:
                        jumpNodes[pitStop.jumpIndex()] = pitStop

        toolTip = ''
        for node, pitStop in jumpNodes.items():
            toolTip += f'<li><nobr>Route World: {node + 1}</nobr></li>'

            if node != 0:
                toolTip += '<li><nobr>Route Distance: {} parsecs</nobr></li>'.format(
                    self._jumpRoute.nodeParsecs(node=node))

            if not pitStop:
                continue # Nothing mor to do

            refuellingType = pitStop.refuellingType()
            if refuellingType:
                toolTip += '<li><nobr>Refuelling Type: {}</nobr></li>'.format(
                    _formatRefuellingTypeString(pitStop=pitStop))

                tonsOfFuel = pitStop.tonsOfFuel()
                toolTip += '<li><nobr>Fuel Amount: {} tons</nobr></li>'.format(
                    common.formatNumber(number=tonsOfFuel.value()))

                fuelCost = pitStop.fuelCost()
                if fuelCost:
                    toolTip += '<li><nobr>Fuel Cost: Cr{}</nobr></li>'.format(
                        common.formatNumber(number=fuelCost.value()))

            berthingCost = pitStop.berthingCost()
            if berthingCost:
                toolTip += '<li><nobr>Berthing Type: {}</nobr></li>'.format(
                    _formatBerthingTypeString(pitStop=pitStop))
                if isinstance(berthingCost, common.ScalarCalculation):
                    toolTip += '<li><nobr>Berthing Cost: Cr{}</nobr></li>'.format(
                        common.formatNumber(number=berthingCost.value()))
                elif isinstance(berthingCost, common.RangeCalculation):
                    toolTip += '<li><nobr>Berthing Cost: Cr{best} - Cr{worst}</nobr></li>'.format(
                        best=common.formatNumber(number=berthingCost.bestCaseValue()),
                        worst=common.formatNumber(number=berthingCost.worstCaseValue()))

            toolTip += '</ul>'

        if not toolTip:
            # Check for waypoints that have been added since the route was last regenerated
            # TODO: This will need updated to account for the fact waypoints can be dead space
            if self._waypointWorldsWidget.containsWorld(hoverWorld):
                return gui.createStringToolTip('<nobr>Waypoint World</nobr>', escape=False)

            # Check for the world being an avoid world. This is done last as
            # start/finish/waypoint worlds can be on the avoid list but we
            # don't want to flag them as such here
            if self._avoidWorldsWidget.containsWorld(hoverWorld):
                return gui.createStringToolTip('<nobr>Avoid World</nobr>', escape=False)

            return None

        toolTip = f'<ul style="list-style-type:none; margin-left:0px; -qt-list-indent:0;">{toolTip}</ul>'
        return gui.createStringToolTip(toolTip, escape=False)

    def _exportJumpRoute(self) -> None:
        if not self._jumpRoute:
            gui.MessageBoxEx.information(
                parent=self,
                text='No jump route to export')
            return

        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            parent=self,
            caption='Export Jump Route',
            directory=QtCore.QDir.homePath() + '/route.json',
            filter='JSON Files (*.json)')
        if not path:
            return

        try:
            logic.writeJumpRoute(self._jumpRoute, path)
        except Exception as ex:
            message = f'Failed to write jump route to "{path}"'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)

    def _exportMapScreenshot(self) -> None:
        try:
            snapshot = self._travellerMapWidget.createSnapshot()
        except Exception as ex:
            message = 'An exception occurred while generating the snapshot'
            logging.error(msg=message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

        # https://doc.qt.io/qt-5/qpixmap.html#reading-and-writing-image-files
        _SupportedFormats = {
            'Bitmap (*.bmp)': 'bmp',
            'JPEG (*.jpg *.jpeg)': 'jpg',
            'PNG (*.png)': 'png',
            'Portable Pixmap (*.ppm)': 'ppm',
            'X11 Bitmap (*.xbm)': 'xbm',
            'X11 Pixmap (*.xpm)': 'xpm'}

        path, filter = QtWidgets.QFileDialog.getSaveFileName(
            parent=self,
            caption='Export Snapshot',
            filter=';;'.join(_SupportedFormats.keys()))
        if not path:
            return # User cancelled

        format = _SupportedFormats.get(filter)
        if format is None:
            message = f'Unable to save unknown format "{filter}"'
            logging.error(msg=message)
            gui.MessageBoxEx.critical(message)
            return

        try:
            if not snapshot.save(path, format):
                gui.MessageBoxEx.critical(f'Failed to save snapshot to "{path}"')
        except Exception as ex:
            message = f'An exception occurred while saving the snapshot to "{path}"'
            logging.error(msg=message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)

    def _showWorldDetails(
            self,
            worlds: typing.Iterable[traveller.World]
            ) -> None:
        infoWindow = gui.WindowManager.instance().showWorldDetailsWindow()
        infoWindow.addWorlds(worlds=worlds)

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

    def _showWorldInTravellerMap(
            self,
            world: traveller.World
            ) -> None:
        try:
            self._resultsDisplayModeTabView.setCurrentWidget(self._travellerMapWidget)
            self._travellerMapWidget.centerOnWorld(
                world=world,
                clearOverlays=False,
                highlightWorld=False)
        except Exception as ex:
            message = 'Failed to show world(s) in Traveller Map'
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
            self._resultsDisplayModeTabView.setCurrentWidget(self._travellerMapWidget)
            self._travellerMapWidget.centerOnWorlds(
                worlds=worlds,
                clearOverlays=False,
                highlightWorlds=False)
        except Exception as ex:
            message = 'Failed to show world(s) in Traveller Map'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)

    def _updateJumpOverlays(self) -> None:
        for handle in self._jumpOverlayHandles:
            self._travellerMapWidget.removeOverlayGroup(handle=handle)
        self._jumpOverlayHandles.clear()

        showJumpRatingOverlay = self._jumpRatingOverlayAction.isChecked()
        showWorldTaggingOverlay = self._worldTaggingOverlayAction.isChecked()
        if not (showJumpRatingOverlay or showWorldTaggingOverlay):
            return # Nothing more to do

        startWorld, finishWorld = self._startFinishWorldsWidget.worlds()
        if not startWorld:
            return # Nothing more to do

        jumpRating = self._shipJumpRatingSpinBox.value()

        if showJumpRatingOverlay:
            isDarkMapStyle = travellermap.isDarkStyle(
                style=app.Config.instance().mapStyle())
            colour = self._JumpRatingOverlayDarkStyleColour \
                if isDarkMapStyle else \
                self._JumpRatingOverlayLightStyleColour
            handle = self._travellerMapWidget.createWorldRadiusOverlayGroup(
                centerWorld=startWorld,
                radius=jumpRating,
                lineColour=colour,
                lineWidth=self._JumpRatingOverlayLineWidth)
            self._jumpOverlayHandles.add(handle)

        if showWorldTaggingOverlay:
            try:
                worlds = traveller.WorldManager.instance().worldsInArea(
                    center=startWorld.hexPosition(),
                    searchRadius=jumpRating)
            except Exception as ex:
                logging.warning(
                    f'An exception occurred while finding worlds reachable from {startWorld.name()} ({startWorld.sectorName()})',
                    exc_info=ex)
                return

            taggedWorlds = []
            for world in worlds:
                if (world == startWorld) or (world == finishWorld):
                    continue # Don't highlight start/finish worlds
                tagLevel = app.calculateWorldTagLevel(world=world)
                if not tagLevel:
                    continue

                colour = QtGui.QColor(app.tagColour(
                    tagLevel=tagLevel))
                tagColour = gui.colourToString(
                    colour=colour,
                    includeAlpha=False)
                taggedWorlds.append((world, tagColour))

            if taggedWorlds:
                handle = self._travellerMapWidget.createWorldOverlayGroup(
                    worlds=taggedWorlds)
                self._jumpOverlayHandles.add(handle)

    def _updateTravellerMapOverlays(self) -> None:
        self._travellerMapWidget.clearOverlays()
        self._jumpRatingOverlayHandle = None
        self._reachableWorldsOverlayHandle = None

        startWorld, finishWorld = self._startFinishWorldsWidget.worlds()
        if startWorld:
            self._travellerMapWidget.highlightWorld(
                world=startWorld,
                colour='#00FF00',
                radius=0.5)
        if finishWorld:
            self._travellerMapWidget.highlightWorld(
                world=finishWorld,
                colour='#00FF00',
                radius=0.5)

        waypointWorlds = self._waypointWorldsWidget.worlds()
        if waypointWorlds:
            self._travellerMapWidget.highlightWorlds(
                worlds=waypointWorlds,
                colour='#0066FF',
                radius=0.3)

        filteredAvoidWorlds = []
        for world in self._avoidWorldsWidget.worlds():
            if (world != startWorld) and (world != finishWorld) and (world not in waypointWorlds):
                filteredAvoidWorlds.append(world)
        if filteredAvoidWorlds:
            self._travellerMapWidget.highlightWorlds(
                worlds=filteredAvoidWorlds,
                colour='#FF0000',
                radius=0.3)

        if self._jumpRoute:
            # TODO: The showJumpRoute method will need updated to take a list of nodes
            # rather than a list of worlds
            self._travellerMapWidget.showJumpRoute(
                jumpRoute=self._jumpRoute,
                refuellingPlan=self._routeLogistics.refuellingPlan() if self._routeLogistics else None,
                # Only zoom to area if this is a 'new' route (i.e. the start/finish worlds have changed).
                # Otherwise we assume this is an iteration of the existing jump route and the user wants
                # to stay with their current view
                zoomToArea=self._zoomToJumpRoute,
                clearOverlays=False,
                pitStopRadius=0.4)

        self._updateJumpOverlays()

    def _shipJumpRatingChanged(self) -> None:
        self._updateJumpOverlays()

    def _fuelBasedRoutingToggled(self) -> None:
        self._enableDisableControls()

    def _anomalyRefuellingToggled(self) -> None:
        self._enableDisableControls()

    def _enableDisableControls(self) -> None:
        # Disable configuration controls while jump route job is running
        runningJob = self._jumpRouteJob != None
        self._jumpWorldsGroupBox.setDisabled(runningJob)
        self._configurationGroupBox.setDisabled(runningJob)
        self._waypointWorldsGroupBox.setDisabled(runningJob)
        self._avoidWorldsGroupBox.setDisabled(runningJob)

        fuelBasedRouting = self._fuelBasedRoutingCheckBox.isChecked()
        anomalyRefuelling = self._useAnomalyRefuellingCheckBox.isChecked()
        self._refuellingStrategyComboBox.setEnabled(fuelBasedRouting)
        self._useFuelCachesCheckBox.setEnabled(fuelBasedRouting)
        self._useAnomalyRefuellingCheckBox.setEnabled(fuelBasedRouting)
        self._anomalyFuelCostSpinBox.setEnabled(fuelBasedRouting and anomalyRefuelling)
        self._anomalyBerthingCostSpinBox.setEnabled(fuelBasedRouting and anomalyRefuelling)

    def _selectWorld(self) -> typing.Optional[traveller.World]:
        dlg = gui.WorldSearchDialog(parent=self)
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return None
        return dlg.world()

    def _allowAvoidWorld(self, world: traveller.World) -> bool:
        if self._avoidWorldsWidget.containsWorld(world):
            # Silently ignore worlds that are already in the table
            return False
        return True

    def _setJumpRoute(self, jumpRoute: logic.JumpRoute) -> None:
        self._jumpRoute = jumpRoute
        if not self._jumpRoute:
            gui.MessageBoxEx.information(
                parent=self,
                text='No jump route found')
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

        # TODO: This will need updated as the jump route table will be dealing
        # with nodes
        self._jumpRouteTable.addWorlds(worlds=self._jumpRoute)
        self._jumpCountLabel.setNum(self._jumpRoute.jumpCount())
        self._routeLengthLabel.setNum(self._jumpRoute.totalParsecs())

        # Only calculate logistics if fuel based routing is enabled. If it's disabled the route will
        # most likely contain worlds that don't match the refuelling strategy
        if self._fuelBasedRoutingCheckBox.isChecked():
            useAnomalyRefuelling = self._useAnomalyRefuellingCheckBox.isChecked()
            pitCostCalculator = logic.PitStopCostCalculator(
                refuellingStrategy=self._refuellingStrategyComboBox.currentEnum(),
                useFuelCaches=self._useFuelCachesCheckBox.isChecked(),
                anomalyFuelCost=self._anomalyFuelCostSpinBox.value() if useAnomalyRefuelling else None,
                anomalyBerthingCost=self._anomalyBerthingCostSpinBox.value() if useAnomalyRefuelling else None,
                rules=app.Config.instance().rules())

            try:
                self._routeLogistics = logic.calculateRouteLogistics(
                    jumpRoute=self._jumpRoute,
                    shipTonnage=self._shipTonnageSpinBox.value(),
                    shipFuelCapacity=self._shipFuelCapacitySpinBox.value(),
                    shipStartingFuel=self._shipCurrentFuelSpinBox.value(),
                    shipFuelPerParsec=self._shipFuelPerParsecSpinBox.value(),
                    perJumpOverheads=self._perJumpOverheadsSpinBox.value(),
                    pitCostCalculator=pitCostCalculator,
                    requiredBerthingIndices=self._generateRequiredBerthingIndices(),
                    includeLogisticsCosts=True) # Always include logistics costs
                if not self._routeLogistics:
                    gui.MessageBoxEx.information(
                        parent=self,
                        text='Unable to calculate logistics for jump route')
            except Exception as ex:
                # TODO: This will need updated to account for the fact the start/finish world
                # could be dead space
                startWorld = self._jumpRoute.startWorld()
                finishWorld = self._jumpRoute.finishWorld()
                message = 'Failed to calculate jump route logistics between {start} and {finish}'.format(
                    start=startWorld.name(includeSubsector=True),
                    finish=finishWorld.name(includeSubsector=True))
                logging.error(message, exc_info=ex)
                gui.MessageBoxEx.critical(
                    parent=self,
                    text=message,
                    exception=ex)

            if self._routeLogistics:
                self._refuellingPlanTable.setPitStops(
                    pitStops=self._routeLogistics.refuellingPlan())
                routeCost = self._routeLogistics.totalCosts()
                self._avgRouteCostLabel.setText(common.formatNumber(
                    number=routeCost.averageCaseValue(),
                    infix='Cr'))
                self._minRouteCostLabel.setText(common.formatNumber(
                    number=routeCost.bestCaseValue(),
                    infix='Cr'))
                self._maxRouteCostLabel.setText(common.formatNumber(
                    number=routeCost.worstCaseValue(),
                    infix='Cr'))

        self._updateTravellerMapOverlays()

        # We've calculated a new jump route so prevent further recalculations of this route from
        # zooming out to show the full jump route. Zooming will be re-enabled if we start
        # calculating a "new" jump route (i.e the start/finish world changes)
        self._zoomToJumpRoute = False

    def _generateRequiredBerthingIndices(self) -> typing.Optional[typing.Set[int]]:
        if not self._jumpRoute or self._jumpRoute.worldCount() < 1:
            return None

        # The jump route planner will reduce sequences of the same waypoint world to a single
        # stop at that world. In order to match the waypoints to the jump route we need to
        # remove such sequences. This includes sequences where the worlds at the start of the
        # waypoint list match the start world and/or worlds at the end of the list match the
        # finish world.

        waypoints = []

        # TODO: This will need updated to account for the fact the start/finish world
        # could be in dead space
        waypoints.append((self._jumpRoute.startWorld(), self._includeStartWorldBerthingCheckBox.isChecked()))

        for row in range(self._waypointWorldTable.rowCount()):
            world = self._waypointWorldTable.world(row)
            berthingRequired = self._waypointWorldTable.isBerthingChecked(row)
            waypoints.append((world, berthingRequired))

        waypoints.append((self._jumpRoute.finishWorld(), self._includeFinishWorldBerthingCheckBox.isChecked()))

        requiredBerthingIndices = set()

        for waypointIndex in range(len(waypoints) - 1, 0, -1):
            if waypoints[waypointIndex][0] == waypoints[waypointIndex - 1][0]:
                # This is a sequence of the same world so remove the last instance in the sequence
                if waypoints[waypointIndex][1]:
                    # Berthing is required if any of the instances of the world in the sequence are
                    # marked as requiring berthing
                    waypoints[waypointIndex - 1] = waypoints[waypointIndex]
                waypoints.pop(waypointIndex)

        waypointIndex = 0
        for jumpIndex in range(self._jumpRoute.worldCount()):
            # TODO: This will need updated to account for the fact indexing
            # the jump route will get a node not a world
            if self._jumpRoute[jumpIndex] == waypoints[waypointIndex][0]:
                # We've found the current waypoint on the jump route
                if waypoints[waypointIndex][1]:
                    requiredBerthingIndices.add(jumpIndex)
                waypointIndex += 1
                if waypointIndex >= len(waypoints):
                    # All waypoints have been matched to the jump route
                    break

        if waypointIndex < len(waypoints):
            # Failed to match waypoints to jump route
            raise RuntimeError('Failed to match waypoints to jump route')

        return requiredBerthingIndices

    def _showWelcomeMessage(self) -> None:
        message = gui.InfoDialog(
            parent=self,
            title=self.windowTitle(),
            html=_WelcomeMessage,
            noShowAgainId='JumpRouteWelcome')
        message.exec()
