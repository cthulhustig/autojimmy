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

    def parsecsTo(
            self,
            dest: typing.Union[
                'World',
                travellermap.HexPosition
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
