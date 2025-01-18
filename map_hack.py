from PyQt5 import QtWidgets, QtCore, QtGui
import PIL.Image, PIL.ImageDraw, PIL.ImageFont
import os
import gui
import io
import common
import typing
import enum
import math
import numpy
import travellermap

class StringAlignment(enum.Enum):
    Baseline = 0
    Centered = 1
    TopLeft = 2
    TopCenter = 3
    TopRight = 4
    CenterLeft = 5

class DashStyle(enum.Enum):
    Solid = 0
    Dot = 1
    Dash = 2
    DashDot = 3
    DashDotDot = 4
    Custom = 5

class FontStyle(enum.IntEnum):
    Regular = 0x0
    Bold = 0x1
    Italic = 0x2
    Underline = 0x4
    Strikeout = 0x8

class LineStyle(enum.Enum):
    Solid = 0 # Default
    Dashed = 1
    Dotted = 2
    NoStyle = 3 # TODO: Was non in traveller map code

class GraphicsUnit(enum.Enum):
    # Specifies the world coordinate system unit as the unit of measure.
    World = 0
    # Specifies the unit of measure of the display device. Typically pixels for video
    # displays, and 1/100 inch for printers.
    Display = 1
    # Specifies a device pixel as the unit of measure.
    Pixel = 2
    # Specifies a printer's point (1/72 inch) as the unit of measure.
    Point = 3
    # Specifies the inch as the unit of measure.
    Inch = 4
    # Specifies the document unit (1/300 inch) as the unit of measure.
    Document = 5
    # Specifies the millimeter as the unit of measure.
    Millimeter = 6

class HexStyle(enum.Enum):
    NoHex = 0 # TODO: Was None in traveller map code
    Hex = 1
    Square = 2

class MicroBorderStyle(enum.Enum):
    Hex = 0
    Square = 1
    Curve = 2

class HexCoordinateStyle(enum.Enum):
    Sector = 0
    Subsector = 1

class MapOptions(enum.IntEnum):
    SectorGrid = 0x0001,
    SubsectorGrid = 0x0002,

    SectorsSelected = 0x0004,
    SectorsAll = 0x0008,
    #SectorsMask = SectorsSelected | SectorsAll,

    BordersMajor = 0x0010,
    BordersMinor = 0x0020,
    #BordersMask = BordersMajor | BordersMinor,

    NamesMajor = 0x0040,
    NamesMinor = 0x0080,
    #NamesMask = NamesMajor | NamesMinor,

    WorldsCapitals = 0x0100,
    WorldsHomeworlds = 0x0200,
    #WorldsMask = WorldsCapitals | WorldsHomeworlds,

    RoutesSelectedDeprecated = 0x0400,

    PrintStyleDeprecated = 0x0800,
    CandyStyleDeprecated = 0x1000,
    #StyleMaskDeprecated = PrintStyleDeprecated | CandyStyleDeprecated,

    ForceHexes = 0x2000,
    WorldColors = 0x4000,
    FilledBorders = 0x8000

class LayerId(enum.Enum):
        #------------------------------------------------------------
        # Background
        #------------------------------------------------------------

        Background_Solid = 0
        Background_NebulaTexture = 1
        Background_Galaxy = 2

        Background_PseudoRandomStars = 3
        Background_Rifts = 4

        #------------------------------------------------------------
        #Foreground
        #------------------------------------------------------------

        Macro_Borders = 5
        Macro_Routes = 6

        Grid_Sector = 7
        Grid_Subsector = 8
        Grid_Parsec = 9

        Names_Subsector = 10

        Micro_BordersFill = 11
        Micro_BordersShade = 12
        Micro_BordersStroke = 13
        Micro_Routes = 14
        Micro_BorderExplicitLabels = 15

        Names_Sector = 16

        Macro_GovernmentRiftRouteNames = 17
        Macro_CapitalsAndHomeWorlds = 18
        Mega_GalaxyScaleLabels = 19

        Worlds_Background = 20
        Worlds_Foreground = 21
        Worlds_Overlays = 22

        #------------------------------------------------------------
        # Overlays
        #------------------------------------------------------------

        Overlay_DroyneChirperWorlds = 23
        Overlay_MinorHomeworlds = 24
        Overlay_AncientsWorlds = 25
        Overlay_ReviewStatus = 26

class WorldDetails(enum.IntEnum):
    NoDetails = 0 # TODO: Was None in traveller map code

    Type = 1 << 0, # Show world type (water/no water/asteroid/unknown)
    KeyNames = 1 << 1, # Show HiPop/Capital names
    Starport = 1 << 2, # Show starport
    GasGiant = 1 << 3, # Show gas giant glyph
    Allegiance = 1 << 4, # Show allegiance code
    Bases = 1 << 5, # Show bases
    Hex = 1 << 6, # Include hex numbers
    Zone = 1 << 7, # Show Amber/Red zones
    AllNames = 1 << 8, # Show all world names, not just HiPop/Capitals
    Uwp = 1 << 9, # Show UWP below world name
    Asteroids = 1 << 10, # Render asteroids as pseudorandom ovals
    Highlight = 1 << 11, # Highlight (text font, text color) HiPopCapital worlds

    #Dotmap = None,
    #Atlas = Type | KeyNames | Starport | GasGiant | Allegiance | Bases | Zone | Highlight,
    #Poster = Atlas | Hex | AllNames | Asteroids,

class Size(object):
    @typing.overload
    def __init__(self, other: 'Size') -> None: ...
    @typing.overload
    def __init__(self, width: int, height: int) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        if len(args) + len(kwargs) == 1:
            other = args[0] if len(args) > 0 else kwargs['other']
            if not isinstance(other, Size):
                raise TypeError('The other parameter must be a Size')
            self._width = other.width
            self._height = other.height
        else:
            self._width = int(args[0] if len(args) > 0 else kwargs['width'])
            self._height = int(args[1] if len(args) > 1 else kwargs['height'])

    @property
    def width(self) -> int:
        return self._width
    @width.setter
    def width(self, width: int) -> None:
        self._width = int(width)

    @property
    def height(self) -> int:
        return self._height
    @height.setter
    def height(self, height: int) -> None:
        self._height = int(height)

    def __eq__(self, other: typing.Any) -> bool:
        if isinstance(other, Size):
            return self.width == other.width and self.height == other.height
        return super().__eq__(other)

