import app
import astronomer
import common
import enum
import gui
import logging
import logic
import traveller
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
    """,
    escape=False)

_RegenerateTradeCodesToolTip = gui.createStringToolTip(
    """
    <p>
    When enabled, this option tells {name} to regenerate Trade Codes for worlds
    based on the selected Rule System and each world’s UWP, instead of using the
    Trade Codes provided in the Traveller Map sector data.
    </p>
    <p>
    Traveller Map sectors have been created by many different contributors over
    a long period of time, often using different rule systems and varying levels
    of accuracy. As a result, the Trade Codes listed in the Traveller Map data
    for a given world may not match the Trade Codes that would be generated for
    that same world using the rules applied in your game.
    </p>
    <p>
    {name} will retain any Trade Codes from the Traveller Map data that are not
    explicitly defined by the selected Rule System. These additional Trade Codes
    do not affect trade calculations, but they can add useful flavour and
    context to your game. For example, some worlds include the Penal Colony (Pe)
    or Ancients Site (An) Trade Codes. While Mongoose Traveller does not define
    equivalents for these, {name} preserves them as they provide valuable
    information about the world.
    </p>
    """.format(name=app.AppName),
    escape=False)

"""
    'Pe': TradeCode.PenalColony,
    'Px': TradeCode.PrisonCamp,
    'Re': TradeCode.Reserve,
    'Ab': TradeCode.DataRepositoryWorld,
    'An': TradeCode.AncientsSiteWorld,
    'Ax': TradeCode.ConstructWorld,
    'Da': TradeCode.DangerousWorld,
    'Fo': TradeCode.ForbiddenWorld,
    'Pz': TradeCode.PuzzleWorld,
    'Rs': TradeCode.ResearchStation,
