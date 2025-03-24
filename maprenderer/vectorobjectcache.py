import base64
import logging
import maprenderer
import travellermap
import typing
import xml.etree.ElementTree

class VectorObject(object):
    def __init__(
            self,
            name: typing.Optional[str],
            originX: float,
            originY: float,
            scaleX: float,
            scaleY: float,
            nameX: float,
            nameY: float,
            bounds: maprenderer.RectangleF,
            path: typing.Optional[maprenderer.AbstractPath],
            mapOptions: maprenderer.MapOptions = 0
            ) -> None:
        super().__init__()

        self.name = name
        self.originX = originX
        self.originY = originY
        self.scaleX = scaleX
        self.scaleY = scaleY
        self.nameX = nameX
        self.nameY = nameY
        self.mapOptions = mapOptions
        self.path = path

        self._bounds = maprenderer.RectangleF(bounds)
        self._bounds.setX(self._bounds.x() - self.originX)
        self._bounds.setY(self._bounds.y() - self.originY)
        self._bounds.setX(self._bounds.x() * self.scaleX)
        self._bounds.setY(self._bounds.y() * self.scaleY)
        self._bounds.setWidth(self._bounds.width() * self.scaleX)
        self._bounds.setHeight(self._bounds.height() * self.scaleY)
        if self._bounds.width() < 0:
            self._bounds.setX(self._bounds.x() + self._bounds.width())
            self._bounds.setWidth(-self._bounds.width())
        if self._bounds.height() < 0:
            self._bounds.setY(self._bounds.y() + self._bounds.height())
            self._bounds.setHeight(-self._bounds.height())

        self._namePosition = self._bounds.centre()
        self._namePosition.setX(
            self._namePosition.x() + (self._bounds.width() * (self.nameX / bounds.width())))
        self._namePosition.setY(
            self._namePosition.y() + (self._bounds.height() * (self.nameY / bounds.height())))

    @property
    def bounds(self) -> maprenderer.RectangleF:
        return maprenderer.RectangleF(self._bounds)

    @property
    def namePosition(self) -> maprenderer.PointF:
        return maprenderer.PointF(self._namePosition)

