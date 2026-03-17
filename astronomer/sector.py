import astronomer
import typing

class Subsector(object):
    def __init__(
            self,
            milieu: astronomer.Milieu,
            index: astronomer.SubsectorIndex,
            subsectorName: str,
            isNameGenerated: bool,
            sectorName: str,
            worlds: typing.Optional[typing.Iterable[astronomer.World]] = None,
            ) -> None:
        self._milieu = milieu
        self._index = index
        self._name = subsectorName
        self._isNameGenerated = isNameGenerated
        self._sectorName = sectorName
        self._worlds = list(worlds) if worlds else []

    def milieu(self) -> astronomer.Milieu:
        return self._milieu

    def code(self) -> str:
        return self._index.code()

    def index(self) -> astronomer.SubsectorIndex:
        return self._index

    def name(self) -> str:
        return self._name

    def sectorName(self) -> str:
        return self._sectorName

    def isNameGenerated(self) -> bool:
        return self._isNameGenerated

    def worldCount(self) -> int:
        return len(self._worlds)

    def worlds(self) -> typing.Collection[astronomer.World]:
        return list(self._worlds)

    def yieldWorlds(self) -> typing.Generator[astronomer.World, None, None]:
        for world in self._worlds:
            yield world

    def __getitem__(self, index: int) -> astronomer.World:
        return self._worlds.__getitem__(index)

    def __iter__(self) -> typing.Iterator[astronomer.World]:
        return self._worlds.__iter__()

    def __next__(self) -> typing.Any:
        return self._worlds.__next__()

    def __len__(self) -> int:
        return self._worlds.__len__()

class Sector(object):
    def __init__(
            self,
            isCustom: bool,
            milieu: astronomer.Milieu,
            index: astronomer.SectorIndex,
            name: str,
            alternateNames: typing.Optional[typing.Iterable[str]] = None,
            abbreviation: typing.Optional[str] = None,
            sectorLabel: typing.Optional[str] = None,
            # Subsectors should be ordered in subsector order (i.e. A-P)
            subsectors: typing.Optional[typing.Iterable[Subsector]] = None,
            allegiances: typing.Optional[typing.Iterable[astronomer.Allegiance]] = None,
            sophonts: typing.Optional[typing.Iterable[astronomer.Sophont]] = None,
            routes: typing.Optional[typing.Iterable[astronomer.Route]] = None,
            borders: typing.Optional[typing.Iterable[astronomer.Border]] = None,
            regions: typing.Optional[typing.Iterable[astronomer.Region]] = None,
            labels: typing.Optional[typing.Iterable[astronomer.Label]] = None,
            selected: bool = False,
            tagging: typing.Optional[astronomer.SectorTagging] = None,
            sources: typing.Optional[astronomer.SectorSources] = None
            ) -> None:
        self._isCustom = isCustom
        self._milieu = milieu
        self._index = index
        self._name = name
        self._alternateNames = list(alternateNames) if alternateNames else None
        self._abbreviation = abbreviation
        self._sectorLabel = sectorLabel
        self._allegiances = list(allegiances) if allegiances else []
        self._sophonts = list(sophonts) if sophonts else []
        self._routes = list(routes) if routes else []
        self._borders = list(borders) if borders else []
        self._regions = list(regions) if regions else []
        self._labels = list(labels) if labels else []
        self._selected = selected
        self._tagging = tagging
        self._sources = sources

        self._subsectorNameMap: typing.Dict[str, Subsector] = {}
        self._subsectorIndexMap: typing.Dict[typing.Tuple[int, int], Subsector] = {}
        self._subsectorCodeMap: typing.Dict[str, Subsector] = {}
        self._worlds: typing.List[astronomer.World] = []
        for subsector in subsectors:
            subsectorIndex = subsector.index()
            self._subsectorNameMap[subsector.name()] = subsector
            self._subsectorIndexMap[(subsectorIndex.indexX(), subsectorIndex.indexY())] = subsector
            self._subsectorCodeMap[subsectorIndex.code()] = subsector
            self._worlds.extend(subsector.worlds())

        self._allegiances: typing.List[astronomer.Allegiance] = []
        self._allegianceCodeMap: typing.Dict[str, astronomer.Allegiance] = {}
        for allegiance in allegiances:
            self._allegiances.append(allegiance)
            self._allegianceCodeMap[allegiance.code()] = allegiance

    def milieu(self) -> astronomer.Milieu:
        return self._milieu

    def index(self) -> astronomer.SectorIndex:
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

    def worlds(self) -> typing.Collection[astronomer.World]:
        return list(self._worlds)

    def yieldWorlds(self) -> typing.Generator[astronomer.World, None, None]:
        for world in self._worlds:
            yield world

    def allegiances(self) -> typing.List[astronomer.Allegiance]:
        return list(self._allegiances)

    def yieldAllegiances(self) -> typing.Generator[astronomer.Allegiance, None, None]:
        for allegiance in self._allegiances:
            yield allegiance

    def allegianceByCode(self, code: str) -> typing.Optional[astronomer.Allegiance]:
        return self._allegianceCodeMap.get(code)

    def routes(self) -> typing.Collection[astronomer.Route]:
        return list(self._routes)

    def yieldRoutes(self) -> typing.Generator[astronomer.Route, None, None]:
        for route in self._routes:
            yield route

    def borders(self) -> typing.Collection[astronomer.Border]:
        return list(self._borders)

    def yieldBorders(self) -> typing.Generator[astronomer.Border, None, None]:
        for border in self._borders:
            yield border

    def regions(self) -> typing.Collection[astronomer.Region]:
        return list(self._regions)

    def yieldRegions(self) -> typing.Generator[astronomer.Region, None, None]:
        for region in self._regions:
            yield region

    def labels(self) -> typing.Collection[astronomer.Label]:
        return list(self._labels)

    def yieldLabels(self) -> typing.Generator[astronomer.Label, None, None]:
        for label in self._labels:
            yield label

    # The concept of 'selected' comes from Traveller Map and what it is isn't
    # exactly clear. The only thing I've noticed it do is when rendering if
    # it's configured to only show some sector names, it only shows the names
    # for sectors that are selected.
    def selected(self) -> bool:
        return self._selected

    def tagging(self) -> typing.Optional[astronomer.SectorTagging]:
        return self._tagging

    def hasTag(self, tag: astronomer.SectorTag) -> bool:
        if self._tagging is None:
            return False
        return self._tagging.contains(tag)

    def sources(self) -> typing.Optional[astronomer.SectorSources]:
        return self._sources

    def isCustom(self) -> bool:
        return self._isCustom

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

    def __getitem__(self, index: int) -> astronomer.World:
        return self._worlds.__getitem__(index)

    def __iter__(self) -> typing.Iterator[astronomer.World]:
        return self._worlds.__iter__()

    def __next__(self) -> typing.Any:
        return self._worlds.__next__()

    def __len__(self) -> int:
        return self._worlds.__len__()
