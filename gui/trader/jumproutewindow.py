import app
import common
import enum
import gui
import jobs
import logging
import logic
import traveller
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
        elif world.isFuelCache():
            text += ' (Fuel Cache)'
        else:
            text += ' (Unknown)'
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
    else:
        return 'Unknown Berthing'

class _WorldFilter(object):
    def __init__(
            self,
            refuellingStrategy: logic.RefuellingStrategy,
            avoidWorlds: typing.List[traveller.World],
            avoidFilters: typing.List[traveller.World],
            avoidFilterLogic: logic.FilterLogic
            ) -> None:
        self._refuellingStrategy = refuellingStrategy

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
    def filter(self, world : traveller.World) -> bool:
        if not logic.selectRefuellingType(world, self._refuellingStrategy):
            # Filter out worlds that don't match the refuelling strategy.
            return False

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
        self._pitStopMap: typing.Dict[int, logic.PitStop] = {}

    def setRoute(
            self,
            jumpRoute: typing.Iterable[traveller.World],
            pitStops: typing.Optional[typing.Iterable[logic.PitStop]]
            ) -> None:
        self.removeAllRows()

        # Add pit stops before worlds so the map can be looked up when inserting rows
        if pitStops:
            for pitStop in pitStops:
                self._pitStopMap[pitStop.jumpIndex()] = pitStop

        self.addWorlds(worlds=jumpRoute)

    def pitStopAt(self, position: QtCore.QPoint) -> typing.Optional[logic.PitStop]:
        item = self.itemAt(position)
        if not item:
            return None
        if item.row() not in self._pitStopMap:
            return None
        return self._pitStopMap[item.row()]

    def removeAllRows(self) -> None:
        super().removeAllRows()
        self._pitStopMap.clear()

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

            for column in range(self.columnCount()):
                columnType = self.columnHeader(column)
                pitStop = None
                if row in self._pitStopMap:
                    pitStop: logic.PitStop = self._pitStopMap[row]

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

    def _createToolTip(self, item: QtWidgets.QTableWidgetItem) -> typing.Optional[str]:
        columnType = self.columnHeader(item.column())
        if columnType == _RefuellingPlanTableColumnType.RefuellingType:
            if item.row() not in self._pitStopMap:
                return None
            pitStop = self._pitStopMap[item.row()]
            if pitStop.isRefuellingStrategyOverridden():
                return gui.createStringToolTip('Refuelling strategy was overridden')

        return super()._createToolTip(item=item)

class _StartFinishWorldsSelectWidget(QtWidgets.QWidget):
    selectionChanged = QtCore.pyqtSignal()

    _StateVersion = '_StartFinishWorldsSelectWidget_v1'

    def __init__(self):
        super().__init__()

        self._startWorldWidget = gui.WorldSelectWidget(
            labelText='Start',
            noSelectionText='Select a start world to continue')
        self._startWorldWidget.selectionChanged.connect(self.selectionChanged.emit)

        self._finishWorldWidget = gui.WorldSelectWidget(
            labelText='Finish',
            noSelectionText='Select a finish world to continue')
        self._finishWorldWidget.selectionChanged.connect(self.selectionChanged.emit)

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._startWorldWidget)
        layout.addWidget(self._finishWorldWidget)

        self.setLayout(layout)

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
            logging.debug(f'Failed to restore _StartFinishWorldSelectWidget state (Incorrect version)')
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

