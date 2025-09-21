import app
import cartographer
import common
import gui
import logic
import logging
import math
import multiverse
import typing
import uuid
from PyQt5 import QtWidgets, QtCore, QtGui

class _MapOverlay(object):
    def __init__(self, enabled: bool = True):
        super().__init__()
        self._handle = str(uuid.uuid4())
        self._enabled = enabled

    def handle(self) -> str:
        return self._handle

    def isEnabled(self) -> bool:
        return self._enabled

    def setEnabled(self, enabled: bool) -> None:
        self._enabled = enabled

    # The draw function will be called with the painters coordinate space
    # set to the isotropic space used for overlays. This is basically the
    # same coordinate space that I use for rendering the dots used for
    # worlds at some zoom levels. The primary reason it's used is so I can
    # use the same trick of rendering groups of circles as points with a
    # pen set to the desired circle with. This technique is limited to
    # drawing circles that are the same size and colour but it allows for
    # multiple circles to be drawn with a single QPainter draw call which,
    # for large numbers of circles (100+), is MUCH faster than drawing
    # individual circles with something like drawEllipse. For this technique
    # to work an isotropic space needs to be used otherwise the circles are
    # drawn as ellipses
    def draw(
            self,
            painter: QtGui.QPainter,
            currentScale: gui.MapScale
            ) -> bool: # True if anything was draw
        raise RuntimeError(f'{type(self)} is derived from _MapOverlay so must implement draw')

class _JumpRouteOverlay(_MapOverlay):
    _JumpRouteColour = QtGui.QColor('#7F048104')
    _PitStopColour = QtGui.QColor('#7F8080FF')
    _PitStopRadius = 0.4 # Default to slightly larger than the size of the highlights Traveller Map puts on jump worlds

    def __init__(self) -> None:
        super().__init__()
        self._jumpRoutePath = None
        self._pitStopPoints = None

        self._jumpRoutePen = QtGui.QPen(
            _JumpRouteOverlay._JumpRouteColour,
            1, # Width will be set when rendering as it's dependant on scale
            QtCore.Qt.PenStyle.SolidLine,
            QtCore.Qt.PenCapStyle.FlatCap)
        self._jumpNodePen = QtGui.QPen(
            _JumpRouteOverlay._JumpRouteColour,
            1, # Width will be set when rendering as it's dependant on scale
            QtCore.Qt.PenStyle.SolidLine,
            QtCore.Qt.PenCapStyle.RoundCap)
        self._pitStopPen = QtGui.QPen(
            _JumpRouteOverlay._PitStopColour,
            _JumpRouteOverlay._PitStopRadius * 2,
            QtCore.Qt.PenStyle.SolidLine,
            QtCore.Qt.PenCapStyle.RoundCap)

    def hasJumpRoute(self) -> bool:
        return self._jumpRoutePath is not None

    def setRoute(
            self,
            jumpRoute: typing.Optional[logic.JumpRoute],
            refuellingPlan: typing.Optional[typing.Iterable[logic.PitStop]] = None
            ) -> None:
        if not jumpRoute:
            self._jumpRoutePath = self._pitStopPoints = None
            return

        self._jumpRoutePath = QtGui.QPolygonF()
        for hex in jumpRoute:
            centerX, centerY = hex.worldCenter()
            self._jumpRoutePath.append(QtCore.QPointF(
                centerX * multiverse.ParsecScaleX,
                centerY * multiverse.ParsecScaleY))

        self._pitStopPoints = None
        if refuellingPlan:
            self._pitStopPoints = QtGui.QPolygonF()
            for pitStop in refuellingPlan:
                centerX, centerY = pitStop.hex().worldCenter()
                self._pitStopPoints.append(QtCore.QPointF(
                    centerX * multiverse.ParsecScaleX,
                    centerY * multiverse.ParsecScaleY))

    def draw(
            self,
            painter: QtGui.QPainter,
            currentScale: gui.MapScale
            ) -> None:
        if not self.isEnabled() or not self._jumpRoutePath:
            return False

        lowDetail = currentScale.log < 7
        routeLineWidth = 0.25 if not lowDetail else (15 / currentScale.linear)

        painter.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_Source)

        self._jumpRoutePen.setWidthF(routeLineWidth)
        painter.setPen(self._jumpRoutePen)
        painter.drawPolyline(self._jumpRoutePath)

        self._jumpNodePen.setWidthF(routeLineWidth * 2)
        painter.setPen(self._jumpNodePen)
        if not lowDetail:
            painter.drawPoints(self._jumpRoutePath)
        else:
            painter.drawPoint(self._jumpRoutePath.at(0))
            painter.drawPoint(self._jumpRoutePath.at(self._jumpRoutePath.count() - 1))

        painter.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_SourceOver)
        if self._pitStopPoints:
            painter.setPen(self._pitStopPen)
            painter.drawPoints(self._pitStopPoints)

        return True # Something was drawn

class _HexHighlightOverlay(_MapOverlay):
    _HexPolygon = QtGui.QPolygonF([
        # Upper left
        QtCore.QPointF(
            (-0.5 + multiverse.HexWidthOffset) * multiverse.ParsecScaleX,
            -0.5 * multiverse.ParsecScaleY),
        # Upper right
        QtCore.QPointF(
            (+0.5 - multiverse.HexWidthOffset) * multiverse.ParsecScaleX,
            -0.5 * multiverse.ParsecScaleY),
        # Center right
        QtCore.QPointF(
            (+0.5 + multiverse.HexWidthOffset) * multiverse.ParsecScaleX,
            0 * multiverse.ParsecScaleY) ,
        # Lower right
        QtCore.QPointF(
            (+0.5 - multiverse.HexWidthOffset) * multiverse.ParsecScaleX,
            +0.5 * multiverse.ParsecScaleY),
        # Lower Left
        QtCore.QPointF(
            (-0.5 + multiverse.HexWidthOffset) * multiverse.ParsecScaleX,
            +0.5 * multiverse.ParsecScaleY),
        # Center left
        QtCore.QPointF(
            (-0.5 - multiverse.HexWidthOffset) * multiverse.ParsecScaleX,
            0 * multiverse.ParsecScaleY),
    ])

    def __init__(self):
        super().__init__()

        # NOTE: The radius is stored as an integer in 100ths of a parsec to avoid
        # floating point inaccuracies causing values that are effectively but not
        # exactly equal causing multiple highlights to be created. It means there
        # is limited precision to the radius but it should be good enough that it
        # doesn't actually mater.
        # In theory all this should be redundant at the moment as all the radii
        # that I'm currently using are hard coded values so comparisons would
        # always guarantee an exact match. However, doing it now prevents bugs in
        # the future if I ever end having calculations that determine the radius
        self._styleMap: typing.Dict[
            typing.Tuple[
                gui.MapPrimitiveType,
                typing.Tuple[int, int, int, int], # Colour
                # Integer radius in 100ths of a parsec for Circle primitive type
                # or 0 for Hex
                int],
            typing.Tuple[
                QtGui.QPolygonF,
                # QPen for Circle primitive type or QBrush for hex
                typing.Union[QtGui.QPen, QtGui.QBrush]]
            ] = {}

        self._hexMap: typing.Dict[
            multiverse.HexPosition,
            typing.Set[typing.Tuple[
                gui.MapPrimitiveType,
                typing.Tuple[int, int, int, int], # Colour
                # Integer radius in 100ths of a parsec for Circle primitive type
                # or 0 for Hex
                int]],
            ] = {}

    def addHex(
            self,
            hex: multiverse.HexPosition,
            type: gui.MapPrimitiveType,
            colour: QtGui.QColor,
            radius: float = 0.0 # Only valid if primitive type is Circle
            ) -> None:
        radius = int(round(radius * 100))
        styleKey = (type, colour.getRgb(), radius)

        hexStyleKeys = self._hexMap.get(hex)
        if hexStyleKeys and styleKey in hexStyleKeys:
            # This hex already has a highlight with this style
            return

        renderData = self._styleMap.get(styleKey)
        if renderData is None:
            renderData = (
                QtGui.QPolygonF(),
                _HexHighlightOverlay._createTool(
                    type=type,
                    colour=colour,
                    radius=radius / 100))
            self._styleMap[styleKey] = renderData

        centerX, centerY = hex.worldCenter()
        polygon = renderData[0]
        polygon.append(QtCore.QPointF(
            centerX * multiverse.ParsecScaleX,
            centerY * multiverse.ParsecScaleY))

        if not hexStyleKeys:
            hexStyleKeys = set()
            self._hexMap[hex] = hexStyleKeys
        hexStyleKeys.add(styleKey)

    def addHexes(
            self,
            hexes: typing.Iterable[multiverse.HexPosition],
            type: gui.MapPrimitiveType,
            colour: typing.Optional[QtGui.QColor],
            colourMap: typing.Optional[typing.Mapping[multiverse.HexPosition, QtGui.QColor]] = None,
            radius: float = 0.0 # Only valid if primitive type is Circle
            ) -> None:
        radius = int(round(radius * 100)) if type is gui.MapPrimitiveType.Circle else 0

        styleKey = None
        renderData = None
        if colourMap:
            # There is a colour map so the style needs to be checked
            # for each hex
            styleKey = None
        else:
            # There is no colour map so all hexes are going to have
            # the same style. Do the lookup once rather than for
            # every hex
            styleKey = (type, colour.getRgb(), radius)
            renderData = self._styleMap.get(styleKey)
            if renderData is None:
                renderData = (
                    QtGui.QPolygonF(),
                    _HexHighlightOverlay._createTool(
                        type=type,
                        colour=colour,
                        radius=radius / 100))
                self._styleMap[styleKey] = renderData

        for hex in hexes:
            if colourMap:
                hexColour = colourMap.get(hex, colour)
                if not hexColour:
                    # No specific colour for this hex and no default so nothing
                    # to draw
                    continue
                styleKey = (type, hexColour.getRgb(), radius)
                renderData = self._styleMap.get(styleKey)
                if renderData is None:
                    renderData = (
                        QtGui.QPolygonF(),
                        _HexHighlightOverlay._createTool(
                            type=type,
                            colour=hexColour,
                            radius=radius / 100))
                    self._styleMap[styleKey] = renderData

            hexStyleKeys = self._hexMap.get(hex)
            if hexStyleKeys and styleKey in hexStyleKeys:
                # This hex already has a highlight with this style
                continue

            centerX, centerY = hex.worldCenter()
            polygon = renderData[0]
            polygon.append(QtCore.QPointF(
                centerX * multiverse.ParsecScaleX,
                centerY * multiverse.ParsecScaleY))

            if not hexStyleKeys:
                hexStyleKeys = set()
                self._hexMap[hex] = hexStyleKeys
            hexStyleKeys.add(styleKey)

    def removeHex(
            self,
            hex: multiverse.HexPosition
            ) -> None:
        hexStyleKeys = self._hexMap.get(hex)
        if not hexStyleKeys:
            return # The hex has no highlight to remove

        centerX, centerY = hex.worldCenter()
        for styleKey in hexStyleKeys:
            polygon, _ = self._styleMap[styleKey]
            for i in range(polygon.count() - 1, -1, -1):
                point = polygon.at(i)
                if math.isclose(point.x(), centerX) and math.isclose(point.y(), centerY):
                    polygon.remove(i)
            if polygon.isEmpty():
                # There are no more highlights with this style so remove it from
                # the map
                del self._styleMap[styleKey]

        del self._hexMap[hex]

    def clear(self) -> None:
        self._styleMap.clear()
        self._hexMap.clear()

    def draw(
            self,
            painter: QtGui.QPainter,
            currentScale: gui.MapScale
            ) -> None:
        if not self.isEnabled() or not self._styleMap:
            return False

        painter.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_Source)
        for (type, _, _), (points, tool) in self._styleMap.items():
            if type is gui.MapPrimitiveType.Circle:
                painter.setPen(tool)
                painter.drawPoints(points)
            elif type is gui.MapPrimitiveType.Hex:
                painter.setBrush(tool)
                painter.setPen(QtCore.Qt.PenStyle.NoPen)

                for i in range(points.count()):
                    point = points.at(i)

                    with gui.PainterStateGuard(painter):
                        transform = painter.transform()
                        transform.translate(point.x(), point.y())
                        painter.setTransform(transform)
                        painter.drawPolygon(_HexHighlightOverlay._HexPolygon)

        return True # Something was drawn

    @staticmethod
    def _createTool(
            type: gui.MapPrimitiveType,
            colour: QtGui.QColor,
            radius: float
            ) -> typing.Union[QtGui.QPen, QtGui.QBrush]:
        if type is gui.MapPrimitiveType.Circle:
            return QtGui.QPen(
                colour,
                radius * 2,
                QtCore.Qt.PenStyle.SolidLine,
                QtCore.Qt.PenCapStyle.RoundCap)
        elif type is gui.MapPrimitiveType.Hex:
            return QtGui.QBrush(colour)
        else:
            raise RuntimeError(f'Invalid map primitive type {type}')

