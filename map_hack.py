from PyQt5 import QtWidgets, QtCore, QtGui
import PIL.Image, PIL.ImageDraw, PIL.ImageFont
import os
import gui
import io
import common
import typing
import enum
import math
import numpy
import travellermap

class StringAlignment(enum.Enum):
    Baseline = 0
    Centered = 1
    TopLeft = 2
    TopCenter = 3
    TopRight = 4
    CenterLeft = 5

class DashStyle(enum.Enum):
    Solid = 0
    Dot = 1
    Dash = 2
    DashDot = 3
    DashDotDot = 4
    Custom = 5

class FontStyle(enum.IntEnum):
    Regular = 0x0
    Bold = 0x1
    Italic = 0x2
    Underline = 0x4
    Strikeout = 0x8

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

class MapOptions(enum.IntEnum):
    SectorGrid = 0x0001,
    SubsectorGrid = 0x0002,

    SectorsSelected = 0x0004,
    SectorsAll = 0x0008,
    #SectorsMask = SectorsSelected | SectorsAll,

    BordersMajor = 0x0010,
    BordersMinor = 0x0020,
    #BordersMask = BordersMajor | BordersMinor,

    NamesMajor = 0x0040,
    NamesMinor = 0x0080,
    #NamesMask = NamesMajor | NamesMinor,

    WorldsCapitals = 0x0100,
    WorldsHomeworlds = 0x0200,
    #WorldsMask = WorldsCapitals | WorldsHomeworlds,

    RoutesSelectedDeprecated = 0x0400,

    PrintStyleDeprecated = 0x0800,
    CandyStyleDeprecated = 0x1000,
    #StyleMaskDeprecated = PrintStyleDeprecated | CandyStyleDeprecated,

    ForceHexes = 0x2000,
    WorldColors = 0x4000,
    FilledBorders = 0x8000

class Size(object):
    def __init__(self, width: int, height: int):
        self.width = int(width)
        self.height = int(height)

    def __eq__(self, other: typing.Any) -> bool:
        if isinstance(other, Size):
            return self.width == other.width and self.height == other.height
        return super().__eq__(other)

class SizeF(object):
    def __init__(self, width: float, height: float):
        self.width = width
        self.height = height

    def __eq__(self, other: typing.Any) -> bool:
        if isinstance(other, SizeF):
            return self.width == other.width and self.height == other.height
        return super().__eq__(other)

class PointF(object):
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y

    def __eq__(self, other: typing.Any) -> bool:
        if isinstance(other, PointF):
            return self.x == other.x and self.y == other.y
        return super().__eq__(other)

class RectangleF(object):
    def __init__(self, x: float, y: float, height: float, width: float):
        self.x = x
        self.y = y
        self.height = height
        self.width = width

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

    def __eq__(self, other: typing.Any) -> bool:
        if isinstance(other, RectangleF):
            return self.x == other.x and self.y == other.y and\
                self.height == other.height and self.width == other.width
        return super().__eq__(other)

class AbstractPen(object):
    def __init__(self, colour: str, width: float = 1):
        self.colour = colour
        self.width = width
        self.dashStyle = DashStyle.Solid
        self.customDashPattern: typing.Optional[typing.List[float]] = None

class AbstractBrush(object):
    def __init__(self, colour: str):
        self.colour = colour

class AbstractFont(object):
    def __init__(self, families: str, emSize: float, style: FontStyle, units: GraphicsUnit):
        pass

