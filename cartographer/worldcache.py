import common
import cartographer
import math
import multiverse
import random
import traveller

class WorldInfo(object):
    # Traveller Map doesn't use trade codes for things you might expect it
    # would. Instead it has it's own logic based on UWP. Best guess is this is
    # to support older sector data that might not have trade codes
    _HighPopulation = 9
    _AgriculturalAtmospheres = set([4, 5, 6, 7, 8, 9])
    _AgriculturalHydrographics = set([4, 5, 6, 7, 8])
    _AgriculturalPopulations = set([5, 6, 7])
    _IndustrialAtmospheres = set([0, 1, 2, 4, 7, 9, 10, 11, 12])
    _IndustrialMinPopulation = 9
    _RichAtmospheres = set([6, 8])
    _RichPopulations = set([6, 7, 8])

    _HydrographicsImageMap = {
        0x1: 'Hyd1',
        0x2: 'Hyd2',
        0x3: 'Hyd3',
        0x4: 'Hyd4',
        0x5: 'Hyd5',
        0x6: 'Hyd6',
        0x7: 'Hyd7',
        0x8: 'Hyd8',
        0x9: 'Hyd9',
        0xA: 'HydA',
    }
    _HydrographicsDefaultImage = 'Hyd0'

    # Basic asteroid pattern, with probability varying per position:
    #   o o o
    #  o o o o
    #   o o o
    _AsteroidXPositions = [-2, 0, 2, -3, -1, 1, 3, -2, 0, 2]
    _AsteroidYPositions = [-2, -2, -2, 0, 0, 0, 0, 2, 2, 2]
    _AsteroidRadii = [0.5, 0.9, 0.5, 0.6, 0.9, 0.9, 0.6, 0.5, 0.9, 0.5]

    def __init__(
            self,
            world: multiverse.World,
            imageCache: cartographer.ImageStore
            ) -> None:
        self.name = world.name() if not world.isNameGenerated() else ''
        self.upperName = self.name.upper()

        hex = world.hex()
        self.hexString = f'{hex.offsetX():02d}{hex.offsetY():02d}'
        self.ssHexString = '{hexX:02d}{hexY:02d}'.format(
            hexX=int((hex.offsetX() - 1) % multiverse.SubsectorWidth) + 1,
            hexY=int((hex.offsetY() - 1) % multiverse.SubsectorHeight) + 1)

        worldCenterX, worldCenterY = hex.worldCenter()
        self.hexCenter = cartographer.PointF(x=worldCenterX, y=worldCenterY)

        uwp = world.uwp()
        self.uwpString = uwp.string()

        self.isPlaceholder = WorldInfo._calcIsPlaceholder(world)
        self.isCapital = WorldInfo._calcIsCapital(world)
        self.isHiPop = WorldInfo._calcIsHighPopulation(world)
        self.isAgricultural = WorldInfo._calcIsAgricultural(world)
        self.isRich = WorldInfo._calcIsRich(world)
        self.isIndustrial = WorldInfo._calcIsIndustrial(world)
        self.isVacuum = WorldInfo._calcIsVacuum(world)
        self.isHarshAtmosphere = WorldInfo._calcIsHarshAtmosphere(world)
        self.isAnomaly = WorldInfo._calcIsAnomaly(world)
        self.isAsteroids = WorldInfo._calcIsAsteroid(world)

        self.asteroidRectangles = None
        if self.isAsteroids:
            # Random generator is seeded with world location so it is always the same
            rand = random.Random(hex.absoluteX() ^ hex.absoluteY())
            self.asteroidRectangles = []
            for i in range(len(WorldInfo._AsteroidXPositions)):
                if rand.random() < WorldInfo._AsteroidRadii[i]:
                    self.asteroidRectangles.append(cartographer.RectangleF(
                        x=WorldInfo._AsteroidXPositions[i] * 0.035,
                        y=WorldInfo._AsteroidYPositions[i] * 0.035,
                        width=0.04 + rand.random() * 0.03,
                        height=0.04 + rand.random() * 0.03))

        # Split zone into separate bools for faster checks. The fact
        # Unabsorbed/Forbidden are equivalent is base do the Traveller Map
        # implementation is IsAmber/IsRed
        zone = world.zone()
        self.isAmberZone = zone is multiverse.ZoneType.AmberZone or \
            zone is multiverse.ZoneType.Unabsorbed
        self.isRedZone = zone is multiverse.ZoneType.RedZone or \
            zone is multiverse.ZoneType.Forbidden

        self.hasWater = WorldInfo._calcHasWater(world)
        self.hasGasGiant = WorldInfo._calcHasGasGiants(world)

        self.starport = uwp.code(multiverse.UWP.Element.StarPort)
        self.techLevel = uwp.code(multiverse.UWP.Element.TechLevel)

        allegiance = world.allegiance()
        self.t5Allegiance = allegiance.code() if allegiance else None
        self.legacyAllegiance = allegiance.legacyCode() if allegiance else None
        if not self.legacyAllegiance:
            # Using the T5 allegiance if there is no legacy one seems odd
            # but it's consistent with the Traveller Map implementation of
            # T5AllegianceCodeToLegacyCode
            self.legacyAllegiance = self.t5Allegiance

        baseAllegiance = allegiance.baseCode() if allegiance else None
        if not baseAllegiance:
            # Using the T5 allegiance if there is no base one seems odd
            # but it's consistent with the Traveller Map implementation of
            # AllegianceCodeToBaseAllegianceCode
            baseAllegiance = self.t5Allegiance

        bases = world.bases()
        self.primaryBaseGlyph = self.secondaryBaseGlyph = self.tertiaryBaseGlyph = self.specialFeatureGlyph = None
        ignoreSecondBase = False

        # NOTE: When determining the primary base glyph the standard allegiance
        # is used but the legacy allegiance is used for the secondary and tertiary
        # base glyphs. This is consistent with Traveller Map (although I've no idea
        # why it's done like this)
        if bases.count() >= 1:
            baseCode = multiverse.Bases.code(bases[0])

            # NOTE: This was is done by Traveller Map in RenderContext.DrawWorld
            # Special case: Show Zho Naval+Military as diamond
            if baseAllegiance == 'Zh' and bases.string() == 'KM':
                baseCode = 'Z'
                ignoreSecondBase = True

            self.primaryBaseGlyph = cartographer.GlyphDefs.fromBaseCode(
                allegiance=baseAllegiance,
                code=baseCode)

        if bases.count() >= 2 and not ignoreSecondBase:
            self.secondaryBaseGlyph = cartographer.GlyphDefs.fromBaseCode(
                allegiance=self.legacyAllegiance,
                code=multiverse.Bases.code(bases[1]))

        if bases.count() >= 3:
            self.tertiaryBaseGlyph = cartographer.GlyphDefs.fromBaseCode(
                allegiance=self.legacyAllegiance,
                code=multiverse.Bases.code(bases[2]))

        remarks = world.remarks()
        if remarks.hasTradeCode(multiverse.TradeCode.ResearchStation):
            self.specialFeatureGlyph = cartographer.GlyphDefs.fromResearchStation(
                remarks.researchStation())
        elif remarks.hasTradeCode(multiverse.TradeCode.Reserve):
            self.specialFeatureGlyph = cartographer.GlyphDefs.Reserve
        elif remarks.hasTradeCode(multiverse.TradeCode.PenalColony):
            self.specialFeatureGlyph = cartographer.GlyphDefs.Prison
        elif remarks.hasTradeCode(multiverse.TradeCode.PrisonCamp):
            self.specialFeatureGlyph = cartographer.GlyphDefs.ExileCamp

        self.worldSize = uwp.numeric(multiverse.UWP.Element.WorldSize)
        self.worldImage = WorldInfo._calcWorldImage(
            world=world,
            images=imageCache)
        self.imageRadius = (0.6 if self.worldSize <= 0 else (0.3 * (self.worldSize / 5.0 + 0.2))) / 2

        population = world.population()
        self.populationOverlayRadius = \
            math.sqrt(population / math.pi) * 0.00002 \
            if population > 0 else \
            0

        importance = WorldInfo._calcImportance(world=world)
        self.isImportant = importance >= 4
        self.importanceOverlayRadius = \
            (importance - 0.5) * multiverse.ParsecScaleX \
            if importance > 0 else \
            0

    @staticmethod
    def _calcIsPlaceholder(world: multiverse.World) -> bool:
        uwp = world.uwp()
        return uwp.sanitised() == '???????-?'

    @staticmethod
    def _calcHasWater(world: multiverse.World) -> bool:
        return traveller.worldHasWaterRefuelling(world=world)

    @staticmethod
    def _calcHasGasGiants(world: multiverse.World) -> bool:
        return traveller.worldHasGasGiantRefuelling(world=world)

    @staticmethod
    def _calcIsHighPopulation(world: multiverse.World) -> bool:
        uwp = world.uwp()
        population = uwp.numeric(element=multiverse.UWP.Element.Population, default=-1)
        return population >= WorldInfo._HighPopulation

    @staticmethod
    def _calcIsAgricultural(world: multiverse.World) -> bool:
        uwp = world.uwp()
        atmosphere = uwp.numeric(element=multiverse.UWP.Element.Atmosphere, default=-1)
        hydrographics = uwp.numeric(element=multiverse.UWP.Element.Hydrographics, default=-1)
        population = uwp.numeric(element=multiverse.UWP.Element.Population, default=-1)
        return atmosphere in WorldInfo._AgriculturalAtmospheres and \
            hydrographics in WorldInfo._AgriculturalHydrographics and \
            population in WorldInfo._AgriculturalPopulations

    @staticmethod
    def _calcIsIndustrial(world: multiverse.World) -> bool:
        uwp = world.uwp()
        atmosphere = uwp.numeric(element=multiverse.UWP.Element.Atmosphere, default=-1)
        population = uwp.numeric(element=multiverse.UWP.Element.Population, default=-1)
        return atmosphere in WorldInfo._IndustrialAtmospheres and \
            population >= WorldInfo._IndustrialMinPopulation

    @staticmethod
    def _calcIsRich(world: multiverse.World) -> bool:
        uwp = world.uwp()
        atmosphere = uwp.numeric(element=multiverse.UWP.Element.Atmosphere, default=-1)
        population = uwp.numeric(element=multiverse.UWP.Element.Population, default=-1)
        return atmosphere in WorldInfo._RichAtmospheres and \
            population in WorldInfo._RichPopulations

    @staticmethod
    def _calcIsVacuum(world: multiverse.World) -> bool:
        uwp = world.uwp()
        atmosphere = uwp.numeric(element=multiverse.UWP.Element.Atmosphere, default=-1)
        return atmosphere == 0

    @staticmethod
    def _calcIsHarshAtmosphere(world: multiverse.World) -> bool:
        uwp = world.uwp()
        atmosphere = uwp.numeric(element=multiverse.UWP.Element.Atmosphere, default=-1)
        return atmosphere > 10

    @staticmethod
    def _calcIsAnomaly(world: multiverse.World) -> bool:
        return world.isAnomaly()

    @staticmethod
    def _calcIsAsteroid(world: multiverse.World) -> bool:
        if world.isAnomaly():
            return False
        uwp = world.uwp()
        worldSize = uwp.numeric(element=multiverse.UWP.Element.WorldSize, default=-1)
        return worldSize == 0

    @staticmethod
    def _calcIsCapital(world: multiverse.World) -> bool:
        remarks = world.remarks()
        return remarks.hasTradeCode(multiverse.TradeCode.SectorCapital) or \
            remarks.hasTradeCode(multiverse.TradeCode.SubsectorCapital) or \
            remarks.hasTradeCode(multiverse.TradeCode.ImperialCapital) or \
            remarks.hasRemark('Capital')

    # This is based on code from Traveller Map which I believe is
    # based on the T5.10 rules
    @staticmethod
    def _calcImportance(world: multiverse.World) -> int:
        importance = 0

        uwp = world.uwp()
        starportCode = uwp.code(multiverse.UWP.Element.StarPort)
        techLevel = uwp.numeric(multiverse.UWP.Element.TechLevel, default=0)
        population = uwp.numeric(multiverse.UWP.Element.Population, default=0)
        atmosphere = uwp.numeric(multiverse.UWP.Element.Atmosphere, default=-1)
        hydrographics = uwp.numeric(multiverse.UWP.Element.Hydrographics, default=-1)

        if 'AB'.find(starportCode) >= 0:
            importance += 1
        elif 'DEX'.find(starportCode) >= 0:
            importance -= 1

        if techLevel >= 16:
            importance += 2
        elif techLevel >= 10:
            importance += 1
        elif techLevel <= 8:
            importance -= 1

        if population >= 9:
            importance += 1
        elif population <= 6:
            importance -= 1

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
            importance += 1
        if isRich:
            importance += 1
        if isIndustrial:
            importance += 1

        # NOTE: The definition of hasNavalBase intentionally doesn't include
        # things like VargrNavalBase as Traveller Map doesn't
        bases = world.bases()
        hasNavalBase = bases.hasBase(multiverse.BaseType.ImperialNavalBase) or \
            bases.hasBase(multiverse.BaseType.NavalBase)
        hasOtherServiceBase = bases.hasBase(multiverse.BaseType.ImperialScoutBase) or \
            bases.hasBase(multiverse.BaseType.MilitaryBase) or \
            bases.hasBase(multiverse.BaseType.ExplorationBase) or \
            bases.hasBase(multiverse.BaseType.VargrCorsairBase)
        hasServiceSpecialBase = bases.hasBase(multiverse.BaseType.WayStation) or \
            bases.hasBase(multiverse.BaseType.NavalDepot)
        hasAslanAndTlaukhuBase = bases.hasBase(multiverse.BaseType.AslanClanBase) and \
            bases.hasBase(multiverse.BaseType.AslanTlaukhuBase)
        if hasNavalBase and hasOtherServiceBase:
            importance += 1
        if hasServiceSpecialBase:
            importance += 1
        if hasAslanAndTlaukhuBase:
            importance += 1

        return importance

    @staticmethod
    def _calcWorldImage(
            world: multiverse.World,
            images: cartographer.ImageStore
            ) -> cartographer.AbstractImage:
        uwp = world.uwp()
        size = uwp.numeric(element=multiverse.UWP.Element.WorldSize, default=-1)
        if size <= 0:
            return images.worldImages['Belt']

        hydrographics = uwp.numeric(element=multiverse.UWP.Element.Hydrographics, default=-1)
        return images.worldImages[
            WorldInfo._HydrographicsImageMap.get(hydrographics, WorldInfo._HydrographicsDefaultImage)]

class WorldCache(object):
    def __init__(
            self,
            milieu: multiverse.Milieu,
            universe: multiverse.Universe,
            imageStore: cartographer.ImageStore,
            capacity: int
            ) -> None:
        self._milieu = milieu
        self._universe = universe
        self._imageStore = imageStore
        self._infoCache = common.LRUCache[
            multiverse.HexPosition,
            WorldInfo](capacity=capacity)

    def setMilieu(self, milieu: multiverse.Milieu) -> None:
        if milieu is self._milieu:
            return
        self._milieu = milieu
        self._infoCache.clear()

    def ensureCapacity(self, capacity) -> None:
        self._infoCache.ensureCapacity(capacity=capacity)

    def worldInfo(
            self,
            hex: multiverse.HexPosition
            ) -> WorldInfo:
        worldInfo = self._infoCache.get(hex)
        if not worldInfo:
            world = self._universe.worldByPosition(
                milieu=self._milieu,
                hex=hex)
            if not world:
                return None
            worldInfo = WorldInfo(
                world=world,
                imageCache=self._imageStore)
            self._infoCache[hex] = worldInfo
        return worldInfo

    def clear(self) -> None:
        self._infoCache.clear()
