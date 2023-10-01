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
# Map parlance). It's based on SubsectorBounds from Traveller Map (Sector.cs) but I've updated it
# so it returns a bounding box that contains the full extent of all hexes in the sector.
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
    left -= _HexEdgePadding
    width += _HexEdgePadding * 2

    # TODO: Why do I need this?????. It might be an even/odd sector index thing.
    # Need to test with sectors that have even/odd x & y values
    left += 0.5

    return (left, bottom, width, height) # Height

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
