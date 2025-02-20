from PyQt5 import QtWidgets, QtCore, QtGui
import app
import common
import gui
import io
import locale
import logging
import maprenderer
import math
import os
import traveller
import travellermap
import typing
import cProfile, pstats, io
from pstats import SortKey

class MapHackView(QtWidgets.QWidget):
    _MinScale = -7
    _MaxScale = 9
    _DefaultCenterX = 0
    _DefaultCenterY = 0
    _DefaultScale = 64
    _DefaultScale = travellermap.logScaleToLinearScale(5.5)
    #_DefaultCenterX, _DefaultCenterY  = (-175,46)

    _WheelScaleMultiplier = 1.5
    _WheelLogScaleDelta = 0.15

    _ZoomInScale = 1.25
    _ZoomOutScale = 0.8

    _TileRendering = False
    _DelayedRendering = False
    _TileSize = 256 # Pixels
    _TileTimerMsecs = 20

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        scene = QtWidgets.QGraphicsScene()
        scene.setSceneRect(0, 0, self.width(), self.height())

        self._absoluteCenterPos = QtCore.QPointF(
            MapHackView._DefaultCenterX,
            MapHackView._DefaultCenterY)
        self._viewScale = travellermap.Scale(value=MapHackView._DefaultScale, linear=True)
        self._options = \
            maprenderer.MapOptions.SectorGrid | maprenderer.MapOptions.SubsectorGrid | \
            maprenderer.MapOptions.SectorsSelected | \
            maprenderer.MapOptions.BordersMajor | maprenderer.MapOptions.BordersMinor | \
            maprenderer.MapOptions.NamesMajor | maprenderer.MapOptions.NamesMinor | \
            maprenderer.MapOptions.WorldsCapitals | maprenderer.MapOptions.WorldsHomeworlds | \
            maprenderer.MapOptions.ForceHexes | maprenderer.MapOptions.WorldColors

        self._style = travellermap.Style.Poster
        #self._style = travellermap.Style.Candy
        self._graphics = gui.QtMapGraphics()
        self._imageCache = maprenderer.ImageCache(
            graphics=self._graphics,
            basePath='./data/map/')
        self._vectorCache = maprenderer.VectorObjectCache(
            graphics=self._graphics,
            basePath='./data/map/')
        self._mapLabelCache = maprenderer.MapLabelCache(basePath='./data/map/')
        self._worldLabelCache = maprenderer.WorldLabelCache(basePath='./data/map/')
        self._styleCache = maprenderer.DefaultStyleCache(basePath='./data/map/')
        maprenderer.WorldHelper.loadData(basePath='./data/map/') # TODO: Not sure where this should live
        self._renderer = self._createRenderer()

        self._worldDragStart: typing.Optional[QtCore.QPointF] = None

        self._tileCache: typing.Dict[
            typing.Tuple[int, int], # Tile space coordinates
            QtGui.QImage] = {}

        self._tileTimer = QtCore.QTimer()
        self._tileTimer.setInterval(MapHackView._TileTimerMsecs)
        self._tileTimer.setSingleShot(True)
        self._tileTimer.timeout.connect(self._handleTileTimer)
        self._tileQueue = []

        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)

    def clear(self) -> None:
        self._graphics = None

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        super().mousePressEvent(event)

        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            worldCursorX, worldCursorY = self._pixelSpaceToWorldSpace(
                pixelX=event.x(),
                pixelY=event.y(),
                clamp=False)
            self._worldDragStart = QtCore.QPointF(worldCursorX, worldCursorY)

            # TODO: Remove debug code
            worldRawX, worldRawY = self._pixelSpaceToWorldSpace(
                pixelX=event.x(),
                pixelY=event.y(),
                clamp=False)
            worldClampedX, worldClampedY = self._pixelSpaceToWorldSpace(
                pixelX=event.x(),
                pixelY=event.y(),
                clamp=True)
            sectorX, sectorY, offsetX, offsetY = travellermap.absoluteSpaceToRelativeSpace(
                (worldClampedX, worldClampedY))
            print(f'RAW: {worldRawX} {worldRawY} ABS: {worldClampedX} {worldClampedY} SECTOR: {sectorX} {sectorY} HEX:{offsetX} {offsetY}')

    # TODO: There is an issue with the drag move where the point you start the
    # drag on isn't staying under the cursor
    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        super().mouseMoveEvent(event)
        if self._renderer and self._worldDragStart:
            worldCurrentPos = self._pixelSpaceToWorldSpace(
                pixelX=event.pos().x(),
                pixelY=event.pos().y(),
                clamp=False) # Float value for extra accuracy
            worldDeltaX = worldCurrentPos[0] - self._worldDragStart.x()
            worldDeltaY = worldCurrentPos[1] - self._worldDragStart.y()

            self._absoluteCenterPos.setX(
                self._absoluteCenterPos.x() - worldDeltaX)
            self._absoluteCenterPos.setY(
                self._absoluteCenterPos.y() - worldDeltaY)
            self._updateRendererView()

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        super().mouseReleaseEvent(event)

        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._worldDragStart = None

    def focusOutEvent(self, event: QtGui.QFocusEvent) -> None:
        super().focusOutEvent(event)
        self._worldDragStart = None

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        self._updateRendererView()

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        super().keyPressEvent(event)

        if self._renderer:
            dx = dy = None
            if event.key() == QtCore.Qt.Key.Key_Left:
                width = self.width() / (self._viewScale.linear * travellermap.ParsecScaleX)
                dx = -width / 10
            elif event.key() == QtCore.Qt.Key.Key_Right:
                width = self.width() / (self._viewScale.linear * travellermap.ParsecScaleX)
                dx = width / 10
            elif event.key() == QtCore.Qt.Key.Key_Up:
                height = self.height() / (self._viewScale.linear * travellermap.ParsecScaleY)
                dy = -height / 10
            elif event.key() == QtCore.Qt.Key.Key_Down:
                height = self.height() / (self._viewScale.linear * travellermap.ParsecScaleY)
                dy = height / 10

            if dx != None or dy != None:
                if dx != None:
                    self._absoluteCenterPos.setX(self._absoluteCenterPos.x() + dx)
                if dy != None:
                    self._absoluteCenterPos.setY(self._absoluteCenterPos.y() + dy)
                self._updateRendererView()

            if event.key() == QtCore.Qt.Key.Key_F1:
                self._debugHack()
            elif event.key() == QtCore.Qt.Key.Key_F2:
                self._style = common.incrementEnum(
                    value=self._style,
                    count=1)
                if self._renderer:
                    self._renderer.setStyle(self._style)
                self._clearTileCache()
            elif event.key() == QtCore.Qt.Key.Key_F3:
                self._style = common.decrementEnum(
                    value=self._style,
                    count=1)
                if self._renderer:
                    self._renderer.setStyle(self._style)
                self._clearTileCache()
            elif event.key() == QtCore.Qt.Key.Key_F7:
                self.update()

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        super().wheelEvent(event)

        if self._renderer:
            cursorScreenPos = event.pos()
            oldWorldCursorX, oldWorldCursorY = self._pixelSpaceToWorldSpace(
                pixelX=cursorScreenPos.x(),
                pixelY=cursorScreenPos.y(),
                clamp=False) # Float value for extra accuracy

            logViewScale = self._viewScale.log
            logViewScale += MapHackView._WheelLogScaleDelta if event.angleDelta().y() > 0 else -MapHackView._WheelLogScaleDelta
            logViewScale = common.clamp(logViewScale, MapHackView._MinScale, MapHackView._MaxScale)
            self._viewScale.log = logViewScale

            # Clear tile cache so it repopulates for the new scale
            self._tileCache.clear()

            newWorldCursorX, newWorldCursorY = self._pixelSpaceToWorldSpace(
                pixelX=cursorScreenPos.x(),
                pixelY=cursorScreenPos.y(),
                clamp=False)

            self._absoluteCenterPos.setX(
                self._absoluteCenterPos.x() + (oldWorldCursorX - newWorldCursorX))
            self._absoluteCenterPos.setY(
                self._absoluteCenterPos.y() + (oldWorldCursorY - newWorldCursorY))

            self._updateRendererView()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        if not self._graphics or not self._renderer:
            return super().paintEvent(event)

        # TODO: Remove debug timer
        with common.DebugTimer('Draw Time'):
            if MapHackView._TileRendering:
                tiles = self._currentDrawTiles()

                painter = QtGui.QPainter(self)
                try:
                    for x, y, image in tiles:
                        painter.drawImage(QtCore.QPointF(x, y), image)
                finally:
                    painter.end()
            else:
                painter = QtGui.QPainter(self)
                try:
                    self._graphics.setPainter(painter=painter)
                    self._renderer.setView(
                        absoluteCenterX=self._absoluteCenterPos.x(),
                        absoluteCenterY=self._absoluteCenterPos.y(),
                        scale=self._viewScale.linear,
                        outputPixelX=self.width(),
                        outputPixelY=self.height())
                    self._renderer.render()
                finally:
                    painter.end()

    def _pixelSpaceToWorldSpace(
            self,
            pixelX: float,
            pixelY: float,
            clamp: bool = False
            ) -> typing.Tuple[float, float]:
        scaleX = (self._viewScale.linear * travellermap.ParsecScaleX)
        scaleY = (self._viewScale.linear * travellermap.ParsecScaleY)

        width = self.width() / scaleX
        height = self.height() / scaleY

        offsetX = pixelX / scaleX
        offsetY = pixelY / scaleY

        worldX = (self._absoluteCenterPos.x() - (width / 2)) + offsetX
        worldY = (self._absoluteCenterPos.y() - (height / 2)) + offsetY

        if not clamp:
            return (worldX, worldY)
        return (
            round(worldX + 0.5),
            round(worldY + (0.5 if (worldX % 2) == 0 else 0)))

    def _worldSpaceToPixelSpace(
            self,
            worldX: float,
            worldY: float
            ) -> typing.Tuple[float, float]:
        scaleX = (self._viewScale.linear * travellermap.ParsecScaleX)
        scaleY = (self._viewScale.linear * travellermap.ParsecScaleY)

        width = self.width() / scaleX
        height = self.height() / scaleY

        offsetX = worldX - (self._absoluteCenterPos.x() - (width / 2))
        offsetY = worldY - (self._absoluteCenterPos.y() - (height / 2))

        pixelX = offsetX * scaleX
        pixelY = offsetY * scaleY

        return (pixelX, pixelY)

    def _createRenderer(self) -> maprenderer.RenderContext:
        return maprenderer.RenderContext(
            graphics=self._graphics,
            absoluteCenterX=self._absoluteCenterPos.x(),
            absoluteCenterY=self._absoluteCenterPos.y(),
            scale=self._viewScale.linear,
            outputPixelX=self.width(),
            outputPixelY=self.height(),
            style=self._style,
            imageCache=self._imageCache,
            vectorCache=self._vectorCache,
            mapLabelCache=self._mapLabelCache,
            worldLabelCache=self._worldLabelCache,
            styleCache=self._styleCache,
            options=self._options)

    def _updateRendererView(self) -> None:
        if not self._renderer:
            self._renderer = self._createRenderer()
            return
        # This shouldn't be needed when using tile rendering
        """
        self._renderer.setView(
            absoluteCenterX=self._absoluteCenterPos.x(),
            absoluteCenterY=self._absoluteCenterPos.y(),
            scale=self._viewScale.linear,
            outputPixelX=self.width(),
            outputPixelY=self.height())
        """
        self.repaint()

    def _currentDrawTiles(self) -> typing.Iterable[typing.Tuple[
            int, # x pixel position
            int, # y pixel position
            QtGui.QImage
            ]]:
        scaleX = (self._viewScale.linear * travellermap.ParsecScaleX)
        scaleY = (self._viewScale.linear * travellermap.ParsecScaleY)
        absoluteViewWidth = self.width() / scaleX
        absoluteViewHeight = self.height() / scaleY
        absoluteViewLeft = self._absoluteCenterPos.x() - (absoluteViewWidth / 2)
        absoluteViewRight = absoluteViewLeft + absoluteViewWidth
        absoluteViewTop = self._absoluteCenterPos.y() - (absoluteViewHeight / 2)
        absoluteViewBottom = absoluteViewTop + absoluteViewHeight

        absoluteTileWidth = MapHackView._TileSize / scaleX
        absoluteTileHeight = MapHackView._TileSize / scaleY
        leftTile = math.floor(absoluteViewLeft / absoluteTileWidth)
        rightTile = math.floor(absoluteViewRight / absoluteTileWidth)
        topTile = math.floor(absoluteViewTop / absoluteTileHeight)
        bottomTile = math.floor(absoluteViewBottom / absoluteTileHeight)

        offsetX = (absoluteViewLeft - (leftTile * absoluteTileWidth)) * scaleX
        offsetY = (absoluteViewTop - (topTile * absoluteTileHeight)) * scaleY

        self._tileTimer.stop()
        self._tileQueue.clear()

        tiles = []
        for x in range(leftTile, rightTile + 1):
            for y in range(topTile, bottomTile + 1):
                key = (x, y)
                image = self._tileCache.get(key)
                if not image:
                    if MapHackView._DelayedRendering:
                        self._tileQueue.append(key)
                        continue
                    image = self._renderTile(x, y)
                    self._tileCache[key] = image

                tiles.append((
                    ((x - leftTile)  * MapHackView._TileSize) - offsetX,
                    ((y - topTile) * MapHackView._TileSize) - offsetY,
                    image))

        if self._tileQueue:
            self._tileTimer.start()

        return tiles

    def _clearTileCache(self) -> None:
        self._tileCache.clear()
        self.update()

    def _renderTile(self, x: int, y: int) -> QtGui.QImage:
        scaleX = (self._viewScale.linear * travellermap.ParsecScaleX)
        scaleY = (self._viewScale.linear * travellermap.ParsecScaleY)
        absoluteWidth = MapHackView._TileSize / (scaleX * travellermap.ParsecScaleX)
        absoluteHeight = MapHackView._TileSize / (scaleY * travellermap.ParsecScaleY)

        absoluteTileCenterX = ((x * MapHackView._TileSize) / scaleX) + (absoluteWidth / 2)
        absoluteTileCenterY = ((y * MapHackView._TileSize) / scaleY) + (absoluteHeight / 2)

        image = QtGui.QImage(
            MapHackView._TileSize,
            MapHackView._TileSize,
            QtGui.QImage.Format.Format_ARGB32)
        painter = QtGui.QPainter()
        painter.begin(image)
        try:
            self._graphics.setPainter(painter)
            self._renderer.setView(
                absoluteCenterX=absoluteTileCenterX,
                absoluteCenterY=absoluteTileCenterY,
                scale=self._viewScale.linear,
                outputPixelX=MapHackView._TileSize,
                outputPixelY=MapHackView._TileSize)
            self._renderer.render()
        finally:
            painter.end()

        return image

    def _handleTileTimer(self) -> None:
        """
        for tileX, tileY in self._tileQueue:
            self._tileCache[(tileX, tileY)] = self._renderTile(tileX, tileY)
        self._tileQueue.clear()
        """
        tileX, tileY = self._tileQueue.pop()
        with common.DebugTimer('Tile Render'):
            self._tileCache[(tileX, tileY)] = self._renderTile(tileX, tileY)
        if self._tileQueue:
            self._tileTimer.start()
        self.update()

    def _debugHack(self):
        tempGraphics = gui.QtMapGraphics()
        tempRenderer = maprenderer.RenderContext(
                    graphics=tempGraphics,
                    absoluteCenterX=self._absoluteCenterPos.x(),
                    absoluteCenterY=self._absoluteCenterPos.y(),
                    scale=self._viewScale.linear,
                    outputPixelX=self.width(),
                    outputPixelY=self.height(),
                    style=self._style,
                    imageCache=self._imageCache,
                    vectorCache=self._vectorCache,
                    mapLabelCache=self._mapLabelCache,
                    worldLabelCache=self._worldLabelCache,
                    styleCache=self._styleCache,
                    options=self._options)

        image = QtGui.QImage(self.width(), self.height(), QtGui.QImage.Format.Format_ARGB32)
        painter = QtGui.QPainter()
        painter.begin(image)

        tempGraphics.setPainter(painter)

        try:
            # Render once before profiling to pre-load caches.
            #tempRenderer.render()

            print('Profiling')
            pr = cProfile.Profile()
            pr.enable()

            for _ in range(20):
                tempRenderer.setView(
                    absoluteCenterX=self._absoluteCenterPos.x(),
                    absoluteCenterY=self._absoluteCenterPos.y(),
                    scale=self._viewScale.linear,
                    outputPixelX=self.width(),
                    outputPixelY=self.height())
                tempRenderer.render()

            pr.disable()
            s = io.StringIO()
            sortby = SortKey.TIME
            #sortby = SortKey.CUMULATIVE
            ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
            ps.print_stats()
            print(s.getvalue())
        finally:
            painter.end()

        #image.save("output.png")

