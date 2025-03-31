import app
import common
import enum
import gui
import logic
import logging
import proxy
import math
import os
import re
import travellermap
import typing
import uuid
from PyQt5 import QtWebEngineWidgets, QtCore, QtGui, QtWidgets, sip

class _CustomWebEnginePage(QtWebEngineWidgets.QWebEnginePage):
    # Massive Hack: This message is expected as a local snapshot of the Traveller Map web interface
    # is used but it's pulling data from the real www.travellermap.com. The message is silently
    # ignored to avoid spamming logs.
    _IgnoreConsoleMessage = \
        'A cookie associated with a cross-site resource at http://travellermap.com/ was set ' \
        'without the `SameSite` attribute. A future release of Chrome will only deliver cookies ' \
        'with cross-site requests if they are set with `SameSite=None` and `Secure`. You can ' \
        'review cookies in developer tools under Application>Storage>Cookies and see more ' \
        'details at https://www.chromestatus.com/feature/5088147346030592 and ' \
        'https://www.chromestatus.com/feature/5633521622188032.'

    def acceptNavigationRequest(
            self,
            url: QtCore.QUrl,
            type: QtWebEngineWidgets.QWebEnginePage.NavigationType,
            isMainFrame: bool):
        # Prevent opening clicked links in the current page, open them in an external browser
        # instead
        if type == QtWebEngineWidgets.QWebEnginePage.NavigationType.NavigationTypeLinkClicked:
            QtGui.QDesktopServices.openUrl(url)
            return False
        return True

    def javaScriptConsoleMessage(
            self,
            level: QtWebEngineWidgets.QWebEnginePage.JavaScriptConsoleMessageLevel,
            message: str,
            lineNumber: int,
            sourceID: str
            ) -> None:
        # Don't call base implementation as all it does is write to the console
        #super().javaScriptConsoleMessage(level, message, lineNumber, sourceID)

        if message == _CustomWebEnginePage._IgnoreConsoleMessage:
            return

        logMessage = f'{sourceID} line {lineNumber}\n{message}'

        if level == QtWebEngineWidgets.QWebEnginePage.JavaScriptConsoleMessageLevel.InfoMessageLevel:
            logging.info(logMessage)
        elif level == QtWebEngineWidgets.QWebEnginePage.JavaScriptConsoleMessageLevel.WarningMessageLevel:
            logging.warning(logMessage)
        elif level == QtWebEngineWidgets.QWebEnginePage.JavaScriptConsoleMessageLevel.ErrorMessageLevel:
            logging.error(logMessage)

class _HexHighlight(object):
    def __init__(
            self,
            hex: travellermap.HexPosition,
            colour: str
            ) -> None:
        self._hex = hex
        self._colour = colour

    def hex(self) -> travellermap.HexPosition:
        return self._hex

    def colour(self) -> str:
        return self._colour

class _CircleHighlight(object):
    def __init__(
            self,
            hex: travellermap.HexPosition,
            colour: str,
            radius: float
            ) -> None:
        self._hex = hex
        self._colour = colour
        self._radius = radius

    def hex(self) -> travellermap.HexPosition:
        return self._hex

    def colour(self) -> str:
        return self._colour

    def radius(self) -> float:
        return self._radius

class _Polygon(object):
    def __init__(
            self,
            mapPoints: typing.Iterable[typing.Tuple[float, float]],
            fillColour: typing.Optional[str] = None,
            lineColour: typing.Optional[str] = None,
            lineWidth: typing.Optional[int] = None # In pixels
            ) -> None:
        self._mapPoints = list(mapPoints)
        self._fillColour = fillColour
        self._lineColour = lineColour
        self._lineWidth = lineWidth

    def maPoints(self) -> typing.Iterable[typing.Tuple[float, float]]:
        return self._mapPoints

    def fillColour(self) -> typing.Optional[str]:
        return self._fillColour

    def lineColour(self) -> typing.Optional[str]:
        return self._lineColour

    def lineWidth(self) -> typing.Optional[int]:
        return self._lineWidth

