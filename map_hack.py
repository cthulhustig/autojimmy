from PyQt5 import QtWidgets, QtCore, QtGui
import app
import base64
import common
import enum
import fnmatch
import gui
import locale
import logging
import io
import math
import numpy
import os
import random
import re
import sys
import traveller
import travellermap
import typing
import xml.etree.ElementTree
import cProfile, pstats, io
from pstats import SortKey

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
    def intersectClipPath(self, clip: AbstractPath) -> None:
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
    def drawArc(self, pen: AbstractPen, rect: RectangleF, startDegrees: float, sweepDegrees: float) -> None:
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

def loadTabFile(path: str) -> typing.Tuple[
        typing.List[str], # Headers
        typing.List[typing.Dict[
            str, # Header
            str]]]: # Value
    with open(path, 'r', encoding='utf-8-sig') as file:
        header = None
        rows = []
        for line in file.readlines():
            if not line:
                continue
            if line.startswith('#'):
                continue
            tokens = [t.strip() for t in line.split('\t')]
            if not header:
                header = tokens
                continue

            rows.append({header[i]:t for i, t in enumerate(tokens)})
    return (header, rows)

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
        _, rows = loadTabFile(path=path)
        labels = []
        for data in rows:
            labels.append(MapLabel(
                text=data['Text'].replace('\\n', '\n'),
                position=PointF(x=float(data['X']), y=float(data['Y'])),
                minor=bool(data['Minor'].lower() == 'true')))
        return labels

class WorldLabel(object):
    def __init__(
            self,
            name: str,
            mapOptions: MapOptions,
            location: PointF,
            labelBiasX: int = 0,
            labelBiasY: int = 0,
            ) -> None:
        self.name = name
        self.mapOptions = mapOptions
        self.location = PointF(location)
        self.labelBiasX = labelBiasX
        self.labelBiasY = labelBiasY

    def paint(
            self,
            graphics: AbstractGraphics,
            dotColor: str,
            labelBrush: AbstractBrush,
            labelFont: AbstractFont
            ) -> None:
        pt = PointF(self.location)

        with graphics.save():
            graphics.translateTransform(dx=pt.x, dy=pt.y)
            graphics.scaleTransform(
                scaleX=1.0 / travellermap.ParsecScaleX,
                scaleY=1.0 / travellermap.ParsecScaleY)

            radius = 3
            brush = AbstractBrush(dotColor)
            pen = AbstractPen(dotColor, 1)
            graphics.setSmoothingMode(AbstractGraphics.SmoothingMode.HighQuality)
            graphics.drawEllipse(
                pen=pen,
                brush=brush,
                rect=RectangleF(x=-radius / 2, y=-radius / 2, width=radius, height=radius))

            if self.labelBiasX > 0:
                if self.labelBiasY < 0:
                    format = TextFormat.BottomLeft
                elif self.labelBiasY > 0:
                    format = TextFormat.TopLeft
                else:
                    format = TextFormat.MiddleLeft
            elif self.labelBiasX < 0:
                if self.labelBiasY < 0:
                    format = TextFormat.BottomRight
                elif self.labelBiasY > 0:
                    format = TextFormat.TopRight
                else:
                    format = TextFormat.MiddleRight
            else:
                if self.labelBiasY < 0:
                    format = TextFormat.BottomCenter
                elif self.labelBiasY > 0:
                    format = TextFormat.TopCenter
                else:
                    format = TextFormat.Center

            drawStringHelper(
                graphics=graphics,
                text=self.name,
                font=labelFont,
                brush=labelBrush,
                x=self.labelBiasX * radius / 2,
                y=self.labelBiasY * radius / 2,
                format=format)

class WorldLabelCache(object):
    _WorldLabelPath = 'res/labels/Worlds.xml'

    def __init__(self, basePath: str):
        filePath = os.path.join(basePath, WorldLabelCache._WorldLabelPath)
        with open(filePath, 'r', encoding='utf-8-sig') as file:
            content = file.read()

        rootElement = xml.etree.ElementTree.fromstring(content)

        self.labels: typing.List[WorldLabel] = []
        for index, worldElement in enumerate(rootElement.findall('./World')):
            try:
                nameElement = worldElement.find('./Name')
                if nameElement is None:
                    raise RuntimeError('World label has no Name element')
                name = nameElement.text

                optionsElement = worldElement.find('./MapOptions')
                if optionsElement is None:
                    raise RuntimeError('World label has no MapOptions element')
                options = 0
                for token in optionsElement.text.split():
                    if token == 'WorldsHomeworlds':
                        options |= MapOptions.WorldsHomeworlds
                    elif token == 'WorldsCapitals':
                        options |= MapOptions.WorldsCapitals

                locationElement = worldElement.find('./Location')
                if locationElement is None:
                    raise RuntimeError('World label has no Location element')
                sector = locationElement.attrib.get('Sector')
                if sector is None:
                    raise RuntimeError('Location element has no Sector attribute')
                hex = locationElement.attrib.get('Hex')
                if hex is None:
                    raise RuntimeError('Location element has no Hex attribute')
                location = traveller.WorldManager.instance().sectorHexToPosition(f'{sector} {hex}')
                centerX, centerY = location.absoluteCenter()
                location = PointF(x=centerX, y=centerY)

                biasXElement = worldElement.find('./LabelBiasX')
                biasX = 0
                if biasXElement is not None:
                    biasX = int(biasXElement.text)
                biasYElement = worldElement.find('./LabelBiasY')
                biasY = 0
                if biasYElement is not None:
                    biasY = int(biasYElement.text)

                self.labels.append(WorldLabel(
                    name=name,
                    mapOptions=options,
                    location=location,
                    labelBiasX=biasX,
                    labelBiasY=biasY))
            except Exception as ex:
                logging.warning(f'Failed to read world label {index} from "{filePath}"', exc_info=ex)

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

class DefaultStyleCache(object):
    _BorderPattern = re.compile(r'border\.(\w+)')
    _RoutePattern = re.compile(r'route\.(\w+)')
    _DefaultStylePath = 'res/styles/otu.css'

    _RouteStyleMap = {
        'solid': traveller.Route.Style.Solid,
        'dashed': traveller.Route.Style.Dashed,
        'dotted': traveller.Route.Style.Dotted}

    def __init__(self, basePath: str):
        self._borderStyles = {}
        self._routeStyles = {}

        content = travellermap.readCssFile(
            os.path.join(basePath, DefaultStyleCache._DefaultStylePath))
        for group, properties in content.items():
            match = DefaultStyleCache._BorderPattern.match(group)
            if match:
                key = match.group(1)
                color = properties.get('color')
                style = properties.get('style')
                if style:
                    style = DefaultStyleCache._RouteStyleMap.get(style.lower())
                self._borderStyles[key] = (color, style)

            match = DefaultStyleCache._RoutePattern.match(group)
            if match:
                key = match.group(1)
                color = properties.get('color')
                style = properties.get('style')
                if style:
                    style = DefaultStyleCache._RouteStyleMap.get(style.lower())
                width = properties.get('width')
                if width:
                    width = float(width)
                self._routeStyles[key] = (color, style, width)

    def defaultBorderStyle(self, key: str) -> typing.Tuple[
            typing.Optional[str], # Colour
            typing.Optional[traveller.Border.Style]]:
        return self._borderStyles.get(key, (None, None))

    def defaultRouteStyle(self, key: str) -> typing.Tuple[
            typing.Optional[str], # Colour
            typing.Optional[traveller.Route.Style],
            typing.Optional[float]]: # Width
        return self._routeStyles.get(key, (None, None, None))

class ClipPathCache(object):
    class PathType(enum.Enum):
        Hex = 0
        # TODO: I don't currently support Square but I'm thinking of deleting
        # support for square hexes all together as I don't think they ever get
        # rendered in standard traveller map
        Square = 1
        # TODO: I don't think TypeCount is needed as it looks like it's only
        # used to initialise cache arrays with a size equal to the number of
        # entries in this enum
        #TypeCount = 2

    # NOTE: These offsets assume a clockwise winding
    _TopOffsets = [
        (-0.5 - travellermap.HexWidthOffset, 0), # Center left
        (-0.5 + travellermap.HexWidthOffset, -0.5), # Upper left
        (+0.5 - travellermap.HexWidthOffset, -0.5), # Upper right
        (+0.5 + travellermap.HexWidthOffset, 0) # Center right
    ]

    _RightOffsets = [
        (+0.5 - travellermap.HexWidthOffset, -0.5), # Upper right
        (+0.5 + travellermap.HexWidthOffset, 0), # Center right
        (+0.5 - travellermap.HexWidthOffset, +0.5), # Lower right
        (+0.5 + travellermap.HexWidthOffset, 1) # Center right of next hex
    ]

    _BottomOffsets = [
        (+0.5 + travellermap.HexWidthOffset, 0), # Center right
        (+0.5 - travellermap.HexWidthOffset, +0.5), # Lower right
        (-0.5 + travellermap.HexWidthOffset, +0.5), # Lower Left
        (-0.5 - travellermap.HexWidthOffset, 0) # Center left
    ]

    _LeftOffsets = [
        (-0.5 + travellermap.HexWidthOffset, +0.5), # Lower Left
        (-0.5 - travellermap.HexWidthOffset, 0), # Center left
        (-0.5 + travellermap.HexWidthOffset, -0.5), # Upper left
        (-0.5 - travellermap.HexWidthOffset, -1) # Center left of next hex
    ]

    def __init__(self):
        self._sectorClipPaths: typing.Mapping[
            typing.Tuple[
                int, # Sector X position
                int, # Sector Y position
                ClipPathCache.PathType
            ],
            AbstractPath
        ] = {}

    def sectorClipPath(
            self,
            sectorX: int,
            sectorY: int,
            pathType: PathType
            ) -> AbstractPath:
        key = (sectorX, sectorY, pathType)
        clipPath = self._sectorClipPaths.get(key)
        if clipPath:
            return clipPath

        originX, originY = travellermap.relativeSpaceToAbsoluteSpace(
            (sectorX, sectorY, 1, 1))

        points = []

        count = len(ClipPathCache._TopOffsets)
        y=0
        for x in range(0, travellermap.SectorWidth, 2):
            for i in range(count):
                offsetX, offsetY = ClipPathCache._TopOffsets[i]
                points.append(PointF(
                    x=((originX + x) - 0.5) + offsetX,
                    y=((originY + y) - 0.5) + offsetY))

        last = travellermap.SectorHeight - 2
        count = len(ClipPathCache._RightOffsets)
        x = travellermap.SectorWidth - 1
        for y in range(0, travellermap.SectorHeight, 2):
            if y == last:
                count -= 1
            for i in range(count):
                offsetX, offsetY = ClipPathCache._RightOffsets[i]
                points.append(PointF(
                    x=((originX + x) - 0.5) + offsetX,
                    y=(originY + y) + offsetY))

        count = len(ClipPathCache._BottomOffsets)
        y = travellermap.SectorHeight - 1
        for x in range(travellermap.SectorWidth - 1, -1, -2):
            for i in range(count):
                offsetX, offsetY = ClipPathCache._BottomOffsets[i]
                points.append(PointF(
                    x=((originX + x) - 0.5) + offsetX,
                    y=(originY + y) + offsetY))

        last = travellermap.SectorHeight - 2
        count = len(ClipPathCache._LeftOffsets)
        x = 0
        for y in range(travellermap.SectorHeight - 1, -1, -2):
            if y == last:
                count -= 1
            for i in range(count):
                offsetX, offsetY = ClipPathCache._LeftOffsets[i]
                points.append(PointF(
                    x=((originX + x) - 0.5) + offsetX,
                    y=((originY + y) - 0.5) + offsetY))

        types = [PathPointType.Start]
        types.extend([PathPointType.Line] * (len(points) - 2))
        types.append([PathPointType.Line | PathPointType.CloseSubpath])

        path = AbstractPath(points=points, types=types, closed=True)
        self._sectorClipPaths[key] = path
        return path

    @staticmethod
    def _sectorBounds(
            sectorX: int,
            sectorY: int
            ) -> RectangleF:
        return RectangleF(
            x=(sectorX * travellermap.SectorWidth) - travellermap.ReferenceHexX,
            y=(sectorY * travellermap.SectorHeight) - travellermap.ReferenceHexY,
            width=travellermap.SectorWidth,
            height=travellermap.SectorHeight)

