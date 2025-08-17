import enum
import cartographer
import travellermap
import typing

# TODO: I think I want to do some reshuffling so this isn't needed
# 1. Move WorldManager, World, Sector & Subsector into a new universe namespace
#   - Probably other stuff as well (Borders, Allegiances etc)
#   - Basically I want to get all the higher level universe related stuff into it's own namespace
# 2. Move what is currently in the travellermap namespace into what is left of the traveller namespace
import traveller

# TODO:I think this is a rough order of attack
# 1. Update WorldCache to use AbstractUniverse & AbstractWorld to populate WorldInfo.
#   - This will need AbstractUniverse to wrap WorldManager adn AllegianceManger
# 2. Update SectorCache to use AbstractUniverse & AbstractSector to generate the sector data
# 3. Update LabelCache to use AbstractUniverse (it has one call to WorldManager)
# 4. Update Selector to use AbstractUniverse & AbstractWorld/AbstractSector/AbstractSubsector

# TODO: While I'm sorting out the interfaces these abstract classes are going to have a
# real implementation as it will be much easier to test. Once I'm finished I'll split
# the implementation out from the abstract classes.

class AbstractWorld(object):
    def __init__(self, world: traveller.World) -> None:
        self._world = world

    def hex(self) -> travellermap.HexPosition:
        return self._world.hex()

    def name(self) -> typing.Optional[str]:
        return self._world.name() if not self._world.isNameGenerated() else None

    def uwp(self) -> traveller.UWP:
        return self._world.uwp()

    def population(self) -> int:
        return self._world.population()

    def zone(self) -> typing.Optional[traveller.ZoneType]:
        return self._world.zone()

    def importance(self) -> int:
        return self._world.importance()

    def isAnomaly(self) -> bool:
        return self._world.isAnomaly()

    def allegiance(self) -> str:
        return self._world.allegiance()

    def legacyAllegiance(self) -> typing.Optional[str]:
        return traveller.AllegianceManager.instance().legacyCode(
            milieu=self._world.milieu(),
            code=self._world.allegiance())

    def basesAllegiance(self) -> typing.Optional[str]:
        return traveller.AllegianceManager.instance().basesCode(
            milieu=self._world.milieu(),
            code=self._world.allegiance())

    def bases(self) -> traveller.Bases:
        return self._world.bases()

    def remarks(self) -> traveller.Remarks:
        return self._world.remarks()

    def hasWaterRefuelling(self) -> bool:
        return self._world.hasWaterRefuelling()

    def hasGasGiantRefuelling(self) -> bool:
        return self._world.hasGasGiantRefuelling()

    # NOTE: It's important that different instances of this class wrapping
    # the same object are seen as the same. This allows the the universe
    # implementation to discard instances of the wrapper that it doesn't
    # need and recreate them later without worrying about caches in the
    # renderer getting messed up
    def __hash__(self) -> int:
        return self._world.__hash__()

    def __eq__(self, other: typing.Any) -> bool:
        if isinstance(other, AbstractWorld):
            return self._world == other._world
        return False # TODO: Should this be not implemented?

class AbstractSubsector(object):
    def AbstractSubsector(self, subsector: traveller.Subsector) -> None:
        self._subsector = subsector

    def name(self) -> str:
        return self._subsector.name()

    # NOTE: It's important that different instances of this class wrapping
    # the same object are seen as the same. This allows the the universe
    # implementation to discard instances of the wrapper that it doesn't
    # need and recreate them later without worrying about caches in the
    # renderer getting messed up
    def __hash__(self) -> int:
        return self._subsector.__hash__()

    def __eq__(self, other: typing.Any) -> bool:
        if isinstance(other, AbstractSubsector):
            return self._subsector == other._subsector
        return False # TODO: Should this be not implemented?

class AbstractSector(object):
    def AbstractSubsector(self, sector: traveller.Sector) -> None:
        self._sector = sector

    def name(self) -> str:
        return self._sector.name()

    # NOTE: It's important that different instances of this class wrapping
    # the same object are seen as the same. This allows the the universe
    # implementation to discard instances of the wrapper that it doesn't
    # need and recreate them later without worrying about caches in the
    # renderer getting messed up
    def __hash__(self) -> int:
        return self._sector.__hash__()

    def __eq__(self, other: typing.Any) -> bool:
        if isinstance(other, AbstractSector):
            return self._sector == other._sector
        return False # TODO: Should this be not implemented?

class AbstractUniverse(object):
    def __init__(self) -> None:
        # TODO: Need to limit the number of wrappers maintained at any one time
        self._worldWrappers: typing.Mapping[travellermap.HexPosition, AbstractWorld] = {}

    def worldAt(
            self,
            milieu: travellermap.Milieu,
            hex: travellermap.HexPosition
            ) -> typing.Optional[AbstractWorld]:
        key = (milieu, hex)
        wrapper = self._worldWrappers.get(key)
        if not wrapper:
            world = traveller.WorldManager.instance().worldByPosition(
                milieu=milieu,
                hex=hex)
            wrapper = AbstractWorld(world=world)
            self._worldWrappers[key] = wrapper
        return wrapper

