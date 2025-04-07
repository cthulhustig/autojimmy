import app
import common
import enum
import gui
import logic
import logging
import cartographer
import math
import traveller
import travellermap
import typing
import uuid
from PyQt5 import QtWidgets, QtCore, QtGui

# TODO: I think a lot of the places I've referred to as absolute space
# is actually map space, or at least my equivalent of it (i.e. without the
# inverted y axis like in Traveller Map). I think anything the problem
# might be around things that are using ParsecScaleX/ParsecScaleY.
# Update: I think the coordinate system naming are a complete mess
# - I think the render is working in its own coordinate system. I think
#   traveller map might refer to it as world coordinates but this term
#   seems a littler overloaded as the traveller map coordinate system
#   documentation seems to use the term world space for the integer pair
#   coordinate system that defines a hex relative to reference (i.e.
#   what I've historically referred to as absolute coordinates)
# - The coordinate system used by the renderer is in parsecs with a hex
#   being 1 parsec high and slightly over 1 parsec wide when rendered.
# - I have what I call relative space but in traveller map it refers to
#   it sector hex. The traveller map terminology is a little ambiguous
#   as there is also the string based sector hex format but that is
#   effectively equivalent just with the sector coordinate replaced with
#   the name
# - I'm overloading the term absolute space. I'm using it as the term
#   for what the renderer is working in and using it for the integer
#   pair that represents a hex elsewhere in the code. I think this is
#   basically the same overloading as traveller map where it uses
#   world coordinates
# TODO: Animated move to new location
# TODO: Fix colour vs color
# TODO: Custom sector import
# - Until I drop the web map widget I need to have it generate the map images
# in case the user changes the rendering type
# - Update welcome message to cover the different rendering types
#   - This would probably be the place to mention that I intend to remove web rendering
#   - Ideally I would force the welcome message to be displayed again if the user has hidden it (new _V2 key????)
# - Add something to the create dialog that makes it clear the options selected there only apply if using the proxy
#   - I still need to have them enabled when local rendering is selected so the user can change them if they want
# TODO: When not using M1105 Traveller Map shows worlds from M1105 as asterisks
# TODO: The current split between the traveller/travellermap directories probably makes less sense now
# - I suspect I want to move traveller bellow travellermap and move a some stuff out of traveller
#   map and into either traveller or cartographer
# - This probably doesn't need done for the first release

class _MapOverlay(object):
    def __init__(self):
        super().__init__()
        self._handle = str(uuid.uuid4())

    def handle(self) -> str:
        return self._handle

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
            currentScale: travellermap.Scale
            ) -> bool: # True if anything was draw
        raise RuntimeError(f'{type(self)} is derived from _MapOverlay so must implement draw')

class _JumpRouteOverlay(_MapOverlay):
    _JumpRouteColour = '#7F048104'
    _PitStopColour = '#7F8080FF'
    _PitStopRadius =  0.4 # Default to slightly larger than the size of the highlights Traveller Map puts on jump worlds

    def __init__(self) -> None:
        super().__init__()
        self._jumpRoutePath = None
        self._pitStopPoints = None

        self._jumpRoutePen = QtGui.QPen(
            QtGui.QColor(_JumpRouteOverlay._JumpRouteColour),
            1, # Width will be set when rendering as it's dependant on scale
            QtCore.Qt.PenStyle.SolidLine,
            QtCore.Qt.PenCapStyle.FlatCap)
        self._jumpNodePen = QtGui.QPen(
            QtGui.QColor(_JumpRouteOverlay._JumpRouteColour),
            1, # Width will be set when rendering as it's dependant on scale
            QtCore.Qt.PenStyle.SolidLine,
            QtCore.Qt.PenCapStyle.RoundCap)
        self._pitStopPen = QtGui.QPen(
            QtGui.QColor(_JumpRouteOverlay._PitStopColour),
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
        for hex, _ in jumpRoute:
            centerX, centerY = hex.absoluteCenter()
            self._jumpRoutePath.append(QtCore.QPointF(
                centerX * travellermap.ParsecScaleX,
                centerY * travellermap.ParsecScaleY))

        self._pitStopPoints = None
        if refuellingPlan:
            self._pitStopPoints = QtGui.QPolygonF()
            for pitStop in refuellingPlan:
                centerX, centerY = pitStop.hex().absoluteCenter()
                self._pitStopPoints.append(QtCore.QPointF(
                    centerX * travellermap.ParsecScaleX,
                    centerY * travellermap.ParsecScaleY))

    def draw(
            self,
            painter: QtGui.QPainter,
            currentScale: travellermap.Scale
            ) -> None:
        if not self._jumpRoutePath:
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
    # This alpha value matches the hard coded (global) alpha used by Traveller Map
    # when drawing it renders overlays (drawOverlay in map.js)
    # TODO: When I get eventually get rid of the web map widget I should drop this
    # constant and instead have alpha specified by the colour passed in
    _HighlightAlpha = 0.5

    _HexPolygon = QtGui.QPolygonF([
        # Upper left
        QtCore.QPointF(
            (-0.5 + travellermap.HexWidthOffset) * travellermap.ParsecScaleX,
            -0.5 * travellermap.ParsecScaleY),
        # Upper right
        QtCore.QPointF(
            (+0.5 - travellermap.HexWidthOffset) * travellermap.ParsecScaleX,
            -0.5 * travellermap.ParsecScaleY),
        # Center right
        QtCore.QPointF(
            (+0.5 + travellermap.HexWidthOffset) * travellermap.ParsecScaleX,
            0 * travellermap.ParsecScaleY) ,
        # Lower right
        QtCore.QPointF(
            (+0.5 - travellermap.HexWidthOffset) * travellermap.ParsecScaleX,
            +0.5 * travellermap.ParsecScaleY),
        # Lower Left
        QtCore.QPointF(
            (-0.5 + travellermap.HexWidthOffset) * travellermap.ParsecScaleX,
            +0.5 * travellermap.ParsecScaleY),
        # Center left
        QtCore.QPointF(
            (-0.5 - travellermap.HexWidthOffset) * travellermap.ParsecScaleX,
            0 * travellermap.ParsecScaleY),
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
                str, # Colour
                # Integer radius in 100ths of a parsec for Circle primitive type
                # or 0 for Hex
                int],
            typing.Tuple[
                QtGui.QPolygonF,
                # QPen for Circle primitive type or QBrush for hex
                typing.Union[QtGui.QPen, QtGui.QBrush]]
            ] = {}

        self._hexMap: typing.Dict[
            travellermap.HexPosition,
            typing.Set[typing.Tuple[
                gui.MapPrimitiveType,
                str, # Colour
                # Integer radius in 100ths of a parsec for Circle primitive type
                # or 0 for Hex
                int]],
            ] = {}

    def addHex(
            self,
            hex: travellermap.HexPosition,
            type: gui.MapPrimitiveType,
            colour: str,
            radius: float = 0.0 # Only valid if primitive type is Circle
            ) -> None:
        radius = int(round(radius * 100))
        styleKey = (type, colour, radius)

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

        centerX, centerY = hex.absoluteCenter()
        polygon = renderData[0]
        polygon.append(QtCore.QPointF(
            centerX * travellermap.ParsecScaleX,
            centerY * travellermap.ParsecScaleY))

        if not hexStyleKeys:
            hexStyleKeys = set()
            self._hexMap[hex] = hexStyleKeys
        hexStyleKeys.add(styleKey)

    def addHexes(
            self,
            hexes: typing.Iterable[travellermap.HexPosition],
            type: gui.MapPrimitiveType,
            colour: typing.Optional[str],
            colourMap: typing.Optional[typing.Mapping[travellermap.HexPosition, str]] = None,
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
            styleKey = (type, colour, radius)
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
                styleKey = (type, hexColour, radius)
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

            centerX, centerY = hex.absoluteCenter()
            polygon = renderData[0]
            polygon.append(QtCore.QPointF(
                centerX * travellermap.ParsecScaleX,
                centerY * travellermap.ParsecScaleY))

            if not hexStyleKeys:
                hexStyleKeys = set()
                self._hexMap[hex] = hexStyleKeys
            hexStyleKeys.add(styleKey)

    def removeHex(
            self,
            hex: travellermap.HexPosition
            ) -> None:
        hexStyleKeys = self._hexMap.get(hex)
        if not hexStyleKeys:
            return # The hex has no highlight to remove

        centerX, centerY = hex.absoluteCenter()
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
            currentScale: travellermap.Scale
            ) -> None:
        if not self._styleMap:
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
            colour: str,
            radius: float
            ) -> typing.Union[QtGui.QPen, QtGui.QBrush]:
        colour = QtGui.QColor(cartographer.makeAlphaColor(
            alpha=_HexHighlightOverlay._HighlightAlpha,
            color=colour,
            isNormalised=True))

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
    # This alpha value matches the hard coded (global) alpha used by Traveller Map
    # when drawing it renders overlays (drawOverlay in map.js)
    # TODO: When I get eventually get rid of the web map widget I should drop this
    # constant and instead have alpha specified by the colour passed in
    _HighlightAlpha = 0.5

    def __init__(
            self,
            hexes: typing.Iterable[travellermap.HexPosition],
            lineColour: typing.Optional[str] = None,
            lineWidth: typing.Optional[int] = None, # In pixels
            fillColour: typing.Optional[str] = None,
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
                # NOTE: Negate the Y as calculateCompleteHexOutlines returns
                # Traveller Map map space coordinates whereas this overlay
                # will render in my isotropic space
                # TODO: When I finally get rid of the Traveller Map web widget I
                # should update these functions to work in my coordinate space
                polygon.append(QtCore.QPointF(x, -y))
            self._polygons.append(polygon)

        self._pen = self._brush = None
        if lineColour:
            self._pen = QtGui.QPen(
                QtGui.QColor(cartographer.makeAlphaColor(
                    alpha=_HexBorderOverlay._HighlightAlpha,
                    color=lineColour,
                    isNormalised=True)),
                0) # Line width set at draw time as it's dependent on scale
            self._lineWidth = lineWidth
        if fillColour:
            self._brush = QtGui.QBrush(
                QtGui.QColor(cartographer.makeAlphaColor(
                    alpha=_HexBorderOverlay._HighlightAlpha,
                    color=fillColour,
                    isNormalised=True)))

    def draw(
            self,
            painter: QtGui.QPainter,
            currentScale: travellermap.Scale
            ) -> None:
        painter.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_Source)

        if self._pen:
            self._pen.setWidthF(self._lineWidth / currentScale.linear)
        painter.setPen(self._pen if self._pen else QtCore.Qt.PenStyle.NoPen)

        painter.setBrush(self._brush if self._brush else QtCore.Qt.BrushStyle.NoBrush)

        for polygon in self._polygons:
            painter.drawPolygon(polygon)

        return True # Something was drawn