class WorldHelper(object):
    # Traveller Map doesn't use trade codes for things you might expect it
    # would. Instead it has it's own logic based on UWP. Best guess is this is
    # to support older sector data that might not have trade codes
    _HighPopulation = 9
    _AgriculturalAtmospheres = set([4, 5, 6, 7, 8, 9])
    _AgriculturalHydrographics = set([4, 5, 6, 7, 8])
    _AgriculturalPopulations = set([5, 6, 7])
    _IndustrialAtmospheres = set([0, 1, 2, 4, 7, 9, 10, 11, 12])
    _IndustrialMinPopulation = 9
    _RichAtmospheres = set([6, 8])
    _RichPopulations = set([6, 7, 8])

    _DefaultAllegiances = set([
        "Im", # Classic Imperium
        "ImAp", # Third Imperium, Amec Protectorate (Dagu)
        "ImDa", # Third Imperium, Domain of Antares (Anta/Empt/Lish)
        "ImDc", # Third Imperium, Domain of Sylea (Core/Delp/Forn/Mass)
        "ImDd", # Third Imperium, Domain of Deneb (Dene/Reft/Spin/Troj)
        "ImDg", # Third Imperium, Domain of Gateway (Glim/Hint/Ley)
        "ImDi", # Third Imperium, Domain of Ilelish (Daib/Ilel/Reav/Verg/Zaru)
        "ImDs", # Third Imperium, Domain of Sol (Alph/Dias/Magy/Olde/Solo)
        "ImDv", # Third Imperium, Domain of Vland (Corr/Dagu/Gush/Reft/Vlan)
        "ImLa", # Third Imperium, League of Antares (Anta)
        "ImLc", # Third Imperium, Lancian Cultural Region (Corr/Dagu/Gush)
        "ImLu", # Third Imperium, Luriani Cultural Association (Ley/Forn)
        "ImSy", # Third Imperium, Sylean Worlds (Core)
        "ImVd", # Third Imperium, Vegan Autonomous District (Solo)
        "XXXX", # Unknown
        "??", # Placeholder - show as blank
        "--", # Placeholder - show as blank
    ])

    _T5OfficialAllegiancesPath = 'res/t5ss/allegiance_codes.tab'
    _T5UnofficialAllegiances = {
            # -----------------------
            # Unofficial/Unreviewed
            # -----------------------

            # M1120
            'FdAr': 'Fa',
            'BoWo': 'Bw',
            'LuIm': 'Li',
            'MaSt': 'Ma',
            'BaCl': 'Bc',
            'FdDa': 'Fd',
            'FdIl': 'Fi',
            'AvCn': 'Ac',
            'CoAl': 'Ca',
            'StIm': 'St',
            'ZiSi': 'Rv', # Ziru Sirka
            'VA16': 'V6',
            'CRVi': 'CV',
            'CRGe': 'CG',
            'CRSu': 'CS',
            'CRAk': 'CA'
    }
    _T5AllegiancesMap: typing.Optional[typing.Dict[
        str, # Code
        str # Legacy Code
        ]] = None

    _HydrographicsImageMap = {
        0x1: 'Hyd1',
        0x2: 'Hyd2',
        0x3: 'Hyd3',
        0x4: 'Hyd4',
        0x5: 'Hyd5',
        0x6: 'Hyd6',
        0x7: 'Hyd7',
        0x8: 'Hyd8',
        0x9: 'Hyd9',
        0xA: 'HydA',
    }
    _HydrographicsDefaultImage = 'Hyd0'

    @staticmethod
    def loadData(basePath: str) -> None:
        if WorldHelper._T5AllegiancesMap is not None:
            return # Already loaded
        WorldHelper._T5AllegiancesMap = {}

        _, rows = loadTabFile(path=os.path.join(basePath, WorldHelper._T5OfficialAllegiancesPath))
        for data in rows:
            code = data.get('Code')
            legacy = data.get('Legacy')
            WorldHelper._T5AllegiancesMap[code] = legacy
        for code, legacy in WorldHelper._T5UnofficialAllegiances.items():
            WorldHelper._T5AllegiancesMap[code] = legacy

    @staticmethod
    def hasWater(world: traveller.World) -> bool:
        return world.hasWaterRefuelling()

    @staticmethod
    def hasGasGiants(world: traveller.World) -> bool:
        return world.hasGasGiantRefuelling()

    @staticmethod
    def isHighPopulation(world: traveller.World) -> bool:
        uwp = world.uwp()
        population = uwp.numeric(element=traveller.UWP.Element.Population, default=-1)
        return population >= WorldHelper._HighPopulation

    @staticmethod
    def isAgricultural(world: traveller.World) -> bool:
        uwp = world.uwp()
        atmosphere = uwp.numeric(element=traveller.UWP.Element.Atmosphere, default=-1)
        hydrographics = uwp.numeric(element=traveller.UWP.Element.Hydrographics, default=-1)
        population = uwp.numeric(element=traveller.UWP.Element.Population, default=-1)
        return atmosphere in WorldHelper._AgriculturalAtmospheres and \
            hydrographics in WorldHelper._AgriculturalHydrographics and \
            population in WorldHelper._AgriculturalPopulations

    @staticmethod
    def isIndustrial(world: traveller.World) -> bool:
        uwp = world.uwp()
        atmosphere = uwp.numeric(element=traveller.UWP.Element.Atmosphere, default=-1)
        population = uwp.numeric(element=traveller.UWP.Element.Population, default=-1)
        return atmosphere in WorldHelper._IndustrialAtmospheres and \
            population >= WorldHelper._IndustrialMinPopulation

    @staticmethod
    def isRich(world: traveller.World) -> bool:
        uwp = world.uwp()
        atmosphere = uwp.numeric(element=traveller.UWP.Element.Atmosphere, default=-1)
        population = uwp.numeric(element=traveller.UWP.Element.Population, default=-1)
        return atmosphere in WorldHelper._RichAtmospheres and \
            population in WorldHelper._RichPopulations

    @staticmethod
    def isVacuum(world: traveller.World) -> bool:
        uwp = world.uwp()
        atmosphere = uwp.numeric(element=traveller.UWP.Element.Atmosphere, default=-1)
        return atmosphere == 0

    @staticmethod
    def isCapital(world: traveller.World) -> bool:
        # TODO: Need to check "Capital" support is working
        return world.hasTradeCode(traveller.TradeCode.SectorCapital) or \
            world.hasTradeCode(traveller.TradeCode.SubsectorCapital) or \
            world.hasTradeCode(traveller.TradeCode.ImperialCapital) or \
            world.hasRemark('Capital')

    @staticmethod
    def allegianceCode(world: traveller.World, ignoreDefault: bool, useLegacy: bool) -> str:
        allegiance = world.allegiance()
        if ignoreDefault and (allegiance in WorldHelper._DefaultAllegiances):
            return None
        if useLegacy and WorldHelper._T5AllegiancesMap:
            allegiance = WorldHelper._T5AllegiancesMap.get(allegiance, allegiance)
        return allegiance

    @staticmethod
    def worldImage(world: traveller.World, images: ImageCache) -> AbstractImage:
        uwp = world.uwp()
        size = uwp.numeric(element=traveller.UWP.Element.WorldSize, default=-1)
        if size <= 0:
            return images.worldImages['Belt']

        hydrographics = uwp.numeric(element=traveller.UWP.Element.Hydrographics, default=-1)
        return images.worldImages[
            WorldHelper._HydrographicsImageMap.get(hydrographics, WorldHelper._HydrographicsDefaultImage)]

def makeAlphaColor(
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
            # TODO: This should probably be an AbstractBrush to avoid having to create it all the time
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

    def worldColors(
            self,
            world: traveller.World
            ) -> typing.Tuple[
                typing.Optional[str], # Pen colour
                typing.Optional[str]]: # Brush colour
        penColor = None
        brushColor = None

        if self.showWorldDetailColors:
            if WorldHelper.isAgricultural(world) and WorldHelper.isRich(world):
                penColor = brushColor = travellermap.MapColours.TravellerAmber
            elif WorldHelper.isAgricultural(world):
                penColor = brushColor = travellermap.MapColours.TravellerGreen
            elif WorldHelper.isRich(world):
                penColor = brushColor = travellermap.MapColours.Purple
            elif WorldHelper.isIndustrial(world):
                penColor = brushColor = '#888888' # Gray
            elif world.uwp().numeric(element=traveller.UWP.Element.Atmosphere, default=-1) > 10:
                penColor = brushColor = '#CC6626' # Rust
            elif WorldHelper.isVacuum(world):
                brushColor = travellermap.MapColours.Black
                penColor = travellermap.MapColours.White
            elif WorldHelper.hasWater(world):
                brushColor = self.worldWater.fillColor
                penColor = self.worldWater.pen.color
            else:
                brushColor = self.worldNoWater.fillColor
                penColor = self.worldNoWater.pen.color
        else:
            # Classic colors

            # World disc
            hasWater = WorldHelper.hasWater(world)
            brushColor = \
                self.worldWater.fillColor \
                if hasWater else \
                self.worldNoWater.fillColor
            penColor = \
                self.worldWater.pen.color \
                if hasWater else \
                self.worldNoWater.pen.color

        return (penColor, brushColor)

    def _handleConfigUpdate(self) -> None:
        # Options
        self.backgroundColor = travellermap.MapColours.Black

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
        self.populationOverlay.visible = (self.options & MapOptions.PopulationOverlay) != 0
        self.importanceOverlay.visible = (self.options & MapOptions.ImportanceOverlay) != 0
        self.capitalOverlay.visible = (self.options & MapOptions.WorldColors) != 0
        self.showStellarOverlay = (self._options & MapOptions.StellarOverlay) != 0

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
            self.worlds.largeFontInfo = FontInfo(self.worlds.fontInfo)
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

        self.capitals.fillColor = travellermap.MapColours.Wheat
        self.capitals.textColor = travellermap.MapColours.TravellerRed
        self.amberZone.visible = self.redZone.visible = True
        self.amberZone.pen.color = travellermap.MapColours.TravellerAmber
        self.redZone.pen.color = travellermap.MapColours.TravellerRed
        self.macroBorders.pen.color = travellermap.MapColours.TravellerRed
        self.macroRoutes.pen.color = travellermap.MapColours.White
        self.microBorders.pen.color = travellermap.MapColours.Gray
        self.microRoutes.pen.color = travellermap.MapColours.Gray

        self.microBorders.textColor = travellermap.MapColours.TravellerAmber
        self.worldWater.fillColor = travellermap.MapColours.DeepSkyBlue
        self.worldNoWater.fillColor = travellermap.MapColours.White
        self.worldNoWater.pen.color = '#0000FF' # TODO: Color.Empty;

        gridColor = self._colorScaleInterpolate(
            scale=self.scale,
            minScale=StyleSheet._SectorGridMinScale,
            maxScale=StyleSheet._SectorGridFullScale,
            color=travellermap.MapColours.Gray)
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
            color='#0000FF', # TODO: Color.Empty,
            width=0.03 * penScale,
            dashStyle=DashStyle.Dash)
        self.importanceOverlay.pen = AbstractPen(
            color='#0000FF', # TODO: Color.Empty,
            width=0.03 * penScale,
            dashStyle=DashStyle.Dot)
        self.highlightWorlds.pen = AbstractPen(
            color='#0000FF', # TODO: Color.Empty,
            width=0.03 * penScale,
            dashStyle=DashStyle.DashDot)

        self.capitalOverlay.fillColor = makeAlphaColor(0x80, travellermap.MapColours.TravellerGreen)
        self.capitalOverlayAltA.fillColor = makeAlphaColor(0x80, travellermap.MapColours.Blue)
        self.capitalOverlayAltB.fillColor = makeAlphaColor(0x80, travellermap.MapColours.TravellerAmber)

        fadeSectorSubsectorNames = True

        self.placeholder.content = "*"
        self.placeholder.fontInfo = FontInfo("Georgia", 0.6)
        self.placeholder.position = PointF(0, 0.17)

        self.anomaly.content = "\u2316"; # POSITION INDICATOR
        self.anomaly.fontInfo = FontInfo("Arial Unicode MS,Segoe UI Symbol", 0.6)

        # Generic colors; applied to various elements by default (see end of this method).
        # May be overridden by specific styles
        foregroundColor = travellermap.MapColours.White
        lightColor = travellermap.MapColours.LightGray
        darkColor = travellermap.MapColours.DarkGray
        dimColor = travellermap.MapColours.DimGray
        highlightColor = travellermap.MapColours.TravellerRed

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

            self.capitals.fillColor = travellermap.MapColours.DarkGray
            self.capitals.textColor = travellermap.MapColours.Black
            self.amberZone.pen.color = travellermap.MapColours.LightGray
            self.redZone.pen.color = travellermap.MapColours.Black
            self.macroBorders.pen.color = travellermap.MapColours.Black
            self.macroRoutes.pen.color = travellermap.MapColours.Gray
            self.microBorders.pen.color = travellermap.MapColours.Black
            self.microRoutes.pen.color = travellermap.MapColours.Gray

            foregroundColor = travellermap.MapColours.Black
            self.backgroundColor = travellermap.MapColours.White
            lightColor = travellermap.MapColours.DarkGray
            darkColor = travellermap.MapColours.DarkGray
            dimColor = travellermap.MapColours.LightGray
            highlightColor = travellermap.MapColours.Gray
            self.microBorders.textColor = travellermap.MapColours.Gray
            self.worldWater.fillColor = travellermap.MapColours.Black
            self.worldNoWater.fillColor = '#0000FF' # TODO: Color.Empty

            self.worldNoWater.fillColor = travellermap.MapColours.White
            self.worldNoWater.pen = AbstractPen(travellermap.MapColours.Black, onePixel)

            self.riftOpacity = min(self.riftOpacity, 0.70)

            self.showWorldDetailColors = False

            self.populationOverlay.fillColor = makeAlphaColor(0x40, highlightColor)
            self.populationOverlay.pen.color = travellermap.MapColours.Gray

            self.importanceOverlay.fillColor = makeAlphaColor(0x20, highlightColor)
            self.importanceOverlay.pen.color = travellermap.MapColours.Gray

            self.highlightWorlds.fillColor = makeAlphaColor(0x30, highlightColor)
            self.highlightWorlds.pen.color = travellermap.MapColours.Gray
        elif self._style is travellermap.Style.Fasa:
            self.showGalaxyBackground = False
            self.deepBackgroundOpacity = 0
            self.riftOpacity = 0

            inkColor = '#5C4033'

            foregroundColor = inkColor
            self.backgroundColor = travellermap.MapColours.White

            # NOTE: This TODO came in from the Traveller Map code
            self.grayscale = True # TODO: Tweak to be "monochrome"
            self.lightBackground = True

            self.capitals.fillColor = inkColor
            self.capitals.textColor = inkColor
            self.amberZone.pen.color = inkColor
            self.amberZone.pen.width = onePixel * 2
            self.redZone.pen.color = '#0000FF' # TODO: Color.Empty
            self.redZone.fillColor = makeAlphaColor(0x80, inkColor)

            self.macroBorders.pen.color = inkColor
            self.macroRoutes.pen.color = inkColor

            self.microBorders.pen.color = inkColor
            self.microBorders.pen.width = onePixel * 2
            self.microBorders.fontInfo.size *= 0.6
            self.microBorders.fontInfo.style = FontStyle.Regular

            self.microRoutes.pen.color = inkColor

            lightColor = makeAlphaColor(0x80, inkColor)
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

            self.populationOverlay.fillColor = makeAlphaColor(0x40, highlightColor)
            self.populationOverlay.pen.color = travellermap.MapColours.Gray

            self.importanceOverlay.fillColor = makeAlphaColor(0x20, highlightColor)
            self.importanceOverlay.pen.color = travellermap.MapColours.Gray

            self.highlightWorlds.fillColor = makeAlphaColor(0x30, highlightColor)
            self.highlightWorlds.pen.color = travellermap.MapColours.Gray
        elif self._style is travellermap.Style.Print:
            self.lightBackground = True

            foregroundColor = travellermap.MapColours.Black
            self.backgroundColor = travellermap.MapColours.White
            lightColor = travellermap.MapColours.DarkGray
            darkColor = travellermap.MapColours.DarkGray
            dimColor = travellermap.MapColours.LightGray
            self.microRoutes.pen.color = travellermap.MapColours.Gray

            self.microBorders.textColor = travellermap.MapColours.Brown

            self.amberZone.pen.color = travellermap.MapColours.TravellerAmber
            self.worldNoWater.fillColor = travellermap.MapColours.White
            self.worldNoWater.pen = AbstractPen(travellermap.MapColours.Black, onePixel)

            self.riftOpacity = min(self.riftOpacity, 0.70)

            self.populationOverlay.fillColor = makeAlphaColor(0x40, self.populationOverlay.fillColor)
            self.populationOverlay.pen.color = travellermap.MapColours.Gray

            self.importanceOverlay.fillColor = makeAlphaColor(0x20, self.importanceOverlay.fillColor)
            self.importanceOverlay.pen.color = travellermap.MapColours.Gray

            self.highlightWorlds.fillColor = makeAlphaColor(0x30, self.highlightWorlds.fillColor)
            self.highlightWorlds.pen.color = travellermap.MapColours.Gray
        elif self._style is travellermap.Style.Draft:
            # TODO: For some reason all text is getting underlining set
            inkOpacity = 0xB0

            self.showGalaxyBackground = False
            self.lightBackground = True

            self.deepBackgroundOpacity = 0

            # TODO: I Need to handle alpha here
            self.backgroundColor = travellermap.MapColours.AntiqueWhite
            foregroundColor = makeAlphaColor(inkOpacity, travellermap.MapColours.Black)
            highlightColor = makeAlphaColor(inkOpacity, travellermap.MapColours.TravellerRed)

            lightColor = makeAlphaColor(inkOpacity, travellermap.MapColours.DarkCyan)
            darkColor = makeAlphaColor(inkOpacity, travellermap.MapColours.Black)
            dimColor = makeAlphaColor(inkOpacity / 2, travellermap.MapColours.Black)

            self.subsectorGrid.pen.color = makeAlphaColor(inkOpacity, travellermap.MapColours.Firebrick)

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

            self.microRoutes.pen.color = travellermap.MapColours.Gray

            self.parsecGrid.pen.color = lightColor
            self.microBorders.textColor = makeAlphaColor(inkOpacity, travellermap.MapColours.Brown)

            self.riftOpacity = min(self.riftOpacity, 0.30)

            self.numberAllHexes = True

            self.populationOverlay.fillColor = makeAlphaColor(0x40, self.populationOverlay.fillColor)
            self.populationOverlay.pen.color = travellermap.MapColours.Gray

            self.importanceOverlay.fillColor = makeAlphaColor(0x20, self.importanceOverlay.fillColor)
            self.importanceOverlay.pen.color = travellermap.MapColours.Gray

            self.highlightWorlds.fillColor = makeAlphaColor(0x30, self.highlightWorlds.fillColor)
            self.highlightWorlds.pen.color = travellermap.MapColours.Gray
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

            self.worldDetails = self.worldDetails &  ~WorldDetails.Starport & \
                ~WorldDetails.Allegiance & ~WorldDetails.Bases & ~WorldDetails.Hex

            if self.scale < StyleSheet._CandyMinWorldNameScale:
                self.worldDetails &= ~WorldDetails.KeyNames & ~WorldDetails.AllNames
            if self.scale < StyleSheet._CandyMinUwpScale:
                self.worldDetails &= ~WorldDetails.Uwp

            self.amberZone.pen.color = travellermap.MapColours.Goldenrod
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
                makeAlphaColor(128, travellermap.MapColours.Goldenrod)

            self.microBorders.textStyle.rotation = 0
            self.microBorders.textStyle.translation = PointF(0, 0.25)
            self.microBorders.textStyle.scale = SizeF(1.0, 0.5) # Expand
            self.microBorders.textStyle.uppercase = True

            self.microBorders.pen.color = makeAlphaColor(128, travellermap.MapColours.TravellerRed)
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

            self.backgroundColor = travellermap.MapColours.Black
            foregroundColor = travellermap.MapColours.Cyan
            highlightColor = travellermap.MapColours.White

            lightColor = travellermap.MapColours.LightBlue
            darkColor = travellermap.MapColours.DarkBlue
            dimColor = travellermap.MapColours.DimGray

            self.subsectorGrid.pen.color = travellermap.MapColours.Cyan

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

            self.microRoutes.pen.color = travellermap.MapColours.Gray

            self.parsecGrid.pen.color = travellermap.MapColours.Plum
            self.microBorders.textColor = travellermap.MapColours.Cyan

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
            foregroundColor = travellermap.MapColours.Black
            highlightColor = travellermap.MapColours.Red

            lightColor = travellermap.MapColours.Black
            darkColor = travellermap.MapColours.Black
            dimColor = travellermap.MapColours.Gray

            self.sectorGrid.pen.color = self.subsectorGrid.pen.color = self.parsecGrid.pen.color = foregroundColor

            self.microBorders.textColor = travellermap.MapColours.DarkSlateGray

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

            self.worldWater.fillColor = travellermap.MapColours.MediumBlue
            self.worldNoWater.fillColor = travellermap.MapColours.DarkKhaki
            self.worldWater.pen = AbstractPen(
                travellermap.MapColours.DarkGray,
                onePixel * 2)
            self.worldNoWater.pen = AbstractPen(
                travellermap.MapColours.DarkGray,
                onePixel * 2)

            self.showZonesAsPerimeters = True
            self.greenZone.visible = True
            self.greenZone.pen.width = self.amberZone.pen.width = self.redZone.pen.width = 0.05

            self.greenZone.pen.color = '#80C676'
            self.amberZone.pen.color = '#FBB040'
            self.redZone.pen.color = travellermap.MapColours.Red

            self.microBorders.textColor = travellermap.MapColours.DarkSlateGray

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
            self.uwp.fillColor = travellermap.MapColours.Black
            self.uwp.textColor = travellermap.MapColours.White
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

        # TODO: Remove hacky code
        self.minorHomeWorlds.visible = True
        #self.droyneWorlds.visible = True
        #self.ancientsWorlds.visible = True

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
        return makeAlphaColor(
            alpha=alpha,
            color=color)

