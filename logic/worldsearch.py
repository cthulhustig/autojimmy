import enum
import logic
import re
import traveller
import multiverse
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

    def match(
            self,
            world: multiverse.World,
            rules: traveller.Rules,
            tagging: logic.WorldTagging
            ) -> bool:
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

    def match(
            self,
            world: multiverse.World,
            rules: traveller.Rules,
            tagging: logic.WorldTagging
            ) -> bool:
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

class TagLevelFiler(WorldFilter):
    def __init__(
            self,
            operation: ComparisonFilterOperation,
            value: logic.TagLevel
            ) -> None:
        super().__init__()
        self._operation = operation
        self._value = value
        self._integer = TagLevelFiler._tagLevelToInt(self._value)

    def operation(self) -> ComparisonFilterOperation:
        return self._operation

    def value(self) -> logic.TagLevel:
        return self._value

    def description(self) -> str:
        operationString = _ComparisonFilterOperationDescriptionMap[self._operation]
        if not operationString:
            return None

        return f'Tag Level {operationString} {self._value.name}'

    def match(
            self,
            world: multiverse.World,
            rules: traveller.Rules,
            tagging: logic.WorldTagging
            ) -> bool:
        return _performComparisonOperation(
            operation=self._operation,
            worldValue=TagLevelFiler._tagLevelToInt(tagging.calculateWorldTagLevel(world)),
            compareValue=self._integer)

    @staticmethod
    def _tagLevelToInt(level: str) -> int:
        if level == logic.TagLevel.Danger:
            return 2
        elif level == logic.TagLevel.Warning:
            return 1
        return 0

class ZoneFiler(WorldFilter):
    def __init__(
            self,
            operation: ComparisonFilterOperation,
            value: multiverse.ZoneType
            ) -> None:
        super().__init__()
        self._operation = operation
        self._value = value
        self._integer = ZoneFiler._zoneToInt(self._value)

    def operation(self) -> ComparisonFilterOperation:
        return self._operation

    def value(self) -> multiverse.ZoneType:
        return self._value

    def description(self) -> str:
        operationString = _ComparisonFilterOperationDescriptionMap[self._operation]
        if not operationString:
            return None

        return f'Zone {operationString} {multiverse.zoneTypeName(self._value)}'

    def match(
            self,
            world: multiverse.World,
            rules: traveller.Rules,
            tagging: logic.WorldTagging
            ) -> bool:
        return _performComparisonOperation(
            operation=self._operation,
            worldValue=ZoneFiler._zoneToInt(world.zone()),
            compareValue=self._integer)

    # Greater/less than comparisons don't really make logical sense for zones
    # but this function makes an attempt to map them to integers so it does
    # something vaguely sensible if the user chooses to do it. It's based on the
    # thinking that Forbidden/Unabsorbed are equivalent to Red/Amber zones
    # respectively (at least the Traveller Map IsAmber/IsRed treat them that way).
    @staticmethod
    def _zoneToInt(zone: multiverse.ZoneType) -> int:
        if zone == multiverse.ZoneType.RedZone:
            return 5
        elif zone == multiverse.ZoneType.Forbidden:
            return 4
        elif zone == multiverse.ZoneType.AmberZone:
            return 3
        elif zone == multiverse.ZoneType.Unabsorbed:
            return 2
        elif zone == multiverse.ZoneType.Balkanized:
            return 1
        else:
            return 0

