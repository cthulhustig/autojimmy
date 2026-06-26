
import astronomer
import common
import gui
import math
import cartographer
import typing
from PyQt5 import QtCore, QtGui

# TODO: This should be private
class BoundsGraphics(cartographer.AbstractGraphics):
    def __init__(self):
        super().__init__()
        self._transformStack: typing.List[QtGui.QTransform] = []
        self._bounds: typing.Optional[cartographer.RectangleF] = None

    def bounds(self) -> typing.Optional[cartographer.RectangleF]:
        return self._bounds

    def reset(self) -> None:
        self._bounds = None

    def supportsWingdings(self) -> bool:
        return True

    def createPointList(
            self,
            points: typing.Sequence[cartographer.PointF]
            ) -> gui.MapPointList:
        return gui.MapPointList(points=points)

    def copyPointList(self, other: gui.MapPointList) -> gui.MapPointList:
        return gui.MapPointList(other=other)

    def createPath(
            self,
            points: typing.Sequence[cartographer.PointF],
            closed: bool
            ) -> gui.MapPath:
        return gui.MapPath(points=points, closed=closed)

    def copyPath(self, other: gui.MapPath) -> gui.MapPath:
        return gui.MapPath(other=other)

    def createSpline(
            self,
            points: typing.Sequence[cartographer.PointF],
            tension: float,
            closed: bool
            ) -> gui.MapSpline:
        return gui.MapSpline(points=points, tension=tension, closed=closed)

    def copySpline(self, other: gui.MapSpline) -> gui.MapSpline:
        return gui.MapSpline(other=other)

    def createIdentityMatrix(self) -> gui.MapMatrix:
        return gui.MapMatrix()

    def createMatrix(
            self,
            m11: float,
            m12: float,
            m21: float,
            m22: float,
            dx: float,
            dy: float
            ) -> gui.MapMatrix:
        return gui.MapMatrix(m11=m11, m12=m12, m21=m21, m22=m22, dx=dx, dy=dy)

    def createBrush(self, colour: str = '') -> gui.MapBrush:
        return gui.MapBrush(colour=colour)

    def copyBrush(self, other: gui.MapBrush) -> gui.MapBrush:
        return gui.MapPath(other=other)

    def createPen(
            self,
            colour: str = '',
            width: float = 1,
            style: cartographer.LineStyle = cartographer.LineStyle.Solid,
            pattern: typing.Optional[typing.Sequence[float]] = None,
            tip: cartographer.PenTip = cartographer.PenTip.Flat
            ) -> gui.MapPen:
        return gui.MapPen(colour=colour, width=width, style=style, pattern=pattern, tip=tip)

    def copyPen(self, other: gui.MapPen) -> gui.MapPen:
        return gui.MapPen(other=other)

    def createImage(
            self,
            data: bytes
            ) -> gui.MapImage:
        return gui.MapImage(data=data)

    def createFont(
            self,
            family: str,
            emSize: float,
            style: cartographer.FontStyle = cartographer.FontStyle.Regular
            ) -> gui.MapFont:
        # NOTE: Traveller Map has this as 1.4 (in makeFont) but I found I needed
        # to lower it to get fonts rendering the correct size.
        return gui.MapFont(family=family, emSize=emSize * 1.05, style=style)

    def setSmoothingMode(self, mode: cartographer.AbstractGraphics.SmoothingMode):
        pass

    def setWorldToImageTransform(self, matrix: gui.MapMatrix) -> None:
        self._transformStack.clear()
        self._transformStack.append(QtGui.QTransform())  

    def scaleTransform(self, scaleX: float, scaleY: float) -> None:
        if scaleX == 1.0 and scaleY == 1.0:
            return
        self._transformStack[-1].scale(scaleX, scaleY)

    def translateTransform(self, dx: float, dy: float) -> None:
        if dx == 0.0 and dy == 0.0:
            return
        self._transformStack[-1].translate(dx, dy)

    def rotateTransform(self, degrees: float) -> None:
        if degrees == 0.0:
            return
        self._transformStack[-1].rotate(degrees, QtCore.Qt.Axis.ZAxis)

    def intersectClipPath(self, path: gui.MapPath) -> None:
        pass

    def intersectClipRect(self, rect: cartographer.RectangleF) -> None:
        pass

    def drawPoint(self, point: cartographer.PointF, pen: gui.MapPen) -> None:
        self._expandBoundsForPoint(self._convertPoint(point))

    def drawPoints(self, points: gui.MapPointList, pen: gui.MapPen) -> None:
        self._expandBoundsForRect(points.qtPolygon().boundingRect())

    def drawLine(
            self,
            pt1: cartographer.PointF,
            pt2: cartographer.PointF,
            pen: gui.MapPen
            ) -> None:
        self._expandBoundsForPoint(self._convertPoint(pt1))
        self._expandBoundsForPoint(self._convertPoint(pt2))

    def drawLines(
            self,
            points: gui.MapPointList,
            pen: gui.MapPen
            ) -> None:
        self._expandBoundsForRect(points.qtPolygon().boundingRect())

    def drawPath(
            self,
            path: gui.MapPath,
            pen: typing.Optional[gui.MapPen] = None,
            brush: typing.Optional[gui.MapBrush] = None
            ) -> None:
        self._expandBoundsForRect(path.qtPolygon().boundingRect())

    def drawRectangle(
            self,
            rect: cartographer.RectangleF,
            pen: typing.Optional[gui.MapPen] = None,
            brush: typing.Optional[gui.MapBrush] = None
            ) -> None:
        self._expandBoundsForRect(self._convertRect(rect))

    def drawEllipse(
            self,
            rect: cartographer.RectangleF,
            pen: typing.Optional[gui.MapPen] = None,
            brush: typing.Optional[gui.MapBrush] = None
            ) -> None:
        self._expandBoundsForRect(self._convertRect(rect))

    def drawArc(
            self,
            rect: cartographer.RectangleF,
            startDegrees: float,
            sweepDegrees: float,
            pen: gui.MapPen
            ) -> None:
        self._expandBoundsForRect(self._convertRect(rect))

    def drawImage(
            self,
            image: gui.MapImage,
            rect: cartographer.RectangleF
            ) -> None:
        self._expandBoundsForRect(self._convertRect(rect))

    def drawImageAlpha(
            self,
            alpha: float,
            image: gui.MapImage,
            rect: cartographer.RectangleF
            ) -> None:
        self._expandBoundsForRect(self._convertRect(rect))

    def drawCurve(
            self,
            spline: gui.MapSpline,
            pen: typing.Optional[gui.MapPen] = None,
            brush: typing.Optional[gui.MapBrush] = None
            ) -> None:
        self._expandBoundsForRect(spline.qtPainterPath().boundingRect())

    def measureString(
            self,
            text: str,
            font: gui.MapFont
            ) -> typing.Tuple[float, float]: # (width, height)
        qtFont = font.qtFont()
        scale = font.emSize() / qtFont.pointSizeF()
        rect = font.qtMeasureText(text)
        return (rect.width() * scale, rect.height() * scale)

    def drawString(
            self,
            text: str,
            font: gui.MapFont,
            brush: gui.MapBrush,
            x: float, y: float,
            format: cartographer.TextAlignment
            ) -> None:
        qtFont = font.qtFont()
        textRect = font.qtMeasureText(text)
        scale = font.emSize() / qtFont.pointSizeF()

        if format == cartographer.TextAlignment.Baseline:
            pass
        elif format == cartographer.TextAlignment.Centered:
            textRect.translate(
                -textRect.x() - (textRect.width() / 2),
                -textRect.y() - (textRect.height() / 2))
        elif format == cartographer.TextAlignment.TopLeft:
            textRect.translate(
                -textRect.x(),
                -textRect.y())
        elif format == cartographer.TextAlignment.TopCenter:
            textRect.translate(
                -textRect.x() - (textRect.width() / 2),
                -textRect.y())
        elif format == cartographer.TextAlignment.TopRight:
            textRect.translate(
                -textRect.x() - textRect.width(),
                -textRect.y())
        elif format == cartographer.TextAlignment.MiddleLeft:
            textRect.translate(
                -textRect.x(),
                -textRect.y() - (textRect.height() / 2))
        elif format == cartographer.TextAlignment.MiddleRight:
            textRect.translate(
                -textRect.x() - textRect.width(),
                -textRect.y() - (textRect.height() / 2))
        elif format == cartographer.TextAlignment.BottomLeft:
            textRect.translate(
                -textRect.x(),
                -textRect.y() - textRect.height())
        elif format == cartographer.TextAlignment.BottomCenter:
            textRect.translate(
                -textRect.x() - (textRect.width() / 2),
                -textRect.y() - textRect.height())
        elif format == cartographer.TextAlignment.BottomRight:
            textRect.translate(
                -textRect.x() - textRect.width(),
                -textRect.y() - textRect.height())

        with self.save():
            transform = QtGui.QTransform()
            if x != 0.0 or y != 0.0:
                transform.translate(x, y)
            if scale != 1.0:
                transform.scale(scale, scale)
            self._transformStack[-1] = transform * self._transformStack[-1]

            self._expandBoundsForRect(textRect)

    def save(self) -> cartographer.AbstractGraphicsState:
        if self._transformStack:
            current = self._transformStack[-1]
            self._transformStack.append(QtGui.QTransform(current))
        return cartographer.AbstractGraphicsState(graphics=self)

    def restore(self) -> None:
        if self._transformStack:
            self._transformStack.pop()

    def _expandBoundsForPoint(self, point: QtCore.QPointF) -> None:
        point = self._transformStack[-1].map(point)

        if self._bounds is None:
            self._bounds = cartographer.RectangleF(
                x=point.x(),
                y=point.y(),
                width=0,
                height=0)
            return
        self._bounds.include(point)

    def _expandBoundsForRect(self, rect: QtCore.QRectF) -> None:
        rect = self._transformStack[-1].mapRect(rect)
        rect = cartographer.RectangleF(
                x=rect.x(),
                y=rect.y(),
                width=rect.width(),
                height=rect.height())

        if self._bounds is None:
            self._bounds = rect
            return
        self._bounds.include(rect)

    def _convertPoint(self, point: cartographer.PointF) -> QtCore.QPointF:
        return QtCore.QPointF(point.x(), point.y())

    def _convertRect(
            self,
            rect: cartographer.RectangleF
            ) -> QtCore.QRectF:
        return QtCore.QRectF(rect.x(), rect.y(), rect.width(), rect.height())

