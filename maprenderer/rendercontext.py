import common
import enum
import logging
import maprenderer
import math
import random
import traveller
import travellermap
import typing

class RenderContext(object):
    class LayerAction(object):
        def __init__(
                self,
                id: maprenderer.LayerId,
                action: typing.Callable[[], typing.NoReturn],
                clip: bool
                ) -> None:
            self.id = id
            self.action = action
            self.clip = clip

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
    _MaxScale = 512; # Math.Pow(2, 9)

    _PseudoRandomStarsChunkSize = 256
    _PseudoRandomStarsMaxPerChunk = 400

    def __init__(
            self,
            graphics: maprenderer.AbstractGraphics,
            absoluteCenterX: float,
            absoluteCenterY: float,
            scale: float,
            outputPixelX: int,
            outputPixelY: int,
            style: travellermap.Style,
            imageCache: maprenderer.ImageCache,
            vectorCache: maprenderer.VectorObjectCache,
            mapLabelCache: maprenderer.MapLabelCache,
            worldLabelCache: maprenderer.WorldLabelCache,
            styleCache: maprenderer.DefaultStyleCache,
            options: maprenderer.MapOptions
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
        self._starfieldCache = maprenderer.StarfieldCache(
            graphics=self._graphics)
        self._selector = maprenderer.RectSelector(
            graphics=self._graphics)
        self._clipOutsectorBorders = True # TODO: Rename this to clipSectorBorders
        self._absoluteViewRect = None

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
        self._absoluteCenterX = absoluteCenterX
        self._absoluteCenterY = absoluteCenterY
        self._scale = common.clamp(scale, RenderContext._MinScale, RenderContext._MaxScale)
        self._outputPixelX = outputPixelX
        self._outputPixelY = outputPixelY

        self._styleSheet.scale = self._styleSheetScale()

        self._updateView()

    def setClipOutsectorBorders(self, enable: bool) -> None:
        self._clipOutsectorBorders = enable

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
                # TODO: Implement clipping if I need it
                """
                // HACK: Clipping to tileRect rapidly becomes inaccurate away from
                // the origin due to float precision. Only do it if really necessary.
                bool clip = layer.clip && (ctx.ForceClip ||
                    !((ClipPath == null) && (graphics is BitmapGraphics)));

                // Impose a clipping region if desired, or remove it if not.
                if (clip && state == null)
                {
                    state = graphics.Save();
                    if (ClipPath != null) graphics.IntersectClip(ClipPath);
                    else graphics.IntersectClip(tileRect);
                }
                else if (!clip && state != null)
                {
                    state.Dispose();
                    state = null;
                }

                layer.Run(this);
                timers.Add(new Timer(layer.id.ToString()));
                """

                # TODO: This should probably save the render state before each
                # layer and restore it afterwards so no one layer can affect another.
                # If I do this I can remove a load of save states from inside
                # layer action handlers
                #with common.DebugTimer(string=str(layer.action)):
                if True:
                    layer.action()

    def _createLayers(self) -> None:
        # TODO: This list probably only needs created once
        self._layers: typing.List[RenderContext.LayerAction] = [
            RenderContext.LayerAction(maprenderer.LayerId.Background_Solid, self._drawBackground, clip=True),

            # NOTE: Since alpha texture brushes aren't supported without
            # creating a new image (slow!) we render the local background
            # first, then overlay the deep background over it, for
            # basically the same effect since the alphas sum to 1.
            RenderContext.LayerAction(maprenderer.LayerId.Background_NebulaTexture, self._drawNebulaBackground, clip=True),
            RenderContext.LayerAction(maprenderer.LayerId.Background_Galaxy, self._drawGalaxyBackground, clip=True),

            RenderContext.LayerAction(maprenderer.LayerId.Background_PseudoRandomStars, self._drawPseudoRandomStars, clip=True),
            RenderContext.LayerAction(maprenderer.LayerId.Background_Rifts, self._drawRifts, clip=True),

            #------------------------------------------------------------
            # Foreground
            #------------------------------------------------------------
            RenderContext.LayerAction(maprenderer.LayerId.Macro_Borders, self._drawMacroBorders, clip=True),
            RenderContext.LayerAction(maprenderer.LayerId.Macro_Routes, self._drawMacroRoutes, clip=True),

            RenderContext.LayerAction(maprenderer.LayerId.Grid_Sector, self._drawSectorGrid, clip=True),
            RenderContext.LayerAction(maprenderer.LayerId.Grid_Subsector, self._drawSubsectorGrid, clip=True),
            RenderContext.LayerAction(maprenderer.LayerId.Grid_Parsec, self._drawParsecGrid, clip=True),

            RenderContext.LayerAction(maprenderer.LayerId.Names_Subsector, self._drawSubsectorNames, clip=True),

            RenderContext.LayerAction(maprenderer.LayerId.Micro_BordersStroke, self._drawMicroBorders, clip=True),
            RenderContext.LayerAction(maprenderer.LayerId.Micro_Routes, self._drawMicroRoutes, clip=True),
            RenderContext.LayerAction(maprenderer.LayerId.Micro_BorderExplicitLabels, self._drawMicroLabels, clip=True),

            RenderContext.LayerAction(maprenderer.LayerId.Names_Sector, self._drawSectorNames, clip=True),
            RenderContext.LayerAction(maprenderer.LayerId.Macro_GovernmentRiftRouteNames, self._drawMacroNames, clip=True),
            RenderContext.LayerAction(maprenderer.LayerId.Macro_CapitalsAndHomeWorlds, self._drawCapitalsAndHomeWorlds, clip=True),
            RenderContext.LayerAction(maprenderer.LayerId.Mega_GalaxyScaleLabels, self._drawMegaLabels, clip=True),

            RenderContext.LayerAction(maprenderer.LayerId.Worlds_Background, self._drawWorldsBackground, clip=True),

            # Not clipped, so names are not clipped in jumpmaps.
            RenderContext.LayerAction(maprenderer.LayerId.Worlds_Foreground, self._drawWorldsForeground, clip=False),

            RenderContext.LayerAction(maprenderer.LayerId.Worlds_Overlays, self._drawWorldsOverlay, clip=True),

            #------------------------------------------------------------
            # Overlays
            #------------------------------------------------------------
            RenderContext.LayerAction(maprenderer.LayerId.Overlay_DroyneChirperWorlds, self._drawDroyneOverlay, clip=True),
            RenderContext.LayerAction(maprenderer.LayerId.Overlay_MinorHomeworlds, self._drawMinorHomeworldOverlay, clip=True),
            RenderContext.LayerAction(maprenderer.LayerId.Overlay_AncientsWorlds, self._drawAncientWorldsOverlay, clip=True),
            RenderContext.LayerAction(maprenderer.LayerId.Overlay_ReviewStatus, self._drawSectorReviewStatusOverlay, clip=True),
        ]

        """
        self._layers: typing.List[RenderContext.LayerAction] = [
            RenderContext.LayerAction(maprenderer.LayerId.Background_Solid, self._drawBackground, clip=True),
            RenderContext.LayerAction(maprenderer.LayerId.Background_PseudoRandomStars, self._drawPseudoRandomStars, clip=True),
        ]
        """

        self._layers.sort(key=lambda l: self._styleSheet.layerOrder[l.id])

    # The style sheet scale is different from the actual scale to simulate
    # the way Traveller Map fonts and
    def _styleSheetScale(self) -> float:
        logScale = round(travellermap.linearScaleToLogScale(self._scale))
        return travellermap.logScaleToLinearScale(logScale)

    def _updateView(self):
        absoluteWidth = self._outputPixelX / (self._scale * travellermap.ParsecScaleX)
        absoluteHeight = self._outputPixelY / (self._scale * travellermap.ParsecScaleY)
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
                    pen=self._styleSheet.macroBorders.pen)

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
                    pen=self._styleSheet.macroRoutes.pen)

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
                    pen=self._styleSheet.sectorGrid.pen,
                    pt1=maprenderer.AbstractPointF(0, self._absoluteViewRect.top() - gridSlop),
                    pt2=maprenderer.AbstractPointF(0, self._absoluteViewRect.bottom() + gridSlop))
            h += travellermap.SectorWidth

        v = ((math.floor((self._absoluteViewRect.top()) / travellermap.SectorHeight) - 1) - travellermap.ReferenceSectorY) * \
            travellermap.SectorHeight - travellermap.ReferenceHexY
        while v <= (self._absoluteViewRect.bottom() + travellermap.SectorHeight):
            self._graphics.drawLine(
                pen=self._styleSheet.sectorGrid.pen,
                pt1=maprenderer.AbstractPointF(self._absoluteViewRect.left() - gridSlop, v),
                pt2=maprenderer.AbstractPointF(self._absoluteViewRect.right() + gridSlop, v))
            v += travellermap.SectorHeight

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
                pen=self._styleSheet.subsectorGrid.pen,
                pt1=maprenderer.AbstractPointF(h, self._absoluteViewRect.top() - gridSlop),
                pt2=maprenderer.AbstractPointF(h, self._absoluteViewRect.bottom() + gridSlop))
            with self._graphics.save():
                self._graphics.translateTransform(dx=h, dy=0)
                self._graphics.scaleTransform(
                    scaleX=1 / travellermap.ParsecScaleX,
                    scaleY=1 / travellermap.ParsecScaleY)
                self._graphics.drawLine(
                    pen=self._styleSheet.subsectorGrid.pen,
                    pt1=maprenderer.AbstractPointF(0, self._absoluteViewRect.top() - gridSlop),
                    pt2=maprenderer.AbstractPointF(0, self._absoluteViewRect.bottom() + gridSlop))

        vmin = int(math.floor(self._absoluteViewRect.top() / travellermap.SubsectorHeight) - 1 -
                   travellermap.ReferenceSectorY)
        vmax = int(math.ceil((self._absoluteViewRect.bottom() + travellermap.SubsectorHeight +
                              travellermap.ReferenceHexY) / travellermap.SubsectorHeight))
        for vi in range(vmin, vmax + 1):
            if (vi % 4) == 0:
                continue
            v = vi * travellermap.SubsectorHeight - travellermap.ReferenceHexY
            self._graphics.drawLine(
                pen=self._styleSheet.subsectorGrid.pen,
                pt1=maprenderer.AbstractPointF(self._absoluteViewRect.left() - gridSlop, v),
                pt2=maprenderer.AbstractPointF(self._absoluteViewRect.right() + gridSlop, v))

    def _drawParsecGrid(self) -> None:
        if not self._styleSheet.parsecGrid.visible:
            return

        self._graphics.setSmoothingMode(
                maprenderer.AbstractGraphics.SmoothingMode.HighQuality)

        parsecSlop = 1

        hx = int(math.floor(self._absoluteViewRect.x()))
        hw = int(math.ceil(self._absoluteViewRect.width()))
        hy = int(math.floor(self._absoluteViewRect.y()))
        hh = int(math.ceil(self._absoluteViewRect.height()))

        pen = self._styleSheet.parsecGrid.pen

        if self._styleSheet.hexStyle == maprenderer.HexStyle.Square:
            rect = self._graphics.createRectangle()
            for px in range(hx - parsecSlop, hx + hw + parsecSlop):
                yOffset = 0 if ((px % 2) != 0) else 0.5
                for py in range(hy - parsecSlop, hy + hh + parsecSlop):
                    inset = 1
                    rect.setX(px + inset)
                    rect.setY(py + inset + yOffset)
                    rect.setWidth(1 - inset * 2)
                    rect.setHeight(1 - inset * 2)
                    self._graphics.drawRectangle(rect=rect, pen=pen)
        elif self._styleSheet.hexStyle == maprenderer.HexStyle.Hex:
            startX = hx - parsecSlop
            startY = hy - parsecSlop
            points = [
                maprenderer.AbstractPointF(startX + -travellermap.HexWidthOffset, startY + 0.5),
                maprenderer.AbstractPointF(startX + travellermap.HexWidthOffset, startY + 1.0),
                maprenderer.AbstractPointF(startX + 1.0 - travellermap.HexWidthOffset, startY + 1.0),
                maprenderer.AbstractPointF(startX + 1.0 + travellermap.HexWidthOffset, startY + 0.5)]
            types = [
                maprenderer.PathPointType.Start,
                maprenderer.PathPointType.Line,
                maprenderer.PathPointType.Line,
                maprenderer.PathPointType.Start | maprenderer.PathPointType.CloseSubpath]
            path = self._graphics.createPath(points=points, types=types, closed=False)
            for px in range(startX, hx + hw + parsecSlop):
                yOffset = 0 if ((px % 2) != 0) else 0.5

                if yOffset:
                    path.translate(0, yOffset)

                for py in range(startY, hy + hh + parsecSlop):
                    self._graphics.drawPath(path=path, pen=pen)
                    path.translate(0, 1)

                path.translate(1, -((py - startY) + yOffset + 1))

        if self._styleSheet.numberAllHexes and (self._styleSheet.worldDetails & maprenderer.WorldDetails.Hex) != 0:
            for px in range(hx - parsecSlop, hx + hw + parsecSlop):
                yOffset = 0 if ((px % 2) != 0) else 0.5
                for py in range(hy - parsecSlop, hy + hh + parsecSlop):

                    if self._styleSheet.hexCoordinateStyle == maprenderer.HexCoordinateStyle.Subsector:
                        # TODO: Need to implement Subsector hex number. Not sure what this
                        # actually is
                        hex = 'TODO'
                    else:
                        relativePos = travellermap.absoluteSpaceToRelativeSpace((px + 1, py + 1))
                        hex = f'{relativePos[2]:02d}{relativePos[3]:02d}'

                    with self._graphics.save():
                        self._graphics.translateTransform(px + 0.5, py + yOffset)
                        self._graphics.scaleTransform(
                            self._styleSheet.hexContentScale / travellermap.ParsecScaleX,
                            self._styleSheet.hexContentScale / travellermap.ParsecScaleY)
                        self._graphics.drawString(
                            hex,
                            self._styleSheet.hexNumber.font,
                            self._styleSheet.hexNumber.textBrush,
                            0, 0,
                            maprenderer.TextAlignment.TopCenter)

    def _drawSubsectorNames(self) -> None:
        if not self._styleSheet.subsectorNames.visible:
            return

        self._graphics.setSmoothingMode(
             maprenderer.AbstractGraphics.SmoothingMode.HighQuality)

        for subsector in self._selector.subsectors():
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

        penWidth = self._styleSheet.microBorders.pen.width()
        # HACK: Due to the fact clipping to the outline being drawn
        # doesn't work with Qt (see HACK below), it means outlines
        # appear twice as thick as they do in Traveller Map. This
        # scales the width to account for this
        penWidth *= 0.5
        pen = self._graphics.createPen(width=penWidth)
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

                regions = self._sectorCache.sectorRegions(x=sector.x(), y=sector.y())
                if regions:
                    for outline in regions:
                        if not self._absoluteViewRect.intersectsWith(outline.bounds()):
                            continue # Outline isn't on screen
                        self._drawMicroBorder(
                            outline=outline,
                            brush=brush)

                borders = self._sectorCache.sectorBorders(x=sector.x(), y=sector.y())
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
            baseWidth = self._styleSheet.microRoutes.pen.width()

            for sector in self._selector.sectors():
                for route in sector.routes():
                    # Compute source/target sectors (may be offset)
                    startPoint = route.startHex()
                    endPoint = route.endHex()

                    # If drawing dashed lines twice and the start/end are swapped the
                    # dashes don't overlap correctly. So "sort" the points.
                    needsSwap = (startPoint.absoluteX() < endPoint.absoluteX()) or \
                        (startPoint.absoluteX() == endPoint.absoluteX() and \
                         startPoint.absoluteY() < endPoint.absoluteY())
                    if needsSwap:
                        (startPoint, endPoint) = (endPoint, startPoint)

                    startPoint = RenderContext._hexToCenter(startPoint)
                    endPoint = RenderContext._hexToCenter(endPoint)

                    # Shorten line to leave room for world glyph
                    self._offsetRouteSegment(startPoint, endPoint, self._styleSheet.routeEndAdjust)

                    routeColor = route.colour()
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
                        presidence = [route.allegiance(), route.type(), 'Im']
                        for key in presidence:
                            defaultColor, defaultStyle, defaltWidth = self._styleCache.defaultRouteStyle(key)
                            if not routeColor:
                                routeColor = defaultColor
                            if not routeStyle:
                                routeStyle = defaultStyle
                            if not routeWidth:
                                routeWidth = defaltWidth

                    # In grayscale, convert default color and style to non-default style
                    if self._styleSheet.grayscale and (not routeColor) and (not routeStyle):
                        routeStyle = maprenderer.LineStyle.Dash

                    if not routeWidth:
                        routeWidth = 1.0
                    if not routeColor:
                        routeColor = self._styleSheet.microRoutes.pen.color()
                    if not routeStyle:
                        routeStyle = maprenderer.LineStyle.Solid

                    # Ensure color is visible
                    # TODO: Handle making colour visible, should be
                    # styles.grayscale || !ColorUtil.NoticeableDifference(routeColor.Value, styles.backgroundColor)
                    if self._styleSheet.grayscale:
                        routeColor = self._styleSheet.microRoutes.pen.color() # default

                    pen.setColor(routeColor)
                    pen.setWidth(routeWidth * baseWidth)
                    pen.setStyle(routeStyle)

                    self._graphics.drawLine(pen, startPoint, endPoint)

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

        brush = self._graphics.createBrush()

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
                    self._graphics.translateTransform(
                        dx=label.position.x(),
                        dy=label.position.y())
                    self._graphics.scaleTransform(
                        scaleX=1.0 / travellermap.ParsecScaleX,
                        scaleY=1.0 / travellermap.ParsecScaleY)
                    maprenderer.drawStringHelper(
                        graphics=self._graphics,
                        text=label.text,
                        font=font,
                        brush=brush,
                        x=0, y=0)

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
                self._graphics.translateTransform(
                    dx=label.position.x(),
                    dy=label.position.y())
                self._graphics.scaleTransform(
                    scaleX=1.0 / travellermap.ParsecScaleX,
                    scaleY=1.0 / travellermap.ParsecScaleY)
                maprenderer.drawStringHelper(
                    graphics=self._graphics,
                    text=label.text,
                    font=font,
                    brush=self._styleSheet.megaNames.textBrush,
                    x=0, y=0)

    def _drawWorldsBackground(self) -> None:
        if not self._styleSheet.worlds.visible or self._styleSheet.showStellarOverlay \
            or not self._styleSheet.worldDetails or self._styleSheet.worldDetails is maprenderer.WorldDetails.NoDetails:
            return

        for world in self._selector.worlds():
            self._drawWorld(
                world=world,
                layer=RenderContext.WorldLayer.Background)

    def _drawWorldsForeground(self) -> None:
        if not self._styleSheet.worlds.visible or self._styleSheet.showStellarOverlay:
            return

        if not self._styleSheet.worldDetails or self._styleSheet.worldDetails is maprenderer.WorldDetails.NoDetails:
            with self._graphics.save():
                self._graphics.setSmoothingMode(
                    maprenderer.AbstractGraphics.SmoothingMode.AntiAlias)


                xScale = self._styleSheet.hexContentScale / travellermap.ParsecScaleX
                yScale = self._styleSheet.hexContentScale / travellermap.ParsecScaleY
                halfWidth = self._styleSheet.discRadius * xScale
                halfHeight = self._styleSheet.discRadius * yScale

                #if halfWidth <= 0.5 or halfHeight <= 0.5:
                if ((halfWidth * self._scale) <= 1) or ((halfHeight * self._scale) <= 1):
                    # TODO: Creating this pen every frame isn't great
                    pen = self._graphics.createPen(
                        color=self._styleSheet.worlds.textBrush.color(),
                        width=(1 / self._scale),
                        style=maprenderer.LineStyle.Solid)
                    for world in self._selector.worlds():
                        self._graphics.drawPoint(
                            point=RenderContext._hexToCenter(world.hex()),
                            pen=pen)
                else:
                    width = halfWidth * 2
                    height = halfHeight * 2
                    rect = self._graphics.createRectangle()
                    for world in self._selector.worlds():
                        center = RenderContext._hexToCenter(world.hex())
                        rect.setRect(
                            x=center.x() - halfWidth,
                            y=center.y() - halfHeight,
                            width=width,
                            height=height)
                        self._graphics.drawEllipse(
                            rect=rect,
                            brush=self._styleSheet.worlds.textBrush)
        else:
            for world in self._selector.worlds():
                self._drawWorld(
                    world=world,
                    layer=RenderContext.WorldLayer.Foreground)

    def _drawWorldsOverlay(self) -> None:
        if not self._styleSheet.worlds.visible:
            return

        with self._graphics.save():
            self._graphics.setSmoothingMode(
                maprenderer.AbstractGraphics.SmoothingMode.HighQuality)
            if self._styleSheet.showStellarOverlay:
                for world in self._selector.worlds():
                    self._drawStars(world)
            elif self._styleSheet.hasWorldOverlays:
                slop = self._selector.worldSlop()
                self._selector.setSectorSlop(max(slop, math.log2(self._scale) - 4))
                try:
                    for world in self._selector.worlds():
                        self._drawWorld(
                            world=world,
                            layer=RenderContext.WorldLayer.Overlay)
                finally:
                    self._selector.setWorldSlop(slop)

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
            for sector in self._selector.sectors():
                if not sector.hasTag('Official') and not sector.hasTag('Preserve') and not sector.hasTag('InReview'):
                    clipPath = self._clipCache.sectorClipPath(
                        sectorX=sector.x(),
                        sectorY=sector.y(),
                        pathType=maprenderer.ClipPathCache.PathType.Hex)

                    self._graphics.drawPath(
                        path=clipPath,
                        brush=brush)

        if self._styleSheet.colorCodeSectorStatus and self._styleSheet.worlds.visible:
            for sector in self._selector.sectors():
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

    def _drawWorld(self, world: traveller.World, layer: WorldLayer) -> None:
        uwp = world.uwp()
        isPlaceholder = False # TODO: Handle placeholder worlds
        isCapital = isHiPop = False
        renderName = False
        if ((self._styleSheet.worldDetails & maprenderer.WorldDetails.AllNames) != 0) or \
            ((self._styleSheet.worldDetails & maprenderer.WorldDetails.KeyNames) != 0):
            isCapital = maprenderer.WorldHelper.isCapital(world)
            isHiPop = maprenderer.WorldHelper.isHighPopulation(world)
            renderName = ((self._styleSheet.worldDetails & maprenderer.WorldDetails.AllNames) != 0) or \
                (isCapital or isHiPop)
        renderUWP = (self._styleSheet.worldDetails & maprenderer.WorldDetails.Uwp) != 0

        # TODO: This calls self._graphics.createRectangle quite a lot, could
        # it just be created once then updated at different stages as needed?

        with self._graphics.save():
            self._graphics.setSmoothingMode(
                maprenderer.AbstractGraphics.SmoothingMode.AntiAlias)

            center = RenderContext._hexToCenter(world.hex())

            self._graphics.translateTransform(
                dx=center.x(),
                dy=center.y())
            self._graphics.scaleTransform(
                scaleX=self._styleSheet.hexContentScale / travellermap.ParsecScaleX,
                scaleY=self._styleSheet.hexContentScale / travellermap.ParsecScaleY)
            self._graphics.rotateTransform(
                degrees=self._styleSheet.hexRotation)

            if layer is RenderContext.WorldLayer.Overlay:
                if self._styleSheet.populationOverlay.visible and (world.population() > 0):
                    self._drawOverlay(
                        element=self._styleSheet.populationOverlay,
                        radius=math.sqrt(world.population() / math.pi) * 0.00002)

                if self._styleSheet.importanceOverlay.visible:
                    # TODO: Handle importance overlay
                    """
                    int im = world.CalculatedImportance;
                    if (im > 0)
                    {
                        DrawOverlay(styles.importanceOverlay, (im - 0.5f) * Astrometrics.ParsecScaleX, ref brush, ref pen);
                    }
                    """

                if self._styleSheet.capitalOverlay.visible:
                    # TODO: Handle capital overlay
                    """
                    bool hasIm = world.CalculatedImportance >= 4;
                    bool hasCp = world.IsCapital;

                    if (hasIm && hasCp)
                        DrawOverlay(styles.capitalOverlay, 2 * Astrometrics.ParsecScaleX, ref brush, ref pen);
                    else if (hasIm)
                        DrawOverlay(styles.capitalOverlayAltA, 2 * Astrometrics.ParsecScaleX, ref brush, ref pen);
                    else if (hasCp)
                        DrawOverlay(styles.capitalOverlayAltB, 2 * Astrometrics.ParsecScaleX, ref brush, ref pen);
                    """

                # TODO: Not sure if I need to bother with highlight pattern stuff. It
                # doesn't look like it's used in tile rendering (just image rendering)
                """
                if (styles.highlightWorlds.visible && styles.highlightWorldsPattern!.Matches(world))
                {
                    DrawOverlay(styles.highlightWorlds, Astrometrics.ParsecScaleX, ref brush, ref pen);
                }
                """

            if not self._styleSheet.useWorldImages:
                # Normal (non-"Eye Candy") styles
                if layer is RenderContext.WorldLayer.Background:
                    if (self._styleSheet.worldDetails & maprenderer.WorldDetails.Zone) != 0:
                        elem = self._zoneStyle(world)
                        if elem and elem.visible:
                            if self._styleSheet.showZonesAsPerimeters:
                                with self._graphics.save():
                                    # TODO: Why is this 2 separate scale transforms?
                                    self._graphics.scaleTransform(
                                        scaleX=travellermap.ParsecScaleX,
                                        scaleY=travellermap.ParsecScaleY)
                                    self._graphics.scaleTransform(
                                        scaleX=0.95,
                                        scaleY=0.95)
                                    self._graphics.drawPath(
                                        path=self._hexOutlinePath,
                                        pen=elem.pen)
                            else:
                                if elem.fillBrush:
                                    self._graphics.drawEllipse(
                                        rect=self._graphics.createRectangle(x=-0.4, y=-0.4, width=0.8, height=0.8),
                                        brush=elem.fillBrush)
                                if elem.pen:
                                    if renderName and self._styleSheet.fillMicroBorders:
                                        # TODO: Is saving the state actually needed here?
                                        with self._graphics.save():
                                            self._graphics.intersectClipRect(
                                                rect=self._graphics.createRectangle(
                                                    x=-0.5,
                                                    y=-0.5,
                                                    width=1,
                                                    height=0.65 if renderUWP else 0.75))
                                            self._graphics.drawEllipse(
                                                rect=self._graphics.createRectangle(
                                                    x=-0.4,
                                                    y=-0.4,
                                                    width=0.8,
                                                    height=0.8),
                                                pen=elem.pen)
                                    else:
                                        self._graphics.drawEllipse(
                                            rect=self._graphics.createRectangle(
                                                x=-0.4,
                                                y=-0.4,
                                                width=0.8,
                                                height=0.8),
                                            pen=elem.pen)

                    if not self._styleSheet.numberAllHexes and \
                        ((self._styleSheet.worldDetails & maprenderer.WorldDetails.Hex) != 0):

                        hex = world.hex()
                        if self._styleSheet.hexContentScale is maprenderer.HexCoordinateStyle.Subsector:
                            # TODO: Handle subsector hex whatever that is
                            #hex=f'{hex.offsetX():02d}{hex.offsetY():02d}'
                            hex='TODO'
                        else:
                            hex=f'{hex.offsetX():02d}{hex.offsetY():02d}'

                        self._graphics.drawString(
                            text=hex,
                            font=self._styleSheet.hexNumber.font,
                            brush=self._styleSheet.hexNumber.textBrush,
                            x=self._styleSheet.hexNumber.position.x(),
                            y=self._styleSheet.hexNumber.position.y(),
                            format=maprenderer.TextAlignment.TopCenter)

                if layer is RenderContext.WorldLayer.Foreground:
                    elem = self._zoneStyle(world)
                    worldTextBackgroundStyle = \
                        maprenderer.TextBackgroundStyle.NoStyle \
                        if (not elem or not elem.fillBrush) else \
                        self._styleSheet.worlds.textBackgroundStyle

                    # TODO: Implement placeholders, this should be
                    # if (!isPlaceholder)
                    if True:
                        if ((self._styleSheet.worldDetails & maprenderer.WorldDetails.GasGiant) != 0) and \
                            maprenderer.WorldHelper.hasGasGiants(world):
                            self._drawGasGiant(
                                brush=self._styleSheet.worlds.textBrush,
                                x=self._styleSheet.gasGiantPosition.x(),
                                y=self._styleSheet.gasGiantPosition.y(),
                                radius=0.05,
                                ring=self._styleSheet.showGasGiantRing)

                        if (self._styleSheet.worldDetails & maprenderer.WorldDetails.Starport) != 0:
                            starport = uwp.code(traveller.UWP.Element.StarPort)
                            if self._styleSheet.showTL:
                                starport += "-" + uwp.code(traveller.UWP.Element.TechLevel)

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
                                text=uwp.string())

                        # NOTE: This todo came in with the traveller map code
                        # TODO: Mask off background for glyphs
                        if (self._styleSheet.worldDetails & maprenderer.WorldDetails.Bases) != 0:
                            bases = world.bases()
                            baseCount = bases.count()

                            # TODO: Handle base allegiances
                            """
                            # Special case: Show Zho Naval+Military as diamond
                            if (world.BaseAllegiance == "Zh" && bases == "KM")
                                bases = "Z";
                            """

                            # Base 1
                            bottomUsed = False
                            if baseCount:
                                glyph = maprenderer.GlyphDefs.fromBaseCode(
                                    allegiance=world.allegiance(),
                                    code=traveller.Bases.code(bases[0]))
                                if glyph.isPrintable:
                                    pt = self._styleSheet.baseTopPosition
                                    if glyph.bias is maprenderer.Glyph.GlyphBias.Bottom and \
                                        not self._styleSheet.ignoreBaseBias:
                                        pt = self._styleSheet.baseBottomPosition
                                        bottomUsed = True

                                    brush = \
                                        self._styleSheet.worlds.textHighlightBrush \
                                        if glyph.highlight else \
                                        self._styleSheet.worlds.textBrush
                                    self._drawWorldGlyph(
                                        glyph=glyph,
                                        brush=brush,
                                        pt=pt)

                            # Base 2
                            # TODO: Add support for legacyAllegiance
                            """
                            if baseCount > 1:
                                glyph = maprenderer.GlyphDefs.fromBaseCode(
                                    allegiance=world.legacyAllegiance, bases[1])
                                if glyph.isPrintable:
                                    pt = self._styles.baseTopPosition if bottomUsed else self._styles.baseBottomPosition
                                    brush.color = \
                                        self._styles.worlds.textHighlightColor \
                                        if glyph.isHighlighted else \
                                        self._styles.worlds.textColor
                                    self._drawWorldGlyph(
                                        glyph=glyph,
                                        brush=brush,
                                        position=pt)

                            # Base 3 (!)
                            if baseCount > 2:
                                glyph = maprenderer.GlyphDefs.fromBaseCode(world.legacyAllegiance, bases[2])
                                if glyph.isPrintable:
                                    brush.color = \
                                        self._styles.worlds.textHighlightColor \
                                        if glyph.isHighlighted else \
                                        self._styles.worlds.textColor
                                    self._drawWorldGlyph(
                                        glyph=glyph,
                                        brush=brush,
                                        position=self._styles.baseMiddlePosition)
                            """

                            # Research Stations
                            # TODO: Handle research stations/penal colony etc
                            """
                            rs = world.researchStation()
                            glyph = None
                            if rs:
                                glyph = maprenderer.GlyphDefs.fromResearchCode(rs)
                            elif world.isReserve:
                                glyph = maprenderer.GlyphDefs.Reserve
                            elif world.isPenalColony:
                                glyph = maprenderer.GlyphDefs.Prison
                            elif world.isPrisonExileCamp:
                                glyph = maprenderer.GlyphDefs.ExileCamp
                            if glyph:
                                brush.color = \
                                    self._styles.worlds.textHighlightColor \
                                    if glyph.isHighlighted else \
                                    self._styles.worlds.textColor
                                self._drawWorldGlyph(
                                    glyph=glyph,
                                    brush=brush,
                                    position=self._styles.baseMiddlePosition)
                            """

                    if (self._styleSheet.worldDetails & maprenderer.WorldDetails.Type) != 0:
                        # TODO: Handle placeholders, this should be
                        # if (isPlaceholder)
                        if False:
                            e = self._styleSheet.anomaly if world.isAnomaly() else self._styleSheet.placeholder
                            self._drawWorldLabel(
                                bkStyle=e.textBackgroundStyle,
                                bkBrush=self._styleSheet.worlds.textBrush,
                                textBrush=e.textColor, # TODO: This will need converted to a brush
                                position=e.position,
                                font=e.font,
                                text=e.content)
                        else:
                            with self._graphics.save():
                                self._graphics.translateTransform(
                                    dx=self._styleSheet.discPosition.x(),
                                    dy=self._styleSheet.discPosition.y())
                                if uwp.numeric(element=traveller.UWP.Element.WorldSize, default=-1) <= 0:
                                    if (self._styleSheet.worldDetails & maprenderer.WorldDetails.Asteroids) != 0:
                                        # Basic pattern, with probability varying per position:
                                        #   o o o
                                        #  o o o o
                                        #   o o o

                                        lpx = [-2, 0, 2, -3, -1, 1, 3, -2, 0, 2]
                                        lpy = [-2, -2, -2, 0, 0, 0, 0, 2, 2, 2]
                                        lpr = [0.5, 0.9, 0.5, 0.6, 0.9, 0.9, 0.6, 0.5, 0.9, 0.5]

                                        # Random generator is seeded with world location so it is always the same
                                        rand = random.Random(world.hex().absoluteX() ^ world.hex().absoluteY())
                                        rect = self._graphics.createRectangle()
                                        for i in range(len(lpx)):
                                            if rand.random() < lpr[i]:
                                                rect.setX(lpx[i] * 0.035)
                                                rect.setY(lpy[i] * 0.035)

                                                rect.setWidth(0.04 + rand.random() * 0.03)
                                                rect.setHeight(0.04 + rand.random() * 0.03)

                                                # If necessary, add jitter here
                                                #rect.x += 0
                                                #rect.y += 0

                                                self._graphics.drawEllipse(
                                                    rect=rect,
                                                    brush=self._styleSheet.worlds.textBrush)
                                    else:
                                        # Just a glyph
                                        self._drawWorldGlyph(
                                            glyph=maprenderer.GlyphDefs.DiamondX,
                                            brush=self._styleSheet.worlds.textBrush,
                                            pt=maprenderer.AbstractPointF(0, 0))
                                else:
                                    # TODO: Creating pens/brushes here every time isn't great.
                                    # The style sheet should probably return brush/pen objects
                                    # rather than string colours. It might make sense to move
                                    # the logic elsewhere so it can be cached
                                    penColor, brushColor = self._styleSheet.worldColors(world)
                                    pen = brush = None
                                    if penColor:
                                        pen = self._graphics.createPen(
                                            color=penColor,
                                            width=self._styleSheet.worldWater.pen.width(),
                                            style=self._styleSheet.worldWater.pen.style(),
                                            pattern=self._styleSheet.worldWater.pen.pattern())
                                    if brushColor:
                                        brush = self._graphics.createBrush(color=brushColor)
                                    self._graphics.drawEllipse(
                                        rect=self._graphics.createRectangle(
                                            x=-self._styleSheet.discRadius,
                                            y=-self._styleSheet.discRadius,
                                            width=2 * self._styleSheet.discRadius,
                                            height=2 * self._styleSheet.discRadius),
                                        pen=pen,
                                        brush=brush)
                    elif not world.isAnomaly():
                        # Dotmap
                        self._graphics.drawEllipse(
                            rect=self._graphics.createRectangle(
                                x=-self._styleSheet.discRadius,
                                y=-self._styleSheet.discRadius,
                                width=2 * self._styleSheet.discRadius,
                                height=2 * self._styleSheet.discRadius),
                            brush=self._styleSheet.worlds.textBrush)

                    if renderName:
                        name = world.name()
                        highlight = (self._styleSheet.worldDetails & maprenderer.WorldDetails.Highlight) != 0
                        if (isHiPop and highlight) or \
                            self._styleSheet.worlds.textStyle.uppercase:
                            name = name.upper()

                        textBrush = \
                            self._styleSheet.worlds.textHighlightBrush \
                            if isCapital and highlight else \
                            self._styleSheet.worlds.textBrush

                        font = \
                            self._styleSheet.worlds.largeFont \
                            if (isHiPop or isCapital) and highlight else \
                            self._styleSheet.worlds.font

                        self._drawWorldLabel(
                            bkStyle=worldTextBackgroundStyle,
                            bkBrush=self._styleSheet.worlds.textBrush,
                            textBrush=textBrush,
                            position=self._styleSheet.worlds.textStyle.translation,
                            font=font,
                            text=name)

                    if (self._styleSheet.worldDetails & maprenderer.WorldDetails.Allegiance) != 0:
                        alleg = maprenderer.WorldHelper.allegianceCode(
                            world=world,
                            ignoreDefault=True,
                            useLegacy=not self._styleSheet.t5AllegianceCodes)
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
                worldSize = world.physicalSize()
                imageRadius = (0.6 if worldSize <= 0 else (0.3 * (worldSize / 5.0 + 0.2))) / 2
                decorationRadius = imageRadius

                if layer is RenderContext.WorldLayer.Background:
                    if (self._styleSheet.worldDetails & maprenderer.WorldDetails.Type) != 0:
                        # TODO: Handle placeholders, this should be
                        #if isPlaceholder:
                        if False:
                            e = self._styleSheet.anomaly if world.isAnomaly() else self._styleSheet.placeholder
                            self._drawWorldLabel(
                                bkStyle=e.textBackgroundStyle,
                                bkBrush=self._styleSheet.worlds.textBrush,
                                textBrush=e.textColor,
                                position=e.position,
                                font=e.font,
                                text=e.content)
                        else:
                            scaleX = 1.5 if worldSize <= 0 else 1
                            scaleY = 1.0 if worldSize <= 0 else 1
                            self._graphics.drawImage(
                                image=maprenderer.WorldHelper.worldImage(
                                    world=world,
                                    images=self._imageCache),
                                rect=self._graphics.createRectangle(
                                    x=-imageRadius * scaleX,
                                    y=-imageRadius * scaleY,
                                    width=imageRadius * 2 * scaleX,
                                    height=imageRadius * 2 * scaleY))
                    elif not world.isAnomaly():
                        # Dotmap
                        self._graphics.drawEllipse(
                            rect=self._graphics.createRectangle(
                                x=-self._styleSheet.discRadius,
                                y=-self._styleSheet.discRadius,
                                width=2 * self._styleSheet.discRadius,
                                height=2 * self._styleSheet.discRadius),
                            brush=self._styleSheet.worlds.textBrush)

                # TODO: Support placeholders, this should be
                # if (isPlaceholder)
                if False:
                    return

                if layer is RenderContext.WorldLayer.Foreground:
                    decorationRadius += 0.1

                    if (self._styleSheet.worldDetails & maprenderer.WorldDetails.Zone) != 0:
                        zone = world.zone()
                        if zone is traveller.ZoneType.AmberZone or zone is traveller.ZoneType.RedZone:
                            pen = \
                                self._styleSheet.amberZone.pen \
                                if zone is traveller.ZoneType.AmberZone else \
                                self._styleSheet.redZone.pen
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

                    if (self._styleSheet.worldDetails & maprenderer.WorldDetails.GasGiant) != 0:
                        symbolRadius = 0.05
                        if self._styleSheet.showGasGiantRing:
                            decorationRadius += symbolRadius
                        self._drawGasGiant(
                            brush=self._styleSheet.worlds.textHighlightBrush,
                            x=decorationRadius,
                            y=0,
                            radius=symbolRadius,
                            ring=self._styleSheet.showGasGiantRing)
                        decorationRadius += 0.1

                    if renderUWP:
                        # NOTE: This todo came in with the traveller map code
                        # TODO: Scale, like the name text.
                        self._graphics.drawString(
                            text=uwp.string(),
                            font=self._styleSheet.hexNumber.font,
                            brush=self._styleSheet.worlds.textBrush,
                            x=decorationRadius,
                            y=self._styleSheet.uwp.position.y(),
                            format=maprenderer.TextAlignment.MiddleLeft)

                    if renderName:
                        name = world.name()
                        if isHiPop:
                            name.upper()

                        with self._graphics.save():
                            highlight = (self._styleSheet.worldDetails & maprenderer.WorldDetails.Highlight) != 0
                            textBrush = \
                                self._styleSheet.worlds.textHighlightBrush \
                                if isCapital and highlight else \
                                self._styleSheet.worlds.textBrush

                            if self._styleSheet.worlds.textStyle.uppercase:
                                name = name.upper()

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
                        # TODO: This doesn't seem right. I think this is drawing a shadow behind the text
                        # but if it's just drawing the background colour will you actually see it??
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
            pen.setWidth(self._styleSheet.worlds.pen.width())
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
            brush: maprenderer.AbstractBrush,
            x: float,
            y: float,
            radius: float,
            ring: bool
            ) -> None:
        with self._graphics.save():
            self._graphics.translateTransform(dx=x, dy=y)
            self._graphics.drawEllipse(
                rect=self._graphics.createRectangle(
                    x=-radius,
                    y=-radius,
                    width=radius * 2,
                    height=radius * 2),
                brush=brush)

            if ring:
                self._graphics.rotateTransform(degrees=-30)
                self._graphics.drawEllipse(
                    rect=self._graphics.createRectangle(
                        x=-radius * 1.75,
                        y=-radius * 0.4,
                        width=radius * 1.75 * 2,
                        height=radius * 0.4 * 2),
                    # TODO: Creating a pen each time is bad. Could store gas giant
                    # brush & pen a specific objects in the style sheet
                    pen=self._graphics.createPen(color=brush.color(), width=radius / 4))

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
            pen=element.pen,
            brush=element.fillBrush)

    _MicroBorderFillAlpha = 64
    _MicroBorderShadeAlpha = 128
    def _drawMicroBorder(
            self,
            outline: maprenderer.SectorOutline,
            brush: maprenderer.AbstractBrush,
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
            color = self._styleSheet.microRoutes.pen.color()

        style = outline.style()
        if not style:
            style = maprenderer.LineStyle.Solid

        # TODO: Handle noticable colours, this should be
        # styles.grayscale || !ColorUtil.NoticeableDifference(borderColor.Value, styles.backgroundColor
        if self._styleSheet.grayscale:
            color = self._styleSheet.microBorders.pen.color() # default

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
                if self._styleSheet.microBorders.pen.style() is maprenderer.LineStyle.Solid else
                self._styleSheet.microBorders.pen.style())

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
            pt: maprenderer.AbstractPointF
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
            x=pt.x(),
            y=pt.y(),
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
            self._graphics.translateTransform(
                dx=centerX,
                dy=centerY)
            self._graphics.scaleTransform(
                scaleX=1 / travellermap.ParsecScaleX,
                scaleY=1 / travellermap.ParsecScaleY)
            self._graphics.drawString(
                text=glyph,
                font=font,
                brush=brush,
                x=0, y=0,
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
            world: traveller.World
            ) -> typing.Optional[maprenderer.StyleSheet.StyleElement]:
        zone = world.zone()
        if zone is traveller.ZoneType.AmberZone:
            return self._styleSheet.amberZone
        if zone is traveller.ZoneType.RedZone:
            return self._styleSheet.redZone
        # TODO: Handle placeholders, this should be
        # if (styles.greenZone.visible && !world.IsPlaceholder)
        if self._styleSheet.greenZone.visible:
            return self._styleSheet.greenZone
        return None

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
