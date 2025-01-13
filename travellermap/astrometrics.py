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

# Reimplementation of code from Traveller Map source code.
# CoordinatesToLocation in Astrometrics.cs
def absoluteSpaceToRelativeSpace(
        pos: typing.Tuple[int, int]
        ) -> typing.Tuple[int, int, int, int]:
    absoluteX = pos[0] + (ReferenceHexX - 1)
    absoluteY = pos[1] + (ReferenceHexY - 1)
    sectorX = absoluteX // SectorWidth
    sectorY = absoluteY // SectorHeight
    offsetX = absoluteX - (sectorX * SectorWidth) + 1
    offsetY = absoluteY - (sectorY * SectorHeight) + 1
    return (sectorX, sectorY, offsetX, offsetY)

def absoluteSpaceToMapSpace(
        pos: typing.Tuple[int, int]
        ) -> typing.Tuple[float, float]:
    ix = pos[0] - 0.5
    iy = pos[1] - 0.5 if (pos[0] % 2) == 0 else pos[1]
    x = ix * ParsecScaleX
    y = iy * -ParsecScaleY
    return x, y

def relativeSpaceToMapSpace(
        pos: typing.Tuple[int, int, int, int]
        ) -> typing.Tuple[float, float]:
    return absoluteSpaceToMapSpace(pos=relativeSpaceToAbsoluteSpace(pos=pos))

def mapSpaceToTileSpace(
        pos: typing.Tuple[float, float],
        scale: float
        ) -> typing.Tuple[float, float]:
    scalar = scale / TravellerMapTileSize
    return (pos[0] * scalar, -pos[1] * scalar)

def tileSpaceToMapSpace(
        pos: typing.Tuple[float, float],
        scale: float
        ) -> typing.Tuple[float, float]:
    scalar = scale / TravellerMapTileSize
    return (pos[0] / scalar, -pos[1] / scalar)

