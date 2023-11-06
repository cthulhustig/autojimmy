import enum
import math
import typing

_SectorWidth = 32
_SectorHeight = 40
_ReferenceSectorX = 0
_ReferenceSectorY = 0
_ReferenceHexX = 1
_ReferenceHexY = 40
_TravellerMapTileSize = 256
_ParsecScaleX = math.cos(math.pi / 6) # cosine 30°
_ParsecScaleY = 1
_HexEdgePadding = math.tan(math.pi / 6) / 4 / _ParsecScaleX

# Implementation taken from https://travellermap.com/doc/api
def relativeHexToAbsoluteHex(
        sectorX: int,
        sectorY: int,
        worldX: int,
        worldY: int
        ) -> typing.Tuple[int, int]:
    worldX = (sectorX - _ReferenceSectorX) * \
        _SectorWidth + \
        (worldX - _ReferenceHexX)
    worldY = (sectorY - _ReferenceSectorY) * \
        _SectorHeight + \
        (worldY - _ReferenceHexY)
    return (worldX, worldY)

# Reimplementation of code from Traveller Map source code.
# CoordinatesToLocation in Astrometrics.cs
def absoluteHexToRelativeHex(
        absoluteX: int,
        absoluteY: int
        ) -> typing.Tuple[int, int, int, int]:
    absoluteX += _ReferenceHexX - 1
    absoluteY += _ReferenceHexY - 1
    sectorX = absoluteX // _SectorWidth
    sectorY = absoluteY // _SectorHeight
    worldX = absoluteX - (sectorX * _SectorWidth) + 1
    worldY = absoluteY - (sectorY * _SectorHeight) + 1
    return (sectorX, sectorY, worldX, worldY)

def absoluteHexToMapSpace(
        absoluteX: int,
        absoluteY: int
        ) -> typing.Tuple[float, float]:
    ix = absoluteX - 0.5
    iy = absoluteY - 0.5 if (absoluteX % 2) == 0 else absoluteY
    x = ix * _ParsecScaleX
    y = iy * -_ParsecScaleY
    return x, y

def mapSpaceToTileSpace(
        mapX: int,
        mapY: int,
        scale: float
        ) -> typing.Tuple[int, int]:
    scalar = scale / _TravellerMapTileSize
    return (mapX * scalar, -mapY * scalar)

def tileSpaceToMapSpace(
        tileX,
        tileY,
        scale: float
        ) -> typing.Tuple[int, int]:
    scalar = scale / _TravellerMapTileSize
    return (tileX / scalar, -tileY / scalar)

# This gets the bounding rect of a sector in absolute coordinates (world coordinates in Traveller
# Map parlance). It's based on Bounds from Traveller Map (Sector.cs) but I've updated it so it
# returns a bounding box that contains the full extent of all hexes in the sector.
def sectorBoundingRect(
        sectorX: int,
        sectorY: int
        ) -> typing.Tuple[int, int, int, int]:
    left = (sectorX * _SectorWidth) - _ReferenceHexX
    bottom = (sectorY * _SectorHeight) - _ReferenceHexY
    width = _SectorWidth
    height = _SectorHeight

    # Adjust to completely contain all hexes in the sector
    height += 0.5
    left += 0.5 - _HexEdgePadding
    width += _HexEdgePadding * 2

    return (left, bottom, width, height)

# Similar to sectorBoundingRect but gets the largest absolute coordinate rect that can
# fit inside the sector without overlapping any hexes from adjacent sectors. This is
# useful as any rect that falls completely inside this rect is guaranteed to only cover
# this sector
def sectorInteriorRect(
        sectorX: int,
        sectorY: int
        ) -> typing.Tuple[int, int, int, int]:
    left = (sectorX * _SectorWidth) - _ReferenceHexX
    bottom = (sectorY * _SectorHeight) - _ReferenceHexY
    width = _SectorWidth
    height = _SectorHeight

    # Shrink to fit within the hexes of this sector
    bottom += 0.5
    height -= 1
    left += 0.5 + _HexEdgePadding
    width -= (_HexEdgePadding * 2)

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

class NeighbourDirs(enum.Enum):
    Upper = 0
    UpperRight = 1
    LowerRight = 2
    Lower = 3
    LowerLeft = 4
    UpperLeft = 5

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