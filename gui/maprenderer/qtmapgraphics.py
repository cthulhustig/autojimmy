import maprenderer
import typing
from PyQt5 import QtCore, QtGui

# TODO: This (and PointF) could do with an offsetX, offsetY functions as there
# are quite a few places that are having to do get x/y then set x/y with modifier
class QtMapRectangleF(maprenderer.AbstractRectangleF):
    @typing.overload
    def __init__(self) -> None: ...
    @typing.overload
    def __init__(self, other: 'QtMapRectangleF') -> None: ...
    @typing.overload
    def __init__(self, x: float, y: float, width: float, height: float) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        if not args and not kwargs:
            self._x = self._y = self._width = self._height = 0
        elif len(args) + len(kwargs) == 1:
            other = args[0] if len(args) > 0 else kwargs['other']
            if not isinstance(other, QtMapRectangleF):
                raise TypeError('The other parameter must be a QtMapRectangleF')
            self._x, self._y, self._width, self._height = other.rect()
        else:
            self._x = float(args[0] if len(args) > 0 else kwargs['x'])
            self._y = float(args[1] if len(args) > 1 else kwargs['y'])
            self._width = float(args[2] if len(args) > 2 else kwargs['width'])
            self._height = float(args[3] if len(args) > 3 else kwargs['height'])

        self._qtRect: typing.Optional[QtCore.QRectF] = None

    def x(self) -> float:
        return self._x

    def setX(self, x: float) -> None:
        self._x = x
        if self._qtRect:
            self._qtRect.setX(self._x)

    def y(self) -> float:
        return self._y

    def setY(self, y: float) -> None:
        self._y = y
        if self._qtRect:
            self._qtRect.setY(self._y)

    def width(self) -> float:
        return self._width

    def setWidth(self, width: float) -> None:
        self._width = width
        if self._qtRect:
            self._qtRect.setWidth(self._width)

    def height(self) -> float:
        return self._height

    def setHeight(self, height: float) -> None:
        self._height = height
        if self._qtRect:
            self._qtRect.setHeight(self._height)

    def rect(self) -> typing.Tuple[int, int, int, int]: # (x, y, width, height)
        return (self._x, self._y, self._width, self._height)

    def setRect(self, x: float, y: float, width: float, height: float) -> None:
        self._x = x
        self._y = y
        self._width = width
        self._height = height
        if self._qtRect:
            self._qtRect.setCoords(
                self._x,
                self._y,
                self._x + self._width,
                self._y + self._height)

    def translate(self, dx: float, dy: float) -> None:
        self._x += dx
        self._y += dy

    def copyFrom(self, other: 'QtMapRectangleF') -> None:
        self._x, self._y, self._width, self._height = other.rect()
        if self._qtRect:
            self._qtRect.setCoords(
                self._x,
                self._y,
                self._x + self._width,
                self._y + self._height)

    def qtRect(self) -> QtCore.QRectF:
        if not self._qtRect:
            self._qtRect = QtCore.QRectF(self._x, self._y, self._width, self._height)
        return self._qtRect

class QtMapPointList(maprenderer.AbstractPath):
    @typing.overload
    def __init__(self) -> None: ...
    @typing.overload
    def __init__(self, other: 'QtMapPath') -> None: ...
    @typing.overload
    def __init__(self, points: typing.Sequence[maprenderer.AbstractPointF]) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        if len(args) == 1:
            arg = args[0]
            if isinstance(arg, QtMapPointList):
                self._points = list(arg.points())
            else:
                self._points = list(arg)
        elif 'other' in kwargs:
            other = kwargs['other']
            if not isinstance(other, QtMapPointList):
                raise TypeError('The other parameter must be a QtMapPointList')
            self._points = list(other.points())
        else:
            self._points = list(kwargs['points'])

        # These are created on demand
        self._bounds: typing.Optional[maprenderer.AbstractRectangleF] = None
        self._qtPolygon: typing.Optional[QtGui.QPolygonF] = None

    def points(self) -> typing.Sequence[maprenderer.AbstractPointF]:
        return self._points

    def bounds(self) -> maprenderer.AbstractRectangleF:
        if self._bounds is not None:
            return self._bounds

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

        self._bounds = QtMapRectangleF(
            x=minX,
            y=minY,
            width=maxX - minX,
            height=maxY - minY)
        return self._bounds

    def translate(self, dx: float, dy: float) -> None:
        for point in self._points:
            point.translate(dx, dy)
        if self._bounds:
            self._bounds.translate(dx, dy)
        if self._qtPolygon:
            self._qtPolygon.translate(dx, dy)

    def copyFrom(self, other: 'QtMapPath') -> None:
        self._points = list(other.points())
        self._bounds = None # Calculate on demand
        self._qtPolygon = None # TODO: is it possible to update an existing polygon?

    def qtPolygon(self) -> QtGui.QPolygonF:
        if not self._qtPolygon:
            self._qtPolygon = QtGui.QPolygonF(
                [QtCore.QPointF(p.x(), p.y()) for p in self._points])
        return self._qtPolygon

