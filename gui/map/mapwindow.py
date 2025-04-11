import gui
import logging
import logic
import travellermap
import typing
from PyQt5 import QtCore, QtWidgets

class MapWindow(gui.WindowWidget):
    def __init__(self) -> None:
        super().__init__(
            title='Traveller Map',
            configSection='MapWindow')
        self._mapWidget = gui.MapWidgetEx()

        self._importJumpRouteButton = QtWidgets.QPushButton('Import Jump Route...')
        self._importJumpRouteButton.clicked.connect(self._importJumpRoute)

        windowLayout = QtWidgets.QVBoxLayout()
        windowLayout.addWidget(self._mapWidget)
        windowLayout.addWidget(self._importJumpRouteButton)
        self.setLayout(windowLayout)

    def centerOnHex(
            self,
            hex: travellermap.HexPosition,
            linearScale: typing.Optional[float] = 64 # None keeps current scale
            ) -> None:
        self._mapWidget.centerOnHex(
            hex=hex,
            linearScale=linearScale,
            skipAnimation=self.isHidden())

    def centerOnHexes(
            self,
            hexes: travellermap.HexPosition
            ) -> None:
        self._mapWidget.centerOnHexes(
            hexes=hexes,
            skipAnimation=self.isHidden())

    def setJumpRoute(
            self,
            jumpRoute: typing.Optional[logic.JumpRoute],
            refuellingPlan: typing.Optional[typing.Iterable[logic.PitStop]] = None
            ) -> None:
        self._mapWidget.setJumpRoute(
            jumpRoute=jumpRoute,
            refuellingPlan=refuellingPlan)
        self._mapWidget.centerOnJumpRoute(
            skipAnimation=self.isHidden())

    def highlightHex(
            self,
            hex: travellermap.HexPosition,
            radius: float = 0.5,
            colour: str = '#8080FF'
            ) -> None:
        self._mapWidget.highlightHex(
            hex=hex,
            radius=radius,
            colour=colour)
        self._mapWidget.centerOnHex(
            hex=hex,
            skipAnimation=self.isHidden())

    def highlightHexes(
            self,
            hexes: typing.Iterable[travellermap.HexPosition],
            radius: float = 0.5,
            colour: str = '#8080FF'
            ) -> None:
        self._mapWidget.highlightHexes(
            hexes=hexes,
            radius=radius,
            colour=colour)
        self._mapWidget.centerOnHexes(
            hexes=hexes,
            skipAnimation=self.isHidden())

    def clearOverlays(self) -> None:
        self._mapWidget.clearHexHighlights()
        self._mapWidget.clearJumpRoute()

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

        self.setJumpRoute(jumpRoute=jumpRoute)