class _HexBorderOverlay(_MapOverlay):
    def __init__(
            self,
            hexes: typing.Iterable[multiverse.HexPosition],
            lineColour: typing.Optional[QtGui.QColor] = None,
            lineWidth: typing.Optional[int] = None, # In pixels
            fillColour: typing.Optional[QtGui.QColor] = None,
            includeInterior: bool = True,
            ) -> None:
        super().__init__()

        if includeInterior:
            outlines = logic.calculateCompleteHexOutlines(hexes=hexes)
        else:
            outlines = logic.calculateOuterHexOutlines(hexes=hexes)
        self._polygons: typing.List[QtGui.QPolygonF] = []
        for outline in outlines:
            polygon = QtGui.QPolygonF()
            for x, y in outline:
                polygon.append(QtCore.QPointF(x, y))
            self._polygons.append(polygon)

        self._pen = self._brush = None
        if lineColour:
            self._pen = QtGui.QPen(
                lineColour,
                0) # Line width set at draw time as it's dependent on scale
            self._lineWidth = lineWidth
        if fillColour:
            self._brush = QtGui.QBrush(fillColour)

    def draw(
            self,
            painter: QtGui.QPainter,
            currentScale: gui.MapScale
            ) -> None:
        if not self.isEnabled():
            return False

        painter.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_Source)

        if self._pen:
            self._pen.setWidthF(self._lineWidth / currentScale.linear)
        painter.setPen(self._pen if self._pen else QtCore.Qt.PenStyle.NoPen)

        painter.setBrush(self._brush if self._brush else QtCore.Qt.BrushStyle.NoBrush)

        for polygon in self._polygons:
            painter.drawPolygon(polygon)

        return True # Something was drawn

class _EmpressWaveOverlay(_MapOverlay):
    # The origin is taken from Traveller Map where it's 0, 10000 in its map space
    _WaveOriginHex = multiverse.HexPosition(0, -10000)
    _WaveColour = QtGui.QColor('#4CFFCC00')
    _WaveVelocity = math.pi / 3.26 # Velocity of effect is light speed (so 1 ly/y)

    def __init__(
            self,
            milieu: multiverse.Milieu
            ) -> None:
        super().__init__()
        self._milieu = milieu
        self._pen = QtGui.QPen(
            _EmpressWaveOverlay._WaveColour,
            0) # Width will be set at render time

    def setMilieu(self, milieu: multiverse.Milieu) -> None:
        self._milieu = milieu

    # This code is based on the Traveller Map drawWave code (map.js)
    def draw(
            self,
            painter: QtGui.QPainter,
            currentScale: gui.MapScale
            ) -> None:
        if not self.isEnabled():
            return False

        year = multiverse.milieuToYear(milieu=self._milieu)

        w = 1 #pc

        # Per MWM: center is 10000pc coreward
        x, y = _EmpressWaveOverlay._WaveOriginHex.absolute()
        x *= multiverse.ParsecScaleX
        y *= multiverse.ParsecScaleY

        # Per MWM: Wave crosses Ring 10,000 [Reference] on 045-1281
        radius = (year - (1281 + (45 - 1) / 365)) * _EmpressWaveOverlay._WaveVelocity - y
        if radius < 0:
            return False

        rect = QtCore.QRectF(
            (x - radius) + 0.5,
            (y - radius) - 0.5,
            radius * 2,
            radius * 2)
        painter.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_Source)
        self._pen.setWidthF(max(w, 5 / currentScale.linear))
        painter.setPen(self._pen)

        start = math.degrees(math.pi / 2 - math.pi / 12) + 180
        finish = math.degrees(math.pi / 2 + math.pi / 12) + 180
        painter.drawArc(rect, int(start * 16), int((finish - start) * 16))

        return True # Something was drawn

class _QrekrshaZoneOverlay(_MapOverlay):
    # This center position was taken from Traveller Map where it's
    # -179.4, 131 in its map space
    _CenterHex = multiverse.HexPosition(-207,  -131)
    _ZoneColour = QtGui.QColor('#4CFFCC00')

    def __init__(self) -> None:
        super().__init__()
        self._pen = QtGui.QPen(
            _QrekrshaZoneOverlay._ZoneColour,
            0) # Width will be set at render time

    # This code is based on the Traveller Map drawQZ code (map.js)
    def draw(
            self,
            painter: QtGui.QPainter,
            currentScale: gui.MapScale
            ) -> None:
        if not self.isEnabled():
            return False

        x, y = _QrekrshaZoneOverlay._CenterHex.absolute()
        x *= multiverse.ParsecScaleX
        y *= multiverse.ParsecScaleY

        radius = 30 * multiverse.ParsecScaleX

        rect = QtCore.QRectF(
            (x - radius) + 0.5,
            (y - radius) - 0.5,
            radius * 2,
            radius * 2)
        painter.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_Source)
        self._pen.setWidthF(max(1, 5 / currentScale.linear))
        painter.setPen(self._pen)
        painter.drawArc(rect, 0, 360 * 16)

        return True # Something was drawn

class _AntaresSupernovaOverlay(_MapOverlay):
    _SupernovaColour = QtGui.QColor('#26FFCC00')
    _SupernovaCenter = multiverse.HexPosition(55, -59) # Antares
    _SupernovaVelocity = 1 / 3.26 # Velocity of effect is light speed (so 1 ly/y)

    def __init__(
            self,
            milieu: multiverse.Milieu
            ) -> None:
        super().__init__()
        self._milieu = milieu
        self._brush = QtGui.QBrush(
            _AntaresSupernovaOverlay._SupernovaColour)

    def setMilieu(self, milieu: multiverse.Milieu) -> None:
        self._milieu = milieu

    # This code is based on the Traveller Map drawAS code (map.js)
    def draw(
            self,
            painter: QtGui.QPainter,
            currentScale: gui.MapScale
            ) -> None:
        if not self.isEnabled():
            return False

        year = multiverse.milieuToYear(milieu=self._milieu)
        yearRadius = (year - 1270) * _AntaresSupernovaOverlay._SupernovaVelocity
        if yearRadius < 0:
            return False

        # Center is Antares (ANT 2421)
        x, y = _AntaresSupernovaOverlay._SupernovaCenter.worldCenter()
        x *= multiverse.ParsecScaleX
        y *= multiverse.ParsecScaleY

        for section, sectionRadius in enumerate([0.5, 4, 8, 12]):
            # Date of supernova: 1270
            radius = min(yearRadius, sectionRadius)
            rect = QtCore.QRectF(
                x - radius,
                y - radius,
                radius * 2,
                radius * 2)
            painter.setBrush(self._brush)
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.drawEllipse(rect)

        return True # Something was drawn

class _MainsOverlay(_MapOverlay):
    _SmallMainColour = QtGui.QColor('#3FFFC0CB')
    _MediumMainColour = QtGui.QColor('#3FFFCC00')
    _LargeMainColour = QtGui.QColor('#3F00FFFF')
    _PointSize = 1.15

    def __init__(self) -> None:
        super().__init__()
        self._points = None
        self._pen = None

    def setMain(self, main: typing.Optional[multiverse.Main]) -> None:
        if not main:
            self._points = self._pen = None
            return

        self._points = QtGui.QPolygonF()
        for world in main:
            centerX, centerY = world.hex().worldCenter()
            self._points.append(QtCore.QPointF(
                centerX * multiverse.ParsecScaleX,
                centerY * multiverse.ParsecScaleY))

        if len(main) <= 10:
            colour = _MainsOverlay._SmallMainColour
        elif len(main) < 50:
            colour = _MainsOverlay._MediumMainColour
        else:
            colour = _MainsOverlay._LargeMainColour

        self._pen = QtGui.QPen(
            colour,
            _MainsOverlay._PointSize,
            QtCore.Qt.PenStyle.SolidLine,
            QtCore.Qt.PenCapStyle.RoundCap)

    # This code is based on the Traveller Map drawQZ code (map.js)
    def draw(
            self,
            painter: QtGui.QPainter,
            currentScale: gui.MapScale
            ) -> None:
        if not self.isEnabled() or not self._points or not self._pen:
            return False

        painter.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_Source)
        painter.setPen(self._pen)
        painter.drawPoints(self._points)

        return True # Something was drawn

class _MoveKeyTracker(object):
    _LeftKeys = [
        QtCore.Qt.Key.Key_Left,
        QtCore.Qt.Key.Key_J, # Taken from Traveller Map
        QtCore.Qt.Key.Key_A]
    _RightKeys = [
        QtCore.Qt.Key.Key_Right,
        QtCore.Qt.Key.Key_L, # Taken from Traveller Map
        QtCore.Qt.Key.Key_D]
    _UpKeys = [
        QtCore.Qt.Key.Key_Up,
        QtCore.Qt.Key.Key_I, # Taken from Traveller Map
        QtCore.Qt.Key.Key_W]
    _DownKeys = [
        QtCore.Qt.Key.Key_Down,
        QtCore.Qt.Key.Key_K, # Taken from Traveller Map
        QtCore.Qt.Key.Key_S]
    _TrackedKeys = set(_LeftKeys + _RightKeys + _UpKeys + _DownKeys)

    def __init__(self) -> None:
        self._trackedKeys: typing.Set[QtCore.Qt.Key] = set()

    def direction(self) -> typing.Tuple[int, int]:
        x = y = 0

        if any(key in _MoveKeyTracker._LeftKeys for key in self._trackedKeys):
            x -= 1
        if any(key in _MoveKeyTracker._RightKeys for key in self._trackedKeys):
            x += 1
        if any(key in _MoveKeyTracker._UpKeys for key in self._trackedKeys):
            y -= 1
        if any(key in _MoveKeyTracker._DownKeys for key in self._trackedKeys):
            y += 1

        return (x, y)

    def keyDown(self, event: QtGui.QKeyEvent) -> bool:
        key = event.key()
        if key in _MoveKeyTracker._TrackedKeys:
            if not event.isAutoRepeat():
                self._trackedKeys.add(key)
            return True
        return False

    def keyUp(self, event: QtGui.QKeyEvent) -> bool:
        key = event.key()
        if key in _MoveKeyTracker._TrackedKeys:
            if not event.isAutoRepeat():
                if key in self._trackedKeys:
                    self._trackedKeys.remove(key)
            return True
        return False

    def isIdle(self) -> bool:
        return len(self._trackedKeys) == 0

    def clear(self) -> None:
        self._trackedKeys.clear()

