import astronomer
import common
import logging
import multiverse
import survey
import traveller
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
            percentage: typing.Optional[int], # None means unknown percentage
            isMajorRace: bool,
            isHomeWorld: bool,
            isDieBack: bool
            ) -> None:
        self._code = code
        self._name = name
        self._percentage = percentage
        self._isMajorRace = isMajorRace
        self._isHomeWorld = isHomeWorld
        self._isDieBack = isDieBack

    def code(self) -> int:
        return self._code

    def name(self) -> int:
        return self._name

    def percentage(self) -> typing.Optional[int]:
        return self._percentage

    def isMajorRace(self) -> bool:
        return self._isMajorRace

    def isHomeWorld(self) -> bool:
        return self._isHomeWorld

    def isDieBack(self) -> bool:
        return self._isDieBack

class Remarks(object):
    def __init__(
            self,
            zone: astronomer.ZoneType,
            uwp: astronomer.UWP,
            dbTradeCodes: typing.Optional[typing.Collection[multiverse.DbTradeCode]],
            dbSophontPopulations: typing.Optional[typing.Collection[multiverse.DbSophontPopulation]],
            dbRulingAllegiances: typing.Optional[typing.Collection[multiverse.DbRulingAllegiance]],
            dbOwningSystems: typing.Optional[typing.Collection[multiverse.DbOwningSystem]],
            dbColonySystems: typing.Optional[typing.Collection[multiverse.DbColonySystem]],
            dbResearchStations: typing.Optional[typing.Collection[multiverse.DbResearchStation]],
            dbCustomRemarks: typing.Optional[typing.Collection[multiverse.DbCustomRemark]]
            ) -> None:
        self._zone = zone
        self._uwp = uwp
        self._tradeCodes = common.OrderedSet[traveller.TradeCode]()
        self._rulingAllegiances = list[str]()
        self._owningWorlds = list[WorldReference]()
        self._colonyWorlds = list[WorldReference]()
        self._researchStations = common.OrderedSet[str]()
        self._sophontPopulationMap = dict[str, SophontPopulation]() # Map Sophont code to sophont
        self._customRemarks = common.OrderedSet[str]()

        self._ruleSystemTradeCodesMap: typing.Dict[traveller.RuleSystem, common.OrderedSet[str]] = {}
        self._remarkStringMap: typing.Dict[typing.Optional[traveller.RuleSystem], str] = {}

        self._processTradeCodes(dbCodes=dbTradeCodes)
        self._processSophontPopulations(dbPopulations=dbSophontPopulations)
        self._processRulingAllegiances(dbAllegiances=dbRulingAllegiances)
        self._processOwningSystems(dbSystems=dbOwningSystems)
        self._processColonySystems(dbSystems=dbColonySystems)
        self._processResearchStations(dbStations=dbResearchStations)
        self._processCustomRemarks(dbRemarks=dbCustomRemarks)

    def tradeCodes(
            self,
            rules: typing.Optional[traveller.Rules] = None
            ) -> typing.Collection[traveller.TradeCode]:
        if rules is not None and rules.regenerateTradeCodes():
            return self._ruleSystemTradeCodes(rules.system())

        return self._tradeCodes

    def hasTradeCode(
            self,
            tradeCode: traveller.TradeCode,
            rules: typing.Optional[traveller.Rules] = None
            ) -> bool:
        if rules is not None and rules.regenerateTradeCodes():
            tradeCodes = self._ruleSystemTradeCodes(rules.system())
            return tradeCode in tradeCodes

        return tradeCode in self._tradeCodes

    def sophonts(self) -> typing.Collection[SophontPopulation]:
        return self._sophontPopulationMap.values()

    def hasSophont(self, code: str) -> bool:
        return code in self._sophontPopulationMap

    # NOTE: This includes die back sophonts
    def sophontCount(self) -> int:
        return len(self._sophontPopulationMap)

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

    def string(
            self,
            rules: typing.Optional[traveller.Rules] = None
            ) -> str:
        ruleSystem = rules.system() if rules and rules.regenerateTradeCodes() else None
        string = self._remarkStringMap.get(ruleSystem)
        if string is not None:
            return string

        tradeCodes = []
        majorRaceHomeWorlds = []
        minorRaceHomeWorlds = []
        sophontPopulations = []
        dieBackSophonts = []
        owningSystems = []
        colonySystems = []

        if ruleSystem is not None:
            for tradeCode in self._ruleSystemTradeCodes(ruleSystem=ruleSystem):
                tradeCodes.append(traveller.tradeCodeString(tradeCode))
        else:
            for tradeCode in self._tradeCodes:
                tradeCodes.append(traveller.tradeCodeString(tradeCode))
        tradeCodes.sort()

        for sophont in self._sophontPopulationMap.values():
            # NOTE: Home world and die back checks are intentionally separate so
            # that a sophonts home world can be marked as die back if they user
            # wants. If it is marked as die back, any population other than None
            # doesn't really make sense but I'm not doing anything to prevent it.
            if sophont.isHomeWorld():
                if sophont.isMajorRace():
                    majorRaceHomeWorlds.append((sophont.name(), sophont.percentage()))
                else:
                    minorRaceHomeWorlds.append((sophont.name(), sophont.percentage()))

            if sophont.isDieBack():
                dieBackSophonts.append(sophont.name())
            elif not sophont.isHomeWorld():
                # It's not die back and not a home world so just add a standard
                # population entry
                sophontPopulations.append((sophont.code(), sophont.percentage()))

        for owner in self._owningWorlds:
            owningSystems.append((owner.hexX(), owner.hexY(), owner.sectorAbbreviation()))

        for colony in self._colonyWorlds:
            colonySystems.append((colony.hexX(), colony.hexY(), colony.sectorAbbreviation()))

        string = survey.formatSystemRemarksString(
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
        self._remarkStringMap[ruleSystem] = string
        return string

    def isEmpty(
            self,
            rules: typing.Optional[traveller.Rules] = None
            ) -> bool:
        return len(self.string(rules=rules)) == 0

    def _processTradeCodes(
            self,
            dbCodes: typing.Optional[typing.Collection[multiverse.DbTradeCode]]
            ) -> None:
        if not dbCodes:
            return

        for dbCode in dbCodes:
            tradeCode = traveller.tradeCode(tradeCodeString=dbCode.code())
            if not tradeCode:
                logging.warning(f'Ignoring unknown Trade Code {dbCode.code()}')
                continue
            self._tradeCodes.add(tradeCode)

    def _processSophontPopulations(
            self,
            dbPopulations: typing.Optional[typing.Collection[multiverse.DbSophontPopulation]]
            ) -> None:
        if not dbPopulations:
            return

        for dbPopulation in dbPopulations:
            dbSophont = dbPopulation.sophont()
            sophont = SophontPopulation(
                code=dbSophont.code(),
                name=dbSophont.name(),
                percentage=dbPopulation.percentage(),
                isMajorRace=dbSophont.isMajor(),
                isHomeWorld=dbPopulation.isHomeWorld(),
                isDieBack=dbPopulation.isDieBack())
            self._sophontPopulationMap[sophont.code()] = sophont

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
                sectorAbbreviation=dbSystem.sectorAbbreviation()))

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
                sectorAbbreviation=dbSystem.sectorAbbreviation()))

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

    def _ruleSystemTradeCodes(
            self,
            ruleSystem: traveller.RuleSystem
            ) -> common.OrderedSet:
        tradeCodes = self._ruleSystemTradeCodesMap.get(ruleSystem)
        if tradeCodes is not None:
            return tradeCodes

        tradeCodes = traveller.calculateMongooseTradeCodes(
            uwp=self._uwp.string(),
            ruleSystem=ruleSystem,
            # Merge the trade codes stored in the DB so any non-calculated trade
            # codes (sector capital, penal colony etc) are maintained
            mergeTradeCodes=self._tradeCodes)
        self._ruleSystemTradeCodesMap[ruleSystem] = tradeCodes
        return tradeCodes