class SizeF(object):
    @typing.overload
    def __init__(self, other: 'SizeF') -> None: ...
    @typing.overload
    def __init__(self, width: float, height: float) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        if len(args) + len(kwargs) == 1:
            other = args[0] if len(args) > 0 else kwargs['other']
            if not isinstance(other, SizeF):
                raise TypeError('The other parameter must be a SizeF')
            self.width = other.width
            self.height = other.height
        else:
            self.width = args[0] if len(args) > 0 else kwargs['width']
            self.height = args[1] if len(args) > 1 else kwargs['height']

    def __eq__(self, other: typing.Any) -> bool:
        if isinstance(other, SizeF):
            return self.width == other.width and self.height == other.height
        return super().__eq__(other)

class Point(object):
    @typing.overload
    def __init__(self, other: 'PointF') -> None: ...
    @typing.overload
    def __init__(self, x: int, y: int) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        if len(args) + len(kwargs) == 1:
            other = args[0] if len(args) > 0 else kwargs['other']
            if not isinstance(other, Point):
                raise TypeError('The other parameter must be a Point')
            self.x = other.x
            self.y = other.y
        else:
            self.x = int(args[0] if len(args) > 0 else kwargs['x'])
            self.y = int(args[1] if len(args) > 1 else kwargs['y'])

    def __init__(self, x: int, y: int):
        self._x = int(x)
        self._y = int(y)

    @property
    def x(self) -> int:
        return self._x
    @x.setter
    def x(self, x: int) -> None:
        self._x = int(x)

    @property
    def y(self) -> int:
        return self._y
    @y.setter
    def y(self, y: int) -> None:
        self._y = int(y)

    def __eq__(self, other: typing.Any) -> bool:
        if isinstance(other, Point):
            return self.x == other.x and self.y == other.y
        return super().__eq__(other)

class PointF(object):
    @typing.overload
    def __init__(self, other: 'PointF') -> None: ...
    @typing.overload
    def __init__(self, x: float, y: float) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        if len(args) + len(kwargs) == 1:
            other = args[0] if len(args) > 0 else kwargs['other']
            if not isinstance(other, PointF):
                raise TypeError('The other parameter must be a PointF')
            self.x = other.x
            self.y = other.y
        else:
            self.x = args[0] if len(args) > 0 else kwargs['x']
            self.y = args[1] if len(args) > 1 else kwargs['y']

    def __eq__(self, other: typing.Any) -> bool:
        if isinstance(other, PointF):
            return self.x == other.x and self.y == other.y
        return super().__eq__(other)

class RectangleF(object):
    @typing.overload
    def __init__(self, other: 'RectangleF') -> None: ...
    @typing.overload
    def __init__(self, x: float, y: float, width: float, height: float) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        if len(args) + len(kwargs) == 1:
            other = args[0] if len(args) > 0 else kwargs['other']
            if not isinstance(other, RectangleF):
                raise TypeError('The other parameter must be a RectangleF')
            self.x = other.x
            self.y = other.y
            self.width = other.width
            self.height = other.height
        else:
            self.x = args[0] if len(args) > 0 else kwargs['x']
            self.y = args[1] if len(args) > 1 else kwargs['y']
            self.width = args[3] if len(args) > 3 else kwargs['width']
            self.height = args[2] if len(args) > 2 else kwargs['height']

    @property
    def left(self) -> float:
        return self.x

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def top(self) -> float:
        return self.y

    @property
    def bottom(self) -> float:
        return self.y + self.height

    def inflate(self, x: float, y: float) -> None:
        self.x -= x
        self.y -= y
        self.width += x * 2
        self.height += y * 2

    def __eq__(self, other: typing.Any) -> bool:
        if isinstance(other, RectangleF):
            return self.x == other.x and self.y == other.y and\
                self.height == other.height and self.width == other.width
        return super().__eq__(other)

class FontInfo():
    def __init__(self, families: str, size: float, style: FontStyle = FontStyle.Regular):
        self.families = families
        self.size = size
        self.style = style

    def makeFont(self) -> 'AbstractFont':
        if not self.families:
            raise RuntimeError("FontInfo has null name")
        return AbstractFont(self.families, self.size * 1.4, self.style, GraphicsUnit.World)

class HighlightWorldPattern(object):
    class Field(enum.Enum):
        Starport = 0
        Size = 1
        Atmosphere = 2
        Hydrosphere = 3
        Population = 4
        Government = 5
        Law = 6
        Tech = 7
        Importance = 8
        Bases = 9

    def __init__(
            self,
            field: 'HighlightWorldPattern.Field' = Field.Starport,
            min: typing.Optional[int] = None,
            max: typing.Optional[int] = None,
            matches: typing.Optional[typing.Collection[str]] = None
            ):
        self.field = field
        self.min = min
        self.max = max
        self.matches = list(matches)

class AbstractPen(object):
    def __init__(self, color: str, width: float = 1):
        self.color = color
        self.width = width
        self.dashStyle = DashStyle.Solid
        self.customDashPattern: typing.Optional[typing.List[float]] = None

class AbstractBrush(object):
    def __init__(self, color: str):
        self.color = color

# TODO: Using Qt fonts here is a temp hack. Tge traveller map version of
# AbstractFont implementation uses a system drawing font class. I want to
# differ from this approach by having a completely abstract font interface
# so using this code doesn't require some specific library for rendering
# library for the font implementation
# TODO: Need to do something with GraphicsUnit
class AbstractFont(object):
    def __init__(self, families: str, emSize: float, style: FontStyle, units: GraphicsUnit):
        self.families = families
        self.emSize = emSize
        self.style = style
        self.units = units

        self.font = None
        for family in self.families.split(','):
            try:
                self.font = QtGui.QFont(family)
                if self.font:
                    #self.font.setPointSizeF(emSize)
                    self.font.setPointSizeF(20)
                    if style & FontStyle.Bold:
                        self.font.setBold(True)
                    if style & FontStyle.Italic:
                        self.font.setBold(True)
                    if style & FontStyle.Underline:
                        self.font.setUnderline(True)
                    if style & FontStyle.Strikeout:
                        self.font.setStrikeOut(True)
                    break
            except:
                self.font = None

        if not self.font:
            raise RuntimeError("No matching font family")

