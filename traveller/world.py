import math
import traveller
import travellermap
import typing

class World(object):
    def __init__(
            self,
            name: str,
            sectorName: str,
            subsectorName: str,
            hex: str,
            allegiance: str,
            uwp: str,
            economics: str,
            culture: str,
            nobilities: str,
            remarks: str,
            zone: str,
            stellar: str,
            pbg: str,
            systemWorlds: str,
            bases: str,
            sectorX: int,
            sectorY: int
            ) -> None:
        self._name = name
        self._sectorName = sectorName
        self._subsectorName = subsectorName
        self._hex = hex
        self._allegiance = allegiance
        self._uwp = traveller.UWP(uwp)
        self._economics = traveller.Economics(economics)
        self._culture = traveller.Culture(culture)
        self._nobilities = traveller.Nobilities(nobilities)
        self._zone = traveller.parseZoneString(zone)
        self._remarks = traveller.Remarks(
            string=remarks,
            sectorName=sectorName,
            zone=self._zone)
        self._isAnomaly = self._remarks.hasRemark('{Anomaly}')
        self._isFuelCache = self._remarks.hasRemark('{Fuel}')
        self._stellar = traveller.Stellar(stellar)
        self._pbg = traveller.PBG(pbg)
        # There is always 1 system world (the main world)
        self._systemWorlds = int(systemWorlds) if systemWorlds else 1
        self._bases = traveller.Bases(bases)
        self._x = int(self._hex[:2])
        self._y = int(self._hex[-2:])
        self._sectorX = sectorX
        self._sectorY = sectorY
        self._absoluteX, self._absoluteY = travellermap.relativeHexToAbsoluteHex(
            sectorX=self._sectorX,
            sectorY=self._sectorY,
            worldX=self._x,
            worldY=self._y)

    def name(self, includeSubsector: bool = False) -> str:
        if includeSubsector:
            return f'{self._name} ({self._subsectorName})'
        return self._name

    def sectorName(self) -> str:
        return self._sectorName

    def subsectorName(self) -> str:
        return self._subsectorName

    def hex(self) -> str:
        return self._hex

    def sectorHex(self) -> str:
        return f'{self._sectorName} {self._hex}'

    def allegiance(self) -> str:
        return self._allegiance

    def uwp(self) -> traveller.UWP:
        return self._uwp

    def economics(self) -> traveller.Economics:
        return self._economics

    def culture(self) -> traveller.Culture:
        return self._culture

    def remarks(self) -> traveller.Remarks:
        return self._remarks

    def zone(self) -> typing.Optional[traveller.ZoneType]:
        return self._zone

    def nobilities(self) -> traveller.Nobilities:
        return self._nobilities

    def hasNobility(self, nobilityType: str) -> bool:
        return nobilityType in self._nobilities

    def bases(self) -> traveller.Bases:
        return self._bases

    def hasBase(self, baseType: traveller.BaseType) -> bool:
        return self._bases.hasBase(baseType)

    def tradeCodes(self) -> typing.Iterable[traveller.TradeCode]:
        return self._remarks.tradeCodes()

    def hasTradeCode(self, tradeCode: traveller.TradeCode) -> bool:
        return self._remarks.hasTradeCode(tradeCode)

    def hasStarPort(self):
        starPortCode = self._uwp.code(traveller.UWP.Element.StarPort)
        return starPortCode == 'A' or starPortCode == 'B' or starPortCode == 'C' or starPortCode == 'D' or starPortCode == 'E'

    def hasOwner(self) -> bool:
        return self._remarks.hasOwner()

    def ownerSectorHex(self) -> typing.Optional[str]:
        return self._remarks.ownerSectorHex()

    def hasColony(self) -> bool:
        return self._remarks.hasColony()

    def colonyCount(self) -> int:
        return self._remarks.colonyCount()

    def colonySectorHexes(self) -> typing.Optional[typing.Iterable[str]]:
        return self._remarks.colonySectorHexes()

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

    # This method of detecting if the system has water is based on Traveller Maps (WaterPresent in
    # World.cs). I've added the check for the water world trade code as it gives a quick out.
    # There are a couple of things i'm not entirely convinced by about the Traveller Map algorithm
    # but i've gone with them anyway for consistency
    # - It counts anything with a hydrographics > 0 as having water. My concern is that this could be
    # as low as 6% water, such a low parentage could cause issues if you're trying to do water refuelling
    # - It includes worlds with atmosphere code 15. This is 'Unusual (Varies)' which doesn't sound like
    # it would guarantee accessible water for refuelling
    def waterPresent(self) -> bool:
        if self.hasTradeCode(traveller.TradeCode.WaterWorld):
            return True

        try:
            hydrographics = traveller.ehexToInteger(
                value=self._uwp.code(traveller.UWP.Element.Hydrographics),
                default=-1)
            atmosphere = traveller.ehexToInteger(
                value=self._uwp.code(traveller.UWP.Element.Atmosphere),
                default=-1)
        except ValueError:
            return 0

        return (hydrographics > 0) and ((2 <= atmosphere <= 9) or (13 <= atmosphere <= 15))

    def stellar(self) -> traveller.Stellar:
        return self._stellar

    def numberOfStars(self) -> int:
        return self._stellar.starCount()

    def pbg(self) -> traveller.PBG:
        return self._pbg

    def population(self) -> int:
        multiplier = traveller.ehexToInteger(
            value=self._pbg.code(traveller.PBG.Element.PopulationMultiplier),
            default=None)
        exponent = traveller.ehexToInteger(
            value=self._uwp.code(traveller.UWP.Element.Population),
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

    def numberOfPlanetoidBelts(self) -> int:
        return traveller.ehexToInteger(
            value=self._pbg.code(traveller.PBG.Element.PlanetoidBelts),
            default=-1)

    def numberOfGasGiants(self) -> int:
        return traveller.ehexToInteger(
            value=self._pbg.code(traveller.PBG.Element.GasGiants),
            default=-1)

    def numberOfSystemWorlds(self) -> int:
        return self._systemWorlds

    # TODO: This change needs a decent amount of testing
    def hasStarPortRefuelling(
            self,
            includeRefined: bool = True,
            includeUnrefined: bool = True,
            refinedFuelExclusive: bool = False # Do A/B class star ports _only_ have refined fuel
            ) -> bool:
        starPortCode = self._uwp.code(traveller.UWP.Element.StarPort)
        if starPortCode == 'A' or starPortCode == 'B':
            return includeRefined or (includeUnrefined and not refinedFuelExclusive)
        if starPortCode == 'C' or starPortCode == 'D':
            return includeUnrefined
        return False

    def hasGasGiantRefuelling(self) -> bool:
        return self.numberOfGasGiants() > 0

    def hasWaterRefuelling(self) -> bool:
        return self.waterPresent()

    def hasWildernessRefuelling(self) -> bool:
        return self.hasGasGiantRefuelling() or self.hasWaterRefuelling()

    def x(self) -> int:
        return self._x

    def y(self) -> int:
        return self._y

    def sectorX(self) -> int:
        return self._sectorX

    def sectorY(self) -> int:
        return self._sectorY

    def absoluteX(self) -> int:
        return self._absoluteX

    def absoluteY(self) -> int:
        return self._absoluteY

    # Prevent deep and shallow copies of world objects some code
    # (specifically the jump route calculations) expect there to
    # only be one instance of a world (as they compare world
    # objects to see if they are the same instance)
    def __deepcopy__(self, el):
        assert 1 == 0, 'Deep copying World objects will lead to bugs'

    def __copy__(self):
        assert 1 == 0, 'Copying World objects will lead to bugs'
