import app
import common
import gui
import logging
import logic
import traveller
import travellermap
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

_WelcomeMessage = """
    <html>
    <p>The World Search window allows you to search for worlds that meet specified criteria.
    Filters are used to control which worlds the search will match. Multiple filters can be
    combined to further refine the search (e.g. to find all worlds in the local are that have
    scout bases, a population over 1 million and a law level under 6).</p>
    <p>For Mongoose Traveller players, {name} can calculate Sale and Purchase Trade Scores for
    the chosen worlds. These are calculated as the sum of the Sale and Purchase DMs for a given
    list of Trade Goods. These values are only aimed as a guide but in general the larger the value,
    the better the sale/purchase prices are likely to be. By selecting the Trade Goods the player
    has to sell or selecting the Trade Goods in their purchase range the Trade Score can help
    players quickly identify worlds which may be good options for trading.</p>
    </html>
""".format(name=app.AppName)

class _CustomTradeGoodTable(gui.TradeGoodTable):
    def __init__(self):
        super().__init__()

        self.setCheckable(enable=True)

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

# TODO: This MUST be updated to refresh if the milieu changes.
# The sector/subsector combo boxes should be updated to contain the
# names of sectors/subsectors for the milieu and the comboboxes should
# be resized so they're big enough for the names. If the currently
# selected sector/subsector doesn't exist in the new milieu the selection
# should be set to the 'default'. Filling the combo box drop down on
# demand with the values for the milieu at the point it's displayed
# isn't a great option as it means the combo box doesn't have the correct
# size as it's empty when it's sizing is done.
class _RegionSelectWidget(QtWidgets.QWidget):
    _StateVersion = '_RegionSelectWidget_v1'
    _AllSubsectorsText = '<All Subsectors>'

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        milieu = app.Config.instance().milieu()
        sectorNames = sorted(
            traveller.WorldManager.instance().sectorNames(milieu=milieu),
            key=str.casefold)

        self._sectorComboBox = QtWidgets.QComboBox()
        self._sectorComboBox.addItems(sectorNames)
        self._sectorComboBox.currentIndexChanged.connect(self._selectedSectorChanged)
        self._subsectorComboBox = QtWidgets.QComboBox()
        self._selectedSectorChanged()

        layout = gui.FormLayoutEx()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addRow('Sector:', self._sectorComboBox)
        layout.addRow('Subsector:', self._subsectorComboBox)

        self.setLayout(layout)

    def sectorName(self) -> str:
        return self._sectorComboBox.currentText()

    def subsectorName(self) -> typing.Optional[str]:
        subsectorName = self._subsectorComboBox.currentText()
        return subsectorName if subsectorName != self._AllSubsectorsText else None

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(_RegionSelectWidget._StateVersion)
        stream.writeQString(self.sectorName())
        subsectorName = self.subsectorName()
        stream.writeBool(subsectorName != None)
        if subsectorName:
            stream.writeQString(subsectorName)
        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> None:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != _RegionSelectWidget._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore _RegionSelectWidget state (Incorrect version)')
            return False

        self._sectorComboBox.setCurrentText(stream.readQString())
        if stream.readBool():
            self._subsectorComboBox.setCurrentText(stream.readQString())

        return True

    def _selectedSectorChanged(self) -> None:
        self._subsectorComboBox.clear()
        self._subsectorComboBox.addItem(self._AllSubsectorsText)

        sector = traveller.WorldManager.instance().sectorByName(
            name=self._sectorComboBox.currentText(),
            milieu=app.Config.instance().milieu())
        if not sector:
            return

        subsectorNames = sorted(
            sector.subsectorNames(),
            key=str.casefold)
        self._subsectorComboBox.addItems(subsectorNames)

