import enum
import maprenderer
import typing

# TODO: This (and PointF) could do with an offsetX, offsetY functions as there
# are quite a few places that are having to do get x/y then set x/y with modifier
class AbstractRectangleF(object):
    def x(self) -> float:
        raise RuntimeError(f'{type(self)} is derived from AbstractRectangleF so must implement x')
    def setX(self, x: float) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractRectangleF so must implement setX')
    def y(self) -> float:
        raise RuntimeError(f'{type(self)} is derived from AbstractRectangleF so must implement y')
    def setY(self, y: float) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractRectangleF so must implement setY')
    def width(self) -> float:
        raise RuntimeError(f'{type(self)} is derived from AbstractRectangleF so must implement width')
    def setWidth(self, width: float) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractRectangleF so must implement setWidth')
    def height(self) -> float:
        raise RuntimeError(f'{type(self)} is derived from AbstractRectangleF so must implement height')
    def setHeight(self, height: float) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractRectangleF so must implement setHeight')
    def rect(self) -> typing.Tuple[int, int, int, int]: # (x, y, width, height)
        raise RuntimeError(f'{type(self)} is derived from AbstractRectangleF so must implement rect')
    def setRect(self, x: float, y: float, width: float, height: float) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractRectangleF so must implement setRect')
    def copyFrom(self, other: 'AbstractRectangleF') -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractRectangleF so must implement copyFrom')

    def left(self) -> float:
        return self.x()

    def right(self) -> float:
        return self.x() + self.width()

    def top(self) -> float:
        return self.y()

    def bottom(self) -> float:
        return self.y() + self.height()

    def centre(self) -> maprenderer.AbstractPointF:
        x, y, width, height = self.rect()
        return maprenderer.AbstractPointF(x + (width / 2), y + (height / 2))

    def inflate(self, x: float, y: float) -> None:
        currentX, currentY, currentWidth, currentHeight = self.rect()
        self.setRect(
            x=currentX - x,
            y=currentY - y,
            width=currentWidth + (x * 2),
            height=currentHeight + (y * 2))

    def intersectsWith(self, other: 'AbstractRectangleF') -> bool:
        selfX, selfY, selfWidth, selfHeight = self.rect()
        otherX, otherY, otherWidth, otherHeight = other.rect()
        return (otherX < selfX + selfWidth) and \
            (selfX < otherX + otherWidth) and \
            (otherY < selfY + selfHeight) and \
            (selfY < otherY + otherHeight)

    def __eq__(self, other: typing.Any) -> bool:
        if isinstance(other, AbstractRectangleF):
            selfX, selfY, selfWidth, selfHeight = self.rect()
            otherX, otherY, otherWidth, otherHeight = other.rect()
            return selfX == otherX and selfY == otherY and\
                selfHeight == otherHeight and selfWidth == otherWidth
        return super().__eq__(other)

