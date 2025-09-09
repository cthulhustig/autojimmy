import app
import enum
import gui
import logging
import logic
import traveller
import travellermap
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

class HexTableManagerWidget(QtWidgets.QWidget):
    contentChanged = QtCore.pyqtSignal()

    class MenuAction(enum.Enum):
        AddLocation = enum.auto()
        AddNearby = enum.auto()
        RemoveSelected = enum.auto()
        RemoveAll = enum.auto()

    _StateVersion = 'HexTableManagerWidget_v1'

    def __init__(
            self,
            milieu: travellermap.Milieu,
            rules: traveller.Rules,
            mapStyle: travellermap.MapStyle,
            mapOptions: typing.Iterable[travellermap.MapOption],
            mapRendering: app.MapRendering,
            mapAnimations: bool,
            worldTagging: typing.Optional[logic.WorldTagging] = None,
            taggingColours: typing.Optional[app.TaggingColours] = None,
            allowHexCallback: typing.Optional[typing.Callable[[travellermap.HexPosition], bool]] = None,
            isOrderedList: bool = False,
            hexTable: typing.Optional[gui.HexTable] = None,
            displayModeTabs: typing.Optional[gui.HexTableTabBar] = None
            ) -> None:
        super().__init__()

        self._milieu = milieu
        self._rules = traveller.Rules(rules)
        self._mapStyle = mapStyle
        self._mapOptions = set(mapOptions) # Use a set for easy checking for differences
        self._mapRendering = mapRendering
        self._mapAnimations = mapAnimations
        self._worldTagging = logic.WorldTagging(worldTagging) if worldTagging else None
        self._taggingColours = app.TaggingColours(taggingColours) if taggingColours else None
        self._allowHexCallback = allowHexCallback
        self._isOrderedList = isOrderedList
        self._relativeHex = None
        self._enableDeadSpace = False

        self._displayModeTabs = displayModeTabs
        if not self._displayModeTabs:
            self._displayModeTabs = gui.HexTableTabBar()
        self._displayModeTabs.currentChanged.connect(self._displayModeChanged)

        self._hexTable = hexTable
        if not self._hexTable:
            self._hexTable = gui.HexTable(
                milieu=self._milieu,
                rules=self._rules,
                worldTagging=self._worldTagging,
                taggingColours=self._taggingColours)
        else:
            self._hexTable.setMilieu(milieu=self._milieu)
            self._hexTable.setRules(rules=self._rules)
            self._hexTable.setWorldTagging(tagging=self._worldTagging)
            self._hexTable.setTaggingColours(colours=self._taggingColours)
        self._hexTable.setActiveColumns(self._displayColumns())
        self._hexTable.setMinimumHeight(100)
        self._hexTable.installEventFilter(self)
        self._hexTable.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.NoContextMenu)
        self._hexTable.itemSelectionChanged.connect(self._tableSelectionChanged)
        # Disable sorting if the list is to be ordered
        self._hexTable.setSortingEnabled(not self._isOrderedList)

        addLocationAction = QtWidgets.QAction('Add...', self)
        addLocationAction.triggered.connect(self.promptAddLocation)
        self._hexTable.setMenuAction(HexTableManagerWidget.MenuAction.AddLocation, addLocationAction)

        addNearbyAction = QtWidgets.QAction('Add Nearby...', self)
        addNearbyAction.setVisible(not self._isOrderedList)
        addNearbyAction.triggered.connect(self.promptAddNearby)
        self._hexTable.setMenuAction(HexTableManagerWidget.MenuAction.AddNearby, addNearbyAction)

        removeSelectionAction = QtWidgets.QAction('Remove', self)
        removeSelectionAction.setEnabled(False) # No selection
        removeSelectionAction.triggered.connect(self.removeSelectedRows)
        self._hexTable.setMenuAction(HexTableManagerWidget.MenuAction.RemoveSelected, removeSelectionAction)

        removeAllAction = QtWidgets.QAction('Remove All', self)
        removeAllAction.setEnabled(False) # No content
        removeAllAction.triggered.connect(self.removeAllRows)
        self._hexTable.setMenuAction(HexTableManagerWidget.MenuAction.RemoveAll, removeAllAction)

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

        self._addLocationsButton = gui.ActionButton(
            action=addLocationAction)
        self._addLocationsButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)

        self._addNearbyButton = None
        if not self._isOrderedList:
            # Adding multiple hexes as one time doesn't really make sense for
            # ordered list
            self._addNearbyButton = gui.ActionButton(
                action=addNearbyAction)
            self._addNearbyButton.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Minimum,
                QtWidgets.QSizePolicy.Policy.Minimum)

        self._removeSelectionButton = gui.ActionButton(
            action=removeSelectionAction,
            text='Remove')
        self._removeSelectionButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)

        self._removeAllButton = gui.ActionButton(
            action=removeAllAction)
        self._removeAllButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)

        buttonLayout = QtWidgets.QHBoxLayout()
        buttonLayout.setContentsMargins(0, 0, 0, 0)
        buttonLayout.addStretch()
        buttonLayout.addWidget(self._addLocationsButton)
        if self._addNearbyButton:
            buttonLayout.addWidget(self._addNearbyButton)
        buttonLayout.addWidget(self._removeSelectionButton)
        buttonLayout.addWidget(self._removeAllButton)

        widgetLayout = QtWidgets.QVBoxLayout()
        widgetLayout.setContentsMargins(0, 0, 0, 0)
        widgetLayout.addLayout(tableLayout)
        widgetLayout.addLayout(buttonLayout)

        self.setLayout(widgetLayout)
        self.installEventFilter(self)

    def milieu(self) -> travellermap.Milieu:
        return self._milieu

    def setMilieu(self, milieu: travellermap.Milieu) -> None:
        if milieu is self._milieu:
            return
        self._milieu = milieu
        self._hexTable.setMilieu(milieu=self._milieu)

    def rules(self) -> traveller.Rules:
        return traveller.Rules(self._rules)

    def setRules(self, rules: traveller.Rules) -> None:
        if rules == self._rules:
            return

        self._rules = traveller.Rules(rules)
        self._hexTable.setRules(rules=self._rules)

    def mapStyle(self) -> travellermap.MapStyle:
        return self._mapStyle

    def setMapStyle(self, style: travellermap.MapStyle) -> None:
        if style == self._mapStyle:
            return
        self._mapStyle = style

    def mapOptions(self) -> typing.Iterable[travellermap.MapOption]:
        return list(self._mapStyle)

    def setMapOptions(self, options: typing.Iterable[travellermap.MapOption]) -> None:
        options = set(options) # Force use of set so options can be compared
        if options == self._mapOptions:
            return
        self._mapOptions = options

    def mapRendering(self) -> app.MapRendering:
        return self._mapRendering

    def setMapRendering(self, rendering: app.MapRendering):
        if rendering == self._mapRendering:
            return
        self._mapRendering = rendering

    def mapAnimations(self) -> bool:
        return self._mapAnimations

    def setMapAnimations(self, enabled: bool) -> None:
        if enabled == self._mapAnimations:
            return
        self._mapAnimations = enabled

    def worldTagging(self) -> typing.Optional[logic.WorldTagging]:
        return logic.WorldTagging(self._worldTagging) if self._worldTagging else None

    def setWorldTagging(
            self,
            tagging: typing.Optional[logic.WorldTagging],
            ) -> None:
        if tagging == self._worldTagging:
            return
        self._worldTagging = logic.WorldTagging(tagging) if tagging else None
        self._hexTable.setWorldTagging(tagging=self._worldTagging)

    def taggingColours(self) -> typing.Optional[app.TaggingColours]:
        return app.TaggingColours(self._taggingColours) if self._taggingColours else None

    def setTaggingColours(
            self,
            colours: typing.Optional[app.TaggingColours]
            ) -> None:
        if colours == self._taggingColours:
            return
        self._taggingColours = app.TaggingColours(colours) if colours else None
        self._hexTable.setTaggingColours(colours=self._taggingColours)

    def addHex(
            self,
            hex: travellermap.HexPosition
            ) -> None:
        if self._allowHexCallback:
            if not self._allowHexCallback(hex):
                return
        self._hexTable.addHex(hex)
        self._notifyContentChangeObservers()

    def addHexes(
            self,
            hexes: typing.Iterable[travellermap.HexPosition]
            ) -> None:
        if self._allowHexCallback:
            filteredHexes: typing.List[travellermap.HexPosition] = []
            for hex in hexes:
                if not self._allowHexCallback(hex):
                    continue
                filteredHexes.append(hex)
            if not filteredHexes:
                return # Nothing to do
            self._hexTable.addHexes(hexes=filteredHexes)
        else:
            self._hexTable.addHexes(hexes=hexes)

        self._notifyContentChangeObservers()

    def removeHex(
            self,
            hex: travellermap.HexPosition
            ) -> bool:
        removed = self._hexTable.removeHex(hex)
        if removed:
            self._notifyContentChangeObservers()
        return removed

    def removeAllRows(self) -> None:
        if self._hexTable.isEmpty():
            return
        self._hexTable.removeAllRows()
        self._notifyContentChangeObservers()

    def isEmpty(self) -> bool:
        return self._hexTable.isEmpty()

    def containsHex(
            self,
            hex: travellermap.HexPosition
            ) -> bool:
        return self._hexTable.containsHex(hex)

    def rowCount(self) -> int:
        return self._hexTable.rowCount()

    def hex(self, row: int) -> typing.Optional[travellermap.HexPosition]:
        return self._hexTable.hex(row=row)

    def world(self, row: int) -> typing.Optional[travellermap.World]:
        return self._hexTable.world(row)

    def hexes(self) -> typing.List[travellermap.HexPosition]:
        return self._hexTable.hexes()

    # NOTE: Indexing into the list of returned worlds does not match
    # table row indexing if the table contains dead space hexes.
    def worlds(self) -> typing.List[travellermap.World]:
        return self._hexTable.worlds()

    def rowAt(self, y: int) -> int:
        translated = self.mapToGlobal(QtCore.QPoint(self.x(), y))
        translated = self._hexTable.viewport().mapFromGlobal(translated)
        return self._hexTable.rowAt(translated.y())

    def hexAt(self, y: int) -> typing.Optional[travellermap.HexPosition]:
        row = self.rowAt(y)
        return self.hex(row) if row >= 0 else None

    def worldAt(self, y: int) -> typing.Optional[travellermap.World]:
        row = self.rowAt(y)
        return self.world(row) if row >= 0 else None

    def hasSelection(self) -> bool:
        return self._hexTable.hasSelection()

    def selectedHexes(self) -> typing.List[travellermap.HexPosition]:
        return self._hexTable.selectedHexes()

    # NOTE: Indexing into the list of returned worlds does not match table
    # selection indexing if the selection contains dead space hexes.
    def selectedWorlds(self) -> typing.List[travellermap.World]:
        return self._hexTable.selectedWorlds()

    def removeSelectedRows(self) -> None:
        if not self._hexTable.hasSelection():
            return

        self._hexTable.removeSelectedRows()
        self._notifyContentChangeObservers()

    def setRelativeHex(
            self,
            hex: typing.Union[travellermap.HexPosition, travellermap.World]
            ) -> None:
        if isinstance(hex, travellermap.World):
            hex = hex.hex()
        self._relativeHex = hex

    def setRelativeWorld(
            self,
            world: travellermap.World
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
        result = self._hexTable.restoreContent(state=state)
        if not self._hexTable.isEmpty():
            self._notifyContentChangeObservers()
        return result

    def setHexTooltipProvider(
            self,
            provider: typing.Optional[gui.HexTooltipProvider]
            ) -> None:
        self._hexTable.setHexTooltipProvider(provider=provider)

    def enableDeadSpace(self, enable: bool) -> None:
        if enable == self._enableDeadSpace:
            return

        self._enableDeadSpace = enable

        if not enable:
            # Dead space hexes are not allowed so remove any that are already in
            # the table
            contentChanged = False
            for row in range(self._hexTable.rowCount() - 1, -1, -1):
                world = travellermap.WorldManager.instance().worldByPosition(
                    milieu=self._milieu,
                    hex=self.hex(row=row))
                if not world:
                    self._hexTable.removeRow(row=row)
                    contentChanged = True
            if contentChanged:
                self._notifyContentChangeObservers()

    def isDeadSpaceEnabled(self) -> bool:
        return self._enableDeadSpace

    def promptAddLocation(self) -> None:
        currentHexes = self.hexes()

        dlg = gui.HexSelectDialog(
            milieu=self._milieu,
            rules=self._rules,
            mapStyle=self._mapStyle,
            mapOptions=self._mapOptions,
            mapRendering=self._mapRendering,
            mapAnimations=self._mapAnimations,
            worldTagging=self._worldTagging,
            taggingColours=self._taggingColours,
            parent=self)
        dlg.configureSelection(
            singleSelect=self._isOrderedList,
            includeDeadSpace=self._enableDeadSpace)

        # If it's not an ordered list that is being managed then the dialog should
        # show the current table contents and allow the user to select more hexes or
        # unselect currently selected ones to have them removed from the table. If
        # we are dealing with an ordered list the dialog is just used to select a
        # new world that should be added to the table, in which case the current
        # table contents are not shown.
        if not self._isOrderedList:
            dlg.selectHexes(hexes=currentHexes)

        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return

        newHexes = dlg.selectedHexes()
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
                if self._allowHexCallback and not self._allowHexCallback(hex):
                    # Silently ignore worlds that are filtered out
                    continue

                self._hexTable.addHex(hex)
                updated = True
        finally:
            self._hexTable.setSortingEnabled(sortingEnabled)

        if updated:
            self._notifyContentChangeObservers()

    def promptAddNearby(
            self,
            initialHex: typing.Optional[typing.Union[
                travellermap.HexPosition,
                travellermap.World
                ]] = None
            ) -> None:
        centerHex = initialHex.hex() if isinstance(initialHex, travellermap.World) else initialHex
        if not centerHex and self._relativeHex:
            centerHex = self._relativeHex

        dlg = gui.HexRadiusSelectDialog(
            milieu=self._milieu,
            rules=self._rules,
            mapStyle=self._mapStyle,
            mapOptions=self._mapOptions,
            mapRendering=self._mapRendering,
            mapAnimations=self._mapAnimations,
            worldTagging=self._worldTagging,
            taggingColours=self._taggingColours,
            parent=self)
        dlg.enableDeadSpaceSelection(enable=self._enableDeadSpace)
        if centerHex:
            dlg.setCenterHex(hex=centerHex)
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return

        self.addHexes(hexes=dlg.selectedHexes())

    def menuAction(
            self,
            id: enum.Enum
            ) -> typing.Optional[QtWidgets.QAction]:
        return self._hexTable.menuAction(id)

    def setMenuAction(
            self,
            id: enum.Enum,
            action: typing.Optional[QtWidgets.QAction]
            ) -> None:
        self._hexTable.setMenuAction(id, action)

        if id is HexTableManagerWidget.MenuAction.AddLocation:
            self._addLocationsButton.setAction(action=action)
        elif id is HexTableManagerWidget.MenuAction.AddNearby:
            self._addNearbyButton.setAction(action=action)
        elif id is HexTableManagerWidget.MenuAction.RemoveSelected:
            self._removeSelectionButton.setAction(action=action)
        elif id is HexTableManagerWidget.MenuAction.RemoveAll:
            self._removeAllButton.setAction(action=action)

    def fillContextMenu(self, menu: QtWidgets.QMenu) -> None:
        needsSeparator = False

        action = self.menuAction(HexTableManagerWidget.MenuAction.AddLocation)
        if action:
            menu.addAction(action)
            needsSeparator = True

        action = self.menuAction(HexTableManagerWidget.MenuAction.AddNearby)
        if action:
            menu.addAction(action)
            needsSeparator = True

        if needsSeparator:
            menu.addSeparator()
            needsSeparator = False

        action = self.menuAction(HexTableManagerWidget.MenuAction.RemoveSelected)
        if action:
            menu.addAction(action)
            needsSeparator = True

        action = self.menuAction(HexTableManagerWidget.MenuAction.RemoveAll)
        if action:
            menu.addAction(action)
            needsSeparator = True

        if needsSeparator:
            menu.addSeparator()
            needsSeparator = False

        # Add table menu options
        self._hexTable.fillContextMenu(menu)

    def contextMenuEvent(self, event: typing.Optional[QtGui.QContextMenuEvent]) -> None:
        if self.contextMenuPolicy() != QtCore.Qt.ContextMenuPolicy.DefaultContextMenu:
            super().contextMenuEvent(event)
            return

        if not event or not self._hexTable:
            return

        globalPos = event.globalPos()
        tablePos = self._hexTable.mapFromGlobal(globalPos)
        viewport = self._hexTable.viewport()
        tableGeometry = viewport.geometry() if viewport else self._hexTable.geometry()
        if tableGeometry.contains(tablePos):
            menu = QtWidgets.QMenu(self)
            self.fillContextMenu(menu=menu)
            menu.exec(globalPos)

        #super().contextMenuEvent(event)

    def eventFilter(self, object: object, event: QtCore.QEvent) -> bool:
        if object == self:
            if event.type() == QtCore.QEvent.Type.ContextMenu:
                if self.contextMenuPolicy() == QtCore.Qt.ContextMenuPolicy.CustomContextMenu:
                    assert(isinstance(event, QtGui.QContextMenuEvent))
                    if self._hexTable:
                        globalPos = event.globalPos()
                        tablePos = self._hexTable.mapFromGlobal(globalPos)

                        # Only allow context menu if mouse is over the table viewport
                        viewport = self._hexTable.viewport()
                        tableGeometry = viewport.geometry() if viewport else self._hexTable.geometry()
                        if tableGeometry.contains(tablePos):
                            self.customContextMenuRequested.emit(event.pos())

                    event.accept()
                    return True
        elif object == self._hexTable:
            if event.type() == QtCore.QEvent.Type.KeyPress:
                assert(isinstance(event, QtGui.QKeyEvent))
                if event.key() == QtCore.Qt.Key.Key_Delete:
                    self.removeSelectedRows()
                    event.accept()
                    return True

        return super().eventFilter(object, event)

    def _syncActions(self) -> None:
        hasContent = not self.isEmpty()
        hasSelection = self.hasSelection()

        action = self.menuAction(HexTableManagerWidget.MenuAction.AddNearby)
        if action:
            action.setVisible(not self._isOrderedList)

        action = self.menuAction(HexTableManagerWidget.MenuAction.RemoveSelected)
        if action:
            action.setEnabled(hasSelection)

        action = self.menuAction(HexTableManagerWidget.MenuAction.RemoveAll)
        if action:
            action.setEnabled(hasContent)

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

    def _notifyContentChangeObservers(self) -> None:
        self._syncActions()
        self.contentChanged.emit()

    def _showTableContextMenu(self, point: QtCore.QPoint) -> None:
        globalPos = self._hexTable.viewport().mapToGlobal(point)
        menu = QtWidgets.QMenu(self)
        self.fillContextMenu(menu=menu)
        menu.exec(globalPos)

    def _tableSelectionChanged(self) -> None:
        self._syncActions()

    def _displayModeChanged(self, index: int) -> None:
        self._hexTable.setActiveColumns(self._displayColumns())