class AbstractPointList(object):
    def points(self) -> typing.Sequence[cartographer.PointF]:
        raise RuntimeError(f'{type(self)} is derived from AbstractPointList so must implement points')

    def bounds(self) -> cartographer.RectangleF:
        raise RuntimeError(f'{type(self)} is derived from AbstractPointList so must implement bounds')

    def translate(self, dx: float, dy: float) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractPointList so must implement translate')

    def copyFrom(self, other: 'AbstractPointList') -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractPointList so must implement copyFrom')

class AbstractPath(object):
    def points(self) -> typing.Sequence[cartographer.PointF]:
        raise RuntimeError(f'{type(self)} is derived from AbstractPath so must implement points')

    def closed(self) -> bool:
        raise RuntimeError(f'{type(self)} is derived from AbstractPath so must implement closed')

    def bounds(self) -> cartographer.RectangleF:
        raise RuntimeError(f'{type(self)} is derived from AbstractPath so must implement bounds')

    def translate(self, dx: float, dy: float) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractPath so must implement translate')

    def copyFrom(self, other: 'AbstractPath') -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractPath so must implement copyFrom')

class AbstractSpline(object):
    def points(self) -> typing.Sequence[cartographer.PointF]:
        raise RuntimeError(f'{type(self)} is derived from AbstractSpline so must implement points')

    def closed(self) -> bool:
        raise RuntimeError(f'{type(self)} is derived from AbstractSpline so must implement closed')

    def bounds(self) -> cartographer.RectangleF:
        raise RuntimeError(f'{type(self)} is derived from AbstractSpline so must implement bounds')

    def translate(self, dx: float, dy: float) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractSpline so must implement translate')

    def copyFrom(self, other: 'AbstractSpline') -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractSpline so must implement copyFrom')

class AbstractMatrix(object):
    def m11(self) -> float:
        raise RuntimeError(f'{type(self)} is derived from AbstractMatrix so must implement m11')

    def m12(self) -> float:
        raise RuntimeError(f'{type(self)} is derived from AbstractMatrix so must implement m12')

    def m21(self) -> float:
        raise RuntimeError(f'{type(self)} is derived from AbstractMatrix so must implement m21')

    def m22(self) -> float:
        raise RuntimeError(f'{type(self)} is derived from AbstractMatrix so must implement m22')

    def offsetX(self) -> float:
        raise RuntimeError(f'{type(self)} is derived from AbstractMatrix so must implement offsetX')

    def offsetY(self) -> float:
        raise RuntimeError(f'{type(self)} is derived from AbstractMatrix so must implement offsetY')

    def isIdentity(self) -> bool:
        raise RuntimeError(f'{type(self)} is derived from AbstractMatrix so must implement isIdentity')

    def invert(self) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractMatrix so must implement invert')

    def rotatePrepend(self, degrees: float, center: cartographer.PointF) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractMatrix so must implement rotatePrepend')

    def scalePrepend(self, sx: float, sy: float) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractMatrix so must implement scalePrepend')

    def translatePrepend(self, dx: float, dy: float) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractMatrix so must implement translatePrepend')

    def prepend(self, matrix: 'AbstractMatrix') -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractMatrix so must implement prepend')

    def transform(self, point: cartographer.PointF) -> cartographer.PointF:
        raise RuntimeError(f'{type(self)} is derived from AbstractMatrix so must implement transform')

class AbstractBrush(object):
    def colour(self) -> str:
        raise RuntimeError(f'{type(self)} is derived from AbstractBrush so must implement colour')

    def setColour(self, colour: str) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractBrush so must implement setColour')

    def copyFrom(self, other: 'AbstractBrush') -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractBrush so must implement copyFrom')

class AbstractPen(object):
    def colour(self) -> str:
        raise RuntimeError(f'{type(self)} is derived from AbstractPen so must implement colour')

    def setColour(self, colour: str) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractPen so must implement setColour')

    def width(self) -> float:
        raise RuntimeError(f'{type(self)} is derived from AbstractPen so must implement width')

    def setWidth(self, width: float) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractPen so must implement setWidth')

    def style(self) -> cartographer.LineStyle:
        raise RuntimeError(f'{type(self)} is derived from AbstractPen so must implement style')

    def setStyle(self, style: cartographer.LineStyle, pattern: typing.Optional[typing.List[float]] = None) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractPen so must implement setStyle')

    def pattern(self) -> typing.Optional[typing.Sequence[float]]:
        raise RuntimeError(f'{type(self)} is derived from AbstractPen so must implement pattern')

    def setPattern(self, pattern: typing.Sequence[float]) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractPen so must implement setPattern')

    def tip(self) -> cartographer.PenTip:
        raise RuntimeError(f'{type(self)} is derived from AbstractPen so must implement tip')

    def setTip(self, tip: cartographer.PenTip) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractPen so must implement setTip')

    def copyFrom(self, other: 'AbstractPen') -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractPen so must implement copyFrom')

class AbstractImage(object):
    def width(self) -> int:
        raise RuntimeError(f'{type(self)} is derived from AbstractImage so must implement width')

    def height(self) -> int:
        raise RuntimeError(f'{type(self)} is derived from AbstractImage so must implement height')