class _HexSearchRadiusWidget(QtWidgets.QWidget):
    _StateVersion = '_HexSearchRadiusWidget_v1'

    _MinWorldWidgetWidth = 350

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self._hexWidget = gui.HexSelectToolWidget(
            labelText='Center Hex:')
        self._hexWidget.enableMapSelectButton(True)
        self._hexWidget.enableShowInfoButton(True)
        # Setting this to a fixed size is horrible, but no mater what I try I
        # can't get this f*cking thing to expand to fill available space. I
        # suspect it might be something to do with one of layers of widgets or
        # layouts that contain this widget but I can't for the life of me figure
        # out what is wrong. My best guess is it's something to do with the fact
        # this widget ends up being put inside a QGridLayout but my only basis
        # for this is the fact it's the most obvious difference between what is
        # happening for this window and what is happening for something like the
        # jump route planner window where the start/finish world combo boxes do
        # expand to fil available space.
        self._hexWidget.setMinimumWidth(
            int(_HexSearchRadiusWidget._MinWorldWidgetWidth *
                app.Config.instance().interfaceScale()))
        # Enable dead space selection so the user can find things centred around
        # a dead space hex
        self._hexWidget.enableDeadSpaceSelection(enable=True)

        self._radiusSpinBox = gui.SpinBoxEx()
        self._radiusSpinBox.setRange(1, 32)
        radiusLayout = QtWidgets.QHBoxLayout()
        radiusLayout.setContentsMargins(0, 0, 0, 0)
        radiusLayout.addWidget(QtWidgets.QLabel('Search Radius:'))
        radiusLayout.addWidget(self._radiusSpinBox)
        radiusLayout.addStretch()

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._hexWidget)
        layout.addLayout(radiusLayout)

        self.setLayout(layout)

    def centerHex(self) -> typing.Optional[travellermap.HexPosition]:
        return self._hexWidget.selectedHex()

    def searchRadius(self) -> int:
        return self._radiusSpinBox.value()

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(_HexSearchRadiusWidget._StateVersion)

        bytes = self._hexWidget.saveState()
        stream.writeUInt32(bytes.count() if bytes else 0)
        if bytes:
            stream.writeRawData(bytes.data())

        bytes = self._radiusSpinBox.saveState()
        stream.writeUInt32(bytes.count() if bytes else 0)
        if bytes:
            stream.writeRawData(bytes.data())

        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> None:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != _HexSearchRadiusWidget._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore _HexSearchRadiusWidget state (Incorrect version)')
            return False

        count = stream.readUInt32()
        if count > 0:
            if not self._hexWidget.restoreState(
                    QtCore.QByteArray(stream.readRawData(count))):
                return False

        count = stream.readUInt32()
        if count > 0:
            if not self._radiusSpinBox.restoreState(
                    QtCore.QByteArray(stream.readRawData(count))):
                return False

        return True

