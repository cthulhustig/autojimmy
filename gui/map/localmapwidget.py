import common
import enum
import gc
import gui
import logic
import maprenderer
import math
import travellermap
import typing
import uuid
from PyQt5 import QtWidgets, QtCore, QtGui

# TODO: I think a lot of the places I've referred to as absolute space
# is actually map space, or at least my equivalent of it (i.e. without the
# inverted y axis like in Traveller Map). I think anything the problem
# might be around things that are using ParsecScaleX/ParsecScaleY.
# Update: I think the coordinate system naming are a complete mess
# - I think the render is working in its own coordinate system. I think
#   traveller map might refer to it as world coordinates but this term
#   seems a littler overloaded as the traveller map coordinate system
#   documentation seems to use the term world space for the integer pair
#   coordinate system that defines a hex relative to reference (i.e.
#   what I've historically referred to as absolute coordinates)
# - The coordinate system used by the renderer is in parsecs with a hex
#   being 1 parsec high and slightly over 1 parsec wide when rendered.
# - I have what I call relative space but in traveller map it refers to
#   it sector hex. The traveller map terminology is a little ambiguous
#   as there is also the string based sector hex format but that is
#   effectively equivalent just with the sector coordinate replaced with
#   the name
# - I'm overloading the term absolute space. I'm using it as the term
#   for what the renderer is working in and using it for the integer
#   pair that represents a hex elsewhere in the code. I think this is
#   basically the same overloading as traveller map where it uses
#   world coordinates
# TODO: Not sure if me not inverting the y axis in my map space might
# be an issue when it comes to rendering mains (or other things that
# would be done with client side map space in Traveller Map)
# TODO: Jump routes
# TODO: mains
# - I could render these onto the tiles but it might be better to have them
#   rendered on top of the final frame
# TODO: Other overlays
# TODO: Ability to switch between this and the existing TravellerMapWidget
# TODO: Animated move to new location
# TODO: Spinwards/corewards etc labels
# TODO: Current scale line in bottom right
# TODO: Fix colour vs color
# TODO: Update tooltips to use renderer
# TODO: Saving/restoring last view position and zoom

