import astronomer
import traveller
import typing

class EntityFactoryInterface(object):
    def createUniverse(
            self,
            universeId: str,
            sectors: typing.Collection[astronomer.Sector], # Sectors for all milieu
            placeholderMilieu: typing.Optional[astronomer.Milieu] = None
            ) -> astronomer.Universe:
        raise NotImplementedError(f'{type(self)} is derived from EntityFactoryInterface so must implement createUniverse')

    def createSector(
            self,
            entityId: str,
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
            ) -> astronomer.Sector:
        raise NotImplementedError(f'{type(self)} is derived from EntityFactoryInterface so must implement createSector')

    def createWorld(
            self,
            entityId: str,
            milieu: astronomer.Milieu,
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
            hexList: typing.Iterable[astronomer.HexPosition],
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
            hexList: typing.Iterable[astronomer.HexPosition],
            colour: typing.Optional[str] = None,
            label: typing.Optional[str] = None,
            labelWorldX: typing.Optional[float] = None,
            labelWorldY: typing.Optional[float] = None,
            showLabel: bool = True,
            wrapLabel: bool = False
            ) -> astronomer.Region:
        raise NotImplementedError(f'{type(self)} is derived from EntityFactoryInterface so must implement createRegion')

    def createLabel(
            self,
            entityId: str,
            text: str,
            worldX: float,
            worldY: float,
            colour: typing.Optional[str] = None,
            size: typing.Optional[astronomer.Label.Size] = None,
            wrap: bool = False
            ) -> astronomer.Label:
        raise NotImplementedError(f'{type(self)} is derived from EntityFactoryInterface so must implement createLabel')

class DefaultEntityFactory(EntityFactoryInterface):
    def createUniverse(
            self,
            universeId: str,
            sectors: typing.Collection[astronomer.Sector], # Sectors for all milieu
            placeholderMilieu: typing.Optional[astronomer.Milieu] = None
            ) -> astronomer.Universe:
        return astronomer.Universe(
            universeId=universeId,
            sectors=sectors,
            placeholderMilieu=placeholderMilieu)

    def createSector(
            self,
            entityId: str,
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
            ) -> astronomer.Sector:
        return astronomer.Sector(
            entityId=entityId,
            isCustom=isCustom,
            milieu=milieu,
            position=position,
            name=name,
            alternateNames=alternateNames,
            abbreviation=abbreviation,
            sectorLabel=sectorLabel,
            subsectorNames=subsectorNames,
            worlds=worlds,
            allegiances=allegiances,
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
            milieu: astronomer.Milieu,
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
            milieu=milieu,
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
            hexList: typing.Iterable[astronomer.HexPosition],
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
            hexList=hexList,
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
            hexList: typing.Iterable[astronomer.HexPosition],
            colour: typing.Optional[str] = None,
            label: typing.Optional[str] = None,
            labelWorldX: typing.Optional[float] = None,
            labelWorldY: typing.Optional[float] = None,
            showLabel: bool = True,
            wrapLabel: bool = False
            ) -> astronomer.Region:
        return astronomer.Region(
            entityId=entityId,
            hexList=hexList,
            colour=colour,
            label=label,
            labelWorldX=labelWorldX,
            labelWorldY=labelWorldY,
            showLabel=showLabel,
            wrapLabel=wrapLabel)

    def createLabel(
            self,
            entityId: str,
            text: str,
            worldX: float,
            worldY: float,
            colour: typing.Optional[str] = None,
            size: typing.Optional[astronomer.Label.Size] = None,
            wrap: bool = False
            ) -> astronomer.Label:
        return astronomer.Label(
            entityId=entityId,
            text=text,
            worldX=worldX,
            worldY=worldY,
            colour=colour,
            size=size,
            wrap=wrap)
