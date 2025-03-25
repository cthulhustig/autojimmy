import maprenderer
import math
import traveller
import travellermap
import typing

class SectorPath(object):
    def __init__(
            self,
            path: maprenderer.AbstractPath,
            spline: maprenderer.AbstractSpline,
            color: typing.Optional[str],
            style: typing.Optional[maprenderer.LineStyle]
            ) -> None:
        self._path = path
        self._spline = spline
        self._color = color
        self._style = style

    def path(self) -> maprenderer.AbstractPath:
        return self._path

    def spline(self) -> maprenderer.AbstractSpline:
        return self._spline

    def color(self) -> typing.Optional[str]:
        return self._color

    def style(self) -> typing.Optional[maprenderer.LineStyle]:
        return self._style

class SectorLines(object):
    def __init__(
            self,
            points: typing.Iterable[maprenderer.AbstractPointList],
            color: typing.Optional[str],
            width: typing.Optional[float],
            style: typing.Optional[maprenderer.LineStyle],
            type: typing.Optional[str],
            allegiance: typing.Optional[str]
            ) -> None:
        self._points = points
        self._color = color
        self._width = width
        self._style = style
        self._type = type
        self._allegiance = allegiance

    def points(self) -> maprenderer.AbstractPointList:
        return self._points

    def color(self) -> typing.Optional[str]:
        return self._color

    def width(self) -> typing.Optional[float]:
        return self._width

    def style(self) -> typing.Optional[maprenderer.LineStyle]:
        return self._style

    def type(self) -> typing.Optional[str]:
        return self._type

    def allegiance(self) -> typing.Optional[str]:
        return self._allegiance

