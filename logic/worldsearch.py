import app
import enum
import re
import traveller
import travellermap
import typing

class ComparisonFilterOperation(enum.Enum):
    Equal = 0
    NotEqual = 1
    Greater = 2
    GreaterOrEqual = 3
    Less = 4
    LessOrEqual = 5

class ListFilterOperation(enum.Enum):
    ContainsAny = 0
    ContainsAll = 1
    ContainsOnly = 2

class StringFilterOperation(enum.Enum):
    ContainsString = 0
    MatchRegex = 1

class FilterLogic(enum.Enum):
    MatchesAny = 0
    MatchesAll = 1
    MatchesNone = 2


# these string mappings are all lower case as they're used to generate natural language
# descriptions of the search
_ComparisonFilterOperationDescriptionMap = {
    ComparisonFilterOperation.Equal: 'is equal to',
    ComparisonFilterOperation.NotEqual: 'is not equal to',
    ComparisonFilterOperation.Greater: 'is greater than',
    ComparisonFilterOperation.GreaterOrEqual: 'is greater than or equal to',
    ComparisonFilterOperation.Less: 'is less than',
    ComparisonFilterOperation.LessOrEqual: 'is less than or equal to'
}

_ListFilterSingleOperationDescriptionMap = {
    ListFilterOperation.ContainsAny: 'contains',
    ListFilterOperation.ContainsAll: 'contains',
    ListFilterOperation.ContainsOnly: 'contains only'
}

_ListFilterMultiOperationDescriptionMap = {
    ListFilterOperation.ContainsAny: 'contains any of',
    ListFilterOperation.ContainsAll: 'contains all of',
    ListFilterOperation.ContainsOnly: 'contains only'
}

_StringFilterOperationDescriptionMap = {
    StringFilterOperation.ContainsString: 'contains the string',
    StringFilterOperation.MatchRegex: 'matches the expression'
}

def _performComparisonOperation(
        operation: ComparisonFilterOperation,
        worldValue: typing.Optional[int],
        compareValue: typing.Optional[int]
        ) -> bool:
    if operation == ComparisonFilterOperation.Equal:
        return worldValue == compareValue
    elif operation == ComparisonFilterOperation.NotEqual:
        return worldValue != compareValue
    elif operation == ComparisonFilterOperation.Greater:
        if worldValue != None and compareValue != None:
            return worldValue > compareValue
        return False
    elif operation == ComparisonFilterOperation.GreaterOrEqual:
        if worldValue != None and compareValue != None:
            return worldValue >= compareValue
        return worldValue == compareValue
    elif operation == ComparisonFilterOperation.Less:
        if worldValue != None and compareValue != None:
            return worldValue < compareValue
        return False
    elif operation == ComparisonFilterOperation.LessOrEqual:
        if worldValue != None and compareValue != None:
            return worldValue <= compareValue
        return worldValue == compareValue
    raise TypeError('Invalid comparison operation')

class WorldFilter(object):
    def description(self) -> str:
        raise RuntimeError('The description method should be implemented by the derived class')

    def match(self, world: traveller.World) -> bool:
        raise RuntimeError('The match method should be implemented by the derived class')

