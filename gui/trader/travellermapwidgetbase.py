import app
import common
import gui
import logic
import logging
import proxy
import math
import os
import re
import traveller
import travellermap
import typing
from PyQt5 import QtWebEngineCore, QtWebEngineWidgets, QtCore, QtGui, QtWidgets, sip

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

class _MapStyleToggleAction(QtWidgets.QAction):
    def __init__(
            self,
            style: travellermap.Style,
            parent: typing.Optional[QtCore.QObject] = None
            ) -> None:
        super().__init__(style.value, parent)

        self._style = style

        self.setCheckable(True)
        self.setChecked(app.Config.instance().mapStyle() == style)

        # It's important that this is connected to the trigger signal before any instances
        # of TravellerMapWidget. This call needs to made first as it will write the updated
        # setting to the config so the instances of TravellerMapWidget can read it back when
        # updating their URL.
        self.triggered.connect(self._optionToggled)

    def _optionToggled(self) -> None:
        if self.isChecked():
            app.Config.instance().setMapStyle(style=self._style)

class _MapOptionToggleAction(QtWidgets.QAction):
    def __init__(
            self,
            option: travellermap.Option,
            parent: typing.Optional[QtCore.QObject] = None
            ) -> None:
        super().__init__(option.value, parent)

        self._option = option

        self.setCheckable(True)
        self.setChecked(app.Config.instance().mapOption(option=option))

        # It's important that this is connected to the trigger signal before any instances
        # of TravellerMapWidget. This call needs to made first as it will write the updated
        # setting to the config so the instances of TravellerMapWidget can read it back when
        # updating their URL.
        self.triggered.connect(self._optionToggled)

    def _optionToggled(self) -> None:
        app.Config.instance().setMapOption(
            option=self._option,
            enabled=self.isChecked())

class _HexOverlay(object):
    def __init__(
            self,
            absoluteX: int,
            absoluteY: int,
            radius: float,
            colour: str
            ) -> None:
        self._absoluteX = absoluteX
        self._absoluteY = absoluteY
        self._radius = radius
        self._colour = colour

    def absoluteX(self) -> int:
        return self._absoluteX

    def absoluteY(self) -> int:
        return self._absoluteY

    def radius(self) -> float:
        return self._radius

    def colour(self) -> str:
        return self._colour