class UWPFilter(WorldFilter):
    def __init__(
            self,
            element: multiverse.UWP.Element,
            operation: ComparisonFilterOperation,
            value: str
            ) -> None:
        super().__init__()
        self._element = element
        self._operation = operation
        self._value = value
        self._integer = multiverse.ehexToInteger(value=self._value, default=None)

    def element(self) -> multiverse.UWP.Element:
        return self._element

    def operation(self) -> ComparisonFilterOperation:
        return self._operation

    def value(self) -> str:
        return self._value

    def description(self) -> str:
        if self._element == multiverse.UWP.Element.StarPort:
            elementString = 'Star Port'
        elif self._element == multiverse.UWP.Element.WorldSize:
            elementString = 'World size'
        elif self._element == multiverse.UWP.Element.Atmosphere:
            elementString = 'Atmosphere'
        elif self._element == multiverse.UWP.Element.Hydrographics:
            elementString = 'Hydrographics'
        elif self._element == multiverse.UWP.Element.Population:
            elementString = 'Population'
        elif self._element == multiverse.UWP.Element.Government:
            elementString = 'Government'
        elif self._element == multiverse.UWP.Element.LawLevel:
            elementString = 'Law Level'
        elif self._element == multiverse.UWP.Element.TechLevel:
            elementString = 'Tech Level'
        else:
            return None

        operationString = _ComparisonFilterOperationDescriptionMap[self._operation]
        if not operationString:
            return None

        return f'{elementString} {operationString} {self._value}'

    def match(
            self,
            world: multiverse.World,
            rules: traveller.Rules,
            tagging: logic.WorldTagging
            ) -> bool:
        return _performComparisonOperation(
            operation=self._operation,
            worldValue=multiverse.ehexToInteger(
                value=world.uwp().code(self._element),
                default=None),
            compareValue=self._integer)

class EconomicsFilter(WorldFilter):
    def __init__(
            self,
            element: multiverse.Economics.Element,
            operation: ComparisonFilterOperation,
            value: str
            ) -> None:
        super().__init__()
        self._element = element
        self._operation = operation
        self._value = value

        if self._element == multiverse.Economics.Element.Efficiency:
            self._integer = int(self._value) if self._value != '?' else None
        else:
            self._integer = multiverse.ehexToInteger(value=self._value, default=None)

    def element(self) -> multiverse.Economics.Element:
        return self._element

    def operation(self) -> ComparisonFilterOperation:
        return self._operation

    def value(self) -> str:
        return self._value

    def description(self) -> str:
        if self._element == multiverse.Economics.Element.Resources:
            elementString = 'Resources'
        elif self._element == multiverse.Economics.Element.Labour:
            elementString = 'Labour'
        elif self._element == multiverse.Economics.Element.Infrastructure:
            elementString = 'Infrastructure'
        elif self._element == multiverse.Economics.Element.Efficiency:
            elementString = 'Efficiency'
        else:
            return None

        operationString = _ComparisonFilterOperationDescriptionMap.get(self._operation)
        if not operationString:
            return None

        return f'{elementString} {operationString} {self._value}'

    def match(
            self,
            world: multiverse.World,
            rules: traveller.Rules,
            tagging: logic.WorldTagging
            ) -> bool:
        code = world.economics().code(self._element)
        if self._element == multiverse.Economics.Element.Efficiency:
            worldValue = int(code) if code != '?' else None
        else:
            worldValue = multiverse.ehexToInteger(
                value=code,
                default=None)

        return _performComparisonOperation(
            operation=self._operation,
            worldValue=worldValue,
            compareValue=self._integer)

