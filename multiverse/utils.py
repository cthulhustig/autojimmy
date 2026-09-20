import enum
import typing

# TODO: This is all duplicated from astrometrics

def parsecsBetweenAbsoluteSpace(
        pos1: typing.Tuple[int, int],
        pos2: typing.Tuple[int, int]
        ) -> int:
    dx = pos2[0] - pos1[0]
    dy = pos2[1] - pos1[1]

    adx = dx if dx >= 0 else -dx

    ody = dy + (adx // 2)

    if ((pos1[0] & 0b1) == 0) and ((pos2[0] & 0b1) != 0):
        ody += 1

    max = ody if ody > adx else adx
    adx -= ody
    return adx if adx > max else max

ReferenceSectorX = 0
ReferenceSectorY = 0
ReferenceHexX = 1
ReferenceHexY = 40
SectorWidth = 32
SectorHeight = 40
def sectorHexToWorldSpace(
        sectorX: int,
        sectorY: int,
        hexX: int,
        hexY: int
        ) -> typing.Tuple[float, float]:
    absX = (sectorX - ReferenceSectorX) * \
        SectorWidth + \
        (hexX - ReferenceHexX)
    absY = (sectorY - ReferenceSectorY) * \
        SectorHeight + \
        (hexY - ReferenceHexY)
    return (
        absX - 0.5,
        absY - (0.0 if ((absX % 2) != 0) else 0.5))

def relativeSpaceToAbsoluteSpace(
        pos: typing.Tuple[int, int, int, int],
        ) -> typing.Tuple[int, int]:
    absoluteX = (pos[0] - ReferenceSectorX) * \
        SectorWidth + \
        (pos[2] - ReferenceHexX)
    absoluteY = (pos[1] - ReferenceSectorY) * \
        SectorHeight + \
        (pos[3] - ReferenceHexY)
    return (absoluteX, absoluteY)

class PathWinding(enum.Enum):
    Clockwise = 0
    AntiClockwise = 1
def calculatePathWinding(hexes: typing.Sequence[typing.Tuple[int, int]]) -> typing.Optional[PathWinding]:
    count = len(hexes)
    total = 0

    for index in range(count):
        x1, y1 = hexes[index]
        x2, y2 = hexes[(index + 1) % count]  # Wrap around to the first vertex
        total += (x2 - x1) * (y2 + y1)

    if total < 0:
        return PathWinding.Clockwise
    elif total > 0:
        return PathWinding.AntiClockwise

    # Hexes are coincident (i.e. the define a "line" of hexes that is one hex
    # "wide" but possibly multiple hexes long)
    return None
