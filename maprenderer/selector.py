import maprenderer
import math
import traveller
import travellermap
import typing

class RectSelector(object):
    def __init__(
            self,
            # TODO: Having this use graphics doesn't really make sense as it's only so
            # it can create a single rect. Might be nicer if it had it's own rect class
            # or something
            graphics: maprenderer.AbstractGraphics,
            sectorSlop: float = 0.3, # Arbitrary, but 0.25 not enough for some routes.
            subsectorSlop: float = 0.1,
            worldSlop: float = 0.1
            ) -> None:
        self._graphics = graphics
        self._sectorSlop = sectorSlop
        self._subsectorSlop = subsectorSlop
        self._worldSlop = worldSlop
        self._rect = self._graphics.createRectangle()

        self._cachedSectors: typing.Optional[typing.List[traveller.Sector]] = None
        self._cachedSubsectors: typing.Optional[typing.List[traveller.Subsector]] = None
        self._cachedWorlds: typing.Optional[typing.List[traveller.World]] = None

    def rect(self) -> maprenderer.AbstractRectangleF:
        return self._graphics.copyRectangle(self._rect)

    def setRect(self, rect: maprenderer.AbstractRectangleF) -> None:
        self._rect = self._graphics.copyRectangle(rect)
        self._cachedSectors = None
        self._cachedSubsectors = None
        self._cachedWorlds = None

    def sectorSlop(self) -> float:
        return self._sectorSlop

    def setSectorSlop(self, slop: float) -> None:
        self._sectorSlop = slop
        self._cachedSectors = None

    def subsectorSlop(self) -> float:
        return self._subsectorSlop

    def setSubsectorSlop(self, slop: float) -> None:
        self._subsectorSlop = slop
        self._cachedSubsectors = None

    def worldSlop(self) -> float:
        return self._sectorSlop

    def setWorldSlop(self, slop: float) -> None:
        self._sectorSlop = slop
        self._cachedWorlds = None

    def sectors(self) -> typing.Iterable[traveller.Sector]:
        if self._cachedSectors is not None:
            return self._cachedSectors

        rect = self._graphics.copyRectangle(self._rect)
        if self._sectorSlop:
            rect.inflate(
                x=rect.width() * self._sectorSlop,
                y=rect.height() * self._sectorSlop)

        left = int(math.floor((rect.left() + travellermap.ReferenceHexX) / travellermap.SectorWidth))
        right = int(math.floor((rect.right() + travellermap.ReferenceHexX) / travellermap.SectorWidth))

        top = int(math.floor((rect.top() + travellermap.ReferenceHexY) / travellermap.SectorHeight))
        bottom = int(math.floor((rect.bottom() + travellermap.ReferenceHexY) / travellermap.SectorHeight))

        self._cachedSectors = traveller.WorldManager.instance().sectorsInArea(
            upperLeft=travellermap.HexPosition(
                sectorX=left,
                sectorY=top,
                offsetX=travellermap.SectorWidth - 1, # TODO: Not sure about -1 here and below
                offsetY=travellermap.SectorHeight - 1),
            lowerRight=travellermap.HexPosition(
                sectorX=right,
                sectorY=bottom,
                offsetX=0, # TODO: Should this be 0 or 1 (same for below)
                offsetY=0))

        #print(f'Sectors={len(self._cachedSectors)}')

        return self._cachedSectors

    def subsectors(self) -> typing.Iterable[traveller.Subsector]:
        if self._cachedSubsectors is not None:
            return self._cachedSubsectors

        rect = self._graphics.copyRectangle(self._rect)
        if self._subsectorSlop:
            rect.inflate(
                x=rect.width() * self._subsectorSlop,
                y=rect.height() * self._subsectorSlop)

        left = int(math.floor(rect.left()))
        right = int(math.ceil(rect.right()))

        top = int(math.floor(rect.top()))
        bottom = int(math.ceil(rect.bottom()))

        self._cachedSubsectors = traveller.WorldManager.instance().subsectorsInArea(
            upperLeft=travellermap.HexPosition(absoluteX=left, absoluteY=top),
            lowerRight=travellermap.HexPosition(absoluteX=right, absoluteY=bottom))

        return self._cachedSubsectors

    def worlds(self) -> typing.Iterable[traveller.World]:
        if self._cachedWorlds is not None:
            return self._cachedWorlds

        rect = self._graphics.copyRectangle(self._rect)
        if self._worldSlop:
            rect.inflate(
                x=rect.width() * self._worldSlop,
                y=rect.height() * self._worldSlop)

        left = int(math.floor(rect.left()))
        right = int(math.ceil(rect.right()))

        top = int(math.floor(rect.top()))
        bottom = int(math.ceil(rect.bottom()))

        self._cachedWorlds = traveller.WorldManager.instance().worldsInArea(
            upperLeft=travellermap.HexPosition(absoluteX=left, absoluteY=top),
            lowerRight=travellermap.HexPosition(absoluteX=right, absoluteY=bottom))

        #print(f'Worlds={len(self._cachedWorlds)}')

        return self._cachedWorlds