class _MoveAnimationEasingCurve(QtCore.QEasingCurve):
    def __init__(
            self,
            normAccelPeriod: float = 0, # Normalised to duration of animation
            normDecelPeriod: float = 0 # Normalised to duration of animation
            ) -> None:
        super().__init__()
        self._normAccelPeriod = normAccelPeriod
        self._normDecelPeriod = normDecelPeriod
        self.setCustomType(self.extrapolate)

    def setPeriods(
            self,
            normAccelPeriod: float, # Normalised to duration of animation
            normDecelPeriod: float # Normalised to duration of animation
            ) -> None:
        self._normAccelPeriod = normAccelPeriod
        self._normDecelPeriod = normDecelPeriod

    def extrapolate(self, normProgress: float) -> float: # Returns value is normalized
        if not self._normAccelPeriod and not self._normDecelPeriod:
            return normProgress
        return self._travellerMapSmoothingFunction(
            time=normProgress,
            duration=1, # QEasingCurve uses normalised progress/time
            accelPeriod=self._normAccelPeriod,
            decelPeriod=self._normDecelPeriod)

    # This is the same algorithm Traveller Map uses (smooth in map.js)
    #
    # Time smoothing function - input time is t within duration dur.
    # Acceleration period is a, deceleration period is d.
    #
    # Example:     t_filtered = smooth( t, 1.0, 0.25, 0.25 );
    #
    # Reference:   http://www.w3.org/TR/2005/REC-SMIL2-20050107/smil-timemanip.html
    @staticmethod
    def _travellerMapSmoothingFunction(
            time: float,
            duration: float,
            accelPeriod: float,
            decelPeriod: float
            ) -> float:
        dacc = duration * accelPeriod
        ddec = duration * decelPeriod
        r = 1 / (1 - accelPeriod / 2 - decelPeriod / 2)

        if time < dacc:
            r_t = r * (time / dacc)
            return time * r_t / 2
        elif time <= (duration - ddec):
            return r * (time - dacc / 2)
        else:
            tdec = time - (duration - ddec)
            pd = tdec / ddec
            return r * (duration - dacc / 2 - ddec + tdec * (2 - pd) / 2)

