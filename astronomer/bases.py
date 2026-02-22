import enum
import survey
import typing

# There are two sets of base codes, an older set from before Traveller 5th
# edition and a newer set from 5th edition onwards. Unfortunately there are
# some minor conflicts (see https://travellermap.com/doc/secondsurvey#bases).
# I've gone with the approach of using a super set of them all, where there
# are conflicts, going with the 5th edition definition.

class BaseType(enum.Enum):
    ExplorationBase = 1
    MilitaryBase = 2
    NavalDepot = 3
    NavalBase = 4
    WayStation = 5
    AslanClanBase = 6
    AslanTlaukhuBase = 7
    DroyneNavalBase = 8
    DroyneMilitaryGarrison = 9
    HiverEmbassy = 10
    HiverNavalBase = 11
    ImperialNavalBase = 12
    ImperialScoutBase = 13
    KkreeNavalOutpose = 14
    VargrCorsairBase = 15
    VargrNavalBase = 16
    ZhodaniRelayStation = 17
    ZhodaniDepot = 18
    ZhodaniNavalMilitaryBase = 19


_CodeToBaseTypeMap = {
    'A': [BaseType.ImperialNavalBase, BaseType.ImperialScoutBase],
    'B': [BaseType.ImperialNavalBase, BaseType.WayStation],
    'C': [BaseType.VargrCorsairBase],
    'D': [BaseType.NavalDepot], # This was 'Depot (Imerial)' prior to 5th edition
    'E': [BaseType.HiverEmbassy], # This was 'Embassy Center (Hiver)' prior to 5th edition
    'F': [BaseType.MilitaryBase, BaseType.NavalBase],
    'G': [BaseType.VargrNavalBase],
    'H': [BaseType.VargrCorsairBase, BaseType.VargrNavalBase],
    'J': [BaseType.NavalBase],
    'K': [BaseType.NavalBase], # This was 'Naval Base (K'kree)' prior to 5th edition
    'L': [BaseType.HiverNavalBase],
    'M': [BaseType.MilitaryBase],
    'N': [BaseType.ImperialNavalBase],
    'O': [BaseType.KkreeNavalOutpose], # Note this uses O so isn't ehex
    'P': [BaseType.DroyneNavalBase],
    'Q': [BaseType.DroyneMilitaryGarrison],
    'R': [BaseType.AslanClanBase],
    'S': [BaseType.ImperialScoutBase],
    'T': [BaseType.AslanTlaukhuBase],
    'U': [BaseType.AslanTlaukhuBase, BaseType.AslanClanBase], # This was 'Tlauku Base (Aslan)' prior to 5th edition
    'V': [BaseType.ExplorationBase], # This was ''Scout/Exploration Base' prior to 5th edition
    'W': [BaseType.WayStation], # This was 'Way Station (Imperial)' prior to 5th edition
    'X': [BaseType.ZhodaniRelayStation],
    'Y': [BaseType.ZhodaniDepot],
    'Z': [BaseType.ZhodaniNavalMilitaryBase]
}

_BaseTypeToCodeMap = {
    BaseType.VargrCorsairBase: 'C',
    BaseType.NavalDepot: 'D',
    BaseType.HiverEmbassy: 'E',
    BaseType.VargrNavalBase: 'G',
    BaseType.NavalBase: 'K', # There are multiple glyphs that map to naval base (see comments above). I've gone with the one from the 5e rules
    BaseType.HiverNavalBase: 'L',
    BaseType.MilitaryBase: 'M',
    BaseType.ImperialNavalBase: 'N',
    BaseType.KkreeNavalOutpose: 'O',
    BaseType.DroyneNavalBase: 'P',
    BaseType.DroyneMilitaryGarrison: 'Q',
    BaseType.AslanClanBase: 'R',
    BaseType.ImperialScoutBase: 'S',
    BaseType.AslanTlaukhuBase: 'T',
    BaseType.ExplorationBase: 'V',
    BaseType.WayStation: 'W',
    BaseType.ZhodaniRelayStation: 'X',
    BaseType.ZhodaniDepot: 'Y',
    BaseType.ZhodaniNavalMilitaryBase: 'Z'
}
assert(set(_BaseTypeToCodeMap.keys()) == set(BaseType))

