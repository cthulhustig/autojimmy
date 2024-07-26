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
        worldX: int,
        worldY: int
        ) -> typing.Tuple[int, int]:
    worldX = (sectorX - ReferenceSectorX) * \
        SectorWidth + \
        (worldX - ReferenceHexX)
    worldY = (sectorY - ReferenceSectorY) * \
        SectorHeight + \
        (worldY - ReferenceHexY)
    return (worldX, worldY)

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
class NeighbourDirs(enum.Enum):
    Upper = 0
    UpperRight = 1
    LowerRight = 2
    Lower = 3
    LowerLeft = 4
    UpperLeft = 5

def neighbourAbsoluteHex(
        origin: typing.Tuple[int, int],
        direction: NeighbourDirs
        ) -> typing.Tuple[int, int]:
    hexX = origin[0]
    hexY = origin[1]
    if direction == NeighbourDirs.Upper:
        hexY -= 1
    elif direction == NeighbourDirs.UpperRight:
        hexY += 0 if (hexX % 2) else -1
        hexX += 1
    elif direction == NeighbourDirs.LowerRight:
        hexY += 1 if (hexX % 2) else 0
        hexX += 1
    elif direction == NeighbourDirs.Lower:
        hexY += 1
    elif direction == NeighbourDirs.LowerLeft:
        hexY += 1 if (hexX % 2) else 0
        hexX -= 1
    elif direction == NeighbourDirs.UpperLeft:
        hexY += 0 if (hexX % 2) else -1
        hexX -= 1
    else:
        raise ValueError('Invalid neighbour direction')
    return (hexX, hexY)

def neighbourRelativeHex(
        origin: typing.Tuple[int, int, int, int],
        direction: NeighbourDirs
        ) -> typing.Tuple[int, int, int, int]:
    sectorX = origin[0]
    sectorY = origin[1]
    hexX = origin[2]
    hexY = origin[3]

    if direction == NeighbourDirs.Upper:
        hexY -= 1
    elif direction == NeighbourDirs.UpperRight:
        hexY += -1 if (hexX % 2) else 0
        hexX += 1
    elif direction == NeighbourDirs.LowerRight:
        hexY += 0 if (hexX % 2) else 1
        hexX += 1
    elif direction == NeighbourDirs.Lower:
        hexY += 1
    elif direction == NeighbourDirs.LowerLeft:
        hexY += 0 if (hexX % 2) else 1
        hexX -= 1
    elif direction == NeighbourDirs.UpperLeft:
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
        current = neighbourAbsoluteHex(current, NeighbourDirs.UpperRight)
        yield current

    for _ in range(radius):
        current = neighbourAbsoluteHex(current, NeighbourDirs.Upper)
        yield current

    for _ in range(radius):
        current = neighbourAbsoluteHex(current, NeighbourDirs.UpperLeft)
        yield current

    for _ in range(radius):
        current = neighbourAbsoluteHex(current, NeighbourDirs.LowerLeft)
        yield current

    for _ in range(radius):
        current = neighbourAbsoluteHex(current, NeighbourDirs.Lower)
        yield current

    for _ in range(radius):
        current = neighbourAbsoluteHex(current, NeighbourDirs.LowerRight)
        yield current

def relativeRadiusHexes(
        centerSectorX: int,
        centerSectorY: int,
        centerHexX: int,
        centerHexY: int,
        radius: int
        ) -> typing.Generator[typing.Tuple[int, int, int, int], None, None]:
    if radius == 0:
        yield (centerSectorX, centerSectorY, centerHexX, centerHexY)
        return

    absoluteCenter = relativeHexToAbsoluteHex(
        sectorX=centerSectorX,
        sectorY=centerSectorY,
        worldX=centerHexX,
        worldY=centerHexY)
    current = absoluteHexToRelativeHex(
        absoluteX=absoluteCenter[0],
        absoluteY=absoluteCenter[1] + radius)

    for _ in range(radius):
        current = neighbourRelativeHex(current, NeighbourDirs.UpperRight)
        yield current

    for _ in range(radius):
        current = neighbourRelativeHex(current, NeighbourDirs.Upper)
        yield current

    for _ in range(radius):
        current = neighbourRelativeHex(current, NeighbourDirs.UpperLeft)
        yield current

    for _ in range(radius):
        current = neighbourRelativeHex(current, NeighbourDirs.LowerLeft)
        yield current

    for _ in range(radius):
        current = neighbourRelativeHex(current, NeighbourDirs.Lower)
        yield current

    for _ in range(radius):
        current = neighbourRelativeHex(current, NeighbourDirs.LowerRight)
        yield current