class _BoundsSelector(cartographer.AbstractSelector):
    def __init__(self) -> None:
        self._objects = []

        # Sets are used for the sectors/worlds to prevent objects getting added
        # multiple times and therefore getting "rendered" multiple times.
        self._sectors = set()
        self._worlds = set()

    def setObjects(self, objects: typing.Optional[typing.Collection[typing.Union[astronomer.Sector, astronomer.World]]]) -> None:
        self._objects.clear()
        if objects is not None:
            self._objects.extend(objects)
        self._updateSelection()

    def setRect(self, rect: cartographer.RectangleF) -> None:
        pass

    def setMilieu(self, milieu: astronomer.Milieu) -> None:
        pass

    def sectorSlop(self) -> float:
        return 0

    def setSectorSlop(self, slop: float) -> None:
        pass

    def worldSlop(self) -> float:
        return 0

    def setWorldSlop(self, slop: float) -> None:
        pass

    def sectors(self, tight: bool = False) -> typing.Collection[astronomer.Sector]:
        return common.ConstCollectionRef(self._sectors)

    def worlds(self, tight: bool = False) -> typing.Iterable[astronomer.World]:
        return common.ConstCollectionRef(self._worlds)

    def placeholderSectors(self, tight: bool = False) -> typing.Iterable[astronomer.Sector]:
        return []

    def placeholderWorlds(self, tight: bool = False) -> typing.Iterable[astronomer.World]:
        return []

    def clearCaches(self):
        pass

    def _updateSelection(self) -> None:
        self._sectors.clear()
        self._worlds.clear()

        for obj in self._objects:
            if isinstance(obj, astronomer.World):
                self._worlds.add(obj)
            elif isinstance(obj, astronomer.Sector):
                self._sectors.add(obj)
                self._worlds.update(obj.worlds())

