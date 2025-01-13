import gui
import logging
import traveller
import travellermap
import typing
from PyQt5 import QtWidgets, QtCore

class HexTableManagerWidget(QtWidgets.QWidget):
    contentChanged = QtCore.pyqtSignal()
    contextMenuRequested = QtCore.pyqtSignal(QtCore.QPoint)
    displayModeChanged = QtCore.pyqtSignal(gui.HexTableTabBar.DisplayMode)
    showInTravellerMap = QtCore.pyqtSignal([list])

    _StateVersion = 'HexTableManagerWidget_v1'

    def __init__(
            self,
            allowHexCallback: typing.Optional[typing.Callable[[travellermap.HexPosition], bool]] = None,
            isOrderedList: bool = False,
            hexTable: typing.Optional[gui.HexTable] = None,
            displayModeTabs: typing.Optional[gui.HexTableTabBar] = None
            ) -> None:
        super().__init__()

        self._allowHexCallback = allowHexCallback
        self._isOrderedList = isOrderedList
        self._relativeHex = None
        self._enableContextMenuEvent = False
        self._enableDisplayModeChangedEvent = False
        self._enableShowInTravellerMapEvent = False
        self._enableDeadSpace = False

        # Instance of dialogs are created on demand then maintained. This is
        # done to prevent the web widget being recreated
        self._locationSelectDialog: typing.Optional[gui.TravellerMapSelectDialog] = None
        self._radiusSelectDialog: typing.Optional[gui.HexRadiusSelectDialog] = None

        self._displayModeTabs = displayModeTabs
        if not self._displayModeTabs:
            self._displayModeTabs = gui.HexTableTabBar()
        self._displayModeTabs.currentChanged.connect(self._displayModeChanged)

        self._hexTable = hexTable
        if not self._hexTable:
            self._hexTable = gui.HexTable()
        self._hexTable.setActiveColumns(self._displayColumns())
        self._hexTable.setMinimumHeight(100)
        self._hexTable.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self._hexTable.customContextMenuRequested.connect(self._showTableContextMenu)
        self._hexTable.keyPressed.connect(self._tableKeyPressed)
        if self._isOrderedList:
            # Disable sorting on if the list is to be ordered
            self._hexTable.setSortingEnabled(False)

        tableLayout = QtWidgets.QVBoxLayout()
        tableLayout.setContentsMargins(0, 0, 0 , 0)
        tableLayout.setSpacing(0) # No gap between tabs and table
        tableLayout.addWidget(self._displayModeTabs)
        tableLayout.addWidget(self._hexTable)

        self._moveSelectionUpButton = None
        self._moveSelectionDownButton = None
        if self._isOrderedList:
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

        self._addLocationsButton = QtWidgets.QPushButton('Add...')
        self._addLocationsButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)
        self._addLocationsButton.clicked.connect(self.promptAddLocations)

        self._addNearbyButton = None
        if not self._isOrderedList:
            # Adding multiple hexes as one time doesn't really make sense for
            # ordered list
            self._addNearbyButton = QtWidgets.QPushButton('Add Nearby...')
            self._addNearbyButton.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Minimum,
                QtWidgets.QSizePolicy.Policy.Minimum)
            self._addNearbyButton.clicked.connect(self.promptAddNearby)

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
        buttonLayout.addStretch()
        buttonLayout.addWidget(self._addLocationsButton)
        if self._addNearbyButton:
            buttonLayout.addWidget(self._addNearbyButton)
        buttonLayout.addWidget(self._removeButton)
        buttonLayout.addWidget(self._removeAllButton)

        widgetLayout = QtWidgets.QVBoxLayout()
        widgetLayout.setContentsMargins(0, 0, 0, 0)
        widgetLayout.addLayout(tableLayout)
        widgetLayout.addLayout(buttonLayout)

        self.setLayout(widgetLayout)

    def addHex(
            self,
            hex: typing.Union[travellermap.HexPosition, traveller.World]
            ) -> None:
        if isinstance(hex, traveller.World):
            hex = hex.hex()
        if self._allowHexCallback:
            if not self._allowHexCallback(hex):
                return
        self._hexTable.addHex(hex)
        self.contentChanged.emit()

    def addWorld(self, world: traveller.World) -> None:
        self.addHex(world)

    def addHexes(
            self,
            hexes: typing.Iterable[
                typing.Union[travellermap.HexPosition, traveller.World]
                ]) -> None:
        if self._allowHexCallback:
            filteredHexes = []
            for hex in hexes:
                if isinstance(hex, traveller.World):
                    hex = hex.hex()
                if not self._allowHexCallback(hex):
                    continue
                filteredHexes.append(hex)
            if not filteredHexes:
                return # Nothing to do
            self._hexTable.addHexes(hexes=filteredHexes)
        else:
            self._hexTable.addHexes(hexes=hexes)

        self.contentChanged.emit()

    def addWorlds(self, worlds: typing.Iterable[traveller.World]) -> None:
        self.addHexes(hexes=worlds)

    def removeHex(
            self,
            hex: typing.Union[travellermap.HexPosition, traveller.World]
            ) -> bool:
        removed = self._hexTable.removeHex(hex)
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
            hex: typing.Union[travellermap.HexPosition, traveller.World]
            ) -> bool:
        return self._hexTable.containsHex(hex)

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

    # NOTE: Indexing into the list of returned worlds does not match
    # table row indexing if the table contains dead space hexes.
    def worlds(self) -> typing.List[traveller.World]:
        return self._hexTable.worlds()

    def rowAt(self, y: int) -> int:
        translated = self.mapToGlobal(QtCore.QPoint(self.x(), y))
        translated = self._hexTable.viewport().mapFromGlobal(translated)
        return self._hexTable.rowAt(translated.y())

    def hexAt(self, y: int) -> typing.Optional[travellermap.HexPosition]:
        row = self.rowAt(y)
        return self.hex(row) if row >= 0 else None

    def worldAt(self, y: int) -> typing.Optional[traveller.World]:
        row = self.rowAt(y)
        return self.world(row) if row >= 0 else None

    def hasSelection(self) -> bool:
        return self._hexTable.hasSelection()

    def selectedHexes(self) -> typing.List[travellermap.HexPosition]:
        return self._hexTable.selectedHexes()

    # NOTE: Indexing into the list of returned worlds does not match table
    # selection indexing if the selection contains dead space hexes.
    def selectedWorlds(self) -> typing.List[traveller.World]:
        return self._hexTable.selectedWorlds()

    def removeSelectedRows(self) -> None:
        if self._hexTable.hasSelection():
            self._hexTable.removeSelectedRows()
            self.contentChanged.emit()

    def setRelativeHex(
            self,
            hex: typing.Union[travellermap.HexPosition, traveller.World]
            ) -> None:
        if isinstance(hex, traveller.World):
            hex = hex.hex()
        self._relativeHex = hex

    def setRelativeWorld(
            self,
            world: traveller.World
            ) -> None:
        self.setRelativeHex(world)

    def displayMode(self) -> gui.HexTableTabBar.DisplayMode:
        return self._displayModeTabs.currentDisplayMode()

    def setActiveColumns(
            self,
            columns: typing.List[gui.HexTable.ColumnType]
            ) -> None:
        self._hexTable.setActiveColumns(columns=columns)

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

    def isContextMenuEventEnabled(self) -> bool:
        return self._enableContextMenuEvent

    def enableDisplayModeChangedEvent(self, enable: bool = True) -> None:
        self._enableDisplayModeChangedEvent = enable

    def isDisplayModeChangedEventEnabled(self) -> bool:
        return self._enableDisplayModeChangedEvent

    def enableShowInTravellerMapEvent(self, enable: bool = True) -> None:
        self._enableShowInTravellerMapEvent = enable

    def isShowInTravellerMapEventEnabled(self) -> bool:
        return self._enableShowInTravellerMapEvent

    def enableDeadSpace(self, enable: bool) -> None:
        self._enableDeadSpace = enable

        if self._radiusSelectDialog:
            self._radiusSelectDialog.enableDeadSpaceSelection(
                enable=enable)

        if self._locationSelectDialog:
            self._locationSelectDialog.configureSelection(
                singleSelect=self._isOrderedList,
                includeDeadSpace=enable)

        if not enable:
            # Dead space hexes are not allowed so remove any that are already in
            # the table
            for row in range(self._hexTable.rowCount() - 1, -1, -1):
                world = traveller.WorldManager.instance().worldByPosition(
                    hex=self.hex(row=row))
                if not world:
                    self._hexTable.removeRow(row=row)

    def isDeadSpaceEnabled(self) -> bool:
        return self._enableDeadSpace

    def promptAddLocations(self) -> None:
        currentHexes = self.hexes()

        if not self._locationSelectDialog:
            self._locationSelectDialog = gui.TravellerMapSelectDialog(parent=self)
            self._locationSelectDialog.configureSelection(
                singleSelect=self._isOrderedList,
                includeDeadSpace=self._enableDeadSpace)

        self._locationSelectDialog.clearSelectedHexes()

        # If it's not an ordered list that is being managed then the dialog should
        # show the current table contents and allow the user to select more hexes or
        # unselect currently selected ones to have them removed from the table. If
        # we are dealing with an ordered list the dialog is just used to select a
        # new world that should be added to the table, in which case the current
        # table contents are not shown.
        if not self._isOrderedList:
            for hex in currentHexes:
                self._locationSelectDialog.selectHex(hex=hex, centerOnHex=False)

        if self._locationSelectDialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return

        newHexes = self._locationSelectDialog.selectedHexes()
        updated = False

        sortingEnabled = self._hexTable.isSortingEnabled()
        self._hexTable.setSortingEnabled(False)

        try:
            # Remove hexes that are no longer selected. This only needs to be
            # done when not managing an ordered list when the dialog shows the
            # current table contents and allows the user to deselect as well as
            # select
            if not self._isOrderedList:
                for hex in currentHexes:
                    if hex not in newHexes:
                        self._hexTable.removeHex(hex)
                        updated = True

            # Add newly selected hexes
            for hex in newHexes:
                if hex not in currentHexes:
                    if self._allowHexCallback and not self._allowHexCallback(hex):
                        # Silently ignore worlds that are filtered out
                        continue

                    self._hexTable.addHex(hex)
                    updated = True
        finally:
            self._hexTable.setSortingEnabled(sortingEnabled)

        if updated:
            self.contentChanged.emit()

    def promptAddNearby(
            self,
            initialHex: typing.Optional[typing.Union[
                travellermap.HexPosition,
                traveller.World
                ]] = None
            ) -> None:
        if isinstance(initialHex, traveller.World):
            initialHex = initialHex.hex()

        if not self._radiusSelectDialog:
            self._radiusSelectDialog = gui.HexRadiusSelectDialog()
            self._radiusSelectDialog.enableDeadSpaceSelection(
                enable=self._enableDeadSpace)
        self._radiusSelectDialog.setCenterHex(
            hex=initialHex if initialHex else self._relativeHex)
        if self._radiusSelectDialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return

        self.addHexes(hexes=self._radiusSelectDialog.selectedHexes())

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

    def _showDetails(
            self,
            hexes: typing.Iterable[travellermap.HexPosition]
            ) -> None:
        detailsWindow = gui.WindowManager.instance().showWorldDetailsWindow()
        detailsWindow.addHexes(hexes=hexes)

    def _showInTravellerMap(
            self,
            hexes: typing.Iterable[travellermap.HexPosition]
            ) -> None:
        if self._enableShowInTravellerMapEvent:
            self.showInTravellerMap.emit(hexes)
            return

        try:
            mapWindow = gui.WindowManager.instance().showTravellerMapWindow()
            mapWindow.clearOverlays()
            mapWindow.highlightHexes(hexes=hexes)
        except Exception as ex:
            message = 'Failed to show world(s) in Traveller Map'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)

    def _showTableContextMenu(self, point: QtCore.QPoint) -> None:
        if self._enableContextMenuEvent:
            translated = self._hexTable.viewport().mapToGlobal(point)
            translated = self.mapFromGlobal(translated)
            self.contextMenuRequested.emit(translated)
            return

        clickedHex = self._hexTable.hexAt(point.y())

        menuItems = []

        menuItems.append(gui.MenuItem(
            text='Add...',
            callback=lambda: self.promptAddLocations(),
            enabled=True))
        if not self._isOrderedList:
            menuItems.append(gui.MenuItem(
                text='Add Nearby...',
                callback=lambda: self.promptAddNearby(initialHex=clickedHex),
                enabled=True,
                displayed=self._addNearbyButton != None))
        menuItems.append(None) # Separator

        menuItems.append(gui.MenuItem(
            text='Remove Selected',
            callback=lambda: self.removeSelectedRows(),
            enabled=self._hexTable.hasSelection()))
        menuItems.append(gui.MenuItem(
            text='Remove All',
            callback=lambda: self.removeAllRows(),
            enabled=not self._hexTable.isEmpty()))
        menuItems.append(None) # Separator

        menuItems.append(gui.MenuItem(
            text='Show Selection Details...',
            callback=lambda: self._showDetails(self._hexTable.selectedHexes()),
            enabled=self._hexTable.hasSelection()))
        menuItems.append(gui.MenuItem(
            text='Show All Details...',
            callback=lambda: self._showDetails(self._hexTable.hexes()),
            enabled=not self._hexTable.isEmpty()))
        menuItems.append(None) # Separator

        menuItems.append(gui.MenuItem(
            text='Show Selection in Traveller Map...',
            callback=lambda: self._showInTravellerMap(self._hexTable.selectedHexes()),
            enabled=self._hexTable.hasSelection()))
        menuItems.append(gui.MenuItem(
            text='Show All in Traveller Map...',
            callback=lambda: self._showInTravellerMap(self._hexTable.hexes()),
            enabled=not self._hexTable.isEmpty()))

        gui.displayMenu(
            self,
            menuItems,
            self._hexTable.viewport().mapToGlobal(point))

    def _tableKeyPressed(self, key: int) -> None:
        if key == QtCore.Qt.Key.Key_Delete:
            self.removeSelectedRows()

    def _displayModeChanged(self, index: int) -> None:
        if self._enableDisplayModeChangedEvent:
            self.displayModeChanged.emit(self._displayModeTabs.currentDisplayMode())
            return

        self._hexTable.setActiveColumns(self._displayColumns())
