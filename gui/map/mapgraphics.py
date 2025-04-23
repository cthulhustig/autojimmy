import common
import gui
import math
import cartographer
import typing
from PyQt5 import QtCore, QtGui

class MapPointList(cartographer.AbstractPath):
    @typing.overload
    def __init__(self) -> None: ...
    @typing.overload
    def __init__(self, other: 'MapPath') -> None: ...
    @typing.overload
    def __init__(self, points: typing.Sequence[cartographer.PointF]) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        if len(args) == 1:
            arg = args[0]
            if isinstance(arg, MapPointList):
                # NOTE: This assumes the points method return a copy of
                # the list held by other not the list itself
                self._points = arg.points()
            else:
                self._points = list(arg)
        elif 'other' in kwargs:
            other = kwargs['other']
            if not isinstance(other, MapPointList):
                raise TypeError('The other parameter must be a MapPointList')
            self._points = list(other.points())
        else:
            self._points = list(kwargs['points'])

        # These are created on demand
        self._bounds: typing.Optional[cartographer.RectangleF] = None
        self._qtPolygon: typing.Optional[QtGui.QPolygonF] = None

    def points(self) -> typing.Sequence[cartographer.PointF]:
        return list(self._points)

    def bounds(self) -> cartographer.RectangleF:
        if self._bounds is None:
            minX = maxX = minY = maxY = None
            for point in self._points:
                if minX is None or point.x() < minX:
                    minX = point.x()
                if maxX is None or point.x() > maxX:
                    maxX = point.x()
                if minY is None or point.y() < minY:
                    minY = point.y()
                if maxY is None or point.y() > maxY:
                    maxY = point.y()
            self._bounds = cartographer.RectangleF(
                x=minX,
                y=minY,
                width=maxX - minX,
                height=maxY - minY)

        return cartographer.RectangleF(self._bounds)

    def translate(self, dx: float, dy: float) -> None:
        for point in self._points:
            point.translate(dx, dy)
        if self._bounds:
            self._bounds.translate(dx, dy)
        if self._qtPolygon:
            self._qtPolygon.translate(dx, dy)

    def copyFrom(self, other: 'MapPointList') -> None:
        # NOTE: This assumes the points method return a copy of
        # the list held by other not the list itself
        self._points = other.points()
        self._bounds = None # Calculate on demand
        self._qtPolygon = None

    def qtPolygon(self) -> QtGui.QPolygonF:
        if not self._qtPolygon:
            self._qtPolygon = QtGui.QPolygonF(
                [QtCore.QPointF(p.x(), p.y()) for p in self._points])
        return self._qtPolygon

class MapPath(cartographer.AbstractPath):
    @typing.overload
    def __init__(self) -> None: ...
    @typing.overload
    def __init__(self, other: 'MapPath') -> None: ...

    @typing.overload
    def __init__(
        self,
        points: typing.Sequence[cartographer.PointF],
        closed: bool) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        if not args and not kwargs:
            self._points: typing.List[cartographer.PointF] = []
            self._closed = False
        elif len(args) + len(kwargs) == 1:
            other = args[0] if len(args) > 0 else kwargs['other']
            if not isinstance(other, MapPath):
                raise TypeError('The other parameter must be a MapPath')
            # NOTE: This assumes the points and types methods return copies of
            # the lists held by other not the lists themselves
            self._points = other.points()
            self._closed = other.closed()
        else:
            self._points = list(args[0] if len(args) > 0 else kwargs['points'])
            self._closed = bool(args[1] if len(args) > 1 else kwargs['closed'])

        # These are created on demand
        self._bounds: typing.Optional[cartographer.RectangleF] = None
        self._qtPolygon: typing.Optional[QtGui.QPolygonF] = None

    def points(self) -> typing.Sequence[cartographer.PointF]:
        return list(self._points)

    def closed(self) -> bool:
        return self._closed

    def bounds(self) -> cartographer.RectangleF:
        if self._bounds is None:
            minX = maxX = minY = maxY = None
            for point in self._points:
                if minX is None or point.x() < minX:
                    minX = point.x()
                if maxX is None or point.x() > maxX:
                    maxX = point.x()
                if minY is None or point.y() < minY:
                    minY = point.y()
                if maxY is None or point.y() > maxY:
                    maxY = point.y()
            self._bounds = cartographer.RectangleF(
                x=minX,
                y=minY,
                width=maxX - minX,
                height=maxY - minY)

        return cartographer.RectangleF(self._bounds)

    def translate(self, dx: float, dy: float) -> None:
        for point in self._points:
            point.translate(dx, dy)
        if self._bounds:
            self._bounds.translate(dx, dy)
        if self._qtPolygon:
            self._qtPolygon.translate(dx, dy)

    def copyFrom(self, other: 'MapPath') -> None:
        # NOTE: This assumes the points methods return a copy of
        # the list held by other not the list itself
        self._points = other.points()
        self._closed = other.closed()
        self._bounds = None # Calculate on demand
        self._qtPolygon = None

    def qtPolygon(self) -> QtGui.QPolygonF:
        if not self._qtPolygon:
            self._qtPolygon = QtGui.QPolygonF(
                [QtCore.QPointF(p.x(), p.y()) for p in self._points])
        return self._qtPolygon

