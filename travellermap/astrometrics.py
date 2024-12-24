import enum
import math
import typing

SectorWidth = 32
SectorHeight = 40
ReferenceSectorX = 0
ReferenceSectorY = 0
ReferenceHexX = 1
ReferenceHexY = 40
TravellerMapTileSize = 256
ParsecScaleX = math.cos(math.pi / 6) # cosine 30°
ParsecScaleY = 1
HexWidthOffset = math.tan(math.pi / 6) / 4 / ParsecScaleX

# I've pinched this diagram from Traveller Map (RenderUtils.cs)
# It shows how the size of hexes are calculated
#                    1
#            +-*------------*x+
#            |/              \|
#            /                \
#           /|                |\
#          * |                +x*  x = tan( pi / 6 ) / 4
#           \|                |/
#            \                /
#            |\              /|
#            +-*------------*-+

# Implementation taken from https://travellermap.com/doc/api
def relativeHexToAbsoluteHex(
        sectorX: int,
        sectorY: int,
        offsetX: int,
        offsetY: int
        ) -> typing.Tuple[int, int]:
    absoluteX = (sectorX - ReferenceSectorX) * \
        SectorWidth + \
        (offsetX - ReferenceHexX)
    absoluteY = (sectorY - ReferenceSectorY) * \
        SectorHeight + \
        (offsetY - ReferenceHexY)
    return (absoluteX, absoluteY)

# Reimplementation of code from Traveller Map source code.
# CoordinatesToLocation in Astrometrics.cs
def absoluteHexToRelativeHex(
        absoluteX: int,
        absoluteY: int
        ) -> typing.Tuple[int, int, int, int]:
    absoluteX += ReferenceHexX - 1
    absoluteY += ReferenceHexY - 1
    sectorX = absoluteX // SectorWidth
    sectorY = absoluteY // SectorHeight
    worldX = absoluteX - (sectorX * SectorWidth) + 1
    worldY = absoluteY - (sectorY * SectorHeight) + 1
    return (sectorX, sectorY, worldX, worldY)

def absoluteHexToMapSpace(
        absoluteX: int,
        absoluteY: int
        ) -> typing.Tuple[float, float]:
    ix = absoluteX - 0.5
    iy = absoluteY - 0.5 if (absoluteX % 2) == 0 else absoluteY
    x = ix * ParsecScaleX
    y = iy * -ParsecScaleY
    return x, y

def mapSpaceToTileSpace(
        mapX: int,
        mapY: int,
        scale: float
        ) -> typing.Tuple[int, int]:
    scalar = scale / TravellerMapTileSize
    return (mapX * scalar, -mapY * scalar)

def tileSpaceToMapSpace(
        tileX,
        tileY,
        scale: float
        ) -> typing.Tuple[int, int]:
    scalar = scale / TravellerMapTileSize
    return (tileX / scalar, -tileY / scalar)

# This gets the bounding rect of a sector in absolute coordinates (world coordinates in Traveller
# Map parlance). It's based on Bounds from Traveller Map (Sector.cs) but I've updated it so it
# returns a bounding box that contains the full extent of all hexes in the sector.
def sectorBoundingRect(
        sectorX: int,
        sectorY: int
        ) -> typing.Tuple[int, int, int, int]:
    left = (sectorX * SectorWidth) - ReferenceHexX
    bottom = (sectorY * SectorHeight) - ReferenceHexY
    width = SectorWidth
    height = SectorHeight

    # Adjust to completely contain all hexes in the sector
    height += 0.5
    left += 0.5 - HexWidthOffset
    width += HexWidthOffset * 2

    return (left, bottom, width, height)

# Similar to sectorBoundingRect but gets the largest absolute coordinate rect that can
# fit inside the sector without overlapping any hexes from adjacent sectors. This is
# useful as any rect that falls completely inside this rect is guaranteed to only cover
# this sector
def sectorInteriorRect(
        sectorX: int,
        sectorY: int
        ) -> typing.Tuple[int, int, int, int]:
    left = (sectorX * SectorWidth) - ReferenceHexX
    bottom = (sectorY * SectorHeight) - ReferenceHexY
    width = SectorWidth
    height = SectorHeight

    # Shrink to fit within the hexes of this sector
    bottom += 0.5
    height -= 1
    left += 0.5 + HexWidthOffset
    width -= (HexWidthOffset * 2)

    return (left, bottom, width, height)

