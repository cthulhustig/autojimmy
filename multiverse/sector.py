import multiverse
import typing

class Subsector(object):
    def __init__(
            self,
            milieu: multiverse.Milieu,
            index: multiverse.SubsectorIndex,
            subsectorName: str,
            isNameGenerated: bool,
            sectorName: str,
            worlds: typing.Iterable[multiverse.World],
            ) -> None:
        self._milieu = milieu
        self._index = index
        self._name = subsectorName
        self._isNameGenerated = isNameGenerated
        self._sectorName = sectorName
        self._worlds = list(worlds)

    def milieu(self) -> multiverse.Milieu:
        return self._milieu

    def code(self) -> str:
        return self._index.code()

    def index(self) -> multiverse.SubsectorIndex:
        return self._index

    def name(self) -> str:
        return self._name

    def sectorName(self) -> str:
        return self._sectorName

    def isNameGenerated(self) -> bool:
        return self._isNameGenerated

    def worldCount(self) -> int:
        return len(self._worlds)

    def worlds(self) -> typing.Collection[multiverse.World]:
        return list(self._worlds)

    def yieldWorlds(self) -> typing.Generator[multiverse.World, None, None]:
        for world in self._worlds:
            yield world

    def __getitem__(self, index: int) -> multiverse.World:
        return self._worlds.__getitem__(index)

    def __iter__(self) -> typing.Iterator[multiverse.World]:
        return self._worlds.__iter__()

    def __next__(self) -> typing.Any:
        return self._worlds.__next__()

    def __len__(self) -> int:
        return self._worlds.__len__()

class Sector(object):
    def __init__(
            self,
            milieu: multiverse.Milieu,
            index: multiverse.SubsectorIndex,
            name: str,
            alternateNames: typing.Optional[typing.Iterable[str]],
            abbreviation: typing.Optional[str],
            sectorLabel: typing.Optional[str],
            # Subsectors should be ordered in subsector order (i.e. A-P)
            subsectors: typing.Iterable[Subsector],
            routes: typing.Iterable[multiverse.Route],
            borders: typing.Iterable[multiverse.Border],
            regions: typing.Iterable[multiverse.Region],
            labels: typing.Iterable[multiverse.Label],
            selected: bool,
            tags: multiverse.SectorTagging
            ) -> None:
        self._milieu = milieu
        self._index = index
        self._name = name
        self._alternateNames = list(alternateNames) if alternateNames else None
        self._abbreviation = abbreviation
        self._sectorLabel = sectorLabel
        self._routes = list(routes)
        self._borders = list(borders)
        self._regions = list(regions)
        self._labels = list(labels)
        self._selected = selected
        self._tags = tags

        self._subsectorNameMap: typing.Dict[str, Subsector] = {}
        self._subsectorIndexMap: typing.Dict[typing.Tuple[int, int], Subsector] = {}
        self._subsectorCodeMap: typing.Dict[str, Subsector] = {}
        self._worlds: typing.List[multiverse.World] = []
        for subsector in subsectors:
            subsectorIndex = subsector.index()
            self._subsectorNameMap[subsector.name()] = subsector
            self._subsectorIndexMap[(subsectorIndex.indexX(), subsectorIndex.indexY())] = subsector
            self._subsectorCodeMap[subsectorIndex.code()] = subsector
            for world in subsector.worlds():
                self._worlds.append(world)

    def milieu(self) -> multiverse.Milieu:
        return self._milieu

    def index(self) -> multiverse.SectorIndex:
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

    def worlds(self) -> typing.Collection[multiverse.World]:
        return list(self._worlds)

    def yieldWorlds(self) -> typing.Generator[multiverse.World, None, None]:
        for world in self._worlds:
            yield world

    def routes(self) -> typing.Collection[multiverse.Route]:
        return list(self._routes)

    def yieldRoutes(self) -> typing.Generator[multiverse.Route, None, None]:
        for route in self._routes:
            yield route

    def borders(self) -> typing.Collection[multiverse.Border]:
        return list(self._borders)

    def yieldBorders(self) -> typing.Generator[multiverse.Border, None, None]:
        for border in self._borders:
            yield border

    def regions(self) -> typing.Collection[multiverse.Region]:
        return list(self._regions)

    def yieldRegions(self) -> typing.Generator[multiverse.Region, None, None]:
        for region in self._regions:
            yield region

    def labels(self) -> typing.Collection[multiverse.Label]:
        return list(self._labels)

    def yieldLabels(self) -> typing.Generator[multiverse.Label, None, None]:
        for label in self._labels:
            yield label

    # The concept of 'selected' comes from Traveller Map and what it is isn't
    # exactly clear. The only thing I've noticed it do is when rendering if
    # it's configured to only show some sector names, it only shows the names
    # for sectors that are selected.
    def selected(self) -> bool:
        return self._selected

    def tagging(self) -> multiverse.SectorTagging:
        return self._tags

    def hasTag(self, tag: multiverse.SectorTagging.Tag) -> bool:
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

    def subsectorByCode(self, code: str) -> typing.Optional[Subsector]:
        return self._subsectorCodeMap.get(code)

    def subsectors(self) -> typing.Sequence[Subsector]:
        return list(self._subsectorIndexMap.values())

    def yieldSubsectors(self) -> typing.Generator[Subsector, None, None]:
        for subsector in self._subsectorIndexMap.values():
            yield subsector

    def __getitem__(self, index: int) -> multiverse.World:
        return self._worlds.__getitem__(index)

    def __iter__(self) -> typing.Iterator[multiverse.World]:
        return self._worlds.__iter__()

    def __next__(self) -> typing.Any:
        return self._worlds.__next__()

    def __len__(self) -> int:
        return self._worlds.__len__()
