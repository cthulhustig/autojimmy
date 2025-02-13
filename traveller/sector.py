import traveller
import travellermap
import typing

class Subsector(object):
    def __init__(
            self,
            indexX: int,
            indexY: int,
            name: str,
            sectorName: str,
            sectorX: int,
            sectorY: int,
            extent: typing.Tuple[
                travellermap.HexPosition,
                travellermap.HexPosition],
            worlds: typing.Iterable[traveller.World],
            ) -> None:
        self._indexX = indexX
        self._indexY = indexY
        self._code = chr(ord('A') + ((indexY * 4) + indexX))
        self._name = name
        self._sectorX = sectorX
        self._sectorY = sectorY
        self._sectorName = sectorName
        self._extent = extent
        self._worlds = worlds

    def indexX(self) -> int:
        return self._indexX

    def indexY(self) -> int:
        return self._indexY

    def code(self) -> str:
        return self._code

    def name(self) -> str:
        return self._name

    def sectorName(self) -> str:
        return self._sectorName

    def sectorX(self) -> int:
        return self._sectorX

    def sectorY(self) -> int:
        return self._sectorY

    def worldCount(self) -> int:
        return len(self._worlds)

    def worlds(self) -> typing.Collection[traveller.World]:
        return list(self._worlds)

    def extent(self) -> typing.Tuple[
            travellermap.HexPosition,
            travellermap.HexPosition]:
        return self._extent

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
            routes: typing.Iterable[traveller.Route],
            borders: typing.Iterable[traveller.Border],
            regions: typing.Iterable[traveller.Region],
            labels: typing.Iterable[traveller.Label],
            selected: bool,
            tags: typing.Iterable[str],
            subsectorNames: typing.Iterable[str] # Subsector names should be ordered in subsector order (i.e. A-P)
            ) -> None:
        self._name = name
        self._alternateNames = alternateNames
        self._abbreviation = abbreviation
        self._x = x
        self._y = y
        self._worlds = list(worlds)
        self._routes = list(routes)
        self._borders = list(borders)
        self._regions = list(regions)
        self._labels = list(labels)
        self._selected = selected
        self._tags = set(tags)
        self._subsectorMap: typing.Dict[str, Subsector] = {}
        self._extent = (
            travellermap.HexPosition(
                sectorX=x,
                sectorY=y,
                offsetX=1,
                offsetY=1),
            travellermap.HexPosition(
                sectorX=x,
                sectorY=y,
                offsetX=travellermap.SectorWidth,
                offsetY=travellermap.SectorHeight))

        subsectorWorldsMap: typing.Dict[str, typing.List[traveller.World]] = {}
        for subsectorName in subsectorNames:
            subsectorWorldsMap[subsectorName] = []

        for world in self._worlds:
            assert(world.subsectorName() in subsectorWorldsMap)
            subsectorWorlds = subsectorWorldsMap[world.subsectorName()]
            subsectorWorlds.append(world)

        self._subsectorIndexMap: typing.Dict[
            typing.Tuple[int, int],
            Subsector] = {}
        for index, (subsectorName, subsectorWorlds) in enumerate(subsectorWorldsMap.items()):
            indexX = index % 4
            indexY = index // 4
            ulHex = travellermap.HexPosition(
                sectorX=x,
                sectorY=y,
                offsetX=(indexX * travellermap.SubsectorWidth) + 1,
                offsetY=(indexY * travellermap.SubsectorHeight) + 1)
            brHex = travellermap.HexPosition(
                sectorX=x,
                sectorY=y,
                offsetX=ulHex.offsetX() + (travellermap.SubsectorWidth - 1),
                offsetY=ulHex.offsetY() + (travellermap.SubsectorHeight - 1))
            subsector = Subsector(
                indexX=indexX,
                indexY=indexY,
                name=subsectorName,
                sectorName=self._name,
                sectorX=self._x,
                sectorY=self._y,
                extent=(ulHex, brHex),
                worlds=subsectorWorlds)
            self._subsectorMap[subsectorName] = subsector
            self._subsectorIndexMap[(indexX, indexY)] = subsector

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

    # TODO: Returning copies of the list of routes/borders probably
    # isn't great when it's done every frame
    def routes(self) -> typing.Collection[traveller.Route]:
        return list(self._routes)

    def borders(self) -> typing.Collection[traveller.Border]:
        return list(self._borders)

    def regions(self) -> typing.Collection[traveller.Region]:
        return list(self._regions)

    def labels(self) -> typing.Collection[traveller.Label]:
        return list(self._labels)

    # The concept of 'selected' comes from Traveller Map and what it is isn't
    # exactly clear. The only thing I've noticed it do is when rendering if
    # it's configured to only show some sector names, it only shows the names
    # for sectors that are selected.
    def selected(self) -> bool:
        return self._selected

    def tags(self) -> typing.Iterable[str]:
        return list(self._tags)

    def hasTag(self, tag: str) -> bool:
        return tag in self._tags

    def subsectorNames(self) -> typing.Sequence[str]:
        return list(self._subsectorMap.keys())

    def subsectorByName(self, name: str) -> typing.Optional[Subsector]:
        return self._subsectorMap.get(name)

    def subsectorByIndex(self, indexX: int, indexY: int) -> typing.Optional[Subsector]:
        return self._subsectorIndexMap.get((indexX, indexY))

    def subsectors(self) -> typing.Sequence[Subsector]:
        return list(self._subsectorMap.values())

    def extent(self) -> typing.Tuple[travellermap.HexPosition, travellermap.HexPosition]:
        return self._extent

    def __getitem__(self, index: int) -> traveller.World:
        return self._worlds.__getitem__(index)

    def __iter__(self) -> typing.Iterator[traveller.World]:
        return self._worlds.__iter__()

    def __next__(self) -> typing.Any:
        return self._worlds.__next__()

    def __len__(self) -> int:
        return self._worlds.__len__()