class FontCache(object):
    def __init__(self, sheet: StyleSheet):
        self.sheet = sheet
        self._wingdingsFont = None
        self._glyphFont = None

    @property
    def wingdingFont(self) -> AbstractFont:
        if self._wingdingsFont:
            return self._wingdingsFont
        self._wingdingsFont = self.sheet.wingdingFont.makeFont()
        return self._wingdingsFont

    @property
    def glyphFont(self) -> AbstractFont:
        if self._glyphFont:
            return self._glyphFont
        self._glyphFont = self.sheet.glyphFont.makeFont()
        return self._glyphFont

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

class RectSelector(object):
    def __init__(
            self,
            rect: RectangleF,
            slop: float = 0.3 # Arbitrary, but 0.25 not enough for some routes.
            ) -> None:
        self._slop = slop
        self._rect = RectangleF(rect)

        self._cachedSectors = None
        self._cachedWorlds = None

    def rect(self) -> RectangleF:
        return RectangleF(self._rect)

    def setRect(self, rect: RectangleF) -> None:
        self._rect = RectangleF(rect)
        self._cachedSectors = None
        self._cachedWorlds = None

    def slop(self) -> float:
        return self._slop

    def setSlop(self, slop) -> None:
        self._slop = slop
        self._cachedSectors = None
        self._cachedWorlds = None

    def sectors(self) -> typing.Iterable[traveller.Sector]:
        if self._cachedSectors is not None:
            return self._cachedSectors

        rect = RectangleF(self._rect)
        if self._slop:
            rect.inflate(
                x=rect.width * self._slop,
                y=rect.height * self._slop)

        left = int(math.floor((rect.left + travellermap.ReferenceHexX) / travellermap.SectorWidth))
        right = int(math.floor((rect.right + travellermap.ReferenceHexX) / travellermap.SectorWidth))

        top = int(math.floor((rect.top + travellermap.ReferenceHexY) / travellermap.SectorHeight))
        bottom = int(math.floor((rect.bottom + travellermap.ReferenceHexY) / travellermap.SectorHeight))

        self._cachedSectors = traveller.WorldManager.instance().sectorsInArea(
            upperLeft=travellermap.HexPosition(
                sectorX=left,
                sectorY=top,
                offsetX=travellermap.SectorWidth - 1, # TODO: Not sure about -1 here and below
                offsetY=travellermap.SectorHeight - 1),
            lowerRight=travellermap.HexPosition(
                sectorX=right,
                sectorY=bottom,
                offsetX=0, # TODO: Should this be 0 or 1 (same for below)
                offsetY=0))

        return self._cachedSectors

    def worlds(self) -> typing.Iterable[traveller.World]:
        if self._cachedWorlds is not None:
            return self._cachedWorlds

        rect = RectangleF(self._rect)
        if self._slop:
            rect.inflate(
                x=rect.width * self._slop,
                y=rect.height * self._slop)

        left = int(math.floor(rect.left))
        right = int(math.ceil(rect.right))

        top = int(math.floor(rect.top))
        bottom = int(math.ceil(rect.bottom))

        self._cachedWorlds = traveller.WorldManager.instance().worldsInArea(
            upperLeft=travellermap.HexPosition(absoluteX=left, absoluteY=top),
            lowerRight=travellermap.HexPosition(absoluteX=right, absoluteY=bottom))

        return self._cachedWorlds

class Glyph(object):
    class GlyphBias(enum.Enum):
        NoBias = 0 # TODO: This was None in Traveller Map code
        Top = 1
        Bottom = 2

    @typing.overload
    def __init__(self, chars: str, highlight: bool = False, bias: GlyphBias = GlyphBias.NoBias) -> None: ...
    @typing.overload
    def __init__(self, other: 'Glyph', highlight: bool = False, bias: GlyphBias = GlyphBias.NoBias) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        if not args and not kwargs:
            self.characters = ''
            self.highlight = False
            self.bias = Glyph.GlyphBias.NoBias
        else:
            if args:
                if isinstance(args[0], Glyph):
                    self.characters = args[0].characters
                else:
                    self.characters = str(args[0])
            elif 'chars' in kwargs:
                self.characters = str(kwargs['chars'])
            elif 'other' in kwargs:
                other = kwargs['other']
                if not isinstance(other, Glyph):
                    raise TypeError('The other parameter must be a Glyph')
                self.characters = other.characters
            else:
                raise ValueError('Invalid arguments')
            self.highlight = int(args[1] if len(args) > 1 else kwargs.get('highlight', False))
            self.bias = args[2] if len(args) > 2 else kwargs.get('bias', Glyph.GlyphBias.NoBias)

    @property
    def isPrintable(self) -> bool:
        return len(self.characters) > 0

