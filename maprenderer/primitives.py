from PyQt5 import QtGui # TODO: Get rid of the need for this include
import enum
import math
import numpy
import typing

class TextAlignment(enum.Enum):
    Baseline = 0
    Centered = 1
    TopLeft = 2
    TopCenter = 3
    TopRight = 4
    MiddleLeft = 5
    MiddleRight = 6
    BottomLeft = 7
    BottomCenter = 8
    BottomRight = 9

class LineStyle(enum.Enum):
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

    # These were added by me. In the Traveller Map code these come from
    # separate URL parameters rather than part of the map options

    PopulationOverlay = 0x10000
    ImportanceOverlay = 0x20000
    CapitalOverlay = 0x40000
    StellarOverlay = 0x80000

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

class AbstractSizeF(object):
    @typing.overload
    def __init__(self) -> None: ...
    @typing.overload
    def __init__(self, other: 'AbstractSizeF') -> None: ...
    @typing.overload
    def __init__(self, width: float, height: float) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        if not args and not kwargs:
            self._width = self._height = 0
        elif len(args) + len(kwargs) == 1:
            other = args[0] if len(args) > 0 else kwargs['other']
            if not isinstance(other, AbstractSizeF):
                raise TypeError('The other parameter must be a SizeF')
            self._width = other._width
            self._height = other._height
        else:
            self._width = float(args[0] if len(args) > 0 else kwargs['width'])
            self._height = float(args[1] if len(args) > 1 else kwargs['height'])

    def __eq__(self, other: typing.Any) -> bool:
        if isinstance(other, AbstractSizeF):
            return self._width == other._width and self._height == other._height
        return super().__eq__(other)

    def width(self) -> int:
        return self._width

    def setWidth(self, width: float) -> None:
        self._width = width

    def height(self) -> int:
        return self._height

    def setHeight(self, height: float) -> None:
        self._height = height

class AbstractPointF(object):
    @typing.overload
    def __init__(self) -> None: ...
    @typing.overload
    def __init__(self, other: 'AbstractPointF') -> None: ...
    @typing.overload
    def __init__(self, x: float, y: float) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        if not args and not kwargs:
            self._x = self._y = 0
        elif len(args) + len(kwargs) == 1:
            other = args[0] if len(args) > 0 else kwargs['other']
            if not isinstance(other, AbstractPointF):
                raise TypeError('The other parameter must be a PointF')
            self._x = other._x
            self._y = other._y
        else:
            self._x = args[0] if len(args) > 0 else kwargs['x']
            self._y = args[1] if len(args) > 1 else kwargs['y']

    def __eq__(self, other: typing.Any) -> bool:
        if isinstance(other, AbstractPointF):
            return self._x == other._y and self.y == other.y
        return super().__eq__(other)

    def x(self) -> float:
        return self._x

    def setX(self, x: float) -> None:
        self._x = x

    def y(self) -> float:
        return self._y

    def setY(self, y: float) -> None:
        self._y = y