class CultureFilter(WorldFilter):
    def __init__(
            self,
            element: multiverse.Culture.Element,
            operation: ComparisonFilterOperation,
            value: str
            ) -> None:
        super().__init__()
        self._element = element
        self._operation = operation
        self._value = value
        self._integer = multiverse.ehexToInteger(value=self._value, default=None)

    def element(self) -> multiverse.Culture.Element:
        return self._element

    def operation(self) -> ComparisonFilterOperation:
        return self._operation

    def value(self) -> str:
        return self._value

    def description(self) -> str:
        if self._element == multiverse.Culture.Element.Heterogeneity:
            elementString = 'Heterogeneity'
        elif self._element == multiverse.Culture.Element.Acceptance:
            elementString = 'Acceptance'
        elif self._element == multiverse.Culture.Element.Strangeness:
            elementString = 'Strangeness'
        elif self._element == multiverse.Culture.Element.Symbols:
            elementString = 'Symbols'
        else:
            return None

        operationString = _ComparisonFilterOperationDescriptionMap.get(self._operation)
        if not operationString:
            return None

        return f'{elementString} {operationString} {self._value}'

    def match(
            self,
            world: multiverse.World,
            rules: traveller.Rules,
            tagging: logic.WorldTagging
            ) -> bool:
        return _performComparisonOperation(
            operation=self._operation,
            worldValue=multiverse.ehexToInteger(
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
            value: typing.Iterable[Type]
            ) -> None:
        super().__init__()
        self._operation = operation
        self._value = set(value)

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

    def match(
            self,
            world: multiverse.World,
            rules: traveller.Rules,
            tagging: logic.WorldTagging
            ) -> bool:
        checkList = RefuellingFilter.Type if self._operation == ListFilterOperation.ContainsOnly else self._value
        for refuelling in checkList:
            match = False
            if refuelling == RefuellingFilter.Type.RefinedRefuelling:
                match = traveller.worldHasStarPortRefuelling(
                    includeUnrefined=False,
                    world=world,
                    rules=rules)
            elif refuelling == RefuellingFilter.Type.UnrefinedRefuelling:
                match = traveller.worldHasStarPortRefuelling(
                    includeRefined=False,
                    world=world,
                    rules=rules)
            elif refuelling == RefuellingFilter.Type.GasGiantRefuelling:
                match = traveller.worldHasGasGiantRefuelling(world=world)
            elif refuelling == RefuellingFilter.Type.WaterRefuelling:
                match = traveller.worldHasWaterRefuelling(world=world)
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

    def match(
            self,
            world: multiverse.World,
            rules: traveller.Rules,
            tagging: logic.WorldTagging
            ) -> bool:
        allegiance = world.allegiance()
        if not allegiance:
            return False

        allegianceCode = allegiance.code()
        if self._operation == StringFilterOperation.ContainsString:
            if self._regex.search(allegianceCode):
                return True
        elif self._operation == StringFilterOperation.MatchRegex:
            if self._regex.match(allegianceCode):
                return True
        else:
            raise ValueError('Invalid allegiance filter operation')

        allegianceName = allegiance.name()
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

    def match(
            self,
            world: multiverse.World,
            rules: traveller.Rules,
            tagging: logic.WorldTagging
            ) -> bool:
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
            value: typing.Iterable[multiverse.BaseType]
            ) -> None:
        super().__init__()
        self._operation = operation
        self._value = set(value)

    def operation(self) -> ListFilterOperation:
        return self._operation

    def value(self) -> typing.Iterable[multiverse.BaseType]:
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
            typeString = multiverse.Bases.description(baseType=base)

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

    def match(
            self,
            world: multiverse.World,
            rules: traveller.Rules,
            tagging: logic.WorldTagging
            ) -> bool:
        checkList = multiverse.BaseType if self._operation == ListFilterOperation.ContainsOnly else self._value
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
            value: typing.Iterable[multiverse.NobilityType]
            ) -> None:
        super().__init__()
        self._operation = operation
        self._value = set(value)

    def operation(self) -> ListFilterOperation:
        return self._operation

    def value(self) -> typing.Iterable[multiverse.NobilityType]:
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
            typeString = multiverse.Nobilities.description(nobilityType=nobility)

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

    def match(
            self,
            world: multiverse.World,
            rules: traveller.Rules,
            tagging: logic.WorldTagging
            ) -> bool:
        checkList = multiverse.NobilityType if self._operation == ListFilterOperation.ContainsOnly else self._value
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

    def match(
            self,
            world: multiverse.World,
            rules: traveller.Rules,
            tagging: logic.WorldTagging
            ) -> bool:
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
            value: typing.Iterable[multiverse.TradeCode]
            ) -> None:
        super().__init__()
        self._operation = operation
        self._value = set(value)

    def operation(self) -> ListFilterOperation:
        return self._operation

    def value(self) -> typing.Iterable[multiverse.TradeCode]:
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
            typeString = multiverse.tradeCodeName(tradeCode=tradeCode)

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

    def match(
            self,
            world: multiverse.World,
            rules: traveller.Rules,
            tagging: logic.WorldTagging
            ) -> bool:
        checkList = multiverse.TradeCode if self._operation == ListFilterOperation.ContainsOnly else self._value
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
            element: multiverse.PBG.Element,
            operation: ComparisonFilterOperation,
            value: str
            ) -> None:
        super().__init__()
        self._element = element
        self._operation = operation
        self._value = value
        self._integer = multiverse.ehexToInteger(value=self._value, default=None)

    def element(self) -> multiverse.UWP.Element:
        return self._element

    def operation(self) -> ComparisonFilterOperation:
        return self._operation

    def value(self) -> str:
        return self._value

    def description(self) -> str:
        if self._element == multiverse.PBG.Element.PopulationMultiplier:
            elementString = 'Population Multiplier'
        elif self._element == multiverse.PBG.Element.PlanetoidBelts:
            elementString = 'Planetoid Belt Count'
        elif self._element == multiverse.PBG.Element.GasGiants:
            elementString = 'Gas Giant Count'
        else:
            return None

        operationString = _ComparisonFilterOperationDescriptionMap[self._operation]
        if not operationString:
            return None

        return f'{elementString} {operationString} {self._value}'

    def match(
            self,
            world: multiverse.World,
            rules: traveller.Rules,
            tagging: logic.WorldTagging
            ) -> bool:
        return _performComparisonOperation(
            operation=self._operation,
            worldValue=multiverse.ehexToInteger(
                value=world.pbg().code(self._element),
                default=None),
            compareValue=self._integer)