class QtMapPath(maprenderer.AbstractPath):
    @typing.overload
    def __init__(self) -> None: ...
    @typing.overload
    def __init__(self, other: 'QtMapPath') -> None: ...
    @typing.overload
    def __init__(
        self,
        points: typing.Sequence[maprenderer.AbstractPointF],
        types: typing.Sequence[maprenderer.PathPointType],
        closed: bool) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        if not args and not kwargs:
            self._points: typing.List[maprenderer.AbstractPointF] = []
            self._types: typing.List[maprenderer.PathPointType] = []
            self._closed = False
        elif len(args) + len(kwargs) == 1:
            other = args[0] if len(args) > 0 else kwargs['other']
            if not isinstance(other, QtMapPath):
                raise TypeError('The other parameter must be a QtMapPath')
            self._points = list(other.points())
            self._types = list(other.types())
            self._closed = other.closed()
        else:
            self._points = list(args[0] if len(args) > 0 else kwargs['points'])
            self._types = list(args[1] if len(args) > 1 else kwargs['types'])
            self._closed = bool(args[2] if len(args) > 2 else kwargs['closed'])
            if len(self._points) != len(self._types):
                raise ValueError('Point and type vectors have different lengths')

        # These are created on demand
        self._bounds: typing.Optional[maprenderer.AbstractRectangleF] = None
        self._qtPolygon: typing.Optional[QtGui.QPolygonF] = None

    def points(self) -> typing.Sequence[maprenderer.AbstractPointF]:
        return self._points

    def types(self) -> typing.Sequence[maprenderer.PathPointType]:
        return self._types

    def closed(self) -> bool:
        return self._closed

    def bounds(self) -> maprenderer.AbstractRectangleF:
        if self._bounds is not None:
            return self._bounds

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

        self._bounds = QtMapRectangleF(
            x=minX,
            y=minY,
            width=maxX - minX,
            height=maxY - minY)
        return self._bounds

    def translate(self, dx: float, dy: float) -> None:
        for point in self._points:
            point.translate(dx, dy)
        if self._bounds:
            self._bounds.translate(dx, dy)
        if self._qtPolygon:
            self._qtPolygon.translate(dx, dy)

    def copyFrom(self, other: 'QtMapPath') -> None:
        self._points = list(other.points())
        self._types = list(other.types())
        self._closed = other.closed()
        self._bounds = None # Calculate on demand
        self._qtPolygon = None # TODO: is it possible to update an existing polygon?

    # TODO: Need to check if I need to make sure that when
    # the polygon is closed, the first and last point are
    # the same
    def qtPolygon(self) -> QtGui.QPolygonF:
        if not self._qtPolygon:
            self._qtPolygon = QtGui.QPolygonF(
                [QtCore.QPointF(p.x(), p.y()) for p in self._points])
        return self._qtPolygon

