from PyQt5 import QtWidgets, QtCore, QtGui
import PIL.Image, PIL.ImageDraw, PIL.ImageFont
import base64
import os
import gui
import io
import common
import typing
import enum
import math
import numpy
import random
import travellermap
import xml.etree.ElementTree

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

class FontStyle(enum.IntFlag):
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

class TextFormat(enum.Enum):
    TopLeft = 0
    TopCenter = 1
    TopRight = 2
    MiddleLeft = 3
    Center = 4
    MiddleRight = 5
    BottomLeft = 6
    BottomCenter = 7
    BottomRight = 8

class TextBackgroundStyle(enum.Enum):
    NoStyle = 0 # TODO: Was non in traveller map code
    Rectangle = 1
    Shadow = 2
    Outline = 3
    Filled = 4

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

class MapOptions(enum.IntFlag):
    SectorGrid = 0x0001
    SubsectorGrid = 0x0002

    SectorsSelected = 0x0004
    SectorsAll = 0x0008
    SectorsMask = SectorsSelected | SectorsAll

    BordersMajor = 0x0010
    BordersMinor = 0x0020
    BordersMask = BordersMajor | BordersMinor,

    NamesMajor = 0x0040
    NamesMinor = 0x0080
    NamesMask = NamesMajor | NamesMinor,

    # TODO: Do I need these if they're deprecated?
    WorldsCapitals = 0x0100
    WorldsHomeworlds = 0x0200
    WorldsMask = WorldsCapitals | WorldsHomeworlds,

    RoutesSelectedDeprecated = 0x0400

    PrintStyleDeprecated = 0x0800
    CandyStyleDeprecated = 0x1000
    StyleMaskDeprecated = PrintStyleDeprecated | CandyStyleDeprecated,

    ForceHexes = 0x2000
    WorldColors = 0x4000
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

class WorldDetails(enum.IntFlag):
    NoDetails = 0 # TODO: Was None in traveller map code

    Type = 1 << 0 # Show world type (water/no water/asteroid/unknown)
    KeyNames = 1 << 1 # Show HiPop/Capital names
    Starport = 1 << 2 # Show starport
    GasGiant = 1 << 3 # Show gas giant glyph
    Allegiance = 1 << 4 # Show allegiance code
    Bases = 1 << 5 # Show bases
    Hex = 1 << 6 # Include hex numbers
    Zone = 1 << 7 # Show Amber/Red zones
    AllNames = 1 << 8 # Show all world names, not just HiPop/Capitals
    Uwp = 1 << 9 # Show UWP below world name
    Asteroids = 1 << 10 # Render asteroids as pseudorandom ovals
    Highlight = 1 << 11 # Highlight (text font, text color) HiPopCapital worlds

    Dotmap = NoDetails
    Atlas = Type | KeyNames | Starport | GasGiant | Allegiance | Bases | Zone | Highlight
    Poster = Atlas | Hex | AllNames | Asteroids

class Size(object):
    @typing.overload
    def __init__(self) -> None: ...
    @typing.overload
    def __init__(self, other: 'Size') -> None: ...
    @typing.overload
    def __init__(self, width: int, height: int) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        if not args and not kwargs:
            self._width = self._height = 0
        elif len(args) + len(kwargs) == 1:
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
    def __init__(self) -> None: ...
    @typing.overload
    def __init__(self, other: 'SizeF') -> None: ...
    @typing.overload
    def __init__(self, width: float, height: float) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        if not args and not kwargs:
            self.width = self.height = 0
        elif len(args) + len(kwargs) == 1:
            other = args[0] if len(args) > 0 else kwargs['other']
            if not isinstance(other, SizeF):
                raise TypeError('The other parameter must be a SizeF')
            self.width = other.width
            self.height = other.height
        else:
            self.width = float(args[0] if len(args) > 0 else kwargs['width'])
            self.height = float(args[1] if len(args) > 1 else kwargs['height'])

    def __eq__(self, other: typing.Any) -> bool:
        if isinstance(other, SizeF):
            return self.width == other.width and self.height == other.height
        return super().__eq__(other)

class Point(object):
    @typing.overload
    def __init__(self) -> None: ...
    @typing.overload
    def __init__(self, other: 'PointF') -> None: ...
    @typing.overload
    def __init__(self, x: int, y: int) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        if not args and not kwargs:
            self.x = self.y = 0
        elif len(args) + len(kwargs) == 1:
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
    def __init__(self) -> None: ...
    @typing.overload
    def __init__(self, other: 'PointF') -> None: ...
    @typing.overload
    def __init__(self, x: float, y: float) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        if not args and not kwargs:
            self.x = self.y = 0
        elif len(args) + len(kwargs) == 1:
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
    def __init__(self) -> None: ...
    @typing.overload
    def __init__(self, other: 'RectangleF') -> None: ...
    @typing.overload
    def __init__(self, x: float, y: float, width: float, height: float) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        if not args and not kwargs:
            self.x = self.y = self.width = self.height = 0
        elif len(args) + len(kwargs) == 1:
            other = args[0] if len(args) > 0 else kwargs['other']
            if not isinstance(other, RectangleF):
                raise TypeError('The other parameter must be a RectangleF')
            self.x = other.x
            self.y = other.y
            self.width = other.width
            self.height = other.height
        else:
            self.x = float(args[0] if len(args) > 0 else kwargs['x'])
            self.y = float(args[1] if len(args) > 1 else kwargs['y'])
            self.width = float(args[2] if len(args) > 2 else kwargs['width'])
            self.height = float(args[3] if len(args) > 3 else kwargs['height'])

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

    @property
    def centre(self) -> PointF:
        return PointF(self.x + (self.width / 2), self.y + (self.height / 2))
    @centre.setter
    def centre(self, center: PointF) -> PointF:
        self.x = center.x - (self.width / 2)
        self.y = center.y - (self.height / 2)

    @property
    def location(self) -> PointF:
        return PointF(self.x, self.y)
    @location.setter
    def location(self, location: PointF) -> None:
        self.x = location.x
        self.y = location.y

    def inflate(self, x: float, y: float) -> None:
        self.x -= x
        self.y -= y
        self.width += x * 2
        self.height += y * 2

    def intersectsWith(self, rect: 'RectangleF') -> bool:
        return (rect.x < self.x + self.width) and \
            (self.x < rect.x + rect.width) and \
            (rect.y < self.y + self.height) and \
            (self.y < rect.y + rect.height)

    def __eq__(self, other: typing.Any) -> bool:
        if isinstance(other, RectangleF):
            return self.x == other.x and self.y == other.y and\
                self.height == other.height and self.width == other.width
        return super().__eq__(other)

class FontInfo():
    @typing.overload
    def __init__(self) -> None: ...
    @typing.overload
    def __init__(self, other: 'FontInfo') -> None: ...
    @typing.overload
    def __init__(self, families: str, size: float, style: FontStyle = FontStyle.Regular) -> None: ...

    def __init__(self, *args, **kwargs):
        if not args and not kwargs:
            self.families = ''
            self.size = 0
            self.style = FontStyle.Regular
        elif len(args) + len(kwargs) == 1:
            other = args[0] if len(args) > 0 else kwargs['other']
            if not isinstance(other, FontInfo):
                raise TypeError('The other parameter must be a FontInfo')
            self.families = other.families
            self.size = other.size
            self.style = other.style
        else:
            self.families = args[0] if len(args) > 0 else kwargs['families']
            self.size = float(args[1] if len(args) > 1 else kwargs['size'])
            self.style = args[2] if len(args) > 2 else kwargs.get('style', FontStyle.Regular)

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
    @typing.overload
    def __init__(self) -> None: ...
    @typing.overload
    def __init__(self, other: 'FontInfo') -> None: ...
    @typing.overload
    def __init__(
        self,
        color: str,
        width: float,
        dashStyle: DashStyle = DashStyle.Solid,
        customDashPattern: typing.Optional[typing.List[float]] = None
        ) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        if not args and not kwargs:
            self.color = ''
            self.width = 0
            self.dashStyle = DashStyle.Solid
            self.customDashPattern = None
        elif len(args) + len(kwargs) == 1:
            other = args[0] if len(args) > 0 else kwargs['other']
            if not isinstance(other, AbstractPen):
                raise TypeError('The other parameter must be an AbstractPen')
            self.color = other.color
            self.width = other.width
            self.dashStyle = other.dashStyle
            self.customDashPattern = list(other.customDashPattern) if other.customDashPattern else None
        else:
            self.color = args[0] if len(args) > 0 else kwargs['color']
            self.width = args[1] if len(args) > 1 else kwargs['width']
            self.dashStyle = args[1] if len(args) > 2 else kwargs.get('dashStyle', DashStyle.Solid)
            self.customDashPattern = args[1] if len(args) > 3 else kwargs.get('customDashPattern', None)

class AbstractBrush(object):
    @typing.overload
    def __init__(self) -> None: ...
    @typing.overload
    def __init__(self, other: 'AbstractBrush') -> None: ...
    @typing.overload
    def __init__(self, color: str) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        if not args and not kwargs:
            self.color = ''
        elif len(args) > 0:
            arg = args[0]
            self.color = arg.color if isinstance(arg, AbstractBrush) else arg
        elif 'other' in kwargs:
            other = kwargs['other']
            if not isinstance(other, AbstractBrush):
                raise TypeError('The other parameter must be an AbstractBrush')
            self.color = other.color
        elif 'color' in kwargs:
            self.color = kwargs['color']
        else:
            raise ValueError('Invalid arguments')

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
                    # Qt doesn't support floating point fonts so instead the font that
                    # is created is always the same point size and we scale it to the
                    # required em size
                    #self.font.setPointSizeF(emSize)
                    self.font.setPointSizeF(10)
                    if style & FontStyle.Bold:
                        self.font.setBold(True)
                    if style & FontStyle.Italic:
                        self.font.setItalic(True)
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

class PathPointType(enum.IntFlag):
    #
    # Summary:
    #     The starting point of a System.Drawing.Drawing2D.GraphicsPath object.
    Start = 0
    #
    # Summary:
    #     A line segment.
    Line = 1
    #
    # Summary:
    #     A default Bézier curve.
    Bezier = 3
    #
    # Summary:
    #     A mask point.
    PathTypeMask = 7
    #
    # Summary:
    #     The corresponding segment is dashed.
    DashMode = 0x10
    #
    # Summary:
    #     A path marker.
    PathMarker = 0x20
    #
    # Summary:
    #     The endpoint of a subpath.
    CloseSubpath = 0x80,
    #
    # Summary:
    #     A cubic Bézier curve.
    Bezier3 = 3

class AbstractPath(object):
    def __init__(
            self,
            points: typing.Sequence[PointF],
            types: typing.Sequence[PathPointType],
            closed: bool
            ):
        if len(points) != len(types):
            raise ValueError('AbstractPath point and type vectors have different lengths')
        self._points = list(points)
        self._types = list(types)
        self.closed = closed

    @property
    def points(self) -> typing.Sequence[PointF]:
        return self._points
    @property
    def types(self) -> typing.Sequence[PathPointType]:
        return self._types

# TODO: In the same way as AbstractFont, the fact this is using a QT
# class is a hack and I need a way to abstract the image format in
# a way that they can still be rendered efficiently
class AbstractImage(object):
    def __init__(self, path: str):
        self.path = path

        self.image = QtGui.QImage(self.path, None)
        if not self.image:
            raise RuntimeError(f'Failed to load {self.path}')

    @property
    def width(self) -> int:
        return self.image.width()
    @property
    def height(self) -> int:
        return self.image.height()

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

    # TODO: Smoothing mode should probably be a property
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
    def rotateTransform(self, degrees: float) -> None:
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

class ImageCache(object):
    def __init__(self, basePath: str) -> None:
        # TODO: There is a readme in the /res/Candy/ that gives copyright info, I'll
        # need to include that as well
        self.nebulaImage = AbstractImage(os.path.join(basePath, 'res/Candy/Nebula.png'))
        self.riftImage = AbstractImage(os.path.join(basePath, 'res/Candy/Rifts.png'))
        self.galaxyImage = AbstractImage(os.path.join(basePath, 'res/Candy/Galaxy.png'))
        self.galaxyImageGray = AbstractImage(os.path.join(basePath, 'res/Candy/Galaxy_Gray.png'))
        self.worldImages: typing.Dict[str, AbstractImage] = {
            'Hyd0': AbstractImage(os.path.join(basePath, 'res/Candy/Hyd0.png')),
            'Hyd1': AbstractImage(os.path.join(basePath, 'res/Candy/Hyd1.png')),
            'Hyd2': AbstractImage(os.path.join(basePath, 'res/Candy/Hyd2.png')),
            'Hyd3': AbstractImage(os.path.join(basePath, 'res/Candy/Hyd3.png')),
            'Hyd4': AbstractImage(os.path.join(basePath, 'res/Candy/Hyd4.png')),
            'Hyd5': AbstractImage(os.path.join(basePath, 'res/Candy/Hyd5.png')),
            'Hyd6': AbstractImage(os.path.join(basePath, 'res/Candy/Hyd6.png')),
            'Hyd7': AbstractImage(os.path.join(basePath, 'res/Candy/Hyd7.png')),
            'Hyd8': AbstractImage(os.path.join(basePath, 'res/Candy/Hyd8.png')),
            'Hyd9': AbstractImage(os.path.join(basePath, 'res/Candy/Hyd9.png')),
            'HydA': AbstractImage(os.path.join(basePath, 'res/Candy/HydA.png')),
            'Belt': AbstractImage(os.path.join(basePath, 'res/Candy/Belt.png'))}

