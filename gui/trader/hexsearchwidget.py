import gui
import logging
import traveller
import travellermap
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

class HexSearchWidget(QtWidgets.QWidget):
    selectionChanged = QtCore.pyqtSignal()

    # NOTE: This state string doesn't match the class name so the user doesn't
    # lose the last selected history due to the updates made to add dead space
    # support. It was already writing a sector hex so previous data should load
    # correctly
    _StateVersion = 'WorldSearchWidget_v1'

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self._searchTimer = QtCore.QTimer()
        self._searchTimer.setInterval(500)
        self._searchTimer.setSingleShot(True)
        self._searchTimer.timeout.connect(self._performSearch)

        self._searchComboBox = gui.HexSelectComboBox()
        self._searchComboBox.enableAutoComplete(False)
        self._searchComboBox.installEventFilter(self)
        self._searchComboBox.currentTextChanged.connect(self._primeSearch)

        searchLayout = QtWidgets.QHBoxLayout()
        searchLayout.setContentsMargins(0, 0, 0, 0)
        searchLayout.addWidget(QtWidgets.QLabel('World/Hex:'))
        searchLayout.addWidget(self._searchComboBox, 1) # Stretch to take up all free space

        self._resultsList = QtWidgets.QListWidget()
        self._resultsList.installEventFilter(self)
        self._resultsList.selectionModel().selectionChanged.connect(self._listSelectionChanged)

        offlineLayout = QtWidgets.QVBoxLayout()
        offlineLayout.addLayout(searchLayout)
        offlineLayout.addWidget(self._resultsList)
        self._offlineWidget = QtWidgets.QWidget()
        self._offlineWidget.setLayout(offlineLayout)

        self._mapWidget = gui.TravellerMapWidget()
        self._mapWidget.setSelectionMode(gui.TravellerMapWidget.SelectionMode.SingleSelect)
        self._mapWidget.enableDeadSpaceSelection(False)
        self._mapWidget.setInfoEnabled(False) # Disabled by default
        self._mapWidget.selectionChanged.connect(self._mapSelectionChanged)

        onlineLayout = QtWidgets.QVBoxLayout()
        # TODO: This should update to say click on the hex dead space selection is enabled
        onlineLayout.addWidget(QtWidgets.QLabel('Click on the world you want to select.'), 0)
        onlineLayout.addWidget(self._mapWidget, 1)
        self._onlineWidget = QtWidgets.QWidget()
        self._onlineWidget.setLayout(onlineLayout)

        self._tabBar = gui.TabWidgetEx()
        self._tabBar.addTab(self._offlineWidget, 'Offline Search')
        self._tabBar.addTab(self._onlineWidget, 'Traveller Map')
        self._tabBar.currentChanged.connect(self._tabBarChanged)

        widgetLayout = QtWidgets.QVBoxLayout()
        widgetLayout.setContentsMargins(0, 0, 0, 0)
        widgetLayout.addWidget(self._tabBar)

        self.setLayout(widgetLayout)

    def selectedHex(self) -> typing.Optional[travellermap.HexPosition]:
        currentWidget = self._tabBar.currentWidget()
        if currentWidget == self._offlineWidget:
            selectedItems = self._resultsList.selectedItems()
            if not selectedItems or len(selectedItems) > 1:
                return None
            return selectedItems[0].data(QtCore.Qt.ItemDataRole.UserRole)
        elif currentWidget == self._onlineWidget:
            selection = self._mapWidget.selectedHexes()
            return selection[0] if selection else None
        return None

    def setSelectedHex(
            self,
            hex: typing.Optional[travellermap.HexPosition]
            ) -> None:
        with gui.SignalBlocker(widget=self._searchComboBox):
            self._searchComboBox.setCurrentHex(hex=hex)

        with gui.SignalBlocker(widget=self._resultsList):
            self._resultsList.clear()
            if hex:
                item = self._createListItem(hex=hex)
                item.setSelected(True)
                self._resultsList.setCurrentItem(item)

        with gui.SignalBlocker(widget=self._mapWidget):
            if hex:
                self._mapWidget.selectHex(
                    hex=hex,
                    centerOnHex=True,
                    setInfoHex=True)
            else:
                self._mapWidget.clearSelectedHexes()

        self.selectionChanged.emit()

    # Helper to get the selected world if a world is selected. Useful for code
    # that never enables dead space selection
    def selectedWorld(self) -> typing.Optional[traveller.World]:
        hex = self.selectedHex()
        if not hex:
            return None
        return traveller.WorldManager.instance().worldByPosition(hex=hex)

    def enableDeadSpaceSelection(self, enable: bool) -> None:
        self._searchComboBox.enableDeadSpaceSelection(enable=enable)
        self._mapWidget.enableDeadSpaceSelection(enable=enable)

        if not enable:
            # Dead space selection has been disabled so remove any dead
            # space entries from the results list
            selectionChanged = False

            with gui.SignalBlocker(self._resultsList):
                for index in range(self._resultsList.count() - 1, -1, -1):
                    item = self._resultsList.item(index)
                    world = traveller.WorldManager.instance().worldByPosition(
                        hex=item.data(QtCore.Qt.ItemDataRole.UserRole))
                    if not world:
                        if item.isSelected():
                            selectionChanged = True
                        self._resultsList.takeItem(row=index)

            if selectionChanged:
                self.selectionChanged.emit()

    def isDeadSpaceSelectionEnabled(self) -> bool:
        return self._searchComboBox.isDeadSpaceSelectionEnabled()

    def eventFilter(self, object: object, event: QtCore.QEvent) -> bool:
        if object == self._searchComboBox:
            if event.type() == QtCore.QEvent.Type.KeyPress:
                assert(isinstance(event, QtGui.QKeyEvent))
                if event.key() == QtCore.Qt.Key.Key_Up or \
                        event.key() == QtCore.Qt.Key.Key_Down:
                    index = self._resultsList.currentIndex()
                    if index:
                        if event.key() == QtCore.Qt.Key.Key_Up:
                            newRow = max(index.row() - 1, 0)
                        else:
                            newRow = min(index.row() + 1, self._resultsList.count() - 1)
                    else:
                        if event.key() == QtCore.Qt.Key.Key_Up:
                            newRow = self._resultsList.count() - 1
                        else:
                            newRow = 0
                    self._resultsList.setCurrentRow(newRow)
                    return True
                elif event.key() == QtCore.Qt.Key.Key_Down:
                    # Move list selection down
                    index = self._resultsList.currentIndex()
                    if index:
                        newRow = min(index.row() + 1, self._resultsList.count() - 1)
                    else:
                        newRow = 0
                    self._resultsList.setCurrentRow(newRow)
                    return True
        elif object == self._resultsList:
            if event.type() == QtCore.QEvent.Type.ToolTip:
                assert(isinstance(event, QtGui.QHelpEvent))
                position = event.pos()
                item = self._resultsList.itemAt(position)

                if item and not item.data(QtCore.Qt.ItemDataRole.ToolTipRole):
                    hex: traveller.World = item.data(QtCore.Qt.ItemDataRole.UserRole)
                    toolTip = gui.createHexToolTip(hex=hex)

                    # Set the items tooltip text so it will be displayed in
                    # the future (we'll no longer get tool tip events for
                    # this item)
                    item.setData(QtCore.Qt.ItemDataRole.ToolTipRole, toolTip)

                    if toolTip:
                        # We've missed the opportunity to use the built in tool tip
                        # display for this event so manually display it
                        QtWidgets.QToolTip.showText(event.globalPos(), toolTip)

        return super().eventFilter(object, event)

    def showEvent(self, a0: QtGui.QShowEvent) -> None:
        self._searchComboBox.setFocus()
        return super().showEvent(a0)

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(HexSearchWidget._StateVersion)

        subState = self._tabBar.saveState()
        stream.writeUInt32(subState.count() if subState else 0)
        if subState:
            stream.writeRawData(subState.data())

        subState = self._mapWidget.saveState()
        stream.writeUInt32(subState.count() if subState else 0)
        if subState:
            stream.writeRawData(subState.data())

        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != HexSearchWidget._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore HexSearchWidget state (Incorrect version)')
            return False

        count = stream.readUInt32()
        if count > 0:
            subState = QtCore.QByteArray(stream.readRawData(count))
            if not self._tabBar.restoreState(subState):
                return False

        count = stream.readUInt32()
        if count > 0:
            subState = QtCore.QByteArray(stream.readRawData(count))
            if not self._mapWidget.restoreState(subState):
                return False

        return True

    def _createListItem(
            self,
            hex: travellermap.HexPosition
            ) -> QtWidgets.QListWidgetItem:
        text = traveller.WorldManager.instance().canonicalHexName(hex=hex)
        item = QtWidgets.QListWidgetItem(text)
        item.setData(QtCore.Qt.ItemDataRole.UserRole, hex)
        return item

    def _primeSearch(self) -> None:
        self._searchTimer.start()

    # TODO: How controls are updated by this function has changed quite
    # a bit so I need to make sure there are no regressions
    def _performSearch(self) -> None:
        oldSelection = self.selectedHex()

        searchString = self._searchComboBox.currentText()
        matches: typing.List[travellermap.HexPosition] = []
        if searchString:
            try:
                worlds = traveller.WorldManager.instance().searchForWorlds(
                    searchString=searchString)
                for world in worlds:
                    matches.append(world.hex())
            except Exception as ex:
                # Log this at debug as it could get very spammy as the user types
                logging.debug(
                    f'Search for "{searchString}" failed',
                    exc_info=ex)

            if self._searchComboBox.isDeadSpaceSelectionEnabled():
                try:
                    hex = traveller.WorldManager.instance().sectorHexToPosition(
                        sectorHex=searchString)
                    isDuplicate = False
                    for other in matches:
                        if hex == other:
                            isDuplicate = True
                            break
                    if not isDuplicate:
                        matches.append(hex)
                except KeyError:
                    pass # The search string isn't a a sector hex so ignore it
                except Exception as ex:
                    # Log this at debug as it could get very spammy as the user types
                    logging.debug(
                        f'Search for sector hex "{searchString}" failed',
                        exc_info=ex)

        newSelection = None
        with gui.SignalBlocker(self._resultsList):
            self._resultsList.clear()

            for hex in matches:
                item = self._createListItem(hex)
                self._resultsList.addItem(item)
                if hex == oldSelection:
                    item.setSelected(True)

            selection = self._resultsList.selectedItems()
            if selection:
                newSelection = selection[0].data(QtCore.Qt.ItemDataRole.UserRole)

            self._resultsList.sortItems(QtCore.Qt.SortOrder.AscendingOrder)

        with gui.SignalBlocker(self._mapWidget):
            if newSelection:
                self._mapWidget.selectHex(
                    hex=newSelection,
                    centerOnHex=True,
                    setInfoHex=True)
            else:
                self._mapWidget.clearSelectedHexes()

        if oldSelection != newSelection:
            self.selectionChanged.emit()

    def _tabBarChanged(self, index: int) -> None:
        self.selectionChanged.emit()

    def _listSelectionChanged(self) -> None:
        hex = self.selectedHex()

        with gui.SignalBlocker(widget=self._mapWidget):
            if hex:
                self._mapWidget.selectHex(
                    hex=hex,
                    centerOnHex=True,
                    setInfoHex=True)
            else:
                self._mapWidget.clearSelectedHexes()

        self.selectionChanged.emit()

    def _mapSelectionChanged(self) -> None:
        hex = self.selectedHex()

        with gui.SignalBlocker(widget=self._searchComboBox):
            self._searchComboBox.setCurrentHex(hex=hex)

        with gui.SignalBlocker(widget=self._resultsList):
            self._resultsList.clear()
            if hex:
                item = self._createListItem(hex)
                self._resultsList.addItem(item)
                item.setSelected(True)

        self.selectionChanged.emit()
