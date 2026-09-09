import astronomer
import cartographer
import typing

class SectorPath(object):
    def __init__(
            self,
            path: cartographer.AbstractPath,
            spline: cartographer.AbstractSpline,
            colour: typing.Optional[str],
            style: typing.Optional[cartographer.LineStyle]
            ) -> None:
        self._path = path
        self._spline = spline
        self._colour = colour
        self._style = style

    def path(self) -> cartographer.AbstractPath:
        return self._path

    def spline(self) -> cartographer.AbstractSpline:
        return self._spline

    def colour(self) -> typing.Optional[str]:
        return self._colour

    def style(self) -> typing.Optional[cartographer.LineStyle]:
        return self._style

class SectorCache(object):
    # This comes from the Traveller Map DrawMicroBorders code
    _SplineTension = 0.6

    # NOTE: These offsets assume a clockwise winding
    _TopClipOffsets = [
        (-0.5 - astronomer.HexWidthOffset, 0), # Center left
        (-0.5 + astronomer.HexWidthOffset, -0.5), # Upper left
        (+0.5 - astronomer.HexWidthOffset, -0.5), # Upper right
        (+0.5 + astronomer.HexWidthOffset, 0) # Center right
    ]

    _RightClipOffsets = [
        (+0.5 - astronomer.HexWidthOffset, -0.5), # Upper right
        (+0.5 + astronomer.HexWidthOffset, 0), # Center right
        (+0.5 - astronomer.HexWidthOffset, +0.5), # Lower right
        (+0.5 + astronomer.HexWidthOffset, 1) # Center right of next hex
    ]

    _BottomClipOffsets = [
        (+0.5 + astronomer.HexWidthOffset, 0), # Center right
        (+0.5 - astronomer.HexWidthOffset, +0.5), # Lower right
        (-0.5 + astronomer.HexWidthOffset, +0.5), # Lower Left
        (-0.5 - astronomer.HexWidthOffset, 0) # Center left
    ]

    _LeftClipOffsets = [
        (-0.5 + astronomer.HexWidthOffset, +0.5), # Lower Left
        (-0.5 - astronomer.HexWidthOffset, 0), # Center left
        (-0.5 + astronomer.HexWidthOffset, -0.5), # Upper left
        (-0.5 - astronomer.HexWidthOffset, -1) # Center left of next hex
    ]

    def __init__(
            self,
            universe: astronomer.Universe,
            graphics: cartographer.AbstractGraphics
            ) -> None:
        self._universe = universe
        self._graphics = graphics
        self._worldsCache: typing.Dict[
            astronomer.SectorPosition,
            cartographer.AbstractPointList
        ] = {}
        self._borderCache: typing.Dict[
            astronomer.SectorPosition,
            typing.List[SectorPath]
        ] = {}
        self._regionCache: typing.Dict[
            astronomer.SectorPosition,
            typing.List[SectorPath]
        ] = {}
        self._clipCache: typing.Dict[
            astronomer.SectorPosition,
            cartographer.AbstractPath
        ] = {}

    def isotropicWorldPoints(
            self,
            sectorPos: astronomer.SectorPosition
            ) -> typing.Optional[cartographer.AbstractPointList]:
        # NOTE: Use -1 as the default so we can differentiate between a sector
        # that is not in the cache and one that is in the cache but is set to
        # None as it has no worlds
        worlds = self._worldsCache.get(sectorPos, -1)
        if worlds != -1:
            return worlds

        sector = self._universe.sectorByPosition(position=sectorPos)
        if not sector:
            # Don't cache the fact the sector doesn't exist to avoid memory bloat
            return None

        points = []
        for world in self._universe.worldsInSector(position=sectorPos):
            centerX, centerY = world.hex().worldCenter()
            points.append(cartographer.PointF(
                # Scale center point by parsec scale to convert to isotropic coordinates
                x=centerX * astronomer.ParsecScaleX,
                y=centerY * astronomer.ParsecScaleY))

        worlds = self._graphics.createPointList(points=points) if points else None
        self._worldsCache[sectorPos] = worlds
        return worlds

    def borderPaths(
            self,
            sectorPos: astronomer.SectorPosition
            ) -> typing.Optional[typing.List[SectorPath]]:
        borders = self._borderCache.get(sectorPos)
        if borders is not None:
            return borders

        sector = self._universe.sectorByPosition(position=sectorPos)
        if not sector:
            # Don't cache the fact the sector doesn't exist to avoid memory bloat
            return None

        borders = []
        for border in sector.borders():
            borders.append(self._createOutline(source=border))
        self._borderCache[sectorPos] = borders
        return borders

    def regionPaths(
            self,
            sectorPos: astronomer.SectorPosition
            ) -> typing.Optional[typing.List[SectorPath]]:
        regions = self._regionCache.get(sectorPos)
        if regions is not None:
            return regions

        sector = self._universe.sectorByPosition(position=sectorPos)
        if not sector:
            # Don't cache the fact the sector doesn't exist to avoid memory bloat
            return None

        regions = []
        for region in sector.regions():
            regions.append(self._createOutline(source=region))
        self._regionCache[sectorPos] = regions
        return regions

    def clipPath(
            self,
            sectorPos: astronomer.SectorPosition
            ) -> cartographer.AbstractPath:
        clipPath = self._clipCache.get(sectorPos)
        if clipPath:
            return clipPath

        absoluteOriginX, absoluteOriginY = astronomer.relativeSpaceToAbsoluteSpace(
            (sectorPos.sectorX(), sectorPos.sectorY(), 1, 1))

        points = []

        count = len(SectorCache._TopClipOffsets)
        y = 0
        for x in range(0, astronomer.SectorWidth, 2):
            for i in range(count):
                offsetX, offsetY = SectorCache._TopClipOffsets[i]
                points.append(cartographer.PointF(
                    x=((absoluteOriginX + x) - 0.5) + offsetX,
                    y=((absoluteOriginY + y) - 0.5) + offsetY))

        last = astronomer.SectorHeight - 2
        count = len(SectorCache._RightClipOffsets)
        x = astronomer.SectorWidth - 1
        for y in range(0, astronomer.SectorHeight, 2):
            if y == last:
                count -= 1
            for i in range(count):
                offsetX, offsetY = SectorCache._RightClipOffsets[i]
                points.append(cartographer.PointF(
                    x=((absoluteOriginX + x) - 0.5) + offsetX,
                    y=(absoluteOriginY + y) + offsetY))

        count = len(SectorCache._BottomClipOffsets)
        y = astronomer.SectorHeight - 1
        for x in range(astronomer.SectorWidth - 1, -1, -2):
            for i in range(count):
                offsetX, offsetY = SectorCache._BottomClipOffsets[i]
                points.append(cartographer.PointF(
                    x=((absoluteOriginX + x) - 0.5) + offsetX,
                    y=(absoluteOriginY + y) + offsetY))

        last = astronomer.SectorHeight - 2
        count = len(SectorCache._LeftClipOffsets)
        x = 0
        for y in range(astronomer.SectorHeight - 1, -1, -2):
            if y == last:
                count -= 1
            for i in range(count):
                offsetX, offsetY = SectorCache._LeftClipOffsets[i]
                points.append(cartographer.PointF(
                    x=((absoluteOriginX + x) - 0.5) + offsetX,
                    y=((absoluteOriginY + y) - 0.5) + offsetY))

        path = self._graphics.createPath(points=points, closed=True)
        self._clipCache[sectorPos] = path
        return path

    def clear(self) -> None:
        self._worldsCache.clear()
        self._borderCache.clear()
        self._regionCache.clear()
        self._clipCache.clear()

    def _createOutline(
            self,
            source: typing.Union[astronomer.Region, astronomer.Border]
            ) -> SectorPath:
        colour = source.colour()
        style = None

        if isinstance(source, astronomer.Border):
            style = source.style()

            allegiance = source.allegiance()
            if allegiance:
                if colour is None:
                    colour = allegiance.borderColour()
                if style is None:
                    style = allegiance.borderStyle()

            if style is astronomer.LineStyle.Solid:
                style = cartographer.LineStyle.Solid
            elif style is astronomer.LineStyle.Dashed:
                style = cartographer.LineStyle.Dash
            elif style is astronomer.LineStyle.Dotted:
                style = cartographer.LineStyle.Dot
            else:
                style = None

        outline = source.worldOutline()
        drawPath = []
        for x, y in outline:
            drawPath.append(cartographer.PointF(x=x, y=y))

        path = self._graphics.createPath(
            points=drawPath,
            closed=True)
        spline = self._graphics.createSpline(
            points=drawPath,
            tension=SectorCache._SplineTension,
            closed=True)

        return SectorPath(path=path, spline=spline, colour=colour, style=style)
