import astronomer
import traveller
import typing

class EditableWorld(astronomer.World):
    def __init__(
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
            ) -> None:
        super().__init__(
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
        self._sectorId = None

    def sectorId(self) -> typing.Optional[str]:
        return self._sectorId

    def setSectorId(self, sectorId: str) -> None:
        self._sectorId = sectorId