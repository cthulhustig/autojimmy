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

def calculateTriangleWinding(
        a: tuple[int, int],
        b: tuple[int, int],
        c: tuple[int, int]
        ) -> typing.Optional[PathWinding]:
    cross = ((b[0] - a[0]) * (c[1] - a[1])
           - (b[1] - a[1]) * (c[0] - a[0]))

    if cross > 0:
        return PathWinding.Clockwise
    elif cross < 0:
        return PathWinding.AntiClockwise

    return None

# These are orientated visually as seen in Traveller Map
class HexEdge(enum.Enum):
    Top = 0
    TopRight = 1
    BottomRight = 2
    Bottom = 3
    BottomLeft = 4
    TopLeft = 5

_OppositeHexEdgeTransitions = {
    HexEdge.Top: HexEdge.Bottom,
    HexEdge.TopRight: HexEdge.BottomLeft,
    HexEdge.BottomRight: HexEdge.TopLeft,
    HexEdge.Bottom: HexEdge.Top,
    HexEdge.BottomLeft: HexEdge.TopRight,
    HexEdge.TopLeft: HexEdge.BottomRight
}

_AnticlockwiseHexEdgeTransitions = {
    HexEdge.Top: HexEdge.TopLeft,
    HexEdge.TopRight: HexEdge.Top,
    HexEdge.BottomRight: HexEdge.TopRight,
    HexEdge.Bottom: HexEdge.BottomRight,
    HexEdge.BottomLeft: HexEdge.Bottom,
    HexEdge.TopLeft: HexEdge.BottomLeft
}

_ClockwiseHexEdgeTransitions = {
    HexEdge.Top: HexEdge.TopRight,
    HexEdge.TopRight: HexEdge.BottomRight,
    HexEdge.BottomRight: HexEdge.Bottom,
    HexEdge.Bottom: HexEdge.BottomLeft,
    HexEdge.BottomLeft: HexEdge.TopLeft,
    HexEdge.TopLeft: HexEdge.Top
}

def oppositeHexEdge(edge: HexEdge) -> HexEdge:
    return _OppositeHexEdgeTransitions[edge]

def clockwiseHexEdge(edge: HexEdge) -> HexEdge:
    return _ClockwiseHexEdgeTransitions[edge]

def anticlockwiseHexEdge(edge: HexEdge) -> HexEdge:
    return _AnticlockwiseHexEdgeTransitions[edge]

def absoluteNeighbourHex(hex: typing.Tuple[int, int], edge: HexEdge) -> typing.Tuple[int, int]:
    hexX, hexY = hex

    if edge == HexEdge.Top:
        hexY -= 1
    elif edge == HexEdge.TopRight:
        hexY += 0 if (hexX % 2) else -1
        hexX += 1
    elif edge == HexEdge.BottomRight:
        hexY += 1 if (hexX % 2) else 0
        hexX += 1
    elif edge == HexEdge.Bottom:
        hexY += 1
    elif edge == HexEdge.BottomLeft:
        hexY += 1 if (hexX % 2) else 0
        hexX -= 1
    elif edge == HexEdge.TopLeft:
        hexY += 0 if (hexX % 2) else -1
        hexX -= 1
    else:
        # TODO: Not sure what is best to do here
        return hex

    return (hexX, hexY)

def connectingEdge(
        pt1: typing.Tuple[int, int],
        pt2: typing.Tuple[int, int]
        ) -> typing.Optional[HexEdge]:
        x1, y1 = pt1
        x2, y2 = pt2
        deltaX = x2 - x1
        deltaY = y2 - y1

        if deltaX == 0:
            if deltaY == -1:
                return HexEdge.Top
            elif deltaY == 1:
                return HexEdge.Bottom

        elif deltaX == 1:
            if deltaY == (0 if x1 % 2 else -1):
                return HexEdge.TopRight
            elif deltaY == (1 if x1 % 2 else 0):
                return HexEdge.BottomRight

        elif deltaX == -1:
            if deltaY == (0 if x1 % 2 else -1):
                return HexEdge.TopLeft
            elif deltaY == (1 if x1 % 2 else 0):
                return HexEdge.BottomLeft

        return None