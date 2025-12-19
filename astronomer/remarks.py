import astronomer
import common
import logging
import multiverse
import typing

class WorldReference(object):
    def __init__(
            self,
            hexX: int,
            hexY: int,
            sectorAbbreviation: typing.Optional[str] = None # None means current system
            ) -> None:
        self._hexX = hexX
        self._hexY = hexY
        self._sectorAbbreviation = sectorAbbreviation

    def hexX(self) -> int:
        return self._hexX

    def hexY(self) -> int:
        return self._hexY

    def sectorAbbreviation(self) -> typing.Optional[str]:
        return self._sectorAbbreviation

class SophontPopulation(object):
    def __init__(
            self,
            code: str,
            name: str,
            percentage: typing.Optional[int], # None means die back
            isHomeWorld: bool,
            isMajorRace: bool
            ) -> None:
        self._code = code
        self._name = name
        self._percentage = percentage
        self._isHomeWorld = isHomeWorld
        self._isMajorRace = isMajorRace

    def code(self) -> int:
        return self._code

    def name(self) -> int:
        return self._name

    def percentage(self) -> typing.Optional[int]:
        return self._percentage

    def isHomeWorld(self) -> bool:
        return self._isHomeWorld

    def isMajorRace(self) -> bool:
        return self._isMajorRace