class AbstractPath(object):
    def points(self) -> typing.Sequence[maprenderer.AbstractPointF]:
        raise RuntimeError(f'{type(self)} is derived from AbstractPath so must implement points')
    def types(self) -> typing.Sequence[maprenderer.PathPointType]:
        raise RuntimeError(f'{type(self)} is derived from AbstractPath so must implement types')
    def closed(self) -> bool:
        raise RuntimeError(f'{type(self)} is derived from AbstractPath so must implement closed')
    def bounds(self) -> AbstractRectangleF:
        raise RuntimeError(f'{type(self)} is derived from AbstractPath so must implement bounds')
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
    def rotatePrepend(self, degrees: float, center: maprenderer.AbstractPointF) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractMatrix so must implement rotatePrepend')
    def scalePrepend(self, sx: float, sy: float) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractMatrix so must implement scalePrepend')
    def translatePrepend(self, dx: float, dy: float) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractMatrix so must implement translatePrepend')
    def prepend(self, matrix: 'AbstractMatrix') -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractMatrix so must implement prepend')
    def transform(self, point: maprenderer.AbstractPointF) -> maprenderer.AbstractPointF:
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
    def style(self) -> float:
        raise RuntimeError(f'{type(self)} is derived from AbstractPen so must implement style')
    def setStyle(self, style: maprenderer.LineStyle, pattern: typing.Optional[typing.List[float]] = None) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractPen so must implement setStyle')
    def pattern(self) -> typing.Optional[typing.Sequence[float]]:
        raise RuntimeError(f'{type(self)} is derived from AbstractPen so must implement pattern')
    def setPattern(self, pattern: typing.Sequence[float]) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractPen so must implement setPattern')
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

    def createRectangle(self, x: float = 0, y: float = 0, width: float = 0, height: float = 0) -> AbstractRectangleF:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement createRectangle')
    def copyRectangle(self, other: AbstractRectangleF) -> AbstractRectangleF:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement copyRectangle')

    def createPath(
            self,
            points: typing.Sequence[maprenderer.AbstractPointF],
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
            pattern: typing.Optional[typing.Sequence[float]] = None
            ) -> AbstractPen:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement createPen')
    def copyPen(self, other: AbstractPen) -> AbstractPen:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement copyPen')

    def createImage(self, path: str) -> AbstractImage:
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
    def intersectClipRect(self, rect: AbstractRectangleF) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement IntersectClip')

    def drawPoint(self, pen: AbstractPen, point: maprenderer.AbstractPointF) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawPoint')

    # TODO: There was also an overload that takes 4 individual floats in the traveller map code
    def drawLine(self, pen: AbstractPen, pt1: maprenderer.AbstractPointF, pt2: maprenderer.AbstractPointF) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawLine')
    def drawLines(self, pen: AbstractPen, points: typing.Sequence[maprenderer.AbstractPointF]):
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawLines')
    # TODO: This was an overload of drawPath in the traveller map code
    def drawPathOutline(self, pen: AbstractPen, path: AbstractPath):
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawPathOutline')
    # TODO: This was an overload of drawPath in the traveller map code
    def drawPathFill(self, brush: AbstractBrush, path: AbstractPath):
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawPathFill')
    def drawCurve(self, pen: AbstractPen, points: typing.Sequence[maprenderer.AbstractPointF], tension: float = 0.5):
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawCurve')
    # TODO: This was an overload of drawClosedCurve in the traveller map code
    def drawClosedCurveOutline(self, pen: AbstractPen, points: typing.Sequence[maprenderer.AbstractPointF], tension: float = 0.5):
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawClosedCurveOutline')
    def drawClosedCurveFill(self, brush: AbstractBrush, points: typing.Sequence[maprenderer.AbstractPointF], tension: float = 0.5):
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawClosedCurveFill')
    # TODO: There was also an overload that takes 4 individual floats in the traveller map code
    def drawRectangleOutline(self, pen: AbstractPen, rect: AbstractRectangleF) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawRectangleOutline')
    # TODO: There was also an overload that takes 4 individual floats in the traveller map code
    def drawRectangleFill(self, brush: AbstractBrush, rect: AbstractRectangleF) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawRectangleFill')
    # TODO: This has changed quite a bit from the traveller map interface
    def drawEllipse(self, pen: typing.Optional[AbstractPen], brush: typing.Optional[AbstractBrush], rect: AbstractRectangleF):
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawEllipse')
    def drawArc(self, pen: AbstractPen, rect: AbstractRectangleF, startDegrees: float, sweepDegrees: float) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawArc')

    def drawImage(self, image: AbstractImage, rect: AbstractRectangleF) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawImage')
    def drawImageAlpha(self, alpha: float, image: AbstractImage, rect: AbstractRectangleF) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawImageAlpha')

    def measureString(self, text: str, font: AbstractFont) -> typing.Tuple[float, float]: # (width, height)
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement measureString')
    def drawString(self, text: str, font: AbstractFont, brush: AbstractBrush, x: float, y: float, format: maprenderer.TextAlignment) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement drawString')

    def save(self) -> AbstractGraphicsState:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement save')
    def restore(self) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement restore')
