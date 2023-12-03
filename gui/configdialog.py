import app
import asyncio
import depschecker
import enum
import gui
import json
import logging
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
                gui.MessageBoxEx.information(message)
            except Exception as ex:
                message = 'Clearing the tile cache succeeded but parsing response failed'
                logging.warning(message, exc_info=ex)
                gui.MessageBoxEx.warning(text=message, exception=ex)
            self.accept()
        elif isinstance(result, Exception):
            message = 'Request to clear tile cache failed'
            logging.error(message, exc_info=result)
            gui.MessageBoxEx.critical(text=message, exception=result)
            self.close()
        else:
            message = 'Request to clear tile cache returned an unexpected result'
            logging.critical(message, exc_info=result)
            gui.MessageBoxEx.critical(text=message, exception=result)
            self.close()

    def _workingTimerFired(self) -> None:
        text = self._workingLabel.text()
        if (len(text) % _ClearTileCacheDialog._WorkingDotCount) == 0:
            text = ''
        text += '.'
        self._workingLabel.setText(text)

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
        self.setWindowFlag(QtCore.Qt.WindowType.WindowMaximizeButtonHint, True)

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

        restartRequiredText = f'<p><b>Changes to this setting will be applied next time {app.AppName} is started</b></p>'

        # Traveller widgets
        self._milieuComboBox = gui.EnumComboBox(
            type=travellermap.Milieu,
            value=app.Config.instance().milieu(),
            textMap={milieu: travellermap.milieuDescription(milieu) for milieu in  travellermap.Milieu})
        self._milieuComboBox.setToolTip(gui.createStringToolTip(
            '<p>The milieu to use when determining sector and world information</p>' +
            restartRequiredText,
            escape=False))

        self._rulesComboBox = gui.EnumComboBox(
            type=traveller.Rules,
            value=app.Config.instance().rules())
        self._rulesComboBox.setToolTip(gui.createStringToolTip(
            '<p>The rules used for trade calculations</p>' +
            restartRequiredText,
            escape=False))

        travellerLayout = gui.FormLayoutEx()
        travellerLayout.addRow('Milieu:', self._milieuComboBox)
        travellerLayout.addRow('Rules:', self._rulesComboBox)

        travellerGroupBox = QtWidgets.QGroupBox('Traveller')
        travellerGroupBox.setLayout(travellerLayout)

        # Proxy Widgets
        self._proxyEnabledCheckBox = gui.CheckBoxEx()
        self._proxyEnabledCheckBox.setChecked(app.Config.instance().proxyEnabled())
        self._proxyEnabledCheckBox.stateChanged.connect(self._enableProxyToggled)
        self._proxyEnabledCheckBox.setToolTip(gui.createStringToolTip(
            '<p>Enable or disable the Traveller Map proxy.</p>'
            '<p>By default, {app} uses a local proxy to access Traveller Map. '
            'Using this proxy has two main benefits:</p>'
            '<ul style="margin-left:15px; -qt-list-indent:0;">'
            '<li>It allows {app} to overlay custom sectors on tiles returned '
            'by Traveller Map, in order to have them rendered in the map '
            'views.</li>'
            '<li>It allows {app} to create a persistent cache of the tiles '
            'returned by Traveller Map, this allows quicker rendering when '
            'viewing sections of the map you\'ve previously viewed.</li>'
            '</ul>'
            '<p>For security, this proxy only listens on localhost, meaning '
            'it can only be accessed from the system {app} is running on. '
            'The proxy also only allows access to the Traveller Map URL '
            'configured below.<p>'.format(app=app.AppName) +
            restartRequiredText,
            escape=False))

        self._proxyPortSpinBox = gui.SpinBoxEx()
        self._proxyPortSpinBox.setRange(1024, 65535)
        self._proxyPortSpinBox.setValue(app.Config.instance().proxyPort())
        self._proxyPortSpinBox.setEnabled(self._proxyEnabledCheckBox.isChecked())
        self._proxyPortSpinBox.setToolTip(gui.createStringToolTip(
            '<p>Specify the port the local Traveller Map proxy will listen '
            'on.</p>' \
            '<p>You may need to change the port the proxy listens on if there '
            'is a conflict with another service running on your system.</p>' +
            restartRequiredText,
            escape=False))

        self._proxyHostPoolSizeSpinBox = gui.SpinBoxEx()
        self._proxyHostPoolSizeSpinBox.setRange(1, 10)
        self._proxyHostPoolSizeSpinBox.setValue(app.Config.instance().proxyHostPoolSize())
        self._proxyHostPoolSizeSpinBox.setEnabled(self._proxyEnabledCheckBox.isChecked())
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
            'outgoing connections to travellermap.com in order to not place '
            'additional load on the site.</b></p>'.format(app=app.AppName) +
            restartRequiredText,
            escape=False))

        self._proxyMapUrlLineEdit = gui.LineEditEx()
        self._proxyMapUrlLineEdit.setText(app.Config.instance().proxyMapUrl())
        self._proxyMapUrlLineEdit.setMaximumWidth(200)
        self._proxyMapUrlLineEdit.setEnabled(self._proxyEnabledCheckBox.isChecked())
        self._proxyMapUrlLineEdit.setToolTip(gui.createStringToolTip(
            '<p>Specify the URL the proxy will use to access Traveller Map.</p>'
            '<p>If you run your own copy of Traveller Map, you can specify its '
            'URL here.</p>' +
            restartRequiredText,
            escape=False))

        # The proxy mode control is only shown if CairoSVG is detected. It's used
        # to set the flag to indicate if SVG composition is enabled. It's shown as a
        # combo box to make it easier to explain to the user what the difference is
        # between having it enabled and disabled.
        self._proxyCompositionModeComboBox = gui.ComboBoxEx()
        self._proxyCompositionModeComboBox.addItem('Hybrid', False)
        self._proxyCompositionModeComboBox.addItem('SVG', True)
        self._proxyCompositionModeComboBox.setCurrentByUserData(
            userData=app.Config.instance().proxySvgCompositionEnabled())
        self._proxyCompositionModeComboBox.setEnabled(
            self._proxyEnabledCheckBox.isChecked())
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
            restartRequiredText,
            escape=False))

        # NOTE: The tile cache size is shown in MB but is actually stored in bytes
        self._proxyTileCacheSizeSpinBox = gui.SpinBoxEx()
        self._proxyTileCacheSizeSpinBox.setRange(0, 4 * 1000) # 4GB max (in MB)
        self._proxyTileCacheSizeSpinBox.setValue(
            int(app.Config.instance().proxyTileCacheSize() / (1000 * 1000)))
        self._proxyTileCacheSizeSpinBox.setEnabled(self._proxyEnabledCheckBox.isChecked())
        self._proxyTileCacheSizeSpinBox.setToolTip(gui.createStringToolTip(
            '<p>Specify the amount of disk space to use to cache tiles.</p>'
            '<p>When the cache size reaches the specified limit, tiles will be '
            'automatically removed starting with the least recently used. A '
            'size of 0 will disable the disk cache.' +
            restartRequiredText,
            escape=False))

        self._proxyTileCacheLifetimeSpinBox = gui.SpinBoxEx()
        self._proxyTileCacheLifetimeSpinBox.setRange(0, 90)
        self._proxyTileCacheLifetimeSpinBox.setValue(
            app.Config.instance().proxyTileCacheLifetime())
        self._proxyTileCacheLifetimeSpinBox.setEnabled(self._proxyEnabledCheckBox.isChecked())
        self._proxyTileCacheLifetimeSpinBox.setToolTip(gui.createStringToolTip(
            '<p>Specify the max time the proxy will cache a tile on disk.</p>'
            '<p>A value of 0 will cause tiles to be cached indefinitely.</p>' +
            restartRequiredText,
            escape=False))

        # NOTE: The button for clearing the tile cache is enabled/disabled
        # based on if the proxy is currently running not if the enable check
        # box is currently checked. Clearing the cache is an immediate operation
        # that requires sending a request to the proxy process so it only makes
        # sense when it's actually running
        self._clearTileCacheButton = QtWidgets.QPushButton('Clear Tile Cache')
        self._clearTileCacheButton.setEnabled(proxy.MapProxy.instance().isRunning())
        self._clearTileCacheButton.clicked.connect(self._clearTileCacheClicked)

        proxyLayout = gui.FormLayoutEx()
        proxyLayout.addRow('Enabled:', self._proxyEnabledCheckBox)
        proxyLayout.addRow('Port:', self._proxyPortSpinBox)
        proxyLayout.addRow('Host Pool Size:', self._proxyHostPoolSizeSpinBox)
        proxyLayout.addRow('Map Url:', self._proxyMapUrlLineEdit)
        proxyLayout.addRow('Composition Mode:', self._proxyCompositionModeComboBox)
        proxyLayout.addRow('Tile Cache Size (MB):', self._proxyTileCacheSizeSpinBox)
        proxyLayout.addRow('Tile Cache Lifetime (days):', self._proxyTileCacheLifetimeSpinBox)
        proxyLayout.addRow('', self._clearTileCacheButton)

        proxyGroupBox = QtWidgets.QGroupBox('Proxy')
        proxyGroupBox.setLayout(proxyLayout)

        # GUI widgets
        self._colourThemeComboBox = gui.EnumComboBox(
            type=app.ColourTheme,
            value=app.Config.instance().colourTheme())
        self._colourThemeComboBox.setToolTip(gui.createStringToolTip(
            '<p>Select the colour theme.</p>' +
            restartRequiredText,
            escape=False))

        # NOTE: The interface scale is displayed in percent but is actually stored as a float scale
        # where 1.0 is 100%
        self._interfaceScaleSpinBox = gui.SpinBoxEx()
        self._interfaceScaleSpinBox.setRange(100, 400)
        self._interfaceScaleSpinBox.setValue(int(app.Config.instance().interfaceScale() * 100))
        self._interfaceScaleSpinBox.setToolTip(gui.createStringToolTip(
            '<p>Scale the UI up to make things easier to read</p>' +
            restartRequiredText,
            escape=False))

        self._showToolTipImagesCheckBox = gui.CheckBoxEx()
        self._showToolTipImagesCheckBox.setChecked(app.Config.instance().showToolTipImages())
        self._showToolTipImagesCheckBox.setToolTip(gui.createStringToolTip(
            '<p>Display world images in tool tips</p>'
            '<p>When enabled, {app.AppName} will retrieve world images to display in tool tips. It\'s '
            'recommended to disable this setting if operating offline or with a slow connection. Tool '
            'tip images are cached, however the first time a tool tip for a given world is displayed it '
            'can cause the user interface to block temporarily while the image is downloaded.</p>',
            escape=False))

        self._averageCaseColourButton = gui.ColourButton(app.Config.instance().averageCaseColour())
        self._averageCaseColourButton.setFixedWidth(ColourButtonWidth)
        self._averageCaseColourButton.setToolTip(gui.createStringToolTip(
            'Colour used to highlight values calculated using average dice rolls'))

        self._worstCaseColourButton = gui.ColourButton(app.Config.instance().worstCaseColour())
        self._worstCaseColourButton.setFixedWidth(ColourButtonWidth)
        self._worstCaseColourButton.setToolTip(gui.createStringToolTip(
            'Colour used to highlight values calculated using worst case dice rolls'))

        self._bestCaseColourButton = gui.ColourButton(app.Config.instance().bestCaseColour())
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
        self._desirableTagColourButton = gui.ColourButton(app.Config.instance().tagColour(app.TagLevel.Desirable))
        self._desirableTagColourButton.setFixedWidth(ColourButtonWidth)
        self._desirableTagColourButton.setToolTip(gui.createStringToolTip(
            'Colour used to highlight desirable tagging'))

        self._warningTagColourButton = gui.ColourButton(app.Config.instance().tagColour(app.TagLevel.Warning))
        self._warningTagColourButton.setFixedWidth(ColourButtonWidth)
        self._warningTagColourButton.setToolTip(gui.createStringToolTip(
            'Colour used to highlight warning tagging'))

        self._dangerTagColourButton = gui.ColourButton(app.Config.instance().tagColour(app.TagLevel.Danger))
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

    def _setupZoneTaggingTab(self) -> None:
        keyDescriptions = {}
        keyAliases = {}
        for zoneType in traveller.ZoneType:
            keyDescriptions[zoneType] = traveller.zoneTypeName(zoneType)
            keyAliases[zoneType] = traveller.zoneTypeCode(zoneType)

        self._zoneTaggingTable = self._createTaggingTable(
            keyTitle='Zone',
            keyDescriptions=keyDescriptions,
            keyAliases=keyAliases,
            taggingMap=app.Config.instance().zoneTagLevels())
        self._addTableTab(
            title='Zone Tagging',
            table=self._zoneTaggingTable)

    def _setupStarPortTaggingTab(self) -> None:
        self._starPortTaggingTable = self._createTaggingTable(
            keyTitle='Star Port',
            keyDescriptions=traveller.UWP.descriptionMap(traveller.UWP.Element.StarPort),
            taggingMap=app.Config.instance().starPortTagLevels())
        self._addTableTab(
            title='Star Port Tagging',
            table=self._starPortTaggingTable)

    def _setupWorldSizeTaggingTab(self) -> None:
        self._worldSizeTaggingTable = self._createTaggingTable(
            keyTitle='World Size',
            keyDescriptions=traveller.UWP.descriptionMap(traveller.UWP.Element.WorldSize),
            taggingMap=app.Config.instance().worldSizeTagLevels())
        self._addTableTab(
            title='World Size Tagging',
            table=self._worldSizeTaggingTable)

    def _setupAtmosphereTaggingTab(self) -> None:
        self._atmosphereTaggingTable = self._createTaggingTable(
            keyTitle='Atmosphere',
            keyDescriptions=traveller.UWP.descriptionMap(traveller.UWP.Element.Atmosphere),
            taggingMap=app.Config.instance().atmosphereTagLevels())
        self._addTableTab(
            title='Atmosphere Tagging',
            table=self._atmosphereTaggingTable)

    def _setupHydrographicsTaggingTab(self) -> None:
        self._hydrographicsTaggingTable = self._createTaggingTable(
            keyTitle='Hydrographics',
            keyDescriptions=traveller.UWP.descriptionMap(traveller.UWP.Element.Hydrographics),
            taggingMap=app.Config.instance().hydrographicsTagLevels())
        self._addTableTab(
            title='Hydrographics Tagging',
            table=self._hydrographicsTaggingTable)

    def _setupPopulationTaggingTab(self) -> None:
        self._populationTaggingTable = self._createTaggingTable(
            keyTitle='Population',
            keyDescriptions=traveller.UWP.descriptionMap(traveller.UWP.Element.Population),
            taggingMap=app.Config.instance().populationTagLevels())
        self._addTableTab(
            title='Population Tagging',
            table=self._populationTaggingTable)

    def _setupGovernmentTaggingTab(self) -> None:
        self._governmentTaggingTable = self._createTaggingTable(
            keyTitle='Government',
            keyDescriptions=traveller.UWP.descriptionMap(traveller.UWP.Element.Government),
            taggingMap=app.Config.instance().governmentTagLevels())
        self._addTableTab(
            title='Government Tagging',
            table=self._governmentTaggingTable)

    def _setupLawLevelTaggingTab(self) -> None:
        self._lawLevelTaggingTable = self._createTaggingTable(
            keyTitle='Law Level',
            keyDescriptions=traveller.UWP.descriptionMap(traveller.UWP.Element.LawLevel),
            taggingMap=app.Config.instance().lawLevelTagLevels())
        self._addTableTab(
            title='Law Level Tagging',
            table=self._lawLevelTaggingTable)

    def _setupTechLevelTaggingTab(self) -> None:
        self._techLevelTaggingTable = self._createTaggingTable(
            keyTitle='Tech Level',
            keyDescriptions=traveller.UWP.descriptionMap(traveller.UWP.Element.TechLevel),
            taggingMap=app.Config.instance().techLevelTagLevels())
        self._addTableTab(
            title='Tech Level Tagging',
            table=self._techLevelTaggingTable)

    def _setupBaseTypeTaggingTab(self) -> None:
        keyDescriptions = {}
        keyAliases = {}
        for baseType in traveller.BaseType:
            keyDescriptions[baseType] = traveller.Bases.description(baseType)
            keyAliases[baseType] = traveller.Bases.code(baseType)

        self._baseTypeTaggingTable = self._createTaggingTable(
            keyTitle='Base',
            keyDescriptions=keyDescriptions,
            keyAliases=keyAliases,
            taggingMap=app.Config.instance().baseTypeTagLevels())
        self._addTableTab(
            title='Base Tagging',
            table=self._baseTypeTaggingTable)

    def _setupTradeCodeTaggingTab(self) -> None:
        keyDescriptions = {}
        keyAliases = {}
        for tradeCode in traveller.TradeCode:
            keyDescriptions[tradeCode] = f'{traveller.tradeCodeName(tradeCode)} - {traveller.tradeCodeDescription(tradeCode)}'
            keyAliases[tradeCode] = traveller.tradeCodeString(tradeCode)

        self._tradeCodeTaggingTable = self._createTaggingTable(
            keyTitle='Trade Code',
            keyDescriptions=keyDescriptions,
            keyAliases=keyAliases,
            taggingMap=app.Config.instance().tradeCodeTagLevels())
        self._addTableTab(
            title='Trade Code Tagging',
            table=self._tradeCodeTaggingTable)

    def _setupResourcesTaggingTab(self) -> None:
        self._resourcesTaggingTable = self._createTaggingTable(
            keyTitle='Resources',
            keyDescriptions=traveller.Economics.descriptionMap(traveller.Economics.Element.Resources),
            taggingMap=app.Config.instance().resourceTagLevels())
        self._addTableTab(
            title='Resources Tagging',
            table=self._resourcesTaggingTable)

    def _setupLabourTaggingTab(self) -> None:
        self._labourTaggingTable = self._createTaggingTable(
            keyTitle='Labour',
            keyDescriptions=traveller.Economics.descriptionMap(traveller.Economics.Element.Labour),
            taggingMap=app.Config.instance().labourTagLevels())
        self._addTableTab(
            title='Labour Tagging',
            table=self._labourTaggingTable)

    def _setupInfrastructureTaggingTab(self) -> None:
        self._infrastructureTaggingTable = self._createTaggingTable(
            keyTitle='Infrastructure',
            keyDescriptions=traveller.Economics.descriptionMap(traveller.Economics.Element.Infrastructure),
            taggingMap=app.Config.instance().infrastructureTagLevels())
        self._addTableTab(
            title='Infrastructure Tagging',
            table=self._infrastructureTaggingTable)

    def _setupEfficiencyTaggingTab(self) -> None:
        self._efficiencyTaggingTable = self._createTaggingTable(
            keyTitle='Efficiency',
            keyDescriptions=traveller.Economics.descriptionMap(traveller.Economics.Element.Efficiency),
            taggingMap=app.Config.instance().efficiencyTagLevels())
        self._addTableTab(
            title='Efficiency Tagging',
            table=self._efficiencyTaggingTable)

    def _setupHeterogeneityTaggingTab(self) -> None:
        self._heterogeneityTaggingTable = self._createTaggingTable(
            keyTitle='Heterogeneity',
            keyDescriptions=traveller.Culture.descriptionMap(traveller.Culture.Element.Heterogeneity),
            taggingMap=app.Config.instance().heterogeneityTagLevels())
        self._addTableTab(
            title='Heterogeneity Tagging',
            table=self._heterogeneityTaggingTable)

    def _setupAcceptanceTaggingTab(self) -> None:
        self._acceptanceTaggingTable = self._createTaggingTable(
            keyTitle='Acceptance',
            keyDescriptions=traveller.Culture.descriptionMap(traveller.Culture.Element.Acceptance),
            taggingMap=app.Config.instance().acceptanceTagLevels())
        self._addTableTab(
            title='Acceptance Tagging',
            table=self._acceptanceTaggingTable)

    def _setupStrangenessTaggingTab(self) -> None:
        self._strangenessTaggingTable = self._createTaggingTable(
            keyTitle='Strangeness',
            keyDescriptions=traveller.Culture.descriptionMap(traveller.Culture.Element.Strangeness),
            taggingMap=app.Config.instance().strangenessTagLevels())
        self._addTableTab(
            title='Strangeness Tagging',
            table=self._strangenessTaggingTable)

    def _setupSymbolsTaggingTab(self) -> None:
        self._symbolsTaggingTable = self._createTaggingTable(
            keyTitle='Symbols',
            keyDescriptions=traveller.Culture.descriptionMap(traveller.Culture.Element.Symbols),
            taggingMap=app.Config.instance().symbolsTagLevels())
        self._addTableTab(
            title='Symbols Tagging',
            table=self._symbolsTaggingTable)

    def _setupNobilityTaggingTab(self) -> None:
        keyDescriptions = {}
        keyAliases = {}
        for nobilityType in traveller.NobilityType:
            keyDescriptions[nobilityType] = traveller.Nobilities.description(nobilityType)
            keyAliases[nobilityType] = traveller.Nobilities.code(nobilityType)

        self._nobilityTaggingTable = self._createTaggingTable(
            keyTitle='Nobility',
            keyDescriptions=keyDescriptions,
            keyAliases=keyAliases,
            taggingMap=app.Config.instance().nobilityTagLevels())
        self._addTableTab(
            title='Nobility Tagging',
            table=self._nobilityTaggingTable)

    def _setupAllegianceTaggingTab(self) -> None:
        allegiances = traveller.AllegianceManager.instance().allegiances()

        # Create a copy of the allegiances list and sort it by code
        allegiances = list(allegiances)
        allegiances.sort(key=lambda x: x.code())

        keyDescriptions = {}
        for allegiance in allegiances:
            nameMap = allegiance.uniqueNameMap()
            for code, name in nameMap.items():
                keyDescriptions[code] = name

        self._allegianceTaggingTable = self._createTaggingTable(
            keyTitle='Allegiance',
            keyDescriptions=keyDescriptions,
            taggingMap=app.Config.instance().allegianceTagLevels())
        self._addTableTab(
            title='Allegiance Tagging',
            table=self._allegianceTaggingTable)

    def _setupSpectralTaggingTab(self) -> None:
        self._spectralTaggingTable = self._createTaggingTable(
            keyTitle='Spectral Class',
            keyDescriptions=traveller.Star.descriptionMap(traveller.Star.Element.SpectralClass),
            taggingMap=app.Config.instance().spectralTagLevels())
        self._addTableTab(
            title='Spectral Class Tagging',
            table=self._spectralTaggingTable)

    def _setupLuminosityTaggingTab(self) -> None:
        self._luminosityTaggingTable = self._createTaggingTable(
            keyTitle='Luminosity Class',
            keyDescriptions=traveller.Star.descriptionMap(traveller.Star.Element.LuminosityClass),
            taggingMap=app.Config.instance().luminosityTagLevels())
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
        class RestartChecker(object):
            def __init__(self) -> None:
                self._needsRestart = False

            def needsRestart(self) -> bool:
                return self._needsRestart

            def update(self, needsRestart: bool):
                if needsRestart:
                    self._needsRestart = True

        checker = RestartChecker()

        try:
            config = app.Config.instance()
            checker.update(config.setMilieu(self._milieuComboBox.currentEnum()))
            checker.update(config.setRules(self._rulesComboBox.currentEnum()))

            checker.update(config.setProxyEnabled(self._proxyEnabledCheckBox.isChecked()))
            checker.update(config.setProxyPort(self._proxyPortSpinBox.value()))
            checker.update(config.setProxyHostPoolSize(self._proxyHostPoolSizeSpinBox.value()))
            checker.update(config.setProxyMapUrl(self._proxyMapUrlLineEdit.text()))
            checker.update(config.setProxyTileCacheSize(
                self._proxyTileCacheSizeSpinBox.value() * (1000 * 1000))) # Convert MB to bytes
            checker.update(config.setProxyTileCacheLifetime(
                self._proxyTileCacheLifetimeSpinBox.value()))
            checker.update(config.setProxySvgCompositionEnabled(
                self._proxyCompositionModeComboBox.currentUserData()))

            checker.update(config.setColourTheme(self._colourThemeComboBox.currentEnum()))
            checker.update(config.setInterfaceScale(
                self._interfaceScaleSpinBox.value() / 100)) # Convert percent to scale
            checker.update(config.setShowToolTipImages(self._showToolTipImagesCheckBox.isChecked()))
            checker.update(config.setAverageCaseColour(self._averageCaseColourButton.colour()))
            checker.update(config.setWorstCaseColour(self._worstCaseColourButton.colour()))
            checker.update(config.setBestCaseColour(self._bestCaseColourButton.colour()))

            checker.update(config.setTagColour(app.TagLevel.Desirable, self._desirableTagColourButton.colour()))
            checker.update(config.setTagColour(app.TagLevel.Warning, self._warningTagColourButton.colour()))
            checker.update(config.setTagColour(app.TagLevel.Danger, self._dangerTagColourButton.colour()))

            checker.update(config.setZoneTagLevels(self._taggingMapFromTable(self._zoneTaggingTable)))
            checker.update(config.setStarPortTagLevels(self._taggingMapFromTable(self._starPortTaggingTable)))
            checker.update(config.setWorldSizeTagLevels(self._taggingMapFromTable(self._worldSizeTaggingTable)))
            checker.update(config.setAtmosphereTagLevels(self._taggingMapFromTable(self._atmosphereTaggingTable)))
            checker.update(config.setHydrographicsTagLevels(self._taggingMapFromTable(self._hydrographicsTaggingTable)))
            checker.update(config.setPopulationTagLevels(self._taggingMapFromTable(self._populationTaggingTable)))
            checker.update(config.setGovernmentTagLevels(self._taggingMapFromTable(self._governmentTaggingTable)))
            checker.update(config.setLawLevelTagLevels(self._taggingMapFromTable(self._lawLevelTaggingTable)))
            checker.update(config.setTechLevelTagLevels(self._taggingMapFromTable(self._techLevelTaggingTable)))
            checker.update(config.setBaseTypeTagLevels(self._taggingMapFromTable(self._baseTypeTaggingTable)))
            checker.update(config.setTradeCodeTagLevels(self._taggingMapFromTable(self._tradeCodeTaggingTable)))
            checker.update(config.setResourceTagLevels(self._taggingMapFromTable(self._resourcesTaggingTable)))
            checker.update(config.setLabourTagLevels(self._taggingMapFromTable(self._labourTaggingTable)))
            checker.update(config.setInfrastructureTagLevels(self._taggingMapFromTable(self._infrastructureTaggingTable)))
            checker.update(config.setEfficiencyTagLevels(self._taggingMapFromTable(self._efficiencyTaggingTable)))
            checker.update(config.setHeterogeneityTagLevels(self._taggingMapFromTable(self._heterogeneityTaggingTable)))
            checker.update(config.setAcceptanceTagLevels(self._taggingMapFromTable(self._acceptanceTaggingTable)))
            checker.update(config.setStrangenessTagLevels(self._taggingMapFromTable(self._strangenessTaggingTable)))
            checker.update(config.setSymbolsTagLevels(self._taggingMapFromTable(self._symbolsTaggingTable)))
            checker.update(config.setNobilityTagLevels(self._taggingMapFromTable(self._nobilityTaggingTable)))
            checker.update(config.setAllegianceTagLevels(self._taggingMapFromTable(self._allegianceTaggingTable)))
            checker.update(config.setSpectralTagLevels(self._taggingMapFromTable(self._spectralTaggingTable)))
            checker.update(config.setLuminosityTagLevels(self._taggingMapFromTable(self._luminosityTaggingTable)))
        except Exception as ex:
            message = 'Failed to save configuration'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

        if checker.needsRestart():
            gui.MessageBoxEx.information(
                parent=self,
                text=f'Some changes will only be applied when {app.AppName} is restarted.')

    def _createTaggingTable(
            self,
            keyTitle: str,
            keyDescriptions: typing.Union[typing.Dict[str, str], typing.Dict[enum.Enum, str]],
            taggingMap: typing.Union[typing.Dict[str, app.TagLevel], typing.Dict[enum.Enum, app.TagLevel]],
            keyAliases: typing.Optional[typing.Union[typing.Dict[str, str], typing.Dict[enum.Enum, str]]] = None
            ) -> gui.ListTable:
        columnNames = [keyTitle, 'Tag Level', 'Description']

        table = gui.ListTable()
        table.setColumnHeaders(columnNames)
        table.setColumnsMoveable(False)
        table.resizeColumnsToContents() # Size columns to header text
        table.setSizeAdjustPolicy(
            QtWidgets.QAbstractScrollArea.SizeAdjustPolicy.AdjustToContentsOnFirstShow)

        # Setup horizontal scroll bar. Setting the last column to stretch to fit its content
        # is required to make the it appear reliably
        table.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollMode.ScrollPerPixel)
        table.horizontalHeader().setSectionResizeMode(
            table.columnCount() - 1,
            QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setStretchLastSection(False)

        # Disable sorting as some tables (e.g. luminosity) have a natural order that is not
        # ordered alphabetically so it makes sense to keep them in that order
        table.setSortingEnabled(False)

        for row, (key, description) in enumerate(keyDescriptions.items()):
            table.insertRow(row)

            toolTip = gui.createStringToolTip(description)

            keyText = None
            if keyAliases and key in keyAliases:
                keyText = keyAliases[key]
            else:
                keyText = key.name if isinstance(key, enum.Enum) else key

            item = QtWidgets.QTableWidgetItem(keyText)
            item.setData(QtCore.Qt.ItemDataRole.UserRole, key)
            item.setToolTip(toolTip)
            table.setItem(row, 0, item)

            tagLevel = None
            if key in taggingMap:
                tagLevel = taggingMap[key]

            item = QtWidgets.QTableWidgetItem()
            item.setToolTip(toolTip)
            table.setItem(row, 1, item)
            comboBox = gui.TagLevelComboBox(value=tagLevel)
            # Set the background role of the combo box to the same background role that will be used
            # for the alternating rows in the table. This makes sure the combo boxes have the same
            # colour as the rest of the row (when no tag level is selected). Note that this will most
            # likely break if sorting is ever enabled on the table
            comboBox.setBackgroundRole(QtGui.QPalette.ColorRole.AlternateBase if row % 2 else QtGui.QPalette.ColorRole.Base)
            table.setCellWidget(row, 1, comboBox)

            item = QtWidgets.QTableWidgetItem(description)
            item.setToolTip(toolTip)
            table.setItem(row, 2, item)

        # Set default column widths
        table.setColumnWidth(1, 100)
        table.horizontalHeader().setStretchLastSection(True)

        return table

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

    def _taggingMapFromTable(
            self,
            table: QtWidgets.QTableWidget
            ) -> typing.Union[typing.Dict[str, app.TagLevel], typing.Dict[enum.Enum, app.TagLevel]]:
        taggingMap = {}
        for row in range(table.rowCount()):
            item = table.item(row, 0)
            key = item.data(QtCore.Qt.ItemDataRole.UserRole)

            combo = table.cellWidget(row, 1)
            assert(isinstance(combo, gui.TagLevelComboBox))
            tagLevel = combo.currentTagLevel()
            if not tagLevel:
                continue # Ignore no tagging

            taggingMap[key] = tagLevel
        return taggingMap

    def _showWelcomeMessage(self) -> None:
        message = gui.InfoDialog(
            title=self.windowTitle(),
            html=_WelcomeMessage,
            noShowAgainId='ConfigWelcome')
        message.exec()

    def _enableProxyToggled(self, value: int) -> None:
        enabled = value != 0
        self._proxyPortSpinBox.setEnabled(enabled)
        self._proxyHostPoolSizeSpinBox.setEnabled(enabled)
        self._proxyMapUrlLineEdit.setEnabled(enabled)
        self._proxyTileCacheSizeSpinBox.setEnabled(enabled)
        self._proxyTileCacheLifetimeSpinBox.setEnabled(enabled)
        self._proxyCompositionModeComboBox.setEnabled(enabled)

    def _proxyModeChanged(self) -> None:
        if not self._proxyCompositionModeComboBox.currentUserData():
            return # Hybrid is selected, nothing to do
        gui.AutoSelectMessageBox.warning(
            text='SVG composition is VERY processor intensive and should only '
            'be used on systems with high core counts.',
            stateKey='SvgCompositionPerformanceWarning')

    def _clearTileCacheClicked(self) -> None:
        dlg = _ClearTileCacheDialog()
        dlg.exec()
