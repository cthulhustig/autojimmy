import traveller
import typing

class Subsector(object):
    def __init__(
            self,
            name: str,
            worlds: typing.Iterable[traveller.World],
            ) -> None:
        self._name = name
        self._worlds = worlds

        self._worldPositionMap: typing.Dict[typing.Tuple[int, int], traveller.World] = {}
        for world in self._worlds:
            self._worldPositionMap[(world.x(), world.y())] = world

    def name(self) -> str:
        return self._name

    def worldCount(self) -> int:
        return len(self._worlds)

    def worlds(self) -> typing.Iterable[traveller.World]:
        return self._worlds

    def worldByPosition(self, x: int, y: int) -> traveller.World:
        return self._worldPositionMap.get((x, y))

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
            subsectorNames: typing.Iterable[str]
            ) -> None:
        self._name = name
        self._alternateNames = alternateNames
        self._abbreviation = abbreviation
        self._x = x
        self._y = y
        self._worlds = worlds
        self._worldPositionMap: typing.Dict[typing.Tuple[int, int], traveller.World] = {}
        self._subsectorMap: typing.Dict[str, Subsector] = {}

        subsectorWorlds: typing.Dict[str, typing.List[traveller.World]] = {}
        for subsectorName in subsectorNames:
            subsectorWorlds[subsectorName] = []

        for world in self._worlds:
            self._worldPositionMap[(world.x(), world.y())] = world

            assert(world.subsectorName() in subsectorWorlds)
            worldList = subsectorWorlds[world.subsectorName()]
            worldList.append(world)

        for subsectorName, worldList in subsectorWorlds.items():
            self._subsectorMap[subsectorName] = Subsector(
                name=subsectorName,
                worlds=worldList)

    def name(self) -> str:
        return self._name

    def alternateNames(self) -> typing.Optional[typing.Iterable[str]]:
        return self._alternateNames

    def abbreviation(self) -> typing.Optional[str]:
        return self._abbreviation

    def x(self) -> int:
        return self._x

    def y(self) -> int:
        return self._y

    def worldCount(self) -> int:
        return len(self._worlds)

    def worlds(self) -> typing.Iterable[traveller.World]:
        return self._worlds

    def worldByPosition(self, x: int, y: int) -> traveller.World:
        return self._worldPositionMap.get((x, y))

    def subsectorNames(self) -> typing.Iterable[str]:
        return self._subsectorMap.keys()

    def subsector(self, name: str) -> typing.Optional[Subsector]:
        return self._subsectorMap.get(name)

    def subsectors(self) -> typing.Iterable[Subsector]:
        return self._subsectorMap.values()

    def __getitem__(self, index: int) -> traveller.World:
        return self._worlds.__getitem__(index)

    def __iter__(self) -> typing.Iterator[traveller.World]:
        return self._worlds.__iter__()

    def __next__(self) -> typing.Any:
        return self._worlds.__next__()

    def __len__(self) -> int:
        return self._worlds.__len__()