"""

class _InPlaceComboBoxWrapper(QtWidgets.QWidget):
    def __init__(self, colours, parent=None, value=None):
        super().__init__(parent)

        self._comboBox = gui.TagLevelComboBox(colours=colours, value=value)

        # NOTE: Change focus policy and install event filter to prevent
        # accidental changes to the value if, while scrolling the list the
        # widget is contained in, the spin box happens to move under the
        # cursor
        self._noWheelFilter = gui.NoWheelEventUnlessFocusedFilter()
        self._comboBox.installEventFilter(self._noWheelFilter)
        self._comboBox.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)

        # Wrap combo box in a layout with a stretch so the combo box
        # doesn't get stretched if the rows are multi-line
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._comboBox)
        layout.addStretch()
        self.setLayout(layout)

    def currentTagLevel(self) -> typing.Optional[logic.TagLevel]:
        return self._comboBox.currentTagLevel()

    def setColours(self, colours: app.TaggingColours) -> None:
        self._comboBox.setColours(colours)

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
            comboBox: _InPlaceComboBoxWrapper = self.cellWidget(row, 1)
            if not isinstance(comboBox, _InPlaceComboBoxWrapper):
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
            item.setTextAlignment(int(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop))
            self.setItem(row, 0, item)

            tagLevel = self._keyTagging.get(key)

            item = QtWidgets.QTableWidgetItem()
            item.setToolTip(toolTip)
            self.setItem(row, 1, item)
            comboBox = _InPlaceComboBoxWrapper(
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

            self.resizeRowToContents(row)

    def _syncToTagging(self) -> None:
        for row in range(self.rowCount()):
            comboBox: _InPlaceComboBoxWrapper = self.cellWidget(row, 1)
            if isinstance(comboBox, _InPlaceComboBoxWrapper):
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
            type=astronomer.Milieu,
            value=app.Config.instance().value(
                option=app.ConfigOption.Milieu,
                futureValue=True),
            textMap={milieu: astronomer.milieuDescription(milieu) for milieu in  astronomer.Milieu})
        self._milieuComboBox.setToolTip(gui.createStringToolTip(
            '<p>The milieu to use when determining sector and world information</p>',
            escape=False))
        self._milieuComboBox.currentIndexChanged.connect(self._milieuChanged)

        travellerLayout = gui.FormLayoutEx()
        travellerLayout.addRow(
            'Milieu:',
            self._milieuComboBox)

        travellerGroupBox = QtWidgets.QGroupBox('Traveller')
        travellerGroupBox.setLayout(travellerLayout)

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
        guiLayout.addRow('Average Case Highlight Colour:', self._averageCaseColourButton)
        guiLayout.addRow('Worst Case Highlight Colour:', self._worstCaseColourButton)
        guiLayout.addRow('Best Case Highlight Colour:', self._bestCaseColourButton)

        guiGroupBox = QtWidgets.QGroupBox('UI')
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

        self._rulesComboBox = gui.EnumComboBox(
            type=traveller.RuleSystem,
            value=rules.system())
        self._rulesComboBox.setToolTip(gui.createStringToolTip(
            '<p>The Traveller rule system to use</p>',
            escape=False))

        self._regenerateTradeCodesCheckBox = gui.CheckBoxEx()
        self._regenerateTradeCodesCheckBox.setChecked(
            rules.regenerateTradeCodes())
        self._regenerateTradeCodesCheckBox.setToolTip(_RegenerateTradeCodesToolTip)

        ruleSystemLayout = gui.FormLayoutEx()
        ruleSystemLayout.addRow(
            'Rule System',
            self._rulesComboBox)
        ruleSystemLayout.addRow(
            'Regenerate Trade Codes',
            self._regenerateTradeCodesCheckBox)

        ruleSystemGroupBox = QtWidgets.QGroupBox('Rule System')
        ruleSystemGroupBox.setLayout(ruleSystemLayout)

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
        tabLayout.addWidget(ruleSystemGroupBox)
        tabLayout.addWidget(starportFuelGroupBox)
        tabLayout.addStretch()

        tab = QtWidgets.QWidget()
        tab.setLayout(tabLayout)
        self._tabWidget.addTab(tab, 'Rules')

    def _setupTaggingTabs(self) -> None:
        self._setupTaggingTab(
            taggingProperty=logic.TaggingProperty.Zone,
            displayName='Zone',
            keyDescriptions={zone: astronomer.zoneTypeName(zone) for zone in astronomer.ZoneType},
            keyAliases={zone: astronomer.zoneTypeCode(zone) for zone in astronomer.ZoneType})

        self._setupTaggingTab(
            taggingProperty=logic.TaggingProperty.StarPort,
            displayName='Star Port',
            keyDescriptions=astronomer.UWP.descriptionMap(astronomer.UWP.Element.StarPort))

        self._setupTaggingTab(
            taggingProperty=logic.TaggingProperty.WorldSize,
            displayName='World Size',
            keyDescriptions=astronomer.UWP.descriptionMap(astronomer.UWP.Element.WorldSize))

        self._setupTaggingTab(
            taggingProperty=logic.TaggingProperty.Atmosphere,
            displayName='Atmosphere',
            keyDescriptions=astronomer.UWP.descriptionMap(astronomer.UWP.Element.Atmosphere))

        self._setupTaggingTab(
            taggingProperty=logic.TaggingProperty.Hydrographics,
            displayName='Hydrographics',
            keyDescriptions=astronomer.UWP.descriptionMap(astronomer.UWP.Element.Hydrographics))

        self._setupTaggingTab(
            taggingProperty=logic.TaggingProperty.Population,
            displayName='Population',
            keyDescriptions=astronomer.UWP.descriptionMap(astronomer.UWP.Element.Population))

        self._setupTaggingTab(
            taggingProperty=logic.TaggingProperty.Government,
            displayName='Government',
            keyDescriptions=astronomer.UWP.descriptionMap(astronomer.UWP.Element.Government))

        self._setupTaggingTab(
            taggingProperty=logic.TaggingProperty.LawLevel,
            displayName='Law Level',
            keyDescriptions=astronomer.UWP.descriptionMap(astronomer.UWP.Element.LawLevel))

        self._setupTaggingTab(
            taggingProperty=logic.TaggingProperty.TechLevel,
            displayName='Tech Level',
            keyDescriptions=astronomer.UWP.descriptionMap(astronomer.UWP.Element.TechLevel))

        self._setupTaggingTab(
            taggingProperty=logic.TaggingProperty.BaseType,
            displayName='Base',
            keyDescriptions={base: astronomer.Bases.description(base) for base in  astronomer.BaseType},
            keyAliases={base: astronomer.Bases.code(base) for base in  astronomer.BaseType})

        self._setupTaggingTab(
            taggingProperty=logic.TaggingProperty.TradeCode,
            displayName='Trade Code',
            keyDescriptions={code: f'{traveller.tradeCodeName(code)} - {traveller.tradeCodeDescription(code)}' for code in  traveller.TradeCode},
            keyAliases={code: traveller.tradeCodeString(code) for code in  traveller.TradeCode})

        self._setupTaggingTab(
            taggingProperty=logic.TaggingProperty.Resources,
            displayName='Resources',
            keyDescriptions=astronomer.Economics.descriptionMap(astronomer.Economics.Element.Resources))

        self._setupTaggingTab(
            taggingProperty=logic.TaggingProperty.Labour,
            displayName='Labour',
            keyDescriptions=astronomer.Economics.descriptionMap(astronomer.Economics.Element.Labour))

        self._setupTaggingTab(
            taggingProperty=logic.TaggingProperty.Infrastructure,
            displayName='Infrastructure',
            keyDescriptions=astronomer.Economics.descriptionMap(astronomer.Economics.Element.Infrastructure))

        self._setupTaggingTab(
            taggingProperty=logic.TaggingProperty.Efficiency,
            displayName='Efficiency',
            keyDescriptions=astronomer.Economics.descriptionMap(astronomer.Economics.Element.Efficiency))

        self._setupTaggingTab(
            taggingProperty=logic.TaggingProperty.Heterogeneity,
            displayName='Heterogeneity',
            keyDescriptions=astronomer.Culture.descriptionMap(astronomer.Culture.Element.Heterogeneity))

        self._setupTaggingTab(
            taggingProperty=logic.TaggingProperty.Acceptance,
            displayName='Acceptance',
            keyDescriptions=astronomer.Culture.descriptionMap(astronomer.Culture.Element.Acceptance))

        self._setupTaggingTab(
            taggingProperty=logic.TaggingProperty.Strangeness,
            displayName='Strangeness',
            keyDescriptions=astronomer.Culture.descriptionMap(astronomer.Culture.Element.Strangeness))

        self._setupTaggingTab(
            taggingProperty=logic.TaggingProperty.Symbols,
            displayName='Symbols',
            keyDescriptions=astronomer.Culture.descriptionMap(astronomer.Culture.Element.Symbols))

        self._setupTaggingTab(
            taggingProperty=logic.TaggingProperty.Nobility,
            displayName='Nobility',
            keyDescriptions={nobility: astronomer.Nobilities.description(nobility) for nobility in astronomer.NobilityType},
            keyAliases={nobility: astronomer.Nobilities.code(nobility) for nobility in astronomer.NobilityType})

        self._setupTaggingTab(
            taggingProperty=logic.TaggingProperty.Allegiance,
            displayName='Allegiance',
            keyDescriptions=self._generateAllegianceDescriptions())

        self._setupTaggingTab(
            taggingProperty=logic.TaggingProperty.Spectral,
            displayName='Spectral Class',
            keyDescriptions=astronomer.Star.descriptionMap(astronomer.Star.Element.SpectralClass))

        self._setupTaggingTab(
            taggingProperty=logic.TaggingProperty.Luminosity,
            displayName='Luminosity Class',
            keyDescriptions=astronomer.Star.descriptionMap(astronomer.Star.Element.LuminosityClass))

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

    def _saveConfig(self) -> None:
        try:
            app.Config.instance().setValue(
                option=app.ConfigOption.Milieu,
                value=self._milieuComboBox.currentEnum())
            app.Config.instance().setValue(
                option=app.ConfigOption.Rules,
                value=traveller.Rules(
                    system=self._rulesComboBox.currentEnum(),
                    regenerateTradeCodes=self._regenerateTradeCodesCheckBox.isChecked(),
                    classAStarPortFuelType=self._classAStarPortFuelType.currentEnum(),
                    classBStarPortFuelType=self._classBStarPortFuelType.currentEnum(),
                    classCStarPortFuelType=self._classCStarPortFuelType.currentEnum(),
                    classDStarPortFuelType=self._classDStarPortFuelType.currentEnum(),
                    classEStarPortFuelType=self._classEStarPortFuelType.currentEnum()))

            app.Config.instance().setValue(
                option=app.ConfigOption.ColourTheme,
                value=self._colourThemeComboBox.currentEnum())
            app.Config.instance().setValue(
                option=app.ConfigOption.InterfaceScale,
                value=self._interfaceScaleSpinBox.value() / 100) # Convert percent to scale
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

    def _taggingColourChanged(self) -> None:
        colours = app.TaggingColours(
            desirableColour=self._desirableTagColourButton.colour(),
            warningColour=self._warningTagColourButton.colour(),
            dangerColour=self._dangerTagColourButton.colour())

        for table in self._taggingTables.values():
            table.setTaggingColours(colours=colours)

    def _generateAllegianceDescriptions(self) -> typing.Mapping[str, str]:
        universe = astronomer.WorldManager.instance().universe()
        milieu = self._milieuComboBox.currentEnum()

        codeToAllegianceMap: typing.Dict[
            str, # Allegiance Code
            typing.List[typing.Tuple[
                astronomer.Sector,
                astronomer.Allegiance]]] = {}
        for sector in universe.yieldSectors(milieu=milieu):
            for allegiance in sector.allegiances():
                allegianceList = codeToAllegianceMap.get(allegiance.code())
                if allegianceList is None:
                    allegianceList = []
                    codeToAllegianceMap[allegiance.code()] = allegianceList
                allegianceList.append((sector, allegiance))

        codeToDescriptionMap: typing.Dict[str, str] = {}
        for allegianceCode, allegianceList in codeToAllegianceMap.items():
            nameToSectorMap: typing.Dict[
                str, # Lower case allegiance name
                typing.List[typing.Tuple[
                    str, # Normal case allegiance name
                    str # Sector name
                    ]]] = {}
            for sector, allegiance in allegianceList:
                lowerName = allegiance.name().lower()
                _, sectorList = nameToSectorMap.get(lowerName, (None, None))
                if sectorList is None:
                    sectorList = []
                    nameToSectorMap[lowerName] = (allegiance.name(), sectorList)
                sectorList.append(sector.name())

            description = ''
            for allegianceName, sectorList in nameToSectorMap.values():
                if len(nameToSectorMap) == 1:
                    description = allegianceName
                    break

                if description:
                    description += '\n'
                description += '{name} in {sectors}'.format(
                    name=allegianceName,
                    sectors=common.humanFriendlyListString(sectorList))

            codeToDescriptionMap[allegianceCode] = description

        # Sort by code
        tempList = [(code, desc) for code, desc in codeToDescriptionMap.items()]
        tempList.sort(key=lambda data: data[0])
        codeToDescriptionMap = {code: desc for code, desc in tempList}

        return codeToDescriptionMap
