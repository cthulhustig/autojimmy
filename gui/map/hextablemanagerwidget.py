import app
import gui
import logging
import logic
import traveller
import travellermap
import typing
from PyQt5 import QtWidgets, QtCore

# TODO: This should have an action/menu item that lets the user import hexes
# - Would need to work with whatever the default Ctrl+C export format is
#   which I think is html for legacy reasons
class HexTableManagerWidget(QtWidgets.QWidget):
    contentChanged = QtCore.pyqtSignal()

    # TODO: Hopefully I'll be able to get rid of this event
    # as part of what I'm working on
    contextMenuRequested = QtCore.pyqtSignal(QtCore.QPoint)

    # TODO: I Need to remind myself why this exists. It looks
    # incredibly hacky but I can't work out what it's achieving
    displayModeChanged = QtCore.pyqtSignal(gui.HexTableTabBar.DisplayMode)

    # TODO: Hopefully I will be able to get rid of this entire
    # event as part of what I'm working on. I think the code
    # that would have called this and handled the event could
    # just set set the 2 actions for showing the selection and
    # showing the content on the map with their own action that
    # shows on their map
    showOnMapRequested = QtCore.pyqtSignal([list])

    _StateVersion = 'HexTableManagerWidget_v1'

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
        self._enableContextMenuEvent = False
        self._enableDisplayModeChangedEvent = False
        self._enableShowOnMapEvent = False
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
        self._hexTable.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self._hexTable.customContextMenuRequested.connect(self._showTableContextMenu)
        self._hexTable.keyPressed.connect(self._tableKeyPressed)
        self._hexTable.itemSelectionChanged.connect(self._tableSelectionChanged)
        if self._isOrderedList:
            # Disable sorting on if the list is to be ordered
            self._hexTable.setSortingEnabled(False)

        self._promptAddFreeSelectAction = QtWidgets.QAction('Add...', self)
        self._promptAddFreeSelectAction.triggered.connect(self.promptAddFreeSelection)

        self._promptAddNearbyAction = QtWidgets.QAction('Add Nearby...', self)
        self._promptAddNearbyAction.setVisible(not self._isOrderedList)
        self._promptAddNearbyAction.triggered.connect(self.promptAddNearby)

        self._removeSelectedAction = QtWidgets.QAction('Remove Selected', self)
        self._removeSelectedAction.setEnabled(False) # No selection
        self._removeSelectedAction.triggered.connect(self.removeSelectedRows)

        self._removeContentAction = QtWidgets.QAction('Remove All', self)
        self._removeContentAction.setEnabled(False) # No content
        self._removeContentAction.triggered.connect(self.removeAllRows)

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

        # TODO: The add and remove buttons should trigger the corresponding
        # action when rather than directly calling a function. This would
        # allow things to replace the action and have it affect the button
        # as well as the menu option.
        self._addLocationsButton = QtWidgets.QPushButton('Add...')
        self._addLocationsButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)
        self._addLocationsButton.clicked.connect(self.promptAddFreeSelection)

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

    def mapStyle(self) -> travellermap.Style:
        return self._mapStyle

    def setMapStyle(self, style: travellermap.Style) -> None:
        if style == self._mapStyle:
            return
        self._mapStyle = style

    def mapOptions(self) -> typing.Iterable[travellermap.Option]:
        return list(self._mapStyle)

    def setMapOptions(self, options: typing.Iterable[travellermap.Option]) -> None:
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
        if not self._hexTable.hasSelection():
            return

        self._hexTable.removeSelectedRows()
        self._notifyContentChangeObservers()

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
        result = self._hexTable.restoreContent(state=state)
        if not self._hexTable.isEmpty():
            self._notifyContentChangeObservers()
        return result

    def setHexTooltipProvider(
            self,
            provider: typing.Optional[gui.HexTooltipProvider]
            ) -> None:
        self._hexTable.setHexTooltipProvider(provider=provider)

    def enableContextMenuEvent(self, enable: bool = True) -> None:
        self._enableContextMenuEvent = enable

    def isContextMenuEventEnabled(self) -> bool:
        return self._enableContextMenuEvent

    def enableDisplayModeChangedEvent(self, enable: bool = True) -> None:
        self._enableDisplayModeChangedEvent = enable

    def isDisplayModeChangedEventEnabled(self) -> bool:
        return self._enableDisplayModeChangedEvent

    def enableShowOnMapEvent(self, enable: bool = True) -> None:
        self._enableShowOnMapEvent = enable

    def isShowOnMapEventEnabled(self) -> bool:
        return self._enableShowOnMapEvent

    def enableDeadSpace(self, enable: bool) -> None:
        if enable == self._enableDeadSpace:
            return

        self._enableDeadSpace = enable

        if not enable:
            # Dead space hexes are not allowed so remove any that are already in
            # the table
            contentChanged = False
            for row in range(self._hexTable.rowCount() - 1, -1, -1):
                world = traveller.WorldManager.instance().worldByPosition(
                    milieu=self._milieu,
                    hex=self.hex(row=row))
                if not world:
                    self._hexTable.removeRow(row=row)
                    contentChanged = True
            if contentChanged:
                self._notifyContentChangeObservers()

    def isDeadSpaceEnabled(self) -> bool:
        return self._enableDeadSpace

    def promptAddFreeSelection(self) -> None:
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
                traveller.World
                ]] = None
            ) -> None:
        centerHex = initialHex.hex() if isinstance(initialHex, traveller.World) else initialHex
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

    def promptAddFreeSelectAction(self) -> QtWidgets.QAction:
        return self._promptAddFreeSelectAction

    def setPromptAddFreeSelectAction(self, action: QtWidgets.QAction) -> None:
        self._promptAddFreeSelectAction = action

    def promptAddNearbyAction(self) -> QtWidgets.QAction:
        return self._promptAddNearbyAction

    def setPromptAddNearbyAction(self, action: QtWidgets.QAction) -> None:
        self._promptAddNearbyAction = action

    def removeSelectedAction(self) -> QtWidgets.QAction:
        return self._removeSelectedAction

    def setRemoveSelectedAction(self, action: QtWidgets.QAction) -> None:
        self._removeSelectedAction = action

    def removeContentAction(self) -> QtWidgets.QAction:
        return self._removeContentAction

    def setRemoveContentAction(self, action: QtWidgets.QAction) -> None:
        self._removeContentAction = action

    def showSelectionDetailsAction(self) -> QtWidgets.QAction:
        return self._hexTable.showSelectionDetailsAction()

    def setShowSelectionDetailsAction(self, action: QtWidgets.QAction) -> None:
        self._hexTable.setShowSelectionDetailsAction(action)

    def showContentDetailsAction(self) -> QtWidgets.QAction:
        return self._hexTable.showContentDetailsAction()

    def setShowContentDetailsAction(self, action: QtWidgets.QAction) -> None:
        self._hexTable.setShowContentDetailsAction(action)

    def showSelectionOnMapAction(self) -> QtWidgets.QAction:
        return self._hexTable.showSelectionOnMapAction()

    def setShowSelectionOnMapAction(self, action: QtWidgets.QAction) -> None:
        self._hexTable.setShowSelectionOnMapAction(action)

    def showContentOnMapAction(self) -> QtWidgets.QAction:
        return self._hexTable.showContentOnMapAction()

    def setShowContentOnMapAction(self, action: QtWidgets.QAction) -> None:
        self._hexTable.setShowContentOnMapAction(action)

    def copyContentToClipboardAsCSvAction(self) -> QtWidgets.QAction:
        return self._hexTable.copyContentToClipboardAsCSvAction()

    def setCopyContentToClipboardAsCsvAction(
            self,
            action: QtWidgets.QAction
            ) -> None:
        self._hexTable.setCopyContentToClipboardAsCsvAction(action)

    def promptExportContentToCsvAction(self) -> QtWidgets.QAction:
        return self._hexTable.promptExportContentToCsvAction()

    def setPromptExportContentToCsvAction(
            self,
            action: QtWidgets.QAction
            ) -> None:
        self._hexTable.setPromptExportContentToCsvAction(action)

    def copyContentToClipboardAsHtmlAction(self) -> QtWidgets.QAction:
        return self._hexTable.copyContentToClipboardAsHtmlAction()

    def setCopyContentToClipboardAsHtmlAction(
            self,
            action: QtWidgets.QAction
            ) -> None:
        self._hexTable.setCopyContentToClipboardAsHtmlAction(action)

    def copyViewToClipboardAction(self) -> QtWidgets.QAction:
        self._hexTable.copyViewToClipboardAction()

    def setCopyViewToClipboardAction(
            self,
            action: QtWidgets.QAction
            ) -> None:
        self._hexTable.setCopyViewToClipboardAction(action)

    def promptExportContentToHtmlAction(self) -> QtWidgets.QAction:
        return self._hexTable.promptExportContentToHtmlAction()

    def setPromptExportContentToHtmlAction(
            self,
            action: QtWidgets.QAction
            ) -> None:
        self._hexTable.setPromptExportContentToHtmlAction(action)

    def fillContextMenu(self, menu: QtWidgets.QMenu) -> None:
        menu.addAction(self.promptAddFreeSelectAction())
        menu.addAction(self.promptAddNearbyAction())
        menu.addSeparator()
        menu.addAction(self.removeSelectedAction())
        menu.addAction(self.removeContentAction())
        menu.addSeparator()

        # Add table menu options
        self._hexTable.fillContextMenu(menu)

    def _syncActions(self) -> None:
        hasContent = not self.isEmpty()
        hasSelection = self.hasSelection()
        if self._promptAddNearbyAction:
            self._promptAddNearbyAction.setVisible(not self._isOrderedList)
        if self._removeSelectedAction:
            self._removeSelectedAction.setEnabled(hasSelection)
        if self._removeContentAction:
            self._removeContentAction.setEnabled(hasContent)

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
        if self._enableContextMenuEvent:
            translated = self._hexTable.viewport().mapToGlobal(point)
            translated = self.mapFromGlobal(translated)
            self.contextMenuRequested.emit(translated)
            return

        menu = QtWidgets.QMenu(self)
        self.fillContextMenu(menu=menu)
        menu.exec(self.mapToGlobal(point))

    def _tableKeyPressed(self, key: int) -> None:
        if key == QtCore.Qt.Key.Key_Delete:
            self.removeSelectedRows()

    def _tableSelectionChanged(self) -> None:
        hasSelection = self._hexTable.hasSelection()
        self._removeButton.setEnabled(hasSelection)
        self._syncActions()

    def _displayModeChanged(self, index: int) -> None:
        if self._enableDisplayModeChangedEvent:
            self.displayModeChanged.emit(self._displayModeTabs.currentDisplayMode())
            return

        self._hexTable.setActiveColumns(self._displayColumns())
