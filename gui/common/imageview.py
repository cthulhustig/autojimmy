import typing
from PyQt5 import QtWidgets, QtCore, QtGui

class ImageView(QtWidgets.QGraphicsView):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._pixmap = None

        self.setTransformationAnchor(
            QtWidgets.QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setDragMode(QtWidgets.QGraphicsView.DragMode.ScrollHandDrag)
        self.setCacheMode(QtWidgets.QGraphicsView.CacheModeFlag.CacheNone)
        self.setViewportUpdateMode(
            QtWidgets.QGraphicsView.ViewportUpdateMode.FullViewportUpdate)

    def imageFromBytes(
            self,
            data: bytes,
            type: str # e.g. 'PNG'
            ) -> bool:
        if not self._pixmap:
            self._pixmap = QtGui.QPixmap()
        if not self._pixmap.loadFromData(data, type):
            self.clear()
            return False
        # Create a new scene otherwise the widget doesn't redraw
        scene = QtWidgets.QGraphicsScene()
        scene.setSceneRect(0, 0, self._pixmap.width(), self._pixmap.height())
        self.setScene(scene)
        self.resetTransform()

    def currentScale(self) -> typing.Tuple[float, float]:
        transform = self.transform()
        return (transform.m11(), transform.m22())

    def clear(self) -> None:
        self._pixmap = None

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        if event.modifiers() == QtCore.Qt.KeyboardModifier.ShiftModifier:
            xScale, yScale = self.currentScale()
            viewRect = self.rect()
            sceneRect = self.sceneRect()

            if event.angleDelta().y() > 0:
                # Prevent further zooming in if the zoom in either axis is already at or
                # greater than the max
                if xScale >= 4 or yScale >= 4: # TODO: Should be a constant
                    return

                xScale *= 1.25 # TODO: Should be a constant
                yScale *= 1.25
            else:
                # Prevent further zooming out if the the current scaled scene fits completely
                # in the view
                if ((sceneRect.width() * xScale) < viewRect.height()) and \
                        ((sceneRect.height() * yScale) < viewRect.height()):
                    return

                xScale *= 0.8 # TODO: Should be a constant
                yScale *= 0.8

            self.resetTransform()
            self.scale(xScale, yScale)
            return
        return super().wheelEvent(event)

    def drawBackground(self, painter: QtGui.QPainter, rect: QtCore.QRectF) -> None:
        if not self._pixmap:
            return super().drawBackground(painter, rect)

        viewportRect = self.viewport().rect()
        scale = viewportRect.width() / rect.width()
        copyRect = rect.intersected(QtCore.QRectF(self._pixmap.rect()))

        pixmapSection = self._pixmap.copy(copyRect.toRect())
        pixmapSection = pixmapSection.scaledToWidth(
            round(copyRect.width() * scale),
            QtCore.Qt.TransformationMode.SmoothTransformation)

        drawRect = QtCore.QRect(
            0 if rect.left() >= 0 else round(abs(rect.left()) * scale),
            0 if rect.top() >= 0 else round(abs(rect.top()) * scale),
            round(copyRect.width() * scale),
            round(copyRect.height() * scale))

        painter.save()
        painter.resetTransform()
        painter.drawPixmap(drawRect, pixmapSection, pixmapSection.rect())
        painter.restore()
