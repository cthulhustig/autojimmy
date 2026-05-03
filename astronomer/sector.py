import astronomer
import typing

class Sector(object):
    def __init__(
            self,
            isCustom: bool,
            milieu: astronomer.Milieu,
            position: astronomer.SectorPosition,
            name: str,
            alternateNames: typing.Optional[typing.Iterable[str]] = None,
            abbreviation: typing.Optional[str] = None,
            sectorLabel: typing.Optional[str] = None,
            subsectorNames: typing.Optional[typing.Mapping[str, str]] = None,
            worlds: typing.Optional[typing.Iterable[astronomer.World]] = None,
            allegiances: typing.Optional[typing.Iterable[astronomer.Allegiance]] = None,
            sophonts: typing.Optional[typing.Iterable[astronomer.Sophont]] = None,
            routes: typing.Optional[typing.Iterable[astronomer.Route]] = None,
            borders: typing.Optional[typing.Iterable[astronomer.Border]] = None,
            regions: typing.Optional[typing.Iterable[astronomer.Region]] = None,
            labels: typing.Optional[typing.Iterable[astronomer.Label]] = None,
            selected: bool = False,
            tagging: typing.Optional[astronomer.SectorTagging] = None,
            credits: typing.Optional[str] = None,
            source: typing.Optional[astronomer.SectorSource] = None,
            products: typing.Optional[typing.Iterable[astronomer.SectorSource]] = None
            ) -> None:
        self._isCustom = isCustom
        self._milieu = milieu
        self._position = position
        self._name = name
        self._alternateNames = list(alternateNames) if alternateNames else []
        self._abbreviation = abbreviation
        self._sectorLabel = sectorLabel
        self._worlds = list(worlds) if worlds else []
        self._allegiances = list(allegiances) if allegiances else []
        self._sophonts = list(sophonts) if sophonts else []
        self._routes = list(routes) if routes else []
        self._borders = list(borders) if borders else []
        self._regions = list(regions) if regions else []
        self._labels = list(labels) if labels else []
        self._selected = selected
        self._tagging = tagging
        self._credits = credits
        self._source = source
        self._products = list(products) if products else []

        self._subsectorCodeToNameMap = dict(subsectorNames) if subsectorNames else {}
        self._subsectorNameToCodeMap = {v: k for k, v in self._subsectorCodeToNameMap.items()}

        self._subsectorCodeToWorldsMap = {}
        for world in self._worlds:
            hex = world.hex()
            subsectorCode = hex.subsectorCode()

            subsectorWorlds = self._subsectorCodeToWorldsMap.get(subsectorCode)
            if not subsectorWorlds:
                subsectorWorlds = []
                self._subsectorCodeToWorldsMap[subsectorCode] = subsectorWorlds
            subsectorWorlds.append(world)

        self._allegiances: typing.List[astronomer.Allegiance] = []
        self._allegianceCodeMap: typing.Dict[str, astronomer.Allegiance] = {}
        for allegiance in allegiances:
            self._allegiances.append(allegiance)
            self._allegianceCodeMap[allegiance.code()] = allegiance

    def milieu(self) -> astronomer.Milieu:
        return self._milieu

    def position(self) -> astronomer.SectorPosition:
        return self._position

    def name(self) -> str:
        return self._name

    def alternateNames(self) -> typing.List[str]:
        return list(self._alternateNames)

    def yieldAlternateNames(self) -> typing.Generator[str, None, None]:
        if self._alternateNames:
            for name in self._alternateNames:
                yield name

    def abbreviation(self) -> typing.Optional[str]:
        return self._abbreviation

    def sectorLabel(self) -> typing.Optional[str]:
        return self._sectorLabel

    def subsectorName(self, code: str) -> typing.Optional[str]:
        return self._subsectorCodeToNameMap.get(code)

    def worldCount(self) -> int:
        return len(self._worlds)

    def worlds(
            self,
            subsectorCode: typing.Optional[str] = None,
            filterCallback: typing.Optional[typing.Callable[[astronomer.World], bool]] = None
            ) -> typing.List[astronomer.World]:
        worlds = self._worlds if subsectorCode is None else self._subsectorCodeToWorldsMap.get(subsectorCode)
        if not worlds:
            return []
        if not filterCallback:
            return list(worlds)

        matched = []
        for world in worlds:
            if filterCallback(world):
                matched.append(world)
        return matched

    def yieldWorlds(
            self,
            subsectorCode: typing.Optional[str] = None,
            filterCallback: typing.Optional[typing.Callable[[astronomer.World], bool]] = None
            ) -> typing.Generator[astronomer.World, None, None]:
        worlds = self._worlds if subsectorCode is None else self._subsectorCodeToWorldsMap.get(subsectorCode)
        if worlds:
            for world in worlds:
                if not filterCallback or filterCallback(world):
                    yield world

    def allegiances(self) -> typing.List[astronomer.Allegiance]:
        return list(self._allegiances)

    def yieldAllegiances(self) -> typing.Generator[astronomer.Allegiance, None, None]:
        for allegiance in self._allegiances:
            yield allegiance

    def allegianceByCode(self, code: str) -> typing.Optional[astronomer.Allegiance]:
        return self._allegianceCodeMap.get(code)

    def routes(self) -> typing.List[astronomer.Route]:
        return list(self._routes)

    def yieldRoutes(self) -> typing.Generator[astronomer.Route, None, None]:
        for route in self._routes:
            yield route

    def borders(self) -> typing.List[astronomer.Border]:
        return list(self._borders)

    def yieldBorders(self) -> typing.Generator[astronomer.Border, None, None]:
        for border in self._borders:
            yield border

    def regions(self) -> typing.List[astronomer.Region]:
        return list(self._regions)

    def yieldRegions(self) -> typing.Generator[astronomer.Region, None, None]:
        for region in self._regions:
            yield region

    def labels(self) -> typing.List[astronomer.Label]:
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

    def credits(self) -> typing.Optional[str]:
        return self._credits

    def source(self) -> typing.Optional[astronomer.SectorSource]:
        return self._source

    def products(self) -> typing.List[astronomer.SectorSource]:
        return list(self._products)

    def isCustom(self) -> bool:
        return self._isCustom

    def subsectorNames(self) -> typing.Sequence[str]:
        return list(self._subsectorCodeToNameMap.values())

    def yieldSubsectorNames(self) -> typing.Generator[str, None, None]:
        for name in self._subsectorCodeToNameMap.values():
            yield name

    def subsectorCodeByName(self, name: str) -> typing.Optional[str]:
        return self._subsectorNameToCodeMap.get(name)

    def __getitem__(self, index: int) -> astronomer.World:
        return self._worlds.__getitem__(index)

    def __iter__(self) -> typing.Iterator[astronomer.World]:
        return self._worlds.__iter__()

    def __next__(self) -> typing.Any:
        return self._worlds.__next__()

    def __len__(self) -> int:
        return self._worlds.__len__()
