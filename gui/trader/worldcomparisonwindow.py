import app
import gui
import logic
import logging
import traveller
import travellermap
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

_WelcomeMessage = """
    <html>
    <p>The World Comparison window allows you to compare worlds by their different attributes (UWP,
    PBG etc). Worlds can be added to the table to view their attributes. Column sorting can be used
    to further aid comparison.</p>
    <p>The world information used is taken from Traveller Map and should be suitable for most
    Traveller rule systems.</p>
    <p>For Mongoose Traveller players, {name} can calculate Sale and Purchase Trade Scores for
    the chosen worlds. These are calculated as the sum of the Sale and Purchase DMs for a given
    list of Trade Goods. These values are only aimed as a guide but in general the larger the value,
    the better the sale/purchase prices are likely to be (in the player's favour).</p>
    <p>By selecting the Trade Goods, the player has to sell or selecting the Trade Goods in their
    purchase range, the Trade Score can help players quickly identify worlds which may be good
    options for trading.</p>
    </html>
""".format(name=app.AppName)

class _CustomTradeGoodTable(gui.TradeGoodTable):
    def __init__(self):
        super().__init__()

        self.setCheckable(True)

        # Don't include exotics in the table as they're not like other trade goods and don't
        # affect the trade score
        tradeGoods = traveller.tradeGoodList(
            rules=app.Config.instance().rules(),
            excludeTradeGoods=[traveller.tradeGoodFromId(
                rules=app.Config.instance().rules(),
                tradeGoodId=traveller.TradeGoodIds.Exotics)])
        for tradeGood in tradeGoods:
            self.addTradeGood(tradeGood=tradeGood)

        self.resizeColumnsToContents()

    def minimumSizeHint(self) -> QtCore.QSize:
        width = 0
        for column in range(self.columnCount()):
            width += self.horizontalHeader().sectionSize(column)
        if not self.verticalScrollBar().isHidden():
            width += self.verticalScrollBar().width()
        width += self.frameWidth()

        # Not sure what I'm missing above but a +1 is needed to prevent
        # the horizontal scroll bar being displayed
        width += 1

        hint = super().minimumSizeHint()
        hint.setWidth(width)
        return hint