class MapSpline(object):
    @typing.overload
    def __init__(self) -> None: ...
    @typing.overload
    def __init__(self, other: 'MapSpline') -> None: ...

    @typing.overload
    def __init__(
        self,
        points: typing.Sequence[cartographer.PointF],
        tension: float,
        closed: bool) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        if not args and not kwargs:
            self._points: typing.List[cartographer.PointF] = []
            self._tension = 0
            self._closed = False
        elif len(args) + len(kwargs) == 1:
            other = args[0] if len(args) > 0 else kwargs['other']
            if not isinstance(other, MapSpline):
                raise TypeError('The other parameter must be a MapSpline')
            # NOTE: This assumes the points methods return copies of
            # the list held by other not the list themselves
            self._points = other.points()
            self._tension = other.tension()
            self._closed = other.closed()
        else:
            self._points = list(args[0] if len(args) > 0 else kwargs['points'])
            self._tension = float(args[1] if len(args) > 1 else kwargs['tension'])
            self._closed = bool(args[2] if len(args) > 2 else kwargs['closed'])

        # These are created on demand
        self._bounds: typing.Optional[cartographer.RectangleF] = None
        self._qtPainterPath: typing.Optional[QtGui.QPainterPath] = None

    def points(self) -> typing.Sequence[cartographer.PointF]:
        return list(self._points)

    def tension(self) -> float:
        return self._tension

    def closed(self) -> bool:
        return self._closed

    def bounds(self) -> cartographer.RectangleF:
        if self._bounds is None:
            # Calculating the bounds of a spline is way to hard for my feeble brain
            # so just get Qt to do it
            qtPainterPath = self.qtPainterPath()
            qtRect = qtPainterPath.boundingRect()
            self._bounds = cartographer.RectangleF(
                x=qtRect.left(),
                y=qtRect.top(),
                width=qtRect.width(),
                height=qtRect.height())

        return cartographer.RectangleF(self._bounds)

    def translate(self, dx: float, dy: float) -> None:
        for point in self._points:
            point.translate(dx, dy)
        if self._bounds:
            self._bounds.translate(dx, dy)
        if self._qtPainterPath:
            self._qtPainterPath.translate(dx, dy)

    def copyFrom(self, other: 'MapPath') -> None:
        # NOTE: This assumes the points methods return copies of
        # the list held by other not the list themselves
        self._points = other.points()
        self._closed = other.closed()
        self._bounds = None # Calculate on demand
        self._qtPainterPath = None

    # Conversion of the Traveller Map Cardinal Spline to cubicTo calls
    # is based on this post
    # https://stackoverflow.com/questions/56528436/whats-the-best-way-to-implement-interactive-spline-like-curve-on-qgraphicsview
    def qtPainterPath(self) -> QtGui.QPainterPath:
        if not self._qtPainterPath:
            self._createSpline()
        return self._qtPainterPath

    def _createSpline(self) -> None:
        self._qtPainterPath = QtGui.QPainterPath()
        if len(self._points) < 3:
            return

        # NOTE: This fudge factor is needed to convert the tension from the
        # values used by Traveller Map to the values used by the algorithm
        # I'm using to convert the spline to cubicTo calls. This value was
        # derived at by trial and error and seems to give an good approximation
        qtTension = self._tension * 2 / 3

        controlPoints = MapSpline._calcControlPoints(
            self._points[-1],
            self._points[0],
            self._points[1],
            qtTension)
        prevPoint = controlPoints[1]
        self._qtPainterPath.moveTo(QtCore.QPointF(*self._points[0].point()))
        for i in range(1, len(self._points) - 1, 1):
            controlPoints = MapSpline._calcControlPoints(
                self._points[i - 1],
                self._points[i],
                self._points[i + 1],
                qtTension)
            self._qtPainterPath.cubicTo(
                QtCore.QPointF(*prevPoint.point()),
                QtCore.QPointF(*controlPoints[0].point()),
                QtCore.QPointF(*self._points[i].point()))
            prevPoint = controlPoints[1]
        controlPoints = MapSpline._calcControlPoints(
            self._points[-2],
            self._points[-1],
            self._points[0],
            qtTension)
        self._qtPainterPath.cubicTo(
            QtCore.QPointF(*prevPoint.point()),
            QtCore.QPointF(*controlPoints[0].point()),
            QtCore.QPointF(*self._points[-1].point()))
        prevPoint = controlPoints[1]

        if self._closed:
            controlPoints = MapSpline._calcControlPoints(
                self._points[-1],
                self._points[0],
                self._points[1],
                qtTension)
            self._qtPainterPath.cubicTo(
                QtCore.QPointF(*prevPoint.point()),
                QtCore.QPointF(*controlPoints[0].point()),
                QtCore.QPointF(*self._points[0].point()))

        self._qtPainterPath.closeSubpath()

    @staticmethod
    def _calcControlPoints(
            p0: cartographer.PointF,
            p1: cartographer.PointF,
            p2: cartographer.PointF,
            tension: float = 0.25
            ) -> typing.Tuple[cartographer.PointF, cartographer.PointF]:
        d01 = math.sqrt((p1.x() - p0.x()) * (p1.x() - p0.x()) + (p1.y() - p0.y()) * (p1.y() - p0.y()))
        d12 = math.sqrt((p2.x() - p1.x()) * (p2.x() - p1.x()) + (p2.y() - p1.y()) * (p2.y() - p1.y()))

        fa = tension * d01 / (d01 + d12)
        fb = tension * d12 / (d01 + d12)

        c1x = p1.x() - fa * (p2.x() - p0.x())
        c1y = p1.y() - fa * (p2.y() - p0.y())
        c2x = p1.x() + fb * (p2.x() - p0.x())
        c2y = p1.y() + fb * (p2.y() - p0.y())

        return (cartographer.PointF(c1x, c1y),
                cartographer.PointF(c2x, c2y))

