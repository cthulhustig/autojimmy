import gui
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

class ImageView(QtWidgets.QGraphicsView):
    _ZoomInScale = 1.25
    _ZoomOutScale = 0.8

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._pixmap = None

        self.setTransformationAnchor(
            QtWidgets.QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setDragMode(QtWidgets.QGraphicsView.DragMode.ScrollHandDrag)
        self.setCacheMode(QtWidgets.QGraphicsView.CacheModeFlag.CacheNone)
        self.setViewportUpdateMode(
            QtWidgets.QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.ActionsContextMenu)
        
        self._zoomInAction = QtWidgets.QAction(gui.loadIcon(gui.Icon.ZoomIn), 'Zoom In', self)
        self._zoomInAction.triggered.connect(self.zoomIn)
        self.addAction(self._zoomInAction)

        self._zoomOutAction = QtWidgets.QAction(gui.loadIcon(gui.Icon.ZoomOut), 'Zoom Out', self)
        self._zoomOutAction.triggered.connect(self.zoomOut)
        self.addAction(self._zoomOutAction)

        self._zoomToFitAction = QtWidgets.QAction(gui.loadIcon(gui.Icon.ZoomToFit), 'Zoom To Fit', self)
        self._zoomToFitAction.triggered.connect(self.zoomToFit)
        self.addAction(self._zoomToFitAction)        

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
    
    def zoomIn(self) -> None:
        xScale, yScale = self.currentScale()
        self.resetTransform()
        self.scale(xScale * ImageView._ZoomInScale, yScale * ImageView._ZoomInScale)

    def zoomOut(self) -> None:
        xScale, yScale = self.currentScale()
        self.resetTransform()
        self.scale(xScale * ImageView._ZoomOutScale, yScale * ImageView._ZoomOutScale)

    def zoomToFit(self) -> None:
        viewRect = self.rect()
        sceneRect = self.sceneRect()
        if sceneRect.width() <= 0 or sceneRect.height() <= 0:
            return # Can't scale image with no size

        scale = min(
            viewRect.width() / sceneRect.width(),
            viewRect.height() / sceneRect.height())
        
        self.resetTransform()
        self.scale(scale, scale)

    def clear(self) -> None:
        self._pixmap = None

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        if event.modifiers() == QtCore.Qt.KeyboardModifier.ShiftModifier:
            if event.angleDelta().y() > 0:
                self.zoomIn()
            else:
                self.zoomOut()
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
