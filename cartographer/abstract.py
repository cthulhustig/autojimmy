import astronomer
import enum
import cartographer
import typing

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

    def setStyle(self, style: cartographer.LineStyle, pattern: typing.Optional[typing.Sequence[float]] = None) -> None:
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

    def setWorldToImageTransform(self, matrix: AbstractMatrix) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement setWorldToImageTransform')

    def scaleTransformUniform(self, scaleXY: float) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement scaleTransformUniform')

    def scaleTransform(self, scaleX: float, scaleY: float) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement scaleTransform')

    def translateTransform(self, dx: float, dy: float) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement translateTransform')

    def rotateTransform(self, degrees: float) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement rotateTransform')

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

# TODO: Move SectorCache & WorldCache behind AbstractSelector so that it returns WorldInfo's and
# a new SectorInfo that contains all the precomputed information for the sector, including the
# points/paths currently managed by SectorCache
# - I'd probably want to create AbstractWorldInfo & AbstractSectorInfo for the AbstractSelector
# to return and the rendering code to use. This would allow custom implementations of where
# the info comes from which can be moved elsewhere. By the end of it I think I can remove the
# dependency on astronomer from the main rendering code barring some stuff from astrometrics
# - In RectSelector I'd need to duplicate code from WorldManager for finding sectors/world in an
# area. However, this should allow me to create a more optimised implementation
# - Updating the rendering code to only use WorldInfo isn't to bad as it's already accessing
# pretty much everything from the WorldInfo rather than the astronomer World. The only exception
# I can see is _worldStarProps which access the stellar information. I think I could solve this
# by moving what it calculates into the WorldCache code and having it store what the function
# returns on the WorldInfo. The main problem with WorldInfo is the rendering code is currently
# accessing its member variables directly and I'll need to update everything to use function
# calls to the new AbstractWorldInfo interface
# - Updating the rendering code to use SectorInfo is a bit more complicated as it currently
# accesses subsector names, regions, borders, labels, sector labels and tagging directly from
# the astronomer Sector object. I'd need to update it so it accesses ABSTRACT representations
# of these via the AbstractSectorInfo interface. Most stuff would just be a case of having the
# implementation for AbstractSectorInfo take the relevant info from the astronomer Sector.
# - By moving to use an AbstractWorldInfo & AbstractSectorInfo interface it means I could have
# the implementations of those interfaces hold references to the relevant astronomer object and
# just pass the abstract interface through to it to avoid holding copies of the data.
class AbstractSelector(object):
    def setRect(self, rect: cartographer.RectangleF) -> None:
        raise NotImplementedError(f'{type(self)} is derived from SelectorInterface so must implement setRect')

    def sectorSlop(self) -> float:
        raise NotImplementedError(f'{type(self)} is derived from SelectorInterface so must implement sectorSlop')

    def setSectorSlop(self, slop: float) -> None:
        raise NotImplementedError(f'{type(self)} is derived from SelectorInterface so must implement setSectorSlop')

    def worldSlop(self) -> float:
        raise NotImplementedError(f'{type(self)} is derived from SelectorInterface so must implement worldSlop')

    def setWorldSlop(self, slop: float) -> None:
        raise NotImplementedError(f'{type(self)} is derived from SelectorInterface so must implement setWorldSlop')

    def sectors(self, tight: bool = False) -> typing.Collection[astronomer.Sector]:
        raise NotImplementedError(f'{type(self)} is derived from SelectorInterface so must implement sectors')

    def worlds(self, tight: bool = False) -> typing.Collection[astronomer.World]:
        raise NotImplementedError(f'{type(self)} is derived from SelectorInterface so must implement worlds')

    def clearCaches(self) -> None:
        raise NotImplementedError(f'{type(self)} is derived from SelectorInterface so must implement clearCaches')