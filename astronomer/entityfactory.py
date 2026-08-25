import astronomer
import traveller
import typing

class EntityFactoryInterface(object):
    def createUniverse(
            self,
            universeId: str,
            milieu: astronomer.Milieu,
            allegiances: typing.Collection[astronomer.Allegiance],
            sectors: typing.Collection[astronomer.Sector],
            worlds: typing.Collection[astronomer.World],
            labels: typing.Collection[astronomer.MapLabel],
            vectors: typing.Collection[astronomer.VectorLayer]
            ) -> astronomer.Universe:
        raise NotImplementedError(f'{type(self)} is derived from EntityFactoryInterface so must implement createUniverse')

    def createAllegiance(
            self,
            entityId: str,
            name: str,
            code: str,
            legacyCode: typing.Optional[str] = None,
            baseCode: typing.Optional[str] = None,
            routeColour: typing.Optional[str] = None,
            routeStyle: typing.Optional[astronomer.LineStyle] = None,
            routeWidth: typing.Optional[float] = None,
            borderColour: typing.Optional[str] = None,
            borderStyle: typing.Optional[astronomer.LineStyle] = None
            ) -> astronomer.Allegiance:
        raise NotImplementedError(f'{type(self)} is derived from EntityFactoryInterface so must implement createAllegiance')

    def createSector(
            self,
            entityId: str,
            position: astronomer.SectorPosition,
            name: str,
            alternateNames: typing.Optional[typing.Iterable[str]] = None,
            nameLanguages: typing.Optional[typing.Mapping[str, str]] = None, # Maps names to the language that name is in
            abbreviation: typing.Optional[str] = None,
            sectorLabel: typing.Optional[str] = None,
            subsectorNames: typing.Optional[typing.Mapping[str, str]] = None,
            worlds: typing.Optional[typing.Iterable[astronomer.World]] = None,
            sophonts: typing.Optional[typing.Iterable[astronomer.Sophont]] = None,
            routes: typing.Optional[typing.Iterable[astronomer.Route]] = None,
            borders: typing.Optional[typing.Iterable[astronomer.Border]] = None,
            regions: typing.Optional[typing.Iterable[astronomer.Region]] = None,
            labels: typing.Optional[typing.Iterable[astronomer.SectorLabel]] = None,
            selected: bool = False,
            tagging: typing.Optional[astronomer.SectorTagging] = None,
            credits: typing.Optional[str] = None,
            source: typing.Optional[astronomer.SectorSource] = None,
            products: typing.Optional[typing.Iterable[astronomer.SectorSource]] = None
            ) -> astronomer.Sector:
        raise NotImplementedError(f'{type(self)} is derived from EntityFactoryInterface so must implement createSector')

    def createWorld(
            self,
            entityId: str,
            hex: astronomer.HexPosition,
            name: str,
            isNameGenerated: bool,
            allegiance: typing.Optional[astronomer.Allegiance] = None,
            zone: typing.Optional[astronomer.ZoneType] = None,
            uwp: typing.Optional[astronomer.UWP] = None,
            economics: typing.Optional[astronomer.Economics] = None,
            culture: typing.Optional[astronomer.Culture] = None,
            nobilities: typing.Optional[astronomer.Nobilities] = None,
            bases: typing.Optional[astronomer.Bases] = None,
            systemWorlds: typing.Optional[int] = None,
            pbg: typing.Optional[astronomer.PBG] = None,
            stellar: typing.Optional[astronomer.Stellar] = None,
            tradeCodes: typing.Optional[typing.Collection[traveller.TradeCode]] = None,
            sophontPopulations: typing.Optional[typing.Collection[astronomer.SophontPopulation]] = None,
            rulingAllegiances: typing.Optional[typing.Collection[astronomer.Allegiance]] = None,
            owningWorldRefs: typing.Optional[typing.Collection[astronomer.WorldReference]] = None,
            colonyWorldRefs: typing.Optional[typing.Collection[astronomer.WorldReference]] = None,
            researchStations: typing.Optional[typing.Collection[str]] = None,
            customRemarks: typing.Optional[typing.Collection[str]] = None
            ) -> astronomer.World:
        raise NotImplementedError(f'{type(self)} is derived from EntityFactoryInterface so must implement createWorld')

    def createRoute(
            self,
            entityId: str,
            startHex: astronomer.HexPosition,
            endHex: astronomer.HexPosition,
            allegiance: typing.Optional[astronomer.Allegiance] = None,
            routeType: typing.Optional[str] = None,
            style: typing.Optional[astronomer.LineStyle] = None,
            colour: typing.Optional[str] = None,
            width: typing.Optional[float] = None
            ) -> astronomer.Route:
        raise NotImplementedError(f'{type(self)} is derived from EntityFactoryInterface so must implement createRoute')

    def createBorder(
            self,
            entityId: str,
            hexes: typing.Iterable[astronomer.HexPosition],
            allegiance: typing.Optional[astronomer.Allegiance] = None,
            style: typing.Optional[astronomer.LineStyle] = None,
            colour: typing.Optional[str] = None,
            label: typing.Optional[str] = None,
            labelWorldX: typing.Optional[float] = None,
            labelWorldY: typing.Optional[float] = None,
            showLabel: bool = True,
            wrapLabel: bool = False
            ) -> astronomer.Border:
        raise NotImplementedError(f'{type(self)} is derived from EntityFactoryInterface so must implement createBorder')

    def createRegion(
            self,
            entityId: str,
            hexes: typing.Iterable[astronomer.HexPosition],
            colour: typing.Optional[str] = None,
            label: typing.Optional[str] = None,
            labelWorldX: typing.Optional[float] = None,
            labelWorldY: typing.Optional[float] = None,
            showLabel: bool = True,
            wrapLabel: bool = False
            ) -> astronomer.Region:
        raise NotImplementedError(f'{type(self)} is derived from EntityFactoryInterface so must implement createRegion')

    def createSectorLabel(
            self,
            entityId: str,
            text: str,
            worldX: float,
            worldY: float,
            colour: typing.Optional[str] = None,
            size: typing.Optional[astronomer.LabelSize] = None,
            wrap: bool = False
            ) -> astronomer.SectorLabel:
        raise NotImplementedError(f'{type(self)} is derived from EntityFactoryInterface so must implement createSectorLabel')

    def createMapLabel(
            self,
            entityId: str,
            text: str,
            worldX: float,
            worldY: float,
            layer: astronomer.LabelLayer,
            alignment: typing.Optional[astronomer.TextAlignment] = None,
            colour: typing.Optional[str] = None,
            size: typing.Optional[astronomer.LabelSize] = None,
            rotation: typing.Optional[float] = None
            ) -> astronomer.MapLabel:
        raise NotImplementedError(f'{type(self)} is derived from EntityFactoryInterface so must implement createMapLabel')

    def createMapVector(
            self,
            entityId: str,
            points: typing.Sequence[typing.Tuple[float, float]],
            layer: astronomer.VectorLayer,
            closed: bool
            ) -> astronomer.MapVector:
        raise NotImplementedError(f'{type(self)} is derived from EntityFactoryInterface so must implement createMapVector')

