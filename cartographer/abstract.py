import enum
import cartographer
import multiverse
import typing

class AbstractWorld(object):
    def milieu(self) -> multiverse.Milieu:
        raise RuntimeError(f'{type(self)} is derived from AbstractWorld so must implement milieu')

    def hex(self) -> multiverse.HexPosition:
        raise RuntimeError(f'{type(self)} is derived from AbstractWorld so must implement hex')

    def name(self) -> typing.Optional[str]:
        raise RuntimeError(f'{type(self)} is derived from AbstractWorld so must implement name')

    def sector(self) -> 'AbstractSector':
        raise RuntimeError(f'{type(self)} is derived from AbstractWorld so must implement sector')

    def uwp(self) -> multiverse.UWP:
        raise RuntimeError(f'{type(self)} is derived from AbstractWorld so must implement uwp')

    def population(self) -> int:
        raise RuntimeError(f'{type(self)} is derived from AbstractWorld so must implement population')

    def zone(self) -> typing.Optional[multiverse.ZoneType]:
        raise RuntimeError(f'{type(self)} is derived from AbstractWorld so must implement zone')

    def isAnomaly(self) -> bool:
        raise RuntimeError(f'{type(self)} is derived from AbstractWorld so must implement isAnomaly')

    def allegiance(self) -> str:
        raise RuntimeError(f'{type(self)} is derived from AbstractWorld so must implement allegiance')

    def legacyAllegiance(self) -> typing.Optional[str]:
        raise RuntimeError(f'{type(self)} is derived from AbstractWorld so must implement legacyAllegiance')

    def basesAllegiance(self) -> typing.Optional[str]:
        raise RuntimeError(f'{type(self)} is derived from AbstractWorld so must implement basesAllegiance')

    def bases(self) -> multiverse.Bases:
        raise RuntimeError(f'{type(self)} is derived from AbstractWorld so must implement bases')

    def stellar(self) -> multiverse.Stellar:
        raise RuntimeError(f'{type(self)} is derived from AbstractWorld so must implement stellar')

    def remarks(self) -> multiverse.Remarks:
        raise RuntimeError(f'{type(self)} is derived from AbstractWorld so must implement remarks')

    def hasWaterRefuelling(self) -> bool:
        raise RuntimeError(f'{type(self)} is derived from AbstractWorld so must implement hasWaterRefuelling')

    def hasGasGiantRefuelling(self) -> bool:
        raise RuntimeError(f'{type(self)} is derived from AbstractWorld so must implement hasGasGiantRefuelling')

class AbstractSubsector(object):
    def milieu(self) -> multiverse.Milieu:
        raise RuntimeError(f'{type(self)} is derived from AbstractSubsector so must implement milieu')

    def index(self) -> multiverse.SubsectorIndex:
        raise RuntimeError(f'{type(self)} is derived from AbstractSubsector so must implement index')

    def sector(self) -> 'AbstractSector':
        raise RuntimeError(f'{type(self)} is derived from AbstractSubsector so must implement sector')

    def name(self) -> typing.Optional[str]:
        raise RuntimeError(f'{type(self)} is derived from AbstractSubsector so must implement name')

    def worlds(self) -> typing.Iterable[AbstractWorld]:
        raise RuntimeError(f'{type(self)} is derived from AbstractSubsector so must implement worlds')

    def worldHexes(self) -> typing.Iterable[multiverse.HexPosition]:
        raise RuntimeError(f'{type(self)} is derived from AbstractSubsector so must implement worldHexes')