class TravellerMapWidgetBase(QtWidgets.QWidget):
    # These signals will pass the sector hex string for the hex under the cursor
    leftClicked = QtCore.pyqtSignal([str], [type(None)])
    rightClicked = QtCore.pyqtSignal([str], [type(None)])

    # Number of pixels of movement we allow between the left mouse button down and up events for
    # the action to be counted as a click. I found that forcing no movement caused clicks to be
    # missed
    _LeftClickMoveThreshold = 3

    # Number of pixels the cursor can move before the displayed tool tip will be hidden
    _ToolTipMoveThreshold = 5

    # Shared profile used by all instances of this widget. With Qt5 I could use the default profile,
    # however that wouldn't be possible if/when I switch to Qt6 as the default profile doesn't
    # persist cookies under Qt6. To avoid potential future issues I'm just using a custom shared
    # profile from the get go.
    _sharedProfile = None

    _sharedRequestInterceptor = None

    # Next script id (used for debugging)
    _nextScriptId = 1

    # Actions shared with all instances of this widget
    _sharedStyleActions: typing.List[_MapStyleToggleAction] = []
    _sharedFeatureActions: typing.List[_MapOptionToggleAction] = []
    _sharedAppearanceActions: typing.List[_MapOptionToggleAction] = []
    _sharedOverlayActions: typing.List[_MapOptionToggleAction] = []

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self._loaded = False
        self._scriptQueue: typing.List[str] = []
        self._clickTrackingRect = None

        self._jumpRoute = None
        self._overlays: typing.List[_HexOverlay] = []

        self._toolTipCallback = None
        self._toolTipTimer = None
        self._toolTipDisplayPos = None
        self._toolTipQueuePos = None
        self._toolTipScriptRunning = False

        self._styleOptionGroup = None

        if not TravellerMapWidgetBase._sharedProfile:
            # Create a shared profile for use by all instances of the widget. It's important to use
            # the application as the parent to prevent the error "Release of profile requested but
            # WebEnginePage still not deleted. Expect troubles !" being written out on application
            # shutdown.
            # https://stackoverflow.com/questions/64719361/closing-qwebengineview-warns-release-of-profile-requested-but-webenginepage-sti
            TravellerMapWidgetBase._sharedProfile = QtWebEngineWidgets.QWebEngineProfile(
                'TravellerMapWidget',
                QtWidgets.QApplication.instance())
            TravellerMapWidgetBase._sharedProfile.setHttpCacheType(
                QtWebEngineWidgets.QWebEngineProfile.HttpCacheType.DiskHttpCache)
            TravellerMapWidgetBase._sharedProfile.setCachePath(
                os.path.join(app.Config.instance().appDir(), 'webwidget', 'cache'))
            TravellerMapWidgetBase._sharedProfile.setPersistentCookiesPolicy(
                QtWebEngineWidgets.QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)
            TravellerMapWidgetBase._sharedProfile.setPersistentStoragePath(
                os.path.join(app.Config.instance().appDir(), 'webwidget', 'persist'))

        page = _CustomWebEnginePage(TravellerMapWidgetBase._sharedProfile, self)
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

        self._createSharedActions()
        self._createPrivateActions()

        self._loadMap()

    def reload(self) -> None:
        self._loaded = False
        self._scriptQueue.clear()
        self._clickTrackingRect = None

        self._hideToolTip()

        self._loadMap()

    def centerOnWorld(
            self,
            world: traveller.World,
            linearScale: typing.Optional[float] = 64, # None keeps current scale
            clearOverlays: bool = False,
            highlightWorld: bool = False,
            highlightRadius: float = 0.5,
            highlightColour: str = '#8080FF'
            ) -> None:
        self.centerOnHex(
            sectorX=world.sectorX(),
            sectorY=world.sectorY(),
            worldX=world.x(),
            worldY=world.y(),
            linearScale=linearScale,
            clearOverlays=clearOverlays,
            highlightHex=highlightWorld,
            highlightRadius=highlightRadius,
            highlightColour=highlightColour)

    def centerOnWorlds(
            self,
            worlds: typing.Iterable[traveller.World],
            clearOverlays: bool = False,
            highlightWorlds: bool = False,
            highlightRadius: float = 0.5,
            highlightColour: str = '#8080FF'
            ) -> None:
        if not worlds:
            # Nothing to display but clear the overlays if requested
            if clearOverlays:
                self.clearOverlays()
            return
        if len(worlds) == 1:
            # If there is just one world in the list so just show use centerOnWorld. This avoids
            # zooming to far because the bounding box surrounding the worlds has no size
            self.centerOnWorld(
                world=next(iter(worlds)),
                clearOverlays=clearOverlays,
                highlightWorld=highlightWorlds,
                highlightRadius=highlightRadius,
                highlightColour=highlightColour)
            return

        minX = maxX = minY = maxY = None
        for world in worlds:
            worldX = world.absoluteX()
            worldY = world.absoluteY()
            if minX == None or worldX < minX:
                minX = worldX
            if maxX == None or worldX > maxX:
                maxX = worldX
            if minY == None or worldY < minY:
                minY = worldY
            if maxY == None or worldY > maxY:
                maxY = worldY

        # Increase the bounding box to avoid zooming in to much with just a small number of close together
        # worlds
        minX -= 1
        maxX += 1
        minY -= 1
        maxY += 1

        script = f'map.CenterOnArea({minX}, {minY}, {maxX}, {maxY});'
        self._runScript(script=script)

        if clearOverlays:
            self.clearOverlays()
        if highlightWorlds:
            for world in worlds:
                self.highlightWorld(
                    world=world,
                    radius=highlightRadius,
                    colour=highlightColour)

    def centerOnHex(
            self,
            sectorX: int,
            sectorY: int,
            worldX: int,
            worldY: int,
            linearScale: typing.Optional[float] = 64, # None keeps current scale
            clearOverlays: bool = False,
            highlightHex: bool = False,
            highlightRadius: float = 0.5,
            highlightColour: str = '#8080FF'
            ) -> None:
        if linearScale != None:
            script = f'map.CenterAtSectorHex({sectorX}, {sectorY}, {worldX}, {worldY}, {{scale: {linearScale}}})'
        else:
            # When keeping the current scale, it's important to use map.scale rather than extracting
            # the scale from the current url. This is required in order for movements to be animated
            # rather than hard cuts to the new location. The implementation of CenterAtSectorHex
            # will only animate if the new scale is exactly the same as current scale. As the scale
            # is a float the only reliable way to do this is to use the current value.
            script = f'map.CenterAtSectorHex({sectorX}, {sectorY}, {worldX}, {worldY}, {{scale: map.scale}})'

        self._runScript(script)

        if clearOverlays:
            self.clearOverlays()
        if highlightHex:
            self.highlightHex(
                sectorX=sectorX,
                sectorY=sectorY,
                worldX=worldX,
                worldY=worldY,
                radius=highlightRadius,
                colour=highlightColour)

    def showJumpRoute(
            self,
            jumpRoute: typing.Iterable[traveller.World],
            refuellingPlan: typing.Optional[typing.Iterable[logic.PitStop]] = None,
            zoomToArea: bool = True,
            clearOverlays: bool = True,
            pitStopRadius: float = 0.4, # Default to slightly larger than the size of the highlights Traveller Map puts on jump worlds
            pitStopColour: str = '#8080FF'
            ) -> None:
        if clearOverlays:
            # When clearing the overlays it's important it's done before we set the new
            # jump route overlay (otherwise that will be cleared as well)
            self.clearOverlays()

        self._jumpRoute = jumpRoute
        if self._loaded:
            self._runJumpRouteScript(jumpRoute)

        if refuellingPlan:
            for pitStop in refuellingPlan:
                self.highlightWorld(
                    world=pitStop.world(),
                    radius=pitStopRadius,
                    colour=pitStopColour)

        if zoomToArea:
            self.centerOnWorlds(jumpRoute)

    def highlightWorlds(
            self,
            worlds: typing.Iterable[traveller.World],
            radius: float = 0.5,
            colour: str = '#8080FF'
            ) -> None:
        for world in worlds:
            self.highlightWorld(
                world=world,
                radius=radius,
                colour=colour)

    def highlightWorld(
            self,
            world: traveller.World,
            radius: float = 0.5,
            colour: str = '#8080FF'
            ) -> None:
        self.highlightHex(
            sectorX=world.sectorX(),
            sectorY=world.sectorY(),
            worldX=world.x(),
            worldY=world.y(),
            radius=radius,
            colour=colour)

    def highlightHex(
            self,
            sectorX: int,
            sectorY: int,
            worldX: int,
            worldY: int,
            radius: float = 0.5,
            colour: str = '#8080FF'
            ) -> None:
        absoluteX, absoluteY = travellermap.relativeHexToAbsoluteHex(sectorX, sectorY, worldX, worldY)
        overlay = _HexOverlay(
            absoluteX=absoluteX,
            absoluteY=absoluteY,
            radius=radius,
            colour=colour)
        self._overlays.append(overlay)

        if self._loaded:
            self._runOverlayScript(overlay=overlay)

    def clearWorldHighlight(
            self,
            world: traveller.World
            ) -> None:
        self.clearHexHighlight(
            sectorX=world.sectorX(),
            sectorY=world.sectorY(),
            worldX=world.x(),
            worldY=world.y())

    def clearHexHighlight(
            self,
            sectorX: int,
            sectorY: int,
            worldX: int,
            worldY: int
            ) -> None:
        absoluteX, absoluteY = travellermap.relativeHexToAbsoluteHex(sectorX, sectorY, worldX, worldY)
        self._overlays = [overlay for overlay in self._overlays if (overlay.absoluteX() != absoluteX or overlay.absoluteY() != absoluteY)]

        if self._loaded:
            script = """
                var worldX = {x}, worldY = {y};
                var filterCallback = (overlay) => {{
                    var worldPos = Traveller.Astrometrics.mapToWorld(overlay.x, overlay.y);
                    return worldPos.x != worldX || worldPos.y != worldY;
                }};
                map.FilterOverlays(filterCallback);
                """.format(x=absoluteX, y=absoluteY)
            self._runScript(script)

    def clearOverlays(self) -> None:
        self._jumpRoute = None
        self._overlays.clear()

        if self._loaded:
            script = """
                map.ClearOverlays();
                map.SetRoute(null);
                """
            self._runScript(script)

    def setToolTipCallback(
            self,
            callback: typing.Optional[typing.Callable[[str], typing.Optional[str]]],
            ) -> None:
        self._toolTipCallback = callback

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

    def _createSharedActions(self) -> None:
        styleMenu = QtWidgets.QMenu('Style', self)
        featureMenu = QtWidgets.QMenu('Features', self)
        appearanceMenu = QtWidgets.QMenu('Appearance', self)
        overlayMenu = QtWidgets.QMenu('Overlays', self)

        self._styleOptionGroup = QtWidgets.QActionGroup(self)

        if not TravellerMapWidgetBase._sharedStyleActions:
            for style in travellermap.Style:
                TravellerMapWidgetBase._sharedStyleActions.append(
                    _MapStyleToggleAction(style=style))

        if not TravellerMapWidgetBase._sharedFeatureActions:
            TravellerMapWidgetBase._sharedFeatureActions.append(_MapOptionToggleAction(
                option=travellermap.Option.GalacticDirections))
            TravellerMapWidgetBase._sharedFeatureActions.append(_MapOptionToggleAction(
                option=travellermap.Option.SectorGrid))
            TravellerMapWidgetBase._sharedFeatureActions.append(_MapOptionToggleAction(
                option=travellermap.Option.SectorNames))
            TravellerMapWidgetBase._sharedFeatureActions.append(_MapOptionToggleAction(
                option=travellermap.Option.Borders))
            TravellerMapWidgetBase._sharedFeatureActions.append(_MapOptionToggleAction(
                option=travellermap.Option.Routes))
            TravellerMapWidgetBase._sharedFeatureActions.append(_MapOptionToggleAction(
                option=travellermap.Option.RegionNames))
            TravellerMapWidgetBase._sharedFeatureActions.append(_MapOptionToggleAction(
                option=travellermap.Option.ImportantWorlds))

        if not TravellerMapWidgetBase._sharedAppearanceActions:
            TravellerMapWidgetBase._sharedAppearanceActions.append(_MapOptionToggleAction(
                option=travellermap.Option.WorldColours))
            TravellerMapWidgetBase._sharedAppearanceActions.append(_MapOptionToggleAction(
                option=travellermap.Option.FilledBorders))
            TravellerMapWidgetBase._sharedAppearanceActions.append(_MapOptionToggleAction(
                option=travellermap.Option.DimUnofficial))

        if not TravellerMapWidgetBase._sharedOverlayActions:
            TravellerMapWidgetBase._sharedOverlayActions.append(_MapOptionToggleAction(
                option=travellermap.Option.ImportanceOverlay))
            TravellerMapWidgetBase._sharedOverlayActions.append(_MapOptionToggleAction(
                option=travellermap.Option.PopulationOverlay))
            TravellerMapWidgetBase._sharedOverlayActions.append(_MapOptionToggleAction(
                option=travellermap.Option.CapitalsOverlay))
            TravellerMapWidgetBase._sharedOverlayActions.append(_MapOptionToggleAction(
                option=travellermap.Option.MinorRaceOverlay))
            TravellerMapWidgetBase._sharedOverlayActions.append(_MapOptionToggleAction(
                option=travellermap.Option.DroyneWorldOverlay))
            TravellerMapWidgetBase._sharedOverlayActions.append(_MapOptionToggleAction(
                option=travellermap.Option.AncientSitesOverlay))
            TravellerMapWidgetBase._sharedOverlayActions.append(_MapOptionToggleAction(
                option=travellermap.Option.StellarOverlay))
            TravellerMapWidgetBase._sharedOverlayActions.append(_MapOptionToggleAction(
                option=travellermap.Option.EmpressWaveOverlay))
            TravellerMapWidgetBase._sharedOverlayActions.append(_MapOptionToggleAction(
                option=travellermap.Option.QrekrshaZoneOverlay))
            TravellerMapWidgetBase._sharedOverlayActions.append(_MapOptionToggleAction(
                option=travellermap.Option.MainsOverlay))

        for action in TravellerMapWidgetBase._sharedStyleActions:
            self._styleOptionGroup.addAction(action)
            action.triggered.connect(self.reload)
            styleMenu.addAction(action)
        stylesAction = QtWidgets.QAction('Styles', self)
        stylesAction.setMenu(styleMenu)
        self.addAction(stylesAction)

        for action in TravellerMapWidgetBase._sharedFeatureActions:
            action.triggered.connect(self.reload)
            featureMenu.addAction(action)
        featuresAction = QtWidgets.QAction('Features', self)
        featuresAction.setMenu(featureMenu)
        self.addAction(featuresAction)

        for action in TravellerMapWidgetBase._sharedAppearanceActions:
            action.triggered.connect(self.reload)
            appearanceMenu.addAction(action)
        appearanceAction = QtWidgets.QAction('Appearance', self)
        appearanceAction.setMenu(appearanceMenu)
        self.addAction(appearanceAction)

        for action in TravellerMapWidgetBase._sharedOverlayActions:
            action.triggered.connect(self.reload)
            overlayMenu.addAction(action)
        overlaysAction = QtWidgets.QAction('Overlays', self)
        overlaysAction.setMenu(overlayMenu)
        self.addAction(overlaysAction)

    def _createPrivateActions(self) -> None:
        reloadAction = QtWidgets.QAction('Reload', self)
        reloadAction.triggered.connect(self.reload)
        self.addAction(reloadAction)

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
            const LoopbackRegex = /^(127\.\d\.\d\.\d|localhost|loopback)$/;
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
            """.format(poolSize=app.Config.instance().proxyHostPoolSize())
        self._runScript(script)

    # NOTE: The 'tilt' url parameter isn't supported as it doesn't draw properly in the Qt widget
    def _generateUrl(self) -> QtCore.QUrl:
        currentUrl = self._mapWidget.url().toString()
        currentPos = travellermap.parsePosFromMapUrl(url=currentUrl) if currentUrl else None
        currentScale = travellermap.parseScaleFromMapUrl(url=currentUrl) if currentUrl else None

        installDir = app.Config.instance().installDir()
        rootPath = installDir.replace('\\', '/') if common.isWindows() else installDir

        if proxy.MapProxy.instance().isRunning():
            indexUrl =  proxy.MapProxy.instance().accessUrl()
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
        logging.debug(f'TravellerMapWidget loading {url.toString()}')

        if proxy.MapProxy.instance().isRunning():
            self._injectImageHostRoundRobin()

        self._mapWidget.load(url)

    def _runJumpRouteScript(
            self,
            jumpRoute: typing.Iterable[traveller.World],
            ) -> None:
        script = 'map.SetRoute(['
        for world in jumpRoute:
            script += f'{{hx:{world.x()}, hy:{world.y()}, sx:{world.sectorX()}, sy:{world.sectorY()}}},'
        script = script.strip(',')
        script += ']);'
        self._runScript(script)

    def _runOverlayScript(
            self,
            overlay: _HexOverlay
            ) -> None:
        script = """
            var worldX = {x}, worldY = {y};
            var mapPosition = Traveller.Astrometrics.worldToMap(worldX, worldY);
            var overlay = {{type: 'circle', x:mapPosition.x, y:mapPosition.y, r:{radius}, style:'{colour}'}};
            map.AddOverlay(overlay);
            """.format(
            x=overlay.absoluteX(),
            y=overlay.absoluteY(),
            radius=overlay.radius(),
            colour=overlay.colour())
        self._runScript(script)

    def _sectorHexAt(
            self,
            position: QtCore.QPoint,
            callback: typing.Callable[[typing.Optional[traveller.World]], None]
            ) -> None:
        script = """
            var mapPos = map.pixelToMap({x}, {y});
            var worldPos = Traveller.Astrometrics.mapToWorld(mapPos.x, mapPos.y);
            var sectorHex = Traveller.Astrometrics.worldToSectorHex(worldPos.x, worldPos.y);
            `${{sectorHex.sx}} ${{sectorHex.sy}} ${{sectorHex.hx}} ${{sectorHex.hy}}`;
            """.format(x=position.x(), y=position.y())

        self._runScript(
            script=script,
            resultsCallback=lambda results: callback(self._parseCursorHexResult(results)))

    def _worldAt(
            self,
            position: QtCore.QPoint,
            callback: typing.Callable[[typing.Optional[traveller.World]], None]
            ) -> None:
        self._sectorHexAt(
            position=position,
            callback=lambda sectorHex: callback(self._sectorHexToWorld(sectorHex=sectorHex)))

    def _parseCursorHexResult(
            self,
            returnValue: str
            ) -> typing.Optional[traveller.World]:
        if not returnValue or type(returnValue) != str:
            logging.error(f'Failed to parse TravellerMapWidget click result (Incorrect result type)')
            return None
        result = re.match(r'^([+-]?\d+) ([+-]?\d+) ([+-]?\d+) ([+-]?\d+)$', returnValue)
        if not result:
            logging.error(f'Failed to parse TravellerMapWidget click result (Incorrect format "{returnValue}")')
            return None

        try:
            sectorX = int(result.group(1))
            sectorY = int(result.group(2))
            sectorName = traveller.WorldManager.instance().sectorName(sectorX=sectorX, sectorY=sectorY)
            if not sectorName:
                # This is only logged at debug as it legitimately occurs if the user clicks
                # on an area which has no sector data
                logging.debug(f'Failed to parse TravellerMapWidget click result (No sector at {sectorX}, {sectorY})')
                return None

            worldX = int(result.group(3))
            worldY = int(result.group(4))
            return traveller.formatSectorHex(
                sectorName=sectorName,
                worldX=worldX,
                worldY=worldY)
        except Exception as ex:
            logging.error(f'Failed to parse TravellerMapWidget click result (Unexpected exception)', exc_info=ex)
            return None

    def _sectorHexToWorld(
            self,
            sectorHex: str
            ) -> typing.Optional[traveller.World]:
        if not sectorHex:
            # This can happen if the cursor is outside the known universe
            return None

        try:
            return traveller.WorldManager.instance().world(sectorHex=sectorHex)
        except Exception as ex:
            logging.error(f'Exception occurred while resolving sector hex "{sectorHex}" to world', exc_info=ex)
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
            position: QtCore.QPoint
            ) -> None:
        self._sectorHexAt(
            position=position,
            callback=self._handleLeftClickEvent)

    def _primeRightClickEvent(
            self,
            position: QtCore.QPoint
            ) -> None:
        self._sectorHexAt(
            position=position,
            callback=self._handleRightClickEvent)

    def _handleLeftClickEvent(
            self,
            sectorHex: typing.Optional[str]
            ) -> None:
        self._emitLeftClickEvent(sectorHex=sectorHex)

    def _handleRightClickEvent(
            self,
            sectorHex: typing.Optional[str]
            ) -> None:
        self._emitRightClickEvent(sectorHex=sectorHex)

    def _emitLeftClickEvent(
            self,
            sectorHex: typing.Optional[str]
            ) -> None:
        if self.isEnabled():
            self.leftClicked.emit(sectorHex)

    def _emitRightClickEvent(
            self,
            sectorHex: typing.Optional[str]
            ) -> None:
        if self.isEnabled():
            self.rightClicked.emit(sectorHex)

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
            self._sectorHexAt(
                position=cursorPos,
                callback=self._handleToolTipSectorHex)
        else:
            self._toolTipQueuePos = cursorPos

    def _handleToolTipSectorHex(
            self,
            sectorHex: typing.Optional[str]
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

        toolTip = self._toolTipCallback(sectorHex)
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

        for overlay in self._overlays:
            self._runOverlayScript(overlay=overlay)

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

        scriptId = TravellerMapWidgetBase._nextScriptId
        TravellerMapWidgetBase._nextScriptId += 1

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