class NameFiler(WorldFilter):
    class Type(enum.Enum):
        WorldName = 0
        SectorName = 1
        SubsectorName = 2

    def __init__(
            self,
            type: Type,
            operation: StringFilterOperation,
            value: str
            ) -> None:
        super().__init__()
        self._type = type
        self._operation = operation
        self._value = value

        self._regex = re.compile(self._value, re.IGNORECASE)

    def type(self) -> Type:
        return self._type

    def operation(self) -> StringFilterOperation:
        return self._operation

    def value(self) -> str:
        return self._value

    def description(self) -> str:
        typeString = None
        if self._type == NameFiler.Type.WorldName:
            typeString = 'World Name'
        elif self._type == NameFiler.Type.SectorName:
            typeString = 'Sector Name'
        elif self._type == NameFiler.Type.SubsectorName:
            typeString = 'Subsector Name'
        else:
            return None

        operationString = _StringFilterOperationDescriptionMap[self._operation]
        if not operationString:
            return None

        return f'{typeString} {operationString} "{self._value}"'

    def match(self, world: traveller.World) -> bool:
        if self._operation == StringFilterOperation.ContainsString:
            if self._type == NameFiler.Type.WorldName:
                return self._regex.search(world.name()) != None
            elif self._type == NameFiler.Type.SectorName:
                return self._regex.search(world.sectorName()) != None
            elif self._type == NameFiler.Type.SubsectorName:
                return self._regex.search(world.subsectorName()) != None
            raise ValueError('Invalid name filter type')
        elif self._operation == StringFilterOperation.MatchRegex:
            if self._type == NameFiler.Type.WorldName:
                return self._regex.match(world.name()) != None
            elif self._type == NameFiler.Type.SectorName:
                return self._regex.match(world.sectorName()) != None
            elif self._type == NameFiler.Type.SubsectorName:
                return self._regex.match(world.subsectorName()) != None
            raise ValueError('Invalid name filter type')
        raise ValueError('Invalid name filter operation')

    @staticmethod
    def _tagLevelToInt(level: str) -> int:
        if level == app.TagLevel.Danger:
            return 2
        elif level == app.TagLevel.Warning:
            return 1
        return 0

class TagLevelFiler(WorldFilter):
    def __init__(
            self,
            operation: ComparisonFilterOperation,
            value: app.TagLevel
            ) -> None:
        super().__init__()
        self._operation = operation
        self._value = value
        self._integer = TagLevelFiler._tagLevelToInt(self._value)

    def operation(self) -> ComparisonFilterOperation:
        return self._operation

    def value(self) -> app.TagLevel:
        return self._value

    def description(self) -> str:
        operationString = _ComparisonFilterOperationDescriptionMap[self._operation]
        if not operationString:
            return None

        return f'Tag Level {operationString} {self._value.name}'

    def match(self, world: traveller.World) -> bool:
        return _performComparisonOperation(
            operation=self._operation,
            worldValue=TagLevelFiler._tagLevelToInt(app.calculateWorldTagLevel(world)),
            compareValue=self._integer)

    @staticmethod
    def _tagLevelToInt(level: str) -> int:
        if level == app.TagLevel.Danger:
            return 2
        elif level == app.TagLevel.Warning:
            return 1
        return 0

class ZoneFiler(WorldFilter):
    def __init__(
            self,
            operation: ComparisonFilterOperation,
            value: traveller.ZoneType
            ) -> None:
        super().__init__()
        self._operation = operation
        self._value = value
        self._integer = ZoneFiler._zoneToInt(self._value)

    def operation(self) -> ComparisonFilterOperation:
        return self._operation

    def value(self) -> traveller.ZoneType:
        return self._value

    def description(self) -> str:
        operationString = _ComparisonFilterOperationDescriptionMap[self._operation]
        if not operationString:
            return None

        return f'Zone {operationString} {traveller.zoneTypeName(self._value)}'

    def match(self, world: traveller.World) -> bool:
        return _performComparisonOperation(
            operation=self._operation,
            worldValue=ZoneFiler._zoneToInt(world.zone()),
            compareValue=self._integer)

    @staticmethod
    def _zoneToInt(zone: traveller.ZoneType) -> int:
        if zone == traveller.ZoneType.RedZone:
            return 2
        elif zone == traveller.ZoneType.AmberZone:
            return 1
        else:
            return 0

class UWPFilter(WorldFilter):
    def __init__(
            self,
            element: traveller.UWP.Element,
            operation: ComparisonFilterOperation,
            value: str
            ) -> None:
        super().__init__()
        self._element = element
        self._operation = operation
        self._value = value
        self._integer = traveller.ehexToInteger(value=self._value, default=None)

    def element(self) -> traveller.UWP.Element:
        return self._element

    def operation(self) -> ComparisonFilterOperation:
        return self._operation

    def value(self) -> str:
        return self._value

    def description(self) -> str:
        if self._element == traveller.UWP.Element.StarPort:
            elementString = 'Star Port'
        elif self._element == traveller.UWP.Element.WorldSize:
            elementString = 'World size'
        elif self._element == traveller.UWP.Element.Atmosphere:
            elementString = 'Atmosphere'
        elif self._element == traveller.UWP.Element.Hydrographics:
            elementString = 'Hydrographics'
        elif self._element == traveller.UWP.Element.Population:
            elementString = 'Population'
        elif self._element == traveller.UWP.Element.Government:
            elementString = 'Government'
        elif self._element == traveller.UWP.Element.LawLevel:
            elementString = 'Law Level'
        elif self._element == traveller.UWP.Element.TechLevel:
            elementString = 'Tech Level'
        else:
            return None

        operationString = _ComparisonFilterOperationDescriptionMap[self._operation]
        if not operationString:
            return None

        return f'{elementString} {operationString} {self._value}'

    def match(self, world: traveller.World) -> bool:
        return _performComparisonOperation(
            operation=self._operation,
            worldValue=traveller.ehexToInteger(
                value=world.uwp().code(self._element),
                default=None),
            compareValue=self._integer)