class MyWidget(gui.WindowWidget):
    def __init__(self):
        super().__init__(title='Map Hack', configSection='MapHack')
        self._widget = MapHackView()
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._widget)

        self.setLayout(layout)


def _installDirectory() -> str:
    return os.path.dirname(os.path.realpath(__file__))

def _applicationDirectory() -> str:
    if os.name == 'nt':
        return os.path.join(os.getenv('APPDATA'), app.AppName)
    else:
        return os.path.join(pathlib.Path.home(), '.' + app.AppName.lower())

if __name__ == "__main__":
    application = QtWidgets.QApplication([])

    installDir = _installDirectory()
    application.setWindowIcon(QtGui.QIcon(os.path.join(installDir, 'icons', 'autojimmy.ico')))

    appDir = _applicationDirectory()
    os.makedirs(appDir, exist_ok=True)

    logDirectory = os.path.join(appDir, 'logs')
    app.setupLogger(logDir=logDirectory, logFile='autojimmy.log')
    # Log version before setting log level as it should always be logged
    logging.info(f'{app.AppName} v{app.AppVersion}')

    try:
        locale.setlocale(locale.LC_ALL, '')
    except Exception as ex:
        logging.warning('Failed to set default locale', exc_info=ex)

    # Set configured log level immediately after configuration has been setup
    logLevel = app.Config.instance().logLevel()
    try:
        app.setLogLevel(logLevel)
    except Exception as ex:
        logging.warning('Failed to set log level', exc_info=ex)

    installMapsDir = os.path.join(installDir, 'data', 'map')
    overlayMapsDir = os.path.join(appDir, 'map')
    customMapsDir = os.path.join(appDir, 'custom_map')
    travellermap.DataStore.setSectorDirs(
        installDir=installMapsDir,
        overlayDir=overlayMapsDir,
        customDir=customMapsDir)

    traveller.WorldManager.setMilieu(milieu=travellermap.Milieu.M1105)
    traveller.WorldManager.instance().loadSectors()

    gui.configureAppStyle(application)

    window = MyWidget()
    window.show()
    application.exec_()
