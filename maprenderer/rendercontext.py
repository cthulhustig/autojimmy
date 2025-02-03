import enum
import logging
import maprenderer
import math
import random
import re
import traveller
import travellermap
import typing

def _drawLabelHelper(
        graphics: maprenderer.AbstractGraphics,
        text: str,
        center: maprenderer.PointF,
        font: maprenderer.AbstractFont,
        brush: maprenderer.AbstractBrush,
        labelStyle: maprenderer.LabelStyle
        ) -> None:
    with graphics.save():
        if labelStyle.uppercase:
            text = text.upper()
        if labelStyle.wrap:
            text = text.replace(' ', '\n')

        graphics.translateTransform(
            dx=center.x,
            dy=center.y)
        graphics.scaleTransform(
            scaleX=1.0 / travellermap.ParsecScaleX,
            scaleY=1.0 / travellermap.ParsecScaleY)

        graphics.translateTransform(
            dx=labelStyle.translation.x,
            dy=labelStyle.translation.y)
        graphics.rotateTransform(
            degrees=labelStyle.rotation)
        graphics.scaleTransform(
            scaleX=labelStyle.scale.width,
            scaleY=labelStyle.scale.height)

        if labelStyle.rotation != 0:
            graphics.setSmoothingMode(
                maprenderer.AbstractGraphics.SmoothingMode.AntiAlias)

        maprenderer.drawStringHelper(
            graphics=graphics,
            text=text,
            font=font,
            brush=brush,
            x=0, y=0)

_DingMap = {
    '\u2666': '\x74', # U+2666 (BLACK DIAMOND SUIT)
    '\u2756': '\x76', # U+2756 (BLACK DIAMOND MINUS WHITE X)
    '\u2726': '\xAA', # U+2726 (BLACK FOUR POINTED STAR)
    '\u2605': '\xAB', # U+2605 (BLACK STAR)
    '\u2736': '\xAC'} # U+2736 (BLACK SIX POINTED STAR)