class MapMatrix(cartographer.AbstractMatrix):
    @typing.overload
    def __init__(self) -> None: ...
    @typing.overload
    def __init__(self, other: 'MapMatrix') -> None: ...
    @typing.overload
    def __init__(self, m11: float, m12: float, m21: float, m22: float, dx: float, dy: float) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        if not args and not kwargs:
            self._qtMatrix = QtGui.QTransform()
        elif len(args) + len(kwargs) == 1:
            other = args[0] if len(args) > 0 else kwargs['other']
            if not isinstance(other, MapMatrix):
                raise TypeError('The other parameter must be an MapMatrix')
            self._qtMatrix = QtGui.QTransform(other._qtMatrix)
        else:
            self._qtMatrix = QtGui.QTransform(
                args[0] if len(args) > 0 else kwargs['m11'],
                args[1] if len(args) > 1 else kwargs['m12'],
                0,
                args[2] if len(args) > 2 else kwargs['m21'],
                args[3] if len(args) > 3 else kwargs['m22'],
                0,
                args[4] if len(args) > 4 else kwargs['dx'],
                args[5] if len(args) > 5 else kwargs['dy'],
                1)

    def m11(self) -> float:
        return self._qtMatrix.m11()

    def m12(self) -> float:
        return self._qtMatrix.m12()

    def m21(self) -> float:
        return self._qtMatrix.m21()

    def m22(self) -> float:
        return self._qtMatrix.m22()

    def offsetX(self) -> float:
        return self._qtMatrix.dx()

    def offsetY(self) -> float:
        return self._qtMatrix.dy()

    def isIdentity(self) -> bool:
        return self._qtMatrix.isIdentity()

    def invert(self) -> None:
        self._qtMatrix, _ = self._qtMatrix.inverted()

    def rotatePrepend(self, degrees: float, center: cartographer.PointF) -> None:
        if degrees == 0.0:
            return # Nothing to do
        self._qtMatrix.translate(-center.x(), -center.y())
        self._qtMatrix.rotate(degrees, QtCore.Qt.Axis.ZAxis)
        self._qtMatrix.translate(center.x(), center.y())

    def scalePrepend(self, sx: float, sy: float) -> None:
        if sx == 1.0 and sy == 1.0:
            return
        self._qtMatrix.scale(sx, sy)

    def translatePrepend(self, dx: float, dy: float) -> None:
        if dx == 0.0 and dy == 0.0:
            return
        self._qtMatrix.translate(dx, dy)

    def prepend(self, matrix: 'MapMatrix') -> None:
        self._qtMatrix = matrix.qtTransform() * self._qtMatrix

    def transform(self, point: cartographer.PointF) -> cartographer.PointF:
        qtPoint = self._qtMatrix.map(QtCore.QPointF(point.x(), point.y()))
        return cartographer.PointF(qtPoint.x(), qtPoint.y())

    def qtTransform(self) -> QtGui.QTransform:
        return self._qtMatrix

