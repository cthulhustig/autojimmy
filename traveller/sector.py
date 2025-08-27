import traveller
import travellermap
import typing

class Subsector(object):
    def __init__(
            self,
            milieu: travellermap.Milieu,
            index: travellermap.SubsectorIndex,
            subsectorName: str,
            isNameGenerated: bool,
            sectorName: str,
            worlds: typing.Iterable[traveller.World],
            ) -> None:
        self._milieu = milieu
        self._index = index
        self._name = subsectorName
        self._isNameGenerated = isNameGenerated
        self._sectorName = sectorName
        self._worlds = list(worlds)

    def milieu(self) -> travellermap.Milieu:
        return self._milieu

    def code(self) -> str:
        return self._index.code()

    def index(self) -> travellermap.SubsectorIndex:
        return self._index

    def name(self) -> str:
        return self._name

    def sectorName(self) -> str:
        return self._sectorName

    def isNameGenerated(self) -> bool:
        return self._isNameGenerated

    def worldCount(self) -> int:
        return len(self._worlds)

    def worlds(self) -> typing.Collection[traveller.World]:
        return list(self._worlds)

    def yieldWorlds(self) -> typing.Generator[traveller.World, None, None]:
        for world in self._worlds:
            yield world

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
            index: travellermap.SubsectorIndex,
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
            tags: typing.Optional[str] = None
            ) -> None:
        self._milieu = milieu
        self._index = index
        self._name = name
        self._alternateNames = alternateNames
        self._abbreviation = abbreviation
        self._sectorLabel = sectorLabel
        self._routes = list(routes)
        self._borders = list(borders)
        self._regions = list(regions)
        self._labels = list(labels)
        self._selected = selected
        self._tags = traveller.SectorTagging(tags)

        self._subsectorNameMap: typing.Dict[str, Subsector] = {}
        self._subsectorIndexMap: typing.Dict[
            typing.Tuple[int, int],
            Subsector] = {}
        self._worlds: typing.List[traveller.World] = []
        for subsector in subsectors:
            subsectorIndex = subsector.index()
            self._subsectorNameMap[subsector.name()] = subsector
            self._subsectorIndexMap[(subsectorIndex.indexX(), subsectorIndex.indexY())] = subsector
            for world in subsector.worlds():
                self._worlds.append(world)

    def milieu(self) -> travellermap.Milieu:
        return self._milieu

    def index(self) -> travellermap.SectorIndex:
        return self._index

    def name(self) -> str:
        return self._name

    def alternateNames(self) -> typing.Optional[typing.Collection[str]]:
        return list(self._alternateNames) if self._alternateNames else None

    def yieldAlternateNames(self) -> typing.Generator[str, None, None]:
        if self._alternateNames:
            for name in self._alternateNames:
                yield name

    def abbreviation(self) -> typing.Optional[str]:
        return self._abbreviation

    def sectorLabel(self) -> typing.Optional[str]:
        return self._sectorLabel

    def worldCount(self) -> int:
        return len(self._worlds)

    def worlds(self) -> typing.Collection[traveller.World]:
        return list(self._worlds)

    def yieldWorlds(self) -> typing.Generator[traveller.World, None, None]:
        for world in self._worlds:
            yield world

    def routes(self) -> typing.Collection[traveller.Route]:
        return list(self._routes)

    def yieldRoutes(self) -> typing.Generator[traveller.Route, None, None]:
        for route in self._routes:
            yield route

    def borders(self) -> typing.Collection[traveller.Border]:
        return list(self._borders)

    def yieldBorders(self) -> typing.Generator[traveller.Border, None, None]:
        for border in self._borders:
            yield border

    def regions(self) -> typing.Collection[traveller.Region]:
        return list(self._regions)

    def yieldRegions(self) -> typing.Generator[traveller.Region, None, None]:
        for region in self._regions:
            yield region

    def labels(self) -> typing.Collection[traveller.Label]:
        return list(self._labels)

    def yieldLabels(self) -> typing.Generator[traveller.Label, None, None]:
        for label in self._labels:
            yield label

    # The concept of 'selected' comes from Traveller Map and what it is isn't
    # exactly clear. The only thing I've noticed it do is when rendering if
    # it's configured to only show some sector names, it only shows the names
    # for sectors that are selected.
    def selected(self) -> bool:
        return self._selected

    def tagging(self) -> traveller.SectorTagging:
        return self._tags

    def hasTag(self, tag: traveller.SectorTagging.Tag) -> bool:
        return self._tags.contains(tag)

    def subsectorNames(self) -> typing.Sequence[str]:
        return list(self._subsectorNameMap.keys())

    def yieldSubsectorNames(self) -> typing.Generator[str, None, None]:
        for name in self._subsectorNameMap.keys():
            yield name

    def subsectorByName(self, name: str) -> typing.Optional[Subsector]:
        return self._subsectorNameMap.get(name)

    def subsectorByIndex(self, indexX: int, indexY: int) -> typing.Optional[Subsector]:
        return self._subsectorIndexMap.get((indexX, indexY))

    def subsectors(self) -> typing.Sequence[Subsector]:
        return list(self._subsectorIndexMap.values())

    def yieldSubsectors(self) -> typing.Generator[Subsector, None, None]:
        for subsector in self._subsectorIndexMap.values():
            yield subsector

    def __getitem__(self, index: int) -> traveller.World:
        return self._worlds.__getitem__(index)

    def __iter__(self) -> typing.Iterator[traveller.World]:
        return self._worlds.__iter__()

    def __next__(self) -> typing.Any:
        return self._worlds.__next__()

    def __len__(self) -> int:
        return self._worlds.__len__()