class LabelStyle(object):
    def __init__(
            self,
            rotation: float = 0,
            scale: SizeF = 1,
            translation: typing.Optional[PointF] = None,
            uppercase: bool = False,
            wrap: bool = False
            ) -> None:
        self.rotation = rotation
        self.scale = scale
        self.translation = translation if translation else PointF()
        self.uppercase = uppercase
        self.wrap = wrap

class MapObject(object):
    pass

class MapLabel(object):
    def __init__(
            self,
            text: str,
            position: PointF,
            minor: bool = False
            ) -> None:
        self.text = text
        self.position = PointF(position)
        self.minor = minor

class MapLabelCache(object):
    _MinorLabelsPath = 'res/labels/minor_labels.tab'
    _MajorLabelsPath = 'res/labels/mega_labels.tab'

    def __init__(self, basePath: str):
        self.minorLabels = self._loadFile(
            os.path.join(basePath, MapLabelCache._MinorLabelsPath))
        self.megaLabels = self._loadFile(
            os.path.join(basePath, MapLabelCache._MajorLabelsPath))

    def _loadFile(self, path: str) -> typing.List[MapLabel]:
        labels = []

        with open(path, 'r', encoding='utf-8-sig') as file:
            header = None
            for line in file.readlines():
                if not line:
                    continue
                if line.startswith('#'):
                    continue
                tokens = [t.strip() for t in line.split('\t')]
                if not header:
                    header = tokens
                    continue

                data = {header[i]:t for i, t in enumerate(tokens)}
                labels.append(MapLabel(
                    text=data['Text'].replace('\\n', '\n'),
                    position=PointF(x=float(data['X']), y=float(data['Y'])),
                    minor=bool(data['Minor'].lower() == 'true')))

        return labels

class VectorObject(MapObject):
    def __init__(
            self,
            name: str,
            originX: float,
            originY: float,
            scaleX: float,
            scaleY: float,
            nameX: float,
            nameY: float,
            points: typing.Sequence[PointF],
            types: typing.Optional[typing.Sequence[PathPointType]] = None,
            bounds: typing.Optional[RectangleF] = None,
            closed: bool = False,
            mapOptions: MapOptions = 0):
        super().__init__()

        if types and (len(points) != len(types)):
            pass # TODO: Remove debug code

        if types and (len(points) != len(types)):
            raise ValueError('VectorObject path point and type vectors have different lengths')

        self.name = name
        self.originX = originX
        self.originY = originY
        self.scaleX = scaleX
        self.scaleY = scaleY
        self.nameX = nameX
        self.nameY = nameY
        self.closed = closed
        self.mapOptions = mapOptions
        self._pathDataPoints = [PointF(p) for p in points]
        # TODO: This uses byte instead of PathPointType
        self._pathDataTypes = list(types) if types else None
        self._minScale = None
        self._maxScale = None
        self._cachedBounds = RectangleF(bounds) if bounds else None
        self._cachedPath: typing.Optional[AbstractPath] = None

    @property
    def pathDataPoints(self) -> typing.Sequence[PointF]:
        return self._pathDataPoints

    @property
    def bounds(self) -> RectangleF:
        # Compute bounds if not already set
        if (not self._cachedBounds) and self.pathDataPoints:
            left = right = top = bottom = None
            for point in self._pathDataPoints:
                if (not left) or (point.x < left):
                    left = point.x
                if (not right) or (point.x > right):
                    right = point.x
                if (not top) or (point.y < top):
                    top = point.y
                if (not bottom) or (point.y > bottom):
                    bottom = point.y
            self._cachedBounds = RectangleF(
                x=left,
                y=top,
                width=right - left,
                height=bottom - top)
        return RectangleF(self._cachedBounds) # Don't return internal copy

    @property
    def pathDataTypes(self) -> typing.List[int]:
        if not self._pathDataPoints:
            raise RuntimeError('Invalid VectorObject - PathDataPoints required')

        if not self._pathDataTypes:
            self._pathDataTypes = [PathPointType.Start]
            for _ in range(1, len(self._pathDataPoints)):
                self._pathDataTypes.append(PathPointType.Line)

        return self._pathDataTypes

    @property
    def path(self) -> AbstractPath:
        if not self.pathDataPoints:
            raise RuntimeError('Invalid VectorObject - PathDataPoints required')
        if not self._cachedPath:
            self._cachedPath = AbstractPath(
                points=self.pathDataPoints,
                types=self.pathDataTypes,
                closed=self.closed)
        return self._cachedPath

    def draw(
            self,
            graphics: AbstractGraphics,
            rect: RectangleF,
            pen: AbstractPen) -> None:
        transformedBounds = self._transformedBounds()
        if transformedBounds.intersectsWith(rect):
            with graphics.save():
                graphics.scaleTransform(scaleX=self.scaleX, scaleY=self.scaleY)
                graphics.translateTransform(dx=-self.originX, dy=-self.originY)
                graphics.drawPathOutline(pen, self.path)

    def drawName(
            self,
            graphics: AbstractGraphics,
            rect: RectangleF,
            font: AbstractFont,
            textBrush: AbstractBrush,
            labelStyle: LabelStyle
            ) -> None:
        transformedBounds = self._transformedBounds()
        if self.name and transformedBounds.intersectsWith(rect):
            str = self.name
            if labelStyle.uppercase:
                str = str.upper()
            pos = self._namePosition()

            with graphics.save():
                # TODO: Need to check rotation works here, GREAT RIFT text should be rotated (when I add support for it)
                graphics.translateTransform(dx=pos.x, dy=pos.y)
                graphics.scaleTransform(
                    scaleX=1.0 / travellermap.ParsecScaleX,
                    scaleY=1.0 / travellermap.ParsecScaleY)
                graphics.rotateTransform(-labelStyle.rotation)

                drawStringHelper(graphics, str, font, textBrush, 0, 0)

    def _transformedBounds(self) -> RectangleF:
        bounds = self.bounds

        bounds.x -= self.originX
        bounds.y -= self.originY

        bounds.x *= self.scaleX
        bounds.y *= self.scaleY
        bounds.width *= self.scaleX
        bounds.height *= self.scaleY
        if bounds.width < 0:
            bounds.x += bounds.width
            bounds.width = -bounds.width
        if bounds.height < 0:
            bounds.y += bounds.height
            bounds.height = -bounds.height

        return bounds

    def _namePosition(self) -> PointF:
        bounds = self.bounds
        transformedBounds = self._transformedBounds()
        center = transformedBounds.centre
        center.x += transformedBounds.width * (self.nameX / bounds.width)
        center.y += transformedBounds.height * (self.nameY / bounds.height)

        return center

# NOTE: My implementation of vectors is slightly different from the Traveller
# Map one. The vector format supports point types which specify a set of flags
# for each point that determine how the point should be interpreted. A full
# list of the flags can be found here
# https://learn.microsoft.com/en-us/windows/win32/api/gdiplusenums/ne-gdiplusenums-pathpointtype
# When vector definitions use the CloseSubpath flag the Traveller Map
# implementation keeps these keeps the sub paths as a single VectorObject (i.e.
# one VectorObject per file). The intention is that the rendering engine should
# interpret the flags and render separate sub paths. This is great if the
# rendering engine supports it, but if it doesn't (e.g. Qt) then it can make
# rendering more complex/inefficient. My implementation splits sub paths into
# multiple VectorObject to avoid repeated processing at render time
class VectorObjectCache(object):
    _BorderFiles = [
        'res/Vectors/Imperium.xml',
        'res/Vectors/Aslan.xml',
        'res/Vectors/Kkree.xml',
        'res/Vectors/Vargr.xml',
        'res/Vectors/Zhodani.xml',
        'res/Vectors/Solomani.xml',
        'res/Vectors/Hive.xml',
        'res/Vectors/SpinwardClient.xml',
        'res/Vectors/RimwardClient.xml',
        'res/Vectors/TrailingClient.xml']

    _RiftFiles = [
        'res/Vectors/GreatRift.xml',
        'res/Vectors/LesserRift.xml',
        'res/Vectors/WindhornRift.xml',
        'res/Vectors/DelphiRift.xml',
        'res/Vectors/ZhdantRift.xml']

    _RouteFiles = [
        'res/Vectors/J5Route.xml',
        'res/Vectors/J4Route.xml',
        'res/Vectors/CoreRoute.xml']

    def __init__(self, basePath: str):
        self.borders = self._loadFiles(basePath, VectorObjectCache._BorderFiles)
        self.rifts = self._loadFiles(basePath, VectorObjectCache._RiftFiles)
        self.routes = self._loadFiles(basePath, VectorObjectCache._RouteFiles)

    def _loadFiles(
            self,
            basePath: str,
            paths: typing.Iterable[str]
            ) -> typing.List[VectorObject]:
        vectors = []
        for path in paths:
            try:
                vectors.extend(self._loadFile(path=os.path.join(basePath, path)))
            except Exception as ex:
                # TODO: Do something better
                print(ex)
        return vectors


    def _loadFile(self, path: str) -> typing.Iterable[VectorObject]:
        with open(path, 'r', encoding='utf-8-sig') as file:
            content = file.read()

        rootElement = xml.etree.ElementTree.fromstring(content)

        name = ''
        element = rootElement.find('./Name')
        if element is not None:
            name = element.text

        mapOptions = 0
        element = rootElement.find('./MapOptions')
        if element is not None:
            for option in element.text.split():
                try:
                    mapOptions |= MapOptions[option]
                except Exception as ex:
                    # TODO: Do something better
                    print(ex)

        originX = 0
        element = rootElement.find('./OriginX')
        if element is not None:
            originX = float(element.text)

        originY = 0
        element = rootElement.find('./OriginY')
        if element is not None:
            originY= float(element.text)

        scaleX = 1 # TODO: Not sure about this default
        element = rootElement.find('./ScaleX')
        if element is not None:
            scaleX = float(element.text)

        scaleY = 1 # TODO: Not sure about this default
        element = rootElement.find('./ScaleY')
        if element is not None:
            scaleY = float(element.text)

        nameX = 0
        element = rootElement.find('./NameX')
        if element is not None:
            nameX = float(element.text)

        nameY = 0
        element = rootElement.find('./NameY')
        if element is not None:
            nameY = float(element.text)

        # TODO: Is this used?
        #element = rootElement.find('./Type')

        # NOTE: Loading the bounds from the file when it's present rather than
        # regenerating it from the points is important as it the bounds in the
        # file doesn't always match the bounds of the points (e.g. the Solomani
        # Sphere). As the bounds determine where the name name is drawn it needs
        # to match what Traveller Map uses.
        xElement = rootElement.find('./Bounds/X')
        yElement = rootElement.find('./Bounds/Y')
        widthElement = rootElement.find('./Bounds/Width')
        heightElement = rootElement.find('./Bounds/Height')
        bounds = None
        if xElement is not None and yElement is not None \
            and widthElement is not None and heightElement is not None:
            bounds = RectangleF(
                x=float(xElement.text),
                y=float(yElement.text),
                width=float(widthElement.text),
                height=float(heightElement.text))

        points = []
        for pointElement in rootElement.findall('./PathDataPoints/PointF'):
            x = 0
            element = pointElement.find('./X')
            if element is not None:
                x = float(element.text)

            y = 0
            element = pointElement.find('./Y')
            if element is not None:
                y = float(element.text)

            points.append(PointF(x=x, y=y))

        element = rootElement.find('./PathDataTypes')
        types = None
        if element is not None:
            types = base64.b64decode(element.text)
            startIndex = 0
            finishIndex = len(points) - 1
            vectorPoints = []
            vectors = []

            for currentIndex, (point, type) in enumerate(zip(points, types)):
                isStartPoint = (type & PathPointType.PathTypeMask) == PathPointType.Start
                isLastPoint = currentIndex == finishIndex
                isClosed = (type & PathPointType.CloseSubpath) == PathPointType.CloseSubpath

                if isClosed or isLastPoint:
                    vectorPoints.append(point)

                if (isStartPoint and vectorPoints) or isClosed or isLastPoint:
                    isFirstVector = not vectors
                    nextIndex = currentIndex + (0 if isStartPoint else 1)
                    vectors.append(VectorObject(
                        name=name if isFirstVector else '', # Only set name on first to avoid multiple rendering
                        originX=originX,
                        originY=originY,
                        scaleX=scaleX,
                        scaleY=scaleY,
                        nameX=nameX,
                        nameY=nameY,
                        points=vectorPoints,
                        types=types[startIndex:nextIndex],
                        bounds=bounds,
                        closed=isClosed,
                        mapOptions=mapOptions))
                    vectorPoints.clear()
                    startIndex = nextIndex

                vectorPoints.append(point)

            return vectors
        else:
            # No path data types so this is just a single path
            return [VectorObject(
                name=name,
                originX=originX,
                originY=originY,
                scaleX=scaleX,
                scaleY=scaleY,
                nameX=nameX,
                nameY=nameY,
                points=points,
                types=types,
                bounds=bounds,
                mapOptions=mapOptions)]

