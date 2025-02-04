import maprenderer
import typing
from PyQt5 import QtCore, QtGui

class QtMapGraphics(maprenderer.AbstractGraphics):
    _DashStyleMap = {
        maprenderer.DashStyle.Solid: QtCore.Qt.PenStyle.SolidLine,
        maprenderer.DashStyle.Dot: QtCore.Qt.PenStyle.DotLine,
        maprenderer.DashStyle.Dash: QtCore.Qt.PenStyle.DashLine,
        maprenderer.DashStyle.DashDot: QtCore.Qt.PenStyle.DashDotLine,
        maprenderer.DashStyle.DashDotDot: QtCore.Qt.PenStyle.DashDotDotLine,
        maprenderer.DashStyle.Custom: QtCore.Qt.PenStyle.CustomDashLine}

    def __init__(self):
        super().__init__()
        self._painter = None
        self._supportsWingdings = None

    def setPainter(self, painter: QtGui.QPainter) -> None:
        self._painter = painter

        # Highest quality by default
        self._painter.setRenderHint(
            QtGui.QPainter.RenderHint.Antialiasing,
            True)
        self._painter.setRenderHint(
            QtGui.QPainter.RenderHint.TextAntialiasing,
            True)
        self._painter.setRenderHint(
            QtGui.QPainter.RenderHint.SmoothPixmapTransform,
            True)
        self._painter.setRenderHint(
            QtGui.QPainter.RenderHint.LosslessImageRendering,
            True)

    def setSmoothingMode(self, mode: maprenderer.AbstractGraphics.SmoothingMode):
        super().setSmoothingMode(mode)

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

    def scaleTransform(self, scaleX: float, scaleY: float) -> None:
        transform = QtGui.QTransform()
        transform.scale(scaleX, scaleY)
        self._painter.setTransform(
            transform * self._painter.transform())
    def translateTransform(self, dx: float, dy: float) -> None:
        transform = QtGui.QTransform()
        transform.translate(dx, dy)
        self._painter.setTransform(
            transform * self._painter.transform())
    def rotateTransform(self, degrees: float) -> None:
        transform = QtGui.QTransform()
        transform.rotate(degrees, QtCore.Qt.Axis.ZAxis)
        self._painter.setTransform(
            transform * self._painter.transform())
    def multiplyTransform(self, matrix: maprenderer.AbstractMatrix) -> None:
        self._painter.setTransform(
            self._convertMatrix(matrix) * self._painter.transform())

    # TODO: This was an overload of intersectClip in traveller map code
    def intersectClipPath(self, path: maprenderer.AbstractPath) -> None:
        clipPath = self._painter.clipPath()
        clipPath.setFillRule(QtCore.Qt.FillRule.WindingFill)
        clipPath.addPolygon(self._convertPath(path))
        self._painter.setClipPath(clipPath, operation=QtCore.Qt.ClipOperation.IntersectClip)
    # TODO: This was an overload of intersectClip in traveller map code
    def intersectClipRect(self, rect: maprenderer.AbstractRectangleF) -> None:
        clipPath = self._painter.clipPath()
        clipPath.setFillRule(QtCore.Qt.FillRule.WindingFill)
        clipPath.addRect(self._convertRect(rect))
        self._painter.setClipPath(clipPath, operation=QtCore.Qt.ClipOperation.IntersectClip)

    # TODO: There was also an overload that takes 4 individual floats in the traveller map code
    def drawLine(
            self,
            pen: maprenderer.AbstractPen,
            pt1: maprenderer.AbstractPointF,
            pt2: maprenderer.AbstractPointF
            ) -> None:
        self._painter.setPen(self._convertPen(pen))
        self._painter.drawLine(
            self._convertPoint(pt1),
            self._convertPoint(pt2))

    def drawLines(self, pen: maprenderer.AbstractPen, points: typing.Sequence[maprenderer.AbstractPointF]):
        self._painter.setPen(self._convertPen(pen))
        self._painter.drawPolyline(self._convertPoints(points))

    # TODO: I don't know if a path is a segmented line or a closed polygon
    # TODO: This was an overload of drawPath in the traveller map code
    def drawPathOutline(self, pen: maprenderer.AbstractPen, path: maprenderer.AbstractPath):
        self._painter.setPen(self._convertPen(pen))
        self._painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        if path.closed:
            self._painter.drawPolygon(self._convertPath(path))
        else:
            self._painter.drawPolyline(self._convertPoints(path.points()))
    # TODO: This was an overload of drawPath in the traveller map code
    def drawPathFill(self, brush: maprenderer.AbstractBrush, path: maprenderer.AbstractPath):
        self._painter.setPen(QtCore.Qt.PenStyle.NoPen)
        self._painter.setBrush(self._convertBrush(brush))
        self._painter.drawPolygon(self._convertPath(path))

    def drawCurve(self, pen: maprenderer.AbstractPen, path: maprenderer.AbstractPath, tension: float = 0.5):
        self.drawLines(pen=pen, points=path.points())
    # TODO: This was an overload of drawClosedCurve in the traveller map code
    def drawClosedCurveOutline(self, pen: maprenderer.AbstractPen, path: maprenderer.AbstractPath, tension: float = 0.5):
        self.drawPathOutline(pen=pen, path=path)
    def drawClosedCurveFill(self, brush: maprenderer.AbstractBrush, path: maprenderer.AbstractPath, tension: float = 0.5):
        self.drawPathOutline(brush=brush, path=path)

    # TODO: There was also an overload that takes 4 individual floats in the traveller map code
    def drawRectangleOutline(self, pen: maprenderer.AbstractPen, rect: maprenderer.AbstractRectangleF) -> None:
        self._painter.setPen(self._convertPen(pen))
        self._painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        self._painter.drawRect(self._convertRect(rect))
    # TODO: There was also an overload that takes 4 individual floats in the traveller map code
    def drawRectangleFill(self, brush: maprenderer.AbstractBrush, rect: maprenderer.AbstractRectangleF) -> None:
        self._painter.setPen(QtCore.Qt.PenStyle.NoPen)
        self._painter.setBrush(self._convertBrush(brush))
        self._painter.drawRect(self._convertRect(rect))

    # TODO: This has changed quite a bit from the traveller map interface
    def drawEllipse(
            self,
            pen: typing.Optional[maprenderer.AbstractPen],
            brush: typing.Optional[maprenderer.AbstractBrush],
            rect: maprenderer.AbstractRectangleF
            ) -> None:
        self._painter.setPen(self._convertPen(pen) if pen else QtCore.Qt.PenStyle.NoPen)
        self._painter.setBrush(self._convertBrush(brush) if brush else QtCore.Qt.BrushStyle.NoBrush)
        self._painter.drawEllipse(self._convertRect(rect))

    def drawArc(
            self,
            pen: maprenderer.AbstractPen,
            rect: maprenderer.AbstractRectangleF,
            startDegrees: float,
            sweepDegrees: float
            ) -> None:
        self._painter.setPen(self._convertPen(pen))
        # NOTE: Angles are in 1/16th of a degree
        self._painter.drawArc(
            self._convertRect(rect),
            int((startDegrees * 16) + 0.5),
            int((sweepDegrees * 16) + 0.5))

    def drawImage(
            self,
            image: maprenderer.AbstractImage,
            rect: maprenderer.AbstractRectangleF
            ) -> None:
        self._painter.drawImage(
            self._convertRect(rect),
            image.qtImage())
    def drawImageAlpha(
            self,
            alpha: float,
            image: maprenderer.AbstractImage,
            rect: maprenderer.AbstractRectangleF
            ) -> None:
        oldAlpha = self._painter.opacity()
        self._painter.setOpacity(alpha)
        try:
            self._painter.drawImage(
                self._convertRect(rect),
                image.qtImage())
        finally:
            self._painter.setOpacity(oldAlpha)

    def measureString(
            self,
            text: str,
            font: maprenderer.AbstractFont
            ) -> maprenderer.AbstractSizeF:
        qtFont = self._convertFont(font)
        scale = font.emSize() / qtFont.pointSize()

        fontMetrics = QtGui.QFontMetrics(qtFont)
        # TODO: Not sure if this should use bounds or tight bounds. It needs to
        # be correct for what will actually be rendered for different alignments
        contentPixelRect = fontMetrics.tightBoundingRect(text)
        #contentPixelRect = fontMetrics.boundingRect(text)
        contentPixelRect.moveTo(0, 0)

        return maprenderer.AbstractSizeF(contentPixelRect.width() * scale, contentPixelRect.height() * scale)

    def drawString(
            self,
            text: str,
            font: maprenderer.AbstractFont,
            brush: maprenderer.AbstractBrush,
            x: float, y: float,
            format: maprenderer.StringAlignment
            ) -> None:
        qtFont = self._convertFont(font)
        scale = font.emSize() / qtFont.pointSize()

        self._painter.setFont(qtFont)
        # TODO: It looks like Qt uses a pen for text rather than the brush
        # it may make more sense for it to just be a colour that is passed
        # to drawString
        self._painter.setPen(QtGui.QColor(brush.color))
        self._painter.setBrush(self._convertBrush(brush))

        fontMetrics = QtGui.QFontMetrics(qtFont)
        # TODO: Not sure if this should use bounds or tight bounds. It needs to
        # be correct for what will actually be rendered for different alignments
        """
        contentPixelRect = fontMetrics.tightBoundingRect(text)
        fullPixelRect = fontMetrics.boundingRect(text)
        leftPadding = contentPixelRect.x() - fullPixelRect.x()
        topPadding = contentPixelRect.y() - fullPixelRect.y()
        """
        contentPixelRect = fontMetrics.tightBoundingRect(text)
        leftPadding = 0
        topPadding = fontMetrics.descent()

        self._painter.save()
        try:
            self.translateTransform(x, y)
            self.scaleTransform(scale, scale)

            if format == maprenderer.StringAlignment.Baseline:
                # TODO: Handle BaseLine strings
                #float fontUnitsToWorldUnits = font.Size / font.FontFamily.GetEmHeight(font.Style);
                #float ascent = font.FontFamily.GetCellAscent(font.Style) * fontUnitsToWorldUnits;
                #g.DrawString(s, font.Font, this.brush, x, y - ascent);
                self._painter.drawText(QtCore.QPointF(x, y), text)
            elif format == maprenderer.StringAlignment.Centered:
                self._painter.drawText(
                    QtCore.QPointF(
                        (-contentPixelRect.width() / 2) - (leftPadding / 2),
                        (contentPixelRect.height() / 2) - (topPadding / 2)),
                    text)
            elif format == maprenderer.StringAlignment.TopLeft:
                self._painter.drawText(
                    QtCore.QPointF(
                        0 + leftPadding,
                        contentPixelRect.height() + topPadding),
                    text)
            elif format == maprenderer.StringAlignment.TopCenter:
                self._painter.drawText(
                    QtCore.QPointF(
                        (-contentPixelRect.width() / 2) - (leftPadding / 2),
                        contentPixelRect.height() + topPadding),
                    text)
            elif format == maprenderer.StringAlignment.TopRight:
                self._painter.drawText(
                    QtCore.QPointF(
                        -contentPixelRect.width() - leftPadding,
                        contentPixelRect.height() + topPadding),
                    text)
            elif format == maprenderer.StringAlignment.CenterLeft:
                self._painter.drawText(
                    QtCore.QPointF(
                        0 + leftPadding,
                        (contentPixelRect.height() / 2) - (topPadding / 2)),
                    text)
            elif format == maprenderer.StringAlignment.CenterRight:
                self._painter.drawText(
                    QtCore.QPointF(
                        -contentPixelRect.width() - leftPadding,
                        (contentPixelRect.height() / 2) - (topPadding / 2)),
                    text)
            elif format == maprenderer.StringAlignment.BottomLeft:
                self._painter.drawText(
                    QtCore.QPointF(
                        0 + leftPadding,
                        contentPixelRect.height()),
                    text)
            elif format == maprenderer.StringAlignment.BottomCenter:
                self._painter.drawText(
                    QtCore.QPointF(
                        (-contentPixelRect.width() / 2) - (leftPadding / 2),
                        contentPixelRect.height()),
                    text)
            elif format == maprenderer.StringAlignment.BottomRight:
                self._painter.drawText(
                    QtCore.QPointF(
                        -contentPixelRect.width() - leftPadding,
                        contentPixelRect.height()),
                    text)
        finally:
            self._painter.restore()

    def save(self) -> maprenderer.AbstractGraphicsState:
        self._painter.save()
        return maprenderer.AbstractGraphicsState(graphics=self)
    def restore(self) -> None:
        self._painter.restore()

    # TODO: Creating a new pen for every primitive that gets drawn is
    # really inefficient. The fact I'm using a string for the colour
    # so it will need to be parsed each time is even worse
    def _convertPen(self, pen: maprenderer.AbstractPen) -> QtGui.QPen:
        qtColor = QtGui.QColor(pen.color)
        qtStyle = QtMapGraphics._DashStyleMap[pen.dashStyle]
        qtPen = QtGui.QPen(qtColor, pen.width, qtStyle)
        if qtStyle == QtCore.Qt.PenStyle.CustomDashLine:
            qtPen.setDashPattern(pen.customDashPattern)
        return qtPen

    # TODO: Creating a new font for every piece of text that gets drawn is
    # really inefficient. The fact I'm using a string for the colour
    # so it will need to be parsed each time is even worse
    def _convertFont(self, font: maprenderer.AbstractFont) -> QtGui.QFont:
        # TODO: This is a temp hack, AbstractFont shouldn't be using QFont
        return font.qtFont()

    def _convertBrush(self, brush: maprenderer.AbstractBrush) -> QtGui.QBrush:
        return QtGui.QBrush(QtGui.QColor(brush.color))

    def _convertRect(self, rect: maprenderer.AbstractRectangleF) -> QtCore.QRectF:
        return QtCore.QRectF(rect.x(), rect.y(), rect.width(), rect.height())

    def _convertPoint(self, point: maprenderer.AbstractPointF) -> QtCore.QPointF:
        return QtCore.QPointF(point.x(), point.y())

    def _convertPoints(
            self,
            points: typing.Sequence[maprenderer.AbstractPointF]
            ) -> typing.Sequence[QtCore.QPointF]:
        return [QtCore.QPointF(p.x(), p.y()) for p in points]

    def _convertPath(self, path: maprenderer.AbstractPath) -> QtGui.QPolygonF:
        return QtGui.QPolygonF(self._convertPoints(path.points()))

    def _convertMatrix(self, transform: maprenderer.AbstractMatrix) -> QtGui.QTransform:
        return QtGui.QTransform(
            transform.m11(),
            transform.m12(),
            0,
            transform.m21(),
            transform.m22(),
            0,
            transform.offsetX(),
            transform.offsetY(),
            1)
