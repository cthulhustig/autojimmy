import maprenderer
import math
import traveller
import travellermap
import typing

class SectorPath(object):
    def __init__(
            self,
            path: maprenderer.AbstractPath,
            color: typing.Optional[str],
            style: typing.Optional[maprenderer.LineStyle]
            ) -> None:
        self._path = path
        self._color = color
        self._style = style

    def path(self) -> maprenderer.AbstractPath:
        return self._path

    def color(self) -> typing.Optional[str]:
        return self._color

    def style(self) -> typing.Optional[maprenderer.LineStyle]:
        return self._style

    def bounds(self) -> maprenderer.AbstractRectangleF:
        return self._path.bounds()

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

# TODO: Should probably flatten style cache into this code as I think it's
# the only thing that actually uses it
class SectorCache(object):
    # This was moved from the style sheet as it never actually changes
    _RouteEndAdjust = 0.25

    def __init__(
            self,
            graphics: maprenderer.AbstractGraphics,
            styleCache: maprenderer.DefaultStyleCache
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
            points.append(maprenderer.AbstractPointF(
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
            typing.List[maprenderer.AbstractPointF]] = {}
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
            startPoint = maprenderer.AbstractPointF(x=centerX, y=centerY)

            centerX, centerY = endPoint.absoluteCenter()
            endPoint = maprenderer.AbstractPointF(x=centerX, y=centerY)

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
                defaultColor, defaultStyle = self._styleCache.defaultBorderStyle(source.allegiance())
                if not color:
                    color = defaultColor
                if not style:
                    style = defaultStyle

        outline = source.absoluteOutline()
        drawPath = []
        for x, y in outline:
            drawPath.append(maprenderer.AbstractPointF(x=x, y=y))
        types = [maprenderer.PathPointType.Start]
        for _ in range(len(outline) - 1):
            types.append(maprenderer.PathPointType.Line)
        types[-1] |= maprenderer.PathPointType.CloseSubpath
        outline = self._graphics.createPath(points=drawPath, types=types, closed=True)

        return SectorPath(path=outline, color=color, style=style)

    @staticmethod
    def _offsetRouteSegment(
            startPoint: maprenderer.AbstractPointF,
            endPoint: maprenderer.AbstractPointF,
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