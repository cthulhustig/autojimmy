import traveller
import typing

class Subsector(object):
    def __init__(
            self,
            name: str,
            sectorName: str,
            worlds: typing.Iterable[traveller.World],
            ) -> None:
        self._name = name
        self._sectorName = sectorName
        self._worlds = worlds

    def name(self) -> str:
        return self._name

    def sectorName(self) -> str:
        return self._sectorName

    def worldCount(self) -> int:
        return len(self._worlds)

    def worlds(self) -> typing.Collection[traveller.World]:
        return list(self._worlds)

    def __getitem__(self, index: int) -> traveller.World:
        return self._worlds.__getitem__(index)

    def __iter__(self) -> typing.Iterator[traveller.World]:
        return self._worlds.__iter__()

    def __next__(self) -> typing.Any:
        return self._worlds.__next__()

    def __len__(self) -> int:
        return self._worlds.__len__()

class Sector(object):
    def __init__(
            self,
            name: str,
            alternateNames: typing.Optional[typing.Iterable[str]],
            abbreviation: typing.Optional[str],
            x: int,
            y: int,
            worlds: typing.Iterable[traveller.World],
            subsectorNames: typing.Iterable[str] # Subsector names should be ordered in subsector order (i.e. A-P)
            ) -> None:
        self._name = name
        self._alternateNames = alternateNames
        self._abbreviation = abbreviation
        self._x = x
        self._y = y
        self._worlds = list(worlds)
        self._subsectorMap: typing.Dict[str, Subsector] = {}

        subsectorWorldsMap: typing.Dict[str, typing.List[traveller.World]] = {}
        for subsectorName in subsectorNames:
            subsectorWorldsMap[subsectorName] = []

        for world in self._worlds:
            assert(world.subsectorName() in subsectorWorldsMap)
            subsectorWorlds = subsectorWorldsMap[world.subsectorName()]
            subsectorWorlds.append(world)

        for subsectorName, subsectorWorlds in subsectorWorldsMap.items():
            self._subsectorMap[subsectorName] = Subsector(
                name=subsectorName,
                sectorName=self._name,
                worlds=subsectorWorlds)

    def name(self) -> str:
        return self._name

    def alternateNames(self) -> typing.Optional[typing.Collection[str]]:
        return list(self._alternateNames) if self._alternateNames else None

    def abbreviation(self) -> typing.Optional[str]:
        return self._abbreviation

    def x(self) -> int:
        return self._x

    def y(self) -> int:
        return self._y

    def worldCount(self) -> int:
        return len(self._worlds)

    def worlds(self) -> typing.Collection[traveller.World]:
        return list(self._worlds)

    def subsectorNames(self) -> typing.Sequence[str]:
        return list(self._subsectorMap.keys())

    def subsector(self, name: str) -> typing.Optional[Subsector]:
        return self._subsectorMap.get(name)

    def subsectors(self) -> typing.Sequence[Subsector]:
        return list(self._subsectorMap.values())

    def __getitem__(self, index: int) -> traveller.World:
        return self._worlds.__getitem__(index)

    def __iter__(self) -> typing.Iterator[traveller.World]:
        return self._worlds.__iter__()

    def __next__(self) -> typing.Any:
        return self._worlds.__next__()

    def __len__(self) -> int:
        return self._worlds.__len__()
