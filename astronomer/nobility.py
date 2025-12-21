import enum
import logging
import multiverse
import typing

class NobilityType(enum.Enum):
    Knight = 0
    Baronet = 1
    Baron = 2
    Marquis = 3
    Viscount = 4
    Count = 5
    Duke = 6
    SubsectorDuke = 7
    Archduke = 8
    Emperor = 9

_CodeToNobilityTypeMap = {
    'B': NobilityType.Knight,
    'c': NobilityType.Baronet,
    'C': NobilityType.Baron,
    'D': NobilityType.Marquis,
    'e': NobilityType.Viscount,
    'E': NobilityType.Count,
    'f': NobilityType.Duke,
    'F': NobilityType.SubsectorDuke,
    'G': NobilityType.Archduke,
    'H': NobilityType.Emperor,
}
_NobilityTypeToCodeMap = {v: k for k, v in _CodeToNobilityTypeMap.items()}

_NobilityTypeToDescriptionMap = {
    NobilityType.Knight: 'Knight',
    NobilityType.Baronet: 'Baronet',
    NobilityType.Baron: 'Baron',
    NobilityType.Marquis: 'Marquis',
    NobilityType.Viscount: 'Viscount',
    NobilityType.Count: 'Count',
    NobilityType.Duke: 'Duke',
    NobilityType.SubsectorDuke: 'Subsector Duke',
    NobilityType.Archduke: 'Archduke',
    NobilityType.Emperor: 'Emperor',
}

class Nobilities(object):
    def __init__(
            self,
            dbNobilities: typing.Optional[typing.Collection[multiverse.DbNobility]]
            ) -> None:
        self._nobilities: typing.List[NobilityType] = []
        if dbNobilities:
            for dbNobility in dbNobilities:
                nobility = _CodeToNobilityTypeMap.get(dbNobility.code())
                if nobility is None:
                    logging.debug(f'Ignoring unknown base code "{dbNobility.code()}"')
                    continue
                self._nobilities.append(nobility)
        self._string = None

    def isEmpty(self) -> bool:
        return len(self._nobilities) == 0

    def hasNobility(self, nobility: NobilityType) -> bool:
        return nobility in self._nobilities

    def string(self) -> str:
        if self._string is None:
            self._string = multiverse.formatSystemNobilityString(
                nobilities=[_NobilityTypeToCodeMap[n] for n in self._nobilities])
        return self._string

    @staticmethod
    def code(nobilityType: NobilityType) -> str:
        return _NobilityTypeToCodeMap[nobilityType]

    @staticmethod
    def description(nobilityType: NobilityType) -> str:
        return _NobilityTypeToDescriptionMap[nobilityType]

    @staticmethod
    def descriptionMap() -> typing.Mapping[NobilityType, str]:
        return _NobilityTypeToDescriptionMap

    @staticmethod
    def _parseString(string: str) -> typing.List[NobilityType]:
        # Use a list rather than a set to maintain priority order of nobilities (lowest to highest)
        nobilities = []
        for nobilityType, nobilityCode in _NobilityTypeToCodeMap.items():
            if string.find(nobilityCode) >= 0:
                nobilities.append(nobilityType)
        return nobilities

    def __getitem__(self, index: int) -> NobilityType:
        return self._nobilities.__getitem__(index)

    def __iter__(self) -> typing.Iterator[NobilityType]:
        return self._nobilities.__iter__()

    def __next__(self) -> typing.Any:
        return self._nobilities.__next__()

    def __len__(self) -> int:
        return self._nobilities.__len__()
