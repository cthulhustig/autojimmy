import re
import typing

_SectorWidth = 32
_SectorHeight = 40
_ReferenceSectorX = 0
_ReferenceSectorY = 0
_ReferenceHexX = 1
_ReferenceHexY = 40
_SectorHexPattern = re.compile('^(.*) ([0-9]{2})([0-9]{2})$')

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

def splitSectorHex(
        sectorHex: str
        ) -> typing.Tuple[str, str]:
    result = _SectorHexPattern.match(sectorHex)
    if not result:
        raise ValueError(f'Invalid sector hex string "{sectorHex}"')
    return (result.group(1), int(result.group(2)), int(result.group(3)))

def formatSectorHex(
        sectorName: str,
        worldX: typing.Union[int, str],
        worldY: typing.Union[int, str]
        ) -> str:
    return f'{sectorName} {int(worldX):02d}{int(worldY):02d}'
