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

class _HexFilter(logic.HexFilterInterface):
    def __init__(
            self,
            avoidHexes: typing.List[travellermap.HexPosition],
            avoidFilters: typing.List[logic.WorldFilter],
            avoidFilterLogic: logic.FilterLogic
            ) -> None:
        self._avoidHexes = set(avoidHexes) if avoidHexes else None

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
        if self._avoidHexes and hex in self._avoidHexes:
            # Filter out worlds on the avoid list
            return False

        if self._avoidFilter and world and self._avoidFilter.checkWorld(world=world):
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

class _RefuellingPlanTable(gui.HexTable):
    AllColumns = [
        gui.HexTable.ColumnType.Name,
        gui.HexTable.ColumnType.Sector,
        _RefuellingPlanTableColumnType.RefuellingType,
        _RefuellingPlanTableColumnType.FuelTons,
        _RefuellingPlanTableColumnType.FuelCost,
        _RefuellingPlanTableColumnType.BerthingType,
        _RefuellingPlanTableColumnType.AverageCaseBerthingCost,
        _RefuellingPlanTableColumnType.WorstCaseBerthingCost,
        _RefuellingPlanTableColumnType.BestCaseBerthingCost,
        gui.HexTable.ColumnType.StarPort,
        gui.HexTable.ColumnType.GasGiantCount,
        gui.HexTable.ColumnType.Hydrographics
    ]

    def __init__(
            self,
            columns: typing.Iterable[typing.Union[_RefuellingPlanTableColumnType, gui.HexTable.ColumnType]] = AllColumns
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
            self.addHex(pos=pitStop.world())

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
            pos: travellermap.HexPosition,
            world: typing.Optional[traveller.World]
            ) -> int:
        assert(world) # Pitstops should always have a world

        # Disable sorting while updating a row. We don't want any sorting to occur
        # until all columns have been updated
        sortingEnabled = self.isSortingEnabled()
        self.setSortingEnabled(False)

        try:
            super()._fillRow(row, pos, world)

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
                    tableItem.setData(QtCore.Qt.ItemDataRole.UserRole, (pos, world))

            # Take note of the sort column item so we can determine which row index after the table
            # has been sorted
            sortItem = self.item(row, self.horizontalHeader().sortIndicatorSection())
        finally:
            self.setSortingEnabled(sortingEnabled)

        # If we don't have a sort item we assume a derived class has overridden _fillRow to add custom
        # columns and the table is currently sorted by one of those columns. In this the expectation is
        # the derived class will be handling working out the post sort row index.
        return sortItem.row() if sortItem else row