class EconomicsFilter(WorldFilter):
    def __init__(
            self,
            element: traveller.Economics.Element,
            operation: ComparisonFilterOperation,
            value: str
            ) -> None:
        super().__init__()
        self._element = element
        self._operation = operation
        self._value = value

        if self._element == traveller.Economics.Element.Efficiency:
            self._integer = int(self._value) if self._value != '?' else None
        else:
            self._integer = traveller.ehexToInteger(value=self._value, default=None)

    def element(self) -> traveller.Economics.Element:
        return self._element

    def operation(self) -> ComparisonFilterOperation:
        return self._operation

    def value(self) -> str:
        return self._value

    def description(self) -> str:
        if self._element == traveller.Economics.Element.Resources:
            elementString = 'Resources'
        elif self._element == traveller.Economics.Element.Labour:
            elementString = 'Labour'
        elif self._element == traveller.Economics.Element.Infrastructure:
            elementString = 'Infrastructure'
        elif self._element == traveller.Economics.Element.Efficiency:
            elementString = 'Efficiency'
        else:
            return None

        operationString = _ComparisonFilterOperationDescriptionMap.get(self._operation)
        if not operationString:
            return None

        return f'{elementString} {operationString} {self._value}'

    def match(self, world: traveller.World) -> bool:
        code = world.economics().code(self._element)
        if self._element == traveller.Economics.Element.Efficiency:
            worldValue = int(code) if code != '?' else None
        else:
            worldValue = traveller.ehexToInteger(
                value=code,
                default=None)

        return _performComparisonOperation(
            operation=self._operation,
            worldValue=worldValue,
            compareValue=self._integer)

class CultureFilter(WorldFilter):
    def __init__(
            self,
            element: traveller.Culture.Element,
            operation: ComparisonFilterOperation,
            value: str
            ) -> None:
        super().__init__()
        self._element = element
        self._operation = operation
        self._value = value
        self._integer = traveller.ehexToInteger(value=self._value, default=None)

    def element(self) -> traveller.Culture.Element:
        return self._element

    def operation(self) -> ComparisonFilterOperation:
        return self._operation

    def value(self) -> str:
        return self._value

    def description(self) -> str:
        if self._element == traveller.Culture.Element.Heterogeneity:
            elementString = 'Heterogeneity'
        elif self._element == traveller.Culture.Element.Acceptance:
            elementString = 'Acceptance'
        elif self._element == traveller.Culture.Element.Strangeness:
            elementString = 'Strangeness'
        elif self._element == traveller.Culture.Element.Symbols:
            elementString = 'Symbols'
        else:
            return None

        operationString = _ComparisonFilterOperationDescriptionMap.get(self._operation)
        if not operationString:
            return None

        return f'{elementString} {operationString} {self._value}'

    def match(self, world: traveller.World) -> bool:
        return _performComparisonOperation(
            operation=self._operation,
            worldValue=traveller.ehexToInteger(
                value=world.culture().code(self._element),
                default=None),
            compareValue=self._integer)

