import astronomer
import math
import traveller
import typing

class World(object):
    def __init__(
            self,
            milieu: astronomer.Milieu,
            hex: astronomer.HexPosition,
            worldName: str,
            isNameGenerated: bool,
            sectorName: str,
            subsectorName: str,
            allegiance: typing.Optional[astronomer.Allegiance],
            uwp: astronomer.UWP,
            economics: astronomer.Economics,
            culture: astronomer.Culture,
            nobilities: astronomer.Nobilities,
            remarks: astronomer.Remarks,
            zone: typing.Optional[astronomer.ZoneType],
            stellar: astronomer.Stellar,
            pbg: astronomer.PBG,
            systemWorlds: typing.Optional[int],
            bases: astronomer.Bases
            ) -> None:
        self._milieu = milieu
        self._hex = hex
        self._name = worldName
        self._isNameGenerated = isNameGenerated
        self._sectorName = sectorName
        self._subsectorName = subsectorName
        self._allegiance = allegiance
        self._uwp = uwp
        self._economics = economics
        self._culture = culture
        self._nobilities = nobilities
        self._zone = zone
        self._remarks = remarks
        self._isAnomaly = self._remarks.hasCustomRemark('{Anomaly}')
        self._isFuelCache = self._remarks.hasCustomRemark('{Fuel}')
        self._stellar = stellar
        self._pbg = pbg
        self._systemWorlds = systemWorlds
        self._bases = bases

    def milieu(self) -> astronomer.Milieu:
        return self._milieu

    def hex(self) -> astronomer.HexPosition:
        return self._hex

    def name(
            self,
            includeSubsector: bool = False
            ) -> str:
        if includeSubsector:
            return f'{self._name} ({self._subsectorName})'
        return self._name

    def isNameGenerated(self) -> bool:
        return self._isNameGenerated

    def sectorName(self) -> str:
        return self._sectorName

    def subsectorName(self) -> str:
        return self._subsectorName

    def sectorHex(self) -> str:
        return astronomer.formatSectorHex(
            sectorName=self._sectorName,
            offsetX=self._hex.offsetX(),
            offsetY=self._hex.offsetY())

    def allegiance(self) -> typing.Optional[astronomer.Allegiance]:
        return self._allegiance

    def uwp(self) -> astronomer.UWP:
        return self._uwp

    def economics(self) -> astronomer.Economics:
        return self._economics

    def culture(self) -> astronomer.Culture:
        return self._culture

    def remarks(self) -> astronomer.Remarks:
        return self._remarks

    def hasRemark(self, remark: str) -> None:
        return self._remarks.hasCustomRemark(remark=remark)

    def zone(self) -> typing.Optional[astronomer.ZoneType]:
        return self._zone

    def nobilities(self) -> astronomer.Nobilities:
        return self._nobilities

    def hasNobility(self, nobilityType: str) -> bool:
        return nobilityType in self._nobilities

    def bases(self) -> astronomer.Bases:
        return self._bases

    def hasBase(self, baseType: astronomer.BaseType) -> bool:
        return self._bases.hasBase(baseType)

    def tradeCodes(self) -> typing.Iterable[traveller.TradeCode]:
        return self._remarks.tradeCodes()

    def hasTradeCode(self, tradeCode: traveller.TradeCode) -> bool:
        return self._remarks.hasTradeCode(tradeCode)

    def hasStarPort(self):
        starPortCode = self._uwp.code(astronomer.UWP.Element.StarPort)
        return starPortCode == 'A' or starPortCode == 'B' or starPortCode == 'C' or starPortCode == 'D' or starPortCode == 'E'

    def ownerCount(self) -> bool:
        return self._remarks.ownerCount()

    def ownerWorldReferences(self) -> typing.Optional[typing.Collection[astronomer.WorldReference]]:
        return self._remarks.ownerWorlds()

    def colonyCount(self) -> int:
        return self._remarks.colonyCount()

    def colonyWorldReferences(self) -> typing.Optional[typing.Collection[astronomer.WorldReference]]:
        return self._remarks.colonyWorlds()

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

    def numberOfTerrestrialPlanets(self) -> typing.Optional[int]:
        systemWorlds = self.numberOfSystemWorlds()
        if systemWorlds is None:
            return None

        planetoidBelts = self.numberOfPlanetoidBelts()
        if planetoidBelts is None:
            return None

        gasGiants = self.numberOfGasGiants()
        if gasGiants is None:
            return None

        terrestrialPlanets = systemWorlds - (planetoidBelts + gasGiants)
        if terrestrialPlanets < 0:
            terrestrialPlanets = 0
        return terrestrialPlanets

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
    # World.cs). I've added the check for the water world trade code as it gives a quick out.
    # There are a couple of things i'm not entirely convinced by about the Traveller Map algorithm
    # but i've gone with them anyway for consistency
    # - It counts anything with a hydrographics > 0 as having water. My concern is that this could be
    # as low as 6% water, such a low parentage could cause issues if you're trying to do water refuelling
    # - It includes worlds with atmosphere code 15. This is 'Unusual (Varies)' which doesn't sound like
    # it would guarantee accessible water for refuelling
    def hasWaterRefuelling(self) -> bool:
        if self.hasTradeCode(traveller.TradeCode.WaterWorld):
            return True

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