# TODO: The label used for widgets should reflect if dead space selection is enabled or not
class _StartFinishSelectWidget(QtWidgets.QWidget):
    selectionChanged = QtCore.pyqtSignal()
    showHexRequested = QtCore.pyqtSignal(travellermap.HexPosition)

    # TODO: I suspect I'll have to leave this as is to avoid users losing the
    # previously selected start/finish world
    _StateVersion = '_StartFinishWorldsSelectWidget_v1'

    def __init__(self):
        super().__init__()

        self._startWorldWidget = gui.WorldSelectToolWidget(text=None)
        self._startWorldWidget.enableShowHexButton(True)
        self._startWorldWidget.enableShowInfoButton(True)
        self._startWorldWidget.selectionChanged.connect(self.selectionChanged.emit)
        self._startWorldWidget.showHex.connect(self._handleShowHex)

        self._finishWorldWidget = gui.WorldSelectToolWidget(text=None)
        self._finishWorldWidget.enableShowHexButton(True)
        self._finishWorldWidget.enableShowInfoButton(True)
        self._finishWorldWidget.selectionChanged.connect(self.selectionChanged.emit)
        self._finishWorldWidget.showHex.connect(self._handleShowHex)

        widgetLayout = gui.FormLayoutEx()
        widgetLayout.setContentsMargins(0, 0, 0, 0)
        widgetLayout.addRow('Start World:', self._startWorldWidget)
        widgetLayout.addRow('Finish World:', self._finishWorldWidget)

        self.setLayout(widgetLayout)

    def startHex(self) -> typing.Optional[travellermap.HexPosition]:
        return self._startWorldWidget.selectedHex()

    def finishHex(self) -> typing.Optional[travellermap.HexPosition]:
        return self._finishWorldWidget.selectedHex()

    def hexes(self) -> typing.Tuple[
            typing.Optional[travellermap.HexPosition],
            typing.Optional[travellermap.HexPosition]
            ]:
        return (self.startHex(), self.finishHex())

    def setStartHex(
            self,
            pos: typing.Optional[travellermap.HexPosition]
            ) -> None:
        self._startWorldWidget.setSelectedHex(pos=pos)

    def setFinishHex(
            self,
            pos: typing.Optional[travellermap.HexPosition]
            ) -> None:
        self._finishWorldWidget.setSelectedHex(pos=pos)

    def setHexes(
            self,
            startPos: typing.Optional[travellermap.HexPosition],
            finishPos: typing.Optional[travellermap.HexPosition]
            ) -> None:
        selectionChanged = False

        # Block signals so we can manually generate a single selection changed
        # event.
        with gui.SignalBlocker(widget=self._startWorldWidget) and \
                gui.SignalBlocker(widget=self._finishWorldWidget):
            if startPos != self._startWorldWidget.selectedHex():
                self._startWorldWidget.setSelectedHex(pos=startPos)
                selectionChanged = True

            if finishPos != self._finishWorldWidget.selectedHex():
                self._finishWorldWidget.setSelectedHex(pos=finishPos)
                selectionChanged = True

        if selectionChanged:
            self.selectionChanged.emit()

    def enableDeadSpaceSelection(self, enable: bool) -> None:
        self._startWorldWidget.enableDeadSpaceSelection(enable=enable)
        self._finishWorldWidget.enableDeadSpaceSelection(enable=enable)

    def isDeadSpaceSelectionEnabled(self) -> bool:
        return self._startWorldWidget.isDeadSpaceSelectionEnabled()

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(_StartFinishSelectWidget._StateVersion)

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
        if version != _StartFinishSelectWidget._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore _StartFinishHexSelectWidget state (Incorrect version)')
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

    def _handleShowHex(
            self,
            pos: typing.Optional[travellermap.HexPosition]
            ) -> None:
        if pos:
            self.showHexRequested.emit(pos)

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
            self._selectStartFinishWidget.restoreState(storedValue)

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

        # TODO: The names of some of the elements here use world
        # when they actually refer to hex tables. I think I'll need
        # to leave them as is if I want backward compatibility
        self._settings.setValue('StartFinishWorldsState', self._selectStartFinishWidget.saveState())
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

    # TODO: Does this style function still make sense now I've switched to better shared
    # controls
    def configureControls(
            self,
            startPos: typing.Optional[travellermap.HexPosition] = None,
            finishPos: typing.Optional[travellermap.HexPosition] = None,
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

        if (startPos != None) and (finishPos != None):
            # Set the start and finish worlds at the same time. If either of them
            # is None then the current world will be kept. This is done so that the
            # user doesn't get prompted twice about clearing the waypoint and avoid
            # worlds if both the start and finish worlds have changed
            self._selectStartFinishWidget.setHexes(
                startPos=startPos,
                finishPos=finishPos)
        elif startPos != None:
            self._selectStartFinishWidget.setStartHex(pos=startPos)
        elif finishPos != None:
            self._selectStartFinishWidget.setFinishHex(pos=finishPos)

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
        self._selectStartFinishWidget = _StartFinishSelectWidget()
        self._selectStartFinishWidget.selectionChanged.connect(self._startFinishChanged)
        self._selectStartFinishWidget.showHexRequested.connect(self._showHexInTravellerMap)

        groupLayout = QtWidgets.QVBoxLayout()
        groupLayout.addWidget(self._selectStartFinishWidget)

        # TODO: Not sure what this should be called, possibly Locations, Nodes or Hexes instead of worlds
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

        # TODO: I need a handler that is triggered when the checked state changes.
        # With it doing the following
        # - Turning on/off dead space selection on the start/finish widget
        # - Turning on/off dead space selection on the map widget
        # - If dead space selection is turned off, remove dead space from waypoint widget
        # - If dead space selection is turned off, remove dead space from avoid widget
        #   - I'm not sure about this, could just leave it in as it will have no effect
        #     I think this will basically mean dead space selection will always be on for
        #     the avoid list
        # - Possibly clearing any current jump route, will need to see what other
        #   config controls do when they change
        self._deadSpaceRoutingCheckBox = gui.SharedDeadSpaceRoutingCheckBox()
        self._deadSpaceRoutingCheckBox.setEnabled(
            self._fuelBasedRoutingCheckBox.isChecked())

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
        leftLayout.addRow('Dead Space Routing:', self._deadSpaceRoutingCheckBox)
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
        self._waypointWorldTable = gui.WaypointTable()
        self._waypointWorldsWidget = gui.HexTableManagerWidget(
            hexTable=self._waypointWorldTable,
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
        self._avoidWorldsWidget = gui.HexTableManagerWidget(
            allowHexCallback=self._allowAvoidHex,
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

        self._jumpRouteDisplayModeTabBar = gui.HexTableTabBar()
        self._jumpRouteDisplayModeTabBar.currentChanged.connect(self._updateJumpRouteTableColumns)

        self._jumpRouteTable = gui.HexTable()
        self._jumpRouteTable.setVisibleColumns(self._jumpRouteColumns())
        self._jumpRouteTable.setMinimumHeight(100) # TODO: Should this have interface scaling applied?
        self._jumpRouteTable.setSortingEnabled(False) # Disable sorting as we only want to display in jump route order
        self._jumpRouteTable.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self._jumpRouteTable.customContextMenuRequested.connect(self._showJumpRouteTableContextMenu)

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

    def _startFinishChanged(self) -> None:
        # Always clear the current jump route as it's invalid if the finish world changes
        self._clearJumpRoute()

        self._updateTravellerMapOverlays()

        # When a new route is calculated for the first time after a start/finish world has been
        # changed, the Traveller Map widget should be zoomed to show the route as it may be
        # displaying a completely different location. After the first route has been calculated
        # for this start/finish pair the view is left as is as it's assumed the user is doing
        # something like adding a waypoint world
        self._zoomToJumpRoute = True

    def _waypointsTableDisplayModeChanged(self, displayMode: gui.HexTableTabBar.DisplayMode) -> None:
        columns = None
        if displayMode == gui.HexTableTabBar.DisplayMode.AllColumns:
            columns = gui.WaypointTable.AllColumns
        elif displayMode == gui.HexTableTabBar.DisplayMode.SystemColumns:
            columns = gui.WaypointTable.SystemColumns
        elif displayMode == gui.HexTableTabBar.DisplayMode.UWPColumns:
            columns = gui.WaypointTable.UWPColumns
        elif displayMode == gui.HexTableTabBar.DisplayMode.EconomicsColumns:
            columns = gui.WaypointTable.EconomicsColumns
        elif displayMode == gui.HexTableTabBar.DisplayMode.CultureColumns:
            columns = gui.WaypointTable.CultureColumns
        elif displayMode == gui.HexTableTabBar.DisplayMode.RefuellingColumns:
            columns = gui.WaypointTable.RefuellingColumns
        else:
            assert(False) # I missed a case
        self._waypointWorldsWidget.setVisibleColumns(columns)

    def _calculateJumpRoute(self) -> None:
        if self._jumpRouteJob:
            # A trade option job is already running so cancel it
            self._jumpRouteJob.cancel()
            return

        self._clearJumpRoute()

        startPos, finishPos = self._selectStartFinishWidget.hexes()
        if not startPos or not finishPos:
            if not startPos and not finishPos:
                message = 'You need to select a start and finish world before calculating a route.'
            elif not startPos:
                message = 'You need to select a start world before calculating a route.'
            else:
                message = 'You need to select a finish world before calculating a route.'
            gui.MessageBoxEx.information(parent=self, text=message)
            return

        # Fuel based route calculation
        pitCostCalculator = None
        deadSpaceRouting = False
        if self._fuelBasedRoutingCheckBox.isChecked():
            deadSpaceRouting = self._deadSpaceRoutingCheckBox.isChecked()

            useAnomalyRefuelling = self._useAnomalyRefuellingCheckBox.isChecked()
            pitCostCalculator = logic.PitStopCostCalculator(
                refuellingStrategy=self._refuellingStrategyComboBox.currentEnum(),
                useFuelCaches=self._useFuelCachesCheckBox.isChecked(),
                anomalyFuelCost=self._anomalyFuelCostSpinBox.value() if useAnomalyRefuelling else None,
                anomalyBerthingCost=self._anomalyBerthingCostSpinBox.value() if useAnomalyRefuelling else None,
                rules=app.Config.instance().rules())

            # Highlight cases where start world or waypoints don't support the
            # refuelling strategy
            # TODO: This should also highlight the case where the ship has no fuel
            # and the start world is dead space
            startWorld = traveller.WorldManager.instance().worldByPosition(pos=startPos)
            if startWorld and not pitCostCalculator.refuellingType(world=startWorld):
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
            for waypointPos in self._waypointWorldsWidget.hexes():
                waypointWorld = traveller.WorldManager.instance().worldByPosition(pos=waypointPos)
                if waypointWorld and not pitCostCalculator.refuellingType(world=waypointWorld):
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

        hexSequence = [startPos]
        hexSequence.extend(self._waypointWorldsWidget.hexes())
        hexSequence.append(finishPos)

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
            avoidHexes=self._avoidWorldsWidget.hexes(),
            avoidFilters=self._avoidWorldsFilterWidget.filters(),
            avoidFilterLogic=self._avoidWorldsFilterWidget.filterLogic())

        try:
            self._jumpRouteJob = jobs.RoutePlannerJob(
                parent=self,
                hexSequence=hexSequence,
                shipTonnage=self._shipTonnageSpinBox.value(),
                shipJumpRating=self._shipJumpRatingSpinBox.value(),
                shipFuelCapacity=self._shipFuelCapacitySpinBox.value(),
                shipCurrentFuel=self._shipCurrentFuelSpinBox.value(),
                shipFuelPerParsec=self._shipFuelPerParsecSpinBox.value(),
                jumpCostCalculator=jumpCostCalculator,
                pitCostCalculator=pitCostCalculator,
                hexFilter=hexFilter,
                useDeadSpace=deadSpaceRouting,
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
            startPos, finishPos = self._selectStartFinishWidget.hexes()
            startString = traveller.WorldManager.instance().canonicalHexName(pos=startPos)
            finishString = traveller.WorldManager.instance().canonicalHexName(pos=finishPos)
            message = f'Failed to calculate jump route between {startString} and {finishString}'
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

    def _updateJumpRouteTableColumns(self, index: int) -> None:
        self._jumpRouteTable.setVisibleColumns(self._jumpRouteColumns())

    def _jumpRouteColumns(self) -> typing.List[gui.HexTable.ColumnType]:
        displayMode = self._jumpRouteDisplayModeTabBar.currentDisplayMode()
        if displayMode == gui.HexTableTabBar.DisplayMode.AllColumns:
            return gui.HexTable.AllColumns
        elif displayMode == gui.HexTableTabBar.DisplayMode.SystemColumns:
            return gui.HexTable.SystemColumns
        elif displayMode == gui.HexTableTabBar.DisplayMode.UWPColumns:
            return gui.HexTable.UWPColumns
        elif displayMode == gui.HexTableTabBar.DisplayMode.EconomicsColumns:
            return gui.HexTable.EconomicsColumns
        elif displayMode == gui.HexTableTabBar.DisplayMode.CultureColumns:
            return gui.HexTable.CultureColumns
        elif displayMode == gui.HexTableTabBar.DisplayMode.RefuellingColumns:
            return gui.HexTable.RefuellingColumns
        else:
            assert(False) # I missed a case

    # TODO: This will need updated to account for the fact the "jump worlds table"
    # will actually be dealing with nodes so some options might not apply (e.g.
    # show world details only makes sense if a world node is selected)
    # TODO: Remember to update the text strings
    def _showJumpRouteTableContextMenu(self, position: QtCore.QPoint) -> None:
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
                callback=lambda: self._showWorldsInTravellerMap(self._jumpRouteTable.selectedHexes()),
                enabled=self._jumpRouteTable.hasSelection()
            ),
            gui.MenuItem(
                text='Show All Worlds in Traveller Map',
                callback=lambda: self._showWorldsInTravellerMap(self._jumpRouteTable.hexes()),
                enabled=not self._jumpRouteTable.isEmpty()
            )
        ]

        gui.displayMenu(
            self,
            menuItems,
            self._jumpRouteTable.viewport().mapToGlobal(position)
        )

    # TODO: This at a minimum will need some rewording as waypoints could be hexes
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
                callback=lambda: self._showWorldsInTravellerMap(self._refuellingPlanTable.selectedHexes()),
                enabled=self._refuellingPlanTable.hasSelection()
            ),
            gui.MenuItem(
                text='Show All Worlds in Traveller Map',
                callback=lambda: self._showWorldsInTravellerMap(self._refuellingPlanTable.hexes()),
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
            pos: typing.Optional[travellermap.HexPosition]
            ) -> None:
        clickedWorld = None
        try:
            if pos:
                clickedWorld = traveller.WorldManager.instance().worldByPosition(pos=pos)
        except Exception as ex:
            absoluteX, absoluteY = pos.absolute()
            logging.warning(
                f'An exception occurred while resolving hex {absoluteX}, {absoluteY} to a world for context menu',
                exc_info=ex)
            # Continue as if no world was clicked

        startPos, finishPos = self._selectStartFinishWidget.hexes()
        menuItems = []

        action = QtWidgets.QAction('Recalculate Jump Route', self)
        menuItems.append(action)
        action.triggered.connect(self._calculateJumpRoute)
        action.setEnabled(startPos != None and finishPos != None)

        action = QtWidgets.QAction('Show World Details...', self)
        menuItems.append(action)
        action.triggered.connect(lambda: self._showWorldDetails([clickedWorld]))
        action.setEnabled(clickedWorld != None)

        menu = QtWidgets.QMenu('Start/Finish Worlds', self)
        menuItems.append(menu)
        action = menu.addAction('Set Start World')
        action.triggered.connect(lambda: self._selectStartFinishWidget.setStartHex(pos=pos))
        action.setEnabled(pos != None)
        action = menu.addAction('Set Finish World')
        action.triggered.connect(lambda: self._selectStartFinishWidget.setFinishHex(pos=pos))
        action.setEnabled(pos != None)
        action = menu.addAction('Swap Start && Finish Worlds')
        action.triggered.connect(
            lambda: self._selectStartFinishWidget.setHexes(startPos=finishPos, finishPos=startPos))
        action.setEnabled(startPos != None and finishPos != None)

        menu = QtWidgets.QMenu('Waypoint Worlds', self)
        menuItems.append(menu)
        action = menu.addAction('Add World')
        action.triggered.connect(lambda: self._waypointWorldsWidget.addHex(pos=pos))
        action.setEnabled(pos != None and not self._waypointWorldsWidget.containsHex(pos=pos))
        action = menu.addAction('Remove World')
        action.triggered.connect(lambda: self._waypointWorldsWidget.removeHex(pos=pos))
        action.setEnabled(pos != None and self._waypointWorldsWidget.containsHex(pos=pos))

        menu = QtWidgets.QMenu('Avoid Worlds', self)
        menuItems.append(menu)
        action = menu.addAction('Add World')
        action.triggered.connect(lambda: self._avoidWorldsWidget.addHex(pos=pos))
        action.setEnabled(pos != None and not self._avoidWorldsWidget.containsHex(pos=pos))
        action = menu.addAction('Remove World')
        action.triggered.connect(lambda: self._avoidWorldsWidget.removeHex(pos=pos))
        action.setEnabled(pos != None and self._avoidWorldsWidget.containsHex(pos=pos))

        menu = QtWidgets.QMenu('Zoom To', self)
        menuItems.append(menu)
        action = menu.addAction('Start World')
        action.triggered.connect(lambda: self._showHexInTravellerMap(pos=startPos))
        action.setEnabled(startPos != None)
        action = menu.addAction('Finish World')
        action.triggered.connect(lambda: self._showHexInTravellerMap(pos=finishPos))
        action.setEnabled(finishPos != None)
        action = menu.addAction('Jump Route')
        action.triggered.connect(lambda: self._showJumpRouteInTravellerMap())
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
            pos: typing.Optional[travellermap.HexPosition]
            ) -> typing.Optional[str]:
        if not pos:
            return None

        if not self._jumpRoute:
            startPos, finishPos = self._selectStartFinishWidget.hexes()
            if (startPos and pos == startPos) and (finishPos and pos == finishPos):
                return gui.createStringToolTip('<nobr>Start &amp; Finish Hex</nobr>', escape=False)
            elif (startPos and pos == startPos):
                return gui.createStringToolTip('<nobr>Start Hex</nobr>', escape=False)
            elif (finishPos and pos == finishPos):
                return gui.createStringToolTip('<nobr>Finish Hex</nobr>', escape=False)
            elif self._waypointWorldsWidget.containsHex(pos):
                return gui.createStringToolTip('<nobr>Waypoint Hex</nobr>', escape=False)
            elif self._avoidWorldsWidget.containsHex(pos):
                return gui.createStringToolTip('<nobr>Avoid Hex</nobr>', escape=False)
            return None

        jumpNodes: typing.Dict[int, typing.Optional[logic.PitStop]] = {}
        for nodeIndex in range(self._jumpRoute.nodeCount()):
            if self._jumpRoute.hex(nodeIndex) == pos:
                jumpNodes[nodeIndex] = None

        if self._routeLogistics:
            refuellingPlan = self._routeLogistics.refuellingPlan()
            if refuellingPlan:
                for pitStop in refuellingPlan:
                    if pitStop.jumpIndex() in jumpNodes:
                        jumpNodes[pitStop.jumpIndex()] = pitStop

        toolTip = ''
        for nodeIndex, pitStop in jumpNodes.items():
            toolTip += f'<li><nobr>Route Node: {nodeIndex + 1}</nobr></li>'

            if nodeIndex != 0:
                toolTip += '<li><nobr>Route Distance: {} parsecs</nobr></li>'.format(
                    self._jumpRoute.nodeParsecs(index=nodeIndex))

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
            if self._waypointWorldsWidget.containsHex(pos):
                return gui.createStringToolTip('<nobr>Waypoint Hex</nobr>', escape=False)

            # Check for the world being an avoid world. This is done last as
            # start/finish/waypoint worlds can be on the avoid list but we
            # don't want to flag them as such here
            if self._avoidWorldsWidget.containsHex(pos):
                return gui.createStringToolTip('<nobr>Avoid Hex</nobr>', escape=False)

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

    def _showHexInTravellerMap(
            self,
            pos: travellermap.HexPosition
            ) -> None:
        try:
            self._resultsDisplayModeTabView.setCurrentWidget(self._travellerMapWidget)
            self._travellerMapWidget.centerOnHex(
                pos=pos,
                clearOverlays=False,
                highlightHex=False)
        except Exception as ex:
            message = 'Failed to show hex in Traveller Map'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)

    def _showJumpRouteInTravellerMap(self) -> None:
        if not self._jumpRoute:
            return

        self._showWorldsInTravellerMap(
            positions=[pos for pos, _ in self._jumpRoute])

    def _showWorldsInTravellerMap(
            self,
            positions: typing.Iterable[travellermap.HexPosition]
            ) -> None:
        try:
            self._resultsDisplayModeTabView.setCurrentWidget(self._travellerMapWidget)
            self._travellerMapWidget.centerOnHexes(
                positions=positions,
                clearOverlays=False,
                highlightHexes=False)
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

        startPos, finishPos = self._selectStartFinishWidget.hexes()
        jumpRating = self._shipJumpRatingSpinBox.value()

        if showJumpRatingOverlay:
            isDarkMapStyle = travellermap.isDarkStyle(
                style=app.Config.instance().mapStyle())
            colour = self._JumpRatingOverlayDarkStyleColour \
                if isDarkMapStyle else \
                self._JumpRatingOverlayLightStyleColour
            handle = self._travellerMapWidget.createHexRadiusOverlayGroup(
                center=startPos,
                radius=jumpRating,
                lineColour=colour,
                lineWidth=self._JumpRatingOverlayLineWidth)
            self._jumpOverlayHandles.add(handle)

        if showWorldTaggingOverlay:
            try:
                worlds = traveller.WorldManager.instance().worldsInArea(
                    center=startPos,
                    searchRadius=jumpRating)
            except Exception as ex:
                startString = traveller.WorldManager.instance().canonicalHexName(pos=startPos)
                logging.warning(
                    f'An exception occurred while finding worlds reachable from {startString}',
                    exc_info=ex)
                return

            taggedWorlds = []
            for world in worlds:
                worldPos = world.hexPosition()
                if (worldPos == startPos) or (worldPos == finishPos):
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

        startPos, finishPos = self._selectStartFinishWidget.hexes()
        if startPos:
            self._travellerMapWidget.highlightHex(
                pos=startPos,
                colour='#00FF00',
                radius=0.5)
        if finishPos:
            self._travellerMapWidget.highlightHex(
                pos=finishPos,
                colour='#00FF00',
                radius=0.5)

        waypointHexes = self._waypointWorldsWidget.hexes()
        if waypointHexes:
            self._travellerMapWidget.highlightHexes(
                positions=waypointHexes,
                colour='#0066FF',
                radius=0.3)

        filteredAvoidHexes = []
        for pos in self._avoidWorldsWidget.hexes():
            if (pos != startPos) and (pos != finishPos) and (pos not in waypointHexes):
                filteredAvoidHexes.append(pos)
        if filteredAvoidHexes:
            self._travellerMapWidget.highlightHexes(
                positions=filteredAvoidHexes,
                colour='#FF0000',
                radius=0.3)

        if self._jumpRoute:
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
        self._deadSpaceRoutingCheckBox.setEnabled(fuelBasedRouting)
        self._refuellingStrategyComboBox.setEnabled(fuelBasedRouting)
        self._useFuelCachesCheckBox.setEnabled(fuelBasedRouting)
        self._useAnomalyRefuellingCheckBox.setEnabled(fuelBasedRouting)
        self._anomalyFuelCostSpinBox.setEnabled(fuelBasedRouting and anomalyRefuelling)
        self._anomalyBerthingCostSpinBox.setEnabled(fuelBasedRouting and anomalyRefuelling)

    def _allowAvoidHex(self, pos: travellermap.HexPosition) -> bool:
        if self._avoidWorldsWidget.containsHex(pos):
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

        self._jumpRouteTable.setHexes(
            positions=[pos for pos, _ in self._jumpRoute])
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
                startHex, _ = self._jumpRoute.startNode()
                finishHex, _ = self._jumpRoute.finishNode()
                startString = traveller.WorldManager.instance().canonicalHexName(pos=startHex)
                finishString = traveller.WorldManager.instance().canonicalHexName(pos=finishHex)
                message = 'Failed to calculate jump route logistics between {start} and {finish}'.format(
                    start=startString,
                    finish=finishString)
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
        if not self._jumpRoute or self._jumpRoute.nodeCount() < 1:
            return None

        # The jump route planner will reduce sequences of the same waypoint world to a single
        # stop at that world. In order to match the waypoints to the jump route we need to
        # remove such sequences. This includes sequences where the worlds at the start of the
        # waypoint list match the start world and/or worlds at the end of the list match the
        # finish world.

        waypoints: typing.List[typing.Tuple[
            travellermap.HexPosition,
            bool # Mandatory berthing required
            ]] = []

        startHex, startWorld = self._jumpRoute.startNode()
        waypoints.append((
            startHex,
            startWorld and self._includeStartWorldBerthingCheckBox.isChecked()))

        for row in range(self._waypointWorldTable.rowCount()):
            waypoints.append((
                self._waypointWorldTable.hex(row),
                self._waypointWorldTable.isBerthingChecked(row)))

        finishHex, finishWorld = self._jumpRoute.finishNode()
        waypoints.append((
            finishHex,
            finishWorld and self._includeFinishWorldBerthingCheckBox.isChecked()))

        requiredBerthingIndices = set()

        for waypointIndex in range(len(waypoints) - 1, 0, -1):
            if waypoints[waypointIndex][0] == waypoints[waypointIndex - 1][0]:
                # This is a sequence of the same hex so remove the last instance in the sequence
                if waypoints[waypointIndex][1]:
                    # Berthing is required if any of the instances of the world in the sequence are
                    # marked as requiring berthing
                    # TODO: This doesn't feel right, should probably check it
                    waypoints[waypointIndex - 1] = waypoints[waypointIndex]
                waypoints.pop(waypointIndex)

        waypointIndex = 0
        for jumpIndex in range(self._jumpRoute.nodeCount()):
            if self._jumpRoute.hex(jumpIndex) == waypoints[waypointIndex][0]:
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
