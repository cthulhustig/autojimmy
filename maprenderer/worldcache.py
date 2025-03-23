import common
import maprenderer
import math
import random
import traveller
import travellermap
import typing

class WorldInfo(object):
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
            imageCache: maprenderer.ImageCache
            ) -> None:
        self.name = world.name() if not world.isNameGenerated() else ''
        self.upperName = self.name.upper()

        worldHex = world.hex()
        self.hexString = f'{worldHex.offsetX():02d}{worldHex.offsetY():02d}'
        self.ssHexString = '{hexX:02d}{hexY:02d}'.format(
            hexX=int((worldHex.offsetX() - 1) % travellermap.SubsectorWidth) + 1,
            hexY=int((worldHex.offsetY() - 1) % travellermap.SubsectorHeight) + 1)

        hexCenterX, hexCenterY = worldHex.absoluteCenter()
        self.hexCenter = maprenderer.PointF(x=hexCenterX, y=hexCenterY)

        uwp = world.uwp()
        self.uwpString = uwp.string()

        self.isPlaceholder = self.uwpString == "XXXXXXX-X" or self.uwpString == "???????-?"

        self.isCapital = maprenderer.WorldHelper.isCapital(world)
        self.isHiPop = maprenderer.WorldHelper.isHighPopulation(world)
        self.isAgricultural = maprenderer.WorldHelper.isAgricultural(world)
        self.isRich = maprenderer.WorldHelper.isRich(world)
        self.isIndustrial = maprenderer.WorldHelper.isIndustrial(world)

        self.isVacuum = maprenderer.WorldHelper.isVacuum(world)
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
                    self.asteroidRectangles.append(maprenderer.RectangleF(
                        x=WorldInfo._AsteroidXPositions[i] * 0.035,
                        y=WorldInfo._AsteroidYPositions[i] * 0.035,
                        width=0.04 + rand.random() * 0.03,
                        height=0.04 + rand.random() * 0.03))

        # Split zone into separate bools for faster checks
        self.isAmberZone = world.zone() is traveller.ZoneType.AmberZone
        self.isRedZone = world.zone() is traveller.ZoneType.RedZone

        self.hasWater = maprenderer.WorldHelper.hasWater(world)
        self.hasGasGiant = maprenderer.WorldHelper.hasGasGiants(world)

        self.starport = uwp.code(traveller.UWP.Element.StarPort)
        self.techLevel = uwp.code(traveller.UWP.Element.TechLevel)

        bases = world.bases()
        self.primaryBaseGlyph = self.secondaryBaseGlyph = self.tertiaryBaseGlyph = self.specialFeatureGlyph = None

        # NOTE: When determining the primary base glyph the standard allegiance
        # is used but the legacy allegiance is used for the secondary and tertiary
        # base glyphs. This is consistent with Traveller Map (although I've no idea
        # why it's done like this)
        if bases.count() >= 1:
            allegiance = maprenderer.WorldHelper.allegianceCode(
                world=world,
                useLegacy=False)
            baseCode = traveller.Bases.code(bases[0])

            # NOTE: This was is done by Traveller Map in RenderContext.DrawWorld
            # Special case: Show Zho Naval+Military as diamond
            if world.allegiance() == 'Zh' and bases.string() == 'KM':
                baseCode = 'Z'

            self.primaryBaseGlyph = maprenderer.GlyphDefs.fromBaseCode(
                allegiance=allegiance,
                code=baseCode)

        if bases.count() >= 2:
            legacyAllegiance = maprenderer.WorldHelper.allegianceCode(
                world=world,
                useLegacy=True)
            self.secondaryBaseGlyph = maprenderer.GlyphDefs.fromBaseCode(
                allegiance=legacyAllegiance,
                code=traveller.Bases.code(bases[1]))

        if bases.count() >= 3:
            legacyAllegiance = maprenderer.WorldHelper.allegianceCode(
                world=world,
                useLegacy=True)
            self.tertiaryBaseGlyph = maprenderer.GlyphDefs.fromBaseCode(
                allegiance=legacyAllegiance,
                code=traveller.Bases.code(bases[2]))

        if world.hasTradeCode(traveller.TradeCode.ResearchStation):
            remarks = world.remarks()
            self.specialFeatureGlyph = maprenderer.GlyphDefs.fromResearchStation(
                remarks.researchStation())
        elif world.hasTradeCode(traveller.TradeCode.Reserve):
            self.specialFeatureGlyph = maprenderer.GlyphDefs.Reserve
        elif world.hasTradeCode(traveller.TradeCode.PenalColony):
            self.specialFeatureGlyph = maprenderer.GlyphDefs.Prison
        elif world.hasTradeCode(traveller.TradeCode.PrisonCamp):
            self.specialFeatureGlyph = maprenderer.GlyphDefs.ExileCamp

        self.worldSize = world.physicalSize()
        self.worldImage = maprenderer.WorldHelper.worldImage(
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

class WorldCache(object):
    _DefaultCapacity = 500
    def __init__(
            self,
            imageCache: maprenderer.ImageCache
            ) -> None:
        self._imageCache = imageCache
        self._infoCache = common.LRUCache[
            traveller.World,
            WorldInfo](capacity=WorldCache._DefaultCapacity)

    def ensureCapacity(self, capacity) -> None:
        self._infoCache.ensureCapacity(capacity=capacity)

    def getWorldInfo(
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