class MapColors(object):
    Black = '#000000'
    White = '#FFFFFF'
    Red = '#FF0000'
    Green = '#00FF00'
    Blue = '#0000FF'

    AntiqueWhite = '#FAEBD7'
    Brown = '#A52A2A'
    Cyan = '#00FFFF'
    DarkCyan = '#008B8B'
    DarkBlue = '#00008B'
    DarkGray = '#A9A9A9'
    DarkKhaki = '#BDB76B'
    DarkSlateGray = '#2F4F4F'
    DeepSkyBlue = '#00BFFF'
    DimGray = '#696969'
    Firebrick = '#B22222'
    Goldenrod = '#DAA520'
    Gray = '#808080'
    LightBlue = '#ADD8E6'
    LightGray = '#D3D3D3'
    MediumBlue = '#0000CD'
    Plum = '#DDA0DD'
    Wheat = '#F5DEB3'

    TravellerRed = '#E32736'
    TravellerAmber = '#FFCC00'
    TravellerGreen = '#048104'

class StyleSheet(object):
    _DefaultFont = 'Arial'

    _SectorGridMinScale = 1 / 2 # Below this, no sector grid is shown
    _SectorGridFullScale = 4 # Above this, sector grid opaque
    _SectorNameMinScale = 1
    _SectorNameAllSelectedScale = 4 # At this point, "Selected" == "All"
    _SectorNameMaxScale = 16
    _PseudoRandomStarsMinScale = 1 # Below this, no pseudo-random stars
    _PseudoRandomStarsMaxScale = 4 # Above this, no pseudo-random stars
    _SubsectorsMinScale = 8
    _SubsectorNameMinScale = 24
    _SubsectorNameMaxScale = 64
    _MegaLabelMaxScale = 1 / 4
    _MacroWorldsMinScale = 1 / 2
    _MacroWorldsMaxScale = 4
    _MacroLabelMinScale = 1 / 2
    _MacroLabelMaxScale = 4
    _MacroRouteMinScale = 1 / 2
    _MacroRouteMaxScale = 4
    _MacroBorderMinScale = 1 / 32
    _MicroBorderMinScale = 4
    _MicroNameMinScale = 16
    _RouteMinScale = 8 # Below this, routes not rendered
    _ParsecMinScale = 16 # Below this, parsec edges not rendered
    _ParsecHexMinScale = 48 # Below this, hex numbers not rendered
    _WorldMinScale = 4 # Below this: no worlds; above this: dotmap
    _WorldBasicMinScale = 24 # Above this: atlas-style abbreviated data
    _WorldFullMinScale = 48 # Above this: full poster-style data
    _WorldUwpMinScale = 96 # Above this: UWP shown above name

    _CandyMinWorldNameScale = 64
    _CandyMinUwpScale = 256
    _CandyMaxWorldRelativeScale = 512
    _CandyMaxBorderRelativeScale = 32
    _CandyMaxRouteRelativeScale = 32

    _T5AllegianceCodeMinScale = 64

    class StyleElement(object):
        def __init__(self):
            self.visible = False
            self.fillColor = ''
            self.content = ''
            self.pen = AbstractPen()
            self.textColor = ''
            self.textHighlightColor = ''

            self.textStyle = LabelStyle()
            self.textBackgroundStyle = TextBackgroundStyle.NoStyle
            self.fontInfo = FontInfo()
            self.smallFontInfo = FontInfo()
            self.mediumFontInfo = FontInfo()
            self.largeFontInfo = FontInfo()
            self.position = PointF()

            # TODO: Still to fill out
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
            options: MapOptions,
            style: travellermap.Style
            ):
        self._scale = scale
        self._options = options
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
    def options(self) -> MapOptions:
        return self._options
    @options.setter
    def options(self, options: MapOptions) -> None:
        self._options = options
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
        self.backgroundColor = MapColors.Black

        self.imageBorderColor = ''
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
        self.worldDetails: WorldDetails = WorldDetails.NoDetails
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
        self.macroNames = StyleSheet.StyleElement()
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

        self.layerOrder: typing.Dict[LayerId, int] = {}

        onePixel = 1.0 / self.scale

        self.subsectorGrid.visible = (self.scale >= StyleSheet._SubsectorsMinScale) and \
            ((self.options & MapOptions.SubsectorGrid) != 0)
        self.sectorGrid.visible = (self.scale >= StyleSheet._SectorGridMinScale) and \
            ((self._options & MapOptions.SectorGrid) != 0)
        self.parsecGrid.visible = (self.scale >= StyleSheet._ParsecMinScale)
        self.showSomeSectorNames = (self.scale >= StyleSheet._SectorNameMinScale) and \
            (self.scale <= StyleSheet._SectorNameMaxScale) and \
            ((self._options & MapOptions.SectorsMask) != 0)
        self.showAllSectorNames = self.showSomeSectorNames and \
            ((self.scale >= StyleSheet._SectorNameAllSelectedScale) or \
             ((self._options & MapOptions.SectorsAll) != 0))
        self.subsectorNames.visible = (self.scale >= StyleSheet._SubsectorNameMinScale) and \
            (self.scale <= StyleSheet._SubsectorNameMaxScale) and \
            ((self._options & MapOptions.SectorsMask) != 0)

        self.worlds.visible = self.scale >= StyleSheet._WorldMinScale
        self.pseudoRandomStars.visible = (StyleSheet._PseudoRandomStarsMinScale <= self.scale) and \
             (self.scale <= StyleSheet._PseudoRandomStarsMaxScale)
        self.showRiftOverlay = (self.scale <= StyleSheet._PseudoRandomStarsMaxScale) or \
             (StyleSheet.style == travellermap.Style.Candy)

        self.t5AllegianceCodes = self.scale >= StyleSheet._T5AllegianceCodeMinScale

        self.riftOpacity = StyleSheet._floatScaleInterpolate(
            minValue=0,
            maxValue=0.85,
            scale=self._scale,
            minScale=1 / 4,
            maxScale=4)

        self.deepBackgroundOpacity = StyleSheet._floatScaleInterpolate(
            minValue=1,
            maxValue=0,
            scale=self._scale,
            minScale=1 / 8,
            maxScale=2)

        self.macroRoutes.visible = (self.scale >= StyleSheet._MacroRouteMinScale) and \
            (self.scale <= StyleSheet._MacroRouteMaxScale)
        self.macroNames.visible = (self.scale >= StyleSheet._MacroLabelMinScale) and \
            (self.scale <= StyleSheet._MacroLabelMaxScale)
        self.megaNames.visible = self.scale <= StyleSheet._MegaLabelMaxScale and \
            ((self.options & MapOptions.NamesMask) != 0)
        self.showMicroNames = (self.scale >= StyleSheet._MicroNameMinScale) and \
            ((self.options & MapOptions.NamesMask) != 0)
        self.capitals.visible = (self.scale >= StyleSheet._MacroWorldsMinScale) and \
            (self.scale <= StyleSheet._MacroWorldsMaxScale)

        self.hexStyle = \
            HexStyle.Square \
            if ((self.options & MapOptions.ForceHexes) == 0) and (self.scale < StyleSheet._ParsecHexMinScale) else \
            HexStyle.Hex
        self.microBorderStyle = MicroBorderStyle.Square if self.hexStyle == HexStyle.Square else MicroBorderStyle.Hex

        self.macroBorders.visible = (self.scale >= StyleSheet._MacroBorderMinScale) and \
            (self.scale < StyleSheet._MicroBorderMinScale) and \
            ((self.options & MapOptions.BordersMask) != 0)
        self.microBorders.visible = (self.scale >= StyleSheet._MicroBorderMinScale) and \
            ((self.options & MapOptions.BordersMask) != 0)
        self.fillMicroBorders = self.microBorders.visible and \
            ((self.options & MapOptions.FilledBorders) != 0)
        self.microRoutes.visible = (self.scale >= StyleSheet._RouteMinScale)

        if self.scale < StyleSheet._WorldBasicMinScale:
            self.worldDetails = WorldDetails.Dotmap
        elif self.scale < StyleSheet._WorldFullMinScale:
            self.worldDetails = WorldDetails.Atlas
        else:
            self.worldDetails = WorldDetails.Poster

        self.discRadius = 0.1 if ((self.worldDetails & WorldDetails.Type) != 0) else  0.2

        self.showWorldDetailColors = self.worldDetails == WorldDetails.Poster and \
            ((self.options & MapOptions.WorldColors) != 0)

        self.lowerCaseAllegiance = (self.scale < StyleSheet._WorldFullMinScale)
        self.showGasGiantRing = (self.scale >= StyleSheet._WorldUwpMinScale)

        self.worlds.textBackgroundStyle = TextBackgroundStyle.Rectangle

        self.hexCoordinateStyle = HexCoordinateStyle.Sector
        self.numberAllHexes = False

        if self.scale < StyleSheet._WorldFullMinScale:
            # Atlas-style

            x = 0.225
            y = 0.125

            self.baseTopPosition = PointF(-x, -y)
            self.baseBottomPosition = PointF(-x, y)
            self.gasGiantPosition =  PointF(x, -y)
            self.allegiancePosition = PointF(x, y)

            self.baseMiddlePosition = PointF(
                -0.35 if ((self.options & MapOptions.ForceHexes) != 0) else -0.2,
                0)
            self.starport.position = PointF(0, -0.24)
            self.uwp.position = PointF(0, 0.24)
            self.worlds.position = PointF(0, 0.4)
        else:
            # Poster-style

            x = 0.25
            y = 0.18

            self.baseTopPosition = PointF(-x, -y)
            self.baseBottomPosition = PointF(-x, y)
            self.gasGiantPosition = PointF(x, -y)
            self.allegiancePosition = PointF(x, y)

            self.baseMiddlePosition = PointF(-0.35, 0)
            self.starport.position = PointF(0, -0.225)
            self.uwp.position = PointF(0, 0.225)
            self.worlds.position = PointF(0, 0.37)#  Don't hide hex bottom, leave room for UWP

        if self.scale >= StyleSheet._WorldUwpMinScale:
            self.worldDetails |= WorldDetails.Uwp
            self.baseBottomPosition.y = 0.1
            self.baseMiddlePosition.y = (self.baseBottomPosition.y + self.baseTopPosition.y) / 2
            self.allegiancePosition.Y = 0.1

        if self.worlds.visible:
            fontScale = \
                1 \
                if (self.scale <= 96) or (self.style == travellermap.Style.Candy) else \
                96 / min(self.scale, 192)

            self.worlds.fontInfo = FontInfo(
                StyleSheet._DefaultFont,
                0.2 if self.scale < StyleSheet._WorldFullMinScale else (0.15 * fontScale),
                FontStyle.Bold)
            self.wingdingFont = FontInfo(
                "Wingdings",
                0.2 if self.scale < StyleSheet._WorldFullMinScale else (0.175 * fontScale))
            self.glyphFont = FontInfo(
                "Arial Unicode MS,Segoe UI Symbol,Arial",
                0.175 if self.scale < StyleSheet._WorldFullMinScale else (0.15 * fontScale),
                FontStyle.Bold)
            self.uwp.fontInfo = FontInfo(StyleSheet._DefaultFont, 0.1 * fontScale)
            self.hexNumber.fontInfo = FontInfo(StyleSheet._DefaultFont, 0.1 * fontScale)
            self.worlds.smallFontInfo = FontInfo(
                StyleSheet._DefaultFont,
                0.2 if self.scale < StyleSheet._WorldFullMinScale else (0.1 * fontScale))
            self.worlds.largeFontInfo = self.worlds.fontInfo
            self.starport.fontInfo = \
                FontInfo(self.worlds.smallFontInfo) \
                if (self.scale < StyleSheet._WorldFullMinScale) else \
                FontInfo(self.worlds.fontInfo)

        self.sectorName.fontInfo = FontInfo(StyleSheet._DefaultFont, 5.5)
        self.subsectorNames.fontInfo = FontInfo(StyleSheet._DefaultFont, 1.5)

        overlayFontSize = max(onePixel * 12, 0.375)
        self.droyneWorlds.fontInfo = FontInfo(StyleSheet._DefaultFont, overlayFontSize)
        self.ancientsWorlds.fontInfo = FontInfo(StyleSheet._DefaultFont, overlayFontSize)
        self.minorHomeWorlds.fontInfo = FontInfo(StyleSheet._DefaultFont, overlayFontSize)

        self.droyneWorlds.content = "\u2605\u2606" # BLACK STAR / WHITE STAR
        self.minorHomeWorlds.content = "\u273B" # TEARDROP-SPOKED ASTERISK
        self.ancientsWorlds.content = "\u2600" # BLACK SUN WITH RAYS

        self.microBorders.fontInfo = FontInfo(
            StyleSheet._DefaultFont,
            # TODO: This was == rather tan <= but in my implementation scale isn't
            # usually going to be an integer value so <= seems more appropriate.
            # Just need to check it shouldn't be >=
            0.6 if self.scale <= StyleSheet._MicroNameMinScale else 0.25,
            FontStyle.Bold)
        self.microBorders.smallFontInfo = FontInfo(StyleSheet._DefaultFont, 0.15, FontStyle.Bold)
        self.microBorders.largeFontInfo = FontInfo(StyleSheet._DefaultFont, 0.75, FontStyle.Bold)

        self.macroNames.fontInfo = FontInfo(
            families=StyleSheet._DefaultFont,
            size=8 / 1.4,
            style=FontStyle.Bold)
        self.macroNames.smallFontInfo = FontInfo(
            families=StyleSheet._DefaultFont,
            size=5 / 1.4,
            style=FontStyle.Regular)
        self.macroNames.mediumFontInfo = FontInfo(
            families=StyleSheet._DefaultFont,
            size=6.5 / 1.4,
            style=FontStyle.Italic)

        test = self.macroNames.font
        families = test.font.families()

        megaNameScaleFactor = min(35, 0.75 * onePixel)
        self.megaNames.fontInfo = FontInfo(
            StyleSheet._DefaultFont,
            24 * megaNameScaleFactor,
            FontStyle.Bold)
        self.megaNames.mediumFontInfo = FontInfo(
            StyleSheet._DefaultFont,
            22 * megaNameScaleFactor,
            FontStyle.Regular)
        self.megaNames.smallFontInfo = FontInfo(
            StyleSheet._DefaultFont,
            18 * megaNameScaleFactor,
            FontStyle.Italic)

        self.capitals.fillColor = MapColors.Wheat
        self.capitals.textColor = MapColors.TravellerRed
        self.amberZone.visible = self.redZone.visible = True
        self.amberZone.pen.color = MapColors.TravellerAmber
        self.redZone.pen.color = MapColors.TravellerRed
        self.macroBorders.pen.color = MapColors.TravellerRed
        self.macroRoutes.pen.color = MapColors.White
        self.microBorders.pen.color = MapColors.Gray
        self.microRoutes.pen.color = MapColors.Gray

        self.microBorders.textColor = MapColors.TravellerAmber
        self.worldWater.fillColor = MapColors.DeepSkyBlue
        self.worldNoWater.fillColor = MapColors.White
        self.worldNoWater.pen.color = '#0000FF' # TODO: Color.Empty;

        gridColor = self._colorScaleInterpolate(
            scale=self.scale,
            minScale=StyleSheet._SectorGridMinScale,
            maxScale=StyleSheet._SectorGridFullScale,
            color=MapColors.Gray)
        self.parsecGrid.pen = AbstractPen(gridColor, onePixel)
        self.subsectorGrid.pen = AbstractPen(gridColor, onePixel * 2)
        self.sectorGrid.pen = AbstractPen(gridColor, (4 if self.subsectorGrid.visible else 2) * onePixel)
        self.worldWater.pen = AbstractPen(
            '#0000FF', # TODO: Color.Empty,
            max(0.01, onePixel))

        self.microBorders.textStyle.rotation = 0
        self.microBorders.textStyle.translation = PointF(0, 0)
        self.microBorders.textStyle.scale = SizeF(1.0, 1.0)
        self.microBorders.textStyle.uppercase = False

        self.sectorName.textStyle.rotation = -50 # degrees
        self.sectorName.textStyle.translation = PointF(0, 0)
        self.sectorName.textStyle.scale = SizeF(0.75, 1.0)
        self.sectorName.textStyle.uppercase = False
        self.sectorName.textStyle.wrap = True

        self.subsectorNames.textStyle = self.sectorName.textStyle

        self.worlds.textStyle.rotation = 0
        self.worlds.textStyle.scale = SizeF(1.0, 1.0)
        self.worlds.textStyle.translation = PointF(self.worlds.position)
        self.worlds.textStyle.uppercase = False

        self.hexNumber.position = PointF(0, -0.5)

        self.showNebulaBackground = False
        self.showGalaxyBackground = self.deepBackgroundOpacity > 0.0
        self.useWorldImages = False

        # Cap pen widths when zooming in
        penScale = 1 if self.scale <= 64 else (64 / self.scale)

        borderPenWidth = 1
        if self.scale >= StyleSheet._MicroBorderMinScale and \
            self.scale >= StyleSheet._ParsecMinScale:
            borderPenWidth = 0.16 * penScale

        routePenWidth = 0.2 if self.scale <= 16 else (0.08 * penScale)

        self.microBorders.pen.width = borderPenWidth
        self.macroBorders.pen.width = borderPenWidth
        self.microRoutes.pen.width = routePenWidth

        self.amberZone.pen.width = self.redZone.pen.width = 0.05 * penScale

        self.macroRoutes.pen.width = borderPenWidth
        self.macroRoutes.pen.dashStyle = DashStyle.Dash

        self.populationOverlay.fillColor = '#80FFFF00'
        self.importanceOverlay.fillColor = '#2080FF00'
        self.highlightWorlds.fillColor = '#80FF0000'

        self.populationOverlay.pen = AbstractPen(
            '#0000FF', # TODO: Color.Empty,
            0.03 * penScale,
            DashStyle.Dash)
        self.importanceOverlay.pen = AbstractPen(
            '#0000FF', # TODO: Color.Empty,
            0.03 * penScale,
            DashStyle.Dot)
        self.highlightWorlds.pen = AbstractPen(
            '#0000FF', # TODO: Color.Empty,
            0.03 * penScale,
            DashStyle.DashDot)

        self.capitalOverlay.fillColor = StyleSheet._makeAlphaColor(0x80, MapColors.TravellerGreen)
        self.capitalOverlayAltA.fillColor = StyleSheet._makeAlphaColor(0x80, MapColors.Blue)
        self.capitalOverlayAltB.fillColor = StyleSheet._makeAlphaColor(0x80, MapColors.TravellerAmber)

        fadeSectorSubsectorNames = True

        self.placeholder.content = "*"
        self.placeholder.fontInfo = FontInfo("Georgia", 0.6)
        self.placeholder.position = PointF(0, 0.17)

        self.anomaly.content = "\u2316"; # POSITION INDICATOR
        self.anomaly.fontInfo = FontInfo("Arial Unicode MS,Segoe UI Symbol", 0.6)

        # Generic colors; applied to various elements by default (see end of this method).
        # May be overridden by specific styles
        foregroundColor = MapColors.White
        lightColor = MapColors.LightGray
        darkColor = MapColors.DarkGray
        dimColor = MapColors.DimGray
        highlightColor = MapColors.TravellerRed

        layers: typing.List[LayerId] = [
            #------------------------------------------------------------
            # Background
            #------------------------------------------------------------

            LayerId.Background_Solid,
            LayerId.Background_NebulaTexture,
            LayerId.Background_Galaxy,
            LayerId.Background_PseudoRandomStars,
            LayerId.Background_Rifts,

            #------------------------------------------------------------
            # Foreground
            #------------------------------------------------------------

            LayerId.Macro_Borders,
            LayerId.Macro_Routes,

            LayerId.Grid_Sector,
            LayerId.Grid_Subsector,
            LayerId.Grid_Parsec,

            LayerId.Names_Subsector,

            LayerId.Micro_BordersFill,
            LayerId.Micro_BordersShade,
            LayerId.Micro_BordersStroke,
            LayerId.Micro_Routes,
            LayerId.Micro_BorderExplicitLabels,

            LayerId.Names_Sector,

            LayerId.Macro_GovernmentRiftRouteNames,
            LayerId.Macro_CapitalsAndHomeWorlds,
            LayerId.Mega_GalaxyScaleLabels,

            LayerId.Worlds_Background,
            LayerId.Worlds_Foreground,
            LayerId.Worlds_Overlays,

            #------------------------------------------------------------
            # Overlays
            #------------------------------------------------------------

            LayerId.Overlay_DroyneChirperWorlds,
            LayerId.Overlay_MinorHomeworlds,
            LayerId.Overlay_AncientsWorlds,
            LayerId.Overlay_ReviewStatus]

        if self._style is travellermap.Style.Poster:
            pass
        elif self._style is travellermap.Style.Atlas:
            self.grayscale = True
            self.lightBackground = True

            self.capitals.fillColor = MapColors.DarkGray
            self.capitals.textColor = MapColors.Black
            self.amberZone.pen.color = MapColors.LightGray
            self.redZone.pen.color = MapColors.Black
            self.macroBorders.pen.color = MapColors.Black
            self.macroRoutes.pen.color = MapColors.Gray
            self.microBorders.pen.color = MapColors.Black
            self.microRoutes.pen.color = MapColors.Gray

            foregroundColor = MapColors.Black
            self.backgroundColor = MapColors.White
            lightColor = MapColors.DarkGray
            darkColor = MapColors.DarkGray
            dimColor = MapColors.LightGray
            highlightColor = MapColors.Gray
            self.microBorders.textColor = MapColors.Gray
            self.worldWater.fillColor = MapColors.Black
            self.worldNoWater.fillColor = '#0000FF' # TODO: Color.Empty

            self.worldNoWater.fillColor = MapColors.White
            self.worldNoWater.pen = AbstractPen(MapColors.Black, onePixel)

            self.riftOpacity = min(self.riftOpacity, 0.70)

            self.showWorldDetailColors = False

            self.populationOverlay.fillColor = StyleSheet._makeAlphaColor(0x40, highlightColor)
            self.populationOverlay.pen.color = MapColors.Gray

            self.importanceOverlay.fillColor = StyleSheet._makeAlphaColor(0x20, highlightColor)
            self.importanceOverlay.pen.color = MapColors.Gray

            self.highlightWorlds.fillColor = StyleSheet._makeAlphaColor(0x30, highlightColor)
            self.highlightWorlds.pen.color = MapColors.Gray
        elif self._style is travellermap.Style.Fasa:
            self.showGalaxyBackground = False
            self.deepBackgroundOpacity = 0
            self.riftOpacity = 0

            inkColor = '#5C4033'

            foregroundColor = inkColor
            self.backgroundColor = MapColors.White

            # NOTE: This TODO came in from the Traveller Map code
            self.grayscale = True # TODO: Tweak to be "monochrome"
            self.lightBackground = True

            self.capitals.fillColor = inkColor
            self.capitals.textColor = inkColor
            self.amberZone.pen.color = inkColor
            self.amberZone.pen.width = onePixel * 2
            self.redZone.pen.color = '#0000FF' # TODO: Color.Empty
            self.redZone.fillColor = StyleSheet._makeAlphaColor(0x80, inkColor)

            self.macroBorders.pen.color = inkColor
            self.macroRoutes.pen.color = inkColor

            self.microBorders.pen.color = inkColor
            self.microBorders.pen.width = onePixel * 2
            self.microBorders.fontInfo.size *= 0.6
            self.microBorders.fontInfo.style = FontStyle.Regular

            self.microRoutes.pen.color = inkColor

            lightColor = StyleSheet._makeAlphaColor(0x80, inkColor)
            darkColor = inkColor
            dimColor = inkColor
            highlightColor = inkColor
            self.microBorders.textColor = inkColor
            self.hexStyle = HexStyle.Hex
            self.microBorderStyle = MicroBorderStyle.Curve

            self.parsecGrid.pen.color = lightColor
            self.sectorGrid.pen.color = lightColor
            self.subsectorGrid.pen.color = lightColor

            self.worldWater.fillColor = inkColor
            self.worldNoWater.fillColor = inkColor
            self.worldWater.pen.color = '#0000FF' # TODO: Color.Empty
            self.worldNoWater.pen.color = '#0000FF' # TODO: Color.Empty

            self.showWorldDetailColors = False

            self.worldDetails &= ~WorldDetails.Starport
            self.worldDetails &= ~WorldDetails.Allegiance
            self.worldDetails &= ~WorldDetails.Bases
            self.worldDetails &= ~WorldDetails.GasGiant
            self.worldDetails &= ~WorldDetails.Highlight
            self.worldDetails &= ~WorldDetails.Uwp
            self.worlds.fontInfo.size *= 0.85
            self.worlds.textStyle.translation = PointF(0, 0.25)

            self.numberAllHexes = True
            self.hexCoordinateStyle = HexCoordinateStyle.Subsector
            self.overrideLineStyle = LineStyle.Solid

            self.populationOverlay.fillColor = StyleSheet._makeAlphaColor(0x40, highlightColor)
            self.populationOverlay.pen.color = MapColors.Gray

            self.importanceOverlay.fillColor = StyleSheet._makeAlphaColor(0x20, highlightColor)
            self.importanceOverlay.pen.color = MapColors.Gray

            self.highlightWorlds.fillColor = StyleSheet._makeAlphaColor(0x30, highlightColor)
            self.highlightWorlds.pen.color = MapColors.Gray
        elif self._style is travellermap.Style.Print:
            self.lightBackground = True

            foregroundColor = MapColors.Black
            self.backgroundColor = MapColors.White
            lightColor = MapColors.DarkGray
            darkColor = MapColors.DarkGray
            dimColor = MapColors.LightGray
            self.microRoutes.pen.color = MapColors.Gray

            self.microBorders.textColor = MapColors.Brown

            self.amberZone.pen.color = MapColors.TravellerAmber
            self.worldNoWater.fillColor = MapColors.White
            self.worldNoWater.pen = AbstractPen(MapColors.Black, onePixel)

            self.riftOpacity = min(self.riftOpacity, 0.70)

            self.populationOverlay.fillColor = StyleSheet._makeAlphaColor(0x40, self.populationOverlay.fillColor)
            self.populationOverlay.pen.color = MapColors.Gray

            self.importanceOverlay.fillColor = StyleSheet._makeAlphaColor(0x20, self.importanceOverlay.fillColor)
            self.importanceOverlay.pen.color = MapColors.Gray

            self.highlightWorlds.fillColor = StyleSheet._makeAlphaColor(0x30, self.highlightWorlds.fillColor)
            self.highlightWorlds.pen.color = MapColors.Gray
        elif self._style is travellermap.Style.Draft:
            inkOpacity = 0xB0

            self.showGalaxyBackground = False
            self.lightBackground = True

            self.deepBackgroundOpacity = 0

            # TODO: I Need to handle alpha here
            self.backgroundColor = MapColors.AntiqueWhite
            foregroundColor = StyleSheet._makeAlphaColor(inkOpacity, MapColors.Black)
            highlightColor = StyleSheet._makeAlphaColor(inkOpacity, MapColors.TravellerRed)

            lightColor = StyleSheet._makeAlphaColor(inkOpacity, MapColors.DarkCyan)
            darkColor = StyleSheet._makeAlphaColor(inkOpacity, MapColors.Black)
            dimColor = StyleSheet._makeAlphaColor(inkOpacity / 2, MapColors.Black)

            self.subsectorGrid.pen.color = StyleSheet._makeAlphaColor(inkOpacity, MapColors.Firebrick)

            fontName = "Comic Sans MS"
            self.worlds.fontInfo.families = fontName
            self.worlds.smallFontInfo.families = fontName
            self.starport.fontInfo.families = fontName
            self.worlds.largeFontInfo.families = fontName
            self.worlds.largeFontInfo.size = self.worlds.fontInfo.size * 1.25
            self.worlds.fontInfo.size *= 0.8

            self.macroNames.fontInfo.families = fontName
            self.macroNames.mediumFontInfo.families = fontName
            self.macroNames.smallFontInfo.families = fontName
            self.megaNames.fontInfo.families = fontName
            self.megaNames.mediumFontInfo.families = fontName
            self.megaNames.smallFontInfo.families = fontName
            self.microBorders.smallFontInfo.families = fontName
            self.microBorders.largeFontInfo.families = fontName
            self.microBorders.fontInfo.families = fontName
            self.macroBorders.fontInfo.families = fontName
            self.macroRoutes.fontInfo.families = fontName
            self.capitals.fontInfo.families = fontName
            self.macroBorders.smallFontInfo.families = fontName

            self.microBorders.textStyle.uppercase = True

            self.sectorName.textStyle.uppercase = True
            self.subsectorNames.textStyle.uppercase = True

            # NOTE: This TODO came in from Traveller Map
            # TODO: Render small, around edges
            self.subsectorNames.visible = False

            self.worlds.textStyle.uppercase = True

            # NOTE: This TODO came in from Traveller Map
            # TODO: Decide on this. It's nice to not overwrite the parsec grid, but
            # it looks very cluttered, especially amber/red zones.
            self.worlds.textBackgroundStyle = TextBackgroundStyle.NoStyle

            self.worldDetails &= ~WorldDetails.Allegiance

            self.subsectorNames.fontInfo.families = fontName
            self.sectorName.fontInfo.families = fontName

            self.worlds.largeFontInfo.style |= FontStyle.Underline

            self.microBorders.pen.width = onePixel * 4
            self.microBorders.pen.dashStyle = DashStyle.Dot

            self.worldNoWater.fillColor = foregroundColor
            self.worldWater.fillColor = '#0000FF' # TODO: Color.Empty
            self.worldWater.pen = AbstractPen(foregroundColor, onePixel * 2)

            self.amberZone.pen.color = foregroundColor
            self.amberZone.pen.width = onePixel
            self.redZone.pen.width = onePixel * 2

            self.microRoutes.pen.color = MapColors.Gray

            self.parsecGrid.pen.color = lightColor
            self.microBorders.textColor = StyleSheet._makeAlphaColor(inkOpacity, MapColors.Brown)

            self.riftOpacity = min(self.riftOpacity, 0.30)

            self.numberAllHexes = True

            self.populationOverlay.fillColor = StyleSheet._makeAlphaColor(0x40, self.populationOverlay.fillColor)
            self.populationOverlay.pen.color = MapColors.Gray

            self.importanceOverlay.fillColor = StyleSheet._makeAlphaColor(0x20, self.importanceOverlay.fillColor)
            self.importanceOverlay.pen.color = MapColors.Gray

            self.highlightWorlds.fillColor = StyleSheet._makeAlphaColor(0x30, self.highlightWorlds.fillColor)
            self.highlightWorlds.pen.color = MapColors.Gray
        elif self._style is travellermap.Style.Candy:
            self.useWorldImages = True
            self.pseudoRandomStars.visible = False
            self.fadeSectorSubsectorNames = False

            self.showNebulaBackground = self.deepBackgroundOpacity < 0.5

            self.hexStyle = HexStyle.NoHex
            self.microBorderStyle = MicroBorderStyle.Curve

            self.sectorGrid.visible = self.sectorGrid.visible and (self.scale >= 4)
            self.subsectorGrid.visible = self.subsectorGrid.visible and (self.scale >= 32)
            self.parsecGrid.visible = False

            self.subsectorGrid.pen.width = 0.03 * (64.0 / self.scale)
            self.subsectorGrid.pen.dashStyle = DashStyle.Custom
            self.subsectorGrid.pen.customDashPattern = [10.0, 8.0]

            self.sectorGrid.pen.width = 0.03 * (64.0 / self.scale)
            self.sectorGrid.pen.dashStyle = DashStyle.Custom
            self.sectorGrid.pen.customDashPattern = [10.0, 8.0]

            self.worlds.textBackgroundStyle = TextBackgroundStyle.Shadow

            self.worldDetails = worldDetails &  ~WorldDetails.Starport & \
                ~WorldDetails.Allegiance & ~WorldDetails.Bases & ~WorldDetails.Hex

            if (self.scale < StyleSheet._CandyMinWorldNameScale):
                worldDetails = worldDetails & ~WorldDetails.KeyNames & ~WorldDetails.AllNames
            if (self.scale < StyleSheet._CandyMinUwpScale):
                worldDetails &= ~WorldDetails.Uwp

            self.amberZone.pen.color = MapColors.Goldenrod
            self.amberZone.pen.width = self.redZone.pen.width = 0.035

            self.sectorName.textStyle.rotation = 0
            self.sectorName.textStyle.translation = PointF(0, -0.25)
            self.sectorName.textStyle.scale = SizeF(0.5, 0.25)
            self.sectorName.textStyle.uppercase = True

            self.subsectorNames.textStyle.rotation = 0
            self.subsectorNames.textStyle.translation = PointF(0, -0.25)
            self.subsectorNames.textStyle.scale = SizeF(0.3, 0.15) #  Expand
            self.subsectorNames.textStyle.uppercase = True

            self.subsectorNames.textColor = self.sectorName.textColor = \
                StyleSheet._makeAlphaColor(128, MapColors.Goldenrod)

            self.microBorders.textStyle.rotation = 0
            self.microBorders.textStyle.translation = PointF(0, 0.25)
            self.microBorders.textStyle.scale = SizeF(1.0, 0.5) # Expand
            self.microBorders.textStyle.uppercase = True

            self.microBorders.pen.color = StyleSheet._makeAlphaColor(128, MapColors.TravellerRed)
            self.microRoutes.pen.width = \
                routePenWidth if self.scale < StyleSheet._CandyMaxRouteRelativeScale else routePenWidth / 2
            self.macroBorders.pen.width = \
                borderPenWidth if self.scale < StyleSheet._CandyMaxBorderRelativeScale else borderPenWidth / 4
            self.microBorders.pen.width = \
                borderPenWidth if self.scale < StyleSheet._CandyMaxBorderRelativeScale else borderPenWidth / 4

            self.worlds.textStyle.rotation = 0
            self.worlds.textStyle.scale = SizeF(1, 0.5) # Expand
            self.worlds.textStyle.translation = PointF(0, 0)
            self.worlds.textStyle.uppercase = True

            if (self.scale > StyleSheet._CandyMaxWorldRelativeScale):
                self.hexContentScale = StyleSheet._CandyMaxWorldRelativeScale / self.scale
        elif self._style is travellermap.Style.Terminal:
            self.fadeSectorSubsectorNames = False
            self.showGalaxyBackground = False
            self.lightBackground = False

            self.backgroundColor = MapColors.Black
            foregroundColor = MapColors.Cyan
            highlightColor = MapColors.White

            lightColor = MapColors.LightBlue
            darkColor = MapColors.DarkBlue
            dimColor = MapColors.DimGray

            self.subsectorGrid.pen.color = MapColors.Cyan

            fontNames = "Courier New"
            self.worlds.fontInfo.families = fontNames
            self.worlds.smallFontInfo.families = fontNames
            self.starport.fontInfo.families = fontNames
            self.worlds.largeFontInfo.families = fontNames
            self.worlds.largeFontInfo.size = self.worlds.fontInfo.size * 1.25
            self.worlds.fontInfo.size *= 0.8

            self.macroNames.fontInfo.families = fontNames
            self.macroNames.mediumFontInfo.families = fontNames
            self.macroNames.smallFontInfo.families = fontNames
            self.megaNames.fontInfo.families = fontNames
            self.megaNames.mediumFontInfo.families = fontNames
            self.megaNames.smallFontInfo.families = fontNames
            self.microBorders.smallFontInfo.families = fontNames
            self.microBorders.largeFontInfo.families = fontNames
            self.microBorders.fontInfo.families = fontNames
            self.macroBorders.fontInfo.families = fontNames
            self.macroRoutes.fontInfo.families = fontNames
            self.capitals.fontInfo.families = fontNames
            self.macroBorders.smallFontInfo.families = fontNames

            self.worlds.textStyle.uppercase = True
            self.microBorders.textStyle.uppercase = True
            self.microBorders.fontInfo.style |= FontStyle.Underline

            self.sectorName.textColor = foregroundColor
            self.sectorName.textStyle.scale = SizeF(1, 1)
            self.sectorName.textStyle.rotation = 0
            self.sectorName.textStyle.uppercase = True
            self.sectorName.fontInfo.style |= FontStyle.Bold
            self.sectorName.fontInfo.size *= 0.5

            self.subsectorNames.textColor = foregroundColor
            self.subsectorNames.textStyle.scale = SizeF(1, 1)
            self.subsectorNames.textStyle.rotation = 0
            self.subsectorNames.textStyle.uppercase = True
            self.subsectorNames.fontInfo.style |= FontStyle.Bold
            self.subsectorNames.fontInfo.size *= 0.5

            self.worlds.textStyle.uppercase = True

            self.worlds.textBackgroundStyle = TextBackgroundStyle.NoStyle

            self.subsectorNames.fontInfo.families = fontNames
            self.sectorName.fontInfo.families = fontNames

            self.worlds.largeFontInfo.style |= FontStyle.Underline

            self.microBorders.pen.width = onePixel * 4
            self.microBorders.pen.dashStyle = DashStyle.Dot

            self.worldNoWater.fillColor = foregroundColor
            self.worldWater.fillColor = '#0000FF' # TODO: Color.Empty
            self.worldWater.pen = AbstractPen(foregroundColor, onePixel * 2)

            self.amberZone.pen.color = foregroundColor
            self.amberZone.pen.width = onePixel
            self.redZone.pen.width = onePixel * 2

            self.microRoutes.pen.color = MapColors.Gray

            self.parsecGrid.pen.color = MapColors.Plum
            self.microBorders.textColor = MapColors.Cyan

            self.riftOpacity = min(self.riftOpacity, 0.30)

            self.numberAllHexes = True

            if (self.scale >= 64):
                self.subsectorNames.visible = False
        elif self._style is travellermap.Style.Mongoose:
            self.showGalaxyBackground = False
            self.lightBackground = True
            self.showGasGiantRing = True
            self.showTL = True
            self.ignoreBaseBias = True
            self.shadeMicroBorders = True

            # TODO: Need to handle moving layers
            # Re-order these elements
            #layers.MoveAfter(LayerId.Worlds_Background, LayerId.Micro_BordersStroke);
            #layers.MoveAfter(LayerId.Worlds_Foreground, LayerId.Micro_Routes);

            self.imageBorderWidth = 0.1
            self.deepBackgroundOpacity = 0

            self.backgroundColor = '#E6E7E8'
            foregroundColor = MapColors.Black
            highlightColor = MapColors.Red

            lightColor = MapColors.Black
            darkColor = MapColors.Black
            dimColor = MapColors.Gray

            self.sectorGrid.pen.color = self.subsectorGrid.pen.color = self.parsecGrid.pen.color = foregroundColor

            self.microBorders.textColor = MapColors.DarkSlateGray

            fontName = "Calibri,Arial"
            self.worlds.fontInfo.families = fontName
            self.worlds.smallFontInfo.families = fontName
            self.starport.fontInfo.families = fontName
            self.starport.fontInfo.style = FontStyle.Regular
            self.worlds.largeFontInfo.families = fontName

            self.worlds.fontInfo.style = FontStyle.Regular
            self.worlds.largeFontInfo.style = FontStyle.Bold

            self.hexNumber.fontInfo = FontInfo(self.worlds.fontInfo)
            self.hexNumber.position.y = -0.49
            self.starport.fontInfo.style = FontStyle.Italic

            self.macroNames.fontInfo.families = fontName
            self.macroNames.mediumFontInfo.families = fontName
            self.macroNames.smallFontInfo.families = fontName
            self.megaNames.fontInfo.families = fontName
            self.megaNames.mediumFontInfo.families = fontName
            self.megaNames.smallFontInfo.families = fontName
            self.microBorders.smallFontInfo.families = fontName
            self.microBorders.largeFontInfo.families = fontName
            self.microBorders.fontInfo.families = fontName
            self.macroBorders.fontInfo.families = fontName
            self.macroRoutes.fontInfo.families = fontName
            self.capitals.fontInfo.families = fontName
            self.macroBorders.smallFontInfo.families = fontName

            self.microBorders.textStyle.uppercase = True

            self.sectorName.textStyle.uppercase = True
            self.subsectorNames.textStyle.uppercase = True

            self.subsectorNames.visible = False

            self.worlds.textStyle.uppercase = True

            self.worldDetails &= ~WorldDetails.Allegiance

            self.subsectorNames.fontInfo.families = fontName
            self.sectorName.fontInfo.families = fontName

            self.microBorders.pen.width = 0.11
            self.microBorders.pen.dashStyle = DashStyle.Dot

            self.worldWater.fillColor = MapColors.MediumBlue
            self.worldNoWater.fillColor = MapColors.DarkKhaki
            self.worldWater.pen = AbstractPen(
                MapColors.DarkGray,
                onePixel * 2)
            self.worldNoWater.pen = AbstractPen(
                MapColors.DarkGray,
                onePixel * 2)

            self.showZonesAsPerimeters = True
            self.greenZone.visible = True
            self.greenZone.pen.width = self.amberZone.pen.width = self.redZone.pen.width = 0.05

            self.greenZone.pen.color = '#80C676'
            self.amberZone.pen.color = '#FBB040'
            self.redZone.pen.color = MapColors.Red

            self.microBorders.textColor = MapColors.DarkSlateGray

            self.riftOpacity = min(self.riftOpacity, 0.30)

            self.discRadius = 0.11
            self.gasGiantPosition = PointF(0, -0.23)
            self.baseTopPosition = PointF(-0.22, -0.21)
            self.baseMiddlePosition = PointF(-0.32, 0.17)
            self.baseBottomPosition = PointF(0.22, -0.21)
            self.starport.position = PointF(0.175, 0.17)
            self.uwp.position = PointF(0, 0.40)
            self.discPosition = PointF(-self.discRadius, 0.16)
            self.worlds.textStyle.translation = PointF(0, -0.04)

            self.worlds.textBackgroundStyle = TextBackgroundStyle.NoStyle

            self.uwp.fontInfo = FontInfo(self.hexNumber.fontInfo)
            self.uwp.fillColor = MapColors.Black
            self.uwp.textColor = MapColors.White
            self.uwp.textBackgroundStyle = TextBackgroundStyle.Filled

        # NOTE: This TODO came in with traveller map
        # TODO: Do this with opacity.
        if fadeSectorSubsectorNames:
            if self.scale < 16:
                self.sectorName.textColor = foregroundColor
                self.subsectorNames.textColor = foregroundColor
            elif self.scale < 48:
                self.sectorName.textColor = darkColor
                self.subsectorNames.textColor = darkColor
            else:
                self.sectorName.textColor = dimColor
                self.subsectorNames.textColor = dimColor

        # Base element colors on foreground/light/dim/dark/highlight, if not specified by style.
        if not self.pseudoRandomStars.fillColor:
            self.pseudoRandomStars.fillColor = foregroundColor

        if not self.droyneWorlds.textColor:
            self.droyneWorlds.textColor = self.microBorders.textColor
        if not self.minorHomeWorlds.textColor:
            self.minorHomeWorlds.textColor = self.microBorders.textColor
        if not self.ancientsWorlds.textColor:
            self.ancientsWorlds.textColor = self.microBorders.textColor


        if not self.megaNames.textColor:
            self.megaNames.textColor = foregroundColor
        if not self.megaNames.textHighlightColor:
            self.megaNames.textHighlightColor = highlightColor

        if not self.macroNames.textColor:
            self.macroNames.textColor = foregroundColor
        if not self.macroNames.textHighlightColor:
            self.macroNames.textHighlightColor = highlightColor

        if not self.macroRoutes.textColor:
            self.macroRoutes.textColor = foregroundColor
        if not self.macroRoutes.textHighlightColor:
            self.macroRoutes.textHighlightColor = highlightColor

        if not self.worlds.textColor:
            self.worlds.textColor = foregroundColor
        if not self.worlds.textHighlightColor:
            self.worlds.textHighlightColor = highlightColor

        if not self.hexNumber.textColor:
            self.hexNumber.textColor = lightColor
        if not self.uwp.textColor:
            self.uwp.textColor = foregroundColor

        if not self.placeholder.textColor:
            self.placeholder.textColor = foregroundColor
        if not self.anomaly.textColor:
            self.anomaly.textColor = highlightColor

        if not self.imageBorderColor:
            self.imageBorderColor = lightColor

        # Convert list into a id -> index mapping.
        self.layerOrder.clear()
        for i, layer in enumerate(layers):
            self.layerOrder[layer] = i


        # TODO: Delete the hacky stuff below
        self.numberAllHexes = True

    @staticmethod
    def _floatScaleInterpolate(
            minValue: float,
            maxValue: float,
            scale: float,
            minScale: float,
            maxScale: float
            ) -> float:
        if scale <= minScale:
            return minValue
        if scale >= maxScale:
            return maxValue

        logscale = math.log(scale, 2.0)
        logmin = math.log(minScale, 2.0)
        logmax = math.log(maxScale, 2.0)
        p = (logscale - logmin) / (logmax - logmin)
        value = minValue + (maxValue - minValue) * p
        return value

    @staticmethod
    def _colorScaleInterpolate(
            scale: float,
            minScale: float,
            maxScale: float,
            color: str
            ) -> str:
        alpha = StyleSheet._floatScaleInterpolate(
            minValue=0,
            maxValue=255,
            scale=scale,
            minScale=minScale,
            maxScale=maxScale)
        return StyleSheet._makeAlphaColor(
            alpha=alpha,
            color=color)

    def _makeAlphaColor(
            alpha: typing.Union[float, int],
            color: str
            ) -> str:
        length = len(color)
        if (length != 7 and length != 9) or color[0] != '#':
            raise ValueError(f'Invalid color "#{color}"')

        alpha = int(alpha)
        if alpha < 0:
            alpha = 0
        if alpha > 255:
            alpha =255

        return f'#{alpha:02X}{color[1 if length == 7 else 3:]}'

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

