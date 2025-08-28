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
    def __init__(
            self,
            rules: traveller.Rules
            ) -> None:
        super().__init__(
            rules=rules,
            filterCallback=self._filterTradeGoods)

        self.setCheckable(True)
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

    def _filterTradeGoods(
            self,
            tradeGood: traveller.TradeGood
            ) -> bool:
        # Don't include exotics in the table as they're not like other trade
        # goods and don't affect the trade score
        exotics = traveller.tradeGoodFromId(
            ruleSystem=self._rules.system(),
            tradeGoodId=traveller.TradeGoodIds.Exotics)
        return tradeGood is not exotics

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

        app.Config.instance().configChanged.connect(self._appConfigChanged)

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
            self._mapWidget.restoreState(storedValue)

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
        self._settings.setValue('MapWidgetState', self._mapWidget.saveState())
        self._settings.setValue('LeftRightSplitter', self._leftRightSplitter.saveState())

        self._settings.endGroup()

        super().saveSettings()

    def _setupTradeGoodsControls(self) -> None:
        self._tradeGoodTable = _CustomTradeGoodTable(
            rules=app.Config.instance().value(option=app.ConfigOption.Rules))
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
        milieu = app.Config.instance().value(option=app.ConfigOption.Milieu)
        rules = app.Config.instance().value(option=app.ConfigOption.Rules)
        mapStyle = app.Config.instance().value(option=app.ConfigOption.MapStyle)
        mapOptions = app.Config.instance().value(option=app.ConfigOption.MapOptions)
        mapRendering = app.Config.instance().value(option=app.ConfigOption.MapRendering)
        mapAnimations = app.Config.instance().value(option=app.ConfigOption.MapAnimations)
        showTooltipImages = app.Config.instance().value(option=app.ConfigOption.ShowToolTipImages)
        worldTagging = app.Config.instance().value(option=app.ConfigOption.WorldTagging)
        taggingColours = app.Config.instance().value(option=app.ConfigOption.TaggingColours)

        self._hexTooltipProvider = gui.HexTooltipProvider(
            milieu=milieu,
            rules=rules,
            showImages=showTooltipImages,
            mapStyle=mapStyle,
            mapOptions=mapOptions,
            worldTagging=worldTagging,
            taggingColours=taggingColours)

        self._worldTable = gui.WorldTradeScoreTable(
            milieu=milieu,
            rules=rules,
            worldTagging=worldTagging,
            taggingColours=taggingColours)
        self._worldManagementWidget = gui.HexTableManagerWidget(
            milieu=milieu,
            rules=rules,
            mapStyle=mapStyle,
            mapOptions=mapOptions,
            mapRendering=mapRendering,
            mapAnimations=mapAnimations,
            worldTagging=worldTagging,
            taggingColours=taggingColours,
            allowHexCallback=self._allowWorld,
            hexTable=self._worldTable)
        self._worldManagementWidget.setHexTooltipProvider(
            provider=self._hexTooltipProvider)
        self._worldManagementWidget.setContextMenuPolicy(
            QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self._worldManagementWidget.customContextMenuRequested.connect(
            self._showWorldTableContextMenu)
        self._worldManagementWidget.contentChanged.connect(
            self._tableContentsChanged)

        # Override the tables actions for showing selected/all worlds on a popup map
        # window with actions that will show them on the main map for this window
        showSelectionOnMapAction = QtWidgets.QAction('Show on Map...', self)
        showSelectionOnMapAction.setEnabled(False) # No selection
        showSelectionOnMapAction.triggered.connect(self._showTableSelectionOnMap)
        self._worldManagementWidget.setMenuAction(
            gui.HexTable.MenuAction.ShowSelectionOnMap,
            showSelectionOnMapAction)

        showAllOnMapAction = QtWidgets.QAction('Show All on Map...', self)
        showAllOnMapAction.setEnabled(False) # No content
        showAllOnMapAction.triggered.connect(self._showTableContentOnMap)
        self._worldManagementWidget.setMenuAction(
            gui.HexTable.MenuAction.ShowAllOnMap,
            showAllOnMapAction)

        self._mapWidget = gui.MapWidgetEx(
            milieu=milieu,
            rules=rules,
            style=mapStyle,
            options=mapOptions,
            rendering=mapRendering,
            animated=mapAnimations,
            worldTagging=worldTagging,
            taggingColours=taggingColours)
        self._mapWidget.setSelectionMode(
            mode=gui.MapWidgetEx.SelectionMode.MultiSelect)
        self._mapWidget.selectionChanged.connect(self._mapSelectionChanged)
        self._mapWidget.mapStyleChanged.connect(self._mapStyleChanged)
        self._mapWidget.mapOptionsChanged.connect(self._mapOptionsChanged)
        self._mapWidget.mapRenderingChanged.connect(self._mapRenderingChanged)
        self._mapWidget.mapAnimationChanged.connect(self._mapAnimationChanged)

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
        self._resultsDisplayModeTabView.addTab(self._worldManagementWidget, 'World Details')
        self._resultsDisplayModeTabView.addTab(self._mapWrapperWidget, 'Universe Map')

        groupLayout = QtWidgets.QVBoxLayout()
        groupLayout.addWidget(self._resultsDisplayModeTabView)

        self._worldsGroupBox = QtWidgets.QGroupBox('Worlds')
        self._worldsGroupBox.setLayout(groupLayout)

    def _allowWorld(self, hex: travellermap.HexPosition) -> bool:
        return not self._worldManagementWidget.containsHex(hex)

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

    def _tableContentsChanged(self) -> None:
        with gui.SignalBlocker(widget=self._mapWidget):
            self._mapWidget.clearSelectedHexes()
            for world in self._worldTable.worlds():
                self._mapWidget.selectHex(
                    hex=world.hex(),
                    setInfoHex=False)

    def _mapSelectionChanged(self) -> None:
        oldSelection = set(self._worldManagementWidget.hexes())
        newSelection = set(self._mapWidget.selectedHexes())

        with gui.SignalBlocker(widget=self._worldManagementWidget):
            for hex in oldSelection:
                if hex not in newSelection:
                    self._worldManagementWidget.removeHex(hex=hex)

            for hex in newSelection:
                if hex not in oldSelection:
                    self._worldManagementWidget.addHex(hex=hex)

    def _appConfigChanged(
            self,
            option: app.ConfigOption,
            oldValue: typing.Any,
            newValue: typing.Any
            ) -> None:
        if option is app.ConfigOption.Milieu:
            self._hexTooltipProvider.setMilieu(milieu=newValue)
            self._worldManagementWidget.setMilieu(milieu=newValue)
            self._mapWidget.setMilieu(milieu=newValue)
        elif option is app.ConfigOption.Rules:
            self._tradeGoodTable.setRules(rules=newValue)
            self._hexTooltipProvider.setRules(rules=newValue)
            self._worldManagementWidget.setRules(rules=newValue)
            self._mapWidget.setRules(rules=newValue)
        elif option is app.ConfigOption.MapStyle:
            self._hexTooltipProvider.setMapStyle(style=newValue)
            self._worldManagementWidget.setMapStyle(style=newValue)
            self._mapWidget.setMapStyle(style=newValue)
        elif option is app.ConfigOption.MapOptions:
            self._hexTooltipProvider.setMapOptions(options=newValue)
            self._worldManagementWidget.setMapOptions(options=newValue)
            self._mapWidget.setMapOptions(options=newValue)
        elif option is app.ConfigOption.MapRendering:
            self._worldManagementWidget.setMapRendering(rendering=newValue)
            self._mapWidget.setRendering(rendering=newValue)
        elif option is app.ConfigOption.MapAnimations:
            self._worldManagementWidget.setMapAnimations(enabled=newValue)
            self._mapWidget.setAnimated(animated=newValue)
        elif option is app.ConfigOption.ShowToolTipImages:
            self._hexTooltipProvider.setShowImages(show=newValue)
        elif option is app.ConfigOption.WorldTagging:
            self._hexTooltipProvider.setWorldTagging(tagging=newValue)
            self._worldManagementWidget.setWorldTagging(tagging=newValue)
            self._mapWidget.setWorldTagging(tagging=newValue)
        elif option is app.ConfigOption.TaggingColours:
            self._hexTooltipProvider.setTaggingColours(colours=newValue)
            self._worldManagementWidget.setTaggingColours(colours=newValue)
            self._mapWidget.setTaggingColours(colours=newValue)

    def _mapStyleChanged(
            self,
            style: travellermap.Style
            ) -> None:
        app.Config.instance().setValue(
            option=app.ConfigOption.MapStyle,
            value=style)

    def _mapOptionsChanged(
            self,
            options: typing.Iterable[travellermap.MapOption]
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

    def _showWorldTableContextMenu(self, point: QtCore.QPoint) -> None:
        hasSelection = self._worldManagementWidget.hasSelection()
        hasContent = not self._worldManagementWidget.isEmpty()

        findTradeOptionsForSelectedAction = QtWidgets.QAction('Find Trade Options...', self)
        findTradeOptionsForSelectedAction.setEnabled(hasSelection)
        findTradeOptionsForSelectedAction.triggered.connect(
            lambda: self._findTradeOptions(self._worldManagementWidget.selectedWorlds()))

        findTradeOptionsForAllAction = QtWidgets.QAction('Find Trade Options for All...', self)
        findTradeOptionsForAllAction.setEnabled(hasContent)
        findTradeOptionsForAllAction.triggered.connect(
            lambda: self._findTradeOptions(self._worldManagementWidget.worlds()))

        menu = QtWidgets.QMenu()
        self._worldManagementWidget.fillContextMenu(menu)
        beforeAction = self._worldTable.menuAction(gui.ListTable.MenuAction.CopyAsCsv)
        menu.insertAction(
            beforeAction, # Insert BEFORE this
            findTradeOptionsForSelectedAction)
        menu.insertAction(
            beforeAction, # Insert BEFORE this
            findTradeOptionsForAllAction)
        menu.insertSeparator(
            beforeAction) # Insert BEFORE this
        menu.exec(self._worldManagementWidget.mapToGlobal(point))

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
        infoWindow = gui.WindowManager.instance().showHexDetailsWindow()
        infoWindow.addHexes(hexes=[world.hex() for world in worlds])

    def _showHexesOnMap(
            self,
            hexes: typing.Iterable[travellermap.HexPosition]
            ) -> None:
        if not hexes:
            return

        try:
            self._resultsDisplayModeTabView.setCurrentWidget(
                self._mapWrapperWidget)
            self._mapWidget.centerOnHexes(hexes=hexes)
        except Exception as ex:
            message = 'Failed to show world(s) on map'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)

    def _showTableSelectionOnMap(self) -> None:
        self._showHexesOnMap(hexes=self._worldTable.selectedHexes())

    def _showTableContentOnMap(self) -> None:
        self._showHexesOnMap(hexes=self._worldTable.hexes())

    def _showWelcomeMessage(self) -> None:
        message = gui.InfoDialog(
            parent=self,
            title=self.windowTitle(),
            html=_WelcomeMessage,
            noShowAgainId='WorldComparisonWelcome')
        message.exec()