class WorldComparisonWindow(gui.WindowWidget):
    def __init__(self) -> None:
        super().__init__(
            title='Compare Worlds',
            configSection='WorldComparisonWindow')

        self._scoreRecalculationTimer = None

        self._setupTradeGoodsControls()
        self._setupWorldControls()

        self._leftRightSplitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self._leftRightSplitter.addWidget(self._scoredGoodGroupBox)
        self._leftRightSplitter.addWidget(self._worldsGroupBox)

        windowLayout = QtWidgets.QVBoxLayout()
        windowLayout.addWidget(self._leftRightSplitter)

        self.setLayout(windowLayout)

    def firstShowEvent(self, e: QtGui.QShowEvent) -> None:
        QtCore.QTimer.singleShot(0, self._showWelcomeMessage)
        super().firstShowEvent(e)

    def loadSettings(self) -> None:
        super().loadSettings()

        self._settings.beginGroup(self._configSection)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='TradeGoodTableState',
            type=QtCore.QByteArray)
        if storedValue:
            self._tradeGoodTable.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='ResultsDisplayModeState',
            type=QtCore.QByteArray)
        if storedValue:
            self._resultsDisplayModeTabView.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='WorldTableState',
            type=QtCore.QByteArray)
        if storedValue:
            self._worldManagementWidget.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='MapWidgetState',
            type=QtCore.QByteArray)
        if storedValue:
            self._travellerMapWidget.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='LeftRightSplitterState',
            type=QtCore.QByteArray)
        if storedValue:
            self._leftRightSplitter.restoreState(storedValue)

        self._settings.endGroup()

    def saveSettings(self) -> None:
        self._settings.beginGroup(self._configSection)

        self._settings.setValue('TradeGoodTableState', self._tradeGoodTable.saveState())
        self._settings.setValue('ResultsDisplayModeState', self._resultsDisplayModeTabView.saveState())
        self._settings.setValue('WorldTableState', self._worldManagementWidget.saveState())
        self._settings.setValue('MapWidgetState', self._travellerMapWidget.saveState())
        self._settings.setValue('LeftRightSplitter', self._leftRightSplitter.saveState())

        self._settings.endGroup()

        super().saveSettings()

    def _setupTradeGoodsControls(self) -> None:
        self._tradeGoodTable = _CustomTradeGoodTable()
        self._tradeGoodTable.itemChanged.connect(self._tradeGoodTableItemChanged)

        self._checkAllTradeGoodsButton = QtWidgets.QPushButton()
        self._checkAllTradeGoodsButton.setText('Check All')
        self._checkAllTradeGoodsButton.clicked.connect(
            lambda: self._tradeGoodTable.setAllRowCheckState(checkState=True))

        self._uncheckAllTradeGoodsButton = QtWidgets.QPushButton()
        self._uncheckAllTradeGoodsButton.setText('Uncheck All')
        self._uncheckAllTradeGoodsButton.clicked.connect(
            lambda: self._tradeGoodTable.setAllRowCheckState(checkState=False))

        buttonLayout = QtWidgets.QHBoxLayout()
        buttonLayout.setContentsMargins(0, 0, 0, 0)
        buttonLayout.addStretch()
        buttonLayout.addWidget(self._checkAllTradeGoodsButton)
        buttonLayout.addWidget(self._uncheckAllTradeGoodsButton)

        groupLayout = QtWidgets.QVBoxLayout()
        groupLayout.addWidget(self._tradeGoodTable)
        groupLayout.addLayout(buttonLayout)

        self._scoredGoodGroupBox = QtWidgets.QGroupBox('Scored Trade Goods')
        self._scoredGoodGroupBox.setLayout(groupLayout)

    def _setupWorldControls(self) -> None:
        self._worldTable = gui.WorldTradeScoreTable()
        self._worldManagementWidget = gui.HexTableManagerWidget(
            allowHexCallback=self._allowWorld,
            hexTable=self._worldTable,
            enableAddNearby=True,
            enableMapSelection=False) # The traveller map instance for this window should be used to select
        self._worldManagementWidget.enableDisplayModeChangedEvent(enable=True)
        self._worldManagementWidget.displayModeChanged.connect(self._updateWorldTableColumns)
        self._worldManagementWidget.enableContextMenuEvent(enable=True)
        self._worldManagementWidget.contextMenuRequested.connect(self._showWorldTableContextMenu)
        self._worldManagementWidget.contentChanged.connect(self._tableContentsChanged)

        self._travellerMapWidget = gui.TravellerMapWidget()
        self._travellerMapWidget.setSelectionMode(
            mode=gui.TravellerMapWidget.SelectionMode.MultiSelect)
        self._travellerMapWidget.selectionChanged.connect(self._mapSelectionChanged)

        self._resultsDisplayModeTabView = gui.TabWidgetEx()
        self._resultsDisplayModeTabView.setTabPosition(QtWidgets.QTabWidget.TabPosition.East)
        self._resultsDisplayModeTabView.addTab(self._worldManagementWidget, 'World Details')
        self._resultsDisplayModeTabView.addTab(self._travellerMapWidget, 'Traveller Map')

        groupLayout = QtWidgets.QVBoxLayout()
        groupLayout.addWidget(self._resultsDisplayModeTabView)

        self._worldsGroupBox = QtWidgets.QGroupBox('Worlds')
        self._worldsGroupBox.setLayout(groupLayout)

    def _allowWorld(self, hex: travellermap.HexPosition) -> bool:
        return not self._worldManagementWidget.containsHex(hex)

    def _worldColumns(self) -> typing.List[gui.HexTable.ColumnType]:
        displayMode = self._worldManagementWidget.displayMode()
        if displayMode == gui.HexTableTabBar.DisplayMode.AllColumns:
            return gui.WorldTradeScoreTable.AllColumns
        elif displayMode == gui.HexTableTabBar.DisplayMode.SystemColumns:
            return gui.WorldTradeScoreTable.SystemColumns
        elif displayMode == gui.HexTableTabBar.DisplayMode.UWPColumns:
            return gui.WorldTradeScoreTable.UWPColumns
        elif displayMode == gui.HexTableTabBar.DisplayMode.EconomicsColumns:
            return gui.WorldTradeScoreTable.EconomicsColumns
        elif displayMode == gui.HexTableTabBar.DisplayMode.CultureColumns:
            return gui.WorldTradeScoreTable.CultureColumns
        elif displayMode == gui.HexTableTabBar.DisplayMode.RefuellingColumns:
            return gui.WorldTradeScoreTable.RefuellingColumns
        else:
            assert(False) # I missed a case

    def _tradeGoodTableItemChanged(self, item: QtWidgets.QTableWidgetItem) -> None:
        if not self._worldTable:
            # This should only happen during setup when the world management widget hasn't
            # been created yet
            return

        # When selecting multiple trade goods at once this will happen once for each of them.
        # Rather repeatedly recalculating the trade score, set a short timer to recalculate
        # once everything has updated
        if not self._scoreRecalculationTimer:
            self._scoreRecalculationTimer = QtCore.QTimer()
            self._scoreRecalculationTimer.timeout.connect(self._scoreRecalculationTimerFired)
            self._scoreRecalculationTimer.setInterval(500)
            self._scoreRecalculationTimer.setSingleShot(True)
        self._scoreRecalculationTimer.start()

    def _scoreRecalculationTimerFired(self) -> None:
        if not self._worldTable:
            # This should never happen but handle it just in case
            return
        self._worldTable.setTradeGoods(tradeGoods=self._tradeGoodTable.checkedTradeGoods())

    def _updateWorldTableColumns(self, displayMode: gui.HexTableTabBar.DisplayMode) -> None:
        self._worldManagementWidget.setVisibleColumns(self._worldColumns())

    def _tableContentsChanged(self) -> None:
        with gui.SignalBlocker(widget=self._travellerMapWidget):
            self._travellerMapWidget.clearSelectedHexes()
            for world in self._worldTable.worlds():
                self._travellerMapWidget.selectHex(
                    hex=world.hex(),
                    centerOnHex=False,
                    setInfoHex=False)

    def _mapSelectionChanged(self) -> None:
        oldSelection = set(self._worldManagementWidget.hexes())
        newSelection = set(self._travellerMapWidget.selectedHexes())

        with gui.SignalBlocker(widget=self._worldManagementWidget):
            for hex in oldSelection:
                if hex not in newSelection:
                    self._worldManagementWidget.removeHex(hex=hex)

            for hex in newSelection:
                if hex not in oldSelection:
                    self._worldManagementWidget.addHex(hex=hex)

    def _showWorldTableContextMenu(self, point: QtCore.QPoint) -> None:
        clickedRow = self._worldManagementWidget.rowAt(y=point.y())
        clickedWorld = self._worldTable.world(row=clickedRow)
        clickedScore = self._worldTable.tradeScore(row=clickedRow)

        menuItems = [
            gui.MenuItem(
                text='Add World...',
                callback=lambda: self._worldManagementWidget.promptAdd(),
                enabled=True
            ),
            gui.MenuItem(
                text='Add Nearby Worlds...',
                callback=lambda: self._worldManagementWidget.promptAddNearby(initialHex=clickedWorld),
                enabled=True
            ),
            gui.MenuItem(
                text='Remove Selected Worlds',
                callback=lambda: self._worldManagementWidget.removeSelectedRows(),
                enabled=self._worldManagementWidget.hasSelection()
            ),
            gui.MenuItem(
                text='Remove All Worlds',
                callback=lambda: self._worldManagementWidget.removeAllRows(),
                enabled=not self._worldManagementWidget.isEmpty()
            ),
            None, # Separator
            gui.MenuItem(
                text='Find Trade Options for Selected Worlds...',
                callback=lambda: self._findTradeOptions(self._worldManagementWidget.selectedWorlds()),
                enabled=self._worldManagementWidget.hasSelection()
            ),
            gui.MenuItem(
                text='Find Trade Options for All Worlds...',
                callback=lambda: self._findTradeOptions(self._worldManagementWidget.worlds()),
                enabled=not self._worldManagementWidget.isEmpty()
            ),
            None, # Separator
            gui.MenuItem(
                text='Show Selected World Details...',
                callback=lambda: self._showWorldDetails(self._worldManagementWidget.selectedWorlds()),
                enabled=self._worldManagementWidget.hasSelection()
            ),
            gui.MenuItem(
                text='Show All World Details...',
                callback=lambda: self._showWorldDetails(self._worldManagementWidget.worlds()),
                enabled=not self._worldManagementWidget.isEmpty()
            ),
            None, # Separator
            gui.MenuItem(
                text='Show Selected Worlds in Traveller Map...',
                callback=lambda: self._showWorldsInTravellerMap(self._worldManagementWidget.selectedWorlds()),
                enabled=self._worldManagementWidget.hasSelection()
            ),
            gui.MenuItem(
                text='Show All Worlds in Traveller Map...',
                callback=lambda: self._showWorldsInTravellerMap(self._worldManagementWidget.worlds()),
                enabled=not self._worldManagementWidget.isEmpty()
            ),
            None, # Separator
            gui.MenuItem(
                text='Show Trade Score Calculations...',
                callback=lambda: self._showTradeScoreCalculations(clickedScore),
                enabled=clickedScore != None
            ),
        ]

        gui.displayMenu(
            self,
            menuItems,
            self._worldManagementWidget.mapToGlobal(point)
        )

    def _findTradeOptions(
            self,
            worlds: typing.Iterable[traveller.World]
            ) -> None:
        try:
            traderWindow = gui.WindowManager.instance().showMultiWorldTradeOptionsWindow()
            traderWindow.configureControls(
                purchaseWorlds=worlds,
                saleWorlds=worlds)
        except Exception as ex:
            message = 'Failed to show trade options window'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)

    def _showTradeScoreCalculations(
            self,
            tradeScore: logic.TradeScore
            ) -> None:
        try:
            calculations = [tradeScore.totalPurchaseScore(), tradeScore.totalSaleScore()]
            calculationWindow = gui.WindowManager.instance().showCalculationWindow()
            calculationWindow.showCalculations(calculations=calculations)
        except Exception as ex:
            message = 'Failed to show calculations'
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

    def _showWorldsInTravellerMap(
            self,
            worlds: typing.Iterable[traveller.World]
            ) -> None:
        try:
            self._resultsDisplayModeTabView.setCurrentWidget(
                self._travellerMapWidget)
            self._travellerMapWidget.centerOnWorlds(
                worlds=worlds)
        except Exception as ex:
            message = 'Failed to show world(s) in Traveller Map'
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
            noShowAgainId='WorldComparisonWelcome')
        message.exec()
