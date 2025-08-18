import math
import traveller
import travellermap
import typing

class World(object):
    def __init__(
            self,
            milieu: travellermap.Milieu,
            hex: travellermap.HexPosition,
            worldName: str,
            isNameGenerated: bool,
            sectorName: str,
            subsectorName: str,
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
            bases: str
            ) -> None:
        self._milieu = milieu
        self._hex = hex
        self._name = worldName
        self._isNameGenerated = isNameGenerated
        self._sectorName = sectorName
        self._subsectorName = subsectorName
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

        # Importance is calculated on demand
        self._importance = None

    def milieu(self) -> travellermap.Milieu:
        return self._milieu

    def hex(self) -> travellermap.HexPosition:
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
        return traveller.formatSectorHex(
            sectorName=self._sectorName,
            offsetX=self._hex.offsetX(),
            offsetY=self._hex.offsetY())

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

    def hasRemark(self, remark: str) -> None:
        return self._remarks.hasRemark(remark=remark)

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

    def hasStarPortRefuelling(
            self,
            rules: traveller.Rules,
            includeRefined: bool = True,
            includeUnrefined: bool = True
            ) -> bool:
        starPortFuelType = rules.starPortFuelType(
            code=self._uwp.code(traveller.UWP.Element.StarPort))
        if starPortFuelType == traveller.StarPortFuelType.AllTypes:
            return includeRefined or includeUnrefined
        elif starPortFuelType == traveller.StarPortFuelType.RefinedOnly:
            return includeRefined
        elif starPortFuelType == traveller.StarPortFuelType.UnrefinedOnly:
            return includeUnrefined
        return False

    def hasGasGiantRefuelling(self) -> bool:
        return self.numberOfGasGiants() > 0

    def hasWaterRefuelling(self) -> bool:
        return self.waterPresent()

    def hasWildernessRefuelling(self) -> bool:
        return self.hasGasGiantRefuelling() or self.hasWaterRefuelling()

    def parsecsTo(
            self,
            dest: typing.Union[
                'World',
                travellermap.HexPosition
            ]
            ) -> int:
        return self._hex.parsecsTo(
            dest.hex() if isinstance(dest, World) else dest)

    # This is based on code from Traveller Map which I believe is
    # based on the T5.10 rules
    # TODO: This should probably be moved into WorldCache as it's not something
    # I think I'll ever use outside of Traveller Map rendering
    def importance(self) -> int:
        if self._importance is None:
            self._importance = 0

            starportCode = self._uwp.code(traveller.UWP.Element.StarPort)
            techLevel = self._uwp.numeric(traveller.UWP.Element.TechLevel, default=0)
            population = self._uwp.numeric(traveller.UWP.Element.Population, default=0)
            atmosphere = self._uwp.numeric(traveller.UWP.Element.Atmosphere, default=-1)
            hydrographics = self._uwp.numeric(traveller.UWP.Element.Hydrographics, default=-1)

            if 'AB'.find(starportCode) >= 0:
                self._importance += 1
            elif 'DEX'.find(starportCode) >= 0:
                self._importance -= 1

            if techLevel >= 16:
                self._importance += 2
            elif techLevel >= 10:
                self._importance += 1
            elif techLevel <= 8:
                self._importance -= 1

            if population >= 9:
                self._importance += 1
            elif population <= 6:
                self._importance -= 1

            isAgricultural = \
                (atmosphere >= 4 and atmosphere <= 9) and \
                (hydrographics >= 4 and hydrographics <= 8) and \
                (population >= 5 and population <= 7)
            isRich = \
                (atmosphere == 6 or atmosphere == 8) and \
                (population >= 6 and population <= 8)
            isIndustrial = \
                ((atmosphere >= 0 and atmosphere <= 2) or \
                 (atmosphere == 4) or \
                 (atmosphere == 7) or
                 (atmosphere >= 9 and atmosphere <= 12)) and \
                (population >= 9)
            if isAgricultural:
                self._importance += 1
            if isRich:
                self._importance += 1
            if isIndustrial:
                self._importance += 1

            # NOTE: The definition of hasNavalBase intentionally doesn't include
            # things like VargrNavalBase as Traveller Map doesn't
            hasNavalBase = self._bases.hasBase(traveller.BaseType.ImperialNavalBase) or \
                self._bases.hasBase(traveller.BaseType.NavalBase)
            hasOtherServiceBase = self._bases.hasBase(traveller.BaseType.ImperialScoutBase) or \
                self._bases.hasBase(traveller.BaseType.MilitaryBase) or \
                self._bases.hasBase(traveller.BaseType.ExplorationBase) or \
                self._bases.hasBase(traveller.BaseType.VargrCorsairBase)
            hasServiceSpecialBase = self._bases.hasBase(traveller.BaseType.WayStation) or \
                self._bases.hasBase(traveller.BaseType.NavalDepot)
            hasAslanAndTlaukhuBase = self._bases.hasBase(traveller.BaseType.AslanClanBase) and \
                self._bases.hasBase(traveller.BaseType.AslanTlaukhuBase)
            if hasNavalBase and hasOtherServiceBase:
                self._importance += 1
            if hasServiceSpecialBase:
                self._importance += 1
            if hasAslanAndTlaukhuBase:
                self._importance += 1

        return self._importance

    # Prevent deep and shallow copies of world objects some code
    # (specifically the jump route calculations) expect there to
    # only be one instance of a world (as they compare world
    # objects to see if they are the same instance)
    def __deepcopy__(self, el):
        assert 1 == 0, 'Deep copying World objects will lead to bugs'

    def __copy__(self):
        assert 1 == 0, 'Copying World objects will lead to bugs'
