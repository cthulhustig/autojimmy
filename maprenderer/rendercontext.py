import common
import enum
import logging
import maprenderer
import math
import traveller
import travellermap
import typing

class RenderContext(object):
    class LayerAction(object):
        def __init__(
                self,
                id: maprenderer.LayerId,
                action: typing.Callable[[], typing.NoReturn]
                ) -> None:
            self.id = id
            self.action = action

    class BorderLayer(enum.Enum):
        Fill = 0
        Shade = 1
        Stroke = 2
        Regions = 3

    class WorldLayer(enum.Enum):
        Background = 0
        Foreground = 1
        Overlay = 2

    _MinScale = 0.0078125; # Math.Pow(2, -7)
    _MaxScale = 1024; # Math.Pow(2, 10)

    _PseudoRandomStarsChunkSize = 256
    _PseudoRandomStarsMaxPerChunk = 400

    _GridCacheCapacity = 50
    _ParsecGridSlop = 1

    def __init__(
            self,
            graphics: maprenderer.AbstractGraphics,
            absoluteCenterX: float,
            absoluteCenterY: float,
            scale: float,
            outputPixelX: int,
            outputPixelY: int,
            style: travellermap.Style,
            options: maprenderer.MapOptions,
            imageCache: maprenderer.ImageCache,
            vectorCache: maprenderer.VectorObjectCache,
            mapLabelCache: maprenderer.MapLabelCache,
            worldLabelCache: maprenderer.WorldLabelCache,
            styleCache: maprenderer.DefaultStyleCache
            ) -> None:
        self._graphics = graphics
        self._absoluteCenterX = absoluteCenterX
        self._absoluteCenterY = absoluteCenterY
        self._scale = common.clamp(scale, RenderContext._MinScale, RenderContext._MaxScale)
        self._outputPixelX = outputPixelX
        self._outputPixelY = outputPixelY
        self._options = options
        self._styleSheet = maprenderer.StyleSheet(
            scale=self._scale,
            options=self._options,
            style=style,
            graphics=self._graphics)
        self._imageCache = imageCache
        self._vectorCache = vectorCache
        self._mapLabelCache = mapLabelCache
        self._worldLabelCache = worldLabelCache
        self._styleCache = styleCache
        self._clipCache = maprenderer.ClipPathCache(
            graphics=self._graphics)
        self._sectorCache = maprenderer.SectorCache(
            graphics=self._graphics,
            styleCache=self._styleCache)
        self._worldCache = maprenderer.WorldCache(
            graphics=self._graphics,
            imageCache=self._imageCache)
        self._gridCache = maprenderer.GridCache(
            graphics=self._graphics,
            capacity=RenderContext._GridCacheCapacity)
        self._starfieldCache = maprenderer.StarfieldCache(
            graphics=self._graphics)
        self._selector = maprenderer.RectSelector(
            graphics=self._graphics)
        self._absoluteViewRect = None
        self._imageSpaceToWorldSpace = None
        self._worldSpaceToImageSpace = None

        self._hexOutlinePath = self._graphics.createPath(
            points=[
                maprenderer.AbstractPointF(-0.5 + travellermap.HexWidthOffset, -0.5),
                maprenderer.AbstractPointF( 0.5 - travellermap.HexWidthOffset, -0.5),
                maprenderer.AbstractPointF( 0.5 + travellermap.HexWidthOffset, 0),
                maprenderer.AbstractPointF( 0.5 - travellermap.HexWidthOffset, 0.5),
                maprenderer.AbstractPointF(-0.5 + travellermap.HexWidthOffset, 0.5),
                maprenderer.AbstractPointF(-0.5 - travellermap.HexWidthOffset, 0),
                maprenderer.AbstractPointF(-0.5 + travellermap.HexWidthOffset, -0.5)],
            types=[
                maprenderer.PathPointType.Start,
                maprenderer.PathPointType.Line,
                maprenderer.PathPointType.Line,
                maprenderer.PathPointType.Line,
                maprenderer.PathPointType.Line,
                maprenderer.PathPointType.Line,
                maprenderer.PathPointType.Line | maprenderer.PathPointType.CloseSubpath],
            closed=True)

        # Chosen to match T5 pp.416
        self._galaxyImageRect = self._graphics.createRectangle(-18257, -26234, 36551, 32462)
        self._riftImageRect = self._graphics.createRectangle(-1374, -827, 2769, 1754)

        self._parsecGrid: typing.Optional[maprenderer.AbstractPointList] = None

        self._createLayers()
        self._updateView()

    def setView(
            self,
            absoluteCenterX: float,
            absoluteCenterY: float,
            scale: float,
            outputPixelX: int,
            outputPixelY: int,
            ) -> None:
        scale = common.clamp(scale, RenderContext._MinScale, RenderContext._MaxScale)

        self._absoluteCenterX = absoluteCenterX
        self._absoluteCenterY = absoluteCenterY
        self._scale = scale
        self._outputPixelX = outputPixelX
        self._outputPixelY = outputPixelY

        self._styleSheet.scale = self._scale

        self._updateView()

    def setStyle(
            self,
            style: travellermap.Style
            ) -> None:
        self._styleSheet.style = style

    def setOptions(
            self,
            options: maprenderer.MapOptions
            ) -> None:
        self._styleSheet.options = options

    def render(self) -> None:
        #mapX, mapY = travellermap.absoluteSpaceToMapSpace((self._absoluteCenterX, self._absoluteCenterY))
        #logScale = travellermap.linearScaleToLogScale(self._scale)
        #print(f'Center {self._absoluteCenterX} {self._absoluteCenterY}')
        #print(f'Scale linear={self._scale} log={logScale}')
        #print(f'{mapX}!{mapY}!{logScale}')

        with self._graphics.save():
            # Overall, rendering is all in world-space; individual steps may transform back
            # to image-space as needed.
            self._graphics.multiplyTransform(self._imageSpaceToWorldSpace)

            for layer in self._layers:
                #with common.DebugTimer(string=str(layer.action)):
                if True:
                    layer.action()

    def _createLayers(self) -> None:
        self._layers: typing.List[RenderContext.LayerAction] = [
            RenderContext.LayerAction(maprenderer.LayerId.Background_Solid, self._drawBackground),

            RenderContext.LayerAction(maprenderer.LayerId.Background_NebulaTexture, self._drawNebulaBackground),
            RenderContext.LayerAction(maprenderer.LayerId.Background_Galaxy, self._drawGalaxyBackground),

            RenderContext.LayerAction(maprenderer.LayerId.Background_PseudoRandomStars, self._drawPseudoRandomStars),
            RenderContext.LayerAction(maprenderer.LayerId.Background_Rifts, self._drawRifts),

            #------------------------------------------------------------
            # Foreground
            #------------------------------------------------------------
            RenderContext.LayerAction(maprenderer.LayerId.Macro_Borders, self._drawMacroBorders),
            RenderContext.LayerAction(maprenderer.LayerId.Macro_Routes, self._drawMacroRoutes),

            RenderContext.LayerAction(maprenderer.LayerId.Grid_Sector, self._drawSectorGrid),
            RenderContext.LayerAction(maprenderer.LayerId.Grid_Subsector, self._drawSubsectorGrid),
            RenderContext.LayerAction(maprenderer.LayerId.Grid_Parsec, self._drawParsecGrid),

            RenderContext.LayerAction(maprenderer.LayerId.Names_Subsector, self._drawSubsectorNames),

            RenderContext.LayerAction(maprenderer.LayerId.Micro_BordersStroke, self._drawMicroBorders),
            RenderContext.LayerAction(maprenderer.LayerId.Micro_Routes, self._drawMicroRoutes),
            RenderContext.LayerAction(maprenderer.LayerId.Micro_BorderExplicitLabels, self._drawMicroLabels),

            RenderContext.LayerAction(maprenderer.LayerId.Names_Sector, self._drawSectorNames),
            RenderContext.LayerAction(maprenderer.LayerId.Macro_GovernmentRiftRouteNames, self._drawMacroNames),
            RenderContext.LayerAction(maprenderer.LayerId.Macro_CapitalsAndHomeWorlds, self._drawCapitalsAndHomeWorlds),
            RenderContext.LayerAction(maprenderer.LayerId.Mega_GalaxyScaleLabels, self._drawMegaLabels),

            RenderContext.LayerAction(maprenderer.LayerId.Worlds_Background, self._drawWorldsBackground),

            RenderContext.LayerAction(maprenderer.LayerId.Worlds_Foreground, self._drawWorldsForeground),

            RenderContext.LayerAction(maprenderer.LayerId.Worlds_Overlays, self._drawWorldsOverlay),

            #------------------------------------------------------------
            # Overlays
            #------------------------------------------------------------
            RenderContext.LayerAction(maprenderer.LayerId.Overlay_DroyneChirperWorlds, self._drawDroyneOverlay),
            RenderContext.LayerAction(maprenderer.LayerId.Overlay_MinorHomeworlds, self._drawMinorHomeworldOverlay),
            RenderContext.LayerAction(maprenderer.LayerId.Overlay_AncientsWorlds, self._drawAncientWorldsOverlay),
            RenderContext.LayerAction(maprenderer.LayerId.Overlay_ReviewStatus, self._drawSectorReviewStatusOverlay),
        ]

        self._layers.sort(key=lambda l: self._styleSheet.layerOrder[l.id])

    def _updateView(self):
        absoluteWidth = self._outputPixelX / (self._scale * travellermap.ParsecScaleX)
        absoluteHeight = self._outputPixelY / (self._scale * travellermap.ParsecScaleY)
        viewAreaChanged = (self._absoluteViewRect is None) or \
            (absoluteWidth != self._absoluteViewRect.width()) or \
            (absoluteHeight != self._absoluteViewRect.height())

        self._absoluteViewRect = self._graphics.createRectangle(
            x=self._absoluteCenterX - (absoluteWidth / 2),
            y=self._absoluteCenterY - (absoluteHeight / 2),
            width=absoluteWidth,
            height=absoluteHeight)

        # This needs to be done after _absoluteViewRect is calculated
        self._selector.setRect(self._absoluteViewRect)

        m = self._graphics.createIdentityMatrix()
        m.translatePrepend(
            dx=-self._absoluteViewRect.left() * self._scale * travellermap.ParsecScaleX,
            dy=-self._absoluteViewRect.top() * self._scale * travellermap.ParsecScaleY)
        m.scalePrepend(
            sx=self._scale * travellermap.ParsecScaleX,
            sy=self._scale * travellermap.ParsecScaleY)
        self._imageSpaceToWorldSpace = self._graphics.copyMatrix(other=m)
        m.invert()
        self._worldSpaceToImageSpace = self._graphics.copyMatrix(other=m)

        if self._styleSheet.parsecGrid.visible:
            if viewAreaChanged or not self._parsecGrid:
                self._parsecGrid = self._gridCache.grid(
                    parsecWidth=int(math.ceil(self._absoluteViewRect.width())),
                    parsecHeight=int(math.ceil(self._absoluteViewRect.height())))
        else:
            self._parsecGrid = None

    def _drawBackground(self) -> None:
        self._graphics.setSmoothingMode(
            maprenderer.AbstractGraphics.SmoothingMode.HighSpeed)

        # NOTE: This is a comment from the original Traveller Map source code
        # HACK: Due to limited precisions of floats, tileRect can end up not covering
        # the full bitmap when far from the origin.
        rect = self._graphics.copyRectangle(self._absoluteViewRect)
        rect.inflate(rect.width() * 0.1, rect.height() * 0.1)
        self._graphics.drawRectangle(
            rect=rect,
            brush=self._styleSheet.backgroundBrush)

    # TODO: When zooming in and out the background doesn't stay in a consistent
    # place between zoom levels. I think traveller map technically has the same
    # issue but it's nowhere near as noticeable as it only actually renders
    # tiles at a few zoom levels then uses digital zoom in the browser to scale
    # between those levels. The result being it doesn't jump around every zoom
    # step, it still does it at some zoom levels but it's far less noticeable.
    # I suspect I could do something in this function that effectively mimics
    # this behaviour
    def _drawNebulaBackground(self) -> None:
        if not self._styleSheet.showNebulaBackground:
            return

        # Render in image-space so it scales/tiles nicely
        with self._graphics.save():
            self._graphics.multiplyTransform(self._worldSpaceToImageSpace)

            backgroundImageScale = 2.0
            nebulaImageWidth = 1024
            nebulaImageHeight = 1024
            # Scaled size of the background
            w = nebulaImageWidth * backgroundImageScale
            h = nebulaImageHeight * backgroundImageScale

            # Offset of the background, relative to the canvas
            ox = (-self._absoluteViewRect.left() * self._scale * travellermap.ParsecScaleX) % w
            oy = (-self._absoluteViewRect.top() * self._scale * travellermap.ParsecScaleY) % h
            if (ox > 0):
                ox -= w
            if (oy > 0):
                oy -= h

            # Number of copies needed to cover the canvas
            nx = 1 + int(math.floor(self._outputPixelX / w))
            ny = 1 + int(math.floor(self._outputPixelY / h))
            if (ox + nx * w < self._outputPixelX):
                nx += 1
            if (oy + ny * h < self._outputPixelY):
                ny += 1

            imageRect = self._graphics.createRectangle(x=ox, y=oy, width=w + 1, height=h + 1)
            for _ in range(nx):
                imageRect.setY(oy)
                for _ in range(ny):
                    self._graphics.drawImage(
                        self._imageCache.nebulaImage,
                        imageRect)
                    imageRect.setY(imageRect.y() + h)
                imageRect.setX(imageRect.x() + w)

    def _drawGalaxyBackground(self) -> None:
        if not self._styleSheet.showGalaxyBackground:
            return

        if self._styleSheet.deepBackgroundOpacity > 0 and \
            self._galaxyImageRect.intersectsWith(self._absoluteViewRect):
            galaxyImage = \
                self._imageCache.galaxyImageGray \
                if self._styleSheet.lightBackground else \
                self._imageCache.galaxyImage
            self._graphics.drawImageAlpha(
                self._styleSheet.deepBackgroundOpacity,
                galaxyImage,
                self._galaxyImageRect)

    # NOTE: How this is implemented differs from the Traveller Map implementation
    # as Traveller Map achieves consistent random star positioning by seeding the
    # rng by the tile origin. As the web interface always chunks the universe into
    # tiles with the same origins this means, for a given tile, the random stars
    # will always be in the same place.
    # This approach doesn't work for me as I'm not using tiles in that way. I'm
    # drawing a single tile where the origin will vary depending on where the
    # current viewport is. To achieve a similar effect I'm chunking the random
    # stars by sector. The downside of this is you always have to draw process
    # all stars for all sectors overlapped by the viewport
    def _drawPseudoRandomStars(self) -> None:
        if not self._styleSheet.pseudoRandomStars.visible:
            return

        chunkParsecs = self._starfieldCache.chunkParsecs()
        startX = math.floor(self._absoluteViewRect.left() / chunkParsecs)
        startY = math.floor(self._absoluteViewRect.top() / chunkParsecs)
        finishX = math.ceil(self._absoluteViewRect.right() / chunkParsecs)
        finishY = math.ceil(self._absoluteViewRect.bottom() / chunkParsecs)

        r, g, b, _ = travellermap.stringToColourChannels(
            self._styleSheet.pseudoRandomStars.fillBrush.color())
        color = travellermap.colourChannelsToString(
            r, g, b,
            alpha=int(255 / self._starfieldCache.intensitySteps()))
        pen = self._graphics.createPen(
            color=color,
            width=1 / self._scale) # One pixel

        self._graphics.setSmoothingMode(
            maprenderer.AbstractGraphics.SmoothingMode.HighQuality)

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
            self._riftImageRect.intersectsWith(self._absoluteViewRect):
            self._graphics.drawImageAlpha(
                alpha=self._styleSheet.riftOpacity,
                image=self._imageCache.riftImage,
                rect=self._riftImageRect)

    def _drawMacroBorders(self) -> None:
        if not self._styleSheet.macroBorders.visible:
            return

        self._graphics.setSmoothingMode(
                maprenderer.AbstractGraphics.SmoothingMode.AntiAlias)
        for vector in self._vectorCache.borders:
            if (vector.mapOptions & self._options & maprenderer.MapOptions.BordersMask) != 0:
                vector.draw(
                    graphics=self._graphics,
                    rect=self._absoluteViewRect,
                    pen=self._styleSheet.macroBorders.linePen)

    def _drawMacroRoutes(self) -> None:
        if not self._styleSheet.macroRoutes.visible:
            return

        self._graphics.setSmoothingMode(
                maprenderer.AbstractGraphics.SmoothingMode.AntiAlias)
        for vector in self._vectorCache.routes:
            if (vector.mapOptions & self._options & maprenderer.MapOptions.BordersMask) != 0:
                vector.draw(
                    graphics=self._graphics,
                    rect=self._absoluteViewRect,
                    pen=self._styleSheet.macroRoutes.linePen)

    def _drawSectorGrid(self) -> None:
        if not self._styleSheet.sectorGrid.visible:
            return

        self._graphics.setSmoothingMode(
                maprenderer.AbstractGraphics.SmoothingMode.HighSpeed)

        h = ((math.floor((self._absoluteViewRect.left()) / travellermap.SectorWidth) - 1) - travellermap.ReferenceSectorX) * \
            travellermap.SectorWidth - travellermap.ReferenceHexX
        gridSlop = 10
        while h <= (self._absoluteViewRect.right() + travellermap.SectorWidth):
            with self._graphics.save():
                self._graphics.translateTransform(dx=h, dy=0)
                self._graphics.scaleTransform(
                    scaleX=1 / travellermap.ParsecScaleX,
                    scaleY=1 / travellermap.ParsecScaleY)
                self._graphics.drawLine(
                    pt1=maprenderer.AbstractPointF(0, self._absoluteViewRect.top() - gridSlop),
                    pt2=maprenderer.AbstractPointF(0, self._absoluteViewRect.bottom() + gridSlop),
                    pen=self._styleSheet.sectorGrid.linePen)
            h += travellermap.SectorWidth

        v = ((math.floor((self._absoluteViewRect.top()) / travellermap.SectorHeight) - 1) - travellermap.ReferenceSectorY) * \
            travellermap.SectorHeight - travellermap.ReferenceHexY
        while v <= (self._absoluteViewRect.bottom() + travellermap.SectorHeight):
            self._graphics.drawLine(
                pt1=maprenderer.AbstractPointF(self._absoluteViewRect.left() - gridSlop, v),
                pt2=maprenderer.AbstractPointF(self._absoluteViewRect.right() + gridSlop, v),
                pen=self._styleSheet.sectorGrid.linePen)
            v += travellermap.SectorHeight

    # TODO: This looks horrible when you pan about if the lines aren't solid
    # (i.e. with Candy) as the dashes/dots don't stay in the same relative
    # place. I __think__ a fix might be to overdraw and always have the start
    # of the line aligned with a subsector boundary. The same issue applies
    # to the sector grid. I'm not seeing the same issue with dashed/dotted
    # region outlines so there might be worth looking at why
    def _drawSubsectorGrid(self) -> None:
        if not self._styleSheet.subsectorGrid.visible:
            return

        self._graphics.setSmoothingMode(
                maprenderer.AbstractGraphics.SmoothingMode.HighSpeed)

        hmin = int(math.floor(self._absoluteViewRect.left() / travellermap.SubsectorWidth) - 1 -
                   travellermap.ReferenceSectorX)
        hmax = int(math.ceil((self._absoluteViewRect.right() + travellermap.SubsectorWidth +
                              travellermap.ReferenceHexX) / travellermap.SubsectorWidth))
        gridSlop = 10
        for hi in range(hmin, hmax + 1):
            if (hi % 4) == 0:
                continue
            h = hi * travellermap.SubsectorWidth - travellermap.ReferenceHexX
            self._graphics.drawLine(
                pt1=maprenderer.AbstractPointF(h, self._absoluteViewRect.top() - gridSlop),
                pt2=maprenderer.AbstractPointF(h, self._absoluteViewRect.bottom() + gridSlop),
                pen=self._styleSheet.subsectorGrid.linePen)
            with self._graphics.save():
                self._graphics.translateTransform(dx=h, dy=0)
                self._graphics.scaleTransform(
                    scaleX=1 / travellermap.ParsecScaleX,
                    scaleY=1 / travellermap.ParsecScaleY)
                self._graphics.drawLine(
                    pt1=maprenderer.AbstractPointF(0, self._absoluteViewRect.top() - gridSlop),
                    pt2=maprenderer.AbstractPointF(0, self._absoluteViewRect.bottom() + gridSlop),
                    pen=self._styleSheet.subsectorGrid.linePen)

        vmin = int(math.floor(self._absoluteViewRect.top() / travellermap.SubsectorHeight) - 1 -
                   travellermap.ReferenceSectorY)
        vmax = int(math.ceil((self._absoluteViewRect.bottom() + travellermap.SubsectorHeight +
                              travellermap.ReferenceHexY) / travellermap.SubsectorHeight))
        for vi in range(vmin, vmax + 1):
            if (vi % 4) == 0:
                continue
            v = vi * travellermap.SubsectorHeight - travellermap.ReferenceHexY
            self._graphics.drawLine(
                pt1=maprenderer.AbstractPointF(self._absoluteViewRect.left() - gridSlop, v),
                pt2=maprenderer.AbstractPointF(self._absoluteViewRect.right() + gridSlop, v),
                pen=self._styleSheet.subsectorGrid.linePen)

    def _drawParsecGrid(self) -> None:
        if not self._styleSheet.parsecGrid.visible:
            return

        self._graphics.setSmoothingMode(
            maprenderer.AbstractGraphics.SmoothingMode.HighQuality)

        if self._parsecGrid:
            with self._graphics.save():
                offsetX = math.floor(self._absoluteViewRect.left())
                offsetY = math.floor(self._absoluteViewRect.top()) + (0.5 if offsetX % 2 else 0)
                self._graphics.translateTransform(dx=offsetX, dy=offsetY)
                self._graphics.drawLines(
                    points=self._parsecGrid,
                    pen=self._styleSheet.parsecGrid.linePen)

        if self._styleSheet.numberAllHexes and (self._styleSheet.worldDetails & maprenderer.WorldDetails.Hex) != 0:
            hx = int(math.floor(self._absoluteViewRect.x()))
            hw = int(math.ceil(self._absoluteViewRect.width()))
            hy = int(math.floor(self._absoluteViewRect.y()))
            hh = int(math.ceil(self._absoluteViewRect.height()))
            for px in range(hx - RenderContext._ParsecGridSlop, hx + hw + RenderContext._ParsecGridSlop):
                yOffset = 0 if ((px % 2) != 0) else 0.5
                for py in range(hy - RenderContext._ParsecGridSlop, hy + hh + RenderContext._ParsecGridSlop):

                    if self._styleSheet.hexCoordinateStyle == maprenderer.HexCoordinateStyle.Subsector:
                        # TODO: Need to implement Subsector hex number. Not sure what this
                        # actually is
                        hex = 'TODO'
                    else:
                        relativePos = travellermap.absoluteSpaceToRelativeSpace((px + 1, py + 1))
                        hex = f'{relativePos[2]:02d}{relativePos[3]:02d}'

                    with self._graphics.save():
                        scaleX = self._styleSheet.hexContentScale / travellermap.ParsecScaleX
                        scaleY = self._styleSheet.hexContentScale / travellermap.ParsecScaleY
                        self._graphics.scaleTransform(
                            scaleX=scaleX,
                            scaleY=scaleY)
                        self._graphics.drawString(
                            text=hex,
                            font=self._styleSheet.hexNumber.font,
                            brush=self._styleSheet.hexNumber.textBrush,
                            x=(px + 0.5) / scaleX,
                            y=(py + yOffset) / scaleY,
                            format=maprenderer.TextAlignment.TopCenter)

    def _drawSubsectorNames(self) -> None:
        if not self._styleSheet.subsectorNames.visible:
            return

        self._graphics.setSmoothingMode(
             maprenderer.AbstractGraphics.SmoothingMode.HighQuality)

        for subsector in self._selector.subsectors():
            if subsector.isNameGenerated():
                continue

            ulHex, brHex = subsector.extent()
            left = ulHex.absoluteX() - 1
            top = ulHex.absoluteY() - 1
            right = brHex.absoluteX()
            bottom = brHex.absoluteY()

            self._drawLabel(
                text=subsector.name(),
                center=maprenderer.AbstractPointF(
                    x=(left + right) / 2,
                    y=(top + bottom) / 2),
                font=self._styleSheet.subsectorNames.font,
                brush=self._styleSheet.subsectorNames.textBrush,
                labelStyle=self._styleSheet.subsectorNames.textStyle)

    def _drawMicroBorders(self) -> None:
        if not self._styleSheet.microBorders.visible:
            return

        self._graphics.setSmoothingMode(
                maprenderer.AbstractGraphics.SmoothingMode.HighQuality)

        pathType = \
            maprenderer.ClipPathCache.PathType.Square \
            if self._styleSheet.microBorderStyle == maprenderer.MicroBorderStyle.Square else \
            maprenderer.ClipPathCache.PathType.Hex

        penWidth = self._styleSheet.microBorders.linePen.width()
        # HACK: Due to the fact clipping to the outline being drawn
        # doesn't work with Qt (see HACK below), it means outlines
        # appear twice as thick as they do in Traveller Map. This
        # scales the width to account for this
        penWidth *= 0.5
        pen = self._graphics.createPen(width=penWidth)
        brush = None
        if self._styleSheet.fillMicroBorders:
            brush = self._graphics.createBrush()

        shadePen = None
        if self._styleSheet.shadeMicroBorders:
            # Shade is a wide/solid outline under the main outline.
            shadePen = self._graphics.createPen(
                width=penWidth * 2.5,
                style=maprenderer.LineStyle.Solid)

        for sector in self._selector.sectors():
            clip = self._clipCache.sectorClipPath(
                sectorX=sector.x(),
                sectorY=sector.y(),
                pathType=pathType)
            if not self._absoluteViewRect.intersectsWith(clip.bounds()):
                continue

            with self._graphics.save():
                self._graphics.intersectClipPath(path=clip)

                regions = self._sectorCache.regionPaths(x=sector.x(), y=sector.y())
                if regions:
                    for outline in regions:
                        if not self._absoluteViewRect.intersectsWith(outline.bounds()):
                            continue # Outline isn't on screen
                        self._drawMicroBorder(
                            outline=outline,
                            brush=brush)

                borders = self._sectorCache.borderPaths(x=sector.x(), y=sector.y())
                if borders:
                    for outline in borders:
                        if not self._absoluteViewRect.intersectsWith(outline.bounds()):
                            continue # Outline isn't on screen
                        self._drawMicroBorder(
                            outline=outline,
                            brush=brush,
                            pen=pen,
                            shadePen=shadePen)

    def _drawMicroRoutes(self) -> None:
        if not self._styleSheet.microRoutes.visible:
            return

        with self._graphics.save():
            self._graphics.setSmoothingMode(
                maprenderer.AbstractGraphics.SmoothingMode.AntiAlias)

            pen = self._graphics.createPen()
            baseWidth = self._styleSheet.microRoutes.linePen.width()

            for sector in self._selector.sectors():
                for route in self._sectorCache.routeLines(x=sector.x(), y=sector.y()):
                    routeColor = route.color()
                    routeWidth = route.width()
                    routeStyle = self._styleSheet.overrideLineStyle
                    if not routeStyle:
                        if route.style() is traveller.Route.Style.Solid:
                            routeStyle = maprenderer.LineStyle.Solid
                        elif route.style() is traveller.Route.Style.Dashed:
                            routeStyle = maprenderer.LineStyle.Dash
                        elif route.style() is traveller.Route.Style.Dotted:
                            routeStyle = maprenderer.LineStyle.Dot

                    if not routeWidth or not routeColor or not routeStyle:
                        precedence = [route.allegiance(), route.type(), 'Im']
                        for key in precedence:
                            defaultColor, defaultStyle, defaultWidth = self._styleCache.defaultRouteStyle(key)
                            if not routeColor:
                                routeColor = defaultColor
                            if not routeStyle:
                                routeStyle = defaultStyle
                            if not routeWidth:
                                routeWidth = defaultWidth

                    # In grayscale, convert default color and style to non-default style
                    if self._styleSheet.grayscale and (not routeColor) and (not routeStyle):
                        routeStyle = maprenderer.LineStyle.Dash

                    if not routeWidth:
                        routeWidth = 1.0
                    if not routeColor:
                        routeColor = self._styleSheet.microRoutes.linePen.color()
                    if not routeStyle:
                        routeStyle = maprenderer.LineStyle.Solid

                    # Ensure color is visible
                    # TODO: Handle making colour visible, should be
                    # styles.grayscale || !ColorUtil.NoticeableDifference(routeColor.Value, styles.backgroundColor)
                    if self._styleSheet.grayscale:
                        routeColor = self._styleSheet.microRoutes.linePen.color() # default

                    pen.setColor(routeColor)
                    pen.setWidth(routeWidth * baseWidth)
                    pen.setStyle(routeStyle)

                    self._graphics.drawLines(
                        points=route.points(),
                        pen=pen)

    _LabelDefaultColor = travellermap.MapColours.TravellerAmber
    def _drawMicroLabels(self) -> None:
        if not self._styleSheet.showMicroNames:
            return

        with self._graphics.save():
            self._graphics.setSmoothingMode(
                maprenderer.AbstractGraphics.SmoothingMode.AntiAlias)

            brush = self._graphics.createBrush()
            for sector in self._selector.sectors():
                brush.copyFrom(self._styleSheet.microBorders.textBrush)

                # TODO: I suspect I'm not drawing text for regions
                for border in sector.borders():
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

                for region in sector.regions():
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

                for label in sector.labels():
                    text = label.text()

                    labelPos = RenderContext._hexToCenter(label.hex())
                    # NOTE: This todo came in with the traveller map code
                    # TODO: Adopt some of the tweaks from .MSEC
                    if label.offsetX():
                        labelPos.setX(labelPos.x() + (label.offsetX() * 0.7))
                    if label.offsetY():
                        labelPos.setY(labelPos.y() - (label.offsetY() * 0.7))

                    if label.size() is traveller.Label.Size.Small:
                        font = self._styleSheet.microBorders.smallFont
                    elif label.size() is traveller.Label.Size.Large:
                        font = self._styleSheet.microBorders.largeFont
                    else:
                        font = self._styleSheet.microBorders.font

                    # TODO: Handle similar colours, should have this in it somewhere
                    # ColorUtil.NoticeableDifference(label.Color.Value, styles.backgroundColor) &&
                    useLabelColor = \
                        not self._styleSheet.grayscale and \
                        label.colour() and \
                        (label.colour() != RenderContext._LabelDefaultColor)
                    if useLabelColor:
                        brush.setColor(label.colour())

                    self._drawLabel(
                        text=text,
                        center=labelPos,
                        font=font,
                        brush=brush if useLabelColor else self._styleSheet.microBorders.textBrush,
                        labelStyle=self._styleSheet.microBorders.textStyle)

    def _drawSectorNames(self) -> None:
        if not (self._styleSheet.showSomeSectorNames or self._styleSheet.showAllSectorNames):
            return

        self._graphics.setSmoothingMode(
                maprenderer.AbstractGraphics.SmoothingMode.HighQuality)

        for sector in self._selector.sectors():
            if not self._styleSheet.showAllSectorNames and not sector.selected():
                continue

            # TODO: Traveller Map would use the sector label first and only
            # fall back to the name if if there was no label. I need to work out
            # where that label is being loaded from
            name = sector.name()

            centerX, centerY = travellermap.relativeSpaceToAbsoluteSpace((
                sector.x(),
                sector.y(),
                int(travellermap.SectorWidth // 2),
                int(travellermap.SectorHeight // 2)))

            self._drawLabel(
                text=name,
                center=maprenderer.AbstractPointF(x=centerX, y=centerY),
                font=self._styleSheet.sectorName.font,
                brush=self._styleSheet.sectorName.textBrush,
                labelStyle=self._styleSheet.sectorName.textStyle)

    def _drawMacroNames(self) -> None:
        if  not self._styleSheet.macroNames.visible:
            return

        self._graphics.setSmoothingMode(
                maprenderer.AbstractGraphics.SmoothingMode.HighQuality)

        for vec in self._vectorCache.borders:
            if (vec.mapOptions & self._options & maprenderer.MapOptions.NamesMask) == 0:
                continue
            major = (vec.mapOptions & maprenderer.MapOptions.NamesMajor) != 0
            labelStyle = maprenderer.LabelStyle(uppercase=major)
            font = \
                self._styleSheet.macroNames.font \
                if major else \
                self._styleSheet.macroNames.smallFont
            brush = \
                self._styleSheet.macroNames.textBrush \
                if major else \
                self._styleSheet.macroNames.textHighlightBrush
            vec.drawName(
                graphics=self._graphics,
                rect=self._absoluteViewRect,
                font=font,
                textBrush=brush,
                labelStyle=labelStyle)

        for vec in self._vectorCache.rifts:
            major = (vec.mapOptions & maprenderer.MapOptions.NamesMajor) != 0
            labelStyle = maprenderer.LabelStyle(rotation=35, uppercase=major)
            font = \
                self._styleSheet.macroNames.font \
                if major else \
                self._styleSheet.macroNames.smallFont
            brush = \
                self._styleSheet.macroNames.textBrush \
                if major else \
                self._styleSheet.macroNames.textHighlightBrush
            vec.drawName(
                graphics=self._graphics,
                rect=self._absoluteViewRect,
                font=font,
                textBrush=brush,
                labelStyle=labelStyle)

        if self._styleSheet.macroRoutes.visible:
            for vec in self._vectorCache.routes:
                if (vec.mapOptions & self._options & maprenderer.MapOptions.NamesMask) == 0:
                    continue
                major = (vec.mapOptions & maprenderer.MapOptions.NamesMajor) != 0
                labelStyle = maprenderer.LabelStyle(uppercase=major)
                font = \
                    self._styleSheet.macroNames.font \
                    if major else \
                    self._styleSheet.macroNames.smallFont
                brush = \
                    self._styleSheet.macroRoutes.textBrush \
                    if major else \
                    self._styleSheet.macroRoutes.textHighlightBrush
                vec.drawName(
                    graphics=self._graphics,
                    rect=self._absoluteViewRect,
                    font=font,
                    textBrush=brush,
                    labelStyle=labelStyle)

        if (self._options & maprenderer.MapOptions.NamesMinor) != 0:
            for label in self._mapLabelCache.minorLabels:
                font = self._styleSheet.macroNames.smallFont if label.minor else self._styleSheet.macroNames.mediumFont
                brush = \
                    self._styleSheet.macroRoutes.textBrush \
                    if label.minor else \
                    self._styleSheet.macroRoutes.textHighlightBrush
                with self._graphics.save():
                    self._graphics.scaleTransform(
                        scaleX=1.0 / travellermap.ParsecScaleX,
                        scaleY=1.0 / travellermap.ParsecScaleY)
                    maprenderer.drawStringHelper(
                        graphics=self._graphics,
                        text=label.text,
                        font=font,
                        brush=brush,
                        x=label.position.x() * travellermap.ParsecScaleX,
                        y=label.position.y() * travellermap.ParsecScaleY)

    def _drawCapitalsAndHomeWorlds(self) -> None:
        if (not self._styleSheet.capitals.visible) or \
            ((self._options & maprenderer.MapOptions.WorldsMask) == 0):
            return

        with self._graphics.save():
            self._graphics.setSmoothingMode(
                maprenderer.AbstractGraphics.SmoothingMode.HighQuality)
            for worldLabel in self._worldLabelCache.labels:
                if (worldLabel.mapOptions & self._options) != 0:
                    worldLabel.paint(
                        graphics=self._graphics,
                        dotBrush=self._styleSheet.capitals.fillBrush,
                        labelBrush=self._styleSheet.capitals.textBrush,
                        labelFont=self._styleSheet.macroNames.smallFont)

    def _drawMegaLabels(self) -> None:
        if not self._styleSheet.megaNames.visible:
            return

        self._graphics.setSmoothingMode(
                maprenderer.AbstractGraphics.SmoothingMode.HighQuality)
        for label in self._mapLabelCache.megaLabels:
            with self._graphics.save():
                font = self._styleSheet.megaNames.smallFont if label.minor else self._styleSheet.megaNames.font
                self._graphics.scaleTransform(
                    scaleX=1.0 / travellermap.ParsecScaleX,
                    scaleY=1.0 / travellermap.ParsecScaleY)
                maprenderer.drawStringHelper(
                    graphics=self._graphics,
                    text=label.text,
                    font=font,
                    brush=self._styleSheet.megaNames.textBrush,
                    x=label.position.x() * travellermap.ParsecScaleX,
                    y=label.position.y() * travellermap.ParsecScaleY)

    def _drawWorldsBackground(self) -> None:
        if not self._styleSheet.worlds.visible or self._styleSheet.showStellarOverlay \
            or not self._styleSheet.worldDetails or self._styleSheet.worldDetails is maprenderer.WorldDetails.NoDetails:
            return

        renderAllNames = (self._styleSheet.worldDetails & maprenderer.WorldDetails.AllNames) != 0
        renderKeyNames = (self._styleSheet.worldDetails & maprenderer.WorldDetails.KeyNames) != 0
        renderZone = (self._styleSheet.worldDetails & maprenderer.WorldDetails.Zone) != 0
        renderHex = (self._styleSheet.worldDetails & maprenderer.WorldDetails.Hex) != 0
        renderSubsector = self._styleSheet.hexContentScale is maprenderer.HexCoordinateStyle.Subsector
        renderType = (self._styleSheet.worldDetails & maprenderer.WorldDetails.Type) != 0

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
                maprenderer.AbstractGraphics.SmoothingMode.AntiAlias)

            scaleX = self._styleSheet.hexContentScale / travellermap.ParsecScaleX
            scaleY = self._styleSheet.hexContentScale / travellermap.ParsecScaleY
            self._graphics.scaleTransform(
                scaleX=scaleX,
                scaleY=scaleY)

            rect = self._graphics.createRectangle()
            for world in worlds:
                worldInfo = self._worldCache.getWorldInfo(world=world)

                renderName = False
                if renderAllNames or renderKeyNames:
                    renderName = renderAllNames or worldInfo.isCapital or worldInfo.isHiPop
                renderUWP = (self._styleSheet.worldDetails & maprenderer.WorldDetails.Uwp) != 0

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
                                            scaleX=0.95 * travellermap.ParsecScaleX,
                                            scaleY=0.95 * travellermap.ParsecScaleY)
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
                            # TODO: Handle subsector hex whatever that is
                            hex = \
                                'TODO' \
                                if renderSubsector else \
                                worldInfo.hexString

                            self._graphics.drawString(
                                text=hex,
                                font=self._styleSheet.hexNumber.font,
                                brush=self._styleSheet.hexNumber.textBrush,
                                x=self._styleSheet.hexNumber.position.x(),
                                y=self._styleSheet.hexNumber.position.y(),
                                format=maprenderer.TextAlignment.TopCenter)
                    else: # styles.useWorldImages
                        # "Eye-Candy" style
                        # TODO: This needs work
                        # - World images aren't being drawn at quite the right location which
                        #   means red/amber zone markers don't line up
                        # - World images aren't being drawn for some worlds at some zoom levels
                        #   an example would be the Breda subsector
                        # - At high zooms (just before it turns to the dot map) as you pan
                        #   about the red/amber zone marker sometimes aren't shown. To replicate
                        #   center on Reference then pan left a bit
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
                            scaleX = 1.5 if worldInfo.worldSize <= 0 else 1
                            scaleY = 1.0 if worldInfo.worldSize <= 0 else 1
                            rect.setRect(
                                x=-worldInfo.imageRadius * scaleX,
                                y=-worldInfo.imageRadius * scaleY,
                                width=worldInfo.imageRadius * 2 * scaleX,
                                height=worldInfo.imageRadius * 2 * scaleY)
                            self._graphics.drawImage(
                                image=worldInfo.worldImage,
                                rect=rect)

    def _drawWorldsForeground(self) -> None:
        if not self._styleSheet.worlds.visible or self._styleSheet.showStellarOverlay:
            return

        if not self._styleSheet.worldDetails or self._styleSheet.worldDetails is maprenderer.WorldDetails.NoDetails:
            # Render dot map
            with self._graphics.save():
                self._graphics.setSmoothingMode(
                    maprenderer.AbstractGraphics.SmoothingMode.AntiAlias)

                # Scale by the parsec scale so we are rendering in a coordinate
                # space that has the same scaling on the x & y axis (I think the
                # term is isotropic scaling). This is works on the assumption
                # that the world points to be rendered have already been
                # transformed into this coordinate space. It's necessary because
                # (for speed) the worlds are being rendered as points with the
                # pen width giving them their size. If this was done in absolute
                # coordinate space (where x & y don't scale the same) then the
                # point would be drawn as an oval
                self._graphics.scaleTransform(
                    scaleX=self._styleSheet.hexContentScale / travellermap.ParsecScaleX,
                    scaleY=self._styleSheet.hexContentScale / travellermap.ParsecScaleY)

                pen = self._graphics.createPen(
                    color=self._styleSheet.worlds.textBrush.color(),
                    width=self._styleSheet.discRadius * self._styleSheet.hexContentScale * 2,
                    style=maprenderer.LineStyle.Solid,
                    tip=maprenderer.PenTip.Round) # Rounded end cap so a circle is drawn

                for sector in self._selector.sectors(tight=True):
                    worlds = self._sectorCache.isotropicWorldPoints(
                        x=sector.x(),
                        y=sector.y())
                    if worlds:
                        self._graphics.drawPoints(points=worlds, pen=pen)

            return # Nothing more to do

        worlds = self._selector.worlds()
        self._worldCache.ensureCapacity(len(worlds))

        renderAllNames = (self._styleSheet.worldDetails & maprenderer.WorldDetails.AllNames) != 0
        renderKeyNames = (self._styleSheet.worldDetails & maprenderer.WorldDetails.KeyNames) != 0
        renderUWP = (self._styleSheet.worldDetails & maprenderer.WorldDetails.Uwp) != 0
        renderGasGiants = (self._styleSheet.worldDetails & maprenderer.WorldDetails.GasGiant) != 0
        renderStarport = (self._styleSheet.worldDetails & maprenderer.WorldDetails.Starport) != 0
        renderBases = (self._styleSheet.worldDetails & maprenderer.WorldDetails.Bases) != 0
        renderAsteroids = (self._styleSheet.worldDetails & maprenderer.WorldDetails.Asteroids) != 0
        renderHighlight = (self._styleSheet.worldDetails & maprenderer.WorldDetails.Highlight) != 0
        renderAllegiances = (self._styleSheet.worldDetails & maprenderer.WorldDetails.Allegiance) != 0
        renderZone = (self._styleSheet.worldDetails & maprenderer.WorldDetails.Zone) != 0
        # NOTE: WorldDetails.Type isn't checked for as (with the current implementation) it is
        # always set when the dot map isn't being rendered so it must be set now

        worldDiscRect = self._graphics.createRectangle(
            x=self._styleSheet.discPosition.x() - self._styleSheet.discRadius,
            y=self._styleSheet.discPosition.y() - self._styleSheet.discRadius,
            width=self._styleSheet.discRadius * 2,
            height=self._styleSheet.discRadius * 2)

        with self._graphics.save():
            self._graphics.setSmoothingMode(
                maprenderer.AbstractGraphics.SmoothingMode.AntiAlias)

            scaleX = self._styleSheet.hexContentScale / travellermap.ParsecScaleX
            scaleY = self._styleSheet.hexContentScale / travellermap.ParsecScaleY
            self._graphics.scaleTransform(scaleX=scaleX, scaleY=scaleY)

            for world in worlds:
                worldInfo = self._worldCache.getWorldInfo(world=world)
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
                            maprenderer.TextBackgroundStyle.NoStyle \
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

                            # NOTE: This todo came in with the traveller map code
                            # TODO: Mask off background for glyphs
                            if renderBases:
                                # Base 1
                                bottomUsed = False
                                if worldInfo.primaryBaseGlyph and worldInfo.primaryBaseGlyph.isPrintable:
                                    pt = self._styleSheet.baseTopPosition
                                    if worldInfo.primaryBaseGlyph.bias is maprenderer.Glyph.GlyphBias.Bottom and \
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
                                        glyph=maprenderer.GlyphDefs.DiamondX,
                                        brush=self._styleSheet.worlds.textBrush,
                                        position=maprenderer.AbstractPointF(
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

                        if renderAllegiances:
                            alleg = maprenderer.WorldHelper.allegianceCode(
                                world=world,
                                useLegacy=not self._styleSheet.t5AllegianceCodes,
                                ignoreDefault=True)
                            if alleg:
                                if self._styleSheet.lowerCaseAllegiance:
                                    alleg = alleg.lower()

                                self._graphics.drawString(
                                    text=alleg,
                                    font=self._styleSheet.worlds.smallFont,
                                    brush=self._styleSheet.worlds.textBrush,
                                    x=self._styleSheet.allegiancePosition.x(),
                                    y=self._styleSheet.allegiancePosition.y(),
                                    format=maprenderer.TextAlignment.Centered)
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
                                rect = self._graphics.createRectangle(
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
                            # NOTE: This todo came in with the traveller map code
                            # TODO: Scale, like the name text.
                            self._graphics.drawString(
                                text=worldInfo.uwpString,
                                font=self._styleSheet.hexNumber.font,
                                brush=self._styleSheet.worlds.textBrush,
                                x=decorationRadius,
                                y=self._styleSheet.uwp.position.y(),
                                format=maprenderer.TextAlignment.MiddleLeft)

                        if renderName and worldInfo.name:
                            name = worldInfo.name
                            if worldInfo.isHiPop or self._styleSheet.worlds.textStyle.uppercase:
                                name = worldInfo.upperName

                            with self._graphics.save():
                                textBrush = \
                                    self._styleSheet.worlds.textHighlightBrush \
                                    if worldInfo.isCapital and renderHighlight else \
                                    self._styleSheet.worlds.textBrush

                                # TODO: Could these translations be combined by manually scaling
                                # the decoration radius
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
                    worldInfo = self._worldCache.getWorldInfo(world=world)

                    with self._graphics.save():
                        self._graphics.setSmoothingMode(
                            maprenderer.AbstractGraphics.SmoothingMode.AntiAlias)

                        self._graphics.translateTransform(
                            dx=worldInfo.hexCenter.x(),
                            dy=worldInfo.hexCenter.y())
                        self._graphics.scaleTransform(
                            scaleX=self._styleSheet.hexContentScale / travellermap.ParsecScaleX,
                            scaleY=self._styleSheet.hexContentScale / travellermap.ParsecScaleY)

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
                                    radius=2 * travellermap.ParsecScaleX)
                            elif worldInfo.isImportant:
                                self._drawOverlay(
                                    element=self._styleSheet.capitalOverlayAltA,
                                    radius=2 * travellermap.ParsecScaleX)
                            elif worldInfo.isCapital:
                                self._drawOverlay(
                                    element=self._styleSheet.capitalOverlayAltB,
                                    radius=2 * travellermap.ParsecScaleX)
            finally:
                self._selector.setWorldSlop(oldSlop)

    def _drawDroyneOverlay(self) -> None:
        if not self._styleSheet.droyneWorlds.visible:
            return

        self._graphics.setSmoothingMode(
                maprenderer.AbstractGraphics.SmoothingMode.HighQuality)
        for world in self._selector.worlds():
            allegiance = world.allegiance()

            droyne = allegiance == 'Dr' or allegiance == 'NaDr' or world.hasRemark('Droy')
            chirpers = world.hasRemark('Chir')

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
                maprenderer.AbstractGraphics.SmoothingMode.HighQuality)
        for world in self._selector.worlds():
            if world.isMinorHomeworld():
                self._drawOverlayGlyph(
                    glyph=self._styleSheet.minorHomeWorlds.content,
                    font=self._styleSheet.minorHomeWorlds.font,
                    brush=self._styleSheet.minorHomeWorlds.textBrush,
                    position=world.hex())

    def _drawAncientWorldsOverlay(self) -> None:
        if not self._styleSheet.ancientsWorlds.visible:
            return

        self._graphics.setSmoothingMode(
                maprenderer.AbstractGraphics.SmoothingMode.HighQuality)
        for world in self._selector.worlds():
            if world.hasTradeCode(traveller.TradeCode.AncientsSiteWorld):
                self._drawOverlayGlyph(
                    glyph=self._styleSheet.ancientsWorlds.content,
                    font=self._styleSheet.ancientsWorlds.font,
                    brush=self._styleSheet.ancientsWorlds.textBrush,
                    position=world.hex())

    def _drawSectorReviewStatusOverlay(self) -> None:
        brush = self._graphics.createBrush()

        if self._styleSheet.dimUnofficialSectors and self._styleSheet.worlds.visible:
            brush.setColor(maprenderer.makeAlphaColor(
                alpha=128,
                color=self._styleSheet.backgroundBrush.color()))
            for sector in self._selector.sectors(tight=True):
                if not sector.hasTag('Official') and not sector.hasTag('Preserve') and not sector.hasTag('InReview'):
                    clipPath = self._clipCache.sectorClipPath(
                        sectorX=sector.x(),
                        sectorY=sector.y(),
                        pathType=maprenderer.ClipPathCache.PathType.Hex)

                    self._graphics.drawPath(
                        path=clipPath,
                        brush=brush)

        if self._styleSheet.colorCodeSectorStatus and self._styleSheet.worlds.visible:
            for sector in self._selector.sectors(tight=True):
                if sector.hasTag('Official'):
                    brush.setColor(maprenderer.makeAlphaColor(
                        alpha=128,
                        color=travellermap.MapColours.TravellerRed))
                elif sector.hasTag('InReview'):
                    brush.setColor(maprenderer.makeAlphaColor(
                        alpha=128,
                        color=travellermap.MapColours.Orange))
                elif sector.hasTag('Unreviewed'):
                    brush.setColor(maprenderer.makeAlphaColor(
                        alpha=128,
                        color=travellermap.MapColours.TravellerAmber))
                elif sector.hasTag('Apocryphal'):
                    brush.setColor(maprenderer.makeAlphaColor(
                        alpha=128,
                        color=travellermap.MapColours.Magenta))
                elif sector.hasTag('Preserve'):
                    brush.setColor(maprenderer.makeAlphaColor(
                        alpha=128,
                        color=travellermap.MapColours.TravellerGreen))
                else:
                    continue

                clipPath = self._clipCache.sectorClipPath(
                    sectorX=sector.x(),
                    sectorY=sector.y(),
                    pathType=maprenderer.ClipPathCache.PathType.Hex)

                self._graphics.drawPath(
                    path=clipPath,
                    brush=brush)

    def _drawWorldLabel(
            self,
            bkStyle: maprenderer.TextBackgroundStyle,
            bkBrush: maprenderer.AbstractBrush,
            textBrush: str,
            position: maprenderer.AbstractPointF,
            font: maprenderer.AbstractFont,
            text: str
            ) -> None:
        width, height = self._graphics.measureString(text=text, font=font)

        if bkStyle is maprenderer.TextBackgroundStyle.Rectangle:
            if not self._styleSheet.fillMicroBorders:
                # NOTE: This todo came over from traveller map
                # TODO: Implement this with a clipping region instead
                self._graphics.drawRectangle(
                    rect=self._graphics.createRectangle(
                        x=position.x() - width / 2,
                        y=position.y() - height / 2,
                        width=width,
                        height=height),
                    brush=self._styleSheet.backgroundBrush)
        elif bkStyle is maprenderer.TextBackgroundStyle.Filled:
            self._graphics.drawRectangle(
                rect=self._graphics.createRectangle(
                    x=position.x() - width / 2,
                    y=position.y() - height / 2,
                    width=width,
                    height=height),
                brush=bkBrush)
        elif bkStyle is maprenderer.TextBackgroundStyle.Outline or \
            bkStyle is maprenderer.TextBackgroundStyle.Shadow:
            # NOTE: This todo came over from traveller map
            # TODO: These scaling factors are constant for a render; compute once

            # Invert the current scaling transforms
            sx = 1.0 / self._styleSheet.hexContentScale
            sy = 1.0 / self._styleSheet.hexContentScale
            sx *= travellermap.ParsecScaleX
            sy *= travellermap.ParsecScaleY
            sx /= self._scale * travellermap.ParsecScaleX
            sy /= self._scale * travellermap.ParsecScaleY

            outlineSize = 2
            outlineSkip = 1

            outlineStart = -outlineSize if bkStyle is maprenderer.TextBackgroundStyle.Outline else 0

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
                        format=maprenderer.TextAlignment.Centered)
                    dy += outlineSkip
                dx += outlineSkip

        self._graphics.drawString(
            text=text,
            font=font,
            brush=textBrush,
            x=position.x(),
            y=position.y(),
            format=maprenderer.TextAlignment.Centered)

    def _drawStars(self, world: traveller.World) -> None:
        with self._graphics.save():
            self._graphics.setSmoothingMode(
                maprenderer.AbstractGraphics.SmoothingMode.AntiAlias)
            center = self._hexToCenter(world.hex())

            self._graphics.translateTransform(dx=center.x(), dy=center.y())
            self._graphics.scaleTransform(
                scaleX=self._styleSheet.hexContentScale / travellermap.ParsecScaleX,
                scaleY=self._styleSheet.hexContentScale / travellermap.ParsecScaleY)

            pen = self._graphics.createPen()
            pen.setStyle(maprenderer.LineStyle.Solid)
            # TODO: Not sure what this should be set to, Traveller Map uses it but never
            # explicitly sets it so must be picking up a default
            pen.setWidth(0)
            brush = self._graphics.createBrush()
            for i, (fillColour, lineColor, radius) in enumerate(RenderContext._worldStarProps(world=world)):
                brush.setColor(fillColour)
                pen.setColor(lineColor)
                offset = RenderContext._starOffset(i)
                offsetScale = 0.3
                radius *= 0.15
                self._graphics.drawEllipse(
                    rect=self._graphics.createRectangle(
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

        rect = self._graphics.createRectangle(
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
            element: maprenderer.StyleSheet.StyleElement,
            radius: float
            ) -> None:
        # Prevent "Out of memory" exception when rendering to GDI+.
        if radius < 0.001:
            return

        self._graphics.drawEllipse(
            rect=self._graphics.createRectangle(
                x=-radius,
                y=-radius, width=radius * 2,
                height=radius * 2),
            pen=element.linePen,
            brush=element.fillBrush)

    _MicroBorderFillAlpha = 64
    _MicroBorderShadeAlpha = 128
    def _drawMicroBorder(
            self,
            outline: maprenderer.SectorPath,
            brush: typing.Optional[maprenderer.AbstractBrush] = None,
            pen: typing.Optional[maprenderer.AbstractPen] = None,
            shadePen: typing.Optional[maprenderer.AbstractPen] = None
            ) -> None:
        # Clip to the path itself - this means adjacent borders don't clash
        # HACK: I've disabled this as it doesn't do what it is
        # intended when rendering with Qt so there is no point
        # wasting the time setting the new clip path. This also
        # means there is no point in saving the state
        # The intention is this should prevent anything being
        # drawn outside the exact bounds of the outline. This is
        # done due to the fact the line has a width which would
        # mean what was drawn would normally extend half the pen
        # width outside the the boundary. In Traveller Map the
        # result is when two regions are touching, you can see
        # both border colours along the edges where they touch.
        # Unfortunately it doesn't look like Qt applies the clip
        # path to the pen width so the effect doesn't work.
        # It should be noted that this clipping not working also
        # has the side effect that (if it wasn't accounted for)
        # borders would be drawn twice as wide as they are in
        # Traveller Map
        # NOTE: If I ever do figure out how to make this work
        # I think it would only need to be set if drawing the
        # outline (i.e. not when just filling)
        #with self._graphics.save():
        #    self._graphics.intersectClipPath(path=outline.path())

        color = outline.color()
        if not color:
            color = self._styleSheet.microRoutes.linePen.color()

        style = outline.style()
        if not style:
            style = maprenderer.LineStyle.Solid

        # TODO: Handle noticable colours, this should be
        # styles.grayscale || !ColorUtil.NoticeableDifference(borderColor.Value, styles.backgroundColor
        if self._styleSheet.grayscale:
            color = self._styleSheet.microBorders.linePen.color() # default

        if brush:
            try:
                brush.setColor(maprenderer.makeAlphaColor(
                    alpha=RenderContext._MicroBorderFillAlpha,
                    color=color))
            except Exception as ex:
                logging.warning('Failed to parse region colour', exc_info=ex)
                return

        if pen:
            pen.setColor(color)
            pen.setStyle(
                style
                if self._styleSheet.microBorders.linePen.style() is maprenderer.LineStyle.Solid else
                self._styleSheet.microBorders.linePen.style())

        if shadePen:
            try:
                color = maprenderer.makeAlphaColor(
                    alpha=RenderContext._MicroBorderShadeAlpha,
                    color=color)
            except Exception as ex:
                logging.warning('Failed to parse region colour', exc_info=ex)
                return
            shadePen.setColor(color)
            pen.setStyle(maprenderer.LineStyle.Solid)

        self._graphics.drawPath(
            path=outline.path(),
            pen=shadePen if shadePen else pen,
            brush=brush)

        if pen and shadePen:
            self._graphics.drawPath(
                path=outline.path(),
                pen=pen)

    _WorldDingMap = {
        '\u2666': '\x74', # U+2666 (BLACK DIAMOND SUIT)
        '\u2756': '\x76', # U+2756 (BLACK DIAMOND MINUS WHITE X)
        '\u2726': '\xAA', # U+2726 (BLACK FOUR POINTED STAR)
        '\u2605': '\xAB', # U+2605 (BLACK STAR)
        '\u2736': '\xAC'} # U+2736 (BLACK SIX POINTED STAR)
    def _drawWorldGlyph(
            self,
            glyph: maprenderer.Glyph,
            brush: maprenderer.AbstractBrush,
            position: maprenderer.AbstractPointF
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
            format=maprenderer.TextAlignment.Centered)

    def _drawOverlayGlyph(
            self,
            glyph: str,
            font: maprenderer.AbstractFont,
            brush: maprenderer.AbstractBrush,
            position: travellermap.HexPosition
            ) -> None:
        centerX, centerY = position.absoluteCenter()
        with self._graphics.save():
            self._graphics.scaleTransform(
                scaleX=1 / travellermap.ParsecScaleX,
                scaleY=1 / travellermap.ParsecScaleY)
            self._graphics.drawString(
                text=glyph,
                font=font,
                brush=brush,
                x=centerX * travellermap.ParsecScaleX,
                y=centerY * travellermap.ParsecScaleY,
                format=maprenderer.TextAlignment.Centered)

    def _drawLabel(
            self,
            text: str,
            center: maprenderer.AbstractPointF,
            font: maprenderer.AbstractFont,
            brush: maprenderer.AbstractBrush,
            labelStyle: maprenderer.LabelStyle
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
                scaleX=1.0 / travellermap.ParsecScaleX,
                scaleY=1.0 / travellermap.ParsecScaleY)

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
                    maprenderer.AbstractGraphics.SmoothingMode.AntiAlias)

            maprenderer.drawStringHelper(
                graphics=self._graphics,
                text=text,
                font=font,
                brush=brush,
                x=0, y=0)

    def _zoneStyle(
            self,
            worldInfo: maprenderer.WorldInfo
            ) -> typing.Optional[maprenderer.StyleSheet.StyleElement]:
        if worldInfo.isAmberZone:
            return self._styleSheet.amberZone
        if worldInfo.isRedZone:
            return self._styleSheet.redZone
        if self._styleSheet.greenZone.visible and not worldInfo.isPlaceholder:
            return self._styleSheet.greenZone
        return None

    def _worldStyle(
            self,
            worldInfo: maprenderer.WorldInfo
            ) -> maprenderer.StyleSheet.StyleElement:
        if self._styleSheet.showWorldDetailColors:
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

        # Classic colors
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
    def _worldStarProps(world: traveller.World) -> typing.Iterable[typing.Tuple[
            str, # Fill Color,
            str, # Border Color
            float]]: # Radius
        stellar = world.stellar()
        props = []
        for star in stellar.yieldStars():
            classification = star.string()
            if classification == 'D':
                props.append((travellermap.MapColours.White, travellermap.MapColours.Black, 0.3))
            # NOTE: This todo came in with traveller map code
            # TODO: Distinct rendering for black holes, neutron stars, pulsars
            elif classification == 'NS' or classification == 'PSR' or classification == 'BH':
                props.append((travellermap.MapColours.Black, travellermap.MapColours.White, 0.8))
            elif classification == 'BD':
                props.append((travellermap.MapColours.Brown, travellermap.MapColours.Black, 0.3))
            else:
                color, radius = RenderContext._StarPropsMap.get(
                    star.code(element=traveller.Star.Element.SpectralClass),
                    (None, None))
                if color:
                    luminance = star.code(element=traveller.Star.Element.LuminosityClass)
                    luminance = RenderContext._StarLuminanceMap.get(luminance, 0)
                    props.append((color, travellermap.MapColours.Black, radius + luminance))

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
    def _starOffset(index: int) -> maprenderer.AbstractPointF:
        if index >= len(RenderContext._StarOffsetX):
            index = (index % (len(RenderContext._StarOffsetX) - 1)) + 1
        return maprenderer.AbstractPointF(RenderContext._StarOffsetX[index], RenderContext._StarOffsetY[index])

    @staticmethod
    def _offsetRouteSegment(startPoint: maprenderer.AbstractPointF, endPoint: maprenderer.AbstractPointF, offset: float) -> None:
        dx = (endPoint.x() - startPoint.x()) * travellermap.ParsecScaleX
        dy = (endPoint.y() - startPoint.y()) * travellermap.ParsecScaleY
        length = math.sqrt(dx * dx + dy * dy)
        if not length:
            return # No offset
        ddx = (dx * offset / length) / travellermap.ParsecScaleX
        ddy = (dy * offset / length) / travellermap.ParsecScaleY
        startPoint.setX(startPoint.x() + ddx)
        startPoint.setY(startPoint.y() + ddy)
        endPoint.setX(endPoint.x() - ddx)
        endPoint.setY(endPoint.y() - ddy)

    @staticmethod
    def _hexToCenter(hex: travellermap.HexPosition) -> maprenderer.AbstractPointF:
        centerX, centerY = hex.absoluteCenter()
        return maprenderer.AbstractPointF(x=centerX, y=centerY)
