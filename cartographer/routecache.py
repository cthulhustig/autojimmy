import astronomer
import azathoth
import cartographer
import common
import itertools
import math
import typing

class RouteInfo(object):
    def __init__(
            self,
            start: cartographer.PointF,
            end: cartographer.PointF,
            width: float,
            colour: typing.Optional[str],
            style: typing.Optional[cartographer.LineStyle]
            ) -> None:
        self._start = start
        self._end = end
        self._width = width
        self._colour = colour
        self._style = style

        self._bounds = None

    def start(self) -> cartographer.PointF:
        return self._start

    def end(self) -> cartographer.PointF:
        return self._end

    def width(self) -> float:
        return self._width

    def colour(self) -> typing.Optional[str]:
        return self._colour

    def style(self) -> typing.Optional[cartographer.LineStyle]:
        return self._style

    def bounds(self) -> cartographer.RectangleF:
        if self._bounds is not None:
            return self._bounds

        dx = self._end.x() - self._start.x()
        dy = self._end.y() - self._start.y()

        length = math.hypot(dx, dy)
        if length == 0:
            self._bounds = cartographer.RectangleF(
                x=self._start.x(),
                y=self._start.y(),
                width=0,
                height=0)
            return self._bounds

        halfWidth = self._width / 2

        # Maximum X/Y displacement caused by the thickness
        offsetX = abs(dy) / length * halfWidth
        offsetY = abs(dx) / length * halfWidth

        minX = min(self._start.x(), self._end.x()) - offsetX
        maxX = max(self._start.x(), self._end.x()) + offsetX
        minY = min(self._start.y(), self._end.y()) - offsetY
        maxY = max(self._start.y(), self._end.y()) + offsetY

        self._bounds = cartographer.RectangleF(
            x=minX,
            y=minY,
            width=maxX - minX,
            height=maxY - minY)
        return self._bounds

class RouteCache(object):
    # This was moved from the style sheet as it never actually changes
    _RouteEndAdjust = 0.25

    def __init__(
            self,
            universe: astronomer.Universe
            ) -> None:
        self._universe = universe

        self._routeIdToRouteInfoMap: typing.Optional[typing.Dict[str, RouteInfo]] = None
        self._quadTree: typing.Optional[cartographer.QuadTree] = None

        azathoth.UniverseEditor.instance().addPreUpdateObserver(self._handleUniversePreUpdate)
        azathoth.UniverseEditor.instance().addPostUpdateObserver(self._handleUniversePostUpdate)

    def __del__(self) -> None:
        azathoth.UniverseEditor.instance().removeObserver(self._handleUniversePreUpdate)
        azathoth.UniverseEditor.instance().removeObserver(self._handleUniversePostUpdate)

    def routesInArea(
            self,
            bounds: cartographer.RectangleF
            ) -> typing.List[RouteInfo]:
        if self._quadTree is None:
            self._populate()
        return self._quadTree.query(bounds=bounds)

    def clear(self) -> None:
        self._routeIdToRouteInfoMap = None
        self._quadTree = None

    def _populate(self):
        self._routeIdToRouteInfoMap = {}
        self._quadTree = cartographer.QuadTree(
            bounds=cartographer.RectangleF(0, 0, 1000, 1000),
            maxObjects=10,
            maxDepth=8)

        for sector in self._universe.sectors():
            for route in sector.routes():
                routeInfo = RouteCache._createRouteInfo(route=route)
                if routeInfo is None:
                    continue
                self._routeIdToRouteInfoMap[route.entityId()] = routeInfo

                self._quadTree.add(
                    obj=routeInfo,
                    bounds=routeInfo.bounds())

    def _handleUniversePreUpdate(
            self,
            universe: azathoth.EditableUniverse,
            changeEvent: azathoth.ChangeEvent
            ) -> None:
        if self._routeIdToRouteInfoMap is None:
            # The cache hasn't been populated so nothing to update
            return

        if self._universe != universe:
            return

        for obj in itertools.chain(changeEvent.deleted(), changeEvent.modified()):
            if isinstance(obj, astronomer.Route):
                routeInfo = self._routeIdToRouteInfoMap.get(obj.entityId())
                if routeInfo is None:
                    continue # Route hasn't been cached for some reason
                del self._routeIdToRouteInfoMap[obj.entityId()]
                self._quadTree.remove(routeInfo, routeInfo.bounds())
            elif isinstance(obj, astronomer.Allegiance):
                # TODO: If the allegiance used by a route has changed then that route needs to
                # update as its width/colour/style may have changed
                pass

    def _handleUniversePostUpdate(
            self,
            universe: azathoth.EditableUniverse,
            changeEvent: azathoth.ChangeEvent
            ) -> None:
        if self._routeIdToRouteInfoMap is None:
            # The cache hasn't been populated so nothing to update
            return

        if self._universe != universe:
            return

        for obj in itertools.chain(changeEvent.added(), changeEvent.modified()):
            if isinstance(obj, astronomer.Route):
                routeInfo = RouteCache._createRouteInfo(route=obj)
                if routeInfo is not None:
                    self._routeIdToRouteInfoMap[obj.entityId()] = routeInfo
                    self._quadTree.add(routeInfo, routeInfo.bounds())
            elif isinstance(obj, astronomer.Allegiance):
                # TODO: If the allegiance used by a route has changed then that route needs to
                # update as its width/colour/style may have changed
                pass

    @staticmethod
    def _createRouteInfo(
            route: astronomer.Route
            ) -> typing.Optional[RouteInfo]:
        startPoint = route.startHex()
        endPoint = route.endHex()
        if startPoint == endPoint:
            # Ignore routes where the start & end point are the same as there
            # is nothing to draw
            return None

        # If drawing dashed lines twice and the start/end are swapped the
        # dashes don't overlap correctly. So "sort" the points.
        needsSwap = (startPoint.absoluteX() < endPoint.absoluteX()) or \
            (startPoint.absoluteX() == endPoint.absoluteX() and \
                startPoint.absoluteY() < endPoint.absoluteY())
        if needsSwap:
            (startPoint, endPoint) = (endPoint, startPoint)

        centerX, centerY = startPoint.worldCenter()
        startPoint = cartographer.PointF(x=centerX, y=centerY)

        centerX, centerY = endPoint.worldCenter()
        endPoint = cartographer.PointF(x=centerX, y=centerY)

        # Shorten line to leave room for world glyph
        RouteCache._offsetRouteSegment(
            startPoint=startPoint,
            endPoint=endPoint,
            offset=RouteCache._RouteEndAdjust)

        width = route.width()
        colour = route.colour()
        style = route.style()
        allegiance = route.allegiance()
        if allegiance:
            if colour is None:
                colour = allegiance.routeColour()
            if style is None:
                style = allegiance.routeStyle()
            if width is None:
                width = allegiance.routeWidth()

        if style is astronomer.LineStyle.Solid:
            style = cartographer.LineStyle.Solid
        elif style is astronomer.LineStyle.Dashed:
            style = cartographer.LineStyle.Dash
        elif style is astronomer.LineStyle.Dotted:
            style = cartographer.LineStyle.Dot
        else:
            style = None

        return RouteInfo(
            start=startPoint,
            end=endPoint,
            width=width if width is not None else 1.0,
            colour=colour,
            style=style)

    @staticmethod
    def _offsetRouteSegment(
            startPoint: cartographer.PointF,
            endPoint: cartographer.PointF,
            offset: float
            ) -> None:
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