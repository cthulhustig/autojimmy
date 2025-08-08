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

class _InPlaceTagLevelComboBox(gui.TagLevelComboBox):
    def __init__(self, colours, parent = None, value = None):
        super().__init__(colours, parent, value)
        # NOTE: Change focus policy and install event filter to prevent
        # accidental changes to the value if, while scrolling the list the
        # widget is contained in, the spin box happens to move under the
        # cursor
        self._noWheelFilter = gui.NoWheelEventUnlessFocusedFilter()
        self.installEventFilter(self._noWheelFilter)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)

class _TaggingTable(gui.ListTable):
    def __init__(
            self,
            keyColumnName: str,
            keyDescriptions: typing.Mapping[typing.Union[str, enum.Enum], str],
            taggingColours: app.TaggingColours,
            keyTagging: typing.Optional[typing.Mapping[typing.Union[str, enum.Enum], logic.TagLevel]] = None,
            keyAliases: typing.Optional[typing.Mapping[typing.Union[str, enum.Enum], str]] = None,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self._keyColumnName = keyColumnName
        self._keyDescriptions = dict(keyDescriptions)
        self._keyTagging = dict(keyTagging) if keyTagging else {}
        self._keyAliases = dict(keyAliases) if keyAliases else {}
        self._taggingColours = app.TaggingColours(taggingColours)
        self._tableFilled = False

        columnNames = [keyColumnName, 'Tag Level', 'Description']

        self.setColumnHeaders(columnNames)
        self.setColumnsMoveable(False)
        self.resizeColumnsToContents() # Size columns to header text
        self.setSizeAdjustPolicy(
            QtWidgets.QAbstractScrollArea.SizeAdjustPolicy.AdjustToContentsOnFirstShow)
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.NoContextMenu)

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

    def setContent(
            self,
            keyDescriptions: typing.Mapping[typing.Union[str, enum.Enum], str],
            keyTagging: typing.Optional[typing.Mapping[typing.Union[str, enum.Enum], logic.TagLevel]] = None,
            keyAliases: typing.Optional[typing.Mapping[typing.Union[str, enum.Enum], str]] = None
            ) -> None:
        self._keyDescriptions = dict(keyDescriptions)
        self._keyTagging = dict(keyTagging) if keyTagging else {}
        self._keyAliases = dict(keyAliases) if keyAliases else {}
        if self._tableFilled:
            self._fillTable()

    def setTaggingColours(self, colours: app.TaggingColours) -> None:
        if colours == self._taggingColours:
            return

        self._taggingColours = app.TaggingColours(colours)
        self._syncToTagging()

    def taggingConfig(self) -> typing.Dict[typing.Union[str, enum.Enum], typing.Optional[logic.TagLevel]]:
        if not self._tableFilled:
            return dict(self._keyTagging)

        tagging = {}
        for row in range(self.rowCount()):
            comboBox: _InPlaceTagLevelComboBox = self.cellWidget(row, 1)
            if not isinstance(comboBox, _InPlaceTagLevelComboBox):
                continue

            tagLevel = comboBox.currentTagLevel()
            if not tagLevel:
                continue

            item = self.item(row, 0)
            key = item.data(QtCore.Qt.ItemDataRole.UserRole)
            tagging[key] = tagLevel
        return tagging

    def showEvent(self, event: typing.Optional[QtGui.QShowEvent]) -> None:
        if not self._tableFilled:
            self._fillTable()
            self._tableFilled = True
        return super().showEvent(event)

    def _fillTable(self) -> None:
        self.removeAllRows()

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

            tagLevel = self._keyTagging.get(key)

            item = QtWidgets.QTableWidgetItem()
            item.setToolTip(toolTip)
            self.setItem(row, 1, item)
            comboBox = _InPlaceTagLevelComboBox(
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
            comboBox: _InPlaceTagLevelComboBox = self.cellWidget(row, 1)
            if isinstance(comboBox, _InPlaceTagLevelComboBox):
                comboBox.setColours(self._taggingColours)

class ConfigDialog(gui.DialogEx):
    _TaggingTableSettingKeys = {
        logic.TaggingProperty.Zone: 'ZoneTaggingTableState',
        logic.TaggingProperty.StarPort: 'StarportTaggingTableState',
        logic.TaggingProperty.WorldSize: 'WorldSizeTaggingTableState',
        logic.TaggingProperty.Atmosphere: 'AtmosphereTaggingTableState',
        logic.TaggingProperty.Hydrographics: 'HydrographicsTaggingTableState',
        logic.TaggingProperty.Population: 'PopulationTaggingTableState',
        logic.TaggingProperty.Government: 'GovernmentTaggingTableState',
        logic.TaggingProperty.LawLevel: 'LawLevelTaggingTableState',
        logic.TaggingProperty.TechLevel: 'TechLevelTaggingTableState',
        logic.TaggingProperty.BaseType: 'BaseTypeTaggingTableState',
        logic.TaggingProperty.TradeCode: 'TradeCodeTaggingTableState',
        logic.TaggingProperty.Resources: 'ResourcesTaggingTableState',
        logic.TaggingProperty.Labour: 'LabourTaggingTableState',
        logic.TaggingProperty.Infrastructure: 'InfrastructureTaggingTableState',
        logic.TaggingProperty.Efficiency: 'EfficiencyTaggingTableState',
        logic.TaggingProperty.Heterogeneity: 'HeterogeneityTaggingTableState',
        logic.TaggingProperty.Acceptance: 'AcceptanceTaggingTableState',
        logic.TaggingProperty.Strangeness: 'StrangenessTaggingTableState',
        logic.TaggingProperty.Symbols: 'SymbolsTaggingTableState',
        logic.TaggingProperty.Nobility: 'NobilityTaggingTableState',
        logic.TaggingProperty.Allegiance: 'AllegianceTaggingTableState',
        logic.TaggingProperty.Spectral: 'SpectralTaggingTableState',
        logic.TaggingProperty.Luminosity: 'LuminosityTaggingTableState',
        }

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            title='Configuration',
            configSection='ConfigDialog',
            parent=parent)

        self._tabWidget = gui.VerticalTabWidget()
        self._taggingTables: typing.Dict[logic.TaggingProperty, _TaggingTable] = {}

        self._setupGeneralTab()
        self._setupRulesTab()
        self._setupTaggingTabs()
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

        for taggingProperty, settingKey in ConfigDialog._TaggingTableSettingKeys.items():
            table = self._taggingTables.get(taggingProperty)
            if not table:
                continue
            storedState = gui.safeLoadSetting(
                settings=self._settings,
                key=settingKey,
                type=QtCore.QByteArray)
            if storedState:
                table.restoreState(storedState)

        self._settings.endGroup()

    def saveSettings(self) -> None:
        super().saveSettings()

        # Note that this is saving the state of the various tables not the actual configuration
        self._settings.beginGroup(self._configSection)

        for taggingProperty, settingKey in ConfigDialog._TaggingTableSettingKeys.items():
            table = self._taggingTables.get(taggingProperty)
            if table:
                self._settings.setValue(settingKey, table.saveState())

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
        self._milieuComboBox.currentIndexChanged.connect(self._milieuChanged)

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
        if not depschecker.DetectedCairoSvgState:
            self._proxyCompositionModeComboBox.setHidden(True)
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
            taggingColours.colour(level=logic.TagLevel.Desirable)))
        self._desirableTagColourButton.setFixedWidth(ColourButtonWidth)
        self._desirableTagColourButton.setToolTip(gui.createStringToolTip(
            'Colour used to highlight desirable tagging'))
        self._desirableTagColourButton.colourChanged.connect(
                self._taggingColourChanged)

        self._warningTagColourButton = gui.ColourButton(QtGui.QColor(
            taggingColours.colour(level=logic.TagLevel.Warning)))
        self._warningTagColourButton.setFixedWidth(ColourButtonWidth)
        self._warningTagColourButton.setToolTip(gui.createStringToolTip(
            'Colour used to highlight warning tagging'))
        self._warningTagColourButton.colourChanged.connect(
                self._taggingColourChanged)

        self._dangerTagColourButton = gui.ColourButton(QtGui.QColor(
            taggingColours.colour(level=logic.TagLevel.Danger)))
        self._dangerTagColourButton.setFixedWidth(ColourButtonWidth)
        self._dangerTagColourButton.setToolTip(gui.createStringToolTip(
            'Colour used to highlight danger tagging'))
        self._dangerTagColourButton.colourChanged.connect(
                self._taggingColourChanged)

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

    def _setupTaggingTabs(self) -> None:
        self._setupTaggingTab(
            taggingProperty=logic.TaggingProperty.Zone,
            displayName='Zone',
            keyDescriptions={zone: traveller.zoneTypeName(zone) for zone in traveller.ZoneType},
            keyAliases={zone: traveller.zoneTypeCode(zone) for zone in traveller.ZoneType})

        self._setupTaggingTab(
            taggingProperty=logic.TaggingProperty.StarPort,
            displayName='Star Port',
            keyDescriptions=traveller.UWP.descriptionMap(traveller.UWP.Element.StarPort))

        self._setupTaggingTab(
            taggingProperty=logic.TaggingProperty.WorldSize,
            displayName='World Size',
            keyDescriptions=traveller.UWP.descriptionMap(traveller.UWP.Element.WorldSize))

        self._setupTaggingTab(
            taggingProperty=logic.TaggingProperty.Atmosphere,
            displayName='Atmosphere',
            keyDescriptions=traveller.UWP.descriptionMap(traveller.UWP.Element.Atmosphere))

        self._setupTaggingTab(
            taggingProperty=logic.TaggingProperty.Hydrographics,
            displayName='Hydrographics',
            keyDescriptions=traveller.UWP.descriptionMap(traveller.UWP.Element.Hydrographics))

        self._setupTaggingTab(
            taggingProperty=logic.TaggingProperty.Population,
            displayName='Population',
            keyDescriptions=traveller.UWP.descriptionMap(traveller.UWP.Element.Population))

        self._setupTaggingTab(
            taggingProperty=logic.TaggingProperty.Government,
            displayName='Government',
            keyDescriptions=traveller.UWP.descriptionMap(traveller.UWP.Element.Government))

        self._setupTaggingTab(
            taggingProperty=logic.TaggingProperty.LawLevel,
            displayName='Law Level',
            keyDescriptions=traveller.UWP.descriptionMap(traveller.UWP.Element.LawLevel))

        self._setupTaggingTab(
            taggingProperty=logic.TaggingProperty.TechLevel,
            displayName='Tech Level',
            keyDescriptions=traveller.UWP.descriptionMap(traveller.UWP.Element.TechLevel))

        self._setupTaggingTab(
            taggingProperty=logic.TaggingProperty.BaseType,
            displayName='Base',
            keyDescriptions={base: traveller.Bases.description(base) for base in  traveller.BaseType},
            keyAliases={base: traveller.Bases.code(base) for base in  traveller.BaseType})

        self._setupTaggingTab(
            taggingProperty=logic.TaggingProperty.TradeCode,
            displayName='Trade Code',
            keyDescriptions={code: f'{traveller.tradeCodeName(code)} - {traveller.tradeCodeDescription(code)}' for code in  traveller.TradeCode},
            keyAliases={code: traveller.tradeCodeString(code) for code in  traveller.TradeCode})

        self._setupTaggingTab(
            taggingProperty=logic.TaggingProperty.Resources,
            displayName='Resources',
            keyDescriptions=traveller.Economics.descriptionMap(traveller.Economics.Element.Resources))

        self._setupTaggingTab(
            taggingProperty=logic.TaggingProperty.Labour,
            displayName='Labour',
            keyDescriptions=traveller.Economics.descriptionMap(traveller.Economics.Element.Labour))

        self._setupTaggingTab(
            taggingProperty=logic.TaggingProperty.Infrastructure,
            displayName='Infrastructure',
            keyDescriptions=traveller.Economics.descriptionMap(traveller.Economics.Element.Infrastructure))

        self._setupTaggingTab(
            taggingProperty=logic.TaggingProperty.Efficiency,
            displayName='Efficiency',
            keyDescriptions=traveller.Economics.descriptionMap(traveller.Economics.Element.Efficiency))

        self._setupTaggingTab(
            taggingProperty=logic.TaggingProperty.Heterogeneity,
            displayName='Heterogeneity',
            keyDescriptions=traveller.Culture.descriptionMap(traveller.Culture.Element.Heterogeneity))

        self._setupTaggingTab(
            taggingProperty=logic.TaggingProperty.Acceptance,
            displayName='Acceptance',
            keyDescriptions=traveller.Culture.descriptionMap(traveller.Culture.Element.Acceptance))

        self._setupTaggingTab(
            taggingProperty=logic.TaggingProperty.Strangeness,
            displayName='Strangeness',
            keyDescriptions=traveller.Culture.descriptionMap(traveller.Culture.Element.Strangeness))

        self._setupTaggingTab(
            taggingProperty=logic.TaggingProperty.Symbols,
            displayName='Symbols',
            keyDescriptions=traveller.Culture.descriptionMap(traveller.Culture.Element.Symbols))

        self._setupTaggingTab(
            taggingProperty=logic.TaggingProperty.Nobility,
            displayName='Nobility',
            keyDescriptions={nobility: traveller.Nobilities.description(nobility) for nobility in traveller.NobilityType},
            keyAliases={nobility: traveller.Nobilities.code(nobility) for nobility in traveller.NobilityType})

        self._setupTaggingTab(
            taggingProperty=logic.TaggingProperty.Allegiance,
            displayName='Allegiance',
            keyDescriptions=self._generateAllegianceDescriptions())

        self._setupTaggingTab(
            taggingProperty=logic.TaggingProperty.Spectral,
            displayName='Spectral Class',
            keyDescriptions=traveller.Star.descriptionMap(traveller.Star.Element.SpectralClass))

        self._setupTaggingTab(
            taggingProperty=logic.TaggingProperty.Luminosity,
            displayName='Luminosity Class',
            keyDescriptions=traveller.Star.descriptionMap(traveller.Star.Element.LuminosityClass))

    def _setupTaggingTab(
            self,
            taggingProperty: logic.TaggingProperty,
            displayName: str,
            keyDescriptions: typing.Mapping[typing.Union[str, enum.Enum], str],
            keyAliases: typing.Optional[typing.Mapping[typing.Union[str, enum.Enum], str]] = None,
            ) -> None:
        worldTagging = app.Config.instance().value(
            option=app.ConfigOption.WorldTagging,
            futureValue=True)
        taggingColours = app.Config.instance().value(
            option=app.ConfigOption.TaggingColours,
            futureValue=True)

        table = _TaggingTable(
            keyColumnName=displayName,
            keyDescriptions=keyDescriptions,
            keyTagging=worldTagging.propertyConfig(property=taggingProperty),
            keyAliases=keyAliases,
            taggingColours=taggingColours)
        self._taggingTables[taggingProperty] = table
        self._addTableTab(
            title=displayName + ' Tagging',
            table=table)

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

            tagging = logic.WorldTagging()
            for taggingProperty, table in self._taggingTables.items():
                tagging.setPropertyConfig(
                    property=taggingProperty,
                    config=table.taggingConfig())
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

    def _milieuChanged(self) -> None:
        # Update allegiance tagging table as allegiances are milieu dependant.
        # This will clear any tagging set for the previously selected milieu.
        # This seems like the sensible thing to do as there is no guarantee that
        # the code that was tagged for the previous milieu has any relation to
        # the allegiance that is using that code in the new milieu.
        table = self._taggingTables.get(logic.TaggingProperty.Allegiance)
        if table:
            table.setContent(
                keyDescriptions=self._generateAllegianceDescriptions())

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

    def _taggingColourChanged(self) -> None:
        colours = app.TaggingColours(
            desirableColour=self._desirableTagColourButton.colour(),
            warningColour=self._warningTagColourButton.colour(),
            dangerColour=self._dangerTagColourButton.colour())

        for table in self._taggingTables.values():
            table.setTaggingColours(colours=colours)

    def _generateAllegianceDescriptions(self) -> typing.Mapping[str, str]:
        allegiances = traveller.AllegianceManager.instance().allegiances(
            milieu=self._milieuComboBox.currentEnum())

        # Create a copy of the allegiances list and sort it by code
        allegiances = list(allegiances)
        allegiances.sort(key=lambda x: x.code())

        descriptions: typing.Mapping[str, str] = {}
        for allegiance in allegiances:
            nameMap = allegiance.uniqueNameMap()
            for code, name in nameMap.items():
                descriptions[code] = name

        return descriptions