class QtMapMatrix(maprenderer.AbstractMatrix):
    @typing.overload
    def __init__(self) -> None: ...
    @typing.overload
    def __init__(self, other: 'QtMapMatrix') -> None: ...
    @typing.overload
    def __init__(self, m11: float, m12: float, m21: float, m22: float, dx: float, dy: float) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        if not args and not kwargs:
            self._qtMatrix = QtGui.QTransform()
        elif len(args) + len(kwargs) == 1:
            other = args[0] if len(args) > 0 else kwargs['other']
            if not isinstance(other, QtMapMatrix):
                raise TypeError('The other parameter must be an QtMapMatrix')
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

    def rotatePrepend(self, degrees: float, center: maprenderer.AbstractPointF) -> None:
        if degrees == 0.0:
            return # Nothing to do
        self.translatePrepend(dx=-center.x(), dy=-center.y())

        transform = QtGui.QTransform()
        transform.rotate(degrees, QtCore.Qt.Axis.ZAxis)
        transform *= self._qtMatrix
        self._qtMatrix = transform

    def scalePrepend(self, sx: float, sy: float) -> None:
        if sx == 1.0 and sy == 1.0:
            return
        transform = QtGui.QTransform()
        transform.scale(sx, sy)
        transform *= self._qtMatrix
        self._qtMatrix = transform

    def translatePrepend(self, dx: float, dy: float) -> None:
        if dx == 0.0 and dy == 0.0:
            return
        transform = QtGui.QTransform()
        transform.translate(dx, dy)
        transform *= self._qtMatrix
        self._qtMatrix = transform

    def prepend(self, matrix: 'QtMapMatrix') -> None:
        self._qtMatrix = matrix.qtMatrix() * self._qtMatrix

    def transform(self, point: maprenderer.AbstractPointF) -> maprenderer.AbstractPointF:
        qtPoint = self._qtMatrix.map(QtCore.QPointF(point.x(), point.y()))
        return maprenderer.AbstractPointF(qtPoint.x(), qtPoint.y())

    def qtMatrix(self) -> QtGui.QTransform:
        return self._qtMatrix

class QtMapBrush(maprenderer.AbstractBrush):
    @typing.overload
    def __init__(self) -> None: ...
    @typing.overload
    def __init__(self, other: 'QtMapBrush') -> None: ...
    @typing.overload
    def __init__(self, color: str) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        if not args and not kwargs:
            self._color = ''
        elif len(args) == 1:
            arg = args[0]
            if isinstance(arg, QtMapBrush):
                self._color = arg.color()
            else:
                self._color = arg
        elif 'other' in kwargs:
            other = kwargs['other']
            if not isinstance(other, QtMapBrush):
                raise TypeError('The other parameter must be a QtMapBrush')
            self._color = other.color()
        else:
            self._color = kwargs['color']

        self._qtBrush: typing.Optional[QtGui.QBrush] = None

    def color(self) -> str:
        return self._color

    def setColor(self, color: str) -> None:
        self._color = color
        if self._qtBrush:
            # TODO: Could create my own AbstractColour to wrap a QColor to
            # avoid repeatedly converting from a string
            self._qtBrush.setColor(QtGui.QColor(self._color))

    def copyFrom(self, other: 'QtMapBrush') -> None:
        self._color = other._color
        if self._qtBrush:
            self._qtBrush.setColor(
                other._qtBrush.color()
                if other._qtBrush else
                QtGui.QColor(self._color))

    def qtBrush(self) -> QtGui.QBrush:
        if not self._qtBrush:
            self._qtBrush = QtGui.QBrush(QtGui.QColor(self._color))
        return self._qtBrush

