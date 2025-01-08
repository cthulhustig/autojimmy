import app
import gui
import logging
import traveller
import travellermap
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

class HexSelectDialog(gui.DialogEx):
    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            title='Select',
            configSection='HexSelectDialog',
            parent=parent)

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

        self._resultsList = gui.ListWidgetEx()
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
        onlineLayout.addWidget(QtWidgets.QLabel('Click on the location you want to select.'), 0)
        onlineLayout.addWidget(self._mapWidget, 1)
        self._onlineWidget = QtWidgets.QWidget()
        self._onlineWidget.setLayout(onlineLayout)

        self._tabBar = gui.TabWidgetEx()
        self._tabBar.addTab(self._offlineWidget, 'Offline Search')
        self._tabBar.addTab(self._onlineWidget, 'Traveller Map')

        widgetLayout = QtWidgets.QVBoxLayout()
        widgetLayout.setContentsMargins(0, 0, 0, 0)
        widgetLayout.addWidget(self._tabBar)

        self._okButton = QtWidgets.QPushButton('OK')
        self._okButton.setDisabled(True)
        self._okButton.setDefault(True)
        self._okButton.clicked.connect(self.accept)

        self._cancelButton = QtWidgets.QPushButton('Cancel')
        self._cancelButton.clicked.connect(self.reject)

        buttonLayout = QtWidgets.QHBoxLayout()
        buttonLayout.setContentsMargins(0, 0, 0, 0)
        buttonLayout.addStretch()
        buttonLayout.addWidget(self._okButton)
        buttonLayout.addWidget(self._cancelButton)

        windowLayout = QtWidgets.QVBoxLayout()
        windowLayout.addLayout(widgetLayout)
        windowLayout.addLayout(buttonLayout)

        self.setLayout(windowLayout)

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

    def hasSelection(self) -> bool:
        currentWidget = self._tabBar.currentWidget()
        if currentWidget == self._offlineWidget:
            return self._resultsList.hasSelection()
        elif currentWidget == self._onlineWidget:
            return self._mapWidget.hasSelection()
        return False

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

        self._handleSelectionChanged()

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
                self._handleSelectionChanged()

    def isDeadSpaceSelectionEnabled(self) -> bool:
        return self._searchComboBox.isDeadSpaceSelectionEnabled()

    def loadSettings(self) -> None:
        super().loadSettings()

        self._settings.beginGroup(self._configSection)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='TabBarState',
            type=QtCore.QByteArray)
        if storedValue:
            self._tabBar.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='SearchState',
            type=QtCore.QByteArray)
        if storedValue:
            self._searchComboBox.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='MapState',
            type=QtCore.QByteArray)
        if storedValue:
            self._mapWidget.restoreState(storedValue)

        self._settings.endGroup()

    def saveSettings(self) -> None:
        self._settings.beginGroup(self._configSection)
        self._settings.setValue('TabBarState', self._tabBar.saveState())
        self._settings.setValue('SearchState', self._searchComboBox.saveState())
        self._settings.setValue('MapState', self._mapWidget.saveState())
        self._settings.endGroup()

        super().saveSettings()

    def accept(self) -> None:
        hex = self.selectedHex()
        if not hex:
            return # A valid hex must be selected to accept

        # Add the selected hex to the selection history
        app.HexHistory.instance().addHex(hex=hex)

        super().accept()

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
        oldSelectedHex = self.selectedHex()

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

        newSelectedHex = None
        with gui.SignalBlocker(self._resultsList) and gui.UpdateBlocker(self._resultsList):
            self._resultsList.clear()

            for hex in matches:
                item = self._createListItem(hex)
                self._resultsList.addItem(item)
                if hex == oldSelectedHex:
                    item.setSelected(True)

            if not self._resultsList.hasSelection() and not self._resultsList.isEmpty():
                item = self._resultsList.item(0)
                item.setSelected(True)

            selection = self._resultsList.selectedItems()
            if selection:
                newSelectedHex = selection[0].data(QtCore.Qt.ItemDataRole.UserRole)
        self._resultsList.repaint() # Needed as updates were blocked

        with gui.SignalBlocker(self._mapWidget):
            if newSelectedHex:
                self._mapWidget.selectHex(
                    hex=newSelectedHex,
                    centerOnHex=True,
                    setInfoHex=True)
            else:
                self._mapWidget.clearSelectedHexes()

        if oldSelectedHex != newSelectedHex:
            self._handleSelectionChanged()

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

        self._handleSelectionChanged()

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

        self._handleSelectionChanged()

    def _handleSelectionChanged(self):
        self._okButton.setDisabled(not self.hasSelection())