class AbstractFont(object):
    def family(self) -> str:
        raise RuntimeError(f'{type(self)} is derived from AbstractFont so must implement family')

    def emSize(self) -> float:
        raise RuntimeError(f'{type(self)} is derived from AbstractFont so must implement emSize')

    def style(self) -> cartographer.FontStyle:
        raise RuntimeError(f'{type(self)} is derived from AbstractFont so must implement style')

    def pointSize(self) -> float:
        raise RuntimeError(f'{type(self)} is derived from AbstractFont so must implement pointSize')

    def lineSpacing(self) -> float:
        raise RuntimeError(f'{type(self)} is derived from AbstractFont so must implement lineSpacing')

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

    def supportsWingdings(self) -> bool:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement supportsWingdings')

    def createPointList(
            self,
            points: typing.Sequence[cartographer.PointF]
            ) -> AbstractPointList:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement createPointList')

    def copyPointList(self, other: AbstractPointList) -> AbstractPointList:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement copyPointList')

    def createPath(
            self,
            points: typing.Sequence[cartographer.PointF],
            closed: bool
            ) -> AbstractPath:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement createPath')

    def copyPath(self, other: AbstractPath) -> AbstractPath:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement copyPath')

    def createSpline(
            self,
            points: typing.Sequence[cartographer.PointF],
            tension: float,
            closed: bool
            ) -> AbstractSpline:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement createSpline')

    def copySpline(self, other: AbstractSpline) -> AbstractSpline:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement copySpline')

    def createIdentityMatrix(self) -> AbstractMatrix:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement createIdentityMatrix')

    def createMatrix(
            self,
            m11: float,
            m12: float,
            m21: float,
            m22: float,
            dx: float,
            dy: float
            ) -> AbstractMatrix:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement createMatrix')

    def copyMatrix(self, other: AbstractMatrix) -> AbstractMatrix:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement copyMatrix')

    def createBrush(self, colour: str = '') -> AbstractBrush:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement createBrush')

    def copyBrush(self, other: AbstractBrush) -> AbstractBrush:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement copyBrush')

    def createPen(
            self,
            colour: str = '',
            width: float = 1,
            style: cartographer.LineStyle = cartographer.LineStyle.Solid,
            pattern: typing.Optional[typing.Sequence[float]] = None,
            tip: cartographer.PenTip = cartographer.PenTip.Flat
            ) -> AbstractPen:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement createPen')

    def copyPen(self, other: AbstractPen) -> AbstractPen:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement copyPen')

    def createImage(self, data: bytes) -> AbstractImage:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement createImage')

    def createFont(
            self,
            family: str,
            emSize: float,
            style: cartographer.FontStyle = cartographer.FontStyle.Regular
            ) -> AbstractFont:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement createFont')

    def setSmoothingMode(self, mode: SmoothingMode) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement setSmoothingMode')

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

    def intersectClipPath(self, clip: AbstractPath) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement intersectClipPath')

    def intersectClipRect(self, rect: cartographer.RectangleF) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement intersectClipRect')

    def drawPoint(self, point: cartographer.PointF, pen: AbstractPen) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawPoint')

    def drawPoints(self, points: AbstractPointList, pen: AbstractPen) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawPoints')

    def drawLine(
            self,
            pt1: cartographer.PointF,
            pt2: cartographer.PointF,
            pen: AbstractPen
            ) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawLine')

    def drawLines(
            self,
            points: AbstractPointList,
            pen: AbstractPen
            ) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawLines')

    def drawPath(
            self,
            path: AbstractPath,
            pen: typing.Optional[AbstractPen] = None,
            brush: typing.Optional[AbstractBrush] = None
            ) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawPath')

    def drawRectangle(
            self,
            rect: cartographer.RectangleF,
            pen: typing.Optional[AbstractPen] = None,
            brush: typing.Optional[AbstractBrush] = None
            ) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawRectangle')

    def drawEllipse(
            self,
            rect: cartographer.RectangleF,
            pen: typing.Optional[AbstractPen] = None,
            brush: typing.Optional[AbstractBrush] = None
            ) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawEllipse')

    def drawArc(
            self,
            rect: cartographer.RectangleF,
            startDegrees: float,
            sweepDegrees: float,
            pen: AbstractPen
            ) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawArc')

    def drawCurve(
            self,
            spline: AbstractSpline,
            pen: typing.Optional[AbstractPen] = None,
            brush: typing.Optional[AbstractBrush] = None
            ) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawCurve')

    def drawImage(self, image: AbstractImage, rect: cartographer.RectangleF) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawImage')

    def drawImageAlpha(self, alpha: float, image: AbstractImage, rect: cartographer.RectangleF) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawImageAlpha')

    def measureString(self, text: str, font: AbstractFont) -> typing.Tuple[float, float]: # (width, height)
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement measureString')

    def drawString(self, text: str, font: AbstractFont, brush: AbstractBrush, x: float, y: float, format: cartographer.TextAlignment) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawString')

    def save(self) -> AbstractGraphicsState:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement save')

    def restore(self) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement restore')
