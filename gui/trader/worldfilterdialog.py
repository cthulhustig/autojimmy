import app
import enum
import gui
import logic
import traveller
import typing
from PyQt5 import QtWidgets, QtCore

class _FilterType(enum.Enum):
    NameFilter = 'Name'
    TagLevelFilter = 'Tag Level'
    ZoneFilter = 'Zone'
    UWPFilter = 'UWP'
    EconomicsFilter = 'Economics'
    CultureFilter = 'Culture'
    RefuellingFilter = 'Refuelling'
    AllegianceFilter = 'Allegiance'
    SophontFilter = 'Sophonts'
    BaseFilter = 'Bases'
    RemarksFilter = 'Remarks'
    NobilityFilter = 'Nobilities'
    TradeCodeFilter = 'TradeCodes'
    PBGFilter = 'PBG'


_ComparisonFilterOperationTextMap = {
    logic.ComparisonFilterOperation.Equal: 'Equal To',
    logic.ComparisonFilterOperation.NotEqual: 'Not Equal To',
    logic.ComparisonFilterOperation.Greater: 'Greater Than',
    logic.ComparisonFilterOperation.GreaterOrEqual: 'Greater Than or Equal To',
    logic.ComparisonFilterOperation.Less: 'Less Than',
    logic.ComparisonFilterOperation.LessOrEqual: 'Less Than or Equal To'
}

_ListFilterOperationTextMap = {
    logic.ListFilterOperation.ContainsAny: 'Contains Any',
    logic.ListFilterOperation.ContainsAll: 'Contains All',
    logic.ListFilterOperation.ContainsOnly: 'Contains Only'
}

_StringFilterOperationTextMap = {
    logic.StringFilterOperation.ContainsString: 'Contains String',
    logic.StringFilterOperation.MatchRegex: 'Matches Regex'
}

_NameFilterTypeTextMap = {
    logic.NameFiler.Type.WorldName: 'World Name',
    logic.NameFiler.Type.SectorName: 'Sector Name',
    logic.NameFiler.Type.SubsectorName: 'Subsector Name'
}

_RefuellingFilterTypeTextMap = {
    logic.RefuellingFilter.Type.RefinedRefuelling: 'Refined',
    logic.RefuellingFilter.Type.UnrefinedRefuelling: 'Unrefined',
    logic.RefuellingFilter.Type.GasGiantRefuelling: 'Gas Giant',
    logic.RefuellingFilter.Type.WaterRefuelling: 'Water',
    logic.RefuellingFilter.Type.FuelCacheRefuelling: 'Fuel Cache',
    logic.RefuellingFilter.Type.AnomalyRefuelling: 'Anomaly',
}

_UWPElementTextMap = {
    traveller.UWP.Element.StarPort: 'Star Port',
    traveller.UWP.Element.WorldSize: 'World Size',
    traveller.UWP.Element.Atmosphere: 'Atmosphere',
    traveller.UWP.Element.Hydrographics: 'Hydrographics',
    traveller.UWP.Element.Population: 'Population',
    traveller.UWP.Element.Government: 'Government',
    traveller.UWP.Element.LawLevel: 'Law Level',
    traveller.UWP.Element.TechLevel: 'Tech Level'
}

_EconomicsElementTextMap = {
    traveller.Economics.Element.Resources: 'Resources',
    traveller.Economics.Element.Labour: 'Labour',
    traveller.Economics.Element.Infrastructure: 'Infrastructure',
    traveller.Economics.Element.Efficiency: 'Efficiency'
}

_CultureElementTextMap = {
    traveller.Culture.Element.Heterogeneity: 'Heterogeneity',
    traveller.Culture.Element.Acceptance: 'Acceptance',
    traveller.Culture.Element.Strangeness: 'Strangeness',
    traveller.Culture.Element.Symbols: 'Symbols'
}

_PBGElementTextMap = {
    traveller.PBG.Element.PopulationMultiplier: 'Population Multiplier',
    traveller.PBG.Element.PlanetoidBelts: 'Planetoid Belts',
    traveller.PBG.Element.GasGiants: 'Gas Giants'
}

class _CodeComboBox(QtWidgets.QComboBox):
    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        # Some of the description text is pretty long, limit the size of the combo box so it
        # doesn't make the dialog really wide
        self.setMaximumWidth(300)

    def currentCode(self) -> str:
        return self.currentData(QtCore.Qt.ItemDataRole.UserRole)

    def setCurrentCode(self, code: str) -> None:
        for index in range(self.count()):
            if code == self.itemData(index, QtCore.Qt.ItemDataRole.UserRole):
                self.setCurrentIndex(index)
                return