class _EmpressWaveOverlay(_MapOverlay):
    _WaveColour = '#4CFFCC00'
    _WaveVelocity = math.pi / 3.26 # Velocity of effect is light speed (so 1 ly/y)

    def __init__(self) -> None:
        super().__init__()
        self._pen = QtGui.QPen(
            QtGui.QColor(_EmpressWaveOverlay._WaveColour),
            0) # Width will be set at render time

    # This code is based on the Traveller Map drawWave code (map.js)
    def draw(
            self,
            painter: QtGui.QPainter,
            currentScale: travellermap.Scale
            ) -> None:
        if not app.Config.instance().mapOption(travellermap.Option.EmpressWaveOverlay):
            return False

        year = travellermap.milieuToYear(milieu=app.Config.instance().milieu())

        w = 1 #pc

        # Per MWM: center is 10000pc coreward
        x, y = travellermap.mapSpaceToAbsoluteSpace((0, 10000))
        x *= travellermap.ParsecScaleX
        y *= travellermap.ParsecScaleY

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
    _ZoneColour = '#4CFFCC00'

    def __init__(self) -> None:
        super().__init__()
        self._pen = QtGui.QPen(
            QtGui.QColor(_QrekrshaZoneOverlay._ZoneColour),
            0) # Width will be set at render time

    # This code is based on the Traveller Map drawQZ code (map.js)
    def draw(
            self,
            painter: QtGui.QPainter,
            currentScale: travellermap.Scale
            ) -> None:
        if not app.Config.instance().mapOption(travellermap.Option.QrekrshaZoneOverlay):
            return False

        x, y = travellermap.mapSpaceToAbsoluteSpace((-179.4, 131))
        x *= travellermap.ParsecScaleX
        y *= travellermap.ParsecScaleY

        radius = 30 * travellermap.ParsecScaleX

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
    _SupernovaColour = '#26FFCC00'
    _SupernovaCenter = travellermap.HexPosition(55, -59) # Antares
    _SupernovaVelocity = 1 / 3.26 # Velocity of effect is light speed (so 1 ly/y)

    def __init__(self) -> None:
        super().__init__()
        self._brush = QtGui.QBrush(
            QtGui.QColor(_AntaresSupernovaOverlay._SupernovaColour))

    # This code is based on the Traveller Map drawAS code (map.js)
    def draw(
            self,
            painter: QtGui.QPainter,
            currentScale: travellermap.Scale
            ) -> None:
        if not app.Config.instance().mapOption(travellermap.Option.AntaresSupernovaOverlay):
            return False

        year = travellermap.milieuToYear(milieu=app.Config.instance().milieu())
        yearRadius = (year - 1270) * _AntaresSupernovaOverlay._SupernovaVelocity
        if yearRadius < 0:
            return False

        # Center is Antares (ANT 2421)
        x, y = _AntaresSupernovaOverlay._SupernovaCenter.absoluteCenter()
        x *= travellermap.ParsecScaleX
        y *= travellermap.ParsecScaleY

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
    _SmallMainColour = travellermap.HtmlColors.Pink
    _MediumMainColour = '#FFCC00'
    _LargeMainColour = travellermap.HtmlColors.Cyan
    _MainAlpha = 0.25
    _PointSize = 1.15

    def __init__(self) -> None:
        super().__init__()
        self._points = None
        self._pen = None

    def setMain(self, main: typing.Optional[traveller.Main]) -> None:
        if not main:
            self._points = self._pen = None
            return

        self._points = QtGui.QPolygonF()
        for world in main:
            centerX, centerY = world.hex().absoluteCenter()
            self._points.append(QtCore.QPointF(
                centerX * travellermap.ParsecScaleX,
                centerY * travellermap.ParsecScaleY))

        if len(main) <= 10:
            colour = _MainsOverlay._SmallMainColour
        elif len(main) < 50:
            colour = _MainsOverlay._MediumMainColour
        else:
            colour = _MainsOverlay._LargeMainColour

        self._pen = QtGui.QPen(
            QtGui.QColor(cartographer.makeAlphaColor(
                color=colour,
                alpha=_MainsOverlay._MainAlpha,
                isNormalised=True)),
            _MainsOverlay._PointSize,
            QtCore.Qt.PenStyle.SolidLine,
            QtCore.Qt.PenCapStyle.RoundCap)

    # This code is based on the Traveller Map drawQZ code (map.js)
    def draw(
            self,
            painter: QtGui.QPainter,
            currentScale: travellermap.Scale
            ) -> None:
        if not self._points or not self._pen or \
            not app.Config.instance().mapOption(travellermap.Option.MainsOverlay):
            return False

        painter.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_Source)
        painter.setPen(self._pen)
        painter.drawPoints(self._points)

        return True # Something was drawn

