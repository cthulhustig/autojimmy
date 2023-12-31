import gui
import logging
import logic
import traveller
import typing
from PyQt5 import QtCore, QtWidgets

class TravellerMapWindow(gui.WindowWidget):
    def __init__(self) -> None:
        super().__init__(
            title='Traveller Map',
            configSection='TravellerMapWindow')
        self._mapWidget = gui.TravellerMapWidget()

        self._importJumpRouteButton = QtWidgets.QPushButton('Import Jump Route...')
        self._importJumpRouteButton.clicked.connect(self._importJumpRoute)

        windowLayout = QtWidgets.QVBoxLayout()
        windowLayout.addWidget(self._mapWidget)
        windowLayout.addWidget(self._importJumpRouteButton)
        self.setLayout(windowLayout)

    def centerOnWorld(
            self,
            world: traveller.World,
            linearScale: typing.Optional[float] = 64, # None keeps current scale
            clearOverlays: bool = False,
            highlightWorld: bool = False,
            highlightRadius: float = 0.5
            ) -> None:
        self._mapWidget.centerOnWorld(
            world=world,
            linearScale=linearScale,
            clearOverlays=clearOverlays,
            highlightWorld=highlightWorld,
            highlightRadius=highlightRadius)

    def centerOnWorlds(
            self,
            worlds: typing.Iterable[traveller.World],
            clearOverlays: bool = False,
            highlightWorlds: bool = False,
            highlightRadius: float = 0.5
            ) -> None:
        self._mapWidget.centerOnWorlds(
            worlds=worlds,
            clearOverlays=clearOverlays,
            highlightWorlds=highlightWorlds,
            highlightRadius=highlightRadius)

    def centerOnHex(
            self,
            sectorX: int,
            sectorY: int,
            worldX: int,
            worldY: int,
            linearScale: typing.Optional[float] = 64, # None keeps current scale
            clearOverlays: bool = False,
            highlightHex: bool = False,
            highlightRadius: float = 0.5
            ) -> None:
        self._mapWidget.centerOnHex(
            self,
            sectorX=sectorX,
            sectorY=sectorY,
            worldX=worldX,
            worldY=worldY,
            linearScale=linearScale,
            clearOverlays=clearOverlays,
            highlightHex=highlightHex,
            highlightRadius=highlightRadius)

    def showJumpRoute(
            self,
            jumpRoute: typing.Iterable[traveller.World],
            refuellingPlan: typing.Optional[typing.Iterable[logic.PitStop]] = None,
            zoomToArea: bool = True,
            clearOverlays: bool = True,
            highlightRadius: float = 0.4 # Default to slightly larger than the size of the highlights Traveller Map puts on jump worlds
            ) -> None:
        self._mapWidget.showJumpRoute(
            jumpRoute=jumpRoute,
            refuellingPlan=refuellingPlan,
            zoomToArea=zoomToArea,
            clearOverlays=clearOverlays,
            pitStopRadius=highlightRadius)

    def highlightWorld(
            self,
            world: traveller.World,
            radius: float = 0.5
            ) -> None:
        self.highlightHex(
            sectorX=world.sectorX(),
            sectorY=world.sectorY(),
            worldX=world.x(),
            worldY=world.y(),
            radius=radius)

    def highlightHex(
            self,
            sectorX: int,
            sectorY: int,
            worldX: int,
            worldY: int,
            radius: float = 0.5
            ) -> None:
        self._mapWidget.highlightHex(
            sectorX=sectorX,
            sectorY=sectorY,
            worldX=worldX,
            worldY=worldY,
            radius=radius)

    def clearWorldHighlight(
            self,
            world: traveller.World
            ) -> None:
        self._mapWidget.clearWorldHighlight(world=world)

    def clearHexHighlight(
            self,
            sectorX: int,
            sectorY: int,
            worldX: int,
            worldY: int
            ) -> None:
        self._mapWidget.clearWorldHighlight(
            sectorX=sectorX,
            sectorY=sectorY,
            hexX=worldX,
            hexY=worldY)

    def clearOverlays(self) -> None:
        self._mapWidget.clearOverlays()

    def loadSettings(self) -> None:
        super().loadSettings()

        self._settings.beginGroup(self._configSection)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='MapWidgetState',
            type=QtCore.QByteArray)
        if storedValue:
            self._mapWidget.restoreState(storedValue)

        self._settings.endGroup()

    def saveSettings(self) -> None:
        self._settings.beginGroup(self._configSection)
        self._settings.setValue('MapWidgetState', self._mapWidget.saveState())
        self._settings.endGroup()

        super().saveSettings()

    def  _importJumpRoute(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            'Open File',
            QtCore.QDir.homePath(),
            'JSON (*.json)')
        if not path:
            return

        try:
            jumpRoute = logic.readJumpRoute(path)
        except Exception as ex:
            message = f'Failed to import jump route from "{path}"'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

        self.showJumpRoute(
            jumpRoute=jumpRoute,
            clearOverlays=True)
