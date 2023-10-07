import app
import enum
import gui
import logging
import traveller
import travellermap
import typing
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
        self._mapUrlLineEdit = gui.LineEditEx()
        self._mapUrlLineEdit.setText(app.Config.instance().travellerMapUrl())
        self._mapUrlLineEdit.setToolTip(gui.createStringToolTip(
            '<p>If you run your own copy of Traveller Map, you can specify it\'s URL here.</p>' +
            restartRequiredText,
            escape=False))

        self._mapProxyPortSpinBox = gui.SpinBoxEx()
        self._mapProxyPortSpinBox.setRange(0, 65535)
        self._mapProxyPortSpinBox.setValue(app.Config.instance().mapProxyPort())
        self._mapProxyPortSpinBox.setToolTip(gui.createStringToolTip(
            '<p>Specify the port the local Traveller Map proxy will listen on.</p>' +
            f'<p>By default {app.AppName} uses a local proxy to access Traveller Map. ' +
            'Using this proxy has two main benefits:</p>' +
            '<ul style="margin-left:15px; -qt-list-indent:0;">' +
            f'<li>It allows {app.AppName} to overlay custom sectors on tiles returned by ' +
            'Traveller Map, in order to have them rendered in the integrated map views.</li>' +
            '<li>It allocates more memory to be used for caching tiles in order to ' +
            'improve performance when doing a lot of scrolling & zooming.</li>' +
            '</ul>' +
            '<p>For increased security, this proxy only listens on localhost, meaning ' +
            f'it can only be accessed from the system {app.AppName} is running on. ' +
            'The proxy also only allows access to the Traveller Map URL configured ' +
            'above.<p>' +
            '<p>You may need to change the port the proxy listens on if there is a ' +
            'conflict with another service running on you system. The port can be set ' +
            'to 0 in order to disable the use of the proxy, however this will also ' +
            'disable the features mentioned above.</p>' +
            restartRequiredText,
            escape=False))

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
        travellerLayout.addRow('Traveller Map Url:', self._mapUrlLineEdit)
        travellerLayout.addRow('Map Proxy Port:', self._mapProxyPortSpinBox)
        travellerLayout.addRow('Milieu:', self._milieuComboBox)
        travellerLayout.addRow('Rules:', self._rulesComboBox)

        gameGroupBox = QtWidgets.QGroupBox('Traveller')
        gameGroupBox.setLayout(travellerLayout)

        # GUI widgets
        self._colourThemeComboBox = gui.EnumComboBox(
            type=app.ColourTheme,
            value=app.Config.instance().colourTheme())
        self._colourThemeComboBox.setToolTip(gui.createStringToolTip(
            '<p>Select the colour theme.</p>' +
            restartRequiredText,
            escape=False))

        # Note that this displays the interface scale as an integer percentage increase but it's
        # actually stored as a float scalar
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
            '<p>Display world images in tool tips</p>' \
            f'<p>When enabled, {app.AppName} will retrieve world images to display in tool tips. It\'s '
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
        tabLayout.addWidget(gameGroupBox)
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
        mapUrl = QtCore.QUrl(self._mapUrlLineEdit.text())
        # Map URL must have a scheme but no path or options
        if mapUrl.scheme() != 'http' and mapUrl.scheme() != 'https':
            gui.MessageBoxEx.critical('The Traveller Map URL must use http or https')
            return False
        if (mapUrl.path() != '' and mapUrl.path() != '/') or mapUrl.query():
            gui.MessageBoxEx.critical('The Traveller Map URL can\'t have a path or query')
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
            checker.update(config.setTravellerMapUrl(self._mapUrlLineEdit.text()))
            checker.update(config.setMapProxyPort(self._mapProxyPortSpinBox.value()))
            checker.update(config.setMilieu(self._milieuComboBox.currentEnum()))
            checker.update(config.setRules(self._rulesComboBox.currentEnum()))
            checker.update(config.setColourTheme(self._colourThemeComboBox.currentEnum()))
            checker.update(config.setInterfaceScale(self._interfaceScaleSpinBox.value() / 100))
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