# This gets the bounding rect of a sector in absolute coordinates (world coordinates in Traveller
# Map parlance). It's based on Bounds from Traveller Map (Sector.cs) but I've updated it so it
# returns a bounding box that contains the full extent of all hexes in the sector.
def sectorBoundingRect(
        sector: typing.Tuple[int, int],
        ) -> typing.Tuple[int, int, int, int]:
    left = (sector[0] * SectorWidth) - ReferenceHexX
    bottom = (sector[1] * SectorHeight) - ReferenceHexY
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
        sector: typing.Tuple[int, int],
        ) -> typing.Tuple[int, int, int, int]:
    left = (sector[0] * SectorWidth) - ReferenceHexX
    bottom = (sector[1] * SectorHeight) - ReferenceHexY
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
        absolute1: typing.Tuple[int, int],
        absolute2: typing.Tuple[int, int]
        ) -> int:
    dx = absolute2[0] - absolute1[0]
    dy = absolute2[1] - absolute1[1]

    adx = dx if dx >= 0 else -dx

    ody = dy + (adx // 2)

    if ((absolute1[0] & 0b1) == 0) and ((absolute2[0] & 0b1) != 0):
        ody += 1

    max = ody if ody > adx else adx
    adx -= ody
    return adx if adx > max else max

# These are orientated visually as seen in Traveller Map
class HexEdge(enum.Enum):
    Upper = 0
    UpperRight = 1
    LowerRight = 2
    Lower = 3
    LowerLeft = 4
    UpperLeft = 5


_OppositeEdgeTransitions = {
    HexEdge.Upper: HexEdge.Lower,
    HexEdge.UpperRight: HexEdge.LowerLeft,
    HexEdge.LowerRight: HexEdge.UpperLeft,
    HexEdge.Lower: HexEdge.Upper,
    HexEdge.LowerLeft: HexEdge.UpperRight,
    HexEdge.UpperLeft: HexEdge.LowerRight
}

_ClockwiseEdgeTransitions = {
    HexEdge.Upper: HexEdge.UpperLeft,
    HexEdge.UpperRight: HexEdge.Upper,
    HexEdge.LowerRight: HexEdge.UpperRight,
    HexEdge.Lower: HexEdge.LowerRight,
    HexEdge.LowerLeft: HexEdge.Lower,
    HexEdge.UpperLeft: HexEdge.LowerLeft
}

_AnticlockwiseEdgeTransitions = {
    HexEdge.Upper: HexEdge.UpperRight,
    HexEdge.UpperRight: HexEdge.LowerRight,
    HexEdge.LowerRight: HexEdge.Lower,
    HexEdge.Lower: HexEdge.LowerLeft,
    HexEdge.LowerLeft: HexEdge.UpperLeft,
    HexEdge.UpperLeft: HexEdge.Upper
}

def oppositeHexEdge(edge: HexEdge) -> HexEdge:
    return _OppositeEdgeTransitions[edge]

def clockwiseHexEdge(edge: HexEdge) -> HexEdge:
    return _ClockwiseEdgeTransitions[edge]

def anticlockwiseHexEdge(edge: HexEdge) -> HexEdge:
    return _AnticlockwiseEdgeTransitions[edge]

def neighbourAbsoluteHex(
        origin: typing.Tuple[int, int],
        edge: HexEdge
        ) -> typing.Tuple[int, int]:
    hexX = origin[0]
    hexY = origin[1]
    if edge == HexEdge.Upper:
        hexY -= 1
    elif edge == HexEdge.UpperRight:
        hexY += 0 if (hexX % 2) else -1
        hexX += 1
    elif edge == HexEdge.LowerRight:
        hexY += 1 if (hexX % 2) else 0
        hexX += 1
    elif edge == HexEdge.Lower:
        hexY += 1
    elif edge == HexEdge.LowerLeft:
        hexY += 1 if (hexX % 2) else 0
        hexX -= 1
    elif edge == HexEdge.UpperLeft:
        hexY += 0 if (hexX % 2) else -1
        hexX -= 1
    else:
        raise ValueError('Invalid hex edge')
    return (hexX, hexY)

def neighbourRelativeHex(
        origin: typing.Tuple[int, int, int, int],
        edge: HexEdge
        ) -> typing.Tuple[int, int, int, int]:
    sectorX = origin[0]
    sectorY = origin[1]
    hexX = origin[2]
    hexY = origin[3]

    if edge == HexEdge.Upper:
        hexY -= 1
    elif edge == HexEdge.UpperRight:
        hexY += -1 if (hexX % 2) else 0
        hexX += 1
    elif edge == HexEdge.LowerRight:
        hexY += 0 if (hexX % 2) else 1
        hexX += 1
    elif edge == HexEdge.Lower:
        hexY += 1
    elif edge == HexEdge.LowerLeft:
        hexY += 0 if (hexX % 2) else 1
        hexX -= 1
    elif edge == HexEdge.UpperLeft:
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

def yieldAbsoluteRadiusHexes(
        center: typing.Tuple[int, int],
        radius: int,
        includeInterior: bool = True
        ) -> typing.Generator[typing.Tuple[int, int], None, None]:
    if radius == 0:
        yield center
        return

    if includeInterior:
        minLength = radius + 1
        maxLength = (radius * 2) + 1
        deltaLength = int(math.floor((maxLength - minLength) / 2))

        centerX = center[0]
        centerY = center[1]
        startX = centerX - radius
        finishX = centerX + radius
        startY = (centerY - radius) + deltaLength
        finishY = (centerY + radius) - deltaLength
        if (startX & 0b1) != 0:
            startY += 1
            if (radius & 0b1) != 0:
                finishY -= 1
        else:
            if (radius & 0b1) != 0:
                startY += 1
            finishY -= 1

        for x in range(startX, finishX + 1):
            if (x & 0b1) != 0:
                if x <= centerX:
                    startY -= 1
                else:
                    finishY -= 1
            else:
                if x <= centerX:
                    finishY += 1
                else:
                    startY += 1

            for y in range(startY, finishY + 1):
                yield (x, y)
    else:
        current = (center[0], center[1] + radius)

        for _ in range(radius):
            current = neighbourAbsoluteHex(current, HexEdge.UpperRight)
            yield current

        for _ in range(radius):
            current = neighbourAbsoluteHex(current, HexEdge.Upper)
            yield current

        for _ in range(radius):
            current = neighbourAbsoluteHex(current, HexEdge.UpperLeft)
            yield current

        for _ in range(radius):
            current = neighbourAbsoluteHex(current, HexEdge.LowerLeft)
            yield current

        for _ in range(radius):
            current = neighbourAbsoluteHex(current, HexEdge.Lower)
            yield current

        for _ in range(radius):
            current = neighbourAbsoluteHex(current, HexEdge.LowerRight)
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
            self._absolute = (int(absoluteX), int(absoluteY))
            self._relative = None
        else:
            self._relative = (int(sectorX), int(sectorY), int(offsetX), int(offsetY))
            self._absolute = None

    def __eq__(self, other):
        if isinstance(other, HexPosition):
            # Only need to compare absolute position
            return self.absolute() == other.absolute()
        return super().__eq__(other)

    def __lt__(self, other: 'HexPosition') -> bool:
        if isinstance(other, HexPosition):
            thisX, thisY = self.absolute()
            otherX, otherY = other.absolute()
            if thisY < otherY:
                return True
            elif thisY > otherY:
                return False
            return thisX < otherX
        return super().__lt__(other)

    def __hash__(self) -> int:
        return hash(self.absolute())

    def __str__(self) -> str:
        absoluteX, absoluteY = self.absolute()
        return f'{absoluteX},{absoluteY}'

    def absoluteX(self) -> int:
        if not self._absolute:
            self._calculateAbsolute()
        return self._absolute[0]

    def absoluteY(self) -> int:
        if not self._absolute:
            self._calculateAbsolute()
        return self._absolute[1]

    def absolute(self) -> typing.Tuple[int, int]:
        if not self._absolute:
            self._calculateAbsolute()
        return self._absolute

    def sectorX(self) -> int:
        if not self._relative:
            self._calculateRelative()
        return self._relative[0]

    def sectorY(self) -> int:
        if not self._relative:
            self._calculateRelative()
        return self._relative[1]

    def offsetX(self) -> int:
        if not self._relative:
            self._calculateRelative()
        return self._relative[2]

    def offsetY(self) -> int:
        if not self._relative:
            self._calculateRelative()
        return self._relative[3]

    def relative(self) -> typing.Tuple[int, int, int, int]:
        if not self._relative:
            self._calculateRelative()
        return self._relative

    def mapSpace(self) -> typing.Tuple[float, float]:
        if not self._absolute:
            self._calculateAbsolute()
        return absoluteSpaceToMapSpace(pos=self._absolute)

    def parsecsTo(
            self,
            other: 'HexPosition'
            ) -> int:
        return hexDistance(
            absolute1=self.absolute(),
            absolute2=other.absolute())

    def neighbourHex(
            self,
            edge: HexEdge
            ) -> 'HexPosition':
        if self._absolute:
            absoluteX, absoluteY = neighbourAbsoluteHex(
                origin=self._absolute,
                edge=edge)
            return HexPosition(absoluteX=absoluteX, absoluteY=absoluteY)
        else:
            sectorX, sectorY, offsetX, offsetY = neighbourRelativeHex(
                origin=self._relative,
                edge=edge)
            return HexPosition(
                sectorX=sectorX,
                sectorY=sectorY,
                offsetX=offsetX,
                offsetY=offsetY)

    def yieldRadiusHexes(
            self,
            radius: int,
            includeInterior: bool = True
            ) -> typing.Generator['HexPosition', None, None]:
        if not self._absolute:
            self._calculateAbsolute()

        generator = yieldAbsoluteRadiusHexes(
            center=self._absolute,
            radius=radius,
            includeInterior=includeInterior)
        for absoluteX, absoluteY in generator:
            yield HexPosition(absoluteX=absoluteX, absoluteY=absoluteY)

    def _calculateRelative(self) -> None:
        self._relative = absoluteSpaceToRelativeSpace(pos=self._absolute)

    def _calculateAbsolute(self) -> None:
        self._absolute = relativeSpaceToAbsoluteSpace(pos=self._relative)