class AbstractMatrix(object):
    _IdentityMatrix = numpy.identity(3)

    @typing.overload
    def __init__(self) -> None: ...
    @typing.overload
    def __init__(self, other: typing.Union['AbstractMatrix', numpy.ndarray]) -> None: ...
    @typing.overload
    def __init__(self, m11: float, m12: float, m21: float, m22: float, dx: float, dy: float) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        if not args and not kwargs:
            self._matrix = AbstractMatrix._IdentityMatrix.copy()
        elif len(args) + len(kwargs) == 1:
            other = args[0] if len(args) > 0 else kwargs['other']
            if isinstance(other, AbstractMatrix):
                self._matrix = other.numpyMatrix().copy()
            elif isinstance(other, numpy.ndarray):
                self._matrix = other.copy()
            else:
                raise TypeError('The other parameter must be an AbstractMatrix or ndarray')
        else:
            m11 = args[0] if len(args) > 0 else kwargs['m11']
            m12 = args[1] if len(args) > 1 else kwargs['m12']
            m21 = args[2] if len(args) > 2 else kwargs['m21']
            m22 = args[3] if len(args) > 3 else kwargs['m22']
            dx = args[4] if len(args) > 4 else kwargs['dx']
            dy = args[5] if len(args) > 5 else kwargs['dy']

            self._matrix = AbstractMatrix._createNumpyMatrix(m11=m11, m12=m12, m21=m21, m22=m22, dx=dx, dy=dy)

    @property
    def m11(self) -> float:
        return self._matrix[0][0]
    @m11.setter
    def m11(self, val: float) -> None:
        self._matrix[0][0] = val

    @property
    def m12(self) -> float:
        return self._matrix[0][1]
    @m12.setter
    def m12(self, val: float) -> None:
        self._matrix[0][1] = val

    @property
    def m21(self) -> float:
        return self._matrix[1][0]
    @m21.setter
    def m21(self, val: float) -> None:
        self._matrix[1][0] = val

    @property
    def m22(self) -> float:
        return self._matrix[1][1]
    @m22.setter
    def m22(self, val: float) -> None:
        self._matrix[1][1] = val

    @property
    def offsetX(self) -> float:
        return self._matrix[0][2]
    @offsetX.setter
    def offsetX(self, val: float) -> None:
        self._matrix[0][2] = val

    @property
    def offsetY(self) -> float:
        return self._matrix[1][2]
    @offsetY.setter
    def offsetY(self, val: float) -> None:
        self._matrix[1][2] = val

    def isIdentity(self) -> bool:
        return self._matrix == AbstractMatrix._IdentityMatrix

    def invert(self) -> None:
        self._matrix = numpy.linalg.inv(self._matrix)

    def rotatePrepend(self, degrees: float, center: PointF) -> None:
        degrees %= 360
        radians = math.radians(degrees)
        sinAngle = math.sin(radians)
        cosAngle = math.cos(radians)

        rotationMatrix = AbstractMatrix._createNumpyMatrix(
            m11=cosAngle,
            m12=sinAngle,
            m21=-sinAngle,
            m22=cosAngle,
            dx=center.x * (1 - cosAngle) + center.y * sinAngle,
            dy=center.y * (1 - cosAngle) + center.x * sinAngle)

        self._matrix = self._matrix.dot(rotationMatrix)

    def scalePrepend(self, sx: float, sy: float) -> None:
        scalingMatrix = AbstractMatrix._createNumpyMatrix(
            m11=sx,
            m12=0,
            m21=0,
            m22=sy,
            dx=0,
            dy=0)

        self._matrix = self._matrix.dot(scalingMatrix)

    def translatePrepend(self, dx: float, dy: float) -> None:
        translationMatrix = AbstractMatrix._createNumpyMatrix(
            m11=1,
            m12=0,
            m21=0,
            m22=1,
            dx=dx,
            dy=dy)

        self._matrix = self._matrix.dot(translationMatrix)

    def prepend(self, matrix: 'AbstractMatrix') -> None:
        self._matrix = self._matrix.dot(matrix.numpyMatrix())

    def numpyMatrix(self) -> numpy.matrix:
        return self._matrix

    def transform(self, point: typing.Union[Point, PointF]) -> PointF:
        result = self._matrix.dot([point.x, point.y, 1])
        x = result[0]
        y = result[1]
        w = result[2]
        if w != 0:
            x /= w
            y /= w
        return PointF(x, y)

    def __eq__(self, other: typing.Any) -> bool:
        if isinstance(other, AbstractMatrix):
            return self._matrix == other.numpyMatrix()
        return False

    @staticmethod
    def _createNumpyMatrix(
            m11: float,
            m12: float,
            m21: float,
            m22: float,
            dx: float,
            dy: float
            ) -> numpy.ndarray:
        return numpy.array([[m11, m12, dx], [m21, m22, dy], [0, 0, 1]])

class AbstractPath(object):
    class PointFlag(enum.IntFlag):
        # The starting point
        Start = 0
        # A line segment.
        Line = 1
        # A default Bézier curve.
        Bezier = 3
        # A mask point.
        PathTypeMask = 7
        # The corresponding segment is dashed.
        DashMode = 0x10,
        # A path marker.
        PathMarker = 0x20,
        # The endpoint of a subpath.
        CloseSubpath = 0x80,
        # A cubic Bézier curve.
        Bezier3 = 3

    def __init__(
            self,
            points: typing.Iterable[PointF],
            flags: typing.Iterable[PointFlag]
            ):
        pass

class AbstractImage(object):
    def __init__(self, path: str, url: str):
        pass

class AbstractGraphicsState():
    def __init__(self, graphics: 'AbstractGraphics'):
        self._graphics = graphics

    def __enter__(self):
        pass

    def __exit__(self, type, value, traceback):
        self._graphics.restore()

