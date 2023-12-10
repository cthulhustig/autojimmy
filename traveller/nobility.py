import enum
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


_NobilityCodeMap = {
    NobilityType.Knight: 'B',
    NobilityType.Baronet: 'c',
    NobilityType.Baron: 'C',
    NobilityType.Marquis: 'D',
    NobilityType.Viscount: 'e',
    NobilityType.Count: 'E',
    NobilityType.Duke: 'f',
    NobilityType.SubsectorDuke: 'F',
    NobilityType.Archduke: 'G',
    NobilityType.Emperor: 'H',
}

_NobilityDescriptionMap = {
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
            string: str
            ) -> None:
        self._string = string
        self._nobilities = self._parseString(self._string)

    def string(self) -> str:
        return self._string
    
    def hasNobilities(self) -> bool:
        return len(self._nobilities) > 0

    def hasNobility(self, nobility: NobilityType) -> bool:
        return nobility in self._nobilities

    @staticmethod
    def code(nobilityType: NobilityType) -> str:
        return _NobilityCodeMap[nobilityType]

    @staticmethod
    def description(nobilityType: NobilityType) -> str:
        return _NobilityDescriptionMap[nobilityType]

    @staticmethod
    def descriptionMap() -> typing.Mapping[NobilityType, str]:
        return _NobilityDescriptionMap

    @staticmethod
    def _parseString(string: str) -> typing.List[NobilityType]:
        # Use a list rather than a set to maintain priority order of nobilities (lowest to highest)
        nobilities = []
        for nobilityType, nobilityCode in _NobilityCodeMap.items():
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