class RenderBoundsCalculator(object):
    def __init__(
            self,
            universe: astronomer.Universe,
            milieu: astronomer.Milieu,
            style: cartographer.MapStyle,
            options: cartographer.RenderOptions
            ) -> None:
        self._universe = universe
        self._milieu = milieu
        self._style = style
        self._options = options

        self._graphics = BoundsGraphics()
        self._selector = _BoundsSelector()
        self._imageStore = cartographer.ImageStore(graphics=self._graphics)
        self._vectorStore = cartographer.VectorStore(graphics=self._graphics)
        self._renderer = None

    def setUniverse(self, universe) -> None:
        if self._universe != universe:
            return

        self._universe = universe
        self._renderer = None

    def setMilieu(self, milieu) -> None:
        if self._milieu is not milieu:
            return

        self._milieu = milieu
        self._renderer = None

    def calculateBounds(
            self,
            objects: typing.Collection[typing.Union[astronomer.Sector, astronomer.World]],
            scale: float
            ) -> typing.Optional[cartographer.RectangleF]:
        if self._renderer is None:
            self._createRenderer()

        self._renderer.disableAllLayers()
        self._renderer.enableLayer(cartographer.LayerId.Micro_Routes)
        self._renderer.enableLayer(cartographer.LayerId.Micro_BordersBackground)
        self._renderer.enableLayer(cartographer.LayerId.Micro_BordersForeground)
        self._renderer.enableLayer(cartographer.LayerId.Micro_Labels)
        self._renderer.enableLayer(cartographer.LayerId.Names_Sector)
        self._renderer.enableLayer(cartographer.LayerId.Names_Subsector)
        self._renderer.enableLayer(cartographer.LayerId.Worlds_Background)
        self._renderer.enableLayer(cartographer.LayerId.Worlds_Foreground)
        self._renderer.enableLayer(cartographer.LayerId.Worlds_Overlays)

        self._graphics.reset()

        self._selector.setObjects(objects)
        try:
            self._renderer.renderUniverse(scale=scale)
            return self._graphics.bounds()
        finally:
            self._selector.setObjects(None)

    def clearCaches(self) -> None:
        if self._renderer:
            self._renderer.clearCaches()

    def _createRenderer(self) -> None:
        self._renderer = cartographer.RenderContext(
            universe=self._universe,
            milieu=self._milieu,
            graphics=self._graphics,
            style=self._style,
            options=self._options,
            imageStore=self._imageStore,
            vectorStore=self._vectorStore,
            # TODO: This causes 3 files to be parsed every time the render is recreated
            labelStore=cartographer.LabelStore(universe=self._universe),
            selector=self._selector)