class WorldSearchWindow(gui.WindowWidget):
    # We need to limit the max results as I was seeing a crash (not in the python code) if to many
    # results were added (i.e. a name search for .*)
    _MaxSearchResults = 2000

    def __init__(self) -> None:
        super().__init__(
            title='World Search',
            configSection='WorldSearchWindow')

        self._scoreRecalculationTimer = None

        self._setupAreaControls()
        self._setupFilterControls()
        self._setupTradeGoodsControls()
        self._setupFoundWorldsControls()

        self._configSplitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        self._configSplitter.addWidget(self._configGroupBox)
        self._configSplitter.addWidget(self._scoredGoodGroupBox)

        configLayout = QtWidgets.QVBoxLayout()
        configLayout.setContentsMargins(0, 0, 0, 0)
        configLayout.addWidget(self._areaGroupBox)
        configLayout.addWidget(self._configSplitter)
        configWidget = QtWidgets.QWidget()
        configWidget.setLayout(configLayout)

        self._leftRightSplitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self._leftRightSplitter.addWidget(configWidget)
        self._leftRightSplitter.addWidget(self._foundWorldsGroupBox)
        self._leftRightSplitter.setStretchFactor(0, 1)
        self._leftRightSplitter.setStretchFactor(1, 100)

        windowLayout = QtWidgets.QVBoxLayout()
        windowLayout.addWidget(self._leftRightSplitter)

        self.setLayout(windowLayout)

    def loadSettings(self) -> None:
        super().loadSettings()

        self._settings.beginGroup(self._configSection)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='UniverseSearchState',
            type=QtCore.QByteArray)
        if storedValue:
            self._universeSearchRadioButton.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='RegionSearchState',
            type=QtCore.QByteArray)
        if storedValue:
            self._regionSearchRadioButton.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='WorldRadiusSearchState',
            type=QtCore.QByteArray)
        if storedValue:
            self._worldRadiusSearchRadioButton.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='RegionSearchConfigState',
            type=QtCore.QByteArray)
        if storedValue:
            self._regionSearchSelectWidget.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='WorldRadiusSearchConfigState',
            type=QtCore.QByteArray)
        if storedValue:
            self._worldRadiusSearchWidget.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='FilterTableState',
            type=QtCore.QByteArray)
        if storedValue:
            self._filterWidget.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='FilterTableContent',
            type=QtCore.QByteArray)
        if storedValue:
            self._filterWidget.restoreContent(storedValue)

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
            key='WorldTableDisplayModeState',
            type=QtCore.QByteArray)
        if storedValue:
            self._worldTableDisplayModeTabs.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='WorldTableState',
            type=QtCore.QByteArray)
        if storedValue:
            self._worldTable.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='MapWidgetState',
            type=QtCore.QByteArray)
        if storedValue:
            self._mapWidget.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='ConfigSplitterState',
            type=QtCore.QByteArray)
        if storedValue:
            self._configSplitter.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='LeftRightSplitterState',
            type=QtCore.QByteArray)
        if storedValue:
            self._leftRightSplitter.restoreState(storedValue)

        self._settings.endGroup()

    def saveSettings(self) -> None:
        self._settings.beginGroup(self._configSection)

        self._settings.setValue('UniverseSearchState', self._universeSearchRadioButton.saveState())
        self._settings.setValue('RegionSearchState', self._regionSearchRadioButton.saveState())
        self._settings.setValue('WorldRadiusSearchState', self._worldRadiusSearchRadioButton.saveState())
        self._settings.setValue('RegionSearchConfigState', self._regionSearchSelectWidget.saveState())
        self._settings.setValue('WorldRadiusSearchConfigState', self._worldRadiusSearchWidget.saveState())
        self._settings.setValue('FilterTableState', self._filterWidget.saveState())
        self._settings.setValue('FilterTableContent', self._filterWidget.saveContent())
        self._settings.setValue('TradeGoodTableState', self._tradeGoodTable.saveState())
        self._settings.setValue('ResultsDisplayModeState', self._resultsDisplayModeTabView.saveState())
        self._settings.setValue('WorldTableDisplayModeState', self._worldTableDisplayModeTabs.saveState())
        self._settings.setValue('WorldTableState', self._worldTable.saveState())
        self._settings.setValue('MapWidgetState', self._mapWidget.saveState())
        self._settings.setValue('ConfigSplitterState', self._configSplitter.saveState())
        self._settings.setValue('LeftRightSplitterState', self._leftRightSplitter.saveState())

        self._settings.endGroup()

        super().saveSettings()

    def firstShowEvent(self, e: QtGui.QShowEvent) -> None:
        # Schedule the Traveller Map init fix to be run shortly after the window is displayed. We
        # can't run it directly here as the window won't have finished being resized (after loading
        # the saved window layout) so the fix won't work.
        QtCore.QTimer.singleShot(1000, self._travellerMapInitFix)
        QtCore.QTimer.singleShot(0, self._showWelcomeMessage)
        return super().firstShowEvent(e)

    def _setupAreaControls(self) -> None:
        self._worldRadiusSearchWidget = _HexSearchRadiusWidget()
        self._worldRadiusSearchRadioButton = gui.RadioButtonEx()
        self._worldRadiusSearchRadioButton.setToolTip('Search for worlds in the area surrounding the specified world.')
        self._worldRadiusSearchRadioButton.toggled.connect(self._worldRadiusSearchToggled)
        self._worldRadiusSearchRadioButton.setChecked(True)

        self._regionSearchSelectWidget = _RegionSelectWidget()
        self._regionSearchSelectWidget.setDisabled(True)
        self._regionSearchRadioButton = gui.RadioButtonEx()
        self._regionSearchRadioButton.setToolTip('Search for worlds in the selected sector/subsector.')
        self._regionSearchRadioButton.toggled.connect(self._regionSearchToggled)

        self._universeSearchRadioButton = gui.RadioButtonEx()
        self._universeSearchRadioButton.setToolTip('Search the entire universe for worlds.')
        self._universeSearchRadioButton.toggled.connect(self._universeSearchToggled)

        layout = QtWidgets.QGridLayout()

        layout.addWidget(
            QtWidgets.QLabel('World Radius:'),
            0, 0,
            QtCore.Qt.AlignmentFlag.AlignRight)
        layout.addWidget(
            self._worldRadiusSearchRadioButton,
            0, 1,
            QtCore.Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(
            self._worldRadiusSearchWidget,
            0, 2,
            QtCore.Qt.AlignmentFlag.AlignLeft)

        layout.addWidget(
            QtWidgets.QLabel('Region:'),
            1, 0,
            QtCore.Qt.AlignmentFlag.AlignRight)
        layout.addWidget(
            self._regionSearchRadioButton,
            1, 1,
            QtCore.Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(
            self._regionSearchSelectWidget,
            1, 2,
            QtCore.Qt.AlignmentFlag.AlignLeft)

        layout.addWidget(
            QtWidgets.QLabel('Universe:'),
            2, 0,
            QtCore.Qt.AlignmentFlag.AlignRight)
        layout.addWidget(
            self._universeSearchRadioButton,
            2, 1,
            QtCore.Qt.AlignmentFlag.AlignLeft)

        layout.setColumnStretch(0, 0)
        layout.setColumnStretch(1, 0)
        layout.setColumnStretch(2, 1)

        self._areaGroupBox = QtWidgets.QGroupBox('Area')
        self._areaGroupBox.setLayout(layout)

    def _setupFilterControls(self) -> None:
        self._filterWidget = gui.WorldFilterTableManagerWidget()

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self._filterWidget)

        self._configGroupBox = QtWidgets.QGroupBox('Filters')
        self._configGroupBox.setLayout(layout)

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

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self._tradeGoodTable)
        layout.addLayout(buttonLayout)

        self._scoredGoodGroupBox = QtWidgets.QGroupBox('Scored Trade Goods')
        self._scoredGoodGroupBox.setLayout(layout)

    def _setupFoundWorldsControls(self) -> None:
        self._findWorldsButton = QtWidgets.QPushButton('Perform Search')
        self._findWorldsButton.clicked.connect(self._findWorlds)

        self._resultsCountLabel = gui.PrefixLabel(prefix='Results Count: ')

        self._worldTableDisplayModeTabs = gui.HexTableTabBar()
        self._worldTableDisplayModeTabs.currentChanged.connect(self._updateWorldTableColumns)

        self._worldTable = gui.WorldTradeScoreTable()
        self._worldTable.setActiveColumns(self._worldColumns())
        self._worldTable.setMinimumHeight(100)
        self._worldTable.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self._worldTable.customContextMenuRequested.connect(self._showWorldTableContextMenu)

        tableLayout = QtWidgets.QVBoxLayout()
        tableLayout.setContentsMargins(0, 0, 0, 0)
        tableLayout.setSpacing(0) # No spacing between tabs and table
        tableLayout.addWidget(self._worldTableDisplayModeTabs)
        tableLayout.addWidget(self._worldTable)
        tableLayoutWidget = QtWidgets.QTabWidget()
        tableLayoutWidget.setLayout(tableLayout)

        self._mapWidget = gui.MapWidgetEx()
        self._mapWidget.enableDeadSpaceSelection(enable=True)

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
        self._resultsDisplayModeTabView.addTab(tableLayoutWidget, 'World Details')
        self._resultsDisplayModeTabView.addTab(self._mapWrapperWidget, 'Universe Map')

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self._findWorldsButton)
        layout.addWidget(self._resultsCountLabel)
        layout.addWidget(self._resultsDisplayModeTabView)

        self._foundWorldsGroupBox = QtWidgets.QGroupBox('Worlds')
        self._foundWorldsGroupBox.setLayout(layout)

    # This is a MASSIVE hack. It works around the fact the Traveller Map widget isn't resized until
    # its tab is displayed. This caused zooming to the jump route to not zoom to the correct area
    # if the route was calculated before the widget was displayed for the first time. The hack works
    # by checking if the Traveller Map widget is not the displayed widget and forces a resize if
    # it's not.
    # TODO: This can be removed when I finally ditch the web map widget
    def _travellerMapInitFix(self) -> None:
        currentWidget = self._resultsDisplayModeTabView.currentWidget()
        if currentWidget != self._mapWidget:
            size = currentWidget.size()
            self._mapWidget.resize(size)
            self._mapWidget.show()

    def _worldColumns(self) -> typing.List[gui.HexTable.ColumnType]:
        displayMode = self._worldTableDisplayModeTabs.currentDisplayMode()
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

    def _universeSearchToggled(self, selected: bool) -> None:
        pass

    def _regionSearchToggled(self, selected: bool) -> None:
        self._regionSearchSelectWidget.setDisabled(not selected)

    def _worldRadiusSearchToggled(self, selected: bool) -> None:
        self._worldRadiusSearchWidget.setDisabled(not selected)

    def _scoreRecalculationTimerFired(self) -> None:
        if not self._worldTable:
            # This should never happen but handle it just in case
            return
        self._worldTable.setTradeGoods(tradeGoods=self._tradeGoodTable.checkedTradeGoods())

    def _findWorlds(self) -> None:
        self._worldTable.removeAllRows()
        self._worldTable.setTradeGoods(
            tradeGoods=self._tradeGoodTable.checkedTradeGoods())
        self._resultsCountLabel.setText(common.formatNumber(0))
        self._mapWidget.clearHexHighlights()

        foundWorlds = None
        try:
            worldFilter = logic.WorldSearch()
            worldFilter.setLogic(filterLogic=self._filterWidget.filterLogic())
            worldFilter.setFilters(filters=self._filterWidget.filters())

            if self._universeSearchRadioButton.isChecked():
                foundWorlds = worldFilter.search(
                    milieu=app.Config.instance().milieu(),
                    maxResults=self._MaxSearchResults)
            elif self._regionSearchRadioButton.isChecked():
                foundWorlds = worldFilter.searchRegion(
                    milieu=app.Config.instance().milieu(),
                    sectorName=self._regionSearchSelectWidget.sectorName(),
                    subsectorName=self._regionSearchSelectWidget.subsectorName(),
                    maxResults=self._MaxSearchResults)
            elif self._worldRadiusSearchRadioButton.isChecked():
                hex = self._worldRadiusSearchWidget.centerHex()
                if not hex:
                    gui.MessageBoxEx.information(
                        parent=self,
                        text='Select a hex to center the search radius around')
                    return
                foundWorlds = worldFilter.searchArea(
                    milieu=app.Config.instance().milieu(),
                    centerHex=hex,
                    searchRadius=self._worldRadiusSearchWidget.searchRadius())
                if len(foundWorlds) > self._MaxSearchResults:
                    foundWorlds = foundWorlds[:self._MaxSearchResults]
        except Exception as ex:
            message = 'Failed to find nearby worlds'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return
        if not foundWorlds:
            gui.AutoSelectMessageBox.information(
                parent=self,
                text='No results found for the current search criteria',
                stateKey='WorldSearchNoResultsFound')
            return

        if len(foundWorlds) >= self._MaxSearchResults:
            gui.AutoSelectMessageBox.information(
                parent=self,
                text=f'The number of search results has been limited to {self._MaxSearchResults}',
                stateKey='WorldSearchResultCountCapped')

        self._worldTable.addWorlds(worlds=foundWorlds)
        self._resultsCountLabel.setText(common.formatNumber(len(foundWorlds)))

        self._showWorldsOnMap(
            worlds=foundWorlds,
            highlightWorlds=True,
            switchTab=False)

    def _updateWorldTableColumns(self, index: int) -> None:
        self._worldTable.setActiveColumns(self._worldColumns())

    def _showWorldTableContextMenu(self, point: QtCore.QPoint) -> None:
        world = self._worldTable.worldAt(y=point.y())

        menuItems = [
            gui.MenuItem(
                text='Find Trade Options for Selected Worlds...',
                callback=lambda: self._findTradeOptions(self._worldTable.selectedWorlds()),
                enabled=self._worldTable.hasSelection()
            ),
            gui.MenuItem(
                text='Find Trade Options for All Worlds...',
                callback=lambda: self._findTradeOptions(self._worldTable.worlds()),
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
                text='Show Selected Worlds on Map...',
                callback=lambda: self._showWorldsOnMap(self._worldTable.selectedWorlds()),
                enabled=self._worldTable.hasSelection()
            ),
            gui.MenuItem(
                text='Show All Worlds on Map...',
                callback=lambda: self._showWorldsOnMap(self._worldTable.worlds()),
                enabled=not self._worldTable.isEmpty()
            ),
            None, # Separator
            gui.MenuItem(
                text='Show Trade Score Calculations...',
                callback=lambda: self._showTradeScoreCalculations(world),
                enabled=world != None
            ),
        ]

        gui.displayMenu(
            self,
            menuItems,
            self._worldTable.viewport().mapToGlobal(point)
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

    def _showWorldDetails(
            self,
            worlds: typing.Iterable[traveller.World]
            ) -> None:
        infoWindow = gui.WindowManager.instance().showWorldDetailsWindow()
        infoWindow.addHexes(hexes=worlds)

    def _showTradeScoreCalculations(
            self,
            row: int
            ) -> None:
        try:
            tradeScore = self._worldTable.tradeScore(row=row)
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

    def _showWorldsOnMap(
            self,
            worlds: typing.Iterable[traveller.World],
            highlightWorlds: bool = False,
            switchTab: bool = True
            ) -> None:
        try:
            if switchTab:
                self._resultsDisplayModeTabView.setCurrentWidget(
                    self._mapWrapperWidget)

            hexes = [world.hex() for world in worlds]
            if highlightWorlds:
                # Clear old highlight when highlighting new worlds
                self._mapWidget.clearHexHighlights()
                self._mapWidget.highlightHexes(hexes=hexes)
            self._mapWidget.centerOnHexes(hexes=hexes)
        except Exception as ex:
            message = 'Failed to show world(s) on map'
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
            noShowAgainId='WorldSearchWelcome')
        message.exec()