# NOTE: My implementation of vectors is slightly different from the Traveller
# Map one. The vector format supports point types which specify a set of flags
# for each point that determine how the point should be interpreted. A full
# list of the flags can be found here
# https://learn.microsoft.com/en-us/windows/win32/api/gdiplusenums/ne-gdiplusenums-pathpointtype
# When vector definitions use the CloseSubpath flag the Traveller Map
# implementation keeps these keeps the sub paths as a single VectorObject (i.e.
# one VectorObject per file). The intention is that the rendering engine should
# interpret the flags and render separate sub paths. This is great if the
# rendering engine supports it, but if it doesn't (e.g. Qt) then it can make
# rendering more complex/inefficient. My implementation splits sub paths into
# multiple VectorObject to avoid repeated processing at render time
class VectorObjectCache(object):
    _BorderFiles = [
        'res/Vectors/Imperium.xml',
        'res/Vectors/Aslan.xml',
        'res/Vectors/Kkree.xml',
        'res/Vectors/Vargr.xml',
        'res/Vectors/Zhodani.xml',
        'res/Vectors/Solomani.xml',
        'res/Vectors/Hive.xml',
        'res/Vectors/SpinwardClient.xml',
        'res/Vectors/RimwardClient.xml',
        'res/Vectors/TrailingClient.xml']

    _RiftFiles = [
        'res/Vectors/GreatRift.xml',
        'res/Vectors/LesserRift.xml',
        'res/Vectors/WindhornRift.xml',
        'res/Vectors/DelphiRift.xml',
        'res/Vectors/ZhdantRift.xml']

    _RouteFiles = [
        'res/Vectors/J5Route.xml',
        'res/Vectors/J4Route.xml',
        'res/Vectors/CoreRoute.xml']

    def __init__(
            self,
            graphics: maprenderer.AbstractGraphics
            ) -> None:
        self._graphics = graphics
        self.borders = self._loadFiles(VectorObjectCache._BorderFiles)
        self.rifts = self._loadFiles(VectorObjectCache._RiftFiles)
        self.routes = self._loadFiles(VectorObjectCache._RouteFiles)

    def _loadFiles(
            self,
            paths: typing.Iterable[str]
            ) -> typing.List[VectorObject]:
        vectors = []
        for path in paths:
            try:
                vectors.extend(self._parseFile(
                    content=travellermap.DataStore.instance().loadTextResource(
                        filePath=path)))
            except Exception as ex:
                logging.warning(f'Failed to parse vector object file "{path}"', exc_info=ex)
        return vectors

    def _parseFile(self, content: str) -> typing.Iterable[VectorObject]:
        rootElement = xml.etree.ElementTree.fromstring(content)

        name = None
        element = rootElement.find('./Name')
        if element is not None:
            name = element.text

        mapOptions = 0
        element = rootElement.find('./MapOptions')
        if element is not None:
            for option in element.text.split():
                mapOptions |= maprenderer.MapOptions[option]

        originX = 0
        element = rootElement.find('./OriginX')
        if element is not None:
            originX = float(element.text)

        originY = 0
        element = rootElement.find('./OriginY')
        if element is not None:
            originY= float(element.text)

        scaleX = 1
        element = rootElement.find('./ScaleX')
        if element is not None:
            scaleX = float(element.text)

        scaleY = 1
        element = rootElement.find('./ScaleY')
        if element is not None:
            scaleY = float(element.text)

        nameX = 0
        element = rootElement.find('./NameX')
        if element is not None:
            nameX = float(element.text)

        nameY = 0
        element = rootElement.find('./NameY')
        if element is not None:
            nameY = float(element.text)

        # NOTE: Only routes have a type and it doesn't seem to be used so
        # don't bother loading it
        #element = rootElement.find('./Type')

        # NOTE: Loading the bounds from the file when it's present rather than
        # regenerating it from the points is important as the bounds in the file
        # doesn't always match the bounds of the points (e.g. the Solomani
        # Sphere). As the bounds determine where the name name is drawn it needs
        # to match what Traveller Map uses.
        xElement = rootElement.find('./Bounds/X')
        yElement = rootElement.find('./Bounds/Y')
        widthElement = rootElement.find('./Bounds/Width')
        heightElement = rootElement.find('./Bounds/Height')
        if xElement is None or yElement is None or widthElement is None or heightElement is None:
            raise RuntimeError('Invalid bounds')

        bounds = maprenderer.RectangleF(
            x=float(xElement.text),
            y=float(yElement.text),
            width=float(widthElement.text),
            height=float(heightElement.text))

        points = []
        for pointElement in rootElement.findall('./PathDataPoints/PointF'):
            x = 0
            element = pointElement.find('./X')
            if element is not None:
                x = float(element.text)

            y = 0
            element = pointElement.find('./Y')
            if element is not None:
                y = float(element.text)

            points.append(maprenderer.PointF(x=x, y=y))

        element = rootElement.find('./PathDataTypes')
        types = None
        if points and element is not None:
            types = base64.b64decode(element.text)
            startIndex = 0
            finishIndex = len(points) - 1
            sectionPoints = []
            vectorObjects = []

            # TODO: I'm not handling the different curve types here
            for currentIndex, (point, type) in enumerate(zip(points, types)):
                isStartPoint = (type & maprenderer.PathPointType.PathTypeMask) == \
                    maprenderer.PathPointType.Start
                isLastPoint = currentIndex == finishIndex
                isClosed = (type & maprenderer.PathPointType.CloseSubpath) == \
                    maprenderer.PathPointType.CloseSubpath

                if isClosed or isLastPoint:
                    sectionPoints.append(point)

                if (isStartPoint and sectionPoints) or isClosed or isLastPoint:
                    isFirstVector = not vectorObjects
                    nextIndex = currentIndex + (0 if isStartPoint else 1)
                    vectorObjects.append(VectorObject(
                        name=name if isFirstVector else '', # Only set name on first to avoid multiple rendering
                        originX=originX,
                        originY=originY,
                        scaleX=scaleX,
                        scaleY=scaleY,
                        nameX=nameX,
                        nameY=nameY,
                        bounds=bounds,
                        path=self._createPath(points=sectionPoints, types=types[startIndex:nextIndex], closed=isClosed),
                        mapOptions=mapOptions))
                    sectionPoints.clear()
                    startIndex = nextIndex

                sectionPoints.append(point)

            return vectorObjects
        else:
            # No path data types so this is just a single path
            return [VectorObject(
                name=name,
                originX=originX,
                originY=originY,
                scaleX=scaleX,
                scaleY=scaleY,
                nameX=nameX,
                nameY=nameY,
                bounds=bounds,
                path=self._createPath(points=points, types=None, closed=False) if points else None,
                mapOptions=mapOptions)]

    def _createPath(
            self,
            points: typing.Sequence[maprenderer.PointF],
            types: typing.Optional[typing.Sequence[maprenderer.PathPointType]],
            closed: bool
            ) -> maprenderer.AbstractPath:
        if not types:
            types = [maprenderer.PathPointType.Start]
            for _ in range(1, len(points)):
                types.append(maprenderer.PathPointType.Line)
        return self._graphics.createPath(points=points, types=types, closed=closed)