class MapWidget(QtWidgets.QWidget):
    centerChanged = QtCore.pyqtSignal(QtCore.QPointF)
    scaleChanged = QtCore.pyqtSignal(gui.MapScale)
    leftClicked = QtCore.pyqtSignal(multiverse.HexPosition)
    rightClicked = QtCore.pyqtSignal(multiverse.HexPosition)

    _MinLogScale = -5
    _MaxLogScale = 10
    _DefaultCenterX = 0
    _DefaultCenterY = 0
    _DefaultLogScale = gui.linearScaleToLogScale(64)

    _WheelZoomDelta = 0.15
    _KeyboardZoomDelta = 0.5
    _KeyboardMoveDelta = 40 # Pixels

    # NOTE: The delay between keyboard movement updates can't be to low or it
    # causes the tile rendering queue to stall and you just end up scrolling
    # over background checkerboard
    _KeyboardMovementTimerMs = 30

    _MoveAnimationTimeMs = 1000

    _TileSize = 256 # Pixels
    _TileCacheSize = 1000 # Number of tiles
    _TileRenderTimerMs = 1
    _LookaheadBorderTiles = 2

    _CheckerboardColourA = '#000000'
    _CheckerboardColourB = '#404040'
    _CheckerboardRectSize = 16

    _DirectionTextFontFamily = 'Arial'
    _DirectionTextFontSize = 12
    _DirectionTextIndent = 10

    _ScaleTextFontFamily = 'Arial'
    _ScaleTextFontSize = 10
    _ScaleLineIndent = 10
    _ScaleLineTickHeight = 10
    _ScaleLineWidth = 2

    # Number of pixels of movement we allow between the left mouse button down and up events for
    # the action to be counted as a click. I found that forcing no movement caused clicks to be
    # missed
    _LeftClickMoveThreshold = 3

    # NOTE: This is LocalMapWidget for legacy reasons. The class was renamed as
    # part of the work to remove the legacy web map widget but the state
    # structure didn't change
    _StateVersion = 'LocalMapWidget_v1'

    # TODO: I don't like the fact this has the universe in the key
    # TODO: If I do keep the universe as part of the key I need to check there
    # is no perf degradation
    _sharedTileCache = common.LRUCache[
        typing.Tuple[
            int, # Tile X
            int, # Tile Y
            int,
            multiverse.Universe,
            multiverse.Milieu,
            cartographer.MapStyle,
            int], # MapOptions as an int
        QtGui.QImage](capacity=_TileCacheSize)

    # PyQt5 has a limitation of 10 custom easing curve functions being
    # registered over the lifetime of the application (i.e. setCustomType) and
    # there doesn't seem to be a way to unregister them. As each instance of
    # _MoveAnimationEasingCurve registers it's own callback this limit of 10 is
    # reached after creating 10 instances of the class. I'm not sure if this is
    # really a sign that I'm not implementing QEasingCurve correctly but I'm
    # not sure how I should be doing it. For now I've come up with the hacky
    # workaround of creating a shared cache of easing curve objects that can
    # be used by instances of the widget as they need them. If no curve is
    # available when a widget needs one it will skip the animation and do an
    # immediate move.
    _sharedEasingCurves: typing.List[_MoveAnimationEasingCurve] = None
    # The number of curves needs to be kept low as it will limit the number
    # of custom curves that could be used elsewhere in the app. It only makes
    # sense for it to be a multiple of 2 as a widget uses 2 curves to animate
    # a move.
    _sharedEasingCurveMaxCount = 4

    def __init__(
            self,
            universe: multiverse.Universe,
            milieu: multiverse.Milieu,
            style: cartographer.MapStyle,
            options: typing.Collection[app.MapOption],
            rendering: app.MapRendering,
            animated: bool,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent=parent)

        if MapWidget._sharedEasingCurves is None:
            MapWidget._sharedEasingCurves = []
            for _ in range(MapWidget._sharedEasingCurveMaxCount):
                MapWidget._sharedEasingCurves.append(_MoveAnimationEasingCurve())

        self._universe = universe
        self._milieu = milieu
        self._style = style
        self._options = set(options)
        self._rendering = rendering
        self._animated = animated
        self._locked = False

        scene = QtWidgets.QGraphicsScene()
        scene.setSceneRect(0, 0, self.width(), self.height())

        # NOTE: The view center is in world coordinates
        self._viewCenter = QtCore.QPointF(MapWidget._DefaultCenterX, MapWidget._DefaultCenterY)
        self._viewScale = gui.MapScale(log=MapWidget._DefaultLogScale)
        self._imageSpaceToWorldSpace = None
        self._imageSpaceToOverlaySpace = None

        self._upperLeftViewLimit = None
        self._lowerRightViewLimit = None
        self._minViewScale = None
        self._maxViewScale = None

        self._mapGraphics = gui.MapGraphics()
        self._imageStore = cartographer.ImageStore(graphics=self._mapGraphics)
        self._vectorStore = cartographer.VectorStore(graphics=self._mapGraphics)
        self._labelStore = cartographer.LabelStore(universe=self._universe)
        self._styleStore = cartographer.StyleStore()
        self._renderer = self._newRenderer()

        self._worldDragAnchor: typing.Optional[QtCore.QPointF] = None
        self._pixelDragStart: typing.Optional[QtCore.QPoint] = None

        # Off screen buffer used when not using tile rendering to prevent
        # Windows font scaling messing up the size of rendered text on a
        # 4K+ screen
        self._isWindows = common.isWindows()
        self._offscreenRenderImage: typing.Optional[QtGui.QImage] = None

        self._tileRenderTimer = QtCore.QTimer()
        self._tileRenderTimer.setInterval(MapWidget._TileRenderTimerMs)
        self._tileRenderTimer.setSingleShot(True)
        self._tileRenderTimer.timeout.connect(self._handleRenderTileTimer)
        self._tileRenderQueue: typing.List[typing.Tuple[
            int, # Tile X
            int, # Tile Y
            int # Tile Scale (linear)
            ]] = []
        self._forceAtomicRedraw = False

        self._placeholderTile = MapWidget._createPlaceholderTile()

        self._directionTextFont = QtGui.QFont(
            MapWidget._DirectionTextFontFamily,
            MapWidget._DirectionTextFontSize)
        self._directionTextFont.setBold(True)
        self._directionTextPen = QtGui.QPen(
            QtGui.QColor(common.HtmlColours.TravellerRed),
            0)

        self._scaleFont = QtGui.QFont(
            MapWidget._ScaleTextFontFamily,
            MapWidget._ScaleTextFontSize)
        self._scalePen = QtGui.QPen(
            QtGui.QColor(common.HtmlColours.Black), # Colour will be updated when drawn
            MapWidget._ScaleLineWidth,
            QtCore.Qt.PenStyle.SolidLine,
            QtCore.Qt.PenCapStyle.FlatCap)

        # This is a staging buffer used when generating an overlay in order
        # to get a consistent alpha blend level when the overlay consists
        # of multiple overlapping primitives. The idea is that the overlay
        # set to have a transparent background then the overlay is rendered
        # to it without any alpha, the staging image is then applied on top
        # of the final image with the alpha value required by the overlay.
        self._overlayStagingImage: typing.Optional[QtGui.QImage] = None

        self._overlayMap: typing.Dict[
            str, # Overlay handle
            _MapOverlay] = {}

        self._jumpRoute = None
        self._refuellingPlan = None
        self._jumpRouteOverlay = _JumpRouteOverlay()
        self._overlayMap[self._jumpRouteOverlay.handle()] = self._jumpRouteOverlay

        self._hexHighlightOverlay = _HexHighlightOverlay()
        self._overlayMap[self._hexHighlightOverlay.handle()] = self._hexHighlightOverlay

        self._empressWaveOverlay = _EmpressWaveOverlay(milieu=self._milieu)
        self._empressWaveOverlay.setEnabled(
            enabled=app.MapOption.EmpressWaveOverlay in self._options)
        self._overlayMap[self._empressWaveOverlay.handle()] = self._empressWaveOverlay

        self._qrekrshaZoneOverlay = _QrekrshaZoneOverlay()
        self._qrekrshaZoneOverlay.setEnabled(
            enabled=app.MapOption.QrekrshaZoneOverlay in self._options)
        self._overlayMap[self._qrekrshaZoneOverlay.handle()] = self._qrekrshaZoneOverlay

        self._antaresSupernovaOverlay = _AntaresSupernovaOverlay(milieu=self._milieu)
        self._antaresSupernovaOverlay.setEnabled(
            enabled=app.MapOption.AntaresSupernovaOverlay in self._options)
        self._overlayMap[self._antaresSupernovaOverlay.handle()] = self._antaresSupernovaOverlay

        self._mainsOverlay = _MainsOverlay()
        self._mainsOverlay.setEnabled(
            enabled=app.MapOption.MainsOverlay in self._options)
        self._overlayMap[self._mainsOverlay.handle()] = self._mainsOverlay

        # NOTE: It looks like Qt has a hard limitation fo 10 easing curve
        # objects for the entire app so need to create them when needed
        # (which means creating the animations when needed) and make sure
        # they're destroyed after use. If I didn't I would get this error
        # after a bit:
        # ValueError: a maximum of 10 different easing functions are supported
        self._viewCenterAnimationEasing = None
        self._viewScaleAnimationEasing = None
        self._viewCenterAnimation = None
        self._viewScaleAnimation = None
        self._viewAnimationGroup = None

        # This set keeps track of the move keys that are currently held
        # down. Movement is then processed on a timer. This is done to
        # give smoother movement and allows things like diagonal movement
        # by holding down multiple keys at once
        self._keyboardMovementTracker = _MoveKeyTracker()
        self._keyboardMovementTimer = QtCore.QTimer()
        self._keyboardMovementTimer.setInterval(MapWidget._KeyboardMovementTimerMs)
        self._keyboardMovementTimer.setSingleShot(False)
        self._keyboardMovementTimer.timeout.connect(self._handleKeyboardMovementTimer)

        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)

        self._updateView()

    def universe(self) -> multiverse.Universe:
        return self._universe

    def setUniverse(
            self,
            universe: multiverse.Universe
            ) -> None:
        if universe is self._universe:
            return

        self._universe = universe

        self._labelStore = cartographer.LabelStore(universe=self._universe)

        self._renderer = self._newRenderer()

        # Clear the main when the universe changes as the main may have
        # changed
        self._mainsOverlay.setMain(main=None)

        self.update() # Force redraw

    def milieu(self) -> multiverse.Milieu:
        return self._milieu

    def setMilieu(self, milieu: multiverse.Milieu) -> None:
        if milieu is self._milieu:
            return

        self._milieu = milieu
        self._renderer = self._newRenderer()

        self._empressWaveOverlay.setMilieu(milieu=self._milieu)
        self._antaresSupernovaOverlay.setMilieu(milieu=self._milieu)

        # Clear the main when the milieu changes as the main may have
        # changed
        self._mainsOverlay.setMain(main=None)

        self.update() # Force redraw

    def mapStyle(self) -> cartographer.MapStyle:
        return self._style

    def setMapStyle(self, style: cartographer.MapStyle) -> None:
        if style is self._style:
            return

        self._style = style
        self._renderer = self._newRenderer()

        self.update() # Force redraw

    def mapOptions(self) -> typing.List[app.MapOption]:
        return list(self._options)

    def setMapOptions(self, options: typing.Collection[app.MapOption]) -> None:
        options = set(options)
        if options == self._options:
            return

        self._options = options
        self._renderer = self._newRenderer()

        self._empressWaveOverlay.setEnabled(
            enabled=app.MapOption.EmpressWaveOverlay in self._options)
        self._qrekrshaZoneOverlay.setEnabled(
            enabled=app.MapOption.QrekrshaZoneOverlay in self._options)
        self._antaresSupernovaOverlay.setEnabled(
            enabled=app.MapOption.AntaresSupernovaOverlay in self._options)
        self._mainsOverlay.setEnabled(
            enabled=app.MapOption.MainsOverlay in self._options)

        self.update() # Force redraw

    def modifyMapOptions(
            self,
            add: typing.Optional[typing.Union[
                app.MapOption,
                typing.Collection[app.MapOption]]] = None,
            remove: typing.Optional[typing.Union[
                app.MapOption,
                typing.Collection[app.MapOption]]] = None
            ) -> None:
        options = set(self._options)

        if isinstance(add, app.MapOption):
            options.add(add)
        elif add is not None:
            for option in add:
                options.add(option)

        if isinstance(remove, app.MapOption):
            if remove in options:
                options.remove(remove)
        elif remove is not None:
            for option in remove:
                if option in options:
                    options.remove(option)

        self.setMapOptions(options=options)

    def rendering(self) -> app.MapRendering:
        return self._rendering

    def setRendering(self, rendering: app.MapRendering) -> None:
        if rendering == self._rendering:
            return

        self._rendering = rendering

        self.update() # Force redraw

    def isAnimated(self) -> bool:
        return self._animated

    def setAnimated(self, animated: bool) -> None:
        if animated == self._animated:
            return

        self._animated = animated

    def isLocked(self) -> bool:
        return self._locked

    def setLocked(self, locked: bool) -> None:
        if locked == self._locked:
            return

        self._locked = locked
        if self._locked:
            self._pixelDragStart = self._worldDragAnchor = None
            self._keyboardMovementTracker.clear()

    def setView(
            self,
            center: typing.Optional[QtCore.QPointF] = None, # Center in World coordinates
            scale: typing.Optional[gui.MapScale] = None,
            immediate: bool = False
            ) -> None:
        center = self._viewCenter if center is None else QtCore.QPointF(center)
        center = self._clampCenter(center=center)

        scale = self._viewScale if scale is None else gui.MapScale(scale)
        scale = self._clampScale(scale=scale)

        self._stopMoveAnimation()

        if not immediate:
            immediate = not self._shouldAnimateViewTransition(
                newViewCenter=center,
                newViewScale=scale)

        if immediate:
            self._updateView(
                center=center,
                scale=scale,
                forceAtomicRedraw=True)
        else:
            self._startMoveAnimation(
                newViewCenter=center,
                newViewScale=scale)

    def viewCenter(self) -> QtCore.QPointF:
        return QtCore.QPointF(self._viewCenter)

    def setViewCenter(
            self,
            center: QtCore.QPointF, # Center in World coordinates
            immediate: bool = False
            ) -> None:
        self.setView(center=center, immediate=immediate)

    def viewScale(self) -> gui.MapScale:
        return gui.MapScale(self._viewScale)

    def setViewScale(
            self,
            scale: gui.MapScale,
            immediate: bool = False
            ) -> None:
        self.setView(scale=scale, immediate=immediate)

    def viewAreaLimits(self) -> typing.Tuple[
            QtCore.QPointF, # Upper Left
            QtCore.QPointF]: # Lower Right
        return (
            QtCore.QPointF(self._upperLeftViewLimit) if self._upperLeftViewLimit else None,
            QtCore.QPointF(self._lowerRightViewLimit) if self._lowerRightViewLimit else None)

    def setViewAreaLimits(
            self,
            upperLeft: typing.Optional[QtCore.QPointF], # In World coordinates
            lowerRight: typing.Optional[QtCore.QPointF] # In World coordinates
            ) -> None:
        if upperLeft and lowerRight:
            self._upperLeftViewLimit = QtCore.QPointF(
                min(upperLeft.x(), lowerRight.x()),
                min(upperLeft.y(), lowerRight.y()))

            self._lowerRightViewLimit = QtCore.QPointF(
                max(upperLeft.x(), lowerRight.x()),
                max(upperLeft.y(), lowerRight.y()))
        elif upperLeft:
            self._upperLeftViewLimit = QtCore.QPointF(upperLeft)
            self._lowerRightViewLimit = None
        elif lowerRight:
            self._upperLeftViewLimit = None
            self._lowerRightViewLimit = QtCore.QPointF(lowerRight)
        else:
            self._upperLeftViewLimit = None
            self._lowerRightViewLimit = None

    def viewScaleLimits(self) -> typing.Tuple[
            typing.Optional[gui.MapScale], # Min Scale
            typing.Optional[gui.MapScale]]: # Max Scale
        return (
            gui.MapScale(self._minViewScale) if self._minViewScale else None,
            gui.MapScale(self._maxViewScale) if self._maxViewScale else None)

    def setViewScaleLimits(
            self,
            minScale: typing.Optional[gui.MapScale],
            maxScale: typing.Optional[gui.MapScale]
            ) -> None:
        if minScale and maxScale and maxScale < minScale:
            minScale, maxScale = maxScale, minScale

        self._minViewScale = gui.MapScale(minScale)
        self._maxViewScale = gui.MapScale(maxScale)

        self._updateView()

    def fullRedraw(self) -> None:
        if self._renderer:
            self._renderer.clearCaches()
        self._clearTileCache()

    def hexAt(
            self,
            pos: typing.Union[QtCore.QPoint, QtCore.QPointF]
            ) -> multiverse.HexPosition:
        return self._pixelSpaceToHex(pixelPos=pos)

    def worldAt(
            self,
            pos: typing.Union[QtCore.QPoint, QtCore.QPointF]
            ) -> typing.Optional[multiverse.World]:
        hex = self._pixelSpaceToHex(pixelPos=pos)
        return self._universe.worldByPosition(
            milieu=self._milieu,
            hex=hex)

    def centerOnHex(
            self,
            hex: multiverse.HexPosition,
            scale: typing.Optional[gui.MapScale] = gui.MapScale(linear=64), # None keeps current scale
            immediate: bool = False
            ) -> None:
        self.setView(
            center=QtCore.QPointF(*hex.worldCenter()),
            scale=scale,
            immediate=immediate)

    def centerOnHexes(
            self,
            hexes: typing.Collection[multiverse.HexPosition],
            immediate: bool = False
            ) -> None:
        self._stopMoveAnimation()

        if not hexes:
            return

        left = right = top = bottom = None
        for hex in hexes:
            hexLeft, hexTop, hexWidth, hexHeight = hex.worldBounds()
            if left is None or hexLeft < left:
                left = hexLeft
            if top is None or hexTop < top:
                top = hexTop
            if right is None or (hexLeft + hexWidth) > right:
                right = hexLeft + hexWidth
            if bottom is None or (hexTop + hexHeight) > bottom:
                bottom = hexTop + hexHeight

        width = right - left
        height = bottom - top
        center = QtCore.QPointF(
            left + (width / 2),
            top + (height / 2))
        logScale = common.clamp(
            value=min(
                gui.linearScaleToLogScale(self.width() / width),
                gui.linearScaleToLogScale(self.height() / height)),
            minValue=MapWidget._MinLogScale,
            maxValue=MapWidget._MaxLogScale)

        self.setView(
            center=center,
            scale=gui.MapScale(log=logScale),
            immediate=immediate)

    def hasJumpRoute(self) -> bool:
        return self._jumpRoute is not None

    def setJumpRoute(
            self,
            jumpRoute: typing.Optional[logic.JumpRoute],
            refuellingPlan: typing.Optional[typing.Iterable[logic.PitStop]] = None
            ) -> None:
        self._jumpRoute = jumpRoute
        self._refuellingPlan = refuellingPlan
        self._jumpRouteOverlay.setRoute(
            jumpRoute=jumpRoute,
            refuellingPlan=refuellingPlan)
        self.update()

    def clearJumpRoute(self) -> None:
        self._jumpRoute = self._refuellingPlan = None
        self._jumpRouteOverlay.setRoute(jumpRoute=None)
        self.update()

    def centerOnJumpRoute(
            self,
            immediate: bool = False
            ) -> None:
        if not self._jumpRoute:
            return
        self.centerOnHexes(
            hexes=self._jumpRoute.nodes(),
            immediate=immediate)

    def highlightHex(
            self,
            hex: multiverse.HexPosition,
            radius: float = 0.5,
            colour: str = QtGui.QColor('#7F8080FF')
            ) -> None:
        self._hexHighlightOverlay.addHex(
            hex=hex,
            type=gui.MapPrimitiveType.Circle,
            colour=colour,
            radius=radius)
        self.update() # Trigger redraw

    def highlightHexes(
            self,
            hexes: typing.Iterable[multiverse.HexPosition],
            radius: float = 0.5,
            colour: QtGui.QColor = QtGui.QColor('#7F8080FF')
            ) -> None:
        self._hexHighlightOverlay.addHexes(
            hexes=hexes,
            type=gui.MapPrimitiveType.Circle,
            colour=colour,
            radius=radius)
        self.update() # Trigger redraw

    def clearHexHighlight(
            self,
            hex: multiverse.HexPosition
            ) -> None:
        self._hexHighlightOverlay.removeHex(hex)
        self.update() # Trigger redraw

    def clearHexHighlights(self) -> None:
        self._hexHighlightOverlay.clear()
        self.update() # Trigger redraw

    # Create an overlay with a primitive at each hex
    def createHexOverlay(
            self,
            hexes: typing.Iterable[multiverse.HexPosition],
            primitive: gui.MapPrimitiveType,
            fillColour: typing.Optional[QtGui.QColor] = None,
            fillMap: typing.Optional[typing.Mapping[
                multiverse.HexPosition,
                QtGui.QColor
            ]] = None,
            radius: float = 0.5 # Only used for circle primitive
            ) -> str:
        overlay = _HexHighlightOverlay()
        overlay.addHexes(
            hexes=hexes,
            type=primitive,
            colour=fillColour,
            colourMap=fillMap,
            radius=radius)
        self._overlayMap[overlay.handle()] = overlay

        self.update() # Trigger redraw
        return overlay.handle()

    def createHexBordersOverlay(
            self,
            hexes: typing.Iterable[multiverse.HexPosition],
            lineColour: typing.Optional[QtGui.QColor] = None,
            lineWidth: typing.Optional[int] = None, # In pixels
            fillColour: typing.Optional[QtGui.QColor] = None,
            includeInterior: bool = True
            ) -> str:
        overlay = _HexBorderOverlay(
            hexes=hexes,
            lineColour=lineColour,
            lineWidth=lineWidth,
            fillColour=fillColour,
            includeInterior=includeInterior)
        self._overlayMap[overlay.handle()] = overlay

        self.update() # Trigger redraw
        return overlay.handle()

    def removeOverlay(
            self,
            handle: str
            ) -> None:
        if handle not in self._overlayMap:
            return
        del self._overlayMap[handle]
        self.update() # Trigger redraw

    def createPixmap(self) -> QtGui.QPixmap:
        image = QtGui.QPixmap(self.size())

        rendering = self._rendering
        if rendering is app.MapRendering.Tiled:
            # If tiled rendering is currently in use force hybrid so any
            # missing tiles will be created
            rendering = app.MapRendering.Hybrid

        self._drawView(
            paintDevice=image,
            rendering=rendering)
        return image

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(MapWidget._StateVersion)
        stream.writeFloat(self._viewCenter.x())
        stream.writeFloat(self._viewCenter.y())
        stream.writeFloat(self._viewScale.log)
        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != MapWidget._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore LocalMapWidget state (Incorrect version)')
            return False

        center = QtCore.QPointF(stream.readFloat(), stream.readFloat())
        scale = gui.MapScale(log=stream.readFloat())
        self._updateView(center=center, scale=scale)
        return True

    # I've disabled doing a full redraw on first show as it's to slow at some
    # scales so causes windows that contain the widget to display all white
    # for a noticeable amount of time when first opened
    """
    def showEvent(self, e: QtGui.QShowEvent) -> None:
        if not e.spontaneous():
            # Force an atomic redraw when the widget is first shown so the user
            # doesn't see the tiles draw in
            self._forceAtomicRedraw = True
            self.update()
        return super().showEvent(e)
    """

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        # The user is interacting with the view so stop any in progress
        # transition animation or they will just end up fighting it
        self._stopMoveAnimation()

        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            if not self._locked:
                self._pixelDragStart = event.pos()
                self._worldDragAnchor = self._pixelSpaceToWorldSpace(self._pixelDragStart)

            event.accept()
            return

        #super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        if not self._locked and self._worldDragAnchor:
            worldCurrentPos = self._pixelSpaceToWorldSpace(event.pos())
            worldDeltaX = worldCurrentPos.x() - self._worldDragAnchor.x()
            worldDeltaY = worldCurrentPos.y() - self._worldDragAnchor.y()

            newViewCenter = QtCore.QPointF(
                self._viewCenter.x() - worldDeltaX,
                self._viewCenter.y() - worldDeltaY)
            self._updateView(center=newViewCenter)

        event.accept()

        #super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        leftRelease = event.button() == QtCore.Qt.MouseButton.LeftButton
        rightRelease = event.button() == QtCore.Qt.MouseButton.RightButton

        if leftRelease or rightRelease:
            if not self._locked:
                pixelReleasePos = QtCore.QPointF(event.x(), event.y())

                if leftRelease and self._pixelDragStart:
                    clickRect = QtCore.QRectF(
                        self._pixelDragStart.x() - self._LeftClickMoveThreshold,
                        self._pixelDragStart.y() - self._LeftClickMoveThreshold,
                        self._LeftClickMoveThreshold * 2,
                        self._LeftClickMoveThreshold * 2)

                    self._worldDragAnchor = self._pixelDragStart = None

                    if not clickRect.contains(pixelReleasePos):
                        event.accept()
                        return # A drag was performed so it doesn't count as a click

                hex = self._pixelSpaceToHex(pixelReleasePos)
                if leftRelease:
                    self._handleLeftClickEvent(hex)
                else:
                    self._handleRightClickEvent(hex)

            event.accept()
            return

        super().mouseReleaseEvent(event)

    def focusOutEvent(self, event: QtGui.QFocusEvent) -> None:
        super().focusOutEvent(event)
        self._worldDragAnchor = self._pixelDragStart = None
        self._keyboardMovementTracker.clear()
        self._keyboardMovementTimer.stop()

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        self._updateView()

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        # The user is interacting with the view so stop any in progress
        # transition animation or they will just end up fighting it
        self._stopMoveAnimation()

        if not self._locked:
            if self._keyboardMovementTracker.keyDown(event):
                if not self._keyboardMovementTimer.isActive():
                    self._keyboardMovementTimer.start()
                event.accept()
                return
            elif event.key() == QtCore.Qt.Key.Key_Z:
                self._zoomView(
                    step=MapWidget._KeyboardZoomDelta if not gui.isShiftKeyDown() else -MapWidget._KeyboardZoomDelta)
                event.accept()
                return
            elif event.key() == QtCore.Qt.Key.Key_Plus or event.key() == QtCore.Qt.Key.Key_Equal:
                self._zoomView(step=MapWidget._KeyboardZoomDelta)
                event.accept()
                return
            elif event.key() == QtCore.Qt.Key.Key_Minus:
                self._zoomView(step=-MapWidget._KeyboardZoomDelta)
                event.accept()
                return

        super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QtGui.QKeyEvent):
        if not self._locked:
            if self._keyboardMovementTracker.keyUp(event):
                if self._keyboardMovementTracker.isIdle():
                    self._keyboardMovementTimer.stop()
                event.accept()
                return

        super().keyReleaseEvent(event)

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        # The user is interacting with the view so stop any in progress
        # transition animation or they will just end up fighting it
        self._stopMoveAnimation()

        if not self._locked:
            self._zoomView(
                step=MapWidget._WheelZoomDelta if event.angleDelta().y() > 0 else -MapWidget._WheelZoomDelta,
                cursor=event.pos())

        event.accept()
        #super().wheelEvent(event)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        if not self._mapGraphics or not self._renderer:
            return super().paintEvent(event)

        viewRect = event.rect()

        rendering = self._rendering
        if rendering is app.MapRendering.Tiled and self._forceAtomicRedraw:
            # Render any missing tiles now rather than in the background. Hybrid
            # rendering is used rather than Full as we want the same digital
            # zooming between log scales that you would get with Background
            # rendering
            rendering = app.MapRendering.Hybrid

        if self._isWindows:
            # On Windows the view is rendered to an offscreen image then blitted
            # to the screen. This is done to prevent text being scaled by
            # Windows font scaling on 4K+ screens
            needsNewImage = self._offscreenRenderImage is None or \
                self._offscreenRenderImage.width() != self.width() or \
                self._offscreenRenderImage.height() != self.height()
            if needsNewImage:
                self._offscreenRenderImage = QtGui.QImage(
                    self.width(),
                    self.height(),
                    QtGui.QImage.Format.Format_ARGB32)
        else:
            self._offscreenRenderImage = None

        self._drawView(
            paintDevice=self._offscreenRenderImage if self._offscreenRenderImage is not None else self,
            rendering=rendering,
            viewRect=viewRect)

        if rendering is app.MapRendering.Tiled or \
                rendering is app.MapRendering.Hybrid:
            if not self._tileRenderQueue and MapWidget._LookaheadBorderTiles:
                # If there are no tiles needing loaded, pre-load tiles just
                # outside the current view area.
                self._loadLookaheadTiles()

            # Start the timer to trigger loading of missing tiles. It's
            # important to re-check the tile queue as it may have had
            # lookahead tiles added
            if self._tileRenderQueue:
                self._tileRenderTimer.start()

        if self._offscreenRenderImage is not None:
            painter = QtGui.QPainter()
            with gui.PainterDrawGuard(painter, self):
                painter.drawImage(
                    viewRect,
                    self._offscreenRenderImage,
                    viewRect)

        self._forceAtomicRedraw = False

    def _clampCenter(self, center: QtCore.QPointF) -> QtCore.QPointF:
        center = QtCore.QPointF(center)
        if self._upperLeftViewLimit:
            if center.x() < self._upperLeftViewLimit.x():
                center.setX(self._upperLeftViewLimit.x())
            if center.y() < self._upperLeftViewLimit.y():
                center.setY(self._upperLeftViewLimit.y())
        if self._lowerRightViewLimit:
            if center.x() > self._lowerRightViewLimit.x():
                center.setX(self._lowerRightViewLimit.x())
            if center.y() > self._lowerRightViewLimit.y():
                center.setY(self._lowerRightViewLimit.y())
        return center

    def _clampScale(self, scale: gui.MapScale) -> gui.MapScale:
        if self._minViewScale and scale < self._minViewScale:
            scale = self._minViewScale
        if self._maxViewScale and scale > self._maxViewScale:
            scale = self._maxViewScale
        return scale

    def _drawView(
            self,
            paintDevice: QtGui.QPaintDevice,
            rendering: app.MapRendering,
            viewRect: typing.Optional[QtCore.QRect] = None
            ) -> None:
        if viewRect is None:
            viewRect = self.rect()

        painter = QtGui.QPainter()
        with gui.PainterDrawGuard(painter, paintDevice):
            painter.setBrush(QtCore.Qt.GlobalColor.black)
            painter.drawRect(viewRect)
            painter.setClipRect(viewRect)

            self._drawMap(painter, rendering, viewRect)
            self._drawOverlays(painter)
            self._drawScale(painter)
            self._drawDirections(painter)

    def _drawMap(
            self,
            painter: QtGui.QPainter,
            rendering: app.MapRendering,
            viewRect: QtCore.QRect
            ) -> None:
        if rendering is app.MapRendering.Tiled or \
                rendering is app.MapRendering.Hybrid:
            tiles = self._currentDrawTiles(
                viewRect=viewRect,
                createMissing=rendering is not app.MapRendering.Tiled)

            # This is disabled as I think it actually makes scaled tiles
            # look worse (a bit to blurry)
            #painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform, True)

            for image, renderRect, clipRect in tiles:
                with gui.PainterStateGuard(painter):
                    if clipRect:
                        clipPath = QtGui.QPainterPath()
                        clipPath.setFillRule(QtCore.Qt.FillRule.WindingFill)
                        clipPath.addRect(clipRect)
                        # Add the new clip path, intersecting it with any current clip path
                        painter.setClipPath(clipPath, operation=QtCore.Qt.ClipOperation.IntersectClip)
                    else:
                        # Manually scale the image if needed as drawImage does a piss poor job.
                        # This is only done when there is no clip rect. A clip rect means it's
                        # a placeholder tile so won't be drawn for very long so quality doesn't
                        # mater as much so best to avoid the expensive scaling
                        if image.width() != renderRect.width() or image.height() != renderRect.height():
                            image = image.smoothScaled(
                                round(renderRect.width()),
                                round(renderRect.height()))

                    painter.drawImage(renderRect, image)
        else:
            clipRect = None
            if viewRect != self.rect():
                clipRect = (viewRect.x(), viewRect.y(), viewRect.width(), viewRect.height())

            self._mapGraphics.setPainter(painter=painter)
            try:
                self._renderer.setView(
                    worldCenterX=self._viewCenter.x(),
                    worldCenterY=self._viewCenter.y(),
                    scale=self._viewScale.linear,
                    outputPixelWidth=self.width(),
                    outputPixelHeight=self.height(),
                    clipRect=clipRect)
                self._renderer.render()
            finally:
                self._mapGraphics.setPainter(painter=None)

    def _drawOverlays(
            self,
            painter: QtGui.QPainter
            ) -> None:
        if not self._overlayStagingImage or \
                self._overlayStagingImage.width() != self.width() or \
                self._overlayStagingImage.height() != self.height():
            self._overlayStagingImage = QtGui.QImage(
                self.width(),
                self.height(),
                QtGui.QImage.Format.Format_ARGB32_Premultiplied)

        for overlay in self._overlayMap.values():
            self._overlayStagingImage.fill(QtCore.Qt.GlobalColor.transparent)

            try:
                stagingPainter = QtGui.QPainter()
                with gui.PainterDrawGuard(stagingPainter, self._overlayStagingImage):
                    stagingPainter.setTransform(self._imageSpaceToOverlaySpace)

                    # Draw the overlay to the staging image
                    somethingWasDrawn = overlay.draw(
                        painter=stagingPainter,
                        currentScale=self._viewScale)

                    if somethingWasDrawn:
                        # Draw the staging image
                        painter.drawImage(
                            QtCore.QRectF(0, 0, self.width(), self.height()),
                            self._overlayStagingImage)
            except:
                continue

    def _drawScale(
            self,
            painter: QtGui.QPainter
            ) -> None:
        distance = (self.width() / self._viewScale.linear) / 10

        factor = math.pow(10, math.floor(math.log(distance) / math.log(10)))
        distance = math.floor(distance / factor) * factor
        label = common.formatNumber(number=distance, decimalPlaces=1, suffix=' pc')
        distance *= self._viewScale.linear

        scaleRight = self.width() - MapWidget._ScaleLineIndent
        scaleLeft = scaleRight - int(distance)
        scaleY = self.height() - MapWidget._ScaleLineIndent

        fontMetrics = QtGui.QFontMetricsF(self._scaleFont)
        labelRect = fontMetrics.tightBoundingRect(label)

        self._scalePen.setColor(QtGui.QColor(
            common.HtmlColours.White
            if gui.isDarkMapStyle(self._renderer.style()) else
            common.HtmlColours.Black))

        with gui.PainterStateGuard(painter):
            painter.setPen(self._scalePen)
            painter.setFont(self._scaleFont)
            painter.drawText(
                QtCore.QPointF(
                    scaleLeft + ((distance / 2) - (labelRect.width() / 2)),
                    scaleY - MapWidget._ScaleLineIndent),
                label)

            painter.drawLine(
                QtCore.QPointF(scaleLeft - (MapWidget._ScaleLineWidth / 2), scaleY),
                QtCore.QPointF(scaleRight + (MapWidget._ScaleLineWidth / 2), scaleY))
            painter.drawLine(
                QtCore.QPointF(scaleLeft, scaleY),
                QtCore.QPointF(scaleLeft, scaleY - MapWidget._ScaleLineTickHeight))
            painter.drawLine(
                QtCore.QPointF(scaleRight, scaleY),
                QtCore.QPointF(scaleRight, scaleY - MapWidget._ScaleLineTickHeight))

    _DirectionLabels = [
        # Text, Rotation, X View Alignment, Y View Alignment
        ('COREWARD', 0, 0, -1),
        ('RIMWARD', 0, 0, 1),
        ('SPINWARD', 270, -1, 0),
        ('TRAILING', 270, 1, 0)]

    def _drawDirections(
            self,
            painter: QtGui.QPainter
            ) -> None:
        if not self._directionTextFont or app.MapOption.GalacticDirections not in self._options:
            return

        viewWidth = self.width()
        viewHeight = self.height()

        fontMetrics = QtGui.QFontMetricsF(self._directionTextFont)

        with gui.PainterStateGuard(painter):
            painter.setFont(self._directionTextFont)
            painter.setPen(self._directionTextPen)
            for text, angle, alignX, alignY in MapWidget._DirectionLabels:
                textRect = fontMetrics.boundingRect(text)
                textRect.moveTo(
                    -textRect.width() / 2,
                    -textRect.height() / 2)
                textHeight = textRect.height()
                with gui.PainterStateGuard(painter):
                    if alignX:
                        offsetX = (textHeight / 2) + MapWidget._DirectionTextIndent
                        if alignX > 0:
                            offsetX = viewWidth - offsetX
                    else:
                        offsetX = (viewWidth / 2)

                    if alignY:
                        offsetY = (textHeight / 2) + MapWidget._DirectionTextIndent
                        if alignY > 0:
                            offsetY = viewHeight - offsetY
                    else:
                        offsetY = (viewHeight / 2)

                    transform = painter.transform()
                    transform.translate(offsetX, offsetY)
                    transform.rotate(angle, QtCore.Qt.Axis.ZAxis)
                    painter.setTransform(transform)

                    painter.drawText(
                        textRect,
                        QtCore.Qt.AlignmentFlag.AlignCenter,
                        text)

    def _handleLeftClickEvent(
            self,
            hex: typing.Optional[multiverse.HexPosition]
            ) -> None:
        if hex and self.isEnabled():
            if app.MapOption.MainsOverlay in self._options:
                main = self._universe.mainByPosition(
                    milieu=self._milieu,
                    hex=hex)
                self._mainsOverlay.setMain(main)
                self.update() # Trigger redraw

            self.leftClicked.emit(hex)

    def _handleRightClickEvent(
            self,
            hex: typing.Optional[multiverse.HexPosition]
            ) -> None:
        if hex and self.isEnabled():
            self.rightClicked.emit(hex)

    def _pixelSpaceToWorldSpace(
            self,
            pixelPos: typing.Union[QtCore.QPointF, QtCore.QPoint]
            ) -> QtCore.QPointF:
        scaleX = (self._viewScale.linear * multiverse.ParsecScaleX)
        scaleY = (self._viewScale.linear * multiverse.ParsecScaleY)

        width = self.width() / scaleX
        height = self.height() / scaleY

        offsetX = pixelPos.x() / scaleX
        offsetY = pixelPos.y() / scaleY

        return QtCore.QPointF(
            (self._viewCenter.x() - (width / 2)) + offsetX,
            (self._viewCenter.y() - (height / 2)) + offsetY)

    def _worldSpaceToPixelSpace(
            self,
            worldPos: typing.Union[QtCore.QPointF, QtCore.QPoint]
            ) -> QtCore.QPointF:
        scaleX = (self._viewScale.linear * multiverse.ParsecScaleX)
        scaleY = (self._viewScale.linear * multiverse.ParsecScaleY)

        width = self.width() / scaleX
        height = self.height() / scaleY

        offsetX = worldPos.x() - (self._viewCenter.x() - (width / 2))
        offsetY = worldPos.y() - (self._viewCenter.y() - (height / 2))

        return QtCore.QPointF(
            offsetX * scaleX,
            offsetY * scaleY)

    def _pixelSpaceToHex(
            self,
            pixelPos: typing.Union[QtCore.QPointF, QtCore.QPoint]
            ) -> multiverse.HexPosition:
        return self._worldSpaceToHex(self._pixelSpaceToWorldSpace(pixelPos))

    def _worldSpaceToHex(
            self,
            worldPos: typing.Union[QtCore.QPointF, QtCore.QPoint]
            ) -> multiverse.HexPosition:
        absoluteX = int(round(worldPos.x() + 0.5))
        absoluteY = int(round(worldPos.y() + (0.5 if (absoluteX % 2 == 0) else 0)))

        return multiverse.HexPosition(
            absoluteX=absoluteX,
            absoluteY=absoluteY)

    def _newRenderer(self) -> cartographer.RenderContext:
        return cartographer.RenderContext(
            universe=self._universe,
            graphics=self._mapGraphics,
            worldCenterX=self._viewCenter.x(),
            worldCenterY=self._viewCenter.y(),
            scale=self._viewScale.linear,
            outputPixelX=self.width(),
            outputPixelY=self.height(),
            milieu=self._milieu,
            style=self._style,
            options=gui.mapOptionsToRenderOptions(self._options),
            imageStore=self._imageStore,
            styleStore=self._styleStore,
            vectorStore=self._vectorStore,
            labelStore=self._labelStore)

    def _updateView(
            self,
            center: typing.Optional[QtCore.QPointF] = None,
            scale: typing.Optional[gui.MapScale] = None,
            forceAtomicRedraw: bool = False
            ) -> None:
        center = self._clampCenter(center=self._viewCenter if center is None else center)
        centerChanged = center != self._viewCenter
        self._viewCenter = center

        scale = self._clampScale(scale=self._viewScale if scale is None else scale)
        scaleChanged = scale != self._viewScale
        self._viewScale = scale

        worldWidth = self.width() / (self._viewScale.linear * multiverse.ParsecScaleX)
        worldHeight = self.height() / (self._viewScale.linear * multiverse.ParsecScaleY)
        worldLeft = self._viewCenter.x() - (worldWidth / 2)
        worldTop = self._viewCenter.y() - (worldHeight / 2)

        self._imageSpaceToWorldSpace = QtGui.QTransform()
        self._imageSpaceToWorldSpace.scale(
            self._viewScale.linear * multiverse.ParsecScaleX,
            self._viewScale.linear * multiverse.ParsecScaleY)
        self._imageSpaceToWorldSpace.translate(
            -worldLeft,
            -worldTop)

        scaleMatrix = QtGui.QTransform()
        scaleMatrix.scale(
            1 / multiverse.ParsecScaleX,
            1 / multiverse.ParsecScaleY)
        self._imageSpaceToOverlaySpace = scaleMatrix * self._imageSpaceToWorldSpace

        # Clear the tile queue as the render view/style map have
        # changed so previous queue map be invalid. The redraw
        # that is triggered will refill the queue if needed
        self._tileRenderQueue.clear()
        self._tileRenderTimer.stop()

        self._forceAtomicRedraw = forceAtomicRedraw

        self.update() # Trigger redraw

        if centerChanged:
            self.centerChanged.emit(QtCore.QPointF(self._viewCenter))

        if scaleChanged:
            self.scaleChanged.emit(gui.MapScale(self._viewScale))

    def _zoomView(
            self,
            step: float,
            cursor: typing.Optional[QtCore.QPoint] = None
            ) -> None:
        if cursor:
            oldWorldCursor = self._pixelSpaceToWorldSpace(cursor)

        logViewScale = self._viewScale.log
        logViewScale += step
        logViewScale = common.clamp(logViewScale, MapWidget._MinLogScale, MapWidget._MaxLogScale)
        if logViewScale == self._viewScale.log:
            return # Reached min/max zoom
        newViewScale = gui.MapScale(log=logViewScale)

        newViewCenter = None
        if cursor:
            # This code is just doing _pixelSpaceToWorldSpace except it's
            # using the scale that we are going to apply rather than the
            # current scale
            scaleX = (newViewScale.linear * multiverse.ParsecScaleX)
            scaleY = (newViewScale.linear * multiverse.ParsecScaleY)

            width = self.width() / scaleX
            height = self.height() / scaleY

            offsetX = cursor.x() / scaleX
            offsetY = cursor.y() / scaleY

            newWorldCursor = QtCore.QPointF(
                (self._viewCenter.x() - (width / 2)) + offsetX,
                (self._viewCenter.y() - (height / 2)) + offsetY)

            # Calculate the new view center so that the cursor stays at
            # the same world position
            newViewCenter = QtCore.QPointF(
                self._viewCenter.x() + (oldWorldCursor.x() - newWorldCursor.x()),
                self._viewCenter.y() + (oldWorldCursor.y() - newWorldCursor.y()))

        self._updateView(center=newViewCenter, scale=newViewScale)

    def _currentDrawTiles(
            self,
            viewRect: QtCore.QRect,
            createMissing: bool = False
            ) -> typing.Iterable[typing.Tuple[
                QtGui.QImage,
                QtCore.QRectF, # Render rect
                typing.Optional[QtCore.QRectF], # Clip rect
                ]]:
        # This method of rounding the scale is intended to match how it would
        # be rounded by the Traveller Map Javascript code which uses Math.round
        # https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Math/round
        tileScale = int(math.floor(self._viewScale.log + 0.5))

        tileMultiplier = math.pow(2, self._viewScale.log - tileScale)
        tileSize = MapWidget._TileSize * tileMultiplier

        scaleX = (self._viewScale.linear * multiverse.ParsecScaleX)
        scaleY = (self._viewScale.linear * multiverse.ParsecScaleY)

        worldWidgetWidth = self.width() / scaleX
        worldWidgetHeight = self.height() / scaleY
        worldWidgetLeft = self._viewCenter.x() - (worldWidgetWidth / 2)
        worldWidgetTop = self._viewCenter.y() - (worldWidgetHeight / 2)

        worldViewLeft = worldWidgetLeft + (viewRect.x() / scaleX)
        worldViewRight = worldViewLeft + (viewRect.width() / scaleX)
        worldViewTop = worldWidgetTop + (viewRect.y() / scaleY)
        worldViewBottom = worldViewTop + (viewRect.height() / scaleY)

        worldTileWidth = tileSize / scaleX
        worldTileHeight = tileSize / scaleY
        leftTile = math.floor(worldViewLeft / worldTileWidth)
        rightTile = math.floor(worldViewRight / worldTileWidth)
        topTile = math.floor(worldViewTop / worldTileHeight)
        bottomTile = math.floor(worldViewBottom / worldTileHeight)

        offsetX = ((worldWidgetLeft - (leftTile * worldTileWidth)) * scaleX)
        offsetY = ((worldWidgetTop - (topTile * worldTileHeight)) * scaleY)

        tiles = []
        for x in range(leftTile, rightTile + 1):
            for y in range(topTile, bottomTile + 1):
                image = self._lookupTile(
                    tileX=x,
                    tileY=y,
                    tileScale=tileScale,
                    createMissing=createMissing)
                renderRect = QtCore.QRectF(
                    ((x - leftTile) * tileSize) - offsetX,
                    ((y - topTile) * tileSize) - offsetY,
                    tileSize,
                    tileSize)
                if image:
                    tiles.append((image, renderRect, None))
                else:
                    placeholders = self._gatherPlaceholderTiles(
                        currentScale=tileScale,
                        tileRect=renderRect,
                        viewRect=viewRect)
                    if placeholders:
                        tiles.extend(placeholders)

        if self._tileRenderQueue:
            self._optimiseTileQueue()

        return tiles

    def _optimiseTileQueue(self) -> None:
        targetWorld = self._viewCenter

        if not self._keyboardMovementTracker.isIdle():
            # If there are tiles needing rendered and the user is currently
            # panning the view, sort the tiles so that the ones in the direction
            # of movement will be rendered first
            dirX, dirY = self._keyboardMovementTracker.direction()
            if dirX or dirY:
                viewPixelWidth = self.width()
                viewHalfPixelWidth = viewPixelWidth / 2
                viewPixelHeight = self.height()
                viewHalfPixelHeight = viewPixelHeight / 2

                targetPixel = QtCore.QPointF(
                    viewHalfPixelWidth + (dirX * viewHalfPixelWidth),
                    viewHalfPixelHeight + (dirY * viewHalfPixelHeight))
                targetWorld = self._pixelSpaceToWorldSpace(targetPixel)
        else:
            cursorPos = self.mapFromGlobal(QtGui.QCursor.pos())
            isCursorOverWindow = cursorPos.x() >= 0 and cursorPos.x() < self.width() and \
                cursorPos.y() >= 0 and cursorPos.y() < self.height()
            if isCursorOverWindow:
                # If the cursor is over the window, fan out from the cursor
                # position when generating tiles
                targetWorld = self._pixelSpaceToWorldSpace(cursorPos)

        tileScale = int(math.floor(self._viewScale.log + 0.5))
        tileMultiplier = math.pow(2, self._viewScale.log - tileScale)
        tilePixelSize = MapWidget._TileSize * tileMultiplier
        tileWorldWidth = tilePixelSize / (self._viewScale.linear * multiverse.ParsecScaleX)
        tileWorldHeight = tilePixelSize / (self._viewScale.linear * multiverse.ParsecScaleY)
        targetTileX = int(math.floor(targetWorld.x() / tileWorldWidth))
        targetTileY = int(math.floor(targetWorld.y() / tileWorldHeight))

        # Sort tiles by the square of the distance between them in tile space.
        # The square of the distance is used for speed as we don't need exact
        # distance, just distance relative to other tiles being compared.
        # NOTE: There is a massive assumption here that the tiles to be rendered
        # are all the same scale as the tile scale used when calculating the
        # target tile.
        self._tileRenderQueue.sort(
            key=lambda tile: ((targetTileX - tile[0]) ** 2) + ((targetTileY - tile[1]) ** 2))

    def _tileSortFunction(
            self,
            tileX,
            tileY,
            tileScale,
            worldTarget: QtCore.QPointF
            ) -> float:
        tileMultiplier = math.pow(2, self._viewScale.log - tileScale)
        tileSize = MapWidget._TileSize * tileMultiplier

        pixelTileCenter = QtCore.QPointF(
            (tileX * tileSize) + (tileSize / 2),
            (tileY * tileSize) + (tileSize / 2))
        worldTileCenter = self._pixelSpaceToWorldSpace(pixelTileCenter)

        distance = math.hypot(
            worldTarget.x() - worldTileCenter.x(),
            worldTarget.y() - worldTileCenter.y())
        return distance

    def _loadLookaheadTiles(self) -> None:
        # This method of rounding the scale is intended to match how it would
        # be rounded by the Traveller Map Javascript code which uses Math.round
        # https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Math/round
        tileScale = int(math.floor(self._viewScale.log + 0.5))

        tileMultiplier = math.pow(2, self._viewScale.log - tileScale)
        tileSize = MapWidget._TileSize * tileMultiplier

        scaleX = (self._viewScale.linear * multiverse.ParsecScaleX)
        scaleY = (self._viewScale.linear * multiverse.ParsecScaleY)
        worldViewWidth = self.width() / scaleX
        worldViewHeight = self.height() / scaleY
        worldViewLeft = self._viewCenter.x() - (worldViewWidth / 2)
        worldViewRight = worldViewLeft + worldViewWidth
        worldViewTop = self._viewCenter.y() - (worldViewHeight / 2)
        worldViewBottom = worldViewTop + worldViewHeight

        worldTileWidth = tileSize / scaleX
        worldTileHeight = tileSize / scaleY
        leftTile = math.floor(worldViewLeft / worldTileWidth)
        rightTile = math.floor(worldViewRight / worldTileWidth)
        topTile = math.floor(worldViewTop / worldTileHeight)
        bottomTile = math.floor(worldViewBottom / worldTileHeight)

        for _ in range(MapWidget._LookaheadBorderTiles):
            leftTile -= 1
            rightTile += 1
            topTile -= 1
            bottomTile += 1

            for x in range(leftTile, rightTile):
                self._lookupTile(
                    tileX=x,
                    tileY=topTile,
                    tileScale=tileScale,
                    createMissing=False)
            for y in range(topTile, bottomTile):
                self._lookupTile(
                    tileX=rightTile,
                    tileY=y,
                    tileScale=tileScale,
                    createMissing=False)
            for x in range(rightTile, leftTile, -1):
                self._lookupTile(
                    tileX=x,
                    tileY=bottomTile,
                    tileScale=tileScale,
                    createMissing=False)
            for y in range(bottomTile, topTile, -1):
                self._lookupTile(
                    tileX=leftTile,
                    tileY=y,
                    tileScale=tileScale,
                    createMissing=False)

    def _lookupTile(
            self,
            tileX: int,
            tileY: int,
            tileScale: int, # Log scale rounded down,
            createMissing: bool
            ) -> typing.Optional[QtGui.QImage]:
        tileCacheKey = (
            tileX,
            tileY,
            tileScale,
            self._universe,
            self._milieu,
            self._renderer.style(),
            int(self._renderer.options()))
        image = self._sharedTileCache.get(tileCacheKey)
        if not image:
            if not createMissing:
                # Add the tile to the queue of tiles to be created in the background
                requiredTile = (tileX, tileY, tileScale)
                if requiredTile not in self._tileRenderQueue:
                    self._tileRenderQueue.append(requiredTile)
            else:
                # Render the tile
                image = None
                if self._sharedTileCache.isFull():
                    # Reuse oldest cached tile
                    _, image = self._sharedTileCache.pop()
                image = self._renderTile(tileX, tileY, tileScale, image)
                self._sharedTileCache[tileCacheKey] = image
        return image

    def _gatherPlaceholderTiles(
            self,
            currentScale: int,
            tileRect: QtCore.QRectF,
            viewRect: QtCore.QRect
            ) -> typing.List[typing.Tuple[
                QtGui.QImage,
                QtCore.QRectF, # Render rect
                typing.Optional[QtCore.QRectF]]]: # Clip rect
        clipRect = tileRect.intersected(QtCore.QRectF(viewRect))

        placeholders = self._findPlaceholderTiles(
            currentScale=currentScale,
            tileRect=tileRect,
            clipRect=clipRect,
            viewRect=viewRect,
            lookLower=True)
        if placeholders:
            return placeholders

        placeholders = self._findPlaceholderTiles(
            currentScale=currentScale,
            tileRect=tileRect,
            clipRect=clipRect,
            viewRect=viewRect,
            lookLower=False)
        if placeholders:
            return placeholders

        # No alternate tiles found so use standard placeholder
        return [(self._placeholderTile, tileRect, clipRect)]

    def _findPlaceholderTiles(
            self,
            currentScale: int,
            tileRect: QtCore.QRectF, # Pixel space
            clipRect: QtCore.QRectF, # Pixel space
            viewRect: QtCore.QRect, # Pixel space
            lookLower: bool
            ) -> typing.Iterable[typing.Tuple[
                QtGui.QImage,
                QtCore.QRectF, # Render rect
                typing.Optional[QtCore.QRectF]]]: # Clip rect
        placeholderScale = currentScale + (-1 if lookLower else 1)
        if placeholderScale < MapWidget._MinLogScale or placeholderScale > MapWidget._MaxLogScale:
            return[]

        tileMultiplier = math.pow(2, self._viewScale.log - placeholderScale)
        tileSize = MapWidget._TileSize * tileMultiplier

        scaleX = (self._viewScale.linear * multiverse.ParsecScaleX)
        scaleY = (self._viewScale.linear * multiverse.ParsecScaleY)

        worldWidgetWidth = self.width() / scaleX
        worldWidgetHeight = self.height() / scaleY
        worldWidgetLeft = self._viewCenter.x() - (worldWidgetWidth / 2)
        worldWidgetTop = self._viewCenter.y() - (worldWidgetHeight / 2)

        worldViewLeft = worldWidgetLeft + (viewRect.x() / scaleX)
        worldViewTop = worldWidgetTop + (viewRect.y() / scaleY)

        worldTileWidth = tileSize / scaleX
        worldTileHeight = tileSize / scaleY
        leftTile = math.floor((((clipRect.left() / scaleX) + worldViewLeft) / worldTileWidth))
        rightTile = math.floor((((clipRect.right() / scaleX) + worldViewLeft) / worldTileWidth))
        topTile = math.floor((((clipRect.top() / scaleY) + worldViewTop) / worldTileHeight))
        bottomTile = math.floor((((clipRect.bottom() / scaleY) + worldViewTop) / worldTileHeight))

        offsetX = (worldWidgetLeft - (leftTile * worldTileWidth)) * scaleX
        offsetY = (worldWidgetTop - (topTile * worldTileHeight)) * scaleY

        placeholders = []
        missing = []
        for x in range(leftTile, rightTile + 1):
            for y in range(topTile, bottomTile + 1):
                key = (
                    x,
                    y,
                    placeholderScale,
                    self._universe,
                    self._milieu,
                    self._renderer.style(),
                    int(self._renderer.options()))

                placeholderRenderRect = QtCore.QRectF(
                    ((x - leftTile) * tileSize) - offsetX,
                    ((y - topTile) * tileSize) - offsetY,
                    tileSize,
                    tileSize)
                placeholderClipRect = placeholderRenderRect.intersected(clipRect)
                if not placeholderClipRect.isValid():
                    continue

                # NOTE: Don't use _lookupTile as we don't want to create
                # this tile if it doesn't exist
                image = self._sharedTileCache.get(key)
                if image:
                    placeholders.append((image, placeholderRenderRect, placeholderClipRect))
                else:
                    if lookLower:
                        lowerPlaceholders = self._findPlaceholderTiles(
                            currentScale=placeholderScale,
                            tileRect=tileRect,
                            clipRect=placeholderClipRect,
                            viewRect=viewRect,
                            lookLower=lookLower)
                        if lowerPlaceholders:
                            placeholders.extend(lowerPlaceholders)
                            continue

                    missing.append(placeholderClipRect)

        if placeholders and missing:
            for placeholderClipRect in missing:
                placeholders.append((self._placeholderTile, tileRect, placeholderClipRect))

        return placeholders

    def _clearTileCache(self) -> None:
        self._sharedTileCache.clear()
        self._tileRenderQueue.clear()
        self._tileRenderTimer.stop()
        self.update() # Force redraw

    def _renderTile(
            self,
            tileX: int,
            tileY: int,
            tileScale: int, # Log scale rounded down
            image: typing.Optional[QtGui.QImage]
            ) -> QtGui.QImage:
        tileScale = gui.logScaleToLinearScale(tileScale)
        scaleX = (tileScale * multiverse.ParsecScaleX)
        scaleY = (tileScale * multiverse.ParsecScaleY)
        worldTileWidth = MapWidget._TileSize / scaleX
        worldTileHeight = MapWidget._TileSize / scaleY

        worldTileCenterX = ((tileX * MapWidget._TileSize) / scaleX) + (worldTileWidth / 2)
        worldTileCenterY = ((tileY * MapWidget._TileSize) / scaleY) + (worldTileHeight / 2)

        if not image:
            image = QtGui.QImage(
                MapWidget._TileSize,
                MapWidget._TileSize,
                QtGui.QImage.Format.Format_ARGB32)
        painter = QtGui.QPainter()
        painter.begin(image)
        try:
            self._mapGraphics.setPainter(painter=painter)
            self._renderer.setView(
                worldCenterX=worldTileCenterX,
                worldCenterY=worldTileCenterY,
                scale=tileScale,
                outputPixelWidth=MapWidget._TileSize,
                outputPixelHeight=MapWidget._TileSize)
            self._renderer.render()
        finally:
            self._mapGraphics.setPainter(painter=None)
            painter.end()

        return image

    def _handleRenderTileTimer(self) -> None:
        tileX, tileY, tileScale = self._tileRenderQueue.pop(0)
        image = None
        if self._sharedTileCache.isFull():
            # Reuse oldest cached tile
            _, image = self._sharedTileCache.pop()
        tileCacheKey = (
            tileX,
            tileY,
            tileScale,
            self._universe,
            self._milieu,
            # Use the settings for the renderer that is going to render the
            # tile to make sure the key is accurate
            self._renderer.style(),
            int(self._renderer.options()))
        self._sharedTileCache[tileCacheKey] = self._renderTile(
            tileX=tileX,
            tileY=tileY,
            tileScale=tileScale,
            image=image)
        if self._tileRenderQueue:
            self._tileRenderTimer.start()
        self.update()

    def _handleKeyboardMovementTimer(self) -> None:
        deltaX, deltaY = self._keyboardMovementTracker.direction()
        if deltaX or deltaY:
            # Normalize the delta and translate it to world space
            length = math.sqrt((deltaX * deltaX) + (deltaY * deltaY))
            if length:
                horzStep = MapWidget._KeyboardMoveDelta / (self._viewScale.linear * multiverse.ParsecScaleX)
                vertStep = MapWidget._KeyboardMoveDelta / (self._viewScale.linear * multiverse.ParsecScaleY)
                deltaX = (deltaX / length) * horzStep
                deltaY = (deltaY / length) * vertStep

            newViewCenter = QtCore.QPointF(
                self._viewCenter.x() + deltaX,
                self._viewCenter.y() + deltaY)
            self._updateView(center=newViewCenter)

    def _animateViewCenterGetter(self) -> QtCore.QPointF:
        return self._viewCenter

    def _animateViewCenterSetter(self, worldCenter: QtCore.QPointF) -> None:
        self._updateView(center=worldCenter)

    _viewCenterAnimationProp = QtCore.pyqtProperty(
        QtCore.QPointF,
        fget=_animateViewCenterGetter,
        fset=_animateViewCenterSetter)

    def _shouldAnimateViewTransition(
            self,
            newViewCenter: QtCore.QPointF,
            newViewScale: gui.MapScale
            ) -> bool:
        if self.isHidden() or not self._animated:
            return False

        deltaX = newViewCenter.x() - self._viewCenter.x()
        deltaY = newViewCenter.y() - self._viewCenter.y()
        xyDistance = math.sqrt(
            (deltaX * deltaX) + (deltaY * deltaY))
        # Traveller Map uses a value of 64 for the multiplier but I've
        # increased it to 256 so it will animate over a larger transition
        # as drawing tiles is "cheaper" with my implementation
        xyThreshold = multiverse.SectorHeight * 256 / self._viewScale.linear
        return xyDistance < xyThreshold

    def _startMoveAnimation(
            self,
            newViewCenter: QtCore.QPointF,
            newViewScale: gui.MapScale
            ) -> None:
        self._stopMoveAnimation()

        try:
            if len(MapWidget._sharedEasingCurves) >= 2:
                self._viewCenterAnimationEasing = MapWidget._sharedEasingCurves.pop()
                self._viewScaleAnimationEasing = MapWidget._sharedEasingCurves.pop()
            else:
                self._viewCenterAnimationEasing = self._viewScaleAnimationEasing = None

                # Fall back to immediate move
                self._updateView(
                    center=newViewCenter,
                    scale=newViewScale,
                    forceAtomicRedraw=True)
                return

            self._viewCenterAnimation = QtCore.QPropertyAnimation(
                self,
                b"_viewCenterAnimationProp")
            self._viewCenterAnimation.setDuration(MapWidget._MoveAnimationTimeMs)
            self._viewCenterAnimation.setEasingCurve(self._viewCenterAnimationEasing)
            self._viewCenterAnimation.setStartValue(self._viewCenter)
            self._viewCenterAnimation.setEndValue(newViewCenter)
            if newViewScale == self._viewScale:
                self._viewCenterAnimationEasing.setPeriods(
                    normAccelPeriod=0.25,
                    normDecelPeriod=0.25)
            elif newViewScale < self._viewScale:
                # Zooming out
                self._viewCenterAnimationEasing.setPeriods(
                    normAccelPeriod=0.75,
                    normDecelPeriod=0)
            else: # newViewLogScale > self._viewScale.log
                # Zooming in
                self._viewCenterAnimationEasing.setPeriods(
                    normAccelPeriod=0.05,
                    normDecelPeriod=0.75)

            self._viewScaleAnimation = QtCore.QPropertyAnimation(
                self,
                b"_viewScaleAnimationProp")
            self._viewScaleAnimation.setDuration(MapWidget._MoveAnimationTimeMs)
            self._viewScaleAnimation.setEasingCurve(self._viewScaleAnimationEasing)
            self._viewScaleAnimation.setStartValue(self._viewScale.log)
            self._viewScaleAnimation.setEndValue(newViewScale.log)
            self._viewScaleAnimationEasing.setPeriods(
                normAccelPeriod=0.25,
                normDecelPeriod=0.25)

            self._viewAnimationGroup = QtCore.QParallelAnimationGroup()
            self._viewAnimationGroup.addAnimation(self._viewCenterAnimation)
            self._viewAnimationGroup.addAnimation(self._viewScaleAnimation)
            self._viewAnimationGroup.finished.connect(self._handleMoveAnimationFinished)
            self._viewAnimationGroup.start()
        except:
            # If any error occurs during setting up the animation make sure
            # stop is called to make sure any assigned curves are returned to
            # the shared cache
            self._stopMoveAnimation()
            raise

    def _animateViewScaleGetter(self) -> QtCore.QPointF:
        return self._viewScale.log

    def _animateViewScaleSetter(self, logScale: float) -> None:
        newViewScale = gui.MapScale(log=logScale)
        self._updateView(scale=newViewScale)

    def _stopMoveAnimation(self):
        if self._viewAnimationGroup:
            self._viewAnimationGroup.stop()
            if self._viewCenterAnimation:
                self._viewAnimationGroup.removeAnimation(self._viewCenterAnimation)
            if self._viewScaleAnimation:
                self._viewAnimationGroup.removeAnimation(self._viewScaleAnimation)
            self._viewAnimationGroup.deleteLater()
            self._viewAnimationGroup = None

        if self._viewCenterAnimation:
            self._viewCenterAnimation.deleteLater()
            self._viewCenterAnimation = None

        if self._viewScaleAnimation:
            self._viewScaleAnimation.deleteLater()
            self._viewScaleAnimation = None

        if self._viewCenterAnimationEasing:
            MapWidget._sharedEasingCurves.append(self._viewCenterAnimationEasing)
            self._viewCenterAnimationEasing = None

        if self._viewScaleAnimationEasing:
            MapWidget._sharedEasingCurves.append(self._viewScaleAnimationEasing)
            self._viewScaleAnimationEasing = None

    def _handleMoveAnimationFinished(self):
        self._stopMoveAnimation()

    _viewScaleAnimationProp = QtCore.pyqtProperty(
        float,
        fget=_animateViewScaleGetter,
        fset=_animateViewScaleSetter)

    @staticmethod
    def _createPlaceholderTile() -> QtGui.QImage:
        image = QtGui.QImage(
            MapWidget._TileSize,
            MapWidget._TileSize,
            QtGui.QImage.Format.Format_ARGB32)
        rectsPerSize = math.ceil(MapWidget._TileSize / MapWidget._CheckerboardRectSize)

        painter = QtGui.QPainter()
        with gui.PainterDrawGuard(painter, image):
            painter.setBrush(QtGui.QColor(MapWidget._CheckerboardColourA))
            painter.drawRect(0, 0, MapWidget._TileSize, MapWidget._TileSize)

            painter.setBrush(QtGui.QColor(MapWidget._CheckerboardColourB))
            for x in range(rectsPerSize):
                for y in range(1 if x % 2 else 0, rectsPerSize, 2):
                    painter.drawRect(
                        x * MapWidget._CheckerboardRectSize,
                        y * MapWidget._CheckerboardRectSize,
                        MapWidget._CheckerboardRectSize,
                        MapWidget._CheckerboardRectSize)

        return image
