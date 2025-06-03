import app
import asyncio
import depschecker
import enum
import gui
import json
import logging
import logic
import proxy
import traveller
import travellermap
import typing
import urllib.parse
from PyQt5 import QtWidgets, QtCore, QtGui

_WelcomeMessage = """
    <html>
    <p>The Configuration window, as you might expect, allows you to configure {name}. The majority
    of the options relate to tagging. This is an {name} feature where the user can choose to assign
    different world attributes a tag level of Desirable, Warning or Danger.<p>
    <p>When displaying world information, {name} will highlight tagged attributes. This highlighting
    is intended to allow players to quickly identify worlds they may want to visit and worlds they
    might want to avoid. Examples of this would be a trading crew tagging agricultural worlds as
    Desirable as textiles should be an easy profit or a crew of reprobates tagging worlds with scout
    bases as Danger because they're in a stolen scout ship.</p>
    <p>The individually tagged attributes are also used to generate an overall tag level for the
    world. The logic for calculating the overall tag level is simply:
    <ol style="margin-left:15px; -qt-list-indent:0;">
    <li>If the world has any attributes tagged as Danger, its overall tag level is Danger</li>
    <li>If the world has any attributes tagged as Warning, its overall tag level is Warning<li>
    <li>If the world has any attributes tagged as Desirable, its overall tag level is Desirable<li>
    <li>If the world no tagged attributes, it has no overall tag level<li>
    </ol></p>
    </html>
""".format(name=app.AppName)

_RestartRequiredParagraph = \
    f'<p><b>Changes to this setting will be applied next time {app.AppName} is started</b></p>'

_StarPortFuelToolTip = gui.createStringToolTip(
    """
    <p>This lets you specify what types of fuel are available at different
    classes of starport based on your interpretation of the rules.</p>
    <p>In the Mongoose rules there is some ambiguity around what types of fuel
    are available at different classes of starport. The 1e, 2e & 2022 core
    rules all have tables that state refined fuel is available at class A/B
    starports and unrefined fuel is available at C/D starports. They makes no
    mention of if unrefined fuel is also available at class A/B starports. The
    2e Traveller Companion (p125) muddies the water further by stating that
    refined and unrefined fuel is available at class A starports, making no
    mention of what fuel is available at class B starports but then stating
    that unrefined _and_ refined fuel is usually available at class C
    starports.</p>
    <p>T5 core rules are much clearer, explicitly stating that class A/B
    starports sell refined and unrefined fuel and class C/D only sell unrefined
    fuel (p267).</p>
    <p>The 1982 CT rules are a little less clear, however, the descriptions of
    the starport types (p84) state "Only unrefined fuel available." for class
    C/D starports but "Refined fuel available." for class A/B. The fact the
    class A/B description does\'t say "<i>Only</i> refined fuel available."
    would imply that unrefined fuel is also available. This seems to be backed
    up by the description of Alell Down Starport in the example adventure
    (p141), where it\'s stated to be a class B starport and to sell refined and
    unrefined fuel.</p>
    """ + _RestartRequiredParagraph,
    escape=False)

# This intentionally doesn't inherit from DialogEx. We don't want it saving its size as it
# can cause incorrect sizing if the font scaling is increased then decreased
class _ClearTileCacheDialog(QtWidgets.QDialog):
    _WorkingDotCount = 5

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent=parent)

        self._request = None

        self._workingLabel = gui.PrefixLabel(
            prefix='Communicating with proxy')

        self._workingTimer = QtCore.QTimer()
        self._workingTimer.timeout.connect(self._workingTimerFired)
        self._workingTimer.setInterval(500)
        self._workingTimer.setSingleShot(False)

        self._cancelButton = QtWidgets.QPushButton('Cancel')
        self._cancelButton.clicked.connect(self._cancelRequest)

        windowLayout = QtWidgets.QVBoxLayout()
        windowLayout.addWidget(self._workingLabel)
        windowLayout.addWidget(self._cancelButton)

        self.setWindowTitle('Clearing Cache')
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowType.WindowContextHelpButtonHint)
        self.setSizeGripEnabled(False)
        self.setLayout(windowLayout)

        # Setting up the title bar needs to be done before the window is show to take effect. It
        # needs to be done every time the window is shown as the setting is lost if the window is
        # closed then reshown
        gui.configureWindowTitleBar(widget=self)

    def exec(self) -> int:
        try:
            clearCacheUrl = urllib.parse.urljoin(
                proxy.MapProxy.instance().accessUrl(),
                '/proxy/clearcache')
            self._request = app.AsyncRequest(parent=self)
            self._request.complete.connect(self._requestComplete)
            self._request.get(
                url=clearCacheUrl,
                loop=asyncio.get_event_loop())
        except Exception as ex:
            message = 'Failed to initiate request to clear cache'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            # Closing a dialog from showEvent doesn't work so schedule it to happen immediately after
            # the window is shown
            QtCore.QTimer.singleShot(0, self.close)

        return super().exec()

    def showEvent(self, e: QtGui.QShowEvent) -> None:
        if not e.spontaneous():
            # Setting up the title bar needs to be done before the window is show to take effect. It
            # needs to be done every time the window is shown as the setting is lost if the window is
            # closed then reshown
            gui.configureWindowTitleBar(widget=self)

        return super().showEvent(e)

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        if self._request:
            self._request.cancel()
            self._request = None
        return super().closeEvent(a0)

    def _cancelRequest(self) -> None:
        if self._request:
            self._request.cancel()
            self._request = None
        self.close()

    def _requestComplete(
            self,
            result: typing.Union[app.AsyncResponse, Exception]
            ) -> None:
        self._workingTimer.stop()

        if isinstance(result, app.AsyncResponse):
            try:
                response = json.loads(result.content().decode())
                message = 'Cleared {memTiles} tiles from memory and {diskTiles} from disk'.format(
                    memTiles=response["memoryTiles"],
                    diskTiles=response["diskTiles"])
                gui.MessageBoxEx.information(
                    parent=self,
                    text=message)
            except Exception as ex:
                message = 'Clearing the tile cache succeeded but parsing response failed'
                logging.warning(message, exc_info=ex)
                gui.MessageBoxEx.warning(
                    parent=self,
                    text=message,
                    exception=ex)
            self.accept()
        elif isinstance(result, Exception):
            message = 'Request to clear tile cache failed'
            logging.error(message, exc_info=result)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=result)
            self.close()
        else:
            message = 'Request to clear tile cache returned an unexpected result'
            logging.critical(message, exc_info=result)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=result)
            self.close()

    def _workingTimerFired(self) -> None:
        text = self._workingLabel.text()
        if (len(text) % _ClearTileCacheDialog._WorkingDotCount) == 0:
            text = ''
        text += '.'
        self._workingLabel.setText(text)