class AbstractGraphics(object):
    class SmoothingMode(enum.Enum):
        # Specifies an invalid mode.
        Invalid = -1
        # Specifies no antialiasing.
        Default = 0
        # Specifies no antialiasing.
        HighSpeed = 1
        # Specifies antialiased rendering.
        HighQuality = 2
        # Specifies no antialiasing.
        NoAntiAlias = 3 # Was None in traveller map code
        # Specifies antialiased rendering.
        AntiAlias = 4

    def __init__(self):
        self._smoothingMode = AbstractGraphics.SmoothingMode.Default

    # TODO: Need to do something with smoothing mode????
    def smoothingMode(self) -> SmoothingMode:
        return self._smoothingMode

    def setSmoothingMode(self, mode: SmoothingMode) -> None:
        self._smoothingMode = mode

    def supportsWingdings(self) -> bool:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement supportsWingdings')

    # TODO: This was an overloaded version of scaleTransform in the traveller map code
    def scaleTransformUniform(self, scaleXY: float) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement scaleTransformUniform')
    def scaleTransform(self, scaleX: float, scaleY: float) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement scaleTransform')
    def translateTransform(self, dx: float, dy: float) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement translateTransform')
    def rotateTransform(self, angle: float) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement rotateTransform')
    def multiplyTransform(self, matrix: AbstractMatrix) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement multiplyTransform')

    # TODO: This was an overload of intersectClip in traveller map code
    def intersectClipPath(self, path: AbstractPath) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement IntersectClip')
    # TODO: This was an overload of intersectClip in traveller map code
    def intersectClipRect(self, rect: RectangleF) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement IntersectClip')

    # TODO: There was also an overload that takes 4 individual floats in the traveller map code
    def drawLine(self, pen: AbstractPen, pt1: PointF, pt2: PointF) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawLine')
    def drawLines(self, pen: AbstractPen, points: typing.Sequence[PointF]):
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawLines')
    # TODO: This was an overload of drawPath in the traveller map code
    def drawPathOutline(self, pen: AbstractPen, path: AbstractPath):
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawPathOutline')
    # TODO: This was an overload of drawPath in the traveller map code
    def drawPathFill(self, brush: AbstractBrush, path: AbstractPath):
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawPathFill')
    def drawCurve(self, pen: AbstractPen, points: typing.Sequence[PointF], tension: float = 0.5):
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawCurve')
    # TODO: This was an overload of drawClosedCurve in the traveller map code
    def drawClosedCurveOutline(self, pen: AbstractPen, points: typing.Sequence[PointF], tension: float = 0.5):
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawClosedCurveOutline')
    def drawClosedCurveFill(self, brush: AbstractBrush, points: typing.Sequence[PointF], tension: float = 0.5):
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawClosedCurveFill')
    # TODO: There was also an overload that takes 4 individual floats in the traveller map code
    def drawRectangleOutline(self, pen: AbstractPen, rect: RectangleF) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawRectangleOutline')
    # TODO: There was also an overload that takes 4 individual floats in the traveller map code
    def drawRectangleFill(self, brush: AbstractBrush, rect: RectangleF) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawRectangleFill')
    # TODO: This has changed quite a bit from the traveller map interface
    def drawEllipse(self, pen: typing.Optional[AbstractPen], brush: typing.Optional[AbstractBrush], rect: RectangleF):
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawEllipse')
    def drawArc(self, pen: AbstractPen, rect: RectangleF, startAngle: float, sweepAngle: float) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawArc')

    def drawImage(self, image: AbstractImage, rect: RectangleF) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawImage')
    def drawImageAlpha(self, alpha: float, image: AbstractImage, rect: RectangleF) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawImageAlpha')

    def measureString(self, text: str, font: AbstractFont) -> SizeF:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement measureString')
    def drawString(self, text: str, font: AbstractFont, brush: AbstractBrush, x: float, y: float, format: StringAlignment) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawString')

    def save(self) -> AbstractGraphicsState:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement save')
    def restore(self) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement restore')