class SectorCache(object):
    # This was moved from the style sheet as it never actually changes
    _RouteEndAdjust = 0.25

    # This comes from the Traveller Map DrawMicroBorders code
    _SplineTension = 0.6

    # NOTE: These offsets assume a clockwise winding
    _TopClipOffsets = [
        (-0.5 - travellermap.HexWidthOffset, 0), # Center left
        (-0.5 + travellermap.HexWidthOffset, -0.5), # Upper left
        (+0.5 - travellermap.HexWidthOffset, -0.5), # Upper right
        (+0.5 + travellermap.HexWidthOffset, 0) # Center right
    ]

    _RightClipOffsets = [
        (+0.5 - travellermap.HexWidthOffset, -0.5), # Upper right
        (+0.5 + travellermap.HexWidthOffset, 0), # Center right
        (+0.5 - travellermap.HexWidthOffset, +0.5), # Lower right
        (+0.5 + travellermap.HexWidthOffset, 1) # Center right of next hex
    ]

    _BottomClipOffsets = [
        (+0.5 + travellermap.HexWidthOffset, 0), # Center right
        (+0.5 - travellermap.HexWidthOffset, +0.5), # Lower right
        (-0.5 + travellermap.HexWidthOffset, +0.5), # Lower Left
        (-0.5 - travellermap.HexWidthOffset, 0) # Center left
    ]

    _LeftClipOffsets = [
        (-0.5 + travellermap.HexWidthOffset, +0.5), # Lower Left
        (-0.5 - travellermap.HexWidthOffset, 0), # Center left
        (-0.5 + travellermap.HexWidthOffset, -0.5), # Upper left
        (-0.5 - travellermap.HexWidthOffset, -1) # Center left of next hex
    ]

    def __init__(
            self,
            graphics: maprenderer.AbstractGraphics,
            styleCache: maprenderer.StyleCache
            ) -> None:
        self._graphics = graphics
        self._styleCache = styleCache
        self._worldsCache: typing.Dict[
            typing.Union[int, int], # Sector x/y
            maprenderer.AbstractPointList
        ] = {}
        self._borderCache: typing.Dict[
            typing.Union[int, int], # Sector x/y
            typing.List[SectorPath]
        ] = {}
        self._regionCache: typing.Dict[
            typing.Union[int, int], # Sector x/y
            typing.List[SectorPath]
        ] = {}
        self._routeCache: typing.Dict[
            typing.Union[int, int], # Sector x/y
            typing.List[SectorLines]
        ] = {}
        self._clipCache: typing.Mapping[
            typing.Tuple[int, int], # Sector x/y
            maprenderer.AbstractPath
        ] = {}

    def isotropicWorldPoints(
            self,
            x: int,
            y: int
            ) -> typing.Optional[maprenderer.AbstractPointList]:
        key = (x, y)
        worlds = self._worldsCache.get(key)
        if worlds is not None:
            return worlds

        sector = traveller.WorldManager.instance().sectorByPosition(
            hex=travellermap.HexPosition(sectorX=x, sectorY=y, offsetX=1, offsetY=1))
        if not sector:
            # Don't cache the fact the sector doesn't exist to avoid memory bloat
            return None

        points = []
        for world in sector.worlds():
            hex = world.hex()
            centerX, centerY = hex.absoluteCenter()
            points.append(maprenderer.PointF(
                # Scale center point by parsec scale to convert to isotropic coordinates
                x=centerX * travellermap.ParsecScaleX,
                y=centerY * travellermap.ParsecScaleY))

        worlds = self._graphics.createPointList(points=points)
        self._worldsCache[key] = worlds
        return worlds

    def borderPaths(
            self,
            x: int,
            y: int
            ) -> typing.Optional[typing.List[SectorPath]]:
        key = (x, y)
        borders = self._borderCache.get(key)
        if borders is not None:
            return borders

        sector = traveller.WorldManager.instance().sectorByPosition(
            hex=travellermap.HexPosition(sectorX=x, sectorY=y, offsetX=1, offsetY=1))
        if not sector:
            # Don't cache the fact the sector doesn't exist to avoid memory bloat
            return None

        borders = []
        for border in sector.borders():
            borders.append(self._createOutline(source=border))
        self._borderCache[key] = borders
        return borders

    def regionPaths(
            self,
            x: int,
            y: int
            ) -> typing.Optional[typing.List[SectorPath]]:
        key = (x, y)
        regions = self._regionCache.get(key)
        if regions is not None:
            return regions

        sector = traveller.WorldManager.instance().sectorByPosition(
            hex=travellermap.HexPosition(sectorX=x, sectorY=y, offsetX=1, offsetY=1))
        if not sector:
            # Don't cache the fact the sector doesn't exist to avoid memory bloat
            return None

        regions = []
        for region in sector.regions():
            regions.append(self._createOutline(source=region))
        self._regionCache[key] = regions
        return regions

    def routeLines(
            self,
            x: int,
            y: int
            ) -> typing.Optional[typing.List[SectorLines]]:
        key = (x, y)
        routes = self._routeCache.get(key)
        if routes is not None:
            return routes

        sector = traveller.WorldManager.instance().sectorByPosition(
            hex=travellermap.HexPosition(sectorX=x, sectorY=y, offsetX=1, offsetY=1))
        if not sector:
            # Don't cache the fact the sector doesn't exist to avoid memory bloat
            return None

        routePointsMap: typing.Dict[
            typing.Tuple[
                typing.Optional[str], # Color
                typing.Optional[float], # Width
                typing.Optional[maprenderer.LineStyle], # Line style
                typing.Optional[str], # Type
                typing.Optional[str]], # Allegiance
            typing.List[maprenderer.PointF]] = {}
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

            centerX, centerY = startPoint.absoluteCenter()
            startPoint = maprenderer.PointF(x=centerX, y=centerY)

            centerX, centerY = endPoint.absoluteCenter()
            endPoint = maprenderer.PointF(x=centerX, y=centerY)

            # Shorten line to leave room for world glyph
            SectorCache._offsetRouteSegment(
                startPoint=startPoint,
                endPoint=endPoint,
                offset=SectorCache._RouteEndAdjust)

            routeKey = (route.colour(), route.width(), route.style(), route.type(), route.allegiance())
            routePoints = routePointsMap.get(routeKey)
            if not routePoints:
                routePoints = []
                routePointsMap[routeKey] = routePoints

            routePoints.append(startPoint)
            routePoints.append(endPoint)

        routes = []
        for (color, width, style, type, allegiance), points in routePointsMap.items():
            routes.append(SectorLines(
                points=self._graphics.createPointList(points=points),
                color=color,
                width=width,
                style=style,
                type=type,
                allegiance=allegiance))
        self._routeCache[key] = routes

        return routes

    def clipPath(
            self,
            sectorX: int,
            sectorY: int
            ) -> maprenderer.AbstractPath:
        key = (sectorX, sectorY)
        clipPath = self._clipCache.get(key)
        if clipPath:
            return clipPath

        originX, originY = travellermap.relativeSpaceToAbsoluteSpace(
            (sectorX, sectorY, 1, 1))

        points = []

        count = len(SectorCache._TopClipOffsets)
        y=0
        for x in range(0, travellermap.SectorWidth, 2):
            for i in range(count):
                offsetX, offsetY = SectorCache._TopClipOffsets[i]
                points.append(maprenderer.PointF(
                    x=((originX + x) - 0.5) + offsetX,
                    y=((originY + y) - 0.5) + offsetY))

        last = travellermap.SectorHeight - 2
        count = len(SectorCache._RightClipOffsets)
        x = travellermap.SectorWidth - 1
        for y in range(0, travellermap.SectorHeight, 2):
            if y == last:
                count -= 1
            for i in range(count):
                offsetX, offsetY = SectorCache._RightClipOffsets[i]
                points.append(maprenderer.PointF(
                    x=((originX + x) - 0.5) + offsetX,
                    y=(originY + y) + offsetY))

        count = len(SectorCache._BottomClipOffsets)
        y = travellermap.SectorHeight - 1
        for x in range(travellermap.SectorWidth - 1, -1, -2):
            for i in range(count):
                offsetX, offsetY = SectorCache._BottomClipOffsets[i]
                points.append(maprenderer.PointF(
                    x=((originX + x) - 0.5) + offsetX,
                    y=(originY + y) + offsetY))

        last = travellermap.SectorHeight - 2
        count = len(SectorCache._LeftClipOffsets)
        x = 0
        for y in range(travellermap.SectorHeight - 1, -1, -2):
            if y == last:
                count -= 1
            for i in range(count):
                offsetX, offsetY = SectorCache._LeftClipOffsets[i]
                points.append(maprenderer.PointF(
                    x=((originX + x) - 0.5) + offsetX,
                    y=((originY + y) - 0.5) + offsetY))

        path = self._graphics.createPath(points=points, closed=True)
        self._clipCache[key] = path
        return path

    def _createOutline(
            self,
            source: typing.Union[traveller.Region, traveller.Border]
            ) -> SectorPath:
        color = source.colour()
        style = None

        if isinstance(source, traveller.Border):
            if source.style() is traveller.Border.Style.Solid:
                style = maprenderer.LineStyle.Solid
            elif source.style() is traveller.Border.Style.Dashed:
                style = maprenderer.LineStyle.Dash
            elif source.style() is traveller.Border.Style.Dotted:
                style = maprenderer.LineStyle.Dot

            if not color or not style:
                defaultColor, defaultStyle = self._styleCache.borderStyle(source.allegiance())
                if not color:
                    color = defaultColor
                if not style:
                    style = defaultStyle

        outline = source.absoluteOutline()
        drawPath = []
        for x, y in outline:
            drawPath.append(maprenderer.PointF(x=x, y=y))

        path = self._graphics.createPath(
            points=drawPath,
            closed=True)
        spline = self._graphics.createSpline(
            points=drawPath,
            tension=SectorCache._SplineTension,
            closed=True)

        return SectorPath(path=path, spline=spline, color=color, style=style)

    @staticmethod
    def _offsetRouteSegment(
            startPoint: maprenderer.PointF,
            endPoint: maprenderer.PointF,
            offset: float
            ) -> None:
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