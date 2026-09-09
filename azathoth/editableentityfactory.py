import astronomer
import azathoth
import traveller
import typing

class EditableEntityFactory(astronomer.EntityFactoryInterface):
    def createUniverse(
            self,
            universeId: str,
            milieu: astronomer.Milieu,
            allegiances: typing.Collection[astronomer.Allegiance],
            sophonts: typing.Collection[astronomer.Sophont],
            sectors: typing.Collection[astronomer.Sector],
            worlds: typing.Collection[astronomer.World],
            routes: typing.Collection[astronomer.Route],
            labels: typing.Collection[astronomer.MapLabel],
            vectors: typing.Collection[astronomer.MapVector]
            ) -> astronomer.Universe:
        return azathoth.EditableUniverse(
            universeId=universeId,
            milieu=milieu,
            allegiances=allegiances,
            sophonts=sophonts,
            sectors=sectors,
            worlds=worlds,
            routes=routes,
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
        return azathoth.EditableAllegiance(
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

    def createSophont(
            self,
            entityId: str,
            name: str,
            code: str,
            isMajor: bool
            ) -> astronomer.Sophont:
        return azathoth.EditableSophont(
            entityId=entityId,
            name=name,
            code=code,
            isMajor=isMajor)

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
            borders: typing.Optional[typing.Iterable[astronomer.Border]] = None,
            regions: typing.Optional[typing.Iterable[astronomer.Region]] = None,
            labels: typing.Optional[typing.Iterable[astronomer.SectorLabel]] = None,
            selected: bool = False,
            tagging: typing.Optional[astronomer.SectorTagging] = None,
            credits: typing.Optional[str] = None,
            source: typing.Optional[astronomer.SectorSource] = None,
            products: typing.Optional[typing.Iterable[astronomer.SectorSource]] = None
            ) -> astronomer.Sector:
        return azathoth.EditableSector(
            entity=entityId,
            position=position,
            name=name,
            alternateNames=alternateNames,
            nameLanguages=nameLanguages,
            abbreviation=abbreviation,
            sectorLabel=sectorLabel,
            subsectorNames=subsectorNames,
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
        return azathoth.EditableWorld(
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
        return azathoth.EditableRoute(
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
        return azathoth.EditableBorder(
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
        return azathoth.EditableRegion(
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
        return azathoth.EditableSectorLabel(
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
        return azathoth.EditableMapLabel(
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
        return azathoth.EditableMapVector(
            entityId=entityId,
            points=points,
            layer=layer,
            closed=closed)