class StyleSheet(object):
    _DefaultFont = "Arial"

    class StyleElement(object):
        def __init__(self):
            self.visible = False
            self.fillColor = '#000000'
            self.content = ''
            self.pen = AbstractPen('#000000')
            self.textColor = '#000000'
            self.textHighlightColor = '#000000'

            # TODO: Still to fill out
            self.textStyle = None
            self.textBackgroundStyle = None
            self.fontInfo = None
            self.smallFontInfo = None
            self.mediumFontInfo = None
            self.largeFontInfo = None
            self.position = PointF(0, 0)

            self._font = None
            self._smallFont = None
            self._mediumFont = None
            self._largeFont = None

        @property
        def font(self) -> AbstractFont:
            if not self._font:
                if not self.fontInfo:
                    raise RuntimeError('AbstractFont has no fontInfo')
                self._font = self.fontInfo.makeFont()
            return self._font
        @property
        def smallFont(self) -> AbstractFont:
            if not self._smallFont:
                if not self.smallFontInfo:
                    raise RuntimeError('AbstractFont has no font smallFontInfo')
                self._smallFont = self.smallFontInfo.makeFont()
            return self._smallFont
        @property
        def mediumFont(self) -> AbstractFont:
            if not self._mediumFont:
                if not self.mediumFontInfo:
                    raise RuntimeError('AbstractFont has no font mediumFontInfo')
                self._mediumFont = self.mediumFontInfo.makeFont()
            return self._mediumFont
        @property
        def largeFont(self) -> AbstractFont:
            if not self._largeFont:
                if not self.largeFontInfo:
                    raise RuntimeError('AbstractFont has no font largeFontInfo')
                self._largeFont = self.largeFontInfo.makeFont()
            return self._largeFont

    def __init__(
            self,
            scale: float,
            style: travellermap.Style
            ):
        self._scale = scale
        self._style = style
        self._handleConfigUpdate()

    @property
    def scale(self) -> float:
        return self._scale
    @scale.setter
    def scale(self, scale: float) -> None:
        self._scale = scale
        self._handleConfigUpdate()

    @property
    def style(self) -> float:
        return self._style
    @scale.setter
    def style(self, style: float) -> None:
        self._style = style
        self._handleConfigUpdate()

    @property
    def hasWorldOverlays(self) -> bool:
        return self.populationOverlay.visible or \
            self.importanceOverlay.visible or  \
            self.highlightWorlds.visible or \
            self.showStellarOverlay or \
            self.capitalOverlay.visible

    def _handleConfigUpdate(self) -> None:
        # Options
        self.backgroundColor = '#000000'

        self.imageBorderColor ='#FF0000'
        self.imageBorderWidth = 0.2

        self.showNebulaBackground = False
        self.showGalaxyBackground = False
        self.useWorldImages = False
        self.dimUnofficialSectors = False
        self.colorCodeSectorStatus = False

        self.deepBackgroundOpacity = 0.0 # TODO: Not sure about this

        self.grayscale = False
        self.lightBackground = False

        self.showRiftOverlay = False
        self.riftOpacity = 0.0 # TODO: Not sure about this

        self.hexContentScale = 1.0
        self.hexRotation = 0

        self.routeEndAdjust = 0.25

        # TODO: Not sure I'll need this
        self.preferredMimeType = ''
        self.t5AllegianceCodes = False

        self.highlightWorlds = StyleSheet.StyleElement()
        self.highlightWorldsPattern: typing.Optional[HighlightWorldPattern] = None

        self.droyneWorlds = StyleSheet.StyleElement()
        self.ancientsWorlds = StyleSheet.StyleElement()
        self.minorHomeWorlds = StyleSheet.StyleElement()

        # Worlds
        self.worlds = StyleSheet.StyleElement()
        self.showWorldDetailColors = False
        self.populationOverlay = StyleSheet.StyleElement()
        self.importanceOverlay = StyleSheet.StyleElement()
        self.capitalOverlay = StyleSheet.StyleElement()
        self.capitalOverlayAltA = StyleSheet.StyleElement()
        self.capitalOverlayAltB = StyleSheet.StyleElement()
        self.showStellarOverlay = False

        self.discPosition = PointF(0, 0)
        self.discRadius = 0.1
        self.gasGiantPosition = PointF(0, 0)
        self.allegiancePosition = PointF(0, 0)
        self.baseTopPosition = PointF(0, 0)
        self.baseBottomPosition = PointF(0, 0)
        self.baseMiddlePosition = PointF(0, 0)

        self.uwp = StyleSheet.StyleElement()
        self.starport = StyleSheet.StyleElement()

        #self.glyphFont = FontInfo() # TODO: Need to figure out defaults
        self.worldDetails: WorldDetails = 0
        self.lowerCaseAllegiance = False
        #self.wingdingFont = FontInfo() # TODO: Need to figure out defaults
        self.showGasGiantRing = False

        self.showTL = False
        self.ignoreBaseBias = False
        self.showZonesAsPerimeters = False

        # Hex Coordinates
        self.hexNumber = StyleSheet.StyleElement()
        self.hexCoordinateStyle = HexCoordinateStyle.Sector
        self.numberAllHexes = False

        # Sector Name
        self.sectorName = StyleSheet.StyleElement()
        self.showSomeSectorNames = False
        self.showAllSectorNames = False

        self.capitals = StyleSheet.StyleElement()
        self.subsectorNames = StyleSheet.StyleElement()
        self.greenZone = StyleSheet.StyleElement()
        self.amberZone = StyleSheet.StyleElement()
        self.redZone = StyleSheet.StyleElement()
        self.sectorGrid = StyleSheet.StyleElement()
        self.subsectorGrid = StyleSheet.StyleElement()
        self.parsecGrid = StyleSheet.StyleElement()
        self.worldWater = StyleSheet.StyleElement()
        self.worldNoWater = StyleSheet.StyleElement()
        self.macroRoutes = StyleSheet.StyleElement()
        self.microRoutes = StyleSheet.StyleElement()
        self.macroBorders = StyleSheet.StyleElement()
        self.megaNames = StyleSheet.StyleElement()
        self.pseudoRandomStars = StyleSheet.StyleElement()
        self.placeholder = StyleSheet.StyleElement()
        self.anomaly = StyleSheet.StyleElement()

        self.microBorders = StyleSheet.StyleElement()
        self.fillMicroBorders = False
        self.shadeMicroBorders = False
        self.showMicroNames = False
        self.microBorderStyle = MicroBorderStyle.Hex
        self.hexStyle = HexStyle.Hex
        self.overrideLineStyle: typing.Optional[LineStyle] = None

        # TODO: The stuff below is still a WIP

        self.parsecGrid.visible = True
        self.worlds.visible = True

        self.numberAllHexes = True # TODO: Remove override of default

        self.hexNumber.textColor = '#FF0000'

        onePixel = 1.0 / self.scale
        self.parsecGrid.pen = AbstractPen('#FF0000', onePixel)

        if self.worlds.visible:
            fontScale = 1 if (self.scale <= 96 or self.style == travellermap.Style.Candy) else 96 / min(self.scale, 192)
            self.hexNumber.fontInfo = FontInfo(
                StyleSheet._DefaultFont,
                0.1 * fontScale)

class LayerAction(object):
    def __init__(
            self,
            id: LayerId,
            action: typing.Callable[[], typing.NoReturn],
            clip: bool
            ) -> None:
        self.id = id
        self.action = action
        self.clip = clip

