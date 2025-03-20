import enum
import maprenderer
import typing

class AbstractPointList(object):
    def points(self) -> typing.Sequence[maprenderer.PointF]:
        raise RuntimeError(f'{type(self)} is derived from AbstractPointList so must implement points')
    def bounds(self) -> maprenderer.RectangleF:
        raise RuntimeError(f'{type(self)} is derived from AbstractPointList so must implement bounds')
    def translate(self, dx: float, dy: float) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractPointList so must implement translate')
    def copyFrom(self, other: 'AbstractPointList') -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractPointList so must implement copyFrom')

class AbstractPath(object):
    def points(self) -> typing.Sequence[maprenderer.PointF]:
        raise RuntimeError(f'{type(self)} is derived from AbstractPath so must implement points')
    def types(self) -> typing.Sequence[maprenderer.PathPointType]:
        raise RuntimeError(f'{type(self)} is derived from AbstractPath so must implement types')
    def closed(self) -> bool:
        raise RuntimeError(f'{type(self)} is derived from AbstractPath so must implement closed')
    def bounds(self) -> maprenderer.RectangleF:
        raise RuntimeError(f'{type(self)} is derived from AbstractPath so must implement bounds')
    def translate(self, dx: float, dy: float) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractPath so must implement translate')
    def copyFrom(self, other: 'AbstractPath') -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractPath so must implement copyFrom')

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
    def rotatePrepend(self, degrees: float, center: maprenderer.PointF) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractMatrix so must implement rotatePrepend')
    def scalePrepend(self, sx: float, sy: float) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractMatrix so must implement scalePrepend')
    def translatePrepend(self, dx: float, dy: float) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractMatrix so must implement translatePrepend')
    def prepend(self, matrix: 'AbstractMatrix') -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractMatrix so must implement prepend')
    def transform(self, point: maprenderer.PointF) -> maprenderer.PointF:
        raise RuntimeError(f'{type(self)} is derived from AbstractMatrix so must implement prepend')

class AbstractBrush(object):
    def color(self) -> str:
        raise RuntimeError(f'{type(self)} is derived from AbstractBrush so must implement color')
    def setColor(self, color: str) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractBrush so must implement setColor')
    def copyFrom(self, other: 'AbstractBrush') -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractBrush so must implement copyFrom')

class AbstractPen(object):
    def color(self) -> str:
        raise RuntimeError(f'{type(self)} is derived from AbstractPen so must implement color')
    def setColor(self, color: str) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractPen so must implement setColor')
    def width(self) -> float:
        raise RuntimeError(f'{type(self)} is derived from AbstractPen so must implement width')
    def setWidth(self, width: float) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractPen so must implement setWidth')
    def style(self) -> maprenderer.LineStyle:
        raise RuntimeError(f'{type(self)} is derived from AbstractPen so must implement style')
    def setStyle(self, style: maprenderer.LineStyle, pattern: typing.Optional[typing.List[float]] = None) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractPen so must implement setStyle')
    def pattern(self) -> typing.Optional[typing.Sequence[float]]:
        raise RuntimeError(f'{type(self)} is derived from AbstractPen so must implement pattern')
    def setPattern(self, pattern: typing.Sequence[float]) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractPen so must implement setPattern')
    def tip(self) -> maprenderer.PenTip:
        raise RuntimeError(f'{type(self)} is derived from AbstractPen so must implement tip')
    def setTip(self, tip: maprenderer.PenTip) -> None:
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
    def style(self) -> maprenderer.FontStyle:
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
            points: typing.Sequence[maprenderer.PointF]
            ) -> AbstractPointList:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement createPointList')
    def copyPointList(self, other: AbstractPointList) -> AbstractPointList:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement copyPointList')

    def createPath(
            self,
            points: typing.Sequence[maprenderer.PointF],
            types: typing.Sequence[maprenderer.PathPointType],
            closed: bool
            ) -> AbstractPath:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement createPath')
    def copyPath(self, other: AbstractPath) -> AbstractPath:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement copyPath')

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

    def createBrush(self, color: str = '') -> AbstractBrush:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement createBrush')
    def copyBrush(self, other: AbstractBrush) -> AbstractBrush:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement copyBrush')

    def createPen(
            self,
            color: str = '',
            width: float = 1,
            style: maprenderer.LineStyle = maprenderer.LineStyle.Solid,
            pattern: typing.Optional[typing.Sequence[float]] = None,
            tip: maprenderer.PenTip = maprenderer.PenTip.Flat
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
            style: maprenderer.FontStyle = maprenderer.FontStyle.Regular
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
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement IntersectClip')
    def intersectClipRect(self, rect: maprenderer.RectangleF) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement IntersectClip')

    def drawPoint(self, point: maprenderer.PointF, pen: AbstractPen) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawPoint')
    def drawPoints(self, points: AbstractPointList, pen: AbstractPen) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawPoints')

    def drawLine(
            self,
            pt1: maprenderer.PointF,
            pt2: maprenderer.PointF,
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
            rect: maprenderer.RectangleF,
            pen: typing.Optional[AbstractPen] = None,
            brush: typing.Optional[AbstractBrush] = None
            ) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawRectangle')

    def drawEllipse(
            self,
            rect: maprenderer.RectangleF,
            pen: typing.Optional[AbstractPen] = None,
            brush: typing.Optional[AbstractBrush] = None
            ) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawEllipse')

    def drawArc(
            self,
            rect: maprenderer.RectangleF,
            startDegrees: float,
            sweepDegrees: float,
            pen: AbstractPen
            ) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawArc')

    def drawImage(self, image: AbstractImage, rect: maprenderer.RectangleF) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawImage')
    def drawImageAlpha(self, alpha: float, image: AbstractImage, rect: maprenderer.RectangleF) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawImageAlpha')

    def measureString(self, text: str, font: AbstractFont) -> typing.Tuple[float, float]: # (width, height)
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement measureString')
    def drawString(self, text: str, font: AbstractFont, brush: AbstractBrush, x: float, y: float, format: maprenderer.TextAlignment) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawString')

    def save(self) -> AbstractGraphicsState:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement save')
    def restore(self) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement restore')