class LocalMapWidget(QtWidgets.QWidget):
    leftClicked = QtCore.pyqtSignal([travellermap.HexPosition])
    rightClicked = QtCore.pyqtSignal([travellermap.HexPosition])

    _MinScale = -5
    _MaxScale = 10
    _DefaultCenterX = 0
    _DefaultCenterY = 0
    _DefaultScale = 64
    _DefaultScale = travellermap.logScaleToLinearScale(7)
    #_DefaultCenterX, _DefaultCenterY = (13.971588572221023, -28.221357863973523)
    #_DefaultCenterX, _DefaultCenterY = (-95.914 / travellermap.ParsecScaleX, 70.5 / -travellermap.ParsecScaleY)
    #_DefaultCenterX, _DefaultCenterY = (-110.50311757412467, -70.5033270610736)
    #_DefaultCenterX, _DefaultCenterY = travellermap.mapSpaceToAbsoluteSpace((-95.914, 70.5))

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

    # TODO: This should be shared with web map widget
    class PrimitiveType(enum.Enum):
        Hex = 0
        Circle = 1

    # Number of pixels of movement we allow between the left mouse button down and up events for
    # the action to be counted as a click. I found that forcing no movement caused clicks to be
    # missed
    # TODO: This should be shared with web map widget
    _LeftClickMoveThreshold = 3

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        scene = QtWidgets.QGraphicsScene()
        scene.setSceneRect(0, 0, self.width(), self.height())

        self._absoluteCenterPos = QtCore.QPointF(
            LocalMapWidget._DefaultCenterX,
            LocalMapWidget._DefaultCenterY)
        self._viewScale = travellermap.Scale(value=LocalMapWidget._DefaultScale, linear=True)
        self._options = \
            maprenderer.MapOptions.SectorGrid | maprenderer.MapOptions.SubsectorGrid | \
            maprenderer.MapOptions.SectorsSelected | \
            maprenderer.MapOptions.BordersMajor | maprenderer.MapOptions.BordersMinor | \
            maprenderer.MapOptions.NamesMajor | maprenderer.MapOptions.NamesMinor | \
            maprenderer.MapOptions.WorldsCapitals | maprenderer.MapOptions.WorldsHomeworlds | \
            maprenderer.MapOptions.WorldColors

        self._style = travellermap.Style.Poster
        #self._style = travellermap.Style.Candy
        self._graphics = gui.QtMapGraphics()
        self._imageCache = maprenderer.ImageCache(
            graphics=self._graphics)
        self._vectorCache = maprenderer.VectorObjectCache(
            graphics=self._graphics)
        self._labelCache = maprenderer.LabelCache()
        self._styleCache = maprenderer.StyleCache()
        self._renderer = self._createRenderer()

        self._worldDragAnchor: typing.Optional[QtCore.QPointF] = None
        self._pixelDragStart: typing.Optional[QtCore.QPoint] = None

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
            QtGui.QImage](capacity=LocalMapWidget._TileCacheSize)

        self._tileTimer = QtCore.QTimer()
        self._tileTimer.setInterval(LocalMapWidget._TileTimerMsecs)
        self._tileTimer.setSingleShot(True)
        self._tileTimer.timeout.connect(self._handleTileTimer)
        self._tileQueue: typing.List[typing.Tuple[
            int, # Tile X
            int, # Tile Y
            int # Tile Scale (linear)
            ]] = []

        self._placeholderTile = LocalMapWidget._createPlaceholderTile()

        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)

    def reload(self) -> None:
        self._clearTileCache()
        self.update() # Force a redraw

    def centerOnHex(
            self,
            hex: travellermap.HexPosition,
            linearScale: typing.Optional[float] = 64 # None keeps current scale
            ) -> None:
        center = hex.absoluteCenter()
        self._absoluteCenterPos.setX(center[0])
        self._absoluteCenterPos.setY(center[1])
        self.update() # Force redraw

    def hasJumpRoute(self) -> bool:
        return False # TODO: Implement me

    def setJumpRoute(
            self,
            jumpRoute: typing.Optional[logic.JumpRoute],
            refuellingPlan: typing.Optional[typing.Iterable[logic.PitStop]] = None,
            pitStopRadius: float = 0.4, # Default to slightly larger than the size of the highlights Traveller Map puts on jump worlds
            pitStopColour: str = '#8080FF'
            ) -> None:
        pass # TODO: Implement me

    def clearJumpRoute(self) -> None:
        pass # TODO: Implement me

    def centerOnJumpRoute(self) -> None:
        pass # TODO: Implement me

    def highlightHex(
            self,
            hex: travellermap.HexPosition,
            radius: float = 0.5,
            colour: str = '#8080FF'
            ) -> None:
        pass # TODO: Implement me

    def highlightHexes(
            self,
            hexes: typing.Iterable[travellermap.HexPosition],
            radius: float = 0.5,
            colour: str = '#8080FF'
            ) -> None:
        pass # TODO: Implement me

    def clearHexHighlight(
            self,
            hex: travellermap.HexPosition
            ) -> None:
        pass # TODO: Implement me

    def clearHexHighlights(self) -> None:
        pass # TODO: Implement me

    # Create an overlay with a primitive at each hex
    def createHexOverlay(
            self,
            hexes: typing.Iterable[travellermap.HexPosition],
            primitive: PrimitiveType,
            fillColour: typing.Optional[str] = None,
            fillMap: typing.Optional[typing.Mapping[
                travellermap.HexPosition,
                str # Colour string
            ]] = None,
            radius: float = 0.5 # Only used for circle primitive
            ) -> str:
        return str(uuid.uuid4()) # TODO: Implement me

    def createHexGroupsOverlay(
            self,
            hexes: typing.Iterable[travellermap.HexPosition],
            fillColour: typing.Optional[str] = None,
            lineColour: typing.Optional[str] = None,
            lineWidth: typing.Optional[int] = None,
            outerOutlinesOnly: bool = False
            ) -> str:
        return str(uuid.uuid4()) # TODO: Implement me

    def createRadiusOverlay(
            self,
            center: travellermap.HexPosition,
            radius: int,
            fillColour: typing.Optional[str] = None,
            lineColour: typing.Optional[str] = None,
            lineWidth: typing.Optional[int] = None
            ) -> str:
        return str(uuid.uuid4()) # TODO: Implement me

    def removeOverlay(
            self,
            handle: str
            ) -> None:
        pass # TODO: Implement me

    def setToolTipCallback(
            self,
            callback: typing.Optional[typing.Callable[[typing.Optional[travellermap.HexPosition]], typing.Optional[str]]],
            ) -> None:
        pass # TODO: Implement me

    def createSnapshot(self) -> QtGui.QPixmap:
        pass # TODO: Implement me

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        super().mousePressEvent(event)

        if self.isEnabled() and event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._pixelDragStart = event.pos()
            self._worldDragAnchor = self._pixelSpaceToWorldSpace(self._pixelDragStart)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        super().mouseMoveEvent(event)
        if self.isEnabled() and self._renderer and self._worldDragAnchor:
            worldCurrentPos = self._pixelSpaceToWorldSpace(event.pos())
            worldDeltaX = worldCurrentPos.x() - self._worldDragAnchor.x()
            worldDeltaY = worldCurrentPos.y() - self._worldDragAnchor.y()

            self._absoluteCenterPos.setX(
                self._absoluteCenterPos.x() - worldDeltaX)
            self._absoluteCenterPos.setY(
                self._absoluteCenterPos.y() - worldDeltaY)
            self._updateRendererView()

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        super().mouseReleaseEvent(event)

        if not self.isEnabled():
            return

        leftRelease = event.button() == QtCore.Qt.MouseButton.LeftButton
        rightRelease = event.button() == QtCore.Qt.MouseButton.RightButton
        if not (leftRelease or rightRelease):
            return

        pixelReleasePos = QtCore.QPointF(event.x(), event.y())

        if leftRelease and self._pixelDragStart:
            clickRect = QtCore.QRectF(
                self._pixelDragStart.x() - self._LeftClickMoveThreshold,
                self._pixelDragStart.y() - self._LeftClickMoveThreshold,
                self._LeftClickMoveThreshold * 2,
                self._LeftClickMoveThreshold * 2)

            self._worldDragAnchor = self._pixelDragStart = None

            if not clickRect.contains(pixelReleasePos):
                return # A drag was performed so it doesn't count as a click

        hex = self._pixelSpaceToHex(pixelReleasePos)
        if leftRelease:
            self._handleLeftClickEvent(hex)
        else:
            self._handleRightClickEvent(hex)

    def focusOutEvent(self, event: QtGui.QFocusEvent) -> None:
        super().focusOutEvent(event)
        self._worldDragAnchor = self._pixelDragStart = None

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
                scale += LocalMapWidget._WheelLogScaleDelta if not gui.isShiftKeyDown() else -LocalMapWidget._WheelLogScaleDelta
                scale = common.clamp(scale, LocalMapWidget._MinScale, LocalMapWidget._MaxScale)
                self._viewScale.log = scale
                self._updateRendererView()
                return

            if event.key() == QtCore.Qt.Key.Key_F1:
                pass
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
                LocalMapWidget._TileRendering = not LocalMapWidget._TileRendering
                print(f'TileRendering={LocalMapWidget._TileRendering}')
                self.update()

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        super().wheelEvent(event)

        if self._renderer:
            oldWorldCursor = self._pixelSpaceToWorldSpace(event.pos())

            logViewScale = self._viewScale.log
            logViewScale += LocalMapWidget._WheelLogScaleDelta if event.angleDelta().y() > 0 else -LocalMapWidget._WheelLogScaleDelta
            logViewScale = common.clamp(logViewScale, LocalMapWidget._MinScale, LocalMapWidget._MaxScale)
            if logViewScale == self._viewScale.log:
                return # Reached min/max zoom
            self._viewScale.log = logViewScale

            newWorldCursor = self._pixelSpaceToWorldSpace(event.pos())

            self._absoluteCenterPos.setX(
                self._absoluteCenterPos.x() + (oldWorldCursor.x() - newWorldCursor.x()))
            self._absoluteCenterPos.setY(
                self._absoluteCenterPos.y() + (oldWorldCursor.y() - newWorldCursor.y()))

            self._updateRendererView()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        if not self._graphics or not self._renderer:
            return super().paintEvent(event)

        #print(f'View: {self.width()} {self.height()}')
        #print(f'Pos: {self._absoluteCenterPos.x()} {self._absoluteCenterPos.y()}')
        #print(f'Scale: Linear={self._viewScale.linear} Log={self._viewScale.log}')

        # TODO: Remove debug timer
        #with common.DebugTimer('Draw Time'):
        if True:
            if not LocalMapWidget._TileRendering and self._isWindows:
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

                if LocalMapWidget._TileRendering:
                    tiles = self._currentDrawTiles()

                    # This is disabled as I think it actually makes scaled tiles
                    # look worse (a bit to blurry)
                    """
                    painter.setRenderHint(
                        QtGui.QPainter.RenderHint.SmoothPixmapTransform,
                        True)
                    """

                    #with common.DebugTimer('Blit Time'):
                    if True:
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

                    if LocalMapWidget._LookaheadTiles and not self._tileQueue:
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

    def _handleLeftClickEvent(
            self,
            hex: typing.Optional[travellermap.HexPosition]
            ) -> None:
        if hex and self.isEnabled():
            self.leftClicked.emit(hex)

    def _handleRightClickEvent(
            self,
            hex: typing.Optional[travellermap.HexPosition]
            ) -> None:
        if hex and self.isEnabled():
            self.rightClicked.emit(hex)

    def _pixelSpaceToWorldSpace(
            self,
            pixelPos: typing.Union[QtCore.QPointF, QtCore.QPoint]
            ) -> QtCore.QPointF:
        scaleX = (self._viewScale.linear * travellermap.ParsecScaleX)
        scaleY = (self._viewScale.linear * travellermap.ParsecScaleY)

        width = self.width() / scaleX
        height = self.height() / scaleY

        offsetX = pixelPos.x() / scaleX
        offsetY = pixelPos.y() / scaleY

        return QtCore.QPointF(
            (self._absoluteCenterPos.x() - (width / 2)) + offsetX,
            (self._absoluteCenterPos.y() - (height / 2)) + offsetY)

    def _worldSpaceToPixelSpace(
            self,
            worldPos: typing.Union[QtCore.QPointF, QtCore.QPoint]
            ) -> QtCore.QPointF:
        scaleX = (self._viewScale.linear * travellermap.ParsecScaleX)
        scaleY = (self._viewScale.linear * travellermap.ParsecScaleY)

        width = self.width() / scaleX
        height = self.height() / scaleY

        offsetX = worldPos.x() - (self._absoluteCenterPos.x() - (width / 2))
        offsetY = worldPos.y() - (self._absoluteCenterPos.y() - (height / 2))

        return QtCore.QPointF(
            offsetX * scaleX,
            offsetY * scaleY)

    def _pixelSpaceToHex(
            self,
            pixelPos: typing.Union[QtCore.QPointF, QtCore.QPoint]
            ) -> travellermap.HexPosition:
        return self._worldSpaceToHex(self._pixelSpaceToWorldSpace(pixelPos))

    def _worldSpaceToHex(
            self,
            worldPos: typing.Union[QtCore.QPointF, QtCore.QPoint]
            ) -> travellermap.HexPosition:
        worldClampedX = int(round(worldPos.x() + 0.5))
        worldClampedY = int(round(worldPos.y() + (0.5 if (worldClampedX % 2 == 0) else 0)))

        return travellermap.HexPosition(
            absoluteX=worldClampedX,
            absoluteY=worldClampedY)

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
            labelCache=self._labelCache,
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
        tileSize = LocalMapWidget._TileSize * tileMultiplier

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
            absoluteOrigin = self._pixelSpaceToWorldSpace(cursorPos)
        else:
            # If the cursor is not over the window, fan out from the
            # center of the view when generating tiles
            absoluteOrigin = self._absoluteCenterPos
        centerTileX = math.floor(absoluteOrigin.x() / absoluteTileWidth)
        centerTileY = math.floor(absoluteOrigin.y() / absoluteTileHeight)

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
        tileSize = LocalMapWidget._TileSize * tileMultiplier

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
            if LocalMapWidget._DelayedRendering:
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
        if placeholderScale < LocalMapWidget._MinScale or placeholderScale > LocalMapWidget._MaxScale:
            return[]

        tileMultiplier = math.pow(2, self._viewScale.log - placeholderScale)
        tileSize = LocalMapWidget._TileSize * tileMultiplier

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
        absoluteTileWidth = LocalMapWidget._TileSize / scaleX
        absoluteTileHeight = LocalMapWidget._TileSize / scaleY

        absoluteTileCenterX = ((tileX * LocalMapWidget._TileSize) / scaleX) + (absoluteTileWidth / 2)
        absoluteTileCenterY = ((tileY * LocalMapWidget._TileSize) / scaleY) + (absoluteTileHeight / 2)

        if not image:
            image = QtGui.QImage(
                LocalMapWidget._TileSize,
                LocalMapWidget._TileSize,
                QtGui.QImage.Format.Format_ARGB32)
        painter = QtGui.QPainter()
        painter.begin(image)
        try:
            self._graphics.setPainter(painter=painter)
            self._renderer.setView(
                absoluteCenterX=absoluteTileCenterX,
                absoluteCenterY=absoluteTileCenterY,
                scale=tileScale,
                outputPixelX=LocalMapWidget._TileSize,
                outputPixelY=LocalMapWidget._TileSize)
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
            LocalMapWidget._TileSize,
            LocalMapWidget._TileSize,
            QtGui.QImage.Format.Format_ARGB32)
        rectsPerSize = math.ceil(LocalMapWidget._TileSize / LocalMapWidget._CheckerboardRectSize)

        painter = QtGui.QPainter()
        painter.begin(image)
        try:
            painter.setBrush(QtGui.QColor(LocalMapWidget._CheckerboardColourA))
            painter.drawRect(0, 0, LocalMapWidget._TileSize, LocalMapWidget._TileSize)

            painter.setBrush(QtGui.QColor(LocalMapWidget._CheckerboardColourB))
            for x in range(rectsPerSize):
                for y in range(1 if x % 2 else 0, rectsPerSize, 2):
                    painter.drawRect(
                        x * LocalMapWidget._CheckerboardRectSize,
                        y * LocalMapWidget._CheckerboardRectSize,
                        LocalMapWidget._CheckerboardRectSize,
                        LocalMapWidget._CheckerboardRectSize)
        finally:
            painter.end()

        return image
