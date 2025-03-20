import maprenderer
import random
import travellermap
import typing

class StarfieldCache(object):
    _ScaleChunkSize = 4
    _IntensitySteps = 5
    _MinStarsPerChunk = 50
    _MaxStarsPerChunk = 300
    _RepeatAfter = 16
    _ChunkParsecSize = 256

    def __init__(
            self,
            graphics: maprenderer.AbstractGraphics
            ) -> None:
        self._graphics = graphics
        self._starfieldCache: typing.Dict[
            typing.Tuple[int, int], # Sector x/y
            maprenderer.AbstractPointList
        ] = {}

    def chunkParsecs(self) -> int:
        return self._ChunkParsecSize

    def intensitySteps(self) -> int:
        return self._IntensitySteps

    def sectorStarfield(
            self,
            chunkX: int,
            chunkY: int
            ) -> maprenderer.AbstractPointList:
        indexX = chunkX % StarfieldCache._RepeatAfter
        indexY = chunkY % StarfieldCache._RepeatAfter
        key = (indexX, indexY)
        starfield = self._starfieldCache.get(key)
        if not starfield:
            starfield = self._generateStarfield(indexX, indexY)
            self._starfieldCache[key] = starfield
        return starfield

    def _generateStarfield(
            self,
            indexX: int,
            indexY: int
            ) -> maprenderer.AbstractPointList:
        rand = random.Random((indexX << 16) ^ indexY)
        count = rand.randrange(StarfieldCache._MinStarsPerChunk, StarfieldCache._MaxStarsPerChunk)
        points = []
        for _ in range(count):
            point = maprenderer.PointF(
                x=rand.random() * StarfieldCache._ChunkParsecSize,
                y=rand.random() * StarfieldCache._ChunkParsecSize)
            intensity = rand.randrange(1, StarfieldCache._IntensitySteps)
            for _ in range(intensity):
                points.append(point)
        return self._graphics.createPointList(points=points)