class _UWPCodeComboBox(_CodeComboBox):
    def setElement(self, element: traveller.UWP.Element) -> None:
        self.clear()
        for code, description in traveller.UWP.descriptionMap(element=element).items():
            self.addItem(f'{code} - {description}', code)

class _EconomicsCodeComboBox(_CodeComboBox):
    def setElement(self, element: traveller.Economics.Element) -> None:
        self.clear()
        for code, description in traveller.Economics.descriptionMap(element=element).items():
            self.addItem(f'{code} - {description}', code)

class _CultureCodeComboBox(_CodeComboBox):
    def setElement(self, element: traveller.Culture.Element) -> None:
        self.clear()
        for code, description in traveller.Culture.descriptionMap(element=element).items():
            self.addItem(f'{code} - {description}', code)

class _PBGCodeComboBox(_CodeComboBox):
    def setElement(self, element: traveller.PBG.Element) -> None:
        self.clear()
        for code in traveller.PBG.codeList(element=element):
            self.addItem(f'{code}', code)

class _VerticallyResizingStackWidget(QtWidgets.QStackedWidget):
    def sizeHint(self) -> QtCore.QSize:
        hint = self.currentWidget().sizeHint()
        for index in range(self.count()):
            widget = self.widget(index)
            hint.setWidth(max(hint.width(), widget.sizeHint().width()))
        return hint

    def minimumSizeHint(self) -> QtCore.QSize:
        hint = self.currentWidget().minimumSizeHint()
        for index in range(self.count()):
            widget = self.widget(index)
            hint.setWidth(max(hint.width(), widget.minimumSizeHint().width()))
        return hint