class QtMapPen(maprenderer.AbstractPen):
    _LineStyleMap = {
        maprenderer.LineStyle.Solid: QtCore.Qt.PenStyle.SolidLine,
        maprenderer.LineStyle.Dot: QtCore.Qt.PenStyle.DotLine,
        maprenderer.LineStyle.Dash: QtCore.Qt.PenStyle.DashLine,
        maprenderer.LineStyle.DashDot: QtCore.Qt.PenStyle.DashDotLine,
        maprenderer.LineStyle.DashDotDot: QtCore.Qt.PenStyle.DashDotDotLine,
        maprenderer.LineStyle.Custom: QtCore.Qt.PenStyle.CustomDashLine}

    _PenTipMap = {
        maprenderer.PenTip.Flat: QtCore.Qt.PenCapStyle.FlatCap,
        maprenderer.PenTip.Square: QtCore.Qt.PenCapStyle.SquareCap,
        maprenderer.PenTip.Round: QtCore.Qt.PenCapStyle.RoundCap}

    @typing.overload
    def __init__(self) -> None: ...
    @typing.overload
    def __init__(self, other: 'QtMapPen') -> None: ...
    @typing.overload
    def __init__(
        self,
        color: str,
        width: float,
        style: maprenderer.LineStyle = maprenderer.LineStyle.Solid,
        pattern: typing.Optional[typing.Sequence[float]] = None,
        tip: maprenderer.PenTip = maprenderer.PenTip.Flat
        ) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        if not args and not kwargs:
            self._color = ''
            self._width = 0
            self._style = maprenderer.LineStyle.Solid
            self._pattern = None
            self._tip = maprenderer.PenTip.Flat
        elif len(args) + len(kwargs) == 1:
            other = args[0] if len(args) > 0 else kwargs['other']
            if not isinstance(other, QtMapPen):
                raise TypeError('The other parameter must be a QtMapPen')
            self._color = other.color()
            self._width = other.width()
            self._style = other.style()
            self._pattern = list(other.pattern()) if other.pattern() else None
            self._tip = other.tip()
        else:
            self._color = args[0] if len(args) > 0 else kwargs['color']
            self._width = args[1] if len(args) > 1 else kwargs['width']
            self._style = args[2] if len(args) > 2 else kwargs['style']
            self._pattern = args[3] if len(args) > 3 else kwargs.get('pattern')
            self._tip = args[4] if len(args) > 4 else kwargs['tip']

        self._qtPen = None

    def color(self) -> str:
        return self._color

    def setColor(self, color: str) -> None:
        self._color = color
        if self._qtPen:
            self._qtPen.setColor(QtGui.QColor(self._color))

    def width(self) -> float:
        return self._width

    def setWidth(self, width: float) -> None:
        self._width = width
        if self._qtPen:
            self._qtPen.setWidthF(self._width)

    def style(self) -> float:
        return self._style

    def setStyle(
            self,
            style: maprenderer.LineStyle,
            pattern: typing.Optional[typing.List[float]] = None
            ) -> None:
        self._style = style
        if self._qtPen:
            self._qtPen.setStyle(QtMapPen._LineStyleMap[self._style])

        if (self._style is maprenderer.LineStyle.Custom):
            if  pattern is not None:
                self._pattern = list(pattern)
                if self._qtPen:
                    self._qtPen.setDashPattern(pattern)
        else:
            self._pattern = None

    def pattern(self) -> typing.Optional[typing.Sequence[float]]:
        return self._pattern

    def setPattern(
            self,
            pattern: typing.Sequence[float]
            ) -> None:
        self._style = maprenderer.LineStyle.Custom
        self._pattern = list(pattern)
        if self._qtPen:
            self._qtPen.setDashPattern(pattern)

    def tip(self) -> maprenderer.PenTip:
        return self._tip

    def setTip(self, tip: maprenderer.PenTip):
        if tip == self._tip:
            return tip
        self._tip = tip
        if self._qtPen:
            self._qtPen.setCapStyle(QtMapPen._PenTipMap[tip])

    def copyFrom(
            self,
            other: 'QtMapPen'
            ) -> None:
        self._color = other._color
        self._width = other._width
        self._style = other._style
        self._pattern = list(other._pattern) if other._pattern else None
        if self._qtPen:
            self._qtPen.setColor(QtGui.QColor(self._color))
            self._qtPen.setWidthF(self._width)
            self._qtPen.setStyle(QtMapPen._LineStyleMap[self._style])
            if self._style is maprenderer.LineStyle.Custom:
                self._qtPen.setDashPattern(self._pattern)
            self._qtPen.setCapStyle(QtMapPen._PenTipMap[self._tip])

    def qtPen(self) -> QtGui.QPen:
        if not self._qtPen:
            self._qtPen = QtGui.QPen(
                QtGui.QColor(self._color),
                self._width,
                QtMapPen._LineStyleMap[self._style])
            if self._style is maprenderer.LineStyle.Custom:
                self._qtPen.setDashPattern(self._pattern)
            self._qtPen.setCapStyle(QtMapPen._PenTipMap[self._tip])
        return self._qtPen

