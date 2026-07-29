import astronomer
import common
import itertools
import typing

class Sector(astronomer.Entity):
    def __init__(
            self,
            entityId: str,
            position: astronomer.SectorPosition,
            name: str,
            alternateNames: typing.Optional[typing.Collection[str]] = None,
            nameLanguages: typing.Optional[typing.Mapping[str, str]] = None, # Maps names to the language that name is in
            abbreviation: typing.Optional[str] = None,
            sectorLabel: typing.Optional[str] = None,
            subsectorNames: typing.Optional[typing.Mapping[str, str]] = None,
            worlds: typing.Optional[typing.Collection[astronomer.World]] = None,
            allegiances: typing.Optional[typing.Collection[astronomer.Allegiance]] = None,
            sophonts: typing.Optional[typing.Collection[astronomer.Sophont]] = None,
            routes: typing.Optional[typing.Collection[astronomer.Route]] = None,
            borders: typing.Optional[typing.Collection[astronomer.Border]] = None,
            regions: typing.Optional[typing.Collection[astronomer.Region]] = None,
            labels: typing.Optional[typing.Collection[astronomer.SectorLabel]] = None,
            selected: bool = False,
            tagging: typing.Optional[astronomer.SectorTagging] = None,
            credits: typing.Optional[str] = None,
            source: typing.Optional[astronomer.SectorSource] = None,
            products: typing.Optional[typing.Collection[astronomer.SectorSource]] = None
            ) -> None:
        super().__init__(entityId=entityId)

        common.validateObject(name='position', value=position, objectType=astronomer.SectorPosition)
        common.validateStr(name='name', value=name, allowEmpty=False)
        common.validateStrCollection(name='alternateNames', value=alternateNames, allowNone=True, allowEmptyValues=False)
        common.validateStrMapping(name='nameLanguages', value=nameLanguages, allowNone=True, allowEmptyKeys=False, allowEmptyValues=False)
        common.validateStr(name='abbreviation', value=abbreviation, allowEmpty=False, allowNone=True)
        common.validateStr(name='sectorLabel', value=sectorLabel, allowEmpty=False, allowNone=True)
        common.validateStrMapping(name='subsectorNames', value=subsectorNames, allowNone=True, allowEmptyKeys=False, allowEmptyValues=False, validationFn=Sector._validateSubsectorCode)
        common.validateCollection(name='worlds', value=worlds, elementType=astronomer.World, allowNone=True)
        common.validateCollection(name='allegiances', value=allegiances, elementType=astronomer.Allegiance, allowNone=True)
        common.validateCollection(name='sophonts', value=sophonts, elementType=astronomer.Sophont, allowNone=True)
        common.validateCollection(name='routes', value=routes, elementType=astronomer.Route, allowNone=True)
        common.validateCollection(name='borders', value=borders, elementType=astronomer.Border, allowNone=True)
        common.validateCollection(name='regions', value=regions, elementType=astronomer.Region, allowNone=True)
        common.validateCollection(name='labels', value=labels, elementType=astronomer.SectorLabel, allowNone=True)
        common.validateBool(name='selected', value=selected)
        common.validateObject(name='tagging', value=tagging, objectType=astronomer.SectorTagging, allowNone=True)
        common.validateStr(name='credits', value=credits, allowEmpty=False, allowNone=True)
        common.validateObject(name='source', value=source, objectType=astronomer.SectorSource, allowNone=True)
        common.validateCollection(name='products', value=products, elementType=astronomer.SectorSource, allowNone=True)

        self._position = position
        self._name = name
        self._alternateNames = list(alternateNames) if alternateNames else []
        self._nameLanguages = dict(nameLanguages) if nameLanguages else {}
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

        self._subsectorCodeToWorldsMap = {}
        for world in self._worlds:
            hex = world.hex()
            subsectorCode = hex.subsectorCode()

            subsectorWorlds = self._subsectorCodeToWorldsMap.get(subsectorCode)
            if not subsectorWorlds:
                subsectorWorlds = []
                self._subsectorCodeToWorldsMap[subsectorCode] = subsectorWorlds
            subsectorWorlds.append(world)

        self._allegianceCodeMap: typing.Dict[str, astronomer.Allegiance] = {}
        for allegiance in self._allegiances:
            self._allegianceCodeMap[allegiance.code()] = allegiance

        self._idToEntityMap: typing.Dict[str, astronomer.Entity] = {}
        for entity in itertools.chain(self._worlds, self._borders, self._regions, self._routes, self._labels):
            self._idToEntityMap[entity.entityId()] = entity

    def position(self) -> astronomer.SectorPosition:
        return self._position

    def name(self) -> str:
        return self._name

    def alternateNames(self) -> typing.Sequence[str]:
        return common.ConstSequenceRef(self._alternateNames)

    def nameLanguage(self, name: str) -> typing.Optional[str]:
        return self._nameLanguages.get(name)

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
            subsectorCode: typing.Optional[str] = None
            ) -> typing.Collection[astronomer.World]:
        worlds = self._worlds if subsectorCode is None else self._subsectorCodeToWorldsMap.get(subsectorCode)
        if not worlds:
            return []
        return common.ConstCollectionRef(worlds)

    def allegiances(self) -> typing.Collection[astronomer.Allegiance]:
        return common.ConstCollectionRef(self._allegiances)

    def sophonts(self) -> typing.Collection[astronomer.Sophont]:
        return common.ConstCollectionRef(self._sophonts)

    def allegianceByCode(self, code: str) -> typing.Optional[astronomer.Allegiance]:
        return self._allegianceCodeMap.get(code)

    def routes(self) -> typing.Collection[astronomer.Route]:
        return common.ConstCollectionRef(self._routes)

    def borders(self) -> typing.Collection[astronomer.Border]:
        return common.ConstCollectionRef(self._borders)

    def regions(self) -> typing.Collection[astronomer.Region]:
        return common.ConstCollectionRef(self._regions)

    def labels(self) -> typing.Collection[astronomer.SectorLabel]:
        return common.ConstCollectionRef(self._labels)

    def entities(self) -> typing.Collection[astronomer.Entity]:
        return common.ConstCollectionRef(self._idToEntityMap.values())

    # The concept of 'selected' comes from Traveller Map and what it is isn't
    # exactly clear. The only thing I've noticed it do is when rendering if
    # it's configured to only show some sector names, it only shows the names
    # for sectors that are selected.
    def selected(self) -> bool:
        return self._selected

    def tagging(self) -> typing.Optional[astronomer.SectorTagging]:
        return self._tagging

    def hasTag(self, tag: str) -> bool:
        if self._tagging is None:
            return False
        return self._tagging.contains(tag)

    def credits(self) -> typing.Optional[str]:
        return self._credits

    def source(self) -> typing.Optional[astronomer.SectorSource]:
        return self._source

    def products(self) -> typing.Collection[astronomer.SectorSource]:
        return common.ConstCollectionRef(self._products)

    def subsectorNames(self) -> typing.Collection[str]:
        return common.ConstCollectionRef(self._subsectorCodeToNameMap.values())

    @staticmethod
    def _validateSubsectorCode(
            name: str,
            subsectorCode: str,
            subsectorName: str
            ) -> None:
        if subsectorCode not in astronomer.SubsectorCodes:
            raise ValueError(f'{name} key must be a subsector code in the range A-P')