class RefuellingFilter(WorldFilter):
    class Type(enum.Enum):
        RefinedRefuelling = 0
        UnrefinedRefuelling = 1
        GasGiantRefuelling = 2
        WaterRefuelling = 3
        FuelCacheRefuelling = 4
        AnomalyRefuelling = 5

    def __init__(
            self,
            operation: ListFilterOperation,
            value: typing.Iterable[Type],
            rules: traveller.Rules
            ) -> None:
        super().__init__()
        self._operation = operation
        self._value = set(value)
        self._rules = rules

    def operation(self) -> ListFilterOperation:
        return self._operation

    def value(self) -> typing.Iterable[Type]:
        return self._value

    def description(self) -> str:
        if len(self._value) == 1:
            operationString = _ListFilterSingleOperationDescriptionMap.get(self._operation)
        else:
            operationString = _ListFilterMultiOperationDescriptionMap.get(self._operation)
        if not operationString:
            return None

        listString = ''
        for index, type in enumerate(self._value):
            if type == RefuellingFilter.Type.RefinedRefuelling:
                typeString = 'Refined Fuel'
            elif type == RefuellingFilter.Type.UnrefinedRefuelling:
                typeString = 'Unrefined Fuel'
            elif type == RefuellingFilter.Type.GasGiantRefuelling:
                typeString = 'Gas Giant Refuelling'
            elif type == RefuellingFilter.Type.WaterRefuelling:
                typeString = 'Water Refuelling'
            elif type == RefuellingFilter.Type.FuelCacheRefuelling:
                typeString = 'Fuel Cache'
            elif type == RefuellingFilter.Type.AnomalyRefuelling:
                typeString = 'Anomaly'
            else:
                return None

            if index == 0:
                listString = typeString
            elif index == len(self._value) - 1:
                if self._operation == ListFilterOperation.ContainsAny:
                    listString += f' or {typeString}'
                else:
                    listString += f' and {typeString}'
            else:
                listString += f', {typeString}'
        return f'Refuelling options {operationString} {listString}'

    def match(self, world: traveller.World) -> bool:
        checkList = RefuellingFilter.Type if self._operation == ListFilterOperation.ContainsOnly else self._value
        for refuelling in checkList:
            match = False
            if refuelling == RefuellingFilter.Type.RefinedRefuelling:
                match = world.hasStarPortRefuelling(
                    includeUnrefined=False,
                    rules=self._rules)
            elif refuelling == RefuellingFilter.Type.UnrefinedRefuelling:
                match = world.hasStarPortRefuelling(
                    includeRefined=False,
                    rules=self._rules)
            elif refuelling == RefuellingFilter.Type.GasGiantRefuelling:
                match = world.hasGasGiantRefuelling()
            elif refuelling == RefuellingFilter.Type.WaterRefuelling:
                match = world.hasWaterRefuelling()
            elif refuelling == RefuellingFilter.Type.FuelCacheRefuelling:
                match = world.isFuelCache()
            elif refuelling == RefuellingFilter.Type.AnomalyRefuelling:
                match = world.isAnomaly()
            else:
                raise ValueError('Invalid refuelling filter type')

            if self._operation == ListFilterOperation.ContainsAny:
                if match:
                    return True
            elif self._operation == ListFilterOperation.ContainsAll:
                if not match:
                    return False
            elif self._operation == ListFilterOperation.ContainsOnly:
                allowed = refuelling in self._value
                if match != allowed:
                    return False
            else:
                raise ValueError('Invalid refuelling filter operation')

        return self._operation != ListFilterOperation.ContainsAny

class AllegianceFilter(WorldFilter):
    def __init__(
            self,
            operation: StringFilterOperation,
            value: str
            ) -> None:
        super().__init__()
        self._operation = operation
        self._value = value
        self._regex = re.compile(self._value, re.IGNORECASE)

    def operation(self) -> StringFilterOperation:
        return self._operation

    def value(self) -> str:
        return self._value

    def description(self) -> str:
        operationString = _StringFilterOperationDescriptionMap.get(self._operation)
        if not operationString:
            return None

        return f'Allegiance {operationString} "{self._value}"'

    def match(self, world: traveller.World) -> bool:
        allegianceCode = world.allegiance()
        if allegianceCode:
            if self._operation == StringFilterOperation.ContainsString:
                if self._regex.search(allegianceCode):
                    return True
            elif self._operation == StringFilterOperation.MatchRegex:
                if self._regex.match(allegianceCode):
                    return True
            else:
                raise ValueError('Invalid allegiance filter operation')

            allegianceName = traveller.AllegianceManager.instance().allegianceName(world)
            if allegianceName:
                if self._operation == StringFilterOperation.ContainsString:
                    if self._regex.search(allegianceName):
                        return True
                elif self._operation == StringFilterOperation.MatchRegex:
                    if self._regex.match(allegianceName):
                        return True
                else:
                    raise ValueError('Invalid allegiance filter operation')
        return False

