import astronomer
import azathoth
import cartographer
import itertools
import typing

class RegionInfo(object):
    class LabelInfo(object):
        def __init__(
                self,
                text: str,
                pos: cartographer.PointF
                ) -> None:
            self._text = text
            self._pos = pos

        def text(self) -> str:
            return self._text

        def pos(self) -> cartographer.PointF:
            return self._pos

    def __init__(
            self,
            fillPath: cartographer.AbstractPath,
            fillSpline: cartographer.AbstractSpline,
            colour: typing.Optional[str],
            labelInfos: typing.Optional[typing.List[LabelInfo]]
            ) -> None:
        self._fillPath = fillPath
        self._fillSpline = fillSpline
        self._colour = colour
        self._labelInfos = labelInfos

    def fillPath(self) -> cartographer.AbstractPath:
        return self._fillPath

    def fillSpline(self) -> cartographer.AbstractSpline:
        return self._fillSpline

    def colour(self) -> typing.Optional[str]:
        return self._colour

    def labelInfos(self) -> typing.Optional[typing.Collection[LabelInfo]]:
        return self._labelInfos

    def pathBounds(self) -> cartographer.RectangleF:
        # TODO: Not sure what is best to do here as the spline and path can have
        # slightly different bounds. I think the spline bounds will always be the
        # larger of the two so I'm using that for now
        return self._fillPath.bounds()

class RegionCache(object):
    # This comes from the Traveller Map DrawMicroBorders code
    _SplineTension = 0.6

    def __init__(
            self,
            universe: astronomer.Universe,
            graphics: cartographer.AbstractGraphics
            ) -> None:
        self._universe = universe
        self._graphics = graphics

        self._regionIdToInfoMap: typing.Optional[typing.Dict[str, RegionInfo]] = None
        self._quadTree: typing.Optional[cartographer.QuadTree] = None

        azathoth.UniverseEditor.instance().addPreUpdateObserver(self._handleUniversePreUpdate)
        azathoth.UniverseEditor.instance().addPostUpdateObserver(self._handleUniversePostUpdate)

    def __del__(self) -> None:
        azathoth.UniverseEditor.instance().removeObserver(self._handleUniversePreUpdate)
        azathoth.UniverseEditor.instance().removeObserver(self._handleUniversePostUpdate)

    def regionsInArea(
            self,
            bounds: cartographer.RectangleF
            ) -> typing.List[RegionInfo]:
        if self._quadTree is None:
            self._populate()
        return self._quadTree.query(bounds=bounds)

    def clear(self) -> None:
        self._regionIdToInfoMap = None
        self._quadTree = None

    def _populate(self):
        self._regionIdToInfoMap = {}
        self._quadTree = cartographer.QuadTree(
            bounds=cartographer.RectangleF(0, 0, 1000, 1000),
            maxObjects=10,
            maxDepth=8)

        for region in self._universe.regions():
            regionInfo = self._createRegionInfo(region=region)
            if regionInfo is None:
                continue
            self._regionIdToInfoMap[region.entityId()] = regionInfo

            self._quadTree.add(
                obj=regionInfo,
                bounds=regionInfo.pathBounds())

    def _handleUniversePreUpdate(
            self,
            universe: azathoth.EditableUniverse,
            changeEvent: azathoth.ChangeEvent
            ) -> None:
        if self._regionIdToInfoMap is None:
            # The cache hasn't been populated so nothing to update
            return

        if self._universe != universe:
            return

        for obj in itertools.chain(changeEvent.deleted(), changeEvent.modified()):
            if isinstance(obj, astronomer.Region):
                regionInfo = self._regionIdToInfoMap.get(obj.entityId())
                if regionInfo is None:
                    continue # Route hasn't been cached for some reason
                del self._regionIdToInfoMap[obj.entityId()]
                self._quadTree.remove(regionInfo, regionInfo.pathBounds())

    def _handleUniversePostUpdate(
            self,
            universe: azathoth.EditableUniverse,
            changeEvent: azathoth.ChangeEvent
            ) -> None:
        if self._regionIdToInfoMap is None:
            # The cache hasn't been populated so nothing to update
            return

        if self._universe != universe:
            return

        for obj in itertools.chain(changeEvent.added(), changeEvent.modified()):
            if isinstance(obj, astronomer.Region):
                regionInfo = self._createRegionInfo(region=obj)
                if regionInfo is not None:
                    self._regionIdToInfoMap[obj.entityId()] = regionInfo
                    self._quadTree.add(regionInfo, regionInfo.pathBounds())

    def _createRegionInfo(
            self,
            region: astronomer.Region
            ) -> typing.Optional[RegionInfo]:
        try:
            colour = region.colour()

            # TODO: The fill paths/splines should be calculated on
            # demand when rendered. Here I just need to convert the world
            # points to PointF paths and pass them into the info, the info
            # can then generate the graphics objects when needed and then
            # cache them (it will need to know about the graphics object)
            path = []
            for x, y in region.worldPath():
                path.append(cartographer.PointF(x=x, y=y))
            if not path:
                return None

            fillPath = self._graphics.createPath(
                points=path,
                closed=True)
            fillSpline = self._graphics.createSpline(
                points=path,
                tension=RegionCache._SplineTension,
                closed=True)

            labels = region.labels()
            labelInfos = None
            if labels:
                for label in labels:
                    if not label.show():
                        continue

                    text = label.text()
                    if text and label.wrap():
                        text = cartographer.wrapLabelText(text)

                    if labelInfos is None:
                        labelInfos = []
                    labelInfos.append(RegionInfo.LabelInfo(
                        text=text,
                        pos=cartographer.PointF(label.worldX(), label.worldY())))

            return RegionInfo(
                fillPath=fillPath,
                fillSpline=fillSpline,
                colour=colour,
                labelInfos=labelInfos)
        except Exception as ex:
            # TODO: Log something
            print(str(ex))
            return None
