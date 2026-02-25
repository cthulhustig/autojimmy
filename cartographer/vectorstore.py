import base64
import cartographer
import logging
import multiverse
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
            bounds: cartographer.RectangleF,
            path: typing.Optional[cartographer.AbstractPath],
            mapOptions: cartographer.RenderOptions = 0
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

        self._bounds = cartographer.RectangleF(bounds)
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
    def bounds(self) -> cartographer.RectangleF:
        return cartographer.RectangleF(self._bounds)

    @property
    def namePosition(self) -> cartographer.PointF:
        return cartographer.PointF(self._namePosition)

# NOTE: My implementation of vector objects is slightly different from the
# Traveller Map one. The vector format allows specifying the type of each point.
# This allows for curves to be specified and/or multiple unconnected polygons
# to be specified in a single vector object. A full list of what the point types
# support can be found here
# https://learn.microsoft.com/en-us/windows/win32/api/gdiplusenums/ne-gdiplusenums-pathpointtype
# Although the format allows for curves, none of the Traveller Map vectors
# actually use them. I suspect support for it is just something that came for
# free because the GDI point types are being used. As nothing uses them, I'm
# not supporting them and this code assumes straight lines should be used to
# connect each point.
# There are multiple instances of vector objects containing multiple
# unconnected polygons. To simplify rendering I split these so a single file
# can result in multiple vector objects, each of which represents a single
# polygon.
class VectorStore(object):
    _BorderFiles = [
        'vectors/Imperium.xml',
        'vectors/Aslan.xml',
        'vectors/Kkree.xml',
        'vectors/Vargr.xml',
        'vectors/Zhodani.xml',
        'vectors/Solomani.xml',
        'vectors/Hive.xml',
        'vectors/SpinwardClient.xml',
        'vectors/RimwardClient.xml',
        'vectors/TrailingClient.xml']

    _RiftFiles = [
        'vectors/GreatRift.xml',
        'vectors/LesserRift.xml',
        'vectors/WindhornRift.xml',
        'vectors/DelphiRift.xml',
        'vectors/ZhdantRift.xml']

    _RouteFiles = [
        'vectors/J5Route.xml',
        'vectors/J4Route.xml',
        'vectors/CoreRoute.xml']

    _PointTypeStart = 0x00
    _PointTypeLine = 0x01
    _PointTypeMask = 0x07
    _PointTypeCloseSubpath = 0x80

    def __init__(
            self,
            graphics: cartographer.AbstractGraphics
            ) -> None:
        self._graphics = graphics
        self.borders = self._loadFiles(VectorStore._BorderFiles)
        self.rifts = self._loadFiles(VectorStore._RiftFiles)
        self.routes = self._loadFiles(VectorStore._RouteFiles)

    def _loadFiles(
            self,
            paths: typing.Iterable[str]
            ) -> typing.List[VectorObject]:
        vectors = []
        for path in paths:
            try:
                vectors.extend(self._parseFile(
                    content=multiverse.SnapshotManager.instance().loadTextResource(
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
                mapOptions |= cartographer.RenderOptions[option]

        originX = 0
        element = rootElement.find('./OriginX')
        if element is not None:
            originX = float(element.text)

        originY = 0
        element = rootElement.find('./OriginY')
        if element is not None:
            originY = float(element.text)

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

        bounds = cartographer.RectangleF(
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

            points.append(cartographer.PointF(x=x, y=y))

        element = rootElement.find('./PathDataTypes')
        types = None
        if points and element is not None:
            types = base64.b64decode(element.text)
            finishIndex = len(points) - 1
            sectionPoints = []
            vectorObjects = []

            for currentIndex, (point, type) in enumerate(zip(points, types)):
                isStartPoint = (type & VectorStore._PointTypeMask) == \
                    VectorStore._PointTypeStart
                isLastPoint = currentIndex == finishIndex
                isClosed = (type & VectorStore._PointTypeCloseSubpath) == \
                    VectorStore._PointTypeCloseSubpath

                if isClosed or isLastPoint:
                    sectionPoints.append(point)

                if (isStartPoint and sectionPoints) or isClosed or isLastPoint:
                    isFirstVector = not vectorObjects
                    vectorObjects.append(VectorObject(
                        name=name if isFirstVector else '', # Only set name on first to avoid multiple rendering
                        originX=originX,
                        originY=originY,
                        scaleX=scaleX,
                        scaleY=scaleY,
                        nameX=nameX,
                        nameY=nameY,
                        bounds=bounds,
                        path=self._graphics.createPath(points=sectionPoints, closed=isClosed),
                        mapOptions=mapOptions))
                    sectionPoints.clear()

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
                path=self._graphics.createPath(points=points, closed=False) if points else None,
                mapOptions=mapOptions)]