class SophontFilter(WorldFilter):
    def __init__(
            self,
            operation: StringFilterOperation,
            value: str
            ) -> None:
        super().__init__()
        self._operation = operation
        self._value = value
        self._regex = re.compile(self._value, re.IGNORECASE)

    def operation(self) -> StringFilterOperation:
        return self._operation

    def value(self) -> str:
        return self._value

    def description(self) -> str:
        operationString = _StringFilterOperationDescriptionMap.get(self._operation)
        if not operationString:
            return None

        return f'Sophont {operationString} "{self._value}"'

    def match(self, world: traveller.World) -> bool:
        remarks = world.remarks()
        if remarks:
            sophonts = remarks.sophonts()
            if self._operation == StringFilterOperation.ContainsString:
                for sophont in sophonts:
                    if self._regex.search(sophont):
                        return True
            elif self._operation == StringFilterOperation.MatchRegex:
                for sophont in sophonts:
                    if self._regex.match(sophont):
                        return True
            else:
                raise ValueError('Invalid sophont filter operation')
        return False

class BaseFilter(WorldFilter):
    def __init__(
            self,
            operation: ListFilterOperation,
            value: typing.Iterable[traveller.BaseType]
            ) -> None:
        super().__init__()
        self._operation = operation
        self._value = set(value)

    def operation(self) -> ListFilterOperation:
        return self._operation

    def value(self) -> typing.Iterable[traveller.BaseType]:
        return self._value

    def description(self) -> str:
        if len(self._value) == 1:
            operationString = _ListFilterSingleOperationDescriptionMap.get(self._operation)
        else:
            operationString = _ListFilterMultiOperationDescriptionMap.get(self._operation)
        if not operationString:
            return None

        listString = ''
        for index, base in enumerate(self._value):
            typeString = traveller.Bases.description(baseType=base)

            if index == 0:
                listString = typeString
            elif index == len(self._value) - 1:
                if self._operation == ListFilterOperation.ContainsAny:
                    listString += f' or {typeString}'
                else:
                    listString += f' and {typeString}'
            else:
                listString += f', {typeString}'
        return f'Bases {operationString} {listString}'

    def match(self, world: traveller.World) -> bool:
        checkList = traveller.BaseType if self._operation == ListFilterOperation.ContainsOnly else self._value
        worldBases = world.bases()
        for base in checkList:
            match = base in worldBases
            if self._operation == ListFilterOperation.ContainsAny:
                if match:
                    return True
            elif self._operation == ListFilterOperation.ContainsAll:
                if not match:
                    return False
            elif self._operation == ListFilterOperation.ContainsOnly:
                allowed = base in self._value
                if match != allowed:
                    return False
            else:
                raise ValueError('Invalid base filter operation')

        return self._operation != ListFilterOperation.ContainsAny

class NobilityFilter(WorldFilter):
    def __init__(
            self,
            operation: ListFilterOperation,
            value: typing.Iterable[traveller.NobilityType]
            ) -> None:
        super().__init__()
        self._operation = operation
        self._value = set(value)

    def operation(self) -> ListFilterOperation:
        return self._operation

    def value(self) -> typing.Iterable[traveller.NobilityType]:
        return self._value

    def description(self) -> str:
        if len(self._value) == 1:
            operationString = _ListFilterSingleOperationDescriptionMap.get(self._operation)
        else:
            operationString = _ListFilterMultiOperationDescriptionMap.get(self._operation)
        if not operationString:
            return None

        listString = ''
        for index, nobility in enumerate(self._value):
            typeString = traveller.Nobilities.description(nobilityType=nobility)

            if index == 0:
                listString = typeString
            elif index == len(self._value) - 1:
                if self._operation == ListFilterOperation.ContainsAny:
                    listString += f' or {typeString}'
                else:
                    listString += f' and {typeString}'
            else:
                listString += f', {typeString}'
        return f'Nobilities {operationString} {listString}'

    def match(self, world: traveller.World) -> bool:
        checkList = traveller.NobilityType if self._operation == ListFilterOperation.ContainsOnly else self._value
        worldNobilities = world.nobilities()
        for nobility in checkList:
            match = nobility in worldNobilities
            if self._operation == ListFilterOperation.ContainsAny:
                if match:
                    return True
            elif self._operation == ListFilterOperation.ContainsAll:
                if not match:
                    return False
            elif self._operation == ListFilterOperation.ContainsOnly:
                allowed = nobility in self._value
                if match != allowed:
                    return False
            else:
                raise ValueError('Invalid nobility filter operation')

        return self._operation != ListFilterOperation.ContainsAny

