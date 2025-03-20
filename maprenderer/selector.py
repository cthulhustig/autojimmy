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
            sectorSlop: int = 1, # Numbers of sectors
            subsectorSlop: int = 1, # Number of subsectors
            worldSlop: int = 1 # Number of parsecs
            ) -> None:
        self._graphics = graphics
        self._sectorSlop = sectorSlop
        self._subsectorSlop = subsectorSlop
        self._worldSlop = worldSlop
        self._rect = maprenderer.RectangleF()

        self._tightSectors: typing.Optional[typing.List[traveller.Sector]] = None
        self._sloppySectors: typing.Optional[typing.List[traveller.Sector]] = None

        self._tightSubsectors: typing.Optional[typing.List[traveller.Subsector]] = None
        self._sloppySubsectors: typing.Optional[typing.List[traveller.Subsector]] = None

        self._tightWorlds: typing.Optional[typing.List[traveller.World]] = None
        self._sloppyWorlds: typing.Optional[typing.List[traveller.World]] = None

    def rect(self) -> maprenderer.RectangleF:
        return maprenderer.RectangleF(self._rect)

    def setRect(self, rect: maprenderer.RectangleF) -> None:
        self._rect = maprenderer.RectangleF(rect)
        self._tightSectors = self._sloppySectors = None
        self._tightSubsectors = self._sloppySubsectors = None
        self._tightWorlds = self._sloppyWorlds = None

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

        sloppyRect = maprenderer.RectangleF(self._rect)
        if self._sectorSlop:
            sloppyRect.inflate(
                x=self._sectorSlop * travellermap.SectorWidth,
                y=self._sectorSlop * travellermap.SectorHeight)

        left = int(math.floor((sloppyRect.left() + travellermap.ReferenceHexX) / travellermap.SectorWidth))
        right = int(math.floor((sloppyRect.right() + travellermap.ReferenceHexX) / travellermap.SectorWidth))
        top = int(math.floor((sloppyRect.top() + travellermap.ReferenceHexY) / travellermap.SectorHeight))
        bottom = int(math.floor((sloppyRect.bottom() + travellermap.ReferenceHexY) / travellermap.SectorHeight))

        self._sloppySectors = traveller.WorldManager.instance().sectorsInArea(
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

        if not self._sectorSlop:
            self._tightSectors = self._sloppySectors

        if tight and self._tightSectors is None:
            rect = maprenderer.RectangleF()
            self._tightSectors = []
            for sector in self._sloppySectors:
                left, top, width, height = travellermap.sectorBoundingRect(
                    sector=(sector.x(), sector.y()))
                rect.setRect(x=left, y=top, width=width, height=height)
                if self._rect.intersectsWith(other=rect):
                    self._tightSectors.append(sector)

        #print('Sectors: Sloppy={sloppy} Tight={tight}'.format(
        #    sloppy=len(self._sloppySectors),
        #    tight=len(self._tightSectors) if self._tightSectors is not None else 'None'))

        return self._tightSectors if tight else self._sloppySectors

    def subsectors(self, tight: bool = True) -> typing.Iterable[traveller.Subsector]:
        subsectors = self._tightSubsectors if tight else self._sloppySubsectors
        if subsectors is not None:
            return subsectors

        sloppyRect = maprenderer.RectangleF(self._rect)
        if self._subsectorSlop:
            sloppyRect.inflate(
                x=self._subsectorSlop * travellermap.SubsectorWidth,
                y=self._subsectorSlop * travellermap.SubsectorHeight)

        left = int(math.floor(sloppyRect.left()))
        right = int(math.ceil(sloppyRect.right()))

        top = int(math.floor(sloppyRect.top()))
        bottom = int(math.ceil(sloppyRect.bottom()))

        self._sloppySubsectors = traveller.WorldManager.instance().subsectorsInArea(
            upperLeft=travellermap.HexPosition(absoluteX=left, absoluteY=top),
            lowerRight=travellermap.HexPosition(absoluteX=right, absoluteY=bottom))

        if not self._subsectorSlop:
            self._tightSubsectors = self._sloppySubsectors

        if tight and self._tightSubsectors is None:
            rect = maprenderer.RectangleF()
            self._tightSubsectors = []
            for subsector in self._sloppySubsectors:
                left, top, width, height = travellermap.subsectorBoundingRect(
                    subsector=(
                        subsector.sectorX(), subsector.sectorY(),
                        subsector.indexX(), subsector.indexY()))
                rect.setRect(x=left, y=top, width=width, height=height)
                if self._rect.intersectsWith(other=rect):
                    self._tightSubsectors.append(subsector)

        #print('Subsectors: Sloppy={sloppy} Tight={tight}'.format(
        #    sloppy=len(self._sloppySubsectors),
        #    tight=len(self._tightSubsectors) if self._tightSubsectors is not None else 'None'))

        return self._tightSubsectors if tight else self._sloppySubsectors

    def worlds(self, tight: bool = False) -> typing.Iterable[traveller.World]:
        worlds = self._tightWorlds if tight else self._sloppyWorlds
        if worlds is not None:
            return worlds

        rect = maprenderer.RectangleF(self._rect)
        if self._worldSlop:
            rect.inflate(x=self._worldSlop, y=self._worldSlop)

        left = int(math.floor(rect.left()))
        right = int(math.ceil(rect.right()))

        top = int(math.floor(rect.top()))
        bottom = int(math.ceil(rect.bottom()))

        self._sloppyWorlds = traveller.WorldManager.instance().worldsInArea(
            upperLeft=travellermap.HexPosition(absoluteX=left, absoluteY=top),
            lowerRight=travellermap.HexPosition(absoluteX=right, absoluteY=bottom))

        if not self._worldSlop:
            self._tightWorlds = self._sloppyWorlds

        if tight and self._tightWorlds is None:
            rect = maprenderer.RectangleF()
            self._tightWorlds = []
            for world in self._sloppyWorlds:
                left, top, width, height = travellermap.hexBoundingRect(
                    absolute=world.hex().absolute())
                rect.setRect(x=left, y=top, width=width, height=height)
                if self._rect.intersectsWith(other=rect):
                    self._tightWorlds.append(world)

        #print('Worlds: Sloppy={sloppy} Tight={tight}'.format(
        #    sloppy=len(self._sloppyWorlds),
        #    tight=len(self._tightWorlds) if self._tightWorlds is not None else 'None'))

        return self._tightWorlds if tight else self._sloppyWorlds