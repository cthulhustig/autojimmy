from PyQt5 import QtGui # TODO: Get rid of the need for this include
import enum
import math
import numpy
import typing

class StringAlignment(enum.Enum):
    Baseline = 0
    Centered = 1
    TopLeft = 2
    TopCenter = 3
    TopRight = 4
    CenterLeft = 5
    CenterRight = 6
    BottomLeft = 7
    BottomCenter = 8
    BottomRight = 9

class DashStyle(enum.Enum):
    Solid = 0
    Dot = 1
    Dash = 2
    DashDot = 3
    DashDotDot = 4
    Custom = 5

# TODO: Why is this needed when DashStyle exists?
class LineStyle(enum.Enum):
    Solid = 0 # Default
    Dashed = 1
    Dotted = 2
    NoStyle = 3 # TODO: Was None in traveller map code

_LineStyleToDashStyleMap = {
    LineStyle.Solid: DashStyle.Solid,
    LineStyle.Dashed: DashStyle.Dash,
    LineStyle.Dotted: DashStyle.Dot
}
def lineStyleToDashStyle(lineStyle: LineStyle) -> DashStyle:
    return _LineStyleToDashStyleMap.get(lineStyle, DashStyle.Solid)

class FontStyle(enum.IntFlag):
    Regular = 0x0
    Bold = 0x1
    Italic = 0x2
    Underline = 0x4
    Strikeout = 0x8

# TODO: This should probably be combined with StringAlignment
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
            self.dashStyle = args[2] if len(args) > 2 else kwargs.get('dashStyle', DashStyle.Solid)
            self.customDashPattern = args[3] if len(args) > 3 else kwargs.get('customDashPattern', None)

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
        self._bounds = None # Calculate on demand

    @property
    def points(self) -> typing.Sequence[PointF]:
        return self._points
    @property
    def types(self) -> typing.Sequence[PathPointType]:
        return self._types

    @property
    def bounds(self) -> RectangleF:
        if self._bounds is not None:
            return self._bounds

        minX = maxX = minY = maxY = None
        for point in self._points:
            if minX is None or point.x < minX:
                minX = point.x
            if maxX is None or point.x > maxX:
                maxX = point.x
            if minY is None or point.y < minY:
                minY = point.y
            if maxY is None or point.y > maxY:
                maxY = point.y

        self._bounds = RectangleF(
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