# TODO: This pane should update if the user changes the tagging colours on
# the main pane
class _TaggingTable(gui.ListTable):
    def __init__(
            self,
            taggingConfig: typing.Dict[typing.Union[str, enum.Enum], app.TagLevel],
            taggingColours: app.TaggingColours,
            keyColumnName: str,
            keyDescriptions: typing.Dict[typing.Union[str, enum.Enum], str],
            keyAliases: typing.Optional[typing.Dict[typing.Union[str, enum.Enum], str]] = None,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self._taggingMap = dict(taggingConfig)
        self._taggingColours = app.TaggingColours(taggingColours)
        self._keyColumnName = keyColumnName
        self._keyDescriptions = dict(keyDescriptions)
        self._keyAliases = dict(keyAliases) if keyAliases else {}
        self._tableFilled = False

        columnNames = [keyColumnName, 'Tag Level', 'Description']

        self.setColumnHeaders(columnNames)
        self.setColumnsMoveable(False)
        self.resizeColumnsToContents() # Size columns to header text
        self.setSizeAdjustPolicy(
            QtWidgets.QAbstractScrollArea.SizeAdjustPolicy.AdjustToContentsOnFirstShow)

        # Setup horizontal scroll bar. Setting the last column to stretch to fit its content
        # is required to make the it appear reliably
        self.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.horizontalHeader().setSectionResizeMode(
            self.columnCount() - 1,
            QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setStretchLastSection(False)

        # Disable sorting as some tables (e.g. luminosity) have a natural order that is not
        # ordered alphabetically so it makes sense to keep them in that order
        self.setSortingEnabled(False)

        # Set default column widths
        self.setColumnWidth(1, 100)
        self.horizontalHeader().setStretchLastSection(True)

    def taggingConfig(self) -> typing.Dict[typing.Union[str, enum.Enum], typing.Optional[app.TagLevel]]:
        if not self._tableFilled:
            return dict(self._taggingMap)

        tagging = {}
        for row in range(self.rowCount()):
            comboBox: gui.TagLevelComboBox = self.cellWidget(row, 1)
            if not isinstance(comboBox, gui.TagLevelComboBox):
                continue

            tagLevel = comboBox.currentTagLevel()
            if not tagLevel:
                continue

            item = self.item(row, 0)
            key = item.data(QtCore.Qt.ItemDataRole.UserRole)
            tagging[key] = tagLevel
        return tagging

    def setTaggingColours(self, colours: app.TaggingColours) -> None:
        if colours == self._taggingColours:
            return

        self._taggingColours = app.TaggingColours(colours)
        self._syncToTagging()

    def showEvent(self, event: typing.Optional[QtGui.QShowEvent]) -> None:
        self._fillTable()
        return super().showEvent(event)

    def _fillTable(self) -> None:
        if self._tableFilled:
            return # Nothing to do

        self._tableFilled = True

        for row, (key, description) in enumerate(self._keyDescriptions.items()):
            self.insertRow(row)

            toolTip = gui.createStringToolTip(description)

            keyText = self._keyAliases.get(key)
            if keyText is None:
                keyText = key.name if isinstance(key, enum.Enum) else key

            item = QtWidgets.QTableWidgetItem(keyText)
            item.setData(QtCore.Qt.ItemDataRole.UserRole, key)
            item.setToolTip(toolTip)
            self.setItem(row, 0, item)

            tagLevel = self._taggingMap.get(key)

            item = QtWidgets.QTableWidgetItem()
            item.setToolTip(toolTip)
            self.setItem(row, 1, item)
            comboBox = gui.TagLevelComboBox(
                value=tagLevel,
                colours=self._taggingColours)
            # Set the background role of the combo box to the same background role that will be used
            # for the alternating rows in the table. This makes sure the combo boxes have the same
            # colour as the rest of the row (when no tag level is selected). Note that this will most
            # likely break if sorting is ever enabled on the table
            comboBox.setBackgroundRole(QtGui.QPalette.ColorRole.AlternateBase if row % 2 else QtGui.QPalette.ColorRole.Base)
            self.setCellWidget(row, 1, comboBox)

            item = QtWidgets.QTableWidgetItem(description)
            item.setToolTip(toolTip)
            self.setItem(row, 2, item)

    def _syncToTagging(self) -> None:
        for row in range(self.rowCount()):
            comboBox: gui.TagLevelComboBox = self.cellWidget(row, 1)
            if isinstance(comboBox, gui.TagLevelComboBox):
                comboBox.setColours(self._taggingColours)

class ConfigDialog(gui.DialogEx):
    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            title='Configuration',
            configSection='ConfigDialog',
            parent=parent)

        self._tabWidget = gui.VerticalTabWidget()

        self._setupGeneralTab()
        self._setupRulesTab()
        self._setupZoneTaggingTab()
        self._setupStarPortTaggingTab()
        self._setupWorldSizeTaggingTab()
        self._setupAtmosphereTaggingTab()
        self._setupHydrographicsTaggingTab()
        self._setupPopulationTaggingTab()
        self._setupGovernmentTaggingTab()
        self._setupLawLevelTaggingTab()
        self._setupTechLevelTaggingTab()
        self._setupTradeCodeTaggingTab()
        self._setupBaseTypeTaggingTab()
        self._setupResourcesTaggingTab()
        self._setupLabourTaggingTab()
        self._setupInfrastructureTaggingTab()
        self._setupEfficiencyTaggingTab()
        self._setupHeterogeneityTaggingTab()
        self._setupAcceptanceTaggingTab()
        self._setupStrangenessTaggingTab()
        self._setupSymbolsTaggingTab()
        self._setupNobilityTaggingTab()
        self._setupAllegianceTaggingTab()
        self._setupSpectralTaggingTab()
        self._setupLuminosityTaggingTab()
        self._setupButtons()

        dialogLayout = QtWidgets.QVBoxLayout()
        dialogLayout.addWidget(self._tabWidget)
        dialogLayout.addLayout(self._buttonLayout)

        self.setLayout(dialogLayout)
        self.showMaximizeButton()

    def firstShowEvent(self, e: QtGui.QShowEvent) -> None:
        QtCore.QTimer.singleShot(0, self._showWelcomeMessage)
        super().firstShowEvent(e)

    def accept(self) -> None:
        if not self._validateConfig():
            return
        self._saveConfig()
        super().accept()

    def loadSettings(self) -> None:
        super().loadSettings()

        self._settings.beginGroup(self._configSection)

        storedState = gui.safeLoadSetting(
            settings=self._settings,
            key='ZoneTaggingTableState',
            type=QtCore.QByteArray)
        if storedState:
            self._zoneTaggingTable.restoreState(storedState)

        storedState = gui.safeLoadSetting(
            settings=self._settings,
            key='StarPortTaggingTableState',
            type=QtCore.QByteArray)
        if storedState:
            self._starPortTaggingTable.restoreState(storedState)

        storedState = gui.safeLoadSetting(
            settings=self._settings,
            key='WorldSizeTaggingTableState',
            type=QtCore.QByteArray)
        if storedState:
            self._worldSizeTaggingTable.restoreState(storedState)

        storedState = gui.safeLoadSetting(
            settings=self._settings,
            key='AtmosphereTaggingTableState',
            type=QtCore.QByteArray)
        if storedState:
            self._atmosphereTaggingTable.restoreState(storedState)

        storedState = gui.safeLoadSetting(
            settings=self._settings,
            key='HydrographicsTaggingTableState',
            type=QtCore.QByteArray)
        if storedState:
            self._hydrographicsTaggingTable.restoreState(storedState)

        storedState = gui.safeLoadSetting(
            settings=self._settings,
            key='PopulationTaggingTableState',
            type=QtCore.QByteArray)
        if storedState:
            self._populationTaggingTable.restoreState(storedState)

        storedState = gui.safeLoadSetting(
            settings=self._settings,
            key='GovernmentTaggingTableState',
            type=QtCore.QByteArray)
        if storedState:
            self._governmentTaggingTable.restoreState(storedState)

        storedState = gui.safeLoadSetting(
            settings=self._settings,
            key='LawLevelTaggingTableState',
            type=QtCore.QByteArray)
        if storedState:
            self._lawLevelTaggingTable.restoreState(storedState)

        storedState = gui.safeLoadSetting(
            settings=self._settings,
            key='TechLevelTaggingTableState',
            type=QtCore.QByteArray)
        if storedState:
            self._techLevelTaggingTable.restoreState(storedState)

        storedState = gui.safeLoadSetting(
            settings=self._settings,
            key='BaseTypeTaggingTableState',
            type=QtCore.QByteArray)
        if storedState:
            self._baseTypeTaggingTable.restoreState(storedState)

        storedState = gui.safeLoadSetting(
            settings=self._settings,
            key='TradeCodeTaggingTableState',
            type=QtCore.QByteArray)
        if storedState:
            self._tradeCodeTaggingTable.restoreState(storedState)

        storedState = gui.safeLoadSetting(
            settings=self._settings,
            key='ResourcesTaggingTableState',
            type=QtCore.QByteArray)
        if storedState:
            self._resourcesTaggingTable.restoreState(storedState)

        storedState = gui.safeLoadSetting(
            settings=self._settings,
            key='LabourTaggingTableState',
            type=QtCore.QByteArray)
        if storedState:
            self._labourTaggingTable.restoreState(storedState)

        storedState = gui.safeLoadSetting(
            settings=self._settings,
            key='InfrastructureTaggingTableState',
            type=QtCore.QByteArray)
        if storedState:
            self._infrastructureTaggingTable.restoreState(storedState)

        storedState = gui.safeLoadSetting(
            settings=self._settings,
            key='EfficiencyTaggingTableState',
            type=QtCore.QByteArray)
        if storedState:
            self._efficiencyTaggingTable.restoreState(storedState)

        storedState = gui.safeLoadSetting(
            settings=self._settings,
            key='HeterogeneityTaggingTableState',
            type=QtCore.QByteArray)
        if storedState:
            self._heterogeneityTaggingTable.restoreState(storedState)

        storedState = gui.safeLoadSetting(
            settings=self._settings,
            key='AcceptanceTaggingTableState',
            type=QtCore.QByteArray)
        if storedState:
            self._acceptanceTaggingTable.restoreState(storedState)

        storedState = gui.safeLoadSetting(
            settings=self._settings,
            key='StrangenessTaggingTableState',
            type=QtCore.QByteArray)
        if storedState:
            self._strangenessTaggingTable.restoreState(storedState)

        storedState = gui.safeLoadSetting(
            settings=self._settings,
            key='SymbolsTaggingTableState',
            type=QtCore.QByteArray)
        if storedState:
            self._symbolsTaggingTable.restoreState(storedState)

        storedState = gui.safeLoadSetting(
            settings=self._settings,
            key='NobilityTaggingTableState',
            type=QtCore.QByteArray)
        if storedState:
            self._nobilityTaggingTable.restoreState(storedState)

        storedState = gui.safeLoadSetting(
            settings=self._settings,
            key='AllegianceTaggingTableState',
            type=QtCore.QByteArray)
        if storedState:
            self._allegianceTaggingTable.restoreState(storedState)

        storedState = gui.safeLoadSetting(
            settings=self._settings,
            key='SpectralTaggingTableState',
            type=QtCore.QByteArray)
        if storedState:
            self._spectralTaggingTable.restoreState(storedState)

        storedState = gui.safeLoadSetting(
            settings=self._settings,
            key='LuminosityTaggingTableState',
            type=QtCore.QByteArray)
        if storedState:
            self._luminosityTaggingTable.restoreState(storedState)

        self._settings.endGroup()

    def saveSettings(self) -> None:
        super().saveSettings()

        # Note that this is saving the state of the various tables not the actual configuration
        self._settings.beginGroup(self._configSection)
        self._settings.setValue('ZoneTaggingTableState', self._zoneTaggingTable.saveState())
        self._settings.setValue('StarPortTaggingTableState', self._starPortTaggingTable.saveState())
        self._settings.setValue('WorldSizeTaggingTableState', self._worldSizeTaggingTable.saveState())
        self._settings.setValue('AtmosphereTaggingTableState', self._atmosphereTaggingTable.saveState())
        self._settings.setValue('HydrographicsTaggingTableState', self._hydrographicsTaggingTable.saveState())
        self._settings.setValue('PopulationTaggingTableState', self._populationTaggingTable.saveState())
        self._settings.setValue('GovernmentTaggingTableState', self._governmentTaggingTable.saveState())
        self._settings.setValue('LawLevelTaggingTableState', self._lawLevelTaggingTable.saveState())
        self._settings.setValue('TechLevelTaggingTableState', self._techLevelTaggingTable.saveState())
        self._settings.setValue('BaseTypeTaggingTableState', self._baseTypeTaggingTable.saveState())
        self._settings.setValue('TradeCodeTaggingTableState', self._tradeCodeTaggingTable.saveState())
        self._settings.setValue('ResourcesTaggingTableState', self._resourcesTaggingTable.saveState())
        self._settings.setValue('LabourTaggingTableState', self._labourTaggingTable.saveState())
        self._settings.setValue('InfrastructureTaggingTableState', self._infrastructureTaggingTable.saveState())
        self._settings.setValue('EfficiencyTaggingTableState', self._efficiencyTaggingTable.saveState())
        self._settings.setValue('HeterogeneityTaggingTableState', self._heterogeneityTaggingTable.saveState())
        self._settings.setValue('AcceptanceTaggingTableState', self._acceptanceTaggingTable.saveState())
        self._settings.setValue('StrangenessTaggingTableState', self._strangenessTaggingTable.saveState())
        self._settings.setValue('SymbolsTaggingTableState', self._symbolsTaggingTable.saveState())
        self._settings.setValue('NobilityTaggingTableState', self._nobilityTaggingTable.saveState())
        self._settings.setValue('AllegianceTaggingTableState', self._allegianceTaggingTable.saveState())
        self._settings.setValue('SpectralTaggingTableState', self._spectralTaggingTable.saveState())
        self._settings.setValue('LuminosityTaggingTableState', self._luminosityTaggingTable.saveState())
        self._settings.endGroup()

    def _setupGeneralTab(self) -> None:
        ColourButtonWidth = 75

        # Traveller widgets
        self._milieuComboBox = gui.EnumComboBox(
            type=travellermap.Milieu,
            value=app.Config.instance().value(
                option=app.ConfigOption.Milieu,
                futureValue=True),
            textMap={milieu: travellermap.milieuDescription(milieu) for milieu in  travellermap.Milieu})
        self._milieuComboBox.setToolTip(gui.createStringToolTip(
            '<p>The milieu to use when determining sector and world information</p>' +
            _RestartRequiredParagraph,
            escape=False))

        rules = app.Config.instance().value(
            option=app.ConfigOption.Rules,
            futureValue=True)

        self._rulesComboBox = gui.EnumComboBox(
            type=traveller.RuleSystem,
            value=rules.system())
        self._rulesComboBox.setToolTip(gui.createStringToolTip(
            '<p>The rules used for trade calculations</p>' +
            _RestartRequiredParagraph,
            escape=False))

        travellerLayout = gui.FormLayoutEx()
        travellerLayout.addRow(
            'Milieu:',
            self._milieuComboBox)
        travellerLayout.addRow(
            'Rule System:',
            self._rulesComboBox)

        travellerGroupBox = QtWidgets.QGroupBox('Traveller')
        travellerGroupBox.setLayout(travellerLayout)

        self._mapEngineComboBox = gui.EnumComboBox(
            type=app.MapEngine,
            value=app.Config.instance().value(
                option=app.ConfigOption.MapEngine,
                futureValue=True))
        self._mapEngineComboBox.currentIndexChanged.connect(
            self._renderingTypeChanged)
        self._mapEngineComboBox.setToolTip(gui.createStringToolTip(
            '<p>Select how the map will be rendered.</p>'
            '<ul style="list-style-type:none; margin-left:0px; -qt-list-indent:0;">'
            '<li><b>Local</b> - By default, {app} uses its own map rendering '
            'code to draw the map. This is a reimplementation of the Traveller '
            'Map rendering code (in Python) and is intended to replicate the '
            'look of the Traveller Map website as closely as possible, '
            'however, it\'s not a pixel perfect recreation, so there may be '
            'some very minor differences. As this rendering is done locally, '
            'on most systems, it will be the fastest option. Local rendering '
            'is also the recommended type when using custom sectors, as it '
            'doesn\'t suffer from any of the compositing artifacts seen when '
            'using the Web (Proxy) rendering.</li>'
            '<li><b>Web (Proxy)</b> - When using Web (Proxy) rendering, {app} '
            'uses a built-in web browser to display the Traveller Map website '
            'with, access to it going through a local proxy. This proxy is '
            'used to cache map tiles for faster access and overlay custom '
            'sectors on those map tiles.</li>'
            '<li><b>Web (Direct)</b> - When using Web (Direct) rendering, '
            '{app} uses a built-in web browser to display the Traveller Map '
            'website. Custom sectors are not supported when using Web (Direct) '
            'rendering.</li>'
            '</ul>'.format(app=app.AppName) +
            _RestartRequiredParagraph,
            escape=False))

        # Proxy Widgets
        isProxyEnabled = self._mapEngineComboBox.currentEnum() is app.MapEngine.WebProxy

        self._proxyPortSpinBox = gui.SpinBoxEx()
        self._proxyPortSpinBox.setRange(1024, 65535)
        self._proxyPortSpinBox.setValue(app.Config.instance().value(
            option=app.ConfigOption.ProxyPort,
            futureValue=True))
        self._proxyPortSpinBox.setEnabled(isProxyEnabled)
        self._proxyPortSpinBox.setToolTip(gui.createStringToolTip(
            '<p>Specify the port the local Traveller Map proxy will listen '
            'on.</p>' \
            '<p>You may need to change the port the proxy listens on if there '
            'is a conflict with another service running on your system.</p>' +
            _RestartRequiredParagraph,
            escape=False))

        self._proxyHostPoolSizeSpinBox = gui.SpinBoxEx()
        self._proxyHostPoolSizeSpinBox.setRange(1, 10)
        self._proxyHostPoolSizeSpinBox.setValue(app.Config.instance().value(
            option=app.ConfigOption.ProxyHostPoolSize,
            futureValue=True))
        self._proxyHostPoolSizeSpinBox.setEnabled(isProxyEnabled)
        self._proxyHostPoolSizeSpinBox.setToolTip(gui.createStringToolTip(
            '<p>Specify the number of localhost addresses the proxy will '
            'listen on.</p>'
            '<p>The Chromium browser that {app} uses to display Traveller Map '
            'has a hard coded limit of 6 simultaneous connections to a single '
            'host. This is a standard feature of browsers to prevent excessive '
            'load being put on a site. However, this limitation can reduce '
            'rendering performance as the browser may delay requests for tiles '
            'that the proxy could satisfy using its tile cache. To work around '
            'this issue, the proxy can listen on multiple localhost addresses '
            '(e.g. 127.0.0.1, 127.0.0.2), with requests for tiles are then '
            'spread evenly over all these addresses.</p>'
            '<p><b>This setting only affects the number of simultaneous '
            'connections made to the proxy in order to allow better use of the '
            'tile cache. The proxy will enforce a limit of 6 simultaneous '
            'outgoing connections to travellermap.com so as not to place '
            'additional load on the site.</b></p>'.format(app=app.AppName) +
            _RestartRequiredParagraph,
            escape=False))

        self._proxyMapUrlLineEdit = gui.LineEditEx()
        self._proxyMapUrlLineEdit.setText(app.Config.instance().value(
            option=app.ConfigOption.ProxyMapUrl,
            futureValue=True))
        self._proxyMapUrlLineEdit.setMaximumWidth(200)
        self._proxyMapUrlLineEdit.setEnabled(isProxyEnabled)
        self._proxyMapUrlLineEdit.setToolTip(gui.createStringToolTip(
            '<p>Specify the URL the proxy will use to access Traveller Map.</p>'
            '<p>If you run your own copy of Traveller Map, you can specify its '
            'URL here.</p>' +
            _RestartRequiredParagraph,
            escape=False))

        # The proxy mode control is only shown if CairoSVG is detected. It's used
        # to set the flag to indicate if SVG composition is enabled. It's shown as a
        # combo box to make it easier to explain to the user what the difference is
        # between having it enabled and disabled.
        self._proxyCompositionModeComboBox = gui.ComboBoxEx()
        self._proxyCompositionModeComboBox.addItem('Hybrid', False)
        self._proxyCompositionModeComboBox.addItem('SVG', True)
        self._proxyCompositionModeComboBox.setCurrentByUserData(
            userData=app.Config.instance().value(
                option=app.ConfigOption.ProxySvgComposition,
                futureValue=True))
        self._proxyCompositionModeComboBox.setEnabled(isProxyEnabled)
        self._proxyCompositionModeComboBox.setHidden(
            not depschecker.DetectedCairoSvgState)
        self._proxyCompositionModeComboBox.currentIndexChanged.connect(
            self._proxyModeChanged)
        self._proxyCompositionModeComboBox.setToolTip(gui.createStringToolTip(
            '<p>Change the type of composition used when overlaying custom '
            'sectors onto tiles from Traveller Map.</p>'
            '<p>When CairoSVG is installed, there are multiple ways the proxy '
            'can composite tiles.</p>'
            '<ul style="list-style-type:none; margin-left:0px; -qt-list-indent:0;">'
            '<li><b>Hybrid</b> - Traveller map is used to generate SVG posters '
            'of the custom sectors, however, these posters are processed to '
            'split them into multiple bitmap layers prior to composition. '
            'These bitmap layers are then used to composite individual tiles. '
            'This method is fast but can result in slight blockiness at '
            'higher zoom levels.'
            '<li><b>SVG</b> - Traveller map is used to generate SVG posters of '
            'the custom sectors and these SVG are composited directly onto '
            'tiles. This prevents blockiness at high zoom levels, however, '
            'it\'s <b>significantly</b> more CPU intensive than Hybrid '
            'composition and should only be used on systems with high core '
            'counts (and even then I don\'t really recommend it).</ul> '
            '</ul>' +
            _RestartRequiredParagraph,
            escape=False))

        # NOTE: The tile cache size is shown in MB but is actually stored in bytes
        self._proxyTileCacheSizeSpinBox = gui.SpinBoxEx()
        self._proxyTileCacheSizeSpinBox.setRange(0, 4 * 1000) # 4GB max (in MB)
        self._proxyTileCacheSizeSpinBox.setValue(
            int(app.Config.instance().value(
                option=app.ConfigOption.ProxyTileCacheSize,
                futureValue=True) / (1000 * 1000)))
        self._proxyTileCacheSizeSpinBox.setEnabled(isProxyEnabled)
        self._proxyTileCacheSizeSpinBox.setToolTip(gui.createStringToolTip(
            '<p>Specify the amount of disk space to use to cache tiles.</p>'
            '<p>When the cache size reaches the specified limit, tiles will be '
            'automatically removed starting with the least recently used. A '
            'size of 0 will disable the disk cache.' +
            _RestartRequiredParagraph,
            escape=False))

        self._proxyTileCacheLifetimeSpinBox = gui.SpinBoxEx()
        self._proxyTileCacheLifetimeSpinBox.setRange(0, 90)
        self._proxyTileCacheLifetimeSpinBox.setValue(
            app.Config.instance().value(
                option=app.ConfigOption.ProxyTileCacheLifetime,
                futureValue=True))
        self._proxyTileCacheLifetimeSpinBox.setEnabled(isProxyEnabled)
        self._proxyTileCacheLifetimeSpinBox.setToolTip(gui.createStringToolTip(
            '<p>Specify the max time the proxy will cache a tile on disk.</p>'
            '<p>A value of 0 will cause tiles to be cached indefinitely.</p>' +
            _RestartRequiredParagraph,
            escape=False))

        # NOTE: The button for clearing the tile cache is enabled/disabled
        # based on if the proxy is currently running not if the enable check
        # box is currently checked. Clearing the cache is an immediate operation
        # that requires sending a request to the proxy process so it only makes
        # sense when it's actually running
        self._clearTileCacheButton = QtWidgets.QPushButton('Clear')
        self._clearTileCacheButton.setEnabled(proxy.MapProxy.instance().isRunning())
        self._clearTileCacheButton.clicked.connect(self._clearTileCacheClicked)

        proxyLayout = gui.FormLayoutEx()
        proxyLayout.addRow('Map Engine:', self._mapEngineComboBox)
        proxyLayout.addRow('Port:', self._proxyPortSpinBox)
        proxyLayout.addRow('Host Pool Size:', self._proxyHostPoolSizeSpinBox)
        proxyLayout.addRow('Map Url:', self._proxyMapUrlLineEdit)
        proxyLayout.addRow('Composition Mode:', self._proxyCompositionModeComboBox)
        proxyLayout.addRow('Tile Cache Size (MB):', self._proxyTileCacheSizeSpinBox)
        proxyLayout.addRow('Tile Cache Lifetime (days):', self._proxyTileCacheLifetimeSpinBox)
        proxyLayout.addRow('Clear Tile Cache:', self._clearTileCacheButton)

        proxyGroupBox = QtWidgets.QGroupBox('Map Rendering')
        proxyGroupBox.setLayout(proxyLayout)

        # GUI widgets
        self._colourThemeComboBox = gui.EnumComboBox(
            type=app.ColourTheme,
            value=app.Config.instance().value(
                option=app.ConfigOption.ColourTheme,
                futureValue=True))
        self._colourThemeComboBox.setToolTip(gui.createStringToolTip(
            '<p>Select the colour theme.</p>' +
            _RestartRequiredParagraph,
            escape=False))

        # NOTE: The interface scale is displayed in percent but is actually stored as a float scale
        # where 1.0 is 100%
        self._interfaceScaleSpinBox = gui.SpinBoxEx()
        self._interfaceScaleSpinBox.setRange(100, 400)
        self._interfaceScaleSpinBox.setValue(int(app.Config.instance().value(
            option=app.ConfigOption.InterfaceScale,
            futureValue=True) * 100))
        self._interfaceScaleSpinBox.setToolTip(gui.createStringToolTip(
            '<p>Scale the UI up to make things easier to read</p>' +
            _RestartRequiredParagraph,
            escape=False))

        self._showToolTipImagesCheckBox = gui.CheckBoxEx()
        self._showToolTipImagesCheckBox.setChecked(app.Config.instance().value(
            option=app.ConfigOption.ShowToolTipImages,
            futureValue=True))
        self._showToolTipImagesCheckBox.setToolTip(gui.createStringToolTip(
            '<p>Display world images in tool tips</p>'
            '<p>When enabled, {app.AppName} will retrieve world images to display in tool tips. It\'s '
            'recommended to disable this setting if operating offline or with a slow connection. Tool '
            'tip images are cached, however the first time a tool tip for a given world is displayed it '
            'can cause the user interface to block temporarily while the image is downloaded.</p>',
            escape=False))

        outcomeColours = app.Config.instance().value(
            option=app.ConfigOption.OutcomeColours,
            futureValue=True)

        self._averageCaseColourButton = gui.ColourButton(
            colour=outcomeColours.colour(outcome=logic.RollOutcome.AverageCase))
        self._averageCaseColourButton.setFixedWidth(ColourButtonWidth)
        self._averageCaseColourButton.setToolTip(gui.createStringToolTip(
            'Colour used to highlight values calculated using average dice rolls'))

        self._worstCaseColourButton = gui.ColourButton(
            colour=outcomeColours.colour(outcome=logic.RollOutcome.WorstCase))
        self._worstCaseColourButton.setFixedWidth(ColourButtonWidth)
        self._worstCaseColourButton.setToolTip(gui.createStringToolTip(
            'Colour used to highlight values calculated using worst case dice rolls'))

        self._bestCaseColourButton = gui.ColourButton(
            colour=outcomeColours.colour(outcome=logic.RollOutcome.BestCase))
        self._bestCaseColourButton.setFixedWidth(ColourButtonWidth)
        self._bestCaseColourButton.setToolTip(gui.createStringToolTip(
            'Colour used to highlight values calculated using best case dice rolls'))

        guiLayout = gui.FormLayoutEx()
        guiLayout.addRow('Colour Theme:', self._colourThemeComboBox)
        guiLayout.addRow('Scale (%):', self._interfaceScaleSpinBox)
        guiLayout.addRow('Show World Image in Tool Tips:', self._showToolTipImagesCheckBox)
        guiLayout.addRow('Average Case Highlight Colour:', self._averageCaseColourButton)
        guiLayout.addRow('Worst Case Highlight Colour:', self._worstCaseColourButton)
        guiLayout.addRow('Best Case Highlight Colour:', self._bestCaseColourButton)

        guiGroupBox = QtWidgets.QGroupBox('GUI')
        guiGroupBox.setLayout(guiLayout)

        # Tagging widgets
        taggingColours = app.Config.instance().value(
            option=app.ConfigOption.TaggingColours,
            futureValue=True)
        self._desirableTagColourButton = gui.ColourButton(QtGui.QColor(
            taggingColours.colour(level=app.TagLevel.Desirable)))
        self._desirableTagColourButton.setFixedWidth(ColourButtonWidth)
        self._desirableTagColourButton.setToolTip(gui.createStringToolTip(
            'Colour used to highlight desirable tagging'))

        self._warningTagColourButton = gui.ColourButton(QtGui.QColor(
            taggingColours.colour(level=app.TagLevel.Warning)))
        self._warningTagColourButton.setFixedWidth(ColourButtonWidth)
        self._warningTagColourButton.setToolTip(gui.createStringToolTip(
            'Colour used to highlight warning tagging'))

        self._dangerTagColourButton = gui.ColourButton(QtGui.QColor(
            taggingColours.colour(level=app.TagLevel.Danger)))
        self._dangerTagColourButton.setFixedWidth(ColourButtonWidth)
        self._dangerTagColourButton.setToolTip(gui.createStringToolTip(
            'Colour used to highlight danger tagging'))

        taggingLayout = gui.FormLayoutEx()
        taggingLayout.addRow('Desirable Tagging Colour:', self._desirableTagColourButton)
        taggingLayout.addRow('Warning Tagging Colour:', self._warningTagColourButton)
        taggingLayout.addRow('Danger Tagging Colour:', self._dangerTagColourButton)

        taggingGroupBox = QtWidgets.QGroupBox('Tagging')
        taggingGroupBox.setLayout(taggingLayout)

        tabLayout = QtWidgets.QVBoxLayout()
        tabLayout.setContentsMargins(0, 0, 0, 0)
        tabLayout.addWidget(travellerGroupBox)
        tabLayout.addWidget(proxyGroupBox)
        tabLayout.addWidget(guiGroupBox)
        tabLayout.addWidget(taggingGroupBox)
        tabLayout.addStretch()

        tab = QtWidgets.QWidget()
        tab.setLayout(tabLayout)
        self._tabWidget.addTab(tab, 'General')

    def _setupRulesTab(self) -> None:
        rules = app.Config.instance().value(
            option=app.ConfigOption.Rules,
            futureValue=True)

        self._classAStarPortFuelType = gui.EnumComboBox(
            type=traveller.StarPortFuelType,
            value=rules.starPortFuelType(code='A'))
        self._classAStarPortFuelType.setToolTip(_StarPortFuelToolTip)

        self._classBStarPortFuelType = gui.EnumComboBox(
            type=traveller.StarPortFuelType,
            value=rules.starPortFuelType(code='B'))
        self._classBStarPortFuelType.setToolTip(_StarPortFuelToolTip)

        self._classCStarPortFuelType = gui.EnumComboBox(
            type=traveller.StarPortFuelType,
            value=rules.starPortFuelType(code='C'))
        self._classCStarPortFuelType.setToolTip(_StarPortFuelToolTip)

        self._classDStarPortFuelType = gui.EnumComboBox(
            type=traveller.StarPortFuelType,
            value=rules.starPortFuelType(code='D'))
        self._classDStarPortFuelType.setToolTip(_StarPortFuelToolTip)

        self._classEStarPortFuelType = gui.EnumComboBox(
            type=traveller.StarPortFuelType,
            value=rules.starPortFuelType(code='E'))
        self._classEStarPortFuelType.setToolTip(_StarPortFuelToolTip)

        starportFuelLayout = gui.FormLayoutEx()
        starportFuelLayout.addRow(
            'Class A:',
            self._classAStarPortFuelType)
        starportFuelLayout.addRow(
            'Class B:',
            self._classBStarPortFuelType)
        starportFuelLayout.addRow(
            'Class C:',
            self._classCStarPortFuelType)
        starportFuelLayout.addRow(
            'Class D:',
            self._classDStarPortFuelType)
        starportFuelLayout.addRow(
            'Class E:',
            self._classEStarPortFuelType)

        starportFuelGroupBox = QtWidgets.QGroupBox('Starport Fuel Availability')
        starportFuelGroupBox.setLayout(starportFuelLayout)

        tabLayout = QtWidgets.QVBoxLayout()
        tabLayout.setContentsMargins(0, 0, 0, 0)
        tabLayout.addWidget(starportFuelGroupBox)
        tabLayout.addStretch()

        tab = QtWidgets.QWidget()
        tab.setLayout(tabLayout)
        self._tabWidget.addTab(tab, 'Rules')

    # TODO: There is a LOT of duplicated code setting up these table, it
    # should really be a loop that iterates over logic.TaggingProperty
    def _setupZoneTaggingTab(self) -> None:
        worldTagging = app.Config.instance().value(
            option=app.ConfigOption.WorldTagging,
            futureValue=True)
        taggingColours = app.Config.instance().value(
            option=app.ConfigOption.TaggingColours,
            futureValue=True)

        keyDescriptions = {}
        keyAliases = {}
        for zoneType in traveller.ZoneType:
            keyDescriptions[zoneType] = traveller.zoneTypeName(zoneType)
            keyAliases[zoneType] = traveller.zoneTypeCode(zoneType)

        self._zoneTaggingTable = _TaggingTable(
            taggingConfig=worldTagging.propertyConfig(property=logic.TaggingProperty.Zone),
            taggingColours=taggingColours,
            keyColumnName='Zone',
            keyDescriptions=keyDescriptions,
            keyAliases=keyAliases)
        self._addTableTab(
            title='Zone Tagging',
            table=self._zoneTaggingTable)

    def _setupStarPortTaggingTab(self) -> None:
        worldTagging = app.Config.instance().value(
            option=app.ConfigOption.WorldTagging,
            futureValue=True)
        taggingColours = app.Config.instance().value(
            option=app.ConfigOption.TaggingColours,
            futureValue=True)

        self._starPortTaggingTable = _TaggingTable(
            taggingConfig=worldTagging.propertyConfig(property=logic.TaggingProperty.StarPort),
            taggingColours=taggingColours,
            keyColumnName='Star Port',
            keyDescriptions=traveller.UWP.descriptionMap(traveller.UWP.Element.StarPort))
        self._addTableTab(
            title='Star Port Tagging',
            table=self._starPortTaggingTable)

    def _setupWorldSizeTaggingTab(self) -> None:
        worldTagging = app.Config.instance().value(
            option=app.ConfigOption.WorldTagging,
            futureValue=True)
        taggingColours = app.Config.instance().value(
            option=app.ConfigOption.TaggingColours,
            futureValue=True)

        self._worldSizeTaggingTable = _TaggingTable(
            taggingConfig=worldTagging.propertyConfig(property=logic.TaggingProperty.WorldSize),
            taggingColours=taggingColours,
            keyColumnName='World Size',
            keyDescriptions=traveller.UWP.descriptionMap(traveller.UWP.Element.WorldSize))
        self._addTableTab(
            title='World Size Tagging',
            table=self._worldSizeTaggingTable)

    def _setupAtmosphereTaggingTab(self) -> None:
        worldTagging = app.Config.instance().value(
            option=app.ConfigOption.WorldTagging,
            futureValue=True)
        taggingColours = app.Config.instance().value(
            option=app.ConfigOption.TaggingColours,
            futureValue=True)

        self._atmosphereTaggingTable = _TaggingTable(
            taggingConfig=worldTagging.propertyConfig(property=logic.TaggingProperty.Atmosphere),
            taggingColours=taggingColours,
            keyColumnName='Atmosphere',
            keyDescriptions=traveller.UWP.descriptionMap(traveller.UWP.Element.Atmosphere))
        self._addTableTab(
            title='Atmosphere Tagging',
            table=self._atmosphereTaggingTable)

    def _setupHydrographicsTaggingTab(self) -> None:
        worldTagging = app.Config.instance().value(
            option=app.ConfigOption.WorldTagging,
            futureValue=True)
        taggingColours = app.Config.instance().value(
            option=app.ConfigOption.TaggingColours,
            futureValue=True)

        self._hydrographicsTaggingTable = _TaggingTable(
            taggingConfig=worldTagging.propertyConfig(property=logic.TaggingProperty.Hydrographics),
            taggingColours=taggingColours,
            keyColumnName='Hydrographics',
            keyDescriptions=traveller.UWP.descriptionMap(traveller.UWP.Element.Hydrographics))
        self._addTableTab(
            title='Hydrographics Tagging',
            table=self._hydrographicsTaggingTable)

    def _setupPopulationTaggingTab(self) -> None:
        worldTagging = app.Config.instance().value(
            option=app.ConfigOption.WorldTagging,
            futureValue=True)
        taggingColours = app.Config.instance().value(
            option=app.ConfigOption.TaggingColours,
            futureValue=True)

        self._populationTaggingTable = _TaggingTable(
            taggingConfig=worldTagging.propertyConfig(property=logic.TaggingProperty.Population),
            taggingColours=taggingColours,
            keyColumnName='Population',
            keyDescriptions=traveller.UWP.descriptionMap(traveller.UWP.Element.Population))
        self._addTableTab(
            title='Population Tagging',
            table=self._populationTaggingTable)

    def _setupGovernmentTaggingTab(self) -> None:
        worldTagging = app.Config.instance().value(
            option=app.ConfigOption.WorldTagging,
            futureValue=True)
        taggingColours = app.Config.instance().value(
            option=app.ConfigOption.TaggingColours,
            futureValue=True)

        self._governmentTaggingTable = _TaggingTable(
            taggingConfig=worldTagging.propertyConfig(property=logic.TaggingProperty.Government),
            taggingColours=taggingColours,
            keyColumnName='Government',
            keyDescriptions=traveller.UWP.descriptionMap(traveller.UWP.Element.Government))
        self._addTableTab(
            title='Government Tagging',
            table=self._governmentTaggingTable)

    def _setupLawLevelTaggingTab(self) -> None:
        worldTagging = app.Config.instance().value(
            option=app.ConfigOption.WorldTagging,
            futureValue=True)
        taggingColours = app.Config.instance().value(
            option=app.ConfigOption.TaggingColours,
            futureValue=True)

        self._lawLevelTaggingTable = _TaggingTable(
            taggingConfig=worldTagging.propertyConfig(property=logic.TaggingProperty.LawLevel),
            taggingColours=taggingColours,
            keyColumnName='Law Level',
            keyDescriptions=traveller.UWP.descriptionMap(traveller.UWP.Element.LawLevel))
        self._addTableTab(
            title='Law Level Tagging',
            table=self._lawLevelTaggingTable)

    def _setupTechLevelTaggingTab(self) -> None:
        worldTagging = app.Config.instance().value(
            option=app.ConfigOption.WorldTagging,
            futureValue=True)
        taggingColours = app.Config.instance().value(
            option=app.ConfigOption.TaggingColours,
            futureValue=True)

        self._techLevelTaggingTable = _TaggingTable(
            taggingConfig=worldTagging.propertyConfig(property=logic.TaggingProperty.TechLevel),
            taggingColours=taggingColours,
            keyColumnName='Tech Level',
            keyDescriptions=traveller.UWP.descriptionMap(traveller.UWP.Element.TechLevel))
        self._addTableTab(
            title='Tech Level Tagging',
            table=self._techLevelTaggingTable)

    def _setupBaseTypeTaggingTab(self) -> None:
        worldTagging = app.Config.instance().value(
            option=app.ConfigOption.WorldTagging,
            futureValue=True)
        taggingColours = app.Config.instance().value(
            option=app.ConfigOption.TaggingColours,
            futureValue=True)

        keyDescriptions = {}
        keyAliases = {}
        for baseType in traveller.BaseType:
            keyDescriptions[baseType] = traveller.Bases.description(baseType)
            keyAliases[baseType] = traveller.Bases.code(baseType)

        self._baseTypeTaggingTable = _TaggingTable(
            taggingConfig=worldTagging.propertyConfig(property=logic.TaggingProperty.BaseType),
            taggingColours=taggingColours,
            keyColumnName='Base',
            keyDescriptions=keyDescriptions,
            keyAliases=keyAliases)
        self._addTableTab(
            title='Base Tagging',
            table=self._baseTypeTaggingTable)

    def _setupTradeCodeTaggingTab(self) -> None:
        worldTagging = app.Config.instance().value(
            option=app.ConfigOption.WorldTagging,
            futureValue=True)
        taggingColours = app.Config.instance().value(
            option=app.ConfigOption.TaggingColours,
            futureValue=True)

        keyDescriptions = {}
        keyAliases = {}
        for tradeCode in traveller.TradeCode:
            keyDescriptions[tradeCode] = f'{traveller.tradeCodeName(tradeCode)} - {traveller.tradeCodeDescription(tradeCode)}'
            keyAliases[tradeCode] = traveller.tradeCodeString(tradeCode)

        self._tradeCodeTaggingTable = _TaggingTable(
            taggingConfig=worldTagging.propertyConfig(property=logic.TaggingProperty.TradeCode),
            taggingColours=taggingColours,
            keyColumnName='Trade Code',
            keyDescriptions=keyDescriptions,
            keyAliases=keyAliases)
        self._addTableTab(
            title='Trade Code Tagging',
            table=self._tradeCodeTaggingTable)

    def _setupResourcesTaggingTab(self) -> None:
        worldTagging = app.Config.instance().value(
            option=app.ConfigOption.WorldTagging,
            futureValue=True)
        taggingColours = app.Config.instance().value(
            option=app.ConfigOption.TaggingColours,
            futureValue=True)

        self._resourcesTaggingTable = _TaggingTable(
            taggingConfig=worldTagging.propertyConfig(property=logic.TaggingProperty.Resources),
            taggingColours=taggingColours,
            keyColumnName='Resources',
            keyDescriptions=traveller.Economics.descriptionMap(traveller.Economics.Element.Resources))
        self._addTableTab(
            title='Resources Tagging',
            table=self._resourcesTaggingTable)

    def _setupLabourTaggingTab(self) -> None:
        worldTagging = app.Config.instance().value(
            option=app.ConfigOption.WorldTagging,
            futureValue=True)
        taggingColours = app.Config.instance().value(
            option=app.ConfigOption.TaggingColours,
            futureValue=True)

        self._labourTaggingTable = _TaggingTable(
            taggingConfig=worldTagging.propertyConfig(property=logic.TaggingProperty.Labour),
            taggingColours=taggingColours,
            keyColumnName='Labour',
            keyDescriptions=traveller.Economics.descriptionMap(traveller.Economics.Element.Labour))
        self._addTableTab(
            title='Labour Tagging',
            table=self._labourTaggingTable)

    def _setupInfrastructureTaggingTab(self) -> None:
        worldTagging = app.Config.instance().value(
            option=app.ConfigOption.WorldTagging,
            futureValue=True)
        taggingColours = app.Config.instance().value(
            option=app.ConfigOption.TaggingColours,
            futureValue=True)

        self._infrastructureTaggingTable = _TaggingTable(
            taggingConfig=worldTagging.propertyConfig(property=logic.TaggingProperty.Infrastructure),
            taggingColours=taggingColours,
            keyColumnName='Infrastructure',
            keyDescriptions=traveller.Economics.descriptionMap(traveller.Economics.Element.Infrastructure))
        self._addTableTab(
            title='Infrastructure Tagging',
            table=self._infrastructureTaggingTable)

    def _setupEfficiencyTaggingTab(self) -> None:
        worldTagging = app.Config.instance().value(
            option=app.ConfigOption.WorldTagging,
            futureValue=True)
        taggingColours = app.Config.instance().value(
            option=app.ConfigOption.TaggingColours,
            futureValue=True)

        self._efficiencyTaggingTable = _TaggingTable(
            taggingConfig=worldTagging.propertyConfig(property=logic.TaggingProperty.Efficiency),
            taggingColours=taggingColours,
            keyColumnName='Efficiency',
            keyDescriptions=traveller.Economics.descriptionMap(traveller.Economics.Element.Efficiency))
        self._addTableTab(
            title='Efficiency Tagging',
            table=self._efficiencyTaggingTable)

    def _setupHeterogeneityTaggingTab(self) -> None:
        worldTagging = app.Config.instance().value(
            option=app.ConfigOption.WorldTagging,
            futureValue=True)
        taggingColours = app.Config.instance().value(
            option=app.ConfigOption.TaggingColours,
            futureValue=True)

        self._heterogeneityTaggingTable = _TaggingTable(
            taggingConfig=worldTagging.propertyConfig(property=logic.TaggingProperty.Heterogeneity),
            taggingColours=taggingColours,
            keyColumnName='Heterogeneity',
            keyDescriptions=traveller.Culture.descriptionMap(traveller.Culture.Element.Heterogeneity))
        self._addTableTab(
            title='Heterogeneity Tagging',
            table=self._heterogeneityTaggingTable)

    def _setupAcceptanceTaggingTab(self) -> None:
        worldTagging = app.Config.instance().value(
            option=app.ConfigOption.WorldTagging,
            futureValue=True)
        taggingColours = app.Config.instance().value(
            option=app.ConfigOption.TaggingColours,
            futureValue=True)

        self._acceptanceTaggingTable = _TaggingTable(
            taggingConfig=worldTagging.propertyConfig(property=logic.TaggingProperty.Acceptance),
            taggingColours=taggingColours,
            keyColumnName='Acceptance',
            keyDescriptions=traveller.Culture.descriptionMap(traveller.Culture.Element.Acceptance))
        self._addTableTab(
            title='Acceptance Tagging',
            table=self._acceptanceTaggingTable)

    def _setupStrangenessTaggingTab(self) -> None:
        worldTagging = app.Config.instance().value(
            option=app.ConfigOption.WorldTagging,
            futureValue=True)
        taggingColours = app.Config.instance().value(
            option=app.ConfigOption.TaggingColours,
            futureValue=True)

        self._strangenessTaggingTable = _TaggingTable(
            taggingConfig=worldTagging.propertyConfig(property=logic.TaggingProperty.Strangeness),
            taggingColours=taggingColours,
            keyColumnName='Strangeness',
            keyDescriptions=traveller.Culture.descriptionMap(traveller.Culture.Element.Strangeness))
        self._addTableTab(
            title='Strangeness Tagging',
            table=self._strangenessTaggingTable)

    def _setupSymbolsTaggingTab(self) -> None:
        worldTagging = app.Config.instance().value(
            option=app.ConfigOption.WorldTagging,
            futureValue=True)
        taggingColours = app.Config.instance().value(
            option=app.ConfigOption.TaggingColours,
            futureValue=True)

        self._symbolsTaggingTable = _TaggingTable(
            taggingConfig=worldTagging.propertyConfig(property=logic.TaggingProperty.Symbols),
            taggingColours=taggingColours,
            keyColumnName='Symbols',
            keyDescriptions=traveller.Culture.descriptionMap(traveller.Culture.Element.Symbols))
        self._addTableTab(
            title='Symbols Tagging',
            table=self._symbolsTaggingTable)

    def _setupNobilityTaggingTab(self) -> None:
        worldTagging = app.Config.instance().value(
            option=app.ConfigOption.WorldTagging,
            futureValue=True)
        taggingColours = app.Config.instance().value(
            option=app.ConfigOption.TaggingColours,
            futureValue=True)

        keyDescriptions = {}
        keyAliases = {}
        for nobilityType in traveller.NobilityType:
            keyDescriptions[nobilityType] = traveller.Nobilities.description(nobilityType)
            keyAliases[nobilityType] = traveller.Nobilities.code(nobilityType)

        self._nobilityTaggingTable = _TaggingTable(
            taggingConfig=worldTagging.propertyConfig(property=logic.TaggingProperty.Nobility),
            taggingColours=taggingColours,
            keyColumnName='Nobility',
            keyDescriptions=keyDescriptions,
            keyAliases=keyAliases)
        self._addTableTab(
            title='Nobility Tagging',
            table=self._nobilityTaggingTable)

    def _setupAllegianceTaggingTab(self) -> None:
        worldTagging = app.Config.instance().value(
            option=app.ConfigOption.WorldTagging,
            futureValue=True)
        taggingColours = app.Config.instance().value(
            option=app.ConfigOption.TaggingColours,
            futureValue=True)

        # TODO: If the user changes the milieu on the main config pane, this
        # config pane should probably update
        # TODO: This probably shouldn't use app.Config
        allegiances = traveller.AllegianceManager.instance().allegiances(
            milieu=app.Config.instance().value(
                option=app.ConfigOption.Milieu,
                futureValue=False)) # Use current value

        # Create a copy of the allegiances list and sort it by code
        allegiances = list(allegiances)
        allegiances.sort(key=lambda x: x.code())

        keyDescriptions = {}
        for allegiance in allegiances:
            nameMap = allegiance.uniqueNameMap()
            for code, name in nameMap.items():
                keyDescriptions[code] = name

        self._allegianceTaggingTable = _TaggingTable(
            taggingConfig=worldTagging.propertyConfig(property=logic.TaggingProperty.Allegiance),
            taggingColours=taggingColours,
            keyColumnName='Allegiance',
            keyDescriptions=keyDescriptions)
        self._addTableTab(
            title='Allegiance Tagging',
            table=self._allegianceTaggingTable)

    def _setupSpectralTaggingTab(self) -> None:
        worldTagging = app.Config.instance().value(
            option=app.ConfigOption.WorldTagging,
            futureValue=True)
        taggingColours = app.Config.instance().value(
            option=app.ConfigOption.TaggingColours,
            futureValue=True)

        self._spectralTaggingTable = _TaggingTable(
            taggingConfig=worldTagging.propertyConfig(property=logic.TaggingProperty.Spectral),
            taggingColours=taggingColours,
            keyColumnName='Spectral Class',
            keyDescriptions=traveller.Star.descriptionMap(traveller.Star.Element.SpectralClass))
        self._addTableTab(
            title='Spectral Class Tagging',
            table=self._spectralTaggingTable)

    def _setupLuminosityTaggingTab(self) -> None:
        worldTagging = app.Config.instance().value(
            option=app.ConfigOption.WorldTagging,
            futureValue=True)
        taggingColours = app.Config.instance().value(
            option=app.ConfigOption.TaggingColours,
            futureValue=True)

        self._luminosityTaggingTable = _TaggingTable(
            taggingConfig=worldTagging.propertyConfig(property=logic.TaggingProperty.Luminosity),
            taggingColours=taggingColours,
            keyColumnName='Luminosity Class',
            keyDescriptions=traveller.Star.descriptionMap(traveller.Star.Element.LuminosityClass),)
        self._addTableTab(
            title='Luminosity Class Tagging',
            table=self._luminosityTaggingTable)

    def _setupButtons(self):
        self._okButton = QtWidgets.QPushButton('OK')
        self._okButton.setDefault(True)
        self._okButton.clicked.connect(self.accept)

        self._cancelButton = QtWidgets.QPushButton('Cancel')
        self._cancelButton.clicked.connect(self.reject)

        self._buttonLayout = QtWidgets.QHBoxLayout()
        self._buttonLayout.addStretch()
        self._buttonLayout.addWidget(self._okButton)
        self._buttonLayout.addWidget(self._cancelButton)

    def _validateConfig(self) -> bool:
        mapUrl = QtCore.QUrl(self._proxyMapUrlLineEdit.text())
        # Map URL must have a scheme but no path or options
        if mapUrl.scheme() != 'http' and mapUrl.scheme() != 'https':
            gui.MessageBoxEx.critical(
                parent=self,
                text='The Traveller Map URL must use http or https')
            return False
        if (mapUrl.path() != '' and mapUrl.path() != '/') or mapUrl.query():
            gui.MessageBoxEx.critical(
                parent=self,
                text='The Traveller Map URL can\'t have a path or query')
            return False
        return True

    def _saveConfig(self) -> None:
        try:
            app.Config.instance().setValue(
                option=app.ConfigOption.Milieu,
                value=self._milieuComboBox.currentEnum())
            app.Config.instance().setValue(
                option=app.ConfigOption.Rules,
                value=traveller.Rules(
                    system=self._rulesComboBox.currentEnum(),
                    classAStarPortFuelType=self._classAStarPortFuelType.currentEnum(),
                    classBStarPortFuelType=self._classBStarPortFuelType.currentEnum(),
                    classCStarPortFuelType=self._classCStarPortFuelType.currentEnum(),
                    classDStarPortFuelType=self._classDStarPortFuelType.currentEnum(),
                    classEStarPortFuelType=self._classEStarPortFuelType.currentEnum()))
            app.Config.instance().setValue(
                option=app.ConfigOption.MapEngine,
                value=self._mapEngineComboBox.currentEnum())
            app.Config.instance().setValue(
                option=app.ConfigOption.ProxyPort,
                value=self._proxyPortSpinBox.value())
            app.Config.instance().setValue(
                option=app.ConfigOption.ProxyHostPoolSize,
                value=self._proxyHostPoolSizeSpinBox.value())
            app.Config.instance().setValue(
                option=app.ConfigOption.ProxyMapUrl,
                value=self._proxyMapUrlLineEdit.text())
            app.Config.instance().setValue(
                option=app.ConfigOption.ProxyTileCacheSize,
                value=self._proxyTileCacheSizeSpinBox.value() * (1000 * 1000)) # Convert MB to bytes
            app.Config.instance().setValue(
                option=app.ConfigOption.ProxyTileCacheLifetime,
                value=self._proxyTileCacheLifetimeSpinBox.value())
            app.Config.instance().setValue(
                option=app.ConfigOption.ProxySvgComposition,
                value=self._proxyCompositionModeComboBox.currentUserData())

            app.Config.instance().setValue(
                option=app.ConfigOption.ColourTheme,
                value=self._colourThemeComboBox.currentEnum())
            app.Config.instance().setValue(
                option=app.ConfigOption.InterfaceScale,
                value=self._interfaceScaleSpinBox.value() / 100) # Convert percent to scale
            app.Config.instance().setValue(
                option=app.ConfigOption.ShowToolTipImages,
                value=self._showToolTipImagesCheckBox.isChecked())
            app.Config.instance().setValue(
                option=app.ConfigOption.OutcomeColours,
                value=app.OutcomeColours(
                    averageCaseColour=gui.colourToString(self._averageCaseColourButton.colour()),
                    worstCaseColour=gui.colourToString(self._worstCaseColourButton.colour()),
                    bestCaseColour=gui.colourToString(self._bestCaseColourButton.colour())))

            app.Config.instance().setValue(
                option=app.ConfigOption.TaggingColours,
                value=app.TaggingColours(
                    desirableColour=gui.colourToString(self._desirableTagColourButton.colour()),
                    warningColour=gui.colourToString(self._warningTagColourButton.colour()),
                    dangerColour=gui.colourToString(self._dangerTagColourButton.colour())))

            # TODO: This should be in some kind of loop rather than handling
            # each property independently. It's related to the fact there
            # is so much duplicated code setting the tables up
            tagging = logic.WorldTagging()
            tagging.setPropertyConfig(
                property=logic.TaggingProperty.Zone,
                config=self._zoneTaggingTable.taggingConfig())
            tagging.setPropertyConfig(
                property=logic.TaggingProperty.StarPort,
                config=self._starPortTaggingTable.taggingConfig())
            tagging.setPropertyConfig(
                property=logic.TaggingProperty.WorldSize,
                config=self._worldSizeTaggingTable.taggingConfig())
            tagging.setPropertyConfig(
                property=logic.TaggingProperty.Atmosphere,
                config=self._atmosphereTaggingTable.taggingConfig())
            tagging.setPropertyConfig(
                property=logic.TaggingProperty.Hydrographics,
                config=self._hydrographicsTaggingTable.taggingConfig())
            tagging.setPropertyConfig(
                property=logic.TaggingProperty.Population,
                config=self._populationTaggingTable.taggingConfig())
            tagging.setPropertyConfig(
                property=logic.TaggingProperty.Government,
                config=self._governmentTaggingTable.taggingConfig())
            tagging.setPropertyConfig(
                property=logic.TaggingProperty.LawLevel,
                config=self._lawLevelTaggingTable.taggingConfig())
            tagging.setPropertyConfig(
                property=logic.TaggingProperty.TechLevel,
                config=self._techLevelTaggingTable.taggingConfig())
            tagging.setPropertyConfig(
                property=logic.TaggingProperty.BaseType,
                config=self._baseTypeTaggingTable.taggingConfig())
            tagging.setPropertyConfig(
                property=logic.TaggingProperty.TradeCode,
                config=self._tradeCodeTaggingTable.taggingConfig())
            tagging.setPropertyConfig(
                property=logic.TaggingProperty.Resources,
                config=self._resourcesTaggingTable.taggingConfig())
            tagging.setPropertyConfig(
                property=logic.TaggingProperty.Labour,
                config=self._labourTaggingTable.taggingConfig())
            tagging.setPropertyConfig(
                property=logic.TaggingProperty.Infrastructure,
                config=self._infrastructureTaggingTable.taggingConfig())
            tagging.setPropertyConfig(
                property=logic.TaggingProperty.Efficiency,
                config=self._efficiencyTaggingTable.taggingConfig())
            tagging.setPropertyConfig(
                property=logic.TaggingProperty.Heterogeneity,
                config=self._heterogeneityTaggingTable.taggingConfig())
            tagging.setPropertyConfig(
                property=logic.TaggingProperty.Acceptance,
                config=self._acceptanceTaggingTable.taggingConfig())
            tagging.setPropertyConfig(
                property=logic.TaggingProperty.Strangeness,
                config=self._strangenessTaggingTable.taggingConfig())
            tagging.setPropertyConfig(
                property=logic.TaggingProperty.Symbols,
                config=self._symbolsTaggingTable.taggingConfig())
            tagging.setPropertyConfig(
                property=logic.TaggingProperty.Nobility,
                config=self._nobilityTaggingTable.taggingConfig())
            tagging.setPropertyConfig(
                property=logic.TaggingProperty.Allegiance,
                config=self._allegianceTaggingTable.taggingConfig())
            tagging.setPropertyConfig(
                property=logic.TaggingProperty.Spectral,
                config=self._spectralTaggingTable.taggingConfig())
            tagging.setPropertyConfig(
                property=logic.TaggingProperty.Luminosity,
                config=self._luminosityTaggingTable.taggingConfig())
            app.Config.instance().setValue(
                option=app.ConfigOption.WorldTagging,
                value=tagging)
        except Exception as ex:
            message = 'Failed to save configuration'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

    def _addTableTab(
            self,
            title: str,
            table: QtWidgets.QTableWidget
            ) -> None:
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(table)

        tab = QtWidgets.QWidget()
        tab.setLayout(layout)
        self._tabWidget.addTab(tab, title)

    def _showWelcomeMessage(self) -> None:
        message = gui.InfoDialog(
            parent=self,
            title=self.windowTitle(),
            html=_WelcomeMessage,
            noShowAgainId='ConfigWelcome')
        message.exec()

    def _renderingTypeChanged(self) -> None:
        isProxyEnabled = self._mapEngineComboBox.currentEnum() is app.MapEngine.WebProxy
        self._proxyPortSpinBox.setEnabled(isProxyEnabled)
        self._proxyHostPoolSizeSpinBox.setEnabled(isProxyEnabled)
        self._proxyMapUrlLineEdit.setEnabled(isProxyEnabled)
        self._proxyTileCacheSizeSpinBox.setEnabled(isProxyEnabled)
        self._proxyTileCacheLifetimeSpinBox.setEnabled(isProxyEnabled)
        self._proxyCompositionModeComboBox.setEnabled(isProxyEnabled)

    def _proxyModeChanged(self) -> None:
        if not self._proxyCompositionModeComboBox.currentUserData():
            return # Hybrid is selected, nothing to do
        gui.AutoSelectMessageBox.warning(
            parent=self,
            text='SVG composition is VERY processor intensive and should only '
            'be used on systems with high core counts.',
            stateKey='SvgCompositionPerformanceWarning')

    def _clearTileCacheClicked(self) -> None:
        dlg = _ClearTileCacheDialog(parent=self)
        dlg.exec()