def _drawGlyphHelper(
        graphics: maprenderer.AbstractGraphics,
        glyph: maprenderer.Glyph,
        fonts: maprenderer.FontCache,
        brush: maprenderer.AbstractBrush,
        pt: maprenderer.PointF
        ) -> None:
    font = fonts.glyphFont
    s = glyph.characters
    if graphics.supportsWingdings():
        dings = ''
        for c in s:
            c = _DingMap.get(c)
            if c is None:
                dings = ''
                break
            dings += c
        if dings:
            font = fonts.wingdingFont
            s = dings

    graphics.drawString(
        text=s,
        font=font,
        brush=brush,
        x=pt.x,
        y=pt.y,
        format=maprenderer.StringAlignment.Centered)

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

    _GalaxyImageRect = maprenderer.RectangleF(-18257, -26234, 36551, 32462) # Chosen to match T5 pp.416
    _RiftImageRect = maprenderer.RectangleF(-1374, -827, 2769, 1754)

    _PseudoRandomStarsChunkSize = 256
    _PseudoRandomStarsMaxPerChunk = 400

    _HexPath = maprenderer.AbstractPath(
        points=[
            maprenderer.PointF(-0.5 + travellermap.HexWidthOffset, -0.5),
            maprenderer.PointF( 0.5 - travellermap.HexWidthOffset, -0.5),
            maprenderer.PointF( 0.5 + travellermap.HexWidthOffset, 0),
            maprenderer.PointF( 0.5 - travellermap.HexWidthOffset, 0.5),
            maprenderer.PointF(-0.5 + travellermap.HexWidthOffset, 0.5),
            maprenderer.PointF(-0.5 - travellermap.HexWidthOffset, 0),
            maprenderer.PointF(-0.5 + travellermap.HexWidthOffset, -0.5)],
        types=[
            maprenderer.PathPointType.Start,
            maprenderer.PathPointType.Line,
            maprenderer.PathPointType.Line,
            maprenderer.PathPointType.Line,
            maprenderer.PathPointType.Line,
            maprenderer.PathPointType.Line,
            maprenderer.PathPointType.Line | maprenderer.PathPointType.CloseSubpath],
        closed=True)

    def __init__(
            self,
            graphics: maprenderer.AbstractGraphics,
            tileRect: maprenderer.RectangleF, # Region to render in map coordinates
            tileSize: maprenderer.Size, # Pixel size of view to render to
            scale: float,
            styles: maprenderer.StyleSheet,
            imageCache: maprenderer.ImageCache,
            vectorCache: maprenderer.VectorObjectCache,
            mapLabelCache: maprenderer.MapLabelCache,
            worldLabelCache: maprenderer.WorldLabelCache,
            styleCache: maprenderer.DefaultStyleCache,
            options: maprenderer.MapOptions
            ) -> None:
        self._graphics = graphics
        self._tileRect = tileRect
        self._scale = scale
        self._options = options
        self._styles = styles
        self._imageCache = imageCache
        self._vectorCache = vectorCache
        self._mapLabelCache = mapLabelCache
        self._worldLabelCache = worldLabelCache
        self._styleCache = styleCache
        self._fontCache = maprenderer.FontCache(sheet=self._styles)
        self._clipCache = maprenderer.ClipPathCache()
        self._tileSize = tileSize
        self._selector = maprenderer.RectSelector(rect=self._tileRect)
        self._clipOutsectorBorders = True
        self._createLayers()
        self._updateSpaceTransforms()

    def setTileRect(self, rect: maprenderer.RectangleF) -> None:
        self._tileRect = rect
        self._selector.setRect(rect=self._tileRect)
        self._updateSpaceTransforms()

    def setClipOutsectorBorders(self, enable: bool) -> None:
        self._clipOutsectorBorders = enable

    def pixelSpaceToWorldSpace(self, pixel: maprenderer.Point, clamp: bool = True) -> maprenderer.PointF:
        world = self._worldSpaceToImageSpace.transform(pixel)

        if clamp:
            x = round(world.x + 0.5)
            y = round(world.y + (0.5 if x % 2 == 0 else 0))
            world = maprenderer.PointF(x, y)

        return world

    def render(self) -> None:
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

            RenderContext.LayerAction(maprenderer.LayerId.Micro_BordersFill, self._drawMicroBordersFill, clip=True),
            RenderContext.LayerAction(maprenderer.LayerId.Micro_BordersShade, self._drawMicroBordersShade, clip=True),
            RenderContext.LayerAction(maprenderer.LayerId.Micro_BordersStroke, self._drawMicroBordersStroke, clip=True),
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

        self._layers.sort(key=lambda l: self._styles.layerOrder[l.id])

    # TODO: I'm not sure about the use of the term world space
    # here. It comes from traveller map but as far as I can tell
    # it's actually dealing with map space
    def _updateSpaceTransforms(self):
        m = maprenderer.AbstractMatrix()
        m.translatePrepend(
            dx=-self._tileRect.left * self._scale * travellermap.ParsecScaleX,
            dy=-self._tileRect.top * self._scale * travellermap.ParsecScaleY)
        m.scalePrepend(
            sx=self._scale * travellermap.ParsecScaleX,
            sy=self._scale * travellermap.ParsecScaleY)
        self._imageSpaceToWorldSpace = maprenderer.AbstractMatrix(m)
        m.invert()
        self._worldSpaceToImageSpace = maprenderer.AbstractMatrix(m)

    def _drawBackground(self) -> None:
        self._graphics.setSmoothingMode(
            maprenderer.AbstractGraphics.SmoothingMode.HighSpeed)

        # TODO: Inefficient to create this every frame
        brush = maprenderer.AbstractBrush(self._styles.backgroundColor)

        # NOTE: This is a comment from the original Traveller Map source code
        # HACK: Due to limited precisions of floats, tileRect can end up not covering
        # the full bitmap when far from the origin.
        rect = maprenderer.RectangleF(self._tileRect)
        rect.inflate(rect.width * 0.1, rect.height * 0.1)
        self._graphics.drawRectangleFill(brush, rect)

    # TODO: When zooming in and out the background doesn't stay in a consistent
    # place between zoom levels. I think traveller map technically has the same
    # issue but it's nowhere near as noticeable as it only actually renders
    # tiles at a few zoom levels then uses digital zoom in the browser to scale
    # between those levels. The result being it doesn't jump around every zoom
    # step, it still does it at some zoom levels but it's far less noticeable.
    # I suspect I could do something in this function that effectively mimics
    # this behaviour
    def _drawNebulaBackground(self) -> None:
        if not self._styles.showNebulaBackground:
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
            ox = (-self._tileRect.left * self._scale * travellermap.ParsecScaleX) % w
            oy = (-self._tileRect.top * self._scale * travellermap.ParsecScaleY) % h
            if (ox > 0):
                ox -= w
            if (oy > 0):
                oy -= h

            # Number of copies needed to cover the canvas
            nx = 1 + int(math.floor(self._tileSize.width / w))
            ny = 1 + int(math.floor(self._tileSize.height / h))
            if (ox + nx * w < self._tileSize.width):
                nx += 1
            if (oy + ny * h < self._tileSize.height):
                ny += 1

            imageRect = maprenderer.RectangleF(x=ox, y=oy, width=w + 1, height=h + 1)
            for _ in range(nx):
                imageRect.y=oy
                for _ in range(ny):
                    self._graphics.drawImage(
                        self._imageCache.nebulaImage,
                        imageRect)
                    imageRect.y += h
                imageRect.x += w

    def _drawGalaxyBackground(self) -> None:
        if not self._styles.showGalaxyBackground:
            return

        if self._styles.deepBackgroundOpacity > 0 and \
            RenderContext._GalaxyImageRect.intersectsWith(self._tileRect):
            galaxyImage = \
                self._imageCache.galaxyImageGray \
                if self._styles.lightBackground else \
                self._imageCache.galaxyImage
            self._graphics.drawImageAlpha(
                self._styles.deepBackgroundOpacity,
                galaxyImage,
                RenderContext._GalaxyImageRect)

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
        if not self._styles.pseudoRandomStars.visible:
            return

        startX = math.floor(self._tileRect.left / RenderContext._PseudoRandomStarsChunkSize) * \
            RenderContext._PseudoRandomStarsChunkSize
        startY = math.floor(self._tileRect.top / RenderContext._PseudoRandomStarsChunkSize) * \
            RenderContext._PseudoRandomStarsChunkSize
        finishX = math.ceil(self._tileRect.right / RenderContext._PseudoRandomStarsChunkSize) * \
            RenderContext._PseudoRandomStarsChunkSize
        finishY = math.ceil(self._tileRect.bottom / RenderContext._PseudoRandomStarsChunkSize) * \
            RenderContext._PseudoRandomStarsChunkSize

        brush = maprenderer.AbstractBrush(self._styles.pseudoRandomStars.fillColor)
        rect = maprenderer.RectangleF()
        with self._graphics.save():
            self._graphics.setSmoothingMode(
                maprenderer.AbstractGraphics.SmoothingMode.HighQuality)

            for chunkLeft in range(startX, finishX + 1, RenderContext._PseudoRandomStarsChunkSize):
                for chunkTop in range(startY, finishY + 1, RenderContext._PseudoRandomStarsChunkSize):
                    rand = random.Random((chunkLeft << 8) ^ chunkTop)

                    starCount =  \
                        RenderContext._PseudoRandomStarsMaxPerChunk \
                        if self._scale >= 1 else \
                        int(RenderContext._PseudoRandomStarsMaxPerChunk / self._scale)

                    for _ in range(starCount):
                        rect.x = rand.random() * RenderContext._PseudoRandomStarsChunkSize + chunkLeft
                        rect.y = rand.random() * RenderContext._PseudoRandomStarsChunkSize + chunkTop
                        diameter = rand.random() * 2
                        rect.width = diameter / self._scale * travellermap.ParsecScaleX
                        rect.height = diameter / self._scale * travellermap.ParsecScaleY

                        self._graphics.drawEllipse(
                            pen=None,
                            brush=brush,
                            rect=rect)

    def _drawRifts(self) -> None:
        if not self._styles.showRiftOverlay:
            return

        if self._styles.riftOpacity > 0 and \
            RenderContext._RiftImageRect.intersectsWith(self._tileRect):
            self._graphics.drawImageAlpha(
                alpha=self._styles.riftOpacity,
                image=self._imageCache.riftImage,
                rect=self._RiftImageRect)

    def _drawMacroBorders(self) -> None:
        if not self._styles.macroBorders.visible:
            return

        self._graphics.setSmoothingMode(
                maprenderer.AbstractGraphics.SmoothingMode.AntiAlias)
        for vector in self._vectorCache.borders:
            if (vector.mapOptions & self._options & maprenderer.MapOptions.BordersMask) != 0:
                vector.draw(
                    graphics=self._graphics,
                    rect=self._tileRect,
                    pen=self._styles.macroBorders.pen)

    def _drawMacroRoutes(self) -> None:
        if not self._styles.macroRoutes.visible:
            return

        self._graphics.setSmoothingMode(
                maprenderer.AbstractGraphics.SmoothingMode.AntiAlias)
        for vector in self._vectorCache.routes:
            if (vector.mapOptions & self._options & maprenderer.MapOptions.BordersMask) != 0:
                vector.draw(
                    graphics=self._graphics,
                    rect=self._tileRect,
                    pen=self._styles.macroRoutes.pen)

    def _drawSectorGrid(self) -> None:
        if not self._styles.sectorGrid.visible:
            return

        self._graphics.setSmoothingMode(
                maprenderer.AbstractGraphics.SmoothingMode.HighSpeed)

        h = ((math.floor((self._tileRect.left) / travellermap.SectorWidth) - 1) - travellermap.ReferenceSectorX) * \
            travellermap.SectorWidth - travellermap.ReferenceHexX
        gridSlop = 10
        while h <= (self._tileRect.right + travellermap.SectorWidth):
            with self._graphics.save():
                self._graphics.translateTransform(dx=h, dy=0)
                self._graphics.scaleTransform(
                    scaleX=1 / travellermap.ParsecScaleX,
                    scaleY=1 / travellermap.ParsecScaleY)
                self._graphics.drawLine(
                    pen=self._styles.sectorGrid.pen,
                    pt1=maprenderer.PointF(0, self._tileRect.top - gridSlop),
                    pt2=maprenderer.PointF(0, self._tileRect.bottom + gridSlop))
            h += travellermap.SectorWidth

        v = ((math.floor((self._tileRect.top) / travellermap.SectorHeight) - 1) - travellermap.ReferenceSectorY) * \
            travellermap.SectorHeight - travellermap.ReferenceHexY
        while v <= (self._tileRect.bottom + travellermap.SectorHeight):
            self._graphics.drawLine(
                pen=self._styles.sectorGrid.pen,
                pt1=maprenderer.PointF(self._tileRect.left - gridSlop, v),
                pt2=maprenderer.PointF(self._tileRect.right + gridSlop, v))
            v += travellermap.SectorHeight

    def _drawSubsectorGrid(self) -> None:
        if not self._styles.subsectorGrid.visible:
            return

        self._graphics.setSmoothingMode(
                maprenderer.AbstractGraphics.SmoothingMode.HighSpeed)

        hmin = int(math.floor(self._tileRect.left / travellermap.SubsectorWidth) - 1 -
                   travellermap.ReferenceSectorX)
        hmax = int(math.ceil((self._tileRect.right + travellermap.SubsectorWidth +
                              travellermap.ReferenceHexX) / travellermap.SubsectorWidth))
        gridSlop = 10
        for hi in range(hmin, hmax + 1):
            if (hi % 4) == 0:
                continue
            h = hi * travellermap.SubsectorWidth - travellermap.ReferenceHexX
            self._graphics.drawLine(
                pen=self._styles.subsectorGrid.pen,
                pt1=maprenderer.PointF(h, self._tileRect.top - gridSlop),
                pt2=maprenderer.PointF(h, self._tileRect.bottom + gridSlop))
            with self._graphics.save():
                self._graphics.translateTransform(dx=h, dy=0)
                self._graphics.scaleTransform(
                    scaleX=1 / travellermap.ParsecScaleX,
                    scaleY=1 / travellermap.ParsecScaleY)
                self._graphics.drawLine(
                    pen=self._styles.subsectorGrid.pen,
                    pt1=maprenderer.PointF(0, self._tileRect.top - gridSlop),
                    pt2=maprenderer.PointF(0, self._tileRect.bottom + gridSlop))

        vmin = int(math.floor(self._tileRect.top / travellermap.SubsectorHeight) - 1 -
                   travellermap.ReferenceSectorY)
        vmax = int(math.ceil((self._tileRect.bottom + travellermap.SubsectorHeight +
                              travellermap.ReferenceHexY) / travellermap.SubsectorHeight))
        for vi in range(vmin, vmax + 1):
            if (vi % 4) == 0:
                continue
            v = vi * travellermap.SubsectorHeight - travellermap.ReferenceHexY
            self._graphics.drawLine(
                pen=self._styles.subsectorGrid.pen,
                pt1=maprenderer.PointF(self._tileRect.left - gridSlop, v),
                pt2=maprenderer.PointF(self._tileRect.right + gridSlop, v))

    def _drawParsecGrid(self) -> None:
        if not self._styles.parsecGrid.visible:
            return

        self._graphics.setSmoothingMode(
                maprenderer.AbstractGraphics.SmoothingMode.HighQuality)

        parsecSlop = 1

        hx = int(math.floor(self._tileRect.x))
        hw = int(math.ceil(self._tileRect.width))
        hy = int(math.floor(self._tileRect.y))
        hh = int(math.ceil(self._tileRect.height))

        pen = self._styles.parsecGrid.pen

        if self._styles.hexStyle == maprenderer.HexStyle.Square:
            rect = maprenderer.RectangleF()
            for px in range(hx - parsecSlop, hx + hw + parsecSlop):
                yOffset = 0 if ((px % 2) != 0) else 0.5
                for py in range(hy - parsecSlop, hy + hh + parsecSlop):
                    inset = 1
                    rect.x = px + inset
                    rect.y = py + inset + yOffset
                    rect.height = rect.width = 1 - inset * 2
                    self._graphics.drawRectangleOutline(pen=pen, rect=rect)
        elif self._styles.hexStyle == maprenderer.HexStyle.Hex:
            points = [maprenderer.PointF(), maprenderer.PointF(), maprenderer.PointF(), maprenderer.PointF()]
            for px in range(hx - parsecSlop, hx + hw + parsecSlop):
                yOffset = 0 if ((px % 2) != 0) else 0.5
                for py in range(hy - parsecSlop, hy + hh + parsecSlop):
                    points[0].x = px + -travellermap.HexWidthOffset
                    points[0].y = py + 0.5 + yOffset
                    points[1].x = px + travellermap.HexWidthOffset
                    points[1].y = py + 1.0 + yOffset
                    points[2].x = px + 1.0 - travellermap.HexWidthOffset
                    points[2].y = py + 1.0 + yOffset
                    points[3].x = px + 1.0 + travellermap.HexWidthOffset
                    points[3].y = py + 0.5 + yOffset
                    self._graphics.drawLines(pen, points)

        if self._styles.numberAllHexes and (self._styles.worldDetails & maprenderer.WorldDetails.Hex) != 0:
            solidBrush = maprenderer.AbstractBrush(self._styles.hexNumber.textColor)
            for px in range(hx - parsecSlop, hx + hw + parsecSlop):
                yOffset = 0 if ((px % 2) != 0) else 0.5
                for py in range(hy - parsecSlop, hy + hh + parsecSlop):

                    if self._styles.hexCoordinateStyle == maprenderer.HexCoordinateStyle.Subsector:
                        # TODO: Need to implement Subsector hex number. Not sure what this
                        # actually is
                        hex = 'TODO'
                    else:
                        relativePos = travellermap.absoluteSpaceToRelativeSpace((px + 1, py + 1))
                        hex = f'{relativePos[2]:02d}{relativePos[3]:02d}'

                    with self._graphics.save():
                        self._graphics.translateTransform(px + 0.5, py + yOffset)
                        self._graphics.scaleTransform(
                            self._styles.hexContentScale / travellermap.ParsecScaleX,
                            self._styles.hexContentScale / travellermap.ParsecScaleY)
                        self._graphics.drawString(
                            hex,
                            self._styles.hexNumber.font,
                            solidBrush,
                            0, 0,
                            maprenderer.StringAlignment.TopCenter)

    def _drawSubsectorNames(self) -> None:
        if not self._styles.subsectorNames.visible:
            return

        not self._graphics.setSmoothingMode(
                maprenderer.AbstractGraphics.SmoothingMode.HighQuality)
        brush = maprenderer.AbstractBrush(self._styles.subsectorNames.textColor)
        for sector in self._selector.sectors():
            for index, subsector in enumerate(sector.subsectors()):
                name = subsector.name()
                if not name:
                    continue

                ssx = index % 4
                ssy = index // 4
                centerX, centerY = travellermap.relativeSpaceToAbsoluteSpace((
                    sector.x(),
                    sector.y(),
                    int(travellermap.SubsectorWidth * (2 * ssx + 1) // 2),
                    int(travellermap.SubsectorHeight * (2 * ssy + 1) // 2)))
                _drawLabelHelper(
                    graphics=self._graphics,
                    text=subsector.name(),
                    center=maprenderer.PointF(x=centerX, y=centerY),
                    font=self._styles.subsectorNames.font,
                    brush=brush,
                    labelStyle=self._styles.subsectorNames.textStyle)

    def _drawMicroBordersFill(self) -> None:
        if not self._styles.microBorders.visible:
            return

        self._drawMicroBorders(RenderContext.BorderLayer.Regions)

        if self._styles.fillMicroBorders:
            self._drawMicroBorders(RenderContext.BorderLayer.Fill)

    def _drawMicroBordersShade(self) -> None:
        if not self._styles.microBorders.visible or not self._styles.shadeMicroBorders:
            return

        self._drawMicroBorders(RenderContext.BorderLayer.Shade)

    def _drawMicroBordersStroke(self) -> None:
        if not self._styles.microBorders.visible:
            return

        self._drawMicroBorders(RenderContext.BorderLayer.Stroke)

    def _drawMicroRoutes(self) -> None:
        if not self._styles.microRoutes.visible:
            return

        with self._graphics.save():
            self._graphics.setSmoothingMode(
                maprenderer.AbstractGraphics.SmoothingMode.AntiAlias)
            pen = maprenderer.AbstractPen(self._styles.microRoutes.pen)
            baseWidth = self._styles.microRoutes.pen.width

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
                    self._offsetRouteSegment(startPoint, endPoint, self._styles.routeEndAdjust)

                    routeColor = route.colour()
                    routeWidth = route.width()
                    routeStyle = self._styles.overrideLineStyle
                    if not routeStyle:
                        if route.style() is traveller.Route.Style.Solid:
                            routeStyle = maprenderer.LineStyle.Solid
                        elif route.style() is traveller.Route.Style.Dashed:
                            routeStyle = maprenderer.LineStyle.Dashed
                        elif route.style() is traveller.Route.Style.Dotted:
                            routeStyle = maprenderer.LineStyle.Dotted

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
                    if self._styles.grayscale and (not routeColor) and (not routeStyle):
                        routeStyle = maprenderer.LineStyle.Dashed

                    if not routeWidth:
                        routeWidth = 1.0
                    if not routeColor:
                        routeColor = self._styles.microRoutes.pen.color
                    if not routeStyle:
                        routeStyle = maprenderer.LineStyle.Solid

                    # Ensure color is visible
                    # TODO: Handle making colour visible
                    """
                    if (styles.grayscale || !ColorUtil.NoticeableDifference(routeColor.Value, styles.backgroundColor))
                        routeColor = styles.microRoutes.pen.color; // default
                    """

                    pen.color = routeColor
                    pen.width = routeWidth * baseWidth
                    pen.dashStyle = maprenderer.lineStyleToDashStyle(routeStyle)

                    self._graphics.drawLine(pen, startPoint, endPoint)

    _WrapPattern = re.compile(r'\s+(?![a-z])')
    def _drawMicroLabels(self) -> None:
        if not self._styles.showMicroNames:
            return

        with self._graphics.save():
            self._graphics.setSmoothingMode(
                maprenderer.AbstractGraphics.SmoothingMode.AntiAlias)

            solidBrush = maprenderer.AbstractBrush()
            for sector in self._selector.sectors():
                solidBrush.color = self._styles.microBorders.textColor

                for border in sector.borders():
                    label = border.label()
                    if not label and border.allegiance():
                        label = traveller.AllegianceManager.instance().allegianceName(
                            allegianceCode=border.allegiance(),
                            sectorName=sector.name())
                    if not label:
                        continue
                    if border.wrapLabel:
                        label = RenderContext._WrapPattern.sub('\n', label)

                    labelPos = border.labelHex()
                    if not labelPos:
                        continue
                    labelPos = RenderContext._hexToCenter(labelPos)
                    if border.labelOffsetX():
                        labelPos.x += border.labelOffsetX() * 0.7
                    if border.labelOffsetY():
                        labelPos.y -= border.labelOffsetY() * 0.7

                    _drawLabelHelper(
                        graphics=self._graphics,
                        text=label,
                        center=labelPos,
                        font=self._styles.microBorders.font,
                        brush=solidBrush,
                        labelStyle=self._styles.microBorders.textStyle)

                for label in sector.labels():
                    text = label.text()
                    if label.wrap():
                        text = RenderContext._WrapPattern.sub('\n', text)

                    labelPos = RenderContext._hexToCenter(label.hex())
                    # NOTE: This todo came in with the traveller map code
                    # TODO: Adopt some of the tweaks from .MSEC
                    if label.offsetX():
                        labelPos.x += label.offsetX() * 0.7
                    if label.offsetY():
                        labelPos.y -= label.offsetY() * 0.7

                    if label.size() is traveller.Label.Size.Small:
                        font = self._styles.microBorders.smallFont
                    elif label.size() is traveller.Label.Size.Large:
                        font = self._styles.microBorders.largeFont
                    else:
                        font = self._styles.microBorders.font

                    # TODO: Handle similar colours
                    solidBrush.color = label.colour() if label.colour() else travellermap.MapColours.TravellerAmber
                    """
                    if (!styles.grayscale &&
                        label.Color != null &&
                        ColorUtil.NoticeableDifference(label.Color.Value, styles.backgroundColor) &&
                        (label.Color != Label.DefaultColor))
                        solidBrush.Color = label.Color.Value;
                    else
                        solidBrush.Color = styles.microBorders.textColor;
                    """
                    _drawLabelHelper(
                        graphics=self._graphics,
                        text=text,
                        center=labelPos,
                        font=font,
                        brush=solidBrush,
                        labelStyle=self._styles.microBorders.textStyle)

    def _drawSectorNames(self) -> None:
        if not (self._styles.showSomeSectorNames or self._styles.showAllSectorNames):
            return

        if not self._styles.showAllSectorNames:
            # TODO: Add support for only showing selected sectors. I think
            # this happens when you zoom out a bit and it still shows some
            # sector names (Core, Ley) but not all
            return

        self._graphics.setSmoothingMode(
                maprenderer.AbstractGraphics.SmoothingMode.HighQuality)
        for sector in self._selector.sectors():
            # TODO: Traveller Map would use the sector label first and only
            # fall back to the name if if there was no label. I need to work out
            # where that label is being loaded from
            name = sector.name()

            centerX, centerY = travellermap.relativeSpaceToAbsoluteSpace((
                sector.x(),
                sector.y(),
                int(travellermap.SectorWidth // 2),
                int(travellermap.SectorHeight // 2)))

            _drawLabelHelper(
                graphics=self._graphics,
                text=name,
                center=maprenderer.PointF(x=centerX, y=centerY),
                font=self._styles.sectorName.font,
                brush=maprenderer.AbstractBrush(self._styles.sectorName.textColor),
                labelStyle=self._styles.sectorName.textStyle)

    def _drawMacroNames(self) -> None:
        if  not self._styles.macroNames.visible:
            return

        self._graphics.setSmoothingMode(
                maprenderer.AbstractGraphics.SmoothingMode.HighQuality)

        for vec in self._vectorCache.borders:
            if (vec.mapOptions & self._options & maprenderer.MapOptions.NamesMask) == 0:
                continue
            major = (vec.mapOptions & maprenderer.MapOptions.NamesMajor) != 0
            labelStyle = maprenderer.LabelStyle(uppercase=major)
            font = \
                self._styles.macroNames.font \
                if major else \
                self._styles.macroNames.smallFont
            solidBrush = maprenderer.AbstractBrush(
                self._styles.macroNames.textColor
                if major else
                self._styles.macroNames.textHighlightColor)
            vec.drawName(
                graphics=self._graphics,
                rect=self._tileRect,
                font=font,
                textBrush=solidBrush,
                labelStyle=labelStyle)

        for vec in self._vectorCache.rifts:
            major = (vec.mapOptions & maprenderer.MapOptions.NamesMajor) != 0
            labelStyle = maprenderer.LabelStyle(rotation=35, uppercase=major)
            font = \
                self._styles.macroNames.font \
                if major else \
                self._styles.macroNames.smallFont
            solidBrush = maprenderer.AbstractBrush(
                self._styles.macroNames.textColor
                if major else
                self._styles.macroNames.textHighlightColor)
            vec.drawName(
                graphics=self._graphics,
                rect=self._tileRect,
                font=font,
                textBrush=solidBrush,
                labelStyle=labelStyle)

        if self._styles.macroRoutes.visible:
            for vec in self._vectorCache.routes:
                if (vec.mapOptions & self._options & maprenderer.MapOptions.NamesMask) == 0:
                    continue
                major = (vec.mapOptions & maprenderer.MapOptions.NamesMajor) != 0
                labelStyle = maprenderer.LabelStyle(uppercase=major)
                font = \
                    self._styles.macroNames.font \
                    if major else \
                    self._styles.macroNames.smallFont
                solidBrush = maprenderer.AbstractBrush(
                    self._styles.macroRoutes.textColor
                    if major else
                    self._styles.macroRoutes.textHighlightColor)
                vec.drawName(
                    graphics=self._graphics,
                    rect=self._tileRect,
                    font=font,
                    textBrush=solidBrush,
                    labelStyle=labelStyle)

        if (self._options & maprenderer.MapOptions.NamesMinor) != 0:
            for label in self._mapLabelCache.minorLabels:
                font = self._styles.macroNames.smallFont if label.minor else self._styles.macroNames.mediumFont
                solidBrush = maprenderer.AbstractBrush(
                    self._styles.macroRoutes.textColor
                    if label.minor else
                    self._styles.macroRoutes.textHighlightColor)
                with self._graphics.save():
                    self._graphics.translateTransform(
                        dx=label.position.x,
                        dy=label.position.y)
                    self._graphics.scaleTransform(
                        scaleX=1.0 / travellermap.ParsecScaleX,
                        scaleY=1.0 / travellermap.ParsecScaleY)
                    maprenderer.drawStringHelper(
                        graphics=self._graphics,
                        text=label.text,
                        font=font,
                        brush=solidBrush,
                        x=0, y=0)

    def _drawCapitalsAndHomeWorlds(self) -> None:
        if (not self._styles.capitals.visible) or \
            ((self._options & maprenderer.MapOptions.WorldsMask) == 0):
            return

        with self._graphics.save():
            self._graphics.setSmoothingMode(
                maprenderer.AbstractGraphics.SmoothingMode.HighQuality)
            solidBrush = maprenderer.AbstractBrush(self._styles.capitals.textColor)
            for worldLabel in self._worldLabelCache.labels:
                if (worldLabel.mapOptions & self._options) != 0:
                    worldLabel.paint(
                        graphics=self._graphics,
                        dotColor=self._styles.capitals.fillColor,
                        labelBrush=solidBrush,
                        labelFont=self._styles.macroNames.smallFont)

    def _drawMegaLabels(self) -> None:
        if not self._styles.megaNames.visible:
            return

        self._graphics.setSmoothingMode(
                maprenderer.AbstractGraphics.SmoothingMode.HighQuality)
        solidBrush = maprenderer.AbstractBrush(self._styles.megaNames.textColor)
        for label in self._mapLabelCache.megaLabels:
            with self._graphics.save():
                font = self._styles.megaNames.smallFont if label.minor else self._styles.megaNames.font
                self._graphics.translateTransform(
                    dx=label.position.x,
                    dy=label.position.y)
                self._graphics.scaleTransform(
                    scaleX=1.0 / travellermap.ParsecScaleX,
                    scaleY=1.0 / travellermap.ParsecScaleY)
                maprenderer.drawStringHelper(
                    graphics=self._graphics,
                    text=label.text,
                    font=font,
                    brush=solidBrush,
                    x=0, y=0)

    def _drawWorldsBackground(self) -> None:
        if not self._styles.worlds.visible or self._styles.showStellarOverlay:
            return

        for world in self._selector.worlds():
            self._drawWorld(
                world=world,
                layer=RenderContext.WorldLayer.Background)

    def _drawWorldsForeground(self) -> None:
        if not self._styles.worlds.visible or self._styles.showStellarOverlay:
            return

        for world in self._selector.worlds():
            self._drawWorld(
                world=world,
                layer=RenderContext.WorldLayer.Foreground)

    def _drawWorldsOverlay(self) -> None:
        if not self._styles.worlds.visible:
            return

        with self._graphics.save():
            self._graphics.setSmoothingMode(
                maprenderer.AbstractGraphics.SmoothingMode.HighQuality)
            if self._styles.showStellarOverlay:
                for world in self._selector.worlds():
                    self._drawStars(world)
            elif self._styles.hasWorldOverlays:
                slop = self._selector.slop()
                self._selector.setSlop(max(slop, math.log(self._scale, 2.0) - 4))
                try:
                    for world in self._selector.worlds():
                        self._drawWorld(
                            world=world,
                            layer=RenderContext.WorldLayer.Overlay)
                finally:
                    self._selector.setSlop(slop)

    def _drawDroyneOverlay(self) -> None:
        if not self._styles.droyneWorlds.visible:
            return

        self._graphics.setSmoothingMode(
                maprenderer.AbstractGraphics.SmoothingMode.HighQuality)
        solidBrush = maprenderer.AbstractBrush(self._styles.droyneWorlds.textColor)
        for world in self._selector.worlds():
            allegiance = world.allegiance()

            droyne = allegiance == 'Dr' or allegiance == 'NaDr' or world.hasRemark('Droy')
            chirpers = world.hasRemark('Chir')

            if droyne or chirpers:
                glyph = self._styles.droyneWorlds.content[0 if droyne else 1]
                self._drawOverlayGlyph(
                    glyph=glyph,
                    font=self._styles.droyneWorlds.font,
                    brush=solidBrush,
                    position=world.hex())

    def _drawMinorHomeworldOverlay(self) -> None:
        if not self._styles.minorHomeWorlds.visible:
            return

        self._graphics.setSmoothingMode(
                maprenderer.AbstractGraphics.SmoothingMode.HighQuality)
        solidBrush = maprenderer.AbstractBrush(self._styles.minorHomeWorlds.textColor)
        for world in self._selector.worlds():
            if world.isMinorHomeworld():
                self._drawOverlayGlyph(
                    glyph=self._styles.minorHomeWorlds.content,
                    font=self._styles.minorHomeWorlds.font,
                    brush=solidBrush,
                    position=world.hex())

    def _drawAncientWorldsOverlay(self) -> None:
        if not self._styles.ancientsWorlds.visible:
            return

        self._graphics.setSmoothingMode(
                maprenderer.AbstractGraphics.SmoothingMode.HighQuality)
        solidBrush = maprenderer.AbstractBrush(self._styles.ancientsWorlds.textColor)
        for world in self._selector.worlds():
            if world.hasTradeCode(traveller.TradeCode.AncientsSiteWorld):
                self._drawOverlayGlyph(
                    glyph=self._styles.ancientsWorlds.content,
                    font=self._styles.ancientsWorlds.font,
                    brush=solidBrush,
                    position=world.hex())

    def _drawSectorReviewStatusOverlay(self) -> None:
        solidBrush = maprenderer.AbstractBrush()

        if self._styles.dimUnofficialSectors and self._styles.worlds.visible:
            solidBrush.color = maprenderer.makeAlphaColor(
                alpha=128,
                color=self._styles.backgroundColor)
            for sector in self._selector.sectors():
                if not sector.hasTag('Official') and not sector.hasTag('Preserve') and not sector.hasTag('InReview'):
                    clipPath = self._clipCache.sectorClipPath(
                        sectorX=sector.x(),
                        sectorY=sector.y(),
                        pathType=maprenderer.ClipPathCache.PathType.Hex)

                    self._graphics.drawPathFill(
                        brush=solidBrush,
                        path=clipPath)

        if self._styles.colorCodeSectorStatus and self._styles.worlds.visible:
            for sector in self._selector.sectors():
                if sector.hasTag('Official'):
                    solidBrush.color = maprenderer.makeAlphaColor(
                        alpha=128,
                        color=travellermap.MapColours.TravellerRed)
                elif sector.hasTag('InReview'):
                    solidBrush.color = maprenderer.makeAlphaColor(
                        alpha=128,
                        color=travellermap.MapColours.Orange)
                elif sector.hasTag('Unreviewed'):
                    solidBrush.color = maprenderer.makeAlphaColor(
                        alpha=128,
                        color=travellermap.MapColours.TravellerAmber)
                elif sector.hasTag('Apocryphal'):
                    solidBrush.color = maprenderer.makeAlphaColor(
                        alpha=128,
                        color=travellermap.MapColours.Magenta)
                elif sector.hasTag('Preserve'):
                    solidBrush.color = maprenderer.makeAlphaColor(
                        alpha=128,
                        color=travellermap.MapColours.TravellerGreen)
                else:
                    continue

                clipPath = self._clipCache.sectorClipPath(
                    sectorX=sector.x(),
                    sectorY=sector.y(),
                    pathType=maprenderer.ClipPathCache.PathType.Hex)

                self._graphics.drawPathFill(
                    brush=solidBrush,
                    path=clipPath)

    def _drawWorld(self, world: traveller.World, layer: WorldLayer) -> None:
        uwp = world.uwp()
        isPlaceholder = False # TODO: Handle placeholder worlds
        isCapital = maprenderer.WorldHelper.isCapital(world)
        isHiPop = maprenderer.WorldHelper.isHighPopulation(world)
        renderName = ((self._styles.worldDetails & maprenderer.WorldDetails.AllNames) != 0) or \
            (((self._styles.worldDetails & maprenderer.WorldDetails.KeyNames) != 0) and (isCapital or isHiPop))
        renderUWP = (self._styles.worldDetails & maprenderer.WorldDetails.Uwp) != 0

        with self._graphics.save():
            self._graphics.setSmoothingMode(
                maprenderer.AbstractGraphics.SmoothingMode.AntiAlias)

            center = RenderContext._hexToCenter(world.hex())

            self._graphics.translateTransform(
                dx=center.x,
                dy=center.y)
            self._graphics.scaleTransform(
                scaleX=self._styles.hexContentScale / travellermap.ParsecScaleX,
                scaleY=self._styles.hexContentScale / travellermap.ParsecScaleY)
            self._graphics.rotateTransform(
                degrees=self._styles.hexRotation)

            if layer is RenderContext.WorldLayer.Overlay:
                if self._styles.populationOverlay.visible and (world.population() > 0):
                    self._drawOverlay(
                        element=self._styles.populationOverlay,
                        radius=math.sqrt(world.population() / math.pi) * 0.00002)

                if self._styles.importanceOverlay.visible:
                    # TODO: Handle importance overlay
                    """
                    int im = world.CalculatedImportance;
                    if (im > 0)
                    {
                        DrawOverlay(styles.importanceOverlay, (im - 0.5f) * Astrometrics.ParsecScaleX, ref solidBrush, ref pen);
                    }
                    """

                if self._styles.capitalOverlay.visible:
                    # TODO: Handle capital overlay
                    """
                    bool hasIm = world.CalculatedImportance >= 4;
                    bool hasCp = world.IsCapital;

                    if (hasIm && hasCp)
                        DrawOverlay(styles.capitalOverlay, 2 * Astrometrics.ParsecScaleX, ref solidBrush, ref pen);
                    else if (hasIm)
                        DrawOverlay(styles.capitalOverlayAltA, 2 * Astrometrics.ParsecScaleX, ref solidBrush, ref pen);
                    else if (hasCp)
                        DrawOverlay(styles.capitalOverlayAltB, 2 * Astrometrics.ParsecScaleX, ref solidBrush, ref pen);
                    """

                # TODO: Not sure if I need to bother with highlight pattern stuff. It
                # doesn't look like it's used in tile rendering (just image rendering)
                """
                if (styles.highlightWorlds.visible && styles.highlightWorldsPattern!.Matches(world))
                {
                    DrawOverlay(styles.highlightWorlds, Astrometrics.ParsecScaleX, ref solidBrush, ref pen);
                }
                """

            if not self._styles.useWorldImages:
                # Normal (non-"Eye Candy") styles
                if layer is RenderContext.WorldLayer.Background:
                    if (self._styles.worldDetails & maprenderer.WorldDetails.Zone) != 0:
                        elem = self._zoneStyle(world)
                        if elem and elem.visible:
                            if self._styles.showZonesAsPerimeters:
                                with self._graphics.save():
                                    # TODO: Why is this 2 separate scale transforms?
                                    self._graphics.scaleTransform(
                                        scaleX=travellermap.ParsecScaleX,
                                        scaleY=travellermap.ParsecScaleY)
                                    self._graphics.scaleTransform(
                                        scaleX=0.95,
                                        scaleY=0.95)
                                    self._graphics.drawPathOutline(
                                        pen=elem.pen,
                                        path=RenderContext._HexPath)
                            else:
                                if elem.fillColor:
                                    self._graphics.drawEllipse(
                                        brush=maprenderer.AbstractBrush(elem.fillColor),
                                        pen=None,
                                        rect=maprenderer.RectangleF(x=-0.4, y=-0.4, width=0.8, height=0.8))
                                if elem.pen.color:
                                    if renderName and self._styles.fillMicroBorders:
                                        # TODO: Is saving the state actually needed here?
                                        with self._graphics.save():
                                            self._graphics.intersectClipRect(
                                                rect=maprenderer.RectangleF(
                                                    x=-0.5,
                                                    y=-0.5,
                                                    width=1,
                                                    height=0.65 if renderUWP else 0.75))
                                            self._graphics.drawEllipse(
                                                pen=elem.pen,
                                                brush=None,
                                                rect=maprenderer.RectangleF(
                                                    x=-0.4,
                                                    y=-0.4,
                                                    width=0.8,
                                                    height=0.8))
                                    else:
                                        self._graphics.drawEllipse(
                                            pen=elem.pen,
                                            brush=None,
                                            rect=maprenderer.RectangleF(
                                                x=-0.4,
                                                y=-0.4,
                                                width=0.8,
                                                height=0.8))

                    if not self._styles.numberAllHexes and \
                        ((self._styles.worldDetails & maprenderer.WorldDetails.Hex) != 0):

                        hex = world.hex()
                        if self._styles.hexContentScale is maprenderer.HexCoordinateStyle.Subsector:
                            # TODO: Handle subsector hex whatever that is
                            #hex=f'{hex.offsetX():02d}{hex.offsetY():02d}'
                            hex='TODO'
                        else:
                            hex=f'{hex.offsetX():02d}{hex.offsetY():02d}'
                        self._graphics.drawString(
                            text=hex,
                            font=self._styles.hexNumber.font,
                            brush=maprenderer.AbstractBrush(self._styles.hexNumber.textColor),
                            x=self._styles.hexNumber.position.x,
                            y=self._styles.hexNumber.position.y,
                            format=maprenderer.StringAlignment.TopCenter)

                if layer is RenderContext.WorldLayer.Foreground:
                    elem = self._zoneStyle(world)
                    worldTextBackgroundStyle = \
                        maprenderer.TextBackgroundStyle.NoStyle \
                        if (not elem or not elem.fillColor) else \
                        self._styles.worlds.textBackgroundStyle

                    # TODO: Implement placeholders, this should be
                    # if (!isPlaceholder)
                    if True:
                        if ((self._styles.worldDetails & maprenderer.WorldDetails.GasGiant) != 0) and \
                            maprenderer.WorldHelper.hasGasGiants(world):
                            self._drawGasGiant(
                                self._styles.worlds.textColor,
                                self._styles.gasGiantPosition.x,
                                self._styles.gasGiantPosition.y,
                                0.05,
                                self._styles.showGasGiantRing)

                        if (self._styles.worldDetails & maprenderer.WorldDetails.Starport) != 0:
                            starport = uwp.code(traveller.UWP.Element.StarPort)
                            if self._styles.showTL:
                                starport += "-" + uwp.code(traveller.UWP.Element.TechLevel)
                            self._drawWorldLabel(
                                backgroundStyle=worldTextBackgroundStyle,
                                brush=maprenderer.AbstractBrush(self._styles.uwp.fillColor),
                                color=self._styles.worlds.textColor,
                                position=self._styles.starport.position,
                                font=self._styles.starport.font,
                                text=starport)

                        if renderUWP:
                            self._drawWorldLabel(
                                backgroundStyle=self._styles.uwp.textBackgroundStyle,
                                brush=maprenderer.AbstractBrush(self._styles.uwp.fillColor),
                                color=self._styles.uwp.textColor,
                                position=self._styles.uwp.position,
                                font=self._styles.hexNumber.font,
                                text=uwp.string())

                        # NOTE: This todo came in with the traveller map code
                        # TODO: Mask off background for glyphs
                        if (self._styles.worldDetails & maprenderer.WorldDetails.Bases) != 0:
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
                                    pt = self._styles.baseTopPosition
                                    if glyph.bias is maprenderer.Glyph.GlyphBias.Bottom and \
                                        not self._styles.ignoreBaseBias:
                                        pt = self._styles.baseBottomPosition
                                        bottomUsed = True

                                    brush = maprenderer.AbstractBrush(
                                        self._styles.worlds.textHighlightColor
                                        if glyph.highlight else
                                        self._styles.worlds.textColor)
                                    _drawGlyphHelper(
                                        graphics=self._graphics,
                                        glyph=glyph,
                                        fonts=self._fontCache,
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
                                    solidBrush.color = \
                                        self._styles.worlds.textHighlightColor \
                                        if glyph.isHighlighted else \
                                        self._styles.worlds.textColor
                                    drawGlyphHelper(
                                        graphics=self._graphics,
                                        glyph=glyph,
                                        fonts=self._fontCache,
                                        brush=solidBrush,
                                        position=pt)

                            # Base 3 (!)
                            if baseCount > 2:
                                glyph = maprenderer.GlyphDefs.fromBaseCode(world.legacyAllegiance, bases[2])
                                if glyph.isPrintable:
                                    solidBrush.color = \
                                        self._styles.worlds.textHighlightColor \
                                        if glyph.isHighlighted else \
                                        self._styles.worlds.textColor
                                    drawGlyphHelper(
                                        graphics=self._graphics,
                                        glyph=glyph,
                                        fonts=self._fontCache,
                                        brush=solidBrush,
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
                                solidBrush.color = \
                                    self._styles.worlds.textHighlightColor \
                                    if glyph.isHighlighted else \
                                    self._styles.worlds.textColor
                                drawGlyphHelper(
                                    graphics=self._graphics,
                                    glyph=glyph,
                                    fonts=self._fontCache,
                                    brush=solidBrush,
                                    position=self._styles.baseMiddlePosition)
                            """

                    if (self._styles.worldDetails & maprenderer.WorldDetails.Type) != 0:
                        # TODO: Handle placeholders, this should be
                        # if (isPlaceholder)
                        if False:
                            e = self._styles.anomaly if world.isAnomaly() else self._styles.placeholder
                            self._drawWorldLabel(
                                backgroundStyle=e.textBackgroundStyle,
                                brush=AbstractBrush(self._styles.worlds.textColor),
                                color=e.textColor,
                                position=e.position,
                                font=e.font,
                                text=e.content)
                        else:
                            with self._graphics.save():
                                self._graphics.translateTransform(
                                    dx=self._styles.discPosition.x,
                                    dy=self._styles.discPosition.y)
                                if uwp.numeric(element=traveller.UWP.Element.WorldSize, default=-1) <= 0:
                                    if (self._styles.worldDetails & maprenderer.WorldDetails.Asteroids) != 0:
                                        # Basic pattern, with probability varying per position:
                                        #   o o o
                                        #  o o o o
                                        #   o o o

                                        lpx = [-2, 0, 2, -3, -1, 1, 3, -2, 0, 2]
                                        lpy = [-2, -2, -2, 0, 0, 0, 0, 2, 2, 2]
                                        lpr = [0.5, 0.9, 0.5, 0.6, 0.9, 0.9, 0.6, 0.5, 0.9, 0.5]

                                        brush = maprenderer.AbstractBrush(self._styles.worlds.textColor)

                                        # Random generator is seeded with world location so it is always the same
                                        rand = random.Random(world.hex().absoluteX() ^ world.hex().absoluteY())
                                        rect = maprenderer.RectangleF()
                                        for i in range(len(lpx)):
                                            if rand.random() < lpr[i]:
                                                rect.x = lpx[i] * 0.035
                                                rect.y = lpy[i] * 0.035

                                                rect.width = 0.04 + rand.random() * 0.03
                                                rect.height = 0.04 + rand.random() * 0.03

                                                # If necessary, add jitter here
                                                #rect.x += 0
                                                #rect.y += 0

                                                self._graphics.drawEllipse(
                                                    brush=brush,
                                                    pen=None,
                                                    rect=rect)
                                    else:
                                        # Just a glyph
                                        _drawGlyphHelper(
                                            graphics=self._graphics,
                                            glyph=maprenderer.GlyphDefs.DiamondX,
                                            fonts=self._fontCache,
                                            brush=maprenderer.AbstractBrush(self._styles.worlds.textColor),
                                            pt=maprenderer.PointF(0, 0))
                                else:
                                    penColor, brushColor = self._styles.worldColors(world)
                                    brush = maprenderer.AbstractBrush(brushColor) if brushColor else None
                                    pen = maprenderer.AbstractPen(self._styles.worldWater.pen) if penColor else None
                                    if pen:
                                        pen.color = penColor
                                    self._graphics.drawEllipse(
                                        pen=pen,
                                        brush=brush,
                                        rect=maprenderer.RectangleF(
                                            x=-self._styles.discRadius,
                                            y=-self._styles.discRadius,
                                            width=2 * self._styles.discRadius,
                                            height=2 * self._styles.discRadius))
                    elif not world.isAnomaly():
                        # Dotmap
                        self._graphics.drawEllipse(
                            brush=maprenderer.AbstractBrush(self._styles.worlds.textColor),
                            pen=None,
                            rect=maprenderer.RectangleF(
                                x=-self._styles.discRadius,
                                y=-self._styles.discRadius,
                                width=2 * self._styles.discRadius,
                                height=2 * self._styles.discRadius))

                    if renderName:
                        name = world.name()
                        highlight = (self._styles.worldDetails & maprenderer.WorldDetails.Highlight) != 0
                        if (isHiPop and highlight) or \
                            self._styles.worlds.textStyle.uppercase:
                            name = name.upper()

                        textColor = \
                            self._styles.worlds.textHighlightColor \
                            if isCapital and highlight else \
                            self._styles.worlds.textColor
                        font = \
                            self._styles.worlds.largeFont \
                            if (isHiPop or isCapital) and highlight else \
                            self._styles.worlds.font

                        self._drawWorldLabel(
                            backgroundStyle=worldTextBackgroundStyle,
                            brush=maprenderer.AbstractBrush(self._styles.worlds.textColor),
                            color=textColor,
                            position=self._styles.worlds.textStyle.translation,
                            font=font,
                            text=name)

                    if (self._styles.worldDetails & maprenderer.WorldDetails.Allegiance) != 0:
                        alleg = maprenderer.WorldHelper.allegianceCode(
                            world=world,
                            ignoreDefault=True,
                            useLegacy=not self._styles.t5AllegianceCodes)
                        if alleg:
                            if self._styles.lowerCaseAllegiance:
                                alleg = alleg.lower()

                            self._graphics.drawString(
                                text=alleg,
                                font=self._styles.worlds.smallFont,
                                brush=maprenderer.AbstractBrush(self._styles.worlds.textColor),
                                x=self._styles.allegiancePosition.x,
                                y=self._styles.allegiancePosition.y,
                                format=maprenderer.StringAlignment.Centered)
            else: # styles.useWorldImages
                # "Eye-Candy" style
                worldSize = world.physicalSize()
                imageRadius = (0.6 if worldSize <= 0 else (0.3 * (worldSize / 5.0 + 0.2))) / 2
                decorationRadius = imageRadius

                if layer is RenderContext.WorldLayer.Background:
                    if (self._styles.worldDetails & maprenderer.WorldDetails.Type) != 0:
                        # TODO: Handle placeholders, this should be
                        #if isPlaceholder:
                        if False:
                            e = self._styles.anomaly if world.isAnomaly() else self._styles.placeholder
                            self._drawWorldLabel(
                                backgroundStyle=e.textBackgroundStyle,
                                brush=AbstractBrush(self._styles.worlds.textColor),
                                color=e.textColor,
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
                                rect=maprenderer.RectangleF(
                                    x=-imageRadius * scaleX,
                                    y=-imageRadius * scaleY,
                                    width=imageRadius * 2 * scaleX,
                                    height=imageRadius * 2 * scaleY))
                    elif not world.isAnomaly():
                        # Dotmap
                        self._graphics.drawEllipse(
                            brush=maprenderer.AbstractBrush(self._styles.worlds.textColor),
                            pen=None,
                            rect=maprenderer.RectangleF(
                                x=-self._styles.discRadius,
                                y=-self._styles.discRadius,
                                width=2 * self._styles.discRadius,
                                height=2 * self._styles.discRadius))

                # TODO: Support placeholders, this should be
                # if (isPlaceholder)
                if False:
                    return

                if layer is RenderContext.WorldLayer.Foreground:
                    decorationRadius += 0.1

                    if (self._styles.worldDetails & maprenderer.WorldDetails.Zone) != 0:
                        zone = world.zone()
                        if zone is traveller.ZoneType.AmberZone or zone is traveller.ZoneType.RedZone:
                            pen = \
                                self._styles.amberZone.pen \
                                if zone is traveller.ZoneType.AmberZone else \
                                self._styles.redZone.pen
                            rect = maprenderer.RectangleF(
                                x=-decorationRadius,
                                y=-decorationRadius,
                                width=decorationRadius * 2,
                                height=decorationRadius * 2)

                            self._graphics.drawArc(
                                pen=pen,
                                rect=rect,
                                startDegrees=5,
                                sweepDegrees=80)
                            self._graphics.drawArc(
                                pen=pen,
                                rect=rect,
                                startDegrees=95,
                                sweepDegrees=80)
                            self._graphics.drawArc(
                                pen=pen,
                                rect=rect,
                                startDegrees=185,
                                sweepDegrees=80)
                            self._graphics.drawArc(
                                pen=pen,
                                rect=rect,
                                startDegrees=275,
                                sweepDegrees=80)
                            decorationRadius += 0.1

                    if (self._styles.worldDetails & maprenderer.WorldDetails.GasGiant) != 0:
                        symbolRadius = 0.05
                        if self._styles.showGasGiantRing:
                            decorationRadius += symbolRadius
                        self._drawGasGiant(
                            color=self._styles.worlds.textHighlightColor,
                            x=decorationRadius,
                            y=0,
                            radius=symbolRadius,
                            ring=self._styles.showGasGiantRing)
                        decorationRadius += 0.1

                    if renderUWP:
                        # NOTE: This todo came in with the traveller map code
                        # TODO: Scale, like the name text.
                        self._graphics.drawString(
                            text=uwp.string(),
                            font=self._styles.hexNumber.font,
                            brush=maprenderer.AbstractBrush(self._styles.worlds.textColor),
                            x=decorationRadius,
                            y=self._styles.uwp.position.y,
                            format=maprenderer.StringAlignment.CenterLeft)

                    if renderName:
                        name = world.name()
                        if isHiPop:
                            name.upper()

                        with self._graphics.save():
                            highlight = (self._styles.worldDetails & maprenderer.WorldDetails.Highlight) != 0
                            textColor = \
                                self._styles.worlds.textHighlightColor \
                                if isCapital and highlight else \
                                self._styles.worlds.textColor

                            if self._styles.worlds.textStyle.uppercase:
                                name = name.upper()

                            self._graphics.translateTransform(
                                dx=decorationRadius,
                                dy=0.0)
                            self._graphics.scaleTransform(
                                scaleX=self._styles.worlds.textStyle.scale.width,
                                scaleY=self._styles.worlds.textStyle.scale.height)
                            self._graphics.translateTransform(
                                dx=self._graphics.measureString(
                                    text=name,
                                    font=self._styles.worlds.font).width / 2,
                                dy=0.0) # Left align

                            self._drawWorldLabel(
                                backgroundStyle=self._styles.worlds.textBackgroundStyle,
                                brush=maprenderer.AbstractBrush(self._styles.worlds.textColor),
                                color=textColor,
                                position=self._styles.worlds.textStyle.translation,
                                font=self._styles.worlds.font,
                                text=name)

    def _drawWorldLabel(
            self,
            backgroundStyle: maprenderer.TextBackgroundStyle,
            brush: maprenderer.AbstractBrush,
            color: str,
            position: maprenderer.PointF,
            font: maprenderer.AbstractFont,
            text: str
            ) -> None:
        size = self._graphics.measureString(text=text, font=font)

        if backgroundStyle is maprenderer.TextBackgroundStyle.Rectangle:
            if not self._styles.fillMicroBorders:
                # NOTE: This todo came over from traveller map
                # TODO: Implement this with a clipping region instead
                self._graphics.drawRectangleFill(
                    brush=maprenderer.AbstractBrush(self._styles.backgroundColor),
                    rect=maprenderer.RectangleF(
                        x=position.x - size.width / 2,
                        y=position.y - size.height / 2,
                        width=size.width,
                        height=size.height))
        elif backgroundStyle is maprenderer.TextBackgroundStyle.Filled:
            self._graphics.drawRectangleFill(
                brush=brush,
                rect=maprenderer.RectangleF(
                    x=position.x - size.width / 2,
                    y=position.y - size.height / 2,
                    width=size.width,
                    height=size.height))
        elif backgroundStyle is maprenderer.TextBackgroundStyle.Outline or \
            backgroundStyle is maprenderer.TextBackgroundStyle.Shadow:
            # NOTE: This todo came over from traveller map
            # TODO: These scaling factors are constant for a render; compute once

            # Invert the current scaling transforms
            sx = 1.0 / self._styles.hexContentScale
            sy = 1.0 / self._styles.hexContentScale
            sx *= travellermap.ParsecScaleX
            sy *= travellermap.ParsecScaleY
            sx /= self._scale * travellermap.ParsecScaleX
            sy /= self._scale * travellermap.ParsecScaleY

            outlineSize = 2
            outlineSkip = 1

            outlineStart = -outlineSize if backgroundStyle is maprenderer.TextBackgroundStyle.Outline else 0
            brush = maprenderer.AbstractBrush(self._styles.backgroundColor)

            dx = outlineStart
            while dx <= outlineSize:
                dy = outlineStart
                while dy <= outlineSize:
                    self._graphics.drawString(
                        text=text,
                        font=font,
                        brush=brush,
                        x=position.x + sx * dx,
                        y=position.y + sy * dy,
                        format=maprenderer.StringAlignment.Centered)
                    dy += outlineSkip
                dx += outlineSkip

        self._graphics.drawString(
            text=text,
            font=font,
            brush=maprenderer.AbstractBrush(color),
            x=position.x,
            y=position.y,
            format=maprenderer.StringAlignment.Centered)

    def _drawStars(self, world: traveller.World) -> None:
        with self._graphics.save():
            self._graphics.setSmoothingMode(
                maprenderer.AbstractGraphics.SmoothingMode.AntiAlias)
            center = self._hexToCenter(world.hex())

            self._graphics.translateTransform(dx=center.x, dy=center.y)
            self._graphics.scaleTransform(
                scaleX=self._styles.hexContentScale / travellermap.ParsecScaleX,
                scaleY=self._styles.hexContentScale / travellermap.ParsecScaleY)

            solidBrush = maprenderer.AbstractBrush()
            pen = maprenderer.AbstractPen()
            for i, (fillColour, lineColor, radius) in enumerate(RenderContext._worldStarProps(world=world)):
                solidBrush.color = fillColour
                pen.color = lineColor
                pen.dashStyle = maprenderer.DashStyle.Solid
                pen.width = self._styles.worlds.pen.width
                offset = RenderContext._starOffset(i)
                offsetScale = 0.3
                radius *= 0.15
                self._graphics.drawEllipse(
                    pen=pen,
                    brush=solidBrush,
                    rect=maprenderer.RectangleF(
                        x=offset.x * offsetScale - radius,
                        y=offset.y * offsetScale - radius,
                        width=radius * 2,
                        height=radius * 2))

    def _drawGasGiant(
            self,
            color: str,
            x: float,
            y: float,
            radius: float,
            ring: bool
            ) -> None:
        with self._graphics.save():
            self._graphics.translateTransform(dx=x, dy=y)
            self._graphics.drawEllipse(
                brush=maprenderer.AbstractBrush(color),
                pen=None,
                rect=maprenderer.RectangleF(
                    x=-radius,
                    y=-radius,
                    width=radius * 2,
                    height=radius * 2))

            if ring:
                self._graphics.rotateTransform(degrees=-30)
                self._graphics.drawEllipse(
                    pen=maprenderer.AbstractPen(color=color, width=radius / 4),
                    brush=None,
                    rect=maprenderer.RectangleF(
                        x=-radius * 1.75,
                        y=-radius * 0.4,
                        width=radius * 1.75 * 2,
                        height=radius * 0.4 * 2))

    def _drawOverlay(
            self,
            element: maprenderer.StyleSheet.StyleElement,
            radius: float
            ) -> None:
        # Prevent "Out of memory" exception when rendering to GDI+.
        if radius < 0.001:
            return

        self._graphics.drawEllipse(
            pen=element.pen,
            brush=maprenderer.AbstractBrush(element.fillColor),
            rect=maprenderer.RectangleF(x=-radius, y=-radius, width=radius * 2, height=radius * 2))

    def _drawMicroBorders(self, layer: BorderLayer) -> None:
        fillAlpha = 64
        shadeAlpha = 128

        self._graphics.setSmoothingMode(
                maprenderer.AbstractGraphics.SmoothingMode.HighQuality)

        pathType = \
            maprenderer.ClipPathCache.PathType.Square \
            if self._styles.microBorderStyle == maprenderer.MicroBorderStyle.Square else \
            maprenderer.ClipPathCache.PathType.Hex

        solidBrush = maprenderer.AbstractBrush()
        pen = maprenderer.AbstractPen(self._styles.microBorders.pen) # TODO: Color.Empty)

        penWidth = pen.width
        for sector in self._selector.sectors():
            # This looks craptacular for Candy style borders :(
            shouldClip = self._clipOutsectorBorders and \
                ((layer == RenderContext.BorderLayer.Fill) or \
                    (self._styles.microBorderStyle != maprenderer.MicroBorderStyle.Curve))
            clip = None
            if shouldClip:
                clip = self._clipCache.sectorClipPath(
                    sectorX=sector.x(),
                    sectorY=sector.y(),
                    pathType=pathType)
                if not self._tileRect.intersectsWith(clip.bounds):
                    continue

            with self._graphics.save():
                if clip:
                    self._graphics.intersectClipPath(path=clip)

                self._graphics.setSmoothingMode(
                    maprenderer.AbstractGraphics.SmoothingMode.AntiAlias)

                regions = \
                    sector.regions() \
                    if layer is RenderContext.BorderLayer.Regions else \
                    sector.borders()

                for region in regions:
                    regionColor = region.colour()
                    regionStyle = None

                    if isinstance(region, traveller.Border):
                        if region.style() is traveller.Border.Style.Solid:
                            regionStyle = maprenderer.LineStyle.Solid
                        elif region.style() is traveller.Border.Style.Dashed:
                            regionStyle = maprenderer.LineStyle.Dashed
                        elif region.style() is traveller.Border.Style.Dotted:
                            regionStyle = maprenderer.LineStyle.Dotted

                        if not regionColor or not regionStyle:
                            defaultColor, defaultStyle = self._styleCache.defaultBorderStyle(region.allegiance())
                            if not regionColor:
                                regionColor = defaultColor
                            if not regionStyle:
                                regionStyle = defaultStyle

                    if not regionColor:
                        regionColor = self._styles.microRoutes.pen.color
                    if not regionStyle:
                        regionStyle = maprenderer.LineStyle.Solid

                    if (layer is RenderContext.BorderLayer.Stroke) and (regionStyle is maprenderer.LineStyle.NoStyle):
                        continue

                    # TODO: Handle noticable colours
                    """
                    if (styles.grayscale ||
                        !ColorUtil.NoticeableDifference(borderColor.Value, styles.backgroundColor))
                    {
                        borderColor = styles.microBorders.pen.color; // default
                    }
                    """

                    outline = region.absoluteOutline()
                    drawPath = []
                    for x, y in outline:
                        drawPath.append(maprenderer.PointF(x=x, y=y))
                    types = [maprenderer.PathPointType.Start]
                    for _ in range(len(outline) - 1):
                        types.append(maprenderer.PathPointType.Line)
                    types[-1] |= maprenderer.PathPointType.CloseSubpath
                    drawPath = maprenderer.AbstractPath(points=drawPath, types=types, closed=True)

                    pen.color = regionColor
                    pen.dashStyle = maprenderer.lineStyleToDashStyle(regionStyle)

                    # Allow style to override
                    if self._styles.microBorders.pen.dashStyle is not maprenderer.DashStyle.Solid:
                        pen.dashStyle = self._styles.microBorders.pen.dashStyle
                    else:
                        pen.dashStyle = maprenderer.lineStyleToDashStyle(regionStyle)

                    # Shade is a wide/solid outline under the main outline.
                    if layer is RenderContext.BorderLayer.Shade:
                        pen.width = penWidth * 2.5
                        pen.dashStyle = maprenderer.DashStyle.Solid
                        pen.color = maprenderer.makeAlphaColor(
                            alpha=shadeAlpha,
                            color=pen.color)

                    # TODO: There should be alternate handling for curves but I don't think i'm
                    # going to be able to support it as I'm not sure how to draw them with QPainter
                    #if self._styles.microBorderStyle is not MicroBorderStyle.Curve:
                    with self._graphics.save():
                        # Clip to the path itself - this means adjacent borders don't clash
                        self._graphics.intersectClipPath(path=drawPath)
                        if layer is RenderContext.BorderLayer.Regions or layer is RenderContext.BorderLayer.Fill:
                            try:
                                red, green, blue, _ = travellermap.stringToColourChannels(colour=regionColor)
                            except Exception as ex:
                                logging.warning('Failed to parse region colour', exc_info=ex)
                                continue
                            solidBrush.color = travellermap.colourChannelsToString(
                                red=red,
                                green=green,
                                blue=blue,
                                alpha=fillAlpha)
                            self._graphics.drawPathFill(brush=solidBrush, path=drawPath)
                        elif layer is RenderContext.BorderLayer.Shade or layer is RenderContext.BorderLayer.Stroke:
                            self._graphics.drawPathOutline(pen=pen, path=drawPath)

    def _drawOverlayGlyph(
            self,
            glyph: str,
            font: maprenderer.AbstractFont,
            brush: maprenderer.AbstractBrush,
            position: travellermap.HexPosition
            ) -> None:
        centerX, centerY = position.absoluteCenter()
        with self._graphics.save():
            self._graphics.translateTransform(centerX, centerY)
            self._graphics.scaleTransform(1 / travellermap.ParsecScaleX, 1 / travellermap.ParsecScaleY)
            self._graphics.drawString(glyph, font, brush, 0, 0, maprenderer.StringAlignment.Centered)

    def _zoneStyle(
            self,
            world: traveller.World
            ) -> typing.Optional[maprenderer.StyleSheet.StyleElement]:
        zone = world.zone()
        if zone is traveller.ZoneType.AmberZone:
            return self._styles.amberZone
        if zone is traveller.ZoneType.RedZone:
            return self._styles.redZone
        # TODO: Handle placeholders, this should be
        # if (styles.greenZone.visible && !world.IsPlaceholder)
        if self._styles.greenZone.visible:
            return self._styles.greenZone
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
    def _starOffset(index: int) -> maprenderer.PointF:
        if index >= len(RenderContext._StarOffsetX):
            index = (index % (len(RenderContext._StarOffsetX) - 1)) + 1
        return maprenderer.PointF(RenderContext._StarOffsetX[index], RenderContext._StarOffsetY[index])

    @staticmethod
    def _offsetRouteSegment(startPoint: maprenderer.PointF, endPoint: maprenderer.PointF, offset: float) -> None:
        dx = (endPoint.x - startPoint.x) * travellermap.ParsecScaleX
        dy = (endPoint.y - startPoint.y) * travellermap.ParsecScaleY
        length = math.sqrt(dx * dx + dy * dy)
        if not length:
            return # No offset
        ddx = (dx * offset / length) / travellermap.ParsecScaleX
        ddy = (dy * offset / length) / travellermap.ParsecScaleY
        startPoint.x += ddx
        startPoint.y += ddy
        endPoint.x -= ddx
        endPoint.y -= ddy

    @staticmethod
    def _hexToCenter(hex: travellermap.HexPosition) -> maprenderer.PointF:
        centerX, centerY = hex.absoluteCenter()
        return maprenderer.PointF(x=centerX, y=centerY)
