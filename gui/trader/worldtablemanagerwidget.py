import gui
import logging
import traveller
import typing
from PyQt5 import QtWidgets, QtCore

class WorldTableManagerWidget(QtWidgets.QWidget):
    contentChanged = QtCore.pyqtSignal()
    contextMenuRequested = QtCore.pyqtSignal(QtCore.QPoint)
    displayModeChanged = QtCore.pyqtSignal(gui.WorldTableTabBar.DisplayMode)
    showInTravellerMap = QtCore.pyqtSignal([list])

    _StateVersion = 'WorldTableManagerWidget_v1'

    def __init__(
            self,
            allowWorldCallback: typing.Optional[typing.Callable[[traveller.World], bool]] = None,
            isOrderedList: bool = False,
            showAddNearbyWorldsButton: bool = True,
            showSelectInTravellerMapButton: bool = True,
            worldTable: typing.Optional[gui.WorldTable] = None,
            displayModeTabs: typing.Optional[gui.WorldTableTabBar] = None
            ) -> None:
        super().__init__()

        self._allowWorldCallback = allowWorldCallback
        self._relativeWorld = None
        self._enableContextMenuEvent = False
        self._enableDisplayModeChangedEvent = False
        self._enableShowInTravellerMapEvent = False

        self._showInTravellerMap = None

        # An instance of TravellerMapWorldSelectDialog is created on demand then maintained. This
        # is done to prevent the web widget being recreated and data being re-requested from
        # Traveller Map
        self._worldSelectDialog = None

        self._displayModeTabs = displayModeTabs
        if not self._displayModeTabs:
            self._displayModeTabs = gui.WorldTableTabBar()
        self._displayModeTabs.currentChanged.connect(self._displayModeChanged)

        self._worldTable = worldTable
        if not self._worldTable:
            self._worldTable = gui.WorldTable()
        self._worldTable.setVisibleColumns(self._displayColumns())
        self._worldTable.setMinimumHeight(100)
        self._worldTable.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self._worldTable.customContextMenuRequested.connect(self._showWorldTableContextMenu)
        self._worldTable.keyPressed.connect(self._worldTableKeyPressed)
        if isOrderedList:
            # Disable sorting on if the list is to be ordered
            self._worldTable.setSortingEnabled(False)

        tableLayout = QtWidgets.QVBoxLayout()
        tableLayout.setContentsMargins(0, 0, 0 , 0)
        tableLayout.setSpacing(0) # No gap between tabs and table
        tableLayout.addWidget(self._displayModeTabs)
        tableLayout.addWidget(self._worldTable)

        self._moveSelectionUpButton = None
        self._moveSelectionDownButton = None
        if isOrderedList:
            self._moveSelectionUpButton = QtWidgets.QToolButton()
            self._moveSelectionUpButton.setArrowType(QtCore.Qt.ArrowType.UpArrow)
            self._moveSelectionUpButton.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Minimum,
                QtWidgets.QSizePolicy.Policy.Minimum)
            self._moveSelectionUpButton.clicked.connect(self._worldTable.moveSelectionUp)

            self._moveSelectionDownButton = QtWidgets.QToolButton()
            self._moveSelectionDownButton.setArrowType(QtCore.Qt.ArrowType.DownArrow)
            self._moveSelectionDownButton.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Minimum,
                QtWidgets.QSizePolicy.Policy.Minimum)
            self._moveSelectionDownButton.clicked.connect(self._worldTable.moveSelectionDown)

            moveButtonLayout = QtWidgets.QVBoxLayout()
            moveButtonLayout.setContentsMargins(0, 0, 0 , 0)
            moveButtonLayout.addWidget(self._moveSelectionUpButton)
            moveButtonLayout.addWidget(self._moveSelectionDownButton)

            orderedTableLayout = QtWidgets.QHBoxLayout()
            orderedTableLayout.setContentsMargins(0, 0, 0 , 0)
            orderedTableLayout.addLayout(tableLayout)
            orderedTableLayout.addLayout(moveButtonLayout)

            tableLayout = orderedTableLayout

        self._addNearbyWorldsButton = None
        if showAddNearbyWorldsButton:
            self._addNearbyWorldsButton = QtWidgets.QPushButton('Add Nearby Worlds...')
            self._addNearbyWorldsButton.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Minimum,
                QtWidgets.QSizePolicy.Policy.Minimum)
            self._addNearbyWorldsButton.clicked.connect(self.promptAddNearbyWorlds)

        self._selectWithTravellerMapButton = None
        if showSelectInTravellerMapButton:
            self._selectWithTravellerMapButton = QtWidgets.QPushButton('Select with Traveller Map...')
            self._selectWithTravellerMapButton.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Minimum,
                QtWidgets.QSizePolicy.Policy.Minimum)
            self._selectWithTravellerMapButton.clicked.connect(self.promptSelectWithTravellerMap)

        self._addWorldButton = QtWidgets.QPushButton('Add...')
        self._addWorldButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)
        self._addWorldButton.clicked.connect(self.promptAddWorld)

        self._removeWorldButton = QtWidgets.QPushButton('Remove')
        self._removeWorldButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)
        self._removeWorldButton.clicked.connect(self.removeSelectedWorlds)

        self._removeAllWorldButton = QtWidgets.QPushButton('Remove All')
        self._removeAllWorldButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)
        self._removeAllWorldButton.clicked.connect(self.removeAllWorlds)

        buttonLayout = QtWidgets.QHBoxLayout()
        buttonLayout.setContentsMargins(0, 0, 0, 0)
        if self._addNearbyWorldsButton:
            buttonLayout.addWidget(self._addNearbyWorldsButton)
        if self._selectWithTravellerMapButton:
            buttonLayout.addWidget(self._selectWithTravellerMapButton)
        buttonLayout.addStretch()
        buttonLayout.addWidget(self._addWorldButton)
        buttonLayout.addWidget(self._removeWorldButton)
        buttonLayout.addWidget(self._removeAllWorldButton)

        widgetLayout = QtWidgets.QVBoxLayout()
        widgetLayout.setContentsMargins(0, 0, 0, 0)
        widgetLayout.addLayout(tableLayout)
        widgetLayout.addLayout(buttonLayout)

        self.setLayout(widgetLayout)

    def addWorld(self, world: traveller.World) -> None:
        if self._allowWorldCallback and not self._allowWorldCallback(world):
            return
        self._worldTable.addWorld(world=world)
        self.contentChanged.emit()

    def addWorlds(self, worlds: typing.Iterable[traveller.World]) -> None:
        if self._allowWorldCallback:
            filteredWorlds = []
            for world in worlds:
                if not self._allowWorldCallback(world):
                    continue
                filteredWorlds.append(world)
            if not filteredWorlds:
                return # Nothing to do
            self._worldTable.addWorlds(worlds=filteredWorlds)
        else:
            self._worldTable.addWorlds(worlds=worlds)

        self.contentChanged.emit()

    def removeWorld(self, world: traveller.World) -> bool:
        removed = self._worldTable.removeWorld(world=world)
        if removed:
            self.contentChanged.emit()
        return removed

    def removeAllWorlds(self) -> None:
        if not self._worldTable.isEmpty():
            self._worldTable.removeAllRows()
            self.contentChanged.emit()

    def isEmpty(self) -> bool:
        return self._worldTable.isEmpty()

    def containsWorld(self, world: traveller.World) -> bool:
        return self._worldTable.containsWorld(world)

    def worldCount(self) -> int:
        return self._worldTable.rowCount()

    def world(self, row) -> typing.Optional[traveller.World]:
        return self._worldTable.world(row)

    def worlds(self) -> typing.List[traveller.World]:
        return self._worldTable.worlds()

    def worldAt(self, position: QtCore.QPoint) -> typing.Optional[traveller.World]:
        translated = self.mapToGlobal(position)
        translated = self._worldTable.viewport().mapFromGlobal(translated)
        return self._worldTable.worldAt(position=translated)

    def hasSelection(self) -> bool:
        return self._worldTable.hasSelection()

    def selectedWorlds(self) -> typing.List[traveller.World]:
        return self._worldTable.selectedWorlds()

    def removeSelectedWorlds(self) -> None:
        if self._worldTable.hasSelection():
            self._worldTable.removeSelectedRows()
            self.contentChanged.emit()

    def setRelativeWorld(
            self,
            world: typing.Optional[traveller.World]
            ) -> None:
        self._relativeWorld = world

    def displayMode(self) -> gui.WorldTableTabBar.DisplayMode:
        return self._displayModeTabs.currentDisplayMode()

    def setVisibleColumns(
            self,
            columns: typing.List[gui.WorldTable.ColumnType]
            ) -> None:
        self._worldTable.setVisibleColumns(columns=columns)

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(WorldTableManagerWidget._StateVersion)

        tabState = self._displayModeTabs.saveState()
        stream.writeUInt32(tabState.count() if tabState else 0)
        if tabState:
            stream.writeRawData(tabState.data())

        tableState = self._worldTable.saveState()
        stream.writeUInt32(tableState.count() if tableState else 0)
        if tableState:
            stream.writeRawData(tableState.data())

        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != WorldTableManagerWidget._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore WorldTableManagerWidget state (Incorrect version)')
            return False

        result = True

        count = stream.readUInt32()
        if count > 0:
            tabState = QtCore.QByteArray(stream.readRawData(count))
            if not self._displayModeTabs.restoreState(tabState):
                result = False

        count = stream.readUInt32()
        if count > 0:
            tableState = QtCore.QByteArray(stream.readRawData(count))
            if not self._worldTable.restoreState(tableState):
                result = False

        return result

    def saveContent(self) -> QtCore.QByteArray:
        return self._worldTable.saveContent()

    def restoreContent(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        return self._worldTable.restoreContent(state=state)

    def enableContextMenuEvent(self, enable: bool = True) -> None:
        self._enableContextMenuEvent = enable

    def enableDisplayModeChangedEvent(self, enable: bool = True) -> None:
        self._enableDisplayModeChangedEvent = enable

    def enableShowInTravellerMapEvent(self, enable: bool = True) -> None:
        self._enableShowInTravellerMapEvent = enable

    def promptAddNearbyWorlds(
            self,
            initialWorld: typing.Optional[traveller.World] = None
            ) -> None:
        dlg = gui.NearbyWorldsDialog(parent=self)
        dlg.setWorld(world=initialWorld if initialWorld else self._relativeWorld)
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return

        searchWorld = dlg.world()
        searchRadius = dlg.searchRadius()

        try:
            worlds = traveller.WorldManager.instance().worldsInArea(
                center=searchWorld.hexPosition(),
                searchRadius=searchRadius)
        except Exception as ex:
            message = 'Failed to find nearby worlds'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

        if not worlds:
            gui.AutoSelectMessageBox.information(
                parent=self,
                text='No nearby worlds found.',
                stateKey='WorldTableNoNearbyWorldsFound')
            return

        self.addWorlds(worlds=worlds)

    def promptSelectWithTravellerMap(self) -> None:
        currentWorlds = self.worlds()
        if not self._worldSelectDialog:
            self._worldSelectDialog = gui.TravellerMapSelectDialog(parent=self)
            self._worldSelectDialog.setSingleSelect(False)
        self._worldSelectDialog.setSelectedWorlds(currentWorlds)
        if self._worldSelectDialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return

        newWorlds = self._worldSelectDialog.selectedWorlds()
        updated = False

        sortingEnabled = self._worldTable.isSortingEnabled()
        self._worldTable.setSortingEnabled(False)

        try:
            # Remove worlds that are no longer selected
            for world in currentWorlds:
                if world not in newWorlds:
                    self._worldTable.removeWorld(world=world)
                    updated = True

            # Add newly selected worlds
            for world in newWorlds:
                if world not in currentWorlds:
                    if self._allowWorldCallback and not self._allowWorldCallback(world):
                        # Silently ignore worlds that are filtered out
                        continue

                    self._worldTable.addWorld(world=world)
                    updated = True
        finally:
            self._worldTable.setSortingEnabled(sortingEnabled)

        if updated:
            self.contentChanged.emit()

    def promptAddWorld(self) -> None:
        dlg = gui.WorldSearchDialog(parent=self)
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        self.addWorld(dlg.world())

    def _displayColumns(self) -> typing.List[gui.WorldTable.ColumnType]:
        displayMode = self._displayModeTabs.currentDisplayMode()
        if displayMode == gui.WorldTableTabBar.DisplayMode.AllColumns:
            return self._worldTable.AllColumns
        elif displayMode == gui.WorldTableTabBar.DisplayMode.SystemColumns:
            return self._worldTable.SystemColumns
        elif displayMode == gui.WorldTableTabBar.DisplayMode.UWPColumns:
            return self._worldTable.UWPColumns
        elif displayMode == gui.WorldTableTabBar.DisplayMode.EconomicsColumns:
            return self._worldTable.EconomicsColumns
        elif displayMode == gui.WorldTableTabBar.DisplayMode.CultureColumns:
            return self._worldTable.CultureColumns
        elif displayMode == gui.WorldTableTabBar.DisplayMode.RefuellingColumns:
            return self._worldTable.RefuellingColumns
        else:
            assert(False) # I missed a case

    def _showWorldDetails(
            self,
            worlds: typing.Iterable[traveller.World]
            ) -> None:
        detailsWindow = gui.WindowManager.instance().showWorldDetailsWindow()
        detailsWindow.addWorlds(worlds=worlds)

    def _showWorldsInTravellerMap(
            self,
            worlds: typing.Iterable[traveller.World]
            ) -> None:
        if self._enableShowInTravellerMapEvent:
            self.showInTravellerMap.emit(worlds)
            return

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

    def _showWorldTableContextMenu(self, position: QtCore.QPoint) -> None:
        if self._enableContextMenuEvent:
            translated = self._worldTable.viewport().mapToGlobal(position)
            translated = self.mapFromGlobal(translated)
            self.contextMenuRequested.emit(translated)
            return

        world = self._worldTable.worldAt(position=position)

        menuItems = [
            gui.MenuItem(
                text='Select Worlds with Traveller Map...',
                callback=lambda: self.promptSelectWithTravellerMap(),
                enabled=True
            ),
            None, # Separator
            gui.MenuItem(
                text='Add World...',
                callback=lambda: self.promptAddWorld(),
                enabled=True
            ),
            gui.MenuItem(
                text='Add Nearby Worlds...',
                callback=lambda: self.promptAddNearbyWorlds(initialWorld=world),
                enabled=True,
                displayed=self._addNearbyWorldsButton != None
            ),
            gui.MenuItem(
                text='Remove Selected Worlds',
                callback=lambda: self.removeSelectedWorlds(),
                enabled=self._worldTable.hasSelection()
            ),
            gui.MenuItem(
                text='Remove All Worlds',
                callback=lambda: self.removeAllWorlds(),
                enabled=not self._worldTable.isEmpty()
            ),
            None, # Separator
            gui.MenuItem(
                text='Show Selected World Details...',
                callback=lambda: self._showWorldDetails(self._worldTable.selectedWorlds()),
                enabled=self._worldTable.hasSelection()
            ),
            gui.MenuItem(
                text='Show All World Details...',
                callback=lambda: self._showWorldDetails(self._worldTable.worlds()),
                enabled=not self._worldTable.isEmpty()
            ),
            None, # Separator
            gui.MenuItem(
                text='Show Selected Worlds in Traveller Map...',
                callback=lambda: self._showWorldsInTravellerMap(self._worldTable.selectedWorlds()),
                enabled=self._worldTable.hasSelection()
            ),
            gui.MenuItem(
                text='Show All Worlds in Traveller Map...',
                callback=lambda: self._showWorldsInTravellerMap(self._worldTable.worlds()),
                enabled=not self._worldTable.isEmpty()
            )
        ]

        gui.displayMenu(
            self,
            menuItems,
            self._worldTable.viewport().mapToGlobal(position)
        )

    def _worldTableKeyPressed(self, key: int) -> None:
        if key == QtCore.Qt.Key.Key_Delete:
            self.removeSelectedWorlds()

    def _displayModeChanged(self, index: int) -> None:
        if self._enableDisplayModeChangedEvent:
            self.displayModeChanged.emit(self._displayModeTabs.currentDisplayMode())
            return

        self._worldTable.setVisibleColumns(self._displayColumns())