class JumpRouteWindow(gui.WindowWidget):
    def __init__(self) -> None:
        super().__init__(
            title='Jump Route Planner',
            configSection='JumpRouteWindow')

        self._jumpRouteJob = None
        self._jumpRoute = None
        self._routeLogistics = None
        self._zoomToJumpRoute = False

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

        self._settings.endGroup()

        self._updateTravellerMapOverlay()

    def saveSettings(self) -> None:
        self._settings.beginGroup(self._configSection)

        self._settings.setValue('StartFinishWorldsState', self._startFinishWorldsWidget.saveState())
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

        self._settings.endGroup()

        super().saveSettings()

    def configureControls(
            self,
            startWorld: typing.Optional[traveller.World] = None,
            finishWorld: typing.Optional[traveller.World] = None,
            shipTonnage: typing.Optional[int] = None,
            shipJumpRating: typing.Optional[int] = None,
            shipFuelCapacity: typing.Optional[int] = None,
            shipCurrentFuel: typing.Optional[int] = None,
            routeOptimisation: typing.Optional[logic.RouteOptimisation] = None,
            perJumpOverheads: typing.Optional[int] = None,
            refuellingStrategy: typing.Optional[logic.RefuellingStrategy] = None,
            refuellingStrategyOptional: typing.Optional[bool] = None,
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
            self._shipCurrentFuelSpinBox.setValue(int(shipCurrentFuel))
        if refuellingStrategy != None:
            self._refuellingStrategyComboBox.setCurrentEnum(refuellingStrategy)
        if refuellingStrategyOptional != None:
            self._refuellingStrategyOptionalCheckBox.setChecked(refuellingStrategyOptional)
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
        self._startFinishWorldsWidget = _StartFinishWorldsSelectWidget()
        self._startFinishWorldsWidget.selectionChanged.connect(self._startFinishWorldsChanged)

        groupLayout = QtWidgets.QVBoxLayout()
        groupLayout.addWidget(self._startFinishWorldsWidget)

        self._jumpWorldsGroupBox = QtWidgets.QGroupBox('Jump Worlds')
        self._jumpWorldsGroupBox.setLayout(groupLayout)

    def _setupConfigurationControls(self) -> None:
        # Left hand column of options
        self._shipTonnageSpinBox = gui.SharedShipTonnageSpinBox()
        self._shipJumpRatingSpinBox = gui.SharedJumpRatingSpinBox()
        self._shipFuelCapacitySpinBox = gui.SharedFuelCapacitySpinBox()
        self._shipCurrentFuelSpinBox = gui.SharedCurrentFuelSpinBox()

        leftLayout = gui.FormLayoutEx()
        leftLayout.setContentsMargins(0, 0, 0, 0)
        leftLayout.addRow('Ship Total Tonnage:', self._shipTonnageSpinBox)
        leftLayout.addRow('Ship Jump Rating:', self._shipJumpRatingSpinBox)
        leftLayout.addRow('Ship Fuel Capacity:', self._shipFuelCapacitySpinBox)
        leftLayout.addRow('Ship Current Fuel:', self._shipCurrentFuelSpinBox)

        # Center column of options
        self._refuellingStrategyComboBox = gui.SharedRefuellingStrategyComboBox()
        self._refuellingStrategyOptionalCheckBox = gui.SharedRefuellingStrategyOptionalCheckBox()
        self._routeOptimisationComboBox = gui.SharedRouteOptimisationComboBox()
        self._perJumpOverheadsSpinBox = gui.SharedJumpOverheadSpinBox()
        self._includeStartWorldBerthingCheckBox = gui.SharedIncludeStartBerthingCheckBox()
        self._includeFinishWorldBerthingCheckBox = gui.SharedIncludeFinishBerthingCheckBox()

        rightLayout = gui.FormLayoutEx()
        rightLayout.setContentsMargins(0, 0, 0, 0)
        rightLayout.addRow('Route Optimisation:', self._routeOptimisationComboBox)
        rightLayout.addRow('Refuelling Strategy:', self._refuellingStrategyComboBox)
        rightLayout.addRow('Strategy Optional:', self._refuellingStrategyOptionalCheckBox)
        rightLayout.addRow('Per Jump Overheads:', self._perJumpOverheadsSpinBox)
        rightLayout.addRow('Start World Berthing:', self._includeStartWorldBerthingCheckBox)
        rightLayout.addRow('Finish World Berthing:', self._includeFinishWorldBerthingCheckBox)

        optionsLayout = QtWidgets.QHBoxLayout()
        optionsLayout.addLayout(leftLayout)
        optionsLayout.addLayout(rightLayout)
        optionsLayout.addStretch()

        self._configurationGroupBox = QtWidgets.QGroupBox('Configuration')
        self._configurationGroupBox.setLayout(optionsLayout)

    def _setupWaypointWorldsControls(self) -> None:
        self._waypointWorldTable = gui.WorldBerthingTable()
        self._waypointWorldsWidget = gui.WorldTableManagerWidget(
            worldTable=self._waypointWorldTable,
            allowWorldCallback=self._allowWaypointWorld,
            isOrderedList=True, # List order determines order waypoints are to be travelled to
            showSelectInTravellerMapButton=False, # The windows Traveller Map widget should be used to select worlds
            showAddNearbyWorldsButton=False) # Adding nearby worlds doesn't make sense for waypoints
        self._waypointWorldsWidget.contentChanged.connect(self._updateTravellerMapOverlay)
        self._waypointWorldsWidget.enableDisplayModeChangedEvent(enable=True)
        self._waypointWorldsWidget.displayModeChanged.connect(self._waypointsTableDisplayModeChanged)
        self._waypointWorldsWidget.enableShowInTravellerMapEvent(enable=True)
        self._waypointWorldsWidget.showInTravellerMap.connect(self._showWorldsInTravellerMap)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self._waypointWorldsWidget)

        self._waypointWorldsGroupBox = QtWidgets.QGroupBox('Waypoint Worlds')
        self._waypointWorldsGroupBox.setLayout(layout)

    def _setupAvoidWorldsControls(self) -> None:
        self._avoidWorldsWidget = gui.WorldTableManagerWidget(
            allowWorldCallback=self._allowAvoidWorld,
            showSelectInTravellerMapButton=False) # The windows Traveller Map widget should be used to select worlds
        self._avoidWorldsWidget.contentChanged.connect(self._updateTravellerMapOverlay)
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

        self._processedWorldLabel = gui.PrefixLabel(prefix='Processed Worlds: ')
        self._jumpCountLabel = gui.PrefixLabel(prefix='Jumps: ')
        self._routeLengthLabel = gui.PrefixLabel(prefix='Parsecs: ')

        self._avgRouteCostLabel = gui.PrefixLabel(prefix='Average Cost: ')
        self._minRouteCostLabel = gui.PrefixLabel(prefix='Minimum Cost: ')
        self._maxRouteCostLabel = gui.PrefixLabel(prefix='Maximum Cost: ')

        labelLayout = QtWidgets.QHBoxLayout()
        labelLayout.setContentsMargins(0, 0, 0, 0)
        labelLayout.addWidget(self._processedWorldLabel)
        labelLayout.addWidget(self._jumpCountLabel)
        labelLayout.addWidget(self._routeLengthLabel)
        labelLayout.addWidget(self._avgRouteCostLabel)
        labelLayout.addWidget(self._minRouteCostLabel)
        labelLayout.addWidget(self._maxRouteCostLabel)

        self._jumpRouteDisplayModeTabBar = gui.WorldTableTabBar()
        self._jumpRouteDisplayModeTabBar.currentChanged.connect(self._updateWorldTableColumns)

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

        self._resultsDisplayModeTabView = gui.TabWidgetEx()
        self._resultsDisplayModeTabView.setTabPosition(QtWidgets.QTabWidget.TabPosition.East)
        self._resultsDisplayModeTabView.addTab(jumpRouteWidget, 'Jump Route')
        self._resultsDisplayModeTabView.addTab(self._refuellingPlanTable, 'Refuelling Plan')
        self._resultsDisplayModeTabView.addTab(self._travellerMapWidget, 'Traveller Map')

        self._exportRouteButton = QtWidgets.QPushButton('Export Jump Route...')
        self._exportRouteButton.clicked.connect(self._exportJumpRoute)

        routeLayout = QtWidgets.QVBoxLayout()
        routeLayout.addWidget(self._calculateRouteButton)
        routeLayout.addLayout(labelLayout)
        routeLayout.addWidget(self._resultsDisplayModeTabView)
        routeLayout.addWidget(self._exportRouteButton)

        self._plannedRouteGroupBox = QtWidgets.QGroupBox('Jump Route')
        self._plannedRouteGroupBox.setLayout(routeLayout)

    def _clearJumpRoute(self):
        self._jumpRouteTable.removeAllRows()
        self._refuellingPlanTable.removeAllRows()
        self._processedWorldLabel.clear()
        self._jumpCountLabel.clear()
        self._routeLengthLabel.clear()
        self._avgRouteCostLabel.clear()
        self._minRouteCostLabel.clear()
        self._maxRouteCostLabel.clear()
        self._jumpRoute = None
        self._routeLogistics = None
        self._updateTravellerMapOverlay()

    def _startFinishWorldsChanged(self) -> None:
        if self._waypointWorldsWidget.worldCount() > 0:
            answer = gui.MessageBoxEx.question(
                parent=self,
                text='Clear waypoint worlds?')
            if answer == QtWidgets.QMessageBox.StandardButton.Yes:
                self._waypointWorldsWidget.removeAllWorlds()

        if self._avoidWorldsWidget.worldCount() > 0:
            answer = gui.MessageBoxEx.question(
                parent=self,
                text='Clear avoid worlds?')
            if answer == QtWidgets.QMessageBox.StandardButton.Yes:
                self._avoidWorldsWidget.removeAllWorlds()
            else:
                # Make sure the start and finish worlds aren't on the avoid list
                startWorld, finishWorld = self._startFinishWorldsWidget.worlds()
                if startWorld:
                    self._avoidWorldsWidget.removeWorld(world=startWorld)
                if finishWorld:
                    self._avoidWorldsWidget.removeWorld(world=finishWorld)

        # Always clear the current jump route as it's invalid if the finish world changes
        self._clearJumpRoute()

        self._updateTravellerMapOverlay()

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

    def _calculateJumpRoute(self) -> None:
        if self._jumpRouteJob:
            # A trade option job is already running so cancel it
            self._jumpRouteJob.cancel()
            return

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

        fuelForMaxJump = traveller.calculateFuelRequiredForJump(
            jumpDistance=self._shipJumpRatingSpinBox.value(),
            shipTonnage=self._shipTonnageSpinBox.value())
        if self._shipFuelCapacitySpinBox.value() < fuelForMaxJump.value():
            gui.MessageBoxEx.information(
                parent=self,
                text=f'With a fuel capacity of {self._shipFuelCapacitySpinBox.value()} tons your ship can\'t carry ' + \
                f'the {fuelForMaxJump.value()} tons required for Jump-{self._shipJumpRatingSpinBox.value()}')
            return

        self._clearJumpRoute()

        worldList = [startWorld]
        worldList.extend(self._waypointWorldsWidget.worlds())
        worldList.append(finishWorld)

        routeOptimisation = self._routeOptimisationComboBox.currentEnum()
        if routeOptimisation == logic.RouteOptimisation.ShortestDistance:
            costCalculator = logic.ShortestDistanceCostCalculator()
        elif routeOptimisation == logic.RouteOptimisation.ShortestTime:
            costCalculator = logic.ShortestTimeCostCalculator()
        elif routeOptimisation == logic.RouteOptimisation.LowestCost:
            costCalculator = logic.CheapestRouteCostCalculator(
                shipTonnage=self._shipTonnageSpinBox.value(),
                refuellingStrategy=self._refuellingStrategyComboBox.currentEnum(),
                perJumpOverheads=self._perJumpOverheadsSpinBox.value())
        else:
            assert(False) # I've missed an enum

        worldFilter = _WorldFilter(
            refuellingStrategy=self._refuellingStrategyComboBox.currentEnum(),
            avoidWorlds=self._avoidWorldsWidget.worlds(),
            avoidFilters=self._avoidWorldsFilterWidget.filters(),
            avoidFilterLogic=self._avoidWorldsFilterWidget.filterLogic())

        try:
            self._jumpRouteJob = jobs.RoutePlannerJob(
                parent=self,
                worldSequence=worldList,
                jumpRating=self._shipJumpRatingSpinBox.value(),
                jumpCostCallback=costCalculator.calculate,
                worldFilterCallback=worldFilter.filter,
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

    def _jumpRouteJobProgressUpdate(self, worldCount: int) -> None:
        self._processedWorldLabel.setNum(worldCount)

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

    def _showTravellerMapContextMenu(
            self,
            sectorHex: str
            ) -> None:
        clickedWorld = None
        try:
            if sectorHex:
                clickedWorld = traveller.WorldManager.instance().world(sectorHex=sectorHex)
        except Exception as ex:
            logging.warning(f'Exception occurred while resolving sector hex "{sectorHex}" to world', exc_info=ex)

        startWorld, finishWorld = self._startFinishWorldsWidget.worlds()

        menuItems = [
            gui.MenuItem(
                text='Add World to Waypoints',
                callback=lambda: self._waypointWorldsWidget.addWorld(clickedWorld),
                enabled=clickedWorld != None and not self._waypointWorldsWidget.containsWorld(clickedWorld)
            ),
            gui.MenuItem(
                text='Remove World from Waypoints',
                callback=lambda: self._waypointWorldsWidget.removeWorld(clickedWorld),
                enabled=clickedWorld != None and self._waypointWorldsWidget.containsWorld(clickedWorld)
            ),
            None, # Separator
            gui.MenuItem(
                text='Add World to Avoid Worlds',
                callback=lambda: self._avoidWorldsWidget.addWorld(clickedWorld),
                enabled=clickedWorld != None and not self._avoidWorldsWidget.containsWorld(clickedWorld)
            ),
            gui.MenuItem(
                text='Remove World from Avoid Worlds',
                callback=lambda: self._avoidWorldsWidget.removeWorld(clickedWorld),
                enabled=clickedWorld != None and self._avoidWorldsWidget.containsWorld(clickedWorld)
            ),
            None, # Separator
            gui.MenuItem(
                text='Use World as Start World',
                callback=lambda: self._startFinishWorldsWidget.setStartWorld(clickedWorld),
                enabled=clickedWorld != None
            ),
            gui.MenuItem(
                text='Use World as Finish World',
                callback=lambda: self._startFinishWorldsWidget.setFinishWorld(clickedWorld),
                enabled=clickedWorld != None
            ),
            None, # Separator
            gui.MenuItem(
                text='Recalculate Jump Route',
                callback=self._calculateJumpRoute,
                enabled=True
            ),
            None, # Separator
            gui.MenuItem(
                text='Zoom to Start World',
                callback=lambda: self._showWorldInTravellerMap(startWorld),
                enabled=startWorld != None
            ),
            gui.MenuItem(
                text='Zoom to Finish World',
                callback=lambda: self._showWorldInTravellerMap(finishWorld),
                enabled=finishWorld != None
            ),
            gui.MenuItem(
                text='Zoom to Jump Route',
                callback=lambda: self._showWorldsInTravellerMap(self._jumpRoute),
                enabled=self._jumpRoute != None
            ),
            None, # Separator
            gui.MenuItem(
                text='Show World Details...',
                callback=lambda: self._showWorldDetails([clickedWorld]),
                enabled=clickedWorld != None
            ),
            None, # Separator
        ]

        sectionMenu = QtWidgets.QMenu('Traveller Map', self)
        sectionMenu.addActions(self._travellerMapWidget.actions())
        sectionAction = QtWidgets.QAction('Traveller Map')
        sectionAction.setMenu(sectionMenu)
        menuItems.append(sectionAction)

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

        if self._avoidWorldsWidget.containsWorld(hoverWorld):
            return gui.createStringToolTip('<nobr>Avoid World</nobr>', escape=False)

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
            return None

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
            if self._waypointWorldsWidget.containsWorld(hoverWorld):
                return gui.createStringToolTip('<nobr>Waypoint World</nobr>', escape=False)
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
            self,
            'Save File',
            QtCore.QDir.homePath() + '/route.json',
            'JSON Files(*.json)')
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

    def _updateTravellerMapOverlay(self) -> None:
        self._travellerMapWidget.clearOverlays()

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

        self._travellerMapWidget.highlightWorlds(
            worlds=self._waypointWorldsWidget.worlds(),
            colour='#0066FF',
            radius=0.3)

        self._travellerMapWidget.highlightWorlds(
            worlds=self._avoidWorldsWidget.worlds(),
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

    def _enableDisableControls(self) -> None:
        # Disable configuration controls while jump route job is running
        disable = self._jumpRouteJob != None
        self._jumpWorldsGroupBox.setDisabled(disable)
        self._configurationGroupBox.setDisabled(disable)
        self._waypointWorldsGroupBox.setDisabled(disable)
        self._avoidWorldsGroupBox.setDisabled(disable)

    def _selectWorld(self) -> typing.Optional[traveller.World]:
        dlg = gui.WorldSearchDialog()
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return None
        return dlg.world()

    def _allowWaypointWorld(self, world: traveller.World) -> bool:
        if self._avoidWorldsWidget.containsWorld(world):
            gui.MessageBoxEx.information(
                parent=self,
                text=f'{world.name(includeSubsector=True)} can\'t be added as a waypoint as it\'s on the avoid list')
            return False
        return True

    def _allowAvoidWorld(self, world: traveller.World) -> bool:
        if self._avoidWorldsWidget.containsWorld(world):
            # Silently ignore worlds that are already in the table
            return False
        if world == self._startFinishWorldsWidget.startWorld():
            gui.MessageBoxEx.information(
                parent=self,
                text=f'{world.name(includeSubsector=True)} can\'t be added to the avoid list as it\'s the start world')
            return False
        if world == self._startFinishWorldsWidget.finishWorld():
            gui.MessageBoxEx.information(
                parent=self,
                text=f'{world.name(includeSubsector=True)} can\'t be added to the avoid list as it\'s the finish world')
            return False
        if self._waypointWorldsWidget.containsWorld(world):
            gui.MessageBoxEx.information(
                parent=self,
                text=f'{world.name(includeSubsector=True)} can\'t be added to the avoid list as it\'s a waypoint')
            return
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

        self._jumpRouteTable.addWorlds(worlds=self._jumpRoute)
        self._jumpCountLabel.setNum(self._jumpRoute.jumpCount())
        self._routeLengthLabel.setNum(self._jumpRoute.totalParsecs())

        try:
            self._routeLogistics = logic.calculateRouteLogistics(
                jumpRoute=self._jumpRoute,
                shipTonnage=self._shipTonnageSpinBox.value(),
                shipFuelCapacity=self._shipFuelCapacitySpinBox.value(),
                shipStartingFuel=self._shipCurrentFuelSpinBox.value(),
                perJumpOverheads=self._perJumpOverheadsSpinBox.value(),
                refuellingStrategy=self._refuellingStrategyComboBox.currentEnum(),
                refuellingStrategyOptional=self._refuellingStrategyOptionalCheckBox.isChecked(),
                requiredBerthingIndices=self._generateRequiredBerthingIndices(),
                includeLogisticsCosts=True) # Always include logistics costs
            if not self._routeLogistics:
                gui.MessageBoxEx.information(
                    parent=self,
                    text='Unable to calculate logistics for jump route')
            elif self._routeLogistics.isRefuellingStrategyOverridden():
                gui.MessageBoxEx.information(
                    parent=self,
                    text='In order to calculate a refuelling plan for the jump route it\nwas necessary to override the selected refuelling strategy')
        except Exception as ex:
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
            self._refuellingPlanTable.setRoute(
                jumpRoute=self._jumpRoute,
                pitStops=self._routeLogistics.refuellingPlan())
            routeCost = self._routeLogistics.totalCosts()
            self._avgRouteCostLabel.setText('Cr' + common.formatNumber(routeCost.averageCaseValue()))
            self._minRouteCostLabel.setText('Cr' + common.formatNumber(routeCost.bestCaseValue()))
            self._maxRouteCostLabel.setText('Cr' + common.formatNumber(routeCost.worstCaseValue()))

        self._updateTravellerMapOverlay()

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
            title=self.windowTitle(),
            html=_WelcomeMessage,
            noShowAgainId='JumpRouteWelcome')
        message.exec()