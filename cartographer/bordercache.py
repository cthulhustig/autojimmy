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
            outlinePaths: typing.List[cartographer.AbstractPath],
            outlineSplines: typing.List[cartographer.AbstractSpline],
            fillPath: cartographer.AbstractPath,
            fillSpline: cartographer.AbstractSpline,
            colour: typing.Optional[str],
            style: typing.Optional[cartographer.LineStyle]
            ) -> None:
        self._outlinePaths = outlinePaths
        self._outlineSplines = outlineSplines
        self._fillPath = fillPath
        self._fillSpline = fillSpline
        self._colour = colour
        self._style = style

    def outlinePaths(self) -> typing.Collection[cartographer.AbstractPath]:
        return self._outlinePaths

    def outlineSplines(self) -> typing.Collection[cartographer.AbstractSpline]:
        return self._outlineSplines

    def fillPath(self) -> cartographer.AbstractPath:
        return self._fillPath

    def fillSpline(self) -> cartographer.AbstractSpline:
        return self._fillSpline

    def colour(self) -> typing.Optional[str]:
        return self._colour

    def style(self) -> typing.Optional[cartographer.LineStyle]:
        return self._style

    def bounds(self) -> cartographer.RectangleF:
        # TODO: Not sure what is best to do here as the spline and path can have
        # slightly different bounds. I think the spline bounds will always be the
        # larger of the two so I'm using that for now
        return self._fillPath.bounds()

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

            # TODO: The outline/fill paths/splines should be calculated on
            # demand when rendered. Here I just need to convert the world
            # points to PointF paths and pass them into the info, the info
            # can then generate the graphics objects when needed and then
            # cache them (it will need to know about the graphics object)
            outlinePaths = []
            outlineSplines = []
            for outline in border.worldOutlines():
                path = []
                for x, y in outline:
                    path.append(cartographer.PointF(x=x, y=y))
                if not path:
                    continue

                outlinePaths.append(self._graphics.createPath(
                    points=path,
                    closed=True))
                outlineSplines.append(self._graphics.createSpline(
                    points=path,
                    tension=BorderCache._SplineTension,
                    closed=True))

            path = []
            for x, y in border.worldPath():
                path.append(cartographer.PointF(x=x, y=y))
            if not path:
                return None

            fillPath = self._graphics.createPath(
                points=path,
                closed=True)
            fillSpline = self._graphics.createSpline(
                points=path,
                tension=BorderCache._SplineTension,
                closed=True)

            return BorderInfo(
                outlinePaths=outlinePaths,
                outlineSplines=outlineSplines,
                fillPath=fillPath,
                fillSpline=fillSpline,
                colour=colour,
                style=style)
        except Exception as ex:
            # TODO: Log something
            print(str(ex))
            return None