class LocalMapWidget(QtWidgets.QWidget):
    leftClicked = QtCore.pyqtSignal([travellermap.HexPosition])
    rightClicked = QtCore.pyqtSignal([travellermap.HexPosition])

    _MinScale = -5
    _MaxScale = 10
    _DefaultCenterX = 0
    _DefaultCenterY = 0
    _DefaultScale = 64
    _DefaultScale = travellermap.logScaleToLinearScale(7)
    #_DefaultCenterX, _DefaultCenterY = (13.971588572221023, -28.221357863973523)
    #_DefaultCenterX, _DefaultCenterY = (-95.914 / travellermap.ParsecScaleX, 70.5 / -travellermap.ParsecScaleY)
    #_DefaultCenterX, _DefaultCenterY = (-110.50311757412467, -70.5033270610736)
    #_DefaultCenterX, _DefaultCenterY = travellermap.mapSpaceToAbsoluteSpace((-95.914, 70.5))

    _KeyZoomDelta = 0.5
    _WheelZoomDelta = 0.15

    _LookaheadBorderTiles = 2
    _TileSize = 512 # Pixels
    _TileCacheSize = 250 # Number of tiles
    _TileTimerMsecs = 1
    #_TileTimerMsecs = 1000

    _CheckerboardColourA ='#000000'
    _CheckerboardColourB ='#404040'
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

    _StateVersion = 'LocalMapWidget_v1'

    _sharedTileCache = common.LRUCache[
        typing.Tuple[
            int, # Tile X
            int, # Tile Y
            int,
            travellermap.Style,
            int], # MapOptions as an int
        QtGui.QImage](capacity=_TileCacheSize)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        scene = QtWidgets.QGraphicsScene()
        scene.setSceneRect(0, 0, self.width(), self.height())

        self._absoluteCenterPos = QtCore.QPointF(
            LocalMapWidget._DefaultCenterX,
            LocalMapWidget._DefaultCenterY)
        self._viewScale = travellermap.Scale(value=LocalMapWidget._DefaultScale, linear=True)
        self._imageSpaceToWorldSpace = None
        self._imageSpaceToOverlaySpace = None

        self._graphics = gui.MapGraphics()
        self._imageCache = cartographer.ImageCache(
            graphics=self._graphics)
        self._vectorCache = cartographer.VectorObjectCache(
            graphics=self._graphics)
        self._labelCache = cartographer.LabelCache()
        self._styleCache = cartographer.StyleCache()
        self._renderer = self._createRenderer()

        self._worldDragAnchor: typing.Optional[QtCore.QPointF] = None
        self._pixelDragStart: typing.Optional[QtCore.QPoint] = None

        # Off screen buffer used when not using tile rendering to prevent
        # Windows font scaling messing up the size of rendered text on a
        # 4K+ screen
        self._isWindows = common.isWindows()
        self._offscreenRenderImage: typing.Optional[QtGui.QImage] = None

        self._tileTimer = QtCore.QTimer()
        self._tileTimer.setInterval(LocalMapWidget._TileTimerMsecs)
        self._tileTimer.setSingleShot(True)
        self._tileTimer.timeout.connect(self._handleTileTimer)
        self._tileQueue: typing.List[typing.Tuple[
            int, # Tile X
            int, # Tile Y
            int # Tile Scale (linear)
            ]] = []
        self._forceAtomicRedraw = False

        self._placeholderTile = LocalMapWidget._createPlaceholderTile()

        self._directionTextFont = QtGui.QFont(
            LocalMapWidget._DirectionTextFontFamily,
            LocalMapWidget._DirectionTextFontSize)
        self._directionTextFont.setBold(True)
        self._directionTextPen = QtGui.QPen(
            QtGui.QColor(travellermap.HtmlColors.TravellerRed),
            0)

        self._scaleFont = QtGui.QFont(
            LocalMapWidget._ScaleTextFontFamily,
            LocalMapWidget._ScaleTextFontSize)
        self._scalePen = QtGui.QPen(
            QtGui.QColor(travellermap.HtmlColors.Black), # Colour will be updated when drawn
            LocalMapWidget._ScaleLineWidth,
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

        self._empressWaveOverlay = _EmpressWaveOverlay()
        self._overlayMap[self._empressWaveOverlay.handle()] = self._empressWaveOverlay

        self._qrekrshaZoneOverlay = _QrekrshaZoneOverlay()
        self._overlayMap[self._qrekrshaZoneOverlay.handle()] = self._qrekrshaZoneOverlay

        self._antaresSupernovaOverlay = _AntaresSupernovaOverlay()
        self._overlayMap[self._antaresSupernovaOverlay.handle()] = self._antaresSupernovaOverlay

        self._mainsOverlay = _MainsOverlay()
        self._overlayMap[self._mainsOverlay.handle()] = self._mainsOverlay

        self._toolTipCallback = None

        self.installEventFilter(self)

        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)

        self._handleViewUpdate()

    # TODO: When I finally remove WebMapWidget I should rework how
    # reloading work as it doesn't make conceptual sense whe there
    # is nothing to "load"
    def reload(self) -> None:
        self._renderer = self._createRenderer()
        self._clearTileCache()
        self._handleViewUpdate()

    def centerOnHex(
            self,
            hex: travellermap.HexPosition,
            linearScale: typing.Optional[float] = 64 # None keeps current scale
            ) -> None:
        center = hex.absoluteCenter()
        self._absoluteCenterPos.setX(center[0])
        self._absoluteCenterPos.setY(center[1])
        self._viewScale.linear = linearScale
        self._handleViewUpdate(forceAtomicRedraw=True)

    def centerOnHexes(
            self,
            hexes: typing.Collection[travellermap.HexPosition]
            ) -> None:
        if not hexes:
            return

        left = right = top = bottom = None
        for hex in hexes:
            hexLeft, hexTop, hexWidth, hexHeight = hex.absoluteBounds()
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
        centerX = left + (width / 2)
        centerY = top + (height / 2)
        scale = common.clamp(
            value=min(
                travellermap.linearScaleToLogScale(self.width() / width),
                travellermap.linearScaleToLogScale(self.height() / height)),
            minValue=LocalMapWidget._MinScale,
            maxValue=LocalMapWidget._MaxScale)

        self._absoluteCenterPos.setX(centerX)
        self._absoluteCenterPos.setY(centerY)
        self._viewScale.log = scale
        self._handleViewUpdate(forceAtomicRedraw=True)

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

    def centerOnJumpRoute(self) -> None:
        if not self._jumpRoute:
            return
        self.centerOnHexes(
            hexes=[nodeHex for nodeHex, _ in self._jumpRoute])

    def highlightHex(
            self,
            hex: travellermap.HexPosition,
            radius: float = 0.5,
            colour: str = '#8080FF'
            ) -> None:
        self._hexHighlightOverlay.addHex(
            hex=hex,
            type=gui.MapPrimitiveType.Circle,
            colour=colour,
            radius=radius)
        self.update() # Trigger redraw

    def highlightHexes(
            self,
            hexes: typing.Iterable[travellermap.HexPosition],
            radius: float = 0.5,
            colour: str = '#8080FF'
            ) -> None:
        self._hexHighlightOverlay.addHexes(
            hexes=hexes,
            type=gui.MapPrimitiveType.Circle,
            colour=colour,
            radius=radius)
        self.update() # Trigger redraw

    def clearHexHighlight(
            self,
            hex: travellermap.HexPosition
            ) -> None:
        self._hexHighlightOverlay.removeHex(hex)
        self.update() # Trigger redraw

    def clearHexHighlights(self) -> None:
        self._hexHighlightOverlay.clear()
        self.update() # Trigger redraw

    # Create an overlay with a primitive at each hex
    def createHexOverlay(
            self,
            hexes: typing.Iterable[travellermap.HexPosition],
            primitive: gui.MapPrimitiveType,
            fillColour: typing.Optional[str] = None,
            fillMap: typing.Optional[typing.Mapping[
                travellermap.HexPosition,
                str # Colour string
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
            hexes: typing.Iterable[travellermap.HexPosition],
            lineColour: typing.Optional[str] = None,
            lineWidth: typing.Optional[int] = None, # In pixels
            fillColour: typing.Optional[str] = None,
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

    # TODO: When I finally remove WebMapWidget I should rework how tooltips
    # are handled to make them more Qt like
    def setToolTipCallback(
            self,
            callback: typing.Optional[typing.Callable[[typing.Optional[travellermap.HexPosition]], typing.Optional[str]]],
            ) -> None:
        self._toolTipCallback = callback

    def createSnapshot(self) -> QtGui.QPixmap:
        image = QtGui.QPixmap(self.size())
        self._drawView(
            paintDevice=image,
            forceAtomic=True)
        return image

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(LocalMapWidget._StateVersion)
        stream.writeFloat(self._absoluteCenterPos.x())
        stream.writeFloat(self._absoluteCenterPos.y())
        stream.writeFloat(self._viewScale.log)
        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != LocalMapWidget._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore LocalMapWidget state (Incorrect version)')
            return False

        self._absoluteCenterPos.setX(stream.readFloat())
        self._absoluteCenterPos.setY(stream.readFloat())
        self._viewScale.log = stream.readFloat()
        self._handleViewUpdate()
        return True

    def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent):
        if obj is self and event.type() == QtCore.QEvent.Type.ToolTip:
            assert(isinstance(event, QtGui.QHelpEvent))
            hex = self._pixelSpaceToHex(event.pos())
            text = self._toolTipCallback(hex) if self._toolTipCallback else ''
            self.setToolTip(text)
        return super().eventFilter(obj, event)

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
        super().mousePressEvent(event)

        if self.isEnabled() and event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._pixelDragStart = event.pos()
            self._worldDragAnchor = self._pixelSpaceToWorldSpace(self._pixelDragStart)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        super().mouseMoveEvent(event)
        if self.isEnabled() and self._renderer and self._worldDragAnchor:
            worldCurrentPos = self._pixelSpaceToWorldSpace(event.pos())
            worldDeltaX = worldCurrentPos.x() - self._worldDragAnchor.x()
            worldDeltaY = worldCurrentPos.y() - self._worldDragAnchor.y()

            self._absoluteCenterPos.setX(
                self._absoluteCenterPos.x() - worldDeltaX)
            self._absoluteCenterPos.setY(
                self._absoluteCenterPos.y() - worldDeltaY)
            self._handleViewUpdate()

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        super().mouseReleaseEvent(event)

        if not self.isEnabled():
            return

        leftRelease = event.button() == QtCore.Qt.MouseButton.LeftButton
        rightRelease = event.button() == QtCore.Qt.MouseButton.RightButton
        if not (leftRelease or rightRelease):
            return

        pixelReleasePos = QtCore.QPointF(event.x(), event.y())

        if leftRelease and self._pixelDragStart:
            clickRect = QtCore.QRectF(
                self._pixelDragStart.x() - self._LeftClickMoveThreshold,
                self._pixelDragStart.y() - self._LeftClickMoveThreshold,
                self._LeftClickMoveThreshold * 2,
                self._LeftClickMoveThreshold * 2)

            self._worldDragAnchor = self._pixelDragStart = None

            if not clickRect.contains(pixelReleasePos):
                return # A drag was performed so it doesn't count as a click

        hex = self._pixelSpaceToHex(pixelReleasePos)
        if leftRelease:
            self._handleLeftClickEvent(hex)
        else:
            self._handleRightClickEvent(hex)

    def focusOutEvent(self, event: QtGui.QFocusEvent) -> None:
        super().focusOutEvent(event)
        self._worldDragAnchor = self._pixelDragStart = None

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        self._handleViewUpdate()

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        super().keyPressEvent(event)

        if self._renderer:
            dx = dy = None
            if event.key() == QtCore.Qt.Key.Key_Left:
                width = self.width() / (self._viewScale.linear * travellermap.ParsecScaleX)
                dx = -width / 10
            elif event.key() == QtCore.Qt.Key.Key_Right:
                width = self.width() / (self._viewScale.linear * travellermap.ParsecScaleX)
                dx = width / 10
            elif event.key() == QtCore.Qt.Key.Key_Up:
                height = self.height() / (self._viewScale.linear * travellermap.ParsecScaleY)
                dy = -height / 10
            elif event.key() == QtCore.Qt.Key.Key_Down:
                height = self.height() / (self._viewScale.linear * travellermap.ParsecScaleY)
                dy = height / 10

            if dx != None or dy != None:
                if dx != None:
                    self._absoluteCenterPos.setX(self._absoluteCenterPos.x() + dx)
                if dy != None:
                    self._absoluteCenterPos.setY(self._absoluteCenterPos.y() + dy)
                self._handleViewUpdate()
                return

            if event.key() == QtCore.Qt.Key.Key_Z:
                self._zoomView(
                    step=LocalMapWidget._KeyZoomDelta if not gui.isShiftKeyDown() else -LocalMapWidget._KeyZoomDelta)
            elif event.key() == QtCore.Qt.Key.Key_Plus or event.key() == QtCore.Qt.Key.Key_Equal:
                self._zoomView(step=LocalMapWidget._KeyZoomDelta)
            elif event.key() == QtCore.Qt.Key.Key_Minus:
                self._zoomView(step=-LocalMapWidget._KeyZoomDelta)

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        super().wheelEvent(event)

        if self.isEnabled():
            self._zoomView(
                step=LocalMapWidget._WheelZoomDelta if event.angleDelta().y() > 0 else -LocalMapWidget._WheelZoomDelta,
                cursor=event.pos())

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        if not self._graphics or not self._renderer:
            return super().paintEvent(event)

        renderType = app.Config.instance().mapRenderingType()
        if renderType is app.MapRenderingType.Tiled and self._forceAtomicRedraw:
            # Render any missing tiles now rather than in the background. Hybrid
            # rendering is used rather than Full as we want the same digital
            # zooming between log scales that you would get with Background
            # rendering
            renderType = app.MapRenderingType.Hybrid

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
            renderType=renderType)

        if renderType is app.MapRenderingType.Tiled:
            if not self._tileQueue and LocalMapWidget._LookaheadBorderTiles:
                # If there are no tiles needing loaded, pre-load tiles just
                # outside the current view area.
                self._loadLookaheadTiles()

            # Start the timer to trigger loading of missing tiles. It's
            # important to re-check the tile queue as it may have had
            # lookahead tiles added
            if self._tileQueue:
                self._tileTimer.start()

        if self._offscreenRenderImage is not None:
            painter = QtGui.QPainter()
            with gui.PainterDrawGuard(painter, self):
                renderRect = QtCore.QRect(0, 0, self.width(), self.height())
                painter.drawImage(renderRect, self._offscreenRenderImage)

        self._forceAtomicRedraw = False

    def _drawView(
            self,
            paintDevice: QtGui.QPaintDevice,
            renderType: app.MapRenderingType
            ) -> None:
        painter = QtGui.QPainter()
        with gui.PainterDrawGuard(painter, paintDevice):
            painter.setBrush(QtCore.Qt.GlobalColor.black)
            painter.drawRect(0, 0, self.width(), self.height())

            self._drawMap(painter, renderType)
            self._drawOverlays(painter)
            self._drawScale(painter)
            self._drawDirections(painter)

    def _drawMap(
            self,
            painter: QtGui.QPainter,
            renderType: app.MapRenderingType
            ) -> None:
        if renderType is app.MapRenderingType.Tiled or \
            renderType is app.MapRenderingType.Hybrid:
            tiles = self._currentDrawTiles(
                createMissing=renderType is not app.MapRenderingType.Tiled)

            # This is disabled as I think it actually makes scaled tiles
            # look worse (a bit to blurry)
            #painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform, True)

            for image, renderRect, clipRect in tiles:
                painter.save()
                try:
                    if clipRect:
                        clipPath = painter.clipPath()
                        clipPath.setFillRule(QtCore.Qt.FillRule.WindingFill)
                        clipPath.addRect(clipRect)
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
                finally:
                    painter.restore()
        else:
            self._graphics.setPainter(painter=painter)
            try:
                self._renderer.setView(
                    absoluteCenterX=self._absoluteCenterPos.x(),
                    absoluteCenterY=self._absoluteCenterPos.y(),
                    scale=self._viewScale.linear,
                    outputPixelX=self.width(),
                    outputPixelY=self.height())
                self._renderer.render()
            finally:
                self._graphics.setPainter(painter=None)

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

        scaleRight = self.width() - LocalMapWidget._ScaleLineIndent
        scaleLeft = scaleRight - int(distance)
        scaleY = self.height() - LocalMapWidget._ScaleLineIndent

        fontMetrics = QtGui.QFontMetricsF(self._scaleFont)
        labelRect = fontMetrics.tightBoundingRect(label)

        self._scalePen.setColor(QtGui.QColor(
            travellermap.HtmlColors.White
            if travellermap.isDarkStyle(self._renderer.style()) else
            travellermap.HtmlColors.Black))

        with gui.PainterStateGuard(painter):
            painter.setPen(self._scalePen)
            painter.setFont(self._scaleFont)
            painter.drawText(
                QtCore.QPointF(
                    scaleLeft + ((distance / 2) - (labelRect.width() / 2)),
                    scaleY - LocalMapWidget._ScaleLineIndent),
                label)

            painter.drawLine(
                QtCore.QPointF(scaleLeft - (LocalMapWidget._ScaleLineWidth / 2), scaleY),
                QtCore.QPointF(scaleRight + (LocalMapWidget._ScaleLineWidth / 2), scaleY))
            painter.drawLine(
                QtCore.QPointF(scaleLeft, scaleY),
                QtCore.QPointF(scaleLeft, scaleY - LocalMapWidget._ScaleLineTickHeight))
            painter.drawLine(
                QtCore.QPointF(scaleRight, scaleY),
                QtCore.QPointF(scaleRight, scaleY - LocalMapWidget._ScaleLineTickHeight))

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
        if not self._directionTextFont or \
            not app.Config.instance().mapOption(travellermap.Option.GalacticDirections):
            return

        viewWidth = self.width()
        viewHeight = self.height()

        fontMetrics = QtGui.QFontMetricsF(self._directionTextFont)

        with gui.PainterStateGuard(painter):
            painter.setFont(self._directionTextFont)
            painter.setPen(self._directionTextPen)
            for text, angle, alignX, alignY in LocalMapWidget._DirectionLabels:
                textRect = fontMetrics.boundingRect(text)
                textRect.moveTo(
                    -textRect.width() / 2,
                    -textRect.height() / 2)
                textHeight = textRect.height()
                with gui.PainterStateGuard(painter):
                    if alignX:
                        offsetX = (textHeight / 2) + LocalMapWidget._DirectionTextIndent
                        if alignX > 0:
                            offsetX = viewWidth - offsetX
                    else:
                        offsetX = (viewWidth / 2)

                    if alignY:
                        offsetY = (textHeight / 2) + LocalMapWidget._DirectionTextIndent
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
            hex: typing.Optional[travellermap.HexPosition]
            ) -> None:
        if hex and self.isEnabled():
            if app.Config.instance().mapOption(travellermap.Option.MainsOverlay):
                main = traveller.WorldManager.instance().positionToMain(hex=hex)
                self._mainsOverlay.setMain(main)
                self.update() # Trigger redraw

            self.leftClicked.emit(hex)

    def _handleRightClickEvent(
            self,
            hex: typing.Optional[travellermap.HexPosition]
            ) -> None:
        if hex and self.isEnabled():
            self.rightClicked.emit(hex)

    def _pixelSpaceToWorldSpace(
            self,
            pixelPos: typing.Union[QtCore.QPointF, QtCore.QPoint]
            ) -> QtCore.QPointF:
        scaleX = (self._viewScale.linear * travellermap.ParsecScaleX)
        scaleY = (self._viewScale.linear * travellermap.ParsecScaleY)

        width = self.width() / scaleX
        height = self.height() / scaleY

        offsetX = pixelPos.x() / scaleX
        offsetY = pixelPos.y() / scaleY

        return QtCore.QPointF(
            (self._absoluteCenterPos.x() - (width / 2)) + offsetX,
            (self._absoluteCenterPos.y() - (height / 2)) + offsetY)

    def _worldSpaceToPixelSpace(
            self,
            worldPos: typing.Union[QtCore.QPointF, QtCore.QPoint]
            ) -> QtCore.QPointF:
        scaleX = (self._viewScale.linear * travellermap.ParsecScaleX)
        scaleY = (self._viewScale.linear * travellermap.ParsecScaleY)

        width = self.width() / scaleX
        height = self.height() / scaleY

        offsetX = worldPos.x() - (self._absoluteCenterPos.x() - (width / 2))
        offsetY = worldPos.y() - (self._absoluteCenterPos.y() - (height / 2))

        return QtCore.QPointF(
            offsetX * scaleX,
            offsetY * scaleY)

    def _pixelSpaceToHex(
            self,
            pixelPos: typing.Union[QtCore.QPointF, QtCore.QPoint]
            ) -> travellermap.HexPosition:
        return self._worldSpaceToHex(self._pixelSpaceToWorldSpace(pixelPos))

    def _worldSpaceToHex(
            self,
            worldPos: typing.Union[QtCore.QPointF, QtCore.QPoint]
            ) -> travellermap.HexPosition:
        worldClampedX = int(round(worldPos.x() + 0.5))
        worldClampedY = int(round(worldPos.y() + (0.5 if (worldClampedX % 2 == 0) else 0)))

        return travellermap.HexPosition(
            absoluteX=worldClampedX,
            absoluteY=worldClampedY)

    def _createRenderer(self) -> cartographer.RenderContext:
        return cartographer.RenderContext(
            graphics=self._graphics,
            absoluteCenterX=self._absoluteCenterPos.x(),
            absoluteCenterY=self._absoluteCenterPos.y(),
            scale=self._viewScale.linear,
            outputPixelX=self.width(),
            outputPixelY=self.height(),
            style=app.Config.instance().mapStyle(),
            options=cartographer.mapOptionsToRenderOptions(
                app.Config.instance().mapOptions()),
            imageCache=self._imageCache,
            vectorCache=self._vectorCache,
            labelCache=self._labelCache,
            styleCache=self._styleCache)

    def _handleViewUpdate(
            self,
            forceAtomicRedraw: bool = False
            ) -> None:
        absoluteWidth = self.width() / (self._viewScale.linear * travellermap.ParsecScaleX)
        absoluteHeight = self.height() / (self._viewScale.linear * travellermap.ParsecScaleY)
        absoluteLeft = self._absoluteCenterPos.x() - (absoluteWidth / 2)
        absoluteTop = self._absoluteCenterPos.y() - (absoluteHeight / 2)

        self._imageSpaceToWorldSpace = QtGui.QTransform()
        self._imageSpaceToWorldSpace.scale(
            self._viewScale.linear * travellermap.ParsecScaleX,
            self._viewScale.linear * travellermap.ParsecScaleY)
        self._imageSpaceToWorldSpace.translate(
            -absoluteLeft,
            -absoluteTop)

        scaleMatrix = QtGui.QTransform()
        scaleMatrix.scale(
            1 / travellermap.ParsecScaleX,
            1 / travellermap.ParsecScaleY)
        self._imageSpaceToOverlaySpace = scaleMatrix * self._imageSpaceToWorldSpace

        # Clear the tile queue as the render view/style map have
        # changed so previous queue map be invalid. The redraw
        # that is triggered will refill the queue if needed
        self._tileQueue.clear()
        self._tileTimer.stop()

        self._forceAtomicRedraw = forceAtomicRedraw

        self.update() # Trigger redraw

    def _zoomView(
            self,
            step: float,
            cursor: typing.Optional[QtCore.QPoint] = None
            ) -> None:
        if cursor:
            oldWorldCursor = self._pixelSpaceToWorldSpace(cursor)

        logViewScale = self._viewScale.log
        logViewScale += step
        logViewScale = common.clamp(logViewScale, LocalMapWidget._MinScale, LocalMapWidget._MaxScale)
        if logViewScale == self._viewScale.log:
            return # Reached min/max zoom
        self._viewScale.log = logViewScale

        if cursor:
            newWorldCursor = self._pixelSpaceToWorldSpace(cursor)

            self._absoluteCenterPos.setX(
                self._absoluteCenterPos.x() + (oldWorldCursor.x() - newWorldCursor.x()))
            self._absoluteCenterPos.setY(
                self._absoluteCenterPos.y() + (oldWorldCursor.y() - newWorldCursor.y()))

        self._handleViewUpdate()

    def _currentDrawTiles(
            self,
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
        tileSize = LocalMapWidget._TileSize * tileMultiplier

        scaleX = (self._viewScale.linear * travellermap.ParsecScaleX)
        scaleY = (self._viewScale.linear * travellermap.ParsecScaleY)
        absoluteViewWidth = self.width() / scaleX
        absoluteViewHeight = self.height() / scaleY
        absoluteViewLeft = self._absoluteCenterPos.x() - (absoluteViewWidth / 2)
        absoluteViewRight = absoluteViewLeft + absoluteViewWidth
        absoluteViewTop = self._absoluteCenterPos.y() - (absoluteViewHeight / 2)
        absoluteViewBottom = absoluteViewTop + absoluteViewHeight

        absoluteTileWidth = tileSize / scaleX
        absoluteTileHeight = tileSize / scaleY
        leftTile = math.floor(absoluteViewLeft / absoluteTileWidth)
        rightTile = math.floor(absoluteViewRight / absoluteTileWidth)
        topTile = math.floor(absoluteViewTop / absoluteTileHeight)
        bottomTile = math.floor(absoluteViewBottom / absoluteTileHeight)

        offsetX = (absoluteViewLeft - (leftTile * absoluteTileWidth)) * scaleX
        offsetY = (absoluteViewTop - (topTile * absoluteTileHeight)) * scaleY

        cursorPos = self.mapFromGlobal(QtGui.QCursor.pos())
        isCursorOverWindow = cursorPos.x() >= 0 and cursorPos.x() < self.width() and \
            cursorPos.y() >= 0 and cursorPos.y() < self.height()
        if isCursorOverWindow:
            # If the cursor is over the window, fan out from the cursor
            # position when generating tiles
            absoluteOrigin = self._pixelSpaceToWorldSpace(cursorPos)
        else:
            # If the cursor is not over the window, fan out from the
            # center of the view when generating tiles
            absoluteOrigin = self._absoluteCenterPos
        centerTileX = math.floor(absoluteOrigin.x() / absoluteTileWidth)
        centerTileY = math.floor(absoluteOrigin.y() / absoluteTileHeight)

        self._tileTimer.stop()
        self._tileQueue.clear()

        tiles = []
        image = self._lookupTile(
            tileX=centerTileX,
            tileY=centerTileY,
            tileScale=tileScale,
            createMissing=createMissing)
        renderRect = QtCore.QRectF(
            ((centerTileX - leftTile) * tileSize) - offsetX,
            ((centerTileY - topTile) * tileSize) - offsetY,
            tileSize,
            tileSize)
        if image:
            tiles.append((image, renderRect, None))
        else:
            placeholders = self._gatherPlaceholderTiles(
                currentScale=tileScale,
                tileRect=renderRect)
            if placeholders:
                tiles.extend(placeholders)

        minTileX = centerTileX - 1
        maxTileX = centerTileX + 1
        minTileY = centerTileY - 1
        maxTileY = centerTileY + 1
        while minTileX >= leftTile or maxTileX <= rightTile or minTileY >= topTile or maxTileY <= bottomTile:
            if minTileY >= topTile:
                for x in range(max(minTileX, leftTile), min(maxTileX, rightTile + 1)):
                    image = self._lookupTile(
                        tileX=x,
                        tileY=minTileY,
                        tileScale=tileScale,
                        createMissing=createMissing)
                    renderRect = QtCore.QRectF(
                        ((x - leftTile) * tileSize) - offsetX,
                        ((minTileY - topTile) * tileSize) - offsetY,
                        tileSize,
                        tileSize)
                    if image:
                        tiles.append((image, renderRect, None))
                    else:
                        placeholders = self._gatherPlaceholderTiles(
                            currentScale=tileScale,
                            tileRect=renderRect)
                        if placeholders:
                            tiles.extend(placeholders)

            if maxTileX <= rightTile:
                for y in range(max(minTileY, topTile), min(maxTileY, bottomTile + 1)):
                    image = self._lookupTile(
                        tileX=maxTileX,
                        tileY=y,
                        tileScale=tileScale,
                        createMissing=createMissing)
                    renderRect = QtCore.QRectF(
                        ((maxTileX - leftTile) * tileSize) - offsetX,
                        ((y - topTile) * tileSize) - offsetY,
                        tileSize,
                        tileSize)
                    if image:
                        tiles.append((image, renderRect, None))
                    else:
                        placeholders = self._gatherPlaceholderTiles(
                            currentScale=tileScale,
                            tileRect=renderRect)
                        if placeholders:
                            tiles.extend(placeholders)

            if maxTileY <= bottomTile:
                for x in range(min(maxTileX, rightTile), max(minTileX, leftTile - 1), -1):
                    image = self._lookupTile(
                        tileX=x,
                        tileY=maxTileY,
                        tileScale=tileScale,
                        createMissing=createMissing)
                    renderRect = QtCore.QRectF(
                        ((x - leftTile) * tileSize) - offsetX,
                        ((maxTileY - topTile) * tileSize) - offsetY,
                        tileSize,
                        tileSize)
                    if image:
                        tiles.append((image, renderRect, None))
                    else:
                        placeholders = self._gatherPlaceholderTiles(
                            currentScale=tileScale,
                            tileRect=renderRect)
                        if placeholders:
                            tiles.extend(placeholders)

            if minTileX >= leftTile:
                for y in range(min(maxTileY, bottomTile), max(minTileY, topTile - 1), -1):
                    image = self._lookupTile(
                        tileX=minTileX,
                        tileY=y,
                        tileScale=tileScale,
                        createMissing=createMissing)
                    renderRect = QtCore.QRectF(
                        ((minTileX - leftTile) * tileSize) - offsetX,
                        ((y - topTile) * tileSize) - offsetY,
                        tileSize,
                        tileSize)
                    if image:
                        tiles.append((image, renderRect, None))
                    else:
                        placeholders = self._gatherPlaceholderTiles(
                            currentScale=tileScale,
                            tileRect=renderRect)
                        if placeholders:
                            tiles.extend(placeholders)

            minTileX -= 1
            maxTileX += 1
            minTileY -= 1
            maxTileY += 1

        return tiles

    def _loadLookaheadTiles(self) -> None:
        # This method of rounding the scale is intended to match how it would
        # be rounded by the Traveller Map Javascript code which uses Math.round
        # https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Math/round
        tileScale = int(math.floor(self._viewScale.log + 0.5))

        tileMultiplier = math.pow(2, self._viewScale.log - tileScale)
        tileSize = LocalMapWidget._TileSize * tileMultiplier

        scaleX = (self._viewScale.linear * travellermap.ParsecScaleX)
        scaleY = (self._viewScale.linear * travellermap.ParsecScaleY)
        absoluteViewWidth = self.width() / scaleX
        absoluteViewHeight = self.height() / scaleY
        absoluteViewLeft = self._absoluteCenterPos.x() - (absoluteViewWidth / 2)
        absoluteViewRight = absoluteViewLeft + absoluteViewWidth
        absoluteViewTop = self._absoluteCenterPos.y() - (absoluteViewHeight / 2)
        absoluteViewBottom = absoluteViewTop + absoluteViewHeight

        absoluteTileWidth = tileSize / scaleX
        absoluteTileHeight = tileSize / scaleY
        leftTile = math.floor(absoluteViewLeft / absoluteTileWidth)
        rightTile = math.floor(absoluteViewRight / absoluteTileWidth)
        topTile = math.floor(absoluteViewTop / absoluteTileHeight)
        bottomTile = math.floor(absoluteViewBottom / absoluteTileHeight)

        for _ in range(LocalMapWidget._LookaheadBorderTiles):
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
        key = (
            tileX,
            tileY,
            tileScale,
            self._renderer.style(),
            int(self._renderer.options()))
        image = self._sharedTileCache.get(key)
        if not image:
            if not createMissing:
                # Add the tile to the queue of tiles to be created in the background
                if key not in self._tileQueue:
                    self._tileQueue.append(key)
            else:
                # Render the tile
                image = None
                if self._sharedTileCache.isFull():
                    # Reuse oldest cached tile
                    _, image = self._sharedTileCache.pop()
                image = self._renderTile(tileX, tileY, tileScale, image)
                self._sharedTileCache[key] = image
        return image

    def _gatherPlaceholderTiles(
            self,
            currentScale: int,
            tileRect: QtCore.QRectF
            ) -> typing.List[typing.Tuple[
                QtGui.QImage,
                QtCore.QRectF, # Render rect
                typing.Optional[QtCore.QRectF]]]: # Clip rect
        viewRect = QtCore.QRectF(0, 0, self.width(), self.height())
        clipRect = tileRect.intersected(viewRect)

        placeholders = self._findPlaceholderTiles(
            currentScale=currentScale,
            tileRect=tileRect,
            clipRect=clipRect,
            lookLower=True)
        if placeholders:
            return placeholders

        placeholders = self._findPlaceholderTiles(
            currentScale=currentScale,
            tileRect=tileRect,
            clipRect=clipRect,
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
            lookLower: bool
            ) -> typing.Iterable[typing.Tuple[
                QtGui.QImage,
                QtCore.QRectF, # Render rect
                typing.Optional[QtCore.QRectF]]]: # Clip rect
        placeholderScale = currentScale + (-1 if lookLower else 1)
        if placeholderScale < LocalMapWidget._MinScale or placeholderScale > LocalMapWidget._MaxScale:
            return[]

        tileMultiplier = math.pow(2, self._viewScale.log - placeholderScale)
        tileSize = LocalMapWidget._TileSize * tileMultiplier

        scaleX = (self._viewScale.linear * travellermap.ParsecScaleX)
        scaleY = (self._viewScale.linear * travellermap.ParsecScaleY)
        absoluteViewWidth = self.width() / scaleX
        absoluteViewHeight = self.height() / scaleY
        absoluteViewLeft = self._absoluteCenterPos.x() - (absoluteViewWidth / 2)
        absoluteViewTop = self._absoluteCenterPos.y() - (absoluteViewHeight / 2)

        absoluteTileWidth = tileSize / scaleX
        absoluteTileHeight = tileSize / scaleY
        leftTile = math.floor((((clipRect.left() / scaleX) + absoluteViewLeft) / absoluteTileWidth))
        rightTile = math.floor((((clipRect.right() / scaleX) + absoluteViewLeft) / absoluteTileWidth))
        topTile = math.floor((((clipRect.top() / scaleY) + absoluteViewTop) / absoluteTileHeight))
        bottomTile = math.floor((((clipRect.bottom() / scaleY) + absoluteViewTop) / absoluteTileHeight))

        offsetX = (absoluteViewLeft - (leftTile * absoluteTileWidth)) * scaleX
        offsetY = (absoluteViewTop - (topTile * absoluteTileHeight)) * scaleY

        placeholders = []
        missing = []
        for x in range(leftTile, rightTile + 1):
            for y in range(topTile, bottomTile + 1):
                key = (
                    x,
                    y,
                    placeholderScale,
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
        self._tileQueue.clear()
        self._tileTimer.stop()
        self.update() # Force redraw

    def _renderTile(
            self,
            tileX: int,
            tileY: int,
            tileScale: int, # Log scale rounded down
            image: typing.Optional[QtGui.QImage]
            ) -> QtGui.QImage:
        tileScale = travellermap.logScaleToLinearScale(tileScale)
        scaleX = (tileScale * travellermap.ParsecScaleX)
        scaleY = (tileScale * travellermap.ParsecScaleY)
        absoluteTileWidth = LocalMapWidget._TileSize / scaleX
        absoluteTileHeight = LocalMapWidget._TileSize / scaleY

        absoluteTileCenterX = ((tileX * LocalMapWidget._TileSize) / scaleX) + (absoluteTileWidth / 2)
        absoluteTileCenterY = ((tileY * LocalMapWidget._TileSize) / scaleY) + (absoluteTileHeight / 2)

        if not image:
            image = QtGui.QImage(
                LocalMapWidget._TileSize,
                LocalMapWidget._TileSize,
                QtGui.QImage.Format.Format_ARGB32)
        painter = QtGui.QPainter()
        painter.begin(image)
        try:
            self._graphics.setPainter(painter=painter)
            self._renderer.setView(
                absoluteCenterX=absoluteTileCenterX,
                absoluteCenterY=absoluteTileCenterY,
                scale=tileScale,
                outputPixelX=LocalMapWidget._TileSize,
                outputPixelY=LocalMapWidget._TileSize)
            self._renderer.render()
        finally:
            self._graphics.setPainter(painter=None)
            painter.end()

        return image

    def _handleTileTimer(self) -> None:
        tileX, tileY, tileScale, _, _ = self._tileQueue.pop(0)
        image = None
        if self._sharedTileCache.isFull():
            # Reuse oldest cached tile
            _, image = self._sharedTileCache.pop()
        key = (
            tileX,
            tileY,
            tileScale,
            self._renderer.style(),
            int(self._renderer.options()))
        self._sharedTileCache[key] = self._renderTile(
            tileX=tileX,
            tileY=tileY,
            tileScale=tileScale,
            image=image)
        if self._tileQueue:
            self._tileTimer.start()
        self.update()

    @staticmethod
    def _createPlaceholderTile() -> QtGui.QImage:
        image = QtGui.QImage(
            LocalMapWidget._TileSize,
            LocalMapWidget._TileSize,
            QtGui.QImage.Format.Format_ARGB32)
        rectsPerSize = math.ceil(LocalMapWidget._TileSize / LocalMapWidget._CheckerboardRectSize)

        painter = QtGui.QPainter()
        with gui.PainterDrawGuard(painter, image):
            painter.setBrush(QtGui.QColor(LocalMapWidget._CheckerboardColourA))
            painter.drawRect(0, 0, LocalMapWidget._TileSize, LocalMapWidget._TileSize)

            painter.setBrush(QtGui.QColor(LocalMapWidget._CheckerboardColourB))
            for x in range(rectsPerSize):
                for y in range(1 if x % 2 else 0, rectsPerSize, 2):
                    painter.drawRect(
                        x * LocalMapWidget._CheckerboardRectSize,
                        y * LocalMapWidget._CheckerboardRectSize,
                        LocalMapWidget._CheckerboardRectSize,
                        LocalMapWidget._CheckerboardRectSize)

        return image