class AbstractSector(object):
    def milieu(self) -> multiverse.Milieu:
        raise RuntimeError(f'{type(self)} is derived from AbstractSector so must implement milieu')

    def index(self) -> multiverse.SectorIndex:
        raise RuntimeError(f'{type(self)} is derived from AbstractSector so must implement index')

    def name(self) -> str:
        raise RuntimeError(f'{type(self)} is derived from AbstractSector so must implement name')

    # TODO: I really don't like this name (or the one on multiverse.Sector).
    # It can't be named label as that would get confused with the other
    # sector labels. Having a sector label has two effects.
    # - It will be used instead of the sector name when drawing sector names
    # - If rendering is set to show only selected sector names, sectors with
    #   labels will always have their label drawn even if not marked as
    #   selected.
    #       - Need to find out if there are any sectors that have a label but
    #         aren't marked as selected. If not then I can just return the
    #         sector label instead of the name
    def sectorLabel(self) -> typing.Optional[str]:
        raise RuntimeError(f'{type(self)} is derived from AbstractSector so must implement sectorLabel')

    # TODO: I really don't like the name of this function (or the equivalent
    # on multiverse.Sector). It's used to specify if a sector should have its
    # name drawn when drawing sector names is set to "only selected"
    def isSelected(self) -> bool:
        raise RuntimeError(f'{type(self)} is derived from AbstractSector so must implement isSelected')

    def tagging(self) -> multiverse.SectorTagging:
        raise RuntimeError(f'{type(self)} is derived from AbstractSector so must implement tagging')

    def worlds(self) -> typing.Iterable[AbstractWorld]:
        raise RuntimeError(f'{type(self)} is derived from AbstractSector so must implement worlds')

    def worldHexes(self) -> typing.Iterable[multiverse.HexPosition]:
        raise RuntimeError(f'{type(self)} is derived from AbstractSector so must implement worldHexes')

    # TODO: The region, border etc functions should use abstract types
    def regions(self) -> typing.Iterable[multiverse.Region]:
        raise RuntimeError(f'{type(self)} is derived from AbstractSector so must implement regions')

    def borders(self) -> typing.Iterable[multiverse.Border]:
        raise RuntimeError(f'{type(self)} is derived from AbstractSector so must implement borders')

    def routes(self) -> typing.Iterable[multiverse.Route]:
        raise RuntimeError(f'{type(self)} is derived from AbstractSector so must implement routes')

    def labels(self) -> typing.Iterable[multiverse.Label]:
        raise RuntimeError(f'{type(self)} is derived from AbstractSector so must implement labels')

class AbstractUniverse(object):
    def sectorAt(
            self,
            milieu: multiverse.Milieu,
            index: multiverse.SectorIndex,
            includePlaceholders: bool = False
            ) -> typing.Optional[AbstractSector]:
        raise RuntimeError(f'{type(self)} is derived from AbstractUniverse so must implement sectorAt')

    def worldAt(
            self,
            milieu: multiverse.Milieu,
            hex: multiverse.HexPosition,
            includePlaceholders: bool = False
            ) -> typing.Optional[AbstractWorld]:
        raise RuntimeError(f'{type(self)} is derived from AbstractUniverse so must implement worldAt')

    def sectorsInArea(
            self,
            milieu: multiverse.Milieu,
            ulHex: multiverse.HexPosition,
            lrHex: multiverse.HexPosition,
            includePlaceholders: bool = False
            ) -> typing.List[AbstractSector]:
        raise RuntimeError(f'{type(self)} is derived from AbstractUniverse so must implement sectorsInArea')

    def subsectorsInArea(
            self,
            milieu: multiverse.Milieu,
            ulHex: multiverse.HexPosition,
            lrHex: multiverse.HexPosition,
            includePlaceholders: bool = False
            ) -> typing.List[AbstractSubsector]:
        raise RuntimeError(f'{type(self)} is derived from AbstractUniverse so must implement subsectorsInArea')

    def worldsInArea(
            self,
            milieu: multiverse.Milieu,
            ulHex: multiverse.HexPosition,
            lrHex: multiverse.HexPosition,
            includePlaceholders: bool = False
            ) -> typing.List[AbstractWorld]:
        raise RuntimeError(f'{type(self)} is derived from AbstractUniverse so must implement worldsInArea')

    def sectorHexToPosition(
            self,
            milieu: multiverse.Milieu,
            sectorHex: str
            ) -> multiverse.HexPosition:
        raise RuntimeError(f'{type(self)} is derived from AbstractUniverse so must implement sectorHexToPosition')

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