_BaseTypeToDescriptionMap = {
    BaseType.ExplorationBase: 'Exploration Base',
    BaseType.MilitaryBase: 'Military Base',
    BaseType.NavalDepot: 'Naval Depot',
    BaseType.NavalBase: 'Naval Base',
    BaseType.WayStation: 'Way Station',
    BaseType.AslanClanBase: 'Aslan Clan Base',
    BaseType.AslanTlaukhuBase: 'Aslan Tlaukhu Base',
    BaseType.DroyneNavalBase: 'Droyne Naval Base',
    BaseType.DroyneMilitaryGarrison: 'Droyne Military Garrison',
    BaseType.HiverEmbassy: 'Hiver Embassy',
    BaseType.HiverNavalBase: 'Hiver Naval Base',
    BaseType.ImperialNavalBase: 'Imperial Naval Base',
    BaseType.ImperialScoutBase: 'Imperial Scout Base',
    BaseType.KkreeNavalOutpose: 'K\'kree Naval Outpose',
    BaseType.VargrCorsairBase: 'Vargr Corsair Base',
    BaseType.VargrNavalBase: 'Vargr Naval Base',
    BaseType.ZhodaniRelayStation: 'Zhodani Relay Station',
    BaseType.ZhodaniDepot: 'Zhodani Depot',
    BaseType.ZhodaniNavalMilitaryBase: 'Zhodani Naval/Military Base',
}

_ScoutBaseTypes = [
    BaseType.ExplorationBase,
    BaseType.ImperialScoutBase
]

_MilitaryBaseTypes = [
    BaseType.MilitaryBase,
    BaseType.NavalDepot,
    BaseType.NavalBase,
    BaseType.AslanClanBase,
    BaseType.DroyneNavalBase,
    BaseType.DroyneMilitaryGarrison,
    BaseType.HiverNavalBase,
    BaseType.ImperialNavalBase,
    BaseType.KkreeNavalOutpose,
    BaseType.VargrCorsairBase,
    BaseType.VargrNavalBase,
    BaseType.ZhodaniNavalMilitaryBase,
]

def codeToBaseTypes(code: str) -> typing.Optional[typing.Collection[BaseType]]:
    return  _CodeToBaseTypeMap.get(code)

class Bases(object):
    def __init__(
            self,
            bases: typing.Optional[typing.Collection[BaseType]] = None
            ) -> None:
        self._bases = list(bases) if bases else []
        self._string = None

    def isEmpty(self) -> bool:
        return not self._bases

    def count(self) -> int:
        return len(self._bases)

    def hasBase(self, base: BaseType) -> bool:
        return base in self._bases

    def hasScoutBase(self) -> bool:
        for base in _ScoutBaseTypes:
            if base in self._bases:
                return True
        return False

    def scoutBases(self) -> typing.Optional[typing.Iterable[BaseType]]:
        scoutBases = None
        for base in _ScoutBaseTypes:
            if base in self._bases:
                if scoutBases == None:
                    scoutBases = set()
                scoutBases.add(base)
        return scoutBases

    def hasMilitaryBase(self) -> bool:
        for base in _MilitaryBaseTypes:
            if base in self._bases:
                return True
        return False

    def militaryBases(self) -> typing.Optional[typing.Iterable[BaseType]]:
        militaryBases = None
        for base in _MilitaryBaseTypes:
            if base in self._bases:
                if militaryBases == None:
                    militaryBases = set()
                militaryBases.add(base)
        return militaryBases

    def string(self) -> str:
        if self._string is None:
            self._string = survey.formatSystemBasesString(
                bases=[_BaseTypeToCodeMap[b] for b in self._bases])
        return self._string

    @staticmethod
    def code(baseType: BaseType) -> str:
        return _BaseTypeToCodeMap[baseType]

    @staticmethod
    def description(baseType: BaseType) -> str:
        return _BaseTypeToDescriptionMap[baseType]

    @staticmethod
    def descriptionMap() -> typing.Mapping[BaseType, str]:
        return _BaseTypeToDescriptionMap

    def __getitem__(self, index: int) -> BaseType:
        return self._bases.__getitem__(index)

    def __iter__(self) -> typing.Iterator[BaseType]:
        return self._bases.__iter__()

    def __next__(self) -> typing.Any:
        return self._bases.__next__()

    def __len__(self) -> int:
        return self._bases.__len__()