class AbstractMatrix(object):
    _IdentityMatrix = numpy.identity(3)

    @typing.overload
    def __init__(self) -> None: ...
    @typing.overload
    def __init__(self, other: 'AbstractMatrix') -> None: ...
    @typing.overload
    def __init__(self, m11: float, m12: float, m21: float, m22: float, dx: float, dy: float) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        if not args and not kwargs:
            self._matrix = AbstractMatrix._IdentityMatrix.copy()
        elif len(args) + len(kwargs) == 1:
            other = args[0] if len(args) > 0 else kwargs['other']
            if not isinstance(other, AbstractMatrix):
                raise TypeError('The other parameter must be an AbstractMatrix')
            assert(isinstance(other, AbstractMatrix))
            self._matrix = other.numpyMatrix().copy()
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

        self._matrix = numpy.dot(self._matrix, rotationMatrix)

    def scalePrepend(self, sx: float, sy: float) -> None:
        scalingMatrix = AbstractMatrix._createNumpyMatrix(
            m11=sx,
            m12=0,
            m21=0,
            m22=sy,
            dx=0,
            dy=0)

        self._matrix = numpy.dot(self._matrix, scalingMatrix)

    def translatePrepend(self, dx: float, dy: float) -> None:
        translationMatrix = AbstractMatrix._createNumpyMatrix(
            m11=1,
            m12=0,
            m21=0,
            m22=1,
            dx=dx,
            dy=dy)

        self._matrix = numpy.dot(self._matrix, translationMatrix)

    def prepend(self, matrix: 'AbstractMatrix') -> None:
        self._matrix = numpy.dot(self._matrix, matrix.numpyMatrix())

    def numpyMatrix(self) -> numpy.matrix:
        return self._matrix

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

class AbstractPath(object):
    class PointFlag(enum.IntFlag):
        # The starting point
        Start = 0
        # A line segment.
        Line = 1
        # A default Bézier curve.
        Bezier = 3
        # A mask point.
        PathTypeMask = 7
        # The corresponding segment is dashed.
        DashMode = 0x10,
        # A path marker.
        PathMarker = 0x20,
        # The endpoint of a subpath.
        CloseSubpath = 0x80,
        # A cubic Bézier curve.
        Bezier3 = 3

    def __init__(
            self,
            points: typing.Iterable[PointF],
            flags: typing.Iterable[PointFlag]
            ):
        pass

class AbstractImage(object):
    def __init__(self, path: str, url: str):
        pass

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
    def rotateTransform(self, angle: float) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement rotateTransform')
    def multiplyTransform(self, matrix: AbstractMatrix) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement multiplyTransform')

    # TODO: This was an overload of intersectClip in traveller map code
    def intersectClipPath(self, path: AbstractPath) -> None:
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
    def drawArc(self, pen: AbstractPen, rect: RectangleF, startAngle: float, sweepAngle: float) -> None:
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

class StyleSheet(object):
    class StyleElement(object):
        def __init__(self):
            self.visible = False
            self.fillColour = '#000000'
            self.content = ''
            self.pen = AbstractPen('#000000')
            self.textColour = '#000000'
            self.textHighlightColor = '#000000'

            # TODO: Still to fill out
            self.textStyle = None
            self.textBackgroundStyle = None
            self.fontInfo = None
            self.smallFontInfo = None
            self.mediumFontInfo = None
            self.largeFontInfo = None
            self.position = None
            self.font = None
            self.smallFont = None
            self.mediumFont = None
            self.largeFont = None

    def __init__(
            self,
            scale: float
            ):
        self._scale = scale

        self.hexStyle = HexStyle.Hex
        self.parsecGrid = StyleSheet.StyleElement()

        self._handleConfigUpdate()

    @property
    def scale(self) -> float:
        return self._scale
    @scale.setter
    def scale(self, value: float) -> None:
        self._scale = value
        self._handleConfigUpdate()

    def _handleConfigUpdate(self) -> None:
        onePixel = 1.0 / self.scale

        self.parsecGrid.pen = AbstractPen('#FF0000', onePixel)