class RemarksFilter(WorldFilter):
    def __init__(
            self,
            operation: StringFilterOperation,
            value: str
            ) -> None:
        super().__init__()
        self._operation = operation
        self._value = value
        self._regex = re.compile(self._value, re.IGNORECASE)

    def operation(self) -> StringFilterOperation:
        return self._operation

    def value(self) -> str:
        return self._value

    def description(self) -> str:
        operationString = _StringFilterOperationDescriptionMap.get(self._operation)
        if not operationString:
            return None

        return f'Remarks {operationString} "{self._value}"'

    def match(self, world: traveller.World) -> bool:
        remarks = world.remarks()
        if remarks:
            if self._operation == StringFilterOperation.ContainsString:
                if self._regex.search(remarks.string()):
                    return True
            elif self._operation == StringFilterOperation.MatchRegex:
                if self._regex.match(remarks.string()):
                    return True
            else:
                raise ValueError('Invalid remarks filter operation')
        return False

class TradeCodeFilter(WorldFilter):
    def __init__(
            self,
            operation: ListFilterOperation,
            value: typing.Iterable[traveller.TradeCode]
            ) -> None:
        super().__init__()
        self._operation = operation
        self._value = set(value)

    def operation(self) -> ListFilterOperation:
        return self._operation

    def value(self) -> typing.Iterable[traveller.TradeCode]:
        return self._value

    def description(self) -> str:
        if len(self._value) == 1:
            operationString = _ListFilterSingleOperationDescriptionMap.get(self._operation)
        else:
            operationString = _ListFilterMultiOperationDescriptionMap.get(self._operation)
        if not operationString:
            return None

        listString = ''
        for index, tradeCode in enumerate(self._value):
            typeString = traveller.tradeCodeName(tradeCode=tradeCode)

            if index == 0:
                listString = typeString
            elif index == len(self._value) - 1:
                if self._operation == ListFilterOperation.ContainsAny:
                    listString += f' or {typeString}'
                else:
                    listString += f' and {typeString}'
            else:
                listString += f', {typeString}'
        return f'Trade Codes {operationString} {listString}'

    def match(self, world: traveller.World) -> bool:
        checkList = traveller.TradeCode if self._operation == ListFilterOperation.ContainsOnly else self._value
        for tradeCode in checkList:
            match = world.hasTradeCode(tradeCode)
            if self._operation == ListFilterOperation.ContainsAny:
                if match:
                    return True
            elif self._operation == ListFilterOperation.ContainsAll:
                if not match:
                    return False
            elif self._operation == ListFilterOperation.ContainsOnly:
                allowed = tradeCode in self._value
                if match != allowed:
                    return False
            else:
                raise ValueError('Invalid trade code filter operation')

        return self._operation != ListFilterOperation.ContainsAny