class GlyphDefs(object):
    NoGlyph = Glyph('') # TODO: This was Glyph.None in Traveller Map code
    Diamond = Glyph('\u2666') # U+2666 (BLACK DIAMOND SUIT)
    DiamondX = Glyph('\u2756') # U+2756 (BLACK DIAMOND MINUS WHITE X)
    Circle = Glyph('\u2022') # U+2022 (BULLET); alternate:  U+25CF (BLACK CIRCLE)
    Triangle = Glyph('\u25B2') # U+25B2 (BLACK UP-POINTING TRIANGLE)
    Square = Glyph('\u25A0') # U+25A0 (BLACK SQUARE)
    Star4Point = Glyph('\u2726') # U+2726 (BLACK FOUR POINTED STAR)
    Star5Point = Glyph('\u2605') # U+2605 (BLACK STAR)
    StarStar = Glyph('**') # Would prefer U+2217 (ASTERISK OPERATOR) but font coverage is poor

    # Research Stations
    Alpha = Glyph('\u0391', highlight=True)
    Beta = Glyph('\u0392', highlight=True)
    Gamma = Glyph('\u0393', highlight=True)
    Delta = Glyph('\u0394', highlight=True)
    Epsilon = Glyph('\u0395', highlight=True)
    Zeta = Glyph('\u0396', highlight=True)
    Eta = Glyph('\u0397', highlight=True)
    Theta = Glyph('\u0398', highlight=True)
    Omicron = Glyph('\u039F', highlight=True)

    # Other Textual
    Prison = Glyph('P', highlight=True)
    Reserve = Glyph('R')
    ExileCamp = Glyph('X')

    # TNE
    HiverSupplyBase = Glyph('\u2297')
    Terminus = Glyph('\u2297')
    Interface = Glyph('\u2297')

    _ResearchCodeMap = {
        'A': Alpha,
        'B': Beta,
        'G': Gamma,
        'D': Delta,
        'E': Epsilon,
        'Z': Zeta,
        'H': Eta,
        'T': Theta,
        'O': Omicron}

    @staticmethod
    def fromResearchCode(rs: str) -> Glyph:
        glyph = GlyphDefs.Gamma
        if len(rs) == 3:
            glyph = GlyphDefs._ResearchCodeMap.get(rs[2], glyph)
        return glyph

    # TODO: Using regexes for this is horrible AND slow
    def _compileGlyphRegex(wildcard: str) -> re.Pattern:
        return re.compile(fnmatch.translate(wildcard))
    _BaseGlyphs: typing.List[typing.Tuple[re.Pattern, Glyph]] = [
        (_compileGlyphRegex(r'*.C'), Glyph(StarStar, bias=Glyph.GlyphBias.Bottom)), # Vargr Corsair Base
        (_compileGlyphRegex(r'Im.D'), Glyph(Square, bias=Glyph.GlyphBias.Bottom)), # Imperial Depot
        (_compileGlyphRegex(r'*.D'), Glyph(Square, highlight=True)), # Depot
        (_compileGlyphRegex(r'*.E'), Glyph(StarStar, bias=Glyph.GlyphBias.Bottom)), # Hiver Embassy
        (_compileGlyphRegex(r'*.K'), Glyph(Star5Point, highlight=True, bias=Glyph.GlyphBias.Top)), # Naval Base
        (_compileGlyphRegex(r'*.M'), Glyph(Star4Point, bias=Glyph.GlyphBias.Bottom)), # Military Base
        (_compileGlyphRegex(r'*.N'), Glyph(Star5Point, bias=Glyph.GlyphBias.Top)), # Imperial Naval Base
        (_compileGlyphRegex(r'*.O'), Glyph(Square, highlight=True, bias=Glyph.GlyphBias.Top)), # K'kree Naval Outpost (non-standard)
        (_compileGlyphRegex(r'*.R'), Glyph(StarStar, bias=Glyph.GlyphBias.Bottom)), # Aslan Clan Base
        (_compileGlyphRegex(r'*.S'), Glyph(Triangle, bias=Glyph.GlyphBias.Bottom)), # Imperial Scout Base
        (_compileGlyphRegex(r'*.T'), Glyph(Star5Point, highlight=True, bias=Glyph.GlyphBias.Top)), # Aslan Tlaukhu Base
        (_compileGlyphRegex(r'*.V'), Glyph(Circle, bias=Glyph.GlyphBias.Bottom)), # Exploration Base
        (_compileGlyphRegex(r'Zh.W'), Glyph(Diamond, highlight=True)), # Zhodani Relay Station
        (_compileGlyphRegex(r'*.W'), Glyph(Triangle, highlight=True, bias=Glyph.GlyphBias.Bottom)), # Imperial Scout Waystation
        (_compileGlyphRegex(r'Zh.Z'), Diamond), # Zhodani Base (Special case for "Zh.KM")
        # For TNE
        (_compileGlyphRegex(r'Sc.H'), HiverSupplyBase), # Hiver Supply Base
        (_compileGlyphRegex(r'*.I'), Interface), # Interface
        (_compileGlyphRegex(r'*.T'), Terminus), # Terminus
        # Fallback
        (_compileGlyphRegex(r'*.*'), Circle)] # Independent Base

    @staticmethod
    def fromBaseCode(allegiance: str, code: str) -> Glyph:
        for regex, glyph in GlyphDefs._BaseGlyphs:
            if regex.match(allegiance + '.' + code):
                return glyph
        return GlyphDefs.Circle

# TODO: This is drawString from RenderUtils
_TextFormatToStringAlignment = {
    TextFormat.TopLeft: StringAlignment.TopRight,
    TextFormat.TopCenter: StringAlignment.TopCenter,
    TextFormat.TopRight: StringAlignment.TopRight,
    TextFormat.MiddleLeft: StringAlignment.CenterLeft,
    TextFormat.Center: StringAlignment.Centered,
    TextFormat.MiddleRight: StringAlignment.CenterRight,
    TextFormat.BottomLeft: StringAlignment.BottomLeft,
    TextFormat.BottomCenter: StringAlignment.BottomCenter,
    TextFormat.BottomRight: StringAlignment.BottomRight
}
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
    if len(lines) <= 1:
        graphics.drawString(
            text=text,
            font=font,
            brush=brush,
            x=x, y=y,
            format=_TextFormatToStringAlignment.get(format))
        return

    sizes = [graphics.measureString(line, font) for line in lines]

    # TODO: This needs updated to not use QT
    qtFont = font.font
    qtFontMetrics = QtGui.QFontMetrics(qtFont)

    # TODO: Not sure how to calculate this
    #fontUnitsToWorldUnits = qtFont.pointSize() / font.FontFamily.GetEmHeight(font.Style)
    fontUnitsToWorldUnits = font.emSize / qtFont.pointSize()
    lineSpacing = qtFontMetrics.lineSpacing() * fontUnitsToWorldUnits
    # TODO: I've commented this line out, it's uncommented in the traveller map code but
    # the value is never used
    #ascent = qtFontMetrics.ascent() * fontUnitsToWorldUnits
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

def drawLabelHelper(
        graphics: AbstractGraphics,
        text: str,
        center: PointF,
        font: AbstractFont,
        brush: AbstractBrush,
        labelStyle: LabelStyle
        ) -> None:
    with graphics.save():
        if labelStyle.uppercase:
            text = text.upper()
        if labelStyle.wrap:
            text = text.replace(' ', '\n')

        graphics.translateTransform(
            dx=center.x,
            dy=center.y)
        graphics.scaleTransform(
            scaleX=1.0 / travellermap.ParsecScaleX,
            scaleY=1.0 / travellermap.ParsecScaleY)

        graphics.translateTransform(
            dx=labelStyle.translation.x,
            dy=labelStyle.translation.y)
        graphics.rotateTransform(
            degrees=labelStyle.rotation)
        graphics.scaleTransform(
            scaleX=labelStyle.scale.width,
            scaleY=labelStyle.scale.height)

        if labelStyle.rotation != 0:
            graphics.setSmoothingMode(AbstractGraphics.SmoothingMode.AntiAlias)

        drawStringHelper(
            graphics=graphics,
            text=text,
            font=font,
            brush=brush,
            x=0,
            y=0)

_DingMap = {
    '\u2666': '\x74', # U+2666 (BLACK DIAMOND SUIT)
    '\u2756': '\x76', # U+2756 (BLACK DIAMOND MINUS WHITE X)
    '\u2726': '\xAA', # U+2726 (BLACK FOUR POINTED STAR)
    '\u2605': '\xAB', # U+2605 (BLACK STAR)
    '\u2736': '\xAC'} # U+2736 (BLACK SIX POINTED STAR)

def drawGlyphHelper(
        graphics: AbstractGraphics,
        glyph: Glyph,
        fonts: FontCache,
        brush: AbstractBrush,
        pt: PointF
        ) -> None:
    font = fonts.glyphFont
    s = glyph.characters
    if graphics.supportsWingdings():
        dings = ''
        for c in s:
            c = _DingMap.get(c)
            if c is None:
                dings = ''
                break
            dings += c
        if dings:
            font = fonts.wingdingFont
            s = dings

    graphics.drawString(
        text=s,
        font=font,
        brush=brush,
        x=pt.x,
        y=pt.y,
        format=StringAlignment.Centered)