class RenderContext(object):
    _HexEdge = math.tan(math.pi / 6) / 4 / travellermap.ParsecScaleX

    def __init__(
            self,
            graphics: AbstractGraphics,
            tileRect: RectangleF, # Region to render in map coordinates
            tileSize: Size, # Pixel size of view to render to
            scale: float,
            styles: StyleSheet,
            options: MapOptions
            ) -> None:
        self._graphics = graphics
        self._tileRect = tileRect
        self._scale = scale
        self._options = options
        self._styles = styles
        self._tileSize = tileSize
        self._createLayers()
        self._updateSpaceTransforms()

    def setTileRect(self, rect: RectangleF) -> None:
        self._tileRect = rect
        self._updateSpaceTransforms()

    def setTileSize(self, size: Size) -> None:
        self._tileSize  = size
        self._updateSpaceTransforms()

    def setScale(self, scale: float) -> None:
        self._scale = scale
        self._updateSpaceTransforms()

    def moveRelative(self, dx: float, dy: float) -> None:
        self._tileRect.x += (dx * self._scale)
        self._tileRect.y += (dy * self._scale)
        self._updateSpaceTransforms()

    def pixelSpaceToMapSpace(self, point: Point) -> PointF:
        return self._worldSpaceToImageSpace.transform(point)

    def render(self) -> None:
        with self._graphics.save():
            self._graphics.multiplyTransform(self._imageSpaceToWorldSpace)

            for layer in self._layers:
                # TODO: Implement clipping if I need it
                """
                // HACK: Clipping to tileRect rapidly becomes inaccurate away from
                // the origin due to float precision. Only do it if really necessary.
                bool clip = layer.clip && (ctx.ForceClip ||
                    !((ClipPath == null) && (graphics is BitmapGraphics)));

                // Impose a clipping region if desired, or remove it if not.
                if (clip && state == null)
                {
                    state = graphics.Save();
                    if (ClipPath != null) graphics.IntersectClip(ClipPath);
                    else graphics.IntersectClip(tileRect);
                }
                else if (!clip && state != null)
                {
                    state.Dispose();
                    state = null;
                }

                layer.Run(this);
                timers.Add(new Timer(layer.id.ToString()));
                """
                layer.action()

    def _createLayers(self) -> None:
        # TODO: This list probably only needs created once
        self._layers: typing.List[LayerAction] = [
            LayerAction(id=LayerId.Background_Solid, action=self._drawBackground, clip=True),
            LayerAction(id=LayerId.Grid_Parsec, action=self._drawParsecGrid, clip=True)
        ]

        self._layers.sort(key=lambda l: l.id.value)

    def _updateSpaceTransforms(self):
        m = AbstractMatrix()
        m.translatePrepend(
            dx=-self._tileRect.left * self._scale * travellermap.ParsecScaleX,
            dy=-self._tileRect.top * self._scale * travellermap.ParsecScaleY)
        m.scalePrepend(
            sx=self._scale * travellermap.ParsecScaleX,
            sy=self._scale * travellermap.ParsecScaleY)
        self._imageSpaceToWorldSpace = AbstractMatrix(m)
        m.invert()
        self._worldSpaceToImageSpace = AbstractMatrix(m)

    def _drawBackground(self) -> None:
        self._graphics.setSmoothingMode(AbstractGraphics.SmoothingMode.HighSpeed)

        # TODO: Inefficient to create this every frame
        brush = AbstractBrush(self._styles.backgroundColor)

        # NOTE: This is a comment from the original Traveller Map source code
        # HACK: Due to limited precisions of floats, tileRect can end up not covering
        # the full bitmap when far from the origin.
        rect = RectangleF(self._tileRect)
        rect.inflate(rect.width * 0.1, rect.height * 0.1)
        self._graphics.drawRectangleFill(brush, rect)

    def _drawParsecGrid(self) -> None:
        if not self._styles.parsecGrid.visible:
            return

        self._graphics.setSmoothingMode(AbstractGraphics.SmoothingMode.HighQuality)


        self._graphics.drawRectangleFill(
            brush=AbstractBrush('#0000FF'),
            rect=RectangleF(-0.5, -0.5, 1, 1))

        parsecSlop = 1

        hx = int(math.floor(self._tileRect.x))
        hw = int(math.ceil(self._tileRect.width))
        hy = int(math.floor(self._tileRect.y))
        hh = int(math.ceil(self._tileRect.height))

        pen = self._styles.parsecGrid.pen

        if self._styles.hexStyle == HexStyle.Square:
            for px in range(hx - parsecSlop, hx + hw + parsecSlop):
                yOffset = 0 if ((px % 2) != 0) else 0.5
                for py in range(hy - parsecSlop, hy + hh + parsecSlop):
                    inset = 1
                    self._graphics.drawRectangleOutline(
                        pen,
                        RectangleF(
                            x=px + inset,
                            y=py + inset + yOffset,
                            width=1 - inset * 2,
                            height=1 - inset * 2))
        elif self._styles.hexStyle == HexStyle.Hex:
            points = [None] * 4
            for px in range(hx - parsecSlop, hx + hw + parsecSlop):
                yOffset = 0 if ((px % 2) != 0) else 0.5
                for py in range(hy - parsecSlop, hy + hh + parsecSlop):
                    points[0] = PointF(px + -RenderContext._HexEdge, py + 0.5 + yOffset)
                    points[1] = PointF(px + RenderContext._HexEdge, py + 1.0 + yOffset)
                    points[2] = PointF(px + 1.0 - RenderContext._HexEdge, py + 1.0 + yOffset)
                    points[3] = PointF(px + 1.0 + RenderContext._HexEdge, py + 0.5 + yOffset)
                    self._graphics.drawLines(pen, points)

        # TODO: The if statment in the traveller map code is this
        #if (styles.numberAllHexes &&
        #    styles.worldDetails.HasFlag(WorldDetails.Hex))
        if self._styles.numberAllHexes:
            solidBrush = AbstractBrush(self._styles.hexNumber.textColor)
            for px in range(hx - parsecSlop, hx + hw + parsecSlop):
                yOffset = 0 if ((px % 2) != 0) else 0.5
                for py in range(hy - parsecSlop, hy + hh + parsecSlop):

                    if self._styles.hexCoordinateStyle == HexCoordinateStyle.Subsector:
                        # TODO: Need to implement Subsector hex number. Not sure what this
                        # actually is
                        hex = 'TODO'
                    else:
                        relativePos = travellermap.absoluteSpaceToRelativeSpace((px + 1, py + 1))
                        hex = f'{relativePos[2]:02d}{relativePos[3]:02d}'

                    with self._graphics.save():
                        self._graphics.translateTransform(px + 0.5, py + yOffset)
                        self._graphics.scaleTransform(
                            self._styles.hexContentScale / travellermap.ParsecScaleX,
                            self._styles.hexContentScale / travellermap.ParsecScaleY)
                        self._graphics.drawString(
                            hex,
                            self._styles.hexNumber.font,
                            solidBrush,
                            0, 0,
                            StringAlignment.TopCenter)


