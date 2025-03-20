import base64
import maprenderer
import os
import travellermap
import typing
import xml.etree.ElementTree

# TODO: Revisit this class, I suspect it could be more efficient
# TODO: This should probably live elsewhere
class VectorObject(object):
    def __init__(
            self,
            graphics: maprenderer.AbstractGraphics,
            name: str,
            originX: float,
            originY: float,
            scaleX: float,
            scaleY: float,
            nameX: float,
            nameY: float,
            points: typing.Sequence[maprenderer.PointF],
            types: typing.Optional[typing.Sequence[maprenderer.PathPointType]] = None,
            bounds: typing.Optional[maprenderer.RectangleF] = None,
            closed: bool = False,
            mapOptions: maprenderer.MapOptions = 0
            ) -> None:
        super().__init__()

        if types and (len(points) != len(types)):
            raise ValueError('VectorObject path point and type vectors have different lengths')

        self._graphics = graphics
        self.name = name
        self.originX = originX
        self.originY = originY
        self.scaleX = scaleX
        self.scaleY = scaleY
        self.nameX = nameX
        self.nameY = nameY
        self.closed = closed
        self.mapOptions = mapOptions
        self._pathDataPoints = [maprenderer.PointF(p) for p in points]
        self._pathDataTypes = list(types) if types else None
        self._minScale = None
        self._maxScale = None
        self._cachedBounds = maprenderer.RectangleF(bounds) if bounds else None
        self._cachedPath: typing.Optional[maprenderer.AbstractPath] = None

    @property
    def pathDataPoints(self) -> typing.Sequence[maprenderer.PointF]:
        return self._pathDataPoints

    @property
    def bounds(self) -> maprenderer.RectangleF:
        # Compute bounds if not already set
        if (not self._cachedBounds) and self.pathDataPoints:
            left = right = top = bottom = None
            for point in self._pathDataPoints:
                if (not left) or (point.x() < left):
                    left = point.x()
                if (not right) or (point.x() > right):
                    right = point.x()
                if (not top) or (point.y() < top):
                    top = point.y()
                if (not bottom) or (point.y() > bottom):
                    bottom = point.y()
            self._cachedBounds = maprenderer.RectangleF(
                x=left,
                y=top,
                width=right - left,
                height=bottom - top)
        # TODO: Returning a copy is wasteful, is it needed?
        return maprenderer.RectangleF(self._cachedBounds) # Don't return internal copy

    @property
    def pathDataTypes(self) -> typing.List[int]:
        if not self._pathDataPoints:
            raise RuntimeError('Invalid VectorObject - PathDataPoints required')

        if not self._pathDataTypes:
            self._pathDataTypes = [maprenderer.PathPointType.Start]
            for _ in range(1, len(self._pathDataPoints)):
                self._pathDataTypes.append(maprenderer.PathPointType.Line)

        return self._pathDataTypes

    @property
    def path(self) -> maprenderer.AbstractPath:
        if not self.pathDataPoints:
            raise RuntimeError('Invalid VectorObject - PathDataPoints required')
        if not self._cachedPath:
            self._cachedPath = self._graphics.createPath(
                points=self.pathDataPoints,
                types=self.pathDataTypes,
                closed=self.closed)
        return self._cachedPath

    # TODO: I don't like the fact this is here, all rendering should be in the render context
    def draw(
            self,
            graphics: maprenderer.AbstractGraphics,
            rect: maprenderer.RectangleF,
            pen: maprenderer.AbstractPen
            ) -> None:
        transformedBounds = self._transformedBounds()
        if transformedBounds.intersectsWith(rect):
            with graphics.save():
                graphics.scaleTransform(scaleX=self.scaleX, scaleY=self.scaleY)
                graphics.translateTransform(dx=-self.originX, dy=-self.originY)
                graphics.drawPath(path=self.path, pen=pen)

    def drawName(
            self,
            graphics: maprenderer.AbstractGraphics,
            rect: maprenderer.RectangleF,
            font: maprenderer.AbstractFont,
            textBrush: maprenderer.AbstractBrush,
            labelStyle: maprenderer.LabelStyle
            ) -> None:
        transformedBounds = self._transformedBounds()
        if self.name and transformedBounds.intersectsWith(rect):
            str = self.name
            if labelStyle.uppercase:
                str = str.upper()
            pos = self._namePosition()

            with graphics.save():
                # TODO: Need to check rotation works here, GREAT RIFT text should be rotated (when I add support for it)
                graphics.translateTransform(dx=pos.x(), dy=pos.y())
                graphics.scaleTransform(
                    scaleX=1.0 / travellermap.ParsecScaleX,
                    scaleY=1.0 / travellermap.ParsecScaleY)
                graphics.rotateTransform(-labelStyle.rotation)

                maprenderer.drawStringHelper(
                    graphics=graphics,
                    text=str,
                    font=font,
                    brush=textBrush,
                    x=0, y=0)

    def _transformedBounds(self) -> maprenderer.RectangleF:
        bounds = self.bounds

        # TODO: I think subtraction and multiply could be combined in
        # single update
        bounds.setX(bounds.x() - self.originX)
        bounds.setY(bounds.y() - self.originY)

        bounds.setX(bounds.x() * self.scaleX)
        bounds.setY(bounds.y() * self.scaleY)
        bounds.setWidth(bounds.width() * self.scaleX)
        bounds.setHeight(bounds.height() * self.scaleY)
        if bounds.width() < 0:
            bounds.setX(bounds.x() + bounds.width())
            bounds.setWidth(-bounds.width())
        if bounds.height() < 0:
            bounds.setY(bounds.y() + bounds.height())
            bounds.setHeight(-bounds.height())

        return bounds

    def _namePosition(self) -> maprenderer.PointF:
        bounds = self.bounds
        transformedBounds = self._transformedBounds()
        center = transformedBounds.centre()
        center.setX(center.x() + (transformedBounds.width() * (self.nameX / bounds.width())))
        center.setY(center.y() + (transformedBounds.height() * (self.nameY / bounds.height())))

        return center

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
                # TODO: Do something better
                print(ex)
        return vectors

    def _parseFile(self, content: str) -> typing.Iterable[VectorObject]:
        rootElement = xml.etree.ElementTree.fromstring(content)

        name = ''
        element = rootElement.find('./Name')
        if element is not None:
            name = element.text

        mapOptions = 0
        element = rootElement.find('./MapOptions')
        if element is not None:
            for option in element.text.split():
                try:
                    mapOptions |= maprenderer.MapOptions[option]
                except Exception as ex:
                    # TODO: Do something better
                    print(ex)

        originX = 0
        element = rootElement.find('./OriginX')
        if element is not None:
            originX = float(element.text)

        originY = 0
        element = rootElement.find('./OriginY')
        if element is not None:
            originY= float(element.text)

        scaleX = 1 # TODO: Not sure about this default
        element = rootElement.find('./ScaleX')
        if element is not None:
            scaleX = float(element.text)

        scaleY = 1 # TODO: Not sure about this default
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

        # TODO: Is this used?
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
        bounds = None
        if xElement is not None and yElement is not None \
            and widthElement is not None and heightElement is not None:
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
        if element is not None:
            types = base64.b64decode(element.text)
            startIndex = 0
            finishIndex = len(points) - 1
            vectorPoints = []
            vectors = []

            for currentIndex, (point, type) in enumerate(zip(points, types)):
                isStartPoint = (type & maprenderer.PathPointType.PathTypeMask) == \
                    maprenderer.PathPointType.Start
                isLastPoint = currentIndex == finishIndex
                isClosed = (type & maprenderer.PathPointType.CloseSubpath) == \
                    maprenderer.PathPointType.CloseSubpath

                if isClosed or isLastPoint:
                    vectorPoints.append(point)

                if (isStartPoint and vectorPoints) or isClosed or isLastPoint:
                    isFirstVector = not vectors
                    nextIndex = currentIndex + (0 if isStartPoint else 1)
                    vectors.append(VectorObject(
                        graphics=self._graphics,
                        name=name if isFirstVector else '', # Only set name on first to avoid multiple rendering
                        originX=originX,
                        originY=originY,
                        scaleX=scaleX,
                        scaleY=scaleY,
                        nameX=nameX,
                        nameY=nameY,
                        points=vectorPoints,
                        types=types[startIndex:nextIndex],
                        bounds=bounds,
                        closed=isClosed,
                        mapOptions=mapOptions))
                    vectorPoints.clear()
                    startIndex = nextIndex

                vectorPoints.append(point)

            return vectors
        else:
            # No path data types so this is just a single path
            return [VectorObject(
                graphics=self._graphics,
                name=name,
                originX=originX,
                originY=originY,
                scaleX=scaleX,
                scaleY=scaleY,
                nameX=nameX,
                nameY=nameY,
                points=points,
                types=types,
                bounds=bounds,
                mapOptions=mapOptions)]