class RenderContext(object):
    class BorderLayer(enum.Enum):
        Fill = 0
        Shade = 1
        Stroke = 2
        Regions = 3

    class WorldLayer(enum.Enum):
        Background = 0
        Foreground = 1
        Overlay = 2

    _GalaxyImageRect = RectangleF(-18257, -26234, 36551, 32462) # Chosen to match T5 pp.416
    _RiftImageRect = RectangleF(-1374, -827, 2769, 1754)

    _PseudoRandomStarsChunkSize = 256
    _PseudoRandomStarsMaxPerChunk = 400

    _HexPath = AbstractPath(
        points=[
            PointF(-0.5 + travellermap.HexWidthOffset, -0.5),
            PointF( 0.5 - travellermap.HexWidthOffset, -0.5),
            PointF( 0.5 + travellermap.HexWidthOffset, 0),
            PointF( 0.5 - travellermap.HexWidthOffset, 0.5),
            PointF(-0.5 + travellermap.HexWidthOffset, 0.5),
            PointF(-0.5 - travellermap.HexWidthOffset, 0),
            PointF(-0.5 + travellermap.HexWidthOffset, -0.5)],
        types=[
            PathPointType.Start,
            PathPointType.Line,
            PathPointType.Line,
            PathPointType.Line,
            PathPointType.Line,
            PathPointType.Line,
            PathPointType.Line | PathPointType.CloseSubpath],
        closed=True)

    def __init__(
            self,
            graphics: AbstractGraphics,
            tileRect: RectangleF, # Region to render in map coordinates
            tileSize: Size, # Pixel size of view to render to
            scale: float,
            styles: StyleSheet,
            imageCache: ImageCache,
            vectorCache: VectorObjectCache,
            mapLabelCache: MapLabelCache,
            worldLabelCache: WorldLabelCache,
            styleCache: DefaultStyleCache,
            options: MapOptions
            ) -> None:
        self._graphics = graphics
        self._tileRect = tileRect
        self._scale = scale
        self._options = options
        self._styles = styles
        self._imageCache = imageCache
        self._vectorCache = vectorCache
        self._mapLabelCache = mapLabelCache
        self._worldLabelCache = worldLabelCache
        self._styleCache = styleCache
        self._fontCache = FontCache(sheet=self._styles)
        self._clipCache = ClipPathCache()
        self._tileSize = tileSize
        self._selector = RectSelector(rect=self._tileRect)
        self._clipOutsectorBorders = True
        self._createLayers()
        self._updateSpaceTransforms()

    def setTileRect(self, rect: RectangleF) -> None:
        self._tileRect = rect
        self._selector.setRect(rect=self._tileRect)
        self._updateSpaceTransforms()

    def setClipOutsectorBorders(self, enable: bool) -> None:
        self._clipOutsectorBorders = enable

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
        rect = RectangleF()
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
                        rect.x = rand.random() * RenderContext._PseudoRandomStarsChunkSize + chunkLeft
                        rect.y = rand.random() * RenderContext._PseudoRandomStarsChunkSize + chunkTop
                        diameter = rand.random() * 2
                        rect.width = diameter / self._scale * travellermap.ParsecScaleX
                        rect.height = diameter / self._scale * travellermap.ParsecScaleY

                        self._graphics.drawEllipse(
                            pen=None,
                            brush=brush,
                            rect=rect)

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

        parsecSlop = 1

        hx = int(math.floor(self._tileRect.x))
        hw = int(math.ceil(self._tileRect.width))
        hy = int(math.floor(self._tileRect.y))
        hh = int(math.ceil(self._tileRect.height))

        pen = self._styles.parsecGrid.pen

        if self._styles.hexStyle == HexStyle.Square:
            rect = RectangleF()
            for px in range(hx - parsecSlop, hx + hw + parsecSlop):
                yOffset = 0 if ((px % 2) != 0) else 0.5
                for py in range(hy - parsecSlop, hy + hh + parsecSlop):
                    inset = 1
                    rect.x = px + inset
                    rect.y = py + inset + yOffset
                    rect.height = rect.width = 1 - inset * 2
                    self._graphics.drawRectangleOutline(pen=pen, rect=rect)
        elif self._styles.hexStyle == HexStyle.Hex:
            points = [PointF(), PointF(), PointF(), PointF()]
            for px in range(hx - parsecSlop, hx + hw + parsecSlop):
                yOffset = 0 if ((px % 2) != 0) else 0.5
                for py in range(hy - parsecSlop, hy + hh + parsecSlop):
                    points[0].x = px + -travellermap.HexWidthOffset
                    points[0].y = py + 0.5 + yOffset
                    points[1].x = px + travellermap.HexWidthOffset
                    points[1].y = py + 1.0 + yOffset
                    points[2].x = px + 1.0 - travellermap.HexWidthOffset
                    points[2].y = py + 1.0 + yOffset
                    points[3].x = px + 1.0 + travellermap.HexWidthOffset
                    points[3].y = py + 0.5 + yOffset
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
        for sector in self._selector.sectors():
            for index, subsector in enumerate(sector.subsectors()):
                name = subsector.name()
                if not name:
                    continue

                ssx = index % 4
                ssy = index // 4
                centerX, centerY = travellermap.relativeSpaceToAbsoluteSpace((
                    sector.x(),
                    sector.y(),
                    int(travellermap.SubsectorWidth * (2 * ssx + 1) // 2),
                    int(travellermap.SubsectorHeight * (2 * ssy + 1) // 2)))
                drawLabelHelper(
                    graphics=self._graphics,
                    text=subsector.name(),
                    center=PointF(x=centerX, y=centerY),
                    font=self._styles.subsectorNames.font,
                    brush=brush,
                    labelStyle=self._styles.subsectorNames.textStyle)

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
        if not self._styles.microRoutes.visible:
            return

        with self._graphics.save():
            self._graphics.setSmoothingMode(AbstractGraphics.SmoothingMode.AntiAlias)
            pen = AbstractPen(self._styles.microRoutes.pen)
            baseWidth = self._styles.microRoutes.pen.width

            for sector in self._selector.sectors():
                for route in sector.routes():
                    # Compute source/target sectors (may be offset)
                    startPoint = route.startHex()
                    endPoint = route.endHex()

                    # If drawing dashed lines twice and the start/end are swapped the
                    # dashes don't overlap correctly. So "sort" the points.
                    needsSwap = (startPoint.absoluteX() < endPoint.absoluteX()) or \
                        (startPoint.absoluteX() == endPoint.absoluteX() and \
                         startPoint.absoluteY() < endPoint.absoluteY())
                    if needsSwap:
                        (startPoint, endPoint) = (endPoint, startPoint)

                    startPoint = RenderContext._hexToCenter(startPoint)
                    endPoint = RenderContext._hexToCenter(endPoint)

                    # Shorten line to leave room for world glyph
                    self._offsetRouteSegment(startPoint, endPoint, self._styles.routeEndAdjust)

                    routeColor = route.colour()
                    routeWidth = route.width()
                    routeStyle = self._styles.overrideLineStyle
                    if not routeStyle:
                        if route.style() is traveller.Route.Style.Solid:
                            routeStyle = LineStyle.Solid
                        elif route.style() is traveller.Route.Style.Dashed:
                            routeStyle = LineStyle.Dashed
                        elif route.style() is traveller.Route.Style.Dotted:
                            routeStyle = LineStyle.Dotted

                    if not routeWidth or not routeColor or not routeStyle:
                        presidence = [route.allegiance(), route.type(), 'Im']
                        for key in presidence:
                            defaultColor, defaultStyle, defaltWidth = self._styleCache.defaultRouteStyle(key)
                            if not routeColor:
                                routeColor = defaultColor
                            if not routeStyle:
                                routeStyle = defaultStyle
                            if not routeWidth:
                                routeWidth = defaltWidth

                    # In grayscale, convert default color and style to non-default style
                    if self._styles.grayscale and (not routeColor) and (not routeStyle):
                        routeStyle = LineStyle.Dashed

                    if not routeWidth:
                        routeWidth = 1.0
                    if not routeColor:
                        routeColor = self._styles.microRoutes.pen.color
                    if not routeStyle:
                        routeStyle = LineStyle.Solid

                    # Ensure color is visible
                    # TODO: Handle making colour visible
                    """
                    if (styles.grayscale || !ColorUtil.NoticeableDifference(routeColor.Value, styles.backgroundColor))
                        routeColor = styles.microRoutes.pen.color; // default
                    """

                    pen.color = routeColor
                    pen.width = routeWidth * baseWidth
                    pen.dashStyle = lineStyleToDashStyle(routeStyle)

                    self._graphics.drawLine(pen, startPoint, endPoint)

    _WrapPattern = re.compile(r'\s+(?![a-z])')
    def _drawMicroLabels(self) -> None:
        if not self._styles.showMicroNames:
            return

        with self._graphics.save():
            self._graphics.setSmoothingMode(AbstractGraphics.SmoothingMode.AntiAlias)

            solidBrush = AbstractBrush()
            for sector in self._selector.sectors():
                solidBrush.color = self._styles.microBorders.textColor

                for border in sector.borders():
                    label = border.label()
                    if not label and border.allegiance():
                        label = traveller.AllegianceManager.instance().allegianceName(
                            allegianceCode=border.allegiance(),
                            sectorName=sector.name())
                    if not label:
                        continue
                    if border.wrapLabel:
                        label = RenderContext._WrapPattern.sub('\n', label)

                    labelPos = border.labelHex()
                    if not labelPos:
                        continue
                    labelPos = RenderContext._hexToCenter(labelPos)
                    if border.labelOffsetX():
                        labelPos.x += border.labelOffsetX() * 0.7
                    if border.labelOffsetY():
                        labelPos.y -= border.labelOffsetY() * 0.7

                    drawLabelHelper(
                        graphics=self._graphics,
                        text=label,
                        center=labelPos,
                        font=self._styles.microBorders.font,
                        brush=solidBrush,
                        labelStyle=self._styles.microBorders.textStyle)

                for label in sector.labels():
                    text = label.text()
                    if label.wrap():
                        text = RenderContext._WrapPattern.sub('\n', text)

                    labelPos = RenderContext._hexToCenter(label.hex())
                    # NOTE: This todo came in with the traveller map code
                    # TODO: Adopt some of the tweaks from .MSEC
                    if label.offsetX():
                        labelPos.x += label.offsetX() * 0.7
                    if label.offsetY():
                        labelPos.y -= label.offsetY() * 0.7

                    if label.size() is traveller.Label.Size.Small:
                        font = self._styles.microBorders.smallFont
                    elif label.size() is traveller.Label.Size.Large:
                        font = self._styles.microBorders.largeFont
                    else:
                        font = self._styles.microBorders.font

                    # TODO: Handle similar colours
                    solidBrush.color = label.colour() if label.colour() else travellermap.MapColours.TravellerAmber
                    """
                    if (!styles.grayscale &&
                        label.Color != null &&
                        ColorUtil.NoticeableDifference(label.Color.Value, styles.backgroundColor) &&
                        (label.Color != Label.DefaultColor))
                        solidBrush.Color = label.Color.Value;
                    else
                        solidBrush.Color = styles.microBorders.textColor;
                    """
                    drawLabelHelper(
                        graphics=self._graphics,
                        text=text,
                        center=labelPos,
                        font=font,
                        brush=solidBrush,
                        labelStyle=self._styles.microBorders.textStyle)

    def _drawSectorNames(self) -> None:
        if not (self._styles.showSomeSectorNames or self._styles.showAllSectorNames):
            return

        if not self._styles.showAllSectorNames:
            # TODO: Add support for only showing selected sectors. I think
            # this happens when you zoom out a bit and it still shows some
            # sector names (Core, Ley) but not all
            return

        self._graphics.setSmoothingMode(AbstractGraphics.SmoothingMode.HighQuality)
        for sector in self._selector.sectors():
            # TODO: Traveller Map would use the sector label first and only
            # fall back to the name if if there was no label. I need to work out
            # where that label is being loaded from
            name = sector.name()

            centerX, centerY = travellermap.relativeSpaceToAbsoluteSpace((
                sector.x(),
                sector.y(),
                int(travellermap.SectorWidth // 2),
                int(travellermap.SectorHeight // 2)))

            drawLabelHelper(
                graphics=self._graphics,
                text=name,
                center=PointF(x=centerX, y=centerY),
                font=self._styles.sectorName.font,
                brush=AbstractBrush(self._styles.sectorName.textColor),
                labelStyle=self._styles.sectorName.textStyle)

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
            for label in self._mapLabelCache.minorLabels:
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
        if (not self._styles.capitals.visible) or ((self._options & MapOptions.WorldsMask) == 0):
            return

        with self._graphics.save():
            self._graphics.setSmoothingMode(AbstractGraphics.SmoothingMode.HighQuality)
            solidBrush = AbstractBrush(self._styles.capitals.textColor)
            for worldLabel in self._worldLabelCache.labels:
                if (worldLabel.mapOptions & self._options) != 0:
                    worldLabel.paint(
                        graphics=self._graphics,
                        dotColor=self._styles.capitals.fillColor,
                        labelBrush=solidBrush,
                        labelFont=self._styles.macroNames.smallFont)

    def _drawMegaLabels(self) -> None:
        if not self._styles.megaNames.visible:
            return

        self._graphics.setSmoothingMode(AbstractGraphics.SmoothingMode.HighQuality)
        solidBrush = AbstractBrush(self._styles.megaNames.textColor)
        for label in self._mapLabelCache.megaLabels:
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
        if not self._styles.worlds.visible or self._styles.showStellarOverlay:
            return

        for world in self._selector.worlds():
            self._drawWorld(
                world=world,
                layer=RenderContext.WorldLayer.Background)

    def _drawWorldsForeground(self) -> None:
        if not self._styles.worlds.visible or self._styles.showStellarOverlay:
            return

        for world in self._selector.worlds():
            self._drawWorld(
                world=world,
                layer=RenderContext.WorldLayer.Foreground)

    def _drawWorldsOverlay(self) -> None:
        if not self._styles.worlds.visible:
            return

        with self._graphics.save():
            self._graphics.setSmoothingMode(AbstractGraphics.SmoothingMode.HighQuality)
            if self._styles.showStellarOverlay:
                for world in self._selector.worlds():
                    self._drawStars(world)
            elif self._styles.hasWorldOverlays:
                slop = self._selector.slop()
                self._selector.setSlop(max(slop, math.log(self._scale, 2.0) - 4))
                try:
                    for world in self._selector.worlds():
                        self._drawWorld(
                            world=world,
                            layer=RenderContext.WorldLayer.Overlay)
                finally:
                    self._selector.setSlop(slop)

    def _drawDroyneOverlay(self) -> None:
        if not self._styles.droyneWorlds.visible:
            return

        self._graphics.setSmoothingMode(AbstractGraphics.SmoothingMode.HighQuality)
        solidBrush = AbstractBrush(self._styles.droyneWorlds.textColor)
        for world in self._selector.worlds():
            allegiance = world.allegiance()

            droyne = allegiance == 'Dr' or allegiance == 'NaDr' or world.hasRemark('Droy')
            chirpers = world.hasRemark('Chir')

            if droyne or chirpers:
                glyph = self._styles.droyneWorlds.content[0 if droyne else 1]
                self._drawOverlayGlyph(
                    glyph=glyph,
                    font=self._styles.droyneWorlds.font,
                    brush=solidBrush,
                    position=world.hex())

    def _drawMinorHomeworldOverlay(self) -> None:
        if not self._styles.minorHomeWorlds.visible:
            return

        self._graphics.setSmoothingMode(AbstractGraphics.SmoothingMode.HighQuality)
        solidBrush = AbstractBrush(self._styles.minorHomeWorlds.textColor)
        for world in self._selector.worlds():
            if world.isMinorHomeworld():
                self._drawOverlayGlyph(
                    glyph=self._styles.minorHomeWorlds.content,
                    font=self._styles.minorHomeWorlds.font,
                    brush=solidBrush,
                    position=world.hex())

    def _drawAncientWorldsOverlay(self) -> None:
        if not self._styles.ancientsWorlds.visible:
            return

        self._graphics.setSmoothingMode(AbstractGraphics.SmoothingMode.HighQuality)
        solidBrush = AbstractBrush(self._styles.ancientsWorlds.textColor)
        for world in self._selector.worlds():
            if world.hasTradeCode(traveller.TradeCode.AncientsSiteWorld):
                self._drawOverlayGlyph(
                    glyph=self._styles.ancientsWorlds.content,
                    font=self._styles.ancientsWorlds.font,
                    brush=solidBrush,
                    position=world.hex())

    def _drawSectorReviewStatusOverlay(self) -> None:
        solidBrush = AbstractBrush()

        if self._styles.dimUnofficialSectors and self._styles.worlds.visible:
            solidBrush.color = makeAlphaColor(128, self._styles.backgroundColor)
            for sector in self._selector.sectors():
                if not sector.hasTag('Official') and not sector.hasTag('Preserve') and not sector.hasTag('InReview'):
                    clipPath = self._clipCache.sectorClipPath(
                        sectorX=sector.x(),
                        sectorY=sector.y(),
                        pathType=ClipPathCache.PathType.Hex)

                    self._graphics.drawPathFill(
                        brush=solidBrush,
                        path=clipPath)

        if self._styles.colorCodeSectorStatus and self._styles.worlds.visible:
            for sector in self._selector.sectors():
                if sector.hasTag('Official'):
                    solidBrush.color = makeAlphaColor(128, travellermap.MapColours.TravellerRed)
                elif sector.hasTag('InReview'):
                    solidBrush.color = makeAlphaColor(128, travellermap.MapColours.Orange)
                elif sector.hasTag('Unreviewed'):
                    solidBrush.color = makeAlphaColor(128, travellermap.MapColours.TravellerAmber)
                elif sector.hasTag('Apocryphal'):
                    solidBrush.color = makeAlphaColor(128, travellermap.MapColours.Magenta)
                elif sector.hasTag('Preserve'):
                    solidBrush.color = makeAlphaColor(128, travellermap.MapColours.TravellerGreen)
                else:
                    continue

                clipPath = self._clipCache.sectorClipPath(
                    sectorX=sector.x(),
                    sectorY=sector.y(),
                    pathType=ClipPathCache.PathType.Hex)

                self._graphics.drawPathFill(
                    brush=solidBrush,
                    path=clipPath)

    def _drawWorld(self, world: traveller.World, layer: WorldLayer) -> None:
        uwp = world.uwp()
        isPlaceholder = False # TODO: Handle placeholder worlds
        isCapital = WorldHelper.isCapital(world)
        isHiPop = WorldHelper.isHighPopulation(world)
        renderName = ((self._styles.worldDetails & WorldDetails.AllNames) != 0) or \
            (((self._styles.worldDetails & WorldDetails.KeyNames) != 0) and (isCapital or isHiPop))
        renderUWP = (self._styles.worldDetails & WorldDetails.Uwp) != 0

        with self._graphics.save():
            self._graphics.setSmoothingMode(AbstractGraphics.SmoothingMode.AntiAlias)

            center = RenderContext._hexToCenter(world.hex())

            self._graphics.translateTransform(
                dx=center.x,
                dy=center.y)
            self._graphics.scaleTransform(
                scaleX=self._styles.hexContentScale / travellermap.ParsecScaleX,
                scaleY=self._styles.hexContentScale / travellermap.ParsecScaleY)
            self._graphics.rotateTransform(
                degrees=self._styles.hexRotation)

            if layer is RenderContext.WorldLayer.Overlay:
                if self._styles.populationOverlay.visible and (world.population() > 0):
                    self._drawOverlay(
                        element=self._styles.populationOverlay,
                        radius=math.sqrt(world.population() / math.pi) * 0.00002)

                if self._styles.importanceOverlay.visible:
                    # TODO: Handle importance overlay
                    """
                    int im = world.CalculatedImportance;
                    if (im > 0)
                    {
                        DrawOverlay(styles.importanceOverlay, (im - 0.5f) * Astrometrics.ParsecScaleX, ref solidBrush, ref pen);
                    }
                    """

                if self._styles.capitalOverlay.visible:
                    # TODO: Handle capital overlay
                    """
                    bool hasIm = world.CalculatedImportance >= 4;
                    bool hasCp = world.IsCapital;

                    if (hasIm && hasCp)
                        DrawOverlay(styles.capitalOverlay, 2 * Astrometrics.ParsecScaleX, ref solidBrush, ref pen);
                    else if (hasIm)
                        DrawOverlay(styles.capitalOverlayAltA, 2 * Astrometrics.ParsecScaleX, ref solidBrush, ref pen);
                    else if (hasCp)
                        DrawOverlay(styles.capitalOverlayAltB, 2 * Astrometrics.ParsecScaleX, ref solidBrush, ref pen);
                    """

                # TODO: Not sure if I need to bother with highlight pattern stuff. It
                # doesn't look like it's used in tile rendering (just image rendering)
                """
                if (styles.highlightWorlds.visible && styles.highlightWorldsPattern!.Matches(world))
                {
                    DrawOverlay(styles.highlightWorlds, Astrometrics.ParsecScaleX, ref solidBrush, ref pen);
                }
                """

            if not self._styles.useWorldImages:
                # Normal (non-"Eye Candy") styles
                if layer is RenderContext.WorldLayer.Background:
                    if (self._styles.worldDetails & WorldDetails.Zone) != 0:
                        elem = self._zoneStyle(world)
                        if elem and elem.visible:
                            if self._styles.showZonesAsPerimeters:
                                with self._graphics.save():
                                    # TODO: Why is this 2 separate scale transforms?
                                    self._graphics.scaleTransform(
                                        scaleX=travellermap.ParsecScaleX,
                                        scaleY=travellermap.ParsecScaleY)
                                    self._graphics.scaleTransform(
                                        scaleX=0.95,
                                        scaleY=0.95)
                                    self._graphics.drawPathOutline(
                                        pen=elem.pen,
                                        path=RenderContext._HexPath)
                            else:
                                if elem.fillColor:
                                    self._graphics.drawEllipse(
                                        brush=AbstractBrush(elem.fillColor),
                                        pen=None,
                                        rect=RectangleF(x=-0.4, y=-0.4, width=0.8, height=0.8))
                                if elem.pen.color:
                                    if renderName and self._styles.fillMicroBorders:
                                        # TODO: Is saving the state actually needed here?
                                        with self._graphics.save():
                                            self._graphics.intersectClipRect(
                                                rect=RectangleF(
                                                    x=-0.5,
                                                    y=-0.5,
                                                    width=1,
                                                    height=0.65 if renderUWP else 0.75))
                                            self._graphics.drawEllipse(
                                                pen=elem.pen,
                                                brush=None,
                                                rect=RectangleF(x=-0.4, y=-0.4, width=0.8, height=0.8))
                                    else:
                                        self._graphics.drawEllipse(
                                            pen=elem.pen,
                                            brush=None,
                                            rect=RectangleF(x=-0.4, y=-0.4, width=0.8, height=0.8))

                    if not self._styles.numberAllHexes and \
                        ((self._styles.worldDetails & WorldDetails.Hex) != 0):

                        hex = world.hex()
                        if self._styles.hexContentScale is HexCoordinateStyle.Subsector:
                            # TODO: Handle subsector hex whatever that is
                            #hex=f'{hex.offsetX():02d}{hex.offsetY():02d}'
                            hex='TODO'
                        else:
                            hex=f'{hex.offsetX():02d}{hex.offsetY():02d}'
                        self._graphics.drawString(
                            text=hex,
                            font=self._styles.hexNumber.font,
                            brush=AbstractBrush(self._styles.hexNumber.textColor),
                            x=self._styles.hexNumber.position.x,
                            y=self._styles.hexNumber.position.y,
                            format=StringAlignment.TopCenter)

                if layer is RenderContext.WorldLayer.Foreground:
                    elem = self._zoneStyle(world)
                    worldTextBackgroundStyle = \
                        TextBackgroundStyle.NoStyle \
                        if (not elem or not elem.fillColor) else \
                        self._styles.worlds.textBackgroundStyle

                    # TODO: Implement placeholders, this should be
                    # if (!isPlaceholder)
                    if True:
                        if ((self._styles.worldDetails & WorldDetails.GasGiant) != 0) and \
                            WorldHelper.hasGasGiants(world):
                            self._drawGasGiant(
                                self._styles.worlds.textColor,
                                self._styles.gasGiantPosition.x,
                                self._styles.gasGiantPosition.y,
                                0.05,
                                self._styles.showGasGiantRing)

                        if (self._styles.worldDetails & WorldDetails.Starport) != 0:
                            starport = uwp.code(traveller.UWP.Element.StarPort)
                            if self._styles.showTL:
                                starport += "-" + uwp.code(traveller.UWP.Element.TechLevel)
                            self._drawWorldLabel(
                                backgroundStyle=worldTextBackgroundStyle,
                                brush=AbstractBrush(self._styles.uwp.fillColor),
                                color=self._styles.worlds.textColor,
                                position=self._styles.starport.position,
                                font=self._styles.starport.font,
                                text=starport)

                        if renderUWP:
                            self._drawWorldLabel(
                                backgroundStyle=self._styles.uwp.textBackgroundStyle,
                                brush=AbstractBrush(self._styles.uwp.fillColor),
                                color=self._styles.uwp.textColor,
                                position=self._styles.uwp.position,
                                font=self._styles.hexNumber.font,
                                text=uwp.string())

                        # NOTE: This todo came in with the traveller map code
                        # TODO: Mask off background for glyphs
                        if (self._styles.worldDetails & WorldDetails.Bases) != 0:
                            bases = world.bases()
                            baseCount = bases.count()

                            # TODO: Handle base allegiances
                            """
                            # Special case: Show Zho Naval+Military as diamond
                            if (world.BaseAllegiance == "Zh" && bases == "KM")
                                bases = "Z";
                            """

                            # Base 1
                            bottomUsed = False
                            if baseCount:
                                glyph = GlyphDefs.fromBaseCode(
                                    allegiance=world.allegiance(),
                                    code=traveller.Bases.code(bases[0]))
                                if glyph.isPrintable:
                                    pt = self._styles.baseTopPosition
                                    if glyph.bias is Glyph.GlyphBias.Bottom and not self._styles.ignoreBaseBias:
                                        pt = self._styles.baseBottomPosition
                                        bottomUsed = True

                                    brush = AbstractBrush(
                                        self._styles.worlds.textHighlightColor
                                        if glyph.highlight else
                                        self._styles.worlds.textColor)
                                    drawGlyphHelper(
                                        graphics=self._graphics,
                                        glyph=glyph,
                                        fonts=self._fontCache,
                                        brush=brush,
                                        pt=pt)

                            # Base 2
                            # TODO: Add support for legacyAllegiance
                            """
                            if baseCount > 1:
                                glyph = GlyphDefs.fromBaseCode(
                                    allegiance=world.legacyAllegiance, bases[1])
                                if glyph.isPrintable:
                                    pt = self._styles.baseTopPosition if bottomUsed else self._styles.baseBottomPosition
                                    solidBrush.color = \
                                        self._styles.worlds.textHighlightColor \
                                        if glyph.isHighlighted else \
                                        self._styles.worlds.textColor
                                    drawGlyphHelper(
                                        graphics=self._graphics,
                                        glyph=glyph,
                                        fonts=self._fontCache,
                                        brush=solidBrush,
                                        position=pt)

                            # Base 3 (!)
                            if baseCount > 2:
                                glyph = GlyphDefs.fromBaseCode(world.legacyAllegiance, bases[2])
                                if glyph.isPrintable:
                                    solidBrush.color = \
                                        self._styles.worlds.textHighlightColor \
                                        if glyph.isHighlighted else \
                                        self._styles.worlds.textColor
                                    drawGlyphHelper(
                                        graphics=self._graphics,
                                        glyph=glyph,
                                        fonts=self._fontCache,
                                        brush=solidBrush,
                                        position=self._styles.baseMiddlePosition)
                            """

                            # Research Stations
                            # TODO: Handle research stations/penal colony etc
                            """
                            rs = world.researchStation()
                            glyph = None
                            if rs:
                                glyph = GlyphDefs.fromResearchCode(rs)
                            elif world.isReserve:
                                glyph = GlyphDefs.Reserve
                            elif world.isPenalColony:
                                glyph = GlyphDefs.Prison
                            elif world.isPrisonExileCamp:
                                glyph = GlyphDefs.ExileCamp
                            if glyph:
                                solidBrush.color = \
                                    self._styles.worlds.textHighlightColor \
                                    if glyph.isHighlighted else \
                                    self._styles.worlds.textColor
                                drawGlyphHelper(
                                    graphics=self._graphics,
                                    glyph=glyph,
                                    fonts=self._fontCache,
                                    brush=solidBrush,
                                    position=self._styles.baseMiddlePosition)
                            """

                    if (self._styles.worldDetails & WorldDetails.Type) != 0:
                        # TODO: Handle placeholders, this should be
                        # if (isPlaceholder)
                        if False:
                            e = self._styles.anomaly if world.isAnomaly() else self._styles.placeholder
                            self._drawWorldLabel(
                                backgroundStyle=e.textBackgroundStyle,
                                brush=AbstractBrush(self._styles.worlds.textColor),
                                color=e.textColor,
                                position=e.position,
                                font=e.font,
                                text=e.content)
                        else:
                            with self._graphics.save():
                                self._graphics.translateTransform(
                                    dx=self._styles.discPosition.x,
                                    dy=self._styles.discPosition.y)
                                if uwp.numeric(element=traveller.UWP.Element.WorldSize, default=-1) <= 0:
                                    if (self._styles.worldDetails & WorldDetails.Asteroids) != 0:
                                        # Basic pattern, with probability varying per position:
                                        #   o o o
                                        #  o o o o
                                        #   o o o

                                        lpx = [-2, 0, 2, -3, -1, 1, 3, -2, 0, 2]
                                        lpy = [-2, -2, -2, 0, 0, 0, 0, 2, 2, 2]
                                        lpr = [0.5, 0.9, 0.5, 0.6, 0.9, 0.9, 0.6, 0.5, 0.9, 0.5]

                                        brush = AbstractBrush(self._styles.worlds.textColor)

                                        # Random generator is seeded with world location so it is always the same
                                        rand = random.Random(world.hex().absoluteX() ^ world.hex().absoluteY())
                                        rect = RectangleF()
                                        for i in range(len(lpx)):
                                            if rand.random() < lpr[i]:
                                                rect.x = lpx[i] * 0.035
                                                rect.y = lpy[i] * 0.035

                                                rect.width = 0.04 + rand.random() * 0.03
                                                rect.height = 0.04 + rand.random() * 0.03

                                                # If necessary, add jitter here
                                                #rect.x += 0
                                                #rect.y += 0

                                                self._graphics.drawEllipse(
                                                    brush=brush,
                                                    pen=None,
                                                    rect=rect)
                                    else:
                                        # Just a glyph
                                        drawGlyphHelper(
                                            graphics=self._graphics,
                                            glyph=GlyphDefs.DiamondX,
                                            fonts=self._fontCache,
                                            brush=AbstractBrush(self._styles.worlds.textColor),
                                            pt=PointF(0, 0))
                                else:
                                    penColor, brushColor = self._styles.worldColors(world)
                                    brush = AbstractBrush(brushColor) if brushColor else None
                                    pen = AbstractPen(self._styles.worldWater.pen) if penColor else None
                                    if pen:
                                        pen.color = penColor
                                    self._graphics.drawEllipse(
                                        pen=pen,
                                        brush=brush,
                                        rect=RectangleF(
                                            x=-self._styles.discRadius,
                                            y=-self._styles.discRadius,
                                            width=2 * self._styles.discRadius,
                                            height=2 * self._styles.discRadius))
                    elif not world.isAnomaly():
                        # Dotmap
                        self._graphics.drawEllipse(
                            brush=AbstractBrush(self._styles.worlds.textColor),
                            pen=None,
                            rect=RectangleF(
                                x=-self._styles.discRadius,
                                y=-self._styles.discRadius,
                                width=2 * self._styles.discRadius,
                                height=2 * self._styles.discRadius))

                    if renderName:
                        name = world.name()
                        highlight = (self._styles.worldDetails & WorldDetails.Highlight) != 0
                        if (isHiPop and highlight) or \
                            self._styles.worlds.textStyle.uppercase:
                            name = name.upper()

                        textColor = \
                            self._styles.worlds.textHighlightColor \
                            if isCapital and highlight else \
                            self._styles.worlds.textColor
                        font = \
                            self._styles.worlds.largeFont \
                            if (isHiPop or isCapital) and highlight else \
                            self._styles.worlds.font

                        self._drawWorldLabel(
                            backgroundStyle=worldTextBackgroundStyle,
                            brush=AbstractBrush(self._styles.worlds.textColor),
                            color=textColor,
                            position=self._styles.worlds.textStyle.translation,
                            font=font,
                            text=name)

                    if (self._styles.worldDetails & WorldDetails.Allegiance) != 0:
                        alleg = WorldHelper.allegianceCode(
                            world=world,
                            ignoreDefault=True,
                            useLegacy=not self._styles.t5AllegianceCodes)
                        if alleg:
                            if self._styles.lowerCaseAllegiance:
                                alleg = alleg.lower()

                            self._graphics.drawString(
                                text=alleg,
                                font=self._styles.worlds.smallFont,
                                brush=AbstractBrush(self._styles.worlds.textColor),
                                x=self._styles.allegiancePosition.x,
                                y=self._styles.allegiancePosition.y,
                                format=StringAlignment.Centered)
            else: # styles.useWorldImages
                # "Eye-Candy" style
                worldSize = world.physicalSize()
                imageRadius = (0.6 if worldSize <= 0 else (0.3 * (worldSize / 5.0 + 0.2))) / 2
                decorationRadius = imageRadius

                if layer is RenderContext.WorldLayer.Background:
                    if (self._styles.worldDetails & WorldDetails.Type) != 0:
                        # TODO: Handle placeholders, this should be
                        #if isPlaceholder:
                        if False:
                            e = self._styles.anomaly if world.isAnomaly() else self._styles.placeholder
                            self._drawWorldLabel(
                                backgroundStyle=e.textBackgroundStyle,
                                brush=AbstractBrush(self._styles.worlds.textColor),
                                color=e.textColor,
                                position=e.position,
                                font=e.font,
                                text=e.content)
                        else:
                            scaleX = 1.5 if worldSize <= 0 else 1
                            scaleY = 1.0 if worldSize <= 0 else 1
                            self._graphics.drawImage(
                                image=WorldHelper.worldImage(
                                    world=world,
                                    images=self._imageCache),
                                rect=RectangleF(
                                    x=-imageRadius * scaleX,
                                    y=-imageRadius * scaleY,
                                    width=imageRadius * 2 * scaleX,
                                    height=imageRadius * 2 * scaleY))
                    elif not world.isAnomaly():
                        # Dotmap
                        self._graphics.drawEllipse(
                            brush=AbstractBrush(self._styles.worlds.textColor),
                            pen=None,
                            rect=RectangleF(
                                x=-self._styles.discRadius,
                                y=-self._styles.discRadius,
                                width=2 * self._styles.discRadius,
                                height=2 * self._styles.discRadius))

                # TODO: Support placeholders, this should be
                # if (isPlaceholder)
                if False:
                    return

                if layer is RenderContext.WorldLayer.Foreground:
                    decorationRadius += 0.1

                    if (self._styles.worldDetails & WorldDetails.Zone) != 0:
                        zone = world.zone()
                        if zone is traveller.ZoneType.AmberZone or zone is traveller.ZoneType.RedZone:
                            pen = \
                                self._styles.amberZone.pen \
                                if zone is traveller.ZoneType.AmberZone else \
                                self._styles.redZone.pen
                            rect = RectangleF(
                                x=-decorationRadius,
                                y=-decorationRadius,
                                width=decorationRadius * 2,
                                height=decorationRadius * 2)

                            self._graphics.drawArc(
                                pen=pen,
                                rect=rect,
                                startDegrees=5,
                                sweepDegrees=80)
                            self._graphics.drawArc(
                                pen=pen,
                                rect=rect,
                                startDegrees=95,
                                sweepDegrees=80)
                            self._graphics.drawArc(
                                pen=pen,
                                rect=rect,
                                startDegrees=185,
                                sweepDegrees=80)
                            self._graphics.drawArc(
                                pen=pen,
                                rect=rect,
                                startDegrees=275,
                                sweepDegrees=80)
                            decorationRadius += 0.1

                    if (self._styles.worldDetails & WorldDetails.GasGiant) != 0:
                        symbolRadius = 0.05
                        if self._styles.showGasGiantRing:
                            decorationRadius += symbolRadius
                        self._drawGasGiant(
                            color=self._styles.worlds.textHighlightColor,
                            x=decorationRadius,
                            y=0,
                            radius=symbolRadius,
                            ring=self._styles.showGasGiantRing)
                        decorationRadius += 0.1

                    if renderUWP:
                        # NOTE: This todo came in with the traveller map code
                        # TODO: Scale, like the name text.
                        self._graphics.drawString(
                            text=uwp.string(),
                            font=self._styles.hexNumber.font,
                            brush=AbstractBrush(self._styles.worlds.textColor),
                            x=decorationRadius,
                            y=self._styles.uwp.position.y,
                            format=StringAlignment.CenterLeft)

                    if renderName:
                        name = world.name()
                        if isHiPop:
                            name.upper()

                        with self._graphics.save():
                            highlight = (self._styles.worldDetails & WorldDetails.Highlight) != 0
                            textColor = \
                                self._styles.worlds.textHighlightColor \
                                if isCapital and highlight else \
                                self._styles.worlds.textColor

                            if self._styles.worlds.textStyle.uppercase:
                                name = name.upper()

                            self._graphics.translateTransform(
                                dx=decorationRadius,
                                dy=0.0)
                            self._graphics.scaleTransform(
                                scaleX=self._styles.worlds.textStyle.scale.width,
                                scaleY=self._styles.worlds.textStyle.scale.height)
                            self._graphics.translateTransform(
                                dx=self._graphics.measureString(
                                    text=name,
                                    font=self._styles.worlds.font).width / 2,
                                dy=0.0) # Left align

                            self._drawWorldLabel(
                                backgroundStyle=self._styles.worlds.textBackgroundStyle,
                                brush=AbstractBrush(self._styles.worlds.textColor),
                                color=textColor,
                                position=self._styles.worlds.textStyle.translation,
                                font=self._styles.worlds.font,
                                text=name)

    def _drawWorldLabel(
            self,
            backgroundStyle: TextBackgroundStyle,
            brush: AbstractBrush,
            color: str,
            position: PointF,
            font: AbstractFont,
            text: str
            ) -> None:
        size = self._graphics.measureString(text=text, font=font)

        if backgroundStyle is TextBackgroundStyle.Rectangle:
            if not self._styles.fillMicroBorders:
                # NOTE: This todo came over from traveller map
                # TODO: Implement this with a clipping region instead
                self._graphics.drawRectangleFill(
                    brush=AbstractBrush(self._styles.backgroundColor),
                    rect=RectangleF(
                        x=position.x - size.width / 2,
                        y=position.y - size.height / 2,
                        width=size.width,
                        height=size.height))
        elif backgroundStyle is TextBackgroundStyle.Filled:
            self._graphics.drawRectangleFill(
                brush=brush,
                rect=RectangleF(
                    x=position.x - size.width / 2,
                    y=position.y - size.height / 2,
                    width=size.width,
                    height=size.height))
        elif backgroundStyle is TextBackgroundStyle.Outline or \
            backgroundStyle is TextBackgroundStyle.Shadow:
            # NOTE: This todo came over from traveller map
            # TODO: These scaling factors are constant for a render; compute once

            # Invert the current scaling transforms
            sx = 1.0 / self._styles.hexContentScale
            sy = 1.0 / self._styles.hexContentScale
            sx *= travellermap.ParsecScaleX
            sy *= travellermap.ParsecScaleY
            sx /= self._scale * travellermap.ParsecScaleX
            sy /= self._scale * travellermap.ParsecScaleY

            outlineSize = 2
            outlineSkip = 1

            outlineStart = -outlineSize if backgroundStyle is TextBackgroundStyle.Outline else 0
            brush = AbstractBrush(self._styles.backgroundColor)

            dx = outlineStart
            while dx <= outlineSize:
                dy = outlineStart
                while dy <= outlineSize:
                    self._graphics.drawString(
                        text=text,
                        font=font,
                        brush=brush,
                        x=position.x + sx * dx,
                        y=position.y + sy * dy,
                        format=StringAlignment.Centered)
                    dy += outlineSkip
                dx += outlineSkip

        self._graphics.drawString(
            text=text,
            font=font,
            brush=AbstractBrush(color),
            x=position.x,
            y=position.y,
            format=StringAlignment.Centered)

    def _drawStars(self, world: traveller.World) -> None:
        with self._graphics.save():
            self._graphics.setSmoothingMode(AbstractGraphics.SmoothingMode.AntiAlias)
            center = self._hexToCenter(world.hex())

            self._graphics.translateTransform(dx=center.x, dy=center.y)
            self._graphics.scaleTransform(
                scaleX=self._styles.hexContentScale / travellermap.ParsecScaleX,
                scaleY=self._styles.hexContentScale / travellermap.ParsecScaleY)

            solidBrush = AbstractBrush()
            pen = AbstractPen()
            for i, (fillColour, lineColor, radius) in enumerate(RenderContext._worldStarProps(world=world)):
                solidBrush.color = fillColour
                pen.color = lineColor
                pen.dashStyle = DashStyle.Solid
                pen.width = self._styles.worlds.pen.width
                offset = RenderContext._starOffset(i)
                offsetScale = 0.3
                radius *= 0.15
                self._graphics.drawEllipse(
                    pen=pen,
                    brush=solidBrush,
                    rect=RectangleF(
                        x=offset.x * offsetScale - radius,
                        y=offset.y * offsetScale - radius,
                        width=radius * 2,
                        height=radius * 2))

    def _drawGasGiant(
            self,
            color: str,
            x: float,
            y: float,
            radius: float,
            ring: bool
            ) -> None:
        with self._graphics.save():
            self._graphics.translateTransform(dx=x, dy=y)
            self._graphics.drawEllipse(
                brush=AbstractBrush(color),
                pen=None,
                rect=RectangleF(
                    x=-radius,
                    y=-radius,
                    width=radius * 2,
                    height=radius * 2))

            if ring:
                self._graphics.rotateTransform(degrees=-30)
                self._graphics.drawEllipse(
                    pen=AbstractPen(color=color, width=radius / 4),
                    brush=None,
                    rect=RectangleF(
                        x=-radius * 1.75,
                        y=-radius * 0.4,
                        width=radius * 1.75 * 2,
                        height=radius * 0.4 * 2))

    def _drawOverlay(
            self,
            element: StyleSheet.StyleElement,
            radius: float
            ) -> None:
        # Prevent "Out of memory" exception when rendering to GDI+.
        if radius < 0.001:
            return

        self._graphics.drawEllipse(
            pen=element.pen,
            brush=AbstractBrush(element.fillColor),
            rect=RectangleF(x=-radius, y=-radius, width=radius * 2, height=radius * 2))

    def _drawMicroBorders(self, layer: BorderLayer) -> None:
        fillAlpha = 64
        shadeAlpha = 128

        self._graphics.setSmoothingMode(AbstractGraphics.SmoothingMode.HighQuality)

        pathType = \
            ClipPathCache.PathType.Square \
            if self._styles.microBorderStyle == MicroBorderStyle.Square else \
            ClipPathCache.PathType.Hex

        solidBrush = AbstractBrush()
        pen = AbstractPen(self._styles.microBorders.pen) # TODO: Color.Empty)

        penWidth = pen.width
        for sector in self._selector.sectors():
            # This looks craptacular for Candy style borders :(
            shouldClip = self._clipOutsectorBorders and \
                ((layer == RenderContext.BorderLayer.Fill) or \
                    (self._styles.microBorderStyle != MicroBorderStyle.Curve))
            clip = None
            if shouldClip:
                clip = self._clipCache.sectorClipPath(
                    sectorX=sector.x(),
                    sectorY=sector.y(),
                    pathType=pathType)
                if not self._tileRect.intersectsWith(clip.bounds):
                    continue

            with self._graphics.save():
                if clip:
                    self._graphics.intersectClipPath(path=clip)

                self._graphics.setSmoothingMode(AbstractGraphics.SmoothingMode.AntiAlias)

                regions = \
                    sector.regions() \
                    if layer is RenderContext.BorderLayer.Regions else \
                    sector.borders()

                for region in regions:
                    regionColor = region.colour()
                    regionStyle = None

                    if isinstance(region, traveller.Border):
                        if region.style() is traveller.Border.Style.Solid:
                            regionStyle = LineStyle.Solid
                        elif region.style() is traveller.Border.Style.Dashed:
                            regionStyle = LineStyle.Dashed
                        elif region.style() is traveller.Border.Style.Dotted:
                            regionStyle = LineStyle.Dotted

                        if not regionColor or not regionStyle:
                            defaultColor, defaultStyle = self._styleCache.defaultBorderStyle(region.allegiance())
                            if not regionColor:
                                regionColor = defaultColor
                            if not regionStyle:
                                regionStyle = defaultStyle

                    if not regionColor:
                        regionColor = self._styles.microRoutes.pen.color
                    if not regionStyle:
                        regionStyle = LineStyle.Solid

                    if (layer is RenderContext.BorderLayer.Stroke) and (regionStyle is LineStyle.NoStyle):
                        continue

                    # TODO: Handle noticable colours
                    """
                    if (styles.grayscale ||
                        !ColorUtil.NoticeableDifference(borderColor.Value, styles.backgroundColor))
                    {
                        borderColor = styles.microBorders.pen.color; // default
                    }
                    """

                    outline = region.absoluteOutline()
                    drawPath = []
                    for x, y in outline:
                        drawPath.append(PointF(x=x, y=y))
                    types = [PathPointType.Start]
                    for _ in range(len(outline) - 1):
                        types.append(PathPointType.Line)
                    types[-1] |= PathPointType.CloseSubpath
                    drawPath = AbstractPath(points=drawPath, types=types, closed=True)

                    pen.color = regionColor
                    pen.dashStyle = lineStyleToDashStyle(regionStyle)

                    # Allow style to override
                    if self._styles.microBorders.pen.dashStyle is not DashStyle.Solid:
                        pen.dashStyle = self._styles.microBorders.pen.dashStyle
                    else:
                        pen.dashStyle = lineStyleToDashStyle(regionStyle)

                    # Shade is a wide/solid outline under the main outline.
                    if layer is RenderContext.BorderLayer.Shade:
                        pen.width = penWidth * 2.5
                        pen.dashStyle = DashStyle.Solid
                        pen.color = makeAlphaColor(shadeAlpha, pen.color)

                    # TODO: There should be alternate handling for curves but I don't think i'm
                    # going to be able to support it as I'm not sure how to draw them with QPainter
                    #if self._styles.microBorderStyle is not MicroBorderStyle.Curve:
                    with self._graphics.save():
                        # Clip to the path itself - this means adjacent borders don't clash
                        self._graphics.intersectClipPath(path=drawPath)
                        if layer is RenderContext.BorderLayer.Regions or layer is RenderContext.BorderLayer.Fill:
                            try:
                                red, green, blue, _ = travellermap.stringToColourChannels(colour=regionColor)
                            except Exception as ex:
                                logging.warning('Failed to parse region colour', exc_info=ex)
                                continue
                            solidBrush.color = travellermap.colourChannelsToString(
                                red=red,
                                green=green,
                                blue=blue,
                                alpha=fillAlpha)
                            self._graphics.drawPathFill(brush=solidBrush, path=drawPath)
                        elif layer is RenderContext.BorderLayer.Shade or layer is RenderContext.BorderLayer.Stroke:
                            self._graphics.drawPathOutline(pen=pen, path=drawPath)

    def _drawOverlayGlyph(
            self,
            glyph: str,
            font: AbstractFont,
            brush: AbstractBrush,
            position: travellermap.HexPosition
            ) -> None:
        centerX, centerY = position.absoluteCenter()
        with self._graphics.save():
            self._graphics.translateTransform(centerX, centerY)
            self._graphics.scaleTransform(1 / travellermap.ParsecScaleX, 1 / travellermap.ParsecScaleY)
            self._graphics.drawString(glyph, font, brush, 0, 0, StringAlignment.Centered)

    def _zoneStyle(self, world: traveller.World) -> typing.Optional[StyleSheet.StyleElement]:
        zone = world.zone()
        if zone is traveller.ZoneType.AmberZone:
            return self._styles.amberZone
        if zone is traveller.ZoneType.RedZone:
            return self._styles.redZone
        # TODO: Handle placeholders, this should be
        # if (styles.greenZone.visible && !world.IsPlaceholder)
        if self._styles.greenZone.visible:
            return self._styles.greenZone
        return None

    _StarPropsMap = {
        'O': ('#9DB4FF', 4),
        'B': ('#BBCCFF', 3),
        'A': ('#FBF8FF', 2),
        'F': ('#FFFFED', 1.5),
        'G': ('#FFFF00', 1),
        'K': ('#FF9833', 0.7),
        'M': ('#FF0000', 0.5)}
    _StarLuminanceMap = {
        'Ia': 7,
        'Ib': 5,
        'II': 3,
        'III': 2,
        'IV': 1,
        'V': 0}
    @staticmethod
    def _worldStarProps(world: traveller.World) -> typing.Iterable[typing.Tuple[
            str, # Fill Color,
            str, # Border Color
            float]]: # Radius
        stellar = world.stellar()
        props = []
        for star in stellar.yieldStars():
            classification = star.string()
            if classification == 'D':
                props.append((travellermap.MapColours.White, travellermap.MapColours.Black, 0.3))
            # NOTE: This todo came in with traveller map code
            # TODO: Distinct rendering for black holes, neutron stars, pulsars
            elif classification == 'NS' or classification == 'PSR' or classification == 'BH':
                props.append((travellermap.MapColours.Black, travellermap.MapColours.White, 0.8))
            elif classification == 'BD':
                props.append((travellermap.MapColours.Brown, travellermap.MapColours.Black, 0.3))
            else:
                color, radius = RenderContext._StarPropsMap.get(
                    star.code(element=traveller.Star.Element.SpectralClass),
                    (None, None))
                if color:
                    luminance = star.code(element=traveller.Star.Element.LuminosityClass)
                    luminance = RenderContext._StarLuminanceMap.get(luminance, 0)
                    props.append((color, travellermap.MapColours.Black, radius + luminance))

        props.sort(key=lambda p: p[2], reverse=True)
        return props

    _StarOffsetX = [
        0.0,
        math.cos(math.pi * 1 / 3), math.cos(math.pi * 2 / 3), math.cos(math.pi * 3 / 3),
        math.cos(math.pi * 4 / 3), math.cos(math.pi * 5 / 3), math.cos(math.pi * 6 / 3)]
    _StarOffsetY = [
        0.0,
        math.sin(math.pi * 1 / 3), math.sin(math.pi * 2 / 3), math.sin(math.pi * 3 / 3),
        math.sin(math.pi * 4 / 3), math.sin(math.pi * 5 / 3), math.sin(math.pi * 6 / 3)]
    @staticmethod
    def _starOffset(index: int) -> PointF:
        if index >= len(RenderContext._StarOffsetX):
            index = (index % (len(RenderContext._StarOffsetX) - 1)) + 1
        return PointF(RenderContext._StarOffsetX[index], RenderContext._StarOffsetY[index])

    @staticmethod
    def _offsetRouteSegment(startPoint: PointF, endPoint: PointF, offset: float) -> None:
        dx = (endPoint.x - startPoint.x) * travellermap.ParsecScaleX
        dy = (endPoint.y - startPoint.y) * travellermap.ParsecScaleY
        length = math.sqrt(dx * dx + dy * dy)
        if not length:
            return # No offset
        ddx = (dx * offset / length) / travellermap.ParsecScaleX
        ddy = (dy * offset / length) / travellermap.ParsecScaleY
        startPoint.x += ddx
        startPoint.y += ddy
        endPoint.x -= ddx
        endPoint.y -= ddy

    @staticmethod
    def _hexToCenter(hex: travellermap.HexPosition) -> PointF:
        centerX, centerY = hex.absoluteCenter()
        return PointF(x=centerX, y=centerY)

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
        self._supportsWingdings = None

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

    def supportsWingdings(self) -> bool:
        if self._supportsWingdings is not None:
            return self._supportsWingdings

        self._supportsWingdings = False
        try:
            font = QtGui.QFont('Wingdings')
            self._supportsWingdings = font.exactMatch()
        except:
            pass

        return self._supportsWingdings

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
        clipPath = self._painter.clipPath()
        clipPath.setFillRule(QtCore.Qt.FillRule.WindingFill)
        clipPath.addPolygon(self._convertPath(path))
        self._painter.setClipPath(clipPath, operation=QtCore.Qt.ClipOperation.IntersectClip)
    # TODO: This was an overload of intersectClip in traveller map code
    def intersectClipRect(self, rect: RectangleF) -> None:
        clipPath = self._painter.clipPath()
        clipPath.setFillRule(QtCore.Qt.FillRule.WindingFill)
        clipPath.addRect(self._convertRect(rect))
        self._painter.setClipPath(clipPath, operation=QtCore.Qt.ClipOperation.IntersectClip)

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
        self._painter.setPen(QtCore.Qt.PenStyle.NoPen)
        self._painter.setBrush(self._convertBrush(brush))
        self._painter.drawPolygon(self._convertPath(path))

    def drawCurve(self, pen: AbstractPen, path: AbstractPath, tension: float = 0.5):
        self.drawLines(pen=pen, points=path.points)
    # TODO: This was an overload of drawClosedCurve in the traveller map code
    def drawClosedCurveOutline(self, pen: AbstractPen, path: AbstractPath, tension: float = 0.5):
        self.drawPathOutline(pen=pen, path=path)
    def drawClosedCurveFill(self, brush: AbstractBrush, path: AbstractPath, tension: float = 0.5):
        self.drawPathOutline(brush=brush, path=path)

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
    def drawEllipse(
            self,
            pen: typing.Optional[AbstractPen],
            brush: typing.Optional[AbstractBrush],
            rect: RectangleF):
        self._painter.setPen(self._convertPen(pen) if pen else QtCore.Qt.PenStyle.NoPen)
        self._painter.setBrush(self._convertBrush(brush) if brush else QtCore.Qt.BrushStyle.NoBrush)
        self._painter.drawEllipse(self._convertRect(rect))

    def drawArc(
            self,
            pen: AbstractPen,
            rect: RectangleF,
            startDegrees: float,
            sweepDegrees: float
            ) -> None:
        self._painter.setPen(self._convertPen(pen))
        # NOTE: Angles are in 1/16th of a degree
        self._painter.drawArc(
            self._convertRect(rect),
            int((startDegrees * 16) + 0.5),
            int((sweepDegrees * 16) + 0.5))

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
        # TODO: Not sure if this should use bounds or tight bounds. It needs to
        # be correct for what will actually be rendered for different alignments
        contentPixelRect = fontMetrics.tightBoundingRect(text)
        #contentPixelRect = fontMetrics.boundingRect(text)
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
        qtFont = self._convertFont(font)
        scale = font.emSize / qtFont.pointSize()

        self._painter.setFont(qtFont)
        # TODO: It looks like Qt uses a pen for text rather than the brush
        # it may make more sense for it to just be a colour that is passed
        # to drawString
        self._painter.setPen(QtGui.QColor(brush.color))
        self._painter.setBrush(self._convertBrush(brush))

        fontMetrics = QtGui.QFontMetrics(qtFont)
        # TODO: Not sure if this should use bounds or tight bounds. It needs to
        # be correct for what will actually be rendered for different alignments
        """
        contentPixelRect = fontMetrics.tightBoundingRect(text)
        fullPixelRect = fontMetrics.boundingRect(text)
        leftPadding = contentPixelRect.x() - fullPixelRect.x()
        topPadding = contentPixelRect.y() - fullPixelRect.y()
        """
        contentPixelRect = fontMetrics.tightBoundingRect(text)
        leftPadding = 0
        topPadding = fontMetrics.descent()

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
                        (-contentPixelRect.width() / 2) - (leftPadding / 2),
                        (contentPixelRect.height() / 2) - (topPadding / 2)),
                    text)
            elif format == StringAlignment.TopLeft:
                self._painter.drawText(
                    QtCore.QPointF(
                        0 + leftPadding,
                        contentPixelRect.height() + topPadding),
                    text)
            elif format == StringAlignment.TopCenter:
                self._painter.drawText(
                    QtCore.QPointF(
                        (-contentPixelRect.width() / 2) - (leftPadding / 2),
                        contentPixelRect.height() + topPadding),
                    text)
            elif format == StringAlignment.TopRight:
                self._painter.drawText(
                    QtCore.QPointF(
                        -contentPixelRect.width() - leftPadding,
                        contentPixelRect.height() + topPadding),
                    text)
            elif format == StringAlignment.CenterLeft:
                self._painter.drawText(
                    QtCore.QPointF(
                        0 + leftPadding,
                        (contentPixelRect.height() / 2) - (topPadding / 2)),
                    text)
            elif format == StringAlignment.CenterRight:
                self._painter.drawText(
                    QtCore.QPointF(
                        -contentPixelRect.width() - leftPadding,
                        (contentPixelRect.height() / 2) - (topPadding / 2)),
                    text)
            elif format == StringAlignment.BottomLeft:
                self._painter.drawText(
                    QtCore.QPointF(
                        0 + leftPadding,
                        contentPixelRect.height()),
                    text)
            elif format == StringAlignment.BottomCenter:
                self._painter.drawText(
                    QtCore.QPointF(
                        (-contentPixelRect.width() / 2) - (leftPadding / 2),
                        contentPixelRect.height()),
                    text)
            elif format == StringAlignment.BottomRight:
                self._painter.drawText(
                    QtCore.QPointF(
                        -contentPixelRect.width() - leftPadding,
                        contentPixelRect.height()),
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
        qtColor = QtGui.QColor(pen.color)
        qtStyle = QtGraphics._DashStyleMap[pen.dashStyle]
        qtPen = QtGui.QPen(qtColor, pen.width, qtStyle)
        if qtStyle == QtCore.Qt.PenStyle.CustomDashLine:
            qtPen.setDashPattern(pen.customDashPattern)
        return qtPen

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

    def _convertPath(self, path: AbstractPath) -> QtGui.QPolygonF:
        return QtGui.QPolygonF(self._convertPoints(path.points))

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

        self._viewCenterMapPos = PointF(0, 0) # TODO: I think this is actually in world/absolute coordinates
        self._tileSize = Size(self.width(), self.height())
        self._scale = MapHackView._DefaultScale
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
        self._mapLabelCache = MapLabelCache(basePath='./data/map/')
        self._worldLabelCache = WorldLabelCache(basePath='./data/map/')
        self._styleCache = DefaultStyleCache(basePath='./data/map/')
        WorldHelper.loadData(basePath='./data/map/') # TODO: Not sure where this should live
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

                pr = None
                if False:
                    pr = cProfile.Profile()
                    pr.enable()

                self._renderer.render()

                if pr:
                    pr.disable()
                    s = io.StringIO()
                    sortby = SortKey.TIME
                    #sortby = SortKey.CUMULATIVE
                    ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
                    ps.print_stats()
                    print(s.getvalue())
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
            mapLabelCache=self._mapLabelCache,
            worldLabelCache=self._worldLabelCache,
            styleCache=self._styleCache,
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


def _installDirectory() -> str:
    return os.path.dirname(os.path.realpath(__file__))

def _applicationDirectory() -> str:
    if os.name == 'nt':
        return os.path.join(os.getenv('APPDATA'), app.AppName)
    else:
        return os.path.join(pathlib.Path.home(), '.' + app.AppName.lower())

if __name__ == "__main__":
    application = QtWidgets.QApplication([])

    installDir = _installDirectory()
    application.setWindowIcon(QtGui.QIcon(os.path.join(installDir, 'icons', 'autojimmy.ico')))

    appDir = _applicationDirectory()
    os.makedirs(appDir, exist_ok=True)

    logDirectory = os.path.join(appDir, 'logs')
    app.setupLogger(logDir=logDirectory, logFile='autojimmy.log')
    # Log version before setting log level as it should always be logged
    logging.info(f'{app.AppName} v{app.AppVersion}')

    try:
        locale.setlocale(locale.LC_ALL, '')
    except Exception as ex:
        logging.warning('Failed to set default locale', exc_info=ex)

    # Set configured log level immediately after configuration has been setup
    logLevel = app.Config.instance().logLevel()
    try:
        app.setLogLevel(logLevel)
    except Exception as ex:
        logging.warning('Failed to set log level', exc_info=ex)

    installMapsDir = os.path.join(installDir, 'data', 'map')
    overlayMapsDir = os.path.join(appDir, 'map')
    customMapsDir = os.path.join(appDir, 'custom_map')
    travellermap.DataStore.setSectorDirs(
        installDir=installMapsDir,
        overlayDir=overlayMapsDir,
        customDir=customMapsDir)

    traveller.WorldManager.setMilieu(milieu=travellermap.Milieu.M1105)
    traveller.WorldManager.instance().loadSectors()

    gui.configureAppStyle(application)

    window = MyWidget()
    window.show()
    application.exec_()
