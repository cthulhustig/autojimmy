import enum
import math
import typing

SubsectorWidth = 8 # parsecs
SubsectorHeight = 10 # parsecs
HorzSubsectorsPerSector = 4
VertSubsectorPerSector = 4
SubsectorPerSector = HorzSubsectorsPerSector * VertSubsectorPerSector
SectorWidth = HorzSubsectorsPerSector * SubsectorWidth # parsecs (32)
SectorHeight = VertSubsectorPerSector * SubsectorHeight # parsecs (40)
ReferenceSectorX = 0
ReferenceSectorY = 0
ReferenceHexX = 1
ReferenceHexY = 40
ParsecScaleX = math.cos(math.pi / 6) # = cosine 30° = 0.8660254037844387
ParsecScaleY = 1
HexWidthOffset = math.tan(math.pi / 6) / 4 / ParsecScaleX # = 0.16666666666666666

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

def absoluteSpaceToSectorPos(
        pos: typing.Tuple[int, int]
        ) -> typing.Tuple[int, int]:
    absoluteX = pos[0] + (ReferenceHexX - 1)
    absoluteY = pos[1] + (ReferenceHexY - 1)
    return (absoluteX // SectorWidth, absoluteY // SectorHeight)

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

# NOTE: There is a LOT of code that assumes instances of this
# class are immutable
class SectorIndex(object):
    def __init__(self, sectorX: int, sectorY: int) -> None:
        self._sectorX = int(sectorX)
        self._sectorY = int(sectorY)

        self._worldBounds: typing.Optional[typing.Tuple[float, float, float, float]] = None
        self._hexExtent: typing.Optional[typing.Tuple['HexPosition', 'HexPosition']] = None
        self._hash = None

    def __eq__(self, other):
        if isinstance(other, SectorIndex):
            return self._sectorX == other._sectorX and \
                self._sectorY == other._sectorY
        return super().__eq__(other)

    def __hash__(self) -> int:
        if self._hash is None:
            self._hash = hash((self._sectorX, self._sectorY))
        return self._hash

    def __str__(self) -> str:
        return f'{self._sectorX},{self._sectorY}'

    def sectorX(self) -> int:
        return self._sectorX

    def sectorY(self) -> int:
        return self._sectorY

    def elements(self) -> typing.Tuple[int, int]:
        return (self._sectorX, self._sectorY)

    def worldBounds(self) -> typing.Tuple[float, float, float, float]: # (left, top, width, height)
        if self._worldBounds is None:
            left = (self._sectorX * SectorWidth) - ReferenceHexX
            top = (self._sectorY * SectorHeight) - ReferenceHexY
            width = SectorWidth
            height = SectorHeight

            # Adjust to completely contain all hexes in the sector
            height += 0.5
            left -= HexWidthOffset
            width += HexWidthOffset * 2

            self._worldBounds = (left, top, width, height)
        return self._worldBounds

    def hexExtent(self) -> typing.Tuple['HexPosition', 'HexPosition']: # (top left hex, bottom right hex)
        if self._hexExtent is None:
            topLeft = HexPosition(
                sectorX=self._sectorX,
                sectorY=self._sectorY,
                offsetX=1,
                offsetY=1)
            bottomRight = HexPosition(
                sectorX=self._sectorX,
                sectorY=self._sectorY,
                offsetX=SectorWidth,
                offsetY=SectorHeight)
            self._hexExtent = (topLeft, bottomRight)
        return self._hexExtent

# NOTE: There is a LOT of code that assumes instances of this
# class are immutable
class SubsectorIndex(object):
    @typing.overload
    def __init__(self, sectorX: int, sectorY: int, code: str) -> None: ...
    @typing.overload
    def __init__(self, sectorX: int, sectorY: int, indexX: int, indexY: int) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        argCount = len(args) + len(kwargs)
        if argCount == 3:
            sectorX = int(args[0] if len(args) > 0 else kwargs['sectorX'])
            sectorY = int(args[1] if len(args) > 1 else kwargs['sectorY'])
            code = str(args[2] if len(args) > 2 else kwargs['code'])

            self._sectorX = int(sectorX)
            self._sectorY = int(sectorY)
            self._code = str(code).upper()

            index = ord(self._code) - ord('A')
            if index < 0 or index > 15:
                raise ValueError('Subsector index code must be in range in range A-P')

            self._indexX = index % 4
            self._indexY = index // 4
        elif argCount == 4:
            sectorX = int(args[0] if len(args) > 0 else kwargs['sectorX'])
            sectorY = int(args[1] if len(args) > 1 else kwargs['sectorY'])
            indexX = str(args[2] if len(args) > 2 else kwargs['indexX'])
            indexY = str(args[3] if len(args) > 3 else kwargs['indexY'])

            self._sectorX = int(sectorX)
            self._sectorY = int(sectorY)
            self._indexX = int(indexX)
            self._indexY = int(indexY)

            if self._indexX < 0 or self._indexX > 3:
                raise ValueError('Subsector index x value must be in range in range 0-3')
            if self._indexY < 0 or self._indexY > 3:
                raise ValueError('Subsector index y value must be in range in range 0-3')

            self._code=chr(ord('A') + (self._indexY * 4) + self._indexX)
        else:
            raise ValueError('Invalid sector index arguments')

        self._sectorIndex: typing.Optional[SectorIndex] = None
        self._worldBounds: typing.Optional[typing.Tuple[float, float, float, float]] = None
        self._hexExtent: typing.Optional[typing.Tuple['HexPosition', 'HexPosition']] = None
        self._hash = None

    def __eq__(self, other):
        if isinstance(other, SubsectorIndex):
            return self._sectorX == other._sectorX and \
                self._sectorY == other._sectorY and \
                self._code == other._code
        return super().__eq__(other)

    def __hash__(self) -> int:
        if self._hash is None:
            self._hash = hash((self._sectorX, self._sectorY, self._code))
        return self._hash

    def __str__(self) -> str:
        return f'{self._sectorX},{self._sectorY},{self._code}'

    def sectorX(self) -> int:
        return self._sectorX

    def sectorY(self) -> int:
        return self._sectorY

    def code(self) -> str:
        return self._code

    def indexX(self) -> int:
        return self._indexX

    def indexY(self) -> int:
        return self._indexY

    def elements(self) -> typing.Tuple[int, int, str]:
        return (self._sectorX, self._sectorY, self._code)

    def sectorIndex(self) -> SectorIndex:
        if not self._sectorIndex:
            self._sectorIndex = SectorIndex(sectorX=self._sectorX, sectorY=self._sectorY)
        return self._sectorIndex

    def worldBounds(self) -> typing.Tuple[float, float, float, float]: # (left, top, width, height)
        if self._worldBounds is None:
            left = ((self._sectorX * SectorWidth) - ReferenceHexX) + \
                (self._indexX * SubsectorWidth)
            top = ((self._sectorY * SectorHeight) - ReferenceHexY) + \
                (self._indexY * SubsectorHeight)
            width = SubsectorWidth
            height = SubsectorHeight

            # Adjust to completely contain all hexes in the sector
            height += 0.5
            left -= HexWidthOffset
            width += HexWidthOffset * 2

            self._worldBounds = (left, top, width, height)
        return self._worldBounds

    def hexExtent(self) -> typing.Tuple['HexPosition', 'HexPosition']: # (top left hex, bottom right hex)
        if self._hexExtent is None:
            topLeft = HexPosition(
                sectorX=self._sectorX,
                sectorY=self._sectorY,
                offsetX=(self._indexX * SubsectorWidth) + 1,
                offsetY=(self._indexY * SubsectorHeight) + 1)
            bottomRight = HexPosition(
                sectorX=self._sectorX,
                sectorY=self._sectorY,
                offsetX=topLeft.offsetX() + (SubsectorWidth - 1),
                offsetY=topLeft.offsetY() + (SubsectorHeight - 1))
            self._hexExtent = (topLeft, bottomRight)
        return self._hexExtent

# NOTE: There is a LOT of code that assumes instances of this
# class are immutable
class HexPosition(object):
    @typing.overload
    def __init__(self, absoluteX: int, absoluteY: int) -> None: ...
    @typing.overload
    def __init__(self, sectorX: int, sectorY: int, offsetX: int, offsetY: int) -> None: ...
    @typing.overload
    def __init__(self, sectorIndex, offsetX: int, offsetY: int) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        argCount = len(args) + len(kwargs)
        if argCount == 2:
            absoluteX = int(args[0] if len(args) > 0 else kwargs['absoluteX'])
            absoluteY = int(args[1] if len(args) > 1 else kwargs['absoluteY'])
            self._absolute = (absoluteX, absoluteY)
            self._relative = None
        elif argCount == 3:
            sectorIndex = args[0] if len(args) > 0 else kwargs['sectorIndex']
            offsetX = int(args[1] if len(args) > 1 else kwargs['offsetX'])
            offsetY = int(args[2] if len(args) > 2 else kwargs['offsetY'])
            if not isinstance(sectorIndex, SectorIndex):
                raise ValueError('The sectorIndex argument must be a SectorIndex')
            self._relative = (sectorIndex.sectorX(), sectorIndex.sectorY(), offsetX, offsetY)
            self._absolute = None
        elif argCount == 4:
            sectorX = int(args[0] if len(args) > 0 else kwargs['sectorX'])
            sectorY = int(args[1] if len(args) > 1 else kwargs['sectorY'])
            offsetX = int(args[2] if len(args) > 2 else kwargs['offsetX'])
            offsetY = int(args[3] if len(args) > 3 else kwargs['offsetY'])
            self._relative = (sectorX, sectorY, offsetX, offsetY)
            self._absolute = None
        else:
            raise ValueError('Invalid hex position arguments')

        self._sectorIndex: typing.Optional[SectorIndex] = None
        self._subsectorIndex: typing.Optional[SubsectorIndex] = None
        self._worldCenter: typing.Optional[typing.Tuple[float, float]] = None
        self._isotropicSpace: typing.Optional[typing.Tuple[float, float]] = None
        self._hash = None

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
        if self._hash is None:
            self._hash = hash(self.absolute())
        return self._hash

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

    def sector(self) -> typing.Tuple[int, int]:
        if not self._relative:
            self._calculateRelative()
        return (self._relative[0], self._relative[1])

    def sectorIndex(self) -> SectorIndex:
        if not self._sectorIndex:
            sectorX, sectorY, _, _ = self.relative()
            self._sectorIndex = SectorIndex(
                sectorX=sectorX,
                sectorY=sectorY)
        return self._sectorIndex

    def subsectorIndex(self) -> SubsectorIndex:
        if not self._subsectorIndex:
            sectorX, sectorY, offsetX, offsetY = self.relative()
            self._subsectorIndex = SubsectorIndex(
                sectorX=sectorX,
                sectorY=sectorY,
                indexX=(offsetX - 1) // SubsectorWidth,
                indexY=(offsetY - 1) // SubsectorHeight)
        return self._subsectorIndex

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

    def offset(self) -> typing.Tuple[int, int]:
        if not self._relative:
            self._calculateRelative()
        return (self._relative[2], self._relative[3])

    def relative(self) -> typing.Tuple[int, int, int, int]:
        if not self._relative:
            self._calculateRelative()
        return self._relative

    # This gets the center of the hex in an coordinate space where the x & y
    # axis scale the same, unlike world space where they scale differently (I
    # think the term isotropic is correct). It's my equivalent of Traveller Map
    # 'Map Space'. It's basically identical except I don't invert the y axis.
    def isotropicSpace(self) -> typing.Tuple[float, float]:
        if not self._isotropicSpace:
            worldCenter = self.worldCenter()
            self._isotropicSpace = (
                worldCenter[0] * ParsecScaleX,
                worldCenter[1] * ParsecScaleY)
        return self._isotropicSpace

    # Reimplementation of code from Traveller Map source code.
    # HexDistance in Astrometrics.cs
    def parsecsTo(
            self,
            other: 'HexPosition'
            ) -> int:
        x1, y1 = self.absolute()
        x2, y2 = other.absolute()
        dx = x2 - x1
        dy = y2 - y1

        adx = dx if dx >= 0 else -dx

        ody = dy + (adx // 2)

        if ((x1 & 0b1) == 0) and ((x2 & 0b1) != 0):
            ody += 1

        max = ody if ody > adx else adx
        adx -= ody
        return adx if adx > max else max

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

    # Return the absolute center point of the hex
    def worldCenter(self) -> typing.Tuple[float, float]:
        if not self._worldCenter:
            absX, absY = self.absolute()
            self._worldCenter = (
                absX - 0.5,
                absY - (0.0 if ((absX % 2) != 0) else 0.5))
        return self._worldCenter

    def worldBounds(
            self
            ) -> typing.Tuple[float, float, float, float]: # (left, top, width, height)
        absoluteX, absoluteY = self.absolute()
        return (
            absoluteX - (1 + HexWidthOffset),
            absoluteY - (0.5 if absoluteX % 2 else 1),
            1 + (2 * HexWidthOffset),
            1)

    def _calculateRelative(self) -> None:
        self._relative = absoluteSpaceToRelativeSpace(pos=self._absolute)

    def _calculateAbsolute(self) -> None:
        self._absolute = relativeSpaceToAbsoluteSpace(pos=self._relative)
