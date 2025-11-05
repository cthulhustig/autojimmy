import astronomer
import cartographer
import math
import typing

class RectSelector(object):
    def __init__(
            self,
            milieu: astronomer.Milieu,
            universe: astronomer.Universe,
            sectorSlop: int = 1, # Numbers of sectors
            worldSlop: int = 1, # Number of parsecs
            ) -> None:
        self._milieu = milieu
        self._universe = universe
        self._sectorSlop = sectorSlop
        self._worldSlop = worldSlop
        self._rect = cartographer.RectangleF()

        self._tightSectors: typing.Optional[typing.List[astronomer.Sector]] = None
        self._sloppySectors: typing.Optional[typing.List[astronomer.Sector]] = None

        self._tightWorlds: typing.Optional[typing.List[astronomer.World]] = None
        self._sloppyWorlds: typing.Optional[typing.List[astronomer.World]] = None

        self._tightPlaceholderWorlds: typing.Optional[typing.List[astronomer.World]] = None
        self._sloppyPlaceholderWorlds: typing.Optional[typing.List[astronomer.World]] = None

        self._tightPlaceholderSectors: typing.Optional[typing.List[astronomer.Sector]] = None
        self._sloppyPlaceholderSectors: typing.Optional[typing.List[astronomer.Sector]] = None

    def rect(self) -> cartographer.RectangleF:
        return cartographer.RectangleF(self._rect)

    def setRect(self, rect: cartographer.RectangleF) -> None:
        if rect == self._rect:
            return
        self._rect = cartographer.RectangleF(rect)
        self._invalidate()

    def milieu(self) -> astronomer.Milieu:
        return self._milieu

    def setMilieu(self, milieu: astronomer.Milieu) -> None:
        if milieu is self._milieu:
            return
        self._milieu = milieu
        self._invalidate()

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

    def sectors(self, tight: bool = False) -> typing.Iterable[astronomer.Sector]:
        sectors = self._tightSectors if tight else self._sloppySectors
        if sectors is not None:
            return sectors

        self._cacheSectors(tight=tight)

        return self._tightSectors if tight else self._sloppySectors

    def worlds(self, tight: bool = False) -> typing.Iterable[astronomer.World]:
        worlds = self._tightWorlds if tight else self._sloppyWorlds
        if worlds is not None:
            return worlds

        self._cacheWorlds(tight=tight)

        return self._tightWorlds if tight else self._sloppyWorlds

    def placeholderSectors(self, tight: bool = False) -> typing.Iterable[astronomer.Sector]:
        sectors = self._tightPlaceholderSectors if tight else self._sloppyPlaceholderSectors
        if sectors is not None:
            return sectors

        self._cacheSectors(tight=tight)

        return self._tightPlaceholderSectors if tight else self._sloppyPlaceholderSectors

    def placeholderWorlds(self, tight: bool = False) -> typing.Iterable[astronomer.World]:
        placeholders = self._tightPlaceholderWorlds if tight else self._sloppyPlaceholderWorlds
        if placeholders is not None:
            return placeholders

        self._cacheWorlds(tight=tight)

        return self._tightPlaceholderWorlds if tight else self._sloppyPlaceholderWorlds

    def _invalidate(self) -> None:
        self._tightSectors = self._sloppySectors = None
        self._tightWorlds = self._sloppyWorlds = None
        self._tightPlaceholderWorlds = self._sloppyPlaceholderWorlds = None
        self._tightPlaceholderSectors = self._sloppyPlaceholderSectors = None

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

            usePlaceholders = self._milieu is not astronomer.Milieu.M1105
            sloppySectors = self._universe.sectorsInArea(
                milieu=self._milieu,
                upperLeft=upperLeft,
                lowerRight=lowerRight,
                includePlaceholders=usePlaceholders)
            if not usePlaceholders:
                self._sloppySectors = sloppySectors
                self._sloppyPlaceholderSectors = []
            else:
                self._sloppySectors = []
                self._sloppyPlaceholderSectors = []
                for sector in sloppySectors:
                    if sector.milieu() is self._milieu:
                        self._sloppySectors.append(sector)
                    else:
                        self._sloppyPlaceholderSectors.append(sector)

            if not self._sectorSlop:
                self._tightSectors = self._sloppySectors
                self._tightPlaceholderSectors = self._sloppyPlaceholderSectors

        if tight and self._tightSectors is None: # Specifically None to not recalculate if there are no sectors
            rect = cartographer.RectangleF()

            self._tightSectors = []
            for sector in self._sloppySectors:
                index = sector.index()
                left, top, width, height = index.worldBounds()
                rect.setRect(x=left, y=top, width=width, height=height)
                if self._rect.intersects(other=rect):
                    self._tightSectors.append(sector)

            self._tightPlaceholderSectors = []
            for sector in self._sloppyPlaceholderSectors:
                index = sector.index()
                left, top, width, height = index.worldBounds()
                rect.setRect(x=left, y=top, width=width, height=height)
                if self._rect.intersects(other=rect):
                    self._tightPlaceholderSectors.append(sector)

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

            usePlaceholders = self._milieu is not astronomer.Milieu.M1105
            sloppyWorlds = self._universe.worldsInArea(
                milieu=self._milieu,
                upperLeft=upperLeft,
                lowerRight=lowerRight,
                includePlaceholders=usePlaceholders)
            if not usePlaceholders:
                self._sloppyWorlds = sloppyWorlds
                self._sloppyPlaceholderWorlds = []
            else:
                self._sloppyWorlds = []
                self._sloppyPlaceholderWorlds = []
                for world in sloppyWorlds:
                    if world.milieu() is self._milieu:
                        self._sloppyWorlds.append(world)
                    else:
                        self._sloppyPlaceholderWorlds.append(world)

            if not self._worldSlop:
                self._tightWorlds = self._sloppyWorlds
                self._tightPlaceholderWorlds = self._sloppyPlaceholderWorlds

        if tight and self._tightWorlds is None: # Specifically None to not recalculate if there are no worlds
            rect = cartographer.RectangleF()

            self._tightWorlds = []
            for world in self._sloppyWorlds:
                left, top, width, height = world.hex().worldBounds()
                rect.setRect(x=left, y=top, width=width, height=height)
                if self._rect.intersects(other=rect):
                    self._tightWorlds.append(world)

            self._tightPlaceholderWorlds = []
            for world in self._sloppyPlaceholderWorlds:
                left, top, width, height = world.hex().worldBounds()
                rect.setRect(x=left, y=top, width=width, height=height)
                if self._rect.intersects(other=rect):
                    self._tightPlaceholderWorlds.append(world)
