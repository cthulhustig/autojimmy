import gui
import logging
import traveller
import travellermap
import typing
from PyQt5 import QtWidgets, QtCore

# TODO: Pretty much all the logic about removing world versions of functions
# in HexTable apply here as well
# TODO: I've never liked the name of this class, possibly a good time to
# rename it. It's more about letting the user select a group of hexes than
# manage them
class HexTableManagerWidget(QtWidgets.QWidget):
    contentChanged = QtCore.pyqtSignal()
    contextMenuRequested = QtCore.pyqtSignal(QtCore.QPoint)
    displayModeChanged = QtCore.pyqtSignal(gui.HexTableTabBar.DisplayMode)
    showInTravellerMap = QtCore.pyqtSignal([list])

    # TODO: I might need to leave this as the old 'WorldTableManagerWidget_v1'
    # for backwards compatibility
    _StateVersion = 'HexTableManagerWidget_v1'

    def __init__(
            self,
            # TODO: This should be updated to an allowed hex callback
            allowHexCallback: typing.Optional[typing.Callable[[traveller.World], bool]] = None,
            isOrderedList: bool = False,
            showAddNearbyWorldsButton: bool = True,
            showSelectInTravellerMapButton: bool = True,
            hexTable: typing.Optional[gui.HexTable] = None,
            displayModeTabs: typing.Optional[gui.HexTableTabBar] = None
            ) -> None:
        super().__init__()

        self._allowHexCallback = allowHexCallback
        self._relativeHex = None
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
            self._displayModeTabs = gui.HexTableTabBar()
        self._displayModeTabs.currentChanged.connect(self._displayModeChanged)

        self._hexTable = hexTable
        if not self._hexTable:
            self._hexTable = gui.HexTable()
        self._hexTable.setVisibleColumns(self._displayColumns())
        self._hexTable.setMinimumHeight(100)
        self._hexTable.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self._hexTable.customContextMenuRequested.connect(self._showHexTableContextMenu)
        self._hexTable.keyPressed.connect(self._hexTableKeyPressed)
        if isOrderedList:
            # Disable sorting on if the list is to be ordered
            self._hexTable.setSortingEnabled(False)

        tableLayout = QtWidgets.QVBoxLayout()
        tableLayout.setContentsMargins(0, 0, 0 , 0)
        tableLayout.setSpacing(0) # No gap between tabs and table
        tableLayout.addWidget(self._displayModeTabs)
        tableLayout.addWidget(self._hexTable)

        self._moveSelectionUpButton = None
        self._moveSelectionDownButton = None
        if isOrderedList:
            self._moveSelectionUpButton = QtWidgets.QToolButton()
            self._moveSelectionUpButton.setArrowType(QtCore.Qt.ArrowType.UpArrow)
            self._moveSelectionUpButton.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Minimum,
                QtWidgets.QSizePolicy.Policy.Minimum)
            self._moveSelectionUpButton.clicked.connect(self._hexTable.moveSelectionUp)

            self._moveSelectionDownButton = QtWidgets.QToolButton()
            self._moveSelectionDownButton.setArrowType(QtCore.Qt.ArrowType.DownArrow)
            self._moveSelectionDownButton.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Minimum,
                QtWidgets.QSizePolicy.Policy.Minimum)
            self._moveSelectionDownButton.clicked.connect(self._hexTable.moveSelectionDown)

            moveButtonLayout = QtWidgets.QVBoxLayout()
            moveButtonLayout.setContentsMargins(0, 0, 0 , 0)
            moveButtonLayout.addWidget(self._moveSelectionUpButton)
            moveButtonLayout.addWidget(self._moveSelectionDownButton)

            orderedTableLayout = QtWidgets.QHBoxLayout()
            orderedTableLayout.setContentsMargins(0, 0, 0 , 0)
            orderedTableLayout.addLayout(tableLayout)
            orderedTableLayout.addLayout(moveButtonLayout)

            tableLayout = orderedTableLayout

        self._addNearbyButton = None
        if showAddNearbyWorldsButton:
            self._addNearbyButton = QtWidgets.QPushButton('Add Nearby...')
            self._addNearbyButton.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Minimum,
                QtWidgets.QSizePolicy.Policy.Minimum)
            self._addNearbyButton.clicked.connect(self.promptAddNearbyWorlds)

        self._selectWithTravellerMapButton = None
        if showSelectInTravellerMapButton:
            self._selectWithTravellerMapButton = QtWidgets.QPushButton('Select with Traveller Map...')
            self._selectWithTravellerMapButton.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Minimum,
                QtWidgets.QSizePolicy.Policy.Minimum)
            self._selectWithTravellerMapButton.clicked.connect(self.promptSelectWithTravellerMap)

        self._addButton = QtWidgets.QPushButton('Add...')
        self._addButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)
        self._addButton.clicked.connect(self.promptAddHex)

        self._removeButton = QtWidgets.QPushButton('Remove')
        self._removeButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)
        self._removeButton.clicked.connect(self.removeSelectedRows)

        self._removeAllButton = QtWidgets.QPushButton('Remove All')
        self._removeAllButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)
        self._removeAllButton.clicked.connect(self.removeAllRows)

        buttonLayout = QtWidgets.QHBoxLayout()
        buttonLayout.setContentsMargins(0, 0, 0, 0)
        if self._addNearbyButton:
            buttonLayout.addWidget(self._addNearbyButton)
        if self._selectWithTravellerMapButton:
            buttonLayout.addWidget(self._selectWithTravellerMapButton)
        buttonLayout.addStretch()
        buttonLayout.addWidget(self._addButton)
        buttonLayout.addWidget(self._removeButton)
        buttonLayout.addWidget(self._removeAllButton)

        widgetLayout = QtWidgets.QVBoxLayout()
        widgetLayout.setContentsMargins(0, 0, 0, 0)
        widgetLayout.addLayout(tableLayout)
        widgetLayout.addLayout(buttonLayout)

        self.setLayout(widgetLayout)

    def addHex(
            self,
            pos: typing.Union[travellermap.HexPosition, traveller.World]
            ) -> None:
        if isinstance(pos, traveller.World):
            pos = pos.hexPosition()
        if self._allowHexCallback:
            if not self._allowHexCallback(pos):
                return
        self._hexTable.addHex(pos)
        self.contentChanged.emit()

    def addWorld(self, world: traveller.World) -> None:
        self.addHex(world)

    def addHexes(
            self,
            positions: typing.Iterable[
                typing.Union[travellermap.HexPosition, traveller.World]
                ]) -> None:
        if self._allowHexCallback:
            filteredPositions = []
            for pos in positions:
                if isinstance(pos, traveller.World):
                    pos = pos.hexPosition()
                if not self._allowHexCallback(pos):
                    continue
                filteredPositions.append(pos)
            if not filteredPositions:
                return # Nothing to do
            self._hexTable.addHexes(positions=filteredPositions)
        else:
            self._hexTable.addHexes(positions=positions)

        self.contentChanged.emit()

    def addWorlds(self, worlds: typing.Iterable[traveller.World]) -> None:
        self.addHexes(positions=worlds)

    def removeHex(
            self,
            pos: typing.Union[travellermap.HexPosition, traveller.World]
            ) -> bool:
        removed = self._hexTable.removeHex(pos)
        if removed:
            self.contentChanged.emit()
        return removed

    def removeWorld(self, world: traveller.World) -> bool:
        return self.removeHex(world)

    def removeAllRows(self) -> None:
        if not self._hexTable.isEmpty():
            self._hexTable.removeAllRows()
            self.contentChanged.emit()

    def isEmpty(self) -> bool:
        return self._hexTable.isEmpty()

    def containsHex(
            self,
            pos: typing.Union[travellermap.HexPosition, traveller.World]
            ) -> bool:
        return self._hexTable.containsHex(pos)

    def containsWorld(self, world: traveller.World) -> bool:
        return self.containsHex(world)

    def rowCount(self) -> int:
        return self._hexTable.rowCount()

    def hex(self, row: int) -> typing.Optional[travellermap.HexPosition]:
        return self._hexTable.hex(row=row)

    def world(self, row: int) -> typing.Optional[traveller.World]:
        return self._hexTable.world(row)

    def hexes(self) -> typing.List[travellermap.HexPosition]:
        return self._hexTable.hexes()

    def worlds(self) -> typing.List[traveller.World]:
        return self._hexTable.worlds()

    def hexAt(self, position: QtCore.QPoint) -> typing.List[travellermap.HexPosition]:
        translated = self.mapToGlobal(position)
        translated = self._hexTable.viewport().mapFromGlobal(translated)
        return self._hexTable.hexAt(position=translated)

    def worldAt(self, position: QtCore.QPoint) -> typing.Optional[traveller.World]:
        translated = self.mapToGlobal(position)
        translated = self._hexTable.viewport().mapFromGlobal(translated)
        return self._hexTable.worldAt(position=translated)

    def hasSelection(self) -> bool:
        return self._hexTable.hasSelection()

    def selectedHexes(self) -> typing.List[travellermap.HexPosition]:
        return self._hexTable.selectedHexes()

    def selectedWorlds(self) -> typing.List[traveller.World]:
        return self._hexTable.selectedWorlds()

    def removeSelectedRows(self) -> None:
        if self._hexTable.hasSelection():
            self._hexTable.removeSelectedRows()
            self.contentChanged.emit()

    def setRelativeHex(
            self,
            pos: typing.Union[travellermap.HexPosition, traveller.World]
            ) -> None:
        if isinstance(pos, traveller.World):
            pos = pos.hexPosition()
        self._relativeHex = pos

    def displayMode(self) -> gui.HexTableTabBar.DisplayMode:
        return self._displayModeTabs.currentDisplayMode()

    def setVisibleColumns(
            self,
            columns: typing.List[gui.HexTable.ColumnType]
            ) -> None:
        self._hexTable.setVisibleColumns(columns=columns)

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(HexTableManagerWidget._StateVersion)

        tabState = self._displayModeTabs.saveState()
        stream.writeUInt32(tabState.count() if tabState else 0)
        if tabState:
            stream.writeRawData(tabState.data())

        tableState = self._hexTable.saveState()
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
        if version != HexTableManagerWidget._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore HexTableManagerWidget state (Incorrect version)')
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
            if not self._hexTable.restoreState(tableState):
                result = False

        return result

    def saveContent(self) -> QtCore.QByteArray:
        return self._hexTable.saveContent()

    def restoreContent(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        return self._hexTable.restoreContent(state=state)

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
        dlg = gui.HexSearchRadiusDialog(parent=self)
        dlg.setCenterHex(pos=initialWorld.hexPosition() if initialWorld else self._relativeHex)
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return

        try:
            worlds = traveller.WorldManager.instance().worldsInArea(
                center=dlg.centerHex(),
                searchRadius=dlg.searchRadius())
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
                stateKey='HexTableNoNearbyWorldsFound')
            return

        self.addWorlds(worlds=worlds)

    def promptSelectWithTravellerMap(self) -> None:
        # TODO: Need to switch this to use hexes
        gui.MessageBoxEx.critical(
            parent=self,
            text='Implement me!')
        return

        currentWorlds = self.worlds()
        if not self._worldSelectDialog:
            self._worldSelectDialog = gui.TravellerMapSelectDialog(parent=self)
            self._worldSelectDialog.setSingleSelect(False)
        self._worldSelectDialog.setSelectedWorlds(currentWorlds)
        if self._worldSelectDialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return

        newWorlds = self._worldSelectDialog.selectedWorlds()
        updated = False

        sortingEnabled = self._hexTable.isSortingEnabled()
        self._hexTable.setSortingEnabled(False)

        try:
            # Remove worlds that are no longer selected
            for world in currentWorlds:
                if world not in newWorlds:
                    self._hexTable.removeWorld(world=world)
                    updated = True

            # Add newly selected worlds
            for world in newWorlds:
                if world not in currentWorlds:
                    if self._allowHexCallback and not self._allowHexCallback(world):
                        # Silently ignore worlds that are filtered out
                        continue

                    self._hexTable.addWorld(world=world)
                    updated = True
        finally:
            self._hexTable.setSortingEnabled(sortingEnabled)

        if updated:
            self.contentChanged.emit()

    def promptAddHex(self) -> None:
        dlg = gui.HexSearchDialog(parent=self)
        dlg.enableDeadSpaceSelection(enable=False) # TODO: This should be configurable
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        self.addHex(dlg.selectedHex())

    def _displayColumns(self) -> typing.List[gui.HexTable.ColumnType]:
        displayMode = self._displayModeTabs.currentDisplayMode()
        if displayMode == gui.HexTableTabBar.DisplayMode.AllColumns:
            return self._hexTable.AllColumns
        elif displayMode == gui.HexTableTabBar.DisplayMode.SystemColumns:
            return self._hexTable.SystemColumns
        elif displayMode == gui.HexTableTabBar.DisplayMode.UWPColumns:
            return self._hexTable.UWPColumns
        elif displayMode == gui.HexTableTabBar.DisplayMode.EconomicsColumns:
            return self._hexTable.EconomicsColumns
        elif displayMode == gui.HexTableTabBar.DisplayMode.CultureColumns:
            return self._hexTable.CultureColumns
        elif displayMode == gui.HexTableTabBar.DisplayMode.RefuellingColumns:
            return self._hexTable.RefuellingColumns
        else:
            assert(False) # I missed a case

    def _showWorldDetails(
            self,
            worlds: typing.Iterable[traveller.World]
            ) -> None:
        # TODO: Need to switch this to use hexes
        gui.MessageBoxEx.critical(
            parent=self,
            text='Implement me!')
        return

        detailsWindow = gui.WindowManager.instance().showWorldDetailsWindow()
        detailsWindow.addWorlds(worlds=worlds)

    def _showWorldsInTravellerMap(
            self,
            positions: typing.Iterable[travellermap.HexPosition]
            ) -> None:
        if self._enableShowInTravellerMapEvent:
            self.showInTravellerMap.emit(positions)
            return

        try:
            mapWindow = gui.WindowManager.instance().showTravellerMapWindow()
            mapWindow.centerOnHexes(
                positions=positions,
                clearOverlays=True,
                highlightHexes=True)
        except Exception as ex:
            message = 'Failed to show world(s) in Traveller Map'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)

    # TODO: The menu option text for this menu need updated
    def _showHexTableContextMenu(self, position: QtCore.QPoint) -> None:
        if self._enableContextMenuEvent:
            translated = self._hexTable.viewport().mapToGlobal(position)
            translated = self.mapFromGlobal(translated)
            self.contextMenuRequested.emit(translated)
            return

        world = self._hexTable.worldAt(position=position)

        menuItems = [
            gui.MenuItem(
                text='Select Worlds with Traveller Map...',
                callback=lambda: self.promptSelectWithTravellerMap(),
                enabled=True
            ),
            None, # Separator
            gui.MenuItem(
                text='Add World...',
                callback=lambda: self.promptAddHex(),
                enabled=True
            ),
            gui.MenuItem(
                text='Add Nearby Worlds...',
                callback=lambda: self.promptAddNearbyWorlds(initialWorld=world),
                enabled=True,
                displayed=self._addNearbyButton != None
            ),
            gui.MenuItem(
                text='Remove Selected Worlds',
                callback=lambda: self.removeSelectedRows(),
                enabled=self._hexTable.hasSelection()
            ),
            gui.MenuItem(
                text='Remove All Worlds',
                callback=lambda: self.removeAllRows(),
                enabled=not self._hexTable.isEmpty()
            ),
            None, # Separator
            gui.MenuItem(
                text='Show Selected World Details...',
                callback=lambda: self._showWorldDetails(self._hexTable.selectedWorlds()),
                enabled=self._hexTable.hasSelection()
            ),
            gui.MenuItem(
                text='Show All World Details...',
                callback=lambda: self._showWorldDetails(self._hexTable.worlds()),
                enabled=not self._hexTable.isEmpty()
            ),
            None, # Separator
            gui.MenuItem(
                text='Show Selected Worlds in Traveller Map...',
                callback=lambda: self._showWorldsInTravellerMap(self._hexTable.selectedHexes()),
                enabled=self._hexTable.hasSelection()
            ),
            gui.MenuItem(
                text='Show All Worlds in Traveller Map...',
                callback=lambda: self._showWorldsInTravellerMap(self._hexTable.hexes()),
                enabled=not self._hexTable.isEmpty()
            )
        ]

        gui.displayMenu(
            self,
            menuItems,
            self._hexTable.viewport().mapToGlobal(position)
        )

    def _hexTableKeyPressed(self, key: int) -> None:
        if key == QtCore.Qt.Key.Key_Delete:
            self.removeSelectedRows()

    def _displayModeChanged(self, index: int) -> None:
        if self._enableDisplayModeChangedEvent:
            self.displayModeChanged.emit(self._displayModeTabs.currentDisplayMode())
            return

        self._hexTable.setVisibleColumns(self._displayColumns())