class RenderContext(object):
    _HexEdge = math.tan(math.pi / 6) / 4 / travellermap.ParsecScaleX

    def __init__(
            self,
            graphics: AbstractGraphics,
            tileRect: RectangleF,
            scale: float,
            styles: StyleSheet,
            options: MapOptions,
            tileSize: Size
            ) -> None:
        self._graphics = graphics
        self._tileRect = tileRect
        self._scale = scale
        self._options = options
        self._styles = styles
        self._tileSize = tileSize
        self._updateSpaceTransforms()

    def setTileRect(self, rect: RectangleF) -> None:
        self._tileRect = rect
        self._updateSpaceTransforms()

    def setScale(self, scale: float) -> None:
        self._scale = scale
        self._updateSpaceTransforms()

    def render(self) -> None:
        with self._graphics.save():
            self._graphics.multiplyTransform(self._imageSpaceToWorldSpace)
            self._renderHexGrid()

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

    def _renderHexGrid(self) -> None:
        """
        if (!styles.parsecGrid.visible)
            return;
        """

        self._graphics.SmoothingMode = AbstractGraphics.SmoothingMode.HighQuality

        parsecSlop = 1

        hx = int(math.floor(self._tileRect.x))
        hw = int(math.ceil(self._tileRect.width))
        hy = int(math.floor(self._tileRect.y))
        hh = int(math.ceil(self._tileRect.height))

        pen = self._styles.parsecGrid.pen
        """
        styles.parsecGrid.pen.Apply(ref pen);
        """

        if self._styles.hexStyle == HexStyle.Square:
            """
            for (int px = hx - parsecSlop; px < hx + hw + parsecSlop; px++)
            {
                float yOffset = ((px % 2) != 0) ? 0.0f : 0.5f;
                for (int py = hy - parsecSlop; py < hy + hh + parsecSlop; py++)
                {
                    // TODO: use RenderUtil.(Square|Hex)Edges(X|Y) arrays
                    const float inset = 0.1f;
                    graphics.DrawRectangle(pen, px + inset, py + inset + yOffset, 1 - inset * 2, 1 - inset * 2);
                }
            }
            """
            pass
        elif self._styles.hexStyle == HexStyle.Hex:
            points = [None] * 4
            for px in range(hx - parsecSlop, hx + hw + parsecSlop):
                yOffset = 0 if ((px % 2) != 0) else 0.5
                for py in range(hy - parsecSlop, hy + hh + parsecSlop):
                    points[0] = PointF(px + -RenderContext._HexEdge, py + 0.5 + yOffset)
                    points[1] = PointF(px + RenderContext._HexEdge, py + 1.0 + yOffset)
                    points[2] = PointF(px + 1.0 - RenderContext._HexEdge, py + 1.0 + yOffset)
                    points[3] = PointF(px + 1.0 + RenderContext._HexEdge, py + 0.5 + yOffset)
                    self._graphics.drawLines(pen, points)

        """
        if (styles.numberAllHexes &&
            styles.worldDetails.HasFlag(WorldDetails.Hex))
        {
            solidBrush.Color = styles.hexNumber.textColor;
            for (int px = hx - parsecSlop; px < hx + hw + parsecSlop; px++)
            {
                float yOffset = ((px % 2) != 0) ? 0.0f : 0.5f;
                for (int py = hy - parsecSlop; py < hy + hh + parsecSlop; py++)
                {
                    Location loc = Astrometrics.CoordinatesToLocation(px + 1, py + 1);
                    string hex = styles.hexCoordinateStyle switch
                    {
                        HexCoordinateStyle.Sector => loc.HexString,
                        HexCoordinateStyle.Subsector => loc.SubsectorHexString,
                        _ => loc.HexString,
                    };
                    using (graphics.Save())
                    {
                        graphics.TranslateTransform(px + 0.5f, py + yOffset);
                        graphics.ScaleTransform(styles.hexContentScale / Astrometrics.ParsecScaleX, styles.hexContentScale / Astrometrics.ParsecScaleY);
                        graphics.DrawString(hex, styles.hexNumber.Font, solidBrush, 0, 0, Graphics.StringAlignment.TopCenter);
                    }
                }
            }
        }
        """

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

    def setPainter(self, painter: QtGui.QPainter) -> None:
        self._painter = painter

    def scaleTransform(self, scaleX: float, scaleY: float) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement scaleTransform')
    def translateTransform(self, dx: float, dy: float) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement translateTransform')
    def rotateTransform(self, angle: float) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement rotateTransform')
    def multiplyTransform(self, matrix: AbstractMatrix) -> None:
        self._painter.setTransform(
            self._painter.transform() * self._convertTransform(matrix))

    # TODO: This was an overload of intersectClip in traveller map code
    def intersectClipPath(self, path: AbstractPath) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement IntersectClip')
    # TODO: This was an overload of intersectClip in traveller map code
    def intersectClipRect(self, rect: RectangleF) -> None:
        raise RuntimeError(f'{type(self)} is derived from AbstractGraphics so must implement IntersectClip')

    # TODO: There was also an overload that takes 4 individual floats in the traveller map code
    def drawLine(self, pen: AbstractPen, pt1: PointF, pt2: PointF) -> None:
        self._painter.setPen(self._convertPen(pen))
        self._painter.drawLine(pt1.x, pt1.y, pt2.x, pt2.y)

    def drawLines(self, pen: AbstractPen, points: typing.Sequence[PointF]):
        self._painter.setPen(self._convertPen(pen))
        self._painter.drawLines([QtCore.QPointF(p.x, p.y) for p in points])

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
    def drawArc(self, pen: AbstractPen, rect: RectangleF, startAngle: float, sweepAngle: float) -> None:
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
        self._painter.save()
        return AbstractGraphicsState(graphics=self)
    def restore(self) -> None:
        self._painter.restore()

    def _convertPen(self, abstractPen: AbstractPen) -> QtGui.QPen:
        return QtGui.QPen(
            QtGui.QBrush(QtGui.QColor(abstractPen.colour)),
            abstractPen.width,
            QtGraphics._DashStyleMap[abstractPen.dashStyle])

    def _convertTransform(self, transform: AbstractMatrix) -> QtGui.QTransform:
        return QtGui.QTransform(
            transform.m11,
            transform.m12,
            transform.offsetX,
            transform.m21,
            transform.m22,
            transform.offsetY,
            0, 0, 1)