class QtGraphics(AbstractGraphics):
    _DashStyleMap = {
        DashStyle.Solid: QtCore.Qt.PenStyle.SolidLine,
        DashStyle.Dot: QtCore.Qt.PenStyle.DotLine,
        DashStyle.Dash: QtCore.Qt.PenStyle.DashLine,
        DashStyle.DashDot: QtCore.Qt.PenStyle.DashDotLine,
        DashStyle.DashDotDot: QtCore.Qt.PenStyle.DashDotDotLine,
        DashStyle.Custom: QtCore.Qt.PenStyle.CustomDashLine}

    def __init__(self):
        super().__init__()
        self._painter = None

    def setPainter(self, painter: QtGui.QPainter) -> None:
        self._painter = painter

    def scaleTransform(self, scaleX: float, scaleY: float) -> None:
        transform = QtGui.QTransform()
        transform.scale(scaleX, scaleY)
        self._painter.setTransform(
            transform * self._painter.transform())
        #self._painter.setTransform(
        #    self._painter.transform() * transform)
    def translateTransform(self, dx: float, dy: float) -> None:
        transform = QtGui.QTransform()
        transform.translate(dx, dy)
        self._painter.setTransform(
            transform * self._painter.transform())
        #self._painter.setTransform(
        #    self._painter.transform() * transform)
    def rotateTransform(self, angle: float) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement rotateTransform')
    def multiplyTransform(self, matrix: AbstractMatrix) -> None:
        self._painter.setTransform(
            self._convertMatrix(matrix) * self._painter.transform())

    # TODO: This was an overload of intersectClip in traveller map code
    def intersectClipPath(self, path: AbstractPath) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement IntersectClip')
    # TODO: This was an overload of intersectClip in traveller map code
    def intersectClipRect(self, rect: RectangleF) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement IntersectClip')

    # TODO: There was also an overload that takes 4 individual floats in the traveller map code
    def drawLine(self, pen: AbstractPen, pt1: PointF, pt2: PointF) -> None:
        self._painter.setPen(self._convertPen(pen))
        self._painter.drawLine(pt1.x, pt1.y, pt2.x, pt2.y)

    def drawLines(self, pen: AbstractPen, points: typing.Sequence[PointF]):
        self._painter.setPen(self._convertPen(pen))
        self._painter.drawPolyline(self._convertPoints(points))

    # TODO: This was an overload of drawPath in the traveller map code
    def drawPathOutline(self, pen: AbstractPen, path: AbstractPath):
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawPathOutline')
    # TODO: This was an overload of drawPath in the traveller map code
    def drawPathFill(self, brush: AbstractBrush, path: AbstractPath):
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawPathFill')
    def drawCurve(self, pen: AbstractPen, points: typing.Sequence[PointF], tension: float = 0.5):
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawCurve')
    # TODO: This was an overload of drawClosedCurve in the traveller map code
    def drawClosedCurveOutline(self, pen: AbstractPen, points: typing.Sequence[PointF], tension: float = 0.5):
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawClosedCurveOutline')
    def drawClosedCurveFill(self, brush: AbstractBrush, points: typing.Sequence[PointF], tension: float = 0.5):
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawClosedCurveFill')
    # TODO: There was also an overload that takes 4 individual floats in the traveller map code
    def drawRectangleOutline(self, pen: AbstractPen, rect: RectangleF) -> None:
        self._painter.setPen(self._convertPen(pen))
        self._painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        self._painter.drawRect(self._convertRect(rect))
    # TODO: There was also an overload that takes 4 individual floats in the traveller map code
    def drawRectangleFill(self, brush: AbstractBrush, rect: RectangleF) -> None:
        self._painter.setPen(QtCore.Qt.PenStyle.NoPen)
        self._painter.setBrush(self._convertBrush(brush))
        self._painter.drawRect(self._convertRect(rect))

    # TODO: This has changed quite a bit from the traveller map interface
    def drawEllipse(self, pen: typing.Optional[AbstractPen], brush: typing.Optional[AbstractBrush], rect: RectangleF):
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawEllipse')
    def drawArc(self, pen: AbstractPen, rect: RectangleF, startAngle: float, sweepAngle: float) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawArc')

    def drawImage(self, image: AbstractImage, rect: RectangleF) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawImage')
    def drawImageAlpha(self, alpha: float, image: AbstractImage, rect: RectangleF) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawImageAlpha')

    def measureString(self, text: str, font: AbstractFont) -> SizeF:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement measureString')
    def drawString(self, text: str, font: AbstractFont, brush: AbstractBrush, x: float, y: float, format: StringAlignment) -> None:
        qtFont = self._convertFont(font)
        scale = font.emSize / qtFont.pointSize()

        self._painter.setFont(qtFont)
        self._painter.setBrush(self._convertBrush(brush))

        # TODO: This should maybe use self.measureString but it depends
        # what coordinates it ends up working in
        fontMetrics = QtGui.QFontMetrics(qtFont)
        contentPixelRect = fontMetrics.boundingRect(
            QtCore.QRect(0, 0, 65535, 65535),
            QtCore.Qt.AlignmentFlag.AlignCenter,
            text)
        contentPixelRect.moveTo(0, 0)

        self._painter.save()
        try:
            self.translateTransform(x, y)
            self.scaleTransform(scale, scale)

            if format == StringAlignment.Baseline:
                # TODO: Handle BaseLine strings
                #float fontUnitsToWorldUnits = font.Size / font.FontFamily.GetEmHeight(font.Style);
                #float ascent = font.FontFamily.GetCellAscent(font.Style) * fontUnitsToWorldUnits;
                #g.DrawString(s, font.Font, this.brush, x, y - ascent);
                self._painter.drawText(QtCore.QPointF(x, y), text)
            elif format == StringAlignment.Centered:
                self._painter.drawText(
                    QtCore.QPointF(
                        -contentPixelRect.width() / 2,
                        contentPixelRect.height() / 2),
                    text)
            elif format == StringAlignment.TopLeft:
                self._painter.drawText(
                    QtCore.QPointF(
                        0,
                        contentPixelRect.height()),
                    text)
            elif format == StringAlignment.TopCenter:
                self._painter.drawText(
                    QtCore.QPointF(
                        -contentPixelRect.width() / 2,
                        contentPixelRect.height()),
                    text)
            elif format == StringAlignment.TopRight:
                self._painter.drawText(
                    QtCore.QPointF(
                        -contentPixelRect.width(),
                        contentPixelRect.height()),
                    text)
            elif format == StringAlignment.CenterLeft:
                self._painter.drawText(
                    QtCore.QPointF(
                        -contentPixelRect.width(),
                        contentPixelRect.height() / 2),
                    text)
        finally:
            self._painter.restore()

    def save(self) -> AbstractGraphicsState:
        self._painter.save()
        return AbstractGraphicsState(graphics=self)
    def restore(self) -> None:
        self._painter.restore()

    # TODO: Creating a new pen for every primitive that gets drawn is
    # really inefficient. The fact I'm using a string for the colour
    # so it will need to be parsed each time is even worse
    def _convertPen(self, pen: AbstractPen) -> QtGui.QPen:
        return QtGui.QPen(
            QtGui.QBrush(QtGui.QColor(pen.color)),
            pen.width,
            QtGraphics._DashStyleMap[pen.dashStyle])

    # TODO: Creating a new font for every piece of text that gets drawn is
    # really inefficient. The fact I'm using a string for the colour
    # so it will need to be parsed each time is even worse
    def _convertFont(self, font: AbstractFont) -> QtGui.QFont:
        # TODO: This is a temp hack, AbstractFont shouldn't be using QFont
        return font.font

    def _convertBrush(self, brush: AbstractBrush) -> QtGui.QBrush:
        return QtGui.QBrush(QtGui.QColor(brush.color))

    def _convertRect(self, rect: RectangleF) -> QtCore.QRectF:
        return QtCore.QRectF(rect.x, rect.y, rect.width, rect.height)

    def _convertPoints(
            self,
            points: typing.Sequence[PointF]
            ) -> typing.Sequence[QtCore.QPointF]:
        return [QtCore.QPointF(p.x, p.y) for p in points]

    def _convertMatrix(self, transform: AbstractMatrix) -> QtGui.QTransform:
        return QtGui.QTransform(
            transform.m11,
            transform.m12,
            0,
            transform.m21,
            transform.m22,
            0,
            transform.offsetX,
            transform.offsetY,
            1)