# TODO: This is drawString from RenderUtils
def drawStringHelper(
        graphics: AbstractGraphics,
        text: str,
        font: AbstractFont,
        brush: AbstractBrush,
        x: float,
        y: float,
        format: TextFormat = TextFormat.Center
        ) -> None:
    if not text:
        return

    lines = text.split('\n')
    sizes = [graphics.measureString(line, font) for line in lines]

    # TODO: This needs updated to not use QT
    qtFont = font.font
    qtFontMetrics = QtGui.QFontMetrics(qtFont)

    # TODO: Not sure how to calculate this
    #fontUnitsToWorldUnits = qtFont.pointSize() / font.FontFamily.GetEmHeight(font.Style)
    fontUnitsToWorldUnits = font.emSize / qtFont.pointSize()
    lineSpacing = qtFontMetrics.lineSpacing() * fontUnitsToWorldUnits
    ascent = qtFontMetrics.ascent() * fontUnitsToWorldUnits
    # NOTE: This was commented out in the Traveller Map source code
    #float descent = font.FontFamily.GetCellDescent(font.Style) * fontUnitsToWorldUnits;

    maxWidthRect = max(sizes, key=lambda rect: rect.width)
    boundingSize = SizeF(width=maxWidthRect.width, height=lineSpacing * len(sizes))

    # Offset from baseline to top-left.
    y += lineSpacing / 2

    widthFactor = 0
    if format == TextFormat.MiddleLeft or \
        format == TextFormat.Center or \
        format == TextFormat.MiddleRight:
        y -= boundingSize.height / 2
    elif format == TextFormat.BottomLeft or \
        format == TextFormat.BottomCenter or \
        format == TextFormat.BottomRight:
        y -= boundingSize.height

    if format == TextFormat.TopCenter or \
        format == TextFormat.Center or \
        format == TextFormat.BottomCenter:
            widthFactor = -0.5
    elif format == TextFormat.TopRight or \
        format == TextFormat.MiddleRight or \
        format == TextFormat.BottomRight:
            widthFactor = -1

    for line, size in zip(lines, sizes):
        graphics.drawString(
            text=line,
            font=font,
            brush=brush,
            x=x + widthFactor * size.width + size.width / 2,
            y=y,
            format=StringAlignment.Centered)
        y += lineSpacing

