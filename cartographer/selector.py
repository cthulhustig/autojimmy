import cartographer
import math
import traveller
import travellermap
import typing

class RectSelector(object):
    def __init__(
            self,
            sectorSlop: int = 1, # Numbers of sectors
            subsectorSlop: int = 1, # Number of subsectors
            worldSlop: int = 1 # Number of parsecs
            ) -> None:
        self._sectorSlop = sectorSlop
        self._subsectorSlop = subsectorSlop
        self._worldSlop = worldSlop
        self._rect = cartographer.RectangleF()

        self._tightSectors: typing.Optional[typing.List[traveller.Sector]] = None
        self._sloppySectors: typing.Optional[typing.List[traveller.Sector]] = None

        self._tightSubsectors: typing.Optional[typing.List[traveller.Subsector]] = None
        self._sloppySubsectors: typing.Optional[typing.List[traveller.Subsector]] = None

        self._tightWorlds: typing.Optional[typing.List[traveller.World]] = None
        self._sloppyWorlds: typing.Optional[typing.List[traveller.World]] = None

        self._tightPlaceholderWorlds: typing.Optional[typing.List[traveller.PlaceholderWorld]] = None
        self._sloppyPlaceholderWorlds: typing.Optional[typing.List[traveller.PlaceholderWorld]] = None

        self._tightPlaceholderSectors: typing.Optional[typing.List[traveller.PlaceholderSector]] = None
        self._sloppyPlaceholderSectors: typing.Optional[typing.List[traveller.PlaceholderSector]] = None

    def rect(self) -> cartographer.RectangleF:
        return cartographer.RectangleF(self._rect)

    def setRect(self, rect: cartographer.RectangleF) -> None:
        self._rect = cartographer.RectangleF(rect)
        self._tightSectors = self._sloppySectors = None
        self._tightSubsectors = self._sloppySubsectors = None
        self._tightWorlds = self._sloppyWorlds = None
        self._tightPlaceholderWorlds = self._sloppyPlaceholderWorlds = None
        self._tightPlaceholderSectors = self._sloppyPlaceholderSectors = None

    def sectorSlop(self) -> float:
        return self._sectorSlop

    def setSectorSlop(self, slop: float) -> None:
        self._sectorSlop = slop
        self._sloppySectors = None

    def subsectorSlop(self) -> float:
        return self._subsectorSlop

    def setSubsectorSlop(self, slop: float) -> None:
        self._subsectorSlop = slop
        self._sloppySubsectors = None

    def worldSlop(self) -> float:
        return self._worldSlop

    def setWorldSlop(self, slop: float) -> None:
        self._worldSlop = slop
        self._sloppyWorlds = None

    def sectors(self, tight: bool = False) -> typing.Iterable[traveller.Sector]:
        sectors = self._tightSectors if tight else self._sloppySectors
        if sectors is not None:
            return sectors

        self._cacheSectors(tight=tight, placeholders=False)

        return self._tightSectors if tight else self._sloppySectors

    def subsectors(self, tight: bool = True) -> typing.Iterable[traveller.Subsector]:
        subsectors = self._tightSubsectors if tight else self._sloppySubsectors
        if subsectors is not None:
            return subsectors

        self._cacheSubsectors(tight=tight)

        return self._tightSubsectors if tight else self._sloppySubsectors

    def worlds(self, tight: bool = False) -> typing.Iterable[traveller.World]:
        worlds = self._tightWorlds if tight else self._sloppyWorlds
        if worlds is not None:
            return worlds

        self._cacheWorlds(tight=tight, placeholders=False)

        return self._tightWorlds if tight else self._sloppyWorlds

    def placeholderSectors(self, tight: bool = False) -> typing.Iterable[traveller.PlaceholderSector]:
        sectors = self._tightPlaceholderSectors if tight else self._sloppyPlaceholderSectors
        if sectors is not None:
            return sectors

        self._cacheSectors(tight=tight, placeholders=True)

        return self._tightPlaceholderSectors if tight else self._sloppyPlaceholderSectors

    def placeholderWorlds(self, tight: bool = False) -> typing.Iterable[traveller.PlaceholderWorld]:
        placeholders = self._tightPlaceholderWorlds if tight else self._sloppyPlaceholderWorlds
        if placeholders is not None:
            return placeholders

        self._cacheWorlds(tight=tight, placeholders=True)

        return self._tightPlaceholderWorlds if tight else self._sloppyPlaceholderWorlds

    def _cacheSectors(
            self,
            tight: bool,
            placeholders: bool
            ) -> None:
        sloppySectors = self._sloppyPlaceholderSectors if placeholders else self._sloppySectors
        tightSectors = self._tightPlaceholderSectors if placeholders else self._tightSectors

        if sloppySectors is None: # Specifically None to not recalculate if there are no sectors
            sloppyRect = cartographer.RectangleF(self._rect)
            if self._sectorSlop:
                sloppyRect.inflate(
                    x=self._sectorSlop * travellermap.SectorWidth,
                    y=self._sectorSlop * travellermap.SectorHeight)

            upperLeft = travellermap.HexPosition(
                sectorX=int(math.floor((sloppyRect.left() + travellermap.ReferenceHexX) / travellermap.SectorWidth)),
                sectorY=int(math.floor((sloppyRect.top() + travellermap.ReferenceHexY) / travellermap.SectorHeight)),
                offsetX=travellermap.SectorWidth - 1,
                offsetY=travellermap.SectorHeight - 1)
            lowerRight = travellermap.HexPosition(
                sectorX=int(math.floor((sloppyRect.right() + travellermap.ReferenceHexX) / travellermap.SectorWidth)),
                sectorY=int(math.floor((sloppyRect.bottom() + travellermap.ReferenceHexY) / travellermap.SectorHeight)),
                offsetX=0,
                offsetY=0)

            if placeholders:
                sloppySectors = traveller.WorldManager.instance().placeholderSectorsInArea(
                    upperLeft=upperLeft,
                    lowerRight=lowerRight)
                self._sloppyPlaceholderSectors = sloppySectors
            else:
                sloppySectors = traveller.WorldManager.instance().sectorsInArea(
                    upperLeft=upperLeft,
                    lowerRight=lowerRight)
                self._sloppySectors = sloppySectors

            if not self._sectorSlop:
                tightSectors = sloppySectors
                if placeholders:
                    self._tightPlaceholderSectors = tightSectors
                else:
                    self._tightSectors = tightSectors

        if tight and tightSectors is None: # Specifically None to not recalculate if there are no sectors
            rect = cartographer.RectangleF()
            tightSectors = []
            for sector in sloppySectors:
                left, top, width, height = travellermap.sectorBoundingRect(
                    sector=(sector.x(), sector.y()))
                rect.setRect(x=left, y=top, width=width, height=height)
                if self._rect.intersects(other=rect):
                    tightSectors.append(sector)

            if placeholders:
                self._tightPlaceholderSectors = tightSectors
            else:
                self._tightSectors = tightSectors

    def _cacheSubsectors(
            self,
            tight: bool
            ) -> None:
        if self._sloppySubsectors is None: # Specifically None to not recalculate if there are no subsectors
            sloppyRect = cartographer.RectangleF(self._rect)
            if self._subsectorSlop:
                sloppyRect.inflate(
                    x=self._subsectorSlop * travellermap.SubsectorWidth,
                    y=self._subsectorSlop * travellermap.SubsectorHeight)

            upperLeft = travellermap.HexPosition(
                absoluteX=int(math.floor(sloppyRect.left())),
                absoluteY=int(math.floor(sloppyRect.top())))
            lowerRight = travellermap.HexPosition(
                absoluteX=int(math.ceil(sloppyRect.right())),
                absoluteY=int(math.ceil(sloppyRect.bottom())))

            self._sloppySubsectors = traveller.WorldManager.instance().subsectorsInArea(
                upperLeft=upperLeft,
                lowerRight=lowerRight)

            if not self._subsectorSlop:
                self._tightSubsectors = self._sloppySubsectors

        if tight and self._tightSubsectors is None: # Specifically None to not recalculate if there are no subsectors
            rect = cartographer.RectangleF()
            self._tightSubsectors = []
            for subsector in self._sloppySubsectors:
                left, top, width, height = travellermap.subsectorBoundingRect(
                    subsector=(
                        subsector.sectorX(), subsector.sectorY(),
                        subsector.indexX(), subsector.indexY()))
                rect.setRect(x=left, y=top, width=width, height=height)
                if self._rect.intersects(other=rect):
                    self._tightSubsectors.append(subsector)

    def _cacheWorlds(
            self,
            tight: bool,
            placeholders: bool
            ) -> None:
        sloppyWorlds = self._sloppyPlaceholderWorlds if placeholders else self._sloppyWorlds
        tightWorlds = self._tightPlaceholderWorlds if placeholders else self._tightWorlds

        if sloppyWorlds is None: # Specifically None to not recalculate if there are no worlds
            rect = cartographer.RectangleF(self._rect)
            if self._worldSlop:
                rect.inflate(x=self._worldSlop, y=self._worldSlop)

            upperLeft = travellermap.HexPosition(
                absoluteX=int(math.floor(rect.left())),
                absoluteY=int(math.floor(rect.top())))
            lowerRight = travellermap.HexPosition(
                absoluteX=int(math.ceil(rect.right())),
                absoluteY=int(math.ceil(rect.bottom())))

            if placeholders:
                sloppyWorlds = traveller.WorldManager.instance().placeholderWorldsInArea(
                    upperLeft=upperLeft,
                    lowerRight=lowerRight)
                self._sloppyPlaceholderWorlds = sloppyWorlds
            else:
                sloppyWorlds = traveller.WorldManager.instance().worldsInArea(
                    upperLeft=upperLeft,
                    lowerRight=lowerRight)
                self._sloppyWorlds = sloppyWorlds

            if not self._worldSlop:
                tightWorlds = sloppyWorlds
                if placeholders:
                    self._tightPlaceholderWorlds = tightWorlds
                else:
                    self._tightWorlds = tightWorlds

        if tight and tightWorlds is None: # Specifically None to not recalculate if there are no worlds
            rect = cartographer.RectangleF()
            tightWorlds = []
            for world in sloppyWorlds:
                left, top, width, height = world.hex().absoluteBounds()
                rect.setRect(x=left, y=top, width=width, height=height)
                if self._rect.intersects(other=rect):
                    tightWorlds.append(world)

            if placeholders:
                self._tightPlaceholderWorlds = tightWorlds
            else:
                self._tightWorlds = tightWorlds