# TODO: This (and PointF) could do with an offsetX, offsetY functions as there
# are quite a few places that are having to do get x/y then set x/y with modifier
class AbstractRectangleF(object):
    @typing.overload
    def __init__(self) -> None: ...
    @typing.overload
    def __init__(self, other: 'AbstractRectangleF') -> None: ...
    @typing.overload
    def __init__(self, x: float, y: float, width: float, height: float) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        if not args and not kwargs:
            self._x = self._y = self._width = self._height = 0
        elif len(args) + len(kwargs) == 1:
            other = args[0] if len(args) > 0 else kwargs['other']
            if not isinstance(other, AbstractRectangleF):
                raise TypeError('The other parameter must be a RectangleF')
            self._x = other._x
            self._y = other._y
            self._width = other._width
            self._height = other._height
        else:
            self._x = float(args[0] if len(args) > 0 else kwargs['x'])
            self._y = float(args[1] if len(args) > 1 else kwargs['y'])
            self._width = float(args[2] if len(args) > 2 else kwargs['width'])
            self._height = float(args[3] if len(args) > 3 else kwargs['height'])

    def x(self) -> float:
        return self._x

    def setX(self, x: float) -> None:
        self._x = x

    def y(self) -> float:
        return self._y

    def setY(self, y: float) -> None:
        self._y = y

    def width(self) -> float:
        return self._width

    def setWidth(self, width: float) -> None:
        self._width = width

    def height(self) -> float:
        return self._height

    def setHeight(self, height: float) -> None:
        self._height = height

    def left(self) -> float:
        return self._x

    def right(self) -> float:
        return self._x + self._width

    def top(self) -> float:
        return self._y

    def bottom(self) -> float:
        return self._y + self._height

    def centre(self) -> AbstractPointF:
        return AbstractPointF(self._x + (self._width / 2), self._y + (self._height / 2))

    def inflate(self, x: float, y: float) -> None:
        self._x -= x
        self._y -= y
        self._width += x * 2
        self._height += y * 2

    def intersectsWith(self, rect: 'AbstractRectangleF') -> bool:
        return (rect._x < self._x + self._width) and \
            (self._x < rect._x + rect._width) and \
            (rect._y < self._y + self._height) and \
            (self._y < rect._y + rect._height)

    def __eq__(self, other: typing.Any) -> bool:
        if isinstance(other, AbstractRectangleF):
            return self._x == other._x and self._y == other._y and\
                self._height == other._height and self._width == other._width
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
            self.copyFrom(other)
        else:
            self.families = args[0] if len(args) > 0 else kwargs['families']
            self.size = float(args[1] if len(args) > 1 else kwargs['size'])
            self.style = args[2] if len(args) > 2 else kwargs.get('style', FontStyle.Regular)

    def copyFrom(self, other: 'FontInfo') -> None:
        self.families = other.families
        self.size = other.size
        self.style = other.style

    def makeFont(self) -> 'AbstractFont':
        if not self.families:
            raise RuntimeError("FontInfo has null name")
        # TODO: Traveller Map has this as 1.4 but I found I needed to lower it to get
        # fonts rendering the correct size. Ideally I'd account for this in the Qt
        # specific code to keep this code the same as Traveller map
        return AbstractFont(self.families, self.size * 1.1, self.style, GraphicsUnit.World)

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
    def __init__(self, other: 'AbstractPen') -> None: ...
    @typing.overload
    def __init__(
        self,
        color: str,
        width: float,
        style: LineStyle = LineStyle.Solid,
        pattern: typing.Optional[typing.Sequence[float]] = None
        ) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        if not args and not kwargs:
            self._color = ''
            self._width = 0
            self._style = LineStyle.Solid
            self._pattern = None
        elif len(args) + len(kwargs) == 1:
            other = args[0] if len(args) > 0 else kwargs['other']
            if not isinstance(other, AbstractPen):
                raise TypeError('The other parameter must be an AbstractPen')
            self.copyFrom(other)
        else:
            self._color = args[0] if len(args) > 0 else kwargs['color']
            self._width = args[1] if len(args) > 1 else kwargs['width']
            self._style = args[2] if len(args) > 2 else kwargs.get('style', LineStyle.Solid)
            self._pattern = args[3] if len(args) > 3 else kwargs.get('pattern', None)

    def color(self) -> str:
        return self._color

    def setColor(self, color: str) -> None:
        self._color = color

    def width(self) -> float:
        return self._width

    def setWidth(self, width: float) -> None:
        self._width = width

    def style(self) -> float:
        return self._style

    def setStyle(
            self,
            style: LineStyle,
            pattern: typing.Optional[typing.List[float]] = None
            ) -> None:
        self._style = style
        if (self._style is LineStyle.Custom):
            if  pattern is not None:
                self._pattern = list(pattern)
        else:
            self._pattern = None

    def pattern(self) -> typing.Optional[typing.Sequence[float]]:
        return self._pattern

    def setPattern(
            self,
            pattern: typing.Sequence[float]
            ) -> None:
        self._style = LineStyle.Custom
        self._pattern = list(pattern)

    def copyFrom(
            self,
            other: 'AbstractPen'
            ) -> None:
        self._color = other._color
        self._width = other._width
        self._style = other._style
        self._pattern = list(other._pattern) if other._pattern else None

class AbstractBrush(object):
    @typing.overload
    def __init__(self) -> None: ...
    @typing.overload
    def __init__(self, other: 'AbstractBrush') -> None: ...
    @typing.overload
    def __init__(self, color: str) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        if not args and not kwargs:
            self._color = ''
        elif len(args) > 0:
            arg = args[0]
            self._color = arg._color if isinstance(arg, AbstractBrush) else arg
        elif 'other' in kwargs:
            other = kwargs['other']
            if not isinstance(other, AbstractBrush):
                raise TypeError('The other parameter must be an AbstractBrush')
            self.copyFrom(other)
        elif 'color' in kwargs:
            self._color = kwargs['color']
        else:
            raise ValueError('Invalid arguments')

    def color(self) -> str:
        return self._color

    def setColor(self, color: str) -> None:
        self._color = color

    def copyFrom(
            self,
            other: 'AbstractBrush'
            ) -> None:
        self._color = other._color