class MapBrush(cartographer.AbstractBrush):
    @typing.overload
    def __init__(self) -> None: ...
    @typing.overload
    def __init__(self, other: 'MapBrush') -> None: ...
    @typing.overload
    def __init__(self, colour: str) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        if not args and not kwargs:
            self._colour = ''
        elif len(args) == 1:
            arg = args[0]
            if isinstance(arg, MapBrush):
                self._colour = arg.colour()
            else:
                self._colour = arg
        elif 'other' in kwargs:
            other = kwargs['other']
            if not isinstance(other, MapBrush):
                raise TypeError('The other parameter must be a MapBrush')
            self._colour = other.colour()
        else:
            self._colour = kwargs['colour']

        self._qtBrush: typing.Optional[QtGui.QBrush] = None

    def colour(self) -> str:
        return self._colour

    def setColour(self, colour: str) -> None:
        self._colour = colour
        if self._qtBrush:
            self._qtBrush.setColor(QtGui.QColor(self._colour))

    def copyFrom(self, other: 'MapBrush') -> None:
        self._colour = other._colour
        if self._qtBrush:
            self._qtBrush.setColor(
                other._qtBrush.color()
                if other._qtBrush else
                QtGui.QColor(self._colour))

    def qtBrush(self) -> QtGui.QBrush:
        if not self._qtBrush:
            self._qtBrush = QtGui.QBrush(QtGui.QColor(self._colour))
        return self._qtBrush

class MapPen(cartographer.AbstractPen):
    _LineStyleMap = {
        cartographer.LineStyle.Solid: (QtCore.Qt.PenStyle.SolidLine, None),
        cartographer.LineStyle.Dot: (QtCore.Qt.PenStyle.CustomDashLine, [1, 1]),
        cartographer.LineStyle.Dash: (QtCore.Qt.PenStyle.CustomDashLine, [3, 1]),
        cartographer.LineStyle.DashDot: (QtCore.Qt.PenStyle.CustomDashLine,  [3, 1, 1, 1]),
        cartographer.LineStyle.DashDotDot: (QtCore.Qt.PenStyle.CustomDashLine, [3, 1, 1, 1, 1, 1])}

    _PenTipMap = {
        cartographer.PenTip.Flat: QtCore.Qt.PenCapStyle.FlatCap,
        cartographer.PenTip.Square: QtCore.Qt.PenCapStyle.SquareCap,
        cartographer.PenTip.Round: QtCore.Qt.PenCapStyle.RoundCap}

    @typing.overload
    def __init__(self) -> None: ...
    @typing.overload
    def __init__(self, other: 'MapPen') -> None: ...

    @typing.overload
    def __init__(
        self,
        colour: str,
        width: float,
        style: cartographer.LineStyle = cartographer.LineStyle.Solid,
        pattern: typing.Optional[typing.Sequence[float]] = None,
        tip: cartographer.PenTip = cartographer.PenTip.Flat
        ) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        if not args and not kwargs:
            self._colour = ''
            self._width = 0
            self._style = cartographer.LineStyle.Solid
            self._pattern = None
            self._tip = cartographer.PenTip.Flat
        elif len(args) + len(kwargs) == 1:
            other = args[0] if len(args) > 0 else kwargs['other']
            if not isinstance(other, MapPen):
                raise TypeError('The other parameter must be a MapPen')
            self._colour = other.colour()
            self._width = other.width()
            self._style = other.style()
            self._pattern = list(other.pattern()) if other.pattern() else None
            self._tip = other.tip()
        else:
            self._colour = args[0] if len(args) > 0 else kwargs['colour']
            self._width = args[1] if len(args) > 1 else kwargs['width']
            self._style = args[2] if len(args) > 2 else kwargs['style']
            self._pattern = args[3] if len(args) > 3 else kwargs.get('pattern')
            self._tip = args[4] if len(args) > 4 else kwargs['tip']

        self._qtPen = None

    def colour(self) -> str:
        return self._colour

    def setColour(self, colour: str) -> None:
        self._colour = colour
        if self._qtPen:
            self._qtPen.setColor(QtGui.QColor(self._colour))

    def width(self) -> float:
        return self._width

    def setWidth(self, width: float) -> None:
        self._width = width
        if self._qtPen:
            self._qtPen.setWidthF(self._width)

    def style(self) -> cartographer.LineStyle:
        return self._style

    def setStyle(
            self,
            style: cartographer.LineStyle,
            pattern: typing.Optional[typing.List[float]] = None
            ) -> None:
        self._style = style
        self._pattern = list(pattern) if self._style is cartographer.LineStyle.Custom else None

        if self._qtPen:
            if self._style is cartographer.LineStyle.Custom:
                self._qtPen.setStyle(QtCore.Qt.PenStyle.CustomDashLine)
                self._qtPen.setDashPattern(self._pattern)
            else:
                qtStyle, qtPattern = MapPen._LineStyleMap[self._style]
                self._qtPen.setStyle(qtStyle)
                if qtPattern:
                    self._qtPen.setDashPattern(qtPattern)

    def pattern(self) -> typing.Optional[typing.Sequence[float]]:
        return self._pattern

    def setPattern(
            self,
            pattern: typing.Sequence[float]
            ) -> None:
        self._style = cartographer.LineStyle.Custom
        self._pattern = list(pattern)
        if self._qtPen:
            self._qtPen.setDashPattern(pattern)

    def tip(self) -> cartographer.PenTip:
        return self._tip

    def setTip(self, tip: cartographer.PenTip):
        if tip == self._tip:
            return tip
        self._tip = tip
        if self._qtPen:
            self._qtPen.setCapStyle(MapPen._PenTipMap[tip])

    def copyFrom(
            self,
            other: 'MapPen'
            ) -> None:
        self._colour = other._colour
        self._width = other._width
        self._style = other._style
        self._pattern = list(other._pattern) if other._pattern else None
        if self._qtPen:
            self._qtPen.setColor(QtGui.QColor(self._colour))
            self._qtPen.setWidthF(self._width)
            self._qtPen.setCapStyle(MapPen._PenTipMap[self._tip])

            if self._style is cartographer.LineStyle.Custom:
                self._qtPen.setStyle(QtCore.Qt.PenStyle.CustomDashLine)
                self._qtPen.setDashPattern(self._pattern)
            else:
                qtStyle, qtPattern = MapPen._LineStyleMap[self._style]
                self._qtPen.setStyle(qtStyle)
                if qtPattern:
                    self._qtPen.setDashPattern(qtPattern)

    def qtPen(self) -> QtGui.QPen:
        if not self._qtPen:
            if self._style is cartographer.LineStyle.Custom:
                qtStyle = QtCore.Qt.PenStyle.CustomDashLine
                qtPattern = self._pattern
            else:
                qtStyle, qtPattern = MapPen._LineStyleMap[self._style]

            self._qtPen = QtGui.QPen(
                QtGui.QColor(self._colour),
                self._width,
                qtStyle)
            if qtPattern:
                self._qtPen.setDashPattern(qtPattern)
            self._qtPen.setCapStyle(MapPen._PenTipMap[self._tip])
        return self._qtPen