class MapHackView(QtWidgets.QWidget):
    _MinScale = 0.0078125 # Math.Pow(2, -7);
    _MaxScale = 512 # Math.Pow(2, 9);
    _DefaultScale = 64

    _WheelScaleMultiplier = 1.5

    _ZoomInScale = 1.25
    _ZoomOutScale = 0.8

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        scene = QtWidgets.QGraphicsScene()
        scene.setSceneRect(0, 0, self.width(), self.height())

        self._viewCenterMapPos = PointF(0, 0)
        self._tileSize = Size(self.width(), self.height())
        #self._scale = MapHackView._DefaultScale
        self._scale = 128
        self._style = travellermap.Style.Poster
        self._graphics = QtGraphics()
        self._renderer = self._createRender()

        self._isDragging = False
        self._dragPixelPos: typing.Optional[QtCore.QPoint] = None

        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)

    def clear(self) -> None:
        self._graphics = None

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        super().mousePressEvent(event)

        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._dragPixelPos = event.pos()

            mapCursor = self._renderer.pixelSpaceToMapSpace(point=Point(event.x(), event.y()))
            absCursor = travellermap.mapSpaceToAbsoluteSpace((mapCursor.x, mapCursor.y))
            #print(f'MAP: {mapCursor.x} {mapCursor.y}')
            #print(f'ABS: {absCursor[0]} {absCursor[1]}')
            relCursor = travellermap.absoluteSpaceToRelativeSpace(absCursor)
            print(f'{relCursor[2]} {relCursor[3]}')


    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        super().mouseMoveEvent(event)
        if self._renderer and self._dragPixelPos:
            point = event.pos()
            screenDelta = point - self._dragPixelPos
            mapDelta = PointF(
                screenDelta.x() / self._scale,
                screenDelta.y() / self._scale)
            self._dragPixelPos = point

            self._viewCenterMapPos.x -= mapDelta.x
            self._viewCenterMapPos.y -= mapDelta.y
            self._renderer.setTileRect(
                rect=self._calculateTileRect())
            self.repaint()

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        super().mouseReleaseEvent(event)

        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._dragPixelPos = None

    def focusOutEvent(self, event: QtGui.QFocusEvent) -> None:
        super().focusOutEvent(event)
        self._dragPixelPos = None

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        self._tileSize = Size(self.width(), self.height())
        self._renderer = self._createRender()

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        super().keyPressEvent(event)

        if self._renderer:
            dx = dy = None
            if event.key() == QtCore.Qt.Key.Key_Left:
                mapWidth = self._tileSize.width / (self._scale * travellermap.ParsecScaleX)
                dx = -mapWidth / 10
            elif event.key() == QtCore.Qt.Key.Key_Right:
                mapWidth = self._tileSize.width / (self._scale * travellermap.ParsecScaleX)
                dx = mapWidth / 10
            elif event.key() == QtCore.Qt.Key.Key_Up:
                mapHeight = self._tileSize.height / (self._scale * travellermap.ParsecScaleY)
                dy = -mapHeight / 10
            elif event.key() == QtCore.Qt.Key.Key_Down:
                mapHeight = self._tileSize.height / (self._scale * travellermap.ParsecScaleY)
                dy = mapHeight / 10

            if dx != None or dy != None:
                if dx != None:
                    self._viewCenterMapPos.x += dx
                if dy != None:
                    self._viewCenterMapPos.y += dy
                self._renderer.setTileRect(
                    rect=self._calculateTileRect())
                self.repaint()

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        super().wheelEvent(event)

        if self._renderer:
            cursorScreenPos = event.pos()
            oldCursorMapPos = self._renderer.pixelSpaceToMapSpace(PointF(
                cursorScreenPos.x(),
                cursorScreenPos.y()))

            if event.angleDelta().y() > 0:
                self._scale *= MapHackView._WheelScaleMultiplier
            else:
                self._scale /= MapHackView._WheelScaleMultiplier
            self._renderer = self._createRender()

            newCursorMapPos = self._renderer.pixelSpaceToMapSpace(PointF(
                cursorScreenPos.x(),
                cursorScreenPos.y()))

            self._viewCenterMapPos.x += oldCursorMapPos.x - newCursorMapPos.x
            self._viewCenterMapPos.y += oldCursorMapPos.y - newCursorMapPos.y

            self._renderer.setTileRect(
                rect=self._calculateTileRect())

            self.repaint()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        if not self._graphics or not self._renderer:
            return super().paintEvent(event)

        painter = QtGui.QPainter(self)
        try:
            self._graphics.setPainter(painter)
            self._renderer.render()
        finally:
            painter.end()

    def _createRender(self) -> RenderContext:
        return RenderContext(
            graphics=self._graphics,
            tileRect=self._calculateTileRect(),
            tileSize=self._tileSize,
            scale=self._scale,
            styles=StyleSheet(scale=self._scale, style=self._style),
            options=0)

    def _calculateTileRect(self) -> RectangleF:
        mapWidth = self._tileSize.width / (self._scale * travellermap.ParsecScaleX)
        mapHeight = self._tileSize.height / (self._scale * travellermap.ParsecScaleY)
        return RectangleF(
            x=self._viewCenterMapPos.x - (mapWidth / 2),
            y=self._viewCenterMapPos.y - (mapHeight / 2),
            width=mapWidth,
            height=mapHeight)

class MyWidget(gui.WindowWidget):
    def __init__(self):
        super().__init__(title='Map Hack', configSection='MapHack')
        self._widget = MapHackView()
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._widget)

        self.setLayout(layout)


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    window = MyWidget()
    window.show()
    app.exec_()