class MapHackView(QtWidgets.QGraphicsView):
    _MinScale = 0.0078125 # Math.Pow(2, -7);
    _MaxScale = 512 # Math.Pow(2, 9);
    _DefaultScale = 64

    _ZoomInScale = 1.25
    _ZoomOutScale = 0.8

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        scene = QtWidgets.QGraphicsScene()
        scene.setSceneRect(0, 0, self.width(), self.height())
        self.setScene(scene)
        self.resetTransform()

        self._x = 0
        self._y = 0
        self._tileSize = Size(256, 256)
        self._scale = 32

        self._tileRect = RectangleF(
            x=self._x * self._tileSize.width / (self._scale * travellermap.ParsecScaleX),
            y=self._y * self._tileSize.height / (self._scale * travellermap.ParsecScaleY),
            width=self._tileSize.width / (self._scale * travellermap.ParsecScaleX),
            height=self._tileSize.height / (self._scale * travellermap.ParsecScaleY))

        self._graphics = QtGraphics()
        self._styles = StyleSheet(
            scale=self._scale)
        self._renderer = RenderContext(
            graphics=self._graphics,
            tileRect=self._tileRect,
            scale=self._scale,
            styles=self._styles,
            options=0,
            tileSize=self._tileSize)

        self.setTransformationAnchor(
            QtWidgets.QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setDragMode(QtWidgets.QGraphicsView.DragMode.ScrollHandDrag)
        self.setCacheMode(QtWidgets.QGraphicsView.CacheModeFlag.CacheNone)
        self.setViewportUpdateMode(
            QtWidgets.QGraphicsView.ViewportUpdateMode.FullViewportUpdate)

    def clear(self) -> None:
        self._graphics = None

    def drawBackground(self, painter: QtGui.QPainter, rect: QtCore.QRectF) -> None:
        if not self._graphics:
            return super().drawBackground(painter, rect)

        painter.save()
        painter.resetTransform()
        self._graphics.setPainter(painter)
        self._renderer.render()
        painter.restore()

class MyWidget(gui.WindowWidget):
    _ImageFormat = 'PNG'

    def __init__(self):
        super().__init__(title='Map Hack', configSection='MapHack')
        self._widget = MapHackView()
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self._widget)

        self.setLayout(layout)


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    window = MyWidget()
    window.show()
    app.exec_()