class MapImage(cartographer.AbstractImage):
    def __init__(self, data: bytes):
        self._qtImage = QtGui.QImage.fromData(data, None)
        if not self._qtImage:
            raise RuntimeError(f'Failed to load image')

    def width(self) -> int:
        return self._qtImage.width()

    def height(self) -> int:
        return self._qtImage.height()

    def qtImage(self) -> QtGui.QImage:
        return self._qtImage

class MapFont(cartographer.AbstractFont):
    # Qt doesn't seem to have great support for fonts with float
    # point sizes which the Traveller Map rendering expects.
    # Instead I have all fonts set to the same size and when
    # strings are rendered a scale transform is used to scale
    # them to the correct size. Somewhat surprisingly whe I do
    # this Qt seems to render the font smoothly at the correct
    # size rather than rendering at a smaller size and scaling
    # it which would result in artifacts. The actual size chosen
    # for the fonts is somewhat arbitrary, although fonts do
    # renderer noticeably differently if the value is to small
    _TextPointSize = 10

    def __init__(
            self,
            family: str,
            emSize: float,
            style: cartographer.FontStyle
            ) -> None:
        self._family = family
        self._emSize = emSize
        self._style = style

        self._font = QtGui.QFont(family)
        if not self._font:
            raise ValueError(f'Unknown font "{family}"')
        self._font.setPointSizeF(MapFont._TextPointSize)
        if self._style & cartographer.FontStyle.Bold:
            self._font.setBold(True)
        if self._style & cartographer.FontStyle.Italic:
            self._font.setItalic(True)
        if self._style & cartographer.FontStyle.Underline:
            self._font.setUnderline(True)
        if self._style & cartographer.FontStyle.Strikeout:
            self._font.setStrikeOut(True)

        self._fontMetrics = QtGui.QFontMetricsF(self._font)
        self._lineSpacing = self._fontMetrics.lineSpacing()

        self._sizeCache = common.LRUCache[str, QtCore.QRectF](1000)

    def family(self) -> str:
        return self._family

    def emSize(self) -> float:
        return self._emSize

    def style(self) -> cartographer.FontStyle:
        return self._style

    def pointSize(self) -> float:
        return self._TextPointSize

    def lineSpacing(self) -> float:
        return self._lineSpacing

    def qtMeasureText(self, text: str) -> QtCore.QRectF:
        rect = self._sizeCache.get(text)
        if not rect:
            # NOTE: Use of tight bounds is required to have glyph symbols
            # centred correctly
            rect = self._fontMetrics.tightBoundingRect(text)
            self._sizeCache[text] = rect
        return rect

    def qtFont(self) -> QtGui.QFont:
        return self._font