class RenderContext(object):
    class BorderLayer(enum.Enum):
        Fill = 0
        Shade = 1
        Stroke = 2
        Regions = 3

    _HexEdge = math.tan(math.pi / 6) / 4 / travellermap.ParsecScaleX

    _GalaxyImageRect = RectangleF(-18257, -26234, 36551, 32462) # Chosen to match T5 pp.416
    _RiftImageRect = RectangleF(-1374, -827, 2769, 1754)

    _PseudoRandomStarsChunkSize = 256
    _PseudoRandomStarsMaxPerChunk = 800

    def __init__(
            self,
            graphics: AbstractGraphics,
            tileRect: RectangleF, # Region to render in map coordinates
            tileSize: Size, # Pixel size of view to render to
            scale: float,
            styles: StyleSheet,
            imageCache: ImageCache,
            vectorCache: VectorObjectCache,
            labelCache: MapLabelCache,
            options: MapOptions
            ) -> None:
        self._graphics = graphics
        self._tileRect = tileRect
        self._scale = scale
        self._options = options
        self._styles = styles
        self._imageCache = imageCache
        self._vectorCache = vectorCache
        self._labelCache = labelCache
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

    def pixelSpaceToWorldSpace(self, pixel: Point, clamp: bool = True) -> PointF:
        world = self._worldSpaceToImageSpace.transform(pixel)

        if clamp:
            x = round(world.x + 0.5)
            y = round(world.y + (0.5 if x % 2 == 0 else 0))
            world = PointF(x, y)

        return world

    def render(self) -> None:
        with self._graphics.save():
            # Overall, rendering is all in world-space; individual steps may transform back
            # to image-space as needed.
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
            LayerAction(LayerId.Background_Solid, self._drawBackground, clip=True),

            # NOTE: Since alpha texture brushes aren't supported without
            # creating a new image (slow!) we render the local background
            # first, then overlay the deep background over it, for
            # basically the same effect since the alphas sum to 1.
            LayerAction(LayerId.Background_NebulaTexture, self._drawNebulaBackground, clip=True),
            LayerAction(LayerId.Background_Galaxy, self._drawGalaxyBackground, clip=True),

            LayerAction(LayerId.Background_PseudoRandomStars, self._drawPseudoRandomStars, clip=True),
            LayerAction(LayerId.Background_Rifts, self._drawRifts, clip=True),

            #------------------------------------------------------------
            # Foreground
            #------------------------------------------------------------
            LayerAction(LayerId.Macro_Borders, self._drawMacroBorders, clip=True),
            LayerAction(LayerId.Macro_Routes, self._drawMacroRoutes, clip=True),

            LayerAction(LayerId.Grid_Sector, self._drawSectorGrid, clip=True),
            LayerAction(LayerId.Grid_Subsector, self._drawSubsectorGrid, clip=True),
            LayerAction(LayerId.Grid_Parsec, self._drawParsecGrid, clip=True),

            LayerAction(LayerId.Names_Subsector, self._drawSubsectorNames, clip=True),

            LayerAction(LayerId.Micro_BordersFill, self._drawMicroBordersFill, clip=True),
            LayerAction(LayerId.Micro_BordersShade, self._drawMicroBordersShade, clip=True),
            LayerAction(LayerId.Micro_BordersStroke, self._drawMicroBordersStroke, clip=True),
            LayerAction(LayerId.Micro_Routes, self._drawMicroRoutes, clip=True),
            LayerAction(LayerId.Micro_BorderExplicitLabels, self._drawMicroLabels, clip=True),

            LayerAction(LayerId.Names_Sector, self._drawSectorNames, clip=True),
            LayerAction(LayerId.Macro_GovernmentRiftRouteNames, self._drawMacroNames, clip=True),
            LayerAction(LayerId.Macro_CapitalsAndHomeWorlds, self._drawCapitalsAndHomeWorlds, clip=True),
            LayerAction(LayerId.Mega_GalaxyScaleLabels, self._drawMegaLabels, clip=True),

            LayerAction(LayerId.Worlds_Background, self._drawWorldsBackground, clip=True),

            # Not clipped, so names are not clipped in jumpmaps.
            LayerAction(LayerId.Worlds_Foreground, self._drawWorldsForeground, clip=False),

            LayerAction(LayerId.Worlds_Overlays, self._drawWorldsOverlay, clip=True),

            #------------------------------------------------------------
            # Overlays
            #------------------------------------------------------------
            LayerAction(LayerId.Overlay_DroyneChirperWorlds, self._drawDroyneOverlay, clip=True),
            LayerAction(LayerId.Overlay_MinorHomeworlds, self._drawMinorHomeworldOverlay, clip=True),
            LayerAction(LayerId.Overlay_AncientsWorlds, self._drawAncientWorldsOverlay, clip=True),
            LayerAction(LayerId.Overlay_ReviewStatus, self._drawSectorReviewStatusOverlay, clip=True),
        ]

        self._layers.sort(key=lambda l: self._styles.layerOrder[l.id])

    # TODO: I'm not sure about the use of the term world space
    # here. It comes from traveller map but as far as I can tell
    # it's actually dealing with map space
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

    # TODO: When zooming in and out the background doesn't stay in a consistent
    # place between zoom levels. I think traveller map technically has the same
    # issue but it's nowhere near as noticeable as it only actually renders
    # tiles at a few zoom levels then uses digital zoom in the browser to scale
    # between those levels. The result being it doesn't jump around every zoom
    # step, it still does it at some zoom levels but it's far less noticeable.
    # I suspect I could do something in this function that effectively mimics
    # this behaviour
    def _drawNebulaBackground(self) -> None:
        if not self._styles.showNebulaBackground:
            return

        # Render in image-space so it scales/tiles nicely
        with self._graphics.save():
            self._graphics.multiplyTransform(self._worldSpaceToImageSpace)

            backgroundImageScale = 2.0
            nebulaImageWidth = 1024
            nebulaImageHeight = 1024
            # Scaled size of the background
            w = nebulaImageWidth * backgroundImageScale
            h = nebulaImageHeight * backgroundImageScale

            # Offset of the background, relative to the canvas
            ox = (-self._tileRect.left * self._scale * travellermap.ParsecScaleX) % w
            oy = (-self._tileRect.top * self._scale * travellermap.ParsecScaleY) % h
            if (ox > 0):
                ox -= w
            if (oy > 0):
                oy -= h

            # Number of copies needed to cover the canvas
            nx = 1 + int(math.floor(self._tileSize.width / w))
            ny = 1 + int(math.floor(self._tileSize.height / h))
            if (ox + nx * w < self._tileSize.width):
                nx += 1
            if (oy + ny * h < self._tileSize.height):
                ny += 1

            imageRect = RectangleF(x=ox, y=oy, width=w + 1, height=h + 1)
            for _ in range(nx):
                imageRect.y=oy
                for _ in range(ny):
                    self._graphics.drawImage(
                        self._imageCache.nebulaImage,
                        imageRect)
                    imageRect.y += h
                imageRect.x += w

    def _drawGalaxyBackground(self) -> None:
        if not self._styles.showGalaxyBackground:
            return

        if self._styles.deepBackgroundOpacity > 0 and \
            RenderContext._GalaxyImageRect.intersectsWith(self._tileRect):
            galaxyImage = self._imageCache.galaxyImageGray if self._styles.lightBackground else self._imageCache.galaxyImage
            self._graphics.drawImageAlpha(
                self._styles.deepBackgroundOpacity,
                galaxyImage,
                RenderContext._GalaxyImageRect)

    # NOTE: How this is implemented differs from the Traveller Map implementation
    # as Traveller Map achieves consistent random star positioning by seeding the
    # rng by the tile origin. As the web interface always chunks the universe into
    # tiles with the same origins this means, for a given tile, the random stars
    # will always be in the same place.
    # This approach doesn't work for me as I'm not using tiles in that way. I'm
    # drawing a single tile where the origin will vary depending on where the
    # current viewport is. To achieve a similar effect I'm chunking the random
    # stars by sector. The downside of this is you always have to draw process
    # all stars for all sectors overlapped by the viewport
    def _drawPseudoRandomStars(self) -> None:
        if not self._styles.pseudoRandomStars.visible:
            return

        startX = math.floor(self._tileRect.left / RenderContext._PseudoRandomStarsChunkSize) * \
            RenderContext._PseudoRandomStarsChunkSize
        startY = math.floor(self._tileRect.top / RenderContext._PseudoRandomStarsChunkSize) * \
            RenderContext._PseudoRandomStarsChunkSize
        finishX = math.ceil(self._tileRect.right / RenderContext._PseudoRandomStarsChunkSize) * \
            RenderContext._PseudoRandomStarsChunkSize
        finishY = math.ceil(self._tileRect.bottom / RenderContext._PseudoRandomStarsChunkSize) * \
            RenderContext._PseudoRandomStarsChunkSize

        brush = AbstractBrush(self._styles.pseudoRandomStars.fillColor)
        with self._graphics.save():
            self._graphics.setSmoothingMode(AbstractGraphics.SmoothingMode.HighQuality)

            for chunkLeft in range(startX, finishX + 1, RenderContext._PseudoRandomStarsChunkSize):
                for chunkTop in range(startY, finishY + 1, RenderContext._PseudoRandomStarsChunkSize):
                    rand = random.Random((chunkLeft << 8) ^ chunkTop)

                    starCount =  \
                        RenderContext._PseudoRandomStarsMaxPerChunk \
                        if self._scale >= 1 else \
                        int(RenderContext._PseudoRandomStarsMaxPerChunk / self._scale)

                    for _ in range(starCount):
                        starX = rand.random() * RenderContext._PseudoRandomStarsChunkSize + chunkLeft
                        starY = rand.random() * RenderContext._PseudoRandomStarsChunkSize + chunkTop
                        d = rand.random() * 2

                        self._graphics.drawEllipse(
                            pen=None,
                            brush=brush,
                            rect=RectangleF(
                                x=starX,
                                y=starY,
                                width=(d / self._scale * travellermap.ParsecScaleX),
                                height=(d / self._scale * travellermap.ParsecScaleY)))

    def _drawRifts(self) -> None:
        if not self._styles.showRiftOverlay:
            return

        if self._styles.riftOpacity > 0 and \
            RenderContext._RiftImageRect.intersectsWith(self._tileRect):
            self._graphics.drawImageAlpha(
                alpha=self._styles.riftOpacity,
                image=self._imageCache.riftImage,
                rect=self._RiftImageRect)

    def _drawMacroBorders(self) -> None:
        if not self._styles.macroBorders.visible:
            return

        self._graphics.setSmoothingMode(AbstractGraphics.SmoothingMode.AntiAlias)
        for vector in self._vectorCache.borders:
            if (vector.mapOptions & self._options & MapOptions.BordersMask) != 0:
                vector.draw(
                    graphics=self._graphics,
                    rect=self._tileRect,
                    pen=self._styles.macroBorders.pen)

    def _drawMacroRoutes(self) -> None:
        if not self._styles.macroRoutes.visible:
            return

        self._graphics.setSmoothingMode(AbstractGraphics.SmoothingMode.AntiAlias)
        for vector in self._vectorCache.routes:
            if (vector.mapOptions & self._options & MapOptions.BordersMask) != 0:
                vector.draw(
                    graphics=self._graphics,
                    rect=self._tileRect,
                    pen=self._styles.macroRoutes.pen)

    def _drawSectorGrid(self) -> None:
        if not self._styles.sectorGrid.visible:
            return

        self._graphics.setSmoothingMode(AbstractGraphics.SmoothingMode.HighSpeed)

        h = ((math.floor((self._tileRect.left) / travellermap.SectorWidth) - 1) - travellermap.ReferenceSectorX) * \
            travellermap.SectorWidth - travellermap.ReferenceHexX
        gridSlop = 10
        while h <= (self._tileRect.right + travellermap.SectorWidth):
            with self._graphics.save():
                self._graphics.translateTransform(dx=h, dy=0)
                self._graphics.scaleTransform(
                    scaleX=1 / travellermap.ParsecScaleX,
                    scaleY=1 / travellermap.ParsecScaleY)
                self._graphics.drawLine(
                    pen=self._styles.sectorGrid.pen,
                    pt1=PointF(0, self._tileRect.top - gridSlop),
                    pt2=PointF(0, self._tileRect.bottom + gridSlop))
            h += travellermap.SectorWidth

        v = ((math.floor((self._tileRect.top) / travellermap.SectorHeight) - 1) - travellermap.ReferenceSectorY) * \
            travellermap.SectorHeight - travellermap.ReferenceHexY
        while v <= (self._tileRect.bottom + travellermap.SectorHeight):
            self._graphics.drawLine(
                pen=self._styles.sectorGrid.pen,
                pt1=PointF(self._tileRect.left - gridSlop, v),
                pt2=PointF(self._tileRect.right + gridSlop, v))
            v += travellermap.SectorHeight

    def _drawSubsectorGrid(self) -> None:
        if not self._styles.subsectorGrid.visible:
            return

        self._graphics.setSmoothingMode(AbstractGraphics.SmoothingMode.HighSpeed)

        hmin = int(math.floor(self._tileRect.left / travellermap.SubsectorWidth) - 1 -
                   travellermap.ReferenceSectorX)
        hmax = int(math.ceil((self._tileRect.right + travellermap.SubsectorWidth +
                              travellermap.ReferenceHexX) / travellermap.SubsectorWidth))
        gridSlop = 10
        for hi in range(hmin, hmax + 1):
            if (hi % 4) == 0:
                continue
            h = hi * travellermap.SubsectorWidth - travellermap.ReferenceHexX
            self._graphics.drawLine(
                pen=self._styles.subsectorGrid.pen,
                pt1=PointF(h, self._tileRect.top - gridSlop),
                pt2=PointF(h, self._tileRect.bottom + gridSlop))
            with self._graphics.save():
                self._graphics.translateTransform(dx=h, dy=0)
                self._graphics.scaleTransform(
                    scaleX=1 / travellermap.ParsecScaleX,
                    scaleY=1 / travellermap.ParsecScaleY)
                self._graphics.drawLine(
                    pen=self._styles.subsectorGrid.pen,
                    pt1=PointF(0, self._tileRect.top - gridSlop),
                    pt2=PointF(0, self._tileRect.bottom + gridSlop))

        vmin = int(math.floor(self._tileRect.top / travellermap.SubsectorHeight) - 1 -
                   travellermap.ReferenceSectorY)
        vmax = int(math.ceil((self._tileRect.bottom + travellermap.SubsectorHeight +
                              travellermap.ReferenceHexY) / travellermap.SubsectorHeight))
        for vi in range(vmin, vmax + 1):
            if (vi % 4) == 0:
                continue
            v = vi * travellermap.SubsectorHeight - travellermap.ReferenceHexY
            self._graphics.drawLine(
                pen=self._styles.subsectorGrid.pen,
                pt1=PointF(self._tileRect.left - gridSlop, v),
                pt2=PointF(self._tileRect.right + gridSlop, v))

    def _drawParsecGrid(self) -> None:
        if not self._styles.parsecGrid.visible:
            return

        self._graphics.setSmoothingMode(AbstractGraphics.SmoothingMode.HighQuality)

        # TODO: Remove debug drawing code
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

        if self._styles.numberAllHexes and (self._styles.worldDetails & WorldDetails.Hex) != 0:
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

    def _drawSubsectorNames(self) -> None:
        if not self._styles.subsectorNames.visible:
            return

        not self._graphics.setSmoothingMode(AbstractGraphics.SmoothingMode.HighQuality)
        brush = AbstractBrush(self._styles.subsectorNames.textColor)
        # TODO: Finish this off when I add world loading
        """
        foreach (Sector sector in selector.Sectors)
        {
            for (int i = 0; i < 16; i++)
            {
                Subsector ss = sector.Subsector(i);
                if (ss == null || string.IsNullOrEmpty(ss.Name))
                    continue;

                Point center = sector.SubsectorCenter(i);
                RenderUtil.DrawLabel(graphics, ss.Name, center, styles.subsectorNames.Font, brush, styles.subsectorNames.textStyle);
            }
        }
        """

    def _drawMicroBordersFill(self) -> None:
        if not self._styles.microBorders.visible:
            return

        self._drawMicroBorders(RenderContext.BorderLayer.Regions)

        if self._styles.fillMicroBorders:
            self._drawMicroBorders(RenderContext.BorderLayer.Fill)

    def _drawMicroBordersShade(self) -> None:
        if not self._styles.microBorders.visible or not self._styles.shadeMicroBorders:
            return

        self._drawMicroBorders(RenderContext.BorderLayer.Shade)

    def _drawMicroBordersStroke(self) -> None:
        if not self._styles.microBorders.visible:
            return

        self._drawMicroBorders(RenderContext.BorderLayer.Stroke)

    def _drawMicroRoutes(self) -> None:
        # TODO: Implement when I add loading worlds
        pass

    def _drawMicroLabels(self) -> None:
        # TODO: Implement when I add loading worlds
        pass

    def _drawSectorNames(self) -> None:
        # TODO: Implement when I add loading worlds
        pass

    def _drawMacroNames(self) -> None:
        if  not self._styles.macroNames.visible:
            return

        self._graphics.setSmoothingMode(AbstractGraphics.SmoothingMode.HighQuality)

        for vec in self._vectorCache.borders:
            if (vec.mapOptions & self._options & MapOptions.NamesMask) == 0:
                continue
            major = (vec.mapOptions & MapOptions.NamesMajor) != 0
            labelStyle = LabelStyle(uppercase=major)
            font = \
                self._styles.macroNames.font \
                if major else \
                self._styles.macroNames.smallFont
            solidBrush = AbstractBrush(self._styles.macroNames.textColor
                                       if major else
                                       self._styles.macroNames.textHighlightColor)
            vec.drawName(
                graphics=self._graphics,
                rect=self._tileRect,
                font=font,
                textBrush=solidBrush,
                labelStyle=labelStyle)

        for vec in self._vectorCache.rifts:
            major = (vec.mapOptions & MapOptions.NamesMajor) != 0
            labelStyle = LabelStyle(rotation=35, uppercase=major)
            font = \
                self._styles.macroNames.font \
                if major else \
                self._styles.macroNames.smallFont
            solidBrush = AbstractBrush(self._styles.macroNames.textColor
                                       if major else
                                       self._styles.macroNames.textHighlightColor)
            vec.drawName(
                graphics=self._graphics,
                rect=self._tileRect,
                font=font,
                textBrush=solidBrush,
                labelStyle=labelStyle)

        if self._styles.macroRoutes.visible:
            for vec in self._vectorCache.routes:
                if (vec.mapOptions & self._options & MapOptions.NamesMask) == 0:
                    continue
                major = (vec.mapOptions & MapOptions.NamesMajor) != 0
                labelStyle = LabelStyle(uppercase=major)
                font = \
                    self._styles.macroNames.font \
                    if major else \
                    self._styles.macroNames.smallFont
                solidBrush = AbstractBrush(self._styles.macroRoutes.textColor
                                           if major else
                                           self._styles.macroRoutes.textHighlightColor)
                vec.drawName(
                    graphics=self._graphics,
                    rect=self._tileRect,
                    font=font,
                    textBrush=solidBrush,
                    labelStyle=labelStyle)

        if (self._options & MapOptions.NamesMinor) != 0:
            for label in self._labelCache.minorLabels:
                font = self._styles.macroNames.smallFont if label.minor else self._styles.macroNames.mediumFont
                solidBrush = AbstractBrush(self._styles.macroRoutes.textColor
                                           if label.minor else
                                           self._styles.macroRoutes.textHighlightColor)
                with self._graphics.save():
                    self._graphics.translateTransform(
                        dx=label.position.x,
                        dy=label.position.y)
                    self._graphics.scaleTransform(
                        scaleX=1.0 / travellermap.ParsecScaleX,
                        scaleY=1.0 / travellermap.ParsecScaleY)
                    drawStringHelper(
                        graphics=self._graphics,
                        text=label.text,
                        font=font,
                        brush=solidBrush,
                        x=0, y=0)

    def _drawCapitalsAndHomeWorlds(self) -> None:
        # TODO: Need to add worlds and loading of ~/res/labels/Worlds.xml
        pass

    def _drawMegaLabels(self) -> None:
        if not self._styles.megaNames.visible:
            return

        self._graphics.setSmoothingMode(AbstractGraphics.SmoothingMode.HighQuality)
        solidBrush = AbstractBrush(self._styles.megaNames.textColor)
        for label in self._labelCache.megaLabels:
            with self._graphics.save():
                font = self._styles.megaNames.smallFont if label.minor else self._styles.megaNames.font
                self._graphics.translateTransform(
                    dx=label.position.x,
                    dy=label.position.y)
                self._graphics.scaleTransform(
                    scaleX=1.0 / travellermap.ParsecScaleX,
                    scaleY=1.0 / travellermap.ParsecScaleY)
                drawStringHelper(
                    graphics=self._graphics,
                    text=label.text,
                    font=font,
                    brush=solidBrush,
                    x=0, y=0)

    def _drawWorldsBackground(self) -> None:
        # TODO: Implement when I add loading worlds
        pass

    def _drawWorldsForeground(self) -> None:
        # TODO: Implement when I add loading worlds
        pass

    def _drawWorldsOverlay(self) -> None:
        # TODO: Implement when I add loading worlds
        pass

    def _drawDroyneOverlay(self) -> None:
        # TODO: Implement when I add loading worlds
        pass

    def _drawMinorHomeworldOverlay(self) -> None:
        # TODO: Implement when I add loading worlds
        pass

    def _drawAncientWorldsOverlay(self) -> None:
        # TODO: Implement when I add loading worlds
        pass

    def _drawSectorReviewStatusOverlay(self) -> None:
        # TODO: Implement when I add loading worlds
        pass

    def _drawMicroBorders(self, layer: BorderLayer) -> None:
        # TODO: Implement when I add loading worlds
        pass

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

        # Highest quality by default
        self._painter.setRenderHint(
            QtGui.QPainter.RenderHint.Antialiasing,
            True)
        self._painter.setRenderHint(
            QtGui.QPainter.RenderHint.TextAntialiasing,
            True)
        self._painter.setRenderHint(
            QtGui.QPainter.RenderHint.SmoothPixmapTransform,
            True)
        self._painter.setRenderHint(
            QtGui.QPainter.RenderHint.LosslessImageRendering,
            True)

    def setSmoothingMode(self, mode: AbstractGraphics.SmoothingMode):
        super().setSmoothingMode(mode)

        antialias = mode == AbstractGraphics.SmoothingMode.HighQuality or \
            mode == AbstractGraphics.SmoothingMode.AntiAlias

        self._painter.setRenderHint(
            QtGui.QPainter.RenderHint.Antialiasing,
            antialias)
        self._painter.setRenderHint(
            QtGui.QPainter.RenderHint.TextAntialiasing,
            antialias)
        self._painter.setRenderHint(
            QtGui.QPainter.RenderHint.SmoothPixmapTransform,
            antialias)

    def scaleTransform(self, scaleX: float, scaleY: float) -> None:
        transform = QtGui.QTransform()
        transform.scale(scaleX, scaleY)
        self._painter.setTransform(
            transform * self._painter.transform())
    def translateTransform(self, dx: float, dy: float) -> None:
        transform = QtGui.QTransform()
        transform.translate(dx, dy)
        self._painter.setTransform(
            transform * self._painter.transform())
    def rotateTransform(self, degrees: float) -> None:
        transform = QtGui.QTransform()
        transform.rotate(degrees, QtCore.Qt.Axis.ZAxis)
        self._painter.setTransform(
            transform * self._painter.transform())
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
        self._painter.drawLine(
            self._convertPoint(pt1),
            self._convertPoint(pt2))

    def drawLines(self, pen: AbstractPen, points: typing.Sequence[PointF]):
        self._painter.setPen(self._convertPen(pen))
        self._painter.drawPolyline(self._convertPoints(points))

    # TODO: I don't know if a path is a segmented line or a closed polygon
    # TODO: This was an overload of drawPath in the traveller map code
    def drawPathOutline(self, pen: AbstractPen, path: AbstractPath):
        self._painter.setPen(self._convertPen(pen))
        self._painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        if path.closed:
            self._painter.drawPolygon(self._convertPath(path))
        else:
            self._painter.drawPolyline(self._convertPoints(path.points))
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
        self._painter.setPen(self._convertPen(pen) if pen else QtCore.Qt.PenStyle.NoPen)
        self._painter.setBrush(self._convertBrush(brush) if brush else QtCore.Qt.BrushStyle.NoBrush)
        self._painter.drawEllipse(self._convertRect(rect))
    def drawArc(self, pen: AbstractPen, rect: RectangleF, startAngle: float, sweepAngle: float) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawArc')

    def drawImage(self, image: AbstractImage, rect: RectangleF) -> None:
        self._painter.drawImage(
            self._convertRect(rect),
            image.image)
    def drawImageAlpha(self, alpha: float, image: AbstractImage, rect: RectangleF) -> None:
        oldAlpha = self._painter.opacity()
        self._painter.setOpacity(alpha)
        try:
            self._painter.drawImage(
                self._convertRect(rect),
                image.image)
        finally:
            self._painter.setOpacity(oldAlpha)

    def measureString(self, text: str, font: AbstractFont) -> SizeF:
        qtFont = self._convertFont(font)
        scale = font.emSize / qtFont.pointSize()

        fontMetrics = QtGui.QFontMetrics(qtFont)
        contentPixelRect = fontMetrics.tightBoundingRect(text)
        contentPixelRect.moveTo(0, 0)

        return SizeF(contentPixelRect.width() * scale, contentPixelRect.height() * scale)

    def drawString(
            self,
            text: str,
            font: AbstractFont,
            brush: AbstractBrush,
            x: float, y: float,
            format: StringAlignment
            ) -> None:
        # TODO: I've found that to get text sizes to match Traveller Map I need
        # to scale the emSize
        emSize = font.emSize * 0.85
        qtFont = self._convertFont(font)
        scale = emSize / qtFont.pointSize()

        self._painter.setFont(qtFont)
        # TODO: It looks like Qt uses a pen for text rather than the brush
        # it may make more sense for it to just be a colour that is passed
        # to drawString
        self._painter.setPen(QtGui.QColor(brush.color))
        self._painter.setBrush(self._convertBrush(brush))

        fontMetrics = QtGui.QFontMetrics(qtFont)
        contentPixelRect = fontMetrics.tightBoundingRect(text)
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

    def _convertPoint(self, point: PointF) -> QtCore.QPointF:
        return QtCore.QPointF(point.x, point.y)

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

    def _convertPath(self, path: AbstractPath) -> QtGui.QPolygonF:
        return QtGui.QPolygonF(self._convertPoints(path.points))

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

        self._viewCenterMapPos = PointF(0, 0) # TODO: I think this is actually in world/absolute coordinates
        self._tileSize = Size(self.width(), self.height())
        #self._scale = MapHackView._DefaultScale
        self._scale = 64
        self._options = \
            MapOptions.SectorGrid | MapOptions.SubsectorGrid | MapOptions.SectorsSelected | MapOptions.SectorsAll | \
            MapOptions.BordersMajor | MapOptions.BordersMinor | MapOptions.NamesMajor | MapOptions.NamesMinor | \
            MapOptions.WorldsCapitals | MapOptions.WorldsHomeworlds | MapOptions.RoutesSelectedDeprecated | \
            MapOptions.PrintStyleDeprecated | MapOptions.CandyStyleDeprecated | MapOptions.ForceHexes | \
            MapOptions.WorldColors | MapOptions.FilledBorders
        self._style = travellermap.Style.Poster
        #self._style = travellermap.Style.Candy
        self._graphics = QtGraphics()
        self._imageCache = ImageCache(basePath='./data/map/')
        self._vectorCache = VectorObjectCache(basePath='./data/map/')
        self._labelCache = MapLabelCache(basePath='./data/map/')
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

            # TODO: This is borked, need to figure out how to convert a float world space coordinate
            # to an int absolute coordinate
            absCursor = self._renderer.pixelSpaceToWorldSpace(pixel=Point(event.x(), event.y()))
            relCursor = travellermap.absoluteSpaceToRelativeSpace((absCursor.x, absCursor.y))
            print(f'ABS: {absCursor.x} {absCursor.y} HEX:{relCursor[2]} {relCursor[3]}')

    # TODO: There is an issue with the drag move where the point you start the
    # drag on isn't staying under the cursor
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
            oldCursorMapPos = self._renderer.pixelSpaceToWorldSpace(PointF(
                cursorScreenPos.x(),
                cursorScreenPos.y()),
                clamp=False) # Float value for extra accuracy

            if event.angleDelta().y() > 0:
                self._scale *= MapHackView._WheelScaleMultiplier
            else:
                self._scale /= MapHackView._WheelScaleMultiplier
            self._renderer = self._createRender()

            newCursorMapPos = self._renderer.pixelSpaceToWorldSpace(PointF(
                cursorScreenPos.x(),
                cursorScreenPos.y()),
                clamp=False)

            self._viewCenterMapPos.x += oldCursorMapPos.x - newCursorMapPos.x
            self._viewCenterMapPos.y += oldCursorMapPos.y - newCursorMapPos.y

            self._renderer.setTileRect(
                rect=self._calculateTileRect())

            self.repaint()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        if not self._graphics or not self._renderer:
            return super().paintEvent(event)

        # TODO: Remove debug timer
        with common.DebugTimer('Draw Time'):
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
            styles=StyleSheet(
                scale=self._scale,
                options=self._options,
                style=self._style),
            imageCache=self._imageCache,
            vectorCache=self._vectorCache,
            labelCache=self._labelCache,
            options=self._options)

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
