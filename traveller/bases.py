import enum
import logging
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

_BaseTypeDescriptionMap = {
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

class Bases(object):
    def __init__(
            self,
            string: str
            ) -> None:
        self._string = string
        self._bases = Bases._parseString(self._string)

    def string(self) -> str:
        return self._string

    def hasBases(self) -> bool:
        return len(self._bases) > 0

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

    @staticmethod
    def code(baseType: BaseType) -> str:
        return _BaseTypeToCodeMap[baseType]

    @staticmethod
    def description(baseType: BaseType) -> str:
        return _BaseTypeDescriptionMap[baseType]

    @staticmethod
    def descriptionMap() -> typing.Mapping[BaseType, str]:
        return _BaseTypeDescriptionMap

    @staticmethod
    def _parseString(string: str) -> typing.Set[BaseType]:
        bases = set()
        for code in string:
            codeBaseTypes = _CodeToBaseTypeMap.get(code)
            if not codeBaseTypes:
                logging.debug(f'Ignoring unknown base code "{code}"')
                continue

            bases.update(codeBaseTypes)
        return bases

    def __getitem__(self, index: int) -> BaseType:
        return self._bases.__getitem__(index)

    def __iter__(self) -> typing.Iterator[BaseType]:
        return self._bases.__iter__()

    def __next__(self) -> typing.Any:
        return self._bases.__next__()

    def __len__(self) -> int:
        return self._bases.__len__()
