import astronomer
import common
import math
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

class World(object):
    def __init__(
            self,
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
            owningWorldRefs: typing.Optional[typing.Collection[WorldReference]] = None,
            colonyWorldRefs: typing.Optional[typing.Collection[WorldReference]] = None,
            researchStations: typing.Optional[typing.Collection[str]] = None,
            customRemarks: typing.Optional[typing.Collection[str]] = None
            ) -> None:
        self._milieu = milieu
        self._hex = hex
        self._name = name
        self._isNameGenerated = isNameGenerated
        self._allegiance = allegiance
        self._zone = zone
        self._uwp = uwp if uwp else astronomer.UWP()
        self._economics = economics if economics else astronomer.Economics()
        self._culture = culture if culture else astronomer.Culture()
        self._nobilities = nobilities if nobilities else astronomer.Nobilities()
        self._bases = bases if bases else astronomer.Bases()
        self._systemWorlds = systemWorlds
        self._pbg = pbg if pbg else astronomer.PBG()
        self._stellar = stellar if stellar else astronomer.Stellar()
        self._tradeCodes = common.OrderedSet(tradeCodes) if tradeCodes else common.OrderedSet()
        self._sophontPopulationMap = {p.code(): p for p in sophontPopulations} if sophontPopulations else {}
        self._rulingAllegiances = list(rulingAllegiances) if rulingAllegiances else []
        self._owningWorldRefs = list(owningWorldRefs) if owningWorldRefs else []
        self._colonyWorldRefs = list(colonyWorldRefs) if colonyWorldRefs else []
        self._researchStations = common.OrderedSet(researchStations) if researchStations else common.OrderedSet()
        self._customRemarks = common.OrderedSet(customRemarks) if customRemarks else common.OrderedSet()

        self._isAnomaly = '{Anomaly}' in self._customRemarks
        self._isFuelCache = '{Fuel}' in self._customRemarks

        self._remarksString = None # Calculated on demand

    def milieu(self) -> astronomer.Milieu:
        return self._milieu

    def hex(self) -> astronomer.HexPosition:
        return self._hex

    def name(self) -> str:
        return self._name

    def isNameGenerated(self) -> bool:
        return self._isNameGenerated

    def allegiance(self) -> typing.Optional[astronomer.Allegiance]:
        return self._allegiance

    def zone(self) -> typing.Optional[astronomer.ZoneType]:
        return self._zone

    def uwp(self) -> astronomer.UWP:
        return self._uwp

    def economics(self) -> astronomer.Economics:
        return self._economics

    def culture(self) -> astronomer.Culture:
        return self._culture

    def nobilities(self) -> astronomer.Nobilities:
        return self._nobilities

    def hasNobility(self, nobilityType: str) -> bool:
        return nobilityType in self._nobilities

    def bases(self) -> astronomer.Bases:
        return self._bases

    def hasBase(self, baseType: astronomer.BaseType) -> bool:
        return self._bases.hasBase(baseType)

    def hasStarPort(self):
        starPortCode = self._uwp.code(astronomer.UWP.Element.StarPort)
        return starPortCode == 'A' or starPortCode == 'B' or starPortCode == 'C' or starPortCode == 'D' or starPortCode == 'E'

    # Anomalies are worlds that have the {Anomaly} remark
    def isAnomaly(self) -> bool:
        return self._isAnomaly

    # Fuel Caches are worlds that have the {Fuel} remark. From looking at the
    # map data, the only place the remark is used in VoidBridges and Pirian
    # Domain Fuel Factories.
    # NOTE: At the time of writing, all worlds with the {Fuel} remark also have
    # the {Anomaly} remark.
    # https://www.wiki.travellerrpg.com/VoidBridges
    # https://www.wiki.travellerrpg.com/Pirian_Domain_Fuel_Factories
    def isFuelCache(self) -> bool:
        return self._isFuelCache

    def stellar(self) -> astronomer.Stellar:
        return self._stellar

    def numberOfStars(self) -> int:
        return self._stellar.starCount()

    def pbg(self) -> astronomer.PBG:
        return self._pbg

    def population(self) -> int:
        multiplier = self._pbg.numeric(
            element=astronomer.PBG.Element.PopulationMultiplier,
            default=None)
        exponent = self._uwp.numeric(
            element=astronomer.UWP.Element.Population,
            default=None)

        if multiplier == None or exponent == None:
            # Either the multiplier or exponent is unknown
            return -1

        # Handle legacy data (https://travellermap.com/doc/secondsurvey#pbg)
        # "Some legacy files may erroneously have 0 for the population multiplier but non-zero for
        # the population exponent. Treat the multiplier as 1 in these cases."
        if multiplier == 0 and exponent != 0:
            multiplier = 1

        return int(math.pow(10, exponent)) * multiplier

    def numberOfPlanetoidBelts(self) -> typing.Optional[int]:
        return self._pbg.numeric(
            element=astronomer.PBG.Element.PlanetoidBelts,
            default=None)

    def numberOfGasGiants(self) -> typing.Optional[int]:
        return self._pbg.numeric(
            element=astronomer.PBG.Element.GasGiants,
            default=None)

    def numberOfSystemWorlds(self) -> typing.Optional[int]:
        return self._systemWorlds

    def hasStarPortRefuelling(
            self,
            rules: traveller.Rules,
            includeRefined: bool = True,
            includeUnrefined: bool = True
            ) -> bool:
        starPortFuelType = rules.starPortFuelType(
            code=self._uwp.code(astronomer.UWP.Element.StarPort))

        if starPortFuelType is traveller.StarPortFuelType.AllTypes:
            return includeRefined or includeUnrefined
        elif starPortFuelType is traveller.StarPortFuelType.RefinedOnly:
            return includeRefined
        elif starPortFuelType is traveller.StarPortFuelType.UnrefinedOnly:
            return includeUnrefined

        return False

    def hasGasGiantRefuelling(self) -> bool:
        numberOfGasGiants = self.numberOfGasGiants()
        return numberOfGasGiants is not None and numberOfGasGiants > 0

    # This method of detecting if the system has water is based on Traveller Maps (WaterPresent in
    # World.cs).There are a couple of things i'm not entirely convinced by about the Traveller Map
    # algorithm but i've gone with them anyway for consistency
    # - It counts anything with a hydrographics > 0 as having water. My concern is that this could be
    # as low as 6% water, such a low parentage could cause issues if you're trying to do water refuelling
    # - It includes worlds with atmosphere code 15. This is 'Unusual (Varies)' which doesn't sound like
    # it would guarantee accessible water for refuelling
    # NOTE: At one point I had added a check for the WaterWorld trade code to give an early out but that
    # was removed when I added support for rule system trade codes as it would mean every call to
    # hasWaterRefuelling would need to pass the rule system
    def hasWaterRefuelling(self) -> bool:
        try:
            hydrographics = self._uwp.numeric(
                element=astronomer.UWP.Element.Hydrographics,
                default=-1)
            atmosphere = self._uwp.numeric(
                element=astronomer.UWP.Element.Atmosphere,
                default=-1)
        except ValueError:
            return False

        return (hydrographics > 0) and ((2 <= atmosphere <= 9) or (13 <= atmosphere <= 15))

    def hasWildernessRefuelling(self) -> bool:
        return self.hasGasGiantRefuelling() or \
            self.hasWaterRefuelling()

    def hasRefuelling(
            self,
            rules: traveller.Rules
            ) -> bool:
        return self.hasWildernessRefuelling() or \
            self.hasStarPortRefuelling(rules=rules) or \
            self.isFuelCache()

    def tradeCodes(self) -> typing.Sequence[traveller.TradeCode]:
        return common.ConstSequenceRef(self._tradeCodes)

    def hasTradeCode(
            self,
            tradeCode: traveller.TradeCode
            ) -> bool:
        return tradeCode in self._tradeCodes

    def sophonts(self) -> typing.Sequence[astronomer.SophontPopulation]:
        return common.ConstSequenceRef(self._sophontPopulationMap.values())

    def hasSophont(self, code: str) -> bool:
        return code in self._sophontPopulationMap

    # NOTE: This includes die back sophonts
    def sophontCount(self) -> int:
        return len(self._sophontPopulationMap)

    def rulingAllegiances(self) -> typing.Optional[astronomer.Allegiance]:
        return common.ConstSequenceRef(self._rulingAllegiances)

    def ownerCount(self) -> int:
        return len(self._owningWorldRefs)

    def ownerWorldReferences(self) -> typing.Sequence[WorldReference]:
        return common.ConstSequenceRef(self._owningWorldRefs)

    def colonyCount(self) -> int:
        return len(self._colonyWorldRefs)

    def colonyWorldReferences(self) -> typing.Sequence[WorldReference]:
        return common.ConstSequenceRef(self._colonyWorldRefs)

    def researchStations(self) -> typing.Optional[str]:
        return self._researchStations

    def researchStationCount(self) -> int:
        return len(self._researchStations)

    def hasResearchStation(self, code: str) -> bool:
        return code in self._researchStations

    def customRemarks(self) -> typing.Sequence[str]:
        return common.ConstSequenceRef(self._customRemarks)

    def hasCustomRemark(self, remark: str) -> bool:
        return remark in self._customRemarks

    def remarksString(self) -> str:
        if self._remarksString is not None:
            return self._remarksString

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

        for owner in self._owningWorldRefs:
            owningSystems.append((owner.hexX(), owner.hexY(), owner.sectorAbbreviation()))

        for colony in self._colonyWorldRefs:
            colonySystems.append((colony.hexX(), colony.hexY(), colony.sectorAbbreviation()))

        for allegiance in self._rulingAllegiances:
            rulingAllegiances.append(allegiance.code())

        self._remarksString = survey.formatSystemRemarksString(
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
        return self._remarksString

    def parsecsTo(
            self,
            dest: typing.Union[
                'World',
                astronomer.HexPosition
            ]
            ) -> int:
        return self._hex.parsecsTo(
            dest.hex() if isinstance(dest, World) else dest)

    # Prevent deep and shallow copies of world objects some code
    # (specifically the jump route calculations) expect there to
    # only be one instance of a world (as they compare world
    # objects to see if they are the same instance)
    def __deepcopy__(self, el):
        assert 1 == 0, 'Deep copying World objects will lead to bugs'

    def __copy__(self):
        assert 1 == 0, 'Copying World objects will lead to bugs'