class QtMapImage(maprenderer.AbstractImage):
    def __init__(self, path: str):
        self._path = path

        self._qtImage = QtGui.QImage(self._path, None)
        if not self._qtImage:
            raise RuntimeError(f'Failed to load {self._path}')

    def width(self) -> int:
        return self._qtImage.width()
    def height(self) -> int:
        return self._qtImage.height()

    def qtImage(self) -> QtGui.QImage:
        return self._qtImage

class QtMapFont(maprenderer.AbstractFont):
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
            style: maprenderer.FontStyle
            ) -> None:
        self._family = family
        self._emSize = emSize
        self._style = style

        self._font = QtGui.QFont(family)
        if not self._font:
            raise ValueError(f'Unknown font "{family}"')
        self._font.setPointSizeF(QtMapFont._TextPointSize)
        if self._style & maprenderer.FontStyle.Bold:
            self._font.setBold(True)
        if self._style & maprenderer.FontStyle.Italic:
            self._font.setItalic(True)
        if self._style & maprenderer.FontStyle.Underline:
            self._font.setUnderline(True)
        if self._style & maprenderer.FontStyle.Strikeout:
            self._font.setStrikeOut(True)

        self._fontMetrics = QtGui.QFontMetrics(self._font)
        self._lineSpacing = self._fontMetrics.lineSpacing()

        self._sizeCache: typing.Dict[str, typing.Tuple[float, float]] = {}

    def family(self) -> str:
        return self._family

    def emSize(self) -> float:
        return self._emSize

    def style(self) -> maprenderer.FontStyle:
        return self._style

    def pointSize(self) -> float:
        return self._TextPointSize

    def lineSpacing(self) -> float:
        return self._lineSpacing

    def qtMeasureText(self, text: str) -> typing.Tuple[float, float]:
        size = self._sizeCache.get(text)
        if not size:
            rect = self._fontMetrics.tightBoundingRect(text)
            size = (rect.width(), rect.height())
            self._sizeCache[text] = size
        return size

    def qtFont(self) -> QtGui.QFont:
        return self._font

    def qtFontMetrics(self) -> QtGui.QFontMetrics:
        return self._fontMetrics

