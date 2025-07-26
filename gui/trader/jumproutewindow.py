import app
import common
import enum
import gui
import jobs
import logging
import logic
import os
import traveller
import travellermap
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

_WelcomeMessage = """
    <html>
    <p>The Jump Route Planner allows you to create complex jump routes between worlds. It also has
    experimental features to generate refuelling plans for the route and estimate the logistics
    costs based on average, worst and best case dice rolls.</p>
    <p>Jump route calculations are based on the logic used by Traveller Map, so should be compatible
    with most Traveller rule systems. The logistics cost calculations use Mongoose Traveller rules,
    so compatibility with other rule systems will vary. If you're not using Mongoose Traveller rules,
    cost values can simply be ignored as they don't affect the generated route (unless lowest cost
    route optimisation is used).</p>
    <p>Waypoint worlds can be added to create a multipoint route. This includes the creation of
    circular routes.<p>
    <p>Avoid worlds can be added to, as the name suggests, avoid specific world. This can either
    be done by specifying specific worlds or by adding filters which allow worlds to be avoided
    based on their attributes (e.g. avoid worlds that have specific allegiances if you've made some
    enemies or worlds with an imperial bases or a law level over 5 if you're trying to lie low).</p>
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
            avoidFilterLogic: logic.FilterLogic,
            rules: traveller.Rules,
            tagging: logic.WorldTagging
            ) -> None:
        self._avoidHexes = set(avoidHexes) if avoidHexes else None

        if avoidFilters:
            self._avoidFilter = logic.WorldSearch()
            self._avoidFilter.setFilterLogic(filterLogic=avoidFilterLogic)
            self._avoidFilter.setFilters(filters=avoidFilters)
        else:
            self._avoidFilter = None

        self._rules = traveller.Rules(rules)
        self._tagging = logic.WorldTagging(tagging)

    # IMPORTANT: This will be called from the route planner job thread
    def match(
            self,
            hex: travellermap.HexPosition,
            world: typing.Optional[traveller.World]
            ) -> bool:
        if self._avoidHexes and hex in self._avoidHexes:
            # Filter out worlds on the avoid list
            return False

        if self._avoidFilter and world:
            # Filter out worlds that MATCH the avoid filter
            return not self._avoidFilter.checkWorld(
                world=world,
                rules=self._rules,
                tagging=self._tagging)

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
        gui.HexTable.ColumnType.Subsector,
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
            milieu: travellermap.Milieu,
            rules: traveller.Rules,
            outcomeColours: app.OutcomeColours,
            worldTagging: typing.Optional[logic.WorldTagging] = None,
            taggingColours: typing.Optional[app.TaggingColours] = None,
            columns: typing.Iterable[typing.Union[_RefuellingPlanTableColumnType, gui.HexTable.ColumnType]] = AllColumns
            ) -> None:
        super().__init__(
            milieu=milieu,
            rules=rules,
            worldTagging=worldTagging,
            taggingColours=taggingColours,
            columns=columns)

        self._outcomeColours = app.OutcomeColours(outcomeColours)
        self._pitStops: typing.List[logic.PitStop] = []

        self.setSortingEnabled(False)

    def outcomeColours(self) -> app.OutcomeColours:
        return app.OutcomeColours(self._outcomeColours)

    def setOutcomeColours(self, colours: app.OutcomeColours) -> None:
        if colours == self._outcomeColours:
            return
        self._outcomeColours = app.OutcomeColours(colours)
        self._syncContent()

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
            self.addHex(hex=pitStop.hex())

    def pitStopAt(self, y: int) -> typing.Optional[logic.PitStop]:
        row = self.rowAt(y)
        if row < 0 or row >= len(self._pitStops):
            return None
        return self._pitStops[row]

    def _fillRow(
            self,
            row: int,
            hex: travellermap.HexPosition
            ) -> int:
        world = traveller.WorldManager.instance().worldByPosition(
            milieu=self._milieu,
            hex=hex)

        # Disable sorting while updating a row. We don't want any sorting to occur
        # until all columns have been updated
        sortingEnabled = self.isSortingEnabled()
        self.setSortingEnabled(False)

        try:
            super()._fillRow(row, hex)

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
                    tableItem = gui.FormattedNumberTableWidgetItem(
                        pitStop.berthingCost().averageCaseValue() if pitStop and pitStop.berthingCost() else None)
                    tableItem.setBackground(QtGui.QColor(self._outcomeColours.colour(
                        outcome=logic.RollOutcome.AverageCase)))
                elif columnType == _RefuellingPlanTableColumnType.WorstCaseBerthingCost:
                    tableItem = gui.FormattedNumberTableWidgetItem(
                        pitStop.berthingCost().worstCaseValue() if pitStop and pitStop.berthingCost() else None)
                    tableItem.setBackground(QtGui.QColor(self._outcomeColours.colour(
                        outcome=logic.RollOutcome.WorstCase)))
                elif columnType == _RefuellingPlanTableColumnType.BestCaseBerthingCost:
                    tableItem = gui.FormattedNumberTableWidgetItem(
                        pitStop.berthingCost().bestCaseValue() if pitStop and pitStop.berthingCost() else None)
                    tableItem.setBackground(QtGui.QColor(self._outcomeColours.colour(
                        outcome=logic.RollOutcome.BestCase)))

                if tableItem:
                    self.setItem(row, column, tableItem)
                    tableItem.setData(QtCore.Qt.ItemDataRole.UserRole, (hex, world))

            # Take note of the sort column item so we can determine which row index after the table
            # has been sorted
            sortItem = self.item(row, self.horizontalHeader().sortIndicatorSection())
        finally:
            self.setSortingEnabled(sortingEnabled)

        # If we don't have a sort item we assume a derived class has overridden _fillRow to add custom
        # columns and the table is currently sorted by one of those columns. In this the expectation is
        # the derived class will be handling working out the post sort row index.
        return sortItem.row() if sortItem else row

class _StartFinishSelectWidget(QtWidgets.QWidget):
    selectionChanged = QtCore.pyqtSignal()
    showHexRequested = QtCore.pyqtSignal(travellermap.HexPosition)

    # The state version doesn't match the current class name for backwards
    # compatibility. The class name was changed when adding dead space routing
    # but changing the state version would have meant the user would loose
    # any previous configured start/finish world when they upgrade
    _StateVersion = '_StartFinishWorldsSelectWidget_v1'

    def __init__(
            self,
            milieu: travellermap.Milieu,
            rules: traveller.Rules,
            mapStyle: travellermap.Style,
            mapOptions: typing.Iterable[travellermap.Option],
            mapRendering: app.MapRendering,
            mapAnimations: bool,
            worldTagging: typing.Optional[logic.WorldTagging] = None,
            taggingColours: typing.Optional[app.TaggingColours] = None,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self._startWidget = gui.HexSelectToolWidget(
            milieu=milieu,
            rules=rules,
            mapStyle=mapStyle,
            mapOptions=mapOptions,
            mapRendering=mapRendering,
            mapAnimations=mapAnimations,
            worldTagging=worldTagging,
            taggingColours=taggingColours)
        self._startWidget.enableShowHexButton(True)
        self._startWidget.enableShowInfoButton(True)
        self._startWidget.selectionChanged.connect(self.selectionChanged.emit)
        self._startWidget.showHex.connect(self._handleShowHex)

        self._finishWidget = gui.HexSelectToolWidget(
            milieu=milieu,
            rules=rules,
            mapStyle=mapStyle,
            mapOptions=mapOptions,
            mapRendering=mapRendering,
            mapAnimations=mapAnimations,
            worldTagging=worldTagging,
            taggingColours=taggingColours)
        self._finishWidget.enableShowHexButton(True)
        self._finishWidget.enableShowInfoButton(True)
        self._finishWidget.selectionChanged.connect(self.selectionChanged.emit)
        self._finishWidget.showHex.connect(self._handleShowHex)

        widgetLayout = gui.FormLayoutEx()
        widgetLayout.setContentsMargins(0, 0, 0, 0)
        widgetLayout.addRow('Start:', self._startWidget)
        widgetLayout.addRow('Finish:', self._finishWidget)

        self.setLayout(widgetLayout)

    def setMilieu(self, milieu: travellermap.Milieu) -> None:
        self._startWidget.setMilieu(milieu=milieu)
        self._finishWidget.setMilieu(milieu=milieu)

    def setRules(self, rules: traveller.Rules) -> None:
        self._startWidget.setRules(rules=rules)
        self._finishWidget.setRules(rules=rules)

    def setMapStyle(self, style: travellermap.Style) -> None:
        self._startWidget.setMapStyle(style=style)
        self._finishWidget.setMapStyle(style=style)

    def setMapOptions(self, options: typing.Iterable[travellermap.Option]) -> None:
        self._startWidget.setMapOptions(options=options)
        self._finishWidget.setMapOptions(options=options)

    def setMapRendering(self, rendering: app.MapRendering) -> None:
        self._startWidget.setMapRendering(rendering=rendering)
        self._finishWidget.setMapRendering(rendering=rendering)

    def setMapAnimations(self, enabled: bool) -> None:
        self._startWidget.setMapAnimations(enabled=enabled)
        self._finishWidget.setMapAnimations(enabled=enabled)

    def setWorldTagging(self, tagging: logic.WorldTagging) -> None:
        self._startWidget.setWorldTagging(tagging=tagging)
        self._finishWidget.setWorldTagging(tagging=tagging)

    def setTaggingColours(self, colours: app.TaggingColours) -> None:
        self._startWidget.setTaggingColours(colours=colours)
        self._finishWidget.setTaggingColours(colours=colours)

    def startHex(self) -> typing.Optional[travellermap.HexPosition]:
        return self._startWidget.selectedHex()

    def finishHex(self) -> typing.Optional[travellermap.HexPosition]:
        return self._finishWidget.selectedHex()

    def hexes(self) -> typing.Tuple[
            typing.Optional[travellermap.HexPosition],
            typing.Optional[travellermap.HexPosition]
            ]:
        return (self.startHex(), self.finishHex())

    def setStartHex(
            self,
            hex: typing.Optional[travellermap.HexPosition]
            ) -> None:
        self._startWidget.setSelectedHex(hex=hex)

    def setFinishHex(
            self,
            hex: typing.Optional[travellermap.HexPosition]
            ) -> None:
        self._finishWidget.setSelectedHex(hex=hex)

    def setHexes(
            self,
            startHex: typing.Optional[travellermap.HexPosition],
            finishHex: typing.Optional[travellermap.HexPosition]
            ) -> None:
        selectionChanged = False

        # Block signals so we can manually generate a single selection changed
        # event.
        with gui.SignalBlocker(widget=self._startWidget) and \
                gui.SignalBlocker(widget=self._finishWidget):
            if startHex != self._startWidget.selectedHex():
                self._startWidget.setSelectedHex(hex=startHex)
                selectionChanged = True

            if finishHex != self._finishWidget.selectedHex():
                self._finishWidget.setSelectedHex(hex=finishHex)
                selectionChanged = True

        if selectionChanged:
            self.selectionChanged.emit()

    def enableDeadSpaceSelection(self, enable: bool) -> None:
        self._startWidget.enableDeadSpaceSelection(enable=enable)
        self._finishWidget.enableDeadSpaceSelection(enable=enable)

    def isDeadSpaceSelectionEnabled(self) -> bool:
        return self._startWidget.isDeadSpaceSelectionEnabled()

    def setHexTooltipProvider(
            self,
            provider: typing.Optional[gui.HexTooltipProvider]
            ) -> None:
        self._startWidget.setHexTooltipProvider(provider=provider)
        self._finishWidget.setHexTooltipProvider(provider=provider)

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(_StartFinishSelectWidget._StateVersion)

        childState = self._startWidget.saveState()
        stream.writeUInt32(childState.count() if childState else 0)
        if childState:
            stream.writeRawData(childState.data())

        childState = self._finishWidget.saveState()
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
            if not self._startWidget.restoreState(childState):
                return False

        count = stream.readUInt32()
        if count > 0:
            childState = QtCore.QByteArray(stream.readRawData(count))
            if not self._finishWidget.restoreState(childState):
                return False

        return True

    def _handleShowHex(
            self,
            hex: typing.Optional[travellermap.HexPosition]
            ) -> None:
        if hex:
            self.showHexRequested.emit(hex)

class _ImportJumpRouteDialog(gui.DialogEx):
    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(
            title='Import Jump Route',
            configSection='ImportJumpRouteDialog',
            parent=parent)

        self._filePathLineEdit = gui.LineEditEx()
        self._filePathBrowseButton = QtWidgets.QPushButton('Browse...')
        self._filePathBrowseButton.clicked.connect(self._filePathBrowseClicked)
        filePathLayout = QtWidgets.QHBoxLayout()
        filePathLayout.setContentsMargins(0, 0, 0, 0)
        filePathLayout.addWidget(self._filePathLineEdit)
        filePathLayout.addWidget(self._filePathBrowseButton)

        self._includeLogisticsCheckBox = gui.CheckBoxEx()
        self._includeLogisticsCheckBox.setChecked(True)
        self._replaceStartFinishCheckBox = gui.CheckBoxEx()
        self._replaceStartFinishCheckBox.setChecked(False)
        self._replaceWaypointsCheckBox = gui.CheckBoxEx()
        self._replaceWaypointsCheckBox.setChecked(False)
        optionsLayout = gui.FormLayoutEx()
        optionsLayout.addRow('Include Logistics', self._includeLogisticsCheckBox)
        optionsLayout.addRow('Replace Current Start/Finish', self._replaceStartFinishCheckBox)
        optionsLayout.addRow('Replace Current Waypoints', self._replaceWaypointsCheckBox)

        self._importButton = QtWidgets.QPushButton('Import')
        self._importButton.setDefault(True)
        self._importButton.clicked.connect(self.accept)

        self._cancelButton = QtWidgets.QPushButton('Cancel')
        self._cancelButton.clicked.connect(self.reject)

        buttonLayout = QtWidgets.QHBoxLayout()
        buttonLayout.setContentsMargins(0, 0, 0, 0)
        buttonLayout.addStretch()
        buttonLayout.addWidget(self._importButton)
        buttonLayout.addWidget(self._cancelButton)

        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(filePathLayout)
        layout.addLayout(optionsLayout)
        layout.addLayout(buttonLayout)

        self.setLayout(layout)

        sizeHint = self.sizeHint()
        self.setFixedHeight(sizeHint.height())
        self.resize(QtCore.QSize(
            int(400 * gui.interfaceScale()),
            sizeHint.height()))

    def filePath(self) -> str:
        return self._filePathLineEdit.text()

    def includeLogistics(self) -> bool:
        return self._includeLogisticsCheckBox.isChecked()

    def replaceStartFinish(self) -> bool:
        return self._replaceStartFinishCheckBox.isChecked()

    def replaceWaypoints(self) -> bool:
        return self._replaceWaypointsCheckBox.isChecked()

    # NOTE: There is no saveSettings as settings are only saved when accept is triggered (i.e. not
    # if the user cancels the dialog)
    def loadSettings(self) -> None:
        super().loadSettings()

        self._settings.beginGroup(self._configSection)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='FilePath',
            type=str)
        if storedValue:
            self._filePathLineEdit.setText(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='IncludeLogisticsCheckBoxState',
            type=QtCore.QByteArray)
        if storedValue:
            self._includeLogisticsCheckBox.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='ReplaceStartFinishCheckBoxState',
            type=QtCore.QByteArray)
        if storedValue:
            self._replaceStartFinishCheckBox.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='ReplaceWaypointsCheckBoxState',
            type=QtCore.QByteArray)
        if storedValue:
            self._replaceWaypointsCheckBox.restoreState(storedValue)

        self._settings.endGroup()

    def accept(self) -> None:
        self._settings.beginGroup(self._configSection)
        self._settings.setValue('FilePath', self._filePathLineEdit.text())
        self._settings.setValue('IncludeLogisticsCheckBoxState', self._includeLogisticsCheckBox.saveState())
        self._settings.setValue('ReplaceStartFinishCheckBoxState', self._replaceStartFinishCheckBox.saveState())
        self._settings.setValue('ReplaceWaypointsCheckBoxState', self._replaceWaypointsCheckBox.saveState())
        self._settings.endGroup()

        return super().accept()

    def _filePathBrowseClicked(self) -> None:
        path = self._filePathLineEdit.text()
        initialDir = QtCore.QDir.homePath()
        if path and os.path.isfile(path):
            initialDir = os.path.dirname(path)

        path, _ = gui.FileDialogEx.getOpenFileName(
            parent=self,
            caption='Jump Route File',
            directory=initialDir,
            filter=f'{gui.JSONFileFilter};;{gui.AllFileFilter}')
        if not path:
            return None # User cancelled

        self._filePathLineEdit.setText(path)

class _ExportJumpRouteDialog(gui.DialogEx):
    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(
            title='Export Jump Route',
            configSection='ExportJumpRouteDialog',
            parent=parent)

        self._filePathLineEdit = gui.LineEditEx()
        self._filePathBrowseButton = QtWidgets.QPushButton('Browse...')
        self._filePathBrowseButton.clicked.connect(self._filePathBrowseClicked)
        filePathLayout = QtWidgets.QHBoxLayout()
        filePathLayout.setContentsMargins(0, 0, 0, 0)
        filePathLayout.addWidget(self._filePathLineEdit)
        filePathLayout.addWidget(self._filePathBrowseButton)

        self._includeLogisticsCheckBox = gui.CheckBoxEx()
        self._includeLogisticsCheckBox.setChecked(True)
        self._includeCalculationsCheckBox = gui.CheckBoxEx()
        self._includeCalculationsCheckBox.setChecked(False)
        optionsLayout = gui.FormLayoutEx()
        optionsLayout.addRow('Include Logistics', self._includeLogisticsCheckBox)
        optionsLayout.addRow('Include Calculations', self._includeCalculationsCheckBox)

        self._exportButton = QtWidgets.QPushButton('Export')
        self._exportButton.setDefault(True)
        self._exportButton.clicked.connect(self.accept)

        self._cancelButton = QtWidgets.QPushButton('Cancel')
        self._cancelButton.clicked.connect(self.reject)

        buttonLayout = QtWidgets.QHBoxLayout()
        buttonLayout.setContentsMargins(0, 0, 0, 0)
        buttonLayout.addStretch()
        buttonLayout.addWidget(self._exportButton)
        buttonLayout.addWidget(self._cancelButton)

        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(filePathLayout)
        layout.addLayout(optionsLayout)
        layout.addLayout(buttonLayout)

        self.setLayout(layout)

        sizeHint = self.sizeHint()
        self.setFixedHeight(sizeHint.height())
        self.resize(QtCore.QSize(
            int(400 * gui.interfaceScale()),
            sizeHint.height()))

    def filePath(self) -> str:
        return self._filePathLineEdit.text()

    def includeLogistics(self) -> bool:
        return self._includeLogisticsCheckBox.isChecked()

    def includeCalculations(self) -> bool:
        return self._includeCalculationsCheckBox.isChecked()

    # NOTE: There is no saveSettings as settings are only saved when accept is triggered (i.e. not
    # if the user cancels the dialog)
    def loadSettings(self) -> None:
        super().loadSettings()

        self._settings.beginGroup(self._configSection)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='FilePath',
            type=str)
        if storedValue:
            self._filePathLineEdit.setText(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='IncludeLogisticsCheckBoxState',
            type=QtCore.QByteArray)
        if storedValue:
            self._includeLogisticsCheckBox.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='IncludeCalculationsCheckBoxState',
            type=QtCore.QByteArray)
        if storedValue:
            self._includeCalculationsCheckBox.restoreState(storedValue)

        self._settings.endGroup()

    def accept(self) -> None:
        self._settings.beginGroup(self._configSection)
        self._settings.setValue('FilePath', self._filePathLineEdit.text())
        self._settings.setValue('IncludeLogisticsCheckBoxState', self._includeLogisticsCheckBox.saveState())
        self._settings.setValue('IncludeCalculationsCheckBoxState', self._includeCalculationsCheckBox.saveState())
        self._settings.endGroup()

        return super().accept()

    def _filePathBrowseClicked(self) -> None:
        path = self._filePathLineEdit.text()
        initialDir = QtCore.QDir.homePath()
        if path and os.path.isfile(path):
            initialDir = os.path.dirname(path)

        path, _ = gui.FileDialogEx.getSaveFileName(
            parent=self,
            caption='Jump Route File',
            directory=initialDir,
            filter=f'{gui.JSONFileFilter};;{gui.AllFileFilter}',
            defaultFileName='route.json')
        if not path:
            return None # User cancelled

        self._filePathLineEdit.setText(path)

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
        self._shouldZoomToNewRoute = False
        self._jumpOverlayHandles = set()

        self._hexTooltipProvider = gui.HexTooltipProvider(
            milieu=app.Config.instance().value(option=app.ConfigOption.Milieu),
            rules=app.Config.instance().value(option=app.ConfigOption.Rules),
            showImages=app.Config.instance().value(option=app.ConfigOption.ShowToolTipImages),
            mapStyle=app.Config.instance().value(option=app.ConfigOption.MapStyle),
            mapOptions=app.Config.instance().value(option=app.ConfigOption.MapOptions),
            worldTagging=app.Config.instance().value(option=app.ConfigOption.WorldTagging),
            taggingColours=app.Config.instance().value(option=app.ConfigOption.TaggingColours))

        self._setupStartFinishControls()
        self._setupConfigurationControls()
        self._setupWaypointControls()
        self._setupAvoidLocationsControls()
        self._setupJumpRouteControls()

        self._tableSplitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        self._tableSplitter.addWidget(self._waypointsGroupBox)
        self._tableSplitter.addWidget(self._avoidLocationsGroupBox)

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
        self._enableDisableControls()

        app.Config.instance().configChanged.connect(self._appConfigChanged)

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
            self._waypointsWidget.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='WaypointWorldTableContent',
            type=QtCore.QByteArray)
        if storedValue:
            self._waypointsWidget.restoreContent(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='AvoidWorldTableState',
            type=QtCore.QByteArray)
        if storedValue:
            self._avoidHexesWidget.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='AvoidWorldTableContent',
            type=QtCore.QByteArray)
        if storedValue:
            self._avoidHexesWidget.restoreContent(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='AvoidFilterTableState',
            type=QtCore.QByteArray)
        if storedValue:
            self._avoidFiltersWidget.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='AvoidFilterTableContent',
            type=QtCore.QByteArray)
        if storedValue:
            self._avoidFiltersWidget.restoreContent(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='AvoidTabBarState',
            type=QtCore.QByteArray)
        if storedValue:
            self._avoidLocationsTabWidget.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='MapWidgetState',
            type=QtCore.QByteArray)
        if storedValue:
            self._mapWidget.restoreState(storedValue)

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

        self._jumpRatingOverlayToggle.setChecked(
            gui.safeLoadSetting(
                settings=self._settings,
                key='ShowJumpRatingOverlay',
                type=bool,
                default=False))

        self._worldTaggingOverlayToggle.setChecked(
            gui.safeLoadSetting(
                settings=self._settings,
                key='ShowWorldTaggingOverlay',
                type=bool,
                default=False))

        self._settings.endGroup()

        self._updateTravellerMapOverlays()

    def saveSettings(self) -> None:
        self._settings.beginGroup(self._configSection)

        # NOTE: The name of the settings for the waypoint and avoid hex tables
        # states are *WorldTableState for backwards compatibility. The tables
        # were switched to using hexes when adding support for dead space
        # routing but changing the setting name would mean users would lose
        # any previously configured waypoints and avoid worlds
        self._settings.setValue('StartFinishWorldsState', self._selectStartFinishWidget.saveState())
        self._settings.setValue('ConfigurationTabBarState', self._configurationStack.saveState())
        self._settings.setValue('WaypointWorldTableState', self._waypointsWidget.saveState())
        self._settings.setValue('WaypointWorldTableContent', self._waypointsWidget.saveContent())
        self._settings.setValue('AvoidWorldTableState', self._avoidHexesWidget.saveState())
        self._settings.setValue('AvoidWorldTableContent', self._avoidHexesWidget.saveContent())
        self._settings.setValue('AvoidFilterTableState', self._avoidFiltersWidget.saveState())
        self._settings.setValue('AvoidFilterTableContent', self._avoidFiltersWidget.saveContent())
        self._settings.setValue('AvoidTabBarState', self._avoidLocationsTabWidget.saveState())
        self._settings.setValue('MapWidgetState', self._mapWidget.saveState())
        self._settings.setValue('ResultsDisplayModeState', self._resultsDisplayModeTabView.saveState())
        self._settings.setValue('JumpRouteTableState', self._jumpRouteTable.saveState())
        self._settings.setValue('JumpRouteDisplayModeState', self._jumpRouteDisplayModeTabBar.saveState())
        self._settings.setValue('RefuellingPlanTableState', self._refuellingPlanTable.saveState())
        self._settings.setValue('TableSplitterState', self._tableSplitter.saveState())
        self._settings.setValue('MainSplitterState', self._mainSplitter.saveState())
        self._settings.setValue('ShowJumpRatingOverlay', self._jumpRatingOverlayToggle.isChecked())
        self._settings.setValue('ShowWorldTaggingOverlay', self._worldTaggingOverlayToggle.isChecked())

        self._settings.endGroup()

        super().saveSettings()

    def setRoute(
            self,
            route: logic.JumpRoute,
            logistics: typing.Optional[logic.RouteLogistics]
            ) -> None:
        if self._jumpRouteJob:
            raise RuntimeError('Unable to set jump route while a jump route job is in progress')

        self._jumpRoute = route
        self._jumpRouteTable.setHexes(hexes=self._jumpRoute.nodes())

        self._routeLogistics = logistics
        self._refuellingPlanTable.setPitStops(
            pitStops=self._routeLogistics.refuellingPlan() if self._routeLogistics else None)

        self._selectStartFinishWidget.setHexes(
            startHex=route.startNode(),
            finishHex=route.finishNode())
        self._waypointsTable.removeAllRows()

        self._updateRouteLabels()
        self._updateTravellerMapOverlays()

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
    # TODO: This can be removed when I finally ditch the web map widget
    def _travellerMapInitFix(self) -> None:
        currentWidget = self._resultsDisplayModeTabView.currentWidget()
        if currentWidget != self._mapWidget:
            size = currentWidget.size()
            self._mapWidget.resize(size)
            self._mapWidget.show()

    def _setupStartFinishControls(self) -> None:
        milieu = app.Config.instance().value(option=app.ConfigOption.Milieu)
        rules = app.Config.instance().value(option=app.ConfigOption.Rules)
        mapStyle = app.Config.instance().value(option=app.ConfigOption.MapStyle)
        mapOptions = app.Config.instance().value(option=app.ConfigOption.MapOptions)
        mapRendering = app.Config.instance().value(option=app.ConfigOption.MapRendering)
        mapAnimations = app.Config.instance().value(option=app.ConfigOption.MapAnimations)
        worldTagging = app.Config.instance().value(option=app.ConfigOption.WorldTagging)
        taggingColours = app.Config.instance().value(option=app.ConfigOption.TaggingColours)
        routingType = app.Config.instance().value(option=app.ConfigOption.RoutingType)

        self._selectStartFinishWidget = _StartFinishSelectWidget(
            milieu=milieu,
            rules=rules,
            mapStyle=mapStyle,
            mapOptions=mapOptions,
            mapRendering=mapRendering,
            mapAnimations=mapAnimations,
            worldTagging=worldTagging,
            taggingColours=taggingColours)
        self._selectStartFinishWidget.setHexTooltipProvider(
            provider=self._hexTooltipProvider)
        self._selectStartFinishWidget.enableDeadSpaceSelection(
            enable=routingType is logic.RoutingType.DeadSpace)
        self._selectStartFinishWidget.selectionChanged.connect(self._startFinishChanged)
        self._selectStartFinishWidget.showHexRequested.connect(self._showHexOnMap)

        groupLayout = QtWidgets.QVBoxLayout()
        groupLayout.addWidget(self._selectStartFinishWidget)

        self._jumpWorldsGroupBox = QtWidgets.QGroupBox('Start/Finish')
        self._jumpWorldsGroupBox.setLayout(groupLayout)

    def _setupConfigurationControls(self) -> None:
        #
        # Route Configuration
        #
        self._routingTypeComboBox = gui.RoutingTypeComboBox(
            value=app.Config.instance().value(option=app.ConfigOption.RoutingType))
        self._routingTypeComboBox.currentEnumChanged.connect(self._routingTypeChanged)

        self._routeOptimisationComboBox = gui.RouteOptimisationComboBox(
            value=app.Config.instance().value(option=app.ConfigOption.RouteOptimisation))
        self._routeOptimisationComboBox.currentEnumChanged.connect(self._routeOptimisationChanged)

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

        self._perJumpOverheadsSpinBox = gui.JumpOverheadsSpinBox(
            value=app.Config.instance().value(option=app.ConfigOption.PerJumpOverhead))
        self._perJumpOverheadsSpinBox.valueChanged.connect(self._perJumpOverheadsChanged)

        self._includeStartWorldBerthingCheckBox = gui.IncludeStartBerthingCheckBox(
            value=app.Config.instance().value(option=app.ConfigOption.IncludeStartBerthing))
        self._includeStartWorldBerthingCheckBox.stateChanged.connect(self._includeStartWorldBerthingToggled)

        self._includeFinishWorldBerthingCheckBox = gui.IncludeFinishBerthingCheckBox(
            value=app.Config.instance().value(option=app.ConfigOption.IncludeFinishBerthing))
        self._includeFinishWorldBerthingCheckBox.stateChanged.connect(self._includeFinishWorldBerthingToggled)

        leftLayout = gui.FormLayoutEx()
        leftLayout.setContentsMargins(0, 0, 0, 0)
        leftLayout.addRow('Routing Type:', self._routingTypeComboBox)
        leftLayout.addRow('Route Optimisation:', self._routeOptimisationComboBox)
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
            gui.LayoutWrapperWidget(layout=routingLayout),
            'Route')
        self._configurationStack.addTab(
            gui.LayoutWrapperWidget(layout=shipLayout),
            'Ship')

        configurationLayout = QtWidgets.QHBoxLayout()
        configurationLayout.addWidget(self._configurationStack)

        self._configurationGroupBox = QtWidgets.QGroupBox('Configuration')
        self._configurationGroupBox.setLayout(configurationLayout)

    def _setupWaypointControls(self) -> None:
        milieu = app.Config.instance().value(option=app.ConfigOption.Milieu)
        rules = app.Config.instance().value(option=app.ConfigOption.Rules)
        routingType = app.Config.instance().value(option=app.ConfigOption.RoutingType)
        mapStyle = app.Config.instance().value(option=app.ConfigOption.MapStyle)
        mapOptions = app.Config.instance().value(option=app.ConfigOption.MapOptions)
        mapRendering = app.Config.instance().value(option=app.ConfigOption.MapRendering)
        mapAnimations = app.Config.instance().value(option=app.ConfigOption.MapAnimations)
        worldTagging = app.Config.instance().value(option=app.ConfigOption.WorldTagging)
        taggingColours = app.Config.instance().value(option=app.ConfigOption.TaggingColours)

        self._waypointsTable = gui.WaypointTable(
            milieu=milieu,
            rules=rules,
            worldTagging=worldTagging,
            taggingColours=taggingColours)
        self._waypointsWidget = gui.HexTableManagerWidget(
            milieu=milieu,
            rules=rules,
            mapStyle=mapStyle,
            mapOptions=mapOptions,
            mapRendering=mapRendering,
            mapAnimations=mapAnimations,
            worldTagging=worldTagging,
            taggingColours=taggingColours,
            hexTable=self._waypointsTable,
            isOrderedList=True) # List order determines order waypoints are to be travelled to
        self._waypointsWidget.setHexTooltipProvider(
            provider=self._hexTooltipProvider)
        self._waypointsWidget.enableDeadSpace(
            enable=routingType is logic.RoutingType.DeadSpace)
        self._waypointsWidget.contentChanged.connect(self._updateTravellerMapOverlays)
        self._waypointsWidget.enableDisplayModeChangedEvent(enable=True)
        self._waypointsWidget.displayModeChanged.connect(self._waypointsTableDisplayModeChanged)
        self._waypointsWidget.enableShowOnMapEvent(enable=True)
        self._waypointsWidget.showOnMapRequested.connect(self._showHexesOnMap)

        # Override the tables actions for showing selected/all worlds on a popup map
        # window with actions that will show them on the main map for this window
        showSelectionOnMapAction = QtWidgets.QAction('Show Selection on Map...', self)
        showSelectionOnMapAction.setEnabled(False) # No selection
        showSelectionOnMapAction.triggered.connect(self._showWaypointsTableSelectionOnMap)
        self._waypointsWidget.setShowSelectionOnMapAction(showSelectionOnMapAction)

        showContentOnMapAction = QtWidgets.QAction('Show All on Map...', self)
        showContentOnMapAction.setEnabled(False) # No content
        showContentOnMapAction.triggered.connect(self._showWaypointsTableContentOnMap)
        self._waypointsWidget.setShowContentOnMapAction(showContentOnMapAction)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self._waypointsWidget)

        self._waypointsGroupBox = QtWidgets.QGroupBox('Waypoints')
        self._waypointsGroupBox.setLayout(layout)

    def _setupAvoidLocationsControls(self) -> None:
        milieu = app.Config.instance().value(option=app.ConfigOption.Milieu)
        rules = app.Config.instance().value(option=app.ConfigOption.Rules)
        mapStyle = app.Config.instance().value(option=app.ConfigOption.MapStyle)
        mapOptions = app.Config.instance().value(option=app.ConfigOption.MapOptions)
        mapRendering = app.Config.instance().value(option=app.ConfigOption.MapRendering)
        mapAnimations = app.Config.instance().value(option=app.ConfigOption.MapAnimations)
        worldTagging = app.Config.instance().value(option=app.ConfigOption.WorldTagging)
        taggingColours = app.Config.instance().value(option=app.ConfigOption.TaggingColours)

        self._avoidLocationsTabWidget = gui.ItemCountTabWidget()
        self._avoidLocationsTabWidget.setTabPosition(QtWidgets.QTabWidget.TabPosition.West)

        self._avoidHexesWidget = gui.HexTableManagerWidget(
            milieu=milieu,
            rules=rules,
            mapStyle=mapStyle,
            mapOptions=mapOptions,
            mapRendering=mapRendering,
            mapAnimations=mapAnimations,
            worldTagging=worldTagging,
            taggingColours=taggingColours,
            allowHexCallback=self._allowAvoidHex)
        self._avoidHexesWidget.setHexTooltipProvider(
            provider=self._hexTooltipProvider)
        self._avoidHexesWidget.enableDeadSpace(
            enable=True) # Always allow dead space on avoid list
        self._avoidHexesWidget.contentChanged.connect(self._updateTravellerMapOverlays)
        self._avoidHexesWidget.enableShowOnMapEvent(enable=True)
        self._avoidHexesWidget.showOnMapRequested.connect(self._showHexesOnMap)
        self._avoidLocationsTabWidget.addTab(self._avoidHexesWidget, 'Hexes')
        self._avoidLocationsTabWidget.setWidgetItemCount(self._avoidHexesWidget, 0)
        self._avoidHexesWidget.contentChanged.connect(
            lambda: self._avoidLocationsTabWidget.setWidgetItemCount(
                self._avoidHexesWidget,
                self._avoidHexesWidget.rowCount()))

        # Override the tables actions for showing selected/all worlds on a popup map
        # window with actions that will show them on the main map for this window
        showSelectionOnMapAction = QtWidgets.QAction('Show Selection on Map...', self)
        showSelectionOnMapAction.setEnabled(False) # No selection
        showSelectionOnMapAction.triggered.connect(self._showAvoidHexesTableSelectionOnMap)
        self._avoidHexesWidget.setShowSelectionOnMapAction(showSelectionOnMapAction)

        showContentOnMapAction = QtWidgets.QAction('Show All on Map...', self)
        showContentOnMapAction.setEnabled(False) # No content
        showContentOnMapAction.triggered.connect(self._showAvoidHexesTableContentOnMap)
        self._avoidHexesWidget.setShowContentOnMapAction(showContentOnMapAction)

        self._avoidFiltersWidget = gui.WorldFilterTableManagerWidget(
            taggingColours=taggingColours)
        self._avoidLocationsTabWidget.addTab(self._avoidFiltersWidget, 'Filters')
        self._avoidLocationsTabWidget.setWidgetItemCount(self._avoidFiltersWidget, 0)
        self._avoidFiltersWidget.contentChanged.connect(
            lambda: self._avoidLocationsTabWidget.setWidgetItemCount(
                self._avoidFiltersWidget,
                self._avoidFiltersWidget.filterCount()))

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self._avoidLocationsTabWidget)

        self._avoidLocationsGroupBox = QtWidgets.QGroupBox('Avoid Locations')
        self._avoidLocationsGroupBox.setLayout(layout)

    def _setupJumpRouteControls(self) -> None:
        milieu = app.Config.instance().value(
            option=app.ConfigOption.Milieu)
        rules = app.Config.instance().value(
            option=app.ConfigOption.Rules)
        mapStyle = app.Config.instance().value(
            option=app.ConfigOption.MapStyle)
        mapOptions = app.Config.instance().value(
            option=app.ConfigOption.MapOptions)
        mapRendering = app.Config.instance().value(
            option=app.ConfigOption.MapRendering)
        mapAnimations = app.Config.instance().value(
            option=app.ConfigOption.MapAnimations)
        routingType = app.Config.instance().value(
            option=app.ConfigOption.RoutingType)
        outcomeColours = app.Config.instance().value(
            option=app.ConfigOption.OutcomeColours)
        worldTagging = app.Config.instance().value(
            option=app.ConfigOption.WorldTagging)
        taggingColours = app.Config.instance().value(
            option=app.ConfigOption.TaggingColours)

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
        labelLayout.setSpacing(int(15 * gui.interfaceScale()))
        labelLayout.addWidget(self._processedRoutesLabel)
        labelLayout.addWidget(self._jumpCountLabel)
        labelLayout.addWidget(self._routeLengthLabel)
        labelLayout.addWidget(self._avgRouteCostLabel)
        labelLayout.addWidget(self._minRouteCostLabel)
        labelLayout.addWidget(self._maxRouteCostLabel)

        self._jumpRouteDisplayModeTabBar = gui.HexTableTabBar()
        self._jumpRouteDisplayModeTabBar.currentChanged.connect(self._updateJumpRouteTableColumns)

        self._jumpRouteTable = gui.HexTable(
            milieu=milieu,
            rules=rules,
            worldTagging=worldTagging,
            taggingColours=taggingColours)
        self._jumpRouteTable.setHexTooltipProvider(
            provider=self._hexTooltipProvider)
        self._jumpRouteTable.setActiveColumns(self._jumpRouteColumns())
        self._jumpRouteTable.setMinimumHeight(100)
        self._jumpRouteTable.setSortingEnabled(False) # Disable sorting as we only want to display in jump route order
        self._jumpRouteTable.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self._jumpRouteTable.customContextMenuRequested.connect(self._showJumpRouteTableContextMenu)

        # Override the tables actions for showing selected/all worlds on a popup map
        # window with actions that will show them on the main map for this window
        showJumpRouteSelectionOnMapAction = QtWidgets.QAction('Show Selection on Map...', self)
        showJumpRouteSelectionOnMapAction.setEnabled(False) # No selection
        showJumpRouteSelectionOnMapAction.triggered.connect(self._showJumpRouteTableSelectionOnMap)
        self._jumpRouteTable.setShowSelectionOnMapAction(showJumpRouteSelectionOnMapAction)

        showJumpRouteContentOnMapAction = QtWidgets.QAction('Show All on Map...', self)
        showJumpRouteContentOnMapAction.setEnabled(False) # No content
        showJumpRouteContentOnMapAction.triggered.connect(self._showJumpRouteContentOnMap)
        self._jumpRouteTable.setShowContentOnMapAction(showJumpRouteContentOnMapAction)

        jumpRouteLayout = QtWidgets.QVBoxLayout()
        jumpRouteLayout.setContentsMargins(0, 0, 0, 0)
        jumpRouteLayout.setSpacing(0) # No spacing between tabs and table
        jumpRouteLayout.addWidget(self._jumpRouteDisplayModeTabBar)
        jumpRouteLayout.addWidget(self._jumpRouteTable)
        jumpRouteWidget = QtWidgets.QWidget()
        jumpRouteWidget.setLayout(jumpRouteLayout)

        self._refuellingPlanTable = _RefuellingPlanTable(
            milieu=milieu,
            rules=rules,
            outcomeColours=outcomeColours,
            worldTagging=worldTagging,
            taggingColours=taggingColours)
        self._refuellingPlanTable.setHexTooltipProvider(provider=self._hexTooltipProvider)
        self._refuellingPlanTable.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self._refuellingPlanTable.customContextMenuRequested.connect(self._showRefuellingPlanTableContextMenu)

        # Override the tables actions for showing selected/all worlds on a popup map
        # window with actions that will show them on the main map for this window
        showRefuellingSelectionOnMapAction = QtWidgets.QAction('Show Selection on Map...', self)
        showRefuellingSelectionOnMapAction.setEnabled(False) # No selection
        showRefuellingSelectionOnMapAction.triggered.connect(self._showRefuellingTableSelectionOnMap)
        self._refuellingPlanTable.setShowSelectionOnMapAction(showRefuellingSelectionOnMapAction)

        showRefuellingContentOnMapAction = QtWidgets.QAction('Show All on Map...', self)
        showRefuellingContentOnMapAction.setEnabled(False) # No content
        showRefuellingContentOnMapAction.triggered.connect(self._showRefuellingTableContentOnMap)
        self._refuellingPlanTable.setShowContentOnMapAction(showRefuellingContentOnMapAction)

        self._mapWidget = gui.MapWidgetEx(
            milieu=milieu,
            rules=rules,
            style=mapStyle,
            options=mapOptions,
            rendering=mapRendering,
            animated=mapAnimations,
            worldTagging=worldTagging,
            taggingColours=taggingColours)
        self._mapWidget.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self._mapWidget.setToolTipCallback(self._formatMapToolTip)
        self._mapWidget.enableDeadSpaceSelection(
            enable=routingType is logic.RoutingType.DeadSpace)
        self._mapWidget.rightClicked.connect(self._showTravellerMapContextMenu)
        self._mapWidget.mapStyleChanged.connect(self._mapStyleChanged)
        self._mapWidget.mapOptionsChanged.connect(self._mapOptionsChanged)
        self._mapWidget.mapRenderingChanged.connect(self._mapRenderingChanged)
        self._mapWidget.mapAnimationChanged.connect(self._mapAnimationChanged)

        self._jumpRatingOverlayToggle = gui.ToggleButton()
        self._jumpRatingOverlayToggle.setChecked(False)
        self._jumpRatingOverlayToggle.toggled.connect(self._updateJumpOverlays)
        self._worldTaggingOverlayToggle = gui.ToggleButton()
        self._worldTaggingOverlayToggle.setChecked(False)
        self._worldTaggingOverlayToggle.toggled.connect(self._updateJumpOverlays)

        configLayout = QtWidgets.QGridLayout()
        configLayout.addWidget(self._jumpRatingOverlayToggle, 0, 0)
        configLayout.addWidget(gui.MapOverlayLabel('Jump Rating'), 0, 1)
        configLayout.addWidget(self._worldTaggingOverlayToggle, 1, 0)
        configLayout.addWidget(gui.MapOverlayLabel('World Tagging'), 1, 1)

        self._mapWidget.addConfigSection(
            section='Jump Overlays',
            content=configLayout)

        # HACK: This wrapper widget for the map is a hacky fix for what looks
        # like a bug in QTabWidget that is triggered if you make one of the
        # controls it contains full screen (true borderless full screen not
        # maximised). The issue I was seeing is the widget that I made full
        # screen would get a resize event for the screen resolution as you would
        # expect then immediately get another resize event that put it back to
        # the size it was before going full screen. As far as I can tell it's
        # caused by QTabWidget as it doesn't happen with the simulator window
        # which usually doesn't have a QTabWidget but can be made to happen by
        # adding one. The workaround I found is to warp the widget (the map in
        # this case) in a layout and wrap that layout in a widget. When this is
        # done the map doesn't get the second resize event setting it back to
        # its original size.
        mapWrapperLayout = QtWidgets.QVBoxLayout()
        mapWrapperLayout.setContentsMargins(0, 0, 0, 0)
        mapWrapperLayout.addWidget(self._mapWidget)
        self._mapWrapperWidget = gui.LayoutWrapperWidget(mapWrapperLayout)

        self._resultsDisplayModeTabView = gui.TabWidgetEx()
        self._resultsDisplayModeTabView.setTabPosition(QtWidgets.QTabWidget.TabPosition.East)
        self._resultsDisplayModeTabView.addTab(jumpRouteWidget, 'Jump Route')
        self._resultsDisplayModeTabView.addTab(self._refuellingPlanTable, 'Refuelling Plan')
        self._resultsDisplayModeTabView.addTab(self._mapWrapperWidget, 'Universe Map')
        self._resultsDisplayModeTabView.setCurrentWidget(self._mapWrapperWidget)

        routeLayout = QtWidgets.QVBoxLayout()
        routeLayout.addWidget(self._calculateRouteButton)
        routeLayout.addLayout(labelLayout)
        routeLayout.addWidget(self._resultsDisplayModeTabView)

        self._plannedRouteGroupBox = QtWidgets.QGroupBox('Jump Route')
        self._plannedRouteGroupBox.setLayout(routeLayout)

    def _clearJumpRoute(self):
        if self._jumpRouteJob:
            self._jumpRouteJob.cancel()
            self._jumpRouteJob = None

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
        self._shouldZoomToNewRoute = True

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
        self._waypointsWidget.setActiveColumns(columns)

    def _appConfigChanged(
            self,
            option: app.ConfigOption,
            oldValue: typing.Any,
            newValue: typing.Any
            ) -> None:
        if option is app.ConfigOption.Milieu:
            self._hexTooltipProvider.setMilieu(milieu=newValue)
            self._selectStartFinishWidget.setMilieu(milieu=newValue)
            self._waypointsWidget.setMilieu(milieu=newValue)
            self._avoidHexesWidget.setMilieu(milieu=newValue)
            self._jumpRouteTable.setMilieu(milieu=newValue)
            self._refuellingPlanTable.setMilieu(milieu=newValue)
            self._mapWidget.setMilieu(milieu=newValue)
            self._updateJumpOverlays()
        elif option is app.ConfigOption.Rules:
            self._hexTooltipProvider.setRules(rules=newValue)
            self._selectStartFinishWidget.setRules(rules=newValue)
            self._waypointsWidget.setRules(rules=newValue)
            self._avoidHexesWidget.setRules(rules=newValue)
            self._jumpRouteTable.setRules(rules=newValue)
            self._refuellingPlanTable.setRules(rules=newValue)
            self._mapWidget.setRules(rules=newValue)
            self._updateJumpOverlays()
        elif option is app.ConfigOption.MapStyle:
            self._hexTooltipProvider.setMapStyle(style=newValue)
            self._selectStartFinishWidget.setMapStyle(style=newValue)
            self._waypointsWidget.setMapStyle(style=newValue)
            self._avoidHexesWidget.setMapStyle(style=newValue)
            self._mapWidget.setStyle(style=newValue)
        elif option is app.ConfigOption.MapOptions:
            self._hexTooltipProvider.setMapOptions(options=newValue)
            self._selectStartFinishWidget.setMapOptions(options=newValue)
            self._waypointsWidget.setMapOptions(options=newValue)
            self._avoidHexesWidget.setMapOptions(options=newValue)
            self._mapWidget.setOptions(options=newValue)
        elif option is app.ConfigOption.MapRendering:
            self._selectStartFinishWidget.setMapRendering(rendering=newValue)
            self._waypointsWidget.setMapRendering(rendering=newValue)
            self._avoidHexesWidget.setMapRendering(rendering=newValue)
            self._mapWidget.setRendering(rendering=newValue)
        elif option is app.ConfigOption.MapAnimations:
            self._selectStartFinishWidget.setMapAnimations(enabled=newValue)
            self._waypointsWidget.setMapAnimations(enabled=newValue)
            self._avoidHexesWidget.setMapAnimations(enabled=newValue)
            self._mapWidget.setAnimated(animated=newValue)
        elif option is app.ConfigOption.ShowToolTipImages:
            self._hexTooltipProvider.setShowImages(show=newValue)
        elif option is app.ConfigOption.OutcomeColours:
            self._refuellingPlanTable.setOutcomeColours(colours=newValue)
        elif option is app.ConfigOption.WorldTagging:
            self._hexTooltipProvider.setWorldTagging(tagging=newValue)
            self._selectStartFinishWidget.setWorldTagging(tagging=newValue)
            self._waypointsWidget.setWorldTagging(tagging=newValue)
            self._avoidHexesWidget.setWorldTagging(tagging=newValue)
            self._jumpRouteTable.setWorldTagging(tagging=newValue)
            self._refuellingPlanTable.setWorldTagging(tagging=newValue)
            self._mapWidget.setWorldTagging(tagging=newValue)
            self._updateJumpOverlays()
        elif option is app.ConfigOption.TaggingColours:
            self._hexTooltipProvider.setTaggingColours(colours=newValue)
            self._selectStartFinishWidget.setTaggingColours(colours=newValue)
            self._waypointsWidget.setTaggingColours(colours=newValue)
            self._avoidHexesWidget.setTaggingColours(colours=newValue)
            self._avoidFiltersWidget.setTaggingColours(colours=newValue)
            self._jumpRouteTable.setTaggingColours(colours=newValue)
            self._refuellingPlanTable.setTaggingColours(colours=newValue)
            self._mapWidget.setTaggingColours(colours=newValue)
            self._updateJumpOverlays()
        elif option is app.ConfigOption.RoutingType:
            self._routingTypeComboBox.setCurrentEnum(newValue)

            isDeadSpaceRouting = newValue is logic.RoutingType.DeadSpace
            self._selectStartFinishWidget.enableDeadSpaceSelection(enable=isDeadSpaceRouting)
            self._waypointsWidget.enableDeadSpace(enable=isDeadSpaceRouting)
            self._mapWidget.enableDeadSpaceSelection(enable=isDeadSpaceRouting)
            self._enableDisableControls()
            self._updateTravellerMapOverlays()
        elif option is app.ConfigOption.PerJumpOverhead:
            self._perJumpOverheadsSpinBox.setValue(newValue)
        elif option is app.ConfigOption.IncludeStartBerthing:
            self._includeStartWorldBerthingCheckBox.setChecked(newValue)
        elif option is app.ConfigOption.IncludeFinishBerthing:
            self._includeFinishWorldBerthingCheckBox.setChecked(newValue)
        elif option is app.ConfigOption.RefuellingStrategy:
            self._refuellingStrategyComboBox.setCurrentEnum(newValue)
        elif option is app.ConfigOption.RouteOptimisation:
            self._routeOptimisationComboBox.setCurrentEnum(newValue)
        elif option is app.ConfigOption.UseFuelCaches:
            self._useFuelCachesCheckBox.setChecked(newValue)
        elif option is app.ConfigOption.UseAnomalyRefuelling:
            self._useAnomalyRefuellingCheckBox.setChecked(newValue)
            self._enableDisableControls()
        elif option is app.ConfigOption.AnomalyFuelCost:
            self._anomalyFuelCostSpinBox.setValue(newValue)
        elif option is app.ConfigOption.AnomalyBerthingCost:
            self._anomalyBerthingCostSpinBox.setValue(newValue)
        elif option is app.ConfigOption.ShipTonnage:
            self._shipTonnageSpinBox.setValue(newValue)
        elif option is app.ConfigOption.ShipJumpRating:
            self._shipJumpRatingSpinBox.setValue(newValue)
            self._updateJumpOverlays()
        elif option is app.ConfigOption.ShipFuelCapacity:
            self._shipFuelCapacitySpinBox.setValue(newValue)
        elif option is app.ConfigOption.ShipCurrentFuel:
            self._shipCurrentFuelSpinBox.setValue(newValue)
        elif option is app.ConfigOption.UseShipFuelPerParsec:
            self._shipFuelPerParsecSpinBox.setChecked(newValue)
        elif option is app.ConfigOption.ShipFuelPerParsec:
            self._shipFuelPerParsecSpinBox.setValue(newValue)


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

    def _calculateJumpRoute(self) -> None:
        if self._jumpRouteJob:
            # A trade option job is already running so cancel it
            self._jumpRouteJob.cancel()
            return

        self._clearJumpRoute()

        startHex, finishHex = self._selectStartFinishWidget.hexes()
        if not startHex or not finishHex:
            if not startHex and not finishHex:
                message = 'You need to select a start and finish location before calculating a route.'
            elif not startHex:
                message = 'You need to select a start location before calculating a route.'
            else:
                message = 'You need to select a finish location before calculating a route.'
            gui.MessageBoxEx.critical(parent=self, text=message)
            return

        if self._shipJumpRatingSpinBox.value() >= app.ConsideredVeryHighJumpRating:
            message = \
                'Your ship has a very high jump rating. This can significantly increase ' \
                'the number of possible routes that need to be processed, with the result ' \
                'being route calculations can take a long time.\n\n' \
                'Do you want to continue?'
            answer = gui.AutoSelectMessageBox.question(
                parent=self,
                text=message,
                stateKey='JumpRouteHighJumpRatingWarning',
                # Only remember if the user clicked yes
                rememberState=QtWidgets.QMessageBox.StandardButton.Yes)
            if answer == QtWidgets.QMessageBox.StandardButton.No:
                return

        # Fuel based route calculation
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

            # Highlight cases where start world or waypoints don't support the
            # refuelling strategy
            startWorld = traveller.WorldManager.instance().worldByPosition(
                milieu=milieu,
                hex=startHex)
            if startWorld and not pitCostCalculator.refuellingType(world=startWorld):
                message = 'Fuel based route calculation is enabled but the start world doesn\'t support the selected refuelling strategy.'
                if self._shipCurrentFuelSpinBox.value() <= 0:
                    message += ' In order to calculate a route, you must specify the amount of fuel that is currently in the ship.'
                    gui.MessageBoxEx.critical(parent=self, text=message)
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

            # Highlight the case where the start hex is dead space and the ship doesn't
            # have fuel to make a parsec 1 jump
            if (routingType is logic.RoutingType.DeadSpace) and (not startWorld):
                currentFuel = self._shipCurrentFuelSpinBox.value()
                oneParsecFuel = traveller.calculateFuelRequiredForJump(
                    jumpDistance=1,
                    shipTonnage=self._shipTonnageSpinBox.value())
                if currentFuel < oneParsecFuel.value():
                    gui.MessageBoxEx.critical(
                        parent=self,
                        text='The starting location is dead space but the ship doesn\'t have enough fuel to jump.')
                    return

            fuelIssueWorldStrings = []
            for waypointHex in self._waypointsWidget.hexes():
                waypointWorld = traveller.WorldManager.instance().worldByPosition(
                    milieu=milieu,
                    hex=waypointHex)
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

        hexSequence = []
        berthingIndices = []

        hexSequence.append(startHex)
        if self._includeStartWorldBerthingCheckBox.isChecked():
            berthingIndices.append(0)

        for row in range(self._waypointsTable.rowCount()):
            hexSequence.append(self._waypointsTable.hex(row))
            if self._waypointsTable.isBerthingChecked(row):
                berthingIndices.append(row + 1)

        hexSequence.append(finishHex)
        if self._includeFinishWorldBerthingCheckBox.isChecked():
            berthingIndices.append(len(hexSequence) - 1)

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

        tagging = app.Config.instance().value(option=app.ConfigOption.WorldTagging)

        hexFilter = _HexFilter(
            avoidHexes=self._avoidHexesWidget.hexes(),
            avoidFilters=self._avoidFiltersWidget.filters(),
            avoidFilterLogic=self._avoidFiltersWidget.filterLogic(),
            rules=rules,
            tagging=tagging)

        try:
            self._jumpRouteJob = jobs.RoutePlannerJob(
                parent=self,
                routingType=routingType,
                milieu=milieu,
                hexSequence=hexSequence,
                shipTonnage=self._shipTonnageSpinBox.value(),
                shipJumpRating=self._shipJumpRatingSpinBox.value(),
                shipFuelCapacity=self._shipFuelCapacitySpinBox.value(),
                shipCurrentFuel=self._shipCurrentFuelSpinBox.value(),
                shipFuelPerParsec=self._shipFuelPerParsecSpinBox.value(),
                jumpCostCalculator=jumpCostCalculator,
                pitCostCalculator=pitCostCalculator,
                hexFilter=hexFilter,
                berthingIndices=berthingIndices,
                progressCallback=self._jumpRouteJobProgressUpdate,
                finishedCallback=self._jumpRouteJobFinished)
        except Exception as ex:
            message = 'Failed to create route planner job'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

        self._calculateRouteButton.showSecondaryText()
        self._enableDisableControls()

        # Start job after a delay to give the ui time to update
        QtCore.QTimer.singleShot(200, self._jumpRouteJobStart)

    def _jumpRouteJobStart(self) -> None:
        if not self._jumpRouteJob:
            return

        try:
            self._jumpRouteJob.start()
        except Exception as ex:
            self._jumpRouteJob = None
            self._calculateRouteButton.showPrimaryText()
            self._enableDisableControls()

            message = 'Failed to start route planner job'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)

    def _jumpRouteJobProgressUpdate(self, routeCount: int) -> None:
        self._processedRoutesLabel.setNum(routeCount)

    def _jumpRouteJobFinished(self, result: typing.Union[typing.Optional[logic.JumpRoute], Exception]) -> None:
        if isinstance(result, Exception):
            milieu = app.Config.instance().value(option=app.ConfigOption.Milieu)
            startHex, finishHex = self._selectStartFinishWidget.hexes()
            startString = traveller.WorldManager.instance().canonicalHexName(milieu=milieu, hex=startHex)
            finishString = traveller.WorldManager.instance().canonicalHexName(milieu=milieu, hex=finishHex)
            message = f'Failed to calculate jump route between {startString} and {finishString}'
            logging.error(message, exc_info=result)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=result)
        elif self._jumpRouteJob and self._jumpRouteJob.isCancelled():
            pass
        elif isinstance(result, logic.JumpRoute):
            self._setJumpRoute(
                jumpRoute=result,
                routeLogistics=self._interactiveCalculateLogistics(jumpRoute=result))
        else:
            gui.MessageBoxEx.information(
                parent=self,
                text='No jump route found')

        self._jumpRouteJob = None
        self._calculateRouteButton.showPrimaryText()
        self._enableDisableControls()

    def _setJumpRoute(
            self,
            jumpRoute: logic.JumpRoute,
            routeLogistics: typing.Optional[logic.RouteLogistics]
            ) -> None:
            self._jumpRoute = jumpRoute
            self._routeLogistics = routeLogistics
            self._jumpRouteTable.setHexes(hexes=self._jumpRoute.nodes())

            if self._routeLogistics:
                self._refuellingPlanTable.setPitStops(
                    pitStops=self._routeLogistics.refuellingPlan())
            else:
                self._refuellingPlanTable.removeAllRows()

            self._updateRouteLabels()
            self._updateTravellerMapOverlays()

            # We've set a new jump route so prevent future recalculations
            # from zooming out to show the full jump route. Zooming will be
            # re-enabled if we start calculating a "new" jump route (i.e the
            # start/finish world changes)
            self._shouldZoomToNewRoute = False

    def _updateJumpRouteTableColumns(self, index: int) -> None:
        self._jumpRouteTable.setActiveColumns(self._jumpRouteColumns())

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

    def _showJumpRouteTableContextMenu(self, point: QtCore.QPoint) -> None:
        hasSelection = self._jumpRouteTable.hasSelection()

        addSelectionToWaypointsAction = QtWidgets.QAction('Add Selection to Waypoints')
        addSelectionToWaypointsAction.setEnabled(hasSelection)
        addSelectionToWaypointsAction.triggered.connect(
            lambda: [self._waypointsWidget.addHex(hex) for hex in self._jumpRouteTable.selectedHexes()])

        addSelectionToAvoidListAction = QtWidgets.QAction('Add Selection to Avoid List')
        addSelectionToAvoidListAction.setEnabled(hasSelection)
        addSelectionToAvoidListAction.triggered.connect(
            lambda: [self._avoidHexesWidget.addHex(hex) for hex in self._jumpRouteTable.selectedHexes()])

        menu = QtWidgets.QMenu()
        menu.addAction(addSelectionToWaypointsAction)
        menu.addAction(addSelectionToAvoidListAction)
        menu.addSeparator()
        self._jumpRouteTable.fillContextMenu(menu)
        menu.exec(self._jumpRouteTable.viewport().mapToGlobal(point))

    def _showRefuellingPlanTableContextMenu(self, point: QtCore.QPoint) -> None:
        hasSelection = self._refuellingPlanTable.hasSelection()
        clickedPitStop = self._refuellingPlanTable.pitStopAt(point.y())

        addSelectionToWaypointsAction = QtWidgets.QAction('Add Selection to Waypoints')
        addSelectionToWaypointsAction.setEnabled(hasSelection)
        addSelectionToWaypointsAction.triggered.connect(
            lambda: [self._waypointsWidget.addHex(hex) for hex in self._refuellingPlanTable.selectedHexes()])

        addSelectionToAvoidListAction = QtWidgets.QAction('Add Selection to Avoid List')
        addSelectionToAvoidListAction.setEnabled(hasSelection)
        addSelectionToAvoidListAction.triggered.connect(
            lambda: [self._avoidHexesWidget.addHex(hex) for hex in self._refuellingPlanTable.selectedHexes()])

        showPitStopCalculationsAction = QtWidgets.QAction('Show Pit Stop Calculations...')
        showPitStopCalculationsAction.setEnabled(clickedPitStop is not None)
        showPitStopCalculationsAction.triggered.connect(
            lambda: self._showCalculations(clickedPitStop.totalCost()))

        showAllRefuellingCalculationsAction = QtWidgets.QAction('Show All Refuelling Calculations...')
        showAllRefuellingCalculationsAction.setEnabled(self._routeLogistics is not None)
        showAllRefuellingCalculationsAction.triggered.connect(
            lambda: self._showCalculations(self._routeLogistics.totalCosts()))

        menu = QtWidgets.QMenu()
        menu.addAction(addSelectionToWaypointsAction)
        menu.addAction(addSelectionToAvoidListAction)
        menu.addSeparator()
        self._refuellingPlanTable.fillContextMenu(menu)
        menu.addSeparator()
        menu.addAction(showPitStopCalculationsAction)
        menu.addAction(showAllRefuellingCalculationsAction)
        menu.exec(self._refuellingPlanTable.viewport().mapToGlobal(point))

    # TODO: There is a discrepancy between how this menu is structured and
    # how other menus are structured
    def _showTravellerMapContextMenu(
            self,
            hex: typing.Optional[travellermap.HexPosition]
            ) -> None:
        if not hex:
            return

        isCurrentWaypoint = self._waypointsWidget.containsHex(hex=hex)
        isCurrentAvoidHex = self._avoidHexesWidget.containsHex(hex=hex)

        isValidStartFinish = isValidWaypoint = \
            self._routingTypeComboBox.currentEnum() is logic.RoutingType.DeadSpace or \
            traveller.WorldManager.instance().worldByPosition(
                milieu=app.Config.instance().value(option=app.ConfigOption.Milieu),
                hex=hex) != None
        isValidAvoidHex = not isCurrentAvoidHex

        startHex, finishHex = self._selectStartFinishWidget.hexes()
        menuItems = []

        action = QtWidgets.QAction('Recalculate Jump Route', self)
        menuItems.append(action)
        action.triggered.connect(self._calculateJumpRoute)
        action.setEnabled(startHex != None and finishHex != None)

        action = QtWidgets.QAction('Show Location Details...', self)
        menuItems.append(action)
        action.triggered.connect(lambda: self._showHexDetails([hex]))

        menu = QtWidgets.QMenu('Start/Finish', self)
        menuItems.append(menu)
        action = menu.addAction('Set Start Location')
        action.triggered.connect(lambda: self._selectStartFinishWidget.setStartHex(hex=hex))
        action.setEnabled(isValidStartFinish)
        action = menu.addAction('Set Finish Location')
        action.triggered.connect(lambda: self._selectStartFinishWidget.setFinishHex(hex=hex))
        action.setEnabled(isValidStartFinish)
        action = menu.addAction('Swap Start && Finish Locations')
        action.triggered.connect(
            lambda: self._selectStartFinishWidget.setHexes(startHex=finishHex, finishHex=startHex))
        action.setEnabled(startHex != None and finishHex != None)

        menu = QtWidgets.QMenu('Waypoints', self)
        menuItems.append(menu)
        action = menu.addAction('Add Location')
        action.triggered.connect(lambda: self._waypointsWidget.addHex(hex=hex))
        action.setEnabled(isValidWaypoint)
        action = menu.addAction('Remove Location')
        action.triggered.connect(lambda: self._waypointsWidget.removeHex(hex=hex))
        action.setEnabled(isCurrentWaypoint)

        menu = QtWidgets.QMenu('Avoid List', self)
        menuItems.append(menu)
        action = menu.addAction('Add Location')
        action.triggered.connect(lambda: self._avoidHexesWidget.addHex(hex=hex))
        action.setEnabled(isValidAvoidHex)
        action = menu.addAction('Remove Location')
        action.triggered.connect(lambda: self._avoidHexesWidget.removeHex(hex=hex))
        action.setEnabled(isCurrentAvoidHex)

        menu = QtWidgets.QMenu('Zoom To', self)
        menuItems.append(menu)
        action = menu.addAction('Start Location')
        action.triggered.connect(lambda: self._showHexOnMap(hex=startHex))
        action.setEnabled(startHex != None)
        action = menu.addAction('Finish Location')
        action.triggered.connect(lambda: self._showHexOnMap(hex=finishHex))
        action.setEnabled(finishHex != None)
        action = menu.addAction('Jump Route')
        action.triggered.connect(lambda: self._showJumpRouteOnMap())
        action.setEnabled(self._jumpRoute != None)

        menu = QtWidgets.QMenu('Import', self)
        menuItems.append(menu)
        action = menu.addAction('Jump Route...')
        action.triggered.connect(self._importJumpRoute)


        menu = QtWidgets.QMenu('Export', self)
        menuItems.append(menu)
        action = menu.addAction('Jump Route...')
        action.triggered.connect(self._exportJumpRoute)
        action.setEnabled(self._jumpRoute != None)
        action = menu.addAction('Screenshot...')
        action.triggered.connect(self._exportMapScreenshot)

        gui.displayMenu(
            parent=self,
            items=menuItems,
            globalPoint=QtGui.QCursor.pos())

    def _formatMapToolTip(
            self,
            hex: typing.Optional[travellermap.HexPosition]
            ) -> typing.Optional[str]:
        if not hex:
            return None

        if not self._jumpRoute:
            startHex, finishHex = self._selectStartFinishWidget.hexes()
            if (startHex and hex == startHex) and (finishHex and hex == finishHex):
                return gui.createStringToolTip('<nobr>Start &amp; Finish Location</nobr>', escape=False)
            elif (startHex and hex == startHex):
                return gui.createStringToolTip('<nobr>Start Location</nobr>', escape=False)
            elif (finishHex and hex == finishHex):
                return gui.createStringToolTip('<nobr>Finish Location</nobr>', escape=False)
            elif self._waypointsWidget.containsHex(hex):
                return gui.createStringToolTip('<nobr>Waypoint Location</nobr>', escape=False)
            elif self._avoidHexesWidget.containsHex(hex):
                return gui.createStringToolTip('<nobr>Avoid Location</nobr>', escape=False)
            return None

        jumpNodes: typing.Dict[int, typing.Optional[logic.PitStop]] = {}
        for nodeIndex in range(self._jumpRoute.nodeCount()):
            if self._jumpRoute.nodeAt(nodeIndex) == hex:
                jumpNodes[nodeIndex] = None

        if self._routeLogistics:
            refuellingPlan = self._routeLogistics.refuellingPlan()
            if refuellingPlan:
                for pitStop in refuellingPlan:
                    if pitStop.routeIndex() in jumpNodes:
                        jumpNodes[pitStop.routeIndex()] = pitStop

        routeParsecs = self._jumpRoute.totalParsecs()
        toolTip = ''
        for nodeIndex, pitStop in jumpNodes.items():
            toolTip += f'<li><nobr>Route Node: {nodeIndex + 1}</nobr></li>'
            toolTip += f'<ul style="{gui.TooltipIndentListStyle}">'

            nodeParsecs = self._jumpRoute.nodeParsecs(index=nodeIndex)
            toolTip += '<li><nobr>Travelled: {} parsecs</nobr></li>'.format(
                nodeParsecs)
            toolTip += '<li><nobr>Remaining: {} parsecs</nobr></li>'.format(
                routeParsecs - nodeParsecs)

            if pitStop:
                refuellingType = pitStop.refuellingType()
                if refuellingType:
                    toolTip += '<li><nobr>Refuelling Type: {}</nobr></li>'.format(
                        _formatRefuellingTypeString(pitStop=pitStop))

                    tonsOfFuel = pitStop.tonsOfFuel()
                    if tonsOfFuel:
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
            if self._waypointsWidget.containsHex(hex):
                return gui.createStringToolTip('<nobr>Waypoint Location</nobr>', escape=False)

            # Check for the world being an avoid world. This is done last as
            # start/finish/waypoint worlds can be on the avoid list but we
            # don't want to flag them as such here
            if self._avoidHexesWidget.containsHex(hex):
                return gui.createStringToolTip('<nobr>Avoid Location</nobr>', escape=False)

            return None

        toolTip = f'<ul style="list-style-type:none; margin-left:0px; -qt-list-indent:0;">{toolTip}</ul>'
        return gui.createStringToolTip(toolTip, escape=False)

    def _importJumpRoute(self) -> None:
        dlg = _ImportJumpRouteDialog(parent=self)
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return

        try:
            jumpRoute = logic.readJumpRoute(path=dlg.filePath())
        except Exception as ex:
            message = f'Failed to read jump route from "{dlg.filePath()}"'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

        routeLogistics = None
        if isinstance(jumpRoute, logic.RouteLogistics):
            routeLogistics = jumpRoute
            jumpRoute = routeLogistics.jumpRoute()
            if not dlg.includeLogistics():
                routeLogistics = None

            if routeLogistics:
                logisticsMilieu = routeLogistics.milieu()
                currentMilieu = app.Config.instance().value(option=app.ConfigOption.Milieu)
                if logisticsMilieu is not currentMilieu:
                    text = 'The logistics for the imported jump route not from the current milieu\n' \
                        f'Current: {currentMilieu.value}\n' \
                        f'Imported: {logisticsMilieu.value}\n' \
                        '\nDo you want to import them?'
                    answer = gui.MessageBoxEx.question(
                        parent=self,
                        text=text,
                        buttons=QtWidgets.QMessageBox.StandardButton.Yes | \
                        QtWidgets.QMessageBox.StandardButton.No | \
                        QtWidgets.QMessageBox.StandardButton.Cancel)
                    if answer == QtWidgets.QMessageBox.StandardButton.Cancel:
                        return # User cancelled

                    if answer == QtWidgets.QMessageBox.StandardButton.No:
                        # Ignore logistics but continue importing route
                        routeLogistics = None

        if not jumpRoute:
            message = f'No jump route found in "{dlg.filePath()}"'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

        if dlg.replaceStartFinish():
            self._selectStartFinishWidget.setHexes(
                startHex=jumpRoute.startNode(),
                finishHex=jumpRoute.finishNode())

        if dlg.replaceWaypoints():
            self._waypointsTable.removeAllRows()

            # Check for waypoints (start & finish are ignored as they
            # can't be waypoints)
            for index in range(1, jumpRoute.nodeCount() - 1):
                if jumpRoute.isWaypoint(index):
                    node = jumpRoute.nodeAt(index)
                    row = self._waypointsTable.addHex(node)
                    self._waypointsTable.setBerthingChecked(
                        row,
                        jumpRoute.mandatoryBerthing(index))

        self._shouldZoomToNewRoute = True
        self._setJumpRoute(
            jumpRoute=jumpRoute,
            routeLogistics=routeLogistics)

    def _exportJumpRoute(self) -> None:
        if not self._jumpRoute:
            gui.MessageBoxEx.information(
                parent=self,
                text='No jump route to export')
            return

        dlg = _ExportJumpRouteDialog(parent=self)
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return

        try:
            logic.writeJumpRoute(
                route=self._routeLogistics if dlg.includeLogistics() else self._jumpRoute,
                path=dlg.filePath(),
                includeCalculations=dlg.includeCalculations())
        except Exception as ex:
            message = f'Failed to write jump route to "{dlg.filePath()}"'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)

    def _exportMapScreenshot(self) -> None:
        try:
            snapshot = self._mapWidget.createSnapshot()
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

    def _showHexDetails(
            self,
            hexes: typing.Iterable[travellermap.HexPosition]
            ) -> None:
        infoWindow = gui.WindowManager.instance().showHexDetailsWindow()
        infoWindow.addHexes(hexes=hexes)

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

    def _showHexOnMap(
            self,
            hex: travellermap.HexPosition
            ) -> None:
        try:
            self._resultsDisplayModeTabView.setCurrentWidget(self._mapWrapperWidget)
            self._mapWidget.centerOnHex(hex=hex)
        except Exception as ex:
            message = 'Failed to show hex on map'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)

    # This moves/zooms the traveller map widget to show
    # the current jump route
    def _showJumpRouteOnMap(self) -> None:
        if not self._jumpRoute:
            return
        self._showHexesOnMap(hexes=self._jumpRoute.nodes())

    def _showHexesOnMap(
            self,
            hexes: typing.Iterable[travellermap.HexPosition]
            ) -> None:
        if not hexes:
            return

        try:
            self._resultsDisplayModeTabView.setCurrentWidget(self._mapWrapperWidget)
            self._mapWidget.centerOnHexes(hexes=hexes)
        except Exception as ex:
            message = 'Failed to show hexes(s) on map'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)

    def _showWaypointsTableSelectionOnMap(self) -> None:
        self._showHexesOnMap(hexes=self._waypointsWidget.selectedHexes())

    def _showWaypointsTableContentOnMap(self) -> None:
        self._showHexesOnMap(hexes=self._waypointsWidget.hexes())

    def _showAvoidHexesTableSelectionOnMap(self) -> None:
        self._showHexesOnMap(hexes=self._avoidHexesWidget.selectedHexes())

    def _showAvoidHexesTableContentOnMap(self) -> None:
        self._showHexesOnMap(hexes=self._avoidHexesWidget.hexes())

    def _showJumpRouteTableSelectionOnMap(self) -> None:
        self._showHexesOnMap(hexes=self._jumpRouteTable.selectedHexes())

    def _showJumpRouteContentOnMap(self) -> None:
        self._showHexesOnMap(hexes=self._jumpRouteTable.hexes())

    def _showRefuellingTableSelectionOnMap(self) -> None:
        self._showHexesOnMap(hexes=self._refuellingPlanTable.selectedHexes())

    def _showRefuellingTableContentOnMap(self) -> None:
        self._showHexesOnMap(hexes=self._refuellingPlanTable.hexes())

    def _updateJumpOverlays(self) -> None:
        for handle in self._jumpOverlayHandles:
            self._mapWidget.removeOverlay(handle=handle)
        self._jumpOverlayHandles.clear()

        showJumpRatingOverlay = self._jumpRatingOverlayToggle.isChecked()
        showWorldTaggingOverlay = self._worldTaggingOverlayToggle.isChecked()
        if not (showJumpRatingOverlay or showWorldTaggingOverlay):
            return # Nothing more to do

        startHex, finishHex = self._selectStartFinishWidget.hexes()
        jumpRating = self._shipJumpRatingSpinBox.value()

        if startHex and showJumpRatingOverlay:
            mapStyle = app.Config.instance().value(option=app.ConfigOption.MapStyle)
            isDarkMapStyle = travellermap.isDarkStyle(style=mapStyle)
            colour = self._JumpRatingOverlayDarkStyleColour \
                if isDarkMapStyle else \
                self._JumpRatingOverlayLightStyleColour
            handle = self._mapWidget.createRadiusOverlay(
                center=startHex,
                radius=jumpRating,
                lineColour=colour,
                lineWidth=self._JumpRatingOverlayLineWidth)
            self._jumpOverlayHandles.add(handle)

        if startHex and showWorldTaggingOverlay:
            milieu = app.Config.instance().value(
                option=app.ConfigOption.Milieu)
            worldTagging = app.Config.instance().value(
                option=app.ConfigOption.WorldTagging)
            taggingColours = app.Config.instance().value(
                option=app.ConfigOption.TaggingColours)

            try:
                worlds = traveller.WorldManager.instance().worldsInRadius(
                    milieu=milieu,
                    center=startHex,
                    searchRadius=jumpRating)
            except Exception as ex:
                startString = traveller.WorldManager.instance().canonicalHexName(milieu=milieu, hex=startHex)
                logging.warning(
                    f'An exception occurred while finding worlds reachable from {startString}',
                    exc_info=ex)
                return

            taggedHexes = []
            colourMap = {}
            for world in worlds:
                worldHex = world.hex()
                if (worldHex == startHex) or (worldHex == finishHex):
                    continue # Don't highlight start/finish worlds
                tagLevel = worldTagging.calculateWorldTagLevel(world=world)
                if not tagLevel:
                    continue

                colour = QtGui.QColor(taggingColours.colour(level=tagLevel))
                tagColour = gui.colourToString(
                    colour=colour,
                    includeAlpha=False) # Remove alpha from colour
                taggedHexes.append(world.hex())
                colourMap[world.hex()] = tagColour

            if taggedHexes:
                handle = self._mapWidget.createHexOverlay(
                    hexes=taggedHexes,
                    primitive=gui.MapPrimitiveType.Hex,
                    fillMap=colourMap)
                self._jumpOverlayHandles.add(handle)

    def _updateRouteLabels(self) -> None:
        if self._jumpRoute:
            self._jumpCountLabel.setNum(self._jumpRoute.jumpCount())
            self._routeLengthLabel.setNum(self._jumpRoute.totalParsecs())
        else:
            self._jumpCountLabel.clear()
            self._routeLengthLabel.clear()

        if self._routeLogistics:
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
        else:
            self._avgRouteCostLabel.clear()
            self._minRouteCostLabel.clear()
            self._maxRouteCostLabel.clear()

    def _updateTravellerMapOverlays(self) -> None:
        self._mapWidget.clearHexHighlights()
        self._mapWidget.clearJumpRoute()
        self._jumpRatingOverlayHandle = None
        self._reachableWorldsOverlayHandle = None

        startHex, finishHex = self._selectStartFinishWidget.hexes()
        if startHex:
            self._mapWidget.highlightHex(
                hex=startHex,
                colour='#00FF00',
                radius=0.5)
        if finishHex:
            self._mapWidget.highlightHex(
                hex=finishHex,
                colour='#00FF00',
                radius=0.5)

        waypointHexes = self._waypointsWidget.hexes()
        if waypointHexes:
            self._mapWidget.highlightHexes(
                hexes=waypointHexes,
                colour='#0066FF',
                radius=0.3)

        filteredAvoidHexes = []
        for hex in self._avoidHexesWidget.hexes():
            if (hex != startHex) and (hex != finishHex) and (hex not in waypointHexes):
                filteredAvoidHexes.append(hex)
        if filteredAvoidHexes:
            self._mapWidget.highlightHexes(
                hexes=filteredAvoidHexes,
                colour='#FF0000',
                radius=0.3)

        if self._jumpRoute:
            self._mapWidget.setJumpRoute(
                jumpRoute=self._jumpRoute,
                refuellingPlan=self._routeLogistics.refuellingPlan() if self._routeLogistics else None)
            if self._shouldZoomToNewRoute:
                # Only zoom to area if this is a 'new' route (i.e. the start/finish worlds have changed).
                # Otherwise we assume this is an iteration of the existing jump route and the user wants
                # to stay with their current view
                self._mapWidget.centerOnJumpRoute()

        self._updateJumpOverlays()

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

    def _shipTonnageChanged(self, shipTonnage: int) -> None:
        app.Config.instance().setValue(
            option=app.ConfigOption.ShipTonnage,
            value=shipTonnage)

    def _shipJumpRatingChanged(self, jumpRating: int) -> None:
        # NOTE: Jump overlays aren't updated directly, they will be updated
        # when the window processes the config update
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


    def _enableDisableControls(self) -> None:
        # Disable configuration controls while jump route job is running
        runningJob = self._jumpRouteJob != None
        self._jumpWorldsGroupBox.setDisabled(runningJob)
        self._configurationGroupBox.setDisabled(runningJob)
        self._waypointsGroupBox.setDisabled(runningJob)
        self._avoidLocationsGroupBox.setDisabled(runningJob)

        isFuelAwareRouting = self._routingTypeComboBox.currentEnum() is not logic.RoutingType.Basic
        isAnomalyRefuelling = isFuelAwareRouting and self._useAnomalyRefuellingCheckBox.isChecked()
        self._refuellingStrategyComboBox.setEnabled(isFuelAwareRouting)
        self._useFuelCachesCheckBox.setEnabled(isFuelAwareRouting)
        self._useAnomalyRefuellingCheckBox.setEnabled(isFuelAwareRouting)
        self._anomalyFuelCostSpinBox.setEnabled(isAnomalyRefuelling)
        self._anomalyBerthingCostSpinBox.setEnabled(isAnomalyRefuelling)

    def _allowAvoidHex(self, hex: travellermap.HexPosition) -> bool:
        if self._avoidHexesWidget.containsHex(hex):
            # Silently ignore worlds that are already in the table
            return False
        return True

    def _interactiveCalculateLogistics(
            self,
            jumpRoute: logic.JumpRoute
            ) -> logic.RouteLogistics:
            invalidConfigReason = None
            if self._shipFuelCapacitySpinBox.value() > self._shipTonnageSpinBox.value():
                invalidConfigReason = 'The ship\'s fuel capacity can\'t be larger than its total tonnage'
            elif self._shipCurrentFuelSpinBox.value() > self._shipFuelCapacitySpinBox.value():
                invalidConfigReason = 'The ship\'s current fuel can\'t be larger than its fuel capacity'

            if invalidConfigReason:
                gui.MessageBoxEx.information(
                    parent=self,
                    text=f'Unable to calculate logistics for route. {invalidConfigReason}.')
                return

            milieu = app.Config.instance().value(option=app.ConfigOption.Milieu)
            useAnomalyRefuelling = self._useAnomalyRefuellingCheckBox.isChecked()
            pitCostCalculator = logic.PitStopCostCalculator(
                refuellingStrategy=self._refuellingStrategyComboBox.currentEnum(),
                useFuelCaches=self._useFuelCachesCheckBox.isChecked(),
                anomalyFuelCost=self._anomalyFuelCostSpinBox.value() if useAnomalyRefuelling else None,
                anomalyBerthingCost=self._anomalyBerthingCostSpinBox.value() if useAnomalyRefuelling else None,
                rules=app.Config.instance().value(option=app.ConfigOption.Rules))

            try:
                routeLogistics = logic.calculateRouteLogistics(
                    milieu=milieu,
                    jumpRoute=jumpRoute,
                    shipTonnage=self._shipTonnageSpinBox.value(),
                    shipFuelCapacity=self._shipFuelCapacitySpinBox.value(),
                    shipStartingFuel=self._shipCurrentFuelSpinBox.value(),
                    shipFuelPerParsec=self._shipFuelPerParsecSpinBox.value(),
                    perJumpOverheads=self._perJumpOverheadsSpinBox.value(),
                    pitCostCalculator=pitCostCalculator,
                    includeLogisticsCosts=True) # Always include logistics costs
                if not routeLogistics:
                    gui.MessageBoxEx.information(
                        parent=self,
                        text='Unable to calculate logistics for route. This can happen if it\'s not possible to generate a refuelling plan for the route due to waypoints not matching the specified refuelling strategy.')
                return routeLogistics
            except Exception as ex:
                startHex = jumpRoute.startNode()
                finishHex = jumpRoute.finishNode()
                startString = traveller.WorldManager.instance().canonicalHexName(milieu=milieu, hex=startHex)
                finishString = traveller.WorldManager.instance().canonicalHexName(milieu=milieu, hex=finishHex)
                message = 'Failed to calculate jump route logistics between {start} and {finish}'.format(
                    start=startString,
                    finish=finishString)
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
            noShowAgainId='JumpRouteWelcome')
        message.exec()
