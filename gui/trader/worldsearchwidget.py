import gui
import logging
import traveller
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

# TODO: This will probably need updated to allow (optionally) selecting dead space
class WorldSearchWidget(QtWidgets.QWidget):
    selectionChanged = QtCore.pyqtSignal()

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
        searchLayout.addWidget(QtWidgets.QLabel('World:'))
        searchLayout.addWidget(self._searchComboBox, 1) # Stretch to take up all free space

        self._worldList = QtWidgets.QListWidget()
        self._worldList.installEventFilter(self)
        self._worldList.selectionModel().selectionChanged.connect(self._listSelectionChanged)

        offlineLayout = QtWidgets.QVBoxLayout()
        offlineLayout.addLayout(searchLayout)
        offlineLayout.addWidget(self._worldList)
        self._offlineWidget = QtWidgets.QWidget()
        self._offlineWidget.setLayout(offlineLayout)

        self._mapWidget = gui.TravellerMapWidget()
        self._mapWidget.setSelectionMode(gui.TravellerMapWidget.SelectionMode.SingleSelect)
        self._mapWidget.enableDeadSpaceSelection(False) # TODO: This needs to be configurable
        self._mapWidget.setInfoEnabled(False) # Disabled by default
        self._mapWidget.selectionChanged.connect(self._mapSelectionChanged)

        onlineLayout = QtWidgets.QVBoxLayout()
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

    def world(self) -> typing.Optional[traveller.World]:
        currentWidget = self._tabBar.currentWidget()
        if currentWidget == self._offlineWidget:
            selectedItems = self._worldList.selectedItems()
            if not selectedItems or len(selectedItems) > 1:
                return None
            return selectedItems[0].data(QtCore.Qt.ItemDataRole.UserRole)
        elif currentWidget == self._onlineWidget:
            selection = self._mapWidget.hackSelectedWorlds()
            return selection[0] if selection else None
        return None

    def setWorld(self, world: typing.Optional[traveller.World]) -> None:
        with gui.SignalBlocker(widget=self._searchComboBox):
            self._searchComboBox.setCurrentHex(
                pos=world.hexPosition() if world else None) # TODO: This is a hack until this widget supports hexes

        with gui.SignalBlocker(widget=self._worldList):
            self._worldList.clear()
            if world:
                self._worldList.addItem(self._createListItem(world))
                self._worldList.setCurrentRow(0)

        with gui.SignalBlocker(widget=self._mapWidget):
            if world:
                self._mapWidget.selectHex(
                    pos=world.hexPosition(), # TODO: This is a hack until this widget supports hexes
                    centerOnWorld=True,
                    setInfoWorld=True)
            else:
                self._mapWidget.clearSelectedHexes()

        self.selectionChanged.emit()

    def eventFilter(self, object: object, event: QtCore.QEvent) -> bool:
        if object == self._searchComboBox:
            if event.type() == QtCore.QEvent.Type.KeyPress:
                assert(isinstance(event, QtGui.QKeyEvent))
                if event.key() == QtCore.Qt.Key.Key_Up or \
                        event.key() == QtCore.Qt.Key.Key_Down:
                    index = self._worldList.currentIndex()
                    if index:
                        if event.key() == QtCore.Qt.Key.Key_Up:
                            newRow = max(index.row() - 1, 0)
                        else:
                            newRow = min(index.row() + 1, self._worldList.count() - 1)
                    else:
                        if event.key() == QtCore.Qt.Key.Key_Up:
                            newRow = self._worldList.count() - 1
                        else:
                            newRow = 0
                    self._worldList.setCurrentRow(newRow)
                    return True
                elif event.key() == QtCore.Qt.Key.Key_Down:
                    # Move world list selection down
                    index = self._worldList.currentIndex()
                    if index:
                        newRow = min(index.row() + 1, self._worldList.count() - 1)
                    else:
                        newRow = 0
                    self._worldList.setCurrentRow(newRow)
                    return True
        elif object == self._worldList:
            if event.type() == QtCore.QEvent.Type.ToolTip:
                assert(isinstance(event, QtGui.QHelpEvent))
                position = event.pos()
                item = self._worldList.itemAt(position)

                if item and not item.data(QtCore.Qt.ItemDataRole.ToolTipRole):
                    world: traveller.World = item.data(QtCore.Qt.ItemDataRole.UserRole)
                    toolTip = gui.createWorldToolTip(world=world)

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
        stream.writeQString(WorldSearchWidget._StateVersion)

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
        if version != WorldSearchWidget._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore WorldSearchWidget state (Incorrect version)')
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
            world: traveller.World
            ) -> QtWidgets.QListWidgetItem:
        item = QtWidgets.QListWidgetItem(world.name(includeSubsector=True))
        item.setData(QtCore.Qt.ItemDataRole.UserRole, world)
        return item

    def _primeSearch(self) -> None:
        self._searchTimer.start()

    def _performSearch(self) -> None:
        self._worldList.clear()

        searchString = self._searchComboBox.currentText()
        if not searchString:
            return

        try:
            worlds = traveller.WorldManager.instance().searchForWorlds(
                searchString=searchString)
        except Exception as ex:
            logging.error(
                f'World search for "{searchString}" failed',
                exc_info=ex)
            return

        if worlds:
            selectItem = None
            for world in worlds:
                item = self._createListItem(world)
                self._worldList.addItem(item)
                # TODO: The use of hexPosition is a hack until this widget supports hexes
                if world.hexPosition() == self._searchComboBox.currentHex():
                    selectItem = item

            if selectItem:
                selectItem.setSelected(True)

            self._worldList.sortItems(QtCore.Qt.SortOrder.AscendingOrder)

            # Select the first item in the row
            self._worldList.setCurrentRow(0)

    def _tabBarChanged(self, index: int) -> None:
        self.selectionChanged.emit()

    def _listSelectionChanged(self) -> None:
        world = self.world()

        with gui.SignalBlocker(widget=self._mapWidget):
            if world:
                self._mapWidget.selectHex(
                    pos=world.hexPosition(), # TODO: This is a hack until this widget supports hexes
                    centerOnWorld=True,
                    setInfoWorld=True)
            else:
                self._mapWidget.clearSelectedHexes()

        self.selectionChanged.emit()

    def _mapSelectionChanged(self) -> None:
        world = self.world()

        with gui.SignalBlocker(widget=self._searchComboBox):
            self._searchComboBox.setCurrentHex(
                pos=world.hexPosition() if world else None) # TODO: This is a hack until this widget supports hexes

        with gui.SignalBlocker(widget=self._worldList):
            self._worldList.clear()
            if world:
                self._worldList.addItem(self._createListItem(world))
                self._worldList.setCurrentRow(0)

        self.selectionChanged.emit()