class PBGFilter(WorldFilter):
    def __init__(
            self,
            element: traveller.PBG.Element,
            operation: ComparisonFilterOperation,
            value: str
            ) -> None:
        super().__init__()
        self._element = element
        self._operation = operation
        self._value = value
        self._integer = traveller.ehexToInteger(value=self._value, default=None)

    def element(self) -> traveller.UWP.Element:
        return self._element

    def operation(self) -> ComparisonFilterOperation:
        return self._operation

    def value(self) -> str:
        return self._value

    def description(self) -> str:
        if self._element == traveller.PBG.Element.PopulationMultiplier:
            elementString = 'Population Multiplier'
        elif self._element == traveller.PBG.Element.PlanetoidBelts:
            elementString = 'Planetoid Belt Count'
        elif self._element == traveller.PBG.Element.GasGiants:
            elementString = 'Gas Giant Count'
        else:
            return None

        operationString = _ComparisonFilterOperationDescriptionMap[self._operation]
        if not operationString:
            return None

        return f'{elementString} {operationString} {self._value}'

    def match(self, world: traveller.World) -> bool:
        return _performComparisonOperation(
            operation=self._operation,
            worldValue=traveller.ehexToInteger(
                value=world.pbg().code(self._element),
                default=None),
            compareValue=self._integer)

class WorldSearch(object):
    def __init__(self) -> None:
        super().__init__()
        self._logic = FilterLogic.MatchesAll
        self._filters: typing.List[WorldFilter] = []

    def logic(self) -> FilterLogic:
        return self._logic

    def setLogic(self, filterLogic: FilterLogic) -> None:
        self._logic = filterLogic

    def filters(self) -> typing.Iterable[WorldFilter]:
        return self._filters

    def addFilter(self, filter: WorldFilter) -> None:
        self._filters.append(filter)

    def addFilters(self, filters: typing.Iterable[WorldFilter]) -> None:
        for filter in filters:
            self._filters.append(filter)

    def setFilters(self, filters: typing.Iterable[WorldFilter]) -> None:
        self.clear()
        self.addFilters(filters=filters)

    def removeFilter(self, filter: WorldFilter) -> None:
        if filter in self._filters:
            self._filters.remove(filter)

    def clear(self) -> None:
        self._filters.clear()

    def checkWorld(
            self,
            world: traveller.World
            ) -> bool: # # True if matched, False if ignored
        if not self._filters:
            return True # No filter always matches the world

        for filter in self._filters:
            matched = filter.match(world)
            if self._logic == FilterLogic.MatchesAll:
                if not matched:
                    return False
            elif self._logic == FilterLogic.MatchesAny:
                if matched:
                    return True
            elif self._logic == FilterLogic.MatchesNone:
                if matched:
                    return False
            else:
                raise TypeError('Invalid logical operation')
        return self._logic == FilterLogic.MatchesAll or \
            self._logic == FilterLogic.MatchesNone

    def search(
            self,
            maxResults: int = 1000
            ) -> typing.Iterable[traveller.World]:
        results = []
        for sector in traveller.WorldManager.instance().sectors():
            self._searchWorldList(
                worldList=sector,
                inPlaceResults=results,
                maxResults=maxResults)
            if maxResults and len(results) >= maxResults:
                break
        return results

    def searchRegion(
            self,
            sectorName: str,
            subsectorName: typing.Optional[str] = None,
            maxResults: int = 1000
            ) -> typing.Iterable[traveller.World]:
        sector = traveller.WorldManager.instance().sectorByName(name=sectorName)
        if not sector:
            raise RuntimeError(f'Sector "{sectorName}" for found')

        if not subsectorName:
            return self._searchWorldList(worldList=sector, maxResults=maxResults)
        else:
            subsector = sector.subsector(name=subsectorName)
            if not subsector:
                raise RuntimeError(f'Subsector "{subsectorName}" not found in sector "{sectorName}"')
            return self._searchWorldList(worldList=subsector, maxResults=maxResults)

    def searchArea(
            self,
            centerHex: travellermap.HexPosition,
            searchRadius: int
            ) -> typing.Iterable[traveller.World]:
        return traveller.WorldManager.instance().worldsInRadius(
            center=centerHex,
            searchRadius=searchRadius,
            worldFilterCallback=self.checkWorld)

    def _searchWorldList(
            self,
            worldList: typing.Iterable[traveller.World],
            maxResults: int,
            inPlaceResults: typing.Optional[typing.Iterable[traveller.World]] = None
            ) -> typing.Iterable[traveller.World]:
        if inPlaceResults != None:
            results = inPlaceResults
        else:
            results = []

        for world in worldList:
            if self.checkWorld(world):
                results.append(world)
                if maxResults and len(results) >= maxResults:
                    return results
        return results