class QtMapGraphics(maprenderer.AbstractGraphics):
    def __init__(self):
        super().__init__()
        self._painter = None
        self._supportsWingdings = None

    def setPainter(self, painter: QtGui.QPainter) -> None:
        self._painter = painter

        self._painter.setRenderHint(
            QtGui.QPainter.RenderHint.Antialiasing,
            False)
        self._painter.setRenderHint(
            QtGui.QPainter.RenderHint.TextAntialiasing,
            False)
        self._painter.setRenderHint(
            QtGui.QPainter.RenderHint.SmoothPixmapTransform,
            False)
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

    def createRectangle(
            self,
            x: float = 0,
            y: float = 0,
            width: float = 0,
            height: float = 0
            ) -> QtMapRectangleF:
        return QtMapRectangleF(x=x, y=y, width=width, height=height)
    def copyRectangle(self, other: maprenderer.AbstractRectangleF) -> QtMapRectangleF:
        return QtMapRectangleF(other=other)

    def createPointList(
            self,
            points: typing.Sequence[maprenderer.AbstractPointF]
            ) -> QtMapPointList:
        return QtMapPointList(points=points)
    def copyPointList(self, other: maprenderer.AbstractPath) -> QtMapPointList:
        return QtMapPointList(other=other)

    def createPath(
            self,
            points: typing.Sequence[maprenderer.AbstractPointF],
            types: typing.Sequence[maprenderer.PathPointType],
            closed: bool
            ) -> QtMapPath:
        return QtMapPath(points=points, types=types, closed=closed)
    def copyPath(self, other: maprenderer.AbstractPath) -> QtMapPath:
        return QtMapPath(other=other)

    def createIdentityMatrix(self) -> QtMapMatrix:
        return QtMapMatrix()
    def createMatrix(
            self,
            m11: float,
            m12: float,
            m21: float,
            m22: float,
            dx: float,
            dy: float
            ) -> QtMapMatrix:
        return QtMapMatrix(m11=m11, m12=m12, m21=m21, m22=m22, dx=dx, dy=dy)
    def copyMatrix(self, other: QtMapMatrix) -> QtMapMatrix:
        return QtMapMatrix(other=other)

    def createBrush(self, color: str = '') -> QtMapBrush:
        return QtMapBrush(color=color)
    def copyBrush(self, other: maprenderer.AbstractBrush) -> QtMapPath:
        return QtMapPath(other=other)

    def createPen(
            self,
            color: str = '',
            width: float = 1,
            style: maprenderer.LineStyle = maprenderer.LineStyle.Solid,
            pattern: typing.Optional[typing.Sequence[float]] = None,
            tip: maprenderer.PenTip = maprenderer.PenTip.Flat
            ) -> QtMapPen:
        return QtMapPen(color=color, width=width, style=style, pattern=pattern, tip=tip)
    def copyPen(self, other: maprenderer.AbstractPen) -> QtMapPen:
        return QtMapPen(other=other)

    def createImage(
            self,
            path: str
            ) -> QtMapImage:
        return QtMapImage(path=path)

    def createFont(
            self,
            family: str,
            emSize: float,
            style: maprenderer.FontStyle = maprenderer.FontStyle.Regular
            ) -> QtMapFont:
        # TODO: Traveller Map has this as 1.4 (in makeFont) but I found I needed
        # to lower it to get fonts rendering the correct size.
        return QtMapFont(family=family, emSize=emSize * 1.1, style=style)

    # NOTE: Smoothing is disabled as it has a huge performance hit and doesn't seem to
    # give a noticeable improvement
    # TODO: Need to check this on other OS
    def setSmoothingMode(self, mode: maprenderer.AbstractGraphics.SmoothingMode):
        """
        antialias = mode == maprenderer.AbstractGraphics.SmoothingMode.HighQuality or \
            mode == maprenderer.AbstractGraphics.SmoothingMode.AntiAlias

        self._painter.setRenderHint(
            QtGui.QPainter.RenderHint.Antialiasing,
            antialias)
        self._painter.setRenderHint(
            QtGui.QPainter.RenderHint.TextAntialiasing,
            antialias)
        self._painter.setRenderHint(
            QtGui.QPainter.RenderHint.SmoothPixmapTransform,
            antialias)
        """
        pass

    def scaleTransform(self, scaleX: float, scaleY: float) -> None:
        if scaleX == 1.0 and scaleY == 1.0:
            return
        transform = QtGui.QTransform()
        transform.scale(scaleX, scaleY)
        self._painter.setTransform(
            transform * self._painter.transform())
    def translateTransform(self, dx: float, dy: float) -> None:
        if dx == 0.0 and dy == 0.0:
            return
        transform = QtGui.QTransform()
        transform.translate(dx, dy)
        self._painter.setTransform(
            transform * self._painter.transform())
    def rotateTransform(self, degrees: float) -> None:
        if degrees == 0.0:
            return
        transform = QtGui.QTransform()
        transform.rotate(degrees, QtCore.Qt.Axis.ZAxis)
        self._painter.setTransform(
            transform * self._painter.transform())
    def multiplyTransform(self, matrix: QtMapMatrix) -> None:
        self._painter.setTransform(
            matrix.qtMatrix() * self._painter.transform())

    # TODO: This was an overload of intersectClip in traveller map code
    def intersectClipPath(self, path: QtMapPath) -> None:
        clipPath = self._painter.clipPath()
        clipPath.setFillRule(QtCore.Qt.FillRule.WindingFill)
        clipPath.addPolygon(path.qtPolygon())
        self._painter.setClipPath(clipPath, operation=QtCore.Qt.ClipOperation.IntersectClip)
    # TODO: This was an overload of intersectClip in traveller map code
    def intersectClipRect(self, rect: QtMapRectangleF) -> None:
        clipPath = self._painter.clipPath()
        clipPath.setFillRule(QtCore.Qt.FillRule.WindingFill)
        clipPath.addRect(rect.qtRect())
        self._painter.setClipPath(clipPath, operation=QtCore.Qt.ClipOperation.IntersectClip)

    def drawPoint(self, point: maprenderer.AbstractPointF, pen: QtMapPen) -> None:
        self._painter.setPen(pen.qtPen())
        self._painter.drawPoint(self._convertPoint(point))
    def drawPoints(self, points: QtMapPointList, pen: QtMapPen) -> None:
        self._painter.setPen(pen.qtPen())
        self._painter.drawPoints(points.qtPolygon())

    # TODO: There was also an overload that takes 4 individual floats in the traveller map code
    def drawLine(
            self,
            pt1: maprenderer.AbstractPointF,
            pt2: maprenderer.AbstractPointF,
            pen: QtMapPen
            ) -> None:
        self._painter.setPen(pen.qtPen())
        self._painter.drawLine(
            self._convertPoint(pt1),
            self._convertPoint(pt2))
    def drawLines(
            self,
            points: QtMapPointList,
            pen: QtMapPen
            ) -> None:
        self._painter.setPen(pen.qtPen())
        self._painter.drawLines(points.qtPolygon())

    def drawPath(
            self,
            path: QtMapPath,
            pen: typing.Optional[QtMapPen] = None,
            brush: typing.Optional[QtMapBrush] = None
            ) -> None:
        self._painter.setPen(pen.qtPen() if pen else QtCore.Qt.PenStyle.NoPen)
        self._painter.setBrush(brush.qtBrush() if brush else QtCore.Qt.BrushStyle.NoBrush)
        if path.closed():
            self._painter.drawPolygon(path.qtPolygon())
        else:
            self._painter.drawPolyline(path.qtPolygon())

    def drawRectangle(
            self,
            rect: QtMapRectangleF,
            pen: typing.Optional[QtMapPen] = None,
            brush: typing.Optional[QtMapBrush] = None
            ) -> None:
        self._painter.setPen(pen.qtPen() if pen else QtCore.Qt.PenStyle.NoPen)
        self._painter.setBrush(brush.qtBrush() if brush else QtCore.Qt.BrushStyle.NoBrush)
        self._painter.drawRect(rect.qtRect())

    # TODO: This has changed quite a bit from the traveller map interface
    def drawEllipse(
            self,
            rect: QtMapRectangleF,
            pen: typing.Optional[QtMapPen] = None,
            brush: typing.Optional[QtMapBrush] = None
            ) -> None:
        self._painter.setPen(pen.qtPen() if pen else QtCore.Qt.PenStyle.NoPen)
        self._painter.setBrush(brush.qtBrush() if brush else QtCore.Qt.BrushStyle.NoBrush)
        self._painter.drawEllipse(rect.qtRect())

    def drawArc(
            self,
            rect: QtMapRectangleF,
            startDegrees: float,
            sweepDegrees: float,
            pen: QtMapPen
            ) -> None:
        self._painter.setPen(pen.qtPen())
        # NOTE: Angles are in 1/16th of a degree
        self._painter.drawArc(
            rect.qtRect(),
            int((startDegrees * 16) + 0.5),
            int((sweepDegrees * 16) + 0.5))

    def drawImage(
            self,
            image: QtMapImage,
            rect: QtMapRectangleF
            ) -> None:
        self._painter.drawImage(
            rect.qtRect(),
            image.qtImage())
    def drawImageAlpha(
            self,
            alpha: float,
            image: QtMapImage,
            rect: QtMapRectangleF
            ) -> None:
        oldAlpha = self._painter.opacity()
        self._painter.setOpacity(alpha)
        try:
            self._painter.drawImage(
                rect.qtRect(),
                image.qtImage())
        finally:
            self._painter.setOpacity(oldAlpha)

    def measureString(
            self,
            text: str,
            font: QtMapFont
            ) -> typing.Tuple[float, float]: # (width, height)
        qtFont = font.qtFont()
        scale = font.emSize() / qtFont.pointSizeF()

        # TODO: Not sure if this should use bounds or tight bounds. It needs to
        # be correct for what will actually be rendered for different alignments
        contextX, contentY = font.qtMeasureText(text)
        return (contextX * scale, contentY * scale)

    def drawString(
            self,
            text: str,
            font: QtMapFont,
            brush: QtMapBrush,
            x: float, y: float,
            format: maprenderer.TextAlignment
            ) -> None:
        qtFont = font.qtFont()
        qtFontMetrics = font.qtFontMetrics()
        scale = font.emSize() / qtFont.pointSizeF()

        contentX, contentY = font.qtMeasureText(text)
        leftPadding = 0
        topPadding = qtFontMetrics.descent()

        self._painter.save()
        try:
            self.translateTransform(x, y)
            self.scaleTransform(scale, scale)

            self._painter.setFont(qtFont)
            # TODO: It looks like Qt uses a pen for text rather than the brush
            # it may make more sense for it to just be a colour that is passed
            # to drawString. This means the call to setBrush can probably be
            # removed
            qtBrush = brush.qtBrush()
            self._painter.setPen(qtBrush.color())
            self._painter.setBrush(qtBrush)

            if format == maprenderer.TextAlignment.Baseline:
                # TODO: Handle BaseLine strings. I'm thinking just drop support
                # for it as nothing seems to use it
                #float fontUnitsToWorldUnits = font.Size / font.FontFamily.GetEmHeight(font.Style);
                #float ascent = font.FontFamily.GetCellAscent(font.Style) * fontUnitsToWorldUnits;
                #g.DrawString(s, font.Font, this.brush, x, y - ascent);
                self._painter.drawText(QtCore.QPointF(x, y), text)
            elif format == maprenderer.TextAlignment.Centered:
                self._painter.drawText(
                    QtCore.QPointF(
                        (-contentX / 2) - (leftPadding / 2),
                        (contentY / 2) - (topPadding / 2)),
                    text)
            elif format == maprenderer.TextAlignment.TopLeft:
                self._painter.drawText(
                    QtCore.QPointF(
                        leftPadding,
                        contentY),
                    text)
            elif format == maprenderer.TextAlignment.TopCenter:
                self._painter.drawText(
                    QtCore.QPointF(
                        (-contentX / 2) - (leftPadding / 2),
                        contentY),
                    text)
            elif format == maprenderer.TextAlignment.TopRight:
                self._painter.drawText(
                    QtCore.QPointF(
                        -contentX - leftPadding,
                        contentY),
                    text)
            elif format == maprenderer.TextAlignment.MiddleLeft:
                self._painter.drawText(
                    QtCore.QPointF(
                        leftPadding,
                        (contentY / 2) - (topPadding / 2)),
                    text)
            elif format == maprenderer.TextAlignment.MiddleRight:
                self._painter.drawText(
                    QtCore.QPointF(
                        -contentX - leftPadding,
                        (contentY / 2) - (topPadding / 2)),
                    text)
            elif format == maprenderer.TextAlignment.BottomLeft:
                self._painter.drawText(
                    QtCore.QPointF(leftPadding, -topPadding),
                    text)
            elif format == maprenderer.TextAlignment.BottomCenter:
                self._painter.drawText(
                    QtCore.QPointF(
                        (-contentX / 2) - (leftPadding / 2),
                        -topPadding),
                    text)
            elif format == maprenderer.TextAlignment.BottomRight:
                self._painter.drawText(
                    QtCore.QPointF(
                        -contentX - leftPadding,
                        -topPadding),
                    text)
        finally:
            self._painter.restore()

    def save(self) -> maprenderer.AbstractGraphicsState:
        self._painter.save()
        return maprenderer.AbstractGraphicsState(graphics=self)
    def restore(self) -> None:
        self._painter.restore()

    def _convertPoint(self, point: maprenderer.AbstractPointF) -> QtCore.QPointF:
        return QtCore.QPointF(point.x(), point.y())

    def _convertPoints(
            self,
            points: typing.Sequence[maprenderer.AbstractPointF]
            ) -> typing.Sequence[QtCore.QPointF]:
        return [QtCore.QPointF(p.x(), p.y()) for p in points]
