import common
import cartographer
import math
import random
import traveller
import travellermap
import typing

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
            world: traveller.World,
            imageCache: cartographer.ImageCache
            ) -> None:
        self.name = world.name() if not world.isNameGenerated() else ''
        self.upperName = self.name.upper()

        hex = world.hex()
        self.hexString = f'{hex.offsetX():02d}{hex.offsetY():02d}'
        self.ssHexString = '{hexX:02d}{hexY:02d}'.format(
            hexX=int((hex.offsetX() - 1) % travellermap.SubsectorWidth) + 1,
            hexY=int((hex.offsetY() - 1) % travellermap.SubsectorHeight) + 1)

        worldCenterX, worldCenterY = hex.worldCenter()
        self.hexCenter = cartographer.PointF(x=worldCenterX, y=worldCenterY)

        uwp = world.uwp()
        self.uwpString = uwp.string()

        self.isPlaceholder = self.uwpString == "XXXXXXX-X" or self.uwpString == "???????-?"

        self.isCapital = WorldInfo._calcIsCapital(world)
        self.isHiPop = WorldInfo._calcIsHighPopulation(world)
        self.isAgricultural = WorldInfo._calcIsAgricultural(world)
        self.isRich = WorldInfo._calcIsRich(world)
        self.isIndustrial = WorldInfo._calcIsIndustrial(world)

        self.isVacuum = WorldInfo._calcIsVacuum(world)
        self.isHarshAtmosphere = uwp.numeric(element=traveller.UWP.Element.Atmosphere, default=-1) > 10

        self.isAnomaly = world.isAnomaly()

        self.isAsteroids = not self.isAnomaly and \
            uwp.numeric(element=traveller.UWP.Element.WorldSize, default=-1) <= 0
        self.asteroidRectangles = None
        if self.isAsteroids:
            # Random generator is seeded with world location so it is always the same
            rand = random.Random(world.hex().absoluteX() ^ world.hex().absoluteY())
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
        self.isAmberZone = zone is traveller.ZoneType.AmberZone or \
            zone is traveller.ZoneType.Unabsorbed
        self.isRedZone = zone is traveller.ZoneType.RedZone or \
            zone is traveller.ZoneType.Forbidden

        self.hasWater = WorldInfo._calcHasWater(world)
        self.hasGasGiant = WorldInfo._calcHasGasGiants(world)

        self.starport = uwp.code(traveller.UWP.Element.StarPort)
        self.techLevel = uwp.code(traveller.UWP.Element.TechLevel)

        self.t5Allegiance = world.allegiance()
        self.legacyAllegiance = traveller.AllegianceManager.instance().legacyCode(
            milieu=world.milieu(),
            code=self.t5Allegiance)
        if not self.legacyAllegiance:
            # Using the T5 allegiance if there is no legacy one seems odd
            # but it's consistent with the Traveller Map implementation of
            # T5AllegianceCodeToLegacyCode
            self.legacyAllegiance = self.t5Allegiance
        self.basesAllegiance = traveller.AllegianceManager.instance().basesCode(
            milieu=world.milieu(),
            code=self.t5Allegiance)
        if not self.basesAllegiance:
            # Using the T5 allegiance if there is no bases one seems odd
            # but it's consistent with the Traveller Map implementation of
            # AllegianceCodeToBaseAllegianceCode
            self.basesAllegiance = self.t5Allegiance

        bases = world.bases()
        self.primaryBaseGlyph = self.secondaryBaseGlyph = self.tertiaryBaseGlyph = self.specialFeatureGlyph = None
        ignoreSecondBase = False

        # NOTE: When determining the primary base glyph the standard allegiance
        # is used but the legacy allegiance is used for the secondary and tertiary
        # base glyphs. This is consistent with Traveller Map (although I've no idea
        # why it's done like this)
        if bases.count() >= 1:
            baseCode = traveller.Bases.code(bases[0])

            # NOTE: This was is done by Traveller Map in RenderContext.DrawWorld
            # Special case: Show Zho Naval+Military as diamond
            if self.basesAllegiance == 'Zh' and bases.string() == 'KM':
                baseCode = 'Z'
                ignoreSecondBase = True

            self.primaryBaseGlyph = cartographer.GlyphDefs.fromBaseCode(
                allegiance=self.basesAllegiance,
                code=baseCode)

        if bases.count() >= 2 and not ignoreSecondBase:
            self.secondaryBaseGlyph = cartographer.GlyphDefs.fromBaseCode(
                allegiance=self.legacyAllegiance,
                code=traveller.Bases.code(bases[1]))

        if bases.count() >= 3:
            self.tertiaryBaseGlyph = cartographer.GlyphDefs.fromBaseCode(
                allegiance=self.legacyAllegiance,
                code=traveller.Bases.code(bases[2]))

        if world.hasTradeCode(traveller.TradeCode.ResearchStation):
            remarks = world.remarks()
            self.specialFeatureGlyph = cartographer.GlyphDefs.fromResearchStation(
                remarks.researchStation())
        elif world.hasTradeCode(traveller.TradeCode.Reserve):
            self.specialFeatureGlyph = cartographer.GlyphDefs.Reserve
        elif world.hasTradeCode(traveller.TradeCode.PenalColony):
            self.specialFeatureGlyph = cartographer.GlyphDefs.Prison
        elif world.hasTradeCode(traveller.TradeCode.PrisonCamp):
            self.specialFeatureGlyph = cartographer.GlyphDefs.ExileCamp

        self.worldSize = world.physicalSize()
        self.worldImage = WorldInfo._calcWorldImage(
            world=world,
            images=imageCache)
        self.imageRadius = (0.6 if self.worldSize <= 0 else (0.3 * (self.worldSize / 5.0 + 0.2))) / 2

        self.populationOverlayRadius = \
            self.populationOverlayRadius = math.sqrt(world.population() / math.pi) * 0.00002 \
            if world.population() > 0 else \
            0

        self.importance = world.importance()
        self.isImportant = world.importance() >= 4
        self.importanceOverlayRadius = \
            (self.importance - 0.5) * travellermap.ParsecScaleX \
            if self.importance > 0 else \
            0

    @staticmethod
    def _calcHasWater(world: traveller.World) -> bool:
        return world.hasWaterRefuelling()

    @staticmethod
    def _calcHasGasGiants(world: traveller.World) -> bool:
        return world.hasGasGiantRefuelling()

    @staticmethod
    def _calcIsHighPopulation(world: traveller.World) -> bool:
        uwp = world.uwp()
        population = uwp.numeric(element=traveller.UWP.Element.Population, default=-1)
        return population >= WorldInfo._HighPopulation

    @staticmethod
    def _calcIsAgricultural(world: traveller.World) -> bool:
        uwp = world.uwp()
        atmosphere = uwp.numeric(element=traveller.UWP.Element.Atmosphere, default=-1)
        hydrographics = uwp.numeric(element=traveller.UWP.Element.Hydrographics, default=-1)
        population = uwp.numeric(element=traveller.UWP.Element.Population, default=-1)
        return atmosphere in WorldInfo._AgriculturalAtmospheres and \
            hydrographics in WorldInfo._AgriculturalHydrographics and \
            population in WorldInfo._AgriculturalPopulations

    @staticmethod
    def _calcIsIndustrial(world: traveller.World) -> bool:
        uwp = world.uwp()
        atmosphere = uwp.numeric(element=traveller.UWP.Element.Atmosphere, default=-1)
        population = uwp.numeric(element=traveller.UWP.Element.Population, default=-1)
        return atmosphere in WorldInfo._IndustrialAtmospheres and \
            population >= WorldInfo._IndustrialMinPopulation

    @staticmethod
    def _calcIsRich(world: traveller.World) -> bool:
        uwp = world.uwp()
        atmosphere = uwp.numeric(element=traveller.UWP.Element.Atmosphere, default=-1)
        population = uwp.numeric(element=traveller.UWP.Element.Population, default=-1)
        return atmosphere in WorldInfo._RichAtmospheres and \
            population in WorldInfo._RichPopulations

    @staticmethod
    def _calcIsVacuum(world: traveller.World) -> bool:
        uwp = world.uwp()
        atmosphere = uwp.numeric(element=traveller.UWP.Element.Atmosphere, default=-1)
        return atmosphere == 0

    @staticmethod
    def _calcIsCapital(world: traveller.World) -> bool:
        return world.hasTradeCode(traveller.TradeCode.SectorCapital) or \
            world.hasTradeCode(traveller.TradeCode.SubsectorCapital) or \
            world.hasTradeCode(traveller.TradeCode.ImperialCapital) or \
            world.hasRemark('Capital')

    @staticmethod
    def _calcWorldImage(
            world: traveller.World,
            images: cartographer.ImageCache
            ) -> cartographer.AbstractImage:
        uwp = world.uwp()
        size = uwp.numeric(element=traveller.UWP.Element.WorldSize, default=-1)
        if size <= 0:
            return images.worldImages['Belt']

        hydrographics = uwp.numeric(element=traveller.UWP.Element.Hydrographics, default=-1)
        return images.worldImages[
            WorldInfo._HydrographicsImageMap.get(hydrographics, WorldInfo._HydrographicsDefaultImage)]

class WorldCache(object):
    def __init__(
            self,
            imageCache: cartographer.ImageCache,
            capacity: int
            ) -> None:
        self._imageCache = imageCache
        self._infoCache = common.LRUCache[
            traveller.World,
            WorldInfo](capacity=capacity)

    def ensureCapacity(self, capacity) -> None:
        self._infoCache.ensureCapacity(capacity=capacity)

    def worldInfo(
            self,
            world: traveller.World
            ) -> WorldInfo:
        worldInfo = self._infoCache.get(world)
        if not worldInfo:
            worldInfo = WorldInfo(
                world=world,
                imageCache=self._imageCache)
            self._infoCache[world] = worldInfo
        return worldInfo