class _Overlay(object):
    def __init__(
            self,
            ) -> None:
        self._handle = str(uuid.uuid4())
        self._overlays = []

    def handle(self) -> str:
        return self._handle

    def items(self) -> typing.Iterable[typing.Union[_HexHighlight, _Polygon]]:
        return self._overlays

    def addItem(self, overlay: typing.Union[_HexHighlight, _Polygon]) -> None:
        self._overlays.append(overlay)

class WebMapWidget(QtWidgets.QWidget):
    leftClicked = QtCore.pyqtSignal([travellermap.HexPosition])
    rightClicked = QtCore.pyqtSignal([travellermap.HexPosition])

    # Number of pixels of movement we allow between the left mouse button down and up events for
    # the action to be counted as a click. I found that forcing no movement caused clicks to be
    # missed
    _LeftClickMoveThreshold = 3

    # Number of pixels the cursor can move before the displayed tool tip will be hidden
    _ToolTipMoveThreshold = 5

    _JumpRoutePitStopRadius: float = 0.4, # Default to slightly larger than the size of the highlights Traveller Map puts on jump worlds
    _JumpRoutePitStopColour: str = '#8080FF'

    # Shared profile used by all instances of this widget. With Qt5 I could use the default profile,
    # however that wouldn't be possible if/when I switch to Qt6 as the default profile doesn't
    # persist cookies under Qt6. To avoid potential future issues I'm just using a custom shared
    # profile from the get go.
    _sharedProfile = None

    # Next script id (used for debugging)
    _nextScriptId = 1

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self._loaded = False
        self._scriptQueue: typing.List[str] = []
        self._clickTrackingRect = None

        self._overlays: typing.Dict[str, _Overlay] = {}

        self._jumpRoute = None
        self._refuellingPlanOverlayHandle = None

        self._hexHighlights: typing.List[_CircleHighlight] = []

        self._toolTipCallback = None
        self._toolTipTimer = None
        self._toolTipDisplayPos = None
        self._toolTipQueuePos = None
        self._toolTipScriptRunning = False

        if not WebMapWidget._sharedProfile:
            # Create a shared profile for use by all instances of the widget. It's important to use
            # the application as the parent to prevent the error "Release of profile requested but
            # WebEnginePage still not deleted. Expect troubles !" being written out on application
            # shutdown.
            # https://stackoverflow.com/questions/64719361/closing-qwebengineview-warns-release-of-profile-requested-but-webenginepage-sti
            WebMapWidget._sharedProfile = QtWebEngineWidgets.QWebEngineProfile(
                'TravellerMapWidget',
                QtWidgets.QApplication.instance())
            WebMapWidget._sharedProfile.setHttpCacheType(
                QtWebEngineWidgets.QWebEngineProfile.HttpCacheType.DiskHttpCache)
            WebMapWidget._sharedProfile.setCachePath(
                os.path.join(app.Config.instance().appDir(), 'webwidget', 'cache'))
            WebMapWidget._sharedProfile.setPersistentCookiesPolicy(
                QtWebEngineWidgets.QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)
            WebMapWidget._sharedProfile.setPersistentStoragePath(
                os.path.join(app.Config.instance().appDir(), 'webwidget', 'persist'))

        page = _CustomWebEnginePage(WebMapWidget._sharedProfile, self)
        self._mapWidget = QtWebEngineWidgets.QWebEngineView()
        self._mapWidget.setPage(page)
        self._mapWidget.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.NoContextMenu)
        self._mapWidget.settings().setAttribute(
            QtWebEngineWidgets.QWebEngineSettings.WebAttribute.JavascriptEnabled,
            True)
        self._mapWidget.settings().setAttribute(
            QtWebEngineWidgets.QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls,
            True)
        self._mapWidget.loadFinished.connect(self._loadFinished)

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._mapWidget)

        self.setLayout(layout)
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.ActionsContextMenu)

        self._loadMap()

    def reload(self) -> None:
        self._loaded = False
        self._scriptQueue.clear()
        self._clickTrackingRect = None
        self._hideToolTip()
        self._loadMap()

    def centerOnHex(
            self,
            hex: travellermap.HexPosition,
            linearScale: typing.Optional[float] = 64 # None keeps current scale
            ) -> None:
        sectorX, sectorY, offsetX, offsetY = hex.relative()
        if linearScale != None:
            script = f'map.CenterAtSectorHex({sectorX}, {sectorY}, {offsetX}, {offsetY}, {{scale: {linearScale}}})'
        else:
            # When keeping the current scale, it's important to use map.scale rather than extracting
            # the scale from the current url. This is required in order for movements to be animated
            # rather than hard cuts to the new location. The implementation of CenterAtSectorHex
            # will only animate if the new scale is exactly the same as current scale. As the scale
            # is a float the only reliable way to do this is to use the current value.
            script = f'map.CenterAtSectorHex({sectorX}, {sectorY}, {offsetX}, {offsetY}, {{scale: map.scale}})'

        self._runScript(script)

    def centerOnHexes(
            self,
            hexes: typing.Collection[travellermap.HexPosition]
            ) -> None:
        if not hexes:
            return
        if len(hexes) == 1:
            # If there is just one world in the list so just show use centerOnHex. This avoids
            # zooming to far because the bounding box surrounding the worlds has no size
            self.centerOnHex(hex=next(iter(hexes)))
            return

        minX = maxX = minY = maxY = None
        for hex in hexes:
            absoluteX, absoluteY = hex.absolute()
            if minX == None or absoluteX < minX:
                minX = absoluteX
            if maxX == None or absoluteX > maxX:
                maxX = absoluteX
            if minY == None or absoluteY < minY:
                minY = absoluteY
            if maxY == None or absoluteY > maxY:
                maxY = absoluteY

        # Increase the bounding box to avoid zooming in to much with just a small number of close together
        # worlds
        minX -= 1
        maxX += 1
        minY -= 1
        maxY += 1

        script = f'map.CenterOnArea({minX}, {minY}, {maxX}, {maxY});'
        self._runScript(script=script)

    def hasJumpRoute(self) -> bool:
        return self._jumpRoute != None

    def setJumpRoute(
            self,
            jumpRoute: typing.Optional[logic.JumpRoute],
            refuellingPlan: typing.Optional[typing.Iterable[logic.PitStop]] = None
            ) -> None:
        if not jumpRoute:
            self.clearJumpRoute()
            return

        self._jumpRoute = jumpRoute

        if self._loaded:
            self._runJumpRouteScript(jumpRoute)

        if refuellingPlan:
            self._refuellingPlanOverlayHandle = self.createHexOverlay(
                hexes=[pitStop.world().hex() for pitStop in refuellingPlan],
                primitive=gui.MapPrimitiveType.Circle,
                radius=WebMapWidget._JumpRoutePitStopRadius,
                fillColour=WebMapWidget._JumpRoutePitStopColour)
        elif self._refuellingPlanOverlayHandle != None:
            self.removeOverlay(handle=self._refuellingPlanOverlayHandle)
            self._refuellingPlanOverlayHandle = None

    def clearJumpRoute(self) -> None:
        self._jumpRoute = None
        if self._loaded:
            script = """
                map.SetRoute(null);
                """
            self._runScript(script)

        if self._refuellingPlanOverlayHandle != None:
            self.removeOverlay(handle=self._refuellingPlanOverlayHandle)
            self._refuellingPlanOverlayHandle = None

    def centerOnJumpRoute(self) -> None:
        if not self._jumpRoute:
            return

        hexes = [nodeHex for nodeHex, _ in self._jumpRoute]
        self.centerOnHexes(hexes=hexes)

    def highlightHex(
            self,
            hex: travellermap.HexPosition,
            radius: float = 0.5,
            colour: str = '#8080FF'
            ) -> None:
        overlay = _CircleHighlight(
            hex=hex,
            radius=radius,
            colour=colour)
        self._hexHighlights.append(overlay)

        if self._loaded:
            self._runAddHexHighlightScript(highlight=overlay)

    def highlightHexes(
            self,
            hexes: typing.Iterable[travellermap.HexPosition],
            radius: float = 0.5,
            colour: str = '#8080FF'
            ) -> None:
        for hex in hexes:
            self.highlightHex(
                hex=hex,
                radius=radius,
                colour=colour)

    def clearHexHighlight(
            self,
            hex: travellermap.HexPosition
            ) -> None:
        self._hexHighlights = [overlay for overlay in self._hexHighlights if overlay.hex() != hex]

        if self._loaded:
            absoluteX, absoluteY = hex.absolute()
            script = """
                var worldX = {x}, worldY = {y};
                var filterCallback = (overlay) => {{
                    if (overlay.hasOwnProperty("handle")) {{
                        return true;
                    }}
                    var worldPos = Traveller.Astrometrics.mapToWorld(overlay.x, overlay.y);
                    return worldPos.x != worldX || worldPos.y != worldY;
                }};
                map.FilterOverlays(filterCallback);
                """.format(x=absoluteX, y=absoluteY)
            self._runScript(script)

    def clearHexHighlights(self) -> None:
        self._hexHighlights.clear()

        if self._loaded:
            script = """
                var filterCallback = (overlay) => {{
                    if (overlay.hasOwnProperty("handle")) {{
                        return true;
                    }}
                }};
                map.FilterOverlays(filterCallback);
                """
            self._runScript(script)

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
        overlay = _Overlay()
        for hex in hexes:
            itemFillColour = fillMap.get(hex, fillColour) if fillMap else fillColour
            if primitive == gui.MapPrimitiveType.Hex:
                item = _HexHighlight(
                    hex=hex,
                    colour=itemFillColour)
            else:
                item = _CircleHighlight(
                    hex=hex,
                    radius=radius,
                    colour=itemFillColour)
            overlay.addItem(item)
        self._overlays[overlay.handle()] = overlay

        if self._loaded:
            self._runAddOverlayScript(overlay=overlay)

        return overlay.handle()

    # Create an overlay where groups of touching hexes have a border drawn
    # around them
    def createHexGroupsOverlay(
            self,
            hexes: typing.Iterable[travellermap.HexPosition],
            fillColour: typing.Optional[str] = None,
            lineColour: typing.Optional[str] = None,
            lineWidth: typing.Optional[int] = None,
            outerOutlinesOnly: bool = False
            ) -> str:
        overlay = _Overlay()
        self._overlays[overlay.handle()] = overlay

        if outerOutlinesOnly:
            borders = logic.calculateOuterHexOutlines(hexes=hexes)
        else:
            borders = logic.calculateCompleteHexOutlines(hexes=hexes)
        if not borders:
            # Still return the group even if there were no borders, but there
            # is no point running a script
            return overlay.handle()

        for border in borders:
            overlay.addItem(_Polygon(
                mapPoints=border,
                fillColour=fillColour,
                lineColour=lineColour,
                lineWidth=lineWidth))

        if self._loaded:
            self._runAddOverlayScript(overlay=overlay)

        return overlay.handle()

    # Create an overlay covering all hexes within the specified radius of the
    # center hex
    def createRadiusOverlay(
            self,
            center: travellermap.HexPosition,
            radius: int,
            fillColour: typing.Optional[str] = None,
            lineColour: typing.Optional[str] = None,
            lineWidth: typing.Optional[int] = None
            ) -> str:
        radiusHexes = list(center.yieldRadiusHexes(
            radius=radius,
            includeInterior=False))
        return self.createHexGroupsOverlay(
            hexes=radiusHexes,
            fillColour=fillColour,
            lineColour=lineColour,
            lineWidth=lineWidth,
            outerOutlinesOnly=True)

    def removeOverlay(
            self,
            handle: str
            ) -> None:
        if handle in self._overlays:
            del self._overlays[handle]

        if self._loaded:
            script = """
                var handle = "{handle}";
                var filterCallback = (overlay) => {{
                    if (!overlay.hasOwnProperty("handle")) {{
                        return true;
                    }}
                    return overlay.handle != handle;
                }};
                map.FilterOverlays(filterCallback);
                """.format(handle=handle)
            self._runScript(script)

    def setToolTipCallback(
            self,
            callback: typing.Optional[typing.Callable[[typing.Optional[travellermap.HexPosition]], typing.Optional[str]]],
            ) -> None:
        self._toolTipCallback = callback

    def createSnapshot(self) -> QtGui.QPixmap:
        view = self._mapWidget.page().view()
        size = view.size()

        image = QtGui.QPixmap(size.width(), size.height())
        painter = QtGui.QPainter(image)
        self._mapWidget.page().view().render(
            painter,
            QtCore.QPoint(),
            QtGui.QRegion(0, 0, size.width(), size.height()))
        painter.end()
        return image

    # There is no state to save/restore but the methods are part of the
    # interface shared by local & web maps
    def saveState(self) -> QtCore.QByteArray:
        pass

    def restoreState(self, state: QtCore.QByteArray) -> bool:
        pass

    def eventFilter(self, object: object, event: QtCore.QEvent) -> bool:
        if object == self._mapWidget.focusProxy():
            if event.type() == QtCore.QEvent.Type.MouseButtonPress:
                assert(isinstance(event, QtGui.QMouseEvent))
                if event.button() == QtCore.Qt.MouseButton.LeftButton:
                    clickPos = event.pos()
                    self._clickTrackingRect = QtCore.QRect(
                        clickPos.x() - self._LeftClickMoveThreshold,
                        clickPos.y() - self._LeftClickMoveThreshold,
                        (self._LeftClickMoveThreshold * 2) + 1,
                        (self._LeftClickMoveThreshold * 2) + 1)
            elif event.type() == QtCore.QEvent.Type.MouseButtonRelease:
                assert(isinstance(event, QtGui.QMouseEvent))
                if event.button() == QtCore.Qt.MouseButton.LeftButton:
                    if self._clickTrackingRect and self._clickTrackingRect.contains(event.pos()):
                        self._primeLeftClickEvent(event.pos())
                    self._clickTrackingRect = None
            elif event.type() == QtCore.QEvent.Type.ContextMenu:
                assert(isinstance(event, QtGui.QContextMenuEvent))
                self._primeRightClickEvent(event.pos())
            elif event.type() == QtCore.QEvent.Type.MouseMove:
                assert(isinstance(event, QtGui.QMouseEvent))
                if self._toolTipCallback:
                    self._updateToolTip(event.pos())

        return super().eventFilter(object, event)

    # Replace the standard Util.fetchImage function with one that does a round robin
    # of of hosts for loopback requests in order to work around the hard coded limit
    # of 6 connections per host that the underlying Chromium browser enforces.
    # NOTE: This only affects connections to the proxy so cached tiles can be returned
    # without having to wait for the requests for non-cached tiles. The proxy still
    # limits the number of outgoing connections to 6.
    # NOTE: This should only be done when routing through the proxy. It doesn't work
    # when accessing local instances of Traveller Map directly as it only listens on
    # 127.0.0.1
    def _injectImageHostRoundRobin(self) -> None:
        script = """
            const LoopbackRegex = /^(127\\.\\d\\.\\d\\.\\d|localhost|loopback)$/;
            let nextImageHost = 1;
            let imageHostCount = {poolSize};

            Util.real_fetchImage = Util.fetchImage;

            Util.fetchImage = function(url, img) {{
                if (url.startsWith("/")) {{
                    hostname = document.location.hostname;
                }} else {{
                    let parsedUrl = new URL(url);
                    hostname = parsedUrl.hostname;
                }}

                if (hostname.match(LoopbackRegex)) {{
                    let authority = "127.0.0." + nextImageHost;
                    if (document.location.port) {{
                        authority += ":" + document.location.port;
                    }}
                    url = document.location.protocol + "//" + authority + url;

                    nextImageHost += 1
                    if (nextImageHost > imageHostCount) {{
                        nextImageHost = 1;
                    }}
                }}

                return Util.real_fetchImage(url, img);
            }};
            """.format(poolSize=proxy.MapProxy.instance().hostPoolSize())
        self._runScript(script)

    # NOTE: The 'tilt' url parameter isn't supported as it doesn't draw properly in the Qt widget
    def _generateUrl(self) -> QtCore.QUrl:
        currentUrl = self._mapWidget.url().toString()
        currentPos = travellermap.parsePosFromMapUrl(url=currentUrl) if currentUrl else None
        currentScale = travellermap.parseScaleFromMapUrl(url=currentUrl) if currentUrl else None

        installDir = app.Config.instance().installDir()
        rootPath = installDir.replace('\\', '/') if common.isWindows() else installDir

        if proxy.MapProxy.instance().isRunning():
            indexUrl = proxy.MapProxy.instance().accessUrl()
        else:
            indexUrl = f'file:///{rootPath}/data/web/'

        options = set(app.Config.instance().mapOptions())
        options.add(travellermap.Option.HideUI) # Always hide the UI

        return QtCore.QUrl(travellermap.formatMapUrl(
            baseMapUrl=indexUrl,
            milieu=app.Config.instance().milieu(),
            style=app.Config.instance().mapStyle(),
            options=options,
            mapPosition=currentPos,
            linearScale=currentScale))

    def _loadMap(self) -> None:
        url = self._generateUrl()
        logging.debug(f'WebMapWidget loading {url.toString()}')

        if proxy.MapProxy.instance().isRunning():
            self._injectImageHostRoundRobin()

        self._mapWidget.load(url)

    def _runJumpRouteScript(
            self,
            jumpRoute: logic.JumpRoute,
            ) -> None:
        script = 'map.SetRoute(['
        for index in range(jumpRoute.nodeCount()):
            hex = jumpRoute.hex(index)
            sectorX, sectorY, offsetX, offsetY = hex.relative()
            script += f'{{hx:{offsetX}, hy:{offsetY}, sx:{sectorX}, sy:{sectorY}}},'
        script = script.strip(',')
        script += ']);'
        self._runScript(script)

    def _runAddHexHighlightScript(
            self,
            highlight: _CircleHighlight
            ) -> None:
        hex = highlight.hex()
        mapSpace = hex.mapSpace()
        script = """
            var mapX = {x}, mapY = {y};
            var overlay = {{type: 'circle', x:mapX, y:mapY, r:{radius}, style:'{colour}'}};
            map.AddOverlay(overlay);
            """.format(
            x=mapSpace[0],
            y=mapSpace[1],
            radius=highlight.radius(),
            colour=highlight.colour())
        self._runScript(script)

    def _runAddOverlayScript(
            self,
            overlay: _Overlay
            ) -> None:
        hexData = []
        circleData = []
        polygonData = []
        for item in overlay.items():
            if isinstance(item, _HexHighlight):
                hex = item.hex()
                mapSpace = hex.mapSpace()
                hexData.append('[{x}, {y}, "{colour}"]'.format(
                    x=mapSpace[0],
                    y=mapSpace[1],
                    colour=item.colour()))
            elif isinstance(item, _CircleHighlight):
                hex = item.hex()
                mapSpace = hex.mapSpace()
                circleData.append('[{x}, {y}, {radius}, "{colour}"]'.format(
                    x=mapSpace[0],
                    y=mapSpace[1],
                    radius=item.radius(),
                    colour=item.colour()))
            elif isinstance(item, _Polygon):
                points = []
                for x, y in item.maPoints():
                    points.append(f'{{x:{x}, y:{y}}}')

                data = f'{{points:[{",".join(points)}]'
                if item.fillColour() is not None:
                    data += f', fillColour:"{item.fillColour()}"'
                if item.lineColour() is not None:
                    data += f', lineColour:"{item.lineColour()}"'
                if item.lineWidth() is not None:
                    data += f', lineWidth:{item.lineWidth()}'
                data += '}'

                polygonData.append(data)

        if (not hexData) and (not circleData) and (not polygonData):
            return # Nothing to do

        script = """
            var hexes = [{hexData}];
            for (let i = 0; i < hexes.length; i++) {{
                let hex = hexes[i];
                let mapX = hex[0];
                let mapY = hex[1];
                let colour = hex[2];
                let overlay = {{type:'hex', x:mapX, y:mapY, style:colour, handle:'{handle}'}};
                map.AddOverlay(overlay);
            }};
            var circles = [{circleData}];
            for (let i = 0; i < circles.length; i++) {{
                let circle = circles[i];
                let mapX = circle[0];
                let mapY = circle[1];
                let radius = circle[2]
                let colour = circle[3];
                let overlay = {{type:'circle', x:mapX, y:mapY, r:radius, style:colour, handle:'{handle}'}};
                map.AddOverlay(overlay);
            }};
            var polygons = [{polygonData}];
            for (let i = 0; i < polygons.length; i++) {{
                let polygon = polygons[i];
                let overlay = {{type:'polygon', points:polygon.points, handle:'{handle}'}};
                if ('fillColour' in polygon) {{
                    overlay.fill = polygon.fillColour;
                }}
                if ('lineColour' in polygon) {{
                    overlay.line = polygon.lineColour;
                }}
                if ('lineWidth' in polygon) {{
                    overlay.w = polygon.lineWidth;
                }}
                map.AddOverlay(overlay);
            }};
            """.format(
            hexData=','.join(hexData),
            circleData=','.join(circleData),
            polygonData=','.join(polygonData),
            handle=overlay.handle())
        self._runScript(script)

    def _hexAt(
            self,
            point: QtCore.QPoint,
            callback: typing.Callable[[typing.Optional[travellermap.HexPosition]], None]
            ) -> None:
        script = """
            var mapPos = map.pixelToMap({x}, {y});
            var worldPos = Traveller.Astrometrics.mapToWorld(mapPos.x, mapPos.y);
            var wx = (mapPos.x / Traveller.Astrometrics.ParsecScaleX) + 0.5;
            var wy = (-mapPos.y / Traveller.Astrometrics.ParsecScaleY) + ((wx % 2 === 0) ? 0.5 : 0);
            console.log(`${{worldPos.x}} ${{worldPos.y}} ${{wx}} ${{wy}} ${{mapPos.x}} ${{mapPos.y}}`);
            var sectorHex = Traveller.Astrometrics.worldToSectorHex(worldPos.x, worldPos.y);
            `${{sectorHex.sx}} ${{sectorHex.sy}} ${{sectorHex.hx}} ${{sectorHex.hy}}`;
            """.format(x=point.x(), y=point.y())

        self._runScript(
            script=script,
            resultsCallback=lambda results: callback(self._parseCursorHexResult(results)))

    def _parseCursorHexResult(
            self,
            returnValue: str
            ) -> typing.Optional[travellermap.HexPosition]:
        if not returnValue or type(returnValue) != str:
            logging.error(f'Failed to parse WebMapWidget click result (Incorrect result type)')
            return None
        result = re.match(r'^([+-]?\d+) ([+-]?\d+) ([+-]?\d+) ([+-]?\d+)$', returnValue)
        if not result:
            logging.error(f'Failed to parse WebMapWidget click result (Incorrect format "{returnValue}")')
            return None

        try:
            return travellermap.HexPosition(
                sectorX=int(result.group(1)),
                sectorY=int(result.group(2)),
                offsetX=int(result.group(3)),
                offsetY=int(result.group(4)))
        except Exception as ex:
            logging.error(f'Failed to parse WebMapWidget click result (Unexpected exception)', exc_info=ex)
            return None

    def _updateToolTip(
            self,
            cursorPos: QtCore.QPoint
            ) -> None:
        if not self.underMouse():
            # Cursor has moved off the widget so just hide the tool tip
            self._hideToolTip()
            return

        if self._toolTipDisplayPos:
            # A tool tip is currently displayed or in the process of being displayed
            offset = math.sqrt(QtCore.QPoint.dotProduct(cursorPos, self._toolTipDisplayPos))
            if offset <= self._ToolTipMoveThreshold:
                # The cursor movement is within the allowed move threshold
                self._primeToolTipResolve(cursorPos)
                return

            # The cursor movement is outside the allowed move threshold. Hide the current tool tip
            # but pass through to start the timer for the new cursor position
            self._hideToolTip()

        # No tool tip is displayed so start the timer. If the mouse hasn't moved when it fires
        # the tool tip will be displayed
        if not self._toolTipTimer:
            self._toolTipTimer = QtCore.QTimer()
            self._toolTipTimer.timeout.connect(self._toolTipTimerFired)
            self._toolTipTimer.setInterval(1000)
            self._toolTipTimer.setSingleShot(True)
        self._toolTipTimer.start()

    def _hideToolTip(self):
        QtWidgets.QToolTip.hideText()
        if self._toolTipTimer:
            self._toolTipTimer.stop()
        self._toolTipDisplayPos = None
        self._toolTipQueuePos = None
        self._toolTipScriptRunning = False

    def _primeLeftClickEvent(
            self,
            point: QtCore.QPoint
            ) -> None:
        self._hexAt(
            point=point,
            callback=self._handleLeftClickEvent)

    def _primeRightClickEvent(
            self,
            point: QtCore.QPoint
            ) -> None:
        self._hexAt(
            point=point,
            callback=self._handleRightClickEvent)

    def _handleLeftClickEvent(
            self,
            hex: typing.Optional[travellermap.HexPosition]
            ) -> None:
        if hex and self.isEnabled():
            self.leftClicked.emit(hex)

    def _handleRightClickEvent(
            self,
            hex: typing.Optional[travellermap.HexPosition]
            ) -> None:
        if hex and self.isEnabled():
            self.rightClicked.emit(hex)

    def _toolTipTimerFired(self) -> None:
        cursorPos = self.mapFromGlobal(QtGui.QCursor.pos())
        self._primeToolTipResolve(cursorPos)

    def _primeToolTipResolve(
            self,
            cursorPos: QtCore.QPoint
            ) -> None:
        if not self._toolTipScriptRunning:
            self._toolTipDisplayPos = cursorPos
            self._toolTipQueuePos = None
            self._toolTipScriptRunning = True
            self._hexAt(
                point=cursorPos,
                callback=self._handleToolTipEvent)
        else:
            self._toolTipQueuePos = cursorPos

    def _handleToolTipEvent(
            self,
            hex: typing.Optional[travellermap.HexPosition]
            ) -> None:
        if not self._toolTipScriptRunning:
            # Tool tip has been cancelled. Don't call _hideToolTip here as the tool
            # tip timer may have already been started for a new position. This shouldn't
            # be an issue as the expectation is the tool tip would have been hidden at
            # the same point the flag was script running flag was reset
            return
        self._toolTipScriptRunning = False

        if self._toolTipQueuePos:
            # The cursor has moved between the script being started and the results
            # being available. Discard the current results and re-run for the queued
            # position
            self._primeToolTipResolve(self._toolTipQueuePos)
            return

        if not self._toolTipCallback:
            self._hideToolTip()
            return

        toolTip = self._toolTipCallback(hex)
        if not toolTip:
            self._hideToolTip()
            return

        cursorPos = self.mapToGlobal(self._toolTipDisplayPos)
        QtWidgets.QToolTip.showText(cursorPos, toolTip)

    def _loadFinished(self, success: bool) -> None:
        if not success:
            gui.MessageBoxEx.critical(
                parent=self,
                text='Failed to load Traveller Map')
            return

        self._loaded = True

        # Add the current jump route and overlays if there are any. This should be done before
        # running queued scripts in case the scripts are modifying the route/overlay. I suspect
        # there are race conditions here but it seems good enough for what I need.
        if self._jumpRoute:
            self._runJumpRouteScript(jumpRoute=self._jumpRoute)

        for highlight in self._hexHighlights:
            self._runAddHexHighlightScript(highlight=highlight)

        for overlay in self._overlays.values():
            self._runAddOverlayScript(overlay=overlay)

        # Run queued scripts
        for script, resultsCallback in self._scriptQueue:
            self._runScript(script, resultsCallback)
        self._scriptQueue.clear()

        # Install map event filter. This doesn't seem to be possible at construction as the focus
        # proxy doesn't exist at that point.
        self._mapWidget.focusProxy().installEventFilter(self)

    def _runScript(
            self,
            script: str,
            resultsCallback: typing.Optional[typing.Callable[[typing.Any], None]] = None
            ) -> None:
        if not self._loaded:
            self._scriptQueue.append((script, resultsCallback))
            return

        scriptId = WebMapWidget._nextScriptId
        WebMapWidget._nextScriptId += 1

        logging.debug(f'Running script {scriptId}\n{script}')

        self._mapWidget.page().runJavaScript(
            script,
            lambda args: self._scriptCompleteHandler(scriptId=scriptId, callback=resultsCallback, args=args))

    def _scriptCompleteHandler(
            self,
            scriptId: int,
            callback: typing.Optional[typing.Callable[[typing.Any], None]],
            args: typing.Any
            ) -> None:
        # Prevent an exception if the script completes after the wrapped C++ object has been
        # destroyed. I'm sure there must be a better way to do this but I don't know what it is.
        if sip.isdeleted(self):
            logging.debug(f'Script {scriptId} completed after Traveller Map widget was destroyed')
            return

        logging.debug(f'Script {scriptId} completed')
        if callback:
            callback(args)