class Remarks(object):
    def __init__(
            self,
            zone: astronomer.ZoneType,
            dbTradeCodes: typing.Optional[typing.Collection[multiverse.DbTradeCode]],
            dbSophonts: typing.Optional[typing.Collection[multiverse.DbSophont]],
            dbPopulations: typing.Optional[typing.Collection[multiverse.DbSophontPopulation]],
            dbRulingAllegiances: typing.Optional[typing.Collection[multiverse.DbRulingAllegiance]],
            dbOwningSystems: typing.Optional[typing.Collection[multiverse.DbOwningSystem]],
            dbColonySystems: typing.Optional[typing.Collection[multiverse.DbColonySystem]],
            dbResearchStations: typing.Optional[typing.Collection[multiverse.DbResearchStation]],
            dbCustomRemarks: typing.Optional[typing.Collection[multiverse.DbCustomRemark]]
            ) -> None:
        self._zone = zone
        self._tradeCodes = common.OrderedSet[astronomer.TradeCode]()
        self._rulingAllegiances = list[str]()
        self._owningWorlds = list[WorldReference]()
        self._colonyWorlds = list[WorldReference]()
        self._researchStations = common.OrderedSet[str]()
        self._sophontPopulations = list[SophontPopulation]()
        self._customRemarks = common.OrderedSet[str]()
        self._string = None

        self._processTradeCodes(dbCodes=dbTradeCodes)
        self._processSophonts(dbSophonts=dbSophonts, dbPopulations=dbPopulations)
        self._processRulingAllegiances(dbAllegiances=dbRulingAllegiances)
        self._processOwningSystems(dbSystems=dbOwningSystems)
        self._processColonySystems(dbSystems=dbColonySystems)
        self._processResearchStations(dbStations=dbResearchStations)
        self._processCustomRemarks(dbRemarks=dbCustomRemarks)

        # Add custom trade codes for red/amber zone as it simplifies the
        # trade calculation logic as it can just deal with trade codes and
        # doesn't need to understand zones
        # TODO: I probably want to undo this hack before interactive editing
        # is added. I don't want the zone to be written to the database in the
        # remarks as it'd duplication of information. I also don't want to
        # be presenting them to the user as trade codes as they aren't. It might
        # make sense to do it now so I don't forget
        if self._zone == astronomer.ZoneType.AmberZone:
            self._tradeCodes.add(astronomer.TradeCode.AmberZone)
        elif self._zone == astronomer.ZoneType.RedZone:
            self._tradeCodes.add(astronomer.TradeCode.RedZone)

    def string(self) -> str:
        if self._string is None:
            self._string = self._generateRemarksString()
        return self._string

    def isEmpty(self) -> bool:
        return len(self.string()) == 0

    def tradeCodes(self) -> typing.Collection[astronomer.TradeCode]:
        return self._tradeCodes

    def hasTradeCode(
            self,
            tradeCode: astronomer.TradeCode
            ) -> bool:
        return tradeCode in self._tradeCodes

    def sophonts(self) -> typing.Collection[SophontPopulation]:
        return self._sophontPopulations

    # NOTE: This includes die back sophonts
    def sophontCount(self) -> int:
        return len(self._sophontPopulations)

    def rulingAllegiances(self) -> typing.Optional[str]:
        return self._rulingAllegiances

    def ownerCount(self) -> int:
        return len(self._owningWorlds)

    def ownerWorlds(self) -> typing.Collection[WorldReference]:
        return self._owningWorlds

    def colonyCount(self) -> int:
        return len(self._colonyWorlds)

    def colonyWorlds(self) -> typing.Collection[WorldReference]:
        return self._colonyWorlds

    def researchStations(self) -> typing.Optional[str]:
        return self._researchStations

    def researchStationCount(self) -> int:
        return len(self._researchStations)

    def hasResearchStation(self, code: str) -> bool:
        return code in self._researchStations

    def customRemarks(self) -> typing.Collection[str]:
        return self._customRemarks

    def hasCustomRemark(self, remark: str) -> bool:
        return remark in self._customRemarks

    def _processTradeCodes(
            self,
            dbCodes: typing.Optional[typing.Collection[multiverse.DbTradeCode]]
            ) -> None:
        if not dbCodes:
            return

        for dbCode in dbCodes:
            tradeCode = astronomer.tradeCode(tradeCodeString=dbCode.code())
            if not tradeCode:
                # TODO: Should log this
                continue
            self._tradeCodes.add(tradeCode)

    def _processSophonts(
            self,
            dbSophonts: typing.Optional[typing.Collection[multiverse.DbSophont]],
            dbPopulations: typing.Optional[typing.Collection[multiverse.DbSophontPopulation]]
            ) -> None:
        if not dbPopulations:
            return

        if not dbSophonts:
            raise ValueError('Sophont populations supplied without sophonts')

        # TODO: Generating this map each time is inefficient
        sophontMap = {s.id():s for s in dbSophonts}
        for dbPopulation in dbPopulations:
            dbSophont = sophontMap.get(dbPopulation.sophontId())
            if not dbSophont:
                raise ValueError(f'No sophont with id {dbPopulation.sophontId()} for population {dbPopulation.id()}')

            self._sophontPopulations.append(SophontPopulation(
                code=dbSophont.code(),
                name=dbSophont.name(),
                percentage=dbPopulation.percentage(),
                isHomeWorld=dbPopulation.isHomeWorld(),
                isMajorRace=dbSophont.isMajor()))

    def _processRulingAllegiances(
            self,
            dbAllegiances: typing.Optional[typing.Collection[multiverse.DbRulingAllegiance]]
            ) -> None:
        if not dbAllegiances:
            return

        for dbAllegiance in dbAllegiances:
            self._rulingAllegiances.append(dbAllegiance.allegiance().code())

    def _processOwningSystems(
            self,
            dbSystems: typing.Optional[typing.Collection[multiverse.DbOwningSystem]]
            ) -> None:
        if not dbSystems:
            return

        for dbSystem in dbSystems:
            self._owningWorlds.append(WorldReference(
                hexX=dbSystem.hexX(),
                hexY=dbSystem.hexY(),
                sectorAbbreviation=dbSystem.sectorCode()))

    def _processColonySystems(
            self,
            dbSystems: typing.Optional[typing.Collection[multiverse.DbColonySystem]]
            ) -> None:
        if not dbSystems:
            return

        for dbSystem in dbSystems:
            self._colonyWorlds.append(WorldReference(
                hexX=dbSystem.hexX(),
                hexY=dbSystem.hexY(),
                sectorAbbreviation=dbSystem.sectorCode()))

    def _processResearchStations(
            self,
            dbStations: typing.Optional[typing.Collection[multiverse.DbResearchStation]]
            ) -> None:
        if not dbStations:
            return

        for dbStation in dbStations:
            self._researchStations.add(dbStation.code())

    def _processCustomRemarks(
            self,
            dbRemarks: typing.Optional[typing.Collection[multiverse.DbCustomRemark]]
            ) -> None:
        if not dbRemarks:
            return

        for dbRemark in dbRemarks:
            self._customRemarks.add(dbRemark.remark())

    def _generateRemarksString(self) -> str:
        tradeCodes = []
        majorRaceHomeWorlds = []
        minorRaceHomeWorlds = []
        sophontPopulations = []
        dieBackSophonts = []
        owningSystems = []
        colonySystems = []

        for tradeCode in self._tradeCodes:
            tradeCodes.append(astronomer.tradeCodeString(tradeCode))

        for sophont in self._sophontPopulations:
            if sophont.percentage() is None:
                dieBackSophonts.append(sophont.name())
            elif sophont.isHomeWorld():
                if sophont.isMajorRace():
                    majorRaceHomeWorlds.append((sophont.name(), sophont.percentage()))
                else:
                    minorRaceHomeWorlds.append((sophont.name(), sophont.percentage()))
            else:
                sophontPopulations.append((sophont.code(), sophont.percentage()))

        for owner in self._owningWorlds:
            owningSystems.append((owner.hexX(), owner.hexY(), owner.sectorAbbreviation()))

        for colony in self._colonyWorlds:
            colonySystems.append((colony.hexX(), colony.hexY(), colony.sectorAbbreviation()))

        return multiverse.formatSystemRemarksString(
            tradeCodes=tradeCodes,
            majorRaceHomeWorlds=majorRaceHomeWorlds,
            minorRaceHomeWorlds=minorRaceHomeWorlds,
            sophontPopulations=sophontPopulations,
            dieBackSophonts=dieBackSophonts,
            owningSystems=owningSystems,
            colonySystems=colonySystems,
            rulingAllegiances=self._rulingAllegiances,
            researchStations=self._researchStations,
            customRemarks=self._customRemarks)