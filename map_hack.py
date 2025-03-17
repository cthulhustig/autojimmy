from PyQt5 import QtWidgets, QtCore, QtGui
import app
import common
import gc
import gui
import io
import locale
import logging
import maprenderer
import math
import os
import pathlib
import traveller
import travellermap
import typing
import cProfile, pstats, io
from pstats import SortKey

# TODO: I think a lot of the places I've referred to as absolute space
# is actually map space, or at least my equivalent of it (i.e. without the
# inverted y axis like in Traveller Map). I think anything the problem
# might be around things that are using ParsecScaleX/ParsecScaleY
# TODO: Not sure if me not inverting the y axis in my map space might
# be an issue when it comes to rendering mains (or other things that
# would be done with client side map space in Traveller Map)
# TODO: Jump routes
# TODO: Other overlays
# TODO: Ability to switch between this and the existing TravellerMapWidget

class MapHackView(QtWidgets.QWidget):
    _MinScale = -7
    _MaxScale = 10
    _DefaultCenterX = 0
    _DefaultCenterY = 0
    _DefaultScale = 64
    _DefaultScale = travellermap.logScaleToLinearScale(7)
    #_DefaultCenterX, _DefaultCenterY  = (13.971588572221023, -28.221357863973523)

    _WheelLogScaleDelta = 0.15

    _TileRendering = True
    _DelayedRendering = True
    _LookaheadTiles = True
    _TileSize = 512 # Pixels
    _TileCacheSize = 250 # Number of tiles
    _TileTimerMsecs = 1
    #_TileTimerMsecs = 1000

    _CheckerboardColourA ='#000000'
    _CheckerboardColourB ='#404040'
    _CheckerboardRectSize = 16

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

        # Off screen buffer used when not using tile rendering to prevent
        # Windows font scaling messing up the size of rendered text on a
        # 4K+ screen
        self._isWindows = common.isWindows()
        self._offscreenRenderImage: typing.Optional[QtGui.QImage] = None

        self._tileCache = common.LRUCache[
            typing.Tuple[
                int, # Tile X
                int, # Tile Y
                int], # Tile Scale (linear)
            QtGui.QImage](capacity=MapHackView._TileCacheSize)

        self._tileTimer = QtCore.QTimer()
        self._tileTimer.setInterval(MapHackView._TileTimerMsecs)
        self._tileTimer.setSingleShot(True)
        self._tileTimer.timeout.connect(self._handleTileTimer)
        self._tileQueue: typing.List[typing.Tuple[
            int, # Tile X
            int, # Tile Y
            int # Tile Scale (linear)
            ]] = []

        self._placeholderTile = MapHackView._createPlaceholderTile()

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
                return

            if event.key() == QtCore.Qt.Key.Key_Z:
                scale = self._viewScale.log
                scale += MapHackView._WheelLogScaleDelta if not gui.isShiftKeyDown() else -MapHackView._WheelLogScaleDelta
                scale = common.clamp(scale, MapHackView._MinScale, MapHackView._MaxScale)
                self._viewScale.log = scale
                self._updateRendererView()
                return

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
            elif event.key() == QtCore.Qt.Key.Key_F5:
                print('Forcing garbage collection')
                count = gc.collect()
                print(f'{count}')
                count = gc.collect()
                print(f'{count}')
            elif event.key() == QtCore.Qt.Key.Key_F7:
                self.update()
            elif event.key() == QtCore.Qt.Key.Key_F10:
                gc.collect()
            elif event.key() == QtCore.Qt.Key.Key_F11:
                self._tileCache.clear()
                self._tileQueue.clear()
                self._tileTimer.stop()
                self._renderer = self._createRenderer()
                gc.collect()
                self.update()
            elif event.key() == QtCore.Qt.Key.Key_F12:
                MapHackView._TileRendering = not MapHackView._TileRendering
                print(f'TileRendering={MapHackView._TileRendering}')
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
            if logViewScale == self._viewScale.log:
                return # Reached min/max zoom
            self._viewScale.log = logViewScale

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

        #print(f'View: {self.width()} {self.height()}')
        #print(f'Pos: {self._absoluteCenterPos.x()} {self._absoluteCenterPos.y()}')
        #print(f'Scale: Linear={self._viewScale.linear} Log={self._viewScale.log}')

        # TODO: Remove debug timer
        with common.DebugTimer('Draw Time'):
            if not MapHackView._TileRendering and self._isWindows:
                needsNewImage = self._offscreenRenderImage is None or \
                    self._offscreenRenderImage.width() != self.width() or \
                    self._offscreenRenderImage.height() != self.height()
                if needsNewImage:
                    self._offscreenRenderImage = QtGui.QImage(
                        self.width(),
                        self.height(),
                        QtGui.QImage.Format.Format_ARGB32)
            else:
                self._offscreenRenderImage = None

            painter = QtGui.QPainter()
            painter.begin(self._offscreenRenderImage if self._offscreenRenderImage is not None else self)
            try:
                painter.setBrush(QtCore.Qt.GlobalColor.black)
                painter.drawRect(0, 0, self.width(), self.height())

                if MapHackView._TileRendering:
                    tiles = self._currentDrawTiles()

                    # This is disabled as I think it actually makes scaled tiles
                    # look worse (a bit to blurry)
                    """
                    painter.setRenderHint(
                        QtGui.QPainter.RenderHint.SmoothPixmapTransform,
                        True)
                    """

                    with common.DebugTimer('Blit Time'):
                        for image, renderRect, clipRect in tiles:
                            painter.save()
                            try:
                                if clipRect:
                                    clipPath = painter.clipPath()
                                    clipPath.setFillRule(QtCore.Qt.FillRule.WindingFill)
                                    clipPath.addRect(clipRect)
                                    painter.setClipPath(clipPath, operation=QtCore.Qt.ClipOperation.IntersectClip)
                                else:
                                    # Manually scale the image if needed as drawImage does a piss poor job.
                                    # This is only done when there is no clip rect. A clip rect means it's
                                    # a placeholder tile so won't be drawn for very long so quality doesn't
                                    # mater as much so best to avoid the expensive scaling
                                    if image.width() != renderRect.width() or image.height() != renderRect.height():
                                        image = image.smoothScaled(
                                            round(renderRect.width()),
                                            round(renderRect.height()))

                                #print(f'{image} {renderRect} {clipRect}')
                                painter.drawImage(renderRect, image)
                            finally:
                                painter.restore()

                    if MapHackView._LookaheadTiles and not self._tileQueue:
                        # If there are no tiles needing loaded, pre-load tiles just
                        # outside the current view area
                        self._loadLookaheadTiles()

                    if self._tileQueue:
                        # Start the timer to trigger loading of missing tiles
                        self._tileTimer.start()
                else:
                    self._graphics.setPainter(painter=painter)
                    try:
                        self._renderer.setView(
                            absoluteCenterX=self._absoluteCenterPos.x(),
                            absoluteCenterY=self._absoluteCenterPos.y(),
                            scale=self._viewScale.linear,
                            outputPixelX=self.width(),
                            outputPixelY=self.height())
                        self._renderer.render()
                    finally:
                        self._graphics.setPainter(painter=None)
            finally:
                painter.end()

            if self._offscreenRenderImage is not None:
                painter = QtGui.QPainter()
                painter.begin(self)
                try:
                    renderRect = QtCore.QRect(0, 0, self.width(), self.height())
                    painter.drawImage(renderRect, self._offscreenRenderImage)
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
        self.repaint()

    def _currentDrawTiles(self) -> typing.Iterable[typing.Tuple[
            QtGui.QImage,
            QtCore.QRectF, # Render rect
            typing.Optional[QtCore.QRectF], # Clip rect
            ]]:
        # This method of rounding the scale is intended to match how it would
        # be rounded by the Traveller Map Javascript code which uses Math.round
        # https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Math/round
        tileScale = int(math.floor(self._viewScale.log + 0.5))

        tileMultiplier = math.pow(2, self._viewScale.log - tileScale)
        tileSize = MapHackView._TileSize * tileMultiplier

        scaleX = (self._viewScale.linear * travellermap.ParsecScaleX)
        scaleY = (self._viewScale.linear * travellermap.ParsecScaleY)
        absoluteViewWidth = self.width() / scaleX
        absoluteViewHeight = self.height() / scaleY
        absoluteViewLeft = self._absoluteCenterPos.x() - (absoluteViewWidth / 2)
        absoluteViewRight = absoluteViewLeft + absoluteViewWidth
        absoluteViewTop = self._absoluteCenterPos.y() - (absoluteViewHeight / 2)
        absoluteViewBottom = absoluteViewTop + absoluteViewHeight

        absoluteTileWidth = tileSize / scaleX
        absoluteTileHeight = tileSize / scaleY
        leftTile = math.floor(absoluteViewLeft / absoluteTileWidth)
        rightTile = math.floor(absoluteViewRight / absoluteTileWidth)
        topTile = math.floor(absoluteViewTop / absoluteTileHeight)
        bottomTile = math.floor(absoluteViewBottom / absoluteTileHeight)

        offsetX = (absoluteViewLeft - (leftTile * absoluteTileWidth)) * scaleX
        offsetY = (absoluteViewTop - (topTile * absoluteTileHeight)) * scaleY

        cursorPos = self.mapFromGlobal(QtGui.QCursor.pos())
        isCursorOverWindow = cursorPos.x() >= 0 and cursorPos.x() < self.width() and \
            cursorPos.y() >= 0 and cursorPos.y() < self.height()
        if isCursorOverWindow:
            # If the cursor is over the window, fan out from the cursor
            # position when generating tiles
            absoluteOriginX, absoluteOriginY = self._pixelSpaceToWorldSpace(
                pixelX=cursorPos.x(),
                pixelY=cursorPos.y())
        else:
            # If the cursor is not over the window, fan out from the
            # center of the view when generating tiles
            absoluteOriginX = self._absoluteCenterPos.x()
            absoluteOriginY = self._absoluteCenterPos.y()
        centerTileX = math.floor(absoluteOriginX / absoluteTileWidth)
        centerTileY = math.floor(absoluteOriginY / absoluteTileHeight)

        self._tileTimer.stop()
        self._tileQueue.clear()

        tiles = []
        image = self._lookupTile(tileX=centerTileX, tileY=centerTileY, tileScale=tileScale)
        renderRect = QtCore.QRectF(
            ((centerTileX - leftTile) * tileSize) - offsetX,
            ((centerTileY - topTile) * tileSize) - offsetY,
            tileSize,
            tileSize)
        if image:
            tiles.append((image, renderRect, None))
        else:
            placeholders = self._gatherPlaceholderTiles(
                currentScale=tileScale,
                tileRect=renderRect)
            if placeholders:
                tiles.extend(placeholders)

        minTileX = centerTileX - 1
        maxTileX = centerTileX + 1
        minTileY = centerTileY - 1
        maxTileY = centerTileY + 1
        while minTileX >= leftTile or maxTileX <= rightTile or minTileY >= topTile or maxTileY <= bottomTile:
            if minTileY >= topTile:
                for x in range(max(minTileX, leftTile), min(maxTileX, rightTile + 1)):
                    image = self._lookupTile(tileX=x, tileY=minTileY, tileScale=tileScale)
                    renderRect = QtCore.QRectF(
                        ((x - leftTile) * tileSize) - offsetX,
                        ((minTileY - topTile) * tileSize) - offsetY,
                        tileSize,
                        tileSize)
                    if image:
                        tiles.append((image, renderRect, None))
                    else:
                        placeholders = self._gatherPlaceholderTiles(
                            currentScale=tileScale,
                            tileRect=renderRect)
                        if placeholders:
                            tiles.extend(placeholders)

            if maxTileX <= rightTile:
                for y in range(max(minTileY, topTile), min(maxTileY, bottomTile + 1)):
                    image = self._lookupTile(tileX=maxTileX, tileY=y, tileScale=tileScale)
                    renderRect = QtCore.QRectF(
                        ((maxTileX - leftTile) * tileSize) - offsetX,
                        ((y - topTile) * tileSize) - offsetY,
                        tileSize,
                        tileSize)
                    if image:
                        tiles.append((image, renderRect, None))
                    else:
                        placeholders = self._gatherPlaceholderTiles(
                            currentScale=tileScale,
                            tileRect=renderRect)
                        if placeholders:
                            tiles.extend(placeholders)

            if maxTileY <= bottomTile:
                for x in range(min(maxTileX, rightTile), max(minTileX, leftTile - 1), -1):
                    image = self._lookupTile(tileX=x, tileY=maxTileY, tileScale=tileScale)
                    renderRect = QtCore.QRectF(
                        ((x - leftTile) * tileSize) - offsetX,
                        ((maxTileY - topTile) * tileSize) - offsetY,
                        tileSize,
                        tileSize)
                    if image:
                        tiles.append((image, renderRect, None))
                    else:
                        placeholders = self._gatherPlaceholderTiles(
                            currentScale=tileScale,
                            tileRect=renderRect)
                        if placeholders:
                            tiles.extend(placeholders)

            if minTileX >= leftTile:
                for y in range(min(maxTileY, bottomTile), max(minTileY, topTile - 1), -1):
                    image = self._lookupTile(tileX=minTileX, tileY=y, tileScale=tileScale)
                    renderRect = QtCore.QRectF(
                        ((minTileX - leftTile) * tileSize) - offsetX,
                        ((y - topTile) * tileSize) - offsetY,
                        tileSize,
                        tileSize)
                    if image:
                        tiles.append((image, renderRect, None))
                    else:
                        placeholders = self._gatherPlaceholderTiles(
                            currentScale=tileScale,
                            tileRect=renderRect)
                        if placeholders:
                            tiles.extend(placeholders)

            minTileX -= 1
            maxTileX += 1
            minTileY -= 1
            maxTileY += 1

        return tiles

    def _loadLookaheadTiles(self) -> None:
        # This method of rounding the scale is intended to match how it would
        # be rounded by the Traveller Map Javascript code which uses Math.round
        # https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Math/round
        tileScale = int(math.floor(self._viewScale.log + 0.5))

        tileMultiplier = math.pow(2, self._viewScale.log - tileScale)
        tileSize = MapHackView._TileSize * tileMultiplier

        scaleX = (self._viewScale.linear * travellermap.ParsecScaleX)
        scaleY = (self._viewScale.linear * travellermap.ParsecScaleY)
        absoluteViewWidth = self.width() / scaleX
        absoluteViewHeight = self.height() / scaleY
        absoluteViewLeft = self._absoluteCenterPos.x() - (absoluteViewWidth / 2)
        absoluteViewRight = absoluteViewLeft + absoluteViewWidth
        absoluteViewTop = self._absoluteCenterPos.y() - (absoluteViewHeight / 2)
        absoluteViewBottom = absoluteViewTop + absoluteViewHeight

        absoluteTileWidth = tileSize / scaleX
        absoluteTileHeight = tileSize / scaleY
        leftTile = math.floor(absoluteViewLeft / absoluteTileWidth) - 1
        rightTile = math.floor(absoluteViewRight / absoluteTileWidth) + 1
        topTile = math.floor(absoluteViewTop / absoluteTileHeight) - 1
        bottomTile = math.floor(absoluteViewBottom / absoluteTileHeight) + 1

        for x in range(leftTile, rightTile):
            self._lookupTile(tileX=x, tileY=topTile, tileScale=tileScale)
        for y in range(topTile, bottomTile):
            self._lookupTile(tileX=rightTile, tileY=y, tileScale=tileScale)
        for x in range(rightTile, leftTile, -1):
            self._lookupTile(tileX=x, tileY=bottomTile, tileScale=tileScale)
        for y in range(bottomTile, topTile, -1):
            self._lookupTile(tileX=leftTile, tileY=y, tileScale=tileScale)

    def _lookupTile(
            self,
            tileX: int,
            tileY: int,
            tileScale: int # Log scale rounded down
            ) -> typing.Optional[QtGui.QImage]:
        key = (tileX, tileY, tileScale)
        image = self._tileCache.get(key)
        if not image:
            if MapHackView._DelayedRendering:
                if key not in self._tileQueue:
                    self._tileQueue.append(key)
            else:
                image = None
                if self._tileCache.isFull():
                    # Reuse oldest cached tile
                    _, image = self._tileCache.pop()
                image = self._renderTile(tileX, tileY, tileScale, image)
                self._tileCache[key] = image
        return image

    def _gatherPlaceholderTiles(
            self,
            currentScale: int,
            tileRect: QtCore.QRectF
            ) -> typing.List[typing.Tuple[
                QtGui.QImage,
                QtCore.QRectF, # Render rect
                typing.Optional[QtCore.QRectF]]]: # Clip rect
        viewRect = QtCore.QRectF(0, 0, self.width(), self.height())
        clipRect = tileRect.intersected(viewRect)

        placeholders = self._findPlaceholderTiles(
            currentScale=currentScale,
            tileRect=tileRect,
            clipRect=clipRect,
            lookLower=True)
        if placeholders:
            return placeholders

        placeholders = self._findPlaceholderTiles(
            currentScale=currentScale,
            tileRect=tileRect,
            clipRect=clipRect,
            lookLower=False)
        if placeholders:
            return placeholders

        # No alternate tiles found so use standard placeholder
        return [(self._placeholderTile, tileRect, clipRect)]

    def _findPlaceholderTiles(
            self,
            currentScale: int,
            tileRect: QtCore.QRectF, # Pixel space
            clipRect: QtCore.QRectF, # Pixel space
            lookLower: bool
            ) -> typing.Iterable[typing.Tuple[
                QtGui.QImage,
                QtCore.QRectF, # Render rect
                typing.Optional[QtCore.QRectF]]]: # Clip rect
        placeholderScale = currentScale + (-1 if lookLower else 1)
        if placeholderScale < MapHackView._MinScale or placeholderScale > MapHackView._MaxScale:
            return[]

        tileMultiplier = math.pow(2, self._viewScale.log - placeholderScale)
        tileSize = MapHackView._TileSize * tileMultiplier

        scaleX = (self._viewScale.linear * travellermap.ParsecScaleX)
        scaleY = (self._viewScale.linear * travellermap.ParsecScaleY)
        absoluteViewWidth = self.width() / scaleX
        absoluteViewHeight = self.height() / scaleY
        absoluteViewLeft = self._absoluteCenterPos.x() - (absoluteViewWidth / 2)
        absoluteViewTop = self._absoluteCenterPos.y() - (absoluteViewHeight / 2)

        absoluteTileWidth = tileSize / scaleX
        absoluteTileHeight = tileSize / scaleY
        leftTile = math.floor((((clipRect.left() / scaleX) + absoluteViewLeft) / absoluteTileWidth))
        rightTile = math.floor((((clipRect.right() / scaleX) + absoluteViewLeft) / absoluteTileWidth))
        topTile = math.floor((((clipRect.top() / scaleY) + absoluteViewTop) / absoluteTileHeight))
        bottomTile = math.floor((((clipRect.bottom() / scaleY) + absoluteViewTop) / absoluteTileHeight))

        offsetX = (absoluteViewLeft - (leftTile * absoluteTileWidth)) * scaleX
        offsetY = (absoluteViewTop - (topTile * absoluteTileHeight)) * scaleY

        placeholders = []
        missing = []
        for x in range(leftTile, rightTile + 1):
            for y in range(topTile, bottomTile + 1):
                key = (x, y, placeholderScale)

                placeholderRenderRect = QtCore.QRectF(
                    ((x - leftTile) * tileSize) - offsetX,
                    ((y - topTile) * tileSize) - offsetY,
                    tileSize,
                    tileSize)
                placeholderClipRect = placeholderRenderRect.intersected(clipRect)
                if not placeholderClipRect.isValid():
                    continue

                # NOTE: Don't use _lookupTile as we don't want to create
                # this tile if it doesn't exist
                image = self._tileCache.get(key)
                if image:
                    placeholders.append((image, placeholderRenderRect, placeholderClipRect))
                else:
                    if lookLower:
                        lowerPlaceholders = self._findPlaceholderTiles(
                            currentScale=placeholderScale,
                            tileRect=tileRect,
                            clipRect=placeholderClipRect,
                            lookLower=lookLower)
                        if lowerPlaceholders:
                            placeholders.extend(lowerPlaceholders)
                            continue

                    missing.append(placeholderClipRect)

        if placeholders and missing:
            for placeholderClipRect in missing:
                placeholders.append((self._placeholderTile, tileRect, placeholderClipRect))

        return placeholders

    def _clearTileCache(self) -> None:
        self._tileCache.clear()
        self.update() # Force redraw

    def _renderTile(
            self,
            tileX: int,
            tileY: int,
            tileScale: int, # Log scale rounded down
            image: typing.Optional[QtGui.QImage]
            ) -> QtGui.QImage:
        tileScale = travellermap.logScaleToLinearScale(tileScale)
        scaleX = (tileScale * travellermap.ParsecScaleX)
        scaleY = (tileScale * travellermap.ParsecScaleY)
        absoluteTileWidth = MapHackView._TileSize / scaleX
        absoluteTileHeight = MapHackView._TileSize / scaleY

        absoluteTileCenterX = ((tileX * MapHackView._TileSize) / scaleX) + (absoluteTileWidth / 2)
        absoluteTileCenterY = ((tileY * MapHackView._TileSize) / scaleY) + (absoluteTileHeight / 2)

        if not image:
            image = QtGui.QImage(
                MapHackView._TileSize,
                MapHackView._TileSize,
                QtGui.QImage.Format.Format_ARGB32)
        painter = QtGui.QPainter()
        painter.begin(image)
        try:
            self._graphics.setPainter(painter=painter)
            self._renderer.setView(
                absoluteCenterX=absoluteTileCenterX,
                absoluteCenterY=absoluteTileCenterY,
                scale=tileScale,
                outputPixelX=MapHackView._TileSize,
                outputPixelY=MapHackView._TileSize)
            self._renderer.render()

            """
            painter.setPen(QtGui.QColor('#FF0000'))
            painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
            painter.drawRect(0, 0, MapHackView._TileSize, MapHackView._TileSize)
            """
        finally:
            self._graphics.setPainter(painter=None)
            painter.end()

        return image

    def _handleTileTimer(self) -> None:
        tileX, tileY, tileScale = self._tileQueue.pop(0)
        #with common.DebugTimer('Tile Render'):
        if True:
            image = None
            if self._tileCache.isFull():
                # Reuse oldest cached tile
                _, image = self._tileCache.pop()
            self._tileCache[(tileX, tileY, tileScale)] = self._renderTile(
                tileX=tileX,
                tileY=tileY,
                tileScale=tileScale,
                image=image)
        if self._tileQueue:
            self._tileTimer.start()
        self.update()

    @staticmethod
    def _createPlaceholderTile() -> QtGui.QImage:
        image = QtGui.QImage(
            MapHackView._TileSize,
            MapHackView._TileSize,
            QtGui.QImage.Format.Format_ARGB32)
        rectsPerSize = math.ceil(MapHackView._TileSize / MapHackView._CheckerboardRectSize)

        painter = QtGui.QPainter()
        painter.begin(image)
        try:
            painter.setBrush(QtGui.QColor(MapHackView._CheckerboardColourA))
            painter.drawRect(0, 0, MapHackView._TileSize, MapHackView._TileSize)

            painter.setBrush(QtGui.QColor(MapHackView._CheckerboardColourB))
            for x in range(rectsPerSize):
                for y in range(1 if x % 2 else 0, rectsPerSize, 2):
                    painter.drawRect(
                        x * MapHackView._CheckerboardRectSize,
                        y * MapHackView._CheckerboardRectSize,
                        MapHackView._CheckerboardRectSize,
                        MapHackView._CheckerboardRectSize)
        finally:
            painter.end()

        return image

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

        try:
            # Render once before profiling to pre-load caches.
            tempGraphics.setPainter(painter=painter)
            tempRenderer.render()

            print('Profiling')
            pr = cProfile.Profile()
            pr.enable()

            for _ in range(1):
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
            tempGraphics.setPainter(painter=None)
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
    window.resize(800, 600)
    #window.setFixedSize(256, 256)
    #window.setFixedSize(937, 723)
    window.show()
    application.exec_()