# Reimplementation of code from Traveller Map source code.
# HexDistance in Astrometrics.cs
def hexDistance(
        absoluteX1: int,
        absoluteY1: int,
        absoluteX2: int,
        absoluteY2: int
        ) -> int:
    dx = absoluteX2 - absoluteX1
    dy = absoluteY2 - absoluteY1

    adx = dx if dx >= 0 else -dx

    ody = dy + (adx // 2)

    if ((absoluteX1 & 0b1) == 0) and ((absoluteX2 & 0b1) != 0):
        ody += 1

    max = ody if ody > adx else adx
    adx -= ody
    return adx if adx > max else max

# TODO: These are currently labelled visually (i.e. lower is towards the bottom
# of the screen) but I think the coordinate system is actually increasing in
# that direction so the y value would be larger than the upper y value. Need to
# see if there is a canonical way to refer to the edges in the Traveller Map
# source code
class NeighbourDirection(enum.Enum):
    Upper = 0
    UpperRight = 1
    LowerRight = 2
    Lower = 3
    LowerLeft = 4
    UpperLeft = 5

def neighbourAbsoluteHex(
        origin: typing.Tuple[int, int],
        direction: NeighbourDirection
        ) -> typing.Tuple[int, int]:
    hexX = origin[0]
    hexY = origin[1]
    if direction == NeighbourDirection.Upper:
        hexY -= 1
    elif direction == NeighbourDirection.UpperRight:
        hexY += 0 if (hexX % 2) else -1
        hexX += 1
    elif direction == NeighbourDirection.LowerRight:
        hexY += 1 if (hexX % 2) else 0
        hexX += 1
    elif direction == NeighbourDirection.Lower:
        hexY += 1
    elif direction == NeighbourDirection.LowerLeft:
        hexY += 1 if (hexX % 2) else 0
        hexX -= 1
    elif direction == NeighbourDirection.UpperLeft:
        hexY += 0 if (hexX % 2) else -1
        hexX -= 1
    else:
        raise ValueError('Invalid neighbour direction')
    return (hexX, hexY)

def neighbourRelativeHex(
        origin: typing.Tuple[int, int, int, int],
        direction: NeighbourDirection
        ) -> typing.Tuple[int, int, int, int]:
    sectorX = origin[0]
    sectorY = origin[1]
    hexX = origin[2]
    hexY = origin[3]

    if direction == NeighbourDirection.Upper:
        hexY -= 1
    elif direction == NeighbourDirection.UpperRight:
        hexY += -1 if (hexX % 2) else 0
        hexX += 1
    elif direction == NeighbourDirection.LowerRight:
        hexY += 0 if (hexX % 2) else 1
        hexX += 1
    elif direction == NeighbourDirection.Lower:
        hexY += 1
    elif direction == NeighbourDirection.LowerLeft:
        hexY += 0 if (hexX % 2) else 1
        hexX -= 1
    elif direction == NeighbourDirection.UpperLeft:
        hexY += -1 if (hexX % 2) else 0
        hexX -= 1
    else:
        raise ValueError('Invalid neighbour direction')

    if hexX == 0:
        hexX = 32
        sectorX -= 1
    if hexX == 33:
        hexX = 1
        sectorX += 1
    if hexY == 0:
        hexY = 40
        sectorY -= 1
    if hexY == 41:
        hexY = 1
        sectorY += 1

    return (sectorX, sectorY, hexX, hexY)

def absoluteRadiusHexes(
        centerX: int,
        centerY: int,
        radius: int
        ) -> typing.Generator[typing.Tuple[int, int], None, None]:
    if radius == 0:
        yield (centerX, centerY)
        return

    current = (centerX, centerY + radius)

    for _ in range(radius):
        current = neighbourAbsoluteHex(current, NeighbourDirection.UpperRight)
        yield current

    for _ in range(radius):
        current = neighbourAbsoluteHex(current, NeighbourDirection.Upper)
        yield current

    for _ in range(radius):
        current = neighbourAbsoluteHex(current, NeighbourDirection.UpperLeft)
        yield current

    for _ in range(radius):
        current = neighbourAbsoluteHex(current, NeighbourDirection.LowerLeft)
        yield current

    for _ in range(radius):
        current = neighbourAbsoluteHex(current, NeighbourDirection.Lower)
        yield current

    for _ in range(radius):
        current = neighbourAbsoluteHex(current, NeighbourDirection.LowerRight)
        yield current

def relativeRadiusHexes(
        centerSectorX: int,
        centerSectorY: int,
        centerOffsetX: int,
        centerOffsetY: int,
        radius: int
        ) -> typing.Generator[typing.Tuple[int, int, int, int], None, None]:
    if radius == 0:
        yield (centerSectorX, centerSectorY, centerOffsetX, centerOffsetY)
        return

    absoluteCenter = relativeHexToAbsoluteHex(
        sectorX=centerSectorX,
        sectorY=centerSectorY,
        offsetX=centerOffsetX,
        offsetY=centerOffsetY)
    current = absoluteHexToRelativeHex(
        absoluteX=absoluteCenter[0],
        absoluteY=absoluteCenter[1] + radius)

    for _ in range(radius):
        current = neighbourRelativeHex(current, NeighbourDirection.UpperRight)
        yield current

    for _ in range(radius):
        current = neighbourRelativeHex(current, NeighbourDirection.Upper)
        yield current

    for _ in range(radius):
        current = neighbourRelativeHex(current, NeighbourDirection.UpperLeft)
        yield current

    for _ in range(radius):
        current = neighbourRelativeHex(current, NeighbourDirection.LowerLeft)
        yield current

    for _ in range(radius):
        current = neighbourRelativeHex(current, NeighbourDirection.Lower)
        yield current

    for _ in range(radius):
        current = neighbourRelativeHex(current, NeighbourDirection.LowerRight)
        yield current

class HexPosition(object):
    def __init__(
            self,
            absoluteX: typing.Optional[int] = None,
            absoluteY: typing.Optional[int] = None,
            sectorX: typing.Optional[int] = None,
            sectorY: typing.Optional[int] = None,
            offsetX: typing.Optional[int] = None,
            offsetY: typing.Optional[int] = None
            ):
        isAbsolute = absoluteX != None and absoluteY != None
        isRelative = sectorX != None and sectorY != None and offsetX != None and offsetY != None
        if not (isAbsolute or isRelative):
            raise ValueError('Hex position must be absolute or relative')
        elif isAbsolute and isRelative:
            raise ValueError('Hex position can\'t be absolute and relative')

        if isAbsolute:
            self._absoluteX = int(absoluteX)
            self._absoluteY = int(absoluteY)
            self._sectorX, self._sectorY, self._offsetX, self._offsetY = \
                absoluteHexToRelativeHex(
                    absoluteX=self._absoluteX,
                    absoluteY=self._absoluteY)
        else:
            self._sectorX = int(sectorX)
            self._sectorY = int(sectorY)
            self._offsetX = int(offsetX)
            self._offsetY = int(offsetY)
            self._absoluteX, self._absoluteY = \
                relativeHexToAbsoluteHex(
                    sectorX=self._sectorX,
                    sectorY=self._sectorY,
                    offsetX=self._offsetX,
                    offsetY=self._offsetY)

    def __eq__(self, other):
        if isinstance(other, HexPosition):
            # Only need to compare absolute position
            return self._absoluteX == other._absoluteX and \
                self._absoluteY == other._absoluteY
        return super().__eq__(other)

    def __lt__(self, other: 'HexPosition') -> bool:
        if isinstance(other, HexPosition):
            if self._absoluteY < other._absoluteY:
                return True
            elif self._absoluteY > other._absoluteY:
                return False
            return self._absoluteX < other._absoluteX
        return super().__lt__(other)

    def absoluteX(self) -> int:
        return self._absoluteX

    def absoluteY(self) -> int:
        return self._absoluteY

    def absolute(self) -> typing.Tuple[int, int]:
        return (self._absoluteX, self._absoluteY)

    def sectorX(self) -> int:
        return self._sectorX

    def sectorY(self) -> int:
        return self._sectorY

    def offsetX(self) -> int:
        return self._offsetX

    def offsetY(self) -> int:
        return self._offsetY

    def relative(self) -> typing.Tuple[int, int, int, int]:
        return (self._sectorX, self._sectorY, self._offsetX, self._offsetY)

    def mapSpace(self) -> typing.Tuple[float, float]:
        return absoluteHexToMapSpace(
            absoluteX=self._absoluteX,
            absoluteY=self._absoluteY)

    def parsecsTo(
            self,
            other: 'HexPosition'
            ) -> int:
        return hexDistance(
            absoluteX1=self._absoluteX,
            absoluteY1=self._absoluteY,
            absoluteX2=other._absoluteX,
            absoluteY2=other._absoluteY)

    def neighbourHex(
            self,
            direction: NeighbourDirection
            ) -> 'HexPosition':
        neighbourX, neighbourY = neighbourAbsoluteHex(
            origin=(self._absoluteX, self._absoluteY),
            direction=direction)
        return HexPosition(absoluteX=neighbourX, absoluteY=neighbourY)

    def yieldRadiusHexes(
            self,
            radius: int,
            maxOnly: bool = False
            ) -> typing.Generator['HexPosition', None, None]:
        while radius >= 0:
            generator = absoluteRadiusHexes(
                centerX=self._absoluteX,
                centerY=self._absoluteY,
                radius=radius)
            for absoluteX, absoluteY in generator:
                yield HexPosition(absoluteX=absoluteX, absoluteY=absoluteY)

            if maxOnly:
                return
            radius -= 1