import enum
import typing

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

        # Shoelace formula edge step
        total += (x2 - x1) * (y2 + y1)

    if total > 0:
        return PathWinding.Clockwise
    elif total < 0:
        return PathWinding.AntiClockwise

    return None # hexes are coincident
