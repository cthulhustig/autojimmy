import astronomer
import common
import enum
import cartographer
import math
import typing

class RenderContext(object):
    class LayerAction(object):
        def __init__(
                self,
                id: cartographer.LayerId,
                action: typing.Callable[[], typing.NoReturn]
                ) -> None:
            self.id = id
            self.action = action

    class WorldLayer(enum.Enum):
        Background = 0
        Foreground = 1
        Overlay = 2

    class MicroBorderLayer(enum.Enum):
        Background = 0
        Foreground = 1

    _MinScale = 0.0078125; # Math.Pow(2, -7)
    _MaxScale = 1024; # Math.Pow(2, 10)

    _PseudoRandomStarsChunkSize = 256
    _PseudoRandomStarsMaxPerChunk = 400

    # The nebula image is only 1024x1024 but, as with Traveller Map, it
    # gets rendered at double that
    _NebulaRenderWidth = 2048 # Pixels
    _NebulaRenderHeight = 2048 # Pixels

    _GridCacheCapacity = 50
    _WorldCacheCapacity = 500
    _ParsecGridSlop = 1

    _DefaultAllegiances = set([
        'Im', # Classic Imperium
        'ImAp', # Third Imperium, Amec Protectorate (Dagu)
        'ImDa', # Third Imperium, Domain of Antares (Anta/Empt/Lish)
        'ImDc', # Third Imperium, Domain of Sylea (Core/Delp/Forn/Mass)
        'ImDd', # Third Imperium, Domain of Deneb (Dene/Reft/Spin/Troj)
        'ImDg', # Third Imperium, Domain of Gateway (Glim/Hint/Ley)
        'ImDi', # Third Imperium, Domain of Ilelish (Daib/Ilel/Reav/Verg/Zaru)
        'ImDs', # Third Imperium, Domain of Sol (Alph/Dias/Magy/Olde/Solo)
        'ImDv', # Third Imperium, Domain of Vland (Corr/Dagu/Gush/Reft/Vlan)
        'ImLa', # Third Imperium, League of Antares (Anta)
        'ImLc', # Third Imperium, Lancian Cultural Region (Corr/Dagu/Gush)
        'ImLu', # Third Imperium, Luriani Cultural Association (Ley/Forn)
        'ImSy', # Third Imperium, Sylean Worlds (Core)
        'ImVd', # Third Imperium, Vegan Autonomous District (Solo)
        'XXXX', # Unknown
        '??', # Placeholder - show as blank
        '--', # Placeholder - show as blank
    ])

    def __init__(
            self,
            universe: astronomer.Universe,
            graphics: cartographer.AbstractGraphics,
            worldCenterX: float,
            worldCenterY: float,
            scale: float,
            outputPixelX: int,
            outputPixelY: int,
            milieu: astronomer.Milieu,
            style: cartographer.MapStyle,
            options: cartographer.RenderOptions,
            imageStore: cartographer.ImageStore,
            styleStore: cartographer.StyleStore,
            vectorStore: cartographer.VectorStore,
            labelStore: cartographer.LabelStore
            ) -> None:
        self._universe = universe
        self._graphics = graphics
        self._worldCenterX = worldCenterX
        self._worldCenterY = worldCenterY
        self._scale = common.clamp(scale, RenderContext._MinScale, RenderContext._MaxScale)
        self._outputPixelWidth = outputPixelX
        self._outputPixelHeight = outputPixelY
        self._outputClipRect = None
        self._options = options
        self._milieu = milieu
        self._styleSheet = cartographer.StyleSheet(
            scale=self._scale,
            options=self._options,
            style=style,
            graphics=self._graphics)
        self._imageStore = imageStore
        self._styleStore = styleStore
        self._vectorStore = vectorStore
        self._labelStore = labelStore
        self._sectorCache = cartographer.SectorCache(
            milieu=self._milieu,
            universe=self._universe,
            graphics=self._graphics,
            styleStore=self._styleStore)
        self._worldCache = cartographer.WorldCache(
            milieu=self._milieu,
            universe=self._universe,
            imageStore=self._imageStore,
            capacity=RenderContext._WorldCacheCapacity)
        self._gridCache = cartographer.GridCache(
            graphics=self._graphics,
            capacity=RenderContext._GridCacheCapacity)
        self._starfieldCache = cartographer.StarfieldCache(
            graphics=self._graphics)
        self._selector = cartographer.RectSelector(
            milieu=self._milieu,
            universe=self._universe)
        self._worldOutputRect = None
        self._worldViewRect = None
        self._imageSpaceToWorldSpace = None
        self._worldSpaceToImageSpace = None

        self._hexOutlinePath = self._graphics.createPath(
            points=[
                cartographer.PointF(-0.5 + astronomer.HexWidthOffset, -0.5),
                cartographer.PointF( 0.5 - astronomer.HexWidthOffset, -0.5),
                cartographer.PointF( 0.5 + astronomer.HexWidthOffset, 0),
                cartographer.PointF( 0.5 - astronomer.HexWidthOffset, 0.5),
                cartographer.PointF(-0.5 + astronomer.HexWidthOffset, 0.5),
                cartographer.PointF(-0.5 - astronomer.HexWidthOffset, 0),
                cartographer.PointF(-0.5 + astronomer.HexWidthOffset, -0.5)],
            closed=True)

        # Chosen to match T5 pp.416
        self._galaxyImageRect = cartographer.RectangleF(-18257, -26234, 36551, 32462)
        self._riftImageRect = cartographer.RectangleF(-1374, -827, 2769, 1754)

        self._parsecGrid: typing.Optional[cartographer.AbstractPointList] = None

        self._createLayers()
        self._updateView()

    def setView(
            self,
            worldCenterX: float,
            worldCenterY: float,
            scale: float,
            outputPixelWidth: int,
            outputPixelHeight: int,
            clipRect: typing.Optional[typing.Tuple[int, int, int, int]] = None
            ) -> None:
        scale = common.clamp(scale, RenderContext._MinScale, RenderContext._MaxScale)
        scaleUpdated = scale != self._scale

        self._worldCenterX = worldCenterX
        self._worldCenterY = worldCenterY
        self._scale = scale
        self._outputPixelWidth = outputPixelWidth
        self._outputPixelHeight = outputPixelHeight

        if clipRect:
            self._outputClipRect = cartographer.RectangleF(*clipRect)
        else:
            self._outputClipRect = None

        # NOTE: Updating the style sheet must be done before updating the view
        # as it needs to know if it should create a new parsec grid
        self._styleSheet.scale = self._scale

        self._updateView()

        if scaleUpdated:
            self._updateLayerOrder()

    def milieu(self) -> astronomer.Milieu:
        return self._milieu

    def setMilieu(
            self,
            milieu: astronomer.Milieu
            ) -> None:
        if milieu is self._milieu:
            return
        self._milieu = milieu
        self._sectorCache.setMilieu(milieu=self._milieu)
        self._worldCache.setMilieu(milieu=self._milieu)
        self._selector.setMilieu(milieu=self._milieu)

    def style(self) -> cartographer.MapStyle:
        return self._styleSheet.style

    def setStyle(
            self,
            style: cartographer.MapStyle
            ) -> None:
        self._styleSheet.style = style
        self._updateLayerOrder()

    def options(self) -> cartographer.RenderOptions:
        return self._styleSheet.options

    def setOptions(
            self,
            options: cartographer.RenderOptions
            ) -> None:
        self._styleSheet.options = options
        self._updateLayerOrder()

    def render(self) -> None:
        with self._graphics.save():
            if self._outputClipRect:
                self._graphics.intersectClipRect(self._outputClipRect)

            # Overall, rendering is all in world-space; individual steps may transform back
            # to image-space as needed.
            self._graphics.multiplyTransform(self._imageSpaceToWorldSpace)

            for layer in self._layers:
                #with common.DebugTimer(string=str(layer.action)):
                if True:
                    layer.action()

    def clearCaches(self) -> None:
        self._sectorCache.clear()
        self._worldCache.clear()
        self._gridCache.clear()
        self._starfieldCache.clear()

    def _createLayers(self) -> None:
        self._layers: typing.List[RenderContext.LayerAction] = [
            RenderContext.LayerAction(cartographer.LayerId.Background_Solid, self._drawBackground),

            RenderContext.LayerAction(cartographer.LayerId.Background_NebulaTexture, self._drawNebulaBackground),
            RenderContext.LayerAction(cartographer.LayerId.Background_Galaxy, self._drawGalaxyBackground),

            RenderContext.LayerAction(cartographer.LayerId.Background_PseudoRandomStars, self._drawPseudoRandomStars),
            RenderContext.LayerAction(cartographer.LayerId.Background_Rifts, self._drawRifts),

            #------------------------------------------------------------
            # Foreground
            #------------------------------------------------------------
            RenderContext.LayerAction(cartographer.LayerId.Macro_Borders, self._drawMacroBorders),
            RenderContext.LayerAction(cartographer.LayerId.Macro_Routes, self._drawMacroRoutes),

            RenderContext.LayerAction(cartographer.LayerId.Grid_Sector, self._drawSectorGrid),
            RenderContext.LayerAction(cartographer.LayerId.Grid_Subsector, self._drawSubsectorGrid),
            RenderContext.LayerAction(cartographer.LayerId.Grid_Parsec, self._drawParsecGrid),

            RenderContext.LayerAction(cartographer.LayerId.Names_Subsector, self._drawSubsectorNames),

            RenderContext.LayerAction(cartographer.LayerId.Micro_BordersBackground, self._drawMicroBordersBackground),
            RenderContext.LayerAction(cartographer.LayerId.Micro_BordersForeground, self._drawMicroBordersForeground),
            RenderContext.LayerAction(cartographer.LayerId.Micro_Routes, self._drawMicroRoutes),
            RenderContext.LayerAction(cartographer.LayerId.Micro_BorderExplicitLabels, self._drawMicroLabels),

            RenderContext.LayerAction(cartographer.LayerId.Names_Sector, self._drawSectorNames),
            RenderContext.LayerAction(cartographer.LayerId.Macro_GovernmentRiftRouteNames, self._drawMacroNames),
            RenderContext.LayerAction(cartographer.LayerId.Macro_CapitalsAndHomeWorlds, self._drawCapitalsAndHomeWorlds),
            RenderContext.LayerAction(cartographer.LayerId.Mega_GalaxyScaleLabels, self._drawMegaLabels),

            RenderContext.LayerAction(cartographer.LayerId.Worlds_Background, self._drawWorldsBackground),
            RenderContext.LayerAction(cartographer.LayerId.Worlds_Foreground, self._drawWorldsForeground),
            RenderContext.LayerAction(cartographer.LayerId.Worlds_Overlays, self._drawWorldsOverlay),

            #------------------------------------------------------------
            # Overlays
            #------------------------------------------------------------
            RenderContext.LayerAction(cartographer.LayerId.Overlay_DroyneChirperWorlds, self._drawDroyneOverlay),
            RenderContext.LayerAction(cartographer.LayerId.Overlay_MinorHomeworlds, self._drawMinorHomeworldOverlay),
            RenderContext.LayerAction(cartographer.LayerId.Overlay_AncientsWorlds, self._drawAncientWorldsOverlay),
            RenderContext.LayerAction(cartographer.LayerId.Overlay_ReviewStatus, self._drawSectorReviewStatusOverlay),
        ]

        self._updateLayerOrder()

    def _updateLayerOrder(self) -> None:
        self._layers.sort(key=lambda l: self._styleSheet.layerOrder.index(l.id))

    def _updateView(self):
        worldOutputWidth = self._outputPixelWidth / (self._scale * astronomer.ParsecScaleX)
        worldOutputHeight = self._outputPixelHeight / (self._scale * astronomer.ParsecScaleY)
        viewAreaChanged = (self._worldOutputRect is None) or \
            (worldOutputWidth != self._worldOutputRect.width()) or \
            (worldOutputHeight != self._worldOutputRect.height())

        self._worldOutputRect = cartographer.RectangleF(
            x=self._worldCenterX - (worldOutputWidth / 2),
            y=self._worldCenterY - (worldOutputHeight / 2),
            width=worldOutputWidth,
            height=worldOutputHeight)

        self._worldViewRect = self._worldOutputRect
        if self._outputClipRect:
            worldClipOffsetX = self._outputClipRect.x() / (self._scale * astronomer.ParsecScaleX)
            worldClipOffsetY = self._outputClipRect.y() / (self._scale * astronomer.ParsecScaleY)
            worldClipWidth = self._outputClipRect.width() / (self._scale * astronomer.ParsecScaleX)
            worldClipHeight = self._outputClipRect.height() / (self._scale * astronomer.ParsecScaleY)
            self._worldViewRect = cartographer.RectangleF(
                x=self._worldOutputRect.x() + worldClipOffsetX,
                y=self._worldOutputRect.y() + worldClipOffsetY,
                width=worldClipWidth,
                height=worldClipHeight)

        # This needs to be done after _worldViewRect is calculated
        self._selector.setRect(self._worldViewRect)

        m = self._graphics.createIdentityMatrix()
        m.scalePrepend(
            sx=self._scale * astronomer.ParsecScaleX,
            sy=self._scale * astronomer.ParsecScaleY)
        m.translatePrepend(
            dx=-self._worldOutputRect.left(),
            dy=-self._worldOutputRect.top())
        self._imageSpaceToWorldSpace = self._graphics.copyMatrix(other=m)
        m.invert()
        self._worldSpaceToImageSpace = self._graphics.copyMatrix(other=m)

        if self._styleSheet.parsecGrid.visible:
            if viewAreaChanged or not self._parsecGrid:
                self._parsecGrid = self._gridCache.grid(
                    parsecWidth=int(math.ceil(self._worldOutputRect.width())),
                    parsecHeight=int(math.ceil(self._worldOutputRect.height())))
        else:
            self._parsecGrid = None

    def _drawBackground(self) -> None:
        self._graphics.setSmoothingMode(
            cartographer.AbstractGraphics.SmoothingMode.HighSpeed)

        # NOTE: This is a comment from the original Traveller Map source code
        # HACK: Due to limited precisions of floats, tileRect can end up not covering
        # the full bitmap when far from the origin.
        rect = cartographer.RectangleF(self._worldViewRect)
        rect.inflate(rect.width() * 0.1, rect.height() * 0.1)
        self._graphics.drawRectangle(
            rect=rect,
            brush=self._styleSheet.backgroundBrush)

    # Nebula drawing is clunky as hell and doesn't really look right if you
    # look to closely as you zoom in and out. In the Traveller Map code the
    # nebula rendering is done in pixel space and the nebula tiles are
    # always drawn at the same pixel dimensions no mater what the current
    # scale. This is different to how things like the galaxy image which are
    # rendered in world coordinates as so the image scales as you zoom in
    # and out. I expect the reason this is done is so that the nebula is
    # rendered at a high resolution so it always looks nice (which it does
    # if you're just panning around at a single scale). The downside of
    # rendering like this is, as you zoom in/out, the nebula shifts in the
    # view window. In Traveller Map how bad this looks is lessened by tile
    # based rendering as you only see the nebula shift at the point you
    # transition between tile scales, not every time you zoom in/out.
    # My tile based rendering also has the same effect to lessen how bad it
    # looks. Where it's an issue is when not using tile based rendering as
    # it has the effect of making the nebula look like it's scrolling
    # sideways as you zoom. To help mitigate the issue I've updated the
    # nebula drawing code so that it always scales tiles in the same way as
    # they would scale on Traveller Map tiles

    def _drawNebulaBackground(self) -> None:
        if not self._styleSheet.showNebulaBackground:
            return

        renderLogScale = math.log2(self._scale)
        nebulaLogScale = int(math.floor(renderLogScale + 0.5))
        nebulaScale = math.pow(2, nebulaLogScale)

        nebulaWidth = RenderContext._NebulaRenderWidth / (nebulaScale * astronomer.ParsecScaleX)
        nebulaHeight = RenderContext._NebulaRenderHeight / (nebulaScale * astronomer.ParsecScaleY)

        nebulaLeft = (self._worldViewRect.left() // nebulaWidth) * nebulaWidth
        nebulaTop = (self._worldViewRect.top() // nebulaHeight) * nebulaHeight
        nebulaRight = ((self._worldViewRect.right() // nebulaWidth) + 1) * nebulaWidth
        nebulaBottom = ((self._worldViewRect.bottom() // nebulaHeight) + 1) * nebulaHeight

        hCount = math.ceil((nebulaRight - nebulaLeft) / nebulaWidth)
        vCount = math.ceil((nebulaBottom - nebulaTop) / nebulaHeight)

        for x in range(hCount):
            for y in range(vCount):
                rect = cartographer.RectangleF(
                    x=nebulaLeft + (x * nebulaWidth),
                    y=nebulaTop + (y * nebulaHeight),
                    width=nebulaWidth,
                    height=nebulaHeight)
                self._graphics.drawImage(
                    image=self._imageStore.nebulaImage,
                    rect=rect)

    def _drawGalaxyBackground(self) -> None:
        if not self._styleSheet.showGalaxyBackground:
            return

        if self._styleSheet.deepBackgroundOpacity > 0 and \
                self._galaxyImageRect.intersects(self._worldViewRect):
            galaxyImage = \
                self._imageStore.galaxyImageGray \
                if self._styleSheet.lightBackground else \
                self._imageStore.galaxyImage
            self._graphics.drawImageAlpha(
                self._styleSheet.deepBackgroundOpacity,
                galaxyImage,
                self._galaxyImageRect)

    # NOTE: How this is implemented differs from the Traveller Map implementation
    # as Traveller Map achieves consistent random star positioning by seeding the
    # rng by the tile origin. As the web interface always chunks the universe into
    # tiles with the same origins this means, for a given tile, the random stars
    # will always be in the same place.
    # This approach doesn't work for me as I want to support rendering a full
    # frame, effectively a single tile where the origin will vary depending on
    # where the current viewport is. To achieve a similar effect I'm chunking the
    # random stars by sector. The downside of this is you always have to draw
    # process all stars for all sectors overlapped by the viewport
    def _drawPseudoRandomStars(self) -> None:
        if not self._styleSheet.pseudoRandomStars.visible:
            return

        chunkParsecs = self._starfieldCache.chunkParsecs()
        startX = math.floor(self._worldViewRect.left() / chunkParsecs)
        startY = math.floor(self._worldViewRect.top() / chunkParsecs)
        finishX = math.ceil(self._worldViewRect.right() / chunkParsecs)
        finishY = math.ceil(self._worldViewRect.bottom() / chunkParsecs)

        r, g, b, _ = common.parseHtmlColour(
            self._styleSheet.pseudoRandomStars.fillBrush.colour())
        colour = common.formatHtmlColour(
            r, g, b,
            alpha=int(255 / self._starfieldCache.intensitySteps()))
        pen = self._graphics.createPen(
            colour=colour,
            width=1 / self._scale) # One pixel

        self._graphics.setSmoothingMode(
            cartographer.AbstractGraphics.SmoothingMode.HighQuality)

        for x in range(startX, finishX + 1):
            for y in range(startY, finishY + 1):
                with self._graphics.save():
                    starfield = self._starfieldCache.sectorStarfield(
                        chunkX=x,
                        chunkY=y)
                    self._graphics.translateTransform(
                        dx=x * chunkParsecs,
                        dy=y * chunkParsecs)
                    self._graphics.drawPoints(points=starfield, pen=pen)

    def _drawRifts(self) -> None:
        if not self._styleSheet.showRiftOverlay:
            return

        if self._styleSheet.riftOpacity > 0 and \
                self._riftImageRect.intersects(self._worldViewRect):
            self._graphics.drawImageAlpha(
                alpha=self._styleSheet.riftOpacity,
                image=self._imageStore.riftImage,
                rect=self._riftImageRect)

    def _drawMacroBorders(self) -> None:
        if not self._styleSheet.macroBorders.visible:
            return

        self._graphics.setSmoothingMode(
            cartographer.AbstractGraphics.SmoothingMode.AntiAlias)
        for vectorObject in self._vectorStore.borders:
            if (vectorObject.mapOptions & self._options & cartographer.RenderOptions.BordersMask) != 0:
                self._drawVectorObjectOutline(
                    vectorObject=vectorObject,
                    pen=self._styleSheet.macroBorders.linePen)

    def _drawMacroRoutes(self) -> None:
        if not self._styleSheet.macroRoutes.visible:
            return

        self._graphics.setSmoothingMode(
            cartographer.AbstractGraphics.SmoothingMode.AntiAlias)
        for vectorObject in self._vectorStore.routes:
            if (vectorObject.mapOptions & self._options & cartographer.RenderOptions.BordersMask) != 0:
                self._drawVectorObjectOutline(
                    vectorObject=vectorObject,
                    pen=self._styleSheet.macroRoutes.linePen)

    def _drawSectorGrid(self) -> None:
        if not self._styleSheet.sectorGrid.visible:
            return

        self._graphics.setSmoothingMode(
            cartographer.AbstractGraphics.SmoothingMode.HighSpeed)

        # Quantizes the left & top values so grid lines are always drawn from a
        # sector boundary that is off to the left/top of the view area. This is
        # done as a hack so that when the pattern drawn for non-solid lines is
        # always started from a 'constant' point
        left = ((self._worldViewRect.left() // astronomer.SectorWidth) * \
                astronomer.SectorWidth) - astronomer.ReferenceHexX
        right = self._worldViewRect.right()
        top = ((self._worldViewRect.top() // astronomer.SectorHeight) * \
               astronomer.SectorHeight) - astronomer.ReferenceHexY
        bottom = self._worldViewRect.bottom()

        x = left + astronomer.SectorWidth
        while x <= self._worldViewRect.right():
            self._graphics.drawLine(
                pt1=cartographer.PointF(x, top),
                pt2=cartographer.PointF(x, bottom),
                pen=self._styleSheet.sectorGrid.linePen)
            x += astronomer.SectorWidth

        y = top + astronomer.SectorHeight
        while y <= self._worldViewRect.bottom():
            self._graphics.drawLine(
                pt1=cartographer.PointF(left, y),
                pt2=cartographer.PointF(right, y),
                pen=self._styleSheet.sectorGrid.linePen)
            y += astronomer.SectorHeight

    def _drawSubsectorGrid(self) -> None:
        if not self._styleSheet.subsectorGrid.visible:
            return

        self._graphics.setSmoothingMode(
            cartographer.AbstractGraphics.SmoothingMode.HighSpeed)

        # Quantizes the left & top values so grid lines are always drawn from a
        # subsector boundary that is off to the left/top of the view area. This is
        # done as a hack so that when the pattern drawn for non-solid lines is
        # always started from a 'constant' point
        left = ((self._worldViewRect.left() // astronomer.SubsectorWidth) * \
                astronomer.SubsectorWidth) - astronomer.ReferenceHexX
        right = self._worldViewRect.right()
        top = ((self._worldViewRect.top() // astronomer.SubsectorHeight) * \
               astronomer.SubsectorHeight) - astronomer.ReferenceHexY
        bottom = self._worldViewRect.bottom()

        x = left + astronomer.SubsectorWidth
        lineIndex = int(round(x / astronomer.SubsectorWidth))
        while x <= self._worldViewRect.right():
            if lineIndex % 4:
                self._graphics.drawLine(
                    pt1=cartographer.PointF(x, top),
                    pt2=cartographer.PointF(x, bottom),
                    pen=self._styleSheet.subsectorGrid.linePen)
            x += astronomer.SubsectorWidth
            lineIndex += 1

        y = top + astronomer.SubsectorHeight
        lineIndex = int(round(y / astronomer.SubsectorHeight))
        while y <= self._worldViewRect.bottom():
            if lineIndex % 4:
                self._graphics.drawLine(
                    pt1=cartographer.PointF(left, y),
                    pt2=cartographer.PointF(right, y),
                    pen=self._styleSheet.subsectorGrid.linePen)
            y += astronomer.SubsectorHeight
            lineIndex += 1

    def _drawParsecGrid(self) -> None:
        if not self._styleSheet.parsecGrid.visible:
            return

        self._graphics.setSmoothingMode(
            cartographer.AbstractGraphics.SmoothingMode.HighQuality)

        if self._parsecGrid:
            with self._graphics.save():
                offsetX = math.floor(self._worldViewRect.left())
                offsetY = math.floor(self._worldViewRect.top()) + (0.5 if offsetX % 2 else 0)
                self._graphics.translateTransform(dx=offsetX, dy=offsetY)
                self._graphics.drawLines(
                    points=self._parsecGrid,
                    pen=self._styleSheet.parsecGrid.linePen)

        if self._styleSheet.numberAllHexes and (self._styleSheet.worldDetails & cartographer.WorldDetails.Hex) != 0:
            hx = int(math.floor(self._worldViewRect.x()))
            hw = int(math.ceil(self._worldViewRect.width()))
            hy = int(math.floor(self._worldViewRect.y()))
            hh = int(math.ceil(self._worldViewRect.height()))
            for px in range(hx - RenderContext._ParsecGridSlop, hx + hw + RenderContext._ParsecGridSlop):
                yOffset = 0 if ((px % 2) != 0) else 0.5
                for py in range(hy - RenderContext._ParsecGridSlop, hy + hh + RenderContext._ParsecGridSlop):
                    relativePos = astronomer.absoluteSpaceToRelativeSpace((px + 1, py + 1))
                    if self._styleSheet.hexCoordinateStyle == cartographer.HexCoordinateStyle.Subsector:
                        hex = '{hexX:02d}{hexY:02d}'.format(
                            hexX=int((relativePos[2] - 1) % astronomer.SubsectorWidth) + 1,
                            hexY=int((relativePos[3] - 1) % astronomer.SubsectorHeight) + 1)
                    else:
                        hex = '{hexX:02d}{hexY:02d}'.format(
                            hexX=relativePos[2],
                            hexY=relativePos[3])

                    with self._graphics.save():
                        scaleX = self._styleSheet.hexContentScale / astronomer.ParsecScaleX
                        scaleY = self._styleSheet.hexContentScale / astronomer.ParsecScaleY
                        self._graphics.scaleTransform(
                            scaleX=scaleX,
                            scaleY=scaleY)
                        self._graphics.drawString(
                            text=hex,
                            font=self._styleSheet.hexNumber.font,
                            brush=self._styleSheet.hexNumber.textBrush,
                            x=(px + 0.5) / scaleX,
                            y=(py + yOffset) / scaleY,
                            format=cartographer.TextAlignment.TopCenter)

    def _drawSubsectorNames(self) -> None:
        if not self._styleSheet.subsectorNames.visible:
            return

        self._graphics.setSmoothingMode(
            cartographer.AbstractGraphics.SmoothingMode.HighQuality)

        minX = int(math.floor(self._worldViewRect.left()))
        minY = int(math.floor(self._worldViewRect.top()))
        maxX = int(math.ceil(self._worldViewRect.right()))
        maxY = int(math.ceil(self._worldViewRect.bottom()))

        for x in range(minX, maxX + astronomer.SubsectorWidth, astronomer.SubsectorWidth):
            for y in range(minY, maxY + astronomer.SubsectorHeight, astronomer.SubsectorHeight):
                sectorX, sectorY, offsetX, offsetY = \
                    astronomer.absoluteSpaceToRelativeSpace((x, y))
                sectorIndex = astronomer.SectorIndex(
                    sectorX=sectorX,
                    sectorY=sectorY)
                sector = self._universe.sectorBySectorIndex(
                    milieu=self._milieu,
                    index=sectorIndex)
                if not sector:
                    continue

                subsectorIndex = astronomer.SubsectorIndex(
                    sectorX=sectorX,
                    sectorY=sectorY,
                    indexX=(offsetX - 1) // astronomer.SubsectorWidth,
                    indexY=(offsetY - 1) // astronomer.SubsectorHeight)
                subsector = sector.subsectorByCode(subsectorIndex.code())
                if not subsector:
                    continue

                subsectorName = subsector.name()
                if not subsectorName:
                    continue

                ulHex, brHex = subsectorIndex.hexExtent()
                left = ulHex.absoluteX() - 1
                top = ulHex.absoluteY() - 1
                right = brHex.absoluteX()
                bottom = brHex.absoluteY()

                self._drawLabel(
                    text=subsectorName,
                    center=cartographer.PointF(
                        x=(left + right) / 2,
                        y=(top + bottom) / 2),
                    font=self._styleSheet.subsectorNames.font,
                    brush=self._styleSheet.subsectorNames.textBrush,
                    labelStyle=self._styleSheet.subsectorNames.textStyle)

    def _drawMicroBordersBackground(self) -> None:
        if not self._styleSheet.microBorders.visible:
            return

        self._drawMicroBorders(layer=RenderContext.MicroBorderLayer.Background)

    def _drawMicroBordersForeground(self) -> None:
        if not self._styleSheet.microBorders.visible:
            return

        self._drawMicroBorders(layer=RenderContext.MicroBorderLayer.Foreground)

    def _drawMicroRoutes(self) -> None:
        if not self._styleSheet.microRoutes.visible:
            return

        with self._graphics.save():
            self._graphics.setSmoothingMode(
                cartographer.AbstractGraphics.SmoothingMode.AntiAlias)

            pen = self._graphics.createPen()
            baseWidth = self._styleSheet.microRoutes.linePen.width()

            for sector in self._selector.sectors():
                sectorRoutes = self._sectorCache.routeLines(
                    index=sector.index())
                for route in sectorRoutes:
                    routeColour = route.colour()
                    routeWidth = route.width()
                    routeStyle = self._styleSheet.overrideLineStyle
                    if not routeStyle:
                        if route.style() is astronomer.Route.Style.Solid:
                            routeStyle = cartographer.LineStyle.Solid
                        elif route.style() is astronomer.Route.Style.Dashed:
                            routeStyle = cartographer.LineStyle.Dash
                        elif route.style() is astronomer.Route.Style.Dotted:
                            routeStyle = cartographer.LineStyle.Dot

                    if not routeWidth or not routeColour or not routeStyle:
                        precedence = [route.allegiance(), route.type(), 'Im']
                        for key in precedence:
                            defaultColour, defaultStyle, defaultWidth = self._styleStore.routeStyle(key)
                            if not routeColour:
                                routeColour = defaultColour
                            if not routeStyle:
                                routeStyle = defaultStyle
                            if not routeWidth:
                                routeWidth = defaultWidth

                    # In grayscale, convert default colour and style to non-default style
                    if self._styleSheet.grayscale and (not routeColour) and (not routeStyle):
                        routeStyle = cartographer.LineStyle.Dash

                    if not routeWidth:
                        routeWidth = 1.0
                    if not routeColour:
                        routeColour = self._styleSheet.microRoutes.linePen.colour()
                    if not routeStyle:
                        routeStyle = cartographer.LineStyle.Solid

                    # Ensure colour is visible
                    if self._styleSheet.grayscale or \
                            not common.noticeableColourDifference(routeColour, self._styleSheet.backgroundBrush.colour()):
                        routeColour = self._styleSheet.microRoutes.linePen.colour() # default

                    pen.setColour(routeColour)
                    pen.setWidth(routeWidth * baseWidth)
                    pen.setStyle(routeStyle)

                    self._graphics.drawLines(
                        points=route.points(),
                        pen=pen)

    _LabelDefaultColour = common.HtmlColours.TravellerAmber

    def _drawMicroLabels(self) -> None:
        if not self._styleSheet.showMicroNames:
            return

        with self._graphics.save():
            self._graphics.setSmoothingMode(
                cartographer.AbstractGraphics.SmoothingMode.AntiAlias)

            brush = self._graphics.createBrush()
            for sector in self._selector.sectors():
                brush.copyFrom(self._styleSheet.microBorders.textBrush)

                for border in sector.yieldBorders():
                    if not border.showLabel():
                        continue

                    label = border.label()
                    labelPos = border.labelHex()
                    if not label or not labelPos:
                        continue

                    labelPos = RenderContext._hexToCenter(labelPos)
                    if border.labelOffsetX():
                        labelPos.setX(labelPos.x() + (border.labelOffsetX() * 0.7))
                    if border.labelOffsetY():
                        labelPos.setY(labelPos.y() - (border.labelOffsetY() * 0.7))

                    self._drawLabel(
                        text=label,
                        center=labelPos,
                        font=self._styleSheet.microBorders.font,
                        brush=brush,
                        labelStyle=self._styleSheet.microBorders.textStyle)

                for region in sector.yieldRegions():
                    if not region.showLabel():
                        continue

                    label = region.label()
                    labelPos = region.labelHex()
                    if not label or not labelPos:
                        continue

                    labelPos = RenderContext._hexToCenter(labelPos)
                    if region.labelOffsetX():
                        labelPos.setX(labelPos.x() + (region.labelOffsetX() * 0.7))
                    if region.labelOffsetY():
                        labelPos.setY(labelPos.y() - (region.labelOffsetY() * 0.7))

                    self._drawLabel(
                        text=label,
                        center=labelPos,
                        font=self._styleSheet.microBorders.font,
                        brush=brush,
                        labelStyle=self._styleSheet.microBorders.textStyle)

                for label in sector.yieldLabels():
                    text = label.text()

                    labelPos = RenderContext._hexToCenter(label.hex())
                    if label.offsetX():
                        labelPos.setX(labelPos.x() + (label.offsetX() * 0.7))
                    if label.offsetY():
                        labelPos.setY(labelPos.y() - (label.offsetY() * 0.7))

                    if label.size() is astronomer.Label.Size.Small:
                        font = self._styleSheet.microBorders.smallFont
                    elif label.size() is astronomer.Label.Size.Large:
                        font = self._styleSheet.microBorders.largeFont
                    else:
                        font = self._styleSheet.microBorders.font

                    useLabelColour = \
                        not self._styleSheet.grayscale and \
                        label.colour() and \
                        (label.colour() != RenderContext._LabelDefaultColour) and \
                        common.noticeableColourDifference(label.colour(), self._styleSheet.backgroundBrush.colour())
                    if useLabelColour:
                        brush.setColour(label.colour())

                    self._drawLabel(
                        text=text,
                        center=labelPos,
                        font=font,
                        brush=brush if useLabelColour else self._styleSheet.microBorders.textBrush,
                        labelStyle=self._styleSheet.microBorders.textStyle)

    def _drawSectorNames(self) -> None:
        if not (self._styleSheet.showSomeSectorNames or self._styleSheet.showAllSectorNames):
            return

        self._graphics.setSmoothingMode(
            cartographer.AbstractGraphics.SmoothingMode.HighQuality)

        for sector in self._selector.sectors():
            sectorLabel = sector.sectorLabel()

            if not self._styleSheet.showAllSectorNames and not sector.selected() \
                    and not sectorLabel:
                continue

            index = sector.index()
            centerX, centerY = astronomer.relativeSpaceToAbsoluteSpace((
                index.sectorX(),
                index.sectorY(),
                int(astronomer.SectorWidth // 2),
                int(astronomer.SectorHeight // 2)))

            self._drawLabel(
                text=sectorLabel if sectorLabel else sector.name(),
                center=cartographer.PointF(x=centerX, y=centerY),
                font=self._styleSheet.sectorName.font,
                brush=self._styleSheet.sectorName.textBrush,
                labelStyle=self._styleSheet.sectorName.textStyle)

    def _drawMacroNames(self) -> None:
        if  not self._styleSheet.macroNames.visible:
            return

        self._graphics.setSmoothingMode(
            cartographer.AbstractGraphics.SmoothingMode.HighQuality)

        for vectorObject in self._vectorStore.borders:
            if (vectorObject.mapOptions & self._options & cartographer.RenderOptions.NamesMask) == 0:
                continue
            major = (vectorObject.mapOptions & cartographer.RenderOptions.NamesMajor) != 0
            labelStyle = cartographer.LabelStyle(uppercase=major)
            font = \
                self._styleSheet.macroNames.font \
                if major else \
                self._styleSheet.macroNames.smallFont
            brush = \
                self._styleSheet.macroNames.textBrush \
                if major else \
                self._styleSheet.macroNames.textHighlightBrush
            self._drawVectorObjectName(
                vectorObject=vectorObject,
                font=font,
                textBrush=brush,
                labelStyle=labelStyle)

        for vectorObject in self._vectorStore.rifts:
            major = (vectorObject.mapOptions & cartographer.RenderOptions.NamesMajor) != 0
            labelStyle = cartographer.LabelStyle(rotation=35, uppercase=major)
            font = \
                self._styleSheet.macroNames.font \
                if major else \
                self._styleSheet.macroNames.smallFont
            brush = \
                self._styleSheet.macroNames.textBrush \
                if major else \
                self._styleSheet.macroNames.textHighlightBrush
            self._drawVectorObjectName(
                vectorObject=vectorObject,
                font=font,
                textBrush=brush,
                labelStyle=labelStyle)

        if self._styleSheet.macroRoutes.visible:
            for vectorObject in self._vectorStore.routes:
                if (vectorObject.mapOptions & self._options & cartographer.RenderOptions.NamesMask) == 0:
                    continue
                major = (vectorObject.mapOptions & cartographer.RenderOptions.NamesMajor) != 0
                labelStyle = cartographer.LabelStyle(uppercase=major)
                font = \
                    self._styleSheet.macroNames.font \
                    if major else \
                    self._styleSheet.macroNames.smallFont
                brush = \
                    self._styleSheet.macroRoutes.textBrush \
                    if major else \
                    self._styleSheet.macroRoutes.textHighlightBrush
                self._drawVectorObjectName(
                    vectorObject=vectorObject,
                    font=font,
                    textBrush=brush,
                    labelStyle=labelStyle)

        if (self._options & cartographer.RenderOptions.NamesMinor) != 0:
            for label in self._labelStore.minorLabels():
                font = self._styleSheet.macroNames.smallFont if label.minor else self._styleSheet.macroNames.mediumFont
                brush = \
                    self._styleSheet.macroRoutes.textBrush \
                    if label.minor else \
                    self._styleSheet.macroRoutes.textHighlightBrush
                with self._graphics.save():
                    self._graphics.scaleTransform(
                        scaleX=1.0 / astronomer.ParsecScaleX,
                        scaleY=1.0 / astronomer.ParsecScaleY)
                    self._drawMultiLineString(
                        text=label.text,
                        font=font,
                        brush=brush,
                        x=label.position.x() * astronomer.ParsecScaleX,
                        y=label.position.y() * astronomer.ParsecScaleY)

    def _drawCapitalsAndHomeWorlds(self) -> None:
        if not self._styleSheet.capitals.visible or \
                (self._options & cartographer.RenderOptions.WorldsMask) == 0:
            return

        dotPen = self._graphics.createPen(
            colour=self._styleSheet.capitals.fillBrush.colour(),
            width=1)
        dotBrush = self._styleSheet.capitals.fillBrush
        dotRadius = 3
        dotRect = cartographer.RectangleF(
            x=-dotRadius / 2,
            y=-dotRadius / 2,
            width=dotRadius,
            height=dotRadius)

        with self._graphics.save():
            self._graphics.setSmoothingMode(
                cartographer.AbstractGraphics.SmoothingMode.HighQuality)
            for worldLabel in self._labelStore.worldLabels():
                if (worldLabel.options & self._options) == 0:
                    continue

                with self._graphics.save():
                    self._graphics.translateTransform(
                        dx=worldLabel.position.x(),
                        dy=worldLabel.position.y())
                    self._graphics.scaleTransform(
                        scaleX=1.0 / astronomer.ParsecScaleX,
                        scaleY=1.0 / astronomer.ParsecScaleY)

                    self._graphics.drawEllipse(
                        rect=dotRect,
                        pen=dotPen,
                        brush=dotBrush)

                    if worldLabel.biasX > 0:
                        if worldLabel.biasY < 0:
                            format = cartographer.TextAlignment.BottomLeft
                        elif worldLabel.biasY > 0:
                            format = cartographer.TextAlignment.TopLeft
                        else:
                            format = cartographer.TextAlignment.MiddleLeft
                    elif worldLabel.biasX < 0:
                        if worldLabel.biasY < 0:
                            format = cartographer.TextAlignment.BottomRight
                        elif worldLabel.biasY > 0:
                            format = cartographer.TextAlignment.TopRight
                        else:
                            format = cartographer.TextAlignment.MiddleRight
                    else:
                        if worldLabel.biasY < 0:
                            format = cartographer.TextAlignment.BottomCenter
                        elif worldLabel.biasY > 0:
                            format = cartographer.TextAlignment.TopCenter
                        else:
                            format = cartographer.TextAlignment.Centered

                    self._drawMultiLineString(
                        text=worldLabel.text,
                        font=self._styleSheet.macroNames.smallFont,
                        brush=self._styleSheet.capitals.textBrush,
                        x=worldLabel.biasX * dotRadius / 2,
                        y=worldLabel.biasY * dotRadius / 2,
                        format=format)

    def _drawMegaLabels(self) -> None:
        if not self._styleSheet.megaNames.visible:
            return

        self._graphics.setSmoothingMode(
            cartographer.AbstractGraphics.SmoothingMode.HighQuality)
        for label in self._labelStore.megaLabels():
            with self._graphics.save():
                font = self._styleSheet.megaNames.smallFont if label.minor else self._styleSheet.megaNames.font
                self._graphics.scaleTransform(
                    scaleX=1.0 / astronomer.ParsecScaleX,
                    scaleY=1.0 / astronomer.ParsecScaleY)
                self._drawMultiLineString(
                    text=label.text,
                    font=font,
                    brush=self._styleSheet.megaNames.textBrush,
                    x=label.position.x() * astronomer.ParsecScaleX,
                    y=label.position.y() * astronomer.ParsecScaleY)

    def _drawWorldsBackground(self) -> None:
        if not self._styleSheet.worlds.visible or self._styleSheet.showStellarOverlay \
                or not self._styleSheet.worldDetails or self._styleSheet.worldDetails is cartographer.WorldDetails.NoDetails:
            return

        renderAllNames = (self._styleSheet.worldDetails & cartographer.WorldDetails.AllNames) != 0
        renderKeyNames = (self._styleSheet.worldDetails & cartographer.WorldDetails.KeyNames) != 0
        renderZone = (self._styleSheet.worldDetails & cartographer.WorldDetails.Zone) != 0
        renderHex = (self._styleSheet.worldDetails & cartographer.WorldDetails.Hex) != 0
        renderSubsector = self._styleSheet.hexCoordinateStyle is cartographer.HexCoordinateStyle.Subsector
        renderType = (self._styleSheet.worldDetails & cartographer.WorldDetails.Type) != 0

        # Check for early out when style means nothing will be rendered
        if not self._styleSheet.useWorldImages:
            if (not renderZone) and (self._styleSheet.numberAllHexes or not renderHex):
                return
        else:
            if not renderType:
                return

        worlds = self._selector.worlds()
        self._worldCache.ensureCapacity(len(worlds))

        with self._graphics.save():
            self._graphics.setSmoothingMode(
                cartographer.AbstractGraphics.SmoothingMode.AntiAlias)

            scaleX = self._styleSheet.hexContentScale / astronomer.ParsecScaleX
            scaleY = self._styleSheet.hexContentScale / astronomer.ParsecScaleY
            self._graphics.scaleTransform(
                scaleX=scaleX,
                scaleY=scaleY)

            rect = cartographer.RectangleF()
            for world in worlds:
                worldInfo = self._worldCache.worldInfo(hex=world.hex())

                renderName = False
                if renderAllNames or renderKeyNames:
                    renderName = renderAllNames or worldInfo.isCapital or worldInfo.isHiPop
                renderUWP = (self._styleSheet.worldDetails & cartographer.WorldDetails.Uwp) != 0

                with self._graphics.save():
                    self._graphics.translateTransform(
                        dx=worldInfo.hexCenter.x() / scaleX,
                        dy=worldInfo.hexCenter.y() / scaleY)

                    if not self._styleSheet.useWorldImages:
                        # Normal (non-"Eye Candy") styles
                        if renderZone:
                            element = self._zoneStyle(worldInfo)
                            if element and element.visible:
                                if self._styleSheet.showZonesAsPerimeters:
                                    with self._graphics.save():
                                        self._graphics.scaleTransform(
                                            scaleX=0.95 * astronomer.ParsecScaleX,
                                            scaleY=0.95 * astronomer.ParsecScaleY)
                                        self._graphics.drawPath(
                                            path=self._hexOutlinePath,
                                            pen=element.linePen)
                                else:
                                    if element.fillBrush:
                                        rect.setRect(x=-0.4, y=-0.4, width=0.8, height=0.8)
                                        self._graphics.drawEllipse(
                                            rect=rect,
                                            brush=element.fillBrush)
                                    if element.linePen:
                                        if renderName and self._styleSheet.fillMicroBorders:
                                            with self._graphics.save():
                                                rect.setRect(
                                                    x=-0.5,
                                                    y=-0.5,
                                                    width=1,
                                                    height=0.65 if renderUWP else 0.75)
                                                self._graphics.intersectClipRect(rect=rect)

                                                rect.setRect(x=-0.4, y=-0.4, width=0.8, height=0.8)
                                                self._graphics.drawEllipse(
                                                    rect=rect,
                                                    pen=element.linePen)
                                        else:
                                            rect.setRect(x=-0.4, y=-0.4, width=0.8, height=0.8)
                                            self._graphics.drawEllipse(
                                                rect=rect,
                                                pen=element.linePen)

                        if not self._styleSheet.numberAllHexes and renderHex:
                            numberText = \
                                worldInfo.ssHexString \
                                if renderSubsector else \
                                worldInfo.hexString

                            self._graphics.drawString(
                                text=numberText,
                                font=self._styleSheet.hexNumber.font,
                                brush=self._styleSheet.hexNumber.textBrush,
                                x=self._styleSheet.hexNumber.position.x(),
                                y=self._styleSheet.hexNumber.position.y(),
                                format=cartographer.TextAlignment.TopCenter)
                    else: # styles.useWorldImages
                        # "Eye-Candy" style
                        if worldInfo.isPlaceholder:
                            element = self._styleSheet.anomaly if worldInfo.isAnomaly else self._styleSheet.placeholder
                            self._drawWorldLabel(
                                bkStyle=element.textBackgroundStyle,
                                bkBrush=self._styleSheet.worlds.textBrush,
                                textBrush=element.textBrush,
                                position=element.position,
                                font=element.font,
                                text=element.content)
                        else:
                            imageScaleX = 1.5 if worldInfo.worldSize <= 0 else 1
                            imageScaleY = 1.0 if worldInfo.worldSize <= 0 else 1
                            rect.setRect(
                                x=-worldInfo.imageRadius * imageScaleX,
                                y=-worldInfo.imageRadius * imageScaleY,
                                width=worldInfo.imageRadius * 2 * imageScaleX,
                                height=worldInfo.imageRadius * 2 * imageScaleY)
                            self._graphics.drawImage(
                                image=worldInfo.worldImage,
                                rect=rect)

            for placeholder in self._selector.placeholderWorlds(True):
                with self._graphics.save():
                    placeholderHex = placeholder.hex()
                    centerX, centerY = placeholderHex.worldCenter()
                    self._graphics.translateTransform(
                        dx=centerX / scaleX,
                        dy=centerY / scaleY)

                    self._drawWorldLabel(
                        bkStyle=self._styleSheet.placeholder.textBackgroundStyle,
                        bkBrush=self._styleSheet.worlds.textBrush,
                        textBrush=self._styleSheet.placeholder.textBrush,
                        position=self._styleSheet.placeholder.position,
                        font=self._styleSheet.placeholder.font,
                        text=self._styleSheet.placeholder.content)

                    if not self._styleSheet.numberAllHexes and renderHex:
                        if renderSubsector:
                            numberText = '{hexX:02d}{hexY:02d}'.format(
                                hexX=int((placeholderHex.offsetX() - 1) % astronomer.SubsectorWidth) + 1,
                                hexY=int((placeholderHex.offsetY() - 1) % astronomer.SubsectorHeight) + 1)
                        else:
                            numberText = '{hexX:02d}{hexY:02d}'.format(
                                hexX=placeholderHex.offsetX(),
                                hexY=placeholderHex.offsetY())

                        self._graphics.drawString(
                            text=numberText,
                            font=self._styleSheet.hexNumber.font,
                            brush=self._styleSheet.hexNumber.textBrush,
                            x=self._styleSheet.hexNumber.position.x(),
                            y=self._styleSheet.hexNumber.position.y(),
                            format=cartographer.TextAlignment.TopCenter)

    def _drawWorldsForeground(self) -> None:
        if not self._styleSheet.worlds.visible or self._styleSheet.showStellarOverlay:
            return

        if not self._styleSheet.worldDetails or self._styleSheet.worldDetails is cartographer.WorldDetails.NoDetails:
            # Render dot map
            with self._graphics.save():
                self._graphics.setSmoothingMode(
                    cartographer.AbstractGraphics.SmoothingMode.AntiAlias)

                # Scale by the parsec scale so we are rendering in a coordinate
                # space that has the same scaling on the x & y axis (I think the
                # term is isotropic scaling). This is works on the assumption
                # that the world points to be rendered have already been
                # transformed into this coordinate space. It's necessary because
                # (for speed) the worlds are being rendered as points with the
                # pen width giving them their size. If this was done in world
                # coordinate space (where x & y don't scale the same) then the
                # point would be drawn as an oval
                self._graphics.scaleTransform(
                    scaleX=self._styleSheet.hexContentScale / astronomer.ParsecScaleX,
                    scaleY=self._styleSheet.hexContentScale / astronomer.ParsecScaleY)

                pen = self._graphics.createPen(
                    colour=self._styleSheet.worlds.textBrush.colour(),
                    width=self._styleSheet.discRadius * self._styleSheet.hexContentScale * 2,
                    style=cartographer.LineStyle.Solid,
                    tip=cartographer.PenTip.Round) # Rounded end cap so a circle is drawn

                for sector in self._selector.sectors(tight=True):
                    worlds = self._sectorCache.isotropicWorldPoints(
                        index=sector.index())
                    if worlds:
                        self._graphics.drawPoints(points=worlds, pen=pen)

                for sector in self._selector.placeholderSectors(tight=True):
                    worlds = self._sectorCache.isotropicWorldPoints(
                        index=sector.index())
                    if worlds:
                        self._graphics.drawPoints(points=worlds, pen=pen)

            return # Nothing more to do

        worlds = self._selector.worlds()
        self._worldCache.ensureCapacity(len(worlds))

        renderAllNames = (self._styleSheet.worldDetails & cartographer.WorldDetails.AllNames) != 0
        renderKeyNames = (self._styleSheet.worldDetails & cartographer.WorldDetails.KeyNames) != 0
        renderUWP = (self._styleSheet.worldDetails & cartographer.WorldDetails.Uwp) != 0
        renderGasGiants = (self._styleSheet.worldDetails & cartographer.WorldDetails.GasGiant) != 0
        renderStarport = (self._styleSheet.worldDetails & cartographer.WorldDetails.Starport) != 0
        renderBases = (self._styleSheet.worldDetails & cartographer.WorldDetails.Bases) != 0
        renderAsteroids = (self._styleSheet.worldDetails & cartographer.WorldDetails.Asteroids) != 0
        renderHighlight = (self._styleSheet.worldDetails & cartographer.WorldDetails.Highlight) != 0
        renderAllegiances = (self._styleSheet.worldDetails & cartographer.WorldDetails.Allegiance) != 0
        renderZone = (self._styleSheet.worldDetails & cartographer.WorldDetails.Zone) != 0
        # NOTE: WorldDetails.Type isn't checked for as (with the current implementation) it is
        # always set when the dot map isn't being rendered so it must be set now

        worldDiscRect = cartographer.RectangleF(
            x=self._styleSheet.discPosition.x() - self._styleSheet.discRadius,
            y=self._styleSheet.discPosition.y() - self._styleSheet.discRadius,
            width=self._styleSheet.discRadius * 2,
            height=self._styleSheet.discRadius * 2)

        with self._graphics.save():
            self._graphics.setSmoothingMode(
                cartographer.AbstractGraphics.SmoothingMode.AntiAlias)

            scaleX = self._styleSheet.hexContentScale / astronomer.ParsecScaleX
            scaleY = self._styleSheet.hexContentScale / astronomer.ParsecScaleY
            self._graphics.scaleTransform(scaleX=scaleX, scaleY=scaleY)

            for world in worlds:
                worldInfo = self._worldCache.worldInfo(hex=world.hex())
                renderName = False
                if renderAllNames or renderKeyNames:
                    renderName = renderAllNames or worldInfo.isCapital or worldInfo.isHiPop

                with self._graphics.save():
                    self._graphics.translateTransform(
                        dx=worldInfo.hexCenter.x() / scaleX,
                        dy=worldInfo.hexCenter.y() / scaleY)

                    if not self._styleSheet.useWorldImages:
                        # Normal (non-"Eye Candy") styles
                        element = self._zoneStyle(worldInfo)
                        worldTextBackgroundStyle = \
                            cartographer.TextBackgroundStyle.NoStyle \
                            if element and element.fillBrush else \
                            self._styleSheet.worlds.textBackgroundStyle

                        if not worldInfo.isPlaceholder:
                            if worldInfo.hasGasGiant and renderGasGiants:
                                self._drawGasGiant(
                                    x=self._styleSheet.gasGiant.position.x(),
                                    y=self._styleSheet.gasGiant.position.y())

                            if renderStarport:
                                starport = worldInfo.starport
                                if self._styleSheet.showTL:
                                    starport += "-" + worldInfo.techLevel

                                self._drawWorldLabel(
                                    bkStyle=worldTextBackgroundStyle,
                                    bkBrush=self._styleSheet.uwp.fillBrush,
                                    textBrush=self._styleSheet.worlds.textBrush,
                                    position=self._styleSheet.starport.position,
                                    font=self._styleSheet.starport.font,
                                    text=starport)

                            if renderUWP:
                                self._drawWorldLabel(
                                    bkStyle=self._styleSheet.uwp.textBackgroundStyle,
                                    bkBrush=self._styleSheet.uwp.fillBrush,
                                    textBrush=self._styleSheet.uwp.textBrush,
                                    position=self._styleSheet.uwp.position,
                                    font=self._styleSheet.hexNumber.font,
                                    text=worldInfo.uwpString)

                            if renderBases:
                                # Base 1
                                bottomUsed = False
                                if worldInfo.primaryBaseGlyph and worldInfo.primaryBaseGlyph.isPrintable:
                                    pt = self._styleSheet.baseTopPosition
                                    if worldInfo.primaryBaseGlyph.bias is cartographer.Glyph.GlyphBias.Bottom and \
                                            not self._styleSheet.ignoreBaseBias:
                                        pt = self._styleSheet.baseBottomPosition
                                        bottomUsed = True

                                    brush = \
                                        self._styleSheet.worlds.textHighlightBrush \
                                        if worldInfo.primaryBaseGlyph.highlight else \
                                        self._styleSheet.worlds.textBrush
                                    self._drawWorldGlyph(
                                        glyph=worldInfo.primaryBaseGlyph,
                                        brush=brush,
                                        position=pt)

                                # Base 2
                                if worldInfo.secondaryBaseGlyph and worldInfo.secondaryBaseGlyph.isPrintable:
                                    pt = \
                                        self._styleSheet.baseTopPosition \
                                        if bottomUsed else \
                                        self._styleSheet.baseBottomPosition
                                    brush = \
                                        self._styleSheet.worlds.textHighlightBrush \
                                        if worldInfo.secondaryBaseGlyph.highlight else \
                                        self._styleSheet.worlds.textBrush
                                    self._drawWorldGlyph(
                                        glyph=worldInfo.secondaryBaseGlyph,
                                        brush=brush,
                                        position=pt)

                                # Base 3 (!)
                                if worldInfo.tertiaryBaseGlyph and worldInfo.tertiaryBaseGlyph.isPrintable:
                                    brush = \
                                        self._styleSheet.worlds.textHighlightBrush \
                                        if worldInfo.tertiaryBaseGlyph.highlight else \
                                        self._styleSheet.worlds.textBrush
                                    self._drawWorldGlyph(
                                        glyph=worldInfo.tertiaryBaseGlyph,
                                        brush=brush,
                                        position=self._styleSheet.baseMiddlePosition)

                                # Research Stations
                                if worldInfo.specialFeatureGlyph and worldInfo.specialFeatureGlyph.isPrintable:
                                    brush = \
                                        self._styleSheet.worlds.textHighlightBrush \
                                        if worldInfo.specialFeatureGlyph.highlight else \
                                        self._styleSheet.worlds.textBrush
                                    self._drawWorldGlyph(
                                        glyph=worldInfo.specialFeatureGlyph,
                                        brush=brush,
                                        # NOTE: If there is a 3rd base and a special feature they
                                        # will be drawn at the same location. This is consistent with
                                        # what Traveller Map does
                                        position=self._styleSheet.baseMiddlePosition)

                            if worldInfo.asteroidRectangles:
                                if renderAsteroids:
                                    with self._graphics.save():
                                        self._graphics.translateTransform(
                                            dx=self._styleSheet.discPosition.x(),
                                            dy=self._styleSheet.discPosition.y())
                                        for asteroidRect in worldInfo.asteroidRectangles:
                                            self._graphics.drawEllipse(
                                                rect=asteroidRect,
                                                brush=self._styleSheet.worlds.textBrush)
                                else:
                                    self._drawWorldGlyph(
                                        glyph=cartographer.GlyphDefs.DiamondX,
                                        brush=self._styleSheet.worlds.textBrush,
                                        position=cartographer.PointF(
                                            self._styleSheet.discPosition.x(),
                                            self._styleSheet.discPosition.y()))
                            else:
                                element = self._worldStyle(worldInfo)
                                self._graphics.drawEllipse(
                                    rect=worldDiscRect,
                                    pen=element.linePen,
                                    brush=element.fillBrush)
                        else:
                            # World is a placeholder
                            element = self._styleSheet.anomaly if worldInfo.isAnomaly else self._styleSheet.placeholder
                            self._drawWorldLabel(
                                bkStyle=element.textBackgroundStyle,
                                bkBrush=self._styleSheet.worlds.textBrush,
                                textBrush=element.textBrush,
                                position=element.position,
                                font=element.font,
                                text=element.content)

                        if renderName and worldInfo.name:
                            name = worldInfo.name
                            if (worldInfo.isHiPop and renderHighlight) or \
                                    self._styleSheet.worlds.textStyle.uppercase:
                                name = worldInfo.upperName

                            textBrush = \
                                self._styleSheet.worlds.textHighlightBrush \
                                if worldInfo.isCapital and renderHighlight else \
                                self._styleSheet.worlds.textBrush

                            font = \
                                self._styleSheet.worlds.largeFont \
                                if (worldInfo.isHiPop or worldInfo.isCapital) and renderHighlight else \
                                self._styleSheet.worlds.font

                            self._drawWorldLabel(
                                bkStyle=worldTextBackgroundStyle,
                                bkBrush=self._styleSheet.worlds.textBrush,
                                textBrush=textBrush,
                                position=self._styleSheet.worlds.textStyle.translation,
                                font=font,
                                text=name)

                        if renderAllegiances and worldInfo.t5Allegiance not in RenderContext._DefaultAllegiances:
                            allegiance = \
                                worldInfo.t5Allegiance \
                                if self._styleSheet.t5AllegianceCodes else \
                                worldInfo.legacyAllegiance

                            if allegiance:
                                if self._styleSheet.lowerCaseAllegiance:
                                    allegiance = allegiance.lower()

                                self._graphics.drawString(
                                    text=allegiance,
                                    font=self._styleSheet.worlds.smallFont,
                                    brush=self._styleSheet.worlds.textBrush,
                                    x=self._styleSheet.allegiancePosition.x(),
                                    y=self._styleSheet.allegiancePosition.y(),
                                    format=cartographer.TextAlignment.Centered)
                    else: # styles.useWorldImages
                        # "Eye-Candy" style
                        if worldInfo.isPlaceholder:
                            return

                        decorationRadius = worldInfo.imageRadius + 0.1

                        if renderZone:
                            if worldInfo.isAmberZone or worldInfo.isRedZone:
                                pen = \
                                    self._styleSheet.amberZone.linePen \
                                    if worldInfo.isAmberZone else \
                                    self._styleSheet.redZone.linePen
                                rect = cartographer.RectangleF(
                                    x=-decorationRadius,
                                    y=-decorationRadius,
                                    width=decorationRadius * 2,
                                    height=decorationRadius * 2)

                                self._graphics.drawArc(
                                    rect=rect,
                                    startDegrees=5,
                                    sweepDegrees=80,
                                    pen=pen)
                                self._graphics.drawArc(
                                    rect=rect,
                                    startDegrees=95,
                                    sweepDegrees=80,
                                    pen=pen)
                                self._graphics.drawArc(
                                    rect=rect,
                                    startDegrees=185,
                                    sweepDegrees=80,
                                    pen=pen)
                                self._graphics.drawArc(
                                    rect=rect,
                                    startDegrees=275,
                                    sweepDegrees=80,
                                    pen=pen)
                                decorationRadius += 0.1

                        if renderGasGiants:
                            if self._styleSheet.showGasGiantRing:
                                decorationRadius += self._styleSheet.gasGiantRadius
                            self._drawGasGiant(
                                x=decorationRadius,
                                y=0)
                            decorationRadius += 0.1

                        if renderUWP:
                            self._graphics.drawString(
                                text=worldInfo.uwpString,
                                font=self._styleSheet.hexNumber.font,
                                brush=self._styleSheet.worlds.textBrush,
                                x=decorationRadius,
                                y=self._styleSheet.uwp.position.y(),
                                format=cartographer.TextAlignment.MiddleLeft)

                        if renderName and worldInfo.name:
                            name = worldInfo.name
                            if worldInfo.isHiPop or self._styleSheet.worlds.textStyle.uppercase:
                                name = worldInfo.upperName

                            with self._graphics.save():
                                textBrush = \
                                    self._styleSheet.worlds.textHighlightBrush \
                                    if worldInfo.isCapital and renderHighlight else \
                                    self._styleSheet.worlds.textBrush

                                self._graphics.translateTransform(
                                    dx=decorationRadius,
                                    dy=0.0)
                                self._graphics.scaleTransform(
                                    scaleX=self._styleSheet.worlds.textStyle.scale.width(),
                                    scaleY=self._styleSheet.worlds.textStyle.scale.height())
                                self._graphics.translateTransform(
                                    dx=self._graphics.measureString(
                                        text=name,
                                        font=self._styleSheet.worlds.font)[0] / 2,
                                    dy=0.0) # Left align

                                self._drawWorldLabel(
                                    bkStyle=self._styleSheet.worlds.textBackgroundStyle,
                                    bkBrush=self._styleSheet.worlds.textBrush,
                                    textBrush=textBrush,
                                    position=self._styleSheet.worlds.textStyle.translation,
                                    font=self._styleSheet.worlds.font,
                                    text=name)

    def _drawWorldsOverlay(self) -> None:
        if not self._styleSheet.worlds.visible:
            return

        if self._styleSheet.showStellarOverlay:
            for world in self._selector.worlds():
                self._drawStars(world)
        elif self._styleSheet.hasWorldOverlays:
            oldSlop = self._selector.worldSlop()
            self._selector.setWorldSlop(max(oldSlop, math.log2(self._scale) - 2))
            try:
                for world in self._selector.worlds():
                    worldInfo = self._worldCache.worldInfo(hex=world.hex())

                    with self._graphics.save():
                        self._graphics.setSmoothingMode(
                            cartographer.AbstractGraphics.SmoothingMode.AntiAlias)

                        self._graphics.translateTransform(
                            dx=worldInfo.hexCenter.x(),
                            dy=worldInfo.hexCenter.y())
                        self._graphics.scaleTransform(
                            scaleX=self._styleSheet.hexContentScale / astronomer.ParsecScaleX,
                            scaleY=self._styleSheet.hexContentScale / astronomer.ParsecScaleY)

                        if self._styleSheet.populationOverlay.visible and worldInfo.populationOverlayRadius > 0:
                            self._drawOverlay(
                                element=self._styleSheet.populationOverlay,
                                radius=worldInfo.populationOverlayRadius)

                        if self._styleSheet.importanceOverlay.visible and worldInfo.importanceOverlayRadius > 0:
                            self._drawOverlay(
                                element=self._styleSheet.importanceOverlay,
                                radius=worldInfo.importanceOverlayRadius)

                        if self._styleSheet.capitalOverlay.visible:
                            if worldInfo.isImportant and worldInfo.isCapital:
                                self._drawOverlay(
                                    element=self._styleSheet.capitalOverlay,
                                    radius=2 * astronomer.ParsecScaleX)
                            elif worldInfo.isImportant:
                                self._drawOverlay(
                                    element=self._styleSheet.capitalOverlayAltA,
                                    radius=2 * astronomer.ParsecScaleX)
                            elif worldInfo.isCapital:
                                self._drawOverlay(
                                    element=self._styleSheet.capitalOverlayAltB,
                                    radius=2 * astronomer.ParsecScaleX)
            finally:
                self._selector.setWorldSlop(oldSlop)

    def _drawDroyneOverlay(self) -> None:
        if not self._styleSheet.droyneWorlds.visible:
            return

        self._graphics.setSmoothingMode(
            cartographer.AbstractGraphics.SmoothingMode.HighQuality)
        for world in self._selector.worlds():
            allegiance = world.allegiance()
            remarks = world.remarks()

            allegianceCode = allegiance.code() if allegiance else None
            droyne = allegianceCode == 'Dr' or allegianceCode == 'NaDr' or remarks.hasRemark('Droy')
            chirpers = remarks.hasRemark('Chir')

            if droyne or chirpers:
                glyph = self._styleSheet.droyneWorlds.content[0 if droyne else 1]
                self._drawOverlayGlyph(
                    glyph=glyph,
                    font=self._styleSheet.droyneWorlds.font,
                    brush=self._styleSheet.droyneWorlds.textBrush,
                    position=world.hex())

    def _drawMinorHomeworldOverlay(self) -> None:
        if not self._styleSheet.minorHomeWorlds.visible:
            return

        self._graphics.setSmoothingMode(
            cartographer.AbstractGraphics.SmoothingMode.HighQuality)
        for world in self._selector.worlds():
            remarks = world.remarks()
            if remarks.isMinorHomeworld():
                self._drawOverlayGlyph(
                    glyph=self._styleSheet.minorHomeWorlds.content,
                    font=self._styleSheet.minorHomeWorlds.font,
                    brush=self._styleSheet.minorHomeWorlds.textBrush,
                    position=world.hex())

    def _drawAncientWorldsOverlay(self) -> None:
        if not self._styleSheet.ancientsWorlds.visible:
            return

        self._graphics.setSmoothingMode(
            cartographer.AbstractGraphics.SmoothingMode.HighQuality)
        for world in self._selector.worlds():
            remarks = world.remarks()
            if remarks.hasTradeCode(astronomer.TradeCode.AncientsSiteWorld):
                self._drawOverlayGlyph(
                    glyph=self._styleSheet.ancientsWorlds.content,
                    font=self._styleSheet.ancientsWorlds.font,
                    brush=self._styleSheet.ancientsWorlds.textBrush,
                    position=world.hex())

    def _drawSectorReviewStatusOverlay(self) -> None:
        brush = self._graphics.createBrush()

        if self._styleSheet.dimUnofficialSectors and self._styleSheet.worlds.visible:
            brush.setColour(cartographer.makeAlphaColour(
                alpha=128,
                colour=self._styleSheet.backgroundBrush.colour()))
            for sector in self._selector.sectors(tight=True):
                tagging = sector.tagging()
                shouldDim = sector.isCustom()
                if not shouldDim:
                    shouldDim = not tagging.contains(astronomer.SectorTagging.Tag.Official) and \
                        not tagging.contains(astronomer.SectorTagging.Tag.Preserve) and \
                        not tagging.contains(astronomer.SectorTagging.Tag.InReview)
                if shouldDim:
                    clipPath = self._sectorCache.clipPath(
                        index=sector.index())

                    self._graphics.drawPath(
                        path=clipPath,
                        brush=brush)

        if self._styleSheet.colourCodeSectorStatus and self._styleSheet.worlds.visible:
            for sector in self._selector.sectors(tight=True):
                tagging = sector.tagging()
                if tagging.contains(astronomer.SectorTagging.Tag.Official):
                    brush.setColour(cartographer.makeAlphaColour(
                        alpha=128,
                        colour=common.HtmlColours.TravellerRed))
                elif tagging.contains(astronomer.SectorTagging.Tag.InReview):
                    brush.setColour(cartographer.makeAlphaColour(
                        alpha=128,
                        colour=common.HtmlColours.Orange))
                elif tagging.contains(astronomer.SectorTagging.Tag.Unreviewed):
                    brush.setColour(cartographer.makeAlphaColour(
                        alpha=128,
                        colour=common.HtmlColours.TravellerAmber))
                elif tagging.contains(astronomer.SectorTagging.Tag.Apocryphal):
                    brush.setColour(cartographer.makeAlphaColour(
                        alpha=128,
                        colour=common.HtmlColours.Magenta))
                elif tagging.contains(astronomer.SectorTagging.Tag.Preserve):
                    brush.setColour(cartographer.makeAlphaColour(
                        alpha=128,
                        colour=common.HtmlColours.TravellerGreen))
                else:
                    continue

                clipPath = self._sectorCache.clipPath(
                    index=sector.index())

                self._graphics.drawPath(
                    path=clipPath,
                    brush=brush)

    def _drawWorldLabel(
            self,
            bkStyle: cartographer.TextBackgroundStyle,
            bkBrush: cartographer.AbstractBrush,
            textBrush: str,
            position: cartographer.PointF,
            font: cartographer.AbstractFont,
            text: str
            ) -> None:
        width, height = self._graphics.measureString(text=text, font=font)

        # NOTE: This increase is needed as I use a tight bounds for the text
        # and Traveller Map uses a bounds with margins
        width += 0.05
        height += 0.05

        if bkStyle is cartographer.TextBackgroundStyle.Rectangle:
            if not self._styleSheet.fillMicroBorders:
                self._graphics.drawRectangle(
                    rect=cartographer.RectangleF(
                        x=position.x() - width / 2,
                        y=position.y() - height / 2,
                        width=width,
                        height=height),
                    brush=self._styleSheet.backgroundBrush)
        elif bkStyle is cartographer.TextBackgroundStyle.Filled:
            self._graphics.drawRectangle(
                rect=cartographer.RectangleF(
                    x=position.x() - width / 2,
                    y=position.y() - height / 2,
                    width=width,
                    height=height),
                brush=bkBrush)
        elif bkStyle is cartographer.TextBackgroundStyle.Outline or \
                bkStyle is cartographer.TextBackgroundStyle.Shadow:

            # Invert the current scaling transforms
            sx = 1.0 / self._styleSheet.hexContentScale
            sy = 1.0 / self._styleSheet.hexContentScale
            sx *= astronomer.ParsecScaleX
            sy *= astronomer.ParsecScaleY
            sx /= self._scale * astronomer.ParsecScaleX
            sy /= self._scale * astronomer.ParsecScaleY

            outlineSize = 2
            outlineSkip = 1

            outlineStart = -outlineSize if bkStyle is cartographer.TextBackgroundStyle.Outline else 0

            dx = outlineStart
            while dx <= outlineSize:
                dy = outlineStart
                while dy <= outlineSize:
                    self._graphics.drawString(
                        text=text,
                        font=font,
                        brush=self._styleSheet.backgroundBrush,
                        x=position.x() + sx * dx,
                        y=position.y() + sy * dy,
                        format=cartographer.TextAlignment.Centered)
                    dy += outlineSkip
                dx += outlineSkip

        self._graphics.drawString(
            text=text,
            font=font,
            brush=textBrush,
            x=position.x(),
            y=position.y(),
            format=cartographer.TextAlignment.Centered)

    def _drawStars(self, world: astronomer.World) -> None:
        with self._graphics.save():
            self._graphics.setSmoothingMode(
                cartographer.AbstractGraphics.SmoothingMode.AntiAlias)
            center = self._hexToCenter(world.hex())

            self._graphics.translateTransform(dx=center.x(), dy=center.y())
            self._graphics.scaleTransform(
                scaleX=self._styleSheet.hexContentScale / astronomer.ParsecScaleX,
                scaleY=self._styleSheet.hexContentScale / astronomer.ParsecScaleY)

            pen = self._graphics.createPen()
            pen.setStyle(cartographer.LineStyle.Solid)
            # The traveller map code doesn't initialise the width and it wasn't
            # immediately obvious what the default with. Based on a visual
            # comparison it looks like it's defaulting to always have a width of
            # 1 pixel which in Qt is a value of 0 and is called a 'cosmetic pen'
            pen.setWidth(0)
            brush = self._graphics.createBrush()
            for i, (fillColour, lineColour, radius) in enumerate(RenderContext._worldStarProps(world=world)):
                brush.setColour(fillColour)
                pen.setColour(lineColour)
                offset = RenderContext._starOffset(i)
                offsetScale = 0.3
                radius *= 0.15
                self._graphics.drawEllipse(
                    rect=cartographer.RectangleF(
                        x=offset.x() * offsetScale - radius,
                        y=offset.y() * offsetScale - radius,
                        width=radius * 2,
                        height=radius * 2),
                    pen=pen,
                    brush=brush)

    def _drawGasGiant(
            self,
            x: float,
            y: float
            ) -> None:
        width = self._styleSheet.gasGiantRadius * 2

        rect = cartographer.RectangleF(
            x=x - self._styleSheet.gasGiantRadius,
            y=y - self._styleSheet.gasGiantRadius,
            width=width,
            height=width)

        self._graphics.drawEllipse(
            rect=rect,
            brush=self._styleSheet.gasGiant.fillBrush)

        if self._styleSheet.showGasGiantRing:
            with self._graphics.save():
                self._graphics.translateTransform(dx=x, dy=y)
                self._graphics.rotateTransform(degrees=-30)

                rect.setRect(
                    x=-self._styleSheet.gasGiantRadius * 1.75,
                    y=-self._styleSheet.gasGiantRadius * 0.4,
                    width=self._styleSheet.gasGiantRadius * 1.75 * 2,
                    height=self._styleSheet.gasGiantRadius * 0.4 * 2)
                self._graphics.drawEllipse(
                    rect=rect,
                    pen=self._styleSheet.gasGiant.linePen)

    def _drawOverlay(
            self,
            element: cartographer.StyleSheet.StyleElement,
            radius: float
            ) -> None:
        # Prevent "Out of memory" exception when rendering to GDI+.
        if radius < 0.001:
            return

        self._graphics.drawEllipse(
            rect=cartographer.RectangleF(
                x=-radius,
                y=-radius,
                width=radius * 2,
                height=radius * 2),
            pen=element.linePen,
            brush=element.fillBrush)

    _MicroBorderFillAlpha = 64
    _MicroBorderShadeAlpha = 128

    def _drawMicroBorders(
            self,
            layer: MicroBorderLayer
            ) -> None:
        self._graphics.setSmoothingMode(
            cartographer.AbstractGraphics.SmoothingMode.HighQuality)

        brush = pen = None
        if layer is RenderContext.MicroBorderLayer.Background:
            brush = self._graphics.createBrush()

            if self._styleSheet.shadeMicroBorders:
                pen = self._graphics.createPen(
                    width=self._styleSheet.microBorders.linePen.width() * 2.5,
                    style=cartographer.LineStyle.Solid)
        else:
            pen = self._graphics.createPen(
                width=self._styleSheet.microBorders.linePen.width())

        drawCurvedBorders = self._styleSheet.microBorderStyle is cartographer.MicroBorderStyle.Curve
        drawRegions = drawBorders = False
        if layer is RenderContext.MicroBorderLayer.Background:
            drawRegions = True
            drawBorders = self._styleSheet.fillMicroBorders or self._styleSheet.shadeMicroBorders
        else:
            drawRegions = False
            drawBorders = True

        for sector in self._selector.sectors():
            sectorClipPath = self._sectorCache.clipPath(
                index=sector.index())
            sectorClipRect = sectorClipPath.bounds()
            if drawCurvedBorders and self._scale >= 16:
                # HACK: Inflate the sector clip bounds slightly when drawing
                # curved borders to account for the fact the borders can extend
                # out slightly past the hexes they enclose.
                # If I'm ever looking to tweak the bloat value then Juro in
                # Mavuzog is a good test as it is inside a border that touches
                # the edge of the sector and will be clipped if this value is to
                # low. Note that the fill is expected to be clipped but the
                # outline is not. This is consistent with Traveller Map and is
                # down to the fact the fill isn't drawn as a curve.
                # HACK: The fact this is only done as scale value >= 16 is a
                # hack to workaround a draw issue with candy style. Micro
                # borders are rendered as closed polygons so that when border
                # filling is enabled they can be filled. When a logical border
                # covers multiple sectors, each sector has it's own closed
                # polygons representing the area of that sector that is within
                # the border with edges of that polygons running along the edges
                # of the sector where it abuts other sectors in the same logical
                # boundary. When drawing the outline of borders we don't want
                # the polygon edges at the junction between sectors in the same
                # logical border to be shown as the are just a graphical
                # necessity rather than part of the logical boundary. When
                # rendering non-candy styles, not showing these edges is handled
                # by clipping to the sector outline when drawing borders for
                # that sector. I found this doesn't work reliably for candy due
                # a combination of the line width used for borders and the fact
                # it uses curved borders so the border outlines extend outside
                # the hexes they contain. The end result was at some scales
                # (generally < linear 16) there would be noticeable dotted lines
                # running along the boundaries of sectors inside the same
                # border. Part of the solution to this issue is to slightly
                # reduce the width of the border outline compared to the width
                # Traveller Map would use. The other part is to disable the
                # oversizing of the sector bounding box done when rendering zoom
                # levels where the issue was seen. This oversizing is done to
                # prevent the outlines of borders contained completely within
                # the sector from being incorrectly clipped when if they touch
                # the edge of the sector due to the curved outline extending
                # outside the boundary of the hexes they contain. Disabling this
                # oversizing at lower scale values isn't an issue as it's past
                # the point where incorrect clipping of these internal borders
                # is that noticeable.
                sectorClipRect.inflate(
                    astronomer.ParsecScaleX * 0.1,
                    astronomer.ParsecScaleY * 0.1)
            if not self._worldViewRect.intersects(sectorClipRect):
                continue

            sectorRegions = self._sectorCache.regionPaths(
                index=sector.index())
            regionOutlines: typing.List[cartographer.SectorPath] = []
            if sectorRegions and drawRegions:
                for outline in sectorRegions:
                    outlineBounds = \
                        outline.spline().bounds() \
                        if drawCurvedBorders else \
                        outline.path().bounds()
                    if self._worldViewRect.intersects(outlineBounds):
                        regionOutlines.append(outline)

            sectorBorders = self._sectorCache.borderPaths(
                index=sector.index())
            borderOutlines: typing.List[cartographer.SectorPath] = []
            if sectorBorders and drawBorders:
                for outline in sectorBorders:
                    outlineBounds = \
                        outline.spline().bounds() \
                        if drawCurvedBorders else \
                        outline.path().bounds()
                    if self._worldViewRect.intersects(outlineBounds):
                        borderOutlines.append(outline)

            if not regionOutlines and not borderOutlines:
                continue

            if layer is RenderContext.MicroBorderLayer.Background and \
                    borderOutlines and self._styleSheet.fillMicroBorders and \
                    drawCurvedBorders:
                # When drawing filled curved borders the clipping of the fill
                # needs to be handled separately from border pen/shade and
                # regions. This is required due to the kind of hacky way
                # drawing filled borders are handled in Traveller Map. Rather
                # than there being a single polygon covering multiple sectors,
                # each sector has polygons for their portion of the area covered
                # by the border. The problem is that in some cases (e.g. Core)
                # the polygon for that sector extends outside area of that
                # sector. This is problematic if you have to draw two sectors
                # like this next to each other as the regions where the borders
                # overlap are drawn darker. To work around this we clip border
                # fills to the sector outline, this is the same way Traveller
                # Map works around the issue. My code is slightly different as
                # rather than having regions, border fills, border shades
                # and border strokes as 4 render passes, I combine them into
                # just 2 to reduce the number of times the sector clip path is
                # applied to the graphics as it's a relatively costly operation
                with self._graphics.save():
                    self._graphics.intersectClipPath(path=sectorClipPath)

                    for outline in borderOutlines:
                        colour = self._calculateBorderColour(outline)
                        brush.setColour(cartographer.makeAlphaColour(
                            alpha=RenderContext._MicroBorderFillAlpha,
                            colour=colour))
                        self._drawMicroBorder(
                            outline=outline,
                            brush=brush)

            with self._graphics.save():
                useBrush = layer is RenderContext.MicroBorderLayer.Background and \
                    self._styleSheet.fillMicroBorders and not drawCurvedBorders
                usePen = pen is not None

                # Clip the drawing to the sector. When drawing curved borders
                # a slightly expanded clip rect is used rather than the
                # exact sector hex outline as curved borders draw slightly
                # outside the sectors true area
                if not drawCurvedBorders:
                    self._graphics.intersectClipPath(path=sectorClipPath)
                else:
                    self._graphics.intersectClipRect(rect=sectorClipRect)

                for outline in regionOutlines:
                    colour = self._calculateBorderColour(outline)
                    brush.setColour(cartographer.makeAlphaColour(
                        alpha=RenderContext._MicroBorderFillAlpha,
                        colour=colour))

                    self._drawMicroBorder(
                        outline=outline,
                        brush=brush)

                if useBrush or usePen:
                    for outline in borderOutlines:
                        colour = self._calculateBorderColour(outline)

                        if useBrush:
                            brush.setColour(cartographer.makeAlphaColour(
                                alpha=RenderContext._MicroBorderFillAlpha,
                                colour=colour))

                        if usePen:
                            if layer is RenderContext.MicroBorderLayer.Background:
                                pen.setColour(cartographer.makeAlphaColour(
                                    alpha=RenderContext._MicroBorderShadeAlpha,
                                    colour=colour))
                            else:
                                pen.setColour(colour)

                                style = self._styleSheet.microBorders.linePen.style()
                                if style is cartographer.LineStyle.Solid:
                                    style = outline.style()
                                    if not style:
                                        style = cartographer.LineStyle.Solid
                                pen.setStyle(style)

                        self._drawMicroBorder(
                            outline=outline,
                            brush=brush if useBrush else None,
                            pen=pen if usePen else None)

    def _calculateBorderColour(self, outline: cartographer.SectorPath) -> str:
        colour = outline.colour()
        if not colour:
            colour = self._styleSheet.microRoutes.linePen.colour()

        if self._styleSheet.grayscale or \
                not common.noticeableColourDifference(colour, self._styleSheet.backgroundBrush.colour()):
            colour = self._styleSheet.microBorders.linePen.colour()

        return colour

    def _drawMicroBorder(
            self,
            outline: cartographer.SectorPath,
            brush: typing.Optional[cartographer.AbstractBrush] = None,
            pen: typing.Optional[cartographer.AbstractPen] = None
            ) -> None:
        if self._styleSheet.microBorderStyle is cartographer.MicroBorderStyle.Curve:
            self._graphics.drawCurve(
                spline=outline.spline(),
                pen=pen,
                brush=brush)
        elif pen:
            with self._graphics.save():
                # Clip to the path itself - this means adjacent borders don't clash
                self._graphics.intersectClipPath(path=outline.path())
                self._graphics.drawPath(
                    path=outline.path(),
                    pen=pen,
                    brush=brush)
        else:
            self._graphics.drawPath(
                path=outline.path(),
                brush=brush)

    def _drawVectorObjectOutline(
            self,
            vectorObject: cartographer.VectorObject,
            pen: cartographer.AbstractPen
            ) -> None:
        if vectorObject.path and vectorObject.bounds.intersects(self._worldViewRect):
            with self._graphics.save():
                self._graphics.scaleTransform(scaleX=vectorObject.scaleX, scaleY=vectorObject.scaleY)
                self._graphics.translateTransform(dx=-vectorObject.originX, dy=-vectorObject.originY)
                self._graphics.drawPath(path=vectorObject.path, pen=pen)

    def _drawVectorObjectName(
            self,
            vectorObject: cartographer.VectorObject,
            font: cartographer.AbstractFont,
            textBrush: cartographer.AbstractBrush,
            labelStyle: cartographer.LabelStyle
            ) -> None:
        if vectorObject.name and vectorObject.bounds.intersects(self._worldViewRect):
            text = vectorObject.name
            if labelStyle.uppercase:
                text = text.upper()

            with self._graphics.save():
                self._graphics.translateTransform(
                    dx=vectorObject.namePosition.x(),
                    dy=vectorObject.namePosition.y())
                self._graphics.scaleTransform(
                    scaleX=1.0 / astronomer.ParsecScaleX,
                    scaleY=1.0 / astronomer.ParsecScaleY)
                self._graphics.rotateTransform(-labelStyle.rotation)

                self._drawMultiLineString(
                    text=text,
                    font=font,
                    brush=textBrush,
                    x=0, y=0)

    _WorldDingMap = {
        '\u2666': '\x74', # U+2666 (BLACK DIAMOND SUIT)
        '\u2756': '\x76', # U+2756 (BLACK DIAMOND MINUS WHITE X)
        '\u2726': '\xAA', # U+2726 (BLACK FOUR POINTED STAR)
        '\u2605': '\xAB', # U+2605 (BLACK STAR)
        '\u2736': '\xAC'} # U+2736 (BLACK SIX POINTED STAR)

    def _drawWorldGlyph(
            self,
            glyph: cartographer.Glyph,
            brush: cartographer.AbstractBrush,
            position: cartographer.PointF
            ) -> None:
        font = self._styleSheet.glyphFont
        s = glyph.characters
        if self._styleSheet.wingdingFont:
            dings = ''
            for c in s:
                c = RenderContext._WorldDingMap.get(c)
                if c is None:
                    dings = ''
                    break
                dings += c
            if dings:
                font = self._styleSheet.wingdingFont
                s = dings

        self._graphics.drawString(
            text=s,
            font=font,
            brush=brush,
            x=position.x(),
            y=position.y(),
            format=cartographer.TextAlignment.Centered)

    def _drawOverlayGlyph(
            self,
            glyph: str,
            font: cartographer.AbstractFont,
            brush: cartographer.AbstractBrush,
            position: astronomer.HexPosition
            ) -> None:
        centerX, centerY = position.worldCenter()
        with self._graphics.save():
            self._graphics.scaleTransform(
                scaleX=1 / astronomer.ParsecScaleX,
                scaleY=1 / astronomer.ParsecScaleY)
            self._graphics.drawString(
                text=glyph,
                font=font,
                brush=brush,
                x=centerX * astronomer.ParsecScaleX,
                y=centerY * astronomer.ParsecScaleY,
                format=cartographer.TextAlignment.Centered)

    def _drawLabel(
            self,
            text: str,
            center: cartographer.PointF,
            font: cartographer.AbstractFont,
            brush: cartographer.AbstractBrush,
            labelStyle: cartographer.LabelStyle
            ) -> None:
        with self._graphics.save():
            if labelStyle.uppercase:
                text = text.upper()
            if labelStyle.wrap:
                text = text.replace(' ', '\n')

            self._graphics.translateTransform(
                dx=center.x(),
                dy=center.y())
            self._graphics.scaleTransform(
                scaleX=1.0 / astronomer.ParsecScaleX,
                scaleY=1.0 / astronomer.ParsecScaleY)

            self._graphics.translateTransform(
                dx=labelStyle.translation.x(),
                dy=labelStyle.translation.y())
            self._graphics.rotateTransform(
                degrees=labelStyle.rotation)
            self._graphics.scaleTransform(
                scaleX=labelStyle.scale.width(),
                scaleY=labelStyle.scale.height())

            if labelStyle.rotation != 0:
                self._graphics.setSmoothingMode(
                    cartographer.AbstractGraphics.SmoothingMode.AntiAlias)

            self._drawMultiLineString(
                text=text,
                font=font,
                brush=brush,
                x=0, y=0)

    def _drawMultiLineString(
            self,
            text: str,
            font: cartographer.AbstractFont,
            brush: cartographer.AbstractBrush,
            x: float,
            y: float,
            format: cartographer.TextAlignment = cartographer.TextAlignment.Centered
            ) -> None:
        if not text:
            return

        lines = text.split('\n')
        if len(lines) <= 1:
            self._graphics.drawString(
                text=text,
                font=font,
                brush=brush,
                x=x, y=y,
                format=format)
            return

        widths = [self._graphics.measureString(line, font)[0] for line in lines]

        fontUnitsToWorldUnits = font.emSize() / font.pointSize()
        lineSpacing = font.lineSpacing() * fontUnitsToWorldUnits

        totalHeight = lineSpacing * len(widths)

        # Offset from baseline to top-left.
        y += lineSpacing / 2

        widthFactor = 0
        if format == cartographer.TextAlignment.MiddleLeft or \
                format == cartographer.TextAlignment.Centered or \
                format == cartographer.TextAlignment.MiddleRight:
            y -= totalHeight / 2
        elif format == cartographer.TextAlignment.BottomLeft or \
                format == cartographer.TextAlignment.BottomCenter or \
                format == cartographer.TextAlignment.BottomRight:
            y -= totalHeight

        if format == cartographer.TextAlignment.TopCenter or \
                format == cartographer.TextAlignment.Centered or \
                format == cartographer.TextAlignment.BottomCenter:
            widthFactor = -0.5
        elif format == cartographer.TextAlignment.TopRight or \
                format == cartographer.TextAlignment.MiddleRight or \
                format == cartographer.TextAlignment.BottomRight:
            widthFactor = -1

        for line, width in zip(lines, widths):
            self._graphics.drawString(
                text=line,
                font=font,
                brush=brush,
                x=x + widthFactor * width + width / 2,
                y=y,
                format=cartographer.TextAlignment.Centered)
            y += lineSpacing

    def _zoneStyle(
            self,
            worldInfo: cartographer.WorldInfo
            ) -> typing.Optional[cartographer.StyleSheet.StyleElement]:
        if worldInfo.isAmberZone:
            return self._styleSheet.amberZone
        if worldInfo.isRedZone:
            return self._styleSheet.redZone
        if self._styleSheet.greenZone.visible and not worldInfo.isPlaceholder:
            return self._styleSheet.greenZone
        return None

    def _worldStyle(
            self,
            worldInfo: cartographer.WorldInfo
            ) -> cartographer.StyleSheet.StyleElement:
        if self._styleSheet.showWorldDetailColours:
            if worldInfo.isAgricultural and worldInfo.isRich:
                return self._styleSheet.worldRichAgricultural
            elif worldInfo.isAgricultural:
                return self._styleSheet.worldAgricultural
            elif worldInfo.isRich:
                return self._styleSheet.worldRich
            elif worldInfo.isIndustrial:
                return self._styleSheet.worldIndustrial
            elif worldInfo.isHarshAtmosphere:
                return self._styleSheet.worldHarshAtmosphere
            elif worldInfo.isVacuum:
                return self._styleSheet.worldVacuum
            elif worldInfo.hasWater:
                return self._styleSheet.worldWater
            else:
                return self._styleSheet.worldNoWater

        return self._styleSheet.worldWater if worldInfo.hasWater else self._styleSheet.worldNoWater

    _StarPropsMap = {
        'O': ('#9DB4FF', 4),
        'B': ('#BBCCFF', 3),
        'A': ('#FBF8FF', 2),
        'F': ('#FFFFED', 1.5),
        'G': ('#FFFF00', 1),
        'K': ('#FF9833', 0.7),
        'M': ('#FF0000', 0.5)}
    _StarLuminanceMap = {
        'Ia': 7,
        'Ib': 5,
        'II': 3,
        'III': 2,
        'IV': 1,
        'V': 0}

    @staticmethod
    def _worldStarProps(world: astronomer.World) -> typing.Iterable[typing.Tuple[
            str, # Fill Colour,
            str, # Border Colour
            float]]: # Radius
        stellar = world.stellar()
        props = []
        for star in stellar.yieldStars():
            classification = star.string()
            if classification == 'D':
                props.append((common.HtmlColours.White, common.HtmlColours.Black, 0.3))
            elif classification == 'NS' or classification == 'PSR' or classification == 'BH':
                props.append((common.HtmlColours.Black, common.HtmlColours.White, 0.8))
            elif classification == 'BD':
                props.append((common.HtmlColours.Brown, common.HtmlColours.Black, 0.3))
            else:
                colour, radius = RenderContext._StarPropsMap.get(
                    star.code(element=astronomer.Star.Element.SpectralClass),
                    (None, None))
                if colour:
                    luminance = star.code(element=astronomer.Star.Element.LuminosityClass)
                    if luminance == 'VII':
                        # The second survey format spec says that some data uses VII to indicate
                        # a white dwarf (i.e. classification D).
                        # https://travellermap.com/doc/secondsurvey
                        props.append((common.HtmlColours.White, common.HtmlColours.Black, 0.3))
                    else:
                        luminance = RenderContext._StarLuminanceMap.get(luminance, 0)
                        props.append((colour, common.HtmlColours.Black, radius + luminance))

        props.sort(key=lambda p: p[2], reverse=True)
        return props

    _StarOffsetX = [
        0.0,
        math.cos(math.pi * 1 / 3), math.cos(math.pi * 2 / 3), math.cos(math.pi * 3 / 3),
        math.cos(math.pi * 4 / 3), math.cos(math.pi * 5 / 3), math.cos(math.pi * 6 / 3)]
    _StarOffsetY = [
        0.0,
        math.sin(math.pi * 1 / 3), math.sin(math.pi * 2 / 3), math.sin(math.pi * 3 / 3),
        math.sin(math.pi * 4 / 3), math.sin(math.pi * 5 / 3), math.sin(math.pi * 6 / 3)]

    @staticmethod
    def _starOffset(index: int) -> cartographer.PointF:
        if index >= len(RenderContext._StarOffsetX):
            index = (index % (len(RenderContext._StarOffsetX) - 1)) + 1
        return cartographer.PointF(RenderContext._StarOffsetX[index], RenderContext._StarOffsetY[index])

    @staticmethod
    def _offsetRouteSegment(startPoint: cartographer.PointF, endPoint: cartographer.PointF, offset: float) -> None:
        dx = (endPoint.x() - startPoint.x()) * astronomer.ParsecScaleX
        dy = (endPoint.y() - startPoint.y()) * astronomer.ParsecScaleY
        length = math.sqrt(dx * dx + dy * dy)
        if not length:
            return # No offset
        ddx = (dx * offset / length) / astronomer.ParsecScaleX
        ddy = (dy * offset / length) / astronomer.ParsecScaleY
        startPoint.setX(startPoint.x() + ddx)
        startPoint.setY(startPoint.y() + ddy)
        endPoint.setX(endPoint.x() - ddx)
        endPoint.setY(endPoint.y() - ddy)

    @staticmethod
    def _hexToCenter(hex: astronomer.HexPosition) -> cartographer.PointF:
        centerX, centerY = hex.worldCenter()
        return cartographer.PointF(x=centerX, y=centerY)
