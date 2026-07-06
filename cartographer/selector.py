import astronomer
import cartographer
import math
import typing

class RectSelector(cartographer.AbstractSelector):
    def __init__(
            self,
            universe: astronomer.Universe,
            sectorSlop: int = 1, # Numbers of sectors
            worldSlop: int = 1, # Number of parsecs
            ) -> None:
        self._universe = universe
        self._sectorSlop = sectorSlop
        self._worldSlop = worldSlop
        self._rect = cartographer.RectangleF()

        self._tightSectors: typing.Optional[typing.List[astronomer.Sector]] = None
        self._sloppySectors: typing.Optional[typing.List[astronomer.Sector]] = None

        self._tightWorlds: typing.Optional[typing.List[astronomer.World]] = None
        self._sloppyWorlds: typing.Optional[typing.List[astronomer.World]] = None

    def setRect(self, rect: cartographer.RectangleF) -> None:
        if rect == self._rect:
            return
        self._rect = cartographer.RectangleF(rect)
        self.clearCaches()

    def sectorSlop(self) -> float:
        return self._sectorSlop

    def setSectorSlop(self, slop: float) -> None:
        self._sectorSlop = slop
        self._sloppySectors = None

    def worldSlop(self) -> float:
        return self._worldSlop

    def setWorldSlop(self, slop: float) -> None:
        self._worldSlop = slop
        self._sloppyWorlds = None

    def sectors(self, tight: bool = False) -> typing.Collection[astronomer.Sector]:
        sectors = self._tightSectors if tight else self._sloppySectors
        if sectors is not None:
            return sectors

        self._cacheSectors(tight=tight)

        return self._tightSectors if tight else self._sloppySectors

    def worlds(self, tight: bool = False) -> typing.Collection[astronomer.World]:
        worlds = self._tightWorlds if tight else self._sloppyWorlds
        if worlds is not None:
            return worlds

        self._cacheWorlds(tight=tight)

        return self._tightWorlds if tight else self._sloppyWorlds

    def clearCaches(self) -> None:
        self._tightSectors = self._sloppySectors = None
        self._tightWorlds = self._sloppyWorlds = None

    def _cacheSectors(
            self,
            tight: bool
            ) -> None:
        if self._sloppySectors is None: # Specifically None to not recalculate if there are no sectors
            sloppyRect = cartographer.RectangleF(self._rect)
            if self._sectorSlop:
                sloppyRect.inflate(
                    x=self._sectorSlop * astronomer.SectorWidth,
                    y=self._sectorSlop * astronomer.SectorHeight)

            upperLeft = astronomer.HexPosition(
                sectorX=int(math.floor((sloppyRect.left() + astronomer.ReferenceHexX) / astronomer.SectorWidth)),
                sectorY=int(math.floor((sloppyRect.top() + astronomer.ReferenceHexY) / astronomer.SectorHeight)),
                offsetX=astronomer.SectorWidth - 1,
                offsetY=astronomer.SectorHeight - 1)
            lowerRight = astronomer.HexPosition(
                sectorX=int(math.floor((sloppyRect.right() + astronomer.ReferenceHexX) / astronomer.SectorWidth)),
                sectorY=int(math.floor((sloppyRect.bottom() + astronomer.ReferenceHexY) / astronomer.SectorHeight)),
                offsetX=0,
                offsetY=0)

            self._sloppySectors = self._universe.sectorsInArea(
                upperLeft=upperLeft,
                lowerRight=lowerRight)

            if not self._sectorSlop:
                self._tightSectors = self._sloppySectors

        if tight and self._tightSectors is None: # Specifically None to not recalculate if there are no sectors
            rect = cartographer.RectangleF()

            self._tightSectors = []
            for sector in self._sloppySectors:
                left, top, width, height = sector.position().worldBounds()
                rect.setRect(x=left, y=top, width=width, height=height)
                if self._rect.intersects(other=rect):
                    self._tightSectors.append(sector)

    def _cacheWorlds(
            self,
            tight: bool
            ) -> None:
        if self._sloppyWorlds is None: # Specifically None to not recalculate if there are no worlds
            rect = cartographer.RectangleF(self._rect)
            if self._worldSlop:
                rect.inflate(x=self._worldSlop, y=self._worldSlop)

            upperLeft = astronomer.HexPosition(
                absoluteX=int(math.floor(rect.left())),
                absoluteY=int(math.floor(rect.top())))
            lowerRight = astronomer.HexPosition(
                absoluteX=int(math.ceil(rect.right())),
                absoluteY=int(math.ceil(rect.bottom())))

            self._sloppyWorlds = self._universe.worldsInArea(
                upperLeft=upperLeft,
                lowerRight=lowerRight)

            if not self._worldSlop:
                self._tightWorlds = self._sloppyWorlds

        if tight and self._tightWorlds is None: # Specifically None to not recalculate if there are no worlds
            rect = cartographer.RectangleF()

            self._tightWorlds = []
            for world in self._sloppyWorlds:
                left, top, width, height = world.hex().worldBounds()
                rect.setRect(x=left, y=top, width=width, height=height)
                if self._rect.intersects(other=rect):
                    self._tightWorlds.append(world)
