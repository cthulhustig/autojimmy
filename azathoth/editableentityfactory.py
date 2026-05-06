import astronomer
import azathoth
import traveller
import typing

class EditableEntityFactory(astronomer.EntityFactoryInterface):
    def createUniverse(
            self,
            id: str,
            sectors: typing.Collection[astronomer.Sector], # Sectors for all milieu
            placeholderMilieu: typing.Optional[astronomer.Milieu] = None
            ) -> astronomer.Universe:
        return azathoth.EditableUniverse(
            id=id,
            sectors=sectors,
            placeholderMilieu=placeholderMilieu)

    def createSector(
            self,
            id: str,
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
        return azathoth.EditableSector(
            id=id,
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
            id: str,
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
        return azathoth.EditableWorld(
            id=id,
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
            id: str,
            startHex: astronomer.HexPosition,
            endHex: astronomer.HexPosition,
            allegiance: typing.Optional[astronomer.Allegiance] = None,
            routeType: typing.Optional[str] = None,
            style: typing.Optional[astronomer.LineStyle] = None,
            colour: typing.Optional[str] = None,
            width: typing.Optional[float] = None
            ) -> astronomer.Route:
        return azathoth.EditableRoute(
            id=id,
            startHex=startHex,
            endHex=endHex,
            allegiance=allegiance,
            routeType=routeType,
            style=style,
            colour=colour,
            width=width)

    def createBorder(
            self,
            id: str,
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
        return azathoth.EditableBorder(
            id=id,
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
            id: str,
            hexList: typing.Iterable[astronomer.HexPosition],
            colour: typing.Optional[str] = None,
            label: typing.Optional[str] = None,
            labelWorldX: typing.Optional[float] = None,
            labelWorldY: typing.Optional[float] = None,
            showLabel: bool = True,
            wrapLabel: bool = False
            ) -> astronomer.Region:
        return azathoth.EditableRegion(
            id=id,
            hexList=hexList,
            colour=colour,
            label=label,
            labelWorldX=labelWorldX,
            labelWorldY=labelWorldY,
            showLabel=showLabel,
            wrapLabel=wrapLabel)

    def createLabel(
            self,
            id: str,
            text: str,
            worldX: float,
            worldY: float,
            colour: typing.Optional[str] = None,
            size: typing.Optional[astronomer.Label.Size] = None,
            wrap: bool = False
            ) -> astronomer.Label:
        return azathoth.EditableLabel(
            id=id,
            text=text,
            worldX=worldX,
            worldY=worldY,
            colour=colour,
            size=size,
            wrap=wrap)
