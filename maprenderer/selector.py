import maprenderer
import math
import traveller
import travellermap
import typing

class RectSelector(object):
    def __init__(
            self,
            slop: float = 0.3 # Arbitrary, but 0.25 not enough for some routes.
            ) -> None:
        self._slop = slop
        self._rect = maprenderer.AbstractRectangleF()

        self._cachedSectors = None
        self._cachedWorlds = None

    def rect(self) -> maprenderer.AbstractRectangleF:
        return maprenderer.AbstractRectangleF(self._rect)

    def setRect(self, rect: maprenderer.AbstractRectangleF) -> None:
        self._rect = maprenderer.AbstractRectangleF(rect)
        self._cachedSectors = None
        self._cachedWorlds = None

    def slop(self) -> float:
        return self._slop

    def setSlop(self, slop) -> None:
        self._slop = slop
        self._cachedSectors = None
        self._cachedWorlds = None

    def sectors(self) -> typing.Iterable[traveller.Sector]:
        if self._cachedSectors is not None:
            return self._cachedSectors

        rect = maprenderer.AbstractRectangleF(self._rect)
        if self._slop:
            rect.inflate(
                x=rect.width() * self._slop,
                y=rect.height() * self._slop)

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

        return self._cachedSectors

    def worlds(self) -> typing.Iterable[traveller.World]:
        if self._cachedWorlds is not None:
            return self._cachedWorlds

        rect = maprenderer.AbstractRectangleF(self._rect)
        if self._slop:
            rect.inflate(
                x=rect.width() * self._slop,
                y=rect.height() * self._slop)

        left = int(math.floor(rect.left()))
        right = int(math.ceil(rect.right()))

        top = int(math.floor(rect.top()))
        bottom = int(math.ceil(rect.bottom()))

        self._cachedWorlds = traveller.WorldManager.instance().worldsInArea(
            upperLeft=travellermap.HexPosition(absoluteX=left, absoluteY=top),
            lowerRight=travellermap.HexPosition(absoluteX=right, absoluteY=bottom))

        return self._cachedWorlds