class DefaultEntityFactory(EntityFactoryInterface):
    def createUniverse(
            self,
            universeId: str,
            milieu: astronomer.Milieu,
            allegiances: typing.Collection[astronomer.Allegiance],
            sectors: typing.Collection[astronomer.Sector],
            worlds: typing.Collection[astronomer.World],
            labels: typing.Collection[astronomer.MapLabel],
            vectors: typing.Collection[astronomer.MapVector]
            ) -> astronomer.Universe:
        return astronomer.Universe(
            universeId=universeId,
            milieu=milieu,
            allegiances=allegiances,
            sectors=sectors,
            worlds=worlds,
            labels=labels,
            vectors=vectors)

    def createAllegiance(
            self,
            entityId: str,
            name: str,
            code: str,
            legacyCode: typing.Optional[str] = None,
            baseCode: typing.Optional[str] = None,
            routeColour: typing.Optional[str] = None,
            routeStyle: typing.Optional[astronomer.LineStyle] = None,
            routeWidth: typing.Optional[float] = None,
            borderColour: typing.Optional[str] = None,
            borderStyle: typing.Optional[astronomer.LineStyle] = None
            ) -> astronomer.Allegiance:
        return astronomer.Allegiance(
            entityId=entityId,
            name=name,
            code=code,
            legacyCode=legacyCode,
            baseCode=baseCode,
            routeColour=routeColour,
            routeStyle=routeStyle,
            routeWidth=routeWidth,
            borderColour=borderColour,
            borderStyle=borderStyle)

    def createSector(
            self,
            entityId: str,
            position: astronomer.SectorPosition,
            name: str,
            alternateNames: typing.Optional[typing.Iterable[str]] = None,
            nameLanguages: typing.Optional[typing.Mapping[str, str]] = None, # Maps names to the language that name is in
            abbreviation: typing.Optional[str] = None,
            sectorLabel: typing.Optional[str] = None,
            subsectorNames: typing.Optional[typing.Mapping[str, str]] = None,
            worlds: typing.Optional[typing.Iterable[astronomer.World]] = None,
            sophonts: typing.Optional[typing.Iterable[astronomer.Sophont]] = None,
            routes: typing.Optional[typing.Iterable[astronomer.Route]] = None,
            borders: typing.Optional[typing.Iterable[astronomer.Border]] = None,
            regions: typing.Optional[typing.Iterable[astronomer.Region]] = None,
            labels: typing.Optional[typing.Iterable[astronomer.SectorLabel]] = None,
            selected: bool = False,
            tagging: typing.Optional[astronomer.SectorTagging] = None,
            credits: typing.Optional[str] = None,
            source: typing.Optional[astronomer.SectorSource] = None,
            products: typing.Optional[typing.Iterable[astronomer.SectorSource]] = None
            ) -> astronomer.Sector:
        return astronomer.Sector(
            entityId=entityId,
            position=position,
            name=name,
            alternateNames=alternateNames,
            nameLanguages=nameLanguages,
            abbreviation=abbreviation,
            sectorLabel=sectorLabel,
            subsectorNames=subsectorNames,
            worlds=worlds,
            sophonts=sophonts,
            routes=routes,
            borders=borders,
            regions=regions,
            labels=labels,
            selected=selected,
            tagging=tagging,
            credits=credits,
            source=source,
            products=products)

    def createWorld(
            self,
            entityId: str,
            hex: astronomer.HexPosition,
            name: str,
            isNameGenerated: bool,
            allegiance: typing.Optional[astronomer.Allegiance] = None,
            zone: typing.Optional[astronomer.ZoneType] = None,
            uwp: typing.Optional[astronomer.UWP] = None,
            economics: typing.Optional[astronomer.Economics] = None,
            culture: typing.Optional[astronomer.Culture] = None,
            nobilities: typing.Optional[astronomer.Nobilities] = None,
            bases: typing.Optional[astronomer.Bases] = None,
            systemWorlds: typing.Optional[int] = None,
            pbg: typing.Optional[astronomer.PBG] = None,
            stellar: typing.Optional[astronomer.Stellar] = None,
            tradeCodes: typing.Optional[typing.Collection[traveller.TradeCode]] = None,
            sophontPopulations: typing.Optional[typing.Collection[astronomer.SophontPopulation]] = None,
            rulingAllegiances: typing.Optional[typing.Collection[astronomer.Allegiance]] = None,
            owningWorldRefs: typing.Optional[typing.Collection[astronomer.WorldReference]] = None,
            colonyWorldRefs: typing.Optional[typing.Collection[astronomer.WorldReference]] = None,
            researchStations: typing.Optional[typing.Collection[str]] = None,
            customRemarks: typing.Optional[typing.Collection[str]] = None
            ) -> astronomer.World:
        return astronomer.World(
            entityId=entityId,
            hex=hex,
            name=name,
            isNameGenerated=isNameGenerated,
            allegiance=allegiance,
            zone=zone,
            uwp=uwp,
            economics=economics,
            culture=culture,
            nobilities=nobilities,
            bases=bases,
            systemWorlds=systemWorlds,
            pbg=pbg,
            stellar=stellar,
            tradeCodes=tradeCodes,
            sophontPopulations=sophontPopulations,
            rulingAllegiances=rulingAllegiances,
            owningWorldRefs=owningWorldRefs,
            colonyWorldRefs=colonyWorldRefs,
            researchStations=researchStations,
            customRemarks=customRemarks)

    def createRoute(
            self,
            entityId: str,
            startHex: astronomer.HexPosition,
            endHex: astronomer.HexPosition,
            allegiance: typing.Optional[astronomer.Allegiance] = None,
            routeType: typing.Optional[str] = None,
            style: typing.Optional[astronomer.LineStyle] = None,
            colour: typing.Optional[str] = None,
            width: typing.Optional[float] = None
            ) -> astronomer.Route:
        return astronomer.Route(
            entityId=entityId,
            startHex=startHex,
            endHex=endHex,
            allegiance=allegiance,
            routeType=routeType,
            style=style,
            colour=colour,
            width=width)

    def createBorder(
            self,
            entityId: str,
            hexes: typing.Iterable[astronomer.HexPosition],
            allegiance: typing.Optional[astronomer.Allegiance] = None,
            style: typing.Optional[astronomer.LineStyle] = None,
            colour: typing.Optional[str] = None,
            label: typing.Optional[str] = None,
            labelWorldX: typing.Optional[float] = None,
            labelWorldY: typing.Optional[float] = None,
            showLabel: bool = True,
            wrapLabel: bool = False
            ) -> astronomer.Border:
        return astronomer.Border(
            entityId=entityId,
            hexes=hexes,
            allegiance=allegiance,
            style=style,
            colour=colour,
            label=label,
            labelWorldX=labelWorldX,
            labelWorldY=labelWorldY,
            showLabel=showLabel,
            wrapLabel=wrapLabel)

    def createRegion(
            self,
            entityId: str,
            hexes: typing.Iterable[astronomer.HexPosition],
            colour: typing.Optional[str] = None,
            label: typing.Optional[str] = None,
            labelWorldX: typing.Optional[float] = None,
            labelWorldY: typing.Optional[float] = None,
            showLabel: bool = True,
            wrapLabel: bool = False
            ) -> astronomer.Region:
        return astronomer.Region(
            entityId=entityId,
            hexes=hexes,
            colour=colour,
            label=label,
            labelWorldX=labelWorldX,
            labelWorldY=labelWorldY,
            showLabel=showLabel,
            wrapLabel=wrapLabel)

    def createSectorLabel(
            self,
            entityId: str,
            text: str,
            worldX: float,
            worldY: float,
            colour: typing.Optional[str] = None,
            size: typing.Optional[astronomer.LabelSize] = None,
            wrap: bool = False
            ) -> astronomer.SectorLabel:
        return astronomer.SectorLabel(
            entityId=entityId,
            text=text,
            worldX=worldX,
            worldY=worldY,
            colour=colour,
            size=size,
            wrap=wrap)

    def createMapLabel(
            self,
            entityId: str,
            text: str,
            worldX: float,
            worldY: float,
            layer: astronomer.LabelLayer,
            alignment: typing.Optional[astronomer.TextAlignment] = None,
            colour: typing.Optional[str] = None,
            size: typing.Optional[astronomer.LabelSize] = None,
            rotation: typing.Optional[float] = None
            ) -> astronomer.MapLabel:
        return astronomer.MapLabel(
            entityId=entityId,
            text=text,
            worldX=worldX,
            worldY=worldY,
            layer=layer,
            alignment=alignment,
            colour=colour,
            size=size,
            rotation=rotation)

    def createMapVector(
            self,
            entityId: str,
            points: typing.Sequence[typing.Tuple[float, float]],
            layer: astronomer.VectorLayer,
            closed: bool
            ) -> astronomer.MapVector:
        return astronomer.MapVector(
            entityId=entityId,
            points=points,
            layer=layer,
            closed=closed)