class MapGraphics(cartographer.AbstractGraphics):
    def __init__(self):
        super().__init__()
        self._painter = None
        self._supportsWingdings = None

        self._hasLosslessImageRendering = gui.minPyQtVersionCheck('5.13')

        # There was a fix made in PyQt 5.15.7 that means it's possible to pass
        # a QPolygon to QPainter.drawLines where it will be interpreted as a
        # list of point pairs.
        self._hasDrawLinesPolygonFix = gui.minPyQtVersionCheck('5.15.7')

    def setPainter(self, painter: typing.Optional[QtGui.QPainter]) -> None:
        self._painter = painter
        if self._painter:
            self._painter.setRenderHint(
                QtGui.QPainter.RenderHint.Antialiasing,
                False)
            self._painter.setRenderHint(
                QtGui.QPainter.RenderHint.TextAntialiasing,
                False)
            self._painter.setRenderHint(
                QtGui.QPainter.RenderHint.SmoothPixmapTransform,
                False)
            if self._hasLosslessImageRendering:
                self._painter.setRenderHint(
                    QtGui.QPainter.RenderHint.LosslessImageRendering,
                    True)

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

    def createPointList(
            self,
            points: typing.Sequence[cartographer.PointF]
            ) -> MapPointList:
        return MapPointList(points=points)

    def copyPointList(self, other: MapPointList) -> MapPointList:
        return MapPointList(other=other)

    def createPath(
            self,
            points: typing.Sequence[cartographer.PointF],
            closed: bool
            ) -> MapPath:
        return MapPath(points=points, closed=closed)

    def copyPath(self, other: MapPath) -> MapPath:
        return MapPath(other=other)

    def createSpline(
            self,
            points: typing.Sequence[cartographer.PointF],
            tension: float,
            closed: bool
            ) -> MapSpline:
        return MapSpline(points=points, tension=tension, closed=closed)

    def copySpline(self, other: MapSpline) -> MapSpline:
        return MapSpline(other=other)

    def createIdentityMatrix(self) -> MapMatrix:
        return MapMatrix()

    def createMatrix(
            self,
            m11: float,
            m12: float,
            m21: float,
            m22: float,
            dx: float,
            dy: float
            ) -> MapMatrix:
        return MapMatrix(m11=m11, m12=m12, m21=m21, m22=m22, dx=dx, dy=dy)

    def copyMatrix(self, other: MapMatrix) -> MapMatrix:
        return MapMatrix(other=other)

    def createBrush(self, colour: str = '') -> MapBrush:
        return MapBrush(colour=colour)

    def copyBrush(self, other: MapBrush) -> MapBrush:
        return MapPath(other=other)

    def createPen(
            self,
            colour: str = '',
            width: float = 1,
            style: cartographer.LineStyle = cartographer.LineStyle.Solid,
            pattern: typing.Optional[typing.Sequence[float]] = None,
            tip: cartographer.PenTip = cartographer.PenTip.Flat
            ) -> MapPen:
        return MapPen(colour=colour, width=width, style=style, pattern=pattern, tip=tip)

    def copyPen(self, other: MapPen) -> MapPen:
        return MapPen(other=other)

    def createImage(
            self,
            data: bytes
            ) -> MapImage:
        return MapImage(data=data)

    def createFont(
            self,
            family: str,
            emSize: float,
            style: cartographer.FontStyle = cartographer.FontStyle.Regular
            ) -> MapFont:
        # NOTE: Traveller Map has this as 1.4 (in makeFont) but I found I needed
        # to lower it to get fonts rendering the correct size.
        return MapFont(family=family, emSize=emSize * 1.05, style=style)

    def setSmoothingMode(self, mode: cartographer.AbstractGraphics.SmoothingMode):
        antialias = mode == cartographer.AbstractGraphics.SmoothingMode.HighQuality or \
            mode == cartographer.AbstractGraphics.SmoothingMode.AntiAlias

        self._painter.setRenderHint(
            QtGui.QPainter.RenderHint.Antialiasing,
            antialias)
        self._painter.setRenderHint(
            QtGui.QPainter.RenderHint.TextAntialiasing,
            antialias)
        self._painter.setRenderHint(
            QtGui.QPainter.RenderHint.SmoothPixmapTransform,
            antialias)

    def scaleTransform(self, scaleX: float, scaleY: float) -> None:
        if scaleX == 1.0 and scaleY == 1.0:
            return
        transform = self._painter.transform()
        transform.scale(scaleX, scaleY)
        self._painter.setTransform(transform)

    def translateTransform(self, dx: float, dy: float) -> None:
        if dx == 0.0 and dy == 0.0:
            return
        transform = self._painter.transform()
        transform.translate(dx, dy)
        self._painter.setTransform(transform)

    def rotateTransform(self, degrees: float) -> None:
        if degrees == 0.0:
            return
        transform = self._painter.transform()
        transform.rotate(degrees, QtCore.Qt.Axis.ZAxis)
        self._painter.setTransform(transform)

    def multiplyTransform(self, matrix: MapMatrix) -> None:
        self._painter.setTransform(
            matrix.qtTransform() * self._painter.transform())

    def intersectClipPath(self, path: MapPath) -> None:
        newClip = QtGui.QPainterPath()
        newClip.setFillRule(QtCore.Qt.FillRule.WindingFill)
        newClip.addPolygon(path.qtPolygon())
        currentClip = self._painter.clipPath()
        if not currentClip.isEmpty():
            newClip = currentClip.intersected(newClip)
        self._painter.setClipPath(newClip, operation=QtCore.Qt.ClipOperation.IntersectClip)

    def intersectClipRect(self, rect: cartographer.RectangleF) -> None:
        newClip = QtGui.QPainterPath()
        newClip.setFillRule(QtCore.Qt.FillRule.WindingFill)
        newClip.addRect(QtCore.QRectF(*rect.rect()))
        currentClip = self._painter.clipPath()
        if not currentClip.isEmpty():
            newClip = currentClip.intersected(newClip)
        self._painter.setClipPath(newClip, operation=QtCore.Qt.ClipOperation.IntersectClip)

    def drawPoint(self, point: cartographer.PointF, pen: MapPen) -> None:
        self._painter.setPen(pen.qtPen())
        self._painter.drawPoint(self._convertPoint(point))

    def drawPoints(self, points: MapPointList, pen: MapPen) -> None:
        self._painter.setPen(pen.qtPen())
        self._painter.drawPoints(points.qtPolygon())

    def drawLine(
            self,
            pt1: cartographer.PointF,
            pt2: cartographer.PointF,
            pen: MapPen
            ) -> None:
        self._painter.setPen(pen.qtPen())
        self._painter.drawLine(
            self._convertPoint(pt1),
            self._convertPoint(pt2))

    def drawLines(
            self,
            points: MapPointList,
            pen: MapPen
            ) -> None:
        self._painter.setPen(pen.qtPen())
        if self._hasDrawLinesPolygonFix:
            self._painter.drawLines(points.qtPolygon())
        else:
            actualPoints = points.points()
            for i in range(0, len(actualPoints), 2):
                point1 = actualPoints[i]
                point2 = actualPoints[i + 1]
                self._painter.drawLine(
                    QtCore.QPointF(point1.x(), point1.y()),
                    QtCore.QPointF(point2.x(), point2.y()))

    def drawPath(
            self,
            path: MapPath,
            pen: typing.Optional[MapPen] = None,
            brush: typing.Optional[MapBrush] = None
            ) -> None:
        self._painter.setPen(pen.qtPen() if pen else QtCore.Qt.PenStyle.NoPen)
        self._painter.setBrush(brush.qtBrush() if brush else QtCore.Qt.BrushStyle.NoBrush)
        if path.closed():
            self._painter.drawPolygon(path.qtPolygon())
        else:
            self._painter.drawPolyline(path.qtPolygon())

    def drawRectangle(
            self,
            rect: cartographer.RectangleF,
            pen: typing.Optional[MapPen] = None,
            brush: typing.Optional[MapBrush] = None
            ) -> None:
        self._painter.setPen(pen.qtPen() if pen else QtCore.Qt.PenStyle.NoPen)
        self._painter.setBrush(brush.qtBrush() if brush else QtCore.Qt.BrushStyle.NoBrush)
        self._painter.drawRect(QtCore.QRectF(*rect.rect()))

    def drawEllipse(
            self,
            rect: cartographer.RectangleF,
            pen: typing.Optional[MapPen] = None,
            brush: typing.Optional[MapBrush] = None
            ) -> None:
        self._painter.setPen(pen.qtPen() if pen else QtCore.Qt.PenStyle.NoPen)
        self._painter.setBrush(brush.qtBrush() if brush else QtCore.Qt.BrushStyle.NoBrush)
        self._painter.drawEllipse(QtCore.QRectF(*rect.rect()))

    def drawArc(
            self,
            rect: cartographer.RectangleF,
            startDegrees: float,
            sweepDegrees: float,
            pen: MapPen
            ) -> None:
        self._painter.setPen(pen.qtPen())
        # NOTE: Angles are in 1/16th of a degree
        self._painter.drawArc(
            QtCore.QRectF(*rect.rect()),
            int((startDegrees * 16) + 0.5),
            int((sweepDegrees * 16) + 0.5))

    def drawImage(
            self,
            image: MapImage,
            rect: cartographer.RectangleF
            ) -> None:
        self._painter.drawImage(
            QtCore.QRectF(*rect.rect()),
            image.qtImage())

    def drawImageAlpha(
            self,
            alpha: float,
            image: MapImage,
            rect: cartographer.RectangleF
            ) -> None:
        oldAlpha = self._painter.opacity()
        self._painter.setOpacity(alpha)
        try:
            self._painter.drawImage(
                QtCore.QRectF(*rect.rect()),
                image.qtImage())
        finally:
            self._painter.setOpacity(oldAlpha)

    def drawCurve(
            self,
            spline: MapSpline,
            pen: typing.Optional[MapPen] = None,
            brush: typing.Optional[MapBrush] = None
            ) -> None:
        self._painter.setPen(pen.qtPen() if pen else QtCore.Qt.PenStyle.NoPen)
        self._painter.setBrush(brush.qtBrush() if brush else QtCore.Qt.BrushStyle.NoBrush)
        self._painter.drawPath(spline.qtPainterPath())

    def measureString(
            self,
            text: str,
            font: MapFont
            ) -> typing.Tuple[float, float]: # (width, height)
        qtFont = font.qtFont()
        scale = font.emSize() / qtFont.pointSizeF()
        rect = font.qtMeasureText(text)
        return (rect.width() * scale, rect.height() * scale)

    def drawString(
            self,
            text: str,
            font: MapFont,
            brush: MapBrush,
            x: float, y: float,
            format: cartographer.TextAlignment
            ) -> None:
        qtFont = font.qtFont()
        textRect = font.qtMeasureText(text)
        scale = font.emSize() / qtFont.pointSizeF()

        self._painter.save()
        try:
            transform = QtGui.QTransform()
            if x != 0.0 or y != 0.0:
                transform.translate(x, y)
            if scale != 1.0:
                transform.scale(scale, scale)
            self._painter.setTransform(
                transform * self._painter.transform())

            self._painter.setFont(qtFont)

            # The Traveller Map code uses brushes for text but Qt uses the
            # current pen
            qtBrush = brush.qtBrush()
            self._painter.setPen(qtBrush.color())

            if format == cartographer.TextAlignment.Baseline:
                textOrigin = QtCore.QPointF(0, 0)
            elif format == cartographer.TextAlignment.Centered:
                textOrigin = QtCore.QPointF(
                    -textRect.x() - (textRect.width() / 2),
                    -textRect.y() - (textRect.height() / 2))
            elif format == cartographer.TextAlignment.TopLeft:
                textOrigin = QtCore.QPointF(
                    -textRect.x(),
                    -textRect.y())
            elif format == cartographer.TextAlignment.TopCenter:
                textOrigin = QtCore.QPointF(
                    -textRect.x() - (textRect.width() / 2),
                    -textRect.y())
            elif format == cartographer.TextAlignment.TopRight:
                textOrigin = QtCore.QPointF(
                    -textRect.x() - textRect.width(),
                    -textRect.y())
            elif format == cartographer.TextAlignment.MiddleLeft:
                textOrigin = QtCore.QPointF(
                    -textRect.x(),
                    -textRect.y() - (textRect.height() / 2))
            elif format == cartographer.TextAlignment.MiddleRight:
                textOrigin = QtCore.QPointF(
                    -textRect.x() - textRect.width(),
                    -textRect.y() - (textRect.height() / 2))
            elif format == cartographer.TextAlignment.BottomLeft:
                textOrigin = QtCore.QPointF(
                    -textRect.x(),
                    -textRect.y() - textRect.height())
            elif format == cartographer.TextAlignment.BottomCenter:
                textOrigin = QtCore.QPointF(
                    -textRect.x() - (textRect.width() / 2),
                    -textRect.y() - textRect.height())
            elif format == cartographer.TextAlignment.BottomRight:
                textOrigin = QtCore.QPointF(
                    -textRect.x() - textRect.width(),
                    -textRect.y() - textRect.height())

            self._painter.drawText(textOrigin, text)
        finally:
            self._painter.restore()

    def save(self) -> cartographer.AbstractGraphicsState:
        self._painter.save()
        return cartographer.AbstractGraphicsState(graphics=self)

    def restore(self) -> None:
        self._painter.restore()

    def _convertPoint(self, point: cartographer.PointF) -> QtCore.QPointF:
        return QtCore.QPointF(point.x(), point.y())

    def _convertPoints(
            self,
            points: typing.Sequence[cartographer.PointF]
            ) -> typing.Sequence[QtCore.QPointF]:
        return [QtCore.QPointF(p.x(), p.y()) for p in points]
