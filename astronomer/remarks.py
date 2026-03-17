import astronomer
import common
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

class Remarks(object):
    def __init__(
            self,
            tradeCodes: typing.Optional[typing.Collection[traveller.TradeCode]] = None,
            sophontPopulations: typing.Optional[typing.Collection[astronomer.SophontPopulation]] = None,
            rulingAllegiances: typing.Optional[typing.Collection[str]] = None,
            owningSystems: typing.Optional[typing.Collection[WorldReference]] = None,
            colonySystems: typing.Optional[typing.Collection[WorldReference]] = None,
            researchStations: typing.Optional[typing.Collection[str]] = None,
            customRemarks: typing.Optional[typing.Collection[str]] = None
            ) -> None:
        self._tradeCodes = common.OrderedSet(tradeCodes) if tradeCodes else common.OrderedSet()
        self._sophontPopulationMap = {p.code(): p for p in sophontPopulations} if sophontPopulations else {}
        self._rulingAllegiances = list(rulingAllegiances) if rulingAllegiances else []
        self._owningWorlds = list(owningSystems) if owningSystems else []
        self._colonyWorlds = list(colonySystems) if colonySystems else []
        self._researchStations = common.OrderedSet(researchStations) if researchStations else common.OrderedSet()
        self._customRemarks = common.OrderedSet(customRemarks) if customRemarks else common.OrderedSet()

        self._string = None

    def tradeCodes(self) -> typing.Collection[traveller.TradeCode]:
        return self._tradeCodes

    def hasTradeCode(
            self,
            tradeCode: traveller.TradeCode
            ) -> bool:
        return tradeCode in self._tradeCodes

    def sophonts(self) -> typing.Collection[astronomer.SophontPopulation]:
        return self._sophontPopulationMap.values()

    def hasSophont(self, code: str) -> bool:
        return code in self._sophontPopulationMap

    # NOTE: This includes die back sophonts
    def sophontCount(self) -> int:
        return len(self._sophontPopulationMap)

    def rulingAllegiances(self) -> typing.Optional[astronomer.Allegiance]:
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

    def string(self) -> str:
        if self._string is not None:
            return self._string

        tradeCodes = []
        majorRaceHomeWorlds = []
        minorRaceHomeWorlds = []
        sophontPopulations = []
        dieBackSophonts = []
        owningSystems = []
        colonySystems = []
        rulingAllegiances = []

        for tradeCode in self._tradeCodes:
            tradeCodes.append(traveller.tradeCodeString(tradeCode))
        tradeCodes.sort()

        for population in self._sophontPopulationMap.values():
            # NOTE: Home world and die back checks are intentionally separate so
            # that a sophonts home world can be marked as die back if they user
            # wants. If it is marked as die back, any population other than None
            # doesn't really make sense but I'm not doing anything to prevent it.
            if population.isHomeWorld():
                if population.isMajorRace():
                    majorRaceHomeWorlds.append((population.name(), population.percentage()))
                else:
                    minorRaceHomeWorlds.append((population.name(), population.percentage()))

            if population.isDieBack():
                dieBackSophonts.append(population.name())
            elif not population.isHomeWorld():
                # It's not die back and not a home world so just add a standard
                # population entry
                sophontPopulations.append((population.code(), population.percentage()))

        for owner in self._owningWorlds:
            owningSystems.append((owner.hexX(), owner.hexY(), owner.sectorAbbreviation()))

        for colony in self._colonyWorlds:
            colonySystems.append((colony.hexX(), colony.hexY(), colony.sectorAbbreviation()))

        for allegiance in self._rulingAllegiances:
            rulingAllegiances.append(allegiance.code())

        self._string = survey.formatSystemRemarksString(
            tradeCodes=tradeCodes,
            majorRaceHomeWorlds=majorRaceHomeWorlds,
            minorRaceHomeWorlds=minorRaceHomeWorlds,
            sophontPopulations=sophontPopulations,
            dieBackSophonts=dieBackSophonts,
            owningSystems=owningSystems,
            colonySystems=colonySystems,
            rulingAllegiances=rulingAllegiances,
            researchStations=self._researchStations,
            customRemarks=self._customRemarks)
        return self._string

    def isEmpty(self) -> bool:
        return len(self.string()) == 0
