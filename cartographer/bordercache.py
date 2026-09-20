import astronomer
import azathoth
import cartographer
import common
import itertools
import math
import typing

class BorderInfo(object):
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

    def bounds(self) -> cartographer.RectangleF:
        # TODO: Not sure what is best to do here as the spline and path can have
        # slightly different bounds. I think the spline bounds will always be the
        # larger of the two so I'm using that for now
        return self._spline.bounds()

class BorderCache(object):
    # This comes from the Traveller Map DrawMicroBorders code
    _SplineTension = 0.6

    def __init__(
            self,
            universe: astronomer.Universe,
            graphics: cartographer.AbstractGraphics
            ) -> None:
        self._universe = universe
        self._graphics = graphics

        self._borderIdToInfoMap: typing.Optional[typing.Dict[str, BorderInfo]] = None
        self._quadTree: typing.Optional[cartographer.QuadTree] = None

        azathoth.UniverseEditor.instance().addPreUpdateObserver(self._handleUniversePreUpdate)
        azathoth.UniverseEditor.instance().addPostUpdateObserver(self._handleUniversePostUpdate)

    def __del__(self) -> None:
        azathoth.UniverseEditor.instance().removeObserver(self._handleUniversePreUpdate)
        azathoth.UniverseEditor.instance().removeObserver(self._handleUniversePostUpdate)

    def bordersInArea(
            self,
            bounds: cartographer.RectangleF
            ) -> typing.List[BorderInfo]:
        if self._quadTree is None:
            self._populate()
        return self._quadTree.query(bounds=bounds)

    def clear(self) -> None:
        self._borderIdToInfoMap = None
        self._quadTree = None

    def _populate(self):
        self._borderIdToInfoMap = {}
        self._quadTree = cartographer.QuadTree(
            bounds=cartographer.RectangleF(0, 0, 1000, 1000),
            maxObjects=10,
            maxDepth=8)

        for border in self._universe.borders():
            borderInfo = self._createBorderInfo(border=border)
            if borderInfo is None:
                continue
            self._borderIdToInfoMap[border.entityId()] = borderInfo

            self._quadTree.add(
                obj=borderInfo,
                bounds=borderInfo.bounds())

    def _handleUniversePreUpdate(
            self,
            universe: azathoth.EditableUniverse,
            changeEvent: azathoth.ChangeEvent
            ) -> None:
        if self._borderIdToInfoMap is None:
            # The cache hasn't been populated so nothing to update
            return

        if self._universe != universe:
            return

        for obj in itertools.chain(changeEvent.deleted(), changeEvent.modified()):
            if isinstance(obj, astronomer.Border):
                borderInfo = self._borderIdToInfoMap.get(obj.entityId())
                if borderInfo is None:
                    continue # Route hasn't been cached for some reason
                del self._borderIdToInfoMap[obj.entityId()]
                self._quadTree.remove(borderInfo, borderInfo.bounds())
            elif isinstance(obj, astronomer.Allegiance):
                # TODO: If the allegiance used by a route has changed then that route needs to
                # update as its width/colour/style may have changed
                pass

    def _handleUniversePostUpdate(
            self,
            universe: azathoth.EditableUniverse,
            changeEvent: azathoth.ChangeEvent
            ) -> None:
        if self._borderIdToInfoMap is None:
            # The cache hasn't been populated so nothing to update
            return

        if self._universe != universe:
            return

        for obj in itertools.chain(changeEvent.added(), changeEvent.modified()):
            if isinstance(obj, astronomer.Route):
                borderInfo = self._createBorderInfo(border=obj)
                if borderInfo is not None:
                    self._borderIdToInfoMap[obj.entityId()] = borderInfo
                    self._quadTree.add(borderInfo, borderInfo.bounds())
            elif isinstance(obj, astronomer.Allegiance):
                # TODO: If the allegiance used by a route has changed then that route needs to
                # update as its width/colour/style may have changed
                pass

    def _createBorderInfo(
            self,
            border: astronomer.Border
            ) -> typing.Optional[BorderInfo]:
        try:
            colour = border.colour()
            style = border.style()

            allegiance = border.allegiance()
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

            outline = border.worldOutline2()
            drawPath = []
            for x, y in outline:
                drawPath.append(cartographer.PointF(x=x, y=y))

            path = self._graphics.createPath(
                points=drawPath,
                closed=True)
            spline = self._graphics.createSpline(
                points=drawPath,
                tension=BorderCache._SplineTension,
                closed=True)

            return BorderInfo(path=path, spline=spline, colour=colour, style=style)
        except Exception as ex:
            # TODO: Log something
            print(str(ex))
            return None
