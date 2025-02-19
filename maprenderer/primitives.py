from PyQt5 import QtGui # TODO: Get rid of the need for this include
import enum
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

class PenTip(enum.Enum):
    Flat = 0
    Square = 1
    Round = 2

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
    BordersMask = BordersMajor | BordersMinor

    NamesMajor = 0x0040
    NamesMinor = 0x0080
    NamesMask = NamesMajor | NamesMinor

    # TODO: Do I need these if they're deprecated?
    WorldsCapitals = 0x0100
    WorldsHomeworlds = 0x0200
    WorldsMask = WorldsCapitals | WorldsHomeworlds

    RoutesSelectedDeprecated = 0x0400

    ForceHexes = 0x2000
    WorldColors = 0x4000
    FilledBorders = 0x8000

    # These were added by me. In the Traveller Map code these come from
    # separate URL parameters rather than part of the map options

    PopulationOverlay = 0x10000
    ImportanceOverlay = 0x20000
    CapitalOverlay = 0x40000
    StellarOverlay = 0x80000

    AncientWorlds = 0x100000
    DroyneWorlds = 0x200000
    MinorHomeWorlds = 0x400000

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

# TODO: This is only created by StyleSheet now so should probably be moved there
class SizeF(object):
    @typing.overload
    def __init__(self) -> None: ...
    @typing.overload
    def __init__(self, other: 'SizeF') -> None: ...
    @typing.overload
    def __init__(self, width: float, height: float) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        if not args and not kwargs:
            self._width = self._height = 0
        elif len(args) + len(kwargs) == 1:
            other = args[0] if len(args) > 0 else kwargs['other']
            if not isinstance(other, SizeF):
                raise TypeError('The other parameter must be a SizeF')
            self._width = other._width
            self._height = other._height
        else:
            self._width = float(args[0] if len(args) > 0 else kwargs['width'])
            self._height = float(args[1] if len(args) > 1 else kwargs['height'])

    def __eq__(self, other: typing.Any) -> bool:
        if isinstance(other, SizeF):
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

# TODO: The F in this name is probably redundant as there is no non-F version
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

    def translate(self, dx: float, dy: float) -> None:
        self._x += dx
        self._y += dy

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

# TODO: I think this type is pointless as my rendering engine doesn't support
# gaps on paths or curves
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
    CloseSubpath = 0x80
    #
    # Summary:
    #     A cubic Bézier curve.
    Bezier3 = 3

class LabelStyle(object):
    @typing.overload
    def __init__(self) -> None: ...
    @typing.overload
    def __init__(
            self,
            rotation: float = 0,
            scale: typing.Optional[SizeF] = None,
            translation: typing.Optional[AbstractPointF] = None,
            uppercase: bool = False,
            wrap: bool = False
            ) -> None: ...

    def __init__(
            self,
            rotation: float = 0,
            scale: typing.Optional[SizeF] = None,
            translation: typing.Optional[AbstractPointF] = None,
            uppercase: bool = False,
            wrap: bool = False
            ) -> None:
        self.rotation = rotation
        self.scale = SizeF(scale) if scale else SizeF(width=1, height=1)
        self.translation = AbstractPointF(translation) if translation else AbstractPointF()
        self.uppercase = uppercase
        self.wrap = wrap

    def copyFrom(self, other: 'LabelStyle') -> None:
        self.rotation = other.rotation
        self.scale = SizeF(other.scale)
        self.translation = AbstractPointF(other.translation)
        self.uppercase = other.uppercase
        self.wrap = other.wrap
