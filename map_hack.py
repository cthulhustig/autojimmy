from PyQt5 import QtWidgets, QtCore, QtGui
import app
import common
import gui
import io
import locale
import logging
import maprenderer
import os
import traveller
import travellermap
import typing
import cProfile, pstats, io
from pstats import SortKey

class MapHackView(QtWidgets.QWidget):
    _MinScale = 0.0078125 # Math.Pow(2, -7);
    _MaxScale = 512 # Math.Pow(2, 9);
    _DefaultScale = 64

    _WheelScaleMultiplier = 1.5

    _ZoomInScale = 1.25
    _ZoomOutScale = 0.8

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        scene = QtWidgets.QGraphicsScene()
        scene.setSceneRect(0, 0, self.width(), self.height())

        self._viewCenterMapPos = maprenderer.PointF(0, 0) # TODO: I think this is actually in world/absolute coordinates
        self._tileSize = maprenderer.Size(self.width(), self.height())
        self._scale = MapHackView._DefaultScale
        self._options = \
            maprenderer.MapOptions.SectorGrid | maprenderer.MapOptions.SubsectorGrid | \
            maprenderer.MapOptions.SectorsSelected | maprenderer.MapOptions.SectorsAll | \
            maprenderer.MapOptions.BordersMajor | maprenderer.MapOptions.BordersMinor | \
            maprenderer.MapOptions.NamesMajor | maprenderer.MapOptions.NamesMinor | \
            maprenderer.MapOptions.WorldsCapitals | maprenderer.MapOptions.WorldsHomeworlds | \
            maprenderer.MapOptions.RoutesSelectedDeprecated | \
            maprenderer.MapOptions.PrintStyleDeprecated | maprenderer.MapOptions.CandyStyleDeprecated | \
            maprenderer.MapOptions.ForceHexes | maprenderer.MapOptions.WorldColors | \
            maprenderer.MapOptions.FilledBorders
        self._style = travellermap.Style.Poster
        #self._style = travellermap.Style.Candy
        self._graphics = gui.QtMapGraphics()
        self._imageCache = maprenderer.ImageCache(basePath='./data/map/')
        self._vectorCache = maprenderer.VectorObjectCache(basePath='./data/map/')
        self._mapLabelCache = maprenderer.MapLabelCache(basePath='./data/map/')
        self._worldLabelCache = maprenderer.WorldLabelCache(basePath='./data/map/')
        self._styleCache = maprenderer.DefaultStyleCache(basePath='./data/map/')
        maprenderer.WorldHelper.loadData(basePath='./data/map/') # TODO: Not sure where this should live
        self._renderer = self._createRender()

        self._isDragging = False
        self._dragPixelPos: typing.Optional[QtCore.QPoint] = None

        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)

    def clear(self) -> None:
        self._graphics = None

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        super().mousePressEvent(event)

        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._dragPixelPos = event.pos()

            # TODO: This is borked, need to figure out how to convert a float world space coordinate
            # to an int absolute coordinate
            absCursor = self._renderer.pixelSpaceToWorldSpace(pixel=maprenderer.Point(event.x(), event.y()))
            relCursor = travellermap.absoluteSpaceToRelativeSpace((absCursor.x, absCursor.y))
            print(f'ABS: {absCursor.x} {absCursor.y} HEX:{relCursor[2]} {relCursor[3]}')

    # TODO: There is an issue with the drag move where the point you start the
    # drag on isn't staying under the cursor
    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        super().mouseMoveEvent(event)
        if self._renderer and self._dragPixelPos:
            point = event.pos()
            screenDelta = point - self._dragPixelPos
            mapDelta = maprenderer.PointF(
                screenDelta.x() / self._scale,
                screenDelta.y() / self._scale)
            self._dragPixelPos = point

            self._viewCenterMapPos.x -= mapDelta.x
            self._viewCenterMapPos.y -= mapDelta.y
            self._renderer.setTileRect(
                rect=self._calculateTileRect())
            self.repaint()

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        super().mouseReleaseEvent(event)

        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._dragPixelPos = None

    def focusOutEvent(self, event: QtGui.QFocusEvent) -> None:
        super().focusOutEvent(event)
        self._dragPixelPos = None

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        self._tileSize = maprenderer.Size(self.width(), self.height())
        self._renderer = self._createRender()

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        super().keyPressEvent(event)

        if self._renderer:
            dx = dy = None
            if event.key() == QtCore.Qt.Key.Key_Left:
                mapWidth = self._tileSize.width / (self._scale * travellermap.ParsecScaleX)
                dx = -mapWidth / 10
            elif event.key() == QtCore.Qt.Key.Key_Right:
                mapWidth = self._tileSize.width / (self._scale * travellermap.ParsecScaleX)
                dx = mapWidth / 10
            elif event.key() == QtCore.Qt.Key.Key_Up:
                mapHeight = self._tileSize.height / (self._scale * travellermap.ParsecScaleY)
                dy = -mapHeight / 10
            elif event.key() == QtCore.Qt.Key.Key_Down:
                mapHeight = self._tileSize.height / (self._scale * travellermap.ParsecScaleY)
                dy = mapHeight / 10

            if dx != None or dy != None:
                if dx != None:
                    self._viewCenterMapPos.x += dx
                if dy != None:
                    self._viewCenterMapPos.y += dy
                self._renderer.setTileRect(
                    rect=self._calculateTileRect())
                self.repaint()

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        super().wheelEvent(event)

        if self._renderer:
            cursorScreenPos = event.pos()
            oldCursorMapPos = self._renderer.pixelSpaceToWorldSpace(maprenderer.PointF(
                cursorScreenPos.x(),
                cursorScreenPos.y()),
                clamp=False) # Float value for extra accuracy

            if event.angleDelta().y() > 0:
                self._scale *= MapHackView._WheelScaleMultiplier
            else:
                self._scale /= MapHackView._WheelScaleMultiplier
            self._renderer = self._createRender()

            newCursorMapPos = self._renderer.pixelSpaceToWorldSpace(maprenderer.PointF(
                cursorScreenPos.x(),
                cursorScreenPos.y()),
                clamp=False)

            self._viewCenterMapPos.x += oldCursorMapPos.x - newCursorMapPos.x
            self._viewCenterMapPos.y += oldCursorMapPos.y - newCursorMapPos.y

            self._renderer.setTileRect(
                rect=self._calculateTileRect())

            self.repaint()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        if not self._graphics or not self._renderer:
            return super().paintEvent(event)

        # TODO: Remove debug timer
        with common.DebugTimer('Draw Time'):
            painter = QtGui.QPainter(self)
            try:
                self._graphics.setPainter(painter)

                pr = None
                if False:
                    pr = cProfile.Profile()
                    pr.enable()

                self._renderer.render()

                if pr:
                    pr.disable()
                    s = io.StringIO()
                    sortby = SortKey.TIME
                    #sortby = SortKey.CUMULATIVE
                    ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
                    ps.print_stats()
                    print(s.getvalue())
            finally:
                painter.end()

    def _createRender(self) -> maprenderer.RenderContext:
        return maprenderer.RenderContext(
            graphics=self._graphics,
            tileRect=self._calculateTileRect(),
            tileSize=self._tileSize,
            scale=self._scale,
            styles=maprenderer.StyleSheet(
                scale=self._scale,
                options=self._options,
                style=self._style),
            imageCache=self._imageCache,
            vectorCache=self._vectorCache,
            mapLabelCache=self._mapLabelCache,
            worldLabelCache=self._worldLabelCache,
            styleCache=self._styleCache,
            options=self._options)

    def _calculateTileRect(self) -> maprenderer.RectangleF:
        mapWidth = self._tileSize.width / (self._scale * travellermap.ParsecScaleX)
        mapHeight = self._tileSize.height / (self._scale * travellermap.ParsecScaleY)
        return maprenderer.RectangleF(
            x=self._viewCenterMapPos.x - (mapWidth / 2),
            y=self._viewCenterMapPos.y - (mapHeight / 2),
            width=mapWidth,
            height=mapHeight)

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