# TODO: Using Qt fonts here is a temp hack. Tge traveller map version of
# AbstractFont implementation uses a system drawing font class. I want to
# differ from this approach by having a completely abstract font interface
# so using this code doesn't require some specific library for rendering
# library for the font implementation
# TODO: Need to do something with GraphicsUnit
class AbstractFont(object):
    def __init__(self, families: str, emSize: float, style: FontStyle, units: GraphicsUnit):
        self._families = families
        self._family = None
        self._emSize = emSize
        self._style = style
        self._units = units

        self._font = None
        for family in self._families.split(','):
            try:
                self._font = QtGui.QFont(family)
                if self._font:
                    # Qt doesn't support floating point fonts so instead the font that
                    # is created is always the same point size and we scale it to the
                    # required em size
                    #self.font.setPointSizeF(emSize)
                    self._font.setPointSizeF(10)
                    if self._style & FontStyle.Bold:
                        self._font.setBold(True)
                    if self._style & FontStyle.Italic:
                        self._font.setItalic(True)
                    if self._style & FontStyle.Underline:
                        self._font.setUnderline(True)
                    if self._style & FontStyle.Strikeout:
                        self._font.setStrikeOut(True)

                    self._family = family
                    break
            except:
                self._font = None

        if not self._font:
            raise RuntimeError("No matching font family")

    def qtFont(self) -> QtGui.QFont:
        return self._font

    def emSize(self) -> float:
        return self._emSize

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

    def m11(self) -> float:
        return self._matrix[0][0]

    def m12(self) -> float:
        return self._matrix[0][1]

    def m21(self) -> float:
        return self._matrix[1][0]

    def m22(self) -> float:
        return self._matrix[1][1]

    def offsetX(self) -> float:
        return self._matrix[0][2]

    def offsetY(self) -> float:
        return self._matrix[1][2]

    def isIdentity(self) -> bool:
        return self._matrix == AbstractMatrix._IdentityMatrix

    def invert(self) -> None:
        self._matrix = numpy.linalg.inv(self._matrix)

    def rotatePrepend(self, degrees: float, center: AbstractPointF) -> None:
        degrees %= 360
        radians = math.radians(degrees)
        sinAngle = math.sin(radians)
        cosAngle = math.cos(radians)

        rotationMatrix = AbstractMatrix._createNumpyMatrix(
            m11=cosAngle,
            m12=sinAngle,
            m21=-sinAngle,
            m22=cosAngle,
            dx=center.x() * (1 - cosAngle) + center.y() * sinAngle,
            dy=center.y() * (1 - cosAngle) + center.x() * sinAngle)

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

    def transform(self, point: AbstractPointF) -> AbstractPointF:
        result = self._matrix.dot([point.x(), point.y(), 1])
        x = result[0]
        y = result[1]
        w = result[2]
        if w != 0:
            x /= w
            y /= w
        return AbstractPointF(x, y)

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
            points: typing.Sequence[AbstractPointF],
            types: typing.Sequence[PathPointType],
            closed: bool
            ):
        if len(points) != len(types):
            raise ValueError('AbstractPath point and type vectors have different lengths')
        self._points = list(points)
        self._types = list(types)
        self.closed = closed
        self._bounds = None # Calculate on demand

    def points(self) -> typing.Sequence[AbstractPointF]:
        return self._points
    def types(self) -> typing.Sequence[PathPointType]:
        return self._types

    def bounds(self) -> AbstractRectangleF:
        if self._bounds is not None:
            return self._bounds

        minX = maxX = minY = maxY = None
        for point in self._points:
            if minX is None or point.x() < minX:
                minX = point.x()
            if maxX is None or point.x() > maxX:
                maxX = point.x()
            if minY is None or point.y() < minY:
                minY = point.y()
            if maxY is None or point.y() > maxY:
                maxY = point.y()

        self._bounds = AbstractRectangleF(
            x=minX,
            y=minY,
            width=maxX - minX,
            height=maxY - minY)
        return self._bounds

# TODO: In the same way as AbstractFont, the fact this is using a QT
# class is a hack and I need a way to abstract the image format in
# a way that they can still be rendered efficiently
class AbstractImage(object):
    def __init__(self, path: str):
        self._path = path

        self._image = QtGui.QImage(self._path, None)
        if not self._image:
            raise RuntimeError(f'Failed to load {self._path}')

    def qtImage(self) -> QtGui.QImage:
        return self._image

    def width(self) -> int:
        return self._image.width()
    def height(self) -> int:
        return self._image.height()

class LabelStyle(object):
    @typing.overload
    def __init__(self) -> None: ...
    @typing.overload
    def __init__(
            self,
            rotation: float = 0,
            scale: typing.Optional[AbstractSizeF] = None,
            translation: typing.Optional[AbstractPointF] = None,
            uppercase: bool = False,
            wrap: bool = False
            ) -> None: ...

    def __init__(
            self,
            rotation: float = 0,
            scale: typing.Optional[AbstractSizeF] = None,
            translation: typing.Optional[AbstractPointF] = None,
            uppercase: bool = False,
            wrap: bool = False
            ) -> None:
        self.rotation = rotation
        self.scale = AbstractSizeF(scale) if scale else AbstractSizeF(width=1, height=1)
        self.translation = AbstractPointF(translation) if translation else AbstractPointF()
        self.uppercase = uppercase
        self.wrap = wrap

    def copyFrom(self, other: 'LabelStyle') -> None:
        self.rotation = other.rotation
        self.scale = AbstractSizeF(other.scale)
        self.translation = AbstractPointF(other.translation)
        self.uppercase = other.uppercase
        self.wrap = other.wrap
