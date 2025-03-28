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
    NoStyle = 0
    Rectangle = 1
    Shadow = 2
    Outline = 3
    Filled = 4

class MicroBorderStyle(enum.Enum):
    Hex = 0
    Curve = 1

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

    DimUnofficial = 0x1000000
    ColorCodeSectorStatus = 0x2000000

    RoutesMajor = 0x10000000
    RoutesMinor = 0x20000000
    RoutesMask = RoutesMajor | RoutesMinor


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

    Micro_BordersBackground = 11
    Micro_BordersForeground = 12
    Micro_Routes = 13
    Micro_BorderExplicitLabels = 14

    Names_Sector = 15

    Macro_GovernmentRiftRouteNames = 16
    Macro_CapitalsAndHomeWorlds = 17
    Mega_GalaxyScaleLabels = 18

    Worlds_Background = 19
    Worlds_Foreground = 20
    Worlds_Overlays = 21

    #------------------------------------------------------------
    # Overlays
    #------------------------------------------------------------

    Overlay_DroyneChirperWorlds = 22
    Overlay_MinorHomeworlds = 23
    Overlay_AncientsWorlds = 24
    Overlay_ReviewStatus = 25

class WorldDetails(enum.IntFlag):
    NoDetails = 0

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

class PointF(object):
    @typing.overload
    def __init__(self) -> None: ...
    @typing.overload
    def __init__(self, other: 'PointF') -> None: ...
    @typing.overload
    def __init__(self, x: float, y: float) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        if not args and not kwargs:
            self._x = self._y = 0
        elif len(args) + len(kwargs) == 1:
            other = args[0] if len(args) > 0 else kwargs['other']
            if not isinstance(other, PointF):
                raise TypeError('The other parameter must be a PointF')
            self._x = other._x
            self._y = other._y
        else:
            self._x = args[0] if len(args) > 0 else kwargs['x']
            self._y = args[1] if len(args) > 1 else kwargs['y']

    def __eq__(self, other: typing.Any) -> bool:
        if isinstance(other, PointF):
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

    def point(self) -> typing.Tuple[float, float]:
        return (self._x, self._y)

    def setPoint(self, x: float, y: float) -> None:
        self._x = x
        self._y = y

    def translate(self, dx: float, dy: float) -> None:
        self._x += dx
        self._y += dy

class RectangleF(object):
    @typing.overload
    def __init__(self) -> None: ...
    @typing.overload
    def __init__(self, other: 'RectangleF') -> None: ...
    @typing.overload
    def __init__(self, x: float, y: float, width: float, height: float) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        if not args and not kwargs:
            self._x = self._y = self._width = self._height = 0
        elif len(args) + len(kwargs) == 1:
            other = args[0] if len(args) > 0 else kwargs['other']
            if not isinstance(other, RectangleF):
                raise TypeError('The other parameter must be a RectangleF')
            self._x = other._x
            self._y = other._y
            self._width = other._width
            self._height = other._height
        else:
            self._x = args[0] if len(args) > 0 else kwargs['x']
            self._y = args[1] if len(args) > 1 else kwargs['y']
            self._width = args[2] if len(args) > 2 else kwargs['width']
            self._height = args[3] if len(args) > 3 else kwargs['height']

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

    def rect(self) -> typing.Tuple[float, float, float, float]: # (x, y, width, height)
        return (self._x, self._y, self._width, self._height)

    def setRect(self, x: float, y: float, width: float, height: float) -> None:
        self._x = x
        self._y = y
        self._width = width
        self._height = height

    def translate(self, dx: float, dy: float) -> None:
        self._x += dx
        self._y += dy

    def copyFrom(self, other: 'RectangleF') -> None:
        self._x, self._y, self._width, self._height = other.rect()

    def left(self) -> float:
        return self.x()

    def right(self) -> float:
        return self.x() + self.width()

    def top(self) -> float:
        return self.y()

    def bottom(self) -> float:
        return self.y() + self.height()

    def centre(self) -> PointF:
        x, y, width, height = self.rect()
        return PointF(x + (width / 2), y + (height / 2))

    def inflate(self, x: float, y: float) -> None:
        currentX, currentY, currentWidth, currentHeight = self.rect()
        self.setRect(
            x=currentX - x,
            y=currentY - y,
            width=currentWidth + (x * 2),
            height=currentHeight + (y * 2))

    def intersectsWith(self, other: 'RectangleF') -> bool:
        selfX, selfY, selfWidth, selfHeight = self.rect()
        otherX, otherY, otherWidth, otherHeight = other.rect()
        return (otherX < selfX + selfWidth) and \
            (selfX < otherX + otherWidth) and \
            (otherY < selfY + selfHeight) and \
            (selfY < otherY + otherHeight)

    def __eq__(self, other: typing.Any) -> bool:
        if isinstance(other, RectangleF):
            selfX, selfY, selfWidth, selfHeight = self.rect()
            otherX, otherY, otherWidth, otherHeight = other.rect()
            return selfX == otherX and selfY == otherY and\
                selfHeight == otherHeight and selfWidth == otherWidth
        return super().__eq__(other)

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

class LabelStyle(object):
    @typing.overload
    def __init__(self) -> None: ...
    @typing.overload
    def __init__(
            self,
            rotation: float = 0,
            scale: typing.Optional[SizeF] = None,
            translation: typing.Optional[PointF] = None,
            uppercase: bool = False,
            wrap: bool = False
            ) -> None: ...

    def __init__(
            self,
            rotation: float = 0,
            scale: typing.Optional[SizeF] = None,
            translation: typing.Optional[PointF] = None,
            uppercase: bool = False,
            wrap: bool = False
            ) -> None:
        self.rotation = rotation
        self.scale = SizeF(scale) if scale else SizeF(width=1, height=1)
        self.translation = PointF(translation) if translation else PointF()
        self.uppercase = uppercase
        self.wrap = wrap

    def copyFrom(self, other: 'LabelStyle') -> None:
        self.rotation = other.rotation
        self.scale = SizeF(other.scale)
        self.translation = PointF(other.translation)
        self.uppercase = other.uppercase
        self.wrap = other.wrap