class WorldSearch(object):
    def __init__(self) -> None:
        super().__init__()
        self._logic = FilterLogic.MatchesAll
        self._filters: typing.List[WorldFilter] = []

    def filterLogic(self) -> FilterLogic:
        return self._logic

    def setFilterLogic(self, filterLogic: FilterLogic) -> None:
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
            world: multiverse.World,
            rules: traveller.Rules,
            tagging: logic.WorldTagging
            ) -> bool: # # True if matched, False if ignored
        if not self._filters:
            return True # No filter always matches the world

        for filter in self._filters:
            matched = filter.match(world=world, rules=rules, tagging=tagging)
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
            milieu: multiverse.Milieu,
            rules: traveller.Rules,
            tagging: logic.WorldTagging,
            maxResults: int = 1000
            ) -> typing.Iterable[multiverse.World]:
        results = []
        for sector in multiverse.WorldManager.instance().yieldSectors(milieu=milieu):
            self._searchWorlds(
                worlds=sector.yieldWorlds(),
                rules=rules,
                tagging=tagging,
                inPlaceResults=results,
                maxResults=maxResults)
            if maxResults and len(results) >= maxResults:
                break
        return results

    def searchRegion(
            self,
            milieu: multiverse.Milieu,
            rules: traveller.Rules,
            tagging: logic.WorldTagging,
            sectorName: str,
            subsectorName: typing.Optional[str] = None,
            maxResults: int = 1000
            ) -> typing.Iterable[multiverse.World]:
        sector = multiverse.WorldManager.instance().sectorByName(
            milieu=milieu,
            name=sectorName)
        if not sector:
            raise RuntimeError(f'Sector "{sectorName}" for found')

        if not subsectorName:
            return self._searchWorlds(
                worlds=sector.yieldWorlds(),
                rules=rules,
                tagging=tagging,
                maxResults=maxResults)
        else:
            subsector = sector.subsectorByName(name=subsectorName)
            if not subsector:
                raise RuntimeError(f'Subsector "{subsectorName}" not found in sector "{sectorName}"')
            return self._searchWorlds(
                worlds=subsector.yieldWorlds(),
                rules=rules,
                tagging=tagging,
                maxResults=maxResults)

    def searchRadius(
            self,
            milieu: multiverse.Milieu,
            rules: traveller.Rules,
            tagging: logic.WorldTagging,
            centerHex: multiverse.HexPosition,
            searchRadius: int
            ) -> typing.Iterable[multiverse.World]:
        return multiverse.WorldManager.instance().worldsInRadius(
            milieu=milieu,
            center=centerHex,
            searchRadius=searchRadius,
            filterCallback=lambda world: self.checkWorld(world=world, rules=rules, tagging=tagging))

    def _searchWorlds(
            self,
            worlds: typing.Iterable[multiverse.World],
            rules: traveller.Rules,
            tagging: logic.WorldTagging,
            maxResults: int,
            inPlaceResults: typing.Optional[typing.Iterable[multiverse.World]] = None
            ) -> typing.Iterable[multiverse.World]:
        if inPlaceResults != None:
            results = inPlaceResults
        else:
            results = []

        for world in worlds:
            if self.checkWorld(world=world, rules=rules, tagging=tagging):
                results.append(world)
                if maxResults and len(results) >= maxResults:
                    return results
        return results