class _EnumOptionWidget(QtWidgets.QWidget):
    def __init__(
            self,
            type: typing.Type[enum.Enum],
            columnCount: int,
            textMap: typing.Optional[typing.Mapping[enum.Enum, str]] = None,
            sortAlphabetically: bool = False, # Use definition order if False
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self._optionMap: typing.Dict[enum.Enum, gui.CheckBoxEx] = {}

        if sortAlphabetically:
            options = list(type)
            options.sort(key=lambda e: e.name)
        else:
            options = type

        layout = QtWidgets.QGridLayout()
        for index, option in enumerate(options):
            column = index % columnCount
            row = index // columnCount

            text = None
            if textMap:
                text = textMap.get(option)
            if not text:
                text = str(option.value)

            checkBox = gui.CheckBoxEx(text)
            layout.addWidget(checkBox, row, column)
            self._optionMap[option] = checkBox

        # Set size policy so widget will be resized when part of a FormLayout
        self.setLayout(layout)

    def checkedEnums(self) -> typing.Iterable[enum.Enum]:
        checkedEnums = []
        for option, checkBox in self._optionMap.items():
            if checkBox.isChecked():
                checkedEnums.append(option)
        return checkedEnums

    def setCheckedEnums(self, values: typing.Iterable[enum.Enum]) -> None:
        self.clearCheckedEnums()
        for value in values:
            checkBox = self._optionMap.get(value)
            if checkBox:
                checkBox.setChecked(True)

    def clearCheckedEnums(self) -> None:
        for checkBox in self._optionMap.values():
            checkBox.setChecked(False)

class WorldFilterDialog(gui.DialogEx):
    def __init__(
            self,
            title: str,
            editFilter: typing.Optional[logic.WorldFilter] = None,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            title=title,
            configSection='WorldFilterDialog',
            parent=parent)

        self._setupFilterComboBox()
        self._setupLayoutStack()
        self._setupButtonLayout()

        self._setupNameFilterLayout()
        self._setupTagLevelFilterLayout()
        self._setupZoneFilterLayout()
        self._setupUWPFilterLayout()
        self._setupEconomicsFilterLayout()
        self._setupCultureFilterLayout()
        self._setupRefuellingFilerLayout()
        self._setupAllegianceFilerLayout()
        self._setupSophontFilterLayout()
        self._setupBaseFilterLayout()
        self._setupNobilityFilterLayout()
        self._setupRemarksFilterLayout()
        self._setupTradeCodeFilterLayout()
        self._setupPBGFilterLayout()

        topLayout = QtWidgets.QHBoxLayout()
        topLayout.addWidget(self._filterTypeComboBox)
        topLayout.addLayout(self._buttonLayout)

        layout = gui.FormLayoutEx()
        layout.addRow('Filter:', topLayout)
        layout.addRow(self._stack)
        # Prevent manual resizing of the dialog
        layout.setSizeConstraint(QtWidgets.QLayout.SizeConstraint.SetFixedSize)

        self.setLayout(layout)
        self._syncLayouts()

        if editFilter:
            self.setFilter(editFilter)

        self._checkValidity()

    def filter(self) -> logic.WorldFilter:
        filterType = self._filterTypeComboBox.currentEnum()
        if filterType == _FilterType.NameFilter:
            return logic.NameFiler(
                type=self._nameFilterTypeCombo.currentEnum(),
                operation=self._nameFilterOperationCombo.currentEnum(),
                value=self._nameFilterValueLineEdit.text())
        elif filterType == _FilterType.TagLevelFilter:
            return logic.TagLevelFiler(
                operation=self._tagLevelFilterOperationComboBox.currentEnum(),
                value=self._tagLevelFilterValueComboBox.currentTagLevel())
        elif filterType == _FilterType.ZoneFilter:
            return logic.ZoneFiler(
                operation=self._zoneFilterOperationComboBox.currentEnum(),
                value=self._zoneFilterValueComboBox.currentEnum())
        elif filterType == _FilterType.UWPFilter:
            return logic.UWPFilter(
                element=self._uwpFilterElementComboBox.currentEnum(),
                operation=self._uwpFilterOperationComboBox.currentEnum(),
                value=self._uwpFilterValueComboBox.currentCode())
        elif filterType == _FilterType.EconomicsFilter:
            return logic.EconomicsFilter(
                element=self._economicsFilterElementComboBox.currentEnum(),
                operation=self._economicsFilterOperationComboBox.currentEnum(),
                value=self._economicsFilterValueComboBox.currentCode())
        elif filterType == _FilterType.CultureFilter:
            return logic.CultureFilter(
                element=self._cultureFilterElementComboBox.currentEnum(),
                operation=self._cultureFilterOperationComboBox.currentEnum(),
                value=self._cultureFilterValueComboBox.currentCode())
        elif filterType == _FilterType.RefuellingFilter:
            return logic.RefuellingFilter(
                operation=self._refuellingFilterOperationComboBox.currentEnum(),
                value=self._refuellingFilterValuesList.checkedEnums(),
                rules=app.Config.instance().value(option=app.ConfigOption.Rules))
        elif filterType == _FilterType.AllegianceFilter:
            return logic.AllegianceFilter(
                operation=self._allegianceFilterOperationCombo.currentEnum(),
                value=self._allegianceFilterValueLineEdit.text())
        elif filterType == _FilterType.SophontFilter:
            return logic.SophontFilter(
                operation=self._sophontFilterOperationCombo.currentEnum(),
                value=self._sophontFilterValueLineEdit.text())
        elif filterType == _FilterType.BaseFilter:
            return logic.BaseFilter(
                operation=self._basesFilterOperationComboBox.currentEnum(),
                value=self._basesFilterValuesList.checkedEnums())
        elif filterType == _FilterType.NobilityFilter:
            return logic.NobilityFilter(
                operation=self._nobilityFilterOperationComboBox.currentEnum(),
                value=self._nobilityFilterValuesList.checkedEnums())
        elif filterType == _FilterType.RemarksFilter:
            return logic.RemarksFilter(
                operation=self._remarksFilterOperationCombo.currentEnum(),
                value=self._remarksFilterValueLineEdit.text())
        elif filterType == _FilterType.TradeCodeFilter:
            return logic.TradeCodeFilter(
                operation=self._tradeCodeFilterOperationComboBox.currentEnum(),
                value=self._tradeCodeFilterValuesList.checkedEnums())
        elif filterType == _FilterType.PBGFilter:
            return logic.PBGFilter(
                element=self._pbgFilterElementComboBox.currentEnum(),
                operation=self._pbgFilterOperationComboBox.currentEnum(),
                value=self._pbgFilterValueComboBox.currentCode())
        return None # Unknown filter type

    def setFilter(self, filter: logic.WorldFilter) -> None:
        if isinstance(filter, logic.NameFiler):
            self._filterTypeComboBox.setCurrentEnum(_FilterType.NameFilter)
            self._nameFilterTypeCombo.setCurrentEnum(filter.type())
            self._nameFilterOperationCombo.setCurrentEnum(filter.operation())
            self._nameFilterValueLineEdit.setText(filter.value())
        elif isinstance(filter, logic.TagLevelFiler):
            self._filterTypeComboBox.setCurrentEnum(_FilterType.TagLevelFilter)
            self._tagLevelFilterOperationComboBox.setCurrentEnum(filter.operation())
            self._tagLevelFilterValueComboBox.setCurrentTagLevel(filter.value())
        elif isinstance(filter, logic.ZoneFiler):
            self._filterTypeComboBox.setCurrentEnum(_FilterType.ZoneFilter)
            self._zoneFilterOperationComboBox.setCurrentEnum(filter.operation())
            self._zoneFilterValueComboBox.setCurrentEnum(filter.value())
        elif isinstance(filter, logic.UWPFilter):
            self._filterTypeComboBox.setCurrentEnum(_FilterType.UWPFilter)
            self._uwpFilterElementComboBox.setCurrentEnum(filter.element())
            self._uwpFilterOperationComboBox.setCurrentEnum(filter.operation())
            self._uwpFilterValueComboBox.setCurrentCode(filter.value())
        elif isinstance(filter, logic.EconomicsFilter):
            self._filterTypeComboBox.setCurrentEnum(_FilterType.EconomicsFilter)
            self._economicsFilterElementComboBox.setCurrentEnum(filter.element())
            self._economicsFilterOperationComboBox.setCurrentEnum(filter.operation())
            self._economicsFilterValueComboBox.setCurrentCode(filter.value())
        elif isinstance(filter, logic.CultureFilter):
            self._filterTypeComboBox.setCurrentEnum(_FilterType.CultureFilter)
            self._cultureFilterElementComboBox.setCurrentEnum(filter.element())
            self._cultureFilterOperationComboBox.setCurrentEnum(filter.operation())
            self._cultureFilterValueComboBox.setCurrentCode(filter.value())
        elif isinstance(filter, logic.RefuellingFilter):
            self._filterTypeComboBox.setCurrentEnum(_FilterType.RefuellingFilter)
            self._refuellingFilterOperationComboBox.setCurrentEnum(filter.operation())
            self._refuellingFilterValuesList.setCheckedEnums(filter.value())
        elif isinstance(filter, logic.AllegianceFilter):
            self._filterTypeComboBox.setCurrentEnum(_FilterType.AllegianceFilter)
            self._allegianceFilterOperationCombo.setCurrentEnum(filter.operation())
            self._allegianceFilterValueLineEdit.setText(filter.value())
        elif isinstance(filter, logic.SophontFilter):
            self._filterTypeComboBox.setCurrentEnum(_FilterType.SophontFilter)
            self._sophontFilterOperationCombo.setCurrentEnum(filter.operation())
            self._sophontFilterValueLineEdit.setText(filter.value())
        elif isinstance(filter, logic.BaseFilter):
            self._filterTypeComboBox.setCurrentEnum(_FilterType.BaseFilter)
            self._basesFilterOperationComboBox.setCurrentEnum(filter.operation())
            self._basesFilterValuesList.setCheckedEnums(filter.value())
        elif isinstance(filter, logic.NobilityFilter):
            self._filterTypeComboBox.setCurrentEnum(_FilterType.NobilityFilter)
            self._nobilityFilterOperationComboBox.setCurrentEnum(filter.operation())
            self._nobilityFilterValuesList.setCheckedEnums(filter.value())
        elif isinstance(filter, logic.RemarksFilter):
            self._filterTypeComboBox.setCurrentEnum(_FilterType.RemarksFilter)
            self._remarksFilterOperationCombo.setCurrentEnum(filter.operation())
            self._remarksFilterValueLineEdit.setText(filter.value())
        elif isinstance(filter, logic.TradeCodeFilter):
            self._filterTypeComboBox.setCurrentEnum(_FilterType.TradeCodeFilter)
            self._tradeCodeFilterOperationComboBox.setCurrentEnum(filter.operation())
            self._tradeCodeFilterValuesList.setCheckedEnums(filter.value())
        elif isinstance(filter, logic.PBGFilter):
            self._filterTypeComboBox.setCurrentEnum(_FilterType.PBGFilter)
            self._pbgFilterElementComboBox.setCurrentEnum(filter.element())
            self._pbgFilterOperationComboBox.setCurrentEnum(filter.operation())
            self._pbgFilterValueComboBox.setCurrentCode(filter.value())
        else:
            raise TypeError(f'Invalid filter type {type(filter)}')

    def _setupFilterComboBox(self) -> None:
        self._filterTypeComboBox = gui.EnumComboBox(type=_FilterType)
        self._filterTypeComboBox.currentIndexChanged.connect(self._filterTypeChanged)

    def _setupLayoutStack(self) -> None:
        self._stack = _VerticallyResizingStackWidget()
        self._stackMap = {}

    def _setupNameFilterLayout(self) -> None:
        self._nameFilterTypeCombo = gui.EnumComboBox(
            type=logic.NameFiler.Type,
            textMap=_NameFilterTypeTextMap)

        self._nameFilterOperationCombo = gui.EnumComboBox(
            type=logic.StringFilterOperation,
            textMap=_StringFilterOperationTextMap)
        self._nameFilterOperationCombo.currentIndexChanged.connect(self._nameOperationChanged)

        self._nameFilterValueLineEdit = gui.LineEditEx()
        self._nameFilterValueLineEdit.enableRegexChecking(
            enabled=self._nameFilterOperationCombo.currentEnum() == logic.StringFilterOperation.MatchRegex)
        self._nameFilterValueLineEdit.textChanged.connect(self._nameValueTextChanged)

        layout = gui.FormLayoutEx()
        layout.addRow('Type:', self._nameFilterTypeCombo)
        layout.addRow('Operation:', self._nameFilterOperationCombo)
        layout.addRow('Value:', self._nameFilterValueLineEdit)

        self._addLayoutToStack(
            filterType=_FilterType.NameFilter,
            layout=layout)

    def _setupTagLevelFilterLayout(self) -> None:
        self._tagLevelFilterOperationComboBox = gui.EnumComboBox(
            type=logic.ComparisonFilterOperation,
            textMap=_ComparisonFilterOperationTextMap)

        self._tagLevelFilterValueComboBox = gui.TagLevelComboBox()

        layout = gui.FormLayoutEx()
        layout.addRow('Operation:', self._tagLevelFilterOperationComboBox)
        layout.addRow('Value:', self._tagLevelFilterValueComboBox)

        self._addLayoutToStack(
            filterType=_FilterType.TagLevelFilter,
            layout=layout)

    def _setupZoneFilterLayout(self) -> None:
        self._zoneFilterOperationComboBox = gui.EnumComboBox(
            type=logic.ComparisonFilterOperation,
            textMap=_ComparisonFilterOperationTextMap)

        self._zoneFilterValueComboBox = gui.EnumComboBox(
            type=traveller.ZoneType,
            textMap=traveller.zoneTypeNameMap())

        layout = gui.FormLayoutEx()
        layout.addRow('Operation:', self._zoneFilterOperationComboBox)
        layout.addRow('Value:', self._zoneFilterValueComboBox)

        self._addLayoutToStack(
            filterType=_FilterType.ZoneFilter,
            layout=layout)

    def _setupUWPFilterLayout(self) -> None:
        self._uwpFilterElementComboBox = gui.EnumComboBox(
            type=traveller.UWP.Element,
            textMap=_UWPElementTextMap)
        self._uwpFilterElementComboBox.currentIndexChanged.connect(self._uwpElementChanged)

        self._uwpFilterOperationComboBox = gui.EnumComboBox(
            type=logic.ComparisonFilterOperation,
            textMap=_ComparisonFilterOperationTextMap)

        self._uwpFilterValueComboBox = _UWPCodeComboBox()
        self._uwpFilterValueComboBox.setElement(self._uwpFilterElementComboBox.currentEnum())

        layout = gui.FormLayoutEx()
        layout.addRow('Element:', self._uwpFilterElementComboBox)
        layout.addRow('Operation:', self._uwpFilterOperationComboBox)
        layout.addRow('Value:', self._uwpFilterValueComboBox)

        self._addLayoutToStack(
            filterType=_FilterType.UWPFilter,
            layout=layout)

    def _setupEconomicsFilterLayout(self) -> None:
        self._economicsFilterElementComboBox = gui.EnumComboBox(
            type=traveller.Economics.Element,
            textMap=_EconomicsElementTextMap)
        self._economicsFilterElementComboBox.currentIndexChanged.connect(self._economicsElementChanged)

        self._economicsFilterOperationComboBox = gui.EnumComboBox(
            type=logic.ComparisonFilterOperation,
            textMap=_ComparisonFilterOperationTextMap)

        self._economicsFilterValueComboBox = _EconomicsCodeComboBox()
        self._economicsFilterValueComboBox.setElement(self._economicsFilterElementComboBox.currentEnum())

        layout = gui.FormLayoutEx()
        layout.addRow('Element:', self._economicsFilterElementComboBox)
        layout.addRow('Operation:', self._economicsFilterOperationComboBox)
        layout.addRow('Value:', self._economicsFilterValueComboBox)

        self._addLayoutToStack(
            filterType=_FilterType.EconomicsFilter,
            layout=layout)

    def _setupCultureFilterLayout(self) -> None:
        self._cultureFilterElementComboBox = gui.EnumComboBox(
            type=traveller.Culture.Element,
            textMap=_CultureElementTextMap)
        self._cultureFilterElementComboBox.currentIndexChanged.connect(self._cultureElementChanged)

        self._cultureFilterOperationComboBox = gui.EnumComboBox(
            type=logic.ComparisonFilterOperation,
            textMap=_ComparisonFilterOperationTextMap)

        self._cultureFilterValueComboBox = _CultureCodeComboBox()
        self._cultureFilterValueComboBox.setElement(self._cultureFilterElementComboBox.currentEnum())

        layout = gui.FormLayoutEx()
        layout.addRow('Element:', self._cultureFilterElementComboBox)
        layout.addRow('Operation:', self._cultureFilterOperationComboBox)
        layout.addRow('Value:', self._cultureFilterValueComboBox)

        self._addLayoutToStack(
            filterType=_FilterType.CultureFilter,
            layout=layout)

    def _setupRefuellingFilerLayout(self) -> None:
        self._refuellingFilterOperationComboBox = gui.EnumComboBox(
            type=logic.ListFilterOperation,
            textMap=_ListFilterOperationTextMap)

        self._refuellingFilterValuesList = _EnumOptionWidget(
            type=logic.RefuellingFilter.Type,
            columnCount=2,
            textMap=_RefuellingFilterTypeTextMap)

        layout = gui.FormLayoutEx()
        layout.addRow('Operation:', self._refuellingFilterOperationComboBox)
        layout.addRow('Value:', self._refuellingFilterValuesList)

        self._addLayoutToStack(
            filterType=_FilterType.RefuellingFilter,
            layout=layout)

    def _setupAllegianceFilerLayout(self) -> None:
        self._allegianceFilterOperationCombo = gui.EnumComboBox(
            type=logic.StringFilterOperation,
            textMap=_StringFilterOperationTextMap)
        self._allegianceFilterOperationCombo.currentIndexChanged.connect(self._allegianceOperationChanged)

        self._allegianceFilterValueLineEdit = gui.LineEditEx()
        self._allegianceFilterValueLineEdit.enableRegexChecking(
            enabled=self._allegianceFilterOperationCombo.currentEnum() == logic.StringFilterOperation.MatchRegex)
        self._allegianceFilterValueLineEdit.textChanged.connect(self._allegianceValueTextChanged)

        layout = gui.FormLayoutEx()
        layout.addRow('Operation:', self._allegianceFilterOperationCombo)
        layout.addRow('Value:', self._allegianceFilterValueLineEdit)

        self._addLayoutToStack(
            filterType=_FilterType.AllegianceFilter,
            layout=layout)

    def _setupSophontFilterLayout(self) -> None:
        self._sophontFilterOperationCombo = gui.EnumComboBox(
            type=logic.StringFilterOperation,
            textMap=_StringFilterOperationTextMap)
        self._sophontFilterOperationCombo.currentIndexChanged.connect(self._sophontOperationChanged)

        self._sophontFilterValueLineEdit = gui.LineEditEx()
        self._sophontFilterValueLineEdit.enableRegexChecking(
            enabled=self._sophontFilterOperationCombo.currentEnum() == logic.StringFilterOperation.MatchRegex)
        self._sophontFilterValueLineEdit.textChanged.connect(self._sophontValueTextChanged)

        layout = gui.FormLayoutEx()
        layout.addRow('Operation:', self._sophontFilterOperationCombo)
        layout.addRow('Value:', self._sophontFilterValueLineEdit)

        self._addLayoutToStack(
            filterType=_FilterType.SophontFilter,
            layout=layout)

    def _setupBaseFilterLayout(self) -> None:
        self._basesFilterOperationComboBox = gui.EnumComboBox(
            type=logic.ListFilterOperation,
            textMap=_ListFilterOperationTextMap)

        self._basesFilterValuesList = _EnumOptionWidget(
            type=traveller.BaseType,
            columnCount=2,
            textMap=traveller.Bases.descriptionMap(),
            sortAlphabetically=True)

        layout = gui.FormLayoutEx()
        layout.addRow('Operation:', self._basesFilterOperationComboBox)
        layout.addRow('Value:', self._basesFilterValuesList)

        self._addLayoutToStack(
            filterType=_FilterType.BaseFilter,
            layout=layout)

    def _setupNobilityFilterLayout(self) -> None:
        self._nobilityFilterOperationComboBox = gui.EnumComboBox(
            type=logic.ListFilterOperation,
            textMap=_ListFilterOperationTextMap)

        self._nobilityFilterValuesList = _EnumOptionWidget(
            type=traveller.NobilityType,
            columnCount=3,
            textMap=traveller.Nobilities.descriptionMap(),
            sortAlphabetically=False) # Show nobility in priority order rather than alphabetic

        layout = gui.FormLayoutEx()
        layout.addRow('Operation:', self._nobilityFilterOperationComboBox)
        layout.addRow('Value:', self._nobilityFilterValuesList)

        self._addLayoutToStack(
            filterType=_FilterType.NobilityFilter,
            layout=layout)

    def _setupRemarksFilterLayout(self) -> None:
        self._remarksFilterOperationCombo = gui.EnumComboBox(
            type=logic.StringFilterOperation,
            textMap=_StringFilterOperationTextMap)
        self._remarksFilterOperationCombo.currentIndexChanged.connect(self._remarksOperationChanged)

        self._remarksFilterValueLineEdit = gui.LineEditEx()
        self._remarksFilterValueLineEdit.enableRegexChecking(
            enabled=self._remarksFilterOperationCombo.currentEnum() == logic.StringFilterOperation.MatchRegex)
        self._remarksFilterValueLineEdit.textChanged.connect(self._remarksValueTextChanged)

        layout = gui.FormLayoutEx()
        layout.addRow('Operation:', self._remarksFilterOperationCombo)
        layout.addRow('Value:', self._remarksFilterValueLineEdit)

        self._addLayoutToStack(
            filterType=_FilterType.RemarksFilter,
            layout=layout)

    def _setupTradeCodeFilterLayout(self) -> None:
        self._tradeCodeFilterOperationComboBox = gui.EnumComboBox(
            type=logic.ListFilterOperation,
            textMap=_ListFilterOperationTextMap)

        self._tradeCodeFilterValuesList = _EnumOptionWidget(
            type=traveller.TradeCode,
            columnCount=3,
            textMap=traveller.tradeCodeNameMap(),
            sortAlphabetically=True)

        layout = gui.FormLayoutEx()
        layout.addRow('Operation:', self._tradeCodeFilterOperationComboBox)
        layout.addRow('Value:', self._tradeCodeFilterValuesList)

        self._addLayoutToStack(
            filterType=_FilterType.TradeCodeFilter,
            layout=layout)

    def _setupPBGFilterLayout(self) -> None:
        self._pbgFilterElementComboBox = gui.EnumComboBox(
            type=traveller.PBG.Element,
            textMap=_PBGElementTextMap)
        self._pbgFilterElementComboBox.currentIndexChanged.connect(self._pbgElementChanged)

        self._pbgFilterOperationComboBox = gui.EnumComboBox(
            type=logic.ComparisonFilterOperation,
            textMap=_ComparisonFilterOperationTextMap)

        self._pbgFilterValueComboBox = _PBGCodeComboBox()
        self._pbgFilterValueComboBox.setElement(self._pbgFilterElementComboBox.currentEnum())

        layout = gui.FormLayoutEx()
        layout.addRow('Element:', self._pbgFilterElementComboBox)
        layout.addRow('Operation:', self._pbgFilterOperationComboBox)
        layout.addRow('Value:', self._pbgFilterValueComboBox)

        self._addLayoutToStack(
            filterType=_FilterType.PBGFilter,
            layout=layout)

    def _setupButtonLayout(self) -> None:
        self._okButton = QtWidgets.QPushButton('OK')
        self._okButton.setDefault(True)
        self._okButton.clicked.connect(self.accept)

        self._cancelButton = QtWidgets.QPushButton('Cancel')
        self._cancelButton.clicked.connect(self.reject)

        self._buttonLayout = QtWidgets.QHBoxLayout()
        self._buttonLayout.setContentsMargins(0, 0, 0, 0)
        self._buttonLayout.addStretch()
        self._buttonLayout.addWidget(self._okButton)
        self._buttonLayout.addWidget(self._cancelButton)

    def _addLayoutToStack(
            self,
            filterType: _FilterType,
            layout: QtWidgets.QLayout
            ) -> None:
        layout.setContentsMargins(0, 0, 0, 0)

        widget = QtWidgets.QWidget()
        widget.setLayout(layout)

        self._stack.addWidget(widget)
        self._stackMap[filterType] = widget

    # Once the layouts have all been created iterate over the labels for all form layouts to get the
    # max label width, then set all labels to have that fixed width. This is done so that the labels
    # on the main form layout and the form layouts used on the stacked panes align
    def _syncLayouts(self) -> None:
        formLabels = self._formLabels()

        maxWidth = 0
        for widget in formLabels:
            maxWidth = max(maxWidth, widget.sizeHint().width())

        for widget in formLabels:
            widget.setFixedWidth(maxWidth)

    def _formLabels(self) -> typing.Iterable[QtWidgets.QWidget]:
        widgets = []

        layout = self.layout()
        assert(isinstance(layout, gui.FormLayoutEx))
        for row in range(layout.rowCount()):
            label = layout.itemAt(row, QtWidgets.QFormLayout.ItemRole.LabelRole)
            if label:
                widget = label.widget()
                if widget:
                    widgets.append(widget)

        for index in range(self._stack.count()):
            widget = self._stack.widget(index)
            layout = widget.layout()
            assert(isinstance(layout, gui.FormLayoutEx))
            for row in range(layout.rowCount()):
                label = layout.itemAt(row, QtWidgets.QFormLayout.ItemRole.LabelRole)
                if label:
                    widget = label.widget()
                    if widget:
                        widgets.append(widget)

        return widgets

    def _filterTypeChanged(self) -> None:
        currentFilter = self._filterTypeComboBox.currentEnum()
        filterWidget = self._stackMap.get(currentFilter)
        if filterWidget:
            self._stack.setCurrentWidget(filterWidget)
            self._checkValidity()

    def _nameOperationChanged(self) -> None:
        self._nameFilterValueLineEdit.enableRegexChecking(
            enabled=self._nameFilterOperationCombo.currentEnum() == logic.StringFilterOperation.MatchRegex)
        self._checkValidity()

    def _nameValueTextChanged(self, text: str) -> None:
        self._checkValidity()

    def _uwpElementChanged(self) -> None:
        self._uwpFilterValueComboBox.setElement(self._uwpFilterElementComboBox.currentEnum())

    def _economicsElementChanged(self) -> None:
        self._economicsFilterValueComboBox.setElement(self._economicsFilterElementComboBox.currentEnum())

    def _cultureElementChanged(self) -> None:
        self._cultureFilterValueComboBox.setElement(self._cultureFilterElementComboBox.currentEnum())

    def _allegianceOperationChanged(self) -> None:
        self._allegianceFilterValueLineEdit.enableRegexChecking(
            enabled=self._allegianceFilterOperationCombo.currentEnum() == logic.StringFilterOperation.MatchRegex)
        self._checkValidity()

    def _allegianceValueTextChanged(self, text: str) -> None:
        self._checkValidity()

    def _sophontOperationChanged(self) -> None:
        self._sophontFilterValueLineEdit.enableRegexChecking(
            enabled=self._sophontFilterOperationCombo.currentEnum() == logic.StringFilterOperation.MatchRegex)
        self._checkValidity()

    def _sophontValueTextChanged(self, text: str) -> None:
        self._checkValidity()

    def _pbgElementChanged(self) -> None:
        self._pbgFilterValueComboBox.setElement(self._pbgFilterElementComboBox.currentEnum())

    def _remarksOperationChanged(self) -> None:
        self._remarksFilterValueLineEdit.enableRegexChecking(
            enabled=self._remarksFilterOperationCombo.currentEnum() == logic.StringFilterOperation.MatchRegex)
        self._checkValidity()

    def _remarksValueTextChanged(self, text: str) -> None:
        self._checkValidity()

    def _checkValidity(self):
        isValid = False

        currentFilter = self._filterTypeComboBox.currentEnum()
        if currentFilter == _FilterType.NameFilter:
            isValid = not self._nameFilterValueLineEdit.isEmpty()
            if isValid and self._nameFilterValueLineEdit.isRegexCheckingEnabled():
                isValid = self._nameFilterValueLineEdit.isValidRegex()
        elif currentFilter == _FilterType.TagLevelFilter:
            isValid = True
        elif currentFilter == _FilterType.ZoneFilter:
            isValid = True
        elif currentFilter == _FilterType.UWPFilter:
            isValid = True
        elif currentFilter == _FilterType.EconomicsFilter:
            isValid = True
        elif currentFilter == _FilterType.CultureFilter:
            isValid = True
        elif currentFilter == _FilterType.RefuellingFilter:
            isValid = True
        elif currentFilter == _FilterType.AllegianceFilter:
            isValid = not self._allegianceFilterValueLineEdit.isEmpty()
            if isValid and self._allegianceFilterValueLineEdit.isRegexCheckingEnabled():
                isValid = self._allegianceFilterValueLineEdit.isValidRegex()
        elif currentFilter == _FilterType.SophontFilter:
            isValid = not self._sophontFilterValueLineEdit.isEmpty()
            if isValid and self._sophontFilterValueLineEdit.isRegexCheckingEnabled():
                isValid = self._sophontFilterValueLineEdit.isValidRegex()
        elif currentFilter == _FilterType.BaseFilter:
            isValid = True
        elif currentFilter == _FilterType.NobilityFilter:
            isValid = True
        elif currentFilter == _FilterType.RemarksFilter:
            isValid = not self._remarksFilterValueLineEdit.isEmpty()
            if isValid and self._remarksFilterValueLineEdit.isRegexCheckingEnabled():
                isValid = self._remarksFilterValueLineEdit.isValidRegex()
        elif currentFilter == _FilterType.TradeCodeFilter:
            isValid = True
        elif currentFilter == _FilterType.PBGFilter:
            isValid = True
        else:
            isValid = False

        self._okButton.setEnabled(isValid)
