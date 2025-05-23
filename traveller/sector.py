import traveller
import travellermap
import typing

class Subsector(object):
    def __init__(
            self,
            milieu: travellermap.Milieu,
            sectorX: int,
            sectorY: int,
            code: str,
            subsectorName: str,
            isNameGenerated: bool,
            sectorName: str,
            worlds: typing.Iterable[traveller.World],
            ) -> None:
        self._milieu = milieu
        self._sectorX = sectorX
        self._sectorY = sectorY
        self._code = code
        self._name = subsectorName
        self._isNameGenerated = isNameGenerated
        self._sectorName = sectorName
        self._worlds = list(worlds)

        index = ord(code) - ord('A')
        self._indexX = index % 4
        self._indexY = index // 4

        ulHex = travellermap.HexPosition(
            sectorX=self._sectorX,
            sectorY=self._sectorY,
            offsetX=(self._indexX * travellermap.SubsectorWidth) + 1,
            offsetY=(self._indexY * travellermap.SubsectorHeight) + 1)
        brHex = travellermap.HexPosition(
            sectorX=self._sectorX,
            sectorY=self._sectorY,
            offsetX=ulHex.offsetX() + (travellermap.SubsectorWidth - 1),
            offsetY=ulHex.offsetY() + (travellermap.SubsectorHeight - 1))
        self._extent = (ulHex, brHex)

    def milieu(self) -> travellermap.Milieu:
        return self._milieu

    def sectorX(self) -> int:
        return self._sectorX

    def sectorY(self) -> int:
        return self._sectorY

    def code(self) -> str:
        return self._code

    def name(self) -> str:
        return self._name

    def sectorName(self) -> str:
        return self._sectorName

    def isNameGenerated(self) -> bool:
        return self._isNameGenerated

    def indexX(self) -> int:
        return self._indexX

    def indexY(self) -> int:
        return self._indexY

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
            milieu: travellermap.Milieu,
            x: int,
            y: int,
            name: str,
            alternateNames: typing.Optional[typing.Iterable[str]],
            abbreviation: typing.Optional[str],
            sectorLabel: typing.Optional[str],
            # Subsectors should be ordered in subsector order (i.e. A-P)
            subsectors: typing.Iterable[Subsector],
            routes: typing.Iterable[traveller.Route],
            borders: typing.Iterable[traveller.Border],
            regions: typing.Iterable[traveller.Region],
            labels: typing.Iterable[traveller.Label],
            selected: bool,
            tags: typing.Iterable[str]
            ) -> None:
        self._milieu = milieu
        self._x = x
        self._y = y
        self._name = name
        self._alternateNames = alternateNames
        self._abbreviation = abbreviation
        self._sectorLabel = sectorLabel
        self._routes = list(routes)
        self._borders = list(borders)
        self._regions = list(regions)
        self._labels = list(labels)
        self._selected = selected
        self._tags = set(tags)

        self._subsectorNameMap: typing.Dict[str, Subsector] = {}
        self._subsectorIndexMap: typing.Dict[
            typing.Tuple[int, int],
            Subsector] = {}
        self._worlds: typing.List[traveller.World] = []
        for subsector in subsectors:
            self._subsectorNameMap[subsector.name()] = subsector
            self._subsectorIndexMap[(subsector.indexX(), subsector.indexY())] = subsector
            for world in subsector.worlds():
                self._worlds.append(world)

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

    def milieu(self) -> travellermap.Milieu:
        return self._milieu

    def x(self) -> int:
        return self._x

    def y(self) -> int:
        return self._y

    def name(self) -> str:
        return self._name

    def alternateNames(self) -> typing.Optional[typing.Collection[str]]:
        return list(self._alternateNames) if self._alternateNames else None

    def abbreviation(self) -> typing.Optional[str]:
        return self._abbreviation

    def sectorLabel(self) -> typing.Optional[str]:
        return self._sectorLabel

    def worldCount(self) -> int:
        return len(self._worlds)

    def worlds(self) -> typing.Collection[traveller.World]:
        return list(self._worlds)

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
        return list(self._subsectorNameMap.keys())

    def subsectorByName(self, name: str) -> typing.Optional[Subsector]:
        return self._subsectorNameMap.get(name)

    def subsectorByIndex(self, indexX: int, indexY: int) -> typing.Optional[Subsector]:
        return self._subsectorIndexMap.get((indexX, indexY))

    def subsectors(self) -> typing.Sequence[Subsector]:
        return list(self._subsectorNameMap.values())

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
